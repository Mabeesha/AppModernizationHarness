#!/usr/bin/env python3
"""Tests for ModernizationHarness/tools/state.py, the state.json tool.

Each test runs the real script as a subprocess — the way an agent calls it — against a fresh
state.json in a temporary directory, then reads the file back to see what was actually stored.

Run:  uv run tests/test_state_tool.py      (or: python tests/test_state_tool.py)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "ModernizationHarness" / "tools" / "state.py"
DASH = "—"

INITIAL = {
    "project": "Demo",
    "schemaVersion": 1,
    "createdUtc": "2026-01-01T00:00:00Z",
    "updatedUtc": "2026-01-01T00:00:00Z",
    "context": {
        "locations": {"documents": "out", "sharedWithLegacy": False},
        "repo": {"layout": "single", "release": "together"},
    },
    "stages": {"plan": {"status": "pending", "rerunCount": 0}},
    "phases": [],
    "edits": [],
    "changeLog": [],
    "reviews": [],
    "progress": {"lastProcessedChangeLogId": 0, "lastProcessedReviewNumber": 0},
}


class StateToolTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        (self.dir / "out").mkdir()
        self.file = self.dir / "out" / "state.json"
        self.file.write_text(json.dumps(INITIAL), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, *args, ok=True):
        """Run state.py from the temp dir; assert it succeeded (or failed, when ok=False)."""
        res = subprocess.run([sys.executable, str(TOOL), *args], cwd=self.dir,
                             capture_output=True, encoding="ascii")
        if ok:
            self.assertEqual(res.returncode, 0, f"{args} failed: {res.stderr}")
        else:
            self.assertNotEqual(res.returncode, 0, f"{args} should have been refused")
        return res

    def refused(self, *args):
        """Assert the command is refused, prints nothing that looks like success, and leaves
        the file untouched with no stray temp file."""
        before = self.file.read_bytes()
        res = self.run_tool(*args, ok=False)
        self.assertEqual(self.file.read_bytes(), before, f"{args} changed the file on refusal")
        self.assertEqual(res.stdout, "", f"{args} printed output although it was refused")
        self.assertEqual(list(self.dir.rglob("*.tmp")), [], f"{args} left a temp file")
        return res.stderr

    def state(self):
        return json.loads(self.file.read_text(encoding="utf-8"))

    def write_payload(self, obj, encoding="utf-8"):
        path = self.dir / "payload.json"
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding=encoding)
        return "@" + str(path)

    # --- reading ------------------------------------------------------------------------------

    def test_get_returns_only_the_slice(self):
        out = self.run_tool("get", "context.repo").stdout
        self.assertEqual(json.loads(out), INITIAL["context"]["repo"])

    def test_a_missing_file_is_a_clear_error_not_a_traceback(self):
        for args in (("summary",), ("start",), ("set", "progress", "rerunCount=1")):
            with self.subTest(args=args):
                res = self.run_tool("--file", "no-such-state.json", *args, ok=False)
                self.assertIn("state.py: cannot read no-such-state.json", res.stderr)
                self.assertNotIn("Traceback", res.stderr)

    def test_get_unknown_path_is_refused(self):
        self.assertIn("no such path", self.refused("get", "context.nope"))
        self.assertIn("no element with id", self.refused("get", "phases.P-9"))

    def test_summary_lists_statuses_and_marks(self):
        self.run_tool("add", "phases", "name=Auth")
        out = self.run_tool("summary").stdout
        self.assertIn("phases: P-1=pending", out)
        self.assertIn("processed to 0", out)

    def test_new_compares_review_numbers_numerically(self):
        for _ in range(10):
            self.run_tool("add", "reviews", "target=P-1", "result=clean",
                          "blockerCount=0", "findingsCount=0")
        for i in range(3):
            self.run_tool("add", "changeLog", "author=developer", "origin=developer-prompt",
                          f"summary=note {i}")
        self.run_tool("set", "progress", "lastProcessedChangeLogId=2",
                      "lastProcessedReviewNumber=9")
        new = json.loads(self.run_tool("new").stdout)
        self.assertEqual([e["id"] for e in new["changeLog"]], [3])
        self.assertEqual([r["id"] for r in new["reviews"]], ["R-10"])  # not R-2..R-9 as text

    # --- start: one command that begins a Stage 4 run ----------------------------------------

    DOCS = ["PROJECT_CONTEXT.md", "PLAN_Demo.md", "FEATURE_STATUS.md", "features.json",
            "HOW_TO_RUN.md", "HIGH_LEVEL_DESIGN_Demo.md", "LOW_LEVEL_DESIGN_Demo.md",
            "BUSINESS_REQUIREMENTS_Demo.md", "FUNCTIONAL_REQUIREMENTS_Demo.md",
            "TECHNICAL_REQUIREMENTS_Demo.md", "LEGACY_CODE_MAP_Demo.md"]

    def start(self):
        """Run start; assert it exits 0 and leaves state.json byte for byte as it was.
        Returns {section title: [lines]}, in output order."""
        before = self.file.read_bytes()
        out = self.run_tool("start").stdout
        self.assertEqual(self.file.read_bytes(), before, "start changed state.json")
        sections, current = {}, None
        for line in out.splitlines():
            if line.startswith("== "):
                current = line[3:].split(" (")[0]
                sections[current] = []
            else:
                sections[current].append(line)
        return sections

    def doc_lines(self, sections):
        return {line.split()[2].replace("\\", "/").split("/")[-1]: line
                for key, lines in sections.items() if key.startswith("documents")
                for line in lines if line.startswith(("required ", "optional "))}

    def test_start_on_a_fresh_state(self):
        s = self.start()
        self.assertEqual(list(s), ["summary", "new", "context", "phases", "edits",
                                   "stages.plan", "marks at hand-off", "documents in out"])
        self.assertEqual(json.loads(s["stages.plan"][0]), INITIAL["stages"]["plan"])
        self.assertEqual(s["summary"], self.run_tool("summary").stdout.splitlines())
        self.assertEqual(json.loads(s["new"][0]), {"changeLog": [], "reviews": []})
        self.assertEqual(s["context"], [self.run_tool("get", "context").stdout.strip()])
        self.assertEqual((s["phases"], s["edits"]), (["[]"], ["[]"]))
        self.assertEqual(s["marks at hand-off"][0], "no new entries: the marks stay "
                         "lastProcessedChangeLogId=0 lastProcessedReviewNumber=0")
        docs = self.doc_lines(s)
        self.assertEqual(list(docs), self.DOCS)
        for name, line in docs.items():
            optional = name in ("features.json", "HOW_TO_RUN.md", "LEGACY_CODE_MAP_Demo.md")
            self.assertTrue(line.startswith(("optional" if optional else "required") + " missing "),
                            line)

    def test_start_prints_new_entries_and_the_marks_to_write(self):
        for i in range(3):
            self.run_tool("add", "changeLog", "author=developer", "origin=developer-prompt",
                          f"summary=note {i}")
        for _ in range(2):
            self.run_tool("add", "reviews", "target=P-1", "result=clean",
                          "blockerCount=0", "findingsCount=0")
        self.run_tool("set", "progress", "lastProcessedChangeLogId=1",
                      "lastProcessedReviewNumber=1")
        s = self.start()
        self.assertEqual(s["new"], [self.run_tool("new").stdout.strip()])
        self.assertEqual(s["marks at hand-off"][0], "if you fold in everything in new: "
                         "lastProcessedChangeLogId=3 lastProcessedReviewNumber=2")
        self.assertIn("reconcile", s["marks at hand-off"][1])
        # only a review is new: the change-log mark stays where it is
        self.run_tool("set", "progress", "lastProcessedChangeLogId=3")
        self.assertIn("lastProcessedChangeLogId=3 lastProcessedReviewNumber=2",
                      self.start()["marks at hand-off"][0])

    def test_start_finds_documents_by_conventional_name(self):
        out = self.dir / "out"
        for name in self.DOCS:
            (out / name).write_text("x", encoding="utf-8")
        (out / "PLAN_Old.md").write_text("x", encoding="utf-8")  # the exact name wins
        docs = self.doc_lines(self.start())
        self.assertEqual(list(docs), self.DOCS)
        for line in docs.values():
            self.assertRegex(line, r"^(required|optional) found out[\\/]\S+$")

    def test_start_says_when_a_document_is_ambiguous_or_named_differently(self):
        out = self.dir / "out"
        for name in ("HIGH_LEVEL_DESIGN_A.md", "HIGH_LEVEL_DESIGN_B.md", "LOW_LEVEL_DESIGN_Old.md"):
            (out / name).write_text("x", encoding="utf-8")
        s = self.start()
        lines = s["documents in out"]
        self.assertIn("required ambiguous out" + ("\\" if sys.platform == "win32" else "/")
                      + "HIGH_LEVEL_DESIGN_*.md  (HIGH_LEVEL_DESIGN_A.md, HIGH_LEVEL_DESIGN_B.md)",
                      lines)
        lld = next(line for line in lines if "LOW_LEVEL" in line)
        self.assertTrue(lld.startswith("required found ") and "LOW_LEVEL_DESIGN_Old.md" in lld
                        and lld.endswith("(not LOW_LEVEL_DESIGN_Demo.md)"), lld)

    def test_start_reports_code_locations(self):
        (self.dir / "app").mkdir()
        self.run_tool("set", "context.locations", "targetRepo=app", "legacySource=legacy",
                      "targetRepoFrontend=null")
        self.assertEqual(self.start()["code"],
                         ["legacySource: missing legacy", "targetRepo: found app"])

    def test_start_stops_when_state_json_is_not_in_the_documents_location(self):
        (self.dir / "docs").mkdir()
        self.run_tool("set", "context.locations", "documents=docs")
        lines = self.start()["documents in docs"]
        sep = "\\" if sys.platform == "win32" else "/"
        self.assertEqual(lines[0], "state.json is not in the documents location (docs); docs.py "
                         f"updates the ledger and plan beside state.json (out): stop and ask")
        self.assertEqual(len(self.doc_lines({"documents": lines})), len(self.DOCS))
        self.assertTrue(lines[1].endswith(f"docs{sep}PROJECT_CONTEXT.md"), lines[1])

    def test_start_says_once_when_the_documents_location_is_not_found(self):
        self.run_tool("set", "context.locations", "documents=nowhere")
        self.assertEqual(self.start()["documents in nowhere"],
                         ["documents location nowhere not found from here: run from the "
                          "working-tree root"])

    def test_start_uses_the_state_folder_when_documents_is_not_set(self):
        self.run_tool("set", "context.locations", "documents=null")
        s = self.start()
        self.assertIn("documents in out", s)
        self.assertEqual(len(s["documents in out"]), len(self.DOCS))  # no stop line

    def test_start_survives_a_context_that_is_not_an_object(self):
        for context in (None, "text"):
            self.file.write_text(json.dumps(dict(INITIAL, context=context)), encoding="utf-8")
            s = self.start()
            self.assertEqual(s["context"], [json.dumps(context)])
            self.assertIn("documents in out", s)
            self.assertNotIn("code", s)

    def test_start_output_is_ascii(self):
        state = dict(INITIAL, project="Démo")
        self.file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        (self.dir / "out" / "PLAN_Démo.md").write_text("x", encoding="utf-8")
        s = self.start()  # run_tool decodes stdout as ASCII, so any other byte fails here
        self.assertIn('project: "D\\u00e9mo"', s["summary"][0])
        plan = next(line for line in s["documents in out"] if "PLAN_" in line)
        self.assertTrue(plan.startswith("required found ") and plan.endswith("PLAN_D\\u00e9mo.md"),
                        plan)

    def test_start_takes_no_arguments(self):
        self.assertIn("no arguments", self.refused("start", "now"))

    # --- ids ----------------------------------------------------------------------------------

    def test_ids_are_allocated_and_printed(self):
        self.assertEqual(self.run_tool("add", "phases", "name=A").stdout.strip(), "P-1")
        self.assertEqual(self.run_tool("add", "edits", "summary=x",
                                       "afterPhase=P-1").stdout.strip(), "E-1")
        self.assertEqual(self.run_tool("add", "changeLog", "author=developer", "origin=developer-prompt", 
                                       "summary=x").stdout.strip(), "1")
        self.assertEqual(self.run_tool("add", "reviews", "target=P-1",
                                       "result=clean", "blockerCount=0", "findingsCount=0").stdout.strip(), "R-1")
        self.assertIn("allocated by the script", self.refused("add", "phases", "id=P-7"))

    def test_edit_can_be_registered_done(self):
        # Stage 4 registers a minor edit once its checks pass, already done (DD-28).
        self.assertEqual(self.run_tool("add", "edits", "summary=x", "afterPhase=P-1",
                                       "status=done").stdout.strip(), "E-1")
        edit = self.state()["edits"][0]
        self.assertEqual((edit["status"], edit["branch"], edit["prUrls"]), ("done", None, []))
        self.assertEqual(self.run_tool("check").stdout.strip(), "ok")
        self.assertIn("forward only", self.refused("set", "edits.E-1", "status=pending"))

    def test_new_phase_gets_schema_defaults(self):
        self.run_tool("add", "phases", "name=A")
        self.assertEqual(self.state()["phases"][0], {
            "id": "P-1", "status": "pending", "branch": None, "prUrls": [], "notes": "",
            "sizeReport": None, "name": "A"})

    def test_dropped_phase_id_is_never_reused(self):
        for name in "ABC":
            self.run_tool("add", "phases", f"name={name}")
        self.run_tool("drop", "phases.P-3")
        self.assertEqual(self.run_tool("add", "phases", "name=D").stdout.strip(), "P-4")
        self.assertEqual(self.state()["droppedPhases"], ["P-3"])

    def test_only_pending_phases_can_be_dropped(self):
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", "status=in progress")
        self.assertIn("only pending", self.refused("drop", "phases.P-1"))

    def test_ids_are_permanent(self):
        self.run_tool("add", "phases", "name=A")
        self.assertIn("permanent", self.refused("set", "phases.P-1", "id=P-9"))

    def test_add_requires_the_schema_fields(self):
        self.assertIn("missing author", self.refused("add", "changeLog", "summary=x"))
        self.assertIn("missing findingsCount", self.refused(
            "add", "reviews", "target=P-1", "result=clean", "blockerCount=0"))
        self.assertIn("missing afterPhase", self.refused("add", "edits", "summary=x"))
        self.assertIn("missing name", self.refused("add", "phases", "notes=x"))

    def test_add_refuses_values_outside_the_schema(self):
        self.assertIn("author must be", self.refused(
            "add", "changeLog", "author=me", "origin=reconcile", "summary=x"))
        self.assertIn("origin must be", self.refused(
            "add", "changeLog", "author=review-agent", "origin=review-3", "summary=x"))
        self.assertIn("result must be", self.refused(
            "add", "reviews", "target=P-1", "result=ok", "blockerCount=0", "findingsCount=0"))
        self.run_tool("add", "changeLog", "author=review-agent", "origin=review-R-12",
                      "summary=x")

    def test_change_log_lists_default_to_empty(self):
        self.run_tool("add", "changeLog", "author=developer", "origin=out-of-band",
                      "summary=x", "phasesAffected=P-2")
        entry = self.state()["changeLog"][0]
        self.assertEqual((entry["docsTouched"], entry["phasesAffected"], entry["editsAffected"]),
                         ([], ["P-2"], []))

    def test_phase_names_are_permanent(self):
        self.run_tool("add", "phases", "name=A")
        self.assertIn("names are permanent", self.refused("set", "phases.P-1", "name=B"))
        self.run_tool("set", "phases.P-1", "name=A", "notes=same name is fine")

    # --- invariants ---------------------------------------------------------------------------

    def test_status_moves_forward_only(self):
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", "status=in progress")
        self.run_tool("set", "phases.P-1", "status=done")
        self.assertIn("forward only", self.refused("set", "phases.P-1", "status=pending"))
        self.assertIn("must be one of", self.refused("set", "phases.P-1", "status=accepted"))

    def test_history_is_append_only(self):
        self.run_tool("add", "changeLog", "author=developer", "origin=developer-prompt", "summary=x")
        self.run_tool("add", "reviews", "target=P-1", "result=clean", "blockerCount=0", "findingsCount=0")
        self.assertIn("append-only", self.refused("set", "changeLog.1", "summary=y"))
        self.assertIn("append-only", self.refused("set", "reviews.R-1", "result=clean"))

    def test_every_write_stamps_updated_utc(self):
        self.run_tool("set", "stages.plan", "status=complete")
        self.assertNotEqual(self.state()["updatedUtc"], INITIAL["updatedUtc"])

    # --- types (review findings 2, 3, 4) ------------------------------------------------------

    def test_text_that_looks_like_json_stays_text(self):
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", "branch=1234", "notes=true")
        phase = self.state()["phases"][0]
        self.assertEqual((phase["branch"], phase["notes"]), ("1234", "true"))
        self.run_tool("add", "changeLog", "author=developer", "origin=developer-prompt", "summary=2024")
        self.assertEqual(self.state()["changeLog"][0]["summary"], "2024")

    def test_null_is_null(self):
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", "branch=x")
        self.run_tool("set", "phases.P-1", "branch=null")
        self.assertIsNone(self.state()["phases"][0]["branch"])

    def test_integer_fields_refuse_booleans_and_text(self):
        for bad in ("true", "false", "1.5", "two"):
            self.assertIn("must be an integer",
                          self.refused("set", "progress", f"lastProcessedChangeLogId={bad}"))
        self.assertIn("must be an integer",
                      self.refused("set", "progress", self.write_payload(
                          {"lastProcessedChangeLogId": True})))
        self.run_tool("set", "progress", "lastProcessedChangeLogId=3")
        self.assertEqual(self.state()["progress"]["lastProcessedChangeLogId"], 3)

    def test_boolean_fields(self):
        self.run_tool("set", "context.locations", "sharedWithLegacy=true")
        self.assertIs(self.state()["context"]["locations"]["sharedWithLegacy"], True)
        self.assertIn("true or false",
                      self.refused("set", "context.locations", "sharedWithLegacy=yes"))

    def test_list_fields_stay_lists_from_any_input(self):
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", "prUrls=http://a,http://b")
        self.assertEqual(self.state()["phases"][0]["prUrls"], ["http://a", "http://b"])
        self.run_tool("set", "phases.P-1", self.write_payload({"prUrls": "http://x"}))
        self.assertEqual(self.state()["phases"][0]["prUrls"], ["http://x"])
        self.assertIn("must be a list",
                      self.refused("set", "phases.P-1", self.write_payload({"prUrls": 5})))

    def test_size_report_must_be_an_object(self):
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", 'sizeReport={"verdict": "right"}')
        self.assertEqual(self.state()["phases"][0]["sizeReport"], {"verdict": "right"})
        self.assertIn("JSON object", self.refused("set", "phases.P-1", "sizeReport=oops"))

    # --- encoding (review findings 1, 5) ------------------------------------------------------

    def test_file_input_keeps_non_ascii_in_utf8_and_utf16(self):
        self.run_tool("add", "phases", "name=A")
        for enc in ("utf-8", "utf-8-sig", "utf-16"):  # utf-16 is what PowerShell 5.1 '>' writes
            note = f"{enc} {DASH} ok"
            self.run_tool("set", "phases.P-1", self.write_payload({"notes": note}, enc))
            self.assertEqual(self.state()["phases"][0]["notes"], note)

    def test_wrongly_encoded_file_fails_loudly(self):
        self.run_tool("add", "phases", "name=A")
        self.assertIn("cannot read", self.refused(
            "set", "phases.P-1", self.write_payload({"notes": f"ansi {DASH}"}, "cp1252")))

    def test_stdin_input_is_gone(self):
        self.run_tool("add", "phases", "name=A")
        self.assertIn("key=value or \"@FILE\" (quoted)", self.refused("set", "phases.P-1", "-"))

    def test_output_is_ascii_and_round_trips(self):
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", self.write_payload({"notes": f"a {DASH} b"}))
        shown = self.run_tool("get", "phases.P-1.notes").stdout.strip()  # run_tool decodes ascii
        self.assertEqual(shown, '"a \\u2014 b"')
        self.run_tool("set", "phases.P-1", "notes=" + shown.strip('"'))  # an agent copies it back
        self.assertEqual(self.state()["phases"][0]["notes"], f"a {DASH} b")

    def test_emoji_round_trips(self):
        emoji = "\U0001F600"  # printed as two codes: \ud83d\ude00
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", self.write_payload({"notes": f"hi {emoji}"}))
        shown = self.run_tool("get", "phases.P-1.notes").stdout.strip()
        self.assertEqual(shown, '"hi \\ud83d\\ude00"')
        self.run_tool("set", "phases.P-1", "notes=" + shown.strip('"'))
        self.assertEqual(self.state()["phases"][0]["notes"], f"hi {emoji}")

    def test_broken_half_character_is_refused_from_any_input(self):
        self.run_tool("add", "phases", "name=A")
        self.assertIn("broken character", self.refused("set", "phases.P-1", "notes=x \\ud83d"))
        path = self.dir / "half.json"
        path.write_text('{"notes": "x \\ud83d"}', encoding="ascii")
        self.assertIn("broken character", self.refused("set", "phases.P-1", f"@{path}"))

    def test_other_backslashes_are_left_alone(self):
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", "notes=C:\\new\\table \\x41 \\u12")
        self.assertEqual(self.state()["phases"][0]["notes"], "C:\\new\\table \\x41 \\u12")

    def test_file_on_disk_stays_readable_utf8(self):
        self.run_tool("set", "stages.plan", self.write_payload({"notes": f"x {DASH} y"}))
        self.assertIn(DASH, self.file.read_text(encoding="utf-8"))

    # --- check and file discovery -------------------------------------------------------------

    def test_check_accepts_a_valid_file(self):
        self.run_tool("add", "phases", "name=A")
        self.assertEqual(self.run_tool("check").stdout.strip(), "ok")

    def test_check_catches_hand_edit_mistakes(self):
        bad = json.loads(json.dumps(INITIAL))
        bad["phases"] = [{"id": "P-1", "status": "accepted", "prUrls": "http://x"},
                         {"id": "P-1", "status": "done", "prUrls": []}]
        bad["progress"]["lastProcessedChangeLogId"] = True
        bad["stages"]["plan"]["status"] = "done"
        bad["changeLog"] = [{"id": 1, "utc": "x", "author": "someone", "summary": "s"}]
        self.file.write_text(json.dumps(bad), encoding="utf-8")
        err = self.refused("check")
        for problem in ("duplicate ids", "bad status 'accepted'", "prUrls must be a list",
                        "lastProcessedChangeLogId must be an integer", "stages.plan",
                        "1: missing origin", "1: author must be"):
            self.assertIn(problem, err)

    def test_invalid_json_file_fails_loudly(self):
        self.file.write_text("{not json", encoding="utf-8")
        self.assertIn("not valid JSON", self.refused("summary"))

    def values(self, obj, name="values.json", folder=".harness-tmp"):
        path = self.dir / folder / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False),
                        encoding="utf-8")
        return path

    def test_values_folder_is_created_and_not_ignored(self):
        # Values files (@FILE) go in .harness-tmp/ at the working-tree root. The tool creates the
        # folder with no .gitignore: GitLab Duo's file tools refuse a git-ignored path.
        self.run_tool("summary")
        self.assertTrue((self.dir / ".harness-tmp").is_dir())
        self.assertEqual(list((self.dir / ".harness-tmp").iterdir()), [])
        (self.dir / ".harness-tmp" / "state.json").write_text("{}", encoding="utf-8")
        self.run_tool("summary")  # a stray copy there is never taken for the real state.json

    def test_a_values_file_in_the_folder_is_deleted_once_read(self):
        payload = self.values({"author": "developer", "origin": "out-of-band",
                               "summary": f"fixed {DASH} it"})
        res = self.run_tool("add", "changeLog", "@" + str(payload))
        self.assertEqual(res.stdout, "1\n")  # stdout stays the result; the note is on stderr
        self.assertIn("removed", res.stderr)
        self.assertIn("values.json", res.stderr)
        self.assertFalse(payload.exists())
        self.assertEqual(self.state()["changeLog"][0]["summary"], f"fixed {DASH} it")

    def test_a_values_file_is_deleted_on_a_refusal_or_a_malformed_file_too(self):
        self.run_tool("add", "phases", "name=Scaffold")
        cases = {
            "rule": ("set", "phases.P-1", {"status": "pending"}),  # backward: refused
            "malformed": ("set", "phases.P-1", "{not json"),
            "wrong type": ("add", "reviews", {"target": "P-1", "result": "clean",
                                              "blockerCount": "one", "findingsCount": 0}),
        }
        self.run_tool("set", "phases.P-1", "status=done")
        for label, (cmd, target, obj) in cases.items():
            with self.subTest(label):
                payload = self.values(obj, name=f"{label.replace(' ', '-')}.json")
                res = self.refused(cmd, target, "@" + str(payload))
                self.assertFalse(payload.exists(), f"{label}: values file left behind")
                self.assertIn("removed", res)

    def test_a_values_file_never_read_or_outside_the_folder_is_kept(self):
        payload = self.values({"name": "Scaffold"})
        self.refused("add", "nonsense", "@" + str(payload))  # stopped before reading it
        self.assertTrue(payload.exists())
        outside = self.values({"name": "Scaffold"}, folder="elsewhere")
        res = self.run_tool("add", "phases", "@" + str(outside))
        self.assertTrue(outside.exists())
        self.assertNotIn("removed", res.stderr)
        self.run_tool("add", "phases", "@missing.json", ok=False)  # a read error: nothing to remove

    def test_a_values_file_read_from_another_folder_is_still_deleted(self):
        # the folder is recognised by name, not by the current directory
        payload = self.values({"name": "Scaffold"})
        res = subprocess.run([sys.executable, str(TOOL), "--file", str(self.file), "add",
                              "phases", "@" + str(payload)], cwd=self.dir / "out",
                             capture_output=True, encoding="ascii")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertFalse(payload.exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows file locks")
    def test_a_values_file_open_elsewhere_is_named_not_fatal(self):
        payload = self.values({"name": "Scaffold"})
        with open(payload, "rb"):  # an open handle stops a delete on Windows
            res = self.run_tool("add", "phases", "@" + str(payload))
        self.assertIn("could not remove", res.stderr)
        self.assertIn("new name", res.stderr)
        self.assertEqual(self.state()["phases"][0]["name"], "Scaffold")

    def test_the_old_self_ignoring_gitignore_is_removed_and_any_other_kept(self):
        ignore = self.dir / ".harness-tmp" / ".gitignore"
        ignore.parent.mkdir()
        for content in (b"*\n", b"*", b"*\r\n"):
            with self.subTest(content=content):
                ignore.write_bytes(content)
                res = self.run_tool("summary")
                self.assertFalse(ignore.exists())
                self.assertIn("removed", res.stderr)
                self.assertTrue(res.stdout.startswith("project:"))  # stdout is unchanged
        ignore.write_bytes(b"*\n# mine\n")
        self.run_tool("summary")
        self.assertEqual(ignore.read_bytes(), b"*\n# mine\n")

    def test_two_state_files_need_an_explicit_path(self):
        (self.dir / "other").mkdir()
        (self.dir / "other" / "state.json").write_text(json.dumps(INITIAL), encoding="utf-8")
        self.assertIn("pass --file", self.refused("summary"))
        self.run_tool("--file", str(self.file), "summary")


if __name__ == "__main__":
    unittest.main(verbosity=1)
