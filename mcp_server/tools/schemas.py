"""
Tool schema definitions.

Defines JSON schemas for all MCP tools.
"""

# Enhanced schema with backward compatibility
SEARCH_CODE_SCHEMA = {
    "type": "object",
    "description": "Search for code patterns across the codebase with enhanced structured request support",
    "properties": {
        # Structured request format
        "request_type": {
            "type": "string",
            "enum": ["symbol_search", "pattern_search", "edit_preparation", "explain_code", "goto_definition", "find_references"],
            "description": "Type of request for optimized results"
        },
        "target": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "symbol": {"type": "string", "description": "Exact symbol name"},
                "file_path": {"type": "string", "description": "Specific file path"}
            },
            "description": "Search target specification"
        },
        "context_spec": {
            "type": "object",
            "properties": {
                "depth": {"enum": ["minimal", "standard", "comprehensive", "edit_ready"], "description": "Context depth"},
                "include_related": {"type": "array", "items": {"type": "string"}, "description": "Related info to include"}
            },
            "description": "Context specification for results"
        },
        # Legacy properties for backward compatibility
        "query": {
            "type": "string",
            "description": "Search query (legacy format - use target.query in structured requests)"
        },
        "file_pattern": {
            "type": "string",
            "description": "File glob pattern to limit search (e.g., '*.py')",
            "default": "*"
        },
        "search_type": {
            "type": "string",
            "enum": ["regex", "literal", "semantic", "fuzzy"],
            "description": "Type of search to perform",
            "default": "literal"
        },
        "case_sensitive": {
            "type": "boolean",
            "description": "Whether search should be case-sensitive",
            "default": False
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return",
            "default": 100,
            "minimum": 1,
            "maximum": 1000
        },
        "context_lines": {
            "type": "integer",
            "description": "Number of context lines to include",
            "default": 2,
            "minimum": 0,
            "maximum": 10
        }
    },
    # Either structured (request_type + target) or legacy (query) format
    "anyOf": [
        {"required": ["request_type", "target"]},
        {"required": ["query"]}
    ]
}

# Schema for lookup_symbol tool
LOOKUP_SYMBOL_SCHEMA = {
    "type": "object",
    "description": "Look up a symbol definition in the codebase",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Symbol name to look up"
        },
        "symbol_type": {
            "type": "string",
            "enum": ["function", "class", "variable", "method", "any"],
            "description": "Type of symbol to search for",
            "default": "any"
        },
        "file_pattern": {
            "type": "string",
            "description": "File glob pattern to limit search",
            "default": "*"
        },
        "exact_match": {
            "type": "boolean",
            "description": "Require exact symbol name match",
            "default": True
        }
    },
    "required": ["symbol"]
}

# Schema for find_references tool
FIND_REFERENCES_SCHEMA = {
    "type": "object",
    "description": "Find all references to a symbol",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Symbol name to find references for"
        },
        "file_path": {
            "type": "string",
            "description": "File containing the symbol definition (optional)"
        },
        "line_number": {
            "type": "integer",
            "description": "Line number of symbol definition (optional)",
            "minimum": 1
        },
        "include_definitions": {
            "type": "boolean",
            "description": "Include symbol definitions in results",
            "default": False
        },
        "file_pattern": {
            "type": "string",
            "description": "File glob pattern to limit search",
            "default": "*"
        }
    },
    "required": ["symbol"]
}

# Schema for index_file tool
INDEX_FILE_SCHEMA = {
    "type": "object",
    "description": "Index a specific file or directory with repository metadata support",
    "properties": {
        "path": {
            "type": "string",
            "description": "File or directory path to index"
        },
        "recursive": {
            "type": "boolean",
            "description": "Recursively index directories",
            "default": True
        },
        "force": {
            "type": "boolean",
            "description": "Force re-indexing even if file is up-to-date",
            "default": False
        },
        "file_pattern": {
            "type": "string",
            "description": "File pattern to match when indexing directories",
            "default": "*"
        },
        "exclude_patterns": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Patterns to exclude from indexing",
            "default": [".git", "node_modules", "__pycache__", "*.pyc"]
        },
        "repository_metadata": {
            "type": "object",
            "description": "Repository metadata for external/reference codebases",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["local", "reference", "temporary", "external"],
                    "default": "local",
                    "description": "Repository type"
                },
                "language": {
                    "type": "string", 
                    "description": "Primary programming language"
                },
                "purpose": {
                    "type": "string",
                    "description": "Purpose (reference, translation, comparison, etc.)"
                },
                "temporary": {
                    "type": "boolean",
                    "default": False,
                    "description": "Mark as temporary for later cleanup"
                },
                "days_to_keep": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 365,
                    "description": "Days to keep if temporary"
                },
                "project": {
                    "type": "string",
                    "description": "Associated project name"
                },
                "description": {
                    "type": "string",
                    "description": "Repository description"
                }
            }
        }
    },
    "required": ["path"]
}

# Schema for get_file_outline tool
GET_FILE_OUTLINE_SCHEMA = {
    "type": "object",
    "description": "Get the structural outline of a file",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Path to the file"
        },
        "include_private": {
            "type": "boolean",
            "description": "Include private symbols in outline",
            "default": False
        },
        "max_depth": {
            "type": "integer",
            "description": "Maximum nesting depth to include",
            "default": -1,
            "minimum": -1
        }
    },
    "required": ["file_path"]
}

# Schema for analyze_dependencies tool
ANALYZE_DEPENDENCIES_SCHEMA = {
    "type": "object",
    "description": "Analyze dependencies of a file or module",
    "properties": {
        "path": {
            "type": "string",
            "description": "File or module path to analyze"
        },
        "depth": {
            "type": "integer",
            "description": "Maximum dependency depth to analyze",
            "default": 1,
            "minimum": 1,
            "maximum": 5
        },
        "include_external": {
            "type": "boolean",
            "description": "Include external dependencies",
            "default": True
        },
        "format": {
            "type": "string",
            "enum": ["tree", "list", "graph"],
            "description": "Output format for dependencies",
            "default": "tree"
        }
    },
    "required": ["path"]
}

# Registry of all tool schemas
TOOL_SCHEMAS = {
    "search_code": SEARCH_CODE_SCHEMA,
    "lookup_symbol": LOOKUP_SYMBOL_SCHEMA,
    "find_references": FIND_REFERENCES_SCHEMA,
    "index_file": INDEX_FILE_SCHEMA,
    "get_file_outline": GET_FILE_OUTLINE_SCHEMA,
    "analyze_dependencies": ANALYZE_DEPENDENCIES_SCHEMA
}


def get_tool_schema(tool_name: str) -> dict:
    """
    Get schema for a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool schema dictionary
        
    Raises:
        KeyError: If tool schema not found
    """
    if tool_name not in TOOL_SCHEMAS:
        raise KeyError(f"No schema found for tool: {tool_name}")
    return TOOL_SCHEMAS[tool_name]


def list_available_tools() -> list:
    """Get list of all available tool names."""
    return list(TOOL_SCHEMAS.keys())


def validate_tool_name(tool_name: str) -> bool:
    """Check if a tool name is valid."""
    return tool_name in TOOL_SCHEMAS
