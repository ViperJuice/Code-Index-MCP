from __future__ import annotations

from mcp_server.utils import subprocess_env


def test_get_full_env_preserves_vars_and_path_order(monkeypatch) -> None:
    monkeypatch.setattr(subprocess_env.os, "pathsep", ":")
    monkeypatch.setattr(subprocess_env, "site", type("Site", (), {"USER_BASE": "/userbase"})())
    monkeypatch.setattr(subprocess_env.sys, "executable", "/venv/bin/python")

    env = subprocess_env.get_full_env(
        {
            "PATH": "/usr/bin:/bin:/home/test/.cargo/bin",
            "HOME": "/home/test",
            "KEEP_ME": "1",
            "VIRTUAL_ENV": "/venv",
        }
    )

    path_parts = env["PATH"].split(":")
    assert env["KEEP_ME"] == "1"
    assert path_parts[:3] == ["/usr/bin", "/bin", "/home/test/.cargo/bin"]
    assert path_parts.count("/home/test/.cargo/bin") == 1
    assert "/venv/bin" in path_parts
    assert "/userbase/bin" in path_parts
    assert "/venv/bin" in path_parts


def test_get_full_env_adds_linux_and_conda_candidates_without_fs_checks(monkeypatch) -> None:
    monkeypatch.setattr(subprocess_env.os, "pathsep", ":")
    monkeypatch.setattr(subprocess_env, "site", type("Site", (), {"USER_BASE": "/userbase"})())
    monkeypatch.setattr(subprocess_env.sys, "executable", "/python/bin/python3")

    env = subprocess_env.get_full_env(
        {
            "PATH": "/usr/bin",
            "HOME": "/home/dev",
            "CONDA_PREFIX": "/conda",
        }
    )

    path_parts = env["PATH"].split(":")
    assert "/conda/bin" in path_parts
    assert "/home/dev/.local/bin" in path_parts
    assert "/home/dev/bin" in path_parts
    assert "/home/dev/.npm-global/bin" in path_parts
    assert "/home/dev/.cargo/bin" in path_parts


def test_get_full_env_respects_windows_separator_and_candidates(monkeypatch) -> None:
    monkeypatch.setattr(subprocess_env.os, "pathsep", ";")
    monkeypatch.setattr(
        subprocess_env,
        "site",
        type("Site", (), {"USER_BASE": r"C:\Users\Test\AppData\Roaming\Python"})(),
    )
    monkeypatch.setattr(subprocess_env.sys, "executable", r"C:\Python312\python.exe")

    env = subprocess_env.get_full_env(
        {
            "PATH": r"C:\Windows\System32",
            "USERPROFILE": r"C:\Users\Test",
            "APPDATA": r"C:\Users\Test\AppData\Roaming",
            "OS": "Windows_NT",
            "VIRTUAL_ENV": r"C:\venv",
        }
    )

    path_parts = env["PATH"].split(";")
    assert path_parts[0] == r"C:\Windows\System32"
    assert r"C:\venv\Scripts" in path_parts
    assert r"C:\Users\Test\AppData\Roaming\npm" in path_parts
    assert r"C:\Users\Test\.cargo\bin" in path_parts
    assert r"C:\Users\Test\AppData\Roaming\Python\Scripts" in path_parts


def test_get_command_availability_is_metadata_only(monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess_env,
        "get_full_env",
        lambda env=None: {"PATH": "/safe/bin", "TOKEN": "secret"},
    )
    monkeypatch.setattr(subprocess_env.shutil, "which", lambda command, path=None: "/safe/bin/git")

    availability = subprocess_env.get_command_availability("git")

    assert availability.command == "git"
    assert availability.available is True
    assert availability.resolved_path == "/safe/bin/git"
    assert "PATH" not in availability.remediation
    assert "secret" not in availability.remediation
