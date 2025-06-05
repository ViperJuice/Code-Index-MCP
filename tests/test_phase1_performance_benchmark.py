"""
Performance benchmarks for Phase 1 plugins.

Tests the performance of all 5 plugins (C#, Bash, YAML, JSON, Markdown) 
with various file sizes and complexity levels.
"""

import pytest
import time
import tempfile
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Any

from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.plugin_system.models import PluginSystemConfig
from mcp_server.storage.sqlite_store import SQLiteStore


@pytest.fixture
def performance_database():
    """Create a test SQLite database for performance testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        store = SQLiteStore(db_path)
        yield store
    finally:
        # SQLiteStore doesn't have explicit close method, just cleanup the file
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def performance_plugin_manager(performance_database):
    """Create a plugin manager optimized for performance testing."""
    config = PluginSystemConfig(
        plugin_dirs=[Path(__file__).parent.parent / "mcp_server" / "plugins"],
        auto_discover=True,
        auto_load=True,
        validate_interfaces=False  # Skip validation for performance
    )
    
    manager = PluginManager(config, sqlite_store=performance_database)
    manager.load_plugins()
    yield manager
    manager.shutdown()


class PerformanceBenchmark:
    """Base class for performance benchmarks."""
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
        self.results = {}
    
    def time_operation(self, operation, *args, **kwargs) -> Tuple[Any, float]:
        """Time an operation and return result and duration."""
        start_time = time.perf_counter()
        result = operation(*args, **kwargs)
        end_time = time.perf_counter()
        return result, end_time - start_time
    
    def run_multiple_times(self, operation, times: int = 5, *args, **kwargs) -> Dict[str, float]:
        """Run an operation multiple times and return statistics."""
        durations = []
        results = []
        
        for _ in range(times):
            result, duration = self.time_operation(operation, *args, **kwargs)
            durations.append(duration)
            results.append(result)
        
        return {
            "min_time": min(durations),
            "max_time": max(durations),
            "avg_time": statistics.mean(durations),
            "median_time": statistics.median(durations),
            "std_dev": statistics.stdev(durations) if len(durations) > 1 else 0,
            "total_time": sum(durations),
            "iterations": times
        }


class TestCSharpPluginPerformance:
    """Performance tests for C# plugin."""
    
    def generate_csharp_code(self, size: str) -> str:
        """Generate C# code of different sizes."""
        base_class = '''
using System;
using System.Collections.Generic;
using Microsoft.AspNetCore.Mvc;

namespace PerformanceTest
{
    public class TestClass{class_num}
    {
        public int Id {{ get; set; }}
        public string Name {{ get; set; }}
        
        public void Method{method_num}()
        {
            Console.WriteLine("Method {method_num} called");
        }
        
        public async Task<string> AsyncMethod{method_num}()
        {
            await Task.Delay(100);
            return "Result from async method {method_num}";
        }
    }
}
'''
        
        if size == "small":
            # ~1KB - 1 class, 10 methods
            classes = [base_class.format(class_num=1, method_num=i) for i in range(1, 11)]
            return "\n".join(classes)
        
        elif size == "medium":
            # ~10KB - 5 classes, 20 methods each
            classes = []
            for class_num in range(1, 6):
                class_methods = []
                for method_num in range(1, 21):
                    class_methods.append(base_class.format(class_num=class_num, method_num=method_num))
                classes.extend(class_methods)
            return "\n".join(classes)
        
        elif size == "large":
            # ~100KB - 20 classes, 50 methods each
            classes = []
            for class_num in range(1, 21):
                class_methods = []
                for method_num in range(1, 51):
                    class_methods.append(base_class.format(class_num=class_num, method_num=method_num))
                classes.extend(class_methods)
            return "\n".join(classes)
        
        return ""
    
    def test_csharp_plugin_small_files(self, performance_plugin_manager):
        """Test C# plugin performance with small files."""
        plugins = performance_plugin_manager.get_active_plugins()
        csharp_plugin = None
        
        for plugin_name, plugin_instance in plugins.items():
            if hasattr(plugin_instance, 'get_language') and plugin_instance.get_language() == 'csharp':
                csharp_plugin = plugin_instance
                break
        
        if not csharp_plugin:
            pytest.skip("C# plugin not available")
        
        benchmark = PerformanceBenchmark(performance_plugin_manager)
        small_code = self.generate_csharp_code("small")
        
        # Benchmark indexing
        stats = benchmark.run_multiple_times(
            csharp_plugin.indexFile,
            5,
            "test_small.cs",
            small_code
        )
        
        # Assertions for small files
        assert stats["avg_time"] < 0.5, f"Small file indexing too slow: {stats['avg_time']:.3f}s"
        assert stats["max_time"] < 1.0, f"Small file max time too slow: {stats['max_time']:.3f}s"
        
        print(f"C# Small File Performance: {stats['avg_time']:.3f}s avg, {stats['max_time']:.3f}s max")
    
    def test_csharp_plugin_medium_files(self, performance_plugin_manager):
        """Test C# plugin performance with medium files."""
        plugins = performance_plugin_manager.get_active_plugins()
        csharp_plugin = None
        
        for plugin_name, plugin_instance in plugins.items():
            if hasattr(plugin_instance, 'get_language') and plugin_instance.get_language() == 'csharp':
                csharp_plugin = plugin_instance
                break
        
        if not csharp_plugin:
            pytest.skip("C# plugin not available")
        
        benchmark = PerformanceBenchmark(performance_plugin_manager)
        medium_code = self.generate_csharp_code("medium")
        
        # Benchmark indexing
        stats = benchmark.run_multiple_times(
            csharp_plugin.indexFile,
            3,
            "test_medium.cs",
            medium_code
        )
        
        # Assertions for medium files
        assert stats["avg_time"] < 2.0, f"Medium file indexing too slow: {stats['avg_time']:.3f}s"
        assert stats["max_time"] < 5.0, f"Medium file max time too slow: {stats['max_time']:.3f}s"
        
        print(f"C# Medium File Performance: {stats['avg_time']:.3f}s avg, {stats['max_time']:.3f}s max")
    
    def test_csharp_plugin_large_files(self, performance_plugin_manager):
        """Test C# plugin performance with large files."""
        plugins = performance_plugin_manager.get_active_plugins()
        csharp_plugin = None
        
        for plugin_name, plugin_instance in plugins.items():
            if hasattr(plugin_instance, 'get_language') and plugin_instance.get_language() == 'csharp':
                csharp_plugin = plugin_instance
                break
        
        if not csharp_plugin:
            pytest.skip("C# plugin not available")
        
        benchmark = PerformanceBenchmark(performance_plugin_manager)
        large_code = self.generate_csharp_code("large")
        
        # Benchmark indexing (fewer iterations for large files)
        stats = benchmark.run_multiple_times(
            csharp_plugin.indexFile,
            2,
            "test_large.cs",
            large_code
        )
        
        # Assertions for large files
        assert stats["avg_time"] < 10.0, f"Large file indexing too slow: {stats['avg_time']:.3f}s"
        assert stats["max_time"] < 20.0, f"Large file max time too slow: {stats['max_time']:.3f}s"
        
        print(f"C# Large File Performance: {stats['avg_time']:.3f}s avg, {stats['max_time']:.3f}s max")


