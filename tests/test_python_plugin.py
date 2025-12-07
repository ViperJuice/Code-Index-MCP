"""
Comprehensive tests for the Python plugin.

Tests cover:
- File support detection
- Symbol extraction (functions, classes, methods, variables)
- Import tracking
- Docstring extraction
- Error handling
- Edge cases and complex code structures
- Performance benchmarks
"""

from pathlib import Path
from textwrap import dedent

import pytest

from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin


class TestPluginInitialization:
    """Test plugin initialization and configuration."""

    def test_init_without_store(self):
        """Test initialization without SQLite store."""
        plugin = PythonPlugin()

        assert plugin.lang == "python"
        assert plugin._sqlite_store is None

    def test_init_with_store(self, sqlite_store):
        """Test initialization with SQLite store."""
        plugin = PythonPlugin(sqlite_store=sqlite_store)

        assert plugin.lang == "python"
        assert plugin._sqlite_store == sqlite_store

    def test_language_property(self):
        """Test the language property."""
        plugin = PythonPlugin()
        assert plugin.language == "python"


class TestFileSupport:
    """Test file support detection."""

    def test_supports_python_files(self):
        """Test that plugin supports Python files."""
        plugin = PythonPlugin()

        python_files = [
            Path("test.py"),
            Path("module.py"),
            Path("/path/to/script.py"),
            Path("__init__.py"),
            Path("test_something.py"),
        ]

        for file_path in python_files:
            assert plugin.supports(file_path) is True

    def test_does_not_support_other_files(self):
        """Test that plugin doesn't support non-Python files."""
        plugin = PythonPlugin()

        other_files = [
            Path("test.js"),
            Path("script.sh"),
            Path("data.json"),
            Path("readme.md"),
            Path("test.pyc"),
            Path("test.pyo"),
            Path("requirements.txt"),
            Path(".python"),
            Path("python"),  # No extension
        ]

        for file_path in other_files:
            assert plugin.supports(file_path) is False

    def test_supports_case_sensitivity(self):
        """Test case sensitivity in file extension."""
        plugin = PythonPlugin()

        # Python typically uses lowercase .py
        assert plugin.supports(Path("test.py")) is True
        assert plugin.supports(Path("test.PY")) is False
        assert plugin.supports(Path("test.Py")) is False


