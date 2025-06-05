#!/usr/bin/env python3
"""
Targeted test for TOML and Lua plugins on specific files.
"""

import json
import sys
from pathlib import Path

# Add the mcp_server to Python path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))

from mcp_server.plugins.toml_plugin.plugin import Plugin as TomlPlugin
from mcp_server.plugins.lua_plugin.plugin import Plugin as LuaPlugin


def test_toml_plugin():
    """Test TOML plugin on specific files."""
    print("📋 Testing TOML Plugin")
    print("=" * 50)
    
    plugin = TomlPlugin()
    results = []
    
    # Test files
    test_files = [
        "test_repos/fastapi/pyproject.toml",
        "test_repos/django/pyproject.toml", 
        "test_repos/requests/pyproject.toml",
        "test_repos/pandoc-converter/cabal.project"
    ]
    
    for file_path in test_files:
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"❌ File not found: {file_path}")
                continue
            
            content = path.read_text(encoding='utf-8')
            
            # Test plugin support
            supports = plugin.supports(path)
            print(f"\n📄 Testing: {path.name}")
            print(f"   Supports: {supports}")
            
            if supports:
                # Index the file
                shard = plugin.indexFile(str(path), content)
                symbols = shard.get("symbols", [])
                
                print(f"   Symbols found: {len(symbols)}")
                
                # Show first few symbols
                for i, symbol in enumerate(symbols[:5]):
                    print(f"   Symbol {i+1}: {symbol.get('symbol', 'N/A')} ({symbol.get('kind', 'N/A')}) line {symbol.get('line', 'N/A')}")
                
                # Test search functionality
                if symbols:
                    search_results = plugin.search("name")
                    print(f"   Search 'name' results: {len(search_results)}")
                
                results.append({
                    "file": str(path),
                    "symbols_count": len(symbols),
                    "supports": supports,
                    "symbols": symbols[:3]  # First 3 symbols
                })
            
        except Exception as e:
            print(f"❌ Error testing {file_path}: {e}")
    
    return results


def test_lua_plugin():
    """Test Lua plugin on specific files."""
    print("\n🌙 Testing Lua Plugin")
    print("=" * 50)
    
    plugin = LuaPlugin()  # No SQLite store to avoid initialization issues
    results = []
    
    # Test files
    test_files = [
        "test_repos/lua/kong/kong-3.10.0-0.rockspec",
        "test_repos/pandoc-converter/tools/moduledeps.lua",
        "test_repos/pandoc-converter/data/init.lua"
    ]
    
    # Also look for specific Lua files that exist
    additional_files = []
    for pattern in ["**/*.lua", "**/*.rockspec"]:
        for lua_file in Path("test_repos").rglob(pattern):
            if lua_file.is_file() and len(additional_files) < 3:
                additional_files.append(str(lua_file))
    
    test_files.extend(additional_files)
    
    for file_path in test_files[:6]:  # Test first 6 files
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"❌ File not found: {file_path}")
                continue
            
            content = path.read_text(encoding='utf-8')
            
            # Test plugin support
            supports = plugin.supports(path)
            print(f"\n📄 Testing: {path.name}")
            print(f"   Path: {path}")
            print(f"   Supports: {supports}")
            
            if supports:
                # Index the file
                shard = plugin.indexFile(str(path), content)
                symbols = shard.get("symbols", [])
                
                print(f"   Symbols found: {len(symbols)}")
                
                # Get symbol type breakdown
                symbol_types = {}
                for symbol in symbols:
                    kind = symbol.get("kind", "unknown")
                    symbol_types[kind] = symbol_types.get(kind, 0) + 1
                
                if symbol_types:
                    print(f"   Symbol types: {dict(symbol_types)}")
                
                # Show first few symbols
                for i, symbol in enumerate(symbols[:5]):
                    print(f"   Symbol {i+1}: {symbol.get('symbol', 'N/A')} ({symbol.get('kind', 'N/A')}) line {symbol.get('line', 'N/A')}")
                
                # Test search functionality
                if symbols:
                    search_results = plugin.search("function")
                    print(f"   Search 'function' results: {len(search_results)}")
                
                results.append({
                    "file": str(path),
                    "symbols_count": len(symbols),
                    "symbol_types": symbol_types,
                    "supports": supports,
                    "symbols": symbols[:3]  # First 3 symbols
                })
            
        except Exception as e:
            print(f"❌ Error testing {file_path}: {e}")
    
    return results


def test_specific_features():
    """Test specific TOML and Lua features."""
    print("\n🔧 Testing Specific Features")
    print("=" * 50)
    
    # Test TOML Cargo.toml parsing
    print("\n📦 Testing Cargo.toml parsing:")
    cargo_content = '''
[package]
name = "my-project"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
tokio = "1.0"

[features]
default = ["serde"]
full = ["tokio", "serde"]
'''
    
    toml_plugin = TomlPlugin()
    shard = toml_plugin.indexFile("test.toml", cargo_content)
    print(f"Cargo.toml symbols: {len(shard['symbols'])}")
    for symbol in shard['symbols']:
        print(f"  - {symbol.get('symbol', 'N/A')} ({symbol.get('kind', 'N/A')})")
    
    # Test Lua function parsing
    print("\n🔧 Testing Lua function parsing:")
    lua_content = '''
-- Kong plugin example
local kong = require "kong"
local BasePlugin = require "kong.plugins.base_plugin"

local MyPlugin = BasePlugin:extend()

function MyPlugin:new()
    MyPlugin.super.new(self, "my-plugin")
end

function MyPlugin:access(conf)
    kong.log.debug("MyPlugin access")
    
    local function helper_func(param)
        return param * 2
    end
    
    return helper_func(42)
end

local function love.load()
    print("Love2D game loaded")
end

return MyPlugin
'''
    
    lua_plugin = LuaPlugin()
    shard = lua_plugin.indexFile("test.lua", lua_content)
    print(f"Lua symbols: {len(shard['symbols'])}")
    for symbol in shard['symbols']:
        print(f"  - {symbol.get('symbol', 'N/A')} ({symbol.get('kind', 'N/A')}) scope: {symbol.get('scope', 'N/A')}")


def main():
    """Run all tests."""
    print("🚀 Targeted Plugin Testing")
    print("=" * 70)
    
    # Test TOML plugin
    toml_results = test_toml_plugin()
    
    # Test Lua plugin
    lua_results = test_lua_plugin()
    
    # Test specific features
    test_specific_features()
    
    # Summary
    print("\n📊 Summary")
    print("=" * 50)
    print(f"TOML files tested: {len(toml_results)}")
    print(f"Lua files tested: {len(lua_results)}")
    
    total_toml_symbols = sum(r["symbols_count"] for r in toml_results)
    total_lua_symbols = sum(r["symbols_count"] for r in lua_results)
    
    print(f"Total TOML symbols: {total_toml_symbols}")
    print(f"Total Lua symbols: {total_lua_symbols}")
    
    # Save results
    results = {
        "toml_results": toml_results,
        "lua_results": lua_results,
        "summary": {
            "toml_files": len(toml_results),
            "lua_files": len(lua_results),
            "total_toml_symbols": total_toml_symbols,
            "total_lua_symbols": total_lua_symbols
        }
    }
    
    with open("targeted_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: targeted_test_results.json")
    print("✅ Testing completed!")


if __name__ == "__main__":
    main()