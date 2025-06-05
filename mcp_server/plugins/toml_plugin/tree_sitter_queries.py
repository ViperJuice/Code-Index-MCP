"""Tree-sitter queries for TOML language parsing.

This module provides specialized queries for extracting symbols and
structure from TOML files using tree-sitter-toml.
"""

# Symbol extraction queries
SYMBOL_QUERIES = {
    "tables": """
    (table
      (bracket_left)
      (bare_key) @table_name
      (bracket_right)) @table
    
    (table
      (bracket_left)
      (dotted_key) @table_name
      (bracket_right)) @table
    """,
    
    "table_arrays": """
    (table_array_element
      (double_bracket_left)
      (bare_key) @array_name
      (double_bracket_right)) @table_array
    
    (table_array_element
      (double_bracket_left)
      (dotted_key) @array_name
      (double_bracket_right)) @table_array
    """,
    
    "key_value_pairs": """
    (pair
      key: (bare_key) @key
      value: (_) @value) @pair
    
    (pair
      key: (quoted_key) @key
      value: (_) @value) @pair
    
    (pair
      key: (dotted_key) @key
      value: (_) @value) @pair
    """,
    
    "inline_tables": """
    (pair
      key: (_) @key
      value: (inline_table) @inline_table_value) @inline_table_pair
    """,
    
    "arrays": """
    (pair
      key: (_) @key
      value: (array) @array_value) @array_pair
    """,
    
    "strings": """
    (pair
      key: (_) @key
      value: (string) @string_value) @string_pair
    
    (pair
      key: (_) @key
      value: (multi_line_basic_string) @multiline_string) @multiline_pair
    
    (pair
      key: (_) @key
      value: (multi_line_literal_string) @multiline_literal) @multiline_literal_pair
    """,
}

# Cargo.toml specific queries
CARGO_QUERIES = {
    "package_metadata": """
    (table
      (bracket_left)
      (bare_key) @section (#eq? @section "package")
      (bracket_right))
    
    (pair
      key: (bare_key) @key (#match? @key "^(name|version|edition|authors|description|license|repository)$")
      value: (_) @value) @package_field
    """,
    
    "dependencies": """
    (table
      (bracket_left)
      (bare_key) @section (#match? @section "dependencies|dev-dependencies|build-dependencies")
      (bracket_right))
    
    (pair
      key: (bare_key) @dep_name
      value: (string) @version) @simple_dependency
    
    (pair
      key: (bare_key) @dep_name
      value: (inline_table) @dep_spec) @complex_dependency
    """,
    
    "features": """
    (table
      (bracket_left)
      (bare_key) @section (#eq? @section "features")
      (bracket_right))
    
    (pair
      key: (bare_key) @feature_name
      value: (array) @feature_deps) @feature
    """,
    
    "workspace": """
    (table
      (bracket_left)
      (bare_key) @section (#eq? @section "workspace")
      (bracket_right))
    
    (pair
      key: (bare_key) @key (#eq? @key "members")
      value: (array) @members) @workspace_members
    """,
}

# pyproject.toml specific queries
PYPROJECT_QUERIES = {
    "build_system": """
    (table
      (bracket_left)
      (bare_key) @section (#eq? @section "build-system")
      (bracket_right))
    
    (pair
      key: (bare_key) @key (#match? @key "requires|build-backend")
      value: (_) @value) @build_field
    """,
    
    "project_metadata": """
    (table
      (bracket_left)
      (bare_key) @section (#eq? @section "project")
      (bracket_right))
    
    (pair
      key: (bare_key) @key (#match? @key "^(name|version|description|readme|requires-python|license|authors|maintainers)$")
      value: (_) @value) @project_field
    """,
    
    "project_dependencies": """
    (table
      (bracket_left)
      (dotted_key) @section (#match? @section "^project\\.(dependencies|optional-dependencies)")
      (bracket_right))
    """,
    
    "tool_sections": """
    (table
      (bracket_left)
      (dotted_key) @section (#match? @section "^tool\\.")
      (bracket_right)) @tool_section
    """,
    
    "poetry_config": """
    (table
      (bracket_left)
      (dotted_key) @section (#match? @section "^tool\\.poetry")
      (bracket_right))
    
    (table
      (bracket_left)
      (dotted_key) @section (#match? @section "^tool\\.poetry\\.(dependencies|dev-dependencies)")
      (bracket_right))
    """,
}

# Structure analysis queries
STRUCTURE_QUERIES = {
    "nested_tables": """
    (table
      (bracket_left)
      (dotted_key
        (bare_key) @parent
        (dot)
        (bare_key) @child) @path
      (bracket_right)) @nested_table
    """,
    
    "deep_nesting": """
    (table
      (bracket_left)
      (dotted_key
        (bare_key) @level1
        (dot)
        (bare_key) @level2
        (dot)
        (bare_key) @level3) @deep_path
      (bracket_right)) @deep_table
    """,
    
    "comments": """
    (comment) @comment
    """,
}

# Value type detection queries
VALUE_TYPE_QUERIES = {
    "strings": """
    (pair
      value: (string) @string_value)
    (pair
      value: (multi_line_basic_string) @multiline_string)
    (pair
      value: (multi_line_literal_string) @literal_string)
    """,
    
    "numbers": """
    (pair
      value: (integer) @integer_value)
    (pair
      value: (float) @float_value)
    """,
    
    "booleans": """
    (pair
      value: (boolean) @boolean_value)
    """,
    
    "dates": """
    (pair
      value: (offset_date_time) @datetime_value)
    (pair
      value: (local_date_time) @local_datetime)
    (pair
      value: (local_date) @date_value)
    (pair
      value: (local_time) @time_value)
    """,
}


def get_all_queries():
    """Get all available queries for TOML parsing."""
    return {
        **SYMBOL_QUERIES,
        **CARGO_QUERIES,
        **PYPROJECT_QUERIES,
        **STRUCTURE_QUERIES,
        **VALUE_TYPE_QUERIES,
    }


def get_cargo_specific_queries():
    """Get queries specific to Cargo.toml files."""
    return CARGO_QUERIES


def get_pyproject_specific_queries():
    """Get queries specific to pyproject.toml files."""
    return PYPROJECT_QUERIES