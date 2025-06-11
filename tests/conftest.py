"""
Pytest configuration and fixtures for Code-Index-MCP tests.

This module provides reusable fixtures for testing all components of the
MCP server including API endpoints, database operations, file system
operations, and plugin functionality.
"""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any, List
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Import our modules
from mcp_server.gateway import app
from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.watcher import FileWatcher
from mcp_server.plugin_base import IPlugin, SymbolDef, SearchResult
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin


# Performance tracking
@pytest.fixture(scope="session")
def benchmark_results():
    """Fixture to collect benchmark results across all tests."""
    results = {}
    yield results
    
    # Print summary at the end
    if results:
        print("\n\n=== Performance Benchmark Summary ===")
        for test_name, timings in results.items():
            avg_time = sum(timings) / len(timings)
            print(f"{test_name}: avg={avg_time:.3f}s, min={min(timings):.3f}s, max={max(timings):.3f}s")


# Database fixtures
@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database file path."""
    return tmp_path / "test_code_index.db"


@pytest.fixture
def sqlite_store(temp_db_path: Path) -> SQLiteStore:
    """Create a SQLiteStore instance with a temporary database."""
    store = SQLiteStore(str(temp_db_path))
    yield store
    # Cleanup is automatic when tmp_path is cleaned up


@pytest.fixture
def populated_sqlite_store(sqlite_store: SQLiteStore) -> SQLiteStore:
    """Create a SQLiteStore with sample data."""
    # Create a repository
    repo_id = sqlite_store.create_repository("/test/repo", "test-repo", {"type": "git"})
    
    # Create some files
    file1_id = sqlite_store.store_file(
        repo_id, "/test/repo/main.py", "main.py",
        language="python", size=1024, hash="abc123"
    )
    file2_id = sqlite_store.store_file(
        repo_id, "/test/repo/utils.py", "utils.py",
        language="python", size=512, hash="def456"
    )
    
    # Create some symbols
    sqlite_store.store_symbol(
        file1_id, "main", "function",
        line_start=1, line_end=10,
        signature="def main() -> None",
        documentation="Main entry point"
    )
    sqlite_store.store_symbol(
        file1_id, "MyClass", "class",
        line_start=15, line_end=50,
        signature="class MyClass",
        documentation="A sample class"
    )
    sqlite_store.store_symbol(
        file2_id, "helper_function", "function",
        line_start=5, line_end=15,
        signature="def helper_function(x: int) -> str"
    )
    
    return sqlite_store


# File system fixtures
@pytest.fixture
def temp_code_directory(tmp_path: Path) -> Path:
    """Create a temporary directory with sample code files."""
    code_dir = tmp_path / "test_code"
    code_dir.mkdir()
    
    # Create Python files
    (code_dir / "sample.py").write_text("""
def hello_world():
    '''Say hello to the world.'''
    print("Hello, World!")

class Calculator:
    '''A simple calculator class.'''
    
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        return a - b

if __name__ == "__main__":
    hello_world()
""")
    
    # Create JavaScript file
    (code_dir / "app.js").write_text("""
function greet(name) {
    return `Hello, ${name}!`;
}

class UserManager {
    constructor() {
        this.users = [];
    }
    
    addUser(user) {
        this.users.push(user);
    }
}

module.exports = { greet, UserManager };
""")
    
    # Create nested directory structure
    (code_dir / "src").mkdir()
    (code_dir / "src" / "utils.py").write_text("""
import os
from typing import List

def process_files(paths: List[str]) -> None:
    for path in paths:
        if os.path.exists(path):
            print(f"Processing {path}")

class FileHandler:
    def __init__(self, base_path: str):
        self.base_path = base_path
