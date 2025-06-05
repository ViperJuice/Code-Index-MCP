"""Master node for distributed indexing with advanced coordination."""
import redis
import json
import os
import time
import logging
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

from ..models import (
    IndexingJob, 
    JobResult, 
    WorkerStatus, 
    JobStatus, 
    JobPriority,
    WorkerState,
    DistributedConfig
)

logger = logging.getLogger(__name__)

class IndexingCoordinator:
    """Advanced coordinator for distributed indexing with fault tolerance."""
    
    def __init__(self, config: Optional[DistributedConfig] = None):
        self.config = config or DistributedConfig()
        
        # Redis connection with connection pooling
        self.redis = redis.ConnectionPool.from_url(
            self.config.redis_url,
            max_connections=self.config.redis_connection_pool_size,
            socket_keepalive=self.config.redis_socket_keepalive,
            socket_keepalive_options=self.config.redis_socket_keepalive_options
        )
        self.redis_client = redis.Redis(connection_pool=self.redis)
        
        # Active jobs tracking
        self.active_jobs: Dict[str, IndexingJob] = {}
        self.completed_jobs: Dict[str, JobResult] = {}
        self.failed_jobs: Dict[str, IndexingJob] = {}
        self.worker_statuses: Dict[str, WorkerStatus] = {}
        
        # Monitoring
        self.total_files_processed = 0
        self.total_symbols_found = 0
        self.start_time = time.time()
        
        # Background monitoring
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Event callbacks
        self.job_completed_callbacks: List[Callable[[JobResult], None]] = []
        self.job_failed_callbacks: List[Callable[[IndexingJob], None]] = []
        self.worker_health_callbacks: List[Callable[[WorkerStatus], None]] = []
        
    def create_indexing_jobs(self, repo_path: str, priority: JobPriority = JobPriority.NORMAL) -> List[IndexingJob]:
        """Create optimized indexing jobs for a repository."""
        logger.info(f"Creating indexing jobs for repository: {repo_path}")
        
        # Get all files to index with categorization
        all_files = self._discover_files(repo_path)
        
        if not all_files:
            logger.warning(f"No indexable files found in {repo_path}")
            return []
        
        # Create jobs with optimal batching
        jobs = self._create_optimal_jobs(repo_path, all_files, priority)
        
        # Queue jobs with priority ordering
        self._queue_jobs(jobs)
        
        logger.info(f"Created {len(jobs)} indexing jobs for {len(all_files)} files")
        return jobs
    
    def _discover_files(self, repo_path: str) -> List[str]:
        """Discover all indexable files in repository."""
        all_files = []
        
        # File categories for better job distribution
        file_categories = {
            'large': [],  # > 100KB
            'medium': [], # 10KB - 100KB  
            'small': []   # < 10KB
        }
        
        for root, dirs, files in os.walk(repo_path):
            # Skip common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in 
                      {'node_modules', '__pycache__', 'target', 'build', 'dist'}]
            
            for file in files:
                if self._should_index_file(file):
                    file_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        
                        if file_size > 100 * 1024:  # > 100KB
                            file_categories['large'].append(file_path)
                        elif file_size > 10 * 1024:  # 10KB - 100KB
                            file_categories['medium'].append(file_path)
                        else:
                            file_categories['small'].append(file_path)
                            
                        all_files.append(file_path)
                    except OSError:
                        continue
        
        return all_files
    
    def _create_optimal_jobs(self, repo_path: str, all_files: List[str], priority: JobPriority) -> List[IndexingJob]:
        """Create optimally sized jobs for better load balancing."""
        jobs = []
        
        # Sort files by size for better distribution
        file_sizes = []
        for file_path in all_files:
            try:
                size = os.path.getsize(file_path)
                file_sizes.append((file_path, size))
            except OSError:
                file_sizes.append((file_path, 0))
        
        # Sort by size descending (largest first)
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        
        # Create jobs with balanced file distribution
        current_batch = []
        current_batch_size = 0
        max_batch_size = self.config.batch_size
        
        for file_path, size in file_sizes:
            current_batch.append(file_path)
            current_batch_size += 1
            
            # Create job when batch is full or we hit size limits
            if (current_batch_size >= max_batch_size or 
                len(jobs) >= self.config.max_workers * 2):  # 2x workers for queue depth
                
                job = IndexingJob(
                    repo_path=repo_path,
                    files=current_batch.copy(),
                    priority=priority,
                    metadata={
                        'batch_index': len(jobs),
                        'total_size': sum(os.path.getsize(f) for f in current_batch if os.path.exists(f))
                    }
                )
                
                jobs.append(job)
                self.active_jobs[job.job_id] = job
                
                current_batch.clear()
                current_batch_size = 0
        
        # Handle remaining files
        if current_batch:
            job = IndexingJob(
                repo_path=repo_path,
                files=current_batch,
                priority=priority,
                metadata={
                    'batch_index': len(jobs),
                    'total_size': sum(os.path.getsize(f) for f in current_batch if os.path.exists(f))
                }
            )
            jobs.append(job)
            self.active_jobs[job.job_id] = job
        
        return jobs
    
    def _queue_jobs(self, jobs: List[IndexingJob]):
        """Queue jobs with priority handling."""
        # Sort by priority
        sorted_jobs = sorted(jobs, key=lambda j: j.priority.value, reverse=True)
        
        pipeline = self.redis_client.pipeline()
        
        for job in sorted_jobs:
            job_data = asdict(job)
            # Convert enums to strings for JSON serialization
            job_data['status'] = job.status.value
            job_data['priority'] = job.priority.value
            
            # Use priority-based queue names for better scheduling
            queue_name = f"{self.config.job_queue}:{job.priority.name.lower()}"
            pipeline.lpush(queue_name, json.dumps(job_data))
        
        pipeline.execute()
        logger.info(f"Queued {len(jobs)} jobs across priority queues")
    
    def _should_index_file(self, filename: str) -> bool:
        """Check if file should be indexed."""
        extensions = ['.py', '.js', '.ts', '.rs', '.go', '.java', '.kt', '.rb', '.php', 
                     '.c', '.cpp', '.h', '.hpp', '.cs', '.php', '.scala', '.clj', '.dart']
        return any(filename.endswith(ext) for ext in extensions)
    
    def start_monitoring(self):
        """Start background monitoring of jobs and workers."""
        if self._monitoring_active:
            return
            
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Started background monitoring")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring_active = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("Stopped background monitoring")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                # Process completed jobs
                self._process_completed_jobs()
                
                # Check worker health
                self._check_worker_health()
                
                # Retry failed jobs
                self._retry_failed_jobs()
                
                # Clean up old data
                self._cleanup_old_data()
                
                time.sleep(self.config.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1)
    
    def _process_completed_jobs(self):
        """Process completed job results from Redis queue."""
        while True:
            try:
                # Check all priority result queues
                for priority in JobPriority:
                    queue_name = f"{self.config.result_queue}:{priority.name.lower()}"
                    result_data = self.redis_client.brpop(queue_name, timeout=0.1)
                    
                    if result_data:
                        result_json = result_data[1].decode('utf-8')
                        result_dict = json.loads(result_json)
                        
                        job_result = JobResult(**result_dict)
                        self._handle_job_completion(job_result)
                
                # Also check main result queue for backward compatibility
                result_data = self.redis_client.brpop(self.config.result_queue, timeout=0.1)
                if result_data:
                    result_json = result_data[1].decode('utf-8')
                    result_dict = json.loads(result_json)
                    
                    job_result = JobResult(**result_dict)
                    self._handle_job_completion(job_result)
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Error processing completed jobs: {e}")
                break
    
    def _handle_job_completion(self, result: JobResult):
        """Handle a completed job result."""
        job_id = result.job_id
        
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job.status = result.status
            job.completed_at = result.completed_at
            
            if result.success:
                self.completed_jobs[job_id] = result
                self.total_files_processed += result.files_processed
                self.total_symbols_found += result.symbols_found
                
                logger.info(f"Job {job_id} completed: {result.files_processed} files, "
                           f"{result.symbols_found} symbols in {result.processing_time:.2f}s")
                
                # Trigger callbacks
                for callback in self.job_completed_callbacks:
                    try:
                        callback(result)
                    except Exception as e:
                        logger.error(f"Error in job completion callback: {e}")
            else:
                self.failed_jobs[job_id] = job
                job.error_message = result.error_message
                logger.error(f"Job {job_id} failed: {result.error_message}")
                
                # Trigger failure callbacks
                for callback in self.job_failed_callbacks:
                    try:
                        callback(job)
                    except Exception as e:
                        logger.error(f"Error in job failure callback: {e}")
            
            # Remove from active jobs
            del self.active_jobs[job_id]
    
    def _check_worker_health(self):
        """Check health of all workers."""
        worker_keys = self.redis_client.keys(f"{self.config.worker_status_key}:*")
        
        for key in worker_keys:
            try:
                worker_data = self.redis_client.get(key)
                if worker_data:
                    worker_status = WorkerStatus(**json.loads(worker_data))
                    
                    # Update local tracking
                    self.worker_statuses[worker_status.worker_id] = worker_status
                    
                    # Check if worker is unhealthy
                    if not worker_status.is_healthy:
                        logger.warning(f"Worker {worker_status.worker_id} appears unhealthy")
                        
                        # Trigger health callbacks
                        for callback in self.worker_health_callbacks:
                            try:
                                callback(worker_status)
                            except Exception as e:
                                logger.error(f"Error in worker health callback: {e}")
                                
            except Exception as e:
                logger.error(f"Error checking worker health for {key}: {e}")
    
    def _retry_failed_jobs(self):
        """Retry failed jobs that haven't exceeded max retries."""
        jobs_to_retry = []
        
        for job_id, job in list(self.failed_jobs.items()):
            if job.retry_count < job.max_retries:
                jobs_to_retry.append(job)
                del self.failed_jobs[job_id]
        
        if jobs_to_retry:
            logger.info(f"Retrying {len(jobs_to_retry)} failed jobs")
            
            for job in jobs_to_retry:
                job.retry_count += 1
                job.status = JobStatus.RETRYING
                job.worker_id = None
                job.assigned_at = None
                job.started_at = None
                
                self.active_jobs[job.job_id] = job
            
            self._queue_jobs(jobs_to_retry)
    
    def _cleanup_old_data(self):
        """Clean up old completed job data."""
        cutoff_time = time.time() - self.config.result_ttl
        
        # Clean up old completed jobs
        to_remove = [
            job_id for job_id, result in self.completed_jobs.items()
            if result.completed_at < cutoff_time
        ]
        
        for job_id in to_remove:
            del self.completed_jobs[job_id]
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old job results")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get comprehensive progress summary."""
        active_count = len(self.active_jobs)
        completed_count = len(self.completed_jobs)
        failed_count = len(self.failed_jobs)
        total_count = active_count + completed_count + failed_count
        
        healthy_workers = sum(1 for w in self.worker_statuses.values() if w.is_healthy)
        total_workers = len(self.worker_statuses)
        
        processing_times = [r.processing_time for r in self.completed_jobs.values() if r.processing_time]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        return {
            'jobs': {
                'total': total_count,
                'active': active_count,
                'completed': completed_count,
                'failed': failed_count,
                'completion_rate': completed_count / total_count if total_count > 0 else 0
            },
            'workers': {
                'healthy': healthy_workers,
                'total': total_workers,
                'health_rate': healthy_workers / total_workers if total_workers > 0 else 0
            },
            'performance': {
                'total_files_processed': self.total_files_processed,
                'total_symbols_found': self.total_symbols_found,
                'avg_processing_time': avg_processing_time,
                'files_per_second': self.total_files_processed / (time.time() - self.start_time) if time.time() > self.start_time else 0
            },
            'uptime': time.time() - self.start_time
        }
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all active jobs to complete."""
        start_time = time.time()
        
        while self.active_jobs:
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"Timeout waiting for job completion. {len(self.active_jobs)} jobs still active")
                return False
                
            time.sleep(1)
            
            # Print progress periodically
            if int(time.time() - start_time) % 10 == 0:
                summary = self.get_progress_summary()
                logger.info(f"Progress: {summary['jobs']['completed']}/{summary['jobs']['total']} jobs completed")
        
        logger.info("All jobs completed successfully")
        return True
    
    def cancel_all_jobs(self):
        """Cancel all pending and active jobs."""
        # Clear job queues
        for priority in JobPriority:
            queue_name = f"{self.config.job_queue}:{priority.name.lower()}"
            self.redis_client.delete(queue_name)
        
        # Also clear main queue
        self.redis_client.delete(self.config.job_queue)
        
        # Mark active jobs as cancelled
        for job_id, job in self.active_jobs.items():
            job.status = JobStatus.FAILED
            job.error_message = "Cancelled by coordinator"
            self.failed_jobs[job_id] = job
        
        self.active_jobs.clear()
        logger.info("Cancelled all pending and active jobs")
    
    def add_job_completion_callback(self, callback: Callable[[JobResult], None]):
        """Add callback for job completion events."""
        self.job_completed_callbacks.append(callback)
    
    def add_job_failure_callback(self, callback: Callable[[IndexingJob], None]):
        """Add callback for job failure events.""" 
        self.job_failed_callbacks.append(callback)
    
    def add_worker_health_callback(self, callback: Callable[[WorkerStatus], None]):
        """Add callback for worker health events."""
        self.worker_health_callbacks.append(callback)
