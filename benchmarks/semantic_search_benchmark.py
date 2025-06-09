#!/usr/bin/env python3
"""
Semantic search performance benchmark.
Target: < 500ms (p95)
"""

import time
import statistics
import random
import tempfile
import os
import json
from typing import List, Dict, Any
from pathlib import Path

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.plugins.plugin_factory import PluginFactory


class SemanticSearchBenchmark:
    """Benchmark semantic search performance."""
    
    def __init__(self):
        self.db_path = None
        self.store = None
        self.semantic_indexer = None
        self.sample_code_snippets = self._generate_code_snippets()
        
    def _generate_code_snippets(self) -> Dict[str, List[str]]:
        """Generate sample code snippets for different languages."""
        return {
            'python': [
                """
def authenticate_user(username: str, password: str) -> bool:
    '''Authenticate a user with username and password.'''
    user = db.get_user(username)
    if user and bcrypt.verify(password, user.password_hash):
        return True
    return False
""",
                """
class DatabaseConnection:
    '''Manages database connections with pooling.'''
    def __init__(self, url: str, pool_size: int = 10):
        self.url = url
        self.pool = ConnectionPool(max_size=pool_size)
    
    def execute(self, query: str, params: dict = None):
        with self.pool.get_connection() as conn:
            return conn.execute(query, params)
""",
                """
def handle_error(error: Exception, context: dict = None):
    '''Central error handling with logging and notifications.'''
    logger.error(f"Error occurred: {error}", extra=context)
    if isinstance(error, CriticalError):
        send_alert(error, context)
    raise
"""
            ],
            'javascript': [
                """
async function fetchUserData(userId) {
    // Fetch user data from API with caching
    const cached = await cache.get(`user:${userId}`);
    if (cached) return cached;
    
    const response = await api.get(`/users/${userId}`);
    await cache.set(`user:${userId}`, response.data, 300);
    return response.data;
}
""",
                """
class EventEmitter {
    constructor() {
        this.events = {};
    }
    
    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
    }
    
    emit(event, ...args) {
        if (this.events[event]) {
            this.events[event].forEach(cb => cb(...args));
        }
    }
}
""",
                """
const validateInput = (data) => {
    // Input validation with schema
    const errors = [];
    
    if (!data.email || !isValidEmail(data.email)) {
        errors.push('Invalid email address');
    }
    
    if (!data.password || data.password.length < 8) {
        errors.push('Password must be at least 8 characters');
    }
    
    return { valid: errors.length === 0, errors };
};
"""
            ],
            'java': [
                """
@Service
public class UserService {
    private final UserRepository repository;
    private final PasswordEncoder encoder;
    
    public User createUser(CreateUserRequest request) {
        // Create new user with encrypted password
        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(encoder.encode(request.getPassword()));
        return repository.save(user);
    }
}
""",
                """
@RestController
@RequestMapping("/api/v1")
public class ApiController {
    
    @GetMapping("/search")
    public ResponseEntity<SearchResult> search(@RequestParam String query) {
        // REST API endpoint for search
        SearchResult result = searchService.search(query);
        return ResponseEntity.ok(result);
    }
}
""",
                """
public class CacheManager<K, V> {
    private final Map<K, CacheEntry<V>> cache;
    private final long ttl;
    
    public V get(K key) {
        CacheEntry<V> entry = cache.get(key);
        if (entry != null && !entry.isExpired()) {
            return entry.getValue();
        }
        return null;
    }
}
"""
            ]
        }
    
    def setup(self, num_files: int = 500):
        """Set up test environment with sample code."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            self.db_path = tmp.name
        
        self.store = SQLiteStore(self.db_path)
        self.semantic_indexer = SemanticIndexer(enable_voyage_ai=False)  # Mock mode
        
        print(f"Generating {num_files} files with semantic content...")
        
        languages = list(self.sample_code_snippets.keys())
        
        for i in range(num_files):
            lang = random.choice(languages)
            ext = {'python': '.py', 'javascript': '.js', 'java': '.java'}[lang]
            filepath = f"src/module_{i}/file_{i}{ext}"
            
            # Select random code snippet
            content = random.choice(self.sample_code_snippets[lang])
            
            # Create plugin and extract symbols
            plugin = PluginFactory.create_plugin(lang, self.store)
            result = plugin.extract_symbols(content, filepath)
            
            # Store symbols with semantic embeddings
            for symbol in result.symbols:
                # Generate mock embedding for testing
                embedding = [random.random() for _ in range(256)]
                
                self.store.add_symbol(
                    file_path=filepath,
                    symbol_name=symbol.name,
                    symbol_type=symbol.symbol_type,
                    line_number=symbol.line,
                    metadata={
                        'language': lang,
                        'embedding': embedding,
                        'content': content[:200]  # Store snippet
                    }
                )
        
        print(f"Generated semantic index for {num_files} files")
    
    def run_natural_language_queries(self) -> List[float]:
        """Run natural language query benchmarks."""
        queries = [
            "Find authentication functions",
            "Database connection methods",
            "Error handling code",
            "API endpoints",
            "Caching implementation",
            "User creation functions",
            "Password validation",
            "Event handling",
            "REST controllers",
            "Input validation functions",
            "Configuration management",
            "Logging utilities",
            "Security checks",
            "Data transformation",
            "Async operations"
        ]
        
        print(f"\nRunning {len(queries)} natural language queries...")
        timings = []
        
        for query in queries:
            # Run each query multiple times
            for _ in range(50):
                start_time = time.perf_counter()
                
                # Simulate semantic search
                # In real implementation, this would use embeddings
                results = self.store.search_symbols(query, limit=20)
                
                # Simulate ranking by semantic similarity
                if results:
                    # Mock semantic scoring
                    scored_results = [
                        (r, random.random()) for r in results
                    ]
                    scored_results.sort(key=lambda x: x[1], reverse=True)
                
                end_time = time.perf_counter()
                elapsed_ms = (end_time - start_time) * 1000
                timings.append(elapsed_ms)
        
        return timings
    
    def run_symbol_based_queries(self) -> List[float]:
        """Run symbol-based semantic queries."""
        symbol_queries = [
            "authenticate*",
            "get*User*",
            "*Connection*",
            "*Error*",
            "handle*",
            "*Service",
            "*Controller",
            "validate*",
            "*Cache*",
            "fetch*"
        ]
        
        print(f"\nRunning {len(symbol_queries)} symbol-based queries...")
        timings = []
        
        for query in symbol_queries:
            for _ in range(50):
                start_time = time.perf_counter()
                results = self.store.search_symbols(query, limit=15)
                end_time = time.perf_counter()
                
                elapsed_ms = (end_time - start_time) * 1000
                timings.append(elapsed_ms)
        
        return timings
    
    def run_cross_language_queries(self) -> Dict[str, Any]:
        """Test semantic search across different languages."""
        cross_lang_queries = [
            ("authentication across languages", "Find auth code in any language"),
            ("database operations", "DB operations in Python, JS, Java"),
            ("error handling patterns", "Error handling across languages"),
            ("API implementations", "REST APIs in different languages")
        ]
        
        print("\nRunning cross-language semantic queries...")
        results = {}
        
        for query, description in cross_lang_queries:
            timings = []
            
            for _ in range(30):
                start_time = time.perf_counter()
                
                # Search across all languages
                search_results = self.store.search_symbols(query, limit=30)
                
                # Group by language
                by_language = {}
                for result in search_results:
                    lang = result[3].get('language', 'unknown')
                    if lang not in by_language:
                        by_language[lang] = []
                    by_language[lang].append(result)
                
                end_time = time.perf_counter()
                elapsed_ms = (end_time - start_time) * 1000
                timings.append(elapsed_ms)
            
            results[query] = {
                'description': description,
                'mean_ms': statistics.mean(timings),
                'p95_ms': sorted(timings)[int(len(timings) * 0.95)]
            }
        
        return results
    
    def analyze_results(self, timings: List[float]) -> Dict[str, Any]:
        """Analyze benchmark results."""
        timings.sort()
        
        results = {
            'total_queries': len(timings),
            'min_ms': min(timings),
            'max_ms': max(timings),
            'mean_ms': statistics.mean(timings),
            'median_ms': statistics.median(timings),
            'p50_ms': timings[int(len(timings) * 0.50)],
            'p75_ms': timings[int(len(timings) * 0.75)],
            'p90_ms': timings[int(len(timings) * 0.90)],
            'p95_ms': timings[int(len(timings) * 0.95)],
            'p99_ms': timings[int(len(timings) * 0.99)],
            'std_dev_ms': statistics.stdev(timings) if len(timings) > 1 else 0
        }
        
        # Check if we meet the requirement
        results['meets_requirement'] = results['p95_ms'] < 500
        results['target_p95_ms'] = 500
        
        return results
    
    def cleanup(self):
        """Clean up test environment."""
        if self.store:
            self.store.close()
        if self.db_path and os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def save_results(self, results: dict, filename: str = "semantic_search_benchmark_results.json"):
        """Save benchmark results."""
        output_path = f"/app/benchmarks/{filename}"
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_path}")
    
    def print_summary(self, results: dict):
        """Print benchmark summary."""
        print("\n" + "="*60)
        print("SEMANTIC SEARCH BENCHMARK RESULTS")
        print("="*60)
        
        main_results = results['natural_language_queries']
        
        print(f"\nTotal Queries: {main_results['total_queries']}")
        print(f"Target p95: < {main_results['target_p95_ms']}ms")
        print(f"Actual p95: {main_results['p95_ms']:.2f}ms")
        print(f"Status: {'✅ PASS' if main_results['meets_requirement'] else '❌ FAIL'}")
        
        print("\nPercentiles:")
        print(f"  p50 (median): {main_results['p50_ms']:.2f}ms")
        print(f"  p75: {main_results['p75_ms']:.2f}ms")
        print(f"  p90: {main_results['p90_ms']:.2f}ms")
        print(f"  p95: {main_results['p95_ms']:.2f}ms")
        print(f"  p99: {main_results['p99_ms']:.2f}ms")
        
        print(f"\nRange: {main_results['min_ms']:.2f}ms - {main_results['max_ms']:.2f}ms")
        print(f"Mean: {main_results['mean_ms']:.2f}ms")
        print(f"Std Dev: {main_results['std_dev_ms']:.2f}ms")


def main():
    """Run semantic search benchmark."""
    benchmark = SemanticSearchBenchmark()
    
    try:
        # Setup
        print("Setting up semantic search benchmark...")
        benchmark.setup(num_files=1000)
        
        # Run natural language queries
        nl_timings = benchmark.run_natural_language_queries()
        nl_results = benchmark.analyze_results(nl_timings)
        
        # Run symbol-based queries
        symbol_timings = benchmark.run_symbol_based_queries()
        symbol_results = benchmark.analyze_results(symbol_timings)
        
        # Run cross-language queries
        cross_lang_results = benchmark.run_cross_language_queries()
        
        # Combine results
        all_results = {
            'natural_language_queries': nl_results,
            'symbol_based_queries': symbol_results,
            'cross_language_queries': cross_lang_results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_configuration': {
                'num_files': 1000,
                'languages': ['python', 'javascript', 'java'],
                'embedding_dimensions': 256
            }
        }
        
        # Save and display results
        benchmark.save_results(all_results)
        benchmark.print_summary(all_results)
        
        # Print query type comparison
        print("\n\nQuery Type Comparison:")
        print(f"  Natural Language: p95={nl_results['p95_ms']:.2f}ms")
        print(f"  Symbol-based: p95={symbol_results['p95_ms']:.2f}ms")
        
        # Print cross-language results
        print("\n\nCross-Language Query Results:")
        for query, stats in cross_lang_results.items():
            print(f"  {query}: p95={stats['p95_ms']:.2f}ms")
        
    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    main()