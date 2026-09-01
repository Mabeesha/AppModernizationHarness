"""Group G — Document style & EARS conformance.

Group G is the only group that grades the pipeline's *output* rather than its
instructions. G1-G4 read the generated documents supplied via ``--docs`` and skip
cleanly when none are; G5 reads the instruction set itself and verifies the
standard is actually wired into the stages that produce documents.

The standard being checked is ``DOCUMENT_STYLE.md``. A set that does not ship one
skips the whole group rather than failing it — Sets 1-3 predate it, and reporting
their every requirement as non-conforming would be noise, not signal.

Two design notes worth keeping in mind when editing this module:

* **G4 exists to catch the failure mode G3 could cause.** Told to be concise, a
  model prunes citations first, because they read as clutter. A document that got
  shorter by dropping its evidence is a worse document. G4 is graded MAJOR while
  G3 is MINOR for exactly that reason.
* **Every pattern here skips fenced content.** ``DOCUMENT_STYLE.md`` and the stage
  files quote non-conforming examples on purpose ("Before: *The system should
  handle invalid searches…*"). Firing on a document's own counter-examples would
  invert the check.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from ..model import CheckResult, Document, Finding, Metric, Severity
from ..registry import Context, check

# --------------------------------------------------------------------------
# What counts as a normative statement
# --------------------------------------------------------------------------

# Requirement id prefixes. TR-#/DD-#/UC-# label descriptive and decision content,
# which is deliberately not EARS, so they are absent on purpose. The optional
# letter segment covers the NFR-P-1 / NFR-S-4 category form these sets use.
REQ_ID = r"(?:BR|FR|NFR|VR|V)-(?:[A-Z]+-)?\d+(?:\.\d+)*"

# DOCUMENT_STYLE.md §4.5 fixes the bullet shape: a bullet opening with a bold id.
NORMATIVE_ID_RE = re.compile(
    rf"^\s*[-*]\s+\*\*(?P<id>{REQ_ID})\*\*\s*(?P<rest>.*)$"
)

# Business rules and NFRs are commonly tabulated instead — `| **BR-1** | statement |
# evidence |`. Missing these would have scored a whole document as having no
# requirements at all, which reads as a pass.
NORMATIVE_ROW_RE = re.compile(
    rf"^\s*\|\s*\*\*(?P<id>{REQ_ID})\*\*\s*\|(?P<rest>.*)$"
)

# Documents whose requirement sections are EARS-scoped (DOCUMENT_STYLE.md §4.4).
EARS_DOC_RE = re.compile(
    r"^(?:BUSINESS_REQUIREMENTS|FUNCTIONAL_REQUIREMENTS|TECHNICAL_REQUIREMENTS"
    r"|LOW_LEVEL_DESIGN)_.*\.md$",
    re.I,
)

# Any generated pipeline document — the readability surface for G3.
PIPELINE_DOC_RE = re.compile(
    r"^(?:PROJECT_CONTEXT|BUSINESS_REQUIREMENTS|FUNCTIONAL_REQUIREMENTS"
    r"|TECHNICAL_REQUIREMENTS|HIGH_LEVEL_DESIGN|LOW_LEVEL_DESIGN|PLAN"
    r"|HOW_TO_TEST|REVIEW)[_.].*\.md$",
    re.I,
)

# --------------------------------------------------------------------------
# EARS grammar (DOCUMENT_STYLE.md §4.1)
# --------------------------------------------------------------------------

EARS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Complex first: it also matches the state-driven opener, so order matters.
    ("complex", re.compile(r"^While\s+.+?,\s*when\s+.+?,\s*.+?\bshall\b", re.I | re.S)),
    ("event-driven", re.compile(r"^When\s+.+?,\s*.+?\bshall\b", re.S)),
    ("state-driven", re.compile(r"^While\s+.+?,\s*.+?\bshall\b", re.S)),
    ("unwanted", re.compile(r"^If\s+.+?,\s*then\s+.+?\bshall\b", re.S)),
    ("optional", re.compile(r"^Where\s+.+?,\s*.+?\bshall\b", re.S)),
    # Ubiquitous, last because it is the fallback. Both `The <system> shall …`
    # and `<System> shall …` are accepted: with a named system, "The
    # EmployeeSearch shall" is not English, and rejecting the bare form would
    # push authors back to the vague "The system". No comma may precede `shall`
    # — that is what separates a bare obligation from a conditional clause
    # somebody forgot to close.
    ("ubiquitous", re.compile(r"^(?!When\b|While\b|If\b|Where\b)[`\w*][^,]*?\bshall\b", re.S)),
]

EARS_OPENERS = ("The", "When", "While", "If", "Where")

SHALL_RE = re.compile(r"\bshall\b")

# Weak modality, in the statement body only. `must` is included: EARS fixes on
# `shall` precisely so one word means one thing across thousands of statements.
WEAK_MODALITY_RE = re.compile(
    r"\b(should|may|might|could|can|will|must|is expected to|ought to)\b", re.I
)

# `path/to/File.cs:110`, `App.config:12`, and the `:30-37` continuation form the
# sets use when citing further lines of a file already named.
CITATION_RE = re.compile(r"`[^`]*?(?:[\w./\\-]+\.[A-Za-z0-9]+:\d+|:\d+)(?:-\d+)?[^`]*?`")

INLINE_CODE_RE = re.compile(r"`[^`]*`")

# --------------------------------------------------------------------------
# Readability (DOCUMENT_STYLE.md §2)
# --------------------------------------------------------------------------

FILLER = [
    "it is important to note",
    "it should be noted",
    "it is worth noting",
    "as mentioned above",
    "as noted above",
    "in order to",
    "with respect to",
    "in terms of",
    "at this point in time",
    "in essence",
    "needless to say",
    "best-in-class",
    "state-of-the-art",
    "seamless",
    "seamlessly",
    "robustly",
    "leverage",
    "leverages",
    "leveraging",
    "utilize",
    "utilizes",
    "utilizing",
    "facilitate",
    "facilitates",
]
FILLER_RE = re.compile(r"\b(" + "|".join(re.escape(f) for f in FILLER) + r")\b", re.I)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")

MAX_SENTENCE_WORDS = 40

# Below this, a table cell is a label or a cross-reference list, not a statement.
MIN_STATEMENT_WORDS = 5


def _ears_docs(ctx: Context) -> list[Document]:
    return [d for d in ctx.docs if EARS_DOC_RE.match(d.name)]


def _pipeline_docs(ctx: Context) -> list[Document]:
    return [d for d in ctx.docs if PIPELINE_DOC_RE.match(d.name)]


@dataclass(frozen=True)
class Statement:
    """One normative statement, with its evidence kept separate from its wording.

    `text` is graded for EARS form; `evidence` is only searched for citations. In a
    table those live in different cells, and grading the evidence cell as part of
    the sentence would report every well-formed row as malformed.
    """

    id: str
    line: int
    text: str
    evidence: str


def _statements(doc: Document) -> list[Statement]:
    """Every normative statement in a document, bulleted or tabulated.

    A bulleted statement may wrap over continuation lines; they are folded in so
    that a `shall` on the second line still counts. It ends at a blank line, the
    next bullet, a table, or a heading.
    """
    out: list[Statement] = []
    i = 0
    lines = doc.lines
    while i < len(lines):
        line_no = i + 1
        if doc.is_fenced(line_no):
            i += 1
            continue

        row = NORMATIVE_ROW_RE.match(lines[i])
        if row:
            cells = [c.strip() for c in row.group("rest").split("|") if c.strip()]
            # Feature-index tables key their rows by the same ids (`| **FR-1** |
            # Sign in | S-1 |`). Those rows are navigation, not requirements;
            # grading them reports every overview table as a document that states
            # no obligations at all.
            if not cells or max(len(c.split()) for c in cells) < MIN_STATEMENT_WORDS:
                i += 1
                continue
            # Column layout is not fixed across these tables: some put the
            # statement first, others lead with a category label ("Data volume")
            # and carry the statement in a later cell. The longest cell is the
            # prose one; short cells are labels, statuses and cross-references.
            # Citations are searched across every cell regardless.
            text = max(cells, key=lambda c: len(c.split())) if cells else ""
            out.append(Statement(row.group("id"), line_no, text, " ".join(cells)))
            i += 1
            continue

        m = NORMATIVE_ID_RE.match(lines[i])
        if not m:
            i += 1
            continue
        parts = [m.group("rest").strip()]
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip():
                break
            if NORMATIVE_ID_RE.match(nxt) or nxt.lstrip().startswith(("#", "|")):
                break
            if re.match(r"^\s*[-*]\s", nxt) and not nxt.startswith(("   ", "\t")):
                break
            parts.append(nxt.strip())
            j += 1
        joined = " ".join(p for p in parts if p).strip()
        out.append(Statement(m.group("id"), line_no, joined, joined))
        i = j
    return out


def _classify(text: str) -> str | None:
    for name, pat in EARS_PATTERNS:
        if pat.match(text):
            return name
    return None


@check("G1", "EARS conformance in requirement statements")
def g1_ears(ctx: Context) -> CheckResult:
    """Every normative statement matches an EARS pattern, one sentence, one `shall`."""
    res = CheckResult()
    docs = _ears_docs(ctx)
    if not docs:
        res.skipped = (
            "no generated requirements/LLD documents supplied — pass --docs pointing at a "
            "pipeline output directory"
        )
        return res

    for doc in docs:
        stmts = _statements(doc)
        if not stmts:
            continue
        conforming = 0
        by_pattern: dict[str, int] = defaultdict(int)

        for st in stmts:
            rid, line, text = st.id, st.line, st.text
            pattern = _classify(text)
            shalls = len(SHALL_RE.findall(text))

            if pattern and shalls == 1:
                conforming += 1
                by_pattern[pattern] += 1
                continue

            if not pattern:
                opener = text.split(" ", 1)[0].strip("*_`") if text else "(empty)"
                if shalls == 0:
                    summary = f"{rid} states no obligation (`shall` is absent)"
                    detail = (
                        "A normative statement without `shall` is a description, not a "
                        "requirement. Nothing downstream can fail it, so nothing tests it."
                    )
                elif opener not in EARS_OPENERS:
                    summary = f"{rid} does not open with an EARS pattern (starts `{opener}`)"
                    detail = (
                        "DOCUMENT_STYLE.md §4.1 fixes five openers: The / When / While / If / "
                        "Where. A statement outside them has no explicit trigger or "
                        "precondition, which is where ambiguity hides."
                    )
                else:
                    summary = f"{rid} opens `{opener}` but the pattern is incomplete"
                    detail = (
                        "The opener is right but the clause it introduces is not closed — "
                        "`When`/`While`/`Where` need a comma before the response, and `If` "
                        "needs `, then`."
                    )
            else:
                summary = f"{rid} contains {shalls} `shall` clauses; a statement carries one"
                detail = (
                    "Two obligations in one statement get half-implemented, because the "
                    "statement reads as satisfied when either half works. Split it "
                    "(DOCUMENT_STYLE.md §4.2 rule 2)."
                )

            res.findings.append(
                Finding(
                    check="G1",
                    severity=Severity.MAJOR,
                    summary=summary,
                    detail=detail,
                    file=doc.repo_relative,
                    line=line,
                    subject=f"ears:{doc.name}:{rid}",
                    evidence=[text[:220]],
                )
            )

        res.metrics.append(
            Metric(
                check="G1",
                name="ears_conformance",
                value=round(conforming / len(stmts) * 100, 1),
                unit="%",
                context={
                    "file": doc.repo_relative,
                    "statements": len(stmts),
                    "conforming": conforming,
                    "patterns": dict(by_pattern),
                },
            )
        )
    return res


@check("G2", "Weak modality in requirement statements")
def g2_modality(ctx: Context) -> CheckResult:
    """`should` / `may` / `will` / `must` where EARS requires `shall`."""
    res = CheckResult()
    docs = _ears_docs(ctx)
    if not docs:
        res.skipped = "no generated requirements/LLD documents supplied (--docs)"
        return res

    for doc in docs:
        for st in _statements(doc):
            rid, line, text = st.id, st.line, st.text
            # Literal strings and identifiers are quoted; a `Cancel` button label
            # containing "may" is not a modality choice.
            scanned = INLINE_CODE_RE.sub(" ", text)
            hits = sorted({m.group(1).lower() for m in WEAK_MODALITY_RE.finditer(scanned)})
            if not hits:
                continue
            res.findings.append(
                Finding(
                    check="G2",
                    severity=Severity.MINOR,
                    summary=f"{rid} uses `{hits[0]}` where EARS requires `shall`",
                    detail=(
                        f"Found: {', '.join(f'`{h}`' for h in hits)}. One modal verb across "
                        "the whole document set is the point of EARS — a reader never has to "
                        "work out whether `should` was meant as optional. If the behaviour "
                        "genuinely is optional, it is not a requirement: state it in prose or "
                        "raise it as an OPEN QUESTION."
                    ),
                    file=doc.repo_relative,
                    line=line,
                    subject=f"modality:{doc.name}:{rid}",
                    evidence=[text[:220]],
                )
            )
    return res


def _paragraphs(doc: Document) -> list[tuple[int, str]]:
    """(first line, joined text) for each run of prose, with hard wraps removed.

    These documents wrap at ~95 columns. Splitting sentences per *line* measures
    the wrap width instead of the sentence length — every document then scores a
    tidy ten words and the check reports nothing, forever.

    Headings, tables, block quotes, rules and fenced blocks are excluded: they are
    not sentences, and a table row is not improved by being shorter.
    """
    out: list[tuple[int, str]] = []
    start: int | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal start, buf
        if start is not None and buf:
            out.append((start, " ".join(buf)))
        start, buf = None, []

    for line_no, raw in enumerate(doc.lines, start=1):
        if doc.is_fenced(line_no):
            flush()
            continue
        stripped = raw.strip()
        if not stripped or stripped.startswith(("#", "|", ">", "---", "***", "```")):
            flush()
            continue
        # A new bullet or numbered item starts a new unit of prose.
        if re.match(r"^\s*(?:[-*+]\s|\d+[.)]\s|\[[ x]\]\s)", raw):
            flush()
        if start is None:
            start = line_no
        buf.append(stripped)
    flush()
    return out


@check("G3", "Readability of generated documents")
def g3_readability(ctx: Context) -> CheckResult:
    """Filler phrases and over-long sentences, with per-document metrics.

    MINOR throughout: this is the softest check in the suite, and the one most
    likely to disagree with a deliberate authorial choice.
    """
    res = CheckResult()
    docs = _pipeline_docs(ctx)
    if not docs:
        res.skipped = "no generated pipeline documents supplied (--docs)"
        return res

    for doc in docs:
        prose = _paragraphs(doc)
        if not prose:
            continue

        # Filler
        seen_filler: dict[str, tuple[int, str]] = {}
        filler_total = 0
        for line_no, text in prose:
            scanned = INLINE_CODE_RE.sub(" ", text)
            for m in FILLER_RE.finditer(scanned):
                filler_total += 1
                seen_filler.setdefault(m.group(1).lower(), (line_no, text))

        for phrase, (line_no, text) in sorted(seen_filler.items()):
            res.findings.append(
                Finding(
                    check="G3",
                    severity=Severity.MINOR,
                    summary=f"Filler phrase `{phrase}`",
                    detail=(
                        "DOCUMENT_STYLE.md §2 lists this as a phrase to delete outright. It "
                        "adds length without changing what the reader understands."
                    ),
                    file=doc.repo_relative,
                    line=line_no,
                    subject=f"filler:{doc.name}:{phrase}",
                    evidence=[text[:200]],
                )
            )

        # Sentence length
        lengths: list[int] = []
        long_sentences: list[tuple[int, str, int]] = []
        for line_no, text in prose:
            scanned = INLINE_CODE_RE.sub("X", text)
            for sentence in SENTENCE_SPLIT_RE.split(scanned):
                words = len(sentence.split())
                if words < 3:
                    continue
                lengths.append(words)
                if words > MAX_SENTENCE_WORDS:
                    long_sentences.append((line_no, sentence.strip(), words))

        if lengths:
            res.metrics.append(
                Metric(
                    check="G3",
                    name="sentence_length",
                    value=round(sum(lengths) / len(lengths), 1),
                    unit="words (mean)",
                    context={
                        "file": doc.repo_relative,
                        "sentences": len(lengths),
                        "over_limit": len(long_sentences),
                        "longest": max(lengths),
                        "filler_hits": filler_total,
                    },
                )
            )

        for line_no, sentence, words in long_sentences[:10]:
            res.findings.append(
                Finding(
                    check="G3",
                    severity=Severity.MINOR,
                    summary=f"Sentence runs {words} words (limit {MAX_SENTENCE_WORDS})",
                    detail=(
                        "DOCUMENT_STYLE.md §2 caps a sentence at 40 words. Past that a reader "
                        "has to re-parse, and a requirement that needs re-parsing gets "
                        "misread."
                    ),
                    file=doc.repo_relative,
                    line=line_no,
                    subject=f"long-sentence:{doc.name}:{line_no}",
                    evidence=[sentence[:220]],
                )
            )
    return res


@check("G4", "Evidence survives on requirement statements")
def g4_evidence(ctx: Context) -> CheckResult:
    """Every normative statement still carries a `path:line` citation.

    The guard on G3. Told only to be concise, a model prunes citations first —
    they read as clutter and cost the most characters. Without them the Review
    stage cannot verify a single requirement, so this is MAJOR where G3 is MINOR.
    """
    res = CheckResult()
    docs = _ears_docs(ctx)
    if not docs:
        res.skipped = "no generated requirements/LLD documents supplied (--docs)"
        return res

    for doc in docs:
        stmts = _statements(doc)
        if not stmts:
            continue
        cited = 0
        for st in stmts:
            rid, line, text = st.id, st.line, st.text
            # Search the evidence field, not the wording: a table row keeps its
            # citation in a later cell, and the two are graded separately.
            if CITATION_RE.search(st.evidence):
                cited += 1
                continue
            res.findings.append(
                Finding(
                    check="G4",
                    severity=Severity.MAJOR,
                    summary=f"{rid} carries no `path:line` citation",
                    detail=(
                        "DOCUMENT_STYLE.md §1 lists evidence as the first thing brevity may "
                        "never remove. An uncited requirement cannot be verified against the "
                        "legacy source by the Review stage, or by a human."
                    ),
                    file=doc.repo_relative,
                    line=line,
                    subject=f"evidence:{doc.name}:{rid}",
                    evidence=[text[:220]],
                )
            )
        res.metrics.append(
            Metric(
                check="G4",
                name="citation_coverage",
                value=round(cited / len(stmts) * 100, 1),
                unit="%",
                context={
                    "file": doc.repo_relative,
                    "statements": len(stmts),
                    "cited": cited,
                },
            )
        )
    return res


# Stages that produce a document a human reads, and so must be bound by the standard.
DOC_PRODUCING_STAGES = {"stage-0", "stage-1", "stage-2", "stage-3", "stage-4", "stage-5"}

STYLE_FILE = "DOCUMENT_STYLE.md"


@check("G5", "Style standard is wired into every document-producing stage")
def g5_wiring(ctx: Context) -> CheckResult:
    """A standard nothing references is a file, not a rule.

    Runs against the instruction set, not --docs, so it gates in CI. Skips for a
    set that ships no standard rather than failing every stage in it.
    """
    res = CheckResult()
    style = ctx.iset.by_name(STYLE_FILE)
    if style is None:
        res.skipped = f"set ships no {STYLE_FILE}"
        return res

    for stage, doc in sorted(ctx.iset.stage_documents().items()):
        if stage not in DOC_PRODUCING_STAGES:
            continue
        if STYLE_FILE in doc.text:
            continue
        res.findings.append(
            Finding(
                check="G5",
                severity=Severity.MAJOR,
                summary=f"{doc.name} never references {STYLE_FILE}",
                detail=(
                    "The stage writes a document a human reads, but nothing in its "
                    "instructions loads the writing standard. Rules an agent never reads do "
                    "not apply — this is how a shared standard silently becomes decorative."
                ),
                file=doc.repo_relative,
                line=1,
                subject=f"style-wiring:{doc.name}",
            )
        )

    # The standard has to be enforced somewhere, or it only ever gets followed on
    # the run that happened to feel careful.
    reviewer = ctx.iset.by_name("5_REVIEW_INSTRUCTIONS.md")
    if reviewer is not None and "EARS" not in reviewer.text:
        res.findings.append(
            Finding(
                check="G5",
                severity=Severity.MAJOR,
                summary="The review stage does not audit EARS conformance",
                detail=(
                    f"{STYLE_FILE} mandates EARS but the Review stage never checks it. An "
                    "unenforced writing standard decays to advice within a few reruns."
                ),
                file=reviewer.repo_relative,
                line=1,
                subject="style-wiring:review-ears",
            )
        )
    return res
