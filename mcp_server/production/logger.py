"""
Production logging system for MCP server.

Provides structured logging, performance tracking, and log aggregation.
"""

import asyncio
import json
import logging
import sys
import time
import traceback
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import threading
from queue import Queue, Empty
import gzip
import os

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels for structured logging."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogRecord:
    """Structured log record."""
    timestamp: str
    level: str
    message: str
    logger_name: str
    module: str
    function: str
    line_number: int
    process_id: int
    thread_id: int
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    duration_ms: Optional[float] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LogConfig:
    """Configuration for production logging."""
    level: LogLevel = LogLevel.INFO
    enable_console: bool = True
    enable_file: bool = True
    enable_json: bool = True
    enable_compression: bool = True
    file_path: str = "logs/mcp_server.log"
    max_file_size_mb: int = 100
    max_files: int = 10
    flush_interval: float = 1.0
    buffer_size: int = 1000
    enable_performance_logging: bool = True
    enable_error_tracking: bool = True
    enable_audit_logging: bool = True


class LogFormatter:
    """Custom log formatters."""
    
    @staticmethod
    def json_formatter(record: LogRecord) -> str:
        """Format log record as JSON."""
        return json.dumps(asdict(record), default=str, separators=(',', ':'))
    
    @staticmethod
    def human_formatter(record: LogRecord) -> str:
        """Format log record for human reading."""
        timestamp = record.timestamp
        level = record.level.ljust(8)
        name = record.logger_name
        message = record.message
        
        base = f"{timestamp} [{level}] {name}: {message}"
        
        if record.correlation_id:
            base += f" [correlation_id={record.correlation_id}]"
        
        if record.duration_ms is not None:
            base += f" [duration={record.duration_ms:.2f}ms]"
        
        if record.error_type:
            base += f" [error_type={record.error_type}]"
        
        if record.stack_trace:
            base += f"\n{record.stack_trace}"
        
        return base
    
    @staticmethod
    def structured_formatter(record: LogRecord) -> str:
        """Format log record with structured key=value pairs."""
        parts = [
            f"timestamp={record.timestamp}",
            f"level={record.level}",
            f"logger={record.logger_name}",
            f"message=\"{record.message}\""
        ]
        
        if record.correlation_id:
            parts.append(f"correlation_id={record.correlation_id}")
        
        if record.user_id:
            parts.append(f"user_id={record.user_id}")
        
        if record.session_id:
            parts.append(f"session_id={record.session_id}")
        
        if record.request_id:
            parts.append(f"request_id={record.request_id}")
        
        if record.duration_ms is not None:
            parts.append(f"duration_ms={record.duration_ms}")
        
        if record.error_type:
            parts.append(f"error_type={record.error_type}")
        
        for key, value in record.extra.items():
            parts.append(f"{key}={value}")
        
        result = " ".join(parts)
        
        if record.stack_trace:
            result += f"\nstack_trace:\n{record.stack_trace}"
        
        return result


