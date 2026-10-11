#nullable enable
namespace EmployeeSearch.Views;

partial class LoginForm
{
    private System.ComponentModel.IContainer? components = null;

    protected override void Dispose(bool disposing)
    {
        if (disposing && components != null) components.Dispose();
        base.Dispose(disposing);
    }

    private Panel panelCard = null!;
    private Label lblIcon = null!;
    private Label lblTitle = null!;
    private Label lblSubtitle = null!;
    private Label lblUsername = null!;
    private TextBox txtUsername = null!;
    private Label lblPassword = null!;
    private TextBox txtPassword = null!;
    private Label lblError = null!;
    private Button btnLogin = null!;
    private Label lblHint = null!;

    private void InitializeComponent()
    {
        panelCard = new Panel();
        lblIcon = new Label();
        lblTitle = new Label();
        lblSubtitle = new Label();
        lblUsername = new Label();
        txtUsername = new TextBox();
        lblPassword = new Label();
        txtPassword = new TextBox();
        lblError = new Label();
        btnLogin = new Button();
        lblHint = new Label();

        SuspendLayout();

        // LoginForm
        AutoScaleMode = AutoScaleMode.None;
        ClientSize = new Size(420, 520);
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        MinimizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        Text = "Employee Search — Login";
        Font = new Font("Segoe UI", 9F);

        // panelCard
        panelCard.BackColor = Color.White;
        panelCard.Location = new Point(40, 50);
        panelCard.Size = new Size(340, 410);
        panelCard.Controls.Add(lblIcon);
        panelCard.Controls.Add(lblTitle);
        panelCard.Controls.Add(lblSubtitle);
        panelCard.Controls.Add(lblUsername);
        panelCard.Controls.Add(txtUsername);
        panelCard.Controls.Add(lblPassword);
        panelCard.Controls.Add(txtPassword);
        panelCard.Controls.Add(lblError);
        panelCard.Controls.Add(btnLogin);
        panelCard.Controls.Add(lblHint);

        // lblIcon
        lblIcon.Font = new Font("Segoe UI Emoji", 18F);
        lblIcon.Location = new Point(0, 22);
        lblIcon.Size = new Size(340, 40);
        lblIcon.TextAlign = ContentAlignment.MiddleCenter;
        lblIcon.Text = "\U0001F50D";

        // lblTitle
        // AutoSize avoids GDI TextRenderer clipping the top of bold text when
        // a fixed Height is a touch too short for the font's metrics; centered
        // manually in the LoginForm constructor since the width is now dynamic.
        lblTitle.AutoSize = true;
        lblTitle.Font = new Font("Segoe UI", 16F, FontStyle.Bold);
        lblTitle.ForeColor = ColorTranslator.FromHtml("#1B2838");
        lblTitle.Location = new Point(0, 70);
        lblTitle.Text = "Employee Search";

        // lblSubtitle
        lblSubtitle.AutoSize = true;
        lblSubtitle.Font = new Font("Segoe UI", 9F);
        lblSubtitle.ForeColor = ColorTranslator.FromHtml("#6B7280");
        lblSubtitle.Location = new Point(0, 104);
        lblSubtitle.Text = "Sign in to your account";

        // lblUsername
        lblUsername.AutoSize = true;
        lblUsername.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
        lblUsername.ForeColor = ColorTranslator.FromHtml("#374151");
        lblUsername.Location = new Point(30, 144);
        lblUsername.Text = "Username";

        // txtUsername
        txtUsername.Font = new Font("Segoe UI", 10F);
        txtUsername.Location = new Point(30, 164);
        txtUsername.Size = new Size(280, 27);
        txtUsername.KeyDown += Input_KeyDown;

        // lblPassword
        lblPassword.AutoSize = true;
        lblPassword.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
        lblPassword.ForeColor = ColorTranslator.FromHtml("#374151");
        lblPassword.Location = new Point(30, 204);
        lblPassword.Text = "Password";

        // txtPassword
        txtPassword.Font = new Font("Segoe UI", 10F);
        txtPassword.Location = new Point(30, 224);
        txtPassword.Size = new Size(280, 27);
        txtPassword.UseSystemPasswordChar = true;
        txtPassword.KeyDown += Input_KeyDown;

        // lblError
        lblError.Font = new Font("Segoe UI", 8.5F);
        lblError.ForeColor = ColorTranslator.FromHtml("#DC2626");
        lblError.Location = new Point(30, 258);
        lblError.Size = new Size(280, 34);
        lblError.Visible = false;

        // btnLogin
        btnLogin.BackColor = ColorTranslator.FromHtml("#1B4F8A");
        btnLogin.FlatStyle = FlatStyle.Flat;
        btnLogin.FlatAppearance.BorderSize = 0;
        btnLogin.FlatAppearance.MouseOverBackColor = ColorTranslator.FromHtml("#154080");
        btnLogin.FlatAppearance.MouseDownBackColor = ColorTranslator.FromHtml("#0F3060");
        btnLogin.Font = new Font("Segoe UI", 10.5F, FontStyle.Bold);
        btnLogin.ForeColor = Color.White;
        btnLogin.Location = new Point(30, 302);
        btnLogin.Size = new Size(280, 42);
        btnLogin.Text = "Sign In";
        btnLogin.Cursor = Cursors.Hand;
        btnLogin.Click += btnLogin_Click;

        // lblHint
        lblHint.Font = new Font("Segoe UI", 8F);
        lblHint.ForeColor = ColorTranslator.FromHtml("#9CA3AF");
        lblHint.Location = new Point(0, 358);
        lblHint.Size = new Size(340, 18);
        lblHint.TextAlign = ContentAlignment.MiddleCenter;
        lblHint.Text = "Default credentials: admin / admin123";

        // LoginForm
        Controls.Add(panelCard);

        ResumeLayout(false);
    }
}
