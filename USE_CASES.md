# The Modernization Harness by Example

**What to say, and what happens when you say it.**

The other two guides explain the method: [README.md](README.md) gets you running in five
minutes, [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) explains why it's built this way. This
one is different — it walks through the **situations you'll actually hit**, in order of how
likely you are to hit them, and shows the exact prompt plus what the agent does behind it.

Nothing here is new machinery. It's the same six stage files — plus the `AGENTS.md` sitting in
your project root — seen from your chair.

---

## First — the file that makes every scenario below work

Two files get copied into your project before anything else:

```bash
cp ModernizationHarness/AGENTS_TEMPLATE.md   ./AGENTS.md      # project root
cp ModernizationHarness/0_INTAKE_TEMPLATE.md ./out/INTAKE.md  # then fill it in
```

`INTAKE.md` you fill in once. **`AGENTS.md` is the one that changes how the scenarios below
behave** — and it's the easiest to skip, because nothing visibly breaks when you do.

Here's why it matters. Every rule in the six stage files applies **only while you are explicitly
running that stage**. The moment you're just chatting — *"accept P-2"*, *"add a department
filter"*, *"why is this test failing?"* — not one of them is loaded. `AGENTS.md` is the file the
agent reads in **every** session, and it carries the things that have to hold everywhere:

| What it carries | Scenarios that depend on it |
|---|---|
| **The recording protocol** — what `accept P-3` and `P-3 failed` each mean | 2, 4 |
| **The routing rule** — what happens when an agent is about to edit code or a pipeline document outside a stage run | 5, 6, 18, 19 |
| **The out-of-band recording rule** — your hand-fixes get logged | 18 |
| **The invariants** — legacy read-only, append-only history, forward-only status, only you authorize a tested mark, merge only what you were asked to, no secrets, templates are inputs, never mutate a reused schema | all of them |
| **The authority ladder** — who wins when sources contradict each other | Part 7 |

Skip it and the pipeline still runs. What you lose is everything that happens *between* the
stage runs — which is exactly where drift comes from.

---

## Before the scenarios: six words you need

| Word | What it means |
|---|---|
| **Phase** (`P-3`) | One planned increment of the build. Runnable and testable when it lands. |
| **Minor edit** (`E-1`) | A small change that touches no requirement, design contract, or plan scope. Ships like a tiny phase. |
| **`done`** | Built, and the agent's mechanical checks passed. It is the **final** status — nothing rewinds, and nothing waits on you. |
| **`FEATURE_STATUS.md`** | The ledger: one row per feature — how to check it, which phase built it, whether *you* have tested it. Only you authorize a `passed`/`failed` mark, and it blocks nothing. |
| **`state.json`** | The agent's memory: statuses, branches, PRs, merges, the change log, review records. **You never edit it by hand.** |
| **Retrofit phase** | A *new* phase that brings already-delivered code up to a changed design. `done` phases are never reopened. |
| **`AGENTS.md`** | Your copy of `AGENTS_TEMPLATE.md`, in the project root. Loads in *every* session — it governs ordinary chat, not just stage runs. |

**The three locations** every prompt refers to — name them once, they never change:
`./legacy/` (read-only source app), `./out/` (all documents + `state.json`), and the target
repo (where code, branches and PRs live). The examples below use those paths; substitute yours.

**How to read a scenario:** each one gives you the situation, the prompt to send, what happens
behind the scenes, and what is true afterwards. Prompts are copy-paste ready.

---

## Cheat sheet

| Your situation | What you send |
|---|---|
| Starting a brand-new project | Copy `AGENTS.md` and `INTAKE.md` into place, then run Stages 0→3 once each |
| Build the next planned increment | `run stage 4` |
| Merge the phase you just got | Nothing to send — the PR is yours, merge it or leave it |
| Work on the branch you're on | `…do it on this branch, no PR` |
| You tested it and it works | `accept P-3` — or `accept P-3, P-4` — or `search works` |
| You tested it and it's broken | `P-3 failed — the search box returns 500` |
| You want a small tweak | Just describe it. The agent decides if it's a minor edit. |
| You want to change how something *works* | Rerun Stage 2 (design), then run the next phase |
| You want an independent audit | `run stage 5 on P-3` — **in a fresh session** |
| You're unhappy with a stage's output | Rerun that stage with what you want different |
| You changed an intake answer | Edit `INTAKE.md`, rerun Stage 0 |
| You fixed something by hand | Tell the agent — it logs it so the next run isn't surprised |

