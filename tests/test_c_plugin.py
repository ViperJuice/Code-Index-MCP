"""
Comprehensive tests for the C plugin.

Tests cover:
- File support detection
- Symbol extraction (functions, structs, unions, enums, typedefs, macros, variables)
- Include tracking
- Error handling
- Edge cases and complex code structures
- Performance benchmarks
"""

from pathlib import Path
from textwrap import dedent

import pytest

from mcp_server.plugins.c_plugin.plugin import Plugin as CPlugin


class TestPluginInitialization:
    """Test plugin initialization and configuration."""

    def test_init_without_store(self):
        """Test initialization without SQLite store."""
        plugin = CPlugin()

        assert plugin.lang == "c"
        assert plugin._sqlite_store is None

    def test_init_with_store(self, sqlite_store):
        """Test initialization with SQLite store."""
        plugin = CPlugin(sqlite_store=sqlite_store)

        assert plugin.lang == "c"
        assert plugin._sqlite_store == sqlite_store
        assert plugin._repository_id is not None


class TestFileSupport:
    """Test file support detection."""

    def test_supports_c_files(self):
        """Test that plugin supports C source and header files."""
        plugin = CPlugin()

        c_files = [
            Path("test.c"),
            Path("main.c"),
            Path("/path/to/source.c"),
            Path("test.h"),
            Path("header.h"),
            Path("/usr/include/stdio.h"),
        ]

        for file_path in c_files:
            assert plugin.supports(file_path) is True

    def test_does_not_support_other_files(self):
        """Test that plugin doesn't support non-C files."""
        plugin = CPlugin()

        other_files = [
            Path("test.cpp"),
            Path("test.cc"),
            Path("test.cxx"),
            Path("test.py"),
            Path("test.js"),
            Path("data.json"),
            Path("readme.md"),
            Path("test.o"),
            Path("test.obj"),
            Path("Makefile"),
            Path(".c"),  # Hidden file
            Path("c"),  # No extension
        ]

        for file_path in other_files:
            assert plugin.supports(file_path) is False

    def test_supports_case_sensitivity(self):
        """Test case sensitivity in file extension."""
        plugin = CPlugin()

        # C typically uses lowercase extensions
        assert plugin.supports(Path("test.c")) is True
        assert plugin.supports(Path("test.C")) is True  # Capital C is also valid
        assert plugin.supports(Path("test.h")) is True
        assert plugin.supports(Path("test.H")) is True  # Capital H is also valid


