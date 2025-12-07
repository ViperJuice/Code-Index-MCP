"""TypeScript type system support for advanced type inference and analysis."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tree_sitter import Node

logger = logging.getLogger(__name__)


class TypeInferenceEngine:
    """Engine for TypeScript type inference and analysis."""

    def __init__(self):
        """Initialize the type inference engine."""
        self._type_cache: Dict[str, Dict[str, Any]] = {}
        self._symbol_types: Dict[str, str] = {}
        self._type_definitions: Dict[str, Dict[str, Any]] = {}
        self._generic_constraints: Dict[str, Dict[str, str]] = {}

        # Built-in TypeScript types
        self._builtin_types = {
            "string",
            "number",
            "boolean",
            "object",
            "undefined",
            "null",
            "void",
            "never",
            "unknown",
            "any",
            "bigint",
            "symbol",
            "Array",
            "Promise",
            "Set",
            "Map",
            "WeakSet",
            "WeakMap",
            "Date",
            "RegExp",
            "Error",
            "Function",
        }

        # Initialize built-in type information
        self._init_builtin_types()

    def _init_builtin_types(self) -> None:
        """Initialize built-in TypeScript type information."""
        self._type_definitions.update(
            {
                "string": {
                    "kind": "primitive",
                    "properties": {
                        "length": "number",
                        "charAt": "(pos: number) => string",
                        "substring": "(start: number, end?: number) => string",
                        "indexOf": "(searchString: string, position?: number) => number",
                    },
                },
                "number": {
                    "kind": "primitive",
                    "properties": {
                        "toString": "(radix?: number) => string",
                        "toFixed": "(fractionDigits?: number) => string",
                        "valueOf": "() => number",
                    },
                },
                "boolean": {
                    "kind": "primitive",
                    "properties": {
                        "toString": "() => string",
                        "valueOf": "() => boolean",
                    },
                },
                "Array": {
                    "kind": "generic",
                    "type_parameters": ["T"],
                    "properties": {
                        "length": "number",
                        "push": "(...items: T[]) => number",
                        "pop": "() => T | undefined",
                        "map": "<U>(callbackfn: (value: T) => U) => U[]",
                    },
                },
                "Promise": {
                    "kind": "generic",
                    "type_parameters": ["T"],
                    "properties": {
                        "then": "<TResult1, TResult2>(onfulfilled?: (value: T) => TResult1) => Promise<TResult1>",
                        "catch": "<TResult>(onrejected?: (reason: any) => TResult) => Promise<T | TResult>",
                    },
                },
            }
        )

    def infer_type(self, node: Node, content: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Infer the type of a node based on its context and structure."""
        if context is None:
            context = {}

        node_type = node.type

        # Literal types
        if node_type == "string":
            return "string"
        elif node_type == "number":
            return "number"
        elif node_type == "true" or node_type == "false":
            return "boolean"
        elif node_type == "null":
            return "null"
        elif node_type == "undefined":
            return "undefined"

        # Array literals
        elif node_type == "array":
            element_types = set()
            for child in node.named_children:
                elem_type = self.infer_type(child, content, context)
                if elem_type:
                    element_types.add(elem_type)

            if element_types:
                if len(element_types) == 1:
                    return f"{list(element_types)[0]}[]"
                else:
                    union_type = " | ".join(sorted(element_types))
                    return f"({union_type})[]"
            return "any[]"

        # Object literals
        elif node_type == "object":
            return self._infer_object_literal_type(node, content, context)

        # Function expressions and arrow functions
        elif node_type in ["function_expression", "arrow_function"]:
            return self._infer_function_type(node, content, context)

        # Variable references
        elif node_type == "identifier":
            name = content[node.start_byte : node.end_byte]
            return context.get("variables", {}).get(name, "any")

        # Member expressions
        elif node_type == "member_expression":
            return self._infer_member_expression_type(node, content, context)

        # Call expressions
        elif node_type == "call_expression":
            return self._infer_call_expression_type(node, content, context)

        # Binary expressions
        elif node_type == "binary_expression":
            return self._infer_binary_expression_type(node, content, context)

        # Type assertions
        elif node_type == "type_assertion":
            type_node = node.child_by_field_name("type")
            if type_node:
                return content[type_node.start_byte : type_node.end_byte]

        # Conditional expressions
        elif node_type == "ternary_expression":
            true_branch = node.child_by_field_name("consequence")
            false_branch = node.child_by_field_name("alternative")

            true_type = self.infer_type(true_branch, content, context) if true_branch else "any"
            false_type = self.infer_type(false_branch, content, context) if false_branch else "any"

            if true_type == false_type:
                return true_type
            else:
                return f"{true_type} | {false_type}"

        return "any"

    def _infer_object_literal_type(self, node: Node, content: str, context: Dict[str, Any]) -> str:
        """Infer type for object literals."""
        properties = []

        for child in node.named_children:
            if child.type == "pair":
                key_node = child.child_by_field_name("key")
                value_node = child.child_by_field_name("value")

                if key_node and value_node:
                    key = content[key_node.start_byte : key_node.end_byte]
                    if key.startswith('"') or key.startswith("'"):
                        key = key[1:-1]  # Remove quotes

                    value_type = self.infer_type(value_node, content, context)
                    properties.append(f"{key}: {value_type}")
            elif child.type == "method_definition":
                name_node = child.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte : name_node.end_byte]
                    func_type = self._infer_function_type(child, content, context)
                    properties.append(f"{name}: {func_type}")

        if properties:
            return "{ " + "; ".join(properties) + " }"
        return "{}"

    def _infer_function_type(self, node: Node, content: str, context: Dict[str, Any]) -> str:
        """Infer type for functions."""
        # Extract parameters
        params_node = node.child_by_field_name("parameters")
        param_types = []

        if params_node:
            for child in params_node.named_children:
                if child.type in ["required_parameter", "optional_parameter"]:
                    pattern_node = child.child_by_field_name("pattern")
                    type_annotation = child.child_by_field_name("type")

                    if pattern_node:
                        param_name = content[pattern_node.start_byte : pattern_node.end_byte]
                        param_type = "any"

                        if type_annotation:
                            type_node = (
                                type_annotation.named_children[0]
                                if type_annotation.named_children
                                else None
                            )
                            if type_node:
                                param_type = content[type_node.start_byte : type_node.end_byte]

                        optional_suffix = "?" if child.type == "optional_parameter" else ""
                        param_types.append(f"{param_name}{optional_suffix}: {param_type}")

        # Extract return type
        return_type_node = node.child_by_field_name("return_type")
        return_type = "any"

        if return_type_node:
            type_node = (
                return_type_node.named_children[0] if return_type_node.named_children else None
            )
            if type_node:
                return_type = content[type_node.start_byte : type_node.end_byte]
        else:
            # Try to infer return type from body
            body_node = node.child_by_field_name("body")
            if body_node:
                return_type = self._infer_return_type_from_body(body_node, content, context)

        param_str = ", ".join(param_types)
        return f"({param_str}) => {return_type}"

    def _infer_member_expression_type(
        self, node: Node, content: str, context: Dict[str, Any]
    ) -> str:
        """Infer type for member expressions (obj.prop)."""
        object_node = node.child_by_field_name("object")
        property_node = node.child_by_field_name("property")

        if not object_node or not property_node:
            return "any"

        object_type = self.infer_type(object_node, content, context)
        property_name = content[property_node.start_byte : property_node.end_byte]

        # Look up property type in type definitions
        if object_type in self._type_definitions:
            type_def = self._type_definitions[object_type]
            properties = type_def.get("properties", {})
            return properties.get(property_name, "any")

        # Handle array access
        if object_type.endswith("[]") and property_name.isdigit():
            return object_type[:-2]  # Remove []

        # Handle generic types
        if self._is_generic_type(object_type):
            return self._resolve_generic_property_type(object_type, property_name)

        return "any"

    def _infer_call_expression_type(self, node: Node, content: str, context: Dict[str, Any]) -> str:
        """Infer type for call expressions."""
        function_node = node.child_by_field_name("function")

        if not function_node:
            return "any"

        # Handle different types of function calls
        if function_node.type == "identifier":
            func_name = content[function_node.start_byte : function_node.end_byte]

            # Built-in constructors
            if func_name in ["Array", "Object", "String", "Number", "Boolean"]:
                args_node = node.child_by_field_name("arguments")
                if args_node and args_node.named_child_count > 0:
                    # Constructor with arguments
                    if func_name == "Array":
                        first_arg = args_node.named_children[0]
                        if first_arg:
                            elem_type = self.infer_type(first_arg, content, context)
                            return f"{elem_type}[]"
                        return "any[]"
                return func_name.lower()

            # Look up function type in context
            func_type = context.get("functions", {}).get(func_name)
            if func_type:
                return self._extract_return_type_from_signature(func_type)

        elif function_node.type == "member_expression":
            # Method calls
            return self._infer_method_call_type(function_node, node, content, context)

        return "any"

    def _infer_binary_expression_type(
        self, node: Node, content: str, context: Dict[str, Any]
    ) -> str:
        """Infer type for binary expressions."""
        operator_node = node.child_by_field_name("operator")
        if not operator_node:
            return "any"

        operator = content[operator_node.start_byte : operator_node.end_byte]

        left_node = node.child_by_field_name("left")
        right_node = node.child_by_field_name("right")

        left_type = self.infer_type(left_node, content, context) if left_node else "any"
        right_type = self.infer_type(right_node, content, context) if right_node else "any"

        # Arithmetic operators
        if operator in ["+", "-", "*", "/", "%", "**"]:
            if operator == "+" and (left_type == "string" or right_type == "string"):
                return "string"
            elif left_type == "number" and right_type == "number":
                return "number"
            elif left_type == "bigint" or right_type == "bigint":
                return "bigint"
            return "number"

        # Comparison operators
        elif operator in ["<", ">", "<=", ">=", "==", "!=", "===", "!=="]:
            return "boolean"

        # Logical operators
        elif operator in ["&&", "||"]:
            if operator == "&&":
                # AND: result is right type if left is truthy
                return right_type
            else:
                # OR: result is union of both types
                if left_type == right_type:
                    return left_type
                return f"{left_type} | {right_type}"

        # Bitwise operators
        elif operator in ["&", "|", "^", "<<", ">>", ">>>"]:
            return "number"

        return "any"

    def _infer_return_type_from_body(
        self, body_node: Node, content: str, context: Dict[str, Any]
    ) -> str:
        """Infer return type by analyzing function body."""
        return_types = set()

        def find_return_statements(node: Node):
            if node.type == "return_statement":
                value_node = node.child_by_field_name("value")
                if value_node:
                    ret_type = self.infer_type(value_node, content, context)
                    return_types.add(ret_type)
                else:
                    return_types.add("void")

            for child in node.named_children:
                find_return_statements(child)

        find_return_statements(body_node)

        if not return_types:
            return "void"
        elif len(return_types) == 1:
            return list(return_types)[0]
        else:
            return " | ".join(sorted(return_types))

    def _infer_method_call_type(
        self, method_node: Node, call_node: Node, content: str, context: Dict[str, Any]
    ) -> str:
        """Infer type for method calls."""
        object_node = method_node.child_by_field_name("object")
        property_node = method_node.child_by_field_name("property")

        if not object_node or not property_node:
            return "any"

        object_type = self.infer_type(object_node, content, context)
        method_name = content[property_node.start_byte : property_node.end_byte]

        # Handle built-in method calls
        if object_type in self._type_definitions:
            type_def = self._type_definitions[object_type]
            properties = type_def.get("properties", {})
            method_sig = properties.get(method_name)

            if method_sig:
                return self._extract_return_type_from_signature(method_sig)

        # Handle array methods
        if object_type.endswith("[]"):
            element_type = object_type[:-2]

            if method_name == "map":
                # Infer from callback function
                args_node = call_node.child_by_field_name("arguments")
                if args_node and args_node.named_child_count > 0:
                    callback = args_node.named_children[0]
                    callback_return = self._infer_function_return_type(callback, content, context)
                    return f"{callback_return}[]"
                return "any[]"
            elif method_name in ["filter", "slice"]:
                return object_type
            elif method_name in ["pop", "shift"]:
                return f"{element_type} | undefined"
            elif method_name in ["push", "unshift"]:
                return "number"
            elif method_name == "join":
                return "string"

        return "any"

    def _infer_function_return_type(
        self, func_node: Node, content: str, context: Dict[str, Any]
    ) -> str:
        """Infer return type of a function node."""
        if func_node.type in ["function_expression", "arrow_function"]:
            return_type_node = func_node.child_by_field_name("return_type")
            if return_type_node:
                type_node = (
                    return_type_node.named_children[0] if return_type_node.named_children else None
                )
                if type_node:
                    return content[type_node.start_byte : type_node.end_byte]

            # Infer from body
            body_node = func_node.child_by_field_name("body")
            if body_node:
                return self._infer_return_type_from_body(body_node, content, context)

        return "any"

    def _extract_return_type_from_signature(self, signature: str) -> str:
        """Extract return type from a function signature string."""
        # Parse signature like "(param: type) => returnType"
        arrow_index = signature.rfind("=>")
        if arrow_index != -1:
            return_part = signature[arrow_index + 2 :].strip()
            # Handle generic return types
            if return_part.startswith("<"):
                # Generic function, extract the actual return type
                bracket_count = 0
                for i, char in enumerate(return_part):
                    if char == "<":
                        bracket_count += 1
                    elif char == ">":
                        bracket_count -= 1
                        if bracket_count == 0:
                            return return_part[i + 1 :].strip()
            return return_part
        return "any"

    def _is_generic_type(self, type_str: str) -> bool:
        """Check if a type string represents a generic type."""
        return "<" in type_str and ">" in type_str

    def _resolve_generic_property_type(self, generic_type: str, property_name: str) -> str:
        """Resolve property type for generic types."""
        # Extract base type and type arguments
        base_type, type_args = self._parse_generic_type(generic_type)

        if base_type in self._type_definitions:
            type_def = self._type_definitions[base_type]
            properties = type_def.get("properties", {})
            property_sig = properties.get(property_name)

            if property_sig and type_args:
                # Substitute type parameters
                return self._substitute_type_parameters(
                    property_sig, type_def.get("type_parameters", []), type_args
                )

        return "any"

    def _parse_generic_type(self, type_str: str) -> Tuple[str, List[str]]:
        """Parse a generic type string into base type and type arguments."""
        angle_start = type_str.find("<")
        if angle_start == -1:
            return type_str, []

        base_type = type_str[:angle_start]
        type_args_str = type_str[angle_start + 1 : -1]  # Remove < and >

        # Simple parsing - split by commas (doesn't handle nested generics)
        type_args = [arg.strip() for arg in type_args_str.split(",")]

        return base_type, type_args

    def _substitute_type_parameters(
        self, signature: str, type_params: List[str], type_args: List[str]
    ) -> str:
        """Substitute type parameters with actual type arguments."""
        result = signature

        for param, arg in zip(type_params, type_args):
            result = result.replace(param, arg)

        return result

    def analyze_type_compatibility(self, source_type: str, target_type: str) -> bool:
        """Analyze if source type is compatible with target type."""
        # Exact match
        if source_type == target_type:
            return True

        # Any type is compatible with everything
        if source_type == "any" or target_type == "any":
            return True

        # Unknown is compatible with any
        if source_type == "unknown":
            return True

        # Never is compatible with nothing (except never)
        if source_type == "never":
            return target_type == "never"

        # Null and undefined compatibility
        if source_type in ["null", "undefined"]:
            return target_type in ["null", "undefined", "any", "unknown"]

        # Union types
        if " | " in source_type:
            source_parts = [t.strip() for t in source_type.split(" | ")]
            return all(self.analyze_type_compatibility(part, target_type) for part in source_parts)

        if " | " in target_type:
            target_parts = [t.strip() for t in target_type.split(" | ")]
            return any(self.analyze_type_compatibility(source_type, part) for part in target_parts)

        # Array type compatibility
        if source_type.endswith("[]") and target_type.endswith("[]"):
            source_elem = source_type[:-2]
            target_elem = target_type[:-2]
            return self.analyze_type_compatibility(source_elem, target_elem)

        # Object type compatibility (simplified)
        if source_type.startswith("{") and target_type.startswith("{"):
            return self._analyze_object_type_compatibility(source_type, target_type)

        # Function type compatibility
        if "=>" in source_type and "=>" in target_type:
            return self._analyze_function_type_compatibility(source_type, target_type)

        # Primitive type compatibility
        if source_type in self._builtin_types and target_type in self._builtin_types:
            return self._analyze_primitive_compatibility(source_type, target_type)

        return False

    def _analyze_object_type_compatibility(self, source_type: str, target_type: str) -> bool:
        """Analyze compatibility between object types."""
        # Simplified object type compatibility
        source_props = self._parse_object_type(source_type)
        target_props = self._parse_object_type(target_type)

        # Source must have all required properties of target
        for prop_name, prop_type in target_props.items():
            if prop_name not in source_props:
                return False
            if not self.analyze_type_compatibility(source_props[prop_name], prop_type):
                return False

        return True

    def _analyze_function_type_compatibility(self, source_type: str, target_type: str) -> bool:
        """Analyze compatibility between function types."""
        # Function type compatibility is complex in TypeScript
        # For now, do a simple signature comparison
        return source_type == target_type

    def _analyze_primitive_compatibility(self, source_type: str, target_type: str) -> bool:
        """Analyze compatibility between primitive types."""
        # Exact match for primitives
        return source_type == target_type

    def _parse_object_type(self, type_str: str) -> Dict[str, str]:
        """Parse object type string into property map."""
        # Simplified object type parsing
        if not type_str.startswith("{") or not type_str.endswith("}"):
            return {}

        inner = type_str[1:-1].strip()
        if not inner:
            return {}

        properties = {}
        for prop_str in inner.split(";"):
            prop_str = prop_str.strip()
            if ":" in prop_str:
                name, type_part = prop_str.split(":", 1)
                properties[name.strip()] = type_part.strip()

        return properties

    def get_symbol_type(self, symbol_name: str, file_path: Path) -> Optional[str]:
        """Get the type of a symbol."""
        file_key = str(file_path)
        return self._symbol_types.get(f"{file_key}:{symbol_name}")

    def set_symbol_type(self, symbol_name: str, symbol_type: str, file_path: Path) -> None:
        """Set the type of a symbol."""
        file_key = str(file_path)
        self._symbol_types[f"{file_key}:{symbol_name}"] = symbol_type

    def register_type_definition(self, type_name: str, type_def: Dict[str, Any]) -> None:
        """Register a new type definition."""
        self._type_definitions[type_name] = type_def

    def get_type_definition(self, type_name: str) -> Optional[Dict[str, Any]]:
        """Get a type definition."""
        return self._type_definitions.get(type_name)

    def clear_cache(self) -> None:
        """Clear all cached type information."""
        self._type_cache.clear()
        self._symbol_types.clear()


