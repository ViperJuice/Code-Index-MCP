# pytest AI Context
Last Updated: 2025-01-06

## Framework Overview
pytest is a mature Python testing framework that makes it easy to write simple and scalable test cases. It's the de facto standard for Python testing with powerful features and extensive plugin ecosystem.

## Current Version & Features
- **Latest Version**: pytest 7.4+ (as of 2025)
- **Key Features**: 
  - Automatic test discovery
  - Powerful assertions with detailed failure reports
  - Fixtures for setup/teardown and dependency injection
  - Parametrized testing
  - Parallel execution with pytest-xdist
  - Extensive plugin architecture

## Common Patterns in This Project

### Test Structure
```python
# tests/test_module.py
import pytest

class TestComponent:
    @pytest.fixture
    def setup_data(self):
        """Fixture for test data"""
        return {"key": "value"}
    
    def test_functionality(self, setup_data):
        """Test with fixture"""
        assert setup_data["key"] == "value"
```

### Fixtures
```python
# conftest.py - Shared fixtures
@pytest.fixture(scope="session")
def test_db():
    """Database fixture for testing"""
    db = create_test_database()
    yield db
    db.cleanup()

@pytest.fixture
def mock_api(monkeypatch):
    """Mock external API calls"""
    def mock_response(*args, **kwargs):
        return {"status": "ok"}
    monkeypatch.setattr("requests.get", mock_response)
```

### Parametrized Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("python", "python_plugin"),
    ("javascript", "js_plugin"),
    ("unknown", None),
])
def test_plugin_resolution(input, expected):
    assert get_plugin(input) == expected
```

## Integration with Project
- Test files in `tests/` directory
- Base test class in `tests/base_test.py`
- Fixtures in `tests/conftest.py`
- Run with `pytest` or `make test`
- Coverage reports with pytest-cov

## Best Practices
1. **Test Organization**: Group related tests in classes
2. **Fixtures**: Use for common setup, prefer over setUp/tearDown
3. **Mocking**: Use monkeypatch or unittest.mock
4. **Assertions**: Use plain assert with descriptive messages
5. **Test Names**: Descriptive test_what_when_expected pattern

## Common Commands
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_module.py

# Run with coverage
pytest --cov=mcp_server --cov-report=html

# Run in parallel
pytest -n auto

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

## Markers and Configuration
```python
# Custom markers
@pytest.mark.slow
def test_expensive_operation():
    pass

@pytest.mark.skipif(condition, reason="...")
def test_conditional():
    pass
```

## Common Issues and Solutions
1. **Import Errors**: Ensure PYTHONPATH includes project root
2. **Fixture Scope**: Understand session vs function scope
3. **Test Isolation**: Each test should be independent
4. **Async Tests**: Use pytest-asyncio for async code
5. **Database Tests**: Use transactions and rollback

## Performance Considerations
- Use pytest-xdist for parallel execution
- Minimize fixture scope where appropriate
- Mock expensive operations
- Use pytest-benchmark for performance tests

## References
- Official Docs: https://docs.pytest.org/
- Best Practices: https://docs.pytest.org/en/latest/explanation/goodpractices.html
- Fixtures: https://docs.pytest.org/en/latest/explanation/fixtures.html
- Plugins: https://docs.pytest.org/en/latest/reference/plugin_list.html

## AI Agent Notes
- Always use fixtures over manual setup/teardown
- Keep tests independent and idempotent
- Mock external dependencies
- Use descriptive test names
- Group related tests in classes
- Run tests before committing changes

---
*Updated via documentation analysis on 2025-01-06*