class TestBashPluginPerformance:
    """Performance tests for Bash plugin."""
    
    def generate_bash_script(self, size: str) -> str:
        """Generate Bash scripts of different sizes."""
        base_function = '''
function process_item_{func_num}() {{
    local item="$1"
    local output_dir="$2"
    
    echo "Processing item $item in function {func_num}"
    
    # Simulate some work
    for i in {{1..10}}; do
        if [[ "$i" -eq 5 ]]; then
            echo "Halfway through processing $item"
        fi
    done
    
    # Write output
    echo "Result for $item" > "$output_dir/result_{func_num}.txt"
    return 0
}}
'''
        
        script_header = '''#!/bin/bash
# Performance test script
set -euo pipefail

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"
VERBOSE=false

# Utility functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

setup() {
    mkdir -p "$OUTPUT_DIR"
    log "Setup completed"
}
'''
        
        if size == "small":
            # ~1KB - 5 functions
            functions = [base_function.format(func_num=i) for i in range(1, 6)]
            return script_header + "\n".join(functions) + "\n\nsetup\nlog 'Script completed'"
        
        elif size == "medium":
            # ~5KB - 25 functions
            functions = [base_function.format(func_num=i) for i in range(1, 26)]
            return script_header + "\n".join(functions) + "\n\nsetup\nlog 'Script completed'"
        
        elif size == "large":
            # ~20KB - 100 functions
            functions = [base_function.format(func_num=i) for i in range(1, 101)]
            return script_header + "\n".join(functions) + "\n\nsetup\nlog 'Script completed'"
        
        return ""
    
    def test_bash_plugin_performance(self, performance_plugin_manager):
        """Test Bash plugin performance across different file sizes."""
        plugins = performance_plugin_manager.get_active_plugins()
        bash_plugin = None
        
        for plugin_name, plugin_instance in plugins.items():
            if hasattr(plugin_instance, 'get_language') and plugin_instance.get_language() == 'bash':
                bash_plugin = plugin_instance
                break
        
        if not bash_plugin:
            pytest.skip("Bash plugin not available")
        
        benchmark = PerformanceBenchmark(performance_plugin_manager)
        
        # Test small, medium, and large files
        sizes = ["small", "medium", "large"]
        time_limits = [0.5, 2.0, 8.0]  # seconds
        
        for size, time_limit in zip(sizes, time_limits):
            script_content = self.generate_bash_script(size)
            
            stats = benchmark.run_multiple_times(
                bash_plugin.indexFile,
                3,
                f"test_{size}.sh",
                script_content
            )
            
            assert stats["avg_time"] < time_limit, \
                f"Bash {size} file indexing too slow: {stats['avg_time']:.3f}s (limit: {time_limit}s)"
            
            print(f"Bash {size} File Performance: {stats['avg_time']:.3f}s avg")


