import os
from functools import lru_cache
from pathlib import Path
from typing import Optional


def parse_allowed_roots(raw_roots: str) -> tuple[Path, ...]:
    """Parse MCP_ALLOWED_ROOTS into canonical paths.

    The canonical separator is os.pathsep (":" on Unix, ";" on Windows).
    Comma-separated values are accepted only as a legacy fallback.
    """
    raw_roots = raw_roots.strip()
    if not raw_roots:
        return ()

    if os.pathsep in raw_roots:
        parts = raw_roots.split(os.pathsep)
    elif "," in raw_roots:
        parts = raw_roots.split(",")
    else:
        parts = [raw_roots]

    return resolve_allowed_roots(tuple(part.strip() for part in parts if part.strip()))


@lru_cache(maxsize=1)
def resolve_allowed_roots(raw_roots: tuple[str, ...]) -> tuple[Path, ...]:
    return tuple(Path(os.path.realpath(os.path.expanduser(r))) for r in raw_roots)


def path_within_allowed(candidate: Path, roots: Optional[tuple[Path, ...]] = None) -> bool:
    if roots is None:
        return False
    # realpath follows symlinks — detects escape through symlinks without .resolve() on candidate
    candidate_real = os.path.realpath(os.fspath(candidate.expanduser()))
    for root in roots:
        try:
            common = os.path.commonpath([candidate_real, os.fspath(root)])
            if Path(common) == root:
                return True
        except ValueError:
            continue
    return False
