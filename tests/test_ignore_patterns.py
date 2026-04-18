"""Tests for mcp_server/core/ignore_patterns.py — IgnorePatternManager and build_walker_filter."""

from pathlib import Path

import pytest

from mcp_server.core.ignore_patterns import IgnorePatternManager, build_walker_filter, EXCLUDED_DIR_PARTS


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


class TestExcludedDirParts:
    """EXCLUDED_DIR_PARTS must cover all expected directory names."""

    REQUIRED_DIRS = [
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        ".mcp-index", ".indexes", "dist", "build", ".ruff_cache",
        ".mypy_cache", "htmlcov", ".tox", ".pytest_cache", ".idea",
        ".vscode", ".gradle", ".next", ".nuxt", "target", "coverage",
    ]

    def test_excluded_dir_parts_completeness(self, tmp_path):
        f = build_walker_filter(tmp_path)
        for dir_name in self.REQUIRED_DIRS:
            path = tmp_path / dir_name / "some_file.py"
            assert f(path) is True, f"Expected {dir_name} to be excluded but it was not"

    def test_excluded_dir_parts_set_contains_required_dirs(self):
        for d in self.REQUIRED_DIRS:
            assert d in EXCLUDED_DIR_PARTS, f"{d} missing from EXCLUDED_DIR_PARTS"


class TestBuildWalkerFilter:
    """Tests for the build_walker_filter() function."""

    def test_gitignore_log_files_ignored(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n/secrets/\n")
        f = build_walker_filter(tmp_path)
        assert f(tmp_path / "foo.log") is True

    def test_gitignore_secrets_dir_ignored(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n/secrets/\n")
        f = build_walker_filter(tmp_path)
        assert f(tmp_path / "secrets" / "token.txt") is True

    def test_regular_python_file_not_ignored(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n/secrets/\n")
        f = build_walker_filter(tmp_path)
        assert f(tmp_path / "src" / "main.py") is False

    def test_non_ignored_code_files(self, tmp_path):
        """Code files not matched by gitignore or excluded dirs should return False."""
        f = build_walker_filter(tmp_path)
        for filename in ["main.py", "index.ts", "main.go", "lib.rs"]:
            path = tmp_path / "src" / filename
            assert f(path) is False, f"Expected {filename} to NOT be filtered"

    def test_excluded_dir_returns_true(self, tmp_path):
        f = build_walker_filter(tmp_path)
        assert f(tmp_path / "node_modules" / "pkg" / "index.js") is True
        assert f(tmp_path / "__pycache__" / "module.cpython-311.pyc") is True
        assert f(tmp_path / ".git" / "HEAD") is True


class TestWalkerIntegration:
    """Integration: EnhancedDispatcher.index_directory respects the walker filter."""

    def test_log_files_not_indexed(self, tmp_path):
        import os
        from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher

        # Create a minimal git-like structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def hello(): pass\n")
        (tmp_path / "app.log").write_text("log line\n")
        (tmp_path / ".gitignore").write_text("*.log\n")

        dispatcher = EnhancedDispatcher(tmp_path)
        stats = dispatcher.index_directory(tmp_path, recursive=True)

        # .log file should be ignored (by gitignore) — indexed_files should not include it
        # The .py file should be indexed
        assert stats.get("indexed_files", 0) >= 1
        assert stats.get("ignored_files", 0) >= 1