---

# Part 1 — The normal loop

This is 90% of your time. Two prompts per phase.

## Scenario 1 · Build the next phase

**Situation:** P-2 is built. You want P-3. (Whether you've tested P-2 is irrelevant — nothing
waits on it.)

**You send:**

```
run stage 4
Plan/designs/requirements/context/state in ./out/. Repo is this repo; branch and open a PR.
```

You don't have to name the phase. You don't have to say whether it's a phase or an edit — the
agent works that out itself.

**Behind the scenes**, before it writes a line of code:

1. **Classifies** the work (Step 0a) — this matches a planned phase, so: a phase.
2. **Checks its footing.** Which branch are you standing on, and does it *actually contain*
   P-2's code — checked by looking for the files and symbols P-2 delivered, not by trusting a
   branch name or a merge record. It tells you in one line:
   *"Branching P-3 from `dev`. Contains P-2's work."* Nothing here is a gate: if P-2's work is
   genuinely missing, it asks rather than guessing.
3. **Reconciles** (Step 0b) — reads everything added to `state.json`'s change log and reviews
   since the last run, using a high-water mark so it never re-applies the same entry twice.
4. **Refreshes the forward plan** (Step 0c) — the important one. It asks *"are the remaining
   phases still the right shape?"* With nothing new since last time, the answer is one line:
   **"plan unchanged — building P-3."** It will never silently re-slice.
5. Branches, implements task by task with a commit each, writes tests, runs the phase's
   **exit criteria** (mechanical checks it can genuinely fail — the only gate in the pipeline),
   updates the `FEATURE_STATUS.md` rows it delivered or changed, marks the phase `done`, opens a
   PR against the branch it came from, asks whether to merge, and **stops**.

**Afterwards you have:** a branch, an open PR, `P-3` at `done` in `state.json`, and a report
telling you what was built, how to run it, **which ledger rows this phase put at risk**, and
**two counts** — features awaiting your testing, and open review findings.

> It will not roll into P-4. That's the whole point of the loop.

---

## Scenario 2 · Merging, and recording your testing

Two separate things, and **neither one blocks anything**.

### Merging — entirely yours

**Situation:** P-3 landed and its PR is open, pointing at whatever branch you were standing on.

**There is no prompt for this.** The agent never merges. You click Merge in the web UI whenever
you like, or you don't. Squash, rebase or merge commit — all fine; the agent looks for the *code*
on the branch, not for a merge commit, so nothing gets confused.

**And nothing waits on it.** Leave the PR open and the next phase branches from this branch and
continues from here. Merge it and check out your base branch, and the next phase starts from
there. **Either way the next phase has P-3's code** — which is exactly why no merge is needed.

**The cost of never merging** is a chain: P-4 pointing at P-3's branch, P-5 at P-4's, and so on.
They land bottom-up when you get to them. Each hand-off report names the other phases whose PRs
are still open, so you can see how tall the stack has grown.

### Want it on the branch you're already on?

```
Add the department filter — do it on this branch, no PR.
```

Then there's no new branch and no PR: commits land where you are standing, `prUrls` stays empty,
and the history that would have gone in the PR body goes into the commit messages instead.

### Recording that you tested something

**Situation:** you got round to walking the `untested` rows in `FEATURE_STATUS.md` and they
worked.

```
accept P-3
```

It ticks every ledger row P-3 built — `passed <today>` — and tells you plainly what you just
attested to. **P-3 stays `done`;** nothing in `state.json` changes, because the code was already
built and this is a statement about *you*, not about the code.

You have three shapes available:

