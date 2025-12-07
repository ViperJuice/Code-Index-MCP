"""Java import resolver for resolving package imports and dependencies."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from mcp_server.plugins.specialized_plugin_base import IImportResolver, ImportInfo

logger = logging.getLogger(__name__)


@dataclass
class JavaImportInfo(ImportInfo):
    """Extended import info for Java."""

    is_static: bool = False
    is_wildcard: bool = False
    package_path: List[str] = field(default_factory=list)


class JavaImportResolver(IImportResolver):
    """Resolves Java imports and tracks dependencies."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.import_graph: Dict[str, Set[str]] = {}
        self.package_to_file: Dict[str, Path] = {}
        self.class_to_package: Dict[str, str] = {}

        # Standard Java source directories
        self.source_dirs = ["src/main/java", "src/test/java", "src", "test", "tests"]

        # Build dependency cache
        self._external_packages: Set[str] = set()
        self._scan_project_structure()

    def _scan_project_structure(self):
        """Scan project to build package and class mappings."""
        for src_dir in self.source_dirs:
            src_path = self.project_root / src_dir
            if src_path.exists():
                self._scan_directory(src_path, src_path)

    def _scan_directory(self, directory: Path, src_root: Path):
        """Recursively scan directory for Java files."""
        for java_file in directory.rglob("*.java"):
            relative_path = java_file.relative_to(src_root)
            _ = list(relative_path.parts[:-1])

            # Extract package from file
            try:
                content = java_file.read_text(encoding="utf-8")
                package = self._extract_package(content)
                if package:
                    self.package_to_file[package] = java_file

                    # Extract class names
                    classes = self._extract_class_names(content)
                    for class_name in classes:
                        full_name = f"{package}.{class_name}" if package else class_name
                        self.class_to_package[class_name] = package
                        self.class_to_package[full_name] = package

            except Exception as e:
                logger.warning(f"Failed to scan {java_file}: {e}")

    def _extract_package(self, content: str) -> Optional[str]:
        """Extract package declaration from Java source."""
        import javalang

        try:
            tree = javalang.parse.parse(content)
            if tree.package:
                return tree.package.name
        except Exception:
            # Fallback to regex
            import re

            match = re.search(r"^\s*package\s+([\w.]+)\s*;", content, re.MULTILINE)
            if match:
                return match.group(1)
        return None

    def _extract_class_names(self, content: str) -> List[str]:
        """Extract all class/interface names from Java source."""
        import javalang

        classes = []
        try:
            tree = javalang.parse.parse(content)
            for _, node in tree.filter(javalang.tree.ClassDeclaration):
                classes.append(node.name)
            for _, node in tree.filter(javalang.tree.InterfaceDeclaration):
                classes.append(node.name)
            for _, node in tree.filter(javalang.tree.EnumDeclaration):
                classes.append(node.name)
        except Exception:
            # Fallback to regex
            import re

            # Match public/private/protected class/interface/enum declarations
            pattern = r"(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(?:abstract)?\s*(?:class|interface|enum)\s+(\w+)"
            matches = re.findall(pattern, content)
            classes.extend(matches)

        return classes

    def resolve_import(self, import_info: ImportInfo, current_file: Path) -> Optional[Path]:
        """Resolve a Java import to its file path."""
        if isinstance(import_info, JavaImportInfo):
            return self._resolve_java_import(import_info)

        # Handle simple import path
        import_path = import_info.module_path

        # Check if it's a class import (ends with uppercase letter typically)
        parts = import_path.split(".")
        if parts and parts[-1][0].isupper():
            # Class import - check our mappings
            if import_path in self.class_to_package:
                package = self.class_to_package[import_path]
                if package in self.package_to_file:
                    return self.package_to_file[package]
        else:
            # Package import - check if we have files in this package
            if import_path in self.package_to_file:
                return self.package_to_file[import_path]

        # Try to find in project structure
        return self._find_in_source_dirs(import_path)

    def _resolve_java_import(self, import_info: JavaImportInfo) -> Optional[Path]:
        """Resolve a Java-specific import."""
        if import_info.is_wildcard:
            # For wildcard imports, return the package directory
            package_path = import_info.module_path
            if package_path in self.package_to_file:
                return self.package_to_file[package_path].parent

        return self.resolve_import(import_info, Path())

    def _find_in_source_dirs(self, import_path: str) -> Optional[Path]:
        """Try to find import in source directories."""
        # Convert import path to file path
        path_parts = import_path.split(".")

        for src_dir in self.source_dirs:
            src_path = self.project_root / src_dir
            if src_path.exists():
                # Try as a class file
                class_file = src_path / Path(*path_parts[:-1]) / f"{path_parts[-1]}.java"
                if class_file.exists():
                    return class_file

                # Try as a package directory
                package_dir = src_path / Path(*path_parts)
                if package_dir.exists() and package_dir.is_dir():
                    # Return first Java file in package
                    for java_file in package_dir.glob("*.java"):
                        return java_file

        return None

    def get_import_graph(self) -> Dict[str, Set[str]]:
        """Get the complete import dependency graph."""
        return self.import_graph.copy()

    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.import_graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for node in self.import_graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def add_import(self, from_file: str, import_info: JavaImportInfo):
        """Add an import to the graph."""
        if from_file not in self.import_graph:
            self.import_graph[from_file] = set()

        # Resolve the import
        resolved = self.resolve_import(import_info, Path(from_file))
        if resolved:
            self.import_graph[from_file].add(str(resolved))
            import_info.resolved_path = str(resolved)

    def parse_import_statement(self, import_line: str) -> Optional[JavaImportInfo]:
        """Parse a Java import statement."""
        import re

        # Match: import [static] package.path[.*];
        pattern = r"import\s+(static\s+)?([\w.]+)(\.\*)?\s*;"
        match = re.match(pattern, import_line.strip())

        if match:
            is_static = bool(match.group(1))
            import_path = match.group(2)
            is_wildcard = bool(match.group(3))

            return JavaImportInfo(
                module_path=import_path,
                is_static=is_static,
                is_wildcard=is_wildcard,
                package_path=import_path.split("."),
            )

        return None
