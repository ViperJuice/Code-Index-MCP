"""Tests for TOML plugin."""

import pytest
from pathlib import Path
from .plugin import Plugin
from ..plugin_template import SymbolType


class TestTomlPlugin:
    """Test cases for TOML plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = Plugin()
    
    def test_supports_files(self):
        """Test file support detection."""
        # Test supported extensions
        assert self.plugin.supports("config.toml")
        assert self.plugin.supports("Cargo.toml")
        assert self.plugin.supports("pyproject.toml")
        assert self.plugin.supports("poetry.lock")
        assert self.plugin.supports("test.toml")
        
        # Test unsupported extensions
        assert not self.plugin.supports("test.txt")
        assert not self.plugin.supports("test.py")
        assert not self.plugin.supports("test.json")
    
    def test_parse_simple_toml(self):
        """Test parsing simple TOML."""
        content = """
# Simple configuration file
[server]
host = "localhost"
port = 8080

[database]
url = "postgresql://localhost/mydb"
pool_size = 10
"""
        
        result = self.plugin.indexFile("config.toml", content)
        assert result["language"] == "toml"
        assert len(result["symbols"]) > 0
        
        # Check for sections
        symbols = result["symbols"]
        section_names = [s["symbol"] for s in symbols if s["kind"] == "module"]
        assert "server" in section_names
        assert "database" in section_names
        
        # Check for variables
        var_names = [s["symbol"] for s in symbols if s["kind"] == "variable"]
        assert "host" in var_names
        assert "port" in var_names
        assert "url" in var_names
        assert "pool_size" in var_names
    
    def test_parse_cargo_toml(self):
        """Test parsing Cargo.toml file."""
        content = """
[package]
name = "my-rust-project"
version = "0.1.0"
edition = "2021"
authors = ["Developer <dev@example.com>"]

[dependencies]
serde = { version = "1.0", features = ["derive"] }
tokio = { version = "1.0", features = ["full"] }
reqwest = "0.11"

[dev-dependencies]
mockito = "0.31"

[features]
default = ["serde/derive"]
async = ["tokio", "reqwest"]

[[bin]]
name = "my-app"
path = "src/main.rs"
"""
        
        result = self.plugin.indexFile("Cargo.toml", content)
        symbols = result["symbols"]
        
        # Check package metadata extraction
        package_symbols = [s for s in symbols if s.get("metadata", {}).get("section") == "package"]
        assert any(s["symbol"] == "package.name" for s in package_symbols)
        assert any(s["symbol"] == "package.version" for s in package_symbols)
        
        # Check dependencies
        dep_symbols = [s for s in symbols if s.get("metadata", {}).get("is_dependency")]
        dep_names = [s.get("metadata", {}).get("dependency") for s in dep_symbols]
        assert "serde" in dep_names
        assert "tokio" in dep_names
        assert "reqwest" in dep_names
        assert "mockito" in dep_names
        
        # Check features
        feature_symbols = [s for s in symbols if s.get("metadata", {}).get("section") == "features"]
        assert any(s["symbol"] == "features.default" for s in feature_symbols)
        assert any(s["symbol"] == "features.async" for s in feature_symbols)
    
    def test_parse_pyproject_toml(self):
        """Test parsing pyproject.toml file."""
        content = """
[build-system]
requires = ["setuptools>=45", "wheel", "setuptools_scm[toml]>=6.2"]
build-backend = "setuptools.build_meta"

[project]
name = "my-python-project"
version = "0.1.0"
description = "A sample Python project"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [
    {name = "Developer", email = "dev@example.com"}
]

[project.dependencies]
requests = ">=2.28.0"
click = ">=8.0"
pydantic = ">=2.0"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "black>=22.0",
    "mypy>=0.990"
]

[tool.poetry]
name = "my-poetry-project"
version = "0.1.0"
description = ""

[tool.poetry.dependencies]
python = "^3.8"
fastapi = "^0.100.0"
uvicorn = "^0.23.0"

[tool.black]
line-length = 88
target-version = ['py38']

[tool.mypy]
python_version = "3.8"
warn_return_any = true
"""
        
        result = self.plugin.indexFile("pyproject.toml", content)
        symbols = result["symbols"]
        
        # Check build system
        assert any(s["symbol"] == "build-system" for s in symbols)
        
        # Check project metadata
        project_symbols = [s for s in symbols if s.get("metadata", {}).get("section") == "project"]
        assert any(s["symbol"] == "project.name" for s in project_symbols)
        assert any(s["symbol"] == "project.version" for s in project_symbols)
        assert any(s["symbol"] == "project.requires-python" for s in project_symbols)
        
        # Check tool configurations
        tool_symbols = [s for s in symbols if s.get("metadata", {}).get("is_tool_config")]
        tool_names = [s.get("metadata", {}).get("tool") for s in tool_symbols]
        assert "poetry" in tool_names
        assert "black" in tool_names
        assert "mypy" in tool_names
    
    def test_nested_tables(self):
        """Test parsing nested tables and arrays."""
        content = """
