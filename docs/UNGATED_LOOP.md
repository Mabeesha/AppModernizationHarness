# Design Change — The Ungated Loop

*Status: **applied.** The harness, [DESIGN.md](DESIGN.md), [REQUIREMENTS.md](REQUIREMENTS.md)
and the three guides now describe this model; §10 records what it superseded. Kept as the
rationale — the *why*, which the instruction files deliberately don't carry.*

---

## 1. The problem

The harness gates the loop on `accepted` — a mark only the developer may set, meaning "I tested
this increment and it works". The next phase cannot start until the previous one carries it.

That gate is expensive in the one currency the developer actually has: **time**. It demands an
hour of manual testing before any further building can happen. So the developer either stops
building, or is pushed toward a false claim. Neither is what the mark was for.

Three further problems follow from it:

1. **`accepted` does four jobs at once** — it gates the next phase, triggers the PR merge,
   protects built code from being re-planned, and records that a human tested something. Only
   the last one is really about acceptance.
2. **Tracking is phase-shaped.** A phase is a batch of work, not a thing the app does. When a
   later phase changes a feature built earlier, phase-level acceptance cannot express it: `P-2`
   stays accepted forever even after `P-6` rewrites what it delivered.
3. **`HOW_TO_TEST.md` is a copy.** Its detailed steps are derived from the plan's per-phase test
   guides, which the harness itself calls the source of truth — then it is rewritten from
   scratch at every hand-off, forever.

## 2. The new model in one paragraph

Nothing blocks. Phases move `pending → in progress → done`, forward only, and what is built is
built. Testing stops being a gate and becomes a **record**, kept per feature rather than per
phase, in its own document. Merging moves to hand-off, with the developer's permission. Review
stops gating and becomes a report. The harness changes character: from a guarded pipeline to a
fast pipeline with good instruments.

## 3. Decisions

| # | Decision | Why |
|---|---|---|
| **UL-1** | **No `accepted` anywhere.** Phase status is `pending → in progress → done`, forward only. `acceptedUtc` is removed | The gate cost hours and bought a claim the developer was pressured to make. Deleting it removes the harness's only forced choice between working and lying |
| **UL-2** | **What is built is built.** The protection boundary for "never re-plan, never reopen" moves from `accepted` to `done` | One word instead of a two-tier rule. Also resolves an existing contradiction: the plan's sync rule protects `done` entries while §Refreshing says a refresh may re-slice anything not `accepted` |
| **UL-3** | **`FEATURE_STATUS.md`** — the Coverage Matrix leaves the plan, becomes its own document, and gains testing columns | The matrix is already feature-keyed, already survives every refresh, and the harness already calls it "the commitment" against the phase list's "forecast". A permanent record must not live inside a document that is repeatedly rebuilt |
| **UL-4** | **`accept P-N` ticks rows; it gates nothing.** Per-feature marking is also allowed | Restores an honest use for the word. Partial results ("search works, export doesn't") become expressible |
| **UL-5** | **A later phase or edit that changes a feature resets that row to untested** | Otherwise the record lies. This is the thing phase-level acceptance structurally could not do |
| **UL-6** | **A reported failure never rewinds a status.** It marks the row failed and becomes forward work | The last backwards transition in the system. Fixes are planned from now on, like every other change |
| **UL-7** | **The agent never merges unasked, and never asks.** Every PR is the developer's, to merge whenever they choose or not at all — and the agent does merge on an explicit "merge P-3", because refusing a direct instruction about their own repo buys nothing | Acceptance used to trigger the merge, and removing it appeared to leave the next phase with no base — which is why an earlier draft of this change invented a merge-at-hand-off permission step. UL-12 makes that unnecessary: a phase starts from the branch where the previous phase's code already is, so **no merge is needed for the pipeline to function.** Merging drops out of the harness entirely, and with it `mergePolicy`, `mergedUtc` and the permission question |
| **UL-8** | **Git is the truth; `state.json` is a cache.** Presence is checked by **content**, never by branch-merge status | The developer may merge or edit outside the harness, and should not have to report it. Squash and rebase merges make branch-based checks answer "not merged" when every line is in fact present. The harness already says this for the predecessor check; it just needs extending to merges the agent did not perform |
| **UL-9** | **`HOW_TO_RUN.md`** (renamed from `HOW_TO_TEST.md`) — how to build and run the app, plus light testing orientation. Updated only when running the app changes | Removes a duplicated document and a rewrite-from-scratch at every hand-off. Testing detail moves next to the tick box, in `FEATURE_STATUS.md` |
| **UL-10** | **Review reports; it never blocks.** No `reviewStatus`, no `remediated`, no `wholeBuild` object | The gate only ever fired for a developer who voluntarily ran Review. Findings still survive, via the change log the next run reconciles — the gate only changed *when* they were fixed, not *whether* |
| **UL-11** | **Every hand-off report carries two counts**: features awaiting testing, and open review findings | With no gates, visibility is the whole defence. Two numbers, always in front of the developer |
| **UL-12** | **Branch from the current branch, PR back at it, leave the developer on the new branch.** The agent names the branch and what it contains, in one line, before it starts | The developer's git state becomes the instruction, so nothing needs configuring. Whether they merged decides what happens next, with no rule about it: merged and standing on `dev` → the next phase starts clean; not merged → the next phase continues from the phase branch and stacks. Either way the predecessor's code is present, which is what makes UL-7 possible |
| **UL-13** | **`prTarget` stays as a human note that no rule reads** | Where work lands is decided by the branch the developer stands on, not by a field. An earlier draft of §12 claimed setting `prTarget` kept `main` clean — it never could, once UL-12 replaced it. Keeping the field documents intent; reading it would resurrect the setting UL-12 removed |
| **UL-14** | **"Work on this branch" is supported: no new branch, no PR** | Sometimes the developer wants the change where they are standing. Everything else is unchanged; `prUrls` stays `[]` and the PR body's history moves into the commit messages. Per repo under a `split` layout |
| **UL-15** | **Before branching, detect a branch that is already merged or gone from the remote, and propose the alternative** | UL-12 made the *unusual* path (never merging) frictionless and left the *common* one broken: the developer merges on the host, the host deletes the branch, their checkout stays on it, and every check in UL-8 still passes because the code is present. The next phase would then target a branch that no longer exists on the remote. This is the one place the branch-from-current rule needs the agent to look further than "what is checked out" |

