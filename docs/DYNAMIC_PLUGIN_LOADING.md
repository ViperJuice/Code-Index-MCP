# Dynamic Plugin Loading System

## Overview

The MCP Server now features a comprehensive dynamic plugin loading system that automatically discovers, loads, and manages plugins at runtime. This system replaces the previous hardcoded plugin initialization, providing greater flexibility and extensibility.

## Key Components

### 1. Plugin Discovery (`discovery.py`)
- Automatically scans plugin directories for available plugins
- Supports both manifest-based and auto-discovery mechanisms
- Identifies plugins by:
  - `plugin.yaml` manifest files
  - Directory structure conventions
  - Module naming patterns

### 2. Plugin Loader (`loader.py`)
- Manages plugin lifecycle (loading, unloading, reloading)
- Thread-safe plugin management
- Resource cleanup and garbage collection
- Async loading support
- Context manager for temporary plugin usage

### 3. Configuration Manager (`config.py`)
- Centralized plugin configuration
- Environment-specific settings
- YAML/JSON configuration support
- Runtime configuration updates
- Configuration validation

### 4. CLI Tool (`cli.py`)
- Interactive plugin management
- Commands for discovery, loading, configuration
- Testing and debugging utilities

## Usage

### Basic Discovery and Loading

```python
from mcp_server.plugin_system import get_plugin_discovery, get_plugin_loader

# Discover available plugins
discovery = get_plugin_discovery()
plugins = discovery.discover_plugins()
print(f"Found {len(plugins)} plugins")

# Load a specific plugin
loader = get_plugin_loader()
python_plugin = loader.load_plugin('python')
```

### Configuration Management

```python
from mcp_server.plugin_system import get_config_manager

# Load configuration
config_manager = get_config_manager()
config = config_manager.load_plugin_config('python')

# Update settings
config_manager.update_plugin_settings('python', {
    'enable_semantic': True,
    'cache_size': 2000
})
```

### CLI Commands

```bash
# Discover available plugins
python -m mcp_server.plugin_system.cli discover

# Load a plugin
python -m mcp_server.plugin_system.cli load python

# Show plugin information
python -m mcp_server.plugin_system.cli info python

# List loaded plugins
python -m mcp_server.plugin_system.cli list

# Test a plugin
python -m mcp_server.plugin_system.cli test javascript
```

## Plugin Manifest Format

Plugins can include a `plugin.yaml` manifest file:

```yaml
name: "Python Plugin"
version: "1.0.0"
description: "Advanced Python language support"
languages:
  - python
entry_point: "mcp_server.plugins.python_plugin.plugin.PythonPlugin"
features:
  - symbol_extraction
  - semantic_search
  - type_inference
dependencies:
  - "tree-sitter>=0.20.0"
config_schema:
  enable_semantic:
    type: boolean
    default: true
  cache_size:
    type: integer
    default: 1000
```

## Auto-Discovery

Plugins without manifests are automatically discovered based on:
- Directory naming (e.g., `python_plugin/`)
- Module naming (e.g., `python_plugin.py`)
- Class inheritance from `IPlugin`

## Benefits

1. **Flexibility**: Add/remove plugins without code changes
2. **Extensibility**: Third-party plugin support
3. **Configuration**: Runtime configuration updates
4. **Performance**: Lazy loading and parallel initialization
5. **Management**: CLI tools for administration
6. **Testing**: Isolated plugin testing capabilities

## Migration from Static Loading

The gateway now uses dynamic loading:

```python
# Old approach (hardcoded)
plugins = [
    PythonPlugin(store),
    JavaScriptPlugin(store),
    # ... manually listed
]

# New approach (dynamic)
discovery = get_plugin_discovery()
loader = get_plugin_loader()
plugins = []
for language in discovery.get_supported_languages():
    plugin = loader.load_plugin(language)
    if plugin:
        plugins.append(plugin)
```

## Future Enhancements

- Hot-reloading for development
- Plugin marketplace integration
- Remote plugin repositories
- Plugin dependency resolution
- Sandboxed plugin execution
- Plugin versioning and updates