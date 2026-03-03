"""Tests for repository language auto-detection."""

from pathlib import Path

from mcp_server.utils.language_detector import detect_repository_languages


def test_detect_repository_languages_counts_extensions(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('x')\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("print('y')\n", encoding="utf-8")
    (tmp_path / "c.ts").write_text("const x = 1\n", encoding="utf-8")

    result = detect_repository_languages(tmp_path, max_files=100, min_files=2)

    assert "python" in result.detected_languages
    assert "typescript" not in result.detected_languages
    assert result.counts.get("python") == 2
    assert result.counts.get("typescript") == 1


def test_detect_repository_languages_ignores_heavy_directories(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "ignored.py").write_text("print('no')\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('yes')\n", encoding="utf-8")
    (tmp_path / "src" / "util.py").write_text("print('yes')\n", encoding="utf-8")

    result = detect_repository_languages(tmp_path, max_files=100, min_files=1)

    assert result.counts.get("python") == 2


def test_detect_repository_languages_respects_max_files(tmp_path: Path):
    for i in range(20):
        (tmp_path / f"f{i}.py").write_text("print('x')\n", encoding="utf-8")

    result = detect_repository_languages(tmp_path, max_files=5, min_files=1)

    assert result.scanned_files == 5
    assert result.truncated is True
