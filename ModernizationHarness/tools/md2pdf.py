#!/usr/bin/env python3
"""Print Markdown to PDF through the Chrome or Edge already installed - offline.

Usage: python md2pdf.py FILE.md ... [--out DIR] [--check] [--force] [--browser PATH]
                        [--paper A4|letter] [--css FILE]

  FILE.md ...       the files to print, named one by one (no wildcard is expanded)
  --out DIR         where FILE.pdf and FILE.html go; default: a pdf folder beside each file
  --check           render and report only - no PDF; exit 1 on a problem
  --force           print even when a diagram failed, an image is missing or a table is too wide
  --browser PATH    the browser to use; default: the first of Chrome, Edge, Chromium that works
  --paper A4|letter the page size; default A4. Front matter orientation: landscape turns it
  --css FILE        a stylesheet added after the built-in one (a client's look)

How it works. For each file the script builds a page around the bundled markdown-it and mermaid
(md2pdf_assets/, beside this script - nothing is fetched from the internet), then runs the
browser headless twice. Pass 1 (--dump-dom) turns the Markdown into HTML, draws every ```mermaid
block as SVG, gives each heading its GitHub anchor, points links to another .md at its .pdf, and
reports diagrams that failed (with their line), images that did not load, and tables wider than
the page (or, on a portrait page, of 9 columns and more). The script saves that page as FILE.html: scripts removed,
CSS and images inlined, so it opens and prints anywhere - the fallback where policy blocks headless
mode. Pass 2 prints FILE.html with no browser header or footer, so nothing is left to wait for.

The page: A4 (or letter) with margins; a cover page and a contents page when the file starts with
front matter (--- / title: / version: / date: / status: / prepared-for: / prepared-by: / ---);
the footer carries the title and "Page n of N" (Chrome and Edge 131 and later; older print none,
and the script warns); status: Draft adds a DRAFT watermark; tables repeat their header row on
every page and never split a row, 7 columns or more print smaller, a column whose every value is
14 characters or fewer never wraps, and only code breaks inside a word; a diagram or image is
scaled to the page, never split, and kept with a caption paragraph right after it that starts
"Figure", "Fig.", "Diagram" or "Table" (in italics or not).

A browser that exits at once with no output - one part-way through an update, or one handing
the job to a copy already open - is skipped for the next, and the reason is printed. Temporary
files go in .harness-tmp/md2pdf/ under the working-tree root and are removed afterwards. Output
is ASCII. Exit 0: every file printed (or checked clean); 1: a problem stopped a file; 2: a bad
command or no working browser.
"""
import base64
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import unquote, urlparse
from urllib.request import pathname2url, url2pathname

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "md2pdf_assets")
LIBS = ("markdown-it.min.js", "mermaid.min.js")
TMP_DIR = os.path.join(".harness-tmp", "md2pdf")
PAPER = {  # page width, height in mm
    "A4": (210, 297),
    "letter": (215.9, 279.4),
}
MARGIN = (20, 16, 18, 16)  # top, right, bottom, left, mm
FOOTER_MIN_VERSION = 131  # CSS page margin boxes
BUDGET_MS = 30000  # virtual time for pass 1 to draw every diagram
TIMEOUT_S = 180
QUICK_EXIT_S = 5  # a run this short with no output: the browser handed the job off


def die(msg, code=2):
    print(f"md2pdf.py: {msg}", file=sys.stderr)
    sys.exit(code)


def to_url(path):
    return "file:" + pathname2url(os.path.abspath(path))


