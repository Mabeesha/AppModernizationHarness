#!/usr/bin/env python3
"""Tests for ModernizationHarness/tools/clientdocs.py, the client hand-over pack tool.

Each test runs the real script as a subprocess — the way an agent calls it — against five small
source documents in a temporary directory, then reads the files back.

Run:  uv run tests/test_clientdocs_tool.py      (or: python tests/test_clientdocs_tool.py)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "ModernizationHarness" / "tools" / "clientdocs.py"
SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "employee-search" / "reference-output"
TODAY = date.today().isoformat()

SOURCES = {
    "BUSINESS_REQUIREMENTS_Demo.md": """# Business Requirements — Demo

## 0. Revision History
| Date | Change |
|---|---|
| 2026-01-01 | Stage 1 first run |

## 1. Goals
BR-1 Users search employees. See [the rules](FUNCTIONAL_REQUIREMENTS_Demo.md#2-rules) and
[DatabaseHelper.cs:48](../legacy/Db/DatabaseHelper.cs#L48) and [here](../legacy/Db/Seed.cs#L3-L9).

> `ASSUMPTION:` Seed data is sample data,
> not production.

### 1.1 Users
Staff only (ROLE-1).

## 2. Open Questions & Assumptions
- `OPEN QUESTION:` Should salary be hidden?
  It is visible to all; the screen is marked TODO for review.
- Next item.
""",
    "FUNCTIONAL_REQUIREMENTS_Demo.md": """# Functional Requirements — Demo

## 2. Rules
| ID | Rule |
|---|---|
| VR-1 | Name max 50. `ASSUMPTION:` trimmed |

```text
`OPEN QUESTION:` an example in a code block is not a marker
```
""",
    "TECHNICAL_REQUIREMENTS_Demo.md": """# Technical Requirements — Demo

## 1. Stack
SEC-1 BCrypt. TODO (AD) per PROJECT_CONTEXT §4, see intake question 11.
""",
    "HIGH_LEVEL_DESIGN_Demo.md": """# High-Level Design — Demo

## 0. Revision History
| Date | Change |
|---|---|
| 2026-02-01 | Stage 2 rerun after changeLog 4 |

## 3. Decisions
DD-1 Spring Boot, built in P-2.

```java
// TODO sample: OPEN QUESTION: is quoted, not a marker
```
""",
    "LOW_LEVEL_DESIGN_Demo.md": """# Low-Level Design — Demo

## 1. API
`GET /api/employees` (FR-3).

## 3c. Reference Adoption
REF-1 taken from the sample.

### 3c.1 Detail
More sample.

## 4. Validation
VR-1 enforced.

## 7. Configuration Keys
| Key | Shape | Default | Secret? | Set at | Differs per environment |
|---|---|---|---|---|---|
| `api.baseUrl` | URL | `http://localhost:8080` | no | build | yes |
| `db.password` | text | — | yes | run | yes |
""",
}
RUN_SOURCE = """# Running Demo

## Build & run
```powershell
cd D:\\tools\\demo
D:\\Program Files\\maven\\bin\\mvn.cmd spring-boot:run
```

## How to test by hand
Walk the rows in FEATURE_STATUS.md built in P-2.
"""
OTHERS = {
    "HOW_TO_RUN.md": RUN_SOURCE,
    "INTAKE_RESOLVED.md": (
        "# Intake Resolved\n\n| Q | Answer | Provenance |\n|---|---|---|\n"
        "| 5b | Java 21 | `ASSUMPTION: (default applied)` |\n"
        "| 7 | PostgreSQL 16 | `ASSUMPTION: (default applied)` |\n"),
    "REVIEW_R-1_Demo_whole-build.md": "# Review\n\nNo leftover TODO markers in tests.\n",
    "PROJECT_CONTEXT.md": "# Project Context\n\n## 7. Open Questions\n- `OPEN QUESTION:` Which AD group?\n",
    "BUILD_ASSUMPTIONS_Demo.md": (
        "# Build Assumptions & Open Questions — Demo\n\n| # | Run | Date | Item | Why | Where |\n"
        "|---|---|---|---|---|---|\n| BA-1 | P-3 | 2026-03-01 | `ASSUMPTION:` Name search matches "
        "anywhere | LLD silent | `Repo.java:42` |\n"),
}
COPIES = ["Demo_BRD.md", "Demo_FRD.md", "Demo_TRD.md", "Demo_HLD.md", "Demo_LLD.md",
          "Demo_RUN_LOCALLY.md", "Demo_DEPLOYMENT_GUIDE.md"]


class ClientDocsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.out = self.dir / "out"
        self.out.mkdir()
        for name, text in {**SOURCES, **OTHERS}.items():
            (self.out / name).write_text(text, encoding="utf-8")
        (self.out / "state.json").write_text(json.dumps(
            {"project": "Demo", "context": {"locations": {"documents": "out"}}}), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, *args, ok=True):
        p = subprocess.run([sys.executable, str(TOOL), *args], cwd=self.dir, capture_output=True,
                           text=True, encoding="ascii", errors="replace")
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        else:
            self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    def notes(self):
        return (self.out / "CLIENT_PACK_NOTES.md").read_text(encoding="utf-8")

    def hits(self):
        """{hit id: text} from section 3."""
        section = self.notes().split("## 3. Raw markers")[1].split("## 4.")[0]
        return {m.group(1): m.group(2) for m in
                re.finditer(r"^\| (H-[0-9a-f]{6}) \|[^|]*\|[^|]*\|[^|]*\| (.*) \|$", section, re.M)}

    def copy_text(self, name):
        return (self.out / "artifacts" / name).read_text(encoding="utf-8")

    def write_values(self, name, pairs):
        tmp = self.dir / ".harness-tmp"
        tmp.mkdir(exist_ok=True)
        (tmp / name).write_text(json.dumps(pairs), encoding="utf-8")
        return f"@.harness-tmp/{name}"

    def add_rows(self, section, rows):
        text = self.notes()
        head, rest = text.split(f"## {section}.", 1)
        body, tail = (rest.split("\n## ", 1) + [""])[:2]
        body = body.rstrip("\n") + "\n" + "\n".join(rows) + "\n\n"
        (self.out / "CLIENT_PACK_NOTES.md").write_text(
            head + f"## {section}." + body + ("## " + tail if tail else ""), encoding="utf-8")

    # --- scan --------------------------------------------------------------------------------

    def test_scan_finds_markers_in_prose_quotes_tables_and_other_sources(self):
        out = self.run_tool("scan").stdout
        self.assertIn("raw markers", out)
        texts = list(self.hits().values())
        self.assertIn("ASSUMPTION: Seed data is sample data, not production.", texts)
        self.assertIn("ASSUMPTION: trimmed [row: VR-1 \\| Name max 50.]", texts)
        self.assertTrue(any(t.startswith("TODO (AD)") for t in texts), texts)
        self.assertIn("OPEN QUESTION: Which AD group?", texts)
        self.assertTrue(any("Name search matches anywhere" in t for t in texts), texts)
        self.assertFalse(any("code block" in t or "quoted" in t for t in texts),
                         "a marker in a code block counted")
        self.assertFalse(any("leftover" in t for t in texts), "a review's word TODO counted")
        # a question with a TODO on its next line keeps all of its text; the TODO is its own hit
        self.assertIn("OPEN QUESTION: Should salary be hidden? It is visible to all; the screen is "
                      "marked TODO for review.", texts)
        self.assertTrue(any(t.startswith("TODO for review") for t in texts), texts)

    def test_each_table_row_is_its_own_marker(self):
        self.run_tool("scan")
        texts = [t for t in self.hits().values() if "default applied" in t]
        self.assertEqual(len(texts), 2, texts)
        self.assertIn("ASSUMPTION: (default applied) [row: 5b \\| Java 21]", texts)
        self.assertFalse(any(t.count("`") % 2 for t in texts), texts)

    def test_scan_lists_reference_hits_but_not_links_between_the_five(self):
        self.run_tool("scan")
        section = self.notes().split("## 4.")[1].split("## 5.")[0]
        for found in ("PROJECT_CONTEXT", "intake question", "P-2", "Stage 2", "changeLog",
                      "../legacy/Db/DatabaseHelper.cs#L48"):
            self.assertIn(found, section)
        self.assertNotIn("| FUNCTIONAL_REQUIREMENTS_Demo.md#2-rules |", section)

    def test_hit_ids_survive_lines_moving_and_a_rerun_keeps_what_was_written(self):
        self.run_tool("scan")
        before = self.hits()
        self.add_rows("5", ["| I-1 | " + ", ".join(before) + " | new | Still open |  | Ask. |"])
        self.add_rows("6", ["| Demo_BRD.md | legal obligation | client text |"])
        self.add_rows("8", ["### Version 1.0 — Round 1 — FINDINGS", "1. **minor** — x"])
        brd = self.out / "BUSINESS_REQUIREMENTS_Demo.md"
        brd.write_text("\n\n\n" + brd.read_text(encoding="utf-8"), encoding="utf-8")
        out = self.run_tool("scan").stdout
        self.assertEqual(self.hits(), before)
        notes = self.notes()
        for kept in ("| I-1 |", "legal obligation", "Round 1 — FINDINGS"):
            self.assertIn(kept, notes)
        self.assertIn("0 markers in no item", out)

    def test_scan_names_an_item_whose_hit_is_gone(self):
        self.run_tool("scan")
        self.add_rows("5", ["| I-1 | H-000000 | new | Still open |  | Ask. |"])
        self.assertIn("H-000000", self.run_tool("scan").stdout)

    def test_scan_needs_all_five_documents(self):
        (self.out / "LOW_LEVEL_DESIGN_Demo.md").unlink()
        self.assertIn("LOW_LEVEL_DESIGN_Demo.md", self.run_tool("scan", ok=False).stderr)

    def test_scan_reads_the_sample_project(self):
        out = self.dir / "sample"
        out.mkdir()
        for f in SAMPLE.glob("*.md"):
            (out / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        for key, name in (("HIGH", "HIGH_LEVEL_DESIGN"), ("LOW", "LOW_LEVEL_DESIGN")):
            (out / f"{name}_EmployeeSearch.md").write_text(f"# {key}\n", encoding="utf-8")
        self.run_tool("--docs", "sample", "--app", "EmployeeSearch", "scan")
        notes = (out / "CLIENT_PACK_NOTES.md").read_text(encoding="utf-8")
        self.assertGreater(notes.count("| H-"), 20)

    # --- copy --------------------------------------------------------------------------------

    def test_copy_rewrites_links_history_and_front_matter_and_drops_3c(self):
        self.run_tool("scan")
        self.run_tool("copy")
        brd = self.copy_text("Demo_BRD.md")
        self.assertTrue(brd.startswith("---\ntitle: Business Requirements — Demo\nversion: 1.0\n"
                                       f"date: {TODAY}\nstatus: Draft\n"), brd[:200])
        self.assertIn("[the rules](Demo_FRD.md#2-rules)", brd)
        self.assertIn("and\nDatabaseHelper.cs:48 and", brd)
        self.assertIn("here (legacy/Db/Seed.cs:3-9)", brd)
        self.assertNotIn("../legacy", brd)
        self.assertIn("## 0. Document Control", brd)
        self.assertIn(f"| 1.0 | {TODAY} | Draft | First issue |", brd)
        self.assertNotIn("Revision History", brd)
        lld = self.copy_text("Demo_LLD.md")
        self.assertNotIn("Reference Adoption", lld)
        self.assertNotIn("3c.1", lld)
        self.assertIn("## 4. Validation", lld)
        self.assertIn("## 0. Document Control", lld)  # no history to replace: added under the title
        self.assertEqual((self.out / "BUSINESS_REQUIREMENTS_Demo.md").read_text(encoding="utf-8"),
                         SOURCES["BUSINESS_REQUIREMENTS_Demo.md"], "a source changed")

    def test_copy_refuses_to_overwrite_and_a_new_version_counts_up(self):
        self.run_tool("scan")
        self.run_tool("copy")
        self.assertIn("refused", self.run_tool("copy", ok=False).stderr)
        self.clean_pack(scanned=True)
        self.run_tool("set", "status=Final")
        self.run_tool("copy", "--new-version")
        brd = self.copy_text("Demo_BRD.md")
        self.assertIn("version: 2.0", brd)
        self.assertIn("status: Draft", brd)
        self.assertIn(f"| 1.0 | {TODAY} | Final | First issue |", brd)
        self.assertIn(f"| 2.0 | {TODAY} | Draft | New version |", brd)

    def test_copy_needs_a_scan_first(self):
        self.assertIn("scan", self.run_tool("copy", ok=False).stderr)

    # --- replace and set ---------------------------------------------------------------------

    def test_replace_applies_all_or_none_and_deletes_its_values_file(self):
        self.run_tool("scan")
        self.run_tool("copy")
        good = self.write_values("brd.json", [{"old": "BR-1 Users", "new": "BR-1 Staff"}])
        self.run_tool("replace", "BRD", good)
        self.assertIn("BR-1 Staff", self.copy_text("Demo_BRD.md"))
        self.assertFalse((self.dir / ".harness-tmp" / "brd.json").exists())
        bad = self.write_values("brd2.json", [["BR-1 Staff", "BR-1 People"], ["nowhere", "x"]])
        self.assertIn("found 0 times", self.run_tool("replace", "BRD", bad, ok=False).stderr)
        self.assertIn("BR-1 Staff", self.copy_text("Demo_BRD.md"))

    def test_replace_edits_only_a_client_copy(self):
        self.run_tool("scan")
        self.run_tool("copy")
        values = self.write_values("x.json", [{"old": "BR-1", "new": "BR-9"}])
        err = self.run_tool("replace", "BUSINESS_REQUIREMENTS_Demo.md", values, ok=False).stderr
        self.assertIn("refused", err)
        self.assertIn("BR-1", (self.out / "BUSINESS_REQUIREMENTS_Demo.md").read_text(encoding="utf-8"))

    def test_set_changes_notes_front_matter_and_document_control(self):
        self.clean_pack()
        self.run_tool("set", "status=final", "prepared-for=Acme Ltd", "prepared-by=Platform Team")
        hld = self.copy_text("Demo_HLD.md")
        self.assertIn("status: Final\n", hld)
        self.assertIn("prepared-for: Acme Ltd\n", hld)
        self.assertIn(f"| 1.0 | {TODAY} | Final | First issue |", hld)
        self.assertIn("| prepared-by | Platform Team |", self.notes())
        self.assertIn("Draft or Final", self.run_tool("set", "status=Done", ok=False).stderr)

    # --- check -------------------------------------------------------------------------------

    def clean_pack(self, scanned=False):
        """Scan, copy, settle every hit, and edit the copies until nothing harness-like is left."""
        if not scanned:
            self.run_tool("scan")
            self.run_tool("copy")
        self.run_tool("set", "prepared-for=Acme Ltd", "prepared-by=Platform Team")
        rows = [f"| I-{n} | {h} | new | Decided | changeLog 4 | Wording {n}. |"
                for n, h in enumerate(self.hits(), 1)]
        self.add_rows("5", rows)
        fixes = {
            "Demo_BRD.md": [
                ["> `ASSUMPTION:` Seed data is sample data,\n> not production.",
                 "> Seed data is sample data, not production."],
                ["- `OPEN QUESTION:` Should salary be hidden?\n  It is visible to all; the "
                 "screen is marked TODO for review.",
                 "- Salary is hidden from staff without the HR role."]],
            "Demo_FRD.md": [["Name max 50. `ASSUMPTION:` trimmed", "Name max 50, trimmed."],
                            ["`OPEN QUESTION:` an example in a code block is not a marker",
                             "an example"]],
            "Demo_TRD.md": [["SEC-1 BCrypt. TODO (AD) per PROJECT_CONTEXT §4, see intake question 11.",
                             "SEC-1 BCrypt; sign-in uses Active Directory (constraint C2)."]],
            "Demo_HLD.md": [["DD-1 Spring Boot, built in P-2.", "DD-1 Spring Boot."],
                            ["// TODO sample: OPEN QUESTION: is quoted, not a marker",
                             "// TODO sample"]],
        }
        for name, pairs in fixes.items():
            key = name[5:8]
            self.run_tool("replace", key, self.write_values(f"{key}.json", pairs))
        self.run_tool("replace", "RUN", self.write_values("run.json", [
            ["D:\\Program Files\\maven\\bin\\mvn.cmd", "<your Maven folder>\\bin\\mvn.cmd"],
            ["Walk the rows in FEATURE_STATUS.md built in P-2.",
             "Open the app and search for a name."]]))
        if not (self.out / "artifacts" / "Demo_DEPLOYMENT_GUIDE.md").exists():
            self.run_tool("skeleton")
        self.fill_guide()

    def fill_guide(self):
        """Write something in every place the skeleton left to be written."""
        pairs = []
        for line in self.copy_text("Demo_DEPLOYMENT_GUIDE.md").split("\n"):
            if "*To be written" in line:
                new = (re.sub(r"\*To be written\*", "set by ops", line) if line.startswith("|")
                       else "Written for the deployer.")
                pairs.append([line, new])
        self.run_tool("replace", "DEPLOY", self.write_values("g.json", pairs))

    def test_check_passes_a_clean_pack(self):
        self.clean_pack()
        out = self.run_tool("check").stdout
        self.assertIn("ok: 7 documents, version 1.0 (Draft)", out)

    def test_check_finds_what_a_fresh_copy_still_carries(self):
        self.run_tool("scan")
        self.run_tool("copy")
        err = self.run_tool("check", ok=False).stderr
        for expected in ("Demo_BRD.md:1: front matter has no prepared-for",
                         "raw marker '`OPEN QUESTION:`'", "raw marker 'TODO'",
                         "harness file 'PROJECT_CONTEXT'", "harness word 'intake question'",
                         "harness ID 'P-2'", "is settled by no item"):
            self.assertIn(expected, err)

    def test_check_finds_lost_content_and_an_exemption_excuses_it(self):
        self.clean_pack()
        values = self.write_values("lld.json", [["VR-1 enforced.", "Enforced."]])
        self.run_tool("replace", "LLD", values)
        err = self.run_tool("check", ok=False).stderr
        self.assertIn("VR-1 is missing from Demo_LLD.md", err)
        self.assertNotIn("REF-1", err)  # only in the dropped section 3c
        self.add_rows("6", ["| Demo_LLD.md | VR-1 | moved to the FRD on purpose |"])
        self.run_tool("check")

    def test_check_finds_a_lost_numbered_section(self):
        self.clean_pack()
        self.run_tool("replace", "HLD", self.write_values("h.json", [["## 3. Decisions", "Decisions"]]))
        self.assertIn("section 3 of HIGH_LEVEL_DESIGN_Demo.md is missing",
                      self.run_tool("check", ok=False).stderr)

    def test_check_finds_a_lost_sub_section(self):
        self.clean_pack()
        self.run_tool("replace", "BRD", self.write_values("b.json", [
            ["### 1.1 Users\nStaff only (ROLE-1).\n", ""]]))
        err = self.run_tool("check", ok=False).stderr
        self.assertIn("section 1.1 of BUSINESS_REQUIREMENTS_Demo.md is missing", err)
        self.assertIn("ROLE-1 is missing from Demo_BRD.md", err)

    def test_a_marker_in_a_code_block_is_not_a_problem(self):
        self.clean_pack()
        self.assertIn("// TODO sample", self.copy_text("Demo_HLD.md"))
        self.run_tool("check")

    def test_final_needs_a_clean_pack(self):
        self.run_tool("scan")
        self.run_tool("copy")
        err = self.run_tool("set", "status=Final", "prepared-for=A", "prepared-by=B", ok=False).stderr
        self.assertIn("cannot be Final", err)
        self.assertIn("status: Draft", self.copy_text("Demo_BRD.md"))
        # already Final, then changed: setting Final again checks again
        self.clean_pack(scanned=True)
        self.run_tool("set", "status=Final")
        self.run_tool("replace", "BRD", self.write_values("t.json", [["BR-1 Users", "BR-1 Users `TODO`"]]))
        self.assertIn("cannot be Final", self.run_tool("set", "status=Final", ok=False).stderr)

    def test_a_todo_runs_on_to_the_end_of_its_paragraph(self):
        self.run_tool("scan")
        self.assertIn("TODO for review.", self.hits().values())
        trd = self.out / "TECHNICAL_REQUIREMENTS_Demo.md"
        trd.write_text("# T\n\n## 1. Stack\nSEC-1 uses TODO (AD) until\nthe directory is chosen.\n",
                       encoding="utf-8")
        self.run_tool("scan")
        self.assertIn("TODO (AD) until the directory is chosen.", self.hits().values())

    # --- the run document and the deployment guide ---------------------------------------

    def test_copy_makes_the_run_document(self):
        self.run_tool("scan")
        out = self.run_tool("copy").stdout
        self.assertIn("made  Demo_RUN_LOCALLY.md  <- HOW_TO_RUN.md", out)
        self.assertIn("next: `skeleton`", out)
        run = self.copy_text("Demo_RUN_LOCALLY.md")
        self.assertIn("title: Running Locally \u2014 Demo", run)
        self.assertIn("## 0. Document Control", run)
        err = self.run_tool("check", ok=False).stderr
        self.assertIn("Demo_RUN_LOCALLY.md:", err)
        self.assertIn("harness file 'FEATURE_STATUS'", err)

    def test_skeleton_fills_configuration_and_secrets_from_lld_7_and_never_overwrites(self):
        self.run_tool("scan")
        self.run_tool("copy")
        self.assertIn("2 keys from the LLD section 7 table", self.run_tool("skeleton").stdout)
        guide = self.copy_text("Demo_DEPLOYMENT_GUIDE.md")
        for heading in ("## 0. Document Control", "## 4. Configuration", "## 5. Secrets",
                        "## 12. Open Items"):
            self.assertIn(heading, guide)
        config = guide.split("## 4.")[1].split("## 5.")[0]
        secrets = guide.split("## 5.")[1].split("## 6.")[0]
        self.assertIn("| `api.baseUrl` |", config)
        self.assertIn("`http://localhost:8080`", config)
        self.assertNotIn("db.password", config)
        self.assertIn("| `db.password` |", secrets)
        self.assertNotIn("(14a)", guide)
        self.assertIn("refused", self.run_tool("skeleton", ok=False).stderr)

    def test_skeleton_falls_back_to_back_ticked_names_but_check_does_not(self):
        lld = self.out / "LOW_LEVEL_DESIGN_Demo.md"
        text = lld.read_text(encoding="utf-8").split("## 7.")[0]
        lld.write_text(text + "## 7. Configuration Keys\n- `api.baseUrl` in `application.yml`\n",
                       encoding="utf-8")
        self.run_tool("scan")
        self.run_tool("copy")
        self.assertIn("prune them", self.run_tool("skeleton").stdout)
        self.assertIn("`application.yml`", self.copy_text("Demo_DEPLOYMENT_GUIDE.md"))
        self.assertIn("keys not checked", self.run_tool("check", ok=False).stderr)

    def test_check_keeps_the_guide_and_lld_7_in_step(self):
        self.clean_pack()
        self.run_tool("check")
        guide = self.copy_text("Demo_DEPLOYMENT_GUIDE.md")
        row = next(l for l in guide.split("\n") if l.startswith("| `api.baseUrl`"))
        self.run_tool("replace", "DEPLOY", self.write_values("a.json", [
            [row, row.replace("`api.baseUrl`", "`server.port`")]]))
        err = self.run_tool("check", ok=False).stderr
        self.assertIn("LLD section 7 key 'api.baseUrl' is not in section 4 or 5", err)
        self.assertIn("key 'server.port' is not in the LLD section 7 table", err)
        # put the LLD key back, and mark the framework setting as one
        port = row.replace("`api.baseUrl`", "`server.port`")
        cells = port.split(" | ")
        cells[2] = "framework"  # the Required? column
        self.run_tool("replace", "DEPLOY", self.write_values("b.json", [
            [port, row + "\n" + " | ".join(cells)]]))
        self.run_tool("check")

    def test_check_finds_what_the_guide_still_lacks(self):
        self.run_tool("scan")
        self.run_tool("copy")
        self.run_tool("skeleton")
        self.run_tool("replace", "DEPLOY", self.write_values("v.json", [
            ["| Name | What it is for |", "| Name | Value | What it is for |"]]))
        err = self.run_tool("check", ok=False).stderr
        self.assertIn("Demo_DEPLOYMENT_GUIDE.md:", err)
        self.assertIn("still to be written", err)
        self.assertIn("section 5 (Secrets) has a value column", err)

    def test_check_finds_secret_values_and_lets_names_and_placeholders_pass(self):
        self.clean_pack()
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.sig"
        self.run_tool("replace", "RUN", self.write_values("s.json", [[
            "Open the app and search for a name.",
            "Open the app and search for a name.\n\npassword: admin123\n\n"
            "db.password=<db-password> and DB_PASSWORD=${DB_PASSWORD} and token: see section 5\n\n"
            f"Authorization: Bearer {jwt}\n\n"
            "| id | value |\n|---|---|\n| tenant | 1b4e28ba-2fa1-11d2-883f-0016d3cca427 |\n"
            "| file | src/app/orders/OrderService2OrderService2Order |\n"
            "| key | aB3dE5gH7jK9mN1pQ3sT5vX7zA9cE1gI3 |"]]))
        err = self.run_tool("check", ok=False).stderr
        self.assertIn("'password: admin123' looks like a secret value", err)
        self.assertIn("a JWT", err)
        self.assertIn("aB3dE5gH7jK9... looks like a secret value", err)
        for passes in ("db-password", "DB_PASSWORD", "token: see", "1b4e28ba", "OrderService2"):
            self.assertNotIn(passes, err)
        self.add_rows("6", ["| Demo_RUN_LOCALLY.md | password: admin123 | local seed account, in the code |"])
        self.assertNotIn("admin123", self.run_tool("check", ok=False).stderr)

    def test_the_secret_check_tells_a_secret_from_talk_about_one(self):
        self.clean_pack()
        text = ("Open the app and search for a name.\n\nThe access token: 60 minutes.\n\n"
                "```yaml\ntoken-uri: https://login.example.com/oauth2/token\n"
                "tokenEndpoint: 'https://login.example.com/token'\n"
                "secretName: EmployeeSearch-Ldap-Bind\n"
                "bind-password: secret\nsigning-key: changeit\n```\n\n"
                "`Server=db;User Id=sa;Password=sa;`\n\n"
                "| key | note |\n|---|---|\n| SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_ISSUER_URI | set |")
        self.run_tool("replace", "RUN", self.write_values("s.json", [
            ["Open the app and search for a name.", text]]))
        err = self.run_tool("check", ok=False).stderr
        for caught in ("'bind-password: secret'", "'signing-key: changeit'", "'Password=sa'"):
            self.assertIn(caught, err)
        for passes in ("60 minutes", "token-uri", "tokenEndpoint", "secretName", "SPRING_SECURITY"):
            self.assertNotIn(passes, err)

    def test_list_items_and_expressions_are_not_secret_values(self):
        self.clean_pack()
        text = ("Open the app and search for a name.\n\n- password: hashed with bcrypt before storage\n"
                "- Token: issued at sign-in\n- passwordHash: bcrypt hash of the password\n\n"
                "```powershell\n$token = (Invoke-RestMethod -Uri $url -Method Post).token\n```\n\n"
                "```ts\ntokenStorageKey: auth_token,\n```")
        self.run_tool("replace", "RUN", self.write_values("l.json", [
            ["Open the app and search for a name.", text]]))
        self.run_tool("check")

    def test_secret_keys_never_land_in_the_configuration_table(self):
        lld = self.out / "LOW_LEVEL_DESIGN_Demo.md"
        lld.write_text(lld.read_text(encoding="utf-8").replace(
            "| `db.password` | text | — | yes | run | yes |",
            "| `db.password` | text | — | **Yes** | run | yes |\n"
            "| `jwt.signing-key` | text | — | \u2713 | run | yes |\n"
            "| `cache.size` | number | 100 | maybe | run | no |"), encoding="utf-8")
        self.run_tool("scan")
        self.run_tool("copy")
        out = self.run_tool("skeleton").stdout
        self.assertIn("neither yes nor no for cache.size", out)
        guide = self.copy_text("Demo_DEPLOYMENT_GUIDE.md")
        secrets = guide.split("## 5.")[1].split("## 6.")[0]
        self.assertIn("`db.password`", secrets)
        self.assertIn("`jwt.signing-key`", secrets)
        self.clean_pack(scanned=True)
        row = next(l for l in self.copy_text("Demo_DEPLOYMENT_GUIDE.md").split("\n")
                   if l.startswith("| `api.baseUrl`"))
        self.run_tool("replace", "DEPLOY", self.write_values("m.json", [
            [row, row + "\n" + row.replace("`api.baseUrl`", "`db.password`")]]))
        self.assertIn("'db.password' is secret in LLD section 7 - it belongs in section 5",
                      self.run_tool("check", ok=False).stderr)

    def test_lld_7_is_read_from_its_key_table_and_framework_keys_count(self):
        lld = self.out / "LOW_LEVEL_DESIGN_Demo.md"
        lld.write_text(lld.read_text(encoding="utf-8").replace(
            "## 7. Configuration Keys\n",
            "## 7. Configuration Keys\n| File | Purpose |\n|---|---|\n| `application.yml` | backend |\n\n"
        ).replace("| `db.password` | text | — | yes | run | yes |",
                  "| `db.password` | text | — | yes | run | yes |\n| `server.port` | number | 8080 | no | run | no |"),
            encoding="utf-8")
        self.run_tool("scan")
        self.run_tool("copy")
        self.assertIn("3 keys from the LLD section 7 table", self.run_tool("skeleton").stdout)
        self.clean_pack(scanned=True)
        row = next(l for l in self.copy_text("Demo_DEPLOYMENT_GUIDE.md").split("\n")
                   if l.startswith("| `server.port`"))
        cells = row.split(" | ")
        cells[2] = "framework"
        self.run_tool("replace", "DEPLOY", self.write_values("f.json", [[row, " | ".join(cells)]]))
        self.run_tool("check")

    def test_every_guide_section_has_text(self):
        self.clean_pack()
        guide = self.copy_text("Demo_DEPLOYMENT_GUIDE.md")
        section = guide.split("## 7. Database\n")[1].split("\n## 8.")[0]
        self.run_tool("replace", "DEPLOY", self.write_values("e.json", [
            ["## 7. Database\n" + section, "## 7. Database\n\n"]]))
        self.assertIn("section 7 (Database) is empty", self.run_tool("check", ok=False).stderr)

    def test_a_placeholder_hides_only_its_own_part_of_a_command(self):
        self.clean_pack()
        self.run_tool("replace", "RUN", self.write_values("p.json", [
            ["spring-boot:run", "spring-boot:run -DskipTests"]]))
        self.assertIn("the code block starting 'cd D:", self.run_tool("check", ok=False).stderr)

    def test_check_keeps_every_command_of_the_run_document(self):
        self.clean_pack()
        self.run_tool("replace", "RUN", self.write_values("r.json", [
            ["<your Maven folder>\\bin\\mvn.cmd spring-boot:run\n", ""]]))
        err = self.run_tool("check", ok=False).stderr
        self.assertIn("HOW_TO_RUN.md:5: the code block starting 'cd D:", err)

    def test_a_deploy_item_may_name_no_hit(self):
        self.clean_pack()
        self.add_rows("5", ["| I-90 |  | deploy | Still open |  | The production URL is not yet chosen. |"])
        self.run_tool("check")
        self.add_rows("5", ["| I-91 |  | new | Still open |  | Something. |"])
        self.assertIn("item I-91 names no hit (only a deploy item may)",
                      self.run_tool("check", ok=False).stderr)

    def test_a_new_version_remakes_only_copies_whose_source_changed(self):
        self.clean_pack()
        self.run_tool("set", "status=Final")
        brd = self.out / "BUSINESS_REQUIREMENTS_Demo.md"
        brd.write_text(brd.read_text(encoding="utf-8") + "\nBR-2 New rule.\n", encoding="utf-8")
        out = self.run_tool("copy", "--new-version").stdout
        self.assertIn("made  Demo_BRD.md", out)
        self.assertIn("kept  Demo_FRD.md", out)
        self.assertIn("kept  Demo_RUN_LOCALLY.md", out)
        self.assertIn("BR-2 New rule.", self.copy_text("Demo_BRD.md"))
        self.assertIn("`OPEN QUESTION:`", self.copy_text("Demo_BRD.md"))  # re-made: edits redone
        self.assertNotIn("TODO (AD)", self.copy_text("Demo_TRD.md"))  # kept: edits stay
        for name in ("Demo_FRD.md", "Demo_DEPLOYMENT_GUIDE.md", "Demo_RUN_LOCALLY.md"):
            text = self.copy_text(name)
            self.assertIn("version: 2.0\n", text)
            self.assertIn("status: Draft\n", text)
            self.assertIn(f"| 2.0 | {TODAY} | Draft | New version |", text)
        self.assertIn("Written for the deployer.", self.copy_text("Demo_DEPLOYMENT_GUIDE.md"))

    def test_a_copy_with_no_recorded_source_hash_is_made_again(self):
        self.clean_pack()
        notes = self.notes()
        head, tail = notes.split("## 10. Sources")
        (self.out / "CLIENT_PACK_NOTES.md").write_text(head + "## 10. Sources\n", encoding="utf-8")
        out = self.run_tool("copy", "--new-version").stdout
        self.assertIn("made  Demo_FRD.md", out)
        self.assertNotIn("kept", out)

    def test_exemptions_excuse_only_their_text_once(self):
        self.clean_pack()
        self.run_tool("replace", "HLD", self.write_values("h.json", [
            ["DD-1 Spring Boot.", "DD-1 Spring Boot. Our Stage 2 rollout, then Stage 2 support; see P-4."]]))
        self.add_rows("6", ["| Demo_HLD.md | Stage 2 | the client's rollout stages |"])
        err = self.run_tool("check", ok=False).stderr
        self.assertIn("matches 2 times", err)
        self.assertIn("harness ID 'P-4'", err)  # same line, not excused
        text = self.notes().replace("| Demo_HLD.md | Stage 2 |", "| Demo_HLD.md | Our Stage 2 rollout |")
        (self.out / "CLIENT_PACK_NOTES.md").write_text(text, encoding="utf-8")
        err = self.run_tool("check", ok=False).stderr
        self.assertNotIn("matches 2 times", err)
        self.assertEqual(err.count("harness word 'Stage 2'"), 1, err)  # only the second use

    def test_check_finds_a_stale_exemption_a_broken_anchor_and_a_conflict(self):
        self.clean_pack()
        self.add_rows("6", ["| Demo_BRD.md | never written anywhere | x |"])
        self.run_tool("replace", "BRD", self.write_values("b.json", [
            ["(Demo_FRD.md#2-rules)", "(Demo_FRD.md#9-nothing)"]]))
        text = self.notes().replace("| I-1 |", "| I-0 | H-aaaaaa | new | Conflict | x |  |\n| I-1 |", 1)
        (self.out / "CLIENT_PACK_NOTES.md").write_text(text, encoding="utf-8")
        err = self.run_tool("check", ok=False).stderr
        self.assertIn("exemption 'never written anywhere' for Demo_BRD.md matches nothing", err)
        self.assertIn("link 'Demo_FRD.md#9-nothing' names no heading", err)
        self.assertIn("item I-0 is a Conflict", err)
        self.assertIn("names H-aaaaaa, which no longer exists", err)

    def test_check_needs_evidence_for_a_settled_item(self):
        self.clean_pack()
        text = self.notes().replace("| Decided | changeLog 4 |", "| Adopted in build |  |", 1)
        (self.out / "CLIENT_PACK_NOTES.md").write_text(text, encoding="utf-8")
        self.assertIn("Adopted in build with no evidence", self.run_tool("check", ok=False).stderr)

    def test_without_state_json_both_overrides_are_needed(self):
        (self.out / "state.json").unlink()
        self.run_tool("scan", ok=False)
        self.run_tool("--docs", "out", "--app", "Demo", "scan")


if __name__ == "__main__":
    unittest.main()
