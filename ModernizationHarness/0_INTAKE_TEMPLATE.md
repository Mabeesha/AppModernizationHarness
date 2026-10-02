## A. Drivers & Scope

**1. Why modernize, and why now?**
The business driver (platform/vendor end-of-life, cost, scaling limits, compliance deadline,
unmaintainable code, talent availability). Sets the speed-vs-thoroughness tradeoff every later
stage makes.
*Default: none stated — a like-for-like modernization with no deadline pressure.*

**Answer:**

**2. What is explicitly out of scope?**
Features, modules, or screens the target need not reproduce.
*Default: nothing — full parity.*

**Answer:**

**3. Strict parity, or are improvements allowed?**
Must the target reproduce current behavior exactly — including known bugs and awkward UX — or
may it fix and improve? Name anything specifically off-limits to change.
*Default: strict behavioral parity — legacy bugs are reproduced and flagged as
`OPEN QUESTION:`, never silently "fixed".*

**Answer:**

---

## B. Stacks

**4. Current stack?**  ⚠️ **LOAD-BEARING**
Languages, frameworks, UI technology, and data store of the legacy app. Include any logic that
lives **in the database rather than the application source** — stored procedures, triggers,
views, database-scheduled jobs — and say where its definitions can be read. That logic is
behavior the target must reproduce, and it is invisible to an extraction that reads only the
application code.
*The agent can infer the application stack from the legacy source — but confirm it.
Database-resident logic is inferable only if its definitions are supplied; otherwise it is
flagged as `OPEN QUESTION:`.*

**Answer:**

**5. Target stack?**  ⚠️ **LOAD-BEARING**
Frontend, backend, runtime + versions, build tool, data layer. *(Auth is Q11 — don't repeat
it here.)*

**Answer:**

**6. Licensing, component, or package-source constraints?**
Paid legacy components needing a replacement (grid controls, report engines, charting), or
license restrictions on what the target may use (e.g. no GPL, no commercial JDK).
Also state **where dependencies may come from**: public registries (Maven Central, npm,
NuGet, PyPI), only an internal mirror/proxy (give its URL or config location), or an approved
list of packages. Say whether the build environment has internet access at all. An agent that
assumes it may pull any public package fails at the first build in a locked-down environment.
*Default: none stated; public registries are reachable and any permissively licensed package
may be used. Paid legacy components found during extraction are flagged as
`OPEN QUESTION:`.*

**Answer:**

---

## C. Data & Coexistence

**7. Reuse the existing database, or create a new schema?**  ⚠️ **LOAD-BEARING**
Drives whether the data model is captured verbatim and validated against the live schema, or
redesigned.

**Answer:**

**8. Data migration — what moves, and how?**  ⚠️ **LOAD-BEARING if Q7 is a new schema**
The answer depends on Q7:
- **Reusing the existing database** — usually nothing moves: the target connects as-is. Say
  so, or name any data that must still be transformed or back-filled.
- **New schema** — existing data must be moved into it, and this question decides how. State:
  **who builds the migration** (a build phase in this pipeline, or a separate team/tool);
  **one-time or repeated** (a single load at cutover, or a recurring sync while both systems
  run — see Q9 and Q12); **how it is verified** (row counts, checksums, sampled record
  comparison, a reconciliation report); and **what happens to data that fails to migrate**
  (reject and report, default it, or block cutover). Name any data that is deliberately left
  behind.
*Default when reusing: connect as-is, no migration. No default for a new schema — a blank
answer there is a hard stop, because an unplanned migration is discovered only at cutover.*

**Answer:**

**9. Will the legacy application keep running against the same data store?**  ⚠️ **LOAD-BEARING**
During the build, at cutover, indefinitely, or not at all. A concurrent legacy writer is a far
stronger constraint than merely inheriting a schema: no schema evolution at all, shared
sequence/identity ranges, locking and transaction-isolation concerns, and both systems must
tolerate each other's writes.
*Only you can answer this — it isn't inferable from the code.*

**Answer:**

---

## D. Integrations

**10. External systems the target must keep working with.**
Queues, file drops/batch feeds, SMTP, third-party or internal APIs, mainframes, schedulers,
reporting/BI tools. For each, note whether its **contract is fixed** (we must conform exactly)
or **negotiable**, and whether it is preserved, replaced, or retired.
*Default: discover during requirements extraction; every integration found is assumed
preserved with a fixed contract.*

**Answer:**

---

## E. Auth

**11. How does the app authenticate and authorize today, and should the target keep them?**
⚠️ **LOAD-BEARING** where the app is access-controlled.
Two parts — answer both, because they are different questions:
- **Authentication** (proving who the user is) — e.g. keep real AD/SSO, or build an auth
  seam + dev stub with the real IdP deferred.