| You say | What it ticks |
|---|---|
| `accept P-3` | every row P-3 built |
| `accept P-3, P-4, P-5` | the same, for each in turn — **deferring testing is supported** |
| `search works` | that one row |

> **Where this rule actually lives:** `AGENTS.md` — not the stage files. This nearly always
> happens in ordinary chat: you type *accept P-3* between runs, when no stage document is loaded
> at all. So the protocol has to sit in the file that is always there. Stage 4 points back to it
> rather than restating it, precisely so the two can never drift apart.

**Two things it deliberately won't do:**

- **Accept the vague bulk.** "Accept everything so far" usually means nothing was tested. It
  turns that into the explicit list and asks you to confirm the count.
- **Fold it into another request.** Ask for P-4 and it won't offer to tick P-3's rows along the
  way — at that moment your goal is P-4, which makes *yes* reflexive. It has no reason to ask
  anyway, because nothing is blocked.

---

## Scenario 3 · Audit a phase independently

**Situation:** P-3 is built. Before going further, you want a second opinion — whether or not
you have tested it yourself.

**You send — in a brand-new chat session**, not the one that built it:

```
run stage 5 on P-3
State/plan/design/requirements/context in ./out/. Codebase is this repo. Write the report to ./out/.
```

**Behind the scenes:** an agent with no memory of writing the code builds the project, runs the
tests, and audits four areas — requirements coverage, tests, security, static performance
(by inspection; no load testing) — plus every constraint's *Review* obligation. It **changes no
code**. It writes `REVIEW_R-1_<App>_P-3.md`, appends to `reviews[]`, and turns each Blocker or
Major into a change-log entry the next build run will pick up.

**You get** PASS, or CHANGES REQUESTED. What happens next depends on severity — see Part 5.

> Run it in the same session that built the code and you get a self-review, which is worth
> nothing. That's why the instruction says separate run.

---

# Part 2 — The phase isn't right

## Scenario 4 · It failed your testing

**Situation:** you followed the test guide, step 4 blew up.

**You send:**

```
P-3 failed — step 4, employee search returns a 500 when the query is empty
```

**Behind the scenes:** the agent sets `P-3` back to `pending`, records your note, and
**leaves the branch and PR open**.

**Then re-run it:**

```
run stage 4 — re-run P-3 with the failure note.
```

**P-3 stays `done`, and is never reopened** — the code is built, and rewinding a status would
tell every later run that work is still pending. Instead the ledger row reads
`failed — search returns 500`, a change-log entry records it, and the **fix is planned forward**:
a minor edit if it touches no contract, a reconciliation task folded into the next phase run, or
a new phase if it's large. Whatever fixes it puts that row back to `untested` for you to
re-check.

**Be specific about the symptom.** "P-3 failed" alone gives the agent nothing to reproduce.
Naming the `FEATURE_STATUS.md` row and what you saw is the cheapest thing you can do here.

---

## Scenario 5 · It works, but you want a small change

**Situation:** the search screen says "Emp. ID". You want "Employee ID".

**You send** — no ceremony, just ask:

```
The search results column header should read "Employee ID", not "Emp. ID".
```

**Behind the scenes:** the agent classifies it in Step 0a. Does it touch a requirement, a
design contract, or plan scope? A label doesn't. So it's a **minor edit**:

- gets its own id — `E-1` — in `state.json edits[]`, recorded against the phase it follows;
- gets its own branch, its own small commits, its own PR;
- updates the `FEATURE_STATUS.md` rows it changed — including **resetting them to `untested`**,
  because an edit changes delivered behavior exactly as a phase does;
- and behaves **exactly like a phase** otherwise: same merge policy, and you can point Review at
  it as a target in its own right. You record testing against the **feature rows** it touched,
  not against `E-1` itself.

**The test is authority, not size.** A one-line change to an endpoint's response shape is a
contract change (Scenario 6). A hundred-line refactor behind a stable interface is not. If the
agent finds itself weighing whether your request contradicts the design, that's its signal that
this is *not* a minor edit.

---

