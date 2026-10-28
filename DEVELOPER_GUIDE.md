# Developer Guide: Using the Modernization Harness

This guide is for **you, the developer** driving an application modernization with the six
instruction documents in `ModernizationHarness/`. The harness is **stack-agnostic** — nothing
about the source or target technology is baked into the instructions. What you're migrating
*from* and *to*, how it ships, and the rules that can't be broken are all captured **once**,
up front, in a Project Context, and every later stage reads them from there.

> **The load-bearing pieces**: a **Stage 0 Project Context** that parameterizes stacks /
> CI/CD / constraints and forces a decision on load-bearing questions; a **`state.json`** file
> that holds all machine state (statuses, lineage, change log) so the doc stays readable and
> lineage is mechanical; **mechanical (falsifiable) exit criteria** as the only gate; an explicit
> **rolling plan** that covers remaining work only and is refreshed before most build runs; and an
> independent **Stage 5 Review/QA** that feeds findings back into the loop.

> **Looking for a specific situation** — a phase failed your testing, the design has to change
> mid-build, a review came back with a Blocker, you want a stage rerun? **[USE_CASES.md](USE_CASES.md)**
> walks twenty-one of them with the exact prompt to send and what happens behind it. This file is the
> reasoning; that one is the recipe book.

---

## The Files, in the Order You Use Them

All of these live in `ModernizationHarness/`. Filenames are numbered by stage, so the folder
listing reads as the running order:

| File | Stage | What you do with it |
|---|---|---|
| `AGENTS_TEMPLATE.md` | *always* | **Copy to your project root as `AGENTS.md`.** Not a stage — it loads in every session |
| `0_INTAKE_TEMPLATE.md` | — | **Start here.** Copy to `INTAKE.md` in your project and fill it in |
| `0_PROJECT_CONTEXT_INSTRUCTIONS.md` | 0 | Resolves your intake → `PROJECT_CONTEXT.md` + `INTAKE_RESOLVED.md` + `state.json` |
| `1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md` | 1 | Legacy app → three requirements docs + `LEGACY_CODE_MAP_<App>.md` (where the legacy code lives) |
| `2_DESIGN_INSTRUCTIONS.md` | 2 | Requirements → HLD + LLD |
| `3_PLAN_INSTRUCTIONS.md` | 3 | Design → phased plan (**remaining work only**) + `state.json phases[]` + the feature ledger (`features.json`, shown as `FEATURE_STATUS.md`) |
| `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` | 4 | **Run once per phase**, in a loop, until done |
| `5_REVIEW_INSTRUCTIONS.md` | 5 | Independent audit; findings loop back to stage 4 |

Stages 0–2 run **once each, in order** (and are rerun when something changes). Stages **3, 4 and
5 then run in a loop** — refresh the plan, implement a phase, test it, review it, repeat — so
the numbering marks position in the pipeline, not a one-way path. **Stage 3 is not a one-shot:**
the plan covers only remaining work and is re-checked at the start of most Stage 4 runs.

### Setup — do this once, before Stage 0

```bash
mkdir -p out
cp ModernizationHarness/AGENTS_TEMPLATE.md   ./AGENTS.md      # project root
cp ModernizationHarness/0_INTAKE_TEMPLATE.md ./out/INTAKE.md  # then fill it in
```

**`AGENTS.md` matters more than it looks.** Every safety rule in the stage files only applies
when you explicitly invoke that stage. The moment you just chat — *"add a department filter"*,
*"fix this test"*, *"P-3 passed testing"* — none of them are in context, and the pipeline's
state can drift from reality without anyone noticing. `AGENTS.md` loads every session and
closes that gap: it carries the invariants, the authority ladder, and a routing rule that
catches edits made outside a formal stage run (see §Working Outside a Stage).

Its **first section also records where the stage files live** — `ModernizationHarness/` by
default. That is what lets every prompt in this guide name them bare. Keep the harness
somewhere else and you change that one line; nothing else moves.

---

## The Pipeline at a Glance

```
 Legacy app
      │
      ▼
 [0] Project Context ───► PROJECT_CONTEXT.md   (stacks, CI/CD, constraints, questionnaire)
      │                   state.json           (machine state — initialized here)
      ▼
 [1] Requirements ──────► BUSINESS_/FUNCTIONAL_/TECHNICAL_REQUIREMENTS_<App>.md
      │                   LEGACY_CODE_MAP_<App>.md      (where the legacy code lives)
      │
      ▼
 [2] Design ────────────► HIGH_LEVEL_DESIGN_<App>.md   (architecture & decisions)
      │                   LOW_LEVEL_DESIGN_<App>.md     (contracts & specifics)
      ▼
 [3] Planning ──────────► PLAN_<App>.md   (remaining phases)  +  state.json phases[]
      │  ▲
      │  │ Step 0c refreshes the remaining plan before most phase runs
      ▼  │
 [4] Phase Implementation ──┐        [5] Review / QA  (independent agent)
      ▲                     │              │
      │  YOU commit & (when  │◄─────────────┘  findings → state.json changeLog[]
      │  you like) test      │
      └─────────────────────┘   … repeat until FEATURE_STATUS.md is fully delivered
```

Stages 0–2 are each **one agent run** producing documents. Stage 3 produces the plan and is then
**re-entered from Stage 4's Step 0c** whenever the remaining phases need re-slicing. Stage 4 is a
**loop** — one run per phase (or per minor edit), with you in between. Stage 5 (**Review**) runs
independently against any delivered work, and its findings loop back into Stage 4.

**Nothing in this loop blocks on you.** You can run four phases before testing any of them. The
only gate anywhere is a phase's own exit criteria, which the agent must pass before it may call
the phase `done`.

Every stage supports a **rerun with Additional Instructions** if you're not happy with the
output — see §Reruns. **A design change mid-build is a rerun of Stage 2, not a special
procedure** — see §Changing the Design Mid-Build.

---

## `state.json` — the machine's memory

The single source of truth for **progress, lineage, and change history**. The Markdown docs
hold human-readable *content*; `state.json` holds *state*. Stage 0 initializes it; later stages
read and append to it. **You never edit it by hand** — you tell the agent what happened
("accept P-2", "P-2 failed", "P-3's PR is <url>") and it records the change and confirms.

It holds **machine facts only**. What you have tested is *not* in here — that lives in the
feature ledger, per feature, because a later phase can change what an earlier one built.

- `context` — stacks, CI/CD mode, and the **constraints** (by ID, e.g. `C1`, `C2`).
- `stages` — status + `rerunCount` for context/requirements/design/plan.
- `phases[]` — each phase's `status` (`pending`/`in progress`/`done` — **forward only**, and
  `done` is terminal), plus the `branch` and `prUrls` of its work — **filled only when you tell
  the agent where you committed it**, since the agent runs no git (`prUrls` is always an array,
  one per repo under a `split` layout, and empty until you name a PR).
  **Nothing records whether work was committed or merged**, because nothing depends on it. **IDs are permanent** — a plan
  refresh may drop unstarted phases and append new ones, but never renumbers or reuses an ID.
- `edits[]` — **minor** edits (`E-1`, `E-2`…): changes touching no contract. An edit ships code,
  so it gets an id, a status, and a commit hand-off of its own — and can be reviewed
  independently, like a phase.
