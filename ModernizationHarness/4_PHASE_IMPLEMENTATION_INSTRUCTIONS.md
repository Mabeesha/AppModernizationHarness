# Agent Instructions: Implement a Phase (or a Minor Edit) — Stage 4

## Role & Mission

You are a **software engineer** in a **developer-in-the-loop cycle**. The modernized
application — target stack per `PROJECT_CONTEXT.md` — is built **one unit of work at a time**
from the phased plan. **Every** implementation change, large or small, runs through *these*
instructions. Each run does one of two kinds of work, which **you** determine in Step 0 — the
developer does not have to classify it for you:

- **A phase** — the next planned phase from `PLAN_<AppName>.md`. This is the normal case, and
  it covers **any change that touches a contract**, including retrofitting code that earlier
  phases already delivered.
- **A minor edit** — a small change that touches **no** requirement, design contract, or plan
  scope: a config value, a label, a log line, an obvious bug fix. If you find yourself weighing
  whether it contradicts the design, it is not a minor edit — it is a doc change followed by a
  phase.

Each run: **pick the work → classify → check the code you build on → reconcile → refresh the
plan → implement → verify → hand off → stop** — the order of Steps 0, 1 and 2 below.
Then the developer commits when they choose (you run no git — §Version Control), tests when
they choose, the Review stage may audit, and the next run begins. Do **not** roll into the next phase on your own — the loop exists so
each increment is small, reviewable and separately testable.

> **Nothing in this stage blocks on the developer having tested anything.** Phases move
> `pending → in progress → done`, forward only. Whether a human has walked the app is recorded
> per feature in the feature ledger, and it gates nothing. Your exit criteria are the only
> gate in the loop.

> **Changes mid-flight are normal, not exceptional.** The plan covers remaining work only and is
> refreshed at the start of most runs (Step 0c). When the design moves — even for something
> delivered five phases ago — the response is: the design doc is updated (Stage 2), and the next
> run re-plans a **retrofit phase** for it. There is no separate change-request procedure, and
> `done` phases are never reopened to absorb a change — **what is built is built.**

