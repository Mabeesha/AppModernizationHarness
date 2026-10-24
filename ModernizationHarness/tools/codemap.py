#!/usr/bin/env python3
"""Write a map of a legacy codebase, so an agent can find code without searching for it.

Usage: python codemap.py SOURCE_ROOT --out FILE [--title NAME] [--exclude DIR ...]

Walks SOURCE_ROOT read-only and writes FILE, a Markdown map in three sections:

  1. Where Things Live   written by the Stage 1 agent: area -> folders/files, one note each.
                         Never generated. On a rerun everything above the generated-marker
                         line is kept as it stands; a hand-written map with no marker but a
                         "## 1. Where Things Live" heading is kept whole.
  2. Folders             generated: one row per folder - files, lines, file kinds.
  3. Files               generated: one line per text file - path, line count, and the
                         top-level names declared in it (types, functions, procedures,
                         views, tables), each with its line number.

Names are found by pattern, not by a compiler: good enough to say where to look, never
evidence of behavior - cite the code itself. Files of unknown kinds are listed by path and
line count only. Text may be UTF-8, UTF-16 with a byte-order mark, or a legacy 8-bit code
page. Binary files are skipped, and so are folders named in SKIP_DIRS (any letter case) and
each --exclude: a folder name, or a path below SOURCE_ROOT such as Web/Scripts/lib. Files
over MAX_BYTES are listed without names, and lines over MAX_LINE characters are not searched.

Never overwrites a file it did not write (one with neither the marker nor the section-1
heading). An --out inside SOURCE_ROOT is allowed only in a subfolder - the documents
location of a harness installed in the legacy repo - and that folder is left out of the
map; an --out directly in SOURCE_ROOT is refused.
Paths in the map are SOURCE_ROOT as given, joined to the path below it, with forward
slashes - so run this from the working-tree root and the map's paths open from there.
Output is ASCII; nothing is printed until the write has succeeded.

Example:
  python codemap.py ../legacy-app --out out/LEGACY_CODE_MAP_Orders.md --title Orders
"""
import argparse
import os
import re
import sys

MARKER = "<!-- codemap:generated - everything below this line is rewritten by tools/codemap.py; do not edit -->"
SECTION_1 = "## 1. Where Things Live"
SKIP_DIRS = {".git", ".svn", ".hg", ".vs", ".vscode", ".idea", ".gradle", "node_modules",
             "bin", "obj", "packages", "target", "dist", "__pycache__", ".venv", "venv",
             "testresults"}
MAX_BYTES = 2_000_000
MAX_NAMES = 40          # per file; the rest are counted, not listed
MAX_LINE = 300          # longer lines (minified or generated code) are not searched for names
SNIFF = 8192            # bytes read to tell text from binary

_MOD = r"(?:(?:public|private|protected|internal|static|virtual|override|abstract|async|sealed|" \
       r"partial|final|synchronized|extern|new|unsafe|readonly|default|native|strictfp)\s+)"
_TYPE = r"[\w.]+(?:<[\w\s,.<>?\[\]]*>)?[\[\]?]*"
_NOT_METHODS = {"if", "for", "foreach", "while", "switch", "catch", "using", "lock", "return",
                "new", "typeof", "sizeof", "nameof", "base", "this", "throw", "when", "fixed"}
_NOT_TYPES = {"return", "else", "await", "throw", "yield", "case", "goto", "new", "using",
              "var", "if", "do", "in", "is", "as", "out", "ref", "params", "operator"}

