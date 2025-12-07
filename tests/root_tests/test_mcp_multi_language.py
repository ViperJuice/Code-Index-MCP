#!/usr/bin/env python3
"""Test MCP server multi-language indexing with ignore patterns."""

import asyncio
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path


def create_test_codebase(root: Path):
    """Create a test codebase with multiple languages and ignore patterns."""

    # Create .gitignore
    gitignore = """
.env
*.key
node_modules/
__pycache__/
build/
dist/
*.log
"""
    (root / ".gitignore").write_text(gitignore)

    # Python file (should index)
    (root / "app.py").write_text(
        """
def main():
    print("Hello Python")
    
class Application:
    pass
"""
    )

    # JavaScript file (should index)
    (root / "index.js").write_text(
        """
function main() {
    console.log("Hello JavaScript");
}

class App {
    constructor() {}
}
"""
    )

    # Go file (should index)
    (root / "main.go").write_text(
        """
package main

import "fmt"

func main() {
    fmt.Println("Hello Go")
}

type Server struct {
    port int
}
"""
    )

    # Rust file (should index)
    (root / "lib.rs").write_text(
        """
fn main() {
    println!("Hello Rust");
}

struct Calculator {
    value: i32,
}
"""
    )

    # Java file (should index)
    (root / "Main.java").write_text(
        """
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello Java");
    }
}
"""
    )

    # TypeScript file (should index)
    (root / "app.ts").write_text(
        """
interface User {
    name: string;
    age: number;
}

function greet(user: User): void {
    console.log(`Hello ${user.name}`);
}
"""
    )

    # C++ file (should index)
    (root / "main.cpp").write_text(
        """
#include <iostream>

class Vector {
public:
    float x, y, z;
};

int main() {
    std::cout << "Hello C++" << std::endl;
    return 0;
}
"""
    )

    # Ruby file (should index)
    (root / "app.rb").write_text(
        """
class Application
  def initialize
    @name = "MyApp"
  end
  
  def run
    puts "Hello Ruby"
  end
end
"""
    )

    # Markdown file (should index)
    (root / "README.md").write_text(
        """
# Test Project

This is a test project for multi-language indexing.

## Features
- Multiple languages
- Ignore patterns
"""
    )

    # Files that should be ignored
    (root / ".env").write_text("SECRET_KEY=12345")
    (root / "api.key").write_text("secret-api-key")
    (root / "build").mkdir(exist_ok=True)
    (root / "build" / "output.js").write_text("built code")
    (root / "node_modules").mkdir(exist_ok=True)
    (root / "node_modules" / "lib.js").write_text("dependency")
    (root / "debug.log").write_text("log data")

    return {
        "should_index": [
            "app.py",
            "index.js",
            "main.go",
            "lib.rs",
            "Main.java",
            "app.ts",
            "main.cpp",
            "app.rb",
            "README.md",
        ],
        "should_ignore": [".env", "api.key", "build/output.js", "node_modules/lib.js", "debug.log"],
    }


async def test_mcp_indexing():
    """Test MCP server indexing with ignore patterns."""
    print("\n🧪 TESTING MCP MULTI-LANGUAGE INDEXING")
    print("=" * 60)

    # Create test directory in current directory
    test_dir = Path("test_mcp_workspace")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()

    try:
        # Create test codebase
        print("\n📁 Creating test codebase...")
        file_info = create_test_codebase(test_dir)
        print(f"✅ Created {len(file_info['should_index'])} files to index")
        print(f"🚫 Created {len(file_info['should_ignore'])} files to ignore")

        # Change to test directory
        original_dir = os.getcwd()
        os.chdir(test_dir)

        # Create a simple script to call MCP tools
        test_script = """
import asyncio
import sys
sys.path.insert(0, '/app')
from mcp_server_cli import dispatcher, initialize_services, call_tool

async def main():
    # Initialize
    await initialize_services()
    
    # Reindex
    print("\\n📊 Reindexing...")
    result = await call_tool("reindex", {})
    print(result[0].text)
    
    # Get status
    print("\\n📈 Getting status...")
    result = await call_tool("get_status", {})
    status = result[0].text
    print(status)
    
    # List plugins  
    print("\\n🔌 Listing plugins...")
    result = await call_tool("list_plugins", {})
    plugins = result[0].text
    print(plugins)
    
    # Test symbol lookup
    print("\\n🔍 Testing symbol lookup...")
    symbols = ["Application", "main", "Server", "Calculator", "Vector", "User"]
    for symbol in symbols:
        result = await call_tool("symbol_lookup", {"symbol": symbol})
        print(f"  {symbol}: {result[0].text[:100]}...")
    
    # Test search
    print("\\n🔎 Testing search...")
    queries = ["Hello", "class", "struct", "function", "README"]
    for query in queries:
        result = await call_tool("search_code", {"query": query, "limit": 5})
        print(f"  '{query}': {len(eval(result[0].text))} results")

asyncio.run(main())
"""

        with open("test_mcp.py", "w") as f:
            f.write(test_script)

        # Run the test
        print("\n🚀 Running MCP indexing test...")
        result = subprocess.run([sys.executable, "test_mcp.py"], capture_output=True, text=True)

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Check the database
        print("\n🔍 Checking database...")
        db_path = Path("code_index.db")
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Count indexed files
            cursor.execute("SELECT COUNT(*) FROM files")
            total_files = cursor.fetchone()[0]
            print(f"  Total files indexed: {total_files}")

            # Check for ignored files
            ignored_found = []
            for ignored in file_info["should_ignore"]:
                cursor.execute("SELECT 1 FROM files WHERE path LIKE ?", (f"%{ignored}%",))
                if cursor.fetchone():
                    ignored_found.append(ignored)

            if ignored_found:
                print(f"  ❌ Found {len(ignored_found)} ignored files in index:")
                for f in ignored_found:
                    print(f"     - {f}")
            else:
                print("  ✅ No ignored files were indexed")

            # Check languages
            cursor.execute("SELECT DISTINCT json_extract(metadata, '$.language') FROM symbols")
            languages = [row[0] for row in cursor.fetchall() if row[0]]
            print(f"  Languages found: {', '.join(sorted(set(languages)))}")

            conn.close()
        else:
            print("  ❌ No database found!")

    finally:
        # Cleanup
        os.chdir(original_dir)
        if test_dir.exists():
            shutil.rmtree(test_dir)
        print("\n✅ Test completed and cleaned up")


if __name__ == "__main__":
    import sys

    asyncio.run(test_mcp_indexing())
