#!/usr/bin/env python3
"""Update the feature ledger and the plan without hand-editing either.

Usage: python docs.py [--file STATE] [--plan PATH] <feature|plan> <command> ...

The feature ledger: features.json is the record; FEATURE_STATUS.md is a view it generates.
  feature show [P-N | E-N | ID ... | group=<title>]   rows a phase/edit touched, named, or in a group
  feature add ID "feature=..." [k=v ...] | @FILE   new row(s), untested; creates features.json
  feature set ID k=v ... | ID @FILE | @FILE        update row(s) in place
  feature set P-N "tested=passed" --developer-said every row reading "built in P-N" except a
                                      failed one; those, and untested rows that list P-N but were
                                      built elsewhere, are named, not changed
  feature add-group "<title>"         a new, empty group, last
  feature count [P-N | E-N ...]       built-and-untested by phase, failed, totals; scoped if given
  feature check                       schema, values, ids, state.json cross-checks, the view
  feature import PATH                 one time: turn a Markdown FEATURE_STATUS.md into features.json
  feature render                      rewrite FEATURE_STATUS.md (every write already does)
The plan: PLAN_<App>.md stays Markdown.
  plan show P-N ...                   print each phase's section 5 subsection
  plan complete P-N "<summary>" ...   move a done phase out of section 5 into a section 2 line
  plan replace @FILE                  exact old->new pairs, each old found exactly once; all or none
  plan check                          the headings this tool relies on are present and parse

The ledger: app, schemaVersion, preamble (lines), groups ([{title, before, after}] - lines
around each group's table), features (rows). A row: id, feature, howToCheck (lines), phases
(P-N / E-N that built or changed it, in order), build (unscheduled | scheduled in P-N |
built in P-N), tested (untested | passed YYYY-MM-DD |
failed YYYY-MM-DD \\u2014 <symptom>), and optionally group (a groups title; group= ungroups).
The view renders the preamble, the ungrouped rows, then each group as "## <title>", its before
text, its table and its after text. In k=v, howToCheck takes one line (several: @FILE with a
JSON list), and phases=P-4,E-2 appends the ids not yet there - ids are never removed.
@FILE for add: a JSON list of rows; for set: a list of {"id": ..., fields} or one object of
fields after an ID. A date left out of passed/failed is today's.
Rules, refused: no row is ever deleted; an id never changes; build and tested take only the
values above; a row is never scheduled in a done phase or built in a pending one; and tested is
written as passed or failed only with --developer-said - which you pass only when the developer
said so in this chat. The tool cannot check that; the flag is a speed bump, not proof.
A FEATURE_STATUS.md changed by hand is never overwritten silently: writes are refused until
--force (which overwrites it) - first carry any change worth keeping into features.json.
feature import takes every ledger table in the file, in order; the first heading naming
"Feature Status" is the title, a heading with a ledger table under it starts a group, and other
text (other headings included) is kept as the preamble or a group's before/after. It refuses,
by line, what it cannot place - any "|" line outside a code block that is not part of a ledger
table (a blank line inside a table; a header that is not the six columns). tested is taken only
exactly as above - it never fills in a date. It prints the rows per group.
A phase subsection runs from its heading to the next phase heading or the end of section 5
(headings in code blocks never count). Inside a phase, a heading at or above its level that is
not the template's own (Tasks, What is testable, Developer test guide, Exit criteria,
[P-N.T-M]) is ambiguous and refused - except after the last phase, where it ends that phase, as
does a non-template heading one level down after the last phase's Exit criteria. plan complete
refuses a phase that is not done in state.json, refuses a removal that would split a code block
or strand a template heading, and prints the headings it removed; every plan write stops on a
structure plan check cannot delimit safely, including a code fence never closed. plan replace @FILE holds a JSON list of
{"old": ..., "new": ...}.

state.json is found as state.py finds it (--file overrides) and is only read; features.json,
FEATURE_STATUS.md and PLAN_<project>.md sit beside it (--plan overrides the plan's path).
Values files go in .harness-tmp/ under the working-tree root, which this tool and state.py
create (it ignores itself in git); a path outside the repo works too. k=v and @FILE turn a
\\u2014-style escape back into its character. Output is ASCII; writes are UTF-8, keep the
file's line endings, go through a temp file, and nothing is printed until they succeed.
"""
import contextlib
import hashlib
import io
import json
import os
import re
import sys
from datetime import date

SKIP_DIRS = {".git", "node_modules", "bin", "obj", "target", "dist", "ModernizationHarness"}
TMP_DIR = ".harness-tmp"
FIELDS = ("id", "feature", "howToCheck", "phases", "build", "tested")
ROW_KEYS = FIELDS + ("group",)  # group is optional: the title of a groups[] entry
DASH = "—"
UNIT_RE = re.compile(r"[PE]-\d+")
PHASE_RE = re.compile(r"P-\d+")
BUILD_RE = re.compile(r"unscheduled|(scheduled|built) in (P-\d+)")
TESTED_RE = re.compile(r"untested|passed (\d{4}-\d{2}-\d{2})|failed (\d{4}-\d{2}-\d{2}) — \S.*")
MARK = "<!-- generated by tools/docs.py from features.json - do not edit; ask the agent. sha256:"
MARK_RE = re.compile(re.escape(MARK) + r"([0-9a-f]{64}) -->")
FIX_VIEW = ("carry any change worth keeping into features.json with `feature set ... --force` "
            "(passed/failed only on the developer's word), or discard it with "
            "`feature render --force`; a ledger never migrated is `feature import`")


def die(msg):
    """A malformed command: fix it and rerun."""
    sys.exit(f"docs.py: {msg}")


def refuse(msg):
    """A rule speaking: never work around it."""
    sys.exit(f"docs.py: refused: {msg}")


def ensure_tmp_dir():
    """.harness-tmp/ at the working-tree root holds values files; its .gitignore hides it."""
    try:
        os.makedirs(TMP_DIR, exist_ok=True)
        ignore = os.path.join(TMP_DIR, ".gitignore")
        if not os.path.exists(ignore):
            with open(ignore, "w", encoding="ascii", newline="\n") as f:
                f.write("*\n")
    except OSError:
        pass  # a read-only tree still runs every command


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
        die(f"could not write: {e}; " + (f"{done} were written - run `feature check`"
                                          if done else "nothing written"))


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Docs:
    def __init__(self, state_path, plan_path):
        self.state_path = state_path
        self.state = load_json(state_path)
        if not isinstance(self.state, dict):
            die(f"{state_path} must hold a JSON object")
        self.dir = os.path.dirname(state_path) or "."
        self.features = os.path.join(self.dir, "features.json")
        self.view = os.path.join(self.dir, "FEATURE_STATUS.md")
        self._plan = plan_path

    def phase(self, pid):
        return next((p for p in self.state.get("phases", []) if p.get("id") == pid), None)

    def unit_exists(self, uid):
        kind = "phases" if uid.startswith("P-") else "edits"
        return any(e.get("id") == uid for e in self.state.get(kind, []))

    def plan_path(self):
        if self._plan:
            return self._plan
        own = os.path.join(self.dir, f"PLAN_{self.state.get('project')}.md")
        if os.path.exists(own):
            return own
        hits = [f for f in os.listdir(self.dir) if f.startswith("PLAN_") and f.endswith(".md")]
        if len(hits) != 1:
            die(f"found {len(hits)} PLAN_*.md files beside {self.state_path}; pass --plan PATH")
        return os.path.join(self.dir, hits[0])


