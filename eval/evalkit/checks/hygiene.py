"""Group F — Hygiene.

F2/F3 are deterministic. F1 (actor referent ambiguity) needs the judge harness
and is registered as a stub.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..model import CheckResult, Finding, Severity
from ..registry import Context, check
from .references import RUNTIME_ARTIFACTS, RUNTIME_ARTIFACT_PATTERNS

PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|XXX|HACK|WIP)\b(?![-\w])")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
# .md filenames appearing inside fenced examples (B2 deliberately skips fences).
FENCED_MD_RE = re.compile(r"(?P<name>[A-Za-z0-9_<>.-]+\.md)")


# Paths inside example commands that point back into the repo. Built per-run from
# the set's own directory name so a renamed set does not silently stop being checked.
def _set_path_re(set_name: str) -> re.Pattern[str]:
    return re.compile(rf"(?P<path>(?:\./)?{re.escape(set_name)}/[A-Za-z0-9_./<>-]+)")


@check("F2", "Unresolved placeholders")
def f2_placeholders(ctx: Context) -> CheckResult:
    res = CheckResult()
    for doc in ctx.iset.documents:
        for line_no, raw in enumerate(doc.lines, start=1):
            # Blank out inline code spans first. An instruction that tells the
            # agent to *emit* a marker — "mark the AD wiring as `TODO (AD)`" —
            # is the opposite of an unresolved placeholder, and reporting it
            # inverts the check's meaning.
            scanned = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), raw)
            for m in PLACEHOLDER_RE.finditer(scanned):
                res.findings.append(
                    Finding(
                        check="F2",
                        severity=Severity.MAJOR,
                        summary=f"Unresolved `{m.group(1)}` marker",
                        detail=(
                            "An instruction set is a contract that agents execute literally; "
                            "a placeholder left in prose becomes an instruction to improvise."
                        ),
                        file=doc.repo_relative,
                        line=line_no,
                        subject=f"placeholder:{doc.repo_relative}:{line_no}",
                        evidence=[raw.strip()],
                    )
                )
    return res


@check("F3", "Worked-example validity")
def f3_examples(ctx: Context) -> CheckResult:
    """Example commands and prompts reference files that actually exist.

    Complements B2, which skips fenced content. The worked examples are the part
    users copy verbatim, so a stale path there fails on first contact.
    """
    res = CheckResult()
    in_set = {d.name for d in ctx.iset.documents}
    supplied = {d.name for d in ctx.docs}

    def md_known(name: str) -> bool:
        if name in in_set or name in supplied or name in RUNTIME_ARTIFACTS:
            return True
        if any(p.match(name) for p in RUNTIME_ARTIFACT_PATTERNS):
            return True
        if "<" in name and ">" in name:
            return any(p.match(re.sub(r"<[^>]*>", "X", name)) for p in RUNTIME_ARTIFACT_PATTERNS)
        return False

    set_path_re = _set_path_re(ctx.iset.name)

    seen: set[str] = set()
    for doc in ctx.iset.documents:
        for line_no, raw in enumerate(doc.lines, start=1):
            in_fence = doc.is_fenced(line_no)
            is_quote = raw.lstrip().startswith(">")
            if not (in_fence or is_quote):
                continue

            # Repo-relative paths into an instruction set directory.
            for m in set_path_re.finditer(raw):
                rel = m.group("path").lstrip("./")
                if "<" in rel:
                    continue
                key = f"path:{rel}"
                if key in seen:
                    continue
                if not (ctx.repo_root / rel).exists():
                    seen.add(key)
                    res.findings.append(
                        Finding(
                            check="F3",
                            severity=Severity.BLOCKER,
                            summary=f"Example references `{rel}`, which does not exist",
                            detail=(
                                "Worked examples are copied verbatim by users; a stale path "
                                "here fails on first contact."
                            ),
                            file=doc.repo_relative,
                            line=line_no,
                            subject=key,
                            evidence=[raw.strip()],
                        )
                    )

            # Bare .md filenames inside examples.
            for m in FENCED_MD_RE.finditer(raw):
                name = m.group("name")
                key = f"md:{doc.repo_relative}:{name}"
                if key in seen or md_known(name):
                    continue
                seen.add(key)
                res.findings.append(
                    Finding(
                        check="F3",
                        severity=Severity.MAJOR,
                        summary=f"Example references `{name}`, which does not exist",
                        detail=(
                            "Not in the instruction set, not a known generated artifact, and "
                            "not supplied via --docs."
                        ),
                        file=doc.repo_relative,
                        line=line_no,
                        subject=key,
                        evidence=[raw.strip()],
                    )
                )
    return res


# --------------------------------------------------------------------------
# Judge-backed check — stub (design §11 Phase 4).
# --------------------------------------------------------------------------

@check("F1", "Actor referent ambiguity", deterministic=False, implemented=False)
def f1_actor(ctx: Context) -> CheckResult:
    return CheckResult(
        skipped=(
            "not implemented — needs the judge harness (design Phase 4). Will audit where "
            "'you' means the developer vs the agent, and where quoted text leaks the wrong "
            "referent across files."
        )
    )
