"""
Base test class for language plugin testing.

This module provides a comprehensive base class that all language plugin tests
should inherit from. It includes standard test patterns, fixtures, and utilities
for testing plugin functionality.
"""

import abc
import json
import time
from pathlib import Path
from typing import Type, List, Dict, Any, Optional, Set
from unittest.mock import Mock, patch

import pytest

from mcp_server.plugin_base import IPlugin, IndexShard, SymbolDef, Reference, SearchResult
from mcp_server.storage.sqlite_store import SQLiteStore
from ..test_data.test_data_manager import TestDataManager


class PluginTestBase(abc.ABC):
    """
    Base test class for language plugins.
    
    This class provides comprehensive testing patterns that can be used
    across all language plugins. Subclasses should define the plugin_class,
    language, and file_extensions attributes.
    
    Example:
        class TestPythonPlugin(PluginTestBase):
            plugin_class = PythonPlugin
            language = "python"
            file_extensions = [".py"]
    """
    
    # Abstract attributes that must be defined by subclasses
    plugin_class: Type[IPlugin] = None
    language: str = None
    file_extensions: List[str] = []
    
    @classmethod
    def setup_class(cls):
        """Set up test class with validation."""
        if cls.plugin_class is None:
            raise ValueError(f"{cls.__name__} must define plugin_class")
        if cls.language is None:
            raise ValueError(f"{cls.__name__} must define language")
        if not cls.file_extensions:
            raise ValueError(f"{cls.__name__} must define file_extensions")
        
        # Initialize test data manager
        cls.test_data_manager = TestDataManager(cls.language)
        
    def setup_method(self):
        """Set up each test method."""
        self.plugin = self.plugin_class()
        self.mock_sqlite_store = Mock(spec=SQLiteStore)
        self.plugin_with_store = self.plugin_class(sqlite_store=self.mock_sqlite_store)
        
    def teardown_method(self):
        """Clean up after each test method."""
        # Clean up any temporary files or resources
        pass
    
    # ===== Core Plugin Interface Tests =====
    
    def test_plugin_initialization(self):
        """Test plugin initialization without SQLite store."""
        plugin = self.plugin_class()
        
        assert plugin.lang == self.language
        assert hasattr(plugin, '_parser')
        assert hasattr(plugin, '_indexer')
        
    def test_plugin_initialization_with_store(self):
        """Test plugin initialization with SQLite store."""
        mock_store = Mock(spec=SQLiteStore)
        plugin = self.plugin_class(sqlite_store=mock_store)
        
        assert plugin.lang == self.language
        assert plugin._sqlite_store == mock_store
        
    def test_file_support_detection(self):
        """Test that plugin correctly identifies supported files."""
        for ext in self.file_extensions:
            # Test various file path formats
            test_files = [
                Path(f"test{ext}"),
                Path(f"module{ext}"),
                Path(f"/path/to/script{ext}"),
                Path(f"nested/dir/file{ext}")
            ]
            
            for file_path in test_files:
                assert self.plugin.supports(file_path), f"Should support {file_path}"
                assert self.plugin.supports(str(file_path)), f"Should support {str(file_path)}"
    
    def test_file_rejection(self):
        """Test that plugin rejects unsupported files."""
        unsupported_files = [
            Path("test.txt"),
            Path("script.sh"), 
            Path("data.json"),
            Path("readme.md"),
            Path("makefile"),
            Path("config.yaml"),
            Path("test"),  # No extension
        ]
        
        # Add other language extensions
        other_extensions = [".js", ".py", ".java", ".cpp", ".rs", ".go", ".rb", ".php"]
        for ext in other_extensions:
            if ext not in self.file_extensions:
                unsupported_files.append(Path(f"test{ext}"))
        
        for file_path in unsupported_files:
            assert not self.plugin.supports(file_path), f"Should not support {file_path}"
    
    def test_index_file_basic(self):
        """Test basic file indexing functionality."""
        test_files = self.test_data_manager.get_basic_test_files()
        
        for file_name, content in test_files.items():
            result = self.plugin.indexFile(Path(file_name), content)
            
            # Verify result structure
            assert isinstance(result, dict)
            assert "file" in result
            assert "symbols" in result
            assert "language" in result
            assert result["language"] == self.language
            assert isinstance(result["symbols"], list)
            
            # Each symbol should have required fields
            for symbol in result["symbols"]:
                assert "symbol" in symbol or "name" in symbol
                assert "kind" in symbol
                assert "line" in symbol
    
    def test_empty_file_handling(self):
        """Test handling of empty files."""
        result = self.plugin.indexFile(Path(f"empty{self.file_extensions[0]}"), "")
        
        assert isinstance(result, dict)
        assert result.get("symbols", []) == []
        assert result.get("language") == self.language
    
    def test_whitespace_only_file(self):
        """Test handling of files with only whitespace."""
        whitespace_content = "   \n\n\t\t  \n   "
        result = self.plugin.indexFile(Path(f"whitespace{self.file_extensions[0]}"), whitespace_content)
        
        assert isinstance(result, dict)
        assert result.get("language") == self.language
        # Should handle gracefully without crashing
    
    def test_large_file_handling(self):
        """Test handling of large files."""
        large_content = self.test_data_manager.generate_large_file(1000)
        
        start_time = time.time()
        result = self.plugin.indexFile(Path(f"large{self.file_extensions[0]}"), large_content)
        end_time = time.time()
        
        # Should complete within reasonable time (adjust as needed)
        assert end_time - start_time < 30  # 30 seconds max
        
        assert isinstance(result, dict)
        assert result.get("language") == self.language
        
        # Should extract reasonable number of symbols
        symbols = result.get("symbols", [])
        assert len(symbols) > 10  # Should find some symbols in large file
    
    # ===== Symbol Extraction Tests =====
    
    def test_function_extraction(self):
        """Test extraction of function definitions."""
        test_files = self.test_data_manager.get_function_test_files()
        
        for file_name, content in test_files.items():
            result = self.plugin.indexFile(Path(file_name), content)
            symbols = result.get("symbols", [])
            
            # Should extract function symbols
            function_symbols = [s for s in symbols if s.get("kind") == "function"]
            assert len(function_symbols) > 0, f"Should extract functions from {file_name}"
            
            # Verify function symbol structure
            for func in function_symbols:
                assert "symbol" in func or "name" in func
                assert func.get("kind") == "function"
                assert isinstance(func.get("line"), int)
                assert func.get("line") > 0
    
    def test_class_extraction(self):
        """Test extraction of class definitions."""
        test_files = self.test_data_manager.get_class_test_files()
        
        for file_name, content in test_files.items():
            result = self.plugin.indexFile(Path(file_name), content)
            symbols = result.get("symbols", [])
            
            # Should extract class symbols
            class_symbols = [s for s in symbols if s.get("kind") == "class"]
            assert len(class_symbols) > 0, f"Should extract classes from {file_name}"
            
            # Verify class symbol structure
            for cls in class_symbols:
                assert "symbol" in cls or "name" in cls
                assert cls.get("kind") == "class"
                assert isinstance(cls.get("line"), int)
                assert cls.get("line") > 0
    
    def test_nested_symbol_extraction(self):
        """Test extraction of nested symbols (methods, inner classes, etc.)."""
        test_files = self.test_data_manager.get_nested_test_files()
        
        for file_name, content in test_files.items():
            result = self.plugin.indexFile(Path(file_name), content)
            symbols = result.get("symbols", [])
            
            # Should extract nested symbols
            assert len(symbols) > 1, f"Should extract nested symbols from {file_name}"
            
            # Verify various symbol kinds are present
            symbol_kinds = {s.get("kind") for s in symbols}
            assert len(symbol_kinds) > 1, "Should extract different kinds of symbols"
    
    def test_symbol_accuracy(self):
        """Test accuracy of symbol extraction against known correct symbols."""
        accuracy_tests = self.test_data_manager.get_accuracy_test_files()
        
        for test_case in accuracy_tests:
            file_name = test_case["file"]
            content = test_case["content"]
            expected_symbols = test_case["expected_symbols"]
            
            result = self.plugin.indexFile(Path(file_name), content)
            actual_symbols = result.get("symbols", [])
            
            # Check that all expected symbols are found
            actual_names = {s.get("symbol", s.get("name")) for s in actual_symbols}
            expected_names = {s["name"] for s in expected_symbols}
            
            missing_symbols = expected_names - actual_names
            assert not missing_symbols, f"Missing symbols: {missing_symbols}"
            
            # Check symbol details
            for expected in expected_symbols:
                actual = next(
                    (s for s in actual_symbols 
                     if s.get("symbol", s.get("name")) == expected["name"]), 
                    None
                )
                assert actual is not None, f"Symbol {expected['name']} not found"
                assert actual.get("kind") == expected["kind"]
                # Line numbers might vary by 1 due to different parsing methods
                assert abs(actual.get("line", 0) - expected["line"]) <= 1
    
    # ===== Error Handling Tests =====
    
    def test_syntax_error_handling(self):
        """Test handling of syntax errors in source code."""
        invalid_files = self.test_data_manager.get_invalid_syntax_files()
        
        for file_name, content in invalid_files.items():
            # Should not raise exception
            try:
                result = self.plugin.indexFile(Path(file_name), content)
                
                # Should return valid structure even with syntax errors
                assert isinstance(result, dict)
                assert "language" in result
                assert result["language"] == self.language
                assert "symbols" in result
                assert isinstance(result["symbols"], list)
                
            except Exception as e:
                pytest.fail(f"Plugin should handle syntax errors gracefully, but raised: {e}")
    
    def test_unicode_handling(self):
        """Test handling of Unicode characters in source code."""
        unicode_files = self.test_data_manager.get_unicode_test_files()
        
        for file_name, content in unicode_files.items():
            result = self.plugin.indexFile(Path(file_name), content)
            
            assert isinstance(result, dict)
            assert result.get("language") == self.language
            
            # Should handle Unicode symbols if language supports them
            symbols = result.get("symbols", [])
            # At minimum should not crash
    
    def test_encoding_handling(self):
        """Test handling of different text encodings."""
        # Test UTF-8 with BOM
        content_with_bom = "\ufeff" + self.test_data_manager.get_simple_content()
        result = self.plugin.indexFile(Path(f"bom{self.file_extensions[0]}"), content_with_bom)
        
        assert isinstance(result, dict)
        assert result.get("language") == self.language
    
    # ===== Search and Definition Tests =====
    
    def test_get_definition(self):
        """Test symbol definition lookup."""
        test_files = self.test_data_manager.get_definition_test_files()
        
        for test_case in test_files:
            file_name = test_case["file"] 
            content = test_case["content"]
            target_symbols = test_case["target_symbols"]
            
            # Index the file first
            self.plugin.indexFile(Path(file_name), content)
            
            for symbol_name in target_symbols:
                definition = self.plugin.getDefinition(symbol_name)
                
                if definition is not None:
                    assert isinstance(definition, dict)
                    assert definition.get("symbol") == symbol_name
                    assert "kind" in definition
                    assert "language" in definition
                    assert definition.get("language") == self.language
                # Note: Some plugins may not implement getDefinition
    
    def test_find_references(self):
        """Test finding symbol references."""
        test_files = self.test_data_manager.get_reference_test_files()
        
        for test_case in test_files:
            file_name = test_case["file"]
            content = test_case["content"] 
            target_symbols = test_case["target_symbols"]
            
            # Index the file first
            self.plugin.indexFile(Path(file_name), content)
            
            for symbol_name in target_symbols:
                references = list(self.plugin.findReferences(symbol_name))
                
                # Should return list of references
                assert isinstance(references, list)
                for ref in references:
                    assert hasattr(ref, "file") or "file" in ref
                    assert hasattr(ref, "line") or "line" in ref
    
    def test_search_functionality(self):
        """Test search functionality."""
        # Index some test data
        test_content = self.test_data_manager.get_search_test_content()
        self.plugin.indexFile(Path(f"search_test{self.file_extensions[0]}"), test_content)
        
        # Test basic search
        results = list(self.plugin.search("test"))
        assert isinstance(results, list)
        
        # Test search with options
        results_limited = list(self.plugin.search("test", {"limit": 5}))
        assert len(results_limited) <= 5
    
    # ===== Performance Tests =====
    
    def test_indexing_performance(self):
        """Test indexing performance with timing constraints."""
        content = self.test_data_manager.generate_medium_file(100)
        
        start_time = time.time()
        result = self.plugin.indexFile(Path(f"perf_test{self.file_extensions[0]}"), content)
        end_time = time.time()
        
        # Should complete within reasonable time
        elapsed = end_time - start_time
        assert elapsed < 10  # 10 seconds max for medium file
        
        # Should extract reasonable number of symbols
        symbols = result.get("symbols", [])
        assert len(symbols) > 5
    
    def test_memory_usage(self):
        """Test memory usage during indexing."""
        import tracemalloc
        
        tracemalloc.start()
        
        # Index multiple files
        for i in range(10):
            content = self.test_data_manager.generate_small_file(10)
            self.plugin.indexFile(Path(f"memory_test_{i}{self.file_extensions[0]}"), content)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable (adjust threshold as needed)
        assert peak < 100 * 1024 * 1024  # 100MB peak memory
    
    # ===== Integration Tests =====
    
    def test_sqlite_integration(self):
        """Test integration with SQLite storage."""
        if hasattr(self.plugin_with_store, '_sqlite_store'):
            # Test that plugin can work with SQLite store
            content = self.test_data_manager.get_simple_content()
            result = self.plugin_with_store.indexFile(
                Path(f"sqlite_test{self.file_extensions[0]}"), content
            )
            
            assert isinstance(result, dict)
            assert result.get("language") == self.language
    
    def test_parser_backend_switching(self):
        """Test switching between parser backends if supported."""
        if hasattr(self.plugin, 'switch_parser_backend'):
            # Test switching to different backends
            content = self.test_data_manager.get_simple_content()
            
            # Get current backend info
            initial_info = self.plugin.get_parser_info()
            assert "current_backend" in initial_info
            assert "available_backends" in initial_info
            
            # Try switching backends
            for backend in initial_info["available_backends"]:
                success = self.plugin.switch_parser_backend(backend)
                if success:
                    # Test that plugin still works
                    result = self.plugin.indexFile(
                        Path(f"backend_test{self.file_extensions[0]}"), content
                    )
                    assert isinstance(result, dict)
                    assert result.get("language") == self.language
    
    def test_concurrent_indexing(self):
        """Test concurrent file indexing."""
        import threading
        import queue
        
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def index_file(file_id):
            try:
                content = self.test_data_manager.generate_small_file(5)
                result = self.plugin.indexFile(
                    Path(f"concurrent_{file_id}{self.file_extensions[0]}"), content
                )
                results_queue.put((file_id, result))
            except Exception as e:
                errors_queue.put((file_id, e))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=index_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert errors_queue.empty(), f"Concurrent indexing errors: {list(errors_queue.queue)}"
        assert results_queue.qsize() == 5, "Should have 5 successful results"
        
        # Verify all results are valid
        while not results_queue.empty():
            file_id, result = results_queue.get()
            assert isinstance(result, dict)
            assert result.get("language") == self.language
    
    # ===== Utility Methods =====
    
    def assert_valid_symbol(self, symbol: Dict[str, Any]):
        """Assert that a symbol has valid structure."""
        assert isinstance(symbol, dict)
        assert "symbol" in symbol or "name" in symbol
        assert "kind" in symbol
        assert isinstance(symbol.get("line"), int)
        assert symbol.get("line") > 0
        
        if "span" in symbol:
            span = symbol["span"]
            assert isinstance(span, (list, tuple))
            assert len(span) == 2
            assert span[0] <= span[1]
    
    def assert_valid_index_result(self, result: Dict[str, Any]):
        """Assert that an index result has valid structure."""
        assert isinstance(result, dict)
        assert "file" in result
        assert "symbols" in result
        assert "language" in result
        assert result["language"] == self.language
        assert isinstance(result["symbols"], list)
        
        for symbol in result["symbols"]:
            self.assert_valid_symbol(symbol)
    
    def get_symbol_names(self, symbols: List[Dict[str, Any]]) -> Set[str]:
        """Extract symbol names from symbol list."""
        return {s.get("symbol", s.get("name")) for s in symbols}
    
    def get_symbols_by_kind(self, symbols: List[Dict[str, Any]], kind: str) -> List[Dict[str, Any]]:
        """Filter symbols by kind."""
        return [s for s in symbols if s.get("kind") == kind]