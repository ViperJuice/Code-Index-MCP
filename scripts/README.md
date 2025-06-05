# Scripts Directory

This directory contains various utility scripts for the Code-Index-MCP project.

## Plugin Generation

### `generate_language_plugin.py`

**Interactive Plugin Generator for New Languages**

This powerful tool automates the creation of language plugins, scaffolding everything needed to add support for a new programming language in minutes rather than hours.

#### Features

- **Complete Plugin Structure**: Generates all necessary files and directories
- **Boilerplate Code**: Creates language-specific plugin class with all required methods
- **Tree-sitter Integration**: Configures Tree-sitter support when available
- **Regex Patterns**: Generates common regex patterns for symbol extraction
- **Test Files**: Creates comprehensive test suites with sample code
- **Documentation**: Generates AGENTS.md and CLAUDE.md documentation templates
- **Registry Integration**: Automatically updates the plugin registry

#### Usage

**Interactive Mode (Recommended):**
```bash
python3 scripts/generate_language_plugin.py
```

The generator will prompt you for:
- Language name and display name
- File extensions (e.g., .py, .js, .ts)
- Tree-sitter parser availability
- Symbol types to extract (class, function, method, etc.)
- Framework detection requirements
- Language features (async, decorators, type annotations)
- Comment styles

**Example Session:**
```
=== Language Plugin Generator ===

Language name (e.g., Python, JavaScript): Swift
Display name [Swift]: Swift
File extensions (comma-separated, e.g., .py, .pyw): .swift
Does this language have Tree-sitter support? [Y/n]: y
Tree-sitter language name [swift]: swift
Symbol types for this language (comma-separated): class, func, var, enum, protocol
Does this language have frameworks to detect? [Y/n]: y
Framework names (comma-separated): SwiftUI, UIKit, Vapor
```

#### Generated Structure

For a language called "Swift", the generator creates:

```
mcp_server/plugins/swift_plugin/
├── __init__.py                 # Plugin module initialization
├── plugin.py                  # Main plugin implementation
├── patterns.py                # Regex patterns for parsing
├── AGENTS.md                  # Agent instructions
├── CLAUDE.md                  # Claude-specific documentation
└── test_data/
    ├── sample.swift           # Sample code for testing
    └── test_file.swift        # Additional test file

tests/
└── test_swift_plugin.py       # Comprehensive test suite
```

#### Customization After Generation

After generating a plugin, you should:

1. **Review `plugin.py`**: Customize the main plugin implementation
2. **Implement Import Extraction**: Add language-specific import detection in `_extract_imports()`
3. **Add Framework Detection**: Implement framework detection logic in `_detect_frameworks()`
4. **Update Regex Patterns**: Refine patterns in `patterns.py` for better accuracy
5. **Enhance Tests**: Add more test cases in the generated test file
6. **Update Documentation**: Refine the generated documentation

#### Advanced Usage

**Programmatic Generation:**

See `example_plugin_generation.py` for how to use the generator programmatically:

```python
from generate_language_plugin import PluginGenerator

generator = PluginGenerator(base_path)
info = {
    "name": "TypeScript",
    "display_name": "TypeScript", 
    "extensions": [".ts", ".tsx"],
    "has_treesitter": True,
    # ... more configuration
}
generator.generate_plugin(info)
```

### `example_plugin_generation.py`

Demonstrates programmatic usage of the plugin generator with a TypeScript example.

## Development Scripts

### Development Environment

- `start-development.sh`: Start development environment
- `setup-repository-dev.sh`: Set up development repository
- `setup-phase5-development.sh`: Phase 5 development setup

### Testing

- `run-parallel-tests.sh`: Run tests in parallel
- `development/test_repository_features.py`: Test repository features

### Deployment

- `setup-docker-deployment.sh`: Docker deployment setup
- `setup-phase5-container.sh`: Phase 5 container setup

### MCP Integration

- `setup-mcp-index.sh`: Set up MCP index
- `mcp-index`: MCP index utility
- `development/check_mcp_status.py`: Check MCP server status

### Utilities

- `setup-git-hooks.sh`: Set up Git hooks
- `setup-tree-sitter.sh`: Set up Tree-sitter parsers

## Tips for Plugin Development

### Best Practices

1. **Start Simple**: Begin with basic symbol extraction, then add advanced features
2. **Use Tree-sitter When Available**: Provides more accurate parsing than regex
3. **Test Thoroughly**: Use the generated test files and add your own test cases
4. **Follow Patterns**: Look at existing plugins (Python, JavaScript) for reference
5. **Document Everything**: Update AGENTS.md with specific instructions

### Common Symbol Types

- **class**: Class definitions
- **function**: Function definitions  
- **method**: Class methods
- **variable**: Variable declarations
- **constant**: Constants
- **interface**: Interface definitions (TypeScript, Java)
- **enum**: Enumeration types
- **type**: Type aliases
- **module**: Module/namespace definitions

### Framework Detection Tips

- Look for import statements
- Check for specific decorators or annotations
- Scan for framework-specific file patterns
- Detect configuration files (package.json, pom.xml, etc.)

## Getting Help

- Check existing plugins in `mcp_server/plugins/` for examples
- Review the documentation in `docs/`
- Run tests to validate your plugin works correctly
- Use the interactive generator for guidance

The plugin generator is designed to handle most common language patterns, but every language has unique characteristics that may require custom implementation.