class AsyncLogHandler:
    """Asynchronous log handler for high-performance logging."""
    
    def __init__(self, config: LogConfig):
        self.config = config
        self._queue: Queue = Queue(maxsize=config.buffer_size)
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._file_handles: Dict[str, Any] = {}
        self._current_file_sizes: Dict[str, int] = {}
        
        # Ensure log directory exists
        log_path = Path(config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def start(self) -> None:
        """Start the async log handler."""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Async log handler started")
    
    def stop(self) -> None:
        """Stop the async log handler."""
        if not self._running:
            return
        
        self._running = False
        
        # Signal worker to stop
        self._queue.put(None)
        
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
        
        # Close file handles
        for handle in self._file_handles.values():
            try:
                handle.close()
            except Exception:
                pass
        
        self._file_handles.clear()
        logger.info("Async log handler stopped")
    
    def log(self, record: LogRecord) -> None:
        """Add log record to queue."""
        try:
            self._queue.put_nowait(record)
        except Exception as e:
            # Fallback to synchronous logging
            print(f"Log queue full, dropping record: {e}", file=sys.stderr)
    
    def _worker_loop(self) -> None:
        """Main worker loop for processing log records."""
        while self._running:
            try:
                # Process batch of records
                records = []
                
                # Get first record (blocking)
                try:
                    record = self._queue.get(timeout=self.config.flush_interval)
                    if record is None:  # Shutdown signal
                        break
                    records.append(record)
                except Empty:
                    continue
                
                # Get additional records (non-blocking)
                while len(records) < 100:  # Batch size limit
                    try:
                        record = self._queue.get_nowait()
                        if record is None:  # Shutdown signal
                            break
                        records.append(record)
                    except Empty:
                        break
                
                # Process the batch
                if records:
                    self._process_batch(records)
                
            except Exception as e:
                print(f"Log worker error: {e}", file=sys.stderr)
    
    def _process_batch(self, records: List[LogRecord]) -> None:
        """Process a batch of log records."""
        for record in records:
            try:
                self._write_record(record)
            except Exception as e:
                print(f"Error writing log record: {e}", file=sys.stderr)
    
    def _write_record(self, record: LogRecord) -> None:
        """Write a single log record."""
        # Console output
        if self.config.enable_console:
            formatted = LogFormatter.human_formatter(record)
            print(formatted, file=sys.stderr)
        
        # File output
        if self.config.enable_file:
            self._write_to_file(record)
    
    def _write_to_file(self, record: LogRecord) -> None:
        """Write record to file with rotation."""
        file_path = self.config.file_path
        
        # Check if rotation is needed
        if self._needs_rotation(file_path):
            self._rotate_file(file_path)
        
        # Get or create file handle
        handle = self._get_file_handle(file_path)
        
        # Format and write
        if self.config.enable_json:
            formatted = LogFormatter.json_formatter(record)
        else:
            formatted = LogFormatter.structured_formatter(record)
        
        handle.write(formatted + '\n')
        handle.flush()
        
        # Update file size tracking
        self._current_file_sizes[file_path] = self._current_file_sizes.get(file_path, 0) + len(formatted) + 1
    
    def _needs_rotation(self, file_path: str) -> bool:
        """Check if file rotation is needed."""
        if not os.path.exists(file_path):
            return False
        
        current_size = self._current_file_sizes.get(file_path, 0)
        if current_size == 0:
            # Initialize size tracking
            try:
                current_size = os.path.getsize(file_path)
                self._current_file_sizes[file_path] = current_size
            except OSError:
                return False
        
        max_size = self.config.max_file_size_mb * 1024 * 1024
        return current_size >= max_size
    
    def _rotate_file(self, file_path: str) -> None:
        """Rotate log file."""
        try:
            # Close current handle
            if file_path in self._file_handles:
                self._file_handles[file_path].close()
                del self._file_handles[file_path]
            
            # Rotate existing files
            base_path = Path(file_path)
            for i in range(self.config.max_files - 1, 0, -1):
                old_file = base_path.with_suffix(f'.{i}{base_path.suffix}')
                new_file = base_path.with_suffix(f'.{i+1}{base_path.suffix}')
                
                if old_file.exists():
                    if new_file.exists():
                        new_file.unlink()
                    old_file.rename(new_file)
                    
                    # Compress old files
                    if self.config.enable_compression and i > 1:
                        self._compress_file(new_file)
            
            # Move current file to .1
            if base_path.exists():
                rotated_file = base_path.with_suffix(f'.1{base_path.suffix}')
                base_path.rename(rotated_file)
                
                if self.config.enable_compression:
                    self._compress_file(rotated_file)
            
            # Reset size tracking
            self._current_file_sizes[file_path] = 0
            
        except Exception as e:
            print(f"Error rotating log file: {e}", file=sys.stderr)
    
    def _compress_file(self, file_path: Path) -> None:
        """Compress a log file."""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            file_path.unlink()
            
        except Exception as e:
            print(f"Error compressing log file: {e}", file=sys.stderr)
    
    def _get_file_handle(self, file_path: str):
        """Get or create file handle."""
        if file_path not in self._file_handles:
            self._file_handles[file_path] = open(file_path, 'a', encoding='utf-8')
        
        return self._file_handles[file_path]


class StructuredLogger:
    """Structured logger with context support."""
    
    def __init__(self, name: str, handler: Optional[AsyncLogHandler] = None):
        self.name = name
        # Use a default handler if none provided (for testing)
        if handler is None:
            config = LogConfig(enable_console=True)
            handler = AsyncLogHandler(config)
        self.handler = handler
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs) -> None:
        """Set logging context."""
        self._context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear logging context."""
        self._context.clear()
    
    def with_context(self, **kwargs) -> 'ContextLogger':
        """Create logger with additional context."""
        return ContextLogger(self, kwargs)
    
    def _create_record(self, level: LogLevel, message: str, 
                      extra: Optional[Dict[str, Any]] = None,
                      error: Optional[Exception] = None) -> LogRecord:
        """Create a log record."""
        import inspect
        
        # Get caller information
        frame = inspect.currentframe()
        caller_frame = frame.f_back.f_back  # Skip this method and the log method
        
        caller_info = {
            'module': caller_frame.f_globals.get('__name__', 'unknown'),
            'function': caller_frame.f_code.co_name,
            'line_number': caller_frame.f_lineno
        }
        
        # Merge context and extra
        record_extra = dict(self._context)
        if extra:
            record_extra.update(extra)
        
        # Handle error information
        error_type = None
        stack_trace = None
        if error:
            error_type = type(error).__name__
            stack_trace = traceback.format_exception(type(error), error, error.__traceback__)
            stack_trace = ''.join(stack_trace)
        
        return LogRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            message=message,
            logger_name=self.name,
            module=caller_info['module'],
            function=caller_info['function'],
            line_number=caller_info['line_number'],
            process_id=os.getpid(),
            thread_id=threading.get_ident(),
            correlation_id=record_extra.get('correlation_id'),
            user_id=record_extra.get('user_id'),
            session_id=record_extra.get('session_id'),
            request_id=record_extra.get('request_id'),
            duration_ms=record_extra.get('duration_ms'),
            error_type=error_type,
            stack_trace=stack_trace,
            extra=record_extra
        )
    
    def trace(self, message: str, **kwargs) -> None:
        """Log trace message."""
        record = self._create_record(LogLevel.TRACE, message, kwargs)
        self.handler.log(record)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        record = self._create_record(LogLevel.DEBUG, message, kwargs)
        self.handler.log(record)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        record = self._create_record(LogLevel.INFO, message, kwargs)
        self.handler.log(record)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        record = self._create_record(LogLevel.WARNING, message, kwargs)
        self.handler.log(record)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log error message."""
        record = self._create_record(LogLevel.ERROR, message, kwargs, error)
        self.handler.log(record)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log critical message."""
        record = self._create_record(LogLevel.CRITICAL, message, kwargs, error)
        self.handler.log(record)
    
    def performance(self, operation: str, duration_ms: float, **kwargs) -> None:
        """Log performance metric."""
        kwargs['duration_ms'] = duration_ms
        kwargs['operation'] = operation
        record = self._create_record(LogLevel.INFO, f"Performance: {operation}", kwargs)
        self.handler.log(record)
    
    def audit(self, action: str, user_id: Optional[str] = None, **kwargs) -> None:
        """Log audit event."""
        kwargs['audit_action'] = action
        if user_id:
            kwargs['user_id'] = user_id
        record = self._create_record(LogLevel.INFO, f"Audit: {action}", kwargs)
        self.handler.log(record)


class ContextLogger:
    """Logger with additional context."""
    
    def __init__(self, logger: StructuredLogger, context: Dict[str, Any]):
        self.logger = logger
        self.context = context
    
    def _log_with_context(self, method: Callable, message: str, **kwargs):
        """Log with merged context."""
        merged_kwargs = dict(self.context)
        merged_kwargs.update(kwargs)
        return method(message, **merged_kwargs)
    
    def trace(self, message: str, **kwargs) -> None:
        self._log_with_context(self.logger.trace, message, **kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        self._log_with_context(self.logger.debug, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        self._log_with_context(self.logger.info, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        self._log_with_context(self.logger.warning, message, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        merged_kwargs = dict(self.context)
        merged_kwargs.update(kwargs)
        self.logger.error(message, error, **merged_kwargs)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        merged_kwargs = dict(self.context)
        merged_kwargs.update(kwargs)
        self.logger.critical(message, error, **merged_kwargs)
    
    def performance(self, operation: str, duration_ms: float, **kwargs) -> None:
        self._log_with_context(self.logger.performance, operation, duration_ms=duration_ms, **kwargs)
    
    def audit(self, action: str, user_id: Optional[str] = None, **kwargs) -> None:
        merged_kwargs = dict(self.context)
        merged_kwargs.update(kwargs)
        self.logger.audit(action, user_id, **merged_kwargs)


class ProductionLogger:
    """Main production logging system."""
    
    def __init__(self, config: LogConfig):
        self.config = config
        self.handler = AsyncLogHandler(config)
        self._loggers: Dict[str, StructuredLogger] = {}
    
    def start(self) -> None:
        """Start the logging system."""
        self.handler.start()
        logger.info("Production logging system started")
    
    def stop(self) -> None:
        """Stop the logging system."""
        self.handler.stop()
        logger.info("Production logging system stopped")
    
    def get_logger(self, name: str) -> StructuredLogger:
        """Get or create a structured logger."""
        if name not in self._loggers:
            self._loggers[name] = StructuredLogger(name, self.handler)
        return self._loggers[name]
    
    def set_global_context(self, **kwargs) -> None:
        """Set global context for all loggers."""
        for logger_instance in self._loggers.values():
            logger_instance.set_context(**kwargs)


# Global production logger instance
default_config = LogConfig(
    level=LogLevel.INFO,
    enable_console=True,
    enable_file=True,
    enable_json=True
)

production_logger = ProductionLogger(default_config)