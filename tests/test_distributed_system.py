#!/usr/bin/env python3
"""
Comprehensive test suite for the distributed processing system.
Tests master-worker communication, fault tolerance, and performance scaling.
"""

import asyncio
import tempfile
import shutil
import os
import time
import json
import threading
import pytest
import redis
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from mcp_server.distributed import (
    IndexingCoordinator,
    IndexingWorker,
    IndexingJob,
    JobResult,
    WorkerStatus,
    DistributedConfig,
    JobStatus,
    JobPriority,
    WorkerState
)

class TestDistributedSystem:
    """Test suite for distributed processing system."""
    
    @pytest.fixture(autouse=True)
    def setup_redis(self):
        """Setup Redis connection for testing."""
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            self.redis_client.ping()
            
            # Clean up any existing test data
            self.redis_client.flushdb()
            
        except redis.ConnectionError:
            pytest.skip("Redis not available for testing")
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return DistributedConfig(
            redis_url="redis://localhost:6379",
            job_queue="test_indexing_jobs",
            result_queue="test_indexing_results",
            worker_status_key="test_worker_status",
            health_check_interval=1,
            heartbeat_interval=1,
            batch_size=5,
            max_workers=3
        )
    
    @pytest.fixture
    def test_repo(self):
        """Create a temporary test repository with various files."""
        temp_dir = tempfile.mkdtemp()
        
        # Create test files
        test_files = {
            'main.py': '''
def hello_world():
    """Print hello world."""
    print("Hello, World!")

class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
''',
            'utils.js': '''
function factorial(n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

class MathUtils {
    static isPrime(n) {
        if (n < 2) return false;
        for (let i = 2; i < n; i++) {
            if (n % i === 0) return false;
        }
        return true;
    }
}
''',
            'data.json': '{"test": "data"}',
            'README.md': '# Test Repository\n\nThis is a test repository.',
            'lib/helper.py': '''
def parse_config(filename):
    """Parse configuration file."""
    with open(filename) as f:
        return json.load(f)

def validate_input(data):
    """Validate input data."""
    return isinstance(data, dict)
''',
            'src/component.rs': '''
pub struct Component {
    name: String,
    value: i32,
}

impl Component {
    pub fn new(name: String, value: i32) -> Self {
        Component { name, value }
    }
    
    pub fn get_value(&self) -> i32 {
        self.value
    }
}
'''
        }
        
        # Create directory structure and files
        for file_path, content in test_files.items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(content)
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_coordinator_initialization(self, config):
        """Test coordinator initialization and configuration."""
        coordinator = IndexingCoordinator(config)
        
        assert coordinator.config == config
        assert coordinator.active_jobs == {}
        assert coordinator.completed_jobs == {}
        assert coordinator.failed_jobs == {}
        assert coordinator.worker_statuses == {}
        
    def test_worker_initialization(self, config):
        """Test worker initialization and configuration."""
        worker = IndexingWorker("test-worker-1", config)
        
        assert worker.worker_id == "test-worker-1"
        assert worker.config == config
        assert worker.status.worker_id == "test-worker-1"
        assert worker.status.state == WorkerState.IDLE
        assert not worker.is_running
    
    def test_job_creation_and_queuing(self, config, test_repo):
        """Test job creation and Redis queuing."""
        coordinator = IndexingCoordinator(config)
        
        jobs = coordinator.create_indexing_jobs(test_repo, JobPriority.HIGH)
        
        assert len(jobs) > 0
        assert all(job.priority == JobPriority.HIGH for job in jobs)
        assert all(job.repo_path == test_repo for job in jobs)
        
        # Check if jobs were queued in Redis
        high_priority_queue = f"{config.job_queue}:high"
        queue_length = self.redis_client.llen(high_priority_queue)
        assert queue_length == len(jobs)
    
    def test_file_discovery_and_filtering(self, config, test_repo):
        """Test file discovery and filtering logic."""
        coordinator = IndexingCoordinator(config)
        
        # Get discovered files
        files = coordinator._discover_files(test_repo)
        
        # Should find .py, .js, .rs files but not .json, .md
        expected_extensions = {'.py', '.js', '.rs'}
        found_extensions = {os.path.splitext(f)[1] for f in files}
        
        assert expected_extensions.issubset(found_extensions)
        assert '.json' not in found_extensions
        assert '.md' not in found_extensions
        
        # Should find all test files
        assert any('main.py' in f for f in files)
        assert any('utils.js' in f for f in files)
        assert any('component.rs' in f for f in files)
        assert any('helper.py' in f for f in files)
    
    def test_worker_job_processing(self, config, test_repo):
        """Test worker job processing functionality."""
        coordinator = IndexingCoordinator(config)
        worker = IndexingWorker("test-worker-1", config)
        
        # Create and queue jobs
        jobs = coordinator.create_indexing_jobs(test_repo, JobPriority.NORMAL)
        
        # Process one job manually
        job = worker._get_next_job()
        assert job is not None
        assert job.repo_path == test_repo
        
        # Mock the processing to avoid complex setup
        with patch.object(worker, '_process_single_file') as mock_process:
            mock_process.return_value = [
                {'name': 'test_function', 'type': 'function', 'line': 1}
            ]
            
            worker._process_job_with_monitoring(job)
            
            # Check that files were processed
            assert mock_process.call_count == len(job.files)
    
    def test_priority_queue_handling(self, config, test_repo):
        """Test priority queue handling and job ordering."""
        coordinator = IndexingCoordinator(config)
        worker = IndexingWorker("test-worker-1", config)
        
        # Create jobs with different priorities
        high_jobs = coordinator.create_indexing_jobs(test_repo, JobPriority.HIGH)
        normal_jobs = coordinator.create_indexing_jobs(test_repo, JobPriority.NORMAL)
        low_jobs = coordinator.create_indexing_jobs(test_repo, JobPriority.LOW)
        
        # Worker should get high priority job first
        job1 = worker._get_next_job()
        assert job1.priority == JobPriority.HIGH
        
        # Then normal priority
        job2 = worker._get_next_job()
        # Should still be high if there are more high priority jobs
        # or normal if all high priority jobs are taken
        assert job2.priority.value >= JobPriority.NORMAL.value
    
    def test_worker_health_monitoring(self, config):
        """Test worker health monitoring and status updates."""
        worker = IndexingWorker("test-worker-1", config)
        
        # Update status
        worker._update_status()
        
        # Check Redis for status
        status_key = f"{config.worker_status_key}:test-worker-1"
        status_data = self.redis_client.get(status_key)
        
        assert status_data is not None
        status = json.loads(status_data)
        assert status['worker_id'] == "test-worker-1"
        assert 'cpu_usage' in status
        assert 'memory_usage' in status
        assert 'last_heartbeat' in status
    
    def test_job_retry_mechanism(self, config):
        """Test job retry mechanism for failed jobs."""
        coordinator = IndexingCoordinator(config)
        
        # Create a failed job
        job = IndexingJob(
            repo_path="/test/path",
            files=["test.py"],
            priority=JobPriority.NORMAL,
            status=JobStatus.FAILED,
            retry_count=1,
            max_retries=3
        )
        
        coordinator.failed_jobs[job.job_id] = job
        
        # Trigger retry
        coordinator._retry_failed_jobs()
        
        # Job should be moved back to active and queued for retry
        assert job.job_id in coordinator.active_jobs
        assert job.job_id not in coordinator.failed_jobs
        assert job.retry_count == 2
        assert job.status == JobStatus.RETRYING
    
    def test_result_aggregation(self, config):
        """Test result aggregation and completion tracking."""
        coordinator = IndexingCoordinator(config)
        
        # Simulate job completion
        job = IndexingJob(
            repo_path="/test/path",
            files=["test.py"],
            priority=JobPriority.NORMAL
        )
        coordinator.active_jobs[job.job_id] = job
        
        result = JobResult(
            job_id=job.job_id,
            worker_id="test-worker-1",
            status=JobStatus.COMPLETED,
            files_processed=1,
            symbols_found=5,
            processing_time=1.5
        )
        
        # Handle completion
        coordinator._handle_job_completion(result)
        
        # Check tracking
        assert job.job_id in coordinator.completed_jobs
        assert job.job_id not in coordinator.active_jobs
        assert coordinator.total_files_processed == 1
        assert coordinator.total_symbols_found == 5
    
    def test_coordinator_monitoring_loop(self, config):
        """Test coordinator background monitoring functionality."""
        coordinator = IndexingCoordinator(config)
        
        # Start monitoring
        coordinator.start_monitoring()
        assert coordinator._monitoring_active
        assert coordinator._monitor_thread is not None
        assert coordinator._monitor_thread.is_alive()
        
        # Stop monitoring
        coordinator.stop_monitoring()
        assert not coordinator._monitoring_active
    
    def test_worker_graceful_shutdown(self, config):
        """Test worker graceful shutdown handling."""
        worker = IndexingWorker("test-worker-1", config)
        
        # Start worker
        worker.start_processing()
        assert worker.is_running
        
        # Give it a moment to start
        time.sleep(0.1)
        
        # Stop worker
        worker.stop_processing()
        assert not worker.is_running
        assert worker.status.state == WorkerState.OFFLINE
    
    def test_progress_summary(self, config, test_repo):
        """Test progress summary generation."""
        coordinator = IndexingCoordinator(config)
        
        # Create some jobs
        jobs = coordinator.create_indexing_jobs(test_repo, JobPriority.NORMAL)
        
        # Simulate some completions
        for i, job in enumerate(jobs[:2]):
            result = JobResult(
                job_id=job.job_id,
                worker_id="test-worker-1",
                status=JobStatus.COMPLETED,
                files_processed=5,
                symbols_found=20,
                processing_time=2.0
            )
            coordinator._handle_job_completion(result)
        
        # Get progress summary
        summary = coordinator.get_progress_summary()
        
        assert 'jobs' in summary
        assert 'workers' in summary
        assert 'performance' in summary
        assert 'uptime' in summary
        
        assert summary['jobs']['completed'] == 2
        assert summary['performance']['total_files_processed'] == 10
        assert summary['performance']['total_symbols_found'] == 40

