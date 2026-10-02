#!/usr/bin/env python3
"""Read and write the harness state.json without loading the whole file into an agent.

Usage: python state.py [--file PATH] <command> ...

  summary                     one-screen overview: stages, phases, edits, marks, counts
  get [PATH]                  print the value at PATH (whole file if omitted)
  new                         changeLog / reviews entries above the progress high-water marks
  add LIST k=v ... | -        append to changeLog, reviews, edits or phases; id and utc filled in
  set PATH k=v ... | -        update fields on the object at PATH
  drop phases.P-<n>           remove a pending phase (plan refresh only)
  check                       validate the file against the harness rules

PATH is dotted; a list segment matches an element by id, e.g. phases.P-3 or changeLog.12.
A value is parsed as JSON when it parses (7, null, true) and kept as a string otherwise; quote
the whole pair when it has spaces: "summary=fixed the export header". List fields (prUrls,
docsTouched, phasesAffected, editsAffected) also accept a,b,c.
Nested objects or text with quotes: pipe a JSON object and end the command with a lone "-":
  '{"sizeReport": {"verdict": "right", ...}}' | python state.py set phases.P-4 -
Without --file, state.json is found by name under the current directory.

Examples:
  set phases.P-4 "status=in progress"
  set progress lastProcessedChangeLogId=12 lastProcessedReviewNumber=3
  add changeLog author=developer origin=out-of-band "summary=..." phasesAffected=P-2
"""
import json
import os
import sys
from datetime import datetime, timezone

STATUS_ORDER = ["pending", "in progress", "done"]
STAGE_STATUSES = {"pending", "in progress", "complete"}
LIST_FIELDS = {"prUrls", "docsTouched", "phasesAffected", "editsAffected"}
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


def parse_value(key, raw):
    try:
        value = json.loads(raw)
    except ValueError:
        value = raw
    if key in LIST_FIELDS and not isinstance(value, list):
        value = [v for v in str(raw).split(",") if v]
    return value


def parse_fields(args):
    if args == ["-"]:
        try:
            fields = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))  # PowerShell adds a BOM
        except ValueError as e:
            die(f"stdin is not valid JSON: {e}")
        if not isinstance(fields, dict):
            die("stdin must be a JSON object")
        return fields
    fields = {}
    for arg in args:
        if "=" not in arg:
            die(f"expected key=value, got {arg!r}")
        key, raw = arg.split("=", 1)
        fields[key] = parse_value(key, raw)
    if not fields:
        die("nothing to write")
    return fields


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
    print(f"project: {state.get('project')}  updated: {state.get('updatedUtc')}")
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
    print(json.dumps(value, indent=None if args else 2, ensure_ascii=False))


def cmd_new(state, _):
    p = state.get("progress", {})
    out = {
        "changeLog": [e for e in state.get("changeLog", [])
                      if num(e["id"]) > p.get("lastProcessedChangeLogId", 0)],
        "reviews": [r for r in state.get("reviews", [])
                    if num(r["id"]) > p.get("lastProcessedReviewNumber", 0)],
    }
    print(json.dumps(out, ensure_ascii=False))


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
            if not isinstance(v, int):
                die(f"progress.{k} must be an integer")
    target.update(fields)
    print(json.dumps(target, ensure_ascii=False))
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
        if not isinstance(v, int):
            problems.append(f"progress.{k} must be an integer")
    if problems:
        die("\n".join(problems))
    print("ok")


COMMANDS = {"summary": cmd_summary, "get": cmd_get, "new": cmd_new, "add": cmd_add,
            "set": cmd_set, "drop": cmd_drop, "check": cmd_check}


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
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