- `changeLog[]` — **append-only** record of every mid-flight change (developer notes,
  reconciliations, review findings, out-of-band edits). This is what the Implement stage
  reconciles against.
- `reviews[]` — one entry per Review run, with its outcome and `blockerCount`. **A review sets
  no status on anything and blocks nothing**; its findings become `changeLog[]` entries the next
  Implement run folds in, and `progress.lastProcessedReviewNumber` tracks what has been dealt
  with.
- `progress` — the **high-water mark** (`lastProcessedChangeLogId`,
  `lastProcessedReviewNumber`, both integers) telling the next Implement run which entries it
  has already folded in. Without it, every run would re-apply the whole change log.

Keep it in git — your commits are its history. The agent itself runs no git: it tells new from
already-applied by the `progress` high-water mark, not by diffing.

---

## Constraints — the heart of the harness's generality

There is no hardcoded "reuse the DB / use AD / Google Java Style" anymore. In Stage 0 **you
declare the constraints that apply to your project**, each with a stable ID — and, critically,
each with its **per-stage obligations**: what Requirements, Design, Plan, Implement, and Review
must actually *do* to honor it.

That obligations list is the **single place constraint-specific rules live**. The stage
instruction files contain no per-constraint rules at all; they generically say "honor each
constraint per its stated obligation." So:

- Adding a constraint (compliance, data-residency, anything) needs **no edit to any stage file**.
- A constraint that lists no obligation for a stage simply doesn't affect that stage.
- If a stage's behavior should change because of a constraint, that instruction belongs in the
  constraint's obligations — not in the stage file.

Example: a **data/DB-reuse** constraint might state *Requirements:* capture table/column names
verbatim; *Design:* map entities onto existing tables, ORM validate-only; *Plan:* the first
data-store phase must prove the mapping validates; *Implement:* fix the mapping, never the
schema; *Review:* confirm validate-only and exact mappings. A green-field target declares none
of that — and nothing downstream needs changing.

---

## Stage-by-Stage

### Stage 0 — Project Context  · `0_PROJECT_CONTEXT_INSTRUCTIONS.md`
Fill in the **Intake Questionnaire** — copy `0_INTAKE_TEMPLATE.md` to `INTAKE.md` in your
project, answer what you know, and pass its path. The agent resolves your answers: applying
stated **defaults** where you were silent, and **hard-stopping** on load-bearing blanks
rather than guessing. It then derives the constraint set with obligations, pins the delivery
and cutover boundary, writes `PROJECT_CONTEXT.md` and `INTAKE_RESOLVED.md` (its record of how
each answer was reached), and initializes `state.json`.

**The six load-bearing questions** (these block the pipeline until answered): current stack,
target stack, DB reuse vs. new schema, **legacy coexistence**, **cutover strategy**, and auth
(where the app is access-controlled) — plus data migration when Q7 chooses a new schema.
Each topic is split into lettered single-answer parts (e.g. 12a cutover, 12b rollback); the
template marks exactly which parts block.
**Legacy coexistence and cutover strategy** are architecture-defining — a strangler-fig
cutover or a still-live legacy writer changes the design and how phases are sliced, so neither
can be safely defaulted.

**How the questionnaire works** — this trips people up, so:

| | Where it lives | Who edits it |
|---|---|---|
| The **questions** (blank template) | `0_INTAKE_TEMPLATE.md` | only when changing the method for *all* projects |
| **Your answers** | `INTAKE.md` — your copy, in your project | **you.** This is the input, and where you revise |
| The **resolved record** | `INTAKE_RESOLVED.md`, written by the agent beside `PROJECT_CONTEXT.md` | nobody — it's a record, with provenance |

The flow is one-way: **`INTAKE.md` → agent → `INTAKE_RESOLVED.md`**. Copy the template
once, fill in what you know, leave the rest blank. Each question is its own heading with one
`Answer:` line; where the answer is a choice, tick a box by changing `- [ ]` to `- [x]`. The
long explanations sit in folded *Why this matters* blocks — Ctrl+Shift+V in VS Code shows the
file as a page where they stay closed until clicked. To change an answer later, **edit
`INTAKE.md` and rerun Stage 0** — don't edit `INTAKE_RESOLVED.md`, which records what the
*last* run decided (including which answers the agent supplied for you). Only Stage 0 reads that
record. Any answer the agent supplied that matters to a later stage is also written into
`PROJECT_CONTEXT.md`, which is what the later stages read.

```bash
cp ModernizationHarness/0_INTAKE_TEMPLATE.md ./out/INTAKE.md   # then tick boxes and fill in the Answer: lines
```

**Your job after:** read the report's *"Answered without you"* list — every question the agent
defaulted or inferred. Those are decisions you never made, and they propagate into constraints
and every downstream stage. Confirm or override them, then check the stacks and constraints.

### Stage 1 — Requirements  · `1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md`
Produces the three requirements docs (business / functional / technical) from the legacy app,
with depth steered by your constraints (exact data model if DB-reuse; full authz model if an
auth constraint; NFRs expanded from the context).
It also saves **`LEGACY_CODE_MAP_<App>.md`** — a map of where things live in the legacy code.
A small script (`tools/codemap.py`) writes most of it for free: every folder, then every file
with the classes, methods and stored procedures declared in it and their line numbers. The
agent adds one section on top: which files hold each feature, the business rules, data access,
security checks and so on. Every later stage — and ordinary chat — looks legacy code up there
instead of searching for it, which saves model calls on platforms that bill per call. The map
only says where to look; requirements still cite the code itself.
**Your job after:** skim all three; answer every `OPEN QUESTION:`/`ASSUMPTION:` — unresolved
questions compound downstream.

### Stage 2 — Design  · `2_DESIGN_INSTRUCTIONS.md`
Produces the HLD (architecture + rationale) and LLD (exact contracts), designing *within* the
target stack and constraints. Where the target has a UI, the LLD also defines a **design
language** (§3b) — tokens, layout patterns, and a component inventory. If you supplied a UI
sample (intake Q23), that language is extracted from it; if you didn't, idiomatic defaults are
chosen and written down anyway. Either way it's what stops phase 7's screens from looking
unlike phase 3's, since each phase is built in a separate run.
If you supplied **reference implementations** (intake Q24) — example Docker/Helm files, auth
code, file upload/download, and so on — the LLD also writes **§3c Reference Adoption**: what the
target takes from each sample and, just as importantly, what it does not. Each area carries its
own *Governs* scope, because they differ: a sample Dockerfile dictates shape and no behavior,
while sample auth code usually does dictate behavior — and that is normally why you supplied it.
Review grades each area against its own scope, flagging both ignoring the sample and copying
past it.

**Your job after:** validate the big decisions (layering, API style, auth path, data handling)
and clear the open questions. Changing a decision now costs a doc edit; changing it mid-build
costs rework.

### Stage 3 — Plan  · `3_PLAN_INSTRUCTIONS.md`
Produces `PLAN_<App>.md` (each phase runnable & testable, with a developer test guide and
**mechanical exit criteria**) and populates `state.json phases[]`.

