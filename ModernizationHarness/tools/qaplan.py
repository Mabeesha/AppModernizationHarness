#!/usr/bin/env python3
"""Stage 7's record and files: a manual test plan for a QA tester, and an Excel tracker.

Usage: python qaplan.py [--file STATE] <status | apply "@FILE" | check | build> [--force]

  status          where things stand: cases, coverage, the tracker, and what changed in the
                  ledger since the last tracker was written. Reads only
  apply "@FILE"   one batch of changes, all or none; writes qa_plan.json and the plan
  check           the proof: every built ledger row covered or excluded, every case complete,
                  no harness reference in the plan except an allowed one. Reads only
  build           the plan, and the tracker: v1 if none; the last one replaced in place while
                  it is exactly as written; otherwise, if anything in it would change, the next
                  version. A tracker the tester has saved is never overwritten
  --force         (apply, build) overwrite a plan that was edited by hand - first carry any
                  change worth keeping into the record with apply

Files: state.json is found as state.py finds it (--file overrides) and is only read, for the
app name ("project"). features.json - the ledger - sits beside it and is only read. Stage 7's
files are in qa/ beside them: qa_plan.json (the record; written only by this tool),
<App>_TEST_PLAN.md (generated whole; a hand edit is detected by the hash on its last line and
never overwritten without --force) and <App>_TEST_TRACKER_v<N>.xlsx (generated; never
overwritten once the file differs from what this tool wrote).

"@FILE" - always in double quotes ("@.harness-tmp/qa.json"): PowerShell reads a bare leading @
as its own syntax. It holds one JSON object with any of these keys, applied in this order:
  "set":       {"about"|"beforeYouStart"|"accounts"|"testData"|"howToRecord"|"knownLimits":
                "<Markdown text, or a list of lines>"}   the plan's written sections
  "retire":    [{"id": "TC-n", "reason": "..."}]           never deleted; the id is never reused
  "unexclude": ["<ledger row>", ...]
  "edit":      [{"id": "TC-n", <any case fields to replace>}]
  "exclude":   [{"id": "<ledger row>", "reason": "..."}]   not tested by hand; no active case
                                                            may check it
  "add":       [{"title", "checks": [ledger rows], "type", "priority", "before", "steps": [...],
                "expect"}]                                  the tool gives out the TC-n ids
  "allow":     [{"text": "<exactly as check prints it>", "where": "TC-n | <section> | ledger",
                "reason": "..."}]       an exception to the harness-word check; ledger is text the
                                        plan takes from the ledger (requirement names, groups)
  "unallow":   [{"text": "...", "where": "..."}]
A case: type is Smoke, Positive, Negative, Access, Workflow or Non-functional; priority High,
Medium or Low; steps a list of plain steps (the plan numbers them); checks names ledger rows
that are built and not excluded - empty only for a Smoke case. Values files go in .harness-tmp/
under the working-tree root; one there is deleted once read, whatever the outcome (as state.py
and docs.py do). \\u2014-style escapes become their character.

Exit status: 0 done; 1 refused or check found problems (each named); 2 malformed command.
Output is ASCII; writes are UTF-8 through temp files, and nothing is printed until they succeed.
Stdlib only: the tracker is Office Open XML written with zipfile.
"""
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import date

sys.dont_write_bytecode = True  # importing clientdocs must leave no __pycache__ in tools/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from clientdocs import REFERENCES as CLIENT_REFERENCES  # one list of harness references
except ImportError:  # pragma: no cover - shipped together
    sys.exit("qaplan.py: clientdocs.py must sit beside this tool (its reference list is reused)")

SKIP_DIRS = {".git", "node_modules", "bin", "obj", "target", "dist", "ModernizationHarness"}
TMP_DIR = ".harness-tmp"
OLD_IGNORE = (b"*", b"*\n", b"*\r\n")
READ_VALUES = []
DASH = "—"
TYPES = ("Smoke", "Positive", "Negative", "Access", "Workflow", "Non-functional")
PRIORITIES = ("High", "Medium", "Low")
STATUSES = ("Not run", "Pass", "Fail", "Blocked", "Skipped")
SECTIONS = (  # key, heading, required
    ("about", "1. About this plan", True),
    ("beforeYouStart", "3. Before you start", True),
    ("accounts", "4. Test accounts", True),
    ("testData", "5. Test data", True),
    ("howToRecord", "6. How to record results", False),
    ("knownLimits", "7. Known limits", True),
)
SECTION_KEYS = tuple(k for k, _, _ in SECTIONS)
CASE_FIELDS = ("title", "checks", "type", "priority", "before", "steps", "expect")
APPLY_KEYS = ("set", "retire", "unexclude", "edit", "exclude", "add", "allow", "unallow")
TC_RE = re.compile(r"TC-(\d+)")
STEP_NUMBER_RE = re.compile(r"^\s*\d+[.)]\s+")
TO_CONFIRM_RE = re.compile(r"\bto confirm\b", re.I)
REFERENCES = CLIENT_REFERENCES + (
    ("harness file", re.compile(r"\bqa_plan\.json\b")),
    ("harness tool", re.compile(r"\bqaplan(?:\.py)?\b")),
    ("harness word", re.compile(r"\bstage\s+7\b", re.I)),
)
MARK = "<!-- generated file: change it through the agent, not by hand. sha256:"
MARK_RE = re.compile(re.escape(MARK) + r"([0-9a-f]{64}) -->")
COLUMNS = (  # header, width, the tool's (True) or the tester's (False)
    ("Test ID", 9, True), ("Area", 18, True), ("Checks", 12, True), ("Title", 32, True),
    ("Type", 12, True), ("Priority", 9, True), ("Before you start", 28, True),
    ("Steps", 50, True), ("Expected result", 40, True),
    ("Changed since last version?", 13, True), ("Status", 11, False),
    ("Actual result", 30, False), ("Tested by", 14, False), ("Date", 12, False),
    ("Defect ID", 12, False), ("Notes", 30, False),
)
SMOKE_AREA, UNGROUPED_AREA = "Smoke tests", "Features"


