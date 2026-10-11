using System.IO;
using Microsoft.Data.Sqlite;
using EmployeeSearch.Models;

namespace EmployeeSearch.Database;

public static class DatabaseHelper
{
    private static readonly string DbPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "employeesearch.db");
    private static string ConnectionString => $"Data Source={DbPath}";

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
                Department TEXT NOT NULL,
                Role TEXT NOT NULL,
                Status TEXT NOT NULL,
                Email TEXT,
                Phone TEXT,
                HireDate TEXT,
                Salary REAL
            );";
        cmd.ExecuteNonQuery();

        SeedAdminUser(conn);
        SeedEmployees(conn);
    }

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

    private static void SeedEmployees(SqliteConnection conn)
    {
        var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT COUNT(*) FROM Employees";
        var count = (long)(cmd.ExecuteScalar() ?? 0L);
        if (count > 0) return;

        var rows = new (string Name, string Dept, string Role, string Status, string Email, string Phone, string Hire, double Salary)[]
        {
            ("Alice Johnson",   "IT",          "Developer",   "Active",   "alice@corp.com",   "555-0101", "2021-03-15", 85000),
            ("Bob Smith",       "HR",          "Manager",     "Active",   "bob@corp.com",     "555-0102", "2019-07-01", 92000),
            ("Carol White",     "Finance",     "Analyst",     "Active",   "carol@corp.com",   "555-0103", "2020-11-20", 78000),
            ("David Brown",     "Marketing",   "Coordinator", "On Leave", "david@corp.com",   "555-0104", "2022-01-10", 65000),
            ("Eva Martinez",    "IT",          "Developer",   "Active",   "eva@corp.com",     "555-0105", "2021-08-05", 88000),
            ("Frank Lee",       "Operations",  "Manager",     "Active",   "frank@corp.com",   "555-0106", "2018-05-22", 95000),
            ("Grace Kim",       "HR",          "Analyst",     "Inactive", "grace@corp.com",   "555-0107", "2020-04-17", 72000),
            ("Henry Davis",     "Finance",     "Manager",     "Active",   "henry@corp.com",   "555-0108", "2017-09-30",105000),
            ("Irene Wilson",    "IT",          "Designer",    "Active",   "irene@corp.com",   "555-0109", "2023-02-14", 80000),
            ("Jack Taylor",     "Marketing",   "Manager",     "Active",   "jack@corp.com",    "555-0110", "2019-12-01", 98000),
            ("Karen Anderson",  "Operations",  "Coordinator", "Active",   "karen@corp.com",   "555-0111", "2022-06-28", 62000),
            ("Liam Thompson",   "IT",          "Analyst",     "On Leave", "liam@corp.com",    "555-0112", "2021-05-19", 82000),
            ("Maya Patel",      "Finance",     "Coordinator", "Active",   "maya@corp.com",    "555-0113", "2023-08-07", 60000),
            ("Noah Garcia",     "Marketing",   "Designer",    "Active",   "noah@corp.com",    "555-0114", "2022-10-03", 74000),
            ("Olivia Chen",     "Operations",  "Analyst",     "Inactive", "olivia@corp.com",  "555-0115", "2020-07-25", 70000),
        };

        foreach (var r in rows)
        {
            var ins = conn.CreateCommand();
            ins.CommandText = @"
                INSERT INTO Employees (Name, Department, Role, Status, Email, Phone, HireDate, Salary)
                VALUES (@n, @d, @r, @s, @e, @p, @h, @sal)";
            ins.Parameters.AddWithValue("@n",   r.Name);
            ins.Parameters.AddWithValue("@d",   r.Dept);
            ins.Parameters.AddWithValue("@r",   r.Role);
            ins.Parameters.AddWithValue("@s",   r.Status);
            ins.Parameters.AddWithValue("@e",   r.Email);
            ins.Parameters.AddWithValue("@p",   r.Phone);
            ins.Parameters.AddWithValue("@h",   r.Hire);
            ins.Parameters.AddWithValue("@sal", r.Salary);
            ins.ExecuteNonQuery();
        }
    }

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

    public static List<Employee> SearchEmployees(string? name, string? department, string? role, string? status)
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
        if (!string.IsNullOrWhiteSpace(role) && role != "All")
        {
            where.Add("Role = @role");
            cmd.Parameters.AddWithValue("@role", role);
        }
        if (!string.IsNullOrWhiteSpace(status) && status != "All")
        {
            where.Add("Status = @status");
            cmd.Parameters.AddWithValue("@status", status);
        }

        var sql = "SELECT Id, Name, Department, Role, Status, Email, Phone, HireDate, Salary FROM Employees";
        if (where.Count > 0)
            sql += " WHERE " + string.Join(" AND ", where);
        sql += " ORDER BY Name";

        cmd.CommandText = sql;
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            results.Add(new Employee
            {
                Id         = reader.GetInt32(0),
                Name       = reader.GetString(1),
                Department = reader.GetString(2),
                Role       = reader.GetString(3),
                Status     = reader.GetString(4),
                Email      = reader.IsDBNull(5) ? "" : reader.GetString(5),
                Phone      = reader.IsDBNull(6) ? "" : reader.GetString(6),
                HireDate   = reader.IsDBNull(7) ? "" : reader.GetString(7),
                Salary     = reader.IsDBNull(8) ? 0  : reader.GetDouble(8),
            });
        }
        return results;
    }
}