class TestYAMLPluginPerformance:
    """Performance tests for YAML plugin."""
    
    def generate_yaml_content(self, size: str) -> str:
        """Generate YAML content of different sizes."""
        if size == "small":
            return '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: test-app
  template:
    metadata:
      labels:
        app: test-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
'''
        
        elif size == "medium":
            # Generate multiple services
            services = []
            for i in range(1, 11):
                service = f'''
---
apiVersion: v1
kind: Service
metadata:
  name: service-{i}
  namespace: default
spec:
  selector:
    app: app-{i}
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-{i}
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: app-{i}
  template:
    metadata:
      labels:
        app: app-{i}
    spec:
      containers:
      - name: app-{i}
        image: app-{i}:latest
        ports:
        - containerPort: 8080
        env:
        - name: APP_NAME
          value: "app-{i}"
        - name: PORT
          value: "8080"
'''
                services.append(service)
            return "\n".join(services)
        
        elif size == "large":
            # Generate complex Kubernetes resources
            resources = []
            for i in range(1, 21):
                resource = f'''
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-{i}
  namespace: production
data:
  app.properties: |
    app.name=app-{i}
    app.version=1.0.{i}
    app.environment=production
    database.host=db-{i}.example.com
    database.port=5432
    database.name=app_{i}_db
---
apiVersion: v1
kind: Secret
metadata:
  name: secret-{i}
  namespace: production
