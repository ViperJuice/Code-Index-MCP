# TreeSitter Multi-Language Support Refactoring Plan

## Overview
Refactor TreeSitterWrapper to support multiple languages dynamically with regex fallback parsers for robustness.

## Current State Analysis

### Working Components
1. **Go Plugin** (`mcp_server/plugins/go_plugin/plugin.py`):
   - Already has `GoTreeSitterWrapper` with regex-based parsing
   - Provides a proven pattern for fallback parsing
   - Handles functions, interfaces, structs, types, constants, variables

2. **Python Plugin** works because TreeSitterWrapper is hardcoded for Python

3. **Plugin Architecture**:
   - All plugins inherit from `IPlugin` base class
   - Standard `indexFile()` method signature
   - Existing fuzzy indexer and SQLite storage integration

### Broken Components
- TreeSitterWrapper only supports Python (hardcoded `tree_sitter_python()`)
- Ruby, PHP, JavaScript, C, C++, Dart, HTML/CSS plugins all fail
- No fallback when tree-sitter parsing fails

## Implementation Plan

### Phase 1: Refactor TreeSitterWrapper (Priority: High)

#### 1.1 Create Language-Agnostic TreeSitterWrapper

```python
# mcp_server/utils/treesitter_wrapper.py

class TreeSitterWrapper:
    """Multi-language Tree-sitter wrapper with automatic grammar loading."""
    
    LANGUAGE_MAPPING = {
        'python': 'tree_sitter_python',
        'javascript': 'tree_sitter_javascript', 
        'typescript': 'tree_sitter_typescript',
        'go': 'tree_sitter_go',
        'rust': 'tree_sitter_rust',
        'c': 'tree_sitter_c',
        'cpp': 'tree_sitter_cpp',
        'java': 'tree_sitter_java',
        'ruby': 'tree_sitter_ruby',
        'php': 'tree_sitter_php',
        'html': 'tree_sitter_html',
        'css': 'tree_sitter_css',
    }
    
    def __init__(self, language: str = 'python'):
        self.language = language
        self._parser = None
        self._language_obj = None
        self._init_parser()
    
    def _init_parser(self):
        """Initialize parser for specified language."""
        # Implementation details...
```

#### 1.2 Update Existing Plugins
Each plugin needs to pass its language to TreeSitterWrapper:

```python
# Example for JavaScript plugin
self._ts = TreeSitterWrapper(language='javascript')
```

### Phase 2: Create Base Regex Parser (Priority: High)

#### 2.1 Abstract Regex Parser Base Class

```python
# mcp_server/utils/regex_parser.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import re

class RegexParser(ABC):
    """Base class for regex-based language parsers."""
    
    @abstractmethod
    def get_patterns(self) -> Dict[str, re.Pattern]:
        """Return regex patterns for language constructs."""
        pass
    
    def parse_file(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse file content using regex patterns."""
        # Common implementation
```

#### 2.2 Language-Specific Regex Parsers

Based on the Go plugin pattern, create parsers for each language:

```python
# mcp_server/utils/regex_parsers/python_regex_parser.py
class PythonRegexParser(RegexParser):
    def get_patterns(self):
        return {
            'function': re.compile(r'^\s*(?:async\s+)?def\s+(\w+)\s*\([^)]*\):', re.MULTILINE),
            'class': re.compile(r'^\s*class\s+(\w+)\s*(?:\([^)]*\))?:', re.MULTILINE),
            'method': re.compile(r'^\s*(?:async\s+)?def\s+(\w+)\s*\(self[^)]*\):', re.MULTILINE),
            # ... more patterns
        }
```

### Phase 3: Create Fallback Wrapper (Priority: High)

#### 3.1 Smart Parser Wrapper

```python
# mcp_server/utils/smart_parser.py

class SmartParser:
    """Parser that tries tree-sitter first, falls back to regex."""
    
    def __init__(self, language: str):
        self.language = language
        self.tree_sitter = None
        self.regex_parser = None
        
        # Try to initialize tree-sitter
        try:
            self.tree_sitter = TreeSitterWrapper(language)
        except Exception as e:
            logger.warning(f"Tree-sitter unavailable for {language}: {e}")
        
        # Always initialize regex parser as fallback
        self.regex_parser = self._get_regex_parser(language)
    
    def parse(self, content: str) -> ParseResult:
        """Parse with tree-sitter if available, otherwise regex."""
        if self.tree_sitter:
            try:
                return self.tree_sitter.parse(content)
            except Exception as e:
                logger.debug(f"Tree-sitter parse failed, using regex: {e}")
        
        return self.regex_parser.parse_file(content)
```

### Phase 4: Update All Language Plugins (Priority: Medium)

#### 4.1 Plugin Update Pattern

Each plugin should follow this pattern:

```python
class Plugin(IPlugin):
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None):
        self._parser = SmartParser(self.lang)  # Auto-handles fallback
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        # ... rest of init
    
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        # Use smart parser
        parse_result = self._parser.parse(content)
        # Process parse_result...
```

### Phase 5: Testing and Validation (Priority: High)

#### 5.1 Create Test Suite
- Test each language with both tree-sitter and regex
- Verify fallback behavior
- Performance benchmarks

#### 5.2 Test Files Already Available
Leverage existing test fixtures:
- `/home/jenner/Code/Code-Index-MCP/tests/fixtures/`
- Go: `go/sample.go`
- Java/Kotlin: `java/Sample.java`, `kotlin/Sample.kt`
- PHP: `php/User.php`
- Ruby: `ruby/sample_model.rb`
- Rust: Various test files

## Implementation Order

1. **Week 1**: 
   - Refactor TreeSitterWrapper for multi-language support
   - Create RegexParser base class
   - Implement Python and JavaScript regex parsers (most common)

2. **Week 2**:
   - Create SmartParser wrapper
   - Update Python and JavaScript plugins
   - Add comprehensive tests

3. **Week 3**:
   - Implement remaining regex parsers (Go pattern already exists)
   - Update all remaining plugins
   - Performance optimization

## Code Reuse Opportunities

1. **Go Plugin Pattern**: 
   - Copy `GoTreeSitterWrapper` regex patterns
   - Use as template for other languages

2. **Existing Plugin Structure**:
   - All plugins already have similar initialization
   - Just need to swap TreeSitterWrapper → SmartParser

3. **Test Infrastructure**:
   - Test files already exist in fixtures
   - Plugin test patterns can be reused

## Risk Mitigation

1. **Backward Compatibility**: Keep existing TreeSitterWrapper API
2. **Gradual Rollout**: Update plugins one at a time
3. **Feature Flags**: Add config option to force regex-only mode
4. **Logging**: Comprehensive logging for debugging parser selection

## Success Metrics

1. All 20,039 files successfully indexed
2. <5% performance degradation with regex fallback
3. Zero crashes from missing tree-sitter grammars
4. Clear logs showing parser selection

## Configuration

Add to `settings.py`:
```python
PARSER_SETTINGS = {
    'prefer_tree_sitter': True,
    'fallback_to_regex': True,
    'force_regex_only': False,  # For debugging
    'log_parser_selection': True
}
```

## Next Steps

1. Create `mcp_server/utils/regex_parser.py` base class
2. Refactor `mcp_server/utils/treesitter_wrapper.py` 
3. Create `mcp_server/utils/smart_parser.py`
4. Update Python plugin as proof of concept
5. Run indexing tests