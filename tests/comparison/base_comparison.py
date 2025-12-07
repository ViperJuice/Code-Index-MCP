"""Base comparison framework for Code Index MCP.

This module provides abstract base classes and utilities for implementing
standardized comparison operations with comprehensive metric collection,
timing, and parallel execution support.
"""

import abc
import asyncio
import threading
import time
import tracemalloc
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import psutil

# Type variable for generic comparison results
T = TypeVar("T")


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    execution_time: float = 0.0  # seconds
    cpu_usage: float = 0.0  # percentage
    memory_usage: float = 0.0  # MB
    peak_memory: float = 0.0  # MB
    thread_count: int = 0
    io_operations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            "execution_time_seconds": self.execution_time,
            "cpu_usage_percent": self.cpu_usage,
            "memory_usage_mb": self.memory_usage,
            "peak_memory_mb": self.peak_memory,
            "thread_count": self.thread_count,
            "io_operations": self.io_operations,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": (
                self.cache_hits / (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0
                else 0.0
            ),
        }


@dataclass
class TokenUsage:
    """Container for token usage metrics."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    prompt_cache_hits: int = 0
    prompt_cache_misses: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert token usage to dictionary format."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "prompt_cache_hits": self.prompt_cache_hits,
            "prompt_cache_misses": self.prompt_cache_misses,
            "cache_efficiency": (
                self.prompt_cache_hits / (self.prompt_cache_hits + self.prompt_cache_misses)
                if (self.prompt_cache_hits + self.prompt_cache_misses) > 0
                else 0.0
            ),
        }


@dataclass
class ComparisonResult:
    """Standardized result format for comparisons."""

    name: str
    success: bool
    metrics: PerformanceMetrics
    token_usage: Optional[TokenUsage] = None
    quality_scores: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "name": self.name,
            "success": self.success,
            "metrics": self.metrics.to_dict(),
            "token_usage": self.token_usage.to_dict() if self.token_usage else None,
            "quality_scores": self.quality_scores,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class MetricCollector:
    """Collects performance metrics during execution."""

    def __init__(self):
        self._start_time: Optional[float] = None
        self._start_memory: Optional[float] = None
        self._peak_memory: float = 0.0
        self._start_cpu: Optional[float] = None
        self._io_counter: int = 0
        self._process = psutil.Process()

    def start(self):
        """Start metric collection."""
        self._start_time = time.time()
        self._start_cpu = self._process.cpu_percent()

        # Start memory tracking
        tracemalloc.start()
        self._start_memory = self._get_memory_usage()

    def stop(self) -> PerformanceMetrics:
        """Stop collection and return metrics."""
        if self._start_time is None:
            raise RuntimeError("MetricCollector.start() must be called first")

        execution_time = time.time() - self._start_time
        cpu_usage = self._process.cpu_percent() - self._start_cpu

        current_memory = self._get_memory_usage()
        memory_usage = current_memory - self._start_memory

        # Get peak memory from tracemalloc
        _, peak = tracemalloc.get_traced_memory()
        self._peak_memory = peak / 1024 / 1024  # Convert to MB
        tracemalloc.stop()

        return PerformanceMetrics(
            execution_time=execution_time,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            peak_memory=self._peak_memory,
            thread_count=threading.active_count(),
            io_operations=self._io_counter,
        )

    def increment_io(self):
        """Increment IO operation counter."""
        self._io_counter += 1

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        return self._process.memory_info().rss / 1024 / 1024


def timing_decorator(func: Callable[..., T]) -> Callable[..., Tuple[T, float]]:
    """Decorator to measure function execution time."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Tuple[T, float]:
        start = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start
        return result, execution_time

    return wrapper


