#!/usr/bin/env python3
"""Tests for ModernizationHarness/tools/md2pdf.py, the Markdown-to-PDF tool.

The page-building and clean-up functions are tested directly; the end-to-end tests run the real
script as a subprocess and need Chrome, Edge or Chromium - they skip where none is installed.

Run:  uv run tests/test_md2pdf_tool.py      (or: python tests/test_md2pdf_tool.py)
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / "ModernizationHarness" / "tools"
TOOL = TOOLS / "md2pdf.py"
sys.dont_write_bytecode = True  # no __pycache__ beside the tools: the folder is copied into projects
_spec = importlib.util.spec_from_file_location("md2pdf", TOOL)
md2pdf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md2pdf)

GOOD = """---
title: High-Level Design — Demo
version: 1.0
date: 2026-11-05
status: Draft
prepared-for: Acme Ltd
prepared-by: Platform Team
---

# High-Level Design — Demo

## 1. Overview
See [the rules](Demo_FRD.md#2-rules). A tricky </script> stays text.

```mermaid
flowchart LR
  A[Browser<br/>client] --> B[API]
```
*Figure 1 — Topology.*

## 2. Data
| ID | Rule |
|---|---|
| VR-1 | Name max 50 |

## 3. More
Text.
"""

BAD = """# Bad

```mermaid
flowchart TD
  A -->
  this is not valid ((((
```

![missing](nope.png)

| a | b | c | d | e | f | g | h | i |
|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
"""


class PageTest(unittest.TestCase):
    """The parts that need no browser."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_front_matter_is_read_and_counted(self):
        fm, body, offset = md2pdf.front_matter(GOOD)
        self.assertEqual(fm["prepared-for"], "Acme Ltd")
        self.assertEqual(offset, 8)  # body line 1 is file line 9
        self.assertTrue(body.startswith("\n# High-Level Design"))
        self.assertEqual(md2pdf.front_matter("# No front matter\n"), ({}, "# No front matter\n", 0))

    def test_the_page_embeds_the_markdown_safely(self):
        md = self.dir / "Demo_HLD.md"
        md.write_text(GOOD, encoding="utf-8")
        page, title = md2pdf.build_page(str(md), "A4", None)
        self.assertEqual(title, "High-Level Design — Demo")
        source = page.split('id="md2pdf-source">', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("<", source)  # no </script> inside the JSON can end the block early
        self.assertIn("A tricky", json.loads(source))
        self.assertIn('class="cover"', page)
        self.assertIn('class="watermark"', page)
        self.assertIn("size: A4;", page)
        self.assertIn("@page :first", page)
        self.assertNotIn("http", page.split("<script>")[0].replace("http-equiv", ""))

    def test_landscape_and_letter_change_the_page(self):
        md = self.dir / "x.md"
        md.write_text("---\ntitle: X\norientation: landscape\n---\n# X\n", encoding="utf-8")
        page, _ = md2pdf.build_page(str(md), "letter", None)
        self.assertIn("size: letter landscape;", page)
        self.assertIn("width: 247.4mm", page)

    def test_the_static_page_has_nothing_left_to_run_or_fetch(self):
        (self.dir / "img.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
        dom = ('<html><head><base href="file:///x/"><script src="a.js"></script></head><body>'
               '<img src="img.png"><img src="https://example.com/x.png">'
               '<script type="application/json" id="md2pdf-report">{}</script></body></html>')
        out = md2pdf.static_page(dom, str(self.dir))
        self.assertTrue(out.startswith("<!doctype html>"))
        self.assertNotIn("<script", out)
        self.assertNotIn("<base", out)
        self.assertIn('src="data:image/png;base64,', out)
        self.assertIn('src="https://example.com/x.png"', out)

    def test_problems_are_described_for_people(self):
        report = {"failed": [{"line": 3, "error": "Parse error"}], "missingImages": ["nope.png"],
                  "wideTables": [{"heading": "Data", "columns": 9, "width": 900, "available": 670}],
                  "error": None}
        problems = md2pdf.problems_in(report)
        self.assertEqual(len(problems), 3)
        self.assertIn("diagram at line 3", problems[0])
        self.assertIn("orientation: landscape", problems[2])
        self.assertEqual(md2pdf.problems_in(None)[0][:20], "the page reported no")

    def test_a_wildcard_and_a_missing_file_are_refused(self):
        for args, said in ((["*.md"], "expands no wildcard"), (["nope.md"], "does not exist"),
                           (["x.md", "--paper", "A3"], "A4 or letter")):
            (self.dir / "x.md").write_text("# x\n", encoding="utf-8")
            p = subprocess.run([sys.executable, str(TOOL), *args], cwd=self.dir,
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 2, p.stderr)
            self.assertIn(said, p.stderr)


@unittest.skipUnless(md2pdf.candidates(), "no Chrome, Edge or Chromium installed")
class BrowserTest(unittest.TestCase):
    """End to end, through the browser that is installed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args], cwd=self.dir,
                              capture_output=True, text=True, timeout=600)

    def test_a_good_file_prints_with_its_diagram_and_table(self):
        (self.dir / "Demo_HLD.md").write_text(GOOD, encoding="utf-8")
        p = self.run_tool("Demo_HLD.md", "--out", "pdf")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("1 diagrams, 1 tables", p.stdout)
        pdf = (self.dir / "pdf" / "Demo_HLD.pdf").read_bytes()
        self.assertTrue(pdf.startswith(b"%PDF"))
        html = (self.dir / "pdf" / "Demo_HLD.html").read_text(encoding="utf-8")
        self.assertIn("<svg", html)
        self.assertNotIn("<script", html)
        self.assertIn('href="Demo_FRD.pdf#2-rules"', html)
        self.assertIn('class="caption"', html)
        self.assertIn('id="2-data"', html)
        self.assertFalse((self.dir / ".harness-tmp" / "md2pdf").exists(), "temp files left")

    def test_problems_stop_the_print_unless_forced(self):
        (self.dir / "bad.md").write_text(BAD, encoding="utf-8")
        p = self.run_tool("bad.md", "--check")
        self.assertEqual(p.returncode, 1)
        for said in ("diagram at line 3", "image nope.png did not load", "9 columns"):
            self.assertIn(said, p.stdout)
        p = self.run_tool("bad.md")
        self.assertEqual(p.returncode, 1)
        self.assertIn("not printed", p.stdout)
        self.assertFalse((self.dir / "pdf" / "bad.pdf").exists())
        p = self.run_tool("bad.md", "--force")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((self.dir / "pdf" / "bad.pdf").exists())

    def test_a_landscape_page_takes_a_wide_table(self):
        cols = "| " + " | ".join("c" for _ in range(10)) + " |\n|" + "---|" * 10 + "\n"
        (self.dir / "w.md").write_text(f"# W\n\n{cols}", encoding="utf-8")
        self.assertIn("orientation: landscape", self.run_tool("w.md", "--check").stdout)
        (self.dir / "w.md").write_text(f"---\norientation: landscape\n---\n# W\n\n{cols}",
                                       encoding="utf-8")
        p = self.run_tool("w.md", "--check")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_a_browser_that_gives_up_is_skipped(self):
        fake = self.dir / ("fake.bat" if os.name == "nt" else "fake.sh")
        fake.write_text("@exit /b 0\n" if os.name == "nt" else "#!/bin/sh\nexit 0\n")
        fake.chmod(0o755)
        (self.dir / "x.md").write_text("# x\n", encoding="utf-8")
        p = self.run_tool("x.md", "--browser", str(fake))
        self.assertEqual(p.returncode, 2)
        self.assertIn("exited at once with no output", p.stderr)


if __name__ == "__main__":
    unittest.main()