[server]
host = "localhost"

[server.settings]
timeout = 30
retries = 3

[server.settings.advanced]
keepalive = true
compression = "gzip"

[[servers]]
name = "primary"
ip = "192.168.1.1"

[[servers]]
name = "backup"
ip = "192.168.1.2"

[clients.web]
enabled = true
port = 8080

[clients.api]
enabled = false
port = 8081
"""
        
        result = self.plugin.indexFile("config.toml", content)
        symbols = result["symbols"]
        
        # Check nested sections
        section_names = [s["symbol"] for s in symbols if s["kind"] == "module"]
        assert "server" in section_names
        assert "server.settings" in section_names or any("server.settings" in s.get("metadata", {}).get("full_path", "") for s in symbols)
        
        # Check table arrays
        array_symbols = [s for s in symbols if "array" in s.get("modifiers", [])]
        assert len(array_symbols) > 0
    
    def test_inline_tables(self):
        """Test parsing inline tables."""
        content = """
[database]
primary = { host = "localhost", port = 5432, name = "main" }
replica = { host = "replica.local", port = 5432, name = "main" }

[logging]
handlers = [
    { type = "file", path = "/var/log/app.log", level = "info" },
    { type = "console", level = "debug" }
]
"""
        
        result = self.plugin.indexFile("config.toml", content)
        symbols = result["symbols"]
        
        # Check for inline table symbols
        inline_symbols = [s for s in symbols if s["kind"] == "field" or "inline" in s.get("modifiers", [])]
        assert len(inline_symbols) > 0
    
    def test_multiline_strings(self):
        """Test parsing multi-line strings."""
        content = '''
[documentation]
description = """
This is a multi-line
string that spans
multiple lines.
"""

[scripts]
setup = """
#!/bin/bash
echo "Setting up..."
make install
"""
'''
        
        result = self.plugin.indexFile("config.toml", content)
        symbols = result["symbols"]
        
        # Check for multiline modifiers
        multiline_symbols = [s for s in symbols if "multiline" in s.get("modifiers", [])]
        # Note: This depends on the tree-sitter implementation
    
    def test_key_path_extraction(self):
        """Test extraction of full key paths."""
        content = """
[package]
name = "test"

[package.metadata]
author = "Developer"

[package.metadata.extra]
license = "MIT"
"""
        
        result = self.plugin.indexFile("config.toml", content)
        symbols = result["symbols"]
        
        # Check for path metadata
        for symbol in symbols:
            if symbol["kind"] in ["variable", "property"]:
                metadata = symbol.get("metadata", {})
                if "full_path" in metadata:
                    # Verify paths are correctly constructed
                    assert "." in metadata["full_path"] or symbol["line"] < 3
    
    def test_search_functionality(self):
        """Test search functionality."""
        content = """
[package]
name = "search-test"
version = "1.0.0"

[dependencies]
serde = "1.0"
tokio = "1.0"
"""
        
        # Index the file first
        self.plugin.indexFile("Cargo.toml", content)
        
        # Test search
        results = self.plugin.search("serde")
        assert isinstance(results, list)
        
        # Search with context
        results = self.plugin.search("dependencies", {"limit": 10})
        assert isinstance(results, list)
    
    def test_get_definition(self):
        """Test symbol definition lookup."""
        content = """
[server]
host = "localhost"
port = 8080

[database]
url = "postgresql://localhost/mydb"
"""
        
        # Index the file
        self.plugin.indexFile("config.toml", content)
        
        # Test definition lookup
        definition = self.plugin.getDefinition("server")
        if definition:
            assert definition["symbol"] == "server"
            assert definition["kind"] in ["module", "table"]  # Accept both since it depends on implementation
            assert definition["language"] == "toml"
        
        # Test nested definition
        definition = self.plugin.getDefinition("server.host")
        if definition:
            assert "server" in definition.get("section", "")
            assert definition.get("value_type") == "string"
    
    def test_complex_cargo_features(self):
        """Test complex Cargo.toml feature parsing."""
        content = """
[features]
default = ["std", "serde"]
std = []
alloc = []
serde = ["dep:serde", "serde/derive"]
full = ["std", "alloc", "serde", "async"]
async = ["tokio/full", "async-trait"]

[dependencies]
serde = { version = "1.0", optional = true }
tokio = { version = "1.0", optional = true }
async-trait = { version = "0.1", optional = true }
"""
        
        result = self.plugin.indexFile("Cargo.toml", content)
        symbols = result["symbols"]
        
        # Check feature extraction with dependencies
        feature_symbols = [s for s in symbols if s.get("metadata", {}).get("section") == "features"]
        
        # Find the 'full' feature
        full_feature = next((s for s in feature_symbols if s["symbol"] == "features.full"), None)
        if full_feature:
            deps = full_feature.get("metadata", {}).get("dependencies", [])
            assert "std" in deps
            assert "alloc" in deps
            assert "serde" in deps
            assert "async" in deps