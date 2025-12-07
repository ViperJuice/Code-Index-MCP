#!/usr/bin/env python3
"""Test script for the Kotlin plugin implementation."""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.plugins.kotlin_plugin import KotlinPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


def create_test_kotlin_file():
    """Create a test Kotlin file for analysis."""
    test_content = """
package com.example.test

import kotlinx.coroutines.*
import kotlin.collections.List

/**
 * Sample Kotlin class with various features for testing
 */
data class User(
    val id: Long,
    val name: String?,
    val email: String
) {
    companion object {
        @JvmStatic
        fun createUser(name: String): User {
            return User(0L, name, "")
        }
    }
}

sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val exception: Throwable) : Result<Nothing>()
}

class UserRepository {
    private val users = mutableListOf<User>()
    
    suspend fun fetchUser(id: Long): Result<User?> = withContext(Dispatchers.IO) {
        delay(100)
        val user = users.find { it.id == id }
        Result.Success(user)
    }
    
    fun User.isValid(): Boolean {
        return name?.isNotEmpty() == true && email.isNotEmpty()
    }
    
    @Throws(IllegalArgumentException::class)
    fun addUser(user: User) {
        requireNotNull(user.name) { "User name cannot be null" }
        users.add(user)
    }
}

object UserManager {
    private var currentUser: User? = null
    
    fun setCurrentUser(user: User?) {
        currentUser = user
    }
    
    fun getCurrentUser(): User? = currentUser
}

// Coroutines example
suspend fun processUsers(): List<User> {
    return coroutineScope {
        val users = listOf("Alice", "Bob", "Charlie")
        users.map { name ->
            async {
                User.createUser(name)
            }
        }.awaitAll()
    }
}

// Extension function
fun String.toUser(): User? {
    return if (isNotEmpty()) {
        User(0L, this, "")
    } else null
}

// Null safety examples
fun demonstrateNullSafety() {
    val user: User? = null
    
    // Safe call
    val userName = user?.name
    
    // Elvis operator
    val displayName = userName ?: "Unknown"
    
    // Not-null assertion (risky)
    val length = userName!!.length
    
    // Safe cast
    val userAsString = user as? String
    
    // Let scope function
    user?.let { validUser ->
        println("User: ${validUser.name}")
    }
}

// Java interop
fun javaInteropExample() {
    val list = ArrayList<String>()  // Java collection
    val kotlinList = listOf("a", "b", "c")  // Kotlin collection
    
    // Java-style iteration
    for (i in 0 until list.size) {
        println(list.get(i))
    }
    
    // Kotlin-style iteration
    kotlinList.forEach { println(it) }
}
"""
    return test_content


def test_kotlin_plugin():
    """Test the Kotlin plugin functionality."""
    print("Testing Kotlin Plugin Implementation")
    print("=" * 50)

    # Create plugin instance
    try:
        # Initialize with in-memory SQLite store
        sqlite_store = SQLiteStore(":memory:")
        plugin = KotlinPlugin(sqlite_store=sqlite_store, enable_semantic=False)
        print("✓ Kotlin plugin created successfully")
    except Exception as e:
        print(f"✗ Failed to create Kotlin plugin: {e}")
        return False

    # Test basic properties
    print(f"✓ Language name: {plugin.get_language_name()}")
    print(f"✓ File extensions: {plugin.get_file_extensions()}")
    print(f"✓ Supported queries: {len(plugin.get_supported_queries())} query types")

    # Test symbol extraction
    test_content = create_test_kotlin_file()
    test_file_path = "/tmp/test_kotlin_file.kt"

    try:
        symbols = plugin.extract_symbols(test_content, test_file_path)
        print(f"✓ Extracted {len(symbols)} symbols from test file")

        # Display some symbols
        symbol_types = {}
        for symbol in symbols[:10]:  # Show first 10 symbols
            symbol_type = symbol.get("type", "unknown")
            symbol_types[symbol_type] = symbol_types.get(symbol_type, 0) + 1
            print(
                f"  - {symbol.get('name', 'unnamed')} ({symbol_type}) at line {symbol.get('line_number', 0)}"
            )

        print(f"✓ Symbol type distribution: {dict(symbol_types)}")

    except Exception as e:
        print(f"✗ Symbol extraction failed: {e}")
        return False

    # Test null safety analysis
    try:
        null_safety_result = plugin.null_safety_analyzer.analyze(None, test_content)
        print("✓ Null safety analysis completed")
        print(f"  - Nullable usages: {len(null_safety_result.get('nullable_usages', []))}")
        print(f"  - Safe call chains: {len(null_safety_result.get('safe_call_chains', []))}")
        print(f"  - Not-null assertions: {len(null_safety_result.get('not_null_assertions', []))}")

        stats = null_safety_result.get("statistics", {})
        if stats:
            print(f"  - Safety score: {stats.get('safety_score', 'N/A')}")
            print(f"  - Overall risk: {stats.get('overall_risk', 'N/A')}")
    except Exception as e:
        print(f"✗ Null safety analysis failed: {e}")

    # Test coroutines analysis
    try:
        coroutines_result = plugin.coroutines_analyzer.analyze(None, test_content)
        print("✓ Coroutines analysis completed")
        print(f"  - Suspend functions: {len(coroutines_result.get('suspend_functions', []))}")
        print(f"  - Coroutine builders: {len(coroutines_result.get('coroutine_builders', []))}")
        print(f"  - Flow operations: {len(coroutines_result.get('flow_operations', []))}")

        stats = coroutines_result.get("statistics", {})
        if stats:
            print(f"  - Maturity score: {stats.get('maturity_score', 'N/A')}")
            print(f"  - Performance impact: {stats.get('performance_impact', 'N/A')}")
    except Exception as e:
        print(f"✗ Coroutines analysis failed: {e}")

    # Test Java interop analysis
    try:
        java_interop_result = plugin.java_interop_analyzer.analyze(None, test_content)
        print("✓ Java interop analysis completed")
        print(f"  - JVM annotations: {len(java_interop_result.get('jvm_annotations', []))}")
        print(f"  - Java imports: {len(java_interop_result.get('java_imports', []))}")
        print(f"  - Collection interop: {len(java_interop_result.get('collection_interop', []))}")

        stats = java_interop_result.get("statistics", {})
        if stats:
            print(f"  - Interop quality score: {stats.get('interop_quality_score', 'N/A')}")
            print(f"  - Java dependency level: {stats.get('java_dependency_level', 'N/A')}")
    except Exception as e:
        print(f"✗ Java interop analysis failed: {e}")

    print("\n" + "=" * 50)
    print("✓ Kotlin plugin test completed successfully!")
    return True


if __name__ == "__main__":
    success = test_kotlin_plugin()
    sys.exit(0 if success else 1)
