namespace EmployeeSearch.Models;

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