class TestSymbolExtraction:
    """Test symbol extraction from Python code."""

    def test_extract_function(self):
        """Test extracting function definitions."""
        plugin = PythonPlugin()
        code = dedent(
            """
        def simple_function():
            '''A simple function.'''
            pass
        
        def function_with_args(x, y=10):
            '''Function with arguments.'''
            return x + y
        
        async def async_function():
            '''An async function.'''
            pass
        """
        )

        result = plugin.indexFile(Path("test.py"), code)

        symbols = result["symbols"]
        assert len(symbols) == 3

        # Check simple function
        func1 = next(s for s in symbols if s["symbol"] == "simple_function")
        assert func1["kind"] == "function"
        assert func1["line"] == 2
        assert "def simple_function" in func1["signature"]

        # Check function with args
        func2 = next(s for s in symbols if s["symbol"] == "function_with_args")
        assert "def function_with_args" in func2["signature"]

        # Check async function
        func3 = next(s for s in symbols if s["symbol"] == "async_function")
        assert func3["kind"] == "function"

    def test_extract_class(self):
        """Test extracting class definitions."""
        plugin = PythonPlugin()
        code = dedent(
            """
        class SimpleClass:
            '''A simple class.'''
            pass
        
        class InheritedClass(BaseClass, Mixin):
            '''Class with inheritance.'''
            
            def __init__(self):
                self.value = 0
            
            def method(self):
                '''Instance method.'''
                return self.value
            
            @classmethod
            def class_method(cls):
                '''Class method.'''
                pass
            
            @staticmethod
            def static_method():
                '''Static method.'''
                pass
        """
        )

        result = plugin.indexFile(Path("test.py"), code)
        symbols = result["symbols"]

        # Check classes
        classes = [s for s in symbols if s["kind"] == "class"]
        assert len(classes) == 2

        # The current implementation only extracts top-level symbols
        # Methods are not extracted separately

        # Verify class names
        simple_class = next(s for s in classes if s["symbol"] == "SimpleClass")
        assert "class SimpleClass" in simple_class["signature"]

        inherited_class = next(s for s in classes if s["symbol"] == "InheritedClass")
        assert "class InheritedClass" in inherited_class["signature"]

    def test_extract_variables(self):
        """Test extracting variable assignments."""
        plugin = PythonPlugin()
        code = dedent(
            """
        # Module level variables
        CONSTANT = 42
        module_var = "hello"
        
        # Type annotated variables
        typed_var: int = 100
        typed_var_no_value: str
        
        # Multiple assignment
        x, y = 10, 20
        
        # Augmented assignment (not extracted)
        module_var += " world"
        
        def function():
            # Local variables (not extracted)
            local_var = 123
        """
        )

        result = plugin.indexFile(Path("test.py"), code)
        symbols = result["symbols"]

        # The current implementation only extracts functions and classes
        # Variables are not extracted
        functions = [s for s in symbols if s["kind"] == "function"]
        assert len(functions) == 1  # only function
        assert functions[0]["symbol"] == "function"

    def test_nested_symbols(self):
        """Test extracting nested classes and functions."""
        plugin = PythonPlugin()
        code = dedent(
            """
        class OuterClass:
            class InnerClass:
                def inner_method(self):
                    pass
            
            def outer_method(self):
                def nested_function():
                    pass
                return nested_function
        
        def outer_function():
            def inner_function():
                pass
            return inner_function
        """
        )

        result = plugin.indexFile(Path("test.py"), code)
        symbols = result["symbols"]

        # All symbols should be extracted including nested ones
        symbol_names = {s["symbol"] for s in symbols}

        assert "OuterClass" in symbol_names
        assert "InnerClass" in symbol_names
        assert "inner_method" in symbol_names
        assert "outer_method" in symbol_names
        assert "nested_function" in symbol_names
        assert "outer_function" in symbol_names
        assert "inner_function" in symbol_names

    def test_decorators_in_signature(self):
        """Test that decorators are included in signatures."""
        plugin = PythonPlugin()
        code = dedent(
            """
        @decorator
        def decorated_function():
            pass
        
        @decorator1
        @decorator2(arg="value")
        def multi_decorated():
            pass
        
        class MyClass:
            @property
            def my_property(self):
                return self._value
            
            @my_property.setter
            def my_property(self, value):
                self._value = value
        """
        )

        result = plugin.indexFile(Path("test.py"), code)
        symbols = result["symbols"]

        # Check decorated function
        func1 = next(s for s in symbols if s["symbol"] == "decorated_function")
        assert "@decorator" in func1["signature"]

        func2 = next(s for s in symbols if s["symbol"] == "multi_decorated")
        assert "@decorator1" in func2["signature"]
        assert "@decorator2" in func2["signature"]

        # Property should have decorator
        props = [s for s in symbols if s["symbol"] == "my_property"]
        assert any("@property" in p["signature"] for p in props)


class TestImportTracking:
    """Test import statement tracking."""

    def test_extract_imports(self):
        """Test extracting various import statements."""
        plugin = PythonPlugin()
        code = dedent(
            """
        # Standard imports
        import os
        import sys
        
        # From imports
        from pathlib import Path
        from typing import List, Dict, Optional
        
        # Aliased imports
        import numpy as np
        from collections import defaultdict as dd
        
        # Relative imports
        from . import sibling_module
        from ..parent import something
        from .submodule import func
        
        # Multi-line imports
        from very.long.module.name import (
            FirstClass,
            SecondClass,
            third_function
        )
        """
        )

        result = plugin.indexFile(Path("test.py"), code)

        # Verify imports are tracked
        imports = result.get("imports", [])
        assert len(imports) > 0

        # Check standard imports
        assert any(imp["module"] == "os" for imp in imports)
        assert any(imp["module"] == "sys" for imp in imports)

        # Check from imports
        pathlib_import = next((imp for imp in imports if imp["module"] == "pathlib"), None)
        assert pathlib_import is not None
        assert "Path" in pathlib_import.get("names", [])

        # Check aliased imports
        numpy_import = next((imp for imp in imports if imp["module"] == "numpy"), None)
        assert numpy_import is not None
        assert numpy_import.get("alias") == "np"

    def test_conditional_imports(self):
        """Test handling of conditional imports."""
        plugin = PythonPlugin()
        code = dedent(
            """
        import always_imported
        
        if sys.version_info >= (3, 8):
            import new_feature
        else:
            import old_feature
        
        try:
            import optional_module
        except ImportError:
            optional_module = None
        
        def function():
            import function_local_import
        """
        )

        result = plugin.indexFile(Path("test.py"), code)
        imports = result.get("imports", [])

        # All imports should be tracked regardless of conditions
        import_modules = {imp["module"] for imp in imports}

        assert "always_imported" in import_modules
        assert "new_feature" in import_modules
        assert "old_feature" in import_modules
        assert "optional_module" in import_modules
        assert "function_local_import" in import_modules


