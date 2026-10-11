using System.Text;
using EmployeeSearch.Database;
using EmployeeSearch.Models;

namespace EmployeeSearch.Views;

public partial class SearchForm : Form
{
    private readonly string _username;
    private List<Employee> _currentResults = new();

    public bool LoggedOut { get; private set; }

    public SearchForm(string username)
    {
        InitializeComponent();
        _username = username;
        lblUser.Text = $"Logged in as: {username}";
        RunSearch();
    }

    protected override void OnLoad(EventArgs e)
    {
        base.OnLoad(e);
        txtName.Focus();
    }

    private void btnSearch_Click(object? sender, EventArgs e) => RunSearch();

    private void Filter_KeyDown(object? sender, KeyEventArgs e)
    {
        if (e.KeyCode == Keys.Enter)
        {
            e.SuppressKeyPress = true;
            RunSearch();
        }
    }

    private void btnClear_Click(object? sender, EventArgs e)
    {
        txtName.Clear();
        cboDepartment.SelectedIndex = 0;
        cboRole.SelectedIndex = 0;
        cboStatus.SelectedIndex = 0;
        RunSearch();
    }

    private void btnLogout_Click(object? sender, EventArgs e)
    {
        LoggedOut = true;
        Close();
    }

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

    private static string BuildCsv(List<Employee> rows)
    {
        var sb = new StringBuilder();
        sb.AppendLine(string.Join(",", "Id", "Name", "Department", "Role", "Status", "Email", "Phone", "HireDate", "Salary"));

        foreach (var r in rows)
        {
            sb.AppendLine(string.Join(",",
                CsvField(r.Id),
                CsvField(r.Name),
                CsvField(r.Department),
                CsvField(r.Role),
                CsvField(r.Status),
                CsvField(r.Email),
                CsvField(r.Phone),
                CsvField(r.HireDate),
                CsvField(r.Salary)));
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

    private void RunSearch()
    {
        var name = txtName.Text.Trim();
        var department = cboDepartment.SelectedItem?.ToString();
        var role = cboRole.SelectedItem?.ToString();
        var status = cboStatus.SelectedItem?.ToString();

        var results = DatabaseHelper.SearchEmployees(name, department, role, status);

        _currentResults = results;
        dgvResults.DataSource = results;

        lblStatus.Text = results.Count == 0
            ? "No employees match the selected filters."
            : $"{results.Count} employee{(results.Count == 1 ? "" : "s")} found.";
    }

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
}