# --- input ----------------------------------------------------------------------------------

def unescape(raw):
    # \uXXXX is how output shows non-ASCII; decode each run as JSON so a copied value
    # round-trips, including two-code characters such as emoji (the same rule as state.py)
    return re.sub(r"(?:\\u[0-9a-fA-F]{4})+", lambda m: json.loads(f'"{m.group(0)}"'), raw)


def is_file_arg(args):
    return len(args) == 1 and args[0].startswith("@")


def read_values(arg):
    value = load_json(arg[1:])
    return unescape_tree(value)


def unescape_tree(v):
    if isinstance(v, str):
        return unescape(v)
    if isinstance(v, list):
        return [unescape_tree(x) for x in v]
    if isinstance(v, dict):
        return {k: unescape_tree(x) for k, x in v.items()}
    return v


def parse_pairs(args):
    fields = {}
    for arg in args:
        if "=" not in arg:
            die(f"expected key=value or @FILE, got {arg!r}")
        key, raw = arg.split("=", 1)
        raw = unescape(raw)
        if key == "howToCheck":
            if raw.startswith("["):
                try:
                    raw = json.loads(raw)
                except ValueError as e:
                    die(f"howToCheck: not a JSON list: {e}")
            else:
                raw = [raw] if raw else []
        elif key == "phases":
            raw = [p.strip() for p in raw.split(",") if p.strip()]
        fields[key] = raw
    if not fields:
        die("nothing to write")
    return fields


def norm_build(v):
    if not isinstance(v, str):
        return None
    v = " ".join(v.split())
    return v if BUILD_RE.fullmatch(v) else None


def norm_tested(v):
    """Canonical tested text, filling today's date when left out; None if not a valid value."""
    if not isinstance(v, str):
        return None
    v = " ".join(v.split())
    today = date.today().isoformat()
    m = re.fullmatch(r"passed(?: (\d{4}-\d{2}-\d{2}))?", v)
    if m:
        v = f"passed {m.group(1) or today}"
    m = re.fullmatch(r"failed(?: (\d{4}-\d{2}-\d{2}))? ?(?:—|–|--|-|:) ?(\S.*)", v)
    if m:
        v = f"failed {m.group(1) or today} {DASH} {m.group(2)}"
    m = TESTED_RE.fullmatch(v)
    if not m:
        return None
    try:
        for d in m.groups()[:2]:
            if d:
                date.fromisoformat(d)
    except ValueError:
        return None
    return v


# --- the ledger -----------------------------------------------------------------------------

def shape_problems(row):
    """Malformed: what makes a row not a row. Shared by add, set, import and check."""
    rid = row.get("id")
    out = [f"{rid}: unknown field {k!r} (fields: {', '.join(ROW_KEYS)})" for k in row
           if k not in ROW_KEYS]
    if "group" in row and (not isinstance(row["group"], str) or not row["group"].strip()):
        out.append(f"{rid}: group must be a group's title")
    if not isinstance(rid, str) or not rid.strip() or rid != rid.strip() or "|" in rid \
            or "\n" in rid or rid.startswith(("@", "-")) or UNIT_RE.fullmatch(rid or ""):
        out.append(f"bad id {rid!r}: text, no '|', not a phase or edit id")
    if not isinstance(row.get("feature"), str) or not row["feature"].strip():
        out.append(f"{rid}: feature must be non-empty text")
    checks = row.get("howToCheck")
    if not isinstance(checks, list) or not all(isinstance(c, str) and "\n" not in c for c in checks):
        out.append(f"{rid}: howToCheck must be a list of one-line texts")
    units = row.get("phases")
    if not isinstance(units, list) or not all(isinstance(u, str) and UNIT_RE.fullmatch(u) for u in units):
        out.append(f"{rid}: phases must be a list of P-N / E-N ids")
    elif len(units) != len(set(units)):
        out.append(f"{rid}: phases lists an id twice")
    if not isinstance(row.get("build"), str) or norm_build(row["build"]) != row["build"]:
        out.append(f"{rid}: build must be unscheduled, scheduled in P-N or built in P-N, "
                   f"got {row.get('build')!r}")
    if not isinstance(row.get("tested"), str) or norm_tested(row["tested"]) != row["tested"]:
        out.append(f"{rid}: tested must be untested, passed YYYY-MM-DD or failed YYYY-MM-DD "
                   f"\\u2014 <symptom>, got {row.get('tested')!r}")
    return out


def state_problems(docs, row, strict):
    """Cross-checks against state.json, as (malformed, rule breaks). A malformed one names an
    id state.json does not have; a rule break is refused. strict (check) adds consistency."""
    bad, rules, rid = [], [], row.get("id")
    for u in row.get("phases") or []:
        if isinstance(u, str) and not docs.unit_exists(u):
            bad.append(f"{rid}: phases names {u}, which state.json does not have")
    m = BUILD_RE.fullmatch(row.get("build") or "")
    if m and m.group(2):
        kind, pid = m.group(1), m.group(2)
        p = docs.phase(pid)
        if p is None:
            if pid in docs.state.get("droppedPhases", []):
                rules.append(f"{rid}: {kind} in {pid}, which is dropped - re-point it")
            else:
                bad.append(f"{rid}: {kind} in {pid}, which is not in state.json")
        elif kind == "scheduled" and p.get("status") == "done":
            rules.append(f"{rid}: scheduled in {pid}, which is done - re-point it to a remaining "
                         "phase or unscheduled")
        elif kind == "built" and p.get("status") == "pending":
            rules.append(f"{rid}: built in {pid}, which has not started")
        if kind == "built" and strict and pid not in (row.get("phases") or []):
            rules.append(f"{rid}: built in {pid} but phases does not list {pid}")
    return bad, rules


