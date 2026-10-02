#!/usr/bin/env python3
"""Read and write the harness state.json without loading the whole file into an agent.

Usage: python state.py [--file PATH] <command> ...

  summary                     one-screen overview: stages, phases, edits, marks, counts
  get [PATH]                  print the value at PATH (whole file if omitted)
  new                         changeLog / reviews entries above the progress high-water marks
  add LIST k=v ... | @FILE    append to changeLog, reviews, edits or phases; id and utc filled in
  set PATH k=v ... | @FILE    update fields on the object at PATH
  drop phases.P-<n>           remove a pending phase (plan refresh only)
  check                       validate the file against the harness rules

PATH is dotted; a list segment matches an element by id, e.g. phases.P-3 or changeLog.12.
A value is text, except: null; the integer fields (progress marks, rerunCount, blockerCount,
findingsCount); the true/false fields (sharedDataStore, sharedWithLegacy); the list fields
(prUrls, docsTouched, phasesAffected, editsAffected), which take a,b,c; and sizeReport, which
takes a JSON object. A wrong type is refused. Quote the whole pair when it has spaces:
"summary=fixed the export header".
Nested objects or text with quotes: write a JSON object of fields to a UTF-8 file outside the
repo and pass @FILE in place of the pairs. Never pipe JSON in: Windows PowerShell 5.1 turns
non-ASCII characters into "?" on the way.
Output is ASCII; a non-ASCII character prints as an escape such as \\u2014, and both k=v and
@FILE turn that escape back into the character, so a copied value round-trips.
Without --file, state.json is found by name under the current directory.

Examples:
  set phases.P-4 "status=in progress"
  set progress lastProcessedChangeLogId=12 lastProcessedReviewNumber=3
  add changeLog author=developer origin=out-of-band "summary=..." phasesAffected=P-2
"""
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
SKIP_DIRS = {".git", "node_modules", "bin", "obj", "target", "dist", "ModernizationHarness"}


def die(msg):
    sys.exit(f"state.py: {msg}")


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
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


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
            # \uXXXX is how output shows non-ASCII; decode it so a copied value round-trips
            raw = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), raw)
            fields[key] = None if raw == "null" else raw
    if not fields:
        die("nothing to write")
    return {k: coerce(k, v) for k, v in fields.items()}


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


def cmd_new(state, _):
    p = state.get("progress", {})
    out = {
        "changeLog": [e for e in state.get("changeLog", [])
                      if num(e["id"]) > p.get("lastProcessedChangeLogId", 0)],
        "reviews": [r for r in state.get("reviews", [])
                    if num(r["id"]) > p.get("lastProcessedReviewNumber", 0)],
    }
    print(json.dumps(out))


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
    entry.update(fields)
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


COMMANDS = {"summary": cmd_summary, "get": cmd_get, "new": cmd_new, "add": cmd_add,
            "set": cmd_set, "drop": cmd_drop, "check": cmd_check}


def main(argv):
    for stream in (sys.stdout, sys.stderr):  # ASCII survives any console encoding
        stream.reconfigure(encoding="ascii", errors="backslashreplace")
    path = None
    if argv[:1] == ["--file"]:
        if len(argv) < 2:
            die("--file needs a path")
        path, argv = argv[1], argv[2:]
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    path = path or find_file()
    state = load(path)
    if COMMANDS[argv[0]](state, argv[1:]):
        save(path, state)


if __name__ == "__main__":
    main(sys.argv[1:])
