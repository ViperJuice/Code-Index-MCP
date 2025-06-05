#!/usr/bin/env python3
"""Plugin generator script for creating new language plugins.

This script generates boilerplate code for new language plugins based on
templates and user specifications. It supports generating Tree-sitter-based,
regex-based, or hybrid plugins.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .plugin_template import SymbolType


class PluginType(Enum):
    """Types of plugins that can be generated."""
    TREE_SITTER = "tree-sitter"
    REGEX = "regex"
    HYBRID = "hybrid"
    SIMPLE = "simple"


@dataclass
class PluginSpec:
    """Specification for generating a plugin."""
    name: str
    language: str
    extensions: List[str]
    plugin_type: PluginType
    tree_sitter_support: bool = False
    description: str = ""
    author: str = ""
    version: str = "1.0.0"
    
    # Symbol patterns for regex-based plugins
    function_pattern: Optional[str] = None
    class_pattern: Optional[str] = None
    variable_pattern: Optional[str] = None
    import_pattern: Optional[str] = None
    
    # Tree-sitter node types
    function_nodes: List[str] = None
    class_nodes: List[str] = None
    variable_nodes: List[str] = None
    
    def __post_init__(self):
        if self.function_nodes is None:
            self.function_nodes = []
        if self.class_nodes is None:
            self.class_nodes = []
        if self.variable_nodes is None:
            self.variable_nodes = []


class PluginGenerator:
    """Generator for creating new language plugins."""
    
    def __init__(self, output_dir: Path):
        """Initialize the generator."""
        self.output_dir = Path(output_dir)
        self.templates_dir = Path(__file__).parent / "templates"
        
    def generate_plugin(self, spec: PluginSpec) -> Path:
        """Generate a plugin based on the specification."""
        plugin_dir = self.output_dir / f"{spec.name}_plugin"
        plugin_dir.mkdir(exist_ok=True)
        
        # Generate main plugin file
        plugin_file = plugin_dir / "plugin.py"
        self._generate_plugin_file(plugin_file, spec)
        
        # Generate __init__.py
        init_file = plugin_dir / "__init__.py"
        self._generate_init_file(init_file, spec)
        
        # Generate test file
        test_file = plugin_dir / f"test_{spec.name}_plugin.py"
        self._generate_test_file(test_file, spec)
        
        # Generate documentation
        doc_file = plugin_dir / "README.md"
        self._generate_documentation(doc_file, spec)
        
        # Generate test data if patterns are provided
        if spec.function_pattern or spec.class_pattern:
            test_data_dir = plugin_dir / "test_data"
            test_data_dir.mkdir(exist_ok=True)
            self._generate_test_data(test_data_dir, spec)
        
        # Generate configuration file
        config_file = plugin_dir / "plugin_config.json"
        self._generate_config_file(config_file, spec)
        
        print(f"Generated plugin at: {plugin_dir}")
        return plugin_dir
    
    def _generate_plugin_file(self, file_path: Path, spec: PluginSpec) -> None:
        """Generate the main plugin file."""
        if spec.plugin_type == PluginType.TREE_SITTER:
            template = self._get_tree_sitter_template(spec)
        elif spec.plugin_type == PluginType.REGEX:
            template = self._get_regex_template(spec)
        elif spec.plugin_type == PluginType.HYBRID:
            template = self._get_hybrid_template(spec)
        else:  # SIMPLE
            template = self._get_simple_template(spec)
        
        file_path.write_text(template)
    
    def _generate_init_file(self, file_path: Path, spec: PluginSpec) -> None:
        """Generate __init__.py file."""
        template = f'''"""
{spec.name.title()} plugin for {spec.language} language support.

