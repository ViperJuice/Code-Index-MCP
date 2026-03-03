"""Fast repository language detection for plugin allowlist generation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from mcp_server.plugins.language_registry import LANGUAGE_CONFIGS


_IGNORED_DIRS: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".indexes",
    "qdrant_storage",
}


@dataclass(frozen=True)
class LanguageDetectionResult:
    """Language detection output used for runtime plugin selection."""

    detected_languages: List[str]
    counts: Dict[str, int]
    scanned_files: int
    truncated: bool = False
    root: str = "."

    def to_dict(self) -> Dict[str, object]:
        """Serialize detection result for status endpoints."""
        return {
            "detected_languages": list(self.detected_languages),
            "counts": dict(self.counts),
            "scanned_files": self.scanned_files,
            "truncated": self.truncated,
            "root": self.root,
        }


def _build_extension_map() -> Dict[str, str]:
    extension_map: Dict[str, str] = {}
    for language, cfg in LANGUAGE_CONFIGS.items():
        normalized = "csharp" if language == "c_sharp" else language
        for ext in cfg.get("extensions", []):
            extension_map[ext.lower()] = normalized
    return extension_map


_EXTENSION_TO_LANGUAGE = _build_extension_map()


def detect_repository_languages(
    repo_path: Path,
    max_files: int = 5000,
    min_files: int = 2,
) -> LanguageDetectionResult:
    """Detect repository languages quickly from file extensions.

    Args:
        repo_path: Repository root to scan
        max_files: Safety cap for files to scan
        min_files: Minimum file count threshold to include a language
    """
    root = repo_path.resolve()
    counts: Dict[str, int] = {}
    scanned = 0
    truncated = False

    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORED_DIRS]

        for filename in filenames:
            if scanned >= max_files:
                truncated = True
                break

            path = Path(current_root) / filename
            scanned += 1
            language = _EXTENSION_TO_LANGUAGE.get(path.suffix.lower())
            if language:
                counts[language] = counts.get(language, 0) + 1

        if truncated:
            break

    detected = sorted([lang for lang, count in counts.items() if count >= min_files])
    return LanguageDetectionResult(
        detected_languages=detected,
        counts=dict(sorted(counts.items())),
        scanned_files=scanned,
        truncated=truncated,
        root=str(root),
    )
