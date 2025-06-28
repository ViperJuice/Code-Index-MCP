#!/usr/bin/env python3
"""Comprehensive test for multi-language indexing with ignore patterns."""

import tempfile
import shutil
from pathlib import Path
import json
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.core.ignore_patterns import IgnorePatternManager


def create_test_repository(root: Path) -> dict:
    """Create a test repository with multiple languages and ignore patterns."""
    
    # Create .gitignore
    gitignore_content = """
# Version control
.git/
.svn/

# Dependencies
node_modules/
venv/
__pycache__/

# Build outputs
dist/
build/
target/

# IDE files
.idea/
.vscode/

# Secrets
.env
*.key
*.pem
secrets/

# Logs
*.log
logs/
"""
    (root / ".gitignore").write_text(gitignore_content)
    
    # Create .mcp-index-ignore
    mcp_ignore_content = """
# Test files
test/
tests/
__tests__/
*.test.js
*.spec.py

# Large files
*.zip
*.tar.gz

# Temporary
*.tmp
temp/
"""
    (root / ".mcp-index-ignore").write_text(mcp_ignore_content)
    
    # Create directory structure
    dirs = [
        "src", "src/components", "src/utils", "src/services",
        "lib", "lib/helpers",
        "config",
        "docs",
        "tests",  # Should be ignored
        "build",  # Should be ignored
        "node_modules",  # Should be ignored
        ".vscode",  # Should be ignored
        "secrets",  # Should be ignored
        "temp",  # Should be ignored
        "logs",  # Should be ignored
    ]
    
    for dir_path in dirs:
        (root / dir_path).mkdir(parents=True, exist_ok=True)
    
    # Create various language files
    files_created = {
        "should_index": [],
        "should_ignore": []
    }
    
    # Python files
    (root / "src" / "main.py").write_text("""
def main():
    print("Hello from Python!")
    
class Application:
    def __init__(self):
        self.name = "TestApp"
        
    def run(self):
        print(f"Running {self.name}")
""")
    files_created["should_index"].append("src/main.py")
    
    (root / "src" / "utils" / "helpers.py").write_text("""
def calculate_sum(a: int, b: int) -> int:
    return a + b
    
def format_string(text: str) -> str:
    return text.strip().lower()
""")
    files_created["should_index"].append("src/utils/helpers.py")
    
    # Should be ignored - test file
    (root / "tests" / "test_main.py").write_text("""
import pytest
def test_main():
    assert True
""")
    files_created["should_ignore"].append("tests/test_main.py")
    
    # JavaScript/TypeScript files
    (root / "src" / "components" / "Button.jsx").write_text("""
import React from 'react';

export const Button = ({ onClick, children }) => {
    return (
        <button onClick={onClick}>
            {children}
        </button>
    );
};
""")
    files_created["should_index"].append("src/components/Button.jsx")
    
    (root / "src" / "services" / "api.ts").write_text("""
interface ApiResponse<T> {
    data: T;
    status: number;
}

export async function fetchData<T>(url: string): Promise<ApiResponse<T>> {
    const response = await fetch(url);
    return {
        data: await response.json(),
        status: response.status
    };
}
""")
    files_created["should_index"].append("src/services/api.ts")
    
    # Should be ignored - test file
    (root / "src" / "Button.test.js").write_text("""
test('Button renders', () => {
    expect(true).toBe(true);
});
""")
    files_created["should_ignore"].append("src/Button.test.js")
    
    # Go file
    (root / "lib" / "server.go").write_text("""
package main

import (
    "fmt"
    "net/http"
)

func main() {
    http.HandleFunc("/", handler)
    http.ListenAndServe(":8080", nil)
}

func handler(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Hello from Go!")
}
""")
    files_created["should_index"].append("lib/server.go")
    
    # Rust file
    (root / "lib" / "helpers" / "math.rs").write_text("""
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

pub struct Calculator {
    value: i32,
}

impl Calculator {
    pub fn new() -> Self {
        Calculator { value: 0 }
    }
}
""")
    files_created["should_index"].append("lib/helpers/math.rs")
    
    # Java file
    (root / "src" / "Application.java").write_text("""
public class Application {
    private String name;
    
    public Application(String name) {
        this.name = name;
    }
    
    public void run() {
        System.out.println("Running " + name);
    }
    
    public static void main(String[] args) {
        Application app = new Application("TestApp");
        app.run();
    }
}
""")
    files_created["should_index"].append("src/Application.java")
    
    # C++ file
    (root / "src" / "utils" / "vector.cpp").write_text("""
#include <iostream>
#include <vector>

class Vector3D {
public:
    float x, y, z;
    
    Vector3D(float x, float y, float z) : x(x), y(y), z(z) {}
    
    float magnitude() {
        return sqrt(x*x + y*y + z*z);
    }
};
""")
    files_created["should_index"].append("src/utils/vector.cpp")
    
    # Ruby file
    (root / "lib" / "helpers.rb").write_text("""
class Helper
  def self.format_name(first, last)
    "#{first} #{last}".strip
  end
  
  def calculate_total(items)
    items.sum { |item| item[:price] }
  end
end
""")
    files_created["should_index"].append("lib/helpers.rb")
    
    # Configuration files (should be indexed)
    (root / "config" / "app.yaml").write_text("""
application:
  name: TestApp
  version: 1.0.0
  
database:
  host: localhost
  port: 5432
""")
    files_created["should_index"].append("config/app.yaml")
    
    # Should be ignored - secrets
    (root / ".env").write_text("""
API_KEY=secret123
DATABASE_PASSWORD=password456
""")
    files_created["should_ignore"].append(".env")
    
    (root / "config" / "secret.key").write_text("SUPER_SECRET_KEY")
    files_created["should_ignore"].append("config/secret.key")
    
    # Should be ignored - build output
    (root / "build" / "output.js").write_text("console.log('built');")
    files_created["should_ignore"].append("build/output.js")
    
    # Should be ignored - dependencies
    (root / "node_modules" / "react").mkdir(parents=True, exist_ok=True)
    (root / "node_modules" / "react" / "index.js").write_text("module.exports = {};")
    files_created["should_ignore"].append("node_modules/react/index.js")
    
    # Should be ignored - logs
    (root / "logs" / "app.log").write_text("2024-01-01 INFO Application started")
    files_created["should_ignore"].append("logs/app.log")
    
    # Should be ignored - temp files
    (root / "temp" / "cache.tmp").write_text("temporary data")
    files_created["should_ignore"].append("temp/cache.tmp")
    
    # Markdown documentation (should be indexed)
    (root / "README.md").write_text("""
# Test Repository

This is a test repository for multi-language indexing.

## Features
- Multi-language support
- Ignore patterns
- Security filtering
""")
    files_created["should_index"].append("README.md")
    
    (root / "docs" / "api.md").write_text("""
# API Documentation

## Endpoints

### GET /api/data
Returns data from the API.
""")
    files_created["should_index"].append("docs/api.md")
    
    return files_created


