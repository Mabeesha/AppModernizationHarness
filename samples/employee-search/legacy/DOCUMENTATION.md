# Employee Search — Code Documentation

## Table of Contents

1. [Overview](#1-overview)
2. [Project Structure](#2-project-structure)
3. [Technology Stack](#3-technology-stack)
4. [Application Entry Point](#4-application-entry-point)
5. [Database Layer](#5-database-layer)
6. [Data Model](#6-data-model)
7. [Login Form](#7-login-form)
8. [Search Form](#8-search-form)
9. [End-to-End Application Flow](#9-end-to-end-application-flow)
10. [Security Design](#10-security-design)

---

## 1. Overview

Employee Search is a Windows desktop application built with **Windows Forms (WinForms)** on **.NET 8**. It provides two screens:

- A **login form** that authenticates users against a local database using hashed passwords.
- A **search form** where the authenticated user can filter and browse employee records using a combination of text input and dropdown filters.

The database is **SQLite**, an embedded file-based relational database. No server installation or network configuration is required — the database file (`employeesearch.db`) is created automatically the first time the app runs, alongside the executable.

Unlike WPF, WinForms has no markup language (XAML) — every control is created and configured directly in C#. This codebase follows the same `Form` / `Form.Designer.cs` split that Visual Studio's WinForms designer generates: the `.Designer.cs` file declares and configures controls (`InitializeComponent()`), and the main `.cs` file holds the event-handling logic. These files were hand-written here (no visual designer was available in this environment), but they follow exactly the same convention so the project opens and behaves normally in Visual Studio.

---

## 2. Project Structure

```
MT_POC2/
├── EmployeeSearch.csproj            # Project definition: SDK, target framework, NuGet packages
├── Program.cs                       # Application entry point: Main(), login/search loop
│
├── Database/
│   └── DatabaseHelper.cs            # All database operations: init, login, search
│
├── Models/
│   └── Employee.cs                  # C# class that represents one row from the Employees table
│
└── Views/
    ├── LoginForm.cs                 # Login screen logic
    ├── LoginForm.Designer.cs        # Login screen control declarations/layout
    ├── SearchForm.cs                # Search screen logic
    └── SearchForm.Designer.cs       # Search screen control declarations/layout
```

---

## 3. Technology Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| App framework | Windows Forms (.NET) | .NET 8 | Windows desktop UI |
| Database | SQLite | via NuGet | Embedded relational database |
| SQLite driver | Microsoft.Data.Sqlite | 8.0.0 | ADO.NET provider for SQLite |
| Password hashing | BCrypt.Net-Next | 4.0.3 | Secure one-way password hashing |

### EmployeeSearch.csproj

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <UseWindowsForms>true</UseWindowsForms>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="BCrypt.Net-Next" Version="4.0.3" />
    <PackageReference Include="Microsoft.Data.Sqlite" Version="8.0.0" />
  </ItemGroup>
</Project>
```

Key settings explained:

- **`OutputType = WinExe`** — Builds a Windows GUI executable (no console window).
- **`TargetFramework = net8.0-windows`** — Targets .NET 8 with Windows-specific APIs enabled. The `-windows` suffix is required for WinForms (and WPF).
- **`Nullable = enable`** — The C# nullable reference types feature is turned on. This means the compiler warns you if you use a potentially-null variable without checking it first.
- **`ImplicitUsings = enable`** — Common namespaces like `System`, `System.Collections.Generic`, and `System.Linq` are auto-imported into every file, so you don't need to write `using System;` at the top of everything.
- **`UseWindowsForms = true`** — Tells the SDK to include the WinForms framework (`System.Windows.Forms`, `System.Drawing`) and reference the Windows Desktop runtime.

---

## 4. Application Entry Point

**File:** `Program.cs`

```csharp
internal static class Program
{
    [STAThread]
    private static void Main()
    {
        Application.SetHighDpiMode(HighDpiMode.SystemAware);
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        DatabaseHelper.Initialize();

        while (true)
        {
            string? username;
            using (var loginForm = new LoginForm())
            {
                if (loginForm.ShowDialog() != DialogResult.OK)
                    break;

                username = loginForm.Username;
            }

            using var searchForm = new SearchForm(username!);
            Application.Run(searchForm);

            if (!searchForm.LoggedOut)
                break;
        }
    }
}
```

WinForms has no XAML startup URI — `Main()` is the literal entry point, just like a console app. `[STAThread]` marks the thread as Single-Threaded Apartment, which Windows requires for UI components (COM-based controls like `DataGridView` and clipboard/drag-drop interop depend on it).

`Application.EnableVisualStyles()` turns on the modern (themed) rendering of standard controls (buttons, scrollbars, etc.) instead of the classic Windows 98-style look. `SetCompatibleTextRenderingDefault(false)` selects GDI+ text rendering, the recommended default for new applications.

`DatabaseHelper.Initialize()` is called once, before any form is shown, to guarantee the SQLite database file and tables exist before the login form tries to query it.

**The login/search loop.** This is the most important architectural difference from a typical single-window app. `Application.Run(form)` does not just show a window — it starts the Windows message loop and **does not return until that specific form closes**. If `SearchForm` were passed directly to `Application.Run()` as the app's only top-level form, closing it (e.g., via Logout) would end the entire application, with no way to cycle back to the login screen.

The fix used here is a `while (true)` loop with two different display mechanisms:

1. **`LoginForm` is shown modally** with `loginForm.ShowDialog()`. This blocks the calling code (not the whole app) until the login form closes, and returns a `DialogResult` indicating how it closed. If the result isn't `DialogResult.OK` (i.e., the user closed the window without logging in), the loop `break`s and the app exits.
2. **`SearchForm` is run as the "main" form** via `Application.Run(searchForm)`. When the user logs out, `SearchForm` sets `LoggedOut = true` and calls `Close()`. This ends `Application.Run()`, control returns to the `while` loop, and — because `LoggedOut` is `true` — the loop iterates again, showing `LoginForm` once more. If the user instead closes `SearchForm` directly (e.g., the window's `X` button) without logging out, `LoggedOut` stays `false` and the loop `break`s, exiting the app.

Each `using` block disposes the form (releasing its window handle and GDI resources) as soon as it's no longer needed, which is important since the loop can create many `LoginForm`/`SearchForm` instances over a long-running session (one login/logout cycle = one of each).

---

## 5. Database Layer

**File:** `Database/DatabaseHelper.cs`

This file is unchanged from the original WPF version — it has no dependency on any UI framework, so it carried over to WinForms verbatim.

`DatabaseHelper` is a `static` class — it has no instance and all its methods are called directly, like `DatabaseHelper.Initialize()`. It is responsible for every interaction with the SQLite database.

### Database location

```csharp
private static readonly string DbPath = Path.Combine(
    AppDomain.CurrentDomain.BaseDirectory,
    "employeesearch.db"
);
private static string ConnectionString => $"Data Source={DbPath}";
```

`AppDomain.CurrentDomain.BaseDirectory` returns the folder where the compiled `.exe` lives (e.g., `bin\Debug\net8.0-windows\`). The database file is therefore placed in the same folder as the executable, making the application self-contained with no fixed installation path.

`ConnectionString` is a computed property (note the `=>` arrow) rather than a stored string, so it always reflects the current `DbPath` value.

### Initialize()

```csharp
public static void Initialize()
{
    using var conn = new SqliteConnection(ConnectionString);
    conn.Open();

    var cmd = conn.CreateCommand();
    cmd.CommandText = @"
        CREATE TABLE IF NOT EXISTS Users (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT NOT NULL UNIQUE,
            PasswordHash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Employees (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            ...
        );";
    cmd.ExecuteNonQuery();

    SeedAdminUser(conn);
    SeedEmployees(conn);
}
```

`using var conn` — The `using` keyword here ensures that the database connection is automatically closed and its resources released when execution leaves the block, even if an exception occurs. This is the standard safe pattern for working with database connections in .NET.

`CREATE TABLE IF NOT EXISTS` — This SQL clause means "only create the table if it doesn't already exist." This makes `Initialize()` safe to call on every startup: on the first run it creates the tables, on all subsequent runs it is a no-op.

**The two tables created:**

- **`Users`** — Stores login credentials. `Username` has a `UNIQUE` constraint, preventing duplicate accounts. `PasswordHash` stores the BCrypt hash of the password, never the plain text.
- **`Employees`** — Stores the employee records that are searched and displayed.

### SeedAdminUser(conn)

```csharp
private static void SeedAdminUser(SqliteConnection conn)
{
    var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT COUNT(*) FROM Users WHERE Username = 'admin'";
    var count = (long)(cmd.ExecuteScalar() ?? 0L);
    if (count > 0) return;

    var hash = BCrypt.Net.BCrypt.HashPassword("admin123");
    cmd = conn.CreateCommand();
    cmd.CommandText = "INSERT INTO Users (Username, PasswordHash) VALUES ('admin', @hash)";
    cmd.Parameters.AddWithValue("@hash", hash);
    cmd.ExecuteNonQuery();
}
```

This method inserts the default admin account only if it does not already exist (the `COUNT(*)` check). This prevents re-inserting the user on every startup.

`BCrypt.Net.BCrypt.HashPassword("admin123")` runs the BCrypt algorithm on the plain-text password and returns a string that looks like `$2a$11$...`. This hash is what gets stored in the database. The original password `admin123` is never stored anywhere.

`cmd.Parameters.AddWithValue("@hash", hash)` — The `@hash` is a **named parameter placeholder**. The actual value is bound separately by `AddWithValue`. This is parameterized querying, which prevents SQL injection (see [Security Design](#10-security-design)).

`ExecuteScalar()` returns the first column of the first row of the result. For a `COUNT(*)` query, this is a single integer. SQLite returns it as a `long` (64-bit integer), so the cast `(long)` is applied. The `?? 0L` handles the case where `ExecuteScalar()` returns `null` (e.g., on an empty table) by defaulting to zero.

### SeedEmployees(conn)

```csharp
private static void SeedEmployees(SqliteConnection conn)
{
    var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT COUNT(*) FROM Employees";
    var count = (long)(cmd.ExecuteScalar() ?? 0L);
    if (count > 0) return;

    var rows = new (string Name, string Dept, string Role, ...) []
    {
        ("Alice Johnson", "IT", "Developer", "Active", ...),
        ...
    };

    foreach (var r in rows)
    {
        var ins = conn.CreateCommand();
        ins.CommandText = @"INSERT INTO Employees (...) VALUES (@n, @d, @r, ...)";
        ins.Parameters.AddWithValue("@n", r.Name);
        ...
        ins.ExecuteNonQuery();
    }
}
```

Same guard-and-seed pattern as `SeedAdminUser`. The employee data is defined as an array of **C# value tuples** — a concise way to group related values without needing a full class. Each tuple holds all fields for one employee row. The `foreach` loop then inserts each tuple as a parameterized SQL statement.

### ValidateLogin(username, password)

```csharp
public static bool ValidateLogin(string username, string password)
{
    using var conn = new SqliteConnection(ConnectionString);
    conn.Open();
    var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT PasswordHash FROM Users WHERE Username = @u";
    cmd.Parameters.AddWithValue("@u", username);
    var hash = cmd.ExecuteScalar() as string;
    return hash != null && BCrypt.Net.BCrypt.Verify(password, hash);
}
```

This method performs login authentication in two steps:

1. **Lookup:** Query the database for the `PasswordHash` row where `Username` matches the input. If no row is found, `ExecuteScalar()` returns `null`, and the `as string` cast safely produces `null` (rather than throwing an exception).

2. **Verify:** `BCrypt.Net.BCrypt.Verify(password, hash)` re-runs the BCrypt algorithm on the plain-text input using the stored hash's embedded salt, and checks if the result matches. This is the correct way to verify BCrypt passwords — you cannot decrypt a BCrypt hash; you can only verify against it.

The method returns `false` in two cases: the username does not exist (`hash == null`), or the password does not match. Both cases produce the same generic error message in the UI, intentionally not revealing which one failed (this prevents username enumeration).

### SearchEmployees(name, department, role, status)

```csharp
public static List<Employee> SearchEmployees(
    string? name, string? department, string? role, string? status)
{
    var results = new List<Employee>();
    using var conn = new SqliteConnection(ConnectionString);
    conn.Open();

    var where = new List<string>();
    var cmd = conn.CreateCommand();

    if (!string.IsNullOrWhiteSpace(name))
    {
        where.Add("Name LIKE @name");
        cmd.Parameters.AddWithValue("@name", $"%{name.Trim()}%");
    }
    if (!string.IsNullOrWhiteSpace(department) && department != "All")
    {
        where.Add("Department = @dept");
        cmd.Parameters.AddWithValue("@dept", department);
    }
    // ... same pattern for role and status

    var sql = "SELECT Id, Name, ... FROM Employees";
    if (where.Count > 0)
        sql += " WHERE " + string.Join(" AND ", where);
    sql += " ORDER BY Name";

    cmd.CommandText = sql;
    using var reader = cmd.ExecuteReader();
    while (reader.Read())
    {
        results.Add(new Employee { Id = reader.GetInt32(0), ... });
    }
    return results;
}
```

This method builds a SQL query **dynamically** based on which filters have values. The approach works as follows:

- A `List<string>` called `where` accumulates SQL condition fragments (e.g., `"Name LIKE @name"`).
- For each filter that is non-empty and not set to `"All"`, a fragment is added to `where` and a corresponding parameter is added to the command.
- After all filters are checked, the fragments are joined with `" AND "` and appended to the base `SELECT` statement.
- If no filters are active, the `WHERE` clause is omitted entirely, returning all employees.

`LIKE @name` with the value `%alice%` performs a **case-insensitive partial match** — it finds any name that contains "alice" anywhere in it, regardless of capitalisation.

`reader.IsDBNull(5)` checks whether a column value is `NULL` in the database before reading it. Columns like `Email` and `Phone` are not marked `NOT NULL` in the schema, so this guard prevents a runtime exception when those fields are empty.

`ExecuteReader()` returns a `SqliteDataReader`, which works like a cursor. Each call to `reader.Read()` advances it to the next row and returns `false` when all rows are exhausted. `GetInt32(0)`, `GetString(1)`, etc. read column values by their zero-based column index matching the `SELECT` order.

---

## 6. Data Model

**File:** `Models/Employee.cs`

```csharp
public class Employee
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public string Department { get; set; } = "";
    public string Role { get; set; } = "";
    public string Status { get; set; } = "";
    public string Email { get; set; } = "";
    public string Phone { get; set; } = "";
    public string HireDate { get; set; } = "";
    public double Salary { get; set; }
    public string SalaryFormatted => Salary.ToString("C0");
}
```

`Employee` is a plain C# class (a POCO — Plain Old CLR Object). Its properties map one-to-one to the columns in the `Employees` database table. This class also carried over unchanged from the WPF version.

`= ""` on the string properties are **default value initialisers**. Because `Nullable = enable` is set in the project, the compiler would warn that a string property might be `null` unless we either mark it nullable (`string?`) or give it a non-null default. The `= ""` is the cleaner choice here, since these fields always have database values.

`SalaryFormatted` is a **computed property** (read-only, no setter). It has no backing field; it calculates its value on demand by formatting the `Salary` double using the `"C0"` format specifier, which produces a locale-aware currency string with no decimal places (e.g., `$85,000` on a US system).

In WinForms, this property is mapped to a `DataGridView` column via `DataPropertyName = "SalaryFormatted"` (see [Search Form](#8-search-form)), keeping the formatting logic in the model rather than in the UI — the same separation of concerns the WPF version used with its `{Binding SalaryFormatted}` XAML expression.

---

## 7. Login Form

**Files:** `Views/LoginForm.cs`, `Views/LoginForm.Designer.cs`

WinForms has no XAML — every visual element is constructed in code inside `InitializeComponent()`, in `LoginForm.Designer.cs`. This file is meant to be regenerated by Visual Studio's designer when you drag controls onto the form; here it's written by hand but follows the same conventions (field per control, all set up in one method, called once from the constructor).

### Window setup

```csharp
ClientSize = new Size(420, 520);
FormBorderStyle = FormBorderStyle.FixedDialog;
MaximizeBox = false;
MinimizeBox = false;
StartPosition = FormStartPosition.CenterScreen;
Text = "Employee Search — Login";
```

`FormBorderStyle.FixedDialog` produces a non-resizable window with a dialog-style border (no maximize affordance even before `MaximizeBox` is set). `StartPosition.CenterScreen` centers the window on the primary monitor when it first appears — the WinForms equivalent of WPF's `WindowStartupLocation="CenterScreen"`.

### Background gradient

WinForms has no `LinearGradientBrush` markup; the equivalent visual effect is done by overriding a paint method in `LoginForm.cs`:

```csharp
protected override void OnPaintBackground(PaintEventArgs e)
{
    using var brush = new LinearGradientBrush(
        ClientRectangle,
        ColorTranslator.FromHtml("#1B2A4A"),
        ColorTranslator.FromHtml("#2B5278"),
        45f);
    e.Graphics.FillRectangle(brush, ClientRectangle);
}
```

`OnPaintBackground` is called by WinForms before the normal `OnPaint`, specifically to draw the form's background. `LinearGradientBrush` (from `System.Drawing.Drawing2D`, GDI+) takes a rectangle, two colors, and an angle (`45f` degrees) and produces a smooth diagonal gradient — the direct GDI+ analog of WPF's XAML `<LinearGradientBrush>`. `ColorTranslator.FromHtml("#1B2A4A")` converts a CSS-style hex string into a `System.Drawing.Color`, so the same color values from the original WPF design could be reused as-is.

### The card panel

Unlike WPF's `Border` with `CornerRadius`, WinForms' `Panel` control has no built-in rounded corners or drop shadow — those are XAML/visual-effect features without a direct WinForms equivalent. The card here is a plain white `Panel` with square corners:

```csharp
panelCard.BackColor = Color.White;
panelCard.Location = new Point(40, 50);
panelCard.Size = new Size(340, 410);
```

All other controls (icon label, title, subtitle, username/password fields, error label, sign-in button, hint label) are added as children of `panelCard` via `panelCard.Controls.Add(...)`, each manually positioned with a `Location` and `Size` (WinForms has no automatic flow layout unless you opt into a `FlowLayoutPanel` or `TableLayoutPanel`; this form uses fixed coordinates since its size never changes).

### Login logic

**File:** `Views/LoginForm.cs`

```csharp
public partial class LoginForm : Form
{
    public string? Username { get; private set; }

    public LoginForm()
    {
        InitializeComponent();
        txtUsername.Focus();
    }
```

`InitializeComponent()` must be the first call in the constructor — it builds every control declared in the `.Designer.cs` partial class. `txtUsername.Focus()` then places the keyboard cursor in the username field.

`Username` is a public, externally-readable property that `Program.cs` reads after the dialog closes successfully — this is how the chosen username is passed out of the modal form without any other coupling between `Program.cs` and `LoginForm`.

```csharp
private void AttemptLogin()
{
    var username = txtUsername.Text.Trim();
    var password = txtPassword.Text;

    if (string.IsNullOrWhiteSpace(username) || string.IsNullOrWhiteSpace(password))
    {
        ShowError("Please enter both username and password.");
        return;
    }

    if (!DatabaseHelper.ValidateLogin(username, password))
    {
        ShowError("Invalid username or password. Please try again.");
        txtPassword.Clear();
        txtPassword.Focus();
        return;
    }

    Username = username;
    DialogResult = DialogResult.OK;
    Close();
}
```

WinForms has no separate `PasswordBox` type — a regular `TextBox` is used with `UseSystemPasswordChar = true` (set in the Designer file), which masks the displayed characters while still exposing the real text through `.Text`, unlike WPF's `PasswordBox.Password` property which is intentionally non-bindable.

On success, setting `DialogResult = DialogResult.OK` is what makes `loginForm.ShowDialog()` in `Program.cs` return `DialogResult.OK` — this is the standard WinForms pattern for a modal form to report its outcome to its caller, replacing the WPF version's direct `new SearchWindow(username).Show()` call. `Close()` then ends the modal loop.

```csharp
private void Input_KeyDown(object? sender, KeyEventArgs e)
{
    if (e.KeyCode == Keys.Enter)
    {
        e.SuppressKeyPress = true;
        AttemptLogin();
    }
}
```

Both `txtUsername` and `txtPassword` subscribe to this same `KeyDown` handler (wired up in the Designer file), so pressing Enter in either field submits the form — the same UX as the WPF version. `e.SuppressKeyPress = true` prevents the Enter key from also producing a "ding" system sound or inserting a newline-like side effect in the text box.

---

## 8. Search Form

**Files:** `Views/SearchForm.cs`, `Views/SearchForm.Designer.cs`

### Layout via Dock

WPF's `Grid` with `RowDefinitions` (fixed/auto/star heights) has no direct WinForms equivalent; the closest analog is the `Dock` property, which docks a control against an edge of its parent and shrinks the remaining client area for whatever's added next:

```csharp
panelHeader.Dock = DockStyle.Top;     // docked first → claims the top strip
panelFilters.Dock = DockStyle.Top;    // docked second → claims the next strip down
panelStatus.Dock = DockStyle.Bottom;  // claims a strip at the bottom
dgvResults.Dock = DockStyle.Fill;     // takes whatever space is left
```

**Important WinForms quirk:** dock processing order follows the order controls are added to the `Controls` collection, not the order their `Dock` property is set. In `InitializeComponent()`, the controls are added in this exact order at the end of the method:

```csharp
Controls.Add(panelHeader);
Controls.Add(panelFilters);
Controls.Add(panelStatus);
Controls.Add(dgvResults);
```

Because `panelHeader` is added first, it claims the top strip of the *entire* client area. `panelFilters`, added second, then docks to the top of what remains (i.e., directly below the header). `panelStatus` claims a strip off the bottom of what's left after that. Finally `dgvResults`, with `Dock = DockStyle.Fill`, expands to consume whatever rectangle remains — conceptually the same effect as WPF's `Height="*"` row, but driven by add-order rather than declarative row sizing.

### Tab order vs. dock order — a real bug and its fix

`TabIndex` in WinForms is scoped **per container**: it only orders siblings within the same parent. Setting `txtName.TabIndex = 0` only matters relative to other controls inside `panelFilters`; it says nothing about whether `panelFilters` itself is visited before or after `panelHeader` in the overall tab sequence.

During testing, this caused a real bug: because `panelHeader` (which contains `btnLogout`, a `TabStop`-enabled control) was added to the Form's `Controls` collection first, WinForms gave it the lowest top-level `TabIndex` by default — meaning **`btnLogout` received initial keyboard focus when the form opened**, not the name filter textbox. Typing a name and pressing Enter while focus was still on the Logout button caused the button's `Click` handler to fire instead of the search, immediately logging the user out and bouncing back to the login screen.

The fix has two parts:

1. **Explicit initial focus**, set in `SearchForm.cs`:
   ```csharp
   protected override void OnLoad(EventArgs e)
   {
       base.OnLoad(e);
       txtName.Focus();
   }
   ```
   `OnLoad` runs after the form's window handle has been created, which is required for `.Focus()` to take effect reliably — calling `.Focus()` directly in the constructor (before the handle exists, especially for a non-modal form later run via `Application.Run()`) is unreliable.

2. **Explicit top-level `TabIndex` values**, set at the end of `InitializeComponent()`:
   ```csharp
   panelFilters.TabIndex = 0;
   dgvResults.TabIndex = 1;
   panelStatus.TabIndex = 2;
   panelHeader.TabIndex = 3;
   ```
   This explicitly pushes `panelHeader` (and therefore `btnLogout`) to the *end* of the overall Tab key cycle, regardless of dock/add order, so that tabbing through the form from the filters never lands on Logout by surprise.

### DataGridView column setup

WPF's `DataGrid` with `AutoGenerateColumns="False"` and `DataGridTextColumn` has a near-identical WinForms counterpart:

```csharp
dgvResults.AutoGenerateColumns = false;
dgvResults.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
dgvResults.Columns.AddRange(
    new DataGridViewTextBoxColumn { Name = "Id", HeaderText = "#", DataPropertyName = "Id", FillWeight = 50 },
    new DataGridViewTextBoxColumn { Name = "Name", HeaderText = "Name", DataPropertyName = "Name", FillWeight = 160 },
    // ...
    new DataGridViewTextBoxColumn { Name = "Salary", HeaderText = "Salary", DataPropertyName = "SalaryFormatted", FillWeight = 110 }
);
```

`AutoGenerateColumns = false` disables WinForms' default behavior of creating one column per public property via reflection — the same reasoning as the WPF version, for full control over which columns appear and in what order.

`DataPropertyName` is the WinForms equivalent of WPF's `{Binding PropertyName}` — it tells the column which property on the bound object to read for each row. The Salary column reads `SalaryFormatted` rather than `Salary` directly, reusing the model's computed currency-formatting property exactly as the WPF version did.

`AutoSizeColumnsMode = Fill` combined with each column's `FillWeight` is the WinForms analog of WPF's `Width="*"` star-sizing: all columns share the available width proportionally to their `FillWeight`, rather than each having a fixed pixel width. A column with `FillWeight = 160` gets roughly twice the width of one with `FillWeight = 80`.

### Status color via CellFormatting

WPF used a `DataGridTemplateColumn` with `DataTrigger`s to render a colored pill badge per status value. WinForms' plain `DataGridViewTextBoxColumn` has no per-value template system; instead, the `CellFormatting` event is used to inspect and recolor a cell just before it's painted:

```csharp
private void dgvResults_CellFormatting(object? sender, DataGridViewCellFormattingEventArgs e)
{
    if (dgvResults.Columns[e.ColumnIndex].Name != "Status" || e.Value is not string status || e.CellStyle is null)
        return;

    e.CellStyle.BackColor = status switch
    {
        "Active" => ColorTranslator.FromHtml("#D1FAE5"),
        "Inactive" => ColorTranslator.FromHtml("#FEE2E2"),
        "On Leave" => ColorTranslator.FromHtml("#FEF3C7"),
        _ => ColorTranslator.FromHtml("#E5E7EB"),
    };
    e.CellStyle.ForeColor = status switch
    {
        "Active" => ColorTranslator.FromHtml("#065F46"),
        "Inactive" => ColorTranslator.FromHtml("#991B1B"),
        "On Leave" => ColorTranslator.FromHtml("#92400E"),
        _ => ColorTranslator.FromHtml("#374151"),
    };
}
```

This event fires once per visible cell, every time the grid repaints. The handler first filters to only the `Status` column, guards against a non-string or null value, and against `e.CellStyle` itself being `null` (its type is nullable on the event args). It then uses a C# `switch` expression — functionally equivalent to WPF's `DataTrigger` list — to pick a background/foreground color pair matching the cell's text value, falling back to a neutral grey (`_ =>`) for any unrecognized status. This produces the same colored-badge visual effect as the WPF version, just driven by an event handler instead of declarative markup.

### Search logic

**File:** `Views/SearchForm.cs`

```csharp
public SearchForm(string username)
{
    InitializeComponent();
    _username = username;
    lblUser.Text = $"Logged in as: {username}";
    RunSearch();
}
```

The constructor receives the logged-in username from `Program.cs` (passed from `LoginForm.Username`) and calls `RunSearch()` immediately, so the grid is populated with all employees as soon as the form opens — same behavior as the WPF version.

```csharp
private void RunSearch()
{
    var name = txtName.Text.Trim();
    var department = cboDepartment.SelectedItem?.ToString();
    var role = cboRole.SelectedItem?.ToString();
    var status = cboStatus.SelectedItem?.ToString();

    var results = DatabaseHelper.SearchEmployees(name, department, role, status);

    dgvResults.DataSource = results;

    lblStatus.Text = results.Count == 0
        ? "No employees match the selected filters."
        : $"{results.Count} employee{(results.Count == 1 ? "" : "s")} found.";
}
```

Reading a WinForms `ComboBox`'s selection is simpler than WPF's: because the dropdown items are added as plain strings (`cboDepartment.Items.AddRange(new object[] { "All", "Finance", ... })`), `SelectedItem?.ToString()` returns the selected string directly — no cast to a `ComboBoxItem` wrapper and `.Content` lookup is needed, unlike the WPF version which used XAML `<ComboBoxItem>` elements.

`dgvResults.DataSource = results` is the WinForms equivalent of WPF's `ResultsGrid.ItemsSource = results` — assigning a `List<Employee>` directly rebinds the grid, regenerating its rows from the new list.

There is no separate "empty state" panel in the WinForms version (the WPF version toggled visibility between the `DataGrid` and an `EmptyState` panel) — when there are zero results, the grid simply renders with no rows, and the status bar label communicates the "no results" message instead.

```csharp
private void Filter_KeyDown(object? sender, KeyEventArgs e)
{
    if (e.KeyCode == Keys.Enter)
    {
        e.SuppressKeyPress = true;
        RunSearch();
    }
}
```

This handler is wired to `txtName.KeyDown` (set in the Designer file), letting Enter in the name field trigger a search — same UX as the WPF version's input fields.

```csharp
private void btnClear_Click(object? sender, EventArgs e)
{
    txtName.Clear();
    cboDepartment.SelectedIndex = 0;
    cboRole.SelectedIndex = 0;
    cboStatus.SelectedIndex = 0;
    RunSearch();
}
```

Resets all filters (index 0 is always `"All"` in each dropdown's item list) and re-runs the search, mirroring the WPF `ClearButton_Click` logic exactly.

```csharp
private void btnLogout_Click(object? sender, EventArgs e)
{
    LoggedOut = true;
    Close();
}
```

Unlike the WPF version (which directly created and showed a new `LoginWindow` here), the WinForms version just sets the public `LoggedOut` flag and closes itself — the actual decision to show `LoginForm` again lives in `Program.cs`'s loop (see [Application Entry Point](#4-application-entry-point)). This keeps `SearchForm` from needing to know anything about navigation; it just reports its own exit reason.

### Exporting results to CSV

**Files:** `Views/SearchForm.Designer.cs` (button), `Views/SearchForm.cs` (export logic)

A second button, `btnExport`, sits directly below `btnLogout` in `panelHeader`:

```csharp
btnExport.Anchor = AnchorStyles.Top | AnchorStyles.Right;
btnExport.BackColor = ColorTranslator.FromHtml("#217346");  // Excel brand green
btnExport.FlatStyle = FlatStyle.Flat;
btnExport.ForeColor = Color.White;
btnExport.Text = "\U0001F4CA  Export";
btnExport.Click += btnExport_Click;
```

The green background (`#217346`) and bar-chart icon (`\U0001F4CA`, 📊) intentionally echo Microsoft Excel's visual identity, since the button's job is conceptually "send this data to a spreadsheet."

Because `panelHeader` now needs to fit two stacked button rows (Logout, then Export) instead of one, its `Height` was increased from 60 to 100, and `lblHeaderTitle` was re-centered vertically within the taller panel. `panelHeader.Size` is still set explicitly (not just `Height`) before any `Anchor`-right child is configured — see the "Anchor capture timing" note below.

**Tracking what's currently visible.** `SearchForm` keeps the last set of search results in a field:

```csharp
private List<Employee> _currentResults = new();
```

`RunSearch()` assigns this field at the same time it sets `dgvResults.DataSource`, so `_currentResults` always mirrors exactly what's on screen — whatever filters (name/department/role/status) were last applied:

```csharp
var results = DatabaseHelper.SearchEmployees(name, department, role, status);
_currentResults = results;
dgvResults.DataSource = results;
```

**The export itself:**

```csharp
private void btnExport_Click(object? sender, EventArgs e)
{
    if (_currentResults.Count == 0)
    {
        MessageBox.Show(this, "There are no rows to export.", "Export to CSV",
            MessageBoxButtons.OK, MessageBoxIcon.Information);
        return;
    }

    using var dialog = new SaveFileDialog
    {
        Filter = "CSV files (*.csv)|*.csv",
        FileName = $"employees_{DateTime.Now:yyyyMMdd_HHmmss}.csv"
    };

    if (dialog.ShowDialog(this) != DialogResult.OK)
        return;

    File.WriteAllText(dialog.FileName, BuildCsv(_currentResults), Encoding.UTF8);

    lblStatus.Text = $"Exported {_currentResults.Count} employee{(_currentResults.Count == 1 ? "" : "s")} to {Path.GetFileName(dialog.FileName)}.";
}
```

A `SaveFileDialog` is the standard WinForms way to let the user pick a destination file/folder — it's the same OS-native dialog used by virtually every Windows application's "Save As." Restricting `Filter` to `*.csv` and pre-filling `FileName` with a timestamp avoids accidental overwrites between exports. If there are zero rows currently displayed (e.g., a filter combination matched nothing), the method short-circuits with a `MessageBox` instead of writing an empty file.

`BuildCsv` and `CsvField` do the actual formatting:

```csharp
private static string BuildCsv(List<Employee> rows)
{
    var sb = new StringBuilder();
    sb.AppendLine(string.Join(",", "Id", "Name", "Department", "Role", "Status", "Email", "Phone", "HireDate", "Salary"));

    foreach (var r in rows)
    {
        sb.AppendLine(string.Join(",",
            CsvField(r.Id), CsvField(r.Name), CsvField(r.Department), CsvField(r.Role),
            CsvField(r.Status), CsvField(r.Email), CsvField(r.Phone), CsvField(r.HireDate), CsvField(r.Salary)));
    }

    return sb.ToString();
}

private static string CsvField(object value)
{
    var text = value.ToString() ?? "";
    return text.Contains(',') || text.Contains('"') || text.Contains('\n')
        ? $"\"{text.Replace("\"", "\"\"")}\""
        : text;
}
```

This writes plain CSV by hand (no third-party CSV library is referenced in the project) following the relevant parts of RFC 4180: any field containing a comma, a double quote, or a newline is wrapped in double quotes, with internal double quotes doubled (`"` → `""`). Every other field is written as-is. The exported `Salary` column uses the raw numeric value (e.g. `85000`), not the `SalaryFormatted` currency string (`$85,000`) used in the on-screen grid — this keeps the CSV machine-readable (importable into Excel/Sheets as a number, not a formatted string) at the cost of not matching the grid's display formatting exactly.

**Anchor capture timing (why `panelHeader.Size` is set explicitly).** `lblUser`, `btnLogout`, and `btnExport` (and `btnSearch`/`btnClear` in `panelFilters`) all use `Anchor = AnchorStyles.Top | AnchorStyles.Right`. WinForms captures each anchored control's "distance to the parent's right edge" at the moment the control's bounds are set *relative to whatever size the parent currently has* — and `panelHeader`/`panelFilters` are `Dock.Top` panels that only get stretched to the form's full width once an actual layout pass runs, which is later than `InitializeComponent()` sets up these children. Without an explicit `Size` assignment up front, the captured anchor distances would be computed against the wrong (pre-Dock) width, and the controls would end up mispositioned — overlapping each other — once Dock resolves the real width. Setting `panelHeader.Size = new Size(1000, 100)` (matching `ClientSize.Width`) before any anchored child is configured sidesteps this entirely.

---

## 9. End-to-End Application Flow

```
dotnet run
    │
    ▼
Program.Main()
    │  DatabaseHelper.Initialize()
    │  ├─ Open/create employeesearch.db
    │  ├─ CREATE TABLE IF NOT EXISTS Users
    │  ├─ CREATE TABLE IF NOT EXISTS Employees
    │  ├─ SeedAdminUser()  → insert admin/admin123 if missing
    │  └─ SeedEmployees()  → insert 15 sample rows if missing
    │
    ▼
while (true) loop, iteration 1
    │
    ▼
new LoginForm().ShowDialog()   (modal)
    │  User types username + password
    │  Clicks "Sign In" or presses Enter
    │
    ▼
LoginForm.AttemptLogin()
    │  DatabaseHelper.ValidateLogin(username, password)
    │  ├─ SELECT PasswordHash WHERE Username = ?
    │  └─ BCrypt.Verify(plainText, hash)  → true/false
    │
    ├─ [FAIL] ShowError(), clear password field, dialog stays open
    │
    └─ [OK] Username set, DialogResult = OK, Close()
            ShowDialog() returns DialogResult.OK
                │
                ▼
            new SearchForm(username)
            Application.Run(searchForm)   (this form is now "main")
                │  lblUser shows "Logged in as: admin"
                │  OnLoad → txtName.Focus()
                │  RunSearch() called immediately (no filters)
                │  → all 15 employees loaded into DataGridView
                │
                │  User adjusts filters, clicks Search or presses Enter
                │
                ▼
            SearchForm.RunSearch()
                │  Reads txtName.Text, ComboBox selections
                │  DatabaseHelper.SearchEmployees(name, dept, role, status)
                │  ├─ Build dynamic WHERE clause
                │  ├─ Bind parameters
                │  ├─ Execute SELECT
                │  └─ Return List<Employee>
                │
                │  dgvResults.DataSource = results
                │  CellFormatting recolors Status cells
                │  Update lblStatus ("X employees found")
                │
                │  User clicks Logout
                ▼
            LoggedOut = true; Close()
            Application.Run() returns
                │
                ▼
while loop checks searchForm.LoggedOut == true → loop again → new LoginForm()

(If the user closes SearchForm via the window X instead of Logout,
 LoggedOut stays false and the while loop breaks → app exits.)
```

---

## 10. Security Design

This section is unchanged from the WPF version — none of the security-relevant logic lives in the UI layer, so converting frameworks had no effect on it.

### Passwords are never stored in plain text

The BCrypt algorithm is used for all password storage. When the admin account is seeded:

```
"admin123"  →  BCrypt.HashPassword()  →  "$2a$11$V3lF...randomhash..."
```

Only the hash is saved to the database. When a user logs in, BCrypt re-hashes the input and compares it to the stored hash — the original password cannot be recovered even if the database file is stolen.

BCrypt is deliberately slow (the `$11$` in the hash means 2^11 = 2048 iterations), which makes brute-force attacks computationally expensive.

### All queries use parameterized statements

No string concatenation is used to build SQL with user input. Every variable piece of data goes through `cmd.Parameters.AddWithValue("@param", value)`. This means the database driver handles escaping, so malicious input like:

```
username: admin' OR '1'='1
```

is treated as a literal string value, not as SQL syntax. SQL injection is structurally impossible with this pattern.

### Generic error messages

`ValidateLogin` returns a simple `bool`. The login form shows the same error message whether the username doesn't exist or the password is wrong. This is intentional — a message like "username not found" would allow an attacker to enumerate valid usernames by probing different values.

---

*Document generated for EmployeeSearch v2.0 — .NET 8 WinForms / SQLite*
