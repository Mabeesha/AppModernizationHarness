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
Languages, frameworks, UI technology, and data store of the legacy app.
*The agent can infer this from the legacy source — but confirm it.*

**Answer:**

**5. Target stack?**  ⚠️ **LOAD-BEARING**
Frontend, backend, runtime + versions, build tool, data layer. *(Auth is Q11 — don't repeat
it here.)*

**Answer:**

**6. Licensing or component constraints?**
Paid legacy components needing a replacement (grid controls, report engines, charting), or
license restrictions on what the target may use (e.g. no GPL, no commercial JDK).
*Default: none stated; paid legacy components found during extraction are flagged as
`OPEN QUESTION:`.*

**Answer:**

---

## C. Data & Coexistence

**7. Reuse the existing database, or create a new schema?**  ⚠️ **LOAD-BEARING**
Drives whether the data model is captured verbatim and validated against the live schema, or
redesigned.

**Answer:**

**8. If reusing: is data migration in scope, or connect as-is?**
*Default: connect as-is, no migration.*

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

**11. How does the app authenticate today, and should the target keep it?**
⚠️ **LOAD-BEARING** where the app is access-controlled.
E.g. keep real AD/SSO, or build an auth seam + dev stub with the real IdP deferred.
*Inferable from the legacy source — confirm.*

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

**Answer:**

**13. Deployment target?**
On-prem VM / container / Kubernetes / a specific cloud / serverless / app server. Shapes
configuration, secrets, health checks, and statelessness.
*Default: the same deployment model the legacy app uses today.*

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

**16. Locations, and repository conventions.**
Name all three explicitly — they are often, but not always, the same place:
- **Legacy source** — where the app being modernized lives. **Read-only in every stage**,
  whether or not it shares a repo with anything else. Need not be under version control.
- **Documents** — where `PROJECT_CONTEXT.md`, the requirements/design/plan docs, and
  `state.json` are written. Keep these in git if you can: reconciliation diffs them to detect
  what changed between runs, and degrades to change-log-only without it.
- **Target code repository** — where the build branches, commits, and opens PRs. **A single
  repo holds the whole target** (frontend and backend together). **Say so explicitly if this
  is the same repo that holds the legacy source** — the agent must know whether it's adding a
  new tree alongside a frozen legacy one. Legacy files stay read-only either way.

Plus conventions: branch naming, which branch PRs target, commit message conventions, required
reviewers.
*Default: documents and target code both in the current working repository; legacy source
read-only wherever it sits; feature branches per phase; PRs target the default branch.*

**Answer:**

**17. Preferred phase count or slicing strategy?**
*Default: the planner decides — 3–7 phases, consistent with the cutover strategy in Q12.*

**Answer:**

---

## G. Quality

**18. Other sources of truth besides the code.**
Existing automated tests, written specs, runbooks, or available subject-matter experts. Legacy
tests are often the best behavioral specification available.
*Default: code-only extraction; note if tests exist and whether they pass.*

**Answer:**

**19. Code style / quality gates the target must enforce?**
*Default: idiomatic style for the target stack, with a formatter in the build if one is
standard for it.*

**Answer:**

**20. Non-functional priorities — rank your top 3.**
From: performance, security, availability, accessibility, scalability, observability,
maintainability, i18n.
*Default: security, maintainability, performance.*

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

> **Boundary — this governs appearance only.** A UI reference never changes *behavior*.
> Screens, fields, validation, and flows still come from the requirements. If the sample
> implies a different flow than the legacy app, that is an `OPEN QUESTION:`, not a licence to
> redesign — especially under strict parity (Q3).

*Default: no reference supplied. The design picks idiomatic defaults for the target stack and
records them as the design language anyway, so screens stay consistent across phases.*

**Answer:**

---

*Project-specific questions can be appended here. Mark any question the team wants to force an
answer to as load-bearing.*
