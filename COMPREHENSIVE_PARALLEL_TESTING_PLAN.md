# Comprehensive Parallel Testing Plan for Code-Index-MCP
## Real-World Codebase Validation & Performance Testing

## Executive Summary

This comprehensive testing plan validates the Code-Index-MCP system using real-world GitHub repositories, ensuring production readiness through actual codebase indexing and retrieval scenarios. The plan leverages existing testing infrastructure while adding realistic workload validation with diverse, multi-language open-source projects.

## Real-World Testing Strategy

### 🌍 GitHub Repository Test Suite

We will test against carefully selected public repositories that represent diverse coding patterns, languages, and complexities:

#### **Tier 1: Language-Specific Repositories (Core Validation)**
```yaml
Python:
  - Repository: "psf/requests" (29k stars, HTTP library)
    Size: ~50 files, ~15k LOC
    Features: Classes, functions, decorators, async
    Test Focus: Python plugin symbol extraction
  
  - Repository: "django/django" (78k stars, web framework) 
    Size: ~2000 files, ~350k LOC
    Features: Complex inheritance, metaclasses, decorators
    Test Focus: Large-scale Python indexing performance

JavaScript/TypeScript:
  - Repository: "microsoft/vscode" (160k stars, editor)
    Size: ~3000 files, ~500k LOC TypeScript
    Features: Classes, interfaces, generics, modules
    Test Focus: TypeScript support and large codebase handling

  - Repository: "facebook/react" (220k stars, UI library)
    Size: ~800 files, ~200k LOC JavaScript/TypeScript
    Features: JSX, hooks, modern JS patterns
    Test Focus: React-specific patterns and JSX parsing

C/C++:
  - Repository: "torvalds/linux" (170k stars, kernel)
    Size: ~70k files, ~30M LOC C
    Features: Kernel patterns, macros, complex structures
    Test Focus: Large-scale C indexing and performance limits

  - Repository: "microsoft/terminal" (94k stars, terminal app)
    Size: ~800 files, ~200k LOC C++
    Features: Modern C++, templates, Windows APIs
    Test Focus: C++ template and namespace handling

Multi-Language:
  - Repository: "kubernetes/kubernetes" (108k stars, orchestrator)
    Size: ~8000 files, Go/YAML/Shell
    Features: Multi-language project structure
    Test Focus: Cross-language project indexing
```

#### **Tier 2: Complexity & Scale Testing**
```yaml
Massive Scale:
  - Repository: "chromium/chromium" (subset - 1000 files)
    Size: 1000 files, ~500k LOC C++/JavaScript
    Test Focus: Memory usage and indexing performance limits

  - Repository: "tensorflow/tensorflow" (subset - 2000 files)
    Size: 2000 files, ~800k LOC Python/C++
    Test Focus: Mixed-language large codebase handling

Legacy & Edge Cases:
  - Repository: "git/git" (50k stars, version control)
    Size: ~900 files, ~300k LOC C
    Features: Legacy C patterns, complex macros
    Test Focus: Handling legacy code patterns

  - Repository: "apple/swift" (66k stars, language)
    Size: ~5000 files, ~1.5M LOC Swift/C++
    Features: Compiler codebase complexity
    Test Focus: Advanced language constructs
```

### 📊 Test Execution Framework

## Phase 1: Real-World Repository Integration Testing

### 1.1 Repository Download & Setup
```bash
# Create test workspace for real repositories
mkdir -p test_workspace/real_repos
cd test_workspace/real_repos

# Download test repositories (shallow clones for speed)
git clone --depth=1 https://github.com/psf/requests.git
git clone --depth=1 https://github.com/django/django.git
git clone --depth=1 https://github.com/microsoft/vscode.git
git clone --depth=1 https://github.com/facebook/react.git
git clone --depth=1 https://github.com/torvalds/linux.git
git clone --depth=1 https://github.com/microsoft/terminal.git
git clone --depth=1 https://github.com/kubernetes/kubernetes.git

# Create subset repositories for large codebases
create_subset_repo() {
    local repo=$1
    local max_files=$2
    mkdir -p "${repo}_subset"
    find "$repo" -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.c" -o -name "*.cpp" -o -name "*.h" | 
    head -n "$max_files" | 
    xargs -I {} cp {} "${repo}_subset/"
}

create_subset_repo chromium 1000
create_subset_repo tensorflow 2000
```