class TestDistributedPerformance:
    """Performance and scaling tests for distributed system."""
    
    @pytest.fixture
    def large_test_repo(self):
        """Create a larger test repository for performance testing."""
        temp_dir = tempfile.mkdtemp()
        
        # Create many test files
        for i in range(100):
            file_path = os.path.join(temp_dir, f"module_{i}.py")
            with open(file_path, 'w') as f:
                f.write(f'''
def function_{i}():
    """Function {i}."""
    return {i}

class Class_{i}:
    def method_{i}(self):
        return "method_{i}"
        
    def another_method_{i}(self):
        return "another_method_{i}"
''')
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def performance_config(self):
        """Configuration optimized for performance testing."""
        return DistributedConfig(
            redis_url="redis://localhost:6379",
            job_queue="perf_test_jobs",
            result_queue="perf_test_results",
            worker_status_key="perf_test_workers",
            batch_size=10,
            max_workers=5,
            health_check_interval=5,
            heartbeat_interval=2
        )
    
    def test_scaling_performance(self, performance_config, large_test_repo):
        """Test performance scaling with multiple workers."""
        try:
            redis_client = redis.Redis(host='localhost', port=6379)
            redis_client.ping()
            redis_client.flushdb()
        except redis.ConnectionError:
            pytest.skip("Redis not available for performance testing")
        
        coordinator = IndexingCoordinator(performance_config)
        
        # Test with 1 worker
        start_time = time.time()
        jobs = coordinator.create_indexing_jobs(large_test_repo, JobPriority.HIGH)
        single_worker_job_count = len(jobs)
        single_worker_time = time.time() - start_time
        
        # Clean up for next test
        redis_client.flushdb()
        
        # Test with multiple workers would require actual Redis and workers running
        # This test validates job creation performance scales with repository size
        assert single_worker_job_count > 0
        assert single_worker_time < 5.0  # Should create jobs quickly
        
        # Validate job distribution
        total_files = sum(len(job.files) for job in jobs)
        assert total_files >= 100  # Should find our test files
        
        # Jobs should be reasonably sized
        avg_files_per_job = total_files / len(jobs)
        assert 5 <= avg_files_per_job <= 20  # Reasonable batch sizes

