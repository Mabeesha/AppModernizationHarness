# INTAKE — <App>

<!--
This is a filled intake, in the form Stage 0 consumes: copy it to your project as `INTAKE.md`
(e.g. `./out/INTAKE.md`), answer every `TODO`, and run Stage 0.

The answers already written in are settled across the whole modernization set — target stack,
database reuse, Entra auth, Kubernetes topology, coverage bars, the no-shared-files boundary,
code-first OpenAPI. Do not change them without a programme-level decision. Everything still
marked `TODO` differs per app and is not inferable from code.

Find what is left:   grep -n "TODO" INTAKE.md

Questions 4a, 11a and 11c ask the agent to extract an answer from the legacy source rather
than hard-stop; that is deliberate, and the only places this file delegates.

The question text and per-question guidance live in `0_INTAKE_TEMPLATE.md`, which Stage 0 falls
back to — this file carries the answers. The flow is one-way: INTAKE.md → Stage 0 →
`PROJECT_CONTEXT.md §5`. Stage 0 never writes back here. To change an answer later, edit this
file and rerun Stage 0.
-->

---

## A. Drivers & Scope

### 1. Why modernize, and why now?

**Answer:** TODO — the business driver and any deadline. It sets the speed-vs-thoroughness
tradeoff every later stage makes. If there is genuinely none, write: *no deadline pressure;
like-for-like modernization.*

### 2. What is explicitly out of scope?

**Answer:** TODO — any screens, modules, or reports the target need not reproduce. Write
*nothing — full parity* if there are none.

### 3a. Strict parity, or are improvements allowed?

*Tick one:*

- [x] Strict parity — reproduce current behavior exactly, including known bugs and awkward UX
- [ ] Improvements allowed — the target may fix and improve

**Answer:** Legacy bugs are reproduced and flagged as `OPEN QUESTION:`, never silently "fixed".
UI *appearance* may modernize per Q23; behavior, fields, validation and flows may not.

### 3b. Is anything specifically off-limits to change?

**Answer:** TODO — anything off-limits to change even cosmetically (e.g. a report layout the
business reconciles against). Write *nothing beyond 3a* if there is none.

---

## B. Stacks

### 4a. Current application stack?  ⚠️ LOAD-BEARING

**Answer:** Extract this from the legacy source; do not ask me for it. Inspect the legacy app
at the path given in Q16a and record languages, frameworks, UI technology, runtime versions,
data store, and notable libraries — citing the files read as evidence. Record every inferred
value as `ASSUMPTION:` (inferred), list them in the hand-off report under *"Answered without
you — confirm or override"*, and **proceed without hard-stopping**. A one-line summary is
enough; the full inventory is Stage 1's Technical document, not this question.

If the legacy source path is missing or unreadable, *then* stop and ask.

### 4b. Is there logic inside the database? Where can its definitions be read?

**Answer:** TODO — the apps share an MS SQL database, so stored procedures, triggers, and views
are likely carrying behavior. Give the path to their definitions (a schema export or DDL
scripts), or write *none supplied* to have each one the code calls flagged as `OPEN QUESTION:`.

### 5a. Target frontend?  ⚠️ LOAD-BEARING

**Answer:** **Angular 22**, built and tooled on **Node 22**. Node is a **build-time runtime
only** — no Node server process ships. The static bundle is served by nginx in its own
container (see Q13b).

### 5b. Target backend?  ⚠️ LOAD-BEARING

**Answer:** **Java 21**, built with **Maven**. Framework: TODO — Spring Boot? (5d's springdoc
answer presumes it.)

All gates are Maven plugins bound to the build lifecycle so they fail `mvn verify`, not just a
separate command: Spotless (format), JaCoCo (coverage, Q19). API documentation is
**springdoc-openapi**, code-first — see 5d.

### 5c. Target data access layer?  ⚠️ LOAD-BEARING

**Answer:**

- **JPA / Hibernate**, with **explicit hand-written entity↔table mapping**. The schema is
  inherited and not ours to redesign (Q7): every `@Table` / `@Column` name is written out to
  match the live schema exactly, never left to a naming strategy.
- **Schema generation is off** — `ddl-auto` is `validate` locally and `none` in deployed
  environments; Hibernate may never create, alter, or drop anything.
