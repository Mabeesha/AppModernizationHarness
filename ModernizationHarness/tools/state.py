#!/usr/bin/env python3
"""Read and write the harness state.json without loading the whole file into an agent.

Usage: python state.py [--file PATH] <command> ...

  start                       begin a Stage 4 run: summary, new, context, phases, edits,
                              stages.plan, the marks to write at hand-off, the input
                              documents' paths
  summary                     one-screen overview: stages, phases, edits, marks, counts
  get [PATH]                  print the value at PATH (whole file if omitted)
  new                         changeLog / reviews entries above the progress high-water marks
  add LIST k=v ... | @FILE    append to changeLog, reviews, edits or phases; id and utc filled in
  set PATH k=v ... | @FILE    update fields on the object at PATH
  drop phases.P-<n>           remove a pending phase (plan refresh only)
  check                       validate the file against the harness rules

add fills id, utc and the schema defaults, and requires:
  phases name | edits summary afterPhase | changeLog author origin summary |
  reviews target result blockerCount findingsCount
  author: developer, implement-agent, review-agent; origin: developer-prompt, reconcile,
  out-of-band, review-R-<n>; result: clean, findings. A phase's name never changes.

start writes nothing and is one command, so it needs no chaining in any shell. Its marks line
is what to write at hand-off if the run folds in everything new printed. It looks documents up
in context.locations.documents (relative to the current directory - run it from the
working-tree root, like every command; state.json lives in that folder) by their conventional
names, <AppName> being project, and prints each as required or optional, and found, missing or
ambiguous; a missing one still exits 0. A documents location not found from here prints one
line saying so in place of the documents; one that does not hold this state.json prints a
stop-and-ask line.

PATH is dotted; a list segment matches an element by id, e.g. phases.P-3 or changeLog.12.
A value is text, except: null; the integer fields (progress marks, rerunCount, blockerCount,
findingsCount); the true/false fields (sharedDataStore, sharedWithLegacy); the list fields
(prUrls, docsTouched, phasesAffected, editsAffected), which take a,b,c; and sizeReport, which
takes a JSON object. A wrong type is refused. Quote the whole pair when it has spaces:
"summary=fixed the export header".
Nested objects or text with quotes: write a JSON object of fields to a UTF-8 file and pass
@FILE in place of the pairs. Put the file in .harness-tmp/ under the working-tree root - this
tool (and docs.py) creates that folder with a .gitignore of "*", so it never reaches git - or
anywhere outside the repo; deleting it after use is optional. Never pipe JSON in: Windows
PowerShell 5.1 turns non-ASCII characters into "?" on the way.
Output is ASCII; a non-ASCII character prints as an escape such as \\u2014, and both k=v and
@FILE turn that escape back into the character, so a copied value round-trips. (So k=v text
cannot hold a literal backslash-u plus four hex digits; use @FILE with "\\\\u" for that.)
Nothing is printed until the write has succeeded.
Without --file, state.json is found by name under the current directory.

Examples:
  set phases.P-4 "status=in progress"
  set progress lastProcessedChangeLogId=12 lastProcessedReviewNumber=3
  add changeLog author=developer origin=out-of-band "summary=..." phasesAffected=P-2
  add reviews target=P-3 result=findings blockerCount=1 findingsCount=4   (prints R-<n>)
"""
import contextlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

STATUS_ORDER = ["pending", "in progress", "done"]
STAGE_STATUSES = {"pending", "in progress", "complete"}
LIST_FIELDS = {"prUrls", "docsTouched", "phasesAffected", "editsAffected"}
INT_FIELDS = {"lastProcessedChangeLogId", "lastProcessedReviewNumber", "rerunCount",
              "blockerCount", "findingsCount", "schemaVersion"}
