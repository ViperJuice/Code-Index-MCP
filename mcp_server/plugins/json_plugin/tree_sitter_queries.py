"""
Tree-sitter query patterns for JSON parsing.

These queries extract structured information from JSON files using Tree-sitter.
"""

# Tree-sitter query patterns for JSON
JSON_QUERIES = {
    "pairs": """
    (pair
      key: (string (string_content) @key.name)
      value: (_) @value
    ) @pair
    """,
    
    "objects": """
    (object) @object
    """,
    
    "arrays": """
    (array) @array
    """,
    
    "string_values": """
    (pair
      key: (string (string_content) @key.name)
      value: (string (string_content) @string.value)
    ) @string.pair
    """,
    
    "number_values": """
    (pair
      key: (string (string_content) @key.name)
      value: (number) @number.value
    ) @number.pair
    """,
    
    "boolean_values": """
    (pair
      key: (string (string_content) @key.name)
      value: [(true) (false)] @boolean.value
    ) @boolean.pair
    """,
    
    "null_values": """
    (pair
      key: (string (string_content) @key.name)
      value: (null) @null.value
    ) @null.pair
    """,
    
    "nested_objects": """
    (pair
      key: (string (string_content) @key.name)
      value: (object) @object.value
    ) @nested.object
    """,
    
    "nested_arrays": """
    (pair
      key: (string (string_content) @key.name)
      value: (array) @array.value
    ) @nested.array
    """,
    
    "array_elements": """
    (array
      (string (string_content) @string.element)?
      (number) @number.element?
      [(true) (false)] @boolean.element?
      (null) @null.element?
      (object) @object.element?
      (array) @array.element?
    ) @array.container
    """,
    
    # Special patterns for common JSON structures
    "package_json_scripts": """
    (object
      (pair
        key: (string (string_content) @scripts.key)
        value: (object
          (pair
            key: (string (string_content) @script.name)
            value: (string (string_content) @script.command)
          )*
        ) @scripts.object
      )
      (#eq? @scripts.key "scripts")
    ) @package.scripts
    """,
    
    "package_json_dependencies": """
    (object
      (pair
        key: (string (string_content) @deps.key)
        value: (object
          (pair
            key: (string (string_content) @dep.name)
            value: (string (string_content) @dep.version)
          )*
        ) @deps.object
      )
      (#match? @deps.key "(dev)?[Dd]ependencies")
    ) @package.dependencies
    """,
    
    "tsconfig_compiler_options": """
    (object
      (pair
        key: (string (string_content) @compiler.key)
        value: (object
          (pair
            key: (string (string_content) @option.name)
            value: (_) @option.value
          )*
        ) @compiler.object
      )
      (#eq? @compiler.key "compilerOptions")
    ) @tsconfig.compiler_options
    """,
    
    # Deep nesting patterns
    "deep_nested_keys": """
    (object
      (pair
        key: (string (string_content) @level1.key)
        value: (object
          (pair
            key: (string (string_content) @level2.key)
            value: (object
              (pair
                key: (string (string_content) @level3.key)
                value: (_) @level3.value
              )*
            ) @level2.object
          )*
        ) @level1.object
      )*
    ) @nested.structure
    """
}

# Node type mappings for different JSON constructs
JSON_NODE_TYPES = {
    "object": ["object"],
    "array": ["array"],
    "property": ["pair"],
    "string": ["string", "string_content"],
    "number": ["number"],
    "boolean": ["true", "false"],
    "null": ["null"]
}

# Schema-specific query patterns
SCHEMA_QUERIES = {
    "npm_package": {
        "name": """
        (object
          (pair
            key: (string (string_content) @name.key)
            value: (string (string_content) @name.value)
          )
          (#eq? @name.key "name")
        ) @package.name
        """,
        
        "version": """
        (object
          (pair
            key: (string (string_content) @version.key)
            value: (string (string_content) @version.value)
          )
          (#eq? @version.key "version")
        ) @package.version
        """,
        
        "scripts": JSON_QUERIES["package_json_scripts"],
        "dependencies": JSON_QUERIES["package_json_dependencies"]
    },
    
    "typescript_config": {
        "compiler_options": JSON_QUERIES["tsconfig_compiler_options"],
        
        "include_exclude": """
        (object
          (pair
            key: (string (string_content) @include_exclude.key)
            value: (array
              (string (string_content) @path)*
            ) @paths.array
          )
          (#match? @include_exclude.key "(include|exclude)")
        ) @tsconfig.paths
        """
    },
    
    "eslint_config": {
        "rules": """
        (object
          (pair
            key: (string (string_content) @rules.key)
            value: (object
              (pair
                key: (string (string_content) @rule.name)
                value: (_) @rule.config
              )*
            ) @rules.object
          )
          (#eq? @rules.key "rules")
        ) @eslint.rules
        """
    }
}

def get_query_for_schema(schema_type: str) -> dict:
    """Get Tree-sitter queries specific to a schema type."""
    return SCHEMA_QUERIES.get(schema_type, {})

def get_all_json_queries() -> dict:
    """Get all available JSON Tree-sitter queries."""
    return JSON_QUERIES

def get_node_types_for_symbol_type(symbol_type: str) -> list:
    """Get Tree-sitter node types for a given symbol type."""
    return JSON_NODE_TYPES.get(symbol_type, [])