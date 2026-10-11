# Technical Requirements: EmployeeSearch

> **Related documents:**
> - [Business Requirements](BUSINESS_REQUIREMENTS_EmployeeSearch.md) — *why*
> - [Functional Requirements](FUNCTIONAL_REQUIREMENTS_EmployeeSearch.md) — *what*
>
> This document records the current .NET *how* as **constraints to honor** for the
> Angular + Java/Spring Boot + relational-DB rebuild. See Project-Wide Constraints
> **C1** (reuse DB as-is) and **C2** (auth path) in the extraction instructions.

---

## 1. Technical Overview

| Aspect | Value | Source |
|--------|-------|--------|
| App type | Windows desktop, **WinForms** (`WinExe`, `UseWindowsForms`) | [EmployeeSearch.csproj:4-8](../EmployeeSearch.csproj#L4-L8) |
| Framework | **.NET 8** (`net8.0-windows`), nullable + implicit usings enabled | [EmployeeSearch.csproj:5-7](../EmployeeSearch.csproj#L5-L7) |
| Dependencies | `BCrypt.Net-Next` 4.0.3 (password hashing); `Microsoft.Data.Sqlite` 8.0.0 (data access) | [EmployeeSearch.csproj:11-14](../EmployeeSearch.csproj#L11-L14) |
| Database | **SQLite** file `employeesearch.db` in the app base directory | [Database/DatabaseHelper.cs:9-10](../Database/DatabaseHelper.cs#L9-L10) |
| Entry point | `Program.Main()` — `STAThread`; initializes DB, then loops Login → Search | [Program.cs:6-34](../Program.cs#L6-L34) |
| Layers | UI (`Views/*Form`), model (`Models/Employee`), data access (`Database/DatabaseHelper` static). **UI calls the data layer directly**; no service/business layer, no DI. | [Views/](../Views), [Database/DatabaseHelper.cs](../Database/DatabaseHelper.cs) |
| Architecture note | Data layer is a single **static** class opening a new connection per call; all SQL is inline. | [Database/DatabaseHelper.cs:7](../Database/DatabaseHelper.cs#L7) |

**Top-level flow (`Program.Main`)** — [Program.cs:15-33](../Program.cs#L15-L33):
`DatabaseHelper.Initialize()` (create tables + seed) → loop: show `LoginForm` (modal); if
not OK, exit; else open `SearchForm(username)`; when it closes, re-loop only if the user
logged out (else exit).

---

## 2. Data Model  (C1 — existing DB reused as-is)

> **Critical (C1):** The modernized backend maps onto these tables as-is with
> `ddl-auto=validate`. Today the schema is **created by the app** at startup via
> `CREATE TABLE IF NOT EXISTS` — there is no external schema or migration tool.
> Source: [Database/DatabaseHelper.cs:12-39](../Database/DatabaseHelper.cs#L12-L39).
> `OPEN QUESTION:` For production, will the rebuild target this SQLite DB, or a different
> relational engine into which this schema/data is loaded? SQLite specifics below affect
> JPA mapping either way.

### DM-1 — Table `Users` (enforces BR-1, ROLE-1, VR-10)
| Column | Type (declared) | Null | Key / constraint | Source |
|--------|-----------------|------|------------------|--------|
| `Id` | INTEGER | no | PK, `AUTOINCREMENT` | [DatabaseHelper.cs:20](../Database/DatabaseHelper.cs#L20) |
| `Username` | TEXT | no | **UNIQUE** | [DatabaseHelper.cs:21](../Database/DatabaseHelper.cs#L21) |
| `PasswordHash` | TEXT | no | — (BCrypt hash string) | [DatabaseHelper.cs:22](../Database/DatabaseHelper.cs#L22) |

### DM-2 — Table `Employees` (enforces BR-2, BR-5, BR-6; feeds FR-3)
| Column | Type (declared) | Null | Key / constraint | Notes | Source |
|--------|-----------------|------|------------------|-------|--------|
| `Id` | INTEGER | no | PK, `AUTOINCREMENT` | | [DatabaseHelper.cs:25](../Database/DatabaseHelper.cs#L25) |
| `Name` | TEXT | no | | | [DatabaseHelper.cs:26](../Database/DatabaseHelper.cs#L26) |
| `Department` | TEXT | no | | No DB-level enum; value set enforced only by the UI dropdown (VR-2). | [DatabaseHelper.cs:27](../Database/DatabaseHelper.cs#L27) |
| `Role` | TEXT | no | | UI-enforced set (VR-3). | [DatabaseHelper.cs:28](../Database/DatabaseHelper.cs#L28) |
| `Status` | TEXT | no | | UI-enforced set (VR-4). | [DatabaseHelper.cs:29](../Database/DatabaseHelper.cs#L29) |
| `Email` | TEXT | yes | | | [DatabaseHelper.cs:30](../Database/DatabaseHelper.cs#L30) |
| `Phone` | TEXT | yes | | | [DatabaseHelper.cs:31](../Database/DatabaseHelper.cs#L31) |
| `HireDate` | TEXT | yes | | Stored as **text** (`YYYY-MM-DD` in seed data), **not** a DATE type. | [DatabaseHelper.cs:32](../Database/DatabaseHelper.cs#L32) |
| `Salary` | REAL | yes | | Floating-point (read as `double`); displayed as currency (VR-9). | [DatabaseHelper.cs:33](../Database/DatabaseHelper.cs#L33) |

**Relationships:** None. `Users` and `Employees` are independent; **no foreign keys**. A
`User` is not linked to an `Employee`.

**JPA/Hibernate mapping flags (C1):**
- SQLite uses **type affinity**, not strict types — `INTEGER`/`TEXT`/`REAL` map to
  Java `Long`/`String`/`Double`. There is no native SQLite JPA dialect in standard
  Hibernate; a community dialect/driver is required, or migrate to a supported engine.
- `HireDate` is **TEXT**, so map to `String` (or convert on read) rather than
  `LocalDate` unless the target DB stores a real date.
- `Salary` is **REAL** (floating point) — not suitable for exact currency math; note if
  the target DB should use `DECIMAL/NUMERIC`.
- `AUTOINCREMENT` PKs → `GenerationType.IDENTITY`.
- Case-sensitive identifier casing (`Users`, `Employees`, `PasswordHash`, `HireDate`)
  must be preserved exactly.

### DM-3 — Seed / reference data (created on first run only if the table is empty)
- **Admin user** (`Users`): `Username = 'admin'`, `PasswordHash =` BCrypt hash of
  `'admin123'`. Seeded only if no `admin` row exists.
  [DatabaseHelper.cs:41-53](../Database/DatabaseHelper.cs#L41-L53). **Security risk — see §4.**
- **15 employees** (`Employees`), seeded only if the table is empty
  [DatabaseHelper.cs:62-96](../Database/DatabaseHelper.cs#L62-L96). Exact rows
  (`Name, Department, Role, Status, Email, Phone, HireDate, Salary`):

  | Name | Dept | Role | Status | Email | Phone | HireDate | Salary |
  |------|------|------|--------|-------|-------|----------|--------|
  | Alice Johnson | IT | Developer | Active | alice@corp.com | 555-0101 | 2021-03-15 | 85000 |
  | Bob Smith | HR | Manager | Active | bob@corp.com | 555-0102 | 2019-07-01 | 92000 |
  | Carol White | Finance | Analyst | Active | carol@corp.com | 555-0103 | 2020-11-20 | 78000 |
  | David Brown | Marketing | Coordinator | On Leave | david@corp.com | 555-0104 | 2022-01-10 | 65000 |
  | Eva Martinez | IT | Developer | Active | eva@corp.com | 555-0105 | 2021-08-05 | 88000 |
  | Frank Lee | Operations | Manager | Active | frank@corp.com | 555-0106 | 2018-05-22 | 95000 |
  | Grace Kim | HR | Analyst | Inactive | grace@corp.com | 555-0107 | 2020-04-17 | 72000 |
  | Henry Davis | Finance | Manager | Active | henry@corp.com | 555-0108 | 2017-09-30 | 105000 |
  | Irene Wilson | IT | Designer | Active | irene@corp.com | 555-0109 | 2023-02-14 | 80000 |
  | Jack Taylor | Marketing | Manager | Active | jack@corp.com | 555-0110 | 2019-12-01 | 98000 |
  | Karen Anderson | Operations | Coordinator | Active | karen@corp.com | 555-0111 | 2022-06-28 | 62000 |
  | Liam Thompson | IT | Analyst | On Leave | liam@corp.com | 555-0112 | 2021-05-19 | 82000 |
  | Maya Patel | Finance | Coordinator | Active | maya@corp.com | 555-0113 | 2023-08-07 | 60000 |
  | Noah Garcia | Marketing | Designer | Active | noah@corp.com | 555-0114 | 2022-10-03 | 74000 |
  | Olivia Chen | Operations | Analyst | Inactive | olivia@corp.com | 555-0115 | 2020-07-25 | 70000 |

  `ASSUMPTION:` This is POC sample data, not production data (see
  [BUS §7](BUSINESS_REQUIREMENTS_EmployeeSearch.md#7-open-questions--assumptions-business-facing)).

---

## 3. Data Access & Persistence

Raw ADO.NET via `Microsoft.Data.Sqlite`; a fresh `SqliteConnection` opened per operation;
inline parameterized SQL; no ORM, no stored procedures, no transactions, no caching.
Static helper class [DatabaseHelper.cs](../Database/DatabaseHelper.cs).

| ID | Operation | Intent | SQL (shape) | Source |
|----|-----------|--------|-------------|--------|
| DA-1 | `ValidateLogin` (supports FR-1) | Fetch the stored hash for a username, then BCrypt-verify the password in app code. | `SELECT PasswordHash FROM Users WHERE Username = @u` | [DatabaseHelper.cs:99-108](../Database/DatabaseHelper.cs#L99-L108) |
| DA-2 | `SearchEmployees` (supports FR-3, VR-1) | Dynamic filtered search. Builds WHERE from active filters (name `LIKE`, dept/role/status `=`), joined by AND, `ORDER BY Name`. **All values passed as bound parameters** (no SQL injection). | `SELECT Id,Name,Department,Role,Status,Email,Phone,HireDate,Salary FROM Employees [WHERE ...] ORDER BY Name` | [DatabaseHelper.cs:110-163](../Database/DatabaseHelper.cs#L110-L163) |
| DA-3 | `Initialize` / seeding | Create tables if absent; conditionally seed admin + employees. | `CREATE TABLE IF NOT EXISTS ...`; `SELECT COUNT(*)`; `INSERT` | [DatabaseHelper.cs:12-97](../Database/DatabaseHelper.cs#L12-L97) |

- **Concurrency:** none handled — single-user desktop; no locking/optimistic concurrency.
- **Transactions:** none; each seed insert runs independently.
- **Null handling on read:** Email/Phone/HireDate → `""` if NULL; Salary → `0` if NULL.
  [DatabaseHelper.cs:156-159](../Database/DatabaseHelper.cs#L156-L159)

---

## 4. Authentication & Security  (C2)

**C2 determination: the app is NOT Active Directory-based.** It uses a **local `Users`
table with BCrypt-hashed passwords** (forms-style username/password). Therefore the C2
path is: **auth seam + dev stub, with real AD deferred as `TODO (AD)`** — the AD mechanism
to be decided later. The current local-account model is the source of truth for *what
access exists* (a single undifferentiated access level — see ROLE-1).

| ID | Mechanic | Detail | Source |
|----|----------|--------|--------|
| SEC-1 | Authentication | Username/password. `ValidateLogin` reads `PasswordHash` by username and calls `BCrypt.Verify`. Success returns the username string; no session/token/expiry (desktop, single process). | [DatabaseHelper.cs:99-108](../Database/DatabaseHelper.cs#L99-L108), [LoginForm.cs:50-60](../Views/LoginForm.cs#L50-L60) |
| SEC-2 | Password storage | **BCrypt** via `BCrypt.Net-Next` 4.0.3. `BCrypt.HashPassword("admin123")` uses the library default work factor (`ASSUMPTION:` 11) and per-hash salt. Verified with `BCrypt.Verify`. | [DatabaseHelper.cs:48,107](../Database/DatabaseHelper.cs#L48) |
| SEC-3 | Authorization | **None.** Any authenticated user can do everything (ROLE-1 / BR-4). No role, claim, or permission check exists anywhere. | [Views/SearchForm.cs](../Views/SearchForm.cs) |
| SEC-4 | Session/identity | The signed-in username is passed to `SearchForm` and shown in the header; not persisted or re-verified. | [SearchForm.cs:9-18](../Views/SearchForm.cs#L9-L18) |
| SEC-5 | Transport/secrets | No network calls; connection string is a local file path (no credentials/secrets). | [DatabaseHelper.cs:9-10](../Database/DatabaseHelper.cs#L9-L10) |

### Security Concerns / Risks
- **RISK-1 (High):** Default credentials `admin / admin123` are seeded and **displayed on
  the login screen** (`lblHint`). Well-known credentials with no forced change.
  [DatabaseHelper.cs:48](../Database/DatabaseHelper.cs#L48),
  [LoginForm.Designer.cs:145](../Views/LoginForm.Designer.cs#L145)
- **RISK-2 (Medium):** No account lockout, throttling, or audit logging of login attempts.
- **RISK-3 (Medium):** No authorization tiers — salary and all PII are visible to every
  authenticated user (BR-3). Web rebuild should decide whether salary/PII is group-gated.
- **RISK-4 (Low, positive note):** SQL is fully parameterized (DA-2), so there is **no SQL
  injection** despite dynamic WHERE building — preserve this in the rebuild.
- **RISK-5 (Low):** No password policy (length/complexity) and no self-service change/reset.

> The auth direction and its open items are also listed in §10.

---

## 5. Integrations & External Dependencies

| ID | System | Direction | Detail | Source |
|----|--------|-----------|--------|--------|
| INT-1 | SQLite database file (`employeesearch.db`) | in/out | Local file in the app base dir; created/seeded on first run. | [DatabaseHelper.cs:9-10](../Database/DatabaseHelper.cs#L9-L10) |
| INT-2 | Local file system (CSV export) | out | Writes a UTF-8 `.csv` at a user-chosen path via SaveFileDialog (RPT-1). | [SearchForm.cs:63-72](../Views/SearchForm.cs#L63-L72) |

No REST/SOAP/WCF services, message queues, email/SMTP, or third-party APIs.
"No network integrations found."

---

## 6. Background / Scheduled Processing

**None.** No timers, scheduled jobs, Windows Services, or message consumers. The only
startup task is `DatabaseHelper.Initialize()` (schema creation + conditional seeding, DA-3).
[Program.cs:15](../Program.cs#L15)

---

## 7. Non-Functional Requirements

| ID | Area | Observed behaviour | Source |
|----|------|--------------------|--------|
| NFR-1 | Concurrency | Single-user, single-process desktop; no multi-user/locking design. | [Program.cs](../Program.cs) |
| NFR-2 | Performance | Full-table search with `LIKE %..%` and no paging/limits; fine for the 15-row POC, unbounded at scale. | [DatabaseHelper.cs:140-146](../Database/DatabaseHelper.cs#L140-L146) |
| NFR-3 | Error handling | Login errors shown inline; empty-export shown as a dialog. **No try/catch** around DB or file I/O — unexpected failures are unhandled. | [LoginForm.cs:63-67](../Views/LoginForm.cs#L63-L67), [SearchForm.cs:56-72](../Views/SearchForm.cs#L56-L72) |
| NFR-4 | Logging / auditing | None. No logs of logins, searches, or exports. | (absence) |
| NFR-5 | Localization | UI strings hardcoded (en); salary format is culture-dependent (`"C0"`, VR-9). No i18n framework. | [Models/Employee.cs:14](../Models/Employee.cs#L14) |
| NFR-6 | Deployment/runtime | Single Windows desktop executable; requires .NET 8 Windows Desktop runtime; DB auto-created beside the exe. | [EmployeeSearch.csproj:4-5](../EmployeeSearch.csproj#L4-L5) |
| NFR-7 | Accessibility | Standard WinForms controls; no explicit accessibility work observed. | [Views/](../Views) |

---

## 8. Configuration

Configuration is **entirely in code** — there is no `app.config` / `appsettings.json`.

| ID | Setting | Value / shape | Source |
|----|---------|---------------|--------|
| CFG-1 | DB connection string | `Data Source={BaseDirectory}\employeesearch.db` — SQLite, file-based, no credentials. | [DatabaseHelper.cs:9-10](../Database/DatabaseHelper.cs#L9-L10) |
| CFG-2 | DB file location | `AppDomain.CurrentDomain.BaseDirectory` (next to the exe). | [DatabaseHelper.cs:9](../Database/DatabaseHelper.cs#L9) |
| CFG-3 | Default admin credentials | `admin` / `admin123` (hardcoded seed — see RISK-1). | [DatabaseHelper.cs:48](../Database/DatabaseHelper.cs#L48) |
| CFG-4 | Dropdown value lists | Department/Role/Status option sets (VR-2/3/4) hardcoded in the designer. | [SearchForm.Designer.cs:180,193,207](../Views/SearchForm.Designer.cs#L180) |

No feature flags or environment-specific settings exist. For the rebuild, the connection
string shape needed is: a datasource/URL, and (for a server DB) schema/owner + credentials
— none of which exist today because the DB is a local file. `OPEN QUESTION:` target DB
engine and connection details (§10).

---

## 9. Goes Away / New Concerns  (orientation for the migration planner)

**Implementation details that will NOT carry over:**
- WinForms UI and the `*.Designer.cs` layout/styling (colors, fonts, anchors) → replaced
  by Angular components. Colour *meanings* (VR-5) and field lists (UI-2) are worth keeping;
  the pixel layout is not.
- Single-process desktop packaging and the modal Login→Search loop in `Program.Main`.
- **Direct UI-to-DB calls** via a static `DatabaseHelper` → replaced by a Spring Boot
  service/repository layer and a REST API the Angular app consumes.
- The app **creating its own schema and seeding data** at startup (`CREATE TABLE IF NOT
  EXISTS`, seed rows) → the rebuild reuses the existing DB (C1) with `ddl-auto=validate`;
  it must **not** create or seed schema.
- `Salary` display formatting via .NET `"C0"` and the `SalaryFormatted` model property →
  becomes a frontend/formatting concern.

**New concerns the web stack introduces (forward-looking flags, not requirements):**
- **AuthN/AuthZ:** replace the single local `admin` account with an **auth seam** (dev stub
  now, `TODO (AD)` later per C2); introduce tokens/sessions, statelessness, and CORS.
  Decide AD group→access mapping and whether salary/PII is group-gated (RISK-3).
- **Two-tier deployment:** Angular client + Spring Boot server + shared DB, versus today's
  single exe with an embedded file DB.
- **Concurrency & paging:** multi-user access and result paging/limits (NFR-2) become real.
- **DB engine:** SQLite type-affinity, TEXT dates, and REAL salary (DM-1/DM-2) need explicit
  Java type decisions; a supported JPA dialect or target engine must be chosen.
- **Server-side validation:** the value-set constraints currently enforced only by UI
  dropdowns (VR-2/3/4) must be enforced on the server.

---

## 10. Open Questions & Assumptions (technical)

- `OPEN QUESTION:` (C2) What AD mechanism replaces local login (LDAP / Windows Integrated /
  Kerberos / AD-backed OIDC), and which AD group(s) grant access? Marked `TODO (AD)`. The
  only current identity concept is a `Users.Username` row (SEC-1).
- `OPEN QUESTION:` (C1) Does the rebuild connect to this SQLite file, or is the schema/data
  loaded into another relational engine? This determines the JPA dialect and the DM-1/DM-2
  type mappings (TEXT date, REAL salary).
- `OPEN QUESTION:` Should `Employees.Department/Role/Status` become DB-level enums/lookup
  tables, or stay free-text enforced only by the app (VR-2/3/4)? Today there is no DB
  constraint (DM-2).
- `OPEN QUESTION:` Should salary use exact `DECIMAL` rather than floating-point `REAL`
  (DM-2)?
- `ASSUMPTION:` BCrypt work factor is the library default (11) — the seed does not specify
  one (SEC-2).
- `ASSUMPTION:` `HireDate` values follow `YYYY-MM-DD`; the column is untyped TEXT (DM-2).
- `ASSUMPTION:` The SQLite DB and its seed rows are POC artifacts; production data is the
  reused source of truth (C1).

---

## 11. Traceability Index

| Requirement | Source |
|-------------|--------|
| DM-1 | [Database/DatabaseHelper.cs:19-23](../Database/DatabaseHelper.cs#L19-L23) |
| DM-2 | [Database/DatabaseHelper.cs:24-34](../Database/DatabaseHelper.cs#L24-L34) |
| DM-3 | [Database/DatabaseHelper.cs:41-96](../Database/DatabaseHelper.cs#L41-L96) |
| DA-1 | [Database/DatabaseHelper.cs:99-108](../Database/DatabaseHelper.cs#L99-L108) |
| DA-2 | [Database/DatabaseHelper.cs:110-163](../Database/DatabaseHelper.cs#L110-L163) |
| DA-3 | [Database/DatabaseHelper.cs:12-97](../Database/DatabaseHelper.cs#L12-L97) |
| SEC-1..SEC-5 | [Database/DatabaseHelper.cs:99-108](../Database/DatabaseHelper.cs#L99-L108), [Views/LoginForm.cs](../Views/LoginForm.cs) |
| INT-1 | [Database/DatabaseHelper.cs:9-10](../Database/DatabaseHelper.cs#L9-L10) |
| INT-2 | [Views/SearchForm.cs:63-72](../Views/SearchForm.cs#L63-L72) |
| BG (none) | [Program.cs:15](../Program.cs#L15) |
| NFR-1..7 | [Program.cs](../Program.cs), [Views/](../Views), [Database/DatabaseHelper.cs](../Database/DatabaseHelper.cs) |
| CFG-1..4 | [Database/DatabaseHelper.cs:9-10](../Database/DatabaseHelper.cs#L9-L10), [Views/SearchForm.Designer.cs:180](../Views/SearchForm.Designer.cs#L180) |
