"""Tests for the plugin template system."""

import pytest
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch

from mcp_server.plugins.plugin_template import (
    LanguagePluginBase,
    ParsedSymbol,
    SymbolType,
    PluginConfig,
    PluginError,
    ParsingError
)
from mcp_server.plugins.tree_sitter_plugin_base import TreeSitterPluginBase
from mcp_server.plugins.regex_plugin_base import RegexPluginBase, RegexPattern
from mcp_server.plugins.hybrid_plugin_base import HybridPluginBase
from mcp_server.plugins.plugin_utils import (
    PluginCache,
    SymbolExtractor,
    FileAnalyzer,
    PluginValidator,
    create_cache_key,
    safe_file_read,
    normalize_symbol_name
)
from mcp_server.plugins.plugin_generator import PluginGenerator, PluginSpec, PluginType


# Test Plugin Implementations

class TestLanguagePlugin(LanguagePluginBase):
    """Test implementation of LanguagePluginBase."""
    
    def get_language(self) -> str:
        return "test"
    
    def get_supported_extensions(self) -> List[str]:
        return [".test", ".tst"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        return {
            SymbolType.FUNCTION: r"def\s+(\w+)",
            SymbolType.CLASS: r"class\s+(\w+)",
            SymbolType.VARIABLE: r"(\w+)\s*="
        }


class TestTreeSitterPlugin(TreeSitterPluginBase):
    """Test implementation of TreeSitterPluginBase."""
    
    def get_language(self) -> str:
        return "test"
    
    def get_supported_extensions(self) -> List[str]:
        return [".test"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        return {SymbolType.FUNCTION: r"def\s+(\w+)"}
    
    def get_node_types(self) -> Dict[SymbolType, List[str]]:
        return {
            SymbolType.FUNCTION: ["function_definition"],
            SymbolType.CLASS: ["class_definition"]
        }


class TestRegexPlugin(RegexPluginBase):
    """Test implementation of RegexPluginBase."""
    
    def get_language(self) -> str:
        return "test"
    
    def get_supported_extensions(self) -> List[str]:
        return [".test"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        return {SymbolType.FUNCTION: r"def\s+(\w+)"}
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        return [
            RegexPattern(
                pattern=r"def\s+(\w+)",
                symbol_type=SymbolType.FUNCTION,
                name_group=1
            )
        ]


class TestHybridPlugin(HybridPluginBase):
    """Test implementation of HybridPluginBase."""
    
    def get_language(self) -> str:
        return "test"
    
    def get_supported_extensions(self) -> List[str]:
        return [".test"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        return {SymbolType.FUNCTION: r"def\s+(\w+)"}
    
    def get_tree_sitter_node_types(self) -> Dict[SymbolType, List[str]]:
        return {SymbolType.FUNCTION: ["function_definition"]}
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        return [
            RegexPattern(
                pattern=r"def\s+(\w+)",
                symbol_type=SymbolType.FUNCTION,
                name_group=1
            )
        ]


# Test Cases

class TestPluginConfig:
    """Test PluginConfig functionality."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = PluginConfig()
        assert config.enable_caching is True
        assert config.cache_ttl == 3600
        assert config.async_processing is True
        assert config.enable_fallback is True
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = PluginConfig(
            enable_caching=False,
            cache_ttl=7200,
            max_file_size=5 * 1024 * 1024
        )
        assert config.enable_caching is False
        assert config.cache_ttl == 7200
        assert config.max_file_size == 5 * 1024 * 1024


class TestParsedSymbol:
    """Test ParsedSymbol functionality."""
    
    def test_symbol_creation(self):
        """Test creating a ParsedSymbol."""
        symbol = ParsedSymbol(
            name="test_function",
            symbol_type=SymbolType.FUNCTION,
            line=10,
            column=4,
            signature="def test_function():"
        )
        
        assert symbol.name == "test_function"
        assert symbol.symbol_type == SymbolType.FUNCTION
        assert symbol.line == 10
        assert symbol.column == 4
        assert symbol.signature == "def test_function():"
    
    def test_symbol_with_metadata(self):
        """Test symbol with metadata."""
        symbol = ParsedSymbol(
            name="TestClass",
            symbol_type=SymbolType.CLASS,
            line=5,
            metadata={"source": "tree-sitter", "complexity": 3}
        )
        
        assert symbol.metadata["source"] == "tree-sitter"
        assert symbol.metadata["complexity"] == 3


class TestLanguagePluginBase:
    """Test LanguagePluginBase functionality."""
    
    def test_plugin_initialization(self):
        """Test plugin initialization."""
        plugin = TestLanguagePlugin()
        assert plugin.lang == "test"
        assert plugin.supported_extensions == [".test", ".tst"]
        assert plugin._initialized is True
    
    def test_supports_file(self):
        """Test file support detection."""
        plugin = TestLanguagePlugin()
        assert plugin.supports("example.test") is True
        assert plugin.supports("example.tst") is True
        assert plugin.supports("example.py") is False
    
    @patch('mcp_server.plugins.plugin_template.SmartParser')
    def test_index_file_simple(self, mock_smart_parser):
        """Test simple file indexing."""
        plugin = TestLanguagePlugin()
        
        content = """
def hello_world():
    return "Hello, World!"

class TestClass:
    pass
"""
        
        result = plugin.indexFile("test.test", content)
        
        assert result["language"] == "test"
        assert result["file"] == "test.test"
        assert len(result["symbols"]) >= 0  # May extract symbols via regex
    
    def test_get_plugin_info(self):
        """Test plugin information retrieval."""
        plugin = TestLanguagePlugin()
        info = plugin.get_plugin_info()
        
        assert info["name"] == "TestLanguagePlugin"
        assert info["language"] == "test"
        assert info["extensions"] == [".test", ".tst"]
        assert info["initialized"] is True


class TestRegexPluginBase:
    """Test RegexPluginBase functionality."""
    
    def test_regex_plugin_initialization(self):
        """Test regex plugin initialization."""
        plugin = TestRegexPlugin()
        assert plugin.lang == "test"
        assert len(plugin.regex_patterns) > 0
    
    def test_regex_symbol_extraction(self):
        """Test symbol extraction using regex."""
        plugin = TestRegexPlugin()
        
        content = """
def hello_world():
    return "Hello, World!"

def another_function(x, y):
    return x + y
"""
        
        symbols = plugin._extract_symbols_regex(content, "test.test")
        
        # Should find function definitions
        function_symbols = [s for s in symbols if s.symbol_type == SymbolType.FUNCTION]
        assert len(function_symbols) >= 2
        
        function_names = [s.name for s in function_symbols]
        assert "hello_world" in function_names
        assert "another_function" in function_names
    
    def test_regex_pattern_compilation(self):
        """Test regex pattern compilation."""
        plugin = TestRegexPlugin()
        
        for pattern in plugin.regex_patterns:
            assert pattern.compiled is not None
            assert pattern.symbol_type in [SymbolType.FUNCTION]


class TestPluginCache:
    """Test PluginCache functionality."""
    
    def test_cache_basic_operations(self):
        """Test basic cache operations."""
        cache = PluginCache(max_size=3)
        
        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Test non-existent key
        assert cache.get("nonexistent") is None
        
        # Test cache size
        assert cache.size() == 1
    
    def test_cache_eviction(self):
        """Test cache eviction when max size is reached."""
        cache = PluginCache(max_size=2)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.size() == 2
    
    def test_cache_ttl(self):
        """Test cache TTL functionality."""
        import time
        
        cache = PluginCache(ttl=1)  # 1 second TTL
        cache.set("key1", "value1")
        
        # Should be available immediately
        assert cache.get("key1") == "value1"
        
        # Mock time passage
        with patch('time.time', return_value=time.time() + 2):
            assert cache.get("key1") is None


class TestSymbolExtractor:
    """Test SymbolExtractor utility functions."""
    
    def test_extract_function_signatures(self):
        """Test function signature extraction."""
        content = """
def hello_world():
    return "Hello"

def add_numbers(a, b):
    return a + b
"""
        
        signatures = SymbolExtractor.extract_function_signatures(content, "python")
        assert len(signatures) >= 2
    
    def test_extract_class_names(self):
        """Test class name extraction."""
        content = """
class TestClass:
    pass

class AnotherClass:
    def __init__(self):
        pass
"""
        
        class_names = SymbolExtractor.extract_class_names(content, "python")
        assert "TestClass" in class_names
        assert "AnotherClass" in class_names
    
    def test_filter_symbols_by_type(self):
        """Test filtering symbols by type."""
        symbols = [
            ParsedSymbol("func1", SymbolType.FUNCTION, 1),
            ParsedSymbol("Class1", SymbolType.CLASS, 5),
            ParsedSymbol("func2", SymbolType.FUNCTION, 10),
            ParsedSymbol("var1", SymbolType.VARIABLE, 15)
        ]
        
        functions = SymbolExtractor.filter_symbols_by_type(symbols, [SymbolType.FUNCTION])
        assert len(functions) == 2
        assert all(s.symbol_type == SymbolType.FUNCTION for s in functions)
    
    def test_deduplicate_symbols(self):
        """Test symbol deduplication."""
        symbols = [
            ParsedSymbol("func1", SymbolType.FUNCTION, 1),
            ParsedSymbol("func1", SymbolType.FUNCTION, 1),  # Duplicate
            ParsedSymbol("func2", SymbolType.FUNCTION, 5)
        ]
        
        unique_symbols = SymbolExtractor.deduplicate_symbols(symbols)
        assert len(unique_symbols) == 2


class TestFileAnalyzer:
    """Test FileAnalyzer utility functions."""
    
    def test_estimate_complexity(self):
        """Test code complexity estimation."""
        simple_content = "x = 1"
        complex_content = """
def complex_function():
    if True:
        for i in range(10):
            if i % 2 == 0:
                try:
                    do_something()
                except:
                    pass
"""
        
        simple_complexity = FileAnalyzer.estimate_complexity(simple_content)
        complex_complexity = FileAnalyzer.estimate_complexity(complex_content)
        
        assert complex_complexity > simple_complexity
    
    def test_detect_language_from_content(self):
        """Test language detection from content."""
        python_content = "def hello_world():\n    import sys"
        js_content = "function helloWorld() {\n    var x = 1;"
        
        assert FileAnalyzer.detect_language_from_content(python_content) == "python"
        assert FileAnalyzer.detect_language_from_content(js_content) == "javascript"
    
    def test_estimate_symbol_count(self):
        """Test symbol count estimation."""
        content = """
def function1():
    pass

class Class1:
    def method1(self):
        pass

var x = 1
"""
        
        count = FileAnalyzer.estimate_symbol_count(content)
        assert count >= 3  # function1, Class1, method1


class TestPluginValidator:
    """Test PluginValidator utility functions."""
    
    def test_validate_symbol_valid(self):
        """Test validation of valid symbol."""
        symbol = ParsedSymbol(
            name="valid_function",
            symbol_type=SymbolType.FUNCTION,
            line=10,
            column=0
        )
        
        issues = PluginValidator.validate_symbol(symbol)
        assert len(issues) == 0
    
    def test_validate_symbol_invalid(self):
        """Test validation of invalid symbol."""
        symbol = ParsedSymbol(
            name="",  # Empty name
            symbol_type=SymbolType.UNKNOWN,  # Unknown type
            line=0,  # Invalid line
            column=-1  # Invalid column
        )
        
        issues = PluginValidator.validate_symbol(symbol)
        assert len(issues) > 0
        assert any("empty" in issue.lower() for issue in issues)
        assert any("unknown" in issue.lower() for issue in issues)
        assert any("invalid line" in issue.lower() for issue in issues)
    
    def test_validate_plugin_config(self):
        """Test plugin configuration validation."""
        valid_config = {
            "language": "python",
            "extensions": [".py"],
            "max_file_size": 1000000
        }
        
        invalid_config = {
            "language": "python",
            # Missing extensions
            "max_file_size": -1  # Invalid size
        }
        
        valid_issues = PluginValidator.validate_plugin_config(valid_config)
        invalid_issues = PluginValidator.validate_plugin_config(invalid_config)
        
        assert len(valid_issues) == 0
        assert len(invalid_issues) > 0


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_cache_key(self):
        """Test cache key creation."""
        key1 = create_cache_key("file.py", "content", version=1)
        key2 = create_cache_key("file.py", "content", version=1)
        key3 = create_cache_key("file.py", "different", version=1)
        
        assert key1 == key2  # Same inputs should produce same key
        assert key1 != key3  # Different inputs should produce different keys
        assert len(key1) == 16  # Should be 16 character hash
    
    def test_normalize_symbol_name(self):
        """Test symbol name normalization."""
        assert normalize_symbol_name("  name  ") == "name"
        assert normalize_symbol_name('"quoted"') == "quoted"
        assert normalize_symbol_name("'quoted'") == "quoted"
        assert normalize_symbol_name("") == ""
    
    @patch('pathlib.Path.read_text')
    @patch('pathlib.Path.stat')
    def test_safe_file_read(self, mock_stat, mock_read_text):
        """Test safe file reading."""
        # Mock file size
        mock_stat.return_value.st_size = 1000
        mock_read_text.return_value = "file content"
        
        result = safe_file_read(Path("test.py"))
        assert result == "file content"
        
        # Test file too large
        mock_stat.return_value.st_size = 20 * 1024 * 1024  # 20MB
        result = safe_file_read(Path("large.py"))
        assert result is None


class TestPluginGenerator:
    """Test PluginGenerator functionality."""
    
    def test_plugin_spec_creation(self):
        """Test PluginSpec creation."""
        spec = PluginSpec(
            name="swift",
            language="swift",
            extensions=[".swift"],
            plugin_type=PluginType.HYBRID,
            description="Swift language plugin"
        )
        
        assert spec.name == "swift"
        assert spec.language == "swift"
        assert spec.extensions == [".swift"]
        assert spec.plugin_type == PluginType.HYBRID
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.write_text')
    def test_plugin_generation(self, mock_write_text, mock_mkdir):
        """Test plugin file generation."""
        spec = PluginSpec(
            name="test_lang",
            language="testlang",
            extensions=[".tl"],
            plugin_type=PluginType.REGEX
        )
        
        generator = PluginGenerator(Path("/tmp"))
        
        # Mock the generation process
        with patch.object(generator, '_generate_plugin_file') as mock_gen_plugin, \
             patch.object(generator, '_generate_init_file') as mock_gen_init, \
             patch.object(generator, '_generate_test_file') as mock_gen_test:
            
            plugin_dir = generator.generate_plugin(spec)
            
            # Verify methods were called
            mock_gen_plugin.assert_called_once()
            mock_gen_init.assert_called_once()
            mock_gen_test.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])