def die(msg):
    """A malformed command or unreadable file: fix it and rerun (exit 2)."""
    print(f"qaplan.py: {msg}", file=sys.stderr)
    sys.exit(2)


def refuse(msg):
    """A rule speaking: never work around it (exit 1)."""
    print(f"qaplan.py: refused: {msg}", file=sys.stderr)
    sys.exit(1)


# --- values files (the same rules as state.py and docs.py) ----------------------------------

def ensure_tmp_dir():
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
        pass


def in_tmp_dir(path):
    folders = os.path.normcase(os.path.abspath(path)).split(os.sep)[:-1]
    return os.path.normcase(TMP_DIR) in folders


def remove_read_values():
    for path in READ_VALUES:
        for attempt in range(5):
            try:
                os.remove(path)
                print(f"removed {path} (a values file is used once)", file=sys.stderr)
            except FileNotFoundError:
                pass
            except OSError as e:
                if isinstance(e, PermissionError) and attempt < 4:
                    time.sleep(0.1)
                    continue
                print(f"could not remove {path}: {e.strerror}; write the next values file "
                      "under a new name", file=sys.stderr)
            break


def unescape(raw):
    return re.sub(r"(?:\\u[0-9a-fA-F]{4})+", lambda m: json.loads(f'"{m.group(0)}"'), raw)


def unescape_tree(v):
    if isinstance(v, str):
        return unescape(v)
    if isinstance(v, list):
        return [unescape_tree(x) for x in v]
    if isinstance(v, dict):
        return {k: unescape_tree(x) for k, x in v.items()}
    return v


def read_values(arg):
    path = arg[1:]
    if in_tmp_dir(path) and path not in READ_VALUES:
        READ_VALUES.append(path)
    return unescape_tree(load_json(path))


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
            return json.loads(f.read())
    except OSError as e:
        die(f"cannot read {path}: {e}")
    except ValueError as e:
        die(f"{path} is not valid JSON: {e}")


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        die(f"{path} is not UTF-8")
    return text.replace("\r\n", "\n"), (raw.startswith(b"\xef\xbb\xbf"), "\r\n" in text)


def encode(text, style=(False, False)):
    bom, crlf = style
    if crlf:
        text = text.replace("\n", "\r\n")
    try:
        data = text.encode("utf-8")
    except UnicodeEncodeError:
        die("text contains a broken character (half of a \\ud83d\\ude00-style pair?); "
            "nothing written")
    return (b"\xef\xbb\xbf" if bom else b"") + data


def write_all(items):
    done, tmps = [], []
    try:
        for path, data in items:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
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
        die(f"could not write: {e}; " + (f"{done} were written - run `check`" if done
                                          else "nothing written"))