class TypeAnnotationExtractor:
    """Extracts and parses TypeScript type annotations."""

    def __init__(self):
        """Initialize the type annotation extractor."""

    def extract_type_annotation(self, node: Node, content: str) -> Optional[str]:
        """Extract type annotation from a node."""
        # Look for type annotation
        type_annotation = node.child_by_field_name("type")
        if type_annotation:
            # Skip the ':' token
            type_node = (
                type_annotation.named_children[0] if type_annotation.named_children else None
            )
            if type_node:
                return content[type_node.start_byte : type_node.end_byte]

        return None

    def parse_type_string(self, type_str: str) -> Dict[str, Any]:
        """Parse a type string into structured information."""
        type_str = type_str.strip()

        # Union types
        if " | " in type_str:
            return {
                "kind": "union",
                "types": [self.parse_type_string(t.strip()) for t in type_str.split(" | ")],
            }

        # Intersection types
        if " & " in type_str:
            return {
                "kind": "intersection",
                "types": [self.parse_type_string(t.strip()) for t in type_str.split(" & ")],
            }

        # Array types
        if type_str.endswith("[]"):
            return {
                "kind": "array",
                "element_type": self.parse_type_string(type_str[:-2]),
            }

        # Generic types
        if "<" in type_str and ">" in type_str:
            angle_start = type_str.find("<")
            base_type = type_str[:angle_start]
            type_args_str = type_str[angle_start + 1 : -1]

            type_args = []
            if type_args_str.strip():
                # Simple parsing - doesn't handle nested generics perfectly
                type_args = [
                    self.parse_type_string(arg.strip()) for arg in type_args_str.split(",")
                ]

            return {
                "kind": "generic",
                "base_type": base_type,
                "type_arguments": type_args,
            }

        # Function types
        if "=>" in type_str:
            arrow_index = type_str.rfind("=>")
            params_str = type_str[:arrow_index].strip()
            return_str = type_str[arrow_index + 2 :].strip()

            # Parse parameters
            if params_str.startswith("(") and params_str.endswith(")"):
                params_str = params_str[1:-1]

            params = []
            if params_str.strip():
                for param_str in params_str.split(","):
                    param_str = param_str.strip()
                    if ":" in param_str:
                        name, param_type = param_str.split(":", 1)
                        params.append(
                            {
                                "name": name.strip(),
                                "type": self.parse_type_string(param_type.strip()),
                            }
                        )

            return {
                "kind": "function",
                "parameters": params,
                "return_type": self.parse_type_string(return_str),
            }

        # Object types
        if type_str.startswith("{") and type_str.endswith("}"):
            inner = type_str[1:-1].strip()
            properties = {}

            if inner:
                for prop_str in inner.split(";"):
                    prop_str = prop_str.strip()
                    if ":" in prop_str:
                        name, prop_type = prop_str.split(":", 1)
                        properties[name.strip()] = self.parse_type_string(prop_type.strip())

            return {"kind": "object", "properties": properties}

        # Tuple types
        if type_str.startswith("[") and type_str.endswith("]"):
            inner = type_str[1:-1].strip()
            element_types = []

            if inner:
                element_types = [self.parse_type_string(t.strip()) for t in inner.split(",")]

            return {"kind": "tuple", "element_types": element_types}

        # Primitive/identifier types
        return {"kind": "identifier", "name": type_str}