**The plan covers remaining work only** — it's a rolling forecast, not a fixed schedule.
Delivered phases drop out of the phase list into a one-line §2 Completed entry — tested or
not — and the remaining phases are re-checked at the start of most Stage 4 runs. Two rules keep
that safe:

- **Phase IDs are never reused or renumbered.** New phases take the next unused number, even
  when they run *before* lower-numbered ones. IDs will stop being sequential — that's expected.
  Execution order lives in the plan; identity lives in the ID.
- **`FEATURE_STATUS.md` is the real commitment.** Stage 3 creates it: every requirement and
  design element gets a row with how to check it, which phase(s) built it, and whether you have
  tested it. Refreshes may move rows between phases but never delete one, and the ledger is
  **never regenerated** — later runs update rows in place. The phase list is a forecast;
  **the ledger is what proves the build is complete**, and whole-build Review flags any
  `unscheduled` row. The rows live in **`features.json`**; a small script, `tools/docs.py`,
  rewrites `FEATURE_STATUS.md` from them every time the agent changes one. So read
  `FEATURE_STATUS.md`, but don't edit it: if you do, the agent's next ledger write stops and
  asks how to carry your change over. The same script refuses what the ledger's rules forbid —
  deleting a row, changing its id, a value outside the allowed ones.

**Your job after:** sanity-check the slicing. Is P-1 genuinely small? Are the features you need
to see early actually early? If not, say so now — it's cheapest before any code exists.

### Stage 4 — Phase Implementation (the loop)  · `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md`
One run builds one phase **or** one minor edit — and **it classifies which itself**; you don't
have to declare it. Every run: **classifies** the work, **reconciles** changes from
`state.json`, **refreshes the forward plan** (Step 0c), implements in your working tree,
updates **tests + docs + state + the ledger** (the ledger and the plan's bookkeeping through
`tools/docs.py`, one command each), marks the phase `done`, hands you **the list of
changed files and a suggested commit message**, and **stops**. `done` is the end of the line — there is no further
status, and nothing waits on you.

**It runs no git at all** — no branch, commit, push, PR or merge, and no `git log` either.
Version control is yours: commit each phase when you like, on whatever branch you like, or not
at all. The next phase builds on the files as they stand, and tells you in one line what it
found there — so **the next phase starts where the last phase's code already is**, committed or
not. If a run stopped before hand-off, the next run finishes that half-built phase first.

**Step 0c — the plan refresh.** Before building, it checks whether the remaining phases are
still right. Default is **no change** ("plan unchanged — building P-6"). When something did
change — a design revision, a review finding, a lesson from the last phase — it **proposes** a
re-slice and **waits for your approval**. It never re-slices silently: a plan that shifts while
your attention is on testing is how scope moves unnoticed.

**Minor edits (`E-n`) are now genuinely minor** — a config value, a label, an obvious bug fix;
anything touching **no** requirement, design contract, or plan scope. Anything that *does* touch
a contract is a document change followed by a phase (below), never an edit.

### Stage 5 — Review / QA  · `5_REVIEW_INSTRUCTIONS.md`
An **independent** agent audits a phase, a minor edit (`E-1`), or the whole build on four
axes — requirements coverage, tests, security, static performance — plus constraint compliance.
It returns **CLEAN** or **FINDINGS**; actionable findings become `changeLog[]` entries
the next Implement run fixes. It changes no code, and it also reports **what's missing** —
ledger rows asked for but never built — and **what's untested**.

**It reports; it never blocks.** A Blocker means *"I would not build anything further on this"*,
said plainly and with reasons — but nothing enforces it, and you are free to carry on. The gate
it used to hold only ever fired for someone who chose to run a review in the first place, and
its findings already survived without it, through the change log. With no hard gates left in the
pipeline, this stage is your main independent check: run it on every phase that carries risk,
and on the whole build at milestones (see §Keeping the Request Bill Down).

---

## The Build Loop (Stage 4 + 5) — how you live in it

**Phase status lifecycle** (in `state.json phases[]`):

| Status | Meaning | Who sets it |
|---|---|---|
| `pending` | not started | planner |
| `in progress` | agent is building it | agent |
| `done` | built and self-verified against **mechanical exit criteria** — terminal | agent |

**Forward only, and `done` is the end.** Nothing rewinds: a failure you report, or a design
change that invalidates delivered work, becomes *new* work rather than a reopened phase. What is
built is built.

**Whether you have tested something lives elsewhere** — in `FEATURE_STATUS.md`, one row per
feature, because a later phase can change what an earlier one delivered and a phase-level mark
can't express that.

**You never hand-edit `state.json` or the ledger.** You say what happened and the agent records
it:

| You say | It writes |
|---|---|
| "accept P-2" | ticks every ledger row P-2 built — `passed <today>`. P-2 stays `done`. It leaves a row marked `failed` alone, and asks you about it and about any untested row P-2 changed but another phase built |
| "accept P-2, P-3, P-4" | the same, for each in turn |
| "search works" | ticks that one row |
| "P-2 failed — search returns 500" | `failed` on the affected rows, plus a `changeLog` entry. The fix is planned forward |
| "I hand-fixed the connection string" | a `changeLog` entry marked `out-of-band` |
| "P-3 is on branch `phase/P-3`" / "P-3's PR is <url>" | records it on P-3 — the only way `branch` / `prUrls` get filled |
| "commit P-3" / "merge P-3" | runs nothing — gives you the git commands to run yourself |

**It never runs git and never asks you to.** You commit, or you don't, and it needs nothing
from you either way.

A `passed` or `failed` mark goes through the ledger script with a `--developer-said` flag, and
the script refuses one without it. That is a reminder to the agent, not a lock: the script
cannot tell whether you really said it.

Accepting several at once is fine **when you name them** — deferring testing is a supported way
to work. What gets challenged is the vague version: "accept everything so far" usually means
nothing was tested, so the agent turns it into the explicit list and asks you to confirm. It
also won't fold acceptance into another request, because when your mind is on the next phase,
"yes" is reflexive.

**When a phase lands on your desk (`done`):**

1. **Commit it, or don't.** The report lists the changed files and a suggested commit message;
   branching, committing, PRs and merging are all yours. Committing per phase gives you a clean
   rollback point. **If you switch branches, stay on one that has the last phase's code** — the
   next phase builds on whatever files are there, and stops to ask if the last phase's work is
   missing. Nothing in the harness cares which you do.
2. **Carry on, or test — your call.** Running the next phase needs nothing from you but the
   word. When you do want to test: open `FEATURE_STATUS.md`, walk the rows marked `untested`,
   and use `HOW_TO_RUN.md` to get the app up.
3. **Tell the agent what you found:**
   - **A. Good** → **"accept P-2"**, or several at once, or a single feature by name. It ticks
     the rows and confirms — you never touch a file.
   - **B. Works, but you want a change** → ask for it. The agent decides what it is: if it
     touches **no** contract it's a **minor edit** (`E-n`) done on the spot; if it touches a
     requirement, design contract, or plan scope, it tells you which document owns it and stops
     — see §Changing the Design Mid-Build. You never have to classify it yourself.
   - **C. Fails your testing** → say so — **"P-2 failed, search returns 500"**. The row is
     marked `failed`, and the fix is scheduled as forward work: a minor edit, a reconciliation
     task in the next run, or a new phase. P-2 itself stays `done` and is never reopened.
