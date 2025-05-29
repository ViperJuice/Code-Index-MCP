# Watchdog Documentation

## Overview and Key Features

Watchdog is a Python library and shell utilities for monitoring file system events. It provides a cross-platform API to monitor file system changes in real-time, making it ideal for applications that need to respond to file modifications, creations, deletions, or moves.

### Key Features
- **Cross-Platform**: Works on Linux, macOS, Windows, and BSD
- **Multiple Backends**: Uses native OS APIs (inotify on Linux, FSEvents on macOS, etc.)
- **Event Types**: Detects file/directory creation, modification, deletion, and movement
- **Pattern Matching**: Built-in support for filtering events by patterns
- **Thread-Safe**: Events are delivered in a thread-safe manner
- **Shell Utilities**: Command-line tools for quick file monitoring
- **Extensible**: Easy to create custom event handlers

## Installation and Basic Setup

### Installation

```bash
# Basic installation
pip install watchdog

# With optional dependencies for better performance
pip install watchdog[watchmedo]
```

### Basic Setup

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

# Create a basic event handler
class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            print(f"Modified: {event.src_path}")
    
    def on_created(self, event):
        print(f"Created: {event.src_path}")
    
    def on_deleted(self, event):
        print(f"Deleted: {event.src_path}")
    
    def on_moved(self, event):
        print(f"Moved: {event.src_path} to {event.dest_path}")

# Set up the observer
observer = Observer()
event_handler = MyHandler()
observer.schedule(event_handler, path='/path/to/watch', recursive=True)

# Start monitoring
observer.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

## MCP Server Use Cases

### 1. Auto-Indexing Code Changes

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from pathlib import Path
import asyncio
from typing import Set, Dict, Any
import threading
import queue

class CodeIndexWatcher(FileSystemEventHandler):
    """Watch for code changes and trigger re-indexing."""
    
    def __init__(self, index_queue: queue.Queue, extensions: Set[str]):
        self.index_queue = index_queue
        self.extensions = extensions
        self.debounce_timers: Dict[str, threading.Timer] = {}
        self.debounce_delay = 0.5  # seconds
    
    def _should_process(self, path: str) -> bool:
        """Check if file should be processed."""
        if Path(path).name.startswith('.'):
            return False
        
        return any(path.endswith(ext) for ext in self.extensions)
    
    def _debounced_index(self, path: str, event_type: str):
        """Add file to indexing queue after debounce delay."""
        self.index_queue.put({
            'path': path,
            'event': event_type,
            'timestamp': time.time()
        })
    
    def _schedule_index(self, path: str, event_type: str):
        """Schedule indexing with debouncing."""
        # Cancel existing timer for this path
        if path in self.debounce_timers:
            self.debounce_timers[path].cancel()
        
        # Schedule new timer
        timer = threading.Timer(
            self.debounce_delay,
            self._debounced_index,
            args=[path, event_type]
        )
        self.debounce_timers[path] = timer
        timer.start()
    
    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory and self._should_process(event.src_path):
            self._schedule_index(event.src_path, 'modified')
    
    def on_created(self, event: FileSystemEvent):
        if not event.is_directory and self._should_process(event.src_path):
            self._schedule_index(event.src_path, 'created')
    
    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory and self._should_process(event.src_path):
            # Immediate processing for deletions
            self.index_queue.put({
                'path': event.src_path,
                'event': 'deleted',
                'timestamp': time.time()
            })
    
    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            if self._should_process(event.src_path):
                self.index_queue.put({
                    'path': event.src_path,
                    'event': 'deleted',
                    'timestamp': time.time()
                })
            
            if self._should_process(event.dest_path):
                self._schedule_index(event.dest_path, 'created')
```

### 2. Configuration File Hot Reload

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import yaml
import json
from typing import Dict, Any, Callable
import logging

class ConfigWatcher(FileSystemEventHandler):
    """Watch configuration files and reload on changes."""
    
    def __init__(self, config_files: Dict[str, str], 
                 on_reload: Callable[[str, Dict[str, Any]], None]):
        """
        Args:
            config_files: Mapping of config names to file paths
            on_reload: Callback function(config_name, new_config)
        """
        self.config_files = {Path(p).absolute(): name 
                           for name, p in config_files.items()}
        self.on_reload = on_reload
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, path: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(path, 'r') as f:
                if path.suffix == '.json':
                    return json.load(f)
                elif path.suffix in ['.yml', '.yaml']:
                    return yaml.safe_load(f)
                else:
                    raise ValueError(f"Unsupported config format: {path.suffix}")
        except Exception as e:
            self.logger.error(f"Failed to load config {path}: {e}")
            return {}
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        path = Path(event.src_path).absolute()
        if path in self.config_files:
            config_name = self.config_files[path]
            self.logger.info(f"Reloading config: {config_name}")
            
            new_config = self._load_config(path)
            if new_config:
                self.on_reload(config_name, new_config)
```

