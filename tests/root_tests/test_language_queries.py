#!/usr/bin/env python3
"""Test language-specific tree-sitter queries."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


def test_language_queries():
    """Test tree-sitter queries for various languages."""
    print("=== Testing Language-Specific Tree-Sitter Queries ===\n")

    # Test cases with expected symbols and their kinds
    test_cases = {
        "go": {
            "code": """package main

import "fmt"

func calculateSum(a, b int) int {
    return a + b
}

type Calculator struct {
    result int
}

func (c *Calculator) Add(x, y int) {
    c.result = x + y
}

type Operation interface {
    Execute() int
}""",
            "expected": {
                "function": ["calculateSum"],
                "type": ["Calculator", "Operation"],
                "method": ["Add"],
            },
        },
        "rust": {
            "code": """struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn distance(&self, other: &Point) -> f64 {
        ((self.x - other.x).powi(2) + (self.y - other.y).powi(2)).sqrt()
    }
    
    fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }
}

trait Drawable {
    fn draw(&self);
}

enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
}

fn main() {
    let p = Point::new(0.0, 0.0);
}""",
            "expected": {
                "struct": ["Point"],
                "function": ["distance", "new", "main"],
                "trait": ["Drawable"],
                "enum": ["Shape"],
            },
        },
        "kotlin": {
            "code": """data class User(val id: Int, val name: String)

interface Repository<T> {
    fun findById(id: Int): T?
    fun save(item: T)
}

class UserRepository : Repository<User> {
    private val users = mutableListOf<User>()
    
    override fun findById(id: Int): User? {
        return users.find { it.id == id }
    }
    
    override fun save(item: User) {
        users.add(item)
    }
}

fun main() {
    val repo = UserRepository()
    repo.save(User(1, "Alice"))
}""",
            "expected": {
                "class": ["User", "UserRepository"],
                "function": ["findById", "save", "main"],
            },
        },
        "ruby": {
            "code": """class BankAccount
  attr_reader :balance
  
  def initialize(initial_balance = 0)
    @balance = initial_balance
  end
  
  def deposit(amount)
    @balance += amount
  end
  
  def withdraw(amount)
    raise "Insufficient funds" if amount > @balance
    @balance -= amount
  end
end

module Banking
  def self.transfer(from, to, amount)
    from.withdraw(amount)
    to.deposit(amount)
  end
end""",
            "expected": {
                "class": ["BankAccount"],
                "method": ["initialize", "deposit", "withdraw"],
                "module": ["Banking"],
                "singleton_method": ["transfer"],
            },
        },
        "java": {
            "code": """public interface Vehicle {
    void start();
    void stop();
}

public class Car implements Vehicle {
    private String model;
    
    public Car(String model) {
        this.model = model;
    }
    
    @Override
    public void start() {
        System.out.println("Car started");
    }
    
    @Override
    public void stop() {
        System.out.println("Car stopped");
    }
    
    public String getModel() {
        return model;
    }
}

enum VehicleType {
    CAR, TRUCK, MOTORCYCLE
}""",
            "expected": {
                "interface": ["Vehicle"],
                "class": ["Car"],
                "method": ["start", "stop", "getModel"],
                "constructor": ["Car"],
                "enum": ["VehicleType"],
            },
        },
    }

    store = SQLiteStore(":memory:")
    results = {}

    for lang, test_data in test_cases.items():
        print(f"\n--- Testing {lang.upper()} ---")
        try:
            # Create plugin
            plugin = PluginFactory.create_plugin(lang, store, enable_semantic=False)
            print(f"✓ Created {lang} plugin: {plugin.__class__.__name__}")

            # Check if query is available
            if hasattr(plugin, "query_string") and plugin.query_string:
                print(f"✓ Query available: {len(plugin.query_string)} chars")
            else:
                print("✗ No query string found")

            # Create test file
            ext_map = {
                "go": ".go",
                "rust": ".rs",
                "typescript": ".ts",
                "ruby": ".rb",
                "java": ".java",
                "kotlin": ".kt",
            }
            test_file = Path(f"test{ext_map.get(lang, f'.{lang}')}")
            test_file.write_text(test_data["code"])

            # Index the file
            shard = plugin.indexFile(test_file, test_data["code"])

            # Group symbols by kind
            symbols_by_kind = {}
            for symbol in shard["symbols"]:
                kind = symbol["kind"]
                if kind not in symbols_by_kind:
                    symbols_by_kind[kind] = []
                symbols_by_kind[kind].append(symbol["symbol"])

            print("\nExtracted symbols by kind:")
            for kind, symbols in sorted(symbols_by_kind.items()):
                print(f"  {kind}: {', '.join(symbols)}")

            # Verify expected symbols
            all_found = True
            for expected_kind, expected_symbols in test_data["expected"].items():
                found_symbols = symbols_by_kind.get(expected_kind, [])
                missing = [s for s in expected_symbols if s not in found_symbols]
                if missing:
                    print(f"\n✗ Missing {expected_kind}: {', '.join(missing)}")
                    all_found = False
                else:
                    print(f"✓ All {expected_kind} symbols found")

            # Check for query vs traversal
            if hasattr(plugin, "parser") and plugin.parser is not None:
                print("✓ Using tree-sitter parser")
            else:
                print("✗ Parser not available")

            results[lang] = all_found

            # Cleanup
            test_file.unlink(missing_ok=True)

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback

            traceback.print_exc()
            results[lang] = False

    # Summary
    print("\n=== Summary ===")
    successful = sum(1 for v in results.values() if v)
    print(f"Languages with correct query extraction: {successful}/{len(results)}")

    for lang, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {lang}")

    return successful == len(results)


if __name__ == "__main__":
    success = test_language_queries()
    if success:
        print("\n✅ All language queries are working correctly!")
    else:
        print("\n❌ Some language queries need improvement")
        sys.exit(1)
