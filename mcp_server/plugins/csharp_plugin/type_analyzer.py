"""Type system analysis for C# code with generics support."""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GenericConstraint:
    """Represents a generic type constraint."""

    parameter: str
    constraint_type: str  # 'class', 'struct', 'new()', 'interface', 'base_class'
    constraint_value: Optional[str] = None


@dataclass
class GenericParameter:
    """Represents a generic type parameter."""

    name: str
    constraints: List[GenericConstraint]
    variance: Optional[str] = None  # 'in', 'out', or None


@dataclass
class TypeInfo:
    """Represents information about a C# type."""

    name: str
    kind: str  # 'class', 'interface', 'struct', 'enum', 'delegate', 'record'
    namespace: Optional[str]
    modifiers: List[str]  # 'public', 'private', 'static', 'abstract', etc.
    generic_parameters: List[GenericParameter]
    base_type: Optional[str]
    implemented_interfaces: List[str]
    line: int
    end_line: int
    signature: str


@dataclass
class MethodInfo:
    """Represents information about a C# method."""

    name: str
    return_type: str
    parameters: List[Dict[str, str]]
    modifiers: List[str]
    generic_parameters: List[GenericParameter]
    is_async: bool
    line: int
    signature: str


@dataclass
class PropertyInfo:
    """Represents information about a C# property."""

    name: str
    type: str
    modifiers: List[str]
    has_getter: bool
    has_setter: bool
    is_auto_property: bool
    line: int
    signature: str


