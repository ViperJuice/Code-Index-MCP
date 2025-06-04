"""
Tool input validation.

Validates tool inputs against JSON schemas.
"""

import json
from typing import Dict, Any, List, Optional, Union
from jsonschema import validate, ValidationError as JSONSchemaError, Draft7Validator
from jsonschema.exceptions import SchemaError

from ..core.errors import ValidationError


def validate_tool_params(params: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate tool parameters against a JSON schema.
    
    Args:
        params: Parameters to validate
        schema: JSON schema to validate against
        
    Returns:
        Validated parameters (with defaults applied)
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Create validator instance
        validator = Draft7Validator(schema)
        
        # Check if schema is valid
        Draft7Validator.check_schema(schema)
        
        # Validate the parameters
        errors = list(validator.iter_errors(params))
        if errors:
            # Format error messages
            error_messages = []
            for error in errors:
                path = ".".join(str(p) for p in error.path)
                if path:
                    error_messages.append(f"{path}: {error.message}")
                else:
                    error_messages.append(error.message)
            
            error_msg = '\n'.join(error_messages)
            raise ValidationError(
                f"Parameter validation failed: {error_msg}",
                details={"errors": error_messages}
            )
        
        # Apply defaults from schema
        validated_params = apply_schema_defaults(params, schema)
        
        return validated_params
        
    except SchemaError as e:
        raise ValidationError(f"Invalid schema: {str(e)}")
    except JSONSchemaError as e:
        raise ValidationError(f"Validation error: {str(e)}")
    except Exception as e:
        raise ValidationError(f"Unexpected validation error: {str(e)}")


def apply_schema_defaults(params: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply default values from schema to parameters.
    
    Args:
        params: Input parameters
        schema: JSON schema with defaults
        
    Returns:
        Parameters with defaults applied
    """
    result = params.copy()
    
    # Get properties from schema
    properties = schema.get("properties", {})
    
    # Apply defaults for missing properties
    for prop_name, prop_schema in properties.items():
        if prop_name not in result and "default" in prop_schema:
            result[prop_name] = prop_schema["default"]
            
    return result


def validate_schema_structure(schema: Dict[str, Any]) -> None:
    """
    Validate that a schema has the required structure for a tool.
    
    Args:
        schema: Schema to validate
        
    Raises:
        ValidationError: If schema structure is invalid
    """
    if not isinstance(schema, dict):
        raise ValidationError("Schema must be a dictionary")
        
    if "type" not in schema:
        raise ValidationError("Schema must have a 'type' field")
        
    if schema["type"] != "object":
        raise ValidationError("Tool schema type must be 'object'")
        
    if "properties" not in schema:
        raise ValidationError("Schema must have a 'properties' field")
        
    if not isinstance(schema["properties"], dict):
        raise ValidationError("Schema 'properties' must be a dictionary")


def get_required_params(schema: Dict[str, Any]) -> List[str]:
    """
    Get list of required parameters from schema.
    
    Args:
        schema: JSON schema
        
    Returns:
        List of required parameter names
    """
    return schema.get("required", [])


def get_param_type(schema: Dict[str, Any], param_name: str) -> Optional[str]:
    """
    Get the type of a parameter from schema.
    
    Args:
        schema: JSON schema
        param_name: Parameter name
        
    Returns:
        Parameter type or None if not found
    """
    properties = schema.get("properties", {})
    param_schema = properties.get(param_name, {})
    return param_schema.get("type")


def validate_param_value(
    value: Any,
    param_schema: Dict[str, Any],
    param_name: str
) -> None:
    """
    Validate a single parameter value against its schema.
    
    Args:
        value: Value to validate
        param_schema: Schema for this parameter
        param_name: Parameter name (for error messages)
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        validate(value, param_schema)
    except JSONSchemaError as e:
        raise ValidationError(
            f"Invalid value for parameter '{param_name}': {str(e)}",
            field=param_name
        )


def coerce_param_types(
    params: Dict[str, Any],
    schema: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Attempt to coerce parameter types to match schema.
    
    Args:
        params: Input parameters
        schema: JSON schema
        
    Returns:
        Parameters with coerced types
    """
    result = params.copy()
    properties = schema.get("properties", {})
    
    for param_name, value in result.items():
        if param_name in properties:
            param_schema = properties[param_name]
            expected_type = param_schema.get("type")
            
            # Try to coerce common type mismatches
            if expected_type == "string" and not isinstance(value, str):
                result[param_name] = str(value)
            elif expected_type == "number" and isinstance(value, str):
                try:
                    result[param_name] = float(value)
                except ValueError:
                    pass  # Keep original value, will fail validation
            elif expected_type == "integer" and isinstance(value, str):
                try:
                    result[param_name] = int(value)
                except ValueError:
                    pass  # Keep original value, will fail validation
            elif expected_type == "boolean" and isinstance(value, str):
                if value.lower() in ("true", "1", "yes", "on"):
                    result[param_name] = True
                elif value.lower() in ("false", "0", "no", "off"):
                    result[param_name] = False
                    
    return result


# Schema validation cache to avoid repeated validation
_schema_cache: Dict[str, bool] = {}


def is_valid_schema(schema: Dict[str, Any]) -> bool:
    """
    Check if a schema is valid (with caching).
    
    Args:
        schema: Schema to check
        
    Returns:
        True if valid, False otherwise
    """
    # Create cache key from schema
    cache_key = json.dumps(schema, sort_keys=True)
    
    if cache_key in _schema_cache:
        return _schema_cache[cache_key]
        
    try:
        Draft7Validator.check_schema(schema)
        _schema_cache[cache_key] = True
        return True
    except SchemaError:
        _schema_cache[cache_key] = False
        return False