BOOL_FIELDS = {"sharedDataStore", "sharedWithLegacy"}
OBJECT_FIELDS = {"sizeReport"}
APPEND_ONLY = {"changeLog", "reviews"}
PREFIX = {"reviews": "R-", "edits": "E-", "phases": "P-"}
# fields an entry must carry, beyond the id and defaults the script fills in
REQUIRED = {
    "phases": ("name",),
    "edits": ("summary", "afterPhase"),
    "changeLog": ("author", "origin", "summary"),
    "reviews": ("target", "result", "blockerCount", "findingsCount"),
}
# field -> (test, what it must be), for fields with a fixed set of values
ALLOWED = {
    "author": (lambda v: v in ("developer", "implement-agent", "review-agent"),
               "developer, implement-agent or review-agent"),
    "origin": (lambda v: v in ("developer-prompt", "reconcile", "out-of-band")
               or bool(re.fullmatch(r"review-R-\d+", str(v))),
               "developer-prompt, reconcile, out-of-band or review-R-<n>"),
    "result": (lambda v: v in ("clean", "findings"), "clean or findings"),
}
SKIP_DIRS = {".git", "node_modules", "bin", "obj", "target", "dist", "ModernizationHarness"}
TMP_DIR = ".harness-tmp"  # values files; ignores itself in git
STATE_PATH = None  # the state file this run read; set by main, used by start


def die(msg):
    sys.exit(f"state.py: {msg}")


def ensure_tmp_dir():
    """Create .harness-tmp/ with a .gitignore of "*" where missing; no git command needed."""
    try:
        os.makedirs(TMP_DIR, exist_ok=True)
        ignore = os.path.join(TMP_DIR, ".gitignore")
        if not os.path.exists(ignore):
            with open(ignore, "w", encoding="ascii", newline="\n") as f:
                f.write("*\n")
    except OSError:
        pass  # a read-only tree still runs every command


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_file():
    hits = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if "state.json" in files:
            hits.append(os.path.join(root, "state.json"))
    if len(hits) != 1:
        die(f"found {len(hits)} state.json files {hits}; pass --file PATH")
    return hits[0]


def load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except ValueError as e:
        die(f"{path} is not valid JSON: {e}")


