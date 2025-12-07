"""NuGet package integration for C# project analysis."""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class PackageReference:
    """Represents a NuGet package reference."""

    name: str
    version: str
    target_framework: Optional[str] = None
    include_assets: Optional[str] = None
    exclude_assets: Optional[str] = None
    private_assets: Optional[str] = None


@dataclass
class PackageInfo:
    """Detailed information about a NuGet package."""

    name: str
    version: str
    description: Optional[str] = None
    authors: List[str] = None
    dependencies: List["PackageReference"] = None
    target_frameworks: List[str] = None
    assemblies: List[str] = None
    namespaces: Set[str] = None


class NuGetIntegration:
    """Handles NuGet package analysis and dependency resolution."""

    def __init__(self):
        """Initialize NuGet integration."""
        self.package_cache: Dict[str, PackageInfo] = {}
        self.project_packages: Dict[str, List[PackageReference]] = {}
        self.global_packages_path = self._find_global_packages_path()
        self.known_package_namespaces = self._load_known_package_namespaces()

    def _find_global_packages_path(self) -> Optional[str]:
        """Find the global NuGet packages cache path."""
        # Common NuGet cache locations
        cache_paths = [
            Path.home() / ".nuget" / "packages",
            Path("C:/Users") / Path.home().name / ".nuget" / "packages",
            Path("/usr/local/share/dotnet/shared/Microsoft.NETCore.App"),
        ]

        for path in cache_paths:
            if path.exists():
                return str(path)

        return None

    def _load_known_package_namespaces(self) -> Dict[str, Set[str]]:
        """Load known namespaces for popular NuGet packages."""
        return {
            # Microsoft packages
            "Microsoft.EntityFrameworkCore": {
                "Microsoft.EntityFrameworkCore",
                "Microsoft.EntityFrameworkCore.Metadata",
                "Microsoft.EntityFrameworkCore.Storage",
                "Microsoft.EntityFrameworkCore.Infrastructure",
            },
            "Microsoft.AspNetCore": {
                "Microsoft.AspNetCore",
                "Microsoft.AspNetCore.Mvc",
                "Microsoft.AspNetCore.Http",
                "Microsoft.AspNetCore.Routing",
            },
            "Microsoft.Extensions.DependencyInjection": {
                "Microsoft.Extensions.DependencyInjection"
            },
            "Microsoft.Extensions.Logging": {"Microsoft.Extensions.Logging"},
            "Microsoft.Extensions.Configuration": {"Microsoft.Extensions.Configuration"},
            # Popular third-party packages
            "Newtonsoft.Json": {"Newtonsoft.Json"},
            "AutoMapper": {"AutoMapper"},
            "FluentValidation": {"FluentValidation"},
            "Serilog": {"Serilog"},
            "NLog": {"NLog"},
            "Dapper": {"Dapper"},
            "Polly": {"Polly"},
            "MediatR": {"MediatR"},
            "Castle.Core": {"Castle.Core", "Castle.DynamicProxy"},
            "Unity": {"Unity"},
            "Autofac": {"Autofac"},
            "Moq": {"Moq"},
            "xunit": {"Xunit"},
            "NUnit": {"NUnit.Framework"},
            "MSTest.TestFramework": {"Microsoft.VisualStudio.TestTools.UnitTesting"},
        }

    def analyze_project_packages(self, project_path: str) -> Dict[str, Any]:
        """Analyze NuGet packages in a C# project.

        Args:
            project_path: Path to .csproj file

        Returns:
            Dictionary containing package analysis results
        """
        analysis = {
            "project_path": project_path,
            "packages": [],
            "package_namespaces": set(),
            "target_framework": None,
            "package_sources": [],
            "transitive_dependencies": [],
        }

        try:
            # Parse project file
            project_info = self._parse_project_file(project_path)
            analysis["target_framework"] = project_info.get("target_framework")

            # Extract package references
            packages = project_info.get("package_references", [])
            analysis["packages"] = packages

            # Get available namespaces from packages
            for package in packages:
                namespaces = self._get_package_namespaces(package["name"], package["version"])
                analysis["package_namespaces"].update(namespaces)

            # Check for packages.config (legacy)
            packages_config_path = Path(project_path).parent / "packages.config"
            if packages_config_path.exists():
                legacy_packages = self._parse_packages_config(str(packages_config_path))
                analysis["packages"].extend(legacy_packages)

            # Analyze NuGet.config if present
            nuget_config = self._find_nuget_config(project_path)
            if nuget_config:
                analysis["package_sources"] = self._parse_nuget_config(nuget_config)

            # Cache the results
            self.project_packages[project_path] = packages

        except Exception as e:
            logger.error(f"Error analyzing packages in {project_path}: {e}")

        return analysis

    def _parse_project_file(self, project_path: str) -> Dict[str, Any]:
        """Parse a .csproj file for package information."""
        project_info = {
            "target_framework": None,
            "package_references": [],
            "project_references": [],
            "global_usings": [],
        }

        try:
            tree = ET.parse(project_path)
            root = tree.getroot()

            # Extract target framework
            target_framework_elem = root.find(".//TargetFramework")
            if target_framework_elem is not None:
                project_info["target_framework"] = target_framework_elem.text

            # Extract package references
            for package_ref in root.findall(".//PackageReference"):
                package_name = package_ref.get("Include")
                package_version = package_ref.get("Version")

                if package_name:
                    package_info = {
                        "name": package_name,
                        "version": package_version or "latest",
                        "include_assets": package_ref.get("IncludeAssets"),
                        "exclude_assets": package_ref.get("ExcludeAssets"),
                        "private_assets": package_ref.get("PrivateAssets"),
                    }
                    project_info["package_references"].append(package_info)

            # Extract project references
            for proj_ref in root.findall(".//ProjectReference"):
                include = proj_ref.get("Include")
                if include:
                    project_info["project_references"].append(include)

            # Extract global usings (newer .NET feature)
            for using_elem in root.findall(".//Using"):
                include = using_elem.get("Include")
                if include:
                    project_info["global_usings"].append(include)

        except Exception as e:
            logger.error(f"Error parsing project file {project_path}: {e}")

        return project_info

    def _parse_packages_config(self, packages_config_path: str) -> List[Dict[str, str]]:
        """Parse legacy packages.config file."""
        packages = []

        try:
            tree = ET.parse(packages_config_path)
            root = tree.getroot()

            for package in root.findall(".//package"):
                package_id = package.get("id")
                version = package.get("version")
                target_framework = package.get("targetFramework")

                if package_id:
                    packages.append(
                        {
                            "name": package_id,
                            "version": version or "unknown",
                            "target_framework": target_framework,
                        }
                    )

        except Exception as e:
            logger.error(f"Error parsing packages.config {packages_config_path}: {e}")

        return packages

    def _find_nuget_config(self, project_path: str) -> Optional[str]:
        """Find NuGet.config file for the project."""
        current_dir = Path(project_path).parent

        # Walk up the directory tree to find NuGet.config
        while current_dir != current_dir.parent:
            config_files = [
                current_dir / "NuGet.config",
                current_dir / "nuget.config",
                current_dir / "Nuget.config",
            ]

            for config_file in config_files:
                if config_file.exists():
                    return str(config_file)

            current_dir = current_dir.parent

        return None

    def _parse_nuget_config(self, config_path: str) -> List[Dict[str, str]]:
        """Parse NuGet.config for package sources."""
        sources = []

        try:
            tree = ET.parse(config_path)
            root = tree.getroot()

            for source in root.findall(".//packageSources/add"):
                name = source.get("key")
                url = source.get("value")

                if name and url:
                    sources.append({"name": name, "url": url})

        except Exception as e:
            logger.error(f"Error parsing NuGet.config {config_path}: {e}")

        return sources

    def _get_package_namespaces(self, package_name: str, version: str) -> Set[str]:
        """Get namespaces provided by a NuGet package."""
        # Check known packages first
        if package_name in self.known_package_namespaces:
            return self.known_package_namespaces[package_name]

        # Try to analyze package from cache
        if self.global_packages_path:
            package_path = Path(self.global_packages_path) / package_name.lower() / version
            if package_path.exists():
                return self._analyze_package_assemblies(package_path)

        # Fallback: infer namespaces from package name
        return self._infer_namespaces_from_name(package_name)

    def _analyze_package_assemblies(self, package_path: Path) -> Set[str]:
        """Analyze assemblies in a NuGet package to extract namespaces."""
        namespaces = set()

        try:
            # Look for .nuspec file first
            nuspec_files = list(package_path.glob("*.nuspec"))
            if nuspec_files:
                namespaces.update(self._parse_nuspec_file(nuspec_files[0]))

            # Look for lib folders
            lib_dirs = package_path.glob("lib/*")
            for lib_dir in lib_dirs:
                dll_files = list(lib_dir.glob("*.dll"))
                for dll_file in dll_files:
                    # Extract namespace from assembly name (simplified)
                    assembly_name = dll_file.stem
                    if not assembly_name.startswith("System."):
                        namespaces.add(assembly_name)

        except Exception as e:
            logger.debug(f"Error analyzing package assemblies in {package_path}: {e}")

        return namespaces

    def _parse_nuspec_file(self, nuspec_path: Path) -> Set[str]:
        """Parse .nuspec file for namespace information."""
        namespaces = set()

        try:
            tree = ET.parse(nuspec_path)
            root = tree.getroot()

            # Extract from metadata
            ns = {"nuget": "http://schemas.microsoft.com/packaging/2010/07/nuspec.xsd"}

            # Get package ID as potential namespace
            package_id = root.find(".//nuget:id", ns)
            if package_id is not None and package_id.text:
                namespaces.add(package_id.text)

            # Look for dependencies that might indicate namespaces
            dependencies = root.findall(".//nuget:dependency", ns)
            for dep in dependencies:
                dep_id = dep.get("id")
                if dep_id and not dep_id.startswith("System."):
                    namespaces.add(dep_id)

        except Exception as e:
            logger.debug(f"Error parsing nuspec file {nuspec_path}: {e}")

        return namespaces

    def _infer_namespaces_from_name(self, package_name: str) -> Set[str]:
        """Infer likely namespaces from package name."""
        namespaces = {package_name}

        # Common patterns
        if "." in package_name:
            # Split on dots and create hierarchical namespaces
            parts = package_name.split(".")
            for i in range(len(parts)):
                namespace = ".".join(parts[: i + 1])
                namespaces.add(namespace)

        return namespaces

    def get_package_info(self, package_name: str, version: str = None) -> Optional[PackageInfo]:
        """Get detailed information about a specific package."""
        cache_key = f"{package_name}:{version or 'latest'}"

        if cache_key in self.package_cache:
            return self.package_cache[cache_key]

        # Try to load from local cache
        package_info = self._load_package_info(package_name, version)
        if package_info:
            self.package_cache[cache_key] = package_info

        return package_info

    def _load_package_info(self, package_name: str, version: str = None) -> Optional[PackageInfo]:
        """Load package information from local cache or registry."""
        if not self.global_packages_path:
            return None

        try:
            package_dir = Path(self.global_packages_path) / package_name.lower()

            if not package_dir.exists():
                return None

            # Find the specific version or latest
            if version:
                version_dir = package_dir / version
            else:
                # Get the latest version
                version_dirs = [d for d in package_dir.iterdir() if d.is_dir()]
                if not version_dirs:
                    return None
                version_dir = max(version_dirs, key=lambda p: p.name)
                version = version_dir.name

            if not version_dir.exists():
                return None

            # Parse .nuspec file for metadata
            nuspec_files = list(version_dir.glob("*.nuspec"))
            if not nuspec_files:
                return None

            return self._parse_package_metadata(nuspec_files[0], package_name, version)

        except Exception as e:
            logger.debug(f"Error loading package info for {package_name}:{version}: {e}")
            return None

    def _parse_package_metadata(
        self, nuspec_path: Path, package_name: str, version: str
    ) -> PackageInfo:
        """Parse package metadata from .nuspec file."""
        package_info = PackageInfo(
            name=package_name,
            version=version,
            authors=[],
            dependencies=[],
            target_frameworks=[],
            assemblies=[],
            namespaces=set(),
        )

        try:
            tree = ET.parse(nuspec_path)
            root = tree.getroot()
            ns = {"nuget": "http://schemas.microsoft.com/packaging/2010/07/nuspec.xsd"}

            # Extract metadata
            metadata = root.find(".//nuget:metadata", ns)
            if metadata is not None:
                # Description
                desc_elem = metadata.find("nuget:description", ns)
                if desc_elem is not None:
                    package_info.description = desc_elem.text

                # Authors
                authors_elem = metadata.find("nuget:authors", ns)
                if authors_elem is not None and authors_elem.text:
                    package_info.authors = [a.strip() for a in authors_elem.text.split(",")]

                # Dependencies
                deps_group = metadata.find(".//nuget:dependencies/nuget:group", ns)
                if deps_group is not None:
                    target_framework = deps_group.get("targetFramework")
                    if target_framework:
                        package_info.target_frameworks.append(target_framework)

                    for dep in deps_group.findall("nuget:dependency", ns):
                        dep_id = dep.get("id")
                        dep_version = dep.get("version")
                        if dep_id:
                            package_info.dependencies.append(
                                PackageReference(name=dep_id, version=dep_version or "latest")
                            )

            # Get namespaces
            package_info.namespaces = self._get_package_namespaces(package_name, version)

        except Exception as e:
            logger.debug(f"Error parsing package metadata from {nuspec_path}: {e}")

        return package_info

    def resolve_dependencies(self, packages: List[PackageReference]) -> List[PackageReference]:
        """Resolve transitive dependencies for a list of packages."""
        resolved = []
        visited = set()

        def resolve_recursive(package: PackageReference):
            if package.name in visited:
                return

            visited.add(package.name)
            resolved.append(package)

            # Get package info
            package_info = self.get_package_info(package.name, package.version)
            if package_info and package_info.dependencies:
                for dep in package_info.dependencies:
                    resolve_recursive(dep)

        for package in packages:
            resolve_recursive(package)

        return resolved

    def get_available_types_from_packages(self, project_path: str) -> Dict[str, Set[str]]:
        """Get available types from all packages in a project.

        Args:
            project_path: Path to the project file

        Returns:
            Dictionary mapping namespaces to available types
        """
        available_types = {}

        if project_path in self.project_packages:
            packages = self.project_packages[project_path]

            for package in packages:
                namespaces = self._get_package_namespaces(package["name"], package["version"])

                for namespace in namespaces:
                    if namespace not in available_types:
                        available_types[namespace] = set()

                    # Add common types for known packages
                    types = self._get_common_types_for_namespace(namespace)
                    available_types[namespace].update(types)

        return available_types

    def _get_common_types_for_namespace(self, namespace: str) -> Set[str]:
        """Get common types for a namespace."""
        # This would ideally come from assembly metadata
        # For now, return some common types for known namespaces
        common_types = {
            "System": {
                "String",
                "Int32",
                "Int64",
                "Boolean",
                "DateTime",
                "Guid",
                "Object",
                "Exception",
                "Type",
                "Array",
                "Enum",
                "Delegate",
            },
            "System.Collections.Generic": {
                "List<T>",
                "Dictionary<TKey, TValue>",
                "IEnumerable<T>",
                "ICollection<T>",
                "IList<T>",
                "Queue<T>",
                "Stack<T>",
                "HashSet<T>",
                "SortedDictionary<TKey, TValue>",
            },
            "System.Linq": {"Enumerable", "IQueryable<T>", "IGrouping<TKey, TElement>"},
            "System.Threading.Tasks": {
                "Task",
                "Task<T>",
                "TaskCompletionSource<T>",
                "CancellationToken",
            },
            "Microsoft.EntityFrameworkCore": {
                "DbContext",
                "DbSet<T>",
                "DbContextOptions",
                "Entity",
            },
            "Microsoft.AspNetCore.Mvc": {
                "Controller",
                "ControllerBase",
                "ActionResult",
                "IActionResult",
            },
            "Newtonsoft.Json": {
                "JsonConvert",
                "JsonSerializer",
                "JsonProperty",
                "JsonIgnore",
            },
        }

        return common_types.get(namespace, set())

    def check_package_compatibility(
        self, package_name: str, version: str, target_framework: str
    ) -> bool:
        """Check if a package version is compatible with target framework."""
        package_info = self.get_package_info(package_name, version)

        if not package_info or not package_info.target_frameworks:
            return True  # Assume compatible if no info available

        # Simple compatibility check (would be more complex in reality)
        for framework in package_info.target_frameworks:
            if target_framework.startswith(framework.split(".")[0]):
                return True

        return False
