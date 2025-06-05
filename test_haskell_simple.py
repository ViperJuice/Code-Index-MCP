#!/usr/bin/env python3
"""Simple test of Haskell plugin with real repositories."""

import sys
import os
from pathlib import Path

# Add the mcp_server directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp_server'))

from mcp_server.plugins.haskell_plugin.plugin import Plugin

def test_haskell_plugin_simple():
    """Test Haskell plugin with real repository files - simple version."""
    
    # Initialize plugin without SQLite for simplicity
    plugin = Plugin(sqlite_store=None)
    
    # Test files from each repository
    test_files = [
        ("test_repos/yesod-web/yesod-newsfeed/Yesod/AtomFeed.hs", "Yesod AtomFeed"),
        ("test_repos/cabal-haskell/Cabal/src/Distribution/Simple/Setup.hs", "Cabal Setup"),
        ("test_repos/pandoc-converter/xml-light/Text/Pandoc/XML/Light/Types.hs", "Pandoc Types"),
        ("test_repos/cabal-haskell/cabal-install/cabal-install.cabal", "Cabal project file"),
        ("test_repos/yesod-web/stack.yaml", "Stack project file"),
        ("test_repos/pandoc-converter/pandoc.cabal", "Pandoc project file")
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
            
            # Display interesting symbols
            interesting_kinds = ['module', 'function', 'class', 'data', 'newtype', 'type_alias', 'package']
            for kind in interesting_kinds:
                if kind in symbol_types:
                    symbols = symbol_types[kind][:3]  # Show first 3 of each type
                    for symbol in symbols:
                        print(f"     {kind}: {symbol['symbol']} (Line {symbol['line']})")
                        if symbol.get('signature') and len(symbol['signature']) < 100:
                            print(f"       → {symbol['signature']}")
            
            # Test reference finding for a symbol
            if shard['symbols']:
                test_symbol = shard['symbols'][0]['symbol']
                refs = plugin.findReferences(test_symbol)
                if refs:
                    print(f"   References to '{test_symbol}': {len(refs)} found")
            
            results[description] = {
                'file_path': file_path,
                'supports': supports,
                'symbols_count': len(shard['symbols']),
                'symbol_types': {k: len(v) for k, v in symbol_types.items()},
                'language': shard.get('language'),
                'metadata': shard.get('metadata', {})
            }
            
        except Exception as e:
            print(f"   ❌ Error processing {file_path}: {e}")
            import traceback
            traceback.print_exc()
            results[description] = {'error': str(e)}
        
        print()
    
    # Test search functionality
    print("🔍 Testing search functionality:")
    search_terms = ["Feed", "Config", "Atom", "Element", "module"]
    
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
    
    # Collect statistics on Haskell features
    print("\n🧪 Haskell Language Features Detected:")
    
    all_symbol_types = {}
    for description, result in results.items():
        if 'symbol_types' in result:
            for symbol_type, count in result['symbol_types'].items():
                all_symbol_types[symbol_type] = all_symbol_types.get(symbol_type, 0) + count
    
    for symbol_type, count in sorted(all_symbol_types.items()):
        print(f"   {symbol_type}: {count}")
    
    # Test specific language features
    haskell_files = [r for r in results.values() if r.get('language') == 'haskell']
    cabal_files = [r for r in results.values() if r.get('language') == 'cabal']
    yaml_files = [r for r in results.values() if r.get('language') == 'yaml']
    
    print(f"\n📈 File Types:")
    print(f"   Haskell source files: {len(haskell_files)}")
    print(f"   Cabal project files: {len(cabal_files)}")
    print(f"   YAML/Stack files: {len(yaml_files)}")
    
    print(f"\n✅ Haskell plugin testing completed!")
    
    return results

if __name__ == "__main__":
    test_haskell_plugin_simple()