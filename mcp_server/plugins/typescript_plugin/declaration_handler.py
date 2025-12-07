"""TypeScript declaration file (.d.ts) handler for type information extraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from tree_sitter import Node

logger = logging.getLogger(__name__)


class DeclarationHandler:
    """Handler for TypeScript declaration files and type information."""

    def __init__(self):
        """Initialize the declaration handler."""
        self._declaration_cache: Dict[str, Dict[str, Any]] = {}
        self._ambient_declarations: Dict[str, List[Dict[str, Any]]] = {}

    def parse_declaration_file(self, path: Path, content: str, root_node: Node) -> Dict[str, Any]:
        """Parse a TypeScript declaration file and extract type information."""
        file_key = str(path)

        if file_key in self._declaration_cache:
            return self._declaration_cache[file_key]

        declarations = {
            "interfaces": [],
            "types": [],
            "functions": [],
            "classes": [],
            "modules": [],
            "namespaces": [],
            "enums": [],
            "variables": [],
            "exports": [],
            "imports": [],
        }

        self._extract_declarations(root_node, content, declarations, [])

        self._declaration_cache[file_key] = declarations
        return declarations

    def _extract_declarations(
        self,
        node: Node,
        content: str,
        declarations: Dict[str, List],
        scope_path: List[str],
    ) -> None:
        """Recursively extract declarations from the AST."""

        # Interface declarations
        if node.type == "interface_declaration":
            interface_info = self._extract_interface(node, content, scope_path)
            if interface_info:
                declarations["interfaces"].append(interface_info)

        # Type alias declarations
        elif node.type == "type_alias_declaration":
            type_info = self._extract_type_alias(node, content, scope_path)
            if type_info:
                declarations["types"].append(type_info)

        # Function declarations
        elif node.type in ["function_declaration", "function_signature"]:
            func_info = self._extract_function_declaration(node, content, scope_path)
            if func_info:
                declarations["functions"].append(func_info)

        # Class declarations
        elif node.type == "class_declaration":
            class_info = self._extract_class_declaration(node, content, scope_path)
            if class_info:
                declarations["classes"].append(class_info)

        # Module/namespace declarations
        elif node.type in ["module_declaration", "namespace_declaration"]:
            module_info = self._extract_module_declaration(node, content, scope_path)
            if module_info:
                declarations["modules"].append(module_info)

                # Extract nested declarations
                body = node.child_by_field_name("body")
                if body:
                    nested_scope = scope_path + [module_info["name"]]
                    for child in body.named_children:
                        self._extract_declarations(child, content, declarations, nested_scope)

        # Enum declarations
        elif node.type == "enum_declaration":
            enum_info = self._extract_enum_declaration(node, content, scope_path)
            if enum_info:
                declarations["enums"].append(enum_info)

        # Variable declarations
        elif node.type in ["variable_declaration", "lexical_declaration"]:
            var_info = self._extract_variable_declaration(node, content, scope_path)
            if var_info:
                declarations["variables"].extend(var_info)

        # Export declarations
        elif node.type in ["export_statement", "export_declaration"]:
            export_info = self._extract_export_declaration(node, content, scope_path)
            if export_info:
                declarations["exports"].append(export_info)

        # Import declarations
        elif node.type in ["import_statement", "import_declaration"]:
            import_info = self._extract_import_declaration(node, content)
            if import_info:
                declarations["imports"].append(import_info)

        # Continue recursion for other nodes
        else:
            for child in node.named_children:
                self._extract_declarations(child, content, declarations, scope_path)

    def _extract_interface(
        self, node: Node, content: str, scope_path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract interface declaration information."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Extract type parameters
        type_params = []
        type_params_node = node.child_by_field_name("type_parameters")
        if type_params_node:
            type_params = self._extract_type_parameters(type_params_node, content)

        # Extract heritage (extends clause)
        heritage = []
        heritage_node = node.child_by_field_name("heritage")
        if heritage_node:
            heritage = self._extract_heritage_clause(heritage_node, content)

        # Extract interface body
        body_node = node.child_by_field_name("body")
        properties = []
        methods = []

        if body_node:
            for child in body_node.named_children:
                if child.type == "property_signature":
                    prop_info = self._extract_property_signature(child, content)
                    if prop_info:
                        properties.append(prop_info)
                elif child.type == "method_signature":
                    method_info = self._extract_method_signature(child, content)
                    if method_info:
                        methods.append(method_info)

        return {
            "name": name,
            "full_name": ".".join(scope_path + [name]),
            "type_parameters": type_params,
            "extends": heritage,
            "properties": properties,
            "methods": methods,
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
            "scope": ".".join(scope_path) if scope_path else None,
        }

    def _extract_type_alias(
        self, node: Node, content: str, scope_path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract type alias declaration information."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Extract type parameters
        type_params = []
        type_params_node = node.child_by_field_name("type_parameters")
        if type_params_node:
            type_params = self._extract_type_parameters(type_params_node, content)

        # Extract type definition
        type_node = node.child_by_field_name("type")
        type_def = None
        if type_node:
            type_def = content[type_node.start_byte : type_node.end_byte]

        return {
            "name": name,
            "full_name": ".".join(scope_path + [name]),
            "type_parameters": type_params,
            "type_definition": type_def,
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
            "scope": ".".join(scope_path) if scope_path else None,
        }

    def _extract_function_declaration(
        self, node: Node, content: str, scope_path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract function declaration information."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Extract type parameters
        type_params = []
        type_params_node = node.child_by_field_name("type_parameters")
        if type_params_node:
            type_params = self._extract_type_parameters(type_params_node, content)

        # Extract parameters
        params = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            params = self._extract_function_parameters(params_node, content)

        # Extract return type
        return_type = None
        return_type_node = node.child_by_field_name("return_type")
        if return_type_node:
            # Skip the ':' token
            type_node = (
                return_type_node.named_children[0] if return_type_node.named_children else None
            )
            if type_node:
                return_type = content[type_node.start_byte : type_node.end_byte]

        # Check for async/generator modifiers
        is_async = self._has_modifier(node, content, "async")
        is_generator = self._has_modifier(node, content, "*")

        signature = self._build_function_signature(
            name, type_params, params, return_type, is_async, is_generator
        )

        return {
            "name": name,
            "full_name": ".".join(scope_path + [name]),
            "type_parameters": type_params,
            "parameters": params,
            "return_type": return_type,
            "is_async": is_async,
            "is_generator": is_generator,
            "signature": signature,
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
            "scope": ".".join(scope_path) if scope_path else None,
        }

    def _extract_class_declaration(
        self, node: Node, content: str, scope_path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract class declaration information."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Extract type parameters
        type_params = []
        type_params_node = node.child_by_field_name("type_parameters")
        if type_params_node:
            type_params = self._extract_type_parameters(type_params_node, content)

        # Extract heritage (extends/implements)
        extends_clause = None
        implements_clause = []
        heritage_node = node.child_by_field_name("heritage")
        if heritage_node:
            for child in heritage_node.named_children:
                if child.type == "extends_clause":
                    type_node = child.named_children[0] if child.named_children else None
                    if type_node:
                        extends_clause = content[type_node.start_byte : type_node.end_byte]
                elif child.type == "implements_clause":
                    for impl_child in child.named_children:
                        implements_clause.append(
                            content[impl_child.start_byte : impl_child.end_byte]
                        )

        # Extract class body
        body_node = node.child_by_field_name("body")
        properties = []
        methods = []

        if body_node:
            for child in body_node.named_children:
                if child.type == "property_declaration":
                    prop_info = self._extract_property_declaration(child, content)
                    if prop_info:
                        properties.append(prop_info)
                elif child.type == "method_declaration":
                    method_info = self._extract_method_declaration(child, content)
                    if method_info:
                        methods.append(method_info)

        return {
            "name": name,
            "full_name": ".".join(scope_path + [name]),
            "type_parameters": type_params,
            "extends": extends_clause,
            "implements": implements_clause,
            "properties": properties,
            "methods": methods,
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
            "scope": ".".join(scope_path) if scope_path else None,
        }

    def _extract_module_declaration(
        self, node: Node, content: str, scope_path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract module/namespace declaration information."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        return {
            "name": name,
            "full_name": ".".join(scope_path + [name]),
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
            "scope": ".".join(scope_path) if scope_path else None,
        }

    def _extract_enum_declaration(
        self, node: Node, content: str, scope_path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract enum declaration information."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Extract enum members
        body_node = node.child_by_field_name("body")
        members = []

        if body_node:
            for child in body_node.named_children:
                if child.type == "property_identifier":
                    member_name = content[child.start_byte : child.end_byte]
                    members.append({"name": member_name, "value": None})
                elif child.type == "enum_assignment":
                    name_child = child.child_by_field_name("name")
                    value_child = child.child_by_field_name("value")
                    if name_child:
                        member_name = content[name_child.start_byte : name_child.end_byte]
                        member_value = None
                        if value_child:
                            member_value = content[value_child.start_byte : value_child.end_byte]
                        members.append({"name": member_name, "value": member_value})

        return {
            "name": name,
            "full_name": ".".join(scope_path + [name]),
            "members": members,
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
            "scope": ".".join(scope_path) if scope_path else None,
        }

    def _extract_variable_declaration(
        self, node: Node, content: str, scope_path: List[str]
    ) -> List[Dict[str, Any]]:
        """Extract variable declaration information."""
        variables = []
        kind = self._get_declaration_kind(node, content)

        for child in node.named_children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                type_node = child.child_by_field_name("type")

                if name_node:
                    name = content[name_node.start_byte : name_node.end_byte]
                    var_type = None

                    if type_node:
                        # Skip the ':' token
                        actual_type = (
                            type_node.named_children[0] if type_node.named_children else None
                        )
                        if actual_type:
                            var_type = content[actual_type.start_byte : actual_type.end_byte]

                    variables.append(
                        {
                            "name": name,
                            "full_name": ".".join(scope_path + [name]),
                            "kind": kind,
                            "type": var_type,
                            "line": child.start_point[0] + 1,
                            "span": (child.start_point[0] + 1, child.end_point[0] + 1),
                            "scope": ".".join(scope_path) if scope_path else None,
                        }
                    )

        return variables

    def _extract_export_declaration(
        self, node: Node, content: str, scope_path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract export declaration information."""
        # Check for default export
        is_default = False
        for child in node.children:
            if (
                not child.is_named
                and content[child.start_byte : child.end_byte].strip() == "default"
            ):
                is_default = True
                break

        # Extract what's being exported
        declaration = node.child_by_field_name("declaration")
        exported_names = []

        if declaration:
            # Direct export (export function foo() {})
            if declaration.type in [
                "function_declaration",
                "class_declaration",
                "interface_declaration",
                "type_alias_declaration",
            ]:
                name_node = declaration.child_by_field_name("name")
                if name_node:
                    exported_names.append(content[name_node.start_byte : name_node.end_byte])
        else:
            # Named exports (export { foo, bar })
            for child in node.named_children:
                if child.type == "export_clause":
                    for spec in child.named_children:
                        if spec.type == "export_specifier":
                            name_node = spec.child_by_field_name("name")
                            if name_node:
                                exported_names.append(
                                    content[name_node.start_byte : name_node.end_byte]
                                )

        return {
            "names": exported_names,
            "is_default": is_default,
            "line": node.start_point[0] + 1,
        }

    def _extract_import_declaration(self, node: Node, content: str) -> Optional[Dict[str, Any]]:
        """Extract import declaration information."""
        source_node = node.child_by_field_name("source")
        if not source_node:
            return None

        source = content[source_node.start_byte : source_node.end_byte].strip("\"'`")

        # Extract imported names
        default_import = None
        namespace_import = None
        named_imports = []

        import_clause = node.child_by_field_name("import_clause")
        if import_clause:
            for child in import_clause.named_children:
                if child.type == "identifier":
                    default_import = content[child.start_byte : child.end_byte]
                elif child.type == "namespace_import":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        namespace_import = content[name_node.start_byte : name_node.end_byte]
                elif child.type == "named_imports":
                    for spec in child.named_children:
                        if spec.type == "import_specifier":
                            name_node = spec.child_by_field_name("name")
                            alias_node = spec.child_by_field_name("alias")
                            if name_node:
                                name = content[name_node.start_byte : name_node.end_byte]
                                alias = None
                                if alias_node:
                                    alias = content[alias_node.start_byte : alias_node.end_byte]
                                named_imports.append({"name": name, "alias": alias})

        return {
            "source": source,
            "default_import": default_import,
            "namespace_import": namespace_import,
            "named_imports": named_imports,
            "line": node.start_point[0] + 1,
        }

    def _extract_type_parameters(self, node: Node, content: str) -> List[Dict[str, Any]]:
        """Extract type parameters from a node."""
        type_params = []

        for child in node.named_children:
            if child.type == "type_parameter":
                name_node = child.child_by_field_name("name")
                constraint_node = child.child_by_field_name("constraint")
                default_node = child.child_by_field_name("default_type")

                if name_node:
                    param_name = content[name_node.start_byte : name_node.end_byte]
                    constraint = None
                    default_type = None

                    if constraint_node:
                        constraint = content[constraint_node.start_byte : constraint_node.end_byte]
                    if default_node:
                        default_type = content[default_node.start_byte : default_node.end_byte]

                    type_params.append(
                        {
                            "name": param_name,
                            "constraint": constraint,
                            "default": default_type,
                        }
                    )

        return type_params

    def _extract_heritage_clause(self, node: Node, content: str) -> List[str]:
        """Extract heritage clause (extends/implements) information."""
        heritage = []

        for child in node.named_children:
            if child.type in ["extends_clause", "implements_clause"]:
                for type_child in child.named_children:
                    heritage.append(content[type_child.start_byte : type_child.end_byte])

        return heritage

    def _extract_property_signature(self, node: Node, content: str) -> Optional[Dict[str, Any]]:
        """Extract property signature from interface."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Extract type
        type_node = node.child_by_field_name("type")
        prop_type = None
        if type_node:
            prop_type = content[type_node.start_byte : type_node.end_byte]

        # Check if optional
        is_optional = "?" in content[name_node.end_byte : name_node.end_byte + 5]

        return {
            "name": name,
            "type": prop_type,
            "optional": is_optional,
            "line": node.start_point[0] + 1,
        }

    def _extract_method_signature(self, node: Node, content: str) -> Optional[Dict[str, Any]]:
        """Extract method signature from interface."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Extract parameters
        params = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            params = self._extract_function_parameters(params_node, content)

        # Extract return type
        return_type = None
        return_type_node = node.child_by_field_name("return_type")
        if return_type_node:
            type_node = (
                return_type_node.named_children[0] if return_type_node.named_children else None
            )
            if type_node:
                return_type = content[type_node.start_byte : type_node.end_byte]

        return {
            "name": name,
            "parameters": params,
            "return_type": return_type,
            "line": node.start_point[0] + 1,
        }

    def _extract_property_declaration(self, node: Node, content: str) -> Optional[Dict[str, Any]]:
        """Extract property declaration from class."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Extract type
        type_node = node.child_by_field_name("type")
        prop_type = None
        if type_node:
            prop_type = content[type_node.start_byte : type_node.end_byte]

        # Extract modifiers
        is_static = self._has_modifier(node, content, "static")
        is_readonly = self._has_modifier(node, content, "readonly")
        is_private = self._has_modifier(node, content, "private")
        is_protected = self._has_modifier(node, content, "protected")
        _ = self._has_modifier(node, content, "public")

        visibility = "public"
        if is_private:
            visibility = "private"
        elif is_protected:
            visibility = "protected"

        return {
            "name": name,
            "type": prop_type,
            "static": is_static,
            "readonly": is_readonly,
            "visibility": visibility,
            "line": node.start_point[0] + 1,
        }

    def _extract_method_declaration(self, node: Node, content: str) -> Optional[Dict[str, Any]]:
        """Extract method declaration from class."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Extract parameters
        params = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            params = self._extract_function_parameters(params_node, content)

        # Extract return type
        return_type = None
        return_type_node = node.child_by_field_name("return_type")
        if return_type_node:
            type_node = (
                return_type_node.named_children[0] if return_type_node.named_children else None
            )
            if type_node:
                return_type = content[type_node.start_byte : type_node.end_byte]

        # Extract modifiers
        is_static = self._has_modifier(node, content, "static")
        is_async = self._has_modifier(node, content, "async")
        is_private = self._has_modifier(node, content, "private")
        is_protected = self._has_modifier(node, content, "protected")
        _ = self._has_modifier(node, content, "public")

        visibility = "public"
        if is_private:
            visibility = "private"
        elif is_protected:
            visibility = "protected"

        return {
            "name": name,
            "parameters": params,
            "return_type": return_type,
            "static": is_static,
            "async": is_async,
            "visibility": visibility,
            "line": node.start_point[0] + 1,
        }

    def _extract_function_parameters(self, node: Node, content: str) -> List[Dict[str, Any]]:
        """Extract function parameters with type information."""
        params = []

        for child in node.named_children:
            if child.type in [
                "required_parameter",
                "optional_parameter",
                "rest_parameter",
            ]:
                param_info = self._extract_parameter_info(child, content)
                if param_info:
                    params.append(param_info)

        return params

    def _extract_parameter_info(self, node: Node, content: str) -> Optional[Dict[str, Any]]:
        """Extract information about a single parameter."""
        pattern_node = node.child_by_field_name("pattern")
        type_node = node.child_by_field_name("type")

        if not pattern_node:
            return None

        name = content[pattern_node.start_byte : pattern_node.end_byte]
        param_type = None

        if type_node:
            param_type = content[type_node.start_byte : type_node.end_byte]

        is_optional = node.type == "optional_parameter"
        is_rest = node.type == "rest_parameter"

        return {
            "name": name,
            "type": param_type,
            "optional": is_optional,
            "rest": is_rest,
        }

    def _has_modifier(self, node: Node, content: str, modifier: str) -> bool:
        """Check if a node has a specific modifier."""
        for child in node.children:
            if not child.is_named:
                text = content[child.start_byte : child.end_byte].strip()
                if text == modifier:
                    return True
        return False

    def _get_declaration_kind(self, node: Node, content: str) -> str:
        """Get the declaration keyword (var, let, const)."""
        for child in node.children:
            if not child.is_named:
                text = content[child.start_byte : child.end_byte].strip()
                if text in ["var", "let", "const"]:
                    return text
        return "const"

    def _build_function_signature(
        self,
        name: str,
        type_params: List[Dict],
        params: List[Dict],
        return_type: Optional[str],
        is_async: bool,
        is_generator: bool,
    ) -> str:
        """Build a function signature string."""
        sig_parts = []

        if is_async:
            sig_parts.append("async")

        sig_parts.append("function")

        if is_generator:
            sig_parts.append("*")

        sig_parts.append(name)

        # Type parameters
        if type_params:
            type_param_strs = []
            for tp in type_params:
                tp_str = tp["name"]
                if tp.get("constraint"):
                    tp_str += f" extends {tp['constraint']}"
                if tp.get("default"):
                    tp_str += f" = {tp['default']}"
                type_param_strs.append(tp_str)
            sig_parts.append(f"<{', '.join(type_param_strs)}>")

        # Parameters
        param_strs = []
        for param in params:
            param_str = param["name"]
            if param.get("optional"):
                param_str += "?"
            if param.get("type"):
                param_str += f": {param['type']}"
            param_strs.append(param_str)

        sig_parts.append(f"({', '.join(param_strs)})")

        # Return type
        if return_type:
            sig_parts.append(f": {return_type}")

        return " ".join(sig_parts)

    def get_type_information(self, symbol_name: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get type information for a symbol from declaration files."""
        file_key = str(file_path)

        if file_key not in self._declaration_cache:
            return None

        declarations = self._declaration_cache[file_key]

        # Search in all declaration types
        for decl_type, items in declarations.items():
            for item in items:
                if item.get("name") == symbol_name or item.get("full_name") == symbol_name:
                    return {
                        "type": decl_type.rstrip("s"),  # Remove plural
                        "declaration": item,
                        "file": file_path,
                    }

        return None

    def find_all_exports(self, file_path: Path) -> List[Dict[str, Any]]:
        """Find all exported symbols from a declaration file."""
        file_key = str(file_path)

        if file_key not in self._declaration_cache:
            return []

        return self._declaration_cache[file_key].get("exports", [])
