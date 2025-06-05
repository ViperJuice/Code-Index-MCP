"""
Example test using the plugin testing framework for Python plugin.

This demonstrates how to use the framework to test a language plugin.
"""

import pytest
from pathlib import Path

from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from tests.plugin_framework import PluginTestBase, PerformanceTestBase, BenchmarkSuite


class TestPythonPluginExample(PluginTestBase):
    """Example test class using the plugin testing framework."""
    
    plugin_class = PythonPlugin
    language = "python"
    file_extensions = [".py"]
    
    def test_framework_usage_example(self):
        """Example test showing framework usage."""
        # The framework provides test data management
        content = self.test_data_manager.get_simple_content()
        
        # Index the content
        result = self.plugin.indexFile(Path("example.py"), content)
        
        # Use framework validation methods
        self.assert_valid_index_result(result)
        
        # Get symbols by kind
        functions = self.get_symbols_by_kind(result["symbols"], "function")
        classes = self.get_symbols_by_kind(result["symbols"], "class")
        
        assert len(functions) > 0
        assert len(classes) > 0
    
    def test_accuracy_validation_example(self):
        """Example test showing accuracy validation."""
        # Get accuracy test data with expected symbols
        accuracy_cases = self.test_data_manager.get_accuracy_test_files()
        
        for case in accuracy_cases:
            result = self.plugin.indexFile(Path(case.file), case.content)
            
            # Extract symbol names
            actual_names = self.get_symbol_names(result["symbols"])
            expected_names = {s.name for s in case.expected_symbols}
            
            # Check accuracy
            missing_symbols = expected_names - actual_names
            assert not missing_symbols, f"Missing symbols: {missing_symbols}"
    
    def test_parser_backend_example(self):
        """Example test showing parser backend testing."""
        if hasattr(self.plugin, 'get_parser_info'):
            parser_info = self.plugin.get_parser_info()
            print(f"Current backend: {parser_info['current_backend']}")
            print(f"Available backends: {parser_info['available_backends']}")
            
            # Test switching backends
            for backend in parser_info["available_backends"]:
                success = self.plugin.switch_parser_backend(backend)
                if success:
                    content = self.test_data_manager.get_simple_content()
                    result = self.plugin.indexFile(Path("backend_test.py"), content)
                    self.assert_valid_index_result(result)


class TestPythonPerformanceExample(PerformanceTestBase):
    """Example performance test class."""
    
    plugin_class = PythonPlugin
    language = "python"
    file_extensions = [".py"]
    
    def test_performance_example(self):
        """Example performance test."""
        # Test small file performance
        result = self.test_small_file_performance()
        print(f"Small file avg time: {result.summary['duration_mean']:.4f}s")
        
        # Test memory scaling
        self.test_memory_usage_scaling()
        
        # Print performance summary
        self.print_performance_summary()


class TestBenchmarkSuiteExample:
    """Example using the benchmark suite directly."""
    
    def test_benchmark_suite_usage(self):
        """Example of using BenchmarkSuite directly."""
        plugin = PythonPlugin()
        benchmark_suite = BenchmarkSuite(plugin, "python")
        
        # Run individual benchmarks
        small_file_result = benchmark_suite.benchmark_small_file_indexing()
        accuracy_result = benchmark_suite.benchmark_symbol_extraction_accuracy()
        
        # Check results
        assert small_file_result.success_rate > 0.95
        assert accuracy_result.success_rate > 0.9
        
        # Get summary
        summary = benchmark_suite.get_performance_summary()
        assert summary["language"] == "python"
        assert summary["total_benchmarks"] >= 2
        
        print(f"Benchmark summary: {summary['total_benchmarks']} tests run")


@pytest.mark.benchmark
def test_standalone_benchmark_example():
    """Example standalone benchmark test."""
    plugin = PythonPlugin()
    benchmark_suite = BenchmarkSuite(plugin, "python")
    
    # Run a subset of benchmarks
    results = []
    results.append(benchmark_suite.benchmark_small_file_indexing())
    results.append(benchmark_suite.benchmark_medium_file_indexing())
    results.append(benchmark_suite.benchmark_concurrent_indexing())
    
    # Verify all succeeded
    for result in results:
        assert result.success_rate >= 0.9, f"Test {result.test_name} had low success rate"
        assert result.duration_seconds < 60, f"Test {result.test_name} took too long"
    
    print(f"Successfully ran {len(results)} benchmark tests")


@pytest.mark.integration
def test_framework_integration_example():
    """Example integration test using the framework."""
    from tests.plugin_framework import IntegrationTestBase
    from mcp_server.storage.sqlite_store import SQLiteStore
    
    # Create integration test instance
    class TempIntegrationTest(IntegrationTestBase):
        plugin_class = PythonPlugin
        language = "python"
        file_extensions = [".py"]
    
    # Initialize test
    test_instance = TempIntegrationTest()
    test_instance.setup_method()
    
    try:
        # Test full integration scenario
        scenario = test_instance.setup_full_integration_scenario()
        
        assert scenario["repo_id"] is not None
        assert len(scenario["test_files"]) >= 3
        assert scenario["temp_dir"].exists()
        
        print(f"Integration scenario created with {len(scenario['test_files'])} files")
        
    finally:
        test_instance.teardown_method()


if __name__ == "__main__":
    # Example of running benchmarks standalone
    plugin = PythonPlugin()
    benchmark_suite = BenchmarkSuite(plugin, "python")
    
    print("Running example benchmarks...")
    results = benchmark_suite.run_complete_benchmark_suite()
    
    print(f"\nCompleted {len(results)} benchmarks")
    benchmark_suite.print_performance_report()
    
    # Export results
    filename = benchmark_suite.export_results("example_benchmark_results.json")
    print(f"Results exported to: {filename}")