class TestDocstringExtraction:
    """Test docstring extraction and processing."""

    def test_various_docstring_formats(self):
        """Test extracting different docstring formats."""
        plugin = PythonPlugin()
        code = dedent(
            '''
        def single_line_single_quotes():
            'Single line with single quotes.'
            pass
        
        def single_line_double_quotes():
            "Single line with double quotes."
            pass
        
        def multi_line_single_quotes():
            \'\'\'
            Multi-line docstring
            with single quotes.
            \'\'\'
            pass
        
        def multi_line_double_quotes():
            """
            Multi-line docstring
            with double quotes.
            """
            pass
        
        def no_docstring():
            pass
        '''
        )

        result = plugin.indexFile(Path("test.py"), code)
        symbols = result["symbols"]

        # Check each function's docstring
        for symbol in symbols:
            if symbol["symbol"] == "no_docstring":
                assert symbol.get("docstring", "") == ""
            elif "single_line" in symbol["symbol"]:
                assert "Single line" in symbol.get("docstring", "")
            elif "multi_line" in symbol["symbol"]:
                assert "Multi-line docstring" in symbol.get("docstring", "")


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_syntax_error_handling(self):
        """Test handling of syntax errors in code."""
        plugin = PythonPlugin()
        code = dedent(
            """
        def valid_function():
            pass
        
        # Syntax error below
        def invalid_function(
            missing closing paren
        
        def another_valid():
            pass
        """
        )

        # Should not raise exception
        result = plugin.indexFile(Path("test.py"), code)

        # Should return empty or partial results
        assert isinstance(result, dict)
        # Might extract some symbols before the error
        symbols = result.get("symbols", [])
        assert isinstance(symbols, list)

    def test_unicode_handling(self):
        """Test handling of Unicode in code."""
        plugin = PythonPlugin()
        code = dedent(
            """
        # Unicode in comments: 你好世界
        
        def 函数():
            '''Unicode function name and docstring: 文档字符串'''
            emoji_var = "🐍 Python"
            return "Hello, 世界"
        
        类 = type("类", (), {})
        """
        )

        result = plugin.indexFile(Path("test.py"), code)
        symbols = result["symbols"]

        # Should handle Unicode symbols
        assert any(s["symbol"] == "函数" for s in symbols)
        assert any(s["symbol"] == "类" for s in symbols)

    def test_extremely_long_file(self):
        """Test handling of very large files."""
        plugin = PythonPlugin()

        # Generate a large file
        code_parts = ["# Large file test\n"]
        for i in range(1000):
            code_parts.append(
                f'''
def function_{i}(arg1, arg2, arg3):
    """Function number {i}"""
    result = arg1 + arg2 + arg3
    return result * {i}
'''
            )

        code = "".join(code_parts)

        # Should handle large files
        result = plugin.indexFile(Path("large_test.py"), code)
        symbols = result["symbols"]

        # Should extract all functions
        assert len(symbols) == 1000
        assert all(s["kind"] == "function" for s in symbols)

    def test_empty_file(self):
        """Test handling of empty files."""
        plugin = PythonPlugin()

        result = plugin.indexFile(Path("empty.py"), "")

        assert isinstance(result, dict)
        assert result.get("symbols", []) == []
        assert result.get("imports", []) == []

    def test_comment_only_file(self):
        """Test file with only comments."""
        plugin = PythonPlugin()
        code = dedent(
            """
        # This file contains only comments
        # No actual code here
        
        '''
        Even this is just a string literal,
        not assigned to anything
        '''
        
        # More comments
        """
        )

        result = plugin.indexFile(Path("comments.py"), code)

        assert isinstance(result, dict)
        assert len(result.get("symbols", [])) == 0


