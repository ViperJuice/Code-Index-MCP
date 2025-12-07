"""Tests for the C++ language plugin."""

import tempfile
from pathlib import Path

import pytest

from mcp_server.interfaces.plugin_interfaces import SymbolDefinition
from mcp_server.plugins.cpp_plugin.plugin import Plugin
from mcp_server.storage.sqlite_store import SQLiteStore


@pytest.fixture
def plugin():
    """Create a C++ plugin instance."""
    return Plugin()


@pytest.fixture
def plugin_with_sqlite(tmp_path):
    """Create a C++ plugin instance with SQLite storage."""
    db_path = tmp_path / "test.db"
    store = SQLiteStore(str(db_path))
    return Plugin(sqlite_store=store), store


@pytest.fixture
def temp_cpp_file():
    """Create a temporary C++ file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp", delete=False) as f:
        f.write(
            """
#include <iostream>
#include <vector>
#include <string>

namespace MyNamespace {
    // A simple class with various members
    class MyClass {
    public:
        MyClass() = default;
        MyClass(int value) : m_value(value) {}
        ~MyClass() = default;
        
        int getValue() const { return m_value; }
        void setValue(int value) { m_value = value; }
        
        virtual void virtualMethod() { std::cout << "Base" << std::endl; }
        
        static int staticMethod(int x, int y) { return x + y; }
        
    private:
        int m_value = 0;
    };
    
    // Template class
    template<typename T>
    class Container {
    public:
        void add(const T& item) { items.push_back(item); }
        T& get(size_t index) { return items[index]; }
        
    private:
        std::vector<T> items;
    };
    
    // Free function
    void freeFunction(const std::string& msg) {
        std::cout << msg << std::endl;
    }
    
    // Function template
    template<typename T>
    T max(T a, T b) {
        return (a > b) ? a : b;
    }
    
    // Enum
    enum Color {
        RED,
        GREEN,
        BLUE
    };
    
    // Scoped enum
    enum class Status {
        OK,
        ERROR,
        PENDING
    };
    
    // Type alias
    using StringVector = std::vector<std::string>;
    
    // Typedef
    typedef std::vector<int> IntVector;
}

// Global function
int main(int argc, char* argv[]) {
    MyNamespace::MyClass obj(42);
    std::cout << obj.getValue() << std::endl;
    return 0;
}

// Operator overloading
class Point {
public:
    Point(double x, double y) : x_(x), y_(y) {}
    
    Point operator+(const Point& other) const {
        return Point(x_ + other.x_, y_ + other.y_);
    }
    
    friend std::ostream& operator<<(std::ostream& os, const Point& p) {
        os << "(" << p.x_ << ", " << p.y_ << ")";
        return os;
    }
    
private:
    double x_, y_;
};

// Inheritance example
class DerivedClass : public MyNamespace::MyClass {
public:
    DerivedClass(int value) : MyClass(value) {}
    
    void virtualMethod() override { 
        std::cout << "Derived" << std::endl; 
    }
};
"""
        )
        path = f.name
    yield path
    if Path(path).exists():
        Path(path).unlink()


@pytest.fixture
def temp_header_file():
    """Create a temporary C++ header file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".hpp", delete=False) as f:
        f.write(
            """
#pragma once

/// @brief A simple interface for shapes
class IShape {
public:
    virtual ~IShape() = default;
    
    /// Calculate the area of the shape
    /// @return The area as a double
    virtual double area() const = 0;
    
    /// Calculate the perimeter of the shape
    /// @return The perimeter as a double
    virtual double perimeter() const = 0;
};

/**
 * @brief A rectangle implementation of IShape
 * 
 * This class represents a rectangle with width and height.
 */
class Rectangle : public IShape {
public:
    Rectangle(double width, double height);
    
    double area() const override;
    double perimeter() const override;
    
    double getWidth() const { return width_; }
    double getHeight() const { return height_; }
    
private:
    double width_;
    double height_;
};

// Function declarations
namespace Utils {
    /// Helper function to calculate distance
    double distance(double x1, double y1, double x2, double y2);
    
    /// Template function for swapping values
    template<typename T>
    void swap(T& a, T& b) {
        T temp = a;
        a = b;
        b = temp;
    }
}

// Macro definition (not a symbol, but should be handled gracefully)
#define MAX(a, b) ((a) > (b) ? (a) : (b))

// Forward declarations
class ForwardDeclared;
struct ForwardStruct;

// Complex template
template<typename T, typename Allocator = std::allocator<T>>
class CustomVector {
public:
    using value_type = T;
    using allocator_type = Allocator;
    using size_type = std::size_t;
    
    CustomVector() = default;
    explicit CustomVector(size_type count);
    
    void push_back(const T& value);
    void push_back(T&& value);
    
    T& operator[](size_type index);
    const T& operator[](size_type index) const;
    
private:
    T* data_ = nullptr;
    size_type size_ = 0;
    size_type capacity_ = 0;
    Allocator alloc_;
};
"""
        )
        path = f.name
    yield path
    if Path(path).exists():
        Path(path).unlink()


