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
only the slice you ask for. Commands: `start` (**start every Stage 4 run here** — one command,
no chain), `summary` (**start every other run here**), `get <path>`, `new` (entries above the
`progress` marks), `add`, `set`, `drop`, `check`. **Run it with no command for
the full syntax** when a command is refused as malformed. Two things it will not refuse, so get
them right first time: **field names must be exact** — a misspelled one is stored as a new field,
not refused — and a value holding quotes or a nested object goes in an `@FILE`: a UTF-8 JSON
file in **`.harness-tmp/`** at the working-tree root (the tools create it), or outside the repo
— never piped in. **A values file in `.harness-tmp/` is used once:** the tool deletes it after
reading it, refused or not, so write a new one for each command (the same name is free again);
one the command never read stays — if your create tool refuses it, use a new name.

- **Two kinds of refusal.** A malformed command — unknown path, wrong value type, bad syntax — is
  yours: correct it and rerun. A rule refusal — a backward status, a write to
  `changeLog`/`reviews`, a changed id, dropping a non-`pending` phase — is an invariant speaking:
  never work around it, by hand edit or otherwise. Take the path the invariant gives: forward work
  for a status (Invariant 4), an appended entry to correct history (Invariant 3).
- **Stage 0 is the one exception:** it writes the initial file (and a rerun's `context` changes)
  directly, then runs `check`.
- **If Python is unavailable, in any stage,** edit `state.json` — and `features.json`,
  `FEATURE_STATUS.md` and the plan — by hand under the same rules, keep the JSON valid and the
  view's rows equal to `features.json`'s, and say so in the report. The next ledger write by the
  tool then needs `--force`, once you have checked `features.json` holds every change.

---

## The Feature Ledger

**The feature ledger is `features.json`** (beside `state.json`); **`FEATURE_STATUS.md` is a view
generated from it. Never edit either by hand — use the documents tool,** `python <stage
folder>/tools/docs.py`, run like the state tool (same `--file`, `k=v`, `@FILE`, output and
refusal rules; run it with no command for the syntax):

- **Read:** `feature show [P-N | ID …]`; `feature count [P-N]` — built-and-`untested` rows by
  phase, and `failed` ones; `feature check`.
- **Write:** `feature set <ID> k=v …`, or `feature set @FILE` with `[{"id": …, <fields>}, …]` for
  several rows in one call; `feature add` for a new row (always `untested`; in a grouped
  ledger with `group=<title>`, a new group by `feature add-group`). `phases=P-4` appends. No row is ever deleted and no id ever changes. **`tested`: you write only
  `untested`** — `passed` / `failed` need `--developer-said`, passed only on the developer's word
  (invariant 5); the tool cannot check it.

---

## Writing for the Developer

Every message you write to the developer — a stage's closing report, a question, a blocker, an
answer in ordinary chat — must be understood **without a follow-up question**. The developer may
not remember details of the legacy app or of the new design, and may not know every technical
term. Each question back costs them a whole extra request; a clear first answer costs nothing.

- **Closing reports, stops and blockers open with the plain answer**, in two to four short
  sentences: what you did, where things stand, and whether you need them. Then **"What I need
  from you"**: each decision or question, numbered — or "Nothing — you can run <the next
  step>." Then the detail the stage file asks for, in its order. A short chat answer just
  answers plainly, with no headings.
- **Simple English.** Short sentences, plain words, one idea per sentence.
- **Define every term the first time you use it in each message** — technical (CORS,
  idempotent, migration), harness (re-slice, retrofit phase, reconcile, high-water mark) and
  project terms alike.
- **Never name anything by its ID alone.** Say what it is, ID in brackets: "the rule that the
  existing database must not be changed (C3)", "the employee search screen (FR-12)", "the login
  and roles phase (P-4)", "intake question 9 — does the old app keep writing to the database".
  The same goes for a file, table or endpoint that is the subject of a decision, blocker or
  finding: say what it is and where it lives. **Lists the developer copies stay exact** —
  changed files, commands, the commit message, `path:line` citations.
- **Remind, don't assume memory.** For anything from the legacy app, the design or an earlier
  phase, add one sentence: what it is and why it matters now. Write it from what you already
  read this run — never open a file only to explain it in a message.
- **Translate the document markers.** Restate each `OPEN QUESTION:` as a numbered question under
  "What I need from you", and each `ASSUMPTION:` as "I assumed X because Y — tell me if that's
  wrong." Don't paste the document's wording. If there are many, list the ones that block the
  next stage, and say where the rest are recorded.
- **For each decision:** what the choice is, why it matters, the options and what each leads to,
  your recommendation, and what you will assume — or what stays stopped — until they answer.
- **For each blocker:** what is stopped, why, and the one thing that would unblock it.
- **Prefer a concrete example** to an abstract description.
- **Simple wording, not fewer facts.** Keep every item the stage requires in its report, state
  severities and bad news plainly, and let the message be as long as clarity needs. Group a long
  list by topic, one plain line per item.

This governs messages, and the summary and advice sections of a review report. It does not
change the documents a stage writes — requirements, design, plan, `PROJECT_CONTEXT.md`,
`state.json` — whose precise wording later stages depend on. *Want terser reports? Edit this
section in your `AGENTS.md`.*

---

## Keeping the Request Count Down

The agent platform may bill **per model call**, not per token: every tool call you make is
followed by another billed call. Reading more in one call costs nothing extra. So, in every
stage and in ordinary chat:

- **Batch independent reads.** Read several known files in **one step**: with your file tool,
  several reads issued together where it allows (on Windows, prefer this — a shell command that
  labels each file needs `$`, which the outer shell may rewrite); in bash, `tail -n +1 FILE1
  FILE2`.
- **Find legacy code through the code map.** Before searching or listing the legacy source, look
  in `LEGACY_CODE_MAP_<AppName>.md` in the documents location: §1 says where each area lives, §3
  lists every file with the names declared in it and their line numbers. Open only the files it
  points to; search the tree only for what it lacks. It is a pointer — cite the code, never the
  map. Stage 1 writes it (`tools/codemap.py`); other stages and chat only read it. The
  developer may refresh it by rerunning the script; a request to exclude a folder from it is
  that, or a Stage 1 rerun. No map yet? Search as before — it is optional, so never stop to
  ask for it.
- **Don't re-read what cannot have changed.** Within one run, a file only you have touched need
  not be read again. **Every stage run reads its inputs fresh** — between runs the developer,
  a formatter or a build may have changed any of them, and you cannot see that from memory.
- **Chain dependent commands** — build, tests and linter (within the time limit below); a run
  of state-tool writes — into one shell command that stops at the first failure: bash
  `a && b && c`; on Windows **`pwsh -NoProfile -Command "a && b && c"`** (below). When a
  chain stops, say which step failed and which did not run. **Never chain a write that needs an
  id printed by an earlier `add`** — run that `add` on its own first. If your shell tool refuses chained commands, run them one at a time.
- **Keep every command inside the platform's command time limit** (often 120 s, sometimes
  30 s): chain only steps that finish well within it. **A command that may outlast it** — a full
  build, a test suite with coverage — runs through the long-command tool: `python <stage
  folder>/tools/longrun.py start <name> [--dir <folder>] -- <program> <args>` — one program,
  no shell, `pwsh` wrapper or chain; a run-once flag where it watches (`ng test --watch=false`);
  double quotes round an argument with a `.` after a `-` (`"-Dmaven.test.skip=true"`), which
  Windows PowerShell 5.1 splits in two (single quotes inside a `pwsh -Command` wrapper). It runs in the background and `start` waits up to
  100 s; while it answers `still running` (exit 3), run `longrun.py wait <name>` — never a
  shorter `--seconds`; on a 30 s limit add `--seconds 25` to both. Two long checks may run side
  by side: `start a --seconds 0 …`, `start b …`, then `wait` each. Exit 0 passed; exit 1
  failed (it says where the log is); `lost` (exit 4): do what it prints. `longrun.py stop
  <name>` ends one. After a timeout, check by content what it
  changed before re-running anything.