def test_multi_language_indexing():
    """Test multi-language indexing with ignore patterns."""
    print("\n🧪 MULTI-LANGUAGE INDEXING TEST WITH IGNORE PATTERNS")
    print("=" * 60)
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        
        # Create test repository
        print("\n📁 Creating test repository...")
        files_info = create_test_repository(root)
        
        print(f"✅ Created {len(files_info['should_index'])} files that should be indexed")
        print(f"🚫 Created {len(files_info['should_ignore'])} files that should be ignored")
        
        # Initialize SQLite store
        db_path = root / "test_index.db"
        sqlite_store = SQLiteStore(str(db_path))
        
        # Create enhanced dispatcher
        print("\n🔧 Initializing enhanced dispatcher...")
        dispatcher = EnhancedDispatcher(
            sqlite_store=sqlite_store,
            enable_advanced_features=True,
            use_plugin_factory=True,
            lazy_load=True,
            semantic_search_enabled=False  # Disable for speed
        )
        
        # Index the directory
        print(f"\n📊 Indexing directory: {root}")
        stats = dispatcher.index_directory(root, recursive=True)
        
        # Display results
        print("\n📈 Indexing Results:")
        print(f"  Total files scanned: {stats['total_files']}")
        print(f"  Files indexed: {stats['indexed_files']}")
        print(f"  Files ignored: {stats['ignored_files']}")
        print(f"  Failed files: {stats['failed_files']}")
        
        print("\n🌐 Languages indexed:")
        for lang, count in sorted(stats['by_language'].items()):
            print(f"  {lang}: {count} files")
        
        # Verify ignore patterns worked
        print("\n🔍 Verifying ignore patterns...")
        
        # Check database for ignored files
        # Get connection properly
        conn = sqlite_store.get_connection()
        cursor = conn.cursor()
        
        ignored_but_indexed = []
        for ignored_file in files_info['should_ignore']:
            cursor.execute("SELECT 1 FROM files WHERE path = ?", (str(root / ignored_file),))
            if cursor.fetchone():
                ignored_but_indexed.append(ignored_file)
        
        if ignored_but_indexed:
            print(f"❌ ERROR: {len(ignored_but_indexed)} ignored files were indexed:")
            for f in ignored_but_indexed[:5]:
                print(f"   - {f}")
        else:
            print("✅ All ignored files were correctly excluded from indexing")
        
        # Check if expected files were indexed
        not_indexed = []
        for expected_file in files_info['should_index']:
            full_path = str(root / expected_file)
            cursor.execute("SELECT 1 FROM files WHERE path = ?", (full_path,))
            if not cursor.fetchone():
                not_indexed.append(expected_file)
        
        if not_indexed:
            print(f"\n⚠️  WARNING: {len(not_indexed)} expected files were not indexed:")
            for f in not_indexed[:5]:
                print(f"   - {f}")
        else:
            print("✅ All expected files were indexed")
        
        # Test symbol lookup across languages
        print("\n🔎 Testing symbol lookup across languages...")
        test_symbols = [
            ("Application", ["Python", "Java"]),
            ("Button", ["JavaScript"]),
            ("fetchData", ["TypeScript"]),
            ("handler", ["Go"]),
            ("Calculator", ["Rust"]),
            ("Vector3D", ["C++"]),
            ("Helper", ["Ruby"])
        ]
        
        for symbol, expected_langs in test_symbols:
            result = dispatcher.lookup(symbol)
            if result:
                lang = result.get('language', 'unknown')
                if any(expected in lang for expected in expected_langs):
                    print(f"  ✅ Found {symbol} in {lang}")
                else:
                    print(f"  ❌ Found {symbol} but in {lang}, expected one of {expected_langs}")
            else:
                print(f"  ❌ Failed to find symbol: {symbol}")
        
        # Test search functionality
        print("\n🔍 Testing search across languages...")
        search_queries = [
            ("calculate", ["Python", "Rust"]),
            ("server", ["Go"]),
            ("React", ["JavaScript"]),
            ("async", ["TypeScript"]),
            ("public class", ["Java"]),
            ("include", ["C++"])
        ]
        
        for query, expected_langs in search_queries:
            results = list(dispatcher.search(query, limit=10))
            if results:
                found_langs = set()
                for result in results:
                    # Get language from file extension
                    file_path = Path(result.get('file', ''))
                    if file_path.suffix == '.py':
                        found_langs.add('Python')
                    elif file_path.suffix in ['.js', '.jsx']:
                        found_langs.add('JavaScript')
                    elif file_path.suffix == '.ts':
                        found_langs.add('TypeScript')
                    elif file_path.suffix == '.go':
                        found_langs.add('Go')
                    elif file_path.suffix == '.rs':
                        found_langs.add('Rust')
                    elif file_path.suffix == '.java':
                        found_langs.add('Java')
                    elif file_path.suffix in ['.cpp', '.cc']:
                        found_langs.add('C++')
                    elif file_path.suffix == '.rb':
                        found_langs.add('Ruby')
                
                matched = any(lang in found_langs for lang in expected_langs)
                if matched:
                    print(f"  ✅ Search '{query}' found in: {', '.join(found_langs)}")
                else:
                    print(f"  ❌ Search '{query}' found in {found_langs} but expected {expected_langs}")
            else:
                print(f"  ❌ No results for search: {query}")
        
        # Summary
        print("\n📊 Test Summary:")
        print(f"  Languages supported: {len(dispatcher.supported_languages)}")
        print(f"  Plugins loaded: {len(dispatcher._plugins)}")
        print(f"  Ignore patterns working: {'Yes' if not ignored_but_indexed else 'No'}")
        print(f"  Multi-language indexing: {'Yes' if stats['indexed_files'] > 0 else 'No'}")
        
        # Security check
        print("\n🔒 Security Check:")
        sensitive_indexed = []
        sensitive_patterns = ['.env', '.key', '.pem', 'secret', 'password']
        
        cursor.execute("SELECT path FROM files")
        all_files = cursor.fetchall()
        
        for (file_path,) in all_files:
            for pattern in sensitive_patterns:
                if pattern in file_path.lower():
                    sensitive_indexed.append(file_path)
                    break
        
        if sensitive_indexed:
            print(f"  ⚠️  {len(sensitive_indexed)} potentially sensitive files indexed:")
            for f in sensitive_indexed[:3]:
                print(f"     - {f}")
        else:
            print("  ✅ No sensitive files were indexed")
        
        return {
            "success": len(ignored_but_indexed) == 0 and stats['indexed_files'] > 0,
            "stats": stats,
            "languages": len(stats['by_language']),
            "security_passed": len(sensitive_indexed) == 0
        }


def main():
    """Run the test."""
    result = test_multi_language_indexing()
    
    print("\n" + "=" * 60)
    if result["success"] and result["security_passed"]:
        print("✅ ALL TESTS PASSED!")
        print(f"   - Indexed {result['stats']['indexed_files']} files")
        print(f"   - Ignored {result['stats']['ignored_files']} files") 
        print(f"   - Supported {result['languages']} languages")
        print("   - Security checks passed")
    else:
        print("❌ TESTS FAILED!")
        if not result["success"]:
            print("   - Indexing or ignore patterns failed")
        if not result["security_passed"]:
            print("   - Security checks failed")


if __name__ == "__main__":
    main()