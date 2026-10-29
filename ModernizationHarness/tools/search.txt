#!/usr/bin/env python3
"""List files, and find text in files, in one plain command - no shell pipeline, no ripgrep.
For an agent whose own search tools are unavailable (GitLab Duo's need ripgrep) or whose shell
rewrites $ and | (a pwsh -Command wrapper). Reads only; never writes a file.

Usage: python search.py <command> ...

  files ROOT [GLOB ...] [--all] [--max N]
        list each file under ROOT whose path matches a GLOB (no GLOB: every file)
  text PATTERN ROOT [--include GLOB,GLOB] [--ignore-case] [--fixed] [--context N] [--max N]
       [--all]
        print each line under ROOT that PATTERN matches, as  path:line: text  (with
        --context N, N lines either side as  path-line- text, groups split by --)

ROOT is a folder, or one file, from the current directory or absolute. Paths print as ROOT
as given joined to the path below it, with forward slashes (ROOT . prints the path alone), so
run this from the working-tree root and every path opens from there.
PATTERN is a Python regular expression - save|update, \\bOrderId\\b, Save\\w*\\( - or, with
--fixed, plain text; --ignore-case ignores letter case. Pass it as ONE argument in double
quotes: "save|update". Run the tool directly, never inside a pwsh -Command wrapper: | & < >
inside a double-quoted argument are safe in cmd, PowerShell and bash. A shell may still
expand $ and %: write them [$] and [%] (a $ as the pattern's last character is fine). Match a
double quote with \\x22. A PATTERN starting with - goes right after --:
text -- "-Dskip" ROOT [options].
GLOB: * is any characters but /, ** any folders, ? one character, [abc] one of them; a GLOB
with no / matches the file name at any depth (*.ts), one with / the path below ROOT
(src/**/*.cs); letter case is ignored. --include takes GLOBs separated by commas, or repeated.

Skipped below ROOT, unless --all: folders named in SKIP_DIRS (any letter case), and what the
.gitignore files say - those in ROOT and the folders below it, and in the folders above ROOT up
to the one that holds .git. Of .gitignore, supported: blank and # lines, * ? [...] **, a
leading / (relative to that .gitignore's folder), a / inside (the same), a trailing / (folders
only). Not read: ! lines (a re-included path stays skipped - use --all), .git/info/exclude, and
global excludes. A ROOT inside a skipped folder is searched: skipping starts below ROOT.
text also skips binary files (a NUL byte in the first 8 KB, with no UTF-16 byte-order mark) and
files over MAX_BYTES, and counts them. Text may be UTF-8 (with or without a byte-order mark),
UTF-16 with a byte-order mark, or else is read as Windows-1252.

Output stops at --max N results (default 200: matches for text, files for files) and says
when more exist, and stops after TIME_LIMIT (90) seconds - inside a 120 s command limit - and
says so: narrow ROOT, GLOB or --include. A line over MAX_SHOWN characters is cut, around its
first match. Linked folders (symbolic links, Windows junctions) are never followed. The last
line sums up: results, files searched, what was skipped. Output is ASCII, a line at a time
(other characters as backslash escapes, control characters as \\x01 - search for them with
\\xe9 or \\u00e9). Exit status: 0 found (also when stopped early), 1 nothing found (read the
last lines: a search stopped by the time limit says so), 2 a malformed command (it says why;
nothing searched).

Examples:
  python search.py files src "*.component.ts"
  python search.py text "OrderService|OrderRepository" src --include "*.ts,*.java"
  python search.py text "TODO" . --ignore-case --context 2
"""
import argparse
import os
import re
import stat
import sys
import time

SKIP_DIRS = {"node_modules", "target", "bin", "obj", "dist", "build", ".git", ".angular",
             "coverage", ".harness-tmp"}
SKIP_LOWER = {d.lower() for d in SKIP_DIRS}
DEFAULT_MAX = 200
MAX_BYTES = 10_000_000
MAX_SHOWN = 300
SNIFF = 8192
WIN = os.name == "nt"
TIME_LIMIT = float(os.environ.get("SEARCH_PY_SECONDS", "90"))  # inside a 120 s command limit
LINK_TAGS = {0xA0000003, 0xA000000C}  # Windows junction (mount point) and symbolic link
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
DASHED = "<pattern after -->"  # stands in for a PATTERN given after --