type: Opaque
stringData:
  username: user{i}
  password: pass{i}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-{i}
  namespace: production
  labels:
    app: app-{i}
    version: v1.0.{i}
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: app-{i}
  template:
    metadata:
      labels:
        app: app-{i}
        version: v1.0.{i}
    spec:
      containers:
      - name: app-{i}
        image: registry.example.com/app-{i}:v1.0.{i}
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: APP_ID
          value: "{i}"
        envFrom:
        - configMapRef:
            name: config-{i}
        - secretRef:
            name: secret-{i}
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
'''
                resources.append(resource)
            return "\n".join(resources)
        
        return ""
    
    def test_yaml_plugin_performance(self, performance_plugin_manager):
        """Test YAML plugin performance across different file sizes."""
        plugins = performance_plugin_manager.get_active_plugins()
        yaml_plugin = None
        
        for plugin_name, plugin_instance in plugins.items():
            if hasattr(plugin_instance, 'get_language') and plugin_instance.get_language() == 'yaml':
                yaml_plugin = plugin_instance
                break
        
        if not yaml_plugin:
            pytest.skip("YAML plugin not available")
        
        benchmark = PerformanceBenchmark(performance_plugin_manager)
        
        # Test different YAML file sizes
        sizes = ["small", "medium", "large"]
        time_limits = [0.3, 1.5, 6.0]  # seconds
        
        for size, time_limit in zip(sizes, time_limits):
            yaml_content = self.generate_yaml_content(size)
            
            stats = benchmark.run_multiple_times(
                yaml_plugin.indexFile,
                3,
                f"test_{size}.yaml",
                yaml_content
            )
            
            assert stats["avg_time"] < time_limit, \
                f"YAML {size} file indexing too slow: {stats['avg_time']:.3f}s (limit: {time_limit}s)"
            
            print(f"YAML {size} File Performance: {stats['avg_time']:.3f}s avg")


class TestJSONPluginPerformance:
    """Performance tests for JSON plugin."""
    
    def generate_json_content(self, size: str) -> str:
        """Generate JSON content of different sizes."""
        import json
        
        if size == "small":
            data = {
                "name": "test-package",
                "version": "1.0.0",
                "dependencies": {f"package-{i}": f"^{i}.0.0" for i in range(1, 11)},
                "scripts": {f"script-{i}": f"echo 'Running script {i}'" for i in range(1, 6)}
            }
        
        elif size == "medium":
            data = {
                "name": "medium-package",
                "version": "1.0.0",
                "dependencies": {f"package-{i}": f"^{i}.0.0" for i in range(1, 51)},
                "devDependencies": {f"dev-package-{i}": f"^{i}.0.0" for i in range(1, 31)},
                "scripts": {f"script-{i}": f"echo 'Running script {i}'" for i in range(1, 21)},
                "config": {
                    f"setting-{i}": f"value-{i}" for i in range(1, 101)
                }
            }
        
        elif size == "large":
            data = {
                "name": "large-package",
                "version": "1.0.0",
                "dependencies": {f"package-{i}": f"^{i}.0.0" for i in range(1, 201)},
                "devDependencies": {f"dev-package-{i}": f"^{i}.0.0" for i in range(1, 101)},
                "peerDependencies": {f"peer-package-{i}": f"^{i}.0.0" for i in range(1, 51)},
                "scripts": {f"script-{i}": f"echo 'Running script {i}'" for i in range(1, 51)},
                "config": {
                    "database": {
                        f"connection-{i}": {
                            "host": f"db-{i}.example.com",
                            "port": 5432 + i,
                            "database": f"app_{i}_db",
                            "tables": [f"table_{j}" for j in range(1, 21)]
                        } for i in range(1, 21)
                    },
                    "api": {
                        f"endpoint-{i}": {
                            "url": f"https://api-{i}.example.com",
                            "methods": ["GET", "POST", "PUT", "DELETE"],
                            "auth": {"type": "bearer", "token": f"token-{i}"}
                        } for i in range(1, 51)
                    }
                }
            }
        
        return json.dumps(data, indent=2)
    
    def test_json_plugin_performance(self, performance_plugin_manager):
        """Test JSON plugin performance across different file sizes."""
        plugins = performance_plugin_manager.get_active_plugins()
        json_plugin = None
        
        for plugin_name, plugin_instance in plugins.items():
            if hasattr(plugin_instance, 'get_language') and plugin_instance.get_language() == 'json':
                json_plugin = plugin_instance
                break
        
        if not json_plugin:
            pytest.skip("JSON plugin not available")
        
        benchmark = PerformanceBenchmark(performance_plugin_manager)
        
        # Test different JSON file sizes
        sizes = ["small", "medium", "large"]
        time_limits = [0.2, 1.0, 4.0]  # seconds
        
        for size, time_limit in zip(sizes, time_limits):
            json_content = self.generate_json_content(size)
            
            stats = benchmark.run_multiple_times(
                json_plugin.indexFile,
                3,
                f"test_{size}.json",
                json_content
            )
            
            assert stats["avg_time"] < time_limit, \
                f"JSON {size} file indexing too slow: {stats['avg_time']:.3f}s (limit: {time_limit}s)"
            
            print(f"JSON {size} File Performance: {stats['avg_time']:.3f}s avg")


class TestMarkdownPluginPerformance:
    """Performance tests for Markdown plugin."""
    
    def generate_markdown_content(self, size: str) -> str:
        """Generate Markdown content of different sizes."""
        if size == "small":
            return '''
# Test Document

This is a test document for performance testing.

## Section 1

Some content here with **bold** and *italic* text.

```python
def hello_world():
    print("Hello, World!")
```

## Section 2

- [x] Task 1
- [ ] Task 2
- [x] Task 3