def sha(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with open(path, "rb") as f:
        return sha(f.read())


def tc_num(cid):
    m = TC_RE.fullmatch(cid or "")
    return int(m.group(1)) if m else 0


# --- the project ----------------------------------------------------------------------------

class QA:
    def __init__(self, state_path):
        state = load_json(state_path)
        if not isinstance(state, dict):
            die(f"{state_path} must hold a JSON object")
        self.dir = os.path.dirname(state_path) or "."
        ledger_path = os.path.join(self.dir, "features.json")
        if not os.path.exists(ledger_path):
            die(f"no feature ledger at {ledger_path}; Stage 3 creates it, and Stage 7 runs after")
        self.ledger = load_json(ledger_path)
        self.app = state.get("project") or self.ledger.get("app")
        if not self.app:
            die(f"{state_path} has no \"project\" name")
        self.rows = {r.get("id"): r for r in self.ledger.get("features", [])
                     if isinstance(r, dict) and r.get("id")}
        self.order = [r.get("id") for r in self.ledger.get("features", [])
                      if isinstance(r, dict) and r.get("id")]
        self.groups = [g.get("title") for g in self.ledger.get("groups", [])
                       if isinstance(g, dict) and g.get("title")]
        self.qa_dir = os.path.join(self.dir, "qa")
        self.record_path = os.path.join(self.qa_dir, "qa_plan.json")
        self.plan_path = os.path.join(self.qa_dir, f"{self.app}_TEST_PLAN.md")
        self.record = load_json(self.record_path) if os.path.exists(self.record_path) else None
        if self.record is not None and not isinstance(self.record, dict):
            die(f"{self.record_path} must hold a JSON object")

    def built(self, rid):
        return str(self.rows.get(rid, {}).get("build", "")).startswith("built in")

    def snapshot(self):
        return {rid: {"build": self.rows[rid].get("build", ""),
                      "phases": list(self.rows[rid].get("phases", []))} for rid in self.order}

    def tracker_path(self, version):
        return os.path.join(self.qa_dir, f"{self.app}_TEST_TRACKER_v{version}.xlsx")

    def new_record(self):
        return {"app": self.app, "schemaVersion": 1, "updated": date.today().isoformat(),
                "nextId": 1, "sections": {k: "" for k in SECTION_KEYS}, "cases": [],
                "excluded": [], "allowed": [], "trackers": []}


def active(record):
    return sorted((c for c in record.get("cases", []) if c.get("status", "active") == "active"),
                  key=lambda c: tc_num(c.get("id")))


def area_of(qa, case):
    if case.get("type") == "Smoke":
        return SMOKE_AREA
    for rid in case.get("checks", []):
        group = qa.rows.get(rid, {}).get("group")
        if group:
            return group
    return UNGROUPED_AREA


def ordered_cases(qa, record):
    """Active cases in plan order: smoke first, then the ledger's groups, then the rest."""
    areas = [SMOKE_AREA] + qa.groups + [UNGROUPED_AREA]
    rank = {a: i for i, a in enumerate(areas)}
    return sorted(active(record), key=lambda c: (rank.get(area_of(qa, c), len(areas)),
                                                 tc_num(c.get("id"))))


# --- validation -----------------------------------------------------------------------------

def text_of(v):
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return "\n".join(v)
    return v


def case_errors(qa, record, case, label):
    errs = []
    for key in ("title", "expect"):
        if not isinstance(case.get(key), str) or not case[key].strip():
            errs.append(f"{label}: {key} must be non-empty text")
    if not isinstance(case.get("before", ""), str):
        errs.append(f"{label}: before must be text")
    if case.get("type") not in TYPES:
        errs.append(f"{label}: type must be one of {', '.join(TYPES)}")
    if case.get("priority") not in PRIORITIES:
        errs.append(f"{label}: priority must be one of {', '.join(PRIORITIES)}")
    steps = case.get("steps")
    if (not isinstance(steps, list) or not steps
            or not all(isinstance(s, str) and s.strip() for s in steps)):
        errs.append(f"{label}: steps must be a non-empty list of non-empty steps")
    checks = case.get("checks", [])
    if not isinstance(checks, list) or not all(isinstance(r, str) for r in checks):
        errs.append(f"{label}: checks must be a list of ledger row ids")
        return errs
    if not checks and case.get("type") != "Smoke":
        errs.append(f"{label}: checks names no ledger row (only a Smoke case may)")
    excluded = {e.get("id") for e in record.get("excluded", [])}
    for rid in checks:
        if rid not in qa.rows:
            errs.append(f"{label}: {rid} is not a ledger row")
        elif not qa.built(rid):
            errs.append(f"{label}: {rid} is not built ({qa.rows[rid].get('build')}); its cases "
                        "wait until it is")
        elif rid in excluded:
            errs.append(f"{label}: {rid} is recorded as not tested by hand - unexclude it first")
    return errs


def normalise_case(case):
    out = {k: case[k] for k in CASE_FIELDS if k in case}
    for key in ("title", "before", "expect", "type", "priority"):
        if isinstance(out.get(key), str):
            out[key] = out[key].strip()
    if isinstance(out.get("steps"), list):
        out["steps"] = [STEP_NUMBER_RE.sub("", s).strip() if isinstance(s, str) else s
                        for s in out["steps"]]
    if isinstance(out.get("checks"), list):
        seen = []
        for rid in out["checks"]:
            if isinstance(rid, str) and rid.strip() and rid.strip() not in seen:
                seen.append(rid.strip())
        out["checks"] = seen
    out.setdefault("before", "")
    out.setdefault("checks", [])
    return out


# --- the plan -------------------------------------------------------------------------------

def cell(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def render_plan(qa, record, tracker_file, version):
    """The plan as [(line, where)] - where names the record entry a line came from."""
    out = []

    def add(text, where="fixed"):
        for line in text.split("\n"):
            out.append((line, where))

    cases = ordered_cases(qa, record)
    excluded = {e.get("id"): e.get("reason", "") for e in record.get("excluded", [])}
    secs = record.get("sections", {})
    add(f"# Test Plan: {qa.app}", "title")
    add("")
    label = f"Version {version}" if version else "Draft - no tracker written yet"
    add(f"*{label} · updated {record.get('updated', '')}*")
    add("")

    def section(key, heading):
        add(f"## {heading}")
        add("")
        body = (secs.get(key) or "").strip()
        add(body if body else "*Not written yet.*", key)
        add("")

    section("about", "1. About this plan")
    add("## 2. Scope")
    add("")
    counts = {p: sum(1 for c in cases if c.get("priority") == p) for p in PRIORITIES}
    covered = sorted({r for c in cases for r in c.get("checks", [])},
                     key=lambda r: qa.order.index(r) if r in qa.order else 0)
    add(f"This version has **{len(cases)} test cases** — {counts['High']} high, "
        f"{counts['Medium']} medium and {counts['Low']} low priority — checking "
        f"{len(covered)} requirements. It is a sensible first round of manual testing, not "
        "an exhaustive one.")
    add("")
    add("### Not in this build")
    add("")
    unbuilt = [r for r in qa.order if not qa.built(r) and r not in excluded]
    if unbuilt:
        add("*Do not test these yet.*")
        add("")
        add("| ID | Requirement | Status |")
        add("|---|---|---|")
        for rid in unbuilt:
            row = qa.rows[rid]
            status = ("planned" if str(row.get("build", "")).startswith("scheduled")
                      else "not planned yet")
            add(f"| {rid} | {cell(row.get('feature', ''))} | {status} |", "ledger")
    else:
        add("*Every requirement is built.*")
    add("")
    add("### Not tested by hand")
    add("")
    if excluded:
        add("| ID | Requirement | Why |")
        add("|---|---|---|")
        for rid in [r for r in qa.order if r in excluded]:
            name, why = cell(qa.rows[rid].get("feature", "")), cell(excluded[rid])
            add(f"| {rid} | {name} | {why} |", "ledger")
    else:
        add("*None.*")
    add("")
    section("beforeYouStart", "3. Before you start")
    section("accounts", "4. Test accounts")
    section("testData", "5. Test data")
    add("## 6. How to record results")
    add("")
    if tracker_file:
        add(f"Record every result in the tracker, `{tracker_file}`: one row per test case. "
            "Change only the white columns; the grey ones come from this plan.")
    else:
        add("Record every result in the tracker, which comes with this plan: one row per test "
            "case. Change only the white columns; the grey ones come from this plan.")
    add("")
    add("**Run the smoke tests first.** If one fails, stop and report it: nothing else can be "
        "tested reliably.")
    add("")
    add("*Status* takes one of these:")
    add("")
    add("- **Not run** — not tried yet.")
    add("- **Pass** — what happened matched *Expect*.")
    add("- **Fail** — it did not. Write what happened in *Actual result*, and the defect's "
        "ticket number in *Defect ID*.")
    add("- **Blocked** — could not be run (the application would not start, data was "
        "missing, an earlier failure). Say why in *Notes*.")
    add("- **Skipped** — deliberately not run this round. Say why in *Notes*.")
    add("")
    add("*Priority*: **High** — smoke tests, end-to-end workflows, business rules and access "
        "checks; **Medium** — the rest of each feature; **Low** — wording and layout.")
    add("")
    extra = (secs.get("howToRecord") or "").strip()
    if extra:
        add(extra, "howToRecord")
        add("")
    section("knownLimits", "7. Known limits")
    add("## 8. Test cases")
    add("")
    if not cases:
        add("*No test cases yet.*")
        add("")
    area = None
    for c in cases:
        a = area_of(qa, c)
        if a != area:
            add(f"### {a}", "title" if a in (SMOKE_AREA, UNGROUPED_AREA) else "ledger")
            add("")
            area = a
        cid = c["id"]
        add(f"#### {cid} — {c['title']}", cid)
        add("")
        checks = ", ".join(c.get("checks", [])) or DASH
        add(f"**Checks:** {checks} · **Type:** {c['type']} · "
            f"**Priority:** {c['priority']}", cid)
        add("")
        if c.get("before"):
            add(f"**Before:** {c['before']}", cid)
            add("")
        for i, step in enumerate(c["steps"], 1):
            add(f"{i}. {step}", cid)
        add("")
        add(f"**Expect:** {c['expect']}", cid)
        add("")
    retired = sorted((c for c in record.get("cases", []) if c.get("status") == "retired"),
                     key=lambda c: tc_num(c.get("id")))
    if retired:
        add("### Retired test cases")
        add("")
        add("*No longer run. Their IDs are never reused.*")
        add("")
        for c in retired:
            add(f"- {c['id']} — {c.get('title', '')}: {c.get('reason', '')}", c["id"])
        add("")
    add("## 9. Coverage")
    add("")
    add("*Each built requirement, and the test cases that check it.*")
    add("")
    add("| ID | Requirement | Test cases |")
    add("|---|---|---|")
    by_row = {}
    for c in cases:
        for rid in c.get("checks", []):
            by_row.setdefault(rid, []).append(c["id"])
    for rid in qa.order:
        if not qa.built(rid):
            continue
        tests = ", ".join(by_row.get(rid, [])) or ("*not tested by hand*" if rid in excluded
                                                     else "**none**")
        add(f"| {rid} | {cell(qa.rows[rid].get('feature', ''))} | {tests} |", "ledger")
    return out


def plan_text(lines):
    body = "\n".join(line for line, _ in lines).rstrip("\n") + "\n\n"
    return body + f"{MARK}{sha(body)} -->\n"


def plan_status(path):
    """missing | generated | hand-edited | hand-written - and the file's body."""
    if not os.path.exists(path):
        return "missing", None, (False, False)
    text, style = read_text(path)
    lines = text.rstrip("\n").split("\n")
    m = MARK_RE.fullmatch(lines[-1]) if lines else None
    if not m:
        return "hand-written", text, style
    body = "\n".join(lines[:-1]) + "\n"
    return ("generated" if sha(body) == m.group(1) else "hand-edited"), text, style


def plan_guard(qa, force):
    status, _, style = plan_status(qa.plan_path)
    if status in ("hand-edited", "hand-written") and not force:
        refuse(f"{qa.plan_path} was changed by hand; carry any change worth keeping into the "
               "record with apply, then rerun with --force")
    return style


# --- checks ---------------------------------------------------------------------------------

def harness_hits(lines, allowed):
    """(where, found, line) for every harness reference not allowed; and the allowed used."""
    hits, used = [], set()
    allow = {(a.get("text"), a.get("where")) for a in allowed}
    for line, where in lines:
        for kind, pattern in REFERENCES:
            for m in pattern.finditer(line):
                if (m.group(0), where) in allow:
                    used.add((m.group(0), where))
                else:
                    hits.append((where, kind, m.group(0), line.strip()))
    return hits, used


def record_problems(qa, record, lines):
    """Problems that stop build, and warnings that do not."""
    problems, warnings = [], []
    secs = record.get("sections", {})
    for key, heading, required in SECTIONS:
        if required and not (secs.get(key) or "").strip():
            problems.append(f"section \"{heading}\" is empty - set {key}")
    excluded = {e.get("id") for e in record.get("excluded", [])}
    cases = active(record)
    covered = {r for c in cases for r in c.get("checks", [])}
    for c in cases:
        problems += case_errors(qa, record, c, c.get("id", "?"))
    for rid in sorted(excluded - set(qa.rows)):
        problems.append(f"excluded {rid} is not a ledger row - unexclude it")
    for rid in qa.order:
        if rid in excluded and rid in covered:
            problems.append(f"{rid} is excluded yet checked by an active case")
    missing = [r for r in qa.order if qa.built(r) and r not in covered and r not in excluded]
    if missing:
        problems.append(f"built but not covered - add a case or exclude it with a reason: "
                        f"{', '.join(missing)}")
    hits, used = harness_hits(lines, record.get("allowed", []))
    for where, kind, found, line in hits:
        problems.append(f"{kind} \"{found}\" in {where}: {line[:120]} - reword it, or, where "
                        "the tester must see that exact text, allow it")
    for a in record.get("allowed", []):
        if (a.get("text"), a.get("where")) not in used:
            warnings.append(f"allowed \"{a.get('text')}\" in {a.get('where')} no longer occurs - "
                            "unallow it")
    confirm = [k for k in SECTION_KEYS if TO_CONFIRM_RE.search(secs.get(k) or "")]
    if confirm:
        warnings.append(f"still marked To confirm: {', '.join(confirm)} - ask the developer "
                        "before the plan goes to a tester")
    return problems, warnings


def latest(record):
    trackers = record.get("trackers", [])
    return trackers[-1] if trackers else None


def tracker_state(qa, entry):
    if entry is None:
        return "none"
    path = os.path.join(qa.qa_dir, entry.get("file", ""))
    if not os.path.exists(path):
        return "missing"
    return "untouched" if file_sha(path) == entry.get("sha256") else "saved"


# --- the tracker ----------------------------------------------------------------------------

def tracker_rows(qa, record, base):
    """[(case id, [cells])] in plan order; cells hold the tool's columns."""
    snap = qa.snapshot()
    rows = []
    for c in ordered_cases(qa, record):
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(c["steps"], 1))
        cells = [c["id"], area_of(qa, c), ", ".join(c.get("checks", [])) or DASH, c["title"],
                 c["type"], c["priority"], c.get("before", ""), steps, c["expect"]]
        h = sha(json.dumps(cells, ensure_ascii=False))
        if base is None:
            flag = DASH
        elif c["id"] not in base.get("cases", {}):
            flag = "New"
        elif base["cases"][c["id"]] != h or any(
                base.get("ledger", {}).get(r) != snap.get(r) for r in c.get("checks", [])):
            flag = "Yes"
        else:
            flag = "No"
        rows.append((c["id"], cells + [flag], h))
    return rows


def xml(text):
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(text))
    if len(text) > 32767:
        die("a tracker cell would exceed Excel's 32,767 characters; shorten that case")
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def str_cell(ref, text, style):
    return (f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{xml(text)}'
            f'</t></is></c>')