### 3. Build System Integration

```python
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import subprocess
import threading
from collections import defaultdict
from typing import List, Set

class BuildWatcher(PatternMatchingEventHandler):
    """Watch source files and trigger builds."""
    
    def __init__(self, build_rules: Dict[str, Dict[str, Any]]):
        """
        Args:
            build_rules: Mapping of pattern to build configuration
                {
                    "*.py": {
                        "command": ["python", "-m", "py_compile"],
                        "cooldown": 2.0
                    },
                    "*.ts": {
                        "command": ["tsc"],
                        "cooldown": 3.0
                    }
                }
        """
        patterns = list(build_rules.keys())
        super().__init__(patterns=patterns, ignore_directories=True)
        
        self.build_rules = build_rules
        self.build_queues = defaultdict(set)
        self.build_locks = defaultdict(threading.Lock)
        self.cooldown_timers = {}
    
    def _get_matching_rule(self, path: str) -> Optional[tuple]:
        """Find the build rule matching this path."""
        for pattern, rule in self.build_rules.items():
            if Path(path).match(pattern):
                return pattern, rule
        return None
    
    def _run_build(self, pattern: str, files: Set[str]):
        """Execute build command for files."""
        rule = self.build_rules[pattern]
        command = rule['command']
        
        # Build command with file list
        cmd = command + list(files)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                print(f"Build failed for {pattern}:")
                print(result.stderr)
            else:
                print(f"Build successful for {pattern}: {len(files)} files")
        except Exception as e:
            print(f"Build error: {e}")
        finally:
            # Clear the queue
            with self.build_locks[pattern]:
                self.build_queues[pattern].clear()
    
    def _schedule_build(self, pattern: str):
        """Schedule a build after cooldown period."""
        rule = self.build_rules[pattern]
        cooldown = rule.get('cooldown', 1.0)
        
        # Cancel existing timer
        if pattern in self.cooldown_timers:
            self.cooldown_timers[pattern].cancel()
        
        # Get files to build
        with self.build_locks[pattern]:
            files = self.build_queues[pattern].copy()
        
        # Schedule new build
        timer = threading.Timer(
            cooldown,
            self._run_build,
            args=[pattern, files]
        )
        self.cooldown_timers[pattern] = timer
        timer.start()
    
    def on_modified(self, event):
        rule_match = self._get_matching_rule(event.src_path)
        if rule_match:
            pattern, _ = rule_match
            with self.build_locks[pattern]:
                self.build_queues[pattern].add(event.src_path)
            self._schedule_build(pattern)
```

## Code Examples

### Pattern-Based Monitoring

```python
from watchdog.events import PatternMatchingEventHandler

class CodeFileHandler(PatternMatchingEventHandler):
    def __init__(self):
        patterns = ["*.py", "*.js", "*.java", "*.cpp"]
        ignore_patterns = ["*/__pycache__/*", "*/node_modules/*", "*/.git/*"]
        super().__init__(
            patterns=patterns,
            ignore_patterns=ignore_patterns,
            ignore_directories=False,
            case_sensitive=True
        )
    
    def on_created(self, event):
        print(f"New code file: {event.src_path}")
    
    def on_modified(self, event):
        print(f"Code file modified: {event.src_path}")
```

### Async Integration

```python
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from asyncio import Queue

class AsyncEventHandler(FileSystemEventHandler):
    def __init__(self, event_queue: Queue):
        self.event_queue = event_queue
        self.loop = asyncio.get_event_loop()
    
    def on_any_event(self, event):
        # Schedule async task
        asyncio.run_coroutine_threadsafe(
            self.event_queue.put({
                'type': event.event_type,
                'path': event.src_path,
                'is_directory': event.is_directory
            }),
            self.loop
        )

async def process_events(event_queue: Queue):
    """Async event processor."""
    while True:
        event = await event_queue.get()
        print(f"Processing event: {event}")
        # Perform async operations
        await asyncio.sleep(0.1)

async def main():
    event_queue = Queue()
    
    # Set up file watcher
    observer = Observer()
    handler = AsyncEventHandler(event_queue)
    observer.schedule(handler, '.', recursive=True)
    observer.start()
    
    try:
        # Process events asynchronously
        await process_events(event_queue)
    finally:
        observer.stop()
        observer.join()
```

