"""
Comprehensive Plugin Testing Framework

This module provides a complete testing framework for language plugins in the
Code Index MCP server. It includes:

1. Base test classes for language plugins
2. Test data management for multiple languages
3. Performance benchmarking utilities
4. Symbol extraction accuracy testing
5. Tree-sitter vs regex comparison testing
6. Integration testing with the main MCP server
7. Automated test generation for new languages

Usage:
    from tests.plugin_framework import PluginTestBase, TestDataManager, BenchmarkSuite

    class TestMyPlugin(PluginTestBase):
        plugin_class = MyPlugin
        language = "mylang"
        file_extensions = [".mylang"]
"""

from .base.plugin_test_base import PluginTestBase
from .base.performance_test_base import PerformanceTestBase
from .base.integration_test_base import IntegrationTestBase
from .test_data.test_data_manager import TestDataManager
from .benchmarks.benchmark_suite import BenchmarkSuite
from .benchmarks.comparison_suite import ComparisonSuite
from .generators.test_generator import TestGenerator

__all__ = [
    "PluginTestBase",
    "PerformanceTestBase", 
    "IntegrationTestBase",
    "TestDataManager",
    "BenchmarkSuite",
    "ComparisonSuite",
    "TestGenerator"
]

__version__ = "1.0.0"