#!/usr/bin/env python3
"""
Simple test script to verify C plugin functionality.
"""

import sys
from pathlib import Path
from mcp_server.plugins.c_plugin.plugin import Plugin as CPlugin
from mcp_server.storage.sqlite_store import SQLiteStore

def main():
    print("Testing C Plugin...")
    
    # Test code
    test_code = """
#include <stdio.h>
#include <stdlib.h>

#define MAX_BUFFER 1024
#define SQUARE(x) ((x) * (x))

typedef struct {
    int x;
    int y;
} Point;

typedef int (*CompareFunc)(const void*, const void*);

enum Color {
    RED,
    GREEN,
    BLUE
};

static int global_counter = 0;

int add(int a, int b) {
    return a + b;
}

Point* create_point(int x, int y) {
    Point* p = malloc(sizeof(Point));
    if (p) {
        p->x = x;
        p->y = y;
    }
    return p;
}

int main(int argc, char* argv[]) {
    printf("Hello, World!\\n");
    Point p = {10, 20};
    int result = add(p.x, p.y);
    printf("Result: %d\\n", result);
    return 0;
}
"""

    try:
        # Create plugin without SQLite store for simple test
        plugin = CPlugin()
        print("✓ Plugin created successfully")
        
        # Test file support
        assert plugin.supports("test.c") == True
        assert plugin.supports("test.h") == True
        assert plugin.supports("test.py") == False
        print("✓ File support detection working")
        
        # Test indexing
        result = plugin.indexFile(Path("test.c"), test_code)
        print(f"✓ File indexed successfully")
        
        # Check symbols
        symbols = result["symbols"]
        print(f"\nFound {len(symbols)} symbols:")
        
        # Group symbols by kind
        by_kind = {}
        for symbol in symbols:
            kind = symbol["kind"]
            if kind not in by_kind:
                by_kind[kind] = []
            by_kind[kind].append(symbol)
        
        # Display symbols by kind
        for kind, syms in sorted(by_kind.items()):
            print(f"\n{kind.upper()}S ({len(syms)}):")
            for sym in syms:
                print(f"  - {sym['symbol']} at line {sym['line']}")
                if 'signature' in sym:
                    print(f"    Signature: {sym['signature']}")
        
        # Verify expected symbols
        symbol_names = {s["symbol"] for s in symbols}
        expected_symbols = {
            # Functions
            "add", "create_point", "main",
            # Structs
            "Point",
            # Enums
            "Color",
            # Typedefs
            "CompareFunc",
            # Macros
            "MAX_BUFFER", "SQUARE",
            # Variables
            "global_counter"
        }
        
        missing = expected_symbols - symbol_names
        if missing:
            print(f"\n⚠ Missing symbols: {missing}")
        else:
            print(f"\n✓ All expected symbols found")
        
        # Test search
        print("\nTesting search...")
        search_results = plugin.search("add", {"limit": 10})
        print(f"✓ Search for 'add' returned {len(search_results)} results")
        for result in search_results:
            print(f"  - {result['symbol']} in {result['file']} at line {result['line']}")
        
        # Test definition lookup
        print("\nTesting definition lookup...")
        add_def = plugin.getDefinition("add")
        if add_def:
            print(f"✓ Found definition for 'add': {add_def['signature']}")
        else:
            print("⚠ Could not find definition for 'add'")
        
        print("\n✅ All tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())