## Running a stage

The six numbered stage files live in **`ModernizationHarness/`**, relative to the root of this
working tree. *Keeping them somewhere else? Change that path here, once — it is the only place
it is written down.*

The developer need not remember filenames. Any of these names a stage — as does naming the file
outright; neither form is more official. **Load that file and follow it:**

| They say | You run |
|---|---|
| "stage 0", "project context", "intake" | `0_PROJECT_CONTEXT_INSTRUCTIONS.md` |
| "stage 1", "requirements" | `1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md` |
| "stage 2", "design" | `2_DESIGN_INSTRUCTIONS.md` |
| "stage 3", "plan", "replan" | `3_PLAN_INSTRUCTIONS.md` |
| "stage 4", "next phase", "build P-4", "implement" | `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` |
| "stage 5", "review", "audit" | `5_REVIEW_INSTRUCTIONS.md` |

- **Everything after the stage name is that stage's Additional Instructions** ("rerun stage 2 —
  use a modular monolith"). Reruns are normal; the stage file's §Rerunning says what to do.
- **Stage 4 with no target** → the next planned phase. **Stage 5 with no target** → ask whether
  they mean a phase, a minor edit, or the whole build; don't pick one.
- **Stage 0 on a first run** needs the intake path, the legacy app path, an app name, and where
  to write. Every later stage reads `context.locations` from `state.json` — **never make the
  developer retype a path it already holds.**
- **"Run the next stage" is not specific enough.** Say which one you believe is next and why,
  and let them confirm.

**Always open the file and work from it.** These instructions change; a stage run from memory
of what the stage usually does is not a stage run.

---

## Reading and Writing state.json

**Never open, paste, or hand-edit `state.json` — use the state tool,** `tools/state.py` beside
the stage files: `python <stage folder>/tools/state.py <command>` from the working-tree root
(`python3` where `python` is absent; `--file <path>` first when the prompt gives one). It returns
only the slice you ask for. Commands: `summary` (**start every run here**), `get <path>`, `new`
(entries above the `progress` marks), `add`, `set`, `drop`, `check`. **Run it with no command for
the syntax** before your first write.

- **A refusal is an invariant speaking** — a backward status, a write to `changeLog`/`reviews`, a
  non-integer mark. Never work around it; correct the record by appending.
