# Intake Questionnaire

**How to fill this in**

- **One question per heading, one answer per question.** Write after `**Answer:**`.
- **Tick boxes:** change `- [ ]` to `- [x]`. Each list says *Tick one* or *Tick all that
  apply*. Use the `Answer:` line for anything the boxes don't cover (a path, a version,
  "other: …").
- **Blank is fine.** A blank question takes the *Default* shown under it, and Stage 0 tells you
  every default it applied. The exception is **⚠️ LOAD-BEARING**: Stage 0 stops and asks
  instead of guessing.
- **"Why this matters"** blocks hold the detail. In VS Code, Ctrl+Shift+V opens a preview
  where they fold away until clicked.
- Question numbers group related parts (`12a`, `12b`, …). Elsewhere, "Q12" means all of 12's
  parts.

---

## A. Drivers & Scope

### 1. Why modernize, and why now?

*Default: none stated — a like-for-like modernization with no deadline pressure.*

**Answer:**

<details><summary>Why this matters</summary>

The business driver (platform/vendor end-of-life, cost, scaling limits, compliance deadline,
unmaintainable code, talent availability) and any deadline. Sets the speed-vs-thoroughness
tradeoff every later stage makes.

</details>

### 2. What is explicitly out of scope?

Features, modules, reports, or screens the target need not reproduce.

*Default: nothing — full parity.*

**Answer:**

### 3a. Strict parity, or are improvements allowed?

*Tick one:*

- [ ] Strict parity — reproduce current behavior exactly, including known bugs and awkward UX
- [ ] Improvements allowed — the target may fix and improve

*Default: strict behavioral parity — legacy bugs are reproduced and flagged as
`OPEN QUESTION:`, never silently "fixed".*

**Answer:**

### 3b. Is anything specifically off-limits to change?

Even where improvements are allowed — e.g. a report layout the business reconciles against.

*Default: nothing beyond 3a.*

**Answer:**

---

## B. Stacks

### 4a. Current application stack?  ⚠️ LOAD-BEARING

Languages, frameworks, UI technology, runtime versions, and data store of the legacy app.

*The agent can infer this from the legacy source — but confirm it.*

**Answer:**

### 4b. Is there logic inside the database? Where can its definitions be read?

Stored procedures, triggers, views, database-scheduled jobs. Give the path to their definitions
(a schema export or DDL scripts), or write *none*.

*Default: none supplied — every piece of database-resident logic the code calls is flagged as
`OPEN QUESTION:`.*

**Answer:**

<details><summary>Why this matters</summary>

That logic is behavior the target must reproduce, and it is invisible to an extraction that
reads only the application code. It is inferable only if its definitions are supplied.

</details>

### 5a. Target frontend?  ⚠️ LOAD-BEARING

Framework and version, runtime/build tool and version. Write *none* if the target has no UI.

**Answer:**

### 5b. Target backend?  ⚠️ LOAD-BEARING

Language and version, framework, build tool.

**Answer:**

### 5c. Target data access layer?  ⚠️ LOAD-BEARING

