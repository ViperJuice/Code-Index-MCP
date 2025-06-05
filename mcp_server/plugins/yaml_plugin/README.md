# YAML Plugin

A comprehensive YAML language plugin for the Code Index MCP server that provides advanced parsing and indexing capabilities for YAML configuration files commonly used in DevOps workflows.

## Features

### Core YAML Support
- **Multi-document YAML files**: Handles files with multiple YAML documents separated by `---`
- **Anchor and alias resolution**: Tracks YAML anchors (`&name`) and aliases (`*name`) for configuration reuse
- **Complex key path extraction**: Deep indexing of nested objects and arrays with full path resolution
- **Tree-sitter parsing**: Fast, accurate parsing with regex fallback for robustness

### Schema Detection and Validation
The plugin automatically detects and provides enhanced support for common YAML schemas:

- **Kubernetes manifests**: Resources, services, deployments, configmaps, etc.
- **Docker Compose files**: Services, volumes, networks, environment variables
- **GitHub Actions workflows**: Jobs, steps, triggers, actions
- **Ansible playbooks**: Tasks, handlers, variables, roles
- **OpenAPI specifications**: Endpoints, schemas, parameters
- **YAML front matter**: Jekyll, Hugo, and other static site generators

### Advanced Indexing Features
- **Intelligent symbol classification**: Context-aware symbol typing based on schema
- **Metadata extraction**: Schema-specific metadata for enhanced search and navigation
- **Cross-reference tracking**: Links between anchors and aliases
- **Value type detection**: Strings, numbers, booleans, arrays, objects
- **Comment indexing**: Meaningful comments are indexed for searchability

## Supported File Extensions

- `.yml` - Standard YAML files
- `.yaml` - Standard YAML files  
- `.yaml.dist` - Distribution/template YAML files
- `.md` - Markdown files with YAML front matter

## Supported Schemas

### Kubernetes
Automatically detects Kubernetes manifests and extracts:
- Resource kind and API version
- Metadata (name, namespace, labels, annotations)
- Spec configurations
- Container definitions
- Environment variables and secrets

### Docker Compose
Provides specialized support for Docker Compose files:
- Service definitions
- Volume and network configurations
- Environment variables
- Port mappings
- Dependency relationships
- Anchor/alias inheritance patterns

### GitHub Actions
Understands GitHub Actions workflow structure:
- Workflow triggers (`on`)
- Job definitions and dependencies
- Step actions and commands
- Environment variables and secrets
- Matrix strategies
- Conditional expressions

### Front Matter
Handles YAML front matter in Markdown files:
- Blog post metadata
- Page configurations
- SEO settings
- Category and tag systems

## Usage Examples

### Basic Indexing

```python
from mcp_server.plugins.yaml_plugin import Plugin

# Initialize the plugin
plugin = Plugin()

# Index a YAML file
with open('config.yaml', 'r') as f:
    content = f.read()
    shard = plugin.indexFile('config.yaml', content)

print(f"Found {len(shard['symbols'])} symbols")
```

### Schema-Specific Information

```python
# Get plugin information including schema statistics
info = plugin.get_plugin_info()
print(f"Supported schemas: {info['supported_schemas']}")

# Get statistics about detected schemas
stats = plugin.get_schema_statistics()
for schema, count in stats.items():
    print(f"{schema}: {count} symbols")
```

### Symbol Search and Navigation

```python
# Find definition of a symbol
definition = plugin.getDefinition("nginx-deployment")
if definition:
    print(f"Found {definition['symbol']} at {definition['defined_in']}:{definition['line']}")

# Find all references to a symbol
references = plugin.findReferences("common-env")
for ref in references:
    print(f"Reference at {ref.file}:{ref.line}")

# Search for patterns
results = plugin.search("postgres", {"limit": 10})
for result in results:
    print(f"Match: {result['snippet']} in {result['file']}")
```

## Configuration

The plugin can be configured with various options:

```python
from mcp_server.plugins.yaml_plugin.plugin import PluginConfig

config = PluginConfig(
    enable_caching=True,
    cache_ttl=3600,
    preferred_backend="tree-sitter",  # or "yaml" or "regex"
    enable_semantic_analysis=True,
    enable_cross_references=True
)

plugin = Plugin(config=config)
```

## Schema Detection Logic

The plugin uses multiple strategies to detect YAML schemas:

1. **Filename patterns**: `docker-compose.yml`, `.github/workflows/*.yml`
2. **Content analysis**: Presence of specific keys like `apiVersion`, `services`, `on`
3. **Path context**: File location within project structure
4. **Combined heuristics**: Multiple indicators for confident detection

## Symbol Types

The plugin defines specific symbol types for YAML structures:

- `key`: Standard YAML keys
- `anchor`: YAML anchors (`&name`)
- `alias`: YAML aliases (`*name`)
- `array`: List structures
- `object`: Mapping structures
- `document`: Document separators
- `kubernetes_resource`: Kubernetes resources
- `docker_service`: Docker Compose services
- `github_action`: GitHub Actions
- `front_matter`: Front matter blocks

## Tree-sitter Queries

The plugin includes custom Tree-sitter queries for enhanced parsing:

- `highlights.scm`: Syntax highlighting patterns
- `symbols.scm`: Symbol extraction patterns

These queries provide precise identification of YAML constructs and enable advanced features like semantic highlighting and intelligent navigation.

## Performance

The plugin is optimized for performance with:

- **Lazy loading**: Only parses files when needed
- **Caching**: Results are cached to avoid re-parsing
- **Incremental indexing**: Updates only changed files
- **Streaming**: Handles large files efficiently
- **Parallel processing**: Multi-threaded indexing support

## Error Handling

The plugin gracefully handles various error conditions:

- **Malformed YAML**: Falls back to regex parsing
- **Large files**: Implements size limits and streaming
- **Missing dependencies**: Degrades functionality gracefully
- **Encoding issues**: Supports various text encodings

## Dependencies

### Required
- `pathlib` (standard library)
- `re` (standard library)
- `logging` (standard library)

### Optional (for enhanced features)
- `PyYAML`: Advanced YAML parsing
- `tree-sitter`: Fast, accurate parsing
- `tree-sitter-languages`: Language bindings

## Testing

The plugin includes comprehensive tests covering:

- Schema detection accuracy
- Symbol extraction completeness
- Real-world configuration files
- Error handling scenarios
- Performance benchmarks

Run tests with:
```bash
pytest tests/test_yaml_plugin.py -v
```

## Contributing

When contributing to the YAML plugin:

1. Add tests for new features
2. Update schema detection logic for new formats
3. Extend Tree-sitter queries for better parsing
4. Document new symbol types and metadata
5. Consider performance implications

## Examples

See the `test_data/` directory for examples of supported YAML files:

- `kubernetes_deployment.yaml`: Complex Kubernetes manifests
- `docker-compose.yml`: Multi-service Docker setup with anchors
- `github_workflow.yml`: Complete CI/CD pipeline
- `config.yaml`: General configuration with nested structures
- `blog_post.md`: Markdown with YAML front matter
- `ansible_playbook.yml`: Infrastructure automation

These examples demonstrate the plugin's capabilities across different YAML use cases and schemas.