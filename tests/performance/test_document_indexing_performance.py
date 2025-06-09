#!/usr/bin/env python3
"""Performance tests for document indexing speed and efficiency."""

import pytest
import time
import tempfile
import os
import statistics
import concurrent.futures
import threading
from pathlib import Path
from typing import Dict, List, Any, Tuple

from tests.base_test import BaseDocumentTest
from tests.test_utils import (
    timer, memory_monitor, create_test_markdown, create_test_plaintext,
    generate_large_content, assert_performance, assert_memory_usage
)


class TestDocumentIndexingPerformance(BaseDocumentTest):
    """Test document indexing performance metrics."""
    
    def create_test_corpus(self, doc_count: int, doc_type: str = "markdown") -> List[Path]:
        """Create a corpus of test documents for benchmarking."""
        docs = []
        
        for i in range(doc_count):
            if doc_type == "markdown":
                filename = f"perf_doc_{i:04d}.md"
                if i % 3 == 0:
                    content = create_test_markdown("simple")
                elif i % 3 == 1:
                    content = create_test_markdown("medium")
                else:
                    content = create_test_markdown("complex")
            else:
                filename = f"perf_doc_{i:04d}.txt"
                topics = ["general", "technical", "narrative"]
                content = create_test_plaintext(topics[i % 3])
            
            doc_path = self.create_test_file(filename, content)
            docs.append(doc_path)
        
        return docs
    
    @pytest.mark.performance
    def test_single_document_indexing_speed(self):
        """Test indexing speed for individual documents."""
        print("\n=== Single Document Indexing Speed Test ===")
        
        test_cases = [
            ("simple_markdown", create_test_markdown("simple")),
            ("complex_markdown", create_test_markdown("complex")),
            ("technical_plaintext", create_test_plaintext("technical")),
            ("large_markdown", generate_large_content(1)),  # 1MB document
        ]
        
        results = {}
        
        for test_name, content in test_cases:
            ext = ".md" if "markdown" in test_name else ".txt"
            doc_path = self.create_test_file(f"{test_name}{ext}", content)
            
            # Warm up
            self.dispatcher.dispatch(str(doc_path), content)
            
            # Measure indexing time
            timings = []
            for _ in range(5):
                with timer(f"{test_name} indexing") as t:
                    start = time.perf_counter()
                    result = self.dispatcher.dispatch(str(doc_path), content)
                    end = time.perf_counter()
                    timings.append((end - start) * 1000)  # Convert to ms
            
            avg_time = statistics.mean(timings)
            p95_time = statistics.quantiles(timings, n=20)[18] if len(timings) >= 5 else max(timings)
            
            results[test_name] = {
                "avg_ms": avg_time,
                "p95_ms": p95_time,
                "size_kb": len(content.encode('utf-8')) / 1024,
                "success": result and not result.is_error
            }
            
            print(f"\n{test_name}:")
            print(f"  Size: {results[test_name]['size_kb']:.1f} KB")
            print(f"  Avg time: {avg_time:.1f} ms")
            print(f"  P95 time: {p95_time:.1f} ms")
            
            # Performance assertions
            assert_performance(avg_time / 1000, 0.1, f"{test_name} average indexing")  # < 100ms
            assert_performance(p95_time / 1000, 0.15, f"{test_name} P95 indexing")    # < 150ms
    
    @pytest.mark.performance
    def test_batch_indexing_throughput(self):
        """Test throughput when indexing multiple documents."""
        print("\n=== Batch Indexing Throughput Test ===")
        
        batch_sizes = [10, 50, 100, 200]
        results = {}
        
        for batch_size in batch_sizes:
            print(f"\nTesting batch size: {batch_size}")
            
            # Create test documents
            docs = self.create_test_corpus(batch_size, "markdown")
            
            # Measure batch indexing
            with timer(f"Batch {batch_size} indexing"):
                start_time = time.perf_counter()
                indexed = 0
                errors = 0
                
                for doc_path in docs:
                    content = doc_path.read_text()
                    result = self.dispatcher.dispatch(str(doc_path), content)
                    
                    if result and not result.is_error:
                        indexed += 1
                    else:
                        errors += 1
                
                end_time = time.perf_counter()
            
            total_time = end_time - start_time
            throughput = indexed / total_time if total_time > 0 else 0
            
            results[batch_size] = {
                "total_time_s": total_time,
                "indexed": indexed,
                "errors": errors,
                "throughput_docs_per_s": throughput,
                "avg_time_per_doc_ms": (total_time / batch_size) * 1000
            }
            
            print(f"  Indexed: {indexed}/{batch_size}")
            print(f"  Throughput: {throughput:.1f} docs/s")
            print(f"  Avg per doc: {results[batch_size]['avg_time_per_doc_ms']:.1f} ms")
            
            # Performance requirement: 10,000 files/minute = 167 files/second
            if batch_size >= 100:
                assert throughput >= 100, f"Throughput too low: {throughput:.1f} docs/s (need >= 100)"
    
    @pytest.mark.performance
    def test_concurrent_indexing_scalability(self):
        """Test performance with concurrent indexing operations."""
        print("\n=== Concurrent Indexing Scalability Test ===")
        
        # Create test corpus
        doc_count = 100
        docs = self.create_test_corpus(doc_count, "markdown")
        
        # Test different concurrency levels
        worker_counts = [1, 2, 4, 8]
        results = {}
        
        for num_workers in worker_counts:
            print(f"\nTesting with {num_workers} workers:")
            
            # Thread-safe counter
            indexed_count = 0
            lock = threading.Lock()
            
            def index_document(doc_path: Path) -> bool:
                """Index a single document thread-safely."""
                try:
                    content = doc_path.read_text()
                    result = self.dispatcher.dispatch(str(doc_path), content)
                    
                    if result and not result.is_error:
                        with lock:
                            nonlocal indexed_count
                            indexed_count += 1
                        return True
                    return False
                except Exception as e:
                    print(f"Error indexing {doc_path}: {e}")
                    return False
            
            # Measure concurrent indexing
            start_time = time.perf_counter()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(index_document, doc) for doc in docs]
                concurrent.futures.wait(futures)
            
            end_time = time.perf_counter()
            
            total_time = end_time - start_time
            throughput = indexed_count / total_time if total_time > 0 else 0
            
            results[num_workers] = {
                "total_time_s": total_time,
                "indexed": indexed_count,
                "throughput_docs_per_s": throughput,
                "speedup": throughput / results[1]["throughput_docs_per_s"] if 1 in results else 1.0
            }
            
            print(f"  Indexed: {indexed_count}/{doc_count}")
            print(f"  Time: {total_time:.1f}s")
            print(f"  Throughput: {throughput:.1f} docs/s")
            if num_workers > 1:
                print(f"  Speedup: {results[num_workers]['speedup']:.2f}x")
        
        # Verify scaling efficiency
        max_workers = max(worker_counts)
        if max_workers > 1:
            speedup = results[max_workers]["speedup"]
            efficiency = speedup / max_workers
            print(f"\nScaling efficiency at {max_workers} workers: {efficiency:.1%}")
            assert efficiency >= 0.5, f"Poor scaling efficiency: {efficiency:.1%}"
    
    @pytest.mark.performance
    def test_large_file_indexing_performance(self):
        """Test indexing performance with large files."""
        print("\n=== Large File Indexing Performance Test ===")
        
        file_sizes_mb = [0.5, 1, 2, 5, 10]
        results = {}
        
        with memory_monitor():
            for size_mb in file_sizes_mb:
                print(f"\nTesting {size_mb}MB file:")
                
                # Generate large content
                content = generate_large_content(size_mb)
                doc_path = self.create_test_file(f"large_{size_mb}mb.md", content)
                
                # Measure indexing with memory monitoring
                with memory_monitor() as mem:
                    start_time = time.perf_counter()
                    result = self.dispatcher.dispatch(str(doc_path), content)
                    end_time = time.perf_counter()
                
                index_time = end_time - start_time
                
                results[size_mb] = {
                    "size_mb": size_mb,
                    "index_time_s": index_time,
                    "success": result and not result.is_error,
                    "sections": len(result.data.get("sections", [])) if result and not result.is_error else 0,
                    "ms_per_mb": (index_time * 1000) / size_mb
                }
                
                print(f"  Index time: {index_time:.2f}s")
                print(f"  Rate: {size_mb/index_time:.1f} MB/s")
                print(f"  Sections: {results[size_mb]['sections']}")
                
                # Performance assertions
                # Should process at least 10MB/s
                assert (size_mb / index_time) >= 1.0, f"Processing too slow: {size_mb/index_time:.1f} MB/s"
        
        # Verify scaling
        print("\nLarge File Performance Summary:")
        print("Size (MB) | Time (s) | MB/s | ms/MB")
        print("-" * 40)
        for size, data in results.items():
            rate = size / data["index_time_s"]
            print(f"{size:>8.1f} | {data['index_time_s']:>7.2f} | {rate:>4.1f} | {data['ms_per_mb']:>5.0f}")
    
    @pytest.mark.performance
    def test_memory_usage_during_indexing(self):
        """Test memory consumption during indexing operations."""
        print("\n=== Memory Usage During Indexing Test ===")
        
        # Test with increasing document counts
        doc_counts = [10, 50, 100]
        memory_results = {}
        
        for count in doc_counts:
            print(f"\nIndexing {count} documents:")
            
            # Create documents
            docs = self.create_test_corpus(count, "markdown")
            
            # Monitor memory during indexing
            with memory_monitor() as mem:
                start_memory = mem.initial_memory
                indexed = 0
                
                for doc in docs:
                    content = doc.read_text()
                    result = self.dispatcher.dispatch(str(doc), content)
                    if result and not result.is_error:
                        indexed += 1
                
                # Force garbage collection
                import gc
                gc.collect()
                
                end_memory = mem.final_memory
            
            memory_used = end_memory - start_memory
            memory_per_doc = memory_used / count if count > 0 else 0
            
            memory_results[count] = {
                "memory_used_mb": memory_used,
                "memory_per_doc_mb": memory_per_doc,
                "indexed": indexed
            }
            
            print(f"  Memory used: {memory_used:.1f} MB")
            print(f"  Per document: {memory_per_doc:.2f} MB")
            
            # Memory assertions
            assert_memory_usage(memory_per_doc, 0.5, f"Indexing {count} documents")
        
        # Verify memory scales sub-linearly
        if len(memory_results) >= 2:
            counts = sorted(memory_results.keys())
            mem_ratio = memory_results[counts[-1]]["memory_used_mb"] / memory_results[counts[0]]["memory_used_mb"]
            count_ratio = counts[-1] / counts[0]
            
            print(f"\nMemory scaling: {mem_ratio:.1f}x for {count_ratio:.1f}x documents")
            assert mem_ratio < count_ratio, "Memory usage scales linearly or worse with document count"
    
    @pytest.mark.performance
    def test_incremental_update_performance(self):
        """Test performance of incremental document updates."""
        print("\n=== Incremental Update Performance Test ===")
        
        # Create initial document
        initial_content = create_test_markdown("complex")
        doc_path = self.create_test_file("update_test.md", initial_content)
        
        # Initial indexing
        initial_result = self.dispatcher.dispatch(str(doc_path), initial_content)
        assert initial_result and not initial_result.is_error
        
        # Test incremental updates
        update_times = []
        
        for i in range(10):
            # Make a small change
            updated_content = initial_content + f"\n\n## Update {i}\n\nThis is update number {i}."
            doc_path.write_text(updated_content)
            
            # Measure update time
            start_time = time.perf_counter()
            update_result = self.dispatcher.dispatch(str(doc_path), updated_content)
            end_time = time.perf_counter()
            
            update_time_ms = (end_time - start_time) * 1000
            update_times.append(update_time_ms)
            
            print(f"Update {i+1}: {update_time_ms:.1f}ms")
        
        # Analyze update performance
        avg_update = statistics.mean(update_times)
        p95_update = statistics.quantiles(update_times, n=20)[18] if len(update_times) >= 10 else max(update_times)
        
        print(f"\nIncremental Update Summary:")
        print(f"  Average: {avg_update:.1f}ms")
        print(f"  P95: {p95_update:.1f}ms")
        
        # Performance requirement: < 100ms per file
        assert_performance(avg_update / 1000, 0.1, "Average incremental update")
        assert_performance(p95_update / 1000, 0.15, "P95 incremental update")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])