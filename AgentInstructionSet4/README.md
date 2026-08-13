# Developer Guide: Using Agent Instruction Set 4

This guide is for **you, the developer** driving an application modernization with the six
instruction documents in this folder. Set 4 is **stack-agnostic** — nothing about the source
or target technology is baked into the instructions. What you're migrating *from* and *to*,
how it ships, and the rules that can't be broken are all captured **once**, up front, in a
Project Context, and every later stage reads them from there.

> **New in Set 4** (vs. Set 3): a **Stage 0 Project Context** that parameterizes stacks /
> CI/CD / constraints and forces a decision on load-bearing questions; a **`state.json`** file
> that holds all machine state (statuses, lineage, change log) so the doc stays readable and
> branching is tractable; **mechanical (falsifiable) phase acceptance**; an explicit
> **phase-vs-post-phase-edit** classification with a **contradiction check**; and an
> independent **Stage 5 Review/QA** that feeds findings back into the loop. See
> §What Changed From Set 3.

---

## The Files, in the Order You Use Them

Filenames are numbered by stage, so the folder listing reads as the running order:

| File | Stage | What you do with it |
|---|---|---|
| `AGENTS_TEMPLATE.md` | *always* | **Copy to your project root as `AGENTS.md`.** Not a stage — it loads in every session |
| `0_INTAKE_TEMPLATE.md` | — | **Start here.** Copy to `INTAKE.md` in your project and fill it in |
| `0_PROJECT_CONTEXT_INSTRUCTIONS.md` | 0 | Resolves your intake → `PROJECT_CONTEXT.md` + `state.json` |
| `1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md` | 1 | Legacy app → three requirements docs |
| `2_DESIGN_INSTRUCTIONS.md` | 2 | Requirements → HLD + LLD |
| `3_PLAN_INSTRUCTIONS.md` | 3 | Design → phased plan + `state.json phases[]` |
| `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` | 4 | **Run once per phase**, in a loop, until done |
| `5_REVIEW_INSTRUCTIONS.md` | 5 | Independent audit; findings loop back to stage 4 |

Stages 0–3 run **once each, in order**. Stages **4 and 5 alternate in a loop** — implement a
phase, test it, review it, repeat — so the numbering marks position in the pipeline, not a
one-way path. Any stage can be **rerun** when you're unhappy with its output.

### Setup — do this once, before Stage 0

```bash
cp AgentInstructionSet4/AGENTS_TEMPLATE.md   ./AGENTS.md      # project root
cp AgentInstructionSet4/0_INTAKE_TEMPLATE.md ./out/INTAKE.md  # then fill it in
```

**`AGENTS.md` matters more than it looks.** Every safety rule in the stage files only applies
when you explicitly invoke that stage. The moment you just chat — *"add a department filter"*,
*"fix this test"*, *"mark P-3 accepted"* — none of them are in context, and the pipeline's
state can drift from reality without anyone noticing. `AGENTS.md` loads every session and
closes that gap: it carries the invariants, the authority ladder, and a routing rule that
catches edits made outside a formal stage run (see §Working Outside a Stage).

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
      │
      ▼
 [2] Design ────────────► HIGH_LEVEL_DESIGN_<App>.md   (architecture & decisions)
      │                   LOW_LEVEL_DESIGN_<App>.md     (contracts & specifics)
      ▼
 [3] Planning ──────────► PLAN_<App>.md   (phases P-1…P-N)  +  state.json phases[]
      │
      ▼
 [4] Phase Implementation ──┐        [5] Review / QA  (independent agent)
      ▲                     │              │
      │  YOU test & accept  │◄─────────────┘  findings → state.json changeLog[]
      │  Review audits      │
      └─────────────────────┘   … repeat until the final phase is accepted & reviewed
