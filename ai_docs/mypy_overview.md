# mypy AI Context
Last Updated: 2025-01-06

## Framework Overview
mypy is a static type checker for Python that helps catch type-related bugs before runtime. It uses Python's type hints (PEP 484) to analyze code and ensure type safety.

## Current Version & Features
- **Version**: mypy 1.5.1+ (configured in requirements.txt)
- **Python Support**: Full support for Python 3.8+
- **Key Features**:
  - Gradual typing (mix typed and untyped code)
  - Type inference
  - Generics support
  - Protocol (structural subtyping)
  - TypedDict for dictionaries
  - Literal types

## Type Annotation Patterns

### Basic Type Hints
```python
from typing import List, Dict, Optional, Union, Tuple

def process_data(
    items: List[str],
    config: Dict[str, int],
    timeout: Optional[float] = None
) -> Tuple[bool, str]:
    """Process items with configuration"""
    result: bool = True
    message: str = "Success"
    return result, message
```

### Class Type Hints
```python
from typing import Protocol, TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    def __init__(self) -> None:
        self._items: List[T] = []
    
    def add(self, item: T) -> None:
        self._items.append(item)
    
    def get(self, index: int) -> Optional[T]:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
```

### Protocol Example
```python
from typing import Protocol

class Searchable(Protocol):
    def search(self, query: str) -> List[Dict[str, Any]]:
        ...

class PluginBase:
    def search(self, query: str) -> List[Dict[str, Any]]:
        return []

# PluginBase satisfies Searchable protocol
```

## Integration with Project
- Configuration likely in `pyproject.toml` or `setup.cfg`
- Run with `mypy mcp_server` or `make type-check`
- Type stubs in `.pyi` files if needed
- Gradual adoption possible

## Common Configuration
```ini
# mypy.ini or setup.cfg
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

# Per-module options
[mypy-tests.*]
ignore_errors = True

[mypy-third_party_module.*]
ignore_missing_imports = True
```

## Common Patterns in This Project

### Plugin System Types
```python
from typing import Protocol, Dict, Any, Type

class Plugin(Protocol):
    language: str
    
    def index(self, file_path: str) -> Dict[str, Any]:
        ...
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        ...

PluginRegistry = Dict[str, Type[Plugin]]
```

### Async Types
```python
from typing import AsyncIterator, Coroutine
import asyncio

async def process_files(
    paths: List[str]
) -> AsyncIterator[Dict[str, Any]]:
    for path in paths:
        result = await index_file(path)
        yield result

async def index_file(path: str) -> Dict[str, Any]:
    # Async file processing
    return {"path": path, "status": "indexed"}
```

## Best Practices
1. **Start Gradually**: Type public APIs first
2. **Use Optional**: Explicit about nullable values
3. **Avoid Any**: Use specific types or Union
4. **Type Aliases**: For complex repeated types
5. **Protocols**: For structural subtyping

## Common Type Patterns
```python
from typing import TypeAlias, Literal, TypedDict, Final

# Type aliases
PathLike: TypeAlias = Union[str, Path]
JSONValue: TypeAlias = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]

# Literal types
Status = Literal["pending", "processing", "complete", "error"]

# TypedDict for structured dicts
class SearchResult(TypedDict):
    path: str
    line: int
    content: str
    score: float

# Constants
MAX_RETRIES: Final = 3
```

## Common Issues and Solutions
1. **Import Cycles**: Use `TYPE_CHECKING` and string annotations
2. **Third-party Types**: Install type stubs (types-* packages)
3. **Dynamic Code**: Use `cast()` or `# type: ignore` sparingly
4. **Generics Variance**: Understand covariance/contravariance
5. **Protocol vs ABC**: Prefer Protocol for flexibility

## Advanced Features
```python
from typing import overload, TypeGuard

@overload
def process(data: str) -> str: ...

@overload 
def process(data: int) -> int: ...

def process(data: Union[str, int]) -> Union[str, int]:
    if isinstance(data, str):
        return data.upper()
    return data * 2

def is_valid_result(obj: Any) -> TypeGuard[SearchResult]:
    return (
        isinstance(obj, dict) and
        "path" in obj and
        "line" in obj and
        isinstance(obj["line"], int)
    )
```

## Performance Considerations
- mypy runs separately from Python (no runtime overhead)
- Can be slow on large codebases (use daemon mode)
- Cache results between runs
- Incremental checking available

## References
- Official Docs: https://mypy.readthedocs.io/
- Type Hints PEP: https://peps.python.org/pep-0484/
- Typing Module: https://docs.python.org/3/library/typing.html
- Common Patterns: https://mypy.readthedocs.io/en/stable/common_issues.html

## AI Agent Notes
- Add types gradually, start with public APIs
- Use protocols for plugin interfaces
- Keep type annotations readable
- Don't over-annotate obvious cases
- Run mypy in CI/CD pipeline
- Fix type errors before merging

---
*Updated via documentation analysis on 2025-01-06*