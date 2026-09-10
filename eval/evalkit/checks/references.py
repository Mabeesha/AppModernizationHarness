"""Group B — Referential Integrity.

Fully deterministic, no API cost, and every hit is an unambiguous defect. A
dangling reference is a rule that silently never fires — precisely the failure
mode the constraint-obligation design exists to prevent.

The central idea: instruction sets *declare* the shape of the artifacts they
generate inside fenced ```markdown blocks, and then *reference* those artifacts'
sections by number (`PROJECT_CONTEXT.md §4`). This module builds the declaration
registry from the fences, then resolves every reference against it.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from ..model import CheckResult, Document, Finding, Severity
from ..parser import iter_file_refs, iter_ids, iter_section_refs, iter_state_paths
from ..registry import Context, check

# First heading inside an artifact-template fence -> canonical artifact key.
ARTIFACT_TITLES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^#\s*Project Context\b", re.I), "PROJECT_CONTEXT.md"),
    (re.compile(r"^#\s*Phased Implementation Plan\b", re.I), "PLAN.md"),
    (re.compile(r"^#\s*Business Requirements\b", re.I), "BUSINESS_REQUIREMENTS.md"),
    (re.compile(r"^#\s*Functional Requirements\b", re.I), "FUNCTIONAL_REQUIREMENTS.md"),
    (re.compile(r"^#\s*Technical Requirements\b", re.I), "TECHNICAL_REQUIREMENTS.md"),
    (re.compile(r"^#\s*High[- ]Level Design\b", re.I), "HIGH_LEVEL_DESIGN.md"),
    (re.compile(r"^#\s*Low[- ]Level Design\b", re.I), "LOW_LEVEL_DESIGN.md"),
    (re.compile(r"^#\s*Review:", re.I), "REVIEW.md"),
]

# Words in a reference that hint at which artifact a bare `§N` belongs to.
FILE_HINT_ALIASES: dict[str, str] = {
    "project_context": "PROJECT_CONTEXT.md",
    "project_context.md": "PROJECT_CONTEXT.md",
    "plan": "PLAN.md",
    "business": "BUSINESS_REQUIREMENTS.md",
    "functional": "FUNCTIONAL_REQUIREMENTS.md",
    "technical": "TECHNICAL_REQUIREMENTS.md",
}

# Generated at runtime by the pipeline, so they legitimately do not exist in the set.
RUNTIME_ARTIFACTS = {
    "AGENTS.md",
    "HOW_TO_TEST.md",
    "INTAKE.md",
    "PROJECT_CONTEXT.md",
    "README.md",
}
RUNTIME_ARTIFACT_PATTERNS = [
    re.compile(r"^PLAN_.*\.md$"),
    re.compile(r"^(BUSINESS|FUNCTIONAL|TECHNICAL)_REQUIREMENTS_.*\.md$"),
    re.compile(r"^(HIGH|LOW)_LEVEL_DESIGN_.*\.md$"),
    re.compile(r"^REVIEW_.*\.md$"),
]


def _artifact_sections(iset) -> dict[str, dict[str, tuple[str, str, int]]]:
    """artifact key -> {section number: (title, declaring file, line)}."""
    registry: dict[str, dict[str, tuple[str, str, int]]] = defaultdict(dict)
    for doc in iset.documents:
        for fence in doc.fences:
            first = next((l for l in fence.content.splitlines() if l.strip()), "")
            key = next((k for pat, k in ARTIFACT_TITLES if pat.match(first.strip())), None)
            if not key:
                continue
            for h in doc.headings:
                if not h.in_fence:
                    continue
                if not (fence.start_line <= h.line <= fence.end_line):
                    continue
                num = h.section_number
                if num:
                    registry[key].setdefault(num, (h.text, doc.repo_relative, h.line))
    return registry


# How far back of a `§N` a bare prose word may sit and still count as its file
# hint. Without a bound, "…stated in business terms (see §0)" resolves to
# BUSINESS_REQUIREMENTS.md and reports a blocker that does not exist.
HINT_LOOKBACK_CHARS = 30


def _resolve_hint(raw_line: str, explicit: str | None, col: int | None = None) -> str | None:
    if explicit:
        norm = explicit.strip().lower()
        if norm in FILE_HINT_ALIASES:
            return FILE_HINT_ALIASES[norm]
        if norm.endswith(".md"):
            return explicit.strip()
        return None

    window = raw_line.lower()
    if col is not None:
        window = window[max(0, col - HINT_LOOKBACK_CHARS): col]
    best: tuple[int, str] | None = None
    for word, key in FILE_HINT_ALIASES.items():
        pos = window.rfind(word)
        if pos >= 0 and (best is None or pos > best[0]):
            best = (pos, key)
    return best[1] if best else None


@check("B1", "Section anchors resolve")
def b1_section_anchors(ctx: Context) -> CheckResult:
    """Every `§N` reference resolves to a section the target artifact declares.

    Conservative by design. An explicit reference (`PROJECT_CONTEXT.md §7`) that
    does not resolve is a blocker. A bare `§N` with no file hint is only reported
    when the number resolves in *no* known artifact — otherwise the ambiguity is
    the checker's, not the document's, and a false positive here would train
    people to ignore the whole group.
    """
    res = CheckResult()
    registry = _artifact_sections(ctx.iset)
    if not registry:
        res.skipped = "no artifact templates found (no fenced ```markdown blocks)"
        return res

    all_numbers = {n for sections in registry.values() for n in sections}

    for doc in ctx.iset.documents:
        # Sections the document declares as its own live headings. A set may
        # declare `## §0 — Project-Wide Constraints` this way: a real section,
        # written in prose rather than inside an artifact template fence. Without
        # this, every self-reference to it reads as dangling.
        own = {
            h.section_number
            for h in doc.headings
            if not h.in_fence and h.section_number is not None
        }

        for line, explicit, num, col in iter_section_refs(doc):
            raw = doc.line_text(line)
            target = _resolve_hint(raw, explicit, col)

            if target and target in registry:
                if num not in registry[target]:
                    declared = ", ".join(sorted(registry[target], key=int)) or "none"
                    res.findings.append(
                        Finding(
                            check="B1",
                            severity=Severity.BLOCKER,
                            summary=f"Reference to {target} §{num} does not resolve",
                            detail=(
                                f"{target} declares sections {declared}. A reference to a "
                                f"section that does not exist is an instruction that can "
                                f"never be followed."
                            ),
                            file=doc.repo_relative,
                            line=line,
                            subject=f"{target}#{num}",
                            evidence=[raw.strip()],
                        )
                    )
            elif not target and num not in all_numbers and num not in own:
                res.findings.append(
                    Finding(
                        check="B1",
                        severity=Severity.MAJOR,
                        summary=f"Bare §{num} reference resolves to no known artifact",
                        detail=(
                            "No file hint on the reference, and no artifact template in the "
                            f"set declares a section {num}."
                        ),
                        file=doc.repo_relative,
                        line=line,
                        subject=f"?#{num}",
                        evidence=[raw.strip()],
                    )
                )
    return res


@check("B2", "File references resolve")
def b2_file_refs(ctx: Context) -> CheckResult:
    """Every `*.md` mentioned is either in the set, a known runtime artifact, or supplied via --docs."""
    res = CheckResult()
    in_set = {d.name for d in ctx.iset.documents}
    supplied = {d.name for d in ctx.docs}

    def known(name: str) -> bool:
        if name in in_set or name in supplied or name in RUNTIME_ARTIFACTS:
            return True
        if any(p.match(name) for p in RUNTIME_ARTIFACT_PATTERNS):
            return True
        # Template placeholders, e.g. PLAN_<AppName>.md, REVIEW_<Rid>_<App>_<target>.md
        if "<" in name and ">" in name:
            stem = name.split("_", 1)[0].split("<", 1)[0]
            return any(
                n.startswith(stem) for n in (in_set | RUNTIME_ARTIFACTS)
            ) or any(p.match(re.sub(r"<[^>]*>", "X", name)) for p in RUNTIME_ARTIFACT_PATTERNS)
        return False

    seen: set[tuple[str, str]] = set()
    for doc in ctx.iset.documents:
        for line, name in iter_file_refs(doc):
            if known(name) or (doc.repo_relative, name) in seen:
                continue
            seen.add((doc.repo_relative, name))
            res.findings.append(
                Finding(
                    check="B2",
                    severity=Severity.BLOCKER,
                    summary=f"Reference to `{name}` which does not exist",
                    detail=(
                        "Not present in the instruction set, not a known generated artifact, "
                        "and not supplied via --docs. Most often a rename that missed a "
                        "cross-reference."
                    ),
                    file=doc.repo_relative,
                    line=line,
                    subject=name,
                    evidence=[doc.line_text(line).strip()],
                )
            )
    return res


def _flatten(obj, prefix: str = "") -> set[str]:
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            out.add(path)
            out |= _flatten(v, path)
    elif isinstance(obj, list):
        out.add(f"{prefix}[]")
        for item in obj:
            out |= _flatten(item, f"{prefix}[]")
    return out


def _state_schema_paths(ctx: Context) -> tuple[set[str], str | None]:
    """Derive the valid `state.json` path set from the set's own JSON template.

    Deriving beats hand-maintaining here: the check then verifies the set against
    its *own* declaration, so a file referencing a field the schema block never
    declares is caught without a second source of truth to keep in sync.
    """
    paths: set[str] = set()
    source: str | None = None

    for doc in ctx.iset.documents:
        for fence in doc.fences:
            if fence.lang != "json":
                continue
            try:
                data = json.loads(fence.content)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict) or "schemaVersion" not in data:
                continue
            paths |= _flatten(data)
            source = doc.repo_relative

        # Array-element fields are documented in prose as inline JSON snippets
        # (`{ "id": "P-1", "status": ... }`), not in the main template.
        for m in re.finditer(r"\{\s*\"id\"\s*:.*?\}", doc.text, re.S):
            snippet = m.group(0)
            keys = re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:', snippet)
            for array in ("phases", "edits", "changeLog", "reviews"):
                if f'"{array}"' in doc.text:
                    for k in keys:
                        paths.add(f"{array}[].{k}")

    return paths, source


@check("B3", "state.json field paths consistent")
def b3_state_paths(ctx: Context) -> CheckResult:
    res = CheckResult()
    schema, source = _state_schema_paths(ctx)
    if not schema:
        res.skipped = "no state.json schema block found in the set"
        return res

    # `phases[].status` and `phases[]` are both legitimate reference forms.
    schema |= {p.split("[]")[0] + "[]" for p in schema if "[]" in p}

    seen: set[tuple[str, str]] = set()
    for doc in ctx.iset.documents:
        for line, path in iter_state_paths(doc):
            if path in schema or (doc.repo_relative, path) in seen:
                continue
            # Tolerate a trailing element-field on a known array without a
            # documented snippet, and singular/plural container forms.
            base = path.split(".", 1)[0]
            if base in {"phases", "edits", "changeLog", "reviews"} and path.endswith("[]"):
                continue
            seen.add((doc.repo_relative, path))
            res.findings.append(
                Finding(
                    check="B3",
                    severity=Severity.BLOCKER,
                    summary=f"`{path}` is not declared in the state.json schema",
                    detail=(
                        f"The schema block in {source} does not declare this path. Either the "
                        "reference is misspelled or the schema is missing a field that stages "
                        "depend on — both break high-water-mark reconciliation."
                    ),
                    file=doc.repo_relative,
                    line=line,
                    subject=path,
                    evidence=[doc.line_text(line).strip()],
                )
            )
    return res


@check("B4", "ID format consistency")
def b4_id_format(ctx: Context) -> CheckResult:
    """Per-prefix dominant form. The harness uses `C1` (no dash) but `P-1`/`E-1`/`R-1` (dashed),
    so the convention is established per prefix rather than globally."""
    res = CheckResult()
    forms: dict[str, Counter] = defaultdict(Counter)
    sites: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)

    for doc in ctx.iset.documents:
        for line, ident in iter_ids(doc):
            prefix = ident[0].upper()
            dashed = "-" in ident
            forms[prefix][dashed] += 1
            sites[(prefix, "dashed" if dashed else "plain")].append((doc.repo_relative, line))

    for prefix, counter in forms.items():
        if len(counter) < 2:
            continue
        dominant, dom_n = counter.most_common(1)[0]
        minority_n = sum(v for k, v in counter.items() if k != dominant)
        # A handful of stragglers against an established majority is the signal.
        if minority_n == 0 or minority_n > dom_n:
            continue
        minority_form = "dashed" if not dominant else "plain"
        examples = sites[(prefix, minority_form)][:5]
        res.findings.append(
            Finding(
                check="B4",
                severity=Severity.MAJOR,
                summary=f"Inconsistent `{prefix}` id format ({minority_n} of {dom_n + minority_n} deviate)",
                detail=(
                    f"Dominant form is {'dashed' if dominant else 'plain'} "
                    f"(e.g. {prefix}-1 vs {prefix}1). IDs are how stages cross-reference "
                    "constraints and phases; a split convention breaks lookup."
                ),
                file=examples[0][0] if examples else ctx.iset.name,
                line=examples[0][1] if examples else 0,
                subject=f"id-format-{prefix}",
                evidence=[f"{f}:{l}" for f, l in examples],
            )
        )
    return res


@check("B5", "Orphan artifact sections")
def b5_orphans(ctx: Context) -> CheckResult:
    """Declared artifact sections that nothing ever references by number.

    Scoped to artifacts where section numbering is actually load-bearing — i.e.
    those some file references by `§N` at least once. Requirements, design, and
    plan documents are read whole rather than by section, so reporting every one
    of their sections as an orphan is noise, not signal. In the harness that leaves
    PROJECT_CONTEXT.md, where §-referencing *is* the mechanism.

    Still the weakest check in the group — a section can legitimately exist as
    human reference with no machine reader — so MINOR and a prune candidate.
    """
    res = CheckResult()
    registry = _artifact_sections(ctx.iset)
    if not registry:
        res.skipped = "no artifact templates found"
        return res

    referenced: set[tuple[str, str]] = set()
    bare: set[str] = set()
    for doc in ctx.iset.documents:
        for line, explicit, num, col in iter_section_refs(doc):
            target = _resolve_hint(doc.line_text(line), explicit, col)
            if target:
                referenced.add((target, num))
            else:
                bare.add(num)

    # Require section addressing to be an *established convention* for the
    # artifact, not an incidental one-off. One stray "§7 of the Technical
    # requirements" does not make every unreferenced section of that document a
    # finding; three or more distinct cited sections does mean the numbering is
    # load-bearing and a gap in it is worth surfacing.
    cited_per_artifact: dict[str, set[str]] = defaultdict(set)
    for target, num in referenced:
        cited_per_artifact[target].add(num)
    section_addressed = {a for a, nums in cited_per_artifact.items() if len(nums) >= 3}

    if not section_addressed:
        res.skipped = "no artifact is addressed by section number often enough to judge"
        return res

    for artifact, sections in registry.items():
        if artifact not in section_addressed:
            continue
        for num, (title, decl_file, decl_line) in sorted(sections.items(), key=lambda kv: int(kv[0])):
            if (artifact, num) in referenced or num in bare:
                continue
            res.findings.append(
                Finding(
                    check="B5",
                    severity=Severity.MINOR,
                    summary=f"{artifact} §{num} ({title}) is never referenced",
                    detail=(
                        "No stage file refers to this section by number. Either dead weight, "
                        "or a section whose obligation was never wired up to a consumer."
                    ),
                    file=decl_file,
                    line=decl_line,
                    subject=f"{artifact}#{num}",
                )
            )
    return res
