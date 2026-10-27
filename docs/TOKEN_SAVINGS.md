# Token Savings — Options

*Status: a proposal. Nothing in §3 is applied except Option 17 (the legacy code map, DD-27),
Option 19 (`state.py start`, one command that begins a Stage 4 run — DD-18) and Option 20 (the
ledger and plan tool, values files in the repo, and fixes for the failed calls of a real Stage 4
run — DD-29, DD-30); Option 18 is recorded for after a measured Sonnet run.
Each option says whether it needs a design change (and so a yes) or is only a way of running the
harness. Last updated 2026-10-27.*

---

## 0. Read first — GitLab Duo bills per call, not per token (2026-10-23)

This proposal was written to cut **tokens**. GitLab Credits are charged per **model call**: one
chat message is "one or more billable requests, because one or more LLM calls are made", the
price per call depends on the model, and there is no token formula
([GitLab Credits docs](https://docs.gitlab.com/subscriptions/gitlab_credits)). Every tool call
the agent makes is followed by another billed call; reading more in one call is free up to the
context limit. So the goal is **fewer calls**, and some options below now cost more:

| Option | Under per-call billing |
|---|---|
| 1 Smaller model where routine | **Still helps — likely the largest saving** (price per call varies by model: Sonnet $0.50 against Opus $0.74 per request here) |
| 2 Fresh session per run | **Backfires** — a new session re-reads everything; stay in one chat where context allows |
| 3 Keep Stage 4 phases small | **Backfires** — more runs, each with fixed read/reconcile/hand-off calls |
| 4, 5, 10, 11 Split Stage 1 / Stage 2 work into more runs | **Backfire** — more runs |
| 6 Review each phase soon | **Backfires** — review the risky phases, and `whole-build` at milestones |
| 7 Split Stage 4 into prepare and build | **Backfires** — two runs instead of one |
| 8 Read only plan-named sections | **Backfires** — more, smaller reads |
| 13 Mechanical checks as scripts | Still helps — one call replaces several |
| 17 Legacy code map | **Helps — applied** (DD-27): a script builds it for no model calls, and later lookups skip the search calls |
| 19 Start-of-run command | **Helps — applied** (DD-18): one command, no chain, so a `cmd` command tool no longer turns the start into one read per call |
| 20 Ledger and plan tool; fewer failed calls | **Helps — applied** (DD-29, DD-30): one command per ledger or plan update, and limits that stop calls failing |
| 9, 12, 14, 15, 16 | Neutral, or help only if they remove calls |

What was applied for per-call billing (DD-25, Q6, on branch `no-agent-git`): `AGENTS.md
§Keeping the Request Count Down` (batched reads, chained commands, fewer edits, no re-read to
verify); Stage 4 batch points (inputs in one command, build/test/lint and exit criteria
chained, hand-off state writes chained); a re-slice may be approved in advance in the prompt;
and `DEVELOPER_GUIDE.md §Keeping the Request Bill Down` for how the developer runs it. Removing
all agent git (DD-24) also removed roughly 8–15 calls per phase.

Added 2026-10-25, with Stage 4 reworded for a mid-size model (Option 1's Sonnet): state and
documents read in two commands at the start of a run; the predecessor-code check in one
command; Step 0's change-log writes (and, when the plan is unchanged, the `in progress` write)
in one chain; a task's files written in one step;
the test-guide walk and the remaining `HOW_TO_RUN.md` commands chained; the documents read at
the start not reopened. Rough estimate, not measured: 6–15 fewer calls in a 27–72-call phase.
The same change put Stage 4's steps in run order, turned its three decisions into tables, and
counts a check only if it actually ran (R4.1).

Added 2026-10-27 (Option 19): Stage 4's state read is one command, `state.py start`, instead of
a chain of five. A real Duo run showed its command tool runs `cmd`, which does not split on `;`:
the chain reached `state.py` as `summary;`, which printed its usage text, and the agent fell back
to one read per call.

---

## 1. Where the tokens go

**How a session is charged.** An agent re-sends everything loaded so far on every step (each
file read, test run, edit). So a session costs roughly **what is loaded × how many steps it
takes**. Prompt caching charges re-sent, unchanged text at a much lower rate, so real savings are
smaller than raw token counts suggest. How GitLab Duo passes caching through to credits is not
known.

**What each stage loads.** Size check A3, run on the 10-file sample with
`--docs ../samples/employee-search/reference-output`. tiktoken counts run ~15–20% low for Claude;
`+` means some inputs were unmeasured; real apps have much larger generated documents.

| Stage | Instructions | Generated documents | Runs |
|---|---:|---:|---|
| 0 Project context | 25,477 | — | once |
| 1 Requirements | 6,272 | + the legacy source | once or twice |
| 2 Design | 8,380 | 12,697+ | once, plus reruns |
| 3 Plan | 10,822 | 12,697+ | once, plus refreshes |
| **4 Implement** | **14,095** | **12,697+** | **once per phase** |
| 5 Review | 7,710 | 12,697+ | once per phase or batch |
| `AGENTS.md` (every session) | 2,899 | — | loaded once per session, cached |

**Two conclusions.** Stage 4 is where most of the spend is: it loads the most, takes the most
steps, and runs most often. And the **generated documents** (requirements, designs, plan) cost
more than the instructions, so the options that shrink what Stage 4 carries matter most.

---

## 2. Already applied (2026-10-09, merged in PR #9)

- The resolved intake list moved out of `PROJECT_CONTEXT.md §5` into `INTAKE_RESOLVED.md`
  (DD-19, R2.7).
- Constraint obligations are stored once, in `PROJECT_CONTEXT.md §4`; `context.constraints` was
  removed from `state.json` (DD-20, R1.3).
- The state tool's full help is printed only when a command is refused as malformed
  (`AGENTS_TEMPLATE.md §Reading and Writing state.json`).
- Stage 4's Git Discipline and Definition of Done were tidied.

---

## 3. Options

### Ways of running the harness — no instruction change

#### Option 1 — Use a smaller model where the work is routine

- **What:** the harness names no model, so choose one per stage in the agent tool.

  | Stage | Model | Why |
  |---|---|---|
  | 0 Project context | Sonnet | Mostly organizes the developer's answers; read its output carefully |
  | 1 Requirements | **Opus** | A missed rule is missed everywhere after; runs once or twice |
  | 2 Design | **Opus** | The hardest reasoning; a weak design is expensive later |
  | 3 Plan | **Opus** when Stage 4 runs on Sonnet; else Sonnet | Runs rarely, and every Sonnet build run follows what it writes — an exact plan saves fix-up calls in every phase |
  | 4 Implement — phase | **Sonnet by default** | Runs every phase and builds to an exact spec |
  | 4 Implement — minor edit | Sonnet or Haiku 4.5 | Small, low-risk changes |
  | 5 Review | **Opus** | Finding subtle bugs and security gaps |

  Switch Stage 4 back to Opus for login and permissions, data migration, retrofit phases, and
  any phase where Sonnet stops twice as blocked or keeps failing its exit criteria.
- **Reasoning effort:** Anthropic's notes for Sonnet 5.5 say that at low effort it sometimes
  reports a change done without a check that exercised it, or stops to check in before
  finishing. Stage 4 counts a check only if it ran (R4.1), but every early stop costs a call.
  Find out what effort the platform runs Sonnet at, and whether it can be chosen.
- **Judge cost per finished phase, not per call:** a cheaper call that needs more fix-up loops
  or stops is not cheaper.
- **In GitLab Duo:** a top-level group Owner sets a default model per feature (**Settings →
  GitLab Duo → Model selection → Manage models**). Users can choose only where the Owner left
  "GitLab default". IDE model selection sometimes does not apply. GitLab does not publish credit
  cost per model; the developer's own figures (2026-10-26) are **$0.50 per request for Sonnet
  and $0.74 for Opus** — about a third less per call. So Sonnet is cheaper only while a run
  takes fewer than about 1.5 times the calls Opus would (0.74 / 0.50 = 1.48): a phase that
  costs Opus 40 calls must finish within 59 on Sonnet. Measure this before relying on it.
- **Saves:** the most of any option for the least effort, mostly through Stage 4.
- **Risk:** lower quality on hard phases; the escalation rule is the safeguard.
- **Change:** none. Writing this table into `DEVELOPER_GUIDE.md` is new guidance — ask first.

#### Option 2 — One fresh session per stage run and per phase

- **What:** start a new session for every stage run and every phase; never keep working in a
  chat after its stage has handed off.
- **Do not restart inside a Stage 4 run** (between Step 0 and hand-off): Step 0b appends a
  reconcile entry to `changeLog[]`, but the high-water marks advance only at hand-off, so a
  fresh session would reconcile the same changes twice. Answer a Step 0c re-slice proposal in
  the same session.
- **Saves:** stops sessions growing across unrelated work.
- **Risk:** none.
- **Change:** none.

#### Option 3 — Keep Stage 4 phases small

- **What:** ask Stage 3 for smaller phases ("make P-5 smaller"). Mid-phase, Stage 4 already
  stops at a runnable point and proposes a split when a phase proves too large
  (`4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md §When You're Blocked`); the rest becomes a new phase
  in a fresh session.
- **Saves:** session cost grows faster than session length, so two half-size phases usually cost
  less than one full-size phase.
- **Risk:** too-small phases pay the fixed reload (~27k+ tokens on the sample) too often. Use
  each phase's `sizeReport` in `state.json` to find the right size.
- **Change:** none.

#### Option 4 — Stage 1: one pass, then a fresh rerun per module

- **What:** after the first Stage 1 run, rerun it per module with Additional Instructions —
  "survey the leave-approval module in depth". The rerun loads the existing documents and edits
  them in place (`1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md §Rerunning this Stage`).
- **Saves:** each session holds one module's code, not the whole app. Large apps also gain
  coverage.
- **Risk:** never phrase a module as "out of scope" to defer it — that is recorded as a scope
  decision. Each rerun adds a revision-history row; harmless before any phase is built.
- **Change:** none.

#### Option 5 — Stage 2: HLD first, then the LLD in parts

- **What:** run Stage 2 for the HLD only, review it, then write the LLD over fresh reruns, each
  told which sections to write:
  1. shared rules — §6 errors, §7 config keys, §5 auth seam, §2 data model, §3a source tree,
     §3b design language;
  2. one module at a time — its §1 API contracts, §3 components, §4 validation, §3c rows;
  3. last — §8 traceability, then a full-LLD consistency pass on Opus.
- **Saves:** modest; each session still reloads the requirements and HLD. The main gain is
  catching architecture mistakes before contracts are written.
- **Risk:** parts drift apart (an API that does not match the data mapping). The consistency
  pass is the safeguard; a module session must not change a shared rule — that goes back to
  step 1. The stage's Definition of Done expects a complete LLD, so tell each run it writes one
  part.
- **Change:** none. Option 11 makes it built in.

#### Option 6 — Review each phase soon after it is built

- **What:** run Stage 5 per phase rather than over large batches.
- **Saves:** smaller reviews, and problems caught while they are cheap to fix.
- **Risk:** none. (Splitting one review by topic would reload the documents per topic — costs
  more; not recommended.)
- **Change:** none.

### Changes to the instructions or tools — design changes, ask first

#### Option 7 — Split each Stage 4 run into "prepare" and "build"

- **What:** a short **prepare** session does Step 0 (classify, reconcile, refresh the plan) with
  everything loaded, then writes a **phase brief** quoting the exact requirements, design rules
  and constraints the phase needs, with ids and locations. A fresh **build** session loads only
  the brief, the phase's plan entry, the build and hand-off parts of the Stage 4 instructions,
  and the code. Build can run on Sonnet, prepare on Opus.
- **Saves:** the most of the design-change options — the long code-and-test loop stops carrying
  the full documents on every step.
- **Risk:** the brief misses a rule. Mitigated because the brief is written right before the
  build by an agent that has just read everything, and Stage 5 still reviews against the full
  documents.
- **Touches:** Stage 4 (inputs, steps, hand-off, and where the reconcile marks advance), a new
  phase-brief artifact (DESIGN.md components and a DD, REQUIREMENTS.md), `AGENTS_TEMPLATE.md`
  routing, the guides, eval check A3.

#### Option 8 — Stage 4 reads only the sections the plan names

- **What:** each phase's plan entry names the design and requirements sections it needs; Stage 4
  reads only those.
- **Saves:** similar to Option 7.
- **Risk:** high — the sections are chosen weeks ahead, at planning, so a phase can miss a rule
  in a section nobody named. **Option 7 achieves the same saving more safely; prefer it.**
- **Touches:** Stage 3 (phase template), Stage 4 inputs, DESIGN.md, REQUIREMENTS.md.

#### Option 9 — A slim instruction file for minor edits

- **What:** a short file for minor edits only. It keeps the authority test ("does this touch a
  requirement, design contract or plan scope? If yes, stop and run full Stage 4") and the
  bookkeeping (`edits[]`, `FEATURE_STATUS.md`, commit hand-off).
- **Saves:** most of each minor edit's cost, which today loads the full Stage 4 file and every
  document. Worth it only if minor edits are frequent.
- **Risk:** something non-minor is treated as minor; the stop rule is the safeguard.
- **Touches:** Stage 4 Step 0a (today the agent classifies the work; a separate file means the
  developer picks it), a new file, DESIGN.md, REQUIREMENTS.md, the guides, installers.

#### Option 10 — Stage 1 by module, built in

- **What:** make Option 4 a first-class mode: one session per module, then a short **merge**
  session that joins results, removes duplicates and fixes ids.
- **Saves:** less than Option 7 (Stage 1 runs once); large apps gain coverage.
- **Risk:** rules shared across modules (a common helper, a shared table) are missed or
  duplicated; the merge must check for them.
- **Touches:** Stage 1 ("same single survey", Step 1, Definition of Done), DESIGN.md,
  REQUIREMENTS.md.

#### Option 11 — Stage 2 writes the LLD in parts, built in

- **What:** make Option 5 a first-class mode, with its order and its rule that module sessions
  do not change shared rules.
- **Saves:** modest; more on large designs.
- **Risk:** as Option 5; the final consistency pass is mandatory.
- **Touches:** Stage 2 (Steps 2–3, a partial-run rule, Definition of Done), Stage 3 (must wait
  until the LLD is marked complete — a `state.json` field or an LLD §0 status line), DESIGN.md,
  REQUIREMENTS.md, the guides; a new `state.json` field also touches `state.py` and its tests.

#### Option 12 — Exact input paths from the state tool

- **What:** each stage file has a ~18-line "Locating your inputs" section: read
  `context.locations`, then find each document by its conventional name. Replace it with:
  1. **every document's exact path in `state.json`** (e.g. `context.locations.files.lld`),
     written by the stage that creates it; and
  2. **a state-tool command, `state.py inputs <stage>`**, that prints exactly the paths that
     stage needs and refuses clearly if one is missing or ambiguous.

  Each stage's section shrinks to one line.
- **Saves:** ~300 tokens per run, plus the agent's search steps (listing folders, matching
  names), each of which re-sends the session.
- **Risk:** low; code does the lookup, so it is the same every time.
- **Touches:** the `state.json` schema (Stage 0 §Output 2, DESIGN.md §5), every stage that
  writes a document, `state.py` and its tests, DD-18, the five stage files.
- **Smaller alternative:** move the locating procedure once into `AGENTS_TEMPLATE.md` (always
  loaded) and leave a one-line pointer in each stage. Saves the same ~300 tokens and stops five
  copies drifting, with no schema or tool change.
- **Since Option 19 (applied):** Stage 4 already gets its paths from `state.py start`, found by
  conventional name with no schema change; this option would add exact stored paths and the
  other stages.

#### Option 13 — Move other mechanical checks into scripts

- **What:** the state tool shows the pattern. Candidates: checking the working tree contains the
  predecessor phase's work; checking `FEATURE_STATUS.md` and `state.json` agree at hand-off;
  later, extracting the phase brief for Option 7.
- **Saves:** a script costs almost no tokens and never skips a step; fewer agent steps and
  retries.
- **Risk:** low; each script needs tests and must run on Windows and Unix.
- **Touches:** new tools (DESIGN.md, REQUIREMENTS.md), the stage steps they replace, installers,
  the guides.

#### Option 14 — Split stage files into a core file plus on-demand parts

- **What:** the Agent Skills pattern (supported by GitLab Duo, Claude Code, Codex, Gemini CLI):
  keep the core steps in the main file and move rarely needed parts into separate files the agent
  opens only when the case arises. In Stage 4: minor edits, re-running a failed phase, the
  mid-phase split procedure, reference implementations, split-layout hand-off rules.
- **Saves:** moderate, on every run that does not hit those cases.
- **Risk:** the agent does not open a part it needed and misses a rule. Measure first.
- **Touches:** every stage file it applies to, the "ships as Markdown files" description in
  REQUIREMENTS.md §1, the installers, and the Tier 1 eval checks that read stage files.

#### Option 15 — Thin skill wrappers per stage *(convenience, not savings)*

- **What:** one short `SKILL.md` per stage that says only "follow `<stage file>`". The stage
  files stay the single source of truth; the routing table in `AGENTS_TEMPLATE.md §Running a
  stage` could shrink to one line.
- **Saves:** ~200–300 tokens per session at most — skill descriptions are always loaded too.
- **Risk:** low. Do **not** move the invariants, state-tool rules, authority ladder or "record
  what the developer tells you" into skills: they are needed in ad-hoc chat, where no stage is
  loaded.
- **Touches:** new files, installers, the guides.

#### Option 16 — Expose the state tool through MCP *(reliability, not savings)*

- **What:** a thin MCP layer over `state.py`, with typed inputs per command. The command line
  stays for Stage 0, tools without MCP, and as a fallback.
- **Saves:** about break-even — tool definitions (~1–2k tokens) load every session, offset by a
  shorter state section in `AGENTS.md` and fewer malformed-command retries.
- **Gains:** no quoting, `@FILE`, PowerShell-pipe or `\u`-escape pitfalls; a typed schema could
  also refuse misspelled field names (a pending decision for `state.py` itself).
- **Risk:** an MCP server to run on every machine; the "no runtime, no installer" description in
  REQUIREMENTS.md changes.
- **Touches:** DD-18, `state.py` and its tests, `AGENTS_TEMPLATE.md`, installers, the guides.
  Worth it only if bad state-tool commands cause real trouble.

#### Option 17 — A legacy code map *(applied 2026-10-24, DD-27, R13)*

- **What:** Stage 1 saves its survey as `LEGACY_CODE_MAP_<AppName>.md`. A stdlib script,
  `tools/codemap.py`, generates the index — every folder, then every file with the names it
  declares and their line numbers — and Stage 1 adds one section saying where each area lives.
  Every later stage and ordinary chat looks legacy code up there before searching.
- **Saves:** calls, not tokens. Before, Stage 1's survey lived only in its session, so each
  later lookup and each Stage 1 rerun searched again (one billed call per search or listing).
  The agent never changes the legacy source, so the map goes stale only when the developer
  supplies a newer copy — rerunning the script refreshes it. Building it costs no model call.
- **Risk:** low. The index is found by pattern and can miss a name — the agent then searches as
  before, and nothing is ever cited from the map. A very large legacy app gives a long §3;
  agents search it rather than read it whole.
- **Touches (done):** DD-27, R13, `tools/codemap.py` and `eval/tests/test_codemap_tool.py`,
  Stages 1–5, `AGENTS_TEMPLATE.md §Keeping the Request Count Down`, the guides.

#### Option 18 — Sonnet-ready phases: Stage 3 writes more exact phase entries *(not applied — waits for a measured Sonnet run)*

- **What:** Stage 4 now runs on Sonnet by default (Option 1), and Sonnet does best when it
  does not have to infer. So Stage 3's phase template gains five fields:
  1. **Delivers** — the files and code names the phase creates (from LLD §3a). The next phase's
     predecessor check (Stage 4 §Starting From the Right Code) becomes one command with no
     guessing.
  2. **Exit criteria as one ready-to-run command per repo**, plus any non-command criteria
     listed apart. Stage 4 copies the command instead of composing it.
  3. **Exact pointers in each task** — the LLD sections (e.g. LLD §1 for an endpoint, §2 for a
     mapping) and requirement ids it implements.
  4. **Developer test-guide API steps as copy-paste commands** with expected results, so
     Stage 4 runs them in one chained command (Step 2, item 2) and the developer can paste
     them too.
  5. **A "needs the stronger model" mark** on risky phases — login and permissions, data
     mapping, retrofits, literal reference copying — so the developer sees Option 1's
     escalation rule at the moment they start the run.
- **Not Option 8:** Stage 4 still reads every document in full (free under per-call billing).
  The fields are signposts, not cuts.
- **Saves:** fewer build-and-fix loops (the largest share of a phase's 27–72 calls) and fewer
  composed-command mistakes. Not measured.
- **Mid-project:** a plan written before this option lacks the fields. To get them, run one
  Stage 3 refresh on Opus (`run stage 3 — add the Option 18 fields to the remaining phases`),
  about 6–10 calls. Worth it only when many phases remain. Stage 4 must also keep working on a
  plan without them.
- **Risk:** low for quality; the cost is a longer Stage 3 run and more for Stage 3 to get right.
  Run Stage 3 on Opus (Option 1).
- **Touches:** a design change — `3_PLAN_INSTRUCTIONS.md` phase and task templates and its
  Definition of Done; Stage 4 Step 0 (§Starting From the Right Code), Step 1 and Step 2 (use the
  fields when present); a DD in `docs/DESIGN.md`; R5 in `docs/REQUIREMENTS.md`; the guides'
  plan descriptions; possibly a Tier 1 eval check for the template's shape.

#### Option 19 — A start-of-run command in the state tool *(applied 2026-10-27, DD-18)*

- **What:** two additions to `tools/state.py`, both new output only:
  1. **One command that starts a Stage 4 run** — it prints `summary`, `new`, `context`,
     `phases` and `edits` and the exact paths of the input documents from
     `context.locations.documents`, so Stage 4's first two commands
     (`4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md §Locating your inputs`) need no path-finding or
     long PowerShell chain. A variant also prints the documents themselves, making the start
     one call.
  2. **`new` also prints the marks to write at hand-off** — the highest `changeLog` id and
     `R-<n>` it printed — so moving the high-water marks (Step 2, item 5) is copying, not
     judging.
- **Saves:** about one call per run (≈ $0.50 on Sonnet), and one judgment a mid-size model can
  get wrong (advancing the marks past an entry it never folded in).
- **Mid-project:** a drop-in. It adds commands and changes no existing output, refusal or
  `state.json` field, so a project picks it up by getting the new tool file.
- **Risk:** the platform may cut off very long tool output — test the print-the-documents
  variant on a real project first; the paths-only variant has no such risk. Close to Option 12;
  build them together if both are wanted.
- **Why it was applied without waiting:** a real Duo run showed the chained start does not
  work when the command tool runs `cmd` (no `;` splitting): `state.py` received `summary;` and
  printed its usage text, and the agent fell back to one read per call.
- **Applied as:** part 1 as `python state.py start` — `summary`, `new`, `context`, `phases`,
  `edits`, `stages.plan`, then each input document's path from `context.locations.documents`
  (required or optional; found, missing or ambiguous) and the code locations. The print-the-documents variant
  was not built; the documents are read in one step after it. Part 2 is folded into `start`, not
  `new` (whose output is unchanged): a marks line gives the values to write at hand-off if
  everything `new` printed is folded in — information only, with the reminder to raise the
  change-log mark to each entry the run adds, but never past one it did not reconcile.
  R7 lists no commands, so `docs/REQUIREMENTS.md` did not change.
- **Touches (done):** `state.py` and `eval/tests/test_state_tool.py`; DD-18, DD-25 and Q6 in
  `docs/DESIGN.md`; Stage 4 §Locating your inputs, Step 0b item 1, Step 0c and Step 2 item 5;
  `AGENTS_TEMPLATE.md §Reading and Writing state.json`; `DEVELOPER_GUIDE.md`.

#### Option 20 — A tool for the ledger and the plan, and fewer failed calls *(applied 2026-10-27, DD-29, DD-30, R5.5–R5.6, R7.5)*

- **Why:** a real Stage 4 run on Opus counted 31 failed or timed-out tool calls over four runs —
  each a billed call that did nothing. The causes: one step writing 11 files hit the model's
  output limit; build, tests and lint chained into one command hit a 120 s (and a 30 s) limit;
  the command tool sometimes ran `cmd`, not PowerShell; Duo's edit tool refuses a file its own
  reader never opened; Windows PowerShell 5.1 traps (`-Recurse` on `Select-String`, quoting,
  `python -c`, and the harness's own batch-read command reading without `-Encoding UTF8`);
  values files had to sit outside the repo, where Duo's file tool cannot write; and a leftover
  app instance on the test port. Updating the plan, `HOW_TO_RUN.md` and the Markdown ledger
  took ad-hoc scripts and 9–10 calls of reads, retries and checks.
- **What:** (1) `tools/docs.py`: the ledger becomes `features.json`, edited by `feature set` /
  `add` (several rows in one call) with the ledger's rules as refusals, `FEATURE_STATUS.md` a
  generated view, `feature count` for the hand-off's count and `feature check` against
  `state.json`; the plan stays Markdown with `plan complete` (§5 → §2) and `plan replace` (exact
  pairs, all or nothing). (2) Values files in `.harness-tmp/`, which the tools create and which
  ignores itself in git. (3) `AGENTS.md §Keeping the Request Count Down` gains a size cap per
  write step, the command time limit, read-before-edit, and a short PowerShell 5.1 list; Stage 4
  gains the port check before the test-guide walk and "never tick the plan's checkboxes".
- **Saves:** calls that fail, and the 9–10 calls of hand-made ledger and plan scripts per run.
  Not measured. `HOW_TO_RUN.md` is helped only by the read-before-edit rule; a general exact-replace
  command for any document is a possible follow-up.
- **Mid-project:** one `feature import` of the existing `FEATURE_STATUS.md` and a rebuilt
  `AGENTS.md` (`DEVELOPER_GUIDE.md §Upgrading the Harness Mid-Project`).
- **Relation to other options:** this is Option 13 applied to the ledger — `feature check`
  checks the ledger against `state.json` — and the first piece of Option 16's "no quoting or
  PowerShell-pipe pitfalls" without MCP. It does not do Option 19 (a start-of-run command in the
  state tool, applied separately the same day) or Option 18 (more exact phase entries), which
  still waits for a measured Sonnet run.
  Option 18's "Delivers" field would pair with `plan show`.
- **Touches (done):** DD-29, DD-30, R4.4, R5.5–R5.6, R7.5, R10.3, Q6; `tools/docs.py` and
  `eval/tests/test_docs_tool.py`; `tools/state.py` (the folder) and its tests; `tools/codemap.py`
  skips the folder; `AGENTS_TEMPLATE.md`; Stages 0, 3, 4, 5; the guides.

### Rejected

| Idea | Why not |
|---|---|
| Tell each stage to read only certain sections of a file | Saves almost nothing; the file-reading tool loads the whole file anyway |
| Give each stage only its own obligation | Lowers quality: Review falls back to the *Implement* obligation, the plan builds *Implement* obligations into exit checks, and obligations refer to each other |
| Keep constraints only in `state.json`, or move all context into `state.json` | Breaks DD-1, DD-2, R1.2, R7.1 and the authority ladder; prose in JSON also costs more tokens (non-ASCII printed as `\u` escapes) |
| Heavy trim of `AGENTS_TEMPLATE.md`, or moving its rules into skills | Saves at most ~800 tokens on a cached file, and its rules are needed in ad-hoc chat |
| Rewrite instructions as JSON or YAML | Models follow prose better; JSON costs more tokens |
| Split a review by topic | Each part reloads the documents — costs more |
| Split Stage 0 or Stage 3 | They run rarely and need the whole picture |

---

## 4. How to measure

- **Tokens:** from `eval/`, run `uv run run.py --set ../ModernizationHarness --checks A`; add
  `--docs <dir>` for the generated documents. Do not compare against `eval/results/` — it is a
  historical record of older instruction sets.
- **Cost:** compare Duo credits for similar runs before and after (per day or per session on
  the usage page).
- **Quality:** run the same case before and after, at least three times each, and compare the
  outputs. The Tier 2 dataset (`eval/DATASET_PLAN.md`) is built for this.

---

## 5. Recommended order

1. **Now, free:** Options 1, 2, 3 and 6.
2. **For large legacy apps or designs:** Options 4 and 5.
3. **Build the Tier 2 dataset** (`eval/DATASET_PLAN.md`, Steps 1–2) so the next steps can be
   measured.
4. **First design change:** Option 7, tried on one test app and compared before/after. Prefer
   it to Option 8.
5. **Cheap, low-risk tidy-ups:** Option 12 (or its smaller alternative) and Option 13.
6. **Only if needed:** Option 9 (minor edits are frequent), Options 10–11 (Options 4–5 by hand
   prove too manual), Option 14 (after a measured run), Option 15 (for easier starting), Option
   16 (state-tool commands cause real trouble).
7. **After one measured Sonnet phase** (calls, stops and first-time exit-criteria passes against
   an Opus phase): Option 18 if Sonnet loops on fix-ups or guesses file locations, and enough phases
   remain to repay a Stage 3 refresh. Count failed and timed-out calls too — Option 20 (applied)
   is meant to bring them near zero.