def run_integration_test():
    """Run a comprehensive integration test."""
    print("Running distributed system integration test...")
    
    # Setup
    config = DistributedConfig(
        redis_url="redis://localhost:6379",
        job_queue="integration_test_jobs",
        result_queue="integration_test_results",
        worker_status_key="integration_test_workers",
        batch_size=3,
        max_workers=2
    )
    
    try:
        redis_client = redis.Redis(host='localhost', port=6379)
        redis_client.ping()
        redis_client.flushdb()
    except redis.ConnectionError:
        print("Redis not available - skipping integration test")
        return
    
    # Create test repository
    temp_dir = tempfile.mkdtemp()
    test_files = {
        'app.py': 'def main(): pass\nclass App: pass',
        'utils.py': 'def helper(): pass\ndef other(): pass',
        'lib.js': 'function test() {}\nclass Lib {}'
    }
    
    for file_path, content in test_files.items():
        full_path = os.path.join(temp_dir, file_path)
        with open(full_path, 'w') as f:
            f.write(content)
    
    try:
        # Create coordinator and workers
        coordinator = IndexingCoordinator(config)
        workers = [
            IndexingWorker(f"integration-worker-{i}", config)
            for i in range(2)
        ]
        
        # Start monitoring
        coordinator.start_monitoring()
        
        # Create jobs
        print(f"Creating jobs for repository: {temp_dir}")
        jobs = coordinator.create_indexing_jobs(temp_dir, JobPriority.HIGH)
        print(f"Created {len(jobs)} jobs")
        
        # Start workers in threads
        worker_threads = []
        for worker in workers:
            thread = threading.Thread(target=worker.start_processing, daemon=True)
            worker_threads.append(thread)
            thread.start()
            print(f"Started worker {worker.worker_id}")
        
        # Wait for completion
        print("Waiting for job completion...")
        success = coordinator.wait_for_completion(timeout=30)
        
        # Stop workers
        for worker in workers:
            worker.stop_processing()
        
        # Stop monitoring
        coordinator.stop_monitoring()
        
        # Results
        summary = coordinator.get_progress_summary()
        print("\n=== Integration Test Results ===")
        print(f"Jobs completed: {summary['jobs']['completed']}")
        print(f"Jobs failed: {summary['jobs']['failed']}")
        print(f"Files processed: {summary['performance']['total_files_processed']}")
        print(f"Symbols found: {summary['performance']['total_symbols_found']}")
        print(f"Success rate: {summary['jobs']['completion_rate']:.2%}")
        print(f"Test successful: {success}")
        
        if success and summary['jobs']['completed'] > 0:
            print("\n✓ Integration test PASSED")
        else:
            print("\n✗ Integration test FAILED")
            
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        redis_client.flushdb()

if __name__ == "__main__":
    # Run integration test
    run_integration_test()
    
    # Run pytest if available
    try:
        pytest.main([__file__, "-v"])
    except SystemExit:
        pass