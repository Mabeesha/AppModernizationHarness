# Functional Requirements: EmployeeSearch

> **Related documents:**
> - [Business Requirements](BUSINESS_REQUIREMENTS_EmployeeSearch.md) — *why*
> - [Technical Requirements](TECHNICAL_REQUIREMENTS_EmployeeSearch.md) — *how / constraints*

---

## 1. Overview

EmployeeSearch presents two screens: a **Login** screen and a **Search** screen. After a
user signs in (FR-1), the Search screen (UI-2) opens and immediately shows all employees
sorted by name (FR-2). The user narrows results with four filters — name, department,
role, status (FR-3) — clears filters (FR-4), exports the current results to CSV (FR-5),
or logs out (FR-6). Status values are colour-coded in the grid (FR-7). This document
realizes the business goals in [Business Requirements §2/§4](BUSINESS_REQUIREMENTS_EmployeeSearch.md#2-business-objectives).

---

## 2. Functional Requirements

### FR-1 — User login (realizes BO-2, BR-1)
- **Trigger:** App start (login is shown first), the **Sign In** button, or **Enter** in
  the username/password field. [Views/LoginForm.cs:28-37](../Views/LoginForm.cs#L28-L37)
- **Inputs:** Username (text), Password (masked text).
- **Logic:**
  1. Both fields are trimmed/checked; if username **or** password is empty/whitespace,
     show `"Please enter both username and password."` and stop (VR-10).
     [Views/LoginForm.cs:44-48](../Views/LoginForm.cs#L44-L48)
  2. Validate credentials against the `Users` table (BCrypt verify — see
     [TECH SEC-1/DA-1](TECHNICAL_REQUIREMENTS_EmployeeSearch.md#3-data-access--persistence)).
  3. On failure: show `"Invalid username or password. Please try again."`, clear the
     password field, and refocus it. [Views/LoginForm.cs:50-56](../Views/LoginForm.cs#L50-L56)
  4. On success: remember the username and open the Search screen.
- **Outputs:** Either an inline error, or navigation to the Search screen (UI-2).
- **Source:** [Views/LoginForm.cs:39-61](../Views/LoginForm.cs#L39-L61)

### FR-2 — Show all employees on entry (realizes BO-1)
- **Trigger:** Search screen construction (runs a search immediately with empty filters).
- **Logic:** Executes the search (FR-3) with no filters, returning all employees ordered
  by name. Populates the results grid and the status line.
- **Outputs:** Full employee list; status text `"<n> employee(s) found."` (VR-11).
- **Source:** [Views/SearchForm.cs:14-20](../Views/SearchForm.cs#L14-L20), [Views/SearchForm.cs:107-122](../Views/SearchForm.cs#L107-L122)

### FR-3 — Search / filter employees (realizes BO-1, BR-6, BR-5)
- **Trigger:** **Search** button, or **Enter** in the name field.
  [Views/SearchForm.cs:28-37](../Views/SearchForm.cs#L28-L37)
- **Inputs:** Employee Name (free text), Department (dropdown), Role (dropdown),
  Status (dropdown). See UI-2 for values.
- **Logic (VR-1):** Build a WHERE clause from only the *active* filters and combine with
  AND; results are ordered by Name ascending. Specifically:
  - **Name:** if non-empty, `Name LIKE %name%` (trimmed, case-insensitive per SQLite
    default — partial match).
  - **Department / Role / Status:** if the selection is not `"All"`, match exactly.
  - Any filter left blank or set to `"All"` is ignored.
- **Outputs:** Matching rows in the grid; status line updated (VR-11):
  `"No employees match the selected filters."` when empty, else `"<n> employee(s) found."`.
- **Source:** [Views/SearchForm.cs:107-122](../Views/SearchForm.cs#L107-L122), [Database/DatabaseHelper.cs:110-163](../Database/DatabaseHelper.cs#L110-L163)

### FR-4 — Clear filters (realizes BO-1)
- **Trigger:** **Clear** button. [Views/SearchForm.cs:39-46](../Views/SearchForm.cs#L39-L46)
- **Logic:** Reset name to empty and all three dropdowns to `"All"` (index 0), then
  re-run the search (FR-3), which returns all employees.
- **Outputs:** Full employee list restored.
- **Source:** [Views/SearchForm.cs:39-46](../Views/SearchForm.cs#L39-L46)

### FR-5 — Export current results to CSV (realizes BO-3)
- **Trigger:** **Export** button. [Views/SearchForm.cs:54-75](../Views/SearchForm.cs#L54-L75)
- **Inputs:** The current in-memory result set (whatever the last search returned).
- **Logic:**
  1. If there are **0** rows, show an information dialog `"There are no rows to export."`
     (title `"Export to CSV"`) and stop.
  2. Otherwise open a Save-file dialog filtered to `*.csv`, defaulting the file name to
     `employees_yyyyMMdd_HHmmss.csv` (timestamp = now).
  3. If the user cancels, do nothing.
  4. Build CSV content (RPT-1 / VR-12) and write it as UTF-8.
  5. Update the status line: `"Exported <n> employee(s) to <filename>."`.
- **Outputs:** A `.csv` file on disk; status confirmation.
- **Source:** [Views/SearchForm.cs:54-105](../Views/SearchForm.cs#L54-L105)

### FR-6 — Log out (realizes BR-1)
- **Trigger:** **Logout** button. [Views/SearchForm.cs:48-52](../Views/SearchForm.cs#L48-L52)
- **Logic:** Closes the Search screen and returns to the Login screen (a new sign-in can
  occur). Closing the Search screen by any other means (e.g. the window **X**) exits the
  application instead of returning to login.
- **Outputs:** Return to Login screen (UI-1), or application exit.
- **Source:** [Views/SearchForm.cs:48-52](../Views/SearchForm.cs#L48-L52), [Program.cs:17-33](../Program.cs#L17-L33)

### FR-7 — Status colour coding (realizes BO-4, BR-5)
- **Trigger:** Grid cell rendering for the **Status** column.
- **Logic (VR-5):** Each status renders with a fixed background/foreground colour;
  unknown values fall back to grey. Exact colours in VR-5.
- **Outputs:** Colour-coded Status cells.
- **Source:** [Views/SearchForm.cs:124-143](../Views/SearchForm.cs#L124-L143)

---

## 3. User Interface / Screens

### UI-1 — Login screen (`LoginForm`)
Purpose: authenticate a user. Fixed-size dialog (420×520), gradient background, centered
white card. Source: [Views/LoginForm.Designer.cs](../Views/LoginForm.Designer.cs)

| Control | Label / text | Type | Behaviour | Source |
|---------|--------------|------|-----------|--------|
| lblTitle | "Employee Search" | Label | Static heading. | [LoginForm.Designer.cs:82](../Views/LoginForm.Designer.cs#L82) |
| lblSubtitle | "Sign in to your account" | Label | Static. | [LoginForm.Designer.cs:89](../Views/LoginForm.Designer.cs#L89) |
| txtUsername | "Username" | TextBox | Required; focused on open; **Enter** submits. | [LoginForm.Designer.cs:98-102](../Views/LoginForm.Designer.cs#L98-L102) |
| txtPassword | "Password" | TextBox (masked) | Required; masked (`UseSystemPasswordChar`); **Enter** submits; cleared on failed login. | [LoginForm.Designer.cs:111-116](../Views/LoginForm.Designer.cs#L111-L116) |
| lblError | (dynamic) | Label | Hidden until an error; red text (#DC2626). | [LoginForm.Designer.cs:118-123](../Views/LoginForm.Designer.cs#L118-L123) |
| btnLogin | "Sign In" | Button | Triggers login (FR-1). | [LoginForm.Designer.cs:125-137](../Views/LoginForm.Designer.cs#L125-L137) |
| lblHint | "Default credentials: admin / admin123" | Label | **Static hint displaying real default credentials** — flagged as a security risk in [TECH §4](TECHNICAL_REQUIREMENTS_EmployeeSearch.md#4-authentication--security--c2). | [LoginForm.Designer.cs:139-145](../Views/LoginForm.Designer.cs#L139-L145) |

### UI-2 — Search screen (`SearchForm`)
Purpose: search, view, export employees. Resizable (default 1000×700, min 800×560). Three
regions: header, filters, results grid + status bar.
Source: [Views/SearchForm.Designer.cs](../Views/SearchForm.Designer.cs)

**Header**
| Control | Text | Behaviour | Source |
|---------|------|-----------|--------|
| lblHeaderTitle | "🔍  Employee Search" | Static. | [SearchForm.Designer.cs:89-95](../Views/SearchForm.Designer.cs#L89-L95) |
| lblUser | "Logged in as: <username>" | Shows current user. | [SearchForm.cs:18](../Views/SearchForm.cs#L18) |
| btnLogout | "Logout" | FR-6. | [SearchForm.Designer.cs:104-115](../Views/SearchForm.Designer.cs#L104-L115) |
| btnExport | "📊  Export" | FR-5; green (#217346). | [SearchForm.Designer.cs:119-131](../Views/SearchForm.Designer.cs#L119-L131) |

**Filters**
| Field | Label | Type | Values / behaviour | Source |
|-------|-------|------|--------------------|--------|
| txtName | "Employee Name" | TextBox | Free text; partial match; **Enter** searches. | [SearchForm.Designer.cs:159-168](../Views/SearchForm.Designer.cs#L159-L168) |
| cboDepartment | "Department" | Dropdown (list) | **All, Finance, HR, IT, Marketing, Operations** (default All). | [SearchForm.Designer.cs:176-181](../Views/SearchForm.Designer.cs#L176-L181) |
| cboRole | "Role" | Dropdown (list) | **All, Analyst, Coordinator, Designer, Developer, Manager** (default All). | [SearchForm.Designer.cs:189-194](../Views/SearchForm.Designer.cs#L189-L194) |
| cboStatus | "Status" | Dropdown (list) | **All, Active, Inactive, On Leave** (default All). | [SearchForm.Designer.cs:203-208](../Views/SearchForm.Designer.cs#L203-L208) |
| btnSearch | "🔍  Search" | Button | FR-3. | [SearchForm.Designer.cs:210-222](../Views/SearchForm.Designer.cs#L210-L222) |
| btnClear | "Clear" | Button | FR-4. | [SearchForm.Designer.cs:224-235](../Views/SearchForm.Designer.cs#L224-L235) |

**Results grid (`dgvResults`)** — read-only, single full-row select, no add/edit/delete,
alternating row shading, columns fill available width. Columns (in order):

| Header | Bound field | Format | Source |
|--------|-------------|--------|--------|
| # | Id | integer | [SearchForm.Designer.cs:277](../Views/SearchForm.Designer.cs#L277) |
| Name | Name | text | [SearchForm.Designer.cs:278](../Views/SearchForm.Designer.cs#L278) |
| Department | Department | text | [SearchForm.Designer.cs:279](../Views/SearchForm.Designer.cs#L279) |
| Role | Role | text | [SearchForm.Designer.cs:280](../Views/SearchForm.Designer.cs#L280) |
| Status | Status | text, colour-coded (VR-5) | [SearchForm.Designer.cs:281](../Views/SearchForm.Designer.cs#L281) |
| Email | Email | text | [SearchForm.Designer.cs:282](../Views/SearchForm.Designer.cs#L282) |
| Phone | Phone | text | [SearchForm.Designer.cs:283](../Views/SearchForm.Designer.cs#L283) |
| Hire Date | HireDate | text (stored as YYYY-MM-DD) | [SearchForm.Designer.cs:284](../Views/SearchForm.Designer.cs#L284) |
| Salary | SalaryFormatted | whole-unit currency, no decimals (VR-9) | [SearchForm.Designer.cs:285](../Views/SearchForm.Designer.cs#L285) |

**Status bar (`lblStatus`)** — one line of result/export feedback; initial text
`"Use filters above and click Search to find employees."`
[SearchForm.Designer.cs:243-247](../Views/SearchForm.Designer.cs#L243-L247)

---

## 4. Validation Rules

| ID | Rule | Exact constraint | Source |
|----|------|------------------|--------|
| VR-1 | Search filter combination | Active filters combined with **AND**; results **ORDER BY Name** asc. Blank/`"All"` filters omitted. | [Database/DatabaseHelper.cs:116-145](../Database/DatabaseHelper.cs#L116-L145) |
| VR-2 | Department filter values | `All, Finance, HR, IT, Marketing, Operations` | [SearchForm.Designer.cs:180](../Views/SearchForm.Designer.cs#L180) |
| VR-3 | Role filter values | `All, Analyst, Coordinator, Designer, Developer, Manager` | [SearchForm.Designer.cs:193](../Views/SearchForm.Designer.cs#L193) |
| VR-4 | Status filter values | `All, Active, Inactive, On Leave` | [SearchForm.Designer.cs:207](../Views/SearchForm.Designer.cs#L207) |
| VR-5 | Status colour coding (bg / fg) | Active `#D1FAE5`/`#065F46`; Inactive `#FEE2E2`/`#991B1B`; On Leave `#FEF3C7`/`#92400E`; other `#E5E7EB`/`#374151` | [SearchForm.cs:129-142](../Views/SearchForm.cs#L129-L142) |
| VR-6 | Name filter matching | `Name LIKE %<trimmed>%` (partial, case-insensitive per SQLite default). | [Database/DatabaseHelper.cs:119-123](../Database/DatabaseHelper.cs#L119-L123) |
| VR-7 | Department/Role/Status matching | Exact equality; skipped when value is `"All"` or blank. | [Database/DatabaseHelper.cs:124-138](../Database/DatabaseHelper.cs#L124-L138) |
| VR-8 | Result ordering | Always `ORDER BY Name`. | [Database/DatabaseHelper.cs:143](../Database/DatabaseHelper.cs#L143) |
| VR-9 | Salary display format | .NET `"C0"` — currency, **0 decimal places**, culture-dependent symbol/grouping. `ASSUMPTION:` runtime uses the machine locale. | [Models/Employee.cs:14](../Models/Employee.cs#L14) |
| VR-10 | Login required fields | Username **and** password must both be non-empty/non-whitespace; else error `"Please enter both username and password."` | [Views/LoginForm.cs:44-48](../Views/LoginForm.cs#L44-L48) |
| VR-11 | Result count message | 0 → `"No employees match the selected filters."`; else `"<n> employee(s) found."` (singular/plural). | [Views/SearchForm.cs:119-121](../Views/SearchForm.cs#L119-L121) |
| VR-12 | CSV field quoting | A field is quoted only if it contains `,`, `"`, or newline; embedded `"` doubled to `""`. | [Views/SearchForm.cs:99-105](../Views/SearchForm.cs#L99-L105) |

**State model:** There is no editable workflow/state machine. `Status` is a display/filter
attribute only (BR-5); the app never transitions an employee between statuses.

---

## 5. Reports & Exports

### RPT-1 — Employee CSV export (realizes BO-3; triggered by FR-5)
- **Trigger:** Export button (FR-5); requires ≥1 row in the current results.
- **File name:** `employees_yyyyMMdd_HHmmss.csv` (default; user may rename). Encoding UTF-8.
- **Content:** One header row then one row per employee **in the current filtered/sorted
  order**. Quoting per VR-12.
- **Columns (exact order):** `Id, Name, Department, Role, Status, Email, Phone, HireDate, Salary`
- **Note:** The `Salary` column is exported as the **raw numeric value** (e.g. `85000`),
  *not* the currency-formatted display value (VR-9 applies only to the on-screen grid).
- **Source:** [Views/SearchForm.cs:77-97](../Views/SearchForm.cs#L77-L97)

---

## 6. Open Questions & Assumptions (functional)

- `OPEN QUESTION:` Name search is a substring match (`%name%`). Is leading-wildcard search
  acceptable at production data volumes, or is prefix/exact match preferred? (VR-6)
- `OPEN QUESTION:` Closing the Search window via the title-bar **X** exits the app rather
  than returning to login — intended? (FR-6)
- `ASSUMPTION:` Salary currency symbol/format follows the runtime machine locale because
  `"C0"` is culture-dependent and no explicit culture is set. (VR-9)
- `ASSUMPTION:` HireDate is a display string in `YYYY-MM-DD` form (all seed data uses it);
  it is stored as text, not a date type — see
  [TECH DM-2](TECHNICAL_REQUIREMENTS_EmployeeSearch.md#2-data-model--c1--existing-db-reused-as-is).

---

## 7. Traceability Index

| Requirement | Source |
|-------------|--------|
| FR-1 | [Views/LoginForm.cs:39-61](../Views/LoginForm.cs#L39-L61) |
| FR-2 | [Views/SearchForm.cs:14-20](../Views/SearchForm.cs#L14-L20) |
| FR-3 | [Database/DatabaseHelper.cs:110-163](../Database/DatabaseHelper.cs#L110-L163) |
| FR-4 | [Views/SearchForm.cs:39-46](../Views/SearchForm.cs#L39-L46) |
| FR-5 | [Views/SearchForm.cs:54-105](../Views/SearchForm.cs#L54-L105) |
| FR-6 | [Views/SearchForm.cs:48-52](../Views/SearchForm.cs#L48-L52), [Program.cs:17-33](../Program.cs#L17-L33) |
| FR-7 | [Views/SearchForm.cs:124-143](../Views/SearchForm.cs#L124-L143) |
| UI-1 | [Views/LoginForm.Designer.cs](../Views/LoginForm.Designer.cs) |
| UI-2 | [Views/SearchForm.Designer.cs](../Views/SearchForm.Designer.cs) |
| VR-1..VR-8 | [Database/DatabaseHelper.cs:110-163](../Database/DatabaseHelper.cs#L110-L163) |
| VR-9 | [Models/Employee.cs:14](../Models/Employee.cs#L14) |
| VR-10 | [Views/LoginForm.cs:44-48](../Views/LoginForm.cs#L44-L48) |
| VR-11 | [Views/SearchForm.cs:119-121](../Views/SearchForm.cs#L119-L121) |
| VR-12 | [Views/SearchForm.cs:99-105](../Views/SearchForm.cs#L99-L105) |
| RPT-1 | [Views/SearchForm.cs:77-97](../Views/SearchForm.cs#L77-L97) |
