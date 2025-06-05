"""Comprehensive tests for the CSV plugin."""

import os
import pytest
from pathlib import Path

from mcp_server.plugins.csv_plugin import CSVPlugin
from mcp_server.plugins.csv_plugin.plugin import CSVSymbolTypes, ColumnInfo, CSVSchema


class TestCSVPlugin:
    """Test suite for CSV plugin functionality."""
    
    @pytest.fixture
    def plugin(self):
        """Create a CSV plugin instance."""
        return CSVPlugin()
    
    @pytest.fixture
    def test_data_dir(self):
        """Get the test data directory."""
        return Path(__file__).parent.parent / "mcp_server" / "plugins" / "csv_plugin" / "test_data"
    
    def test_plugin_initialization(self, plugin):
        """Test that the plugin initializes correctly."""
        assert plugin.get_language() == "csv"
        assert ".csv" in plugin.get_supported_extensions()
        assert ".tsv" in plugin.get_supported_extensions()
        assert ".tab" in plugin.get_supported_extensions()
        assert ".dat" in plugin.get_supported_extensions()
    
    def test_supports_csv_files(self, plugin):
        """Test file support detection."""
        assert plugin.supports("data.csv")
        assert plugin.supports("data.tsv")
        assert plugin.supports("data.tab")
        assert plugin.supports("data.dat")
        assert plugin.supports("/path/to/file.CSV")  # Case insensitive
        assert not plugin.supports("data.txt")
        assert not plugin.supports("data.py")
    
    def test_simple_csv_indexing(self, plugin, test_data_dir):
        """Test indexing a simple CSV file."""
        csv_file = test_data_dir / "simple.csv"
        content = csv_file.read_text()
        
        result = plugin.indexFile(str(csv_file), content)
        
        assert result["language"] == "csv"
        assert result["file"] == str(csv_file)
        assert len(result["symbols"]) > 0
        
        # Check for schema symbol
        schema_symbols = [s for s in result["symbols"] if s["kind"] == "schema"]
        assert len(schema_symbols) == 1
        
        schema = schema_symbols[0]
        assert schema["metadata"]["column_count"] == 4
        assert schema["metadata"]["row_count"] == 5
        assert schema["metadata"]["has_header"] is True
        
        # Check for header symbols
        header_symbols = [s for s in result["symbols"] if s["kind"] == "header"]
        assert len(header_symbols) == 4
        
        header_names = [h["symbol"] for h in header_symbols]
        assert "name" in header_names
        assert "age" in header_names
        assert "city" in header_names
        assert "active" in header_names
    
    def test_tsv_file_parsing(self, plugin, test_data_dir):
        """Test parsing a TSV file."""
        tsv_file = test_data_dir / "employees.tsv"
        content = tsv_file.read_text()
        
        result = plugin.indexFile(str(tsv_file), content)
        
        # Check schema detection
        schema_symbol = next(s for s in result["symbols"] if s["kind"] == "schema")
        assert schema_symbol["metadata"]["delimiter"] == "\t"
        assert schema_symbol["metadata"]["column_count"] == 7
        assert schema_symbol["metadata"]["row_count"] == 10
        
        # Check column types
        salary_column = next(s for s in result["symbols"] 
                           if s["kind"] == "header" and s["symbol"] == "salary")
        assert salary_column["metadata"]["data_type"] == "number"
        assert salary_column["metadata"]["statistics"] is not None
    
    def test_complex_quoted_csv(self, plugin, test_data_dir):
        """Test parsing CSV with complex quoted values."""
        csv_file = test_data_dir / "complex_quoted.csv"
        content = csv_file.read_text()
        
        result = plugin.indexFile(str(csv_file), content)
        
        # Should handle multi-line cells and embedded quotes
        schema_symbol = next(s for s in result["symbols"] if s["kind"] == "schema")
        assert schema_symbol["metadata"]["row_count"] == 5
        assert schema_symbol["metadata"]["quote_char"] == '"'
    
    def test_pipe_delimited_file(self, plugin, test_data_dir):
        """Test parsing pipe-delimited file."""
        dat_file = test_data_dir / "pipe_delimited.dat"
        content = dat_file.read_text()
        
        result = plugin.indexFile(str(dat_file), content)
        
        schema_symbol = next(s for s in result["symbols"] if s["kind"] == "schema")
        assert schema_symbol["metadata"]["delimiter"] == "|"
        assert schema_symbol["metadata"]["column_count"] == 6
        
        # Check price column is detected as numeric
        price_column = next(s for s in result["symbols"] 
                          if s["kind"] == "header" and s["symbol"] == "price")
        assert price_column["metadata"]["data_type"] == "number"
    
    def test_mixed_types_detection(self, plugin, test_data_dir):
        """Test detection of mixed data types."""
        csv_file = test_data_dir / "mixed_types.csv"
        content = csv_file.read_text()
        
        result = plugin.indexFile(str(csv_file), content)
        
        # Check that mixed types are detected
        value_column = next(s for s in result["symbols"] 
                          if s["kind"] == "header" and s["symbol"] == "value")
        # Should detect mixed type due to "abc" and "mixed,value" entries
        assert value_column["metadata"]["data_type"] in ["mixed", "string"]
        
        # ID column should be mixed (has "eight")
        id_column = next(s for s in result["symbols"] 
                       if s["kind"] == "header" and s["symbol"] == "id")
        assert id_column["metadata"]["data_type"] in ["mixed", "string"]
    
    def test_statistical_analysis(self, plugin, test_data_dir):
        """Test statistical analysis of numeric columns."""
        csv_file = test_data_dir / "sales_data.csv"
        content = csv_file.read_text()
        
        result = plugin.indexFile(str(csv_file), content)
        
        # Check quantity column statistics
        quantity_column = next(s for s in result["symbols"] 
                             if s["kind"] == "header" and s["symbol"] == "quantity")
        
        assert quantity_column["metadata"]["data_type"] == "number"
        stats = quantity_column["metadata"]["statistics"]
        assert stats is not None
        assert "mean" in stats
        assert "median" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["min"] == 1  # Minimum quantity
        assert stats["max"] == 25  # Maximum quantity
        
        # Check total column
        total_column = next(s for s in result["symbols"] 
                          if s["kind"] == "header" and s["symbol"] == "total")
        assert total_column["metadata"]["data_type"] == "number"
        assert total_column["metadata"]["statistics"] is not None
    
    def test_date_detection(self, plugin, test_data_dir):
        """Test date column detection."""
        csv_file = test_data_dir / "sales_data.csv"
        content = csv_file.read_text()
        
        result = plugin.indexFile(str(csv_file), content)
        
        # Check date column
        date_column = next(s for s in result["symbols"] 
                         if s["kind"] == "header" and s["symbol"] == "date")
        assert date_column["metadata"]["data_type"] == "date"
    
    def test_boolean_detection(self, plugin, test_data_dir):
        """Test boolean column detection."""
        csv_file = test_data_dir / "simple.csv"
        content = csv_file.read_text()
        
        result = plugin.indexFile(str(csv_file), content)
        
        # Check active column
        active_column = next(s for s in result["symbols"] 
                           if s["kind"] == "header" and s["symbol"] == "active")
        assert active_column["metadata"]["data_type"] == "boolean"
    
    def test_null_value_handling(self, plugin, test_data_dir):
        """Test handling of null/empty values."""
        csv_file = test_data_dir / "mixed_types.csv"
        content = csv_file.read_text()
        
        result = plugin.indexFile(str(csv_file), content)
        
        # Status column has empty values
        status_column = next(s for s in result["symbols"] 
                           if s["kind"] == "header" and s["symbol"] == "status")
        assert status_column["metadata"]["nullable"] is True
    
    def test_statistics_symbol(self, plugin, test_data_dir):
        """Test generation of statistics symbol."""
        csv_file = test_data_dir / "sales_data.csv"
        content = csv_file.read_text()
        
        result = plugin.indexFile(str(csv_file), content)
        
        # Check for statistics symbol
        stats_symbols = [s for s in result["symbols"] if s["kind"] == "statistic"]
        assert len(stats_symbols) == 1
        
        stats = stats_symbols[0]
        assert stats["metadata"]["total_rows"] == 10
        assert stats["metadata"]["total_columns"] == 7
        assert stats["metadata"]["numeric_columns"] > 0
        assert stats["metadata"]["string_columns"] > 0
        assert stats["metadata"]["date_columns"] > 0
    
    def test_column_search_query(self, plugin):
        """Test column-based search queries."""
        # Test query parsing (actual search would require indexed data)
        query = "column:price > 100"
        # This tests that the search method handles column queries without errors
        results = plugin.search(query)
        assert isinstance(results, list)
    
    def test_empty_csv_handling(self, plugin):
        """Test handling of empty CSV files."""
        with pytest.raises(Exception) as exc_info:
            plugin.indexFile("empty.csv", "")
        assert "Empty CSV file" in str(exc_info.value)
    
    def test_single_column_csv(self, plugin):
        """Test handling of single-column CSV."""
        content = "name\nJohn\nJane\nBob"
        result = plugin.indexFile("single.csv", content)
        
        schema_symbol = next(s for s in result["symbols"] if s["kind"] == "schema")
        assert schema_symbol["metadata"]["column_count"] == 1
        assert schema_symbol["metadata"]["row_count"] == 3
    
    def test_no_header_detection(self, plugin):
        """Test detection of CSV without headers."""
        content = "1,100,2024-01-01\n2,200,2024-01-02\n3,300,2024-01-03"
        result = plugin.indexFile("no_header.csv", content)
        
        schema_symbol = next(s for s in result["symbols"] if s["kind"] == "schema")
        assert schema_symbol["metadata"]["has_header"] is False
        
        # Should generate default column names
        headers = [s for s in result["symbols"] if s["kind"] == "header"]
        assert any("column_0" in h["symbol"] for h in headers)
    
    def test_large_file_handling(self, plugin):
        """Test handling of large files (simulated)."""
        # Create a large CSV content (just headers for this test)
        headers = [f"col_{i}" for i in range(100)]
        content = ",".join(headers) + "\n"
        
        # Add some rows
        for i in range(10):
            row = [str(i * j) for j in range(100)]
            content += ",".join(row) + "\n"
        
        result = plugin.indexFile("large.csv", content)
        
        schema_symbol = next(s for s in result["symbols"] if s["kind"] == "schema")
        assert schema_symbol["metadata"]["column_count"] == 100
        assert schema_symbol["metadata"]["row_count"] == 10
    
    def test_unicode_handling(self, plugin):
        """Test handling of Unicode characters."""
        content = "name,city,notes\nJosé,São Paulo,Café ☕\nMüller,München,Über 🎉\n李明,北京,你好 👋"
        result = plugin.indexFile("unicode.csv", content)
        
        schema_symbol = next(s for s in result["symbols"] if s["kind"] == "schema")
        assert schema_symbol["metadata"]["row_count"] == 3
        
        # Check that headers are properly extracted
        headers = [s["symbol"] for s in result["symbols"] if s["kind"] == "header"]
        assert "name" in headers
        assert "city" in headers
        assert "notes" in headers


@pytest.mark.integration
class TestCSVPluginIntegration:
    """Integration tests for CSV plugin with other components."""
    
    @pytest.fixture
    def plugin_with_storage(self, tmp_path):
        """Create plugin with storage backend."""
        from mcp_server.storage.sqlite_store import SQLiteStore
        
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))
        store.initialize()
        
        return CSVPlugin(sqlite_store=store)
    
    def test_storage_integration(self, plugin_with_storage, test_data_dir):
        """Test integration with SQLite storage."""
        csv_file = test_data_dir / "simple.csv"
        content = csv_file.read_text()
        
        result = plugin_with_storage.indexFile(str(csv_file), content)
        
        # Should store symbols in database
        assert len(result["symbols"]) > 0
        
        # Test symbol lookup
        name_def = plugin_with_storage.getDefinition("name")
        # Since we don't have actual DB integration in tests, this might return None
        # but it shouldn't raise an error
        assert name_def is None or isinstance(name_def, dict)