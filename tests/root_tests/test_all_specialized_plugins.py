#!/usr/bin/env python3
"""Comprehensive test for all specialized language plugins."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore


def test_all_specialized_plugins():
    """Test all specialized plugins with sample code."""
    print("=== Testing All Specialized Language Plugins ===\n")

    # Test data for each specialized plugin
    test_cases = {
        "java": {
            "code": """package com.example.app;

import java.util.List;
import java.util.ArrayList;

public class UserService<T extends BaseEntity> {
    private final Repository<T> repository;
    
    public UserService(Repository<T> repository) {
        this.repository = repository;
    }
    
    public List<T> findAll() {
        return new ArrayList<>(repository.findAll());
    }
    
    public Optional<T> findById(Long id) {
        return repository.findById(id);
    }
}

interface Repository<T> {
    List<T> findAll();
    Optional<T> findById(Long id);
}""",
            "extension": ".java",
            "expected_features": ["generics", "imports", "interface", "class"],
        },
        "go": {
            "code": """package main

import (
    "fmt"
    "context"
    "database/sql"
)

type User struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

type UserRepository interface {
    Create(ctx context.Context, user *User) error
    GetByID(ctx context.Context, id int) (*User, error)
}

type userRepo struct {
    db *sql.DB
}

func NewUserRepository(db *sql.DB) UserRepository {
    return &userRepo{db: db}
}

func (r *userRepo) Create(ctx context.Context, user *User) error {
    query := "INSERT INTO users (name) VALUES ($1)"
    _, err := r.db.ExecContext(ctx, query, user.Name)
    return err
}

func (r *userRepo) GetByID(ctx context.Context, id int) (*User, error) {
    user := &User{}
    query := "SELECT id, name FROM users WHERE id = $1"
    err := r.db.QueryRowContext(ctx, query, id).Scan(&user.ID, &user.Name)
    return user, err
}""",
            "extension": ".go",
            "expected_features": ["interface", "struct", "method", "function"],
        },
        "rust": {
            "code": """use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: u64,
    pub name: String,
    pub email: String,
}

pub trait Repository<T> {
    type Error;
    
    fn create(&mut self, item: T) -> Result<T, Self::Error>;
    fn find_by_id(&self, id: u64) -> Result<Option<T>, Self::Error>;
}

pub struct InMemoryUserRepo {
    users: HashMap<u64, User>,
    next_id: u64,
}

impl InMemoryUserRepo {
    pub fn new() -> Self {
        Self {
            users: HashMap::new(),
            next_id: 1,
        }
    }
}

impl Repository<User> for InMemoryUserRepo {
    type Error = String;
    
    fn create(&mut self, mut user: User) -> Result<User, Self::Error> {
        user.id = self.next_id;
        self.next_id += 1;
        self.users.insert(user.id, user.clone());
        Ok(user)
    }
    
    fn find_by_id(&self, id: u64) -> Result<Option<User>, Self::Error> {
        Ok(self.users.get(&id).cloned())
    }
}""",
            "extension": ".rs",
            "expected_features": ["trait", "struct", "impl", "use"],
        },
        "typescript": {
            "code": """interface User {
    id: number;
    name: string;
    email: string;
}

type UserRole = 'admin' | 'user' | 'guest';

class UserService<T extends User> {
    private users: Map<number, T> = new Map();
    
    constructor(private validator: (user: T) => boolean) {}
    
    async createUser(userData: Omit<T, 'id'>): Promise<T> {
        const user = { ...userData, id: Date.now() } as T;
        
        if (!this.validator(user)) {
            throw new Error('Invalid user data');
        }
        
        this.users.set(user.id, user);
        return user;
    }
    
    findById(id: number): T | undefined {
        return this.users.get(id);
    }
    
    getAllUsers(): T[] {
        return Array.from(this.users.values());
    }
}