def stop_on(bad, rules):
    """Malformed first (fix and rerun), then rule breaks (refused)."""
    if bad:
        die("\n".join(bad))
    if rules:
        refuse("\n".join(rules))


def load_ledger(docs, create=False, validate=True):
    if not os.path.exists(docs.features):
        if not create:
            die(f"no features.json beside {docs.state_path}; Stage 3 creates it with "
                "`feature add`, and `feature import` migrates a Markdown FEATURE_STATUS.md")
        if os.path.exists(docs.view):
            refuse(f"{docs.view} exists but features.json does not: migrate it first with "
                   "`feature import`, so no row is lost")
        return {"app": docs.state.get("project"), "schemaVersion": 1, "features": []}, (False, False)
    _, style = read_text(docs.features)  # line endings to keep
    ledger = load_json(docs.features)
    if not isinstance(ledger, dict) or not isinstance(ledger.get("features"), list):
        die(f"{docs.features} must hold an object with a features list")
    if validate:
        bad = [p for r in ledger["features"]
               for p in (shape_problems(r) if isinstance(r, dict) else [f"not a row: {r!r}"])]
        bad += ledger_problems(ledger)
        if bad:
            die(f"{docs.features} has malformed rows; `feature check` lists them:\n" + "\n".join(bad))
    return ledger, style


def table_lines(rows):
    def cell(s):
        return " ".join(str(s).split()).replace("|", "\\|")

    out = ["| ID | Feature | How to check | Phase(s) | Build | Tested |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| " + " | ".join([
            cell(r["id"]), cell(r["feature"]),
            "<br>".join(cell(c) for c in r["howToCheck"]) or DASH,
            ", ".join(r["phases"]) or DASH, r["build"], cell(r["tested"])]) + " |")
    return out


def render(ledger):
    """The view: title and note; the preamble; ungrouped rows (always a table when there are no
    groups); then each group in order as a '## <title>' heading, its before text, its table
    (a header-only table when it has no rows, so the text around it keeps its place) and its
    after text. Blocks are separated by one blank line."""
    rows, groups = ledger["features"], ledger.get("groups") or []
    blocks = [ledger["preamble"]] if ledger.get("preamble") else []
    ungrouped = [r for r in rows if not r.get("group")]
    if ungrouped or not groups:
        blocks.append(table_lines(ungrouped))
    for g in groups:
        blocks.append([f"## {g['title']}"])
        blocks += [g["before"]] if g.get("before") else []
        blocks.append(table_lines([r for r in rows if r.get("group") == g["title"]]))
        blocks += [g["after"]] if g.get("after") else []
    lines = [f"# Feature Status: {ledger.get('app')}", "",
             "*What has been built, how to check it, and what the developer has tested. Rows are "
             "never deleted.", f"Generated from `features.json` by `tools/docs.py` {DASH} do not "
             "edit this file; tell the agent what you tested.*"]
    for block in blocks:
        lines += [""] + block
    body = "\n".join(lines) + "\n"
    return f"{MARK}{sha(body)} -->\n{body}"


def view_status(docs):
    """('missing' | 'hand-written' | 'hand-edited' | 'ours', LF text, style)."""
    if not os.path.exists(docs.view):
        return "missing", None, (False, False)
    text, style = read_text(docs.view)
    first, _, body = text.partition("\n")
    m = MARK_RE.fullmatch(first)
    if not m:
        return "hand-written", text, style
    return ("ours" if sha(body) == m.group(1) else "hand-edited"), text, style


def save_ledger(docs, ledger, style, force):
    status, _, view_style = view_status(docs)
    if status in ("hand-written", "hand-edited") and not force:
        refuse(f"{docs.view} was changed by hand since docs.py wrote it; nothing written. "
               f"Recover: {FIX_VIEW}")
    data = encode(json.dumps(ordered(ledger), indent=2, ensure_ascii=False) + "\n",
                  (False, style[1]))
    write_all([(docs.features, data), (docs.view, encode(render(ledger), view_style))])


def take_flags(args, allowed):
    flags = {a for a in args if a.startswith("--")}
    bad = flags - allowed
    if bad:
        die(f"unknown option(s) {sorted(bad)} here; allowed: {sorted(allowed) or 'none'}")
    return [a for a in args if a not in flags], flags


def touched(row, units):
    m = BUILD_RE.fullmatch(row["build"])
    return bool(set(row["phases"]) & units) or bool(m and m.group(2) in units)


def apply_fields(docs, row, fields, developer, groups=()):
    """Update one row in place (a copy is passed), applying every rule.
    Returns (malformed, rule breaks)."""
    problems = []
    for key, value in fields.items():
        if key == "id":
            if value != row["id"]:
                refuse(f"{row['id']}: ids are permanent; never changed")
            continue
        if key not in ROW_KEYS:
            problems.append(f"{row['id']}: unknown field {key!r} (fields: {', '.join(ROW_KEYS)})")
            continue
        if key == "group":
            if value in ("", None):
                row.pop("group", None)
            elif value not in groups:
                problems.append(f"{row['id']}: no group {value!r} - `feature add-group` creates one")
            else:
                row["group"] = value
            continue
        if key == "phases":
            value = [value] if isinstance(value, str) else value
            if isinstance(value, list):
                value = row["phases"] + [u for u in value if u not in row["phases"]]
        elif key == "howToCheck" and isinstance(value, str):
            value = [value] if value else []
        elif key == "build":
            value = norm_build(value) or value
        elif key == "tested":
            canon = norm_tested(value)
            if canon and canon != "untested" and canon != row["tested"] and not developer:
                refuse(f"{row['id']}: tested={canon!r} needs --developer-said. Only the developer "
                       "authorizes passed or failed (AGENTS.md invariant 5); you may write only "
                       "untested")
            value = canon or value
        row[key] = value
    bad, rules = state_problems(docs, row, strict=False)
    return problems + shape_problems(row) + bad, rules