class TypeAnalyzer:
    """Analyzes C# type system including generics, inheritance, and members."""

    def __init__(self):
        """Initialize the type analyzer."""
        self.type_cache: Dict[str, TypeInfo] = {}
        self.method_cache: Dict[str, List[MethodInfo]] = {}
        self.property_cache: Dict[str, List[PropertyInfo]] = {}

    def analyze_types(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze all types in the given C# content.

        Args:
            content: C# source code content
            file_path: Path to the source file

        Returns:
            Dictionary containing type analysis results
        """
        analysis = {
            "file_path": file_path,
            "types": [],
            "methods": [],
            "properties": [],
            "fields": [],
            "events": [],
            "generic_types": [],
            "async_patterns": [],
            "linq_queries": [],
        }

        try:
            # Analyze type declarations
            analysis["types"] = self._extract_types(content)

            # Analyze methods
            analysis["methods"] = self._extract_methods(content)

            # Analyze properties
            analysis["properties"] = self._extract_properties(content)

            # Analyze fields
            analysis["fields"] = self._extract_fields(content)

            # Analyze events
            analysis["events"] = self._extract_events(content)

            # Find generic types
            analysis["generic_types"] = self._find_generic_types(content)

            # Find async patterns
            analysis["async_patterns"] = self._find_async_patterns(content)

            # Find LINQ queries
            analysis["linq_queries"] = self._find_linq_queries(content)

            # Cache the results
            for type_info in analysis["types"]:
                self.type_cache[f"{file_path}:{type_info['name']}"] = type_info

        except Exception as e:
            logger.error(f"Error analyzing types in {file_path}: {e}")

        return analysis

    def _extract_types(self, content: str) -> List[Dict[str, Any]]:
        """Extract type declarations with generic support."""
        types = []

        # Enhanced pattern for type declarations including generics
        type_pattern = r"""
            (?P<modifiers>(?:public|private|protected|internal|static|abstract|sealed|partial|readonly|unsafe)\s+)*
            (?P<kind>class|interface|struct|enum|delegate|record)\s+
            (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*
            (?P<generics><[^>]+>)?\s*
            (?P<inheritance>:\s*[^{;]+)?\s*
            (?P<constraints>where\s+[^{;]+)?\s*
            [{;]
        """

        for match in re.finditer(type_pattern, content, re.VERBOSE | re.MULTILINE):
            line_number = content[: match.start()].count("\n") + 1

            modifiers = []
            if match.group("modifiers"):
                modifiers = [m.strip() for m in match.group("modifiers").split() if m.strip()]

            generic_params = []
            if match.group("generics"):
                generic_params = self._parse_generic_parameters(
                    match.group("generics"), match.group("constraints")
                )

            base_type = None
            interfaces = []
            if match.group("inheritance"):
                inheritance_parts = match.group("inheritance")[1:].strip().split(",")
                if inheritance_parts:
                    # First part is base class for classes, all parts are interfaces for interfaces
                    kind = match.group("kind")
                    if kind == "class" and inheritance_parts:
                        # Check if first part looks like an interface (starts with I)
                        first_part = inheritance_parts[0].strip()
                        if (
                            first_part.startswith("I")
                            and len(first_part) > 1
                            and first_part[1].isupper()
                        ):
                            interfaces = [p.strip() for p in inheritance_parts]
                        else:
                            base_type = first_part
                            interfaces = [p.strip() for p in inheritance_parts[1:]]
                    else:
                        interfaces = [p.strip() for p in inheritance_parts]

            type_info = {
                "name": match.group("name"),
                "kind": match.group("kind"),
                "modifiers": modifiers,
                "generic_parameters": generic_params,
                "base_type": base_type,
                "implemented_interfaces": interfaces,
                "line": line_number,
                "end_line": self._find_type_end_line(content, match.start()),
                "signature": match.group(0).strip(),
                "is_generic": len(generic_params) > 0,
            }

            types.append(type_info)

        return types

    def _parse_generic_parameters(
        self, generics_str: str, constraints_str: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Parse generic parameters and their constraints."""
        if not generics_str:
            return []

        # Remove < > brackets
        generics_content = generics_str.strip("<>")

        # Parse parameters
        param_parts = [p.strip() for p in generics_content.split(",")]
        parameters = []

        for param in param_parts:
            # Handle variance (in/out)
            variance = None
            if param.startswith("in "):
                variance = "in"
                param = param[3:].strip()
            elif param.startswith("out "):
                variance = "out"
                param = param[4:].strip()

            param_info = {"name": param, "variance": variance, "constraints": []}

            # Parse constraints if present
            if constraints_str:
                param_constraints = self._parse_constraints(param, constraints_str)
                param_info["constraints"] = param_constraints

            parameters.append(param_info)

        return parameters

    def _parse_constraints(self, param_name: str, constraints_str: str) -> List[Dict[str, Any]]:
        """Parse where constraints for a generic parameter."""
        constraints = []

        # Find constraints for this parameter
        pattern = rf"where\s+{re.escape(param_name)}\s*:\s*([^,{{;]+)"
        match = re.search(pattern, constraints_str)

        if match:
            constraint_parts = [c.strip() for c in match.group(1).split(",")]

            for constraint in constraint_parts:
                constraint = constraint.strip()

                if constraint == "class":
                    constraints.append({"type": "class", "value": None})
                elif constraint == "struct":
                    constraints.append({"type": "struct", "value": None})
                elif constraint == "new()":
                    constraints.append({"type": "new()", "value": None})
                elif constraint == "notnull":
                    constraints.append({"type": "notnull", "value": None})
                elif constraint == "unmanaged":
                    constraints.append({"type": "unmanaged", "value": None})
                else:
                    # Type constraint (interface or base class)
                    constraints.append({"type": "type", "value": constraint})

        return constraints

    def _find_type_end_line(self, content: str, start_pos: int) -> int:
        """Find the end line of a type declaration."""
        # Simple approach: find matching brace or semicolon
        lines = content[start_pos:].split("\n")
        brace_count = 0
        found_opening = False

        for i, line in enumerate(lines):
            if "{" in line:
                found_opening = True
                brace_count += line.count("{")
                brace_count -= line.count("}")
            elif ";" in line and not found_opening:
                return content[:start_pos].count("\n") + i + 1

            if found_opening and brace_count == 0:
                return content[:start_pos].count("\n") + i + 1

        return content[:start_pos].count("\n") + 1

    def _extract_methods(self, content: str) -> List[Dict[str, Any]]:
        """Extract method declarations including async methods."""
        methods = []

        # Pattern for method declarations
        method_pattern = r"""
            (?P<modifiers>(?:public|private|protected|internal|static|virtual|override|abstract|sealed|async|extern|unsafe)\s+)*
            (?P<return_type>[\w\[\]<>,\s]+?)\s+
            (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*
            (?P<generics><[^>]+>)?\s*
            \((?P<parameters>[^)]*)\)\s*
            (?P<constraints>where\s+[^{;]+)?\s*
            [{;]
        """

        for match in re.finditer(method_pattern, content, re.VERBOSE | re.MULTILINE):
            line_number = content[: match.start()].count("\n") + 1

            modifiers = []
            if match.group("modifiers"):
                modifiers = [m.strip() for m in match.group("modifiers").split() if m.strip()]

            is_async = "async" in modifiers
            return_type = match.group("return_type").strip()

            # Parse parameters
            parameters = self._parse_method_parameters(match.group("parameters") or "")

            # Parse generic parameters
            generic_params = []
            if match.group("generics"):
                generic_params = self._parse_generic_parameters(
                    match.group("generics"), match.group("constraints")
                )

            method_info = {
                "name": match.group("name"),
                "return_type": return_type,
                "parameters": parameters,
                "modifiers": modifiers,
                "generic_parameters": generic_params,
                "is_async": is_async,
                "line": line_number,
                "signature": match.group(0).strip(),
            }

            methods.append(method_info)

        return methods

    def _parse_method_parameters(self, params_str: str) -> List[Dict[str, str]]:
        """Parse method parameters."""
        if not params_str.strip():
            return []

        parameters = []
        param_parts = []
        paren_count = 0
        bracket_count = 0
        current_param = ""

        # Handle nested generics in parameters
        for char in params_str:
            if char == "<":
                bracket_count += 1
            elif char == ">":
                bracket_count -= 1
            elif char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
            elif char == "," and bracket_count == 0 and paren_count == 0:
                param_parts.append(current_param.strip())
                current_param = ""
                continue

            current_param += char

        if current_param.strip():
            param_parts.append(current_param.strip())

        for param in param_parts:
            param = param.strip()
            if not param:
                continue

            # Parse parameter attributes, modifiers, type, and name
            parts = param.split()
            param_info = {
                "full": param,
                "modifiers": [],
                "type": "",
                "name": "",
                "default_value": None,
            }

            # Check for default value
            if "=" in param:
                param_part, default_part = param.split("=", 1)
                param_info["default_value"] = default_part.strip()
                param = param_part.strip()
                parts = param.split()

            # Extract modifiers (ref, out, in, params)
            i = 0
            while i < len(parts):
                if parts[i] in ["ref", "out", "in", "params"]:
                    param_info["modifiers"].append(parts[i])
                    i += 1
                else:
                    break

            # Remaining parts are type and name
            if i < len(parts):
                if len(parts) - i >= 2:
                    param_info["type"] = " ".join(parts[i:-1])
                    param_info["name"] = parts[-1]
                elif len(parts) - i == 1:
                    # Only type provided (like in delegates)
                    param_info["type"] = parts[i]

            parameters.append(param_info)

        return parameters

    def _extract_properties(self, content: str) -> List[Dict[str, Any]]:
        """Extract property declarations."""
        properties = []

        # Pattern for property declarations
        property_pattern = r"""
            (?P<modifiers>(?:public|private|protected|internal|static|virtual|override|abstract|sealed)\s+)*
            (?P<type>[\w\[\]<>,\s]+?)\s+
            (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*
            (?P<accessors>\{[^}]*\}|=>|;)
        """

        for match in re.finditer(property_pattern, content, re.VERBOSE | re.MULTILINE):
            line_number = content[: match.start()].count("\n") + 1

            modifiers = []
            if match.group("modifiers"):
                modifiers = [m.strip() for m in match.group("modifiers").split() if m.strip()]

            accessors = match.group("accessors")
            has_getter = "get" in accessors or "=>" in accessors
            has_setter = "set" in accessors
            is_auto_property = "{" in accessors and ("get;" in accessors or "set;" in accessors)

            property_info = {
                "name": match.group("name"),
                "type": match.group("type").strip(),
                "modifiers": modifiers,
                "has_getter": has_getter,
                "has_setter": has_setter,
                "is_auto_property": is_auto_property,
                "line": line_number,
                "signature": match.group(0).strip(),
            }

            properties.append(property_info)

        return properties

    def _extract_fields(self, content: str) -> List[Dict[str, Any]]:
        """Extract field declarations."""
        fields = []

        # Pattern for field declarations
        field_pattern = r"""
            (?P<modifiers>(?:public|private|protected|internal|static|readonly|const|volatile)\s+)*
            (?P<type>[\w\[\]<>,\s]+?)\s+
            (?P<names>[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)\s*
            (?P<initializer>=\s*[^;]+)?\s*;
        """

        for match in re.finditer(field_pattern, content, re.VERBOSE | re.MULTILINE):
            line_number = content[: match.start()].count("\n") + 1

            modifiers = []
            if match.group("modifiers"):
                modifiers = [m.strip() for m in match.group("modifiers").split() if m.strip()]

            # Handle multiple field names
            field_names = [name.strip() for name in match.group("names").split(",")]

            for field_name in field_names:
                field_info = {
                    "name": field_name,
                    "type": match.group("type").strip(),
                    "modifiers": modifiers,
                    "has_initializer": match.group("initializer") is not None,
                    "line": line_number,
                    "signature": f"{' '.join(modifiers)} {match.group('type').strip()} {field_name};",
                }

                fields.append(field_info)

        return fields

    def _extract_events(self, content: str) -> List[Dict[str, Any]]:
        """Extract event declarations."""
        events = []

        # Pattern for event declarations
        event_pattern = r"""
            (?P<modifiers>(?:public|private|protected|internal|static|virtual|override|abstract|sealed)\s+)*
            event\s+
            (?P<type>[\w\[\]<>,\s]+?)\s+
            (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*
            (?P<accessors>\{[^}]*\}|;)
        """

        for match in re.finditer(event_pattern, content, re.VERBOSE | re.MULTILINE):
            line_number = content[: match.start()].count("\n") + 1

            modifiers = []
            if match.group("modifiers"):
                modifiers = [m.strip() for m in match.group("modifiers").split() if m.strip()]

            event_info = {
                "name": match.group("name"),
                "type": match.group("type").strip(),
                "modifiers": modifiers,
                "has_accessors": "{" in match.group("accessors"),
                "line": line_number,
                "signature": match.group(0).strip(),
            }

            events.append(event_info)

        return events

    def _find_generic_types(self, content: str) -> List[Dict[str, Any]]:
        """Find usage of generic types in the code."""
        generic_usages = []

        # Pattern for generic type usage
        generic_pattern = r"(?P<type>[A-Za-z_][A-Za-z0-9_]*)<(?P<args>[^>]+)>"

        for match in re.finditer(generic_pattern, content):
            line_number = content[: match.start()].count("\n") + 1

            type_name = match.group("type")
            type_args = [arg.strip() for arg in match.group("args").split(",")]

            generic_usage = {
                "type": type_name,
                "type_arguments": type_args,
                "line": line_number,
                "usage": match.group(0),
            }

            generic_usages.append(generic_usage)

        return generic_usages

    def _find_async_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Find async/await patterns in the code."""
        async_patterns = []

        # Find async method declarations
        async_method_pattern = r"async\s+[\w<>\[\],\s]+\s+[A-Za-z_][A-Za-z0-9_]*\s*\("
        for match in re.finditer(async_method_pattern, content):
            line_number = content[: match.start()].count("\n") + 1
            async_patterns.append(
                {
                    "type": "async_method",
                    "line": line_number,
                    "pattern": match.group(0).strip(),
                }
            )

        # Find await expressions
        await_pattern = r"await\s+[^;]+"
        for match in re.finditer(await_pattern, content):
            line_number = content[: match.start()].count("\n") + 1
            async_patterns.append(
                {
                    "type": "await_expression",
                    "line": line_number,
                    "pattern": match.group(0).strip(),
                }
            )

        # Find Task/Task<T> usage
        task_pattern = r"Task(?:<[^>]+>)?"
        for match in re.finditer(task_pattern, content):
            line_number = content[: match.start()].count("\n") + 1
            async_patterns.append(
                {
                    "type": "task_usage",
                    "line": line_number,
                    "pattern": match.group(0).strip(),
                }
            )

        return async_patterns

    def _find_linq_queries(self, content: str) -> List[Dict[str, Any]]:
        """Find LINQ query patterns in the code."""
        linq_patterns = []

        # Query syntax patterns
        query_patterns = [
            (r"from\s+\w+\s+in\s+[^;]+", "query_syntax"),
            (r"\.Where\s*\([^)]+\)", "method_syntax_where"),
            (r"\.Select\s*\([^)]+\)", "method_syntax_select"),
            (r"\.OrderBy\s*\([^)]+\)", "method_syntax_orderby"),
            (r"\.GroupBy\s*\([^)]+\)", "method_syntax_groupby"),
            (r"\.Join\s*\([^)]+\)", "method_syntax_join"),
            (r"\.Aggregate\s*\([^)]+\)", "method_syntax_aggregate"),
            (r"\.Any\s*\([^)]*\)", "method_syntax_any"),
            (r"\.All\s*\([^)]*\)", "method_syntax_all"),
            (r"\.First(?:OrDefault)?\s*\([^)]*\)", "method_syntax_first"),
            (r"\.Last(?:OrDefault)?\s*\([^)]*\)", "method_syntax_last"),
            (r"\.Single(?:OrDefault)?\s*\([^)]*\)", "method_syntax_single"),
            (r"\.Count\s*\([^)]*\)", "method_syntax_count"),
            (r"\.Sum\s*\([^)]*\)", "method_syntax_sum"),
            (r"\.Average\s*\([^)]*\)", "method_syntax_average"),
            (r"\.Min\s*\([^)]*\)", "method_syntax_min"),
            (r"\.Max\s*\([^)]*\)", "method_syntax_max"),
        ]

        for pattern, pattern_type in query_patterns:
            for match in re.finditer(pattern, content):
                line_number = content[: match.start()].count("\n") + 1
                linq_patterns.append(
                    {
                        "type": pattern_type,
                        "line": line_number,
                        "pattern": match.group(0).strip(),
                    }
                )

        return linq_patterns

    def get_type_info(self, type_name: str, file_path: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific type."""
        cache_key = f"{file_path}:{type_name}"
        return self.type_cache.get(cache_key)

    def is_generic_type(self, type_name: str) -> bool:
        """Check if a type name represents a generic type."""
        return "<" in type_name and ">" in type_name

    def extract_generic_type_info(self, generic_type: str) -> Dict[str, Any]:
        """Extract information from a generic type string."""
        match = re.match(r"(?P<base>[^<]+)<(?P<args>.+)>", generic_type)
        if match:
            base_type = match.group("base").strip()
            args_str = match.group("args")

            # Parse type arguments (handle nested generics)
            type_args = []
            current_arg = ""
            bracket_count = 0

            for char in args_str:
                if char == "<":
                    bracket_count += 1
                elif char == ">":
                    bracket_count -= 1
                elif char == "," and bracket_count == 0:
                    type_args.append(current_arg.strip())
                    current_arg = ""
                    continue

                current_arg += char

            if current_arg.strip():
                type_args.append(current_arg.strip())

            return {
                "base_type": base_type,
                "type_arguments": type_args,
                "arity": len(type_args),
            }

        return {"base_type": generic_type, "type_arguments": [], "arity": 0}
