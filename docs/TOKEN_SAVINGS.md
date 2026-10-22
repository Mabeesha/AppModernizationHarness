# Token Savings — Options

*Status: a proposal. Nothing in §3 is applied. Each option says whether it needs a design change
(and so a yes) or is only a way of running the harness. Last updated 2026-10-22.*

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

**Applied 2026-10-22 — the Stage 4 redesign (`docs/STAGE4_REDESIGN_PLAN.md`):**

- **Option 9 — a slim minor-edit file.** `4_MINOR_EDIT_INSTRUCTIONS.md` (DD-22, R6.4). The
  developer starts it with *"minor edit: …"*; a phase run that receives one stops and asks for it.
  A minor-edit run's fixed load is ~4,500 tokens (tiktoken), against 14,095 for any Stage 4 run
  before.
- **Git as a setting.** `context.repo.git` = `agent` | `developer` (intake Q16g; DD-21, R12).
  The git rules moved to `GIT_DISCIPLINE.md`, loaded only under `agent`; under `developer` the
  agent runs no git command that changes the repository (read-only ones are allowed). Saves
  ~2,200 tokens per Stage 4 run where the agent does not run git.
- **Re-planning moved to Stage 3.** Stage 4's Step 0c no longer re-slices; it detects a needed
  refresh and stops (DD-23, R5). A design change now costs three prompts, and the middle one
  (Stage 3) can use a cheaper model (Option 1).
- The phase file was compacted (repetition only). A phase run's fixed load, developer git mode,
  is ~10,370 tokens (from 14,095), missing the 9,500 target; with `GIT_DISCIPLINE.md`, ~12,660.

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
  | 3 Plan | Sonnet | Organizes already-decided work |
  | 4 Implement — phase | **Sonnet by default** | Runs every phase and builds to an exact spec |
  | 4 Implement — minor edit | Sonnet or Haiku 4.5 | Small, low-risk changes |
  | 5 Review | **Opus** | Finding subtle bugs and security gaps |

  Switch Stage 4 back to Opus for login and permissions, data migration, retrofit phases, and
  any phase where Sonnet stops twice as blocked or keeps failing its exit criteria.
- **In GitLab Duo:** a top-level group Owner sets a default model per feature (**Settings →
  GitLab Duo → Model selection → Manage models**). Users can choose only where the Owner left
  "GitLab default". IDE model selection sometimes does not apply. GitLab does not publish credit
  cost per model — confirm Sonnet costs fewer credits before relying on the saving.
- **Saves:** the most of any option for the least effort, mostly through Stage 4.
- **Risk:** lower quality on hard phases; the escalation rule is the safeguard.
- **Change:** none. Writing this table into `DEVELOPER_GUIDE.md` is new guidance — ask first.

#### Option 2 — One fresh session per stage run and per phase

- **What:** start a new session for every stage run and every phase; never keep working in a
  chat after its stage has handed off.
- **Do not restart inside a Stage 4 run** (between Step 0 and hand-off): Step 0b appends a
  reconcile entry to `changeLog[]`, but the high-water marks advance only at hand-off, so a
  fresh session would reconcile the same changes twice. (Step 0c no longer proposes re-slices: a
  needed refresh stops the run, and Stage 3 runs in its own session.)
- **Saves:** stops sessions growing across unrelated work.
- **Risk:** none.
- **Change:** none.

#### Option 3 — Keep Stage 4 phases small

- **What:** ask Stage 3 for smaller phases ("make P-5 smaller"). Mid-phase, Stage 4 already
  stops at a runnable point and proposes a split when a phase proves too large
  (`4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md §When You're Blocked`); the next Stage 3 refresh
  schedules the rest, and it is built in a fresh session.
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

#### Option 9 — A slim instruction file for minor edits *(applied 2026-10-22 — see §2)*

- **What:** a short file for minor edits only. It keeps the authority test ("does this touch a
  requirement, design contract or plan scope? If yes, stop and run full Stage 4") and the
  bookkeeping (`edits[]`, `FEATURE_STATUS.md`, PR).
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

#### Option 13 — Move other mechanical checks into scripts

- **What:** the state tool shows the pattern. Candidates: checking the branch contains the
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
  opens only when the case arises. In Stage 4: re-running a failed phase, the mid-phase split
  procedure, reference implementations. (Minor edits and the git rules were split out on
  2026-10-22 — see §2.)
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
6. **Only if needed:** Options 10–11 (Options 4–5 by hand
   prove too manual), Option 14 (after a measured run), Option 15 (for easier starting), Option
   16 (state-tool commands cause real trouble).
