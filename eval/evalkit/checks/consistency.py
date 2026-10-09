"""Group D — Consistency & Drift.

D1/D3/D4/D5 are deterministic. D2 (near-duplicate rules that have *diverged*) is the
most valuable check in the group and needs the judge harness — registered as a
stub. Note D2 fires only on divergence, never on duplication: restatement across
`AGENTS.md` and the stage files is deliberate in these sets, so a naive
duplicate detector would be pure noise.
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from pathlib import Path

from ..model import CheckResult, Finding, Metric, Severity
from ..registry import Context, check

VOCAB_DIR = Path(__file__).resolve().parent.parent / "vocab"

# Terms appear as `pending`, "pending", or bare in prose. Backtick/quote forms
# are the reliable signal; bare prose words like "done" are far too common.
TERM_RE = re.compile(r'[`"](?P<term>[A-Za-z][A-Za-z0-9 _-]{2,30})[`"]')

# Case-insensitive on purpose: these sets write imperatives as lowercase prose
# ("**never** modify", "you must") far more often than in caps. An uppercase-only
# pattern scores every file at zero — which is how this check silently did
# nothing until fault injection caught it.
MODALITY_RE = re.compile(
    r"\b(MUST NOT|MUST|NEVER|ALWAYS|SHALL NOT|SHALL|DO NOT|DON'T|REQUIRED)\b",
    re.IGNORECASE,
)

MERMAID_HINT_RE = re.compile(
    r"^\s*(graph\s+(TD|LR|RL|BT)|flowchart\s+(TD|LR|RL|BT)|sequenceDiagram|"
    r"classDiagram|stateDiagram(-v2)?|erDiagram|gantt|journey)\b",
    re.M,
)


def _load_vocab(name: str) -> list[str]:
    path = VOCAB_DIR / name
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def _norm(term: str) -> str:
    return re.sub(r"[\s_-]+", " ", term.strip().lower())


@check("D1", "Controlled vocabulary")
def d1_vocabulary(ctx: Context) -> CheckResult:
    """Status values and notation markers used in exactly one spelling.

    Catches `in-progress` vs `in progress`, `changes requested` vs
    `changes-requested`, `OPEN_QUESTION:` vs `OPEN QUESTION:` — drift that makes
    an agent guess which literal a state field actually expects.
    """
    res = CheckResult()

    canonical = {_norm(t): t for t in _load_vocab("status_values.txt")}
    if not canonical:
        res.skipped = "vocab/status_values.txt is empty or missing"
        return res

    seen: dict[str, dict[str, list[tuple[str, int]]]] = defaultdict(lambda: defaultdict(list))
    for doc in ctx.iset.documents:
        for line_no, raw in enumerate(doc.lines, start=1):
            for m in TERM_RE.finditer(raw):
                term = m.group("term")
                key = _norm(term)
                if key in canonical:
                    seen[key][term].append((doc.repo_relative, line_no))

    for key, spellings in sorted(seen.items()):
        want = canonical[key]
        deviants = {s: sites for s, sites in spellings.items() if s != want}
        if not deviants:
            continue
        for spelling, sites in sorted(deviants.items()):
            f, l = sites[0]
            res.findings.append(
                Finding(
                    check="D1",
                    severity=Severity.MAJOR,
                    summary=f"`{spelling}` used where the canonical term is `{want}`",
                    detail=(
                        f"{len(sites)} occurrence(s). State values are compared literally by "
                        "agents reading state.json; two spellings means one of them silently "
                        "never matches."
                    ),
                    file=f,
                    line=l,
                    subject=f"vocab:{key}:{spelling}",
                    evidence=[f"{a}:{b}" for a, b in sites[:5]],
                )
            )

    # Notation markers: verbatim, including the colon.
    for marker in _load_vocab("markers.txt"):
        stem = marker.rstrip(":")
        variant = re.compile(
            rf"\b{re.escape(stem).replace(' ', '[ _-]')}\b:?", re.I
        )
        for doc in ctx.iset.documents:
            for line_no, raw in enumerate(doc.lines, start=1):
                for m in variant.finditer(raw):
                    got = m.group(0)
                    if got == marker or got == stem:
                        continue
                    if got.upper().replace("_", " ").rstrip(":") != stem:
                        continue
                    res.findings.append(
                        Finding(
                            check="D1",
                            severity=Severity.MAJOR,
                            summary=f"Notation marker `{got}` deviates from `{marker}`",
                            detail="Markers are matched verbatim by downstream stages.",
                            file=doc.repo_relative,
                            line=line_no,
                            subject=f"marker:{got}",
                            evidence=[raw.strip()],
                        )
                    )
    return res


@check("D3", "Modality density")
def d3_modality(ctx: Context) -> CheckResult:
    """MUST/NEVER/ALWAYS per 1k tokens, flagged only as an outlier against the
    set's own median. A smell, not a defect — MINOR, and a prune candidate."""
    res = CheckResult()
    rows: list[tuple[str, float, int, int]] = []

    for doc in ctx.iset.documents:
        tokens = ctx.counter.count(doc.text)
        if tokens < 200:
            continue
        hits = len(MODALITY_RE.findall(doc.text))
        density = hits / (tokens / 1000)
        rows.append((doc.repo_relative, density, hits, tokens))
        res.metrics.append(
            Metric(
                check="D3",
                name="modality_density",
                value=round(density, 2),
                unit="per 1k tokens",
                context={
                    "file": doc.repo_relative,
                    "hits": hits,
                    "tokens": tokens,
                    "approximate": ctx.counter.approximate,
                },
            )
        )

    if len(rows) < 3:
        return res

    med = statistics.median(r[1] for r in rows)
    if med <= 0:
        return res

    for path, density, hits, tokens in rows:
        if density > med * 2:
            res.findings.append(
                Finding(
                    check="D3",
                    severity=Severity.MINOR,
                    summary=f"Modality density {density:.1f}/1k is {density / med:.1f}x the set median",
                    detail=(
                        f"{hits} imperative markers across ~{tokens} tokens (set median "
                        f"{med:.1f}/1k). Emphasis inflation tends to flatten the signal that "
                        "genuinely load-bearing rules carry."
                    ),
                    file=path,
                    subject=f"modality:{path}",
                )
            )
    return res


