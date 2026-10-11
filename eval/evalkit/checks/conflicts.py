"""Group E — Conflict Detection.

E4 is deterministic and ships now. E1/E2 (the group's reason for existing) and
E3 need rule extraction plus the judge harness; they are registered as stubs so
the CLI reports them as not-yet-implemented rather than silently omitting them.

Clustering note for when E1/E2 land: naive pairwise comparison over the extracted
rules is tens of thousands of judge calls. Bucket by `subject`, then compare only
pairs whose `actor` sets intersect, and skip pairs with identical modality AND
predicate (that is D2's job). For the harness this lands in the low hundreds.
"""

from __future__ import annotations

import re

from ..model import CheckResult, Finding, Severity
from ..registry import Context, check

# Obligation key -> the stage that must honour it.
OBLIGATION_STAGES: dict[str, str] = {
    "requirements": "stage-1",
    "design": "stage-2",
    "plan": "stage-3",
    "implement": "stage-4",
    "review": "stage-5",
}

# Stage 0 authors the obligations, so it is never itself an obligation target.
OBLIGATION_AUTHOR_STAGE = "stage-0"

PROSE_OBLIGATION_RE = re.compile(
    r"\*(?P<key>Requirements|Design|Plan|Implement|Review)\s*:\*", re.I
)


# The `## 4. Constraints` heading inside the PROJECT_CONTEXT template fence.
TEMPLATE_CONSTRAINTS_RE = re.compile(r"^##\s+4\.\s+Constraints\b")
TEMPLATE_SECTION_RE = re.compile(r"^##\s")


def _template_obligation_keys(ctx: Context) -> tuple[set[str], str | None]:
    """The obligation keys offered by the PROJECT_CONTEXT §4 template.

    Obligations are stored only in PROJECT_CONTEXT §4 (DD-20), so the template's
    `*Requirements:*`-style bullets are the vocabulary Stage 0 writes and every
    stage reads back.
    """
    for doc in ctx.iset.documents:
        for fence in doc.fences:
            keys: set[str] = set()
            inside = False
            for line in fence.content.splitlines():
                if TEMPLATE_CONSTRAINTS_RE.match(line):
                    inside = True
                    continue
                if inside and TEMPLATE_SECTION_RE.match(line):
                    break
                if inside:
                    keys.update(m.group("key").lower() for m in PROSE_OBLIGATION_RE.finditer(line))
            if keys:
                return keys, doc.repo_relative
    return set(), None


@check("E4", "Obligation vocabulary closure")
def e4_obligations(ctx: Context) -> CheckResult:
    """The obligation keys in the PROJECT_CONTEXT §4 template, the keys used in
    prose, and the stages that exist must all agree.

    A key with no stage means an obligation nothing executes. A stage with no key
    means constraints can never bind that stage — which, in a design where the
    obligations are the *single place* constraint rules live, is a silent hole.
    """
    res = CheckResult()

    schema_keys, schema_file = _template_obligation_keys(ctx)
    if not schema_keys:
        res.skipped = "no obligation bullets found in a PROJECT_CONTEXT §4 Constraints template"
        return res

    prose_keys: dict[str, tuple[str, int]] = {}
    for doc in ctx.iset.documents:
        for line_no, raw in enumerate(doc.lines, start=1):
            for m in PROSE_OBLIGATION_RE.finditer(raw):
                prose_keys.setdefault(m.group("key").lower(), (doc.repo_relative, line_no))

    stages = set(ctx.iset.stage_documents())

    # 1. Template key with no stage file to execute it.
    for key in sorted(schema_keys):
        stage = OBLIGATION_STAGES.get(key)
        if stage is None:
            res.findings.append(
                Finding(
                    check="E4",
                    severity=Severity.MAJOR,
                    summary=f"Obligation key `{key}` maps to no known stage",
                    detail=(
                        "The obligation vocabulary must map onto the pipeline's stages; an "
                        "unmapped key is an obligation no stage will ever read."
                    ),
                    file=schema_file or ctx.iset.name,
                    subject=f"obligation-key:{key}",
                )
            )
        elif stage not in stages:
            res.findings.append(
                Finding(
                    check="E4",
                    severity=Severity.BLOCKER,
                    summary=f"Obligation `{key}` targets {stage}, which has no instruction file",
                    detail=(
                        "Constraints can state an obligation for this stage, but no stage file "
                        "exists to honour it."
                    ),
                    file=schema_file or ctx.iset.name,
                    subject=f"obligation-stage:{key}",
                )
            )

    # 2. Prose key absent from the template.
    for key, (f, l) in sorted(prose_keys.items()):
        if key not in schema_keys:
            res.findings.append(
                Finding(
                    check="E4",
                    severity=Severity.MAJOR,
                    summary=f"Obligation `{key}` used in prose but absent from the §4 template",
                    detail=(
                        "Stage 0 writes obligations from the PROJECT_CONTEXT §4 template; a key "
                        "the template never offers is never written, so the stage it targets "
                        "has nothing to read."
                    ),
                    file=f,
                    line=l,
                    subject=f"obligation-prose:{key}",
                )
            )

    # 3. Stage that no obligation key can bind.
    bindable = {OBLIGATION_STAGES[k] for k in schema_keys if k in OBLIGATION_STAGES}
    for stage in sorted(stages):
        if stage == OBLIGATION_AUTHOR_STAGE or stage in bindable:
            continue
        doc = ctx.iset.stage_documents()[stage]
        res.findings.append(
            Finding(
                check="E4",
                severity=Severity.MAJOR,
                summary=f"{stage} cannot be bound by any constraint obligation",
                detail=(
                    "No obligation key maps to this stage, so a project constraint has no way "
                    "to change its behaviour — the mechanism the set relies on for "
                    "constraint-specific rules does not reach it."
                ),
                file=doc.repo_relative,
                subject=f"unbindable-stage:{stage}",
            )
        )

    return res


# --------------------------------------------------------------------------
# Judge-backed checks — stubs (design §11 Phase 4).
# --------------------------------------------------------------------------

@check("E1", "Direct contradiction", deterministic=False, implemented=False)
def e1_contradiction(ctx: Context) -> CheckResult:
    return CheckResult(
        skipped=(
            "not implemented — needs rule extraction + judge harness (design Phase 3/4). "
            "Compares rules within a subject cluster where actor sets intersect."
        )
    )


@check("E2", "Authority ambiguity", deterministic=False, implemented=False)
def e2_authority(ctx: Context) -> CheckResult:
    return CheckResult(
        skipped=(
            "not implemented — needs rule extraction + judge harness (design Phase 3/4). "
            "Finds two stages claiming write access to one artifact with no precedence rule."
        )
    )


@check("E3", "Unfalsifiable instruction", deterministic=False,
       experimental=True, implemented=False)
def e3_unfalsifiable(ctx: Context) -> CheckResult:
    return CheckResult(
        skipped=(
            "not implemented and experimental — needs the judge harness (design Phase 4). "
            "Off by default; enable with --include-experimental once implemented. Most likely "
            "of all checks to produce opinionated false positives."
        )
    )
