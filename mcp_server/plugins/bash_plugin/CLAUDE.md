# Bash/Shell Plugin - Claude Instructions

## Purpose

This plugin provides comprehensive parsing and indexing for shell scripts across multiple shell variants. It's specifically designed for DevOps scripts, build automation, and system administration tools.

## Key Capabilities

### Multi-Shell Support
- Bash, Zsh, Fish, Ksh, Csh, and POSIX shell scripts
- Automatic shell type detection via shebang or file extension
- Shell-specific syntax parsing

### Advanced Analysis
- Function definitions (all styles)
- Variable declarations and exports
- Alias definitions
- Control flow structures
- Command substitutions and parameter expansions
- Pipe and redirection analysis
- Source/include dependency tracking
- Error handling pattern detection
- Logging and monitoring code identification
- External tool usage (Docker, Kubernetes, Git, etc.)

### Symbol Extraction
- **Functions**: All function definition styles
- **Variables**: Regular variables, exports, locals, readonly
- **Aliases**: Command aliases
- **Commands**: External commands and utilities

## Usage Instructions

### Basic Operations

```python
# Initialize plugin
plugin = Plugin()

# Check file support
if plugin.supports("deploy.sh"):
    # Index shell script
    content = open("deploy.sh").read()
    result = plugin.indexFile("deploy.sh", content)
    
    # Access results
    print(f"Shell type: {result['shell_type']}")
    print(f"Symbols found: {len(result['symbols'])}")
```

### Symbol Lookup

```python
# Find function definition
definition = plugin.getDefinition("deploy_function")

# Find variable references
references = plugin.findReferences("DATABASE_URL")

# Search for patterns
results = plugin.search("docker build")
```

### Comprehensive Analysis

```python
# Get detailed analysis
analysis = plugin.get_shell_analysis("script.sh", content)

# Check script characteristics
if analysis["has_error_handling"]:
    print("Script includes error handling")

if analysis["complexity_score"] > 10:
    print("High complexity script")

print(f"External dependencies: {analysis['external_dependencies']}")
```

## Supported Patterns

### Function Definitions
```bash
# All these patterns are supported
function name() { ... }
name() { ... }
function name { ... }
function name --description "Fish style"
```

### Variable Patterns
```bash
# Various declaration styles
VAR="value"
export PATH="/usr/local/bin:$PATH"
declare -r VERSION="1.0.0"
local temp="temporary"
readonly CONST="immutable"
typeset -i COUNT=10
```

### Control Structures
```bash
# All control flow patterns
if [[ condition ]]; then ... fi
for item in list; do ... done
while condition; do ... done
case $var in pattern) ... ;; esac
```

## Integration Features

### DevOps Tool Detection
- Docker commands and Dockerfiles
- Kubernetes kubectl operations
- CI/CD pipeline scripts
- Infrastructure as Code tools

### Security Analysis
- SUID file detection patterns
- Permission checking code
- Authentication/authorization patterns
- Credential handling analysis

### Performance Monitoring
- Resource usage tracking
- Performance measurement code
- Monitoring and alerting patterns

## Configuration

### Plugin Settings
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

### Environment Variables
- `SHELL_PLUGIN_DEBUG`: Enable debug output
- `SHELL_PLUGIN_STRICT`: Strict parsing mode
- `SHELL_PLUGIN_CACHE_TTL`: Cache time-to-live

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
            "docstring": "Function documentation",
            "metadata": {
                "shell_type": "bash",
                "body_preview": "..."
            }
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
    "control_structures": 3,
    "pipe_redirect_operations": 7,
    "substitution_count": 4
}
```

## Best Practices

### For Script Analysis
1. **Always check shell type** - Different shells have different syntax
2. **Monitor complexity scores** - High scores indicate maintenance concerns
3. **Track dependencies** - External tools affect portability
4. **Verify error handling** - Critical for production scripts

### For Development
1. **Use consistent function styles** - Improves parsing accuracy
2. **Include documentation comments** - Enhances symbol information
3. **Follow shell best practices** - Better analysis results
4. **Test with multiple shells** - Ensure compatibility

### For Performance
1. **Enable caching** - Reduces re-parsing overhead
2. **Use appropriate batch sizes** - For large repositories
3. **Monitor memory usage** - With very large scripts
4. **Consider Tree-sitter** - For complex parsing needs

## Error Handling

### Common Issues
- **Malformed shebangs**: Ensure proper `#!/shell/path` format
- **Complex nesting**: Deep function/loop nesting may affect parsing
- **Non-standard syntax**: Shell-specific extensions may not parse correctly
- **Large files**: May hit size limits or performance issues

### Debug Mode
Enable detailed debugging:
```bash
export SHELL_PLUGIN_DEBUG=1
# Run plugin operations for detailed output
```

## Limitations

### Parsing Limitations
- Complex heredocs may not be fully parsed
- Dynamic function generation not detected
- Some shell-specific extensions not supported
- Eval statements content not analyzed

### Performance Constraints
- Large files (>10MB) may be skipped
- Very complex scripts may hit parsing timeouts
- Memory usage scales with script complexity

## Future Enhancements

### Planned Features
- Enhanced Tree-sitter integration
- Better shell-specific syntax support
- Improved security analysis
- Performance optimization
- Cross-reference analysis between scripts

### Extensibility
The plugin is designed to be extensible:
- Add new shell types
- Extend pattern recognition
- Enhance analysis capabilities
- Improve performance optimizations