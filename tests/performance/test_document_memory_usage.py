#!/usr/bin/env python3
"""Performance tests for memory usage and resource management."""

import concurrent.futures
import gc
import statistics
import time
import tracemalloc
import weakref
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import pytest

from tests.base_test import BaseDocumentTest
from tests.test_utils import (
    assert_memory_usage,
    create_test_markdown,
    create_test_plaintext,
    generate_large_content,
    memory_monitor,
)


class MemoryProfiler:
    """Advanced memory profiling utility."""

    def __init__(self):
        self.process = psutil.Process()
        self.snapshots = []
        self.tracemalloc_enabled = False

    def start(self):
        """Start memory profiling."""
        gc.collect()
        tracemalloc.start()
        self.tracemalloc_enabled = True

        self.initial_memory = self._get_memory_info()
        self.initial_snapshot = tracemalloc.take_snapshot()

    def checkpoint(self, label: str):
        """Take a memory checkpoint."""
        gc.collect()

        memory_info = self._get_memory_info()
        snapshot = tracemalloc.take_snapshot() if self.tracemalloc_enabled else None

        checkpoint_data = {
            "label": label,
            "timestamp": time.time(),
            "memory": memory_info,
            "delta": {
                "rss": memory_info["rss"] - self.initial_memory["rss"],
                "vms": memory_info["vms"] - self.initial_memory["vms"],
            },
        }

        if snapshot and self.initial_snapshot:
            stats = snapshot.compare_to(self.initial_snapshot, "lineno")
            top_stats = sorted(stats, key=lambda x: x.size_diff, reverse=True)[:10]
            checkpoint_data["top_allocations"] = [
                {
                    "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                    "size_diff": stat.size_diff / 1024 / 1024,  # MB
                    "count_diff": stat.count_diff,
                }
                for stat in top_stats
            ]

        self.snapshots.append(checkpoint_data)
        return checkpoint_data

    def stop(self):
        """Stop profiling and return summary."""
        final_checkpoint = self.checkpoint("final")

        if self.tracemalloc_enabled:
            tracemalloc.stop()

        return self._analyze_results()

    def _get_memory_info(self) -> Dict[str, float]:
        """Get current memory usage."""
        mem_info = self.process.memory_info()
        return {
            "rss": mem_info.rss / 1024 / 1024,  # MB
            "vms": mem_info.vms / 1024 / 1024,  # MB
            "percent": self.process.memory_percent(),
        }

    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze profiling results."""
        if not self.snapshots:
            return {}

        rss_values = [s["memory"]["rss"] for s in self.snapshots]
        delta_values = [s["delta"]["rss"] for s in self.snapshots]

        return {
            "initial_mb": self.initial_memory["rss"],
            "final_mb": self.snapshots[-1]["memory"]["rss"],
            "peak_mb": max(rss_values),
            "total_increase_mb": self.snapshots[-1]["delta"]["rss"],
            "checkpoints": self.snapshots,
            "summary": {
                "avg_memory_mb": statistics.mean(rss_values),
                "max_delta_mb": max(delta_values),
                "checkpoint_count": len(self.snapshots),
            },
        }


class TestDocumentMemoryUsage(BaseDocumentTest):
    """Test memory usage patterns and leak detection."""

    @pytest.mark.performance
    def test_memory_profile_document_processing(self):
        """Profile memory usage during document processing."""
        print("\n=== Memory Profile: Document Processing ===")

        profiler = MemoryProfiler()
        profiler.start()

        # Test with different document sizes
        doc_sizes = [
            ("small", 0.1),  # 100KB
            ("medium", 0.5),  # 500KB
            ("large", 1.0),  # 1MB
            ("xlarge", 5.0),  # 5MB
        ]

        results = {}

        for size_name, size_mb in doc_sizes:
            print(f"\nProcessing {size_name} document ({size_mb}MB):")

            profiler.checkpoint(f"before_{size_name}")

            # Create and process document
            content = generate_large_content(size_mb)
            doc_path = self.create_test_file(f"memory_test_{size_name}.md", content)

            # Process document
            result = self.dispatcher.dispatch(str(doc_path), content)

            profiler.checkpoint(f"after_{size_name}")

            # Get memory stats
            before = next(s for s in profiler.snapshots if s["label"] == f"before_{size_name}")
            after = next(s for s in profiler.snapshots if s["label"] == f"after_{size_name}")

            memory_used = after["memory"]["rss"] - before["memory"]["rss"]
            memory_ratio = memory_used / size_mb if size_mb > 0 else 0

            results[size_name] = {
                "size_mb": size_mb,
                "memory_used_mb": memory_used,
                "memory_ratio": memory_ratio,
                "success": result and not result.is_error,
            }

            print(f"  Memory used: {memory_used:.2f}MB")
            print(f"  Memory/Size ratio: {memory_ratio:.2f}")

            # Clean up
            doc_path.unlink()
            del content
            gc.collect()

            profiler.checkpoint(f"cleanup_{size_name}")

        profile_summary = profiler.stop()

        # Display summary
        print("\nMemory Usage Summary:")
        print("Size   | Doc (MB) | Mem (MB) | Ratio")
        print("-" * 40)
        for name, data in results.items():
            print(
                f"{name:<6} | {data['size_mb']:>7.1f} | {data['memory_used_mb']:>7.2f} | {data['memory_ratio']:>5.2f}"
            )

        print(f"\nPeak memory: {profile_summary['peak_mb']:.1f}MB")
        print(f"Total increase: {profile_summary['total_increase_mb']:.1f}MB")

        # Memory assertions
        for name, data in results.items():
            assert_memory_usage(data["memory_ratio"], 2.0, f"Processing {name} document")

    @pytest.mark.performance
    def test_memory_leak_detection(self):
        """Test for memory leaks in repeated operations."""
        print("\n=== Memory Leak Detection Test ===")

        profiler = MemoryProfiler()
        profiler.start()

        # Create test document
        content = create_test_markdown("complex")
        doc_path = self.create_test_file("leak_test.md", content)

        # Perform repeated operations
        num_iterations = 20
        iteration_memories = []

        print(f"Running {num_iterations} iterations...")

        for i in range(num_iterations):
            profiler.checkpoint(f"iteration_{i}_start")

            # Process document
            result = self.dispatcher.dispatch(str(doc_path), content)

            # Simulate some operations
            if result and not result.is_error:
                # Access result data
                sections = result.data.get("sections", [])
                symbols = result.data.get("symbols", [])

            # Force cleanup
            del result
            gc.collect()

            profiler.checkpoint(f"iteration_{i}_end")

            # Record memory after cleanup
            end_checkpoint = profiler.snapshots[-1]
            iteration_memories.append(end_checkpoint["delta"]["rss"])

            if (i + 1) % 5 == 0:
                print(f"  After {i + 1} iterations: {end_checkpoint['delta']['rss']:.1f}MB")

        profile_summary = profiler.stop()

        # Analyze memory growth
        print("\nMemory Growth Analysis:")

        # Split into early and late iterations
        early_iterations = iteration_memories[:5]
        late_iterations = iteration_memories[-5:]

        early_avg = statistics.mean(early_iterations)
        late_avg = statistics.mean(late_iterations)

        growth = late_avg - early_avg
        growth_percent = (growth / early_avg * 100) if early_avg > 0 else 0

        print(f"  Early average: {early_avg:.2f}MB")
        print(f"  Late average: {late_avg:.2f}MB")
        print(f"  Growth: {growth:.2f}MB ({growth_percent:.1f}%)")

        # Check for memory leak
        # Allow small growth due to caching, but flag significant increases
        assert (
            growth < 5.0
        ), f"Potential memory leak: {growth:.2f}MB growth over {num_iterations} iterations"
        assert growth_percent < 20, f"Memory grew by {growth_percent:.1f}% - potential leak"

    @pytest.mark.performance
    def test_resource_cleanup_effectiveness(self):
        """Test effectiveness of resource cleanup and garbage collection."""
        print("\n=== Resource Cleanup Effectiveness Test ===")

        profiler = MemoryProfiler()
        profiler.start()

        # Create weak references to track object lifecycle
        weak_refs = []

        print("Creating and processing documents...")

        # Phase 1: Create many documents
        profiler.checkpoint("phase1_start")

        documents = []
        for i in range(50):
            content = create_test_markdown("medium" if i % 2 == 0 else "simple")
            doc_path = self.create_test_file(f"cleanup_test_{i:03d}.md", content)

            result = self.dispatcher.dispatch(str(doc_path), content)

            # Keep references
            documents.append({"path": doc_path, "content": content, "result": result})

            # Create weak reference to result
            if result:
                weak_refs.append(weakref.ref(result))

        profiler.checkpoint("phase1_end")
        phase1_memory = profiler.snapshots[-1]["memory"]["rss"]

        print(f"After creating 50 documents: {phase1_memory:.1f}MB")

        # Phase 2: Clear references and trigger cleanup
        print("\nClearing references and forcing cleanup...")

        # Clear strong references
        documents.clear()

        # Force garbage collection
        gc.collect()
        time.sleep(0.1)  # Allow cleanup to complete
        gc.collect()

        profiler.checkpoint("phase2_cleanup")
        phase2_memory = profiler.snapshots[-1]["memory"]["rss"]

        # Check weak references
        alive_refs = sum(1 for ref in weak_refs if ref() is not None)

        print(f"After cleanup: {phase2_memory:.1f}MB")
        print(f"Memory freed: {phase1_memory - phase2_memory:.1f}MB")
        print(f"Alive weak references: {alive_refs}/{len(weak_refs)}")

        # Phase 3: Process more documents to verify memory is reusable
        print("\nProcessing additional documents...")

        profiler.checkpoint("phase3_start")

        for i in range(20):
            content = create_test_plaintext("general")
            doc_path = self.create_test_file(f"reuse_test_{i:03d}.txt", content)

            result = self.dispatcher.dispatch(str(doc_path), content)

            # Immediately cleanup
            del result
            doc_path.unlink()

        gc.collect()

        profiler.checkpoint("phase3_end")
        phase3_memory = profiler.snapshots[-1]["memory"]["rss"]

        print(f"After processing 20 more documents: {phase3_memory:.1f}MB")

        profile_summary = profiler.stop()

        # Verify cleanup effectiveness
        cleanup_ratio = (phase1_memory - phase2_memory) / (
            phase1_memory - profiler.initial_memory["rss"]
        )
        print(f"\nCleanup effectiveness: {cleanup_ratio:.1%}")

        # Assertions
        assert cleanup_ratio > 0.7, f"Poor cleanup effectiveness: {cleanup_ratio:.1%}"
        assert alive_refs == 0, f"Memory leak: {alive_refs} objects still referenced"
        assert phase3_memory < phase1_memory, "Memory not properly reclaimed"

    @pytest.mark.performance
    def test_garbage_collection_impact(self):
        """Test impact of garbage collection on performance."""
        print("\n=== Garbage Collection Impact Test ===")

        # Disable automatic GC for controlled testing
        gc.disable()

        try:
            profiler = MemoryProfiler()
            profiler.start()

            # Test with GC disabled
            print("Testing with GC disabled:")

            profiler.checkpoint("gc_disabled_start")

            gc_disabled_times = []
            for i in range(10):
                content = generate_large_content(0.5)  # 500KB
                doc_path = self.create_test_file(f"gc_test_disabled_{i}.md", content)

                start_time = time.perf_counter()
                result = self.dispatcher.dispatch(str(doc_path), content)
                end_time = time.perf_counter()

                gc_disabled_times.append((end_time - start_time) * 1000)

                if i == 4:
                    profiler.checkpoint("gc_disabled_mid")

            profiler.checkpoint("gc_disabled_end")

            gc_disabled_avg = statistics.mean(gc_disabled_times)
            gc_disabled_memory = profiler.snapshots[-1]["delta"]["rss"]

            print(f"  Avg processing time: {gc_disabled_avg:.1f}ms")
            print(f"  Memory increase: {gc_disabled_memory:.1f}MB")

            # Enable GC and test again
            gc.enable()
            gc.set_threshold(700, 10, 10)  # Default thresholds

            print("\nTesting with GC enabled:")

            profiler.checkpoint("gc_enabled_start")

            gc_enabled_times = []
            gc_count_before = gc.get_count()

            for i in range(10):
                content = generate_large_content(0.5)  # 500KB
                doc_path = self.create_test_file(f"gc_test_enabled_{i}.md", content)

                start_time = time.perf_counter()
                result = self.dispatcher.dispatch(str(doc_path), content)
                end_time = time.perf_counter()

                gc_enabled_times.append((end_time - start_time) * 1000)

                if i == 4:
                    profiler.checkpoint("gc_enabled_mid")

            profiler.checkpoint("gc_enabled_end")

            gc_count_after = gc.get_count()
            gc_collections = sum(gc_count_after[i] - gc_count_before[i] for i in range(3))

            gc_enabled_avg = statistics.mean(gc_enabled_times)
            gc_enabled_memory = profiler.snapshots[-1]["delta"]["rss"] - gc_disabled_memory

            print(f"  Avg processing time: {gc_enabled_avg:.1f}ms")
            print(f"  Memory increase: {gc_enabled_memory:.1f}MB")
            print(f"  GC collections: {gc_collections}")

            # Compare impact
            time_overhead = ((gc_enabled_avg - gc_disabled_avg) / gc_disabled_avg) * 100
            memory_saved = gc_disabled_memory - gc_enabled_memory

            print(f"\nGC Impact:")
            print(f"  Time overhead: {time_overhead:.1f}%")
            print(f"  Memory saved: {memory_saved:.1f}MB")

            profile_summary = profiler.stop()

            # GC should have acceptable overhead
            assert time_overhead < 10, f"GC overhead too high: {time_overhead:.1f}%"
            assert memory_saved > 0, "GC did not reduce memory usage"

        finally:
            # Re-enable GC
            gc.enable()

    @pytest.mark.performance
    def test_memory_usage_under_concurrent_load(self):
        """Test memory usage with concurrent document processing."""
        print("\n=== Memory Usage Under Concurrent Load ===")

        profiler = MemoryProfiler()
        profiler.start()

        # Create test documents
        num_docs = 50
        docs = []

        for i in range(num_docs):
            if i % 2 == 0:
                content = create_test_markdown("medium")
                filename = f"concurrent_{i:03d}.md"
            else:
                content = create_test_plaintext("technical")
                filename = f"concurrent_{i:03d}.txt"

            doc_path = self.create_test_file(filename, content)
            docs.append((doc_path, content))

        profiler.checkpoint("documents_created")

        # Test different concurrency levels
        worker_counts = [1, 4, 8]
        results = {}

        for num_workers in worker_counts:
            print(f"\nTesting with {num_workers} workers:")

            profiler.checkpoint(f"workers_{num_workers}_start")

            def process_document(doc_tuple):
                """Process a single document."""
                doc_path, content = doc_tuple
                try:
                    return self.dispatcher.dispatch(str(doc_path), content)
                except Exception as e:
                    print(f"Error processing {doc_path}: {e}")
                    return None

            # Process documents concurrently
            start_time = time.perf_counter()

            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(process_document, doc) for doc in docs]
                results_list = [f.result() for f in concurrent.futures.as_completed(futures)]

            end_time = time.perf_counter()

            profiler.checkpoint(f"workers_{num_workers}_end")

            # Force cleanup
            gc.collect()

            profiler.checkpoint(f"workers_{num_workers}_cleanup")

            # Get memory stats
            start_checkpoint = next(
                s for s in profiler.snapshots if s["label"] == f"workers_{num_workers}_start"
            )
            end_checkpoint = next(
                s for s in profiler.snapshots if s["label"] == f"workers_{num_workers}_end"
            )
            cleanup_checkpoint = next(
                s for s in profiler.snapshots if s["label"] == f"workers_{num_workers}_cleanup"
            )

            memory_used = end_checkpoint["memory"]["rss"] - start_checkpoint["memory"]["rss"]
            memory_after_cleanup = (
                cleanup_checkpoint["memory"]["rss"] - start_checkpoint["memory"]["rss"]
            )
            processing_time = end_time - start_time

            results[num_workers] = {
                "memory_peak_mb": memory_used,
                "memory_after_cleanup_mb": memory_after_cleanup,
                "time_s": processing_time,
                "memory_per_worker": memory_used / num_workers,
            }

            print(f"  Peak memory: {memory_used:.1f}MB")
            print(f"  After cleanup: {memory_after_cleanup:.1f}MB")
            print(f"  Time: {processing_time:.1f}s")
            print(f"  Memory per worker: {memory_used/num_workers:.1f}MB")

        profile_summary = profiler.stop()

        # Compare concurrent memory usage
        print("\nConcurrent Processing Memory Scaling:")
        print("Workers | Peak (MB) | Cleanup (MB) | MB/Worker")
        print("-" * 45)

        for workers, data in results.items():
            print(
                f"{workers:>7} | {data['memory_peak_mb']:>8.1f} | {data['memory_after_cleanup_mb']:>11.1f} | "
                f"{data['memory_per_worker']:>9.1f}"
            )

        # Verify memory scaling
        if len(results) >= 2:
            worker_list = sorted(results.keys())

            # Memory should not scale linearly with workers
            mem_ratio = (
                results[worker_list[-1]]["memory_peak_mb"]
                / results[worker_list[0]]["memory_peak_mb"]
            )
            worker_ratio = worker_list[-1] / worker_list[0]

            print(f"\nMemory scaling: {mem_ratio:.1f}x for {worker_ratio:.1f}x workers")
            assert mem_ratio < worker_ratio * 0.7, f"Memory scales too steeply: {mem_ratio:.1f}x"

    @pytest.mark.performance
    def test_memory_pressure_handling(self):
        """Test behavior under memory pressure conditions."""
        print("\n=== Memory Pressure Handling Test ===")

        profiler = MemoryProfiler()
        profiler.start()

        # Get initial memory state
        initial_available = psutil.virtual_memory().available / 1024 / 1024  # MB
        print(f"Initial available memory: {initial_available:.1f}MB")

        # Create progressively larger documents
        documents_processed = 0
        max_documents = 20
        base_size_mb = 2.0

        try:
            for i in range(max_documents):
                # Increase size progressively
                size_mb = base_size_mb * (1 + i * 0.5)

                print(f"\nProcessing document {i+1} ({size_mb:.1f}MB):")

                profiler.checkpoint(f"doc_{i}_start")

                # Check available memory
                available_mb = psutil.virtual_memory().available / 1024 / 1024
                print(f"  Available memory: {available_mb:.1f}MB")

                # Simulate memory pressure - skip if low on memory
                if available_mb < size_mb * 3:  # Need 3x document size
                    print("  Skipping due to memory pressure")
                    break

                # Create and process document
                content = generate_large_content(size_mb)
                doc_path = self.create_test_file(f"pressure_test_{i:02d}.md", content)

                try:
                    result = self.dispatcher.dispatch(str(doc_path), content)
                    documents_processed += 1

                    profiler.checkpoint(f"doc_{i}_end")

                    # Clean up immediately
                    del content
                    del result
                    doc_path.unlink()
                    gc.collect()

                    profiler.checkpoint(f"doc_{i}_cleanup")

                    # Check memory recovery
                    cleanup_checkpoint = profiler.snapshots[-1]
                    if cleanup_checkpoint["memory"]["percent"] > 80:
                        print(
                            f"  High memory usage: {cleanup_checkpoint['memory']['percent']:.1f}%"
                        )
                        print("  Triggering aggressive cleanup...")

                        # Aggressive cleanup
                        gc.collect(2)  # Full collection
                        time.sleep(0.1)

                except MemoryError:
                    print("  MemoryError - stopping test")
                    break
                except Exception as e:
                    print(f"  Error: {e}")
                    break

        finally:
            profile_summary = profiler.stop()

        print(f"\nProcessed {documents_processed} documents before stopping")
        print(f"Peak memory: {profile_summary['peak_mb']:.1f}MB")
        print(f"Final memory: {profile_summary['final_mb']:.1f}MB")

        # Should handle at least some documents gracefully
        assert documents_processed >= 3, "Failed to process minimum documents under memory pressure"

        # Memory should be recoverable
        memory_recovered = profile_summary["peak_mb"] - profile_summary["final_mb"]
        recovery_ratio = memory_recovered / (
            profile_summary["peak_mb"] - profile_summary["initial_mb"]
        )

        print(f"Memory recovery: {recovery_ratio:.1%}")
        assert recovery_ratio > 0.5, f"Poor memory recovery: {recovery_ratio:.1%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
