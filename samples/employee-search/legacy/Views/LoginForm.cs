using System.Drawing.Drawing2D;
using EmployeeSearch.Database;

namespace EmployeeSearch.Views;

public partial class LoginForm : Form
{
    public string? Username { get; private set; }

    public LoginForm()
    {
        InitializeComponent();
        lblTitle.Left = (panelCard.Width - lblTitle.Width) / 2;
        lblSubtitle.Left = (panelCard.Width - lblSubtitle.Width) / 2;
        txtUsername.Focus();
    }

    protected override void OnPaintBackground(PaintEventArgs e)
    {
        using var brush = new LinearGradientBrush(
            ClientRectangle,
            ColorTranslator.FromHtml("#1B2A4A"),
            ColorTranslator.FromHtml("#2B5278"),
            45f);
        e.Graphics.FillRectangle(brush, ClientRectangle);
    }

    private void btnLogin_Click(object? sender, EventArgs e) => AttemptLogin();

    private void Input_KeyDown(object? sender, KeyEventArgs e)
    {
        if (e.KeyCode == Keys.Enter)
        {
            e.SuppressKeyPress = true;
            AttemptLogin();
        }
    }

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

    private void ShowError(string message)
    {
        lblError.Text = message;
        lblError.Visible = true;
    }
}
