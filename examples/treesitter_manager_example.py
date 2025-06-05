#!/usr/bin/env python3
"""
Example demonstrating TreeSitterManager usage.

This example shows how to use the TreeSitterManager for:
- Parsing different programming languages
- Extracting symbols from code
- Using the caching system
- Async operations
- Performance monitoring
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the parent directory to the path to import mcp_server
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.utils.treesitter_manager import (
    TreeSitterManager, tree_sitter_manager,
    parse_content, extract_symbols, is_language_supported
)


def basic_parsing_example():
    """Demonstrate basic parsing functionality."""
    print("=== Basic Parsing Example ===")
    
    # Python code sample
    python_code = '''
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

class Calculator:
    """A simple calculator class."""
    
    def __init__(self):
        self.history = []
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

# Global variable
PI = 3.14159
'''
    
    # Parse the code
    print("Parsing Python code...")
    result = parse_content(python_code, 'python')
    
    print(f"✓ Parse successful: {result.error is None}")
    print(f"✓ Parse time: {result.parse_time_ms:.2f}ms")
    print(f"✓ Language: {result.language}")
    print(f"✓ Content hash: {result.source_hash}")
    print(f"✓ Cached: {result.cached}")
    
    # Test caching - second parse should be faster
    print("\nTesting cache...")
    result2 = parse_content(python_code, 'python')
    print(f"✓ Second parse time: {result2.parse_time_ms:.2f}ms")
    print(f"✓ Second parse cached: {result2.cached}")


def symbol_extraction_example():
    """Demonstrate symbol extraction."""
    print("\n=== Symbol Extraction Example ===")
    
    # Multi-language code samples
    code_samples = {
        'python': '''
import os
from typing import List, Optional

def main():
    """Entry point."""
    print("Hello, World!")

class DataProcessor:
    def __init__(self, config: dict):
        self.config = config
        self.data = []
    
    def process(self, items: List[str]) -> Optional[List[str]]:
        return [item.upper() for item in items]

CONSTANT = 42
variable = "test"
''',
        'javascript': '''
const fs = require('fs');

function greet(name) {
    return `Hello, ${name}!`;
}

class Person {
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }
    
    introduce() {
        return greet(this.name);
    }
    
    getAge() {
        return this.age;
    }
}

const DEFAULT_NAME = "Anonymous";
let currentUser = null;
''',
        'go': '''
package main

import (
    "fmt"
    "strings"
)

func main() {
    fmt.Println("Hello, World!")
}

type Person struct {
    Name string
    Age  int
}

func (p Person) Greet() string {
    return fmt.Sprintf("Hello, I'm %s", p.Name)
}

func (p Person) IsAdult() bool {
    return p.Age >= 18
}

const DefaultAge = 18
var GlobalCounter = 0
'''
    }
    
    for language, code in code_samples.items():
        if not is_language_supported(language):
            print(f"⚠ {language}: Language not supported")
            continue
        
        print(f"\n--- {language.upper()} Symbols ---")
        
        # Extract all symbols
        symbols = extract_symbols(code, language)
        
        for symbol_type, symbol_list in symbols.items():
            if symbol_list:  # Only show non-empty categories
                print(f"{symbol_type.capitalize()}: {len(symbol_list)} items")
                for symbol in symbol_list:
                    start_line = symbol['start_point'][0] + 1  # Convert to 1-based line number
                    print(f"  - {symbol['name']} (line {start_line})")


async def async_parsing_example():
    """Demonstrate asynchronous parsing."""
    print("\n=== Async Parsing Example ===")
    
    code_samples = [
        ('python', 'def async_func(): pass'),
        ('javascript', 'async function asyncFunc() {}'),
        ('go', 'func asyncFunc() {}'),
        ('rust', 'fn async_func() {}'),
        ('java', 'public void asyncMethod() {}'),
    ]
    
    print("Parsing multiple languages concurrently...")
    
    # Create async parsing tasks
    tasks = []
    for language, code in code_samples:
        if is_language_supported(language):
            task = tree_sitter_manager.parse_async(code, language)
            tasks.append((language, task))
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
    
    # Display results
    for (language, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            print(f"⚠ {language}: Error - {result}")
        else:
            print(f"✓ {language}: {result.parse_time_ms:.2f}ms ({'cached' if result.cached else 'fresh'})")


def performance_monitoring_example():
    """Demonstrate performance monitoring."""
    print("\n=== Performance Monitoring Example ===")
    
    # Get comprehensive performance statistics
    stats = tree_sitter_manager.get_performance_stats()
    
    print("Overall Statistics:")
    print(f"  Total parses: {stats['total_parses']}")
    print(f"  Cache hit rate: {stats['cache_hit_rate']:.2%}")
    print(f"  Average parse time: {stats['average_parse_time_ms']:.2f}ms")
    
    print("\nParser Cache:")
    print(f"  Cached languages: {stats['parser_cache']['size']}")
    print(f"  Languages: {', '.join(stats['parser_cache']['languages'])}")
    
    print("\nParse Cache:")
    print(f"  Cached entries: {stats['parse_cache']['total_entries']}")
    print(f"  Total size: {stats['parse_cache']['total_size_bytes']:,} bytes")
    print(f"  Average entry size: {stats['parse_cache']['average_entry_size']:.0f} bytes")
    
    if stats['query_cache']['total_queries'] > 0:
        print("\nQuery Cache:")
        print(f"  Cached queries: {stats['query_cache']['total_queries']}")


def file_parsing_example():
    """Demonstrate file parsing with language detection."""
    print("\n=== File Parsing Example ===")
    
    # Create some temporary test files
    test_files = {
        'example.py': '''
def hello_world():
    """A simple greeting function."""
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
''',
        'example.js': '''
function helloWorld() {
    console.log("Hello, World!");
}

helloWorld();
''',
        'example.go': '''
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
'''
    }
    
    try:
        # Create test files
        for filename, content in test_files.items():
            Path(filename).write_text(content)
        
        # Parse each file
        for filename in test_files.keys():
            print(f"\nParsing {filename}:")
            
            # Parse file (language is auto-detected from extension)
            result = tree_sitter_manager.parse_file(filename)
            
            if result.error:
                print(f"  ❌ Error: {result.error}")
            else:
                print(f"  ✓ Parse time: {result.parse_time_ms:.2f}ms")
                print(f"  ✓ Detected language: {result.language}")
                
                # Extract symbols from the file
                with open(filename, 'rb') as f:
                    file_content = f.read()
                
                symbols = extract_symbols(file_content, result.language)
                for symbol_type, symbol_list in symbols.items():
                    if symbol_list:
                        print(f"  ✓ {symbol_type}: {', '.join(s['name'] for s in symbol_list)}")
    
    finally:
        # Clean up test files
        for filename in test_files.keys():
            Path(filename).unlink(missing_ok=True)


def advanced_features_example():
    """Demonstrate advanced features."""
    print("\n=== Advanced Features Example ===")
    
    # Test language support
    print("Language Support:")
    supported = tree_sitter_manager.get_supported_languages()
    print(f"  Total supported languages: {len(supported)}")
    
    # Test some common languages
    common_languages = ['python', 'javascript', 'typescript', 'java', 'go', 'rust', 'cpp', 'c']
    for lang in common_languages:
        status = "✓" if is_language_supported(lang) else "✗"
        print(f"  {status} {lang}")
    
    # Test node utilities
    print("\nNode Utilities:")
    python_code = 'def test_function(param): return param * 2'
    result = parse_content(python_code, 'python')
    
    if result.root_node:
        # Find node at specific position
        node_at_pos = tree_sitter_manager.find_node_at_position(result.root_node, 0, 5)  # Position in "def"
        if node_at_pos:
            print(f"  Node at (0,5): {node_at_pos.type}")
        
        # Get text content
        text = tree_sitter_manager.get_node_text(result.root_node, python_code)
        print(f"  Root node text length: {len(text)} chars")


async def main():
    """Run all examples."""
    print("TreeSitterManager Examples")
    print("=" * 50)
    
    try:
        # Run examples
        basic_parsing_example()
        symbol_extraction_example()
        await async_parsing_example()
        performance_monitoring_example()
        file_parsing_example()
        advanced_features_example()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully! ✓")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())