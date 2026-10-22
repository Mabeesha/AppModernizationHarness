# Tier 2 Test Dataset — Plan

*Status: **plan only. Nothing here is built yet.** Each step that adds files to the repo is a
design change and needs a yes before it starts (see §9).*

This plan describes how to build a small set of test cases for the Tier 2 behavioural eval —
the part of the eval that actually runs the harness and grades what comes out
([EVAL_DESIGN.md §6](EVAL_DESIGN.md)). Tier 2 is designed but not built, and is blocked on
having test cases. This plan unblocks it.

---

## 1. Goal

Build a **small, frozen set of test cases** that:

1. look like the real modernization work this harness is used for (§2);
2. contain **known, planted traps**, so the eval can check "did the harness find it?"
   instead of only "did the output change?";
3. are **cheap enough to run three times per setup** (Tier 2 needs at least 3 runs per
   setup, because AI runs vary — [EVAL_DESIGN.md §6.5](EVAL_DESIGN.md));
4. can later answer cost questions too, such as "is Sonnet good enough for the build
   stage?" — if the cost metrics are approved separately.

## 2. The fixed setup the dataset targets

We start narrow, with one tech profile that matches the real apps. Every test case uses it.

| Setting | Value |
|---|---|
| **Legacy (source)** | Old .NET: **desktop (WinForms)** and **web (ASP.NET MVC 5)**, on .NET Framework 4.x |
| **Legacy database** | SQL Server 2016 or newer |
| **Legacy login** | **Windows / Active Directory login.** Broad roles from **AD groups**; finer permissions from **SQL tables** where needed |
| **Target A** | **Angular** front end + **Java (Spring Boot)** backend |
| **Target B** | **Angular** front end + **.NET Web API** backend |
| **Database** | **Reuse the existing database** — no renaming, no redesign |
| **New login** | **Microsoft Entra ID**, behind an **auth seam** (one plug-in point for login), plus a **local-only dev stub** (a fake login with one fixed test user per role) |
| **Login testing** | **Dev stub only.** No real Entra account or tenant is ever needed. The new app must work end-to-end on the stub. The stub must be structurally unable to switch on in production |
| **Deployment** | Front end and back end are **two separate deployments** |
| **Parity** | **Strict** — the new app behaves exactly like the old one, quirks included |

The intake answers for login can copy the worked example
([INTAKE_EXAMPLE.md, questions 11b–11g](../ModernizationHarness/examples/INTAKE_EXAMPLE.md)),
which already describes Entra + seam + dev stub. **No harness change is needed for this setup.**

**One legacy app, two targets.** Each legacy app gets two intakes, one per target. So two
custom apps give four normal test cases. Bonus check: the requirements extracted from one app
(Stage 1) should be nearly the same for both targets, because they describe the *old* app.

## 3. Where the test apps come from

| Source | Decision | Why |
|---|---|---|
| **Custom apps written for the eval** (AI-assisted, human-checked) | **Use — this is the whole dataset** | Every trap is known. The model has never seen them |
| A cleaned-up slice of a real work app | **Not allowed** (company rules) | — |
| Famous public samples (MVC Music Store, Contoso University, Northwind) | **Do not use** | The model has likely seen them in training and may "remember" features instead of reading the code, which makes scores look too good |

**Rule for custom apps:** whoever writes an app (person or AI session) also drafts its answer
key, and **a human then checks the key against the code**. The AI never grades its own
homework unchecked. Use a *different* session for writing the app than for running the eval.

Because no real-app slice is allowed, the custom apps must carry the realism themselves. They
should be a little messy on purpose: inconsistent naming, logic in the wrong layer, one or two
dead code paths, comments that are out of date.

## 4. What one test case contains

```
eval/fixtures/<app-name>/
  legacy/             the old app's source code (read-only in every run)
  db/schema.sql       tables, views, stored procedures, triggers
  db/seed.sql         a few example rows; needed only for build-stage runs
  intake-dotnet.md    intake answers for Target B
  intake-java.md      intake answers for Target A
  answer-key.md       what a good result must contain (human-checked)
```

