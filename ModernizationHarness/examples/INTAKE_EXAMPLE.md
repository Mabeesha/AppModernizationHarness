# INTAKE — <App> (house template for the <Programme> modernization set)

> **How to use this file.** This is a *filled* intake, not the blank template
> (`0_INTAKE_TEMPLATE.md`). The answers below are the **house standards** that apply to every
> app in the set — copy this file per app, rename it `INTAKE.md`, and edit only what is marked.
>
> | Marker | Meaning |
> |---|---|
> | *(house standard)* | Settled across the whole set. Do not change without a programme-level decision. |
> | ⬜ **FILL PER APP** | You must answer before running Stage 0. |
> | ⬜ **LOAD-BEARING — FILL PER APP** | Stage 0 will hard-stop without it. Not inferable from code. |
>
> Stage 0 reads this file, resolves every answer with provenance into `PROJECT_CONTEXT.md §5`,
> and derives the constraint set in `§4`. **It never writes back here.** To change an answer
> later, edit this file and rerun Stage 0.

---

## A. Drivers & Scope

**1. Why modernize, and why now?**

**Answer:** ⬜ **FILL PER APP.** State the business driver and any deadline — it sets the
speed-vs-thoroughness tradeoff every later stage makes. If there is genuinely none, say
"no deadline pressure; like-for-like modernization".

**2. What is explicitly out of scope?**

**Answer:** ⬜ **FILL PER APP.** Name any screens, modules, or reports the target need not
reproduce. Default if blank: nothing — full parity.

**3. Strict parity, or are improvements allowed?**

**Answer:** *(house standard)* **Strict behavioral parity.** The target reproduces current
behavior exactly, including known bugs and awkward UX. Legacy bugs are reproduced and flagged
as `OPEN QUESTION:`, never silently "fixed". UI *appearance* may modernize per Q23; behavior,
fields, validation and flows may not.

⬜ **FILL PER APP:** anything specifically off-limits to change even cosmetically (e.g. a
report layout the business reconciles against).

---

## B. Stacks

**4. Current stack?**  ⚠️ **LOAD-BEARING**

**Answer:** *(house standard — extraction instruction)*
**Extract this from the legacy source; do not ask me for it.** Inspect the legacy app at the
path given in Q16 and record languages, frameworks, UI technology, runtime versions, data
store, and notable libraries — citing the files you read as evidence. Record every inferred
value as `ASSUMPTION:` (inferred), list them in the hand-off report under *"Answered without
you — confirm or override"*, and **proceed without hard-stopping**. A one-line summary is
enough here; the full inventory is Stage 1's Technical document, not this question.

If the legacy source path is missing or unreadable, *then* stop and ask.

**5. Target stack?**  ⚠️ **LOAD-BEARING**

**Answer:** *(house standard)*