""")
    
    return code_dir


@pytest.fixture
def mock_file_system(monkeypatch):
    """Mock file system operations for isolated testing."""
    mock_fs = {}
    
    def mock_exists(path):
        return str(path) in mock_fs
    
    def mock_read_text(path):
        if str(path) not in mock_fs:
            raise FileNotFoundError(f"File not found: {path}")
        return mock_fs[str(path)]
    
    def mock_write_text(path, content):
        mock_fs[str(path)] = content
    
    # Patch Path methods
    monkeypatch.setattr(Path, "exists", mock_exists)
    monkeypatch.setattr(Path, "read_text", mock_read_text)
    monkeypatch.setattr(Path, "write_text", mock_write_text)
    
    return mock_fs


# Plugin fixtures
@pytest.fixture
def mock_plugin() -> Mock:
    """Create a mock plugin for testing dispatcher."""
    plugin = Mock(spec=IPlugin)
    plugin.lang = "mock"
    plugin.supports.return_value = True
    plugin.indexFile.return_value = {
        "symbols": [
            {
                "name": "test_function",
                "kind": "function",
                "line": 1,
                "signature": "def test_function()"
            }
        ]
    }
    plugin.getDefinition.return_value = SymbolDef(
        name="test_function",
        kind="function",
        path="/test/file.py",
        line=1,
        signature="def test_function()"
    )
    plugin.search.return_value = [
        SearchResult(
            name="test_function",
            kind="function",
            path="/test/file.py",
            score=1.0
        )
    ]
    return plugin


@pytest.fixture
def python_plugin(sqlite_store: SQLiteStore) -> PythonPlugin:
    """Create a Python plugin instance with SQLite store."""
    return PythonPlugin(sqlite_store=sqlite_store)


@pytest.fixture
def dispatcher_with_plugins(python_plugin: PythonPlugin) -> Dispatcher:
    """Create a dispatcher with real plugins."""
    return Dispatcher([python_plugin])


@pytest.fixture
def dispatcher_with_mock(mock_plugin: Mock) -> Dispatcher:
    """Create a dispatcher with mock plugin."""
    return Dispatcher([mock_plugin])


# File watcher fixtures
@pytest.fixture
def file_watcher(temp_code_directory: Path, dispatcher_with_plugins: Dispatcher) -> FileWatcher:
    """Create a file watcher instance."""
    watcher = FileWatcher(temp_code_directory, dispatcher_with_plugins)
    yield watcher
    # Ensure watcher is stopped
    try:
        watcher.stop()
    except:
        pass


# API client fixtures
@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_client_with_dispatcher(
    test_client: TestClient,
    dispatcher_with_plugins: Dispatcher,
    sqlite_store: SQLiteStore,
    monkeypatch
) -> TestClient:
    """Create a test client with initialized dispatcher."""
    # Patch the global variables in gateway module
    import mcp_server.gateway as gateway
    monkeypatch.setattr(gateway, "dispatcher", dispatcher_with_plugins)
    monkeypatch.setattr(gateway, "sqlite_store", sqlite_store)
    
    # Also set in app.state
    test_client.app.state.dispatcher = dispatcher_with_plugins
    test_client.app.state.sqlite_store = sqlite_store
    
    return test_client


# Async fixtures
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Sample data fixtures
@pytest.fixture
def sample_symbol_def() -> SymbolDef:
    """Sample SymbolDef for testing."""
    return SymbolDef(
        name="sample_function",
        kind="function",
        path="/test/sample.py",
        line=10,
        signature="def sample_function(x: int) -> str",
        documentation="A sample function for testing"
    )


@pytest.fixture
def sample_search_results() -> List[SearchResult]:
    """Sample search results for testing."""
    return [
        SearchResult(
            name="function_one",
            kind="function",
            path="/test/file1.py",
            score=0.95
        ),
        SearchResult(
            name="function_two",
            kind="function",
            path="/test/file2.py",
            score=0.85
        ),
        SearchResult(
            name="ClassOne",
            kind="class",
            path="/test/file3.py",
            score=0.75
        )
    ]


# Environment fixtures
@pytest.fixture(autouse=True)
def test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("MCP_TEST_MODE", "1")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_logs(tmp_path):
    """Ensure logs are written to temp directory during tests."""
    log_file = tmp_path / "test.log"
    os.environ["MCP_LOG_FILE"] = str(log_file)
    yield
    # Cleanup happens automatically with tmp_path


# Helper utilities
class TestDataBuilder:
    """Helper class to build test data."""
    
    @staticmethod
    def create_python_file(path: Path, content: str = None) -> Path:
        """Create a Python file with optional content."""
        if content is None:
            content = '''
def test_function():
    """Test function."""
    pass

class TestClass:
    """Test class."""
    def method(self):
        pass
'''
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path
    
    @staticmethod
    def create_project_structure(base_path: Path) -> Dict[str, Path]:
        """Create a sample project structure."""
        files = {}
        
        # Create main module
        files["main"] = TestDataBuilder.create_python_file(
            base_path / "main.py",
            '''
import sys
from src.utils import helper

def main():
    """Main entry point."""
    helper()
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
        )
        
        # Create src directory
        src_dir = base_path / "src"
        src_dir.mkdir()
        
        files["utils"] = TestDataBuilder.create_python_file(
            src_dir / "utils.py",
            '''
def helper():
    """Helper function."""
    print("Helper called")

class Config:
    """Configuration class."""
    def __init__(self):
        self.debug = True
'''
        )
        
        # Create tests
        test_dir = base_path / "tests"
        test_dir.mkdir()
        
        files["test_main"] = TestDataBuilder.create_python_file(
            test_dir / "test_main.py",
            '''
import pytest
from main import main

def test_main():
    """Test main function."""
    assert main() == 0
'''
        )
        
        return files


@pytest.fixture
def test_data_builder():
    """Provide test data builder to tests."""
    return TestDataBuilder


# Performance helpers
import time
from contextlib import contextmanager

@contextmanager
def measure_time(test_name: str, benchmark_results: dict):
    """Context manager to measure test execution time."""
    start = time.time()
    yield
    elapsed = time.time() - start
    
    if test_name not in benchmark_results:
        benchmark_results[test_name] = []
    benchmark_results[test_name].append(elapsed)