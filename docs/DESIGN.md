# Design — Modernization Harness

*How the harness is built, as currently implemented. Pairs with [REQUIREMENTS.md](REQUIREMENTS.md).*

---

## 1. Design in one paragraph

At run time, the harness is **eleven Markdown files, four small tools, and a set of vendored agent
skills** (the install scripts and `examples/` only set it up). Six
files are stage instructions, invoked one unit of work per run; two are templates the developer
copies into their project; three are the guides. One tool, `tools/state.py`, reads and writes
`state.json` (DD-18); `tools/codemap.py` writes the legacy code map (DD-27); `tools/docs.py`
keeps the feature ledger — `features.json`, shown as the generated `FEATURE_STATUS.md` — and makes
the plan's bookkeeping edits (DD-29); and `tools/longrun.py` runs a command that may outlast the
platform's command time limit in the background and waits for it in steps (DD-31). The skills in `skills/` are upstream Angular and .NET helpers the
installer copies into `.agents/skills/`; `AGENTS.md` invariant 6 overrides any git step in
them. All coordination
between sessions happens through **two kinds of artifact on disk** — human-readable Markdown
documents and two machine-readable JSON files, `state.json` and `features.json`. Nothing is held in an agent's memory between runs,
because there is no "between runs": each run reads state and all its inputs fresh — even in a
chat it shares with the previous run (DD-25) — does one unit of work, writes state, and stops.

## 2. Components

| File | Kind | Responsibility |
|---|---|---|
| `AGENTS_TEMPLATE.md` | template → `AGENTS.md` | Invariants, authority ladder, the protocol for recording what the developer tells you, and how every message to the developer is written. Loads in **every** session |
| `0_INTAKE_TEMPLATE.md` | template → `INTAKE.md` | The 25 numbered questions, split into single-answer parts (`12a`, `12b`, …; tick boxes where the answer is a choice), their defaults, and which parts are load-bearing — 6 topics, plus Q8 when the schema is new. API description and hand-testing tools, connection identities (database included), role mapping, test sign-in, config/secrets delivery, and supplied API descriptions/collections each have their own part (R2.6) |
| `0_PROJECT_CONTEXT_INSTRUCTIONS.md` | stage | Resolve intake → `PROJECT_CONTEXT.md` + `INTAKE_RESOLVED.md` (its own record, DD-19) + initialize `state.json` |
| `1_REQUIREMENTS_EXTRACTION_INSTRUCTIONS.md` | stage | Legacy code → business / functional / technical requirements + the legacy code map (DD-27) |
| `2_DESIGN_INSTRUCTIONS.md` | stage | Requirements → HLD + LLD |
| `3_PLAN_INSTRUCTIONS.md` | stage | Design → phased plan + `phases[]` + the feature ledger (`features.json`) |
| `4_PHASE_IMPLEMENTATION_INSTRUCTIONS.md` | stage | Build one phase or one minor edit; hand off; stop |
| `5_REVIEW_INSTRUCTIONS.md` | stage | Independent audit; findings back into `state.json` |
| `tools/state.py` | tool | Reads and writes `state.json` for every stage after 0 (DD-18) |
| `tools/codemap.py` | tool | Writes `LEGACY_CODE_MAP_<AppName>.md` from the legacy source, keeping Stage 1's notes on a rerun (DD-27) |
| `tools/<name>.txt` | copy | A plain-text mirror of each tool, kept identical to it by `eval/tests/test_tool_mirrors.py`; nothing runs or reads it |
| `tools/docs.py` | tool | Writes `features.json` and renders `FEATURE_STATUS.md` from it; moves a done phase to plan §2 and applies exact plan replacements (DD-29) |
| `tools/longrun.py` | tool | Runs a long build or test suite in the background, its output in `.harness-tmp/`, and waits for it in calls that each end inside the command time limit (DD-31) |
| `skills/` | vendored skills | Upstream Angular and .NET agent skills, installed into `.agents/skills/`; `AGENTS.md` invariant 6 overrides any git step in them |
| `DEVELOPER_GUIDE.md` / `README.md` / `USE_CASES.md` | guide | The reasoning / the five-minute start / the situations you'll hit, by example |

## 3. Pipeline