def formula_cell(ref, formula, style=0):
    return f'<c r="{ref}" s="{style}"><f>{xml(formula)}</f></c>'


NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
NS_R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

STYLES = HEAD + (
    f'<styleSheet {NS}>'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="4"><fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FFD9E1F2"/><bgColor indexed="64"/>'
    '</patternFill></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FFF2F2F2"/><bgColor indexed="64"/>'
    '</patternFill></fill></fills>'
    '<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>'
    '<border><left style="thin"><color rgb="FFBFBFBF"/></left><right style="thin">'
    '<color rgb="FFBFBFBF"/></right><top style="thin"><color rgb="FFBFBFBF"/></top>'
    '<bottom style="thin"><color rgb="FFBFBFBF"/></bottom><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="6">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" '
    'applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
    '<xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1" '
    'applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" '
    'applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    '<xf numFmtId="9" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    '</cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    '<dxfs count="3">'
    '<dxf><font><color rgb="FF006100"/></font><fill><patternFill><bgColor rgb="FFC6EFCE"/>'
    '</patternFill></fill></dxf>'
    '<dxf><font><color rgb="FF9C0006"/></font><fill><patternFill><bgColor rgb="FFFFC7CE"/>'
    '</patternFill></fill></dxf>'
    '<dxf><font><color rgb="FF9C5700"/></font><fill><patternFill><bgColor rgb="FFFFEB9C"/>'
    '</patternFill></fill></dxf>'
    '</dxfs></styleSheet>')


