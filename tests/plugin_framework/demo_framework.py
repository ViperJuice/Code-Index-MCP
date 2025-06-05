#!/usr/bin/env python3
"""
Demo script showcasing the Plugin Testing Framework capabilities.

This script demonstrates all major features of the framework including:
- Test generation for new languages
- Performance benchmarking
- Backend comparison
- Integration testing
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.plugin_framework import (
    TestGenerator, 
    BenchmarkSuite, 
    ComparisonSuite,
    TestDataManager
)

def demo_test_generation():
    """Demonstrate automated test generation."""
    print("=" * 60)
    print("DEMO: Automated Test Generation")
    print("=" * 60)
    
    # Create temporary directory for generated tests
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "generated_tests"
        
        # Generate test suite for a hypothetical Rust plugin
        print("Generating test suite for Rust language plugin...")
        generator = TestGenerator(
            language="rust",
            plugin_class_name="RustPlugin",
            file_extensions=[".rs"]
        )
        
        generated_files = generator.generate_complete_test_suite(output_dir)
        
        print(f"Generated {len(generated_files)} files:")
        for file_type, file_path in generated_files.items():
            file_size = Path(file_path).stat().st_size
            print(f"  {file_type}: {Path(file_path).name} ({file_size:,} bytes)")
        
        # Show test statistics
        stats = generator.get_test_statistics()
        print(f"\nTest Suite Statistics:")
        print(f"  Language: {stats['language']}")
        print(f"  Estimated test count: {stats['estimated_test_count']}")
        print(f"  Estimated runtime: {stats['estimated_runtime']}")
        print(f"  Coverage areas: {len(stats['coverage_areas'])}")
        
        # Show sample of generated test file
        basic_test_file = generated_files["basic_tests"]
        with open(basic_test_file, 'r') as f:
            sample_lines = f.readlines()[:20]
        
        print(f"\nSample from generated basic test file:")
        print("```python")
        for line in sample_lines:
            print(line.rstrip())
        print("...")
        print("```")

def demo_test_data_management():
    """Demonstrate test data management capabilities."""
    print("\n" + "=" * 60)
    print("DEMO: Test Data Management")
    print("=" * 60)
    
    # Create test data manager for Python
    print("Creating test data for Python language...")
    test_data = TestDataManager("python")
    
    # Show available test data types
    print(f"\nAvailable test data:")
    basic_files = test_data.get_basic_test_files()
    print(f"  Basic test files: {len(basic_files)}")
    
    function_files = test_data.get_function_test_files()
    print(f"  Function test files: {len(function_files)}")
    
    class_files = test_data.get_class_test_files()
    print(f"  Class test files: {len(class_files)}")
    
    accuracy_cases = test_data.get_accuracy_test_files()
    print(f"  Accuracy test cases: {len(accuracy_cases)}")
    
    # Show sample generated content
    print(f"\nSample generated small file (5 symbols):")
    small_file = test_data.generate_small_file(5)
    print("```python")
    print(small_file[:300] + "..." if len(small_file) > 300 else small_file)
    print("```")
    
    # Show accuracy test case
    if accuracy_cases:
        print(f"\nSample accuracy test case:")
        case = accuracy_cases[0]
        print(f"  File: {case.file}")
        print(f"  Expected symbols: {len(case.expected_symbols)}")
        print(f"  Target symbols: {case.target_symbols}")
        print(f"  Description: {case.description}")
    
    # Show test data statistics
    stats = test_data.get_statistics()
    print(f"\nTest Data Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

def demo_benchmarking():
    """Demonstrate benchmarking capabilities."""
    print("\n" + "=" * 60)
    print("DEMO: Performance Benchmarking")
    print("=" * 60)
    
    try:
        # Import Python plugin for demonstration
        from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
        
        print("Creating Python plugin and benchmark suite...")
        plugin = PythonPlugin()
        benchmark_suite = BenchmarkSuite(plugin, "python")
        
        # Reduce iterations for demo
        benchmark_suite.default_iterations = 3
        
        print("\nRunning sample benchmarks...")
        
        # Run individual benchmarks
        print("  Running small file indexing benchmark...")
        small_file_result = benchmark_suite.benchmark_small_file_indexing()
        print(f"    Average time: {small_file_result.summary['duration_mean']:.4f}s")
        print(f"    Success rate: {small_file_result.success_rate:.1%}")
        
        print("  Running symbol extraction accuracy benchmark...")
        accuracy_result = benchmark_suite.benchmark_symbol_extraction_accuracy()
        print(f"    Success rate: {accuracy_result.success_rate:.1%}")
        
        print("  Running memory usage benchmark...")
        memory_result = benchmark_suite.benchmark_memory_usage_scaling()
        print(f"    Peak memory: {memory_result.memory_peak_mb:.1f}MB")
        
        # Show performance summary
        summary = benchmark_suite.get_performance_summary()
        print(f"\nBenchmark Summary:")
        print(f"  Plugin: {summary['plugin_name']}")
        print(f"  Language: {summary['language']}")
        print(f"  Total benchmarks: {summary['total_benchmarks']}")
        print(f"  Overall success rate: {summary['overall_success_rate']:.1%}")
        
        # Export results to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filename = benchmark_suite.export_results(f.name)
            print(f"  Results exported to: {filename}")
        
    except ImportError as e:
        print(f"Skipping benchmarking demo - Python plugin not available: {e}")

def demo_backend_comparison():
    """Demonstrate backend comparison capabilities."""
    print("\n" + "=" * 60)
    print("DEMO: Parser Backend Comparison")
    print("=" * 60)
    
    try:
        from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
        
        plugin = PythonPlugin()
        comparison_suite = ComparisonSuite("python")
        
        # Check available backends
        if hasattr(plugin, 'get_parser_info'):
            parser_info = plugin.get_parser_info()
            available_backends = parser_info.get("available_backends", [])
            current_backend = parser_info.get("current_backend")
            
            print(f"Parser Information:")
            print(f"  Current backend: {current_backend}")
            print(f"  Available backends: {available_backends}")
            
            if len(available_backends) >= 2:
                print(f"\nRunning backend comparison...")
                
                # Compare first two available backends
                backend_a, backend_b = available_backends[:2]
                
                def test_operation():
                    from tests.plugin_framework.test_data import TestDataManager
                    test_data = TestDataManager("python")
                    content = test_data.generate_medium_file(25)
                    return plugin.indexFile(Path("comparison_test.py"), content)
                
                result = comparison_suite.compare_backends(
                    plugin, backend_a, backend_b,
                    "demo_comparison", test_operation, iterations=3
                )
                
                print(f"Comparison Results:")
                print(f"  Test: {result.test_name}")
                print(f"  Backend A: {result.backend_a_name}")
                print(f"  Backend B: {result.backend_b_name}")
                print(f"  Winner: {result.overall_winner}")
                
                for metric in result.metrics:
                    print(f"    {metric.name}: {metric.backend_a:.4f} vs {metric.backend_b:.4f} {metric.unit}")
                    print(f"      Improvement: {metric.improvement_ratio:.2f}x ({metric.better_backend} better)")
                
            else:
                print("Backend comparison requires at least 2 available backends")
                print("Demonstrating comparison infrastructure instead...")
                
                # Show comparison suite capabilities
                summary = comparison_suite.get_comparison_summary()
                print(f"Comparison suite ready for language: {summary.get('language', 'unknown')}")
        
        else:
            print("Plugin does not support backend information")
            print("Backend comparison features not available for this plugin")
    
    except ImportError as e:
        print(f"Skipping backend comparison demo - Python plugin not available: {e}")

def demo_integration_features():
    """Demonstrate integration testing features."""
    print("\n" + "=" * 60)
    print("DEMO: Integration Testing Features")
    print("=" * 60)
    
    try:
        from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
        from mcp_server.storage.sqlite_store import SQLiteStore
        from tests.plugin_framework.base.integration_test_base import IntegrationTestBase
        
        # Create a temporary integration test
        class DemoIntegrationTest(IntegrationTestBase):
            plugin_class = PythonPlugin
            language = "python"
            file_extensions = [".py"]
        
        print("Setting up integration test scenario...")
        test_instance = DemoIntegrationTest()
        test_instance.setup_method()
        
        try:
            # Demonstrate SQLite integration
            print("  Testing SQLite integration...")
            repo_id = test_instance.create_test_repository("demo_repo")
            print(f"    Created repository ID: {repo_id}")
            
            # Create and index a test file
            result = test_instance.create_and_index_file(
                "demo_file.py", 
                "def hello(): return 'world'\nclass Demo: pass"
            )
            print(f"    Indexed file with {len(result.get('symbols', []))} symbols")
            
            # Test full integration scenario
            print("  Setting up full integration scenario...")
            scenario = test_instance.setup_full_integration_scenario()
            print(f"    Created scenario with {len(scenario['test_files'])} files")
            print(f"    Repository ID: {scenario['repo_id']}")
            print(f"    Temp directory: {scenario['temp_dir']}")
            
            # Show integration capabilities
            print(f"\nIntegration Test Capabilities:")
            print(f"  - SQLite persistence testing")
            print(f"  - Plugin manager integration")
            print(f"  - Dispatcher integration")
            print(f"  - File watching simulation")
            print(f"  - Error recovery testing")
            print(f"  - Concurrent access safety")
            print(f"  - Multi-language project testing")
            
        finally:
            test_instance.teardown_method()
            print("  Integration test cleanup completed")
    
    except ImportError as e:
        print(f"Skipping integration demo - dependencies not available: {e}")

def main():
    """Run all framework demonstrations."""
    print("Plugin Testing Framework Demonstration")
    print("This demo showcases the comprehensive testing capabilities")
    print("for language plugins in the Code Index MCP server.")
    
    # Run all demonstrations
    demo_test_generation()
    demo_test_data_management()
    demo_benchmarking()
    demo_backend_comparison()
    demo_integration_features()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("The Plugin Testing Framework provides:")
    print("✓ Automated test generation for new languages")
    print("✓ Comprehensive test data management") 
    print("✓ Performance benchmarking and analysis")
    print("✓ Parser backend comparison testing")
    print("✓ Integration testing with MCP components")
    print("✓ Standardized testing patterns and utilities")
    print("\nSee tests/plugin_framework/README.md for complete documentation.")

if __name__ == "__main__":
    main()