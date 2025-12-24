"""Go package analyzer for tracking imports and internal structure."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PackageInfo:
    """Information about a Go package."""

    name: str
    path: Path
    imports: Set[str] = field(default_factory=set)
    files: List[Path] = field(default_factory=list)
    types: Dict[str, "TypeInfo"] = field(default_factory=dict)
    functions: Dict[str, "FunctionInfo"] = field(default_factory=dict)
    interfaces: Dict[str, "InterfaceInfo"] = field(default_factory=dict)
    constants: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, str] = field(default_factory=dict)


@dataclass
class TypeInfo:
    """Information about a Go type."""

    name: str
    kind: str  # struct, interface, alias, etc.
    file: Path
    line: int
    fields: Dict[str, str] = field(default_factory=dict)  # field_name -> type
    methods: List[str] = field(default_factory=list)
    embedded: List[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    """Information about a Go function."""

    name: str
    signature: str
    file: Path
    line: int
    receiver: Optional[str] = None
    params: List[Tuple[str, str]] = field(default_factory=list)  # [(name, type), ...]
    returns: List[str] = field(default_factory=list)
    is_exported: bool = False


@dataclass
class InterfaceInfo:
    """Information about a Go interface."""

    name: str
    file: Path
    line: int
    methods: Dict[str, str] = field(default_factory=dict)  # method_name -> signature
    embedded: List[str] = field(default_factory=list)


class GoPackageAnalyzer:
    """Analyzes Go packages and tracks their structure."""

    def __init__(self, module_resolver):
        self.module_resolver = module_resolver
        self.packages: Dict[str, PackageInfo] = {}
        self._import_pattern = re.compile(r'import\s+(?:\(\s*((?:[^)]+))\s*\)|"([^"]+)")')
        self._package_pattern = re.compile(r"^\s*package\s+(\w+)")
        self._type_pattern = re.compile(r"type\s+(\w+)\s+(?:struct|interface|\w+)")
        self._func_pattern = re.compile(
            r"func\s+(?:\(([^)]+)\)\s+)?(\w+)\s*\(([^)]*)\)(?:\s*\(([^)]*)\))?(?:\s+([^{]+))?"
        )

    def analyze_package(self, package_path: Path) -> Optional[PackageInfo]:
        """Analyze a Go package directory."""
        if not package_path.exists() or not package_path.is_dir():
            return None

        # Get all Go files in the package
        go_files = [f for f in package_path.glob("*.go") if not f.name.endswith("_test.go")]

        if not go_files:
            return None

        # Determine package name from first file
        package_name = None
        for go_file in go_files:
            try:
                content = go_file.read_text()
                match = self._package_pattern.search(content)
                if match:
                    package_name = match.group(1)
                    break
            except Exception as e:
                logger.error(f"Failed to read {go_file}: {e}")

        if not package_name:
            return None

        # Create package info
        package_info = PackageInfo(name=package_name, path=package_path)
        package_info.files = go_files

        # Analyze each file
        for go_file in go_files:
            self._analyze_file(go_file, package_info)

        # Cache the package
        self.packages[str(package_path)] = package_info
        return package_info

    def _analyze_file(self, file_path: Path, package_info: PackageInfo):
        """Analyze a single Go file."""
        try:
            content = file_path.read_text()
            lines = content.split("\n")

            # Extract imports
            imports = self._extract_imports(content)
            package_info.imports.update(imports)

            # Extract types, functions, etc.
            self._extract_declarations(file_path, lines, package_info)

        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {e}")

    def _extract_imports(self, content: str) -> Set[str]:
        """Extract import statements from Go source."""
        imports = set()

        # Single imports
        for match in re.finditer(r'import\s+"([^"]+)"', content):
            imports.add(match.group(1))

        # Grouped imports
        import_block_match = re.search(r"import\s*\(((?:[^)]|\n)+)\)", content, re.MULTILINE)
        if import_block_match:
            import_block = import_block_match.group(1)
            for line in import_block.split("\n"):
                line = line.strip()
                if line and not line.startswith("//"):
                    # Handle aliased imports
                    if '"' in line:
                        import_match = re.search(r'"([^"]+)"', line)
                        if import_match:
                            imports.add(import_match.group(1))

        return imports

    def _extract_declarations(self, file_path: Path, lines: List[str], package_info: PackageInfo):
        """Extract type and function declarations."""
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip comments and empty lines
            if not line or line.startswith("//"):
                i += 1
                continue

            # Type declarations
            if line.startswith("type "):
                self._parse_type_declaration(file_path, lines, i, package_info)

            # Function declarations
            elif line.startswith("func "):
                self._parse_function_declaration(file_path, lines, i, package_info)

            # Const declarations
            elif line.startswith("const "):
                self._parse_const_declaration(lines, i, package_info)

            # Var declarations
            elif line.startswith("var "):
                self._parse_var_declaration(lines, i, package_info)

            i += 1

    def _parse_type_declaration(
        self,
        file_path: Path,
        lines: List[str],
        start_line: int,
        package_info: PackageInfo,
    ):
        """Parse a type declaration."""
        line = lines[start_line].strip()

        # Type alias or simple type
        type_match = re.match(r"type\s+(\w+)\s+(\w+)", line)
        if type_match and "struct" not in line and "interface" not in line:
            type_name = type_match.group(1)
            _ = type_match.group(2)
            type_info = TypeInfo(name=type_name, kind="alias", file=file_path, line=start_line + 1)
            package_info.types[type_name] = type_info
            return

        # Struct type
        if "struct" in line:
            struct_match = re.match(r"type\s+(\w+)\s+struct\s*{?", line)
            if struct_match:
                type_name = struct_match.group(1)
                type_info = TypeInfo(
                    name=type_name, kind="struct", file=file_path, line=start_line + 1
                )

                # Parse struct fields
                if "{" in line:
                    self._parse_struct_fields(lines, start_line, type_info)

                package_info.types[type_name] = type_info

        # Interface type
        elif "interface" in line:
            interface_match = re.match(r"type\s+(\w+)\s+interface\s*{?", line)
            if interface_match:
                interface_name = interface_match.group(1)
                interface_info = InterfaceInfo(
                    name=interface_name, file=file_path, line=start_line + 1
                )

                # Parse interface methods
                if "{" in line:
                    self._parse_interface_methods(lines, start_line, interface_info)

                package_info.interfaces[interface_name] = interface_info

    def _parse_struct_fields(self, lines: List[str], start_line: int, type_info: TypeInfo):
        """Parse struct fields."""
        i = start_line
        brace_count = lines[i].count("{") - lines[i].count("}")
        i += 1

        while i < len(lines) and brace_count > 0:
            line = lines[i].strip()
            brace_count += line.count("{") - line.count("}")

            if line and not line.startswith("//") and not line == "}":
                # Parse field
                field_match = re.match(r"(\w+)\s+(.+?)(?:\s+`[^`]+`)?$", line)
                if field_match:
                    field_name = field_match.group(1)
                    field_type = field_match.group(2).strip()
                    type_info.fields[field_name] = field_type
                elif not line.startswith("}"):
                    # Might be an embedded field
                    embedded_match = re.match(r"^\*?(\w+)", line)
                    if embedded_match:
                        type_info.embedded.append(embedded_match.group(1))

            i += 1

    def _parse_interface_methods(
        self, lines: List[str], start_line: int, interface_info: InterfaceInfo
    ):
        """Parse interface methods."""
        i = start_line
        brace_count = lines[i].count("{") - lines[i].count("}")
        i += 1

        while i < len(lines) and brace_count > 0:
            line = lines[i].strip()
            brace_count += line.count("{") - line.count("}")

            if line and not line.startswith("//") and not line == "}":
                # Parse method signature
                method_match = re.match(r"(\w+)\s*\(([^)]*)\)(?:\s*\(([^)]*)\))?(?:\s+(.+))?", line)
                if method_match:
                    method_name = method_match.group(1)
                    params = method_match.group(2) or ""
                    returns = method_match.group(3) or method_match.group(4) or ""
                    signature = f"{method_name}({params})"
                    if returns:
                        signature += f" {returns}"
                    interface_info.methods[method_name] = signature
                elif not line.startswith("}"):
                    # Might be an embedded interface
                    embedded_match = re.match(r"^\w+$", line)
                    if embedded_match:
                        interface_info.embedded.append(line)

            i += 1

    def _parse_function_declaration(
        self,
        file_path: Path,
        lines: List[str],
        start_line: int,
        package_info: PackageInfo,
    ):
        """Parse a function declaration."""
        line = lines[start_line].strip()

        # Match function signature
        func_match = self._func_pattern.match(line)
        if func_match:
            receiver = func_match.group(1)
            func_name = func_match.group(2)
            params = func_match.group(3) or ""
            returns1 = func_match.group(4) or ""
            returns2 = func_match.group(5) or ""

            # Build signature
            signature = "func "
            if receiver:
                signature += f"({receiver}) "
            signature += f"{func_name}({params})"
            if returns1:
                signature += f" ({returns1})"
            elif returns2:
                signature += f" {returns2}"

            func_info = FunctionInfo(
                name=func_name,
                signature=signature,
                file=file_path,
                line=start_line + 1,
                receiver=receiver,
                is_exported=func_name[0].isupper() if func_name else False,
            )

            # Parse parameters
            if params:
                func_info.params = self._parse_params(params)

            # Parse returns
            if returns1 or returns2:
                func_info.returns = self._parse_returns(returns1 or returns2)

            # Add to appropriate collection
            if receiver:
                # It's a method, extract receiver type
                receiver_type = self._extract_receiver_type(receiver)
                if receiver_type and receiver_type in package_info.types:
                    package_info.types[receiver_type].methods.append(func_name)
            else:
                # Regular function
                package_info.functions[func_name] = func_info

    def _parse_params(self, params_str: str) -> List[Tuple[str, str]]:
        """Parse function parameters."""
        params = []
        # Simple parsing - doesn't handle all edge cases
        parts = params_str.split(",")
        for part in parts:
            part = part.strip()
            if part:
                # Try to split name and type
                tokens = part.split()
                if len(tokens) >= 2:
                    params.append((tokens[0], " ".join(tokens[1:])))
                elif tokens:
                    params.append(("", tokens[0]))
        return params

    def _parse_returns(self, returns_str: str) -> List[str]:
        """Parse function return types."""
        returns_str = returns_str.strip()
        if returns_str.startswith("(") and returns_str.endswith(")"):
            returns_str = returns_str[1:-1]
        return [r.strip() for r in returns_str.split(",") if r.strip()]

    def _extract_receiver_type(self, receiver: str) -> Optional[str]:
        """Extract type name from receiver."""
        # Remove pointer if present
        receiver = receiver.replace("*", "").strip()
        # Extract type name
        tokens = receiver.split()
        if len(tokens) >= 2:
            return tokens[1]
        return None

    def _parse_const_declaration(
        self, lines: List[str], start_line: int, package_info: PackageInfo
    ):
        """Parse const declarations."""
        line = lines[start_line].strip()

        # Single const
        const_match = re.match(r"const\s+(\w+)(?:\s+\w+)?\s*=\s*(.+)", line)
        if const_match:
            const_name = const_match.group(1)
            const_value = const_match.group(2)
            package_info.constants[const_name] = const_value

    def _parse_var_declaration(self, lines: List[str], start_line: int, package_info: PackageInfo):
        """Parse var declarations."""
        line = lines[start_line].strip()

        # Single var
        var_match = re.match(r"var\s+(\w+)(?:\s+(\w+))?\s*(?:=\s*(.+))?", line)
        if var_match:
            var_name = var_match.group(1)
            var_type = var_match.group(2) or "unknown"
            package_info.variables[var_name] = var_type

    def get_package_exports(self, package_info: PackageInfo) -> Dict[str, str]:
        """Get all exported symbols from a package."""
        exports = {}

        # Exported types
        for type_name, type_info in package_info.types.items():
            if type_name[0].isupper():
                exports[type_name] = f"type:{type_info.kind}"

        # Exported functions
        for func_name, func_info in package_info.functions.items():
            if func_name[0].isupper():
                exports[func_name] = f"func:{func_info.signature}"

        # Exported constants
        for const_name in package_info.constants:
            if const_name[0].isupper():
                exports[const_name] = "const"

        # Exported variables
        for var_name in package_info.variables:
            if var_name[0].isupper():
                exports[var_name] = "var"

        # Exported interfaces
        for interface_name in package_info.interfaces:
            if interface_name[0].isupper():
                exports[interface_name] = "interface"

        return exports
