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

Run:  uv run tests/fault_injection.py [--set ../ModernizationHarness]
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

from evalkit.runner import run_tier1  # noqa: E402

Mutator = Callable[[Path], bool]


@dataclass
class Case:
    check: str
    description: str
    mutate: Mutator


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
    # The harness's convention is plain `C1`; introduce a dashed minority.
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
                "cp ModernizationHarness/AGENTS_TEMPLATE.md",
                "cp ModernizationHarness/AGENTS_TEMPLATE_MISSING.md")


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
]


def run_case(case: Case, source: Path, repo_root: Path) -> tuple[str, str]:
    """Returns (status, detail) where status is PASS | MUTATION FAILED | CHECK SILENT."""
    with tempfile.TemporaryDirectory() as tmp:
        work_repo = Path(tmp)
        work_set = work_repo / source.name
        shutil.copytree(source, work_set)

        if not case.mutate(work_set):
            return "MUTATION FAILED", "injected edit did not apply — repair the case"

        outcome = run_tier1(
            set_dir=work_set,
            repo_root=work_repo,
            selectors=[case.check],
            det_only=True,
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
                    default=HERE.parent.parent / "ModernizationHarness")
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
    outcome = run_tier1(set_dir=source, repo_root=repo_root, det_only=True, cache_dir=None)
    blockers = [f for f in outcome.findings if f.severity.value == "blocker"]
    print(f"         -> {len(outcome.findings)} finding(s), {len(blockers)} blocker(s)")

    print()
    if failures:
        print(f"{failures} of {len(CASES)} cases did not pass.")
        return 1
    print(f"All {len(CASES)} deterministic checks fire on an injected defect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