| Layer | Decision |
|---|---|
| Frontend | **Angular 22**, built and tooled on **Node 22**. Node is a **build-time runtime only** — no Node server process ships. |
| Frontend packaging | Static bundle served by nginx in its own container (see Q13). |
| Backend | **Java 21**, built with **Maven** — ⬜ **FILL PER APP / PROGRAMME:** the framework (Spring Boot? — Q26's springdoc answer presumes it). |
| Backend build | **Maven.** All gates are Maven plugins bound to the build lifecycle so they fail `mvn verify`, not just a separate command: Spotless (format), JaCoCo (coverage, Q19). |
| Persistence | **JPA / Hibernate**, with **explicit hand-written entity↔table mapping**. The schema is inherited and not ours to redesign (Q7): every `@Table` / `@Column` name is written out to match the live schema exactly, never left to a naming strategy. **Schema generation is off** — `ddl-auto` is `validate` locally and `none` in deployed environments; Hibernate may never create, alter, or drop anything. |
| Data store | **Existing Microsoft SQL Server**, reached over JDBC (`mssql-jdbc`) using **integrated Kerberos authentication** (`authenticationScheme=JavaKerberos`). No SQL logins, and no password ever in a connection string. |
| API documentation | **springdoc-openapi**, code-first — see Q26. |

*(Auth libraries are Q11, not here.)*

**6. Licensing or component constraints?**

**Answer:** ⬜ **FILL PER APP.** Paid legacy components needing replacement (grid controls,
report engines, charting) and any license restrictions on the target. Default if blank: none
stated; paid components found during extraction are flagged as `OPEN QUESTION:`.

---

## C. Data & Coexistence

**7. Reuse the existing database, or create a new schema?**  ⚠️ **LOAD-BEARING**

**Answer:** *(house standard)* **Reuse the existing MS SQL database as-is.** No schema
redesign, no new schema, no table or column renaming. The data model is captured **verbatim**
— exact table, column, and constraint names — and the mapping is validated against the live
schema in the phase that first touches persistence.

**How that validation is mechanized:** Hibernate's `ddl-auto: validate` against a real instance
of the schema. That makes "the entity mapping validates against the live schema" a falsifiable
phase exit criterion rather than a self-assessment — the application context fails to start on
any mismatch. It depends on Q14 having a reachable database; if none exists, say so there.

**8. If reusing: is data migration in scope, or connect as-is?**

**Answer:** *(house standard)* **Connect as-is. No data migration.**

**9. Will the legacy application keep running against the same data store?**  ⚠️ **LOAD-BEARING**

**Answer:** ⬜ **LOAD-BEARING — FILL PER APP.** Choose one and say for how long:
*during the build / until cutover / indefinitely / not at all.*

> Read this before answering. A concurrent legacy **writer** is a far stronger constraint than
> merely inheriting a schema: no schema evolution at all, shared identity/sequence ranges,
> explicit transaction-isolation and locking expectations, and both systems must tolerate each
> other's writes. Across a set of apps modernized one at a time against a shared database,
> "yes, indefinitely" is the likely answer — and it is the single most expensive fact in this
> file to get wrong. Nothing in the code can tell the agent this.
>
> **If yes, it constrains JPA specifically:** Hibernate's second-level cache and query cache
> must be **off** (another writer invalidates them without our knowing), optimistic locking via
> `@Version` needs a column the legacy writer also maintains — or it can't be used at all — and
> identity generation must not assume our process owns the sequence. Say so here; the
> constraint's *Design* obligation is where those rules get written down.

---

## D. Integrations

**10. External systems the target must keep working with.**

**Answer:** ⬜ **FILL PER APP.** One row per system — queues, file drops, SMTP, internal APIs,
schedulers, reporting/BI — noting whether its contract is **fixed** or negotiable, and whether
it is preserved, replaced, or retired. Default if blank: discovered during requirements
extraction and assumed preserved with a fixed contract.

---

## E. Auth

**11. How does the app authenticate today, and should the target keep it?**  ⚠️ **LOAD-BEARING**

**Answer:** *(house standard)*

**Target — Microsoft Entra ID.** OIDC/OAuth2. The backend is a **resource server validating
JWT bearer tokens**; the frontend acquires tokens via **MSAL**. Tenant ID, client ID, audience
and issuer are **configuration keys**, never compiled in. **No client secret in the repository.**

**Build it behind an auth seam with two implementations:**

1. **Entra provider** — the real one. Validates signature, issuer, audience and expiry against
   the tenant's published signing keys.
2. **Dev stub** — selected by a **local-only profile**, issuing a fixed set of test principals
   with configurable roles and bypassing Entra entirely. It exists so local testing and the
   `HOW_TO_TEST.md` walkthrough need no Entra account. **It must be structurally incapable of
   activating under the production profile** — not merely switched off by a default value.

**Authorization model:** roles mapped from Entra **app roles / group claims**. Capture the
legacy role model in portable terms (role → group/claim) during requirements extraction,
independent of either provider.

**Legacy side:** ⬜ **CONFIRM PER APP** — extract how the legacy app authenticates today
(Windows/AD integrated, forms auth against a table, etc.) and record the role model it
implies. Mark inferred values `ASSUMPTION:`.

---

## F. Delivery, Cutover & Environments

**12. Cutover strategy?**  ⚠️ **LOAD-BEARING**

**Answer:** ⬜ **LOAD-BEARING — FILL PER APP.** One of **big-bang** / **strangler fig**
(needs a routing facade; phases sliced by route/feature) / **parallel run** (needs a
reconciliation harness). This is architecture-defining, not a rollout detail — it changes how
the plan slices phases.

**13. Deployment target, deployable units, and runtime topology?**

**Answer:** *(house standard)*

- **Target:** **Kubernetes.**
- **Deployable units: separate artifacts — two independently deployed Helm charts.**
  - *Frontend chart:* the built Angular bundle served by **nginx** in its own container.
  - *Backend chart:* the Java API process.
  - Each has its own image, values file, probes, and release lifecycle.
- **Runtime topology: same origin.** A **single ingress host** fronts both services:
  - `/api/*` → backend service
  - everything else → frontend service
  - The frontend calls the backend at a **relative path** (`/api/...`). There is **no API base
    URL configuration key and no CORS policy** — same-origin removes the need for both, and no
    later stage should add them "just in case".
  - The `/api` prefix is **fixed and identical** in the local dev proxy and in the ingress, so
    neither side configures it.
  - **SPA deep-link fallback** is handled by the **frontend chart's nginx config** (not the
    backend), so a refresh on a nested route serves `index.html`.

  > Note for Stage 0: `deployment.units = separate-artifacts` with
  > `deployment.topology = same-origin` is a deliberate combination. `deployment.servedBy` is
  > therefore **the ingress**, not a process — record it that way rather than forcing one
  > service to serve the other's assets.