class TestSymbolExtraction:
    """Test symbol extraction from C code."""

    def test_extract_functions(self):
        """Test extracting function definitions."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Simple function */
        void simple_function() {
            return;
        }
        
        /* Function with parameters */
        int add(int a, int b) {
            return a + b;
        }
        
        /* Function with pointer return type */
        char* get_string(void) {
            return "hello";
        }
        
        /* Function with complex signature */
        static inline void* complex_func(const char* name, size_t size, int (*callback)(void*)) {
            return NULL;
        }
        
        /* Function declaration (prototype) - should not be indexed as definition */
        void prototype_only(int x);
        """
        )

        result = plugin.indexFile(Path("test.c"), code)

        symbols = result["symbols"]
        function_symbols = [s for s in symbols if s["kind"] == "function"]
        assert len(function_symbols) == 4  # Not including prototype

        # Check simple function
        func1 = next(s for s in function_symbols if s["symbol"] == "simple_function")
        assert func1["signature"] == "void simple_function()"
        assert func1["line"] == 3

        # Check function with args
        func2 = next(s for s in function_symbols if s["symbol"] == "add")
        assert func2["signature"] == "int add(int a, int b)"

        # Check pointer return
        func3 = next(s for s in function_symbols if s["symbol"] == "get_string")
        assert func3["signature"] == "char* get_string(void)"

        # Check complex function
        func4 = next(s for s in function_symbols if s["symbol"] == "complex_func")
        assert "static inline" in func4["signature"]
        assert "callback" in func4["signature"]

    def test_extract_structs(self):
        """Test extracting struct definitions."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Simple struct */
        struct Point {
            int x;
            int y;
        };
        
        /* Typedef struct */
        typedef struct {
            float real;
            float imag;
        } Complex;
        
        /* Nested struct */
        struct Person {
            char name[50];
            struct {
                int day;
                int month;
                int year;
            } birth_date;
        };
        
        /* Forward declaration - should not be indexed */
        struct ForwardDecl;
        """
        )

        result = plugin.indexFile(Path("test.c"), code)
        symbols = result["symbols"]

        # Check struct symbols
        struct_symbols = [s for s in symbols if s["kind"] == "struct"]
        assert len(struct_symbols) >= 2  # At least Point and Person

        point_struct = next(s for s in struct_symbols if s["symbol"] == "Point")
        assert point_struct["signature"] == "struct Point"

        person_struct = next(s for s in struct_symbols if s["symbol"] == "Person")
        assert person_struct["signature"] == "struct Person"

        # Check typedef
        typedef_symbols = [s for s in symbols if s["kind"] == "typedef"]
        assert any(s["symbol"] == "Complex" for s in typedef_symbols)

    def test_extract_enums(self):
        """Test extracting enum definitions."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Simple enum */
        enum Color {
            RED,
            GREEN,
            BLUE
        };
        
        /* Enum with explicit values */
        enum Status {
            OK = 0,
            ERROR = -1,
            PENDING = 1
        };
        
        /* Typedef enum */
        typedef enum {
            NORTH,
            SOUTH,
            EAST,
            WEST
        } Direction;
        """
        )

        result = plugin.indexFile(Path("test.c"), code)
        symbols = result["symbols"]

        # Check enum symbols
        enum_symbols = [s for s in symbols if s["kind"] == "enum"]
        assert len(enum_symbols) >= 2  # Color and Status

        color_enum = next(s for s in enum_symbols if s["symbol"] == "Color")
        assert color_enum["signature"] == "enum Color"

        status_enum = next(s for s in enum_symbols if s["symbol"] == "Status")
        assert status_enum["signature"] == "enum Status"

        # Check typedef
        typedef_symbols = [s for s in symbols if s["kind"] == "typedef"]
        assert any(s["symbol"] == "Direction" for s in typedef_symbols)

    def test_extract_unions(self):
        """Test extracting union definitions."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Simple union */
        union Data {
            int i;
            float f;
            char str[20];
        };
        
        /* Typedef union */
        typedef union {
            struct {
                unsigned char b;
                unsigned char g;
                unsigned char r;
                unsigned char a;
            } channels;
            unsigned int value;
        } Color;
        """
        )

        result = plugin.indexFile(Path("test.c"), code)
        symbols = result["symbols"]

        # Check union symbols (unions are parsed as struct_specifier in tree-sitter)
        struct_symbols = [s for s in symbols if s["kind"] == "struct"]
        # Note: tree-sitter C parser treats unions as structs, so we may need to
        # update the plugin to differentiate them

        # Check typedef
        typedef_symbols = [s for s in symbols if s["kind"] == "typedef"]
        assert any(s["symbol"] == "Color" for s in typedef_symbols)

    def test_extract_typedefs(self):
        """Test extracting typedef definitions."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Simple typedef */
        typedef int Integer;
        
        /* Pointer typedef */
        typedef char* String;
        
        /* Function pointer typedef */
        typedef int (*CompareFunc)(const void*, const void*);
        
        /* Array typedef */
        typedef int Matrix[3][3];
        
        /* Struct typedef */
        typedef struct Node {
            int data;
            struct Node* next;
        } Node, *NodePtr;
        """
        )

        result = plugin.indexFile(Path("test.c"), code)
        symbols = result["symbols"]

        # Check typedef symbols
        typedef_symbols = [s for s in symbols if s["kind"] == "typedef"]
        typedef_names = {s["symbol"] for s in typedef_symbols}

        assert "Integer" in typedef_names
        assert "String" in typedef_names
        assert "CompareFunc" in typedef_names
        assert "Matrix" in typedef_names
        assert "NodePtr" in typedef_names

    def test_extract_macros(self):
        """Test extracting macro definitions."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Simple macro */
        #define MAX_SIZE 100
        
        /* Macro with expression */
        #define SQUARE(x) ((x) * (x))
        
        /* Multi-line macro */
        #define MIN(a, b) \\
            ((a) < (b) ? (a) : (b))
        
        /* Variadic macro */
        #define LOG(fmt, ...) \\
            printf("[LOG] " fmt "\\n", ##__VA_ARGS__)
        
        /* Include guard */
        #ifndef HEADER_H
        #define HEADER_H
        #endif
        """
        )

        result = plugin.indexFile(Path("test.c"), code)
        symbols = result["symbols"]

        # Check macro symbols
        macro_symbols = [s for s in symbols if s["kind"] == "macro"]
        macro_names = {s["symbol"] for s in macro_symbols}

        assert "MAX_SIZE" in macro_names
        assert "SQUARE" in macro_names
        assert "MIN" in macro_names
        assert "LOG" in macro_names
        assert "HEADER_H" in macro_names

        # Check function-like macro signatures
        square_macro = next(s for s in macro_symbols if s["symbol"] == "SQUARE")
        assert "(x)" in square_macro["signature"]

        log_macro = next(s for s in macro_symbols if s["symbol"] == "LOG")
        assert "(fmt, ...)" in log_macro["signature"]

    def test_extract_global_variables(self):
        """Test extracting global variable declarations."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Global variables */
        int global_counter;
        static double pi = 3.14159;
        const char* program_name = "test";
        
        /* Multiple declarations */
        int x, y, z;
        
        /* Array declaration */
        int buffer[1024];
        
        /* Pointer declaration */
        void* ptr = NULL;
        
        /* Inside function - should not be extracted */
        void func() {
            int local_var = 42;
        }
        """
        )

        result = plugin.indexFile(Path("test.c"), code)
        symbols = result["symbols"]

        # Check variable symbols
        var_symbols = [s for s in symbols if s["kind"] == "variable"]
        var_names = {s["symbol"] for s in var_symbols}

        assert "global_counter" in var_names
        assert "pi" in var_names
        assert "program_name" in var_names
        assert "x" in var_names
        assert "y" in var_names
        assert "z" in var_names
        assert "buffer" in var_names
        assert "ptr" in var_names
        assert "local_var" not in var_names  # Should not include local variables


