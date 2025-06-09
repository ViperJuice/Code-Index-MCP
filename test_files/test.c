#include <stdio.h>

// Function to calculate factorial
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

// Main function
int main() {
    int num = 5;
    printf("Factorial of %d is %d\n", num, factorial(num));
    return 0;
}