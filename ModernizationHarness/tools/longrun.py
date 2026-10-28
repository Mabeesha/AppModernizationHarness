#!/usr/bin/env python3
"""Run a command that may outlast the agent platform's command time limit - a full build, a
test suite with coverage - in the background, and wait for it in steps that each end inside it.

Usage: python longrun.py <command> ...

  start NAME [--dir DIR] [--seconds N] [--lines L] -- PROGRAM [ARG ...]
                   start PROGRAM in the background, stdout and stderr to
                   .harness-tmp/NAME.out.txt, then wait for it as wait does (--seconds 0:
                   return at once)
  wait NAME [--seconds N] [--lines L]
                   wait up to N seconds (default 100) for NAME to end; print running or
                   finished, the exit code, the time so far and the last L log lines (default 30)
  stop NAME [--lines L]
                   end NAME and every process it started (a server started for a walk, a
                   build to abandon) - a lost one's program too; print the last L log lines,
                   then delete its files (a lost run whose program is gone: just the files)
  list             every NAME with files in .harness-tmp/, and its state; one that finished
                   with exit code 0 but was never waited for has its files removed

Exit status of start and wait:
  0  finished, exit code 0: NAME.out.txt and NAME.status are deleted
  1  finished with another exit code: the log is kept and named - read it with your file
     tool, or wait NAME --lines 200 to reprint more of it; the next start NAME replaces it
  3  still running after N seconds: run wait NAME again
  4  lost: its runner ended without recording an exit code. The program may still be running
     (stop NAME ends it). If the start or wait call was itself cut off by the time limit, start
     again with a smaller --seconds (25); otherwise it was killed or the machine slept, and
     right after start it means the platform ends background programs - run the command
     directly, and if even that cannot finish inside the limit, report the check as not run
  2  a malformed command or a refusal (NAME already running, PROGRAM not found or not a
     Windows program): nothing started
stop and list exit 0, or 2 when malformed.

Options come before --; everything after it is PROGRAM's (a shell that drops the -- is fine).
NAME is letters, digits, '.', '_' and '-' (build, test-frontend). Run from the working-tree root,
like the other tools: the files go in .harness-tmp/ under the current directory. PROGRAM runs
in DIR (default: the current directory), directly - no shell, so no &&, |, > or shell quoting:
one program and its arguments, each passed as is. A name without a folder is found on PATH (on
Windows also in DIR); ./mvnw is relative to DIR. On Windows a program is the file with a PATHEXT
extension (mvn -> mvn.cmd, ./mvnw -> mvnw.cmd), never the extension-less shell script beside
it; a .cmd or .bat runs through cmd.exe, which would misread & | < > ^ % or a double quote in an
argument, so those are refused. Two NAMEs may run side by side. stdin is empty: a program
that asks for input or watches for changes never ends - pass its run-once flag (ng test
--watch=false).
Keep N inside the platform's command time limit with room to spare: the default 100 fits a
120 s limit; a 30 s limit needs --seconds 25. Each wait is one call - wait the full N, never
poll faster. Output is ASCII.
"""
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import threading
import time

TMP_DIR = ".harness-tmp"
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
DEFAULT_SECONDS = 100
DEFAULT_LINES = 30
BEAT = 2.0    # a running NAME's runner touches NAME.status this often
STALE = 30.0  # untouched this long, with no exit code: the runner is gone
RECENT = 600.0  # a lost run's program pid is trusted this long after the runner's last touch
LOG, STATUS = ".out.txt", ".status"  # not .log: many projects' .gitignore has *.log
WIN = os.name == "nt"
CMD_UNSAFE = set('&|<>^%"\r\n')  # cmd.exe would act on these in a .cmd/.bat argument
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
# Windows process flags
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_NO_WINDOW = 0x08000000


def die(msg):
    """A malformed command or a refusal: nothing was started."""
    sys.stderr.write(f"longrun.py: {msg}\n")
    sys.exit(2)


def files(name, tmp=TMP_DIR):
    base = os.path.join(tmp, name)
    return base + LOG, base + STATUS


def dur(seconds):
    s = max(0, int(round(seconds)))
    return f"{s // 60}m {s % 60:02d}s" if s >= 60 else f"{s}s"


def shown(argv):
    return " ".join([os.path.basename(argv[0])] + list(argv[1:]))


