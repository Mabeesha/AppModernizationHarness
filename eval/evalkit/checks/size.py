"""Group A — Size & Budget.

Emits *metrics*, not findings. Instruction sets tolerate — and often require —
redundancy that prose does not, so "this file is large" is not a defect and this
group never gates CI. The one exception is the opt-in ``--budget-warn`` ceiling,
which fires only when the operator asks for one.

All counts come from the active token backend (see ``evalkit/tokens.py``). With
the interim tiktoken backend they are approximate and labelled as such.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..model import CheckResult, Finding, Metric, Severity
from ..registry import Context, check

# --------------------------------------------------------------------------
# Stage load-outs: what a single run of each stage actually pulls into context.
#
# `fixed`    - instruction files, always present in the set, always measurable.
# `variable` - generated artifacts, only measurable against a real output dir
#              (--docs). Globs, because <AppName> varies per project.
#
# The legacy source is deliberately excluded. It dwarfs the instruction overhead
# and varies per project; folding it in would make the instruction-side number
# meaningless.
# --------------------------------------------------------------------------
STAGE_LOADOUTS: dict[str, dict[str, list[str]]] = {
    "stage-0": {
        "fixed": ["AGENTS_TEMPLATE.md", "0_PROJECT_CONTEXT_INSTRUCTIONS.md", "0_INTAKE_TEMPLATE.md"],
        "variable": [],
    },
    "stage-1": {
        "fixed": ["AGENTS_TEMPLATE.md", "1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md"],
        "variable": ["PROJECT_CONTEXT.md", "state.json"],
    },
    "stage-2": {
        "fixed": ["AGENTS_TEMPLATE.md", "2_DESIGN_INSTRUCTIONS.md"],
        "variable": [
            "PROJECT_CONTEXT.md", "state.json",
            "BUSINESS_REQUIREMENTS_*.md", "FUNCTIONAL_REQUIREMENTS_*.md",
            "TECHNICAL_REQUIREMENTS_*.md",
        ],
    },
    "stage-3": {
        "fixed": ["AGENTS_TEMPLATE.md", "3_PLAN_INSTRUCTIONS.md"],
        "variable": [
            "PROJECT_CONTEXT.md", "state.json",
            "HIGH_LEVEL_DESIGN_*.md", "LOW_LEVEL_DESIGN_*.md",
            "BUSINESS_REQUIREMENTS_*.md", "FUNCTIONAL_REQUIREMENTS_*.md",
            "TECHNICAL_REQUIREMENTS_*.md",
        ],
    },
    "stage-4": {
        "fixed": ["AGENTS_TEMPLATE.md", "4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md"],
        "variable": [
            "PROJECT_CONTEXT.md", "state.json", "PLAN_*.md",
            "HIGH_LEVEL_DESIGN_*.md", "LOW_LEVEL_DESIGN_*.md",
            "BUSINESS_REQUIREMENTS_*.md", "FUNCTIONAL_REQUIREMENTS_*.md",
            "TECHNICAL_REQUIREMENTS_*.md",
        ],
    },
    "stage-5": {
        "fixed": ["AGENTS_TEMPLATE.md", "5_REVIEW_INSTRUCTIONS.md"],
        "variable": [
            "PROJECT_CONTEXT.md", "state.json", "PLAN_*.md",
            "HIGH_LEVEL_DESIGN_*.md", "LOW_LEVEL_DESIGN_*.md",
            "BUSINESS_REQUIREMENTS_*.md", "FUNCTIONAL_REQUIREMENTS_*.md",
            "TECHNICAL_REQUIREMENTS_*.md",
        ],
    },
}


@check("A1", "Per-file token count")
def a1_per_file(ctx: Context) -> CheckResult:
    res = CheckResult()
    for doc in ctx.iset.documents:
        res.metrics.append(
            Metric(
                check="A1",
                name="file_tokens",
                value=ctx.counter.count(doc.text),
                unit="tokens",
                context={
                    "file": doc.repo_relative,
                    "bytes": len(doc.text.encode("utf-8")),
                    "lines": len(doc.lines),
                    "approximate": ctx.counter.approximate,
                },
            )
        )
    return res


@check("A2", "Per-section token count")
def a2_per_section(ctx: Context) -> CheckResult:
    """Attribution within a file: which top-level section carries the weight.

    These will NOT sum to the A1 figure for the same file — same non-additivity
    reason as A3. Reported as share-of-file rather than as a total.
    """
    res = CheckResult()
    for doc in ctx.iset.documents:
        tops = [h for h in doc.headings if h.level == 2 and not h.in_fence]
        if not tops:
            continue
        file_tokens = ctx.counter.count(doc.text)
        bounds = [h.line for h in tops] + [len(doc.lines) + 1]
        for i, h in enumerate(tops):
            body = "\n".join(doc.lines[bounds[i] - 1: bounds[i + 1] - 1])
            tokens = ctx.counter.count(body)
            res.metrics.append(
                Metric(
                    check="A2",
                    name="section_tokens",
                    value=tokens,
                    unit="tokens",
                    context={
                        "file": doc.repo_relative,
                        "section": h.text,
                        "line": h.line,
                        "share_of_file": round(tokens / file_tokens, 4) if file_tokens else 0.0,
                        "approximate": ctx.counter.approximate,
                    },
                )
            )
    return res


def _resolve(patterns: list[str], docs, set_root: Path) -> tuple[list[str], list[str]]:
    """Match load-out patterns against supplied --docs. Returns (texts, missing)."""
    by_name = {d.name: d for d in docs}
    texts: list[str] = []
    missing: list[str] = []
    for pat in patterns:
        if "*" in pat:
            hits = [d for n, d in by_name.items() if Path(n).match(pat)]
            if hits:
                texts.extend(h.text for h in hits)
            else:
                missing.append(pat)
        elif pat in by_name:
            texts.append(by_name[pat].text)
        else:
            missing.append(pat)
    return texts, missing


@check("A3", "Composite per-stage context budget")
def a3_stage_budget(ctx: Context) -> CheckResult:
    """The number that actually matters: what one stage run loads, counted as one payload.

    Split into a fixed half (instruction files) and a variable half (generated
    artifacts). Without --docs the variable half is reported as `unmeasured`
    rather than estimated — a guessed number here is worse than no number.
    """
    res = CheckResult()
    warn_at = ctx.config.get("budget_warn")

    # --docs may hold non-Markdown inputs (state.json); pick them up as raw text.
    extra_texts: dict[str, str] = {}
    docs_dir = ctx.config.get("docs_dir")
    if docs_dir:
        for p in Path(docs_dir).glob("*.json"):
            try:
                extra_texts[p.name] = p.read_text(encoding="utf-8")
            except OSError:
                pass

    class _Shim:
        def __init__(self, name: str, text: str):
            self.name, self.text = name, text

    available = list(ctx.docs) + [_Shim(n, t) for n, t in extra_texts.items()]

    for stage, spec in STAGE_LOADOUTS.items():
        fixed_texts, fixed_missing = _resolve(spec["fixed"], ctx.iset.documents, ctx.iset.root)
        fixed_tokens = ctx.counter.count_composite(fixed_texts) if fixed_texts else 0

        var_tokens = None
        var_missing: list[str] = []
        if spec["variable"]:
            if available:
                var_texts, var_missing = _resolve(spec["variable"], available, ctx.iset.root)
                if var_texts:
                    var_tokens = ctx.counter.count_composite(var_texts)
            # else: leave None -> "unmeasured"

        total = fixed_tokens + (var_tokens or 0)
        res.metrics.append(
            Metric(
                check="A3",
                name="stage_budget",
                value=total,
                unit="tokens",
                context={
                    "stage": stage,
                    "fixed_tokens": fixed_tokens,
                    "fixed_files": spec["fixed"],
                    "fixed_missing": fixed_missing,
                    "variable_tokens": var_tokens if var_tokens is not None else "unmeasured",
                    "variable_patterns": spec["variable"],
                    "variable_missing": var_missing,
                    # "complete" requires every declared artifact to have been
                    # found, not merely some of them — a partial measurement
                    # rendered as a bare total reads as a full one.
                    "complete": (
                        not spec["variable"]
                        or (var_tokens is not None and not var_missing)
                    ),
                    "approximate": ctx.counter.approximate,
                },
            )
        )

        if warn_at and total > warn_at:
            res.findings.append(
                Finding(
                    check="A3",
                    severity=Severity.MAJOR,
                    summary=f"{stage} context budget {total} exceeds --budget-warn {warn_at}",
                    detail=(
                        f"Fixed instruction overhead {fixed_tokens} tokens; variable "
                        f"{var_tokens if var_tokens is not None else 'unmeasured'}. "
                        "Counts are approximate under the tiktoken backend."
                    ),
                    file=ctx.iset.name,
                    subject=stage,
                )
            )
    return res


@check("A4", "Token growth vs git HEAD")
def a4_growth(ctx: Context) -> CheckResult:
    """Per-file token delta against the previous commit.

    Skips cleanly outside a git work tree, and skips files with no HEAD version
    (newly added) rather than reporting their whole size as growth.
    """
    res = CheckResult()

    def git(*args: str) -> tuple[int, str]:
        try:
            # encoding/errors are explicit on purpose: text=True alone decodes with
            # the platform locale, which is cp1252 on Windows. A single em-dash in a
            # tracked file then raises inside subprocess's reader thread, stdout comes
            # back None, and the check dies with an unrelated AttributeError.
            p = subprocess.run(
                ["git", "-C", str(ctx.repo_root), *args],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
            return p.returncode, p.stdout or ""
        except (OSError, subprocess.SubprocessError):
            return 1, ""

    rc, _ = git("rev-parse", "--git-dir")
    if rc != 0:
        res.skipped = "not a git work tree"
        return res

    for doc in ctx.iset.documents:
        rc, prior = git("show", f"HEAD:{doc.repo_relative}")
        if rc != 0:
            continue  # not in HEAD (new file) — no baseline to diff against
        before = ctx.counter.count(prior)
        after = ctx.counter.count(doc.text)
        if before == after:
            continue
        res.metrics.append(
            Metric(
                check="A4",
                name="token_delta",
                value=after - before,
                unit="tokens",
                context={
                    "file": doc.repo_relative,
                    "head_tokens": before,
                    "worktree_tokens": after,
                    "pct": round((after - before) / before * 100, 1) if before else None,
                    "approximate": ctx.counter.approximate,
                },
            )
        )
    return res
