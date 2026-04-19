"""Go go.mod parser — delegates to GoModuleResolver."""

from __future__ import annotations

from pathlib import Path
from typing import Set

from mcp_server.plugins.go_plugin.module_resolver import GoModuleResolver


class GoModParser:
    manifest_filename = "go.mod"

    def parse(self, path: Path) -> Set[str]:
        manifest = path / self.manifest_filename
        if not manifest.exists():
            return set()
        resolver = GoModuleResolver(path)
        module = resolver.current_module
        if module is None:
            return set()
        return {dep.module_path for dep in module.dependencies}