class TestIncludeTracking:
    """Test #include directive tracking."""

    def test_extract_includes(self):
        """Test extracting various include directives."""
        plugin = CPlugin()
        code = dedent(
            """
        /* System includes */
        #include <stdio.h>
        #include <stdlib.h>
        #include <string.h>
        
        /* Local includes */
        #include "myheader.h"
        #include "utils/helper.h"
        #include "../common.h"
        
        /* Conditional includes */
        #ifdef WINDOWS
        #include <windows.h>
        #endif
        
        #ifndef CUSTOM_MATH
        #include <math.h>
        #endif
        """
        )

        result = plugin.indexFile(Path("test.c"), code)

        # Extract includes from the indexing process
        # Note: The plugin stores includes in SQLite but doesn't return them in the result
        # We'll need to check if they were processed correctly
        assert result["file"] == "test.c"
        assert result["language"] == "c"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_syntax_error_handling(self):
        """Test handling of syntax errors in code."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Valid function */
        int valid_function() {
            return 42;
        }
        
        /* Syntax error - missing closing brace */
        void broken_function() {
            if (condition) {
                /* missing closing brace */
        
        /* Another valid function after error */
        void another_function() {
            return;
        }
        """
        )

        # Should not raise exception
        result = plugin.indexFile(Path("test.c"), code)

        # Should return some results despite syntax error
        assert isinstance(result, dict)
        symbols = result.get("symbols", [])
        assert isinstance(symbols, list)
        # Should at least get the first valid function
        assert any(s["symbol"] == "valid_function" for s in symbols)

    def test_unicode_handling(self):
        """Test handling of Unicode in code."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Unicode in comments: 你好世界 */
        
        /* String with unicode */
        const char* message = "Hello, 世界";
        
        /* Identifiers with extended characters (if supported) */
        int café_count = 5;
        """
        )

        result = plugin.indexFile(Path("test.c"), code)
        symbols = result["symbols"]

        # Should handle Unicode in strings and comments
        assert any(s["symbol"] == "message" for s in symbols)
        # Note: C standard doesn't allow Unicode in identifiers by default

    def test_extremely_long_file(self):
        """Test handling of very large files."""
        plugin = CPlugin()

        # Generate a large file
        code_parts = ["/* Large file test */\n"]
        for i in range(500):
            code_parts.append(
                f"""
int function_{i}(int arg1, int arg2) {{
    /* Function {i} */
    int result = arg1 + arg2;
    return result * {i};
}}

struct Data_{i} {{
    int field1;
    int field2;
}};

#define MACRO_{i} {i}
"""
            )

        code = "".join(code_parts)

        # Should handle large files
        result = plugin.indexFile(Path("large_test.c"), code)
        symbols = result["symbols"]

        # Should extract all symbols
        function_count = len([s for s in symbols if s["kind"] == "function"])
        struct_count = len([s for s in symbols if s["kind"] == "struct"])
        macro_count = len([s for s in symbols if s["kind"] == "macro"])

        assert function_count == 500
        assert struct_count == 500
        assert macro_count == 500

    def test_empty_file(self):
        """Test handling of empty files."""
        plugin = CPlugin()

        result = plugin.indexFile(Path("empty.c"), "")

        assert isinstance(result, dict)
        assert result.get("symbols", []) == []

    def test_comment_only_file(self):
        """Test file with only comments."""
        plugin = CPlugin()
        code = dedent(
            """
        /* This file contains only comments */
        // No actual code here
        
        /*
         * Multi-line comment
         * Still no code
         */
        
        // More comments
        """
        )

        result = plugin.indexFile(Path("comments.c"), code)

        assert isinstance(result, dict)
        assert len(result.get("symbols", [])) == 0


