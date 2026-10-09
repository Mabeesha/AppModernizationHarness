
# INTAKE — <app_name>

<!--
A filled intake for a single app replaced in one big-bang cutover, in the form Stage 0
consumes: copy it to your project as `INTAKE.md` (e.g. `./out/INTAKE.md`), replace
`<legacy_repo>` and `<app_name>`, answer every `TODO`, and run Stage 0.

Settled here: Angular 22 / Node frontend, Java 21 / Maven / JPA backend, the reused database
(to confirm, Q7) reached with SQL authentication, Entra ID sign-in behind a seam with a local dev stub,
authorization kept in the database as the legacy app does it, code-first OpenAPI with Swagger
UI, Dockerfiles and Helm charts for separate frontend and backend deployments on OpenShift
(written, but never built, installed or run by the pipeline), no CI/CD, and a 95% coverage gate
that binds only in a final coverage phase.

Find what is left:   grep -n "TODO" INTAKE.md

Every fact about the legacy app (4a, 4b, 11a, 11c, 11e, 18a, 18e) is extracted from its source
rather than answered here. That is deliberate: those answers are marked `ASSUMPTION:` and
listed for confirmation instead of hard-stopping.

Questions this file leaves out, or leaves with an empty Answer, are blank: they take the
template's default, and Stage 0 reports every default it applied. That includes the git
conventions (16g–16j).
-->

---

## A. Drivers & Scope

### 1. Why modernize, and why now?

**Answer:** Replace the legacy application with a modern Angular + Java stack, built in full and
switched over at once. TODO — any deadline or business driver.

### 2. What is explicitly out of scope?

**Answer:** CI/CD pipelines (Q15). Building images from, installing, or running the Dockerfiles
and Helm charts on any cluster — they are written, not exercised (Q13a). TODO — anything else.

### 3a. Strict parity, or are improvements allowed?

*Tick one:*

- [ ] Strict parity — reproduce current behavior exactly, including known bugs and awkward UX
- [ ] Improvements allowed — the target may fix and improve

**Answer:** TODO — tick one. Blank means strict parity (the default).

### 3b. Is anything specifically off-limits to change?

**Answer:**

---

## B. Stacks

### 4a. Current application stack?  ⚠️ LOAD-BEARING

**Answer:** Extract from the legacy source — languages, frameworks, UI technology, runtime
versions and data store. Mark inferred values `ASSUMPTION:` and list them for confirmation; do
not hard-stop.

### 4b. Is there logic inside the database? Where can its definitions be read?

**Answer:** Extract from the legacy source every stored procedure, trigger, view or job the code
calls. TODO — the path to a schema export or DDL scripts, if one exists; without one, each piece
of database logic found is raised as an `OPEN QUESTION:`.

### 5a. Target frontend?  ⚠️ LOAD-BEARING

**Answer:** **Angular 22**, built on **Node**. TODO — the Node version, and whether Node is
only the build tool or also runs in the frontend container to serve the built app (otherwise a
plain web server such as nginx serves it).

### 5b. Target backend?  ⚠️ LOAD-BEARING

