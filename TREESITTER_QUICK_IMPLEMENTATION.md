# Quick TreeSitter Implementation Guide

## Immediate Actions (Can be done in 1-2 hours)

### Step 1: Create Base Regex Parser (10 minutes)

Create `mcp_server/utils/regex_parser.py`:
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple
import re

class RegexParser(ABC):
    """Base class for regex-based language parsers."""
    
    @abstractmethod
    def get_patterns(self) -> Dict[str, re.Pattern]:
        """Return regex patterns for language constructs."""
        pass
    
    def parse_file(self, content: str) -> List[Dict[str, Any]]:
        """Parse file content using regex patterns."""
        symbols = []
        patterns = self.get_patterns()
        
        for symbol_type, pattern in patterns.items():
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                symbols.append({
                    'name': match.group(1),
                    'kind': symbol_type,
                    'line': line_num,
                    'signature': match.group(0).strip()
                })
        
        return symbols
```

### Step 2: Copy Go Parser Pattern (5 minutes)

The Go plugin already has a working regex parser! Copy its patterns:

**From**: `mcp_server/plugins/go_plugin/plugin.py` (lines 22-96)
**Pattern to reuse**:
- Function regex: `r'^\s*func\s+(?:\([^)]*\)\s+)?(\w+)(?:\[[^\]]*\])?\s*\([^)]*\)(?:\s*[^{]*)?(?:\s*\{|\s*$)'`
- Multiple pattern types (functions, interfaces, structs, types, constants, variables)
- Line number calculation method

### Step 3: Create Language-Specific Parsers (20 minutes)

Create regex parsers for each language by adapting patterns:

#### Python Parser
```python
# mcp_server/utils/regex_parsers/python_parser.py
from ..regex_parser import RegexParser
import re

class PythonRegexParser(RegexParser):
    def get_patterns(self):
        return {
            'function': re.compile(r'^\s*(?:async\s+)?def\s+(\w+)\s*\([^)]*\):', re.MULTILINE),
            'class': re.compile(r'^\s*class\s+(\w+)\s*(?:\([^)]*\))?:', re.MULTILINE),
            'constant': re.compile(r'^([A-Z_]+)\s*=', re.MULTILINE),
        }
```

#### JavaScript Parser  
```python
# mcp_server/utils/regex_parsers/javascript_parser.py
class JavaScriptRegexParser(RegexParser):
    def get_patterns(self):
        return {
            'function': re.compile(r'^\s*(?:async\s+)?function\s+(\w+)\s*\([^)]*\)', re.MULTILINE),
            'arrow_function': re.compile(r'^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>', re.MULTILINE),
            'class': re.compile(r'^\s*class\s+(\w+)', re.MULTILINE),
            'const': re.compile(r'^\s*const\s+(\w+)\s*=', re.MULTILINE),
        }
```

### Step 4: Enhance TreeSitterWrapper (15 minutes)

Modify `mcp_server/utils/treesitter_wrapper.py`:

```python
class TreeSitterWrapper:
    """Multi-language Tree-sitter wrapper."""
    
    LANGUAGE_FUNCTIONS = {
        'python': 'tree_sitter_python',
        'javascript': 'tree_sitter_javascript',
        'go': 'tree_sitter_go',
        'rust': 'tree_sitter_rust',
        'ruby': 'tree_sitter_ruby',
        'php': 'tree_sitter_php',
        'c': 'tree_sitter_c',
        'cpp': 'tree_sitter_cpp',
    }
    
    def __init__(self, language: str = 'python'):
        self.language = language
        lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
        self._lib = ctypes.CDLL(str(lib_path))
        
        # Get the appropriate language function
        lang_func_name = self.LANGUAGE_FUNCTIONS.get(language)
        if not lang_func_name:
            raise ValueError(f"Unsupported language: {language}")
            
        # Get language function and set return type
        lang_func = getattr(self._lib, lang_func_name)
        lang_func.restype = ctypes.c_void_p
        
        self._language = Language(lang_func())
        self._parser = Parser()
        self._parser.language = self._language
```

### Step 5: Create Smart Parser Wrapper (10 minutes)

Create `mcp_server/utils/smart_parser.py`:

```python
import logging
from typing import Optional, List, Dict, Any
from .treesitter_wrapper import TreeSitterWrapper
from .regex_parsers import get_regex_parser  # Factory function

logger = logging.getLogger(__name__)

class SmartParser:
    """Parser with automatic tree-sitter/regex fallback."""
    
    def __init__(self, language: str):
        self.language = language
        self.tree_sitter = None
        self.regex_parser = get_regex_parser(language)
        
        # Try tree-sitter
        try:
            self.tree_sitter = TreeSitterWrapper(language)
            logger.debug(f"Tree-sitter initialized for {language}")
        except Exception as e:
            logger.warning(f"Tree-sitter unavailable for {language}, using regex: {e}")
    
    def parse(self, content: str) -> List[Dict[str, Any]]:
        """Parse content with best available parser."""
        if self.tree_sitter:
            try:
                # Try tree-sitter parsing
                tree = self.tree_sitter._parser.parse(content.encode('utf-8'))
                return self._extract_symbols_from_tree(tree.root_node, content)
            except Exception as e:
                logger.debug(f"Tree-sitter failed, fallback to regex: {e}")
        
        # Fallback to regex
        return self.regex_parser.parse_file(content)
```

### Step 6: Update One Plugin as Test (10 minutes)

Update Python plugin to use SmartParser:

```python
# In mcp_server/plugins/python_plugin/plugin.py
# Change line 25 from:
self._ts = TreeSitterWrapper()
# To:
from ...utils.smart_parser import SmartParser
self._parser = SmartParser('python')

# Update indexFile method to use self._parser instead of self._ts
```

## Files to Modify Summary

1. **Create New Files**:
   - `mcp_server/utils/regex_parser.py` (base class)
   - `mcp_server/utils/regex_parsers/__init__.py`
   - `mcp_server/utils/regex_parsers/python_parser.py`
   - `mcp_server/utils/regex_parsers/javascript_parser.py`
   - `mcp_server/utils/smart_parser.py`

2. **Modify Existing**:
   - `mcp_server/utils/treesitter_wrapper.py` (add language support)
   - `mcp_server/plugins/python_plugin/plugin.py` (test implementation)

3. **Copy Patterns From**:
   - `mcp_server/plugins/go_plugin/plugin.py` (regex patterns)

## Testing Commands

```bash
# Test Python file indexing
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "index_file", "arguments": {"path": "mcp_server/plugins/python_plugin/plugin.py"}}}' | python -m mcp_server

# Test JavaScript file indexing  
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "index_file", "arguments": {"path": "mcp_server/tools/handlers/index_file.py"}}}' | python -m mcp_server
```

## Quick Win Implementation Order

1. **Hour 1**: 
   - Create regex parser base class
   - Create Python and JavaScript regex parsers
   - Update TreeSitterWrapper

2. **Hour 2**:
   - Create SmartParser
   - Update Python plugin
   - Test indexing

This approach reuses the proven Go plugin pattern and can be implemented quickly to get indexing working again!