How the backend reaches the data store — ORM, query library, driver, and how it authenticates
to the database. *(User authentication is Q11 — don't repeat it here.)*

**Answer:**

### 6a. Paid legacy components that need a replacement?

Grid controls, report engines, charting libraries, and similar.

*Default: none stated — paid components found during extraction are flagged as
`OPEN QUESTION:`.*

**Answer:**

### 6b. License restrictions on what the target may use?

E.g. no GPL, no commercial JDK.

*Default: none — any permissively licensed package may be used.*

**Answer:**

### 6c. Where may dependencies come from?

*Tick all that apply:*

- [ ] Public registries (Maven Central, npm, NuGet, PyPI)
- [ ] Only an internal mirror/proxy — give its URL or config location (e.g. `settings.xml`, `.npmrc`)
- [ ] Only an approved list of packages — give where the list is

*Default: public registries. If ecosystems differ (e.g. Maven vs. npm), say which applies to
which on the Answer line.*

**Answer:**

<details><summary>Why this matters</summary>

An agent that assumes it may pull any public package fails at the first build in a locked-down
environment.

</details>

### 6d. Does the build environment have internet access?

*Tick one:*

- [ ] Yes
- [ ] No

*Default: yes.*

**Answer:**

---

## C. Data & Coexistence

### 7. Reuse the existing database, or create a new schema?  ⚠️ LOAD-BEARING

*Tick one:*

- [ ] Reuse the existing database as-is
- [ ] New schema

**Answer:**

<details><summary>Why this matters</summary>

Drives whether the data model is captured verbatim and validated against the live schema, or
redesigned.

</details>

> **Q8 — Data migration.**
>
> **Reusing the database (Q7)?** Usually nothing moves — answer 8a with *nothing* and skip
> 8b–8f, or name any data that must still be transformed or back-filled.
> **New schema?** Every part of Q8 is ⚠️ LOAD-BEARING: a blank one is a hard stop, because an
> unplanned migration is discovered only at cutover.

### 8a. What data moves to the new schema?

*Default when reusing the database: nothing — the target connects as-is.*

**Answer:**

### 8b. What data is deliberately left behind?

*Default when reusing the database: does not apply.*

**Answer:**

### 8c. Who builds the migration?

*Tick one:*

- [ ] A build phase in this pipeline
- [ ] A separate team or tool — name it

*Default when reusing the database: does not apply.*

**Answer:**

### 8d. One-time or repeated?

*Tick one:*

- [ ] One-time — a single load at cutover
- [ ] Repeated — a recurring sync while both systems run (see Q9 and Q12a)

*Default when reusing the database: does not apply.*

**Answer:**

### 8e. How is the migration verified?

E.g. row counts, checksums, sampled record comparison, a reconciliation report.

*Default when reusing the database: does not apply.*

**Answer:**

### 8f. What happens to data that fails to migrate?

*Tick one:*

- [ ] Reject and report it
- [ ] Fill in a default value
- [ ] Block cutover until it is fixed

*Default when reusing the database: does not apply.*

**Answer:**

### 9. While the target is live — including any period when old and new run side by side — will the legacy application also write to the same data store?  ⚠️ LOAD-BEARING

*Tick one:*

- [ ] No — the legacy app stops writing before the target goes live (typical of big-bang)
- [ ] Yes, during a side-by-side period — say how long (typical of strangler fig and parallel run)
- [ ] Yes, indefinitely

*Only you can answer this — it isn't inferable from the code.*

**Answer:**

<details><summary>Why this matters</summary>

A concurrent legacy writer is a far stronger constraint than merely inheriting a schema: no
schema evolution at all, shared sequence/identity ranges, locking and transaction-isolation
concerns, and both systems must tolerate each other's writes.

What matters is whether both apps write to the same data store **at the same time**. The
legacy app running until a *big-bang* cutover does not count — the two are never live at once.
Under strangler fig or parallel run (Q12a) both are live together, so the answer is usually
*Yes* — unless the target only reads, or writes to its own copy of the data, during that period.
Stage 0 raises a side-by-side cutover on a reused database with *No* here as an
`OPEN QUESTION:`.

</details>

---

## D. Integrations

### 10. External systems the target must keep working with.

Queues, file drops/batch feeds, SMTP, third-party or internal APIs, mainframes, schedulers,
reporting/BI tools. One row per system.

| System | Contract: fixed or negotiable? | Preserve, replace, or retire? |
|--------|--------------------------------|-------------------------------|
|        |                                |                               |

*Default: discover during requirements extraction; every integration found is assumed
preserved with a fixed contract.*

**Answer:**

<details><summary>Why this matters</summary>

**Fixed** means the target must conform to the contract exactly; **negotiable** means it may
change by agreement.

</details>

---

## E. Auth

> Q11a and Q11b are ⚠️ LOAD-BEARING **where the app is access-controlled**. 11c–11e have
> defaults.
>
> **Authentication** proves who the user is. **Authorization** decides what each user may do.

### 11a. How do users log in today?  ⚠️ LOAD-BEARING

E.g. Windows/AD integrated, forms login against a users table, SSO.

*The agent can infer this from the legacy source — but confirm it.*

**Answer:**

### 11b. How should the target handle login?  ⚠️ LOAD-BEARING

*Tick one:*

- [ ] Keep the real identity provider (AD/SSO/…) — name it
- [ ] Build an auth seam + dev stub, with the real identity provider deferred
- [ ] Other — describe

**Answer:**

### 11c. Where are roles and permissions defined today?

*Tick all that apply:*

- [ ] Hard-coded checks in the source
- [ ] Tables in the database
- [ ] Directory groups (AD/LDAP)
- [ ] Claims from the identity provider

*Default: inferred from the legacy source and marked `ASSUMPTION:` — confirm it. Where the
source of a role or permission cannot be traced, it is flagged as `OPEN QUESTION:`.*

**Answer:**

### 11d. Reproduce the role model exactly, or may it be consolidated?

*Tick one:*

- [ ] Exactly — no roles merged or renamed
- [ ] May be consolidated

*Default: exactly, captured in portable terms (role → group/claim).*

**Answer:**

### 11e. Are there permission rules finer than a role?

Row-level or ownership checks ("users see only their own region's orders"), field-level hiding,
approval limits — and where the legacy app enforces them.

*Default: none known — extraction inventories every permission check it finds; any whose
source cannot be traced is flagged as `OPEN QUESTION:`.*

**Answer:**

<details><summary>Why this matters</summary>

These rules are scattered through legacy code and are the easiest behavior to lose. An
authorization rule lost in migration is a security defect, not a gap.

</details>

---

## F. Delivery, Cutover & Environments

### 12a. How will the target go live?  ⚠️ LOAD-BEARING

*Tick one:*

- [ ] Big-bang — build the replacement, switch over at once
- [ ] Strangler fig — legacy and target run side by side, traffic moved over bit by bit
- [ ] Parallel run — both live, outputs compared before the switch

**Answer:**

<details><summary>Why this matters</summary>

This is architecture-defining, not a rollout detail — it shapes the design and how the plan
slices phases. Strangler fig needs a routing facade, and phases sliced by route/feature.
Parallel run needs a comparison harness.

</details>

### 12b. If the target fails after go-live, must traffic be able to return to the legacy app?

*Tick one:*

- [ ] Yes — rollback must stay possible
- [ ] No — fix forward

*Default: no — once cut over, the target stays live and failures are fixed forward.*

**Answer:**

<details><summary>Why this matters</summary>

Rollback is only possible if the legacy app can still read everything the target has written —
so a target that evolves the schema, or writes data the legacy app does not understand, may
make rollback impossible. If rollback must stay possible, it constrains the design as hard as
Q9 does.

</details>

### 12c. If yes — for how long after go-live must rollback stay possible?

*Default (when 12b is yes): raised as an `OPEN QUESTION:`.*

**Answer:**

### 13a. Where will the target be deployed?

*Tick the most specific one that fits:*

- [ ] On-prem VM
- [ ] Container
- [ ] Kubernetes
- [ ] A specific cloud service — name it
- [ ] Serverless
- [ ] App server — name it

*Default: the same deployment model the legacy app uses today. Use the Answer line for the
rest (e.g. "Kubernetes, on Azure AKS").*

**Answer:**

<details><summary>Why this matters</summary>

Shapes configuration, secrets, health checks, and statelessness.

</details>

### 13b. How many deployable units ship?

*Tick one:*

- [ ] One artifact holding both parts (e.g. the backend serves the built frontend bundle)
- [ ] Two artifacts deployed separately (e.g. an API process plus a static bundle on a web server/CDN)

*Default: one artifact.*

**Answer:**

<details><summary>Why this matters</summary>

This is about what ships, not how many repos you have.

</details>

### 13c. Are the parts shipped together, or released independently?

*Tick one:*

- [ ] Shipped together as one versioned release
- [ ] Released independently, each on its own cadence

*Default: shipped together. Settled here and nowhere else — Design, Plan, and Implement read it
and never re-open it.*

**Answer:**

<details><summary>Why this matters</summary>

This is architectural, not operational: independent release obliges the design to give the
internal API a versioning and backward-compatibility story; shipped-together frees it from one.
Two artifacts (13b) do **not** settle this on their own — two artifacts can still be versioned
and shipped as one release — so answer it even when 13b seems to imply it.

</details>

### 13d. Once deployed, how does the frontend reach the backend?

*Tick one:*

- [ ] Same origin — one host/port; the backend or a fronting web server serves both
- [ ] Separate origins — different hosts/ports

*Default: same origin, with the frontend served from the backend.*

**Answer:**

<details><summary>Why this matters</summary>

Separate origins oblige CORS, a configurable API base URL, and a decision on cookies vs. bearer
tokens.

</details>

### 13e. How is it arranged for local development, where that differs?

E.g. a dev-server proxy standing in for same-origin.

*Default: a dev-server proxy locally.*

**Answer:**

### 14a. Which environments exist?

*Tick all that apply:*

- [ ] Dev
- [ ] Test
- [ ] Staging
- [ ] Prod

*Default: local development only.*

**Answer:**

### 14b. Can a developer reach a database with representative data?

Ideally anonymized. Say where, and how it is accessed.

*Default: no. If a phase needs a real data store and none is reachable, that is a blocker to
report, not to work around.*

**Answer:**

### 15. CI/CD expectation?

*Tick one:*

- [ ] Respect existing — the build slots into a pipeline that already exists; agents don't author pipeline files
- [ ] Generate — a phase wires up pipeline files
- [ ] None — local build/test only

*Default: none yet.*

**Answer:**

### 16a. Where is the legacy source?

**Read-only in every stage**, whether or not it shares a repo with anything else. Need not be
under version control.

*Default: the legacy path given in the Stage 0 prompt.*

**Answer:**

### 16b. Where are the documents written?

`PROJECT_CONTEXT.md`, the requirements/design/plan docs, and `state.json`.

*Default: the current working repository.*

**Answer:**

<details><summary>Why this matters</summary>

Keep these in git if you can: reconciliation diffs them to detect what changed between runs,
and degrades to change-log-only without it.

</details>

### 16c. Where is the target code repository?

Where the build branches, commits, and opens PRs.

*Default: the current working repository.*

**Answer:**

### 16d. Is the target code repository the same repo that holds the legacy source?

*Tick one:*

- [ ] Yes — the new tree is added alongside the frozen legacy one
- [ ] No

*Default: worked out from the paths in 16a and 16c.*

**Answer:**

<details><summary>Why this matters</summary>

The agent must know whether it's adding a new tree alongside a frozen legacy one. Legacy files
stay read-only either way.

</details>

### 16e. Do frontend and backend live in one repo or separate repos?

*Tick one:*

- [ ] One repo
- [ ] Separate repos — give both paths and say which holds which

*Default: one repo. Settled here and nowhere else — Design, Plan, and Implement read it and
never re-open it.*

**Answer:**

<details><summary>Why this matters</summary>

Layout is independent of the release model (13c): one repo can still ship two independently
released artifacts.

</details>

### 16f. Root directory of each part?

E.g. `./frontend` and `./backend`, or the module names in a multi-module build.

*Default: none fixed — Design fixes the source tree once, in the LLD, and every phase builds
to it.*

**Answer:**

### 16g. Branch naming?

*Default: one feature branch per phase.*

**Answer:**

### 16h. Which branch do PRs target?

*Default: the default branch.*

**Answer:**

### 16i. Commit message conventions?

*Default: none stated.*

**Answer:**

### 16j. Required reviewers?

*Default: none stated.*

**Answer:**

### 17. Phase sizing / slicing strategy.

How big each phase should be. The phase count follows from the sizing — it is not fixed up
front. Override the default rules, or name an explicit count or strategy.

*Default: the planner sizes phases per `3_PLAN_INSTRUCTIONS.md §Step 2` — one theme each,
walkable in one sitting, roughly even, no fixed count — consistent with the cutover strategy
in Q12a, and re-slices at refresh when a built phase proves the sizing wrong.*

**Answer:**

---

## G. Quality

### 18a. Are there existing automated tests? Do they pass?

*Default: code-only extraction; any tests found are noted, with whether they pass.*

**Answer:**

<details><summary>Why this matters</summary>

Legacy tests are often the best behavioral specification available.

</details>

### 18b. Written specs or runbooks?

*Default: none.*

**Answer:**

### 18c. Subject-matter experts available?

*Default: none.*

**Answer:**

### 18d. Can the legacy app be built and run somewhere a developer can reach?

*Tick one:*

- [ ] Yes — say where
- [ ] No

*Default: no — behavior is read from the code, not observed.*

**Answer:**

### 18e. Is the legacy source complete?

Missing modules, binary-only dependencies with no source, or configuration held outside the
repository all leave gaps extraction cannot close on its own.

*Tick one:*

- [ ] Yes
- [ ] No — say what is missing

*Default: assumed complete; gaps found during extraction are flagged as `OPEN QUESTION:`.*

**Answer:**

### 19a. Code style guide?

*Default: idiomatic style for the target stack.*

**Answer:**

### 19b. How is the style enforced?

The formatter/linter wired into the build.

*Default: a formatter in the build, if one is standard for the target stack.*

**Answer:**

### 19c. Do you want a unit test coverage bar?

*Tick one:*

- [ ] Yes — answer 19d–19h
- [ ] No

*Default: no. Every stage already requires tests for the behavior built, but no percentage is
enforced, and Review treats thin coverage as a non-gating Minor. No later stage invents a bar.*

**Answer:**

<details><summary>Why this matters</summary>

A bare percentage is not enforceable — a bar needs all five parts, 19d–19h. If you need
separate bars (e.g. backend and frontend), give each part for each bar.

</details>

### 19d. Coverage — metric and threshold?

E.g. line ≥ 80%, branch ≥ 70%.

*Default (when 19c is Yes): raised as an `OPEN QUESTION:` — a value is never invented.*

**Answer:**

### 19e. Coverage — scope?

*Tick one:*

- [ ] Whole codebase
- [ ] Changed/new code only

*Default (when 19c is Yes): raised as an `OPEN QUESTION:` — a value is never invented.*

**Answer:**

<details><summary>Why this matters</summary>

Changed-code bars suit a migration better: code ported early is legacy-shaped and drags a
whole-codebase number down for reasons no phase can fix.

</details>

### 19f. Coverage — exclusions?

E.g. generated sources, DTOs/records, config and bootstrap classes, migrations.

*Default (when 19c is Yes): raised as an `OPEN QUESTION:` — a value is never invented.*

**Answer:**

### 19g. Coverage — enforcement?

*Tick one:*

- [ ] Build fails below the bar
- [ ] CI-only
- [ ] Advisory report

*Default (when 19c is Yes): raised as an `OPEN QUESTION:` — a value is never invented.*

**Answer:**

<details><summary>Why this matters</summary>

"Build fails" always gates. *CI-only* gates **only** where the pipeline is generated for you
(Q15); against an existing pipeline you own, it — like *advisory* — blocks nothing.

</details>

### 19h. Coverage — from when?

*Tick one:*

- [ ] From the scaffold phase onward (recommended — retrofitting coverage across finished phases costs far more)
- [ ] From a named phase — name it

*Default (when 19c is Yes): raised as an `OPEN QUESTION:` — a value is never invented.*

**Answer:**

### 20a. Non-functional priorities — rank your top 3.

From: performance, security, availability, accessibility, scalability, observability,
maintainability, i18n.

*Default: 1. security, 2. maintainability, 3. performance.*

**Answer:**

### 20b. Is an accessibility standard required? Which one and what level?

E.g. WCAG 2.1 AA — whether ranked in 20a or mandated by policy.

*Default: no standard — the target stack's components are used with their built-in
accessibility behavior intact, but no level is verified.*

**Answer:**

<details><summary>Why this matters</summary>

"Accessible" without a standard cannot be checked, and Review will treat it as unmeasurable.

</details>

### 21. Performance baseline.

Current measurable behavior the target must match or beat — response times, batch windows,
report generation, concurrent users.

*Default: none supplied. The Requirements stage records any baseline observable in the legacy
app; without one, the Review stage has no numeric bar and will say so.*

**Answer:**

### 22a. Compliance or regulatory constraints?

*Default: none stated.*

**Answer:**

### 22b. Audit-trail obligations?

*Default: none stated.*

**Answer:**

### 22c. Data-retention obligations?

*Default: none stated.*

**Answer:**

### 22d. Data-residency obligations?

*Default: none stated.*

**Answer:**

---

## H. User Interface

### 23a. Is there a UI reference for the target? Give its path.

A sample page, mockup, design system, component library you already standardize on, or
screenshots (e.g. `./ui-sample/`).

*Default: no reference supplied. The design picks idiomatic defaults for the target stack and
records them as the design language anyway, so screens stay consistent across phases.*

**Answer:**

<details><summary>Why this matters</summary>

**A good sample covers roughly 80% of a CRUD app's surface:** the app shell (nav, header, page
frame), a table/list view, a form including required markers and validation errors, buttons in
every state, and one modal.

