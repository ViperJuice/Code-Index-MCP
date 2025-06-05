#!/usr/bin/env python3
"""
Demonstration of CSV plugin capabilities for data analysis and indexing.

This example shows how the CSV plugin can be used to:
1. Analyze CSV file structure and schema
2. Detect data types automatically
3. Generate statistics for numeric columns
4. Handle various CSV formats and delimiters
5. Search within CSV data
"""

import json
from pathlib import Path
from typing import Dict, List, Any

from mcp_server.plugins.csv_plugin import CSVPlugin
from mcp_server.plugins.csv_plugin.plugin import CSVSymbolType


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}\n")


def analyze_csv_file(plugin: CSVPlugin, file_path: str, content: str):
    """Analyze a CSV file and display results."""
    print(f"Analyzing: {Path(file_path).name}")
    
    # Index the file
    result = plugin.indexFile(file_path, content)
    
    # Extract symbols by type
    symbols_by_type = {}
    for symbol in result["symbols"]:
        kind = symbol["kind"]
        if kind not in symbols_by_type:
            symbols_by_type[kind] = []
        symbols_by_type[kind].append(symbol)
    
    return result, symbols_by_type


def display_schema_info(symbols_by_type: Dict[str, List[Dict[str, Any]]]):
    """Display schema information."""
    if "schema" in symbols_by_type:
        schema = symbols_by_type["schema"][0]
        meta = schema["metadata"]
        
        print("Schema Information:")
        print(f"  - Delimiter: {repr(meta['delimiter'])}")
        print(f"  - Has Header: {meta['has_header']}")
        print(f"  - Columns: {meta['column_count']}")
        print(f"  - Rows: {meta['row_count']}")
        
        if "schema" in meta:
            schema_data = meta["schema"]
            print(f"  - Quote Character: {repr(schema_data.get('quote_char', '\"'))}")
            print(f"  - Encoding: {schema_data.get('encoding', 'utf-8')}")


def display_column_analysis(symbols_by_type: Dict[str, List[Dict[str, Any]]]):
    """Display column analysis."""
    if "header" not in symbols_by_type:
        return
    
    print("\nColumn Analysis:")
    headers = symbols_by_type["header"]
    
    # Group by data type
    by_type = {}
    for header in headers:
        data_type = header["metadata"]["data_type"]
        if data_type not in by_type:
            by_type[data_type] = []
        by_type[data_type].append(header)
    
    for data_type, columns in by_type.items():
        print(f"\n  {data_type.upper()} Columns:")
        for col in columns:
            meta = col["metadata"]
            print(f"    - {col['symbol']}:")
            print(f"        Index: {meta['column_index']}")
            print(f"        Nullable: {meta['nullable']}")
            print(f"        Unique Values: {meta['unique_values']}")
            
            # Show statistics for numeric columns
            if meta.get("statistics"):
                stats = meta["statistics"]
                print("        Statistics:")
                for stat, value in stats.items():
                    print(f"          {stat}: {value:.2f}")


def display_statistics(symbols_by_type: Dict[str, List[Dict[str, Any]]]):
    """Display overall file statistics."""
    if "statistic" not in symbols_by_type:
        return
    
    print("\nFile Statistics:")
    for stat in symbols_by_type["statistic"]:
        meta = stat["metadata"]
        print(f"  - Total Rows: {meta['total_rows']}")
        print(f"  - Total Columns: {meta['total_columns']}")
        print(f"  - Numeric Columns: {meta['numeric_columns']}")
        print(f"  - String Columns: {meta['string_columns']}")
        print(f"  - Date Columns: {meta['date_columns']}")
        print(f"  - Boolean Columns: {meta['boolean_columns']}")
        print(f"  - Mixed Type Columns: {meta['mixed_columns']}")


def demonstrate_search(plugin: CSVPlugin):
    """Demonstrate search capabilities."""
    print("\nSearch Examples:")
    
    # Standard text search
    print("\n1. Text Search:")
    results = plugin.search("New York")
    print(f"   Found {len(results)} results for 'New York'")
    
    # Column-based search (simulated)
    print("\n2. Column-based Queries:")
    queries = [
        "column:age > 30",
        "column:status = 'active'",
        "column:price between 100 and 500"
    ]
    
    for query in queries:
        print(f"   Query: {query}")
        results = plugin.search(query)
        print(f"   Results: {len(results)} matches")


def main():
    """Run the CSV analysis demonstration."""
    print_section("CSV Plugin Demonstration")
    
    # Initialize plugin
    plugin = CSVPlugin()
    print(f"Plugin initialized: {plugin.get_language()}")
    print(f"Supported extensions: {', '.join(plugin.get_supported_extensions())}")
    
    # Test data directory
    test_data_dir = Path(__file__).parent.parent / "mcp_server" / "plugins" / "csv_plugin" / "test_data"
    
    # Example files to analyze
    test_files = [
        "simple.csv",
        "sales_data.csv",
        "employees.tsv",
        "pipe_delimited.dat",
        "complex_quoted.csv",
        "mixed_types.csv"
    ]
    
    for file_name in test_files:
        file_path = test_data_dir / file_name
        if not file_path.exists():
            print(f"\nSkipping {file_name} (not found)")
            continue
        
        print_section(f"Analyzing {file_name}")
        
        try:
            content = file_path.read_text()
            result, symbols_by_type = analyze_csv_file(plugin, str(file_path), content)
            
            # Display analysis results
            display_schema_info(symbols_by_type)
            display_column_analysis(symbols_by_type)
            display_statistics(symbols_by_type)
            
        except Exception as e:
            print(f"Error analyzing {file_name}: {e}")
    
    # Demonstrate search capabilities
    print_section("Search Capabilities")
    demonstrate_search(plugin)
    
    # Show plugin info
    print_section("Plugin Information")
    info = plugin.get_plugin_info()
    print(json.dumps(info, indent=2))
    
    # Show statistics
    print("\nPlugin Statistics:")
    stats = plugin.get_statistics()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()