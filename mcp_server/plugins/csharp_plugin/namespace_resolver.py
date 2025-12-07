"""Namespace resolution utilities for C# code analysis."""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class NamespaceResolver:
    """Resolves C# namespaces, using statements, and assembly references."""

    def __init__(self):
        """Initialize the namespace resolver."""
        self.namespace_cache: Dict[str, Dict[str, str]] = {}
        self.assembly_cache: Dict[str, Set[str]] = {}
        self.project_references: Dict[str, List[str]] = {}

    def analyze_file(self, file_path: str, content: str) -> Dict[str, any]:
        """Analyze a C# file for namespace and using information.

        Args:
            file_path: Path to the C# file
            content: File content

        Returns:
            Dictionary containing namespace analysis results
        """
        analysis = {
            "file_path": file_path,
            "namespace": None,
            "using_statements": [],
            "using_aliases": {},
            "using_static": [],
            "global_using": [],
            "types_declared": [],
            "nested_namespaces": [],
        }

        try:
            # Extract namespace declaration
            analysis["namespace"] = self._extract_namespace(content)

            # Extract using statements
            analysis["using_statements"] = self._extract_using_statements(content)

            # Extract using aliases
            analysis["using_aliases"] = self._extract_using_aliases(content)

            # Extract using static
            analysis["using_static"] = self._extract_using_static(content)

            # Extract global using statements
            analysis["global_using"] = self._extract_global_using(content)

            # Extract declared types
            analysis["types_declared"] = self._extract_declared_types(content)

            # Extract nested namespaces
            analysis["nested_namespaces"] = self._extract_nested_namespaces(content)

            # Cache the namespace info
            if analysis["namespace"]:
                self.namespace_cache[file_path] = {
                    "namespace": analysis["namespace"],
                    "using_statements": analysis["using_statements"],
                    "using_aliases": analysis["using_aliases"],
                }

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")

        return analysis

    def _extract_namespace(self, content: str) -> Optional[str]:
        """Extract the primary namespace declaration."""
        # Match both traditional and file-scoped namespaces
        patterns = [
            r"namespace\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*[{;]",
            r"namespace\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*$",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_using_statements(self, content: str) -> List[str]:
        """Extract using statements (excluding aliases and static)."""
        using_statements = []

        # Pattern for regular using statements
        pattern = r"(?:global\s+)?using\s+(?!static\s)([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*;"

        matches = re.findall(pattern, content, re.MULTILINE)
        for match in matches:
            if "=" not in match:  # Exclude aliases
                using_statements.append(match.strip())

        return using_statements

    def _extract_using_aliases(self, content: str) -> Dict[str, str]:
        """Extract using alias statements."""
        aliases = {}

        # Pattern for using aliases
        pattern = r"(?:global\s+)?using\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+)\s*;"

        matches = re.findall(pattern, content, re.MULTILINE)
        for alias, target in matches:
            aliases[alias.strip()] = target.strip()

        return aliases

    def _extract_using_static(self, content: str) -> List[str]:
        """Extract using static statements."""
        using_static = []

        # Pattern for using static statements
        pattern = r"(?:global\s+)?using\s+static\s+([^;]+)\s*;"

        matches = re.findall(pattern, content, re.MULTILINE)
        for match in matches:
            using_static.append(match.strip())

        return using_static

    def _extract_global_using(self, content: str) -> List[str]:
        """Extract global using statements."""
        global_using = []

        # Pattern for global using statements
        pattern = r"global\s+using\s+(?!static\s)([^=][^;]*)\s*;"

        matches = re.findall(pattern, content, re.MULTILINE)
        for match in matches:
            if "=" not in match:
                global_using.append(match.strip())

        return global_using

    def _extract_declared_types(self, content: str) -> List[Dict[str, any]]:
        """Extract type declarations (classes, interfaces, structs, enums, etc.)."""
        types = []

        # Patterns for different type declarations
        patterns = [
            (
                r"(?:public|private|protected|internal|static|abstract|sealed|partial)?\s*class\s+([A-Za-z_][A-Za-z0-9_]*)",
                "class",
            ),
            (
                r"(?:public|private|protected|internal|static|abstract|sealed|partial)?\s*interface\s+([A-Za-z_][A-Za-z0-9_]*)",
                "interface",
            ),
            (
                r"(?:public|private|protected|internal|static|partial)?\s*struct\s+([A-Za-z_][A-Za-z0-9_]*)",
                "struct",
            ),
            (
                r"(?:public|private|protected|internal|static)?\s*enum\s+([A-Za-z_][A-Za-z0-9_]*)",
                "enum",
            ),
            (
                r"(?:public|private|protected|internal|static)?\s*delegate\s+[^(]+\s+([A-Za-z_][A-Za-z0-9_]*)",
                "delegate",
            ),
            (
                r"(?:public|private|protected|internal|static|partial)?\s*record\s+([A-Za-z_][A-Za-z0-9_]*)",
                "record",
            ),
        ]

        for pattern, type_kind in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                type_name = match.group(1)
                line_number = content[: match.start()].count("\n") + 1

                types.append(
                    {
                        "name": type_name,
                        "kind": type_kind,
                        "line": line_number,
                        "full_match": match.group(0).strip(),
                    }
                )

        return types

    def _extract_nested_namespaces(self, content: str) -> List[str]:
        """Extract nested namespace declarations."""
        nested_namespaces = []

        # Find all namespace declarations
        pattern = r"namespace\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"

        matches = re.findall(pattern, content, re.MULTILINE)
        for match in matches:
            nested_namespaces.append(match.strip())

        return list(set(nested_namespaces))  # Remove duplicates

    def resolve_type(self, type_name: str, file_path: str) -> Optional[Dict[str, any]]:
        """Resolve a type name to its full namespace and assembly.

        Args:
            type_name: The type name to resolve
            file_path: The file where the type is referenced

        Returns:
            Dictionary with resolution information or None if not found
        """
        if file_path not in self.namespace_cache:
            return None

        file_info = self.namespace_cache[file_path]

        # Check if it's a simple name that might be in current namespace
        if "." not in type_name:
            # Check current namespace
            current_namespace = file_info["namespace"]
            if current_namespace:
                full_type = f"{current_namespace}.{type_name}"
                return {
                    "type_name": type_name,
                    "full_name": full_type,
                    "namespace": current_namespace,
                    "assembly": None,  # Would need assembly analysis
                }

        # Check using statements
        for using_ns in file_info["using_statements"]:
            potential_full_name = f"{using_ns}.{type_name}"
            # In a real implementation, you'd check if this type exists
            return {
                "type_name": type_name,
                "full_name": potential_full_name,
                "namespace": using_ns,
                "assembly": None,
            }

        # Check aliases
        if type_name in file_info["using_aliases"]:
            alias_target = file_info["using_aliases"][type_name]
            return {
                "type_name": type_name,
                "full_name": alias_target,
                "namespace": None,  # Alias might be to a full name
                "assembly": None,
                "is_alias": True,
            }

        return None

    def analyze_project_file(self, project_path: str) -> Dict[str, any]:
        """Analyze a .csproj file for references and dependencies.

        Args:
            project_path: Path to the .csproj file

        Returns:
            Dictionary containing project analysis results
        """
        analysis = {
            "project_path": project_path,
            "target_framework": None,
            "package_references": [],
            "project_references": [],
            "assembly_references": [],
            "compile_items": [],
            "global_usings": [],
        }

        try:
            tree = ET.parse(project_path)
            root = tree.getroot()

            # Extract target framework
            target_framework = root.find(".//TargetFramework")
            if target_framework is not None:
                analysis["target_framework"] = target_framework.text

            # Extract package references
            for package_ref in root.findall(".//PackageReference"):
                include = package_ref.get("Include")
                version = package_ref.get("Version")
                if include:
                    analysis["package_references"].append({"name": include, "version": version})

            # Extract project references
            for proj_ref in root.findall(".//ProjectReference"):
                include = proj_ref.get("Include")
                if include:
                    analysis["project_references"].append(include)

            # Extract assembly references
            for asm_ref in root.findall(".//Reference"):
                include = asm_ref.get("Include")
                if include:
                    analysis["assembly_references"].append(include)

            # Extract compile items
            for compile_item in root.findall(".//Compile"):
                include = compile_item.get("Include")
                if include:
                    analysis["compile_items"].append(include)

            # Extract global usings (newer .NET feature)
            for using_item in root.findall(".//Using"):
                include = using_item.get("Include")
                if include:
                    analysis["global_usings"].append(include)

            # Cache project references
            self.project_references[project_path] = analysis["project_references"]

        except Exception as e:
            logger.error(f"Error analyzing project file {project_path}: {e}")

        return analysis

    def get_namespace_hierarchy(self, namespace: str) -> List[str]:
        """Get the hierarchy of a namespace (parent namespaces).

        Args:
            namespace: The namespace to analyze

        Returns:
            List of namespace parts from root to specific
        """
        if not namespace:
            return []

        parts = namespace.split(".")
        hierarchy = []

        for i in range(len(parts)):
            hierarchy.append(".".join(parts[: i + 1]))

        return hierarchy

    def find_type_in_namespace(self, type_name: str, namespace: str) -> Optional[str]:
        """Find a type within a specific namespace.

        Args:
            type_name: Name of the type to find
            namespace: Namespace to search in

        Returns:
            Full type name if found, None otherwise
        """
        # This would typically query an index or symbol table
        # For now, return a constructed name
        if namespace and type_name:
            return f"{namespace}.{type_name}"
        return type_name if type_name else None

    def get_available_types_in_scope(self, file_path: str) -> List[str]:
        """Get all types available in the scope of a given file.

        Args:
            file_path: Path to the C# file

        Returns:
            List of available type names
        """
        if file_path not in self.namespace_cache:
            return []

        available_types = []
        file_info = self.namespace_cache[file_path]

        # Add types from using statements
        for using_ns in file_info["using_statements"]:
            # This would typically query an assembly/metadata index
            # For now, add common .NET types
            if using_ns == "System":
                available_types.extend(
                    [
                        "String",
                        "Int32",
                        "Boolean",
                        "DateTime",
                        "Guid",
                        "Object",
                        "Exception",
                        "Type",
                        "Array",
                        "List",
                    ]
                )
            elif using_ns == "System.Collections.Generic":
                available_types.extend(
                    [
                        "List<T>",
                        "Dictionary<TKey, TValue>",
                        "IEnumerable<T>",
                        "ICollection<T>",
                        "Queue<T>",
                        "Stack<T>",
                    ]
                )

        # Add aliased types
        available_types.extend(file_info["using_aliases"].keys())

        return available_types