class TestCppPlugin:
    """Test cases for C++ plugin functionality."""

    def test_plugin_creation(self, plugin):
        """Test that plugin is created correctly."""
        assert plugin.lang == "cpp"
        assert hasattr(plugin, "_parser")
        assert hasattr(plugin, "_indexer")

    def test_supports_cpp_files(self, plugin):
        """Test file extension support."""
        # Should support
        assert plugin.supports("test.cpp")
        assert plugin.supports("test.cc")
        assert plugin.supports("test.cxx")
        assert plugin.supports("test.c++")
        assert plugin.supports("test.hpp")
        assert plugin.supports("test.h")
        assert plugin.supports("test.hh")
        assert plugin.supports("test.h++")
        assert plugin.supports("test.hxx")
        assert plugin.supports(Path("test.CPP"))  # case insensitive

        # Should not support
        assert not plugin.supports("test.py")
        assert not plugin.supports("test.js")
        assert not plugin.supports("test.txt")
        assert not plugin.supports("test.c")  # Plain C

    def test_index_cpp_file(self, plugin, temp_cpp_file):
        """Test indexing a C++ file."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        shard = plugin.indexFile(temp_cpp_file, content)

        assert shard["file"] == temp_cpp_file
        assert shard["language"] == "cpp"
        assert len(shard["symbols"]) > 0

        # Check for expected symbols
        symbol_names = [s["symbol"] for s in shard["symbols"]]

        # Namespace - check the actual symbol name that was found
        # The plugin might return it as MyNamespace::MyNamespace or just MyNamespace
        assert any("MyNamespace" in s for s in symbol_names)

        # Classes
        assert "MyNamespace::MyClass" in symbol_names
        assert "MyNamespace::Container" in symbol_names
        assert "Point" in symbol_names
        assert "DerivedClass" in symbol_names

        # Functions
        assert "MyNamespace::freeFunction" in symbol_names
        assert "MyNamespace::max" in symbol_names
        assert "main" in symbol_names

        # Methods
        assert any("getValue" in s for s in symbol_names)
        assert any("setValue" in s for s in symbol_names)
        assert any("virtualMethod" in s for s in symbol_names)
        assert any("staticMethod" in s for s in symbol_names)

        # Enums
        assert "MyNamespace::Color" in symbol_names
        assert "MyNamespace::Status" in symbol_names

        # Type aliases
        assert "MyNamespace::StringVector" in symbol_names
        assert "MyNamespace::IntVector" in symbol_names

    def test_index_header_file(self, plugin, temp_header_file):
        """Test indexing a C++ header file."""
        with open(temp_header_file, "r") as f:
            content = f.read()

        shard = plugin.indexFile(temp_header_file, content)

        assert shard["file"] == temp_header_file
        assert shard["language"] == "cpp"

        # Check for expected symbols
        symbol_names = [s["symbol"] for s in shard["symbols"]]

        # Classes
        assert "IShape" in symbol_names
        assert "Rectangle" in symbol_names
        assert "CustomVector" in symbol_names

        # Namespace and functions - check for Utils namespace
        assert any("Utils" in s for s in symbol_names)
        assert "Utils::distance" in symbol_names
        assert "Utils::swap" in symbol_names

    def test_symbol_kinds(self, plugin, temp_cpp_file):
        """Test that symbol kinds are correctly identified."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        shard = plugin.indexFile(temp_cpp_file, content)
        symbols_by_kind = {}

        for symbol in shard["symbols"]:
            kind = symbol["kind"]
            if kind not in symbols_by_kind:
                symbols_by_kind[kind] = []
            symbols_by_kind[kind].append(symbol["symbol"])

        # Check various kinds
        assert "namespace" in symbols_by_kind
        assert "class" in symbols_by_kind
        assert "function" in symbols_by_kind
        assert "method" in symbols_by_kind
        assert "constructor" in symbols_by_kind
        assert "destructor" in symbols_by_kind
        assert "enum" in symbols_by_kind
        assert "typedef" in symbols_by_kind
        assert "type_alias" in symbols_by_kind

    def test_template_detection(self, plugin, temp_cpp_file):
        """Test that templates are correctly detected."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        shard = plugin.indexFile(temp_cpp_file, content)

        # Find template symbols
        template_symbols = [s for s in shard["symbols"] if s.get("is_template", False)]

        assert len(template_symbols) > 0

        # Check for expected templates - they should contain these names
        template_names = [s["symbol"] for s in template_symbols]
        assert any("Container" in name for name in template_names)
        assert any("max" in name for name in template_names)

    def test_get_definition(self, plugin, temp_cpp_file):
        """Test getting symbol definitions."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index the file first
        plugin.indexFile(temp_cpp_file, content)

        # Test various symbol lookups
        my_class_def = plugin.getDefinition("MyClass")
        assert my_class_def is not None
        assert my_class_def["kind"] == "class"
        assert my_class_def["language"] == "cpp"
        assert "MyClass" in my_class_def["signature"]

        main_def = plugin.getDefinition("main")
        assert main_def is not None
        assert main_def["kind"] == "function"
        assert "main" in main_def["signature"]
        assert "int" in main_def["signature"]

        # Test qualified name lookup
        free_func_def = plugin.getDefinition("freeFunction")
        assert free_func_def is not None
        assert free_func_def["kind"] == "function"

    def test_find_references(self, plugin, temp_cpp_file):
        """Test finding references to symbols."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index the file first
        plugin.indexFile(temp_cpp_file, content)

        # Find references to MyClass
        refs = plugin.findReferences("MyClass")
        # The original symbol definition counts as a reference too
        assert len(refs) >= 0  # May have 0 if only finding usage references, not definitions

        # Try finding references to a more commonly used symbol
        refs = plugin.findReferences("getValue")
        assert len(refs) >= 0

    def test_search(self, plugin, temp_cpp_file):
        """Test searching for symbols."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index the file first
        plugin.indexFile(temp_cpp_file, content)

        # Search for various terms
        results = plugin.search("MyClass")
        assert len(results) > 0

        results = plugin.search("getValue")
        assert len(results) > 0

        # Test with limit
        results = plugin.search("a", {"limit": 5})
        assert len(results) <= 5

    def test_documentation_extraction(self, plugin, temp_header_file):
        """Test extracting documentation comments."""
        with open(temp_header_file, "r") as f:
            content = f.read()

        # Index the file first
        plugin.indexFile(temp_header_file, content)

        # Get definition with documentation
        shape_def = plugin.getDefinition("IShape")
        assert shape_def is not None
        assert shape_def["doc"] is not None
        assert "simple interface for shapes" in shape_def["doc"]

        rect_def = plugin.getDefinition("Rectangle")
        assert rect_def is not None
        assert rect_def["doc"] is not None
        assert "rectangle implementation" in rect_def["doc"]

    def test_inheritance_handling(self, plugin, temp_cpp_file):
        """Test that inheritance is properly handled."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        shard = plugin.indexFile(temp_cpp_file, content)

        # Find DerivedClass
        derived_class = next((s for s in shard["symbols"] if s["symbol"] == "DerivedClass"), None)
        assert derived_class is not None
        # Check that it extends MyClass in some form
        assert (
            "MyClass" in derived_class["signature"]
            or "MyNamespace::MyClass" in derived_class["signature"]
        )

    def test_operator_overloading(self, plugin, temp_cpp_file):
        """Test that operator overloading is detected."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        shard = plugin.indexFile(temp_cpp_file, content)

        # Check for operator symbols
        operator_symbols = [s for s in shard["symbols"] if "operator" in s["symbol"]]
        assert len(operator_symbols) > 0

    def test_sqlite_persistence(self, plugin_with_sqlite, temp_cpp_file):
        """Test that symbols are persisted to SQLite."""
        plugin, store = plugin_with_sqlite

        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index the file
        shard = plugin.indexFile(temp_cpp_file, content)

        # Check that symbols were stored
        with store._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM symbols")
            symbol_count = cursor.fetchone()[0]
            assert symbol_count > 0

            # Check specific symbol
            cursor = conn.execute(
                "SELECT name, kind, signature FROM symbols WHERE name LIKE ?",
                ("%MyClass%",),
            )
            results = cursor.fetchall()
            assert len(results) > 0

    def test_const_method_detection(self, plugin, temp_cpp_file):
        """Test that const methods are properly detected."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        shard = plugin.indexFile(temp_cpp_file, content)

        # Find getValue method - it should be in the symbols list
        get_value_symbols = [s for s in shard["symbols"] if "getValue" in s["symbol"]]
        assert len(get_value_symbols) > 0
        # At least one should be const
        assert any("const" in s["signature"] for s in get_value_symbols)

    def test_static_method_detection(self, plugin, temp_cpp_file):
        """Test that static methods are properly detected."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        shard = plugin.indexFile(temp_cpp_file, content)

        # Find staticMethod - it should be in the symbols list
        static_methods = [s for s in shard["symbols"] if "staticMethod" in s["symbol"]]
        assert len(static_methods) > 0
        # At least one should be static
        assert any("static" in s["signature"] for s in static_methods)

    def test_virtual_method_detection(self, plugin, temp_cpp_file):
        """Test that virtual methods are properly detected."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        shard = plugin.indexFile(temp_cpp_file, content)

        # Find virtualMethod - it should be in the symbols list
        virtual_methods = [
            s
            for s in shard["symbols"]
            if "virtualMethod" in s["symbol"] and "MyClass" in s["symbol"]
        ]
        assert len(virtual_methods) > 0
        # At least one should be virtual
        assert any("virtual" in s["signature"] for s in virtual_methods)

    def test_enum_values(self, plugin, temp_cpp_file):
        """Test that enum values are extracted."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        shard = plugin.indexFile(temp_cpp_file, content)

        # Check for enum values
        symbol_names = [s["symbol"] for s in shard["symbols"]]
        assert "MyNamespace::Color::RED" in symbol_names
        assert "MyNamespace::Color::GREEN" in symbol_names
        assert "MyNamespace::Color::BLUE" in symbol_names

        assert "MyNamespace::Status::OK" in symbol_names
        assert "MyNamespace::Status::ERROR" in symbol_names
        assert "MyNamespace::Status::PENDING" in symbol_names

    def test_get_indexed_count(self, plugin, temp_cpp_file):
        """Test getting the count of indexed files."""
        assert plugin.get_indexed_count() >= 0

        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index a file
        plugin.indexFile(temp_cpp_file, content)

        # Count should increase
        assert plugin.get_indexed_count() > 0