def cmd_feature_add(docs, args, flags):
    if is_file_arg(args):
        rows = read_values(args[0])
        rows = [rows] if isinstance(rows, dict) else rows
        if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
            die(f"{args[0][1:]} must hold a JSON list of rows")
    elif len(args) >= 2:
        rows = [{"id": unescape(args[0]), **parse_pairs(args[1:])}]
    else:
        die("add needs ID and fields (at least feature=...), or @FILE")
    ledger, style = load_ledger(docs, create=True)
    have = {r.get("id") for r in ledger["features"]}
    problems, rules, added = [], [], []
    for given in rows:
        row = {"howToCheck": [], "phases": [], "build": "unscheduled", "tested": "untested"}
        for key, value in given.items():
            if key == "phases" and isinstance(value, str):
                value = [u.strip() for u in value.split(",") if u.strip()]
            elif key == "howToCheck" and isinstance(value, str):
                value = [value] if value else []
            elif key == "build":
                value = norm_build(value) or value
            elif key == "tested":
                value = norm_tested(value) or value
            row[key] = value
        if row.get("id") in have:
            refuse(f"{row.get('id')} is already a row; change it with `feature set`, ids are unique")
        if row["tested"] != "untested":
            refuse(f"{row.get('id')}: a new row is untested; only the developer marks one tested")
        if "group" in row and row["group"] not in [g.get("title") for g in ledger.get("groups", [])]:
            problems.append(f"{row.get('id')}: no group {row['group']!r} - `feature add-group` "
                            "creates one")
        bad, broken = state_problems(docs, row, strict=False)
        problems += shape_problems(row) + bad
        rules += broken
        have.add(row.get("id"))
        added.append({**{k: row[k] for k in FIELDS if k in row},  # schema order, id first
                      **{k: v for k, v in row.items() if k not in FIELDS}})
    stop_on(problems, rules)
    ledger["features"] += added
    save_ledger(docs, ledger, style, "--force" in flags)
    for row in added:
        print(f"added {row['id']}")



def cmd_feature_set(docs, args, flags):
    developer = "--developer-said" in flags
    notes = []
    ledger, style = load_ledger(docs)
    by_id = {r["id"]: r for r in ledger["features"] if isinstance(r, dict) and "id" in r}
    if is_file_arg(args):
        raw = read_values(args[0])
        if isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(v, dict) and "id" in v and v["id"] != k:
                    refuse(f"{k}: its fields carry id {v['id']!r}; ids are permanent, never changed")
            raw = [{**v, "id": k} if isinstance(v, dict) else None for k, v in raw.items()]
        if not isinstance(raw, list) or not raw or not all(isinstance(r, dict) and "id" in r for r in raw):
            die(f"{args[0][1:]} must hold a list of {{\"id\": ..., fields}} or an object of id -> fields")
        updates = [(r["id"], {k: v for k, v in r.items() if k != "id"}) for r in raw]
    elif len(args) >= 2:
        sel = unescape(args[0])
        fields = read_values(args[1]) if is_file_arg(args[1:]) else parse_pairs(args[1:])
        if not isinstance(fields, dict):
            die(f"{args[1][1:]} must hold a JSON object of fields")
        if PHASE_RE.fullmatch(sel):
            if set(fields) != {"tested"}:
                die(f"set {sel} takes only tested=... (it sets every row reading built in {sel})")
            built = [r for r in ledger["features"] if r.get("build") == f"built in {sel}"]
            ids = [r["id"] for r in built if not r.get("tested", "").startswith("failed")]
            kept = [r["id"] for r in built if r["id"] not in ids]
            if kept:
                notes.append(f"note: left failed, not changed: {', '.join(kept)} - ask whether "
                             "each was re-tested; name a row to change it")
            also = [r["id"] for r in ledger["features"] if sel in r.get("phases", [])
                    and r.get("build") != f"built in {sel}" and r.get("tested") == "untested"]
            if also:
                notes.append(f"note: {sel} also changed these untested rows, built in another "
                             f"phase: {', '.join(also)} - read them back and ask whether to tick "
                             "them too")
            if not ids:
                print(f"no row to change reads built in {sel}; nothing written")
                for n in notes:
                    print(n)
                return
            updates = [(i, dict(fields)) for i in ids]
        else:
            updates = [(sel, fields)]
    else:
        die("set needs ID (or P-N) and fields, or @FILE")
    problems, rules, changed = [], [], []
    for rid, fields in updates:
        if rid not in by_id:
            die(f"no row {rid!r}; a new row is `feature add`")
        if not fields:
            die(f"{rid}: nothing to write")
        row = json.loads(json.dumps(by_id[rid]))
        bad, broken = apply_fields(docs, row, fields, developer,
                                   [g.get("title") for g in ledger.get("groups", [])])
        problems += bad
        rules += broken
        by_id[rid] = row
        changed.append(rid)
    stop_on(problems, rules)
    ledger["features"] = [by_id.get(r.get("id"), r) for r in ledger["features"]]
    save_ledger(docs, ledger, style, "--force" in flags)
    for rid in changed:
        print(json.dumps(by_id[rid]))
    for n in notes:
        print(n)


def cmd_feature_show(docs, args, flags):
    ledger, _ = load_ledger(docs)
    rows = ledger["features"]
    wanted = [unescape(a.split("=", 1)[1]) for a in args if a.startswith("group=")]
    args = [a for a in args if not a.startswith("group=")]
    if wanted:
        titles = [g.get("title") for g in ledger.get("groups", [])]
        unknown = [w for w in wanted if w not in titles]
        if unknown:
            die(f"no group {unknown}")
        rows = [r for r in rows if r.get("group") in wanted]
    if args:
        units = {a for a in args if UNIT_RE.fullmatch(a)}
        ids = [unescape(a) for a in args if not UNIT_RE.fullmatch(a)]
        missing = [i for i in ids if i not in {r["id"] for r in rows}]
        if missing:
            die(f"no row {missing}")
        rows = [r for r in rows if r["id"] in ids or (units and touched(r, units))]
    for r in rows:
        print(json.dumps(r))
    if not rows:
        print("no rows")


def cmd_feature_count(docs, args, flags):
    ledger, _ = load_ledger(docs)
    rows = ledger["features"]
    bad = [a for a in args if not UNIT_RE.fullmatch(a)]
    if bad:
        die(f"count takes P-N / E-N ids only, got {bad}")
    if args:
        rows = [r for r in rows if touched(r, set(args))]
        print(f"scope: rows touched by {', '.join(args)}")
    kinds = {"built": 0, "scheduled": 0, "unscheduled": 0}
    waiting, failed, passed = {}, [], 0
    for r in rows:
        m = BUILD_RE.fullmatch(r["build"])
        kinds[m.group(1) or "unscheduled"] += 1
        if m.group(1) == "built" and r["tested"] == "untested":
            waiting.setdefault(m.group(2), []).append(r["id"])
        if r["tested"].startswith("failed"):
            failed.append(r["id"])
        passed += r["tested"].startswith("passed")
    total = sum(len(v) for v in waiting.values())
    print(f"rows: {len(rows)} (built {kinds['built']}, scheduled {kinds['scheduled']}, "
          f"unscheduled {kinds['unscheduled']})")
    print(f"awaiting testing (built, untested): {total}" + (" - " + ", ".join(
        f"{p}: {len(v)} ({', '.join(v)})" for p, v in waiting.items()) if total else ""))
    print(f"failed: {len(failed)}" + (f" ({', '.join(failed)})" if failed else ""))
    print(f"passed: {passed}")


