#!/usr/bin/env python3
"""Debug script for JVM parser."""

from mcp_server.plugins.jvm_plugin.plugin import JvmParser

def debug_java_parsing():
    parser = JvmParser()
    
    java_code = '''package com.example.test;

import java.util.List;
import java.util.ArrayList;

@Service
public class Sample<T extends Comparable<T>> implements Runnable {
    
    private static final String CONSTANT = "Hello World";
    private List<T> items;
    
    public Sample() {
        this.items = new ArrayList<>();
    }
    
    public <K, V> Map<K, V> processData(K key, V value) throws Exception {
        return new HashMap<>();
    }
    
    @Override
    public void run() {
        System.out.println("Running...");
    }
    
    public static <T extends Comparable<T>> Sample<T> create() {
        return new Sample<T>();
    }
    
    public interface Callback<R> {
        R callback(String data);
    }
    
    public enum Status {
        ACTIVE, INACTIVE
    }
}'''
    
    print("=== DEBUGGING JAVA PARSING ===")
    print(f"Sample code length: {len(java_code)} chars")
    
    # Test individual patterns
    print("\n--- Testing class pattern ---")
    for match in parser.java_class_pattern.finditer(java_code):
        line_num = java_code[:match.start()].count('\n') + 1
        print(f"Class match: {match.group(1)} at line {line_num}")
    
    print("\n--- Testing method pattern ---")
    for match in parser.java_method_pattern.finditer(java_code):
        line_num = java_code[:match.start()].count('\n') + 1
        print(f"Method match: {match.group(2)} (return: {match.group(1)}) at line {line_num}")
        print(f"  Full match: {match.group(0).strip()}")
    
    print("\n--- Testing generic method pattern ---")
    for match in parser.java_generic_method_pattern.finditer(java_code):
        line_num = java_code[:match.start()].count('\n') + 1
        print(f"Generic method match: {match.group(2)} (return: {match.group(1)}) at line {line_num}")
        print(f"  Full match: {match.group(0).strip()}")
    
    print("\n--- Checking for 'create' method specifically ---")
    create_line = [i+1 for i, line in enumerate(java_code.split('\n')) if 'create' in line]
    print(f"Lines containing 'create': {create_line}")
    if create_line:
        for line_num in create_line:
            line_content = java_code.split('\n')[line_num-1]
            print(f"  Line {line_num}: {repr(line_content)}")
    
    print("\n--- Simple pattern test for create ---")
    import re
    simple_create = re.compile(r'static.*?(\w+)<.*?>\s+create\s*\(')
    for match in simple_create.finditer(java_code):
        line_num = java_code[:match.start()].count('\n') + 1
        print(f"Simple create match: {match.group(1)} at line {line_num}")
    
    print("\n--- Full parsing result ---")
    result = parser.parse_java_file(java_code)
    print(f"Package: {result['package']}")
    print(f"Imports: {len(result['imports'])} items")
    print(f"Classes: {[c['name'] for c in result['classes']]}")
    print(f"Methods: {[m['name'] for m in result['methods']]}")
    print(f"Fields: {[f['name'] for f in result['fields']]}")
    print(f"Annotations: {[a['name'] for a in result['annotations']]}")

if __name__ == "__main__":
    debug_java_parsing()