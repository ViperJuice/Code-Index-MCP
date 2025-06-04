"""
Request validation for MCP protocol.

Provides comprehensive validation for all MCP methods including:
- JSON Schema validation for parameters
- Type validation and coercion
- Capability checking
- Custom MCP-specific constraints
- Integration with error handling
"""

import json
import re
from typing import Dict, Any, Optional, List, Union, Set, Callable
from dataclasses import dataclass
from enum import Enum
import jsonschema
from jsonschema import Draft7Validator, ValidationError

from .methods import MCPMethod
from .errors import (
    MCPError,
    MCPErrorCode,
    MCPException,
    create_invalid_params_error,
    CapabilityNotSupportedException,
    SessionNotInitializedException
)
from ..interfaces.mcp_interfaces import MCPRequest
from ..core.logging import get_logger

logger = get_logger(__name__)


class ValidationType(str, Enum):
    """Types of validation to perform."""
    SCHEMA = "schema"
    CAPABILITY = "capability"
    CONSTRAINT = "constraint"
    TYPE_COERCION = "type_coercion"


@dataclass
class ValidationRule:
    """Container for validation rules."""
    
    validation_type: ValidationType
    rule: Union[Dict[str, Any], Callable[[Any], bool]]
    error_message: Optional[str] = None
    coerce_func: Optional[Callable[[Any], Any]] = None


