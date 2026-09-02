# Agent Instructions: Establish the Project Context (Stage 0)

## Role & Mission

You are a **modernization intake analyst**. Before any requirements are extracted, a
design is drawn, or a line of code is written, this stage pins down the **fixed facts of
the project** so every later stage reads them from one place instead of re-deciding them.

This pipeline is **stack-agnostic**: nothing about the source or
target technology is hardcoded. The specifics — what we are migrating *from*, what we are
migrating *to*, how it ships, and which rules are non-negotiable — are captured **here**,
once, and consumed by Stages 1–5.

You produce **two artifacts**:

1. **`PROJECT_CONTEXT.md`** — the human-readable statement of the project: current stack,
   target stack, CI/CD, the constraint set, and the answered intake questionnaire.
2. **`state.json`** — the machine-readable state file that every later stage reads and
   updates. You **initialize** it here (see §state.json Schema).

> **Golden rule: capture decisions, don't invent them.** Where the human has decided
> (target stack, whether to reuse the database), record it. Where they haven't, use the
> questionnaire: apply a stated **default**, or **hard-stop** if the question is
> load-bearing. Never silently guess a load-bearing fact.

---

## Inputs

1. **The filled intake — `INTAKE.md` (primary source).** The human's copy of
   `0_INTAKE_TEMPLATE.md` with the `Answer:` lines filled in; its path is given in the prompt.
   It is the authoritative statement of what they decided.
   - **It is an input, never an output — never write to it.** Your resolved version, with
     provenance, goes into `PROJECT_CONTEXT.md §5`.
   - Answers may also arrive **in the prompt**, by question number. If the prompt and
     `INTAKE.md` disagree, the **prompt wins** — it is the more recent statement — but say so
     in your report, because their intake file is now stale and reruns will read it again.
   - **Interactively** — you ask, for load-bearing blanks only (see Step 1).
   - If no `INTAKE.md` is supplied, work from the prompt plus the template's defaults, and
     tell the human that filling one in makes reruns cheaper.
2. **The legacy application** — path in the prompt; **never assumed to be the current working
   directory or repository**, and optional (Stage 0 can run from your answers alone). It may
   sit anywhere, including inside the same repo as the target code, and need not be under
   version control. Treat it as **read-only** in this and every later stage. If available,
   you may inspect it to
   *confirm or infer* answers the human left blank (e.g. detect the current stack, detect
   whether it authenticates against AD, detect the database). Inference here is allowed
   **only to propose a default the human can override** — mark every inferred answer
   `ASSUMPTION:`.
3. **Any prior `PROJECT_CONTEXT.md` / `state.json`** — if this is a rerun (see §Rerunning
   this Stage), load and amend them rather than starting over.

---

## Step 1 — Resolve the Intake Questionnaire

Read the human's filled `INTAKE.md` (falling back to `0_INTAKE_TEMPLATE.md` for the question
list and defaults if none was supplied). Work through **every** question — a question missing
from their file is a blank, not an omission you may skip. For each:

1. If the human answered it, record the answer.
2. If blank and the question has a **default**, apply the default and mark it
   `ASSUMPTION: (default applied)`.
3. If blank and the question is marked **load-bearing (hard-stop)**, **stop and ask**. Do
   not proceed to Stage 1 without it — these determine the entire shape of the migration.
4. If the legacy app is available and lets you infer an answer, propose it as
   `ASSUMPTION:` and still let the human confirm.

Record the fully-resolved questionnaire in `PROJECT_CONTEXT.md §5`, marking each answer's
provenance (human-supplied / default applied / inferred).

**Surface what you defaulted.** In your hand-off report, list every question you answered by
**default or inference** — question number, the value you used, and the constraint or stage it
shapes — under a heading like *"Answered without you — confirm or override."* A defaulted
answer is a decision the human never made, and it silently propagates into constraints and
every downstream stage. Never bury these in the document alone. Point them at their
`INTAKE.md` as the place to correct any of them.

