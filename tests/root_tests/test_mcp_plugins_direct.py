#!/usr/bin/env python3
"""
Direct MCP Plugin Testing - Test plugins directly without dispatcher complexity.
Focuses on core plugin functionality and symbol extraction.
"""

import asyncio
import json
import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Test code snippets for each language
TEST_CODE_SAMPLES = {
    "python": {
        "content": '''
class UserManager:
    def __init__(self):
        self.users = []
    
    def add_user(self, name: str, email: str) -> dict:
        """Add a new user."""
        user = {
            "id": len(self.users) + 1,
            "name": name,
            "email": email
        }
        self.users.append(user)
        return user
    
    def get_user(self, user_id: int) -> dict:
        for user in self.users:
            if user["id"] == user_id:
                return user
        return None

def main():
    manager = UserManager()
    manager.add_user("John", "john@example.com")
''',
        "expected_symbols": ["UserManager", "add_user", "get_user", "main"],
        "plugin_module": "mcp_server.plugins.python_plugin",
    },
    "javascript": {
        "content": """
class UserService {
    constructor() {
        this.users = [];
    }
    
    addUser(name, email) {
        const user = {
            id: this.users.length + 1,
            name: name,
            email: email
        };
        this.users.push(user);
        return user;
    }
    
    getUser(id) {
        return this.users.find(user => user.id === id);
    }
    
    async fetchUsers() {
        return new Promise(resolve => {
            setTimeout(() => resolve(this.users), 100);
        });
    }
}

function createService() {
    return new UserService();
}

export { UserService, createService };
""",
        "expected_symbols": ["UserService", "addUser", "getUser", "fetchUsers", "createService"],
        "plugin_module": "mcp_server.plugins.js_plugin",
    },
    "typescript": {
        "content": """
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
""",
        "expected_symbols": ["User", "UserService", "createUser", "UserRole"],
        "plugin_module": "mcp_server.plugins.typescript_plugin",
    },
    "java": {
        "content": """
package com.example.app;

import java.util.*;
import java.util.concurrent.CompletableFuture;

public interface Repository<T, ID> {
    CompletableFuture<List<T>> findAll();
    CompletableFuture<Optional<T>> findById(ID id);
}

public class UserService implements Repository<User, Long> {
    private final Map<Long, User> users = new HashMap<>();
    
    @Override
    public CompletableFuture<List<User>> findAll() {
        return CompletableFuture.completedFuture(new ArrayList<>(users.values()));
    }
    
    @Override 
    public CompletableFuture<Optional<T>> findById(Long id) {
        return CompletableFuture.completedFuture(Optional.ofNullable(users.get(id)));
    }
}

class User {
    private Long id;
    private String name;
    
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
}
""",
        "expected_symbols": ["Repository", "UserService", "User", "findAll"],
        "plugin_module": "mcp_server.plugins.java_plugin",
    },
    "go": {
        "content": """
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
""",
        "expected_symbols": ["User", "UserRepository", "userRepo", "NewUserRepository"],
        "plugin_module": "mcp_server.plugins.go_plugin",
    },
    "rust": {
        "content": """
use std::collections::HashMap;

#[derive(Debug, Clone)]
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
""",
        "expected_symbols": ["User", "Repository", "InMemoryUserRepo", "find_all"],
        "plugin_module": "mcp_server.plugins.rust_plugin",
    },
    "csharp": {
        "content": """
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
            await Task.Delay(1);
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
    }
}
""",
        "expected_symbols": ["IRepository", "User", "UserService", "GetAllAsync"],
        "plugin_module": "mcp_server.plugins.csharp_plugin",
    },
    "swift": {
        "content": """
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
    
    func create(user: User) async -> User {
        var newUser = user
        storedUsers.append(newUser)
        return newUser
    }
    
    func findById(id: Int) -> User? {
        return storedUsers.first { $0.id == id }
    }
}

extension UserService: Drawable {
    func draw() -> String {
        return "UserService with \\(storedUsers.count) users"
    }
}
""",
        "expected_symbols": ["User", "UserService", "Drawable", "UserDefault"],
        "plugin_module": "mcp_server.plugins.swift_plugin",
    },
    "kotlin": {
        "content": """
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
        delay(10)
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
""",
        "expected_symbols": ["User", "UserRepository", "UserRepositoryImpl", "create"],
        "plugin_module": "mcp_server.plugins.kotlin_plugin",
    },
}


