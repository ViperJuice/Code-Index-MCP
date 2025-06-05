# Bash/Shell Plugin - Agent Instructions

## Overview

The Bash/Shell plugin provides comprehensive analysis and indexing capabilities for shell scripts across multiple shell variants including Bash, Zsh, Fish, Ksh, and Csh. This plugin is specifically designed to handle DevOps scripts, build automation, and system administration tools.

## Key Features

### Multi-Shell Support
- **Bash** (`.bash`, `.sh` with bash shebang)
- **Zsh** (`.zsh`)
- **Fish** (`.fish`)
- **Ksh** (`.ksh`)
- **Csh/Tcsh** (`.csh`)
- **POSIX Shell** (`.sh`)

### Advanced Shell Analysis
- **Shebang Detection**: Automatically identifies shell type from `#!` lines
- **Function Parsing**: Supports all function definition styles
- **Variable Analysis**: Tracks exports, locals, readonly, and typeset variables
- **Alias Detection**: Identifies command aliases
- **Control Structures**: Parses if/then/else, for/while/until loops, case statements
- **Command Substitution**: Detects `$()` and backtick substitutions
- **Parameter Expansion**: Tracks `${}` parameter expansions
- **Pipe/Redirection Analysis**: Identifies complex command pipelines
- **Source/Include Tracking**: Maps script dependencies

### DevOps and System Administration Features
- **Error Handling Detection**: Identifies `set -e`, traps, and error handling patterns
- **Logging Analysis**: Detects logging and monitoring code
- **External Command Tracking**: Catalogs usage of Docker, Kubernetes, Git, and other tools
- **Environment Variable Mapping**: Tracks all environment variables used
- **Complexity Scoring**: Provides script complexity metrics
- **Security Analysis**: Basic security pattern detection

## Symbol Types Extracted

### Functions
```bash
function deploy() { ... }
deploy() { ... }
function cleanup { ... }
```

### Variables and Exports
```bash
NAME="value"
export PATH="/usr/local/bin:$PATH"
declare -r VERSION="1.0.0"
local temp_var="temp"
readonly CONSTANT="immutable"
```

### Aliases
```bash
alias ll='ls -la'
alias grep='grep --color=auto'
```

### Commands
```bash
docker build -t app:latest .
kubectl apply -f deployment.yaml
systemctl restart nginx
```

## Usage Examples

### Basic Indexing
```python
from mcp_server.plugins.bash_plugin import Plugin

plugin = Plugin()

# Index a shell script
content = open('deploy.sh').read()
result = plugin.indexFile('deploy.sh', content)

print(f"Found {len(result['symbols'])} symbols")
print(f"Shell type: {result['shell_type']}")
print(f"Complexity score: {result['metadata']['complexity_score']}")
```

### Symbol Lookup
```python
# Find function definition
definition = plugin.getDefinition('deploy_application')
if definition:
    print(f"Function defined in {definition['defined_in']} at line {definition['line']}")

# Find all references
references = plugin.findReferences('DATABASE_URL')
for ref in references:
    print(f"Used in {ref.file} at line {ref.line}")
```

### Comprehensive Analysis
```python
# Get detailed shell script analysis
analysis = plugin.get_shell_analysis('deploy.sh', content)

print(f"Functions: {analysis['function_count']}")
print(f"Variables: {analysis['variable_count']}")
print(f"Exports: {analysis['export_count']}")
print(f"External dependencies: {analysis['external_dependencies']}")
print(f"Has error handling: {analysis['has_error_handling']}")
print(f"Has logging: {analysis['has_logging']}")
```

## Configuration

### Plugin Settings
The plugin can be configured via `plugin_config.json`:

```json
{
  "plugin": {
    "name": "bash",
    "language": "shell",
    "type": "hybrid"
  },
  "features": {
    "tree_sitter_support": true,
    "caching": true,
    "semantic_analysis": true
  },
  "performance": {
    "max_file_size": 10485760,
    "cache_ttl": 3600
  }
}
```