### Custom Event Filtering

```python
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import re

class FilteredEventHandler(FileSystemEventHandler):
    def __init__(self, 
                 include_patterns: List[str] = None,
                 exclude_patterns: List[str] = None,
                 min_file_size: int = 0,
                 max_file_size: int = None):
        self.include_re = [re.compile(p) for p in (include_patterns or [])]
        self.exclude_re = [re.compile(p) for p in (exclude_patterns or [])]
        self.min_file_size = min_file_size
        self.max_file_size = max_file_size
    
    def should_process(self, path: str) -> bool:
        """Determine if event should be processed."""
        # Check include patterns
        if self.include_re:
            if not any(r.search(path) for r in self.include_re):
                return False
        
        # Check exclude patterns
        if any(r.search(path) for r in self.exclude_re):
            return False
        
        # Check file size
        try:
            size = Path(path).stat().st_size
            if size < self.min_file_size:
                return False
            if self.max_file_size and size > self.max_file_size:
                return False
        except:
            pass
        
        return True
    
    def on_modified(self, event):
        if not event.is_directory and self.should_process(event.src_path):
            print(f"Processing: {event.src_path}")
```

## Best Practices

### 1. Event Debouncing

```python
import threading
from typing import Dict, Callable

class DebouncedEventHandler(FileSystemEventHandler):
    """Handler with event debouncing."""
    
    def __init__(self, callback: Callable, delay: float = 0.5):
        self.callback = callback
        self.delay = delay
        self.timers: Dict[str, threading.Timer] = {}
        self.lock = threading.Lock()
    
    def _debounced_callback(self, event_type: str, path: str):
        """Execute callback after delay."""
        with self.lock:
            self.timers.pop(path, None)
        self.callback(event_type, path)
    
    def _handle_event(self, event_type: str, path: str):
        """Handle event with debouncing."""
        with self.lock:
            # Cancel existing timer
            if path in self.timers:
                self.timers[path].cancel()
            
            # Schedule new timer
            timer = threading.Timer(
                self.delay,
                self._debounced_callback,
                args=[event_type, path]
            )
            self.timers[path] = timer
            timer.start()
    
    def on_modified(self, event):
        if not event.is_directory:
            self._handle_event('modified', event.src_path)
```

### 2. Resource Management

```python
class ManagedWatcher:
    """Context manager for file watching."""
    
    def __init__(self, path: str, handler: FileSystemEventHandler,
                 recursive: bool = True):
        self.path = path
        self.handler = handler
        self.recursive = recursive
        self.observer = None
    
    def __enter__(self):
        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            self.path,
            recursive=self.recursive
        )
        self.observer.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5)

# Usage
with ManagedWatcher('/path/to/watch', MyHandler()) as watcher:
    # Do something
    time.sleep(10)
```

### 3. Error Handling

```python
class ResilientEventHandler(FileSystemEventHandler):
    """Event handler with comprehensive error handling."""
    
    def __init__(self, error_callback: Callable = None):
        self.error_callback = error_callback
        self.error_count = 0
        self.max_errors = 10
    
    def _handle_error(self, event_type: str, path: str, error: Exception):
        """Handle processing errors."""
        self.error_count += 1
        
        if self.error_callback:
            self.error_callback(event_type, path, error)
        else:
            print(f"Error processing {event_type} for {path}: {error}")
        
        if self.error_count > self.max_errors:
            raise RuntimeError("Too many errors in event processing")
    
    def _safe_process(self, event_type: str, path: str):
        """Process event with error handling."""
        try:
            # Your processing logic here
            print(f"Processing {event_type}: {path}")
        except Exception as e:
            self._handle_error(event_type, path, e)
    
    def on_any_event(self, event):
        if not event.is_directory:
            self._safe_process(event.event_type, event.src_path)
```

### 4. Platform-Specific Considerations

```python
import platform
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

def create_observer(use_polling: bool = False) -> Observer:
    """Create appropriate observer for platform."""
    if use_polling:
        # Use polling observer (works everywhere but less efficient)
        return PollingObserver()
    
    system = platform.system()
    
    if system == 'Linux':
        # Linux has inotify with limits
        try:
            with open('/proc/sys/fs/inotify/max_user_watches', 'r') as f:
                max_watches = int(f.read().strip())
                if max_watches < 100000:
                    print(f"Warning: Low inotify limit ({max_watches})")
        except:
            pass
    
    elif system == 'Darwin':
        # macOS FSEvents can have delays
        print("Note: macOS FSEvents may have slight delays")
    
    elif system == 'Windows':
        # Windows has good support but path length limits
        print("Note: Watch for Windows path length limits")
    
    return Observer()
```

