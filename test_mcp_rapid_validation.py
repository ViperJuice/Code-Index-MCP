#!/usr/bin/env python3
"""
Rapid MCP Validation - Quick test of all specialized plugins using existing test files.
Tests all 7 specialized language plugins in under 60 seconds.
"""

import asyncio
import json
import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Use existing test repositories and create small test files
RAPID_TEST_CONFIG = {
    "python": {
        "test_files": ["test_repos/httpie/httpie/core.py", "test_repos/httpie/httpie/client.py"],
        "expected_symbols": ["main", "HTTPieArgumentParser", "ExitStatus"],
        "description": "HTTPie Python HTTP client"
    },
    "javascript": {
        "test_files": ["test_repos/lodash/lodash.js"],
        "expected_symbols": ["_", "forEach", "map", "filter"], 
        "description": "Lodash JavaScript utility library"
    },
    "typescript": {
        # Create small TypeScript test file since we don't have TS repos
        "test_content": '''
interface User {
    id: number;
    name: string;
    email?: string;
}

class UserService {
    private users: User[] = [];
    
    constructor() {}
    
    async createUser(userData: Partial<User>): Promise<User> {
        const newUser: User = {
            id: Date.now(),
            name: userData.name || "Unknown",
            email: userData.email
        };
        this.users.push(newUser);
        return newUser;
    }
    
    findById(id: number): User | undefined {
        return this.users.find(user => user.id === id);
    }
}

type UserRole = "admin" | "user" | "guest";
export { User, UserService, UserRole };
''',
        "expected_symbols": ["User", "UserService", "createUser", "UserRole"],
        "description": "TypeScript type system test"
    },
    "java": {
        "test_content": '''
package com.example.app;

import java.util.*;
import java.util.concurrent.CompletableFuture;

public interface Repository<T, ID> {
    CompletableFuture<List<T>> findAll();
    CompletableFuture<Optional<T>> findById(ID id);
}

@Component
public class UserService implements Repository<User, Long> {
    private final Map<Long, User> users = new HashMap<>();
    
    @Override
    public CompletableFuture<List<User>> findAll() {
        return CompletableFuture.completedFuture(new ArrayList<>(users.values()));
    }
    
    @Override 
    public CompletableFuture<Optional<User>> findById(Long id) {
        return CompletableFuture.completedFuture(Optional.ofNullable(users.get(id)));
    }
}

class User {
    private Long id;
    private String name;
    
    // getters and setters
}
''',
        "expected_symbols": ["Repository", "UserService", "User", "findAll"],
        "description": "Java generics and annotations test"
    },
    "go": {
        "test_content": '''
package main

import (
    "context"
    "fmt"
    "sync"
)

type User struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

type UserRepository interface {
    FindAll(ctx context.Context) ([]User, error)
    FindByID(ctx context.Context, id int) (*User, error)
}

type userRepo struct {
    mu    sync.RWMutex
    users map[int]*User
}

func NewUserRepository() UserRepository {
    return &userRepo{
        users: make(map[int]*User),
    }
}

func (r *userRepo) FindAll(ctx context.Context) ([]User, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()
    
    result := make([]User, 0, len(r.users))
    for _, user := range r.users {
        result = append(result, *user)
    }
    return result, nil
}

func (r *userRepo) FindByID(ctx context.Context, id int) (*User, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()
    
    if user, exists := r.users[id]; exists {
        return user, nil
    }
    return nil, fmt.Errorf("user not found")
}
''',
        "expected_symbols": ["User", "UserRepository", "userRepo", "NewUserRepository"],
        "description": "Go interfaces and concurrency test"
    },
    "rust": {
        "test_content": '''
use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: u64,
    pub name: String,
}

pub trait Repository<T> {
    type Error;
    
    fn find_all(&self) -> Result<Vec<T>, Self::Error>;
    fn find_by_id(&self, id: u64) -> Result<Option<T>, Self::Error>;
}

pub struct InMemoryUserRepo {
    users: HashMap<u64, User>,
}

impl InMemoryUserRepo {
    pub fn new() -> Self {
        Self {
            users: HashMap::new(),
        }
    }
}

impl Repository<User> for InMemoryUserRepo {
    type Error = String;
    
    fn find_all(&self) -> Result<Vec<User>, Self::Error> {
        Ok(self.users.values().cloned().collect())
    }
    
    fn find_by_id(&self, id: u64) -> Result<Option<User>, Self::Error> {
        Ok(self.users.get(&id).cloned())
    }
}
''',
        "expected_symbols": ["User", "Repository", "InMemoryUserRepo", "find_all"],
        "description": "Rust traits and generics test"
    },
    "csharp": {
        "test_content": '''
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Linq;

namespace App.Domain
{
    public interface IRepository<T> where T : class
    {
        Task<IEnumerable<T>> GetAllAsync();
        Task<T?> GetByIdAsync(int id);
    }

    public class User
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public DateTime CreatedAt { get; set; }
    }

    public class UserService : IRepository<User>
    {
        private readonly List<User> _users = new();

        public async Task<IEnumerable<User>> GetAllAsync()
        {
            await Task.Delay(1); // Simulate async work
            return _users.AsQueryable()
                        .Where(u => u.Name != null)
                        .OrderBy(u => u.Name)
                        .ToList();
        }

        public async Task<User?> GetByIdAsync(int id)
        {
            await Task.Delay(1);
            return _users.FirstOrDefault(u => u.Id == id);
        }

        public async Task<User> CreateAsync(User user)
        {
            user.Id = _users.Count + 1;
            user.CreatedAt = DateTime.UtcNow;
            _users.Add(user);
            return user;
        }
    }
}
''',
        "expected_symbols": ["IRepository", "User", "UserService", "GetAllAsync"],
        "description": "C# async/await and LINQ test"
    },
    "swift": {
        "test_content": '''
import Foundation

protocol Drawable {
    func draw() -> String
}

struct User: Codable {
    let id: Int
    let name: String
    var email: String?
}

@propertyWrapper
struct UserDefault<T> {
    let key: String
    let defaultValue: T
    
    var wrappedValue: T {
        get { UserDefaults.standard.object(forKey: key) as? T ?? defaultValue }
        set { UserDefaults.standard.set(newValue, forKey: key) }
    }
}

class UserService: ObservableObject {
    @UserDefault(key: "users", defaultValue: [])
    private var storedUsers: [User]
    
    @Published var users: [User] = []
    
    func loadUsers() async {
        users = storedUsers
    }
    
    func create(user: User) async -> User {
        var newUser = user
        storedUsers.append(newUser)
        users.append(newUser)
        return newUser
    }
    
    func findById(id: Int) -> User? {
        return users.first { $0.id == id }
    }
}

extension UserService: Drawable {
    func draw() -> String {
        return "UserService with \(users.count) users"
    }
}
''',
        "expected_symbols": ["User", "UserService", "Drawable", "UserDefault"],
        "description": "Swift protocols and property wrappers test"
    },
    "kotlin": {
        "test_content": '''
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

data class User(
    val id: Long,
    val name: String,
    val email: String? = null
)

interface UserRepository {
    suspend fun findAll(): List<User>
    suspend fun findById(id: Long): User?
    fun observeAll(): Flow<List<User>>
}

class UserRepositoryImpl : UserRepository {
    private val _users = mutableListOf<User>()
    private val _usersFlow = MutableStateFlow(emptyList<User>())
    
    override suspend fun findAll(): List<User> = withContext(Dispatchers.IO) {
        delay(10) // Simulate network call
        _users.toList()
    }
    
    override suspend fun findById(id: Long): User? = withContext(Dispatchers.IO) {
        _users.find { it.id == id }
    }
    
    override fun observeAll(): Flow<List<User>> = _usersFlow.asStateFlow()
    
    suspend fun create(user: User): User = withContext(Dispatchers.IO) {
        val newUser = user.copy(id = System.currentTimeMillis())
        _users.add(newUser)
        _usersFlow.value = _users.toList()
        newUser
    }
}

// Extension function
fun User?.isValid(): Boolean = this?.name?.isNotEmpty() == true

// Null safety examples
fun processUser(user: User?) {
    user?.let { u ->
        println("Processing user: ${u.name}")
        u.email?.let { email ->
            println("Email: $email")
        } ?: println("No email provided")
    } ?: println("User is null")
}
''',
        "expected_symbols": ["User", "UserRepository", "UserRepositoryImpl", "create"],
        "description": "Kotlin coroutines and null safety test"
    }
}


