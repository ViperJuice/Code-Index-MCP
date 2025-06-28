"""Test different search features of the MCP server."""

def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number using recursion."""
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)

def calculate_factorial(n):
    """Calculate the factorial of n using iteration."""
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

class MathOperations:
    """A class for various mathematical operations."""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        """Add two numbers and store in history."""
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result
    
    def multiply(self, a, b):
        """Multiply two numbers and store in history."""
        result = a * b
        self.history.append(f"multiply({a}, {b}) = {result}")
        return result
    
    def fibonacci_sequence(self, count):
        """Generate Fibonacci sequence of given length."""
        sequence = []
        for i in range(count):
            sequence.append(calculate_fibonacci(i))
        return sequence