## 4. Documents after the change

| Document | Holds | Written when |
|---|---|---|
| `state.json` | machine facts: status, branch, PRs, merges, reviews, change log | every run |
| `FEATURE_STATUS.md` | per feature: how to check it, which phase built it, tested or not | every hand-off (rows only) |
| `HOW_TO_RUN.md` | how to build, run and configure the app; where to start testing | only when running the app changes |
| `PLAN_<App>.md` | specification for work **not yet built**, incl. per-phase developer test guides | plan refreshes |

## 5. `FEATURE_STATUS.md`

Rows are keyed by **requirement ID / design element** — the keys that already flow from Stage 1
through Stage 3. Created by Stage 3 from the design's coverage checklist; rows are updated by
Stage 4 at hand-off and by the developer's word.

| Column | Values |
|---|---|
| `ID` | requirement ID / design element |
| `Feature` | one line, what it does |
| `How to check` | 1–3 concrete lines: URL / command / expected result |
| `Phase(s)` | every phase and edit that built or changed it |
| `Build` | `unscheduled`, `scheduled in P-N`, or `built in P-N` |
| `Tested` | `untested`, `passed <date>`, or `failed <date> — <symptom>` |

Rules:

- **Every row survives every refresh.** Rows move between phases; they are never deleted. An
  `unscheduled` row must be named in the plan's Risks & Open Questions (inherited, unchanged).
- **`accept P-N`** sets every row `built in P-N` to `passed <today>`. The agent states what is
  being attested to, per row, before writing it.
- **"search works" / "export failed — 500 on large sets"** marks a single row.
- A phase or edit that changes an existing feature **adds itself to `phase(s)` and resets
  `tested` to `untested`**.
- A `failed` row produces a change-log entry; the fix is scheduled as forward work — a minor
  edit or a new phase. No status is rewound.
- `how to check` stays short. A row needing a long walkthrough should be two rows.

## 6. `HOW_TO_RUN.md`

```markdown
# Running <AppName>
## Prerequisites            <- versions, tools, what must be installed
## Build & run              <- exact commands per part, ports, URLs
## Configuration            <- env vars, config files, where values come from
## Test data & accounts     <- seeded data, dev users, how to reset to a clean state
## Running the automated tests
## How to test by hand      <- 5-10 lines of orientation; points at FEATURE_STATUS.md
```

- The agent **runs these commands itself** at hand-off and fixes whatever is stale.
- It is **not** rewritten each hand-off — only when the way to build, run or configure the app
  actually changes.
- The plan's per-phase developer test guide stays the source for unbuilt work. At hand-off it is
  distilled into `FEATURE_STATUS.md` "how to check" cells, and then leaves with its phase.

## 7. The loop

