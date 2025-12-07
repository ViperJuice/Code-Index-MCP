#!/usr/bin/env python3
"""
Comprehensive MCP Server Validation Test

This script validates all 7 specialized language plugins with:
- Small test repositories
- Efficient database management
- Comprehensive result tracking
- Real MCP server integration testing
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.config.settings import get_settings
from mcp_server.core.logging import get_logger
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugin_system.plugin_loader import PluginLoader
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.plugin_system.plugin_registry import PluginRegistry
from mcp_server.storage.sqlite_store import SQLiteStore

logger = get_logger(__name__)


@dataclass
class TestResult:
    """Represents the result of a single test."""

    language: str
    test_type: str
    success: bool
    duration: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language,
            "test_type": self.test_type,
            "success": self.success,
            "duration": self.duration,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class LanguageTestSuite:
    """Test suite configuration for a language."""

    language: str
    file_extension: str
    sample_files: Dict[str, str]
    expected_symbols: List[str]
    search_queries: List[str]
    advanced_features: List[str] = field(default_factory=list)


class ComprehensiveMCPTester:
    """Comprehensive MCP Server testing framework."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.test_dir = None
        self.db_path = None

    def setup_test_environment(self) -> Path:
        """Set up temporary test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="mcp_test_"))
        self.db_path = self.test_dir / "test.db"

        # Create necessary directories
        (self.test_dir / "repos").mkdir()
        (self.test_dir / "logs").mkdir()

        return self.test_dir

    def cleanup_test_environment(self):
        """Clean up test environment."""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def get_test_suites(self) -> Dict[str, LanguageTestSuite]:
        """Get test configurations for all languages."""
        return {
            "java": LanguageTestSuite(
                language="java",
                file_extension=".java",
                sample_files={
                    "Main.java": """package com.example;

import java.util.*;
import java.util.stream.Collectors;

public class Main {
    public static void main(String[] args) {
        UserService service = new UserService();
        service.processUsers();
    }
}""",
                    "UserService.java": """package com.example;

import java.util.*;

public class UserService {
    private List<User> users = new ArrayList<>();
    
    public void processUsers() {
        users.stream()
            .filter(u -> u.isActive())
            .forEach(System.out::println);
    }
    
    public Optional<User> findById(Long id) {
        return users.stream()
            .filter(u -> u.getId().equals(id))
            .findFirst();
    }
}""",
                    "User.java": """package com.example;

public class User {
    private Long id;
    private String name;
    private boolean active;
    
    public User(Long id, String name) {
        this.id = id;
        this.name = name;
        this.active = true;
    }
    
    public Long getId() { return id; }
    public String getName() { return name; }
    public boolean isActive() { return active; }
}""",
                },
                expected_symbols=["Main", "UserService", "User", "processUsers", "findById"],
                search_queries=["User", "process", "find"],
                advanced_features=["imports", "packages", "generics"],
            ),
            "go": LanguageTestSuite(
                language="go",
                file_extension=".go",
                sample_files={
                    "main.go": """package main

import (
    "fmt"
    "log"
)

func main() {
    service := NewUserService()
    users, err := service.GetAllUsers()
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Found %d users\\n", len(users))
}""",
                    "user.go": """package main

type User struct {
    ID   int
    Name string
    Email string
}

type UserService struct {
    users []User
}

func NewUserService() *UserService {
    return &UserService{
        users: make([]User, 0),
    }
}

func (s *UserService) GetAllUsers() ([]User, error) {
    return s.users, nil
}

func (s *UserService) AddUser(user User) error {
    s.users = append(s.users, user)
    return nil
}""",
                },
                expected_symbols=["main", "User", "UserService", "NewUserService", "GetAllUsers"],
                search_queries=["User", "Service", "Get"],
                advanced_features=["packages", "imports", "methods"],
            ),
            "rust": LanguageTestSuite(
                language="rust",
                file_extension=".rs",
                sample_files={
                    "main.rs": """mod user;

use user::{User, UserService};

fn main() {
    let mut service = UserService::new();
    let user = User::new(1, "Alice".to_string());
    service.add_user(user);
    
    match service.find_user(1) {
        Some(u) => println!("Found user: {}", u.name),
        None => println!("User not found"),
    }
}""",
                    "user.rs": """#[derive(Debug, Clone)]
pub struct User {
    pub id: u32,
    pub name: String,
}

