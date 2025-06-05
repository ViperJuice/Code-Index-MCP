"""
MCP-specific interface definitions.

Defines interfaces for MCP protocol components.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass

@dataclass
class MCPRequest:
    """Base MCP request structure."""
    method: str
    params: Optional[Dict[str, Any]] = None
    
@dataclass
class MCPResponse:
    """Base MCP response structure."""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class IMCPHandler(ABC):
    """Interface for MCP method handlers."""
    
    @abstractmethod
    async def handle(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request and return a response."""
        pass

class IMCPResource(ABC):
    """Interface for MCP resources."""
    
    @abstractmethod
    def get_uri(self) -> str:
        """Get the resource URI."""
        pass
        
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Get resource metadata."""
        pass

class IMCPTool(ABC):
    """Interface for MCP tools."""
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's JSON schema."""
        pass
        
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Any:
        """Execute the tool with given parameters."""
        pass

# TODO: Add more specific interfaces as needed
# TODO: Add interface documentation
# TODO: Add type hints for all methods
