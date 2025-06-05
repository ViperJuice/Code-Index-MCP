#!/usr/bin/env python3
"""
Performance benchmarks for the CSV plugin.

Tests various aspects of CSV parsing and analysis performance.
"""

import csv
import io
import time
import random
import string
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.plugins.csv_plugin import CSVPlugin


def generate_random_string(length: int = 10) -> str:
    """Generate a random string."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_date(start_date: datetime, days_range: int = 365) -> str:
    """Generate a random date string."""
    random_days = random.randint(0, days_range)
    date = start_date + timedelta(days=random_days)
    return date.strftime("%Y-%m-%d")


def generate_csv_content(rows: int, cols: int, complexity: str = "simple") -> str:
    """Generate CSV content for benchmarking."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Generate headers
    headers = [f"column_{i}" for i in range(cols)]
    if complexity != "simple":
        # Add typed column names
        headers[0] = "id"
        headers[1] = "name"
        if cols > 2:
            headers[2] = "age"
        if cols > 3:
            headers[3] = "salary"
        if cols > 4:
            headers[4] = "hire_date"
        if cols > 5:
            headers[5] = "is_active"
        if cols > 6:
            headers[6] = "department"
        if cols > 7:
            headers[7] = "notes"
    
    writer.writerow(headers)
    
    # Generate data rows
    start_date = datetime(2020, 1, 1)
    departments = ["Engineering", "Sales", "Marketing", "HR", "Finance"]
    
    for i in range(rows):
        row = []
        for j in range(cols):
            if complexity == "simple":
                # Simple string/number values
                if j % 3 == 0:
                    row.append(str(i * cols + j))
                else:
                    row.append(generate_random_string(8))
            else:
                # Typed values based on column
                if j == 0:  # ID
                    row.append(f"ID{i:06d}")
                elif j == 1:  # Name
                    row.append(f"{generate_random_string(6)} {generate_random_string(8)}")
                elif j == 2:  # Age
                    row.append(str(random.randint(22, 65)))
                elif j == 3:  # Salary
                    row.append(f"{random.randint(30000, 150000):.2f}")
                elif j == 4:  # Date
                    row.append(generate_random_date(start_date))
                elif j == 5:  # Boolean
                    row.append(random.choice(["true", "false"]))
                elif j == 6:  # Department
                    row.append(random.choice(departments))
                elif j == 7:  # Notes (may contain special chars)
                    if i % 10 == 0:
                        row.append(f"Note with, comma and \"quotes\" for row {i}")
                    else:
                        row.append(f"Simple note {i}")
                else:
                    row.append(generate_random_string(10))
        
        writer.writerow(row)
    
    return output.getvalue()


def benchmark_parsing(plugin: CSVPlugin, content: str, description: str) -> Tuple[float, dict]:
    """Benchmark CSV parsing."""
    start_time = time.time()
    result = plugin.indexFile("benchmark.csv", content)
    end_time = time.time()
    
    elapsed = end_time - start_time
    
    # Extract metrics
    symbols = result["symbols"]
    schema = next((s for s in symbols if s["kind"] == "schema"), None)
    
    metrics = {
        "elapsed_time": elapsed,
        "total_symbols": len(symbols),
        "rows": schema["metadata"]["row_count"] if schema else 0,
        "columns": schema["metadata"]["column_count"] if schema else 0,
        "rows_per_second": (schema["metadata"]["row_count"] / elapsed) if schema and elapsed > 0 else 0
    }
    
    return elapsed, metrics