def cases_sheet(rows):
    last = len(rows) + 1
    end = col(len(COLUMNS) - 1)
    status_col = col([h for h, _, _ in COLUMNS].index("Status"))
    out = [HEAD, f'<worksheet {NS} {NS_R}>',
           '<sheetViews><sheetView tabSelected="1" workbookViewId="0">'
           '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
           '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/></sheetView></sheetViews>',
           '<sheetFormatPr defaultRowHeight="15"/><cols>']
    for i, (_, width, _) in enumerate(COLUMNS, 1):
        out.append(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>')
    out.append('</cols><sheetData><row r="1">')
    out += [str_cell(f"{col(i)}1", h, 1) for i, (h, _, _) in enumerate(COLUMNS)]
    out.append("</row>")
    for n, (_, cells, _) in enumerate(rows, 2):
        values = cells + ["Not run"] + [""] * (len(COLUMNS) - len(cells) - 1)
        out.append(f'<row r="{n}">')
        for i, (value, (_, _, tool)) in enumerate(zip(values, COLUMNS)):
            out.append(str_cell(f"{col(i)}{n}", value, 2 if tool else 3))
        out.append("</row>")
    out.append(f'</sheetData><autoFilter ref="A1:{end}{last}"/>')
    if rows:
        rng = f"{status_col}2:{status_col}{last}"
        out.append(f'<conditionalFormatting sqref="{rng}">')
        for prio, (word, dxf) in enumerate((("Pass", 0), ("Fail", 1), ("Blocked", 2)), 1):
            out.append(f'<cfRule type="cellIs" dxfId="{dxf}" priority="{prio}" '
                       f'operator="equal"><formula>"{word}"</formula></cfRule>')
        out.append('</conditionalFormatting>')
        out.append(f'<dataValidations count="1"><dataValidation type="list" allowBlank="1" '
                   f'showErrorMessage="1" sqref="{rng}"><formula1>"{",".join(STATUSES)}"'
                   '</formula1></dataValidation></dataValidations>')
    out.append('<pageMargins left="0.5" right="0.5" top="0.75" bottom="0.75" header="0.3" '
               'footer="0.3"/></worksheet>')
    return "".join(out)


def summary_sheet(app, version, areas, last):
    heads = [h for h, _, _ in COLUMNS]
    sc = col(heads.index("Status"))
    pc = col(heads.index("Priority"))
    ac = col(heads.index("Area"))
    ref = "'Test cases'!"
    end = max(last, 2)  # every count covers the case rows only, the same rows for every count
    status = f"{ref}${sc}$2:${sc}${end}"
    rows = [[str_cell("A1", f"Test tracker: {app} — version {version}", 4)],
            [str_cell("A3", "Status", 1), str_cell("B3", "Cases", 1)]]
    for i, s in enumerate(STATUSES, 4):
        rows.append([str_cell(f"A{i}", s, 0),
                     formula_cell(f"B{i}", f'COUNTIF({status},"{s}")')])
    total = 4 + len(STATUSES)
    pass_row = 4 + STATUSES.index("Pass")
    rows.append([str_cell(f"A{total}", "Total", 4),
                 formula_cell(f"B{total}", f"COUNTA({ref}$A$2:$A${end})")])
    rows.append([str_cell(f"A{total + 2}", "High priority, not yet passed", 0),
                 formula_cell(f"B{total + 2}",
                              f'COUNTIFS({ref}${pc}$2:${pc}${end},"High",{status},"<>Pass")')])
    rows.append([str_cell(f"A{total + 3}", "Passed, of all cases", 0),
                 formula_cell(f"B{total + 3}",
                              f"IF(B{total}=0,0,B{pass_row}/B{total})", 5)])
    head = total + 5
    rows.append([str_cell(f"{col(i)}{head}", h, 1)
                 for i, h in enumerate(("Area",) + STATUSES + ("Total",))])
    # exact matches: COUNTIF would read * ? ~ and a leading < > = in an area's name as a pattern
    area_rng = f"{ref}${ac}$2:${ac}${end}"
    status_rng = status
    for n, area in enumerate(areas, head + 1):
        cells = [str_cell(f"A{n}", area, 0)]
        for i, s in enumerate(STATUSES, 1):
            cells.append(formula_cell(f"{col(i)}{n}",
                                      f'SUMPRODUCT(({area_rng}=$A{n})*({status_rng}="{s}"))'))
        cells.append(formula_cell(f"{col(len(STATUSES) + 1)}{n}",
                                  f"SUMPRODUCT(--({area_rng}=$A{n}))"))
        rows.append(cells)
    out = [HEAD, f'<worksheet {NS} {NS_R}><sheetViews><sheetView workbookViewId="0"/>'
           '</sheetViews><sheetFormatPr defaultRowHeight="15"/><cols>'
           '<col min="1" max="1" width="34" customWidth="1"/>'
           f'<col min="2" max="{len(STATUSES) + 2}" width="11" customWidth="1"/></cols>'
           '<sheetData>']
    for cells in rows:
        r = re.match(r'<c r="[A-Z]+(\d+)"', cells[0]).group(1)
        out.append(f'<row r="{r}">' + "".join(cells) + "</row>")
    out.append('</sheetData><pageMargins left="0.5" right="0.5" top="0.75" bottom="0.75" '
               'header="0.3" footer="0.3"/></worksheet>')
    return "".join(out)


def xlsx_bytes(app, version, rows, areas):
    last = len(rows) + 1
    end = col(len(COLUMNS) - 1)
    parts = [
        ("[Content_Types].xml", HEAD + '<Types xmlns="http://schemas.openxmlformats.org/'
         'package/2006/content-types"><Default Extension="rels" ContentType="application/'
         'vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" '
         'ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType='
         '"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
         '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/'
         'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName='
         '"/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-'
         'officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" '
         'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"'
         '/></Types>'),
        ("_rels/.rels", HEAD + '<Relationships xmlns="http://schemas.openxmlformats.org/'
         'package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.'
         'openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
         'Target="xl/workbook.xml"/></Relationships>'),
        ("xl/workbook.xml", HEAD + f'<workbook {NS} {NS_R}><bookViews><workbookView/>'
         '</bookViews><sheets><sheet name="Test cases" sheetId="1" r:id="rId1"/>'
         '<sheet name="Summary" sheetId="2" r:id="rId2"/></sheets><definedNames>'
         '<definedName name="_xlnm._FilterDatabase" localSheetId="0" hidden="1">'
         f"'Test cases'!$A$1:${end}${last}</definedName></definedNames>"
         '<calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>'),
        ("xl/_rels/workbook.xml.rels", HEAD + '<Relationships xmlns="http://schemas.'
         'openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://'
         'schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target='
         '"worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.'
         'org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
         '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
         'relationships/styles" Target="styles.xml"/></Relationships>'),
        ("xl/styles.xml", STYLES),
        ("xl/worksheets/sheet1.xml", cases_sheet(rows)),
        ("xl/worksheets/sheet2.xml", summary_sheet(app, version, areas, last)),
    ]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in parts:  # a fixed date, so the same content gives the same bytes
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, text.encode("utf-8"))
    return buf.getvalue()


