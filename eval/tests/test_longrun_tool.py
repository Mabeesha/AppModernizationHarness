#!/usr/bin/env python3
"""Tests for ModernizationHarness/tools/longrun.py, the long-command tool.

Each test runs the real script as a subprocess — the way an agent calls it — from a fresh
temporary directory, with a tiny Python program standing in for the build, then looks at what
it printed, its exit status and the files it left in .harness-tmp/.

Run:  uv run tests/test_longrun_tool.py      (or: python tests/test_longrun_tool.py)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "ModernizationHarness" / "tools" / "longrun.py"
PY = sys.executable
WIN = os.name == "nt"


def alive(pid: int) -> bool:
    if WIN:
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class LongrunToolTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.tmp = self.dir / ".harness-tmp"
        self.started: list[str] = []

    def tearDown(self):
        for name in self.started:  # never leave a sleeping program behind
            self.run_tool("stop", name)
        for _ in range(50):  # Windows may hold a just-killed program's log for a moment
            try:
                self._tmp.cleanup()
                break
            except OSError:
                time.sleep(0.1)

    def run_tool(self, *args, cwd=None):
        return subprocess.run([PY, str(TOOL), *args], cwd=cwd or self.dir, capture_output=True,
                              encoding="ascii", timeout=120)

    def start(self, name, code, *opts, seconds="30"):
        """start NAME running `python -c code`; the default wait lets a quick program finish."""
        if name not in self.started:
            self.started.append(name)
        return self.run_tool("start", name, "--seconds", seconds, *opts, "--", PY, "-c", code)

    def files(self):
        return sorted(p.name for p in self.tmp.iterdir()) if self.tmp.exists() else []

    # --- help and malformed commands ---------------------------------------------------------

    def test_no_command_prints_help(self):
        res = self.run_tool()
        self.assertEqual(res.returncode, 2)
        for text in ("start NAME", "wait NAME", "stop NAME", "--seconds 25"):
            self.assertIn(text, res.stdout)

    def test_malformed_commands_exit_2_and_start_nothing(self):
        for args in (("start", "../x", "--", PY), ("start", "b", "--wait", PY), ("start", "b", "--"),
                     ("start", "b", "--seconds", "soon", "--", PY), ("wait",), ("stop", "b", "x"),
                     ("start", "b", "--dir", "missing", "--", PY)):
            with self.subTest(args=args):
                res = self.run_tool(*args)
                self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
                self.assertIn("longrun.py:", res.stderr)
        self.assertEqual(self.files(), [])

    def test_unknown_program_is_refused(self):
        res = self.run_tool("start", "b", "--", "no-such-program-xyz", "verify")
        self.assertEqual(res.returncode, 2)
        self.assertIn("no-such-program-xyz: not found", res.stderr)
        self.assertNotIn("b.status", self.files())

    def test_wait_for_nothing_exits_2(self):
        res = self.run_tool("wait", "b", "--seconds", "0")
        self.assertEqual(res.returncode, 2)
        self.assertIn("nothing started under b", res.stderr)

    # --- outcomes ------------------------------------------------------------------------------

    def test_success_prints_the_tail_and_removes_its_files(self):
        res = self.start("build", "import sys; print('compiled'); sys.stderr.write('warn\\n')")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("build: finished, exit code 0", res.stdout)
        self.assertIn("compiled", res.stdout)
        self.assertIn("warn", res.stdout)  # stderr goes to the same log
        self.assertIn("removed", res.stdout)
        self.assertEqual(self.files(), [])
        self.assertEqual(self.run_tool("wait", "build").returncode, 2)  # nothing left to wait on

    def test_failure_keeps_the_log_and_names_it(self):
        res = self.start("build", "import sys; print('Tests run: 3, Failures: 1'); sys.exit(7)")
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("FAILED, exit code 7", res.stdout)
        self.assertIn("Failures: 1", res.stdout)
        # .out.txt, not .log: many projects' .gitignore has *.log, which Duo's file tool refuses
        self.assertIn(os.path.join(".harness-tmp", "build.out.txt"), res.stdout)
        self.assertIn("--lines 200", res.stdout)
        self.assertEqual(self.files(), ["build.out.txt", "build.status"])
        again = self.run_tool("wait", "build", "--seconds", "0")  # the same answer again
        self.assertEqual(again.returncode, 1)
        self.assertIn("exit code 7", again.stdout)
        # the next start replaces the old log
        res = self.start("build", "print('second run')")
        self.assertEqual(res.returncode, 0)
        self.assertNotIn("Failures", res.stdout)
        self.assertEqual(self.files(), [])

    def test_still_running_then_finished_across_waits(self):
        res = self.start("tests", "import time; print('begin', flush=True); time.sleep(4); "
                                  "print('done')", seconds="0")
        self.assertEqual(res.returncode, 3, res.stdout + res.stderr)
        self.assertIn("tests: started", res.stdout)
        self.assertIn("still running", res.stdout)
        res = self.run_tool("wait", "tests", "--seconds", "1")
        self.assertEqual(res.returncode, 3)
        self.assertIn("begin", res.stdout)  # the log so far
        self.assertIn("run `longrun.py wait tests` again", res.stdout)
        res = self.run_tool("wait", "tests", "--seconds", "60")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("done", res.stdout)

    def test_start_returns_at_once_and_does_not_hold_the_callers_output(self):
        # A command tool reads the command's output until it closes; a background program that
        # kept it open would hold the tool for its whole run.
        began = time.monotonic()
        res = self.start("slow", "import time; time.sleep(30)", seconds="0")
        self.assertLess(time.monotonic() - began, 15)
        self.assertEqual(res.returncode, 3)

    def test_a_second_start_is_refused_while_running(self):
        self.start("build", "import time; time.sleep(30)", seconds="0")
        res = self.start("build", "print('again')", seconds="0")
        self.assertEqual(res.returncode, 2)
        self.assertIn("refused: build is already running", res.stderr)

    def test_stop_ends_the_program_prints_its_log_and_removes_its_files(self):
        pidfile = self.dir / "pid.txt"
        code = (f"import os, time; open({str(pidfile)!r}, 'w').write(str(os.getpid())); "
                "print('serving', flush=True); time.sleep(60)")
        self.assertEqual(self.start("app", code, seconds="0").returncode, 3)
        for _ in range(100):
            if pidfile.exists() and pidfile.read_text():
                break
            time.sleep(0.1)
        pid = int(pidfile.read_text())
        self.assertTrue(alive(pid))
        res = self.run_tool("stop", "app")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("app: stopped", res.stdout)
        self.assertIn("serving", res.stdout)  # the log's last lines, before it goes
        for _ in range(50):
            if not alive(pid):
                break
            time.sleep(0.1)
        self.assertFalse(alive(pid), "stop left the program running")
        self.assertEqual(self.files(), [])
        self.assertEqual(self.run_tool("wait", "app", "--seconds", "0").returncode, 2)
        self.assertIn("not running", self.run_tool("stop", "nothing").stdout)

    def test_lost_runner_is_reported(self):
        self.tmp.mkdir()
        status = self.tmp / "build.status"
        then = time.time() - 120
        status.write_text(json.dumps({"command": ["mvn", "verify"], "pid": 4242,
                                      "started": then}), encoding="utf-8")
        os.utime(status, (then, then))
        res = self.run_tool("wait", "build", "--seconds", "0")
        self.assertEqual(res.returncode, 4, res.stdout + res.stderr)
        self.assertIn("LOST", res.stdout)
        self.assertIn("mvn verify", res.stdout)
        res = self.run_tool("stop", "build")  # its program is gone: stop clears the files
        self.assertIn("no longer running - nothing to stop", res.stdout)
        self.assertEqual(self.files(), [])
        # a lost run does not block a new start
        self.assertEqual(self.start("build", "print('ok')").returncode, 0)

    def test_the_build_survives_when_the_start_call_is_cut_off(self):
        # A platform may kill the whole process tree of a command that hit its time limit. The
        # runner is started through a go-between that exits at once, so it is not in that tree.
        self.started.append("b")
        call = subprocess.Popen([PY, str(TOOL), "start", "b", "--seconds", "60", "--", PY, "-c",
                                 "import time; time.sleep(4); print('built')"], cwd=self.dir,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=not WIN)
        status = self.tmp / "b.status"
        for _ in range(100):
            if status.exists() and "program_pid" in status.read_text(encoding="utf-8"):
                break
            time.sleep(0.1)
        if WIN:
            subprocess.run(["taskkill", "/PID", str(call.pid), "/T", "/F"], capture_output=True)
        else:
            os.killpg(call.pid, 9)
        call.wait()
        res = self.run_tool("wait", "b", "--seconds", "60")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("built", res.stdout)

    def test_a_lost_runner_whose_program_still_runs_can_be_stopped(self):
        pidfile = self.dir / "pid.txt"
        code = (f"import os, time; open({str(pidfile)!r}, 'w').write(str(os.getpid())); "
                "time.sleep(60)")
        self.assertEqual(self.start("app", code, seconds="0").returncode, 3)
        status = self.tmp / "app.status"
        for _ in range(100):
            if pidfile.exists() and pidfile.read_text() and \
                    "program_pid" in status.read_text(encoding="utf-8"):
                break
            time.sleep(0.1)
        program, runner = int(pidfile.read_text()), json.loads(status.read_text())["pid"]
        if WIN:  # only the runner dies; the program goes on
            subprocess.run(["taskkill", "/PID", str(runner), "/F"], capture_output=True)
        else:
            os.kill(runner, 9)
        for _ in range(50):
            if not alive(runner):
                break
            time.sleep(0.1)
        then = time.time() - 60  # its last touch a minute ago: lost, but recent
        os.utime(status, (then, then))
        res = self.run_tool("wait", "app", "--seconds", "0")
        self.assertEqual(res.returncode, 4, res.stdout + res.stderr)
        self.assertIn("may still be running", res.stdout)
        self.assertIn("smaller --seconds", res.stdout)
        self.assertIn("report the check as not run", res.stdout)
        self.assertTrue(alive(program))
        res = self.start("app", "print('again')", seconds="0")
        self.assertEqual(res.returncode, 2)
        self.assertIn("may still be running", res.stderr)
        res = self.run_tool("stop", "app")
        self.assertEqual(res.returncode, 0, res.stderr)
        for _ in range(50):
            if not alive(program):
                break
            time.sleep(0.1)
        self.assertFalse(alive(program), "stop left the lost run's program running")
        self.assertEqual(self.files(), [])

    def test_list_clears_a_run_that_passed_but_was_never_waited_for(self):
        self.start("quick", "print('ok')", seconds="0")
        status = self.tmp / "quick.status"
        for _ in range(100):
            if '"exit"' in status.read_text(encoding="utf-8"):
                break
            time.sleep(0.1)
        out = self.run_tool("list").stdout
        self.assertIn("quick: finished, exit code 0", out)
        self.assertIn("never waited for", out)
        self.assertEqual(self.files(), [])

    # --- the log tail --------------------------------------------------------------------------

    def test_tail_is_the_last_lines_and_lines_sets_how_many(self):
        code = "import sys\nfor i in range(100): print('line', i)\nsys.exit(1)"
        res = self.start("build", code)
        self.assertEqual(res.returncode, 1)
        self.assertIn("line 70\n", res.stdout)
        self.assertIn("line 99\n", res.stdout)
        self.assertNotIn("line 69\n", res.stdout)
        res = self.run_tool("wait", "build", "--lines", "5")
        self.assertIn("line 95\n", res.stdout)
        self.assertNotIn("line 94\n", res.stdout)

    def test_tail_strips_colours_and_progress_redraws_and_prints_ascii(self):
        code = ("print('\\x1b[32mBUILD SUCCESS\\x1b[0m'); print('10%\\r50%\\r100%'); "
                "print('caf\\u00e9')")
        res = self.start("build", code, "--lines", "5")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)  # encoding="ascii" read it
        log = res.stdout.split("--- last", 1)[1]  # the command line itself is echoed above it
        self.assertIn("BUILD SUCCESS\n", log)
        self.assertNotIn("\x1b", log)
        self.assertIn("100%\n", log)
        self.assertNotIn("50%", log)
        self.assertIn("caf", log)

    def test_tail_of_a_long_log_starts_at_a_line_and_stays_utf8(self):
        # The tail reads the last 256 KiB; a window starting inside a two-byte character must not
        # turn the whole tail into the code page's reading.
        for prefix in (b"", b"x"):
            data = prefix + "\u00e9".encode() * 150000 + b"\nend \xc3\xa9\n"
            if data[len(data) - 262144] & 0xC0 == 0x80:  # starts on a continuation byte
                break
        source = self.dir / "big.bin"
        source.write_bytes(data)
        res = self.start("big", f"import sys; sys.stdout.buffer.write(open({str(source)!r}, "
                                "'rb').read())", "--lines", "1")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("end \\xe9\n", res.stdout)  # printed as an ASCII escape of the one character

    # --- where it runs ---------------------------------------------------------------------------

    def test_dir_runs_the_program_there_and_files_stay_in_the_callers_folder(self):
        (self.dir / "frontend").mkdir()
        res = self.start("ng", "import os; print('in', os.path.basename(os.getcwd()))",
                         "--dir", "frontend")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("in frontend", res.stdout)
        self.assertFalse((self.dir / "frontend" / ".harness-tmp").exists())

    def test_start_works_when_a_shell_dropped_the_separator(self):
        self.started.append("b")
        res = self.run_tool("start", "b", "--seconds", "30", PY, "-c", "print('no separator')")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("no separator", res.stdout)

    def test_works_from_any_folder(self):
        other = self.dir / "elsewhere"
        other.mkdir()
        res = subprocess.run([PY, str(TOOL), "start", "b", "--", PY, "-c", "print('hi')"],
                             cwd=other, capture_output=True, encoding="ascii", timeout=120)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("hi", res.stdout)
        self.assertTrue((other / ".harness-tmp").is_dir())

    def test_list_shows_each_name(self):
        self.assertIn("nothing in .harness-tmp/", self.run_tool("list").stdout)
        self.start("fails", "import sys; sys.exit(2)")
        self.start("sleeps", "import time; time.sleep(30)", seconds="0")
        out = self.run_tool("list").stdout
        self.assertIn("fails: finished, exit code 2", out)
        self.assertIn("sleeps: running", out)

    @unittest.skipUnless(WIN, "Windows program extensions")
    def test_windows_never_runs_an_extensionless_script(self):
        # ./mvnw beside mvnw.cmd: the .cmd is the program on Windows, never the shell script
        (self.dir / "mvnw").write_text("#!/bin/sh\necho unix\n", encoding="ascii")
        (self.dir / "mvnw.cmd").write_text("@echo off\r\necho windows\r\n", encoding="ascii")
        self.started.append("b")
        for program in ("./mvnw", "mvnw"):
            with self.subTest(program=program):
                res = self.run_tool("start", "b", "--", program)
                self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
                self.assertIn("windows", res.stdout)
        (self.dir / "mvnw.cmd").unlink()
        res = self.run_tool("start", "b", "--", "./mvnw")  # only the script: refused
        self.assertEqual(res.returncode, 2)
        self.assertIn("no Windows program extension", res.stderr)
        self.assertNotIn("b.status", self.files())

    @unittest.skipUnless(WIN, "Windows .cmd programs")
    def test_windows_cmd_program_runs_through_cmd_and_unsafe_arguments_are_refused(self):
        (self.dir / "build.cmd").write_text("@echo off\r\necho hello %1\r\nexit /b 5\r\n",
                                            encoding="ascii")
        self.started.append("b")
        res = self.run_tool("start", "b", "--", "build", "world")  # found as build.cmd in DIR
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("exit code 5", res.stdout)
        self.assertIn("hello world", res.stdout)
        res = self.run_tool("start", "b", "--", "build.cmd", "-Dx=a&b")
        self.assertEqual(res.returncode, 2)
        self.assertIn("cmd.exe", res.stderr)


if __name__ == "__main__":
    unittest.main()