impl User {
    pub fn new(id: u32, name: String) -> Self {
        Self { id, name }
    }
}

pub struct UserService {
    users: Vec<User>,
}

impl UserService {
    pub fn new() -> Self {
        Self { users: Vec::new() }
    }
    
    pub fn add_user(&mut self, user: User) {
        self.users.push(user);
    }
    
    pub fn find_user(&self, id: u32) -> Option<&User> {
        self.users.iter().find(|u| u.id == id)
    }
}""",
                },
                expected_symbols=["User", "UserService", "new", "add_user", "find_user"],
                search_queries=["User", "find", "add"],
                advanced_features=["modules", "traits", "ownership"],
            ),
            "typescript": LanguageTestSuite(
                language="typescript",
                file_extension=".ts",
                sample_files={
                    "index.ts": """import { UserService } from './userService';
import { User } from './types';

const service = new UserService();

async function main() {
    const user: User = {
        id: 1,
        name: 'Alice',
        email: 'alice@example.com'
    };
    
    await service.createUser(user);
    const found = await service.findUser(1);
    console.log('Found user:', found);
}

main().catch(console.error);""",
                    "types.ts": """export interface User {
    id: number;
    name: string;
    email: string;
}

export type UserRole = 'admin' | 'user' | 'guest';

export interface UserWithRole extends User {
    role: UserRole;
}""",
                    "userService.ts": """import { User } from './types';

export class UserService {
    private users: Map<number, User> = new Map();
    
    async createUser(user: User): Promise<User> {
        this.users.set(user.id, user);
        return user;
    }
    
    async findUser(id: number): Promise<User | undefined> {
        return this.users.get(id);
    }
    
    async getAllUsers(): Promise<User[]> {
        return Array.from(this.users.values());
    }
}""",
                },
                expected_symbols=["UserService", "User", "UserRole", "createUser", "findUser"],
                search_queries=["User", "Service", "create"],
                advanced_features=["interfaces", "types", "generics", "async"],
            ),
            "csharp": LanguageTestSuite(
                language="csharp",
                file_extension=".cs",
                sample_files={
                    "Program.cs": """using System;
using System.Threading.Tasks;

namespace UserApp
{
    class Program
    {
        static async Task Main(string[] args)
        {
            var service = new UserService();
            var user = await service.CreateUserAsync("Alice", "alice@example.com");
            Console.WriteLine($"Created user: {user.Name}");
        }
    }
}""",
                    "User.cs": """using System;

namespace UserApp
{
    public class User
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Email { get; set; }
        public DateTime CreatedAt { get; set; }
        
        public User(string name, string email)
        {
            Name = name;
            Email = email;
            CreatedAt = DateTime.UtcNow;
        }
    }
}""",
                    "UserService.cs": """using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Linq;

namespace UserApp
{
    public class UserService
    {
        private readonly List<User> _users = new List<User>();
        private int _nextId = 1;
        
        public async Task<User> CreateUserAsync(string name, string email)
        {
            var user = new User(name, email) { Id = _nextId++ };
            _users.Add(user);
            return await Task.FromResult(user);
        }
        
        public async Task<User> GetUserAsync(int id)
        {
            var user = _users.FirstOrDefault(u => u.Id == id);
            return await Task.FromResult(user);
        }
    }
}""",
                },
                expected_symbols=["User", "UserService", "CreateUserAsync", "GetUserAsync"],
                search_queries=["User", "Create", "Async"],
                advanced_features=["namespaces", "properties", "async", "LINQ"],
            ),
            "swift": LanguageTestSuite(
                language="swift",
                file_extension=".swift",
                sample_files={
                    "main.swift": """import Foundation

let service = UserService()

Task {
    do {
        let user = try await service.createUser(name: "Alice", email: "alice@example.com")
        print("Created user: \\(user.name)")
    } catch {
        print("Error: \\(error)")
    }
}

RunLoop.main.run()""",
                    "User.swift": """import Foundation

struct User: Codable, Identifiable {
    let id: UUID
    var name: String
    var email: String
    
    init(name: String, email: String) {
        self.id = UUID()
        self.name = name
        self.email = email
    }
}

extension User: CustomStringConvertible {
    var description: String {
        "User(\\(name), \\(email))"
    }
}""",
                    "UserService.swift": """import Foundation

@MainActor
class UserService: ObservableObject {
    @Published var users: [User] = []
    
    func createUser(name: String, email: String) async throws -> User {
        let user = User(name: name, email: email)
        users.append(user)
        return user
    }
    
