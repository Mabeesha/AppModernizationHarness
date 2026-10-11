# Employee Search

A Windows desktop application built with Windows Forms (WinForms, .NET 8) and SQLite. It provides a login screen backed by a local database and a searchable employee directory with filter controls.

---

## How to Run

### Prerequisites

- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8) (Windows)

### Run in development

```
cd MT_POC2
dotnet run
```

### Build a standalone executable

```
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true
```

Output: `bin\Release\net8.0-windows\win-x64\publish\EmployeeSearch.exe`

Double-click the `.exe` — no installation or .NET runtime required on the target machine.

### Default login credentials

| Username | Password  |
|----------|-----------|
| `admin`  | `admin123` |

---

## What the App Does

**Login screen** — Enter credentials and press Enter or click Sign In. Passwords are stored as BCrypt hashes; the plain-text password is never saved.

**Search screen** — Opens automatically after login showing all 15 sample employees. Use any combination of filters and click Search (or press Enter):

| Filter | Type | Behaviour |
|--------|------|-----------|
| Employee Name | Text box | Partial match, case-insensitive |
| Department | Dropdown | Exact match (IT, HR, Finance, Marketing, Operations) |
| Role | Dropdown | Exact match (Analyst, Coordinator, Designer, Developer, Manager) |
| Status | Dropdown | Exact match (Active, Inactive, On Leave) |

**Exporting results** — Click the green **Export** button (below Logout) to save the rows currently shown in the grid to a CSV file. A Save dialog lets you choose the file name/location; the default name is `employees_<timestamp>.csv`. Only the rows matching the active filters are exported — exporting after filtering by `Status = Active`, for example, writes only the active employees.

Results appear in a table with colour-coded status badges. Click **Clear** to reset all filters. Click **Export** to save the currently displayed rows (i.e. whatever the active filters show) to a CSV file. Click **Logout** to return to the login screen.

---

## Project Structure

```
MT_POC2/
├── Program.cs                       # App entry point; initialises the database; login/search loop
├── EmployeeSearch.csproj            # Project file: .NET 8 WinForms, NuGet packages
├── Database/
│   └── DatabaseHelper.cs            # All DB operations: init, login validation, search
├── Models/
│   └── Employee.cs                  # Data class bound to the results DataGridView
└── Views/
    ├── LoginForm.cs/.Designer.cs    # Login UI and authentication logic
    └── SearchForm.cs/.Designer.cs   # Filter panel, DataGridView, and search logic
```

**Database:** A SQLite file (`employeesearch.db`) is created automatically next to the executable on first run. No server or configuration needed.

**NuGet packages used:**
- `Microsoft.Data.Sqlite 8.0.0` — SQLite ADO.NET driver
- `BCrypt.Net-Next 4.0.3` — password hashing

---

## Security Notes

- Passwords are hashed with BCrypt (work factor 11) before storage — they cannot be recovered from the database file.
- All SQL queries use parameterized statements; SQL injection is not possible.
- Login errors return a generic message regardless of whether the username or password was wrong, preventing username enumeration.

---

For a detailed explanation of every file and design decision, see [DOCUMENTATION.md](DOCUMENTATION.md).
