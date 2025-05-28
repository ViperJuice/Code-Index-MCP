# MCP Server Plugins

This directory contains language-specific plugins for code indexing and analysis. Each plugin implements the `PluginBase` interface and provides language-specific functionality.

## Available Plugins

- `python_plugin/`: Python code indexing and analysis
- `c_plugin/`: C code indexing and analysis
- `cpp_plugin/`: C++ code indexing and analysis
- `dart_plugin/`: Dart code indexing and analysis
- `html_css_plugin/`: HTML/CSS code indexing and analysis
- `js_plugin/`: JavaScript code indexing and analysis

## Plugin Structure

Each plugin directory should contain:
1. `__init__.py`: Plugin registration
2. `indexer.py`: Main indexing logic
3. `parser.py`: Language-specific parsing
4. `utils.py`: Helper functions
5. `tests/`: Plugin-specific tests

## Plugin Development

When creating a new plugin:
1. Inherit from `PluginBase`
2. Implement required methods
3. Add language-specific tests
4. Document language quirks
5. Handle edge cases

## Common Patterns

- Use Tree-sitter for parsing
- Implement incremental updates
- Cache parsed results
- Handle language-specific features 