## Scenario 6 · Your change touches a contract

**Situation:** you ask for the search endpoint to also return the employee's department, which
the LLD doesn't specify.

**You send:** the request, in plain language, same as Scenario 5.

**Behind the scenes:** the agent classifies it as touching a **design contract** — and then
does something that surprises people the first time: **it doesn't build it, and it doesn't edit
the design document either.** It:

1. says precisely what would have to change, and in **which document** (here: LLD §1);
2. names the delivered phases the change invalidates, if any;
3. recommends the owning stage — *"rerun `2_DESIGN_INSTRUCTIONS.md` with this change"*;
4. tells you what happens after that — *"then run the next phase; Step 0c will plan it"*;
5. logs the request to the change log, and **stops**.

**This is a two-prompt flow by design, and the pause is the point.** It's where you catch the
design being amended into something you didn't mean, *before* any code is planned around it.

The one carve-out: a genuinely *clarifying* doc fix — a typo'd column name, a blank the design
plainly intended to fill — the agent makes directly, logs, and moves on. If it has to reason
about whether the change alters behavior, it doesn't qualify.

**What to do next:** Scenario 7.

---

# Part 3 — The design moves mid-build

This is the case everyone worries about. It's routine, and it costs **exactly one extra prompt**.

## Scenario 7 · Change how something works, five phases after it was built

**Situation:** you're about to start P-6. Auth was built in P-3 as a local-table stub, and P-5's
endpoints use it. You now need real OIDC against Keycloak.

### Prompt 1 — change the design

```
rerun stage 2 — change auth from the local-table stub to OIDC
against Keycloak; bearer tokens; keep the users table for authorization only.
Context + requirements + state in ./out/.
```

**Behind the scenes:**

- The HLD and LLD are **amended in place** — filenames never change, git holds the history.
- A `## 0. Revision History` row is added naming what changed, why, and — the load-bearing part
  — **which delivered phases it invalidates**: here, `P-3, P-5`. The agent reads `state.json`
  to determine that rather than guessing.
- `stages.design.rerunCount` is bumped and a change-log entry is written.
- **No code is touched. The plan is not edited.** Design doesn't get to plan its own retrofit.

> **Be specific.** "Change the auth mechanism" does not determine a design — protocol, IdP,
> token vs. session, what happens to existing credentials, and the effect on already-built
> endpoints are all still open. The agent will ask you or record explicit `ASSUMPTION:`s. Answer
> it properly here; everything downstream gets built to whatever is decided.

### Prompt 2 — run the next phase, exactly as always

```
run stage 4
```

**Behind the scenes:** Step 0c reads that revision-history row — this is the handoff that makes
a document change land in the code — and **proposes a re-slice**:

> "The LLD gained a revision affecting P-3 and P-5. I propose adding **P-8 — Migrate auth seam
> to OIDC**, run **before P-6**, and adjusting P-6 and P-7 to build against bearer tokens.
> Approve?"

You approve. It builds P-8, rewrites the auth rows' checks in `FEATURE_STATUS.md` and resets
them to `untested`, and opens a PR. Merge it, and ask for the next phase to get P-6.

**Three things that deliberately don't happen:**

| | Why |
|---|---|
| **P-3 is never reopened** | What is built is built. The retrofit is new work that supersedes it, and the rows it changes go back to `untested`. |
| **Nothing is renumbered** | The retrofit is `P-8` even though it runs before `P-6`. IDs are permanent so PRs, branches and review records keep meaning what they said. Execution order lives in the plan. |
| **No work silently vanishes** | The `FEATURE_STATUS.md` rows for auth move from `built in P-3` to `built in P-8`. Rows move; they are never deleted. |

---

## Scenario 8 · A *requirement* was wrong, not the design

**Situation:** you discover the legacy app rounds overtime differently than the requirements say.

**You send:**

```
rerun stage 1 — BR-14 is wrong: overtime rounds
to the nearest 15 minutes, not up to the hour — see ./legacy/Payroll/OvertimeCalc.cs:88.
```