    func findUser(by id: UUID) -> User? {
        users.first { $0.id == id }
    }
    
    func deleteUser(_ user: User) {
        users.removeAll { $0.id == user.id }
    }
}""",
                },
                expected_symbols=["User", "UserService", "createUser", "findUser"],
                search_queries=["User", "Service", "create"],
                advanced_features=["protocols", "extensions", "async", "property wrappers"],
            ),
            "kotlin": LanguageTestSuite(
                language="kotlin",
                file_extension=".kt",
                sample_files={
                    "Main.kt": """import kotlinx.coroutines.*

fun main() = runBlocking {
    val service = UserService()
    
    val user = service.createUser("Alice", "alice@example.com")
    println("Created user: ${user.name}")
    
    service.getAllUsers().collect { users ->
        println("Total users: ${users.size}")
    }
}""",
                    "User.kt": """data class User(
    val id: String,
    val name: String,
    val email: String?
) {
    fun isValid(): Boolean = name.isNotBlank() && email?.contains("@") == true
}

// Extension function
fun User.displayName(): String = "$name (${email ?: "no email"})"
""",
                    "UserService.kt": """import kotlinx.coroutines.flow.*
import java.util.UUID

class UserService {
    private val users = mutableListOf<User>()
    private val usersFlow = MutableStateFlow<List<User>>(emptyList())
    
    suspend fun createUser(name: String, email: String?): User {
        val user = User(
            id = UUID.randomUUID().toString(),
            name = name,
            email = email
        )
        users.add(user)
        usersFlow.emit(users.toList())
        return user
    }
    
    fun getAllUsers(): Flow<List<User>> = usersFlow.asStateFlow()
    
