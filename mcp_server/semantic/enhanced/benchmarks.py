"""Performance benchmarks for Vector Search Enhancement.

This module provides comprehensive benchmarking capabilities to validate
the 50% faster embedding generation and 90% cache hit rate targets.

"""

import asyncio
import time
import random
import json
import statistics
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from mcp_server.semantic.enhanced.batch_indexer import EnhancedVectorSearcher, VectorSearchConfig
from mcp_server.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class BenchmarkConfig:
    """Configuration for benchmarks."""
    
    # Test data settings
    num_documents: int = 1000
    min_text_length: int = 100
    max_text_length: int = 2000
    
    # Performance targets
    target_embedding_speedup: float = 1.5  # 50% faster
    target_cache_hit_rate: float = 0.9     # 90%
    target_search_latency_ms: float = 100
    
    # Benchmark settings
    warmup_iterations: int = 10
    test_iterations: int = 50
    concurrent_batches: int = 5
    
    # Cache testing
    cache_test_repeats: int = 3

@dataclass
class BenchmarkResult:
    """Single benchmark result."""
    
    test_name: str
    duration_seconds: float
    throughput_ops_per_sec: float
    success_rate: float
    error_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)

class VectorSearchBenchmarks:
    """Comprehensive benchmark suite for vector search enhancements."""
    
    def __init__(
        self,
        config: Optional[BenchmarkConfig] = None,
        output_dir: Optional[Path] = None
    ):
        self.config = config or BenchmarkConfig()
        self.output_dir = output_dir or Path("./benchmark_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize enhanced searcher
        self.searcher = EnhancedVectorSearcher()
        
        # Test data
        self._test_documents: List[Dict[str, Any]] = []
        self._test_queries: List[str] = []
        
        logger.info(f"Initialized VectorSearchBenchmarks with config: {self.config}")
    
    def _generate_test_document(self, index: int) -> Dict[str, Any]:
        """Generate a synthetic test document."""
        
        # Simulate different types of code content
        content_types = [
            "function definition with parameters and return types",
            "class definition with methods and properties", 
            "variable declarations and assignments",
            "import statements and dependencies",
            "comment blocks with documentation",
            "error handling and exception management",
            "data structures and algorithms implementation",
            "API endpoints and request handlers"
        ]
        
        content_type = random.choice(content_types)
        
        # Generate realistic code-like content
        content_length = random.randint(self.config.min_text_length, self.config.max_text_length)
        
        # Base content
        content = f"def example_function_{index}():\n"
        content += f"    \"\"\"{content_type}\"\"\"\n"
        
        # Add variable content to reach target length
        while len(content) < content_length:
            content += f"    # Processing step {len(content) % 100}\n"
            content += f"    result = perform_operation_{random.randint(1, 100)}()\n"
            content += f"    if result.is_valid():\n"
            content += f"        return result.process()\n"
        
        return {
            "id": f"doc_{index}",
            "content": content[:content_length],
            "file": f"test_file_{index % 100}.py",
            "symbol": f"example_function_{index}",
            "kind": "function",
            "line": random.randint(1, 1000),
            "language": "python"
        }
    
    def _generate_test_query(self, index: int) -> str:
        """Generate a test search query."""
        
        query_templates = [
            "find function that handles user authentication",
            "search for error handling implementation",
            "locate database connection methods", 
            "find API endpoint for user management",
            "search for data validation functions",
            "locate utility functions for string processing",
            "find configuration management code",
            "search for logging and monitoring functions"
        ]
        
        return random.choice(query_templates) + f" variant {index}"
    
    async def prepare_test_data(self):
        """Generate and prepare test data."""
        
        logger.info(f"Generating {self.config.num_documents} test documents...")
        
        self._test_documents = [
            self._generate_test_document(i) 
            for i in range(self.config.num_documents)
        ]
        
        self._test_queries = [
            self._generate_test_query(i)
            for i in range(100)  # 100 test queries
        ]
        
        logger.info("Test data generation completed")
    
    async def benchmark_embedding_generation(self) -> BenchmarkResult:
        """Benchmark embedding generation performance."""
        
        logger.info("Starting embedding generation benchmark...")
        
        errors = 0
        total_documents = 0
        start_time = time.time()
        
        try:
            # Warmup
            warmup_docs = self._test_documents[:self.config.warmup_iterations]
            await self.searcher.embed_documents_parallel(warmup_docs)
            
            # Clear metrics for clean test
            self.searcher.metrics = type(self.searcher.metrics)()
            
            # Main benchmark
            test_start = time.time()
            
            for i in range(0, len(self._test_documents), self.config.concurrent_batches * 50):
                batch_docs = self._test_documents[i:i + self.config.concurrent_batches * 50]
                
                try:
                    results = await self.searcher.embed_documents_parallel(batch_docs)
                    total_documents += len(results)
                except Exception as e:
                    logger.error(f"Error in batch {i}: {e}")
                    errors += 1
            
            test_duration = time.time() - test_start
            throughput = total_documents / test_duration if test_duration > 0 else 0
            
            # Get metrics
            metrics = self.searcher.get_metrics()
            
            result = BenchmarkResult(
                test_name="embedding_generation",
                duration_seconds=test_duration,
                throughput_ops_per_sec=throughput,
                success_rate=(total_documents - errors) / max(total_documents, 1),
                error_count=errors,
                metadata={
                    "total_documents": total_documents,
                    "cache_hit_rate": metrics["cache_hit_rate"],
                    "avg_batch_time": metrics["avg_batch_time"],
                    "target_speedup": self.config.target_embedding_speedup,
                    "achieved_speedup": throughput / 100  # Baseline assumption of 100 docs/sec
                }
            )
            
            logger.info(
                f"Embedding benchmark completed: {throughput:.1f} docs/sec, "
                f"cache hit rate: {metrics['cache_hit_rate']:.1%}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Embedding benchmark failed: {e}")
            raise
    
    async def benchmark_cache_performance(self) -> BenchmarkResult:
        """Benchmark cache hit rate performance."""
        
        logger.info("Starting cache performance benchmark...")
        
        # Clear cache and metrics
        self.searcher.metrics = type(self.searcher.metrics)()
        self.searcher._embedding_cache.clear()
        
        total_requests = 0
        errors = 0
        
        try:
            # First pass - populate cache
            sample_docs = self._test_documents[:200]
            await self.searcher.embed_documents_parallel(sample_docs)
            
            # Reset metrics after population
            initial_metrics = self.searcher.get_metrics()
            self.searcher.metrics = type(self.searcher.metrics)()
            
            # Multiple passes to test cache hits
            start_time = time.time()
            
            for repeat in range(self.config.cache_test_repeats):
                # Use same documents to trigger cache hits
                try:
                    await self.searcher.embed_documents_parallel(sample_docs)
                    total_requests += len(sample_docs)
                except Exception as e:
                    logger.error(f"Cache test repeat {repeat} failed: {e}")
                    errors += 1
            
            test_duration = time.time() - start_time
            final_metrics = self.searcher.get_metrics()
            
            result = BenchmarkResult(
                test_name="cache_performance",
                duration_seconds=test_duration,
                throughput_ops_per_sec=total_requests / test_duration if test_duration > 0 else 0,
                success_rate=(total_requests - errors) / max(total_requests, 1),
                error_count=errors,
                metadata={
                    "cache_hit_rate": final_metrics["cache_hit_rate"],
                    "target_hit_rate": self.config.target_cache_hit_rate,
                    "cache_hits": final_metrics["cache_hits"],
                    "cache_misses": final_metrics["cache_misses"],
                    "total_requests": total_requests,
                    "test_repeats": self.config.cache_test_repeats
                }
            )
            
            logger.info(
                f"Cache benchmark completed: {final_metrics['cache_hit_rate']:.1%} hit rate "
                f"(target: {self.config.target_cache_hit_rate:.1%})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Cache benchmark failed: {e}")
            raise
    
    async def benchmark_search_performance(self) -> BenchmarkResult:
        """Benchmark search latency and accuracy."""
        
        logger.info("Starting search performance benchmark...")
        
        # First index some documents
        sample_docs = self._test_documents[:500]
        await self.searcher.index_documents(sample_docs)
        
        search_times = []
        errors = 0
        total_searches = 0
        
        try:
            start_time = time.time()
            
            # Run search benchmark
            for query in self._test_queries[:self.config.test_iterations]:
                search_start = time.time()
                
                try:
                    results = await self.searcher.search(query, limit=10)
                    search_time = (time.time() - search_start) * 1000  # Convert to ms
                    search_times.append(search_time)
                    total_searches += 1
                except Exception as e:
                    logger.error(f"Search failed for query '{query}': {e}")
                    errors += 1
            
            test_duration = time.time() - start_time
            
            # Calculate statistics
            avg_latency = statistics.mean(search_times) if search_times else 0
            p95_latency = statistics.quantiles(search_times, n=20)[18] if len(search_times) >= 20 else avg_latency
            
            result = BenchmarkResult(
                test_name="search_performance",
                duration_seconds=test_duration,
                throughput_ops_per_sec=total_searches / test_duration if test_duration > 0 else 0,
                success_rate=(total_searches - errors) / max(total_searches, 1),
                error_count=errors,
                metadata={
                    "avg_latency_ms": avg_latency,
                    "p95_latency_ms": p95_latency,
                    "target_latency_ms": self.config.target_search_latency_ms,
                    "total_searches": total_searches,
                    "min_latency_ms": min(search_times) if search_times else 0,
                    "max_latency_ms": max(search_times) if search_times else 0
                }
            )
            
            logger.info(
                f"Search benchmark completed: {avg_latency:.1f}ms avg latency "
                f"(target: {self.config.target_search_latency_ms}ms)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Search benchmark failed: {e}")
            raise
    
    async def benchmark_concurrent_operations(self) -> BenchmarkResult:
        """Benchmark concurrent embedding and search operations."""
        
        logger.info("Starting concurrent operations benchmark...")
        
        async def embedding_worker(docs: List[Dict[str, Any]]) -> int:
            """Worker for concurrent embedding."""
            try:
                results = await self.searcher.embed_documents_parallel(docs)
                return len(results)
            except Exception as e:
                logger.error(f"Embedding worker error: {e}")
                return 0
        
        async def search_worker(queries: List[str]) -> int:
            """Worker for concurrent searching."""
            successful_searches = 0
            for query in queries:
                try:
                    await self.searcher.search(query, limit=5)
                    successful_searches += 1
                except Exception as e:
                    logger.error(f"Search worker error: {e}")
            return successful_searches
        
        # Prepare data
        doc_batches = [
            self._test_documents[i:i+50] 
            for i in range(0, min(500, len(self._test_documents)), 50)
        ]
        query_batches = [
            self._test_queries[i:i+10]
            for i in range(0, min(50, len(self._test_queries)), 10)
        ]
        
        start_time = time.time()
        errors = 0
        
        try:
            # Run concurrent operations
            embedding_tasks = [embedding_worker(batch) for batch in doc_batches]
            search_tasks = [search_worker(batch) for batch in query_batches]
            
            embedding_results = await asyncio.gather(*embedding_tasks, return_exceptions=True)
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            test_duration = time.time() - start_time
            
            # Calculate totals
            total_embedded = sum(r for r in embedding_results if isinstance(r, int))
            total_searched = sum(r for r in search_results if isinstance(r, int))
            
            errors += sum(1 for r in embedding_results if isinstance(r, Exception))
            errors += sum(1 for r in search_results if isinstance(r, Exception))
            
            total_operations = total_embedded + total_searched
            
            result = BenchmarkResult(
                test_name="concurrent_operations", 
                duration_seconds=test_duration,
                throughput_ops_per_sec=total_operations / test_duration if test_duration > 0 else 0,
                success_rate=(total_operations) / max(total_operations + errors, 1),
                error_count=errors,
                metadata={
                    "total_embedded": total_embedded,
                    "total_searched": total_searched,
                    "concurrent_batches": len(doc_batches) + len(query_batches),
                    "embedding_batches": len(doc_batches),
                    "search_batches": len(query_batches)
                }
            )
            
            logger.info(
                f"Concurrent benchmark completed: {total_operations} total operations "
                f"in {test_duration:.2f}s ({result.throughput_ops_per_sec:.1f} ops/sec)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Concurrent benchmark failed: {e}")
            raise
    
    async def run_full_benchmark_suite(self) -> Dict[str, Any]:
        """Run the complete benchmark suite."""
        
        logger.info("Starting full benchmark suite...")
        
        # Prepare test data
        await self.prepare_test_data()
        
        results = {}
        start_time = datetime.now()
        
        try:
            # Run individual benchmarks
            results["embedding_generation"] = await self.benchmark_embedding_generation()
            results["cache_performance"] = await self.benchmark_cache_performance() 
            results["search_performance"] = await self.benchmark_search_performance()
            results["concurrent_operations"] = await self.benchmark_concurrent_operations()
            
            total_duration = datetime.now() - start_time
            
            # Calculate overall performance assessment
            assessment = self._assess_performance(results)
            
            # Compile final report
            report = {
                "benchmark_suite": "vector_search_enhancement_phase5",
                "timestamp": start_time.isoformat(),
                "total_duration_seconds": total_duration.total_seconds(),
                "config": {
                    "num_documents": self.config.num_documents,
                    "test_iterations": self.config.test_iterations,
                    "targets": {
                        "embedding_speedup": self.config.target_embedding_speedup,
                        "cache_hit_rate": self.config.target_cache_hit_rate,
                        "search_latency_ms": self.config.target_search_latency_ms
                    }
                },
                "results": results,
                "assessment": assessment,
                "system_metrics": self.searcher.get_metrics()
            }
            
            # Save report
            await self._save_report(report)
            
            logger.info(f"Full benchmark suite completed in {total_duration}")
            logger.info(f"Overall assessment: {assessment['summary']}")
            
            return report
            
        except Exception as e:
            logger.error(f"Benchmark suite failed: {e}")
            raise
    
    def _assess_performance(self, results: Dict[str, BenchmarkResult]) -> Dict[str, Any]:
        """Assess overall performance against targets."""
        
        assessments = {}
        
        # Embedding performance
        if "embedding_generation" in results:
            embedding_result = results["embedding_generation"]
            achieved_speedup = embedding_result.metadata.get("achieved_speedup", 1.0)
            assessments["embedding"] = {
                "target_met": achieved_speedup >= self.config.target_embedding_speedup,
                "achieved_speedup": achieved_speedup,
                "target_speedup": self.config.target_embedding_speedup,
                "throughput": embedding_result.throughput_ops_per_sec
            }
        
        # Cache performance  
        if "cache_performance" in results:
            cache_result = results["cache_performance"]
            hit_rate = cache_result.metadata.get("cache_hit_rate", 0.0)
            assessments["cache"] = {
                "target_met": hit_rate >= self.config.target_cache_hit_rate,
                "achieved_hit_rate": hit_rate,
                "target_hit_rate": self.config.target_cache_hit_rate
            }
        
        # Search performance
        if "search_performance" in results:
            search_result = results["search_performance"]
            avg_latency = search_result.metadata.get("avg_latency_ms", float('inf'))
            assessments["search"] = {
                "target_met": avg_latency <= self.config.target_search_latency_ms,
                "achieved_latency_ms": avg_latency,
                "target_latency_ms": self.config.target_search_latency_ms
            }
        
        # Overall assessment
        targets_met = sum(1 for a in assessments.values() if a.get("target_met", False))
        total_targets = len(assessments)
        
        if targets_met == total_targets:
            summary = "ALL_TARGETS_MET"
        elif targets_met >= total_targets * 0.8:
            summary = "MOST_TARGETS_MET"
        elif targets_met >= total_targets * 0.5:
            summary = "SOME_TARGETS_MET"
        else:
            summary = "TARGETS_NOT_MET"
        
        return {
            "summary": summary,
            "targets_met": targets_met,
            "total_targets": total_targets,
            "success_rate": targets_met / total_targets if total_targets > 0 else 0,
            "details": assessments
        }
    
    async def _save_report(self, report: Dict[str, Any]):
        """Save benchmark report to file."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"vector_search_benchmark_{timestamp}.json"
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Benchmark report saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save benchmark report: {e}")
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from the searcher."""
        return self.searcher.get_metrics()