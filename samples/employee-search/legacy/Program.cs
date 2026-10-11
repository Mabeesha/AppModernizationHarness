using EmployeeSearch.Database;
using EmployeeSearch.Views;

namespace EmployeeSearch;

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