{spec.description}
"""

from .plugin import Plugin

__version__ = "{spec.version}"
__author__ = "{spec.author}"
__description__ = "{spec.description}"

__all__ = ["Plugin"]
'''
        file_path.write_text(template)
    
    def _generate_test_file(self, file_path: Path, spec: PluginSpec) -> None:
        """Generate test file."""
        template = f'''"""Tests for {spec.name} plugin."""

import pytest
from pathlib import Path
from ..plugin import Plugin
from ...plugin_template import SymbolType


class Test{spec.name.title()}Plugin:
    """Test cases for {spec.name.title()} plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = Plugin()
    
    def test_supports_files(self):
        """Test file support detection."""
        # Test supported extensions
        {self._generate_extension_tests(spec.extensions)}
        
        # Test unsupported extensions
        assert not self.plugin.supports("test.txt")
        assert not self.plugin.supports("test.unknown")
    
    def test_parse_simple_code(self):
        """Test parsing simple code."""
        content = """{self._generate_test_content(spec)}"""
        
        result = self.plugin.indexFile("test{spec.extensions[0]}", content)
        assert result["language"] == "{spec.language}"
        assert len(result["symbols"]) > 0
    
    def test_symbol_extraction(self):
        """Test symbol extraction."""
        content = """{self._generate_test_content(spec)}"""
        
        result = self.plugin.indexFile("test{spec.extensions[0]}", content)
        symbols = result["symbols"]
        
        # Check for expected symbol types
        symbol_types = {{s["kind"] for s in symbols}}
        expected_types = {{{self._generate_expected_types(spec)}}}
        
        assert symbol_types.intersection(expected_types), f"Expected symbols of types {{expected_types}}, got {{symbol_types}}"
    
    def test_get_definition(self):
        """Test symbol definition lookup."""
        # This would need actual symbol data
        definition = self.plugin.getDefinition("test_symbol")
        # Add assertions based on expected behavior
    
    def test_search_functionality(self):
        """Test search functionality."""
        results = self.plugin.search("test_query")
        assert isinstance(results, list)
'''
        file_path.write_text(template)
    
    def _generate_documentation(self, file_path: Path, spec: PluginSpec) -> None:
        """Generate plugin documentation."""
        template = f'''# {spec.name.title()} Plugin

{spec.description}

## Features

- **Language**: {spec.language}
- **File Extensions**: {", ".join(spec.extensions)}
- **Plugin Type**: {spec.plugin_type.value}
- **Tree-sitter Support**: {"Yes" if spec.tree_sitter_support else "No"}

## Supported Symbol Types

{self._generate_symbol_documentation(spec)}

## Usage

```python
from mcp_server.plugins.{spec.name}_plugin import Plugin

# Initialize the plugin
plugin = Plugin()

# Check if a file is supported
if plugin.supports("example{spec.extensions[0]}"):
    # Index the file
    with open("example{spec.extensions[0]}", "r") as f:
        content = f.read()
    
    result = plugin.indexFile("example{spec.extensions[0]}", content)
    print(f"Found {{len(result['symbols'])}} symbols")
```

## Configuration

The plugin can be configured using the `plugin_config.json` file:

```json
{self._generate_config_example(spec)}
```

## Testing

Run tests with:
```bash
pytest test_{spec.name}_plugin.py
```

## Development

This plugin was generated using the MCP Server plugin generator.

### Extending the Plugin

To add new features:

1. **Add new symbol patterns** (for regex-based plugins)
2. **Add new node types** (for Tree-sitter-based plugins)
3. **Implement language-specific features**
4. **Add tests for new functionality**

### Performance Considerations

- The plugin uses caching to improve performance
- Large files are processed incrementally
- Tree-sitter parsing is preferred when available

## License

{spec.author} - {spec.version}
'''
        file_path.write_text(template)
    
    def _generate_test_data(self, test_data_dir: Path, spec: PluginSpec) -> None:
        """Generate test data files."""
        # Generate a sample file for testing
        sample_file = test_data_dir / f"sample{spec.extensions[0]}"
        sample_content = self._generate_sample_code(spec)
        sample_file.write_text(sample_content)
        
        # Generate a complex example
        complex_file = test_data_dir / f"complex{spec.extensions[0]}"
        complex_content = self._generate_complex_code(spec)
        complex_file.write_text(complex_content)
    
    def _generate_config_file(self, file_path: Path, spec: PluginSpec) -> None:
        """Generate plugin configuration file."""
        config = {
            "plugin": {
                "name": spec.name,
                "language": spec.language,
                "version": spec.version,
                "type": spec.plugin_type.value,
                "author": spec.author,
                "description": spec.description
            },
            "extensions": spec.extensions,
            "features": {
                "tree_sitter_support": spec.tree_sitter_support,
                "caching": True,
                "async_processing": True,
                "semantic_analysis": spec.plugin_type != PluginType.SIMPLE
            },
            "patterns": self._generate_pattern_config(spec),
            "node_types": self._generate_node_type_config(spec) if spec.tree_sitter_support else {},
            "performance": {
                "max_file_size": 10485760,  # 10MB
                "cache_ttl": 3600,
                "batch_size": 100
            }
        }
        
        file_path.write_text(json.dumps(config, indent=2))
    
    def _get_tree_sitter_template(self, spec: PluginSpec) -> str:
        """Generate Tree-sitter plugin template."""
        return f'''"""
{spec.name.title()} language plugin using Tree-sitter.

{spec.description}
"""

