#!/usr/bin/env python3
"""Debug the query.captures issue."""

import ctypes
from pathlib import Path

import tree_sitter_languages
from tree_sitter import Language, Parser

# Set up parser using ctypes
lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
lib = ctypes.CDLL(str(lib_path))

# Test with Rust
lib.tree_sitter_rust.restype = ctypes.c_void_p
rust_language = Language(lib.tree_sitter_rust())
rust_parser = Parser()
rust_parser.language = rust_language

# Parse some Rust code
rust_code = b"""fn hello() -> &'static str {
    "Hello, World!"
}

struct User {
    name: String,
    age: u32,
}
"""

tree = rust_parser.parse(rust_code)

# Test query
query_string = """
(function_item name: (identifier) @function)
(struct_item name: (type_identifier) @struct)
"""

print("Testing query.captures()...")
try:
    query = rust_language.query(query_string)
    print(f"Query created: {query}")

    # Check what captures returns
    captures_result = query.captures(tree.root_node)
    print(f"Captures type: {type(captures_result)}")

    # Try to iterate
    capture_list = list(captures_result)
    print(f"Number of captures: {len(capture_list)}")

    for i, capture in enumerate(capture_list):
        print(f"\nCapture {i}:")
        print(f"  Type: {type(capture)}")
        print(f"  Length: {len(capture) if hasattr(capture, '__len__') else 'N/A'}")
        print(f"  Value: {capture}")

        # If it's a tuple/list, examine elements
        if hasattr(capture, "__getitem__"):
            for j, elem in enumerate(capture):
                print(f"  Element {j}: {elem} (type: {type(elem)})")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 50)
print("\nTrying alternative approaches...")

# Check if there's a different API
print("\nQuery methods:")
query = rust_language.query(query_string)
print([m for m in dir(query) if not m.startswith("_")])