def read_file(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        die(f"cannot read {path}: {e}")
    try:
        return raw.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeDecodeError:
        die(f"{path} is not UTF-8; save it as UTF-8 and rerun")


def front_matter(text):
    """({key: value}, body, number of lines the front matter took)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text, 0
    values = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return values, "\n".join(lines[i + 1:]), i + 1
        if ":" in lines[i]:
            k, v = lines[i].split(":", 1)
            values[k.strip().lower()] = v.strip()
    return {}, text, 0


def first_heading(body):
    m = re.search(r"^#\s+(.+?)\s*#*\s*$", body, re.M)
    return m.group(1).strip() if m else None


def css_string(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def script_json(value):
    """JSON safe inside <script>: no </script>, no <!--, ASCII only."""
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&",
                                                                                     "\\u0026")


# --- browser --------------------------------------------------------------------------------

def candidates():
    env = os.environ
    if os.name == "nt":
        roots = [env.get("PROGRAMFILES", r"C:\Program Files"),
                 env.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), env.get("LOCALAPPDATA")]
        rels = (r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe",
                r"Chromium\Application\chrome.exe")
        paths = [os.path.join(r, rel) for rel in rels for r in roots if r]
    elif sys.platform == "darwin":
        paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                 "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    else:
        paths = [shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium",
                                           "chromium-browser", "microsoft-edge",
                                           "microsoft-edge-stable")]
    out = []
    for p in paths:
        if p and os.path.isfile(p) and os.path.normcase(p) not in map(os.path.normcase, out):
            out.append(p)
    return out


def browser_version(path):
    """The major version, or None. On Windows the exe prints nothing for --version, so the
    version-named folder beside it is read instead."""
    folder = os.path.dirname(path)
    try:
        found = [d for d in os.listdir(folder)
                 if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", d) and os.path.isdir(os.path.join(folder, d))]
    except OSError:
        found = []
    if found:
        return max(int(d.split(".")[0]) for d in found)
    if os.name == "nt":
        return None
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+)\.\d+", out or "")
    return int(m.group(1)) if m else None


class GaveUp(Exception):
    """The browser ran but produced nothing - try the next one."""


def run_browser(browser, profile, extra):
    cmd = [browser, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--disable-extensions", f"--user-data-dir={profile}",
           "--allow-file-access-from-files"] + extra
    start = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise GaveUp(f"no result within {TIMEOUT_S} s")
    except OSError as e:
        raise GaveUp(f"cannot start it: {e}")
    return p, time.time() - start


def dump(browser, profile, page):
    p, secs = run_browser(browser, profile, [f"--virtual-time-budget={BUDGET_MS}", "--dump-dom",
                                             to_url(page)])
    dom = p.stdout.decode("utf-8", "replace")
    if not dom.strip():
        why = "exited at once with no output" if secs < QUICK_EXIT_S else "printed nothing"
        tail = p.stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
        raise GaveUp(f"{why} (exit {p.returncode})" + (f": {tail[0][:160]}" if tail[0] else "")
                     + " - part-way through an update, handing off to a copy already open, or "
                       "headless mode blocked by policy")
    return dom


def print_pdf(browser, profile, page, pdf):
    if os.path.exists(pdf):
        os.remove(pdf)
    p, _ = run_browser(browser, profile, ["--no-pdf-header-footer", "--print-to-pdf-no-header",
                                          f"--print-to-pdf={os.path.abspath(pdf)}", to_url(page)])
    if not os.path.isfile(pdf) or os.path.getsize(pdf) == 0:
        raise GaveUp(f"wrote no PDF (exit {p.returncode})")


# --- the page -------------------------------------------------------------------------------

RENDER_JS = r"""
(async function () {
  const cfg = JSON.parse(document.getElementById('md2pdf-config').textContent);
  const src = JSON.parse(document.getElementById('md2pdf-source').textContent);
  const report = {diagrams: 0, failed: [], missingImages: [], wideTables: [], tables: 0,
                  headings: 0, error: null};
  const slug = t => t.trim().toLowerCase().replace(/[^\p{L}\p{N}\p{M}_\- ]/gu, '').replace(/ /g, '-');
  const near = el => { let e = el; while (e) { let p = e.previousElementSibling;
    while (p) { if (/^H[1-6]$/.test(p.tagName)) return p.textContent.trim(); p = p.previousElementSibling; }
    e = e.parentElement; if (e && e.id === 'content') break; } return '(before the first heading)'; };
  try {
    const md = window.markdownit({html: true, linkify: false, typographer: false});
    const fence = md.renderer.rules.fence;
    md.renderer.rules.fence = function (tokens, idx, options, env, self) {
      const t = tokens[idx];
      if ((t.info || '').trim().split(/\s+/)[0] === 'mermaid') {
        const line = t.map ? t.map[0] + 1 + cfg.lineOffset : 0;
        return '<div class="mermaid-src" data-line="' + line + '">' + md.utils.escapeHtml(t.content) + '</div>\n';
      }
      return fence(tokens, idx, options, env, self);
    };
    const body = document.getElementById('content');
    body.innerHTML = md.render(src);
    body.querySelectorAll('script, iframe, object, embed').forEach(e => e.remove());
    if (cfg.dropFirstH1) { const h = body.querySelector('h1'); if (h) h.remove(); }
    const seen = {};
    body.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
      const b = slug(h.textContent); const n = seen[b] || 0; seen[b] = n + 1;
      h.id = n ? b + '-' + n : b; report.headings++;
    });
    body.querySelectorAll('a[href]').forEach(a => {
      const href = a.getAttribute('href');
      const m = href.match(/^([^#?:]+\.md)(#.*)?$/i);
      if (m) a.setAttribute('href', m[1].split('/').pop().replace(/\.md$/i, '.pdf') + (m[2] || ''));
    });
    body.querySelectorAll('table').forEach(t => {
      report.tables++;
      const cols = t.rows.length ? t.rows[0].cells.length : 0;
      if (cols >= 7) t.classList.add('many-columns');
      t.dataset.cols = cols;
      const rows = Array.from(t.rows);
      for (let c = 0; c < cols; c++) {
        const cells = rows.map(r => r.cells[c]).filter(Boolean);
        if (cells.length && cells.every(x => x.textContent.trim().length <= 14)) cells.forEach(x => x.classList.add('nowrap'));
      }
      const w = document.createElement('div'); w.className = 'table-wrap';
      t.parentNode.insertBefore(w, t); w.appendChild(t);
    });
    mermaid.initialize({startOnLoad: false, theme: 'neutral', securityLevel: 'strict',
                        fontFamily: getComputedStyle(document.body).fontFamily});
    let n = 0;
    for (const el of Array.from(body.querySelectorAll('.mermaid-src'))) {
      report.diagrams++;
      try {
        const out = await mermaid.render('md2pdf-diagram-' + (n++), el.textContent);
        const d = document.createElement('div'); d.className = 'diagram'; d.innerHTML = out.svg;
        el.replaceWith(d);
      } catch (e) {
        const lines = String((e && e.message) || e).split('\n').map(l => l.trim()).filter(Boolean);
        const msg = [lines[0], lines.find(l => /^(Expecting|Lexical|Unrecognized)/.test(l))].filter(Boolean).join(' ');
        report.failed.push({line: +el.dataset.line, error: msg});
        const box = document.createElement('pre'); box.className = 'diagram-error';
        box.textContent = 'This diagram could not be drawn (line ' + el.dataset.line + '): ' + msg;
        el.replaceWith(box);
      }
    }
    document.querySelectorAll('body > [id^="dmd2pdf-diagram"], body > [id^="md2pdf-diagram"]').forEach(e => e.remove());
    const isCaption = p => p && p.tagName === 'P' && /^(figure|fig\.|diagram|table)\b/i.test(p.textContent.trim());
    body.querySelectorAll('.diagram, p > img:only-child').forEach(el => {
      const block = el.tagName === 'IMG' ? el.parentElement : el;
      const next = block.nextElementSibling;
      const fig = document.createElement('figure'); fig.className = 'keep';
      block.parentNode.insertBefore(fig, block); fig.appendChild(block);
      if (isCaption(next)) { next.classList.add('caption'); fig.appendChild(next); }
    });
    if (cfg.toc) {
      const hs = Array.from(body.querySelectorAll('h2'));
      if (hs.length >= 3) {
        const nav = document.createElement('nav'); nav.className = 'toc';
        nav.innerHTML = '<h2>Contents</h2><ol></ol>';
        const ol = nav.querySelector('ol');
        hs.forEach(h => { const li = document.createElement('li'); const a = document.createElement('a');
          a.href = '#' + h.id; a.textContent = h.textContent; li.appendChild(a); ol.appendChild(li); });
        body.parentNode.insertBefore(nav, body);
      }
    }
    const imgs = Array.from(body.querySelectorAll('img'));
    await Promise.all(imgs.map(img => img.complete ? null : new Promise(r => {
      img.addEventListener('load', r); img.addEventListener('error', r); setTimeout(r, 5000); })));
    imgs.forEach(img => { if (!img.complete || img.naturalWidth === 0) report.missingImages.push(img.getAttribute('src')); });
    const avail = body.clientWidth;
    body.querySelectorAll('table').forEach(t => {
      const w = Math.ceil(t.scrollWidth);
      if (w > avail + 1 || (+t.dataset.cols >= 9 && !cfg.landscape)) {
        report.wideTables.push({heading: near(t.parentElement), columns: +t.dataset.cols,
                                width: w, available: Math.floor(avail),
                                landscape: !!cfg.landscape});
      }
    });
  } catch (e) {
    report.error = String((e && e.stack) || e);
  }
  const out = document.createElement('script');
  out.type = 'application/json'; out.id = 'md2pdf-report'; out.textContent = JSON.stringify(report);
  document.body.appendChild(out);
})();
"""


def build_page(md_path, paper, extra_css):
    text = read_file(md_path)
    fm, body, offset = front_matter(text)
    landscape = fm.get("orientation", "").lower() == "landscape"
    w, h = PAPER[paper]
    if landscape:
        w, h = h, w
    top, right, bottom, left = MARGIN
    width = round(w - left - right, 1)
    title = fm.get("title") or first_heading(body) or os.path.splitext(os.path.basename(md_path))[0]
    cover = bool(fm.get("title"))
    size = f"{paper} landscape" if landscape else paper
    page_css = (
        f"@page {{ size: {size}; margin: {top}mm {right}mm {bottom}mm {left}mm;"
        f" @bottom-left {{ content: {css_string(title)}; font: 8pt Arial, sans-serif; color: #57606a; }}"
        f" @bottom-right {{ content: \"Page \" counter(page) \" of \" counter(pages);"
        f" font: 8pt Arial, sans-serif; color: #57606a; }} }}\n"
        + ("@page :first { @bottom-left { content: none; } @bottom-right { content: none; } }\n"
           if cover else "")
        + f"#content, .cover, .toc {{ width: {width}mm; }}\n"
        + f".cover {{ height: {round(h - top - bottom - 6, 1)}mm; }}\n")
    css = read_file(os.path.join(ASSETS, "print.css"))
    parts = [
        "<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
        f"<title>{html.escape(title)}</title>",
        f'<base href="{html.escape(to_url(os.path.dirname(os.path.abspath(md_path))) + "/")}">',
        f"<style>\n{css}\n{page_css}</style>",
    ]
    if extra_css:
        parts.append(f"<style>\n{read_file(extra_css)}\n</style>")
    for lib in LIBS:
        parts.append(f'<script src="{html.escape(to_url(os.path.join(ASSETS, lib)))}"></script>')
    parts.append("</head><body>")
    if fm.get("status", "").lower() == "draft":
        parts.append('<div class="watermark">DRAFT</div>')
    if cover:
        rows = [("Prepared for", fm.get("prepared-for")), ("Prepared by", fm.get("prepared-by")),
                ("Version", fm.get("version")), ("Date", fm.get("date")),
                ("Status", fm.get("status"))]
        meta = "".join(f"<tr><th>{k}</th><td>{html.escape(v)}</td></tr>" for k, v in rows if v)
        parts.append(f'<section class="cover"><div class="doc-title">{html.escape(title)}</div>'
                     f'<div class="doc-status">{html.escape(fm.get("status", ""))}'
                     f'{" &middot; Version " + html.escape(fm["version"]) if fm.get("version") else ""}'
                     f"</div><table>{meta}</table></section>")
    config = {"lineOffset": offset, "dropFirstH1": cover, "toc": cover,
              "landscape": landscape}
    parts += [
        '<main id="content"></main>',
        f'<script type="application/json" id="md2pdf-config">{script_json(config)}</script>',
        f'<script type="application/json" id="md2pdf-source">{script_json(body)}</script>',
        f"<script>{RENDER_JS}</script>",
        "</body></html>",
    ]
    return "\n".join(parts), title


def report_of(dom):
    m = re.search(r'<script[^>]*id="md2pdf-report"[^>]*>(.*?)</script>', dom, re.S)
    if not m:
        return None
    try:
        return json.loads(html.unescape(m.group(1)) if "&quot;" in m.group(1) else m.group(1))
    except ValueError:
        return None


def inline_image(m, base_dir):
    src = html.unescape(m.group(2))
    if src.startswith("data:") or re.match(r"^https?:", src, re.I):
        return m.group(0)
    path = url2pathname(urlparse(src).path) if src.startswith("file:") else \
        os.path.join(base_dir, unquote(src.split("#", 1)[0].split("?", 1)[0]))
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
    except OSError:
        return m.group(0)
    kind = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return f'{m.group(1)}"data:{kind};base64,{data}"'


def static_page(dom, base_dir):
    """The rendered page with nothing left to run or fetch: scripts and <base> removed, images
    inlined."""
    dom = re.sub(r"<script\b[^>]*>.*?</script>", "", dom, flags=re.S | re.I)
    dom = re.sub(r"<base\b[^>]*>", "", dom, flags=re.I)
    dom = re.sub(r'(<img\b[^>]*?\bsrc=)"([^"]*)"', lambda m: inline_image(m, base_dir), dom,
                 flags=re.I)
    return dom if dom.lstrip().lower().startswith("<!doctype") else "<!doctype html>\n" + dom


def problems_in(report):
    if report is None:
        return ["the page reported nothing - the bundled scripts did not run"]
    out = []
    if report.get("error"):
        out.append(f"the page failed: {report['error'].splitlines()[0]}")
    for f in report.get("failed", []):
        out.append(f"diagram at line {f['line']} could not be drawn: {f['error']}")
    for src in report.get("missingImages", []):
        out.append(f"image {src} did not load")
    for t in report.get("wideTables", []):
        out.append(f"table under \"{t['heading']}\" ({t['columns']} columns) is "
                   + (f"{t['width']}px wide, the page {t['available']}px"
                      if t["width"] > t["available"] + 1 else "very wide")
                   + (" - split it" if t.get("landscape") else
                      " - split it, or set orientation: landscape in the front matter"))
    return out


def pdf_pages(path):
    with open(path, "rb") as f:
        return len(re.findall(rb"/Type\s*/Page(?!s)", f.read()))


def parse_args(argv):
    opts = {"--out": None, "--browser": None, "--paper": "A4", "--css": None}
    flags, files = set(), []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in opts:
            if i + 1 >= len(argv):
                die(f"{a} needs a value")
            opts[a] = argv[i + 1]
            i += 2
            continue
        if a in ("--check", "--force"):
            flags.add(a)
        elif a.startswith("--"):
            die(f"unknown flag {a}")
        else:
            files.append(a)
        i += 1
    if not files:
        print(__doc__)
        sys.exit(2)
    paper = next((p for p in PAPER if p.lower() == opts["--paper"].lower()), None)
    if not paper:
        die(f"--paper is A4 or letter, not {opts['--paper']}")
    opts["--paper"] = paper
    for f in files:
        if any(c in f for c in "*?"):
            die(f"{f}: name each file - this script expands no wildcard")
        if not os.path.isfile(f):
            die(f"{f} does not exist")
    for k in ("--css", "--browser"):
        if opts[k] and not os.path.isfile(opts[k]):
            die(f"{k} {opts[k]} does not exist")
    return files, opts, flags


class Run:
    """The browser that works, once found, and the ones skipped on the way."""

    def __init__(self, browsers, profile):
        self.browsers, self.profile = browsers, profile
        self.working, self.skipped = None, []

    def render(self, md, paper, css):
        page_html, _ = build_page(md, paper, css)
        stem = os.path.splitext(os.path.basename(md))[0]
        page = os.path.join(TMP_DIR, f"{stem}.page.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write(page_html)
        try:
            for b in ([self.working] if self.working else self.browsers):
                try:
                    dom = dump(b, self.profile, page)
                except GaveUp as e:
                    self.skipped.append(f"{b}: {e}")
                    continue
                self.working = b
                return dom
        finally:
            os.remove(page)
        for s in self.skipped:
            print(f"skipped {s}", file=sys.stderr)
        die("no browser could render the page", 2)


def show(name, headline, problems):
    print(f"{name}: {headline}")
    for p in problems:
        print(f"  {p}")


def one_file(run, md, opts, flags):
    """Check or print one file; True when it went through."""
    dom = run.render(md, opts["--paper"], opts["--css"])
    report = report_of(dom)
    problems = problems_in(report)
    name = os.path.basename(md)
    if "--check" in flags:
        if problems:
            show(name, f"{len(problems)} problem(s)", problems)
        else:
            print(f"{name}: ok - {report['diagrams']} diagrams, {report['tables']} tables, "
                  f"{report['headings']} headings")
        return not problems
    if problems and "--force" not in flags:
        show(name, f"not printed - {len(problems)} problem(s) (--force prints anyway)", problems)
        return False
    stem = os.path.splitext(name)[0]
    out_dir = opts["--out"] or os.path.join(os.path.dirname(os.path.abspath(md)), "pdf")
    os.makedirs(out_dir, exist_ok=True)
    static = os.path.join(out_dir, stem + ".html")
    with open(static, "w", encoding="utf-8") as f:
        f.write(static_page(dom, os.path.dirname(os.path.abspath(md))))
    pdf = os.path.join(out_dir, stem + ".pdf")
    try:
        print_pdf(run.working, run.profile, static, pdf)
    except GaveUp as e:
        print(f"{name}: not printed - {run.working}: {e}; print {static} by hand instead")
        return False
    pages = pdf_pages(pdf)
    show(name, f"-> {pdf}: {str(pages) + ' pages, ' if pages else ''}{report['diagrams']} "
               f"diagrams, {report['tables']} tables"
               + (f"; printed with {len(problems)} problem(s)" if problems else ""), problems)
    return True


def main(argv):
    for stream in (sys.stdout, sys.stderr):  # ASCII survives any console encoding
        stream.reconfigure(encoding="ascii", errors="backslashreplace")
    files, opts, flags = parse_args(argv)
    missing = [n for n in LIBS + ("print.css",) if not os.path.isfile(os.path.join(ASSETS, n))]
    if missing:
        die(f"{ASSETS} lacks {', '.join(missing)} - copy the whole tools folder")
    browsers = [opts["--browser"]] if opts["--browser"] else candidates()
    if not browsers:
        die("no Chrome, Edge or Chromium found - install one, or pass --browser PATH")
    os.makedirs(TMP_DIR, exist_ok=True)
    run = Run(browsers, os.path.abspath(os.path.join(TMP_DIR, f"profile-{os.getpid()}")))
    try:
        failed = sum(not one_file(run, md, opts, flags) for md in files)
    finally:
        shutil.rmtree(run.profile, ignore_errors=True)
        try:
            os.rmdir(TMP_DIR)
        except OSError:
            pass
    print(f"browser: {run.working}", file=sys.stderr)
    version = browser_version(run.working)
    if version is not None and version < FOOTER_MIN_VERSION:
        print(f"warning: this browser is version {version}; page numbers and the footer need "
              f"{FOOTER_MIN_VERSION} or later, so the PDFs have none", file=sys.stderr)
    for s in run.skipped:
        print(f"skipped {s}", file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