from typing import Dict, List
from ..tree_sitter_plugin_base import TreeSitterPluginBase
from ..plugin_template import SymbolType


class Plugin(TreeSitterPluginBase):
    """Tree-sitter based plugin for {spec.language}."""
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "{spec.language}"
    
    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return {spec.extensions}
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return regex patterns as fallback."""
        return {{
            {self._generate_symbol_patterns(spec)}
        }}
    
    def get_node_types(self) -> Dict[SymbolType, List[str]]:
        """Return Tree-sitter node types for symbol extraction."""
        return {{
            {self._generate_node_types(spec)}
        }}
    
    def get_query_patterns(self) -> Dict[str, str]:
        """Return Tree-sitter query patterns."""
        return {{
            "functions": """
                (function_definition
                  name: (identifier) @name) @function
            """,
            "classes": """
                (class_definition
                  name: (identifier) @name) @class
            """,
            "variables": """
                (variable_declaration
                  name: (identifier) @name) @variable
            """,
            # Add more patterns as needed
        }}
    
    def _extract_docstring_from_node(self, node, content: str):
        """Extract docstring from Tree-sitter node for {spec.language}."""
        # Language-specific docstring extraction
        # Override this method to implement {spec.language}-specific logic
        return super()._extract_docstring_from_node(node, content)
    
    def _extract_modifiers_from_node(self, node, content: str):
        """Extract modifiers from Tree-sitter node for {spec.language}."""
        # Language-specific modifier extraction
        # Override this method to implement {spec.language}-specific logic
        return super()._extract_modifiers_from_node(node, content)
'''
    
    def _get_regex_template(self, spec: PluginSpec) -> str:
        """Generate regex plugin template."""
        return f'''"""
{spec.name.title()} language plugin using regex patterns.

{spec.description}
"""

from typing import Dict, List
from ..regex_plugin_base import RegexPluginBase, RegexPattern
from ..plugin_template import SymbolType
import re


class Plugin(RegexPluginBase):
    """Regex-based plugin for {spec.language}."""
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "{spec.language}"
    
    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return {spec.extensions}
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return basic symbol patterns."""
        return {{
            {self._generate_symbol_patterns(spec)}
        }}
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        """Return detailed regex patterns for symbol extraction."""
        return [
            {self._generate_regex_patterns(spec)}
        ]
    
    def get_multi_line_patterns(self) -> Dict[SymbolType, RegexPattern]:
        """Return patterns for multi-line constructs."""
        patterns = super().get_multi_line_patterns()
        
        # Add {spec.language}-specific multi-line patterns
        {self._generate_multiline_patterns(spec)}
        
        return patterns
    
    def get_context_patterns(self) -> Dict[str, RegexPattern]:
        """Return patterns for extracting context information."""
        patterns = super().get_context_patterns()
        
        # Add {spec.language}-specific context patterns
        {self._generate_context_patterns(spec)}
        
        return patterns
'''
    
    def _get_hybrid_template(self, spec: PluginSpec) -> str:
        """Generate hybrid plugin template."""
        return f'''"""
{spec.name.title()} language plugin using hybrid approach.

{spec.description}
"""

from typing import Dict, List
from ..hybrid_plugin_base import HybridPluginBase
from ..regex_plugin_base import RegexPattern
from ..plugin_template import SymbolType


