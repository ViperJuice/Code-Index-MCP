"""
Comparison suite for testing different parser backends and plugins.

This module provides tools for comparing:
- Tree-sitter vs regex parser performance
- Different plugin implementations
- Cross-language parser accuracy
- Backend switching overhead
"""

import time
import statistics
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from mcp_server.plugin_base import IPlugin
from ..test_data.test_data_manager import TestDataManager


@dataclass
class ComparisonMetric:
    """Metric for comparing different approaches."""
    name: str
    backend_a: float
    backend_b: float
    unit: str
    improvement_ratio: float
    better_backend: str


@dataclass
class ComparisonResult:
    """Result of comparing two backends/plugins."""
    test_name: str
    backend_a_name: str
    backend_b_name: str
    metrics: List[ComparisonMetric]
    overall_winner: str
    timestamp: str
    language: str


class ComparisonSuite:
    """
    Suite for comparing different parser backends and plugins.
    
    Provides comparisons for:
    - Tree-sitter vs regex parsing
    - Performance across backends
    - Symbol extraction accuracy
    - Memory usage patterns
    """
    
    def __init__(self, language: str):
        """Initialize comparison suite for a language."""
        self.language = language
        self.test_data_manager = TestDataManager(language)
        self.results: List[ComparisonResult] = []
    
    # ===== Core Comparison Infrastructure =====
    
    def compare_backends(self,
                        plugin: IPlugin,
                        backend_a: str,
                        backend_b: str,
                        test_name: str,
                        test_operation: callable,
                        iterations: int = 10) -> ComparisonResult:
        """Compare two parser backends on the same plugin."""
        
        if not hasattr(plugin, 'switch_parser_backend'):
            raise ValueError("Plugin does not support backend switching")
        
        print(f"Comparing {backend_a} vs {backend_b} for {test_name}")
        
        # Test backend A
        print(f"  Testing {backend_a}...")
        if not plugin.switch_parser_backend(backend_a):
            raise ValueError(f"Could not switch to backend {backend_a}")
        
        metrics_a = self._run_performance_test(test_operation, iterations)
        
        # Test backend B
        print(f"  Testing {backend_b}...")
        if not plugin.switch_parser_backend(backend_b):
            raise ValueError(f"Could not switch to backend {backend_b}")
        
        metrics_b = self._run_performance_test(test_operation, iterations)
        
        # Compare metrics
        comparison_metrics = []
        
        for metric_name in ["execution_time", "memory_usage", "symbols_extracted"]:
            value_a = metrics_a.get(metric_name, 0)
            value_b = metrics_b.get(metric_name, 0)
            
            if value_a > 0 and value_b > 0:
                if metric_name == "execution_time" or metric_name == "memory_usage":
                    # Lower is better
                    improvement_ratio = value_a / value_b
                    better_backend = backend_b if value_b < value_a else backend_a
                else:
                    # Higher is better  
                    improvement_ratio = value_b / value_a
                    better_backend = backend_b if value_b > value_a else backend_a
                
                comparison_metrics.append(ComparisonMetric(
                    name=metric_name,
                    backend_a=value_a,
                    backend_b=value_b,
                    unit=self._get_metric_unit(metric_name),
                    improvement_ratio=improvement_ratio,
                    better_backend=better_backend
                ))
        
        # Determine overall winner
        backend_wins = {}
        for metric in comparison_metrics:
            backend_wins[metric.better_backend] = backend_wins.get(metric.better_backend, 0) + 1
        
        overall_winner = max(backend_wins, key=backend_wins.get) if backend_wins else "tie"
        
        result = ComparisonResult(
            test_name=test_name,
            backend_a_name=backend_a,
            backend_b_name=backend_b,
            metrics=comparison_metrics,
            overall_winner=overall_winner,
            timestamp=datetime.now().isoformat(),
            language=self.language
        )
        
        self.results.append(result)
        return result
    
    def _run_performance_test(self, test_operation: callable, iterations: int) -> Dict[str, float]:
        """Run performance test and return metrics."""
        execution_times = []
        memory_usages = []
        symbol_counts = []
        
        for i in range(iterations):
            # Run test operation
            start_time = time.time()
            
            try:
                result = test_operation()
                end_time = time.time()
                
                execution_times.append(end_time - start_time)
                
                # Extract metrics from result
                if isinstance(result, dict):
                    symbols = result.get("symbols", [])
                    symbol_counts.append(len(symbols))
                
                # Memory usage would need to be measured separately
                # For now, use a placeholder
                memory_usages.append(0)
                
            except Exception as e:
                # Record failed execution
                end_time = time.time()
                execution_times.append(end_time - start_time)
                symbol_counts.append(0)
                memory_usages.append(0)
        
        return {
            "execution_time": statistics.mean(execution_times),
            "memory_usage": statistics.mean(memory_usages) if memory_usages else 0,
            "symbols_extracted": statistics.mean(symbol_counts) if symbol_counts else 0
        }
    
    def _get_metric_unit(self, metric_name: str) -> str:
        """Get unit for a metric."""
        units = {
            "execution_time": "seconds",
            "memory_usage": "MB",
            "symbols_extracted": "count"
        }
        return units.get(metric_name, "")
    
    # ===== Standard Backend Comparisons =====
    
    def compare_treesitter_vs_regex(self, plugin: IPlugin) -> List[ComparisonResult]:
        """Compare Tree-sitter vs regex parsing backends."""
        if not hasattr(plugin, 'get_parser_info'):
            raise ValueError("Plugin does not support parser backend information")
        
        parser_info = plugin.get_parser_info()
        available_backends = parser_info.get("available_backends", [])
        
        treesitter_backend = None
        regex_backend = None
        
        for backend in available_backends:
            if "tree" in backend.lower() or "sitter" in backend.lower():
                treesitter_backend = backend
            elif "regex" in backend.lower() or "ast" in backend.lower():
                regex_backend = backend
        
        if not treesitter_backend or not regex_backend:
            raise ValueError(f"Could not find both tree-sitter and regex backends. Available: {available_backends}")
        
        print(f"Comparing Tree-sitter ({treesitter_backend}) vs Regex ({regex_backend})")
        
        comparison_results = []
        
        # Test 1: Small file parsing
        def small_file_test():
            content = self.test_data_manager.generate_small_file(5)
            return plugin.indexFile(Path(f"small.{self.language}"), content)
        
        result1 = self.compare_backends(
            plugin, treesitter_backend, regex_backend,
            "small_file_parsing", small_file_test, iterations=20
        )
        comparison_results.append(result1)
        
        # Test 2: Medium file parsing
        def medium_file_test():
            content = self.test_data_manager.generate_medium_file(50)
            return plugin.indexFile(Path(f"medium.{self.language}"), content)
        
        result2 = self.compare_backends(
            plugin, treesitter_backend, regex_backend,
            "medium_file_parsing", medium_file_test, iterations=10
        )
        comparison_results.append(result2)
        
        # Test 3: Complex code parsing
        def complex_code_test():
            complex_files = self.test_data_manager.get_complex_patterns()
            if complex_files:
                filename, content = next(iter(complex_files.items()))
                return plugin.indexFile(Path(filename), content)
            else:
                content = self.test_data_manager.generate_large_file(100)
                return plugin.indexFile(Path(f"complex.{self.language}"), content)
        
        result3 = self.compare_backends(
            plugin, treesitter_backend, regex_backend,
            "complex_code_parsing", complex_code_test, iterations=5
        )
        comparison_results.append(result3)
        
        # Test 4: Error handling
        def error_handling_test():
            invalid_files = self.test_data_manager.get_invalid_syntax_files()
            if invalid_files:
                filename, content = next(iter(invalid_files.items()))
                return plugin.indexFile(Path(filename), content)
            else:
                return plugin.indexFile(Path(f"empty.{self.language}"), "")
        
        result4 = self.compare_backends(
            plugin, treesitter_backend, regex_backend,
            "error_handling", error_handling_test, iterations=10
        )
        comparison_results.append(result4)
        
        return comparison_results
    
    def compare_accuracy(self, plugin: IPlugin, backend_a: str, backend_b: str) -> ComparisonResult:
        """Compare symbol extraction accuracy between backends."""
        accuracy_cases = self.test_data_manager.get_accuracy_test_files()
        
        def accuracy_test():
            total_expected = 0
            total_found = 0
            
            for case in accuracy_cases:
                result = plugin.indexFile(Path(case.file), case.content)
                symbols = result.get("symbols", [])
                
                expected_names = {s.name for s in case.expected_symbols}
                found_names = {s.get("symbol", s.get("name")) for s in symbols}
                
                total_expected += len(expected_names)
                total_found += len(expected_names & found_names)
            
            accuracy = total_found / total_expected if total_expected > 0 else 0
            return {"symbols": [{"accuracy": accuracy}]}
        
        return self.compare_backends(
            plugin, backend_a, backend_b,
            "accuracy_comparison", accuracy_test, iterations=5
        )
    
    # ===== Cross-Plugin Comparisons =====
    
    def compare_plugins(self,
                       plugin_a: IPlugin,
                       plugin_b: IPlugin,
                       plugin_a_name: str,
                       plugin_b_name: str) -> List[ComparisonResult]:
        """Compare two different plugin implementations."""
        
        if plugin_a.lang != plugin_b.lang:
            raise ValueError("Plugins must be for the same language")
        
        print(f"Comparing {plugin_a_name} vs {plugin_b_name}")
        
        comparison_results = []
        
        # Test 1: Basic indexing performance
        def indexing_test(plugin):
            content = self.test_data_manager.generate_medium_file(25)
            return plugin.indexFile(Path(f"test.{self.language}"), content)
        
        result1 = self._compare_plugin_operations(
            plugin_a, plugin_b, plugin_a_name, plugin_b_name,
            "indexing_performance", indexing_test, iterations=10
        )
        comparison_results.append(result1)
        
        # Test 2: Symbol extraction accuracy
        def accuracy_test(plugin):
            accuracy_cases = self.test_data_manager.get_accuracy_test_files()
            if accuracy_cases:
                case = accuracy_cases[0]
                result = plugin.indexFile(Path(case.file), case.content)
                symbols = result.get("symbols", [])
                
                expected_names = {s.name for s in case.expected_symbols}
                found_names = {s.get("symbol", s.get("name")) for s in symbols}
                
                accuracy = len(expected_names & found_names) / len(expected_names) if expected_names else 0
                return {"symbols": [{"accuracy": accuracy}]}
            return {"symbols": []}
        
        result2 = self._compare_plugin_operations(
            plugin_a, plugin_b, plugin_a_name, plugin_b_name,
            "accuracy_comparison", accuracy_test, iterations=5
        )
        comparison_results.append(result2)
        
        return comparison_results
    
    def _compare_plugin_operations(self,
                                  plugin_a: IPlugin,
                                  plugin_b: IPlugin,
                                  name_a: str,
                                  name_b: str,
                                  test_name: str,
                                  test_operation: callable,
                                  iterations: int = 10) -> ComparisonResult:
        """Compare the same operation on two different plugins."""
        
        print(f"  Testing {name_a}...")
        metrics_a = self._run_plugin_performance_test(plugin_a, test_operation, iterations)
        
        print(f"  Testing {name_b}...")
        metrics_b = self._run_plugin_performance_test(plugin_b, test_operation, iterations)
        
        # Compare metrics
        comparison_metrics = []
        
        for metric_name in ["execution_time", "symbols_extracted"]:
            value_a = metrics_a.get(metric_name, 0)
            value_b = metrics_b.get(metric_name, 0)
            
            if value_a > 0 and value_b > 0:
                if metric_name == "execution_time":
                    # Lower is better
                    improvement_ratio = value_a / value_b
                    better_backend = name_b if value_b < value_a else name_a
                else:
                    # Higher is better
                    improvement_ratio = value_b / value_a
                    better_backend = name_b if value_b > value_a else name_a
                
                comparison_metrics.append(ComparisonMetric(
                    name=metric_name,
                    backend_a=value_a,
                    backend_b=value_b,
                    unit=self._get_metric_unit(metric_name),
                    improvement_ratio=improvement_ratio,
                    better_backend=better_backend
                ))
        
        # Determine overall winner
        backend_wins = {}
        for metric in comparison_metrics:
            backend_wins[metric.better_backend] = backend_wins.get(metric.better_backend, 0) + 1
        
        overall_winner = max(backend_wins, key=backend_wins.get) if backend_wins else "tie"
        
        return ComparisonResult(
            test_name=test_name,
            backend_a_name=name_a,
            backend_b_name=name_b,
            metrics=comparison_metrics,
            overall_winner=overall_winner,
            timestamp=datetime.now().isoformat(),
            language=self.language
        )
    
    def _run_plugin_performance_test(self, plugin: IPlugin, test_operation: callable, iterations: int) -> Dict[str, float]:
        """Run performance test on a specific plugin."""
        execution_times = []
        symbol_counts = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                result = test_operation(plugin)
                end_time = time.time()
                
                execution_times.append(end_time - start_time)
                
                if isinstance(result, dict):
                    symbols = result.get("symbols", [])
                    symbol_counts.append(len(symbols))
                
            except Exception as e:
                end_time = time.time()
                execution_times.append(end_time - start_time)
                symbol_counts.append(0)
        
        return {
            "execution_time": statistics.mean(execution_times),
            "symbols_extracted": statistics.mean(symbol_counts) if symbol_counts else 0
        }
    
    # ===== Specialized Comparisons =====
    
    def compare_backend_switching_overhead(self, plugin: IPlugin) -> ComparisonResult:
        """Compare overhead of switching between backends."""
        if not hasattr(plugin, 'get_parser_info'):
            raise ValueError("Plugin does not support backend switching")
        
        parser_info = plugin.get_parser_info()
        available_backends = parser_info.get("available_backends", [])
        
        if len(available_backends) < 2:
            raise ValueError("Need at least 2 backends to test switching overhead")
        
        backend_a, backend_b = available_backends[:2]
        
        def no_switching_test():
            # Ensure we're on backend_a
            plugin.switch_parser_backend(backend_a)
            
            content = self.test_data_manager.generate_small_file(10)
            results = []
            
            for i in range(5):
                result = plugin.indexFile(Path(f"no_switch_{i}.{self.language}"), content)
                results.append(result)
            
            return {"symbols": [{"count": len(results)}]}
        
        def with_switching_test():
            content = self.test_data_manager.generate_small_file(10)
            results = []
            
            for i in range(5):
                # Switch backend before each operation
                backend = backend_a if i % 2 == 0 else backend_b
                plugin.switch_parser_backend(backend)
                
                result = plugin.indexFile(Path(f"with_switch_{i}.{self.language}"), content)
                results.append(result)
            
            return {"symbols": [{"count": len(results)}]}
        
        return self.compare_backends(
            plugin, "no_switching", "with_switching",
            "backend_switching_overhead", 
            lambda: no_switching_test() if plugin.get_parser_info()["current_backend"] == backend_a else with_switching_test(),
            iterations=5
        )
    
    def compare_unicode_handling(self, plugin: IPlugin, backend_a: str, backend_b: str) -> ComparisonResult:
        """Compare Unicode text handling between backends."""
        unicode_files = self.test_data_manager.get_unicode_test_files()
        
        def unicode_test():
            results = []
            for filename, content in unicode_files.items():
                try:
                    result = plugin.indexFile(Path(filename), content)
                    results.append(result)
                except Exception:
                    pass
            
            return {"symbols": [{"files_processed": len(results)}]}
        
        return self.compare_backends(
            plugin, backend_a, backend_b,
            "unicode_handling", unicode_test, iterations=5
        )
    
    # ===== Results Analysis =====
    
    def get_comparison_summary(self) -> Dict[str, Any]:
        """Get summary of all comparison results."""
        if not self.results:
            return {"error": "No comparison results available"}
        
        summary = {
            "language": self.language,
            "total_comparisons": len(self.results),
            "comparisons": {}
        }
        
        # Aggregate wins by backend/plugin
        backend_wins = {}
        
        for result in self.results:
            # Count wins
            winner = result.overall_winner
            backend_wins[winner] = backend_wins.get(winner, 0) + 1
            
            # Store detailed results
            summary["comparisons"][result.test_name] = {
                "backend_a": result.backend_a_name,
                "backend_b": result.backend_b_name,
                "winner": result.overall_winner,
                "metrics": [asdict(m) for m in result.metrics],
                "timestamp": result.timestamp
            }
        
        summary["overall_performance"] = {
            "wins_by_backend": backend_wins,
            "best_overall": max(backend_wins, key=backend_wins.get) if backend_wins else None
        }
        
        return summary
    
    def export_comparison_results(self, filename: Optional[str] = None) -> str:
        """Export comparison results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comparison_results_{self.language}_{timestamp}.json"
        
        export_data = {
            "metadata": {
                "language": self.language,
                "export_time": datetime.now().isoformat(),
                "total_comparisons": len(self.results)
            },
            "summary": self.get_comparison_summary(),
            "detailed_results": [asdict(result) for result in self.results]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Comparison results exported to: {filename}")
        return filename
    
    def print_comparison_report(self):
        """Print a detailed comparison report."""
        summary = self.get_comparison_summary()
        
        print(f"\n{'='*60}")
        print(f"BACKEND COMPARISON REPORT")
        print(f"{'='*60}")
        print(f"Language: {summary['language']}")
        print(f"Total comparisons: {summary['total_comparisons']}")
        
        if "overall_performance" in summary:
            performance = summary["overall_performance"]
            wins = performance.get("wins_by_backend", {})
            
            print(f"\nOverall Performance Wins:")
            for backend, win_count in sorted(wins.items(), key=lambda x: x[1], reverse=True):
                print(f"  {backend}: {win_count} wins")
            
            if performance.get("best_overall"):
                print(f"\nBest Overall Backend: {performance['best_overall']}")
        
        print(f"\nDetailed Results:")
        print("-" * 60)
        
        for test_name, test_data in summary["comparisons"].items():
            print(f"\n{test_name}:")
            print(f"  {test_data['backend_a']} vs {test_data['backend_b']}")
            print(f"  Winner: {test_data['winner']}")
            
            for metric in test_data["metrics"]:
                print(f"    {metric['name']}: "
                      f"{metric['backend_a']:.4f} vs {metric['backend_b']:.4f} {metric['unit']} "
                      f"(Improvement: {metric['improvement_ratio']:.2f}x)")
        
        print("-" * 60)