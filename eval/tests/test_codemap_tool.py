#!/usr/bin/env python3
"""Tests for ModernizationHarness/tools/codemap.py, the legacy code map tool.

Each test runs the real script as a subprocess — the way an agent calls it — against a small
fake legacy app in a temporary directory, then reads the map it wrote.

Run:  uv run tests/test_codemap_tool.py      (or: python tests/test_codemap_tool.py)
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "ModernizationHarness" / "tools" / "codemap.py"
MARKER = "<!-- codemap:generated"

FILES = {
    "src/Orders/OrderService.cs": (
        "namespace Shop.Orders\n{\n"
        "    public class OrderService\n    {\n"
        "        private readonly List<Order> _orders = new List<Order>();\n"
        "        public decimal Total(int orderId)\n        {\n"
        "            if (orderId < 0) return 0;\n"
        "            return Calc(orderId);\n        }\n"
        "        private static decimal Calc(int id) { return 1; }\n"
        "    }\n}\n"),
    "src/Legacy/Billing.vb": (
        "Public Class Billing\n"
        "    Private Sub btnSave_Click(sender As Object, e As EventArgs)\n"
        "    End Sub\n"
        "    Public Function Rate() As Decimal\n        Return 1\n    End Function\n"
        "End Class\n"),
    "db/procs.sql": (
        "CREATE PROCEDURE [dbo].[usp_GetOrders] AS SELECT 1\nGO\n"
        "create or alter view dbo.vOrders as select 1\nGO\n"),
    "web/app.js": (
        "export class Cart {}\n"
        "function addItem(x) {}\n"
        "export const removeItem = (x) => x;\n"),
    "Web.config": "<configuration>\n</configuration>\n",
    "bin/Shop.dll": "MZ\0\0binary",
    "node_modules/lib/index.js": "function hidden() {}\n",
}


class CodemapToolTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        for rel, text in FILES.items():
            p = self.dir / "legacy" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(text.encode("utf-8"))
        self.map = self.dir / "out" / "LEGACY_CODE_MAP_Shop.md"

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, *args, ok=True):
        """Run codemap.py from the temp dir; assert it succeeded (or failed, when ok=False)."""
        res = subprocess.run([sys.executable, str(TOOL), *args], cwd=self.dir,
                             capture_output=True, encoding="ascii")
        if ok:
            self.assertEqual(res.returncode, 0, f"{args} failed: {res.stderr}")
        else:
            self.assertNotEqual(res.returncode, 0, f"{args} should have been refused")
            self.assertEqual(res.stdout, "", f"{args} printed output although it was refused")
        return res

    def build(self, *extra):
        self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md", "--title", "Shop", *extra)
        return self.map.read_text(encoding="utf-8")

    def line_for(self, text, rel):
        return next(l for l in text.splitlines() if l.startswith(f"- `legacy/{rel}`"))

    # --- what the map holds -------------------------------------------------------------------

    def test_declared_names_carry_their_line_numbers(self):
        text = self.build()
        cs = self.line_for(text, "src/Orders/OrderService.cs")
        self.assertIn("OrderService :3", cs)
        self.assertIn("Total :6", cs)
        self.assertIn("Calc :11", cs)
        self.assertNotIn("_orders", cs, "a field initializer is not a method")
        self.assertNotIn("if :", cs)

    def test_each_supported_language_is_read(self):
        text = self.build()
        vb = self.line_for(text, "src/Legacy/Billing.vb")
        for name in ("Billing :1", "btnSave_Click :2", "Rate :4"):
            self.assertIn(name, vb)
        self.assertNotIn("End", vb.split(" - ", 1)[1])
        sql = self.line_for(text, "db/procs.sql")
        self.assertIn("dbo.usp_GetOrders :1", sql)
        self.assertIn("dbo.vOrders :3", sql)
        js = self.line_for(text, "web/app.js")
        for name in ("Cart :1", "addItem :2", "removeItem :3"):
            self.assertIn(name, js)

    def test_unknown_kinds_are_listed_without_names(self):
        self.assertIn("- `legacy/Web.config` (2)\n", self.build())

    def test_binary_files_and_build_folders_are_skipped(self):
        text = self.build()
        self.assertNotIn("Shop.dll", text)
        self.assertNotIn("node_modules", text)
        self.assertNotIn("hidden", text)

    def test_exclude_skips_a_named_folder(self):
        text = self.build("--exclude", "db")
        self.assertNotIn("procs.sql", text)
        self.assertIn("OrderService.cs", text)

    def test_folder_table_counts_files(self):
        text = self.build()
        self.assertIn("| `legacy/src/Orders` | 1 | 13 | .cs 1 |", text)

    def test_map_has_the_three_sections_in_order(self):
        text = self.build()
        one, two, three = (text.index(h) for h in
                           ("## 1. Where Things Live", "## 2. Folders", "## 3. Files"))
        self.assertTrue(one < text.index(MARKER) < two < three)

    def test_output_reports_counts(self):
        res = self.run_tool("legacy", "--out", "out/m.md")
        self.assertIn("5 files", res.stdout)
        self.assertIn("placeholder for Stage 1", res.stdout)

    # --- rerun keeps Stage 1's notes ----------------------------------------------------------

    def test_rerun_keeps_section_one_and_refreshes_the_rest(self):
        text = self.build()
        notes = "| Orders | `legacy/src/Orders/` | order totals |\n\n"
        self.map.write_text(text.replace("*(Stage 1 fills this in", notes + "*(was", 1),
                            encoding="utf-8")
        (self.dir / "legacy" / "src" / "New.cs").write_text("public class Added {}\n",
                                                            encoding="utf-8")
        res = self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md")
        self.assertIn("kept section 1", res.stdout)
        again = self.map.read_text(encoding="utf-8")
        self.assertIn(notes, again)
        self.assertIn("Added :1", again)
        self.assertEqual(again.count(MARKER), 1)

    # --- refusals -----------------------------------------------------------------------------

    def test_map_inside_the_legacy_source_is_refused(self):
        err = self.run_tool("legacy", "--out", "legacy/MAP.md", ok=False).stderr
        self.assertIn("read-only", err)
        self.assertFalse((self.dir / "legacy" / "MAP.md").exists())

    def test_foreign_file_is_not_overwritten(self):
        self.map.parent.mkdir()
        self.map.write_text("# someone else's notes\n", encoding="utf-8")
        err = self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md", ok=False).stderr
        self.assertIn("not written by this tool", err)
        self.assertEqual(self.map.read_text(encoding="utf-8"), "# someone else's notes\n")

    def test_missing_source_root_is_refused(self):
        self.assertIn("not found", self.run_tool("nope", "--out", "out/m.md", ok=False).stderr)


if __name__ == "__main__":
    unittest.main(verbosity=1)