- **Local dev:** Angular dev-server **proxy** stands in for the ingress, forwarding `/api` to
  the backend. State both ports in HLD §9.
- **Config & secrets delivery:**
  - *Kerberos:* a **keytab / ticket cache supplied by the environment** as a mounted file,
    plus a `krb5.conf` path — both configuration keys, never baked into an image.
  - *Entra:* tenant ID, client ID, audience, issuer as environment variables.
  - No secret is ever committed, defaulted in source, or printed in logs.

**14. Environments & test data.**

**Answer:** ⬜ **FILL PER APP** — and answer the second half explicitly:

- Which environments exist (dev / test / staging / prod)?
- **Can a developer reach a database with representative data from a local machine, and is that
  database Kerberized?**

> Read this before answering. If every reachable MS SQL instance requires Kerberos and
> developer machines cannot obtain a ticket, that is a **blocker to report, not to work around**
> — and it surfaces in phase 1, which is exactly where Kerberos connectivity gets proven. If
> the local story is instead a container with SQL authentication while every deployed
> environment is Kerberos, say so **here**: that is a second seam, and it belongs in the intake
> rather than being discovered mid-build.

**15. CI/CD expectation?**

**Answer:** ⬜ **FILL PER APP.** **Respect existing** / **Generate** / **None yet**.

> This one gates Q19: a *CI-only* coverage bar is enforceable **only** where this answer is
> **Generate**, because only then does an agent author the pipeline. Under *respect existing*,
> agents must not author pipeline files at all. The bars in Q19 are set to *build fails*
> precisely so they hold regardless of this answer.

**16. Locations, repository layout, and conventions.**

**Answer:**

**Locations** — ⬜ **FILL PER APP** (all three, even where they coincide):

| | Path |
|---|---|
| **Legacy source** *(read-only in every stage)* | ⬜ `<path>` |
| **Documents** (`PROJECT_CONTEXT.md`, requirements/design/plan, `state.json`) | ⬜ `<path>` — keep in git; reconciliation diffs it |
| **Target code repository** | ⬜ `<path>` — state explicitly whether this is the same repo as the legacy source |

**Repository layout:** *(house standard)* **single repo** holding frontend and backend.

**Source tree roots:** *(house standard — fixed here, not by Design)*

```
<root>/
└── <app>-modernized/
    ├── frontend/     # Angular 22 app     → context.repo.frontendRoot
    └── backend/      # Java 21 service    → context.repo.backendRoot
```

Record these in `context.repo.frontendRoot` / `backendRoot`. They are **not** `null` — Stage 2
reproduces this tree in LLD §3a verbatim and every phase builds to it. No phase invents a
directory layout.

**Release model:** ⬜ **FILL PER APP / PROGRAMME.** *Shipped together* as one versioned unit,
or *released independently*?

> Two Helm charts does **not** settle this. Independent release obliges Stage 2 to design a
> versioned, backward-compatible internal API and Stage 4 to keep each part separately
> deployable; shipped-together frees both from that. Given the charts deploy separately,
> *independent* is the likely answer — but say it deliberately, because it is expensive to
> change once Stage 2 has designed against it.

**Conventions:** ⬜ **FILL PER APP** — branch naming, PR target branch, commit conventions,
required reviewers. Default if blank: feature branches per phase; PRs target the default branch.

**17. Preferred phase count or slicing strategy?**

**Answer:** *(house standard)* Planner decides — 3–7 phases, consistent with the cutover
strategy in Q12. Phase 1 proves the riskiest plumbing: **scaffold + Kerberos JDBC connectivity
+ entity mapping validated against the live schema + the auth seam with its dev stub**, behind
one or two endpoints exercised through Swagger UI.