- **Authorization** (deciding what each user may do) — the roles and permissions, and
  **where they are defined today**: hard-coded checks in the source, tables in the database,
  directory groups (AD/LDAP), or claims from the identity provider. Say whether the target
  must reproduce the role model **exactly**, or may consolidate it. Name any rule finer than a
  role — row-level or ownership checks ("users see only their own region's orders"),
  field-level hiding, approval limits — because those are scattered through legacy code and
  are the easiest behavior to lose.
*Inferable from the legacy source — confirm. Default for authorization: the legacy role model
is reproduced exactly, captured in portable terms (role → group/claim); permission rules found
during extraction whose source cannot be traced are flagged as `OPEN QUESTION:`.*

**Answer:**

---

## F. Delivery, Cutover & Environments

**12. Cutover strategy?**  ⚠️ **LOAD-BEARING**
How the target goes live. This is architecture-defining, not a rollout detail — it shapes the
design and how the plan slices phases:
- **Big-bang** — build the replacement, switch over at once.
- **Strangler fig** — legacy and target run side by side with traffic routed incrementally.
  Needs a routing facade, and phases sliced by route/feature.
- **Parallel run** — both live, outputs reconciled before the switch. Needs a comparison
  harness.

**Also state the rollback plan:** if the target fails after go-live, can traffic return to the
legacy app, and within what window? Rollback is only possible if the legacy app can still read
everything the target has written — so a target that evolves the schema, or writes data the
legacy app does not understand, may make rollback impossible. If rollback must stay possible,
say so: it constrains the design as hard as Q9 does.
*Default for rollback: none required — once cut over, the target stays live and failures are
fixed forward.*

**Answer:**

**13. Deployment target, deployable units, release model, and runtime topology?**
Four answers, because they are decided together and each shapes the build. The release model
is **settled here and nowhere else** — Design, Plan, and Implement read it and never re-open
it:
- **Target** — on-prem VM / container / Kubernetes / a specific cloud / serverless / app
  server. Shapes configuration, secrets, health checks, and statelessness.
- **Deployable units** — what actually ships: **one artifact** holding both parts (e.g. the
  backend serves the built frontend bundle), or **two artifacts** deployed separately (an API
  process plus a static bundle on a web server/CDN). Independent of how many repos you have.
- **Release model** — are the parts **shipped together** as one versioned unit, or **released
  independently**, each deployable on its own cadence? This is architectural, not operational:
  independent release obliges the design to give the internal API a versioning and
  backward-compatibility story; shipped-together frees it from one. Two artifacts do **not**
  settle this on their own — two artifacts can still be versioned and shipped as one release —
  so answer it even when the units answer seems to imply it.
- **Runtime topology** — how the frontend reaches the backend once deployed: **same origin**
  (one host/port; the backend or a fronting web server serves both) or **separate origins**
  (different hosts/ports — which obliges CORS, a configurable API base URL, and a decision on
  cookies vs. bearer tokens). Note the local dev arrangement too where it differs, e.g. a
  dev-server proxy standing in for same-origin.
*Default: the same deployment model the legacy app uses today; one deployable unit, shipped
together as one versioned release, serving the frontend from the backend at the same origin,
with a dev-server proxy locally.*

**Answer:**

**14. Environments & test data.**
Which environments exist (dev/test/staging/prod), and can the developer reach a database with
representative (ideally anonymized) data?
*Default: local development only. If a phase needs a real data store and none is reachable,
that is a blocker to report, not to work around.*

**Answer:**

**15. CI/CD expectation?**
**Respect existing** (the build slots into a pipeline that already exists; agents don't author
pipeline files) / **Generate** (a phase wires up pipeline files) / **None**.
*Default: None yet — local build/test only.*

**Answer:**

**16. Locations, repository layout, and conventions.**
Three parts. Answer each under its own label — they are separate decisions that happen to be
recorded together.

**16a. Locations.** Name all three explicitly — they are often, but not always, the same
place:
- **Legacy source** — where the app being modernized lives. **Read-only in every stage**,
  whether or not it shares a repo with anything else. Need not be under version control.
- **Documents** — where `PROJECT_CONTEXT.md`, the requirements/design/plan docs, and
  `state.json` are written. Keep these in git if you can: reconciliation diffs them to detect
  what changed between runs, and degrades to change-log-only without it.
- **Target code repository** — where the build branches, commits, and opens PRs. **Say so
  explicitly if this is the same repo that holds the legacy source** — the agent must know
  whether it's adding a new tree alongside a frozen legacy one. Legacy files stay read-only
  either way.