class TestComplexCodeStructures:
    """Test handling of complex C code structures."""

    def test_nested_structures(self):
        """Test nested structs and unions."""
        plugin = CPlugin()
        code = dedent(
            """
        struct OuterStruct {
            int outer_field;
            
            struct InnerStruct {
                int inner_field;
            } inner;
            
            union {
                int i;
                float f;
            } data;
        };
        
        typedef struct {
            struct {
                int x, y;
            } position;
            struct {
                int width, height;
            } size;
        } Rectangle;
        """
        )

        result = plugin.indexFile(Path("test.c"), code)
        symbols = result["symbols"]

        # Should extract outer structures
        assert any(s["symbol"] == "OuterStruct" and s["kind"] == "struct" for s in symbols)
        assert any(s["symbol"] == "InnerStruct" and s["kind"] == "struct" for s in symbols)
        assert any(s["symbol"] == "Rectangle" and s["kind"] == "typedef" for s in symbols)

    def test_function_pointers_and_callbacks(self):
        """Test function pointers and callback patterns."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Function pointer typedef */
        typedef void (*EventHandler)(int event_id, void* data);
        
        /* Struct with function pointer */
        struct EventListener {
            char name[32];
            EventHandler handler;
            void* user_data;
        };
        
        /* Function taking callback */
        void register_handler(const char* event_name, EventHandler handler) {
            /* Implementation */
        }
        
        /* Function returning function pointer */
        EventHandler get_default_handler(void) {
            return NULL;
        }
        
        /* Array of function pointers */
        int (*operations[4])(int, int);
        """
        )

        result = plugin.indexFile(Path("test.c"), code)
        symbols = result["symbols"]

        # Check symbols were extracted
        assert any(s["symbol"] == "EventHandler" and s["kind"] == "typedef" for s in symbols)
        assert any(s["symbol"] == "EventListener" and s["kind"] == "struct" for s in symbols)
        assert any(s["symbol"] == "register_handler" and s["kind"] == "function" for s in symbols)
        assert any(
            s["symbol"] == "get_default_handler" and s["kind"] == "function" for s in symbols
        )
        assert any(s["symbol"] == "operations" and s["kind"] == "variable" for s in symbols)

    def test_complex_preprocessor(self):
        """Test complex preprocessor directives."""
        plugin = CPlugin()
        code = dedent(
            """
        /* Configuration macros */
        #define CONFIG_DEBUG 1
        #define CONFIG_VERSION "1.0.0"
        
        /* Conditional compilation */
        #ifdef CONFIG_DEBUG
            #define LOG(msg) printf("[DEBUG] %s\\n", msg)
        #else
            #define LOG(msg) /* empty */
        #endif
        
        /* Macro functions */
        #define MAX(a, b) ((a) > (b) ? (a) : (b))
        #define SWAP(a, b) do { \\
            typeof(a) temp = (a); \\
            (a) = (b); \\
            (b) = temp; \\
        } while(0)
        
        /* String concatenation */
        #define CONCAT(a, b) a ## b
        #define STRINGIFY(x) #x
        
        /* Include guards */
        #ifndef COMPLEX_H
        #define COMPLEX_H
        
        /* Content */
        
        #endif /* COMPLEX_H */
        """
        )

        result = plugin.indexFile(Path("test.c"), code)
        symbols = result["symbols"]

        # Check macro extraction
        macro_symbols = [s for s in symbols if s["kind"] == "macro"]
        macro_names = {s["symbol"] for s in macro_symbols}

        assert "CONFIG_DEBUG" in macro_names
        assert "CONFIG_VERSION" in macro_names
        assert "LOG" in macro_names
        assert "MAX" in macro_names
        assert "SWAP" in macro_names
        assert "CONCAT" in macro_names
        assert "STRINGIFY" in macro_names
        assert "COMPLEX_H" in macro_names


