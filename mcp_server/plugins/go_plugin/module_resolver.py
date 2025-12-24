"""Go module resolver for handling go.mod dependencies."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GoModuleResolver:
    """Handles Go module resolution and dependency tracking."""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.module_cache: Dict[str, GoModule] = {}
        self.go_mod_path = self._find_go_mod()
        self.current_module = self._parse_current_module() if self.go_mod_path else None

    def _find_go_mod(self) -> Optional[Path]:
        """Find the go.mod file in the project."""
        current = self.root_path
        while current != current.parent:
            go_mod = current / "go.mod"
            if go_mod.exists():
                return go_mod
            current = current.parent
        return None

    def _parse_current_module(self) -> Optional["GoModule"]:
        """Parse the current module's go.mod file."""
        if not self.go_mod_path:
            return None

        try:
            content = self.go_mod_path.read_text()
            module = self._parse_go_mod(content)
            if module:
                self.module_cache[module.name] = module
            return module
        except Exception as e:
            logger.error(f"Failed to parse go.mod: {e}")
            return None

    def _parse_go_mod(self, content: str) -> Optional["GoModule"]:
        """Parse go.mod content."""
        lines = content.strip().split("\n")
        module_name = None
        go_version = None
        dependencies: List[ModuleDependency] = []
        replacements: Dict[str, str] = {}

        in_require_block = False
        in_replace_block = False

        for line in lines:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("//"):
                continue

            # Module declaration
            if line.startswith("module "):
                module_name = line[7:].strip()
                continue

            # Go version
            if line.startswith("go "):
                go_version = line[3:].strip()
                continue

            # Require block
            if line == "require (":
                in_require_block = True
                continue
            elif line == "replace (":
                in_replace_block = True
                continue
            elif line == ")":
                in_require_block = False
                in_replace_block = False
                continue

            # Parse dependencies
            if in_require_block:
                dep = self._parse_dependency_line(line)
                if dep:
                    dependencies.append(dep)
            elif in_replace_block:
                replacement = self._parse_replacement_line(line)
                if replacement:
                    replacements[replacement[0]] = replacement[1]
            elif line.startswith("require "):
                dep = self._parse_dependency_line(line[8:])
                if dep:
                    dependencies.append(dep)
            elif line.startswith("replace "):
                replacement = self._parse_replacement_line(line[8:])
                if replacement:
                    replacements[replacement[0]] = replacement[1]

        if module_name:
            return GoModule(
                name=module_name,
                version=go_version,
                dependencies=dependencies,
                replacements=replacements,
                path=self.go_mod_path.parent,
            )
        return None

    def _parse_dependency_line(self, line: str) -> Optional["ModuleDependency"]:
        """Parse a dependency line from go.mod."""
        # Remove comments
        if "//" in line:
            line = line[: line.index("//")]
        line = line.strip()

        if not line:
            return None

        # Match module version pairs
        match = re.match(r"(\S+)\s+(\S+)", line)
        if match:
            module_path = match.group(1)
            version = match.group(2)
            return ModuleDependency(module_path, version)
        return None

    def _parse_replacement_line(self, line: str) -> Optional[Tuple[str, str]]:
        """Parse a replacement line from go.mod."""
        # Remove comments
        if "//" in line:
            line = line[: line.index("//")]
        line = line.strip()

        if not line or "=>" not in line:
            return None

        parts = line.split("=>")
        if len(parts) == 2:
            old = parts[0].strip()
            new = parts[1].strip()
            return (old, new)
        return None

    def resolve_import(self, import_path: str) -> Optional[str]:
        """Resolve an import path to its actual location."""
        if not self.current_module:
            return None

        # Check if it's a standard library import
        if self._is_stdlib_import(import_path):
            return f"stdlib:{import_path}"

        # Check if it's an internal import
        if import_path.startswith(self.current_module.name):
            relative_path = import_path[len(self.current_module.name) :].lstrip("/")
            return str(self.current_module.path / relative_path)

        # Check replacements
        for old, new in self.current_module.replacements.items():
            if import_path.startswith(old):
                if new.startswith("./") or new.startswith("../"):
                    # Local replacement
                    replacement_path = self.go_mod_path.parent / new
                    relative_part = import_path[len(old) :].lstrip("/")
                    return str(replacement_path / relative_part)
                else:
                    # Module replacement
                    return import_path.replace(old, new, 1)

        # External dependency
        return f"external:{import_path}"

    def _is_stdlib_import(self, import_path: str) -> bool:
        """Check if an import is from the Go standard library."""
        # Common stdlib packages
        stdlib_prefixes = [
            "archive/",
            "bufio",
            "builtin",
            "bytes",
            "compress/",
            "container/",
            "context",
            "crypto/",
            "database/",
            "debug/",
            "embed",
            "encoding/",
            "errors",
            "expvar",
            "flag",
            "fmt",
            "go/",
            "hash/",
            "html/",
            "image/",
            "index/",
            "io",
            "log/",
            "math/",
            "mime/",
            "net/",
            "os",
            "path/",
            "plugin",
            "reflect",
            "regexp",
            "runtime/",
            "sort",
            "strconv",
            "strings",
            "sync/",
            "syscall",
            "testing/",
            "text/",
            "time",
            "unicode/",
            "unsafe",
        ]

        for prefix in stdlib_prefixes:
            if import_path == prefix.rstrip("/") or import_path.startswith(prefix):
                return True
        return False

    def get_package_files(self, package_path: str) -> List[Path]:
        """Get all Go files in a package directory."""
        if package_path.startswith("stdlib:") or package_path.startswith("external:"):
            return []

        package_dir = Path(package_path)
        if not package_dir.exists() or not package_dir.is_dir():
            return []

        # Get all .go files except test files
        go_files = [f for f in package_dir.glob("*.go") if not f.name.endswith("_test.go")]
        return go_files


class GoModule:
    """Represents a Go module."""

    def __init__(
        self,
        name: str,
        version: Optional[str],
        dependencies: List["ModuleDependency"],
        replacements: Dict[str, str],
        path: Path,
    ):
        self.name = name
        self.version = version
        self.dependencies = dependencies
        self.replacements = replacements
        self.path = path


class ModuleDependency:
    """Represents a module dependency."""

    def __init__(self, module_path: str, version: str):
        self.module_path = module_path
        self.version = version
