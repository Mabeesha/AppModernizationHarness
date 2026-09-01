"""Group C — Pipeline Coherence.

Treats the instruction set as a graph of stages producing and consuming
artifacts. C1/C3/C5 are deterministic; C2 and C4 need the judge harness and are
registered as stubs so the CLI reports them honestly rather than silently
omitting them.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ..model import CheckResult, Finding, Severity
from ..registry import Context, check
from .references import ARTIFACT_TITLES, RUNTIME_ARTIFACT_PATTERNS

# Artifacts that legitimately have no producing stage: authored by the human,
# copied from a template, or external to the pipeline.
EXOGENOUS = {
    "INTAKE.md",
    "AGENTS.md",
    "AGENTS_TEMPLATE.md",
    "0_INTAKE_TEMPLATE.md",
    "README.md",
    # A standing reference every stage reads and none produces — the writing standard,
    # not a pipeline artifact handed from one stage to the next.
    "DOCUMENT_STYLE.md",
}

# Canonical artifact key -> the reference forms that mean the same thing.
CANON: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^PROJECT_CONTEXT(\.md)?$", re.I), "PROJECT_CONTEXT.md"),
    (re.compile(r"^PLAN[_<].*\.md$|^PLAN\.md$", re.I), "PLAN.md"),
    (re.compile(r"^BUSINESS_REQUIREMENTS.*\.md$", re.I), "BUSINESS_REQUIREMENTS.md"),
    (re.compile(r"^FUNCTIONAL_REQUIREMENTS.*\.md$", re.I), "FUNCTIONAL_REQUIREMENTS.md"),
    (re.compile(r"^TECHNICAL_REQUIREMENTS.*\.md$", re.I), "TECHNICAL_REQUIREMENTS.md"),
    (re.compile(r"^HIGH_LEVEL_DESIGN.*\.md$", re.I), "HIGH_LEVEL_DESIGN.md"),
    (re.compile(r"^LOW_LEVEL_DESIGN.*\.md$", re.I), "LOW_LEVEL_DESIGN.md"),
    (re.compile(r"^REVIEW[_<].*\.md$", re.I), "REVIEW.md"),
    (re.compile(r"^state\.json$", re.I), "state.json"),
]

ARTIFACT_MENTION_RE = re.compile(
    r"`?(?P<name>(?:[A-Za-z0-9_<>.-]+\.md)|state\.json|PROJECT_CONTEXT)`?"
)


def canonical(name: str) -> str | None:
    """Map a reference form to a canonical artifact key.

    Falls back to a normalised key for *unrecognised* pipeline artifacts —
    without it, C1 can only see handoff breaks among artifact types it already
    knows about, which is precisely the case where a break is least likely.
    The SCREAMING_SNAKE shape keeps ordinary prose mentions (`README.md`) out.
    """
    for pat, key in CANON:
        if pat.match(name):
            return key

    stem = re.sub(r"\.md$", "", name, flags=re.I)
    stem = re.sub(r"_?<[^>]*>", "", stem)          # PLAN_<AppName> -> PLAN
    if not stem:
        return None
    if re.fullmatch(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*", stem):
        return f"{stem}.md"
    return None


def _section_lines(doc, *titles: str) -> list[tuple[int, str]]:
    """Lines belonging to the first heading whose text starts with any of `titles`."""
    wanted = tuple(t.lower() for t in titles)
    tops = [h for h in doc.headings if not h.in_fence]
    for i, h in enumerate(tops):
        if h.text.strip().lower().startswith(wanted):
            end = tops[i + 1].line if i + 1 < len(tops) else len(doc.lines) + 1
            return [(n, doc.lines[n - 1]) for n in range(h.line, end)]
    return []


def _declared_inputs(doc) -> set[str]:
    out: set[str] = set()
    for line_no, raw in _section_lines(doc, "inputs"):
        if doc.is_fenced(line_no):
            continue
        for m in ARTIFACT_MENTION_RE.finditer(raw):
            key = canonical(m.group("name"))
            if key:
                out.add(key)
    return out


def _declared_outputs(doc) -> set[str]:
    """Artifacts a stage produces: template fences it declares, plus explicit
    'Save as' / 'Output N —' / 'Produce' statements, plus state.json writes."""
    out: set[str] = set()

    for fence in doc.fences:
        first = next((l for l in fence.content.splitlines() if l.strip()), "")
        for pat, key in ARTIFACT_TITLES:
            if pat.match(first.strip()):
                out.add(key.replace("BUSINESS_REQUIREMENTS.md", "BUSINESS_REQUIREMENTS.md"))

    patterns = (
        re.compile(r"\bSave as\b(?P<rest>.*)", re.I),
        re.compile(r"\bOutput\s+\d+\s*[—:-](?P<rest>.*)", re.I),
        re.compile(r"\bProduces?\b(?P<rest>.*)", re.I),
        re.compile(r"\byou\s+(?:produce|initialize|write)\b(?P<rest>.*)", re.I),
    )
    for line_no, raw in enumerate(doc.lines, start=1):
        for pat in patterns:
            m = pat.search(raw)
            if not m:
                continue
            for am in ARTIFACT_MENTION_RE.finditer(m.group("rest")):
                key = canonical(am.group("name"))
                if key:
                    out.add(key)
    return out


def _stage_order(ctx: Context) -> list[tuple[str, object]]:
    stages = ctx.iset.stage_documents()
    return sorted(stages.items(), key=lambda kv: int(kv[0].split("-")[1]))


@check("C1", "Stage handoff closure")
def c1_handoff(ctx: Context) -> CheckResult:
    """Every artifact a stage declares as an input is produced by an earlier stage
    (or is exogenous — human-authored, templated, or external)."""
    res = CheckResult()
    ordered = _stage_order(ctx)
    if len(ordered) < 2:
        res.skipped = "fewer than two numbered stage files"
        return res

    produced_by: dict[str, str] = {}
    for stage, doc in ordered:
        for artifact in _declared_outputs(doc):
            produced_by.setdefault(artifact, stage)

    exogenous_keys = {canonical(n) or n for n in EXOGENOUS}

    for stage, doc in ordered:
        idx = int(stage.split("-")[1])
        for artifact in sorted(_declared_inputs(doc)):
            if artifact in exogenous_keys:
                continue
            origin = produced_by.get(artifact)
            if origin is None:
                res.findings.append(
                    Finding(
                        check="C1",
                        severity=Severity.MAJOR,
                        summary=f"{stage} consumes {artifact}, which no stage declares as an output",
                        detail=(
                            "Either a stage is missing an output declaration, or this input "
                            "arrives from outside the pipeline and should be documented as such."
                        ),
                        file=doc.repo_relative,
                        subject=f"{stage}<-{artifact}",
                    )
                )
                continue
            origin_idx = int(origin.split("-")[1])
            if origin_idx > idx:
                res.findings.append(
                    Finding(
                        check="C1",
                        severity=Severity.BLOCKER,
                        summary=f"{stage} consumes {artifact}, produced later by {origin}",
                        detail="A stage cannot read an artifact that a later stage creates.",
                        file=doc.repo_relative,
                        subject=f"{stage}<-{artifact}",
                    )
                )
    return res


@check("C3", "Artifact lifecycle")
def c3_lifecycle(ctx: Context) -> CheckResult:
    """Every pipeline artifact has exactly one creating stage."""
    res = CheckResult()
    ordered = _stage_order(ctx)
    if not ordered:
        res.skipped = "no numbered stage files"
        return res

    creators: dict[str, list[str]] = defaultdict(list)
    for stage, doc in ordered:
        for artifact in _declared_outputs(doc):
            creators[artifact].append(stage)

    for artifact, stages in sorted(creators.items()):
        # state.json is initialised once and appended to by every later stage —
        # multiple writers is the design, not a defect.
        if artifact == "state.json":
            continue
        if len(stages) > 1:
            res.findings.append(
                Finding(
                    check="C3",
                    severity=Severity.MAJOR,
                    summary=f"{artifact} is declared as an output by {len(stages)} stages",
                    detail=(
                        f"Declared by {', '.join(stages)}. Two creators means no single owner, "
                        "and the ownership table cannot be authoritative."
                    ),
                    file=ctx.iset.name,
                    subject=f"creators:{artifact}",
                    evidence=stages,
                )
            )
    return res


@check("C5", "Rerun path present")
def c5_rerun(ctx: Context) -> CheckResult:
    """Every stage exposes an Additional Instructions block; every stage that has a
    `state.json stages.*` entry also increments its `rerunCount`.

    The second half is deliberately conditional. Stages 4 and 5 have no entry in
    `state.json.stages` — they are loop stages, not one-shot document stages — so
    requiring a rerunCount from them would be a false positive.
    """
    res = CheckResult()
    ordered = _stage_order(ctx)
    if not ordered:
        res.skipped = "no numbered stage files"
        return res

    # Which stages the schema actually tracks a rerunCount for.
    tracked: set[str] = set()
    for doc in ctx.iset.documents:
        for m in re.finditer(r'"(?P<name>[a-z]+)"\s*:\s*\{\s*"status"[^}]*"rerunCount"', doc.text):
            tracked.add(m.group("name"))

    alias = {
        "stage-0": "context",
        "stage-1": "requirements",
        "stage-2": "design",
        "stage-3": "plan",
    }

    for stage, doc in ordered:
        if not doc.has_heading("Additional Instructions"):
            res.findings.append(
                Finding(
                    check="C5",
                    severity=Severity.MAJOR,
                    summary=f"{stage} has no Additional Instructions block",
                    detail="Every stage must accept run-specific overrides and rerun requests.",
                    file=doc.repo_relative,
                    subject=f"{stage}:additional-instructions",
                )
            )

        key = alias.get(stage)
        if key and key in tracked and "rerunCount" not in doc.text:
            res.findings.append(
                Finding(
                    check="C5",
                    severity=Severity.MAJOR,
                    summary=f"{stage} never increments `stages.{key}.rerunCount`",
                    detail=(
                        f"The state schema tracks a rerunCount for `{key}`, but this stage "
                        "file never mentions incrementing it, so reruns will be invisible "
                        "to downstream reconciliation."
                    ),
                    file=doc.repo_relative,
                    subject=f"{stage}:rerunCount",
                )
            )
    return res


# --------------------------------------------------------------------------
# Judge-backed checks — registered as stubs (design §11 Phase 4).
# --------------------------------------------------------------------------

@check("C2", "Ownership matrix drift", deterministic=False, implemented=False)
def c2_ownership(ctx: Context) -> CheckResult:
    return CheckResult(
        skipped=(
            "not implemented — needs the rule-extraction + judge harness (design Phase 3/4). "
            "Will derive a write-permission matrix from rule records and diff it against the "
            "README 'Who Writes What' table."
        )
    )


@check("C4", "Definition-of-Done coverage", deterministic=False, implemented=False)
def c4_dod(ctx: Context) -> CheckResult:
    return CheckResult(
        skipped=(
            "not implemented — needs the judge harness (design Phase 4). Will check both "
            "directions: DoD items with no backing instruction, and hard rules absent from the DoD."
        )
    )