**Behind the scenes:** the three requirements docs are amended in place (not regenerated — you'd
lose curated content), a Revision History row names the delivered phases affected,
`stages.requirements.rerunCount` is bumped, and a change-log entry is written.

**Then usually one more step:** a requirements change normally needs the **design rerun next**
(Scenario 7, prompt 1), because the design was built on the old rule. The agent says so in its
report. After that, the next phase run plans the retrofit as usual.

---

## Scenario 9 · The change arrives while a phase is half-built

**Situation:** P-6 is mid-run with an open branch when you realize auth has to change.

**Don't stack two changes on one branch.** Pick one:

- **Land P-6 as-is** if it's genuinely unaffected — merge it, then do Scenario 7.
- **Reset the branch**, do the retrofit, then redo P-6.

Redoing a half-built phase is cheap, because nothing depends on it yet. That's what the small
you: nothing you'd have to unpick has been certified yet.

---

## Scenario 10 · The change is too big for a retrofit

**Situation:** at P-6 you decide the monolith should have been microservices.

**What happens:** the agent will **tell you so rather than proposing a retrofit that can't
work.** No incremental path saves you when the change invalidates the decision everything is
shaped around. The honest answer:

```
rerun stage 2 — <the new architecture>.
```
```
rerun stage 3 — re-slice the remaining work against the revised design.
Existing plan + state in ./out/.
```

…and take the hit that a lot of the build is being redone. This is rare. When it happens, an agent
that cheerfully proposed a small retrofit would be lying to you.

**The agent will never unilaterally decide to redo large amounts of work.** Scope decisions
bigger than "absorb this into the current run" are yours.

---

# Part 4 — Re-running a stage

Every stage takes a rerun. The shape is always the same: **say which stage, say "Rerun", say
what you want different.** Documents are amended in place; that stage's `rerunCount` goes up; a
change-log entry tells downstream runs the ground moved.

## Scenario 11 · Stage 0 answered something for you and got it wrong

**Situation:** the hand-off report's *"Answered without you"* list says CI/CD defaulted to
"none". You actually have GitHub Actions.

**Do this — and note where the edit goes:**

1. **Edit `INTAKE.md`** — Q15 becomes *"Respect existing: GitHub Actions."*
2. Then:

```
rerun stage 0 — intake: ./out/INTAKE.md (updated).
Existing ./out/PROJECT_CONTEXT.md and ./out/state.json. Re-derive the constraints and their
obligations accordingly.
```

**Why `INTAKE.md` and not `PROJECT_CONTEXT.md`?** The flow is one-way:
**`INTAKE.md` → agent → `PROJECT_CONTEXT.md §5`.** Your answers live in the intake; §5 is a
*record* of what the last run decided, including which answers the agent supplied for you.
Editing §5 changes the record, not the input — and the next rerun would read your stale intake
and undo it.

**Behind the scenes:** the agent re-reads the intake fresh, diffs the new answers against §5,
reports what actually changed, bumps `stages.context.rerunCount`, and — if later stages already
ran — logs a change-log entry naming which documents are now stale so they get rerun or
reconciled.

> **Always read the "Answered without you" list after Stage 0.** Those are decisions you never
> made, and they propagate into constraints and every downstream stage.

---

## Scenario 12 · P-1 is too big

**Situation:** you read the plan and phase 1 is half the application.

**You send:**

```
rerun stage 3 — P-1 is too big; split the frontend out into its own later phase and keep
P-1 to backend scaffold + DB validation + two endpoints only. Re-slice future phases only;
leave any delivered phases untouched.
```

**Behind the scenes:** the planner re-slices phases that **haven't started**. Delivered phases are
history — they live as one-line entries in the plan's §2 Completed and are never re-planned. New
phases take the next unused IDs. **`FEATURE_STATUS.md`** carries forward whole: rows may move to
different phases, but not one row is deleted.

**Cheapest moment to do this is before any code exists.** Sanity-check the slicing when the plan
first lands: is P-1 genuinely small? Are the features you need to see early actually early?

