# Code-Index-MCP Testing Guide

This guide provides comprehensive instructions for testing the Code-Index-MCP project, covering unit tests, integration tests, plugin testing, performance testing, and test coverage.

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [Plugin Testing](#plugin-testing)
6. [Performance Testing](#performance-testing)
7. [Test Coverage](#test-coverage)
8. [Continuous Integration](#continuous-integration)
9. [Best Practices](#best-practices)

## Testing Overview

Code-Index-MCP uses a multi-layered testing approach:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Plugin Tests**: Language-specific plugin testing
- **Performance Tests**: Ensure indexing and query performance
- **End-to-End Tests**: Test complete user workflows

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_dispatcher.py
│   ├── test_gateway.py
│   ├── test_watcher.py
│   └── utils/
│       ├── test_fuzzy_indexer.py
│       ├── test_semantic_indexer.py
│       └── test_treesitter_wrapper.py
├── integration/             # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_file_sync.py
│   └── test_plugin_integration.py
├── plugins/                 # Plugin-specific tests
│   ├── test_python_plugin.py
│   ├── test_js_plugin.py
│   ├── test_dart_plugin.py
│   ├── test_c_plugin.py
│   ├── test_cpp_plugin.py
│   └── test_html_css_plugin.py
├── performance/            # Performance tests
│   ├── test_indexing_speed.py
│   ├── test_query_performance.py
│   └── test_memory_usage.py
├── fixtures/               # Test fixtures
│   ├── sample_code/
│   └── mock_data/
└── conftest.py            # Pytest configuration

```

## Test Environment Setup

### 1. Install Testing Dependencies

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or install with development extras
pip install -e ".[test]"
```

### 2. Create requirements-test.txt

```txt
# Testing frameworks
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
pytest-benchmark>=4.0.0
pytest-timeout>=2.1.0

# Test utilities
httpx>=0.24.0
fakeredis>=2.18.0
freezegun>=1.2.0
hypothesis>=6.82.0

# Code quality
black>=23.7.0
isort>=5.12.0
flake8>=6.1.0
mypy>=1.5.1
pylint>=2.17.0

# Performance testing
locust>=2.15.0
memory-profiler>=0.61.0
```

### 3. Configure pytest

Create `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=mcp_server
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    slow: Slow running tests
    plugin: Plugin-specific tests
asyncio_mode = auto
timeout = 300
```

## Unit Testing

### Basic Unit Test Example

```python
# tests/unit/test_dispatcher.py
import pytest
from unittest.mock import Mock, patch
from mcp_server.dispatcher import Dispatcher

class TestDispatcher:
    @pytest.fixture
    def dispatcher(self):
        """Create a dispatcher instance for testing."""
        return Dispatcher()
    
    @pytest.fixture
    def mock_plugin(self):
        """Create a mock plugin."""
        plugin = Mock()
        plugin.supports_language.return_value = True
        plugin.indexFile.return_value = {"symbols": [], "references": []}
        return plugin
    
    def test_register_plugin(self, dispatcher, mock_plugin):
        """Test plugin registration."""
        dispatcher.register_plugin("python", mock_plugin)
        assert "python" in dispatcher.plugins
        assert dispatcher.plugins["python"] == mock_plugin
    
    def test_dispatch_to_correct_plugin(self, dispatcher, mock_plugin):
        """Test dispatching to the correct plugin."""
        dispatcher.register_plugin("python", mock_plugin)
        
        result = dispatcher.dispatch("test.py", "def foo(): pass")
        
        mock_plugin.indexFile.assert_called_once()
        assert result == {"symbols": [], "references": []}
    
    @pytest.mark.parametrize("filename,expected_lang", [
        ("test.py", "python"),
        ("test.js", "javascript"),
        ("test.dart", "dart"),
        ("test.c", "c"),
        ("test.cpp", "cpp"),
        ("test.html", "html"),
    ])
    def test_language_detection(self, dispatcher, filename, expected_lang):
        """Test language detection from file extension."""
        detected = dispatcher.detect_language(filename)
        assert detected == expected_lang
```

### Testing Async Components

```python
# tests/unit/test_gateway.py
import pytest
from httpx import AsyncClient
from mcp_server.gateway import app

@pytest.mark.asyncio
class TestGateway:
    async def test_health_endpoint(self):
        """Test health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
    
    async def test_index_file_endpoint(self):
        """Test file indexing endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "path": "test.py",
                "content": "def hello(): pass"
            }
            response = await client.post("/index", json=payload)
            assert response.status_code == 200
            assert "symbols" in response.json()
    
    async def test_search_endpoint(self):
        """Test code search endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/search?query=hello")
            assert response.status_code == 200
            assert "results" in response.json()
```

### Testing Utilities

```python
# tests/unit/utils/test_treesitter_wrapper.py
import pytest
from pathlib import Path
from mcp_server.utils.treesitter_wrapper import TreeSitterWrapper

class TestTreeSitterWrapper:
    @pytest.fixture
    def wrapper(self):
        return TreeSitterWrapper()
    
    def test_parse_python_code(self, wrapper):
        """Test parsing Python code."""
        code = """
def hello(name):
    return f"Hello, {name}!"
"""
        tree = wrapper.parse_code(code, "python")
        assert tree is not None
        assert tree.root_node.type == "module"
    
    def test_extract_functions(self, wrapper):
        """Test extracting function definitions."""
        code = """
def func1():
    pass

def func2(arg1, arg2):
    return arg1 + arg2
"""
        functions = wrapper.extract_functions(code, "python")
        assert len(functions) == 2
        assert functions[0]["name"] == "func1"
        assert functions[1]["name"] == "func2"
        assert len(functions[1]["parameters"]) == 2
```

## Integration Testing

### API Integration Tests

```python
# tests/integration/test_api_endpoints.py
import pytest
from httpx import AsyncClient
from pathlib import Path
import tempfile
from mcp_server.gateway import app

@pytest.mark.integration
class TestAPIIntegration:
    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    async def test_full_indexing_workflow(self, client, temp_workspace):
        """Test complete file indexing workflow."""
        # Create test file
        test_file = temp_workspace / "test.py"
        test_file.write_text("""
def calculate_sum(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
""")
        
        # Index the file
        response = await client.post("/index", json={
            "path": str(test_file),
            "content": test_file.read_text()
        })
        assert response.status_code == 200
        index_data = response.json()
        
        # Search for indexed content
        response = await client.get("/search?query=calculate_sum")
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) > 0
        assert any("calculate_sum" in r["content"] for r in results)
    
    async def test_multi_file_indexing(self, client, temp_workspace):
        """Test indexing multiple files."""
        files = {
            "module1.py": "def func1(): pass",
            "module2.py": "def func2(): pass",
            "module3.py": "def func3(): pass"
        }
        
        # Index all files
        for filename, content in files.items():
            file_path = temp_workspace / filename
            file_path.write_text(content)
            
            response = await client.post("/index", json={
                "path": str(file_path),
                "content": content
            })
            assert response.status_code == 200
        
        # Verify all functions are searchable
        for func_name in ["func1", "func2", "func3"]:
            response = await client.get(f"/search?query={func_name}")
            assert response.status_code == 200
            results = response.json()["results"]
            assert len(results) > 0
```

### File System Integration

```python
# tests/integration/test_file_sync.py
import pytest
import asyncio
from pathlib import Path
import tempfile
from mcp_server.watcher import FileWatcher
from mcp_server.sync import FileSynchronizer

@pytest.mark.integration
class TestFileSync:
    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    async def watcher(self, temp_workspace):
        watcher = FileWatcher(temp_workspace)
        await watcher.start()
        yield watcher
        await watcher.stop()
    
    async def test_file_creation_detection(self, watcher, temp_workspace):
        """Test detecting new file creation."""
        events = []
        watcher.on_created = lambda path: events.append(("created", path))
        
        # Create new file
        test_file = temp_workspace / "new_file.py"
        test_file.write_text("def new_function(): pass")
        
        # Wait for event
        await asyncio.sleep(0.1)
        
        assert len(events) == 1
        assert events[0][0] == "created"
        assert events[0][1].name == "new_file.py"
    
    async def test_file_modification_detection(self, watcher, temp_workspace):
        """Test detecting file modifications."""
        test_file = temp_workspace / "test.py"
        test_file.write_text("def original(): pass")
        
        events = []
        watcher.on_modified = lambda path: events.append(("modified", path))
        
        # Modify file
        test_file.write_text("def modified(): pass")
        
        # Wait for event
        await asyncio.sleep(0.1)
        
        assert len(events) == 1
        assert events[0][0] == "modified"
```

## Plugin Testing

### Base Plugin Test Class

```python
# tests/plugins/base_plugin_test.py
import pytest
from abc import ABC, abstractmethod
from pathlib import Path

class BasePluginTest(ABC):
    """Base class for plugin tests."""
    
    @abstractmethod
    def get_plugin(self):
        """Return plugin instance to test."""
        pass
    
    @abstractmethod
    def get_sample_code(self):
        """Return sample code for the language."""
        pass
    
    def test_plugin_initialization(self):
        """Test plugin can be initialized."""
        plugin = self.get_plugin()
        assert plugin is not None
        assert hasattr(plugin, "indexFile")
        assert hasattr(plugin, "supports_language")
    
    def test_supports_correct_language(self):
        """Test plugin supports its language."""
        plugin = self.get_plugin()
        assert plugin.supports_language(self.get_language())
    
    def test_basic_indexing(self):
        """Test basic code indexing."""
        plugin = self.get_plugin()
        code = self.get_sample_code()
        
        result = plugin.indexFile("test_file", code)
        
        assert "symbols" in result
        assert "references" in result
        assert isinstance(result["symbols"], list)
        assert isinstance(result["references"], list)
```

### Python Plugin Tests

```python
# tests/plugins/test_python_plugin.py
import pytest
from mcp_server.plugins.python_plugin.plugin import Plugin
from tests.plugins.base_plugin_test import BasePluginTest

class TestPythonPlugin(BasePluginTest):
    def get_plugin(self):
        return Plugin()
    
    def get_language(self):
        return "python"
    
    def get_sample_code(self):
        return """
import os
from typing import List

def calculate_average(numbers: List[float]) -> float:
    '''Calculate the average of a list of numbers.'''
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)

class DataProcessor:
    def __init__(self, name: str):
        self.name = name
        self.data = []
    
    def add_data(self, value: float):
        self.data.append(value)
    
    def get_average(self) -> float:
        return calculate_average(self.data)
"""
    
    def test_extract_functions(self):
        """Test extracting Python functions."""
        plugin = self.get_plugin()
        result = plugin.indexFile("test.py", self.get_sample_code())
        
        functions = [s for s in result["symbols"] if s["type"] == "function"]
        assert len(functions) == 1
        assert functions[0]["name"] == "calculate_average"
        assert functions[0]["line"] == 5
    
    def test_extract_classes(self):
        """Test extracting Python classes."""
        plugin = self.get_plugin()
        result = plugin.indexFile("test.py", self.get_sample_code())
        
        classes = [s for s in result["symbols"] if s["type"] == "class"]
        assert len(classes) == 1
        assert classes[0]["name"] == "DataProcessor"
        assert classes[0]["line"] == 11
    
    def test_extract_methods(self):
        """Test extracting class methods."""
        plugin = self.get_plugin()
        result = plugin.indexFile("test.py", self.get_sample_code())
        
        methods = [s for s in result["symbols"] if s["type"] == "method"]
        assert len(methods) == 3  # __init__, add_data, get_average
        method_names = {m["name"] for m in methods}
        assert method_names == {"__init__", "add_data", "get_average"}
    
    def test_extract_imports(self):
        """Test extracting import statements."""
        plugin = self.get_plugin()
        result = plugin.indexFile("test.py", self.get_sample_code())
        
        imports = [s for s in result["symbols"] if s["type"] == "import"]
        assert len(imports) == 2
        import_names = {i["name"] for i in imports}
        assert "os" in import_names
        assert "List" in import_names
    
    def test_docstring_extraction(self):
        """Test extracting docstrings."""
        plugin = self.get_plugin()
        result = plugin.indexFile("test.py", self.get_sample_code())
        
        functions = [s for s in result["symbols"] if s["name"] == "calculate_average"]
        assert len(functions) == 1
        assert "docstring" in functions[0]
        assert "Calculate the average" in functions[0]["docstring"]
    
    def test_type_annotations(self):
        """Test extracting type annotations."""
        plugin = self.get_plugin()
        result = plugin.indexFile("test.py", self.get_sample_code())
        
        functions = [s for s in result["symbols"] if s["name"] == "calculate_average"]
        assert len(functions) == 1
        func = functions[0]
        assert "parameters" in func
        assert "return_type" in func
        assert func["return_type"] == "float"
```

### JavaScript Plugin Tests

```python
# tests/plugins/test_js_plugin.py
import pytest
from mcp_server.plugins.js_plugin.plugin import Plugin
from tests.plugins.base_plugin_test import BasePluginTest

class TestJavaScriptPlugin(BasePluginTest):
    def get_plugin(self):
        return Plugin()
    
    def get_language(self):
        return "javascript"
    
    def get_sample_code(self):
        return """
// Utility functions
const calculateSum = (a, b) => a + b;

function calculateProduct(x, y) {
    return x * y;
}

class Calculator {
    constructor(name) {
        this.name = name;
        this.history = [];
    }
    
    add(a, b) {
        const result = a + b;
        this.history.push({operation: 'add', result});
        return result;
    }
    
    async compute(operation, ...args) {
        // Async computation
        return await this[operation](...args);
    }
}

export { calculateSum, calculateProduct, Calculator };
"""
    
    def test_extract_arrow_functions(self):
        """Test extracting arrow functions."""
        plugin = self.get_plugin()
        result = plugin.indexFile("test.js", self.get_sample_code())
        
        arrow_funcs = [s for s in result["symbols"] 
                      if s["type"] == "function" and s["name"] == "calculateSum"]
        assert len(arrow_funcs) == 1
        assert arrow_funcs[0]["line"] == 2
    
    def test_extract_regular_functions(self):
        """Test extracting regular functions."""
        plugin = self.get_plugin()
        result = plugin.indexFile("test.js", self.get_sample_code())
        
        functions = [s for s in result["symbols"] 
                    if s["type"] == "function" and s["name"] == "calculateProduct"]
        assert len(functions) == 1
        assert functions[0]["line"] == 4
    
    def test_extract_classes_and_methods(self):
        """Test extracting ES6 classes and methods."""
        plugin = self.get_plugin()
        result = plugin.indexFile("test.js", self.get_sample_code())
        
        classes = [s for s in result["symbols"] if s["type"] == "class"]
        assert len(classes) == 1
        assert classes[0]["name"] == "Calculator"
        
        methods = [s for s in result["symbols"] if s["type"] == "method"]
        assert len(methods) == 3  # constructor, add, compute
        method_names = {m["name"] for m in methods}
        assert method_names == {"constructor", "add", "compute"}
    
    def test_extract_exports(self):
        """Test extracting export statements."""
        plugin = self.get_plugin()
        result = plugin.indexFile("test.js", self.get_sample_code())
        
        exports = [s for s in result["symbols"] if s["type"] == "export"]
        assert len(exports) > 0
        exported_names = {e["name"] for e in exports}
        assert "calculateSum" in exported_names
        assert "Calculator" in exported_names
```

## Performance Testing

### Indexing Performance Tests

```python
# tests/performance/test_indexing_speed.py
import pytest
import time
from pathlib import Path
from mcp_server.dispatcher import Dispatcher

@pytest.mark.performance
class TestIndexingPerformance:
    @pytest.fixture
    def dispatcher(self):
        dispatcher = Dispatcher()
        dispatcher.load_plugins()
        return dispatcher
    
    @pytest.fixture
    def large_python_file(self, tmp_path):
        """Generate a large Python file for testing."""
        content = []
        for i in range(1000):
            content.append(f"""
def function_{i}(arg1, arg2):
    '''Function {i} documentation'''
    result = arg1 + arg2 + {i}
    return result * 2

class Class_{i}:
    def __init__(self):
        self.value = {i}
    
    def method_{i}(self):
        return self.value * 2
""")
        
        file_path = tmp_path / "large_file.py"
        file_path.write_text("\n".join(content))
        return file_path
    
    def test_large_file_indexing_speed(self, dispatcher, large_python_file):
        """Test indexing speed for large files."""
        content = large_python_file.read_text()
        
        start_time = time.time()
        result = dispatcher.dispatch(str(large_python_file), content)
        end_time = time.time()
        
        indexing_time = end_time - start_time
        
        # Assert reasonable performance
        assert indexing_time < 5.0  # Should index in under 5 seconds
        assert len(result["symbols"]) == 3000  # 1000 functions + 1000 classes + 1000 methods
        
        # Log performance metrics
        print(f"Indexed {len(content)} characters in {indexing_time:.2f} seconds")
        print(f"Rate: {len(content) / indexing_time:.0f} chars/second")
    
    @pytest.mark.benchmark
    def test_indexing_benchmark(self, benchmark, dispatcher):
        """Benchmark indexing performance."""
        code = """
def example_function():
    return 42

class ExampleClass:
    def example_method(self):
        pass
"""
        
        result = benchmark(dispatcher.dispatch, "test.py", code)
        assert "symbols" in result
```

### Query Performance Tests

```python
# tests/performance/test_query_performance.py
import pytest
import asyncio
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer
from mcp_server.utils.semantic_indexer import SemanticIndexer

@pytest.mark.performance
class TestQueryPerformance:
    @pytest.fixture
    def fuzzy_indexer_with_data(self):
        """Create fuzzy indexer with test data."""
        indexer = FuzzyIndexer()
        
        # Add 10,000 symbols
        for i in range(10000):
            indexer.add_symbol(f"function_{i}", f"file_{i % 100}.py", i)
            indexer.add_symbol(f"class_{i}", f"file_{i % 100}.py", i * 2)
        
        return indexer
    
    def test_fuzzy_search_performance(self, fuzzy_indexer_with_data):
        """Test fuzzy search performance."""
        indexer = fuzzy_indexer_with_data
        
        queries = [
            "function_123",
            "class_456",
            "func",
            "cls",
            "nonexistent"
        ]
        
        total_time = 0
        for query in queries:
            start = time.time()
            results = indexer.search(query, limit=100)
            end = time.time()
            
            query_time = end - start
            total_time += query_time
            
            # Each query should be fast
            assert query_time < 0.1  # Under 100ms
            
            print(f"Query '{query}' took {query_time*1000:.2f}ms, found {len(results)} results")
        
        avg_time = total_time / len(queries)
        assert avg_time < 0.05  # Average under 50ms
    
    @pytest.mark.asyncio
    async def test_concurrent_query_performance(self, fuzzy_indexer_with_data):
        """Test performance under concurrent queries."""
        indexer = fuzzy_indexer_with_data
        
        async def perform_search(query):
            start = time.time()
            results = await asyncio.to_thread(indexer.search, query)
            end = time.time()
            return end - start, len(results)
        
        # Simulate 100 concurrent queries
        queries = [f"function_{i}" for i in range(100)]
        tasks = [perform_search(q) for q in queries]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # All queries should complete quickly
        assert total_time < 2.0  # Under 2 seconds for 100 queries
        
        # Individual queries should still be fast
        max_query_time = max(r[0] for r in results)
        assert max_query_time < 0.5  # No query takes more than 500ms
```

### Memory Usage Tests

```python
# tests/performance/test_memory_usage.py
import pytest
import psutil
import os
from memory_profiler import memory_usage
from mcp_server.dispatcher import Dispatcher

@pytest.mark.performance
class TestMemoryUsage:
    def test_indexing_memory_usage(self):
        """Test memory usage during indexing."""
        def index_large_codebase():
            dispatcher = Dispatcher()
            dispatcher.load_plugins()
            
            # Index 100 files
            for i in range(100):
                code = f"""
def function_{i}():
    pass

class Class_{i}:
    def method_{i}(self):
        pass
"""
                dispatcher.dispatch(f"file_{i}.py", code * 10)
        
        # Measure memory usage
        mem_usage = memory_usage(index_large_codebase)
        
        # Memory usage should be reasonable
        max_memory = max(mem_usage)
        min_memory = min(mem_usage)
        memory_increase = max_memory - min_memory
        
        # Should not use more than 100MB for this test
        assert memory_increase < 100
        
        print(f"Memory usage: {min_memory:.1f}MB -> {max_memory:.1f}MB")
        print(f"Increase: {memory_increase:.1f}MB")
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations."""
        dispatcher = Dispatcher()
        dispatcher.load_plugins()
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform repeated indexing
        for iteration in range(10):
            for i in range(100):
                code = f"def func_{i}(): pass"
                dispatcher.dispatch(f"test_{i}.py", code)
            
            # Force garbage collection
            import gc
            gc.collect()
            
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = current_memory - initial_memory
            
            # Memory growth should stabilize
            if iteration > 5:
                assert memory_growth < 50  # Should not grow more than 50MB
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        print(f"Total memory growth: {total_growth:.1f}MB")
```

## Test Coverage

### Coverage Configuration

Add to `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["mcp_server"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
    "*/venv/*",
    "*/.venv/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "class .*\\(Protocol\\):",
    "@abstractmethod"
]
precision = 2
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"

[tool.coverage.xml]
output = "coverage.xml"
```

### Running Coverage

```bash
# Run tests with coverage
pytest --cov=mcp_server --cov-report=html --cov-report=term

# Run specific test categories with coverage
pytest -m unit --cov=mcp_server
pytest -m integration --cov=mcp_server
pytest -m plugin --cov=mcp_server

# Generate detailed HTML report
pytest --cov=mcp_server --cov-report=html
open htmlcov/index.html

# Check coverage thresholds
pytest --cov=mcp_server --cov-fail-under=80
```

### Coverage Goals

- **Overall Coverage**: Aim for >80%
- **Core Components**: >90% (dispatcher, gateway, watcher)
- **Plugins**: >85%
- **Utilities**: >90%
- **Integration Points**: >75%

## Continuous Integration

### GitHub Actions Workflow

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, '3.10', 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run linting
      run: |
        black --check mcp_server tests
        isort --check-only mcp_server tests
        flake8 mcp_server tests
        mypy mcp_server
    
    - name: Run unit tests
      run: |
        pytest -m unit -v --cov=mcp_server --cov-report=xml
    
    - name: Run integration tests
      run: |
        pytest -m integration -v --cov=mcp_server --cov-append --cov-report=xml
    
    - name: Run plugin tests
      run: |
        pytest -m plugin -v --cov=mcp_server --cov-append --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
    
    - name: Generate coverage report
      run: |
        coverage report
        coverage html
    
    - name: Upload coverage artifacts
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report
        path: htmlcov/
  
  performance:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run performance tests
      run: |
        pytest -m performance -v --benchmark-only
    
    - name: Upload benchmark results
      uses: actions/upload-artifact@v3
      with:
        name: benchmark-results
        path: .benchmarks/
```

## Best Practices

### 1. Test Organization

- Keep tests close to the code they test
- Use descriptive test names that explain what is being tested
- Group related tests in classes
- Use fixtures for common setup

### 2. Test Data

- Use fixtures for test data
- Keep test data minimal but representative
- Use factories for complex object creation
- Clean up test data after tests

### 3. Mocking and Patching

```python
# Example of proper mocking
from unittest.mock import Mock, patch

@patch('mcp_server.external.api_client')
def test_with_mocked_api(mock_client):
    mock_client.fetch.return_value = {"status": "ok"}
    # Test code here
```

### 4. Async Testing

```python
# Use pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```

### 5. Parameterized Tests

```python
# Test multiple scenarios efficiently
@pytest.mark.parametrize("input,expected", [
    ("python", True),
    ("javascript", True),
    ("unknown", False),
])
def test_language_support(input, expected):
    assert supports_language(input) == expected
```

### 6. Test Isolation

- Each test should be independent
- Use setup and teardown properly
- Don't rely on test execution order
- Clean up resources after tests

### 7. Performance Test Guidelines

- Set realistic performance targets
- Test with representative data sizes
- Run performance tests separately from unit tests
- Track performance over time

### 8. Coverage Guidelines

- Don't aim for 100% coverage at all costs
- Focus on critical paths and edge cases
- Exclude generated code and interfaces
- Review uncovered code regularly

## Running Tests

### Quick Test Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_dispatcher.py

# Run specific test class
pytest tests/unit/test_dispatcher.py::TestDispatcher

# Run specific test method
pytest tests/unit/test_dispatcher.py::TestDispatcher::test_register_plugin

# Run tests matching pattern
pytest -k "test_index"

# Run tests with specific marker
pytest -m unit
pytest -m "not slow"

# Run tests in parallel
pytest -n auto

# Run with coverage
pytest --cov=mcp_server

# Run and stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Run with debugging
pytest --pdb
```

### Test Debugging

```python
# Add breakpoint in test
def test_something():
    import pdb; pdb.set_trace()
    # Or in Python 3.7+
    breakpoint()
    
    result = function_under_test()
    assert result == expected
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure PYTHONPATH includes project root
   - Check for circular imports
   - Verify all dependencies are installed

2. **Flaky Tests**
   - Add proper waits for async operations
   - Mock time-dependent code
   - Ensure proper test isolation

3. **Slow Tests**
   - Use pytest-timeout to identify slow tests
   - Mock expensive operations
   - Use smaller test datasets

4. **Coverage Gaps**
   - Review coverage reports regularly
   - Add tests for error conditions
   - Test edge cases and boundaries

This comprehensive testing guide should help maintain high code quality and reliability for the Code-Index-MCP project. Regular testing and coverage monitoring will ensure the codebase remains maintainable and bug-free.