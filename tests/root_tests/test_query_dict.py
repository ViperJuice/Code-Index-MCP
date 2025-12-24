#!/usr/bin/env python3
"""Debug the query.captures dict structure."""

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

print("Testing query.captures() dictionary...")
try:
    query = rust_language.query(query_string)
    captures_dict = query.captures(tree.root_node)

    print(f"Captures is a dict: {isinstance(captures_dict, dict)}")
    print(f"Dict keys: {list(captures_dict.keys())}")
    print("Dict items:")

    for key, value in captures_dict.items():
        print(f"\n  Key: {key} (type: {type(key)})")
        print(f"  Value type: {type(value)}")
        print(f"  Value: {value}")

        if isinstance(value, list):
            print(f"  List length: {len(value)}")
            for i, item in enumerate(value):
                print(f"    Item {i}: {item} (type: {type(item)})")
                if hasattr(item, "text"):
                    print(f"      Text: {rust_code[item.start_byte:item.end_byte].decode()}")
                    print(f"      Type: {item.type}")
                    print(f"      Line: {item.start_point[0] + 1}")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 50)
print("\nTrying matches() instead...")

try:
    matches = query.matches(tree.root_node)
    print(f"Matches type: {type(matches)}")

    matches_list = list(matches)
    print(f"Number of matches: {len(matches_list)}")

    for i, match in enumerate(matches_list):
        print(f"\nMatch {i}:")
        print(f"  Type: {type(match)}")
        print(f"  Value: {match}")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
