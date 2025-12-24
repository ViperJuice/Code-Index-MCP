#!/usr/bin/env python3
"""Debug tree_sitter_languages API."""

import tree_sitter_languages

print("Testing tree_sitter_languages API...")

# Check what get_parser actually returns
try:
    print("\n1. Testing get_parser return type:")
    parser_result = tree_sitter_languages.get_parser("python")
    print(f"   Type: {type(parser_result)}")
    print(f"   Value: {parser_result}")
    print(f"   Dir: {[x for x in dir(parser_result) if not x.startswith('_')]}")
except Exception as e:
    print(f"   Error: {e}")
    import traceback

    traceback.print_exc()

# Check what get_language returns
try:
    print("\n2. Testing get_language return type:")
    lang_result = tree_sitter_languages.get_language("python")
    print(f"   Type: {type(lang_result)}")
    print(f"   Value: {lang_result}")
    print(f"   Dir: {[x for x in dir(lang_result) if not x.startswith('_')]}")
except Exception as e:
    print(f"   Error: {e}")

# Try the approach from working plugins (ctypes)
print("\n3. Testing ctypes approach (from working plugins):")
try:
    import ctypes
    from pathlib import Path

    from tree_sitter import Language, Parser

    lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
    print(f"   Library path: {lib_path}")
    print(f"   Library exists: {lib_path.exists()}")

    if lib_path.exists():
        lib = ctypes.CDLL(str(lib_path))
        lib.tree_sitter_python.restype = ctypes.c_void_p

        language = Language(lib.tree_sitter_python())
        parser = Parser()
        parser.language = language

        # Test parsing
        tree = parser.parse(b"def hello(): pass")
        print(f"   ✓ Successfully parsed, root type: {tree.root_node.type}")
    else:
        # Try the .dll extension for Windows
        lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.dll"
        if lib_path.exists():
            print(f"   Found Windows DLL: {lib_path}")
except Exception as e:
    print(f"   Error: {e}")
    import traceback

    traceback.print_exc()

# Check the tree_sitter_languages package structure
print("\n4. Package structure:")
import os

pkg_path = Path(tree_sitter_languages.__path__[0])
print(f"   Package path: {pkg_path}")
print(f"   Contents: {list(os.listdir(pkg_path))[:10]}")
