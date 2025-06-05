#!/usr/bin/env python3
"""
Language Plugin Generator for Code-Index-MCP

This tool generates a complete plugin structure for adding support for a new programming language.
It creates all necessary files, boilerplate code, and integrates with the existing plugin system.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import textwrap
from datetime import datetime


class PluginGenerator:
    """Generates plugin structure and files for a new language."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.mcp_server_path = base_path / "mcp_server"
        self.plugins_path = self.mcp_server_path / "plugins"
        self.tests_path = base_path / "tests"
        
    def prompt_user(self, question: str, default: str = "") -> str:
        """Prompt user for input with optional default value."""
        if default:
            prompt = f"{question} [{default}]: "
        else:
            prompt = f"{question}: "
        
        answer = input(prompt).strip()
        return answer if answer else default
    
    def prompt_yes_no(self, question: str, default: bool = True) -> bool:
        """Prompt user for yes/no answer."""
        default_str = "Y" if default else "N"
        prompt = f"{question} [{default_str}/{'n' if default else 'y'}]: "
        
        answer = input(prompt).strip().lower()
        if not answer:
            return default
        return answer in ['y', 'yes', 'true', '1']
    
    def prompt_list(self, question: str, example: str = "") -> List[str]:
        """Prompt user for comma-separated list."""
        if example:
            prompt = f"{question} (comma-separated, e.g., {example}): "
        else:
            prompt = f"{question} (comma-separated): "
        
        answer = input(prompt).strip()
        if not answer:
            return []
        
        return [item.strip() for item in answer.split(',') if item.strip()]
    
    def gather_language_info(self) -> Dict:
        """Interactively gather information about the language."""
        print("\n=== Language Plugin Generator ===\n")
        
        # Basic information
        name = self.prompt_user("Language name (e.g., Python, JavaScript)")
        if not name:
            print("Language name is required!")
            sys.exit(1)
            
        display_name = self.prompt_user("Display name", name)
        plugin_name = name.lower().replace(" ", "_").replace("-", "_") + "_plugin"
        
        extensions = self.prompt_list(
            "File extensions", 
            ".py, .pyw" if "python" in name.lower() else ".js, .jsx"
        )
        
        # Tree-sitter support
        has_treesitter = self.prompt_yes_no("Does this language have Tree-sitter support?")
        treesitter_language = ""
        if has_treesitter:
            treesitter_language = self.prompt_user(
                "Tree-sitter language name", 
                name.lower().replace(" ", "_")
            )
        
        # Symbol types
        print("\nCommon symbol types for programming languages:")
        print("- class, function, method, variable, constant")
        print("- interface, enum, struct, type, trait")
        print("- module, namespace, package")
        
        symbol_types = self.prompt_list(
            "Symbol types for this language",
            "class, function, method, variable"
        )
        
        # Framework detection
        has_frameworks = self.prompt_yes_no("Does this language have frameworks to detect?")
        frameworks = []
        if has_frameworks:
            frameworks = self.prompt_list(
                "Framework names",
                "Django, Flask" if "python" in name.lower() else "React, Vue"
            )
        
        # Special considerations
        print("\nSpecial parsing considerations:")
        multiline_strings = self.prompt_yes_no("Supports multiline strings?")
        decorators = self.prompt_yes_no("Has decorators/annotations?")
        type_annotations = self.prompt_yes_no("Supports type annotations?")
        async_support = self.prompt_yes_no("Has async/await support?")
        
        # Comment styles
        single_line_comment = self.prompt_user("Single-line comment prefix", "//")
        multi_line_comment_start = self.prompt_user("Multi-line comment start", "/*")
        multi_line_comment_end = self.prompt_user("Multi-line comment end", "*/")
        
        return {
            "name": name,
            "display_name": display_name,
            "plugin_name": plugin_name,
            "extensions": extensions,
            "has_treesitter": has_treesitter,
            "treesitter_language": treesitter_language,
            "symbol_types": symbol_types,
            "frameworks": frameworks,
            "features": {
                "multiline_strings": multiline_strings,
                "decorators": decorators,
                "type_annotations": type_annotations,
                "async_support": async_support
            },
            "comments": {
                "single": single_line_comment,
                "multi_start": multi_line_comment_start,
                "multi_end": multi_line_comment_end
            }
        }
    
    def generate_plugin_py(self, info: Dict) -> str:
        """Generate the main plugin.py file."""
        template = '''"""
{display_name} Language Plugin for Code-Index-MCP

Provides language-specific parsing and analysis for {display_name} files.
Generated on: {date}
"""

from typing import Dict, List, Optional, Set, Tuple
import logging
from pathlib import Path

from mcp_server.plugin_base import BasePlugin, PluginCapabilities
from mcp_server.utils.smart_parser import SmartParser

logger = logging.getLogger(__name__)


class {class_name}(BasePlugin):
    """Language plugin for {display_name} files."""
    
    language = "{language}"
    file_extensions = {extensions}
    
    def __init__(self):
        """Initialize the {display_name} plugin."""
        super().__init__()
        self.parser = SmartParser(
            language="{language}",
            fallback_to_regex=True
        )
        
    def get_capabilities(self) -> PluginCapabilities:
        """Return the capabilities of this plugin."""
        return PluginCapabilities(
            language=self.language,
            file_extensions=self.file_extensions,
            can_parse_imports={has_imports},
            can_extract_symbols=True,
            can_detect_frameworks={has_frameworks},
            supports_treesitter={has_treesitter}
        )
    
    def parse_file(self, file_path: str, content: str) -> Dict:
        """Parse a {display_name} file and extract relevant information."""
        try:
            # Use smart parser for symbol extraction
            symbols = self.parser.extract_symbols(content, file_path)
            
            # Extract imports
            imports = self._extract_imports(content) if {has_imports} else []
            
            # Detect frameworks
            frameworks = self._detect_frameworks(content, file_path) if {has_frameworks} else []
            
            return {{
                "symbols": symbols,
                "imports": imports,
                "frameworks": frameworks,
                "language": self.language,
                "file_path": file_path
            }}
            
        except Exception as e:
            logger.error(f"Error parsing {{file_path}}: {{e}}")
            return self._create_empty_result(file_path)
    
    def _extract_imports(self, content: str) -> List[Dict[str, str]]:
        """Extract import statements from {display_name} code."""
        imports = []
        
        # TODO: Implement language-specific import extraction
        # This is a placeholder - replace with actual logic
        lines = content.split('\\n')
        for line in lines:
            line = line.strip()
            # Add language-specific import detection here
            pass
            
        return imports
    
    def _detect_frameworks(self, content: str, file_path: str) -> List[str]:
        """Detect frameworks used in the {display_name} code."""
        detected = []
        frameworks = {frameworks}
        
        for framework in frameworks:
            # TODO: Add framework-specific detection logic
            if framework.lower() in content.lower():
                detected.append(framework)
        
        return detected
    
    def _create_empty_result(self, file_path: str) -> Dict:
        """Create an empty result structure."""
        return {{
            "symbols": [],
            "imports": [],
            "frameworks": [],
            "language": self.language,
            "file_path": file_path
        }}
    
    def validate_syntax(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validate {display_name} syntax."""
        try:
            # Use smart parser's validation if available
            return self.parser.validate_syntax(content)
        except Exception as e:
            return False, str(e)
    
    def get_symbol_types(self) -> List[str]:
        """Return the types of symbols this plugin can extract."""
        return {symbol_types}


# Plugin registration
plugin = {class_name}
'''
        
        class_name = info["name"].replace(" ", "").replace("-", "") + "Plugin"
        
        return template.format(
            display_name=info["display_name"],
            date=datetime.now().strftime("%Y-%m-%d"),
            class_name=class_name,
            language=info["name"].lower(),
            extensions=repr(info["extensions"]),
            has_imports="True",  # Most languages have imports
            has_frameworks=str(bool(info["frameworks"])),
            has_treesitter=str(info["has_treesitter"]),
            frameworks=repr(info["frameworks"]),
            symbol_types=repr(info["symbol_types"])
        )
    
    def generate_init_py(self, info: Dict) -> str:
        """Generate __init__.py file."""
        return f'''"""
{info["display_name"]} Language Plugin

Generated on: {datetime.now().strftime("%Y-%m-%d")}
"""

from .plugin import plugin

__all__ = ["plugin"]
'''
    
    def generate_agents_md(self, info: Dict) -> str:
        """Generate AGENTS.md documentation."""
        return f'''# {info["display_name"]} Plugin Agent Instructions

## Overview
This plugin provides support for {info["display_name"]} language files with extensions: {", ".join(info["extensions"])}

## Capabilities
- Symbol extraction: {", ".join(info["symbol_types"])}
- Tree-sitter support: {info["has_treesitter"]}
- Framework detection: {", ".join(info["frameworks"]) if info["frameworks"] else "None"}

## Special Features
- Multiline strings: {info["features"]["multiline_strings"]}
- Decorators/Annotations: {info["features"]["decorators"]}
- Type annotations: {info["features"]["type_annotations"]}
- Async support: {info["features"]["async_support"]}

## Usage Instructions
When working with {info["display_name"]} files:
1. Use appropriate symbol extraction for {", ".join(info["symbol_types"])}
2. Handle comment styles: {info["comments"]["single"]} for single-line, {info["comments"]["multi_start"]}...{info["comments"]["multi_end"]} for multi-line
3. Consider framework-specific patterns when detected

## Testing
Run tests with: `pytest tests/test_{info["plugin_name"]}.py`
'''
    
    def generate_claude_md(self, info: Dict) -> str:
        """Generate CLAUDE.md documentation."""
        return f'''# {info["display_name"]} Plugin Instructions

This file contains instructions for Claude when working with the {info["display_name"]} plugin.

## Plugin Overview
- **Language**: {info["display_name"]}
- **Extensions**: {", ".join(info["extensions"])}
- **Plugin Directory**: `mcp_server/plugins/{info["plugin_name"]}/`

## Implementation Notes
1. The plugin uses SmartParser for symbol extraction
2. Tree-sitter support: {info["has_treesitter"]}
3. Supports these symbol types: {", ".join(info["symbol_types"])}

## Do Not Modify
This file should not be modified directly. Updates should be added to AGENTS.md.
'''
    
    def generate_test_data(self, info: Dict) -> Dict[str, str]:
        """Generate sample test data files."""
        ext = info["extensions"][0] if info["extensions"] else ".txt"
        
        # Generate sample code based on language features
        sample_code = f'''{info["comments"]["single"]} Sample {info["display_name"]} file for testing
{info["comments"]["multi_start"]}
This file demonstrates various language features
for the {info["display_name"]} plugin.
{info["comments"]["multi_end"]}

'''
        
        # Add class example if supported
        if "class" in info["symbol_types"]:
            sample_code += f'''class SampleClass {{
    {info["comments"]["single"]} Constructor
    constructor() {{
        this.name = "{info["display_name"]} Sample";
    }}
    
    {info["comments"]["single"]} Sample method
    sampleMethod() {{
        return "Hello from {info["display_name"]}";
    }}
}}

'''
        
        # Add function example if supported
        if "function" in info["symbol_types"]:
            sample_code += f'''function sampleFunction(param1, param2) {{
    {info["comments"]["single"]} Sample function implementation
    return param1 + param2;
}}

'''
        
        # Add async example if supported
        if info["features"]["async_support"]:
            sample_code += f'''async function asyncExample() {{
    {info["comments"]["single"]} Async function example
    const result = await someAsyncOperation();
    return result;
}}
'''
        
        return {
            f"sample{ext}": sample_code,
            f"test_file{ext}": f"{info['comments']['single']} Test file for {info['display_name']} plugin\\n"
        }
    
    def generate_test_file(self, info: Dict) -> str:
        """Generate pytest test file."""
        return f'''"""
Tests for {info["display_name"]} Language Plugin

Generated on: {datetime.now().strftime("%Y-%m-%d")}
"""

import pytest
from pathlib import Path

from mcp_server.plugins.{info["plugin_name"]}.plugin import plugin


class Test{info["name"].replace(" ", "")}Plugin:
    """Test cases for {info["display_name"]} plugin."""
    
    @pytest.fixture
    def sample_code(self):
        """Provide sample {info["display_name"]} code for testing."""
        return """
{info["comments"]["single"]} Sample code for testing
class TestClass {{
    constructor() {{
        this.value = 42;
    }}
    
    testMethod() {{
        return this.value;
    }}
}}

function testFunction(x, y) {{
    return x + y;
}}
"""
    
    def test_plugin_initialization(self):
        """Test plugin can be initialized."""
        assert plugin.language == "{info["name"].lower()}"
        assert plugin.file_extensions == {info["extensions"]}
    
    def test_get_capabilities(self):
        """Test plugin capabilities."""
        caps = plugin.get_capabilities()
        assert caps.language == "{info["name"].lower()}"
        assert caps.file_extensions == {info["extensions"]}
        assert caps.can_extract_symbols is True
        assert caps.supports_treesitter is {info["has_treesitter"]}
    
    def test_parse_file(self, sample_code, tmp_path):
        """Test parsing a {info["display_name"]} file."""
        ext = "{info["extensions"][0] if info["extensions"] else '.txt'}"
        test_file = tmp_path / f"test{{ext}}"
        test_file.write_text(sample_code)
        
        result = plugin.parse_file(str(test_file), sample_code)
        
        assert result["language"] == "{info["name"].lower()}"
        assert result["file_path"] == str(test_file)
        assert "symbols" in result
        assert "imports" in result
        assert "frameworks" in result
    
    def test_symbol_extraction(self, sample_code):
        """Test symbol extraction from {info["display_name"]} code."""
        result = plugin.parse_file("test.js", sample_code)
        symbols = result["symbols"]
        
        # Check that some symbols were extracted
        assert len(symbols) > 0
        
        # Verify symbol types
        symbol_types = {{s["type"] for s in symbols}}
        expected_types = set({info["symbol_types"]})
        assert len(symbol_types.intersection(expected_types)) > 0
    
    @pytest.mark.skipif(not {info["has_frameworks"]}, reason="No frameworks to detect")
    def test_framework_detection(self):
        """Test framework detection."""
        frameworks = {info["frameworks"]}
        for framework in frameworks:
            code = f'{info["comments"]["single"]} Using {{framework}}\\nimport {{framework}};'
            result = plugin.parse_file("test.js", code)
            assert framework in result["frameworks"]
    
    def test_validate_syntax(self, sample_code):
        """Test syntax validation."""
        valid, error = plugin.validate_syntax(sample_code)
        assert valid is True or valid is False  # Should return boolean
        if not valid:
            assert error is not None  # Should provide error message
    
    def test_empty_file(self):
        """Test parsing empty file."""
        result = plugin.parse_file("empty.js", "")
        assert result["symbols"] == []
        assert result["language"] == "{info["name"].lower()}"
    
    def test_get_symbol_types(self):
        """Test getting supported symbol types."""
        types = plugin.get_symbol_types()
        assert isinstance(types, list)
        assert len(types) > 0
        for symbol_type in {info["symbol_types"]}:
            assert symbol_type in types
'''
    
    def generate_regex_patterns(self, info: Dict) -> str:
        """Generate regex patterns file."""
        patterns = f'''"""
Regex patterns for {info["display_name"]} language parsing.

Generated on: {datetime.now().strftime("%Y-%m-%d")}
"""

import re
from typing import Dict, Pattern

# Comment patterns
SINGLE_LINE_COMMENT = re.compile(r'{re.escape(info["comments"]["single"])}.*$', re.MULTILINE)
MULTI_LINE_COMMENT = re.compile(
    r'{re.escape(info["comments"]["multi_start"])}.*?{re.escape(info["comments"]["multi_end"])}', 
    re.DOTALL
)

# Symbol patterns
PATTERNS: Dict[str, Pattern] = {{
'''
        
        # Add patterns based on symbol types
        if "class" in info["symbol_types"]:
            patterns += '''    "class": re.compile(r'class\\s+(\\w+)'),
'''
        
        if "function" in info["symbol_types"]:
            patterns += '''    "function": re.compile(r'function\\s+(\\w+)\\s*\\('),
'''
        
        if "method" in info["symbol_types"]:
            patterns += '''    "method": re.compile(r'(\\w+)\\s*\\(.*?\\)\\s*{'),
'''
        
        if "variable" in info["symbol_types"]:
            patterns += '''    "variable": re.compile(r'(?:var|let|const)\\s+(\\w+)'),
'''
        
        patterns += '''}

# Import patterns
IMPORT_PATTERNS = [
    re.compile(r'import\\s+.*?\\s+from\\s+["\'](.+?)["\']'),
    re.compile(r'import\\s+["\'](.+?)["\']'),
    re.compile(r'require\\(["\'](.+?)["\']\\)'),
]

# Framework patterns
FRAMEWORK_PATTERNS = {
'''
        
        for framework in info["frameworks"]:
            patterns += f'''    "{framework}": re.compile(r'{framework.lower()}|@{framework.lower()}', re.IGNORECASE),
'''
        
        patterns += '''}
'''
        
        return patterns
    
    def create_plugin_structure(self, info: Dict) -> None:
        """Create the complete plugin directory structure."""
        plugin_dir = self.plugins_path / info["plugin_name"]
        test_data_dir = plugin_dir / "test_data"
        
        # Create directories
        plugin_dir.mkdir(parents=True, exist_ok=True)
        test_data_dir.mkdir(exist_ok=True)
        
        # Generate and write files
        files_to_create = {
            plugin_dir / "__init__.py": self.generate_init_py(info),
            plugin_dir / "plugin.py": self.generate_plugin_py(info),
            plugin_dir / "AGENTS.md": self.generate_agents_md(info),
            plugin_dir / "CLAUDE.md": self.generate_claude_md(info),
            plugin_dir / "patterns.py": self.generate_regex_patterns(info),
        }
        
        # Add test data files
        test_data = self.generate_test_data(info)
        for filename, content in test_data.items():
            files_to_create[test_data_dir / filename] = content
        
        # Write all files
        for file_path, content in files_to_create.items():
            file_path.write_text(content)
            print(f"Created: {file_path}")
        
        # Create test file
        test_file = self.tests_path / f"test_{info['plugin_name']}.py"
        test_file.write_text(self.generate_test_file(info))
        print(f"Created: {test_file}")
    
    def update_plugin_registry(self, info: Dict) -> None:
        """Update the plugin registry to include the new plugin."""
        registry_file = self.plugins_path / "__init__.py"
        
        if not registry_file.exists():
            print(f"Warning: Plugin registry not found at {registry_file}")
            return
        
        # Read current content
        content = registry_file.read_text()
        
        # Check if already registered
        if info["plugin_name"] in content:
            print(f"Plugin {info['plugin_name']} already registered")
            return
        
        # Add import statement
        import_line = f"from .{info['plugin_name']} import plugin as {info['plugin_name'][:-7]}_plugin"
        
        # Find the right place to insert
        lines = content.split('\\n')
        import_index = -1
        for i, line in enumerate(lines):
            if line.startswith("from .") and "_plugin import" in line:
                import_index = i
        
        if import_index >= 0:
            lines.insert(import_index + 1, import_line)
        else:
            # Add after other imports
            for i, line in enumerate(lines):
                if line.strip() == "" and i > 0:
                    lines.insert(i, import_line)
                    break
        
        # Update __all__ if present
        all_updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith("__all__"):
                # Parse and update __all__
                if "[" in line and "]" in line:
                    # Single line __all__
                    before = line[:line.index("[") + 1]
                    after = line[line.index("]"):]
                    items = line[line.index("[") + 1:line.index("]")].split(",")
                    items = [item.strip() for item in items if item.strip()]
                    items.append(f'"{info["plugin_name"][:-7]}_plugin"')
                    lines[i] = before + ", ".join(items) + after
                    all_updated = True
                break
        
        # Write back
        registry_file.write_text('\n'.join(lines))
        print(f"Updated plugin registry: {registry_file}")
    
    def generate_plugin(self, info: Dict) -> None:
        """Generate the complete plugin."""
        print(f"\nGenerating {info['display_name']} plugin...")
        
        # Create plugin structure
        self.create_plugin_structure(info)
        
        # Update registry
        self.update_plugin_registry(info)
        
        print(f"\n✅ Successfully generated {info['display_name']} plugin!")
        print(f"\nPlugin location: {self.plugins_path / info['plugin_name']}")
        test_file_name = f"test_{info['plugin_name']}.py"
        print(f"Test file: {self.tests_path / test_file_name}")
        print("\nNext steps:")
        print(f"1. Review and customize the generated plugin at mcp_server/plugins/{info['plugin_name']}/plugin.py")
        print("2. Implement language-specific import extraction in _extract_imports()")
        print("3. Add framework detection logic in _detect_frameworks()")
        print(f"4. Run tests: pytest tests/{test_file_name}")
        print("5. Update documentation as needed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate a new language plugin for Code-Index-MCP"
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Base path of the Code-Index-MCP project"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (not implemented)"
    )
    
    args = parser.parse_args()
    
    if args.non_interactive:
        print("Non-interactive mode not yet implemented")
        sys.exit(1)
    
    # Create generator
    generator = PluginGenerator(args.base_path)
    
    # Gather information
    info = generator.gather_language_info()
    
    # Confirm before generating
    print(f"\n=== Summary ===")
    print(f"Language: {info['display_name']}")
    print(f"Plugin name: {info['plugin_name']}")
    print(f"Extensions: {', '.join(info['extensions'])}")
    print(f"Symbol types: {', '.join(info['symbol_types'])}")
    if info['frameworks']:
        print(f"Frameworks: {', '.join(info['frameworks'])}")
    
    if not generator.prompt_yes_no("\nGenerate plugin with these settings?"):
        print("Plugin generation cancelled.")
        sys.exit(0)
    
    # Generate the plugin
    generator.generate_plugin(info)


if __name__ == "__main__":
    main()