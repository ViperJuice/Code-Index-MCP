#!/usr/bin/env python3
"""Test the enhanced dispatcher with multiple languages."""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


def create_test_files():
    """Create test files for various languages."""
    test_files = {
        "test.go": '''package main

import "fmt"

func greetUser(name string) string {
    return fmt.Sprintf("Hello, %s!", name)
}

func main() {
    fmt.Println(greetUser("World"))
}
''',
        "test.rs": '''fn calculate_area(width: f64, height: f64) -> f64 {
    width * height
}

fn main() {
    let area = calculate_area(10.0, 20.0);
    println!("Area: {}", area);
}
''',
        "test.rb": '''def fibonacci(n)
  return n if n <= 1
  fibonacci(n - 1) + fibonacci(n - 2)
end

puts fibonacci(10)
''',
        "test.swift": '''func quickSort(_ array: [Int]) -> [Int] {
    guard array.count > 1 else { return array }
    let pivot = array[array.count / 2]
    let less = array.filter { $0 < pivot }
    let equal = array.filter { $0 == pivot }
    let greater = array.filter { $0 > pivot }
    return quickSort(less) + equal + quickSort(greater)
}

print(quickSort([3, 1, 4, 1, 5, 9, 2, 6]))
''',
        "test.kt": '''fun isPalindrome(s: String): Boolean {
    val cleaned = s.lowercase().filter { it.isLetterOrDigit() }
    return cleaned == cleaned.reversed()
}

fun main() {
    println(isPalindrome("A man, a plan, a canal: Panama"))
}
''',
        "test.lua": '''function mergeSort(arr)
    if #arr <= 1 then
        return arr
    end
    
    local mid = math.floor(#arr / 2)
    local left = {}
    local right = {}
    
    for i = 1, mid do
        left[i] = arr[i]
    end
    
    for i = mid + 1, #arr do
        right[i - mid] = arr[i]
    end
    
    return merge(mergeSort(left), mergeSort(right))
end

function merge(left, right)
    local result = {}
    local i, j = 1, 1
    
    while i <= #left and j <= #right do
        if left[i] <= right[j] then
            table.insert(result, left[i])
            i = i + 1
        else
            table.insert(result, right[j])
            j = j + 1
        end
    end
    
    while i <= #left do
        table.insert(result, left[i])
        i = i + 1
    end
    
    while j <= #right do
        table.insert(result, right[j])
        j = j + 1
    end
    
    return result
end
''',
        "test.php": '''<?php
class Calculator {
    public function factorial($n) {
        if ($n <= 1) {
            return 1;
        }
        return $n * $this->factorial($n - 1);
    }
}

$calc = new Calculator();
echo $calc->factorial(5);
?>
''',
        "test.scala": '''object BinarySearch {
  def search(arr: Array[Int], target: Int): Int = {
    var left = 0
    var right = arr.length - 1
    
    while (left <= right) {
      val mid = left + (right - left) / 2
      if (arr(mid) == target) {
        return mid
      } else if (arr(mid) < target) {
        left = mid + 1
      } else {
        right = mid - 1
      }
    }
    
    -1
  }
  
  def main(args: Array[String]): Unit = {
    val arr = Array(1, 3, 5, 7, 9, 11, 13)
    println(search(arr, 7))
  }
}
'''
    }
    
    # Create temporary directory with test files
    temp_dir = tempfile.mkdtemp()
    file_paths = {}
    
    for filename, content in test_files.items():
        file_path = Path(temp_dir) / filename
        file_path.write_text(content)
        file_paths[filename] = file_path
    
    return temp_dir, file_paths