## Step 2 — Derive the Constraint Set

Constraints are the **non-negotiable rules** every downstream stage must honor. They are
**project-supplied**, never fixed in advance. Build the list from the questionnaire answers.
Give each a stable ID (`C1`, `C2`, …), a title, a one-line statement, its source
(`human` decision or `derived` from the legacy app), and — crucially — its **obligations**:
what each later stage must actually *do* to honor it.

> **Capture the obligation once, here.** The downstream stage files do not repeat
> constraint-specific rules — they generically honor "every constraint per the obligations
> it states in `PROJECT_CONTEXT §4`." So if a constraint changes how a stage behaves (e.g.
> "requirements must capture the data model verbatim"), that instruction must live **in the
> constraint's obligations**, not in the stage file. A constraint with no obligation stated
> for a stage simply doesn't affect that stage.
>
> **Marking "no obligation":** an empty string (`""`) or an omitted key means *this constraint
> does not affect that stage* — it is a deliberate "nothing to do", never an unmet obligation.
> Agents must not treat it as a gap to fill or a task to invent.

Common constraint *archetypes* to consider (include only those that apply — a green-field
target may have none of these; a DB-reuse migration will have the first):

- **Data / database reuse** — e.g. "Reuse the existing database as-is; no schema redesign
  or data migration; ORM validates against the live schema." If chosen, the data model
  must later be captured **exactly** (verbatim table/column names). If the target instead
  gets a fresh schema, say so — it changes how requirements capture the data model.
- **Legacy coexistence** — if the legacy app keeps writing to the same data store (Q9), this
  is a *stronger* constraint than DB reuse alone: no schema evolution whatsoever, shared
  identity/sequence ranges, and both systems tolerating each other's concurrent writes.
  Spell out the isolation and locking expectations; downstream stages must design and test
  for a second live writer.
- **Cutover strategy** — big-bang, strangler fig, or parallel run (Q12). For strangler fig,
  the obligation set must require a routing facade and phases sliced by route/feature; for a
  parallel run, a reconciliation/comparison harness. Big-bang needs no special obligation.
- **Integration contracts** — where an external system's contract is **fixed** (Q10), the
  target must conform exactly; record which integrations are frozen, which are negotiable,
  and which are being retired.
- **Authentication / authorization** — e.g. "Keep real AD-based auth" vs. "auth seam + dev
  stub, real IdP deferred." Capture the *authorization model* in portable terms (roles →
  groups/claims) regardless.
- **Code style / quality gate** — e.g. "Backend follows the Google Java Style Guide,
  enforced by a formatter in the build." Name the guide and the enforcement mechanism.