class Plugin(HybridPluginBase):
    """Hybrid plugin for {spec.language} with Tree-sitter and regex fallback."""
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "{spec.language}"
    
    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return {spec.extensions}
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return basic symbol patterns for fallback."""
        return {{
            {self._generate_symbol_patterns(spec)}
        }}
    
    def get_tree_sitter_node_types(self) -> Dict[SymbolType, List[str]]:
        """Return Tree-sitter node types for symbol extraction."""
        return {{
            {self._generate_node_types(spec)}
        }}
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        """Return regex patterns for fallback."""
        return [
            {self._generate_regex_patterns(spec)}
        ]
    
    def get_fallback_threshold(self) -> float:
        """Return threshold for deciding when to fallback to regex."""
        return 0.2  # Fallback if Tree-sitter finds less than 20% expected symbols
'''
    
    def _get_simple_template(self, spec: PluginSpec) -> str:
        """Generate simple plugin template."""
        return f'''"""
Simple {spec.name.title()} language plugin.

{spec.description}
"""

from typing import Dict, List
from ..plugin_template import LanguagePluginBase, SymbolType


class Plugin(LanguagePluginBase):
    """Simple plugin for {spec.language}."""
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "{spec.language}"
    
    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return {spec.extensions}
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return regex patterns for symbol extraction."""
        return {{
            {self._generate_symbol_patterns(spec)}
        }}
    
    def supports_tree_sitter(self) -> bool:
        """Simple plugins don't use Tree-sitter."""
        return False
