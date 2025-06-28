#!/usr/bin/env python3
"""Test that tree-sitter parsing is working correctly after the fix."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore


def test_treesitter_languages():
    """Test tree-sitter parsing for various languages."""
    print("=== Testing Tree-Sitter Fix ===\n")
    
    # Test cases with expected symbols
    test_cases = {
        "go": {
            "code": '''package main

func calculateSum(a, b int) int {
    return a + b
}

type Calculator struct {
    result int
}

func (c *Calculator) Add(x, y int) {
    c.result = x + y
}''',
            "expected_symbols": ["calculateSum", "Calculator", "Add"]
        },
        "rust": {
            "code": '''struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn distance(&self, other: &Point) -> f64 {
        ((self.x - other.x).powi(2) + (self.y - other.y).powi(2)).sqrt()
    }
}

fn main() {
    let p1 = Point { x: 0.0, y: 0.0 };
}''',
            "expected_symbols": ["Point", "distance", "main"]
        },
        "python": {
            "code": '''class DataProcessor:
    def __init__(self, data):
        self.data = data
    
    def process(self):
        return [x * 2 for x in self.data]

def transform_data(input_list):
    processor = DataProcessor(input_list)
    return processor.process()''',
            "expected_symbols": ["DataProcessor", "__init__", "process", "transform_data"]
        }
    }
    
    store = SQLiteStore(":memory:")
    results = {}
    
    for lang, test_data in test_cases.items():
        print(f"\n--- Testing {lang} ---")
        try:
            # Create plugin
            plugin = PluginFactory.create_plugin(lang, store, enable_semantic=False)
            print(f"✓ Created {lang} plugin: {plugin.__class__.__name__}")
            
            # Create test file
            test_file = Path(f"test.{lang}")
            test_file.write_text(test_data["code"])
            
            # Index the file
            shard = plugin.indexFile(test_file, test_data["code"])
            symbols = [s["symbol"] for s in shard["symbols"]]
            
            print(f"✓ Found {len(symbols)} symbols: {', '.join(symbols)}")
            
            # Check if expected symbols were found
            missing = [s for s in test_data["expected_symbols"] if s not in symbols]
            if missing:
                print(f"✗ Missing expected symbols: {', '.join(missing)}")
                results[lang] = False
            else:
                print(f"✓ All expected symbols found!")
                results[lang] = True
            
            # Check if parser is working (not just fallback)
            if hasattr(plugin, 'parser') and plugin.parser is not None:
                print(f"✓ Tree-sitter parser is active")
            else:
                print(f"✗ Using fallback parsing (no tree-sitter)")
            
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
    print(f"Passed: {successful}/{len(results)} languages")
    
    return successful == len(results)


if __name__ == "__main__":
    success = test_treesitter_languages()
    if success:
        print("\n✅ Tree-sitter fix is working correctly!")
    else:
        print("\n❌ Tree-sitter fix needs more work")
        sys.exit(1)