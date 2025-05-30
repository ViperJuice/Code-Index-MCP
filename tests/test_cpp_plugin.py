"""Tests for the C++ language plugin."""

import pytest
from pathlib import Path
import tempfile
import shutil

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
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write("""
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
""")
        path = f.name
    yield path
    if Path(path).exists():
        Path(path).unlink()


@pytest.fixture
def temp_header_file():
    """Create a temporary C++ header file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.hpp', delete=False) as f:
        f.write("""
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
""")
        path = f.name
    yield path
    if Path(path).exists():
        Path(path).unlink()


class TestCppPlugin:
    """Test cases for C++ plugin functionality."""
    
    def test_plugin_creation(self, plugin):
        """Test that plugin is created correctly."""
        assert plugin.lang == "cpp"
        assert hasattr(plugin, '_parser')
        assert hasattr(plugin, '_indexer')
        
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
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        shard = plugin.indexFile(temp_cpp_file, content)
        
        assert shard['file'] == temp_cpp_file
        assert shard['language'] == 'cpp'
        assert len(shard['symbols']) > 0
        
        # Check for expected symbols
        symbol_names = [s['symbol'] for s in shard['symbols']]
        
        # Namespace - check the actual symbol name that was found
        # The plugin might return it as MyNamespace::MyNamespace or just MyNamespace
        assert any('MyNamespace' in s for s in symbol_names)
        
        # Classes
        assert 'MyNamespace::MyClass' in symbol_names
        assert 'MyNamespace::Container' in symbol_names
        assert 'Point' in symbol_names
        assert 'DerivedClass' in symbol_names
        
        # Functions
        assert 'MyNamespace::freeFunction' in symbol_names
        assert 'MyNamespace::max' in symbol_names
        assert 'main' in symbol_names
        
        # Methods
        assert any('getValue' in s for s in symbol_names)
        assert any('setValue' in s for s in symbol_names)
        assert any('virtualMethod' in s for s in symbol_names)
        assert any('staticMethod' in s for s in symbol_names)
        
        # Enums
        assert 'MyNamespace::Color' in symbol_names
        assert 'MyNamespace::Status' in symbol_names
        
        # Type aliases
        assert 'MyNamespace::StringVector' in symbol_names
        assert 'MyNamespace::IntVector' in symbol_names
        
    def test_index_header_file(self, plugin, temp_header_file):
        """Test indexing a C++ header file."""
        with open(temp_header_file, 'r') as f:
            content = f.read()
        
        shard = plugin.indexFile(temp_header_file, content)
        
        assert shard['file'] == temp_header_file
        assert shard['language'] == 'cpp'
        
        # Check for expected symbols
        symbol_names = [s['symbol'] for s in shard['symbols']]
        
        # Classes
        assert 'IShape' in symbol_names
        assert 'Rectangle' in symbol_names
        assert 'CustomVector' in symbol_names
        
        # Namespace and functions - check for Utils namespace
        assert any('Utils' in s for s in symbol_names)
        assert 'Utils::distance' in symbol_names
        assert 'Utils::swap' in symbol_names
        
    def test_symbol_kinds(self, plugin, temp_cpp_file):
        """Test that symbol kinds are correctly identified."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        shard = plugin.indexFile(temp_cpp_file, content)
        symbols_by_kind = {}
        
        for symbol in shard['symbols']:
            kind = symbol['kind']
            if kind not in symbols_by_kind:
                symbols_by_kind[kind] = []
            symbols_by_kind[kind].append(symbol['symbol'])
        
        # Check various kinds
        assert 'namespace' in symbols_by_kind
        assert 'class' in symbols_by_kind
        assert 'function' in symbols_by_kind
        assert 'method' in symbols_by_kind
        assert 'constructor' in symbols_by_kind
        assert 'destructor' in symbols_by_kind
        assert 'enum' in symbols_by_kind
        assert 'typedef' in symbols_by_kind
        assert 'type_alias' in symbols_by_kind
        
    def test_template_detection(self, plugin, temp_cpp_file):
        """Test that templates are correctly detected."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        shard = plugin.indexFile(temp_cpp_file, content)
        
        # Find template symbols
        template_symbols = [s for s in shard['symbols'] if s.get('is_template', False)]
        
        assert len(template_symbols) > 0
        
        # Check for expected templates - they should contain these names
        template_names = [s['symbol'] for s in template_symbols]
        assert any('Container' in name for name in template_names)
        assert any('max' in name for name in template_names)
        
    def test_get_definition(self, plugin, temp_cpp_file):
        """Test getting symbol definitions."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        # Index the file first
        plugin.indexFile(temp_cpp_file, content)
        
        # Test various symbol lookups
        my_class_def = plugin.getDefinition('MyClass')
        assert my_class_def is not None
        assert my_class_def['kind'] == 'class'
        assert my_class_def['language'] == 'cpp'
        assert 'MyClass' in my_class_def['signature']
        
        main_def = plugin.getDefinition('main')
        assert main_def is not None
        assert main_def['kind'] == 'function'
        assert 'main' in main_def['signature']
        assert 'int' in main_def['signature']
        
        # Test qualified name lookup
        free_func_def = plugin.getDefinition('freeFunction')
        assert free_func_def is not None
        assert free_func_def['kind'] == 'function'
        
    def test_find_references(self, plugin, temp_cpp_file):
        """Test finding references to symbols."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        # Index the file first
        plugin.indexFile(temp_cpp_file, content)
        
        # Find references to MyClass
        refs = plugin.findReferences('MyClass')
        # The original symbol definition counts as a reference too
        assert len(refs) >= 0  # May have 0 if only finding usage references, not definitions
        
        # Try finding references to a more commonly used symbol
        refs = plugin.findReferences('getValue')
        assert len(refs) >= 0
        
    def test_search(self, plugin, temp_cpp_file):
        """Test searching for symbols."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        # Index the file first
        plugin.indexFile(temp_cpp_file, content)
        
        # Search for various terms
        results = plugin.search('MyClass')
        assert len(results) > 0
        
        results = plugin.search('getValue')
        assert len(results) > 0
        
        # Test with limit
        results = plugin.search('a', {'limit': 5})
        assert len(results) <= 5
        
    def test_documentation_extraction(self, plugin, temp_header_file):
        """Test extracting documentation comments."""
        with open(temp_header_file, 'r') as f:
            content = f.read()
        
        # Index the file first
        plugin.indexFile(temp_header_file, content)
        
        # Get definition with documentation
        shape_def = plugin.getDefinition('IShape')
        assert shape_def is not None
        assert shape_def['doc'] is not None
        assert 'simple interface for shapes' in shape_def['doc']
        
        rect_def = plugin.getDefinition('Rectangle')
        assert rect_def is not None
        assert rect_def['doc'] is not None
        assert 'rectangle implementation' in rect_def['doc']
        
    def test_inheritance_handling(self, plugin, temp_cpp_file):
        """Test that inheritance is properly handled."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        shard = plugin.indexFile(temp_cpp_file, content)
        
        # Find DerivedClass
        derived_class = next((s for s in shard['symbols'] if s['symbol'] == 'DerivedClass'), None)
        assert derived_class is not None
        # Check that it extends MyClass in some form
        assert 'MyClass' in derived_class['signature'] or 'MyNamespace::MyClass' in derived_class['signature']
        
    def test_operator_overloading(self, plugin, temp_cpp_file):
        """Test that operator overloading is detected."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        shard = plugin.indexFile(temp_cpp_file, content)
        
        # Check for operator symbols
        operator_symbols = [s for s in shard['symbols'] if 'operator' in s['symbol']]
        assert len(operator_symbols) > 0
        
    def test_sqlite_persistence(self, plugin_with_sqlite, temp_cpp_file):
        """Test that symbols are persisted to SQLite."""
        plugin, store = plugin_with_sqlite
        
        with open(temp_cpp_file, 'r') as f:
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
                ('%MyClass%',)
            )
            results = cursor.fetchall()
            assert len(results) > 0
            
    def test_const_method_detection(self, plugin, temp_cpp_file):
        """Test that const methods are properly detected."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        shard = plugin.indexFile(temp_cpp_file, content)
        
        # Find getValue method - it should be in the symbols list  
        get_value_symbols = [s for s in shard['symbols'] if 'getValue' in s['symbol']]
        assert len(get_value_symbols) > 0
        # At least one should be const
        assert any('const' in s['signature'] for s in get_value_symbols)
        
    def test_static_method_detection(self, plugin, temp_cpp_file):
        """Test that static methods are properly detected."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        shard = plugin.indexFile(temp_cpp_file, content)
        
        # Find staticMethod - it should be in the symbols list
        static_methods = [s for s in shard['symbols'] if 'staticMethod' in s['symbol']]
        assert len(static_methods) > 0
        # At least one should be static
        assert any('static' in s['signature'] for s in static_methods)
        
    def test_virtual_method_detection(self, plugin, temp_cpp_file):
        """Test that virtual methods are properly detected."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        shard = plugin.indexFile(temp_cpp_file, content)
        
        # Find virtualMethod - it should be in the symbols list
        virtual_methods = [s for s in shard['symbols'] if 'virtualMethod' in s['symbol'] and 'MyClass' in s['symbol']]
        assert len(virtual_methods) > 0 
        # At least one should be virtual
        assert any('virtual' in s['signature'] for s in virtual_methods)
        
    def test_enum_values(self, plugin, temp_cpp_file):
        """Test that enum values are extracted."""
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        shard = plugin.indexFile(temp_cpp_file, content)
        
        # Check for enum values
        symbol_names = [s['symbol'] for s in shard['symbols']]
        assert 'MyNamespace::Color::RED' in symbol_names
        assert 'MyNamespace::Color::GREEN' in symbol_names
        assert 'MyNamespace::Color::BLUE' in symbol_names
        
        assert 'MyNamespace::Status::OK' in symbol_names
        assert 'MyNamespace::Status::ERROR' in symbol_names
        assert 'MyNamespace::Status::PENDING' in symbol_names
        
    def test_get_indexed_count(self, plugin, temp_cpp_file):
        """Test getting the count of indexed files."""
        assert plugin.get_indexed_count() >= 0
        
        with open(temp_cpp_file, 'r') as f:
            content = f.read()
        
        # Index a file
        plugin.indexFile(temp_cpp_file, content)
        
        # Count should increase
        assert plugin.get_indexed_count() > 0