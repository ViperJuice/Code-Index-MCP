#!/usr/bin/env python3
"""Debug the Python plugin specifically."""

import sys
import traceback
from pathlib import Path

# Add the mcp_server directory to Python path
sys.path.insert(0, '/home/jenner/Code/Code-Index-MCP')

from mcp_server.plugin_system.plugin_manager import PluginManager

def debug_python_plugin():
    """Debug Python plugin specifically."""
    try:
        # Initialize plugin manager
        plugin_manager = PluginManager()
        plugin_manager.load_plugins()
        
        # Get Python plugin
        python_plugin = plugin_manager.get_plugin_instance('Python')
        
        if not python_plugin:
            print("❌ Python plugin not found!")
            return
        
        print(f"✅ Python plugin found: {type(python_plugin)}")
        print(f"   Methods: {[m for m in dir(python_plugin) if not m.startswith('_')]}")
        
        # Test with a simple Python file
        test_file = "/home/jenner/Code/Code-Index-MCP/test_repos/django/django/__init__.py"
        
        if Path(test_file).exists():
            with open(test_file, 'r') as f:
                content = f.read()
            
            print(f"\n📄 Testing with file: {test_file}")
            print(f"   Content length: {len(content)} chars")
            print(f"   Content preview: {repr(content[:100])}")
            
            # Test indexFile method
            if hasattr(python_plugin, 'indexFile'):
                print("\n🔍 Calling indexFile...")
                try:
                    result = python_plugin.indexFile(test_file, content)
                    print(f"   Result type: {type(result)}")
                    print(f"   Result: {result}")
                    
                    if isinstance(result, dict) and 'symbols' in result:
                        symbols = result['symbols']
                        print(f"   Symbols found: {len(symbols)}")
                        if symbols:
                            print(f"   First symbol: {symbols[0]}")
                    
                except Exception as e:
                    print(f"   ❌ Error calling indexFile: {e}")
                    traceback.print_exc()
            
            # Test _extract_symbols method
            if hasattr(python_plugin, '_extract_symbols'):
                print("\n🔍 Calling _extract_symbols...")
                try:
                    symbols = python_plugin._extract_symbols(content, test_file)
                    print(f"   Symbols type: {type(symbols)}")
                    print(f"   Symbols found: {len(symbols)}")
                    if symbols:
                        print(f"   First symbol: {symbols[0]}")
                        
                except Exception as e:
                    print(f"   ❌ Error calling _extract_symbols: {e}")
                    traceback.print_exc()
        
        else:
            print(f"❌ Test file not found: {test_file}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_python_plugin()