export { User, UserRole, UserService };""",
            "extension": ".ts",
            "expected_features": ["interface", "type", "class", "generic"],
        },
        "csharp": {
            "code": """using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Linq;

namespace UserManagement
{
    public interface IRepository<T> where T : class
    {
        Task<T> CreateAsync(T entity);
        Task<T?> GetByIdAsync(int id);
        Task<IEnumerable<T>> GetAllAsync();
    }
    
    public class User
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;
        public DateTime CreatedAt { get; set; }
    }
    
    public class UserService
    {
        private readonly IRepository<User> _repository;
        
        public UserService(IRepository<User> repository)
        {
            _repository = repository ?? throw new ArgumentNullException(nameof(repository));
        }
        
        public async Task<User> CreateUserAsync(string name, string email)
        {
            var user = new User
            {
                Name = name,
                Email = email,
                CreatedAt = DateTime.UtcNow
            };
            
            return await _repository.CreateAsync(user);
        }
        
        public async Task<IEnumerable<User>> GetActiveUsersAsync()
        {
            var users = await _repository.GetAllAsync();
            return users.Where(u => u.CreatedAt > DateTime.UtcNow.AddDays(-30));
        }
    }
}""",
            "extension": ".cs",
            "expected_features": ["namespace", "interface", "class", "async"],
        },
        "swift": {
            "code": """import Foundation

protocol Drawable {
    func draw()
}

protocol UserRepository {
    func create(_ user: User) async throws -> User
    func findById(_ id: UUID) async throws -> User?
}

struct User: Codable, Drawable {
    let id: UUID
    var name: String
    var email: String
    
    func draw() {
        print("Drawing user: \\(name)")
    }
}

@propertyWrapper
struct UserDefault<T> {
    let key: String
    let defaultValue: T
    
    var wrappedValue: T {
        get {
            UserDefaults.standard.object(forKey: key) as? T ?? defaultValue
        }
        set {
            UserDefaults.standard.set(newValue, forKey: key)
        }
    }
}

class UserService: ObservableObject {
    @Published var users: [User] = []
    @UserDefault(key: "maxUsers", defaultValue: 100)
    var maxUsers: Int
    
    private let repository: UserRepository
    
    init(repository: UserRepository) {
        self.repository = repository
    }
    
    func createUser(name: String, email: String) async throws {
        let user = User(id: UUID(), name: name, email: email)
        let created = try await repository.create(user)
        await MainActor.run {
            users.append(created)
        }
    }
}""",
            "extension": ".swift",
            "expected_features": ["protocol", "struct", "class", "@propertyWrapper"],
        },
        "kotlin": {
            "code": """import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

data class User(
    val id: String,
    val name: String,
    val email: String?
)

interface UserRepository {
    suspend fun create(user: User): User
    suspend fun findById(id: String): User?
    fun observeAll(): Flow<List<User>>
}