'''
    
    def _generate_symbol_patterns(self, spec: PluginSpec) -> str:
        """Generate symbol pattern entries."""
        patterns = []
        
        if spec.function_pattern:
            patterns.append(f'SymbolType.FUNCTION: r"{spec.function_pattern}"')
        else:
            # Generate default patterns based on language
            default_patterns = self._get_default_patterns(spec.language)
            if 'function' in default_patterns:
                patterns.append(f'SymbolType.FUNCTION: r"{default_patterns["function"]}"')
        
        if spec.class_pattern:
            patterns.append(f'SymbolType.CLASS: r"{spec.class_pattern}"')
        elif 'class' in self._get_default_patterns(spec.language):
            default_patterns = self._get_default_patterns(spec.language)
            patterns.append(f'SymbolType.CLASS: r"{default_patterns["class"]}"')
        
        if spec.variable_pattern:
            patterns.append(f'SymbolType.VARIABLE: r"{spec.variable_pattern}"')
        elif 'variable' in self._get_default_patterns(spec.language):
            default_patterns = self._get_default_patterns(spec.language)
            patterns.append(f'SymbolType.VARIABLE: r"{default_patterns["variable"]}"')
        
        if spec.import_pattern:
            patterns.append(f'SymbolType.IMPORT: r"{spec.import_pattern}"')
        elif 'import' in self._get_default_patterns(spec.language):
            default_patterns = self._get_default_patterns(spec.language)
            patterns.append(f'SymbolType.IMPORT: r"{default_patterns["import"]}"')
        
        return ",\\n            ".join(patterns) if patterns else ""
    
    def _generate_node_types(self, spec: PluginSpec) -> str:
        """Generate node type entries."""
        patterns = []
        
        if spec.function_nodes:
            patterns.append(f'SymbolType.FUNCTION: {spec.function_nodes}')
        else:
            default_nodes = self._get_default_node_types(spec.language)
            if 'function' in default_nodes:
                patterns.append(f'SymbolType.FUNCTION: {default_nodes["function"]}')
        
        if spec.class_nodes:
            patterns.append(f'SymbolType.CLASS: {spec.class_nodes}')
        elif 'class' in self._get_default_node_types(spec.language):
            default_nodes = self._get_default_node_types(spec.language)
            patterns.append(f'SymbolType.CLASS: {default_nodes["class"]}')
        
        if spec.variable_nodes:
            patterns.append(f'SymbolType.VARIABLE: {spec.variable_nodes}')
        elif 'variable' in self._get_default_node_types(spec.language):
            default_nodes = self._get_default_node_types(spec.language)
            patterns.append(f'SymbolType.VARIABLE: {default_nodes["variable"]}')
        
        return ",\\n            ".join(patterns) if patterns else ""
    
    def _generate_regex_patterns(self, spec: PluginSpec) -> str:
        """Generate RegexPattern objects."""
        patterns = []
        
        if spec.function_pattern:
            patterns.append(f'''RegexPattern(
                pattern=r"{spec.function_pattern}",
                symbol_type=SymbolType.FUNCTION,
                name_group=1
            )''')
        
        if spec.class_pattern:
            patterns.append(f'''RegexPattern(
                pattern=r"{spec.class_pattern}",
                symbol_type=SymbolType.CLASS,
                name_group=1
            )''')
        
        if spec.variable_pattern:
            patterns.append(f'''RegexPattern(
                pattern=r"{spec.variable_pattern}",
                symbol_type=SymbolType.VARIABLE,
                name_group=1
            )''')
        
        return ",\\n            ".join(patterns) if patterns else ""
    
    def _generate_multiline_patterns(self, spec: PluginSpec) -> str:
        """Generate multi-line pattern configurations."""
        # This would be language-specific
        return "# Add language-specific multi-line patterns here"
    
    def _generate_context_patterns(self, spec: PluginSpec) -> str:
        """Generate context pattern configurations."""
        # This would be language-specific
        return "# Add language-specific context patterns here"
    
    def _get_default_patterns(self, language: str) -> Dict[str, str]:
        """Get default regex patterns for a language."""
        patterns = {
            "python": {
                "function": r"^\\s*def\\s+(\\w+)",
                "class": r"^\\s*class\\s+(\\w+)",
                "variable": r"^\\s*(\\w+)\\s*=",
                "import": r"^\\s*(?:import\\s+(\\w+)|from\\s+(\\w+)\\s+import)"
            },
            "javascript": {
                "function": r"^\\s*function\\s+(\\w+)",
                "class": r"^\\s*class\\s+(\\w+)",
                "variable": r"^\\s*(?:var|let|const)\\s+(\\w+)",
                "import": r"^\\s*import\\s+.*?from\\s+['\"]([^'\"]+)['\"]"
            },
            "java": {
                "function": r"^\\s*(?:public|private|protected)?\\s*(?:static)?\\s*\\w+\\s+(\\w+)\\s*\\(",
                "class": r"^\\s*(?:public|private|protected)?\\s*class\\s+(\\w+)",
                "variable": r"^\\s*(?:public|private|protected)?\\s*(?:static)?\\s*\\w+\\s+(\\w+)\\s*[=;]",
                "import": r"^\\s*import\\s+([^;]+);"
            },
            "cpp": {
                "function": r"^\\s*(?:\\w+\\s+)*\\w+\\s+(\\w+)\\s*\\(",
                "class": r"^\\s*class\\s+(\\w+)",
                "variable": r"^\\s*(?:\\w+\\s+)*\\w+\\s+(\\w+)\\s*[=;]",
                "import": r"^\\s*#include\\s*[<\"]([^>\"]+)[>\"]"
            },
            "go": {
                "function": r"^\\s*func\\s+(\\w+)",
                "class": r"^\\s*type\\s+(\\w+)\\s+struct",
                "variable": r"^\\s*var\\s+(\\w+)",
                "import": r"^\\s*import\\s+[\"']([^\"']+)[\"']"
            },
            "rust": {
                "function": r"^\\s*fn\\s+(\\w+)",
                "class": r"^\\s*(?:struct|enum)\\s+(\\w+)",
                "variable": r"^\\s*let\\s+(?:mut\\s+)?(\\w+)",
                "import": r"^\\s*use\\s+([^;]+);"
            }
        }
        
        return patterns.get(language, {})
    
    def _get_default_node_types(self, language: str) -> Dict[str, List[str]]:
        """Get default Tree-sitter node types for a language."""
        node_types = {
            "python": {
                "function": ["function_definition", "async_function_definition"],
                "class": ["class_definition"],
                "variable": ["assignment", "augmented_assignment"]
            },
            "javascript": {
                "function": ["function_declaration", "function_expression", "arrow_function"],
                "class": ["class_declaration"],
                "variable": ["variable_declaration", "lexical_declaration"]
            },
            "java": {
                "function": ["method_declaration", "constructor_declaration"],
                "class": ["class_declaration", "interface_declaration"],
                "variable": ["variable_declarator", "field_declaration"]
            },
            "cpp": {
                "function": ["function_definition", "function_declarator"],
                "class": ["class_specifier", "struct_specifier"],
                "variable": ["declaration", "init_declarator"]
            },
            "go": {
                "function": ["function_declaration", "method_declaration"],
                "class": ["type_declaration"],
                "variable": ["var_declaration", "short_var_declaration"]
            },
            "rust": {
                "function": ["function_item", "function_signature_item"],
                "class": ["struct_item", "enum_item"],
                "variable": ["let_declaration"]
            }
        }
        
        return node_types.get(language, {})
    
    def _generate_extension_tests(self, extensions: List[str]) -> str:
        """Generate test assertions for extensions."""
        tests = []
        for ext in extensions:
            tests.append(f'assert self.plugin.supports("test{ext}")')
        return "\\n        ".join(tests)
    
    def _generate_test_content(self, spec: PluginSpec) -> str:
        """Generate test content for the language."""
        test_contents = {
            "python": '''def hello_world():
    return "Hello, World!"

