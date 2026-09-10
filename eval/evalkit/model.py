"""Core data types shared by every check.

Kept dependency-free (stdlib dataclasses, not pydantic) so the deterministic
surface runs with no third-party imports beyond the token backend.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class Severity(str, Enum):
    BLOCKER = "blocker"
    MAJOR = "major"
    MINOR = "minor"

    @property
    def rank(self) -> int:
        return {"blocker": 0, "major": 1, "minor": 2}[self.value]


@dataclass(frozen=True)
class Heading:
    """A Markdown heading, whether in live prose or inside a fenced template block."""

    level: int
    text: str
    line: int
    # True when the heading lives inside a ``` fence. Those fences are how the harness
    # *defines* the shape of generated artifacts (PROJECT_CONTEXT.md, PLAN_<App>.md),
    # so they are the declaration site for sections other files then reference.
    in_fence: bool = False
    fence_lang: str | None = None

    @property
    def section_number(self) -> str | None:
        """Extract a section number from a heading, or None.

        Handles both conventions seen across the sets:
          '## 4. Constraints (non-negotiable)'      -> '4'
          '## §0 — Project-Wide Constraints'        -> '0'
        """
        stripped = self.text.strip()
        if stripped.startswith("§"):
            rest = stripped[1:].lstrip()
            digits = ""
            for ch in rest:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            return digits or None
        head = stripped.split(".", 1)[0].strip()
        return head if head.isdigit() else None


@dataclass(frozen=True)
class FencedBlock:
    lang: str | None
    content: str
    start_line: int
    end_line: int


@dataclass
class Document:
    """One parsed Markdown file from an instruction set."""

    path: Path
    repo_relative: str
    text: str
    lines: list[str]
    headings: list[Heading]
    fences: list[FencedBlock]
    # Lines that are inside a fenced code block (1-indexed). Checks that look for
    # prose patterns use this to avoid firing on example/template content.
    fenced_lines: set[int] = field(default_factory=set)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def stage(self) -> str | None:
        """'4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md' -> 'stage-4'. None if not a stage file."""
        head = self.path.name.split("_", 1)[0]
        return f"stage-{head}" if head.isdigit() else None

    def line_text(self, line: int) -> str:
        return self.lines[line - 1] if 1 <= line <= len(self.lines) else ""

    def is_fenced(self, line: int) -> bool:
        return line in self.fenced_lines

    def section_at(self, line: int) -> str:
        """Nearest enclosing non-fenced heading above `line`."""
        best = ""
        for h in self.headings:
            if h.in_fence:
                continue
            if h.line <= line:
                best = h.text
            else:
                break
        return best

    def has_heading(self, *candidates: str) -> bool:
        wanted = {c.lower() for c in candidates}
        return any(h.text.strip().lower() in wanted for h in self.headings if not h.in_fence)


@dataclass
class InstructionSet:
    """A folder of instruction documents, e.g. ModernizationHarness/."""

    root: Path
    name: str
    documents: list[Document]

    def by_name(self, name: str) -> Document | None:
        for d in self.documents:
            if d.name == name:
                return d
        return None

    def stage_documents(self) -> dict[str, Document]:
        """Stage id -> document, for files named with a leading stage number."""
        out: dict[str, Document] = {}
        for d in self.documents:
            if d.stage:
                out[d.stage] = d
        return out


@dataclass
class Finding:
    check: str
    severity: Severity
    summary: str
    detail: str
    file: str
    line: int = 0
    subject: str = ""
    evidence: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        """Stable across runs and line-number drift: keyed on check + file + subject."""
        basis = f"{self.check}|{self.file}|{self.subject or self.summary}"
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:10]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["id"] = self.id
        return d


@dataclass
class Metric:
    """A reported measurement. Data, not a defect — never gates CI."""

    check: str
    name: str
    value: Any
    unit: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CheckResult:
    findings: list[Finding] = field(default_factory=list)
    metrics: list[Metric] = field(default_factory=list)
    # Set when a check could not run (missing input, needs --with-llm, etc.).
    skipped: str | None = None

    def extend(self, other: "CheckResult") -> None:
        self.findings.extend(other.findings)
        self.metrics.extend(other.metrics)


def worst(findings: Iterable[Finding]) -> Severity | None:
    ordered = sorted(findings, key=lambda f: f.severity.rank)
    return ordered[0].severity if ordered else None
