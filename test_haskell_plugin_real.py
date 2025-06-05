#!/usr/bin/env python3
"""Test Haskell plugin with real repositories."""

import sys
import os
from pathlib import Path
import sqlite3

# Add the mcp_server directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp_server'))

from mcp_server.plugins.haskell_plugin.plugin import Plugin
from mcp_server.storage.sqlite_store import SQLiteStore

def test_haskell_plugin():
    """Test Haskell plugin with real repository files."""
    
    # Initialize SQLite store
    db_path = "test_haskell_real.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    store = SQLiteStore(db_path)
    plugin = Plugin(sqlite_store=store)
    
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
            
            # Display first few symbols
            for i, symbol in enumerate(shard['symbols'][:5]):
                print(f"     {i+1}. {symbol['symbol']} ({symbol['kind']}) - Line {symbol['line']}")
                if symbol.get('signature'):
                    print(f"        Signature: {symbol['signature'][:80]}...")
            
            if len(shard['symbols']) > 5:
                print(f"     ... and {len(shard['symbols']) - 5} more symbols")
            
            # Test specific symbol lookup
            if shard['symbols']:
                test_symbol = shard['symbols'][0]['symbol']
                definition = plugin.getDefinition(test_symbol)
                if definition:
                    print(f"   Definition found for '{test_symbol}': {definition['defined_in']}:{definition['line']}")
                
                # Test reference finding
                refs = plugin.findReferences(test_symbol)
                print(f"   References to '{test_symbol}': {len(refs)} found")
            
            results[description] = {
                'file_path': file_path,
                'supports': supports,
                'symbols_count': len(shard['symbols']),
                'symbols': shard['symbols'][:10],  # Store first 10 symbols
                'language': shard.get('language'),
                'metadata': shard.get('metadata', {})
            }
            
        except Exception as e:
            print(f"   ❌ Error processing {file_path}: {e}")
            results[description] = {'error': str(e)}
        
        print()
    
    # Test search functionality
    print("🔍 Testing search functionality:")
    search_terms = ["Feed", "Config", "Atom", "Element", "module"]
    
    for term in search_terms:
        try:
            search_results = plugin.search(term, {"limit": 3})
            print(f"   Search for '{term}': {len(search_results)} results")
            for result in search_results[:2]:
                print(f"     - {result['file']}:{result['line']} - {result['content'][:50]}...")
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
    
    # Test specific Haskell language features
    print("\n🧪 Testing advanced Haskell features:")
    
    # Language pragmas detection
    pragma_count = 0
    type_sig_count = 0
    class_count = 0
    instance_count = 0
    
    for description, result in results.items():
        if 'symbols' in result:
            for symbol in result['symbols']:
                if symbol.get('kind') == 'pragma':
                    pragma_count += 1
                elif symbol.get('kind') == 'function' and symbol.get('type_signature'):
                    type_sig_count += 1
                elif symbol.get('kind') == 'class':
                    class_count += 1
                elif symbol.get('kind') == 'instance':
                    instance_count += 1
    
    print(f"   Language pragmas found: {pragma_count}")
    print(f"   Type signatures found: {type_sig_count}")
    print(f"   Type classes found: {class_count}")
    print(f"   Instance declarations found: {instance_count}")
    
    # Display some notable symbols
    notable_symbols = []
    for description, result in results.items():
        if 'symbols' in result:
            for symbol in result['symbols']:
                if symbol.get('kind') in ['class', 'data', 'newtype', 'type_alias']:
                    notable_symbols.append((description, symbol))
    
    if notable_symbols:
        print(f"\n🏗️  Notable type definitions found:")
        for desc, symbol in notable_symbols[:8]:
            print(f"   {symbol['symbol']} ({symbol['kind']}) in {desc}")
            if symbol.get('signature'):
                print(f"     {symbol['signature'][:100]}...")
    
    print(f"\n✅ Haskell plugin testing completed!")
    
    # Clean up
    store.close()
    
    return results

if __name__ == "__main__":
    test_haskell_plugin()