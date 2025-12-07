"""
Real-World Advanced Indexing Testing for Dormant Features Validation

Tests advanced indexing options and capabilities with real codebases.
Validates parallel processing, embedding generation, and optimization features.
"""

import asyncio
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

import pytest


@pytest.mark.advanced_indexing
class TestAdvancedIndexing:
    """Test advanced indexing options with real codebases."""

    @pytest.fixture
    def setup_advanced_indexer(self):
        """Setup advanced indexer with test configuration."""
        try:
            from mcp_server.indexer.index_engine import IndexEngine, IndexOptions
            from mcp_server.plugin_system import PluginManager
            from mcp_server.storage.sqlite_store import SQLiteStore
        except ImportError:
            pytest.skip("Advanced indexing components not available")

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
            store = SQLiteStore(db_file.name)
            plugin_manager = PluginManager(sqlite_store=store)

            # Load plugins
            load_result = plugin_manager.load_plugins_safe()
            if not load_result.success:
                pytest.skip(f"Failed to load plugins: {load_result.error.message}")

            engine = IndexEngine(plugin_manager, store)

            yield {"engine": engine, "store": store, "plugin_manager": plugin_manager}

            # Cleanup
            try:
                Path(db_file.name).unlink()
            except:
                pass

    def test_parallel_indexing_performance(self, setup_advanced_indexer, benchmark):
        """Test parallel indexing with different worker counts."""
        indexer_components = setup_advanced_indexer
        engine = indexer_components["engine"]

        # Create test files with substantial content
        test_files = []
        test_code_samples = [
            '''
def calculate_fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number recursively."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def fibonacci_iterative(n: int) -> int:
    """Calculate nth Fibonacci number iteratively."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

class FibonacciCalculator:
    """Calculator for Fibonacci sequences."""
    
    def __init__(self, cache_size: int = 100):
        self.cache = {}
        self.cache_size = cache_size
    
    def calculate(self, n: int) -> int:
        """Calculate with caching."""
        if n in self.cache:
            return self.cache[n]
        
        result = self._calculate_uncached(n)
        if len(self.cache) < self.cache_size:
            self.cache[n] = result
        return result
    
    def _calculate_uncached(self, n: int) -> int:
        """Internal calculation method."""
        return fibonacci_iterative(n)
''',
            '''
import json
import requests
from typing import Dict, Any, Optional

class APIClient:
    """HTTP API client with authentication and error handling."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to API endpoint."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.get(url, params=params)
        return self._handle_response(response)
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to API endpoint."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.post(url, json=data)
        return self._handle_response(response)
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and errors."""
        if response.status_code >= 400:
            raise APIError(f"API request failed: {response.status_code}")
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"raw_response": response.text}

class APIError(Exception):
    """Custom exception for API errors."""
    pass
''',
            '''
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class User:
    """User data model."""
    id: int
    username: str
    email: str
    created_at: datetime
    is_active: bool = True
    roles: List[str] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = ['user']
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles
    
    def add_role(self, role: str) -> None:
        """Add role to user."""
        if role not in self.roles:
            self.roles.append(role)
    
    def remove_role(self, role: str) -> None:
        """Remove role from user."""
        if role in self.roles:
            self.roles.remove(role)

class UserManager:
    """Manage user operations and database interactions."""
    
    def __init__(self, database_connection):
        self.db = database_connection
        self.users_cache = {}
    
    def create_user(self, username: str, email: str) -> User:
        """Create new user in database."""
        user_data = {
            'username': username,
            'email': email,
            'created_at': datetime.now(),
            'is_active': True
        }
        
        user_id = self.db.insert('users', user_data)
        user = User(id=user_id, **user_data)
        self.users_cache[user_id] = user
        return user
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        if user_id in self.users_cache:
            return self.users_cache[user_id]
        
        user_data = self.db.get('users', user_id)
        if user_data:
            user = User(**user_data)
            self.users_cache[user_id] = user
            return user
        
        return None
''',
        ]

        # Create temporary files
        for i, code in enumerate(test_code_samples):
            with tempfile.NamedTemporaryFile(suffix=f"_test_{i}.py", mode="w", delete=False) as f:
                f.write(code)
                f.flush()
                test_files.append(Path(f.name))

        try:

            def test_indexing_workers(max_workers):
                """Test indexing with specific worker count."""
                options = IndexOptions(
                    max_workers=max_workers,
                    batch_size=5,
                    force_reindex=True,
                    generate_embeddings=False,  # Disabled for speed
                )

                start_time = time.time()

                # Index files using asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:

                    async def index_files():
                        tasks = []
                        for file_path in test_files:
                            tasks.append(engine.index_file(str(file_path), options))

                        return await asyncio.gather(*tasks, return_exceptions=True)

                    results = loop.run_until_complete(index_files())
                    duration = time.time() - start_time

                    successful = sum(
                        1
                        for r in results
                        if not isinstance(r, Exception) and getattr(r, "success", False)
                    )
                    return successful, duration

                finally:
                    loop.close()

            # Test different worker configurations
            worker_configs = [1, 2, 4]
            performance_results = {}

            for workers in worker_configs:
                successful, duration = test_indexing_workers(workers)
                throughput = successful / duration if duration > 0 else 0

                performance_results[workers] = {
                    "successful": successful,
                    "duration": duration,
                    "throughput": throughput,
                }

                print(
                    f"{workers} workers: {successful} files in {duration:.2f}s ({throughput:.1f} files/s)"
                )

            # Validate scaling benefits
            single_thread_throughput = performance_results[1]["throughput"]
            multi_thread_throughput = max(
                performance_results[w]["throughput"] for w in worker_configs if w > 1
            )

            if single_thread_throughput > 0:
                speedup = multi_thread_throughput / single_thread_throughput
                assert speedup >= 1.2, f"Multi-threading should provide speedup: {speedup:.2f}x"
                print(f"Best speedup: {speedup:.2f}x with parallel processing")

            # Verify all files were processed successfully
            best_result = max(performance_results.values(), key=lambda x: x["successful"])
            assert (
                best_result["successful"] >= len(test_files) - 1
            ), "Should successfully index most files"

        finally:
            # Cleanup test files
            for file_path in test_files:
                try:
                    file_path.unlink()
                except:
                    pass

    def test_embedding_generation_integration(self, setup_advanced_indexer):
        """Test embedding generation during indexing."""
        if not os.getenv("SEMANTIC_SEARCH_ENABLED", "false").lower() == "true":
            pytest.skip("Semantic search not enabled")

        try:
            from mcp_server.utils.semantic_indexer import SemanticIndexer
        except ImportError:
            pytest.skip("Semantic indexer not available")

        indexer_components = setup_advanced_indexer
        engine = indexer_components["engine"]

        # Setup semantic indexer
        semantic_indexer = SemanticIndexer(collection="test-embedding", qdrant_path=":memory:")

        # Test code with rich semantic content
        test_code = '''
def authenticate_user_with_password(username: str, password: str) -> bool:
    """
    Authenticate a user using their username and password.
    
    This function validates user credentials against the database
    and returns True if authentication is successful.
    """
    hashed_password = hash_password(password)
    user_record = database.get_user_by_username(username)
    
    if user_record and user_record.password_hash == hashed_password:
        log_successful_login(username)
        return True
    
    log_failed_login_attempt(username)
    return False

class SessionManager:
    """
    Manages user sessions and authentication tokens.
    
    Provides functionality for creating, validating, and invalidating
    user sessions in a web application context.
    """
    
    def __init__(self, token_expiry_minutes: int = 60):
        self.token_expiry = token_expiry_minutes
        self.active_sessions = {}
    
    def create_session_token(self, user_id: int) -> str:
        """
        Create a new session token for authenticated user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Secure session token string
        """
        token = generate_secure_token()
        expiry_time = datetime.now() + timedelta(minutes=self.token_expiry)
        
        self.active_sessions[token] = {
            'user_id': user_id,
            'expires_at': expiry_time,
            'created_at': datetime.now()
        }
        
        return token
    
    def validate_session_token(self, token: str) -> Optional[int]:
        """
        Validate session token and return user ID if valid.
        
        Args:
            token: Session token to validate
            
        Returns:
            User ID if token is valid, None otherwise
        """
        if token not in self.active_sessions:
            return None
        
        session = self.active_sessions[token]
        if datetime.now() > session['expires_at']:
            del self.active_sessions[token]
            return None
        
        return session['user_id']
'''

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(test_code)
            f.flush()
            temp_path = Path(f.name)

            try:
                # Index with embedding generation enabled
                options = IndexOptions(generate_embeddings=True, semantic_indexer=semantic_indexer)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    result = loop.run_until_complete(engine.index_file(str(temp_path), options))

                    assert (
                        result.success
                    ), f"Indexing with embeddings should succeed: {result.error}"
                    assert (
                        result.symbols_count >= 3
                    ), f"Should extract symbols: {result.symbols_count}"

                    # Test semantic search on indexed content
                    semantic_results = list(
                        semantic_indexer.query("user authentication function", limit=3)
                    )
                    assert len(semantic_results) > 0, "Should find semantic matches"

                    # Test specific semantic queries
                    session_results = list(
                        semantic_indexer.query("session token management", limit=3)
                    )
                    assert len(session_results) > 0, "Should find session-related matches"

                    print(f"Embedded indexing: {result.symbols_count} symbols")
                    print(
                        f"Semantic matches: {len(semantic_results)} auth, {len(session_results)} session"
                    )

                finally:
                    loop.close()

            finally:
                temp_path.unlink()

    def test_batch_processing_optimization(self, setup_advanced_indexer, benchmark):
        """Test batch processing performance with different batch sizes."""
        indexer_components = setup_advanced_indexer
        engine = indexer_components["engine"]

        # Create multiple small files for batch testing
        test_files = []
        for i in range(20):
            code = f'''
def function_{i}(param: int) -> int:
    """Function number {i}."""
    return param * {i}

class Class{i}:
    """Class number {i}."""
    def method_{i}(self):
        return {i}

CONSTANT_{i} = {i}
'''
            with tempfile.NamedTemporaryFile(suffix=f"_batch_{i}.py", mode="w", delete=False) as f:
                f.write(code)
                f.flush()
                test_files.append(Path(f.name))

        try:

            def test_batch_size(batch_size):
                """Test indexing with specific batch size."""
                options = IndexOptions(
                    batch_size=batch_size,
                    max_workers=2,
                    force_reindex=True,
                    generate_embeddings=False,
                )

                start_time = time.time()

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:

                    async def batch_index():
                        results = []
                        for i in range(0, len(test_files), batch_size):
                            batch = test_files[i : i + batch_size]
                            batch_tasks = [engine.index_file(str(f), options) for f in batch]
                            batch_results = await asyncio.gather(
                                *batch_tasks, return_exceptions=True
                            )
                            results.extend(batch_results)
                        return results

                    results = loop.run_until_complete(batch_index())
                    duration = time.time() - start_time

                    successful = sum(
                        1
                        for r in results
                        if not isinstance(r, Exception) and getattr(r, "success", False)
                    )
                    return successful, duration

                finally:
                    loop.close()

            # Test different batch sizes
            batch_sizes = [1, 5, 10, 20]
            batch_results = {}

            for batch_size in batch_sizes:
                successful, duration = test_batch_size(batch_size)
                throughput = successful / duration if duration > 0 else 0

                batch_results[batch_size] = {
                    "successful": successful,
                    "duration": duration,
                    "throughput": throughput,
                }

                print(
                    f"Batch size {batch_size}: {successful} files in {duration:.2f}s ({throughput:.1f} files/s)"
                )

            # Find optimal batch size (highest throughput)
            optimal_batch = max(batch_results.items(), key=lambda x: x[1]["throughput"])
            optimal_size, optimal_stats = optimal_batch

            print(f"Optimal batch size: {optimal_size} ({optimal_stats['throughput']:.1f} files/s)")

            # Verify batch processing improves over single-file processing
            single_throughput = batch_results[1]["throughput"]
            if single_throughput > 0:
                best_throughput = optimal_stats["throughput"]
                improvement = best_throughput / single_throughput
                assert (
                    improvement >= 1.1
                ), f"Batch processing should improve performance: {improvement:.2f}x"

        finally:
            # Cleanup
            for file_path in test_files:
                try:
                    file_path.unlink()
                except:
                    pass

    def test_indexing_options_configuration(self, setup_advanced_indexer):
        """Test various indexing option configurations."""
        indexer_components = setup_advanced_indexer
        engine = indexer_components["engine"]

        # Test code with various symbol types
        test_code = '''
"""Module docstring for testing."""

import os
import sys
from typing import Dict, List, Optional

# Global constant
MAX_RETRIES = 3

def utility_function(param: str) -> bool:
    """Utility function for testing."""
    return len(param) > 0

class TestClass:
    """Test class with various members."""
    
    class_variable = "test"
    
    def __init__(self, name: str):
        self.name = name
        self._private_var = 0
    
    @property
    def display_name(self) -> str:
        """Property for display name."""
        return f"Display: {self.name}"
    
    @staticmethod
    def static_method() -> int:
        """Static method."""
        return 42
    
    @classmethod
    def create_default(cls):
        """Class method."""
        return cls("default")

def async_function() -> None:
    """Async function for testing."""
    pass

# Decorator function
def decorator_function(func):
    """Decorator for testing."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
'''

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(test_code)
            f.flush()
            temp_path = Path(f.name)

            try:
                # Test different indexing configurations
                test_configurations = [
                    {
                        "name": "basic",
                        "options": IndexOptions(
                            force_reindex=True,
                            extract_imports=True,
                            extract_docstrings=True,
                        ),
                    },
                    {
                        "name": "comprehensive",
                        "options": IndexOptions(
                            force_reindex=True,
                            extract_imports=True,
                            extract_docstrings=True,
                            extract_decorators=True,
                            extract_type_hints=True,
                        ),
                    },
                    {
                        "name": "minimal",
                        "options": IndexOptions(
                            force_reindex=True,
                            extract_imports=False,
                            extract_docstrings=False,
                        ),
                    },
                ]

                results = {}

                for config in test_configurations:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    try:
                        result = loop.run_until_complete(
                            engine.index_file(str(temp_path), config["options"])
                        )

                        results[config["name"]] = {
                            "success": result.success,
                            "symbols_count": result.symbols_count,
                            "error": result.error if not result.success else None,
                        }

                    finally:
                        loop.close()

                # Verify all configurations work
                for config_name, result in results.items():
                    assert result["success"], f"Configuration '{config_name}' should succeed"
                    assert (
                        result["symbols_count"] > 0
                    ), f"Configuration '{config_name}' should extract symbols"

                # Comprehensive should extract more information than minimal
                comprehensive_count = results["comprehensive"]["symbols_count"]
                minimal_count = results["minimal"]["symbols_count"]

                print(
                    f"Symbol extraction: minimal={minimal_count}, comprehensive={comprehensive_count}"
                )

                # Both should find core symbols, comprehensive may find more
                assert (
                    comprehensive_count >= minimal_count
                ), "Comprehensive indexing should extract at least as many symbols as minimal"

            finally:
                temp_path.unlink()

    def test_indexing_error_handling_and_recovery(self, setup_advanced_indexer):
        """Test error handling during indexing operations."""
        indexer_components = setup_advanced_indexer
        engine = indexer_components["engine"]

        # Test files with various issues
        test_scenarios = [
            {
                "name": "valid_file",
                "code": "def valid_function(): return True",
                "should_succeed": True,
            },
            {
                "name": "syntax_error",
                "code": "def invalid_function( invalid syntax here",
                "should_succeed": False,
            },
            {
                "name": "empty_file",
                "code": "",
                "should_succeed": True,  # Empty files should be handled gracefully
            },
            {
                "name": "only_comments",
                "code": "# This file only contains comments\n# No actual code here",
                "should_succeed": True,
            },
            {
                "name": "encoding_issues",
                "code": "# -*- coding: utf-8 -*-\ndef unicode_test():\n    return 'test with unicode: ñ'",
                "should_succeed": True,
            },
        ]

        results = {}
        temp_files = []

        try:
            for scenario in test_scenarios:
                with tempfile.NamedTemporaryFile(
                    suffix=f"_{scenario['name']}.py",
                    mode="w",
                    delete=False,
                    encoding="utf-8",
                ) as f:
                    f.write(scenario["code"])
                    f.flush()
                    temp_path = Path(f.name)
                    temp_files.append(temp_path)

                    # Index the file
                    options = IndexOptions(force_reindex=True)

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    try:
                        result = loop.run_until_complete(engine.index_file(str(temp_path), options))

                        results[scenario["name"]] = {
                            "success": result.success,
                            "symbols_count": result.symbols_count,
                            "error": result.error,
                            "expected_success": scenario["should_succeed"],
                        }

                    finally:
                        loop.close()

            # Validate error handling
            for scenario_name, result in results.items():
                expected_success = result["expected_success"]
                actual_success = result["success"]

                if expected_success:
                    assert (
                        actual_success
                    ), f"Scenario '{scenario_name}' should succeed but failed: {result['error']}"
                else:
                    # For scenarios that should fail, we expect graceful handling
                    # (either success with 0 symbols or controlled failure)
                    if not actual_success:
                        assert (
                            result["error"] is not None
                        ), f"Failed scenario '{scenario_name}' should have error message"
                        print(f"Expected failure for '{scenario_name}': {result['error']}")

                print(
                    f"Scenario '{scenario_name}': success={actual_success}, symbols={result['symbols_count']}"
                )

            # Verify at least the valid scenarios worked
            valid_results = [r for r in results.values() if r["expected_success"]]
            successful_valid = [r for r in valid_results if r["success"]]

            assert (
                len(successful_valid) >= len(valid_results) - 1
            ), "Most valid scenarios should succeed"

        finally:
            # Cleanup
            for temp_path in temp_files:
                try:
                    temp_path.unlink()
                except:
                    pass

    def test_memory_usage_during_indexing(self, setup_advanced_indexer):
        """Test memory usage patterns during indexing operations."""
        indexer_components = setup_advanced_indexer
        engine = indexer_components["engine"]

        try:
            import psutil

            process = psutil.Process()
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        # Create larger files to test memory usage
        large_code_template = '''
"""Large file for memory testing - File {file_num}."""

import os
import sys
import json
import datetime
from typing import Dict, List, Optional, Union, Any

# Constants
DEFAULT_CONFIG = {{
    "setting_{i}": "value_{i}" for i in range(50)
}}

{classes}

{functions}

# Global variables
GLOBAL_REGISTRY = {{}}
for i in range(100):
    GLOBAL_REGISTRY[f"item_{{i}}"] = f"data_{{i}}"
'''

        class_template = '''
class DataProcessor{class_num}:
    """Data processor class {class_num}."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache = {{}}
        self.statistics = {{"processed": 0, "errors": 0}}
    
    def process_data(self, data: List[Dict]) -> List[Dict]:
        """Process list of data items."""
        results = []
        for item in data:
            try:
                processed = self._process_item(item)
                results.append(processed)
                self.statistics["processed"] += 1
            except Exception as e:
                self.statistics["errors"] += 1
                continue
        return results
    
    def _process_item(self, item: Dict) -> Dict:
        """Process single data item."""
        # Simulate complex processing
        result = item.copy()
        result["processed_at"] = datetime.datetime.now().isoformat()
        result["processor_id"] = {class_num}
        return result
    
    def get_statistics(self) -> Dict[str, int]:
        """Get processing statistics."""
        return self.statistics.copy()
'''

        function_template = '''
def utility_function_{func_num}(param1: str, param2: int = 0) -> Optional[str]:
    """Utility function {func_num}."""
    if not param1 or param2 < 0:
        return None
    
    # Simulate some processing
    result = f"{{param1}}_processed_{{param2}}_by_func_{func_num}"
    return result

def async_operation_{func_num}(data: Dict[str, Any]) -> Dict[str, Any]:
    """Async operation {func_num}."""
    import asyncio
    
    async def process():
        # Simulate async work
        await asyncio.sleep(0.01)
        return {{"result": "processed", "function": {func_num}}}
    
    return asyncio.run(process())
'''

        test_files = []
        memory_samples = []

        try:
            # Record initial memory
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_samples.append(("initial", initial_memory))

            # Create and index multiple large files
            for file_num in range(5):
                # Generate classes and functions
                classes = "\n".join(
                    class_template.format(class_num=i)
                    for i in range(file_num * 3, (file_num + 1) * 3)
                )
                functions = "\n".join(
                    function_template.format(func_num=i)
                    for i in range(file_num * 5, (file_num + 1) * 5)
                )

                large_code = large_code_template.format(
                    file_num=file_num, classes=classes, functions=functions
                )

                with tempfile.NamedTemporaryFile(
                    suffix=f"_large_{file_num}.py", mode="w", delete=False
                ) as f:
                    f.write(large_code)
                    f.flush()
                    temp_path = Path(f.name)
                    test_files.append(temp_path)

                    # Index the file
                    options = IndexOptions(force_reindex=True)

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    try:
                        result = loop.run_until_complete(engine.index_file(str(temp_path), options))
                        assert result.success, f"Should index large file {file_num}"

                        # Record memory after indexing
                        current_memory = process.memory_info().rss / 1024 / 1024
                        memory_samples.append((f"after_file_{file_num}", current_memory))

                    finally:
                        loop.close()

            # Analyze memory usage
            final_memory = memory_samples[-1][1]
            memory_increase = final_memory - initial_memory

            print(
                f"Memory usage: {initial_memory:.1f} MB -> {final_memory:.1f} MB (increase: {memory_increase:.1f} MB)"
            )

            # Memory usage should be reasonable for the amount of code processed
            assert (
                memory_increase < 200
            ), f"Memory increase {memory_increase:.1f} MB should be < 200 MB"

            # Check for memory leaks (memory should not grow linearly with each file)
            if len(memory_samples) >= 4:
                first_file_memory = memory_samples[1][1]
                last_file_memory = memory_samples[-1][1]
                per_file_growth = (last_file_memory - first_file_memory) / (len(memory_samples) - 2)

                assert (
                    per_file_growth < 50
                ), f"Per-file memory growth {per_file_growth:.1f} MB should be < 50 MB"
                print(f"Average memory growth per file: {per_file_growth:.1f} MB")

        finally:
            # Cleanup
            for temp_path in test_files:
                try:
                    temp_path.unlink()
                except:
                    pass