@check("D4", "Format conventions")
def d4_format(ctx: Context) -> CheckResult:
    """Diagram fences tagged `mermaid`, and fenced blocks carrying a language tag.

    The sets declare both conventions themselves ("Diagrams in Mermaid, fenced as
    ```mermaid, with a caption"), so this measures the set against its own rule.
    """
    res = CheckResult()

    for doc in ctx.iset.documents:
        for fence in doc.fences:
            if fence.lang == "mermaid":
                continue
            if MERMAID_HINT_RE.search(fence.content):
                res.findings.append(
                    Finding(
                        check="D4",
                        severity=Severity.MAJOR,
                        summary="Diagram fence is not tagged ```mermaid",
                        detail=(
                            f"Fence at line {fence.start_line} contains Mermaid syntax but is "
                            f"tagged `{fence.lang or 'none'}`. The set's own notation rule "
                            "requires the mermaid tag; untagged diagrams do not render."
                        ),
                        file=doc.repo_relative,
                        line=fence.start_line,
                        subject=f"mermaid-fence:{doc.repo_relative}:{fence.start_line}",
                    )
                )
            elif fence.lang is None and len(fence.content.strip()) > 40:
                res.findings.append(
                    Finding(
                        check="D4",
                        severity=Severity.MINOR,
                        summary="Fenced block has no language tag",
                        detail=(
                            f"Fence at line {fence.start_line}. Untagged fences lose syntax "
                            "highlighting and make template blocks harder to identify "
                            "programmatically."
                        ),
                        file=doc.repo_relative,
                        line=fence.start_line,
                        subject=f"untagged-fence:{doc.repo_relative}:{fence.start_line}",
                    )
                )
    return res


INTAKE_TEMPLATE = "0_INTAKE_TEMPLATE.md"
INTAKE_QID_RE = re.compile(r"^(?P<qid>\d+[a-z]?)\.\s")
# Any GFM task item: indented, quoted, bulleted with -/*/+ or numbered.
TICK_RE = re.compile(r"^\s*(?:>\s*)*(?:[-*+]|\d+[.)]) \[[ xX]\](?:\s|$)")


def _details_lines(doc) -> tuple[set[int], list[tuple[int, str]]]:
    """Line numbers inside `<details>…</details>` — folded guidance, never question content.

    Only tags that start a line count, so prose mentioning `<details>` cannot open a
    fold. Also returns problems: a fold opened inside another (the template never
    nests them) or never closed — either hides the questions after it, up to the
    next `<details>`.
    """
    out: set[int] = set()
    problems: list[tuple[int, str]] = []
    open_at = 0
    for n, raw in enumerate(doc.lines, start=1):
        if doc.is_fenced(n):
            continue
        low = raw.strip().lower()
        opens, closes = low.startswith("<details"), "</details>" in low
        if opens and open_at:
            problems.append((open_at, f"`<details>` opened at line {open_at} is not closed before line {n}"))
        if opens:
            open_at = n
        if open_at:
            out.add(n)
        if closes and (opens or low.startswith("</details>")):
            open_at = 0
    if open_at:
        problems.append((open_at, f"`<details>` opened at line {open_at} is never closed"))
    return out, problems


