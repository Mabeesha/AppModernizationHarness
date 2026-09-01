#!/usr/bin/env python3
"""Fault injection: prove every deterministic check actually fires.

A check that silently never fires is worse than no check — it reads as a clean
bill of health. This copies a real instruction set, injects one defect per
check, and asserts that check reports it.

Each case reports two distinct failure modes so they are never confused:

  MUTATION FAILED - the injected edit did not apply (the source text moved),
                    so the case proves nothing and must be repaired.
  CHECK SILENT    - the edit applied but the check found nothing. That is a
                    real defect in the check.

Run:  uv run tests/fault_injection.py [--set ../AgentInstructionSet4]
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

# A tiny, fully EARS-conforming requirements document. The control pass asserts
# group G stays silent on it, so every G finding below is attributable to the
# injected defect rather than to the fixture's own prose.
DOCS_FIXTURE = HERE / "fixtures" / "docs"

from evalkit.runner import run_tier1  # noqa: E402

Mutator = Callable[[Path], bool]


@dataclass
class Case:
    check: str
    description: str
    mutate: Mutator
    # Group G's output checks grade generated documents, not the instruction set.
    # These cases mutate a copy of tests/fixtures/docs instead, and the check runs
    # with that directory passed as --docs.
    docs: bool = False


def _sub(path: Path, old: str, new: str, count: int = 1) -> bool:
    """Replace `old` with `new`. Returns False if `old` was not present."""
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if old not in text:
        return False
    path.write_text(text.replace(old, new, count), encoding="utf-8")
    return True


def _append(path: Path, text: str) -> bool:
    if not path.exists():
        return False
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")
    return True


# --------------------------------------------------------------------------
# One mutation per deterministic check.
# --------------------------------------------------------------------------

def m_b1(root: Path) -> bool:
    return _sub(root / "1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md",
                "`PROJECT_CONTEXT.md §4 (Constraints)`",
                "`PROJECT_CONTEXT.md §42 (Constraints)`")


def m_b2(root: Path) -> bool:
    return _sub(root / "README.md",
                "`4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md`",
                "`4_PHASE_IMPL_RENAMED.md`")


def m_b3(root: Path) -> bool:
    return _sub(root / "4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md",
                "`progress.lastProcessedChangeLogId`",
                "`progress.lastChangeLogId`")


def m_b4(root: Path) -> bool:
    # Set 4's convention is plain `C1`; introduce a dashed minority.
    return _append(root / "2_DESIGN_INSTRUCTIONS.md",
                   "\n\nHonor C-1 and C-2 exactly as stated.\n")


def m_b5(root: Path) -> bool:
    # An extra PROJECT_CONTEXT section nothing will ever reference by number.
    return _sub(root / "0_PROJECT_CONTEXT_INSTRUCTIONS.md",
                "## 10. Performance Baseline",
                "## 11. Orphaned Section For Testing\n- Nothing references this.\n\n"
                "## 10. Performance Baseline")


def m_c1(root: Path) -> bool:
    return _sub(root / "2_DESIGN_INSTRUCTIONS.md",
                "## Inputs",
                "## Inputs\n\n0. **`CAPACITY_MODEL_<AppName>.md`** — required input.\n")


def m_c3(root: Path) -> bool:
    # A second stage declaring the plan template = two creators.
    return _append(root / "5_REVIEW_INSTRUCTIONS.md",
                   "\n\n## Extra Output\n\n"
                   "```markdown\n# Phased Implementation Plan: <AppName>\n"
                   "## 1. Overview\n```\n")


def m_c5(root: Path) -> bool:
    return _sub(root / "2_DESIGN_INSTRUCTIONS.md",
                "## Additional Instructions",
                "## Extra Notes")


def m_d1(root: Path) -> bool:
    return _sub(root / "3_PLAN_INSTRUCTIONS.md",
                '`status: "pending"`',
                '`status: "in-progress"`')


def m_d3(root: Path) -> bool:
    # AGENTS_TEMPLATE is the smallest file, so density spikes hard.
    return _append(root / "AGENTS_TEMPLATE.md",
                   "\n\n" + "You MUST always do this and MUST NEVER do that. "
                   "You SHALL ALWAYS comply. DO NOT deviate. " * 12 + "\n")


def m_d4(root: Path) -> bool:
    return _append(root / "2_DESIGN_INSTRUCTIONS.md",
                   "\n\n```text\ngraph TD\n  A[Start] --> B[End]\n```\n")


def m_e4(root: Path) -> bool:
    # Drop the `review` obligation key -> stage-5 becomes unbindable.
    return _sub(root / "0_PROJECT_CONTEXT_INSTRUCTIONS.md",
                '"implement": "", "review": ""',
                '"implement": ""')


def m_f2(root: Path) -> bool:
    return _append(root / "3_PLAN_INSTRUCTIONS.md",
                   "\n\nTODO: decide whether phases can be parallelised.\n")


def m_f3(root: Path) -> bool:
    return _sub(root / "README.md",
                "cp AgentInstructionSet4/AGENTS_TEMPLATE.md",
                "cp AgentInstructionSet4/AGENTS_TEMPLATE_MISSING.md")


def m_g1(root: Path) -> bool:
    # Strip the pattern opener: the statement still reads fine to a human and
    # still says `shall`, which is exactly why a machine has to catch it.
    return _sub(root / "FUNCTIONAL_REQUIREMENTS_Fixture.md",
                "**FR-2.1** When the user submits a surname filter, Fixture shall return",
                "**FR-2.1** Fixture returns")


def m_g2(root: Path) -> bool:
    return _sub(root / "FUNCTIONAL_REQUIREMENTS_Fixture.md",
                "Fixture shall clear the password field",
                "Fixture should clear the password field")


def m_g3(root: Path) -> bool:
    return _append(root / "FUNCTIONAL_REQUIREMENTS_Fixture.md",
                   "\n## 4. Notes\n\nIt is important to note that the search screen was "
                   "designed in order to facilitate a seamless experience, and it should be "
                   "noted that the team chose to leverage the existing grid control rather "
                   "than utilize a new one, with respect to the timeline that was agreed at "
                   "the outset of the project by every party involved.\n")


def m_g4(root: Path) -> bool:
    return _sub(root / "FUNCTIONAL_REQUIREMENTS_Fixture.md",
                "  (`Program.cs:22`)",
                "")


def m_g5(root: Path) -> bool:
    # A document-producing stage that no longer loads the writing standard.
    path = root / "1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if "DOCUMENT_STYLE.md" not in text:
        return False
    path.write_text(text.replace("DOCUMENT_STYLE.md", "the house style"), encoding="utf-8")
    return True


CASES: list[Case] = [
    Case("B1", "§ reference to a section that does not exist", m_b1),
    Case("B2", "renamed instruction file leaves a dangling reference", m_b2),
    Case("B3", "state.json path not declared in the schema", m_b3),
    Case("B4", "dashed C-1 against the plain C1 convention", m_b4),
    Case("B5", "PROJECT_CONTEXT section nothing references", m_b5),
    Case("C1", "stage consumes an artifact no stage produces", m_c1),
    Case("C3", "two stages declare the same artifact as output", m_c3),
    Case("C5", "stage loses its Additional Instructions block", m_c5),
    Case("D1", "`in-progress` against the canonical `in progress`", m_d1),
    Case("D3", "modality density outlier", m_d3),
    Case("D4", "mermaid diagram in an untagged fence", m_d4),
    Case("E4", "obligation key removed, leaving a stage unbindable", m_e4),
    Case("F2", "TODO marker left in prose", m_f2),
    Case("F3", "worked example points at a missing file", m_f3),
    Case("G1", "requirement statement drops its EARS pattern", m_g1, docs=True),
    Case("G2", "`should` used where EARS requires `shall`", m_g2, docs=True),
    Case("G3", "filler-laden 45-word sentence added", m_g3, docs=True),
    Case("G4", "requirement statement loses its path:line citation", m_g4, docs=True),
    Case("G5", "a document-producing stage stops referencing the style standard", m_g5),
]


def run_case(case: Case, source: Path, repo_root: Path) -> tuple[str, str]:
    """Returns (status, detail) where status is PASS | MUTATION FAILED | CHECK SILENT."""
    with tempfile.TemporaryDirectory() as tmp:
        work_repo = Path(tmp)
        work_set = work_repo / source.name
        shutil.copytree(source, work_set)

        work_docs: Path | None = None
        if case.docs:
            if not DOCS_FIXTURE.is_dir():
                return "MUTATION FAILED", f"missing docs fixture at {DOCS_FIXTURE}"
            work_docs = work_repo / "docs"
            shutil.copytree(DOCS_FIXTURE, work_docs)

        target = work_docs if case.docs else work_set
        if not case.mutate(target):
            return "MUTATION FAILED", "injected edit did not apply — repair the case"

        outcome = run_tier1(
            set_dir=work_set,
            repo_root=work_repo,
            selectors=[case.check],
            det_only=True,
            docs_dir=work_docs,
            cache_dir=None,
        )
        hits = [f for f in outcome.findings if f.check == case.check]
        if hits:
            return "PASS", hits[0].summary
        skip = outcome.skipped.get(case.check)
        return "CHECK SILENT", f"skipped: {skip}" if skip else "no finding produced"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_dir", type=Path,
                    default=HERE.parent.parent / "AgentInstructionSet4")
    args = ap.parse_args(argv)

    source = args.set_dir.resolve()
    if not source.is_dir():
        print(f"error: {source} is not a directory", file=sys.stderr)
        return 2

    repo_root = source.parent
    print(f"Fault injection against {source.name}\n")

    failures = 0
    for case in CASES:
        status, detail = run_case(case, source, repo_root)
        mark = {"PASS": "ok  ", "MUTATION FAILED": "MUT!", "CHECK SILENT": "FAIL"}[status]
        print(f"  [{mark}] {case.check}  {case.description}")
        if status != "PASS":
            print(f"         -> {status}: {detail}")
            failures += 1
        else:
            print(f"         -> {detail}")

    # A control run: the unmodified set must NOT produce the injected findings.
    print("\n  control (unmodified set):")
    outcome = run_tier1(
        set_dir=source,
        repo_root=repo_root,
        det_only=True,
        docs_dir=DOCS_FIXTURE if DOCS_FIXTURE.is_dir() else None,
        cache_dir=None,
    )
    blockers = [f for f in outcome.findings if f.severity.value == "blocker"]
    print(f"         -> {len(outcome.findings)} finding(s), {len(blockers)} blocker(s)")

    # The docs fixture is written to conform, so any group G finding on it means a
    # check fires on clean input — the failure mode that makes a whole group noise.
    g_noise = [f for f in outcome.findings if f.check.startswith("G")]
    if g_noise:
        print(f"         -> FAIL: {len(g_noise)} group-G finding(s) on the conforming fixture:")
        for f in g_noise[:5]:
            print(f"            {f.check} {f.summary}")
        failures += 1

    print()
    if failures:
        print(f"{failures} of {len(CASES)} cases did not pass.")
        return 1
    print(f"All {len(CASES)} deterministic checks fire on an injected defect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
