# Code-Index-MCP Test Suite

This directory contains the comprehensive test suite for the Code-Index-MCP project.

## Test Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `test_gateway.py` - Tests for FastAPI endpoints and API gateway
- `test_dispatcher.py` - Tests for plugin routing and caching logic
- `test_sqlite_store.py` - Tests for SQLite persistence layer
- `test_watcher.py` - Tests for file system monitoring
- `test_python_plugin.py` - Tests for Python language plugin

## Running Tests

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_server --cov-report=html
```

### Using Make

```bash
# Run unit tests only
make test

# Run all tests with coverage
make test-all

# Run specific test categories
make test-unit
make test-integration
make benchmark
```

### Test Categories

Tests are marked with the following categories:

- `unit` - Fast, isolated unit tests
- `integration` - Tests requiring external resources
- `slow` - Tests that take >1s to run
- `benchmark` - Performance benchmarks
- `e2e` - End-to-end tests
- `requires_db` - Tests requiring database
- `requires_network` - Tests requiring network

Run specific categories:

```bash
# Only unit tests
pytest -m "unit"

# Integration tests only
pytest -m "integration"

# Exclude slow tests
pytest -m "not slow"
```

## Coverage Requirements

The project maintains >80% code coverage. Coverage reports are generated in:

- Terminal: Use `--cov-report=term-missing`
- HTML: `htmlcov/index.html`
- XML: `coverage.xml` (for CI integration)

## CI/CD Integration

Tests run automatically on:

- Every push to `main` and `develop` branches
- All pull requests
- Daily at 2 AM UTC

The CI pipeline includes:

1. **Linting** - Black, isort, flake8, mypy
2. **Testing** - Multi-OS, multi-Python version matrix
3. **Coverage** - Upload to Codecov
4. **Security** - Safety and Bandit scans
5. **Performance** - Benchmark tests
6. **Docker** - Build verification

## Writing Tests

### Test Organization

```python
class TestComponentName:
    """Test suite for ComponentName."""
    
    def test_specific_behavior(self):
        """Test that component does X when Y."""
        # Arrange
        # Act
        # Assert
```

### Using Fixtures

Common fixtures from `conftest.py`:

```python
def test_with_sqlite(sqlite_store):
    """Test using SQLite store fixture."""
    # sqlite_store is a fresh SQLite instance
    
def test_with_mock_plugin(mock_plugin):
    """Test using mock plugin."""
    # mock_plugin is a Mock(spec=IPlugin)
    
def test_with_temp_files(temp_code_directory):
    """Test with temporary code files."""
    # temp_code_directory contains sample code files
```

### Performance Testing

```python
@pytest.mark.benchmark
def test_performance(benchmark_results):
    """Benchmark critical operations."""
    from conftest import measure_time
    
    with measure_time("operation_name", benchmark_results):
        # Code to benchmark
        pass
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure package is installed with `pip install -e .`
2. **Fixture not found**: Check if test file imports from conftest
3. **Slow tests**: Use `-m "not slow"` to skip slow tests
4. **Database errors**: Tests use in-memory SQLite by default

### Debug Mode

Run tests with verbose output and stop on first failure:

```bash
pytest -vvs -x
```

Use pytest's built-in debugger:

```bash
pytest --pdb
```

## Contributing

When adding new tests:

1. Follow existing naming conventions
2. Add appropriate markers (`@pytest.mark.unit`, etc.)
3. Include docstrings explaining what is tested
4. Aim for >80% coverage of new code
5. Run `make lint` before committing