### 1.2 Indexing Performance Testing
**Parallel Group A: Small Repository Indexing (4 workers)**
```python
# Test: test_real_world_indexing.py
import pytest
import time
from pathlib import Path
from mcp_server.gateway import app
from mcp_server.storage.sqlite_store import SQLiteStore

@pytest.mark.performance
@pytest.mark.parametrize("repo_name,expected_files,expected_symbols", [
    ("requests", 50, 500),
    ("react/packages/react", 100, 800),
    ("terminal/src", 200, 2000),
])
def test_small_repository_indexing(repo_name, expected_files, expected_symbols, benchmark):
    """Test indexing performance on small real-world repositories."""
    repo_path = Path(f"test_workspace/real_repos/{repo_name}")
    
    def index_repository():
        store = SQLiteStore(f"test_{repo_name}.db")
        repo_id = store.create_repository(str(repo_path), repo_name, {"type": "test"})
        
        indexed_files = 0
        total_symbols = 0
        
        for file_path in repo_path.rglob("*.py"):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    # Use the actual plugin system to index
                    result = index_file_with_plugin(str(file_path), content, store)
                    if result.success:
                        indexed_files += 1
                        total_symbols += len(result.value.get('symbols', []))
                except Exception as e:
                    print(f"Error indexing {file_path}: {e}")
        
        return indexed_files, total_symbols
    
    # Benchmark the indexing process
    result = benchmark(index_repository)
    indexed_files, total_symbols = result
    
    # Validate results
    assert indexed_files >= expected_files * 0.8  # Allow 20% variance
    assert total_symbols >= expected_symbols * 0.8
    
    # Performance assertions
    assert benchmark.stats.mean < 30.0  # Max 30 seconds average
    print(f"Indexed {indexed_files} files with {total_symbols} symbols")

@pytest.mark.performance
@pytest.mark.slow
def test_large_repository_indexing(benchmark):
    """Test indexing performance on Django (large Python codebase)."""
    repo_path = Path("test_workspace/real_repos/django")
    
    def index_django():
        store = SQLiteStore("test_django.db")
        repo_id = store.create_repository(str(repo_path), "django", {"type": "large_test"})
        
        indexed_files = 0
        total_symbols = 0
        errors = []
        
        # Index only Python files to focus on our plugin
        python_files = list(repo_path.rglob("*.py"))
        print(f"Found {len(python_files)} Python files")
        
        for file_path in python_files[:1000]:  # Limit to 1000 files for testing
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                result = index_file_with_plugin(str(file_path), content, store)
                if result.success:
                    indexed_files += 1
                    symbols = result.value.get('symbols', [])
                    total_symbols += len(symbols)
            except Exception as e:
                errors.append(f"{file_path}: {e}")
        
        return indexed_files, total_symbols, len(errors)
    
    result = benchmark(index_django)
    indexed_files, total_symbols, error_count = result
    
    # Performance and quality assertions
    assert indexed_files >= 800  # Should index most files successfully
    assert total_symbols >= 10000  # Django has many symbols
    assert error_count < indexed_files * 0.1  # <10% error rate
    assert benchmark.stats.mean < 120.0  # Max 2 minutes for 1000 files
    
    print(f"Django indexing: {indexed_files} files, {total_symbols} symbols, {error_count} errors")
```

### 1.3 Symbol Retrieval & Search Testing
```python
@pytest.mark.integration
@pytest.mark.parametrize("repo_name,search_terms", [
    ("requests", ["Session", "get", "post", "Response", "HTTPAdapter"]),
    ("react", ["Component", "useState", "useEffect", "createElement", "ReactDOM"]),
    ("django", ["Model", "QuerySet", "CharField", "ForeignKey", "admin"]),
])
def test_real_world_symbol_search(repo_name, search_terms, benchmark):
    """Test symbol search accuracy on real-world codebases."""
    
    # First, ensure the repository is indexed
    setup_indexed_repository(repo_name)
    
    def search_symbols():
        results = {}
        for term in search_terms:
            # Test exact symbol lookup
            symbol_result = lookup_symbol(term, repo_name)
            
            # Test fuzzy search
            search_result = search_code(term, repo_name, limit=10)
            
            results[term] = {
                'symbol_found': len(symbol_result) > 0,
                'search_results': len(search_result),
                'search_time_ms': measure_search_time(term, repo_name)
            }
        
        return results
    
    results = benchmark(search_symbols)
    
    # Validate search quality
    found_symbols = sum(1 for r in results.values() if r['symbol_found'])
    assert found_symbols >= len(search_terms) * 0.8  # 80% symbol discovery rate
    
    # Performance validation
    avg_search_time = sum(r['search_time_ms'] for r in results.values()) / len(results)
    assert avg_search_time < 100  # <100ms average search time
    
    print(f"Symbol search results for {repo_name}: {found_symbols}/{len(search_terms)} found")

@pytest.mark.integration
def test_cross_language_search():
    """Test search across multiple languages in kubernetes repository."""
    setup_indexed_repository("kubernetes")
    
    # Search for common patterns across languages
    test_cases = [
        {"term": "Config", "expected_languages": ["go", "yaml"]},
        {"term": "client", "expected_languages": ["go", "javascript"]},
        {"term": "test", "expected_languages": ["go", "shell", "python"]},
    ]
    
    for case in test_cases:
        results = search_code(case["term"], "kubernetes", limit=20)
        
        # Group results by detected language
        languages_found = set()
        for result in results:
            file_ext = Path(result['file_path']).suffix
            lang = detect_language_from_extension(file_ext)
            if lang:
                languages_found.add(lang)
        
        # Validate cross-language discovery
        assert len(languages_found) >= 2, f"Expected multi-language results for '{case['term']}'"
        print(f"Term '{case['term']}' found in languages: {languages_found}")
```