```mermaid
flowchart TD
    L[Legacy app<br/>read-only] --> S0
    I[INTAKE.md<br/>25 questions, one answer per part] --> S0[0 · Project Context]
    S0 --> PC[PROJECT_CONTEXT.md<br/>constraints C1..Cn]
    S0 --> ST[(state.json)]
    S0 --> IR[INTAKE_RESOLVED.md<br/>read by Stage 0 only]
    PC --> S1[1 · Requirements]
    L --> S1
    S1 --> REQ[BUSINESS / FUNCTIONAL /<br/>TECHNICAL requirements]
    S1 --> CM[LEGACY_CODE_MAP.md<br/>where legacy code lives]
    CM -.->|find legacy code<br/>without searching| S2
    REQ --> S2[2 · Design]
    S2 --> D[HLD + LLD]
    D --> S3[3 · Plan]
    S3 --> PL[PLAN.md — remaining work]
    S3 --> FS[features.json → FEATURE_STATUS.md<br/>one row per requirement, never deleted]
    PL --> S4[4 · Implement one phase]
    S4 --> HO[Changed files + suggested commit<br/>+ HOW_TO_RUN.md]
    S4 -->|rows built / reset to untested| FS
    HO --> DEV{Developer — commits, merges<br/>and tests whenever they choose}
    DEV -- next phase --> S4
    DEV -- accept P-N / P-N failed --> FS
    S4 -.->|Step 0c re-slices| S3
    HO --> S5[5 · Review · separate session]
    S5 -->|findings, never a gate| ST
    ST -.->|reconciled at Step 0b| S4
```

**Nothing on this diagram blocks.** The developer's testing and the Review stage both feed the
loop without holding it: the only gate is a phase's own falsifiable exit criteria.

Stages 0–2 run once each (and on rerun). Stages 3–4–5 are the loop.

## 4. Key design decisions