```

Stages 0–3 are each **one agent run** producing documents. Stage 4 is a **loop** — one run per
phase (or per post-phase edit), with you in between. Stage 5 (**Review**) runs independently,
usually after you accept a phase, and its findings loop back into Stage 4.

Every stage supports a **rerun with Additional Instructions** if you're not happy with the
output — see §Reruns.

---

## `state.json` — the machine's memory

The single source of truth for **progress, lineage, and change history**. The Markdown docs
hold human-readable *content*; `state.json` holds *state*. Stage 0 initializes it; later stages
read and append to it. **You never edit it by hand** — you tell the agent what happened
("accept P-2", "P-2 failed") and it records the change and confirms.

- `context` — stacks, CI/CD mode, and the **constraints** (by ID, e.g. `C1`, `C2`).
- `stages` — status + `rerunCount` for context/requirements/design/plan.
- `phases[]` — each phase's `status` (`pending`/`in progress`/`done`/`accepted`),
  `reviewStatus`, `branchedFrom` (lineage), plus the `branch` and `prUrl` of its work.
- `edits[]` — post-phase edits (`E-1`, `E-2`…). An edit ships code, so it gets an id, a
  status, and a branch/PR of its own — and can be reviewed independently, like a phase.
- `changeLog[]` — **append-only** record of every mid-flight change (developer notes,
  reconciliations, review findings, out-of-band edits). This is what the Implement stage
  reconciles against.
- `reviews[]` — one entry per Review run, with its verdict and `blockerCount`. A target's
  `reviewStatus` goes `changes-requested` → `remediated` once Implement fixes the Blockers;
  until then the next phase is gated.
- `progress` — the **high-water mark** (`lastProcessedChangeLogId`,
  `lastProcessedReviewNumber`, both integers) telling the next Implement run which entries it
  has already folded in. Without it, every run would re-apply the whole change log.

Keep it in git. Its history is how the Implement stage detects what changed between runs.

---

## Constraints — the heart of Set 4's generality

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
and cutover boundary, writes `PROJECT_CONTEXT.md`, and initializes `state.json`.

**The six load-bearing questions** (these block the pipeline until answered): current stack,
target stack, DB reuse vs. new schema, **legacy coexistence**, **cutover strategy**, and auth
(where the app is access-controlled). The last two are architecture-defining — a strangler-fig
cutover or a still-live legacy writer changes the design and how phases are sliced, so neither
can be safely defaulted.

**How the questionnaire works** — this trips people up, so:

| | Where it lives | Who edits it |
|---|---|---|
| The **questions** (blank template) | `0_INTAKE_TEMPLATE.md` | only when changing the method for *all* projects |
| **Your answers** | `INTAKE.md` — your copy, in your project | **you.** This is the input, and where you revise |
| The **resolved record** | `PROJECT_CONTEXT.md §5`, written by the agent | nobody — it's a record, with provenance |

The flow is one-way: **`INTAKE.md` → agent → `PROJECT_CONTEXT.md §5`**. Copy the template
once, fill in what you know, leave the rest blank. To change an answer later, **edit
`INTAKE.md` and rerun Stage 0** — don't edit §5, which records what the *last* run decided
(including which answers the agent supplied for you).

```bash
cp AgentInstructionSet4/0_INTAKE_TEMPLATE.md ./out/INTAKE.md   # then fill in the Answer: lines
```

**Your job after:** read the report's *"Answered without you"* list — every question the agent
defaulted or inferred. Those are decisions you never made, and they propagate into constraints
and every downstream stage. Confirm or override them, then check the stacks and constraints.

### Stage 1 — Requirements  · `1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md`
Produces the three requirements docs (business / functional / technical) from the legacy app,
with depth steered by your constraints (exact data model if DB-reuse; full authz model if an
auth constraint; NFRs expanded from the context).
**Your job after:** skim all three; answer every `OPEN QUESTION:`/`ASSUMPTION:` — unresolved
questions compound downstream.

### Stage 2 — Design  · `2_DESIGN_INSTRUCTIONS.md`
Produces the HLD (architecture + rationale) and LLD (exact contracts), designing *within* the
target stack and constraints. Where the target has a UI, the LLD also defines a **design
language** (§3b) — tokens, layout patterns, and a component inventory. If you supplied a UI
sample (intake Q23), that language is extracted from it; if you didn't, idiomatic defaults are
chosen and written down anyway. Either way it's what stops phase 7's screens from looking
unlike phase 3's, since each phase is built in a separate run.
**Your job after:** validate the big decisions (layering, API style, auth path, data handling)
and clear the open questions. Changing a decision now costs a doc edit; changing it mid-build
costs rework.

### Stage 3 — Plan  · `3_PLAN_INSTRUCTIONS.md`
Produces `PLAN_<App>.md` (phases P-1…P-N, each runnable & testable, with a developer test guide
and **mechanical exit criteria**) and populates `state.json phases[]`.
**Your job after:** sanity-check the slicing. Is P-1 genuinely small? Are the features you need
to see early actually early? If not, rerun the planner now — it's cheapest before any code exists.

### Stage 4 — Phase Implementation (the loop)  · `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md`
One run builds one phase **or** one post-phase edit. Every run: **classifies** the work,
**reconciles** changes from `state.json`, runs the **contradiction check**, implements on a
**branch** with **small commits**, updates **tests + docs + state**, opens a **PR** with a
descriptive body, marks the phase `done`, and **stops**. It never sets `accepted` (that's you)
and never rolls into the next phase.

### Stage 5 — Review / QA  · `5_REVIEW_INSTRUCTIONS.md`
An **independent** agent audits a phase, a post-phase edit (`E-1`), or the whole build on four
axes — requirements coverage, tests, security, static performance — plus constraint compliance.
It returns **PASS** or **CHANGES REQUESTED**; actionable findings become `changeLog[]` entries
the next Implement run fixes. It changes no code.

**Blockers gate, Majors don't.** A Blocker stops the next phase from starting — building on a
known-broken foundation is what the loop exists to prevent — no matter whether it was found on a
phase, an edit, or a whole-build review. The gate clears when Implement fixes them and marks the
target `remediated`; a re-review then confirms. Majors ride along into the next run's
reconciliation.

---

## The Build Loop (Stage 4 + 5) — how you live in it

**Phase status lifecycle** (in `state.json phases[]`):

| Status | Meaning | Who sets it |
|---|---|---|
| `pending` | not started (or reopened by you) | planner / you |
| `in progress` | agent is building it | agent |
| `done` | built and self-verified against **mechanical exit criteria** | agent |
| `accepted` | **you** tested it and approved | **you only** |

Two rules keep the loop safe: **only you authorize `accepted`**, and the agent **refuses to
start phase N+1 while phase N is merely `done`**.

**You never hand-edit `state.json`.** You say what happened and the agent records it:

| You say | It writes |
|---|---|
| "accept P-2" | merges the PR, sets `accepted` + `acceptedUtc` |
| "P-2 failed — search returns 500" | `pending` + your note, PR left open |
| "accept E-1" | the same, for a post-phase edit |
| "I hand-fixed the connection string" | a `changeLog` entry marked `out-of-band` |

Acceptance is the one thing it won't do loosely: it must be **its own instruction naming the
phase**. Ask to start P-3 while P-2 is only `done` and it will stop and point you back rather
than offering to accept P-2 for you — because at that moment your goal is P-3, and a reflexive
"yes" is exactly how untested work slips through. It also won't accept several phases at once.

**When a phase lands on your desk (`done`):**

1. **Test it** — follow the phase's Developer test guide in `PLAN_<App>.md`.
2. **Decide:**
   - **A. Good, no changes** → just say **"accept P-2"**. The agent merges the PR, sets
     `accepted` + `acceptedUtc`, and confirms what it recorded — you never touch `state.json`.
     (If your repo needs reviewers or green CI, it records the acceptance and leaves the merge
     to you.) Then optionally run **Review**, and launch the next phase.
   - **B. Works, but you want a change** → this is a **post-phase edit**. Either edit the
     owning doc yourself (LLD for contracts, HLD for architecture, plan for sequencing) and add
     a `changeLog` note, or just describe the change in the next run's prompt and tell the agent
     **"this is a post-phase edit"**. The agent runs the **contradiction check**: if it's
     additive it does it on top; if it's a requirement/design change it presents options and
     **waits for your call** on anything large.
   - **C. Fails your testing** → say so — **"P-2 failed, search returns 500"**. The agent
     reopens it to `pending` with your note and leaves the PR open. Re-run it on the same
     phase; it reuses that branch and PR rather than opening a second one.
3. **Repeat** until the final phase is `accepted` (and, if you want, whole-build Review is PASS).

**Big course-corrections:** if your feedback amounts to "the design is wrong", don't funnel it
through a prompt note — rerun the Design stage, then rerun the Planner to re-slice the remaining
phases. The Implement agent will itself recommend this when a change is too large to absorb —
listen to it. Only future (non-`accepted`) phases get re-planned.

---

## Working Outside a Stage

You won't always want to launch a formal stage run. You'll ask questions, chase a bug, or want
one small thing changed. With `AGENTS.md` in place, the agent sorts those into three buckets —
deciding **at the moment it's about to write**, not from how you phrased the question, because
debugging so often turns into editing halfway through:

| What you're doing | What happens |
|---|---|
| Asking, explaining, diagnosing, running tests | Just done. No gate. |
| Changing **target code** | It asks whether to run it through Stage 4 (branch, tests, docs, state, PR) or make the change directly |
| Changing a **pipeline document** (requirements / HLD / LLD / plan) | It declines and points you at the stage that owns it |

**If you say "just do it directly", it still logs a `changeLog[]` entry** marked `out-of-band`.
That's deliberate: skipping the process is your call, but skipping the *record* would leave the
next Implement run reconciling against a baseline that moved without it knowing. One line in the
log keeps the loop honest.

The third bucket is the one that saves you most often — an agent casually editing the LLD breaks
the contract that both Implement and Review judge everything against.

---

## Reruns (any stage)

Every stage document ends with an **Additional Instructions** block. If you're unhappy with an
output, relaunch that stage's agent with your change requests appended there — e.g. *"Design:
use a modular monolith, not microservices"* or *"Plan: make P-1 smaller and pull reporting
earlier."* The agent amends the existing artifacts in place (rather than regenerating from
scratch), bumps that stage's `rerunCount`, and — if later stages already consumed the old
output — logs a `changeLog` entry so the downstream work gets reconciled or replanned.

---

## Ground Rules & Tips

- **One unit of work per run.** One phase, or one edit — never "just finish the rest".
- **The designs are the contract; the plan is living; `state.json` is the memory.** The agent
  may edit the plan's bookkeeping and statuses (via state.json) but never the design. Design
  changes are yours to make or commission.
- **Keep everything in git.** Commit docs, `state.json`, and code at each phase boundary. The
  agent uses git history to detect changes during reconciliation, and you get clean rollback
  points and reviewable PRs.
- **The change log is the loop's memory.** If a future run would behave differently knowing
  something, it belongs in `changeLog[]`.
- **Blockers are the system working.** The agent stops and reports rather than improvising when
  the schema surprises it, auth details are missing, or your change contradicts the design.
  Answer and relaunch.
- **Never let anyone "fix" a reused database.** If a DB-reuse constraint applies, the mapping
  changes, not the schema.
- **Secrets stay out of everything** — config/env only.
- **Review is independent.** Don't run it in the same session that built the code.

---

## Worked Examples

The examples below show the **prompts** you'd give the agent at each step. Replace bracketed
values.

**Three locations, named separately.** Nothing is assumed to be "the current repo" — tell the
agent each one, even when they're the same place:

| | Example A uses | Access |
|---|---|---|
| **Legacy source** | `./legacy/` | **read-only in every stage** — never modified, even if it shares your repo |
| **Documents** | `./out/` | context, requirements, design, plan, `state.json`. Keep in git — Stage 4 diffs these to detect changes between runs |
| **Target code repo** | this repo | where Stage 4 branches, commits, opens PRs |

If the legacy source sits inside the repo you're building in (common for a POC), **say so** —
the agent then adds the new tree alongside it and still refuses to touch legacy files.

### Example A — A .NET → Angular + Spring Boot migration that reuses the database

**Stage 0 — Project Context.** First copy the template and fill it in:

```bash
cp AgentInstructionSet4/0_INTAKE_TEMPLATE.md ./out/INTAKE.md
```

Filled-in extract (leave anything you don't know blank — it defaults and gets reported back):

```markdown
**1. Why modernize, and why now?**
**Answer:** The .NET desktop platform is end-of-life. No hard deadline.