def cmd_feature_check(docs, args, flags):
    ledger, _ = load_ledger(docs, validate=False)
    problems = [] if ledger.get("app") else ["features.json: app missing"]
    problems += ledger_problems(ledger)
    ids = [r.get("id") for r in ledger["features"] if isinstance(r, dict)]
    problems += [f"duplicate id {i}" for i in sorted({i for i in ids if ids.count(i) > 1}, key=str)]
    for r in ledger["features"]:
        if not isinstance(r, dict):
            problems.append(f"not a row: {r!r}")
            continue
        shape = shape_problems(r)
        problems += shape or sum(state_problems(docs, r, strict=True), [])
    status, text, _ = view_status(docs)
    if status == "missing":
        problems.append("FEATURE_STATUS.md is missing - run `feature render`")
    elif status != "ours":
        problems.append(f"FEATURE_STATUS.md was changed by hand - {FIX_VIEW}")
    elif not problems and text != render(ledger):
        problems.append("FEATURE_STATUS.md is out of date - run `feature render`")
    if problems:
        die("\n".join(problems))
    print(f"ok ({len(ids)} rows)")


def cmd_feature_render(docs, args, flags):
    ledger, style = load_ledger(docs)
    save_ledger(docs, ledger, style, "--force" in flags)
    print(f"rendered {docs.view} ({len(ledger['features'])} rows)")


def ledger_problems(ledger):
    """Malformed preamble, groups, or a row's group naming no group."""
    out = []
    pre = ledger.get("preamble", [])
    if not isinstance(pre, list) or not all(isinstance(l, str) and "\n" not in l for l in pre):
        out.append("preamble must be a list of one-line texts")
    groups = ledger.get("groups", [])
    titles = []
    if not isinstance(groups, list):
        out.append("groups must be a list")
        groups = []
    for g in groups:
        t = g.get("title") if isinstance(g, dict) else None
        if not isinstance(t, str) or not t.strip() or t != t.strip() or "\n" in t:
            out.append(f"group {g!r}: title must be one line of text")
            continue
        if t in titles:
            out.append(f"group {t!r} appears twice")
        titles.append(t)
        for k in ("before", "after"):
            v = g.get(k, [])
            if not isinstance(v, list) or not all(isinstance(l, str) and "\n" not in l for l in v):
                out.append(f"group {t!r}: {k} must be a list of one-line texts")
        out += [f"group {t!r}: unknown field {k!r}" for k in g if k not in ("title", "before", "after")]
    for r in ledger.get("features", []):
        if isinstance(r, dict) and "group" in r and r["group"] not in titles:
            out.append(f"{r.get('id')}: group {r['group']!r} is not in groups - "
                       "`feature add-group` creates one")
    return out


def ordered(ledger):
    """Top-level keys in schema order; empty preamble and groups left out."""
    out = {k: ledger[k] for k in ("app", "schemaVersion") if k in ledger}
    out.update({k: ledger[k] for k in ("preamble", "groups") if ledger.get(k)})
    out["features"] = ledger["features"]
    out.update({k: v for k, v in ledger.items() if k not in out and k not in ("preamble", "groups")})
    return out


def cmd_feature_add_group(docs, args, flags):
    if len(args) != 1 or not unescape(args[0]).strip():
        die('add-group takes one title: feature add-group "<title>"')
    title = " ".join(unescape(args[0]).split())
    ledger, style = load_ledger(docs)
    groups = ledger.setdefault("groups", [])
    if any(g.get("title") == title for g in groups):
        refuse(f"group {title!r} already exists")
    groups.append({"title": title, "before": [], "after": []})
    save_ledger(docs, ledger, style, "--force" in flags)
    print(f"added group {title}")


HEAD_NAMES = {"id": "id", "feature": "feature", "how to check": "howToCheck",
              "phase(s)": "phases", "phases": "phases", "build": "build", "tested": "tested"}
def is_separator(line):
    """A Markdown table's |---|---| line."""
    s = line.strip()
    return s.startswith("|") and "---" in s and not s.strip("|:- ")


def split_row(line):
    s = line.strip()[1:]  # drop the leading |
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def plain(cell):
    """A cell without emphasis, its leading keyword (Built in, Passed) in lower case."""
    s = " ".join(re.sub(r"[*`]", "", cell).split())
    return re.sub(r"(?i)^(unscheduled|scheduled in|built in|untested|passed|failed)\b",
                  lambda m: m.group(1).lower(), s)


def ledger_header(line):
    """The column order if this line is a ledger table's header row, else None."""
    if not line.lstrip().startswith("|"):
        return None
    names = [plain(c).lower() for c in split_row(line)]
    if sorted(HEAD_NAMES.get(n, n) for n in names) != sorted(FIELDS):
        return None
    return [HEAD_NAMES[n] for n in names]


def parse_row(docs, cols, line):
    raw = dict(zip(cols, split_row(line)))
    empty = {"", "-", "—", "–"}
    row = {"id": plain(raw["id"]), "feature": raw["feature"],
           "howToCheck": [] if raw["howToCheck"] in empty else
           [c.strip() for c in re.split(r"(?i)<br\s*/?>", raw["howToCheck"]) if c.strip()],
           "phases": [] if plain(raw["phases"]) in empty else
           [u for u in re.split(r"[,;\s]+", plain(raw["phases"])) if u],
           "build": norm_build(plain(raw["build"])) or plain(raw["build"]),
           "tested": plain(raw["tested"])}  # exact: a date is never invented here
    return row, shape_problems(row) + state_problems(docs, row, strict=False)[0]


def trim(lines):
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def squeeze(lines):
    """Trim blank lines at both ends and collapse each run of blank lines outside a code block
    to one."""
    out, code = [], dict(fences(lines))
    for i, line in enumerate(lines):
        if line.strip() or code.get(i) or (out and out[-1].strip()):
            out.append(line if line.strip() or code.get(i) else "")
    return trim(out)


def stray_table_lines(lines, code, table):
    """Problems for each run of '|' lines outside a code block that no ledger table took."""
    out, i = [], 0
    while i < len(lines):
        if code.get(i) or i in table or not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        j = i
        while j < len(lines) and not code.get(j) and j not in table \
                and lines[j].lstrip().startswith("|"):
            j += 1
        where = f"line {i + 1}" if j == i + 1 else f"lines {i + 1}-{j}"
        p = i - 1
        while p >= 0 and not lines[p].strip():
            p -= 1
        if p >= 0 and p in table and p < i - 1:
            why = f"a blank line splits the ledger table above (line {p + 2}); remove it"
        elif j - i >= 2 and is_separator(lines[i + 1]):
            why = ("this table's header is not the six ledger columns (ID | Feature | How to "
                   "check | Phase(s) | Build | Tested): " + " | ".join(split_row(lines[i]))
                   + " - rename or remove the extra column, or put a table that is not part of "
                   "the ledger in a code block")
        else:
            why = ("a table row outside any ledger table - join it to its table, or put it in a "
                   "code block")
        out.append(f"{where}: {why}")
        i = j
    return out


