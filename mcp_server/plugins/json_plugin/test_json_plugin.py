"""Tests for json plugin."""

import pytest
from pathlib import Path
from ..plugin import Plugin
from ...plugin_template import SymbolType


class TestJsonPlugin:
    """Test cases for Json plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = Plugin()
    
    def test_supports_files(self):
        """Test file support detection."""
        # Test supported extensions
        assert self.plugin.supports("test.json")\n        assert self.plugin.supports("test.jsonc")\n        assert self.plugin.supports("test.json5")\n        assert self.plugin.supports("test.jsonl")\n        assert self.plugin.supports("test.ndjson")
        
        # Test unsupported extensions
        assert not self.plugin.supports("test.txt")
        assert not self.plugin.supports("test.unknown")
    
    def test_parse_simple_code(self):
        """Test parsing simple code."""
        content = """// Test content for json"""
        
        result = self.plugin.indexFile("test.json", content)
        assert result["language"] == "json"
        assert len(result["symbols"]) > 0
    
    def test_symbol_extraction(self):
        """Test symbol extraction."""
        content = """// Test content for json"""
        
        result = self.plugin.indexFile("test.json", content)
        symbols = result["symbols"]
        
        # Check for expected symbol types
        symbol_types = {s["kind"] for s in symbols}
        expected_types = {"unknown"}
        
        assert symbol_types.intersection(expected_types), f"Expected symbols of types {expected_types}, got {symbol_types}"
    
    def test_get_definition(self):
        """Test symbol definition lookup."""
        # This would need actual symbol data
        definition = self.plugin.getDefinition("test_symbol")
        # Add assertions based on expected behavior
    
    def test_search_functionality(self):
        """Test search functionality."""
        results = self.plugin.search("test_query")
        assert isinstance(results, list)
