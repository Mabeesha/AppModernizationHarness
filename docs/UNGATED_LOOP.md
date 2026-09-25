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
| **UL-7** | **Merge at hand-off, on the developer's permission** (`context.repo.mergePolicy`: `ask` or `auto`, default `ask`) | Acceptance was what merged the PR; removing it leaves merging with no trigger, and the next phase with no base. Permission costs one word and claims nothing about testing |
| **UL-8** | **Git is the truth; `state.json` is a cache.** Presence is checked by **content**, never by branch-merge status | The developer may merge or edit outside the harness, and should not have to report it. Squash and rebase merges make branch-based checks answer "not merged" when every line is in fact present. The harness already says this for the predecessor check; it just needs extending to merges the agent did not perform |
| **UL-9** | **`HOW_TO_RUN.md`** (renamed from `HOW_TO_TEST.md`) — how to build and run the app, plus light testing orientation. Updated only when running the app changes | Removes a duplicated document and a rewrite-from-scratch at every hand-off. Testing detail moves next to the tick box, in `FEATURE_STATUS.md` |
| **UL-10** | **Review reports; it never blocks.** No `reviewStatus`, no `remediated`, no `wholeBuild` object | The gate only ever fired for a developer who voluntarily ran Review. Findings still survive, via the change log the next run reconciles — the gate only changed *when* they were fixed, not *whether* |
| **UL-11** | **Every hand-off report carries two counts**: features awaiting testing, and open review findings | With no gates, visibility is the whole defence. Two numbers, always in front of the developer |
| **UL-12** | **Branch from the current branch; the PR targets it.** The agent names the branch and what it contains, in one line, before it starts | The developer's git state becomes the instruction, so nothing needs configuring. Merging returns them to the base branch and the next phase starts clean; not merging leaves them on the phase branch and the next phase stacks — automatically, with no rule about stacking and nothing stalled |

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
| `id` | requirement ID / design element |
| `feature` | one line, what it does |
| `how to check` | 1–3 concrete lines: URL / command / expected result |
| `phase(s)` | every phase and edit that built or changed it |
| `build` | `unscheduled`, `scheduled in P-N`, or `built in P-N` |
| `tested` | `untested`, `passed <date>`, or `failed <date> — <symptom>` |

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
    A-->>D: report + 2 counts + "may I merge P-3?"
    opt mergePolicy = ask
        D->>A: "merge P-3"
    end
    A->>G: merge
    A->>S: mergedUtc
    Note over D,F: testing happens whenever — "accept P-3" ticks rows, gates nothing
```

**Branching.** Three lines, no configuration:

1. **Branch from the current branch; the PR targets it.** Per repo under a `split` layout.
2. **Check by content that the predecessor's work is present, and report it** — one line, every
   run: *"Branching P-3 from `phase/P-2`. Contains P-2's work. (note: `dev` has 2 commits not in
   this branch.)"* The agent only stops if that work is **missing**, and then it asks rather
   than refuses.
3. **At hand-off it asks to merge.** Yes → the developer lands back on the base branch and the
   next phase starts clean. No → they stay on the phase branch and the next phase stacks.

Nothing stalls, nothing is invented, nothing is configured. `context.repo.prTarget` stops being
a rule the instructions read; it stays as a human-facing note about where work eventually lands.

**Merging.** Under `ask`, the agent requests permission in its hand-off report and again at the
start of the next run if still unmerged; declining is not a blocker, it just means the next phase
stacks. Under `auto`, it merges at hand-off without asking. The existing exception is unchanged:
where the repository requires reviewers or green CI, the agent does not merge and says the merge
is the developer's.

**Merged or changed outside the harness.** The agent checks the branch by content, records what
it finds (`mergedUtc`, or a change-log entry with `origin: out-of-band`), reconciles any code it
did not write, and continues. The developer never has to report their own actions. If built work
is **missing**, the agent stops and asks — it never silently rebuilds.

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
- **Removed:** `acceptedUtc`, `reviewStatus` (all three locations), the `wholeBuild` object
- **Added:** `mergedUtc` on `phases[]` and `edits[]`; `context.repo.mergePolicy`
- **Unchanged:** `changeLog[]`, `reviews[]`, `progress` high-water marks, constraints, permanent
  IDs, append-only rules

## 10. What this supersedes

| Where | Currently | After |
|---|---|---|
| `DESIGN.md` DD-4 | two gates, agent then human | one gate: falsifiable exit criteria |
| `DESIGN.md` DD-6 | retrofit, never reopen `accepted` | retrofit, never reopen `done` |
| `DESIGN.md` DD-9 | one `HOW_TO_TEST.md`, regenerated each hand-off | `HOW_TO_RUN.md` + `FEATURE_STATUS.md` |
| `DESIGN.md` §7 | the review gate | deleted; Review reports |
| `REQUIREMENTS.md` R4.2, R4.3 | only the developer sets `accepted`; next phase blocked | deleted; R4.1 survives |
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
| `0_PROJECT_CONTEXT_INSTRUCTIONS.md` | schema edits per §9; constraint-retrofit paragraph keys on `done`; add `mergePolicy`; documents list |
| `3_PLAN_INSTRUCTIONS.md` | delete §Two-Tier Acceptance; move Coverage Matrix out to `FEATURE_STATUS.md`; §2 Completed keys on `done`; fix "non-`accepted`" in §Refreshing; checklist items |
| `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` | remove entry gate and Blocker scan; merge at hand-off + permission; rewrite §Starting From the Right Base — branch from current, PR targets it, content check **reported not gated**, `prTarget` demoted from a rule to a note; §Recording Developer Decisions → ledger marking; Step 2.3 → `HOW_TO_RUN.md` + rows; two counts in the report; Definition of Done |
| `5_REVIEW_INSTRUCTIONS.md` | target any built work; verdict → report with coverage and untested sections; stop writing `reviewStatus` |
| `AGENTS_TEMPLATE.md` | rule 4; rewrite §Recording What the Developer Tells You (table, guards, merging) |
| `docs/DESIGN.md` | supersede DD-4/6/9, delete §7, add UL decisions, update the three diagrams and §9 |
| `docs/REQUIREMENTS.md` | R4, R5.1, R8.3–8.4, R10.2–10.4 |
| `README.md`, `DEVELOPER_GUIDE.md`, `USE_CASES.md`, `examples/INTAKE_EXAMPLE.md` | 25 `HOW_TO_TEST` references; acceptance narrative throughout |

## 12. Trade-offs accepted

- **No hard gates remain.** Nothing prevents a bad build from growing except the developer
  reading the reports. Defensible for a modernization build with one user and nothing deployed;
  it would not be for a team shipping to production.
- **The base branch contains untested code.** The "just don't merge it" escape disappears: by
  the time a bad phase is discovered, later phases sit on top of it and the only way out is
  forward. Largely mitigated by pointing the work at an integration branch (`prTarget: dev`), so
  untested code never reaches `main` until the developer sends it there.
- **Two counts are the whole warning system.** They must appear in every hand-off report, or
  "no gates" becomes "no idea".
- **Prompt-only enforcement**, as before. Nothing validates `state.json` or the ledger.
