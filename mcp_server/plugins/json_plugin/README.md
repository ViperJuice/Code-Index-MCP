# Json Plugin

Comprehensive JSON plugin with schema detection, JSONPath support, and nested object navigation

## Features

- **Language**: json
- **File Extensions**: .json, .jsonc, .json5, .jsonl, .ndjson
- **Plugin Type**: hybrid
- **Tree-sitter Support**: Yes

## Supported Symbol Types

- Basic symbol extraction

## Usage

```python
from mcp_server.plugins.json_plugin import Plugin

# Initialize the plugin
plugin = Plugin()

# Check if a file is supported
if plugin.supports("example.json"):
    # Index the file
    with open("example.json", "r") as f:
        content = f.read()
    
    result = plugin.indexFile("example.json", content)
    print(f"Found {len(result['symbols'])} symbols")
```

## Configuration

The plugin can be configured using the `plugin_config.json` file:

```json
{
  "enabled": true,
  "max_file_size": 10485760,
  "cache_ttl": 3600,
  "strict_mode": false
}
```

## Testing

Run tests with:
```bash
pytest test_json_plugin.py
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

MCP Code Index - 1.0.0