class RapidMCPTester:
    """Rapid MCP testing for all specialized plugins."""
    
    def __init__(self):
        self.test_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mcp_rapid_"))
        self.results = {
            "session_id": self.test_session_id,
            "start_time": datetime.now().isoformat(),
            "test_type": "rapid_validation",
            "results": {},
            "summary": {},
            "total_time": 0
        }
        
    def create_test_file(self, language: str, content: str) -> Path:
        """Create a temporary test file for a language."""
        extensions = {
            "python": ".py",
            "javascript": ".js", 
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "csharp": ".cs",
            "swift": ".swift",
            "kotlin": ".kt"
        }
        
        file_path = self.temp_dir / f"test_{language}{extensions.get(language, '.txt')}"
        file_path.write_text(content, encoding='utf-8')
        return file_path
        
    async def test_language_plugin(self, language: str, config: Dict) -> Dict[str, Any]:
        """Test a single language plugin."""
        start_time = time.time()
        
        try:
            # Import required modules
            from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
            from mcp_server.storage.sqlite_store import SQLiteStore
            
            # Create in-memory database
            sqlite_store = SQLiteStore(":memory:")
            
            # Create dispatcher with plugin factory
            dispatcher = EnhancedDispatcher(
                plugins=[],
                sqlite_store=sqlite_store,
                enable_advanced_features=True,
                use_plugin_factory=True,
                lazy_load=True,
                semantic_search_enabled=False
            )
            
            result = {
                "language": language,
                "description": config["description"],
                "plugin_loaded": False,
                "symbols_found": 0,
                "files_tested": 0,
                "lookups_successful": 0,
                "searches_successful": 0,
                "performance": {},
                "errors": []
            }
            
            # Determine test files/content
            test_files = []
            
            if "test_content" in config:
                # Create test file from content
                test_file = self.create_test_file(language, config["test_content"])
                test_files.append(test_file)
            elif "test_files" in config:
                # Use existing files
                for file_path in config["test_files"]:
                    full_path = Path(file_path)
                    if full_path.exists():
                        test_files.append(full_path)
            
            # Index test files
            total_symbols = 0
            for test_file in test_files:
                try:
                    index_result = dispatcher.index_file(test_file)
                    if index_result:
                        symbols = len(index_result.get("symbols", []))
                        total_symbols += symbols
                        result["files_tested"] += 1
                except Exception as e:
                    result["errors"].append(f"Indexing error: {str(e)}")
            
            result["symbols_found"] = total_symbols
            result["plugin_loaded"] = total_symbols > 0
            
            # Test symbol lookups
            for symbol in config.get("expected_symbols", [])[:3]:  # Test first 3
                try:
                    lookup_result = dispatcher.lookup(symbol)
                    if lookup_result:
                        result["lookups_successful"] += 1
                except Exception as e:
                    result["errors"].append(f"Lookup error for '{symbol}': {str(e)}")
            
            # Test search
            search_queries = [language, "function", "user"]
            for query in search_queries:
                try:
                    search_results = list(dispatcher.search(query, semantic=False, limit=3))
                    if search_results:
                        result["searches_successful"] += 1
                except Exception as e:
                    result["errors"].append(f"Search error for '{query}': {str(e)}")
            
            # Performance metrics
            end_time = time.time()
            result["performance"] = {
                "test_time_seconds": round(end_time - start_time, 3),
                "symbols_per_second": round(total_symbols / (end_time - start_time), 2) if end_time > start_time else 0
            }
            
            return result
            
        except Exception as e:
            return {
                "language": language,
                "plugin_loaded": False,
                "error": str(e),
                "performance": {"test_time_seconds": time.time() - start_time}
            }
    
    async def run_all_tests(self, parallel: bool = True) -> Dict[str, Any]:
        """Run tests for all languages."""
        logger.info(f"Starting rapid MCP validation (parallel={parallel})...")
        start_time = time.time()
        
        if parallel:
            # Run tests in parallel
            tasks = []
            for language, config in RAPID_TEST_CONFIG.items():
                task = self.test_language_plugin(language, config)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (language, config) in enumerate(RAPID_TEST_CONFIG.items()):
                result = results[i]
                if isinstance(result, Exception):
                    self.results["results"][language] = {
                        "language": language,
                        "plugin_loaded": False,
                        "error": str(result)
                    }
                else:
                    self.results["results"][language] = result
        else:
            # Run tests sequentially  
            for language, config in RAPID_TEST_CONFIG.items():
                result = await self.test_language_plugin(language, config)
                self.results["results"][language] = result
        
        # Calculate summary
        end_time = time.time()
        self.results["total_time"] = round(end_time - start_time, 3)
        self._calculate_summary()
        
        return self.results
    
    def _calculate_summary(self):
        """Calculate test summary statistics."""
        results = self.results["results"]
        
        total_languages = len(results)
        successful_plugins = sum(1 for r in results.values() if r.get("plugin_loaded", False))
        total_symbols = sum(r.get("symbols_found", 0) for r in results.values())
        total_files = sum(r.get("files_tested", 0) for r in results.values())
        
        self.results["summary"] = {
            "total_languages": total_languages,
            "successful_plugins": successful_plugins,
            "success_rate": round(successful_plugins / total_languages * 100, 1) if total_languages > 0 else 0,
            "total_symbols_extracted": total_symbols,
            "total_files_tested": total_files,
            "avg_test_time": round(sum(r.get("performance", {}).get("test_time_seconds", 0) for r in results.values()) / total_languages, 3) if total_languages > 0 else 0
        }
    
    def print_results(self):
        """Print formatted test results."""
        summary = self.results["summary"]
        
        print(f"\n{'='*50}")
        print(f"RAPID MCP VALIDATION RESULTS")
        print(f"{'='*50}")
        print(f"Session: {self.test_session_id}")
        print(f"Total Time: {self.results['total_time']}s")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"Plugins Working: {summary['successful_plugins']}/{summary['total_languages']}")
        print(f"Symbols Extracted: {summary['total_symbols_extracted']}")
        
        print(f"\n📋 PLUGIN RESULTS:")
        for language, result in self.results["results"].items():
            status = "✅" if result.get("plugin_loaded", False) else "❌"
            symbols = result.get("symbols_found", 0)
            time_taken = result.get("performance", {}).get("test_time_seconds", 0)
            print(f"  {status} {language:12s} | {symbols:2d} symbols | {time_taken:.3f}s")
            
            if result.get("errors"):
                for error in result["errors"][:2]:  # Show first 2 errors
                    print(f"     ⚠️  {error}")
    
    def cleanup(self):
        """Clean up temporary files."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


async def main():
    """Main test execution."""
    tester = RapidMCPTester()
    
    try:
        # Test sequential vs parallel performance
        print("Testing sequential execution...")
        results_sequential = await tester.run_all_tests(parallel=False)
        sequential_time = results_sequential["total_time"]
        
        # Reset for parallel test
        tester = RapidMCPTester()
        
        print("Testing parallel execution...")
        results_parallel = await tester.run_all_tests(parallel=True)
        parallel_time = results_parallel["total_time"]
        
        # Print results
        tester.print_results()
        
        print(f"\n⚡ PERFORMANCE COMPARISON:")
        print(f"  Sequential: {sequential_time:.3f}s")
        print(f"  Parallel:   {parallel_time:.3f}s")
        print(f"  Speedup:    {sequential_time/parallel_time:.1f}x")
        
        # Save results
        results_file = Path(f"rapid_mcp_results_{tester.test_session_id}.json")
        with open(results_file, 'w') as f:
            json.dump(results_parallel, f, indent=2)
        print(f"\n💾 Results saved to: {results_file}")
        
        # Cleanup
        tester.cleanup()
        
        # Return exit code based on success rate
        success_rate = results_parallel["summary"]["success_rate"]
        return 0 if success_rate >= 80 else 1
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        tester.cleanup()
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    print(f"\n🎯 Test completed with exit code: {exit_code}")
    sys.exit(exit_code)