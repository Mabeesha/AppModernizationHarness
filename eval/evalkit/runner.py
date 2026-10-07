"""Tier 1 orchestration: build the context, run selected checks, collect results."""

from __future__ import annotations

import subprocess
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .model import CheckResult, Finding, Metric, Severity
from .parser import load_documents, load_set
from .registry import Check, Context, load_builtin_checks, select
from .tokens import CachingCounter, get_counter


@dataclass
class RunOutcome:
    findings: list[Finding] = field(default_factory=list)
    metrics: list[Metric] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)
    checks_run: list[Check] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def _git_commit(repo_root: Path) -> str:
    try:
        p = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
        )
        return p.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def run_tier1(
    *,
    set_dir: Path,
    repo_root: Path,
    selectors: list[str] | None = None,
    det_only: bool = False,
    include_experimental: bool = False,
    with_llm: bool = False,
    docs_dir: Path | None = None,
    token_backend: str = "tiktoken",
    model: str = "claude-opus-5",
    cache_dir: Path | None = None,
    budget_warn: int | None = None,
) -> RunOutcome:
    load_builtin_checks()

    iset = load_set(set_dir, repo_root)
    docs = []
    if docs_dir and docs_dir.is_dir():
        docs = load_documents(sorted(docs_dir.glob("*.md")), repo_root)

    counter = get_counter(token_backend, model=model, cache_dir=cache_dir)

    ctx = Context(
        iset=iset,
        repo_root=repo_root,
        counter=counter,
        docs=docs,
        with_llm=with_llm,
        include_experimental=include_experimental,
        config={
            "budget_warn": budget_warn,
            "docs_dir": str(docs_dir) if docs_dir else None,
        },
    )

    chosen = select(
        selectors, det_only=det_only, include_experimental=include_experimental
    )

    outcome = RunOutcome()
    for chk in chosen:
        if not chk.deterministic and not with_llm:
            outcome.skipped[chk.id] = "needs --with-llm (judge harness)"
            continue
        try:
            result: CheckResult = chk.fn(ctx)
        except Exception:  # a broken check must not take the run down
            outcome.skipped[chk.id] = f"check raised: {traceback.format_exc(limit=1).strip()}"
            continue
        # A check can both skip and report, so always keep what it produced —
        # but a skipped check must not be counted as run, or "18 run, 7 skipped"
        # over a selection of 18 double-counts and overstates coverage.
        outcome.findings.extend(result.findings)
        outcome.metrics.extend(result.metrics)
        if result.skipped:
            outcome.skipped[chk.id] = result.skipped
        else:
            outcome.checks_run.append(chk)

    if isinstance(counter, CachingCounter):
        counter.flush()

    outcome.meta = {
        "set": iset.name,
        "set_dir": str(set_dir),
        "repo_root": str(repo_root),
        "commit": _git_commit(repo_root),
        "tier": "static",
        "checks_run": len(outcome.checks_run),
        "checks_selected": [c.id for c in chosen],
        "token_backend": counter.name,
        "token_backend_approximate": counter.approximate,
        "token_disclaimer": counter.disclaimer,
        "token_model": model,
        "docs_dir": str(docs_dir) if docs_dir else None,
        "det_only": det_only,
        "with_llm": with_llm,
    }
    return outcome


def exit_code(findings: list[Finding]) -> int:
    return 1 if any(f.severity is Severity.BLOCKER for f in findings) else 0