4. **Repeat** until every ledger row reads `built` — and, ideally, `passed`.

**Watch the two counts.** Every hand-off report ends with them: features awaiting your testing,
and open review findings. With nothing blocking, those two numbers are the only standing signal
that the build has run a long way ahead of anyone checking it.

---

## Changing the Design Mid-Build

The common hard case: you're at P-6, and you need to change how auth works — which was built
back in P-3. **This is a normal, supported flow, and it takes two prompts.**

**1. Change the design.**

> rerun stage 2 — change auth from the local-table stub to OIDC
> against `<IdP>`; bearer tokens, existing users table retained for authorization only.

The agent amends the HLD/LLD **in place** (filenames never change — git holds the history), adds
a `## 0. Revision History` row naming what changed and **which delivered phases it invalidates**
(here: P-3 and P-5), and logs a `changeLog` entry. It writes no code and doesn't touch the plan.

> **Be specific.** "Change the auth mechanism" doesn't determine a design — protocol, IdP,
> token vs. session, what happens to existing credentials. The agent will ask or record
> `ASSUMPTION:`s. **This pause is the point:** it's where you catch it assuming SAML when you
> meant OIDC, *before* any code is planned around it.

**2. Run the next phase as usual.**

> run stage 4

Step 0c reads the revision-history row and proposes a re-slice: a **retrofit phase** (say
*P-8 — Migrate auth seam to OIDC*), sequenced **before** P-6 so nothing else gets built on the
old contract, plus any adjustment to P-6/P-7. You approve; it builds P-8.

Then run the next phase. **The second prompt is the one you always
use** — so a mid-flight design change costs you exactly one extra prompt (plus your yes to the
re-slice, unless you pre-approved it with `run stage 4 — apply any re-slice without asking`;
it then applies the re-slice and reports it first, for that run only).

**Three things that deliberately don't happen:**

- **P-3 is never reopened.** What is built is built; the retrofit is new work that supersedes
  it. The auth feature rows go back to `untested` so you know to re-check them.
- **No phase is renumbered.** The retrofit is `P-8` even though it runs before `P-6`.
- **No work silently disappears.** The `FEATURE_STATUS.md` rows for auth move from
  `built in P-3` to `built in P-8`; they're never deleted.

**If the current phase is mid-run**: don't stack two changes on one set of uncommitted work.
Either land it as-is (if genuinely unaffected by the change), or discard its changes, do the
retrofit, then redo it. P-6 stays `in progress`, so name the retrofit in the prompt and say to do it
first; P-6 resumes afterwards, judged by what is actually in the files. Redoing a half-built phase is cheap — nothing depends on it yet.

**When it's bigger than a retrofit.** If the change invalidates a foundational decision that
everything is shaped around (monolith → microservices at P-6), no incremental path saves you:
rerun Design, rerun Plan, and take the hit that much of the build is being redone. The agent will say
so rather than proposing a retrofit that can't work. This is rare — but when it happens, the
honest answer is the expensive one.

---

## Working Outside a Stage

You won't always want to launch a formal stage run. You'll ask questions, chase a bug, or want
one small thing changed. With `AGENTS.md` in place, the agent sorts those into three buckets —
deciding **at the moment it's about to write**, not from how you phrased the question, because
debugging so often turns into editing halfway through:

| What you're doing | What happens |
|---|---|
| Asking, explaining, diagnosing, running tests | Just done. No gate. |
| Changing **target code** | It asks whether to run it through Stage 4 (tests, docs, state, commit hand-off) or make the change directly |
| Changing a **pipeline document** (requirements / HLD / LLD) | It declines and points you at the stage that owns it |
| Changing the **plan's remaining phases** | Stage 4 owns this — it proposes the re-slice at Step 0c and applies it once you approve |

**If you say "just do it directly", it still logs a `changeLog[]` entry** marked `out-of-band`.
That's deliberate: skipping the process is your call, but skipping the *record* would leave the
next Implement run reconciling against a baseline that moved without it knowing. One line in the
log keeps the loop honest.

The third bucket is the one that saves you most often — an agent casually editing the LLD breaks
the contract that both Implement and Review judge everything against.

---

## Reruns (any stage)

Every stage document ends with an **Additional Instructions** block. If you're unhappy with an
output, relaunch that stage and say what you want changed:

> rerun stage 2 — use a modular monolith, not microservices

> rerun stage 3 — make P-5 smaller and pull reporting earlier

Everything after the dash *is* the Additional Instructions block; you don't have to name it.

The agent amends the existing artifacts **in place** (rather than regenerating from scratch —
filenames never change; git holds the history), bumps that stage's `rerunCount`, and logs a
`changeLog` entry so the downstream work gets reconciled or replanned. (Two exceptions write
nothing: a plan check that changes no phase, and a Stage 1 rerun that changes only the legacy
code map.)

**Reruns of Stages 1 and 2 also add a `## 0. Revision History` row** naming what changed and
**which delivered phases it invalidates**. That row is what Step 0c reads to decide whether a
retrofit phase is needed — it's the handoff that makes a mid-build change land in the code
rather than sit in a document nobody rebuilt against.

---

## Ground Rules & Tips

- **One unit of work per run.** One phase, or one edit — never "just finish the rest".
- **The designs are the contract; the plan is a rolling forecast; `state.json` is the memory.**
  The agent re-slices the *remaining* plan with your approval, but never changes the design.
  Design changes are yours to make or commission — and they reach the code as a retrofit phase.
- **Built is built.** A `done` phase is never reopened to absorb a change, and no status ever
  rewinds. New work gets a new phase.
- **Keep everything in git.** Commit docs, `state.json`, and code at each phase boundary — the
  agent runs no git, so these commits are yours to make. You get clean rollback points and
  reviewable PRs. The agent detects changes from the change log and Revision History rows, so
  log any hand edit to a document.
- **The change log is the loop's memory.** If a future run would behave differently knowing
  something, it belongs in `changeLog[]`.
- **Blockers are the system working.** The agent stops and reports rather than improvising when
  the schema surprises it, auth details are missing, or your change contradicts the design.
  Answer and relaunch.
- **Never let anyone "fix" a reused database.** If a DB-reuse constraint applies, the mapping
  changes, not the schema.
- **Secrets stay out of everything** — config/env only.
- **Review is independent.** Don't run it in the same session that built the code.
- **Reports are written for you to act on without asking again.** Every stage ends with a short
  plain-English summary, then **"What I need from you"** (or "Nothing"), then the detail. Terms
  are explained the first time, and nothing is named by ID alone — "the rule that the old
  database must not change (C3)", not "C3". If a report still loses you, say which part; if you
  want terser reports, edit `§Writing for the Developer` in your `AGENTS.md`.

---

## Keeping the Request Bill Down

Some agent platforms — GitLab Duo among them — bill **per model call**, not per token. Every
tool call the agent makes (read a file, run a test, edit) is followed by another billed call,
and how much it reads in that call does not change the price. The agent's own habits are set in
`AGENTS.md §Keeping the Request Count Down`: it batches reads, chains commands, and makes fewer,
larger edits. The rest is how **you** run it:

1. **Choose the model by its price per call.** Prices per call differ by model (on GitLab Duo
   here, Sonnet $0.50 and Opus $0.74 per request — `docs/TOKEN_SAVINGS.md` Option 1). A cheaper model for routine phases (scaffolding, CRUD
   screens) and the strongest one for design and tricky phases is usually the biggest saving.
2. **Answer questions before they are asked.** Each time the agent stops and you reply, a new
   chain of calls starts. Put known answers in the prompt — for example
   `run stage 4 — apply any re-slice without asking`. The agent then applies a re-slice without
   stopping and reports it first (Step 0c). It holds for that run only — say it again next time.
3. **Stay in the same chat for the next phase.** It already has the stage instructions loaded.
   It still reads the documents fresh at the start of each run, because you may have changed
   them. Start a new chat when the conversation grows long enough to slow it down or crowd its
   context — and always for Review.
4. **Lean towards the larger end of the phase-sizing rules.** Every run pays a fixed cost to
   read, reconcile and hand off; fewer, fuller phases pay it less often. Stay within "testable
   in one sitting" — tell Stage 3 so when you run it.
5. **Review selectively.** Review the phases that carry risk (auth, data mapping, anything a
   constraint governs) rather than every one, and run `run stage 5 whole-build` at milestones.
   Each review run pays its own read-and-report overhead.
6. **Keep the legacy code map.** Stage 1 saves `LEGACY_CODE_MAP_<App>.md` so later runs find
   legacy code without searching. Don't delete it. If the legacy code you were given changes (a
   newer drop of the old app), refresh it — free, no model involved. Its hand-written first
   section and the folders Stage 1 excluded are both kept (run it without `--exclude`, or the
   list you give replaces the saved one). If your new code now sits inside the legacy folder
   and is not yet on the map's *Excluded:* line, add `--exclude` for it and for every folder
   already on that line that still exists (the script refuses a folder that is gone):
   `python <stage folder>/tools/codemap.py <legacy app> --out ./out/LEGACY_CODE_MAP_<App>.md`
7. **Leave `.harness-tmp/` alone.** The tools create this folder in your project for the small
   files the agent hands them (it used to have to squeeze them into long shell commands, which
   often failed), and for the output of long builds (tip 8). Git does **not** ignore it, on
   purpose: GitLab Duo's file tools refuse to read or write a git-ignored path. It stays almost
   empty anyway — a tool deletes each file it was handed once it has read it, and a build's log
   once the build passes. So a file you see there in `git status` is a leftover: a run stopped
   before using it, or the log of a build that failed. Don't commit it; delete it if you like.
   Don't add the folder to your `.gitignore` either — the agent could no longer write there.
8. **Long builds run in the background.** Agent platforms cut a command off after a time limit
   — on GitLab Duo often 120 seconds, sometimes 30. A full build with tests and coverage
   (`mvn verify`, `ng test`) can take longer. The agent then runs it through a small script,
   `tools/longrun.py`: it starts the build in the background, then checks on it in steps that
   each end inside the limit. Each check is one more billed call, so a 6-minute build costs
   about four calls instead of one. If your platform stops background programs, so that even
   this cannot finish, the agent reports that check as not run and asks you to run it.
   **Ask your Duo admin whether the command time limit can be raised** — that is the cheaper
   fix. You can use the script yourself too:
   `python <stage folder>/tools/longrun.py` with no command prints how.

---

## Upgrading the Harness Mid-Project

You can move a project that is part-way through its build onto a newer harness version. Do it
**between two runs**, never while a stage is running. Below, `<harness>` means the
`ModernizationHarness` folder of the newer harness checkout, e.g.
`D:\tools\modernization-harness\ModernizationHarness`. To get the newer version there, run
`git fetch`, then `git checkout <newer branch or tag>` in that checkout.

**Before you start, check what changed.** Compare the two versions' `ModernizationHarness/`
folders (`git diff <old> <new> -- ModernizationHarness`). The steps below are enough when
`tools/state.py` and the `state.json` schema are unchanged and no stage you already ran gained a
new output. If either changed, read the new version's `docs/DESIGN.md` first — you may need a
stage rerun — and look below for a subsection about that version.

### 1. Find your stage folder

The installer never copies the stage files. Your project's `AGENTS.md` names where they live, in
its first section ("The six numbered stage files live in …"). That path is your **stage
folder**:

| Case | `AGENTS.md` points to… | What to do |
|---|---|---|
| **A** | the harness checkout itself | Note the current commit (`git rev-parse HEAD` in the checkout), then check out the newer version there — this upgrades every project that uses that checkout. Skip step 3 |
| **B** | `ModernizationHarness/` inside your project | Do every step |
| **C** | some other folder | Do every step, using that folder in place of `ModernizationHarness` |

### 2. Back up (PowerShell, in your project folder)

```powershell
Copy-Item AGENTS.md AGENTS.md.bak                                # everyone
Copy-Item -Recurse ModernizationHarness ModernizationHarness.bak # cases B and C
```

The backup name must not already exist, or the copy lands *inside* it.

### 3. Copy in the new stage files (cases B and C)

```powershell
Copy-Item -Recurse -Force <harness>\* .\ModernizationHarness\
```

This overwrites changed files and deletes nothing. If the new version **removed** a file, delete
it by hand.