> **Boundary — this governs appearance only.** A UI reference never changes *behavior*.
> Screens, fields, validation, and flows still come from the requirements. If the sample
> implies a different flow than the legacy app, that is an `OPEN QUESTION:`, not a licence to
> redesign — especially under strict parity (Q3a).

</details>

### 23b. How should the UI reference be used?

*Tick one:*

- [ ] Reference — extract a visual language, build with the target stack's own components themed to match
- [ ] Literal — reproduce the sample's markup and CSS as-is

*Default: reference.*

**Answer:**

<details><summary>Why this matters</summary>

- **Reference** *(recommended)* — the design extracts a visual language from it (colors, type
  scale, spacing, radii, elevation, layout and component patterns) and builds with the target
  stack's own components, themed to match. Idiomatic and accessible.
- **Literal** — only sensible when the sample is already written in the target framework;
  otherwise it means fighting that framework, with brittle overrides and lost
  keyboard/accessibility behavior.

</details>

### 23c. Must the UI be responsive?

*Tick one:*

- [ ] Yes
- [ ] No

*Default: not required.*

**Answer:**

### 23d. Is dark mode required?

*Tick one:*

- [ ] Yes
- [ ] No

*Default: not required.*

**Answer:**

### 23e. Any i18n or right-to-left (RTL) language need?

