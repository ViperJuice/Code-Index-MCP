# Language Plugin Testing Framework

A comprehensive testing framework for language plugins in the Code Index MCP server. This framework provides standardized testing patterns, performance benchmarking, and automated test generation for language plugins.

## Overview

The plugin testing framework consists of several key components:

### Base Test Classes
- **`PluginTestBase`** - Core functionality testing (symbol extraction, file support, error handling)
- **`PerformanceTestBase`** - Performance and scalability testing  
- **`IntegrationTestBase`** - Integration testing with MCP server components

### Testing Utilities
- **`TestDataManager`** - Language-specific test data generation and management
- **`BenchmarkSuite`** - Comprehensive performance benchmarking
- **`ComparisonSuite`** - Parser backend and plugin comparison testing
- **`TestGenerator`** - Automated test suite generation for new languages

### Test Data Management
- **`LanguageTemplates`** - Language-specific code templates and patterns
- Automated generation of test files with varying complexity
- Accuracy testing with known expected symbols
- Error case generation for robustness testing

## Quick Start

### Basic Plugin Testing

```python
from tests.plugin_framework import PluginTestBase
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin

class TestMyPlugin(PluginTestBase):
    plugin_class = PythonPlugin
    language = "python"
    file_extensions = [".py"]
    
    # Framework provides all standard tests automatically
    # Add custom tests as needed
```

### Performance Testing

```python
from tests.plugin_framework import PerformanceTestBase

class TestMyPluginPerformance(PerformanceTestBase):
    plugin_class = PythonPlugin
    language = "python"
    file_extensions = [".py"]
    
    # Customize performance thresholds
    max_indexing_time_small = 0.5
    max_indexing_time_medium = 2.0
    max_memory_usage = 50 * 1024 * 1024  # 50MB
```

### Standalone Benchmarking

```python
from tests.plugin_framework import BenchmarkSuite

plugin = PythonPlugin()
benchmark_suite = BenchmarkSuite(plugin, "python")

# Run complete benchmark suite
results = benchmark_suite.run_complete_benchmark_suite()

# Print performance report
benchmark_suite.print_performance_report()

# Export results
benchmark_suite.export_results("python_benchmarks.json")
```

### Backend Comparison

```python
from tests.plugin_framework import ComparisonSuite

comparison_suite = ComparisonSuite("python")

# Compare tree-sitter vs regex parsing
results = comparison_suite.compare_treesitter_vs_regex(plugin)

# Print comparison report
comparison_suite.print_comparison_report()
```

## Automated Test Generation

Generate complete test suites for new language plugins:

```python
from tests.plugin_framework import TestGenerator

generator = TestGenerator(
    language="rust",
    plugin_class_name="RustPlugin", 
    file_extensions=[".rs"]
)

# Generate complete test suite
generated_files = generator.generate_complete_test_suite(
    Path("tests/test_rust_plugin/")
)

print(f"Generated {len(generated_files)} test files")
```

This creates:
- `test_rust_plugin.py` - Basic functionality tests
- `test_rust_performance.py` - Performance tests
- `test_rust_integration.py` - Integration tests
- `benchmark_rust.py` - Standalone benchmark script
- `conftest.py` - Pytest fixtures
- `README.md` - Documentation

## Framework Components

### 1. Base Test Classes

#### PluginTestBase

Provides comprehensive testing for:
- File support detection
- Symbol extraction (functions, classes, variables)
- Error handling and edge cases
- Unicode and encoding support
- Parser backend switching
- Search and definition lookup

Standard test methods:
- `test_plugin_initialization()`
- `test_file_support_detection()`
- `test_symbol_extraction()`
- `test_error_handling()`
- `test_unicode_handling()`
- `test_parser_backend_switching()`

#### PerformanceTestBase

Benchmarks for:
- File size scaling (small/medium/large files)
- Memory usage analysis
- Concurrent operation performance
- Symbol count scaling
- Cross-backend performance comparison

Standard benchmark methods:
- `test_small_file_performance()`
- `test_memory_usage_scaling()`
- `test_concurrent_indexing_performance()`
- `test_symbol_count_scaling()`

#### IntegrationTestBase

Integration testing for:
- SQLite persistence integration
- Plugin manager integration
- Dispatcher integration
- File watching integration
- Cross-plugin scenarios

Standard integration methods:
- `test_sqlite_integration()`
- `test_dispatcher_integration()`
- `test_concurrent_access_safety()`
- `test_error_recovery()`

### 2. Test Data Management

#### TestDataManager

Manages test data for language plugins:

