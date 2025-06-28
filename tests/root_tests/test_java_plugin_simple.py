#!/usr/bin/env python3
"""Simple test for Java plugin."""

import tempfile
from pathlib import Path
from mcp_server.plugins.java_plugin import Plugin


def test_java_plugin_simple():
    """Test basic Java plugin functionality."""
    
    # Simple Java code
    java_code = """package com.example;

import java.util.List;
import java.util.ArrayList;

public class HelloWorld {
    private String message;
    
    public HelloWorld(String message) {
        this.message = message;
    }
    
    public void sayHello() {
        System.out.println(message);
    }
    
    public static void main(String[] args) {
        HelloWorld hw = new HelloWorld("Hello, World!");
        hw.sayHello();
    }
}"""
    
    # Create plugin without semantic search to simplify
    plugin = Plugin(enable_semantic=False)
    
    print("1. Testing file support:")
    assert plugin.supports("HelloWorld.java")
    assert not plugin.supports("hello.py")
    print("✓ File support works")
    
    print("\n2. Testing indexing:")
    shard = plugin.indexFile("HelloWorld.java", java_code)
    print(f"✓ Found {len(shard['symbols'])} symbols:")
    for sym in shard['symbols']:
        print(f"  - {sym['kind']}: {sym['symbol']}")
    
    print("\n3. Testing getDefinition:")
    definition = plugin.getDefinition("HelloWorld")
    if definition:
        print(f"✓ Found definition: {definition.get('signature', 'N/A')}")
    
    print("\n4. Testing search:")
    results = list(plugin.search("HelloWorld"))
    print(f"✓ Search returned {len(results)} results")
    
    print("\n✅ Basic test passed!")


if __name__ == "__main__":
    test_java_plugin_simple()