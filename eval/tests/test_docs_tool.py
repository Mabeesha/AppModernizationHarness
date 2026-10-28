#!/usr/bin/env python3
"""Tests for ModernizationHarness/tools/docs.py, the feature-ledger and plan tool.

Each test runs the real script as a subprocess — the way an agent calls it — against a fresh
state.json, features.json and plan in a temporary directory, then reads the files back.

Run:  uv run tests/test_docs_tool.py      (or: python tests/test_docs_tool.py)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / "ModernizationHarness" / "tools"
TOOL = TOOLS / "docs.py"
STATE_TOOL = TOOLS / "state.py"
DASH, ARROW = "—", "→"
TODAY = date.today().isoformat()

STATE = {
    "project": "Demo",
    "schemaVersion": 1,
    "context": {"locations": {"documents": "out"}},
    "stages": {"plan": {"status": "complete", "rerunCount": 0}},
    "phases": [
        {"id": "P-1", "name": "Walking skeleton", "status": "done"},
        {"id": "P-2", "name": "Employee search", "status": "done"},
        {"id": "P-3", "name": "Export", "status": "in progress"},
        {"id": "P-4", "name": "Audit", "status": "pending"},
    ],
    "droppedPhases": ["P-5"],
    "edits": [{"id": "E-1", "summary": "label", "afterPhase": "P-2", "status": "done"}],
    "changeLog": [],
    "reviews": [],
    "progress": {"lastProcessedChangeLogId": 0, "lastProcessedReviewNumber": 0},
}

# The ledger exactly as Stage 3's Output 2 template shaped it before features.json.
TEMPLATE_LEDGER = f"""# Feature Status: Demo

*What has been built, how to check it, and what the developer has tested.
Rows are never deleted. Updated by the Implement stage at every hand-off.*

| ID | Feature | How to check | Phase(s) | Build | Tested |
|---|---|---|---|---|---|
| FR-3 | Employee search by name | `GET /api/employees?q=smith` {ARROW} 200, 3 rows | P-2 | built in P-2 | passed 2026-02-14 |
| FR-7 | CSV export | Search screen {ARROW} *Export* {ARROW} file downloads<br>3 rows in it | P-2, E-1 | built in P-2 | untested |
| FR-9 | Audit log | {DASH} | {DASH} | scheduled in P-4 | untested |
| FR-10 | Pipe a \\| b | {DASH} | {DASH} | unscheduled | failed 2026-03-01 {DASH} returns 500 |
"""

# A grouped ledger, shaped like a real one: the title at ##, groups at #, a table per group,
# note lines around the tables.
GROUPED_LEDGER = f"""## Feature Status: RMM

Kept up to date by the build agent.

# Platform, data and build

Covers the scaffold and the data layer.

| ID | Feature | How to check | Phase(s) | Build | Tested |
|---|---|---|---|---|---|
| FR-1 | Scaffold | `dotnet build` {ARROW} 0 errors | P-1 | built in P-1 | passed 2026-02-01 |
| FR-2 | DB mapping | {DASH} | {DASH} | scheduled in P-4 | untested |

A note between the tables.

# Auth and roles

| ID | Feature | How to check | Phase(s) | Build | Tested |
|---|---|---|---|---|---|
| FR-3 | Login | sign in as dev1 | P-2 | built in P-2 | untested |

Roles come from LLD section 4.

```text
| ID | Feature | How to check | Phase(s) | Build | Tested |
# not a group
```

# Reporting

| ID | Feature | How to check | Phase(s) | Build | Tested |
|---|---|---|---|---|---|
| FR-4 | Export | {DASH} | {DASH} | unscheduled | untested |
"""

PLAN = f"""# Phased Implementation Plan: Demo

## 1. Overview
- Remaining phases below.

```mermaid
flowchart LR
## 5. not a heading inside a fence
```

## 2. Completed
- P-1 {DASH} Walking skeleton {DASH} delivered the scaffold.

## 3. Plan Revision History
| date | what |
|---|---|

## 4. Assumptions & Prerequisites
- none

## 5. Phases (remaining)

## Phase P-2: Employee search
- **Goal:** search {ARROW} results.

### Tasks
#### [P-2.T-1] Endpoint
- **Done when:** it answers.

### Exit criteria (mechanical {DASH} the agent gate)
- [ ] build green

## Phase P-3: Export
- **Goal:** export.

## Phase P-4: Audit
- **Goal:** audit.

## 6. Risks & Open Questions
- none