*Default: none.*

**Answer:**

### 23f. Which browsers and devices must be supported?

E.g. current Chrome/Edge only, a named older browser, or tablets.

*Default: the current versions of the major evergreen browsers (Chrome, Edge, Firefox, Safari)
on desktop.*

**Answer:**

<details><summary>Why this matters</summary>

Legacy apps are sometimes tied to one browser, and users may still be on it — the target
stack's supported-browser list must cover them.

</details>

---

## I. Reference Implementations

### 24. Reference implementations — example code the build should follow for a given area.

One row per area; leave the table empty if you have none. **Mode** is `reference` or
`literal`. **Governs** is what the sample dictates — fill it in for every row.

| Area | Path | Mode | Governs |
|------|------|------|---------|
|      |      |      |         |

*Default: none supplied. Each stage picks idiomatic defaults for the target stack.*

**Answer:**

<details><summary>Why this matters — and example rows</summary>

| Area | Path | Mode | Governs |
|------|------|------|---------|
| Deployment | `./refs/deploy/` | reference | Dockerfile layering, compose/chart structure, values layout, probe and secret conventions — **not** this app's names, ports, or resource sizing |
| Auth | `./refs/auth/` | reference | token shape, claim names, filter/middleware chain, refresh and logout handling |
| File upload/download | `./refs/storage/` | literal | streaming, size-limit and content-type handling, reproduced as given |

