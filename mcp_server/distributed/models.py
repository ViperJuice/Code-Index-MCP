"""Data models for distributed processing."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import time
import uuid

class JobStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class JobPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class WorkerState(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

@dataclass
class IndexingJob:
    """Represents a distributed indexing job."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    repo_path: str = ""
    files: List[str] = field(default_factory=list)
    worker_id: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    assigned_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def processing_time(self) -> Optional[float]:
        """Calculate processing time if job is completed."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def file_count(self) -> int:
        """Number of files in this job."""
        return len(self.files)

@dataclass 
class JobResult:
    """Result of a completed indexing job."""
    job_id: str
    worker_id: str
    status: JobStatus
    files_processed: int
    symbols_found: int
    processing_time: float
    error_message: Optional[str] = None
    symbols: List[Dict[str, Any]] = field(default_factory=list)
    completed_at: float = field(default_factory=time.time)
    
    @property
    def success(self) -> bool:
        """Whether the job completed successfully."""
        return self.status == JobStatus.COMPLETED

@dataclass
class WorkerStatus:
    """Status information for a worker node."""
    worker_id: str
    state: WorkerState = WorkerState.IDLE
    current_job_id: Optional[str] = None
    jobs_completed: int = 0
    jobs_failed: int = 0
    total_files_processed: int = 0
    total_symbols_found: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    start_time: float = field(default_factory=time.time)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    error_message: Optional[str] = None
    
    @property
    def uptime(self) -> float:
        """Worker uptime in seconds."""
        return time.time() - self.start_time
    
    @property
    def is_healthy(self) -> bool:
        """Check if worker is healthy based on last heartbeat."""
        return time.time() - self.last_heartbeat < 30  # 30 second timeout

@dataclass
class DistributedConfig:
    """Configuration for distributed processing."""
    redis_url: str = "redis://localhost:6379"
    job_queue: str = "indexing_jobs"
    result_queue: str = "indexing_results"
    worker_status_key: str = "worker_status"
    health_check_interval: int = 10  # seconds
    job_timeout: int = 300  # 5 minutes
    max_retries: int = 3
    heartbeat_interval: int = 5  # seconds
    batch_size: int = 100  # files per job
    max_workers: int = 10
    queue_max_size: int = 1000
    result_ttl: int = 3600  # 1 hour
    
    # Performance tuning
    redis_connection_pool_size: int = 10
    redis_socket_keepalive: bool = True
    redis_socket_keepalive_options: Dict[str, Any] = field(default_factory=lambda: {
        'TCP_KEEPIDLE': 1,
        'TCP_KEEPINTVL': 3,
        'TCP_KEEPCNT': 5
    })