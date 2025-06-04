"""
Integration module for tool registry and dispatcher.

Provides utilities to connect the tool registry with the existing dispatcher.
"""

from typing import Optional
from ..dispatcher.dispatcher import Dispatcher
from .registry import ToolRegistry, get_registry


def create_integrated_registry(dispatcher: Dispatcher) -> ToolRegistry:
    """
    Create a tool registry integrated with the dispatcher.
    
    Args:
        dispatcher: The dispatcher instance to integrate
        
    Returns:
        Configured ToolRegistry instance
    """
    registry = get_registry(dispatcher)
    
    # Auto-discover and register tools
    # (This happens automatically in __init__)
    
    return registry


def register_code_tools(registry: ToolRegistry) -> None:
    """
    Register all code-related tools with the registry.
    
    Args:
        registry: The registry to register tools with
    """
    # Import handlers
    from .handlers import search_code, lookup_symbol, find_references, index_file
    
    # Register each tool
    # (Each handler module should have a register_tool function)
    for module in [search_code, lookup_symbol, find_references, index_file]:
        if hasattr(module, "register_tool"):
            module.register_tool(registry)


async def execute_tool_with_dispatcher(
    tool_name: str,
    params: dict,
    dispatcher: Dispatcher
) -> dict:
    """
    Execute a tool with a specific dispatcher instance.
    
    Args:
        tool_name: Name of the tool to execute
        params: Tool parameters
        dispatcher: Dispatcher instance
        
    Returns:
        Tool execution result
    """
    registry = get_registry(dispatcher)
    
    # Execute with dispatcher in context
    context = {"dispatcher": dispatcher}
    result = await registry.execute(tool_name, params, context)
    
    return result


# Example usage patterns
__all__ = [
    "create_integrated_registry",
    "register_code_tools",
    "execute_tool_with_dispatcher"
]