```python
test_data = TestDataManager("python")

# Get basic test files
basic_files = test_data.get_basic_test_files()

# Generate files with specific symbol counts
medium_file = test_data.generate_medium_file(50)  # ~50 symbols

# Get accuracy test cases with expected symbols
accuracy_cases = test_data.get_accuracy_test_files()

# Get complex language patterns
complex_patterns = test_data.get_complex_patterns()
```

#### LanguageTemplates

Language-specific code generation:

```python
templates = LanguageTemplates("python")

# Get simple code template
simple_code = templates.get_simple_template()

# Generate file with specific symbol count
generated_code = templates.generate_file_with_symbols(100, "medium")

# Get language-specific patterns
functions_code = templates.get_functions_template()
classes_code = templates.get_classes_template()
```

### 3. Benchmarking System

#### BenchmarkSuite

Comprehensive performance testing:

```python
benchmark_suite = BenchmarkSuite(plugin, "python")

# Individual benchmarks
small_file_result = benchmark_suite.benchmark_small_file_indexing()
memory_result = benchmark_suite.benchmark_memory_usage_scaling()
concurrent_result = benchmark_suite.benchmark_concurrent_indexing()

# Complete benchmark suite
all_results = benchmark_suite.run_complete_benchmark_suite()

# Analysis and reporting
summary = benchmark_suite.get_performance_summary()
benchmark_suite.export_results("benchmarks.json")
```

Available benchmarks:
- Small/medium/large file indexing
- Symbol extraction accuracy
- Memory usage scaling
- Concurrent indexing performance
- Search performance
- Error handling performance
- Cross-file scaling

#### ComparisonSuite

Backend and plugin comparison:

```python
comparison_suite = ComparisonSuite("python")

# Compare parser backends
backend_results = comparison_suite.compare_treesitter_vs_regex(plugin)

# Compare different plugins
plugin_results = comparison_suite.compare_plugins(
    plugin_a, plugin_b, "PluginA", "PluginB"
)

# Specialized comparisons
unicode_results = comparison_suite.compare_unicode_handling(
    plugin, "tree-sitter", "regex"
)
```

### 4. Test Generation

#### TestGenerator

Automated test suite generation:

```python
generator = TestGenerator("go", "GoPlugin", [".go"])

# Generate specific test types
basic_tests = generator.generate_basic_functionality_tests()
performance_tests = generator.generate_performance_tests()
integration_tests = generator.generate_integration_tests()

# Generate complete suite
all_files = generator.generate_complete_test_suite(output_dir)
```

Generated test features:
- Language-specific test patterns
- Customizable performance thresholds
- Framework integration
- Pytest configuration
- Standalone benchmark scripts
- Comprehensive documentation

## Configuration

### Performance Thresholds

Customize performance expectations:

```python
class TestMyPluginPerformance(PerformanceTestBase):
    # Timing thresholds
    max_indexing_time_small = 0.5   # seconds
    max_indexing_time_medium = 2.0  # seconds
    max_indexing_time_large = 10.0  # seconds
    
    # Memory thresholds
    max_memory_usage = 50 * 1024 * 1024  # 50MB
    
    # Throughput thresholds
    min_throughput_files_per_second = 20.0
```

### Test Data Customization

Add language-specific test data:

```python
# Extend LanguageTemplates for your language
class MyLanguageTemplate(LanguageTemplate):
    def get_file_extension(self):
        return ".mylang"
    
    def get_simple_template(self):
        return "// Simple MyLang code\nfunction hello() { return 'world'; }"
    
    def generate_file_with_symbols(self, count, complexity):
        # Generate MyLang code with specified symbols
        pass
```

### Benchmark Configuration

Customize benchmark parameters:

```python
benchmark_suite = BenchmarkSuite(plugin, "python")

# Adjust iteration counts
benchmark_suite.default_iterations = 20
benchmark_suite.warmup_iterations = 5

# Run with custom settings
result = benchmark_suite.run_benchmark(
    "custom_test", test_operation, iterations=50
)
```

## Running Tests

### Basic Test Execution

```bash
# Run all plugin framework tests
pytest tests/plugin_framework/

# Run specific test classes
pytest tests/plugin_framework/examples/test_python_plugin_example.py

# Run with markers
pytest -m benchmark          # Only benchmark tests
pytest -m integration        # Only integration tests
pytest -m "not slow"         # Skip slow tests
```

### Benchmark Execution

```bash
# Run standalone benchmarks
python tests/plugin_framework/examples/test_python_plugin_example.py

# Run generated benchmark script
python tests/test_rust_plugin/benchmark_rust.py --export --iterations 20
```

