"""Cargo.toml parser — delegates to CargoIntegration."""

from __future__ import annotations

from pathlib import Path
from typing import Set

from mcp_server.plugins.rust_plugin.cargo_integration import CargoIntegration


class CargoTomlParser:
    manifest_filename = "Cargo.toml"

    def parse(self, path: Path) -> Set[str]:
        manifest = path / self.manifest_filename
        if not manifest.exists():
            return set()
        integration = CargoIntegration(path)
        crate_info = integration.parse_cargo_toml(manifest)
        if crate_info is None:
            return set()
        packages: Set[str] = set()
        packages.update(crate_info.dependencies.keys())
        packages.update(crate_info.dev_dependencies.keys())
        packages.update(crate_info.build_dependencies.keys())
        return packages
