"""
Basic validation test for the plugin testing framework.

This test ensures the framework components can be imported and initialized properly.
"""

import pytest
from pathlib import Path


def test_framework_imports():
    """Test that all framework components can be imported."""
    # Test main framework imports
    from tests.plugin_framework import (
        PluginTestBase,
        PerformanceTestBase,
        IntegrationTestBase,
        TestDataManager,
        BenchmarkSuite,
        ComparisonSuite,
        TestGenerator
    )
    
    # Verify classes exist
    assert PluginTestBase is not None
    assert PerformanceTestBase is not None  
    assert IntegrationTestBase is not None
    assert TestDataManager is not None
    assert BenchmarkSuite is not None
    assert ComparisonSuite is not None
    assert TestGenerator is not None


def test_test_data_manager():
    """Test TestDataManager functionality."""
    from tests.plugin_framework import TestDataManager
    
    # Create manager for Python
    manager = TestDataManager("python")
    
    # Test basic content generation
    simple_content = manager.get_simple_content()
    assert isinstance(simple_content, str)
    assert len(simple_content) > 0
    
    # Test file generation
    small_file = manager.generate_small_file(5)
    assert isinstance(small_file, str)
    assert len(small_file) > 0
    
    # Test statistics
    stats = manager.get_statistics()
    assert isinstance(stats, dict)
    assert stats["language"] == "python"


def test_test_generator():
    """Test TestGenerator functionality."""
    from tests.plugin_framework import TestGenerator
    
    # Create generator
    generator = TestGenerator("python", "PythonPlugin", [".py"])
    
    # Test basic test generation
    basic_tests = generator.generate_basic_functionality_tests()
    assert isinstance(basic_tests, str)
    assert "TestPythonPlugin" in basic_tests
    assert "python" in basic_tests
    
    # Test statistics
    stats = generator.get_test_statistics()
    assert isinstance(stats, dict)
    assert stats["language"] == "python"


def test_benchmark_suite_initialization():
    """Test BenchmarkSuite can be initialized."""
    from tests.plugin_framework import BenchmarkSuite
    from unittest.mock import Mock
    from mcp_server.plugin_base import IPlugin
    
    # Create mock plugin
    mock_plugin = Mock(spec=IPlugin)
    mock_plugin.lang = "python"
    mock_plugin.__class__.__name__ = "MockPlugin"
    
    # Create benchmark suite
    benchmark_suite = BenchmarkSuite(mock_plugin, "python")
    
    assert benchmark_suite.plugin == mock_plugin
    assert benchmark_suite.language == "python"
    assert benchmark_suite.plugin_name == "MockPlugin"


def test_comparison_suite_initialization():
    """Test ComparisonSuite can be initialized."""
    from tests.plugin_framework import ComparisonSuite
    
    # Create comparison suite
    comparison_suite = ComparisonSuite("python")
    
    assert comparison_suite.language == "python"
    assert hasattr(comparison_suite, 'results')


def test_language_templates():
    """Test language template system."""
    from tests.plugin_framework.test_data.language_templates import LanguageTemplates
    
    # Test Python templates
    templates = LanguageTemplates("python")
    
    assert templates.get_file_extension() == ".py"
    
    simple_template = templates.get_simple_template()
    assert isinstance(simple_template, str)
    assert len(simple_template) > 0
    
    generated_file = templates.generate_file_with_symbols(3, "small")
    assert isinstance(generated_file, str)
    assert len(generated_file) > 0


def test_framework_integration():
    """Test that framework components work together."""
    from tests.plugin_framework import TestDataManager, TestGenerator
    
    # Create test data manager
    test_data = TestDataManager("python")
    
    # Create test generator
    generator = TestGenerator("python", "PythonPlugin", [".py"])
    
    # Verify they use compatible data
    simple_content = test_data.get_simple_content()
    basic_tests = generator.generate_basic_functionality_tests()
    
    assert isinstance(simple_content, str)
    assert isinstance(basic_tests, str)
    assert "python" in basic_tests.lower()


if __name__ == "__main__":
    # Run basic validation
    print("Testing plugin framework imports...")
    test_framework_imports()
    print("✓ Framework imports successful")
    
    print("Testing TestDataManager...")
    test_test_data_manager()
    print("✓ TestDataManager working")
    
    print("Testing TestGenerator...")
    test_test_generator()
    print("✓ TestGenerator working")
    
    print("Testing BenchmarkSuite...")
    test_benchmark_suite_initialization()
    print("✓ BenchmarkSuite working")
    
    print("Testing ComparisonSuite...")
    test_comparison_suite_initialization()
    print("✓ ComparisonSuite working")
    
    print("Testing LanguageTemplates...")
    test_language_templates()
    print("✓ LanguageTemplates working")
    
    print("Testing framework integration...")
    test_framework_integration()
    print("✓ Framework integration working")
    
    print("\n🎉 All plugin framework tests passed!")
    print("The comprehensive testing framework is ready for use.")