"""Tests for mcp_server/core/ignore_patterns.py — IgnorePatternManager."""

from pathlib import Path

import pytest

from mcp_server.core.ignore_patterns import IgnorePatternManager


class TestDefaultPatterns:
    """When no .mcp-index-ignore file is present, built-in defaults apply."""

    def test_default_patterns_are_loaded(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        assert len(manager.get_mcp_ignore_patterns()) > 0

    def test_ignores_pyc_files(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path("some/module.pyc")) is True

    def test_ignores_files_under_vendor_directory(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path("vendor/lib.py")) is True

    def test_ignores_files_under_test_workspace(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path("test_workspace/repo/file.py")) is True

    def test_ignores_protobuf_generated_files(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path("protos/service_pb2.py")) is True
        assert manager.should_ignore(Path("protos/service_pb2_grpc.py")) is True

    def test_ignores_env_files(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path(".env")) is True

    def test_ignores_dotenv_variants(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path(".env.local")) is True

    def test_does_not_ignore_regular_python_source_file(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path("src/main.py")) is False

    def test_does_not_ignore_test_source_file_outside_special_dirs(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path("tests/test_server.py")) is False


class TestCustomIgnoreFile:
    """When .mcp-index-ignore exists its patterns replace defaults."""

    def test_patterns_from_file_are_loaded(self, tmp_path):
        (tmp_path / ".mcp-index-ignore").write_text("*.foo\n*.bar\n# comment\n\n")
        manager = IgnorePatternManager(root_path=tmp_path)
        patterns = manager.get_mcp_ignore_patterns()
        assert "*.foo" in patterns
        assert "*.bar" in patterns

    def test_comments_and_blank_lines_excluded(self, tmp_path):
        (tmp_path / ".mcp-index-ignore").write_text("# skip this\n\n*.skip\n")
        manager = IgnorePatternManager(root_path=tmp_path)
        patterns = manager.get_mcp_ignore_patterns()
        assert "# skip this" not in patterns
        assert "" not in patterns

    def test_custom_pattern_ignores_matching_file(self, tmp_path):
        (tmp_path / ".mcp-index-ignore").write_text("*.foo\n")
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path("thing.foo")) is True

    def test_custom_pattern_does_not_ignore_non_matching_file(self, tmp_path):
        (tmp_path / ".mcp-index-ignore").write_text("*.foo\n")
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path("thing.py")) is False


class TestGitignoreIntegration:
    """Patterns from .gitignore are also loaded and respected."""

    def test_gitignore_patterns_loaded(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\ndist/\n")
        manager = IgnorePatternManager(root_path=tmp_path)
        gi_patterns = manager.get_gitignore_patterns()
        assert "*.log" in gi_patterns
        assert "dist/" in gi_patterns

    def test_gitignore_pattern_ignores_file(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n")
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.should_ignore(Path("server.log")) is True

    def test_gitignore_comments_excluded(self, tmp_path):
        (tmp_path / ".gitignore").write_text("# version control\n*.log\n")
        manager = IgnorePatternManager(root_path=tmp_path)
        gi_patterns = manager.get_gitignore_patterns()
        assert "# version control" not in gi_patterns

    def test_no_gitignore_returns_empty_gitignore_patterns(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        assert manager.get_gitignore_patterns() == []


class TestAbsolutePathHandling:
    """should_ignore handles absolute paths by making them relative to root."""

    def test_absolute_path_under_root_matches_default_pattern(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        abs_pyc = tmp_path / "pkg" / "module.pyc"
        assert manager.should_ignore(abs_pyc) is True

    def test_absolute_regular_file_not_ignored(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        abs_py = tmp_path / "src" / "main.py"
        assert manager.should_ignore(abs_py) is False

    def test_absolute_path_outside_root_does_not_crash(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        outside = Path("/some/other/place/module.pyc")
        result = manager.should_ignore(outside)
        assert isinstance(result, bool)


class TestGetPatterns:
    def test_get_patterns_returns_combined_list(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n")
        (tmp_path / ".mcp-index-ignore").write_text("*.foo\n")
        manager = IgnorePatternManager(root_path=tmp_path)
        all_patterns = manager.get_patterns()
        assert "*.log" in all_patterns
        assert "*.foo" in all_patterns

    def test_reload_picks_up_new_ignore_file(self, tmp_path):
        manager = IgnorePatternManager(root_path=tmp_path)
        initial_count = len(manager.get_mcp_ignore_patterns())
        (tmp_path / ".mcp-index-ignore").write_text("*.custom\n")
        manager.reload()
        assert "*.custom" in manager.get_mcp_ignore_patterns()
