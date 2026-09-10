# Running the Instruction Set Eval

Practical guide. For *why* the checks exist and how they were designed, see
[EVAL_DESIGN.md](EVAL_DESIGN.md).

---

## 1. Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** for dependency and venv management

```bash
uv --version   # confirm it's installed
```

## 2. Setup — once

```bash
cd eval
uv sync
```

That creates `eval/.venv` and installs `tiktoken` (the only runtime dependency).
Everything below is run from the `eval/` directory. `uv run` uses the venv
automatically — you never need to activate it.

Verify:

```bash
uv run run.py --list-checks
```

You should see 25 checks: **18 `implemented`** (deterministic, shipping) and
**7 `stub`** (registered but awaiting the judge harness — C2, C4, D2, E1, E2,
E3, F1). E3 is additionally marked experimental and stays out of any run unless
`--include-experimental` is passed.

---

## 3. The command you'll use most

```bash
uv run run.py --set ../ModernizationHarness --det-only
```

Runs every deterministic check. **No API calls, no credentials, ~2 seconds.**
This is the CI default.

Output:

```
ModernizationHarness  (5e3a2c0)
  checks run : 18  skipped: 0
  findings   : 0 blocker, 0 major, 0 minor  (3 suppressed)
  tokens     : APPROXIMATE via tiktoken:cl100k_base
  report     : /path/to/eval/results/20260731-081530-ModernizationHarness/report.md
```

Open the `report.md` path for the readable version.

---

## 4. Common tasks

| I want to… | Command |
|---|---|
| Check one set, everything deterministic | `uv run run.py --set ../ModernizationHarness --det-only` |
| Just token budgets | `uv run run.py --set ../ModernizationHarness --checks A` |
| Complete the stage-budget table | `uv run run.py --set ../ModernizationHarness --checks A --docs ../instruction_output` |
| Run one group | `uv run run.py --set ../ModernizationHarness --checks B` |
| Run specific checks | `uv run run.py --set ../ModernizationHarness --checks B1 B3 F2` |
| See findings the baseline hides | `uv run run.py --set ../ModernizationHarness --det-only --baseline /dev/null` |
| Write output somewhere specific | `uv run run.py --set ../ModernizationHarness --det-only --out results/today` |
| Prove the checks still work | `uv run tests/fault_injection.py` |

`--checks` accepts check ids (`B1`) and group letters (`B`), mixed freely. An
unknown selector is an error, not a silent no-op — a typo in CI must not read as
a passing run.

---

## 5. Reading the output

Each run writes two files to `eval/results/<timestamp>-<set>/`.

### `report.md` — for humans

1. **Severity summary** — blocker / major / minor counts.
2. **Token budget tables** — per file, per stage composite, and growth vs git HEAD.
3. **Findings** — grouped by check, each with a stable id, a clickable
   `path:line`, an explanation, and quoted evidence.
4. **Skipped checks** — with the reason each was skipped.
5. **Suppressed** — anything hidden by the baseline.

### `findings.json` — for tooling

`meta`, `summary`, `findings`, `suppressed`, `metrics`, `skipped`. Findings carry
a stable `id` (see §6) and a `subject` used for grouping.

### Severities and exit codes

| Severity | Meaning | Effect |
|---|---|---|
| **blocker** | An instruction is unenforceable or contradictory. An agent will do the wrong thing or stall. | **exit 1** |
| **major** | Real inconsistency that will cause drift, but an agent can proceed. | exit 0 |
| **minor** | Hygiene or smell. May well be intentional. | exit 0 |

| Exit code | Meaning |
|---|---|
| `0` | Clean, or findings no worse than major |
| `1` | At least one blocker |
| `2` | Harness error — bad path, unknown check selector, unimplemented tier |

### "Skipped" is not "passed"

A skipped check reports *why*. A set with no `state.json` schema, no numbered
stage files and no artifact template fences skips B1/B3/B5/C1/C3/C5/E4 — there is
nothing for those checks to verify. That is very different from those checks
passing, and the report distinguishes them. The `checks run` count excludes
skipped checks for the same reason.

---

## 6. Working with the baseline

`baseline.json` suppresses individual findings that are deliberate design
choices rather than defects.

Suppression is keyed on a **stable finding id** — `sha1(check + file + subject)`,
deliberately independent of line numbers, so editing a file above a finding does
not orphan its entry. It is **per finding, never per check**: suppressing one
instance can never hide a new one from the same check.

**To suppress a finding:**

1. Get its id from `report.md` (shown in backticks under each finding) or `findings.json`.
2. Add an entry with a real reason:

```json
{
  "suppressed": {
    "f4b0458edb": "B5 — PROJECT_CONTEXT.md §2 (Stacks) is read as prose by every stage, not cited as '§2'. Intentional: narrative context, not an obligation target."
  }
}
```

The reason is not optional in practice — an unexplained suppression is
indistinguishable from a bug being swept under the rug.

**To see what's hidden:** `--baseline /dev/null`.

**Do not baseline a false positive.** If a finding is wrong, the *check* is
wrong — fix it. Five checker bugs were found and fixed this way rather than
suppressed (EVAL_DESIGN.md §11.3).

---

