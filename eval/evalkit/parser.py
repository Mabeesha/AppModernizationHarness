"""Markdown parsing for instruction documents.

The one non-obvious behaviour: fenced code blocks are parsed for headings too.
The harness *defines* the shape of its generated artifacts inside ```markdown fences —
`PROJECT_CONTEXT.md`'s ten sections and `PLAN_<App>.md`'s five are declared that
way. Those fences are therefore the declaration site for sections that other
files reference as `§4`, so a reference checker that ignored fences would report
every one of them as dangling.
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import Document, FencedBlock, Heading, InstructionSet

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([A-Za-z0-9_+-]*)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")


def parse_document(path: Path, repo_root: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    headings: list[Heading] = []
    fences: list[FencedBlock] = []
    fenced_lines: set[int] = set()

    open_fence: tuple[str, str | None, int, list[str]] | None = None

    for idx, raw in enumerate(lines, start=1):
        fence_match = FENCE_RE.match(raw)

        if open_fence is None:
            if fence_match:
                marker = fence_match.group(2)
                lang = fence_match.group(3) or None
                open_fence = (marker, lang, idx, [])
                fenced_lines.add(idx)
                continue
        else:
            marker, lang, start, body = open_fence
            fenced_lines.add(idx)
            # A closing fence uses the same character and is at least as long,
            # and carries no language tag.
            if fence_match and fence_match.group(2)[0] == marker[0] \
                    and len(fence_match.group(2)) >= len(marker) \
                    and not fence_match.group(3):
                fences.append(
                    FencedBlock(lang=lang, content="\n".join(body), start_line=start, end_line=idx)
                )
                open_fence = None
                continue
            body.append(raw)
            h = HEADING_RE.match(raw)
            if h:
                headings.append(
                    Heading(level=len(h.group(1)), text=h.group(2).strip(),
                            line=idx, in_fence=True, fence_lang=lang)
                )
            continue

        h = HEADING_RE.match(raw)
        if h:
            headings.append(
                Heading(level=len(h.group(1)), text=h.group(2).strip(), line=idx, in_fence=False)
            )

    # Unterminated fence: keep what we have rather than discarding the block.
    if open_fence is not None:
        marker, lang, start, body = open_fence
        fences.append(
            FencedBlock(lang=lang, content="\n".join(body), start_line=start, end_line=len(lines))
        )

    try:
        rel = str(path.relative_to(repo_root))
    except ValueError:
        rel = str(path)

    return Document(
        path=path,
        repo_relative=rel.replace("\\", "/"),
        text=text,
        lines=lines,
        headings=headings,
        fences=fences,
        fenced_lines=fenced_lines,
    )


def load_set(set_dir: Path, repo_root: Path) -> InstructionSet:
    if not set_dir.is_dir():
        raise NotADirectoryError(f"instruction set not found: {set_dir}")
    docs = [parse_document(p, repo_root) for p in sorted(set_dir.glob("*.md"))]
    if not docs:
        raise FileNotFoundError(f"no .md files in {set_dir}")
    return InstructionSet(root=set_dir, name=set_dir.name, documents=docs)


def load_documents(paths: list[Path], repo_root: Path) -> list[Document]:
    return [parse_document(p, repo_root) for p in paths if p.is_file()]


# --------------------------------------------------------------------------
# Reference extraction
# --------------------------------------------------------------------------

# `PROJECT_CONTEXT.md §4`, `PROJECT_CONTEXT §4 (Constraints)`, `§7 of the Technical...`
SECTION_REF_RE = re.compile(
    r"(?:(?P<file>[A-Za-z0-9_<>.-]+?\.md|PROJECT_CONTEXT|state\.json)\s*)?"
    r"§\s*(?P<num>\d+)"
)
# Any *.md filename mentioned anywhere.
#
# The lookbehind must reject BOTH a preceding `*` (glob patterns like
# `*_TEMPLATE.md` describe a class of files, not one file) and a preceding word
# character. Without the latter the engine simply re-anchors one token to the
# right — `*_TEMPLATE.md` fails at `_TEMPLATE.md` and then happily matches
# `TEMPLATE.md`, reporting a file nobody ever named.
FILE_REF_RE = re.compile(r"(?<![*\w])`?(?P<name>[A-Za-z0-9_<>.-]+\.md)`?")
# state.json dotted/bracketed paths: `progress.lastProcessedChangeLogId`, `phases[]`,
# `stages.requirements.rerunCount`, `context.locations.sharedWithLegacy`
STATE_PATH_RE = re.compile(
    r"`(?P<path>(?:context|stages|phases|edits|changeLog|reviews|progress)"
    r"(?:\[\])?(?:\.[A-Za-z_][A-Za-z0-9_]*(?:\[\])?)*)`"
)
ID_RE = re.compile(r"\b(?P<id>C-?\d+|P-?\d+(?:\.T-?\d+)?|E-?\d+|R-?\d+)\b")


def iter_section_refs(doc: Document, include_fenced: bool = False):
    """Yield (line, file_hint, section_number, column) for every `§N` reference.

    The column lets callers bound how far back a prose file-hint may sit — a bare
    word like "business" anywhere on the line is far too loose a signal.
    """
    for idx, raw in enumerate(doc.lines, start=1):
        if not include_fenced and doc.is_fenced(idx):
            continue
        for m in SECTION_REF_RE.finditer(raw):
            yield idx, (m.group("file") or None), m.group("num"), m.start()


def iter_file_refs(doc: Document, include_fenced: bool = False):
    for idx, raw in enumerate(doc.lines, start=1):
        if not include_fenced and doc.is_fenced(idx):
            continue
        for m in FILE_REF_RE.finditer(raw):
            yield idx, m.group("name")


def iter_state_paths(doc: Document, include_fenced: bool = False):
    for idx, raw in enumerate(doc.lines, start=1):
        if not include_fenced and doc.is_fenced(idx):
            continue
        for m in STATE_PATH_RE.finditer(raw):
            yield idx, m.group("path")


def iter_ids(doc: Document, include_fenced: bool = False):
    for idx, raw in enumerate(doc.lines, start=1):
        if not include_fenced and doc.is_fenced(idx):
            continue
        for m in ID_RE.finditer(raw):
            yield idx, m.group("id")