class TestClass:
    def __init__(self):
        self.value = 42''',
            "javascript": '''function helloWorld() {
    return "Hello, World!";
}

class TestClass {
    constructor() {
        this.value = 42;
    }
}''',
            "java": '''public class TestClass {
    private int value = 42;
    
    public String helloWorld() {
        return "Hello, World!";
    }
}''',
            "cpp": '''class TestClass {
private:
    int value = 42;
    
public:
    std::string helloWorld() {
        return "Hello, World!";
    }
};''',
            "go": '''type TestStruct struct {
    Value int
}

func helloWorld() string {
    return "Hello, World!"
}''',
            "rust": '''struct TestStruct {
    value: i32,
}

fn hello_world() -> String {
    "Hello, World!".to_string()
}'''
        }
        
        return test_contents.get(spec.language, "// Test content for " + spec.language)
    
    def _generate_expected_types(self, spec: PluginSpec) -> str:
        """Generate expected symbol types for tests."""
        types = []
        if spec.function_pattern or spec.function_nodes:
            types.append('"function"')
        if spec.class_pattern or spec.class_nodes:
            types.append('"class"')
        if spec.variable_pattern or spec.variable_nodes:
            types.append('"variable"')
        
        # Add default types based on language
        if not types:
            if spec.language in ["python", "javascript", "java", "cpp", "go", "rust"]:
                types = ['"function"', '"class"']
        
        return ", ".join(types) if types else '"unknown"'
    
    def _generate_symbol_documentation(self, spec: PluginSpec) -> str:
        """Generate symbol documentation."""
        symbols = []
        if spec.function_pattern or spec.function_nodes:
            symbols.append("- **Functions**: Method and function definitions")
        if spec.class_pattern or spec.class_nodes:
            symbols.append("- **Classes**: Class and interface definitions")
        if spec.variable_pattern or spec.variable_nodes:
            symbols.append("- **Variables**: Variable declarations")
        if spec.import_pattern:
            symbols.append("- **Imports**: Import statements")
        
        return "\\n".join(symbols) if symbols else "- Basic symbol extraction"
    
    def _generate_config_example(self, spec: PluginSpec) -> str:
        """Generate configuration example."""
        config = {
            "enabled": True,
            "max_file_size": 10485760,
            "cache_ttl": 3600,
            "strict_mode": False
        }
        
        return json.dumps(config, indent=2)
    
    def _generate_pattern_config(self, spec: PluginSpec) -> Dict[str, str]:
        """Generate pattern configuration."""
        patterns = {}
        if spec.function_pattern:
            patterns["function"] = spec.function_pattern
        if spec.class_pattern:
            patterns["class"] = spec.class_pattern
        if spec.variable_pattern:
            patterns["variable"] = spec.variable_pattern
        if spec.import_pattern:
            patterns["import"] = spec.import_pattern
        
        return patterns
    
    def _generate_node_type_config(self, spec: PluginSpec) -> Dict[str, List[str]]:
        """Generate node type configuration."""
        node_types = {}
        if spec.function_nodes:
            node_types["function"] = spec.function_nodes
        if spec.class_nodes:
            node_types["class"] = spec.class_nodes
        if spec.variable_nodes:
            node_types["variable"] = spec.variable_nodes
        
        return node_types
    
    def _generate_sample_code(self, spec: PluginSpec) -> str:
        """Generate sample code for testing."""
        return self._generate_test_content(spec)
    
    def _generate_complex_code(self, spec: PluginSpec) -> str:
        """Generate complex code example."""
        complex_examples = {
            "python": '''"""
Complex Python example with multiple constructs.
"""
import os
import sys
from typing import List, Dict, Optional

