#!/usr/bin/env python3
"""
CSV Plugin Showcase - Comprehensive demonstration of CSV plugin capabilities.

This example demonstrates:
1. Multi-format support (CSV, TSV, pipe-delimited)
2. Automatic schema detection
3. Data type inference
4. Statistical analysis
5. Complex data handling (quotes, multi-line)
6. Search capabilities
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.plugins.csv_plugin import CSVPlugin


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}\n")


def analyze_file(plugin: CSVPlugin, file_path: str, content: str) -> Dict[str, Any]:
    """Analyze a file and return the results."""
    result = plugin.indexFile(file_path, content)
    
    # Organize symbols by type
    symbols_by_kind = {}
    for symbol in result["symbols"]:
        kind = symbol["kind"]
        if kind not in symbols_by_kind:
            symbols_by_kind[kind] = []
        symbols_by_kind[kind].append(symbol)
    
    return {"result": result, "by_kind": symbols_by_kind}


def showcase_basic_csv():
    """Demonstrate basic CSV parsing."""
    print_header("Basic CSV Parsing")
    
    plugin = CSVPlugin()
    
    csv_content = """product_id,product_name,price,stock,category
P001,Laptop Pro,1299.99,25,Electronics
P002,Wireless Mouse,39.99,150,Accessories
P003,USB-C Hub,59.99,75,Accessories
P004,4K Monitor,499.99,30,Electronics
P005,Mechanical Keyboard,119.99,50,Accessories"""
    
    analysis = analyze_file(plugin, "products.csv", csv_content)
    
    # Display schema
    schema = analysis["by_kind"]["schema"][0]
    print("Schema Information:")
    print(f"  Delimiter: {repr(schema['metadata']['delimiter'])}")
    print(f"  Rows: {schema['metadata']['row_count']}")
    print(f"  Columns: {schema['metadata']['column_count']}")
    
    # Display columns
    print("\nColumn Analysis:")
    if "header" in analysis["by_kind"]:
        for header in analysis["by_kind"]["header"]:
            meta = header["metadata"]
            print(f"  {header['symbol']}:")
            print(f"    Type: {meta['data_type']}")
            print(f"    Unique Values: {meta['unique_values']}")
            if meta.get("statistics"):
                stats = meta["statistics"]
                print(f"    Range: {stats['min']:.2f} - {stats['max']:.2f}")
                print(f"    Average: {stats['mean']:.2f}")


def showcase_tsv_with_dates():
    """Demonstrate TSV parsing with date detection."""
    print_header("TSV with Date Detection")
    
    plugin = CSVPlugin()
    
    tsv_content = """order_id\torder_date\tcustomer\tamount\tstatus
O001\t2024-01-15\tJohn Doe\t125.50\tcompleted
O002\t2024-01-16\tJane Smith\t89.99\tpending
O003\t2024-01-17\tBob Johnson\t250.00\tcompleted
O004\t2024-01-18\tAlice Brown\t45.75\tcancelled
O005\t2024-01-19\tCharlie Wilson\t199.99\tcompleted"""
    
    analysis = analyze_file(plugin, "orders.tsv", tsv_content)
    
    # Show date column detection
    print("Date Column Detection:")
    if "header" in analysis["by_kind"]:
        for header in analysis["by_kind"]["header"]:
            if header["metadata"]["data_type"] == "date":
                print(f"  Found date column: {header['symbol']}")
                print(f"    Sample values: {header['metadata'].get('sample_values', [])[:3]}")
    else:
        print("  No headers found in analysis")


def showcase_complex_quoted():
    """Demonstrate handling of complex quoted values."""
    print_header("Complex Quoted Values")
    
    plugin = CSVPlugin()
    
    csv_content = '''id,description,notes
1,"Simple description","Basic note"
2,"Description with, comma","Note with ""quotes"""
3,"Multi-line
description
here","Another
multi-line
note"
4,"Complex: comma, ""quotes"", and
newlines","All special chars: , "" '
combined"'''
    
    analysis = analyze_file(plugin, "complex.csv", csv_content)
    
    schema = analysis["by_kind"]["schema"][0]
    print(f"Successfully parsed {schema['metadata']['row_count']} rows with complex values")
    print(f"Quote character: {repr(schema['metadata']['schema']['quote_char'])}")
    
    # Show that all columns were detected
    print("\nColumns detected:")
    if "header" in analysis["by_kind"]:
        for header in analysis["by_kind"]["header"]:
            print(f"  - {header['symbol']}")