class MCPValidator:
    """Main validator for MCP protocol requests."""
    
    # MCP protocol versions
    SUPPORTED_PROTOCOL_VERSIONS = {"1.0", "1.1"}
    
    # Method parameter schemas
    METHOD_SCHEMAS: Dict[str, Dict[str, Any]] = {
        MCPMethod.INITIALIZE: {
            "type": "object",
            "properties": {
                "protocolVersion": {
                    "type": "string",
                    "pattern": r"^\d+\.\d+$"
                },
                "capabilities": {
                    "type": "object",
                    "properties": {
                        "resources": {
                            "type": "object",
                            "properties": {
                                "subscribe": {"type": "boolean"},
                                "listSupported": {"type": "boolean"}
                            }
                        },
                        "tools": {
                            "type": "object",
                            "properties": {
                                "listSupported": {"type": "boolean"}
                            }
                        },
                        "prompts": {
                            "type": "object",
                            "properties": {
                                "listSupported": {"type": "boolean"}
                            }
                        },
                        "logging": {
                            "type": "object",
                            "properties": {
                                "setLevel": {"type": "boolean"}
                            }
                        },
                        "sampling": {
                            "type": "object",
                            "properties": {
                                "createMessage": {"type": "boolean"}
                            }
                        }
                    }
                },
                "clientInfo": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"}
                    },
                    "required": ["name", "version"]
                }
            },
            "required": ["protocolVersion", "capabilities"]
        },
        
        MCPMethod.RESOURCES_LIST: {
            "type": "object",
            "properties": {
                "cursor": {"type": "string"}
            }
        },
        
        MCPMethod.RESOURCES_READ: {
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "minLength": 1
                }
            },
            "required": ["uri"]
        },
        
        MCPMethod.RESOURCES_SUBSCRIBE: {
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "minLength": 1
                }
            },
            "required": ["uri"]
        },
        
        MCPMethod.RESOURCES_UNSUBSCRIBE: {
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "minLength": 1
                }
            },
            "required": ["uri"]
        },
        
        MCPMethod.TOOLS_LIST: {
            "type": "object",
            "properties": {
                "cursor": {"type": "string"}
            }
        },
        
        MCPMethod.TOOLS_CALL: {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1
                },
                "arguments": {
                    "type": "object"
                }
            },
            "required": ["name"]
        },
        
        MCPMethod.PROMPTS_LIST: {
            "type": "object",
            "properties": {
                "cursor": {"type": "string"}
            }
        },
        
        MCPMethod.PROMPTS_GET: {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1
                },
                "arguments": {
                    "type": "object"
                }
            },
            "required": ["name"]
        },
        
        MCPMethod.SAMPLING_CREATE_MESSAGE: {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["user", "assistant", "system"]
                            },
                            "content": {
                                "type": "string"
                            }
                        },
                        "required": ["role", "content"]
                    },
                    "minItems": 1
                },
                "modelPreferences": {
                    "type": "object",
                    "properties": {
                        "temperature": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 2
                        },
                        "maxTokens": {
                            "type": "integer",
                            "minimum": 1
                        },
                        "stopSequences": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "seed": {"type": "integer"}
                    }
                },
                "includeContext": {
                    "type": "string",
                    "enum": ["none", "thisServer", "allServers"]
                },
                "systemPrompt": {"type": "string"}
            },
            "required": ["messages"]
        },
        
        MCPMethod.LOGGING_SET_LEVEL: {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"]
                }
            },
            "required": ["level"]
        },
        
        # Methods with no parameters
        MCPMethod.SHUTDOWN: {"type": "null"},
        MCPMethod.PING: {"type": "null"}
    }
    
    def __init__(self, capabilities: Optional[Dict[str, Any]] = None):
        """
        Initialize the validator.
        
        Args:
            capabilities: Server capabilities for validation
        """
        self.capabilities = capabilities or {}
        self._validators: Dict[str, Draft7Validator] = {}
        self._custom_rules: Dict[str, List[ValidationRule]] = {}
        self._initialized = False
        
        # Pre-compile validators for better performance
        self._compile_validators()
        
        # Register custom validation rules
        self._register_custom_rules()
    
    def _compile_validators(self) -> None:
        """Pre-compile JSON Schema validators for all methods."""
        for method, schema in self.METHOD_SCHEMAS.items():
            if schema.get("type") != "null":
                self._validators[method.value] = Draft7Validator(schema)
    
    def _register_custom_rules(self) -> None:
        """Register custom validation rules for specific methods."""
        # Initialize protocol version validation
        self._custom_rules[MCPMethod.INITIALIZE.value] = [
            ValidationRule(
                validation_type=ValidationType.CONSTRAINT,
                rule=lambda params: params.get("protocolVersion") in self.SUPPORTED_PROTOCOL_VERSIONS,
                error_message=f"Unsupported protocol version. Supported versions: {', '.join(self.SUPPORTED_PROTOCOL_VERSIONS)}"
            )
        ]
        
        # Resource URI validation
        uri_pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')
        for method in [MCPMethod.RESOURCES_READ, MCPMethod.RESOURCES_SUBSCRIBE, MCPMethod.RESOURCES_UNSUBSCRIBE]:
            self._custom_rules.setdefault(method.value, []).append(
                ValidationRule(
                    validation_type=ValidationType.CONSTRAINT,
                    rule=lambda params: uri_pattern.match(params.get("uri", "")),
                    error_message="Invalid URI format. URI must start with a scheme (e.g., 'file:', 'http:')"
                )
            )
        
        # Tool name validation
        tool_name_pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
        self._custom_rules.setdefault(MCPMethod.TOOLS_CALL.value, []).append(
            ValidationRule(
                validation_type=ValidationType.CONSTRAINT,
                rule=lambda params: tool_name_pattern.match(params.get("name", "")),
                error_message="Invalid tool name. Must start with a letter and contain only alphanumeric characters, underscores, and hyphens"
            )
        )
        
        # Prompt name validation
        self._custom_rules.setdefault(MCPMethod.PROMPTS_GET.value, []).append(
            ValidationRule(
                validation_type=ValidationType.CONSTRAINT,
                rule=lambda params: tool_name_pattern.match(params.get("name", "")),
                error_message="Invalid prompt name. Must start with a letter and contain only alphanumeric characters, underscores, and hyphens"
            )
        )
    
    def validate_request(self, request: MCPRequest, session_initialized: bool = False) -> None:
        """
        Validate an MCP request.
        
        Args:
            request: The MCP request to validate
            session_initialized: Whether the session has been initialized
            
        Raises:
            MCPError: If validation fails
        """
        try:
            # Check if method requires initialization
            if not session_initialized and request.method not in [
                MCPMethod.INITIALIZE.value,
                MCPMethod.SHUTDOWN.value,
                MCPMethod.PING.value
            ]:
                raise SessionNotInitializedException(request.method)
            
            # Special handling for methods with no parameters
            if request.method in [MCPMethod.SHUTDOWN.value, MCPMethod.PING.value]:
                if request.params is not None:
                    raise create_invalid_params_error(
                        request.method,
                        "This method does not accept parameters"
                    )
                return
            
            # Validate parameters are provided for methods that require them
            if request.method not in [MCPMethod.SHUTDOWN.value, MCPMethod.PING.value] and request.params is None:
                raise create_invalid_params_error(
                    request.method,
                    "Parameters are required for this method"
                )
            
            # Schema validation
            self._validate_schema(request.method, request.params)
            
            # Custom validation rules
            self._validate_custom_rules(request.method, request.params)
            
            # Capability validation
            self._validate_capabilities(request.method)
            
            # Type coercion
            if request.params:
                request.params = self._coerce_types(request.method, request.params)
                
        except MCPException:
            raise
        except ValidationError as e:
            # Convert jsonschema validation errors to MCP errors
            path = " -> ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            raise create_invalid_params_error(
                request.method,
                f"Schema validation failed at {path}: {e.message}"
            )
        except Exception as e:
            logger.error(f"Unexpected validation error for {request.method}: {e}")
            raise MCPError(
                code=int(MCPErrorCode.MCP_INTERNAL_ERROR),
                message="Validation failed",
                data={"method": request.method, "error": str(e)}
            )
    
    def _validate_schema(self, method: str, params: Optional[Dict[str, Any]]) -> None:
        """Validate parameters against JSON schema."""
        validator = self._validators.get(method)
        if validator and params is not None:
            validator.validate(params)
    
    def _validate_custom_rules(self, method: str, params: Optional[Dict[str, Any]]) -> None:
        """Apply custom validation rules."""
        rules = self._custom_rules.get(method, [])
        for rule in rules:
            if rule.validation_type == ValidationType.CONSTRAINT:
                if not rule.rule(params):
                    raise create_invalid_params_error(
                        method,
                        rule.error_message or "Custom validation failed"
                    )
    
    def _validate_capabilities(self, method: str) -> None:
        """Validate that the server supports the requested capability."""
        capability_map = {
            MCPMethod.RESOURCES_SUBSCRIBE.value: ("resources", "subscribe"),
            MCPMethod.RESOURCES_UNSUBSCRIBE.value: ("resources", "subscribe"),
            MCPMethod.SAMPLING_CREATE_MESSAGE.value: ("sampling", "createMessage"),
            MCPMethod.LOGGING_SET_LEVEL.value: ("logging", "setLevel")
        }
        
        if method in capability_map:
            cap_path = capability_map[method]
            cap_dict = self.capabilities
            
            for i, key in enumerate(cap_path):
                if i == len(cap_path) - 1:
                    # Last key - check if it exists and is truthy
                    if key not in cap_dict or not cap_dict.get(key):
                        raise CapabilityNotSupportedException(f"{'.'.join(cap_path)}")
                    return
                else:
                    # Intermediate key - navigate deeper
                    cap_dict = cap_dict.get(key, {})
                    if not isinstance(cap_dict, dict):
                        raise CapabilityNotSupportedException(f"{'.'.join(cap_path)}")

    def _coerce_types(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coerce parameter types where safe to do so.
        
        Args:
            method: Method name
            params: Parameters to coerce
            
        Returns:
            Parameters with coerced types
        """
        # Define safe type coercions
        coercions = {
            MCPMethod.SAMPLING_CREATE_MESSAGE.value: {
                "modelPreferences.temperature": float,
                "modelPreferences.maxTokens": int,
                "modelPreferences.seed": int
            }
        }
        
        method_coercions = coercions.get(method, {})
        if not method_coercions:
            return params
        
        # Apply coercions
        result = params.copy()
        for path, coerce_func in method_coercions.items():
            keys = path.split(".")
            target = result
            
            # Navigate to the target value
            for key in keys[:-1]:
                if key in target and isinstance(target[key], dict):
                    target = target[key]
                else:
                    break
            else:
                # Apply coercion to the final key
                final_key = keys[-1]
                if final_key in target:
                    try:
                        target[final_key] = coerce_func(target[final_key])
                    except (ValueError, TypeError):
                        # If coercion fails, let schema validation handle it
                        pass
        
        return result
    
    def validate_capability_request(self, capability: str) -> bool:
        """
        Check if a capability is supported.
        
        Args:
            capability: Dot-separated capability path (e.g., "resources.subscribe")
            
        Returns:
            True if capability is supported
        """
        keys = capability.split(".")
        cap_dict = self.capabilities
        
        for key in keys:
            if not isinstance(cap_dict, dict) or key not in cap_dict:
                return False
            cap_dict = cap_dict[key]
        
        return bool(cap_dict)
    
    def get_method_schema(self, method: str) -> Optional[Dict[str, Any]]:
        """
        Get the JSON schema for a method.
        
        Args:
            method: Method name
            
        Returns:
            JSON schema or None if not found
        """
        # Convert string to MCPMethod if possible
        for mcp_method in MCPMethod:
            if mcp_method.value == method:
                return self.METHOD_SCHEMAS.get(mcp_method)
        return None
    
    def update_capabilities(self, capabilities: Dict[str, Any]) -> None:
        """
        Update server capabilities.
        
        Args:
            capabilities: New capability dictionary
        """
        self.capabilities = capabilities
        self._initialized = True


class ResourceURIValidator:
    """Specialized validator for resource URIs."""
    
    # Common URI schemes
    STANDARD_SCHEMES = {
        "file", "http", "https", "ftp", "sftp",
        "git", "ssh", "ws", "wss", "data"
    }
    
    # MCP-specific schemes
    MCP_SCHEMES = {
        "mcp", "resource", "index", "code",
        "symbol", "ast", "graph", "cache"
    }
    
    @classmethod
    def validate_uri(cls, uri: str, allowed_schemes: Optional[Set[str]] = None) -> bool:
        """
        Validate a resource URI.
        
        Args:
            uri: URI to validate
            allowed_schemes: Set of allowed schemes (None = all)
            
        Returns:
            True if valid
        """
        # Basic URI pattern
        match = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*):(.+)$', uri)
        if not match:
            return False
        
        scheme = match.group(1).lower()
        
        # Check allowed schemes
        if allowed_schemes is not None:
            return scheme in allowed_schemes
        
        # Allow standard and MCP schemes by default
        return scheme in cls.STANDARD_SCHEMES or scheme in cls.MCP_SCHEMES
    
    @classmethod
    def parse_uri(cls, uri: str) -> Dict[str, str]:
        """
        Parse a URI into components.
        
        Args:
            uri: URI to parse
            
        Returns:
            Dictionary with scheme, path, and other components
        """
        match = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*):(.+)$', uri)
        if not match:
            raise ValueError(f"Invalid URI format: {uri}")
        
        return {
            "scheme": match.group(1).lower(),
            "path": match.group(2),
            "full": uri
        }


class ToolArgumentValidator:
    """Specialized validator for tool arguments."""
    
    @staticmethod
    def validate_against_schema(
        arguments: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> None:
        """
        Validate tool arguments against a JSON schema.
        
        Args:
            arguments: Tool arguments to validate
            schema: JSON schema for the tool
            
        Raises:
            ValidationError: If validation fails
        """
        validator = Draft7Validator(schema)
        validator.validate(arguments)
    
    @staticmethod
    def coerce_tool_arguments(
        arguments: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Coerce tool arguments based on schema.
        
        Args:
            arguments: Arguments to coerce
            schema: Tool schema
            
        Returns:
            Coerced arguments
        """
        # Simple type coercion based on schema
        if "properties" not in schema:
            return arguments
        
        result = arguments.copy()
        properties = schema.get("properties", {})
        
        for key, prop_schema in properties.items():
            if key in result:
                value = result[key]
                prop_type = prop_schema.get("type")
                
                # Coerce basic types
                if prop_type == "string" and not isinstance(value, str):
                    result[key] = str(value)
                elif prop_type == "number" and isinstance(value, (int, str)):
                    try:
                        result[key] = float(value)
                    except ValueError:
                        pass
                elif prop_type == "integer" and isinstance(value, (float, str)):
                    try:
                        result[key] = int(value)
                    except ValueError:
                        pass
                elif prop_type == "boolean" and isinstance(value, str):
                    result[key] = value.lower() in ("true", "1", "yes", "on")
        
        return result


# Create a default validator instance
default_validator = MCPValidator()


# Convenience functions

def validate_mcp_request(
    request: MCPRequest,
    capabilities: Optional[Dict[str, Any]] = None,
    session_initialized: bool = False
) -> None:
    """
    Validate an MCP request.
    
    Args:
        request: Request to validate
        capabilities: Server capabilities
        session_initialized: Whether session is initialized
        
    Raises:
        MCPError: If validation fails
    """
    validator = MCPValidator(capabilities) if capabilities else default_validator
    validator.validate_request(request, session_initialized)


def validate_resource_uri(uri: str, allowed_schemes: Optional[Set[str]] = None) -> bool:
    """
    Validate a resource URI.
    
    Args:
        uri: URI to validate
        allowed_schemes: Allowed URI schemes
        
    Returns:
        True if valid
    """
    return ResourceURIValidator.validate_uri(uri, allowed_schemes)


def validate_tool_arguments(
    arguments: Dict[str, Any],
    schema: Dict[str, Any],
    coerce: bool = True
) -> Dict[str, Any]:
    """
    Validate and optionally coerce tool arguments.
    
    Args:
        arguments: Arguments to validate
        schema: Tool schema
        coerce: Whether to coerce types
        
    Returns:
        Validated (and possibly coerced) arguments
        
    Raises:
        ValidationError: If validation fails
    """
    if coerce:
        arguments = ToolArgumentValidator.coerce_tool_arguments(arguments, schema)
    
    ToolArgumentValidator.validate_against_schema(arguments, schema)
    return arguments
