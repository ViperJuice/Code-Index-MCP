"""Cargo.toml integration for Rust projects."""

try:
    import toml

    HAS_TOML = True
except ImportError:
    HAS_TOML = False

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class CrateInfo:
    """Information about a Rust crate."""

    name: str
    version: str
    path: Path
    dependencies: Dict[str, str]
    dev_dependencies: Dict[str, str]
    build_dependencies: Dict[str, str]
    features: Dict[str, List[str]]
    default_features: List[str]
    edition: str
    workspace_members: List[str]


@dataclass
class DependencyInfo:
    """Detailed information about a dependency."""

    name: str
    version: Optional[str]
    path: Optional[str]
    git: Optional[str]
    branch: Optional[str]
    features: List[str]
    optional: bool


class CargoIntegration:
    """Integration with Cargo for Rust projects."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self._crate_cache: Dict[Path, CrateInfo] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}

    def find_cargo_tomls(self) -> List[Path]:
        """Find all Cargo.toml files in the workspace."""
        cargo_files = []

        import os

        for root, dirs, files in os.walk(self.workspace_root):
            # Skip target directories
            if "target" in dirs:
                dirs.remove("target")

            if "Cargo.toml" in files:
                cargo_files.append(Path(root) / "Cargo.toml")

        return cargo_files

    def parse_cargo_toml(self, cargo_path: Path) -> Optional[CrateInfo]:
        """Parse a Cargo.toml file."""
        if cargo_path in self._crate_cache:
            return self._crate_cache[cargo_path]

        try:
            content = cargo_path.read_text(encoding="utf-8")
            if HAS_TOML:
                data = toml.loads(content)
            else:
                # Fallback basic TOML parser
                data = self._parse_toml_basic(content)

            # Extract package information
            package = data.get("package", {})
            name = package.get("name", "unknown")
            version = package.get("version", "0.0.0")
            edition = package.get("edition", "2018")

            # Extract dependencies
            dependencies = self._parse_dependencies(data.get("dependencies", {}))
            dev_dependencies = self._parse_dependencies(data.get("dev-dependencies", {}))
            build_dependencies = self._parse_dependencies(data.get("build-dependencies", {}))

            # Extract features
            features = data.get("features", {})
            default_features = features.get("default", [])

            # Extract workspace members
            workspace = data.get("workspace", {})
            workspace_members = workspace.get("members", [])

            crate_info = CrateInfo(
                name=name,
                version=version,
                path=cargo_path.parent,
                dependencies=dependencies,
                dev_dependencies=dev_dependencies,
                build_dependencies=build_dependencies,
                features=features,
                default_features=default_features,
                edition=edition,
                workspace_members=workspace_members,
            )

            self._crate_cache[cargo_path] = crate_info
            return crate_info

        except Exception as e:
            print(f"Error parsing {cargo_path}: {e}")
            return None

    def _parse_dependencies(self, deps_dict: Dict[str, Any]) -> Dict[str, str]:
        """Parse dependencies section."""
        dependencies = {}

        for name, spec in deps_dict.items():
            if isinstance(spec, str):
                # Simple version string
                dependencies[name] = spec
            elif isinstance(spec, dict):
                # Complex dependency specification
                version = spec.get("version", "*")
                dependencies[name] = version

        return dependencies

    def get_detailed_dependency(
        self, deps_dict: Dict[str, Any], dep_name: str
    ) -> Optional[DependencyInfo]:
        """Get detailed information about a specific dependency."""
        if dep_name not in deps_dict:
            return None

        spec = deps_dict[dep_name]

        if isinstance(spec, str):
            return DependencyInfo(
                name=dep_name,
                version=spec,
                path=None,
                git=None,
                branch=None,
                features=[],
                optional=False,
            )
        elif isinstance(spec, dict):
            return DependencyInfo(
                name=dep_name,
                version=spec.get("version"),
                path=spec.get("path"),
                git=spec.get("git"),
                branch=spec.get("branch"),
                features=spec.get("features", []),
                optional=spec.get("optional", False),
            )

        return None

    def build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build a dependency graph for all crates in the workspace."""
        if self._dependency_graph:
            return self._dependency_graph

        cargo_files = self.find_cargo_tomls()

        for cargo_path in cargo_files:
            crate_info = self.parse_cargo_toml(cargo_path)
            if crate_info:
                deps = set()
                deps.update(crate_info.dependencies.keys())
                deps.update(crate_info.dev_dependencies.keys())
                deps.update(crate_info.build_dependencies.keys())
                self._dependency_graph[crate_info.name] = deps

        return self._dependency_graph

    def find_crate_by_name(self, crate_name: str) -> Optional[CrateInfo]:
        """Find a crate by its name."""
        for crate_info in self._crate_cache.values():
            if crate_info.name == crate_name:
                return crate_info

        # If not in cache, search for it
        cargo_files = self.find_cargo_tomls()
        for cargo_path in cargo_files:
            crate_info = self.parse_cargo_toml(cargo_path)
            if crate_info and crate_info.name == crate_name:
                return crate_info

        return None

    def get_workspace_info(self) -> Optional[Dict[str, Any]]:
        """Get workspace-level information."""
        workspace_cargo = self.workspace_root / "Cargo.toml"

        if not workspace_cargo.exists():
            return None

        try:
            content = workspace_cargo.read_text(encoding="utf-8")
            data = toml.loads(content)

            workspace = data.get("workspace", {})
            if not workspace:
                return None

            return {
                "members": workspace.get("members", []),
                "exclude": workspace.get("exclude", []),
                "dependencies": workspace.get("dependencies", {}),
                "metadata": workspace.get("metadata", {}),
            }

        except Exception:
            return None

    def resolve_local_dependency(self, from_crate: str, dep_name: str) -> Optional[Path]:
        """Resolve a local dependency path."""
        crate_info = self.find_crate_by_name(from_crate)
        if not crate_info:
            return None

        cargo_path = crate_info.path / "Cargo.toml"

        try:
            content = cargo_path.read_text(encoding="utf-8")
            data = toml.loads(content)

            # Check all dependency sections
            for dep_section in [
                "dependencies",
                "dev-dependencies",
                "build-dependencies",
            ]:
                deps = data.get(dep_section, {})
                if dep_name in deps:
                    dep_spec = deps[dep_name]
                    if isinstance(dep_spec, dict) and "path" in dep_spec:
                        dep_path = crate_info.path / dep_spec["path"]
                        if dep_path.exists():
                            return dep_path.resolve()

        except Exception:
            pass

        return None

    def get_crate_features(self, crate_name: str) -> Dict[str, List[str]]:
        """Get all features defined by a crate."""
        crate_info = self.find_crate_by_name(crate_name)
        if crate_info:
            return crate_info.features
        return {}

    def get_enabled_features(self, from_crate: str, dep_name: str) -> List[str]:
        """Get features enabled for a dependency."""
        crate_info = self.find_crate_by_name(from_crate)
        if not crate_info:
            return []

        cargo_path = crate_info.path / "Cargo.toml"

        try:
            content = cargo_path.read_text(encoding="utf-8")
            data = toml.loads(content)

            # Check all dependency sections
            for dep_section in [
                "dependencies",
                "dev-dependencies",
                "build-dependencies",
            ]:
                deps = data.get(dep_section, {})
                if dep_name in deps:
                    dep_spec = deps[dep_name]
                    if isinstance(dep_spec, dict):
                        return dep_spec.get("features", [])

        except Exception:
            pass

        return []

    def get_binary_targets(self, crate_name: str) -> List[str]:
        """Get binary targets defined in a crate."""
        crate_info = self.find_crate_by_name(crate_name)
        if not crate_info:
            return []

        cargo_path = crate_info.path / "Cargo.toml"

        try:
            content = cargo_path.read_text(encoding="utf-8")
            data = toml.loads(content)

            binaries = []

            # Check [[bin]] sections
            bins = data.get("bin", [])
            if isinstance(bins, list):
                for bin_spec in bins:
                    if isinstance(bin_spec, dict) and "name" in bin_spec:
                        binaries.append(bin_spec["name"])

            # Check default binary (src/main.rs)
            main_rs = crate_info.path / "src" / "main.rs"
            if main_rs.exists() and crate_info.name not in binaries:
                binaries.append(crate_info.name)

            return binaries

        except Exception:
            return []

    def _parse_toml_basic(self, content: str) -> Dict[str, Any]:
        """Basic TOML parser fallback when toml library is not available."""
        data = {}
        _ = None
        current_table = data

        for line in content.split("\n"):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Handle section headers [section]
            if line.startswith("[") and line.endswith("]"):
                section_name = line[1:-1]
                if "." in section_name:
                    # Handle nested sections like [dev-dependencies]
                    parts = section_name.split(".")
                    current_table = data
                    for part in parts[:-1]:
                        if part not in current_table:
                            current_table[part] = {}
                        current_table = current_table[part]

                    if parts[-1] not in current_table:
                        current_table[parts[-1]] = {}
                    current_table = current_table[parts[-1]]
                else:
                    if section_name not in data:
                        data[section_name] = {}
                    current_table = data[section_name]
                _ = section_name
                continue

            # Handle key-value pairs
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().strip('"')
                value = value.strip()

                # Parse value
                if value.startswith('"') and value.endswith('"'):
                    # String value
                    value = value[1:-1]
                elif value.startswith("[") and value.endswith("]"):
                    # Array value
                    array_content = value[1:-1]
                    if array_content.strip():
                        value = [item.strip().strip('"') for item in array_content.split(",")]
                    else:
                        value = []
                elif value.startswith("{") and value.endswith("}"):
                    # Inline table (simplified)
                    value = {"version": "1.0"}  # Basic fallback
                elif value.isdigit():
                    # Integer
                    value = int(value)
                elif value in ["true", "false"]:
                    # Boolean
                    value = value == "true"

                current_table[key] = value

        return data
