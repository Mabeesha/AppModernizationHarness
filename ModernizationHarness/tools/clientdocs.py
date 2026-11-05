#!/usr/bin/env python3
"""Build and check the hand-over pack (Stage 6) without hand-editing it.

Usage: python clientdocs.py [--file STATE] [--docs DIR] [--app NAME] <command> ...

  scan                     write or refresh CLIENT_PACK_NOTES.md in the documents folder: every
                           OPEN QUESTION / ASSUMPTION / TODO in the sources, and every harness
                           reference in the five documents and HOW_TO_RUN.md; what was filled
                           in is kept
  copy [--new-version]     make artifacts/<App>_BRD.md, _FRD, _TRD, _HLD and _LLD from the five
                           documents, and <App>_RUN_LOCALLY.md from HOW_TO_RUN.md, with the
                           mechanical rewrites; refuses once any copy exists, unless
                           --new-version: one more version, Draft again, every missing copy
                           made, and an existing copy made again only when its source changed
                           since (or no hash of its source is recorded)
  skeleton                 write artifacts/<App>_DEPLOYMENT_GUIDE.md from the template, its
                           configuration and secrets tables filled from LLD section 7; never
                           overwrites the guide - not even in a new version
  replace DOC "@FILE"      exact old->new pairs in one document (DOC: BRD, FRD, TRD, HLD, LLD,
                           RUN or DEPLOY), each old found exactly once; all or none
  set k=v ...              the pack's status (Draft | Final), prepared-for, prepared-by: in the
                           notes and in every document's front matter and Document control;
                           status=Final is refused while check reports a problem
  check                    prove the pack clean; each problem printed as file:line, exit 1

The five documents: BUSINESS_REQUIREMENTS_<App>.md (BRD), FUNCTIONAL_REQUIREMENTS_<App>.md (FRD),
TECHNICAL_REQUIREMENTS_<App>.md (TRD), HIGH_LEVEL_DESIGN_<App>.md (HLD) and
LOW_LEVEL_DESIGN_<App>.md (LLD), in the documents folder. scan also reads, where present,
PROJECT_CONTEXT.md, INTAKE_RESOLVED.md, PLAN_<App>.md, BUILD_ASSUMPTIONS_<App>.md and every
REVIEW_*.md there, and HOW_TO_RUN.md. A TODO is a marker only in the five documents and
HOW_TO_RUN.md. Markers inside code blocks are
quoted samples and are skipped, by scan and by check; a marker in a table row is its cell plus
the rest of the row, so each row is its own marker; one in a paragraph, list item or block quote
runs on to the end of it, a TODO there being a marker of its own.

CLIENT_PACK_NOTES.md holds: 1 Pack (version, status, prepared-for, prepared-by); 2 Versions;
3 Raw markers and 4 Reference hits (rewritten by every scan); 5 Items, 6 Exemptions,
7 Developer answers, 8 Review log and 9 Deployment facts (kept as written); 10 Sources (the hash
of each copy's source when copy made it). A raw marker's id, H-<6 hex>, comes from
its source file and its text, so it survives lines moving; an item lists the hits it settles.
An item row: Item | Hits | About (legacy | new | deploy) | Outcome | Evidence | Client
wording - a deploy item, raised while working out the deployment facts, may name no hit; Outcome
is one of Decided, Chosen in design, Adopted in build, Confirmed, Corrected, Not applicable,
Still open, Conflict. An exemption row: File (a copy) | Text | Reason - it excuses only that
exact text in that file, which must appear there once (or, for an ID the copy dropped, appear
in its source instead).

copy rewrites mechanically: a link to one of the five documents -> the copy's name; a link to
anything else outside the pack -> plain text (a #L48 line anchor becomes :48); an image under the
documents folder is copied beside the copies; the Revision History section -> a Document
control table built from 2 Versions; the LLD's section 3c (Reference Adoption) is dropped; front
matter (title, version, date, status, prepared-for, prepared-by) is added. Everything else is
copied unchanged - the judgement edits go through replace. The deployment guide's template has
sections 0-12; section 4 (Configuration: Key | What it does | Required? | Set at | Default |
Example | Differs per environment? | Where it is set) and section 5 (Secrets: Name | What it is
for | How it reaches the application | Who provides it | Format - no value column) are filled
from the first LLD section 7 table with a Key column (Key | Shape | Default | Secret? | Set at
| Differs per environment), a secret key (Secret? yes, y, true or a tick) going to section 5 and
any other Secret? value warned of; an LLD with no such table gives its back-ticked names
instead, for the agent to prune. Every place still to write reads "*To be written".

check fails on: a copy missing; front matter missing, or its version, status, prepared-for or
prepared-by not matching 1 Pack; a harness reference
not covered by an exemption; a raw marker; a link that leaves the pack or names a heading that is
not there; an ID (BR-7, FR-12, DD-3...) or a numbered heading (3, 3c, 3.3) of a source missing
from its copy
without an exemption; a raw marker no item settles; an item naming a hit that no longer exists;
an item with a bad About or Outcome, a settled outcome with no evidence, or no client wording;
any Conflict; an exemption that is stale or matches more than once; in any document, what looks
like a secret value - a literal assigned to a password, secret, token, api key, client secret,
or private, signing, encryption or access key name: any value as configuration (in a code block,
or the key a line starts with), one with a digit or symbol or 12+ characters in prose - while a
name about a secret (ending in uri, url, endpoint, name, expiry, ttl, id...), an env-var name,
${...}, an address (://) and a <placeholder> pass; a Password= or Pwd= value in a connection
string; a private-key block, a JWT, an AWS key; a table cell that is wholly a 32+ character
random-looking string (a GUID, a path or an UPPER_CASE name passes). In the run document: a code
block of HOW_TO_RUN.md missing (a <placeholder> in the copy stands for some text of its line,
the rest must be the same). In the guide: "*To be written" left, a section 1-12 with no text, a
value column in section 5, an LLD secret key in section 4, or an LLD section 7 key missing from
sections 4 and 5, or a key there missing from the table (a framework setting, "framework" under
Required?, may be missing from it; with no section 7 table the keys are not checked, and check
says so).

state.json is found as state.py finds it (--file overrides) and only read: the documents folder
is the folder it is in and the app is its "project" (--docs and --app override; with both,
state.json is not needed). "@FILE" - always in double quotes ("@.harness-tmp/brd.json"):
PowerShell reads a bare leading @ as its own syntax - holds a JSON list of {"old": ..., "new":
...}. Values files go in .harness-tmp/ under the working-tree root, which this tool creates; a
values file in a folder named .harness-tmp is deleted once the command has read it, whatever the
outcome. k=v and "@FILE" turn a \\u2014-style escape back into its character. Output is ASCII;
writes are UTF-8, keep the file's line endings, go through a temp file, and nothing is printed
until they succeed.
"""
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import time
from datetime import date

SKIP_DIRS = {".git", "node_modules", "bin", "obj", "target", "dist", "ModernizationHarness"}
TMP_DIR = ".harness-tmp"  # values files; deleted once read
OLD_IGNORE = (b"*", b"*\n", b"*\r\n")  # the .gitignore older versions wrote in TMP_DIR
READ_VALUES = []  # values files in TMP_DIR this command read; deleted when it ends
NOTES = "CLIENT_PACK_NOTES.md"
PACK_DIR = "artifacts"
DOCS = (  # key, source name pattern, title
    ("BRD", "BUSINESS_REQUIREMENTS_{app}.md", "Business Requirements"),
    ("FRD", "FUNCTIONAL_REQUIREMENTS_{app}.md", "Functional Requirements"),
    ("TRD", "TECHNICAL_REQUIREMENTS_{app}.md", "Technical Requirements"),
    ("HLD", "HIGH_LEVEL_DESIGN_{app}.md", "High-Level Design"),
    ("LLD", "LOW_LEVEL_DESIGN_{app}.md", "Low-Level Design"),
)
RUN_SOURCE = "HOW_TO_RUN.md"
OPS = (  # key, copy name pattern, title: the run document (copied) and the guide (a skeleton)
    ("RUN", "{app}_RUN_LOCALLY.md", "Running Locally"),
    ("DEPLOY", "{app}_DEPLOYMENT_GUIDE.md", "Deployment Guide"),
)
OTHER_SOURCES = ("PROJECT_CONTEXT.md", "INTAKE_RESOLVED.md", "PLAN_{app}.md",
                 "BUILD_ASSUMPTIONS_{app}.md")
OUTCOMES = ("Decided", "Chosen in design", "Adopted in build", "Confirmed", "Corrected",
            "Not applicable", "Still open", "Conflict")