class DirectPluginTester:
    """Test plugins directly without dispatcher overhead."""

    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mcp_direct_"))
        self.results = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "test_type": "direct_plugin",
            "results": {},
            "summary": {},
        }

    def create_test_file(self, language: str, content: str) -> Path:
        """Create a test file for the language."""
        extensions = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "csharp": ".cs",
            "swift": ".swift",
            "kotlin": ".kt",
        }

        ext = extensions.get(language, ".txt")
        file_path = self.temp_dir / f"test_{language}{ext}"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_plugin_directly(self, language: str, config: Dict) -> Dict[str, Any]:
        """Test a plugin directly by importing and using it."""
        start_time = time.time()

        result = {
            "language": language,
            "plugin_loaded": False,
            "symbols_found": 0,
            "indexing_success": False,
            "search_success": False,
            "plugin_type": "unknown",
            "performance": {},
            "errors": [],
        }

        try:
            # Create test file
            test_file = self.create_test_file(language, config["content"])

            # Try to import the plugin module
            try:
                import importlib

                plugin_module = importlib.import_module(config["plugin_module"])
                plugin_class = getattr(plugin_module, "Plugin")

                # Create plugin instance without SQLite to avoid database issues
                plugin = plugin_class(sqlite_store=None)
                result["plugin_loaded"] = True
                result["plugin_type"] = plugin.__class__.__name__

            except (ImportError, AttributeError) as e:
                # Try generic plugin as fallback
                result["errors"].append(f"Specific plugin import failed: {str(e)}")

                from mcp_server.plugins.generic_treesitter_plugin import GenericTreeSitterPlugin
                from mcp_server.plugins.language_registry import LANGUAGE_CONFIGS

                if language in LANGUAGE_CONFIGS:
                    plugin = GenericTreeSitterPlugin(LANGUAGE_CONFIGS[language], sqlite_store=None)
                    result["plugin_loaded"] = True
                    result["plugin_type"] = "GenericTreeSitterPlugin"
                else:
                    result["errors"].append(f"No configuration found for {language}")
                    return result

            # Test file support
            if not plugin.supports(test_file):
                result["errors"].append(f"Plugin doesn't support file: {test_file}")
                return result

            # Test indexing
            try:
                content = test_file.read_text(encoding="utf-8")
                index_result = plugin.indexFile(test_file, content)

                if index_result and "symbols" in index_result:
                    result["symbols_found"] = len(index_result["symbols"])
                    result["indexing_success"] = True

                    # Log some symbols for verification
                    symbols = index_result["symbols"][:5]  # First 5 symbols
                    result["sample_symbols"] = [s.get("symbol", "unknown") for s in symbols]
                else:
                    result["errors"].append("No symbols returned from indexing")

            except Exception as e:
                result["errors"].append(f"Indexing failed: {str(e)}")

            # Test search if indexing worked
            if result["indexing_success"]:
                try:
                    search_results = list(plugin.search("user", {"limit": 5}))
                    result["search_success"] = len(search_results) > 0
                    result["search_results_count"] = len(search_results)
                except Exception as e:
                    result["errors"].append(f"Search failed: {str(e)}")

            # Performance metrics
            end_time = time.time()
            result["performance"] = {
                "test_time_seconds": round(end_time - start_time, 3),
                "symbols_per_second": (
                    round(result["symbols_found"] / (end_time - start_time), 2)
                    if end_time > start_time and result["symbols_found"] > 0
                    else 0
                ),
            }

        except Exception as e:
            result["errors"].append(f"General error: {str(e)}")
            result["performance"] = {"test_time_seconds": time.time() - start_time}

        return result

    def run_all_tests(self) -> Dict[str, Any]:
        """Run tests for all languages."""
        logger.info("Starting direct plugin testing...")
        start_time = time.time()

        for language, config in TEST_CODE_SAMPLES.items():
            logger.info(f"Testing {language} plugin...")
            result = self.test_plugin_directly(language, config)
            self.results["results"][language] = result

        # Calculate summary
        end_time = time.time()
        self.results["total_time"] = round(end_time - start_time, 3)
        self._calculate_summary()

        return self.results

    def _calculate_summary(self):
        """Calculate summary statistics."""
        results = self.results["results"]

        total_languages = len(results)
        successful_plugins = sum(1 for r in results.values() if r.get("plugin_loaded", False))
        successful_indexing = sum(1 for r in results.values() if r.get("indexing_success", False))
        total_symbols = sum(r.get("symbols_found", 0) for r in results.values())

        self.results["summary"] = {
            "total_languages": total_languages,
            "successful_plugins": successful_plugins,
            "successful_indexing": successful_indexing,
            "plugin_success_rate": (
                round(successful_plugins / total_languages * 100, 1) if total_languages > 0 else 0
            ),
            "indexing_success_rate": (
                round(successful_indexing / total_languages * 100, 1) if total_languages > 0 else 0
            ),
            "total_symbols_extracted": total_symbols,
            "avg_symbols_per_language": (
                round(total_symbols / total_languages, 1) if total_languages > 0 else 0
            ),
        }

    def print_results(self):
        """Print formatted results."""
        summary = self.results["summary"]

        print(f"\n{'='*60}")
        print(f"DIRECT MCP PLUGIN TESTING RESULTS")
        print(f"{'='*60}")
        print(f"Total Time: {self.results['total_time']}s")
        print(f"Plugin Success Rate: {summary['plugin_success_rate']}%")
        print(f"Indexing Success Rate: {summary['indexing_success_rate']}%")
        print(f"Total Symbols: {summary['total_symbols_extracted']}")
        print(f"Avg Symbols/Language: {summary['avg_symbols_per_language']}")

        print(f"\n📋 DETAILED RESULTS:")
        for language, result in self.results["results"].items():
            plugin_status = "✅" if result.get("plugin_loaded", False) else "❌"
            index_status = "✅" if result.get("indexing_success", False) else "❌"
            symbols = result.get("symbols_found", 0)
            plugin_type = result.get("plugin_type", "unknown")
            time_taken = result.get("performance", {}).get("test_time_seconds", 0)

            print(
                f"  {plugin_status}{index_status} {language:12s} | {symbols:2d} symbols | {plugin_type:20s} | {time_taken:.3f}s"
            )

            # Show sample symbols if available
            sample_symbols = result.get("sample_symbols", [])
            if sample_symbols:
                print(f"      Symbols: {', '.join(sample_symbols[:3])}")

            # Show errors if any
            if result.get("errors"):
                for error in result["errors"][:2]:  # Show first 2 errors
                    print(f"      ⚠️  {error[:80]}...")

    def cleanup(self):
        """Clean up temporary files."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


def main():
    """Main test execution."""
    tester = DirectPluginTester()

    try:
        # Run tests
        results = tester.run_all_tests()

        # Print results
        tester.print_results()

        # Save results
        results_file = Path(f"direct_plugin_results_{results['session_id']}.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {results_file}")

        # Cleanup
        tester.cleanup()

        # Return exit code based on success rate
        success_rate = results["summary"]["indexing_success_rate"]
        if success_rate >= 70:
            print(f"\n🎉 Testing completed successfully! ({success_rate}% success rate)")
            return 0
        else:
            print(f"\n⚠️  Testing completed with issues ({success_rate}% success rate)")
            return 1

    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        tester.cleanup()
        return 1


if __name__ == "__main__":
    import sys

    exit_code = main()
    print(f"\n🎯 Test completed with exit code: {exit_code}")
    sys.exit(exit_code)
