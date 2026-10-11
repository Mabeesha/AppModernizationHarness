#nullable enable
namespace EmployeeSearch.Views;

partial class SearchForm
{
    private System.ComponentModel.IContainer? components = null;

    protected override void Dispose(bool disposing)
    {
        if (disposing && components != null) components.Dispose();
        base.Dispose(disposing);
    }

    private Panel panelHeader = null!;
    private Label lblHeaderTitle = null!;
    private Label lblUser = null!;
    private Button btnLogout = null!;
    private Button btnExport = null!;

    private Panel panelFilters = null!;
    private Label lblFiltersTitle = null!;
    private Label lblName = null!;
    private TextBox txtName = null!;
    private Label lblDepartment = null!;
    private ComboBox cboDepartment = null!;
    private Label lblRole = null!;
    private ComboBox cboRole = null!;
    private Label lblStatusFilter = null!;
    private ComboBox cboStatus = null!;
    private Button btnSearch = null!;
    private Button btnClear = null!;

    private Panel panelStatus = null!;
    private Label lblStatus = null!;

    private DataGridView dgvResults = null!;

    private void InitializeComponent()
    {
        panelHeader = new Panel();
        lblHeaderTitle = new Label();
        lblUser = new Label();
        btnLogout = new Button();
        btnExport = new Button();

        panelFilters = new Panel();
        lblFiltersTitle = new Label();
        lblName = new Label();
        txtName = new TextBox();
        lblDepartment = new Label();
        cboDepartment = new ComboBox();
        lblRole = new Label();
        cboRole = new ComboBox();
        lblStatusFilter = new Label();
        cboStatus = new ComboBox();
        btnSearch = new Button();
        btnClear = new Button();

        panelStatus = new Panel();
        lblStatus = new Label();

        dgvResults = new DataGridView();

        SuspendLayout();

        // SearchForm
        AutoScaleMode = AutoScaleMode.None;
        ClientSize = new Size(1000, 700);
        MinimumSize = new Size(800, 560);
        StartPosition = FormStartPosition.CenterScreen;
        Text = "Employee Search";
        Font = new Font("Segoe UI", 9F);
        BackColor = ColorTranslator.FromHtml("#F3F4F6");

        // ===== Header =====
        panelHeader.Dock = DockStyle.Top;
        // Width must be set explicitly (matching ClientSize.Width) before any
        // Anchor-right children below are positioned: Dock only stretches the
        // panel to the form's width once a layout pass runs, which is too late
        // for the Anchor distance-to-right-edge to be captured correctly.
        // Height is taller than a single button row to fit Export below Logout.
        panelHeader.Size = new Size(1000, 100);
        panelHeader.BackColor = ColorTranslator.FromHtml("#1B2A4A");
        panelHeader.Controls.Add(lblHeaderTitle);
        panelHeader.Controls.Add(lblUser);
        panelHeader.Controls.Add(btnLogout);
        panelHeader.Controls.Add(btnExport);

        lblHeaderTitle.AutoSize = false;
        lblHeaderTitle.Font = new Font("Segoe UI", 13F, FontStyle.Bold);
        lblHeaderTitle.ForeColor = Color.White;
        lblHeaderTitle.Location = new Point(20, 35);
        lblHeaderTitle.Size = new Size(320, 30);
        lblHeaderTitle.Text = "\U0001F50D  Employee Search";
        lblHeaderTitle.TextAlign = ContentAlignment.MiddleLeft;

        lblUser.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        lblUser.AutoSize = false;
        lblUser.ForeColor = ColorTranslator.FromHtml("#93C5FD");
        lblUser.Location = new Point(700, 20);
        lblUser.Size = new Size(180, 20);
        lblUser.TextAlign = ContentAlignment.MiddleRight;

        btnLogout.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        btnLogout.BackColor = ColorTranslator.FromHtml("#F3F4F6");
        btnLogout.FlatStyle = FlatStyle.Flat;
        btnLogout.FlatAppearance.BorderColor = ColorTranslator.FromHtml("#D1D5DB");
        btnLogout.FlatAppearance.MouseOverBackColor = ColorTranslator.FromHtml("#E5E7EB");
        btnLogout.ForeColor = ColorTranslator.FromHtml("#374151");
        btnLogout.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
        btnLogout.Location = new Point(890, 14);
        btnLogout.Size = new Size(90, 32);
        btnLogout.Text = "Logout";
        btnLogout.Cursor = Cursors.Hand;
        btnLogout.Click += btnLogout_Click;

        // btnExport — Excel-green button (matches Microsoft Excel's brand
        // color/icon style) for exporting the currently visible rows to CSV.
        btnExport.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        btnExport.BackColor = ColorTranslator.FromHtml("#217346");
        btnExport.FlatStyle = FlatStyle.Flat;
        btnExport.FlatAppearance.BorderSize = 0;
        btnExport.FlatAppearance.MouseOverBackColor = ColorTranslator.FromHtml("#1A5C37");
        btnExport.FlatAppearance.MouseDownBackColor = ColorTranslator.FromHtml("#134628");
        btnExport.ForeColor = Color.White;
        btnExport.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
        btnExport.Location = new Point(850, 54);
        btnExport.Size = new Size(130, 32);
        btnExport.Text = "\U0001F4CA  Export";
        btnExport.Cursor = Cursors.Hand;
        btnExport.Click += btnExport_Click;

        // ===== Filters =====
        panelFilters.Dock = DockStyle.Top;
        // Same Anchor-capture timing issue as panelHeader above.
        panelFilters.Size = new Size(1000, 160);
        panelFilters.BackColor = Color.White;
        panelFilters.Controls.Add(lblFiltersTitle);
        panelFilters.Controls.Add(lblName);
        panelFilters.Controls.Add(txtName);
        panelFilters.Controls.Add(lblDepartment);
        panelFilters.Controls.Add(cboDepartment);
        panelFilters.Controls.Add(lblRole);
        panelFilters.Controls.Add(cboRole);
        panelFilters.Controls.Add(lblStatusFilter);
        panelFilters.Controls.Add(cboStatus);
        panelFilters.Controls.Add(btnSearch);
        panelFilters.Controls.Add(btnClear);

        // AutoSize avoids GDI TextRenderer clipping the top of bold text
        // when a fixed Height is a touch too short for the font's metrics.
        lblFiltersTitle.AutoSize = true;
        lblFiltersTitle.Font = new Font("Segoe UI", 10F, FontStyle.Bold);
        lblFiltersTitle.ForeColor = ColorTranslator.FromHtml("#1F2937");
        lblFiltersTitle.Location = new Point(20, 12);
        lblFiltersTitle.Text = "Search Filters";

        // Row 1
        lblName.AutoSize = true;
        lblName.ForeColor = ColorTranslator.FromHtml("#374151");
        lblName.Font = new Font("Segoe UI", 8.5F, FontStyle.Bold);
        lblName.Location = new Point(20, 42);
        lblName.Text = "Employee Name";

        txtName.Font = new Font("Segoe UI", 10F);
        txtName.Location = new Point(20, 60);
        txtName.Size = new Size(606, 26);
        txtName.KeyDown += Filter_KeyDown;

        lblDepartment.AutoSize = true;
        lblDepartment.ForeColor = ColorTranslator.FromHtml("#374151");
        lblDepartment.Font = new Font("Segoe UI", 8.5F, FontStyle.Bold);
        lblDepartment.Location = new Point(640, 42);
        lblDepartment.Text = "Department";

        cboDepartment.DropDownStyle = ComboBoxStyle.DropDownList;
        cboDepartment.Font = new Font("Segoe UI", 9.5F);
        cboDepartment.Location = new Point(640, 60);
        cboDepartment.Size = new Size(160, 26);
        cboDepartment.Items.AddRange(new object[] { "All", "Finance", "HR", "IT", "Marketing", "Operations" });
        cboDepartment.SelectedIndex = 0;

        lblRole.AutoSize = true;
        lblRole.ForeColor = ColorTranslator.FromHtml("#374151");
        lblRole.Font = new Font("Segoe UI", 8.5F, FontStyle.Bold);
        lblRole.Location = new Point(814, 42);
        lblRole.Text = "Role";

        cboRole.DropDownStyle = ComboBoxStyle.DropDownList;
        cboRole.Font = new Font("Segoe UI", 9.5F);
        cboRole.Location = new Point(814, 60);
        cboRole.Size = new Size(160, 26);
        cboRole.Items.AddRange(new object[] { "All", "Analyst", "Coordinator", "Designer", "Developer", "Manager" });
        cboRole.SelectedIndex = 0;

        // Row 2
        lblStatusFilter.AutoSize = true;
        lblStatusFilter.ForeColor = ColorTranslator.FromHtml("#374151");
        lblStatusFilter.Font = new Font("Segoe UI", 8.5F, FontStyle.Bold);
        lblStatusFilter.Location = new Point(20, 100);
        lblStatusFilter.Text = "Status";

        cboStatus.DropDownStyle = ComboBoxStyle.DropDownList;
        cboStatus.Font = new Font("Segoe UI", 9.5F);
        cboStatus.Location = new Point(20, 118);
        cboStatus.Size = new Size(160, 26);
        cboStatus.Items.AddRange(new object[] { "All", "Active", "Inactive", "On Leave" });
        cboStatus.SelectedIndex = 0;

        btnSearch.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        btnSearch.BackColor = ColorTranslator.FromHtml("#1B4F8A");
        btnSearch.FlatStyle = FlatStyle.Flat;
        btnSearch.FlatAppearance.BorderSize = 0;
        btnSearch.FlatAppearance.MouseOverBackColor = ColorTranslator.FromHtml("#154080");
        btnSearch.FlatAppearance.MouseDownBackColor = ColorTranslator.FromHtml("#0F3060");
        btnSearch.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold);
        btnSearch.ForeColor = Color.White;
        btnSearch.Location = new Point(760, 114);
        btnSearch.Size = new Size(110, 34);
        btnSearch.Text = "\U0001F50D  Search";
        btnSearch.Cursor = Cursors.Hand;
        btnSearch.Click += btnSearch_Click;

