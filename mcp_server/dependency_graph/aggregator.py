"""DependencyGraphAnalyzer — resolves package names to registered repo_ids."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Set

from mcp_server.dependency_graph.ecosystems.cargo import CargoTomlParser
from mcp_server.dependency_graph.ecosystems.go import GoModParser
from mcp_server.dependency_graph.ecosystems.npm import NpmPackageJsonParser
from mcp_server.dependency_graph.ecosystems.python import PythonRequirementsParser

if TYPE_CHECKING:
    from mcp_server.storage.multi_repo_manager import MultiRepositoryManager

_PARSERS = [
    PythonRequirementsParser(),
    NpmPackageJsonParser(),
    GoModParser(),
    CargoTomlParser(),
]


class DependencyGraphAnalyzer:
    def __init__(self, multi_repo_manager: "MultiRepositoryManager") -> None:
        self._manager = multi_repo_manager

    async def analyze(self, repo_id: str) -> Set[str]:
        """Return repo_ids that repo_id directly depends on.

        Package names not owned by any registered repo are silently dropped.
        """
        repo_info = self._manager.get_repository_info(repo_id)
        if repo_info is None:
            return set()

        repo_path = Path(repo_info.path)
        package_names: Set[str] = set()
        for parser in _PARSERS:
            package_names.update(parser.parse(repo_path))

        if not package_names:
            return set()

        # Build name -> repo_id map from registered repos
        name_to_id: dict[str, str] = {}
        for info in self._manager.list_repositories():
            if info.repository_id != repo_id:
                name_to_id[info.name] = info.repository_id

        return {name_to_id[pkg] for pkg in package_names if pkg in name_to_id}