def retry(action, tries=50):
    """Windows refuses to replace or delete a file another process has open for a moment."""
    for n in range(tries):
        try:
            return action()
        except PermissionError:
            if n == tries - 1:
                raise
            time.sleep(0.1)


def write_status(path, status):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f)
    retry(lambda: os.replace(tmp, path))


def read_status(path):
    """(status, seconds since its runner last touched it), or (None, None) when there is none."""
    for _ in range(40):
        try:
            with open(path, "rb") as f:
                status = json.loads(f.read())
            return status, time.time() - os.path.getmtime(path)
        except FileNotFoundError:
            return None, None
        except (OSError, ValueError):
            time.sleep(0.05)  # caught mid-replace; read again
    die(f"{path} cannot be read; delete it and start again")


def state_of(name):
    status, age = read_status(files(name)[1])
    if status is None:
        return "none", None, None
    if "exit" in status:
        return "finished", status, age
    return ("lost" if age > STALE else "running"), status, age


def remove(paths):
    gone, kept = [], []
    for p in paths:
        try:
            retry(lambda p=p: os.remove(p), tries=20)
            gone.append(p)
        except FileNotFoundError:
            pass
        except OSError:
            kept.append(p)
    return gone, kept


def tail(path, count):
    """The last count lines of the log as plain text: colours stripped, progress redraws folded."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            start = max(0, f.tell() - 262144)
            f.seek(start)
            raw = f.read()
    except OSError:
        return []
    if start:  # the window may begin inside a line, or inside a character: start at a line
        raw = raw.split(b"\n", 1)[-1]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:  # not UTF-8 at all, e.g. an older JVM writing the code page
        text = raw.decode(locale.getpreferredencoding(False) or "latin-1", errors="replace")
    lines = ANSI_RE.sub("", text).replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    lines = [ln.rstrip("\r").rsplit("\r", 1)[-1] for ln in lines[-count:]] if count else []
    return [ln if len(ln) <= 400 else ln[:400] + " ..." for ln in lines]


def print_tail(log, count, what):
    lines = tail(log, count)
    if lines:
        print(f"--- {what} {len(lines)} lines of {log} ---")
        for ln in lines:
            print(ln)
        print("--- end ---")
    elif count:
        print(f"(nothing in {log} yet)")


def report(name, state, status, age, lines, waited):
    """Print where NAME stands; return the exit status start and wait share."""
    log = files(name)[0]
    cmd = shown(status.get("command", ["?"]))
    since = status.get("started", status.get("requested", time.time()))
    if state == "running":
        print(f"{name}: still running after {dur(time.time() - since)} ({cmd}); waited "
              f"{dur(waited)}")
        print_tail(log, lines, "last")
        print(f"run `longrun.py wait {name}` again")
        return 3
    if state == "lost":
        print(f"{name}: LOST - its background runner ended without recording an exit code, "
              f"{dur(age)} ago ({cmd})")
        if program_running(status, age):
            print(f"- the program may still be running: `longrun.py stop {name}` ends it")
        print("- if the start or wait call before this was itself cut off by the time limit, "
              "start again with a smaller --seconds (25)")
        print("- otherwise it was killed, or the machine slept; right after start, the platform "
              "ends background programs: run the command directly and say so in the report, "
              "and if even that cannot finish inside the limit, report the check as not run "
              "and ask the developer to run it")
        print_tail(log, lines, "last")
        print(f"log kept: {log}; `longrun.py stop {name}` clears it")
        return 4
    took = dur(status.get("ended", time.time()) - since)
    code = status.get("exit")
    if code == 0:
        print(f"{name}: finished, exit code 0, after {took} ({cmd})")
        print_tail(log, lines, "last")
        clean_up(name)
        return 0
    print(f"{name}: FAILED, exit code {code}, after {took} ({cmd})")
    print_tail(log, lines, "last")
    print(f"full log kept: {log} - read it with your file tool, or `longrun.py wait {name} "
          f"--lines 200` reprints more; the next start {name} replaces it")
    return 1


def clean_up(name):
    log, stat = files(name)
    gone, kept = remove([log, stat, stat + ".tmp"])
    print(f"removed {' and '.join(gone) or 'nothing'}"
          + (f"; could not remove {', '.join(kept)} (still open in another program?) - "
             "delete it later" if kept else ""))


def wait(name, seconds, lines):
    start = time.monotonic()
    stale_seen = None
    while True:
        state, status, age = state_of(name)
        if state == "none":
            die(f"nothing started under {name} (or it already finished with exit code 0 and "
                f"its files were removed); `longrun.py list` shows what there is")
        now = time.monotonic()
        if state == "lost":  # a moment's grace: the machine may have just woken up
            stale_seen = now if stale_seen is None else stale_seen
            if now - stale_seen >= 2.5 * BEAT:
                break
        else:
            stale_seen = None
            if state == "finished" or now - start >= seconds:
                break
        time.sleep(min(0.5, max(0.05, seconds - (now - start))))
    return report(name, state, status, age, lines, time.monotonic() - start)


def windows_program(path):
    """path with each PATHEXT extension added, then path itself only if it already has one -
    never an extension-less file (./mvnw, node_modules/.bin/ng are shell scripts there)."""
    exts = [e for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";") if e]
    for ext in exts:
        if os.path.isfile(path + ext):
            return path + ext
    if os.path.isfile(path) and os.path.splitext(path)[1].lower() in {e.lower() for e in exts}:
        return path
    return None


def resolve(program, workdir):
    """(full path, None), or (None, why it is refused)."""
    if os.path.dirname(program):
        places = [program if os.path.isabs(program) else os.path.join(workdir, program)]
    elif WIN:  # as cmd.exe does: PATH, and the folder it runs in
        places = [os.path.join(d, program) for d in os.environ.get("PATH", "").split(os.pathsep)
                  if d] + [os.path.join(workdir, program)]
    else:
        found = shutil.which(program)
        return (os.path.abspath(found), None) if found else (None, "not found on PATH")
    if not WIN:
        found = shutil.which(places[0])
        return (os.path.abspath(found), None) if found else (None, f"not found ({places[0]})")
    for place in places:
        found = windows_program(place)
        if found:
            return os.path.abspath(found), None
    plain = [pl for pl in places if os.path.isfile(pl)]
    if plain:
        return None, (f"{plain[0]} has no Windows program extension (it is likely a shell "
                      "script); name its .cmd or .exe, e.g. mvnw.cmd")
    return None, ("not found " + (f"({places[0]})" if os.path.dirname(program)
                                  else f"on PATH or in {workdir}"))


def run_spec(program, args):
    """What the runner hands to the operating system: a list, or for a .cmd on Windows one
    cmd.exe line (/s keeps the quoting exactly as written)."""
    if WIN and program.lower().endswith((".cmd", ".bat")):
        bad = sorted({c for a in args for c in a if c in CMD_UNSAFE})
        if bad:
            die(f"refused: {os.path.basename(program)} runs through cmd.exe, which would misread "
                f"{' '.join(repr(c) for c in bad)} in an argument; nothing started")
        comspec = os.environ.get("COMSPEC") or "cmd.exe"
        return f'"{comspec}" /d /s /c "{subprocess.list2cmdline([program, *args])}"'
    return [program, *args]


def take(args, options):
    """Pull --option VALUE pairs (all integers but --dir) off the front of args."""
    found = {}
    while args and args[0] in options:
        if len(args) < 2:
            die(f"{args[0]} needs a value")
        key, value = args[0], args[1]
        if key != "--dir":
            if not value.isdigit():
                die(f"{key} takes a whole number, got {value!r}")
            value = int(value)
        found[key], args = value, args[2:]
    return found, args


def check_name(args, command):
    if not args or not NAME_RE.fullmatch(args[0]):
        die(f"{command} needs a NAME of letters, digits, '.', '_' and '-' first, got "
            f"{args[0] if args else 'nothing'!r}")
    return args[0], args[1:]


def cmd_start(args):
    name, args = check_name(args, "start")
    opts, args = take(args, ("--dir", "--seconds", "--lines"))
    argv = args[1:] if args[:1] == ["--"] else args  # a shell that drops the -- still works
    if not argv or argv[0].startswith("-"):
        die("start needs `-- PROGRAM [ARG ...]` after NAME and its options, got "
            f"{argv[0] if argv else 'nothing'!r}")
    state, status, age = state_of(name)
    if state == "running":
        die(f"refused: {name} is already running ({shown(status.get('command', ['?']))}); wait "
            "for it, or stop it")
    if state == "lost" and program_running(status, age):
        die(f"refused: {name}'s runner was lost but its program may still be running "
            f"({shown(status.get('command', ['?']))}); `longrun.py stop {name}` ends it")
    workdir = os.path.abspath(opts.get("--dir", "."))
    if not os.path.isdir(workdir):
        die(f"--dir {opts['--dir']} is not a folder")
    program, why = resolve(argv[0], workdir)
    if not program:
        die(f"{argv[0]}: {why}; nothing started")
    spec = run_spec(program, argv[1:])
    os.makedirs(TMP_DIR, exist_ok=True)
    log, stat = files(name)
    _, kept = remove([log, stat, stat + ".tmp"])
    if kept:
        die(f"cannot replace {', '.join(kept)} - open in another program (an earlier {name} "
            f"still running? `longrun.py stop {name}`)? Close it and rerun")
    write_status(stat, {"command": argv, "run": spec, "dir": workdir, "requested": time.time()})
    try:  # through a go-between that exits at once, so the runner is not in this call's tree
        proc = detach(lambda _: [sys.executable, os.path.abspath(__file__), "_spawn",
                                 os.path.abspath(stat)], workdir)
        proc.wait(timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        remove([stat])
        die(f"could not start the background runner: {e}; nothing started")
    if proc.returncode:
        remove([stat])
        die(f"could not start the background runner (exit {proc.returncode}); nothing started")
    print(f"{name}: started {shown(argv)} in {workdir}")
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        status, _ = read_status(stat)
        if status is None or "pid" in status or "exit" in status:
            break
        time.sleep(0.05)
    else:
        print("note: the background runner has not reported within 15 s; it may still start "
              f"(wait {name} says, or reports it lost after 30 s)")
    if status and status.get("job") == "stayed":
        print("note: could not leave the command tool's job; if the platform ends the job when "
              "a command returns, the next wait reports lost")
    return wait(name, opts.get("--seconds", DEFAULT_SECONDS), opts.get("--lines", DEFAULT_LINES))


def detach(command, cwd):
    """The process command(left) starts with no console, no handle of ours, and on Unix in a
    new session; left says whether it got out of the command tool's job."""
    quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL, close_fds=True, cwd=cwd)
    if not WIN:
        return subprocess.Popen(command(True), start_new_session=True, **quiet)
    flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    try:  # leave the command tool's job, so closing it cannot end the build
        return subprocess.Popen(command(True), creationflags=flags | CREATE_BREAKAWAY_FROM_JOB,
                                **quiet)
    except OSError:  # the job forbids it
        return subprocess.Popen(command(False), creationflags=flags, **quiet)


