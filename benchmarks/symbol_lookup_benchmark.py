#!/usr/bin/env python3
"""
Symbol lookup performance benchmark.
Target: < 100ms (p95)
"""

import time
import statistics
import random
import tempfile
import os
from typing import List, Tuple
import json

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugins.plugin_factory import PluginFactory


class SymbolLookupBenchmark:
    """Benchmark symbol lookup performance."""
    
    def __init__(self):
        self.results = []
        self.db_path = None
        self.store = None
        
    def setup(self, num_files: int = 1000):
        """Set up test database with sample data."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            self.db_path = tmp.name
        
        self.store = SQLiteStore(self.db_path)
        
        # Generate sample symbols for multiple languages
        languages = ['python', 'javascript', 'java', 'go', 'rust', 'c', 'cpp']
        symbol_types = ['function', 'class', 'variable', 'interface', 'method']
        
        print(f"Generating {num_files} files with symbols...")
        
        for i in range(num_files):
            lang = random.choice(languages)
            ext = {
                'python': '.py',
                'javascript': '.js',
                'java': '.java',
                'go': '.go',
                'rust': '.rs',
                'c': '.c',
                'cpp': '.cpp'
            }[lang]
            
            filepath = f"src/module_{i}/file_{i}{ext}"
            
            # Add 10-50 symbols per file
            num_symbols = random.randint(10, 50)
            for j in range(num_symbols):
                symbol_type = random.choice(symbol_types)
                symbol_name = f"{symbol_type}_{i}_{j}"
                
                self.store.add_symbol(
                    file_path=filepath,
                    symbol_name=symbol_name,
                    symbol_type=symbol_type,
                    line_number=random.randint(1, 1000),
                    metadata={
                        'language': lang,
                        'visibility': random.choice(['public', 'private', 'protected']),
                        'complexity': random.randint(1, 10)
                    }
                )
        
        print(f"Generated approximately {num_files * 30} symbols")
    
    def run_benchmark(self, num_queries: int = 1000):
        """Run symbol lookup benchmark."""
        print(f"\nRunning {num_queries} symbol lookup queries...")
        
        # Generate random queries
        query_patterns = [
            "function_",
            "class_",
            "variable_",
            "interface_",
            "method_",
            "_100_",
            "_200_",
            "_300_",
            "get",
            "set",
            "init",
            "process",
            "handle"
        ]
        
        timings = []
        
        for i in range(num_queries):
            # Random query
            query = random.choice(query_patterns) + str(random.randint(0, 999))
            
            # Measure lookup time
            start_time = time.perf_counter()
            results = self.store.search_symbols(query, limit=10)
            end_time = time.perf_counter()
            
            elapsed_ms = (end_time - start_time) * 1000
            timings.append(elapsed_ms)
            
            if i % 100 == 0:
                print(f"  Completed {i}/{num_queries} queries...")
        
        return timings
    
    def analyze_results(self, timings: List[float]):
        """Analyze benchmark results."""
        timings.sort()
        
        results = {
            'total_queries': len(timings),
            'min_ms': min(timings),
            'max_ms': max(timings),
            'mean_ms': statistics.mean(timings),
            'median_ms': statistics.median(timings),
            'p50_ms': timings[int(len(timings) * 0.50)],
            'p75_ms': timings[int(len(timings) * 0.75)],
            'p90_ms': timings[int(len(timings) * 0.90)],
            'p95_ms': timings[int(len(timings) * 0.95)],
            'p99_ms': timings[int(len(timings) * 0.99)],
            'std_dev_ms': statistics.stdev(timings) if len(timings) > 1 else 0
        }
        
        # Check if we meet the requirement
        results['meets_requirement'] = results['p95_ms'] < 100
        results['target_p95_ms'] = 100
        
        return results
    
    def run_language_specific_benchmarks(self):
        """Run benchmarks for specific language lookups."""
        languages = ['python', 'javascript', 'java', 'go', 'rust']
        language_results = {}
        
        for lang in languages:
            print(f"\nBenchmarking {lang} symbol lookups...")
            timings = []
            
            for i in range(200):
                query = f"function_{random.randint(0, 999)}"
                
                start_time = time.perf_counter()
                # Search with language filter in metadata
                results = self.store.search_symbols(query, limit=10)
                # Filter by language in post-processing
                filtered = [r for r in results if r[3].get('language') == lang]
                end_time = time.perf_counter()
                
                elapsed_ms = (end_time - start_time) * 1000
                timings.append(elapsed_ms)
            
            language_results[lang] = {
                'mean_ms': statistics.mean(timings),
                'p95_ms': sorted(timings)[int(len(timings) * 0.95)]
            }
        
        return language_results
    
    def run_complex_query_benchmark(self):
        """Test complex queries with multiple conditions."""
        print("\nBenchmarking complex queries...")
        
        complex_queries = [
            ("class AND public", "Class with public visibility"),
            ("function OR method", "Function or method symbols"),
            ("init* NOT test", "Init functions excluding tests"),
            ("get* interface", "Getter methods in interfaces"),
            ("*_handler_*", "Handler pattern symbols")
        ]
        
        results = {}
        
        for query, description in complex_queries:
            timings = []
            
            for _ in range(100):
                start_time = time.perf_counter()
                results_found = self.store.search_symbols(query, limit=20)
                end_time = time.perf_counter()
                
                elapsed_ms = (end_time - start_time) * 1000
                timings.append(elapsed_ms)
            
            results[query] = {
                'description': description,
                'mean_ms': statistics.mean(timings),
                'p95_ms': sorted(timings)[int(len(timings) * 0.95)]
            }
        
        return results
    
    def cleanup(self):
        """Clean up test database."""
        if self.store:
            self.store.close()
        if self.db_path and os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def save_results(self, results: dict, filename: str = "symbol_lookup_benchmark_results.json"):
        """Save benchmark results to file."""
        # Use environment variable or fallback to relative path for CI/CD compatibility
        base_path = os.environ.get('BENCHMARK_OUTPUT_DIR', os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(base_path, filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_path}")
    
    def print_summary(self, results: dict):
        """Print benchmark summary."""
        print("\n" + "="*60)
        print("SYMBOL LOOKUP BENCHMARK RESULTS")
        print("="*60)
        
        print(f"\nTotal Queries: {results['total_queries']}")
        print(f"Target p95: < {results['target_p95_ms']}ms")
        print(f"Actual p95: {results['p95_ms']:.2f}ms")
        print(f"Status: {'✅ PASS' if results['meets_requirement'] else '❌ FAIL'}")
        
        print("\nPercentiles:")
        print(f"  p50 (median): {results['p50_ms']:.2f}ms")
        print(f"  p75: {results['p75_ms']:.2f}ms")
        print(f"  p90: {results['p90_ms']:.2f}ms")
        print(f"  p95: {results['p95_ms']:.2f}ms")
        print(f"  p99: {results['p99_ms']:.2f}ms")
        
        print(f"\nRange: {results['min_ms']:.2f}ms - {results['max_ms']:.2f}ms")
        print(f"Mean: {results['mean_ms']:.2f}ms")
        print(f"Std Dev: {results['std_dev_ms']:.2f}ms")


def main():
    """Run the symbol lookup benchmark."""
    benchmark = SymbolLookupBenchmark()
    
    try:
        # Setup
        print("Setting up benchmark database...")
        benchmark.setup(num_files=5000)  # 5K files for realistic test
        
        # Run main benchmark
        timings = benchmark.run_benchmark(num_queries=1000)
        main_results = benchmark.analyze_results(timings)
        
        # Run language-specific benchmarks
        language_results = benchmark.run_language_specific_benchmarks()
        
        # Run complex query benchmarks
        complex_results = benchmark.run_complex_query_benchmark()
        
        # Combine all results
        all_results = {
            'main_benchmark': main_results,
            'language_specific': language_results,
            'complex_queries': complex_results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_configuration': {
                'num_files': 5000,
                'num_queries': 1000,
                'approx_total_symbols': 150000
            }
        }
        
        # Save and display results
        benchmark.save_results(all_results)
        benchmark.print_summary(main_results)
        
        # Print language-specific results
        print("\n\nLanguage-Specific Results:")
        for lang, stats in language_results.items():
            print(f"  {lang}: mean={stats['mean_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms")
        
        # Print complex query results
        print("\n\nComplex Query Results:")
        for query, stats in complex_results.items():
            print(f"  {query}: {stats['description']}")
            print(f"    mean={stats['mean_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms")
        
    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    main()