    fun findUserById(id: String): User? = users.find { it.id == id }
}""",
                },
                expected_symbols=["User", "UserService", "createUser", "getAllUsers"],
                search_queries=["User", "create", "Flow"],
                advanced_features=["coroutines", "data classes", "extensions", "null safety"],
            ),
        }

    async def test_plugin_initialization(
        self, language: str, suite: LanguageTestSuite
    ) -> TestResult:
        """Test plugin initialization."""
        start_time = time.time()

        try:
            # Import and create plugin
            from mcp_server.plugins.plugin_factory import PluginFactory

            store = SQLiteStore(":memory:")
            plugin = PluginFactory.create_plugin(language, store, enable_semantic=False)

            duration = time.time() - start_time
            return TestResult(
                language=language,
                test_type="initialization",
                success=True,
                duration=duration,
                message=f"Successfully initialized {plugin.__class__.__name__}",
                details={"plugin_class": plugin.__class__.__name__},
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                language=language,
                test_type="initialization",
                success=False,
                duration=duration,
                message=f"Failed to initialize: {str(e)}",
                details={"error": str(e)},
            )

    async def test_file_indexing(self, language: str, suite: LanguageTestSuite) -> TestResult:
        """Test file indexing capabilities."""
        start_time = time.time()

        try:
            from mcp_server.plugins.plugin_factory import PluginFactory

            # Create test repository
            repo_dir = self.test_dir / "repos" / language
            repo_dir.mkdir(parents=True)

            # Write sample files
            for filename, content in suite.sample_files.items():
                (repo_dir / filename).write_text(content)

            # Create plugin and index files
            store = SQLiteStore(":memory:")
            plugin = PluginFactory.create_plugin(language, store, enable_semantic=False)

            total_symbols = 0
            indexed_files = []

            for filename, content in suite.sample_files.items():
                file_path = repo_dir / filename
                shard = plugin.indexFile(file_path, content)
                symbols = shard.get("symbols", [])
                total_symbols += len(symbols)
                indexed_files.append(
                    {
                        "file": filename,
                        "symbols": len(symbols),
                        "types": list(set(s.get("kind", "unknown") for s in symbols)),
                    }
                )

            duration = time.time() - start_time
            return TestResult(
                language=language,
                test_type="indexing",
                success=total_symbols > 0,
                duration=duration,
                message=f"Indexed {len(indexed_files)} files with {total_symbols} symbols",
                details={
                    "total_symbols": total_symbols,
                    "files": indexed_files,
                    "indexed_count": plugin.get_indexed_count(),
                },
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                language=language,
                test_type="indexing",
                success=False,
                duration=duration,
                message=f"Indexing failed: {str(e)}",
                details={"error": str(e)},
            )

    async def test_search_functionality(
        self, language: str, suite: LanguageTestSuite
    ) -> TestResult:
        """Test search functionality."""
        start_time = time.time()

        try:
            from mcp_server.plugins.plugin_factory import PluginFactory

            # Set up and index files
            repo_dir = self.test_dir / "repos" / language
            repo_dir.mkdir(parents=True, exist_ok=True)

            store = SQLiteStore(":memory:")
            plugin = PluginFactory.create_plugin(language, store, enable_semantic=False)

            # Index files
            for filename, content in suite.sample_files.items():
                file_path = repo_dir / filename
                file_path.write_text(content)
                plugin.indexFile(file_path, content)

            # Perform searches
            search_results = {}
            for query in suite.search_queries:
                results = list(plugin.search(query, {"limit": 10}))
                search_results[query] = {
                    "count": len(results),
                    "symbols": [r.get("symbol", "N/A") for r in results[:3]],
                }

            total_results = sum(r["count"] for r in search_results.values())
            duration = time.time() - start_time

            return TestResult(
                language=language,
                test_type="search",
                success=total_results > 0,
                duration=duration,
                message=f"Found {total_results} results across {len(suite.search_queries)} queries",
                details={"search_results": search_results},
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                language=language,
                test_type="search",
                success=False,
                duration=duration,
                message=f"Search failed: {str(e)}",
                details={"error": str(e)},
            )

    async def test_advanced_features(self, language: str, suite: LanguageTestSuite) -> TestResult:
        """Test advanced language-specific features."""
        start_time = time.time()

        try:
            from mcp_server.plugins.plugin_factory import PluginFactory

            store = SQLiteStore(":memory:")
            plugin = PluginFactory.create_plugin(language, store, enable_semantic=False)

            features_found = []

            # Check for advanced capabilities
            if hasattr(plugin, "analyze_imports"):
                features_found.append("import analysis")

            if hasattr(plugin, "get_project_dependencies"):
                features_found.append("dependency tracking")

            if hasattr(plugin, "findReferences"):
                features_found.append("reference finding")

            if hasattr(plugin, "getDefinition"):
                features_found.append("definition lookup")

            if hasattr(plugin, "analyze_types"):
                features_found.append("type analysis")

            duration = time.time() - start_time
            return TestResult(
                language=language,
                test_type="advanced_features",
                success=len(features_found) > 0,
                duration=duration,
                message=f"Found {len(features_found)} advanced features",
                details={"features": features_found},
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                language=language,
                test_type="advanced_features",
                success=False,
                duration=duration,
                message=f"Feature test failed: {str(e)}",
                details={"error": str(e)},
            )

    async def test_mcp_integration(self, language: str, suite: LanguageTestSuite) -> TestResult:
        """Test full MCP server integration."""
        start_time = time.time()

        try:
            # Set up test repository
            repo_dir = self.test_dir / "repos" / language
            repo_dir.mkdir(parents=True, exist_ok=True)

            for filename, content in suite.sample_files.items():
                (repo_dir / filename).write_text(content)

            # Create MCP server command
            env = os.environ.copy()
            env.update(
                {
                    "DATABASE_PATH": str(self.db_path),
                    "SEMANTIC_SEARCH_ENABLED": "false",
                    "LOG_LEVEL": "INFO",
                }
            )

            # Start MCP server
            server_proc = subprocess.Popen(
                [sys.executable, "mcp_server_cli.py"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
            )

            # Wait for server to start
            await asyncio.sleep(2)

            # Send reindex command
            request = {
                "jsonrpc": "2.0",
                "method": "reindex",
                "params": {"path": str(repo_dir)},
                "id": 1,
            }

            server_proc.stdin.write(json.dumps(request) + "\n")
            server_proc.stdin.flush()

            # Wait for indexing
            await asyncio.sleep(3)

            # Send status command
            request = {"jsonrpc": "2.0", "method": "get_status", "params": {}, "id": 2}

            server_proc.stdin.write(json.dumps(request) + "\n")
            server_proc.stdin.flush()

            # Read response
            response_line = server_proc.stdout.readline()
            if response_line:
                response = json.loads(response_line)

                # Terminate server
                server_proc.terminate()
                await asyncio.sleep(1)

                duration = time.time() - start_time

                # Check if language appears in status
                result = response.get("result", {})
                plugins = result.get("plugins", {})

                success = language in plugins and plugins[language]["indexed_files"] > 0

                return TestResult(
                    language=language,
                    test_type="mcp_integration",
                    success=success,
                    duration=duration,
                    message=f"MCP integration {'successful' if success else 'failed'}",
                    details={"status": plugins.get(language, {})},
                )
            else:
                server_proc.terminate()
                raise Exception("No response from MCP server")

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                language=language,
                test_type="mcp_integration",
                success=False,
                duration=duration,
                message=f"MCP integration failed: {str(e)}",
                details={"error": str(e)},
            )

    async def run_language_tests(self, language: str, suite: LanguageTestSuite) -> List[TestResult]:
        """Run all tests for a language."""
        print(f"\n{'='*60}")
        print(f"Testing {language.upper()} Plugin")
        print(f"{'='*60}")

        results = []

        # Run each test
        tests = [
            ("Initialization", self.test_plugin_initialization),
            ("File Indexing", self.test_file_indexing),
            ("Search Functionality", self.test_search_functionality),
            ("Advanced Features", self.test_advanced_features),
            ("MCP Integration", self.test_mcp_integration),
        ]

        for test_name, test_func in tests:
            print(f"\n{test_name}...", end=" ", flush=True)
            result = await test_func(language, suite)
            results.append(result)

            if result.success:
                print(f"✅ PASSED ({result.duration:.2f}s)")
                if result.details:
                    print(f"   {result.message}")
            else:
                print(f"❌ FAILED ({result.duration:.2f}s)")
                print(f"   {result.message}")

        return results

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        # Group results by language
        by_language = {}
        for result in self.results:
            if result.language not in by_language:
                by_language[result.language] = []
            by_language[result.language].append(result)

        # Calculate statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests

        # Language summaries
        language_summaries = {}
        for language, results in by_language.items():
            passed = sum(1 for r in results if r.success)
            total = len(results)
            language_summaries[language] = {
                "passed": passed,
                "total": total,
                "success_rate": (passed / total * 100) if total > 0 else 0,
                "tests": {r.test_type: r.success for r in results},
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            },
            "languages": language_summaries,
            "detailed_results": [r.to_dict() for r in self.results],
        }

    async def run_all_tests(self):
        """Run comprehensive tests for all languages."""
        print("🚀 Starting Comprehensive MCP Validation Tests")
        print(f"Test Directory: {self.test_dir}")
        print(f"Database: {self.db_path}")

        # Get all test suites
        test_suites = self.get_test_suites()

        # Run tests for each language
        for language, suite in test_suites.items():
            language_results = await self.run_language_tests(language, suite)
            self.results.extend(language_results)

        # Generate and display report
        report = self.generate_report()

        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY REPORT")
        print("=" * 80)

        print(f"\n📈 Overall Results:")
        print(f"   Total Tests: {report['summary']['total_tests']}")
        print(f"   Passed: {report['summary']['passed']} ✅")
        print(f"   Failed: {report['summary']['failed']} ❌")
        print(f"   Success Rate: {report['summary']['success_rate']:.1f}%")

        print(f"\n📋 Language Results:")
        for language, summary in report["languages"].items():
            status = (
                "✅"
                if summary["success_rate"] == 100
                else "⚠️" if summary["success_rate"] > 0 else "❌"
            )
            print(
                f"   {status} {language.upper()}: {summary['passed']}/{summary['total']} tests passed ({summary['success_rate']:.1f}%)"
            )

            # Show failed tests
            failed_tests = [test for test, passed in summary["tests"].items() if not passed]
            if failed_tests:
                print(f"      Failed: {', '.join(failed_tests)}")

        # Save detailed report
        report_path = self.test_dir / "test_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Detailed report saved to: {report_path}")

        return report["summary"]["success_rate"] == 100


async def main():
    """Main test execution."""
    tester = ComprehensiveMCPTester()

    try:
        # Set up test environment
        tester.setup_test_environment()

        # Run all tests
        success = await tester.run_all_tests()

        if success:
            print("\n🎉 All tests PASSED! MCP server is fully functional.")
            return 0
        else:
            print("\n⚠️ Some tests FAILED. Please review the report for details.")
            return 1

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        logger.exception("Test execution error")
        return 2

    finally:
        # Keep test directory for debugging if tests failed
        if success:
            tester.cleanup_test_environment()
        else:
            print(f"\n🔍 Test directory preserved for debugging: {tester.test_dir}")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