def cmd_spawn(args):
    """The go-between start launches (not for direct use): start the runner, then exit."""
    runner = [sys.executable, os.path.abspath(__file__), "_run", args[0]]
    try:  # the runner is told whether it left the job, and records it for start
        detach(lambda left: runner + ["left" if left else "stayed"], os.path.dirname(args[0]))
    except OSError:
        return 1
    return 0


def cmd_wait(args):
    name, args = check_name(args, "wait")
    opts, args = take(args, ("--seconds", "--lines"))
    if args:
        die(f"wait takes NAME [--seconds N] [--lines L], got {args!r}")
    return wait(name, opts.get("--seconds", DEFAULT_SECONDS), opts.get("--lines", DEFAULT_LINES))


def win_process(pid):
    """(alive, creation time in epoch seconds or None) for a Windows process id."""
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    k.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    k.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    k.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False, None
    try:
        code = wintypes.DWORD()
        if not k.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
            return False, None  # 259: STILL_ACTIVE
        times = [wintypes.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
            return True, None
        ticks = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        return True, ticks / 1e7 - 11644473600  # 100 ns since 1601 -> epoch seconds
    finally:
        k.CloseHandle(handle)


def program_running(status, age):
    """Whether a lost run's program still runs - only while its pid cannot have been reused:
    the runner touched the status within RECENT seconds, and on Windows the process with that
    id was created after the run started."""
    pid = status.get("program_pid")
    if not pid or age is None or age > RECENT:
        return False
    if WIN:
        alive, created = win_process(pid)
        return alive and (created is None or created >= status.get("started", 0) - 5)
    try:
        os.kill(pid, 0)
    except OSError:  # gone, or not ours
        return False
    return True


def kill_tree(pid):
    if WIN:
        taskkill = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32",
                                "taskkill.exe")
        res = subprocess.run([taskkill if os.path.exists(taskkill) else "taskkill", "/PID",
                              str(pid), "/T", "/F"], capture_output=True)
        if res.returncode not in (0, 128):  # 128: already gone
            print(f"note: taskkill exit {res.returncode}: "
                  f"{res.stdout.decode(errors='replace').strip()}")
        return
    import signal
    for sig, grace in ((signal.SIGTERM, 5.0), (signal.SIGKILL, 2.0)):
        try:
            os.killpg(pid, sig)  # the runner leads its own session: its group is everything
        except ProcessLookupError:
            return
        end = time.monotonic() + grace
        while time.monotonic() < end:
            try:
                os.killpg(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.1)


