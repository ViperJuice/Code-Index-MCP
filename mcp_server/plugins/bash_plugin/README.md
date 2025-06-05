# Bash/Shell Plugin

A comprehensive plugin for analyzing and indexing shell scripts across multiple shell variants.

## Features

### Multi-Shell Support
- **Bash** (`.bash`, `.sh` with bash shebang)
- **Zsh** (`.zsh`) 
- **Fish** (`.fish`)
- **Ksh** (`.ksh`)
- **Csh/Tcsh** (`.csh`)
- **POSIX Shell** (`.sh`)

### Advanced Analysis Capabilities
- **Shebang Detection**: Automatically identifies shell type from `#!` lines
- **Function Parsing**: All function definition styles (`function name()`, `name()`, etc.)
- **Variable Analysis**: Variables, exports, locals, readonly, typeset declarations
- **Alias Detection**: Command aliases and their definitions
- **Control Flow**: if/then/else, for/while/until loops, case statements
- **Command Substitution**: `$()` and backtick substitutions
- **Parameter Expansion**: `${}` parameter expansions
- **Source/Include Tracking**: Script dependencies via source/include
- **Error Handling Detection**: `set -e`, traps, error handling patterns
- **Logging Analysis**: Logging and monitoring code detection

### DevOps and System Administration
- **External Command Tracking**: Docker, Kubernetes, Git, system tools
- **Environment Variable Mapping**: All environment variables used
- **Complexity Scoring**: Script complexity metrics
- **Security Pattern Detection**: Basic security analysis

## Installation

The plugin is automatically available as part of the MCP Server plugin system.

```python
from mcp_server.plugins.bash_plugin import Plugin

plugin = Plugin()
```

## Usage Examples

### Basic Indexing

```python
# Index a shell script
content = open('deploy.sh').read()
result = plugin.indexFile('deploy.sh', content)

print(f"Found {len(result['symbols'])} symbols")
print(f"Shell type: {result['shell_type']}")
```

### Symbol Lookup

```python
# Find function definition
definition = plugin.getDefinition('deploy_function')
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
print(f"Has error handling: {analysis['has_error_handling']}")
print(f"Complexity score: {analysis['complexity_score']}")
```

## Supported Patterns

### Function Definitions
```bash
function name() { ... }    # Bash/Zsh style
name() { ... }            # POSIX style
function name { ... }     # Bash/Zsh without parentheses
function name --description "desc"  # Fish style
```

### Variable Declarations
```bash
VAR=value                 # Basic assignment
export VAR=value          # Export
declare -r VAR=value      # Declare readonly
local VAR=value           # Local variable
readonly VAR=value        # Readonly
typeset VAR=value         # Typeset (Zsh/Ksh)
```

### Control Structures
```bash
if [[ condition ]]; then ... fi
for var in list; do ... done
while condition; do ... done
until condition; do ... done
case $var in pattern) ... ;; esac
select var in list; do ... done
```

### Advanced Features
```bash
source ./config.sh       # Source inclusion
. ./utils.sh             # Dot notation
alias ll='ls -la'        # Aliases
$(command)               # Command substitution
${VAR:-default}          # Parameter expansion
```

## Output Format

### IndexShard Structure
```python
{
    "file": "path/to/script.sh",
    "language": "shell",
    "shell_type": "bash",
    "shebang": "/bin/bash",
    "symbols": [
        {
            "symbol": "function_name",
            "kind": "function",
            "signature": "function function_name() {",
            "line": 10,
            "span": (10, 20),
            "metadata": {"shell_type": "bash"}
        }
    ],
    "metadata": {
        "complexity_score": 15,
        "has_error_handling": true,
        "has_logging": true,
        "external_deps": ["docker", "kubectl"],
        "environment_vars": ["PATH", "DATABASE_URL"]
    }
}
```

### Analysis Output
```python
{
    "shell_type": "bash",
    "function_count": 5,
    "variable_count": 8,
    "export_count": 3,
    "alias_count": 2,
    "complexity_score": 15,
    "has_error_handling": true,
    "has_logging": true,
    "external_dependencies": ["docker", "kubectl", "git"],
    "environment_variables": ["PATH", "DATABASE_URL"],
    "control_structures": 3
}
```

## Test Data

The plugin includes comprehensive test scripts:

- **`sample_devops.sh`**: DevOps deployment script with Docker/Kubernetes
- **`build_system.sh`**: Build automation with parallel processing
- **`system_admin.zsh`**: Zsh system administration utilities
- **`fish_config.fish`**: Fish shell configuration and functions

## Testing

```bash
# Run all tests
pytest mcp_server/plugins/bash_plugin/test_bash_plugin.py

# Test with sample scripts
python -c "
from mcp_server.plugins.bash_plugin import Plugin
plugin = Plugin()
# Test functionality...
"
```

## Performance

- **Regex-based parsing** for maximum compatibility
- **Incremental processing** of large files
- **Symbol caching** with configurable TTL
- **Memory-efficient** for large repositories
- **Batch processing** support

## Tree-sitter Integration

The plugin is designed to work with tree-sitter-bash when available:

```bash
npm install tree-sitter-bash
```

When tree-sitter is available, the plugin can provide more accurate parsing for complex shell constructs.

## Configuration

```json
{
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

## Limitations

- Complex heredocs may not be fully parsed
- Dynamic function generation not detected
- Some shell-specific extensions not supported
- Large files (>10MB) may be skipped for performance

## Contributing

To extend the plugin:

1. Add new shell types to `ShellType` enum
2. Update pattern dictionaries for new syntax
3. Add test cases for new features
4. Update documentation

## License

Part of the MCP Server project.