@pytest.mark.advanced_indexing
@pytest.mark.slow
class TestAdvancedIndexingIntegration:
    """Test advanced indexing integration with real repositories."""

    def test_real_repository_advanced_indexing(self):
        """Test advanced indexing on real repository if available."""
        # Try to use requests repository if available
        repo_path = Path("test_workspace/real_repos/requests")
        if not repo_path.exists():
            pytest.skip("Requests repository not available for advanced indexing testing")

        try:
            from mcp_server.indexer.index_engine import IndexEngine, IndexOptions
            from mcp_server.plugin_system import PluginManager
            from mcp_server.storage.sqlite_store import SQLiteStore
        except ImportError:
            pytest.skip("Advanced indexing components not available")

        # Setup indexing system
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
            store = SQLiteStore(db_file.name)
            plugin_manager = PluginManager(sqlite_store=store)

            load_result = plugin_manager.load_plugins_safe()
            if not load_result.success:
                pytest.skip(f"Failed to load plugins: {load_result.error.message}")

            engine = IndexEngine(plugin_manager, store)

            try:
                # Get Python files from requests repository
                python_files = list(repo_path.rglob("*.py"))[:20]  # Limit for testing

                if len(python_files) < 5:
                    pytest.skip("Not enough Python files found in repository")

                # Index with advanced options
                options = IndexOptions(
                    max_workers=4,
                    batch_size=5,
                    force_reindex=True,
                    extract_imports=True,
                    extract_docstrings=True,
                    generate_embeddings=False,  # Disabled unless semantic search is enabled
                )

                start_time = time.time()
                indexed_count = 0
                total_symbols = 0
                errors = []

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Index files in batches
                    for i in range(0, len(python_files), options.batch_size):
                        batch = python_files[i : i + options.batch_size]

                        tasks = [engine.index_file(str(f), options) for f in batch]
                        results = await asyncio.gather(*tasks, return_exceptions=True)

                        for j, result in enumerate(results):
                            if isinstance(result, Exception):
                                errors.append(f"{batch[j]}: {result}")
                            elif result.success:
                                indexed_count += 1
                                total_symbols += result.symbols_count
                            else:
                                errors.append(f"{batch[j]}: {result.error}")

                finally:
                    loop.close()

                duration = time.time() - start_time

                # Validate results
                assert (
                    indexed_count >= len(python_files) * 0.8
                ), f"Should index most files: {indexed_count}/{len(python_files)}"

                assert (
                    total_symbols >= indexed_count * 2
                ), f"Should extract multiple symbols per file: {total_symbols} symbols from {indexed_count} files"

                assert (
                    len(errors) < len(python_files) * 0.2
                ), f"Error rate should be low: {len(errors)} errors out of {len(python_files)} files"

                print(
                    f"Real repository indexing: {indexed_count} files, {total_symbols} symbols in {duration:.2f}s"
                )
                print(
                    f"Performance: {indexed_count/duration:.1f} files/s, {total_symbols/duration:.1f} symbols/s"
                )

                if errors:
                    print(f"Errors encountered ({len(errors)}):")
                    for error in errors[:5]:  # Show first 5 errors
                        print(f"  {error}")

            finally:
                # Cleanup
                try:
                    Path(db_file.name).unlink()
                except:
                    pass