- **Write in as few edits as possible.** Write a new file whole; group changes to one file into
  one edit where the tool allows; and where your tools allow several calls in one step, write
  several files in that one step — **at most about three files or 400 lines per step**, so one
  reply never reaches the model's output limit (a cut-off reply loses its writes). A large file
  goes alone.
- **Open a file with your edit tool's own reader before editing it,** where that tool requires
  it (GitLab Duo's does) — a shell read does not count. A file you wrote this run needs none.
- **Don't spend a call checking your own write.** A failed write or edit reports itself; re-read
  only when a later step needs the content.

**On Windows, run shell commands through PowerShell 7** — `pwsh -NoProfile -Command "…"`. A
command tool may hand a command to `cmd` or to Windows PowerShell 5.1 (on GitLab Duo, often the
first command of a session goes to `cmd`); either one starts `pwsh`, which then runs the rest the
same way, with `&&`, and reads and writes UTF-8. Each trap below costs a failed call:

- **Inside the quotes:** single quotes only, and no `$` or `%` — the outer shell rewrites them
  (`"... 'status=in progress' ..."`). A command that needs `$` goes in a script file in
  `.harness-tmp/`, run with `pwsh -NoProfile -File`; end it with
  `Remove-Item -LiteralPath $PSCommandPath` so it does not linger. A program alone with plain
  arguments (`python ... start`) needs no wrapper. **Every temporary file — values file, script
  — goes in `.harness-tmp/`, never in a project folder.**
- **No `pwsh`** (`pwsh -v` fails): run one plain program per command — no `;`, `&&` or `|` —
  and say so in the report.
- **Answered `is not recognized as an internal or external command`, or by a tool's usage text
  for a `;` chain:** it ran in `cmd`. Rerun it through `pwsh`; don't switch to `cmd` syntax.
- Write files with your file or edit tool, never `>` or `Out-File` from Windows PowerShell 5.1
  (UTF-16). `Select-String` has no `-Recurse`: pipe `Get-ChildItem -Recurse` into it. No
  `python -c` with quotes inside — write a script file.

These never override a rule elsewhere: a stage's checks, stops and reports all still happen —
they are just done in fewer calls.

---

## Before you write anything

Classify what you are about to do **at the moment you are about to write**, not when you read
the prompt — investigation often turns into editing partway through, and the gate belongs in
front of the edit.

- **Reading, explaining, diagnosing, running tests** → just do it.
- **About to change target application code** → this is a phase or a minor edit. Stop and ask:
  > "This changes built code. Run it through `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` — tests,
  > docs, state, commit hand-off — or make the change directly?"

  If they choose "directly", **still append a `changeLog[]` entry** (author `developer`, origin
  `out-of-band`) naming what changed. Skipping the process is their call; skipping the record is
  not — the next Implement run reconciles against this log, and an unrecorded change makes its
  baseline silently wrong.
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
3. **That phase is built like any other**, and the feature-ledger rows it changes reset to
   `untested`.

A `done` phase is never reopened to absorb the change — the retrofit is new work that supersedes
it — and a phase ID is **never reused or renumbered**.

---

## Invariants — never violate these, in any stage or ad-hoc request

1. **The legacy source is read-only.** Never modify, move, or delete it — even when it shares a
   repository with the target code. Build the new tree beside it.
2. **`INTAKE.md` and the `*_TEMPLATE.md` files are inputs — never write to them.** Resolved
   answers belong in `INTAKE_RESOLVED.md`, which Stage 0 writes.
3. **`state.json`'s `changeLog[]` and `reviews[]` are append-only.** Correct the record by
   appending, never by rewriting or deleting.
4. **Phase and edit status moves forward only: `pending` → `in progress` → `done`.** You set all
   three on a phase as work proceeds; a minor edit is registered once its checks pass, already
   `done`. `done` is terminal — **what is built is built.** A reported failure is
   recorded in the feature ledger and fixed as forward work, never by reopening what shipped it.
5. **Only the developer authorizes `passed` or `failed` in the feature ledger** — they mean a
   human ran the app. Write one only on their explicit word (the tool's `--developer-said`);
   never infer one, pass that flag otherwise, or write one to clear an inconvenient `untested`.
   The only value you may write yourself is `untested`, when your work changed that feature's
   behavior. **That mark gates nothing:** no stage waits on it, so never
   ask for it — least of all as a precondition for something else, which turns an attestation
   into a reflexive yes.
6. **Never run a git command** — not to branch, commit, push, open or merge a PR, and not the
   read-only ones either. Version control is the developer's, done whenever they choose or never,
   and nothing depends on it: each phase builds on the files as they stand in the working tree.
   Asked to run one, give them the command to run themselves; never ask them to run one. This
   overrides any skill or older project document that says to commit or run git.
7. **No secrets anywhere** — not in code, documents, `state.json`, commit messages, or PR bodies.
   Connection strings, IdP config, and credentials come from environment or profiles.
8. **Never mutate a reused database's schema.** Where a data-reuse constraint is in force, fix
   the mapping, never the database.

---

## Recording What the Developer Tells You

**This section is normative and lives only here** — these statements arrive in ordinary chat,
where no stage file is loaded; stage files point back here.

The developer edits neither `state.json` nor the feature ledger. They say what happened in
plain language; you write it (`§The Feature Ledger`) and confirm what you wrote:

| They say | You write |
|---|---|
| "accept P-2" / "P-2 passed testing" | `feature set P-2 tested=passed --developer-said` — every row reading `built in P-2` → `passed <today>`, except a `failed` one; ask about the rows the tool names (left `failed`, or changed by P-2 but built elsewhere) and change only those they name. **Nothing in `state.json` changes** — P-2 stays `done` |
| "search works" / "the export screen is fine" | the matching row(s) only: `feature set <ID> tested=passed --developer-said` |
| "P-2 failed — search returns 500" | the affected row(s): `feature set <ID> "tested=failed - search returns 500" --developer-said` (the tool adds the date and the dash), **plus** a `changeLog[]` entry (`author: developer`, `origin: developer-prompt`). P-2 stays `done`; the fix is forward work |
| "I hand-fixed X myself" | a `changeLog[]` entry, `author: developer`, `origin: out-of-band` |
| "P-3 is on branch `phase/P-3`" / "P-3's PR is <url>" | that phase's (or edit's) `branch` / `prUrls` — the only way either is ever filled |
| "commit P-3" / "merge P-3" / "open a PR" | **run nothing** (invariant 6) — give them the git commands, with the suggested commit message from that run's hand-off |
| "I committed P-3" / "I merged P-3 myself" | nothing to write |

Phases and edits behave **identically** here: both are units of shipped work with a status and a
commit hand-off, and both are tested through the feature rows they touched, never as units.

**Recording testing:**

1. **Several at once is fine, when they name them.** "accept P-2, P-3 and P-4" is legitimate —
   they may have deferred testing deliberately. Tick each phase's rows in turn. The vague bulk
   ("accept everything so far") is turned into the explicit list and read back for confirmation.
2. **Say what they are attesting to**, per phase: *"Recording that you tested P-2's two features
   and P-3's four against their checks in `FEATURE_STATUS.md`."* They should register the claim,
   not just see boxes tick.

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