```mermaid
sequenceDiagram
    participant D as Developer
    participant A as Build agent
    participant S as state.json
    participant F as FEATURE_STATUS.md
    participant G as Git

    D->>A: "Do P-3"
    A->>G: read the CURRENT branch; check it by CONTENT for P-2's work
    A-->>D: "Branching P-3 from <current>. Contains P-2's work."
    alt predecessor's work missing
        A-->>D: ask — branch from here anyway, or merge first?
    end
    A->>A: 0b reconcile · 0c refresh plan (default: unchanged)
    A->>G: branch from current, task-sized commits
    A->>A: run exit criteria (falsifiable)
    A->>S: status=done, branch, prUrls
    A->>F: rows built in P-3; rows P-3 changed reset to untested
    A->>G: push + open PR targeting the branch it came from
    A-->>D: report + 2 counts + PR link (+ any other open PRs)
    Note over D,G: the developer merges whenever they choose, or not at all
    Note over D,F: testing happens whenever — "accept P-3" ticks rows, gates nothing
```

**Branching — the whole rule, four lines, no configuration:**

1. **Read the branch that is currently checked out**, and name it in the report.
2. **Branch from it**, do the work, and **open the PR back at it.** Per repo under a `split`
   layout.
3. **Leave the developer on the branch created**, and stop. **Never merge.**
4. **Unless they said to work on the current branch** — then no branch, no PR; commit there.

Alongside step 1, check **by content** that the predecessor's work is present and say so in one
line: *"Branching P-3 from `phase/P-2`. Contains P-2's work. (Note: `dev` has 2 commits not in
this branch.)"* The agent stops only if that work is **missing**, and then it asks rather than
refuses — it never silently rebuilds.

**Why no merge is needed.** The next phase starts from the branch where the previous phase's code
already is. So an unmerged PR costs the pipeline nothing: if the developer merged and is standing
on `dev`, the next phase starts clean; if they didn't, it continues from the phase branch and
stacks. Merging is housekeeping the developer does on their own schedule, and the harness holds
no state about it.

**What that costs.** Never merging means phases can stack into a chain of open PRs. They are
landed **oldest first**: merging the bottom PR makes the host re-point the one above it at the base
branch, and so on until the chain is empty. The only mitigation is visibility — the hand-off report
names the other phases whose PRs are still open. There is no setting for this:
`context.repo.prTarget` records where work is headed and **no rule reads it**.

**The spent-branch check (UL-15).** Branching from the current branch is right, but "current" is
not enough on its own: after the developer merges a PR on the host, the host usually deletes that
branch while their checkout stays on it. The code is still present, so the content check passes and
nothing looks wrong — yet a PR opened against that branch targets something the remote no longer
has. So before branching, the agent also asks *is this branch finished?* and, if so, names the
branch it was merged into and waits:

> "You're on `phase/P-2`, which is already merged into `dev` and gone from the remote. I'd branch
> P-3 from `dev` instead — it has P-2's work. Confirm, or name another branch."

It never pushes a deleted branch back up to make a PR fit.

**Changed outside the harness.** The developer may merge, hand-fix a file, or resolve a conflict
without telling anyone; nothing needs keeping in step, because nothing records merges. The agent
still notices code it did not write, logs it (`origin: out-of-band`), and reconciles it at
Step 0b.

## 8. Review after the change

Review stays a separate, read-only session, invoked when the developer wants it. It may target a
built phase, an edit, or the whole build. Its report:

1. **Coverage** — `FEATURE_STATUS.md` rows built / scheduled / missing against what was asked for
2. **Quality findings**, graded Blocker / Major / Minor — as information
3. **Untested** — rows the developer has not ticked
4. **What I would fix before building further** — advice, plainly stated

Findings become change-log entries; the next build run reconciles and fixes them, tracked by the
existing `lastProcessedReviewNumber` high-water mark. Nothing is blocked.

## 9. `state.json` changes

- `phases[].status` / `edits[].status`: drop `accepted`, leaving `pending | in progress | done`
- `reviews[].result`: `pass | changes-requested` → **`clean | findings`**, since a review is no
  longer a verdict on a target
- **Removed:** `acceptedUtc`, `reviewStatus` (all three locations), the `wholeBuild` object
- **Added:** nothing. `prUrls` may now legitimately be `[]` (the no-PR case, UL-14),
  `context.repo.prTarget` survives as a note no rule reads (UL-13), and so do
  `repo.branchNaming`'s companions — PR target and required reviewers are recorded for humans,
  since the agent targets the branch it branched from and does not merge unasked
- **Unchanged:** `changeLog[]` (including its `origin` values), `progress` high-water marks,
  constraints, permanent IDs, append-only rules

## 10. What this supersedes

