#!/usr/bin/env python3
"""Tests for ModernizationHarness/tools/search.py, the file and text search tool.

Each test runs the real script as a subprocess — the way an agent calls it — against a small
fake project in a temporary directory, then checks what it printed and its exit status.

Run:  uv run tests/test_search_tool.py      (or: python tests/test_search_tool.py)
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "ModernizationHarness" / "tools" / "search.py"

FILES = {
    "src/app/order.service.ts": "export class OrderService {\n  save(order) {}\n  update() {}\n}\n",
    "src/app/order.component.ts": "import { OrderService } from './order.service';\n",
    "src/main/java/Shop/OrderRepository.java": "public class OrderRepository {\n  void save() {}\n}\n",
    "README.md": "# Shop\nRun with -Dmaven.test.skip=true\n",
    "node_modules/lib/index.js": "function save() {}\n",
    "frontend/dist/main.js": "save()\n",
    "backend/target/classes/x.txt": "save\n",
    "obj/Debug/x.cs": "save\n",
    ".harness-tmp/build.out.txt": "save\n",
    "logs/app.log": "save at 10:00\n",
    "generated/api.ts": "save\n",
    "keep/generated/note.txt": "save\n",
}


class SearchToolTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        (self.dir / ".git").mkdir()  # the working-tree root, as git marks it
        for rel, text in FILES.items():
            p = self.dir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(text.encode("utf-8"))
        (self.dir / ".gitignore").write_text("# build output\n*.log\n/generated/\n",
                                             encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, *args, cwd=None, code=0, env=None):
        res = subprocess.run([sys.executable, str(TOOL), *args], cwd=cwd or self.dir,
                             capture_output=True, encoding="ascii",
                             env=dict(os.environ, **env) if env else None)
        self.assertEqual(res.returncode, code, f"{args}: {res.stdout}{res.stderr}")
        return res

    def lines(self, res):
        return [ln for ln in res.stdout.splitlines() if not ln.startswith("--")]

    # --- help and malformed commands ---------------------------------------------------------

    def test_no_command_prints_help(self):
        res = self.run_tool(code=2)
        for text in ("files ROOT", "text PATTERN ROOT", "--include", "--all", "Exit status"):
            self.assertIn(text, res.stdout)

    def test_malformed_commands_exit_2_with_a_reason(self):
        for args in (("find", "x", "."), ("text", "x"), ("text", "x", "missing-folder"),
                     ("text", "(", "."), ("files", ".", "--max", "0"), ("text", "x", ".", "--nope"),
                     ("text", "x", ".", "--context", "two"), ("text", "--")):
            with self.subTest(args=args):
                res = self.run_tool(*args, code=2)
                self.assertIn("search.py:", res.stderr)
                self.assertEqual(res.stdout, "")

    def test_a_bad_regex_suggests_fixed(self):
        res = self.run_tool("text", "save(", ".", code=2)
        self.assertIn("--fixed", res.stderr)
        res = self.run_tool("text", "save(", "src", "--fixed")
        self.assertIn("src/app/order.service.ts:2:   save(order) {}", res.stdout)

    # --- text --------------------------------------------------------------------------------

    def test_regex_with_a_bar_prints_path_line_text(self):
        res = self.run_tool("text", "class (OrderService|OrderRepository)", ".")
        self.assertEqual(self.lines(res), [
            "src/app/order.service.ts:1: export class OrderService {",
            "src/main/java/Shop/OrderRepository.java:1: public class OrderRepository {"])
        self.assertIn("-- 2 match(es) in 2 file(s)", res.stdout)

    def test_paths_start_with_root_as_given(self):
        res = self.run_tool("text", "OrderService", "src/app", "--fixed")
        self.assertTrue(all(ln.startswith("src/app/") for ln in self.lines(res)), res.stdout)
        res = self.run_tool("text", "OrderService", "src\\app\\")  # Windows separators too
        self.assertTrue(all(ln.startswith("src/app/") for ln in self.lines(res)), res.stdout)

    def test_works_from_any_folder(self):
        res = self.run_tool("text", "OrderRepository", "..", cwd=self.dir / "src")
        self.assertIn("../src/main/java/Shop/OrderRepository.java:1:", res.stdout)

    def test_root_may_be_one_file(self):
        res = self.run_tool("text", "save", "src/app/order.service.ts")
        self.assertEqual(self.lines(res), ["src/app/order.service.ts:2:   save(order) {}"])

    def test_default_skips_and_gitignore(self):
        res = self.run_tool("text", "save", ".")
        found = {ln.split(":")[0] for ln in self.lines(res)}
        self.assertEqual(found, {"src/app/order.service.ts",
                                 "src/main/java/Shop/OrderRepository.java",
                                 "keep/generated/note.txt"})  # /generated/ is anchored
        self.assertIn("skipped", res.stdout)
        self.assertIn("--all", res.stdout)

    def test_all_searches_everything(self):
        res = self.run_tool("text", "save", ".", "--all")
        found = {ln.split(":")[0] for ln in self.lines(res)}
        for rel in ("node_modules/lib/index.js", "frontend/dist/main.js", "logs/app.log",
                    "backend/target/classes/x.txt", "obj/Debug/x.cs", ".harness-tmp/build.out.txt",
                    "generated/api.ts"):
            self.assertIn(rel, found)

    def test_a_root_inside_a_skipped_folder_is_searched(self):
        res = self.run_tool("text", "save", "node_modules")
        self.assertIn("node_modules/lib/index.js:1:", res.stdout)

    def test_nested_gitignore_and_gitignore_above_root(self):
        (self.dir / "src" / ".gitignore").write_text("*.java\n", encoding="utf-8")
        res = self.run_tool("text", "class", "src")
        self.assertNotIn("OrderRepository.java", res.stdout)
        self.assertIn("order.service.ts", res.stdout)
        # the root .gitignore's *.log applies to a ROOT below it
        res = self.run_tool("text", "save", "logs", code=1)
        self.assertIn("0 match(es)", res.stdout)

    def test_folder_only_and_negation_rules(self):
        (self.dir / ".gitignore").write_text("keep/\n!keep/generated/\n", encoding="utf-8")
        (self.dir / "keep.txt").write_text("save\n", encoding="utf-8")
        found = {ln.split(":")[0] for ln in self.lines(self.run_tool("text", "save", "."))}
        self.assertIn("keep.txt", found)  # keep/ names folders only
        self.assertNotIn("keep/generated/note.txt", found)  # ! lines are not read: documented

    def test_include_ignore_case_and_fixed(self):
        res = self.run_tool("text", "ORDERSERVICE", ".", "--include", "*.component.ts",
                            "--ignore-case")
        self.assertEqual(self.lines(res), [
            "src/app/order.component.ts:1: import { OrderService } from './order.service';"])
        res = self.run_tool("text", "save", ".", "--include", "*.java,src/app/*.ts")
        self.assertEqual(len(self.lines(res)), 2)
        res = self.run_tool("text", "save", ".", "--include", "**/Shop/*.java")
        self.assertEqual(len(self.lines(res)), 1)
        res = self.run_tool("text", "a.b", "README.md", "--fixed", code=1)
        self.assertIn("0 match(es)", res.stdout)

    def test_a_pattern_starting_with_a_dash_follows_double_dash(self):
        res = self.run_tool("text", "--", "-Dmaven", ".", "--include", "*.md")
        self.assertEqual(self.lines(res), ["README.md:2: Run with -Dmaven.test.skip=true"])

    def test_context_lines_and_group_separator(self):
        (self.dir / "big.txt").write_text("\n".join(f"line {i}" for i in range(1, 21)) + "\n",
                                          encoding="utf-8")
        res = self.run_tool("text", "^line (3|5|15)$", "big.txt", "--context", "1")
        self.assertEqual(res.stdout.splitlines()[:-1], [
            "big.txt-2- line 2", "big.txt:3: line 3", "big.txt-4- line 4", "big.txt:5: line 5",
            "big.txt-6- line 6", "--", "big.txt-14- line 14", "big.txt:15: line 15",
            "big.txt-16- line 16"])

    def test_max_stops_and_says_more_exist(self):
        (self.dir / "many.txt").write_text("hit\n" * 10, encoding="utf-8")
        res = self.run_tool("text", "hit", "many.txt", "--max", "3")
        self.assertEqual(len(self.lines(res)), 3)
        self.assertIn("stopped at --max 3", res.stdout)
        res = self.run_tool("text", "hit", "many.txt", "--max", "10")
        self.assertNotIn("stopped", res.stdout)

    def test_default_max_is_200(self):
        (self.dir / "many.txt").write_text("hit\n" * 250, encoding="utf-8")
        res = self.run_tool("text", "hit", "many.txt")
        self.assertEqual(len(self.lines(res)), 200)
        self.assertIn("stopped at --max 200", res.stdout)

    def test_encodings_and_binary(self):
        (self.dir / "enc").mkdir()
        (self.dir / "enc" / "bom.cs").write_bytes("﻿class Café {}\n".encode("utf-8"))
        (self.dir / "enc" / "utf16.sql").write_bytes("CREATE VIEW vCafé\r\n".encode("utf-16"))
        (self.dir / "enc" / "ansi.vb").write_bytes("Sub Café()\r\n".encode("cp1252"))
        (self.dir / "enc" / "image.png").write_bytes(b"\x89PNG\0\0Caf")
        res = self.run_tool("text", "Caf\\u00e9", "enc")
        self.assertEqual(sorted(self.lines(res)), [
            "enc/ansi.vb:1: Sub Caf\\xe9()", "enc/bom.cs:1: class Caf\\xe9 {}",
            "enc/utf16.sql:1: CREATE VIEW vCaf\\xe9"])  # ASCII output, escaped
        self.assertIn("1 binary file(s)", res.stdout)

    def test_long_lines_are_cut_around_the_match(self):
        (self.dir / "min.js").write_text("x" * 5000 + "NEEDLE" + "y" * 5000 + "\n",
                                         encoding="utf-8")
        line = self.lines(self.run_tool("text", "NEEDLE", "min.js"))[0]
        self.assertIn("NEEDLE", line)
        self.assertLess(len(line), 400)
        self.assertTrue(line.endswith(" ..."))

    def test_line_numbers_follow_line_breaks_only(self):
        (self.dir / "ff.txt").write_bytes(b"a\x0cb\r\nc\rtarget\n")
        res = self.run_tool("text", "target", "ff.txt")
        self.assertEqual(self.lines(res), ["ff.txt:3: target"])

    def test_control_characters_are_escaped(self):
        (self.dir / "ctl.txt").write_bytes(b"bell\x07 here\tand esc\x1b[31m\x0cend\n")
        line = self.lines(self.run_tool("text", "bell", "ctl.txt"))[0]
        self.assertEqual(line, "ctl.txt:1: bell\\x07 here\tand esc\\x1b[31m\\x0cend")

    def test_the_time_limit_stops_and_says_so(self):
        for command in (("text", "save", "."), ("files", ".")):
            with self.subTest(command=command[0]):
                res = self.run_tool(*command, code=1, env={"SEARCH_PY_SECONDS": "0"})
                self.assertIn("-- stopped after 0 s - narrow ROOT", res.stdout)

    def test_linked_folders_are_never_followed(self):
        # Python 3.11's walk follows a Windows junction; one to a parent would loop.
        loop = self.dir / "src" / "loop"
        if os.name == "nt":
            made = subprocess.run(["cmd", "/c", "mklink", "/J", str(loop), str(self.dir)],
                                  capture_output=True)
        else:
            try:
                loop.symlink_to(self.dir, target_is_directory=True)
                made = subprocess.CompletedProcess([], 0)
            except OSError:
                made = subprocess.CompletedProcess([], 1)
        if made.returncode or not loop.exists():
            self.skipTest("cannot make a junction or symbolic link here")
        try:
            res = self.run_tool("text", "class OrderRepository", ".")
            self.assertEqual(self.lines(res), [
                "src/main/java/Shop/OrderRepository.java:1: public class OrderRepository {"])
            self.assertIn("1 linked folder(s), never followed", res.stdout)
            self.assertNotIn("src/loop/", self.run_tool("files", ".", "--all").stdout)
        finally:
            os.rmdir(loop) if os.name == "nt" else loop.unlink()  # the link only, not its target

    def test_nothing_found_exits_1(self):
        res = self.run_tool("text", "no-such-text-anywhere", ".", code=1)
        self.assertIn("0 match(es)", res.stdout)

    # --- files -------------------------------------------------------------------------------

    def test_files_by_name_and_by_path(self):
        res = self.run_tool("files", ".", "*.ts")
        self.assertEqual(self.lines(res), ["src/app/order.component.ts",
                                           "src/app/order.service.ts"])
        res = self.run_tool("files", "src", "main/**/*.java", "*.component.ts")
        self.assertEqual(self.lines(res), ["src/app/order.component.ts",
                                           "src/main/java/Shop/OrderRepository.java"])
        res = self.run_tool("files", ".", "*.TS")  # letter case is ignored
        self.assertEqual(len(self.lines(res)), 2)

    def test_files_with_no_glob_lists_every_unskipped_file(self):
        found = self.lines(self.run_tool("files", "."))
        self.assertIn(".gitignore", found)
        self.assertIn("README.md", found)
        self.assertNotIn("node_modules/lib/index.js", found)
        self.assertNotIn("logs/app.log", found)
        self.assertIn("node_modules/lib/index.js", self.lines(self.run_tool("files", ".", "--all")))

    def test_files_max_and_nothing_found(self):
        res = self.run_tool("files", ".", "--max", "2")
        self.assertEqual(len(self.lines(res)), 2)
        self.assertIn("stopped at --max 2", res.stdout)
        self.run_tool("files", ".", "*.nothing", code=1)

    def test_never_writes(self):
        before = sorted(p.as_posix() for p in self.dir.rglob("*"))
        self.run_tool("text", "save", ".")
        self.run_tool("files", ".")
        self.assertEqual(sorted(p.as_posix() for p in self.dir.rglob("*")), before)


if __name__ == "__main__":
    unittest.main()