# --- commands -------------------------------------------------------------------------------

def changes_since(qa, entry):
    """Ledger rows newly built, rebuilt, and new since a tracker's ledger copy."""
    snap, old = qa.snapshot(), (entry or {}).get("ledger", {})
    newly, rebuilt, new = [], [], []
    for rid in qa.order:
        if rid not in old:
            new.append(rid)
        elif qa.built(rid) and not str(old[rid].get("build", "")).startswith("built in"):
            newly.append(rid)
        elif qa.built(rid) and old[rid] != snap[rid]:
            rebuilt.append(f"{rid} ({', '.join(old[rid].get('phases', [])) or DASH} -> "
                           f"{', '.join(snap[rid]['phases'])})")
    return newly, rebuilt, new


def cmd_status(qa, args, flags):
    if args:
        die("status takes no arguments")
    built = [r for r in qa.order if qa.built(r)]
    print(f"ledger: {len(qa.order)} rows, {len(built)} built")
    if qa.record is None:
        print(f"record: none yet - the first apply creates {qa.record_path}")
        print(f"to cover: {', '.join(built) or 'nothing is built yet'}")
        return
    rec = qa.record
    cases = active(rec)
    retired = len(rec.get("cases", [])) - len(cases)
    by = ", ".join(f"{p} {sum(1 for c in cases if c.get('priority') == p)}" for p in PRIORITIES)
    print(f"record: {qa.record_path} (updated {rec.get('updated', '?')})")
    print(f"cases: {len(cases)} active ({by}), {retired} retired; "
          f"{len(rec.get('excluded', []))} rows not tested by hand")
    excluded = {e.get("id") for e in rec.get("excluded", [])}
    covered = {r for c in cases for r in c.get("checks", [])}
    missing = [r for r in built if r not in covered and r not in excluded]
    print(f"not covered (built, no case, not excluded): {', '.join(missing) or 'none'}")
    entry = latest(rec)
    state = tracker_state(qa, entry)
    words = {"none": "none written yet", "untouched": "exactly as written (build may replace it)",
             "saved": "saved by the tester (never overwritten; a change makes the next version)",
             "missing": "not found in qa/ (moved or sent; a change makes the next version)"}
    print(f"tracker: {entry['file'] + ' - ' if entry else ''}{words[state]}")
    if entry:
        newly, rebuilt, new = changes_since(qa, entry)
        print(f"since that tracker: newly built {', '.join(newly) or 'none'}; rebuilt "
              f"{'; '.join(rebuilt) or 'none'}; new rows {', '.join(new) or 'none'}")
    status, _, _ = plan_status(qa.plan_path)
    print(f"plan: {qa.plan_path} - {status}")
    confirm = [k for k in SECTION_KEYS if TO_CONFIRM_RE.search(rec.get("sections", {}).get(k)
                                                                or "")]
    print(f"to confirm: {', '.join(confirm) or 'none'}")