[Link to example](https://example.com)

![Image](https://example.com/image.png)
'''
        
        elif size == "medium":
            sections = []
            for i in range(1, 21):
                section = f'''
## Section {i}

This is section {i} with various Markdown elements.

### Subsection {i}.1

Here's some content with formatting:

- **Bold text {i}**
- *Italic text {i}*
- `Inline code {i}`

#### Code Block {i}

```python
def function_{i}():
    """Function {i} documentation."""
    return "Result from function {i}"

class Class{i}:
    def __init__(self):
        self.value = {i}
    
    def method_{i}(self):
        return self.value * {i}
```

#### Math Formula {i}

The formula for calculation {i} is: $y = {i}x + {i}$

Display formula:

$$f(x) = \\sum_{{i=1}}^{{{i}}} x^i$$

#### Task List {i}

- [x] Completed task {i}.1
- [ ] Pending task {i}.2
- [x] Completed task {i}.3
- [ ] Pending task {i}.4

#### Links and References {i}

- [External link {i}](https://example-{i}.com)
- [[Internal link {i}]]
- [Reference link {i}][ref{i}]

[ref{i}]: https://reference-{i}.com "Reference {i}"

#### Table {i}

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value {i}.1 | Value {i}.2 | Value {i}.3 |
| Data {i}.1 | Data {i}.2 | Data {i}.3 |

#### Image {i}

![Image {i}](https://example.com/image{i}.png "Image {i} description")
'''
                sections.append(section)
            
            return f"# Performance Test Document\n\nThis document tests Markdown parsing performance.\n" + "\n".join(sections)
        
        elif size == "large":
            sections = []
            for i in range(1, 51):
                section = f'''
## Chapter {i}: Advanced Topics

This chapter covers advanced topics related to subject {i}.

### {i}.1 Introduction

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

### {i}.2 Technical Details

Here are the technical specifications for component {i}:

#### Configuration {i}

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-{i}
data:
  setting1: "value{i}"
  setting2: "value{i * 2}"
  setting3: "value{i * 3}"
```

#### Implementation {i}

```python
class Implementation{i}:
    """Implementation {i} for handling specific use cases."""
    
    def __init__(self, config):
        self.config = config
        self.value = {i}
    
    def process_{i}(self, data):
        """Process data using algorithm {i}."""
        result = []
        for item in data:
            processed = self._transform_{i}(item)
            result.append(processed)
        return result
    
    def _transform_{i}(self, item):
        """Transform item using method {i}."""
        return item * self.value + {i}
    
    async def async_process_{i}(self, data):
        """Asynchronously process data."""
        import asyncio
        tasks = []
        for item in data:
            task = asyncio.create_task(self._async_transform_{i}(item))
            tasks.append(task)
        return await asyncio.gather(*tasks)
    
    async def _async_transform_{i}(self, item):
        """Asynchronously transform item."""
        await asyncio.sleep(0.1)  # Simulate async work
        return self._transform_{i}(item)
```

### {i}.3 Mathematical Formulas

The relationship between variables in system {i} is described by:

Inline formula: $f_{i}(x) = x^{i} + {i}x + {i * i}$

Complex display formula:

$$\\begin{{align}}
f_{i}(x) &= \\sum_{{j=1}}^{{{i}}} x^j \\\\
g_{i}(x) &= \\prod_{{k=1}}^{{{i}}} (x + k) \\\\
h_{i}(x) &= \\int_0^{{{i}}} f_{i}(t) dt
\\end{{align}}$$

### {i}.4 Task Management

Project {i} tasks:

- [x] Design phase {i} completed
- [x] Implementation phase {i} completed  
- [ ] Testing phase {i} in progress
- [ ] Documentation phase {i} pending
- [ ] Deployment phase {i} not started

Subtasks for phase {i}:

- [x] Setup environment {i}
- [x] Create base structure {i}
- [ ] Implement core features {i}
- [ ] Add error handling {i}
- [ ] Write unit tests {i}
- [ ] Integration testing {i}
- [ ] Performance optimization {i}

### {i}.5 Reference Materials

Important resources for topic {i}:

- [Official Documentation {i}](https://docs.example{i}.com)
- [API Reference {i}](https://api.example{i}.com)
- [Community Forum {i}](https://forum.example{i}.com)
- [[Internal Wiki Page {i}]]
- [Research Paper {i}][paper{i}]

[paper{i}]: https://research.example{i}.com/paper{i}.pdf "Research Paper {i}: Advanced Techniques"

### {i}.6 Data Tables

Performance metrics for system {i}:

| Metric | Value | Unit | Benchmark |
|--------|-------|------|-----------|
| Throughput {i} | {i * 100} | req/sec | {i * 80} |
| Latency {i} | {i * 10} | ms | {i * 15} |
| Memory Usage {i} | {i * 512} | MB | {i * 400} |
| CPU Usage {i} | {i * 2} | % | {i * 3} |
| Disk I/O {i} | {i * 1024} | KB/s | {i * 800} |

### {i}.7 Architecture Diagrams

![System Architecture {i}](https://diagrams.example{i}.com/architecture{i}.png "System {i} Architecture")

![Data Flow {i}](https://diagrams.example{i}.com/dataflow{i}.png "Data Flow for System {i}")
'''
                sections.append(section)
            
            return f"# Comprehensive Performance Test Document\n\nThis document contains extensive Markdown content for performance testing.\n" + "\n".join(sections)
        
        return ""
    
    def test_markdown_plugin_performance(self, performance_plugin_manager):
        """Test Markdown plugin performance across different file sizes."""
        plugins = performance_plugin_manager.get_active_plugins()
        markdown_plugin = None
        
        for plugin_name, plugin_instance in plugins.items():
            if hasattr(plugin_instance, 'get_language') and plugin_instance.get_language() == 'markdown':
                markdown_plugin = plugin_instance
                break
        
        if not markdown_plugin:
            pytest.skip("Markdown plugin not available")
        
        benchmark = PerformanceBenchmark(performance_plugin_manager)
        
        # Test different Markdown file sizes
        sizes = ["small", "medium", "large"]
        time_limits = [0.3, 2.0, 8.0]  # seconds
        
        for size, time_limit in zip(sizes, time_limits):
            markdown_content = self.generate_markdown_content(size)
            
            stats = benchmark.run_multiple_times(
                markdown_plugin.indexFile,
                3,
                f"test_{size}.md",
                markdown_content
            )
            
            assert stats["avg_time"] < time_limit, \
                f"Markdown {size} file indexing too slow: {stats['avg_time']:.3f}s (limit: {time_limit}s)"
            
            print(f"Markdown {size} File Performance: {stats['avg_time']:.3f}s avg")


class TestMultiLanguageProjectPerformance:
    """Test performance with multi-language projects."""
    
    def test_mixed_project_indexing(self, performance_plugin_manager, tmp_path):
        """Test indexing performance on a mixed-language project."""
        # Create test files for each language
        test_files = {
            "Program.cs": '''
using System;
namespace TestApp {
    public class Program {
        public static void Main() {
            Console.WriteLine("Hello World");
        }
    }
}''',
            "build.sh": '''#!/bin/bash
build_app() {
    echo "Building application"
    dotnet build
}
build_app''',
            "deployment.yaml": '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: app
        image: test:latest''',
            "package.json": '''{
  "name": "test-project",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.0"
  }
}''',
            "README.md": '''# Test Project

This is a test project with multiple languages.

## Components

- C# backend
- Shell scripts
- Kubernetes manifests
- Node.js frontend
'''
        }
        
        # Write test files
        for filename, content in test_files.items():
            (tmp_path / filename).write_text(content)
        
        # Get all active plugins
        plugins = performance_plugin_manager.get_active_plugins()
        
        # Time the indexing of all files
        start_time = time.perf_counter()
        
        total_symbols = 0
        processed_files = 0
        
        for filename, content in test_files.items():
            file_path = tmp_path / filename
            
            # Find appropriate plugin
            for plugin_name, plugin_instance in plugins.items():
                if hasattr(plugin_instance, 'supports') and plugin_instance.supports(str(file_path)):
                    shard = plugin_instance.indexFile(str(file_path), content)
                    total_symbols += len(shard.get('symbols', []))
                    processed_files += 1
                    break
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 3.0, f"Multi-language project indexing too slow: {total_time:.3f}s"
        assert processed_files >= 3, f"Too few files processed: {processed_files}"
        assert total_symbols > 10, f"Too few symbols extracted: {total_symbols}"
        
        print(f"Multi-language Project Performance:")
        print(f"  - Total time: {total_time:.3f}s")
        print(f"  - Files processed: {processed_files}")
        print(f"  - Total symbols: {total_symbols}")
        print(f"  - Avg time per file: {total_time/processed_files:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])