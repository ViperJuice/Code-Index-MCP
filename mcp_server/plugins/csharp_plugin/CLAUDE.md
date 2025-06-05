# C# Plugin - Claude Integration Guide

## Overview
This C# plugin provides comprehensive C# language support for the Code-Index-MCP system, specifically designed to work seamlessly with Claude Code for advanced code analysis and assistance.

## Claude Code Integration

### Symbol Analysis with Claude
Claude can leverage the rich symbol information extracted by this plugin:

```python
# Example: Getting detailed symbol analysis
result = plugin.indexFile("UserController.cs", content)
symbols = result["symbols"]

for symbol in symbols:
    if symbol["kind"] == "function" and "async" in symbol.get("modifiers", set()):
        # Claude can identify this as an async method
        print(f"Async method: {symbol['name']}")
        
        # Access parameter information
        if symbol.get("metadata", {}).get("parameters"):
            params = symbol["metadata"]["parameters"]
            print(f"Parameters: {[p['name'] + ': ' + p['type'] for p in params]}")
```

### Project Context for Claude
The plugin provides project-level context that Claude can use for better code understanding:

```python
# Project information available to Claude
symbols_with_context = []
for symbol in symbols:
    metadata = symbol.get("metadata", {})
    if metadata.get("target_framework"):
        # Claude knows this is a .NET 8.0 project
        print(f"Framework: {metadata['target_framework']}")
    
    if metadata.get("project_type") == "web":
        # Claude can provide ASP.NET-specific guidance
        print("This is a web application")
```

## Advanced Features for Claude Analysis

### 1. Generic Type Analysis
```python
# Claude can understand generic constraints and usage
def analyze_generics(symbol):
    if symbol.get("metadata", {}).get("generics"):
        generic_info = symbol["metadata"]["generics"]
        if generic_info["is_generic"]:
            type_params = generic_info["type_parameters"]
            return f"Generic type with parameters: {', '.join(type_params)}"
    return "Non-generic type"
```

### 2. Async Pattern Detection
```python
# Claude can identify async/await patterns
def find_async_patterns(symbols):
    async_methods = []
    for symbol in symbols:
        if (symbol["kind"] == "function" and 
            "async" in symbol.get("modifiers", set())):
            async_methods.append(symbol)
    return async_methods
```

### 3. LINQ Usage Analysis
```python
# Claude can detect LINQ usage for optimization suggestions
def analyze_linq_usage(symbols):
    linq_methods = []
    for symbol in symbols:
        if symbol.get("metadata", {}).get("uses_linq"):
            linq_methods.append(symbol["name"])
    return linq_methods
```

### 4. Attribute-based Architecture Analysis
```python
# Claude can understand attribute-driven architectures
def analyze_attributes(symbols):
    controller_methods = []
    for symbol in symbols:
        attributes = symbol.get("metadata", {}).get("attributes", [])
        if any(attr.startswith("Http") for attr in attributes):
            controller_methods.append({
                "name": symbol["name"],
                "http_methods": [attr for attr in attributes if attr.startswith("Http")]
            })
    return controller_methods
```

## Claude Code Use Cases

### 1. Code Review Assistance
Claude can use symbol metadata to provide intelligent code reviews:

```python
def review_code_quality(symbols):
    issues = []
    
    for symbol in symbols:
        # Check for missing async suffix
        if (symbol["kind"] == "function" and 
            "async" in symbol.get("modifiers", set()) and
            not symbol["name"].endswith("Async")):
            issues.append(f"Method {symbol['name']} should end with 'Async'")
        
        # Check for missing XML documentation
        if (symbol["kind"] in ["class", "function"] and 
            not symbol.get("docstring")):
            issues.append(f"{symbol['kind']} {symbol['name']} missing documentation")
    
    return issues
```

### 2. Architecture Analysis
Claude can analyze project architecture patterns:

```python
def analyze_architecture(symbols):
    patterns = {
        "controllers": [],
        "services": [],
        "repositories": [],
        "dtos": []
    }
    
    for symbol in symbols:
        if symbol["kind"] == "class":
            name = symbol["name"]
            if name.endswith("Controller"):
                patterns["controllers"].append(name)
            elif name.endswith("Service"):
                patterns["services"].append(name)
            elif name.endswith("Repository"):
                patterns["repositories"].append(name)
            elif name.endswith("Dto") or name.endswith("DTO"):
                patterns["dtos"].append(name)
    
    return patterns
```

### 3. Dependency Analysis
Claude can analyze project dependencies:

```python
def analyze_dependencies(symbols):
    dependencies = {
        "framework_dependencies": set(),
        "external_packages": set(),
        "internal_dependencies": set()
    }
    
    for symbol in symbols:
        if symbol["kind"] == "import":
            namespace = symbol["name"]
            if namespace.startswith("System"):
                dependencies["framework_dependencies"].add(namespace)
            elif "." in namespace and not namespace.startswith("System"):
                dependencies["external_packages"].add(namespace.split(".")[0])
    
    return dependencies
```

### 4. Performance Analysis
Claude can identify potential performance issues:

```python
def analyze_performance(symbols):
    performance_issues = []
    
    for symbol in symbols:
        # Check for synchronous methods that could be async
        if (symbol["kind"] == "function" and
            "async" not in symbol.get("modifiers", set()) and
            any(keyword in symbol.get("signature", "") for keyword in 
                ["Database", "Http", "File", "Stream"])):
            performance_issues.append(f"Method {symbol['name']} might benefit from async")
        
        # Check for LINQ in tight loops (would need more context)
        if symbol.get("metadata", {}).get("uses_linq"):
            performance_issues.append(f"Method {symbol['name']} uses LINQ - review for performance")
    
    return performance_issues
```

### 5. Security Analysis
Claude can identify potential security issues:

```python
def analyze_security(symbols):
    security_issues = []
    
    for symbol in symbols:
        attributes = symbol.get("metadata", {}).get("attributes", [])
        
        # Check for missing authorization on controller actions
        if (symbol["kind"] == "function" and
            any(attr.startswith("Http") for attr in attributes) and
            not any(attr.startswith("Authorize") for attr in attributes)):
            security_issues.append(f"Action {symbol['name']} may need authorization")
        
        # Check for potential SQL injection (basic check)
        signature = symbol.get("signature", "")
        if "string" in signature and any(keyword in signature.lower() for keyword in 
                                       ["sql", "query", "command"]):
            security_issues.append(f"Method {symbol['name']} may be vulnerable to SQL injection")
    
    return security_issues
```

## Integration Examples

### Complete Analysis Pipeline
```python
def complete_csharp_analysis(file_path, content):
    """Complete C# file analysis for Claude Code."""
    plugin = Plugin()
    result = plugin.indexFile(file_path, content)
    
    analysis = {
        "basic_info": {
            "language": result["language"],
            "symbol_count": len(result["symbols"]),
            "file_path": file_path
        },
        "symbols": result["symbols"],
        "code_quality": review_code_quality(result["symbols"]),
        "architecture": analyze_architecture(result["symbols"]),
        "dependencies": analyze_dependencies(result["symbols"]),
        "performance": analyze_performance(result["symbols"]),
        "security": analyze_security(result["symbols"]),
        "async_patterns": find_async_patterns(result["symbols"]),
        "linq_usage": analyze_linq_usage(result["symbols"])
    }
    
    return analysis
```

### Claude Response Generation
```python
def generate_claude_response(analysis):
    """Generate structured response for Claude Code."""
    response = []
    
    # Basic overview
    basic = analysis["basic_info"]
    response.append(f"Analyzed {basic['symbol_count']} symbols in {basic['file_path']}")
    
    # Architecture summary
    arch = analysis["architecture"]
    if arch["controllers"]:
        response.append(f"Found {len(arch['controllers'])} controllers")
    if arch["services"]:
        response.append(f"Found {len(arch['services'])} services")
    
    # Issues summary
    issues = analysis["code_quality"] + analysis["performance"] + analysis["security"]
    if issues:
        response.append(f"Identified {len(issues)} potential issues:")
        response.extend(f"  - {issue}" for issue in issues[:5])  # Top 5 issues
    
    # Advanced features
    if analysis["async_patterns"]:
        response.append(f"Uses async/await patterns in {len(analysis['async_patterns'])} methods")
    
    if analysis["linq_usage"]:
        response.append(f"LINQ usage detected in {len(analysis['linq_usage'])} methods")
    
    return "\n".join(response)
```

## Configuration for Claude Code

### Recommended Settings
```json
{
  "csharp_plugin": {
    "enable_project_analysis": true,
    "cache_project_info": true,
    "detailed_metadata": true,
    "security_analysis": true,
    "performance_hints": true
  }
}
```

### Performance Tuning for Claude Workloads
```python
# Optimize for Claude Code usage
config = PluginConfig(
    enable_caching=True,
    cache_ttl=7200,  # 2 hours for Claude sessions
    enable_fallback=True,
    fallback_threshold=0.1,  # Lower threshold for better coverage
    max_file_size=20 * 1024 * 1024  # 20MB for large files
)

plugin = Plugin(config=config)
```

## Best Practices for Claude Integration

### 1. Symbol Filtering
Filter symbols based on Claude's current context:
```python
def filter_symbols_for_claude(symbols, context="all"):
    if context == "public_api":
        return [s for s in symbols if "public" in s.get("modifiers", set())]
    elif context == "methods_only":
        return [s for s in symbols if s["kind"] == "function"]
    return symbols
```

### 2. Contextual Analysis
Provide context-aware analysis:
```python
def contextual_analysis(symbols, file_type):
    if file_type == "controller":
        return analyze_controller_patterns(symbols)
    elif file_type == "service":
        return analyze_service_patterns(symbols)
    elif file_type == "model":
        return analyze_model_patterns(symbols)
    return general_analysis(symbols)
```

### 3. Progressive Disclosure
Provide information at different levels of detail:
```python
def get_symbol_summary(symbol, detail_level="basic"):
    summary = {
        "name": symbol["name"],
        "kind": symbol["kind"],
        "line": symbol["line"]
    }
    
    if detail_level in ["intermediate", "full"]:
        summary["modifiers"] = list(symbol.get("modifiers", set()))
        summary["signature"] = symbol.get("signature")
    
    if detail_level == "full":
        summary["metadata"] = symbol.get("metadata", {})
        summary["docstring"] = symbol.get("docstring")
    
    return summary
```

This integration guide enables Claude Code to provide sophisticated C# code analysis, suggestions, and assistance by leveraging the comprehensive symbol information and metadata extracted by the C# plugin.