# (kind label, regex, group holding the name); patterns are tried per line, in order
_C_LIKE = [
    ("type", re.compile(r"^\s*" + _MOD + r"*(?:class|interface|enum|struct|record)\s+(\w+)"), 1),
    ("method", re.compile(r"^\s*" + _MOD + r"*(" + _TYPE + r")\s+(\w+)\s*(?:<[\w\s,]*>)?\s*\("), 2),
    ("ctor", re.compile(r"^\s*" + _MOD + r"+(\w+)\s*\("), 1),
]
_VB = [
    ("type", re.compile(r"^\s*(?:(?:Public|Private|Friend|Protected|Shared|Partial|MustInherit|"
                        r"NotInheritable)\s+)*(?:Class|Module|Interface|Structure|Enum)\s+(\w+)", re.I), 1),
    ("vb", re.compile(r"^\s*(?:(?:Public|Private|Friend|Protected|Shared|Overrides|Overridable|"
                      r"Overloads|MustOverride|NotOverridable|Async)\s+)*(?:Sub|Function)\s+(\w+)", re.I), 1),
]
_JS = [
    ("type", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:class|interface|enum)\s+(\w+)"), 1),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(\w+)"), 1),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?"
                            r"(?:function\b|\([^)]*\)\s*=>|\w+\s*=>)"), 1),
]
_PY = [
    ("type", re.compile(r"^\s*class\s+(\w+)"), 1),
    ("function", re.compile(r"^\s*(?:async\s+)?def\s+(\w+)"), 1),
]
_SQL = [
    ("sql", re.compile(r"^\s*(?:CREATE|ALTER)\s+(?:OR\s+(?:ALTER|REPLACE)\s+)?"
                       r"(PROCEDURE|PROC|FUNCTION|VIEW|TABLE|TRIGGER|PACKAGE(?:\s+BODY)?)\s+([\w\[\]\".]+)", re.I), 2),
]
PATTERNS = {
    ".cs": _C_LIKE, ".java": _C_LIKE, ".kt": _C_LIKE, ".scala": _C_LIKE, ".groovy": _C_LIKE,
    ".cpp": _C_LIKE, ".cc": _C_LIKE, ".h": _C_LIKE, ".hpp": _C_LIKE,
    ".vb": _VB, ".bas": _VB, ".cls": _VB, ".frm": _VB,
    ".js": _JS, ".jsx": _JS, ".ts": _JS, ".tsx": _JS, ".mjs": _JS,
    ".py": _PY,
    ".sql": _SQL,
}


def say(msg, stream=sys.stdout):
    stream.write(msg.encode("ascii", "backslashreplace").decode("ascii") + "\n")


def fail(msg):
    say(f"codemap: {msg}", sys.stderr)
    sys.exit(2)


def inside(path, root):
    """True when path is root or below it (False across drives)."""
    try:
        return os.path.commonpath([os.path.normcase(root), os.path.normcase(path)]) == os.path.normcase(root)
    except ValueError:
        return False


def _keep(kind, m, line):
    """False for a match that is a statement or call, not a declaration."""
    if kind not in ("method", "ctor"):
        return True
    stripped = line.rstrip()
    if stripped.endswith(";") and "=>" not in stripped:
        return False                    # a call, field or abstract member, not a body
    if stripped.endswith(","):
        return False                    # an argument list continued on the next line
    if kind == "method":
        return m.group(1) not in _NOT_TYPES and m.group(2) not in _NOT_METHODS
    return m.group(1) not in _NOT_METHODS and not line.lstrip().startswith("new ")


def names_in(lines, patterns):
    """Return [(name, line_no)] for each top-level-looking declaration."""
    found = []
    for no, line in enumerate(lines, 1):
        if len(line) > MAX_LINE:
            continue
        for kind, rx, grp in patterns:
            m = rx.match(line)
            if not m or not _keep(kind, m, line):
                continue
            name = m.group(grp)
            if kind == "sql":
                name = name.replace("[", "").replace("]", "").replace('"', "")
            found.append((name, no))
            break
    return found


def _encoding(head):
    """Text encoding from the first bytes, or None for a binary file."""
    if head.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    if b"\0" in head:
        return None
    return "utf-8-sig"


def read_file(path, size):
    """Return (line count, lines or None); (None, None) for a binary file.

    Lines are returned only for a file small enough to search; a larger one is streamed
    to count its lines and never held in memory whole."""
    with open(path, "rb") as fh:
        head = fh.read(SNIFF)
        enc = _encoding(head)
        if enc is None:
            return None, None
        if size > MAX_BYTES:
            unit = b"\n\0" if enc == "utf-16" and head.startswith(b"\xff\xfe") else b"\n"
            count, tail = head.count(unit), head[-1:]
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                count += chunk.count(unit)
                tail = chunk[-1:]
            return count + (0 if tail in (b"\n", b"\0", b"") else 1), None
        data = head + fh.read()
    if enc == "utf-16":
        text = data.decode("utf-16", errors="replace")
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("latin-1")   # an 8-bit code page; identifiers are ASCII either way
    lines = text.splitlines()
    return len(lines), lines


def scan(root, skip_names, skip_paths):
    """Return (relative path, line count, names or None) for every text file, sorted."""
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        dirnames[:] = sorted(d for d in dirnames
                             if d.lower() not in skip_names
                             and (rel_dir + d).lower() not in skip_paths)
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(full)
                count, lines = read_file(full, size)
            except OSError:
                continue
            if count is None:
                continue
            ext = os.path.splitext(fn)[1].lower()
            names = names_in(lines, PATTERNS[ext]) if lines is not None and ext in PATTERNS else None
            entries.append((rel_dir + fn, count, names))
    entries.sort(key=lambda e: e[0].lower())
    return entries


