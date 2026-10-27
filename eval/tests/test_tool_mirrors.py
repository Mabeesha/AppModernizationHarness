#!/usr/bin/env python3
"""Every tool in ModernizationHarness/tools/ has a plain-text mirror, <name>.txt, with the same
content as <name>.py. This test fails when a mirror is missing, stale, or has no tool.

Run:     python tests/test_tool_mirrors.py           (check)
Refresh: python tests/test_tool_mirrors.py --sync    (rewrite every mirror from its tool)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / "ModernizationHarness" / "tools"


def _text(path: Path) -> str:
    # Compare content, not line endings: git may check either file out with CRLF.
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def sync() -> None:
    for tool in sorted(TOOLS.glob("*.py")):
        mirror = tool.with_suffix(".txt")
        mirror.write_bytes(tool.read_bytes())
        print(f"mirrored {tool.name} -> {mirror.name}")


class ToolMirrorTest(unittest.TestCase):
    def test_every_tool_has_an_identical_mirror(self):
        tools = sorted(TOOLS.glob("*.py"))
        self.assertTrue(tools, "no tools found")
        for tool in tools:
            mirror = tool.with_suffix(".txt")
            with self.subTest(tool=tool.name):
                self.assertTrue(mirror.exists(), f"{mirror.name} is missing - run "
                                "python tests/test_tool_mirrors.py --sync")
                self.assertEqual(_text(mirror), _text(tool), f"{mirror.name} differs from "
                                 f"{tool.name} - run python tests/test_tool_mirrors.py --sync")

    def test_every_mirror_has_a_tool(self):
        for mirror in sorted(TOOLS.glob("*.txt")):
            with self.subTest(mirror=mirror.name):
                self.assertTrue(mirror.with_suffix(".py").exists(),
                                f"{mirror.name} has no {mirror.stem}.py - delete it")


if __name__ == "__main__":
    if "--sync" in sys.argv[1:]:
        sync()
    else:
        unittest.main()