def run_benchmarks():
    """Run comprehensive benchmarks."""
    plugin = CSVPlugin()
    
    print("CSV Plugin Performance Benchmarks")
    print("=" * 60)
    print()
    
    # Benchmark configurations
    benchmarks = [
        # (rows, cols, complexity, description)
        (100, 5, "simple", "Small simple CSV"),
        (1000, 10, "simple", "Medium simple CSV"),
        (10000, 10, "simple", "Large simple CSV"),
        (100, 50, "simple", "Wide simple CSV"),
        (1000, 10, "typed", "Medium typed CSV"),
        (10000, 10, "typed", "Large typed CSV"),
        (5000, 20, "typed", "Large wide typed CSV"),
    ]
    
    results = []
    
    for rows, cols, complexity, description in benchmarks:
        print(f"Benchmarking: {description} ({rows} rows x {cols} cols)")
        
        # Generate content
        content = generate_csv_content(rows, cols, complexity)
        content_size = len(content) / 1024  # KB
        
        # Run benchmark
        elapsed, metrics = benchmark_parsing(plugin, content, description)
        
        # Display results
        print(f"  Content Size: {content_size:.1f} KB")
        print(f"  Parse Time: {elapsed:.3f} seconds")
        print(f"  Rows/Second: {metrics['rows_per_second']:.0f}")
        print(f"  Total Symbols: {metrics['total_symbols']}")
        print()
        
        results.append({
            "description": description,
            "rows": rows,
            "cols": cols,
            "complexity": complexity,
            "size_kb": content_size,
            "time_seconds": elapsed,
            "rows_per_second": metrics['rows_per_second'],
            "symbols": metrics['total_symbols']
        })
    
    # Summary
    print("\nBenchmark Summary")
    print("-" * 60)
    print(f"{'Description':<30} {'Time (s)':<10} {'Rows/s':<10} {'Size (KB)':<10}")
    print("-" * 60)
    
    for result in results:
        print(f"{result['description']:<30} "
              f"{result['time_seconds']:<10.3f} "
              f"{result['rows_per_second']:<10.0f} "
              f"{result['size_kb']:<10.1f}")
    
    # Performance analysis
    print("\nPerformance Analysis")
    print("-" * 60)
    
    # Calculate average parsing speed
    total_rows = sum(r['rows'] for r in results)
    total_time = sum(r['time_seconds'] for r in results)
    avg_speed = total_rows / total_time if total_time > 0 else 0
    
    print(f"Average Parsing Speed: {avg_speed:.0f} rows/second")
    print(f"Total Rows Processed: {total_rows:,}")
    print(f"Total Time: {total_time:.2f} seconds")
    
    # Find best and worst performers
    best = max(results, key=lambda x: x['rows_per_second'])
    worst = min(results, key=lambda x: x['rows_per_second'])
    
    print(f"\nBest Performance: {best['description']} ({best['rows_per_second']:.0f} rows/s)")
    print(f"Worst Performance: {worst['description']} ({worst['rows_per_second']:.0f} rows/s)")
    
    # Test special cases
    print("\n\nSpecial Case Benchmarks")
    print("=" * 60)
    
    # Benchmark with many unique values
    print("\n1. High Cardinality Test (many unique values)")
    content = generate_csv_content(1000, 5, "simple")
    elapsed, metrics = benchmark_parsing(plugin, content, "High cardinality")
    print(f"   Parse Time: {elapsed:.3f} seconds")
    
    # Benchmark with quoted values
    print("\n2. Complex Quoted Values Test")
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["id", "description", "notes"])
    for i in range(1000):
        writer.writerow([
            i,
            f"Description with, comma and \"quotes\" in row {i}",
            f"Multi-line\nnote\nfor row {i}"
        ])
    content = output.getvalue()
    elapsed, metrics = benchmark_parsing(plugin, content, "Quoted values")
    print(f"   Parse Time: {elapsed:.3f} seconds")
    
    # Benchmark delimiter detection
    print("\n3. Delimiter Detection Test")
    delimiters = [',', '\t', '|', ';']
    for delim in delimiters:
        output = io.StringIO()
        writer = csv.writer(output, delimiter=delim)
        writer.writerow(["col1", "col2", "col3"])
        for i in range(100):
            writer.writerow([f"val{i}_1", f"val{i}_2", f"val{i}_3"])
        content = output.getvalue()
        
        start = time.time()
        result = plugin.indexFile(f"test{delim}.csv", content)
        elapsed = time.time() - start
        
        schema = next(s for s in result["symbols"] if s["kind"] == "schema")
        detected_delim = schema["metadata"]["delimiter"]
        print(f"   Delimiter '{delim}' -> Detected: '{detected_delim}' ({elapsed:.3f}s)")


def benchmark_search():
    """Benchmark search operations."""
    print("\n\nSearch Performance Benchmarks")
    print("=" * 60)
    
    plugin = CSVPlugin()
    
    # Create a large dataset for search
    content = generate_csv_content(10000, 10, "typed")
    plugin.indexFile("search_benchmark.csv", content)
    
    search_queries = [
        ("Simple text search", "Engineering"),
        ("Numeric comparison", "column:age > 30"),
        ("String equality", "column:department = 'Sales'"),
        ("Complex pattern", "column:name ~ 'John.*'"),
    ]
    
    for description, query in search_queries:
        start = time.time()
        results = plugin.search(query)
        elapsed = time.time() - start
        
        print(f"{description}: {elapsed:.3f}s ({len(results)} results)")


if __name__ == "__main__":
    run_benchmarks()
    benchmark_search()