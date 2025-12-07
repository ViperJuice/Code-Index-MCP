#!/usr/bin/env python3
"""Test the generic plugin system with multiple languages."""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore


def create_test_files():
    """Create test files for various languages."""
    test_files = {
        "test.go": """package main

import "fmt"

type User struct {
    Name string
    Age  int
}

func (u *User) Greet() string {
    return fmt.Sprintf("Hello, I'm %s", u.Name)
}

func main() {
    user := User{Name: "Alice", Age: 30}
    fmt.Println(user.Greet())
}
""",
        "test.rs": """struct Rectangle {
    width: f64,
    height: f64,
}

impl Rectangle {
    fn area(&self) -> f64 {
        self.width * self.height
    }
    
    fn new(width: f64, height: f64) -> Self {
        Rectangle { width, height }
    }
}

fn calculate_perimeter(rect: &Rectangle) -> f64 {
    2.0 * (rect.width + rect.height)
}

fn main() {
    let rect = Rectangle::new(10.0, 20.0);
    println!("Area: {}", rect.area());
}
""",
        "test.java": """public class Calculator {
    private double result;
    
    public Calculator() {
        this.result = 0.0;
    }
    
    public double add(double a, double b) {
        result = a + b;
        return result;
    }
    
    public double multiply(double a, double b) {
        result = a * b;
        return result;
    }
    
    public static void main(String[] args) {
        Calculator calc = new Calculator();
        System.out.println(calc.add(5, 3));
    }
}
""",
        "test.rb": """class BankAccount
  attr_reader :balance, :owner
  
  def initialize(owner, initial_balance = 0)
    @owner = owner
    @balance = initial_balance
  end
  
  def deposit(amount)
    raise ArgumentError, "Amount must be positive" if amount <= 0
    @balance += amount
  end
  
  def withdraw(amount)
    raise ArgumentError, "Insufficient funds" if amount > @balance
    @balance -= amount
  end
end

module Banking
  def self.transfer(from, to, amount)
    from.withdraw(amount)
    to.deposit(amount)
  end
end
""",
        "test.kt": """data class Person(val name: String, val age: Int)

interface Greeting {
    fun greet(): String
}

class FormalGreeting(private val person: Person) : Greeting {
    override fun greet(): String {
        return "Good day, ${person.name}"
    }
}

fun main() {
    val person = Person("John", 25)
    val greeting = FormalGreeting(person)
    println(greeting.greet())
}
""",
        "test.swift": """protocol Vehicle {
    var numberOfWheels: Int { get }
    func start()
    func stop()
}

class Car: Vehicle {
    let model: String
    let numberOfWheels = 4
    
    init(model: String) {
        self.model = model
    }
    
    func start() {
        print("\\(model) engine started")
    }
    
    func stop() {
        print("\\(model) engine stopped")
    }
}

struct ElectricCar: Vehicle {
    let model: String
    let numberOfWheels = 4
    let batteryCapacity: Double
    
    func start() {
        print("\\(model) electric motor engaged")
    }
    
    func stop() {
        print("\\(model) electric motor disengaged")
    }
}
""",
        "test.lua": """-- Define a class-like table
local Animal = {}
Animal.__index = Animal

function Animal:new(name, species)
    local self = setmetatable({}, Animal)
    self.name = name
    self.species = species
    return self
end

function Animal:speak()
    print(self.name .. " makes a sound")
end

-- Define a module
local math_utils = {}

function math_utils.factorial(n)
    if n <= 1 then
        return 1
    else
        return n * math_utils.factorial(n - 1)
    end
end

function math_utils.fibonacci(n)
    if n <= 1 then
        return n
    else
        return math_utils.fibonacci(n - 1) + math_utils.fibonacci(n - 2)
    end
end

return math_utils
""",
        "test.sh": """#!/bin/bash

# Function to check if a command exists
function command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install packages
function install_packages() {
    local packages=("$@")
    
    for package in "${packages[@]}"; do
        echo "Installing $package..."
        if command_exists apt-get; then
            sudo apt-get install -y "$package"
        elif command_exists yum; then
            sudo yum install -y "$package"
        else
            echo "Package manager not found"
            return 1
        fi
    done
}

# Main function
function main() {
    echo "System setup script"
    install_packages git vim curl
}

main "$@"
""",
    }

    # Create temporary directory with test files
    temp_dir = tempfile.mkdtemp()
    file_paths = {}

    for filename, content in test_files.items():
        file_path = Path(temp_dir) / filename
        file_path.write_text(content)
        file_paths[filename] = file_path

    return temp_dir, file_paths


