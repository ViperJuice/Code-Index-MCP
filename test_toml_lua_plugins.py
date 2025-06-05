#!/usr/bin/env python3
"""
Comprehensive test for TOML and Lua plugins using real-world repositories.

Tests:
1. TOML plugin on Cargo.toml files (Rust repositories)
2. Lua plugin on Lua files (Kong, Love2D, OpenResty)
3. Cross-language project analysis
4. Framework detection
5. Symbol extraction and searching
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add the mcp_server to Python path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))

from mcp_server.plugins.toml_plugin.plugin import Plugin as TomlPlugin
from mcp_server.plugins.lua_plugin.plugin import Plugin as LuaPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


class RepositoryTester:
    """Test TOML and Lua plugins on real repositories."""
    
    def __init__(self):
        """Initialize tester with plugins."""
        # Initialize SQLite store
        self.sqlite_store = SQLiteStore(":memory:")
        
        # Initialize plugins
        self.toml_plugin = TomlPlugin()
        self.lua_plugin = LuaPlugin(sqlite_store=self.sqlite_store)
        
        # Test repositories
        self.test_repos_dir = Path("test_repos")
        self.results = {
            "toml_tests": [],
            "lua_tests": [],
            "framework_detections": {},
            "cross_language_analysis": [],
            "summary": {}
        }
    
    def run_all_tests(self):
        """Run all tests and generate report."""
        print("🚀 Starting comprehensive TOML and Lua plugin testing...")
        
        # Test TOML files
        self.test_toml_files()
        
        # Test Lua files  
        self.test_lua_files()
        
        # Test framework detection
        self.test_framework_detection()
        
        # Test cross-language analysis
        self.test_cross_language_analysis()
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        self.save_results()
        
        print("✅ All tests completed!")
        return self.results
    
    def test_toml_files(self):
        """Test TOML plugin on various TOML files."""
        print("\n📋 Testing TOML plugin...")
        
        # Find all TOML files
        toml_files = list(self.test_repos_dir.rglob("*.toml"))
        toml_files.extend(list(self.test_repos_dir.rglob("*.lock")))
        
        print(f"Found {len(toml_files)} TOML files")
        
        for toml_file in toml_files[:10]:  # Test first 10 for demo
            try:
                content = toml_file.read_text(encoding='utf-8')
                
                # Test if plugin supports file
                supports = self.toml_plugin.supports(toml_file)
                
                if supports:
                    # Index the file
                    shard = self.toml_plugin.indexFile(toml_file, content)
                    
                    # Analyze results
                    file_type = self._classify_toml_file(toml_file)
                    symbols_count = len(shard.get("symbols", []))
                    
                    test_result = {
                        "file": str(toml_file.relative_to(Path.cwd())),
                        "file_type": file_type,
                        "supports": supports,
                        "symbols_count": symbols_count,
                        "symbols": shard.get("symbols", [])[:5],  # First 5 symbols
                        "frameworks_detected": self._detect_toml_frameworks(toml_file, content)
                    }
                    
                    self.results["toml_tests"].append(test_result)
                    
                    print(f"  ✓ {toml_file.name}: {symbols_count} symbols ({file_type})")
                
            except Exception as e:
                print(f"  ❌ Error processing {toml_file.name}: {e}")
    
    def test_lua_files(self):
        """Test Lua plugin on various Lua files."""
        print("\n🌙 Testing Lua plugin...")
        
        # Find all Lua files
        lua_files = list(self.test_repos_dir.rglob("*.lua"))
        lua_files.extend(list(self.test_repos_dir.rglob("*.rockspec")))
        
        print(f"Found {len(lua_files)} Lua files")
        
        for lua_file in lua_files[:15]:  # Test first 15 for demo
            try:
                content = lua_file.read_text(encoding='utf-8')
                
                # Test if plugin supports file
                supports = self.lua_plugin.supports(lua_file)
                
                if supports:
                    # Index the file
                    shard = self.lua_plugin.indexFile(lua_file, content)
                    
                    # Analyze results
                    file_type = self._classify_lua_file(lua_file)
                    symbols_count = len(shard.get("symbols", []))
                    
                    # Get symbol type breakdown
                    symbol_types = {}
                    for symbol in shard.get("symbols", []):
                        kind = symbol.get("kind", "unknown")
                        symbol_types[kind] = symbol_types.get(kind, 0) + 1
                    
                    test_result = {
                        "file": str(lua_file.relative_to(Path.cwd())),
                        "file_type": file_type,
                        "supports": supports,
                        "symbols_count": symbols_count,
                        "symbol_types": symbol_types,
                        "sample_symbols": shard.get("symbols", [])[:5],  # First 5 symbols
                        "frameworks_detected": self._detect_lua_frameworks(lua_file, content)
                    }
                    
                    self.results["lua_tests"].append(test_result)
                    
                    print(f"  ✓ {lua_file.name}: {symbols_count} symbols ({file_type})")
                
            except Exception as e:
                print(f"  ❌ Error processing {lua_file.name}: {e}")
    
    def test_framework_detection(self):
        """Test framework and project type detection."""
        print("\n🔍 Testing framework detection...")
        
        # Test specific framework detections
        framework_tests = [
            ("Cargo.toml", "rust", self._test_cargo_detection),
            ("pyproject.toml", "python", self._test_pyproject_detection),
            ("love2d", "lua", self._test_love2d_detection),
            ("kong", "lua", self._test_kong_detection),
            ("openresty", "lua", self._test_openresty_detection)
        ]
        
        for framework_name, language, test_func in framework_tests:
            try:
                detection_result = test_func()
                self.results["framework_detections"][framework_name] = {
                    "language": language,
                    "detected": detection_result["detected"],
                    "evidence": detection_result.get("evidence", []),
                    "files_analyzed": detection_result.get("files_analyzed", 0)
                }
                
                status = "✓" if detection_result["detected"] else "○"
                print(f"  {status} {framework_name}: {detection_result['detected']}")
                
            except Exception as e:
                print(f"  ❌ Error testing {framework_name}: {e}")
    
    def test_cross_language_analysis(self):
        """Test cross-language project analysis."""
        print("\n🔗 Testing cross-language analysis...")
        
        # Find mixed-language projects
        projects = self._find_mixed_projects()
        
        for project in projects[:3]:  # Test first 3 projects
            try:
                analysis = self._analyze_mixed_project(project)
                self.results["cross_language_analysis"].append(analysis)
                
                print(f"  ✓ {project['name']}: {', '.join(project['languages'])}")
                
            except Exception as e:
                print(f"  ❌ Error analyzing {project['name']}: {e}")
    
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
    
    def _detect_toml_frameworks(self, file_path: Path, content: str) -> List[str]:
        """Detect frameworks from TOML content."""
        frameworks = []
        
        if "cargo" in content.lower():
            frameworks.append("rust")
        if "poetry" in content.lower():
            frameworks.append("poetry")
        if "setuptools" in content.lower():
            frameworks.append("setuptools")
        if "black" in content.lower():
            frameworks.append("black")
        if "pytest" in content.lower():
            frameworks.append("pytest")
        
        return frameworks
    
    def _detect_lua_frameworks(self, file_path: Path, content: str) -> List[str]:
        """Detect frameworks from Lua content."""
        frameworks = []
        
        if "love." in content:
            frameworks.append("love2d")
        if "ngx." in content or "resty." in content:
            frameworks.append("openresty")
        if "kong." in content:
            frameworks.append("kong")
        if "require(\"ffi\")" in content:
            frameworks.append("luajit")
        if "coroutine." in content:
            frameworks.append("coroutines")
        
        return frameworks
    
    def _test_cargo_detection(self) -> Dict[str, Any]:
        """Test Cargo.toml detection."""
        cargo_files = list(self.test_repos_dir.rglob("Cargo.toml"))
        detected = len(cargo_files) > 0
        
        evidence = []
        for cargo_file in cargo_files[:3]:
            try:
                content = cargo_file.read_text(encoding='utf-8')
                shard = self.toml_plugin.indexFile(cargo_file, content)
                evidence.append({
                    "file": str(cargo_file.relative_to(Path.cwd())),
                    "symbols": len(shard.get("symbols", []))
                })
            except Exception:
                pass
        
        return {
            "detected": detected,
            "evidence": evidence,
            "files_analyzed": len(cargo_files)
        }
    
    def _test_pyproject_detection(self) -> Dict[str, Any]:
        """Test pyproject.toml detection."""
        pyproject_files = list(self.test_repos_dir.rglob("pyproject.toml"))
        detected = len(pyproject_files) > 0
        
        evidence = []
        for pyproject_file in pyproject_files[:3]:
            try:
                content = pyproject_file.read_text(encoding='utf-8')
                shard = self.toml_plugin.indexFile(pyproject_file, content)
                evidence.append({
                    "file": str(pyproject_file.relative_to(Path.cwd())),
                    "symbols": len(shard.get("symbols", []))
                })
            except Exception:
                pass
        
        return {
            "detected": detected,
            "evidence": evidence,
            "files_analyzed": len(pyproject_files)
        }
    
    def _test_love2d_detection(self) -> Dict[str, Any]:
        """Test Love2D detection."""
        love_indicators = list(self.test_repos_dir.rglob("**/love/**/*.lua"))
        love_indicators.extend(list(self.test_repos_dir.rglob("main.lua")))
        love_indicators.extend(list(self.test_repos_dir.rglob("conf.lua")))
        
        detected = len(love_indicators) > 0
        
        evidence = []
        for love_file in love_indicators[:3]:
            try:
                content = love_file.read_text(encoding='utf-8')
                if "love." in content:
                    shard = self.lua_plugin.indexFile(love_file, content)
                    evidence.append({
                        "file": str(love_file.relative_to(Path.cwd())),
                        "symbols": len(shard.get("symbols", []))
                    })
            except Exception:
                pass
        
        return {
            "detected": detected,
            "evidence": evidence,
            "files_analyzed": len(love_indicators)
        }
    
    def _test_kong_detection(self) -> Dict[str, Any]:
        """Test Kong detection."""
        kong_files = list(self.test_repos_dir.rglob("**/kong/**/*.lua"))
        detected = len(kong_files) > 0
        
        evidence = []
        for kong_file in kong_files[:3]:
            try:
                content = kong_file.read_text(encoding='utf-8')
                shard = self.lua_plugin.indexFile(kong_file, content)
                evidence.append({
                    "file": str(kong_file.relative_to(Path.cwd())),
                    "symbols": len(shard.get("symbols", []))
                })
            except Exception:
                pass
        
        return {
            "detected": detected,
            "evidence": evidence,
            "files_analyzed": len(kong_files)
        }
    
    def _test_openresty_detection(self) -> Dict[str, Any]:
        """Test OpenResty detection."""
        resty_files = list(self.test_repos_dir.rglob("**/resty/**/*.lua"))
        resty_files.extend(list(self.test_repos_dir.rglob("lua-resty-*/**/*.lua")))
        
        detected = len(resty_files) > 0
        
        evidence = []
        for resty_file in resty_files[:3]:
            try:
                content = resty_file.read_text(encoding='utf-8')
                if "ngx." in content or "resty." in content:
                    shard = self.lua_plugin.indexFile(resty_file, content)
                    evidence.append({
                        "file": str(resty_file.relative_to(Path.cwd())),
                        "symbols": len(shard.get("symbols", []))
                    })
            except Exception:
                pass
        
        return {
            "detected": detected,
            "evidence": evidence,
            "files_analyzed": len(resty_files)
        }
    
    def _find_mixed_projects(self) -> List[Dict[str, Any]]:
        """Find projects with multiple languages."""
        projects = []
        
        # Look for directories with both TOML and Lua files
        for project_dir in self.test_repos_dir.iterdir():
            if project_dir.is_dir():
                languages = set()
                
                # Check for TOML files
                if list(project_dir.rglob("*.toml")):
                    languages.add("toml")
                
                # Check for Lua files
                if list(project_dir.rglob("*.lua")):
                    languages.add("lua")
                
                # Check for other common languages
                if list(project_dir.rglob("*.py")):
                    languages.add("python")
                if list(project_dir.rglob("*.rs")):
                    languages.add("rust")
                if list(project_dir.rglob("*.js")):
                    languages.add("javascript")
                
                if len(languages) > 1:
                    projects.append({
                        "name": project_dir.name,
                        "path": str(project_dir),
                        "languages": sorted(list(languages))
                    })
        
        return projects
    
    def _analyze_mixed_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a mixed-language project."""
        project_path = Path(project["path"])
        analysis = {
            "name": project["name"],
            "languages": project["languages"],
            "files_by_language": {},
            "symbols_by_language": {},
            "cross_references": []
        }
        
        # Analyze TOML files if present
        if "toml" in project["languages"]:
            toml_files = list(project_path.rglob("*.toml"))
            analysis["files_by_language"]["toml"] = len(toml_files)
            
            symbols_count = 0
            for toml_file in toml_files[:3]:  # Analyze first 3
                try:
                    content = toml_file.read_text(encoding='utf-8')
                    shard = self.toml_plugin.indexFile(toml_file, content)
                    symbols_count += len(shard.get("symbols", []))
                except Exception:
                    pass
            
            analysis["symbols_by_language"]["toml"] = symbols_count
        
        # Analyze Lua files if present
        if "lua" in project["languages"]:
            lua_files = list(project_path.rglob("*.lua"))
            analysis["files_by_language"]["lua"] = len(lua_files)
            
            symbols_count = 0
            for lua_file in lua_files[:3]:  # Analyze first 3
                try:
                    content = lua_file.read_text(encoding='utf-8')
                    shard = self.lua_plugin.indexFile(lua_file, content)
                    symbols_count += len(shard.get("symbols", []))
                except Exception:
                    pass
            
            analysis["symbols_by_language"]["lua"] = symbols_count
        
        return analysis
    
    def generate_summary(self):
        """Generate test summary."""
        summary = {
            "toml_files_tested": len(self.results["toml_tests"]),
            "lua_files_tested": len(self.results["lua_tests"]),
            "frameworks_detected": len([f for f, data in self.results["framework_detections"].items() if data["detected"]]),
            "mixed_projects": len(self.results["cross_language_analysis"]),
            "total_symbols_toml": sum(test["symbols_count"] for test in self.results["toml_tests"]),
            "total_symbols_lua": sum(test["symbols_count"] for test in self.results["lua_tests"])
        }
        
        self.results["summary"] = summary
        
        print(f"\n📊 Test Summary:")
        print(f"  TOML files tested: {summary['toml_files_tested']}")
        print(f"  Lua files tested: {summary['lua_files_tested']}")
        print(f"  Frameworks detected: {summary['frameworks_detected']}")
        print(f"  Mixed projects: {summary['mixed_projects']}")
        print(f"  Total TOML symbols: {summary['total_symbols_toml']}")
        print(f"  Total Lua symbols: {summary['total_symbols_lua']}")
    
    def save_results(self):
        """Save test results to JSON file."""
        results_file = Path("toml_lua_test_results.json")
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")


def main():
    """Run the comprehensive test suite."""
    tester = RepositoryTester()
    results = tester.run_all_tests()
    
    print(f"\n🎉 Testing completed! Check 'toml_lua_test_results.json' for detailed results.")
    
    return results


if __name__ == "__main__":
    main()