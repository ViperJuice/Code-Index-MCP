#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int id;
    char name[50];
    float salary;
} Employee;

Employee* createEmployee(int id, const char* name, float salary) {
    Employee* emp = (Employee*)malloc(sizeof(Employee));
    emp->id = id;
    snprintf(emp->name, sizeof(emp->name), "%s", name);
    emp->salary = salary;
    return emp;
}

void printEmployee(const Employee* emp) {
    printf("Employee ID: %d\n", emp->id);
    printf("Name: %s\n", emp->name);
    printf("Salary: %.2f\n", emp->salary);
}