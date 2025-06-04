"""
MCP Tools package.

Provides tool registry and handlers for MCP operations.
"""

from .registry import (
    ToolRegistry,
    ToolCapability,
    ToolMetadata,
    RegisteredTool,
    get_registry,
    reset_registry
)

from .validators import (
    validate_tool_params,
    validate_schema_structure,
    get_required_params,
    get_param_type,
    coerce_param_types
)

from .schemas import (
    SEARCH_CODE_SCHEMA,
    LOOKUP_SYMBOL_SCHEMA,
    FIND_REFERENCES_SCHEMA,
    INDEX_FILE_SCHEMA,
    GET_FILE_OUTLINE_SCHEMA,
    ANALYZE_DEPENDENCIES_SCHEMA,
    TOOL_SCHEMAS,
    get_tool_schema,
    list_available_tools,
    validate_tool_name
)

__all__ = [
    # Registry
    "ToolRegistry",
    "ToolCapability",
    "ToolMetadata",
    "RegisteredTool",
    "get_registry",
    "reset_registry",
    
    # Validators
    "validate_tool_params",
    "validate_schema_structure",
    "get_required_params",
    "get_param_type",
    "coerce_param_types",
    
    # Schemas
    "SEARCH_CODE_SCHEMA",
    "LOOKUP_SYMBOL_SCHEMA",
    "FIND_REFERENCES_SCHEMA",
    "INDEX_FILE_SCHEMA",
    "GET_FILE_OUTLINE_SCHEMA",
    "ANALYZE_DEPENDENCIES_SCHEMA",
    "TOOL_SCHEMAS",
    "get_tool_schema",
    "list_available_tools",
    "validate_tool_name"
]
