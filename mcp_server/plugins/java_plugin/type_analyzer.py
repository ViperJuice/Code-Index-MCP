"""Java type analyzer with generics support."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from mcp_server.plugins.specialized_plugin_base import ITypeAnalyzer, TypeInfo

logger = logging.getLogger(__name__)


@dataclass
class JavaTypeInfo(TypeInfo):
    """Extended type info for Java."""

    access_modifier: str = "public"
    is_static: bool = False
    is_final: bool = False
    is_abstract: bool = False
    implements: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    type_bounds: Dict[str, List[str]] = field(default_factory=dict)  # For generics


class JavaTypeAnalyzer(ITypeAnalyzer):
    """Analyzes Java types, generics, and inheritance."""

    def __init__(self, project_root):
        self.project_root = project_root
        self.type_registry: Dict[str, JavaTypeInfo] = {}
        self.inheritance_graph: Dict[str, Set[str]] = {}
        self.implementation_graph: Dict[str, Set[str]] = {}
        self.generic_definitions: Dict[str, Dict[str, Any]] = {}

        # Primitive types and common Java types
        self.primitive_types = {
            "boolean",
            "byte",
            "char",
            "short",
            "int",
            "long",
            "float",
            "double",
            "void",
        }
        self.common_types = {
            "String",
            "Object",
            "Integer",
            "Long",
            "Double",
            "Float",
            "Boolean",
            "Character",
            "Byte",
            "Short",
            "List",
            "Set",
            "Map",
            "Collection",
            "ArrayList",
            "HashSet",
            "HashMap",
            "LinkedList",
            "TreeSet",
            "TreeMap",
        }

    def analyze_file(self, file_path: str, content: str):
        """Analyze types in a Java file."""
        import javalang

        try:
            tree = javalang.parse.parse(content)
            package = tree.package.name if tree.package else ""

            # Analyze classes
            for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
                self._analyze_class(class_node, package, file_path)

            # Analyze interfaces
            for _, interface_node in tree.filter(javalang.tree.InterfaceDeclaration):
                self._analyze_interface(interface_node, package, file_path)

            # Analyze enums
            for _, enum_node in tree.filter(javalang.tree.EnumDeclaration):
                self._analyze_enum(enum_node, package, file_path)

        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
            # Fallback to regex-based analysis
            self._analyze_with_regex(content, file_path)

    def _analyze_class(self, class_node, package: str, file_path: str):
        """Analyze a class declaration."""

        full_name = f"{package}.{class_node.name}" if package else class_node.name

        # Extract modifiers
        modifiers = class_node.modifiers or []
        is_abstract = "abstract" in modifiers
        is_final = "final" in modifiers
        is_static = "static" in modifiers
        access = self._get_access_modifier(modifiers)

        # Extract generics
        generic_params = []
        type_bounds = {}
        if class_node.type_parameters:
            for param in class_node.type_parameters:
                generic_params.append(param.name)
                if param.extends:
                    bounds = []
                    for bound in param.extends:
                        bounds.append(self._type_to_string(bound))
                    type_bounds[param.name] = bounds

        # Extract superclass
        super_types = []
        if class_node.extends:
            super_type = self._type_to_string(class_node.extends)
            super_types.append(super_type)

            # Update inheritance graph
            if full_name not in self.inheritance_graph:
                self.inheritance_graph[full_name] = set()
            self.inheritance_graph[full_name].add(super_type)

        # Extract interfaces
        implements = []
        if class_node.implements:
            for interface in class_node.implements:
                interface_name = self._type_to_string(interface)
                implements.append(interface_name)

                # Update implementation graph
                if interface_name not in self.implementation_graph:
                    self.implementation_graph[interface_name] = set()
                self.implementation_graph[interface_name].add(full_name)

        # Extract annotations
        annotations = []
        if class_node.annotations:
            for annotation in class_node.annotations:
                annotations.append(annotation.name)

        # Create type info
        type_info = JavaTypeInfo(
            type_name=full_name,
            is_generic=bool(generic_params),
            generic_params=generic_params,
            is_interface=False,
            super_types=super_types,
            access_modifier=access,
            is_static=is_static,
            is_final=is_final,
            is_abstract=is_abstract,
            implements=implements,
            annotations=annotations,
            type_bounds=type_bounds,
        )

        self.type_registry[full_name] = type_info
        self.type_registry[class_node.name] = type_info  # Also store by simple name

    def _analyze_interface(self, interface_node, package: str, file_path: str):
        """Analyze an interface declaration."""
        full_name = f"{package}.{interface_node.name}" if package else interface_node.name

        # Extract modifiers
        modifiers = interface_node.modifiers or []
        access = self._get_access_modifier(modifiers)

        # Extract generics
        generic_params = []
        type_bounds = {}
        if interface_node.type_parameters:
            for param in interface_node.type_parameters:
                generic_params.append(param.name)
                if hasattr(param, "extends") and param.extends:
                    bounds = []
                    for bound in param.extends:
                        bounds.append(self._type_to_string(bound))
                    type_bounds[param.name] = bounds

        # Extract extended interfaces
        super_types = []
        if interface_node.extends:
            for extended in interface_node.extends:
                super_type = self._type_to_string(extended)
                super_types.append(super_type)

        # Create type info
        type_info = JavaTypeInfo(
            type_name=full_name,
            is_generic=bool(generic_params),
            generic_params=generic_params,
            is_interface=True,
            super_types=super_types,
            access_modifier=access,
            type_bounds=type_bounds,
        )

        self.type_registry[full_name] = type_info
        self.type_registry[interface_node.name] = type_info

    def _analyze_enum(self, enum_node, package: str, file_path: str):
        """Analyze an enum declaration."""
        full_name = f"{package}.{enum_node.name}" if package else enum_node.name

        # Enums are final by default
        type_info = JavaTypeInfo(type_name=full_name, is_final=True, super_types=["java.lang.Enum"])

        self.type_registry[full_name] = type_info
        self.type_registry[enum_node.name] = type_info

    def _get_access_modifier(self, modifiers: List[str]) -> str:
        """Extract access modifier from modifiers list."""
        for mod in ["public", "protected", "private"]:
            if mod in modifiers:
                return mod
        return "package"  # Default package-private

    def _type_to_string(self, type_obj) -> str:
        """Convert a javalang type object to string."""
        if hasattr(type_obj, "name"):
            base_type = type_obj.name

            # Handle generic arguments
            if hasattr(type_obj, "arguments") and type_obj.arguments:
                args = []
                for arg in type_obj.arguments:
                    args.append(self._type_to_string(arg))
                base_type += f"<{', '.join(args)}>"

            # Handle array dimensions
            if hasattr(type_obj, "dimensions") and type_obj.dimensions:
                base_type += "[]" * len(type_obj.dimensions)

            return base_type

        return str(type_obj)

    def _analyze_with_regex(self, content: str, file_path: str):
        """Fallback regex-based analysis."""
        # Extract package
        package_match = re.search(r"package\s+([\w.]+)\s*;", content)
        package = package_match.group(1) if package_match else ""

        # Find class declarations
        class_pattern = r"(public|private|protected)?\s*(static)?\s*(final)?\s*(abstract)?\s*class\s+(\w+)(?:<([^>]+)>)?\s*(?:extends\s+([\w.<>,\s]+))?\s*(?:implements\s+([\w.<>,\s]+))?"

        for match in re.finditer(class_pattern, content):
            access = match.group(1) or "package"
            is_static = bool(match.group(2))
            is_final = bool(match.group(3))
            is_abstract = bool(match.group(4))
            class_name = match.group(5)
            generics = match.group(6)
            extends = match.group(7)
            implements = match.group(8)

            full_name = f"{package}.{class_name}" if package else class_name

            type_info = JavaTypeInfo(
                type_name=full_name,
                is_generic=bool(generics),
                generic_params=generics.split(",") if generics else [],
                super_types=[extends.strip()] if extends else [],
                access_modifier=access,
                is_static=is_static,
                is_final=is_final,
                is_abstract=is_abstract,
                implements=implements.split(",") if implements else [],
            )

            self.type_registry[full_name] = type_info
            self.type_registry[class_name] = type_info

    def get_type_info(self, symbol: str, file_path: str) -> Optional[TypeInfo]:
        """Get type information for a symbol."""
        # Direct lookup
        if symbol in self.type_registry:
            return self.type_registry[symbol]

        # Try with common prefixes
        for prefix in ["java.lang", "java.util", "java.io"]:
            full_name = f"{prefix}.{symbol}"
            if full_name in self.type_registry:
                return self.type_registry[full_name]

        # Check if it's a primitive or common type
        if symbol in self.primitive_types:
            return JavaTypeInfo(type_name=symbol, is_final=True)

        if symbol in self.common_types:
            return JavaTypeInfo(
                type_name=symbol,
                is_generic=symbol in {"List", "Set", "Map", "Collection"},
                generic_params=(
                    ["T"]
                    if symbol in {"List", "Set", "Collection"}
                    else ["K", "V"] if symbol == "Map" else []
                ),
            )

        return None

    def find_implementations(self, interface_name: str) -> List[Tuple[str, str]]:
        """Find all implementations of an interface."""
        implementations = []

        if interface_name in self.implementation_graph:
            for impl_class in self.implementation_graph[interface_name]:
                # Find file path for implementation
                # This is simplified - in real implementation would need file tracking
                implementations.append((impl_class, "unknown"))

        return implementations

    def resolve_generic_type(self, type_expr: str, context: Dict[str, str]) -> str:
        """Resolve a generic type expression in context."""
        # Simple implementation - replace type parameters with concrete types
        resolved = type_expr

        for param, concrete_type in context.items():
            resolved = resolved.replace(param, concrete_type)

        return resolved

    def get_inheritance_hierarchy(self, class_name: str) -> List[str]:
        """Get the full inheritance hierarchy for a class."""
        hierarchy = []
        visited = set()

        def traverse(name: str):
            if name in visited or name not in self.type_registry:
                return

            visited.add(name)
            type_info = self.type_registry[name]

            hierarchy.append(name)

            for super_type in type_info.super_types:
                traverse(super_type)

        traverse(class_name)
        return hierarchy

    def is_subtype_of(self, subtype: str, supertype: str) -> bool:
        """Check if one type is a subtype of another."""
        if subtype == supertype:
            return True

        if subtype not in self.type_registry:
            return False

        type_info = self.type_registry[subtype]

        # Check direct supertypes
        if supertype in type_info.super_types:
            return True

        # Check interfaces
        if supertype in type_info.implements:
            return True

        # Check transitively
        for parent in type_info.super_types:
            if self.is_subtype_of(parent, supertype):
                return True

        return False