## 7. Token counts are approximate right now

The active backend is **tiktoken**, which is OpenAI's tokenizer, not Anthropic's.
It systematically **undercounts** Claude tokens — typically 15–20% on prose, more
on the heavy Markdown tables in these files.

Every metric is tagged `approximate: true` and the report banners it. **Use these
numbers for relative signal** — growth over time, which stage load-out is
heaviest — **not for absolute budget decisions.**

**To switch to real Claude counts:**

1. Fill in `AnthropicCounter._count_uncached` in `evalkit/tokens.py` (the body is
   in the class docstring — three lines).
2. Move `anthropic` from the `[llm]` extra into the base dependencies in
   `pyproject.toml`, then `uv sync`.
3. Run with `--token-backend anthropic`.

Nothing else changes; every caller goes through the `TokenCounter` interface.
Requires `ANTHROPIC_API_KEY` or an `ant auth login` profile. The token cache is
keyed by backend, so tiktoken results are never served to the Anthropic backend.

### Completing the stage budget table

The per-stage composite splits into **fixed** (instruction files, always
measurable) and **variable** (generated artifacts). Without `--docs` the variable
half reads `unmeasured` — deliberately not estimated.

```bash
uv run run.py --set ../ModernizationHarness --checks A --docs ../instruction_output
```

A partially-measured stage renders as `15,765+` with the missing artifacts named
in a column, so a floor is never mistaken for a total. To close the rows fully,
point `--docs` at a directory holding a complete pipeline run —
`PROJECT_CONTEXT.md`, `state.json`, both designs, the plan, and all three
requirements documents.

---

## 8. Verifying the checks themselves

```bash
uv run tests/fault_injection.py
```

Copies a real set, injects one specific defect per check, and asserts that check
catches it. A check that silently never fires is worse than no check — it reads
as a clean bill of health.

Two distinct failure modes are reported so they are never confused:

- **MUTATION FAILED** — the injected edit did not apply (the source text moved).
  The *case* is broken and proves nothing; repair it in `tests/fault_injection.py`.
- **CHECK SILENT** — the edit applied but the check found nothing. The *check* is
  broken.

It also runs a control pass over the unmodified set, so a check that fires on
everything is caught too.

Run this after touching any check, and in CI. It has already caught two checks
that could never have fired on real input (EVAL_DESIGN.md §11.1).

---

## 9. Adding a check

1. Pick the module in `evalkit/checks/` matching the group (`references.py` for
   B, `hygiene.py` for F, …).
2. Write the function and register it:

```python
from ..model import CheckResult, Finding, Severity
from ..registry import Context, check

@check("B6", "Short title")
def b6_my_check(ctx: Context) -> CheckResult:
    res = CheckResult()
    for doc in ctx.iset.documents:
        ...
        res.findings.append(Finding(
            check="B6",
            severity=Severity.MAJOR,
            summary="One line, states the defect",
            detail="Why it matters and what to do.",
            file=doc.repo_relative,
            line=42,
            subject="stable-grouping-key",   # feeds the finding id — keep it stable
            evidence=["the offending line"],
        ))
    return res
```

3. If it can't run, set `res.skipped = "reason"` — never return silently empty.
4. **Add a fault-injection case** for it in `tests/fault_injection.py` and confirm
   it fires. A check without one is unverified.

Useful `Context` members: `ctx.iset.documents`, `ctx.iset.by_name()`,
`ctx.iset.stage_documents()`, `ctx.docs` (from `--docs`), `ctx.counter.count()`,
`ctx.repo_root`. `Document` gives `.headings` (fenced and unfenced), `.fences`,
`.is_fenced(line)`, `.section_at(line)`, `.has_heading()`.

For a check needing a judge call, pass `deterministic=False, implemented=False`
and return a `CheckResult(skipped="…")` until Phase 3 lands the harness.

---

## 10. CI integration

```yaml
- name: Evaluate instruction sets
  run: |
    cd eval
    uv sync --frozen
    uv run tests/fault_injection.py
    for s in ../ModernizationHarness; do
      uv run run.py --set "$s" --det-only
    done
```

Fails the build on any blocker (exit 1) or harness error (exit 2). Run fault
injection first — if the checks are broken, a clean report means nothing.

To upload the reports, archive `eval/results/`.

---

## 11. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `error: unknown check selector(s): X` | Typo. `--list-checks` shows valid ids and groups. |
| `error: instruction set not found` | `--set` is relative to your shell's cwd. From `eval/`, use `../ModernizationHarness`. |
| `checks run: 0` | Every selected check skipped — read the Skipped table in the report for why. |
| Exit 2 on `--tier behavioral` | Tier 2 isn't built. Blocked on `eval/fixtures/INTAKE.md` (EVAL_DESIGN.md §13.2). |
| Stubs report "needs `--with-llm`" | Expected. The judge harness is Phase 3; `--with-llm` currently just changes the skip reason. |
| Token numbers look low | They are — tiktoken undercounts Claude. See §7. |
| `tiktoken is not installed` | `uv sync` in `eval/`. |
| Results directory growing | `eval/results/` and `.cache/` are gitignored; delete freely. `--no-cache` bypasses the token cache. |
