"""Helpers for subprocess environment construction and command metadata."""

from __future__ import annotations

import os
import shutil
import site
import sys
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Mapping


@dataclass(frozen=True)
class CommandAvailability:
    """Metadata-only command availability result."""

    command: str
    available: bool
    resolved_path: str | None
    remediation: str


def get_full_env(base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a subprocess-safe environment with common tool paths appended."""

    env = dict(os.environ if base_env is None else base_env)
    pathsep = os.pathsep
    existing_paths = _split_path(env.get("PATH", ""), pathsep)
    merged_paths = list(existing_paths)

    for candidate in _candidate_paths(env):
        if not _contains_path(merged_paths, candidate):
            merged_paths.append(candidate)

    env["PATH"] = pathsep.join(merged_paths)
    return env


def get_command_availability(
    command: str, env: Mapping[str, str] | None = None
) -> CommandAvailability:
    """Return metadata-only availability information for a command."""

    full_env = get_full_env(env)
    resolved_path = shutil.which(command, path=full_env.get("PATH"))
    available = resolved_path is not None
    remediation = (
        f"Install `{command}` or add it to PATH before retrying."
        if not available
        else f"`{command}` is available for subprocess discovery."
    )
    return CommandAvailability(
        command=command,
        available=available,
        resolved_path=resolved_path,
        remediation=remediation,
    )


def _candidate_paths(env: Mapping[str, str]) -> list[str]:
    windows = _is_windows(env)
    candidates: list[str] = []
    home = _home_path(env)
    script_dir_name = "Scripts" if windows else "bin"

    for prefix in (env.get("VIRTUAL_ENV"), env.get("CONDA_PREFIX")):
        if prefix:
            candidates.append(_join_path(prefix, script_dir_name, windows=windows))

    python_user_base = env.get("PYTHONUSERBASE") or site.USER_BASE
    if python_user_base:
        candidates.append(_join_path(python_user_base, script_dir_name, windows=windows))

    candidates.append(str(Path(sys.executable).resolve().parent))

    if windows:
        appdata = env.get("APPDATA") or _join_path(str(home), "AppData", "Roaming", windows=True)
        candidates.extend(
            [
                _join_path(str(home), "bin", windows=True),
                _join_path(str(home), ".cargo", "bin", windows=True),
                _join_path(appdata, "npm", windows=True),
                _join_path(appdata, "Python", "Scripts", windows=True),
                _join_path(str(home), "scoop", "shims", windows=True),
            ]
        )
    else:
        candidates.extend(
            [
                _join_path(str(home), ".local", "bin", windows=False),
                _join_path(str(home), "bin", windows=False),
                _join_path(str(home), ".cargo", "bin", windows=False),
                _join_path(str(home), ".npm-global", "bin", windows=False),
            ]
        )

    return [candidate for candidate in candidates if candidate]


def _split_path(path_value: str, pathsep: str) -> list[str]:
    return [entry for entry in path_value.split(pathsep) if entry]


def _contains_path(paths: list[str], candidate: str) -> bool:
    normalized_candidate = _normalize_path(candidate)
    return any(_normalize_path(path) == normalized_candidate for path in paths)


def _normalize_path(path: str) -> str:
    expanded = os.path.expanduser(path)
    return os.path.normcase(os.path.normpath(expanded))


def _is_windows(env: Mapping[str, str]) -> bool:
    return os.pathsep == ";" or env.get("OS") == "Windows_NT"


def _home_path(env: Mapping[str, str]) -> Path:
    explicit_home = env.get("HOME") or env.get("USERPROFILE")
    if explicit_home:
        return Path(explicit_home)
    return Path.home()


def _join_path(*parts: str, windows: bool) -> str:
    if windows:
        return str(PureWindowsPath(parts[0], *parts[1:]))
    return str(Path(parts[0], *parts[1:]))