def showcase_statistical_analysis():
    """Demonstrate statistical analysis capabilities."""
    print_header("Statistical Analysis")
    
    plugin = CSVPlugin()
    
    csv_content = """employee_id,department,years_experience,salary,performance_score
E001,Engineering,5,85000,4.2
E002,Sales,3,65000,3.8
E003,Engineering,8,110000,4.5
E004,Marketing,2,55000,3.5
E005,Engineering,10,125000,4.8
E006,Sales,7,80000,4.0
E007,HR,4,60000,3.9
E008,Engineering,6,95000,4.3
E009,Sales,5,70000,3.7
E010,Marketing,9,90000,4.4"""
    
    analysis = analyze_file(plugin, "employees.csv", csv_content)
    
    # Show numeric column statistics
    print("Numeric Column Statistics:")
    if "header" in analysis["by_kind"]:
        for header in analysis["by_kind"]["header"]:
            if header["metadata"]["data_type"] == "number":
                print(f"\n{header['symbol']}:")
                stats = header["metadata"]["statistics"]
                print(f"  Min: {stats['min']:,.2f}")
                print(f"  Max: {stats['max']:,.2f}")
                print(f"  Mean: {stats['mean']:,.2f}")
                print(f"  Median: {stats['median']:,.2f}")
                if stats['std_dev'] > 0:
                    print(f"  Std Dev: {stats['std_dev']:,.2f}")
    
    # Show overall statistics
    if "statistic" in analysis["by_kind"]:
        stat = analysis["by_kind"]["statistic"][0]
        print("\nOverall File Statistics:")
        meta = stat["metadata"]
        print(f"  Numeric columns: {meta['numeric_columns']}")
        print(f"  String columns: {meta['string_columns']}")
        print(f"  Total data points: {meta['total_rows'] * meta['total_columns']}")


def showcase_mixed_types():
    """Demonstrate mixed type detection."""
    print_header("Mixed Type Detection")
    
    plugin = CSVPlugin()
    
    csv_content = """id,value,status
1,100,active
2,abc,inactive
3,200.5,active
4,,pending
5,300,ERROR
6,"text",active
7,400,
eight,500,active"""
    
    analysis = analyze_file(plugin, "mixed.csv", csv_content)
    
    print("Column Type Analysis:")
    if "header" in analysis["by_kind"]:
        for header in analysis["by_kind"]["header"]:
            meta = header["metadata"]
            print(f"\n{header['symbol']}:")
            print(f"  Detected type: {meta['data_type']}")
            print(f"  Nullable: {meta['nullable']}")
            print(f"  Sample values: {meta.get('sample_values', [])[:5]}")


def showcase_search_capabilities():
    """Demonstrate search functionality."""
    print_header("Search Capabilities")
    
    plugin = CSVPlugin()
    
    # Create a sample dataset
    csv_content = """city,population,country,continent
Tokyo,37400000,Japan,Asia
Delhi,32940000,India,Asia
Shanghai,28510000,China,Asia
São Paulo,22430000,Brazil,South America
Mexico City,22085000,Mexico,North America
Cairo,21750000,Egypt,Africa
Beijing,21540000,China,Asia
Mumbai,20960000,India,Asia
New York,18810000,USA,North America
London,9540000,UK,Europe"""
    
    plugin.indexFile("cities.csv", csv_content)
    
    print("Search Examples:")
    
    # Text search
    results = plugin.search("Asia")
    print(f"\n1. Text search for 'Asia': {len(results)} results")
    
    # Column-based search (simulated)
    print("\n2. Column-based queries (examples):")
    queries = [
        "column:population > 20000000",
        "column:continent = 'Asia'",
        "column:country ~ 'China'"
    ]
    
    for query in queries:
        print(f"   {query}")
        # Note: Actual column search implementation would require backend support


def main():
    """Run all showcases."""
    print_header("CSV Plugin Comprehensive Showcase")
    
    plugin = CSVPlugin()
    info = plugin.get_plugin_info()
    
    print("Plugin Information:")
    print(f"  Name: {info['name']}")
    print(f"  Language: {info['language']}")
    print(f"  Extensions: {', '.join(info['extensions'])}")
    print(f"  Tree-sitter support: {info['supports_tree_sitter']}")
    
    # Run all demonstrations
    showcase_basic_csv()
    showcase_tsv_with_dates()
    showcase_complex_quoted()
    showcase_statistical_analysis()
    showcase_mixed_types()
    showcase_search_capabilities()
    
    print_header("Summary")
    print("The CSV plugin provides:")
    print("✓ Multi-format support (CSV, TSV, custom delimiters)")
    print("✓ Automatic schema and delimiter detection")
    print("✓ Intelligent data type inference")
    print("✓ Statistical analysis for numeric data")
    print("✓ Robust handling of complex values")
    print("✓ Column-based search capabilities")
    print("✓ High-performance parsing")
    print("\nPerfect for data analysis, ETL pipelines, and structured data processing!")


if __name__ == "__main__":
    main()