---

## G. Quality

**18. Other sources of truth besides the code.**

**Answer:** ⬜ **FILL PER APP.** Existing automated tests (and whether they pass), written
specs, runbooks, available SMEs. Legacy tests are often the best behavioral specification
available — name them if they exist.

**19. Code style / quality gates the target must enforce?**

**Answer:** *(house standard)*

**Style:** ⬜ **CONFIRM** — backend: Google Java Style enforced by the **Spotless Maven plugin**
bound to the `verify` lifecycle (`spotless:check`, not just `spotless:apply`); frontend: Angular
style guide with ESLint + Prettier in the build. Both must **fail the build**, not merely warn.

**Coverage — two separate bars, each with all five parts. Raise them as two constraints, not
one**, so Review grades them independently:

| | **Backend** | **Frontend** |
|---|---|---|
| **Metric & threshold** | line ≥ **95%**, branch ≥ **90%** | line ≥ **95%**, branch ≥ **90%** |
| **Tool** | **JaCoCo Maven plugin**, `jacoco:check` bound to `verify` | Angular CLI karma/istanbul thresholds |
| **Scope** | **changed / new code only** | **changed / new code only** |
| **Exclusions** | generated sources, DTOs/records, configuration and bootstrap classes, Spring config, migrations, generated OpenAPI artifacts | `main.ts`, polyfills, environment files, `*.module.ts`, generated API clients, generated OpenAPI artifacts |
| **Enforcement** | **build fails below the bar** | **build fails below the bar** |
| **From when** | the backend scaffold phase onward | the first frontend phase onward |

> **Why changed-code scope.** Whole-codebase at 95% fails phase 4 because of phase 1's
> legacy-shaped ported code, and no honest action inside phase 4 can fix it.
>
> **The branch floor is deliberate.** 95% line coverage is exactly the pressure that produces
> accessor tests; branch coverage is much harder to satisfy vacuously. Review must check the
> bar was not met by vacuous tests or a widened exclusion list.
>
> **Expect the agent to stop and ask.** It may not lower the threshold, widen exclusions, or
> disable the gate to go green. At 95% that will happen — approving a specific exclusion is
> the intended outcome, not a failure of the process.

**20. Non-functional priorities — rank your top 3.**

**Answer:** *(house standard, adjust per app)* **1. Security · 2. Maintainability ·
3. Performance.**

**21. Performance baseline.**

**Answer:** ⬜ **FILL PER APP.** Measurable current behavior the target must match or beat.
If none is supplied, Stage 1 records whatever baseline is observable in the legacy app, and
Review will say plainly that it has no numeric bar.

**22. Compliance/regulatory constraints.**

**Answer:** ⬜ **FILL PER APP.** Plus any audit-trail, data-retention, or data-residency
obligations.

---

## H. User Interface

**23. Is there a UI reference for the target?**

**Answer:** ⬜ **FILL PER APP.** Give the path and say **reference** (recommended — extract a
visual language and build with Angular Material/CDK themed to match) or **literal** (reproduce
the markup as-is). Also state: responsive? dark mode? i18n/RTL?

Default if blank: no reference; Design picks idiomatic Angular defaults and records them as the
design language anyway, so screens stay consistent across phases.

> Appearance only. A UI reference never changes behavior — under strict parity (Q3), a sample
> implying a different flow is an `OPEN QUESTION:`, not a licence to redesign.

---

## I. Reference Implementations

**24. Reference implementations for the target.**

**Answer:** ⬜ **FILL PER APP / PROGRAMME** — fill the paths, or delete rows you have no sample
for. These are the areas every project otherwise rewrites badly from scratch.

| Area | Path | Mode | Governs |
|------|------|------|---------|
| Deployment (Helm) | ⬜ `<path>` | reference | Chart structure, values layout, probe/secret conventions, image build and nginx config for the frontend chart — **not** this app's names, ports, hostnames, or resource sizing |
| Auth (Entra + seam + stub) | ⬜ `<path>` | reference | Token validation chain, claim names, role mapping, the seam interface and how the stub is profile-gated — **does** dictate behavior, deliberately |
| Data access (Kerberos JDBC) | ⬜ `<path>` | reference | DataSource configuration, `krb5.conf`/keytab wiring, connection-pool settings — **not** this app's schema, entities, or queries |

