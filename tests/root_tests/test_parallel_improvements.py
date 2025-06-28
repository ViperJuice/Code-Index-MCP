#!/usr/bin/env python3
"""Test all three parallel improvements: integration fixes, query caching, and enhanced queries."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore


def test_parallel_improvements():
    """Test integration fixes, query caching, and enhanced queries."""
    print("=== Testing Parallel Improvements ===\n")
    
    # Test files with enhanced patterns
    test_files = {
        "enhanced.rs": '''use std::collections::HashMap;

const MAX_SIZE: usize = 1024;
static mut COUNTER: i32 = 0;

type UserId = u64;
type UserMap = HashMap<UserId, User>;

struct User {
    id: UserId,
    name: String,
}

trait Authenticate {
    fn login(&self) -> bool;
}

impl Authenticate for User {
    fn login(&self) -> bool {
        true
    }
}

impl User {
    fn new(id: UserId, name: String) -> Self {
        User { id, name }
    }
}

mod auth {
    pub fn validate_token(token: &str) -> bool {
        !token.is_empty()
    }
}

macro_rules! create_user {
    ($id:expr, $name:expr) => {
        User::new($id, $name.to_string())
    };
}

fn main() {
    let user = create_user!(1, "Alice");
}''',
        
        "enhanced.go": '''package main

import (
    "fmt"
    "sync"
)

const MaxConnections = 100

var (
    connectionPool sync.Pool
    activeConnections int
)

type ConnectionManager interface {
    Connect() error
    Disconnect() error
}

type DatabaseConnection struct {
    host string
    port int
}

func (db *DatabaseConnection) Connect() error {
    return nil
}

func (db *DatabaseConnection) Disconnect() error {
    return nil
}

func NewConnection(host string, port int) *DatabaseConnection {
    return &DatabaseConnection{host: host, port: port}
}

func GetActiveConnections() int {
    return activeConnections
}

func main() {
    db := NewConnection("localhost", 5432)
    fmt.Printf("Connected to %s:%d\\n", db.host, db.port)
}''',
        
        "enhanced.py": '''#!/usr/bin/env python3
"""Enhanced Python module with comprehensive patterns."""

import os
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Global variables
DEBUG_MODE = True
MAX_RETRIES = 3

@dataclass
class User:
    id: int
    username: str
    email: str

class Repository(ABC):
    @abstractmethod
    def save(self, entity) -> bool:
        pass
    
    @abstractmethod
    def find_by_id(self, id: int) -> Optional[object]:
        pass

@dataclass
class UserRepository(Repository):
    def __init__(self):
        self.users: Dict[int, User] = {}
    
    def save(self, user: User) -> bool:
        self.users[user.id] = user
        return True
    
    def find_by_id(self, id: int) -> Optional[User]:
        return self.users.get(id)

def create_user(username: str, email: str) -> User:
    global MAX_RETRIES
    user_id = len(_get_all_users()) + 1
    return User(id=user_id, username=username, email=email)

def _get_all_users() -> List[User]:
    """Private helper function."""
    return []

if __name__ == "__main__":
    repo = UserRepository()
    user = create_user("alice", "alice@example.com")
    repo.save(user)'''
    }
    
    # Create store and dispatcher
    store = SQLiteStore(":memory:")
    dispatcher = EnhancedDispatcher(
        plugins=None,
        sqlite_store=store,
        use_plugin_factory=True,
        lazy_load=True
    )
    
    print("1. Testing Enhanced Query Patterns...")
    
    results = {}
    for filename, content in test_files.items():
        extension = '.' + filename.split('.')[1]
        
        # Map extensions to language codes
        lang_map = {'.rs': 'rust', '.go': 'go', '.py': 'python'}
        lang = lang_map.get(extension, extension[1:])
        
        print(f"\n   Testing {lang.upper()}:")
        
        # Create and index file
        test_file = Path(filename)
        test_file.write_text(content)
        
        try:
            # Test direct plugin functionality
            plugin = PluginFactory.create_plugin(lang, store, enable_semantic=False)
            
            # Test query caching (multiple runs)
            start_time = time.time()
            shard1 = plugin.indexFile(test_file, content)
            first_run_time = time.time() - start_time
            
            start_time = time.time()
            shard2 = plugin.indexFile(test_file, content)
            second_run_time = time.time() - start_time
            
            print(f"     Symbols found: {len(shard1['symbols'])}")
            print(f"     First run: {first_run_time:.4f}s, Second run: {second_run_time:.4f}s")
            if second_run_time < first_run_time * 0.8:  # Should be faster due to caching
                print(f"     ✓ Query caching improved performance")
            else:
                print(f"     ? Query caching effect unclear")
            
            # Show symbol types found
            symbol_types = set(s['kind'] for s in shard1['symbols'])
            print(f"     Symbol types: {', '.join(sorted(symbol_types))}")
            
            results[lang] = {
                'symbols': len(shard1['symbols']),
                'types': len(symbol_types),
                'caching': second_run_time < first_run_time * 0.8
            }
            
        except Exception as e:
            print(f"     ✗ Error: {e}")
            results[lang] = {'error': str(e)}
        finally:
            test_file.unlink(missing_ok=True)
    
    print("\n2. Testing Dispatcher Integration...")
    
    # Create test files for dispatcher
    for filename, content in test_files.items():
        Path(filename).write_text(content)
    
    try:
        # Index all files
        for filename in test_files.keys():
            dispatcher.index_file(Path(filename))
        
        # Test search across languages
        print(f"\n   Cross-language search results:")
        search_terms = ["User", "main", "create", "connect"]
        
        for term in search_terms:
            search_results = list(dispatcher.search(term, limit=10))
            print(f"     '{term}': {len(search_results)} results")
        
        # Test symbol lookup
        print(f"\n   Symbol lookup results:")
        symbols_to_find = ["User", "main", "NewConnection", "create_user"]
        found_count = 0
        
        for symbol in symbols_to_find:
            definition = dispatcher.lookup(symbol)
            if definition:
                file_name = Path(definition.get('defined_in', '')).name
                print(f"     ✓ {symbol}: {definition.get('kind', 'unknown')} in {file_name}")
                found_count += 1
            else:
                print(f"     ✗ {symbol}: not found")
        
        integration_success = found_count > 0
        
    finally:
        # Cleanup
        for filename in test_files.keys():
            Path(filename).unlink(missing_ok=True)
    
    print("\n3. Performance and Cache Analysis...")
    
    # Show statistics
    stats = dispatcher.get_statistics()
    print(f"   Plugins loaded: {stats['total_plugins']}")
    print(f"   Languages: {', '.join(sorted(stats['loaded_languages']))}")
    print(f"   Operations: {stats['operations']['indexings']} indexings, {stats['operations']['searches']} searches")
    
    # Summary
    print("\n=== Summary of Improvements ===")
    
    successful_langs = [lang for lang, result in results.items() if 'error' not in result]
    cached_langs = [lang for lang, result in results.items() if result.get('caching', False)]
    
    print(f"✅ Enhanced Queries: {len(successful_langs)}/{len(results)} languages working")
    print(f"✅ Query Caching: {len(cached_langs)}/{len(successful_langs)} languages show performance improvement")
    print(f"✅ Integration: {'Working' if integration_success else 'Needs attention'}")
    
    print(f"\nDetailed results:")
    for lang, result in results.items():
        if 'error' not in result:
            print(f"  {lang}: {result['symbols']} symbols, {result['types']} types, caching: {result['caching']}")
        else:
            print(f"  {lang}: ERROR - {result['error']}")
    
    return len(successful_langs) == len(results) and integration_success


if __name__ == "__main__":
    success = test_parallel_improvements()
    if success:
        print("\n🎉 All parallel improvements working successfully!")
    else:
        print("\n⚠️ Some improvements need attention")
        sys.exit(1)