This replaces the single `eval/fixtures/INTAKE.md` that [EVAL_DESIGN.md §6.1](EVAL_DESIGN.md)
plans today. Changing that is part of Step 1 (§8).

### The answer key

The answer key is what makes this a real test. It has four parts:

1. **Requirements** — each real behaviour of the old app, with the `file:line` where it lives.
2. **Traps** — each planted trap, with an id (`T01`, `T02`, …), its category (§5), the stage
   that should catch it, and what "caught" looks like.
3. **Expected questions** — the things a good agent should raise as `OPEN QUESTION:` instead
   of deciding alone.
4. **Data model** — every table and column. This part is **generated from `db/schema.sql`
   by a script**, not typed by hand, so a simple deterministic check can ask "did Stage 1
   capture every table and column?"

Example trap entry:

| Id | Category | Planted at | Should be caught by | Caught means |
|---|---|---|---|---|
| T03 | Strict parity | `Services/LeaveCalc.cs:41` | Stage 1 | A requirement states half days are rounded **down**, with this citation |

## 5. Trap catalogue

Traps are grouped by the setting they test. Each custom app gets about **12 traps**, drawn
from these groups, with **no trap reused across apps**.

### 5.1 Reusing the database

- Odd column names (`EMP_STAT_CD`) that must not be renamed.
- A `'Y'/'N'` text column used as a true/false flag.
- A composite key (a key made of two columns).
- A stored procedure that holds business logic.
- A trigger that writes audit rows the C# code never mentions.
- A view the app reads from as if it were a table.

### 5.2 Login: Windows/AD today, Entra + dev stub tomorrow

- **User identity format (the key trap).** The old app stores users as Windows names
  (`CORP\jsmith`): in a permissions table key, and in audit columns such as `CreatedBy`.
  The new app gets Entra names (`jsmith@corp.com`). With the database reused and strict parity
  required, a good agent must **raise this as an `OPEN QUESTION:`**, not quietly pick a
  conversion.
- One user-name comparison in code that is **case-sensitive**.
- A role check hidden in a view (`User.IsInRole` inside a `.cshtml`), not in the controller.
- A permission enforced **only inside a stored procedure**.
- One "super user" granted by **user name** in code, not by group.
- Every AD group must map to an Entra app role or group (intake question 11f), using
  **made-up** names and placeholder ids, never a real tenant.
- **Dev stub fits the data:** the stub's test users must carry identities that match rows in
  `db/seed.sql`. Otherwise the SQL permission checks find nobody, and the app "works" with no
  data visible. The design and plan must handle this.
- The dev stub must be **structurally unable** to run under the production profile — not just
  "off by default".

### 5.3 Two separate deployments

- Logic in MVC controllers that must become API endpoints.
- A server-rendered dropdown whose list now needs its own API call.
- Front-end config that must point at the backend's address (not hard-coded).
- Cross-origin calls (CORS) between the two deployments must be designed for.

### 5.4 Strict parity

- Rounding rules (for example half days rounded down).
- Default sort order of a list.
- **Case-insensitive search that comes from the database's collation** (its text-comparison
  setting), so it is invisible in the C# code.
- A hard cap on result rows (for example 100).
- Exact validation and error messages.
- Exact date and number formats.

### 5.5 Desktop-specific (Fixture 3 only)

- Business logic inside button-click handlers, which must be pulled out into the API.
- Direct SQL inside forms, with no data layer.
- `WindowsIdentity.GetCurrent()` used for the user, with AD group checks.

## 6. The test cases