ABOUT = ("legacy", "new", "deploy")
STATUSES = ("Draft", "Final")
PACK_KEYS = ("version", "status", "prepared-for", "prepared-by")

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_RE = re.compile(r"^([-*+]|\d+[.)])\s")
MARKER_RE = re.compile(r"`?\b(OPEN QUESTION|ASSUMPTION)\s*:`?|\bTODO\b")
HIT_ID_RE = re.compile(r"\bH-[0-9a-f]{6}\b")
LINK_RE = re.compile(r"(!?)\[((?:[^\[\]]|\[[^\]]*\])*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,5}-\d+(?:\.\d+)*\b")
HARNESS_ID_PREFIXES = {"BA"}  # harness-only ids a copy is meant to lose
NUMBERED_HEADING_RE = re.compile(r"^(\d+[a-z]?(?:\.\d+[a-z]?)*)\.?\s")  # 3, 3c, 3.3, 2.1a
START_MARKER_RE = re.compile(r"^`?(OPEN QUESTION|ASSUMPTION)\s*:")
REVISION_RE = re.compile(r"^(?:0\.\s*)?Revision History\b", re.I)
CONTROL_RE = re.compile(r"^(?:0\.\s*)?Document Control\b", re.I)
REFERENCE_ADOPTION_RE = re.compile(r"^3c\b")
LLD_CONFIG_RE = re.compile(r"^7\.?\s")
GUIDE_CONFIG_RE = re.compile(r"^4\.?\s+Configuration\b", re.I)
GUIDE_SECRETS_RE = re.compile(r"^5\.?\s+Secrets\b", re.I)
TO_WRITE = "*To be written"
SECRET_NAME = (r"(?:password|passwd|pwd|secret|token|api[_-]?key|client[_-]?secret"
               r"|(?:private|signing|encryption|access|secret)[_-]?key)")
SECRET_ASSIGN_RE = re.compile(
    r"(?P<k>[\w.-]*" + SECRET_NAME + r"[\w.-]*)[\"']?\s*[:=]\s*[\"']?"
    r"(?P<v>[^\s\"',;|`<>)\]}]+)", re.I)
NOT_SECRET_KEY_RE = re.compile(  # names about a secret, not holding one: token-uri, secretName
    r"(?:uri|url|endpoint|name|expiry|expires|lifetime|ttl|timeout|length|type|header|path|file"
    r"|location|id|storagekey|hash|prefix|format)$", re.I)