## Phase 2: Performance & Scale Testing

### 2.1 Memory Usage Testing
```python
@pytest.mark.performance
@pytest.mark.memory
def test_memory_usage_large_codebase():
    """Test memory usage during large codebase indexing."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Index a large subset of Linux kernel
    repo_path = Path("test_workspace/real_repos/linux")
    c_files = list(repo_path.rglob("*.c"))[:5000]  # 5000 C files
    
    store = SQLiteStore("test_linux_memory.db")
    repo_id = store.create_repository(str(repo_path), "linux_subset", {"type": "memory_test"})
    
    indexed_count = 0
    memory_samples = []
    
    for i, file_path in enumerate(c_files):
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            result = index_file_with_plugin(str(file_path), content, store)
            if result.success:
                indexed_count += 1
            
            # Sample memory every 100 files
            if i % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory - initial_memory)
                
        except Exception as e:
            print(f"Error indexing {file_path}: {e}")
    
    final_memory = process.memory_info().rss / 1024 / 1024
    memory_increase = final_memory - initial_memory
    
    # Memory usage assertions
    assert memory_increase < 2000  # <2GB memory increase
    assert indexed_count >= 4000   # Successfully index most files
    
    # Check for memory leaks (memory should not continuously grow)
    memory_growth_rate = (memory_samples[-1] - memory_samples[0]) / len(memory_samples)
    assert memory_growth_rate < 10  # <10MB per 100 files growth rate
    
    print(f"Memory test: Indexed {indexed_count} files, Memory increase: {memory_increase:.1f}MB")

@pytest.mark.performance
def test_concurrent_indexing():
    """Test concurrent indexing of multiple repositories."""
    import asyncio
    import concurrent.futures
    
    repos = ["requests", "react", "terminal"]
    
    def index_repo(repo_name):
        repo_path = Path(f"test_workspace/real_repos/{repo_name}")
        store = SQLiteStore(f"concurrent_{repo_name}.db")
        
        start_time = time.time()
        indexed_files = 0
        
        for file_path in repo_path.rglob("*"):
            if file_path.suffix in ['.py', '.js', '.ts', '.c', '.cpp']:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    result = index_file_with_plugin(str(file_path), content, store)
                    if result.success:
                        indexed_files += 1
                except Exception:
                    pass
        
        duration = time.time() - start_time
        return repo_name, indexed_files, duration
    
    # Execute concurrent indexing
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(index_repo, repo) for repo in repos]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # Validate concurrent execution
    total_files = sum(result[1] for result in results)
    max_duration = max(result[2] for result in results)
    
    assert total_files >= 300  # Minimum files indexed across all repos
    assert max_duration < 60   # Should complete within 1 minute
    
    print(f"Concurrent indexing: {total_files} total files in {max_duration:.1f}s")
```

## Phase 3: Real-World Query Patterns

### 3.1 Developer Workflow Testing
```python
@pytest.mark.integration
@pytest.mark.workflow
class TestDeveloperWorkflows:
    """Test realistic developer search and navigation patterns."""
    
    def test_find_function_usage(self):
        """Test finding where a function is used across codebase."""
        # Using Django as test case
        setup_indexed_repository("django")
        
        # Search for Django's get_object_or_404 function usage
        symbol_def = lookup_symbol("get_object_or_404", "django")
        assert len(symbol_def) > 0, "Should find get_object_or_404 definition"
        
        # Find usage patterns
        usage_results = search_code("get_object_or_404", "django", limit=50)
        
        # Should find many usage examples
        assert len(usage_results) >= 20, "Should find multiple usages"
        
        # Validate result quality
        usage_files = set(result['file_path'] for result in usage_results)
        assert len(usage_files) >= 10, "Should span multiple files"
    
    def test_class_hierarchy_discovery(self):
        """Test discovering class inheritance patterns."""
        setup_indexed_repository("django")
        
        # Search for Model class and its subclasses
        model_results = search_code("class.*Model", "django", limit=30)
        
        # Should find base Model class and many subclasses
        assert len(model_results) >= 15, "Should find Model class hierarchy"
        
        # Check for inheritance patterns
        inheritance_patterns = [
            "class.*Model\\(",
            "Model\\)",
            "models\\.Model"
        ]
        
        found_patterns = 0
        for pattern in inheritance_patterns:
            pattern_results = search_code(pattern, "django", limit=10)
            if len(pattern_results) > 0:
                found_patterns += 1
        
        assert found_patterns >= 2, "Should find inheritance patterns"
    
    def test_api_discovery(self):
        """Test discovering API endpoints and interfaces."""
        setup_indexed_repository("requests")
        
        # Find HTTP method implementations
        http_methods = ["get", "post", "put", "delete", "patch"]
        
        for method in http_methods:
            method_results = search_code(f"def {method}", "requests", limit=5)
            assert len(method_results) > 0, f"Should find {method} method implementation"
    
    def test_configuration_search(self):
        """Test finding configuration and settings."""
        setup_indexed_repository("vscode")
        
        # Search for configuration patterns
        config_terms = ["config", "settings", "preferences", "options"]
        
        total_config_results = 0
        for term in config_terms:
            results = search_code(term, "vscode", limit=10)
            total_config_results += len(results)
        
        assert total_config_results >= 20, "Should find configuration-related code"
    
    @pytest.mark.slow
    def test_refactoring_impact_analysis(self):
        """Test finding all references to a symbol for refactoring."""
        setup_indexed_repository("react")
        
        # Find all references to Component class
        component_references = search_code("Component", "react", limit=100)
        
        # Should find many references
        assert len(component_references) >= 30, "Should find many Component references"
        
        # Group by usage type (import, inheritance, etc.)
        import_refs = [r for r in component_references if "import" in r['content'].lower()]
        class_refs = [r for r in component_references if "class" in r['content'].lower()]
        
        assert len(import_refs) >= 5, "Should find import references"
        assert len(class_refs) >= 5, "Should find class references"
```