class UserService(
    private val repository: UserRepository
) {
    fun isValidEmail(email: String?): Boolean = 
        email?.contains("@") == true
    
    suspend fun createUser(name: String, email: String?): Result<User> {
        return try {
            val user = User(
                id = generateId(),
                name = name,
                email = email?.takeIf { isValidEmail(it) }
            )
            
            val created = repository.create(user)
            Result.success(created)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    fun getAllUsers(): Flow<List<User>> = 
        repository.observeAll()
            .map { users -> users.filter { it.email != null } }
    
    private fun generateId(): String = 
        System.currentTimeMillis().toString()
}

// Extension function
fun User.isValid(): Boolean = 
    name.isNotBlank() && (email == null || email.contains("@"))""",
            "extension": ".kt",
            "expected_features": ["data class", "interface", "suspend", "extension"],
        },
    }

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()
    os.chdir(temp_dir)

    results = {}

    try:
        # Create SQLite store
        store = SQLiteStore(":memory:")

        for language, test_data in test_cases.items():
            print(f"\n--- Testing {language.upper()} Plugin ---")

            try:
                # Create plugin
                plugin = PluginFactory.create_plugin(language, store, enable_semantic=False)
                print(f"✓ Created {language} plugin: {plugin.__class__.__name__}")

                # Create test file
                filename = f"test{test_data['extension']}"
                test_file = Path(filename)
                test_file.write_text(test_data["code"])

                # Index the file
                shard = plugin.indexFile(test_file, test_data["code"])
                symbols = shard.get("symbols", [])

                print(f"✓ Indexed file with {len(symbols)} symbols")

                # Show symbol types found
                if symbols:
                    symbol_types = set(s.get("kind", "unknown") for s in symbols)
                    print(f"  Symbol types: {', '.join(sorted(symbol_types))}")

                    # Show some symbols
                    for i, symbol in enumerate(symbols[:5]):
                        print(
                            f"    {i+1}. {symbol.get('kind', 'unknown')}: {symbol.get('symbol', 'N/A')}"
                        )

                # Test search functionality
                search_results = list(plugin.search("user", {"limit": 5}))
                print(f"✓ Search for 'user' found {len(search_results)} results")

                # Test definition lookup if available
                if hasattr(plugin, "getDefinition"):
                    # Try to find a class or function definition
                    test_symbols = ["User", "UserService", "createUser", "create"]
                    for test_sym in test_symbols:
                        definition = plugin.getDefinition(test_sym)
                        if definition:
                            print(
                                f"✓ Found definition for '{test_sym}': {definition.get('kind', 'unknown')}"
                            )
                            break

                # Check for advanced features based on plugin type
                advanced_features = []

                if hasattr(plugin, "analyze_imports"):
                    imports = plugin.analyze_imports(test_file)
                    if imports:
                        advanced_features.append(f"Import analysis ({len(imports)} imports)")

                if hasattr(plugin, "get_project_dependencies"):
                    deps = plugin.get_project_dependencies()
                    if deps:
                        advanced_features.append(f"Dependency analysis ({len(deps)} deps)")

                if hasattr(plugin, "findReferences"):
                    refs = plugin.findReferences("User")
                    if refs:
                        advanced_features.append(f"Reference tracking ({len(refs)} refs)")

                if advanced_features:
                    print(f"✓ Advanced features: {', '.join(advanced_features)}")

                results[language] = {
                    "success": True,
                    "symbols": len(symbols),
                    "search_results": len(search_results),
                    "plugin_type": plugin.__class__.__name__,
                }

            except Exception as e:
                print(f"✗ Error testing {language}: {e}")
                results[language] = {"success": False, "error": str(e), "plugin_type": "Failed"}

            finally:
                # Cleanup
                if test_file.exists():
                    test_file.unlink()

    finally:
        # Restore directory
        os.chdir(original_dir)
        import shutil

        shutil.rmtree(temp_dir)

    # Summary
    print("\n=== Test Summary ===")
    successful = [lang for lang, result in results.items() if result.get("success", False)]
    failed = [lang for lang, result in results.items() if not result.get("success", False)]

    print(f"✅ Successful: {len(successful)}/{len(results)} plugins")
    print(f"❌ Failed: {len(failed)}/{len(results)} plugins")

    if successful:
        print("\nSuccessful plugins:")
        for lang in successful:
            result = results[lang]
            print(
                f"  {lang}: {result['symbols']} symbols, {result['search_results']} search results ({result['plugin_type']})"
            )

    if failed:
        print("\nFailed plugins:")
        for lang in failed:
            result = results[lang]
            print(f"  {lang}: {result.get('error', 'Unknown error')}")

    return len(successful) == len(results)


if __name__ == "__main__":
    success = test_all_specialized_plugins()
    if success:
        print("\n🎉 All specialized language plugins are working correctly!")
    else:
        print("\n⚠️ Some specialized plugins need attention.")
        sys.exit(1)