def cmd_apply(qa, args, flags):
    if len(args) != 1 or not args[0].startswith("@"):
        die('apply takes one "@FILE" (in double quotes)')
    values = read_values(args[0])
    if not isinstance(values, dict) or not values:
        die("the values file must hold a JSON object with any of: " + ", ".join(APPLY_KEYS))
    unknown = sorted(set(values) - set(APPLY_KEYS))
    if unknown:
        die(f"unknown key(s) {', '.join(unknown)}; allowed: {', '.join(APPLY_KEYS)}")
    rec = json.loads(json.dumps(qa.record)) if qa.record is not None else qa.new_record()
    errs, report = [], []
    cases = {c.get("id"): c for c in rec.setdefault("cases", [])}

    def entries(key, kind=dict):
        v = values.get(key, [])
        if not isinstance(v, list) or not all(isinstance(x, kind) for x in v):
            errs.append(f"{key} must be a list of {'objects' if kind is dict else 'ids'}")
            return []
        return v

    sets = values.get("set", {})
    if not isinstance(sets, dict):
        errs.append("set must be an object")
        sets = {}
    for key, text in sets.items():
        text = text_of(text)
        if key not in SECTION_KEYS:
            errs.append(f"set: {key} is not a section; one of {', '.join(SECTION_KEYS)}")
        elif not isinstance(text, str):
            errs.append(f"set: {key} must be text or a list of lines")
        else:
            rec.setdefault("sections", {})[key] = text.strip()
            report.append(f"set {key}")
    excluded = rec.setdefault("excluded", [])
    for e in entries("retire"):
        c = cases.get(e.get("id"))
        if not c or c.get("status", "active") != "active":
            errs.append(f"retire: {e.get('id')} is not an active case")
        elif not isinstance(e.get("reason"), str) or not e["reason"].strip():
            errs.append(f"retire {e.get('id')}: a reason is required")
        else:
            c["status"], c["reason"] = "retired", e["reason"].strip()
            report.append(f"retired {c['id']}")
    for rid in entries("unexclude", str):
        if not any(x.get("id") == rid for x in excluded):
            errs.append(f"unexclude: {rid} is not excluded")
        excluded[:] = [x for x in excluded if x.get("id") != rid]
        report.append(f"unexcluded {rid}")
    for e in entries("edit"):
        c = cases.get(e.get("id"))
        bad = sorted(set(e) - set(CASE_FIELDS) - {"id"})
        if not c or c.get("status", "active") != "active":
            errs.append(f"edit: {e.get('id')} is not an active case")
            continue
        if bad:
            errs.append(f"edit {c['id']}: unknown field(s) {', '.join(bad)}")
            continue
        merged = normalise_case({**{k: c[k] for k in CASE_FIELDS if k in c},
                                 **{k: v for k, v in e.items() if k != "id"}})
        found = case_errors(qa, rec, merged, f"edit {c['id']}")
        if found:
            errs += found
        else:
            c.update(merged)
            report.append(f"edited {c['id']}")
    for e in entries("exclude"):
        rid, reason = e.get("id"), e.get("reason")
        users = [c["id"] for c in active(rec) if rid in c.get("checks", [])]
        if rid not in qa.rows:
            errs.append(f"exclude: {rid} is not a ledger row")
        elif not isinstance(reason, str) or not reason.strip():
            errs.append(f"exclude {rid}: a reason is required")
        elif users:
            errs.append(f"exclude {rid}: checked by {', '.join(users)} - retire or edit those")
        else:
            excluded[:] = [x for x in excluded if x.get("id") != rid]
            excluded.append({"id": rid, "reason": reason.strip()})
            report.append(f"excluded {rid}")
    added = []
    for i, e in enumerate(entries("add"), 1):
        bad = sorted(set(e) - set(CASE_FIELDS))
        if bad:
            errs.append(f"add #{i}: unknown field(s) {', '.join(bad)} (the tool gives out ids)")
            continue
        case = normalise_case(e)
        found = case_errors(qa, rec, case, f"add #{i} ({case.get('title', '?')})")
        if found:
            errs += found
            continue
        nxt = max([rec.get("nextId", 1)] + [tc_num(x) + 1 for x in cases])
        case = {"id": f"TC-{nxt}", **case, "status": "active"}
        rec["nextId"] = nxt + 1
        rec["cases"].append(case)
        cases[case["id"]] = case
        added.append(case["id"])
    if added:
        report.append(f"added {added[0]}" + (f"..{added[-1]}" if len(added) > 1 else "")
                      + f" ({len(added)})")
    allowed = rec.setdefault("allowed", [])
    places = set(SECTION_KEYS) | {"ledger"} | set(cases)
    for a in entries("allow"):
        text, where, reason = a.get("text"), a.get("where"), a.get("reason")
        if not all(isinstance(x, str) and x.strip() for x in (text, where, reason)):
            errs.append("allow: text, where and reason are all required")
        elif where not in places:
            errs.append(f"allow \"{text}\": where must be a case id, a section "
                        f"({', '.join(SECTION_KEYS)}) or ledger - got {where}")
        else:
            allowed[:] = [x for x in allowed if (x.get("text"), x.get("where")) != (text, where)]
            allowed.append({"text": text, "where": where, "reason": reason.strip()})
            report.append(f"allowed \"{text}\" in {where}")
    for a in entries("unallow"):
        key = (a.get("text"), a.get("where"))
        if not any((x.get("text"), x.get("where")) == key for x in allowed):
            errs.append(f"unallow: \"{key[0]}\" in {key[1]} is not allowed")
        allowed[:] = [x for x in allowed if (x.get("text"), x.get("where")) != key]
        report.append(f"unallowed \"{key[0]}\" in {key[1]}")
    if errs:
        refuse("nothing written:\n  " + "\n  ".join(errs))
    rec["updated"] = date.today().isoformat()
    style = plan_guard(qa, "--force" in flags)
    entry = latest(rec)
    lines = render_plan(qa, rec, entry and entry.get("file"), entry and entry.get("version"))
    write_all([(qa.record_path, encode(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")),
               (qa.plan_path, encode(plan_text(lines), style))])
    for line in report:
        print(line)
    print(f"wrote {qa.record_path} and {qa.plan_path}; run check, then build")


def cmd_check(qa, args, flags):
    if args:
        die("check takes no arguments")
    if qa.record is None:
        refuse(f"no record yet ({qa.record_path}); the first apply creates it")
    entry = latest(qa.record)
    lines = render_plan(qa, qa.record, entry and entry.get("file"), entry and entry.get("version"))
    problems, warnings = record_problems(qa, qa.record, lines)
    status, text, _ = plan_status(qa.plan_path)
    if status in ("hand-edited", "hand-written"):
        problems.append(f"{qa.plan_path} was changed by hand - carry the change into the record "
                        "with apply, then build --force")
    elif status == "missing" or text.replace("\r\n", "\n") != plan_text(lines):
        warnings.append("the plan is out of date - build rewrites it")
    state = tracker_state(qa, entry)
    write, version, _, _ = tracker_decision(qa, qa.record)
    if state == "none":
        warnings.append("no tracker yet - build writes it")
    elif write == "replace":
        warnings.append(f"{entry['file']} is out of date - build rewrites it in place (no "
                        "tester has saved it)")
    elif write == "new":
        warnings.append(f"{entry['file']} is out of date - build writes the next version, "
                        f"v{version}")
    elif state == "missing":
        warnings.append(f"{entry['file']} is not in qa/ - the next change makes a new version")
    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print(f"- {p}")
        for w in warnings:
            print(f"warning: {w}")
        sys.exit(1)
    cases = active(qa.record)
    print(f"ok: {len(cases)} active cases; every built requirement covered or excluded")
    for w in warnings:
        print(f"warning: {w}")


def areas_of(qa, record):
    areas = []
    for c in ordered_cases(qa, record):
        if area_of(qa, c) not in areas:
            areas.append(area_of(qa, c))
    return areas


def tracker_decision(qa, record):
    """What build would do with the tracker: (write, version, base, note).
    write is None (keep it), "replace" (the latest, still exactly as written) or "new"."""
    trackers = record.get("trackers", [])
    entry = trackers[-1] if trackers else None
    state = tracker_state(qa, entry)
    if state == "none":
        return "new", 1, None, ""
    if state == "untouched":
        base = trackers[-2] if len(trackers) > 1 else None
        data = xlsx_bytes(qa.app, entry["version"], tracker_rows(qa, record, base),
                          areas_of(qa, record))
        if sha(data) == entry.get("sha256"):
            return None, entry["version"], base, f"{entry['file']} unchanged"
        return "replace", entry["version"], base, ""
    rows = tracker_rows(qa, record, entry)
    if (any(cells[-1] != "No" for _, cells, _ in rows)
            or {cid for cid, _, _ in rows} != set(entry.get("cases", {}))):
        return "new", entry["version"] + 1, entry, ""
    return None, entry["version"], entry, (
        f"{entry['file']} kept: nothing in it would change"
        + (" (it is not in qa/ - moved or sent?)" if state == "missing" else ""))


def cmd_build(qa, args, flags):
    if args:
        die("build takes no arguments")
    rec = qa.record
    if rec is None:
        refuse(f"no record yet ({qa.record_path}); write cases with apply first")
    rec = json.loads(json.dumps(rec))
    trackers = rec.setdefault("trackers", [])
    write, version, base, note = tracker_decision(qa, rec)
    areas = areas_of(qa, rec)
    file_name = os.path.basename(qa.tracker_path(version))
    lines = render_plan(qa, rec, file_name, version)
    problems, warnings = record_problems(qa, rec, lines)
    if problems:
        refuse("build needs a clean record - fix these with apply:\n  - " + "\n  - ".join(problems))
    style = plan_guard(qa, "--force" in flags)
    items = []
    if write:
        rows = tracker_rows(qa, rec, base)
        data = xlsx_bytes(qa.app, version, rows, areas)
        new_entry = {"version": version, "file": file_name, "date": date.today().isoformat(),
                     "sha256": sha(data), "cases": {cid: h for cid, _, h in rows},
                     "ledger": qa.snapshot()}
        if write == "replace":
            trackers[-1] = new_entry
        else:
            trackers.append(new_entry)
        items.append((qa.tracker_path(version), data))
        items.append((qa.record_path,
                      encode(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")))
        changed = sum(1 for _, cells, _ in rows if cells[-1] in ("Yes", "New"))
        note = (f"{'replaced' if write == 'replace' else 'wrote'} {file_name}: {len(rows)} cases"
                + (f", {changed} marked changed or new since v{base['version']}" if base else ""))
    items.append((qa.plan_path, encode(plan_text(lines), style)))
    write_all(items)
    print(note)
    print(f"wrote {qa.plan_path}")
    for w in warnings:
        print(f"warning: {w}")


COMMANDS = {
    "status": (cmd_status, set()),
    "apply": (cmd_apply, {"--force"}),
    "check": (cmd_check, set()),
    "build": (cmd_build, {"--force"}),
}


def main(argv):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="ascii", errors="backslashreplace")
    try:
        run(argv)
    finally:
        remove_read_values()


def run(argv):
    ensure_tmp_dir()
    state_path = None
    if argv[:1] == ["--file"]:
        if len(argv) < 2:
            die("--file needs a path")
        state_path, argv = argv[1], argv[2:]
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    func, allowed = COMMANDS[argv[0]]
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if flags - allowed:
        die(f"{argv[0]} does not take {', '.join(sorted(flags - allowed))}")
    qa = QA(state_path or find_state())
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):  # a command prints only after its writes succeed
            func(qa, args, flags)
    finally:  # check's findings print before its exit status; a refusal has printed nothing
        sys.stdout.write(out.getvalue())


if __name__ == "__main__":
    main(sys.argv[1:])