class DataProcessor:
    """Main data processing class."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data: Optional[List[Dict]] = None
    
    async def process_data(self, input_data: List[Dict]) -> List[Dict]:
        """Process input data asynchronously."""
        results = []
        for item in input_data:
            processed = await self._process_item(item)
            results.append(processed)
        return results
    
    def _process_item(self, item: Dict) -> Dict:
        """Process a single data item."""
        return {**item, "processed": True}

@dataclass
class Config:
    """Configuration dataclass."""
    max_items: int = 1000
    timeout: float = 30.0
    
def main():
    """Main entry point."""
    processor = DataProcessor({"debug": True})
    # Process data...
''',
            "javascript": '''/**
 * Complex JavaScript example with multiple constructs.
 */

import { EventEmitter } from 'events';
import fs from 'fs/promises';

class DataProcessor extends EventEmitter {
    /**
     * Main data processing class.
     */
    constructor(config = {}) {
        super();
        this.config = config;
        this.data = null;
    }
    
    async processData(inputData) {
        /**
         * Process input data asynchronously.
         */
        const results = [];
        for (const item of inputData) {
            const processed = await this._processItem(item);
            results.push(processed);
            this.emit('processed', processed);
        }
        return results;
    }
    
    _processItem(item) {
        /**
         * Process a single data item.
         */
        return { ...item, processed: true };
    }
}

const config = {
    maxItems: 1000,
    timeout: 30000
};

export default DataProcessor;
'''
        }
        
        return complex_examples.get(spec.language, f"// Complex {spec.language} example")


def create_plugin_from_cli():
    """Create plugin from command line arguments."""
    parser = argparse.ArgumentParser(description="Generate a new language plugin")
    
    parser.add_argument("name", help="Plugin name (e.g., 'swift')")
    parser.add_argument("language", help="Programming language (e.g., 'swift')")
    parser.add_argument("--extensions", nargs="+", required=True, 
                       help="File extensions (e.g., '.swift' '.playground')")
    parser.add_argument("--type", choices=[t.value for t in PluginType], 
                       default=PluginType.HYBRID.value,
                       help="Plugin type")
    parser.add_argument("--output-dir", default=".", 
                       help="Output directory for generated plugin")
    parser.add_argument("--description", default="", 
                       help="Plugin description")
    parser.add_argument("--author", default="", 
                       help="Plugin author")
    parser.add_argument("--version", default="1.0.0", 
                       help="Plugin version")
    
    # Pattern arguments
    parser.add_argument("--function-pattern", 
                       help="Regex pattern for functions")
    parser.add_argument("--class-pattern", 
                       help="Regex pattern for classes")
    parser.add_argument("--variable-pattern", 
                       help="Regex pattern for variables")
    parser.add_argument("--import-pattern", 
                       help="Regex pattern for imports")
    
    # Tree-sitter node arguments
    parser.add_argument("--function-nodes", nargs="+", 
                       help="Tree-sitter node types for functions")
    parser.add_argument("--class-nodes", nargs="+", 
                       help="Tree-sitter node types for classes")
    parser.add_argument("--variable-nodes", nargs="+", 
                       help="Tree-sitter node types for variables")
    
    args = parser.parse_args()
    
    spec = PluginSpec(
        name=args.name,
        language=args.language,
        extensions=args.extensions,
        plugin_type=PluginType(args.type),
        tree_sitter_support=args.type in [PluginType.TREE_SITTER.value, PluginType.HYBRID.value],
        description=args.description or f"Plugin for {args.language} language support",
        author=args.author,
        version=args.version,
        function_pattern=args.function_pattern,
        class_pattern=args.class_pattern,
        variable_pattern=args.variable_pattern,
        import_pattern=args.import_pattern,
        function_nodes=args.function_nodes or [],
        class_nodes=args.class_nodes or [],
        variable_nodes=args.variable_nodes or []
    )
    
    generator = PluginGenerator(Path(args.output_dir))
    plugin_dir = generator.generate_plugin(spec)
    
    print(f"\\nPlugin generated successfully at: {plugin_dir}")
    print("\\nNext steps:")
    print("1. Review the generated code")
    print("2. Customize patterns and node types for your language")
    print("3. Add language-specific features")
    print("4. Run tests to verify functionality")
    print("5. Add the plugin to your MCP server configuration")


if __name__ == "__main__":
    create_plugin_from_cli()