"""
Tool registry for MCP.

Manages available tools and their schemas.
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
import json
import importlib
import inspect
from pathlib import Path

from ..core.errors import ValidationError, ToolError
from ..dispatcher.dispatcher import Dispatcher
from .validators import validate_tool_params

logger = logging.getLogger(__name__)


class ToolCapability(Enum):
    """Tool capabilities for categorization."""
    SEARCH = "search"
    INDEX = "index"
    LOOKUP = "lookup"
    ANALYZE = "analyze"
    MODIFY = "modify"


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: List[ToolCapability] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    author: str = ""
    
    
@dataclass
class RegisteredTool:
    """Represents a registered tool with all its information."""
    name: str
    handler: Callable
    schema: Dict[str, Any]
    metadata: ToolMetadata
    enabled: bool = True
    
    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters against the tool's schema."""
        return validate_tool_params(params, self.schema)


class ToolRegistry:
    """
    Central registry for MCP tools.
    
    Manages tool registration, discovery, validation, and execution dispatch.
    """
    
    def __init__(self, dispatcher: Optional[Dispatcher] = None):
        """
        Initialize the tool registry.
        
        Args:
            dispatcher: Optional dispatcher for code operations integration
        """
        self._tools: Dict[str, RegisteredTool] = {}
        self._dispatcher = dispatcher
        self._tool_schemas: Dict[str, Dict[str, Any]] = {}
        self._execution_stats: Dict[str, Dict[str, int]] = {}
        
        # Auto-discover tools on initialization
        self._auto_discover_tools()
        
    def register(
        self,
        name: str,
        handler: Callable,
        schema: Dict[str, Any],
        metadata: Optional[ToolMetadata] = None
    ) -> None:
        """
        Register a new tool.
        
        Args:
            name: Unique tool name
            handler: Tool execution handler function
            schema: JSON Schema for tool parameters
            metadata: Optional tool metadata
            
        Raises:
            ValueError: If tool with same name already exists
            ValidationError: If schema is invalid
        """
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")
            
        # Validate schema structure
        self._validate_schema(schema)
        
        # Create metadata if not provided
        if metadata is None:
            metadata = ToolMetadata(
                name=name,
                description=schema.get("description", ""),
            )
            
        # Register the tool
        tool = RegisteredTool(
            name=name,
            handler=handler,
            schema=schema,
            metadata=metadata
        )
        
        self._tools[name] = tool
        self._tool_schemas[name] = schema
        self._execution_stats[name] = {"calls": 0, "errors": 0}
        
        logger.info(f"Registered tool: {name}")
        
    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.
        
        Args:
            name: Tool name to unregister
            
        Returns:
            True if tool was unregistered, False if not found
        """
        if name not in self._tools:
            return False
            
        del self._tools[name]
        del self._tool_schemas[name]
        del self._execution_stats[name]
        
        logger.info(f"Unregistered tool: {name}")
        return True
        
    def get_tool(self, name: str) -> Optional[RegisteredTool]:
        """Get a registered tool by name."""
        return self._tools.get(name)
        
    def list_tools(self, enabled_only: bool = True) -> List[str]:
        """
        List all registered tools.
        
        Args:
            enabled_only: Only return enabled tools
            
        Returns:
            List of tool names
        """
        if enabled_only:
            return [name for name, tool in self._tools.items() if tool.enabled]
        return list(self._tools.keys())
        
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a tool.
        
        Args:
            name: Tool name
            
        Returns:
            Tool information dictionary or None if not found
        """
        tool = self._tools.get(name)
        if not tool:
            return None
            
        return {
            "name": tool.name,
            "description": tool.metadata.description,
            "version": tool.metadata.version,
            "schema": tool.schema,
            "capabilities": [cap.value for cap in tool.metadata.capabilities],
            "tags": tool.metadata.tags,
            "enabled": tool.enabled,
            "stats": self._execution_stats.get(name, {})
        }
        
    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the JSON schema for a tool."""
        return self._tool_schemas.get(name)
        
    def list_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Get all tool schemas."""
        return self._tool_schemas.copy()
        
    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a tool with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters
            context: Optional execution context
            
        Returns:
            Tool execution result
            
        Raises:
            ToolError: If tool not found or execution fails
            ValidationError: If parameters are invalid
        """
        tool = self._tools.get(tool_name)
        if not tool:
            raise ToolError(f"Tool '{tool_name}' not found")
            
        if not tool.enabled:
            raise ToolError(f"Tool '{tool_name}' is disabled")
            
        # Update stats
        self._execution_stats[tool_name]["calls"] += 1
        
        try:
            # Validate parameters
            validated_params = tool.validate_params(params)
            
            # Inject dispatcher if tool needs it
            if context is None:
                context = {}
                
            if self._dispatcher and "dispatcher" not in context:
                context["dispatcher"] = self._dispatcher
                
            # Execute tool
            result = await self._execute_tool(tool, validated_params, context)
            
            return result
            
        except Exception as e:
            self._execution_stats[tool_name]["errors"] += 1
            logger.error(f"Tool execution failed for '{tool_name}': {e}")
            raise ToolError(f"Tool execution failed: {e}") from e
            
    async def _execute_tool(
        self,
        tool: RegisteredTool,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """
        Internal tool execution with proper async handling.
        
        Args:
            tool: Tool to execute
            params: Validated parameters
            context: Execution context
            
        Returns:
            Tool result
        """
        handler = tool.handler
        
        # Check if handler is async
        if inspect.iscoroutinefunction(handler):
            return await handler(params, context)
        else:
            # Run sync handler in thread pool to avoid blocking
            import asyncio
            return await asyncio.get_event_loop().run_in_executor(
                None, handler, params, context
            )
            
    def enable_tool(self, name: str) -> bool:
        """Enable a tool."""
        tool = self._tools.get(name)
        if tool:
            tool.enabled = True
            return True
        return False
        
    def disable_tool(self, name: str) -> bool:
        """Disable a tool."""
        tool = self._tools.get(name)
        if tool:
            tool.enabled = False
            return True
        return False
        
    def get_tools_by_capability(
        self,
        capability: ToolCapability
    ) -> List[str]:
        """Get tools that have a specific capability."""
        return [
            name for name, tool in self._tools.items()
            if capability in tool.metadata.capabilities and tool.enabled
        ]
        
    def get_tools_by_tag(self, tag: str) -> List[str]:
        """Get tools that have a specific tag."""
        return [
            name for name, tool in self._tools.items()
            if tag in tool.metadata.tags and tool.enabled
        ]
        
    def _validate_schema(self, schema: Dict[str, Any]) -> None:
        """Validate a tool schema structure."""
        required_fields = ["type", "properties"]
        for field in required_fields:
            if field not in schema:
                raise ValidationError(f"Schema missing required field: {field}")
                
        if schema["type"] != "object":
            raise ValidationError("Schema type must be 'object'")
            
    def _auto_discover_tools(self) -> None:
        """Auto-discover and register tools from handlers directory."""
        handlers_dir = Path(__file__).parent / "handlers"
        if not handlers_dir.exists():
            return
            
        for handler_file in handlers_dir.glob("*.py"):
            if handler_file.name.startswith("_"):
                continue
                
            module_name = f"mcp_server.tools.handlers.{handler_file.stem}"
            
            try:
                module = importlib.import_module(module_name)
                
                # Look for register_tool function
                if hasattr(module, "register_tool"):
                    module.register_tool(self)
                    logger.info(f"Auto-discovered tool from {handler_file.name}")
                    
            except Exception as e:
                logger.warning(f"Failed to auto-discover tool from {handler_file.name}: {e}")
                
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_tools": len(self._tools),
            "enabled_tools": len([t for t in self._tools.values() if t.enabled]),
            "execution_stats": self._execution_stats.copy(),
            "tools_by_capability": {
                cap.value: len(self.get_tools_by_capability(cap))
                for cap in ToolCapability
            }
        }
        
    def reset_statistics(self) -> None:
        """Reset execution statistics."""
        for tool_name in self._execution_stats:
            self._execution_stats[tool_name] = {"calls": 0, "errors": 0}


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_registry(dispatcher: Optional[Dispatcher] = None) -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Args:
        dispatcher: Optional dispatcher for initialization
        
    Returns:
        The global ToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry(dispatcher)
    return _registry


def reset_registry() -> None:
    """Reset the global registry (mainly for testing)."""
    global _registry
    _registry = None
