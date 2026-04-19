"""EcosystemParser Protocol and concrete implementations."""

from __future__ import annotations

from pathlib import Path
from typing import Set

from mcp_server.dependency_graph.ecosystems.cargo import CargoTomlParser
from mcp_server.dependency_graph.ecosystems.go import GoModParser
from mcp_server.dependency_graph.ecosystems.npm import NpmPackageJsonParser
from mcp_server.dependency_graph.ecosystems.python import PythonRequirementsParser


class EcosystemParser:
    """Protocol for ecosystem manifest parsers.

    Concrete parsers implement:
      manifest_filename: str  — the filename to look for in the repo root
      parse(path: Path) -> Set[str]  — path is the repo root directory
    """

    manifest_filename: str

    def parse(self, path: Path) -> Set[str]:  # pragma: no cover
        raise NotImplementedError


__all__ = [
    "EcosystemParser",
    "PythonRequirementsParser",
    "NpmPackageJsonParser",
    "GoModParser",
    "CargoTomlParser",
]
