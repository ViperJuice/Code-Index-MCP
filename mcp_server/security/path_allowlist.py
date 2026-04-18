import os
from functools import lru_cache
from pathlib import Path
from typing import Optional


@lru_cache(maxsize=1)
def resolve_allowed_roots(raw_roots: tuple[str, ...]) -> tuple[Path, ...]:
    return tuple(Path(os.path.realpath(r)) for r in raw_roots)


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
