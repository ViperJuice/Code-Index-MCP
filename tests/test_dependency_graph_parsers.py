"""Tests for ecosystem dependency parsers (IF-0-P14-2 — SL-2.1)."""

from pathlib import Path

import pytest

from mcp_server.dependency_graph.parsers import (
    CargoTomlParser,
    GoModParser,
    NpmPackageJsonParser,
    PythonRequirementsParser,
)


# ---------------------------------------------------------------------------
# PythonRequirementsParser
# ---------------------------------------------------------------------------


def test_python_requirements_parser(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "requests==2.31.0\nflask>=2.0\n# comment\nnumpy\n"
    )
    parser = PythonRequirementsParser()
    assert parser.manifest_filename == "requirements.txt"
    result = parser.parse(tmp_path)
    assert result == {"requests", "flask", "numpy"}


def test_python_requirements_parser_empty(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("# only comments\n\n")
    result = PythonRequirementsParser().parse(tmp_path)
    assert result == set()


def test_python_requirements_parser_missing(tmp_path: Path) -> None:
    result = PythonRequirementsParser().parse(tmp_path)
    assert result == set()


# ---------------------------------------------------------------------------
# NpmPackageJsonParser
# ---------------------------------------------------------------------------


def test_npm_package_json_parser(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"name": "my-app", "dependencies": {"react": "^18", "lodash": "4.17"}, '
        '"devDependencies": {"jest": "29"}}'
    )
    parser = NpmPackageJsonParser()
    assert parser.manifest_filename == "package.json"
    result = parser.parse(tmp_path)
    assert result == {"react", "lodash", "jest"}


def test_npm_package_json_parser_no_deps(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "empty-pkg"}')
    result = NpmPackageJsonParser().parse(tmp_path)
    assert result == set()


def test_npm_package_json_parser_missing(tmp_path: Path) -> None:
    result = NpmPackageJsonParser().parse(tmp_path)
    assert result == set()


# ---------------------------------------------------------------------------
# GoModParser
# ---------------------------------------------------------------------------


def test_go_mod_parser(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text(
        "module github.com/myorg/myapp\n\ngo 1.21\n\n"
        "require (\n"
        "\tgithub.com/gin-gonic/gin v1.9.0\n"
        "\tgolang.org/x/sync v0.3.0\n"
        ")\n"
    )
    parser = GoModParser()
    assert parser.manifest_filename == "go.mod"
    result = parser.parse(tmp_path)
    assert result == {"github.com/gin-gonic/gin", "golang.org/x/sync"}


def test_go_mod_parser_single_require(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text(
        "module example.com/foo\n\ngo 1.20\n\nrequire example.com/bar v0.1.0\n"
    )
    result = GoModParser().parse(tmp_path)
    assert result == {"example.com/bar"}


def test_go_mod_parser_missing(tmp_path: Path) -> None:
    result = GoModParser().parse(tmp_path)
    assert result == set()


# ---------------------------------------------------------------------------
# CargoTomlParser
# ---------------------------------------------------------------------------


def test_cargo_toml_parser(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text(
        '[package]\nname = "my-crate"\nversion = "0.1.0"\n\n'
        "[dependencies]\nserde = { version = \"1\", features = [\"derive\"] }\ntokio = \"1.0\"\n\n"
        "[dev-dependencies]\npretty_assertions = \"1\"\n"
    )
    parser = CargoTomlParser()
    assert parser.manifest_filename == "Cargo.toml"
    result = parser.parse(tmp_path)
    assert result == {"serde", "tokio", "pretty_assertions"}


def test_cargo_toml_parser_missing(tmp_path: Path) -> None:
    result = CargoTomlParser().parse(tmp_path)
    assert result == set()