**Mid-build you usually don't need this prompt at all** — Step 0c is already re-checking the
remaining plan before each build run, and will propose a re-slice when something changed.

---

## Scenario 13 · You just don't like an output

**Situation:** the design chose microservices; you want a modular monolith. Or the requirements
skated over the reporting module.

Same pattern for any stage:

```
rerun stage 2 — use a modular monolith, not microservices.
```
```
rerun stage 1 — go deeper on the reporting
module — the current pass missed the scheduled export.
```

Reruns of Stages 1 and 2 add a Revision History row naming the delivered phases invalidated —
which is what makes the change reach the code, via Step 0c, instead of sitting in a document
nobody rebuilt against.

---

# Part 5 — Review findings

## Scenario 14 · Review found a Blocker

**Situation:** the P-3 review came back FINDINGS with 1 Blocker — the frontend calls an
endpoint shape the backend doesn't serve.

**What's true immediately:** nothing is blocked. A Blocker means *"I would not build anything
further on this"* — said plainly, with reasons, in the report — but the pipeline does not enforce
it. Ask for P-4 and you will get P-4. **The judgement is yours.**

The finding is not lost, though: Review wrote it into `state.json` as a change-log entry, and the
next build run picks it up as reconciliation work whatever else that run is doing. Every hand-off
report also counts open findings for you.

**So you have two sensible moves.** Fix it first:

```
run stage 4 — address the R-1 findings on P-3.
```

…or carry on and let it ride along:

```
run stage 4
```

which builds P-4 **and** folds the R-1 fixes in as reconciliation, because unprocessed findings
are input to every run. Fixing a broken foundation first is usually right; the harness just
doesn't force it on you.

**Then re-review, in a fresh session:**

```
run stage 5 on P-3 — re-review after the R-1 fixes.
```

A claim in a hand-off report that something was fixed is **a claim awaiting confirmation, never
a verdict**. The re-review reads the earlier findings and verifies those specific fixes.

> With no hard gates left in the pipeline, Review is your main independent check. Run it more
> often than you think you need to — and read the *"what I would fix before building further"*
> section, because nothing else will stop you.

## Scenario 15 · Review found Majors but no Blockers

**Nothing is gated.** Carry on:

```
run stage 4
```

The Majors ride along: Step 0b folds them into that run's reconciliation and fixes them
alongside the new phase. Stalling a sound build over non-critical findings costs more than it
saves — which is exactly why the two severities are recorded separately.

## Scenario 16 · Review a minor edit on its own

An edit ships code, so it's a review target like any other:

```
run stage 5 on E-1
```

Worth doing when an edit turned out bigger or more delicate than "a label".

## Scenario 17 · The final whole-build review

**Situation:** the last phase is delivered. Is the build actually complete?

```
run stage 5 on the whole build
Codebase is this repo. Emphasize security and requirements coverage. Write the report to ./out/.
```

**Behind the scenes**, in addition to the four areas, a whole-build review does something no
other target does: **it audits `FEATURE_STATUS.md` itself.**

- Any row still marked `unscheduled` is a **Blocker** — that's work that was never delivered and
  no longer has a phase that would deliver it.
- Any row that existed in an earlier version of the ledger and has since **disappeared** is also
  a Blocker — found by reading the plan's git history. That's work a refresh silently dropped.

This is the check that makes "the plan is a rolling forecast" safe. The phase list is allowed to
move; **the matrix is the commitment.**

---

# Part 6 — Outside the process

## Scenario 18 · You fixed something by hand

**Situation:** you edited a connection string yourself at 11pm rather than opening a session.

**Tell the agent next time you're in:**

```
Heads up: I hand-fixed the JDBC URL in application-local.yml myself.
```

**Behind the scenes:** a change-log entry, author `developer`, origin `out-of-band`.

**Why it matters:** the next build run reconciles against that log to work out what moved since
it last ran. An unrecorded change makes its baseline silently wrong — it may "fix" your fix, or
build on an assumption that no longer holds. **Skipping the process is your call; skipping the
record isn't.**