## 7. Coverage
Coverage lives in `FEATURE_STATUS.md`.
"""


class DocsToolTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.out = self.dir / "out"
        self.out.mkdir()
        self.state_file = self.out / "state.json"
        self.state_file.write_text(json.dumps(STATE), encoding="utf-8")
        self.features = self.out / "features.json"
        self.view = self.out / "FEATURE_STATUS.md"
        self.plan = self.out / "PLAN_Demo.md"

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, *args, ok=True, tool=TOOL):
        res = subprocess.run([sys.executable, str(tool), *args], cwd=self.dir,
                             capture_output=True, encoding="ascii")
        if ok:
            self.assertEqual(res.returncode, 0, f"{args} failed: {res.stderr}")
        else:
            self.assertNotEqual(res.returncode, 0, f"{args} should have been refused")
        return res

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.out.iterdir() if p.is_file()}

    def refused(self, *args):
        """Assert the command fails, prints nothing on stdout, and changes no file."""
        before = self.snapshot()
        res = self.run_tool(*args, ok=False)
        self.assertEqual(self.snapshot(), before, f"{args} changed a file on refusal")
        self.assertEqual(res.stdout, "", f"{args} printed output although it was refused")
        self.assertEqual(list(self.dir.rglob("*.tmp")), [], f"{args} left a temp file")
        return res.stderr

    def ledger(self):
        return json.loads(self.features.read_text(encoding="utf-8"))

    def row(self, rid):
        return next(r for r in self.ledger()["features"] if r["id"] == rid)

    def payload(self, obj, name="values.json", encoding="utf-8"):
        path = self.dir / ".harness-tmp" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding=encoding)
        return "@" + str(path)

    def imported(self):
        self.view.write_text(TEMPLATE_LEDGER, encoding="utf-8")
        return self.run_tool("feature", "import", str(self.view)).stdout

    # --- help and the values folder -----------------------------------------------------------

    def test_no_command_prints_help(self):
        res = self.run_tool(ok=False)
        self.assertEqual(res.returncode, 2)
        self.assertIn("feature show", res.stdout)
        self.assertIn("plan complete", res.stdout)

    def test_both_tools_create_the_values_folder_without_a_gitignore(self):
        # GitLab Duo's file tools refuse a git-ignored path, so the folder no longer ignores
        # itself; the .gitignore of "*" older versions wrote is removed, any other kept.
        folder = self.dir / ".harness-tmp"
        ignore = folder / ".gitignore"
        for tool in (TOOL, STATE_TOOL):
            with self.subTest(tool=tool.name):
                if folder.exists():
                    folder.rmdir()
                args = ("summary",) if tool == STATE_TOOL else ("plan", "check")
                self.run_tool(*args, ok=tool == STATE_TOOL, tool=tool)
                self.assertTrue(folder.is_dir())
                self.assertFalse(ignore.exists())
                ignore.write_bytes(b"*\n")
                res = self.run_tool(*args, ok=tool == STATE_TOOL, tool=tool)
                self.assertFalse(ignore.exists(), "the old .gitignore was not removed")
                self.assertIn("removed", res.stderr)

    def test_values_folder_keeps_a_gitignore_someone_changed(self):
        (self.dir / ".harness-tmp").mkdir()
        (self.dir / ".harness-tmp" / ".gitignore").write_text("*\n# mine\n", encoding="ascii")
        self.run_tool(ok=False)
        self.assertIn("# mine", (self.dir / ".harness-tmp" / ".gitignore").read_text())

    def test_a_values_file_is_deleted_once_read_whatever_the_outcome(self):
        self.imported()
        values = self.dir / ".harness-tmp" / "values.json"
        # success: several new rows from one file
        res = self.run_tool("feature", "add", self.payload([{"id": "FR-20", "feature": "a"},
                                                             {"id": "FR-21", "feature": "b"}]))
        self.assertEqual(res.stdout, "added FR-20\nadded FR-21\n")  # the note is on stderr
        self.assertIn("removed", res.stderr)
        self.assertFalse(values.exists())
        # success: one row's fields from a file after its id
        self.run_tool("feature", "set", "FR-20", self.payload({"feature": "a, renamed"}))
        self.assertEqual(self.row("FR-20")["feature"], "a, renamed")
        self.assertFalse(values.exists())
        # a rule refusal, a malformed file and a plan replace that matches nothing
        self.plan.write_text(PLAN, encoding="utf-8")
        (self.dir / ".harness-tmp" / "bad.json").write_text("{not json", encoding="utf-8")
        for name, args in (("refusal.json", ("feature", "set", self.payload(
                               [{"id": "FR-20", "tested": "passed"}], name="refusal.json"))),
                           ("bad.json", ("feature", "set", "@" + str(self.dir / ".harness-tmp"
                                                                     / "bad.json"))),
                           ("replace.json", ("plan", "replace", self.payload(
                               [{"old": "no such text anywhere", "new": "x"}],
                               name="replace.json")))):
            with self.subTest(name):
                path = self.dir / ".harness-tmp" / name
                self.assertTrue(path.exists())
                self.assertIn("removed", self.refused(*args))
                self.assertFalse(path.exists(), f"{name}: values file left behind")

    def test_a_values_file_outside_the_folder_is_kept(self):
        self.imported()
        outside = self.dir / "rows.json"
        outside.write_text(json.dumps([{"id": "FR-20", "feature": "a"}]), encoding="utf-8")
        res = self.run_tool("feature", "add", "@" + str(outside))
        self.assertTrue(outside.exists())
        self.assertNotIn("removed", res.stderr)

    # --- import -------------------------------------------------------------------------------

    def test_import_of_a_template_shaped_ledger(self):
        out = self.imported()
        self.assertIn("imported 4 rows: FR-3, FR-7, FR-9, FR-10", out)
        self.assertIn("FEATURE_STATUS.md.bak", out)
        self.assertNotIn("note:", out)  # title and the two-line italic note are regenerated
        self.assertEqual(self.row("FR-7"), {
            "id": "FR-7", "feature": "CSV export",
            "howToCheck": [f"Search screen {ARROW} *Export* {ARROW} file downloads", "3 rows in it"],
            "phases": ["P-2", "E-1"], "build": "built in P-2", "tested": "untested"})
        self.assertEqual(self.row("FR-9")["howToCheck"], [])
        self.assertEqual(self.row("FR-9")["phases"], [])
        self.assertEqual(self.row("FR-10")["feature"], "Pipe a | b")
        self.assertEqual(self.row("FR-10")["tested"], f"failed 2026-03-01 {DASH} returns 500")
        self.assertEqual((self.out / "FEATURE_STATUS.md.bak").read_text(encoding="utf-8"),
                         TEMPLATE_LEDGER)
        self.assertEqual(self.run_tool("feature", "check").stdout.strip(), "ok (4 rows)")

    def test_render_round_trips_through_import(self):
        self.imported()
        rendered = self.view.read_text(encoding="utf-8")
        self.assertTrue(rendered.startswith("<!-- generated by tools/docs.py"))
        self.assertIn("| FR-10 | Pipe a \\| b |", rendered)
        self.assertIn("file downloads<br>3 rows in it", rendered)
        first = self.ledger()
        self.features.unlink()
        self.run_tool("feature", "import", str(self.view))
        self.assertEqual(self.ledger(), first)

    def test_import_refuses_rows_it_cannot_parse_and_names_them(self):
        bad = TEMPLATE_LEDGER.replace("| built in P-2 | untested |", "| built | untested |") \
            .replace("| scheduled in P-4 |", "| scheduled in P-44 |") \
            .replace("passed 2026-02-14", "passed yesterday") \
            + "| FR-3 | again | x | P-2 | built in P-2 | untested |\n" \
            + "| FR-11 | short row | x |\n"
        self.view.write_text(bad, encoding="utf-8")
        err = self.refused("feature", "import", str(self.view))
        self.assertIn("nothing written", err)
        for problem in ("(FR-7): FR-7: build must be", "(FR-9): FR-9: scheduled in P-44",
                        "(FR-3): FR-3: tested must be", "duplicate id FR-3", "3 cells, expected 6"):
            self.assertIn(problem, err)
        self.assertFalse(self.features.exists())

    def test_import_never_invents_a_tested_date(self):
        old = TEMPLATE_LEDGER.replace("passed 2026-02-14", "passed") \
            .replace(f"failed 2026-03-01 {DASH} returns 500", "failed 2026-03-01 - returns 500")
        self.view.write_text(old, encoding="utf-8")
        err = self.refused("feature", "import", str(self.view))
        self.assertIn("(FR-3): FR-3: tested must be", err)
        self.assertIn("(FR-10): FR-10: tested must be", err)
        self.assertFalse(self.features.exists())

    def _older_forms(self):
        return TEMPLATE_LEDGER + (
            "| C2 | Strict parity | P-1 part: verbatim | P-1..P-4 | built in P-1 | untested |\n"
            "| A-2 | Menu gate | Server part: authorities | P-2, P-4 | "
            "built in P-2 (server); P-4 (client) | untested |\n")

    def test_import_refuses_a_split_build_without_a_choice(self):
        self.view.write_text(self._older_forms(), encoding="utf-8")
        err = self.refused("feature", "import", str(self.view))
        self.assertIn("(A-2): build 'built in P-2 (server); P-4 (client)' names several phases",
                      err)
        self.assertIn("--split-scheduled", err)
        self.assertNotIn("C2", err)  # the range alone converts without a choice
        self.assertIn("not both", self.run_tool("feature", "import", str(self.view),
                                                "--split-scheduled", "--split-built",
                                                ok=False).stderr)

    def test_import_converts_ranges_and_split_builds(self):
        self.view.write_text(self._older_forms(), encoding="utf-8")
        out = self.run_tool("feature", "import", str(self.view), "--split-scheduled").stdout
        self.assertIn("C2: phases P-1..P-4 imported as P-1 to P-4", out)
        self.assertIn("A-2: build 'built in P-2 (server); P-4 (client)' imported as "
                      "'scheduled in P-4'", out)
        self.assertEqual(self.row("C2")["phases"], ["P-1", "P-2", "P-3", "P-4"])
        a2 = self.row("A-2")
        self.assertEqual((a2["build"], a2["phases"]), ("scheduled in P-4", ["P-2", "P-4"]))
        self.assertEqual(a2["howToCheck"][-1],
                         "Build before import: built in P-2 (server); P-4 (client)")
        self.run_tool("feature", "check")

    def test_import_split_built_counts_the_first_phase(self):
        self.view.write_text(self._older_forms(), encoding="utf-8")
        self.run_tool("feature", "import", str(self.view), "--split-built")
        self.assertEqual(self.row("A-2")["build"], "built in P-2")

    def test_import_runs_once(self):
        self.imported()
        self.assertIn("already exists", self.refused("feature", "import", str(self.view)))

    def test_import_warns_about_cross_checks_it_cannot_fix(self):
        self.view.write_text(TEMPLATE_LEDGER.replace("scheduled in P-4", "scheduled in P-1"),
                             encoding="utf-8")
        out = self.run_tool("feature", "import", str(self.view)).stdout
        self.assertIn("warning: FR-9: scheduled in P-1, which is done", out)
        self.assertIn("scheduled in P-1", self.refused("feature", "check"))

    def test_import_keeps_text_after_the_table(self):
        self.view.write_text(TEMPLATE_LEDGER + "\nA note the developer added.\n", encoding="utf-8")
        out = self.run_tool("feature", "import", str(self.view)).stdout
        self.assertIn("note: text after the ungrouped table now sits above it", out)
        self.assertEqual(self.ledger()["preamble"], ["A note the developer added."])
        self.assertIn("A note the developer added.", self.view.read_text(encoding="utf-8"))

    def test_single_table_ledger_renders_as_before(self):
        self.imported()
        self.assertNotIn("groups", self.ledger())
        self.assertNotIn("preamble", self.ledger())
        body = self.view.read_text(encoding="utf-8").split("\n", 1)[1]
        self.assertTrue(body.startswith(
            "# Feature Status: Demo\n\n*What has been built, how to check it, and what the "
            "developer has tested. Rows are never deleted.\nGenerated from `features.json` by "
            f"`tools/docs.py` {DASH} do not edit this file; tell the agent what you tested.*\n\n"
            "| ID | Feature | How to check | Phase(s) | Build | Tested |\n|---|---|---|---|---|---|\n"
            "| FR-3 |"))

    # --- groups -------------------------------------------------------------------------------

    def test_grouped_ledger_imports_every_table_and_round_trips(self):
        self.view.write_text(GROUPED_LEDGER, encoding="utf-8")
        out = self.run_tool("feature", "import", str(self.view)).stdout
        self.assertIn("imported 4 rows: FR-1, FR-2, FR-3, FR-4", out)
        self.assertIn("rows per group: Platform, data and build: 2; Auth and roles: 1; "
                      "Reporting: 1; total 4", out)
        self.assertIn("note: group headings at # are shown as ## under the title", out)
        self.assertEqual(out.count("note:"), 1)
        first = self.ledger()
        self.assertEqual(first["preamble"], ["Kept up to date by the build agent."])
        self.assertEqual(first["groups"], [
            {"title": "Platform, data and build", "before": ["Covers the scaffold and the data layer."],
             "after": ["A note between the tables."]},
            {"title": "Auth and roles", "before": [], "after": [
                "Roles come from LLD section 4.", "", "```text",
                "| ID | Feature | How to check | Phase(s) | Build | Tested |", "# not a group", "```"]},
            {"title": "Reporting", "before": [], "after": []}])
        self.assertEqual([r.get("group") for r in first["features"]],
                         ["Platform, data and build", "Platform, data and build", "Auth and roles",
                          "Reporting"])
        self.assertEqual(list(first["features"][0]),
                         ["id", "feature", "howToCheck", "phases", "build", "tested", "group"])
        view = self.view.read_text(encoding="utf-8")
        self.assertIn("## Platform, data and build\n\nCovers the scaffold and the data layer.\n\n"
                      "| ID | Feature", view)
        self.assertIn("| FR-2 | DB mapping |", view)
        self.assertIn("A note between the tables.\n\n## Auth and roles\n\n| ID |", view)
        self.assertEqual(self.run_tool("feature", "check").stdout.strip(), "ok (4 rows)")
        self.features.unlink()  # import the rendered view again: identical JSON
        self.run_tool("feature", "import", str(self.view))
        self.assertEqual(self.ledger(), first)
        self.assertEqual(self.view.read_text(encoding="utf-8"), view)

    def test_a_blank_line_inside_a_table_is_refused_not_lost(self):
        split = GROUPED_LEDGER.replace("| FR-1 | Scaffold", "\n| FR-1 | Scaffold")
        self.view.write_text(split, encoding="utf-8")
        err = self.refused("feature", "import", str(self.view))
        self.assertIn("a blank line splits the ledger table above", err)
        self.assertIn("remove it", err)
        self.assertFalse(self.features.exists())

    def test_a_table_with_other_columns_is_refused_not_kept_as_text(self):
        header = "| ID | Feature | How to check | Phase(s) | Build | Tested |"
        for bad in ("| ID | Feature | How to check | Phase(s) | Build | Tested | Notes |",
                    "| ID | Feature | How to check | Phase(s) | Build | Status |",
                    "| ID | Feature | How to check | Phase | Build | Tested |"):
            with self.subTest(header=bad):
                text = GROUPED_LEDGER.replace(f"# Reporting\n\n{header}", f"# Reporting\n\n{bad}")
                self.view.write_text(text, encoding="utf-8")
                err = self.refused("feature", "import", str(self.view))
                self.assertIn("this table's header is not the six ledger columns", err)
                self.assertIn("rename or remove the extra column", err)

    def test_a_heading_without_a_table_stays_text_and_round_trips(self):
        legend = GROUPED_LEDGER + "\n# Legend\n\nP-N is a phase.\n\n\n\nE-N is an edit.\n"
        self.view.write_text(legend, encoding="utf-8")
        out = self.run_tool("feature", "import", str(self.view)).stdout
        self.assertIn("note: heading(s) with no ledger table kept as text: # Legend", out)
        first = self.ledger()
        self.assertEqual([g["title"] for g in first["groups"]],
                         ["Platform, data and build", "Auth and roles", "Reporting"])
        self.assertEqual(first["groups"][-1]["after"],
                         ["# Legend", "", "P-N is a phase.", "", "E-N is an edit."])  # blanks collapsed
        view = self.view.read_text(encoding="utf-8")
        self.assertEqual(view.count("|---|---|---|---|---|---|"), 3)  # no empty table for the legend
        self.features.unlink()
        self.run_tool("feature", "import", str(self.view))
        self.assertEqual(self.ledger(), first)

    def test_import_refuses_what_it_cannot_place(self):
        twice = GROUPED_LEDGER.replace("# Reporting", "# Auth and roles")
        self.view.write_text(twice, encoding="utf-8")
        self.assertIn("two group headings read 'Auth and roles'",
                      self.refused("feature", "import", str(self.view)))
        no_sep = GROUPED_LEDGER.replace("| ID | Feature | How to check | Phase(s) | Build | Tested |\n"
                                        "|---|---|---|---|---|---|\n| FR-4", "| ID | Feature | How "
                                        "to check | Phase(s) | Build | Tested |\n| FR-4")
        self.view.write_text(no_sep, encoding="utf-8")
        self.assertIn("header is not followed by |---|", self.refused("feature", "import", str(self.view)))
        self.assertFalse(self.features.exists())

    def test_add_group_and_rows_in_it(self):
        self.run_tool("feature", "add", "FR-1", "feature=Login")
        self.assertIn("no group 'Auth'", self.refused("feature", "add", "FR-2", "feature=x", "group=Auth"))
        self.assertEqual(self.run_tool("feature", "add-group", "Auth").stdout, "added group Auth\n")
        self.assertIn("already exists", self.refused("feature", "add-group", "Auth"))
        self.run_tool("feature", "add", "FR-2", "feature=Roles", "group=Auth")
        self.assertIn("no group 'Nope'", self.refused("feature", "set", "FR-1", "group=Nope"))
        self.run_tool("feature", "set", "FR-1", "group=Auth")
        shown = [json.loads(l)["id"] for l in self.run_tool("feature", "show", "group=Auth").stdout.splitlines()]
        self.assertEqual(shown, ["FR-1", "FR-2"])
        self.run_tool("feature", "set", "FR-1", "group=")  # back to ungrouped
        self.assertNotIn("group", self.row("FR-1"))
        view = self.view.read_text(encoding="utf-8")
        self.assertLess(view.index("| FR-1 |"), view.index("## Auth"))
        self.assertLess(view.index("## Auth"), view.index("| FR-2 |"))
        self.assertEqual(list(self.ledger()), ["app", "schemaVersion", "groups", "features"])
        self.run_tool("feature", "check")

    def test_check_finds_a_row_whose_group_is_missing(self):
        self.run_tool("feature", "add", "FR-1", "feature=Login")
        ledger = self.ledger()
        ledger["features"][0]["group"] = "Gone"
        self.features.write_text(json.dumps(ledger), encoding="utf-8")
        self.assertIn("group 'Gone' is not in groups", self.refused("feature", "check"))

    # --- add and set --------------------------------------------------------------------------

    def test_add_creates_the_ledger_with_defaults(self):
        self.assertEqual(self.run_tool("feature", "add", "FR-1", "feature=Login").stdout,
                         "added FR-1\n")
        self.assertEqual(self.ledger(), {"app": "Demo", "schemaVersion": 1, "features": [{
            "id": "FR-1", "feature": "Login", "howToCheck": [], "phases": [],
            "build": "unscheduled", "tested": "untested"}]})
        self.assertIn("| FR-1 | Login | — | — | unscheduled | untested |",
                      self.view.read_text(encoding="utf-8"))

    def test_add_several_rows_from_a_file(self):
        rows = [{"id": f"FR-{n}", "feature": f"F{n}", "build": "scheduled in P-4"} for n in (1, 2)]
        self.assertEqual(self.run_tool("feature", "add", self.payload(rows)).stdout,
                         "added FR-1\nadded FR-2\n")
        self.assertEqual(self.row("FR-2")["build"], "scheduled in P-4")

    def test_add_refusals(self):
        self.run_tool("feature", "add", "FR-1", "feature=Login")
        self.assertIn("already a row", self.refused("feature", "add", "FR-1", "feature=x"))
        self.assertIn("new row is untested",
                      self.refused("feature", "add", "FR-2", "feature=x", "tested=passed"))
        self.assertIn("unknown option", self.refused("feature", "add", "FR-2", "feature=x",
                                                     "--developer-said"))
        self.assertIn("unknown field 'Feature'", self.refused("feature", "add", "FR-2", "Feature=x"))
        self.assertIn("bad id 'P-9'", self.refused("feature", "add", "P-9", "feature=x"))
        self.assertIn("scheduled in P-1, which is done",
                      self.refused("feature", "add", "FR-2", "feature=x", "build=scheduled in P-1"))
        self.assertIn("built in P-4, which has not started",
                      self.refused("feature", "add", "FR-2", "feature=x", "build=built in P-4"))
        self.assertIn("P-5, which is dropped",
                      self.refused("feature", "add", "FR-2", "feature=x", "build=scheduled in P-5"))
        self.assertIn("phases names E-7",
                      self.refused("feature", "add", "FR-2", "feature=x", "phases=E-7"))
        # a rule break against state.json is a refusal; an unknown id is a malformed command
        self.assertIn("refused: FR-2: scheduled in P-1",
                      self.refused("feature", "add", "FR-2", "feature=x", "build=scheduled in P-1"))
        self.assertNotIn("refused", self.refused("feature", "add", "FR-2", "feature=x",
                                                 "build=scheduled in P-9"))

    def test_add_refuses_while_an_unmigrated_markdown_ledger_exists(self):
        self.view.write_text(TEMPLATE_LEDGER, encoding="utf-8")
        self.assertIn("feature import", self.refused("feature", "add", "FR-1", "feature=x"))

    def test_set_updates_in_place_and_phases_only_grow(self):
        self.imported()
        out = self.run_tool("feature", "set", "FR-9", "build=built in P-3", "phases=P-3",
                            "howToCheck=GET /api/audit \\u2192 200").stdout
        self.assertEqual(json.loads(out)["howToCheck"], [f"GET /api/audit {ARROW} 200"])
        self.run_tool("feature", "set", "FR-7", "phases=P-3,P-2")
        self.assertEqual(self.row("FR-7")["phases"], ["P-2", "E-1", "P-3"])
        self.assertIn("ids are permanent", self.refused("feature", "set", "FR-7", "id=FR-77"))
        self.assertIn("no row 'FR-99'", self.refused("feature", "set", "FR-99", "feature=x"))
        self.assertIn("build must be", self.refused("feature", "set", "FR-7", "build=done"))

    def test_set_several_rows_in_one_call(self):
        self.imported()
        values = self.payload([
            {"id": "FR-9", "build": "built in P-3", "phases": ["P-3"],
             "howToCheck": [f"Audit screen {ARROW} 1 row", "export it"]},
            {"id": "FR-7", "tested": "untested", "phases": ["P-3"]}])
        out = self.run_tool("feature", "set", values).stdout.splitlines()
        self.assertEqual([json.loads(line)["id"] for line in out], ["FR-9", "FR-7"])
        self.assertEqual(self.row("FR-9")["howToCheck"][0], f"Audit screen {ARROW} 1 row")

    def test_set_file_refuses_an_inner_id_that_differs_from_its_key(self):
        self.imported()
        err = self.refused("feature", "set", self.payload({"FR-9": {"id": "FR-99", "feature": "x"}}))
        self.assertIn("refused: FR-9", err)

    def test_new_rows_are_written_in_schema_order(self):
        rows = [{"build": "unscheduled", "feature": "Login", "id": "FR-1"}]
        self.run_tool("feature", "add", self.payload(rows))
        self.assertEqual(list(self.ledger()["features"][0]),
                         ["id", "feature", "howToCheck", "phases", "build", "tested"])

    def test_set_is_all_or_nothing(self):
        self.imported()
        values = self.payload({"FR-9": {"build": "built in P-3"}, "FR-7": {"build": "nonsense"}})
        self.refused("feature", "set", values)

    def test_tested_needs_the_developer_flag_except_untested(self):
        self.imported()
        err = self.refused("feature", "set", "FR-7", "tested=passed")
        self.assertIn("refused", err)
        self.assertIn("--developer-said", err)
        self.run_tool("feature", "set", "FR-3", "tested=untested")  # a reset needs no flag
        self.run_tool("feature", "set", "FR-7", "tested=passed", "--developer-said")
        self.assertEqual(self.row("FR-7")["tested"], f"passed {TODAY}")
        self.run_tool("feature", "set", "FR-7", "tested=failed - export is empty",
                      "--developer-said")
        self.assertEqual(self.row("FR-7")["tested"], f"failed {TODAY} {DASH} export is empty")
        self.assertIn("tested must be", self.refused("feature", "set", "FR-7", "tested=great",
                                                     "--developer-said"))

    def test_accept_a_phase_ticks_every_row_built_in_it(self):
        self.imported()
        self.run_tool("feature", "set", "FR-3", "tested=untested")
        self.assertIn("--developer-said", self.refused("feature", "set", "P-2", "tested=passed"))
        out = self.run_tool("feature", "set", "P-2", "tested=passed 2026-10-20",
                            "--developer-said").stdout.splitlines()
        self.assertEqual([json.loads(line)["id"] for line in out], ["FR-3", "FR-7"])
        self.assertEqual(self.row("FR-9")["tested"], "untested")
        self.assertIn("takes only tested", self.refused("feature", "set", "P-2", "feature=x"))
        before = self.features.read_bytes()
        out = self.run_tool("feature", "set", "P-4", "tested=passed", "--developer-said").stdout
        self.assertIn("no row to change reads built in P-4; nothing written", out)
        self.assertEqual(self.features.read_bytes(), before)

    def test_accept_names_untested_rows_the_phase_changed_but_did_not_build(self):
        self.imported()
        self.run_tool("feature", "set", "FR-9", "phases=E-1")  # E-1 changed FR-9, built nowhere
        self.run_tool("feature", "set", "FR-3", "phases=P-3")  # built in P-2, changed in P-3
        self.run_tool("feature", "set", "FR-3", "tested=untested")
        out = self.run_tool("feature", "set", "P-3", "tested=passed", "--developer-said").stdout
        self.assertIn("no row to change reads built in P-3", out)
        self.assertIn("note: P-3 also changed these untested rows, built in another phase: FR-3",
                      out)
        self.assertEqual(self.row("FR-3")["tested"], "untested")  # the rule is unchanged
        out = self.run_tool("feature", "set", "P-2", "tested=passed", "--developer-said").stdout
        self.assertNotIn("note:", out)

    def test_accept_never_overwrites_a_failed_row(self):
        self.imported()
        self.run_tool("feature", "set", "FR-7", "tested=failed - export is empty", "--developer-said")
        out = self.run_tool("feature", "set", "P-2", "tested=passed 2026-10-20",
                            "--developer-said").stdout
        self.assertIn("note: left failed, not changed: FR-7", out)
        self.assertEqual(self.row("FR-3")["tested"], "passed 2026-10-20")
        self.assertTrue(self.row("FR-7")["tested"].startswith("failed"))
        self.run_tool("feature", "set", "FR-7", "tested=passed", "--developer-said")  # named
        self.assertEqual(self.row("FR-7")["tested"], f"passed {TODAY}")

    def test_there_is_no_delete(self):
        res = self.run_tool("feature", "delete", "FR-3", ok=False)
        self.assertEqual(res.returncode, 2)  # unknown command: help, nothing removed

    # --- reading ------------------------------------------------------------------------------

    def test_show_and_count(self):
        self.imported()
        shown = [json.loads(l)["id"] for l in self.run_tool("feature", "show", "P-2").stdout.splitlines()]
        self.assertEqual(shown, ["FR-3", "FR-7"])
        shown = [json.loads(l)["id"] for l in self.run_tool("feature", "show", "E-1", "FR-9").stdout.splitlines()]
        self.assertEqual(shown, ["FR-7", "FR-9"])
        self.assertIn("no row", self.refused("feature", "show", "FR-99"))
        count = self.run_tool("feature", "count").stdout
        self.assertIn("rows: 4 (built 2, scheduled 1, unscheduled 1)", count)
        self.assertIn("awaiting testing (built, untested): 1 - P-2: 1 (FR-7)", count)
        self.assertIn("failed: 1 (FR-10)", count)
        self.assertIn("passed: 1", count)
        scoped = self.run_tool("feature", "count", "P-4").stdout
        self.assertIn("scope: rows touched by P-4", scoped)
        self.assertIn("rows: 1 (built 0, scheduled 1", scoped)

    def test_output_is_ascii_and_escapes_round_trip(self):
        self.imported()
        out = self.run_tool("feature", "show", "FR-7").stdout
        self.assertIn("\\u2192", out)
        copied = json.loads(out)["howToCheck"][0]
        self.run_tool("feature", "set", "FR-9", f"howToCheck={copied}")
        self.assertEqual(self.row("FR-9")["howToCheck"], self.row("FR-7")["howToCheck"][:1])

    def test_values_file_in_utf16_with_bom(self):
        self.imported()
        values = self.payload({"feature": f"Audit {DASH} trail"}, encoding="utf-16")
        self.run_tool("feature", "set", "FR-9", values)
        self.assertEqual(self.row("FR-9")["feature"], f"Audit {DASH} trail")
        self.assertIn(f"Audit {DASH} trail", self.view.read_text(encoding="utf-8"))

    # --- check --------------------------------------------------------------------------------

    def test_check_cross_checks_state(self):
        self.imported()
        ledger = self.ledger()
        ledger["features"][2]["build"] = "built in P-3"   # in progress, not done
        ledger["features"][2]["phases"] = ["P-3"]
        ledger["features"][3]["build"] = "scheduled in P-2"  # done
        ledger["features"].append(dict(ledger["features"][0]))  # duplicate id
        ledger["features"][1]["phases"] = ["P-8"]
        self.features.write_text(json.dumps(ledger), encoding="utf-8")
        err = self.refused("feature", "check")
        for problem in ("duplicate id FR-3", "FR-10: scheduled in P-2, which is done",
                        "phases names P-8", "FR-7: built in P-2 but phases does not list P-2"):
            self.assertIn(problem, err)
        # a run that stopped after its ledger update leaves rows built in an in-progress phase
        self.assertNotIn("FR-9", err)

    # --- the generated view -------------------------------------------------------------------

    def test_hand_edited_view_is_never_overwritten_silently(self):
        self.imported()
        self.view.write_text(self.view.read_text(encoding="utf-8").replace("untested", "passed", 1),
                             encoding="utf-8")
        err = self.refused("feature", "set", "FR-9", "feature=Audit trail")
        self.assertIn("changed by hand", err)
        self.assertIn("--force", err)
        self.assertIn("changed by hand", self.refused("feature", "check"))
        self.assertIn("changed by hand", self.refused("feature", "render"))
        self.run_tool("feature", "set", "FR-9", "feature=Audit trail", "--force")
        self.assertEqual(self.run_tool("feature", "check").stdout.strip(), "ok (4 rows)")

    def test_line_endings_are_kept_and_a_crlf_checkout_is_not_a_hand_edit(self):
        self.imported()
        lf = self.view.read_bytes().replace(b"\r\n", b"\n")
        self.view.write_bytes(lf.replace(b"\n", b"\r\n"))  # what git autocrlf does on Windows
        self.run_tool("feature", "set", "FR-9", "feature=Audit trail")
        data = self.view.read_bytes()
        self.assertEqual(data.count(b"\r\n"), data.count(b"\n"))
        self.assertIn("Audit trail".encode(), data)

    def test_stale_view_is_reported_and_rendered(self):
        self.imported()
        ledger = self.ledger()
        ledger["features"][2]["feature"] = "Audit trail"
        self.features.write_text(json.dumps(ledger), encoding="utf-8")
        self.assertIn("out of date", self.refused("feature", "check"))
        self.assertIn("rendered", self.run_tool("feature", "render").stdout)
        self.run_tool("feature", "check")

    def test_view_is_written_as_utf8(self):
        self.imported()
        text = self.view.read_bytes().decode("utf-8")
        self.assertIn(f"`GET /api/employees?q=smith` {ARROW} 200", text)
        self.assertIn(DASH, text)

    # --- plan ---------------------------------------------------------------------------------

    def write_plan(self, text=PLAN, newline="\n"):
        self.plan.write_bytes(text.replace("\n", newline).encode("utf-8"))

    def test_plan_show_prints_one_phase(self):
        self.write_plan()
        out = self.run_tool("plan", "show", "P-2").stdout
        self.assertTrue(out.startswith("## Phase P-2: Employee search"))
        self.assertIn("#### [P-2.T-1] Endpoint", out)
        self.assertIn("\\u2192", out)
        self.assertNotIn("P-3", out)
        self.assertIn("section 2 Completed", self.run_tool("plan", "show", "P-1").stdout)

    def test_plan_complete_moves_a_done_phase(self):
        self.write_plan(newline="\r\n")
        out = self.run_tool("plan", "complete", "P-2", "delivered search \\u2192 results.").stdout
        self.assertEqual(out, "P-2 moved to section 2 Completed; removed: ## Phase P-2: Employee "
                              "search | ### Tasks | #### [P-2.T-1] Endpoint | ### Exit criteria "
                              "(mechanical \\u2014 the agent gate)\n")
        data = self.plan.read_bytes()
        self.assertEqual(data.count(b"\r\n"), data.count(b"\n"))  # CRLF kept
        text = data.decode("utf-8").replace("\r\n", "\n")
        self.assertNotIn("## Phase P-2", text)
        self.assertIn(f"- P-1 {DASH} Walking skeleton {DASH} delivered the scaffold.\n"
                      f"- P-2 {DASH} Employee search {DASH} delivered search {ARROW} results.\n",
                      text)
        self.assertIn("## 5. Phases (remaining)\n\n## Phase P-3: Export", text)
        self.assertEqual(self.run_tool("plan", "check").stdout.splitlines()[0],
                         "ok: section 5 has P-3, P-4; section 2 lists P-1, P-2")

    def test_plan_complete_at_heading_level_three_moves_the_whole_phase(self):
        nested = PLAN.replace("## Phase P-", "### Phase P-").replace("#### [P-2.T-1]", "### [P-2.T-1]")
        self.assertIn("### Tasks", nested)  # same level as the phase heading
        self.write_plan(nested)
        self.run_tool("plan", "check")
        self.run_tool("plan", "complete", "P-2", "search.")
        text = self.plan.read_text(encoding="utf-8")
        for gone in ("### Phase P-2", "[P-2.T-1]", "it answers", "build green"):
            self.assertNotIn(gone, text)
        self.assertIn("## 5. Phases (remaining)\n\n### Phase P-3: Export\n- **Goal:** export.\n\n"
                      "### Phase P-4: Audit", text)

    def test_plan_complete_at_heading_level_two_moves_the_whole_phase(self):
        self.write_plan()
        self.run_tool("plan", "complete", "P-2", "search.")
        text = self.plan.read_text(encoding="utf-8")
        for gone in ("## Phase P-2", "[P-2.T-1]", "it answers", "build green"):
            self.assertNotIn(gone, text)
        self.assertIn("## Phase P-3: Export\n- **Goal:** export.\n\n## Phase P-4: Audit", text)

    def mark_done(self, pid):
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        next(p for p in state["phases"] if p["id"] == pid)["status"] = "done"
        self.state_file.write_text(json.dumps(state), encoding="utf-8")

    def complete_last(self, phase_text):
        """Swap in a last phase (P-4) and complete it; return (output, plan text)."""
        self.write_plan(PLAN.replace("## Phase P-4: Audit\n- **Goal:** audit.\n", phase_text))
        self.mark_done("P-4")
        out = self.run_tool("plan", "complete", "P-4", "audit.").stdout
        return out, self.plan.read_text(encoding="utf-8")

    def test_plan_complete_on_the_last_phase_keeps_trailing_material(self):
        out, text = self.complete_last(
            "## Phase P-4: Audit\n- **Goal:** audit.\n\n### Tasks\n- t\n\n### Exit criteria\n"
            "- [ ] green\n\n### Sequencing notes\nkeep me 1\n")
        self.assertIn("removed: ## Phase P-4: Audit | ### Tasks | ### Exit criteria\n", out)
        self.assertNotIn("**Goal:** audit.", text)
        self.assertIn("### Sequencing notes\nkeep me 1", text)
        out, text = self.complete_last("## Phase P-4: Audit\n- **Goal:** audit.\n\n## Notes\nkeep me 2\n")
        self.assertNotIn("**Goal:** audit.", text)
        self.assertIn("## Notes\nkeep me 2", text)

    def test_last_phase_with_a_yaml_block_holding_a_rule_moves_whole(self):
        out, text = self.complete_last(
            "## Phase P-4: Audit\n- **Goal:** audit.\n\n### Developer test guide\n```yaml\n---\n"
            "key: value\n## yaml comment, not a heading\n```\nafter the block\n\n### Exit criteria\n- [ ] green\n")
        for gone in ("key: value", "after the block", "- [ ] green", "yaml comment"):
            self.assertNotIn(gone, text)
        self.assertIn("## 6. Risks", text)
        self.assertEqual(self.run_tool("plan", "check").stdout.split(";")[0], "ok: section 5 has P-2, P-3")

    def test_last_phase_with_a_rule_in_its_test_guide_moves_whole(self):
        out, text = self.complete_last(
            "## Phase P-4: Audit\n- **Goal:** audit.\n\n### Developer test guide\n1. start\n\n---\n\n"
            "2. open the screen\n\n### Exit criteria\n- [ ] green\n")
        for gone in ("2. open the screen", "- [ ] green", "### Exit criteria\n- [ ] green"):
            self.assertNotIn(gone, text)

    def test_a_template_heading_left_behind_is_refused(self):
        self.write_plan(PLAN.replace("## Phase P-4: Audit\n- **Goal:** audit.\n",
                                     "## Phase P-4: Audit\n### Tasks\n- t\n\n## Notes\nn\n\n"
                                     "### Exit criteria\n- [ ] green\n"))
        self.mark_done("P-4")
        err = self.refused("plan", "complete", "P-4", "audit.")
        self.assertIn("cannot delimit safely; nothing written", err)
        self.assertIn("'### Exit criteria' would be left behind", err)

    def test_a_same_level_note_inside_a_phase_is_ambiguous_and_refused(self):
        nested = PLAN.replace("## Phase P-", "### Phase P-").replace(
            "### Phase P-3: Export", "### Notes on P-2\nkeep or move?\n\n### Phase P-3: Export")
        self.write_plan(nested)
        err = self.refused("plan", "check")
        self.assertIn("'### Notes on P-2' inside P-2 is not part of the phase template", err)
        self.assertIn("cannot be parsed safely", self.refused("plan", "complete", "P-2", "x"))

    def test_a_note_one_level_down_stays_with_its_phase(self):
        self.write_plan(PLAN.replace("## Phase P-3: Export", "### Notes on P-2\nnote\n\n## Phase P-3: Export"))
        self.run_tool("plan", "complete", "P-2", "search.")
        text = self.plan.read_text(encoding="utf-8")
        self.assertNotIn("Notes on P-2", text)
        self.assertIn("## 5. Phases (remaining)\n\n## Phase P-3: Export", text)

    def test_an_unclosed_code_fence_is_reported(self):
        self.write_plan(PLAN.replace("## Phase P-3: Export\n", "## Phase P-3: Export\n```bash\nrun\n"))
        self.assertIn("a code fence is never closed", self.refused("plan", "check"))
        self.assertIn("cannot be parsed safely", self.refused("plan", "complete", "P-2", "x"))

    def test_plan_structure_it_cannot_delimit_is_reported_and_refused(self):
        mixed = PLAN.replace("## Phase P-3", "### Phase P-3")
        self.write_plan(mixed)
        self.assertIn("mix levels", self.refused("plan", "check"))
        self.assertIn("cannot be parsed safely", self.refused("plan", "complete", "P-2", "x"))
        above = PLAN.replace("## Phase P-", "### Phase P-").replace(
            "### Phase P-3: Export", "## Notes on export\n\n### Phase P-3: Export")
        self.write_plan(above)
        self.assertIn("where P-2 ends is unclear", self.refused("plan", "check"))
        self.assertIn("cannot be parsed safely", self.refused("plan", "complete", "P-2", "x"))

    def test_plan_complete_refusals(self):
        self.write_plan()
        self.assertIn("in progress", self.refused("plan", "complete", "P-3", "x"))
        self.assertIn("already in section 2", self.refused("plan", "complete", "P-1", "x"))
        self.assertIn("pairs", self.refused("plan", "complete", "P-2"))
        self.assertIn("P-9 is not in state.json", self.refused("plan", "complete", "P-9", "x"))

    def test_plan_complete_into_an_empty_section_2(self):
        self.write_plan(PLAN.replace(f"- P-1 {DASH} Walking skeleton {DASH} delivered the scaffold.",
                                     "*None yet.*\n\n---"))
        self.run_tool("plan", "complete", "P-2", "search.")
        text = self.plan.read_text(encoding="utf-8")
        self.assertIn(f"## 2. Completed\n\n- P-2 {DASH} Employee search {DASH} search.\n\n---\n\n"
                      "## 3.", text)
        self.assertNotIn("None yet", text)

    def test_plan_complete_drops_a_placeholder_list_item(self):
        self.write_plan(PLAN.replace(f"- P-1 {DASH} Walking skeleton {DASH} delivered the scaffold.",
                                     "- None yet."))
        self.run_tool("plan", "complete", "P-2", "search.")
        text = self.plan.read_text(encoding="utf-8")
        self.assertIn(f"## 2. Completed\n\n- P-2 {DASH} Employee search {DASH} search.\n\n## 3.", text)
        self.assertNotIn("None yet", text)

    def test_plan_replace_is_exact_and_all_or_nothing(self):
        self.write_plan()
        good = {"old": f"search {ARROW} results.", "new": "search by name."}
        twice = {"old": "- none", "new": "- nothing"}
        self.assertIn("pair 2: old text found 2 times",
                      self.refused("plan", "replace", self.payload([good, twice])))
        missing = {"old": "not there", "new": "x"}
        self.assertIn("found 0 times", self.refused("plan", "replace", self.payload([missing])))
        self.run_tool("plan", "replace", self.payload([good, ["- **Goal:** export.",
                                                             "- **Goal:** export \\u2014 CSV."]]))
        text = self.plan.read_text(encoding="utf-8")
        self.assertIn("search by name.", text)
        self.assertIn(f"export {DASH} CSV.", text)

    def test_plan_check_reports_what_it_cannot_parse(self):
        self.write_plan(PLAN.replace("## Phase P-3: Export", "## Export phase (P-3)")
                        .replace("## 2. Completed", "## Completed"))
        err = self.refused("plan", "check")
        self.assertIn("expected one '## 2.' heading, found 0", err)
        self.assertIn("P-3 is in progress in state.json but has no subsection", err)
        self.assertIn("note: P-2 is done and still in section 5", err)

    def test_plan_found_by_project_name_or_flag(self):
        self.write_plan()
        other = self.out / "elsewhere.md"
        other.write_text(PLAN.replace("Employee search", "Staff search"), encoding="utf-8")
        self.assertIn("Staff search",
                      self.run_tool("--plan", str(other), "plan", "show", "P-2").stdout)
        self.plan.unlink()
        (self.out / "PLAN_A.md").write_text(PLAN, encoding="utf-8")
        (self.out / "PLAN_B.md").write_text(PLAN, encoding="utf-8")
        self.assertIn("pass --plan", self.refused("plan", "show", "P-2"))

    def test_non_utf8_plan_is_refused_with_a_hint(self):
        self.plan.write_bytes(PLAN.replace(DASH, "-").replace(ARROW, "->").encode("utf-8")
                              + "café".encode("cp1252"))
        self.assertIn("not UTF-8", self.refused("plan", "check"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