def save(path, state):
    state["updatedUtc"] = now()
    try:  # encode before touching disk, so a bad value writes nothing at all
        data = (json.dumps(state, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    except UnicodeEncodeError:
        die("text contains a broken character (half of a \\ud83d\\ude00-style pair?); nothing written")
    tmp = path + ".tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except OSError as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        die(f"could not write {path}: {e}; nothing written")


def num(id_):
    """R-10 -> 10, 7 -> 7. Ids are compared as numbers, never as text."""
    return int(str(id_).rsplit("-", 1)[-1])


def resolve(state, path):
    node = state
    for seg in path.split(".") if path else []:
        if isinstance(node, list):
            match = [e for e in node if isinstance(e, dict) and str(e.get("id")) == seg]
            if not match:
                die(f"no element with id {seg} in {path}")
            node = match[0]
        elif isinstance(node, dict) and seg in node:
            node = node[seg]
        else:
            die(f"no such path: {path}")
    return node


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)  # bool is an int in Python


def json_or_text(s):
    try:
        return json.loads(s)
    except ValueError:
        return s


# field -> (convert text from k=v, accept the result, what it must be)
RULES = {
    **{k: (lambda s: int(s) if s.lstrip("-").isdigit() else s, is_int, "an integer")
       for k in INT_FIELDS},
    **{k: (lambda s: {"true": True, "false": False}.get(s, s), lambda v: isinstance(v, bool),
           "true or false") for k in BOOL_FIELDS},
    **{k: (lambda s: [v for v in s.split(",") if v], lambda v: isinstance(v, list), "a list")
       for k in LIST_FIELDS},
    **{k: (json_or_text, lambda v: v is None or isinstance(v, dict), "a JSON object or null")
       for k in OBJECT_FIELDS},
}


def coerce(key, value):
    """Give a field its schema type: text from k=v is converted; anything else must already fit."""
    if key not in RULES:
        return value
    convert, ok, kind = RULES[key]
    if isinstance(value, str):
        value = convert(value)
    if not ok(value):
        die(f"{key} must be {kind}, got {value!r}")
    return value


def parse_fields(args):
    if len(args) == 1 and args[0].startswith("@"):
        try:
            with open(args[0][1:], "rb") as f:
                fields = json.loads(f.read())  # bytes: detects UTF-8/16/32 and a BOM itself
        except (OSError, ValueError) as e:
            die(f"cannot read {args[0][1:]}: {e}")
        if not isinstance(fields, dict):
            die(f"{args[0][1:]} must hold a JSON object")
    else:
        fields = {}
        for arg in args:
            if "=" not in arg:
                die(f"expected key=value or @FILE, got {arg!r}")
            key, raw = arg.split("=", 1)
            # \uXXXX is how output shows non-ASCII; decode each run as JSON so a copied value
            # round-trips, including two-code characters such as emoji (😀)
            raw = re.sub(r"(?:\\u[0-9a-fA-F]{4})+", lambda m: json.loads(f'"{m.group(0)}"'), raw)
            fields[key] = None if raw == "null" else raw
    if not fields:
        die("nothing to write")
    return {k: coerce(k, v) for k, v in fields.items()}


def entry_problems(kind, entry):
    """What is missing or out of range on one entry; shared by add and check."""
    problems = [f"{entry.get('id', 'new entry')}: missing {k}" for k in REQUIRED.get(kind, ())
                if entry.get(k) in (None, "")]
    for k, (ok, kind_) in ALLOWED.items():
        if k in entry and not ok(entry[k]):
            problems.append(f"{entry.get('id', 'new entry')}: {k} must be {kind_}, got {entry[k]!r}")
    return problems


def check_status(kind, old, new):
    if kind == "stages":
        if new not in STAGE_STATUSES:
            die(f"stage status must be one of {sorted(STAGE_STATUSES)}")
        return
    if new not in STATUS_ORDER:
        die(f"status must be one of {STATUS_ORDER}")
    if old is not None and STATUS_ORDER.index(new) < STATUS_ORDER.index(old):
        die(f"status moves forward only: {old} -> {new} refused")


def cmd_summary(state, _):
    p = state.get("progress", {})
    log, reviews = state.get("changeLog", []), state.get("reviews", [])
    print(f"project: {json.dumps(state.get('project'))}  updated: {state.get('updatedUtc')}")
    print("stages: " + ", ".join(f"{k}={v.get('status')}" for k, v in state.get("stages", {}).items()))
    for kind in ("phases", "edits"):
        rows = state.get(kind, [])
        print(f"{kind}: " + (", ".join(f"{e['id']}={e.get('status')}" for e in rows) or "none"))
    print(f"changeLog: {len(log)} entries, last id {max((e['id'] for e in log), default=0)}, "
          f"processed to {p.get('lastProcessedChangeLogId')}")
    print(f"reviews: {len(reviews)}, last {reviews[-1]['id'] if reviews else 'none'}, "
          f"processed to R-{p.get('lastProcessedReviewNumber')}")


def cmd_get(state, args):
    value = resolve(state, args[0] if args else "")
    print(json.dumps(value, indent=None if args else 2))


def unprocessed(state):
    p = state.get("progress", {})
    return {
        "changeLog": [e for e in state.get("changeLog", [])
                      if num(e["id"]) > p.get("lastProcessedChangeLogId", 0)],
        "reviews": [r for r in state.get("reviews", [])
                    if num(r["id"]) > p.get("lastProcessedReviewNumber", 0)],
    }


def cmd_new(state, _):
    print(json.dumps(unprocessed(state)))


# Stage 4's input documents in the documents location: (name, required, said when missing)
START_DOCS = (
    ("PROJECT_CONTEXT.md", True, ""),
    ("PLAN_{app}.md", True, ""),
    ("FEATURE_STATUS.md", True, ""),
    ("features.json", False,
     "docs.py needs it; a Markdown-only ledger moves over by feature import"),
    ("HOW_TO_RUN.md", False, "no phase has written it yet"),
    ("HIGH_LEVEL_DESIGN_{app}.md", True, ""),
    ("LOW_LEVEL_DESIGN_{app}.md", True, ""),
    ("BUSINESS_REQUIREMENTS_{app}.md", True, ""),
    ("FUNCTIONAL_REQUIREMENTS_{app}.md", True, ""),
    ("TECHNICAL_REQUIREMENTS_{app}.md", True, ""),
    ("LEGACY_CODE_MAP_{app}.md", False, "search the legacy source instead"),
)


def text(s):
    """A path or name as ASCII, non-ASCII as \\u escapes like every other value printed."""
    return "".join(c if ord(c) < 128 else json.dumps(c)[1:-1] for c in str(s))


def same_dir(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def find_doc(folder, pattern, app):
    """(status, path, note): the exact conventional name, else the one <prefix>_*.md there."""
    exact = os.path.join(folder, pattern.format(app=app))
    if os.path.isfile(exact) or "{app}" not in pattern:
        return ("found" if os.path.isfile(exact) else "missing"), exact, ""
    prefix = pattern.split("{app}")[0]
    try:
        hits = sorted(f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith(".md"))
    except OSError:
        hits = []
    if len(hits) == 1:
        return "found", os.path.join(folder, hits[0]), f"not {pattern.format(app=app)}"
    if hits:
        return "ambiguous", os.path.join(folder, prefix + "*.md"), ", ".join(hits)
    return "missing", exact, ""


def print_marks(state, new):
    p = state.get("progress", {})
    log_mark = max([num(e["id"]) for e in new["changeLog"]]
                   + [p.get("lastProcessedChangeLogId", 0)])
    review_mark = max([num(r["id"]) for r in new["reviews"]]
                      + [p.get("lastProcessedReviewNumber", 0)])
    marks = f"lastProcessedChangeLogId={log_mark} lastProcessedReviewNumber={review_mark}"
    print("== marks at hand-off (information only; start writes nothing)")
    print(f"if you fold in everything in new: {marks}" if new["changeLog"] or new["reviews"]
          else f"no new entries: the marks stay {marks}")
    print("raise lastProcessedChangeLogId to the id of each entry this run adds, but never past "
          "an entry you did not reconcile")


def print_inputs(state, state_path):
    """The documents by conventional name, from the documents location as read from the
    working-tree root; state.json lives in that folder (Stage 0 puts it there)."""
    context = state.get("context")
    locations = context.get("locations") if isinstance(context, dict) else None
    locations = locations if isinstance(locations, dict) else {}
    state_dir = os.path.normpath(os.path.dirname(state_path) or ".")
    folder = locations.get("documents")
    stop = "a required one missing or ambiguous: stop and ask"
    if isinstance(folder, str) and folder:
        print(f"== documents in {text(folder)} (context.locations.documents; {stop})")
    else:
        folder = state_dir
        print(f"== documents in {text(folder)} (state.json's folder, as "
              f"context.locations.documents is not set; {stop})")
    if not os.path.isdir(folder):
        print(f"documents location {text(folder)} not found from here: run from the "
              "working-tree root")
    else:
        if not same_dir(folder, state_dir):
            print(f"state.json is not in the documents location ({text(folder)}); docs.py "
                  f"updates the ledger and plan beside state.json ({text(state_dir)}): "
                  "stop and ask")
        app = state.get("project") or "<AppName>"
        for pattern, required, why in START_DOCS:
            status, path, note = find_doc(folder, pattern, app)
            note = why if status == "missing" and why else note
            line = (f"{'required' if required else 'optional'} {status} "
                    f"{text(os.path.normpath(path))}")
            print(line + (f"  ({text(note)})" if note else ""))
    code = [(k, locations[k]) for k in ("legacySource", "targetRepo", "targetRepoFrontend")
            if isinstance(locations.get(k), str) and locations[k]]
    if code:
        print("== code (context.locations)")
    for k, v in code:
        print(f"{k}: {'found' if os.path.isdir(v) else 'missing'} {text(v)}")


def cmd_start(state, args):
    """Everything a Stage 4 run reads from state at its start, in one command; writes nothing."""
    if args:
        die("start takes no arguments")
    print("== summary")
    cmd_summary(state, [])
    new = unprocessed(state)
    print("== new (changeLog and reviews above the progress marks)")
    print(json.dumps(new))
    for part in ("context", "phases", "edits"):
        print(f"== {part}")
        cmd_get(state, [part])
    stages = state.get("stages")
    print("== stages.plan")
    print(json.dumps(stages.get("plan") if isinstance(stages, dict) else None))
    print_marks(state, new)
    print_inputs(state, STATE_PATH)


def cmd_add(state, args):
    if not args or args[0] not in ("changeLog", "reviews", "edits", "phases"):
        die("add needs one of: changeLog, reviews, edits, phases")
    kind, fields = args[0], parse_fields(args[1:])
    items = state.setdefault(kind, [])
    if "id" in fields:
        die("ids are allocated by the script; leave id out")
    used = [e["id"] for e in items] + (state.get("droppedPhases", []) if kind == "phases" else [])
    n = max((num(i) for i in used), default=0) + 1
    entry = {"id": f"{PREFIX[kind]}{n}" if kind in PREFIX else n}
    if kind != "phases":
        entry["utc"] = now()
    if kind in ("edits", "phases"):
        entry.update(status="pending", branch=None, prUrls=[], notes="")
        if kind == "phases":
            entry["sizeReport"] = None
        check_status(kind, None, fields.get("status", "pending"))
    if kind == "changeLog":
        entry.update(docsTouched=[], phasesAffected=[], editsAffected=[])
    entry.update(fields)
    problems = entry_problems(kind, entry)
    if problems:
        die("\n".join(problems))
    items.append(entry)
    print(entry["id"])
    return True


def cmd_set(state, args):
    if len(args) < 2:
        die("set needs PATH and fields")
    path, fields = args[0], parse_fields(args[1:])
    top = path.split(".")[0]
    if top in APPEND_ONLY:
        die(f"{top} is append-only; correct it by appending a new entry")
    target = resolve(state, path)
    if not isinstance(target, dict):
        die(f"{path} is not an object")
    if "id" in fields:
        die("ids are permanent")
    if top == "phases" and "name" in fields and fields["name"] != target.get("name"):
        die("phase names are permanent; a different phase is a new entry (drop a pending one)")
    if "status" in fields and top in ("phases", "edits", "stages"):
        check_status(top, target.get("status"), fields["status"])
    if top == "progress":
        for k, v in fields.items():
            if not is_int(v):
                die(f"progress.{k} must be an integer")
    target.update(fields)
    print(json.dumps(target))
    return True


def cmd_drop(state, args):
    if len(args) != 1 or not args[0].startswith("phases."):
        die("drop takes exactly phases.P-<n>")
    phase = resolve(state, args[0])
    if phase.get("status") != "pending":
        die(f"{phase['id']} is {phase.get('status')}; only pending phases may be dropped")
    state["phases"].remove(phase)
    state.setdefault("droppedPhases", []).append(phase["id"])  # so the id is never reused
    print(f"dropped {phase['id']}")
    return True


def cmd_check(state, _):
    problems = []
    for kind in ("phases", "edits", "changeLog", "reviews"):
        ids = [str(e.get("id")) for e in state.get(kind, [])]
        if len(ids) != len(set(ids)):
            problems.append(f"{kind}: duplicate ids")
        for e in state.get(kind, []):
            problems += entry_problems(kind, e)
    for kind in ("phases", "edits"):
        for e in state.get(kind, []):
            if e.get("status") not in STATUS_ORDER:
                problems.append(f"{e.get('id')}: bad status {e.get('status')!r}")
            if not isinstance(e.get("prUrls"), list):
                problems.append(f"{e.get('id')}: prUrls must be a list")
    for name, s in state.get("stages", {}).items():
        if s.get("status") not in STAGE_STATUSES:
            problems.append(f"stages.{name}: bad status {s.get('status')!r}")
    for k, v in state.get("progress", {}).items():
        if not is_int(v):
            problems.append(f"progress.{k} must be an integer")
    if problems:
        die("\n".join(problems))
    print("ok")


COMMANDS = {"start": cmd_start, "summary": cmd_summary, "get": cmd_get, "new": cmd_new,
            "add": cmd_add, "set": cmd_set, "drop": cmd_drop, "check": cmd_check}


def main(argv):
    for stream in (sys.stdout, sys.stderr):  # ASCII survives any console encoding
        stream.reconfigure(encoding="ascii", errors="backslashreplace")
    ensure_tmp_dir()
    path = None
    if argv[:1] == ["--file"]:
        if len(argv) < 2:
            die("--file needs a path")
        path, argv = argv[1], argv[2:]
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    global STATE_PATH
    path = STATE_PATH = path or find_file()
    state = load(path)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):  # hold the result back until the write succeeds
        changed = COMMANDS[argv[0]](state, argv[1:])
    if changed:
        save(path, state)
    sys.stdout.write(out.getvalue())


if __name__ == "__main__":
    main(sys.argv[1:])