- **Stage 0 is the one exception:** it writes the initial file (and a rerun's `context` changes)
  directly, then runs `check`. If Python is unavailable, edit by hand under the same rules, keep
  it valid JSON, and say so in the report.

---

## Before you write anything

Classify what you are about to do **at the moment you are about to write**, not when you read
the prompt — investigation often turns into editing partway through, and the gate belongs in
front of the edit.

- **Reading, explaining, diagnosing, running tests** → just do it.
- **About to change target application code** → this is a phase or a minor edit. Stop and ask:
  > "This changes built code. Run it through `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` — branch,
  > tests, docs, state, PR — or make the change directly?"

  If they choose "directly", **still append a `changeLog[]` entry** (author `developer`, origin
  `out-of-band`) naming what changed. Skipping the process is their call; skipping the record is
  not — the next Implement run reconciles against this log.
- **About to change a pipeline document** (requirements, HLD, LLD, plan) → **don't.** Name the
  stage that owns it and offer to rerun it; these documents are the contract later stages are
  judged against. This governs **ad-hoc requests outside a stage run**. A stage writes the
  documents it owns, and Stage 4 owns the **forward plan**: at Step 0c it may add, remove,
  reorder, split, and merge the **remaining** phases (with the developer's approval) and updates
  statuses, tasks, and test guides — but changes design or requirements only by a purely
  clarifying fix.

---

## How a mid-flight change is handled

A design or requirements change — even one affecting something delivered many phases ago — has
**one** path:

1. **The owning stage amends its document** (normally Stage 2 for design, Stage 1 for
   requirements) and adds a `## 0. Revision History` row naming the delivered phases it
   invalidates.
2. **The next Stage 4 run's Step 0c re-plans**, proposing a **retrofit phase** for the
   invalidated code; the developer approves it.
3. **That phase is built like any other**, and the `FEATURE_STATUS.md` rows it changes reset to
   `untested`.

A `done` phase is never reopened to absorb the change, and a phase ID is **never reused or
renumbered**.

---

## Invariants — never violate these, in any stage or ad-hoc request

1. **The legacy source is read-only.** Never modify, move, or delete it — even when it shares a
   repository with the target code. Build the new tree beside it.
2. **`INTAKE.md` and the `*_TEMPLATE.md` files are inputs — never write to them.** Resolved
   answers belong in `PROJECT_CONTEXT.md §5`.
3. **`state.json`'s `changeLog[]` and `reviews[]` are append-only.** Correct the record by
   appending, never by rewriting or deleting.
4. **Phase and edit status moves forward only: `pending` → `in progress` → `done`.** You set all
   three as work proceeds; `done` is terminal — **what is built is built.** A reported failure is
   recorded in `FEATURE_STATUS.md` and fixed as forward work, never by reopening what shipped it.
5. **Only the developer authorizes `passed` or `failed` in `FEATURE_STATUS.md`** — they mean a
   human ran the app. Write one only on their explicit word; never infer one or write one to clear
   an inconvenient `untested`. The only value you may write yourself is `untested`, when your work
   changed that feature's behavior. **That mark gates nothing:** no stage waits on it, so never
   ask for it — least of all as a precondition for something else, which turns an attestation
   into a reflexive yes.
6. **Never merge, ask to merge, or offer to — unless the developer asks, in those words.** Every
   PR is theirs, to merge whenever they choose or never. Nothing depends on a merge: a phase
   branches from the branch currently checked out, which already has its predecessor's code.
7. **No secrets anywhere** — not in code, documents, `state.json`, commit messages, or PR bodies.
   Connection strings, IdP config, and credentials come from environment or profiles.
8. **Never mutate a reused database's schema.** Where a data-reuse constraint is in force, fix
   the mapping, never the database.

---

## Recording What the Developer Tells You

**This section is normative and lives only here** — these statements arrive in ordinary chat,
where no stage file is loaded; stage files point back here.

The developer edits neither `state.json` nor `FEATURE_STATUS.md`. They say what happened in
plain language; you write it and confirm what you wrote:

| They say | You write |
|---|---|
| "accept P-2" / "P-2 passed testing" | in `FEATURE_STATUS.md`, every row reading `built in P-2` → `Tested: passed <today>`. **Nothing in `state.json` changes** — P-2 stays `done` |
| "search works" / "the export screen is fine" | the matching row(s) only → `passed <today>` |
| "P-2 failed — search returns 500" | the affected row(s) → `failed <today> — search returns 500`, **plus** a `changeLog[]` entry (`author: developer`, `origin: developer-prompt`). P-2 stays `done`; the fix is forward work |
| "I hand-fixed X myself" | a `changeLog[]` entry, `author: developer`, `origin: out-of-band` |
| "do it on this branch" / "no PR" | commit to the current branch; no new branch, no PR; `prUrls` stays `[]` |
| "merge P-3" | merge every PR in its `prUrls` and report what you merged; **write nothing** — no field records merges |
| "I merged P-3 myself" | nothing to write |

After either merge, the one thing worth saying is which branch they are now on: the merged one is
spent, so the next phase should start elsewhere (`4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md §Starting
From the Right Base`).

Phases and edits behave **identically** here: both are units of shipped work with a status, a
branch and a PR, and both are tested through the feature rows they touched, never as units.

**Recording testing:**

1. **Several at once is fine, when they name them.** "accept P-2, P-3 and P-4" is legitimate —
   they may have deferred testing deliberately. Tick each phase's rows in turn. The vague bulk
   ("accept everything so far") is turned into the explicit list and read back for confirmation.
2. **Say what they are attesting to**, per phase: *"Recording that you tested P-2's two features
   and P-3's four against their checks in `FEATURE_STATUS.md`."* They should register the claim,
   not just see boxes tick.

**Open each PR against the branch you branched from**, report the link, and stop. Where earlier phases' PRs are still open, name
them in one line so the developer sees how much has stacked up — a report, not a request. They
land such a chain **oldest first**: as each PR merges, the host re-points the one above it at the
base branch.

---

## Constraints

The project's constraints live in `PROJECT_CONTEXT.md §4`, each with a stable ID and its
**per-stage obligations**. Honor every obligation for the work you are doing, as written. Never
re-derive constraint rules from first principles: if a constraint should change how something is
done and no obligation says so, raise an `OPEN QUESTION:` rather than inventing the rule. A
constraint with no obligation for your stage does not affect it.

---

## Authority when sources conflict

1. **A constraint in `PROJECT_CONTEXT.md §4` always wins.** If honoring it would break a design
   contract, that is a blocker for a human — not a choice you may make.
2. **Otherwise**, in descending order: **plan → LLD → HLD → requirements → the rest of
   `PROJECT_CONTEXT.md`**.
3. **A material conflict is reported, not resolved.** Say what conflicts and stop.

---

## Notation

- `ASSUMPTION:` — anything inferred rather than observed or decided by a human.
- `OPEN QUESTION:` — anything unresolved. Never resolve one by guessing.
- Cite evidence as `path:line`, e.g. `src/data/UserRepository.cs:110`.
- Diagrams in Mermaid, fenced as ```mermaid, with a caption.

---

## When in doubt

**Raise it; don't resolve it silently.** If the inputs are ambiguous, contradictory, or
incomplete, say so and stop — state the blocker, what you tried, and the options, and let the
developer decide. Flag problems outside your scope rather than fixing them, and never expand
scope, redo completed work, or re-decide an upstream decision without explicit authorization.
