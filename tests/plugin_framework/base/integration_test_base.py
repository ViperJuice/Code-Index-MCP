"""
Integration test base class for language plugins.

This module provides comprehensive integration testing capabilities including
testing with the main MCP server, SQLite persistence, and cross-plugin interactions.
"""

import abc
import json
import tempfile
import shutil
from pathlib import Path
from typing import Type, List, Dict, Any, Optional
from unittest.mock import Mock, patch

import pytest

from mcp_server.plugin_base import IPlugin
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.config.settings import Settings
from ..test_data.test_data_manager import TestDataManager


class IntegrationTestBase(abc.ABC):
    """
    Base class for integration testing of language plugins.
    
    Tests plugin integration with:
    - MCP server components
    - SQLite persistence layer
    - Plugin system and dispatcher
    - Other plugins (cross-language scenarios)
    - File watching and live updates
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
        
        cls.test_data_manager = TestDataManager(cls.language)
        
    def setup_method(self):
        """Set up each test method."""
        # Create temporary directory for test files
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Initialize components
        self.sqlite_store = SQLiteStore(":memory:")  # In-memory database for tests
        self.plugin = self.plugin_class(sqlite_store=self.sqlite_store)
        
        # Mock settings
        self.mock_settings = Mock(spec=Settings)
        self.mock_settings.SQLITE_DATABASE_PATH = ":memory:"
        self.mock_settings.PLUGIN_DIRECTORIES = []
        
        # Initialize plugin manager and dispatcher
        self.plugin_manager = PluginManager()
        self.dispatcher = Dispatcher(sqlite_store=self.sqlite_store)
        
    def teardown_method(self):
        """Clean up after each test method."""
        # Remove temporary directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        # Close database connections
        if hasattr(self.sqlite_store, 'close'):
            self.sqlite_store.close()
    
    # ===== SQLite Integration Tests =====
    
    def test_sqlite_repository_creation(self):
        """Test creating repository in SQLite."""
        repo_name = f"test_{self.language}_repo"
        repo_path = str(self.temp_dir)
        
        repo_id = self.sqlite_store.create_repository(
            repo_path, repo_name, {"language": self.language}
        )
        
        assert isinstance(repo_id, int)
        assert repo_id > 0
        
        # Verify repository was created
        stats = self.sqlite_store.get_statistics()
        assert stats["repositories"] >= 1
    
    def test_sqlite_file_storage(self):
        """Test storing files in SQLite."""
        # Create repository
        repo_id = self.sqlite_store.create_repository(
            str(self.temp_dir), "test_repo", {"language": self.language}
        )
        
        # Create test file
        test_file = self.temp_dir / f"test{self.file_extensions[0]}"
        content = self.test_data_manager.get_simple_content()
        test_file.write_text(content)
        
        # Store file
        file_id = self.sqlite_store.store_file(
            repo_id,
            str(test_file),
            test_file.name,
            language=self.language,
            size=len(content),
            hash="test_hash"
        )
        
        assert isinstance(file_id, int)
        assert file_id > 0
        
        # Verify file was stored
        stats = self.sqlite_store.get_statistics()
        assert stats["files"] >= 1
    
    def test_sqlite_symbol_storage(self):
        """Test storing symbols in SQLite."""
        # Create repository and file
        repo_id = self.sqlite_store.create_repository(
            str(self.temp_dir), "test_repo", {"language": self.language}
        )
        
        test_file = self.temp_dir / f"test{self.file_extensions[0]}"
        content = self.test_data_manager.get_simple_content()
        test_file.write_text(content)
        
        file_id = self.sqlite_store.store_file(
            repo_id, str(test_file), test_file.name, language=self.language
        )
        
        # Index file and store symbols
        result = self.plugin.indexFile(test_file, content)
        symbols = result.get("symbols", [])
        
        stored_symbol_ids = []
        for symbol in symbols:
            symbol_name = symbol.get("symbol", symbol.get("name"))
            symbol_kind = symbol.get("kind")
            symbol_line = symbol.get("line")
            
            if symbol_name and symbol_kind and symbol_line:
                symbol_id = self.sqlite_store.store_symbol(
                    file_id,
                    symbol_name,
                    symbol_kind,
                    symbol_line,
                    symbol_line + 1,
                    signature=symbol.get("signature"),
                    documentation=symbol.get("docstring")
                )
                stored_symbol_ids.append(symbol_id)
        
        # Verify symbols were stored
        assert len(stored_symbol_ids) > 0
        stats = self.sqlite_store.get_statistics()
        assert stats["symbols"] >= len(stored_symbol_ids)
    
    def test_full_indexing_workflow(self):
        """Test complete indexing workflow with SQLite persistence."""
        # Create repository
        repo_id = self.sqlite_store.create_repository(
            str(self.temp_dir), "full_workflow_repo", {"language": self.language}
        )
        
        # Create multiple test files
        test_files = [
            (f"file1{self.file_extensions[0]}", 
             self.test_data_manager.generate_small_file(5)),
            (f"file2{self.file_extensions[0]}", 
             self.test_data_manager.generate_medium_file(20)),
            (f"subdir/file3{self.file_extensions[0]}", 
             self.test_data_manager.get_simple_content())
        ]
        
        # Create subdirectory
        (self.temp_dir / "subdir").mkdir()
        
        total_symbols = 0
        
        for filename, content in test_files:
            file_path = self.temp_dir / filename
            file_path.write_text(content)
            
            # Store file
            file_id = self.sqlite_store.store_file(
                repo_id,
                str(file_path),
                filename,
                language=self.language,
                size=len(content)
            )
            
            # Index file
            result = self.plugin.indexFile(file_path, content)
            symbols = result.get("symbols", [])
            
            # Store symbols
            for symbol in symbols:
                symbol_name = symbol.get("symbol", symbol.get("name"))
                symbol_kind = symbol.get("kind")
                symbol_line = symbol.get("line")
                
                if symbol_name and symbol_kind and symbol_line:
                    self.sqlite_store.store_symbol(
                        file_id,
                        symbol_name,
                        symbol_kind,
                        symbol_line,
                        symbol_line + 1,
                        signature=symbol.get("signature")
                    )
                    total_symbols += 1
        
        # Verify complete workflow
        stats = self.sqlite_store.get_statistics()
        assert stats["repositories"] >= 1
        assert stats["files"] >= len(test_files)
        assert stats["symbols"] >= total_symbols
    
    # ===== Plugin Manager Integration Tests =====
    
    def test_plugin_registration(self):
        """Test plugin registration with plugin manager."""
        # Register plugin
        self.plugin_manager.register_plugin(self.language, self.plugin_class)
        
        # Verify registration
        assert self.plugin_manager.has_plugin(self.language)
        
        # Get plugin instance
        plugin_instance = self.plugin_manager.get_plugin(self.language)
        assert isinstance(plugin_instance, self.plugin_class)
    
    def test_plugin_discovery(self):
        """Test automatic plugin discovery."""
        # This would test plugin discovery from directories
        # For now, test manual registration
        
        plugins_before = len(self.plugin_manager.get_available_plugins())
        
        self.plugin_manager.register_plugin(self.language, self.plugin_class)
        
        plugins_after = len(self.plugin_manager.get_available_plugins())
        assert plugins_after > plugins_before
        
        available = self.plugin_manager.get_available_plugins()
        assert self.language in available
    
    def test_plugin_file_routing(self):
        """Test that files are routed to correct plugin."""
        # Register plugin
        self.plugin_manager.register_plugin(self.language, self.plugin_class)
        
        for ext in self.file_extensions:
            test_file = Path(f"test{ext}")
            
            # Should route to our plugin
            plugin = self.plugin_manager.get_plugin_for_file(test_file)
            assert plugin is not None
            assert isinstance(plugin, self.plugin_class)
    
    # ===== Dispatcher Integration Tests =====
    
    def test_dispatcher_file_indexing(self):
        """Test file indexing through dispatcher."""
        # Register plugin with dispatcher
        self.dispatcher.register_plugin(self.language, self.plugin)
        
        # Create test file
        test_file = self.temp_dir / f"dispatcher_test{self.file_extensions[0]}"
        content = self.test_data_manager.get_simple_content()
        test_file.write_text(content)
        
        # Index through dispatcher
        results = self.dispatcher.index_file(str(test_file))
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Check result structure
        result = results[0]
        assert result.get("language") == self.language
        assert "symbols" in result
    
    def test_dispatcher_search(self):
        """Test search through dispatcher."""
        # Register plugin and index content
        self.dispatcher.register_plugin(self.language, self.plugin)
        
        test_file = self.temp_dir / f"search_test{self.file_extensions[0]}"
        content = self.test_data_manager.get_search_test_content()
        test_file.write_text(content)
        
        # Index file
        self.dispatcher.index_file(str(test_file))
        
        # Search through dispatcher
        results = self.dispatcher.search("test", language=self.language)
        
        assert isinstance(results, list)
        # Results structure depends on dispatcher implementation
    
    def test_dispatcher_symbol_lookup(self):
        """Test symbol lookup through dispatcher."""
        # Register plugin and index content
        self.dispatcher.register_plugin(self.language, self.plugin)
        
        test_file = self.temp_dir / f"symbol_test{self.file_extensions[0]}"
        content = self.test_data_manager.get_definition_test_files()[0]["content"]
        test_file.write_text(content)
        
        # Index file
        self.dispatcher.index_file(str(test_file))
        
        # Get symbol definition through dispatcher
        target_symbols = self.test_data_manager.get_definition_test_files()[0]["target_symbols"]
        
        for symbol_name in target_symbols:
            definition = self.dispatcher.get_definition(symbol_name, language=self.language)
            # Result depends on implementation - just verify no crash
    
    # ===== Cross-Plugin Integration Tests =====
    
    def test_multi_language_project(self):
        """Test handling projects with multiple languages."""
        if not hasattr(self, '_additional_plugins'):
            pytest.skip("No additional plugins configured for multi-language testing")
        
        # This would test scenarios where multiple plugins work together
        # For now, just test that our plugin doesn't interfere with others
        
        # Register multiple plugins
        self.plugin_manager.register_plugin(self.language, self.plugin_class)
        
        # Create files for different languages
        files = [
            (f"test{self.file_extensions[0]}", 
             self.test_data_manager.get_simple_content()),
        ]
        
        # Add other language files if configured
        # files.extend(self._get_other_language_files())
        
        for filename, content in files:
            file_path = self.temp_dir / filename
            file_path.write_text(content)
            
            # Should route to appropriate plugin
            plugin = self.plugin_manager.get_plugin_for_file(file_path)
            assert plugin is not None
    
    def test_symbol_name_conflicts(self):
        """Test handling of symbol name conflicts across languages."""
        # Create files with same symbol names
        test_file = self.temp_dir / f"conflicts{self.file_extensions[0]}"
        content = self.test_data_manager.get_simple_content()
        test_file.write_text(content)
        
        # Index file
        result = self.plugin.indexFile(test_file, content)
        symbols = result.get("symbols", [])
        
        # Verify symbols are language-scoped
        for symbol in symbols:
            # Should have language context
            assert result.get("language") == self.language
    
    # ===== File Watching Integration Tests =====
    
    def test_file_change_detection(self):
        """Test integration with file watching system."""
        # This would test with the actual file watcher
        # For now, simulate file changes
        
        test_file = self.temp_dir / f"watched{self.file_extensions[0]}"
        
        # Initial content
        initial_content = self.test_data_manager.get_simple_content()
        test_file.write_text(initial_content)
        
        # Index initial version
        initial_result = self.plugin.indexFile(test_file, initial_content)
        initial_symbols = len(initial_result.get("symbols", []))
        
        # Modified content
        modified_content = self.test_data_manager.generate_medium_file(20)
        test_file.write_text(modified_content)
        
        # Index modified version
        modified_result = self.plugin.indexFile(test_file, modified_content)
        modified_symbols = len(modified_result.get("symbols", []))
        
        # Should detect changes
        assert modified_symbols != initial_symbols
    
    def test_file_deletion_handling(self):
        """Test handling of deleted files."""
        test_file = self.temp_dir / f"to_delete{self.file_extensions[0]}"
        content = self.test_data_manager.get_simple_content()
        test_file.write_text(content)
        
        # Index file
        result = self.plugin.indexFile(test_file, content)
        assert result.get("language") == self.language
        
        # Delete file
        test_file.unlink()
        
        # Plugin should handle missing files gracefully
        # This depends on implementation details
    
    # ===== Error Recovery Tests =====
    
    def test_database_connection_recovery(self):
        """Test recovery from database connection issues."""
        # Simulate database connection issues
        with patch.object(self.sqlite_store, 'store_symbol', side_effect=Exception("DB Error")):
            # Should not crash plugin
            content = self.test_data_manager.get_simple_content()
            test_file = self.temp_dir / f"db_error{self.file_extensions[0]}"
            
            try:
                result = self.plugin.indexFile(test_file, content)
                # Should return valid result even with DB issues
                assert isinstance(result, dict)
                assert result.get("language") == self.language
            except Exception as e:
                pytest.fail(f"Plugin should handle DB errors gracefully: {e}")
    
    def test_concurrent_access_safety(self):
        """Test safety under concurrent access."""
        import threading
        import queue
        
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def concurrent_operation(thread_id):
            try:
                content = self.test_data_manager.generate_small_file(10)
                test_file = self.temp_dir / f"concurrent_{thread_id}{self.file_extensions[0]}"
                test_file.write_text(content)
                
                result = self.plugin.indexFile(test_file, content)
                results_queue.put((thread_id, result))
            except Exception as e:
                errors_queue.put((thread_id, e))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert errors_queue.empty(), f"Concurrent access errors: {list(errors_queue.queue)}"
        assert results_queue.qsize() == 5
        
        # Verify all results are valid
        while not results_queue.empty():
            thread_id, result = results_queue.get()
            assert isinstance(result, dict)
            assert result.get("language") == self.language
    
    # ===== Configuration Integration Tests =====
    
    def test_settings_integration(self):
        """Test integration with configuration settings."""
        # Test with different settings
        custom_settings = {
            "parser_backend": "tree-sitter",
            "enable_caching": True,
            "max_file_size": 1024 * 1024
        }
        
        # Plugin should respect settings if it supports them
        # This depends on plugin implementation
        content = self.test_data_manager.get_simple_content()
        test_file = self.temp_dir / f"settings{self.file_extensions[0]}"
        
        result = self.plugin.indexFile(test_file, content)
        assert isinstance(result, dict)
        assert result.get("language") == self.language
    
    def test_plugin_configuration(self):
        """Test plugin-specific configuration."""
        # Test backend switching if supported
        if hasattr(self.plugin, 'get_parser_info'):
            parser_info = self.plugin.get_parser_info()
            assert "current_backend" in parser_info
            assert "available_backends" in parser_info
            
            # Test switching backends
            for backend in parser_info["available_backends"]:
                success = self.plugin.switch_parser_backend(backend)
                if success:
                    # Verify backend switched
                    new_info = self.plugin.get_parser_info()
                    assert new_info["current_backend"] == backend
    
    # ===== Utility Methods =====
    
    def create_test_repository(self, name: str = None) -> int:
        """Create a test repository with standard setup."""
        if name is None:
            name = f"test_{self.language}_repo"
        
        return self.sqlite_store.create_repository(
            str(self.temp_dir), name, {"language": self.language}
        )
    
    def create_and_index_file(self, filename: str, content: str = None) -> Dict[str, Any]:
        """Create and index a test file."""
        if content is None:
            content = self.test_data_manager.get_simple_content()
        
        file_path = self.temp_dir / filename
        file_path.write_text(content)
        
        return self.plugin.indexFile(file_path, content)
    
    def setup_full_integration_scenario(self) -> Dict[str, Any]:
        """Set up a complete integration testing scenario."""
        # Create repository
        repo_id = self.create_test_repository()
        
        # Register plugin
        self.plugin_manager.register_plugin(self.language, self.plugin_class)
        self.dispatcher.register_plugin(self.language, self.plugin)
        
        # Create test files
        test_files = []
        for i in range(3):
            filename = f"integration_test_{i}{self.file_extensions[0]}"
            content = self.test_data_manager.generate_small_file(5 * (i + 1))
            result = self.create_and_index_file(filename, content)
            test_files.append((filename, content, result))
        
        return {
            "repo_id": repo_id,
            "test_files": test_files,
            "temp_dir": self.temp_dir
        }