def test_enhanced_dispatcher():
    """Test the enhanced dispatcher."""
    print("=== Testing Enhanced Dispatcher ===\n")
    
    # Create test files
    temp_dir, test_files = create_test_files()
    os.chdir(temp_dir)
    
    # Create SQLite store and initialize tables
    store = SQLiteStore(":memory:")
    # Store should auto-initialize tables in __init__
    
    # Create enhanced dispatcher with lazy loading
    print("Creating enhanced dispatcher...")
    dispatcher = EnhancedDispatcher(
        plugins=None,  # Start with no plugins
        sqlite_store=store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=True
    )
    
    # Check initial status
    print(f"Supported languages: {len(dispatcher.supported_languages)}")
    print(f"Initially loaded plugins: {len(dispatcher._plugins)}")
    print(f"Languages available: {', '.join(dispatcher.supported_languages[:15])}...\n")
    
    # Test indexing each file (this should trigger lazy loading)
    results = {}
    for filename, file_path in test_files.items():
        print(f"\n--- Testing {filename} ---")
        
        try:
            # Index the file
            dispatcher.index_file(file_path)
            
            # Check if plugin was loaded
            language = file_path.suffix[1:]  # Remove dot
            if language in ['rs', 'rb', 'kt', 'swift', 'php', 'scala']:
                # Map file extensions to language codes
                lang_map = {
                    'rs': 'rust',
                    'rb': 'ruby', 
                    'kt': 'kotlin',
                    'swift': 'swift',
                    'php': 'php',
                    'scala': 'scala'
                }
                language = lang_map.get(language, language)
            
            if language == 'lua':
                # Special case: lua uses .lua extension
                pass
            elif language == 'go':
                # Go language uses 'go' as code
                pass
                
            loaded = language in dispatcher._loaded_languages
            print(f"  ✓ File indexed")
            print(f"  ✓ Plugin for '{language}' loaded: {loaded}")
            print(f"  ✓ Total plugins loaded: {len(dispatcher._plugins)}")
            
            # Test search on the file
            content = file_path.read_text()
            # Extract a function/method name for search
            search_term = None
            if "func " in content:
                search_term = content.split("func ")[1].split("(")[0]
            elif "def " in content:
                search_term = content.split("def ")[1].split("(")[0]
            elif "function " in content:
                search_term = content.split("function ")[1].split("(")[0]
                
            if search_term:
                search_results = list(dispatcher.search(search_term, limit=5))
                print(f"  ✓ Search for '{search_term}' found {len(search_results)} results")
                
            results[filename] = True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            results[filename] = False
    
    # Final statistics
    print("\n=== Final Statistics ===")
    stats = dispatcher.get_statistics()
    print(f"Total plugins loaded: {stats['total_plugins']}")
    print(f"Languages loaded: {', '.join(sorted(stats['loaded_languages']))}")
    print(f"Operations performed:")
    for op, count in stats['operations'].items():
        if count > 0:
            print(f"  - {op}: {count}")
    
    # Health check
    print("\n=== Health Check ===")
    health = dispatcher.health_check()
    print(f"Overall status: {health['status']}")
    print(f"Dispatcher config:")
    for key, value in health['components']['dispatcher'].items():
        print(f"  - {key}: {value}")
    
    # Summary
    print("\n=== Summary ===")
    successful = sum(1 for v in results.values() if v)
    print(f"Successfully tested: {successful}/{len(results)} files")
    
    for filename, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {filename}")
    
    # Cleanup
    os.chdir("/")
    import shutil
    shutil.rmtree(temp_dir)
    
    return successful == len(results)


def test_search_across_languages():
    """Test searching across multiple languages."""
    print("\n=== Testing Search Across Languages ===\n")
    
    # Create test files with common term
    test_files = {
        "calc.py": "def calculate_sum(a, b):\n    return a + b",
        "calc.js": "function calculateProduct(a, b) {\n    return a * b;\n}",
        "calc.go": "func calculateDifference(a, b int) int {\n    return a - b\n}",
        "calc.rs": "fn calculate_quotient(a: f64, b: f64) -> f64 {\n    a / b\n}",
        "calc.rb": "def calculate_power(base, exp)\n  base ** exp\nend"
    }
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    os.chdir(temp_dir)
    
    for filename, content in test_files.items():
        Path(filename).write_text(content)
    
    # Create dispatcher
    store = SQLiteStore(":memory:")
    dispatcher = EnhancedDispatcher(
        plugins=None,
        sqlite_store=store,
        use_plugin_factory=True,
        lazy_load=False  # Load all plugins immediately for this test
    )
    
    print(f"Loaded {len(dispatcher._plugins)} plugins")
    
    # Index all files
    for filename in test_files:
        dispatcher.index_file(Path(filename))
    
    # Search for "calculate"
    print("\nSearching for 'calculate'...")
    results = list(dispatcher.search("calculate", limit=20))
    
    print(f"Found {len(results)} results:")
    for result in results:
        print(f"  - {result['file']}:{result['line']} - {result['snippet'].strip()}")
    
    # Cleanup
    os.chdir("/")
    import shutil
    shutil.rmtree(temp_dir)
    
    return len(results) >= len(test_files)


def main():
    """Run all tests."""
    print("Testing Enhanced Dispatcher with 48 Language Support\n")
    
    # Test basic enhanced dispatcher
    test1_ok = test_enhanced_dispatcher()
    
    # Test cross-language search
    test2_ok = test_search_across_languages()
    
    if test1_ok and test2_ok:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()