### Environment Variables
- `SHELL_PLUGIN_DEBUG`: Enable debug output
- `SHELL_PLUGIN_STRICT`: Enable strict parsing mode
- `SHELL_PLUGIN_CACHE_TTL`: Override cache TTL

## Supported Patterns

### Function Definitions
- `function name() { ... }`
- `name() { ... }`
- `function name { ... }` (Bash/Zsh)
- `function name --description "desc"` (Fish)

### Variable Declarations
- `VAR=value`
- `export VAR=value`
- `declare -r VAR=value`
- `local VAR=value`
- `readonly VAR=value`
- `typeset VAR=value`

### Control Structures
- `if [[ condition ]]; then ... fi`
- `for var in list; do ... done`
- `while condition; do ... done`
- `until condition; do ... done`
- `case $var in pattern) ... ;; esac`
- `select var in list; do ... done`

### Advanced Features
- Here documents (`<<EOF ... EOF`)
- Process substitution (`<(command)`)
- Arithmetic expansion (`$((expression))`)
- Brace expansion (`{a,b,c}`)
- Glob patterns (`*.txt`, `**/*.sh`)

## Integration with Other Tools

### Tree-sitter Support
The plugin can utilize tree-sitter-bash for more accurate parsing when available:
```bash
# Install tree-sitter-bash
npm install tree-sitter-bash
```

### Docker Integration
Automatically detects Dockerfile patterns and Docker commands:
```bash
docker build -t $IMAGE_NAME .
docker-compose up -d
```

### Kubernetes Integration
Recognizes kubectl commands and YAML file references:
```bash
kubectl apply -f deployment.yaml
helm install myapp ./charts/myapp
```

### CI/CD Integration
Identifies common CI/CD patterns:
```bash
# GitLab CI
gitlab-runner exec docker build
# GitHub Actions
act -j build
# Jenkins
jenkins-cli build project
```

## Performance Considerations

### Optimization Features
- **Regex Fallback**: Fast regex parsing when Tree-sitter unavailable
- **Incremental Parsing**: Only re-parse changed files
- **Symbol Caching**: Cache extracted symbols with TTL
- **Batch Processing**: Process multiple files efficiently

### Memory Management
- Streaming parser for large files
- Configurable memory limits
- Automatic cleanup of temporary data

### Scalability
- Supports repositories with thousands of shell scripts
- Parallel processing for multiple files
- Database persistence for symbol storage

## Testing

### Test Data
The plugin includes comprehensive test data:
- `sample_devops.sh`: DevOps deployment script
- `build_system.sh`: Build automation script
- `system_admin.zsh`: System administration utilities
- `fish_config.fish`: Fish shell configuration

### Running Tests
```bash
# Run all tests
pytest mcp_server/plugins/bash_plugin/test_bash_plugin.py

# Run specific test class
pytest mcp_server/plugins/bash_plugin/test_bash_plugin.py::TestBashPlugin

# Run with coverage
pytest --cov=mcp_server.plugins.bash_plugin
```

## Troubleshooting

### Common Issues

#### Shebang Not Detected
```bash
# Ensure proper shebang format
#!/bin/bash  # Correct
#! /bin/bash  # May not be detected
```

#### Complex Functions Not Parsed
- Check for nested braces and proper syntax
- Enable debug mode for detailed parsing information
- Consider using Tree-sitter for complex cases

#### Performance Issues
- Increase cache TTL for frequently accessed files
- Use regex mode for very large repositories
- Configure appropriate batch sizes

### Debug Mode
```bash
export SHELL_PLUGIN_DEBUG=1
# Re-run plugin operations to see detailed output
```

## Contributing

### Adding New Shell Support
1. Add shell type to `ShellType` enum
2. Update `detect_shell_type()` method
3. Add shell-specific patterns to parser
4. Create test cases for new shell
5. Update documentation

### Extending Pattern Recognition
1. Add patterns to appropriate pattern dictionaries
2. Update parsing methods
3. Add test cases
4. Update symbol extraction logic

### Performance Improvements
1. Profile existing code
2. Optimize regex patterns
3. Implement caching improvements
4. Add benchmarks