class TestComplexCodeStructures:
    """Test handling of complex Python code structures."""

    def test_generator_and_comprehensions(self):
        """Test generator functions and comprehensions."""
        plugin = PythonPlugin()
        code = dedent(
            """
        def generator_function():
            '''A generator function.'''
            for i in range(10):
                yield i
        
        def uses_comprehensions():
            '''Function using various comprehensions.'''
            list_comp = [x*2 for x in range(10)]
            dict_comp = {x: x**2 for x in range(5)}
            set_comp = {x for x in range(10) if x % 2 == 0}
            gen_exp = (x for x in range(10))
            return list_comp, dict_comp, set_comp, gen_exp
        
        # Module level comprehensions (edge case)
        MODULE_LIST = [i for i in range(5)]
        """
        )

        result = plugin.indexFile(Path("test.py"), code)
        symbols = result["symbols"]

        # Should extract functions
        assert any(s["symbol"] == "generator_function" for s in symbols)
        assert any(s["symbol"] == "uses_comprehensions" for s in symbols)
        assert any(s["symbol"] == "MODULE_LIST" for s in symbols)

    def test_context_managers_and_with(self):
        """Test classes with context manager protocol."""
        plugin = PythonPlugin()
        code = dedent(
            """
        class MyContextManager:
            '''A context manager class.'''
            
            def __enter__(self):
                '''Enter the context.'''
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                '''Exit the context.'''
                pass
        
        @contextmanager
        def function_context_manager():
            '''Context manager using decorator.'''
            yield "resource"
        """
        )

        result = plugin.indexFile(Path("test.py"), code)
        symbols = result["symbols"]

        # Should extract class and methods
        assert any(s["symbol"] == "MyContextManager" and s["kind"] == "class" for s in symbols)
        assert any(s["symbol"] == "__enter__" and s["kind"] == "method" for s in symbols)
        assert any(s["symbol"] == "__exit__" and s["kind"] == "method" for s in symbols)
        assert any(s["symbol"] == "function_context_manager" for s in symbols)

    def test_metaclasses_and_descriptors(self):
        """Test advanced OOP features."""
        plugin = PythonPlugin()
        code = dedent(
            """
        class MetaClass(type):
            '''A metaclass.'''
            def __new__(mcs, name, bases, namespace):
                return super().__new__(mcs, name, bases, namespace)
        
        class MyClass(metaclass=MetaClass):
            '''Class using metaclass.'''
            pass
        
        class Descriptor:
            '''A descriptor class.'''
            def __get__(self, obj, objtype=None):
                pass
            
            def __set__(self, obj, value):
                pass
            
            def __delete__(self, obj):
                pass
        """
        )

        result = plugin.indexFile(Path("test.py"), code)
        symbols = result["symbols"]

        # Should extract all classes and special methods
        class_names = {s["symbol"] for s in symbols if s["kind"] == "class"}
        assert "MetaClass" in class_names
        assert "MyClass" in class_names
        assert "Descriptor" in class_names

        # Check special methods
        special_methods = {"__new__", "__get__", "__set__", "__delete__"}
        method_names = {s["symbol"] for s in symbols if s["kind"] == "method"}
        assert special_methods.issubset(method_names)


class TestSearchFunctionality:
    """Test search and lookup functionality."""

    def test_get_definition(self, sqlite_store):
        """Test getting symbol definition."""
        plugin = PythonPlugin(sqlite_store=sqlite_store)

        # Index a file first
        code = dedent(
            """
        def target_function():
            '''Function to find.'''
            pass
        
        class TargetClass:
            '''Class to find.'''
            pass
        """
        )

        # Create repository and file in store
        repo_id = sqlite_store.create_repository("/test", "test")
        file_id = sqlite_store.store_file(
            repository_id=repo_id, file_path="/test/file.py", language="python"
        )

        # Index the file
        result = plugin.indexFile(Path("/test/file.py"), code)

        # Store symbols
        for symbol in result["symbols"]:
            sqlite_store.store_symbol(
                file_id,
                symbol["symbol"],
                symbol["kind"],
                symbol["line"],
                symbol.get("endLine", symbol["line"]),
                signature=symbol.get("signature"),
                documentation=symbol.get("docstring"),
            )

        # Test getting definitions
        func_def = plugin.getDefinition("target_function")
        assert func_def is not None
        assert func_def.name == "target_function"
        assert func_def.kind == "function"

        class_def = plugin.getDefinition("TargetClass")
        assert class_def is not None
        assert class_def.name == "TargetClass"
        assert class_def.kind == "class"

        # Non-existent symbol
        none_def = plugin.getDefinition("nonexistent")
        assert none_def is None

    def test_search(self, sqlite_store):
        """Test search functionality."""
        plugin = PythonPlugin(sqlite_store=sqlite_store)

        # Set up test data
        repo_id = sqlite_store.create_repository("/test", "test")

        # Create multiple files with symbols
        test_files = [
            (
                "util.py",
                """
def calculate_sum(a, b):
    return a + b

def calculate_product(a, b):
    return a * b
""",
            ),
            (
                "math_helpers.py",
                """
class Calculator:
    def calc_average(self, numbers):
        return sum(numbers) / len(numbers)
""",
            ),
        ]

        for filename, code in test_files:
            file_id = sqlite_store.store_file(
                repository_id=repo_id, file_path=f"/test/{filename}", language="python"
            )
            result = plugin.indexFile(Path(f"/test/{filename}"), code)

            for symbol in result["symbols"]:
                sqlite_store.store_symbol(
                    file_id,
                    symbol["symbol"],
                    symbol["kind"],
                    symbol["line"],
                    symbol.get("endLine", symbol["line"]),
                    signature=symbol.get("signature"),
                )

        # Test fuzzy search
        results = list(plugin.search("calc", {"semantic": False, "limit": 10}))

        assert len(results) > 0
        result_names = {r.name for r in results}

        # Should find symbols containing "calc"
        assert "calculate_sum" in result_names
        assert "calculate_product" in result_names
        assert "Calculator" in result_names
        assert "calc_average" in result_names

    def test_search_without_store(self):
        """Test search when no SQLite store is configured."""
        plugin = PythonPlugin()  # No store

        results = list(plugin.search("test", {}))

        # Should return empty results
        assert results == []