| # | Decision | Why |
|---|---|---|
| **DD-1** | **Constraints carry per-stage obligations**, defined once in `PROJECT_CONTEXT §4` | Stage files hold zero project-specific rules, so a new constraint needs no edit to any stage file. This is what makes the harness stack-agnostic (R1) |
| **DD-2** | **Split state from content**: `state.json` for machine state, Markdown for prose | Markdown status tables were unmergeable and drifted. JSON gives lineage, mechanical reconciliation, and diffable history (R7) |
| **DD-3** | **High-water mark** rather than "diff everything" | A run must distinguish new change-log entries from ones it already applied, without re-reading history each time (R7.3) |
| **DD-4** | **One gate: falsifiable exit criteria.** Status moves `pending → in progress → done`, forward only | The acceptance gate cost the developer an hour of testing before any further building, so it forced a choice between working and claiming something untrue. Removing it leaves the self-check — which is meaningful only because it can fail, so a check that never ran (a command that failed to start, a syntax-only check) is never counted as a pass (R4) |
| **DD-5** | **Permanent phase IDs; order lives in the plan** | PRs, branches, and reviews keep meaning what they said, even after re-slicing (R5.4) |
| **DD-6** | **Retrofit phases, never reopened `done` ones** | What is built is built: a delivered phase's ID, scope and place in history stay as written, and the change is new work that supersedes its behavior (R6.3) |
| **DD-7** | **Contract changes are a two-prompt flow** (rerun Stage 2, then next phase) | The pause is the point — it's where the developer catches a design being amended into something they didn't intend |
| **DD-8** | **`AGENTS.md` always loaded** | Stage rules only bind when a stage is invoked; most drift happens in ordinary chat |
| **DD-9** | **`HOW_TO_RUN.md` (how to run it) + `FEATURE_STATUS.md` (what is built and tested)** | Per-phase test docs went stale, and one regenerated file duplicated the plan's own test guides. Splitting *how to run* from *what to check* leaves each written once: the run doc changes only when running changes, and each feature's check sits beside the column the developer ticks (R10). Since DD-29 the ledger's record is `features.json` and `FEATURE_STATUS.md` is its generated view |
| **DD-13** | **Testing is tracked per feature, not per phase** | A phase is a batch of work; a later phase can change what an earlier one delivered, and a phase-level mark cannot express that. A feature row can — it gains the new phase and resets to `untested` (R4.3, UL-5) |
| **DD-24** | **No agent runs git; version control is the developer's.** The agent edits the working tree and hands off a list of changed files and a suggested commit message; the developer branches, commits, pushes, opens PRs and merges | In the developer's environments the agent's git tool hangs, and their projects forbid agent git. Nothing in the pipeline ever needed git *actions*: each phase builds on the files as they stand, so the previous phase's work is present whether or not it was committed. Change detection between runs already had a git-free path — `changeLog[]` and Revision History rows. Replaces DD-14 and DD-17; folds in DD-16. Numbered 24, not 21, so it does not collide with DD-21..23 on the unmerged `stage4-redesign` branch (R11) |
| **DD-25** | **Shape each run to make as few model calls as possible, not to read as few tokens as possible** | The developer's platform (GitLab Duo) bills per model call: each tool call is followed by a new, billed call, and the size of what is read does not change the price. So one command that prints ten input files beats ten reads, and a chained command beats separate ones. The rules live once, in `AGENTS.md §Keeping the Request Count Down`, with Stage 4 naming its own batch points (state and inputs at the start — state through the state tool's one `start` command, which needs no chaining in any shell (DD-18) — the predecessor check, Step 0's change-log writes, a task's files, verification and exit criteria, the test-guide walk and run-doc commands, hand-off state writes). Chaining is "where the shell tool allows it", because not every agent's command tool accepts it. Batching stops where a failed call would cost more than it saves: a step writes at most about three files or 400 lines, so one reply cannot hit the model's output limit; a chain stays inside the platform's command time limit, with a command that may outlast it run through `tools/longrun.py` (DD-31), and after a timeout the agent checks by content before re-running; a file whose edit tool needs its own read first is opened with that tool's reader; and on Windows every shell command runs through PowerShell 7 (`pwsh -NoProfile -Command "…"`, single quotes and no `$` or `%` inside), because a command tool may hand a command to `cmd` or to Windows PowerShell 5.1 — on GitLab Duo the first command of a session often goes to `cmd` — and either one starts `pwsh` the same way; without `pwsh`, one plain program per command — each seen in a real Stage 4 run that counted 31 failed or timed-out calls over four runs. A prompt may also approve a plan re-slice in advance, which saves a stop-and-ask round trip (R5.3, Q6) |
| **DD-26** | **Every message to the developer is written to be understood without a follow-up: plain English, summary and "what I need from you" first, every term and ID explained** | The developer often could not follow a stage's closing report — terms undefined, things named only by ID, legacy details assumed remembered — and had to ask again, which on a per-call platform costs a full extra request (DD-25). The rule lives once, in `AGENTS.md §Writing for the Developer`, because messages are written in every session, not only in stage runs; each stage's Definition of Done points to it. Documents keep their precise style — later stages are judged against them — except the summary and advice sections of a review report, which the developer reads as a message. Reminders are written from what was already read, never by opening a file, so the rule adds no tool calls (R12, Q7) |
| **DD-27** | **A legacy code map, built once: `tools/codemap.py` generates a file-and-name index of the legacy source, and Stage 1 adds one section saying where each area lives. Every later stage, and ordinary chat, finds legacy code through it before searching** | On a per-call platform (DD-25) every search and directory listing is a billed call, and Stage 1's survey was held only in that session's memory — so each later stage that needed a legacy detail, and each Stage 1 rerun, hunted for it again. The agent never changes the legacy source (Invariant 1), so the map goes stale only when the developer supplies a new drop, and then rerunning the script refreshes it; a script builds the index for no model calls at all. The index is found by pattern, not by a compiler, so it is a pointer, never evidence: requirements still cite the code. The generated part is marked and rewritten on every run; everything above the marker — Stage 1's notes — is kept, and so is a hand-written map with no marker. The map records the folders excluded from it (the target code, where it sits inside the legacy source), and a refresh reuses them, so once the target code's folder is excluded a new legacy drop cannot pull it into the index; a target folder that does not exist yet at Stage 1 is excluded on a later refresh. The tool never overwrites a file it did not write; where the documents location sits inside the legacy source it leaves that folder out of the map, and it refuses a map placed directly in the legacy root. Without Python, or after a refusal that cannot be fixed, Stage 1 writes its section by hand and the generated part is left out until the tool next runs; a non-map file at the map's path is never overwritten. A rerun that changes only the map writes nothing to `state.json` (R13, Q6) |
| **DD-28** | **A minor edit is registered in `edits[]` once, when its checks pass, already `done` — never `pending` or `in progress`** | Nothing plans an edit ahead the way Stage 3 plans phases, so it has no `pending` state to start from. Registered any earlier, an edit that turns out to touch a contract leaves an entry nothing can close when the run stops (§When a Change Touches a Contract): status moves forward only (DD-4), edits are never dropped, and `done` would claim work that never shipped. A resumed edit run could also register the same edit twice. The cost: an edit run that stops before its checks pass leaves no `edits[]` entry to resume — its stop report says what is half made, and the change-log entries Step 0 writes before any stop record the request. Its other lifecycle fields (`branch`, `prUrls`) behave as a phase's (R6.4) |
| **DD-29** | **The feature ledger is `features.json`, written only through `tools/docs.py`; `FEATURE_STATUS.md` becomes a view the tool generates on every write. The plan stays Markdown, and its two mechanical edits — moving a `done` phase from §5 to a §2 Completed line, and exact text replacements — are tool commands too** | In a real Stage 4 run the agent updated the plan, the run doc and the Markdown ledger with ad-hoc scripts of its own (an exact-replace helper, a row-reset helper) and spent 9–10 calls reading, retrying and checking them — every call billed (DD-25). A Markdown table is also hard to edit exactly: one wrong cell, a lost row or a stray `passed` goes unnoticed. The tool makes each update one call and turns the ledger's rules into refusals: no delete command, permanent unique ids, only the defined `build` / `tested` values, no row `scheduled in` a `done` phase or `built in` a `pending` one, and `phases` that only grow. `tested` takes `passed` / `failed` only with a `--developer-said` flag — a speed bump the tool cannot verify, so invariant 5 stays a rule the agent follows, not one the tool proves. The view carries a hash of its own body, so a hand edit is detected and never overwritten without `--force`; the hash ignores line endings, so a CRLF checkout is not an edit. `feature count` prints the hand-off's features-awaiting-testing count, and `feature check` cross-checks the ledger against `state.json`. The ledger may be grouped under headings: each group keeps its title and the text around its table, and rows name their group. A project with a Markdown ledger migrates once with `feature import`, which takes every ledger table in the file, makes each heading with a table under it a group and keeps every other line as text — refusing, by line, anything it cannot place, including a `|` line outside a code block that no ledger table took (a blank line inside a table, a header that is not the six columns) — prints the rows per group so the developer can compare them with the original, refuses and names any row it cannot parse (two older forms convert with a note: a phase range `P-1..P-15` becomes its list, and a build naming several phases becomes `scheduled in` the last or `built in` the first, as the developer chooses with `--split-scheduled` / `--split-built`, the original kept as a How to check line), and keeps the original as `FEATURE_STATUS.md.bak`. `plan complete` refuses a phase that is not `done`; a phase runs to the next phase heading or the end of §5, and headings in code blocks never count. Inside a phase, a heading at or above the phase's level that is not one of the template's own is refused — except in the last phase, where such a heading (or one a level down after its Exit criteria) ends the phase and stays in the plan. An unclosed code fence, or a removal that would strand a template heading, is refused too — never guessed; it prints the headings it removed; `plan replace` applies all its pairs or none, each old text found exactly once. Writes are UTF-8, keep the file's line endings, and go through a temp file. Same input and output conventions as `state.py`; without Python, the agent edits both files by hand under the same rules and says so (R4.4, R5.5, R5.6, R10.3, Q6) |
| **DD-30** | **Values files for the tools' `@FILE` go in `.harness-tmp/` at the working-tree root, a folder the tools create and git does not ignore; a values file there is deleted once a tool has read it, whatever the outcome; a path outside the repo still works** | The rule was "outside the repo", so nothing temporary could be committed by accident. But GitLab Duo's file tool cannot write outside the repo, so agents wrapped whole JSON payloads in PowerShell here-strings — fragile quoting, more failed calls. The folder first ignored itself (a `.gitignore` of `*`), but Duo's file tools also refuse a git-ignored path, and its create tool will not overwrite a file, so values files piled up and one was written into a project folder instead. So the folder is no longer ignored, and `state.py` and `docs.py` delete a values file in a folder named `.harness-tmp` once they have read it — on success, a refusal or a malformed file alike — with one line on stderr saying so: every write there is a new file, and nothing lingers to be committed. A file the command never read (it stopped first) is kept, so the corrected command can reuse it; a file elsewhere is never deleted; one that cannot be deleted (on Windows, open in another program) is named, not fatal. A leftover — a run stopped before using it, or a failed long command's log (DD-31) — shows in `git status` as untracked, the visible signal; the developer may delete it. Both tools create the folder on every run, so it exists before the agent needs it, and remove the `.gitignore` older versions wrote there — only when it holds exactly `*`; one the developer changed is kept, and the folder then stays ignored. The code map skips the folder (R7.5) |
| **DD-31** | **A command that may outlast the platform's command time limit — a full build, a test suite with coverage — runs through `tools/longrun.py`: `start` runs it in the background, its output in `.harness-tmp/<name>.out.txt`, and waits up to 100 s; `wait` waits again, each call inside the limit, until it ends** | In a real Duo session `ng test` and `mvn verify` (formatter, static analysis, 138 tests, coverage) were cut off by a 120 s — sometimes 30 s — command time limit, and the agent improvised a background job writing a log, then polled it, in shell syntax of its own; every improvised step is a billed call (DD-25). The tool gives it one shape in every shell. The program runs directly, no shell — on Windows a program is the file with a `PATHEXT` extension (`mvn` → `mvn.cmd`, `./mvnw` → `mvnw.cmd`), never the extension-less shell script beside it, which is refused when it is all there is; a `.cmd` runs through `cmd.exe`, with any argument cmd would misread refused. A small runner is started through a go-between that exits at once, so it is in neither the call's process tree — which a platform may kill when the call hits its limit — nor its output handles, and the call returns at once; it is detached (Windows: no console, and it asks to leave the command tool's job; Unix: a new session). The runner records the program's process id and, when it ends, the exit code in `<name>.status`, and touches that file every 2 s, so a runner that died — killed, or the machine slept — is told apart from one still running (no touch for 30 s: *lost*). A lost run's program may still be running: `stop` ends it, and `start` of that name is refused until then, but only while its id cannot have been reused — the runner's last touch under 10 minutes ago, and on Windows a process created after the run started; with its program gone, `stop` just clears its files. The log is `.out.txt`, not `.log`, because many projects' `.gitignore` holds `*.log`, which Duo's file tools would refuse (DD-30). Each report gives the state, the exit code, the time so far and the last 30 log lines (colours and progress redraws stripped), and an exit status per outcome: 0 passed (log and status deleted), 1 failed (log kept and named, for the agent's file tool — possible because the folder is not ignored, DD-30 — or reprinted by `wait <name> --lines 200`; the next `start` of that name replaces it), 3 still running, 4 lost, 2 malformed or refused (the name already running, the program not found or not a Windows program). A run that passed but was never waited for is cleared by the next `list`. Several names may run side by side. `start` waits as `wait` does, so a command that finishes inside the limit still costs one call. The default 100 s fits a 120 s limit; a 30 s limit needs `--seconds 25`. `stop` ends the program and everything it started (Windows `taskkill /T`, Unix the process group), prints the log's last lines and deletes its files — also how a server started for the test-guide walk is ended, leaving nothing behind. *Lost* names the causes in order: a `start` or `wait` call itself cut off by the limit (start again with a smaller `--seconds`); otherwise the platform ends background programs, and the agent runs the command directly — a check that cannot finish inside the limit even so is reported as not run, and the developer asked to run it (R4.1). Stdlib Python, one file, ASCII output (R4.5, Q6) |
| **DD-14** | *Replaced by DD-24.* Was: branch from the currently checked-out branch, PR back at it, and never merge unasked | Kept so references to it still resolve |
| **DD-17** | *Replaced by DD-24.* Was: before branching, detect a branch that is already merged or gone from the remote | With no agent branching there is no spent branch to detect |
| **DD-15** | **The working tree is the truth; `state.json` is a cache** — presence checked by content, never by git state | The developer may commit, merge or edit outside the harness and need not report it; only the files decide whether the previous phase's work is there (R11.3) |
| **DD-16** | *Folded into DD-24.* `prTarget` is kept as a human note that no rule reads | Now widened to every git field: branch naming, PR target and reviewers are the developer's notes (R11.5) |
| **DD-10** | **Plan defaults to "no change"** | Churn burns the developer's review attention and destabilizes what they thought was coming next |
| **DD-11** | **Review is a separate session, read-only on code, and never blocks** | An agent cannot audit its own work; read-only keeps the verdict honest. The gate it used to hold only ever fired for a developer who chose to run it, and its findings already survive through the change log — so it reports and advises instead (R8) |
| **DD-12** | **Documents amended in place; git is the history** | No `_v2` filenames; Revision History rows plus commits give lineage |
| **DD-18** | **`state.json` is read and written through `tools/state.py`, not by the agent directly** | `changeLog[]` and `reviews[]` only grow, so whole-file reads cost more every run; the tool returns the slice asked for (`summary`, `get`, `new`). A Stage 4 run starts with one command, `start`, which prints `summary`, `new`, `context`, `phases`, `edits` and `stages.plan`, the high-water marks to write at hand-off if everything `new` printed is folded in (information, never a write), and each input document's path from `context.locations.documents` (read from the working-tree root; `state.json` lives in that folder) by its conventional name — required or optional, found, missing or ambiguous — plus the code locations. A documents location not found from there, or one that does not hold this `state.json`, prints one line saying so; the second is a stop-and-ask, since `docs.py` updates the ledger and plan beside `state.json`. One command, not a chain, because a platform's command tool may run `cmd`, which does not split on `;` (a real Duo run fell back to one read per call); it writes nothing and exits 0 even when a document is missing, since stopping to ask is Stage 4's call. It also turns the mechanical rules — forward-only status, append-only history, id allocation, numeric `R-<n>` comparison — from prompt text into refusals. Stdlib Python, one file; Stage 0 still writes the initial file by hand, and hand edits under the same rules remain the fallback. A value too awkward for `k=v` goes in an `@FILE` kept in `.harness-tmp/` (DD-30) (R7) |
| **DD-19** | **The resolved intake lives in its own file, `INTAKE_RESOLVED.md`, which only Stage 0 reads** — `PROJECT_CONTEXT §5` is a one-line pointer to it | The answer-by-answer ledger (one row per intake part, ~2–3k tokens) is Stage 0's record and its rerun diff baseline; no later stage uses it, yet every later stage paid for it by opening the context file. The safeguard is a Stage 0 rule: any defaulted or inferred answer that shapes a later stage is also stated in `PROJECT_CONTEXT.md` (its home section, a constraint, or §7), so nothing a later stage needs is only in the ledger. §5 keeps its number so §6–§10 do not shift (R2.3, R2.7) |
| **DD-20** | **Constraint obligations are stored only in `PROJECT_CONTEXT §4`; `state.json` holds no copy of the constraints** | A second copy in `context.constraints` was read by four stages on top of §4, and nothing checked the two stayed equal. DD-1 already makes §4 their home, and DD-2 keeps prose out of `state.json`. Keeping only ids or titles in state was rejected: no stage would read them, and they would be one more copy to drift (R1.3) |

## 5. Data model — `state.json`

```mermaid
erDiagram
    STATE ||--|| CONTEXT : has
    STATE ||--|| STAGES : has
    STATE ||--|| PROGRESS : has
    STATE ||--o{ PHASE : "phases[]"
    STATE ||--o{ EDIT : "edits[]"
    STATE ||--o{ CHANGELOG : "changeLog[] (append-only)"
    STATE ||--o{ REVIEW : "reviews[] (append-only)"
    REVIEW }o--|| PHASE : targets
    REVIEW }o--|| EDIT : targets
    CHANGELOG }o--o{ PHASE : phasesAffected

    PHASE   { string id  string status  string branch  string[] prUrls }
    EDIT    { string id  string status  string afterPhase  string[] prUrls }
    CHANGELOG { int id  string author  string origin  string summary }
    REVIEW  { string id  string target  string result  int blockerCount }
    PROGRESS { int lastProcessedChangeLogId  int lastProcessedReviewNumber }
```

`state.json` holds **machine facts only**. The constraints are not in it: they and their
per-stage obligations live only in `PROJECT_CONTEXT §4` (DD-1, DD-20). What a human has tested is not in it: that lives in
the feature ledger, `features.json` (shown as `FEATURE_STATUS.md`), keyed by requirement ID,
because a later phase can change what an earlier one delivered (DD-13). A review has no status to set on its target (DD-11), so there is no
`reviewStatus` anywhere and no `wholeBuild` record.

Rules that hold the model together:

- **Append-only:** `changeLog[]`, `reviews[]`. Correct by superseding, never rewriting.
  `edits[]` entries are never deleted or renumbered, but their lifecycle fields are updated in
  place, like `phases[]`. An edit is registered once its checks pass, already `done` (DD-28).
- **ID allocation:** `changeLog.id` = max + 1; `E-<n>` and `R-<n>` use the next unused *n* for
  their own array. IDs are never reused.
- **`progress` is numeric** — `R-10` sorts before `R-2` as a string, which would silently skip
  reviews.
- **`context.repo` / `context.deployment`** are decided *only* in Stage 0, which is also the
  only stage that writes them. Where `frontendRoot` / `backendRoot` were left null, Stage 2
  settles the tree in **LLD §3a** rather than in state; nothing downstream may invent a layout.

### `features.json` — the feature ledger (DD-29)

Beside `state.json` in the documents location. Stage 3 creates it; every write goes through
`tools/docs.py`, which renders `FEATURE_STATUS.md` from it.

```json
{ "app": "<AppName>", "schemaVersion": 1,
  "preamble": ["<text under the title>"],
  "groups": [ { "title": "Reporting", "before": ["<text above its table>"],
                "after": ["<text below it>"] } ],
  "features": [ { "id": "FR-7", "feature": "CSV export",
                  "howToCheck": ["Search screen → Export → file downloads with 3 rows"],
                  "phases": ["P-4", "E-2"],
                  "build": "unscheduled | scheduled in P-N | built in P-N",
                  "tested": "untested | passed YYYY-MM-DD | failed YYYY-MM-DD — <symptom>",
                  "group": "Reporting" } ] }
```

`preamble`, `groups` and a row's `group` are optional; an ungrouped ledger has none of them and
renders exactly as one table. The view renders the title, the preamble, the ungrouped rows, then
each group in order as a `## <title>` heading (whatever level the imported file used), its
`before` text, its table (header only when empty, so the text keeps its place) and its `after`
text — so import → render → import gives the same JSON.

- **Rows are never deleted** and an `id` never changes; `phases` only grows, in order. A row's
  `group` must name a `groups` entry; `feature add-group` creates one.
- **Cross-checks with `state.json`** (`feature check`): every `phases` id exists; no row is
  `scheduled in` a `done` or dropped phase; a row `built in` a phase needs that phase started
  (`in progress` — a run stopped after its ledger update — or `done`) and listed in its `phases`.
- **"accept P-N"** ticks only the rows `built in P-N`, and never overwrites a `failed` one; the
  tool names those, and any `untested` row that lists P-N but was built elsewhere, for the agent
  to ask about.
- **`tested`** is the developer's (invariant 5): the tool writes `passed` / `failed` only under
  `--developer-said`.

## 6. Control flow of a build run (Stage 4)

```mermaid
sequenceDiagram
    participant D as Developer
    participant A as Build agent
    participant S as state.json
    participant F as features.json (via docs.py)
    participant W as Working tree

    D->>A: "Next phase."
    A->>S: state.py start — phases[], changeLog[] > mark, reviews[] > mark, input paths
    opt a phase was left in progress
        A->>W: resume it (tasks judged by content)
    end
    A->>A: 0a classify — phase / contract change / minor edit
    A->>W: check by content for predecessor's work
    A-->>D: "Building P-3 in <target repo>. Contains P-2's work."
    A->>A: 0b reconcile changes + review findings since last run
    A->>A: 0c refresh plan (default: unchanged)
    opt re-slice needed
        alt approved in this run's prompt
            A->>A: apply; report it first
        else
            A-->>D: propose; wait for approval
        end
    end
    A->>W: edit files task by task — no git
    A->>A: run exit criteria (the only gate)
    A->>S: status=done, advance high-water mark
    A->>F: rows built in P-3; rows P-3 changed reset to untested
    A-->>D: report + 2 counts + changed files + suggested commit message
    Note over D,W: the developer commits, pushes and merges whenever they choose, or not at all
    Note over D,F: testing happens whenever — "accept P-3" ticks rows, gates nothing
```

## 7. Review, and why nothing blocks

```mermaid
flowchart LR
    R[Review run] --> V{Findings}
    V -->|none| C[CLEAN<br/>recorded in reviews - ]
    V -->|Blocker / Major / Minor| F[FINDINGS<br/>severities are advice]
    F --> CL[changeLog entries]
    CL --> I[Next Implement run<br/>reconciles and fixes]
    I --> RR[Re-review verifies<br/>those specific fixes] --> V
```

The gate this stage used to hold only ever fired for a developer who **chose** to run a review —
it punished the careful and protected nobody else. Its findings already survived without it, via
the change log and the `lastProcessedReviewNumber` high-water mark; the gate only changed *when*
they were fixed, not *whether*. So Review states plainly what it would not build on, and the
developer decides.

That leaves the pipeline with **no hard gate but a phase's own exit criteria**. The trade is
recorded in §10.

## 8. Conflict resolution

A single ladder, stated in `AGENTS.md` and repeated by reference only:

**constraint (`PROJECT_CONTEXT §4`) → plan → LLD → HLD → requirements → rest of context**

A constraint always wins; if honoring it breaks a design contract, that is a blocker for a
human, not a choice the agent makes. Material conflicts are reported, not resolved.

## 9. Traceability

| Requirement | Realized by |
|---|---|
| R1 stack-agnostic | DD-1 constraints + obligations, stored once in `PROJECT_CONTEXT §4` (DD-20); `context.currentStack` / `targetStack` |
| R2 load-bearing questions | `0_INTAKE_TEMPLATE.md` defaults / hard-stops; Stage 0 Step 1 (incl. its cross-checks); `INTAKE_RESOLVED.md` (DD-19); eval check D5 holds the template's shape |
| R3 document order | Stage files 0–5; `stages.<name>.status` |
| R4 one gate + testing record | Plan §The Only Gate; `features.json` / `FEATURE_STATUS.md` (DD-29); `AGENTS.md` §Recording What the Developer Tells You; long checks through `tools/longrun.py` (DD-31) |
| R5 rolling plan | Plan §Refreshing the Plan; Stage 4 Step 0c (incl. approval given in advance); `features.json`; `tools/docs.py` `plan complete` / `plan replace` (DD-29) |
| R6 mid-build change | Stage 4 §0a, §When a Change Touches a Contract, §Minor Edits (DD-28); retrofit phases |
| R7 machine state | `state.json` schema (Stage 0 Output 2); `progress` high-water mark; values files in `.harness-tmp/` (DD-30) |
| R8 review | Stage 5 §Outcome; `reviews[]`; findings reconciled at Stage 4 Step 0b |
| R9 governance | `AGENTS.md` invariants + authority ladder |
| R10 testability | Stage 4 Step 2.3–2.4 (`features.json` through `tools/docs.py`, `HOW_TO_RUN.md`); plan test guides |
| R11 version control | DD-24, DD-15; Stage 4 §Version Control; Step 0's §Pick the work (resume `in progress`, R11.7) and §Starting From the Right Code; `AGENTS.md` invariant 6 |
| R12 plain-language reports | DD-26; `AGENTS.md §Writing for the Developer`; a Definition of Done line in every stage file |
| R13 legacy code map | DD-27; `tools/codemap.py`; Stage 1 Step 1; the legacy-reading inputs of Stages 2–5; `AGENTS.md §Keeping the Request Count Down` |
| Q6 low request count | DD-18 (`state.py start`), DD-25, DD-27, DD-29, DD-30, DD-31; `AGENTS.md §Keeping the Request Count Down`; Stage 4's batch points (state and inputs at the start, the predecessor check, Step 0's change-log writes, a task's files, verification and exit criteria, the test-guide walk and run-doc commands, hand-off state writes) |

## 10. Known trade-offs

- **No hard gates remain.** Nothing prevents a bad build from growing except the developer
  reading the reports — the two counts at every hand-off, and Stage 5 when they run it.
  Defensible for a modernization build with one user and nothing deployed; it would not be for
  a team shipping to production, and whoever inherits this harness should know that is the
  trade that was made.
- **Nothing is committed until the developer commits it.** The agent runs no git (DD-24), so a
  run's work sits uncommitted in the working tree until the developer commits it. Untested code
  reaches a branch only when they put it there. The cost: if they never commit, several phases'
  work piles up as one large uncommitted change, with no per-phase rollback point. Each hand-off
  lists its changed files and a suggested commit message, so committing per phase costs one
  command.
- **Prompt-only enforcement.** Almost every rule depends on the agent following instructions.
  The exceptions are `state.json`'s mechanical rules, which the state tool enforces (DD-18), and
  the ledger's, which `tools/docs.py` enforces (DD-29) — but only when the agent uses them;
  nothing stops a direct edit. Even through the tool, a `passed` or `failed` mark rests on the
  agent's honesty: `--developer-said` cannot be verified. Mitigated by falsifiable exit
  criteria, `AGENTS.md` in every session, and an independent Stage 5.
- **A background build may not survive every platform.** `tools/longrun.py` detaches its
  program from the command tool (DD-31), but a platform that ends every process a command
  started, job and all, ends it too. The tool cannot prevent that; it reports it — the next
  `wait` says *lost* — and the agent falls back to running the command directly, inside the
  limit or not.
- **Non-sequential phase IDs** confuse at first read. Deliberate (DD-5); the plan's summary
  table carries the running order.
- **The code map can miss names.** `tools/codemap.py` finds declarations by pattern, so an
  unusual one may be absent from the index, and a file of an unknown kind is listed with no
  names at all. The map only says where to look; an agent that cannot find something in it
  searches as before, and nothing is ever cited from the map (DD-27).
- **Volume.** ~2,900 lines of instruction across the six stage files and two templates;
  the three guides exist to keep the entry cost low (Q1).
- **Git-dependent history.** Superseded design and plan versions exist only as commits the
  developer makes, so a project that keeps `./out/` out of git loses that lineage. The Implement
  stage does not read git: it sees a document change only through `changeLog[]` and Revision
  History rows, so a hand edit to a document with neither goes unnoticed until the developer
  reports it. The same holds for code: with no git, a hand edit to built code is noticed only
  when the developer reports it or a run happens to read that file.
