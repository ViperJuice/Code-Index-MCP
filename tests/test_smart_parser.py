"""Tests for the SmartParser system."""

import pytest
from pathlib import Path

from mcp_server.utils.smart_parser import SmartParser, TreeSitterBackend, ASTBackend
from mcp_server.plugins.python_plugin.plugin import Plugin


class TestSmartParser:
    """Test SmartParser functionality."""
    
    def test_smart_parser_initialization(self):
        """Test SmartParser can be initialized for Python."""
        parser = SmartParser('python')
        assert parser.language == 'python'
        assert parser.get_backend_name() in ['tree-sitter', 'ast']
        assert len(parser.available_backends) >= 1
    
    def test_parse_python_code(self):
        """Test parsing Python code."""
        parser = SmartParser('python')
        code = b"def hello():\n    print('Hello, world!')"
        
        result = parser.parse(code)
        assert result is not None
    
    def test_backend_switching(self):
        """Test switching between backends."""
        parser = SmartParser('python')
        initial_backend = parser.get_backend_name()
        
        # Only test switching if multiple backends available
        if len(parser.available_backends) > 1:
            other_backend = [b for b in parser.available_backends if b != initial_backend][0]
            parser.switch_backend(other_backend)
            assert parser.get_backend_name() == other_backend
    
    def test_tree_sitter_backend(self):
        """Test TreeSitter backend directly."""
        backend = TreeSitterBackend()
        if backend.is_available() and 'python' in backend.supported_languages:
            code = b"class Test:\n    pass"
            result = backend.parse(code, 'python')
            assert result is not None
    
    def test_ast_backend(self):
        """Test AST backend directly."""
        backend = ASTBackend()
        assert backend.is_available()
        assert 'python' in backend.supported_languages
        
        code = b"def test():\n    return 42"
        result = backend.parse(code, 'python')
        assert result is not None


class TestPythonPluginWithSmartParser:
    """Test Python plugin with SmartParser integration."""
    
    def test_plugin_initialization(self):
        """Test plugin initializes with SmartParser."""
        plugin = Plugin()
        assert hasattr(plugin, '_parser')
        assert isinstance(plugin._parser, SmartParser)
    
    def test_plugin_indexing(self):
        """Test file indexing with SmartParser."""
        plugin = Plugin()
        
        code = """
class MyClass:
    def method1(self):
        pass
    
    def method2(self):
        pass

def standalone_function():
    return True
"""
        
        result = plugin.indexFile("test.py", code)
        assert result['language'] == 'python'
        
        # Get current backend to adjust expectations
        backend_name = plugin._parser.get_backend_name()
        
        if backend_name == 'tree-sitter':
            # Tree-sitter only finds top-level definitions
            assert len(result['symbols']) >= 2  # MyClass, standalone_function
        else:  # AST backend
            # AST finds all definitions including methods
            assert len(result['symbols']) >= 4  # MyClass, __init__, method1, method2, standalone_function
        
        # Verify symbol details
        symbols = {s['symbol']: s for s in result['symbols']}
        assert 'MyClass' in symbols
        assert symbols['MyClass']['kind'] == 'class'
        assert 'standalone_function' in symbols
        assert symbols['standalone_function']['kind'] == 'function'
    
    def test_plugin_parser_info(self):
        """Test getting parser information from plugin."""
        plugin = Plugin()
        info = plugin.get_parser_info()
        
        assert 'current_backend' in info
        assert 'available_backends' in info
        assert 'language' in info
        assert info['language'] == 'python'
    
    def test_plugin_backend_switching(self):
        """Test switching parser backends through plugin."""
        plugin = Plugin()
        info = plugin.get_parser_info()
        
        # Only test if multiple backends available
        if len(info['available_backends']) > 1:
            current = info['current_backend']
            other = [b for b in info['available_backends'] if b != current][0]
            
            assert plugin.switch_parser_backend(other)
            new_info = plugin.get_parser_info()
            assert new_info['current_backend'] == other
    
    def test_error_handling(self):
        """Test error handling in parsing."""
        plugin = Plugin()
        
        # Invalid Python code
        code = "def broken syntax here"
        result = plugin.indexFile("broken.py", code)
        
        # Should return empty symbols on parse error
        assert result['file'] == "broken.py"
        assert result['symbols'] == []
        assert result['language'] == 'python'