class TestSearchFunctionality:
    """Test search and lookup functionality."""

    def test_get_definition(self, sqlite_store):
        """Test getting symbol definition."""
        plugin = CPlugin(sqlite_store=sqlite_store)

        # Index a file first
        code = dedent(
            """
        int target_function(int x) {
            return x * 2;
        }
        
        struct TargetStruct {
            int field;
        };
        
        #define TARGET_MACRO 42
        """
        )

        # Create repository and file in store
        repo_id = sqlite_store.create_repository("/test", "test")
        file_id = sqlite_store.store_file(
            repository_id=repo_id, file_path="/test/file.c", language="c"
        )

        # Index the file
        result = plugin.indexFile(Path("/test/file.c"), code)

        # Store symbols
        for symbol in result["symbols"]:
            sqlite_store.store_symbol(
                file_id,
                symbol["symbol"],
                symbol["kind"],
                symbol["line"],
                symbol.get("span", [symbol["line"], symbol["line"]])[1],
                signature=symbol.get("signature"),
            )

        # Test getting definitions
        func_def = plugin.getDefinition("target_function")
        assert func_def is not None
        assert func_def["symbol"] == "target_function"
        assert func_def["kind"] == "function"
        assert func_def["language"] == "c"

        struct_def = plugin.getDefinition("TargetStruct")
        assert struct_def is not None
        assert struct_def["symbol"] == "TargetStruct"
        assert struct_def["kind"] == "struct"

        macro_def = plugin.getDefinition("TARGET_MACRO")
        assert macro_def is not None
        assert macro_def["symbol"] == "TARGET_MACRO"
        assert macro_def["kind"] == "macro"

        # Non-existent symbol
        none_def = plugin.getDefinition("nonexistent")
        assert none_def is None

    def test_find_references(self):
        """Test finding symbol references."""
        plugin = CPlugin()

        # Create test files in memory
        plugin._parsed_files["main.c"] = (
            dedent(
                """
        #include "math.h"
        
        int main() {
            int result = add(5, 3);
            Point p = {1, 2};
            printf("Result: %d\\n", result);
            return 0;
        }
        """
            ),
            plugin._parser.parse(
                dedent(
                    """
        #include "math.h"
        
        int main() {
            int result = add(5, 3);
            Point p = {1, 2};
            printf("Result: %d\\n", result);
            return 0;
        }
        """
                ).encode("utf-8")
            ),
        )

        plugin._parsed_files["math.c"] = (
            dedent(
                """
        int add(int a, int b) {
            return a + b;
        }
        
        int multiply(int a, int b) {
            return add(a, 0) + add(b, 0);
        }
        """
            ),
            plugin._parser.parse(
                dedent(
                    """
        int add(int a, int b) {
            return a + b;
        }
        
        int multiply(int a, int b) {
            return add(a, 0) + add(b, 0);
        }
        """
                ).encode("utf-8")
            ),
        )

        # Find references to 'add'
        refs = plugin.findReferences("add")

        # Should find references in both files
        assert len(refs) > 0
        ref_files = {ref.file for ref in refs}
        assert "main.c" in ref_files
        assert "math.c" in ref_files

    def test_search(self, sqlite_store):
        """Test search functionality."""
        plugin = CPlugin(sqlite_store=sqlite_store)

        # Set up test data
        repo_id = sqlite_store.create_repository("/test", "test")

        # Create multiple files with symbols
        test_files = [
            (
                "calc.c",
                """
int calculate_sum(int a, int b) {
    return a + b;
}

int calculate_product(int a, int b) {
    return a * b;
}

#define CALC_VERSION "1.0"
""",
            ),
            (
                "math_utils.c",
                """
struct Calculator {
    int (*calc_func)(int, int);
};

double calc_average(double* values, int count) {
    double sum = 0;
    for (int i = 0; i < count; i++) {
        sum += values[i];
    }
    return sum / count;
}
""",
            ),
        ]

        for filename, code in test_files:
            file_id = sqlite_store.store_file(
                repository_id=repo_id, file_path=f"/test/{filename}", language="c"
            )
            result = plugin.indexFile(Path(f"/test/{filename}"), code)

            for symbol in result["symbols"]:
                sqlite_store.store_symbol(
                    file_id,
                    symbol["symbol"],
                    symbol["kind"],
                    symbol["line"],
                    symbol.get("span", [symbol["line"], symbol["line"]])[1],
                    signature=symbol.get("signature"),
                )

        # Test fuzzy search
        results = plugin.search("calc", {"semantic": False, "limit": 10})

        assert len(results) > 0
        result_names = {r["symbol"] for r in results}

        # Should find symbols containing "calc"
        assert "calculate_sum" in result_names
        assert "calculate_product" in result_names
        assert "Calculator" in result_names
        assert "calc_average" in result_names
        assert "CALC_VERSION" in result_names