| Where | Currently | After |
|---|---|---|
| `DESIGN.md` DD-4 | two gates, agent then human | one gate: falsifiable exit criteria |
| `DESIGN.md` DD-6 | retrofit, never reopen `accepted` | retrofit, never reopen `done` |
| `DESIGN.md` DD-9 | one `HOW_TO_TEST.md`, regenerated each hand-off | `HOW_TO_RUN.md` + `FEATURE_STATUS.md` |
| `DESIGN.md` §7 | the review gate | deleted; Review reports |
| `REQUIREMENTS.md` R4.2, R4.3 | only the developer sets `accepted`; next phase blocked | **the IDs were reused, not retired** — R4.1 survives unchanged, and R4.2–R4.4 now state forward-only status, per-feature testing, and that a tested mark blocks nothing. An old reference to "R4.2" silently reads a different rule |
| `REQUIREMENTS.md` R5.1 | accepted phases drop to a Completed line | `done` phases do |
| `REQUIREMENTS.md` R8.3, R8.4 | Blockers gate; cleared by `remediated` | severities are information; findings ride the change log |
| `REQUIREMENTS.md` R10.2–R10.4 | one regenerated `HOW_TO_TEST.md` with Regression | `HOW_TO_RUN.md` + per-feature checks |

**Unchanged:** Stages 0–2 entirely; constraints and per-stage obligations (DD-1); state/content
split (DD-2); high-water marks (DD-3); permanent phase IDs (DD-5); contract changes as a
two-prompt flow (DD-7); `AGENTS.md` always loaded (DD-8); Review as a separate read-only session
(DD-11); documents amended in place (DD-12); the conflict ladder; falsifiable exit criteria.

## 11. Implementation checklist

| File | Work |
|---|---|
| `0_PROJECT_CONTEXT_INSTRUCTIONS.md` | schema edits per §9; constraint-retrofit paragraph keys on `done`; `prTarget` marked as read by nothing |
| `3_PLAN_INSTRUCTIONS.md` | delete §Two-Tier Acceptance; move Coverage Matrix out to `FEATURE_STATUS.md`; §2 Completed keys on `done`; fix "non-`accepted`" in §Refreshing; checklist items |
| `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` | remove entry gate and Blocker scan; rewrite §Starting From the Right Base as the four-line rule (branch from current, PR back at it, never merge, plus the no-PR case), content check **reported not gated**; delete the merge block from §Git Discipline; §Recording Developer Decisions → ledger marking; Step 2 → `FEATURE_STATUS.md` + `HOW_TO_RUN.md`; two counts and the open-PR line in the report; Definition of Done |
| `5_REVIEW_INSTRUCTIONS.md` | target any built work; verdict → report with coverage and untested sections; stop writing `reviewStatus` |
| `AGENTS_TEMPLATE.md` | invariants 4–6 (forward-only status, who authorizes a tested mark, never merge); rewrite §Recording What the Developer Tells You (table, guards) |
| `docs/DESIGN.md` | supersede DD-4/6/9, delete §7, add UL decisions, update the three diagrams and §9 |
| `docs/REQUIREMENTS.md` | R4, R5.1, R8.3–8.4, R10.2–10.4 |
| `README.md`, `DEVELOPER_GUIDE.md`, `USE_CASES.md`, `examples/INTAKE_EXAMPLE.md` | 25 `HOW_TO_TEST` references; acceptance narrative throughout |
| **`eval/`** | **Not Markdown, and therefore missed on the first pass.** `evalkit/checks/references.py` `RUNTIME_ARTIFACTS` (drop `HOW_TO_TEST.md`, add `HOW_TO_RUN.md` and `FEATURE_STATUS.md`) and `evalkit/vocab/status_values.txt` (drop `accepted`/`pass`/`changes-requested`, add the new values). The eval harness reads the instruction set **mechanically**, so a rename it does not know about produces a page of false blockers |

> **Lesson for the next change of this size:** grep the whole repo, not `--include=*.md`. Two
> Python files consume these documents as data, and every verification sweep on the first pass was
> scoped to Markdown. A stage's declared outputs are also machine-checked — `FEATURE_STATUS.md`
> had to be declared as a Stage 3 **Output**, in those words, or checks C/D report three stages
> consuming a document nothing produces.

## 12. Trade-offs accepted

- **No hard gates remain.** Nothing prevents a bad build from growing except the developer
  reading the reports. Defensible for a modernization build with one user and nothing deployed;
  it would not be for a team shipping to production.
- **Untested code reaches a branch only when the developer merges it there.** The agent never
  merges (UL-7), so nothing lands on `main` without a human clicking Merge — there is no
  agent-side protection to rely on and no setting that changes this. The mirror-image cost is
  that never merging leaves a chain of open PRs, landed oldest first (§7). The hand-off report
  naming the other open PRs is the whole of the visibility.
- **Two counts are the whole warning system.** They must appear in every hand-off report, or
  "no gates" becomes "no idea".
- **Prompt-only enforcement**, as before. Nothing validates `state.json` or the ledger.
