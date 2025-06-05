#!/usr/bin/env python3
"""
Demo script for the distributed processing system.
Shows how to use the distributed indexing for large repositories.
"""

import os
import time
import tempfile
import shutil
import logging
from typing import Dict, Any

from mcp_server.distributed import (
    IndexingCoordinator,
    IndexingWorker,
    DistributedConfig,
    JobPriority
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_demo_repository() -> str:
    """Create a demo repository with various file types for testing."""
    temp_dir = tempfile.mkdtemp(prefix="distributed_demo_")
    
    # Python files
    python_files = {
        'main.py': '''
#!/usr/bin/env python3
"""Main application entry point."""

import sys
import os
from typing import List, Dict, Any

class Application:
    """Main application class."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
    
    def start(self):
        """Start the application."""
        self.running = True
        logger.info("Application started")
    
    def stop(self):
        """Stop the application."""
        self.running = False
        logger.info("Application stopped")
    
    def process_data(self, data: List[str]) -> Dict[str, int]:
        """Process input data and return statistics."""
        return {
            'total_items': len(data),
            'unique_items': len(set(data)),
            'max_length': max(len(item) for item in data) if data else 0
        }

def main():
    """Main function."""
    app = Application({'debug': True})
    app.start()
    
    try:
        # Application logic here
        data = ['hello', 'world', 'distributed', 'processing']
        stats = app.process_data(data)
        print(f"Processed {stats['total_items']} items")
    finally:
        app.stop()

if __name__ == "__main__":
    main()
''',
        'utils/helpers.py': '''
"""Utility helper functions."""

import json
import os
from typing import Any, Dict, List, Optional

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return json.load(f)

def save_results(results: Dict[str, Any], output_path: str):
    """Save results to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

class DataProcessor:
    """Process various types of data."""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.processed_count = 0
    
    def process_batch(self, batch: List[Any]) -> List[Any]:
        """Process a batch of data."""
        processed = []
        for item in batch:
            if isinstance(item, str):
                processed.append(item.strip().lower())
            elif isinstance(item, (int, float)):
                processed.append(item * 2)
            else:
                processed.append(str(item))
        
        self.processed_count += len(processed)
        return processed
    
    def get_statistics(self) -> Dict[str, int]:
        """Get processing statistics."""
        return {
            'processed_count': self.processed_count,
            'batch_size': self.batch_size
        }
''',
        'models/data_model.py': '''
"""Data models for the application."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class DataItem:
    """Represents a single data item."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: Optional[float] = None
    processed_at: Optional[float] = None
    
    def mark_completed(self):
        """Mark item as completed."""
        import time
        self.status = ProcessingStatus.COMPLETED
        self.processed_at = time.time()
    
    def mark_failed(self, error: str):
        """Mark item as failed."""
        self.status = ProcessingStatus.FAILED
        self.metadata['error'] = error

@dataclass
class ProcessingJob:
    """Represents a processing job."""
    job_id: str
    items: List[DataItem]
    priority: int = 1
    worker_id: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    @property
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return all(item.status == ProcessingStatus.COMPLETED for item in self.items)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if not self.items:
            return 0.0
        
        completed = sum(1 for item in self.items if item.status == ProcessingStatus.COMPLETED)
        return completed / len(self.items)

class JobManager:
    """Manages processing jobs."""
    
    def __init__(self):
        self.jobs: Dict[str, ProcessingJob] = {}
        self.completed_jobs: List[str] = []
    
    def create_job(self, job_id: str, items: List[DataItem], priority: int = 1) -> ProcessingJob:
        """Create a new processing job."""
        job = ProcessingJob(job_id=job_id, items=items, priority=priority)
        self.jobs[job_id] = job
        return job
    
    def complete_job(self, job_id: str):
        """Mark job as completed."""
        if job_id in self.jobs:
            self.completed_jobs.append(job_id)
            del self.jobs[job_id]
    
    def get_pending_jobs(self) -> List[ProcessingJob]:
        """Get all pending jobs."""
        return [job for job in self.jobs.values() if not job.is_completed]
''',
    }
    
    # JavaScript files
    javascript_files = {
        'frontend/app.js': '''
/**
 * Main frontend application
 */

class Application {
    constructor(config) {
        this.config = config;
        this.modules = new Map();
        this.initialized = false;
    }
    
    async initialize() {
        console.log('Initializing application...');
        
        // Load modules
        await this.loadModule('data', new DataModule());
        await this.loadModule('ui', new UIModule());
        await this.loadModule('api', new APIModule());
        
        this.initialized = true;
        console.log('Application initialized successfully');
    }
    
    async loadModule(name, module) {
        try {
            await module.initialize(this.config);
            this.modules.set(name, module);
            console.log(`Module '${name}' loaded`);
        } catch (error) {
            console.error(`Failed to load module '${name}':`, error);
            throw error;
        }
    }
    
    getModule(name) {
        return this.modules.get(name);
    }
    
    async shutdown() {
        console.log('Shutting down application...');
        
        for (const [name, module] of this.modules) {
            try {
                if (module.shutdown) {
                    await module.shutdown();
                }
                console.log(`Module '${name}' shut down`);
            } catch (error) {
                console.error(`Error shutting down module '${name}':`, error);
            }
        }
        
        this.modules.clear();
        this.initialized = false;
        console.log('Application shut down complete');
    }
}

class DataModule {
    constructor() {
        this.cache = new Map();
        this.processors = [];
    }
    
    async initialize(config) {
        this.config = config;
        console.log('Data module initialized');
    }
    
    addProcessor(processor) {
        this.processors.push(processor);
    }
    
    async processData(data) {
        let result = data;
        
        for (const processor of this.processors) {
            result = await processor.process(result);
        }
        
        return result;
    }
    
    cache(key, value) {
        this.cache.set(key, value);
    }
    
    getCached(key) {
        return this.cache.get(key);
    }
}

class UIModule {
    constructor() {
        this.components = new Map();
        this.eventListeners = [];
    }
    
    async initialize(config) {
        this.config = config;
        this.setupEventListeners();
        console.log('UI module initialized');
    }
    
    setupEventListeners() {
        // Setup global event listeners
        document.addEventListener('click', this.handleClick.bind(this));
        document.addEventListener('keydown', this.handleKeydown.bind(this));
    }
    
    handleClick(event) {
        // Handle click events
        const target = event.target;
        if (target.dataset.action) {
            this.executeAction(target.dataset.action, target);
        }
    }
    
    handleKeydown(event) {
        // Handle keyboard shortcuts
        if (event.ctrlKey || event.metaKey) {
            switch (event.key) {
                case 's':
                    event.preventDefault();
                    this.executeAction('save');
                    break;
                case 'z':
                    event.preventDefault();
                    this.executeAction('undo');
                    break;
            }
        }
    }
    
    executeAction(action, element) {
        console.log(`Executing action: ${action}`);
        // Action execution logic
    }
    
    async shutdown() {
        // Remove event listeners
        this.eventListeners.forEach(listener => {
            document.removeEventListener(listener.type, listener.handler);
        });
        
        console.log('UI module shut down');
    }
}

class APIModule {
    constructor() {
        this.baseURL = '';
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
    }
    
    async initialize(config) {
        this.baseURL = config.apiBaseURL || '';
        this.defaultHeaders = { ...this.defaultHeaders, ...config.headers };
        console.log('API module initialized');
    }
    
    async request(method, endpoint, data = null) {
        const url = `${this.baseURL}${endpoint}`;
        const options = {
            method,
            headers: this.defaultHeaders
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${method} ${url}`, error);
            throw error;
        }
    }
    
    async get(endpoint) {
        return this.request('GET', endpoint);
    }
    
    async post(endpoint, data) {
        return this.request('POST', endpoint, data);
    }
    
    async put(endpoint, data) {
        return this.request('PUT', endpoint, data);
    }
    
    async delete(endpoint) {
        return this.request('DELETE', endpoint);
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    const config = {
        apiBaseURL: '/api/v1',
        debug: true
    };
    
    const app = new Application(config);
    
    try {
        await app.initialize();
        window.app = app; // Make globally available
    } catch (error) {
        console.error('Failed to initialize application:', error);
    }
});
''',
    }
    
    # Rust files
    rust_files = {
        'backend/src/main.rs': '''
//! Main backend application

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Clone)]
pub struct AppConfig {
    pub port: u16,
    pub database_url: String,
    pub redis_url: String,
    pub max_connections: u32,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            port: 8080,
            database_url: "postgresql://localhost/app".to_string(),
            redis_url: "redis://localhost:6379".to_string(),
            max_connections: 100,
        }
    }
}

#[derive(Debug)]
pub struct Application {
    config: AppConfig,
    services: Arc<RwLock<HashMap<String, Box<dyn Service + Send + Sync>>>>,
    running: Arc<RwLock<bool>>,
}

#[async_trait::async_trait]
pub trait Service {
    async fn start(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>>;
    async fn stop(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>>;
    fn name(&self) -> &str;
}

impl Application {
    pub fn new(config: AppConfig) -> Self {
        Self {
            config,
            services: Arc::new(RwLock::new(HashMap::new())),
            running: Arc::new(RwLock::new(false)),
        }
    }
    
    pub async fn register_service<S>(&self, service: S) 
    where 
        S: Service + Send + Sync + 'static 
    {
        let mut services = self.services.write().await;
        let name = service.name().to_string();
        services.insert(name, Box::new(service));
    }
    
    pub async fn start(&self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        println!("Starting application on port {}", self.config.port);
        
        let mut running = self.running.write().await;
        *running = true;
        
        // Start all services
        let mut services = self.services.write().await;
        for (name, service) in services.iter_mut() {
            println!("Starting service: {}", name);
            service.start().await?;
        }
        
        println!("Application started successfully");
        Ok(())
    }
    
    pub async fn stop(&self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        println!("Stopping application...");
        
        let mut running = self.running.write().await;
        *running = false;
        
        // Stop all services
        let mut services = self.services.write().await;
        for (name, service) in services.iter_mut() {
            println!("Stopping service: {}", name);
            if let Err(e) = service.stop().await {
                eprintln!("Error stopping service {}: {}", name, e);
            }
        }
        
        println!("Application stopped");
        Ok(())
    }
    
    pub async fn is_running(&self) -> bool {
        *self.running.read().await
    }
}

#[derive(Debug)]
pub struct DatabaseService {
    connection_pool: Option<sqlx::PgPool>,
}

impl DatabaseService {
    pub fn new() -> Self {
        Self {
            connection_pool: None,
        }
    }
}

#[async_trait::async_trait]
impl Service for DatabaseService {
    async fn start(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        // Initialize database connection pool
        println!("Initializing database connection pool");
        // self.connection_pool = Some(PgPool::connect(&database_url).await?);
        Ok(())
    }
    
    async fn stop(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        if let Some(pool) = &self.connection_pool {
            pool.close().await;
        }
        self.connection_pool = None;
        Ok(())
    }
    
    fn name(&self) -> &str {
        "database"
    }
}

#[derive(Debug)]
pub struct CacheService {
    redis_client: Option<redis::Client>,
}

impl CacheService {
    pub fn new() -> Self {
        Self {
            redis_client: None,
        }
    }
}

#[async_trait::async_trait]
impl Service for CacheService {
    async fn start(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        println!("Connecting to Redis");
        // self.redis_client = Some(redis::Client::open(redis_url)?);
        Ok(())
    }
    
    async fn stop(&mut self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        self.redis_client = None;
        Ok(())
    }
    
    fn name(&self) -> &str {
        "cache"
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    // Initialize logging
    env_logger::init();
    
    // Load configuration
    let config = AppConfig::default();
    
    // Create application
    let app = Application::new(config);
    
    // Register services
    app.register_service(DatabaseService::new()).await;
    app.register_service(CacheService::new()).await;
    
    // Start application
    app.start().await?;
    
    // Setup graceful shutdown
    tokio::signal::ctrl_c().await?;
    println!("Received shutdown signal");
    
    // Stop application
    app.stop().await?;
    
    Ok(())
}
''',
    }
    
    # Create all files
    all_files = {**python_files, **javascript_files, **rust_files}
    
    for file_path, content in all_files.items():
        full_path = os.path.join(temp_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
    
    logger.info(f"Created demo repository with {len(all_files)} files at {temp_dir}")
    return temp_dir

def run_distributed_demo():
    """Run a complete demonstration of the distributed system."""
    logger.info("Starting distributed processing demo...")
    
    # Configuration for demo
    config = DistributedConfig(
        redis_url="redis://localhost:6379",
        job_queue="demo_jobs",
        result_queue="demo_results", 
        worker_status_key="demo_workers",
        batch_size=5,  # Small batches for demo
        max_workers=3,
        health_check_interval=2,
        heartbeat_interval=1
    )
    
    # Create demo repository
    repo_path = create_demo_repository()
    
    try:
        # Test Redis connection
        import redis
        redis_client = redis.Redis(host='localhost', port=6379)
        redis_client.ping()
        redis_client.flushdb()  # Clean slate
        logger.info("Redis connection successful")
        
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        logger.info("Please ensure Redis is running on localhost:6379")
        return
    
    try:
        # Create coordinator and workers
        logger.info("Creating coordinator and workers...")
        coordinator = IndexingCoordinator(config)
        workers = [
            IndexingWorker(f"demo-worker-{i}", config)
            for i in range(3)
        ]
        
        # Start monitoring
        coordinator.start_monitoring()
        
        # Start workers in separate threads
        import threading
        worker_threads = []
        
        for worker in workers:
            thread = threading.Thread(target=worker.start_processing, daemon=True)
            worker_threads.append(thread)
            thread.start()
            logger.info(f"Started {worker.worker_id}")
        
        # Give workers time to start
        time.sleep(2)
        
        # Create and process jobs
        logger.info(f"Creating indexing jobs for repository: {repo_path}")
        jobs = coordinator.create_indexing_jobs(repo_path, JobPriority.HIGH)
        logger.info(f"Created {len(jobs)} jobs")
        
        # Monitor progress
        logger.info("Monitoring progress...")
        start_time = time.time()
        
        # Wait for completion with periodic status updates
        while coordinator.active_jobs:
            time.sleep(2)
            
            summary = coordinator.get_progress_summary()
            elapsed = time.time() - start_time
            
            logger.info(f"[{elapsed:.1f}s] Progress: "
                       f"{summary['jobs']['completed']}/{summary['jobs']['total']} jobs, "
                       f"{summary['performance']['total_files_processed']} files, "
                       f"{summary['performance']['total_symbols_found']} symbols, "
                       f"{summary['workers']['healthy']}/{summary['workers']['total']} workers")
            
            # Timeout after 60 seconds
            if elapsed > 60:
                logger.warning("Demo timeout reached")
                break
        
        # Final results
        final_summary = coordinator.get_progress_summary()
        total_time = time.time() - start_time
        
        logger.info("\n" + "="*50)
        logger.info("DISTRIBUTED PROCESSING DEMO RESULTS")
        logger.info("="*50)
        logger.info(f"Total processing time: {total_time:.2f} seconds")
        logger.info(f"Jobs completed: {final_summary['jobs']['completed']}")
        logger.info(f"Jobs failed: {final_summary['jobs']['failed']}")
        logger.info(f"Files processed: {final_summary['performance']['total_files_processed']}")
        logger.info(f"Symbols found: {final_summary['performance']['total_symbols_found']}")
        logger.info(f"Average processing time: {final_summary['performance']['avg_processing_time']:.2f}s")
        logger.info(f"Files per second: {final_summary['performance']['files_per_second']:.2f}")
        logger.info(f"Completion rate: {final_summary['jobs']['completion_rate']:.1%}")
        
        # Show some example symbols found
        if coordinator.completed_jobs:
            logger.info("\nExample symbols found:")
            for result in list(coordinator.completed_jobs.values())[:3]:
                if result.symbols:
                    for symbol in result.symbols[:5]:  # Show first 5 symbols
                        logger.info(f"  - {symbol.get('name', 'unnamed')} "
                                   f"({symbol.get('type', 'unknown')}) "
                                   f"in {os.path.basename(symbol.get('file_path', ''))}")
        
        # Performance analysis
        if final_summary['performance']['files_per_second'] > 10:
            logger.info("🚀 Excellent performance! System is processing files efficiently.")
        elif final_summary['performance']['files_per_second'] > 5:
            logger.info("✅ Good performance! System is working well.")
        else:
            logger.info("⚠️  Performance could be improved. Consider adding more workers.")
        
        # Stop workers
        logger.info("\nStopping workers...")
        for worker in workers:
            worker.stop_processing()
        
        # Stop monitoring
        coordinator.stop_monitoring()
        
        logger.info("Demo completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
        
    finally:
        # Cleanup
        logger.info("Cleaning up demo repository...")
        shutil.rmtree(repo_path)

if __name__ == "__main__":
    try:
        run_distributed_demo()
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo error: {e}")
        import traceback
        traceback.print_exc()