"""Base classes for MCP tools"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field, asdict
import logging
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class MCPTool:
    """MCP tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP protocol"""
        result = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result

@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP protocol"""
        if self.success:
            result = {"result": self.result}
            if self.metadata:
                result["metadata"] = self.metadata
            return result
        else:
            return {
                "error": {
                    "type": "tool_error",
                    "message": self.error or "Unknown error"
                }
            }

class ToolHandler(ABC):
    """Abstract base class for tool handlers"""
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given parameters
        
        Args:
            params: Tool parameters
            
        Returns:
            ToolResult with execution result or error
        """
        pass
    
    def validate_params(self, params: Dict[str, Any], schema: Dict[str, Any]) -> Optional[str]:
        """
        Validate parameters against schema
        
        Args:
            params: Parameters to validate
            schema: JSON schema for validation
            
        Returns:
            Error message if validation fails, None if valid
        """
        # Basic validation - can be enhanced with jsonschema library
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Check required parameters
        for req in required:
            if req not in params:
                return f"Missing required parameter: {req}"
        
        # Check parameter types
        for param_name, param_value in params.items():
            if param_name in properties:
                expected_type = properties[param_name].get("type")
                if expected_type:
                    if not self._check_type(param_value, expected_type):
                        return f"Invalid type for {param_name}: expected {expected_type}"
        
        return None
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type"""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected = type_map.get(expected_type)
        if expected:
            return isinstance(value, expected)
        return True

class AsyncToolHandler(ToolHandler):
    """Base class for async tool handlers with common functionality"""
    
    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    async def execute_with_timeout(
        self, 
        func: Callable[..., Awaitable[Any]], 
        timeout: float, 
        *args, 
        **kwargs
    ) -> Any:
        """
        Execute an async function with timeout
        
        Args:
            func: Async function to execute
            timeout: Timeout in seconds
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            asyncio.TimeoutError: If execution times out
        """
        return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
    
    def create_tracked_task(self, coro: Awaitable[Any], name: str) -> asyncio.Task:
        """
        Create a tracked async task
        
        Args:
            coro: Coroutine to run
            name: Name for the task
            
        Returns:
            Created task
        """
        task = asyncio.create_task(coro, name=name)
        self._running_tasks[name] = task
        
        def cleanup(t):
            self._running_tasks.pop(name, None)
        
        task.add_done_callback(cleanup)
        return task
    
    async def cancel_all_tasks(self):
        """Cancel all running tasks"""
        for task in list(self._running_tasks.values()):
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to complete
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        
        self._running_tasks.clear()