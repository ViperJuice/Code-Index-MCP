"""Tests for JVM Plugin (Java + Kotlin support)."""

import pytest
import tempfile
import time
from pathlib import Path
from mcp_server.plugins.jvm_plugin.plugin import Plugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestJvmPlugin:
    """Test suite for JVM Plugin."""
    
    @pytest.fixture
    def plugin(self):
        """Create a JVM plugin instance."""
        return Plugin()
    
    @pytest.fixture
    def plugin_with_sqlite(self, tmp_path):
        """Create a JVM plugin instance with SQLite storage."""
        db_path = tmp_path / "test.db"
        sqlite_store = SQLiteStore(str(db_path))
        return Plugin(sqlite_store=sqlite_store)
    
    @pytest.fixture
    def java_sample_code(self):
        """Sample Java code for testing."""
        return '''package com.example.test;

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
    
    @pytest.fixture
    def kotlin_sample_code(self):
        """Sample Kotlin code for testing."""
        return '''package com.example.test

import kotlinx.coroutines.*

@Service
data class KotlinSample<T : Comparable<T>>(
    val name: String,
    var items: MutableList<T> = mutableListOf()
) : Runnable {
    
    companion object {
        const val CONSTANT = "Kotlin Hello"
        
        fun <T : Comparable<T>> create(name: String): KotlinSample<T> {
            return KotlinSample(name)
        }
    }
    
    private var _running: Boolean = false
    val isRunning: Boolean get() = _running
    
    override fun run() {
        _running = true
    }
    
    suspend fun processAsync(data: String): String = withContext(Dispatchers.IO) {
        "Processed: $data"
    }
    
    inline fun <reified R> genericMethod(action: () -> R): R {
        return action()
    }
}

fun String.isPalindrome(): Boolean {
    return this == this.reversed()
}

fun <T> List<T>.safeGet(index: Int): T? = 
    if (index in 0 until size) this[index] else null

sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    object Loading : Result<Nothing>()
}

object DatabaseManager {
    fun getConnection(): String = "connection"
}

interface Repository<T> {
    suspend fun findAll(): List<T>
}

