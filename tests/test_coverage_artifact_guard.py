"""Coverage artifact guard contract tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import check_coverage_artifacts


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Coverage Guard")
    _git(repo, "config", "user.email", "coverage@example.com")
    (repo / ".gitignore").write_text(".coverage*\ncoverage.xml\ncoverage.json\nhtmlcov/\n")
    (repo / "README.md").write_text("# temp\n")
    _git(repo, "add", ".gitignore", "README.md")
    _git(repo, "commit", "-m", "init")
    return repo


def test_untracked_generated_artifacts_do_not_fail(tmp_path: Path, capsys) -> None:
    repo = _init_repo(tmp_path)
    (repo / "coverage.xml").write_text("<coverage/>\n")
    (repo / "coverage.json").write_text("{}\n")
    (repo / ".coverage.unit").write_text("data\n")
    htmlcov = repo / "htmlcov"
    htmlcov.mkdir()
    (htmlcov / "index.html").write_text("<html></html>\n")

    assert check_coverage_artifacts.main(["--repo", str(repo)]) == 0
    assert capsys.readouterr().out.strip() == "coverage artifact guard passed"


def test_tracked_generated_artifacts_fail(tmp_path: Path, capsys) -> None:
    repo = _init_repo(tmp_path)
    (repo / "coverage.xml").write_text("<coverage/>\n")
    _git(repo, "add", "-f", "coverage.xml")
    _git(repo, "commit", "-m", "track coverage xml")

    assert check_coverage_artifacts.main(["--repo", str(repo)]) == 1
    output = capsys.readouterr().out
    assert "coverage artifact guard failed" in output
    assert "tracked: coverage.xml" in output


def test_staged_generated_artifacts_fail_without_being_tracked(tmp_path: Path, capsys) -> None:
    repo = _init_repo(tmp_path)
    htmlcov = repo / "htmlcov"
    htmlcov.mkdir()
    (htmlcov / "index.html").write_text("<html></html>\n")
    _git(repo, "add", "-f", "htmlcov/index.html")

    assert check_coverage_artifacts.main(["--repo", str(repo)]) == 1
    output = capsys.readouterr().out
    assert "coverage artifact guard failed" in output
    assert "staged: htmlcov/index.html" in output