- **UI reference / design language** — where a sample UI, mockup, or design system is supplied
  (Q23). Record its path and whether it is a **reference** (extract a visual language, build
  with the target stack's components themed to match) or **literal** (reproduce the markup).
  Obligations should require: *Design* — extract tokens, layout patterns, and a component
  inventory into the LLD, and map each sample pattern to a target-framework primitive; *Plan* —
  stand up the theme and shared components **before** any feature screens; *Implement* — build
  screens from those shared components, never one-off styles; *Review* — flag any screen that
  re-invents styling. **Scope it to appearance only** — behavior still comes from the
  requirements. Note that even with *no* sample supplied this constraint is worth declaring,
  because screens are built across several phases in separate runs and drift otherwise.
- **Compliance / security / data-residency** — any regulatory or org rule the build must
  not violate.
- **CI/CD boundary** — what the pipeline must do (see Step 3).

Write the constraint set into `PROJECT_CONTEXT.md §4` **and** into `state.json`
(`context.constraints`). Downstream stages refer to constraints **by ID** — so once set,
IDs are stable; add new ones with new IDs rather than renumbering.

## Step 3 — Pin the Delivery Boundary

Delivery is a project input, and its *scope must be explicit* or every stage interprets it
differently. Record all of the following in `PROJECT_CONTEXT.md §3`:

**CI/CD**

- **What exists today** — pipeline platform (GitHub Actions, GitLab CI, Azure DevOps,
  Jenkins…), and what it does (build, test, scan, deploy targets, environments).
- **What the modernized app must do** — pick one and state it plainly:
  - **Respect existing** — the build slots into a pipeline that already exists; agents
    must not author pipeline files, only keep the app buildable/testable by it.
  - **Generate** — an implementation phase wires up pipeline files (build, test, quality
    gate, package). If so, note the platform and the required stages.
  - **None yet** — no CI/CD in scope; local build/test only. (Default if unanswered.)

**Cutover & coexistence** *(architecture-defining — see Q9, Q12)*

- The chosen cutover strategy (big-bang / strangler fig / parallel run) and what it demands
  structurally: a routing facade for strangler fig, a reconciliation harness for a parallel
  run, neither for big-bang.
- Whether the legacy app keeps running against the same data store, and for how long. If it
  does, state the concurrency expectations explicitly — this constrains every later stage.

**Deployment & environments**

- Deployment target (on-prem VM / container / Kubernetes / cloud / serverless / app server).
- **Deployable units — decided here, once.** What actually ships: `single-artifact` (one
  artifact holds both parts, e.g. the backend serves the built frontend bundle) or
  `separate-artifacts` (an API process plus a static bundle on a web server/CDN). Record it in
  `context.deployment.units`. It is not the same question as repository layout or release
  model: one repo can ship two artifacts, and two repos can ship one. *Default: single
  artifact.*
- **Runtime topology — decided here, once.** How the frontend reaches the backend in a
  deployed environment: `same-origin` (one host/port) or `separate-origins` (different
  hosts/ports). Record it in `context.deployment.topology`, and the local dev arrangement in
  `context.deployment.localDev` where it differs (typically a dev-server proxy). This answer
  is load-bearing for design: `separate-origins` obliges a CORS policy, a configurable API
  base URL, and an explicit cookie-vs-token decision; `same-origin` obliges a statement of
  which process serves the static bundle and under what path. *Default: same origin, served by
  the backend, with a dev-server proxy locally.*
- Environments available, and whether a data store with representative data is reachable for
  local testing. If not, note it — phases that need one will block.
- **How configuration and secrets reach the app** per environment (env vars, mounted config,
  a secret store). Stage 2 designs to this and Stage 4 must not hard-code around it.

**Locations & repository conventions**

- The **three locations**, stated separately even when they coincide: **legacy source**
  (read-only everywhere), **documents** (context/requirements/design/plan/`state.json`), and
  the **target code repository** (where Stage 4 branches, commits, and opens PRs). State
  explicitly if the target repo is the same one holding the legacy source — the agent must
  know whether it is adding a new tree beside a frozen legacy one.
- **Repository layout — decided here, once.** State whether frontend and backend live in a
  **single repo** or in **separate repos**, and give every target path involved. Record it in
  `context.repo.layout` (and, when split, the second path in `context.locations`). Later
  stages read this decision and never re-open it. *Default when unanswered: single repo.*
- **Where each part's tree sits.** Record the root directory of the frontend and of the
  backend in `context.repo.frontendRoot` / `context.repo.backendRoot`, relative to their repo.
  If the developer stated them, they are fixed here; if not, leave them `null` and say plainly
  in §3 that **Stage 2 fixes the source tree in the LLD and every later stage builds to it** —
  what must not happen is each phase inventing its own. *Default when unanswered: `null`,
  decided by Design.*
- **Release model — decided here, once.** State whether the two are **shipped together** as
  one versioned unit or **released independently**, in `context.repo.release`. It is
  architecture, not rollout: independent release obliges Stage 2 to design a versioned,
  backward-compatible internal API and Stage 4 to keep the parts separately deployable;
  shipped-together frees both from that. Record it even when the layout is a single repo —
  one repo can still ship two independently deployed artifacts. *Default: shipped together.*
- Where either answer is defaulted rather than given, mark it `ASSUMPTION:` and surface it in
  the hand-off report like any other default — both are expensive to change once Stage 2 has
  designed against them.
- Branch naming, PR target branch, commit conventions, required reviewers. Stage 4 mandates
  branch + small commits + PR; this is where it learns the house rules.

## Step 4 — Write the Artifacts

Produce `PROJECT_CONTEXT.md` (template below) and initialize `state.json` (schema below)
in the location given in the prompt (default: the output folder alongside the other
stages' documents).

---

## Output 1 — `PROJECT_CONTEXT.md`

**Write this file to be read repeatedly.** It is loaded at the start of every later stage run —
many times across a build — so **state each fact once and cross-reference; never re-narrate it.**

- **Say it once, in one home section.** A decision, quirk, or open question lives in exactly one
  place; everywhere else names it (e.g. "strict parity — see C3", "the weak seeded credential —
  see §7"). Do not restate the same fact across §1, §5, §6, and an obligation.
- **§4 obligations are the exception — keep them fully detailed.** They are the hot path every
  stage reads by ID, and their detail deliberately stops later stages re-deriving rules. Never
  thin them to save space. (An obligation states *what to do*; the matching §7 entry states
  *what's still undecided* — complementary, not duplicates.)
- **§5 is a terse provenance ledger, not prose** — one line per answer plus its provenance,
  pointing to where any fuller detail lives.
- **§1 is lean orientation**, not a synopsis of the whole file.
- Prefer tables and one-line bullets to paragraphs — except the §3/§4 reasoning a later stage
  would otherwise re-derive, which you state once, there.

```markdown
# Project Context: <AppName>

## 1. Summary  *(lean orientation — one line each; don't expand defaults into paragraphs)*
- One paragraph: what is being modernized, to what, and the single hard part — at a glance.
- **Business driver** / deadline pressure (Q1) — the speed-vs-thoroughness tradeoff, in one line.
- **Parity stance** (Q3): strict parity or improvements-permitted, plus anything off-limits — one
  line; the detail lives in the parity constraint (§4), not here.

## 2. Stacks
- **Current stack:** languages, frameworks, UI tech, runtime/versions, data store,
  notable libraries. (Confirmed from the legacy app where possible — cite what you saw.)
- **Target stack:** frontend, backend, runtime/versions, build tool, data layer, auth
  libraries, anything mandated. This is the authoritative statement of "what we build in".
- **Licensing / component constraints** (Q6): paid legacy components needing replacement,
  and any license restrictions on the target.
- **UI reference** (Q23): the sample/mockup/design-system path if supplied, and whether it is
  used as a **reference** or **literally**; plus responsive, dark-mode, and i18n/RTL
  expectations. Appearance only — never a licence to change behavior.

## 3. Delivery, Cutover & Environments
- **CI/CD:** current pipeline (platform + what it does); target expectation — Respect
  existing / Generate / None yet, with specifics.
- **Cutover strategy:** big-bang / strangler fig / parallel run, and what it demands
  structurally.
- **Legacy coexistence:** whether the legacy app keeps writing to the same data store, for
  how long, and the resulting concurrency expectations.
- **Deployment target:** where the target runs.
- **Deployable units:** one artifact holding both parts, or separate artifacts — and which
  process serves the frontend bundle.
- **Runtime topology:** same origin or separate origins, plus the local dev arrangement.
  **This is the pipeline's one statement of it** — the CORS / API-base-URL / cookie-vs-token
  obligations follow from it, and no later stage re-decides it.
- **Config & secrets delivery:** how each environment supplies them.
- **Environments & test data:** what exists, and whether a representative data store is
  reachable for local testing.
- **Locations:** legacy source (read-only) / documents / target code repository — stated
  separately, noting explicitly where any of them are the same place.
- **Repository layout:** single repo (frontend and backend together) or separate repos, with
  every target path. **This is the pipeline's one statement of it** — later stages build to it.
- **Source tree roots:** the frontend root and the backend root within their repo — or, if not
  given, an explicit note that Stage 2 fixes them in the LLD and later stages build to that.
- **Release model:** shipped together as one versioned unit, or released independently — plus
  the API-compatibility obligation that follows from the answer.
- **Repository conventions:** branch naming, PR target, commit conventions, reviewers.

## 4. Constraints (non-negotiable)
For each constraint, one block — the table row plus the per-stage obligations that make it
actionable downstream:

| ID | Title | Statement | Source |
|----|-------|-----------|--------|
| C1 | …     | …         | human / derived |

- **C1 obligations** (list only the stages it affects; omit the rest):
  - *Requirements:* what this stage must capture/verify because of C1.
  - *Design:* what the design must show/honor.
  - *Plan:* what the phasing must guarantee (e.g. an early validation step).
  - *Implement:* what must hold in the running app.
  - *Review:* what compliance to check.
- Repeat for C2, C3, … These obligations are the **single place** constraint-specific rules
  live; every later stage reads them by ID rather than re-deriving them.

## 5. Intake Questionnaire (resolved)
A **provenance ledger** — one row per question, terse. Do **not** restate detail already in
§1–§10; cross-reference it instead.

| Q | Answer (one line) | Provenance |
|---|-------------------|------------|
| 1 | <the decision in a single line; where fuller, point to its home, e.g. "Reuse SQLite — see C1"> | human-supplied / `ASSUMPTION: (default applied)` / `ASSUMPTION:` (inferred) |

- Note the `INTAKE.md` this was resolved from.
- **This is a record, not an input.** To change an answer, the human edits `INTAKE.md` and
  reruns this stage.

## 6. Non-Functional / Quality Requirements (initial)
- Performance, scalability, availability, security posture, accessibility, i18n,
  observability, data-residency — as far as known now, **one line each**. (Requirements Stage
  deepens these; this section only seeds them.)
- Where an item is already an obligation (§4) or an open question (§7), **name it and
  cross-reference** — don't re-tell it here.

## 7. Open Questions
- Anything unresolved that isn't a hard-stop but should be answered before it compounds.
  Prefix `OPEN QUESTION:`. **This is the single home for each open question** — other sections
  point here by name rather than restating it.

## 8. Integrations & External Systems
| System | Direction | Contract | Disposition |
|--------|-----------|----------|-------------|
| …      | in/out/both | **fixed** / negotiable | preserve / replace / retire |
- **What was known up front** (Q10) only. The Requirements stage inventories the rest in its
  Technical document and raises anything new as an `OPEN QUESTION:` — it does not write here.
  This file is owned by Stage 0; fold discoveries in by rerunning this stage. A **fixed**
  contract means the target conforms exactly — it is effectively a constraint.

## 9. Other Sources of Truth
- Existing tests (and whether they pass), specs, runbooks, available SMEs (Q18). The
  Requirements stage should use these alongside the code, not just the code.

## 10. Performance Baseline
- Measurable current behavior the target must match or beat, **as supplied by the human**
  (Q21), or an explicit statement that none was supplied. Baselines *observed* in the legacy
  app are recorded by the Requirements stage in its Technical document instead; Review reads
  both, and reports plainly when neither exists.
```

*(Sections 8–10 are appended rather than inserted so that §4 Constraints and §5 Questionnaire
keep their numbers — every other stage document references them by those numbers.)*

---

## Output 2 — `state.json` (initialize)

This is the **single source of truth for progress, lineage, and change history** across
all stages. Markdown documents hold human-readable *content*; `state.json` holds
*machine state*. Initialize it with the context filled in and the stage/phase machinery
empty:

```json
{
  "project": "<AppName>",
  "schemaVersion": 1,
  "createdUtc": "<ISO-8601>",
  "updatedUtc": "<ISO-8601>",
  "context": {
    "currentStack": "<short string>",
    "targetStack": "<short string>",
    "parity": "strict | improvements-allowed",
    "cicd": { "mode": "respect | generate | none", "platform": "<or null>", "notes": "" },
    "cutover": { "strategy": "big-bang | strangler | parallel-run", "notes": "" },
    "legacyCoexistence": { "sharedDataStore": true, "duration": "build | cutover | indefinite | none" },
    "deploymentTarget": "<short string>",
    "deployment": {
      "units": "single-artifact | separate-artifacts",
      "topology": "same-origin | separate-origins",
      "servedBy": "<which process serves the frontend bundle, or null when separate-origins>",
      "localDev": "<how the parts are run together locally — e.g. dev-server proxy>",
      "configDelivery": "<how config/secrets reach the app per environment>"
    },
    "locations": {
      "legacySource": "<path — read-only>",
      "documents": "<path>",
      "targetRepo": "<path — the target repo; when layout is \"split\", the backend/primary one>",
      "targetRepoFrontend": "<path — only when layout is \"split\"; else null>",
      "sharedWithLegacy": false
    },
    "repo": { "layout": "single | split", "release": "together | independent",
              "frontendRoot": "<path within its repo, or null — then Design fixes it>",
              "backendRoot": "<path within its repo, or null — then Design fixes it>",
              "branchNaming": "", "prTarget": "", "conventions": "" },
    "constraints": [
      { "id": "C1", "title": "", "statement": "", "source": "human | derived",
        "obligations": { "requirements": "", "design": "", "plan": "", "implement": "", "review": "" } }
    ]
  },
  "stages": {
    "context":      { "status": "complete", "rerunCount": 0, "updatedUtc": "<ISO-8601>" },
    "requirements": { "status": "pending",  "rerunCount": 0 },
    "design":       { "status": "pending",  "rerunCount": 0 },
    "plan":         { "status": "pending",  "rerunCount": 0 }
  },
  "phases": [],
  "edits": [],
  "changeLog": [],
  "reviews": [],
  "progress": { "lastProcessedChangeLogId": 0, "lastProcessedReviewNumber": 0 }
}
```

Field notes (the later stages depend on these; keep them exact):

- **`repo.layout` / `repo.release`** — the repository-layout and release-model decisions,
  made **only in this stage**. Stages 2–4 read them to shape the internal API contract and the
  branch/PR flow; none of them decide or override. Changing either is a rerun of this stage
  plus a `changeLog` entry naming the downstream docs it invalidates.
- **`repo.frontendRoot` / `repo.backendRoot`** — where each part's tree lives inside its repo.
  Set here when the developer states them; otherwise `null`, and **Stage 2 fixes them in the
  LLD source-tree section**, after which Stages 3–4 build to that and nothing invents a
  second layout.
- **`deployment.units` / `deployment.topology`** — the deployable-unit and runtime-topology
  decisions, also made **only in this stage**. They are distinct from `repo.layout` and
  `repo.release`: layout is where source lives, release is versioning cadence, and these two
  are what ships and how the parts talk at runtime. Stage 2 designs the CORS/base-URL/session
  consequences, Stage 3 phases the test guide around them, Stage 4 must not hard-code past
  them, and Stage 5 checks the built app matches. Changing either is a rerun of this stage.
- **`stages.<name>.status`** — `pending` → `in progress` → `complete`. `rerunCount`
  increments each time a stage is rerun with additional instructions. For `plan`, it counts
  **substantive refreshes only** — a Step 0c check that left the phase list unchanged is not a
  rerun and writes nothing.
- **`phases[]`** — created by the Plan stage, and **re-synced on every plan refresh**. Each: `{ "id": "P-1", "name": "...", "status": "pending|in progress|done|accepted", "branch": "<or null>", "prUrl": "<or null>", "acceptedUtc": "<or null>", "reviewStatus": "none|pass|changes-requested|remediated", "notes": "" }`.
  - **IDs are permanent.** A refresh may drop `pending` entries and append new ones with the
    next unused number; it never renumbers or reuses an ID, and never rewrites a non-`pending`
    entry. IDs therefore stop matching execution order — the plan document holds the order.
  - `branch` / `prUrl` are written by the Implement stage so the work is findable later.
  - `reviewStatus` moves `changes-requested` → **`remediated`** when the Implement stage has
    fixed that review's findings. Nothing else clears it, and the Blocker gate reads it — so a
    review left at `changes-requested` blocks the next phase indefinitely, by design. A
    re-review after remediation is what returns it to `pass`.
  - `status: "accepted"` and `acceptedUtc` are written **only on the developer's explicit
    per-phase instruction** ("accept P-2"); an agent records them then, never on its own.
- **`edits[]`** — **minor** edits, created by the Implement stage: changes that touch no
  requirement, design contract, or plan scope (a config value, a label, an obvious bug fix).
  Anything that touches a contract is a doc change followed by a **phase**, not an edit. Each: `{ "id": "E-1", "utc": "...", "summary": "...", "afterPhase": "P-2", "status": "pending|in progress|done|accepted", "branch": "<or null>", "prUrl": "<or null>", "acceptedUtc": "<or null>", "reviewStatus": "none|pass|changes-requested|remediated" }`.
  An edit is a **reviewable unit in its own right** — it ships code, so it can be a Review
  target exactly like a phase.
- **`changeLog[]`** — the loop's memory. Each: `{ "id": <int>, "utc": "...", "author": "developer|implement-agent|review-agent", "origin": "developer-prompt|reconcile|review-<Rid>|out-of-band", "summary": "...", "docsTouched": ["requirements|design|plan|context"], "phasesAffected": ["P-3"], "editsAffected": ["E-1"] }`.
- **`reviews[]`** — created by the Review stage. Each: `{ "id": "R-1", "target": "P-3 | E-1 | whole-build", "utc": "...", "result": "pass|changes-requested", "blockerCount": <int>, "findingsCount": <int> }`.
- **`progress`** — the reconciliation **high-water mark**, written by the Implement stage at
  every hand-off. Both are **integers**, compared numerically:
  - `lastProcessedChangeLogId` — the highest `changeLog[].id` that run actually folded in.
  - `lastProcessedReviewNumber` — the `<n>` of the last `R-<n>` it addressed (`0` if none).
    It is stored as a **number, not the `R-<n>` string**, because string comparison puts
    `R-10` before `R-2`.

  Without these, a run cannot tell new entries from ones it already applied.

**Allocating ids:** `changeLog[].id` is `max(existing ids) + 1`, starting at `1`. `reviews[].id`
is `R-<n>` and `edits[].id` is `E-<n>`, each using the next unused `n` for its own array. Ids
are never reused, even if an entry is superseded.

Only ever **append** to `changeLog`, `reviews`, and `edits`; never rewrite history. Correct a
mistaken entry by appending a new one that supersedes it.

---

## Intake Questionnaire

**The question list lives in `0_INTAKE_TEMPLATE.md`**, beside these instructions — it is the
single source for what gets asked, including each question's default and whether it is
load-bearing. It is not duplicated here; read it if you need the full set.

The human copies that template to `INTAKE.md` in their project, fills in the `Answer:` lines,
and gives you the path. Blanks are expected — resolve them per Step 1.

**Load-bearing (hard-stop) questions** — no safe default exists, so the pipeline stops until
each is answered:

| Q | Question | Why it can't be defaulted |
|---|----------|---------------------------|
| 4 | Current stack | Everything downstream reads it |
| 5 | Target stack | Everything downstream reads it |
| 7 | Reuse the existing database, or new schema? | Determines how the data model is captured |
| 9 | Does the legacy app keep writing to the same data store? | A concurrent writer constrains every stage |
| 11 | Current auth, and whether to keep it | Load-bearing **only where the app is access-controlled** |
| 12 | Cutover strategy | Architecture-defining; shapes design and phase slicing |

To change the *questions* for all future projects, edit `0_INTAKE_TEMPLATE.md`. To change
*answers* for one project, edit that project's `INTAKE.md` and rerun this stage.

---

## Rerunning this Stage

The normal way to revise intake is: the human **edits their `INTAKE.md`** and reruns this
stage. They may also rerun with **Additional Instructions** (see below) for changes that
aren't questionnaire answers.

On rerun: **re-read `INTAKE.md`** as the current answers (not §5 of the previous
`PROJECT_CONTEXT.md`, which is a record of the *last* run), load the existing
`PROJECT_CONTEXT.md` and `state.json`, apply the changes, **increment
`stages.context.rerunCount`**, and — if a constraint changed after later stages ran — **add a
`changeLog` entry** describing the change and which downstream docs it invalidates, so the
affected stages get rerun. Diff the new answers against §5 of the previous run and report what
actually changed.

---

## Definition of Done

- [ ] Every load-bearing questionnaire item is answered (not defaulted); no hard-stop is
  outstanding — current stack, target stack, DB reuse, **legacy coexistence**,
  **cutover strategy**, and auth (where the app is access-controlled).
- [ ] Current stack and target stack are stated authoritatively.
- [ ] The CI/CD mode is one of respect / generate / none, with specifics.
- [ ] Repository layout (single / split) and release model (together / independent) are both
  stated, with every target path — in `PROJECT_CONTEXT.md §3` and in `state.json`
  (`context.repo.layout`, `context.repo.release`). No later stage decides these.
- [ ] Deployable units (single-artifact / separate-artifacts) and runtime topology
  (same-origin / separate-origins) are both stated in §3 and in `state.json`
  (`context.deployment.*`), along with the local dev arrangement and how config/secrets are
  supplied. No later stage decides these either.
- [ ] The frontend and backend source-tree roots are either recorded
  (`context.repo.frontendRoot` / `backendRoot`) or explicitly left to Stage 2, stated as such
  in §3 — never simply unmentioned.
- [ ] Cutover strategy is recorded, with the structural demands it implies (routing facade /
  reconciliation harness / none) expressed as constraint obligations where they bind.
- [ ] Legacy coexistence is settled; if a second live writer exists, its concurrency
  expectations are stated as a constraint.
- [ ] The constraint set is written with stable IDs, in both `PROJECT_CONTEXT.md` and
  `state.json`.
- [ ] `state.json` is initialized per schema, with `phases`, `changeLog`, `reviews` empty.
- [ ] Defaults and inferences are marked `ASSUMPTION:`; unresolved non-blockers are
  `OPEN QUESTION:`.
- [ ] Every defaulted/inferred answer is listed explicitly in the hand-off report for the
  human to confirm or override — not left to be discovered in the document.
- [ ] Neither `INTAKE.md` nor `0_INTAKE_TEMPLATE.md` was written to — the intake is an input.
  §5 of `PROJECT_CONTEXT.md` holds the resolved answers with their provenance.
- [ ] The document states each fact once: §5 is a terse provenance ledger, each recurring
  quirk/open question lives once (in §7 or its §4 obligation) and is cross-referenced elsewhere,
  and §1 is lean — while §4 obligations stay fully detailed.

---

## Additional Instructions

*(The prompt may append project-specific guidance here — the path to the filled `INTAKE.md`,
the legacy app path, an output location, answers given inline, or overrides. On a rerun, put
the human's change requests here. Treat these as overrides/additions to the above.)*