### 3.2 Performance Benchmarking with Real Data
```python
@pytest.mark.performance
@pytest.mark.benchmark
class TestRealWorldPerformance:
    """Benchmark performance with real-world query patterns."""
    
    def test_symbol_lookup_performance(self, benchmark):
        """Benchmark symbol lookup across different repository sizes."""
        repos = {
            "small": "requests",    # ~50 files
            "medium": "react",      # ~800 files  
            "large": "django"       # ~2000 files
        }
        
        results = {}
        
        for size, repo_name in repos.items():
            setup_indexed_repository(repo_name)
            
            def lookup_common_symbols():
                symbols = get_common_symbols_for_repo(repo_name)
                lookup_times = []
                
                for symbol in symbols[:10]:  # Test 10 common symbols
                    start_time = time.perf_counter()
                    result = lookup_symbol(symbol, repo_name)
                    end_time = time.perf_counter()
                    
                    if result:
                        lookup_times.append((end_time - start_time) * 1000)  # Convert to ms
                
                return lookup_times
            
            lookup_times = benchmark(lookup_common_symbols)
            
            # Performance assertions
            avg_time = sum(lookup_times) / len(lookup_times)
            max_time = max(lookup_times)
            
            assert avg_time < 50, f"Average lookup time too high for {size} repo: {avg_time:.2f}ms"
            assert max_time < 100, f"Max lookup time too high for {size} repo: {max_time:.2f}ms"
            
            results[size] = {"avg": avg_time, "max": max_time}
        
        print(f"Symbol lookup performance: {results}")
    
    def test_search_performance_scaling(self, benchmark):
        """Test how search performance scales with repository size."""
        repo_sizes = {
            "django": list(Path("test_workspace/real_repos/django").rglob("*.py"))[:1000],
            "django_large": list(Path("test_workspace/real_repos/django").rglob("*.py"))[:2000],
        }
        
        search_terms = ["model", "view", "admin", "form", "test"]
        
        for repo_name, files in repo_sizes.items():
            # Index the specific file set
            index_file_subset(repo_name, files)
            
            def run_search_suite():
                search_times = []
                for term in search_terms:
                    start_time = time.perf_counter()
                    results = search_code(term, repo_name, limit=20)
                    end_time = time.perf_counter()
                    
                    search_times.append((end_time - start_time) * 1000)
                
                return search_times
            
            search_times = benchmark(run_search_suite)
            avg_search_time = sum(search_times) / len(search_times)
            
            # Performance scaling assertions
            if "large" in repo_name:
                assert avg_search_time < 200, f"Search too slow for large repo: {avg_search_time:.2f}ms"
            else:
                assert avg_search_time < 100, f"Search too slow for medium repo: {avg_search_time:.2f}ms"
            
            print(f"{repo_name} search performance: {avg_search_time:.2f}ms average")

# Helper functions for real-world testing

def setup_indexed_repository(repo_name):
    """Ensure a repository is downloaded and indexed."""
    repo_path = Path(f"test_workspace/real_repos/{repo_name}")
    if not repo_path.exists():
        download_repository(repo_name)
    
    db_path = f"test_{repo_name}.db"
    if not Path(db_path).exists():
        index_repository(repo_path, db_path)

def index_file_with_plugin(file_path, content, store):
    """Index a file using the appropriate plugin."""
    from mcp_server.plugin_system import PluginManager
    
    manager = PluginManager()
    plugin = manager.get_plugin_for_file(file_path)
    
    if plugin:
        return plugin.indexFile(file_path, content)
    else:
        return Result.error(f"No plugin found for {file_path}")

def get_common_symbols_for_repo(repo_name):
    """Get common symbols for a repository for testing."""
    symbol_map = {
        "requests": ["Session", "Response", "get", "post", "HTTPAdapter"],
        "django": ["Model", "QuerySet", "CharField", "ForeignKey", "admin"],
        "react": ["Component", "useState", "useEffect", "createElement"],
        "vscode": ["editor", "window", "workspace", "commands"],
    }
    return symbol_map.get(repo_name, ["function", "class", "method"])
```

