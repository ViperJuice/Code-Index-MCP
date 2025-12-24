#!/usr/bin/env python3
"""Test the generic plugin with various languages."""

from mcp_server.plugins.generic_treesitter_plugin import GenericTreeSitterPlugin
from mcp_server.plugins.language_registry import LANGUAGE_CONFIGS

# Test code samples for different languages
TEST_SAMPLES = {
    "go": """package main

func Add(a, b int) int {
    return a + b
}

type Calculator struct {
    result int
}

func (c *Calculator) Compute(x, y int) {
    c.result = x + y
}
""",
    "rust": """pub fn multiply(a: i32, b: i32) -> i32 {
    a * b
}

pub struct Vector {
    x: f64,
    y: f64,
}

impl Vector {
    pub fn new(x: f64, y: f64) -> Self {
        Vector { x, y }
    }
}

pub trait Drawable {
    fn draw(&self);
}
""",
    "java": """public class MathUtils {
    private int value;
    
    public int add(int a, int b) {
        return a + b;
    }
    
    public static double multiply(double x, double y) {
        return x * y;
    }
}

interface Calculator {
    int calculate(int a, int b);
}
""",
    "kotlin": """class StringUtils {
    fun capitalize(text: String): String {
        return text.capitalize()
    }
}

data class Point(val x: Double, val y: Double)

interface Shape {
    fun area(): Double
}
""",
    "swift": """class Vehicle {
    var speed: Double = 0.0
    
    func accelerate(by amount: Double) {
        speed += amount
    }
}

struct Rectangle {
    var width: Double
    var height: Double
    
    func area() -> Double {
        return width * height
    }
}

protocol Flyable {
    func fly()
}
""",
    "ruby": """class BankAccount
  attr_reader :balance
  
  def initialize(initial_balance = 0)
    @balance = initial_balance
  end
  
  def deposit(amount)
    @balance += amount
  end
end

module Helpers
  def self.format_currency(amount)
    "$#{amount}"
  end
end
""",
    "php": """<?php
class Database {
    private $connection;
    
    public function __construct($host, $user, $pass) {
        $this->connection = new PDO("mysql:host=$host", $user, $pass);
    }
    
    public function query($sql) {
        return $this->connection->query($sql);
    }
}

interface Repository {
    public function find($id);
    public function save($entity);
}
?>
""",
    "c_sharp": """public class Person {
    public string Name { get; set; }
    public int Age { get; set; }
    
    public Person(string name, int age) {
        Name = name;
        Age = age;
    }
    
    public void Greet() {
        Console.WriteLine($"Hello, I am {Name}");
    }
}

public interface IService {
    void Execute();
}
""",
    "scala": """class Calculator {
  def add(x: Int, y: Int): Int = x + y
  
  def multiply(x: Int, y: Int): Int = x * y
}

trait Printable {
  def print(): Unit
}

object MathUtils {
  def factorial(n: Int): Int = {
    if (n <= 1) 1 else n * factorial(n - 1)
  }
}
""",
}


def test_language(lang_code: str, sample_code: str):
    """Test a specific language."""
    if lang_code not in LANGUAGE_CONFIGS:
        return False, f"Language {lang_code} not in registry"

    try:
        lang_config = LANGUAGE_CONFIGS[lang_code]
        plugin = GenericTreeSitterPlugin(lang_config)

        # Check if parser is available
        if not plugin.parser:
            return False, "Parser not available"

        # Index the sample code
        result = plugin.indexFile(f"test.{lang_code}", sample_code)
        symbols = result["symbols"]

        if not symbols:
            return False, "No symbols found"

        # Success
        symbol_summary = ", ".join(f"{s['kind']}:{s['symbol']}" for s in symbols[:3])
        if len(symbols) > 3:
            symbol_summary += f" ... ({len(symbols)} total)"

        return True, symbol_summary

    except Exception as e:
        return False, str(e)


def main():
    """Test all languages."""
    print("Testing Generic Tree-Sitter Plugin with Multiple Languages\n")
    print("=" * 60)

    results = []

    for lang_code, sample_code in TEST_SAMPLES.items():
        success, message = test_language(lang_code, sample_code)
        status = "✓" if success else "✗"
        results.append((lang_code, success))

        print(f"\n{status} {LANGUAGE_CONFIGS.get(lang_code, {}).get('name', lang_code)}:")
        print(f"  {message}")

    # Summary
    print("\n" + "=" * 60)
    successful = sum(1 for _, success in results if success)
    print(f"\nSummary: {successful}/{len(results)} languages working")

    # List all supported languages in registry
    print(f"\nTotal languages in registry: {len(LANGUAGE_CONFIGS)}")
    print("Sample languages:", ", ".join(list(LANGUAGE_CONFIGS.keys())[:15]) + "...")


if __name__ == "__main__":
    main()
