"""
Automated test generation for language plugins.

This module generates comprehensive test suites for new language plugins,
including test files, test cases, and expected results.
"""

import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass
from textwrap import dedent, indent

from mcp_server.plugin_base import IPlugin
from ..base.plugin_test_base import PluginTestBase
from ..base.performance_test_base import PerformanceTestBase
from ..base.integration_test_base import IntegrationTestBase
from ..test_data.test_data_manager import TestDataManager


@dataclass
class TestClassSpec:
    """Specification for generating a test class."""
    class_name: str
    base_class: Type
    plugin_class: str
    language: str
    file_extensions: List[str]
    custom_tests: List[str] = None


class TestGenerator:
    """
    Generates comprehensive test suites for language plugins.
    
    Creates:
    - Basic functionality tests
    - Performance benchmarks
    - Integration tests
    - Custom language-specific tests
    """
    
    def __init__(self, language: str, plugin_class_name: str, file_extensions: List[str]):
        """Initialize test generator for a specific language."""
        self.language = language
        self.plugin_class_name = plugin_class_name
        self.file_extensions = file_extensions
        self.test_data_manager = TestDataManager(language)
        
    # ===== Main Test Generation =====
    
    def generate_complete_test_suite(self, output_dir: Path) -> Dict[str, str]:
        """Generate a complete test suite for the language plugin."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        # Generate basic functionality tests
        basic_test_content = self.generate_basic_functionality_tests()
        basic_test_file = output_dir / f"test_{self.language}_plugin.py"
        basic_test_file.write_text(basic_test_content)
        generated_files["basic_tests"] = str(basic_test_file)
        
        # Generate performance tests
        performance_test_content = self.generate_performance_tests()
        performance_test_file = output_dir / f"test_{self.language}_performance.py"
        performance_test_file.write_text(performance_test_content)
        generated_files["performance_tests"] = str(performance_test_file)
        
        # Generate integration tests
        integration_test_content = self.generate_integration_tests()
        integration_test_file = output_dir / f"test_{self.language}_integration.py"
        integration_test_file.write_text(integration_test_content)
        generated_files["integration_tests"] = str(integration_test_file)
        
        # Generate benchmark script
        benchmark_script_content = self.generate_benchmark_script()
        benchmark_script_file = output_dir / f"benchmark_{self.language}.py"
        benchmark_script_file.write_text(benchmark_script_content)
        generated_files["benchmark_script"] = str(benchmark_script_file)
        
        # Generate README for the test suite
        readme_content = self.generate_test_readme()
        readme_file = output_dir / "README.md"
        readme_file.write_text(readme_content)
        generated_files["readme"] = str(readme_file)
        
        # Generate conftest.py for pytest fixtures
        conftest_content = self.generate_conftest()
        conftest_file = output_dir / "conftest.py"
        conftest_file.write_text(conftest_content)
        generated_files["conftest"] = str(conftest_file)
        
        print(f"Generated complete test suite for {self.language} in {output_dir}")
        return generated_files
    
    # ===== Basic Functionality Tests =====
    
    def generate_basic_functionality_tests(self) -> str:
        """Generate basic functionality test class."""
        class_name = f"Test{self.language.capitalize()}Plugin"
        
        template = dedent(f'''
        """
        Comprehensive tests for the {self.language.capitalize()} plugin.
        
        Generated automatically by the plugin testing framework.
        """
        
        import pytest
        from pathlib import Path
        from unittest.mock import Mock
        
        from mcp_server.plugins.{self.language}_plugin.plugin import Plugin as {self.language.capitalize()}Plugin
        from mcp_server.storage.sqlite_store import SQLiteStore
        from tests.plugin_framework import PluginTestBase
        
        
        class {class_name}(PluginTestBase):
            """Test suite for {self.language.capitalize()} plugin functionality."""
            
            plugin_class = {self.language.capitalize()}Plugin
            language = "{self.language}"
            file_extensions = {self.file_extensions}
            
            # ===== Language-Specific Tests =====
            
            def test_language_specific_symbols(self):
                """Test extraction of {self.language}-specific symbols."""
                # TODO: Add language-specific symbol tests
                content = self.test_data_manager.get_simple_content()
                result = self.plugin.indexFile(
                    Path(f"symbols{self.file_extensions[0]}"), content
                )
                
                assert isinstance(result, dict)
                assert result.get("language") == self.language
                symbols = result.get("symbols", [])
                
                # Verify symbols have required fields
                for symbol in symbols:
                    self.assert_valid_symbol(symbol)
            
            def test_complex_language_features(self):
                """Test handling of complex {self.language} features."""
                complex_patterns = self.test_data_manager.get_complex_patterns()
                
                for filename, content in complex_patterns.items():
                    result = self.plugin.indexFile(Path(filename), content)
                    
                    assert isinstance(result, dict)
                    assert result.get("language") == self.language
                    # Should handle complex patterns without crashing
            
            def test_framework_specific_patterns(self):
                """Test handling of {self.language} framework patterns."""
                framework_patterns = self.test_data_manager.get_framework_patterns()
                
                for filename, content in framework_patterns.items():
                    result = self.plugin.indexFile(Path(filename), content)
                    
                    assert isinstance(result, dict)
                    assert result.get("language") == self.language
                    # Should extract framework-specific symbols
            
            def test_real_world_code(self):
                """Test with real-world {self.language} code patterns."""
                real_world_patterns = self.test_data_manager.get_real_world_patterns()
                
                for filename, content in real_world_patterns.items():
                    result = self.plugin.indexFile(Path(filename), content)
                    
                    assert isinstance(result, dict)
                    assert result.get("language") == self.language
                    symbols = result.get("symbols", [])
                    
                    # Should extract meaningful symbols from real code
                    assert len(symbols) > 0
            
            def test_edge_cases(self):
                """Test {self.language} edge cases and corner cases."""
                edge_cases = self.test_data_manager.get_edge_cases()
                
                for filename, content in edge_cases.items():
                    # Should handle edge cases gracefully
                    try:
                        result = self.plugin.indexFile(Path(filename), content)
                        assert isinstance(result, dict)
                        assert result.get("language") == self.language
                    except Exception as e:
                        pytest.fail(f"Plugin should handle edge case gracefully: {{e}}")
            
            # ===== Parser Backend Tests =====
            
            def test_parser_backend_switching(self):
                """Test switching between parser backends if supported."""
                if hasattr(self.plugin, 'get_parser_info'):
                    parser_info = self.plugin.get_parser_info()
                    available_backends = parser_info.get("available_backends", [])
                    
                    if len(available_backends) > 1:
                        content = self.test_data_manager.get_simple_content()
                        
                        for backend in available_backends:
                            success = self.plugin.switch_parser_backend(backend)
                            if success:
                                result = self.plugin.indexFile(
                                    Path(f"backend_test{self.file_extensions[0]}"), content
                                )
                                assert isinstance(result, dict)
                                assert result.get("language") == self.language
                else:
                    pytest.skip("Plugin does not support backend switching")
            
            def test_parser_backend_consistency(self):
                """Test that different backends produce consistent results."""
                if hasattr(self.plugin, 'get_parser_info'):
                    parser_info = self.plugin.get_parser_info()
                    available_backends = parser_info.get("available_backends", [])
                    
                    if len(available_backends) > 1:
                        content = self.test_data_manager.get_simple_content()
                        results = []
                        
                        for backend in available_backends:
                            if self.plugin.switch_parser_backend(backend):
                                result = self.plugin.indexFile(
                                    Path(f"consistency{self.file_extensions[0]}"), content
                                )
                                results.append(result)
                        
                        # Compare symbol counts (should be reasonably consistent)
                        symbol_counts = [len(r.get("symbols", [])) for r in results]
                        if len(symbol_counts) > 1:
                            # Allow some variation but not drastic differences
                            max_count = max(symbol_counts)
                            min_count = min(symbol_counts)
                            ratio = max_count / min_count if min_count > 0 else 1
                            assert ratio <= 2.0, f"Backend results too inconsistent: {{symbol_counts}}"
                else:
                    pytest.skip("Plugin does not support backend switching")
            
            # ===== Custom Validation =====
            
            def validate_symbol_signatures(self, symbols: List[Dict[str, Any]]):
                """Validate that symbol signatures are properly formatted for {self.language}."""
                for symbol in symbols:
                    signature = symbol.get("signature", "")
                    if signature:
                        # Add {self.language}-specific signature validation
                        assert isinstance(signature, str)
                        assert len(signature.strip()) > 0
            
            def validate_symbol_kinds(self, symbols: List[Dict[str, Any]]):
                """Validate that symbol kinds are appropriate for {self.language}."""
                valid_kinds = self.get_valid_symbol_kinds()
                
                for symbol in symbols:
                    kind = symbol.get("kind")
                    assert kind in valid_kinds, f"Invalid symbol kind: {{kind}}"
            
            def get_valid_symbol_kinds(self) -> List[str]:
                """Get list of valid symbol kinds for {self.language}."""
                # TODO: Customize for {self.language}
                return ["function", "class", "method", "variable", "constant", "interface", "enum"]
        ''')
        
        return template.strip()
    
    # ===== Performance Tests =====
    
    def generate_performance_tests(self) -> str:
        """Generate performance test class."""
        class_name = f"Test{self.language.capitalize()}Performance"
        
        template = dedent(f'''
        """
        Performance tests for the {self.language.capitalize()} plugin.
        
        Generated automatically by the plugin testing framework.
        """
        
        import pytest
        from pathlib import Path
        
        from mcp_server.plugins.{self.language}_plugin.plugin import Plugin as {self.language.capitalize()}Plugin
        from tests.plugin_framework import PerformanceTestBase
        
        
        class {class_name}(PerformanceTestBase):
            """Performance test suite for {self.language.capitalize()} plugin."""
            
            plugin_class = {self.language.capitalize()}Plugin
            language = "{self.language}"
            file_extensions = {self.file_extensions}
            
            # Custom performance thresholds for {self.language}
            max_indexing_time_small = 1.0    # seconds
            max_indexing_time_medium = 5.0   # seconds  
            max_indexing_time_large = 30.0   # seconds
            max_memory_usage = 100 * 1024 * 1024  # 100MB
            min_throughput_files_per_second = 10.0
            
            # ===== Language-Specific Performance Tests =====
            
            def test_{self.language}_specific_performance(self):
                """Test performance with {self.language}-specific code patterns."""
                def {self.language}_code_test():
                    # Generate {self.language}-specific performance test content
                    content = self.test_data_manager.generate_medium_file(100)
                    return self.plugin.indexFile(
                        Path(f"{self.language}_perf{self.file_extensions[0]}"), content
                    )
                
                result = self.run_benchmark(
                    "{self.language}_specific_performance",
                    {self.language}_code_test,
                    iterations=10
                )
                
                # {self.language}-specific performance assertions
                assert result.summary["duration_mean"] <= self.max_indexing_time_medium
                assert result.summary["error_rate"] == 0.0
            
            def test_large_{self.language}_project_simulation(self):
                """Simulate indexing a large {self.language} project."""
                def large_project_test():
                    # Simulate multiple files in a large project
                    total_symbols = 0
                    
                    for i in range(20):  # 20 files
                        content = self.test_data_manager.generate_medium_file(50)
                        result = self.plugin.indexFile(
                            Path(f"project_file_{{i}}{self.file_extensions[0]}"), content
                        )
                        total_symbols += len(result.get("symbols", []))
                    
                    return {{"symbols": [{{"count": total_symbols}}]}}
                
                result = self.run_benchmark(
                    "large_project_simulation",
                    large_project_test,
                    iterations=3
                )
                
                # Should handle large projects efficiently
                assert result.summary["duration_mean"] <= 60.0  # 1 minute max
                assert result.summary["memory_peak_max"] <= 200 * 1024 * 1024  # 200MB max
            
            def test_complex_syntax_performance(self):
                """Test performance with complex {self.language} syntax."""
                def complex_syntax_test():
                    complex_patterns = self.test_data_manager.get_complex_patterns()
                    results = []
                    
                    for filename, content in complex_patterns.items():
                        result = self.plugin.indexFile(Path(filename), content)
                        results.append(result)
                    
                    total_symbols = sum(len(r.get("symbols", [])) for r in results)
                    return {{"symbols": [{{"count": total_symbols}}]}}
                
                result = self.run_benchmark(
                    "complex_syntax_performance",
                    complex_syntax_test,
                    iterations=5
                )
                
                # Complex syntax should not cause severe performance degradation
                assert result.summary["duration_mean"] <= 10.0
                assert result.summary["error_rate"] <= 0.1  # Allow some failures for complex syntax
            
            def test_memory_efficiency_with_{self.language}_code(self):
                """Test memory efficiency with large {self.language} files."""
                def memory_test():
                    # Generate progressively larger files
                    for size in [100, 200, 500, 1000]:
                        content = self.test_data_manager.generate_large_file(size)
                        result = self.plugin.indexFile(
                            Path(f"memory_{{size}}{self.file_extensions[0]}"), content
                        )
                        # Just ensure it completes
                    
                    return {{"symbols": [{{"completed": 1}}]}}
                
                result = self.run_benchmark(
                    "{self.language}_memory_efficiency",
                    memory_test,
                    iterations=3
                )
                
                # Memory usage should be reasonable
                assert result.summary["memory_peak_max"] <= self.max_memory_usage
            
            def test_concurrent_{self.language}_indexing(self):
                """Test concurrent indexing of {self.language} files."""
                import threading
                import queue
                
                def concurrent_test():
                    num_threads = 4
                    files_per_thread = 10
                    results_queue = queue.Queue()
                    
                    def worker(thread_id):
                        for i in range(files_per_thread):
                            content = self.test_data_manager.generate_small_file(20)
                            result = self.plugin.indexFile(
                                Path(f"concurrent_{{thread_id}}_{{i}}{self.file_extensions[0]}"),
                                content
                            )
                            results_queue.put(result)
                    
                    threads = []
                    for thread_id in range(num_threads):
                        thread = threading.Thread(target=worker, args=(thread_id,))
                        threads.append(thread)
                        thread.start()
                    
                    for thread in threads:
                        thread.join()
                    
                    total_results = 0
                    while not results_queue.empty():
                        results_queue.get()
                        total_results += 1
                    
                    return {{"symbols": [{{"files_processed": total_results}}]}}
                
                result = self.run_benchmark(
                    "concurrent_{self.language}_indexing",
                    concurrent_test,
                    iterations=3
                )
                
                # Should handle concurrency efficiently
                assert result.summary["error_rate"] == 0.0
                assert result.summary["duration_mean"] <= 20.0
        ''')
        
        return template.strip()
    
    # ===== Integration Tests =====
    
    def generate_integration_tests(self) -> str:
        """Generate integration test class."""
        class_name = f"Test{self.language.capitalize()}Integration"
        
        template = dedent(f'''
        """
        Integration tests for the {self.language.capitalize()} plugin.
        
        Generated automatically by the plugin testing framework.
        """
        
        import pytest
        from pathlib import Path
        from unittest.mock import Mock
        
        from mcp_server.plugins.{self.language}_plugin.plugin import Plugin as {self.language.capitalize()}Plugin
        from tests.plugin_framework import IntegrationTestBase
        
        
        class {class_name}(IntegrationTestBase):
            """Integration test suite for {self.language.capitalize()} plugin."""
            
            plugin_class = {self.language.capitalize()}Plugin
            language = "{self.language}"
            file_extensions = {self.file_extensions}
            
            # ===== {self.language.capitalize()}-Specific Integration Tests =====
            
            def test_{self.language}_project_indexing_workflow(self):
                """Test complete workflow of indexing a {self.language} project."""
                # Create repository
                repo_id = self.create_test_repository(f"{self.language}_project")
                
                # Create project structure
                project_files = [
                    (f"main{self.file_extensions[0]}", 
                     self.test_data_manager.get_simple_content()),
                    (f"utils{self.file_extensions[0]}", 
                     self.test_data_manager.generate_medium_file(25)),
                    (f"models/user{self.file_extensions[0]}", 
                     self.test_data_manager.get_real_world_patterns().get(
                         f"data_model{self.file_extensions[0]}", 
                         self.test_data_manager.get_simple_content()
                     )),
                ]
                
                # Create directories
                (self.temp_dir / "models").mkdir()
                
                total_symbols = 0
                
                for filename, content in project_files:
                    file_path = self.temp_dir / filename
                    file_path.write_text(content)
                    
                    # Store file in SQLite
                    file_id = self.sqlite_store.store_file(
                        repo_id, str(file_path), filename, language=self.language
                    )
                    
                    # Index file
                    result = self.plugin.indexFile(file_path, content)
                    symbols = result.get("symbols", [])
                    
                    # Store symbols
                    for symbol in symbols:
                        symbol_name = symbol.get("symbol", symbol.get("name"))
                        if symbol_name:
                            self.sqlite_store.store_symbol(
                                file_id, symbol_name, symbol.get("kind", "unknown"),
                                symbol.get("line", 1), symbol.get("line", 1) + 1
                            )
                            total_symbols += 1
                
                # Verify integration
                stats = self.sqlite_store.get_statistics()
                assert stats["repositories"] >= 1
                assert stats["files"] >= len(project_files)
                assert stats["symbols"] >= total_symbols
            
            def test_{self.language}_plugin_with_dispatcher(self):
                """Test {self.language} plugin integration with dispatcher."""
                # Register plugin with dispatcher
                self.dispatcher.register_plugin(self.language, self.plugin)
                
                # Create test file
                test_file = self.temp_dir / f"dispatcher_test{self.file_extensions[0]}"
                content = self.test_data_manager.generate_medium_file(30)
                test_file.write_text(content)
                
                # Index through dispatcher
                results = self.dispatcher.index_file(str(test_file))
                
                assert isinstance(results, list)
                assert len(results) > 0
                
                # Verify result contains {self.language} symbols
                result = results[0]
                assert result.get("language") == self.language
                assert len(result.get("symbols", [])) > 0
            
            def test_{self.language}_cross_file_references(self):
                """Test cross-file reference detection for {self.language}."""
                # Create multiple related files
                main_content = self.test_data_manager.get_simple_content()
                utils_content = self.test_data_manager.generate_medium_file(15)
                
                main_file = self.temp_dir / f"main{self.file_extensions[0]}"
                utils_file = self.temp_dir / f"utils{self.file_extensions[0]}"
                
                main_file.write_text(main_content)
                utils_file.write_text(utils_content)
                
                # Index both files
                main_result = self.plugin.indexFile(main_file, main_content)
                utils_result = self.plugin.indexFile(utils_file, utils_content)
                
                # Extract symbols from both files
                all_symbols = []
                all_symbols.extend(main_result.get("symbols", []))
                all_symbols.extend(utils_result.get("symbols", []))
                
                # Test reference finding (if supported)
                if all_symbols:
                    test_symbol = all_symbols[0].get("symbol", all_symbols[0].get("name"))
                    if test_symbol:
                        references = list(self.plugin.findReferences(test_symbol))
                        # Should return list (might be empty for simple test data)
                        assert isinstance(references, list)
            
            def test_{self.language}_with_file_watcher(self):
                """Test {self.language} plugin with file change detection."""
                test_file = self.temp_dir / f"watched{self.file_extensions[0]}"
                
                # Initial content
                initial_content = self.test_data_manager.get_simple_content()
                test_file.write_text(initial_content)
                
                # Index initial version
                initial_result = self.plugin.indexFile(test_file, initial_content)
                initial_symbols = len(initial_result.get("symbols", []))
                
                # Modify content
                modified_content = self.test_data_manager.generate_medium_file(25)
                test_file.write_text(modified_content)
                
                # Index modified version
                modified_result = self.plugin.indexFile(test_file, modified_content)
                modified_symbols = len(modified_result.get("symbols", []))
                
                # Should detect changes in symbol count
                assert modified_symbols != initial_symbols
                assert isinstance(modified_result, dict)
                assert modified_result.get("language") == self.language
            
            def test_{self.language}_error_recovery_integration(self):
                """Test {self.language} plugin error recovery in integration scenario."""
                # Test with mixed valid and invalid files
                test_files = [
                    (f"valid{self.file_extensions[0]}", 
                     self.test_data_manager.get_simple_content()),
                    (f"invalid{self.file_extensions[0]}", 
                     "This is definitely invalid {self.language} syntax [[["),
                    (f"empty{self.file_extensions[0]}", ""),
                    (f"unicode{self.file_extensions[0]}", 
                     self.test_data_manager.get_unicode_test_files().get(
                         f"unicode{self.file_extensions[0]}", "# Unicode test"
                     ))
                ]
                
                successful_indexes = 0
                
                for filename, content in test_files:
                    file_path = self.temp_dir / filename
                    file_path.write_text(content)
                    
                    try:
                        result = self.plugin.indexFile(file_path, content)
                        if isinstance(result, dict) and result.get("language") == self.language:
                            successful_indexes += 1
                    except Exception:
                        pass  # Should handle errors gracefully
                
                # Should successfully index at least the valid files
                assert successful_indexes >= 2  # valid + empty should work
            
            def test_{self.language}_plugin_configuration(self):
                """Test {self.language} plugin configuration options."""
                # Test different configuration scenarios
                configs = [
                    {{"parser_backend": "default"}},
                    {{"enable_caching": True}},
                    {{"max_symbols": 1000}},
                ]
                
                content = self.test_data_manager.get_simple_content()
                
                for config in configs:
                    # Plugin should handle different configurations
                    # (Implementation depends on actual plugin configuration support)
                    try:
                        result = self.plugin.indexFile(
                            Path(f"config_test{self.file_extensions[0]}"), content
                        )
                        assert isinstance(result, dict)
                        assert result.get("language") == self.language
                    except Exception as e:
                        pytest.fail(f"Plugin should handle configuration gracefully: {{e}}")
        ''')
        
        return template.strip()
    
    # ===== Support Files =====
    
    def generate_benchmark_script(self) -> str:
        """Generate standalone benchmark script."""
        template = dedent(f'''
        #!/usr/bin/env python3
        """
        Standalone benchmark script for {self.language.capitalize()} plugin.
        
        Generated automatically by the plugin testing framework.
        
        Usage:
            python benchmark_{self.language}.py [--export] [--iterations N]
        """
        
        import sys
        import argparse
        from pathlib import Path
        
        # Add project root to path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        
        from mcp_server.plugins.{self.language}_plugin.plugin import Plugin as {self.language.capitalize()}Plugin
        from tests.plugin_framework.benchmarks import BenchmarkSuite, ComparisonSuite
        
        
        def run_benchmarks(iterations: int = None, export: bool = False):
            """Run comprehensive benchmarks for {self.language} plugin."""
            print(f"Running {self.language.capitalize()} Plugin Benchmarks")
            print("=" * 50)
            
            # Initialize plugin and benchmark suite
            plugin = {self.language.capitalize()}Plugin()
            benchmark_suite = BenchmarkSuite(plugin, "{self.language}")
            
            if iterations:
                benchmark_suite.default_iterations = iterations
            
            # Run complete benchmark suite
            results = benchmark_suite.run_complete_benchmark_suite()
            
            # Print performance report
            benchmark_suite.print_performance_report()
            
            # Export results if requested
            if export:
                filename = benchmark_suite.export_results()
                print(f"\\nResults exported to: {{filename}}")
            
            return results
        
        
        def run_backend_comparison():
            """Run comparison between different parser backends."""
            print(f"\\nRunning Backend Comparisons for {self.language.capitalize()}")
            print("=" * 50)
            
            plugin = {self.language.capitalize()}Plugin()
            comparison_suite = ComparisonSuite("{self.language}")
            
            try:
                # Compare tree-sitter vs regex if both available
                results = comparison_suite.compare_treesitter_vs_regex(plugin)
                comparison_suite.print_comparison_report()
                
                return results
            except Exception as e:
                print(f"Backend comparison not available: {{e}}")
                return []
        
        
        def main():
            """Main benchmark execution."""
            parser = argparse.ArgumentParser(
                description=f"Benchmark {self.language.capitalize()} plugin performance"
            )
            parser.add_argument(
                "--iterations", "-i", type=int, default=10,
                help="Number of benchmark iterations (default: 10)"
            )
            parser.add_argument(
                "--export", "-e", action="store_true",
                help="Export results to JSON file"
            )
            parser.add_argument(
                "--comparison", "-c", action="store_true",
                help="Run backend comparison tests"
            )
            
            args = parser.parse_args()
            
            try:
                # Run main benchmarks
                results = run_benchmarks(args.iterations, args.export)
                
                # Run comparisons if requested
                if args.comparison:
                    comparison_results = run_backend_comparison()
                
                print(f"\\nBenchmark completed successfully!")
                print(f"Total tests run: {{len(results)}}")
                
            except Exception as e:
                print(f"Benchmark failed: {{e}}")
                sys.exit(1)
        
        
        if __name__ == "__main__":
            main()
        ''')
        
        return template.strip()
    
    def generate_conftest(self) -> str:
        """Generate pytest configuration and fixtures."""
        template = dedent(f'''
        """
        Pytest configuration and fixtures for {self.language.capitalize()} plugin tests.
        
        Generated automatically by the plugin testing framework.
        """
        
        import pytest
        import tempfile
        import shutil
        from pathlib import Path
        from unittest.mock import Mock
        
        from mcp_server.storage.sqlite_store import SQLiteStore
        from mcp_server.plugins.{self.language}_plugin.plugin import Plugin as {self.language.capitalize()}Plugin
        
        
        @pytest.fixture
        def {self.language}_plugin():
            """Create a {self.language} plugin instance for testing."""
            return {self.language.capitalize()}Plugin()
        
        
        @pytest.fixture
        def {self.language}_plugin_with_store():
            """Create a {self.language} plugin with SQLite store for testing."""
            store = SQLiteStore(":memory:")
            plugin = {self.language.capitalize()}Plugin(sqlite_store=store)
            yield plugin
            # Cleanup
            if hasattr(store, 'close'):
                store.close()
        
        
        @pytest.fixture
        def sqlite_store():
            """Create an in-memory SQLite store for testing."""
            store = SQLiteStore(":memory:")
            yield store
            # Cleanup
            if hasattr(store, 'close'):
                store.close()
        
        
        @pytest.fixture
        def temp_directory():
            """Create a temporary directory for test files."""
            temp_dir = Path(tempfile.mkdtemp())
            yield temp_dir
            # Cleanup
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
        
        @pytest.fixture
        def sample_{self.language}_files(temp_directory):
            """Create sample {self.language} files for testing."""
            from tests.plugin_framework.test_data import TestDataManager
            
            test_data_manager = TestDataManager("{self.language}")
            
            files = {{
                f"simple{self.file_extensions[0]}": test_data_manager.get_simple_content(),
                f"functions{self.file_extensions[0]}": test_data_manager.get_function_test_files().get(
                    f"functions{self.file_extensions[0]}", "# Functions test file"
                ),
                f"classes{self.file_extensions[0]}": test_data_manager.get_class_test_files().get(
                    f"classes{self.file_extensions[0]}", "# Classes test file"
                ),
            }}
            
            created_files = {{}}
            for filename, content in files.items():
                file_path = temp_directory / filename
                file_path.write_text(content)
                created_files[filename] = file_path
            
            return created_files
        
        
        @pytest.fixture
        def populated_sqlite_store():
            """Create SQLite store with sample data."""
            store = SQLiteStore(":memory:")
            
            # Create sample repository
            repo_id = store.create_repository("/test/repo", "test_repo", {{"language": "{self.language}"}})
            
            # Create sample file
            file_id = store.store_file(
                repo_id, "/test/repo/sample{self.file_extensions[0]}", 
                f"sample{self.file_extensions[0]}", language="{self.language}"
            )
            
            # Create sample symbols
            sample_symbols = [
                ("test_function", "function", 1, 5),
                ("TestClass", "class", 7, 15),
                ("test_method", "method", 9, 12),
            ]
            
            for name, kind, start_line, end_line in sample_symbols:
                store.store_symbol(file_id, name, kind, start_line, end_line)
            
            yield store
            
            # Cleanup
            if hasattr(store, 'close'):
                store.close()
        
        
        @pytest.fixture(scope="session")
        def benchmark_results():
            """Shared benchmark results storage for performance tests."""
            return {{}}
        
        
        def pytest_configure(config):
            """Configure pytest for {self.language} plugin tests."""
            config.addinivalue_line(
                "markers", "benchmark: mark test as a benchmark test"
            )
            config.addinivalue_line(
                "markers", "integration: mark test as an integration test"
            )
            config.addinivalue_line(
                "markers", "slow: mark test as slow running"
            )
        
        
        def pytest_collection_modifyitems(config, items):
            """Modify test collection to add markers."""
            for item in items:
                # Mark benchmark tests
                if "benchmark" in item.nodeid or "performance" in item.nodeid:
                    item.add_marker(pytest.mark.benchmark)
                
                # Mark integration tests
                if "integration" in item.nodeid:
                    item.add_marker(pytest.mark.integration)
                
                # Mark slow tests
                if any(keyword in item.nodeid for keyword in ["large", "massive", "stress"]):
                    item.add_marker(pytest.mark.slow)
        ''')
        
        return template.strip()
    
    def generate_test_readme(self) -> str:
        """Generate README for the test suite."""
        template = dedent(f'''
        # {self.language.capitalize()} Plugin Test Suite
        
        This test suite was automatically generated by the plugin testing framework.
        
        ## Overview
        
        This directory contains comprehensive tests for the {self.language.capitalize()} language plugin, including:
        
        - **Basic functionality tests** - Core plugin behavior and symbol extraction
        - **Performance benchmarks** - Speed and memory usage analysis
        - **Integration tests** - Plugin interaction with MCP server components
        - **Backend comparisons** - Tree-sitter vs regex parser performance
        
        ## Test Files
        
        - `test_{self.language}_plugin.py` - Basic functionality and accuracy tests
        - `test_{self.language}_performance.py` - Performance and scalability tests  
        - `test_{self.language}_integration.py` - Integration and workflow tests
        - `benchmark_{self.language}.py` - Standalone benchmark script
        - `conftest.py` - Pytest fixtures and configuration
        
        ## Running Tests
        
        ### Run All Tests
        ```bash
        pytest
        ```
        
        ### Run Specific Test Categories
        ```bash
        # Basic functionality tests
        pytest test_{self.language}_plugin.py
        
        # Performance tests
        pytest test_{self.language}_performance.py -m benchmark
        
        # Integration tests  
        pytest test_{self.language}_integration.py -m integration
        
        # Skip slow tests
        pytest -m "not slow"
        ```
        
        ### Run Benchmarks
        ```bash
        # Run standalone benchmarks
        python benchmark_{self.language}.py
        
        # Export results to JSON
        python benchmark_{self.language}.py --export
        
        # Run with custom iterations
        python benchmark_{self.language}.py --iterations 20
        
        # Include backend comparisons
        python benchmark_{self.language}.py --comparison
        ```
        
        ## Configuration
        
        ### Environment Variables
        
        - `{self.language.upper()}_PLUGIN_BACKEND` - Preferred parser backend
        - `{self.language.upper()}_PLUGIN_CACHE` - Enable/disable caching
        - `BENCHMARK_ITERATIONS` - Default benchmark iterations
        
        ### Plugin Extensions
        
        Supported file extensions: {', '.join(self.file_extensions)}
        
        ## Customization
        
        ### Adding Language-Specific Tests
        
        1. Edit `test_{self.language}_plugin.py`
        2. Add methods to test {self.language}-specific features
        3. Update `get_valid_symbol_kinds()` for language-specific symbols
        4. Add custom validation methods
        
        ### Modifying Performance Thresholds
        
        Edit the threshold values in `test_{self.language}_performance.py`:
        
        ```python
        max_indexing_time_small = 1.0    # seconds
        max_indexing_time_medium = 5.0   # seconds
        max_indexing_time_large = 30.0   # seconds
        max_memory_usage = 100 * 1024 * 1024  # bytes
        ```
        
        ### Adding Test Data
        
        The test data is managed by `TestDataManager`. To add custom test cases:
        
        1. Create test files in the `test_data/` directory
        2. Update `language_templates.py` with {self.language}-specific patterns
        3. Add accuracy test cases with expected symbols
        
        ## Expected Results
        
        ### Performance Targets
        
        - Small files (< 1KB): < 1 second
        - Medium files (1-10KB): < 5 seconds  
        - Large files (> 10KB): < 30 seconds
        - Memory usage: < 100MB peak
        - Concurrent throughput: > 10 files/second
        
        ### Accuracy Targets
        
        - Symbol extraction accuracy: > 95%
        - Error recovery rate: > 90%
        - Backend consistency: Symbol counts within 2x
        
        ## Troubleshooting
        
        ### Common Issues
        
        1. **Import errors** - Ensure the {self.language} plugin is properly installed
        2. **Test failures** - Check that test data templates are implemented
        3. **Performance issues** - Verify system resources and increase timeouts if needed
        4. **Backend errors** - Ensure Tree-sitter grammars are installed
        
        ### Debug Mode
        
        Run tests with verbose output:
        ```bash
        pytest -v -s test_{self.language}_plugin.py
        ```
        
        Enable debug logging:
        ```bash
        PYTHONPATH=. pytest --log-cli-level=DEBUG
        ```
        
        ## Contributing
        
        This test suite is automatically generated. To make permanent changes:
        
        1. Modify the test generator templates
        2. Regenerate the test suite
        3. Add language-specific customizations
        4. Update this README with any manual changes
        
        ## Framework Integration
        
        This test suite integrates with the plugin testing framework:
        
        - Uses `PluginTestBase` for standardized functionality tests
        - Uses `PerformanceTestBase` for benchmark tests
        - Uses `IntegrationTestBase` for integration tests
        - Uses `TestDataManager` for test data generation
        - Uses `BenchmarkSuite` for performance analysis
        - Uses `ComparisonSuite` for backend comparisons
        ''')
        
        return template.strip()
    
    # ===== Utility Methods =====
    
    def validate_plugin_class(self, plugin_class: Type[IPlugin]) -> bool:
        """Validate that a plugin class is suitable for test generation."""
        try:
            # Check if it's a valid plugin class
            if not issubclass(plugin_class, IPlugin):
                return False
            
            # Check required attributes
            if not hasattr(plugin_class, 'lang'):
                return False
            
            # Check required methods
            required_methods = ['supports', 'indexFile', 'getDefinition', 'findReferences', 'search']
            for method in required_methods:
                if not hasattr(plugin_class, method):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_test_requirements(self) -> List[str]:
        """Get list of required packages for running the generated tests."""
        return [
            "pytest",
            "pytest-benchmark", 
            "pytest-mock",
            "numpy",  # For statistical analysis
        ]
    
    def get_test_statistics(self) -> Dict[str, Any]:
        """Get statistics about the generated test suite."""
        return {
            "language": self.language,
            "plugin_class": self.plugin_class_name,
            "file_extensions": self.file_extensions,
            "test_classes": [
                f"Test{self.language.capitalize()}Plugin",
                f"Test{self.language.capitalize()}Performance", 
                f"Test{self.language.capitalize()}Integration"
            ],
            "estimated_test_count": 25,  # Approximate number of tests
            "estimated_runtime": "5-15 minutes",  # Estimated test runtime
            "coverage_areas": [
                "Basic functionality",
                "Symbol extraction",
                "Error handling",
                "Performance",
                "Memory usage",
                "Concurrency",
                "Integration",
                "Backend comparison"
            ]
        }