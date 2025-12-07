"""Test cases for the Go plugin."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from mcp_server.plugins.go_plugin import Plugin as GoPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestGoPlugin:
    """Test cases for Go plugin functionality."""

    @pytest.fixture
    def temp_go_project(self):
        """Create a temporary Go project for testing."""
        # Save current directory
        original_dir = os.getcwd()

        # Create temporary directory
        test_dir = tempfile.mkdtemp(prefix="go_test_")
        os.chdir(test_dir)

        # Create go.mod
        go_mod = """module example.com/testapp

go 1.21

require github.com/gorilla/mux v1.8.0
"""
        Path("go.mod").write_text(go_mod)

        # Create a simple Go file
        main_go = """package main

import "fmt"

// Config holds application configuration
type Config struct {
    Port string
    Host string
}

// Runnable defines something that can be run
type Runnable interface {
    Run() error
    Stop() error
}

// Server implements the Runnable interface
type Server struct {
    config *Config
}

// NewServer creates a new server
func NewServer(config *Config) *Server {
    return &Server{config: config}
}

// Run starts the server
func (s *Server) Run() error {
    fmt.Printf("Server running on %s:%s\\n", s.config.Host, s.config.Port)
    return nil
}

// Stop stops the server
func (s *Server) Stop() error {
    fmt.Println("Server stopped")
    return nil
}

func main() {
    config := &Config{
        Port: "8080",
        Host: "localhost",
    }
    server := NewServer(config)
    server.Run()
}
"""
        Path("main.go").write_text(main_go)

        # Create a package directory
        os.makedirs("pkg/utils", exist_ok=True)
        utils_go = """package utils

// StringPtr returns a pointer to a string
func StringPtr(s string) *string {
    return &s
}

// IntPtr returns a pointer to an int
func IntPtr(i int) *int {
    return &i
}
"""
        Path("pkg/utils/utils.go").write_text(utils_go)

        yield test_dir

        # Cleanup
        os.chdir(original_dir)
        shutil.rmtree(test_dir)

    def test_plugin_initialization(self, temp_go_project):
        """Test plugin can be initialized."""
        plugin = GoPlugin(sqlite_store=SQLiteStore(":memory:"))
        assert plugin.lang == "go"
        assert plugin.supports("main.go")
        assert plugin.supports("test.go")
        assert not plugin.supports("test.py")

    def test_module_resolution(self, temp_go_project):
        """Test Go module resolution."""
        plugin = GoPlugin()
        module_info = plugin.get_module_info()

        assert module_info is not None
        assert module_info["name"] == "example.com/testapp"
        assert module_info["version"] == "1.21"
        assert len(module_info["dependencies"]) == 1
        assert module_info["dependencies"][0]["module"] == "github.com/gorilla/mux"

    def test_file_indexing(self, temp_go_project):
        """Test indexing Go files."""
        plugin = GoPlugin(sqlite_store=SQLiteStore(":memory:"))

        content = Path("main.go").read_text()
        shard = plugin.indexFile("main.go", content)

        assert shard["file"] == "main.go"
        assert shard["language"] == "go"
        assert len(shard["symbols"]) > 0

        # Check specific symbols
        symbol_names = {s["symbol"] for s in shard["symbols"]}
        assert "Config" in symbol_names
        assert "Server" in symbol_names
        assert "NewServer" in symbol_names
        assert "Run" in symbol_names
        assert "Stop" in symbol_names

    def test_interface_checking(self, temp_go_project):
        """Test interface satisfaction checking."""
        plugin = GoPlugin()

        # Index the file first
        content = Path("main.go").read_text()
        plugin.indexFile("main.go", content)

        # Check interface implementation
        result = plugin.check_interface_implementation("Server", "Runnable")

        assert result is not None
        assert result["satisfied"] is True
        assert "Run" in result["implemented_methods"]
        assert "Stop" in result["implemented_methods"]
        assert len(result["missing_methods"]) == 0

    def test_symbol_definition(self, temp_go_project):
        """Test finding symbol definitions."""
        plugin = GoPlugin()

        # Index files
        content = Path("main.go").read_text()
        plugin.indexFile("main.go", content)

        # Find definition
        definition = plugin.getDefinition("NewServer")

        assert definition is not None
        assert definition["symbol"] == "NewServer"
        assert definition["kind"] == "function"
        assert definition["language"] == "go"
        assert "main.go" in definition["defined_in"]

    def test_find_references(self, temp_go_project):
        """Test finding references to symbols."""
        plugin = GoPlugin()

        # Index files
        for go_file in Path(".").rglob("*.go"):
            content = go_file.read_text()
            plugin.indexFile(str(go_file), content)

        # Find references
        refs = plugin.findReferences("Config")

        assert len(refs) > 0
        assert any(ref.file == "main.go" for ref in refs)

    def test_package_analysis(self, temp_go_project):
        """Test package analysis functionality."""
        plugin = GoPlugin()

        # Index utils package
        utils_file = Path("pkg/utils/utils.go")
        content = utils_file.read_text()
        plugin.indexFile(str(utils_file), content)

        # Get package info
        package_info = plugin.get_package_info("pkg/utils")

        assert package_info is not None
        assert package_info["name"] == "utils"
        assert "StringPtr" in package_info["functions"]
        assert "IntPtr" in package_info["functions"]

    def test_search_functionality(self, temp_go_project):
        """Test search functionality."""
        plugin = GoPlugin()

        # Index all files
        for go_file in Path(".").rglob("*.go"):
            content = go_file.read_text()
            plugin.indexFile(str(go_file), content)

        # Search for symbols
        results = list(plugin.search("Server", {"limit": 10}))

        assert len(results) > 0
        assert any("main.go" in result["file"] for result in results)

    def test_import_resolution(self, temp_go_project):
        """Test import path resolution."""
        plugin = GoPlugin()

        # Test standard library import
        stdlib_path = plugin.module_resolver.resolve_import("fmt")
        assert stdlib_path == "stdlib:fmt"

        # Test external import
        external_path = plugin.module_resolver.resolve_import("github.com/gorilla/mux")
        assert external_path == "external:github.com/gorilla/mux"

        # Test internal import
        internal_path = plugin.module_resolver.resolve_import("example.com/testapp/pkg/utils")
        assert "pkg/utils" in internal_path
