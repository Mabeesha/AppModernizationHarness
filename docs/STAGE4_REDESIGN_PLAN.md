# Stage 4 Redesign — Implementation Plan

*Status: **plan, not applied.** Written 2026-10-22 for a fresh agent to implement. This is a
**design change** under the root `AGENTS.md` ("Design changes: ask me first"): before editing
anything, show the developer the five decisions in §3 and get a yes on each.*

---

## 1. Goal

Make each Stage 4 run load fewer tokens without changing what gets built:

1. **Split minor edits out** of the phase file into their own small file.
2. **Move git out** of the always-loaded Stage 4 text into a file loaded only when the agent is
   allowed to run git. The developer's current projects forbid agent git (the git tool hangs), so
   they pay ~2,400 tokens per phase run for rules they never use.
3. **Move re-planning out** of Stage 4. Stage 3 becomes the only stage that edits remaining
   phases; Stage 4 only detects that a refresh is needed and stops.
4. **Compact** what remains, without losing rules.

**Baseline to beat** (tiktoken, size checks A1/A3, 2026-10-21): Stage 4 instructions 14,095
tokens; its Git Discipline section alone ~2,400. **Targets:** a phase run's fixed load
(`AGENTS_TEMPLATE.md` + phase file, developer git mode) **≤ 9,500 tokens**; a minor-edit run's
fixed load (`AGENTS_TEMPLATE.md` + edit file) **≤ 4,500 tokens**. Report the measured numbers;
if a target is missed, say so and why — do not cut rules to hit it.

## 2. Ground rules for the implementing agent

- **Read first:** root `AGENTS.md` (repo rules), `docs/DESIGN.md`, `docs/REQUIREMENTS.md`,
  `docs/TOKEN_SAVINGS.md`, then every file named in §5.
- **Order of edits** (root `AGENTS.md`): `docs/DESIGN.md` and `docs/REQUIREMENTS.md` first,
  then the harness files, then the guides.
- **Voice:** harness files (`ModernizationHarness/*`) keep their dense, exact specification
  style. Talk to the developer in plain English.
- **No git that changes state.** Do not branch, commit, push or open PRs. The developer handles
  git. End with a list of changed files.
- **Do not edit** `eval/results/` or `docs/UNGATED_LOOP.md` (historical records).
- **Out of scope:** the prepare/build split (TOKEN_SAVINGS Option 7), exact input paths
  (Option 12), and compaction of any stage other than Stage 4.

## 3. Decisions — confirm with the developer before starting

Each is pre-filled with the recommendation. If the developer chooses differently, adjust §4.

