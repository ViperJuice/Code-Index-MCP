#!/usr/bin/env python3
"""Test Scala plugin with real repositories."""

import sys
import os
from pathlib import Path

# Add the mcp_server directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp_server'))

from mcp_server.plugins.scala_plugin.plugin import Plugin

def test_scala_plugin():
    """Test Scala plugin with real repository files."""
    
    # Initialize plugin without SQLite for simplicity
    plugin = Plugin(sqlite_store=None)
    
    # Test files from each repository
    test_files = [
        ("test_repos/akka-framework/akka-cluster-sharding-typed/src/main/scala/akka/cluster/sharding/typed/javadsl/ShardedDaemonProcess.scala", "Akka ShardedDaemonProcess"),
        ("test_repos/apache-spark/core/src/main/scala/org/apache/spark/SparkContext.scala", "Spark Context"),
        ("test_repos/play-framework/dev-mode/play-docs-sbt-plugin/src/main/scala/org/playframework/docs/sbtplugin/PlayDocsPlugin.scala", "Play Framework Plugin"),
        ("test_repos/akka-framework/build.sbt", "Akka SBT build file"),
        ("test_repos/apache-spark/project/SparkBuild.scala", "Spark Build definitions"),
        ("test_repos/play-framework/core/play/src/main/scala/play/api/Application.scala", "Play Application API")
    ]
    
    results = {}
    
    for file_path, description in test_files:
        full_path = Path(file_path)
        if not full_path.exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        try:
            # Test if plugin supports the file
            supports = plugin.supports(full_path)
            print(f"📁 {description} ({file_path})")
            print(f"   Supports: {supports}")
            
            if not supports:
                continue
                
            # Read file content and index it
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            
            # Index the file
            shard = plugin.indexFile(full_path, content)
            
            print(f"   Symbols found: {len(shard['symbols'])}")
            print(f"   Language: {shard.get('language', 'unknown')}")
            
            # Categorize symbols by type
            symbol_types = {}
            for symbol in shard['symbols']:
                kind = symbol['kind']
                if kind not in symbol_types:
                    symbol_types[kind] = []
                symbol_types[kind].append(symbol)
            
            print(f"   Symbol types: {', '.join(f'{k}({len(v)})' for k, v in symbol_types.items())}")
            
            # Display interesting symbols by category
            interesting_kinds = ['class', 'trait', 'object', 'case_class', 'case_object', 'def', 'val', 'var', 'actor', 'controller', 'spark', 'setting', 'dependency']
            for kind in interesting_kinds:
                if kind in symbol_types:
                    symbols = symbol_types[kind][:3]  # Show first 3 of each type
                    for symbol in symbols:
                        print(f"     {kind}: {symbol['symbol']} (Line {symbol['line']})")
                        if symbol.get('signature') and len(symbol['signature']) < 120:
                            print(f"       → {symbol['signature']}")
                        
                        # Show modifiers for interesting symbols
                        if symbol.get('modifiers') and kind in ['class', 'trait', 'object', 'def']:
                            modifiers = ', '.join(symbol['modifiers'])
                            print(f"       Modifiers: {modifiers}")
            
            # Test definition lookup for a symbol
            if shard['symbols']:
                test_symbol = shard['symbols'][0]['symbol']
                definition = plugin.getDefinition(test_symbol)
                if definition:
                    print(f"   Definition found for '{test_symbol}': {definition['defined_in']}:{definition['line']}")
                
                # Test reference finding
                refs = plugin.findReferences(test_symbol)
                if refs:
                    print(f"   References to '{test_symbol}': {len(refs)} found")
            
            results[description] = {
                'file_path': file_path,
                'supports': supports,
                'symbols_count': len(shard['symbols']),
                'symbol_types': {k: len(v) for k, v in symbol_types.items()},
                'language': shard.get('language'),
                'package': shard.get('package'),
                'imports': shard.get('imports', [])[:5],  # Show first 5 imports
            }
            
        except Exception as e:
            print(f"   ❌ Error processing {file_path}: {e}")
            import traceback
            traceback.print_exc()
            results[description] = {'error': str(e)}
        
        print()
    
    # Test search functionality
    print("🔍 Testing search functionality:")
    search_terms = ["Actor", "Context", "Spark", "Play", "Application", "Controller"]
    
    for term in search_terms:
        try:
            search_results = plugin.search(term, {"limit": 5})
            print(f"   Search for '{term}': {len(search_results)} results")
            for i, result in enumerate(search_results[:2]):
                print(f"     {i+1}. {result.get('file', 'unknown')} - Score: {result.get('score', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Search error for '{term}': {e}")
    
    print()
    
    # Show statistics
    total_symbols = sum(r.get('symbols_count', 0) for r in results.values() if 'symbols_count' in r)
    indexed_files = len([r for r in results.values() if r.get('supports', False)])
    
    print(f"📊 Summary:")
    print(f"   Files processed: {len(test_files)}")
    print(f"   Files supported: {indexed_files}")
    print(f"   Total symbols indexed: {total_symbols}")
    print(f"   Plugin indexed count: {plugin.get_indexed_count()}")
    
    # Collect statistics on Scala features
    print("\n🧪 Scala Language Features Detected:")
    
    all_symbol_types = {}
    for description, result in results.items():
        if 'symbol_types' in result:
            for symbol_type, count in result['symbol_types'].items():
                all_symbol_types[symbol_type] = all_symbol_types.get(symbol_type, 0) + count
    
    for symbol_type, count in sorted(all_symbol_types.items()):
        print(f"   {symbol_type}: {count}")
    
    # Test framework-specific patterns
    print(f"\n🎯 Framework-Specific Features:")
    
    # Count framework-specific patterns
    akka_features = sum(1 for r in results.values() 
                       if 'symbol_types' in r and r['symbol_types'].get('actor', 0) > 0)
    play_features = sum(1 for r in results.values() 
                       if 'symbol_types' in r and r['symbol_types'].get('controller', 0) > 0)
    spark_features = sum(1 for r in results.values() 
                        if 'symbol_types' in r and r['symbol_types'].get('spark', 0) > 0)
    
    print(f"   Files with Akka Actor patterns: {akka_features}")
    print(f"   Files with Play Controller patterns: {play_features}")
    print(f"   Files with Spark patterns: {spark_features}")
    
    # Show some package structures
    packages = [r.get('package') for r in results.values() if r.get('package')]
    if packages:
        print(f"\n📦 Package Structure Examples:")
        for pkg in set(packages):
            print(f"   {pkg}")
    
    # Test file types
    scala_files = [r for r in results.values() if r.get('language') == 'scala']
    sbt_files = [r for r in results.values() if r.get('language') == 'sbt']
    
    print(f"\n📈 File Types:")
    print(f"   Scala source files: {len(scala_files)}")
    print(f"   SBT build files: {len(sbt_files)}")
    
    print(f"\n✅ Scala plugin testing completed!")
    
    return results

if __name__ == "__main__":
    test_scala_plugin()