These steps do not touch the agent skills in `.agents\skills\` — only the installer copies
those. If the new version changed `ModernizationHarness\skills\`, back up `.agents\skills\`
first (`Copy-Item -Recurse .agents\skills .agents\skills.bak` — again, the backup name must not
already exist), then copy the changed skill folders into it.

### 4. Update `AGENTS.md`

```powershell
Copy-Item -Force <harness>\AGENTS_TEMPLATE.md .\AGENTS.md
```

Then compare it with `AGENTS.md.bak` and:

- copy back any lines you added yourself (house rules, glossary) — **add** them to the new
  file; don't copy the old file over it, or you lose the sections the new version added;
- put your stage-folder path back in the first section — the template says
  `ModernizationHarness/`, which is right only for case B.

### 5. Check `state.json`

Run from your project folder — the tool finds `state.json` by searching the folder you run it
from:

```powershell
python <stage folder>\tools\state.py check
```

If it says none or several were found, put `--file <path to state.json>` before `check`.

### 6. Carry on

Run the stage you were going to run next — for most projects mid-build:

```
run stage 4
```

If the last run stopped half-way, Stage 4 finishes that phase first (a stopped minor edit is
simply asked for again). If the remaining
plan needs re-slicing (splitting, merging or reordering the phases still to come), Stage 4 asks
you first; to let it go ahead without asking for that one run, add
`— apply any re-slice without asking` (see §Keeping the Request Bill Down).

**Do not re-run the installer to upgrade.** It does not update the stage files, and it would
reset `out/INTAKE.md` to the blank template and overwrite `AGENTS.md` (both are backed up to
`.harness-backups\<timestamp>\`, but your filled-in intake would no longer be in place).

### If something goes wrong

Close any agent session, editor or terminal that has files open in the stage folder — a locked
file can stop a delete half-way. Then:

```powershell
Copy-Item -Force AGENTS.md.bak AGENTS.md                         # everyone
Remove-Item -Recurse -Force ModernizationHarness; if ($?) { Rename-Item ModernizationHarness.bak ModernizationHarness }  # B and C
```

In case A, check out the commit you noted in step 1 in the harness checkout again.

### Upgrading from a version before the no-git, request-count and plain-report changes

This covers a project started on a harness from before three changes: the agent runs no git
(DD-24), each run makes fewer model calls (DD-25), and every report is written in plain English
(DD-26). The steps above are all you need: the state tool and `state.json` are unchanged, and
stages 0–3 changed only in wording, so nothing you have produced is redone. Stage 5 (Review)
changed too: a whole-build review now checks for dropped feature rows against the requirement
IDs instead of git history, and its report names each finding and constraint in words. Review
reports you already have stay as they are. Before your next run:

- **Check out the branch with your latest phase's code.** The old Stage 4 left you on its last
  phase branch; the new one builds on whatever files are on disk.
- **Earlier phases' open PRs (pull requests — requests to merge a branch) and branches are
  yours now.** The report no longer lists them — merge or close them when you like.
- **Keep uncommitted work** from an interrupted run; Stage 4 resumes from the files.
- **`branch` / `prUrls` values already in `state.json` stay as they are.**
- **Your `PROJECT_CONTEXT.md` may still say Stage 4 branches and opens PRs.** Leave it; the new
  Stage 4 overrides that wording (`4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md §Version Control`).
- **Expect one extra note in the first report:** a design or requirements Revision History row
  (the change table at the top of that document) with no matching change-log entry (in
  `changeLog` in `state.json`) is logged as a hand edit — a change made outside a stage run —
  and folded in, because document changes are no longer detected through git. It happens once.
- **Your new `AGENTS.md` has two new sections.** *Writing for the Developer* makes every report
  open with a plain summary and "What I need from you", explain each term, and never name
  anything by ID alone. *Keeping the Request Count Down* — the agent's side of §Keeping the
  Request Bill Down above — makes the agent batch its reads and commands. If you merged your
  own lines into `AGENTS.md`, check that neither section was lost. Want terser reports? Edit
  *Writing for the Developer* there.
- **Reports end with a commit hand-off**, not a PR link: the changed files and a suggested
  commit message. Committing is yours.
- **You can pre-approve a plan re-slice** (a change to the phases still to come) for one run —
  see step 6.

### Upgrading to a version with the legacy code map

This covers a project that ran Stage 1 before the legacy code map existed (DD-27). Nothing you
have is redone, and the map is optional: without it, every stage searches the legacy code as
before. To get it, generate the map yourself — a script, so it costs no model calls:

```powershell
python <stage folder>\tools\codemap.py <legacy app> --out .\out\LEGACY_CODE_MAP_<App>.md --title <App>
```

Use the legacy path and documents folder from your `PROJECT_CONTEXT.md` if they differ. If
your new code sits inside the legacy folder, add `--exclude <that folder>` so it is not listed
as legacy code (the map remembers it for later refreshes). Build output such as `bin` and
`obj`, and folders named `ModernizationHarness` or `ModernizationHarness.bak`, are skipped
already; if your stage folder has another name and sits inside the legacy folder, add
`--exclude` for it too. That gives every later stage the file index
(sections 2 and 3). Section 1 — which files hold each
feature — stays a placeholder until Stage 1 fills it. To have it filled, run
`rerun stage 1 — write section 1 of the legacy code map only; change nothing else`. It changes
only the map, so it writes nothing to `state.json` and needs no Design rerun. That costs one
run; skip it if the requirements are already done and you rarely go back to the legacy code.

---

### Upgrading to a version with the feature-ledger tool (`features.json`)

This covers a project whose `FEATURE_STATUS.md` was written before `tools/docs.py` existed
(DD-29). The ledger's rows now live in `features.json`, and `FEATURE_STATUS.md` is rewritten from
them. Your state file is unchanged (`tools/state.py` only gained the `.harness-tmp/` folder,
DD-30), and nothing you have produced is redone. Do steps 1–6 above, then **one migration
step, before your next run**:

1. **Rebuild `AGENTS.md` from the new template** (step 4) — it has a new section, *The Feature
   Ledger*, the rule to run Windows shell commands through `pwsh` with its short list of traps, and new limits on how
   much the agent writes or chains in one go. Add your own lines back.
2. **Turn your ledger into `features.json`.** From your project folder:

   ```powershell
   python <stage folder>\tools\docs.py feature import .\out\FEATURE_STATUS.md
   ```

   Use your documents folder if it is not `out`. It reads every table in the file. If your
   ledger is split under headings (one table per feature area, say), each heading becomes a
   group, and your notes around the tables are kept with it. It prints the rows it read, their
   ids, and **the number of rows in each group and in total — compare these with your
   original** before you go on. Your original file is kept beside it as `FEATURE_STATUS.md.bak`,
   and `FEATURE_STATUS.md` is rewritten in the new layout: the title, then each group under a
   `##` heading with its notes and its table.

   **Already imported with an earlier version of this tool?** That version read only the first
   table and could drop rows. Undo it and import again, from your documents folder:

   ```powershell
   Move-Item -Force FEATURE_STATUS.md.bak FEATURE_STATUS.md; if ($?) { Remove-Item features.json }
   ```

   It removes `features.json` only once your original is back in place. Do this only if no
   Stage 4 run has changed the ledger since that import — those changes would be lost. If one has, ask the agent to compare the two files and carry the missing rows
   over instead.
3. **If it refuses**, it writes nothing and names each row it could not read — a value that is
   not one of `unscheduled` / `scheduled in P-N` / `built in P-N`, a tested mark without a
   `YYYY-MM-DD` date, a phase id that `state.json` does not have, a duplicate id. Fix those rows
   in the Markdown file — the last time you edit it by hand — and run the command again. It
   also refuses, naming the lines: a blank line inside a table (remove it); a table whose header
   is not exactly the six ledger columns, such as an extra `Notes` column or `Status` for
   `Tested` (rename or remove the column; a table that is not part of the ledger goes in a code
   block); two group headings with the same title; and a table header with no `|---|` line under
   it. A heading with no table under it, such as `# Legend`, is kept as text, not as a group.

   Two older forms are converted for you, each with a `note:` line. A phase range such as
   `P-1..P-15` becomes the list of those phases. A Build cell naming several phases, such as
   `built in P-2 (server); P-4 (client)`, is refused until you choose how to read it — for
   every such row at once — and the original text is kept as a *How to check* line:
   - `--split-scheduled` → `scheduled in P-4`: the feature is still owed to the later phase, and
     a re-slice cannot lose it; the part already built is not counted as awaiting testing.
   - `--split-built` → `built in P-2`: the part already built counts now and can be accepted;
     the later phase resets the row to `untested` when it adds its part.

   ```powershell
   python <stage folder>\tools\docs.py feature import .\out\FEATURE_STATUS.md --split-scheduled
   ```
4. **If it prints `warning:` lines**, the rows were imported but disagree with `state.json` (for
   example a row still `scheduled in` a phase that is done). Tell the next Stage 4 run about
   them; it re-points them.
