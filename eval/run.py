#!/usr/bin/env python3
"""Instruction-set evaluation CLI.

Tier 1 (static analysis) is implemented. Tier 2 (behavioural) is designed in
EVAL_DESIGN.md §6 and not yet built; `--tier behavioral` reports that plainly
rather than pretending.

Examples
--------
    # CI default: every deterministic check, zero API calls
    uv run run.py --set ../ModernizationHarness --det-only

    # Token budgets, with the variable half measured against real outputs
    uv run run.py --set ../ModernizationHarness --checks A --docs ../instruction_output

    # Single check
    uv run run.py --set ../ModernizationHarness --checks B1
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from evalkit.model import Severity
from evalkit.registry import all_checks, load_builtin_checks
from evalkit.report import load_baseline, partition, render_markdown, write_json
from evalkit.runner import exit_code, run_tier1

HERE = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = HERE.parent


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run.py",
        description="Evaluate an agent instruction set (see EVAL_DESIGN.md).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--set", dest="set_dir", type=Path,
                   help="Instruction set directory, e.g. ../ModernizationHarness")
    p.add_argument("--tier", choices=["static", "behavioral"], default="static")
    p.add_argument("--checks", nargs="*", default=None,
                   help="Check ids or groups to run (e.g. B B3 A1). Default: all.")
    p.add_argument("--det-only", action="store_true",
                   help="Deterministic checks only — no API calls. The CI default.")
    p.add_argument("--with-llm", action="store_true",
                   help="Enable judge-backed checks (not yet implemented; see design Phase 4).")
    p.add_argument("--include-experimental", action="store_true",
                   help="Include checks marked experimental (currently E3).")
    p.add_argument("--docs", dest="docs_dir", type=Path, default=None,
                   help="Directory of generated pipeline artifacts, to complete A3's "
                        "variable half and resolve generated-file references.")
    p.add_argument("--token-backend", choices=["tiktoken", "anthropic"], default="tiktoken",
                   help="tiktoken (default, approximate) | anthropic (placeholder, exact).")
    p.add_argument("--model", default="claude-opus-5",
                   help="Model id for token counting; part of the cache key.")
    p.add_argument("--budget-warn", type=int, default=None,
                   help="Emit a MAJOR finding when a stage composite exceeds N tokens. "
                        "Off by default — group A reports data, it does not gate.")
    p.add_argument("--baseline", type=Path, default=HERE / "baseline.json",
                   help="Finding ids to suppress (per-finding, with a reason).")
    p.add_argument("--out", type=Path, default=None,
                   help="Output directory. Default: eval/results/<ts>-<set>/")
    p.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    p.add_argument("--no-cache", action="store_true", help="Bypass the token cache.")
    p.add_argument("--quiet", action="store_true", help="Suppress the console summary.")
    p.add_argument("--list-checks", action="store_true", help="List registered checks and exit.")
    return p


def cmd_list_checks() -> int:
    load_builtin_checks()
    print(f"{'ID':<5} {'KIND':<14} {'STATUS':<16} TITLE")
    print("-" * 78)
    for c in all_checks():
        kind = "deterministic" if c.deterministic else "llm-judge"
        if not c.implemented:
            status = "stub"
        elif c.experimental:
            status = "experimental"
        else:
            status = "implemented"
        print(f"{c.id:<5} {kind:<14} {status:<16} {c.title}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_checks:
        return cmd_list_checks()

    if args.tier == "behavioral":
        print(
            "Tier 2 (behavioural) is designed but not implemented — see EVAL_DESIGN.md §6 "
            "and §11 Phase 5/6. It is blocked on eval/fixtures/INTAKE.md, which needs a "
            "human judgement call against sample_legacy_app/.",
            file=sys.stderr,
        )
        return 2

    if not args.set_dir:
        print("error: --set is required (e.g. --set ../ModernizationHarness)", file=sys.stderr)
        return 2

    set_dir = args.set_dir.resolve()
    repo_root = args.repo_root.resolve()
    cache_dir = None if args.no_cache else HERE / ".cache"

    try:
        outcome = run_tier1(
            set_dir=set_dir,
            repo_root=repo_root,
            selectors=args.checks,
            det_only=args.det_only,
            include_experimental=args.include_experimental,
            with_llm=args.with_llm,
            docs_dir=args.docs_dir.resolve() if args.docs_dir else None,
            token_backend=args.token_backend,
            model=args.model,
            cache_dir=cache_dir,
            budget_warn=args.budget_warn,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    baseline = load_baseline(args.baseline)
    active, suppressed = partition(outcome.findings, baseline)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = (args.out or (HERE / "results" / f"{ts}-{outcome.meta['set']}")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    titles = {c.id: c.title for c in all_checks()}

    write_json(
        out_dir / "findings.json",
        meta=outcome.meta,
        findings=active,
        suppressed=suppressed,
        metrics=outcome.metrics,
        skipped=outcome.skipped,
    )
    md = render_markdown(
        meta=outcome.meta,
        findings=active,
        suppressed=suppressed,
        metrics=outcome.metrics,
        skipped=outcome.skipped,
        check_titles=titles,
    )
    (out_dir / "report.md").write_text(md, encoding="utf-8")

    if not args.quiet:
        b = sum(1 for f in active if f.severity is Severity.BLOCKER)
        mj = sum(1 for f in active if f.severity is Severity.MAJOR)
        mn = sum(1 for f in active if f.severity is Severity.MINOR)
        print(f"{outcome.meta['set']}  ({outcome.meta['commit']})")
        print(f"  checks run : {len(outcome.checks_run)}  skipped: {len(outcome.skipped)}")
        print(f"  findings   : {b} blocker, {mj} major, {mn} minor"
              + (f"  ({len(suppressed)} suppressed)" if suppressed else ""))
        if outcome.meta["token_backend_approximate"]:
            print(f"  tokens     : APPROXIMATE via {outcome.meta['token_backend']}")
        print(f"  report     : {out_dir / 'report.md'}")

    return exit_code(active)


if __name__ == "__main__":
    raise SystemExit(main())