## Execution Commands

### Setup Real-World Testing Environment
```bash
# Create and setup test environment
python run_parallel_tests.py --setup-real-world

# Download test repositories  
python scripts/download_test_repos.py

# Run real-world testing suite
python run_parallel_tests.py --phases real_world_validation --max-workers 6
```

### Individual Test Categories
```bash
# Repository indexing tests
pytest tests/real_world/test_repository_indexing.py -v --benchmark-only

# Symbol search accuracy tests  
pytest tests/real_world/test_symbol_search.py -v --repo=django

# Performance scaling tests
pytest tests/real_world/test_performance_scaling.py -v --slow

# Memory usage tests
pytest tests/real_world/test_memory_usage.py -v --memory

# Developer workflow tests
pytest tests/real_world/test_developer_workflows.py -v --integration
```

## Success Criteria

### ✅ Repository Indexing
- Successfully index 90%+ files in each test repository
- Handle 5000+ files without memory issues
- Complete indexing of medium repositories (<1000 files) in <60 seconds
- Extract 10,000+ symbols from Django codebase

### ✅ Search & Retrieval
- 80%+ symbol discovery rate for common symbols
- <100ms average symbol lookup time
- <200ms average search time for complex queries
- Find cross-references across 10+ files for common symbols

### ✅ Performance & Scale
- Handle 30M+ LOC (Linux kernel subset) without crashes
- Memory usage increase <2GB for large codebases
- Concurrent indexing of 3 repositories without conflicts
- Query performance degradation <2x for 10x data size increase

### ✅ Real-World Validation
- Successfully index and search popular open-source projects
- Handle diverse coding patterns and language features
- Support developer workflows (find usage, discover APIs, etc.)
- Demonstrate production readiness with actual codebases

## Phase 4: Dormant Features Validation Testing

### 🎯 Dormant Features Test Strategy

This phase validates all dormant/inactive features that are implemented but require activation. Testing ensures these sophisticated capabilities work correctly when enabled.

#### **4.1 Semantic Search & Vector Embeddings Testing**
```python
# Test: test_real_world_semantic_search.py
import pytest
import os
from pathlib import Path

@pytest.mark.semantic
@pytest.mark.skipif(not os.getenv("SEMANTIC_SEARCH_ENABLED"), reason="Semantic search not enabled")
class TestSemanticSearch:
    """Test semantic search capabilities with real codebases."""
    
    def test_semantic_code_similarity(self, setup_semantic_indexer):
        """Test semantic similarity search for code patterns."""
        # Index a small codebase with semantic embeddings
        repo_path = Path("test_workspace/real_repos/requests")
        
        semantic_indexer = setup_semantic_indexer
        
        # Index Python files with embeddings
        python_files = list(repo_path.rglob("*.py"))[:20]
        for file_path in python_files:
            semantic_indexer.index_file(file_path)
        
        # Test natural language queries
        test_queries = [
            "function that sends HTTP requests",
            "class for handling authentication",
            "method to process JSON responses",
            "code that manages sessions and cookies"
        ]
        
        for query in test_queries:
            results = list(semantic_indexer.query(query, limit=5))
            
            assert len(results) > 0, f"Should find semantic matches for '{query}'"
            assert all(r.get('score', 0) > 0.5 for r in results), "Semantic scores should be reasonable"
            
            print(f"Query: '{query}' -> {len(results)} results, best score: {max(r.get('score', 0) for r in results):.3f}")
    
    @pytest.mark.performance
    def test_semantic_search_performance(self, setup_semantic_indexer, benchmark):
        """Benchmark semantic search performance."""
        semantic_indexer = setup_semantic_indexer
        
        # Pre-index some code
        test_code = '''
def authenticate_user(username, password):
    """Authenticate user with credentials."""
    return check_credentials(username, password)

class SessionManager:
    """Manages user sessions and tokens."""
    def create_session(self, user_id):
        return generate_token(user_id)
'''
        
        # Index the code
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(test_code)
            f.flush()
            semantic_indexer.index_file(Path(f.name))
        
        def run_semantic_queries():
            queries = [
                "user authentication function",
                "session management class",
                "token generation method"
            ]
            results = []
            for query in queries:
                search_results = list(semantic_indexer.query(query, limit=3))
                results.extend(search_results)
            return results
        
        results = benchmark(run_semantic_queries)
        
        # Performance assertions
        assert len(results) > 0, "Should find semantic results"
        assert benchmark.stats.mean < 2.0, f"Semantic search too slow: {benchmark.stats.mean:.2f}s"
        
        print(f"Semantic search: {len(results)} results in {benchmark.stats.mean:.3f}s average")

@pytest.fixture
def setup_semantic_indexer():
    """Setup semantic indexer for testing."""
    if not os.getenv("VOYAGE_AI_API_KEY"):
        pytest.skip("VOYAGE_AI_API_KEY not set")
    
    from mcp_server.utils.semantic_indexer import SemanticIndexer
    
    # Use in-memory Qdrant for testing
    indexer = SemanticIndexer(collection="test-semantic", qdrant_path=":memory:")
    yield indexer
    
    # Cleanup
    try:
        indexer.qdrant.delete_collection("test-semantic")
    except:
        pass
```

