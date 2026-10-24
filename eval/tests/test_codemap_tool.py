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
    "src/Orders/Modern.cs": (
        "public class Modern\n{\n"
        "    public Modern(int seed)\n    {\n"
        "        var t = new Thread(() =>\n"
        "            Run(seed,\n"
        "                1));\n    }\n"
        "    public Dictionary<string, int> Map(int a)\n    {\n        return Lookup(a);\n    }\n"
        "    public static IEnumerable<Tuple<int, string>> Pairs() { yield break; }\n"
        "    public int Calc() => 42;\n"
        "    void ImplicitPrivate()\n    {\n    }\n"
        "    public abstract void Declared();\n"
        "}\n"),
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

    def run_tool(self, *args, ok=True, cwd=None):
        """Run codemap.py from the temp dir; assert it succeeded (or failed, when ok=False)."""
        res = subprocess.run([sys.executable, str(TOOL), *args], cwd=cwd or self.dir,
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

    def test_common_csharp_method_shapes_are_found(self):
        cs = self.line_for(self.build(), "src/Orders/Modern.cs")
        for name in ("Modern :1", "Modern :3", "Map :9", "Pairs :13", "Calc :14",
                     "ImplicitPrivate :15"):
            self.assertIn(name, cs)
        for wrong in ("Thread", "Run", "Lookup", "Declared"):
            self.assertNotIn(wrong, cs, "a call or a bodiless declaration is not a method")

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

    def test_utf16_sql_script_is_read(self):
        # SQL Server Management Studio saves generated scripts as UTF-16 with a byte-order mark
        path = self.dir / "legacy" / "db" / "unicode.sql"
        path.write_bytes("CREATE PROCEDURE dbo.usp_GetEmp AS\r\nSELECT 1\r\n".encode("utf-16"))
        sql = self.line_for(self.build(), "db/unicode.sql")
        self.assertIn("(2) - dbo.usp_GetEmp :1", sql)

    def test_wrapped_parameter_lists_are_found(self):
        path = self.dir / "legacy" / "src" / "Ctl.cs"
        path.write_text("public class Ctl\n{\n"
                        "    public Ctl(IRepo repo,\n        ILog log)\n    {\n    }\n"
                        "    public ActionResult Search(string name, int page,\n"
                        "        int size)\n    {\n    }\n}\n", encoding="utf-8")
        cs = self.line_for(self.build(), "src/Ctl.cs")
        self.assertIn("Ctl :3", cs)
        self.assertIn("Search :7", cs)

    def test_statement_lines_are_not_names(self):
        path = self.dir / "legacy" / "src" / "Stmts.cs"
        path.write_text("public class Stmts\n{\n    public void Go()\n    {\n"
                        "        else if (ready)\n"
                        "        await Send(x)\n"
                        "        throw new InvalidOperationException(\n"
                        "            select new Row(\n"
                        "        new Runnable() {\n"
                        "        return Build(a,\n"
                        "            where IsActive(o)\n"
                        "            orderby Key(o)\n"
                        "    }\n}\n", encoding="utf-8")
        cs = self.line_for(self.build(), "src/Stmts.cs")
        self.assertTrue(cs.endswith(" - Stmts :1, Go :3"), cs)

    def test_windows_1252_file_keeps_true_line_numbers(self):
        # a 0x85 ellipsis and a form feed must not count as line breaks
        path = self.dir / "legacy" / "src" / "Form1.cs"
        path.write_bytes(b"public class Form1\r\n{\r\n    string s = \"Loading\x85\"; // \x0c\r\n"
                         b"    public void Save()\r\n    {\r\n    }\r\n}\r\n")
        cs = self.line_for(self.build(), "src/Form1.cs")
        self.assertIn("(7) - Form1 :1, Save :4", cs)

    def test_utf16_big_endian_file_is_read(self):
        path = self.dir / "legacy" / "db" / "be.sql"
        path.write_bytes(b"\xfe\xff" + "SELECT 1\nCREATE VIEW dbo.vBig AS SELECT 1\n".encode("utf-16-be"))
        self.assertIn("(2) - dbo.vBig :2", self.line_for(self.build(), "db/be.sql"))

    def test_harness_folders_are_skipped(self):
        for rel in ("ModernizationHarness/tools/state.py", ".agents/skills/x/run.py"):
            p = self.dir / "legacy" / rel
            p.parent.mkdir(parents=True)
            p.write_text("def harness():\n    pass\n", encoding="utf-8")
        text = self.build()
        self.assertNotIn("ModernizationHarness", text.split("## 3. Files", 1)[1])
        self.assertNotIn("harness :1", text)

    def test_large_file_is_counted_without_names(self):
        path = self.dir / "legacy" / "src" / "Huge.cs"
        path.write_bytes(b"public class Huge {}\n" + b"// filler line of text\n" * 100_000)
        self.assertIn("- `legacy/src/Huge.cs` (100001)\n", self.build())

    def test_unknown_kinds_are_listed_without_names(self):
        self.assertIn("- `legacy/Web.config` (2)\n", self.build())

    def test_binary_files_and_build_folders_are_skipped(self):
        text = self.build()
        self.assertNotIn("Shop.dll", text)
        self.assertNotIn("node_modules", text)
        self.assertNotIn("hidden", text)

    def test_rerun_without_exclude_reuses_the_saved_excludes(self):
        text = self.build("--exclude", "db", "--exclude", "src/Legacy")
        self.assertIn("Excluded: `db`, `./src/Legacy`.", text)
        self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md")      # a later refresh
        again = self.map.read_text(encoding="utf-8")
        self.assertNotIn("procs.sql", again)
        self.assertNotIn("Billing.vb", again)
        self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md", "--exclude", "web")
        replaced = self.map.read_text(encoding="utf-8")
        self.assertIn("procs.sql", replaced)
        self.assertNotIn("app.js", replaced)

    def test_exclude_path_may_be_spelled_from_the_working_tree_or_absolute(self):
        # agents take paths from state.json: relative to the working-tree root, or absolute
        for spelling in ("legacy/src/Legacy", "./legacy/src/Legacy",
                         str(self.dir / "legacy" / "src" / "Legacy"), "./src/Legacy"):
            text = self.build("--exclude", spelling)
            self.assertNotIn("Billing.vb", text, spelling)
            self.assertIn("Excluded: `./src/Legacy`.", text, spelling)

    def test_exclude_naming_no_folder_is_refused(self):
        self.build()
        before = self.map.read_bytes()
        for wrong in ("legacy/src/Nope", "Nope", str(self.dir / "elsewhere")):
            err = self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md",
                                "--exclude", wrong, ok=False).stderr
            self.assertIn("no folder", err)
        self.assertEqual(self.map.read_bytes(), before)

    def test_top_level_path_exclude_spares_nested_folders_of_that_name(self):
        for rel in ("Scripts/deploy.ps1", "Site/Scripts/site.js"):
            p = self.dir / "legacy" / rel
            p.parent.mkdir(parents=True)
            p.write_text("x\n", encoding="utf-8")
        for spelling in ("legacy/Scripts", "./Scripts"):
            text = self.build("--exclude", spelling)
            self.assertNotIn("deploy.ps1", text, spelling)
            self.assertIn("legacy/Site/Scripts/site.js", text, spelling)
        self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md")   # refresh reuses it
        again = self.map.read_text(encoding="utf-8")
        self.assertNotIn("deploy.ps1", again)
        self.assertIn("legacy/Site/Scripts/site.js", again)
        text = self.build("--exclude", "Scripts")                          # a bare name: all
        self.assertNotIn("deploy.ps1", text)
        self.assertNotIn("site.js", text)

    def test_only_default_skip_excludes_keep_the_saved_list(self):
        self.build("--exclude", "db")
        self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md", "--exclude", "bin")
        self.assertNotIn("procs.sql", self.map.read_text(encoding="utf-8"))

    def test_stale_saved_exclude_is_dropped_not_blamed_when_only_defaults_are_given(self):
        self.build("--exclude", "Legacy")
        for f in (self.dir / "legacy" / "src" / "Legacy").iterdir():
            f.unlink()
        (self.dir / "legacy" / "src" / "Legacy").rmdir()                 # a newer legacy drop
        res = self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md", "--exclude", "bin")
        self.assertIn("dropped saved excludes: Legacy", res.stdout)

    def test_replacing_the_saved_list_names_what_was_dropped(self):
        self.build("--exclude", "db")
        res = self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md", "--exclude", "web")
        self.assertIn("dropped saved excludes: db", res.stdout)
        self.assertIn("procs.sql", self.map.read_text(encoding="utf-8"))

    def test_excluding_a_default_skip_folder_is_a_quiet_no_op(self):
        # bin and obj may not exist yet on a fresh clone; they are skipped by default anyway
        text = self.build("--exclude", "bin", "--exclude", "OBJ")
        self.assertNotIn("codemap:exclude", text)
        self.assertIn("OrderService.cs", text)

    def test_exclude_climbing_out_of_the_root_is_refused(self):
        (self.dir / "other" / "x").mkdir(parents=True)
        err = self.run_tool("legacy", "--out", "out/m.md", "--exclude", "../other/x",
                            ok=False).stderr
        self.assertIn("no folder", err)

    def test_saved_exclude_that_no_longer_matches_is_dropped_with_a_note(self):
        self.build("--exclude", "db")
        for f in (self.dir / "legacy" / "db").iterdir():
            f.unlink()
        (self.dir / "legacy" / "db").rmdir()
        res = self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md")
        self.assertIn("dropped saved excludes: db", res.stdout)
        self.assertNotIn("codemap:exclude", self.map.read_text(encoding="utf-8"))

    def test_skipped_folder_names_ignore_letter_case(self):
        p = self.dir / "legacy" / "src" / "Bin" / "App.xml"
        p.parent.mkdir()
        p.write_text("<x/>\n", encoding="utf-8")
        self.assertNotIn("App.xml", self.build())

    def test_exclude_skips_a_named_folder(self):
        text = self.build("--exclude", "db")
        self.assertNotIn("procs.sql", text)
        self.assertIn("OrderService.cs", text)

    def test_exclude_takes_a_path_below_the_root(self):
        text = self.build("--exclude", "src\\Legacy")
        self.assertNotIn("Billing.vb", text)
        self.assertIn("OrderService.cs", text)

    def test_root_given_as_dot_or_with_trailing_slash(self):
        self.run_tool(".", "--out", "../out/m.md", cwd=self.dir / "legacy")
        self.assertIn("- `web/app.js` (3)", (self.dir / "out" / "m.md").read_text(encoding="utf-8"))
        self.run_tool("legacy/", "--out", "out/n.md")
        self.assertIn("- `legacy/web/app.js` (3)",
                      (self.dir / "out" / "n.md").read_text(encoding="utf-8"))

    def test_folder_table_counts_files(self):
        text = self.build()
        self.assertIn("| `legacy/src/Orders` | 2 | 32 | .cs 2 |", text)

    def test_map_has_the_three_sections_in_order(self):
        text = self.build()
        one, two, three = (text.index(h) for h in
                           ("## 1. Where Things Live", "## 2. Folders", "## 3. Files"))
        self.assertTrue(one < text.index(MARKER) < two < three)

    def test_output_reports_counts(self):
        res = self.run_tool("legacy", "--out", "out/m.md")
        self.assertIn("6 files", res.stdout)
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

    def test_rerun_keeps_section_one_of_a_crlf_file_with_bom(self):
        text = self.build().replace("*(Stage 1 fills this in", "| Orders | x |\n\n*(was", 1)
        self.map.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8"))
        self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md")
        self.assertIn("| Orders | x |", self.map.read_text(encoding="utf-8"))

    def test_hand_written_map_without_marker_is_kept_and_extended(self):
        # Stage 1 without Python writes section 1 by hand, with no marker line
        self.map.parent.mkdir()
        hand = "# Legacy Code Map: Shop\n\n## 1. Where Things Live\n\n| Orders | x |\n"
        self.map.write_text(hand, encoding="utf-8")
        res = self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md")
        self.assertIn("kept section 1", res.stdout)
        text = self.map.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(hand))
        self.assertIn("## 3. Files", text)

    def test_hand_written_map_in_a_windows_encoding_is_kept(self):
        # Windows PowerShell 5.1 writes ANSI (Set-Content) or UTF-16 (Out-File)
        self.map.parent.mkdir()
        hand = "# Legacy Code Map: Shop\r\n\r\n## 1. Where Things Live\r\n\r\n| Orders — totals |\r\n"
        for encoded in (hand.encode("cp1252"), hand.encode("utf-16")):
            self.map.write_bytes(encoded)
            self.run_tool("legacy", "--out", "out/LEGACY_CODE_MAP_Shop.md")
            text = self.map.read_text(encoding="utf-8")
            self.assertIn("| Orders — totals |\n", text)
            self.assertIn("## 3. Files", text)

    # --- where the map may go -----------------------------------------------------------------

    def test_map_directly_in_the_legacy_root_is_refused(self):
        err = self.run_tool("legacy", "--out", "legacy/MAP.md", ok=False).stderr
        self.assertIn("read-only", err)
        self.assertFalse((self.dir / "legacy" / "MAP.md").exists())

    def test_documents_folder_inside_the_legacy_source_is_left_out(self):
        # a harness installed in the legacy repo: legacy source ".", documents "./out"
        docs = self.dir / "legacy" / "out"
        docs.mkdir()
        (docs / "PROJECT_CONTEXT.md").write_text("# context\n", encoding="utf-8")
        self.run_tool(".", "--out", "out/LEGACY_CODE_MAP_Shop.md", cwd=self.dir / "legacy")
        text = (docs / "LEGACY_CODE_MAP_Shop.md").read_text(encoding="utf-8")
        self.assertNotIn("PROJECT_CONTEXT", text)
        self.assertNotIn("`out", text)
        self.assertIn("src/Orders/OrderService.cs", text)

    def test_out_that_is_a_folder_is_refused(self):
        (self.dir / "out").mkdir()
        self.assertIn("is a folder", self.run_tool("legacy", "--out", "out", ok=False).stderr)

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