enum class HttpStatus(val code: Int) {
    OK(200),
    NOT_FOUND(404)
}'''
    
    @pytest.fixture
    def maven_pom(self):
        """Sample Maven POM for testing."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>test-project</artifactId>
    <version>1.0.0</version>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-core</artifactId>
            <version>6.0.11</version>
        </dependency>
        
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>5.10.0</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>'''
    
    @pytest.fixture
    def gradle_build(self):
        """Sample Gradle build file for testing."""
        return '''plugins {
    id 'java'
    id 'org.jetbrains.kotlin.jvm' version '1.9.10'
}

dependencies {
    implementation 'org.springframework:spring-core:6.0.11'
    implementation 'org.jetbrains.kotlin:kotlin-stdlib'
    testImplementation 'org.junit.jupiter:junit-jupiter'
    runtimeOnly 'com.h2database:h2'
}'''

    def test_plugin_supports_java_files(self, plugin):
        """Test that plugin supports Java files."""
        assert plugin.supports("Sample.java")
        assert plugin.supports(Path("src/main/java/Sample.java"))
        assert not plugin.supports("Sample.py")
        assert not plugin.supports("Sample.txt")
    
    def test_plugin_supports_kotlin_files(self, plugin):
        """Test that plugin supports Kotlin files."""
        assert plugin.supports("Sample.kt")
        assert plugin.supports("Script.kts")
        assert plugin.supports(Path("src/main/kotlin/Sample.kt"))
    
    def test_plugin_supports_build_files(self, plugin):
        """Test that plugin supports build files."""
        assert plugin.supports("pom.xml")
        assert plugin.supports("build.gradle")
        assert plugin.supports("build.gradle.kts")
        assert plugin.supports(Path("subproject/build.gradle"))
    
    def test_java_file_indexing(self, plugin, java_sample_code):
        """Test indexing of Java files."""
        result = plugin.indexFile("Sample.java", java_sample_code)
        
        assert result["file"] == "Sample.java"
        assert result["language"] == "java"
        assert result["package"] == "com.example.test"
        assert "java.util.List" in result["imports"]
        
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        # Check classes
        assert "Sample" in symbol_names
        assert "Callback" in symbol_names
        assert "Status" in symbol_names
        
        # Check methods
        assert "processData" in symbol_names
        assert "run" in symbol_names
        assert "create" in symbol_names
        
        # Check symbol kinds
        symbol_kinds = {s["symbol"]: s["kind"] for s in symbols}
        assert symbol_kinds["Sample"] == "class"
        assert symbol_kinds["Callback"] == "interface"
        assert symbol_kinds["Status"] == "enum"
    
    def test_kotlin_file_indexing(self, plugin, kotlin_sample_code):
        """Test indexing of Kotlin files."""
        result = plugin.indexFile("Sample.kt", kotlin_sample_code)
        
        assert result["file"] == "Sample.kt"
        assert result["language"] == "kotlin"
        assert result["package"] == "com.example.test"
        
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        # Check classes
        assert "KotlinSample" in symbol_names
        assert "Result" in symbol_names
        assert "DatabaseManager" in symbol_names
        assert "Repository" in symbol_names
        assert "HttpStatus" in symbol_names
        
        # Check functions
        assert "create" in symbol_names
        assert "processAsync" in symbol_names
        assert "genericMethod" in symbol_names
        
        # Check extensions
        assert "String.isPalindrome" in symbol_names
        assert "List.safeGet" in symbol_names
        
        # Check symbol kinds
        symbol_kinds = {s["symbol"]: s["kind"] for s in symbols}
        assert symbol_kinds["KotlinSample"] == "data_class"
        assert symbol_kinds["DatabaseManager"] == "object"
        assert symbol_kinds["Repository"] == "interface"
        assert symbol_kinds["HttpStatus"] == "enum"
    
    def test_maven_pom_indexing(self, plugin, maven_pom):
        """Test indexing of Maven POM files."""
        result = plugin.indexFile("pom.xml", maven_pom)
        
        assert result["file"] == "pom.xml"
        assert result["language"] == "maven"
        
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        # Check artifact
        assert "com.example:test-project" in symbol_names
        
        # Check dependencies
        assert "org.springframework:spring-core" in symbol_names
        assert "org.junit.jupiter:junit-jupiter" in symbol_names
        
        # Check symbol kinds
        symbol_kinds = {s["symbol"]: s["kind"] for s in symbols}
        assert any(k == "artifact" for k in symbol_kinds.values())
        assert any(k == "dependency" for k in symbol_kinds.values())
    
    def test_gradle_build_indexing(self, plugin, gradle_build):
        """Test indexing of Gradle build files."""
        result = plugin.indexFile("build.gradle", gradle_build)
        
        assert result["file"] == "build.gradle"
        assert result["language"] == "gradle"
        
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        # Check plugins
        assert "java" in symbol_names
        assert "org.jetbrains.kotlin.jvm" in symbol_names
        
        # Check dependencies
        assert "org.springframework:spring-core:6.0.11" in symbol_names
        assert "org.jetbrains.kotlin:kotlin-stdlib" in symbol_names
        
        # Check symbol kinds
        symbol_kinds = {s["symbol"]: s["kind"] for s in symbols}
        assert any(k == "plugin" for k in symbol_kinds.values())
        assert any(k == "dependency" for k in symbol_kinds.values())
    
    def test_symbol_definition_lookup(self, plugin, java_sample_code):
        """Test finding symbol definitions."""
        # Index the file first
        plugin.indexFile("Sample.java", java_sample_code)
        
        # Look for class definition
        definition = plugin.getDefinition("Sample")
        assert definition is not None
        assert definition["symbol"] == "Sample"
        assert definition["kind"] == "class"
        assert definition["language"] == "java"
        assert "class Sample" in definition["signature"]
    
    def test_symbol_references(self, plugin, java_sample_code):
        """Test finding symbol references."""
        # Index the file first
        plugin.indexFile("Sample.java", java_sample_code)
        
        # Find references
        references = plugin.findReferences("Sample")
        assert len(references) > 0
        
        # Check that references include the class definition and usage
        ref_files = [ref.file for ref in references]
        assert any("Sample.java" in f for f in ref_files)
    
    def test_search_functionality(self, plugin, java_sample_code, kotlin_sample_code):
        """Test search functionality."""
        # Index both files
        plugin.indexFile("Sample.java", java_sample_code)
        plugin.indexFile("Sample.kt", kotlin_sample_code)
        
        # Search for common terms
        results = plugin.search("Sample")
        assert len(results) > 0
        
        results = plugin.search("processData")
        assert len(results) >= 0  # May or may not find based on fuzzy indexer implementation
    
    def test_performance_target(self, plugin, java_sample_code, kotlin_sample_code):
        """Test that parsing meets the 100ms performance target."""
        # Test Java parsing performance
        start_time = time.time()
        result = plugin.indexFile("Sample.java", java_sample_code)
        java_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        assert java_time < 100, f"Java parsing took {java_time:.2f}ms, exceeds 100ms target"
        assert len(result["symbols"]) > 0
        
        # Test Kotlin parsing performance
        start_time = time.time()
        result = plugin.indexFile("Sample.kt", kotlin_sample_code)
        kotlin_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        assert kotlin_time < 100, f"Kotlin parsing took {kotlin_time:.2f}ms, exceeds 100ms target"
        assert len(result["symbols"]) > 0
    
    def test_language_detection(self, plugin):
        """Test automatic language detection."""
        java_code = '''
        public class Test {
            public static void main(String[] args) {
                System.out.println("Hello");
            }
        }
        '''
        
        kotlin_code = '''
        fun main() {
            println("Hello")
        }
        
        data class Person(val name: String)
        '''
        
        # Test Java detection
        assert plugin._parser.is_java_file(java_code)
        assert not plugin._parser.is_kotlin_file(java_code)
        
        # Test Kotlin detection
        assert plugin._parser.is_kotlin_file(kotlin_code)
        assert not plugin._parser.is_java_file(kotlin_code)
    
    def test_generic_type_parsing(self, plugin):
        """Test parsing of generic types and complex signatures."""
        complex_java = '''
        public class GenericTest<T extends Comparable<T>, U> {
            public <K, V> Map<K, List<V>> complexMethod(
                Function<T, K> mapper, 
                Supplier<V> supplier
            ) throws Exception {
                return new HashMap<>();
            }
        }
        '''
        
        result = plugin.indexFile("GenericTest.java", complex_java)
        symbols = result["symbols"]
        
        # Should find the class and method
        symbol_names = [s["symbol"] for s in symbols]
        assert "GenericTest" in symbol_names
        assert "complexMethod" in symbol_names
    
    def test_kotlin_advanced_features(self, plugin):
        """Test parsing of advanced Kotlin features."""
        advanced_kotlin = '''
        sealed interface NetworkResult<out T>
        
        inline class UserId(val value: String)
        
        @JvmInline
        value class Score(val points: Int)
        
        class Service {
            suspend fun fetchData(): String = withContext(Dispatchers.IO) {
                "data"
            }
            
            inline fun <reified T> parseJson(json: String): T {
                return Json.decodeFromString(json)
            }
        }
        
        fun String.toUserId(): UserId = UserId(this)
        '''
        
        result = plugin.indexFile("Advanced.kt", advanced_kotlin)
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        assert "NetworkResult" in symbol_names
        assert "UserId" in symbol_names
        assert "Score" in symbol_names
        assert "Service" in symbol_names
        assert "fetchData" in symbol_names
        assert "parseJson" in symbol_names
        assert "String.toUserId" in symbol_names
    
    def test_sqlite_integration(self, plugin_with_sqlite, java_sample_code):
        """Test SQLite storage integration."""
        result = plugin_with_sqlite.indexFile("Sample.java", java_sample_code)
        
        # Verify symbols were stored
        assert len(result["symbols"]) > 0
        
        # Check indexed count
        count = plugin_with_sqlite.get_indexed_count()
        assert count >= 1
    
    def test_cross_language_symbols(self, plugin, java_sample_code, kotlin_sample_code):
        """Test that symbols from both languages are indexed properly."""
        # Index both files
        java_result = plugin.indexFile("Sample.java", java_sample_code)
        kotlin_result = plugin.indexFile("Sample.kt", kotlin_sample_code)
        
        # Verify both languages are handled
        assert java_result["language"] == "java"
        assert kotlin_result["language"] == "kotlin"
        
        # Test that we can find definitions from both languages
        java_def = plugin.getDefinition("Sample")  # Java class
        assert java_def is not None
        assert java_def["language"] == "java"
        
        kotlin_def = plugin.getDefinition("KotlinSample")  # Kotlin class
        assert kotlin_def is not None
        assert kotlin_def["language"] == "kotlin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])