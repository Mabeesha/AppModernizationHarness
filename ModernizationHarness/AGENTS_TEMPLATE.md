## Running a stage

The six numbered stage files live in **`ModernizationHarness/`**, relative to the root of this
working tree. *Keeping them somewhere else? Change that path here, once — it is the only place
it is written down.*

The developer should not have to remember filenames. Any of these names a stage; **load that
file and follow it**:

| They say | You run |
|---|---|
| "stage 0", "project context", "intake" | `0_PROJECT_CONTEXT_INSTRUCTIONS.md` |
| "stage 1", "requirements" | `1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md` |
| "stage 2", "design" | `2_DESIGN_INSTRUCTIONS.md` |
| "stage 3", "plan", "replan" | `3_PLAN_INSTRUCTIONS.md` |
| "stage 4", "next phase", "build P-4", "implement" | `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` |
| "stage 5", "review", "audit" | `5_REVIEW_INSTRUCTIONS.md` |

Naming the file outright — *"Follow `3_PLAN_INSTRUCTIONS.md`"* — means exactly the same thing.
Neither form is more official than the other.

**How to read what follows the name:**

- **"rerun stage 2 — use a modular monolith"** — everything after the stage name is that
  stage's **Additional Instructions**. Reruns are normal; see the stage file's own §Rerunning
  section for what it does with them.
- **Stage 4 with no target** → the next planned phase. **Stage 5 with no target** → ask whether
  they mean a phase, a minor edit, or the whole build; don't pick one.
- **Stage 0 on a first run** needs the intake path, the legacy app path, an app name, and where
  to write. Every stage after it reads `context.locations` from `state.json` instead — **never
  make the developer retype a path that `state.json` already holds.**
- **"Run the next stage" is not specific enough to act on.** Say which one you believe is next,
  and why, and let them confirm.

**Always open the file and work from it.** These instructions are detailed and change; a stage
run that proceeds from memory of what the stage usually does is not a stage run.

---

## Before you write anything

Classify what you are about to do **at the moment you are about to write** — not when you read
the prompt. Investigation frequently turns into editing partway through a conversation, and the
gate belongs in front of the edit, not in front of the question.

- **Reading, explaining, diagnosing, running tests** → just do it. No gate, no ceremony.
- **About to change target application code** → this is a phase or a minor edit. Stop and
  ask:
  > "This changes built code. Run it through `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` — branch,
  > tests, docs, state, PR — or make the change directly?"

  Then follow their answer.
