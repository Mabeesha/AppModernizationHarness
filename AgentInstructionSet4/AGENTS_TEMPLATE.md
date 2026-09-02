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
3. **That phase is built and accepted like any other.**

Two things never happen: an `accepted` phase is **never reopened** to absorb a change (that
attestation stays true of what was tested — the retrofit is new work with its own acceptance),
and a phase ID is **never reused or renumbered**.

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
4. **Only the developer *authorizes* `accepted` — per item, explicitly.** That mark means a
   human tested the increment, so you may write it **only** when they instruct you to accept a
   named phase or edit ("accept P-2"). Never infer it, never bundle it into another request
   (especially not "run the next phase"), and never accept several at once.
   You may set `in progress` and `done` yourself as work proceeds. Set **`pending` only when
   the developer reports a failure** — reopening an accepted item otherwise would discard a
   human's attestation that they tested it.
5. **No secrets anywhere** — not in code, documents, `state.json`, commit messages, or PR
   bodies. Connection strings, IdP config, and credentials come from environment or profiles.
6. **Never mutate a reused database's schema.** Where a data-reuse constraint is in force, fix
   the mapping, never the database.

---

## Recording What the Developer Tells You

**This section is normative and lives only here.** Acceptance often happens in ordinary chat,
where no stage file is loaded — so the protocol belongs in the file that always loads. The
stage instructions point back at this section rather than restating it.

The developer does not edit `state.json`. They state what happened in plain language; you
translate it into the state and confirm what you wrote:

| They say | You write |
|---|---|
| "accept P-2" / "P-2 passed testing" | merge its PR (see below), `status: "accepted"`, `acceptedUtc: <now>` |
| "P-2 failed — search returns 500" | `status: "pending"` + the failure note; **leave the branch and PR open** for the re-run |
| "accept E-1" | same as a phase, on the `edits[]` entry |
| "E-1 failed — <symptom>" | same as a failed phase, on the `edits[]` entry |
| "I hand-fixed X myself" | a `changeLog[]` entry, `author: developer`, `origin: out-of-band` |

Phases and edits behave **identically** here: both are units of shipped work with a status, a
branch, a PR, and a review status. Anything you can do to a phase you can do to an edit.

**Three guards on acceptance** — it is the one mark that certifies a human tested something:

1. **It must be its own instruction, naming the item.** If they ask for the next phase while the
   current one is only `done`, **do not offer to accept it as part of that request** — their
   goal in that moment is the next phase, which makes "yes" reflexive. Stop and route them back:
   > "P-2 is `done` but not accepted — I can't start P-3 until it is. If you tested it and it
   > passed, say *accept P-2* and I'll merge the PR, record it, and start P-3."
2. **Never accept several at once.** "Accept everything so far" means nothing was tested —
   challenge it and accept them one at a time.
3. **Say what they are attesting to**, e.g. "Recording that you tested P-2 against its test
   guide and it passed." They should register the claim, not just see a box ticked.

**Merging:** accepting normally includes merging that item's PR, because the next phase branches
from a base that must contain it. If the repository requires reviewers or green CI
(`PROJECT_CONTEXT §3`), **do not merge** — record the acceptance, and tell them the merge is
still theirs to do.

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
