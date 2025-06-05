# TOML Plugin

Comprehensive TOML language support with Tree-sitter parsing for configuration files, Rust projects (Cargo.toml), and Python projects (pyproject.toml).

## Features

- **Language**: TOML
- **File Extensions**: .toml, .lock
- **Special Files**: Cargo.toml, pyproject.toml, poetry.lock, config.toml
- **Plugin Type**: Tree-sitter based with regex fallback
- **Tree-sitter Support**: Yes (tree-sitter-toml)

## Supported Symbol Types

- **Tables/Sections**: `[section]` headers for configuration grouping
- **Table Arrays**: `[[array]]` for repeated configuration blocks
- **Key-Value Pairs**: Configuration variables and their values
- **Inline Tables**: Compact table definitions `{ key = "value" }`
- **Nested Structures**: Dotted keys and nested table support

## Special Features

### Cargo.toml Support
- Package metadata extraction (name, version, authors, edition)
- Dependency parsing with version and features
- Feature flag definitions and dependencies
- Workspace configuration
- Build targets (bin, lib, test, bench)

### pyproject.toml Support
- Project metadata (PEP 621)
- Build system configuration
- Tool-specific sections (poetry, black, mypy, etc.)
- Dependency specifications
- Optional dependencies

### Configuration File Support
- Nested table navigation
- Array of tables handling
- Multi-line string detection
- Date/time value recognition
- Key path extraction for nested values

## Usage

```python
from mcp_server.plugins.toml_plugin import Plugin

# Initialize the plugin
plugin = Plugin()

# Check if a file is supported
if plugin.supports("Cargo.toml"):
    # Index the file
    with open("Cargo.toml", "r") as f:
        content = f.read()
    
    result = plugin.indexFile("Cargo.toml", content)
    print(f"Found {len(result['symbols'])} symbols")
    
    # Access specific sections
    for symbol in result['symbols']:
        if symbol['kind'] == 'module':
            print(f"Section: {symbol['symbol']}")
        elif symbol.get('metadata', {}).get('is_dependency'):
            print(f"Dependency: {symbol['symbol']}")
```

## Configuration

The plugin can be configured using the `plugin_config.json` file:

```json
{
  "enabled": true,
  "max_file_size": 10485760,
  "cache_ttl": 3600,
  "strict_mode": false,
  "features": {
    "cargo_enhanced_parsing": true,
    "pyproject_enhanced_parsing": true,
    "path_extraction": true
  }
}
```

## Symbol Extraction

### Tables and Sections
```toml
[server]           # Extracted as MODULE symbol "server"
host = "localhost" # Extracted as VARIABLE symbol "host"

[server.database]  # Extracted as MODULE symbol "server.database"
url = "postgres"   # Full path: "server.database.url"
```

### Cargo.toml Specifics
```toml
[package]
name = "my-app"    # Extracted as PROPERTY "package.name"

[dependencies]
serde = "1.0"      # Extracted as IMPORT "dependencies.serde"

[features]
default = ["std"]  # Extracted as PROPERTY "features.default"
```

### pyproject.toml Specifics
```toml
[tool.poetry]
name = "my-project"  # Extracted as "tool.poetry"

[tool.black]
line-length = 88     # Tool configuration

[project]
requires-python = ">=3.8"  # Project metadata
```

## Advanced Features

### Key Path Navigation
The plugin extracts full key paths for nested structures, making it easy to navigate complex configurations:

```toml
[database.primary.connection]
host = "localhost"
# Full path: "database.primary.connection.host"
```

### Inline Table Support
```toml
database = { host = "localhost", port = 5432 }
# Detected as inline table with FIELD type
```

### Array of Tables
```toml
[[servers]]
name = "primary"

[[servers]]
name = "backup"
# Each entry is marked with "array" modifier
```

## Testing

Run tests with:
```bash
pytest test_toml_plugin.py
```

## Performance Considerations

- Tree-sitter parsing is preferred for accurate AST traversal
- Regex fallback available for systems without Tree-sitter
- Caching enabled by default for improved performance
- Large TOML files are processed incrementally

## Integration with Development Tools

### Rust Development
- Quick navigation through Cargo.toml dependencies
- Feature flag analysis
- Workspace member discovery
- Version conflict detection

### Python Development
- pyproject.toml standard compliance
- Tool configuration extraction
- Dependency management support
- Build system configuration parsing

### General Configuration
- Environment-specific settings
- Application configuration
- Docker compose files
- CI/CD pipeline configuration

## Future Enhancements

- [ ] Schema validation support
- [ ] Value type inference improvements
- [ ] Cross-reference analysis for dependencies
- [ ] Integration with package registries
- [ ] TOML syntax validation
- [ ] Automatic formatting suggestions

## License

MCP Server Team - 1.0.0