- **Existing Microsoft SQL Server**, reached over JDBC (`mssql-jdbc`). How it logs in is 10b.

### 5d. How should the target's API be described?

*Tick one:*

- [ ] None — no API description is required
- [x] Generated from the code (code-first) — name the library if you have one in mind
- [ ] Written first, and the code must match it (spec-first) — give the spec's path

**Answer:** **OpenAPI 3**, generated from the backend by **springdoc-openapi**, served at
`/v3/api-docs`. **Code-first, explicitly — not spec-first.** Spec-first would put generated
clients or server stubs somewhere, and under Q26 a generated TypeScript client must live
**entirely inside the frontend root** and be regenerated there. No shared codegen module, ever.

### 5e. Which tools should developers use to try the API by hand?

*Tick all that apply:*

- [x] Swagger UI — needs an API description (5d); say where it may run (e.g. not in production)
- [ ] A Postman (or Insomnia) collection, kept up to date with the API
- [ ] `.http` / REST-client files in the repository

**Answer:** **Swagger UI at `/swagger-ui`, non-production profiles only** — unreachable in the
production profile. Every backend phase's developer test guide drives its endpoints through it;
this is what makes backend-only early phases manually testable.

### 6a. Paid legacy components that need a replacement?

**Answer:** TODO — grid controls, report engines, charting. Write *none stated* if there are
none; paid components found during extraction are then flagged as `OPEN QUESTION:`.

### 6b. License restrictions on what the target may use?

**Answer:** TODO — write *none* if any permissively licensed package may be used.

### 6c. Where may dependencies come from?

*Tick all that apply:*

- [ ] Public registries (Maven Central, npm, NuGet, PyPI)
- [ ] Only an internal mirror/proxy — give its URL or config location (e.g. `settings.xml`, `.npmrc`)
- [ ] Only an approved list of packages — give where the list is

**Answer:** TODO — tick the source for Maven and the source for npm, and say which is which if
they differ. This is set once for the whole modernization set.

### 6d. Does the build environment have internet access?

*Tick one:*

- [ ] Yes
- [ ] No

**Answer:** TODO

---

## C. Data & Coexistence

### 7. Reuse the existing database, or create a new schema?  ⚠️ LOAD-BEARING

*Tick one:*

- [x] Reuse the existing database as-is
- [ ] New schema

**Answer:** No schema redesign, no new schema, no table or column renaming. The data model is
captured **verbatim** — exact table, column, and constraint names — and the mapping is
validated against the live schema in the phase that first touches persistence.

**How that validation is mechanized:** Hibernate's `ddl-auto: validate` against a real instance
of the schema. That makes "the entity mapping validates against the live schema" a falsifiable
phase exit criterion rather than a self-assessment — the application context fails to start on
any mismatch. It depends on Q14b having a reachable database; if none exists, say so there.

### 8a. What data moves to the new schema?

**Answer:** Nothing moves. The database is reused (Q7), so the target connects as-is. No data
migration, transformation, or back-fill. *(8b–8f do not apply.)*

### 9. While the target is live — including any period when old and new run side by side — will the legacy application also write to the same data store?  ⚠️ LOAD-BEARING

*Tick one:*

- [ ] No — the legacy app stops writing before the target goes live (typical of big-bang)
- [ ] Yes, during a side-by-side period — say how long (typical of strangler fig and parallel run)
- [ ] Yes, indefinitely

**Answer:** TODO — tick one.

> Read this before answering. A concurrent legacy **writer** is a far stronger constraint than
> merely inheriting a schema: no schema evolution at all, shared identity/sequence ranges,
> explicit transaction-isolation and locking expectations, and both systems must tolerate each
> other's writes. Across a set of apps modernized one at a time against a shared database,
> "yes, indefinitely" is the likely answer — and it is the single most expensive fact in this
> file to get wrong. Nothing in the code can tell the agent this.
>
> **If yes, it constrains JPA specifically:** Hibernate's second-level cache and
> query cache must be **off** (another writer invalidates them without our knowing), optimistic
> locking via `@Version` needs a column the legacy writer also maintains — or it can't be used
> at all — and identity generation must not assume our process owns the sequence. Say so here;
> the constraint's *Design* obligation is where those rules get written down.

