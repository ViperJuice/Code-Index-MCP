"""Base classes for MCP resources"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
import mimetypes
from pathlib import Path

@dataclass
class MCPResource:
    """MCP resource definition"""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP protocol"""
        result = {
            "uri": self.uri,
            "name": self.name
        }
        if self.description:
            result["description"] = self.description
        if self.mimeType:
            result["mimeType"] = self.mimeType
        if self.metadata:
            result["metadata"] = self.metadata
        return result

@dataclass
class MCPResourceContent:
    """Content of an MCP resource"""
    uri: str
    mimeType: str
    text: Optional[str] = None
    blob: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP protocol"""
        result = {
            "uri": self.uri,
            "mimeType": self.mimeType
        }
        
        # Include either text or blob (base64 encoded)
        if self.text is not None:
            result["text"] = self.text
        elif self.blob is not None:
            import base64
            result["blob"] = base64.b64encode(self.blob).decode('utf-8')
        
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result

class ResourceType:
    """Constants for resource types"""
    FILE = "file"
    SYMBOL = "symbol"
    SEARCH = "search"
    INDEX = "index"
    OUTLINE = "outline"
    DEPENDENCIES = "dependencies"

def create_file_resource(path: str, base_path: Optional[str] = None) -> MCPResource:
    """
    Create a file resource
    
    Args:
        path: File path
        base_path: Optional base path for relative display
        
    Returns:
        MCPResource for the file
    """
    path_obj = Path(path)
    relative_path = path_obj.relative_to(base_path) if base_path else path_obj
    
    mime_type = mimetypes.guess_type(str(path_obj))[0] or "text/plain"
    
    return MCPResource(
        uri=f"code://file/{path}",
        name=path_obj.name,
        description=f"Source file: {relative_path}",
        mimeType=mime_type,
        metadata={
            "path": str(path),
            "relative_path": str(relative_path),
            "exists": path_obj.exists()
        }
    )

def create_symbol_resource(
    name: str, 
    kind: str, 
    file_path: str, 
    line: int,
    language: Optional[str] = None
) -> MCPResource:
    """
    Create a symbol resource
    
    Args:
        name: Symbol name
        kind: Symbol kind (function, class, etc.)
        file_path: File containing the symbol
        line: Line number
        language: Optional language
        
    Returns:
        MCPResource for the symbol
    """
    return MCPResource(
        uri=f"code://symbol/{name}",
        name=name,
        description=f"{kind}: {name}",
        mimeType="application/json",
        metadata={
            "kind": kind,
            "file": file_path,
            "line": line,
            "language": language
        }
    )

def create_search_resource() -> MCPResource:
    """Create a search resource"""
    return MCPResource(
        uri="code://search",
        name="Code Search",
        description="Search through indexed code",
        mimeType="application/json",
        metadata={"type": "dynamic"}
    )

def create_index_resource() -> MCPResource:
    """Create an index status resource"""
    return MCPResource(
        uri="code://index",
        name="Index Status",
        description="Current indexing status and statistics",
        mimeType="application/json",
        metadata={"type": "dynamic"}
    )