### Performance Analysis

```bash
# Run with performance profiling
pytest --benchmark-only tests/plugin_framework/

# Generate detailed reports
pytest --benchmark-json=benchmark_results.json
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Plugin Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-benchmark
      
      - name: Run plugin tests
        run: |
          pytest tests/plugin_framework/ -v
      
      - name: Run benchmarks
        run: |
          pytest tests/plugin_framework/ -m benchmark --benchmark-json=benchmarks.json
      
      - name: Upload benchmark results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: benchmarks.json
```

## Extending the Framework

### Adding New Test Types

```python
class CustomTestBase(PluginTestBase):
    """Custom test base with additional functionality."""
    
    def test_custom_feature(self):
        """Test custom plugin feature."""
        # Custom test implementation
        pass
    
    def validate_custom_symbols(self, symbols):
        """Custom symbol validation."""
        # Custom validation logic
        pass
```

### Adding Language Support

1. **Create language template:**
```python
class NewLanguageTemplate(LanguageTemplate):
    def get_file_extension(self):
        return ".newlang"
    
    def get_simple_template(self):
        return "// NewLang simple template"
    
    # Implement required methods
```

2. **Register template:**
```python
# In LanguageTemplates.__init__
elif self.language == "newlang":
    return NewLanguageTemplate()
```

3. **Generate test suite:**
```python
generator = TestGenerator("newlang", "NewLangPlugin", [".newlang"])
generator.generate_complete_test_suite(Path("tests/test_newlang/"))
```

### Custom Benchmarks

```python
class CustomBenchmarkSuite(BenchmarkSuite):
    """Custom benchmark suite with additional tests."""
    
    def benchmark_custom_feature(self):
        """Benchmark custom plugin feature."""
        def custom_test():
            # Custom benchmark operation
            return self.plugin.custom_method()
        
        return self.run_benchmark(
            "custom_feature", custom_test, iterations=10
        )
```

## Best Practices

### Test Organization

1. **Use framework base classes** for standardized testing
2. **Customize thresholds** based on language characteristics
3. **Add language-specific tests** for unique features
4. **Use test data manager** for consistent test data
5. **Export benchmark results** for performance tracking

### Performance Testing

1. **Set realistic thresholds** based on language complexity
2. **Test multiple file sizes** to understand scaling
3. **Include memory analysis** to detect leaks
4. **Test concurrent scenarios** for thread safety
5. **Compare backends** when multiple parsers available

### Test Data Quality

1. **Use real-world patterns** in test data
2. **Include edge cases** and error scenarios
3. **Test Unicode support** for international code
4. **Validate symbol accuracy** with known expected results
5. **Generate varying complexity** for comprehensive testing

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Ensure framework is in Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/mcp-server"
```

**Test Failures:**
- Check that plugin class is properly defined
- Verify file extensions are correct
- Ensure test data templates are implemented

**Performance Issues:**
- Increase timeout thresholds for slower systems
- Reduce iteration counts for faster testing
- Check system resources during benchmarks

**Memory Issues:**
- Use smaller test files for memory-constrained environments
- Enable garbage collection between test iterations
- Monitor memory usage during benchmarks

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run tests with debug output
pytest -v -s --log-cli-level=DEBUG
```

### Custom Validation

Add custom validation for specific requirements:
```python
def validate_plugin_output(self, result):
    """Custom validation for plugin output."""
    assert isinstance(result, dict)
    assert "language" in result
    assert "symbols" in result
    
    # Add custom checks
    for symbol in result["symbols"]:
        assert self.is_valid_symbol_name(symbol.get("name"))
        assert self.is_valid_symbol_kind(symbol.get("kind"))
```

## Contributing

To contribute to the plugin testing framework:

1. **Add new test patterns** to base classes
2. **Extend language templates** for new languages
3. **Improve benchmark accuracy** and coverage
4. **Add new comparison methods** for backend analysis
5. **Enhance test generation** capabilities

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd mcp-server

# Install development dependencies
pip install -e .
pip install pytest pytest-benchmark pytest-mock

# Run framework tests
pytest tests/plugin_framework/examples/

# Generate test suite for testing
python -c "
from tests.plugin_framework import TestGenerator
gen = TestGenerator('python', 'PythonPlugin', ['.py'])
gen.generate_complete_test_suite(Path('tests/generated_example/'))
"
```

The plugin testing framework provides a comprehensive foundation for testing language plugins with standardized patterns, performance analysis, and automated generation capabilities.