| # | Decision | Recommendation |
|---|---|---|
| D1 | How git is switched off | A new setting **`context.repo.git`: `agent` \| `developer`**, default `agent` (today's behavior). Git rules move to a separate file loaded only under `agent`. *Alternative:* delete git rules entirely — rejected, it removes a working feature for projects that can use git |
| D2 | What `developer` mode allows | **No git commands at all**, read-only ones included (`status`, `diff`, `log` can hang too). The agent never branches, commits, pushes or opens a PR; `branch` stays `null` and `prUrls` `[]`; the hand-off lists changed files and a suggested commit message. The developer commits after each run, before the next |
| D3 | How a minor edit is routed | The developer says "minor edit: …" (routing row in `AGENTS_TEMPLATE.md`). If the phase file receives a request that is not a planned phase and touches no contract, it **loads the minor-edit file and follows it** in the same session — no round trip. The edit file stops and routes back if the request touches a contract or is a planned phase |
| D4 | Re-planning | Stage 4 **detects** refresh triggers and stops: *"Run Stage 3 (refresh) first: <reason>."* It no longer proposes or applies re-slices and never opens `3_PLAN_INSTRUCTIONS.md`. It **keeps** editing the **current** phase's tasks, test guide and exit criteria when reconciliation requires it. Changes affecting only future phases go to `changeLog[]` for Stage 3 |
| D5 | Mid-phase split | Stage 4 still stops at a runnable point and proposes a split. On approval it trims the current phase, records the moved work in `sizeReport.pushedLater` with **`toPhase: null`**, and sets those `FEATURE_STATUS.md` rows to `unscheduled`. **Stage 3's next refresh schedules them** (a new refresh trigger). Stage 4 creates no phase |

**A trigger counts as handled** (D4) when `PLAN_<AppName>.md §3 Plan Revision History` has a row
dated after it. That is how the next Stage 4 run knows Stage 3 has already acted.

**Workflow change the developer must accept:** a design change becomes **three prompts** —
rerun Stage 2, run Stage 3 (refresh), run the next phase — instead of two. Stage 3 can run on a
cheaper model.

## 4. Work items, in order

### W1 — `docs/DESIGN.md` and `docs/REQUIREMENTS.md`

- **New DDs** (next free numbers, from DD-21): the git-mode setting (D1, D2); the Stage 4 split
  into phase and minor-edit files (D3); Stage 3 as sole owner of the forward plan (D4, D5).
- **Amend:** DD-7 (two-prompt flow → three); DD-10 (plan default "no change" now applies in
  Stage 3); DD-14, DD-15, DD-16, DD-17 (apply in `agent` mode only; give the `developer`-mode
  equivalent, e.g. presence of predecessor work checked by files and symbols, without git);
  DD-12 and Q5 (git is the history only where git is used — under `developer`, the developer's
  commits are); the components list; the diagrams at DESIGN.md:54 and :147; the R5 row at :199;
  §5 schema (new `context.repo.git`).
- **REQUIREMENTS.md:** R5 (rolling plan — owner is Stage 3), R6.4 (an edit gets a branch and PR
  only in `agent` mode), R11 (all of it conditional on `agent` mode; add the `developer`-mode
  rules), the stage-output table at :80 ("a PR" → only in `agent` mode), and a new requirement
  for the git-mode setting.

### W2 — `0_INTAKE_TEMPLATE.md` and Stage 0

- Add one intake question in the git section (near 16g–16i): **"Who runs git — the agent, or
  you?"** Follow the intake shape rules in root `AGENTS.md`: one `###` heading, one
  `**Answer:**` line, a `*Default: …*` line (default: the agent), one *Tick one:* list. Mark
  16g–16i as applying only when the agent runs git. Eval check D5 flags shape breaks.
- `0_PROJECT_CONTEXT_INSTRUCTIONS.md`: map the answer to `context.repo.git` in the
  `state.json` schema (§Output 2) and record it in `PROJECT_CONTEXT §3`. Fix the Step 0c
  references at :264 and :675.
- Update `examples/INTAKE_EXAMPLE.md` and `examples/INTAKE_EXAMPLE_BIG_BANG.md`, and every place
  that cites a question id you renumbered.

### W3 — Split Stage 4 into three files

| File | Holds | Loaded |
|---|---|---|
| `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` (existing) | Phase runs only | Every phase run |
| `4_MINOR_EDIT_INSTRUCTIONS.md` (new) | Minor edits only: the authority test, the change, verification, `edits[]`, `FEATURE_STATUS.md`, `HOW_TO_RUN.md` if needed, the report | Minor-edit runs |
| `GIT_DISCIPLINE.md` (new) | Today's §Git Discipline, §Starting From the Right Base, the "work on this branch" case, and the git items from Step 1, Step 2 and the Definition of Done | Only when `context.repo.git` is `agent` |

- Both Stage 4 files say, in one line near the top: *"If `context.repo.git` is `agent`, also
  load `GIT_DISCIPLINE.md` and follow it."*
- Under `developer`, both files state the D2 rules in a few lines: no git commands, `branch`
  null, `prUrls` `[]`, changed-files list plus suggested commit message in the report,
  predecessor work checked by files and symbols.
- Keep each rule in **one** file. Where both Stage 4 files need it, keep it in the phase file
  and have the edit file point to the section — or, if it is already in `AGENTS_TEMPLATE.md`,
  point there.
- **Check the eval:** `eval/evalkit/model.py:89` maps the leading digit to a stage, so both
  `4_*` files become `stage-4`, while `GIT_DISCIPLINE.md` is not a stage file. Confirm no
  check assumes one file per stage, and adjust if one does.

### W4 — Remove re-planning from Stage 4 (D4, D5)

- Replace Step 0c with **"0c. Check whether the plan needs a refresh"**: the same triggers as
  today, plus the D4 "handled" rule. If one applies and is not handled, stop and say which
  trigger and why. Default: "plan unchanged — building P-N".
- Step 0b: "affects future phases only" → append a `changeLog` entry naming the phases; do
  not edit them.
- §When a Change Touches a Contract, step 4: "then run Stage 3 (refresh), then the next phase".
- §When You're Blocked: delete the "unapproved refresh" bullet; rewrite the split bullet per
  D5.
- Hard Rules 9 and 12: Stage 4 does not re-slice the forward plan; it may edit only the current
  phase's tasks, test guide and exit criteria.
- Definition of Done: replace the Step 0c item and the re-slice clauses to match.
- `3_PLAN_INSTRUCTIONS.md`: :30 and :444 (refreshes are now invoked by the developer, after a
  Stage 4 stop or a Stage 1/2 rerun); add the `pushedLater` entries with `toPhase: null` as a
  refresh trigger, and schedule them; check `sizeReport` handling elsewhere in the file.
- `1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md:236` and `2_DESIGN_INSTRUCTIONS.md:358-360`:
  "run Stage 3 (refresh) next, then the next phase".
- `AGENTS_TEMPLATE.md:76` and `:91` (mid-flight changes): Stage 3 owns the forward plan.

### W5 — Compact the phase file

Cut repetition, not rules. Keep the Definition of Done as a **full checklist**: in a long run
it is what catches missed steps (lesson from the earlier tidy).

- **Role & Mission:** phases only; one line pointing to the minor-edit file; shorten the
  "changes mid-flight" callout to its rule.
- **Inputs, item 3:** the "testing state is irrelevant" and "review findings do not block"
  paragraphs repeat §When You're Blocked "Not blockers". Keep them once, there.
- **Building From a Reference Implementation:** condense to its rules (LLD §3c is the contract;
  the two failure modes; a sample is never a requirement; missing §3c is a design gap).
- **Re-running a Phase That Failed Testing:** condense to the four steps and the "never reopen"
  rule.
- **Step 2 report:** remove the git items (they move to `GIT_DISCIPLINE.md`); merge items that
  restate the Definition of Done.
- **Hard Rule 11:** keep the legacy read-only rule; move "you may branch and commit in that
  repo" to `GIT_DISCIPLINE.md`.

### W6 — The rest of the harness

- `AGENTS_TEMPLATE.md`: routing table — add "minor edit", "small fix", "edit:" →
  `4_MINOR_EDIT_INSTRUCTIONS.md`; Invariant 6 (:119-120) and the merge / no-PR rows (:142-151,
  :162-165) apply only under `agent`, with one line for `developer`. Do not grow the file.
- `5_REVIEW_INSTRUCTIONS.md:92`: the `git log` check on the ledger applies only under `agent`;
  under `developer`, compare against `changeLog[]`. Check how Review finds what an edit or a
  phase changed when there is no branch or PR, and fix it.
- `tools/state.py`: if `check` validates `context`, accept `repo.git` ∈ {`agent`,
  `developer`}; confirm `sizeReport.pushedLater[].toPhase` may be `null`. Add tests in
  `eval/tests/test_state_tool.py` for anything you change.
- `install.sh` / `install.ps1`: confirm they copy the two new files; keep the two in step.

### W7 — Eval

- `eval/evalkit/checks/size.py` (stage map at :33-67): give Stage 4 two composites — phase run
  and minor-edit run — and show the git file as an optional add-on, not a fixed load.
- Update `eval/README.md` and `eval/EVAL_DESIGN.md` to match; check `eval/baseline.json`.

### W8 — Guides

`DEVELOPER_GUIDE.md` (:82, :92, :261, :273, :390, :429, :457, :674, :721), `USE_CASES.md`
(:114, :322, :373, :510, :531, :666, :673, :695), `README.md`: the three-prompt design-change
flow, minor-edit routing, the git setting, and "commit after each run" under `developer`.
`docs/TOKEN_SAVINGS.md`: move Option 9 and the git change to §2 "Already applied", and note
that Step 0c's re-planning now lives in Stage 3.

## 5. Verification

1. From `eval/`: `python tests/test_state_tool.py` — all pass.
2. From `eval/`: `uv run run.py --set ../ModernizationHarness --baseline baseline.json` — no
   blocker; read every major (D5 intake shape included).
3. From `eval/`: `uv run run.py --set ../ModernizationHarness --checks A --docs
   ../samples/employee-search/reference-output` — report Stage 4 fixed load before and after,
   for a phase run and a minor-edit run, against the §1 targets.
4. **Stale-reference sweep:** search the repo (excluding `eval/results/` and
   `docs/UNGATED_LOOP.md`) for `Step 0c`, `§Git Discipline`, `§Minor Edits`, `Starting From the
   Right Base`, `Re-running a Phase`, `prUrls`, `branch`, `re-slice`, `retrofit`, and every
   moved section name. Each hit must point at the right file and match the new rules.
5. **Rule inventory:** list every rule in the old Stage 4 file (Hard Rules, Definition of Done
   items, blocker list) and show where each now lives — or that it was removed on purpose per
   §3. No rule may disappear silently.

## 6. Hand-off report

In plain English, for the developer:

- The decisions as applied (D1–D5), and anything that differed from this plan.
- Token numbers before and after (§5.3).
- The rule inventory (§5.5), or where to find it.
- Test and eval results, with any findings.
- Every changed file. No git was run; the developer commits.
- Anything left undone, and any mismatch between documents found along the way.