| # | Fixture | Kind | Legacy | Targets | Purpose |
|---|---|---|---|---|---|
| F1 | `employee-search` (exists) | Smoke test | WinForms + **SQLite**, username/password form | Target B only | Quick "does it run at all" check. Cheap. **Not** the main test — its database and login do not match the real setup |
| F2 | Custom web app (e.g. leave requests with approvals) | Main | ASP.NET MVC 5 + SQL Server, Windows login, AD groups + SQL permissions table | A and B | The main test. About 20–40 files, 3–4 modules, ~12 traps |
| F3 | Custom desktop app (e.g. stock or asset tracking) | Main | WinForms + SQL Server, `WindowsIdentity` + AD groups | A and B | Desktop problems (§5.5), different traps from F2 |
| N1–N3 | Bad-input copies of one F2 intake | Negative | (F2's) | B | Check the harness refuses correctly (§7) |

Total: **1 smoke + 4 main + 3 negative = 8 cases.**

## 7. Bad-input cases

Each is a copy of an F2 intake with exactly one thing broken. They stop early, so they are
cheap.

| Case | What is broken | Correct behaviour |
|---|---|---|
| N1 | A blocking question left blank (login method) | Stage 0 **hard-stops** |
| N2 | A contradiction: "strict parity" plus "the role model may be merged" | Raised as an `OPEN QUESTION:`, not quietly resolved |
| N3 | A vague answer on a non-blocking question | Gets a **stated default**, reported back in the Stage 0 hand-off |

## 8. Steps

Each step ends with a clear "done" check. Steps 1–5 need a yes before they start (§9).

### Step 1 — Agree the format
- Update [EVAL_DESIGN.md §6.1](EVAL_DESIGN.md) and [README.md](README.md): the folder layout
  (§4), the answer-key format, and the move from one `INTAKE.md` to per-fixture intakes.
- **Done when:** the two docs describe the layout, and you have approved it.

### Step 2 — F1: the existing employee-search app
- Write `intake-dotnet.md` (Target B, the setup in §2).
- Write a small answer key (5–10 items) from the existing code. Human-check it.
- **Done when:** Tier 2 is no longer blocked on a missing intake
  ([EVAL_DESIGN.md §13, item 2](EVAL_DESIGN.md)).

### Step 3 — F2: the custom MVC web app
- Write the app, `schema.sql` and `seed.sql`, with ~12 traps from §5.1–5.4.
- Write both intakes and the answer key. Generate the data-model part from `schema.sql`.
- Human-check the answer key against the code.
- **Done when:** every trap in the key points at real code, and the app builds.

### Step 4 — F3: the custom WinForms app
- Same as Step 3, with traps from §5.5 plus ones not used in F2.
- **Done when:** same checks as Step 3.

### Step 5 — Bad-input cases N1–N3
- Copy one F2 intake three times and break one thing in each (§7).
- **Done when:** each file differs from its source in exactly one answer.

### Step 6 — Freeze and take a baseline
- Freeze the fixtures. Change them only on purpose, with a version note.
- Run Stages 0–3 three times per case with Opus; record the scores. This is the baseline
  every later change is compared against.
- If the cost metrics are approved (separate decision), record tokens and cost too, then
  repeat with Sonnet.
- **Done when:** a baseline result file exists for every case.

### Later — build-stage runs
- Run Stage 4 (build) and Stage 5 (review) on F2 and F3. Needs a SQL Server (for example in
  Docker) loaded from `schema.sql` + `seed.sql`. Login uses the dev stub only — **no Entra
  needed**, so these runs work fully offline.

## 9. Decisions that need a yes

These are design changes under this repo's rules, so each needs approval before work starts:

1. **The fixture layout and answer-key format** (Step 1) — changes the Tier 2 design.
2. **Adding the fixture files** (Steps 2–5) — new eval content.
3. **The data-model generator script** (Step 3) — a new eval tool.
4. **Cost metrics in Tier 2** — separate decision, discussed earlier; touches the
   "minimizing tokens is a non-goal" wording in [EVAL_DESIGN.md §1](EVAL_DESIGN.md).

## 10. Risks

| Risk | What could go wrong | Mitigation |
|---|---|---|
| Too clean | Custom apps are tidier than real ones, so scores look too good | Add deliberate mess (§3); keep each trap subtle |
| Self-grading | The AI that writes an app writes a key that matches its own blind spots | Human checks every key; separate sessions |
| Trap leakage | Traps named in comments or file names give the answer away | No comment or name hints at a trap |
| Drift | Fixtures change between runs, so score changes mean nothing | Freeze after Step 6; version every change |
| Cost | 8 cases × 3 runs × 4 stages adds up | Stages 0–3 only at first; negative cases stop early; set the per-run cap from [EVAL_DESIGN.md §13, item 4](EVAL_DESIGN.md) before Step 6 |