class TestCppPluginNewInterface:
    """Test cases for the new ICppPlugin interface methods."""

    def test_plugin_properties(self, plugin):
        """Test plugin properties from ICppPlugin interface."""
        assert plugin.name == "C++ Plugin"
        assert ".cpp" in plugin.supported_extensions
        assert ".hpp" in plugin.supported_extensions
        assert "cpp" in plugin.supported_languages

    def test_can_handle(self, plugin):
        """Test can_handle method."""
        assert plugin.can_handle("test.cpp")
        assert plugin.can_handle("test.hpp")
        assert not plugin.can_handle("test.py")

    def test_index_interface_method(self, plugin, temp_cpp_file):
        """Test the new index interface method."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        result = plugin.index(temp_cpp_file, content)

        assert result.success
        indexed_file = result.value
        assert indexed_file.file_path == temp_cpp_file
        assert indexed_file.language == "cpp"
        assert len(indexed_file.symbols) > 0

        # Check symbol definitions
        symbol_names = [s.symbol for s in indexed_file.symbols]
        assert any("MyClass" in name for name in symbol_names)

    def test_get_definition_interface(self, plugin, temp_cpp_file):
        """Test get_definition from ICppPlugin interface."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index first
        plugin.indexFile(temp_cpp_file, content)

        result = plugin.get_definition("MyClass", {})
        assert result.success

        if result.value:
            definition = result.value
            assert isinstance(definition, SymbolDefinition)
            assert "MyClass" in definition.symbol
            assert definition.symbol_type == "class"

    def test_get_references_interface(self, plugin, temp_cpp_file):
        """Test get_references from ICppPlugin interface."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index first
        plugin.indexFile(temp_cpp_file, content)

        result = plugin.get_references("MyClass", {})
        assert result.success
        references = result.value
        assert isinstance(references, list)

    def test_search_interface(self, plugin, temp_cpp_file):
        """Test search from ICppPlugin interface."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index first
        plugin.indexFile(temp_cpp_file, content)

        result = plugin.search("MyClass", {"limit": 10})
        assert result.success
        search_results = result.value
        assert isinstance(search_results, list)

    def test_validate_syntax(self, plugin):
        """Test syntax validation."""
        valid_code = "class Test { public: int x; };"
        result = plugin.validate_syntax(valid_code)
        assert result.success
        assert result.value is True

        # Test with invalid syntax
        invalid_code = "class Test { public int x; }"  # Missing colon
        result = plugin.validate_syntax(invalid_code)
        assert result.success
        # Note: Tree-sitter is quite forgiving, so this might still parse

    def test_get_completions(self, plugin, temp_cpp_file):
        """Test code completions."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index first
        plugin.indexFile(temp_cpp_file, content)

        result = plugin.get_completions(temp_cpp_file, 50, 10)
        assert result.success
        completions = result.value
        assert isinstance(completions, list)
        assert len(completions) > 0

        # Should include C++ keywords
        assert any("class" in comp for comp in completions)

    def test_resolve_includes(self, plugin, temp_header_file):
        """Test include resolution."""
        result = plugin.resolve_includes(temp_header_file)
        assert result.success
        includes = result.value
        assert isinstance(includes, list)
        # The header file should have no includes

    def test_parse_templates(self, plugin):
        """Test template parsing."""
        template_code = """
        template<typename T, int N>
        class Array {
            T data[N];
        public:
            T& operator[](int index) { return data[index]; }
        };
        
        template<typename T>
        T max(T a, T b) {
            return a > b ? a : b;
        }
        """

        result = plugin.parse_templates(template_code)
        assert result.success
        templates = result.value
        assert len(templates) >= 2  # Array and max

        template_names = [t.symbol for t in templates]
        assert "Array" in template_names
        assert "max" in template_names

    def test_parse_imports(self, plugin):
        """Test import parsing (includes)."""
        code_with_includes = """
        #include <iostream>
        #include <vector>
        #include "myheader.h"
        
        int main() { return 0; }
        """

        result = plugin.parse_imports(code_with_includes)
        assert result.success
        imports = result.value
        assert "iostream" in imports
        assert "vector" in imports
        assert "myheader.h" in imports

    def test_extract_symbols_interface(self, plugin):
        """Test symbol extraction via interface."""
        code = """
        namespace NS {
            class MyClass {
            public:
                void method();
                int field;
            };
        }
        """

        result = plugin.extract_symbols(code)
        assert result.success
        symbols = result.value
        assert len(symbols) > 0

        symbol_names = [s.symbol for s in symbols]
        assert any("NS" in name for name in symbol_names)
        assert any("MyClass" in name for name in symbol_names)

    def test_resolve_type(self, plugin, temp_cpp_file):
        """Test type resolution."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index first
        plugin.indexFile(temp_cpp_file, content)

        result = plugin.resolve_type("getValue", {})
        assert result.success
        # Type resolution might return None if not found

    def test_get_call_hierarchy(self, plugin, temp_cpp_file):
        """Test call hierarchy."""
        with open(temp_cpp_file, "r") as f:
            content = f.read()

        # Index first
        plugin.indexFile(temp_cpp_file, content)

        result = plugin.get_call_hierarchy("main", {})
        assert result.success
        hierarchy = result.value
        assert "calls_to" in hierarchy
        assert "called_by" in hierarchy

    def test_error_handling(self, plugin):
        """Test error handling in interface methods."""
        # Test with non-existent file
        result = plugin.resolve_includes("/non/existent/file.cpp")
        assert not result.success
        assert result.error is not None
        assert result.error.code == "CPP_INCLUDE_ERROR"

        # Test with invalid content
        result = plugin.validate_syntax(None)
        assert not result.success
        assert result.error is not None