5. **Check the plan:** `python <stage folder>\tools\docs.py plan check`. The agent now moves a
   finished phase into the plan's Completed section with this tool, which finds each phase by
   a heading like `## Phase P-4: Reporting`. It also needs every phase heading at the same
   level (all `##` or all `###`), and every code block closed. Inside a phase, any other
   heading at or above the phase's level is refused, except in the last phase: there such a
   heading — or one a level down that comes after the phase's Exit criteria — ends the phase
   and stays in the plan. One level down is otherwise fine (`### Notes` under `## Phase` moves
   with its phase). Where it cannot tell where a phase ends, it refuses rather than guess. If the check names a
   heading or a line, change it to fit — a formatting fix, not a plan change.

Without Python nothing changes: the agent edits both files by hand under the same rules and
says so in its report.

### Upgrading to a version with `state.py start`

`tools/state.py` gained one command, `start`, which Stage 4 now runs to begin each run (one
command instead of a chain that failed when the agent's command tool ran `cmd`). Nothing to
migrate: copy in the new stage folder and rebuild `AGENTS.md` (steps 3–4) so both mention it;
your `state.json` is unchanged.

### Upgrading to a version with `longrun.py` and values files the agent can write

Two changes, nothing to migrate by hand. Copy in the new stage folder and rebuild `AGENTS.md`
(steps 3–4) so both mention them; your `state.json` is unchanged.

- **`.harness-tmp/` is no longer ignored by git.** The older tools put a `.gitignore` in that
  folder holding only `*`. GitLab Duo's file tools refuse a git-ignored path, so the agent could
  not write its values files there. The next time `state.py` or `docs.py` runs, it deletes that
  `.gitignore` and prints one line saying so. It only deletes it if it holds exactly `*`. If you
  changed that file, it is left alone and the folder stays ignored — delete it yourself, or
  remove its `*` line. From now on each tool deletes a values file once it has read it, so the
  folder stays nearly empty. Old values files left there from before are not deleted — delete
  them yourself; `git status` now shows them.
- **`tools/longrun.py` is new.** It runs a long build or test suite in the background, so a
  command time limit no longer cuts it off (`§Keeping the Request Bill Down`, tip 8). It needs
  nothing set up.

### Windows: install PowerShell 7 (`pwsh`)

The rebuilt `AGENTS.md` tells the agent to run its shell commands on Windows as
`pwsh -NoProfile -Command "…"`. That works whether the agent's command tool hands the command to
`cmd` or to Windows PowerShell 5.1 — on GitLab Duo the first command of a session often goes to
`cmd`, which breaks PowerShell syntax. Check that `pwsh -v` works on the machine the agent runs
on; if not, install PowerShell 7. Without it the agent falls back to one plain command per call:
nothing breaks, but chained steps cost more calls.

## Worked Examples

The examples below show the **prompts** you'd give the agent at each step. Replace bracketed
values.

**Three locations, named separately.** Nothing is assumed to be "the current repo" — tell the
agent each one, even when they're the same place:

| | Example A uses | Access |
|---|---|---|
| **Legacy source** | `./legacy/` | **read-only in every stage** — never modified, even if it shares your repo |
| **Documents** | `./out/` | context, requirements, design, plan, `state.json`. Keep in git — your commits are their only history |
| **Target code repo** | this repo | where Stage 4 writes code; you branch, commit and open PRs |

If the legacy source sits inside the repo you're building in (common for a POC), **say so** —
the agent then adds the new tree alongside it and still refuses to touch legacy files.

**Two structural answers Stage 0 owns.** Q16e asks whether frontend and backend live in
**one repo or two**, and Q13c asks whether they are **shipped together or released independently**. Both
are settled once, in Stage 0; Design, Plan, and Implement read them and never re-decide.
Unanswered, they default to one repo shipped as one unit — and the default is reported back to
you like any other. Changing either later means rerunning Stage 0 and redoing the design that
was built on it.

### Example A — A .NET → Angular + Spring Boot migration that reuses the database

**Stage 0 — Project Context.** First copy the template and fill it in:

```bash
cp ModernizationHarness/0_INTAKE_TEMPLATE.md ./out/INTAKE.md
```

Filled-in extract (leave anything you don't know blank — it defaults and gets reported back;
unticked boxes and the folded *Why this matters* blocks are left out here for brevity):

```markdown
### 1. Why modernize, and why now?
**Answer:** The .NET desktop platform is end-of-life. No hard deadline.

### 3a. Strict parity, or are improvements allowed?
- [x] Strict parity — reproduce current behavior exactly, including known bugs and awkward UX

### 4a. Current application stack?  ⚠️ LOAD-BEARING
**Answer:** .NET WinForms + SQL Server (confirm from the app).

### 5a. Target frontend?  ⚠️ LOAD-BEARING
**Answer:** Angular, Node 25.9.0.

### 5b. Target backend?  ⚠️ LOAD-BEARING
**Answer:** Java 21 / Spring Boot, Maven.

### 5c. Target data access layer?  ⚠️ LOAD-BEARING
**Answer:** Spring Data JPA.

### 7. Reuse the existing database, or create a new schema?  ⚠️ LOAD-BEARING
- [x] Reuse the existing database as-is

### 9. While the target is live — including any period when old and new run side by side — will the legacy application also write to the same data store?  ⚠️ LOAD-BEARING
- [x] No — the legacy app stops writing before the target goes live (typical of big-bang)
**Answer:** The WinForms app is retired at cutover. No concurrent writers.

### 11a. How do users log in today?  ⚠️ LOAD-BEARING
**Answer:** Local users table.

### 11b. How should the target handle login?  ⚠️ LOAD-BEARING
- [x] Build an auth seam + dev stub, with the real identity provider deferred
**Answer:** Real AD comes later.

### 12a. How will the target go live?  ⚠️ LOAD-BEARING
- [x] Big-bang — build the replacement, switch over at once

### 13a. Where will the target be deployed?
- [x] Kubernetes
**Answer:** An internal cluster.

### 13b. How many deployable units ship?
- [x] One artifact holding both parts
**Answer:** The Angular build is packaged into the Spring Boot image.

### 13d. Once deployed, how does the frontend reach the backend?
- [x] Same origin — one host/port; the backend or a fronting web server serves both

### 13e. How is it arranged for local development, where that differs?
**Answer:** The Angular dev server proxies /api to Spring Boot on 8080.

### 14b. Can a developer reach a database with representative data?
**Answer:** Yes — a restored copy of prod data, locally.

### 16a. Where is the legacy source?
**Answer:** ./legacy/ (read-only).

### 16b. Where are the documents written?
**Answer:** ./out/

### 16d. Is the target code repository the same repo that holds the legacy source?
- [x] Yes — the new tree is added alongside the frozen legacy one

### 16e. Do frontend and backend live in one repo or separate repos?
- [x] One repo

### 16f. Root directory of each part?
**Answer:** ./frontend/ and ./backend/

### 19a. Code style guide?
**Answer:** Google Java Style Guide.

### 19b. How is the style enforced?
**Answer:** google-java-format in Maven.

### 19c. Do you want a unit test coverage bar?
- [x] Yes — answer 19d–19h

### 19d. Coverage — metric and threshold?
**Answer:** JaCoCo, line ≥ 80% and branch ≥ 70%.

### 19e. Coverage — scope?
- [x] Changed/new code only

### 19f. Coverage — exclusions?
**Answer:** Generated sources, DTOs, the Spring bootstrap class.

### 19g. Coverage — enforcement?
- [x] Build fails below the bar

### 19h. Coverage — from when?
- [x] From the scaffold phase onward
```

Then launch:

> run stage 0 — intake: `./out/INTAKE.md`, legacy app: `./legacy/`, app: `EmployeeSearch`,
> write to `./out/`

*→ You get `PROJECT_CONTEXT.md` with constraints **C1** (DB reuse), **C2** (auth seam), **C3**
(Java style) — each carrying its own per-stage obligations, e.g. C1 → *Requirements:* capture
the schema verbatim; *Plan:* validate the mapping in the first data-store phase; *Implement:*
run validate-only, fix mappings not the DB — plus `INTAKE_RESOLVED.md` and an initialized
`state.json`.*
**Review these obligations carefully** — they are what every later stage actually executes, so
a missing obligation is a rule that silently won't be enforced.*

**Stage 1 — Requirements:**

> run stage 1

**Stage 2 — Design:**

> run stage 2

**Stage 3 — Plan:**

> run stage 3 — prefer ~5 phases

**Stage 4 — Implement phase 1:**

> run stage 4

*→ Agent builds P-1 in your working tree, marks it `done`, lists the changed files with a
suggested commit message, and stops. Commit it yourself if you want — or don't; P-2 can start
either way. When you get round to testing, walk the `untested` rows in `FEATURE_STATUS.md` and
say:*

> accept P-1

*→ It ticks those rows — no JSON editing, and nothing was waiting on it.*

**Stage 5 — Review P-1** (independent run):

> run stage 5 on **P-1**

*→ CLEAN → launch P-2. FINDINGS → the findings are now in `state.json changeLog[]`; your
next Implement run reconciles and fixes them before/at P-2. Either way nothing is blocked.*

### Example B — Changing the design mid-build (the auth change at P-6)

You're six phases in. Auth was built in P-3 and is used by P-5's endpoints. You now need OIDC
instead of the local-table stub. **Two prompts.**

> rerun stage 2 — change auth from the local-table stub to OIDC
> against Keycloak; bearer tokens; keep the users table for authorization only.

*→ HLD §5 and LLD §1/§5 amended in place; a `## 0. Revision History` row records the change and
names **P-3 and P-5** as invalidated; a `changeLog` entry is added. No code, no plan edits.*

Then, exactly as always:

> run stage 4

*→ Step 0c reads the revision-history row and proposes: **add P-8 "Migrate auth seam to OIDC"**,
run it **before P-6**, and adjust P-6/P-7 to build against bearer tokens. You approve (or
pre-approved it in the prompt); it builds P-8, rewrites the auth rows' checks in
`FEATURE_STATUS.md` and resets them to `untested`, and hands you its changed files and commit message. P-3 is never reopened.*

Then run the next phase to get P-6 — committing P-8 first if you want it as its own commit.

**A change that touches nothing** — say a `department` filter the LLD already provides for — is
just a minor edit; ask for it and the agent does it as `E-1` without any of the above.

### Example C — Rerunning a stage you're unhappy with

**Revising your intake answers** (Stage 0 defaulted something you care about — say it assumed
no CI/CD, but you do have a pipeline). Edit **`INTAKE.md`** — Q15 becomes *"Respect existing:
GitHub Actions"* — then:

> rerun stage 0 — the intake at `./out/INTAKE.md` is updated; re-derive the constraints and
> their obligations accordingly

*→ If later stages already ran, the agent logs a `changeLog` entry naming which docs are now
stale so they get reconciled or rerun.*

**Re-slicing a plan** that front-loaded too much into P-1:

> rerun stage 3 — P-1 is too big; split the frontend out into its own later phase and keep P-1
> to backend scaffold + DB validation + two endpoints only. Re-slice future phases only; leave
> any delivered phases untouched.

### Example D — Whole-build final review

After the final phase is delivered:

> run stage 5 on the **whole build**
> Codebase is this repo. Emphasize security and requirements coverage. Write the report to `./out/`.

---

## Quick Reference — Who Writes What

| Artifact | Created by | You edit? | Agent edits? |
|---|---|---|---|
| `AGENTS.md` (your copy) | you, from the template | **add** project specifics only — never remove the invariants or the recording protocol | **never** |
| `0_INTAKE_TEMPLATE.md` | the method | no — copy it | **never** |
| `INTAKE.md` (your copy) | **you** | **yes — this is where answers live** | **never** (input only) |
| `PROJECT_CONTEXT.md` | Stage 0 | to fix constraints/obligations (rerun) | Stage 0 only — no other stage writes here |
| 3 requirements docs | Stage 1 | to answer open questions | Stage 1 rerun only (Stage 4 may make a purely *clarifying* fix and log it) |
| `LEGACY_CODE_MAP_<App>.md` | Stage 1 (sections 2–3 by `tools/codemap.py`) | no — rerun the tool if the legacy code changes, or once your new code's folder exists inside the legacy folder (tip 6 in §Keeping the Request Bill Down) | Stage 1 only; every other stage reads it |
| HLD / LLD | Stage 2 | **yes — design changes** | Stage 2 rerun only (same clarifying carve-out). Every rerun adds a §0 Revision History row |
| `PLAN_<App>.md` — remaining phases | Stage 3 | say what you want; the agent re-slices | **Stage 4 Step 0c re-slices remaining phases with your approval**; statuses and test-guide fixes |
| `features.json` (the ledger) | Stage 3, through `tools/docs.py` | **no hand-editing** — say "accept P-2" / "search works" | Stage 4 updates rows in place through `tools/docs.py`; rows **never deleted**, ledger **never regenerated** |
| `FEATURE_STATUS.md` | `tools/docs.py`, from `features.json` | no — read it; a hand edit stops the agent's next ledger write | rewritten by the tool on every ledger write |
| `.harness-tmp/` | the tools | no — a file in it that `git status` shows is a leftover; never commit it, delete it if you like | the agent's values files (deleted by the tool once read) and long-build logs from `tools/longrun.py` (deleted when the build passes); **not** ignored by git, so the agent's file tools can write there |
| `HOW_TO_RUN.md` (one file) | Stage 4 | no | only when building/running/configuring the app changes |
| `state.json` phases[] | Stage 3 (init) | **no hand-editing** | status (forward only); branch and PRs only when you name them |
| `state.json` edits[] | Stage 4 | **no hand-editing** | appends each **minor** edit once its checks pass, already `done`; otherwise the same lifecycle as a phase |
| `state.json` changeLog[] | Stage 0 (init) | tell it what you changed | your notes, reconciliations, review findings (append-only) |
| `state.json` reviews[] | Review stage | no | Review appends |
| `state.json` progress | Stage 0 (init) | no | Stage 4 advances the high-water mark |
| Application code | Stage 4 | hotfixes → log them | yes (in the working tree; you commit) |
| Review reports | Stage 5 | no | yes |

*(If you hotfix code or edit a design doc by hand, add a `changeLog` entry so the next run knows
the baseline moved.)*

---

## Where to go next

| You want | Read |
|---|---|
| To start, in five minutes | [README.md](README.md) |
| A worked recipe for the situation you're in | [USE_CASES.md](USE_CASES.md) |
| How the set is built, and why | [docs/DESIGN.md](docs/DESIGN.md) / [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) |