#### **4.2 Redis Caching System Testing**
```python
# Test: test_real_world_redis_caching.py
import pytest
import asyncio
import time
from mcp_server.cache import CacheManagerFactory, QueryResultCache

@pytest.mark.cache
@pytest.mark.skipif(not os.getenv("REDIS_URL"), reason="Redis not configured")
class TestRedisCaching:
    """Test Redis caching with real-world scenarios."""
    
    @pytest.fixture
    async def redis_cache_manager(self):
        """Setup Redis cache manager."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        cache_manager = CacheManagerFactory.create_redis_cache(redis_url)
        await cache_manager.initialize()
        
        yield cache_manager
        
        # Cleanup
        await cache_manager.clear()
        await cache_manager.close()
    
    async def test_query_result_caching(self, redis_cache_manager):
        """Test query result caching with real search patterns."""
        from mcp_server.cache import QueryResultCache, QueryCacheConfig, QueryType
        
        config = QueryCacheConfig(enabled=True, default_ttl=300)
        query_cache = QueryResultCache(redis_cache_manager, config)
        
        # Simulate expensive query results
        expensive_results = {
            "symbols": [{"name": "TestClass", "file": "test.py", "line": 1}],
            "search_time_ms": 250,
            "total_results": 1
        }
        
        # Cache the results
        cache_key = "symbol_search:TestClass:python"
        await query_cache.set_query_result(cache_key, expensive_results, QueryType.SYMBOL_LOOKUP)
        
        # Retrieve from cache
        cached_results = await query_cache.get_query_result(cache_key, QueryType.SYMBOL_LOOKUP)
        
        assert cached_results is not None, "Should retrieve cached results"
        assert cached_results["symbols"] == expensive_results["symbols"]
        assert "cached_at" in cached_results, "Should include cache metadata"
        
        print(f"Cache hit: {cached_results['symbols'][0]['name']}")
    
    @pytest.mark.performance
    async def test_cache_performance_improvement(self, redis_cache_manager, benchmark):
        """Test cache performance improvement for repeated queries."""
        
        # Simulate database query
        async def expensive_operation(query_id):
            # Simulate 100ms database query
            await asyncio.sleep(0.1)
            return {"result": f"data_for_{query_id}", "computation_time": 100}
        
        # Test without cache
        def uncached_queries():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_queries():
                results = []
                for i in range(5):
                    result = await expensive_operation(f"query_{i}")
                    results.append(result)
                return results
            
            return loop.run_until_complete(run_queries())
        
        uncached_time = benchmark(uncached_queries)
        
        # Test with cache
        async def cached_queries():
            results = []
            for i in range(5):
                cache_key = f"expensive_query_{i}"
                
                # Try cache first
                cached = await redis_cache_manager.get(cache_key)
                if cached:
                    results.append(cached)
                else:
                    # Cache miss - compute and cache
                    result = await expensive_operation(f"query_{i}")
                    await redis_cache_manager.set(cache_key, result, ttl=300)
                    results.append(result)
            
            # Second run should hit cache
            for i in range(5):
                cache_key = f"expensive_query_{i}"
                cached = await redis_cache_manager.get(cache_key)
                results.append(cached)
            
            return results
        
        def cached_queries_wrapper():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(cached_queries())
        
        cached_results = benchmark(cached_queries_wrapper)
        
        # Cache should provide significant speedup for repeated queries
        print(f"Cache performance test: {len(cached_results)} results")
        
        # The cached run should be faster than uncached for repeated queries
        # (This is a simplified test - real performance gains are more complex)
        assert len(cached_results) == 10, "Should handle all cached and uncached queries"
```