CONN_PASSWORD_RE = re.compile(r"\b(?:password|pwd)\s*=\s*(?P<v>[^;\s\"'<>]+)", re.I)
CONFIG_LINE_RE = re.compile(r"^\s*[-\"']?\s*[\w.-]+[\"']?\s*[:=]")
SECRET_SHAPES = (
    ("a private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("a JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.")),
    ("an AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
)
NOT_A_VALUE = {"null", "none", "true", "false", "yes", "no", "required", "optional", "string",
               "text", "env", "empty", "n/a", "tbd"}
YES = {"yes", "y", "true", "\u2713", "\u2714", "x"}
NO = {"no", "n", "false", "", "\u2014", "-", "\u2717", "\u2718"}
GUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
RANDOM_RE = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
GUIDE_SECTIONS = (  # number, title, what goes there (the "*To be written" line)
    ("1", "What You Are Deploying",
     "the parts of the application, what each is built into, and how they fit together"),
    ("2", "Environments", "each environment, and what differs between them"),
    ("3", "Before You Start",
     "the platform, runtime versions, network and database access, and the accounts the "
     "application uses - and who provides each"),
    ("4", "Configuration", None),
    ("5", "Secrets", None),
    ("6", "Build the Release", "the exact commands for each part, and the pipeline if there is one"),
    ("7", "Database",
     "whether the database is reused or new, how its structure is put in place or must be left "
     "unchanged, and how the application connects to it"),
    ("8", "Deploy", "the steps, in order, for each part"),
    ("9", "Check It Worked", "what to open and try once it is deployed, including one sign-in per role"),
    ("10", "Logging and Monitoring", "where the logs go and what to watch"),
    ("11", "Go-Live, Rollback and the Old System",
     "how the new system goes live, how to go back, and how long the old system runs beside it"),
    ("12", "Open Items", "anything still to be decided that affects deployment"),
)
CONFIG_HEADER = ("Key", "What it does", "Required?", "Set at", "Default", "Example",
                 "Differs per environment?", "Where it is set")
SECRETS_HEADER = ("Name", "What it is for", "How it reaches the application", "Who provides it",
                  "Format")
REFERENCES = (  # kind, pattern - what a copy must not contain
    ("harness file", re.compile(
        r"\bPROJECT_CONTEXT\b|\bINTAKE(?:_RESOLVED)?\b|\bstate\.json\b|\bfeatures\.json\b"
        r"|\bFEATURE_STATUS\b|\bLEGACY_CODE_MAP\w*|\bPLAN_\w+|\bHOW_TO_RUN\w*|\bREVIEW_R-\d+\w*"
        r"|\bAGENTS(?:_TEMPLATE)?\.md\b|\.harness-tmp\b|\bBUILD_ASSUMPTIONS\w*|\bCLIENT_PACK_NOTES\b"
        r"|\b(?:BUSINESS|FUNCTIONAL|TECHNICAL)_REQUIREMENTS\w*|\b(?:HIGH|LOW)_LEVEL_DESIGN\w*")),
    ("harness tool", re.compile(
        r"\b(?:state|docs|codemap|longrun|search|clientdocs|md2pdf)\.py\b|ModernizationHarness")),
    ("harness word", re.compile(
        r"\bharness\b|\bstage\s+[0-6]\b|\bretrofit\w*|\bre-?slic\w*|\bhigh-water mark\b"
        r"|\bobligations?\b|\bextraction instructions\b|\bchangeLog\b"
        r"|\bintake\s+(?:question|answer|part|template)s?\b"
        r"|\bcontext\.(?:repo|locations|deployment|currentStack|targetStack|referenceImplementations)\b",
        re.I)),
    ("harness ID", re.compile(
        r"\bQ\d{1,2}[a-z]?\b|\bP-\d+(?:\.T-\d+)?\b|\bE-\d+\b|\bR-\d+\b|\bBA-\d+\b"
        r"|\bH-[0-9a-f]{6}\b|\bI-\d+\b")),
)
SECTIONS = (  # number, title, help line, default table header
    ("1", "Pack", "*The pack's version, status and cover values. Change them with `set`.*", None),
    ("2", "Versions", "*One row per pack version - the Document control table of every copy.*",
     "| Version | Date | Status | Change |"),
    ("3", "Raw markers", "*Written by `scan` - do not edit; scan again instead.*",
     "| Hit | Source | Line | Where | Text |"),
    ("4", "Reference hits in the source documents",
     "*Written by `scan` - the worklist of harness references to rewrite. `check` looks at the "
     "copies.*", "| Source | Line | Kind | Found | Text |"),
    ("5", "Items",
     "*One row per distinct question or assumption. About: legacy | new | deploy. Outcome: "
     + " | ".join(OUTCOMES) + ". Evidence: where the answer came from (`path:line`, a change-log "
     "id, \"developer, <date>\"); Still open needs none.*",
     "| Item | Hits | About | Outcome | Evidence | Client wording |"),
    ("6", "Exemptions",
     "*Client text that looks like a harness reference, or an ID a copy dropped on purpose: the "
     "copy's file name, the exact text, why.*", "| File | Text | Reason |"),
    ("7", "Developer answers",
     "*Each answer the developer gave, dated, and the id of any change-log entry recorded for "
     "one.*", None),
    ("8", "Review log",
     "*Written only by the reviewer: `### Version <v> — Round <n> — PASS | FINDINGS`, then the "
     "numbered findings.*", None),
    ("9", "Deployment facts",
     "*Every fact the deployment guide states, with where it came from.*",
     "| Fact | Value | Source |"),
    ("10", "Sources",
     "*Written by `copy` - the hash of each copy's source when the copy was made.*",
     "| Copy | Source | Hash |"),
)
KEPT = ("1", "2", "5", "6", "7", "8", "9", "10")


def die(msg):
    """A malformed command: fix it and rerun."""
    sys.exit(f"clientdocs.py: {msg}")


def refuse(msg):
    """A rule speaking: never work around it."""
    sys.exit(f"clientdocs.py: refused: {msg}")


def ensure_tmp_dir():
    """.harness-tmp/ at the working-tree root holds values files. It is not git-ignored -
    GitLab Duo's file tools refuse an ignored path - so the .gitignore of "*" older versions
    wrote there is removed; one with anything else in it is the developer's and is kept."""
    try:
        os.makedirs(TMP_DIR, exist_ok=True)
        ignore = os.path.join(TMP_DIR, ".gitignore")
        if os.path.isfile(ignore):
            with open(ignore, "rb") as f:
                old = f.read() in OLD_IGNORE
            if old:
                os.remove(ignore)
                print(f"removed {ignore} (an older harness wrote it; the folder is no longer "
                      "git-ignored, so the agent's file tools can write there)", file=sys.stderr)
    except OSError:
        pass  # a read-only tree still runs every command


def in_tmp_dir(path):
    """True for a file inside a folder named .harness-tmp, wherever the command runs from."""
    folders = os.path.normcase(os.path.abspath(path)).split(os.sep)[:-1]
    return os.path.normcase(TMP_DIR) in folders


def remove_read_values():
    """Delete the values files this command read from .harness-tmp/, success or not, so the next
    write there is a new file (a create-only file tool cannot overwrite) and none is left over."""
    for path in READ_VALUES:
        for attempt in range(5):
            try:
                os.remove(path)
                print(f"removed {path} (a values file is used once)", file=sys.stderr)
            except FileNotFoundError:
                pass
            except OSError as e:  # on Windows, open in another program - perhaps for a moment
                if isinstance(e, PermissionError) and attempt < 4:
                    time.sleep(0.1)
                    continue
                print(f"could not remove {path}: {e.strerror}; write the next values file "
                      "under a new name", file=sys.stderr)
            break


# --- files ----------------------------------------------------------------------------------

def find_state():
    hits = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if "state.json" in files:
            hits.append(os.path.join(root, "state.json"))
    if len(hits) != 1:
        die(f"found {len(hits)} state.json files {hits}; pass --file PATH")
    return hits[0]


def load_json(path):
    try:
        with open(path, "rb") as f:
            return json.loads(f.read())  # bytes: detects UTF-8/16/32 and a BOM itself
    except OSError as e:
        die(f"cannot read {path}: {e}")
    except ValueError as e:
        die(f"{path} is not valid JSON: {e}")


def read_text(path):
    """Text with LF line endings, plus how to write it back: (has BOM, used CRLF)."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        die(f"cannot read {path}: {e}")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        die(f"{path} is not UTF-8 (written by Set-Content or Out-File without -Encoding UTF8?); "
            "save it as UTF-8 and rerun")
    return text.replace("\r\n", "\n"), (raw.startswith(b"\xef\xbb\xbf"), "\r\n" in text)


def encode(text, style=(False, False)):
    bom, crlf = style
    if crlf:
        text = text.replace("\n", "\r\n")
    try:
        data = text.encode("utf-8")
    except UnicodeEncodeError:
        die("text contains a broken character (half of a \\ud83d\\ude00-style pair?); nothing written")
    return (b"\xef\xbb\xbf" if bom else b"") + data


def write_all(items):
    """Write each (path, bytes) to a temp file, then move them all into place."""
    done, tmps = [], []
    try:
        for path, data in items:
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            tmp = path + ".tmp"
            tmps.append(tmp)
            with open(tmp, "wb") as f:
                f.write(data)
        for (path, _), tmp in zip(items, tmps):
            os.replace(tmp, path)
            done.append(path)
    except OSError as e:
        for tmp in tmps:
            if os.path.exists(tmp):
                os.remove(tmp)
        die(f"could not write: {e}; " + (f"{done} were written - run `check`"
                                          if done else "nothing written"))


def unescape(raw):
    # \uXXXX is how output shows non-ASCII; decode each run as JSON so a copied value
    # round-trips, including two-code characters such as emoji (the same rule as state.py)
    return re.sub(r"(?:\\u[0-9a-fA-F]{4})+", lambda m: json.loads(f'"{m.group(0)}"'), raw)


def unescape_tree(v):
    if isinstance(v, str):
        return unescape(v)
    if isinstance(v, list):
        return [unescape_tree(x) for x in v]
    if isinstance(v, dict):
        return {k: unescape_tree(x) for k, x in v.items()}
    return v


def is_file_arg(args):
    return len(args) == 1 and args[0].startswith("@")


def read_values(arg):
    """An @FILE's JSON; a file in .harness-tmp/ is deleted when the command ends."""
    path = arg[1:]
    if in_tmp_dir(path) and path not in READ_VALUES:
        READ_VALUES.append(path)
    return unescape_tree(load_json(path))


# --- markdown -------------------------------------------------------------------------------

def split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def cell(s):
    return " ".join(str(s).split()).replace("|", "\\|")


def row(*cells):
    return "| " + " | ".join(cell(c) for c in cells) + " |"


def is_table_line(line):
    return line.lstrip().startswith("|")


def table_rows(lines):
    """The data rows of the first table in lines, as lists of cells."""
    rows, started = [], False
    for line in lines:
        if is_table_line(line):
            cells = split_row(line)
            if started and not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                rows.append(cells)
            started = True
        elif started:
            break
    return rows


def fence_flags(lines):
    """For each line, True when it is inside (or opens/closes) a code block."""
    flags, inside = [], False
    for line in lines:
        if FENCE_RE.match(line):
            flags.append(True)
            inside = not inside
        else:
            flags.append(inside)
    return flags


def headings(lines):
    """(index, level, text) of every heading outside a code block."""
    out = []
    for i, (line, fenced) in enumerate(zip(lines, fence_flags(lines))):
        m = HEADING_RE.match(line)
        if m and not fenced:
            out.append((i, len(m.group(1)), m.group(2).strip()))
    return out


def section_span(lines, title_re):
    """(start, end) of the first section whose heading text matches, end exclusive."""
    hs = headings(lines)
    for n, (i, level, text) in enumerate(hs):
        if title_re.match(text):
            end = next((j for j, lv, _ in hs[n + 1:] if lv <= level), len(lines))
            return i, end
    return None


def plain_heading(text):
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return re.sub(r"<[^>]+>", "", text)


def slug(text):
    """A heading's anchor, as GitHub (and md2pdf.py) make it."""
    t = plain_heading(text).strip().lower()
    t = re.sub(r"[^\w\- ]", "", t)
    return t.replace(" ", "-")


def anchors(lines):
    seen, out = {}, set()
    for _, _, text in headings(lines):
        base = slug(text)
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.add(base if n == 0 else f"{base}-{n}")
    return out


def front_matter(lines):
    """({key: value}, index of the first body line) - ({}, 0) when there is none."""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    values = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return values, i + 1
        if ":" in lines[i]:
            k, v = lines[i].split(":", 1)
            values[k.strip()] = v.strip()
    return {}, 0


# --- the pack -------------------------------------------------------------------------------

class Pack:
    def __init__(self, docs_dir, app):
        self.dir = docs_dir
        self.app = app
        self.notes = os.path.join(docs_dir, NOTES)
        self.out = os.path.join(docs_dir, PACK_DIR)

    def source(self, key):
        """The document a copy is made from; None for the guide, which has none."""
        if key == "RUN":
            return os.path.join(self.dir, RUN_SOURCE)
        pattern = next((p for k, p, _ in DOCS if k == key), None)
        return pattern and os.path.join(self.dir, pattern.format(app=self.app))

    def copy_name(self, key):
        pattern = next((p for k, p, _ in OPS if k == key), None)
        return pattern.format(app=self.app) if pattern else f"{self.app}_{key}.md"

    def copy_path(self, key):
        return os.path.join(self.out, self.copy_name(key))

    def title(self, key):
        return next(t for k, _, t in DOCS + OPS if k == key)

    def copyable(self):
        """The documents copy makes: the five, and the run document when HOW_TO_RUN.md exists."""
        return [k for k, _, _ in DOCS] + (["RUN"] if os.path.isfile(self.source("RUN")) else [])

    def documents(self):
        """Every document of the pack: what copy makes, and the guide."""
        return self.copyable() + ["DEPLOY"]

    def need_sources(self):
        missing = [os.path.basename(self.source(k)) for k, _, _ in DOCS
                   if not os.path.isfile(self.source(k))]
        if missing:
            die(f"missing in {self.dir}: {', '.join(missing)} - the pack needs all five documents")

    def other_sources(self):
        out = []
        for pattern in OTHER_SOURCES:
            path = os.path.join(self.dir, pattern.format(app=self.app))
            if os.path.isfile(path):
                out.append(path)
        if not any(os.path.basename(p).startswith("PLAN_") for p in out):
            plans = [f for f in sorted(os.listdir(self.dir))
                     if f.startswith("PLAN_") and f.endswith(".md")]
            if len(plans) == 1:
                out.append(os.path.join(self.dir, plans[0]))
        out += [os.path.join(self.dir, f) for f in sorted(os.listdir(self.dir))
                if f.startswith("REVIEW_") and f.endswith(".md")]
        return out

    def source_names(self):
        """Every way a link may name a copied document -> its copy's name."""
        return {os.path.basename(self.source(k)): self.copy_name(k) for k in self.copyable()}


# --- notes ----------------------------------------------------------------------------------

def default_body(number, today):
    _, _, help_line, header = next(s for s in SECTIONS if s[0] == number)
    body = [help_line, ""]
    if number == "1":
        body += ["| Key | Value |", "|---|---|", row("version", "1.0"), row("status", "Draft"),
                 row("prepared-for", ""), row("prepared-by", "")]
    elif header:
        body += [header, "|" + "---|" * header.count(" | ") + "---|"]
        if number == "2":
            body.append(row("1.0", today, "Draft", "First issue"))
    return body


def read_notes(pack):
    """{section number: body lines} - empty when there are no notes yet."""
    if not os.path.isfile(pack.notes):
        return {}
    text, _ = read_text(pack.notes)
    lines = text.split("\n")
    out, current = {}, None
    for line, fenced in zip(lines, fence_flags(lines)):
        m = re.match(r"^##\s+(\d+)\.\s", line)
        if m and not fenced:
            current = m.group(1)
            out[current] = []
        elif current:
            out[current].append(line)
    for number in out:
        while out[number] and not out[number][-1].strip():
            out[number].pop()
        while out[number] and not out[number][0].strip():
            out[number].pop(0)
    return out


def load_notes(pack):
    """The notes, every section present (an older file gains the ones it lacks); die if none."""
    sections = read_notes(pack)
    if not sections:
        die(f"no {NOTES} yet - run `scan` first")
    today = date.today().isoformat()
    for number, _, _, _ in SECTIONS:
        sections.setdefault(number, default_body(number, today))
    return sections


def source_hashes(sections):
    return {r[0]: r[2] for r in table_rows(sections.get("10", [])) if len(r) >= 3}


def set_source_hashes(sections, hashes, sources):
    body = [l for l in sections["10"] if not is_table_line(l)]
    while body and not body[-1].strip():
        body.pop()
    sections["10"] = body + ["", "| Copy | Source | Hash |", "|---|---|---|"] + [
        row(name, sources.get(name, ""), h) for name, h in sorted(hashes.items())]


def file_hash(path):
    return hashlib.sha256(read_text(path)[0].encode("utf-8")).hexdigest()[:16]


def notes_text(pack, sections):
    lines = [f"# Client Pack Notes — {pack.app}", "",
             "Stage 6's working record for the hand-over pack. **Internal - never sent to "
             "the client.** The copies in `artifacts/` are made by `tools/clientdocs.py copy` and "
             "edited only through `clientdocs.py replace` and `set`: do not edit them by hand, and "
             "to change "
             "what a source document says, rerun the stage that owns it and start a new pack "
             "version.", ""]
    for number, title, _, _ in SECTIONS:
        lines += [f"## {number}. {title}", ""] + sections[number] + [""]
    return "\n".join(lines)


def pack_values(sections):
    values = {r[0]: (r[1] if len(r) > 1 else "") for r in table_rows(sections.get("1", []))}
    return {k: values.get(k, "") for k in PACK_KEYS}


def set_pack_values(sections, values):
    body = [l for l in sections["1"] if not is_table_line(l)]
    while body and not body[-1].strip():
        body.pop()
    sections["1"] = body + ["", "| Key | Value |", "|---|---|"] + [
        row(k, values[k]) for k in PACK_KEYS]


def versions(sections):
    return [r + [""] * (4 - len(r)) for r in table_rows(sections.get("2", []))]


def set_versions(sections, rows):
    body = [l for l in sections["2"] if not is_table_line(l)]
    while body and not body[-1].strip():
        body.pop()
    sections["2"] = body + ["", "| Version | Date | Status | Change |", "|---|---|---|---|"] + [
        row(*r[:4]) for r in rows]


def items(sections):
    return [r + [""] * (6 - len(r)) for r in table_rows(sections.get("5", []))]


def exemptions(sections):
    return [r + [""] * (3 - len(r)) for r in table_rows(sections.get("6", []))
            if any(c.strip() for c in r)]


def raw_hits(sections):
    """{hit id: (source, line)} from section 3."""
    return {r[0]: (r[1], r[2]) for r in table_rows(sections.get("3", [])) if len(r) >= 3}


# --- scanning -------------------------------------------------------------------------------

def hit_id(source, text):
    norm = " ".join(text.replace("`", "").split())
    return "H-" + hashlib.sha1(f"{source}|{norm}".encode("utf-8")).hexdigest()[:6]


def table_markers(cells, todo):
    """(kind, text) for each marker in a table row. A cell alone is often only "ASSUMPTION:
    (default applied)", so the text carries the rest of the row - each row its own marker."""
    out = []
    for n, c in enumerate(cells):
        for m in MARKER_RE.finditer(c):
            if m.group(1) or todo:
                rest = [x for x in cells[:n] + [c[:m.start()].strip()] + cells[n + 1:] if x.strip()]
                text = c[m.start():] + (f" [row: {' | '.join(rest)}]" if rest else "")
                out.append((m.group(1) or "TODO", text))
    return out


def markers(lines, todo=True):
    """(line number, kind, text, where) for every marker outside a code block. todo=False skips
    TODO, which only the five documents use as a marker (a review may say "no TODO left")."""
    out, heading = [], ""
    fenced = fence_flags(lines)
    for i, line in enumerate(lines):
        if fenced[i]:
            continue
        h = HEADING_RE.match(line)
        if h:
            heading = h.group(2).strip()
        if is_table_line(line):
            cells = split_row(line)
            out += [(i + 1, kind, text, cells[0]) for kind, text in table_markers(cells, todo)]
            continue
        questions = [m for m in MARKER_RE.finditer(line) if m.group(1)]
        for n, m in enumerate(questions):
            end = questions[n + 1].start() if n + 1 < len(questions) else len(line)
            text = line[m.start():end].strip()
            if n + 1 == len(questions):  # the last one runs on to the end of its paragraph
                text = run_on(lines, fenced, i, text)
            out.append((i + 1, m.group(1), text, heading))
        if todo:  # a TODO is its own marker, and never cuts a question short
            out += [(i + 1, "TODO", run_on(lines, fenced, i, line[m.start():].strip()), heading)
                    for m in MARKER_RE.finditer(line) if not m.group(1)]
    return out


def run_on(lines, fenced, i, text):
    """text, carried on over the lines after line i to the end of its paragraph or quote."""
    quote = lines[i].lstrip().startswith(">")
    for j in range(i + 1, min(i + 9, len(lines))):
        nxt, s = lines[j], lines[j].strip()
        if quote:
            if not s.startswith(">"):
                break
            s = s.lstrip(">").strip()
        if (not s or fenced[j] or HEADING_RE.match(nxt) or s.startswith("|")
                or LIST_RE.match(s) or START_MARKER_RE.match(s)):
            break
        text += " " + s
    return text


def clean_marker(text):
    text = re.sub(r"^`?(OPEN QUESTION|ASSUMPTION)\s*:`?\s*", r"\1: ", text.strip())
    if text.count("`") % 2:  # the marker's code span closed after the text: "`ASSUMPTION: x`"
        i = text.rfind("`")
        text = (text[:i] + text[i + 1:]).strip()
    return text if len(text) <= 400 else text[:399] + "…"


def link_leaves(target, allowed):
    """True when a link target is outside the pack: not a web link, an anchor, or a copy."""
    if re.match(r"^(?:[a-z][a-z0-9+.-]*:|#)", target, re.I):
        return False
    path = target.split("#", 1)[0]
    return os.path.basename(path) not in allowed or path != os.path.basename(path)


def reference_hits(lines, allowed):
    """(line number, kind, found, line text) for every harness reference and outside link."""
    out = []
    for i, line in enumerate(lines):
        links = list(LINK_RE.finditer(line))
        inside = [(m.start(3), m.end(3)) for m in links  # a link to a copy is rewritten by copy
                  if os.path.basename(m.group(3).split("#", 1)[0]) in allowed]
        for kind, pattern in REFERENCES:
            for m in pattern.finditer(line):
                if not any(a <= m.start() and m.end() <= b for a, b in inside):
                    out.append((i + 1, kind, m.group(0), m.start(), m.end()))
        for m in links:
            target = m.group(3)
            if m.group(1) == "!":
                continue  # images are checked as files
            if link_leaves(target, allowed):
                out.append((i + 1, "link", target, m.start(), m.end()))
    return out


def cmd_scan(pack, args, flags):
    if args:
        die("scan takes no arguments")
    pack.need_sources()
    today = date.today().isoformat()
    sections = read_notes(pack)
    first = not sections
    for number, _, _, _ in SECTIONS:
        if number not in KEPT or number not in sections:
            sections[number] = default_body(number, today)

    hits, order = {}, []
    copied = [pack.source(k) for k in pack.copyable()]
    sources = copied + pack.other_sources()
    for path in sources:
        name = os.path.basename(path)
        lines = read_text(path)[0].split("\n")
        for line_no, kind, text, where in markers(lines, todo=path in copied):
            text = clean_marker(text)
            hid = hit_id(name, text)
            if hid in hits:
                hits[hid][2].append(str(line_no))
                continue
            hits[hid] = [hid, name, [str(line_no)], (where or "")[:40], text]
            order.append(hid)
    sections["3"] = default_body("3", today) + [
        row(h[0], h[1], ", ".join(h[2]), h[3], h[4]) for h in (hits[i] for i in order)]

    allowed = set(pack.source_names())
    refs = []
    for path in copied:
        lines = read_text(path)[0].split("\n")
        for line_no, kind, found, _, _ in reference_hits(lines, allowed):
            refs.append(row(os.path.basename(path), line_no, kind, found,
                            lines[line_no - 1].strip()[:160]))
    sections["4"] = default_body("4", today) + refs

    write_all([(pack.notes, encode(notes_text(pack, sections)))])
    settled = {h for r in items(sections) for h in HIT_ID_RE.findall(r[1])}
    open_hits = [h for h in order if h not in settled]
    orphans = sorted({h for r in items(sections) for h in HIT_ID_RE.findall(r[1])} - set(hits))
    print(f"{'wrote' if first else 'refreshed'} {pack.notes}: {len(order)} raw markers in "
          f"{len(sources)} sources, {len(refs)} reference hits in the documents to copy; "
          f"{len(items(sections))} items kept, {len(open_hits)} markers in no item"
          + (f", {len(orphans)} items naming hits that are gone ({', '.join(orphans)})"
             if orphans else ""))


# --- copying --------------------------------------------------------------------------------

def control_lines(level, number, rows):
    return [f"{'#' * level} {number}Document Control", "",
            "| Version | Date | Status | Change |", "|---|---|---|---|"] + [
        row(*r[:4]) for r in rows] + [""]


def front_lines(pack, key, values, today):
    return ["---", f"title: {pack.title(key)} — {pack.app}", f"version: {values['version']}",
            f"date: {today}", f"status: {values['status']}",
            f"prepared-for: {values['prepared-for']}", f"prepared-by: {values['prepared-by']}",
            "---", ""]


def rewrite_link(m, names, pack, images):
    bang, label, target = m.group(1), m.group(2), m.group(3)
    if re.match(r"^(?:[a-z][a-z0-9+.-]*:|#)", target, re.I):
        return m.group(0)
    path, _, anchor = target.partition("#")
    base = os.path.basename(path)
    if base in names and not bang:
        return f"[{label}]({names[base]}{'#' + anchor if anchor else ''})"
    if bang:
        full = os.path.normpath(os.path.join(pack.dir, path))
        inside = os.path.commonpath([os.path.abspath(full), os.path.abspath(pack.dir)]) == \
            os.path.abspath(pack.dir)
        if inside and os.path.isfile(full):
            images.append(path)
        return m.group(0)
    where = re.sub(r"^(?:\.\./|\./)+", "", path)
    lines = re.fullmatch(r"L(\d+)(?:-L?(\d+))?", anchor or "")
    if lines:
        where += f":{lines.group(1)}" + (f"-{lines.group(2)}" if lines.group(2) else "")
    if re.search(r"[/.:\\]", label):
        return label
    return f"{label} ({where})" if label.strip() else f"`{where}`"


def make_copy(pack, key, values, rows, today):
    lines = read_text(pack.source(key))[0].split("\n")
    _, body = front_matter(lines)
    lines = lines[body:]
    if key == "LLD":
        span = section_span(lines, REFERENCE_ADOPTION_RE)
        if span:
            del lines[span[0]:span[1]]
    span = section_span(lines, REVISION_RE)
    if span:
        level = len(HEADING_RE.match(lines[span[0]]).group(1))
        number = "0. " if lines[span[0]].lstrip("# ").startswith("0") else ""
        lines[span[0]:span[1]] = control_lines(level, number, rows)
    else:
        h1 = next((i for i, lv, _ in headings(lines) if lv == 1), None)
        at = h1 + 1 if h1 is not None else 0
        lines[at:at] = [""] + control_lines(2, "0. ", rows)
    names, images = pack.source_names(), []
    fenced = fence_flags(lines)
    lines = [l if fenced[i] else LINK_RE.sub(lambda m: rewrite_link(m, names, pack, images), l)
             for i, l in enumerate(lines)]
    return "\n".join(front_lines(pack, key, values, today) + lines), images


def cmd_copy(pack, args, flags):
    if args:
        die("copy takes no arguments")
    pack.need_sources()
    sections = load_notes(pack)
    today = date.today().isoformat()
    values, rows = pack_values(sections), versions(sections)
    keys = pack.copyable()
    existing = [k for k in keys if os.path.exists(pack.copy_path(k))]
    if existing and "--new-version" not in flags:
        refuse(f"{', '.join(pack.copy_name(k) for k in existing)} already exist in {pack.out} - "
               "copying again would wipe every edit made through replace. Fix a copy with "
               "replace; start a new version (copy --new-version) only when the developer asks "
               "for one")
    if existing:
        try:
            major = int(float(values["version"] or "1")) + 1
        except ValueError:
            die(f"version {values['version']!r} in {NOTES} is not a number like 1.0")
        values["version"], values["status"] = f"{major}.0", "Draft"
        rows.append([values["version"], today, "Draft", "New version"])
        set_pack_values(sections, values)
    if not rows:
        rows = [[values["version"] or "1.0", today, values["status"] or "Draft", "First issue"]]
    set_versions(sections, rows)
    hashes, sources = source_hashes(sections), {}
    writes, made, kept, copied = [], [], [], []
    for key in keys:
        name, digest = pack.copy_name(key), file_hash(pack.source(key))
        sources[name] = os.path.basename(pack.source(key))
        if key in existing and hashes.get(name) == digest:
            kept.append(key)
            continue
        text, images = make_copy(pack, key, values, rows, today)
        writes.append((pack.copy_path(key), encode(text + ("" if text.endswith("\n") else "\n"))))
        hashes[name] = digest
        made.append(key)
        for rel in images:
            src, dst = os.path.join(pack.dir, rel), os.path.join(pack.out, rel)
            if not os.path.exists(dst):
                with open(src, "rb") as f:
                    writes.append((dst, f.read()))
                copied.append(rel)
    for key in kept + (["DEPLOY"] if os.path.isfile(pack.copy_path("DEPLOY")) else []):
        text, style = read_text(pack.copy_path(key))  # the new version's front matter and control
        lines = set_control(set_front(text.split("\n"), values), rows)
        writes.append((pack.copy_path(key), encode("\n".join(lines), style)))
    set_source_hashes(sections, hashes, sources)
    writes.append((pack.notes, encode(notes_text(pack, sections))))
    write_all(writes)
    print(f"version {values['version']} ({values['status']}) in {pack.out}")
    for key in made:
        print(f"  made  {pack.copy_name(key)}  <- {os.path.basename(pack.source(key))}")
    for key in kept:
        print(f"  kept  {pack.copy_name(key)}  (its source is unchanged; its edits stay)")
    if copied:
        print(f"  images: {', '.join(copied)}")
    if "RUN" not in keys:
        print(f"  note: no {RUN_SOURCE} in {pack.dir} - no run document")
    if not os.path.isfile(pack.copy_path("DEPLOY")):
        print(f"  next: `skeleton` writes {pack.copy_name('DEPLOY')}")


# --- the deployment guide -------------------------------------------------------------------

def header_and_rows(lines):
    """(header cells, data rows) of the first table in lines; ([], []) when there is none."""
    start = next((i for i, l in enumerate(lines) if is_table_line(l)), None)
    if start is None:
        return [], []
    return split_row(lines[start]), table_rows(lines[start:])


def column(header, *names):
    """The index of the first header cell starting with one of names, or None."""
    low = [h.lower() for h in header]
    return next((i for i, h in enumerate(low) if any(h.startswith(n) for n in names)), None)


def bare(cell_text):
    return cell_text.strip().strip("`").strip()


def lld_keys(pack):
    """([{key, shape, default, secret, set at, differs}], how): from the LLD section 7 table, or
    how is "table" / "names" (back-ticked names - loose) / "none"."""
    path = pack.source("LLD")
    if not path or not os.path.isfile(path):
        return [], "none"
    lines = read_text(path)[0].split("\n")
    span = section_span(lines, LLD_CONFIG_RE)
    if not span:
        return [], "none"
    part = lines[span[0]:span[1]]
    header, rows, k = [], [], None
    for i, line in enumerate(part):  # the first table in section 7 with a Key column
        if is_table_line(line) and (i == 0 or not is_table_line(part[i - 1])):
            header, rows = header_and_rows(part[i:])
            k = column(header, "key")
            if k is not None:
                break
    if k is not None:
        cols = {n: column(header, *names) for n, names in (
            ("shape", ("shape",)), ("default", ("default",)), ("secret", ("secret",)),
            ("set at", ("set at",)), ("differs", ("differs",)))}
        out = []
        for r in rows:
            if bare(r[k]):
                out.append({"key": bare(r[k]), **{n: (r[i].strip() if i is not None and i < len(r)
                                                      else "") for n, i in cols.items()}})
        for item in out:
            flag = bare(item["secret"]).strip("*_ ").lower()
            item["is secret"] = flag in YES
            item["unclear"] = flag not in YES | NO
        return out, "table"
    names = []
    for line in part[1:]:
        names += [n for n in re.findall(r"`([A-Za-z_][\w.:\-]*)`", line) if n not in names]
    return [{"key": n, "shape": "", "default": "", "secret": "", "set at": "", "differs": "",
             "is secret": False, "unclear": False} for n in names], ("names" if names else "none")


def guide_text(pack, values, rows, keys, today):
    tbw = TO_WRITE + "*"
    lines = front_lines(pack, "DEPLOY", values, today) + [
        f"# {pack.title('DEPLOY')} — {pack.app}", ""] + control_lines(2, "0. ", rows)
    for number, title, what in GUIDE_SECTIONS:
        lines += [f"## {number}. {title}", ""]
        if what:
            lines += [f"{TO_WRITE}: {what}.*", ""]
        elif number == "4":
            lines += ["Settings the application reads. None of them is secret - secrets are in "
                      "section 5.", "", row(*CONFIG_HEADER),
                      "|" + "---|" * len(CONFIG_HEADER)]
            plain = [k for k in keys if not k["is secret"]]
            lines += [row(f"`{k['key']}`", tbw, tbw, k["set at"] or tbw, k["default"] or tbw, tbw,
                          k["differs"] or tbw, tbw) for k in plain] or [row(*[tbw] * 8)]
            lines.append("")
        else:
            lines += ["Each secret by name - never its value.", "", row(*SECRETS_HEADER),
                      "|" + "---|" * len(SECRETS_HEADER)]
            secret = [k for k in keys if k["is secret"]]
            lines += [row(f"`{k['key']}`", tbw, tbw, tbw, k["shape"] or tbw)
                      for k in secret] or [row(*[tbw] * 5)]
            lines.append("")
    return "\n".join(lines)


def cmd_skeleton(pack, args, flags):
    if args:
        die("skeleton takes no arguments")
    sections = load_notes(pack)
    path = pack.copy_path("DEPLOY")
    if os.path.exists(path):
        refuse(f"{path} exists - the guide is written once and never made again, not even in a "
               "new version; change it with replace")
    values, rows = pack_values(sections), versions(sections)
    if not rows:
        die("no version yet - run `copy` first")
    keys, how = lld_keys(pack)
    write_all([(path, encode(guide_text(pack, values, rows, keys, date.today().isoformat())
                             + "\n"))])
    unclear = [k["key"] for k in keys if k["unclear"]]
    print(f"wrote {path}: " + {
        "table": f"{len(keys)} keys from the LLD section 7 table",
        "names": f"{len(keys)} back-ticked names from LLD section 7 - not a table, so some may "
                 "be file names or values: prune them",
        "none": "no keys - LLD section 7 has none; fill the tables from the code",
    }[how])
    if unclear:
        print(f"warning: Secret? is neither yes nor no for {', '.join(unclear)} - put in section 4 "
              "as not secret; move each that is secret to section 5, and fix LLD section 7")


# --- editing --------------------------------------------------------------------------------

def doc_key(arg):
    key = arg.upper()
    m = re.search(r"_(BRD|FRD|TRD|HLD|LLD|RUN_LOCALLY|DEPLOYMENT_GUIDE)\.MD$", key)
    key = {"RUN_LOCALLY": "RUN", "DEPLOYMENT_GUIDE": "DEPLOY"}.get(m.group(1), m.group(1)) if m else key
    if key not in {k for k, _, _ in DOCS + OPS}:
        refuse(f"{arg!r} is not a document of the pack - replace edits only BRD, FRD, TRD, HLD, "
               f"LLD, RUN or DEPLOY in {PACK_DIR}/; a source document belongs to the stage that "
               "wrote it")
    return key


def cmd_replace(pack, args, flags):
    if len(args) != 2 or not args[1].startswith("@"):
        die("replace takes DOC \"@FILE\": DOC is BRD, FRD, TRD, HLD, LLD, RUN or DEPLOY; FILE a JSON list of "
            "{\"old\": ..., \"new\": ...}")
    key = doc_key(args[0])
    path = pack.copy_path(key)
    pairs = read_values(args[1])
    if isinstance(pairs, dict) and "pairs" in pairs:
        pairs = pairs["pairs"]
    if not isinstance(pairs, list) or not pairs:
        die(f"{args[1][1:]} must hold a JSON list of {{\"old\": ..., \"new\": ...}}")
    if not os.path.isfile(path):
        die(f"{path} does not exist - run `{'skeleton' if key == 'DEPLOY' else 'copy'}` first")
    text, style = read_text(path)
    problems = []
    for n, pair in enumerate(pairs, 1):
        if isinstance(pair, list) and len(pair) == 2:
            pair = {"old": pair[0], "new": pair[1]}
        if not isinstance(pair, dict) or not isinstance(pair.get("old"), str) \
                or not isinstance(pair.get("new"), str) or not pair["old"]:
            problems.append(f"pair {n}: needs a non-empty text old and a text new")
            continue
        old, new = (pair[k].replace("\r\n", "\n") for k in ("old", "new"))
        found = text.count(old)
        if found != 1:
            problems.append(f"pair {n}: old text found {found} times, must be exactly once: "
                            f"{old[:60]!r}")
            continue
        text = text.replace(old, new)
    if problems:
        die("nothing written:\n" + "\n".join(problems))
    write_all([(path, encode(text, style))])
    print(f"replaced {len(pairs)} in {path}")


def set_front(lines, values):
    fm, body = front_matter(lines)
    if not fm:
        return lines
    for i in range(1, body - 1):
        if ":" in lines[i]:
            k = lines[i].split(":", 1)[0].strip()
            if k in values:
                lines[i] = f"{k}: {values[k]}"
    return lines


def set_control(lines, rows):
    span = section_span(lines, CONTROL_RE)
    if not span:
        return lines
    start = next((i for i in range(span[0], span[1]) if is_table_line(lines[i])), None)
    if start is None:
        return lines
    end = start
    while end < span[1] and is_table_line(lines[end]):
        end += 1
    lines[start:end] = ["| Version | Date | Status | Change |", "|---|---|---|---|"] + [
        row(*r[:4]) for r in rows]
    return lines


def cmd_set(pack, args, flags):
    if not args:
        die("set takes k=v ...: status=Draft|Final, prepared-for=..., prepared-by=...")
    sections = load_notes(pack)
    values, rows = pack_values(sections), versions(sections)
    for arg in args:
        if "=" not in arg:
            die(f"expected key=value, got {arg!r}")
        k, v = arg.split("=", 1)
        v = unescape(v).strip()
        if k not in ("status", "prepared-for", "prepared-by"):
            die(f"set takes status, prepared-for or prepared-by, not {k!r}")
        if k == "status":
            v = v.capitalize()
            if v not in STATUSES:
                die(f"status is Draft or Final, not {v!r}")
            if rows:
                rows[-1][2] = v
        values[k] = v
    if values["status"] == "Final" and any(a.startswith("status=") for a in args):  # every time
        # front matter is what this command writes; the cover values it needs, it takes from here
        problems = [p for p in pack_problems(pack, sections) if ": front matter " not in p]
        problems += [f"{NOTES}: no {k} - set it with this command"
                     for k in ("prepared-for", "prepared-by") if not values[k]]
        if problems:
            refuse(f"the pack cannot be Final while `check` reports {len(problems)} problem(s) - "
                   "the first: " + problems[0])
    set_pack_values(sections, values)
    set_versions(sections, rows)
    writes, changed = [(pack.notes, encode(notes_text(pack, sections)))], []
    for key in pack.documents():
        path = pack.copy_path(key)
        if not os.path.isfile(path):
            continue
        text, style = read_text(path)
        lines = set_control(set_front(text.split("\n"), values), rows)
        writes.append((path, encode("\n".join(lines), style)))
        changed.append(pack.copy_name(key))
    write_all(writes)
    print("set " + ", ".join(f"{k}={values[k]}" for k in PACK_KEYS if k != "version")
          + f" (version {values['version']}) in {NOTES}"
          + (f" and {', '.join(changed)}" if changed else ""))


# --- checking -------------------------------------------------------------------------------

def ids_and_numbers(lines, key):
    """The IDs and heading numbers a copy must keep: everything outside the dropped sections."""
    drop = []
    for title_re in (REVISION_RE, REFERENCE_ADOPTION_RE if key == "LLD" else None):
        span = title_re and section_span(lines, title_re)
        if span:
            drop.append(span)
    ids, numbers = {}, set()
    for i, line in enumerate(lines):
        if any(a <= i < b for a, b in drop):
            continue
        for m in ID_RE.finditer(line):
            if m.group(0).split("-")[0] not in HARNESS_ID_PREFIXES:
                ids.setdefault(m.group(0), i + 1)
    for i, _, text in headings(lines):
        if any(a <= i < b for a, b in drop):
            continue
        m = NUMBERED_HEADING_RE.match(text)
        if m:
            numbers.add(m.group(1))
    return ids, numbers


FRONT_KEYS = ("title", "version", "date", "status", "prepared-for", "prepared-by")


def front_problems(name, lines, values):
    fm, _ = front_matter(lines)
    if not fm:
        return [f"{name}:1: no front matter ({', '.join(FRONT_KEYS)})"]
    out = [f"{name}:1: front matter has no {k}"
           + (" - ask the developer, then `set`" if k.startswith("prepared") else "")
           for k in FRONT_KEYS if not fm.get(k)]
    out += [f"{name}:1: front matter says {k} {fm[k]}, {NOTES} says {values[k]} - use `set`"
            for k in PACK_KEYS if fm.get(k) and values[k] and fm[k] != values[k]]
    return out


def link_problems(pack, name, i, line, lines, allowed):
    out = []
    for m in LINK_RE.finditer(line):
        bang, target = m.group(1), m.group(3)
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            continue
        path_part, _, anchor = target.partition("#")
        if bang:
            if not os.path.isfile(os.path.join(pack.out, path_part)):
                out.append(f"{name}:{i + 1}: image {target!r} is not in {PACK_DIR}/")
        elif path_part and path_part not in allowed:
            out.append(f"{name}:{i + 1}: link {target!r} leaves the pack")
        elif anchor:
            other = os.path.join(pack.out, path_part)
            target_lines = lines if not path_part else (
                read_text(other)[0].split("\n") if os.path.isfile(other) else [])
            if anchor not in anchors(target_lines):
                out.append(f"{name}:{i + 1}: link {target!r} names no heading")
    return out


def line_problems(pack, name, lines, mine, allowed):
    """Harness references no exemption covers, raw markers outside code blocks, bad links."""
    out = []
    fenced = fence_flags(lines)
    for i, line in enumerate(lines):
        spans = [(m.start(), m.end()) for t in mine for m in re.finditer(re.escape(t), line)]
        for _, kind, found, a, b in reference_hits([line], allowed):
            if kind != "link" and not any(s <= a and b <= e for s, e in spans):
                out.append(f"{name}:{i + 1}: {kind} {found!r} - rewrite for the client or, if it "
                           "is client text, add an exemption")
        if not fenced[i]:  # a marker in a code block is a quoted sample, as scan treats it
            out += [f"{name}:{i + 1}: raw marker {m.group(0)!r} - replace it with the item's "
                    "client wording" for m in MARKER_RE.finditer(line)]
        out += link_problems(pack, name, i, line, lines, allowed)
    return out


def exemption_problems(name, whole, src_text, mine):
    out = []
    for t in mine:
        n = whole.count(t)
        if n == 0 and t not in src_text:
            out.append(f"{NOTES}: exemption {t!r} for {name} matches nothing - remove it")
        elif n > 1:
            out.append(f"{NOTES}: exemption {t!r} matches {n} times in {name} - give each use "
                       "its own exemption with more of the text around it")
    return out


def lost_problems(pack, key, name, lines, mine):
    """An ID or numbered heading of the source the copy no longer has."""
    if not os.path.isfile(pack.source(key)):
        return []
    source = os.path.basename(pack.source(key))
    ids, numbers = ids_and_numbers(read_text(pack.source(key))[0].split("\n"), key)
    kept = set(ID_RE.findall("\n".join(lines)))
    have = {m.group(1) for _, _, t in headings(lines) for m in [NUMBERED_HEADING_RE.match(t)] if m}
    out = [f"{source}:{line_no}: {ident} is missing from {name} - content lost? Restore it, or "
           "add an exemption saying why it was dropped"
           for ident, line_no in sorted(ids.items(), key=lambda x: x[1])
           if ident not in kept and ident not in mine]
    out += [f"{name}: section {number} of {source} is missing - content lost?"
            for number in sorted(numbers - have)]
    return out


def item_problems(sections):
    out, hits, named = [], raw_hits(sections), set()
    for r in items(sections):
        item, hit_ids = r[0] or "(no id)", HIT_ID_RE.findall(r[1])
        about, outcome, evidence, wording = (r[2].strip().lower(), r[3].strip(), r[4].strip(),
                                             r[5].strip())
        named.update(hit_ids)
        if not hit_ids and about != "deploy":
            out.append(f"{NOTES}: item {item} names no hit (only a deploy item may)")
        out += [f"{NOTES}: item {item} names {h}, which no longer exists (orphaned) - re-link "
                "the item to its new hit, or retire it" for h in hit_ids if h not in hits]
        if about not in ABOUT:
            out.append(f"{NOTES}: item {item}: About is {r[2]!r}, not legacy, new or deploy")
        match = next((o for o in OUTCOMES if o.lower() == outcome.lower()), None)
        if not match:
            out.append(f"{NOTES}: item {item}: Outcome {outcome!r} is not one of "
                       + ", ".join(OUTCOMES))
        elif match == "Conflict":
            out.append(f"{NOTES}: item {item} is a Conflict - the developer must settle it "
                       "before the pack can pass")
        elif match != "Still open" and not evidence:
            out.append(f"{NOTES}: item {item} is {match} with no evidence - cite it, or make it "
                       "Still open")
        if match and match != "Conflict" and not wording:
            out.append(f"{NOTES}: item {item} has no client wording")
    out += [f"{source}:{line.split(',')[0]}: marker {h} is settled by no item"
            for h, (source, line) in hits.items() if h not in named]
    return out


def is_reference(v):
    """A value that points at a secret rather than holding one: a variable, an address."""
    return (v.startswith(("$", "%", "{", "(", "@(", "process.env")) or "://" in v
            or re.fullmatch(r"[A-Z][A-Z0-9_]*", v) is not None or set(v) <= set("*.x-"))


def secret_values(line, fenced):
    """(start, end, text) of what looks like a secret value in one line. As configuration - any
    line of a code block, or the key a line starts with (key: value, key=value) - any value
    counts; in prose only one that looks like a password: with a digit or a symbol, or long."""
    out = []
    lead = (CONFIG_LINE_RE.match(line) and not is_table_line(line)  # a list item is prose
            and (fenced or not LIST_RE.match(line.lstrip())))
    first_key = re.match(r"^\s*[-\"']?\s*", line).end() if lead else -1
    for m in SECRET_ASSIGN_RE.finditer(line):
        v, k = m.group("v"), m.group("k")
        if NOT_SECRET_KEY_RE.search(k.rstrip("-_.")) or is_reference(v):
            continue
        if fenced or m.start() == first_key:
            if v.lower() in NOT_A_VALUE or len(v) < 3:
                continue
        elif (v.lower() in NOT_A_VALUE | {"secret"}
              or not (re.search(r"[\d!@#$%^&*+/=]", v) and len(v) >= 4 or len(v) >= 12)):
            continue
        out.append((m.start(), m.end(), m.group(0)))
    for m in CONN_PASSWORD_RE.finditer(line):  # Password=sa; - any value in a connection string
        if not is_reference(m.group("v")) and not any(a <= m.start() < b for a, b, _ in out):
            out.append((m.start(), m.end(), m.group(0)))
    return out


def secret_problems(name, lines, mine):
    """What looks like a secret value, outside the exempted text."""
    out = []
    fenced = fence_flags(lines)
    for i, line in enumerate(lines):
        spans = [(m.start(), m.end()) for t in mine for m in re.finditer(re.escape(t), line)]

        def free(a, b):
            return not any(s <= a and b <= e for s, e in spans)
        out += [f"{name}:{i + 1}: {text!r} looks like a secret value - name the secret, never "
                "its value (a <placeholder> is fine)"
                for a, b, text in secret_values(line, fenced[i]) if free(a, b)]
        for what, pattern in SECRET_SHAPES:
            out += [f"{name}:{i + 1}: {what} - never in a document"
                    for m in pattern.finditer(line) if free(m.start(), m.end())]
        if is_table_line(line):
            for c in split_row(line):
                v = c.strip().strip("`\"'")
                if (RANDOM_RE.fullmatch(v) and re.search(r"[A-Za-z]", v) and re.search(r"\d", v)
                        and not GUID_RE.fullmatch(v) and not re.fullmatch(r"[A-Z][A-Z0-9_]+", v)
                        and v.count("/") < 2 and all(v not in t for t in mine)):
                    out.append(f"{name}:{i + 1}: {v[:12]}... looks like a secret value")
    return out


def code_blocks(lines):
    """[(first line number, [lines])] of each fenced code block, fences left out."""
    out, current = [], None
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            if current is None:
                current = (i + 2, [])
            else:
                out.append(current)
                current = None
        elif current is not None:
            current[1].append(line.rstrip())
    return out


def command_matches(source_line, copy_line):
    """The copy's line, each <placeholder> standing for some text (spaces and all), is the whole
    source line - so nothing but the placeholder's part may differ."""
    parts = re.split(r"<[^<>\s][^<>]*>", copy_line)
    pattern = ".+".join(re.escape(p) for p in parts)
    return re.fullmatch(pattern, source_line) is not None


def command_problems(pack, name, lines, mine):
    """Every code block of HOW_TO_RUN.md is in the run document."""
    source = os.path.basename(pack.source("RUN"))
    have = code_blocks(lines)
    out = []
    for line_no, block in code_blocks(read_text(pack.source("RUN"))[0].split("\n")):
        wanted = [l for l in block if l.strip()]
        if not wanted or any(wanted[0].strip() in t or t in wanted[0] for t in mine):
            continue
        if not any(len(got) == len(wanted) and all(map(command_matches, wanted, got))
                   for got in ([l for l in b if l.strip()] for _, b in have)):
            out.append(f"{source}:{line_no}: the code block starting {wanted[0].strip()[:50]!r} is "
                       f"not in {name} - keep it (a <placeholder> may stand in for part of a line), "
                       "or add an exemption with its first line saying why it was dropped")
    return out


def guide_problems(pack, name, lines):
    """Nothing left to write, no value column for secrets, and keys that agree with LLD 7."""
    out = [f"{name}:{i + 1}: still to be written" for i, l in enumerate(lines) if TO_WRITE in l]
    for number, title, _ in GUIDE_SECTIONS:
        span = section_span(lines, re.compile(rf"^{number}\.?\s"))
        if span and not any(l.strip() for l in lines[span[0] + 1:span[1]]):
            out.append(f"{name}:{span[0] + 1}: section {number} ({title}) is empty")
    sections = {}
    for key, title_re in (("4", GUIDE_CONFIG_RE), ("5", GUIDE_SECRETS_RE)):
        span = section_span(lines, title_re)
        sections[key] = header_and_rows(lines[span[0]:span[1]]) if span else ([], [])
        if not span:
            out.append(f"{name}: no section {key} ({'Configuration' if key == '4' else 'Secrets'})")
    header5 = sections["5"][0]
    if column(header5, "value", "default", "example") is not None:
        out.append(f"{name}: section 5 (Secrets) has a value column - name each secret, never "
                   "its value")
    keys, how = lld_keys(pack)
    if how != "table":
        return out, ["no LLD section 7 table - keys not checked; compare them by hand"]
    header4, rows4 = sections["4"]
    req = column(header4, "required")
    in4 = {bare(r[0]) for r in rows4 if r}
    framework = {bare(r[0]) for r in rows4 if r and req is not None and req < len(r)
                 and r[req].strip().lower() == "framework"}
    in5 = {bare(r[0]) for r in sections["5"][1] if r}
    in_lld = {k["key"] for k in keys}
    out += [f"{name}: LLD section 7 key {k!r} is not in section 4 or 5"
            for k in sorted(in_lld - in4 - in5)]
    out += [f"{name}: key {k!r} is not in the LLD section 7 table - fix whichever is wrong (the "
            "design or the code), or mark a framework setting `framework` under Required?"
            for k in sorted((in4 | in5) - in_lld - framework) if k and TO_WRITE not in k]
    out += [f"{name}: {k['key']!r} is secret in LLD section 7 - it belongs in section 5, which "
            "has no value column, never in section 4" for k in keys
            if k["is secret"] and k["key"] in in4]
    return out, []


def pack_problems(pack, sections, notes=None):
    """Everything check reports, in order: exemptions, then each document, then the items."""
    values, exempt = pack_values(sections), exemptions(sections)
    names = {pack.copy_name(k) for k in pack.documents()}
    problems = []
    for e in exempt:
        if e[0] not in names:
            problems.append(f"{NOTES}: exemption names {e[0]!r}, which is not a copy "
                            f"({', '.join(sorted(names))})")
        elif not e[1].strip() or not e[2].strip():
            problems.append(f"{NOTES}: exemption for {e[0]} needs the exact text and a reason")
    for key in pack.documents():
        name, path = pack.copy_name(key), pack.copy_path(key)
        if not os.path.isfile(path):
            problems.append(f"{name}: missing - run `"
                            + ("skeleton" if key == "DEPLOY" else "copy") + "`"
                            + (" (a new version, on a pack made before it existed)"
                               if key != "DEPLOY" else ""))
            continue
        lines = read_text(path)[0].split("\n")
        mine = [e[1] for e in exempt if e[0] == name and e[1].strip()]
        source = pack.source(key)
        src_text = read_text(source)[0] if source and os.path.isfile(source) else ""
        problems += front_problems(name, lines, values)
        problems += line_problems(pack, name, lines, mine, names)
        problems += exemption_problems(name, "\n".join(lines), src_text, mine)
        problems += secret_problems(name, lines, mine)
        if source:
            problems += lost_problems(pack, key, name, lines, mine)
        if key == "RUN":
            problems += command_problems(pack, name, lines, mine)
        if key == "DEPLOY":
            found, said = guide_problems(pack, name, lines)
            problems += found
            if notes is not None:
                notes += said
    return problems + item_problems(sections)


def cmd_check(pack, args, flags):
    if args:
        die("check takes no arguments")
    sections = load_notes(pack)
    notes = []
    problems = pack_problems(pack, sections, notes)
    if problems:
        sys.exit("\n".join(problems + [f"note: {n}" for n in notes])
                 + f"\n{len(problems)} problem(s)")
    values, counts = pack_values(sections), {}
    for r in items(sections):
        counts[r[3].strip()] = counts.get(r[3].strip(), 0) + 1
    for n in notes:
        print(f"note: {n}")
    print(f"ok: {len(pack.documents())} documents, version {values['version']} ({values['status']}); "
          f"{len(items(sections))} items"
          + (" (" + ", ".join(f"{n} {o}" for o, n in counts.items()) + ")" if counts else "")
          + f"; {len(exemptions(sections))} exemptions")


COMMANDS = {
    "scan": (cmd_scan, set()),
    "copy": (cmd_copy, {"--new-version"}),
    "skeleton": (cmd_skeleton, set()),
    "replace": (cmd_replace, set()),
    "set": (cmd_set, set()),
    "check": (cmd_check, set()),
}


def take_flags(argv, allowed):
    args, flags = [], set()
    for a in argv:
        if a.startswith("--"):
            if a not in allowed:
                die(f"unknown flag {a}" + (f"; this command takes {', '.join(sorted(allowed))}"
                                           if allowed else ""))
            flags.add(a)
        else:
            args.append(a)
    return args, flags


def main(argv):
    for stream in (sys.stdout, sys.stderr):  # ASCII survives any console encoding
        stream.reconfigure(encoding="ascii", errors="backslashreplace")
    try:
        run(argv)
    finally:  # on a refusal too: sys.exit raises, so this runs before its message is printed
        remove_read_values()


def run(argv):
    ensure_tmp_dir()
    opts = {"--file": None, "--docs": None, "--app": None}
    while argv[:1] and argv[0] in opts:
        if len(argv) < 2:
            die(f"{argv[0]} needs a value")
        opts[argv[0]] = argv[1]
        argv = argv[2:]
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    func, allowed = COMMANDS[argv[0]]
    args, flags = take_flags(argv[1:], allowed)
    docs_dir, app = opts["--docs"], opts["--app"]
    if not (docs_dir and app):
        state_path = opts["--file"] or find_state()
        state = load_json(state_path)
        if not isinstance(state, dict):
            die(f"{state_path} must hold a JSON object")
        docs_dir = docs_dir or os.path.dirname(state_path) or "."
        app = app or state.get("project")
        if not app:
            die(f"{state_path} has no \"project\"; pass --app NAME")
    if not os.path.isdir(docs_dir):
        die(f"documents folder {docs_dir} does not exist")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):  # hold the result back until every write succeeds
        func(Pack(docs_dir, app), args, flags)
    sys.stdout.write(out.getvalue())


if __name__ == "__main__":
    main(sys.argv[1:])
