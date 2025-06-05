# C# Plugin Agent Instructions

## Overview
The C# plugin provides comprehensive support for C# language analysis within the Code-Index-MCP system. It's designed to handle modern C# codebases including .NET Framework, .NET Core, and .NET 5+ projects.

## Core Features

### Language Support
- **File Extensions**: `.cs`, `.csx`, `.cshtml`
- **Parsing Strategy**: Hybrid (Tree-sitter with regex fallback)
- **Tree-sitter Grammar**: `tree-sitter-c-sharp`

### Symbol Types Detected
- **Classes**: `public class`, `abstract class`, `sealed class`, `static class`
- **Interfaces**: `public interface`, `internal interface`
- **Structs**: `public struct`, `readonly struct`
- **Enums**: `public enum`, `[Flags] enum`
- **Methods**: Instance, static, async, generic, extension methods
- **Properties**: Auto-implemented, expression-bodied, get/set properties
- **Fields**: Private, public, static, readonly, const fields
- **Events**: Event declarations and handlers
- **Constructors**: Instance and static constructors
- **Namespaces**: Nested namespace support
- **Using Directives**: Import statements and aliases

### Advanced C# Features
- **Generics**: Type parameters, constraints, generic methods
- **Async/Await**: Task-based asynchronous patterns
- **LINQ**: Query syntax and method syntax detection
- **Attributes**: Custom and built-in attribute detection
- **Nullable Reference Types**: C# 8.0+ nullable annotations
- **Pattern Matching**: Switch expressions and patterns
- **Records**: Record types and positional parameters

### Project Analysis
- **.NET Framework Detection**: Automatic framework version detection
- **NuGet Package Analysis**: Parse `.csproj` and `packages.config`
- **Project Type Detection**: Console, Web, WPF, WinForms, Blazor
- **MSBuild Integration**: Property and target analysis

## Usage Examples

### Basic Indexing
```python
from mcp_server.plugins.csharp_plugin import Plugin

plugin = Plugin()

# Index a C# file
with open("UserService.cs", "r") as f:
    content = f.read()

result = plugin.indexFile("UserService.cs", content)
symbols = result["symbols"]

# Find all classes
classes = [s for s in symbols if s["kind"] == "class"]
print(f"Found {len(classes)} classes")
```

### Advanced Features
```python
# Get plugin information
info = plugin.get_csharp_info()
print(f"Supports LINQ: {info['language_features']['linq']}")
print(f"Framework support: {info['framework_support']}")

# Get parsing statistics
stats = plugin.get_parsing_statistics()
print(f"Tree-sitter success rate: {stats['tree_sitter_success_rate']:.2%}")
```

### Symbol Analysis
```python
# Analyze symbols with metadata
for symbol in symbols:
    print(f"Symbol: {symbol['name']} ({symbol['kind']})")
    
    if symbol.get("metadata"):
        metadata = symbol["metadata"]
        
        # Check for generics
        if metadata.get("generics"):
            print(f"  Generic: {metadata['generics']['type_parameters']}")
        
        # Check for attributes
        if metadata.get("attributes"):
            print(f"  Attributes: {metadata['attributes']}")
        
        # Check for async
        if "async" in symbol.get("modifiers", set()):
            print(f"  Async method")
        
        # Check for LINQ usage
        if metadata.get("uses_linq"):
            print(f"  Contains LINQ expressions")
```

## Configuration

### Plugin Configuration
```json
{
  "plugin": {
    "name": "csharp",
    "language": "c#",
    "type": "hybrid",
    "extensions": [".cs", ".csx", ".cshtml"]
  },
  "features": {
    "tree_sitter_support": true,
    "caching": true,
    "async_processing": true,
    "semantic_analysis": true
  },
  "performance": {
    "max_file_size": 10485760,
    "cache_ttl": 3600,
    "batch_size": 100,
    "fallback_threshold": 0.15
  }
}
```

### Tree-sitter Queries
The plugin uses sophisticated Tree-sitter queries for accurate parsing:

```scheme
; Classes
(class_declaration
  name: (identifier) @name) @class

; Methods with modifiers
(method_declaration
  (modifier)* @modifiers
  name: (identifier) @name) @method

; Generic types
(type_parameter_list
  (type_parameter
    (identifier) @name)) @generic
```

## Symbol Metadata

### Class Symbols
```json
{
  "name": "UserService",
  "kind": "class",
  "line": 15,
  "signature": "public class UserService : IUserService",
  "modifiers": ["public"],
  "metadata": {
    "inheritance": {
      "base_types": ["IUserService"],
      "has_inheritance": true
    },
    "attributes": ["Service", "Transient"],
    "generics": {
      "is_generic": false
    }
  }
}
```

### Method Symbols
```json
{
  "name": "GetUserAsync",
  "kind": "function",
  "line": 25,
  "signature": "public async Task<User> GetUserAsync(int id)",
  "modifiers": ["public", "async"],
  "metadata": {
    "parameters": [
      {"name": "id", "type": "int"}
    ],
    "uses_linq": false,
    "attributes": ["HttpGet"],
    "generics": {
      "is_generic": false
    }
  }
}
```

### Property Symbols
```json
{
  "name": "UserId",
  "kind": "property",
  "line": 10,
  "signature": "public int UserId { get; set; }",
  "modifiers": ["public"],
  "metadata": {
    "attributes": ["Key", "Required"],
    "property_type": "auto_implemented"
  }
}
```

## Project Context Analysis

### .csproj Parsing
The plugin automatically analyzes `.csproj` files to extract:
- Target framework version
- Package references
- Project type (Console, Web, WPF, etc.)
- Build properties

### Example Project Metadata
```json
{
  "framework_version": "net8.0",
  "target_framework": "net8.0",
  "project_type": "web",
  "packages": [
    "Microsoft.AspNetCore.OpenApi:8.0.0",
    "EntityFramework:6.4.4",
    "Newtonsoft.Json:13.0.3"
  ]
}
```

## Performance Optimization

### Hybrid Parsing Strategy
1. **Primary**: Tree-sitter parsing for accurate AST analysis
2. **Fallback**: Regex patterns when Tree-sitter fails or finds insufficient symbols
3. **Threshold**: Falls back if Tree-sitter finds < 15% expected symbols

### Caching Strategy
- Project information caching
- Pattern compilation caching
- Symbol result caching with TTL

### Memory Management
- Incremental parsing for large files
- Lazy loading of project context
- Efficient regex compilation

## Error Handling

### Graceful Degradation
- Malformed syntax handling
- Partial symbol extraction
- Robust error recovery

### Logging
- Debug-level parsing statistics
- Warning-level fallback notifications
- Error-level parsing failures

## Testing

### Test Coverage
- Basic symbol extraction
- Advanced C# features (generics, async, LINQ)
- Project file parsing
- Blazor component support
- Error handling and robustness

### Test Files
- `SampleClass.cs`: Comprehensive example with ASP.NET patterns
- `Program.cs`: Console application with async/LINQ
- `BlazorComponent.cshtml`: Blazor component example
- `Test.csproj`: Sample project file

## Integration

### MCP Server Integration
The plugin integrates seamlessly with the MCP server infrastructure:
- Symbol indexing
- Search functionality
- Real-time analysis
- Project monitoring

### Tool Integration
Works with MCP tools for:
- Symbol lookup
- Code navigation
- Refactoring support
- Documentation generation

## Best Practices

### For Developers
1. Use meaningful symbol names
2. Add XML documentation comments
3. Follow C# naming conventions
4. Use appropriate access modifiers

### For Plugin Users
1. Ensure Tree-sitter grammar is available
2. Configure appropriate cache TTL
3. Monitor parsing statistics
4. Adjust fallback threshold for specific codebases

## Troubleshooting

### Common Issues
1. **Tree-sitter not available**: Install `tree-sitter-c-sharp`
2. **Low symbol detection**: Check fallback threshold
3. **Project info missing**: Verify `.csproj` file location
4. **Performance issues**: Adjust cache settings

### Debug Information
Use `get_parsing_statistics()` to analyze plugin performance:
- Tree-sitter success rate
- Fallback usage
- Processing times
- Memory usage