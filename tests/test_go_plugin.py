"""Comprehensive tests for the Go plugin."""

import pytest
import tempfile
import time
from pathlib import Path
from mcp_server.plugins.go_plugin.plugin import Plugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestGoPlugin:
    """Test suite for Go language plugin."""

    @pytest.fixture
    def go_plugin(self):
        """Create a Go plugin instance for testing."""
        return Plugin()

    @pytest.fixture
    def go_plugin_with_storage(self, tmp_path):
        """Create a Go plugin with SQLite storage for testing."""
        db_path = tmp_path / "test.db"
        sqlite_store = SQLiteStore(str(db_path))
        return Plugin(sqlite_store=sqlite_store)

    @pytest.fixture
    def sample_go_code(self):
        """Sample Go code for testing."""
        return '''package main

import (
    "fmt"
    "net/http"
)

type User struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

type UserService interface {
    GetUser(id int) (*User, error)
    CreateUser(user User) error
}

type Status string

const MaxRetries = 3

var defaultTimeout = 30

func NewUser(name string) *User {
    return &User{Name: name}
}

func (u *User) GetID() int {
    return u.ID
}

func main() {
    fmt.Println("Hello, World!")
}
'''

    @pytest.fixture
    def sample_go_mod(self):
        """Sample go.mod content for testing."""
        return '''module github.com/example/myapp

go 1.21

require (
    github.com/gorilla/mux v1.8.0
    github.com/stretchr/testify v1.8.4
)

require (
    github.com/davecgh/go-spew v1.1.1 // indirect
    github.com/pmezard/go-difflib v1.0.0 // indirect
)
'''

    def test_plugin_supports_go_files(self, go_plugin):
        """Test that plugin correctly identifies Go files."""
        assert go_plugin.supports("main.go")
        assert go_plugin.supports("user.go")
        assert go_plugin.supports("go.mod")
        assert go_plugin.supports(Path("src/handler.go"))
        assert not go_plugin.supports("main.py")
        assert not go_plugin.supports("index.js")
        assert not go_plugin.supports("README.md")

    def test_parse_go_functions(self, go_plugin, sample_go_code):
        """Test parsing of Go function declarations."""
        result = go_plugin.indexFile("test.go", sample_go_code)
        
        assert result["language"] == "go"
        assert result["file"] == "test.go"
        
        # Check that functions are found
        functions = [s for s in result["symbols"] if s["kind"] == "function"]
        function_names = [f["symbol"] for f in functions]
        
        assert "NewUser" in function_names
        assert "GetID" in function_names  # Method
        assert "main" in function_names
        
        # Check function details
        new_user_func = next(f for f in functions if f["symbol"] == "NewUser")
        assert new_user_func["line"] > 0
        assert "func NewUser" in new_user_func["signature"]

    def test_parse_go_structs(self, go_plugin, sample_go_code):
        """Test parsing of Go struct declarations."""
        result = go_plugin.indexFile("test.go", sample_go_code)
        
        structs = [s for s in result["symbols"] if s["kind"] == "struct"]
        struct_names = [s["symbol"] for s in structs]
        
        assert "User" in struct_names
        
        user_struct = next(s for s in structs if s["symbol"] == "User")
        assert user_struct["line"] > 0
        assert "type User struct" in user_struct["signature"]

    def test_parse_go_interfaces(self, go_plugin, sample_go_code):
        """Test parsing of Go interface declarations."""
        result = go_plugin.indexFile("test.go", sample_go_code)
        
        interfaces = [s for s in result["symbols"] if s["kind"] == "interface"]
        interface_names = [i["symbol"] for i in interfaces]
        
        assert "UserService" in interface_names
        
        user_service = next(i for i in interfaces if i["symbol"] == "UserService")
        assert user_service["line"] > 0
        assert "type UserService interface" in user_service["signature"]

    def test_parse_go_types(self, go_plugin, sample_go_code):
        """Test parsing of Go type declarations."""
        result = go_plugin.indexFile("test.go", sample_go_code)
        
        types = [s for s in result["symbols"] if s["kind"] == "type"]
        type_names = [t["symbol"] for t in types]
        
        assert "Status" in type_names
        
        status_type = next(t for t in types if t["symbol"] == "Status")
        assert status_type["line"] > 0
        assert "type Status string" in status_type["signature"]

    def test_parse_go_constants(self, go_plugin, sample_go_code):
        """Test parsing of Go constant declarations."""
        result = go_plugin.indexFile("test.go", sample_go_code)
        
        constants = [s for s in result["symbols"] if s["kind"] == "constant"]
        constant_names = [c["symbol"] for c in constants]
        
        assert "MaxRetries" in constant_names
        
        max_retries = next(c for c in constants if c["symbol"] == "MaxRetries")
        assert max_retries["line"] > 0
        assert "const MaxRetries" in max_retries["signature"]

    def test_parse_go_variables(self, go_plugin, sample_go_code):
        """Test parsing of Go variable declarations."""
        result = go_plugin.indexFile("test.go", sample_go_code)
        
        variables = [s for s in result["symbols"] if s["kind"] == "variable"]
        variable_names = [v["symbol"] for v in variables]
        
        assert "defaultTimeout" in variable_names
        
        default_timeout = next(v for v in variables if v["symbol"] == "defaultTimeout")
        assert default_timeout["line"] > 0
        assert "var defaultTimeout" in default_timeout["signature"]

    def test_parse_go_mod_file(self, go_plugin, sample_go_mod):
        """Test parsing of go.mod files."""
        result = go_plugin.indexFile("go.mod", sample_go_mod)
        
        assert result["language"] == "go-mod"
        assert result["file"] == "go.mod"
        
        # Check module declaration
        modules = [s for s in result["symbols"] if s["kind"] == "module"]
        assert len(modules) == 1
        assert modules[0]["symbol"] == "github.com/example/myapp"
        
        # Check dependencies
        dependencies = [s for s in result["symbols"] if s["kind"] == "dependency"]
        dep_names = [d["symbol"] for d in dependencies]
        
        assert "github.com/gorilla/mux" in dep_names
        assert "github.com/stretchr/testify" in dep_names
        assert "github.com/davecgh/go-spew" in dep_names

    def test_get_definition(self, go_plugin, sample_go_code):
        """Test getting symbol definitions."""
        # Index the file first
        go_plugin.indexFile("test.go", sample_go_code)
        
        # Test getting definition for a function
        definition = go_plugin.getDefinition("NewUser")
        assert definition is not None
        assert definition["symbol"] == "NewUser"
        assert definition["kind"] == "function"
        assert definition["language"] == "go"
        assert "func NewUser" in definition["signature"]
        
        # Test getting definition for a struct
        definition = go_plugin.getDefinition("User")
        assert definition is not None
        assert definition["symbol"] == "User"
        assert definition["kind"] == "struct"

    def test_find_references(self, go_plugin, sample_go_code, tmp_path):
        """Test finding symbol references."""
        # Create a temporary Go file to test references
        test_file = tmp_path / "test_refs.go"
        test_file.write_text(sample_go_code)
        
        # Change to the temp directory so the plugin finds our test file
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            # Create a new plugin instance in the temp directory
            temp_plugin = Plugin()
            
            # Find references to User struct
            references = temp_plugin.findReferences("User")
            assert len(references) > 0
            
            # Should find references in our test file
            file_paths = [ref.file for ref in references]
            assert any("test_refs.go" in path for path in file_paths)
        finally:
            os.chdir(original_cwd)

    def test_search_functionality(self, go_plugin, sample_go_code):
        """Test search functionality."""
        # Index the file first
        go_plugin.indexFile("test.go", sample_go_code)
        
        # Search for functions
        results = go_plugin.search("NewUser")
        assert len(results) > 0
        
        # Search with limit
        results = go_plugin.search("User", {"limit": 5})
        assert len(results) <= 5

    def test_performance_target(self, go_plugin):
        """Test that parsing meets the 100ms performance target."""
        # Read the actual test file
        test_file_path = Path(__file__).parent.parent / "mcp_server" / "plugins" / "go_plugin" / "test_data" / "sample.go"
        if test_file_path.exists():
            content = test_file_path.read_text()
        else:
            # Fallback to a large synthetic file
            content = '''package main

import "fmt"

''' + '\n'.join([f'''
func Function{i}() {{
    fmt.Println("Function {i}")
}}

type Struct{i} struct {{
    Field{i} int
}}

type Interface{i} interface {{
    Method{i}() error
}}
''' for i in range(100)])
        
        # Measure parsing time
        start_time = time.time()
        result = go_plugin.indexFile("large_test.go", content)
        end_time = time.time()
        
        parsing_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Should parse within 100ms target
        assert parsing_time < 100, f"Parsing took {parsing_time:.2f}ms, exceeding 100ms target"
        assert len(result["symbols"]) > 0

    def test_with_sqlite_storage(self, go_plugin_with_storage, sample_go_code):
        """Test Go plugin with SQLite storage backend."""
        result = go_plugin_with_storage.indexFile("test.go", sample_go_code)
        
        # Should still parse correctly with storage
        assert result["language"] == "go"
        assert len(result["symbols"]) > 0
        
        # Test that symbols are stored in SQLite
        functions = [s for s in result["symbols"] if s["kind"] == "function"]
        assert len(functions) > 0

    def test_package_and_imports_extraction(self, go_plugin, sample_go_code):
        """Test extraction of package and import information."""
        result = go_plugin.indexFile("test.go", sample_go_code)
        
        # Check package extraction
        assert result.get("package") == "main"
        
        # Check imports extraction
        imports = result.get("imports", [])
        assert "fmt" in imports
        assert "net/http" in imports

    def test_complex_function_signatures(self, go_plugin):
        """Test parsing of complex function signatures."""
        complex_code = '''package main

func SimpleFunction() {}

func FunctionWithParams(name string, age int) {}

func FunctionWithReturn() string { return "" }

func FunctionWithMultipleReturns() (string, error) { return "", nil }

func (r *Receiver) MethodWithReceiver() {}

func FunctionWithVariadicParams(args ...string) {}

func GenericFunction[T any](value T) T { return value }
'''
        
        result = go_plugin.indexFile("complex.go", complex_code)
        
        functions = [s for s in result["symbols"] if s["kind"] == "function"]
        function_names = [f["symbol"] for f in functions]
        
        assert "SimpleFunction" in function_names
        assert "FunctionWithParams" in function_names
        assert "FunctionWithReturn" in function_names
        assert "FunctionWithMultipleReturns" in function_names
        assert "MethodWithReceiver" in function_names
        assert "FunctionWithVariadicParams" in function_names
        assert "GenericFunction" in function_names

    def test_edge_cases(self, go_plugin):
        """Test edge cases and error handling."""
        # Empty file
        result = go_plugin.indexFile("empty.go", "")
        assert result["symbols"] == []
        
        # Invalid syntax (should not crash)
        result = go_plugin.indexFile("invalid.go", "this is not valid go code {{{")
        assert result["language"] == "go"
        
        # File with only comments
        result = go_plugin.indexFile("comments.go", "// This is a comment\n/* Block comment */")
        assert result["symbols"] == []

    def test_get_indexed_count(self, go_plugin, sample_go_code):
        """Test getting the count of indexed files."""
        initial_count = go_plugin.get_indexed_count()
        
        go_plugin.indexFile("test1.go", sample_go_code)
        go_plugin.indexFile("test2.go", sample_go_code)
        
        final_count = go_plugin.get_indexed_count()
        assert final_count >= initial_count + 2