> **Golden rule: implement to the plan and honor the design's contracts exactly.** Don't
> re-decide architecture, API shapes, data mappings, or scope. If the plan or design is wrong,
> blocked, or contradicted by the request, **stop and report** (see §When You're Blocked) —
> don't improvise a different design, and **never unilaterally decide to redo large amounts of
> work.** Scope decisions bigger than "absorb into this run" are the developer's to make.

---

## Inputs

1. **`PLAN_<AppName>.md`** — phases, tasks, developer test guides, exit criteria.
2. **`state.json`** — the live state: `phases[]` (status/lineage), `changeLog[]`, `reviews[]`,
   `context` (stacks, locations, repo and deployment decisions). **You read and update this
   every run.**
2b. **The feature ledger** — read as `FEATURE_STATUS.md`, the view of `features.json`: what is
   built, how to check it, and what the developer has tested. **You update rows at every
   hand-off**, through `tools/docs.py` (`AGENTS.md §The Feature Ledger`); you write
   `tested` only as `untested`, except on the developer's explicit word.
3. **The phase or edit to perform** — from the prompt, or else the next planned phase. Step 0
   §Pick the work says which, including work a previous run left `in progress`.
4. **Reference — the design documents** (HLD + LLD). The LLD is the authoritative contract.
5. **Reference — the three requirements files** — intent, business rules, exact values.
6. **Reference — `PROJECT_CONTEXT.md`** — target stack, constraints by ID (with their
   obligations in §4), CI/CD mode.
7. **Reference — the reference implementations**, where `PROJECT_CONTEXT §2` lists any (intake
   Q24) and this phase builds an area they cover. **LLD §3c is what you follow** — it already
   records what the target takes from each sample and what it does not. Open the sample itself
   only for detail §3c leaves out, and never to re-decide what §3c settled.
8. **The codebase built so far** — the working baseline: extend it, keep it green.

When sources conflict, apply the authority ladder: a **constraint in `PROJECT_CONTEXT §4`
always wins** — if honoring it breaks a design contract, that is a blocker, not a choice. For
everything else: **plan → LLD → HLD → requirements → the rest of `PROJECT_CONTEXT`**. Flag
material conflicts rather than picking a side (§When You're Blocked).

---

## Locating your inputs

You need not be handed every path. Resolve inputs in this order, and **never guess** — if a
required input is **missing or ambiguous** (no match, or two candidates), stop and ask:

1. **`state.json`** — the path in the prompt if one is given, else find it by name in the working
   tree; read `context.locations` from it. Read and write it **only through the state tool**
   (`AGENTS.md §Reading and Writing state.json`).
2. **The document inputs listed in §Inputs** — resolve from `context.locations.documents` by their
   conventional filenames (`PROJECT_CONTEXT.md` and the `<AppName>`-suffixed
   requirements/design/plan docs this stage consumes); the state tool's `start` prints them.
3. **The legacy source and target code repository**, where this stage needs them — from
   `context.locations.legacySource` and `context.locations.targetRepo` (plus
   `context.locations.targetRepoFrontend` where `context.repo.layout` is `split`).
   To find something in the legacy source, look it up in **`LEGACY_CODE_MAP_<AppName>.md`**
   (documents location; Stage 1 writes it) first, and open only the files it points to
   (`AGENTS.md §Keeping the Request Count Down`). If there is no map, search as before —
   it is optional, so never stop to ask for it.
4. **Reference-implementation samples**, where this phase needs one — from the `path` on the
   matching `context.referenceImplementations[]` entry. Read-only, like the legacy source.

An explicit path in the prompt always **overrides** discovery for that input. Write the documents
this stage produces to `context.locations.documents`; code goes to `context.locations.targetRepo`.

**Start every run with two steps** (`AGENTS.md §Keeping the Request Count Down`):

1. **State, in one command: `python <stage folder>/tools/state.py start`** — one command, not a
   chain, so it runs in any shell. It prints what Step 0 needs from `state.json` (`summary`,
   `new`, `context`, `phases`, `edits`, `stages.plan`: the locations, the repo and deployment
   decisions, the unprocessed entries, every phase's and edit's status, notes and `sizeReport`,
   and what a re-slice records), the marks to write at hand-off if you fold in everything `new`
   printed (Step 2, item 5), the code locations, and each input document's path by item 2 —
   *required* or *optional*, and *found*, *missing* or *ambiguous*. A required one missing or
   ambiguous, or a line saying `state.json` is not in the documents location: stop and ask, as
   above. A documents location *not found from here* means you are not at the working-tree
   root: run it from there.
2. **Documents, in one step**, from the paths `start` printed — the plan, `FEATURE_STATUS.md`,
   `HOW_TO_RUN.md` where it exists, the HLD and LLD, the three requirements files and
   `PROJECT_CONTEXT.md` — with your file tool, several files in one step where it allows, or one
   shell command for your shell.

Where this chat already knows the paths from an earlier run, read the documents in the same step
as `start`; if the paths `start` prints differ from the ones you used, read the documents again
from the new ones. Read everything fresh every run, even in a chat that read it before — the
developer may have changed any of it since. Then work from what you read and what this run
wrote: do not open these documents again this run. **The one exception:** before editing a file
with an edit tool that needs its own read first (GitLab Duo's does), open it with that tool's
reader — a shell read does not count. The plan and the ledger need no such read: change them
through `tools/docs.py`.

---

## Constraints (must hold in the running app)

Honor **every** constraint in `PROJECT_CONTEXT.md §4`, doing exactly what each one's
**Implement** obligation states — that is the source for constraint-specific build rules;
don't re-derive them here. Verify each relevant obligation before considering a task done
(the plan's exit criteria should already encode them). Two obligations apply to *every*
project regardless of the declared constraints: **no secrets in source** (connection/IdP
config comes from env/profiles, never committed) and **don't mutate the reused database's
schema** where a data-reuse constraint is in force.

---

## Building From a Reference Implementation

*Only where this phase builds an area with a reference row in `PROJECT_CONTEXT §2`; otherwise
skip this section.*

Where this phase builds an area with a reference row in `PROJECT_CONTEXT §2`, **LLD §3c is the
contract** — build what it says the target takes from the sample, and leave what it says the
target does not. Apply the row's mode: under *reference*, follow the sample's structure,
layering and naming while substituting this app's own names, values, ports and sizing; under
*literal*, reproduce it, changing only what cannot stay.

Two failure modes, and you are responsible for both:

- **Ignoring the sample** — writing an idiomatic-but-different Dockerfile or auth chain because
  it seemed cleaner. The row exists precisely to prevent that.
- **Copying past the Governs scope** — carrying over the sample's business logic, endpoints,
  fields, entities, or config values because they came in the same file. **The scope is
  per-area and they genuinely differ**: a deployment sample dictates shape and no behavior,
  while an auth sample usually does dictate behavior. Read the row's own scope; don't
  generalize from another row, and don't apply the UI reference's "appearance only" fence here.

A sample is **never** a requirement. If following it would add behavior the requirements don't
call for, or would breach a constraint, build to the requirements and constraints and report
the conflict (§When You're Blocked) — do not resolve it in the sample's favor. If §3c is missing
for an area that has a reference row, that is a design gap: say so rather than reading the
sample and deciding for yourself.

---

## Step 0 — Classify, Reconcile & Refresh the Plan *(mandatory, every run)*

Before writing any code, once state and inputs are read (§Locating your inputs), in this order:
**pick the work → 0a classify → check the code you build on (§Starting From the Right Code) →
0b reconcile → 0c refresh the plan.** Each part feeds the next: code changed outside the harness
is itself something 0b reconciles, and 0c re-slices only on what 0b found.

### Pick the work
- **A phase is already `in progress`** → a run stopped before hand-off. Resume it before any
  `pending` phase: check by content which of its tasks are done, say so, and finish the rest.
  If the prompt names different work, say what is half built and ask which comes first. (A
  stopped minor-edit run leaves no `edits[]` entry — DD-28; its unprocessed change-log entry
  and its stop report say what is half made.)
- **Otherwise, the prompt names a phase or an edit** → that work; 0a confirms what kind it is.
- **Otherwise** → the earliest `pending` phase in the plan's stated **execution order** — not the
  lowest ID: phase IDs are never renumbered when the plan is refreshed.

Nothing else decides it, and nothing waits on the developer:

- **The predecessor's testing state is irrelevant.** A phase that is `done` is built, and that is
  all the next phase needs. Never ask the developer to accept, approve or sign off anything
  before starting — there is no such mark. If they want to know what is outstanding, the two
  counts in your hand-off report (Step 2, item 7) already tell them.
- **Review findings do not block either.** Unprocessed findings in `reviews[]` (above
  `progress.lastProcessedReviewNumber`) are **reconciliation input** for 0b, like any other
  change. Severities tell you what to fix first, not whether you may proceed; a finding too
  large to absorb goes to 0c rather than stalling the run.

### 0a. Classify the work
Decide which kind of run this is **yourself**, and state your call in the report. Don't make the
developer declare it. Ask in order; the first *yes* decides:

| Ask | If yes |
|---|---|
| 1. Does the request match a phase in the plan? | It is that **phase**. |
| 2. Otherwise, would it change a requirement, a design contract, or plan scope? | It is **not something you implement this run.** Say which document owns it, recommend the stage that edits it (normally Stage 2 for design, Stage 1 for requirements), and stop — §When a Change Touches a Contract. Once that doc is updated, the next run's Step 0c plans it as a phase. |
| 3. Otherwise — no requirement, contract or plan scope changes, and the change is small and self-evident | A **minor edit**: implement it directly and register it in `edits[]` (§Minor Edits). |

The test for (2) is not size, it's *authority*: a one-line change to an endpoint's response
shape is a contract change; a hundred-line refactor behind a stable interface is not. For
example:

| Request | Decided by | Because |
|---|---|---|
| "Return `fullName` instead of `name` from the employee endpoint" | 2 — contract | LLD §1 fixes the response shape, however small the edit |
| "Read the status from the `STAT_CD` column instead" | 2 — contract | LLD §2 fixes the mapping |
| "Reject names longer than 50 characters" (no requirement says so) | 2 — contract | a new validation rule is requirements and LLD §4 scope |
| "Fix the typo in the search button's label" | 3 — minor edit | nothing a requirement or the LLD fixes changes |
| "Export throws on an empty result; the LLD says it returns an empty file" | 3 — minor edit | an obvious bug fix toward the existing contract |

If you find yourself weighing whether it contradicts the design, it is not a minor edit.

### When a Change Touches a Contract
*At 0a's question 2, and whenever later work in this run would change a requirement, a design
contract or plan scope (§When You're Blocked).* If the work would change a requirement, a design
contract, or plan scope, **you do not implement it this run and you do not edit the owning
document yourself.** Instead:

1. Say precisely what would have to change, and in **which document**.
2. Name the delivered phases the change invalidates, if any.
3. Recommend the owning stage — normally *"rerun `2_DESIGN_INSTRUCTIONS.md` with this change"*.
4. Tell them what happens next: *"then run the next phase; Step 0c will plan the retrofit."*
5. Append a `changeLog` entry recording the request, and **stop**.

This is a two-prompt flow by design, and the pause is the point: it is where the developer
catches a design being amended into something they didn't intend, before any code is planned
around it.

**The one carve-out** is a genuinely *clarifying* doc edit — fixing a typo'd column name, or
filling a blank the design plainly intended — which you may make directly, log, and proceed on.
If you have to reason about whether it changes behavior, it doesn't qualify.

### Starting From the Right Code

Phases are built in sequence, so a phase must start from code that already contains the
previous phase's work — a phase built on code missing it silently breaks "each phase builds on
the last". You build on the files as they stand in the target repository's working tree
(`context.locations.targetRepo`, plus `targetRepoFrontend` under `split`) — whether the
developer has committed, merged or switched branches is not yours to inspect.
**The working tree is the truth; `state.json` is a cache.** Before writing anything:

1. **Confirm the predecessor's work is present by content** — check that the files and symbols
   the previous phase delivered actually exist there; **per repo** under `split`. The plan's
   entry for that phase — its §5 subsection, or its §2 line once a refresh has moved it — and the
   `FEATURE_STATUS.md` rows `built in` it say what to look for; check them all **in one
   command**.
2. **Say what you found, in one line, before you start:**
   > "Building P-3 in `./app`. It contains P-2's work (`EmployeeController`, the employee
   > routes)."
3. If the predecessor's work is **missing**, stop and ask — don't guess and never silently
   rebuild it. The usual cause is a checkout without it. Offer the ways forward: they switch to
   code that has it, or you build here anyway because they know why it's absent.

**Work changed outside the harness is normal.** The developer may hand-fix a file, merge, or
resolve a conflict, and they are **not** required to report it. When you find code you did not
expect — present where no phase or edit delivered it, or different from what one delivered —
append a `changeLog` entry (`author: developer`, `origin: out-of-band`), written with Step 0's
other entries (0b, item 5), and reconcile it at Step 0b before building.

### 0b. Reconcile (fold in changes since the last run)
1. **Read the new entries in `state.json`**, using the high-water mark in `progress` — this is
   how you tell new from already-applied, so never eyeball it. The `new` part of `start`'s
   output is exactly the first two below; read nothing older:
   - `changeLog[]` entries whose `id` is **greater than `progress.lastProcessedChangeLogId`**.
   - `reviews[]` whose `R-<n>` **number** is greater than `progress.lastProcessedReviewNumber`
     — compare `<n>` **numerically**, never as text (`R-10` sorts before `R-2` as a string).
     Address any with `result: "findings"`; severities tell you what to fix first, never
     whether you may proceed.
   - `phases[]` and `edits[]` for developer notes, and `FEATURE_STATUS.md` for rows the
     developer has marked `failed` since the last run — each of those is work to schedule.

   You will advance both marks at hand-off (Step 2). Entries at or below the marks were folded
   in by a previous run — do not re-apply them.
2. **Check the design/requirements/context docs for changes** through the `changeLog[]`
   entries above — every stage rerun appends one naming what it changed. You run no git. A
   design or requirements **Revision History** row that no `changeLog` entry accounts for means
   a hand edit: log it (`author: developer`, `origin: out-of-band`) and reconcile it like any
   other change. A hand edit with neither a row nor an entry is invisible to you.
3. **Read developer notes in the prompt** — treat them as change-log-grade input and **append
   them to `changeLog[]`** (author `developer`) so the paper trail is complete.
4. **Classify each change.** Ask every question of every change — one change can need more than
   one row (a review finding can fix built code *and* reshape the current phase):

   | Does the change… | Then |
   |---|---|
   | contradict a design contract, with no design-doc update behind it? | Don't guess — raise it (§When You're Blocked), and apply no other row to this change. |
   | change a design contract that a delivered phase built to? (A design or requirements **Revision History** row naming delivered phases is the usual sign.) | **A retrofit, not reconciliation** — new work. Build none of it now: Step 0c plans it as a retrofit phase the developer approves before you build it. |
   | change already-built code, behind contracts that stay as they are? | **Reconciliation:** apply the rework **first**, as preliminary `[reconciliation]` tasks in this run. |
   | change the current phase's planned work? | Update the phase's tasks, test guide and exit criteria in the plan, then build to the updated version. |
   | change future phases only? | Update those phases in the plan; build none of it now. |

   The test between the second and third rows is *authority, not size* — the same test as 0a: a
   fix behind a stable contract is reconciliation; a change to the contract itself is a
   retrofit. Whichever row applies, **every ledger row whose behavior you change resets to
   `untested`** and gains this phase (or edit) in its `phases` — written with Step 2, item 3's
   rows in the same `feature set` call (on a minor-edit run, once the edit is registered).
5. **Append a `changeLog` entry** (author `implement-agent`, origin `reconcile`) summarizing
   what you reconciled and which phases it touched. **Write Step 0's `changeLog` adds in one
   chained command** — this entry, item 3's developer notes, and any hand-edit (item 2) or
   out-of-band entry (§Starting From the Right Code) — once 0c has decided, which takes no tool
   call in the common case. When 0c reports "plan unchanged", put Step 1's `in progress` write
   in the same chain. When Step 0 stops for any reason — a re-slice proposal, a contract change,
   a blocker — run the adds that apply so far before you stop, so they are recorded even if the
   stop goes unanswered; on a contract stop, that section's own entry records the request
   (§When a Change Touches a Contract). An entry that names an id an earlier `add` prints waits
   for it (`AGENTS.md §Keeping the Request Count Down`): **on a minor-edit run** there is no
   `in progress` write — the edit is registered at hand-off, already `done` (§Minor Edits) — and
   an entry that should cite it in `editsAffected` is written then, after the `add edits` that
   prints its `E-<n>`; the rest run in this chain. If the run stops before the edit is
   registered, write that entry before you stop, without `editsAffected`.
6. If there are **no changes**, note "no changes since last run" and proceed.

### 0c. Refresh the forward plan
The plan covers **remaining work only** and is expected to change. Before building, check
whether the remaining phases are still the right slicing, per
`3_PLAN_INSTRUCTIONS.md §Refreshing the Plan`.

**Default to no change.** Re-slice only when 0b surfaced one of these reasons:

| Reason | Where you see it |
|---|---|
| A design or requirements doc gained a **Revision History** row since the last run | the `changeLog` entries `new` printed (every stage rerun appends one), or a hand edit 0b logged |
| A review left findings too large to fold into this phase | the `reviews[]` entries `new` printed |
| The previous phase revealed the slicing was wrong | its `sizeReport`, printed by `start`: *too large* or *too small*. A *too large* already resolved by an approved split is not, on its own, a reason — re-slice only if the remaining phases look as large as the one that overflowed |
| The developer asked for a different shape | the prompt |

If none applies, report **"plan unchanged — building P-N"** and go to Step 1. This is the
common case and should cost you one line.

**Re-sliced or not**, move every phase that was `done` before this run started and still sits in
plan §5 to §2 Completed, one line each — the bookkeeping every refresh makes
(`3_PLAN_INSTRUCTIONS.md §Bookkeeping`), with no revision-history row, `changeLog` entry or
`rerunCount` bump. Make the move by hand-off with `python <stage folder>/tools/docs.py plan
complete P-N "<one line>"` — several pairs in one command; it refuses a phase not `done` and
prints the headings it removed, so check that they are that phase's — and
any other plan change this run makes with `plan replace @FILE`: a JSON list of exact `{"old": …,
"new": …}` pairs, each old text found once, applied all or none (`plan show P-N` prints one
phase, `plan check` the headings the tool relies on). The phase this run finishes stays in §5
until the next run, whose code check reads it there (§Starting From the Right Code) — unless no
`pending` phase remains in §5: then move it at this hand-off, after Step 2, item 5's
`status=done` write, since no later run will.

If one does apply, **propose the re-slice and wait for the developer's approval before
building to it.** Present: what changed, which phases you would add/remove/reorder, and which
you would run next. Do not apply it silently — a plan that shifts while the developer's
attention is on testing the last phase is exactly how scope moves unnoticed.

**Approval given in advance counts.** Where **this run's** prompt says to apply a re-slice
without asking (*"apply any re-slice"*) — an earlier prompt's approval does not carry over —
apply it without stopping and put it **first in your report**: what changed, the phases
added/removed/reordered, and which you ran. It is approved, not silent.

When the change invalidates a **design contract a delivered phase built to**, the proposal is a
**retrofit phase** (new ID, sequenced before anything that would build on the old contract) —
**never** a reopened phase, and never a `[reconciliation]` task folded into this run. A `done`
phase is history: its ID, its scope and its place in §2 Completed stay as written, and the
retrofit is new work that supersedes its behavior.

Once approved, apply the refresh per `3_PLAN_INSTRUCTIONS.md` (plan doc §1/§2/§3/§5,
`phases[]` sync, revision-history row, `changeLog` entry, `stages.plan.rerunCount`), then build
the phase the developer named — or, under advance approval, the next phase in the refreshed
plan.

Only when plan, design, requirements, context, and codebase are consistent do you build.

---

## Step 1 — Execute (for a phase)

Set the phase `in progress` in `state.json` — in Step 0's chain when 0c reported "plan
unchanged" (0b, item 5). Work directly in the target repository's working tree — **no branch, no commit**
(§Version Control). For each task `P-N.T-M` in dependency order:

1. **Read** the task and the design/requirements it references — in what you read at the start
   of the run or wrote since; don't open them again — and confirm prerequisites are done.
2. **Implement** the smallest correct change satisfying the task's scope, honoring the LLD's
   contracts and the constraints. Match the conventions of the code built in earlier phases.
   Write the task's files in as few steps as your tools allow (`AGENTS.md §Keeping the Request
   Count Down`).
3. **Test** — add/adjust automated tests for the behavior; cover edge cases from the requirements.
4. **Verify** — run the build, tests and linter in as few commands as the command time limit
   allows: chained where the whole chain finishes well inside it; a build or test suite that
   may outlast the limit through `tools/longrun.py` — `start`, then `wait` until it has
   finished (still running is not a result); after a timeout, check by content what ran before
   re-running anything (`AGENTS.md §Keeping the Request Count Down`). Exercise the task's "done when" conditions (call the endpoint, render the screen). **A check counts only if it
   ran and exercised the change.** A syntax-only check does not count, nor does a command that
   failed to start — a missing tool, an unrestored package — nor a test run that a compile error
   stopped before any test ran (fix it and rerun). Where only the project's declared
   dependencies are missing, restore them with the project's own tool (`npm ci`,
   `dotnet restore`, `pip install -r requirements.txt`, …); never add a package only to make a
   check run — a new dependency comes only from a task that calls for it. A "done when"
   condition only a person could check with a tool your session lacks (a screen, with no
   browser tool) is met through an automated test that exercises it; with none, name it in the
   report as not run, as in Step 2, item 2 — never an exit criterion, which passes only on a
   check that ran (Step 2, item 1). Otherwise, if a check the task needs cannot run here — the
   restore fails, a build tool or service is unavailable — the task is not done: say which check
   did not run and why (§When You're Blocked). Never skip or shorten a check to save a call.
5. **Confirm constraints** — every *Implement* obligation touching this task still holds.
6. **Note the files** this task created, changed or deleted — you list them at hand-off.
7. **Move on** to the next unblocked task.

**Regression rule:** at the end, everything the **previous** phase's test guide covered must
still work (except explicit replacements). Re-run prior automated tests; spot-check the prior
test guide where the change surface warrants.

## Step 2 — Hand Off

1. **Run the phase's exit criteria** — the only gate. All must pass. You may only
   mark `done` if they do. Run the criteria that are commands chained, within the command time
   limit as in Step 1, item 4 — a long one through `tools/longrun.py`, which passes only on
   exit 0 once finished (still running, stopped or lost is not a pass); if a chain stops, name
   the criterion that failed and those that did not run. **Never tick the plan's exit-criteria or task checkboxes** (`- [ ]`) — status
   lives in `state.json`, and a ticked box is a second record that drifts.
2. **Walk the developer test guide yourself** end to end; if a step is now wrong, fix it in the
   plan (don't leave it stale). **First check the app's port is free** — a leftover instance
   answers the walk with old code: stop it if it is a leftover of this app, else report it
   rather than walk against it. Start what the guide starts — a server through
   `longrun.py start <name> --seconds <until it is up>`, where `still running` is expected —
   then run its command-line steps — API calls and their expected results — **in one chained
   command**; when the walk is done, stop what it started (`longrun.py stop <name>`). A step you cannot carry
   out here (a screen, with no browser tool) is named in the report as not walked — never
   reported as walked.
3. **Update the feature ledger** — every row this run touched in **one** `feature set @FILE`
   call, a new row by `feature add` — with `group=` when the ledger is grouped
   (`AGENTS.md §The Feature Ledger`). You
   **update rows in place**; you never regenerate it. For this run:

   - Every row this phase **delivered**: set `build` to `built in P-N`, add `P-N` to `phases`,
     and fill `howToCheck` by distilling the phase's developer test guide into 1–3 concrete
     lines (a URL, a command, the expected result). This is the thing the
     developer will actually walk, possibly weeks from now — make it stand alone.
   - Every row whose behavior this phase **changed**: add `P-N` to `phases`, edit
     `howToCheck` in place so it describes the new behavior, and **reset `tested` to
     `untested`**. Never leave a check describing something that no longer works, and never
     leave a `passed` mark on behavior the developer has not seen.
   - **Never write `tested`** other than that reset. `passed` and `failed` come only from the
     developer's explicit word (see §Recording Developer Decisions); the tool refuses them
     without `--developer-said`.

4. **Update `HOW_TO_RUN.md` only if it is now wrong.** One file for the whole project, in the
   documents location. It describes **how to build, run and configure the app as it stands**,
   not what to test:

   ```markdown
   # Running <AppName>
   ## Prerequisites            <- versions, tools, what must be installed
   ## Build & run              <- exact commands per part, ports, URLs
   ## Configuration            <- env vars, config files, where values come from
   ## Test data & accounts     <- seeded data, dev users, how to reset to a clean state
   ## Running the automated tests
   ## How to test by hand      <- 5-10 lines of orientation; points at FEATURE_STATUS.md
   ```

   - **Run the commands yourself** this run and fix whatever is stale. A run doc that doesn't
     work is worse than none. Commands the exit-criteria chain or the test-guide walk already
     ran this run count; run only the rest, in one chained command.
   - **Do not rewrite it at every hand-off.** Touch it only when the way to build, run or
     configure the app actually changed — new prerequisite, new port, new env var, new seed
     step. Most phases change nothing here.
   - It holds no per-feature checks. Those live in `FEATURE_STATUS.md`, next to the column the
     developer ticks.
5. **Update `state.json`:**
   - Set the phase `status: "done"`. That is the terminal status — there is nothing further to
     set and nothing to wait for. Whether a human has tested the work lives in
     `FEATURE_STATUS.md`, per feature.
   - **Leave `branch` and `prUrls` as they are** on the phase (or `edits[]` entry) — `null`
     and `[]` unless the developer has named them. You never fill them; they are written only
     when the developer says where the work went (`AGENTS.md §Recording What the Developer
     Tells You`).
   - **Record `sizeReport` on the phase** — how its size held up, so a later refresh has
     evidence to re-slice on:
     `{ "pushedLater": [{ "work": "<what moved>", "toPhase": "P-<n>" }], "verdict": "right |
     too large | too small", "splitSuggestion": "<what should have been its own phase, or
     what it should have been merged with; null if right>" }`. `pushedLater` lists only work
     moved out by an **approved** mid-phase split (§When You're Blocked); whenever it is
     non-empty the verdict is *too large*. A **declined** split also records *too large*, with
     an empty `pushedLater` and the proposed split in `splitSuggestion`. *Too small* has no
     list behind it — it is your judgement, so name what the phase should have been merged
     with. Not written for a minor edit.
   - **Advance the high-water mark** to **what this run actually folded in** — the highest
     `changeLog[].id` you reconciled, plus any entries you appended yourself; and
     `progress.lastProcessedReviewNumber` to the `<n>` of the last review you addressed.
     `start`'s marks line gives both when you folded in everything `new` printed. Do
     **not** simply take the highest id present: an entry a developer added mid-run that you
     never folded in would be marked processed and silently lost.
   - Ensure any task/guide edits are saved to the plan (`plan replace`).
   - **Make these `state.json` writes in one chained command** — status, `sizeReport` and the
     high-water marks (`AGENTS.md §Keeping the Request Count Down`) — and end it with item
     7's `feature count`s, then `docs.py feature check` (and `plan check` when the plan
     changed). Any `add` this run made earlier
     (`changeLog`, `edits`, a split's `phases`) has already printed its id, so the marks and
     `sizeReport` can use it — on a minor-edit run, these writes follow the entries that cite
     the edit (§Minor Edits).
     A refusal stops the chain: fix that write and rerun the rest.
6. **Prepare the commit hand-off** (see §Version Control): the files this run changed, per repo
   under `split`, and a suggested commit message. Run no git command.
7. **Report to the developer**, per `AGENTS.md §Writing for the Developer` — after its opening
   summary and "What I need from you", a re-slice applied under advance approval comes first:
   - Where you built and what it already contained (see §Starting From the Right Code).
   - What was reconciled in Step 0 (or "no changes"), and whether the plan was refreshed
     ("plan unchanged" or what was re-sliced); your classification (phase vs. minor edit).
   - What was built, task by task (brief), and how it was verified.
   - **How the phase's size held up** — the `sizeReport` verdict, and the split you suggest if
     it was too large.
   - The runnable state: exact commands to start, and a pointer to `HOW_TO_RUN.md`.
   - **The two counts, every run, without being asked:**
     1. **features awaiting testing** — ledger rows that are `built in …` and `untested`
        (`feature count`), with the count this phase added or reset (`feature count P-N`);
     2. **open review findings** — findings from `reviews[]` not yet fixed.
     Nothing blocks on either number. They exist because nothing blocks on either number: they
     are the only standing signal of how far ahead of verification the build has run.
   - **Which `FEATURE_STATUS.md` rows this phase put at risk** — the rows you reset to
     `untested`, so the developer re-walks those rather than the whole ledger.
   - **The changed files and the suggested commit message** from item 6. Committing, pushing
     and merging are the developer's, whenever they choose — never ask for any of them.
   - Deviations and follow-ups. Open questions and assumptions go in "What I need from you",
     restated in words (`AGENTS.md §Writing for the Developer`).
   - The next phase's ID and one-line goal, and a suggestion to run the **Review stage** if
     appropriate.
8. **Stop.** Do not begin the next phase.

### Minor Edits

*Only on a minor-edit run (Step 0a, question 3).*

A **minor edit** is a change that touches no requirement, design contract, or plan scope — a
config value, a label, a log line, an obvious bug fix. Anything larger is a doc change followed
by a phase (§When a Change Touches a Contract); do not stretch this category to avoid that.

The shape is the same as a phase, minus phase-status transitions: make the change with
tests/docs/state updated, verify, update the ledger, prepare the commit hand-off, report, stop.

**The documents on an edit run.** In the feature ledger — one `feature set` call — edit in
place the `howToCheck` of any row whose behavior this edit changed, add `E-<n>` to its `phases`,
and **reset its `tested` to `untested`** — an edit changes delivered behavior exactly as a phase
does. Add a row (`feature add`) if the edit introduced a checkable feature. If the change is invisible to the developer, leave
the ledger alone. Touch `HOW_TO_RUN.md` only if the edit changed how the app is built, run or
configured.

**Register every minor edit in `state.json edits[]` — once, at hand-off, as soon as its checks
pass — including the `HOW_TO_RUN.md` commands Step 2, item 4 would run — and before the ledger
rows that name it (Step 2, item 3)** (DD-28). An edit ships code — it deserves an id, a status, and a reviewable identity, not
just a change-log line. Append
`{ "id": "E-<n>", "utc": ..., "summary": ..., "afterPhase": "<the phase it follows>",
"status": "done", "branch": null, "prUrls": [], "notes": "" }`
with `add edits "summary=..." afterPhase=P-<n> status=done`, on its own — the tool allocates the
`E-<n>` id, prints it, and fills the other defaults; never pass an `id`. Then write every
`changeLog[]` entry that cites that printed id in its `editsAffected` field (0b, item 5) in one
chained command, and the hand-off's high-water marks (Step 2, item 5), which count the ids those
entries print, in the next. Never register an edit
earlier: one that turns out to touch a contract stops (§When a Change Touches a Contract) and
must leave nothing to close. A run that stops before the edit's checks pass registers no edit;
its stop report says what is half made.

**Otherwise, edits behave like phases throughout.** Status moves forward only; the commit hand-off follows
the same rule; the developer records testing against the **feature rows** the edit touched, not
against `E-1` itself; and it can be handed to the Review stage as a target in its own right. A failure
the developer reports against an edit is forward work, exactly as for a phase — see
§Re-running a Phase (or Edit) That Failed Testing.

---

## Version Control *(the developer's — you run no git)*

**You run no git command, ever** — not `branch`, `checkout`, `commit`, `push`, `merge`, `stash`
or `reset`, and not the read-only ones (`status`, `log`, `diff`) either. Branching, committing,
pushing, PRs and merging belong to the developer, done whenever they choose or not at all.
Nothing in this stage depends on any of them: you build on the files as they stand in the
working tree. If you are asked to run one, give the developer the command to run themselves.

The repository conventions in `PROJECT_CONTEXT §3` — branch naming, PR target
(`context.repo.prTarget`), required reviewers — are the developer's notes, and no rule reads
them. **The commit message convention is the one you apply:** in the message you suggest.
**This section overrides** any wording in `PROJECT_CONTEXT.md` (written by an older harness
version) or in a skill that says the agent branches, commits, opens PRs or runs git.

For every unit of work:

- **Update, in the same run:** the **tests** (new/changed behavior is covered), the
  **documentation** (READMEs, the plan's test guide, **the feature ledger**, and
  **`HOW_TO_RUN.md`** if running the app changed), and **`state.json`** (statuses, change log).
- **Hand off what the developer needs to commit it:**
  1. **The files you changed** — created, edited, deleted — including the documents and
     `state.json`; grouped **per repo** under a `split` layout.
  2. **A suggested commit message**, following the commit convention in `PROJECT_CONTEXT §3`
     where one is set: a one-line subject naming the phase or edit, then
     **initial task** (the phase goal or the edit request), **reasoning** (key decisions, and any
     reconciliation or plan-refresh handling), **outcome** (what was built, how it was
     verified, follow-ups). Under `split`, one message per repo, each naming the others.
- **Never fill `branch` or `prUrls` yourself.** They stay `null` / `[]` until the developer
  says where the work went; then record what they said.

**Layout, file locations and release model are given — never your call.** Build to them and
don't re-open them:

- **Repository layout** (`context.repo.layout`, `PROJECT_CONTEXT §3`). **`single`** — the work
  lives in one repo. **`split`** — the work touches every repo it needs, and it is not finished
  until each repo's part is built and they run together per the test guide.
- **Where files go** — the source tree in **LLD §3a** (`context.repo.frontendRoot` /
  `backendRoot` where those are set). If the tree you need isn't described there, stop and
  report it as a design gap — don't pick a directory layout mid-phase, because later phases and
  later runs will pick a different one.
- **Release model** (`context.repo.release`) — under `independent`, keep each part deployable on
  its own and respect the API-compatibility rule the LLD sets.

If the developer wants the layout or release model changed, that is a Stage 0 rerun, not a
decision you make mid-build.

*Starting from the right code — the content check before any build — is part of Step 0
(§Starting From the Right Code).*

### Recording Developer Decisions

The developer never hand-edits `state.json` or the feature ledger. They tell you what
happened; you write it and confirm. **The protocol — what each statement maps to — is defined
in `AGENTS.md §Recording What the Developer Tells You`, which is loaded in every session.
Follow it there; it is not restated here so the two cannot drift.**

Two points specific to this stage:

- **Testing results are ledger writes, not status writes.** "accept P-2" ticks the ledger
  rows built in P-2 (`feature set P-2 tested=passed --developer-said`); it does not change
  P-2's `status`, which stays `done`
  because the code is still built. Nothing in this stage waits on it.
- **A reported failure is work to schedule**, not a rewind. Record it on the row and handle it
  per §Re-running a Phase (or Edit) That Failed Testing.

### Re-running a Phase (or Edit) That Failed Testing

When the developer reports that delivered behavior is broken, the phase **stays `done`** — the
code is built, and rewinding a status would tell every later run that work is still pending.
What happens instead:

1. The `FEATURE_STATUS.md` row reads `failed <date> — <symptom>` (written per `AGENTS.md`).
2. A `changeLog` entry records it (`author: developer`, `origin: developer-prompt`).
3. The fix is **forward work**, classified at Step 0a like anything else: a **minor edit** if it
   touches no contract, a **reconciliation task** folded into the next phase run if it is small
   and the run is already happening, or a **new phase** if it is large or contract-touching.
4. Whatever fixes it sets that row back to `untested` — the developer re-walks the check and
   ticks it themselves.

**Never** re-open the original phase or re-use its ID. The fix lands in the working tree on top
of whatever is there, like any other work.

---

## Hard Rules

1. **One unit of work per run.** Classify → reconcile → implement the phase/edit → hand off →
   stop. Never "just finish the rest".
2. **Never skip Step 0.** Building on a stale plan/design wastes the testing round.
3. **Honor the contracts exactly.** Endpoint paths/verbs/shapes, status codes, entity/column
   names, component/route names, validation rules come from the LLD — match them. Capture exact
   values (formulas, enumerations, defaults) from the requirements.
4. **Keep the baseline green.** The app builds and runs at every hand-off; previous phases'
   behavior survives except explicit replacements.
5. **Verify every task before moving on.** A task isn't done until build compiles, relevant
   tests pass, and its "done when" conditions are met — by checks that actually ran (Step 1,
   item 4; a screen with no browser tool and no automated test is named as not run instead).
6. **Write tests. Update docs. Update state.** Every run leaves all three current.
7. **Idiomatic, clean code** for the target stack; honor the code-style constraint mechanically.
   **For UI work, build from the design language in LLD §3b** — use the shared components and
   tokens the frontend-scaffold phase established; never hand-roll a one-off style, colour, or
   spacing value on a screen. If §3b lacks a component you need, add it to the shared set and
   note it, rather than styling it locally: a local style is invisible to every later phase and
   is exactly how the UI drifts. The design language governs **appearance only** — screens,
   fields, validation, and flows still come from the requirements and the LLD.
8. **Stay in scope.** Build the current phase/edit — not future phases' features. Surface
   gold-plating temptations instead of building them.
9. **You may re-slice the forward plan; you may not change what gets built.** Step 0c lets
   you add, remove, reorder, split, and merge **remaining** phases — with the developer's
   approval — and update statuses, tasks, and test guides. It does not let you change a design
   contract, drop a `FEATURE_STATUS.md` row, or invent scope; those are the developer's and the
   design agent's calls. Never renumber or reuse a phase ID, and never reopen a `done`
   phase to absorb a change — that is what a retrofit phase is for.
10. **No secrets in source**, and **no hard-coded origins**. The API base URL, allowed CORS
    origins, and anything else that differs between local and the deployment target come from
    the configuration keys in **LLD §7**. Honor the runtime topology in `PROJECT_CONTEXT §3`:
    under `same-origin`, don't introduce a second origin or a CORS shim to make something work;
    under `separate-origins`, use the designed CORS policy and session mechanism rather than
    widening it. Building against the wrong topology passes locally and fails on deployment —
    if the phase seems to require the other one, stop and report.
11. **Don't touch the source app or the existing database schema.** Read-only on the legacy
    side; non-destructive on the DB. **This holds even when the legacy source shares a
    repository with the target code** (`context.locations.sharedWithLegacy`) — you write in
    that repo, but legacy files are never modified, moved, or deleted, and no change of yours
    may touch them. Build the new tree beside it.
12. **Never self-authorize a scope change.** Recommend the doc edit and the re-slice; let the
    developer decide. Apply an approved refresh (approved in advance counts), never a silent
    one.

---

## When You're Blocked

Stop and report (rather than improvising) if:

- The plan/design/requirements are contradictory, ambiguous on a material point, or missing
  something a task needs — including developer changes (Step 0) that conflict with the design.
- A change request touches a **requirement, design contract, or plan scope** — name the owning
  document, the delivered phases it invalidates, and the stage that should amend it, then stop
  (§When a Change Touches a Contract). Do not implement it and do not amend the doc yourself.
- A plan refresh you proposed in Step 0c has not been approved — build the phase as it stands,
  or stop; never build to an unapproved re-slice.
- Honoring a constraint (`PROJECT_CONTEXT §4`) would break a design contract — the constraint
  wins; this needs a human/design decision.
- You cannot satisfy a constraint's *Implement* obligation with what you have — the fixed thing
  it protects can't be changed and the missing input isn't yours to invent (e.g. a reused
  schema that doesn't match the mapping; deferred auth specifics; unavailable connection
  config). Do what the obligation says for the blocked case if it specifies one; otherwise
  report and wait.
- The predecessor's work is **missing** from the target code and the developer has not said
  to build there anyway (§Starting From the Right Code).
- An external dependency, credential, or access is unavailable.
- **The phase proves too large** to finish within the sizing rules (`3_PLAN_INSTRUCTIONS.md
  §Step 2` — walkable in one sitting, reviewable in one pass; e.g. the remaining tasks would
  not fit in this run with full verification). Bring a coherent part of it to a runnable
  state — everything built so far checkable by hand — start nothing further, and
  **propose a split**: what is built, what moves to a new phase, and that phase's one-sentence
  goal. Never move work out on your own; this is a plan-scope change (rule 12). On approval:
  - add the moved work as a new phase with the next unused ID, sequenced next, per
    `3_PLAN_INSTRUCTIONS.md §Refreshing the Plan`;
  - trim the current phase's tasks, test guide, and exit criteria in the plan to what was
    built, so its gate passes honestly rather than by waiver. **Remove only exit criteria
    about the moved work.** Criteria that bind every phase — build, tests, formatter/linter,
    any coverage bar, earlier phases still working — stay, and must pass. A split is never a
    way around a failing gate; name in the proposal every criterion you would remove;
  - re-point every ledger row for the moved work to `scheduled in` the new phase (`feature
    set`, one call), leaving `tested` untouched;
  - record the move in `sizeReport.pushedLater` and a `changeLog` entry, then hand off as
    usual.

  Until approval, build nothing further in this phase. **If the developer declines**, continue
  the phase as planned, or stop if they say so; either way record `sizeReport.verdict` as
  *too large* with your proposed split in `splitSuggestion`, so the next refresh still has
  the evidence.

**Not blockers** — never stop for these: a phase the developer hasn't tested, a
`FEATURE_STATUS.md` row still `untested` or marked `failed`, uncommitted or unmerged work, or
open review findings. The first two are recorded and reported; committing and merging are the
developer's; findings are reconciliation input.

State the blocker, what you tried, and the options — let the developer decide. Record unresolved
items as `OPEN QUESTION:` and assumptions as `ASSUMPTION:`.

---

## Definition of Done (for this run)

Items below are written for a phase run. **On a minor-edit run they apply to the `edits[]` entry
instead**, with the test-guide and phase-status items scoped as §Minor Edits states — an edit has
no plan test guide of its own and does not displace the current phase.

- [ ] Step 0 done: work classified by you (phase / minor edit); changes reconciled into plan +
      code; developer notes and reconciliation appended to `changeLog[]` (or "no changes"
      confirmed).
- [ ] **Step 0c done:** "plan unchanged" reported, or a re-slice **proposed, approved, and
      applied** per `3_PLAN_INSTRUCTIONS.md` — or applied under this run's prompt's advance approval
      and reported first — never applied silently. Either way, phases `done` before this run
      moved from plan §5 to §2 Completed — and, when no `pending` phase remains in §5, the
      phase this run finished.
- [ ] Nothing touching a requirement, design contract, or plan scope was built or doc-edited —
      such requests were routed to their owning stage and stopped on — apart from an approved
      Step 0c refresh or mid-phase split.
- [ ] No `done` phase reopened; retrofits planned as new phases.
- [ ] Every task completed and verified, reported blocked, or moved out by an **approved**
      split and listed in `sizeReport.pushedLater`.
- [ ] `sizeReport` recorded and stated in the report, its verdict consistent with `pushedLater`.
      An approved split re-pointed its `FEATURE_STATUS.md` rows to the new phase; no row reads
      `scheduled in` this phase once it is `done`.
- [ ] App in the promised runnable state; the developer test guide walked on a free port
      (steps that cannot be carried out here named as not walked), accurate, and what the walk
      started stopped.
- [ ] **The feature ledger updated in place through `tools/docs.py`** (by hand under its rules
      only without Python, said in the report): delivered rows read `built in P-N` with a
      concrete `howToCheck`; rows whose **behavior** changed gained this phase and were **reset
      to `untested`**; no `tested` value invented; no row deleted; `feature check` passes.
- [ ] **`HOW_TO_RUN.md` accurate:** its commands run this session; edited only if building,
      running or configuring the app changed.
- [ ] Previous phases' testable behavior still works (explicit replacements aside); the report
      names the ledger rows this phase put at risk.
- [ ] Every constraint's *Implement* obligation (`PROJECT_CONTEXT §4`) holds in the running app;
      no secrets in source.
- [ ] Contracts built this run match the LLD exactly and are exercised by tests.
- [ ] Code sits in the LLD §3a source tree; no directory layout invented.
- [ ] No hard-coded origins or hosts — the `PROJECT_CONTEXT §3` runtime topology is honored
      through LLD §7 config keys.
- [ ] Before any code: the target code was checked **by content** for the predecessor's work,
      and what was found **named in the report**; missing work was raised, not rebuilt.
- [ ] **No git command run.** Tests, docs and `state.json` updated; the report lists the
      changed files (per repo under `split`) and a suggested commit message (initial task /
      reasoning / outcome).
- [ ] `branch` and `prUrls` left as they were unless the developer said where the work went; a
      minor edit registered in `edits[]` once its checks passed, already `done`, with its own
      `E-<n>` id.
- [ ] `progress.lastProcessedChangeLogId` and `lastProcessedReviewNumber` advanced to exactly
      what this run folded in — never blindly to the highest present.
- [ ] Review findings folded in are named in the report; any too large went to Step 0c rather
      than stalling the run.
- [ ] Phase (or edit) `status` is `done` in `state.json` — terminal; plan edits saved; no plan
      checkbox ticked.
- [ ] **The two counts are in the report** — features awaiting testing, and open review
      findings — asked for or not.
- [ ] Open questions and assumptions reported, not silently resolved.
- [ ] Every message to the developer, including the closing report, follows `AGENTS.md §Writing for the Developer`.

---

## Additional Instructions

*(The prompt may append run-specific guidance — plan/design/requirements/context/state file
paths, the phase to execute or the edit to make, approval of a plan refresh proposed by a
previous run, developer feedback/change notes from testing, Review findings to address, the
target repo, or the commit message convention. Treat these as overrides/additions; fold change
notes through Step 0. You classify the work yourself — the prompt need not declare whether it
is a phase or an edit.)*