def parse_ledger_md(docs, text):
    """Every ledger table in the file, in order, with the text around it.
    Returns (rows, preamble, groups, problems, notes, counts)."""
    lines = text.split("\n")
    code = dict(fences(lines))
    heads = sorted(i for i, _, _ in headings(lines))
    title = next((i for i in heads if "feature status" in lines[i].lower()), None)
    skip = set()  # lines regenerated by render: the marker, the title, the generated note
    if lines and MARK_RE.fullmatch(lines[0]):
        skip.add(0)
    if title is not None:
        skip.add(title)
        j = title + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        k = j
        while k < len(lines) and lines[k].strip() and k not in heads:
            k += 1
        para = " ".join(lines[j:k])
        if para.startswith("*") and "what has been built" in para.lower():
            skip.update(range(j, k))
    rows, problems, notes = [], [], []
    # a heading starts a group only when a ledger table follows it before the next heading;
    # any other heading (a legend, a sub-note) is kept as text where it stands
    tabled = set()
    for n, h in enumerate(heads):
        nxt = heads[n + 1] if n + 1 < len(heads) else len(lines)
        if h != title and any(not code.get(i) and ledger_header(lines[i]) for i in range(h + 1, nxt)):
            tabled.add(h)
    untabled = [lines[h].strip() for h in heads if h != title and h not in tabled]
    if untabled:
        notes.append(f"note: heading(s) with no ledger table kept as text: {'; '.join(untabled)}")
    levels = sorted({len(lines[h]) - len(lines[h].lstrip("#")) for h in tabled})
    if levels and levels != [2]:
        notes.append(f"note: group headings at {', '.join('#' * l for l in levels)} are shown "
                     "as ## under the title")
    preamble, groups, placed, consumed, table = [], [], set(), set(skip), set()
    group, seen_table = None, False  # group None: the ungrouped area before the first group
    i = 0
    while i < len(lines):
        line = lines[i]
        if i in skip:
            i += 1
            continue
        if i in tabled:
            group = {"title": " ".join(line.lstrip("#").split()), "before": [], "after": []}
            if not group["title"]:
                problems.append(f"line {i + 1}: a heading with no title")
            groups.append(group)
            consumed.add(i)
            seen_table = False
            i += 1
            continue
        cols = None if code.get(i) else ledger_header(line)
        if cols:
            if i + 1 >= len(lines) or not is_separator(lines[i + 1]):
                problems.append(f"line {i + 2}: a ledger table's header is not followed by |---|")
                consumed.add(i)
                table.add(i)
                i += 1
                continue
            name = group["title"] if group else "(ungrouped)"
            if seen_table:
                notes.append(f"note: {name} has more than one table; they become one, and the "
                             "text between them now follows it")
            seen_table = True
            consumed.update((i, i + 1))
            table.update((i, i + 1))
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = split_row(lines[i])
                consumed.add(i)
                table.add(i)
                if len(cells) != len(cols):
                    problems.append(f"line {i + 1}: {len(cells)} cells, expected {len(cols)}: "
                                    f"{lines[i].strip()}")
                else:
                    row, bad = parse_row(docs, cols, lines[i])
                    problems += [f"line {i + 1} ({row['id']}): {p}" for p in bad]
                    if group:
                        row["group"] = group["title"]
                    rows.append(row)
                i += 1
            continue
        if group is None:
            if seen_table and line.strip() and not notes_moved(notes):
                notes.append("note: text after the ungrouped table now sits above it")
            preamble.append(line)
        else:
            (group["after"] if seen_table else group["before"]).append(line)
        placed.add(i)
        i += 1
    problems += stray_table_lines(lines, code, table)
    titles = [g["title"] for g in groups]
    problems += [f"two group headings read {t!r}; rename one" for t in sorted(set(titles))
                 if titles.count(t) > 1]
    lost = [i for i, l in enumerate(lines) if l.strip() and i not in consumed | placed]
    problems += [f"line {i + 1}: cannot be placed: {lines[i].strip()}" for i in lost]
    for g in groups:
        g["before"], g["after"] = squeeze(g["before"]), squeeze(g["after"])
    counts = [("(ungrouped)", sum(1 for r in rows if "group" not in r))] + \
        [(g["title"], sum(1 for r in rows if r.get("group") == g["title"])) for g in groups]
    return rows, squeeze(preamble), groups, problems, notes, counts


def notes_moved(notes):
    return any("now sits above it" in n for n in notes)


