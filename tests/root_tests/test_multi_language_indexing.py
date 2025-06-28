#!/usr/bin/env python3
"""Test multi-language indexing functionality."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
import tempfile
import shutil

def create_test_files(test_dir: Path):
    """Create test files in various languages."""
    test_files = {
        "test.py": "def hello(): print('Python')",
        "test.js": "function hello() { console.log('JavaScript'); }",
        "test.go": "package main\nfunc hello() { fmt.Println(\"Go\") }",
        "test.rs": "fn hello() { println!(\"Rust\"); }",
        "test.java": "public class Test { void hello() { System.out.println(\"Java\"); } }",
        "test.c": "#include <stdio.h>\nvoid hello() { printf(\"C\"); }",
        "test.cpp": "#include <iostream>\nvoid hello() { std::cout << \"C++\"; }",
        "test.md": "# Test Markdown\n\nThis is a test document.",
        "test.txt": "This is a plain text file for testing.",
        "test.yaml": "test:\n  key: value",
        "test.json": '{"test": "json"}',
        "test.html": "<html><body>Test HTML</body></html>",
        "test.css": "body { color: red; }",
        "test.sh": "#!/bin/bash\necho 'Shell script'",
        "test.rb": "def hello\n  puts 'Ruby'\nend",
        "test.swift": "func hello() { print(\"Swift\") }",
        "test.kt": "fun hello() { println(\"Kotlin\") }",
        "test.dart": "void hello() { print('Dart'); }",
        ".env": "SECRET_KEY=this_should_be_ignored",
        "secrets.txt": "password=should_be_ignored",
        "__pycache__/test.pyc": "# This should be ignored",
    }
    
    for filename, content in test_files.items():
        filepath = test_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content)
        
    # Create .mcp-index-ignore
    ignore_content = """
# Test ignore patterns
*.env
.env*
*secret*
*password*
__pycache__/
*.pyc
"""
    (test_dir / ".mcp-index-ignore").write_text(ignore_content)
    
    return test_files

def test_multi_language_indexing():
    """Test that all supported languages are indexed."""
    print("Testing Multi-Language Indexing")
    print("="*60)
    
    # Create temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        test_files = create_test_files(test_dir)
        
        # Initialize components
        store = SQLiteStore(":memory:")  # In-memory for testing
        # Use plugin factory to load all plugins
        dispatcher = EnhancedDispatcher(
            plugins=[],  # Empty list, will use factory
            sqlite_store=store,
            use_plugin_factory=True,
            lazy_load=False  # Load all plugins immediately for testing
        )
        
        # Index the directory
        print(f"\nIndexing directory: {test_dir}")
        stats = dispatcher.index_directory(test_dir, recursive=True)
        
        # Display results
        print(f"\nIndexing Results:")
        print(f"  Total files found: {stats['total_files']}")
        print(f"  Files indexed: {stats['indexed_files']}")
        print(f"  Files ignored: {stats['ignored_files']}")
        print(f"  Failed files: {stats['failed_files']}")
        
        print(f"\nLanguage Breakdown:")
        for lang, count in sorted(stats['by_language'].items()):
            print(f"  {lang}: {count} files")
            
        # Verify sensitive files were ignored
        print(f"\n✅ Security Check:")
        if stats['ignored_files'] >= 3:  # .env, secrets.txt, __pycache__/test.pyc
            print(f"  Sensitive files properly ignored: {stats['ignored_files']} files")
        else:
            print(f"  ❌ Warning: Expected at least 3 ignored files, got {stats['ignored_files']}")
            
        # Verify multi-language support
        print(f"\n✅ Language Support Check:")
        expected_languages = {'python', 'javascript', 'go', 'rust', 'java', 'c', 'cpp', 
                            'markdown', 'yaml', 'json', 'html', 'css', 'bash', 'ruby',
                            'swift', 'kotlin', 'dart'}
        indexed_languages = set(stats['by_language'].keys())
        
        if len(indexed_languages) >= 15:
            print(f"  Successfully indexed {len(indexed_languages)} different languages")
        else:
            print(f"  ❌ Warning: Expected at least 15 languages, got {len(indexed_languages)}")
            missing = expected_languages - indexed_languages
            if missing:
                print(f"  Missing languages: {missing}")
                
        # Test file watcher extensions
        from mcp_server.plugins.language_registry import get_all_extensions
        all_extensions = get_all_extensions()
        print(f"\n✅ Extension Support:")
        print(f"  Total supported extensions: {len(all_extensions)}")
        print(f"  Sample extensions: {list(all_extensions)[:10]}...")
        
        return stats['indexed_files'] > 10 and stats['ignored_files'] > 0

if __name__ == "__main__":
    success = test_multi_language_indexing()
    if success:
        print("\n✅ Multi-language indexing test PASSED!")
    else:
        print("\n❌ Multi-language indexing test FAILED!")
        sys.exit(1)