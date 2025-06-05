#!/usr/bin/env python3
"""
Simple test for TOML and Lua plugins using real-world repositories.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add the mcp_server to Python path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))

from mcp_server.plugins.toml_plugin.plugin import Plugin as TomlPlugin
from mcp_server.plugins.lua_plugin.plugin import Plugin as LuaPlugin


class SimplePluginTester:
    """Simple test for TOML and Lua plugins."""
    
    def __init__(self):
        """Initialize tester with plugins."""
        # Initialize plugins without SQLite for simplicity
        self.toml_plugin = TomlPlugin()
        self.lua_plugin = LuaPlugin()  # Don't pass SQLite store
        
        # Test repositories
        self.test_repos_dir = Path("test_repos")
        self.results = {
            "toml_tests": [],
            "lua_tests": [],
            "summary": {}
        }
    
    def run_tests(self):
        """Run tests and generate report."""
        print("🚀 Starting TOML and Lua plugin testing...")
        
        # Test TOML files
        self.test_toml_files()
        
        # Test Lua files  
        self.test_lua_files()
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        self.save_results()
        
        print("✅ Tests completed!")
        return self.results
    
    def test_toml_files(self):
        """Test TOML plugin on various TOML files."""
        print("\n📋 Testing TOML plugin...")
        
        # Find specific TOML files
        test_files = [
            # Cargo.toml files
            *list(self.test_repos_dir.rglob("Cargo.toml")),
            # Python project files
            *list(self.test_repos_dir.rglob("pyproject.toml")),
            # Other TOML files
            *list(self.test_repos_dir.rglob("*.toml"))
        ]
        
        print(f"Found {len(test_files)} TOML files")
        
        for toml_file in test_files[:8]:  # Test first 8 for demo
            try:
                content = toml_file.read_text(encoding='utf-8')
                
                # Test if plugin supports file
                supports = self.toml_plugin.supports(toml_file)
                
                if supports:
                    # Index the file
                    shard = self.toml_plugin.indexFile(str(toml_file), content)
                    
                    # Analyze results
                    file_type = self._classify_toml_file(toml_file)
                    symbols_count = len(shard.get("symbols", []))
                    
                    # Get sample symbols
                    sample_symbols = []
                    for symbol in shard.get("symbols", [])[:3]:
                        sample_symbols.append({
                            "name": symbol.get("symbol", ""),
                            "kind": symbol.get("kind", ""),
                            "line": symbol.get("line", 0),
                            "signature": symbol.get("signature", "")
                        })
                    
                    test_result = {
                        "file": str(toml_file.relative_to(Path.cwd())),
                        "file_type": file_type,
                        "supports": supports,
                        "symbols_count": symbols_count,
                        "sample_symbols": sample_symbols,
                        "frameworks_detected": self._detect_toml_frameworks(content)
                    }
                    
                    self.results["toml_tests"].append(test_result)
                    
                    print(f"  ✓ {toml_file.name}: {symbols_count} symbols ({file_type})")
                
            except Exception as e:
                print(f"  ❌ Error processing {toml_file.name}: {e}")
    
    def test_lua_files(self):
        """Test Lua plugin on various Lua files."""
        print("\n🌙 Testing Lua plugin...")
        
        # Find specific Lua files
        test_files = [
            # Kong files
            *list(self.test_repos_dir.rglob("**/kong/**/*.lua")),
            # Love2D files
            *list(self.test_repos_dir.rglob("**/love/**/*.lua")),
            # OpenResty files
            *list(self.test_repos_dir.rglob("**/resty/**/*.lua")),
            # General Lua files
            *list(self.test_repos_dir.rglob("*.lua")),
            # Rockspec files
            *list(self.test_repos_dir.rglob("*.rockspec"))
        ]
        
        # Remove duplicates
        test_files = list(set(test_files))
        
        print(f"Found {len(test_files)} Lua files")
        
        for lua_file in test_files[:10]:  # Test first 10 for demo
            try:
                content = lua_file.read_text(encoding='utf-8')
                
                # Test if plugin supports file
                supports = self.lua_plugin.supports(lua_file)
                
                if supports:
                    # Index the file
                    shard = self.lua_plugin.indexFile(str(lua_file), content)
                    
                    # Analyze results
                    file_type = self._classify_lua_file(lua_file)
                    symbols_count = len(shard.get("symbols", []))
                    
                    # Get symbol type breakdown
                    symbol_types = {}
                    sample_symbols = []
                    for symbol in shard.get("symbols", []):
                        kind = symbol.get("kind", "unknown")
                        symbol_types[kind] = symbol_types.get(kind, 0) + 1
                        
                        # Add to sample if we have less than 3
                        if len(sample_symbols) < 3:
                            sample_symbols.append({
                                "name": symbol.get("symbol", ""),
                                "kind": kind,
                                "line": symbol.get("line", 0),
                                "signature": symbol.get("signature", "")
                            })
                    
                    test_result = {
                        "file": str(lua_file.relative_to(Path.cwd())),
                        "file_type": file_type,
                        "supports": supports,
                        "symbols_count": symbols_count,
                        "symbol_types": symbol_types,
                        "sample_symbols": sample_symbols,
                        "frameworks_detected": self._detect_lua_frameworks(content)
                    }
                    
                    self.results["lua_tests"].append(test_result)
                    
                    print(f"  ✓ {lua_file.name}: {symbols_count} symbols ({file_type})")
                
            except Exception as e:
                print(f"  ❌ Error processing {lua_file.name}: {e}")
    
    def _classify_toml_file(self, file_path: Path) -> str:
        """Classify TOML file type."""
        name = file_path.name.lower()
        if name == "cargo.toml":
            return "rust_project"
        elif name == "pyproject.toml":
            return "python_project"
        elif name.endswith(".lock"):
            return "lock_file"
        elif "config" in name:
            return "configuration"
        else:
            return "general_toml"
    
    def _classify_lua_file(self, file_path: Path) -> str:
        """Classify Lua file type."""
        name = file_path.name.lower()
        path_str = str(file_path).lower()
        
        if name.endswith(".rockspec"):
            return "luarocks_spec"
        elif "kong" in path_str:
            return "kong_plugin"
        elif "love" in path_str or name in ["main.lua", "conf.lua"]:
            return "love2d_game"
        elif "resty" in path_str or "openresty" in path_str:
            return "openresty_module"
        elif name == "init.lua":
            return "module_init"
        else:
            return "general_lua"
    
    def _detect_toml_frameworks(self, content: str) -> List[str]:
        """Detect frameworks from TOML content."""
        frameworks = []
        content_lower = content.lower()
        
        if "cargo" in content_lower or "[package]" in content_lower:
            frameworks.append("rust")
        if "poetry" in content_lower:
            frameworks.append("poetry")
        if "setuptools" in content_lower or "[project]" in content_lower:
            frameworks.append("setuptools")
        if "black" in content_lower:
            frameworks.append("black")
        if "pytest" in content_lower:
            frameworks.append("pytest")
        if "ruff" in content_lower:
            frameworks.append("ruff")
        
        return frameworks
    
    def _detect_lua_frameworks(self, content: str) -> List[str]:
        """Detect frameworks from Lua content."""
        frameworks = []
        
        if "love." in content or "function love." in content:
            frameworks.append("love2d")
        if "ngx." in content or "resty." in content:
            frameworks.append("openresty")
        if "kong." in content:
            frameworks.append("kong")
        if 'require("ffi")' in content or "require 'ffi'" in content:
            frameworks.append("luajit")
        if "coroutine." in content:
            frameworks.append("coroutines")
        if "setmetatable" in content:
            frameworks.append("oop")
        
        return frameworks
    
    def generate_summary(self):
        """Generate test summary."""
        # Calculate statistics
        toml_symbols = sum(test["symbols_count"] for test in self.results["toml_tests"])
        lua_symbols = sum(test["symbols_count"] for test in self.results["lua_tests"])
        
        # Count by file types
        toml_by_type = {}
        for test in self.results["toml_tests"]:
            file_type = test["file_type"]
            toml_by_type[file_type] = toml_by_type.get(file_type, 0) + 1
        
        lua_by_type = {}
        for test in self.results["lua_tests"]:
            file_type = test["file_type"]
            lua_by_type[file_type] = lua_by_type.get(file_type, 0) + 1
        
        # Count frameworks
        all_toml_frameworks = []
        for test in self.results["toml_tests"]:
            all_toml_frameworks.extend(test["frameworks_detected"])
        
        all_lua_frameworks = []
        for test in self.results["lua_tests"]:
            all_lua_frameworks.extend(test["frameworks_detected"])
        
        summary = {
            "toml_files_tested": len(self.results["toml_tests"]),
            "lua_files_tested": len(self.results["lua_tests"]),
            "total_symbols_toml": toml_symbols,
            "total_symbols_lua": lua_symbols,
            "toml_files_by_type": toml_by_type,
            "lua_files_by_type": lua_by_type,
            "toml_frameworks": list(set(all_toml_frameworks)),
            "lua_frameworks": list(set(all_lua_frameworks))
        }
        
        self.results["summary"] = summary
        
        print(f"\n📊 Test Summary:")
        print(f"  TOML files tested: {summary['toml_files_tested']}")
        print(f"  Lua files tested: {summary['lua_files_tested']}")
        print(f"  Total TOML symbols: {summary['total_symbols_toml']}")
        print(f"  Total Lua symbols: {summary['total_symbols_lua']}")
        print(f"  TOML frameworks: {', '.join(summary['toml_frameworks'])}")
        print(f"  Lua frameworks: {', '.join(summary['lua_frameworks'])}")
        
        # Show file type breakdown
        print(f"\n📂 File Type Breakdown:")
        for file_type, count in toml_by_type.items():
            print(f"  TOML {file_type}: {count}")
        for file_type, count in lua_by_type.items():
            print(f"  Lua {file_type}: {count}")
    
    def save_results(self):
        """Save test results to JSON file."""
        results_file = Path("simple_toml_lua_test_results.json")
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
    
    def show_detailed_results(self):
        """Show detailed test results."""
        print(f"\n🔍 Detailed Results:")
        
        print(f"\n📋 TOML Files:")
        for test in self.results["toml_tests"]:
            print(f"  {test['file']} ({test['file_type']})")
            print(f"    Symbols: {test['symbols_count']}")
            if test['frameworks_detected']:
                print(f"    Frameworks: {', '.join(test['frameworks_detected'])}")
            if test['sample_symbols']:
                print(f"    Sample symbols:")
                for symbol in test['sample_symbols']:
                    print(f"      - {symbol['name']} ({symbol['kind']}) line {symbol['line']}")
        
        print(f"\n🌙 Lua Files:")
        for test in self.results["lua_tests"]:
            print(f"  {test['file']} ({test['file_type']})")
            print(f"    Symbols: {test['symbols_count']}")
            if test['frameworks_detected']:
                print(f"    Frameworks: {', '.join(test['frameworks_detected'])}")
            if test['symbol_types']:
                types_str = ', '.join(f"{k}:{v}" for k, v in test['symbol_types'].items())
                print(f"    Symbol types: {types_str}")
            if test['sample_symbols']:
                print(f"    Sample symbols:")
                for symbol in test['sample_symbols']:
                    print(f"      - {symbol['name']} ({symbol['kind']}) line {symbol['line']}")


def main():
    """Run the test suite."""
    tester = SimplePluginTester()
    results = tester.run_tests()
    
    # Show detailed results
    tester.show_detailed_results()
    
    print(f"\n🎉 Testing completed! Check 'simple_toml_lua_test_results.json' for detailed results.")
    
    return results


if __name__ == "__main__":
    main()