## Performance Tips

### 1. Minimize Watched Paths

```python
def create_targeted_observers(project_root: str) -> List[Observer]:
    """Create observers for specific directories only."""
    observers = []
    
    # Define specific paths to watch
    watch_paths = [
        ('src', True),      # recursive
        ('config', False),  # non-recursive
        ('tests', True),    # recursive
    ]
    
    for rel_path, recursive in watch_paths:
        path = os.path.join(project_root, rel_path)
        if os.path.exists(path):
            observer = Observer()
            observer.schedule(
                MyHandler(),
                path,
                recursive=recursive
            )
            observers.append(observer)
    
    return observers
```

### 2. Batch Processing

```python
import queue
import threading
from typing import List

class BatchProcessor:
    """Process file events in batches."""
    
    def __init__(self, batch_size: int = 10, timeout: float = 1.0):
        self.batch_size = batch_size
        self.timeout = timeout
        self.queue = queue.Queue()
        self.processor_thread = threading.Thread(target=self._process_batches)
        self.processor_thread.daemon = True
        self.running = True
    
    def start(self):
        self.processor_thread.start()
    
    def stop(self):
        self.running = False
        self.processor_thread.join()
    
    def add_event(self, event):
        self.queue.put(event)
    
    def _process_batches(self):
        """Process events in batches."""
        while self.running:
            batch = []
            deadline = time.time() + self.timeout
            
            while len(batch) < self.batch_size and time.time() < deadline:
                try:
                    timeout = max(0, deadline - time.time())
                    event = self.queue.get(timeout=timeout)
                    batch.append(event)
                except queue.Empty:
                    break
            
            if batch:
                self._process_batch(batch)
    
    def _process_batch(self, batch: List):
        """Process a batch of events."""
        print(f"Processing batch of {len(batch)} events")
        # Implement batch processing logic
```

### 3. Selective Event Processing

```python
class SelectiveEventHandler(FileSystemEventHandler):
    """Only process events that meet certain criteria."""
    
    def __init__(self):
        self.last_process_time = {}
        self.min_interval = 1.0  # seconds
        self.size_threshold = 1024  # bytes
    
    def should_process(self, path: str) -> bool:
        """Determine if event should be processed."""
        now = time.time()
        
        # Check time since last process
        if path in self.last_process_time:
            if now - self.last_process_time[path] < self.min_interval:
                return False
        
        # Check file size
        try:
            size = os.path.getsize(path)
            if size < self.size_threshold:
                return False
        except:
            return False
        
        self.last_process_time[path] = now
        return True
    
    def on_modified(self, event):
        if not event.is_directory and self.should_process(event.src_path):
            print(f"Processing: {event.src_path}")
```

### 4. Memory-Efficient Event Storage

```python
from collections import deque
import heapq

class EventStore:
    """Memory-efficient storage for events."""
    
    def __init__(self, max_events: int = 1000):
        self.max_events = max_events
        self.events = deque(maxlen=max_events)
        self.event_counts = defaultdict(int)
    
    def add_event(self, event_type: str, path: str):
        """Add event with automatic cleanup."""
        timestamp = time.time()
        
        # Remove oldest event if at capacity
        if len(self.events) >= self.max_events:
            old_event = self.events[0]
            self.event_counts[old_event['path']] -= 1
            if self.event_counts[old_event['path']] == 0:
                del self.event_counts[old_event['path']]
        
        # Add new event
        event = {
            'type': event_type,
            'path': path,
            'timestamp': timestamp
        }
        self.events.append(event)
        self.event_counts[path] += 1
    
    def get_hot_files(self, top_n: int = 10) -> List[tuple]:
        """Get most frequently modified files."""
        return heapq.nlargest(
            top_n,
            self.event_counts.items(),
            key=lambda x: x[1]
        )
```

## Shell Utilities (watchmedo)

```bash
# Watch directory and run command on changes
watchmedo shell-command \
    --patterns="*.py" \
    --recursive \
    --command='echo "${watch_src_path} was modified"' \
    /path/to/watch

# Auto-restart a process on file changes
watchmedo auto-restart \
    --directory=. \
    --pattern="*.py" \
    --recursive \
    -- python app.py

# Log all events
watchmedo log \
    --recursive \
    --verbose \
    /path/to/watch

# Generate tricks configuration
watchmedo tricks-generate-yaml \
    --append \
    --python-tricks \
    watchdog.yaml
```