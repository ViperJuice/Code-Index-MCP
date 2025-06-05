#!/usr/bin/env python3
"""
Simple test of the C# plugin to debug issues.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))

try:
    from mcp_server.plugins.csharp_plugin.plugin import Plugin
    print("✅ C# plugin imported successfully")
    
    # Create plugin instance
    plugin = Plugin()
    print("✅ Plugin instance created")
    
    # Test with simple C# code
    test_code = """
using System;

namespace TestNamespace
{
    public class TestClass
    {
        public string Name { get; set; }
        
        public void TestMethod()
        {
            Console.WriteLine("Hello World");
        }
    }
}
"""
    
    print("🔍 Testing simple C# code...")
    try:
        result = plugin.indexFile("test.cs", test_code)
        print(f"✅ Index result: {result}")
        if hasattr(result, 'symbols'):
            symbols = result.symbols
            print(f"✅ Found {len(symbols)} symbols")
            
            for symbol in symbols[:5]:  # Print first 5 symbols
                print(f"  - {symbol.symbol_type}: {symbol.name} (line {getattr(symbol, 'line', 'N/A')})")
        else:
            print("✅ Index created successfully")
            
    except Exception as e:
        print(f"❌ Parse error: {e}")
        import traceback
        traceback.print_exc()
        
    # Test with existing test file
    test_file_path = Path("mcp_server/plugins/csharp_plugin/test_data/SampleClass.cs")
    if test_file_path.exists():
        print(f"\n🔍 Testing with existing file: {test_file_path}")
        try:
            content = test_file_path.read_text()
            result = plugin.indexFile(str(test_file_path), content)
            print(f"✅ Index result: {result}")
            if hasattr(result, 'symbols'):
                symbols = result.symbols
                print(f"✅ Found {len(symbols)} symbols")
                
                for symbol in symbols[:10]:  # Print first 10 symbols
                    print(f"  - {symbol.symbol_type}: {symbol.name} (line {getattr(symbol, 'line', 'N/A')})")
            else:
                print("✅ Index created successfully")
                
        except Exception as e:
            print(f"❌ Parse error: {e}")
            import traceback
            traceback.print_exc()
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()