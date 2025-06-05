# JSON Plugin for Claude Code

## Overview

A comprehensive JSON plugin that understands modern web development ecosystems and configuration files. This plugin goes beyond basic JSON parsing to provide intelligent schema detection and context-aware symbol extraction.

## Key Capabilities

### Intelligent Schema Detection
- **Automatic Recognition**: Detects package.json, tsconfig.json, composer.json, and other common formats
- **Content-Based Detection**: Identifies schemas even when filenames don't match exactly
- **Schema-Specific Parsing**: Extracts meaningful symbols based on detected schema type

### Modern JSON Support
- **JSON Variants**: Full support for JSON, JSONC (with comments), JSON5, JSONL, and NDJSON
- **Comment Handling**: Properly strips single-line (//) and block (/* */) comments
- **Robust Parsing**: Graceful fallback between parsing strategies

### Advanced Navigation
- **JSONPath Integration**: Build and parse JSONPath expressions for precise data access
- **Nested Structure Analysis**: Deep understanding of object hierarchies and arrays
- **Path-Based Search**: Search for data using JSONPath patterns

## Schema Support

### NPM Package (package.json)
**Detection**: Files named `package.json` or containing `name`, `version`, and `dependencies`

**Extracted Symbols**:
- **Scripts** → Function symbols (e.g., `npm run build`)
- **Dependencies** → Import symbols with version information
- **Metadata** → Property symbols (name, version, description)

**Example Output**:
```
build (function) - npm run build
express (import) - "express": "^4.18.2" 
name (property) - "name": string
```

### TypeScript Configuration (tsconfig.json)
**Detection**: Files named `tsconfig.json` or containing `compilerOptions`

**Extracted Symbols**:
- **Compiler Options** → Property symbols with values
- **Path Mappings** → Configuration symbols
- **Include/Exclude** → File pattern symbols

### Composer Package (composer.json)
**Detection**: Files named `composer.json` or containing `require` object

**Extracted Symbols**:
- **PHP Dependencies** → Import symbols
- **Scripts** → Function symbols
- **Autoload Configuration** → Namespace symbols

### Configuration Files
- **ESLint** (.eslintrc.json): Rules and environment settings
- **VS Code** (settings.json): Workspace and user preferences
- **Browser Extensions** (manifest.json): Extension metadata and permissions

## Advanced Features

### JSONPath Queries
```javascript
// Search for API configuration
$.api.endpoints.users

// Find specific array elements
$.products[0].specifications

// Navigate complex nested structures
$.features.user_management.registration
```

### Symbol Type Intelligence
- **Properties**: Regular key-value pairs
- **Functions**: Executable scripts and commands
- **Imports**: Dependencies and external packages
- **Namespaces**: Complex configuration sections
- **Fields**: Arrays and collections

### Metadata Enrichment
Each symbol includes rich metadata:
- **JSONPath**: Exact location in the structure
- **Value Type**: string, number, object, array, boolean, null
- **Schema Context**: Information from detected schema
- **Scope**: Parent object or configuration section

## Usage Examples

### Basic Indexing
```python
from mcp_server.plugins.json_plugin import Plugin

plugin = Plugin()
result = plugin.indexFile("package.json", content)

# Get all symbols
symbols = result["symbols"]

# Filter by type
scripts = [s for s in symbols if s["kind"] == "function"]
dependencies = [s for s in symbols if s["kind"] == "import"]
```

### Advanced Search
```python
# JSONPath-based search
api_config = plugin.search("$.api")
database_settings = plugin.search("$.database.connections")

# Schema-type search
all_packages = plugin.search("package.json")

# Symbol definition lookup
definition = plugin.getDefinition("compilerOptions")
```

### Configuration
```python
from mcp_server.plugins.plugin_template import PluginConfig

config = PluginConfig(
    enable_caching=True,
    cache_ttl=3600,
    enable_semantic_analysis=True
)
plugin = Plugin(config=config)
```

## Performance Characteristics

- **File Size Limit**: 10MB default (configurable)
- **Caching**: Automatic caching of parsed structures
- **Memory Efficient**: Lazy loading and cleanup
- **Fast Parsing**: Optimized JSON parsing with fallbacks

## Error Handling

The plugin provides robust error handling:
1. **JSON Syntax Errors**: Falls back to regex parsing
2. **Large Files**: Graceful size limit handling
3. **Invalid Comments**: Attempts to clean and reparse
4. **Tree-sitter Failures**: Automatic fallback to JSON parsing

## Integration Features

### MCP Protocol Compatibility
- Standard `indexFile`, `getDefinition`, `findReferences`, `search` methods
- Full integration with MCP server infrastructure
- Session management and caching support

### Plugin System Integration
- Automatic discovery and registration
- Configuration management
- Logging and monitoring
- Resource management

### Development Tools
- Comprehensive test suite
- Performance benchmarks
- Debug logging
- Plugin information API

## Real-World Examples

### NPM Project Analysis
```json
{
  "name": "@company/awesome-app",
  "scripts": {
    "build": "webpack --mode=production",
    "test": "jest --coverage"
  },
  "dependencies": {
    "express": "^4.18.2",
    "lodash": "^4.17.21"
  }
}
```

**Extracted Symbols**:
- `build` (function): npm run build
- `test` (function): npm run test  
- `express` (import): "express": "^4.18.2"
- `lodash` (import): "lodash": "^4.17.21"

### TypeScript Configuration
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "strict": true,
    "outDir": "./dist"
  },
  "include": ["src/**/*"]
}
```

**Extracted Symbols**:
- `target` (property): target: "ES2022"
- `strict` (property): strict: true
- `outDir` (property): outDir: "./dist"

## Future Roadmap

1. **Enhanced Tree-sitter**: Full query-based parsing for maximum performance
2. **Schema Validation**: JSON Schema validation and error reporting
3. **More Formats**: Support for YAML, TOML, and other configuration formats
4. **AI Integration**: Semantic understanding and intelligent suggestions
5. **IDE Features**: Code completion and validation support

This plugin represents a significant advancement in JSON file understanding, moving beyond simple parsing to provide deep, contextual analysis that supports modern development workflows.