The same applies if you ask the agent to change code directly outside a stage run. With
`AGENTS.md` loaded, it'll ask first:

> "This changes built code. Run it through `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` — branch,
> tests, docs, state, PR — or make the change directly?"

Say "directly" and it does — and still logs it.

## Scenario 19 · You just want to ask a question

**Ask.** Questions, explanations, diagnosis and running tests are free — no stage, no gate, no
ceremony. That's most of what you'll do between phases.

The gate sits **in front of the edit, not in front of the question**, because debugging so often
turns into editing halfway through. This is `AGENTS.md`'s routing rule, and it's the reason that
file has to be loaded in every session — no stage document is open during a conversation like
this one. The agent classifies at the moment it's about to write:

| What you're doing | What happens |
|---|---|
| Asking, explaining, diagnosing, running tests | Just done. |
| It's about to change **target code** | It asks: phase process, or directly? |
| It's about to change a **pipeline document** (requirements, HLD, LLD) | It declines and points you at the stage that owns it |
| It's about to change the **plan's remaining phases** | That's Stage 4's job — it proposes at Step 0c and applies once you approve |

That third row is the one that saves you most often. An agent casually editing the LLD breaks
the contract that both Implement and Review judge everything against.

**The carve-out worth knowing:** that rule governs **ad-hoc requests**. It does *not* bind a
stage that legitimately owns those edits — Stage 4 really does rewrite the plan's remaining
phases at Step 0c (with your approval), and Stages 0–3 and 5 write the documents they own. The
rule exists to stop casual edits, not to freeze the pipeline.

## Scenario 20 · You want to add a rule mid-build

**Situation:** four phases in, you decide you want an 80% line-coverage gate.

That's a **constraint**, and constraints are Stage 0's:

1. Edit `INTAKE.md` Q19 with the full rule — metric and threshold, scope (whole codebase vs.
   changed code), exclusions, enforcement (build fails / CI-only / advisory), and from which
   phase it binds. A vague "good coverage" isn't enforceable and the agent will raise it as an
   open question rather than inventing a number.
2. Rerun Stage 0 (Scenario 11).

**Behind the scenes:** a new constraint gets a new ID (`C4` — existing IDs are never renumbered)
carrying its **per-stage obligations**: what Requirements, Design, Plan, Implement and Review
must each *do* about it. That obligations list is the only place constraint-specific rules
live — which is why adding one needs no edit to any stage file.

**The part worth knowing:** a bar added late binds from the **next unstarted phase**, not
retroactively. Delivered phases are not reopened to meet it. Bringing their code up to the
bar is either a **retrofit phase** you approve at the next Step 0c, or an explicit scope-out
recorded in the plan's Risks section — the constraint has to say which. And the agent may not
lower the threshold, widen the exclusion list, or disable the gate to go green; if the bar can't
be met honestly it stops and asks you.

## Scenario 21 · Your team has house rules

**Situation:** your org requires a Jira ticket in every branch name, PRs must target `develop`
rather than `main`, and you want the agent to run `make verify` before it ever says "done".

There are **two different homes** for that, and picking the wrong one costs you a rerun:

| The rule is… | It belongs in | How it gets there |
|---|---|---|
| A **repository convention** — branch naming, PR target branch, commit format, required reviewers | `PROJECT_CONTEXT §3` | Answer intake **Q16**, rerun Stage 0. Stage 4 reads its Git Discipline defaults from there and honors yours instead |
| **How the agent should work with you** — house practices, a domain glossary, an extra check before hand-off | **your `AGENTS.md`** | Edit it directly. It's yours, and it loads in every session |

**The one rule about editing `AGENTS.md`: add, don't remove.** Append your project specifics
freely. Never delete the invariants, the recording protocol, or the authority
ladder — the stage files deliberately point *back* at them instead of restating them, so cutting
a section out of `AGENTS.md` leaves a hole rather than a relaxed rule. Stage 4's "Recording
Developer Decisions" section, for instance, is deliberately a pointer rather than a copy — it
names the protocol's home in `AGENTS.md` and adds only the two details specific to building.