def kind_of(rel):
    ext = os.path.splitext(rel)[1].lower()
    return ext or os.path.basename(rel)


def render(prefix, entries):
    folders = {}
    for rel, count, _ in entries:
        d = os.path.dirname(rel) or "."
        f = folders.setdefault(d, [0, 0, {}])
        f[0] += 1
        f[1] += count
        k = kind_of(rel)
        f[2][k] = f[2].get(k, 0) + 1

    def show(rel):
        return f"{prefix}/{rel}" if prefix not in ("", ".") else rel

    total_names = sum(len(n) for _, _, n in entries if n)
    out = [MARKER, "",
           f"*Generated by `tools/codemap.py` from `{prefix}`: {len(entries)} files, "
           f"{sum(c for _, c, _ in entries)} lines, {total_names} names. Rerun the tool to "
           f"refresh sections 2 and 3; section 1 is kept.*", "",
           "## 2. Folders", "",
           "| Folder | Files | Lines | Kinds |", "|---|---:|---:|---|"]
    for d in sorted(folders, key=str.lower):
        files, lines, kinds = folders[d]
        top = ", ".join(f"{k} {n}" for k, n in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0]))[:6])
        out.append(f"| `{show(d) if d != '.' else prefix}` | {files} | {lines} | {top} |")
    out += ["", "## 3. Files", "",
            "*One line per file: path, line count, then each declared name with its line.*", ""]
    for rel, count, names in entries:
        line = f"- `{show(rel)}` ({count})"
        if names:
            shown = ", ".join(f"{n} :{no}" for n, no in names[:MAX_NAMES])
            more = f", +{len(names) - MAX_NAMES} more" if len(names) > MAX_NAMES else ""
            line += f" - {shown}{more}"
        out.append(line)
    return "\n".join(out) + "\n", total_names


HEADER = """# Legacy Code Map: {title}

*A navigation aid for the legacy source - where things are, not what they do. Never cite it as
evidence; cite the code it points to. Section 1 is written by the Requirements stage (Stage 1);
sections 2 and 3 are generated by `tools/codemap.py` and are rewritten each time it runs.*

""" + SECTION_1 + """

*(Stage 1 fills this in: one row per area - entry points, each feature or screen, business
rules, data access, security checks, integrations, jobs, configuration - naming its folders
or files and saying in one line what lives there.)*

"""


def kept_head(out, shown):
    """Section 1 (everything above the marker) of an existing map, or None for a new one."""
    if not os.path.exists(out):
        return None
    with open(out, encoding="utf-8-sig") as fh:
        text = fh.read()
    if MARKER in text:
        return text.split(MARKER, 1)[0]
    if re.search(r"^" + re.escape(SECTION_1), text, re.M):
        return text.rstrip("\n") + "\n\n"       # hand-written, e.g. where Python was missing
    fail(f"{shown} exists but has neither the generated-marker line nor a '{SECTION_1}' "
         f"heading, so it was not written by this tool or by Stage 1; move it or choose another --out")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title")
    ap.add_argument("--exclude", action="append", default=[], metavar="DIR")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        fail(f"source root not found: {args.root}")
    out = os.path.abspath(args.out)
    if os.path.isdir(out):
        fail(f"--out is a folder ({args.out}); give a file path such as "
             f"{os.path.join(args.out, 'LEGACY_CODE_MAP_<AppName>.md')}")

    skip_names = {d.lower() for d in SKIP_DIRS}
    skip_paths = set()
    for ex in args.exclude:
        ex = ex.replace("\\", "/").strip("/")
        (skip_paths if "/" in ex else skip_names).add(ex.lower())
    if inside(out, root):
        out_dir = os.path.dirname(out)
        if os.path.normcase(out_dir) == os.path.normcase(root):
            fail(f"--out is directly in the source root ({args.root}); the legacy source is "
                 f"read-only - write the map to the documents location instead")
        skip_paths.add(os.path.relpath(out_dir, root).replace(os.sep, "/").lower())

    kept = kept_head(out, args.out)
    prefix = args.root.replace("\\", "/").rstrip("/") or "."
    entries = scan(root, skip_names, skip_paths)
    body, total_names = render(prefix, entries)
    head = kept if kept is not None else HEADER.format(
        title=args.title or os.path.basename(root))

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(head + body)

    lines = (head + body).count("\n")
    note = "kept section 1" if kept is not None else "section 1 is a placeholder for Stage 1"
    say(f"wrote {args.out}: {len(entries)} files, {total_names} names, {lines} map lines; {note}")


if __name__ == "__main__":
    main()
