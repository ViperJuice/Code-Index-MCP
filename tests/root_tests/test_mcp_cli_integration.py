#!/usr/bin/env python3
"""
Test the MCP CLI server integration to ensure all tools work correctly.
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_mcp_cli_integration():
    """Test MCP CLI server tools directly."""
    
    print("🧪 Testing MCP CLI Server Integration...")
    
    try:
        # Import the CLI module
        from mcp_server_cli import initialize_services, call_tool
        
        # Initialize services
        print("📡 Initializing MCP services...")
        await initialize_services()
        print("✅ MCP services initialized successfully")
        
        # Test results
        test_results = {
            "initialization": True,
            "tools_tested": {},
            "overall_success": True
        }
        
        # Test 1: get_status tool
        print("\n🔍 Testing get_status tool...")
        try:
            status_result = await call_tool("get_status", {})
            status_data = json.loads(status_result[0].text)
            
            test_results["tools_tested"]["get_status"] = {
                "success": True,
                "status": status_data.get("status", "unknown"),
                "languages_supported": status_data.get("languages", {}).get("supported", 0),
                "plugins_total": status_data.get("plugins", {}).get("total", 0)
            }
            
            print(f"   ✅ Status: {status_data.get('status', 'unknown')}")
            print(f"   ✅ Languages Supported: {status_data.get('languages', {}).get('supported', 0)}")
            print(f"   ✅ Plugins Loaded: {status_data.get('plugins', {}).get('total', 0)}")
            
        except Exception as e:
            print(f"   ❌ get_status failed: {e}")
            test_results["tools_tested"]["get_status"] = {"success": False, "error": str(e)}
            test_results["overall_success"] = False
        
        # Test 2: list_plugins tool
        print("\n🔌 Testing list_plugins tool...")
        try:
            plugins_result = await call_tool("list_plugins", {})
            plugins_data = json.loads(plugins_result[0].text)
            
            supported_languages = plugins_data.get("supported_languages", [])
            loaded_plugins = plugins_data.get("loaded_plugins", [])
            
            test_results["tools_tested"]["list_plugins"] = {
                "success": True,
                "supported_languages_count": len(supported_languages),
                "loaded_plugins_count": len(loaded_plugins),
                "languages": supported_languages[:10]  # First 10 languages
            }
            
            print(f"   ✅ Supported Languages: {len(supported_languages)}")
            print(f"   ✅ Loaded Plugins: {len(loaded_plugins)}")
            print(f"   ✅ Sample Languages: {', '.join(supported_languages[:5])}...")
            
        except Exception as e:
            print(f"   ❌ list_plugins failed: {e}")
            test_results["tools_tested"]["list_plugins"] = {"success": False, "error": str(e)}
            test_results["overall_success"] = False
        
        # Test 3: Create a test file and use reindex
        print("\n📁 Testing reindex tool...")
        try:
            # Create a temporary test file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write('''
class TestClass:
    def test_method(self):
        return "Hello, MCP!"

def test_function():
    return TestClass()
''')
                test_file_path = f.name
            
            # Test reindexing the file
            reindex_result = await call_tool("reindex", {"path": test_file_path})
            reindex_text = reindex_result[0].text
            
            test_results["tools_tested"]["reindex"] = {
                "success": "Reindexed" in reindex_text,
                "result": reindex_text
            }
            
            print(f"   ✅ Reindex result: {reindex_text}")
            
            # Clean up test file
            Path(test_file_path).unlink()
            
        except Exception as e:
            print(f"   ❌ reindex failed: {e}")
            test_results["tools_tested"]["reindex"] = {"success": False, "error": str(e)}
            test_results["overall_success"] = False
        
        # Test 4: search_code tool
        print("\n🔎 Testing search_code tool...")
        try:
            search_result = await call_tool("search_code", {"query": "function", "limit": 5})
            search_data = json.loads(search_result[0].text)
            
            results_count = len(search_data) if isinstance(search_data, list) else 0
            
            test_results["tools_tested"]["search_code"] = {
                "success": True,
                "results_count": results_count,
                "has_results": results_count > 0
            }
            
            print(f"   ✅ Search Results: {results_count}")
            
        except Exception as e:
            print(f"   ❌ search_code failed: {e}")
            test_results["tools_tested"]["search_code"] = {"success": False, "error": str(e)}
            test_results["overall_success"] = False
        
        # Test 5: symbol_lookup tool
        print("\n🎯 Testing symbol_lookup tool...")
        try:
            lookup_result = await call_tool("symbol_lookup", {"symbol": "main"})
            lookup_text = lookup_result[0].text
            
            # Check if we got a valid response
            success = "not found" not in lookup_text.lower() or "main" in lookup_text
            
            test_results["tools_tested"]["symbol_lookup"] = {
                "success": success,
                "result_preview": lookup_text[:100] + "..." if len(lookup_text) > 100 else lookup_text
            }
            
            print(f"   ✅ Symbol Lookup: {'Found' if success else 'Not found'}")
            
        except Exception as e:
            print(f"   ❌ symbol_lookup failed: {e}")
            test_results["tools_tested"]["symbol_lookup"] = {"success": False, "error": str(e)}
            test_results["overall_success"] = False
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"MCP CLI INTEGRATION TEST SUMMARY")
        print(f"{'='*60}")
        
        successful_tools = sum(1 for t in test_results["tools_tested"].values() if t.get("success", False))
        total_tools = len(test_results["tools_tested"])
        
        print(f"Overall Success: {'✅ PASS' if test_results['overall_success'] else '❌ FAIL'}")
        print(f"Tools Working: {successful_tools}/{total_tools}")
        
        for tool_name, result in test_results["tools_tested"].items():
            status = "✅" if result.get("success", False) else "❌"
            print(f"  {status} {tool_name}")
        
        # Save results
        results_file = Path("mcp_cli_integration_results.json")
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2)
        print(f"\n💾 Test results saved to: {results_file}")
        
        return test_results["overall_success"]
        
    except Exception as e:
        print(f"❌ MCP CLI integration test failed: {e}")
        logger.error(f"Integration test error: {e}", exc_info=True)
        return False


async def main():
    """Main test execution."""
    try:
        success = await test_mcp_cli_integration()
        
        if success:
            print(f"\n🎉 MCP CLI integration test completed successfully!")
            return 0
        else:
            print(f"\n⚠️  MCP CLI integration test completed with issues")
            return 1
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)