*Default: documents and target code both in the current working repository; legacy source
read-only wherever it sits.*

**16b. Repository layout.** **Settled here and nowhere else** — Design, Plan, and Implement
read it and never re-open it. Do frontend and backend live in **one repo** together, or in
**separate repos**? If separate, give both paths and say which holds which. Either way, give
the **root directory of each part** (e.g. `./frontend` and `./backend`, or the module names in
a multi-module build) if you have a preference — otherwise Design fixes the source tree once,
in the LLD, and every phase builds to it. Layout is independent of the release model (Q13):
one repo can still ship two independently released artifacts.
*Default: single repo holding frontend and backend together, in sibling `frontend/` and
`backend/` roots.*

**16c. Conventions.** Branch naming, which branch PRs target, commit message conventions,
required reviewers.
*Default: feature branches per phase; PRs target the default branch.*

**Answer:**

*16a — Locations:*

*16b — Repository layout:*

*16c — Conventions:*

**17. Phase sizing / slicing strategy.**
How big each phase should be. The phase count follows from the sizing — it is not fixed up
front. Override any of those rules, or name an explicit count or strategy.
*Default: the planner sizes phases per `3_PLAN_INSTRUCTIONS.md §Step 2` — one theme each,
walkable in one sitting, roughly even, no fixed count — consistent with the cutover strategy
in Q12, and re-slices at refresh when a built phase proves the sizing wrong.*

**Answer:**

---

## G. Quality

**18. Other sources of truth besides the code.**
Existing automated tests, written specs, runbooks, or available subject-matter experts. Legacy
tests are often the best behavioral specification available.

Also state **whether the legacy app can be built and run** — locally or in an environment the
developer can reach — so its behavior can be observed rather than only read. And state
**whether the legacy source is complete**: missing modules, binary-only dependencies with no
source, or configuration held outside the repository all leave gaps extraction cannot close
on its own.
*Default: code-only extraction; note if tests exist and whether they pass. The legacy app is
assumed not runnable and the source assumed complete; gaps found during extraction are flagged
as `OPEN QUESTION:`.*

**Answer:**

**19. Code style / quality gates the target must enforce?**
Name the style guide and the enforcement mechanism (formatter/linter wired into the build).

**Unit test coverage — state a bar here if you want one, because no later stage invents one.**
If you do, give all five parts; a bare percentage is not enforceable:
- **Metric & threshold** — e.g. line ≥ 80%, branch ≥ 70%.
- **Scope** — whole codebase, or changed/new code only. (Changed-code bars suit a migration
  better: code ported early is legacy-shaped and drags a whole-codebase number down for
  reasons no phase can fix.)
- **Exclusions** — generated sources, DTOs/records, config and bootstrap classes, migrations.
- **Enforcement** — *build fails* below the bar, *CI-only*, or *advisory report*.
  "Build fails" always gates. *CI-only* gates **only** where the pipeline is generated for you
  (Q15); against an existing pipeline you own, it — like *advisory* — blocks nothing.
- **From when** — from the scaffold phase onward (recommended — retrofitting coverage across
  finished phases costs far more), or from a named phase.
*Default: idiomatic style for the target stack, with a formatter in the build if one is
standard for it. **No coverage threshold** — every stage already requires tests for the
behavior built, but no percentage is enforced, and Review treats thin coverage as a
non-gating Minor.*

**Answer:**

**20. Non-functional priorities — rank your top 3.**
From: performance, security, availability, accessibility, scalability, observability,
maintainability, i18n.

**Accessibility, if it is required at all** — whether ranked or mandated by policy — name the
standard and level (e.g. WCAG 2.1 AA). "Accessible" without a standard cannot be checked, and
Review will treat it as unmeasurable.
*Default: security, maintainability, performance. No accessibility standard — the target
stack's components are used with their built-in accessibility behavior intact, but no level is
verified.*

**Answer:**

**21. Performance baseline.**
Current measurable behavior the target must match or beat — response times, batch windows,
report generation, concurrent users.
*Default: none supplied. The Requirements stage records any baseline observable in the legacy
app; without one, the Review stage has no numeric bar and will say so.*

**Answer:**

**22. Compliance/regulatory constraints.**
Plus any audit-trail, data-retention, or data-residency obligations.
*Default: none stated.*

**Answer:**

---

## H. User Interface

**23. Is there a UI reference for the target — a sample page, mockup, or design system?**
Give its path (e.g. `./ui-sample/`) if you have one. A small HTML/CSS sample is ideal; so is a
component library you already standardize on, or screenshots.