The areas worth supplying are the ones every project otherwise rewrites badly from scratch:
**deployment** (Dockerfile, compose, Helm chart, pipeline templates), **auth**, **file
upload/download**, logging and observability wiring, error handling and API envelope shape,
and integration clients.

**Mode:**
- **Reference** *(recommended, and the default)* — follow the sample's **shape**: its
  structure, layering, naming conventions, and the way it decomposes the problem. Substitute
  this app's own names, values, and details. The result should read as though written by the
  same team — not copied.
- **Literal** — reproduce the sample as-is, changing only what cannot stay (package names,
  identifiers). Only sensible when the sample is already written in the target stack and you
  want exactly it.

**Governs** is the field that stops an agent absorbing a reference's *business logic* along
with its shape. Say what the sample dictates, and — where it matters — what it does not. A
reference Dockerfile is purely structural and carries no behavior; reference auth code
genuinely *does* dictate behavior (token shape, session model, claim names), which is usually
the whole reason you supplied it. Both are legitimate. They simply grade differently in Review,
which checks each row against **its own** Governs scope and nothing wider.

> **A reference is not a requirement.** Where a sample implies behavior the requirements don't
> call for — an extra endpoint, a field, a flow — that is an `OPEN QUESTION:`, not a licence to
> build it. Where it **conflicts** with a requirement or a constraint, the requirement or
> constraint wins and the conflict is reported rather than silently resolved.

**The UI is deliberately not a row here — it is Q23.** Its boundary is narrower (appearance
only) and its per-stage obligations differ. Don't answer it twice.

</details>

---

## J. Ownership

> The pipeline stops at gates and raises `OPEN QUESTION:` items that only a person can settle —
> a legacy bug to keep or fix, an ambiguous rule, an exclusion from a coverage bar.

### 25a. Who answers business-rule questions?

E.g. a product owner or SME.

*Default: the developer running the pipeline.*

**Answer:**

### 25b. Who answers technical questions?

E.g. a tech lead.

*Default: the developer running the pipeline.*

**Answer:**

### 25c. Who signs off a finished phase before the next one starts?

*Default: the developer running the pipeline.*

**Answer:**

### 25d. How quickly are open questions usually answered?

So the plan can sequence around ones that will be slow.

*Default: none stated.*

**Answer:**

---

*Project-specific questions can be appended here, one question per heading, numbered from 26.
Mark any question the team wants to force an answer to as ⚠️ LOAD-BEARING.*
