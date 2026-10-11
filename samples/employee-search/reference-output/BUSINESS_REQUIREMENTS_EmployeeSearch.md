# Business Requirements: EmployeeSearch

> **Documents in this set** — all derived from a single survey of the same codebase:
> - Business Requirements (this document) — *why the app exists*
> - [Functional Requirements](FUNCTIONAL_REQUIREMENTS_EmployeeSearch.md) — *what the system does*
> - [Technical Requirements](TECHNICAL_REQUIREMENTS_EmployeeSearch.md) — *how it is built today / constraints*

---

## 1. System Overview

EmployeeSearch is an internal desktop application that lets an authenticated staff
member look up employees in a company directory and filter that directory by name,
department, role, and employment status. Its single business purpose is fast,
gated lookup of employee records — including contact details and salary — from one
central list. Results can be exported to a CSV file for offline use or sharing.

Access is protected by a username/password sign-in; only signed-in users can view
any data. The application today is a single-user, single-machine Windows desktop
tool seeded with sample data (15 employees and one built-in administrator account).
It is a proof-of-concept being modernized to a web application (Angular + Java/Spring
Boot + relational database).

---

## 2. Business Objectives

| ID   | Objective | Success criteria (where evidenced) | Source |
|------|-----------|-------------------------------------|--------|
| BO-1 | Provide a single, searchable directory of employees. | A user can retrieve matching employees by combining name/department/role/status filters. | [Database/DatabaseHelper.cs:110](../Database/DatabaseHelper.cs#L110) |
| BO-2 | Restrict all employee data to authenticated users only. | No employee data is reachable without a successful sign-in. | [Program.cs:17-33](../Program.cs#L17-L33), [Views/LoginForm.cs:39-61](../Views/LoginForm.cs#L39-L61) |
| BO-3 | Allow staff to take the current result set offline. | The visible results can be exported to a CSV file on demand. | [Views/SearchForm.cs:54-75](../Views/SearchForm.cs#L54-L75) |
| BO-4 | Present employment status clearly and at a glance. | Each status is colour-coded in the results list. | [Views/SearchForm.cs:124-143](../Views/SearchForm.cs#L124-L143) |

> `ASSUMPTION:` No formal success metrics (KPIs, SLAs, adoption targets) are recorded
> in the codebase; the objectives above are inferred from observed behaviour.

---

## 3. Scope & User Classes

### 3.1 In scope (observed behaviour)
- Authenticating a user by username and password.
- Searching/filtering the employee directory.
- Viewing employee fields: name, department, role, status, email, phone, hire date, salary.
- Exporting the current results to CSV.
- Logging out and signing in as a different user.

### 3.2 Out of scope (not present in the code)
- Creating, editing, or deleting employees (the directory is **read-only** to the user).
- Creating, editing, or deleting user accounts, or self-service password change/reset.
- Any role-based differences in what a user may see or do (see BR-4 / ROLE-1).
- Reporting beyond the single CSV export; printing; charts/dashboards.
- Multi-user concurrency, networking, or any server/back-office component.

### 3.3 User classes / actors
| Class | Description | Source |
|-------|-------------|--------|
| Authenticated user | Any person who can sign in with valid credentials. Has full access to search, view, and export. There is no differentiated permission level. | [Views/SearchForm.cs:14-20](../Views/SearchForm.cs#L14-L20) |
| Administrator (`admin`) | The built-in seeded account. Technically identical in capability to any other user — "administrator" is a name only, not a privilege tier. | [Database/DatabaseHelper.cs:41-53](../Database/DatabaseHelper.cs#L41-L53) |

> `OPEN QUESTION:` Is a single undifferentiated access level intentional, or is a
> future role model (e.g. who may see salary) expected? Salary is currently visible to
> every authenticated user (see BR-3).

---

## 4. Business Rules & Policies

| ID   | Rule | Notes | Source |
|------|------|-------|--------|
| BR-1 | Only authenticated users may access any employee data. | Enforced by requiring a successful login before the search screen opens. Mechanics in [TECH SEC-1](TECHNICAL_REQUIREMENTS_EmployeeSearch.md#4-authentication--security--c2). | [Program.cs:17-33](../Program.cs#L17-L33) |
| BR-2 | Employee records are viewed only — never modified through this app. | No create/update/delete path exists. | [Views/SearchForm.cs](../Views/SearchForm.cs), [Database/DatabaseHelper.cs](../Database/DatabaseHelper.cs) |
| BR-3 | Salary is shown to every authenticated user, formatted as whole-unit currency (no decimals). | Salary is **not** treated as confidential/restricted today. Formatting rule in [FUNC VR-9](FUNCTIONAL_REQUIREMENTS_EmployeeSearch.md#4-validation-rules). | [Models/Employee.cs:14](../Models/Employee.cs#L14) |
| BR-4 | All authenticated users have identical capabilities. | No permission gating anywhere in the code. | [Views/SearchForm.cs](../Views/SearchForm.cs) |
| BR-5 | Employment status is one of a fixed set: **Active**, **Inactive**, **On Leave**. | Used as a filter and drives colour coding. Values in [FUNC VR-4](FUNCTIONAL_REQUIREMENTS_EmployeeSearch.md#4-validation-rules). | [Views/SearchForm.Designer.cs:207](../Views/SearchForm.Designer.cs#L207) |
| BR-6 | An employee belongs to one department from a fixed set and holds one role from a fixed set. | Departments and roles are enumerated for filtering. Values in [FUNC VR-2, VR-3](FUNCTIONAL_REQUIREMENTS_EmployeeSearch.md#4-validation-rules). | [Views/SearchForm.Designer.cs:180,193](../Views/SearchForm.Designer.cs#L180) |
| BR-7 | A default administrator account (`admin`) exists out of the box, with a well-known default password. | Seeded on first run; credentials are displayed on the login screen. Flagged as a risk in [TECH §4](TECHNICAL_REQUIREMENTS_EmployeeSearch.md#4-authentication--security--c2). | [Database/DatabaseHelper.cs:48](../Database/DatabaseHelper.cs#L48), [Views/LoginForm.Designer.cs:145](../Views/LoginForm.Designer.cs#L145) |

---

## 5. Roles & Permissions

The application has **no differentiated authorization model**. Every authenticated
identity can perform every action. This is the AD-mappable model, stated in business
terms; enforcement mechanics are in
[TECH SEC-1](TECHNICAL_REQUIREMENTS_EmployeeSearch.md#4-authentication--security--c2).

| ID     | Role | Can do | Cannot do | Source |
|--------|------|--------|-----------|--------|
| ROLE-1 | Authenticated user (includes `admin`) | Sign in; search/filter employees; view all employee fields incl. salary; export CSV; log out. | Nothing is additionally restricted — there are no admin-only or elevated actions, and no data-hiding by role. | [Views/SearchForm.cs](../Views/SearchForm.cs), [Database/DatabaseHelper.cs:99-163](../Database/DatabaseHelper.cs#L99-L163) |

> `OPEN QUESTION:` (for C2 mapping) When AD groups replace the local account, which AD
> group(s) should grant access? Today the only "role" concept is membership in the
> `Users` table. See [TECH §10](TECHNICAL_REQUIREMENTS_EmployeeSearch.md#10-open-questions--assumptions--technical).

---

## 6. Glossary

| Term | Meaning |
|------|---------|
| Employee | A person in the company directory: name, department, role, status, email, phone, hire date, salary. |
| Department | The organizational unit an employee belongs to (Finance, HR, IT, Marketing, Operations). |
| Role | The employee's job function (Analyst, Coordinator, Designer, Developer, Manager). |
| Status | Employment state: Active, Inactive, or On Leave. |
| User | A person who can sign in to the application (distinct from an Employee record). |
| Administrator | The built-in `admin` sign-in account; not a privilege level. |
| Export | Saving the current result list as a CSV file. |

---

## 7. Open Questions & Assumptions (business-facing)

- `OPEN QUESTION:` Should salary visibility be restricted to certain roles/groups?
  Today it is visible to all authenticated users (BR-3).
- `OPEN QUESTION:` Is the read-only nature (no add/edit/delete of employees) the intended
  final scope, or a POC limitation? (BR-2)
- `OPEN QUESTION:` Who are the real user classes and which AD groups map to access? Today
  there is a single, undifferentiated access level (ROLE-1).
- `ASSUMPTION:` The 15 seeded employees and the `admin` account are sample/POC data, not
  the production dataset. In the modernized app the real database is reused as-is
  (see [TECH §2](TECHNICAL_REQUIREMENTS_EmployeeSearch.md#2-data-model--c1--existing-db-reused-as-is)).
- `ASSUMPTION:` No formal, documented business KPIs exist; objectives (BO-*) are inferred.

---

## 8. Traceability Index

| Requirement | Source |
|-------------|--------|
| BO-1 | [Database/DatabaseHelper.cs:110](../Database/DatabaseHelper.cs#L110) |
| BO-2 | [Program.cs:17-33](../Program.cs#L17-L33) |
| BO-3 | [Views/SearchForm.cs:54-75](../Views/SearchForm.cs#L54-L75) |
| BO-4 | [Views/SearchForm.cs:124-143](../Views/SearchForm.cs#L124-L143) |
| BR-1 | [Program.cs:17-33](../Program.cs#L17-L33) |
| BR-2 | [Views/SearchForm.cs](../Views/SearchForm.cs) |
| BR-3 | [Models/Employee.cs:14](../Models/Employee.cs#L14) |
| BR-4 | [Views/SearchForm.cs](../Views/SearchForm.cs) |
| BR-5 | [Views/SearchForm.Designer.cs:207](../Views/SearchForm.Designer.cs#L207) |
| BR-6 | [Views/SearchForm.Designer.cs:180](../Views/SearchForm.Designer.cs#L180) |
| BR-7 | [Database/DatabaseHelper.cs:48](../Database/DatabaseHelper.cs#L48) |
| ROLE-1 | [Views/SearchForm.cs](../Views/SearchForm.cs) |
