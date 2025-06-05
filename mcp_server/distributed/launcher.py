#!/usr/bin/env python3
"""
Distributed system launcher for easy deployment and scaling.
Supports launching coordinator, workers, and monitoring dashboard.
"""

import os
import sys
import time
import signal
import argparse
import threading
import logging
from typing import List, Optional, Dict, Any
import subprocess
import json

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp_server.distributed import (
    IndexingCoordinator,
    IndexingWorker, 
    DistributedConfig,
    JobPriority
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DistributedLauncher:
    """Launcher for distributed indexing system."""
    
    def __init__(self, config: Optional[DistributedConfig] = None):
        self.config = config or DistributedConfig()
        self.coordinator: Optional[IndexingCoordinator] = None
        self.workers: List[IndexingWorker] = []
        self.worker_threads: List[threading.Thread] = []
        self.running = False
        
        # Signal handling
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def start_coordinator(self, enable_monitoring: bool = True) -> IndexingCoordinator:
        """Start the coordinator node."""
        logger.info("Starting coordinator...")
        
        self.coordinator = IndexingCoordinator(self.config)
        
        if enable_monitoring:
            self.coordinator.start_monitoring()
            logger.info("Coordinator monitoring started")
        
        # Add logging callbacks
        self.coordinator.add_job_completion_callback(self._on_job_completed)
        self.coordinator.add_job_failure_callback(self._on_job_failed)
        self.coordinator.add_worker_health_callback(self._on_worker_health_change)
        
        logger.info("Coordinator started successfully")
        return self.coordinator
    
    def start_workers(self, worker_count: int) -> List[IndexingWorker]:
        """Start worker nodes."""
        logger.info(f"Starting {worker_count} workers...")
        
        for i in range(worker_count):
            worker_id = f"worker-{i+1}"
            worker = IndexingWorker(worker_id, self.config)
            
            # Start worker in separate thread
            thread = threading.Thread(
                target=worker.start_processing,
                name=f"WorkerThread-{worker_id}",
                daemon=True
            )
            
            self.workers.append(worker)
            self.worker_threads.append(thread)
            thread.start()
            
            logger.info(f"Started worker {worker_id}")
        
        # Give workers time to initialize
        time.sleep(2)
        
        logger.info(f"All {worker_count} workers started successfully")
        return self.workers
    
    def index_repository(self, repo_path: str, priority: JobPriority = JobPriority.NORMAL,
                        wait_for_completion: bool = True, timeout: Optional[float] = None) -> bool:
        """Index a repository using the distributed system."""
        if not self.coordinator:
            raise RuntimeError("Coordinator not started")
        
        logger.info(f"Starting distributed indexing of repository: {repo_path}")
        
        # Create and queue jobs
        jobs = self.coordinator.create_indexing_jobs(repo_path, priority)
        
        if not jobs:
            logger.warning(f"No indexable files found in {repo_path}")
            return True
        
        logger.info(f"Created {len(jobs)} indexing jobs")
        
        if wait_for_completion:
            logger.info("Waiting for indexing to complete...")
            success = self.coordinator.wait_for_completion(timeout)
            
            # Print final summary
            summary = self.coordinator.get_progress_summary()
            logger.info(f"Indexing completed - {summary['jobs']['completed']} jobs, "
                       f"{summary['performance']['total_files_processed']} files, "
                       f"{summary['performance']['total_symbols_found']} symbols")
            
            return success
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the distributed system."""
        if not self.coordinator:
            return {"error": "Coordinator not started"}
        
        summary = self.coordinator.get_progress_summary()
        
        # Add worker details
        worker_details = []
        for worker in self.workers:
            if worker.is_running:
                status = worker.get_status()
                worker_details.append({
                    'worker_id': status.worker_id,
                    'state': status.state.value,
                    'jobs_completed': status.jobs_completed,
                    'jobs_failed': status.jobs_failed,
                    'cpu_usage': status.cpu_usage,
                    'memory_usage': status.memory_usage,
                    'uptime': status.uptime,
                    'is_healthy': status.is_healthy
                })
        
        summary['worker_details'] = worker_details
        summary['system'] = {
            'coordinator_running': self.coordinator is not None,
            'workers_running': len([w for w in self.workers if w.is_running]),
            'total_workers': len(self.workers)
        }
        
        return summary
    
    def shutdown(self):
        """Shutdown the entire distributed system."""
        if not self.running:
            return
            
        logger.info("Shutting down distributed system...")
        self.running = False
        
        # Stop workers
        for worker in self.workers:
            try:
                worker.stop_processing()
            except Exception as e:
                logger.error(f"Error stopping worker {worker.worker_id}: {e}")
        
        # Wait for worker threads
        for thread in self.worker_threads:
            try:
                thread.join(timeout=10)
            except Exception as e:
                logger.error(f"Error joining worker thread: {e}")
        
        # Stop coordinator
        if self.coordinator:
            try:
                self.coordinator.stop_monitoring()
            except Exception as e:
                logger.error(f"Error stopping coordinator: {e}")
        
        logger.info("Distributed system shutdown complete")
    
    def _on_job_completed(self, result):
        """Callback for job completion."""
        logger.info(f"Job {result.job_id} completed by {result.worker_id}: "
                   f"{result.files_processed} files, {result.symbols_found} symbols "
                   f"in {result.processing_time:.2f}s")
    
    def _on_job_failed(self, job):
        """Callback for job failure."""
        logger.error(f"Job {job.job_id} failed: {job.error_message}")
    
    def _on_worker_health_change(self, status):
        """Callback for worker health changes."""
        if not status.is_healthy:
            logger.warning(f"Worker {status.worker_id} health issue: {status.error_message}")

def main():
    """Main entry point for distributed system launcher."""
    parser = argparse.ArgumentParser(description="Distributed Code Indexing System")
    parser.add_argument('command', choices=['coordinator', 'worker', 'full', 'index', 'status'],
                       help='Command to run')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of workers to start (default: 4)')
    parser.add_argument('--repo-path', type=str,
                       help='Repository path to index')
    parser.add_argument('--priority', choices=['low', 'normal', 'high', 'urgent'], 
                       default='normal', help='Job priority (default: normal)')
    parser.add_argument('--redis-url', default='redis://localhost:6379',
                       help='Redis URL (default: redis://localhost:6379)')
    parser.add_argument('--worker-id', type=str,
                       help='Worker ID for single worker mode')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Files per job batch (default: 100)')
    parser.add_argument('--timeout', type=int,
                       help='Timeout for indexing completion (seconds)')
    parser.add_argument('--no-wait', action='store_true',
                       help='Don\'t wait for indexing completion')
    parser.add_argument('--config-file', type=str,
                       help='Configuration file (JSON)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = DistributedConfig(
        redis_url=args.redis_url,
        batch_size=args.batch_size
    )
    
    if args.config_file:
        try:
            with open(args.config_file) as f:
                config_data = json.load(f)
                for key, value in config_data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            sys.exit(1)
    
    # Convert priority string to enum
    priority_map = {
        'low': JobPriority.LOW,
        'normal': JobPriority.NORMAL,
        'high': JobPriority.HIGH,
        'urgent': JobPriority.URGENT
    }
    priority = priority_map[args.priority]
    
    launcher = DistributedLauncher(config)
    
    try:
        if args.command == 'coordinator':
            # Start coordinator only
            coordinator = launcher.start_coordinator()
            logger.info("Coordinator running. Press Ctrl+C to stop.")
            
            try:
                while True:
                    time.sleep(10)
                    summary = coordinator.get_progress_summary()
                    logger.info(f"Status: {summary['jobs']['active']} active jobs, "
                               f"{summary['workers']['healthy']} healthy workers")
            except KeyboardInterrupt:
                pass
                
        elif args.command == 'worker':
            # Start single worker
            if not args.worker_id:
                args.worker_id = f"worker-{os.getpid()}"
            
            worker = IndexingWorker(args.worker_id, config)
            logger.info(f"Starting worker {args.worker_id}. Press Ctrl+C to stop.")
            
            try:
                worker.start_processing()
                # Keep main thread alive
                while worker.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                worker.stop_processing()
                
        elif args.command == 'full':
            # Start coordinator and workers
            launcher.running = True
            coordinator = launcher.start_coordinator()
            workers = launcher.start_workers(args.workers)
            
            logger.info(f"Distributed system running with {len(workers)} workers. "
                       f"Press Ctrl+C to stop.")
            
            try:
                while launcher.running:
                    time.sleep(10)
                    summary = launcher.get_status()
                    logger.info(f"System status: {summary['jobs']['active']} active jobs, "
                               f"{summary['system']['workers_running']} workers running")
            except KeyboardInterrupt:
                pass
                
        elif args.command == 'index':
            # Index a repository
            if not args.repo_path:
                logger.error("--repo-path required for index command")
                sys.exit(1)
            
            if not os.path.exists(args.repo_path):
                logger.error(f"Repository path does not exist: {args.repo_path}")
                sys.exit(1)
            
            launcher.running = True
            coordinator = launcher.start_coordinator()
            workers = launcher.start_workers(args.workers)
            
            success = launcher.index_repository(
                args.repo_path, 
                priority,
                wait_for_completion=not args.no_wait,
                timeout=args.timeout
            )
            
            if success:
                logger.info("Repository indexing completed successfully")
            else:
                logger.error("Repository indexing failed or timed out")
                sys.exit(1)
                
        elif args.command == 'status':
            # Show system status
            coordinator = IndexingCoordinator(config)
            summary = coordinator.get_progress_summary()
            
            print("\n=== Distributed System Status ===")
            print(f"Jobs - Total: {summary['jobs']['total']}, "
                  f"Active: {summary['jobs']['active']}, "
                  f"Completed: {summary['jobs']['completed']}, "
                  f"Failed: {summary['jobs']['failed']}")
            print(f"Workers - Healthy: {summary['workers']['healthy']}, "
                  f"Total: {summary['workers']['total']}")
            print(f"Performance - Files: {summary['performance']['total_files_processed']}, "
                  f"Symbols: {summary['performance']['total_symbols_found']}")
            print(f"Uptime: {summary['uptime']:.1f} seconds")
            
    except Exception as e:
        logger.error(f"Error running command '{args.command}': {e}")
        sys.exit(1)
    finally:
        launcher.shutdown()

if __name__ == "__main__":
    main()