"""Output: findings.json, report.md, and baseline suppression."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import Finding, Metric, Severity


def load_baseline(path: Path | None) -> dict[str, str]:
    """finding id -> reason. Suppression is per-finding, never per-check, so a
    suppressed instance can never hide a newly-appearing one."""
    if not path or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    entries = data.get("suppressed", data if isinstance(data, dict) else {})
    out: dict[str, str] = {}
    for k, v in entries.items():
        out[k] = v if isinstance(v, str) else (v or {}).get("reason", "")
    return out


def partition(findings: list[Finding], baseline: dict[str, str]):
    active = [f for f in findings if f.id not in baseline]
    suppressed = [f for f in findings if f.id in baseline]
    return active, suppressed


def write_json(
    path: Path,
    *,
    meta: dict[str, Any],
    findings: list[Finding],
    suppressed: list[Finding],
    metrics: list[Metric],
    skipped: dict[str, str],
) -> None:
    payload = {
        "meta": meta,
        "summary": {
            "blocker": sum(1 for f in findings if f.severity is Severity.BLOCKER),
            "major": sum(1 for f in findings if f.severity is Severity.MAJOR),
            "minor": sum(1 for f in findings if f.severity is Severity.MINOR),
            "suppressed": len(suppressed),
            "skipped_checks": len(skipped),
        },
        "findings": [f.to_dict() for f in findings],
        "suppressed": [f.to_dict() for f in suppressed],
        "metrics": [m.to_dict() for m in metrics],
        "skipped": skipped,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _fmt_int(n: Any) -> str:
    return f"{n:,}" if isinstance(n, int) else str(n)


def render_markdown(
    *,
    meta: dict[str, Any],
    findings: list[Finding],
    suppressed: list[Finding],
    metrics: list[Metric],
    skipped: dict[str, str],
    check_titles: dict[str, str],
) -> str:
    out: list[str] = []
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    out.append(f"# Instruction Set Eval — {meta['set']}")
    out.append("")
    out.append(f"*Tier 1 (static) · {ts} · commit `{meta.get('commit', 'unknown')}`*")
    out.append("")

    approx = meta.get("token_backend_approximate")
    if approx:
        out.append(
            f"> **Token counts are approximate.** Backend `{meta.get('token_backend')}`. "
            f"{meta.get('token_disclaimer', '')}"
        )
        out.append("")

    counts = {
        Severity.BLOCKER: sum(1 for f in findings if f.severity is Severity.BLOCKER),
        Severity.MAJOR: sum(1 for f in findings if f.severity is Severity.MAJOR),
        Severity.MINOR: sum(1 for f in findings if f.severity is Severity.MINOR),
    }
    out.append("## Summary")
    out.append("")
    out.append("| Severity | Count |")
    out.append("|---|---:|")
    out.append(f"| Blocker | {counts[Severity.BLOCKER]} |")
    out.append(f"| Major | {counts[Severity.MAJOR]} |")
    out.append(f"| Minor | {counts[Severity.MINOR]} |")
    if suppressed:
        out.append(f"| *Suppressed (baseline)* | {len(suppressed)} |")
    out.append("")
    out.append(f"Checks run: {meta.get('checks_run', 0)} · skipped: {len(skipped)}")
    out.append("")

    # ---- Token budget tables (group A) ----
    file_tokens = [m for m in metrics if m.check == "A1"]
    if file_tokens:
        out.append("## Token budget — per file")
        out.append("")
        out.append("| File | Tokens | Lines | Bytes |")
        out.append("|---|---:|---:|---:|")
        for m in sorted(file_tokens, key=lambda m: -m.value):
            c = m.context
            out.append(
                f"| [{Path(c['file']).name}]({c['file']}) | {_fmt_int(m.value)} "
                f"| {_fmt_int(c['lines'])} | {_fmt_int(c['bytes'])} |"
            )
        total = sum(m.value for m in file_tokens)
        out.append(f"| **Set total** | **{_fmt_int(total)}** | | |")
        out.append("")

    budgets = [m for m in metrics if m.check == "A3"]
    if budgets:
        out.append("## Token budget — per stage run (composite)")
        out.append("")
        out.append(
            "What one stage run loads, counted as a single payload rather than a sum of "
            "per-file counts (token counts are not additive). Legacy source excluded."
        )
        out.append("")
        out.append(
            "| Stage | Fixed (instructions) | Fixed + optional add-on | Variable (generated) "
            "| Total | Not measured |"
        )
        out.append("|---|---:|---:|---:|---:|---|")
        for m in sorted(budgets, key=lambda m: m.context["stage"]):
            c = m.context
            opt = c.get("fixed_with_optional_tokens")
            opt_s = (
                f"{_fmt_int(opt)} (+ {', '.join(f'`{f}`' for f in c.get('optional_files', []))})"
                if isinstance(opt, int) else "—"
            )
            var = c["variable_tokens"]
            var_s = _fmt_int(var) if isinstance(var, int) else f"*{var}*"
            total_s = _fmt_int(m.value) if c["complete"] else f"{_fmt_int(m.value)}+"
            missing = c.get("variable_missing") or []
            miss_s = ", ".join(f"`{p}`" for p in missing) if missing else "—"
            out.append(
                f"| {c['stage']} | {_fmt_int(c['fixed_tokens'])} | {opt_s} | {var_s} "
                f"| {total_s} | {miss_s} |"
            )
        out.append("")
        if any(isinstance(m.context.get("fixed_with_optional_tokens"), int) for m in budgets):
            out.append(
                "*Fixed + optional add-on is what the run loads in projects that use the "
                "add-on (Stage 4's git file, only when `context.repo.git` is `agent`). Total "
                "uses the plain Fixed figure.*"
            )
            out.append("")
        if any(not m.context["complete"] for m in budgets):
            out.append(
                "*A `+` total is a floor, not a measurement: one or more generated artifacts "
                "for that stage were unavailable, and are listed in the last column. "
                "`unmeasured` means none were. Pass `--docs <dir>` pointing at a complete "
                "pipeline output directory to close these rows — they are deliberately never "
                "estimated.*"
            )
            out.append("")

    deltas = [m for m in metrics if m.check == "A4"]
    if deltas:
        out.append("## Token growth vs git HEAD")
        out.append("")
        out.append("| File | HEAD | Working tree | Delta | % |")
        out.append("|---|---:|---:|---:|---:|")
        for m in sorted(deltas, key=lambda m: -abs(m.value)):
            c = m.context
            sign = "+" if m.value > 0 else ""
            pct = f"{sign}{c['pct']}%" if c.get("pct") is not None else "—"
            out.append(
                f"| [{Path(c['file']).name}]({c['file']}) | {_fmt_int(c['head_tokens'])} "
                f"| {_fmt_int(c['worktree_tokens'])} | {sign}{_fmt_int(m.value)} | {pct} |"
            )
        out.append("")

    # ---- Findings ----
    if findings:
        out.append("## Findings")
        out.append("")
        by_check: dict[str, list[Finding]] = defaultdict(list)
        for f in findings:
            by_check[f.check].append(f)

        for cid in sorted(by_check, key=lambda c: (c[0], int(c[1:]) if c[1:].isdigit() else 0)):
            group = sorted(by_check[cid], key=lambda f: (f.severity.rank, f.file, f.line))
            title = check_titles.get(cid, "")
            out.append(f"### {cid} — {title} ({len(group)})")
            out.append("")
            for f in group:
                loc = f"{f.file}#L{f.line}" if f.line else f.file
                label = Path(f.file).name + (f":{f.line}" if f.line else "")
                out.append(f"- **[{f.severity.value}]** {f.summary}")
                out.append(f"  - `{f.id}` · [{label}]({loc})")
                out.append(f"  - {f.detail}")
                for ev in f.evidence[:3]:
                    out.append(f"  - > `{ev}`")
            out.append("")
    else:
        out.append("## Findings")
        out.append("")
        out.append("None.")
        out.append("")

    if skipped:
        out.append("## Skipped checks")
        out.append("")
        out.append("| Check | Title | Reason |")
        out.append("|---|---|---|")
        for cid in sorted(skipped, key=lambda c: (c[0], int(c[1:]) if c[1:].isdigit() else 0)):
            out.append(f"| {cid} | {check_titles.get(cid, '')} | {skipped[cid]} |")
        out.append("")

    if suppressed:
        out.append("## Suppressed by baseline")
        out.append("")
        for f in sorted(suppressed, key=lambda f: (f.check, f.file)):
            out.append(f"- `{f.id}` {f.check} — {f.summary} ({f.file})")
        out.append("")

    return "\n".join(out)