**How it will be used — say which, because the two differ sharply:**
- **Reference** *(recommended, and the default)* — the design extracts a visual language from
  it (colors, type scale, spacing, radii, elevation, layout and component patterns) and builds
  with the **target stack's own components, themed to match**. Idiomatic and accessible.
- **Literal** — reproduce the sample's markup and CSS as-is. Only sensible when the sample is
  already written in the target framework; otherwise it means fighting that framework, with
  brittle overrides and lost keyboard/accessibility behavior.

**A good sample covers roughly 80% of a CRUD app's surface:** the app shell (nav, header, page
frame), a table/list view, a form including required markers and validation errors, buttons in
every state, and one modal.

**Also state:** must it be **responsive**? Is **dark mode** required? Any **i18n/RTL** need?
Which **browsers and devices** must be supported (e.g. current Chrome/Edge only, or a named
older browser, or tablets)? Legacy apps are sometimes tied to one browser, and users may still
be on it — the target stack's supported-browser list must cover them.
*Default for browsers: the current versions of the major evergreen browsers (Chrome, Edge,
Firefox, Safari) on desktop.*

> **Boundary — this governs appearance only.** A UI reference never changes *behavior*.
> Screens, fields, validation, and flows still come from the requirements. If the sample
> implies a different flow than the legacy app, that is an `OPEN QUESTION:`, not a licence to
> redesign — especially under strict parity (Q3).

*Default: no reference supplied. The design picks idiomatic defaults for the target stack and
records them as the design language anyway, so screens stay consistent across phases.*

**Answer:**

---

## I. Reference Implementations

**24. Do you have reference implementations for the target — example code the build should
follow for a given area?**
One row per area; leave the table empty if you have none.

| Area | Path | Mode | Governs |
|------|------|------|---------|
| Deployment | `./refs/deploy/` | reference | Dockerfile layering, compose/chart structure, values layout, probe and secret conventions — **not** this app's names, ports, or resource sizing |
| Auth | `./refs/auth/` | reference | token shape, claim names, filter/middleware chain, refresh and logout handling |
| File upload/download | `./refs/storage/` | literal | streaming, size-limit and content-type handling, reproduced as given |

The areas worth supplying are the ones every project otherwise rewrites badly from scratch:
**deployment** (Dockerfile, compose, Helm chart, pipeline templates), **auth**, **file
upload/download**, logging and observability wiring, error handling and API envelope shape,
and integration clients.

**Mode — say which for every row, because the two differ sharply:**
- **Reference** *(recommended, and the default)* — follow the sample's **shape**: its
  structure, layering, naming conventions, and the way it decomposes the problem. Substitute
  this app's own names, values, and details. The result should read as though written by the
  same team — not copied.
- **Literal** — reproduce the sample as-is, changing only what cannot stay (package names,
  identifiers). Only sensible when the sample is already written in the target stack and you
  want exactly it.

**The Governs scope is per-row, and you must fill it in.** It is the field that stops an agent
absorbing a reference's *business logic* along with its shape. Say what the sample dictates,
and — where it matters — what it does not. A reference Dockerfile is purely structural and
carries no behavior; reference auth code genuinely *does* dictate behavior (token shape,
session model, claim names), which is usually the whole reason you supplied it. Both are
legitimate. They simply grade differently in Review, which checks each row against **its own**
Governs scope and nothing wider.

> **A reference is not a requirement.** Where a sample implies behavior the requirements don't
> call for — an extra endpoint, a field, a flow — that is an `OPEN QUESTION:`, not a licence to
> build it. Where it **conflicts** with a requirement or a constraint, the requirement or
> constraint wins and the conflict is reported rather than silently resolved.

**The UI is deliberately not a row here — it is Q23.** Its boundary is narrower (appearance
only) and its per-stage obligations differ, so it keeps its own question. Don't answer it twice.

*Default: none supplied. Each stage picks idiomatic defaults for the target stack.*

**Answer:**

---

## J. Ownership

**25. Who decides, and who signs off?**
The pipeline stops at gates and raises `OPEN QUESTION:` items that only a person can settle —
a legacy bug to keep or fix, an ambiguous rule, an exclusion from a coverage bar. Name:
- **Decision owner(s)** — who answers open questions, split by kind where it differs
  (business rules → a product owner or SME; technical choices → a tech lead).
- **Phase sign-off** — who approves a finished phase before the next one starts.
- **Expected turnaround** — how quickly open questions are answered, so the plan can sequence
  around ones that will be slow.
*Default: the developer running the pipeline owns every decision and every sign-off.*

**Answer:**

---

*Project-specific questions can be appended here. Mark any question the team wants to force an
answer to as load-bearing.*
