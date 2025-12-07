"""Module resolution for Rust files."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class RustModuleResolver:
    """Resolves Rust module paths and dependencies."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self._module_cache: Dict[str, Path] = {}
        self._crate_roots: List[Path] = []
        self._find_crate_roots()

    def _find_crate_roots(self) -> None:
        """Find all crate roots (directories with Cargo.toml)."""
        for root, dirs, files in os.walk(self.workspace_root):
            if "Cargo.toml" in files:
                self._crate_roots.append(Path(root))
                # Don't recurse into target directories
                if "target" in dirs:
                    dirs.remove("target")

    def resolve_module_path(self, from_file: Path, module_path: str) -> Optional[Path]:
        """
        Resolve a module path from a given file.

        Args:
            from_file: The file containing the module declaration
            module_path: The module path (e.g., "crate::utils::helpers")

        Returns:
            Resolved file path or None if not found
        """
        cache_key = f"{from_file}:{module_path}"
        if cache_key in self._module_cache:
            return self._module_cache[cache_key]

        resolved = self._resolve_module_path_impl(from_file, module_path)
        if resolved:
            self._module_cache[cache_key] = resolved
        return resolved

    def _resolve_module_path_impl(self, from_file: Path, module_path: str) -> Optional[Path]:
        """Internal implementation of module path resolution."""
        parts = module_path.split("::")

        # Handle crate:: prefix
        if parts[0] == "crate":
            crate_root = self._find_crate_root(from_file)
            if not crate_root:
                return None
            return self._resolve_from_root(crate_root, parts[1:])

        # Handle super:: prefix
        if parts[0] == "super":
            parent_module = from_file.parent
            _ = parts[1:]
            while parts and parts[0] == "super":
                parent_module = parent_module.parent
                parts = parts[1:]
            return self._resolve_from_root(parent_module, parts)

        # Handle self:: prefix or relative paths
        if parts[0] == "self":
            return self._resolve_from_root(from_file.parent, parts[1:])

        # Try as relative path from current module
        return self._resolve_from_root(from_file.parent, parts)

    def _find_crate_root(self, file_path: Path) -> Optional[Path]:
        """Find the crate root for a given file."""
        current = file_path.parent
        while current >= self.workspace_root:
            if (current / "Cargo.toml").exists():
                return current / "src"
            current = current.parent
        return None

    def _resolve_from_root(self, root: Path, parts: List[str]) -> Optional[Path]:
        """Resolve module parts from a root directory."""
        if not parts:
            return root

        current = root
        for part in parts[:-1]:
            # Try as directory module
            dir_path = current / part
            if dir_path.is_dir():
                mod_file = dir_path / "mod.rs"
                if mod_file.exists():
                    current = dir_path
                    continue

            # Try as file module
            file_path = current / f"{part}.rs"
            if file_path.exists():
                return None  # Can't have more parts after a file module

            return None

        # Handle the last part
        last_part = parts[-1]

        # Try as file
        file_path = current / f"{last_part}.rs"
        if file_path.exists():
            return file_path

        # Try as directory with mod.rs
        dir_path = current / last_part / "mod.rs"
        if dir_path.exists():
            return dir_path

        # Try lib.rs or main.rs for crate root
        if len(parts) == 1 and current.name == "src":
            for special_file in ["lib.rs", "main.rs"]:
                special_path = current / special_file
                if special_path.exists():
                    return special_path

        return None

    def find_mod_declarations(self, file_content: str) -> List[Tuple[str, int]]:
        """
        Find all mod declarations in a file.

        Returns:
            List of (module_name, line_number) tuples
        """
        modules = []
        lines = file_content.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Match both "mod" and "pub mod"
            if (
                stripped.startswith("mod ") or stripped.startswith("pub mod ")
            ) and "mod tests" not in stripped:
                # Extract module name
                parts = stripped.split()
                # Find the position of "mod" keyword
                mod_index = -1
                for j, part in enumerate(parts):
                    if part == "mod":
                        mod_index = j
                        break

                if mod_index >= 0 and mod_index + 1 < len(parts):
                    module_name = parts[mod_index + 1].rstrip(";{")
                    modules.append((module_name, i + 1))

        return modules

    def find_use_statements(self, file_content: str) -> List[Tuple[str, int]]:
        """
        Find all use statements in a file.

        Returns:
            List of (import_path, line_number) tuples
        """
        imports = []
        lines = file_content.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("use "):
                # Extract import path
                import_stmt = stripped[4:].rstrip(";")
                # Handle complex imports with braces
                if "{" in import_stmt:
                    base_path = import_stmt.split("{")[0].strip().rstrip("::")
                    imports.append((base_path, i + 1))
                else:
                    # Simple import
                    import_path = import_stmt.split(" as ")[0].strip()
                    imports.append((import_path, i + 1))

        return imports

    def get_module_dependencies(self, file_path: Path) -> Set[Path]:
        """Get all dependencies of a module."""
        dependencies = set()

        try:
            content = file_path.read_text(encoding="utf-8")

            # Find use statements
            for import_path, _ in self.find_use_statements(content):
                resolved = self.resolve_module_path(file_path, import_path)
                if resolved and resolved != file_path:
                    dependencies.add(resolved)

            # Find mod declarations
            for module_name, _ in self.find_mod_declarations(content):
                resolved = self._resolve_from_root(file_path.parent, [module_name])
                if resolved and resolved != file_path:
                    dependencies.add(resolved)

        except Exception:
            pass

        return dependencies