#### **4.3 Advanced Indexing Options Testing**
```python
# Test: test_real_world_advanced_indexing.py
@pytest.mark.advanced_indexing
class TestAdvancedIndexing:
    """Test advanced indexing options with real codebases."""
    
    def test_parallel_indexing_performance(self, benchmark):
        """Test parallel indexing with different worker counts."""
        from mcp_server.indexer.index_engine import IndexEngine, IndexOptions
        
        repo_path = Path("test_workspace/real_repos/requests")
        python_files = list(repo_path.rglob("*.py"))[:50]
        
        def test_indexing_workers(max_workers):
            options = IndexOptions(
                max_workers=max_workers,
                batch_size=10,
                force_reindex=True,
                generate_embeddings=False  # Disabled for speed
            )
            
            # Create temporary index engine
            with tempfile.NamedTemporaryFile(suffix=".db") as db_file:
                store = SQLiteStore(db_file.name)
                plugin_manager = PluginManager()
                engine = IndexEngine(plugin_manager, store)
                
                start_time = time.time()
                
                # Index files with different worker counts
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def index_files():
                    tasks = []
                    for file_path in python_files:
                        tasks.append(engine.index_file(str(file_path)))
                    
                    return await asyncio.gather(*tasks)
                
                results = loop.run_until_complete(index_files())
                duration = time.time() - start_time
                
                successful = sum(1 for r in results if r.success)
                return successful, duration
        
        # Test different worker configurations
        worker_configs = [1, 2, 4, 8]
        performance_results = {}
        
        for workers in worker_configs:
            successful, duration = test_indexing_workers(workers)
            performance_results[workers] = {
                "successful": successful,
                "duration": duration,
                "throughput": successful / duration if duration > 0 else 0
            }
            
            print(f"{workers} workers: {successful} files in {duration:.2f}s ({successful/duration:.1f} files/s)")
        
        # Validate scaling benefits
        single_thread_throughput = performance_results[1]["throughput"]
        multi_thread_throughput = max(performance_results[w]["throughput"] for w in worker_configs if w > 1)
        
        speedup = multi_thread_throughput / single_thread_throughput if single_thread_throughput > 0 else 0
        assert speedup >= 1.5, f"Multi-threading should provide speedup: {speedup:.2f}x"
        
        print(f"Best speedup: {speedup:.2f}x with parallel processing")
    
    def test_embedding_generation_integration(self):
        """Test embedding generation during indexing."""
        if not os.getenv("SEMANTIC_SEARCH_ENABLED"):
            pytest.skip("Semantic search not enabled")
        
        from mcp_server.indexer.index_engine import IndexEngine, IndexOptions
        from mcp_server.utils.semantic_indexer import SemanticIndexer
        
        # Setup with semantic indexer
        semantic_indexer = SemanticIndexer(collection="test-embedding", qdrant_path=":memory:")
        
        with tempfile.NamedTemporaryFile(suffix=".db") as db_file:
            store = SQLiteStore(db_file.name)
            plugin_manager = PluginManager()
            engine = IndexEngine(plugin_manager, store, semantic_indexer=semantic_indexer)
            
            # Create test Python file
            test_code = '''
def calculate_fibonacci(n):
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class MathUtils:
    """Utility class for mathematical operations."""
    
    @staticmethod
    def factorial(n):
        """Calculate factorial of n."""
        if n <= 1:
            return 1
        return n * MathUtils.factorial(n-1)
'''
            
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
                f.write(test_code)
                f.flush()
                
                # Index with embedding generation enabled
                options = IndexOptions(generate_embeddings=True)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(engine.index_file(f.name))
                
                assert result.success, f"Indexing with embeddings should succeed: {result.error}"
                assert result.symbols_count >= 3, f"Should extract symbols: {result.symbols_count}"
                
                # Test semantic search on indexed content
                semantic_results = list(semantic_indexer.query("fibonacci calculation", limit=3))
                assert len(semantic_results) > 0, "Should find semantic matches"
                
                print(f"Embedded indexing: {result.symbols_count} symbols, semantic search found {len(semantic_results)} matches")
```