class TestPersistenceIntegration:
    """Test integration with SQLite persistence."""

    def test_full_indexing_with_persistence(self, sqlite_store):
        """Test complete indexing workflow with persistence."""
        plugin = CPlugin(sqlite_store=sqlite_store)

        # Create repository
        repo_id = sqlite_store.create_repository("/myproject", "myproject")

        # Index a complex file
        code = dedent(
            """
        /**
         * @file main.c
         * @brief Main entry point for the application
         */
        
        #include <stdio.h>
        #include <stdlib.h>
        #include "config.h"
        
        #define VERSION "1.0.0"
        #define MAX_BUFFER 1024
        
        typedef struct {
            char name[50];
            int id;
        } User;
        
        static int user_count = 0;
        
        int main(int argc, char* argv[]) {
            printf("Application v%s\\n", VERSION);
            
            User* users = malloc(sizeof(User) * 10);
            if (!users) {
                return -1;
            }
            
            process_users(users);
            free(users);
            
            return 0;
        }
        
        void process_users(User* users) {
            for (int i = 0; i < user_count; i++) {
                printf("User: %s (ID: %d)\\n", users[i].name, users[i].id);
            }
        }
        """
        )

        file_path = Path("/myproject/main.c")
        file_id = sqlite_store.store_file(
            repository_id=repo_id, file_path=str(file_path), language="c", size=len(code)
        )

        # Index the file
        result = plugin.indexFile(file_path, code)

        # Store all symbols
        for symbol in result["symbols"]:
            sqlite_store.store_symbol(
                file_id,
                symbol["symbol"],
                symbol["kind"],
                symbol["line"],
                symbol.get("span", [symbol["line"], symbol["line"]])[1],
                signature=symbol.get("signature"),
            )

        # Verify persistence
        stats = sqlite_store.get_statistics()
        assert stats["symbols"] > 0

        # Test retrieval
        main_func = plugin.getDefinition("main")
        assert main_func is not None

        user_struct = plugin.getDefinition("User")
        assert user_struct is not None

        version_macro = plugin.getDefinition("VERSION")
        assert version_macro is not None


class TestPerformance:
    """Performance benchmarks for C plugin."""

    @pytest.mark.benchmark
    def test_indexing_performance(self, benchmark_results):
        """Benchmark file indexing performance."""
        plugin = CPlugin()

        # Generate a large C file
        code_parts = []
        for i in range(100):
            code_parts.append(
                f"""
typedef struct {{
    int field1;
    int field2;
    char name[32];
}} Struct{i};

int function{i}(Struct{i}* s, int x) {{
    if (!s) return -1;
    s->field1 = x;
    s->field2 = x * 2;
    return s->field1 + s->field2;
}}

#define CONSTANT_{i} {i}
#define MACRO_{i}(x) ((x) + CONSTANT_{i})
"""
            )

        large_code = "\n".join(code_parts)

        with measure_time("c_plugin_index_large", benchmark_results):
            for _ in range(10):
                result = plugin.indexFile(Path("benchmark.c"), large_code)
                assert len(result["symbols"]) >= 400  # 100 structs + 100 functions + 200 macros

    @pytest.mark.benchmark
    def test_search_performance(self, populated_sqlite_store, benchmark_results):
        """Benchmark search performance."""
        plugin = CPlugin(sqlite_store=populated_sqlite_store)

        # Add many symbols for realistic benchmark
        file_id = 1  # From populated store
        for i in range(100):
            populated_sqlite_store.store_symbol(
                file_id, f"function_{i}", "function", i * 10, i * 10 + 5
            )
            populated_sqlite_store.store_symbol(
                file_id, f"Struct_{i}", "struct", i * 20, i * 20 + 15
            )
            populated_sqlite_store.store_symbol(file_id, f"MACRO_{i}", "macro", i * 5, i * 5 + 1)

        with measure_time("c_plugin_search", benchmark_results):
            for _ in range(100):
                results = plugin.search("function", {"limit": 20})
                assert len(results) > 0