def cmd_stop(args):
    name, args = check_name(args, "stop")
    opts, args = take(args, ("--lines",))
    if args:
        die(f"stop takes NAME [--lines L], got {args!r}")
    state, status, age = state_of(name)
    if state == "lost" and program_running(status, age):
        if WIN:
            kill_tree(status["program_pid"])
        else:  # the runner led the program's process group, which outlives it
            kill_tree(status.get("pid", status["program_pid"]))
    elif state == "lost":  # its program is gone too: only the files are left
        print(f"{name}: lost, and its program is no longer running - nothing to stop "
              f"({shown(status.get('command', ['?']))})")
        print_tail(files(name)[0], opts.get("--lines", DEFAULT_LINES), "last")
        clean_up(name)
        return 0
    elif state != "running":
        print(f"{name}: not running ({'nothing started' if state == 'none' else state}); "
              "nothing to stop")
        return 0
    elif "pid" in status:
        kill_tree(status["pid"])
    since = status.get("started", status.get("requested", time.time()))
    print(f"{name}: stopped after {dur(time.time() - since)} "
          f"({shown(status.get('command', ['?']))})")
    print_tail(files(name)[0], opts.get("--lines", DEFAULT_LINES), "last")
    clean_up(name)
    return 0


def cmd_list(args):
    if args:
        die("list takes no arguments")
    names = sorted(f[:-len(STATUS)] for f in (os.listdir(TMP_DIR) if os.path.isdir(TMP_DIR)
                                                else []) if f.endswith(STATUS))
    if not names:
        print(f"nothing in {TMP_DIR}/")
    for name in names:
        state, status, age = state_of(name)
        if state == "none":
            continue
        cmd = shown(status.get("command", ["?"]))
        if state == "finished" and status["exit"] == 0:
            print(f"{name}: finished, exit code 0 ({cmd}), never waited for")
            clean_up(name)
            continue
        if state == "finished":
            state = f"finished, exit code {status['exit']}; log kept: {files(name)[0]}"
        elif state == "lost" and program_running(status, age):
            state = f"lost - its program may still be running: `longrun.py stop {name}`"
        print(f"{name}: {state} ({cmd})")
    return 0


