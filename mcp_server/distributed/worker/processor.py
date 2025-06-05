"""Enhanced worker node for processing indexing jobs with fault tolerance."""
import redis
import json
import time
import os
import psutil
import threading
import signal
import sys
import logging
from typing import Dict, Any, Optional, List
from dataclasses import asdict

from mcp_server.indexer.index_engine import IndexEngine
from mcp_server.plugin_system.plugin_manager import PluginManager

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

class IndexingWorker:
    """Enhanced worker with fault tolerance, health monitoring, and performance optimization."""
    
    def __init__(self, worker_id: str, config: Optional[DistributedConfig] = None):
        self.worker_id = worker_id
        self.config = config or DistributedConfig()
        
        # Redis connection with connection pooling
        self.redis_pool = redis.ConnectionPool.from_url(
            self.config.redis_url,
            max_connections=self.config.redis_connection_pool_size,
            socket_keepalive=self.config.redis_socket_keepalive,
            socket_keepalive_options=self.config.redis_socket_keepalive_options
        )
        self.redis = redis.Redis(connection_pool=self.redis_pool)
        
        # Processing components
        self.indexer = IndexEngine()
        self.plugin_manager = PluginManager()
        
        # Worker state
        self.status = WorkerStatus(worker_id=worker_id)
        self.current_job: Optional[IndexingJob] = None
        self.is_running = False
        self.is_healthy = True
        
        # Performance monitoring
        self.process = psutil.Process()
        self.start_time = time.time()
        
        # Threading
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.processing_thread: Optional[threading.Thread] = None
        
        # Signal handling for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def start_processing(self):
        """Start worker with health monitoring and job processing."""
        if self.is_running:
            logger.warning(f"Worker {self.worker_id} is already running")
            return
            
        logger.info(f"Starting worker {self.worker_id}")
        self.is_running = True
        self.status.state = WorkerState.IDLE
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        # Start main processing loop
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=False)
        self.processing_thread.start()
        
        # Update status
        self._update_status()
        
        logger.info(f"Worker {self.worker_id} started successfully")
    
    def stop_processing(self):
        """Gracefully stop the worker."""
        logger.info(f"Stopping worker {self.worker_id}")
        self.is_running = False
        
        # Wait for current job to complete
        if self.current_job:
            logger.info(f"Waiting for current job {self.current_job.job_id} to complete")
            
        # Wait for threads to finish
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=10)
            
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        
        # Final status update
        self.status.state = WorkerState.OFFLINE
        self._update_status()
        
        logger.info(f"Worker {self.worker_id} stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Worker {self.worker_id} received signal {signum}, shutting down gracefully")
        self.stop_processing()
        sys.exit(0)
    
    def _processing_loop(self):
        """Main processing loop with fault tolerance."""
        while self.is_running:
            try:
                # Get job from priority queues
                job = self._get_next_job()
                
                if job:
                    self._process_job_with_monitoring(job)
                else:
                    # No jobs available, wait briefly
                    time.sleep(1)
                    self.status.state = WorkerState.IDLE
                    
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                self.is_healthy = False
                self.status.state = WorkerState.ERROR
                self.status.error_message = str(e)
                time.sleep(5)  # Back off on error
                
        logger.info(f"Worker {self.worker_id} processing loop ended")
    
    def _get_next_job(self) -> Optional[IndexingJob]:
        """Get next job from priority queues."""
        # Check priority queues in order (highest first)
        for priority in sorted(JobPriority, key=lambda p: p.value, reverse=True):
            queue_name = f"{self.config.job_queue}:{priority.name.lower()}"
            
            try:
                result = self.redis.brpop(queue_name, timeout=1)
                if result:
                    job_data = json.loads(result[1].decode('utf-8'))
                    
                    # Convert back to enums
                    job_data['status'] = JobStatus(job_data['status'])
                    job_data['priority'] = JobPriority(job_data['priority'])
                    
                    job = IndexingJob(**job_data)
                    logger.debug(f"Worker {self.worker_id} got job {job.job_id} from {queue_name}")
                    return job
                    
            except Exception as e:
                logger.error(f"Error getting job from {queue_name}: {e}")
        
        # Also check main queue for backward compatibility
        try:
            result = self.redis.brpop(self.config.job_queue, timeout=1)
            if result:
                job_data = json.loads(result[1].decode('utf-8'))
                
                # Handle legacy job format
                if 'status' not in job_data:
                    job_data['status'] = JobStatus.PENDING
                if 'priority' not in job_data:
                    job_data['priority'] = JobPriority.NORMAL
                    
                job = IndexingJob(**job_data)
                logger.debug(f"Worker {self.worker_id} got job {job.job_id} from main queue")
                return job
                
        except Exception as e:
            logger.error(f"Error getting job from main queue: {e}")
        
        return None
    
    def _process_job_with_monitoring(self, job: IndexingJob):
        """Process job with comprehensive monitoring and error handling."""
        self.current_job = job
        self.status.state = WorkerState.BUSY
        self.status.current_job_id = job.job_id
        
        # Update job status
        job.worker_id = self.worker_id
        job.status = JobStatus.PROCESSING
        job.assigned_at = time.time()
        job.started_at = time.time()
        
        start_time = time.time()
        symbols = []
        files_processed = 0
        error_message = None
        
        try:
            logger.info(f"Worker {self.worker_id} processing job {job.job_id} with {len(job.files)} files")
            
            # Process files with progress tracking
            for i, file_path in enumerate(job.files):
                if not self.is_running:
                    logger.warning(f"Worker {self.worker_id} stopping, abandoning job {job.job_id}")
                    return
                    
                try:
                    file_symbols = self._process_single_file(file_path)
                    symbols.extend(file_symbols)
                    files_processed += 1
                    
                    # Update progress periodically
                    if i % 10 == 0:
                        progress = (i + 1) / len(job.files) * 100
                        logger.debug(f"Job {job.job_id} progress: {progress:.1f}% ({i+1}/{len(job.files)} files)")
                        
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    # Continue with other files
                    
            # Job completed successfully
            job.status = JobStatus.COMPLETED
            processing_time = time.time() - start_time
            
            self.status.jobs_completed += 1
            self.status.total_files_processed += files_processed
            self.status.total_symbols_found += len(symbols)
            
            logger.info(f"Worker {self.worker_id} completed job {job.job_id}: "
                       f"{files_processed} files, {len(symbols)} symbols in {processing_time:.2f}s")
                       
        except Exception as e:
            # Job failed
            job.status = JobStatus.FAILED
            error_message = str(e)
            processing_time = time.time() - start_time
            
            self.status.jobs_failed += 1
            self.status.error_message = error_message
            
            logger.error(f"Worker {self.worker_id} failed job {job.job_id}: {error_message}")
            
        finally:
            # Send result
            self._send_job_result(job, files_processed, len(symbols), 
                                time.time() - start_time, error_message, symbols)
            
            # Clean up
            self.current_job = None
            self.status.state = WorkerState.IDLE
            self.status.current_job_id = None
            
    def _process_single_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a single file and extract symbols."""
        try:
            # Check if file exists and is readable
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return []
                
            if not os.access(file_path, os.R_OK):
                logger.warning(f"File not readable: {file_path}")
                return []
            
            # Get file extension for plugin selection
            _, ext = os.path.splitext(file_path)
            
            # Try to get appropriate plugin
            plugin = self.plugin_manager.get_plugin_for_extension(ext)
            
            if plugin:
                # Use plugin for processing
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                symbols = plugin.extract_symbols(content, file_path)
                return symbols if symbols else []
            else:
                # Fallback to basic indexing
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                symbols = self.indexer.index_file(file_path, content)
                return symbols if symbols else []
                
        except UnicodeDecodeError:
            logger.debug(f"Binary file skipped: {file_path}")
            return []
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return []
    
    def _send_job_result(self, job: IndexingJob, files_processed: int, symbols_found: int,
                        processing_time: float, error_message: Optional[str], 
                        symbols: List[Dict[str, Any]]):
        """Send job result to coordinator."""
        result = JobResult(
            job_id=job.job_id,
            worker_id=self.worker_id,
            status=job.status,
            files_processed=files_processed,
            symbols_found=symbols_found,
            processing_time=processing_time,
            error_message=error_message,
            symbols=symbols
        )
        
        try:
            # Send to priority-specific result queue
            queue_name = f"{self.config.result_queue}:{job.priority.name.lower()}"
            result_data = asdict(result)
            result_data['status'] = result.status.value  # Convert enum to string
            
            self.redis.lpush(queue_name, json.dumps(result_data))
            
            # Also send to main queue for backward compatibility
            self.redis.lpush(self.config.result_queue, json.dumps(result_data))
            
            logger.debug(f"Sent result for job {job.job_id}")
            
        except Exception as e:
            logger.error(f"Error sending job result: {e}")
            
    def _heartbeat_loop(self):
        """Send periodic heartbeat updates."""
        while self.is_running:
            try:
                self._update_status()
                time.sleep(self.config.heartbeat_interval)
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(1)
                
    def _update_status(self):
        """Update worker status in Redis."""
        try:
            # Update performance metrics
            self.status.cpu_usage = self.process.cpu_percent()
            self.status.memory_usage = self.process.memory_info().rss / 1024 / 1024  # MB
            self.status.last_heartbeat = time.time()
            
            # Store in Redis with TTL
            status_key = f"{self.config.worker_status_key}:{self.worker_id}"
            status_data = asdict(self.status)
            status_data['state'] = self.status.state.value  # Convert enum to string
            
            self.redis.setex(
                status_key, 
                self.config.heartbeat_interval * 3,  # TTL = 3x heartbeat interval
                json.dumps(status_data)
            )
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    def get_status(self) -> WorkerStatus:
        """Get current worker status."""
        self._update_status()
        return self.status
    
    def is_processing(self) -> bool:
        """Check if worker is currently processing a job."""
        return self.current_job is not None
