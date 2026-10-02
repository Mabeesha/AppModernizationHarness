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
        "constraints": [{"id": "C1", "title": "Reuse DB", "statement": "No schema changes"}],
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
        """Assert the command is refused and the file is left untouched."""
        before = self.file.read_bytes()
        res = self.run_tool(*args, ok=False)
        self.assertEqual(self.file.read_bytes(), before, f"{args} changed the file on refusal")
        return res.stderr

    def state(self):
        return json.loads(self.file.read_text(encoding="utf-8"))

    def write_payload(self, obj, encoding="utf-8"):
        path = self.dir / "payload.json"
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding=encoding)
        return "@" + str(path)

    # --- reading ------------------------------------------------------------------------------

    def test_get_returns_only_the_slice(self):
        out = self.run_tool("get", "context.constraints.C1").stdout
        self.assertEqual(json.loads(out), INITIAL["context"]["constraints"][0])

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

    # --- ids ----------------------------------------------------------------------------------

    def test_ids_are_allocated_and_printed(self):
        self.assertEqual(self.run_tool("add", "phases", "name=A").stdout.strip(), "P-1")
        self.assertEqual(self.run_tool("add", "edits", "summary=x").stdout.strip(), "E-1")
        self.assertEqual(self.run_tool("add", "changeLog", "summary=x").stdout.strip(), "1")
        self.assertEqual(self.run_tool("add", "reviews", "target=P-1").stdout.strip(), "R-1")
        self.assertIn("allocated by the script", self.refused("add", "phases", "id=P-7"))

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

    # --- invariants ---------------------------------------------------------------------------

    def test_status_moves_forward_only(self):
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", "status=in progress")
        self.run_tool("set", "phases.P-1", "status=done")
        self.assertIn("forward only", self.refused("set", "phases.P-1", "status=pending"))
        self.assertIn("must be one of", self.refused("set", "phases.P-1", "status=accepted"))

    def test_history_is_append_only(self):
        self.run_tool("add", "changeLog", "summary=x")
        self.run_tool("add", "reviews", "target=P-1")
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
        self.run_tool("add", "changeLog", "summary=2024")
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
        self.assertIn("key=value or @FILE", self.refused("set", "phases.P-1", "-"))

    def test_output_is_ascii_and_round_trips(self):
        self.run_tool("add", "phases", "name=A")
        self.run_tool("set", "phases.P-1", self.write_payload({"notes": f"a {DASH} b"}))
        shown = self.run_tool("get", "phases.P-1.notes").stdout.strip()  # run_tool decodes ascii
        self.assertEqual(shown, '"a \\u2014 b"')
        self.run_tool("set", "phases.P-1", "notes=" + shown.strip('"'))  # an agent copies it back
        self.assertEqual(self.state()["phases"][0]["notes"], f"a {DASH} b")

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
        self.file.write_text(json.dumps(bad), encoding="utf-8")
        err = self.refused("check")
        for problem in ("duplicate ids", "bad status 'accepted'", "prUrls must be a list",
                        "lastProcessedChangeLogId must be an integer", "stages.plan"):
            self.assertIn(problem, err)

    def test_invalid_json_file_fails_loudly(self):
        self.file.write_text("{not json", encoding="utf-8")
        self.assertIn("not valid JSON", self.refused("summary"))

    def test_two_state_files_need_an_explicit_path(self):
        (self.dir / "other").mkdir()
        (self.dir / "other" / "state.json").write_text(json.dumps(INITIAL), encoding="utf-8")
        self.assertIn("pass --file", self.refused("summary"))
        self.run_tool("--file", str(self.file), "summary")


if __name__ == "__main__":
    unittest.main(verbosity=1)
