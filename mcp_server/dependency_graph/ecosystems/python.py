"""Python requirements.txt parser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Set


class PythonRequirementsParser:
    manifest_filename = "requirements.txt"

    def parse(self, path: Path) -> Set[str]:
        manifest = path / self.manifest_filename
        if not manifest.exists():
            return set()
        packages: Set[str] = set()
        for line in manifest.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip version specifiers and extras
            name = re.split(r"[>=<!;\[#\s]", line)[0].strip()
            if name:
                packages.add(name)
        return packages