class Malformed(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Malformed(f"{message} (python search.py with no command prints the syntax)")


def die(msg):
    sys.stderr.write(f"search.py: {msg}\n")
    sys.exit(2)


def glob_regex(glob, escapes):
    """A regex for a glob: * within a folder, ** across folders, ? and [...]; with escapes, a
    backslash quotes the next character (.gitignore), else it is a folder separator."""
    out, i, n = [], 0, len(glob)
    while i < n:
        c = glob[i]
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
            continue
        if glob.startswith("**", i):
            out.append(".*")
            i += 2
            continue
        if c == "*":
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "[":
            j = glob.find("]", i + 2)
            if j == -1:
                out.append(re.escape(c))
            else:
                body = glob[i + 1:j]
                neg = body[:1] in ("!", "^")
                body = (body[1:] if neg else body).replace("\\", "\\\\").replace("[", "\\[")
                out.append("[" + ("^" if neg else "") + body + "]")
                i = j + 1
                continue
        elif c == "\\" and escapes and i + 1 < n:
            out.append(re.escape(glob[i + 1]))
            i += 2
            continue
        else:
            out.append(re.escape(c))
        i += 1
    return "".join(out)


def compile_globs(globs):
    """[(regex, matches the whole path?)] for user GLOBs: \\ is a folder separator here."""
    out = []
    for g in globs:
        g = g.strip().replace("\\", "/")
        while g.startswith("./"):
            g = g[2:]
        g = g.lstrip("/")
        if not g:
            continue
        out.append((re.compile(glob_regex(g, False), re.I), "/" in g))
    return out


def glob_hit(globs, rel):
    if not globs:
        return True
    name = rel.rsplit("/", 1)[-1]
    return any(rx.fullmatch(rel if whole else name) for rx, whole in globs)


def norm(path):
    return os.path.abspath(path).replace("\\", "/").rstrip("/")


def read_ignore(folder):
    """The rules of folder/.gitignore: [(folder, regex, folders only, relative to folder)]."""
    path = os.path.join(folder, ".gitignore")
    try:
        with open(path, "rb") as fh:
            text = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    base, rules = norm(folder), []
    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.lstrip("﻿")
        if not line.endswith("\\ "):
            line = line.rstrip(" \t")
        if not line or line.startswith("#") or line.startswith("!"):
            continue  # ! (re-include) is not supported: documented
        if line.startswith(("\\#", "\\!")):
            line = line[1:]
        dir_only = line.endswith("/")
        line = line.rstrip("/")
        if not line:
            continue
        anchored = "/" in line
        line = line.lstrip("/")
        try:
            rx = re.compile(glob_regex(line, True), re.I if WIN else 0)
        except re.error:
            continue  # a pattern this reader cannot express is left out
        rules.append((base, rx, dir_only, anchored))
    return rules


def ignored(rules, path, is_dir):
    name = path.rsplit("/", 1)[-1]
    for base, rx, dir_only, anchored in rules:
        if dir_only and not is_dir:
            continue
        if not path.startswith(base + "/"):
            continue
        if rx.fullmatch(path[len(base) + 1:] if anchored else name):
            return True
    return False


def outer_rules(root):
    """The .gitignore rules of the folders above root, up to the one holding .git; none when
    no folder above holds .git."""
    chain, here = [], os.path.abspath(root)
    while not os.path.exists(os.path.join(here, ".git")):
        up = os.path.dirname(here)
        if up == here:
            return []
        here = up
        chain.append(here)
    rules = []
    for folder in reversed(chain):
        rules += read_ignore(folder)
    return rules


def walk(root, skip, counts):
    """Yield (path below root with / separators, full path) for every file, sorted, pruning
    skipped folders (counted in counts["folders"])."""
    root_n = norm(root)
    rules_of = {root_n: (outer_rules(root) + read_ignore(root)) if skip else []}
    seen = {folder_id(root)}
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        here = norm(dirpath)
        rules = rules_of.pop(here, [])
        rel_dir = here[len(root_n) + 1:] + "/" if here != root_n else ""
        kept = []
        for d in sorted(dirnames, key=str.lower):
            full = here + "/" + d
            if skip and (d.lower() in SKIP_LOWER or ignored(rules, full, True)):
                counts["folders"] += 1
                continue
            ident = folder_id(os.path.join(dirpath, d))
            if ident is None or ident in seen:  # a linked folder, or one reached twice
                counts["links"] += 1
                continue
            seen.add(ident)
            kept.append(d)
            if skip:
                rules_of[full] = rules + read_ignore(full)
        dirnames[:] = kept
        for f in sorted(filenames, key=str.lower):
            full = here + "/" + f
            if skip and ignored(rules, full, False):
                counts["ignored"] += 1
                continue
            yield rel_dir + f, os.path.join(dirpath, f)


def folder_id(path):
    """(device, inode) of a real folder; None for a symbolic link or Windows junction, which
    are never followed (a junction to a parent would loop: Python 3.11's walk follows it)."""
    try:
        st = os.lstat(path)
    except OSError:
        return None
    if stat.S_ISLNK(st.st_mode) or getattr(st, "st_reparse_tag", 0) in LINK_TAGS:
        return None
    return (st.st_dev, st.st_ino) if st.st_ino else (st.st_dev, norm(path).lower())


def targets(root, skip, counts):
    if os.path.isfile(root):
        return [("", root)]
    return walk(root, skip, counts)


def read_text(path):
    """The file's text, or None for a binary file."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace")
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    if b"\0" in data[:SNIFF]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def split_lines(text):
    """Split on line breaks only, so line numbers match an editor's."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def shown_path(prefix, rel):
    if not rel:
        return prefix
    return rel if prefix in ("", ".") else f"{prefix}/{rel}"


def cut(line, match):
    line = line.rstrip()
    if len(line) > MAX_SHOWN:
        start = max(0, match.start() - 100) if match else 0
        line = ("... " if start else "") + line[start:start + MAX_SHOWN] + " ..."
    return CONTROL.sub(lambda m: f"\\x{ord(m.group()):02x}", line)


def new_counts():
    return {"folders": 0, "ignored": 0, "binary": 0, "big": 0, "unreadable": 0, "links": 0}


def out_of_time(started):
    return time.monotonic() - started >= TIME_LIMIT


def timed_out_note():
    print(f"-- stopped after {TIME_LIMIT:g} s - narrow ROOT, GLOB or --include; the results "
          "above are only part of it")


def skipped_note(counts):
    parts = []
    if counts["folders"]:
        parts.append(f"{counts['folders']} folder(s) by name or .gitignore")
    if counts["ignored"]:
        parts.append(f"{counts['ignored']} file(s) by .gitignore")
    if counts["binary"]:
        parts.append(f"{counts['binary']} binary file(s)")
    if counts["big"]:
        parts.append(f"{counts['big']} file(s) over {MAX_BYTES // 1_000_000} MB")
    if counts["unreadable"]:
        parts.append(f"{counts['unreadable']} unreadable file(s)")
    if counts["links"]:
        parts.append(f"{counts['links']} linked folder(s), never followed")
    if not parts:
        return ""
    more = " - --all searches the skipped folders" if counts["folders"] or counts["ignored"] else ""
    return "; skipped " + ", ".join(parts) + more


def cmd_files(args, root, prefix):
    globs = compile_globs(args.globs)
    counts = new_counts()
    found, more, late, started = 0, False, False, time.monotonic()
    for rel, _ in targets(root, not args.all, counts):
        if out_of_time(started):
            late = True
            break
        if not glob_hit(globs, rel or os.path.basename(root)):
            continue
        if found == args.max:
            more = True
            break
        print(shown_path(prefix, rel))
        found += 1
    if more:
        print(f"-- stopped at --max {args.max} files; there are more: narrow ROOT or GLOB, or "
              "raise --max")
    if late:
        timed_out_note()
    print(f"-- {found} file(s){skipped_note(counts)}")
    return 0 if found else 1


def cmd_text(args, root, prefix):
    try:
        rx = re.compile(re.escape(args.pattern) if args.fixed else args.pattern,
                        re.I if args.ignore_case else 0)
    except re.error as e:
        die(f"PATTERN is not a valid regular expression ({e}); add --fixed to search for it "
            "as plain text")
    globs = compile_globs([g for value in args.include for g in value.split(",")])
    counts = new_counts()
    found, files, searched, more, printed_any = 0, 0, 0, False, False
    late, started = False, time.monotonic()
    for rel, full in targets(root, not args.all, counts):
        if out_of_time(started):
            late = True
            break
        if not glob_hit(globs, rel or os.path.basename(root)):
            continue
        try:
            if os.path.getsize(full) > MAX_BYTES:
                counts["big"] += 1
                continue
            text = read_text(full)
        except OSError:
            counts["unreadable"] += 1
            continue
        if text is None:
            counts["binary"] += 1
            continue
        searched += 1
        lines = split_lines(text)
        hits = []
        for no, line in enumerate(lines):
            m = rx.search(line)
            if m:
                if found + len(hits) == args.max:
                    more = True
                    break
                hits.append((no, m))
        if hits:
            files += 1
            found += len(hits)
            path = shown_path(prefix, rel)
            if args.context:
                printed_any = print_context(path, lines, hits, args.context, printed_any)
            else:
                for no, m in hits:
                    print(f"{path}:{no + 1}: {cut(lines[no], m)}")
        if more:
            break
    if more:
        print(f"-- stopped at --max {args.max} matches; there are more: narrow PATTERN, ROOT or "
              "--include, or raise --max")
    if late:
        timed_out_note()
    print(f"-- {found} match(es) in {files} file(s); {searched} file(s) searched"
          f"{skipped_note(counts)}")
    return 0 if found else 1


def print_context(path, lines, hits, n, printed_any):
    """Print hits with n lines either side, overlapping windows merged; groups split by --."""
    groups, matched = [], {no: m for no, m in hits}
    for no, _ in hits:
        lo, hi = max(0, no - n), min(len(lines) - 1, no + n)
        if groups and lo <= groups[-1][1] + 1:
            groups[-1][1] = max(groups[-1][1], hi)
        else:
            groups.append([lo, hi])
    for lo, hi in groups:
        if printed_any:
            print("--")
        printed_any = True
        for no in range(lo, hi + 1):
            if no in matched:
                print(f"{path}:{no + 1}: {cut(lines[no], matched[no])}")
            else:
                print(f"{path}-{no + 1}- {cut(lines[no], None)}")
    return printed_any


def positive(value):
    if not value.isdigit() or int(value) < 1:
        raise argparse.ArgumentTypeError(f"takes a whole number of 1 or more, got {value!r}")
    return int(value)


def count(value):
    if not value.isdigit():
        raise argparse.ArgumentTypeError(f"takes a whole number, got {value!r}")
    return int(value)


def parser():
    ap = Parser(prog="search.py", add_help=False, allow_abbrev=False)
    sub = ap.add_subparsers(dest="command", parser_class=Parser)
    f = sub.add_parser("files", add_help=False, allow_abbrev=False)
    f.add_argument("root")
    f.add_argument("globs", nargs="*")
    t = sub.add_parser("text", add_help=False, allow_abbrev=False)
    t.add_argument("pattern")
    t.add_argument("root")
    t.add_argument("--include", action="append", default=[])
    t.add_argument("--ignore-case", action="store_true")
    t.add_argument("--fixed", action="store_true")
    t.add_argument("--context", type=count, default=0)
    for p in (f, t):
        p.add_argument("--all", action="store_true")
        p.add_argument("--max", type=positive, default=DEFAULT_MAX)
    return ap


def main(argv):
    for stream in (sys.stdout, sys.stderr):  # ASCII survives any console encoding; each line
        # goes out at once, so a command cut off by the platform still shows what it found
        stream.reconfigure(encoding="ascii", errors="backslashreplace", line_buffering=True)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0 if argv else 2)
    if argv[0] not in ("files", "text"):
        die(f"unknown command {argv[0]!r}: files or text (python search.py with no command "
            "prints the syntax)")
    dashed = None
    if argv[0] == "text" and "--" in argv[1:]:  # PATTERN starts with -: it follows --
        i = argv.index("--", 1)
        if i + 1 == len(argv):
            die("-- needs PATTERN after it")
        dashed, argv = argv[i + 1], argv[:i] + [DASHED] + argv[i + 2:]
    try:
        args = parser().parse_args(argv)
    except Malformed as e:
        die(str(e))
    if dashed is not None:
        if args.pattern != DASHED:
            die("-- goes right before PATTERN: text -- PATTERN ROOT [options]")
        args.pattern = dashed
    root = args.root
    if not os.path.exists(root):
        die(f"ROOT not found: {root} (paths are from the current directory, {os.getcwd()})")
    prefix = root.replace("\\", "/").rstrip("/") or "/"
    sys.exit(cmd_files(args, root, prefix) if args.command == "files"
             else cmd_text(args, root, prefix))


if __name__ == "__main__":
    main(sys.argv[1:])