**3. Strict parity, or are improvements allowed?**
**Answer:** Strict — reproduce current behavior; flag bugs, don't fix them.

**4. Current stack?**  ⚠️ LOAD-BEARING
**Answer:** .NET WinForms + SQL Server (confirm from the app).

**5. Target stack?**  ⚠️ LOAD-BEARING
**Answer:** Angular (Node 25.9.0) + Java 21 / Spring Boot, Maven, Spring Data JPA.

**7. Reuse the existing database, or create a new schema?**  ⚠️ LOAD-BEARING
**Answer:** Reuse as-is — no schema changes, no migration.

**9. Will the legacy application keep running against the same data store?**  ⚠️ LOAD-BEARING
**Answer:** No — the WinForms app is retired at cutover. No concurrent writers.

**11. How does the app authenticate today...?**  ⚠️ LOAD-BEARING
**Answer:** Local users table → auth seam + dev stub, real AD deferred.

**12. Cutover strategy?**  ⚠️ LOAD-BEARING
**Answer:** Big-bang.

**14. Environments & test data.**
**Answer:** Local dev only; a restored copy of prod data is available locally.

**16. Locations, and repository conventions.**
**Answer:** Legacy source ./legacy/ (read-only, lives in this same repo);
documents ./out/; target code this repo, new tree beside the legacy one.

