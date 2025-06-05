# JSON Plugin - Agent Instructions

## Overview

The JSON plugin provides comprehensive support for JSON file parsing with advanced features including schema detection, JSONPath navigation, and modern web development ecosystem support.

## Key Features

### Schema Detection
- **NPM package.json**: Detects Node.js packages, extracts dependencies, scripts, and metadata
- **TypeScript tsconfig.json**: Parses compiler options and project configuration
- **Composer composer.json**: Identifies PHP packages and dependencies
- **ESLint .eslintrc.json**: Extracts linting rules and configuration
- **VS Code settings**: Handles workspace and user settings
- **Browser extensions**: Parses manifest.json files

### Advanced JSON Support
- **JSONPath navigation**: Build and parse JSONPath expressions for deep object navigation
- **Nested structure analysis**: Extract objects and arrays with metadata
- **Comment support**: Handle JSONC and JSON5 files with comments
- **Multiple formats**: Support for .json, .jsonc, .json5, .jsonl, .ndjson

### Symbol Types
- **Properties**: Regular JSON keys and values
- **Functions**: NPM scripts, executable commands
- **Imports**: Dependencies and package references
- **Namespaces**: Complex objects and configuration sections
- **Fields**: Arrays and collection structures

## Architecture

### Core Components

1. **JSONSchemaDetector**: Automatically identifies file types and applies schema-specific parsing
2. **JSONPathBuilder**: Constructs and parses JSONPath expressions for navigation
3. **Plugin**: Main class integrating all functionality with Tree-sitter fallback

### Parsing Strategy

The plugin uses a multi-layered approach:

1. **Primary**: Standard JSON parsing with schema awareness
2. **Preprocessing**: Handle JSONC/JSON5 comments and variants
3. **Fallback**: Tree-sitter parsing (prepared for future enhancement)
4. **Ultimate fallback**: Regex-based extraction

## Usage Examples

### Basic JSON Indexing
```python
plugin = Plugin()
result = plugin.indexFile("config.json", json_content)
symbols = result["symbols"]
```

### Schema-Aware Processing
```python
# Automatically detects package.json schema
result = plugin.indexFile("package.json", package_content)

# Extract NPM scripts as functions
scripts = [s for s in result["symbols"] if s["kind"] == "function"]

# Extract dependencies as imports
deps = [s for s in result["symbols"] if s["kind"] == "import"]
```

### JSONPath Search
```python
# Search for specific paths
api_keys = plugin.search("$.api")
database_config = plugin.search("$.database.connections")

# Schema type search
packages = plugin.search("package.json")
```

## Configuration

The plugin supports standard LanguagePluginBase configuration:

```python
config = PluginConfig(
    enable_caching=True,
    cache_ttl=3600,
    async_processing=True,
    enable_semantic_analysis=True
)
plugin = Plugin(config=config)
```

## Supported File Types

| Extension | Description | Schema Detection |
|-----------|-------------|------------------|
| .json | Standard JSON | ✓ |
| .jsonc | JSON with Comments | ✓ |
| .json5 | JSON5 format | ✓ |
| .jsonl | JSON Lines | ✓ |
| .ndjson | Newline Delimited JSON | ✓ |

## Schema Types Supported

### NPM Package (package.json)
- Dependencies → Import symbols
- Scripts → Function symbols
- Metadata → Property symbols

### TypeScript Config (tsconfig.json)
- Compiler options → Property symbols
- Paths mapping → Configuration symbols

### Composer Package (composer.json)
- PHP dependencies → Import symbols
- Autoload configuration → Namespace symbols

### ESLint Config (.eslintrc.json)
- Rules → Property symbols
- Environment settings → Configuration symbols

## Performance Considerations

- **Caching**: Automatic caching of parsed structures and schemas
- **Large files**: Graceful handling of files up to 10MB
- **Deep nesting**: Efficient processing of deeply nested structures
- **Memory management**: Lazy loading of Tree-sitter components

## Future Enhancements

1. **Full Tree-sitter Integration**: Complete query-based parsing for better performance
2. **Additional Schemas**: Support for more configuration formats
3. **Validation**: JSON schema validation and error reporting
4. **Semantic Search**: AI-powered content understanding

## Testing

Comprehensive test suite includes:
- Schema detection validation
- JSONPath functionality
- Complex nested structures
- Comment handling
- Performance testing

Run tests with:
```bash
python -m pytest tests/test_json_plugin_comprehensive.py -v
```

## Integration with MCP

The plugin integrates seamlessly with the MCP server infrastructure:
- Automatic registration through plugin discovery
- Standard MCP protocol support
- Resource and tool integration
- Session management compatibility