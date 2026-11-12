#!/usr/bin/env python3
"""Tests for ModernizationHarness/tools/qaplan.py, Stage 7's test-plan and tracker tool.

Each test runs the real script as a subprocess - the way an agent calls it - against a fresh
state.json and features.json in a temporary directory, then reads the files back. The last test
opens a tracker in Excel itself, through PowerShell, where Excel is installed (Windows only); it
skips elsewhere. Excel repairs a file it cannot read without saying so, dropping the part it
could not read, so that test checks every feature survived rather than that the file opened.

Run:  uv run tests/test_qaplan_tool.py      (or: python tests/test_qaplan_tool.py)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.dom.minidom
import zipfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "ModernizationHarness" / "tools" / "qaplan.py"

STATE = {"project": "Demo", "schemaVersion": 1, "context": {"locations": {"documents": "out"}},
         "phases": [{"id": "P-1", "status": "done"}, {"id": "P-2", "status": "done"},
                    {"id": "P-3", "status": "pending"}],
         "edits": [], "changeLog": [], "reviews": []}


def row(rid, feature, build, phases, group=None):
    r = {"id": rid, "feature": feature, "howToCheck": [], "phases": phases, "build": build,
         "tested": "untested"}
    if group:
        r["group"] = group
    return r


LEDGER = {"app": "Demo", "schemaVersion": 1,
          "groups": [{"title": "Search", "before": [], "after": []}],
          "features": [row("FR-1", "Sign in", "built in P-1", ["P-1"]),
                       row("FR-3", "Search by name", "built in P-2", ["P-2"], "Search"),
                       row("VR-1", "Name of two letters or more", "built in P-2", ["P-2"],
                           "Search"),
                       row("FR-9", "Audit log", "scheduled in P-3", [])]}

SECTIONS = {"about": "First round.", "beforeYouStart": "Open https://test.example.",
            "accounts": "Clerk: clerk1 (password from the team lead).",
            "testData": "None needed.", "knownLimits": "None known."}


def case(title, checks, kind="Positive", priority="High", **extra):
    return {"title": title, "checks": checks, "type": kind, "priority": priority,
            "steps": ["Open the search page", "Press Search"], "expect": "Results show", **extra}


FULL = {"set": SECTIONS,
        "add": [case("Clerk signs in", ["FR-1"], "Smoke"),
                case("Search smith", ["FR-3"]),
                case("One letter refused", ["VR-1"], "Negative", "Medium")]}


class QaPlanTool(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "out").mkdir()
        self.write_json("out/state.json", STATE)
        self.write_json("out/features.json", LEDGER)
        self.n = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- helpers -------------------------------------------------------------------------

    def write_json(self, rel, data):
        path = self.tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def run_tool(self, *args, code=0):
        p = subprocess.run([sys.executable, str(TOOL), *args], cwd=self.tmp,
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, code, f"exit {p.returncode}\n{p.stdout}\n{p.stderr}")
        return p.stdout + p.stderr

    def apply(self, values, *flags, code=0):
        self.n += 1
        rel = f".harness-tmp/v{self.n}.json"
        self.write_json(rel, values)
        return self.run_tool("apply", f"@{rel}", *flags, code=code)

    @property
    def qa(self):
        return self.tmp / "out" / "qa"

    def record(self):
        return json.loads((self.qa / "qa_plan.json").read_text(encoding="utf-8"))

    def plan(self):
        return (self.qa / "Demo_TEST_PLAN.md").read_text(encoding="utf-8")

    def ledger_edit(self, fn):
        path = self.tmp / "out" / "features.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for r in data["features"]:
            fn(r)
        path.write_text(json.dumps(data), encoding="utf-8")

    def sheet(self, version, name="sheet1"):
        with zipfile.ZipFile(self.qa / f"Demo_TEST_TRACKER_v{version}.xlsx") as z:
            return z.read(f"xl/worksheets/{name}.xml").decode("utf-8")

    def changed_column(self, version):
        """The 'Changed since last version?' cells, in row order."""
        dom = xml.dom.minidom.parseString(self.sheet(version))
        out = []
        for c in dom.getElementsByTagName("c"):
            ref = c.getAttribute("r")
            if ref.startswith("J") and ref != "J1":
                out.append(c.getElementsByTagName("t")[0].firstChild.data)
        return out

    # --- apply -----------------------------------------------------------------------------

    def test_apply_creates_record_and_plan_and_gives_out_ids(self):
        out = self.apply(FULL)
        self.assertIn("added TC-1..TC-3 (3)", out)
        rec = self.record()
        self.assertEqual([c["id"] for c in rec["cases"]], ["TC-1", "TC-2", "TC-3"])
        self.assertEqual(rec["nextId"], 4)
        self.assertFalse((self.tmp / ".harness-tmp" / "v1.json").exists(), "values file kept")
        plan = self.plan()
        self.assertIn("#### TC-2 — Search smith", plan)
        self.assertIn("1. Open the search page\n2. Press Search", plan)
        self.assertIn("| FR-9 | Audit log | planned |", plan)
        self.assertIn("### Smoke tests", plan)
        self.assertIn("### Search", plan)
        self.assertLess(plan.index("### Smoke tests"), plan.index("### Search"))

    def test_steps_lose_their_own_numbers(self):
        self.apply({"set": SECTIONS, "add": [dict(case("x", ["FR-1"], "Smoke"),
                                                   steps=["1. Open it", "2) Sign in"])]})
        self.assertEqual(self.record()["cases"][0]["steps"], ["Open it", "Sign in"])

    def test_apply_is_all_or_none(self):
        bad = {"set": SECTIONS, "add": [case("good", ["FR-1"]), case("bad", ["FR-404"])]}
        out = self.apply(bad, code=1)
        self.assertIn("FR-404 is not a ledger row", out)
        self.assertFalse((self.qa / "qa_plan.json").exists())

    def test_apply_refusals(self):
        self.apply(FULL)
        cases = [
            ({"add": [case("unbuilt", ["FR-9"])]}, "FR-9 is not built"),
            ({"add": [case("no checks", [], "Positive")]}, "only a Smoke case may"),
            ({"add": [dict(case("no steps", ["FR-1"]), steps=[])]}, "steps must be"),
            ({"add": [dict(case("x", ["FR-1"]), id="TC-99")]}, "the tool gives out ids"),
            ({"add": [case("x", ["FR-1"], "Exploratory")]}, "type must be one of"),
            ({"add": [case("x", ["FR-1"], priority="Urgent")]}, "priority must be one of"),
            ({"edit": [{"id": "TC-77", "title": "x"}]}, "TC-77 is not an active case"),
            ({"retire": [{"id": "TC-1"}]}, "a reason is required"),
            ({"exclude": [{"id": "FR-3", "reason": "x"}]}, "checked by TC-2"),
            ({"set": {"intro": "x"}}, "intro is not a section"),
            ({"allow": [{"text": "E-1", "where": "TC-99", "reason": "x"}]}, "where must be"),
        ]
        for values, message in cases:
            with self.subTest(message):
                self.assertIn(message, self.apply(values, code=1))
        self.assertIn("unknown key", self.apply({"remove": []}, code=2))

    def test_smoke_case_may_check_nothing(self):
        self.apply({"set": SECTIONS, "add": [case("App starts", [], "Smoke")]})
        self.assertEqual(self.record()["cases"][0]["checks"], [])
        self.assertIn("**Checks:** —", self.plan())

    def test_edit_retire_exclude_and_ids_never_reused(self):
        self.apply(FULL)
        self.apply({"retire": [{"id": "TC-3", "reason": "merged into TC-2"}],
                    "edit": [{"id": "TC-2", "checks": ["FR-3", "VR-1"], "title": "Search"}]})
        self.apply({"add": [case("Another", ["FR-3"])]})
        rec = self.record()
        self.assertEqual(rec["cases"][-1]["id"], "TC-4")
        retired = next(c for c in rec["cases"] if c["id"] == "TC-3")
        self.assertEqual((retired["status"], retired["reason"]), ("retired", "merged into TC-2"))
        self.assertIn("### Retired test cases", self.plan())
        self.apply({"retire": [{"id": "TC-1", "reason": "x"}],
                    "exclude": [{"id": "FR-1", "reason": "checked by automated tests"}]})
        self.assertIn("| FR-1 | Sign in | checked by automated tests |", self.plan())
        self.assertIn("FR-1 is recorded as not tested by hand",
                      self.apply({"add": [case("x", ["FR-1"])]}, code=1))
        self.apply({"unexclude": ["FR-1"]})
        self.assertEqual(self.record()["excluded"], [])

    def test_hand_edited_plan_is_never_overwritten_without_force(self):
        self.apply(FULL)
        path = self.qa / "Demo_TEST_PLAN.md"
        path.write_text(self.plan().replace("First round.", "Edited."), encoding="utf-8")
        self.assertIn("changed by hand", self.apply({"set": {"about": "Second."}}, code=1))
        self.assertIn("changed by hand", self.run_tool("check", code=1))
        self.apply({"set": {"about": "Edited."}}, "--force")
        self.assertIn("Edited.", self.plan())
        self.run_tool("check")

    def test_plan_keeps_crlf_line_endings(self):
        self.apply(FULL)
        path = self.qa / "Demo_TEST_PLAN.md"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.apply({"set": {"about": "Second."}})
        self.assertIn(b"Second.\r\n", path.read_bytes())

    # --- check -----------------------------------------------------------------------------

    def test_check_finds_gaps_and_empty_sections(self):
        self.apply({"add": [case("Search", ["FR-3"])]})
        out = self.run_tool("check", code=1)
        self.assertIn("built but not covered", out)
        self.assertIn("FR-1, VR-1", out)
        self.assertIn('section "1. About this plan" is empty', out)

    def test_check_passes_a_full_plan_and_warns(self):
        self.apply(dict(FULL, set=dict(SECTIONS, accounts="Clerk - to confirm")))
        out = self.run_tool("check")
        self.assertIn("ok: 3 active cases", out)
        self.assertIn("still marked To confirm: accounts", out)
        self.assertIn("no tracker yet", out)

    def test_harness_words_and_allowed_exceptions(self):
        self.apply(FULL)
        self.apply({"edit": [{"id": "TC-2", "expect": "Error E-102 shows"}],
                    "set": {"knownLimits": "Built in P-2; see stage 7 and qaplan.py."}})
        out = self.run_tool("check", code=1)
        for found in ('"E-102" in TC-2', '"P-2" in knownLimits', '"stage 7" in knownLimits',
                      '"qaplan.py" in knownLimits'):
            self.assertIn(found, out)
        self.apply({"set": {"knownLimits": "None known."},
                    "allow": [{"text": "E-102", "where": "TC-2", "reason": "the app's code"},
                              {"text": "Q3", "where": "TC-1", "reason": "unused"}]})
        out = self.run_tool("check")
        self.assertIn('allowed "Q3" in TC-1 no longer occurs', out)
        self.apply({"unallow": [{"text": "Q3", "where": "TC-1"}]})
        self.assertNotIn("no longer occurs", self.run_tool("check"))

    def test_a_ledger_name_with_a_harness_id_is_allowed_as_ledger(self):
        self.ledger_edit(lambda r: r.update(feature="Audit log (see R-2)")
                         if r["id"] == "FR-9" else None)
        self.apply(FULL)
        self.assertIn('"R-2" in ledger', self.run_tool("check", code=1))
        self.apply({"allow": [{"text": "R-2", "where": "ledger", "reason": "the name"}]})
        self.run_tool("check")

    # --- build -----------------------------------------------------------------------------

    def test_build_refuses_an_incomplete_record(self):
        self.apply({"set": SECTIONS, "add": [case("Search", ["FR-3"])]})
        self.assertIn("build needs a clean record", self.run_tool("build", code=1))
        self.assertFalse((self.qa / "Demo_TEST_TRACKER_v1.xlsx").exists())

    def test_build_versions(self):
        self.apply(FULL)
        self.assertIn("wrote Demo_TEST_TRACKER_v1.xlsx: 3 cases", self.run_tool("build"))
        self.assertEqual(self.changed_column(1), ["—"] * 3)
        self.assertIn("Demo_TEST_TRACKER_v1.xlsx", self.plan())
        self.assertIn("unchanged", self.run_tool("build"))
        # untouched: a change replaces v1 in place
        self.apply({"edit": [{"id": "TC-3", "expect": "Message: two letters or more"}]})
        self.assertIn("replaced Demo_TEST_TRACKER_v1.xlsx", self.run_tool("build"))
        self.assertEqual(len(self.record()["trackers"]), 1)
        # the tester saves it: only the plan changes when nothing in the tracker would
        v1 = self.qa / "Demo_TEST_TRACKER_v1.xlsx"
        v1.write_bytes(v1.read_bytes() + b"saved")
        saved = v1.read_bytes()
        self.apply({"set": {"accounts": "Clerk: qa-clerk"}})
        self.assertIn("kept: nothing in it would change", self.run_tool("build"))
        self.assertIn("qa-clerk", self.plan())
        # a rebuilt feature, a new feature, a changed case -> v2, the saved v1 untouched
        self.ledger_edit(lambda r: r["phases"].append("E-1") if r["id"] == "FR-3" else None)
        self.ledger_edit(lambda r: r.update(build="built in P-3", phases=["P-3"])
                         if r["id"] == "FR-9" else None)
        self.assertIn("built but not covered", self.run_tool("build", code=1))
        self.apply({"add": [case("Audit entry", ["FR-9"], priority="Medium")]})
        self.assertIn("wrote Demo_TEST_TRACKER_v2.xlsx: 4 cases, 2 marked changed or new "
                      "since v1", self.run_tool("build"))
        self.assertEqual(v1.read_bytes(), saved)
        self.assertEqual(self.changed_column(2), ["No", "Yes", "No", "New"])
        self.assertIn("*Version 2", self.plan())
        rec = self.record()
        self.assertEqual([t["version"] for t in rec["trackers"]], [1, 2])
        self.assertEqual(rec["trackers"][1]["ledger"]["FR-3"]["phases"], ["P-2", "E-1"])

    def test_check_says_when_the_tracker_is_out_of_date(self):
        self.apply(FULL)
        self.run_tool("build")
        self.assertNotIn("out of date", self.run_tool("check"))
        self.apply({"add": [case("More", ["FR-3"])]})
        self.assertIn("rewrites it in place", self.run_tool("check"))
        self.run_tool("build")
        v1 = self.qa / "Demo_TEST_TRACKER_v1.xlsx"
        v1.write_bytes(v1.read_bytes() + b"saved")
        self.apply({"add": [case("Yet more", ["FR-3"])]})
        self.assertIn("writes the next version, v2", self.run_tool("check"))

    def test_a_missing_tracker_is_never_rewritten_under_its_old_name(self):
        self.apply(FULL)
        self.run_tool("build")
        (self.qa / "Demo_TEST_TRACKER_v1.xlsx").unlink()
        self.assertIn("not in qa/", self.run_tool("build"))
        self.assertFalse((self.qa / "Demo_TEST_TRACKER_v1.xlsx").exists())
        self.apply({"add": [case("More", ["FR-3"])]})
        self.assertIn("wrote Demo_TEST_TRACKER_v2.xlsx", self.run_tool("build"))

    def test_status_reports_what_changed(self):
        self.assertIn("record: none yet", self.run_tool("status"))
        self.apply(FULL)
        self.run_tool("build")
        self.ledger_edit(lambda r: r["phases"].append("E-1") if r["id"] == "FR-3" else None)
        self.ledger_edit(lambda r: r.update(build="built in P-3", phases=["P-3"])
                         if r["id"] == "FR-9" else None)
        out = self.run_tool("status")
        self.assertIn("newly built FR-9", out)
        self.assertIn("rebuilt FR-3 (P-2 -> P-2, E-1)", out)
        self.assertIn("not covered (built, no case, not excluded): FR-9", out)
        self.assertIn("exactly as written", out)

    # --- the tracker file ------------------------------------------------------------------

    def test_tracker_is_valid_office_xml(self):
        self.apply(FULL)
        self.run_tool("build")
        path = self.qa / "Demo_TEST_TRACKER_v1.xlsx"
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            for name in names:
                xml.dom.minidom.parseString(z.read(name))  # every part is well-formed XML
            workbook = z.read("xl/workbook.xml").decode()
        for part in ("[Content_Types].xml", "_rels/.rels", "xl/workbook.xml", "xl/styles.xml",
                     "xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"):
            self.assertIn(part, names)
        self.assertIn('name="Test cases"', workbook)
        self.assertIn('name="Summary"', workbook)
        self.assertIn('fullCalcOnLoad="1"', workbook)
        cases = self.sheet(1)
        self.assertIn('state="frozen"', cases)
        self.assertIn('<autoFilter ref="A1:P4"/>', cases)
        self.assertIn('"Not run,Pass,Fail,Blocked,Skipped"', cases)
        self.assertEqual(cases.count('<cfRule type="cellIs"'), 3)
        summary = self.sheet(1, "sheet2")
        self.assertIn("COUNTIF('Test cases'!$K$2:$K$4,\"Pass\")", summary)
        self.assertIn("SUMPRODUCT(('Test cases'!$B$2:$B$4=$A", summary)  # exact, no wildcards

    def test_same_record_gives_the_same_bytes(self):
        self.apply(FULL)
        self.run_tool("build")
        first = (self.qa / "Demo_TEST_TRACKER_v1.xlsx").read_bytes()
        (self.qa / "Demo_TEST_TRACKER_v1.xlsx").unlink()
        rec = self.record()
        rec["trackers"] = []
        self.write_json("out/qa/qa_plan.json", rec)
        self.run_tool("build")
        self.assertEqual((self.qa / "Demo_TEST_TRACKER_v1.xlsx").read_bytes(), first)

    def test_usage_and_malformed(self):
        self.assertIn("Usage:", self.run_tool(code=2))
        self.assertIn("does not take --developer-said",
                      self.run_tool("build", "--developer-said", code=2))
        self.assertIn('takes one "@FILE"', self.run_tool("apply", code=2))

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell"), "Windows only")
    def test_excel_opens_it_with_every_feature(self):
        """Opens the tracker in Excel itself; skipped where Excel is not installed. The two group
        names would match each other as COUNTIF patterns - Q*A matches QzzA - so the per-area
        totals prove the counts are exact."""
        path = self.tmp / "out" / "features.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["groups"] = [{"title": "Q*A", "before": [], "after": []},
                          {"title": "QzzA", "before": [], "after": []}]
        for r in data["features"]:
            r.update({"FR-3": {"group": "Q*A"}, "VR-1": {"group": "QzzA"}}.get(r["id"], {}))
        path.write_text(json.dumps(data), encoding="utf-8")
        self.apply(FULL)
        self.run_tool("build")
        path = self.qa / "Demo_TEST_TRACKER_v1.xlsx"
        script = (
            "$ErrorActionPreference='Stop';"
            "try { $x = New-Object -ComObject Excel.Application } catch { 'NO-EXCEL'; exit 0 };"
            "$x.DisplayAlerts=$false;"
            "try { $wb=$x.Workbooks.Open('" + str(path) + "',0,$true);"
            "$ws=$wb.Worksheets.Item(1); $ws.Activate();"
            "'sheets=' + (($wb.Worksheets | ForEach-Object { $_.Name }) -join ',');"
            "'filter=' + $ws.AutoFilterMode; 'frozen=' + $x.ActiveWindow.FreezePanes;"
            "'list=' + $ws.Range('K2').Validation.Formula1;"
            "'rules=' + $ws.Range('K2:K4').FormatConditions.Count;"
            "$x.Calculate(); 'notrun=' + $wb.Worksheets.Item(2).Range('B4').Text;"
            "'total=' + $wb.Worksheets.Item(2).Range('B9').Text;"
            "'areas=' + ((15..17 | ForEach-Object { $wb.Worksheets.Item(2).Range('A' + $_).Text + ':'"
            " + $wb.Worksheets.Item(2).Range('G' + $_).Text }) -join ',');"
            "$wb.Close($false) } finally { $x.Quit() }")
        p = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                           capture_output=True, text=True, timeout=180)
        if "NO-EXCEL" in p.stdout:
            self.skipTest("Excel is not installed")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for line in ("sheets=Test cases,Summary", "filter=True", "frozen=True",
                     "list=Not run,Pass,Fail,Blocked,Skipped", "rules=3", "notrun=3",
                     "total=3", "areas=Smoke tests:1,Q*A:1,QzzA:1"):
            self.assertIn(line, p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