- **About to change a pipeline document** (requirements, HLD, LLD, or the plan) → **don't.**
  Name the stage that owns it and offer to rerun that stage. These documents are the contract
  that later stages are judged against; editing them casually breaks that contract.

  **Carve-out:** this does not apply when you are executing a stage that owns those edits.
  Stage 4 **owns the forward plan** — at Step 0c it may add, remove, reorder, split, and merge
  the **remaining** phases (with the developer's approval), and it updates statuses, tasks, and
  test guides. It may not change the design or requirements beyond a purely clarifying fix.
  Stages 0–3 and 5 write the documents they own. The rule above governs **ad-hoc requests
  outside a stage run** — that is where casual edits do the damage.

**If they choose "directly", still append a `changeLog[]` entry** in `state.json` (author:
`developer`, origin: `out-of-band`) naming what changed. Skipping the process is their call;
skipping the record is not — the next Implement run reconciles against this log, and an
unrecorded change makes its baseline silently wrong.

---

## How a mid-flight change is handled

A design or requirements change — even one affecting something delivered many phases ago — has
**one** path, and it needs no special ceremony:

1. **The owning stage amends its document** (normally a Stage 2 rerun for design, Stage 1 for
   requirements) and adds a `## 0. Revision History` row naming the delivered phases it
   invalidates.
2. **The next Stage 4 run's Step 0c re-plans**, proposing a **retrofit phase** for the
   invalidated code and adjusting the remaining phases. The developer approves it.
3. **That phase is built like any other**, and the `FEATURE_STATUS.md` rows it changes reset to
   `untested`.

Two things never happen: a `done` phase is **never reopened** to absorb a change (**what is
built is built** — the retrofit is new work that supersedes it), and a phase ID is **never
reused or renumbered**.

---

## Invariants — never violate these, in any stage or ad-hoc request

1. **The legacy source is read-only.** Never modify, move, or delete it — in any stage, even
   when it shares a repository with the target code. Build the new tree beside it.
2. **`INTAKE.md` and the `*_TEMPLATE.md` files are inputs — never write to them.** Resolved
   answers belong in `PROJECT_CONTEXT.md §5`.
3. **`state.json`'s `changeLog[]` and `reviews[]` are append-only.** Never rewrite or delete
   history; correct the record by appending to it.
   **The developer should never have to hand-edit `state.json`** — they tell you what happened
   and you record it (see §Recording What the Developer Tells You). Keep it valid JSON and
   report what you wrote.
4. **Phase and edit status moves forward only: `pending` → `in progress` → `done`.** You set
   all three yourself as work proceeds, and `done` is terminal — **what is built is built.**
   Nothing rewinds a status: a failure the developer reports is recorded in
   `FEATURE_STATUS.md` and fixed as forward work, never by reopening the phase that shipped it.
5. **Only the developer *authorizes* a `Tested` value in `FEATURE_STATUS.md`.** `passed` and
   `failed` mean a human ran the app, so you write them **only** on their explicit word (see
   §Recording What the Developer Tells You). Never infer one, and never write one to clear a
   row that is inconveniently `untested`. The one value you may write yourself is `untested` —
   when work you just did changed that feature's behavior.
   **That mark gates nothing.** No stage waits on it, and you never ask for it before doing
   something else.
6. **You never merge.** Every PR is the developer's, to merge whenever they choose or not at
   all. Nothing in the pipeline depends on a merge having happened, because a phase branches
   from the branch that is currently checked out and therefore already has its predecessor's
   code. Never merge on your own initiative, and never merge because it would be tidy.
7. **No secrets anywhere** — not in code, documents, `state.json`, commit messages, or PR
   bodies. Connection strings, IdP config, and credentials come from environment or profiles.
8. **Never mutate a reused database's schema.** Where a data-reuse constraint is in force, fix
   the mapping, never the database.

---

## Recording What the Developer Tells You

**This section is normative and lives only here.** These statements arrive in ordinary chat,
where no stage file is loaded — so the protocol belongs in the file that always loads. The
stage instructions point back at this section rather than restating it.

The developer edits neither `state.json` nor `FEATURE_STATUS.md`. They state what happened in
plain language; you translate it and confirm what you wrote:

| They say | You write |
|---|---|
| "accept P-2" / "P-2 passed testing" | in `FEATURE_STATUS.md`, every row reading `built in P-2` → `Tested: passed <today>`. **Nothing in `state.json` changes** — P-2 stays `done` |
| "search works" / "the export screen is fine" | the matching row(s) only → `passed <today>` |
| "P-2 failed — search returns 500" | the affected row(s) → `failed <today> — search returns 500`, **plus** a `changeLog[]` entry (`author: developer`, `origin: developer-prompt`). P-2 stays `done`; the fix is forward work |
| "I hand-fixed X myself" | a `changeLog[]` entry, `author: developer`, `origin: out-of-band` |
| "do it on this branch" / "no PR" | commit to the current branch; no new branch, no PR; `prUrls` stays `[]` |

**Merging is not on that list, because it is never yours to do.** The developer merges, or
doesn't, and either way you need nothing from them: the next phase starts from whatever branch
they are standing on. If they mention having merged something, just say thanks — there is no
field to update.

Phases and edits behave **identically** here: both are units of shipped work with a status, a
branch and a PR, and both are tested through the feature rows they touched, never as units.

**Three rules for recording testing:**

1. **Several at once is fine, when they name them.** "accept P-2, P-3 and P-4" is a legitimate
   thing to say — the developer may have deferred testing deliberately, and
   `FEATURE_STATUS.md` is written so they can walk it all in one sitting. Tick the rows for each
   phase in turn. What you do **not** accept is the vague bulk: "accept everything so far" gets
   turned into the explicit list and read back for confirmation.
2. **Say what they are attesting to**, per phase, not as a lump: *"Recording that you tested
   P-2's two features and P-3's four against their checks in `FEATURE_STATUS.md`."* They should
   register the claim, not just see boxes tick.
3. **Never ask for it as a precondition.** Nothing waits on testing. Do not ask "shall I mark
   P-2 tested?" as part of a request to do something else — that turns an attestation into a
   reflexive yes, and there is no reason to ask, because nothing is blocked.

**Never ask to merge, and never offer.** You open the PR against the branch you branched from,
report the link, and stop. Where earlier phases' PRs are also still open, name them in one line
so the developer can see how much has stacked up unlanded — that is a report, not a request.

---

## Constraints

The project's constraints live in `PROJECT_CONTEXT.md §4`, each with a stable ID and its
**per-stage obligations**. Honor every constraint that states an obligation for the work you are
doing, and follow that obligation as written.

Never re-derive constraint rules from first principles: if a constraint should change how
something is done and no obligation says so, raise it as an `OPEN QUESTION:` rather than
inventing the rule. A constraint with no obligation for your stage does not affect it.

---

## Authority when sources conflict

1. **A constraint in `PROJECT_CONTEXT.md §4` always wins.** If honoring it would break a design
   contract, that is a blocker for a human to resolve — not a choice you may make.
2. **For everything else**, in descending order: **plan → LLD → HLD → requirements → the rest of
   `PROJECT_CONTEXT.md`**.
3. **A material conflict is reported, not resolved.** Say what conflicts and stop; do not pick a
   side silently.

---

## Notation

- `ASSUMPTION:` — anything inferred rather than observed or decided by a human.
- `OPEN QUESTION:` — anything unresolved. Never resolve one by guessing.
- Cite evidence as `path:line` (clickable), e.g. `src/data/UserRepository.cs:110`.
- Diagrams in Mermaid, fenced as ```mermaid, with a caption.

---

## When in doubt

**Raise it; don't resolve it silently.** Across every stage the same rule holds: if the inputs
are ambiguous, contradictory, or incomplete, say so and stop — state the blocker, what you
tried, and the options, and let the developer decide. Flag problems rather than fixing them
outside your scope, and never expand scope, redo completed work, or re-decide an upstream
decision without explicit authorization.