@check("D5", "Intake template shape")
def d5_intake_shape(ctx: Context) -> CheckResult:
    """Every intake question asks one thing and takes one answer (R2.1).

    Per `###` question in `0_INTAKE_TEMPLATE.md`: an id like `12` or `12a`, unique;
    exactly one `**Answer:**` line; a `*Default…*` line or a LOAD-BEARING mark (R2.2 —
    without one, a blank leaves Stage 0 nothing to apply); at most one tick-box list,
    since two lists mean two questions bundled under one heading; and each list
    labelled `*Tick …:*` so the reader knows whether one or several ticks are allowed.

    `<details>` blocks are skipped: they hold guidance, not question content. Only
    the harness template is checked — a project's filled `INTAKE.md` may append
    questions with no default, which Stage 0 raises as `OPEN QUESTION:` instead.
    """
    res = CheckResult()
    doc = ctx.iset.by_name(INTAKE_TEMPLATE)
    if doc is None:
        res.skipped = f"{INTAKE_TEMPLATE} not in the set"
        return res

    folded, fold_problems = _details_lines(doc)
    for line, what in fold_problems:
        res.findings.append(
            Finding(
                check="D5",
                severity=Severity.MAJOR,
                summary="Intake template: unclosed `<details>` fold",
                detail=f"{what}. The questions after it, up to the next `<details>`, are treated "
                       "as folded guidance and go unchecked. Close each fold with `</details>` "
                       "on its own line.",
                file=doc.repo_relative,
                line=line,
                subject=f"intake:details:{line}",
                evidence=[doc.lines[line - 1]],
            )
        )

    heads = [h for h in doc.headings if not h.in_fence and h.line not in folded]
    questions = [h for h in heads if h.level == 3]
    if not questions:
        res.skipped = f"no ### questions in {INTAKE_TEMPLATE}"
        return res

    seen: dict[str, int] = {}

    for h in questions:
        label = h.text.split(".", 1)[0].strip()

        def flag(kind: str, summary: str, detail: str) -> None:
            res.findings.append(
                Finding(
                    check="D5",
                    severity=Severity.MAJOR,
                    summary=f"Intake Q{label}: {summary}",
                    detail=detail,
                    file=doc.repo_relative,
                    line=h.line,
                    subject=f"intake:{kind}:{label}",
                    evidence=[f"### {h.text}"],
                )
            )

        nxt = next((o.line for o in heads if o.line > h.line and o.level <= 3), len(doc.lines) + 1)
        body = [doc.lines[n - 1] for n in range(h.line + 1, nxt)
                if not doc.is_fenced(n) and n not in folded]

        m = INTAKE_QID_RE.match(h.text.strip())
        if not m:
            flag("id", "heading has no `<n>.` or `<n><letter>.` id",
                 "Stage 0 and every stage cite intake questions by id (Q12, Q12a); a heading "
                 "without one cannot be cited or recorded in PROJECT_CONTEXT §5.")
        else:
            qid = m.group("qid")
            if qid in seen:
                flag("dup", "id is used twice",
                     f"Also used at line {seen[qid]}. Ids must be unique so §5 has one row each.")
            seen.setdefault(qid, h.line)

        answers = sum(1 for ln in body if ln.lstrip().startswith("**Answer:**"))
        if answers != 1:
            flag("answer", f"has {answers} `**Answer:**` lines, not 1",
                 "R2.1: each question takes exactly one answer. Zero leaves nowhere to write "
                 "it; more than one means several questions are bundled under one heading — "
                 "split them into lettered parts.")

        if "LOAD-BEARING" not in h.text and not any(ln.lstrip().startswith("*Default") for ln in body):
            flag("default", "has neither a default nor a LOAD-BEARING mark",
                 "R2.2: a blank answer must either take a stated default or hard-stop. Add a "
                 "`*Default: …*` line, or mark the heading ⚠️ LOAD-BEARING.")

        # A list is a run of tick lines; blank lines don't end it, nor does an indented
        # line directly continuing a wrapped item. Its label is the last non-blank line
        # before it.
        lists, labelled, in_list, prev, gap = 0, True, False, "", False
        for ln in body:
            if not ln.strip():
                gap = True
                continue
            tick = bool(TICK_RE.match(ln))
            if in_list and not tick and not gap and ln[:1] in (" ", "\t"):
                continue
            if tick and not in_list:
                lists += 1
                labelled = labelled and prev.lstrip().startswith("*Tick")
            in_list, prev, gap = tick, ln, False
        if lists > 1:
            flag("lists", f"has {lists} tick-box lists",
                 "Two lists under one heading are two questions bundled together (R2.1). "
                 "Split them into lettered parts.")
        if lists and not labelled:
            flag("label", "tick-box list has no `*Tick …:*` label",
                 "Without a label such as *Tick one:* or *Tick all that apply:*, the reader "
                 "cannot tell whether one or several ticks are allowed.")

    res.metrics.append(Metric(check="D5", name="intake_questions", value=len(questions),
                              unit="questions", context={"file": doc.repo_relative}))
    return res


# --------------------------------------------------------------------------
# Judge-backed check — stub (design §11 Phase 4).
# --------------------------------------------------------------------------

@check("D2", "Near-duplicate rules, diverged", deterministic=False, implemented=False)
def d2_divergence(ctx: Context) -> CheckResult:
    return CheckResult(
        skipped=(
            "not implemented — needs rule extraction + judge harness (design Phase 3/4). "
            "Will shingle-match restated rules, then report ONLY those whose wordings have "
            "diverged; identical restatement is deliberate in these sets and must not fire."
        )
    )
