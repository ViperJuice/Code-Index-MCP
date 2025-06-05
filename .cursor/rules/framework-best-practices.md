# Code-Index-MCP Framework Best Practices

This document defines best practices and coding standards for the Code-Index-MCP project when using Cursor or other AI-powered coding assistants.

## Project Overview

Code-Index-MCP is a production-ready Model Context Protocol (MCP) server that provides advanced code indexing and analysis capabilities. It complements AI coding assistants like Claude Code by adding deep code search, symbol lookup, and cross-repository analysis.

## Architecture Patterns

### 1. Plugin Architecture
- All language plugins MUST inherit from `PluginBase`
- Use dependency injection for services
- Follow the Template Method pattern for parsing

```python
# Good
class RustPlugin(PluginBase):
    def __init__(self, parser_factory: ParserFactory):
        self.parser = parser_factory.create_parser("rust")
```

### 2. MCP Protocol Implementation
- Use FastAPI for HTTP endpoints
- Implement JSON-RPC 2.0 for MCP communication
- Follow MCP 2024-11-05 specification strictly

### 3. Error Handling
- Use Result[T, Error] pattern for all operations
- Never use bare exceptions
- Always provide context in error messages

```python
# Good
def parse_file(path: str) -> Result[AST, ParseError]:
    try:
        # parsing logic
        return Ok(ast)
    except Exception as e:
        return Err(ParseError(f"Failed to parse {path}: {str(e)}"))
```

## Coding Standards

### Python Style
- Follow PEP 8 with Black formatter (88 char lines)
- Use type hints for ALL functions
- Prefer composition over inheritance
- Use descriptive variable names

### Naming Conventions
- Classes: PascalCase (e.g., `LanguagePlugin`)
- Functions/Methods: snake_case (e.g., `index_file`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_FILE_SIZE`)
- Private methods: prefix with underscore (e.g., `_parse_ast`)

### Import Organization
```python
# Standard library
import os
import sys
from typing import Dict, List, Optional

# Third-party
import pytest
from fastapi import FastAPI

# Local application
from mcp_server.core import errors
from mcp_server.plugins.base import PluginBase
```

## Testing Requirements

### Test Coverage
- Minimum 80% coverage for new code
- 100% coverage for core MCP protocol code
- Write tests BEFORE implementation (TDD)

### Test Structure
```python
class TestFeatureName:
    @pytest.fixture
    def setup_data(self):
        # Setup test data
        
    def test_happy_path(self, setup_data):
        # Test normal operation
        
    def test_edge_cases(self, setup_data):
        # Test boundary conditions
        
    def test_error_handling(self, setup_data):
        # Test failure scenarios
```

## Performance Guidelines

### Target Metrics
- Symbol lookup: <50ms (p95)
- Code search: <200ms (p95)
- File indexing: 15,000+ files/minute
- Memory usage: <1.5GB for 100K files

### Optimization Patterns
- Use async/await for I/O operations
- Implement connection pooling
- Cache frequently accessed data
- Batch database operations

## Security Best Practices

### Input Validation
- Validate ALL user inputs
- Use Pydantic models for request/response
- Sanitize file paths to prevent traversal

### Secret Management
- NEVER commit secrets to repository
- Use environment variables for config
- Implement secret scanning in CI/CD

## Documentation Standards

### Code Documentation
- Docstrings for ALL public functions
- Include examples in docstrings
- Document return types and exceptions

```python
def index_file(self, path: str) -> Dict[str, Any]:
    """Index a source code file and extract symbols.
    
    Args:
        path: Absolute path to the file to index
        
    Returns:
        Dictionary containing:
            - symbols: List of discovered symbols
            - imports: List of import statements
            - errors: Any parsing errors encountered
            
    Raises:
        FileNotFoundError: If the file doesn't exist
        PermissionError: If file cannot be read
        
    Example:
        >>> plugin = PythonPlugin()
        >>> result = plugin.index_file("/path/to/file.py")
        >>> print(result["symbols"])
        [{"name": "MyClass", "type": "class", "line": 10}]
    """
```

### AGENTS.md Maintenance
- Update AGENTS.md when adding new patterns
- Document frequently used commands
- Include environment setup instructions

## Development Workflow

### Essential Commands
```bash
# Development setup
make dev-setup

# Run with hot reload
make dev-run

# Test in watch mode
make dev-test

# Format and lint
make format lint

# Run type checking
make typecheck
```

### Pre-commit Checklist
1. Run tests: `make test`
2. Check coverage: `make test-coverage`
3. Run linters: `make lint`
4. Format code: `make format`
5. Update documentation if needed

## Common Patterns

### Singleton Services
```python
class ServiceRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### Factory Pattern
```python
class PluginFactory:
    @staticmethod
    def create_plugin(language: str) -> PluginBase:
        plugins = {
            "python": PythonPlugin,
            "javascript": JavaScriptPlugin,
            # ...
        }
        return plugins[language]()
```

### Async Context Managers
```python
async with DatabaseConnection() as conn:
    result = await conn.execute(query)
```

## Debugging Tips

### Logging
- Use structured logging with context
- Include correlation IDs for request tracking
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)

### Development Tools
- Use `ipdb` for debugging: `import ipdb; ipdb.set_trace()`
- Enable debug mode: `export MCP_DEBUG=true`
- Use VS Code debugger configuration in `.vscode/launch.json`

## Integration Guidelines

### MCP Client Integration
- Always implement the latest MCP specification
- Test with MCP Inspector regularly
- Provide clear error messages for clients

### Plugin Development
1. Create plugin directory: `mcp_server/plugins/language_plugin/`
2. Implement `plugin.py` inheriting from `PluginBase`
3. Add comprehensive tests
4. Update documentation
5. Register in plugin manager

## Performance Profiling

### Tools
- Use `cProfile` for CPU profiling
- Use `memory_profiler` for memory analysis
- Run benchmarks: `make benchmark`

### Optimization Priority
1. Optimize hot paths first (symbol lookup, search)
2. Implement caching for repeated operations
3. Use batch operations for database access
4. Consider async/parallel processing

## Contribution Guidelines

### Pull Request Process
1. Create feature branch from `main`
2. Write tests first (TDD)
3. Implement feature
4. Ensure all tests pass
5. Update documentation
6. Submit PR with clear description

### Code Review Checklist
- [ ] Tests cover new functionality
- [ ] Type hints are complete
- [ ] Documentation is updated
- [ ] Performance impact considered
- [ ] Security implications reviewed
- [ ] Error handling is comprehensive

## AI Assistant Instructions

When working with this codebase:
1. Always check existing patterns before implementing new features
2. Prioritize test-driven development
3. Follow the established architecture patterns
4. Maintain backward compatibility
5. Document any new patterns in AGENTS.md

Remember: This project complements AI coding assistants by providing deep code intelligence capabilities through the MCP protocol.