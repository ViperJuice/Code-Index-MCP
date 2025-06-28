# Black & isort AI Context
Last Updated: 2025-01-06

## Framework Overview
Black and isort are Python code formatting tools that work together to ensure consistent, readable code:
- **Black**: An opinionated code formatter that enforces consistent style
- **isort**: Sorts and organizes Python imports

## Current Versions & Features
- **Black**: 23.7.0+ (configured in requirements.txt)
- **isort**: 5.12.0+ (configured in requirements.txt)
- Both tools are deterministic and work together seamlessly

## Black Configuration

### Key Features
- No configuration needed (opinionated)
- Consistent formatting across all code
- AST-safe transformations only
- Fast and reliable

### Common Patterns
```python
# Before Black
def function(arg1,arg2,arg3="default",*args,**kwargs):
    return {'key':'value','another_key':'another_value'}

# After Black
def function(
    arg1,
    arg2,
    arg3="default",
    *args,
    **kwargs
):
    return {
        "key": "value",
        "another_key": "another_value"
    }
```

### Configuration (pyproject.toml)
```toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
```

## isort Configuration

### Key Features
- Groups imports (stdlib, third-party, local)
- Removes duplicate imports
- Sorts alphabetically within groups
- Compatible with Black

### Import Grouping
```python
# After isort
# Standard library imports
import os
import sys
from datetime import datetime
from typing import Dict, List

# Third-party imports
import pytest
from fastapi import FastAPI
from pydantic import BaseModel

# Local imports
from mcp_server.core import Config
from mcp_server.utils import logger
```

### Configuration (pyproject.toml)
```toml
[tool.isort]
profile = "black"
line_length = 88
known_first_party = ["mcp_server"]
skip_gitignore = true
```

## Integration with Project
- Configured in `Makefile` for easy formatting
- Pre-commit hooks can enforce formatting
- CI/CD checks formatting compliance
- Run with: `make format` or `make lint`

## Usage Commands
```bash
# Format with Black
black mcp_server tests

# Check without modifying
black --check mcp_server tests

# Sort imports with isort
isort mcp_server tests

# Check import sorting
isort --check-only mcp_server tests

# Combined (from Makefile)
make format  # Runs both
make lint    # Checks both
```

## Common Patterns in This Project

### String Quotes
- Black prefers double quotes
- Single quotes only for strings containing double quotes

### Line Length
- Default 88 characters (Black's recommendation)
- Automatic line breaking for long lines

### Function Definitions
- Multi-line for many parameters
- Trailing commas in multi-line

## Best Practices
1. **Run Before Commit**: Always format before committing
2. **CI Integration**: Fail builds on formatting issues
3. **Editor Integration**: Configure auto-format on save
4. **Team Consistency**: Everyone uses same tools
5. **No Manual Overrides**: Trust the tools

## Common Issues and Solutions
1. **Merge Conflicts**: Format entire file after resolving
2. **Long Strings**: Use implicit string concatenation
3. **Complex Expressions**: Let Black handle line breaks
4. **Import Conflicts**: isort profile="black" prevents conflicts

## Editor Integration

### VS Code
```json
{
    "python.formatting.provider": "black",
    "python.sortImports.path": "isort",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

### Pre-commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
```

## References
- Black: https://black.readthedocs.io/
- isort: https://pycqa.github.io/isort/
- Black playground: https://black.vercel.app/
- PEP 8: https://pep8.org/

## AI Agent Notes
- Always run both tools before committing
- Don't fight the formatter - adapt code structure
- Use `# fmt: off/on` sparingly for special formatting
- Keep imports organized and minimal
- Both tools are idempotent - safe to run multiple times

---
*Updated via documentation analysis on 2025-01-06*