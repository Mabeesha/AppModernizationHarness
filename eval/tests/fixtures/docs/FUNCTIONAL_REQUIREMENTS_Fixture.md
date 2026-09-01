# Functional Requirements: Fixture

A minimal, fully conforming document used only by fault injection. Group G must report
nothing against it in the control pass; each injected defect breaks exactly one rule.

Keep it conforming. If a change here makes the control pass fail, the fixture is wrong, not
the checks.

## 1. Feature Overview

| ID | Feature | Screen |
|---|---|---|
| **FR-1** | Sign in | S-1 |
| **FR-2** | Search the directory | S-2 |

## 2. Detailed Features

### FR-1 — Sign in

**Purpose.** Verify a submitted username and password and admit the user to the directory.

**Trigger.** The user activates `Sign In`, or presses Enter in either credential field.

**Requirements.**

- **FR-1.1** When the user submits the sign-in form, Fixture shall trim leading and trailing
  whitespace from the username. (`Views/LoginForm.cs:41`)
- **FR-1.2** If the trimmed username is empty, then Fixture shall display `Please enter both
  username and password.` without attempting a credential lookup. (`Views/LoginForm.cs:44`)
- **FR-1.3** If credential verification fails, then Fixture shall clear the password field.
  (`Views/LoginForm.cs:50`)
- **FR-1.4** When credential verification succeeds, Fixture shall open the search screen.
  (`Program.cs:22`)

### FR-2 — Search the directory

**Purpose.** Return the employees matching the active filters.

**Requirements.**

- **FR-2.1** When the user submits a surname filter, Fixture shall return every employee
  whose surname contains the filter text, case-insensitively.
  (`Data/EmployeeRepository.cs:64`)
- **FR-2.2** While no filter is active, Fixture shall display the complete employee list.
  (`Views/SearchForm.cs:88`)
- **FR-2.3** If a search returns no rows, then Fixture shall display `No employees matched
  your search.` in the status line. (`Views/SearchForm.cs:112`)

## 3. Business Rules

| ID | Rule | Evidence |
|---|---|---|
| **BR-1** | The directory shall reject every request that carries no authenticated principal. | `Program.cs:17` |
| **BR-2** | Fixture shall store passwords only as a one-way hash. | `Database/DatabaseHelper.cs:48` |
