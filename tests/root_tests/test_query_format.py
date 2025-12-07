#!/usr/bin/env python3
"""Test tree-sitter query capture format."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import ctypes

import tree_sitter_languages
from tree_sitter import Language, Parser


def test_query_format():
    """Test what format captures() returns."""
    print("=== Testing Tree-Sitter Query Format ===\n")

    # Load Go language
    lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
    lib = ctypes.CDLL(str(lib_path))

    func_name = "tree_sitter_go"
    getattr(lib, func_name).restype = ctypes.c_void_p

    language = Language(getattr(lib, func_name)())
    parser = Parser()
    parser.language = language

    # Test code
    code = """package main

func hello() string {
    return "world"
}

type Person struct {
    Name string
}"""

    tree = parser.parse(code.encode("utf-8"))

    # Test query
    query_string = """
        (function_declaration name: (identifier) @function)
        (type_declaration (type_spec name: (type_identifier) @type))
    """

    query = language.query(query_string)
    captures = query.captures(tree.root_node)

    print(f"Type of captures: {type(captures)}")
    print(f"Length: {len(captures)}")

    if isinstance(captures, list):
        print("\nCaptures is a list of tuples:")
        for i, capture in enumerate(captures):
            print(
                f"  [{i}] Type: {type(capture)}, Length: {len(capture) if hasattr(capture, '__len__') else 'N/A'}"
            )
            if isinstance(capture, tuple) and len(capture) == 2:
                node, name = capture
                print(f"      Node: {node.type}, Name: {name}")
                print(f"      Text: {code[node.start_byte:node.end_byte]}")
    elif isinstance(captures, dict):
        print("\nCaptures is a dictionary:")
        for key, value in captures.items():
            print(
                f"  Key: {key}, Value type: {type(value)}, Length: {len(value) if hasattr(value, '__len__') else 'N/A'}"
            )
            if isinstance(value, list):
                for node in value:
                    print(f"    Node type: {node.type}")
                    print(f"    Text: {code[node.start_byte:node.end_byte]}")


if __name__ == "__main__":
    test_query_format()
