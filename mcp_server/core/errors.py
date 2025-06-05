"""Custom exception classes for MCP Server."""

from typing import Optional, Any


class MCPError(Exception):
    """Base exception class for all MCP-related errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        """
        Initialize MCP error.
        
        Args:
            message: Error message
            details: Additional error details (optional)
        """
        super().__init__(message)
        self.message = message
        self.details = details
        
    def __str__(self) -> str:
        """String representation of the error."""
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class PluginError(MCPError):
    """Exception raised for plugin-related issues."""
    
    def __init__(self, plugin_name: str, message: str, details: Optional[Any] = None):
        """
        Initialize plugin error.
        
        Args:
            plugin_name: Name of the plugin that caused the error
            message: Error message
            details: Additional error details (optional)
        """
        self.plugin_name = plugin_name
        super().__init__(f"Plugin '{plugin_name}': {message}", details)


class IndexError(MCPError):
    """Exception raised for indexing problems."""
    
    def __init__(self, file_path: str, message: str, details: Optional[Any] = None):
        """
        Initialize index error.
        
        Args:
            file_path: Path to the file that caused the error
            message: Error message
            details: Additional error details (optional)
        """
        self.file_path = file_path
        super().__init__(f"Indexing error for '{file_path}': {message}", details)


class ConfigError(MCPError):
    """Exception raised for configuration issues."""
    
    def __init__(self, config_key: str, message: str, details: Optional[Any] = None):
        """
        Initialize configuration error.
        
        Args:
            config_key: Configuration key that caused the error
            message: Error message
            details: Additional error details (optional)
        """
        self.config_key = config_key
        super().__init__(f"Configuration error for '{config_key}': {message}", details)

class ValidationError(MCPError):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Any] = None):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field: Field that failed validation (optional)
            details: Additional error details (optional)
        """
        self.field = field
        if field:
            super().__init__(f"Validation error for field '{field}': {message}", details)
        else:
            super().__init__(f"Validation error: {message}", details)


class ToolError(MCPError):
    """Exception raised for tool-related errors."""
    
    def __init__(self, message: str, tool_name: Optional[str] = None, details: Optional[Any] = None):
        """
        Initialize tool error.
        
        Args:
            message: Error message
            tool_name: Name of the tool that caused the error (optional)
            details: Additional error details (optional)
        """
        self.tool_name = tool_name
        if tool_name:
            super().__init__(f"Tool '{tool_name}': {message}", details)
        else:
            super().__init__(f"Tool error: {message}", details)