def async_timing_decorator(func: Callable[..., T]) -> Callable[..., Tuple[T, float]]:
    """Decorator to measure async function execution time."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Tuple[T, float]:
        start = time.time()
        result = await func(*args, **kwargs)
        execution_time = time.time() - start
        return result, execution_time

    return wrapper


@contextmanager
def metric_context():
    """Context manager for collecting metrics."""
    collector = MetricCollector()
    collector.start()
    try:
        yield collector
    finally:
        metrics = collector.stop()
        return metrics


class BaseComparison(abc.ABC):
    """Abstract base class for all comparison operations."""

    def __init__(self, name: str, parallel: bool = False, max_workers: Optional[int] = None):
        """Initialize comparison.

        Args:
            name: Name of the comparison
            parallel: Whether to support parallel execution
            max_workers: Maximum number of parallel workers
        """
        self.name = name
        self.parallel = parallel
        self.max_workers = max_workers or psutil.cpu_count()
        self._cache: Dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    @abc.abstractmethod
    def setup(self, **kwargs) -> None:
        """Setup comparison environment.

        This method should prepare any necessary resources,
        initialize connections, load models, etc.
        """
        pass

    @abc.abstractmethod
    def teardown(self) -> None:
        """Cleanup comparison environment.

        This method should release resources, close connections,
        save results, etc.
        """
        pass

    @abc.abstractmethod
    def run_comparison(self, input_data: Any) -> ComparisonResult:
        """Run the actual comparison.

        Args:
            input_data: Input data for the comparison

        Returns:
            ComparisonResult with metrics and scores
        """
        pass

    @abc.abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data.

        Args:
            input_data: Input data to validate

        Returns:
            True if input is valid, False otherwise
        """
        pass

    @abc.abstractmethod
    def calculate_quality_scores(self, result: Any, expected: Any) -> Dict[str, float]:
        """Calculate quality scores for the result.

        Args:
            result: Actual result
            expected: Expected result

        Returns:
            Dictionary of quality metrics
        """
        pass

    def execute(self, input_data: Any, expected: Any = None) -> ComparisonResult:
        """Execute comparison with full metric collection.

        Args:
            input_data: Input data for comparison
            expected: Expected result for quality scoring

        Returns:
            Complete comparison result with metrics
        """
        # Validate input
        if not self.validate_input(input_data):
            return ComparisonResult(
                name=self.name,
                success=False,
                metrics=PerformanceMetrics(),
                errors=["Invalid input data"],
            )

        # Collect metrics
        collector = MetricCollector()
        collector.start()

        try:
            # Run comparison
            result = self.run_comparison(input_data)

            # Calculate quality scores if expected result provided
            if expected is not None:
                result.quality_scores = self.calculate_quality_scores(
                    result.metadata.get("output"), expected
                )

            # Update cache metrics
            result.metrics.cache_hits = self._cache_hits
            result.metrics.cache_misses = self._cache_misses

            return result

        except Exception as e:
            return ComparisonResult(
                name=self.name,
                success=False,
                metrics=collector.stop(),
                errors=[str(e), traceback.format_exc()],
            )
        finally:
            result.metrics = collector.stop()

    def execute_batch(
        self, inputs: List[Any], expected: Optional[List[Any]] = None
    ) -> List[ComparisonResult]:
        """Execute comparison on multiple inputs.

        Args:
            inputs: List of inputs
            expected: Optional list of expected results

        Returns:
            List of comparison results
        """
        if expected is None:
            expected = [None] * len(inputs)

        if self.parallel:
            return self._execute_parallel(inputs, expected)
        else:
            return self._execute_sequential(inputs, expected)

    def _execute_sequential(self, inputs: List[Any], expected: List[Any]) -> List[ComparisonResult]:
        """Execute comparisons sequentially."""
        results = []
        for inp, exp in zip(inputs, expected):
            results.append(self.execute(inp, exp))
        return results

    def _execute_parallel(self, inputs: List[Any], expected: List[Any]) -> List[ComparisonResult]:
        """Execute comparisons in parallel."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for inp, exp in zip(inputs, expected):
                future = executor.submit(self.execute, inp, exp)
                futures.append(future)

            results = [future.result() for future in futures]

        return results

    def cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]
        else:
            self._cache_misses += 1
            return None

    def cache_set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self._cache[key] = value

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    @staticmethod
    def aggregate_results(results: List[ComparisonResult]) -> Dict[str, Any]:
        """Aggregate multiple comparison results.

        Args:
            results: List of comparison results

        Returns:
            Aggregated statistics
        """
        if not results:
            return {}

        total_results = len(results)
        successful_results = sum(1 for r in results if r.success)

        # Aggregate metrics
        total_time = sum(r.metrics.execution_time for r in results)
        avg_time = total_time / total_results

        avg_memory = sum(r.metrics.memory_usage for r in results) / total_results
        peak_memory = max(r.metrics.peak_memory for r in results)

        # Aggregate quality scores
        all_scores = {}
        for result in results:
            for metric, score in result.quality_scores.items():
                if metric not in all_scores:
                    all_scores[metric] = []
                all_scores[metric].append(score)

        avg_scores = {metric: sum(scores) / len(scores) for metric, scores in all_scores.items()}

        return {
            "total_comparisons": total_results,
            "successful_comparisons": successful_results,
            "success_rate": successful_results / total_results,
            "total_execution_time": total_time,
            "average_execution_time": avg_time,
            "average_memory_usage": avg_memory,
            "peak_memory_usage": peak_memory,
            "average_quality_scores": avg_scores,
            "errors": [error for r in results for error in r.errors],
            "warnings": [warning for r in results for warning in r.warnings],
        }


class AsyncBaseComparison(BaseComparison):
    """Abstract base class for async comparison operations."""

    @abc.abstractmethod
    async def setup_async(self, **kwargs) -> None:
        """Async setup for comparison environment."""
        pass

    @abc.abstractmethod
    async def teardown_async(self) -> None:
        """Async cleanup for comparison environment."""
        pass

    @abc.abstractmethod
    async def run_comparison_async(self, input_data: Any) -> ComparisonResult:
        """Run the actual comparison asynchronously."""
        pass

    async def execute_async(self, input_data: Any, expected: Any = None) -> ComparisonResult:
        """Execute comparison asynchronously with full metric collection."""
        # Validate input
        if not self.validate_input(input_data):
            return ComparisonResult(
                name=self.name,
                success=False,
                metrics=PerformanceMetrics(),
                errors=["Invalid input data"],
            )

        # Collect metrics
        collector = MetricCollector()
        collector.start()

        try:
            # Run async comparison
            result = await self.run_comparison_async(input_data)

            # Calculate quality scores if expected result provided
            if expected is not None:
                result.quality_scores = self.calculate_quality_scores(
                    result.metadata.get("output"), expected
                )

            # Update cache metrics
            result.metrics.cache_hits = self._cache_hits
            result.metrics.cache_misses = self._cache_misses

            return result

        except Exception as e:
            return ComparisonResult(
                name=self.name,
                success=False,
                metrics=collector.stop(),
                errors=[str(e), traceback.format_exc()],
            )
        finally:
            result.metrics = collector.stop()

    async def execute_batch_async(
        self, inputs: List[Any], expected: Optional[List[Any]] = None
    ) -> List[ComparisonResult]:
        """Execute comparison on multiple inputs asynchronously."""
        if expected is None:
            expected = [None] * len(inputs)

        tasks = []
        for inp, exp in zip(inputs, expected):
            task = self.execute_async(inp, exp)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return results