---

## D. Integrations

### 10a. External systems the target must keep working with.

| System | Contract: fixed or negotiable? | Preserve, replace, or retire? | Contract file |
|--------|--------------------------------|-------------------------------|---------------|
| TODO   |                                |                               |               |

**Answer:** TODO — one row per system (queues, file drops, SMTP, internal APIs, schedulers,
reporting/BI). Write *none known* to have them discovered during requirements extraction and
assumed preserved with a fixed contract.

### 10b. Which account does the app use for each connection, and who calls it?

| Connection | Direction (out / in) | How it authenticates in the target | Account or identity name | Notes (permissions it needs, per-environment differences) |
|------------|----------------------|------------------------------------|--------------------------|-----------------------------------------------------------|
| MS SQL Server (the app's database) | out | Kerberos, integrated (`authenticationScheme=JavaKerberos`) | TODO — the service account whose keytab the backend uses | read/write on the app's tables; no DDL (Q5c: schema generation is off) |
| Microsoft Entra ID | out | token validation against the tenant's published signing keys | the app registration in 11f | no client secret |
| TODO — any other system from 10a, or any system that calls the target | | | | |

**Answer:** **No SQL logins, and no password ever in a connection string** — Kerberos is the
only way the backend reaches the database, in every deployed environment. TODO — the service
account per app; not inferable from code, and different for every app in the set.

---

## E. Sign-in and Permissions (Authentication and Authorization)

### 11a. How do users log in today?  ⚠️ LOAD-BEARING

**Answer:** Extract how the legacy app authenticates today (Windows/AD integrated, forms auth
against a table, etc.). Mark inferred values `ASSUMPTION:` and list them for confirmation; do
not hard-stop. TODO — confirm or override once extracted.

### 11b. How should the target handle login?  ⚠️ LOAD-BEARING

*Tick one:*

- [ ] Keep the real identity provider (AD/SSO/…) — name it
- [ ] Build an auth seam + dev stub, with the real identity provider deferred
- [x] Other — describe

**Answer:** **Microsoft Entra ID**, behind an auth seam with a dev stub — the real provider is
built now, not deferred. OIDC/OAuth2. The backend is a **resource server validating JWT bearer
tokens**; the frontend acquires tokens via **MSAL**. Tenant ID, client ID, audience and issuer
are **configuration keys**, never compiled in. **No client secret in the repository.**

**The seam has two implementations:**

1. **Entra provider** — the real one. Validates signature, issuer, audience and expiry against
   the tenant's published signing keys.
2. **Dev stub** — selected by a **local-only profile**, issuing a fixed set of test principals
   with configurable roles and bypassing Entra entirely. It exists so local testing and the
   `FEATURE_STATUS.md` checks need no Entra account. **It must be structurally incapable of
   activating under the production profile** — not merely switched off by a default value.

### 11c. Where are roles and permissions defined today?

*Tick all that apply:*

- [ ] Hard-coded checks in the source
- [ ] Tables in the database
- [ ] Directory groups (AD/LDAP)
- [ ] Claims from the identity provider

**Answer:** Extract this from the legacy source and record the role model it implies. Mark
inferred values `ASSUMPTION:` and list them for confirmation; do not hard-stop. TODO — confirm
or override once extracted.

### 11d. Reproduce the role model exactly, or may it be consolidated?

*Tick one:*

- [x] Exactly — no roles merged or renamed
- [ ] May be consolidated

**Answer:** Roles are mapped from Entra **app roles / group claims**. Capture the legacy role
model in portable terms (role → group/claim) during requirements extraction, independent of
either provider.

### 11e. Are there permission rules finer than a role?

**Answer:** TODO — any row-level or ownership checks, field-level hiding, or approval limits,
and where the legacy app enforces them (code, a permissions table, stored procedures). Write
*none known* to have extraction inventory every permission check it finds.

### 11f. Which group, app role, or claim grants each role in the target?

| Legacy role | Target group / app role / claim | Notes |
|-------------|---------------------------------|-------|
| TODO        |                                 |       |

**Answer:** TODO — the Entra app registration (name + client ID) and the app roles or security
groups that map to each of this app's roles. Not inferable from code, and different for every
app in the set.

### 11g. How does a developer sign in as each role to test?

*Tick one:*

- [x] Dev stub users — one per role, local only
- [ ] Named test accounts in the real identity provider — list the account names, never passwords
- [ ] Not available — say why

**Answer:** The dev stub's fixed test principals (11b), one per role, under the local-only
profile. No Entra account is needed to test locally.

---

## F. Delivery, Cutover & Environments

### 12a. How will the target go live?  ⚠️ LOAD-BEARING

*Tick one:*

- [ ] Big-bang — build the replacement, switch over at once
- [ ] Strangler fig — legacy and target run side by side, traffic moved over bit by bit
- [ ] Parallel run — both live, outputs compared before the switch

**Answer:** TODO — tick one. This is architecture-defining, not a rollout detail — it changes
how the plan slices phases.

### 12b. If the target fails after go-live, must traffic be able to return to the legacy app?

*Tick one:*

- [ ] Yes — rollback must stay possible
- [ ] No — fix forward

**Answer:** TODO — tick one.

> With the schema already frozen by Q7, rollback costs little here: the target cannot evolve
> the schema anyway. What it still forbids is writing values the legacy app cannot read — new
> status codes, longer strings in a column the legacy code truncates, and similar.

### 12c. If yes — for how long after go-live must rollback stay possible?

**Answer:** TODO — only if 12b is yes.

### 13a. Where will the target be deployed?

*Tick the most specific one that fits:*

- [ ] On-prem VM
- [ ] Container
- [x] Kubernetes
- [ ] A specific cloud service — name it
- [ ] Serverless
- [ ] App server — name it

**Answer:**

### 13b. How many deployable units ship?

*Tick one:*

- [ ] One artifact holding both parts (e.g. the backend serves the built frontend bundle)
- [x] Two artifacts deployed separately (e.g. an API process plus a static bundle on a web server/CDN)

**Answer:** Two independently deployed Helm charts.

- *Frontend chart:* the built Angular bundle served by **nginx** in its own container.
- *Backend chart:* the Java API process.
- Each has its own image, values file, probes, and release lifecycle.

### 13c. Are the parts shipped together, or released independently?

*Tick one:*

- [ ] Shipped together as one versioned release
- [ ] Released independently, each on its own cadence

**Answer:** TODO — tick one.

> Two Helm charts does **not** settle this. Independent release obliges Stage 2 to design a
> versioned, backward-compatible internal API and Stage 4 to keep each part separately
> deployable; shipped-together frees both from that. Given the charts deploy separately,
> *independent* is the likely answer — but say it deliberately, because it is expensive to
> change once Stage 2 has designed against it.

### 13d. Once deployed, how does the frontend reach the backend?

*Tick one:*

- [x] Same origin — one host/port; the backend or a fronting web server serves both
- [ ] Separate origins — different hosts/ports

**Answer:** A **single ingress host** fronts both services:

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

### 13e. How is it arranged for local development, where that differs?

**Answer:** Angular dev-server **proxy** stands in for the ingress, forwarding `/api` to the
backend. State both ports in HLD §9.

### 13f. How do configuration and secrets reach the app in each environment?

**Answer:**

- *Kerberos:* a **keytab / ticket cache supplied by the environment** as a mounted file, plus a
  `krb5.conf` path — both configuration keys, never baked into an image.
- *Entra:* tenant ID, client ID, audience, issuer as environment variables.
- No secret is ever committed, defaulted in source, or printed in logs.

### 14a. Which environments exist?

*Tick all that apply:*

- [ ] Dev
- [ ] Test
- [ ] Staging
- [ ] Prod

**Answer:** TODO — tick all that exist.

### 14b. Can a developer reach a database with representative data?

**Answer:** TODO — from a local machine? And is that database Kerberized?

> Read this before answering. If every reachable MS SQL instance requires Kerberos and
> developer machines cannot obtain a ticket, that is a **blocker to report, not to work around**
> — and it surfaces in phase 1, which is exactly where Kerberos connectivity gets proven. If
> the local story is instead a container with SQL authentication while every deployed
> environment is Kerberos, say so **here**: that is a second seam, and it belongs in the intake
> rather than being discovered mid-build.

### 15. CI/CD expectation?

*Tick one:*

- [ ] Respect existing — the build slots into a pipeline that already exists; agents don't author pipeline files
- [ ] Generate — a phase wires up pipeline files
- [ ] None — local build/test only

**Answer:** TODO — tick one.

> This one gates Q19g: a *CI-only* coverage bar is enforceable **only** where this answer is
> **Generate**, because only then does an agent author the pipeline. Under *respect existing*,
> agents must not author pipeline files at all. The bars in Q19 are set to *build fails*
> precisely so they hold regardless of this answer.

### 16a. Where is the legacy source?

**Answer:** TODO `<path>` — read-only in every stage.

### 16b. Where are the documents written?

**Answer:** TODO `<path>` — keep in git; reconciliation diffs it.

### 16c. Where is the target code repository?

**Answer:** TODO `<path>`

### 16d. Is the target code repository the same repo that holds the legacy source?

*Tick one:*

- [ ] Yes — the new tree is added alongside the frozen legacy one
- [ ] No

**Answer:** TODO — tick one.

### 16e. Do frontend and backend live in one repo or separate repos?

*Tick one:*

- [x] One repo
- [ ] Separate repos — give both paths and say which holds which

**Answer:**

### 16f. Root directory of each part?

**Answer:** Fixed here, not by Design:

```
<root>/
└── <app>-modernized/
    ├── frontend/     # Angular 22 app     → context.repo.frontendRoot
    └── backend/      # Java 21 service    → context.repo.backendRoot
```

Record these in `context.repo.frontendRoot` / `backendRoot`. They are **not** `null` — Stage 2
reproduces this tree in LLD §3a verbatim and every phase builds to it. No phase invents a
directory layout.

### 16g. Branch naming?

**Answer:** TODO — write *default* for one feature branch per phase.

### 16h. Which branch do PRs target?

**Answer:** TODO — write *default* for the default branch.

### 16i. Commit message conventions?

**Answer:** TODO

### 16j. Required reviewers?

**Answer:** TODO

### 17. Phase sizing / slicing strategy.

**Answer:** Default sizing — one coherent theme per phase, walkable in one sitting, roughly
even, no fixed count, consistent with the cutover strategy in Q12a. Phase 1 proves the riskiest
plumbing: **scaffold + Kerberos JDBC connectivity + entity mapping validated against the live
schema + the auth seam with its dev stub**, behind one or two endpoints exercised through
Swagger UI.

---

## G. Quality

### 18a. Are there existing automated tests? Do they pass?

**Answer:** TODO — legacy tests are often the best behavioral specification available; name
them if they exist. Write *none* for code-only extraction.

### 18b. Written specs, API descriptions, or saved requests for the legacy app?

| Kind | Path | What it covers | Trust: authoritative or hint |
|------|------|----------------|------------------------------|
| TODO |      |                |                              |

**Answer:** TODO — specs, runbooks, manuals, any API description or Postman collection of the
legacy app. Remove passwords and tokens from collections first. Write *none* for code-only
extraction.

### 18c. Subject-matter experts available?

**Answer:** TODO

### 18d. Can the legacy app be built and run somewhere a developer can reach?

*Tick one:*

- [ ] Yes — say where
- [ ] No

**Answer:** TODO — tick one.

### 18e. Is the legacy source complete?

*Tick one:*

- [ ] Yes
- [ ] No — say what is missing

**Answer:** TODO — tick one; tick *Yes* if unsure.

### 19a. Code style guide?

**Answer:** Backend — Google Java Style. Frontend — Angular style guide. TODO — confirm, or
name a different style guide.

### 19b. How is the style enforced?

**Answer:** Backend — the **Spotless Maven plugin** bound to the `verify` lifecycle
(`spotless:check`, not just `spotless:apply`). Frontend — ESLint + Prettier in the build. Both
must **fail the build**, not merely warn.

### 19c. Do you want a unit test coverage bar?

*Tick one:*

- [x] Yes — answer 19d–19h
- [ ] No

**Answer:** **Two separate bars, backend and frontend. Raise them as two constraints, not
one**, so Review grades them independently.

### 19d. Coverage — metric and threshold?

**Answer:** Both bars: line ≥ **95%**, branch ≥ **90%**.

- *Backend tool:* **JaCoCo Maven plugin**, `jacoco:check` bound to `verify`.
- *Frontend tool:* Angular CLI karma/istanbul thresholds.

> **The branch floor is deliberate.** 95% line coverage is exactly the pressure that produces
> accessor tests; branch coverage is much harder to satisfy vacuously. Review must check the
> bar was not met by vacuous tests or a widened exclusion list.

### 19e. Coverage — scope?

*Tick one:*

- [ ] Whole codebase
- [x] Changed/new code only

**Answer:** Both bars.

> **Why changed-code scope.** Whole-codebase at 95% fails phase 4 because of phase 1's
> legacy-shaped ported code, and no honest action inside phase 4 can fix it.

### 19f. Coverage — exclusions?

**Answer:**

- *Backend:* generated sources, DTOs/records, configuration and bootstrap classes, Spring
  config, migrations, generated OpenAPI artifacts.
- *Frontend:* `main.ts`, polyfills, environment files, `*.module.ts`, generated API clients,
  generated OpenAPI artifacts.

### 19g. Coverage — enforcement?

*Tick one:*

- [x] Build fails below the bar
- [ ] CI-only
- [ ] Advisory report

**Answer:** Both bars.

> **Expect the agent to stop and ask.** It may not lower the threshold, widen exclusions, or
> disable the gate to go green. At 95% that will happen — approving a specific exclusion is the
> intended outcome, not a failure of the process.

### 19h. Coverage — from when?

*Tick one:*

- [x] From the scaffold phase onward (recommended — retrofitting coverage across finished phases costs far more)
- [ ] From a named phase — name it

**Answer:** Backend — from the backend scaffold phase onward. Frontend — from the first
frontend phase onward.

### 20a. Non-functional priorities — rank your top 3.

**Answer:** **1. Security · 2. Maintainability · 3. Performance.** TODO — adjust if this app
ranks differently.

### 20b. Is an accessibility standard required? Which one and what level?

**Answer:** TODO — name one (e.g. WCAG 2.1 AA) if policy requires it, or write *none stated*.

### 21. Performance baseline.

**Answer:** TODO — measurable current behavior the target must match or beat. Write *none
supplied* to have Stage 1 record whatever baseline is observable in the legacy app; Review will
then say plainly that it has no numeric bar.

### 22a. Compliance or regulatory constraints?

**Answer:** TODO — write *none stated* if there are none.

### 22b. Audit-trail obligations?

**Answer:** TODO

### 22c. Data-retention obligations?

**Answer:** TODO

### 22d. Data-residency obligations?

**Answer:** TODO

---

## H. User Interface

### 23a. Is there a UI reference for the target? Give its path.

**Answer:** TODO `<path>` — or write *no reference* to have Design pick idiomatic Angular
defaults and record them as the design language anyway, so screens stay consistent across
phases.

> Appearance only. A UI reference never changes behavior — under strict parity (Q3a), a sample
> implying a different flow is an `OPEN QUESTION:`, not a licence to redesign.

### 23b. How should the UI reference be used?

*Tick one:*

- [ ] Reference — extract a visual language, build with the target stack's own components themed to match
- [ ] Literal — reproduce the sample's markup and CSS as-is

**Answer:** TODO — *reference* is recommended: build with Angular Material/CDK themed to match.

### 23c. Must the UI be responsive?

*Tick one:*

- [ ] Yes
- [ ] No

**Answer:** TODO

### 23d. Is dark mode required?

*Tick one:*

- [ ] Yes
- [ ] No

**Answer:** TODO

### 23e. Any i18n or right-to-left (RTL) language need?

**Answer:** TODO

### 23f. Which browsers and devices must be supported?

**Answer:** TODO — and is any user still on a browser older than Angular 22 supports?

---

## I. Reference Implementations

### 24. Reference implementations — example code the build should follow for a given area.

| Area | Path | Mode | Governs |
|------|------|------|---------|
| Deployment (Helm) | TODO `<path>` | reference | Chart structure, values layout, probe/secret conventions, image build and nginx config for the frontend chart — **not** this app's names, ports, hostnames, or resource sizing |
| Auth (Entra + seam + stub) | TODO `<path>` | reference | Token validation chain, claim names, role mapping, the seam interface and how the stub is profile-gated — **does** dictate behavior, deliberately |
| Data access (Kerberos JDBC) | TODO `<path>` | reference | DataSource configuration, `krb5.conf`/keytab wiring, connection-pool settings — **not** this app's schema, entities, or queries |

**Answer:** TODO — fill the paths, or delete rows you have no sample for. These are the areas
every project otherwise rewrites badly from scratch.

> **A reference is not a requirement.** Where a sample implies behavior the requirements don't
> call for, that is an `OPEN QUESTION:`. Where it conflicts with a requirement or constraint,
> the requirement or constraint wins and the conflict is reported, never silently resolved.

---

## J. Ownership

### 25a. Who answers business-rule questions?

**Answer:** TODO — the product owner or SME for open questions about rules and legacy bugs.

### 25b. Who answers technical questions?

**Answer:** TODO — the tech lead for design choices and coverage exclusions.

### 25c. Who signs off a finished phase before the next one starts?

**Answer:** TODO

### 25d. How quickly are open questions usually answered?

**Answer:** TODO

---

## Project-specific questions *(appended per the template's closing note)*

### 26. Cross-boundary file sharing between frontend and backend?  ⚠️ LOAD-BEARING

**Answer:** **No file is shared between the frontend and backend roots.**

No shared module, no common parent build, no generated-types package spanning both, no symlink,
and no relative import or build path crossing the boundary. **The API contract in LLD §1 is the
sole coupling** — each side declares its own types independently, and a DTO that appears on both
sides is written twice on purpose.

Stage 0 must raise this as a constraint with these obligations:

- *Design:* LLD §3a shows two disjoint trees with no common parent module; DTOs are specified
  once as the API contract and declared separately on each side.
- *Plan:* never schedule a "shared types" or "common module" task; a contract change is a task
  on each side of the boundary.
- *Implement:* neither build references a path outside its own root; no code generation writes
  across the boundary.
- *Review:* **any** cross-root import, symlink, or build-path reference is a **Blocker**.

---

## Appendix — constraints this intake is expected to produce

A checklist for the Stage 0 hand-off, not an input to it. Most map to a documented archetype;
rows 12 and 14 do not — row 12 is spelled out above with its obligations.

| # | Constraint | Source |
|---|---|---|
| 1 | Strict behavioral parity | Q3a |
| 2 | Reuse existing MS SQL schema verbatim; mapping validated against the live schema | Q7 (archetype) |
| 3 | Legacy coexistence / concurrent writer | Q9 (archetype) — **only if Q9 says Yes** |
| 4 | Cutover strategy and what it demands structurally | Q12a (archetype) |
| 5 | Entra ID auth behind a seam, with a profile-gated dev stub | Q11b + Q11f–g (archetype) |
| 6 | Kerberos JDBC data access — no SQL-auth fallback, no credentials in source | Q10b + Q13f (archetype: connection identities) |
| 7 | Backend coverage ≥ 95% line / 90% branch, changed code, build fails | Q19 (archetype) |
| 8 | Frontend coverage ≥ 95% line / 90% branch, changed code, build fails | Q19 (archetype) |
| 9 | Style/format gates fail the build (both sides) | Q19a–b (archetype) |
| 10 | Design language / UI consistency across phases | Q23 (archetype — declare even with no sample) |
| 11 | One constraint **per** reference-implementation row supplied | Q24 (archetype) |
| 12 | **No shared files between frontend and backend roots** | Q26 — no archetype; obligations above |
| 13 | **Code-first OpenAPI, Swagger UI non-prod only** | Q5d–e (archetype) |
| 14 | **Fixed source tree roots** (`<app>-modernized/frontend` and `/backend`) | Q16f — recorded in `context.repo.*`, not a constraint; verify Stage 0 set both non-`null` |
| 15 | Rollback — no value the legacy app cannot read | Q12b (archetype) — **only if rollback is required** |
| 16 | Dependencies resolved only from the internal mirror | Q6c–d (archetype) — **only if Q6c restricts package sources** |
