# MCP Server Benchmark Suite

This benchmark suite provides comprehensive performance testing and validation for the MCP Server, implementing the IBenchmarkRunner and IPerformanceMonitor interfaces to ensure all components meet the performance requirements specified in ROADMAP.md.

## Performance Requirements Validation ✅

| Metric | Target | Implementation Status |
|--------|--------|----------------------|
| Symbol Lookup | < 100ms (p95) | ✅ Automated validation |
| Semantic Search | < 500ms (p95) | ✅ Automated validation |
| Indexing Speed | 10K files/minute | ✅ Throughput measurement |
| Memory Usage | < 2GB for 100K files | ✅ Memory extrapolation |

## Interface Compliance

The benchmark framework implements multiple interface contracts:

### IBenchmarkRunner (BenchmarkRunner)
- `run_indexing_benchmark()` - Validates indexing throughput
- `run_search_benchmark()` - Tests search performance across query types
- `run_memory_benchmark()` - Measures memory usage at scale
- `generate_benchmark_report()` - Creates comprehensive performance reports

### IPerformanceMonitor & IIndexPerformanceMonitor (BenchmarkSuite)
- Real-time timer management with `start_timer()` / `stop_timer()`
- Performance metrics collection with `record_indexing_time()` / `record_search_time()`
- Statistical analysis with `get_performance_metrics()` and `get_slow_queries()`
- SLO validation with `validate_performance_requirements()`

## Implementation Components

### Index Engine Performance Features
- **Incremental Updates**: File hash-based change detection using MD5
- **Batch Processing**: Configurable concurrency with semaphore-based rate limiting
- **Progress Tracking**: Throughput calculation and task monitoring
- **Cache Management**: File metadata and hash caching for performance

### Query Optimizer Performance Features
- **Multi-factor Cost Model**: CPU, I/O, and memory cost estimation
- **Query Selectivity**: Statistics-based filter optimization
- **Index Selection**: Cost-based index usage decisions
- **Result Caching**: Automatic cache key generation for expensive queries

### Supported Query Types for Benchmarking
- **Symbol Search**: Functions, classes, variables lookup
- **Text Search**: Full-text search with SQLite FTS5
- **Fuzzy Search**: Approximate matching with trigrams
- **Semantic Search**: Vector-based similarity (when available)
- **Reference Search**: Symbol usage location finding

## Running Benchmarks

### Using pytest-benchmark

Run individual benchmarks with pytest:

```bash
# Run all benchmarks
pytest tests/test_benchmarks.py -v --benchmark-only

# Run specific benchmark group
pytest tests/test_benchmarks.py -k "symbol_lookup" --benchmark-only

# Generate detailed benchmark report
pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave
```

### Using the Standalone Runner

Run the complete benchmark suite:

```bash
# Quick benchmarks
python -m mcp_server.benchmarks.run_benchmarks --quick

# Full benchmark suite
python -m mcp_server.benchmarks.run_benchmarks --full

# Compare with previous results
python -m mcp_server.benchmarks.run_benchmarks --compare

# Specific plugins only
python -m mcp_server.benchmarks.run_benchmarks --plugins python,javascript
```

### Programmatic Usage

```python
from mcp_server.benchmarks import BenchmarkSuite, BenchmarkRunner
from mcp_server.plugins.python_plugin import PythonPlugin
from mcp_server.plugins.js_plugin import JavaScriptPlugin

# Create plugins
plugins = [PythonPlugin(), JavaScriptPlugin()]

# Run benchmarks
runner = BenchmarkRunner()
result = runner.run_benchmarks(plugins)

# Check if SLOs are met
if all(result.validations.values()):
    print("All performance requirements met!")
else:
    print("Some requirements failed:", result.validations)
```

## Benchmark Components

### BenchmarkSuite

The main benchmark suite that runs performance tests:

- `benchmark_symbol_lookup()`: Tests symbol definition lookup performance
- `benchmark_search()`: Tests fuzzy and semantic search performance
- `benchmark_indexing()`: Measures file indexing throughput
- `benchmark_memory_usage()`: Tracks memory consumption for different codebase sizes
- `benchmark_cache_performance()`: Evaluates cache hit/miss performance

### BenchmarkRunner

Orchestrates benchmark execution and reporting:

- Runs complete benchmark suites
- Saves results with history tracking
- Detects performance regressions
- Generates HTML and text reports
- Exports CI-friendly metrics

### PerformanceMetrics

Tracks performance measurements:

- Timing samples (min, max, mean, median, p95, p99)
- Memory usage
- CPU utilization
- SLO validation

## Output Reports

The benchmark suite generates several reports:

1. **HTML Report** (`benchmark_report.html`):
   - Visual performance metrics
   - SLO validation status
   - Regression analysis
   - Historical trends

2. **Text Summary** (`benchmark_summary.txt`):
   - Console-friendly summary
   - Key metrics and validation results

3. **JSON Results** (`benchmark_YYYYMMDD_HHMMSS.json`):
   - Complete benchmark data
   - Machine-readable format
   - Historical tracking

4. **CI Metrics** (`ci_metrics.json`):
   - Simplified metrics for CI/CD
   - Pass/fail status
   - Key performance indicators

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run Performance Benchmarks
  run: |
    python -m mcp_server.benchmarks.run_benchmarks --compare
    
- name: Upload Benchmark Results
  uses: actions/upload-artifact@v3
  with:
    name: benchmark-results
    path: benchmark_results/
    
- name: Check Performance SLOs
  run: |
    python -c "
    import json
    with open('benchmark_results/ci_metrics.json') as f:
        data = json.load(f)
    if not data['passed']:
        print('Performance requirements not met!')
        exit(1)
    "
```

## Performance Tips

1. **Warm-up Runs**: The suite includes warm-up iterations to stabilize measurements
2. **Statistical Significance**: Uses p95/p99 percentiles instead of averages
3. **Isolation**: Run benchmarks on idle systems for consistent results
4. **Regression Detection**: Automatically compares with previous runs (10% threshold)

## Troubleshooting

### High Variance in Results

- Ensure system is idle during benchmarks
- Increase iteration counts for more stable results
- Check for background processes affecting performance

### Memory Measurements

- Memory usage includes Python interpreter overhead
- Use relative measurements between runs
- Force garbage collection between tests

### Regression Detection

- First run creates baseline (no regression check)
- Subsequent runs compare against history
- Adjust threshold with `threshold_percent` parameter