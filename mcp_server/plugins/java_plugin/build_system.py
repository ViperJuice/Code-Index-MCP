"""Build system integration for Maven and Gradle."""

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp_server.plugins.specialized_plugin_base import (
    BuildDependency,
    IBuildSystemIntegration,
)

logger = logging.getLogger(__name__)


class JavaBuildSystemIntegration(IBuildSystemIntegration):
    """Handles Maven and Gradle build systems."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.dependencies_cache: Dict[str, List[BuildDependency]] = {}
        self.repositories: List[str] = ["https://repo.maven.apache.org/maven2/"]
        self.project_info: Dict[str, Any] = {}

        # Detect build system
        self.build_system = self._detect_build_system()
        logger.info(f"Detected build system: {self.build_system}")

    def _detect_build_system(self) -> Optional[str]:
        """Detect which build system is used."""
        if (self.project_root / "pom.xml").exists():
            return "maven"
        elif (self.project_root / "build.gradle").exists():
            return "gradle"
        elif (self.project_root / "build.gradle.kts").exists():
            return "gradle-kotlin"
        return None

    def parse_build_file(self, build_file_path: Path) -> List[BuildDependency]:
        """Parse build configuration and extract dependencies."""
        if build_file_path.name == "pom.xml":
            return self._parse_maven_pom(build_file_path)
        elif build_file_path.name in ["build.gradle", "build.gradle.kts"]:
            return self._parse_gradle_build(build_file_path)
        else:
            logger.warning(f"Unknown build file type: {build_file_path}")
            return []

    def _parse_maven_pom(self, pom_path: Path) -> List[BuildDependency]:
        """Parse Maven POM file."""
        dependencies = []

        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()

            # Handle namespace
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}
            if root.tag.startswith("{"):
                ns = {"m": root.tag.split("}")[0][1:]}

            # Extract project info
            group_id = self._find_text(root, ".//m:groupId", ns) or self._find_text(
                root, ".//m:parent/m:groupId", ns
            )
            artifact_id = self._find_text(root, ".//m:artifactId", ns)
            version = self._find_text(root, ".//m:version", ns) or self._find_text(
                root, ".//m:parent/m:version", ns
            )

            if artifact_id:
                self.project_info = {
                    "group_id": group_id,
                    "artifact_id": artifact_id,
                    "version": version,
                    "packaging": self._find_text(root, ".//m:packaging", ns) or "jar",
                }

            # Extract properties for variable substitution
            properties = {}
            props_elem = root.find(".//m:properties", ns)
            if props_elem is not None:
                for prop in props_elem:
                    prop_name = prop.tag.split("}")[-1] if "}" in prop.tag else prop.tag
                    properties[prop_name] = prop.text

            # Extract dependencies
            deps_elem = root.find(".//m:dependencies", ns)
            if deps_elem is not None:
                for dep in deps_elem.findall("m:dependency", ns):
                    dep_group = self._find_text(dep, "m:groupId", ns)
                    dep_artifact = self._find_text(dep, "m:artifactId", ns)
                    dep_version = self._find_text(dep, "m:version", ns)
                    dep_scope = self._find_text(dep, "m:scope", ns) or "compile"

                    if dep_group and dep_artifact:
                        # Resolve property placeholders
                        if (
                            dep_version
                            and dep_version.startswith("${")
                            and dep_version.endswith("}")
                        ):
                            prop_name = dep_version[2:-1]
                            dep_version = properties.get(prop_name, dep_version)

                        dependencies.append(
                            BuildDependency(
                                name=dep_artifact,
                                version=dep_version or "latest",
                                group_id=dep_group,
                                is_dev_dependency=dep_scope in ["test", "provided"],
                            )
                        )

            # Also check dependency management section
            dep_mgmt = root.find(".//m:dependencyManagement/m:dependencies", ns)
            if dep_mgmt is not None:
                for dep in dep_mgmt.findall("m:dependency", ns):
                    # These are managed dependencies - store for version resolution
                    pass

            # Extract repositories
            repos = root.find(".//m:repositories", ns)
            if repos is not None:
                for repo in repos.findall("m:repository", ns):
                    url = self._find_text(repo, "m:url", ns)
                    if url:
                        self.repositories.append(url)

        except Exception as e:
            logger.error(f"Failed to parse Maven POM {pom_path}: {e}")

        return dependencies

    def _parse_gradle_build(self, gradle_path: Path) -> List[BuildDependency]:
        """Parse Gradle build file."""
        dependencies = []

        try:
            content = gradle_path.read_text(encoding="utf-8")

            # Extract dependencies using regex patterns
            # This is simplified - real Gradle parsing would require Groovy/Kotlin parsing

            # Pattern for dependencies block
            deps_block_pattern = r"dependencies\s*\{([^}]+)\}"
            deps_match = re.search(deps_block_pattern, content, re.DOTALL)

            if deps_match:
                deps_content = deps_match.group(1)

                # Patterns for different dependency notations
                patterns = [
                    # implementation 'group:artifact:version'
                    r"(\w+)\s*[(\']([^:\']+):([^:\']+):([^\']+)[\')](.*)",
                    # implementation group: 'group', name: 'artifact', version: 'version'
                    r'(\w+)\s*group:\s*[\'"]([^\'"]+)[\'"],\s*name:\s*[\'"]([^\'"]+)[\'"],\s*version:\s*[\'"]([^\'"]+)[\'"]',
                    # implementation("group:artifact:version") - Kotlin DSL
                    r'(\w+)\("([^:]+):([^:]+):([^"]+)"\)',
                ]

                for pattern in patterns:
                    for match in re.finditer(pattern, deps_content):
                        config = match.group(1)

                        if len(match.groups()) >= 4:
                            group_id = match.group(2)
                            artifact_id = match.group(3)
                            version = match.group(4)

                            is_dev = config in [
                                "testImplementation",
                                "testCompile",
                                "testRuntime",
                                "androidTestImplementation",
                                "debugImplementation",
                            ]

                            dependencies.append(
                                BuildDependency(
                                    name=artifact_id,
                                    version=version,
                                    group_id=group_id,
                                    is_dev_dependency=is_dev,
                                )
                            )

            # Extract repositories
            repos_pattern = r"repositories\s*\{([^}]+)\}"
            repos_match = re.search(repos_pattern, content, re.DOTALL)

            if repos_match:
                repos_content = repos_match.group(1)

                # Look for maven repository URLs
                url_pattern = r'url\s*[\'"]([^\'"]+)[\'"]'
                for match in re.finditer(url_pattern, repos_content):
                    self.repositories.append(match.group(1))

                # Check for standard repos
                if "mavenCentral()" in repos_content:
                    self.repositories.append("https://repo.maven.apache.org/maven2/")
                if "jcenter()" in repos_content:
                    self.repositories.append("https://jcenter.bintray.com/")

            # Extract project info
            group_pattern = r'group\s*=?\s*[\'"]([^\'"]+)[\'"]'
            version_pattern = r'version\s*=?\s*[\'"]([^\'"]+)[\'"]'

            group_match = re.search(group_pattern, content)
            version_match = re.search(version_pattern, content)

            if group_match:
                self.project_info["group_id"] = group_match.group(1)
            if version_match:
                self.project_info["version"] = version_match.group(1)

            # For Kotlin DSL, also check for different syntax
            if gradle_path.suffix == ".kts":
                # Kotlin DSL specific patterns
                kotlin_deps_pattern = r"dependencies\s*\{([^}]+)\}"
                kotlin_match = re.search(kotlin_deps_pattern, content, re.DOTALL)

                if kotlin_match:
                    kotlin_content = kotlin_match.group(1)

                    # Pattern for Kotlin DSL dependencies
                    kotlin_pattern = r'(\w+)\("([^:]+):([^:]+):([^"]+)"\)'

                    for match in re.finditer(kotlin_pattern, kotlin_content):
                        config = match.group(1)
                        group_id = match.group(2)
                        artifact_id = match.group(3)
                        version = match.group(4)

                        is_dev = config in ["testImplementation", "testRuntimeOnly"]

                        dependencies.append(
                            BuildDependency(
                                name=artifact_id,
                                version=version,
                                group_id=group_id,
                                is_dev_dependency=is_dev,
                            )
                        )

        except Exception as e:
            logger.error(f"Failed to parse Gradle build file {gradle_path}: {e}")

        return dependencies

    def resolve_external_import(self, import_path: str) -> Optional[str]:
        """Resolve an import from external dependencies."""
        # Check if import matches any known dependency
        parts = import_path.split(".")

        for dep in self.dependencies_cache.values():
            for d in dep:
                # Try to match by group ID pattern
                if d.group_id and import_path.startswith(d.group_id):
                    return f"{d.group_id}:{d.name}:{d.version}"

                # Try to match by common patterns
                if parts[0] in ["com", "org", "net"] and len(parts) > 2:
                    potential_group = ".".join(parts[:2])
                    if d.group_id and d.group_id.startswith(potential_group):
                        return f"{d.group_id}:{d.name}:{d.version}"

        return None

    def get_project_structure(self) -> Dict[str, Any]:
        """Get the project structure from build configuration."""
        structure = {
            "build_system": self.build_system,
            "project_info": self.project_info,
            "source_dirs": [],
            "test_dirs": [],
            "resource_dirs": [],
            "output_dir": None,
        }

        if self.build_system == "maven":
            # Standard Maven structure
            structure["source_dirs"] = ["src/main/java"]
            structure["test_dirs"] = ["src/test/java"]
            structure["resource_dirs"] = ["src/main/resources", "src/test/resources"]
            structure["output_dir"] = "target/classes"
        elif self.build_system in ["gradle", "gradle-kotlin"]:
            # Standard Gradle structure (can be customized)
            structure["source_dirs"] = ["src/main/java"]
            structure["test_dirs"] = ["src/test/java"]
            structure["resource_dirs"] = ["src/main/resources", "src/test/resources"]
            structure["output_dir"] = "build/classes"

            # Try to detect Android project
            if (self.project_root / "src/main/AndroidManifest.xml").exists():
                structure["source_dirs"].append("src/main/kotlin")
                structure["is_android"] = True

        # Check if directories actually exist
        structure["source_dirs"] = [
            d for d in structure["source_dirs"] if (self.project_root / d).exists()
        ]
        structure["test_dirs"] = [
            d for d in structure["test_dirs"] if (self.project_root / d).exists()
        ]
        structure["resource_dirs"] = [
            d for d in structure["resource_dirs"] if (self.project_root / d).exists()
        ]

        return structure

    def _find_text(self, element, path: str, namespaces: Dict[str, str]) -> Optional[str]:
        """Safely find text in XML element."""
        elem = element.find(path, namespaces)
        return elem.text if elem is not None and elem.text else None

    def get_classpath(self) -> List[Path]:
        """Get the full classpath for the project."""
        classpath = []

        # Add project output directories
        structure = self.get_project_structure()
        if structure["output_dir"]:
            output_path = self.project_root / structure["output_dir"]
            if output_path.exists():
                classpath.append(output_path)

        # Add dependency JARs (simplified - would need actual resolution)
        if self.build_system == "maven":
            local_repo = Path.home() / ".m2/repository"
            if local_repo.exists():
                # Would need to resolve actual JAR paths from dependencies
                pass
        elif self.build_system in ["gradle", "gradle-kotlin"]:
            gradle_cache = Path.home() / ".gradle/caches"
            if gradle_cache.exists():
                # Would need to resolve actual JAR paths from dependencies
                pass

        return classpath