def cmd_run(args):
    """The background runner start launches (not for direct use): run the program, keep its
    status file fresh, then record the exit code."""
    stat = args[0]
    status, _ = read_status(stat)
    if status is None:  # stopped before it got here
        return 0
    log = stat[:-len(STATUS)] + LOG
    if args[1:] == ["stayed"]:
        status["job"] = "stayed"
    lock, done = threading.Lock(), threading.Event()

    def beat():
        while not done.wait(BEAT):
            with lock:
                try:
                    os.utime(stat)
                except OSError:
                    pass

    with open(log, "wb") as out:
        status.update(pid=os.getpid(), started=time.time())
        write_status(stat, status)
        threading.Thread(target=beat, daemon=True).start()
        try:
            proc = subprocess.Popen(status["run"], stdin=subprocess.DEVNULL, stdout=out,
                                    stderr=subprocess.STDOUT, cwd=status["dir"],
                                    creationflags=CREATE_NO_WINDOW if WIN else 0)
            with lock:  # so stop can end the program even if this runner is lost
                status["program_pid"] = proc.pid
                write_status(stat, status)
            code = proc.wait()
        except OSError as e:
            out.write(f"longrun.py: could not run {status['command'][0]}: {e}\n".encode())
            code = 127
    done.set()
    with lock:
        status.update(exit=code, ended=time.time())
        write_status(stat, status)
    return 0


COMMANDS = {"start": cmd_start, "wait": cmd_wait, "stop": cmd_stop, "list": cmd_list,
            "_spawn": cmd_spawn, "_run": cmd_run}


def main(argv):
    for stream in (sys.stdout, sys.stderr):  # ASCII survives any console encoding
        stream.reconfigure(encoding="ascii", errors="backslashreplace")
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[argv[0]](argv[1:]))


if __name__ == "__main__":
    main(sys.argv[1:])