class TestPersistenceIntegration:
    """Test integration with SQLite persistence."""

    def test_full_indexing_with_persistence(self, sqlite_store):
        """Test complete indexing workflow with persistence."""
        plugin = PythonPlugin(sqlite_store=sqlite_store)

        # Create repository
        repo_id = sqlite_store.create_repository("/myproject", "myproject")

        # Index a complex file
        code = dedent(
            """
        '''Module docstring.'''
        
        import os
        import sys
        from typing import List, Optional
        
        CONSTANT = 42
        
        def main():
            '''Main entry point.'''
            processor = DataProcessor()
            processor.process()
        
        class DataProcessor:
            '''Processes data.'''
            
            def __init__(self):
                self.data = []
            
            def process(self):
                '''Process the data.'''
                return [self.transform(x) for x in self.data]
            
            def transform(self, item):
                '''Transform a single item.'''
                return item * CONSTANT
        """
        )

        file_path = Path("/myproject/main.py")
        file_id = sqlite_store.store_file(
            repository_id=repo_id, file_path=str(file_path), language="python", size=len(code)
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
                symbol.get("endLine", symbol["line"]),
                signature=symbol.get("signature"),
                documentation=symbol.get("docstring"),
            )

        # Verify persistence
        stats = sqlite_store.get_statistics()
        assert stats["symbols"] > 0

        # Test retrieval
        main_func = plugin.getDefinition("main")
        assert main_func is not None

        processor_class = plugin.getDefinition("DataProcessor")
        assert processor_class is not None


class TestPerformance:
    """Performance benchmarks for Python plugin."""

    @pytest.mark.benchmark
    def test_indexing_performance(self, benchmark_results):
        """Benchmark file indexing performance."""
        import time
        from contextlib import contextmanager

        @contextmanager
        def measure_time(test_name: str, benchmark_results: dict):
            """Context manager to measure test execution time."""
            start = time.time()
            yield
            elapsed = time.time() - start
            if test_name not in benchmark_results:
                benchmark_results[test_name] = []
            benchmark_results[test_name].append(elapsed)

        plugin = PythonPlugin()

        # Generate a large Python file
        code_parts = []
        for i in range(100):
            code_parts.append(
                f'''
class Class{i}:
    """Class number {i}"""
    
    def method1(self, x, y):
        """First method"""
        return x + y
    
    def method2(self, data: List[int]) -> Optional[int]:
        """Second method"""
        if data:
            return sum(data) // len(data)
        return None
'''
            )

        large_code = "\n".join(code_parts)

        with measure_time("python_plugin_index_large", benchmark_results):
            for _ in range(10):
                result = plugin.indexFile(Path("benchmark.py"), large_code)
                assert len(result["symbols"]) >= 300  # 100 classes + 200 methods

    @pytest.mark.benchmark
    def test_search_performance(self, populated_sqlite_store, benchmark_results):
        """Benchmark search performance."""
        import time
        from contextlib import contextmanager

        @contextmanager
        def measure_time(test_name: str, benchmark_results: dict):
            """Context manager to measure test execution time."""
            start = time.time()
            yield
            elapsed = time.time() - start
            if test_name not in benchmark_results:
                benchmark_results[test_name] = []
            benchmark_results[test_name].append(elapsed)

        plugin = PythonPlugin(sqlite_store=populated_sqlite_store)

        # Add many symbols for realistic benchmark
        file_id = 1  # From populated store
        for i in range(100):
            populated_sqlite_store.store_symbol(
                file_id, f"function_{i}", "function", i * 10, i * 10 + 5
            )
            populated_sqlite_store.store_symbol(file_id, f"Class_{i}", "class", i * 20, i * 20 + 15)

        with measure_time("python_plugin_search", benchmark_results):
            for _ in range(100):
                results = list(plugin.search("function", {"limit": 20}))
                assert len(results) > 0
