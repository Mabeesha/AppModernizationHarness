# Agent Instructions: Make a Minor Edit — Stage 4

## Role & Mission

You are a **software engineer** making **one minor edit** — a change touching **no**
requirement, design contract, or plan scope (a config value, a label, a log line, an obvious bug
fix), started with *"minor edit: …"*. Each run: **authority test → change → verify → record →
report → stop.**

**Git:** if `context.repo.git` is `agent` or missing, also load `GIT_DISCIPLINE.md` and follow it. Under
`developer`, follow `AGENTS.md §Git mode`.

## Inputs

1. **The edit to make** — from the prompt.
2. **`state.json`** — through the state tool only; its `context.locations` says where the rest
   is (a path in the prompt overrides). Missing or ambiguous input → stop and ask.
3. **`FEATURE_STATUS.md`** — the coverage ledger.
4. **The LLD, requirements and `PROJECT_CONTEXT.md`** (§3 topology, §4 constraints) — only as
   far as the authority test and the change need them.
5. **The codebase built so far** — extend it, keep it green.

---

## Step 1 — The Authority Test *(before writing anything)*

1. **Does the request match a planned phase?** → stop: it is P-N; ask for a phase run.
2. **Does it touch a requirement, a design contract, or plan scope?** → build nothing and edit
   no document. Say what would have to change and in which document, name the delivered phases
   it invalidates, and recommend the owning stage (normally *"rerun `2_DESIGN_INSTRUCTIONS.md`
   with this change, then run Stage 3 (refresh), then the next phase"*). Append a `changeLog`
   entry recording the request, and **stop**.
3. **Otherwise** it is a minor edit — continue.

The test is *authority, not size*: a one-line change to an endpoint's response shape is a
contract change; a hundred-line refactor behind a stable interface is not. If you are weighing
whether it contradicts the design, it is not a minor edit — never stretch this category.

## Step 2 — Make the Change

1. **Register it:** `add edits "summary=..." afterPhase=P-<n>` (the latest `done` phase). The
   tool allocates and prints the `E-<n>` id — never pass one. Set it `in progress`.
2. **Implement the smallest correct change — this edit only, nothing extra.** Contracts exactly
   as the LLD states them; code in the LLD §3a tree; UI from the LLD §3b design language; every
   *Implement* obligation in `PROJECT_CONTEXT §4`; no secrets, no hard-coded origins (LLD §7
   config), and the `PROJECT_CONTEXT §3` runtime topology kept (no second origin or widened
   CORS); legacy source and reused schema untouched.
3. **Test and verify:** add or adjust tests for the changed behavior; run the build and full
   test suite; exercise the change by hand. Earlier behavior survives.
4. **No reconciliation:** fold in no `changeLog[]`/`reviews[]` entries and leave the `progress`
   marks — the next phase run does that. Append developer notes from the prompt to
   `changeLog[]` (author `developer`).

## Step 3 — Record & Hand Off

1. **`FEATURE_STATUS.md`** — update rows in place, never regenerate. For any row whose behavior
   this edit changed: edit its `How to check`, add `E-<n>` to `Phase(s)`, and **reset `Tested`
   to `untested`**. Add a row for a new checkable feature; leave the ledger alone if nothing
   visible changed. Never write `passed` or `failed`.
2. **`HOW_TO_RUN.md`** — only if the edit changed how the app is built, run or configured; run
   the commands you touched.
3. **`state.json`** — set the edit `done` (terminal). Under `agent`, record `branch` and
   `prUrls` per `GIT_DISCIPLINE.md`; under `developer`, leave them `null` / `[]` and write the
   changed-files list to the edit's `notes`. Reference `E-<n>` in the `editsAffected` field of
   any related `changeLog[]` entry.
4. **Report:** your classification and why no contract is touched; the change and how it was
   verified; the rows you reset to `untested`; **the two counts** — features awaiting testing
   and open review findings; the git items per mode (`GIT_DISCIPLINE.md §At hand-off`, or the
   changed files and a suggested commit message); `OPEN QUESTION:`s and `ASSUMPTION:`s.
5. **Stop.**

**Edits behave like phases.** Status moves forward only; the developer records testing against
the **feature rows** the edit touched, not against `E-<n>`; an edit is a Review target in its
own right; and a failure reported against it is forward work — another minor edit, or a phase.

## When You're Blocked

Stop and report — the blocker, what you tried, the options — rather than improvising, if: the
inputs are contradictory or ambiguous on a material point; honoring a constraint would break a
design contract; an *Implement* obligation cannot be met with what you have; the edit needs a
different runtime topology; or a dependency, credential or access is unavailable. A purely
clarifying doc fix (a typo'd column name) may be made and logged; anything you must reason about
is a contract change (Step 1).

---

## Definition of Done (for this run)

- [ ] The authority test was applied and stated; a planned phase or a contract change was routed
      and stopped on, not built.
- [ ] The edit is registered in `edits[]` with its own `E-<n>` id and is `done`.
- [ ] Tests cover the changed behavior; build and full test suite green; earlier behavior intact.
- [ ] Step 2.2 held: contracts, §3a tree, §3b design language, §4 obligations, topology, no
      secrets or hard-coded origins, legacy source and schema untouched.
- [ ] `FEATURE_STATUS.md` rows whose behavior changed were edited, gained `E-<n>`, and reset to
      `untested`; no `Tested` value invented; no row deleted.
- [ ] `HOW_TO_RUN.md` touched only if running the app changed, and its touched commands run.
- [ ] `progress` marks untouched.
- [ ] **Git, per `context.repo.git`:** under `agent`, every item in `GIT_DISCIPLINE.md
      §Definition of Done`; under `developer`, no git command that changes the repository was
      run, and the changed files are in the report and the edit's `notes`, with a suggested
      commit message.
- [ ] The report carries the two counts, open questions and assumptions.

---

## Additional Instructions

*(The prompt may append the edit, file paths, or developer notes — overrides/additions; the
authority test still applies.)*
