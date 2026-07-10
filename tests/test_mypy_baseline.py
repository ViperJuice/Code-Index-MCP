"""Tests for the non-growing full-project mypy baseline."""

from pathlib import Path

import pytest

from scripts.check_mypy_baseline import (
    BaselineError,
    compare_counts,
    find_ignore_errors,
    parse_mypy_output,
)


def _output(*errors: str) -> str:
    return "\n".join([*errors, f"Found {len(errors)} errors in 1 file (checked 2 source files)"])


def test_shrinking_counts_passes() -> None:
    baseline = {"mcp_server/a.py": {"arg-type": 3, "assignment": 1}}
    current = {"mcp_server/a.py": {"arg-type": 2}}
    assert compare_counts(baseline, current) == []


def test_growing_count_fails() -> None:
    violations = compare_counts(
        {"mcp_server/a.py": {"arg-type": 1}},
        {"mcp_server/a.py": {"arg-type": 2}},
    )
    assert violations == ["error count grew: mcp_server/a.py [arg-type] 1 -> 2"]


def test_new_module_fails() -> None:
    violations = compare_counts({}, {"mcp_server/new.py": {"assignment": 1}})
    assert violations == ["new failing module: mcp_server/new.py"]


def test_new_error_code_fails() -> None:
    violations = compare_counts(
        {"mcp_server/a.py": {"arg-type": 1}},
        {"mcp_server/a.py": {"return-value": 1}},
    )
    assert violations == ["new error code: mcp_server/a.py [return-value] (1)"]


def test_malformed_mypy_output_fails() -> None:
    with pytest.raises(BaselineError, match="Malformed mypy error line"):
        parse_mypy_output("mcp_server/a.py: error: missing line and code")


def test_parser_counts_modules_and_codes() -> None:
    output = _output(
        "mcp_server/a.py:10: error: bad argument  [arg-type]",
        "mcp_server/a.py:12:5: error: bad assignment  [assignment]",
    )
    assert parse_mypy_output(output) == {"mcp_server/a.py": {"arg-type": 1, "assignment": 1}}


def test_project_ignore_errors_fails(tmp_path: Path) -> None:
    config = tmp_path / "pyproject.toml"
    config.write_text("[tool.mypy]\nignore_errors = true\n", encoding="utf-8")
    assert find_ignore_errors(config) == [
        "project-level [tool.mypy].ignore_errors=true is forbidden"
    ]


def test_override_ignore_errors_fails(tmp_path: Path) -> None:
    config = tmp_path / "pyproject.toml"
    config.write_text(
        "[[tool.mypy.overrides]]\nmodule = 'mcp_server.*'\nignore_errors = true\n",
        encoding="utf-8",
    )
    assert find_ignore_errors(config) == [
        "mypy override 0 sets ignore_errors=true; fix or baseline errors instead"
    ]