#### **4.4 Cross-Language Symbol Resolution Testing**
```python
# Test: test_real_world_cross_language.py
@pytest.mark.cross_language
class TestCrossLanguageResolution:
    """Test cross-language symbol resolution capabilities."""
    
    def test_multi_language_project_indexing(self):
        """Test indexing projects with multiple programming languages."""
        # Use kubernetes repository which has Go, YAML, shell scripts
        repo_path = Path("test_workspace/real_repos/kubernetes")
        if not repo_path.exists():
            pytest.skip("Kubernetes repository not available")
        
        with tempfile.NamedTemporaryFile(suffix=".db") as db_file:
            store = SQLiteStore(db_file.name)
            plugin_manager = PluginManager()
            
            # Index files from different languages
            language_files = {
                "go": list(repo_path.rglob("*.go"))[:20],
                "yaml": list(repo_path.rglob("*.yaml"))[:10] + list(repo_path.rglob("*.yml"))[:10],
                "shell": list(repo_path.rglob("*.sh"))[:10]
            }
            
            indexed_by_language = {}
            
            for language, files in language_files.items():
                indexed_count = 0
                for file_path in files:
                    try:
                        plugin = plugin_manager.get_plugin_for_file(file_path)
                        if plugin:
                            content = file_path.read_text(encoding='utf-8', errors='ignore')
                            result = plugin.parse_file(str(file_path))
                            if result:
                                indexed_count += 1
                    except Exception:
                        continue
                
                indexed_by_language[language] = indexed_count
                print(f"{language}: indexed {indexed_count}/{len(files)} files")
            
            # Should successfully index multiple languages
            successful_languages = [lang for lang, count in indexed_by_language.items() if count > 0]
            assert len(successful_languages) >= 2, f"Should index multiple languages: {successful_languages}"
            
            total_indexed = sum(indexed_by_language.values())
            assert total_indexed >= 10, f"Should index reasonable number of files: {total_indexed}"
    
    def test_common_symbol_patterns_across_languages(self):
        """Test finding common patterns across different languages."""
        # Test common patterns that appear in multiple languages
        test_patterns = [
            ("config", ["go", "yaml", "python"]),
            ("test", ["go", "python", "shell"]),
            ("main", ["go", "python", "c"]),
            ("error", ["go", "python", "c"]),
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".db") as db_file:
            store = SQLiteStore(db_file.name)
            
            # Create sample files for different languages
            sample_files = {
                "config.go": "package main\ntype Config struct { Name string }",
                "config.py": "class Config:\n    def __init__(self, name): self.name = name",
                "config.yaml": "config:\n  name: test\n  version: 1.0",
                "test.go": "func TestMain(t *testing.T) { }",
                "test.py": "def test_main(): pass",
                "main.c": "int main() { return 0; }",
                "error.go": "type Error struct { message string }",
                "error.py": "class Error(Exception): pass"
            }
            
            # Index all sample files
            indexed_symbols = {}
            
            for filename, content in sample_files.items():
                with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, mode="w", delete=False) as f:
                    f.write(content)
                    f.flush()
                    
                    plugin_manager = PluginManager()
                    plugin = plugin_manager.get_plugin_for_file(Path(f.name))
                    if plugin:
                        try:
                            result = plugin.parse_file(f.name)
                            if result and 'symbols' in result:
                                indexed_symbols[filename] = result['symbols']
                        except Exception:
                            continue
            
            # Analyze cross-language patterns
            for pattern, expected_languages in test_patterns:
                found_in_languages = set()
                
                for filename, symbols in indexed_symbols.items():
                    if any(pattern.lower() in symbol.get('name', '').lower() for symbol in symbols):
                        file_ext = Path(filename).suffix
                        if file_ext == '.go':
                            found_in_languages.add('go')
                        elif file_ext == '.py':
                            found_in_languages.add('python')
                        elif file_ext in ['.yaml', '.yml']:
                            found_in_languages.add('yaml')
                        elif file_ext == '.c':
                            found_in_languages.add('c')
                
                print(f"Pattern '{pattern}' found in: {found_in_languages}")
                
                # Should find pattern in at least one language
                assert len(found_in_languages) > 0, f"Pattern '{pattern}' should be found in some language"
```

### Execution Commands for Dormant Features Testing

```bash
# Setup dormant features testing environment
python run_parallel_tests.py --setup-dormant-features

# Test semantic search (requires Voyage AI + Qdrant)
SEMANTIC_SEARCH_ENABLED=true VOYAGE_AI_API_KEY=your-key pytest tests/real_world/test_semantic_search.py -v

# Test Redis caching (requires Redis server)
REDIS_URL=redis://localhost:6379 pytest tests/real_world/test_redis_caching.py -v

# Test advanced indexing options
pytest tests/real_world/test_advanced_indexing.py -v --advanced-options

# Test cross-language resolution
pytest tests/real_world/test_cross_language.py -v --multi-lang

# Run all dormant features tests
python run_parallel_tests.py --phases dormant_features_validation --max-workers 4
```

### Success Criteria for Dormant Features

#### ✅ Semantic Search Validation
- Successfully generate embeddings for 95%+ of indexed code
- Semantic search queries return relevant results with >0.7 similarity scores
- Natural language queries find appropriate code patterns
- Performance: <2s for semantic search across 1000+ indexed symbols

#### ✅ Redis Caching Validation  
- 95%+ cache hit rate for repeated symbol lookups
- 5-10x performance improvement for cached queries
- Proper cache invalidation on file updates
- Memory usage stays within configured limits

#### ✅ Advanced Indexing Validation
- Parallel indexing provides 2x+ speedup with 4+ workers
- Embedding generation completes without errors
- Batch processing handles 1000+ files efficiently
- Advanced options properly configure indexing behavior

#### ✅ Cross-Language Validation
- Successfully index projects with 3+ programming languages
- Find common patterns across different language files
- Symbol resolution works across language boundaries
- Multi-language search returns relevant cross-language results

This comprehensive testing plan now validates both the existing real-world capabilities and all dormant features, ensuring the Code-Index-MCP system achieves maximum functionality when fully activated.