**The agent never writes to this file.** It's the one document in the set that's yours alone.

---

# Interlude — the six invariants

These live in `AGENTS.md`, which means they hold in **every** session — a formal stage run, or
you asking a question at midnight:

1. **The legacy source is read-only.** Never modified, moved, or deleted — even when it shares a
   repository with the target code. The new tree gets built beside it.
2. **`INTAKE.md` and the `*_TEMPLATE.md` files are inputs, never written to.** Resolved answers
   live in `PROJECT_CONTEXT §5`.
3. **`changeLog[]` and `reviews[]` are append-only.** History is corrected by appending
   something that supersedes it, never by rewriting. And you never hand-edit `state.json` at all.
4. **Status moves forward only** — `pending` → `in progress` → `done`, and `done` is terminal.
   **Only you authorize a `passed`/`failed` mark** in `FEATURE_STATUS.md`, and it blocks nothing.
5. **No secrets anywhere** — not in code, documents, `state.json`, commit messages, or PR bodies.
   Connection strings and IdP config come from environment or profiles.
6. **Never mutate a reused database's schema.** Where a data-reuse constraint is in force, you
   fix the mapping, never the database.

If you ever catch an agent breaking one of these, the likeliest cause isn't the stage file —
it's that `AGENTS.md` isn't in the project root, or someone trimmed it.

---

# Part 7 — When the agent stops you

These aren't failures. Each one is a specific trap the loop exists to prevent.

| It stops because | What it says | What you do |
|---|---|---|
| The **branch is missing** the predecessor's work | "I'm on `experiment/x` and P-3's code isn't here" | Switch branch, merge P-3, or tell it to build here anyway |
| Your request touches a **contract** | "This changes LLD §1 — rerun Stage 2" | Rerun the design, then the next phase (Scenarios 6, 7) |
| A plan re-slice it proposed **hasn't been approved** | It builds the phase as it stands, or stops | Approve the proposal, or tell it to build as planned |
| Sources **conflict** | "The plan says X, the LLD says Y" | Decide. It reports conflicts, it doesn't silently pick a side |
| A **constraint** can't be honored | "Honoring C1 would break the endpoint contract" | Constraints win — this needs your decision or a design change |
| An input is **missing or ambiguous** | "Two candidate `state.json` files — which?" | Point it at the right one |
| You asked for **two units of work** | It does one and stops | One phase or one edit per run. Always. |

**On that "sources conflict" row**, the ladder is fixed and lives in `AGENTS.md`:
**a constraint in `PROJECT_CONTEXT §4` always wins**, then plan → LLD → HLD → requirements →
the rest of the context. A material conflict is *reported, never silently resolved* — which is
why you get a question instead of a guess.

**One more it will refuse outright:** anything that modifies the legacy source (invariant 1
above). Read-only in every stage, even when the legacy code shares a repository with the
target — the agent branches and commits in that repo, but no commit of its own touches legacy
files.

---

## The six habits that make this smooth

1. **Copy `AGENTS.md` into your project root — and don't gut it.** It's the only thing governing
   the agent *between* stage runs, which is most of your session time.
2. **Watch the two counts** in every hand-off report — features awaiting testing, and open
   review findings. Nothing blocks, so those numbers are your only standing warning.
3. **Never hand-edit `state.json`.** Say what happened; the agent writes it and confirms.
4. **Keep `./out/` and `state.json` in git.** Documents are amended in place, so git is the
   *only* history of superseded designs and plans — and it's what reconciliation diffs against.
5. **Read the report's at-risk rows.** That's the agent telling you which `FEATURE_STATUS.md`
   rows this phase could have broken — it resets them to `untested` for you. Cheaper than
   re-walking the whole ledger.
6. **Expect phase IDs to stop being sequential.** A retrofit added as `P-8` may run before `P-6`.
   That's deliberate. The plan holds the running order; the ID holds the identity.

---

**Want the reasoning behind any of this?** → [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
**Just want to start?** → [README.md](README.md)