        btnClear.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        btnClear.BackColor = ColorTranslator.FromHtml("#F3F4F6");
        btnClear.FlatStyle = FlatStyle.Flat;
        btnClear.FlatAppearance.BorderColor = ColorTranslator.FromHtml("#D1D5DB");
        btnClear.FlatAppearance.MouseOverBackColor = ColorTranslator.FromHtml("#E5E7EB");
        btnClear.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold);
        btnClear.ForeColor = ColorTranslator.FromHtml("#374151");
        btnClear.Location = new Point(880, 114);
        btnClear.Size = new Size(90, 34);
        btnClear.Text = "Clear";
        btnClear.Cursor = Cursors.Hand;
        btnClear.Click += btnClear_Click;

        // ===== Status bar =====
        panelStatus.Dock = DockStyle.Bottom;
        panelStatus.Height = 34;
        panelStatus.BackColor = ColorTranslator.FromHtml("#E5E7EB");
        panelStatus.Controls.Add(lblStatus);

        lblStatus.AutoSize = false;
        lblStatus.ForeColor = ColorTranslator.FromHtml("#6B7280");
        lblStatus.Location = new Point(12, 8);
        lblStatus.Size = new Size(960, 18);
        lblStatus.Text = "Use filters above and click Search to find employees.";

        // ===== Results grid =====
        dgvResults.Dock = DockStyle.Fill;
        dgvResults.BackgroundColor = Color.White;
        dgvResults.BorderStyle = BorderStyle.None;
        dgvResults.AllowUserToAddRows = false;
        dgvResults.AllowUserToDeleteRows = false;
        dgvResults.AllowUserToResizeRows = false;
        dgvResults.AutoGenerateColumns = false;
        dgvResults.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
        dgvResults.ReadOnly = true;
        dgvResults.RowHeadersVisible = false;
        dgvResults.MultiSelect = false;
        dgvResults.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        dgvResults.EnableHeadersVisualStyles = false;
        dgvResults.GridColor = ColorTranslator.FromHtml("#F3F4F6");
        dgvResults.ColumnHeadersHeight = 38;
        dgvResults.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.DisableResizing;
        dgvResults.ColumnHeadersDefaultCellStyle.BackColor = ColorTranslator.FromHtml("#F9FAFB");
        dgvResults.ColumnHeadersDefaultCellStyle.ForeColor = ColorTranslator.FromHtml("#6B7280");
        dgvResults.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
        dgvResults.ColumnHeadersDefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleLeft;
        dgvResults.RowTemplate.Height = 36;
        dgvResults.AlternatingRowsDefaultCellStyle.BackColor = ColorTranslator.FromHtml("#FAFAFA");
        dgvResults.DefaultCellStyle.Font = new Font("Segoe UI", 9.5F);
        dgvResults.DefaultCellStyle.Padding = new Padding(6, 4, 6, 4);
        dgvResults.DefaultCellStyle.SelectionBackColor = ColorTranslator.FromHtml("#DBEAFE");
        dgvResults.DefaultCellStyle.SelectionForeColor = ColorTranslator.FromHtml("#1E3A5F");
        dgvResults.Columns.AddRange(
            new DataGridViewTextBoxColumn { Name = "Id", HeaderText = "#", DataPropertyName = "Id", FillWeight = 50 },
            new DataGridViewTextBoxColumn { Name = "Name", HeaderText = "Name", DataPropertyName = "Name", FillWeight = 160 },
            new DataGridViewTextBoxColumn { Name = "Department", HeaderText = "Department", DataPropertyName = "Department", FillWeight = 130 },
            new DataGridViewTextBoxColumn { Name = "Role", HeaderText = "Role", DataPropertyName = "Role", FillWeight = 130 },
            new DataGridViewTextBoxColumn { Name = "Status", HeaderText = "Status", DataPropertyName = "Status", FillWeight = 100 },
            new DataGridViewTextBoxColumn { Name = "Email", HeaderText = "Email", DataPropertyName = "Email", FillWeight = 180 },
            new DataGridViewTextBoxColumn { Name = "Phone", HeaderText = "Phone", DataPropertyName = "Phone", FillWeight = 120 },
            new DataGridViewTextBoxColumn { Name = "HireDate", HeaderText = "Hire Date", DataPropertyName = "HireDate", FillWeight = 110 },
            new DataGridViewTextBoxColumn { Name = "Salary", HeaderText = "Salary", DataPropertyName = "SalaryFormatted", FillWeight = 110 }
        );
        dgvResults.CellFormatting += dgvResults_CellFormatting;

        // ===== SearchForm =====
        // Dock.Top controls stack with the most-recently-added one closest to
        // the top edge, so panelHeader must be added after panelFilters.
        // The Fill control must be added first so it doesn't claim space that
        // hasn't been carved out by the Top/Bottom docked panels yet.
        Controls.Add(dgvResults);
        Controls.Add(panelStatus);
        Controls.Add(panelFilters);
        Controls.Add(panelHeader);

        ResumeLayout(false);
    }
}