def cmd_feature_import(docs, args, flags):
    if len(args) != 1:
        die("import takes the path of the Markdown FEATURE_STATUS.md")
    if os.path.exists(docs.features):
        refuse(f"{docs.features} already exists; import runs once - use `feature set`")
    source = args[0]
    text, _ = read_text(source)
    same = os.path.exists(docs.view) and os.path.samefile(source, docs.view)
    status = view_status(docs)[0]
    if not same and status in ("hand-written", "hand-edited") and "--force" not in flags:
        refuse(f"{docs.view} exists and is not the file being imported; nothing written")
    rows, preamble, groups, problems, notes, counts = parse_ledger_md(docs, text)
    ids = [r["id"] for r in rows]
    problems += [f"duplicate id {d}" for d in sorted({d for d in ids if ids.count(d) > 1})]
    if not rows:
        problems.append(f"{source}: no ledger table rows (columns ID | Feature | How to check | "
                        "Phase(s) | Build | Tested)")
    if problems:
        die("cannot import; nothing written - fix these in the Markdown file and rerun:\n"
            + "\n".join(problems))
    ledger = ordered({"app": docs.state.get("project"), "schemaVersion": 1,
                      "preamble": preamble, "groups": groups, "features": rows})
    items = [(docs.features, encode(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"))]
    backup = None
    if os.path.exists(docs.view) and status != "ours":
        backup = docs.view + ".bak"
        if os.path.exists(backup):
            refuse(f"{backup} already exists; move it away first, nothing written")
        with open(docs.view, "rb") as f:
            items.append((backup, f.read()))
    view_style = read_text(docs.view)[1] if os.path.exists(docs.view) else (False, False)
    items.append((docs.view, encode(render(ledger), view_style)))
    write_all(items)
    print(f"imported {len(rows)} rows: {', '.join(ids)}")
    shown = [(n, c) for n, c in counts if n != "(ungrouped)" or c]
    print("rows per group: " + "; ".join(f"{n}: {c}" for n, c in shown) + f"; total {len(rows)}")
    if backup:
        print(f"the Markdown original is kept as {backup}")
    for n in notes:
        print(n)
    for r in rows:
        for p in state_problems(docs, r, strict=True)[1]:
            print(f"warning: {p} - fix it with `feature set`")


# --- the plan -------------------------------------------------------------------------------

SECTION_RE = re.compile(r"## +(\d+)\.?(?: |$)")
PHASE_HEAD_RE = re.compile(r"(#{2,4}) +(?:Phase +)?(P-\d+)(?![\d.])")
ITEM_RE = re.compile(r"\s*[-*] +\**(P-\d+)(?!\d)")
RULE_RE = re.compile(r"\s*(-{3,}|\*{3,}|_{3,})\s*")
# the phase template's own subsection headings, and task headings ([P-N.T-M])
OWN_HEAD_RE = re.compile(r"#+ +(Tasks|What is testable|Developer test guide|Exit criteria|"
                         r"\[P-\d+\.T-\d+\])", re.I)


def fences(lines):
    """Yield (index, inside a code block) for each line; fence lines count as inside."""
    fence = None
    for i, line in enumerate(lines):
        s = line.lstrip()
        if s.startswith(("```", "~~~")):
            mark = s[:3]
            yield i, True
            fence = None if fence == mark else (fence or mark)
            continue
        yield i, fence is not None


def open_fence(lines):
    """Index of a code fence that is never closed, or None."""
    start, fence = None, None
    for i, line in enumerate(lines):
        s = line.lstrip()
        if s.startswith(("```", "~~~")):
            mark = s[:3]
            if fence is None:
                start, fence = i, mark
            elif fence == mark:
                start, fence = None, None
    return start


def headings(lines):
    """[(index, level, text)] for every heading outside a fenced block."""
    return [(i, len(lines[i]) - len(lines[i].lstrip("#")), lines[i])
            for i, inside in fences(lines) if not inside and re.match(r"#{1,6} ", lines[i])]


def plan_map(lines):
    """Sections 2 and 5, and each phase subsection in 5: {'2': (a, b), '5': (a, b),
    'phases': {P-N: (a, b)}, 'completed': {P-N: index}, 'problems': [...]}."""
    heads = headings(lines)
    numbered = [(i, SECTION_RE.match(t).group(1)) for i, lvl, t in heads
                if lvl == 2 and SECTION_RE.match(t)]
    out = {"phases": {}, "completed": {}, "problems": []}
    for num in ("2", "5"):
        hits = [k for k, (i, n) in enumerate(numbered) if n == num]
        if len(hits) != 1:
            out["problems"].append(f"expected one '## {num}.' heading, found {len(hits)}")
            continue
        k = hits[0]
        end = numbered[k + 1][0] if k + 1 < len(numbered) else len(lines)
        out[num] = (numbered[k][0], end)
    opened = open_fence(lines)
    if opened is not None:
        out["problems"].append(f"line {opened + 1}: a code fence is never closed")
    if "5" in out:
        a, b = out["5"]
        inner = [(i, lvl, t) for i, lvl, t in heads if a < i < b]
        starts = [(i, lvl, PHASE_HEAD_RE.match(t).group(2)) for i, lvl, t in inner
                  if PHASE_HEAD_RE.match(t)]
        levels = {lvl for _, lvl, _ in starts}
        if len(levels) > 1:
            out["problems"].append("section 5's phase headings mix levels "
                                   f"({', '.join('#' * l for l in sorted(levels))}); use one")
        # A phase runs to the next phase heading or the end of section 5; headings in code
        # blocks never count. A heading at or above the phase level that is not the template's
        # own is ambiguous inside a phase, so it is refused - except after the last phase,
        # where it ends that phase. So does, after the last phase's Exit criteria, a
        # non-template heading one level down (trailing notes).
        for n, (i, lvl, pid) in enumerate(starts):
            last = n + 1 == len(starts)
            end = b if last else starts[n + 1][0]
            exit_seen = False
            for j, l2, t in inner:
                if not i < j < end:
                    continue
                own = OWN_HEAD_RE.match(t)
                exit_seen = exit_seen or bool(own and own.group(1).lower() == "exit criteria")
                if own or l2 > lvl + 1 or (l2 == lvl + 1 and not (last and exit_seen)):
                    continue
                if last:
                    end = j
                    break
                out["problems"].append(f"line {j + 1}: heading {t.strip()!r} inside {pid} is not "
                                       "part of the phase template and not below the phase "
                                       f"heading's level, so where {pid} ends is unclear")
            if pid in out["phases"]:
                out["problems"].append(f"{pid} has two subsections in section 5")
            out["phases"][pid] = (i, end)
        if not out["phases"] and any(PHASE_RE.search(t) for _, _, t in inner):
            out["problems"].append("section 5 names phases but no heading reads "
                                   "'## Phase P-N: <name>'")
    if "2" in out:
        a, b = out["2"]
        for i in range(a + 1, b):
            m = ITEM_RE.match(lines[i])
            if m:
                out["completed"][m.group(1)] = i
    return out


def load_plan(docs):
    path = docs.plan_path()
    text, style = read_text(path)
    return path, text.split("\n"), style


def need(pm, *nums):
    """Stop on any structure the tool cannot delimit safely, not only a missing section."""
    if pm["problems"] or any(n not in pm for n in nums):
        die("the plan cannot be parsed safely; nothing written: " + "; ".join(pm["problems"])
            + " - run `plan check`")


def cmd_plan_show(docs, args, flags):
    if not args or not all(PHASE_RE.fullmatch(a) for a in args):
        die("show takes one or more P-N")
    _, lines, _ = load_plan(docs)
    pm = plan_map(lines)
    need(pm, "5")
    for pid in args:
        if pid in pm["phases"]:
            a, b = pm["phases"][pid]
            print("\n".join(lines[a:b]).rstrip("\n"))
        elif pid in pm["completed"]:
            print(f"(in section 2 Completed) {lines[pm['completed'][pid]].strip()}")
        else:
            die(f"{pid} is not in section 5 or section 2")
        print()


def block_check(lines, pm, pid, a, b):
    """Refuse a removal that would split a code block or strand part of the phase."""
    def stop(why):
        die(f"{pid}: cannot delimit safely; nothing written - {why}")

    opened = open_fence(lines[a:b])
    if opened is not None:
        stop(f"line {a + opened + 1}: the phase's code fence is not closed inside it")
    later = [s for s, _ in pm["phases"].values() if s > a]
    nxt = min(later) if later else pm["5"][1]
    for j, _, t in headings(lines):
        if b <= j < nxt and OWN_HEAD_RE.match(t):
            stop(f"line {j + 1}: {t.strip()!r} would be left behind, cut off from its phase")
    rest = lines[:a] + lines[b:]
    s5, e5 = pm["5"]
    opened = open_fence(rest[s5:e5 - (b - a)])
    if opened is not None:
        stop("what would remain of section 5 has a code fence that is never closed")


def cmd_plan_complete(docs, args, flags):
    if not args or len(args) % 2:
        die('complete takes pairs: P-N "<one-line summary>" ...')
    pairs = [(args[k], unescape(args[k + 1]).strip()) for k in range(0, len(args), 2)]
    path, lines, style = load_plan(docs)
    removed = {}
    for pid, summary in pairs:
        if not PHASE_RE.fullmatch(pid):
            die(f"expected P-N, got {pid!r}")
        if not summary or "\n" in summary:
            die(f"{pid}: the summary is one non-empty line")
        p = docs.phase(pid)
        if p is None:
            die(f"{pid} is not in state.json")
        if p.get("status") != "done":
            refuse(f"{pid} is {p.get('status')}; only a done phase moves to section 2 Completed")
        pm = plan_map(lines)
        need(pm, "2", "5")
        if pid not in pm["phases"]:
            if pid in pm["completed"]:
                refuse(f"{pid} is already in section 2 Completed")
            die(f"{pid} has no subsection in section 5 - run `plan check`")
        a, b = pm["phases"][pid]
        block_check(lines, pm, pid, a, b)
        removed[pid] = [t.strip() for _, _, t in headings(lines[a:b])]
        del lines[a:b]
        while a < len(lines) and a > 0 and not lines[a].strip() and not lines[a - 1].strip():
            del lines[a]
        pm = plan_map(lines)
        s, e = pm["2"]
        entry = f"- {pid} {DASH} {p.get('name')} {DASH} {summary}"
        region = lines[s + 1:e]
        items = [k for k, l in enumerate(region) if ITEM_RE.match(l)]
        if items:
            region.insert(items[-1] + 1, entry)
        else:
            body = [l for l in region  # a placeholder, bare or as a list item, goes
                    if re.sub(r"[*_.\s]", "", re.sub(r"^\s*[-*+]\s+", "", l)).lower()
                    not in ("noneyet", "none", "nothingyet")]
            while body and not body[0].strip():
                body.pop(0)
            tail = []  # a closing rule (---) stays last
            while body and (not body[-1].strip() or RULE_RE.fullmatch(body[-1])):
                line = body.pop()
                if line.strip():
                    tail.insert(0, line)
            region = [""] + body + ([""] if body else []) + [entry, ""] + (tail + [""] if tail else [])
        lines[s + 1:e] = region
    write_all([(path, encode("\n".join(lines), style))])
    for pid, _ in pairs:
        print(f"{pid} moved to section 2 Completed; removed: {' | '.join(removed[pid])}")


def cmd_plan_replace(docs, args, flags):
    if not is_file_arg(args):
        die("replace takes @FILE: a JSON list of {\"old\": ..., \"new\": ...}")
    pairs = read_values(args[0])
    if isinstance(pairs, dict) and "pairs" in pairs:
        pairs = pairs["pairs"]
    if not isinstance(pairs, list) or not pairs:
        die(f"{args[0][1:]} must hold a JSON list of {{\"old\": ..., \"new\": ...}}")
    path, lines, style = load_plan(docs)
    text, problems = "\n".join(lines), []
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


def cmd_plan_check(docs, args, flags):
    _, lines, _ = load_plan(docs)
    pm = plan_map(lines)
    problems, notes = list(pm["problems"]), []
    for pid in pm["phases"]:
        p = docs.phase(pid)
        if p is None:
            problems.append(f"section 5 has {pid}, which state.json does not have")
        elif p.get("status") == "done":
            notes.append(f"note: {pid} is done and still in section 5 - `plan complete` moves it "
                         "(the phase a run just finished stays until the next run)")
        if pid in pm["completed"]:
            problems.append(f"{pid} is in both section 2 and section 5")
    if "5" in pm:
        for p in docs.state.get("phases", []):
            if p.get("status") != "done" and p.get("id") not in pm["phases"]:
                problems.append(f"{p.get('id')} is {p.get('status')} in state.json but has no "
                                "subsection in section 5")
    if problems:
        die("\n".join(problems + notes))
    print(f"ok: section 5 has {', '.join(pm['phases']) or 'no phases'}; section 2 lists "
          f"{', '.join(pm['completed']) or 'none'}")
    for n in notes:
        print(n)


COMMANDS = {
    ("feature", "show"): (cmd_feature_show, set(), True),
    ("feature", "add"): (cmd_feature_add, {"--force"}, False),
    ("feature", "add-group"): (cmd_feature_add_group, {"--force"}, False),
    ("feature", "set"): (cmd_feature_set, {"--force", "--developer-said"}, False),
    ("feature", "count"): (cmd_feature_count, set(), True),
    ("feature", "check"): (cmd_feature_check, set(), True),
    ("feature", "import"): (cmd_feature_import, {"--force"}, False),
    ("feature", "render"): (cmd_feature_render, {"--force"}, False),
    ("plan", "show"): (cmd_plan_show, set(), True),
    ("plan", "complete"): (cmd_plan_complete, set(), False),
    ("plan", "replace"): (cmd_plan_replace, set(), False),
    ("plan", "check"): (cmd_plan_check, set(), True),
}


def main(argv):
    for stream in (sys.stdout, sys.stderr):  # ASCII survives any console encoding
        stream.reconfigure(encoding="ascii", errors="backslashreplace")
    ensure_tmp_dir()
    state_path = plan_path = None
    while argv[:1] in (["--file"], ["--plan"]):
        if len(argv) < 2:
            die(f"{argv[0]} needs a path")
        if argv[0] == "--file":
            state_path = argv[1]
        else:
            plan_path = argv[1]
        argv = argv[2:]
    if tuple(argv[:2]) not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    func, allowed, _ = COMMANDS[tuple(argv[:2])]
    args, flags = take_flags(argv[2:], allowed)
    docs = Docs(state_path or find_state(), plan_path)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):  # hold the result back until every write succeeds
        func(docs, args, flags)
    sys.stdout.write(out.getvalue())


if __name__ == "__main__":
    main(sys.argv[1:])
