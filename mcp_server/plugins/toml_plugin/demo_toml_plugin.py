#!/usr/bin/env python3
"""Demonstration of the TOML plugin capabilities."""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mcp_server.plugins.toml_plugin import Plugin
from pprint import pprint


def demo_toml_plugin():
    """Demonstrate TOML plugin features."""
    plugin = Plugin()
    
    # Example 1: Parse a simple TOML file
    print("=== Example 1: Simple TOML Parsing ===")
    simple_toml = """
[server]
host = "localhost"
port = 8080

[database]
url = "postgresql://localhost/mydb"
pool_size = 10
"""
    
    result = plugin.indexFile("config.toml", simple_toml)
    print(f"Found {len(result['symbols'])} symbols:")
    for symbol in result['symbols']:
        print(f"  {symbol['symbol']} ({symbol['kind']}) at line {symbol['line']}")
    
    # Example 2: Parse Cargo.toml
    print("\n=== Example 2: Cargo.toml Parsing ===")
    cargo_toml = """
[package]
name = "my-app"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
tokio = "1.0"

[features]
default = ["serde/derive"]
async = ["tokio"]
"""
    
    result = plugin.indexFile("Cargo.toml", cargo_toml)
    
    # Show package metadata
    print("\nPackage metadata:")
    for symbol in result['symbols']:
        if symbol.get('metadata', {}).get('cargo_field'):
            print(f"  {symbol['symbol']}: {symbol['metadata']['value']}")
    
    # Show dependencies
    print("\nDependencies:")
    for symbol in result['symbols']:
        if symbol.get('metadata', {}).get('is_dependency'):
            print(f"  {symbol['metadata']['dependency']}")
    
    # Show features
    print("\nFeatures:")
    for symbol in result['symbols']:
        if symbol.get('metadata', {}).get('feature'):
            deps = symbol['metadata']['dependencies']
            print(f"  {symbol['metadata']['feature']}: {deps}")
    
    # Example 3: pyproject.toml parsing
    print("\n=== Example 3: pyproject.toml Parsing ===")
    pyproject_toml = """
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-python-package"
version = "0.1.0"
requires-python = ">=3.8"

[tool.black]
line-length = 88

[tool.mypy]
python_version = "3.8"
"""
    
    result = plugin.indexFile("pyproject.toml", pyproject_toml)
    
    # Show project fields
    print("\nProject metadata:")
    for symbol in result['symbols']:
        if symbol.get('metadata', {}).get('project_field'):
            print(f"  {symbol['metadata']['project_field']}")
    
    # Show tool configurations
    print("\nTool configurations:")
    for symbol in result['symbols']:
        if symbol.get('metadata', {}).get('is_tool_config'):
            print(f"  {symbol['symbol']} (tool: {symbol['metadata']['tool']})")
    
    # Example 4: Nested structures with key paths
    print("\n=== Example 4: Nested Structures ===")
    nested_toml = """
[server]
host = "localhost"

[server.database]
host = "db.example.com"
port = 5432

[server.database.pool]
min_size = 5
max_size = 20
"""
    
    result = plugin.indexFile("nested.toml", nested_toml)
    
    print("\nKey paths:")
    for symbol in result['symbols']:
        metadata = symbol.get('metadata', {})
        if 'full_path' in metadata:
            print(f"  {metadata['full_path']} (parent: {metadata.get('parent_path', 'root')})")
    
    # Example 5: Search functionality
    print("\n=== Example 5: Search Functionality ===")
    # Index a file first
    plugin.indexFile("test.toml", cargo_toml)
    
    # Search for "serde"
    results = plugin.search("serde")
    print(f"\nSearch results for 'serde': {len(results)} found")
    
    # Get definition
    definition = plugin.getDefinition("dependencies.serde")
    if definition:
        print(f"\nDefinition of 'dependencies.serde':")
        print(f"  Kind: {definition['kind']}")
        print(f"  Line: {definition['line']}")
        if 'value_type' in definition:
            print(f"  Value type: {definition['value_type']}")


if __name__ == "__main__":
    demo_toml_plugin()