> **A reference is not a requirement.** Where a sample implies behavior the requirements don't
> call for, that is an `OPEN QUESTION:`. Where it conflicts with a requirement or constraint,
> the requirement or constraint wins and the conflict is reported, never silently resolved.

---

## Project-specific questions *(appended per the template's closing note)*

**25. Cross-boundary file sharing between frontend and backend?**  ⚠️ **LOAD-BEARING**

**Answer:** *(house standard)* **No file is shared between the frontend and backend roots.**

No shared module, no common parent build, no generated-types package spanning both, no
symlink, and no relative import or build path crossing the boundary. **The API contract in
LLD §1 is the sole coupling** — each side declares its own types independently, and a DTO that
appears on both sides is written twice on purpose.

Stage 0 must raise this as a constraint with these obligations:

- *Design:* LLD §3a shows two disjoint trees with no common parent module; DTOs are specified
  once as the API contract and declared separately on each side.
- *Plan:* never schedule a "shared types" or "common module" task; a contract change is a task
  on each side of the boundary.
- *Implement:* neither build references a path outside its own root; no code generation writes
  across the boundary.
- *Review:* **any** cross-root import, symlink, or build-path reference is a **Blocker**.

**26. API documentation expectation?**

**Answer:** *(house standard)* **Code-first OpenAPI 3**, generated from the backend by
**springdoc-openapi**.

- Document served at `/v3/api-docs`; **Swagger UI at `/swagger-ui`**, enabled in non-production
  profiles only (path and gating are configuration keys in LLD §7).
- **Code-first, explicitly — not spec-first.** Spec-first would put generated clients or server
  stubs somewhere, and under Q25 a generated TypeScript client must live **entirely inside the
  frontend root** and be regenerated there. No shared codegen module, ever.

Stage 0 must raise this as a constraint with these obligations:

- *Design:* LLD §1 remains the authoritative contract; the generated document must match it —
  annotations carry summaries, request/response schemas, status codes, error shapes, and the
  authorization required per endpoint.
- *Plan:* springdoc stands up in the **backend scaffold phase, before the first endpoint**, and
  every backend phase's developer test guide drives its endpoints **through Swagger UI**. This
  is what makes backend-only early phases manually testable.
- *Implement:* an endpoint is not done until it appears in the generated document with accurate
  schemas; Swagger UI is unreachable in the production profile.
- *Review:* generated document diffed against LLD §1 — an endpoint in one and not the other is
  a finding.

**27. Which Entra app registration / service principal does this app use?**  ⚠️ **LOAD-BEARING**

**Answer:** ⬜ **LOAD-BEARING — FILL PER APP.** App registration (name + client ID), the app
roles or security groups that map to this app's roles, and the service account whose keytab the
backend uses for Kerberos. Not inferable from code, and different for every app in the set.

---

## Appendix — constraints this intake is expected to produce

A checklist for the Stage 0 hand-off, not an input to it. Most map to a documented archetype;
the last three do not, which is why they are spelled out above with their obligations.

| # | Constraint | Source |
|---|---|---|
| 1 | Strict behavioral parity | Q3 |
| 2 | Reuse existing MS SQL schema verbatim; mapping validated against the live schema | Q7 (archetype) |
| 3 | Legacy coexistence / concurrent writer | Q9 (archetype) — **only if Q9 says yes** |
| 4 | Cutover strategy and what it demands structurally | Q12 (archetype) |
| 5 | Entra ID auth behind a seam, with a profile-gated dev stub | Q11 (archetype) |
| 6 | Kerberos JDBC data access — no SQL-auth fallback, no credentials in source | Q5 + Q13 |
| 7 | Backend coverage ≥ 95% line / 90% branch, changed code, build fails | Q19 (archetype) |
| 8 | Frontend coverage ≥ 95% line / 90% branch, changed code, build fails | Q19 (archetype) |
| 9 | Style/format gates fail the build (both sides) | Q19 (archetype) |
| 10 | Design language / UI consistency across phases | Q23 (archetype — declare even with no sample) |
| 11 | One constraint **per** reference-implementation row supplied | Q24 (archetype) |
| 12 | **No shared files between frontend and backend roots** | Q25 — no archetype; obligations above |
| 13 | **Code-first OpenAPI, Swagger UI non-prod only** | Q26 — no archetype; obligations above |
| 14 | **Fixed source tree roots** (`<app>-modernized/frontend` and `/backend`) | Q16 — recorded in `context.repo.*`, not a constraint; verify Stage 0 set both non-`null` |