**19. Code style / quality gates the target must enforce?**
**Answer:** Google Java Style Guide, enforced by google-java-format in Maven.
```

Then launch:

> Follow `0_PROJECT_CONTEXT_INSTRUCTIONS.md`. Intake: `./out/INTAKE.md`. Legacy app: `./legacy/`.
> App name: `EmployeeSearch`. Write `PROJECT_CONTEXT.md` and `state.json` to `./out/`.

*→ You get `PROJECT_CONTEXT.md` with constraints **C1** (DB reuse), **C2** (auth seam), **C3**
(Java style) — each carrying its own per-stage obligations, e.g. C1 → *Requirements:* capture
the schema verbatim; *Plan:* validate the mapping in the first data-store phase; *Implement:*
run validate-only, fix mappings not the DB — plus an initialized `state.json`.*
**Review these obligations carefully** — they are what every later stage actually executes, so
a missing obligation is a rule that silently won't be enforced.*

**Stage 1 — Requirements:**

> Follow `1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md`. Context: `./out/PROJECT_CONTEXT.md`,
> `./out/state.json`. Legacy app: `./legacy/`. Write the three requirements docs to `./out/`.
> App name: `EmployeeSearch`.

**Stage 2 — Design:**

> Follow `2_DESIGN_INSTRUCTIONS.md`. Context + requirements in `./out/`. Legacy app `./legacy/`
> for schema disambiguation only. Write the HLD and LLD to `./out/`.

**Stage 3 — Plan:**

> Follow `3_PLAN_INSTRUCTIONS.md`. Designs + requirements + context in `./out/`. Write
> `PLAN_EmployeeSearch.md` to `./out/` and populate `state.json phases[]`. Prefer ~5 phases.

**Stage 4 — Implement phase 1:**

> Follow `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md`. Plan/designs/requirements/context/state in
> `./out/`. **This is a phase.** Implement the next pending phase (P-1). Repo is this git
> repo; branch and open a PR.

*→ Agent builds P-1 on a branch, marks it `done`, opens a PR. You test it via the plan's P-1
test guide, then simply say:*

> accept P-1

*→ It merges the PR, records `accepted` + `acceptedUtc`, and confirms — no JSON editing.*

**Stage 5 — Review P-1** (independent run):

> Follow `5_REVIEW_INSTRUCTIONS.md`. Target: **P-1**. State/plan/design/requirements/context in
> `./out/`. Codebase is this repo. Write the review report to `./out/`.

*→ PASS → launch P-2. CHANGES REQUESTED → the findings are now in `state.json changeLog[]`;
your next Implement run reconciles and fixes them before/at P-2.*

### Example B — A post-phase edit (after P-2 was accepted)

You've accepted P-2 but realize you want a `department` filter on employee search:

> Follow `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md`. **This is a post-phase edit, not a new phase.**
> Add a `department` filter to the employee-search endpoint and screen. Plan/designs/
> requirements/context/state in `./out/`. Branch and open a PR.

*→ The agent runs the contradiction check. If the LLD already allows for it, it implements on
top (updating tests/docs/state, PR). If it's actually a requirement change, it tells you the
impact and the options (change-on-top / branch-from-a-stage / redo) and waits for your call.*

### Example C — Rerunning a stage you're unhappy with

**Revising your intake answers** (Stage 0 defaulted something you care about — say it assumed
no CI/CD, but you do have a pipeline). Edit **`INTAKE.md`** — Q15 becomes *"Respect existing:
GitHub Actions"* — then:

> Follow `0_PROJECT_CONTEXT_INSTRUCTIONS.md`. **Rerun.** Intake: `./out/INTAKE.md` (updated).
> Existing `./out/PROJECT_CONTEXT.md` and `./out/state.json`. Re-derive the constraints and
> their obligations accordingly.

*→ If later stages already ran, the agent logs a `changeLog` entry naming which docs are now
stale so they get reconciled or rerun.*

**Re-slicing a plan** that front-loaded too much into P-1:

> Follow `3_PLAN_INSTRUCTIONS.md`. **Rerun.** Existing plan + state in `./out/`. Additional
> Instructions: P-1 is too big — split the frontend out into its own later phase; keep P-1 to
> backend scaffold + DB validation + two endpoints only. Re-slice future phases only; leave any
> accepted phases untouched.

### Example D — Whole-build final review

After the final phase is accepted:

> Follow `5_REVIEW_INSTRUCTIONS.md`. Target: **whole-build**. All docs + state in `./out/`.
> Codebase is this repo. Emphasize security and requirements coverage. Write the report to `./out/`.

---

## Quick Reference — Who Writes What

| Artifact | Created by | You edit? | Agent edits? |
|---|---|---|---|
| `AGENTS.md` (your copy) | you, from the template | **add** project specifics only — never remove the invariants or the recording protocol | **never** |
| `0_INTAKE_TEMPLATE.md` | the method | no — copy it | **never** |
| `INTAKE.md` (your copy) | **you** | **yes — this is where answers live** | **never** (input only) |
| `PROJECT_CONTEXT.md` | Stage 0 | to fix constraints/obligations (rerun) | Stage 0 only — no other stage writes here |
| 3 requirements docs | Stage 1 | to answer open questions | Stage 1 rerun; Stage 4 for **small, unambiguous** edits its contradiction check authorizes |
| HLD / LLD | Stage 2 | **yes — design changes** | Stage 2 rerun; Stage 4 for **small, unambiguous** edits its contradiction check authorizes |
| `PLAN_<App>.md` (phase content) | Stage 3 | future phases only | reconciliation edits, statuses, stale test-guide fixes |
| `state.json` phases[] | Stage 3 (init) | **no hand-editing** — you authorize, it writes | all fields, incl. `accepted` on your explicit instruction |
| `state.json` edits[] | Stage 4 | **no hand-editing** — say "accept E-1" | appends each edit; `accepted` on your instruction |
| `state.json` changeLog[] | Stage 0 (init) | tell it what you changed | your notes, reconciliations, review findings (append-only) |
| `state.json` reviews[] | Review stage | no | Review appends |
| `state.json` progress | Stage 0 (init) | no | Stage 4 advances the high-water mark |
| Application code | Stage 4 | hotfixes → log them | yes (on a branch, via PR) |
| Review reports | Stage 5 | no | yes |

*(If you hotfix code or edit a design doc by hand, add a `changeLog` entry so the next run knows
the baseline moved.)*

---

## What Changed From Set 3

| Concern | Set 3 | Set 4 |
|---|---|---|
| Source/target stack | Hardcoded (.NET → Angular/Spring) | **Declared in Stage 0**, stack-agnostic |
| Constraints | Fixed C1/C2/C3 restated in every doc | **Project-supplied, by ID, with per-stage obligations** defined once in `PROJECT_CONTEXT.md`; stage files carry no constraint-specific rules |
| Ad-hoc chat (outside a stage) | Ungoverned — rules only loaded when a stage was invoked | **`AGENTS.md`** carries invariants + a routing rule; out-of-band edits still get logged |
| Cutover & coexistence | Not addressed (big-bang assumed) | **Load-bearing questions**; strangler-fig / parallel-run shape the design and phase slicing |
| UI appearance | Unspecified — each phase invented its own styling | Optional **UI sample** (Q23) → a **design language** in LLD §3b, stood up before feature screens and checked by Review |
| Integrations | Discovered ad hoc during extraction | Declared up front with **fixed vs. negotiable contracts** (`§8`) |
| Parity stance | Implicit | **Explicit**: strict parity (bugs preserved + flagged) vs. improvements allowed |
| CI/CD | Not addressed | **Explicit boundary** (respect / generate / none) |
| Load-bearing questions | Surfaced as open questions | **Questionnaire with defaults-or-hard-stop** |
| Status board & change log | Markdown tables in the plan | **`state.json`** (enables branching / lineage) |
| Phase acceptance | `done` (self) + `accepted` (human) | Same, but **exit criteria must be mechanical/falsifiable** |
| Post-phase edits | Absorbed via prompt notes | **Explicit phase-vs-edit classification + contradiction check** |
| Big changes | Agent recommends re-plan | Same, plus **change-on-top / branch / redo** options, **human-authorized** |
| Git workflow | "keep it in git" | **Mandated: branch + small commits + PR with descriptive body** |
| QA / Review | None | **Independent Stage 5** feeding findings back into the loop |
| Reruns | Plan/Implement footers | **Uniform Additional-Instructions rerun on every stage** |
