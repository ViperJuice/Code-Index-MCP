"""Custom exception classes for MCP Server."""

from typing import Any, Optional


def record_handled_error(module: str, exception: BaseException) -> None:
    """Increment mcp_errors_by_type_total{module, exception=type(exception).__name__}.

    Must never raise — metric surface failures are swallowed.
    """
    try:
        from mcp_server.metrics.prometheus_exporter import get_prometheus_exporter

        exporter = get_prometheus_exporter()
        if exporter.errors_by_type is not None:
            try:
                exporter.errors_by_type.labels(
                    module=module, exception=type(exception).__name__
                ).inc()
            except Exception:
                pass
    except Exception:
        pass


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


class DocumentProcessingError(MCPError):
    """Exception raised during document processing."""

    def __init__(self, document_path: str, message: str, details: Optional[Any] = None):
        """
        Initialize document processing error.

        Args:
            document_path: Path to the document that caused the error
            message: Error message
            details: Additional error details (optional)
        """
        self.document_path = document_path
        super().__init__(f"Document processing error for '{document_path}': {message}", details)


class IndexingError(MCPError):
    """Exception raised for general indexing pipeline failures (distinct from IndexError)."""

    pass


class ArtifactError(MCPError):
    """Exception raised for artifact upload/download/validation failures."""

    pass