def test_generic_plugins():
    """Test the generic plugin system."""
    print("=== Testing Generic Plugin System ===\\n")

    # Create test files
    temp_dir, test_files = create_test_files()
    os.chdir(temp_dir)

    # Create SQLite store
    store = SQLiteStore(":memory:")

    # Get plugin factory info
    print(f"Supported languages: {len(PluginFactory.get_supported_languages())}")
    print(f"Languages: {', '.join(PluginFactory.get_supported_languages()[:10])}...\\n")

    # Test each language
    results = {}
    for filename, file_path in test_files.items():
        language = file_path.suffix[1:]  # Remove the dot
        print(f"\\n--- Testing {filename} ({language}) ---")

        try:
            # Create plugin for this file
            plugin = PluginFactory.create_plugin_for_file(file_path, store)
            if not plugin:
                print(f"  ❌ No plugin found for {language}")
                results[language] = False
                continue

            print(f"  ✓ Plugin created: {plugin.__class__.__name__}")
            print(f"  ✓ Language: {getattr(plugin, 'language_name', language)}")

            # Index the file
            content = file_path.read_text()
            shard = plugin.indexFile(file_path, content)

            print(f"  ✓ Indexed {len(shard['symbols'])} symbols:")
            for symbol in shard["symbols"][:5]:  # Show first 5
                print(f"    - {symbol['kind']}: {symbol['symbol']} (line {symbol['line']})")

            if len(shard["symbols"]) > 5:
                print(f"    ... and {len(shard['symbols']) - 5} more")

            # Test search
            if shard["symbols"]:
                first_symbol = shard["symbols"][0]["symbol"]
                search_results = list(plugin.search(first_symbol, {"limit": 3}))
                print(f"  ✓ Search for '{first_symbol}' found {len(search_results)} results")

            results[language] = True

        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback

            traceback.print_exc()
            results[language] = False

    # Summary
    print("\\n=== Summary ===")
    successful = sum(1 for v in results.values() if v)
    print(f"Successfully tested: {successful}/{len(results)} languages")

    for lang, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {lang}")

    # Cleanup
    os.chdir("/")
    import shutil

    shutil.rmtree(temp_dir)

    return successful == len(results)


def test_language_detection():
    """Test automatic language detection from file extension."""
    print("\\n=== Testing Language Detection ===\\n")

    test_extensions = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".rb": "ruby",
        ".php": "php",
        ".c": "c",
        ".cpp": "cpp",
        ".cs": "c_sharp",
        ".swift": "swift",
        ".lua": "lua",
        ".sh": "bash",
        ".r": "r",
        ".jl": "julia",
        ".hs": "haskell",
        ".ml": "ocaml",
        ".ex": "elixir",
        ".erl": "erlang",
        ".scala": "scala",
        ".dart": "dart",
        ".vim": "vim",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".yaml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".sql": "sql",
        ".md": "markdown",
        ".tex": "latex",
        ".dockerfile": "dockerfile",
    }

    from mcp_server.plugins.language_registry import get_language_by_extension

    correct = 0
    for ext, expected_lang in test_extensions.items():
        detected = get_language_by_extension(ext)
        if detected == expected_lang:
            print(f"  ✓ {ext} -> {detected}")
            correct += 1
        else:
            print(f"  ✗ {ext} -> {detected} (expected {expected_lang})")

    print(f"\\nCorrectly detected: {correct}/{len(test_extensions)}")
    return correct == len(test_extensions)


def main():
    """Run all tests."""
    print("Testing Generic Plugin System for 48 Languages\\n")

    # Test language detection
    detection_ok = test_language_detection()

    # Test generic plugins
    plugins_ok = test_generic_plugins()

    if detection_ok and plugins_ok:
        print("\\n✅ All tests passed!")
    else:
        print("\\n❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