**Answer:** **Java 21**, built with **Maven**. TODO — confirm Spring Boot as the framework
(5d's springdoc answer presumes it).

### 5c. Target data access layer?  ⚠️ LOAD-BEARING

**Answer:** **JPA** wherever possible, with entity↔table mapping written out to match the
reused schema exactly (Q7); schema generation off. Where JPA cannot express a call — a stored
procedure, say (Q4b) — use the framework's plain SQL support and record why in the design.

### 5d. How should the target's API be described?

*Tick one:*

- [ ] None — no API description is required
- [x] Generated from the code (code-first) — name the library if you have one in mind
- [ ] Written first, and the code must match it (spec-first) — give the spec's path

**Answer:** OpenAPI 3, generated from the backend by **springdoc-openapi**.

### 5e. Which tools should developers use to try the API by hand?

*Tick all that apply:*

- [x] Swagger UI — needs an API description (5d); say where it may run (e.g. not in production)
- [ ] A Postman (or Insomnia) collection, kept up to date with the API
- [ ] `.http` / REST-client files in the repository

**Answer:** Swagger UI, enabled locally and in non-production environments only — unreachable
in production.

### 6a. Paid legacy components that need a replacement?

**Answer:** TODO — or *none stated*; paid components found during extraction are then raised as
`OPEN QUESTION:`.

### 6b. License restrictions on what the target may use?

**Answer:**

### 6c. Where may dependencies come from?

*Tick all that apply:*

- [ ] Public registries (Maven Central, npm, NuGet, PyPI)
- [ ] Only an internal mirror/proxy — give its URL or config location (e.g. `settings.xml`, `.npmrc`)
- [ ] Only an approved list of packages — give where the list is

**Answer:** TODO — tick one.

### 6d. Does the build environment have internet access?

*Tick one:*

- [ ] Yes
- [ ] No

**Answer:** TODO — tick one.

---

## C. Data & Coexistence

### 7. Reuse the existing database, or create a new schema?  ⚠️ LOAD-BEARING

*Tick one:*

- [x] Reuse the existing database as-is
- [ ] New schema

**Answer:** The target connects to the legacy database as-is, and authorization stays in it
(Q11c). TODO — confirm: this is inferred from "authorization is database-based, as the legacy
app does it" and "database access uses SQL authentication".

### 8a. What data moves to the new schema?

**Answer:** Nothing — the target connects as-is.

### 9. While the target is live — including any period when old and new run side by side — will the legacy application also write to the same data store?  ⚠️ LOAD-BEARING

*Tick one:*

- [x] No — the legacy app stops writing before the target goes live (typical of big-bang)
- [ ] Yes, during a side-by-side period — say how long (typical of strangler fig and parallel run)
- [ ] Yes, indefinitely

**Answer:** The legacy app is switched off at cutover.

---

## D. Integrations

### 10a. External systems the target must keep working with.

| System | Contract: fixed or negotiable? | Preserve, replace, or retire? | Contract file |
|--------|--------------------------------|-------------------------------|---------------|
| TODO   |                                |                               |               |

**Answer:** TODO — one row per system, or *none known* to have them discovered during
extraction.

### 10b. Which account does the app use for each connection, and who calls it?

| Connection | Direction (out / in) | How it authenticates in the target | Account or identity name | Notes (permissions it needs, per-environment differences) |
|------------|----------------------|------------------------------------|--------------------------|-----------------------------------------------------------|
| The app's database | out | **SQL authentication** (database login and password) | TODO — the SQL login per environment | Read/write on the app's tables; no schema changes. Password from a secret (13f) |
| Microsoft Entra ID | out | Token validation against the tenant's signing keys | The app registration (11b) | No client secret needed for validation |

**Answer:** SQL authentication is the only way the backend reaches the database. The password
is never in source, config files, or logs (13f). Users calling the backend with their Entra
token are covered by section E, not this table. TODO — add a row for any other system that
calls the backend or that it calls.

---

## E. Sign-in and Permissions (Authentication and Authorization)

### 11a. How do users log in today?  ⚠️ LOAD-BEARING

**Answer:** Extract from the legacy source. Mark inferred values `ASSUMPTION:` and list them for
confirmation; do not hard-stop.

### 11b. How should the target handle login?  ⚠️ LOAD-BEARING

*Tick one:*

- [ ] Keep the real identity provider (AD/SSO/…) — name it
- [ ] Build an auth seam + dev stub, with the real identity provider deferred
- [x] Other — describe

**Answer:** **Microsoft Entra ID**, built now — not deferred — behind an auth seam with **two
implementations**:

1. **Entra** — the real one. OIDC; the frontend signs in with MSAL, and the backend validates
   the bearer token. Tenant ID, client ID, audience and issuer are configuration keys.
2. **Dev stub** — for local testing without an Entra account. Selected only by a local
   profile, and unable to activate in any deployed environment.

Entra proves **who** the user is. **What** they may do still comes from the database (11c).
TODO — the app registration (name + client ID), and which token claim (e.g. UPN, email, object
ID) matches the user's record in the legacy database.

### 11c. Where are roles and permissions defined today?

*Tick all that apply:*

- [ ] Hard-coded checks in the source
- [x] Tables in the database
- [ ] Directory groups (AD/LDAP)
- [ ] Claims from the identity provider

**Answer:** In database tables, and the target keeps it that way: after sign-in, the user's roles
and permissions are read from the same tables the legacy app uses. Extract the exact tables and
checks from the legacy source; tick any other source found.

### 11d. Reproduce the role model exactly, or may it be consolidated?

*Tick one:*

- [ ] Exactly — no roles merged or renamed
- [ ] May be consolidated

**Answer:** TODO — tick one. Blank means exactly (the default).

### 11e. Are there permission rules finer than a role?

**Answer:** Extract from the legacy source — every row-level, ownership or field-level check,
and where it is enforced. TODO — confirm once extracted.

### 11f. Which group, app role, or claim grants each role in the target?

| Legacy role | Target group / app role / claim | Notes |
|-------------|---------------------------------|-------|
| All roles   | None — roles come from the database | Entra supplies identity only |

**Answer:** No Entra group or app role grants any role. Roles are looked up in the database for
the signed-in user (11c).

### 11g. How does a developer sign in as each role to test?

*Tick one:*

- [x] Dev stub users — one per role, local only
- [ ] Named test accounts in the real identity provider — list the account names, never passwords
- [ ] Not available — say why

**Answer:** The dev stub signs in as test users who exist in the developer's database, so their
roles load from the database the same way real users' do.

---

## F. Delivery, Cutover & Environments

### 12a. How will the target go live?  ⚠️ LOAD-BEARING

*Tick one:*

- [x] Big-bang — build the replacement, switch over at once
- [ ] Strangler fig — legacy and target run side by side, traffic moved over bit by bit
- [ ] Parallel run — both live, outputs compared before the switch

**Answer:** Build the whole app, then replace the legacy one.

### 13a. Where will the target be deployed?

*Tick the most specific one that fits:*

- [ ] On-prem VM
- [ ] Container
- [x] Kubernetes
- [ ] A specific cloud service — name it
- [ ] Serverless
- [ ] App server — name it

**Answer:** **Red Hat OpenShift**, in a colocation data center. The build writes a
**Dockerfile** and a **Helm chart** for each deployment (13b), in the phase that scaffolds that
part. They are **not run**: no phase builds the images, installs the charts, or deploys to a
cluster — the developer does that. The only exit check: each Dockerfile exists at its path
(16f) and defines its part's image; each chart exists and contains the deployment, service,
route, and the configuration and secret wiring that 13f describes.

### 13b. How many deployable units ship?

*Tick one:*

- [ ] One artifact holding both parts (e.g. the backend serves the built frontend bundle)
- [x] Two artifacts deployed separately (e.g. an API process plus a static bundle on a web server/CDN)

**Answer:** A frontend deployment (the built Angular app, served as 5a says) and a backend
deployment (the Java service) — each with its own image and Helm chart.

### 13d. Once deployed, how does the frontend reach the backend?

*Tick one:*

- [ ] Same origin — one host/port; the backend or a fronting web server serves both
- [ ] Separate origins — different hosts/ports

**Answer:** TODO — tick one. Do not leave it blank: the default (same origin, frontend served
by the backend) contradicts 13b. *Same origin* — one OpenShift route, with the frontend's web
server forwarding `/api` to the backend — avoids CORS. *Separate origins* — a route each —
needs CORS and a configurable API base URL.

### 13f. How do configuration and secrets reach the app in each environment?

**Answer:** TODO — confirm. Suggested: OpenShift **ConfigMaps** and **Secrets**, supplied as
environment variables through the Helm values. The SQL password and any Entra settings that are
sensitive live in a Secret; nothing secret is committed, defaulted in source, or logged.

### 14a. Which environments exist?

*Tick all that apply:*

- [ ] Dev
- [ ] Test
- [ ] Staging
- [ ] Prod

**Answer:** TODO — tick all that exist.

### 14b. Can a developer reach a database with representative data?

**Answer:** TODO — where, and how. It must hold the authorization tables and the dev stub's test
users (11g).

### 15. CI/CD expectation?

*Tick one:*

- [ ] Respect existing — the build slots into a pipeline that already exists; agents don't author pipeline files
- [ ] Generate — a phase wires up pipeline files
- [x] None — local build/test only

**Answer:** No pipeline files. The Dockerfiles and Helm charts (13a) are deployment files, not a
pipeline.

### 16a. Where is the legacy source?

**Answer:** `<legacy_repo>` — read-only.

### 16b. Where are the documents written?

**Answer:** TODO — e.g. `<legacy_repo>/<app_name>-modernized/docs`.

### 16c. Where is the target code repository?

**Answer:** `<legacy_repo>` — the new code lives in `<app_name>-modernized/` inside it.

### 16d. Is the target code repository the same repo that holds the legacy source?

*Tick one:*

- [x] Yes — the new tree is added alongside the frozen legacy one
- [ ] No

**Answer:**

### 16e. Do frontend and backend live in one repo or separate repos?

*Tick one:*

- [x] One repo
- [ ] Separate repos — give both paths and say which holds which

**Answer:**

### 16f. Root directory of each part?

**Answer:**

- Frontend: `<app_name>-modernized/<app_name>-ui`
- Backend: `<app_name>-modernized/<app_name>-svcs`

Each part's Dockerfile and Helm chart live inside its own root.

---

## G. Quality

### 18a. Are there existing automated tests? Do they pass?

**Answer:** Extract from the legacy source — name any tests found and whether they pass.

### 18d. Can the legacy app be built and run somewhere a developer can reach?

*Tick one:*

- [ ] Yes — say where
- [ ] No

**Answer:** TODO — tick one.

### 18e. Is the legacy source complete?

*Tick one:*

- [ ] Yes
- [ ] No — say what is missing

**Answer:** Extract — flag missing modules, binary-only dependencies, or configuration held
outside the repository as `OPEN QUESTION:`.

### 19c. Do you want a unit test coverage bar?

*Tick one:*

- [x] Yes — answer 19d–19h
- [ ] No

**Answer:** One bar for the frontend and one for the backend, with the same values.

### 19d. Coverage — metric and threshold?

**Answer:** **Over 95%**, frontend and backend each. TODO — confirm the metric (line coverage,
branch coverage, or both) and whether exactly 95% passes.

### 19e. Coverage — scope?

*Tick one:*

- [x] Whole codebase
- [ ] Changed/new code only

**Answer:** The gate is checked once, at the end, so it judges all the code built.

### 19f. Coverage — exclusions?

**Answer:** TODO — e.g. generated sources, DTOs/records, configuration and bootstrap classes.
Left blank, this is raised as an `OPEN QUESTION:`.

### 19g. Coverage — enforcement?

*Tick one:*

- [x] Build fails below the bar
- [ ] CI-only
- [ ] Advisory report

**Answer:** The only option that gates here, since there is no CI (Q15).

### 19h. Coverage — from when?

*Tick one:*

- [ ] From the scaffold phase onward (recommended — retrofitting coverage across finished phases costs far more)
- [x] From a named phase — name it

**Answer:** **A dedicated coverage phase, scheduled after every feature phase.** Every earlier
phase writes unit tests for the behavior it builds, but does not have to reach 95% and carries
no coverage exit criterion. The coverage phase turns the gate on and brings the whole codebase
up to the bar; if a plan refresh adds feature phases, they go before it. The plan records that
catch-up work as a risk.

---

## J. Ownership

### 25a. Who answers business-rule questions?

**Answer:** TODO

### 25b. Who answers technical questions?

**Answer:** TODO

---

## Appendix — constraints this intake is expected to produce

A checklist for the Stage 0 hand-off, not an input to it.

| # | Constraint | Source |
|---|---|---|
| 1 | Strict behavioral parity (default unless 3a says otherwise) | Q3a |
| 2 | Reuse the existing database verbatim; mapping validated against the live schema | Q7 (archetype) — **once confirmed** |
| 3 | Entra ID auth behind a seam, with a dev stub that only a local profile can activate; roles and permissions read from the database | Q11b–c, Q11g (archetype) |
| 4 | Connection identities — SQL authentication to the database, no credential in source | Q10b + Q13f (archetype) |
| 5 | Code-first OpenAPI; Swagger UI never reachable in production | Q5d–e (archetype) |
| 6 | Frontend coverage over 95%, whole codebase, build fails — **bound in the final coverage phase only** | Q19 (archetype) |
| 7 | Backend coverage over 95%, whole codebase, build fails — **bound in the final coverage phase only** | Q19 (archetype) |
| 8 | **Deployment files** — a Dockerfile and Helm chart per part, written in that part's scaffold phase, never built or run; checked only for existence and contents | Q13a–b — no archetype; raise it from 13a's answer |
| 9 | Fixed source tree roots (`<app_name>-modernized/<app_name>-ui` and `-svcs`) | Q16f — recorded in `context.repo.*`, not a constraint |

Not constraints: big-bang cutover with fix-forward (Q12a, Q12b default) and no CI/CD (Q15).
