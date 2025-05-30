# MCP Server Benchmark Suite

This benchmark suite validates that all MCP Server implementations meet the performance requirements specified in `/architecture/performance_requirements.md`.

## Performance Requirements (SLOs)

- **Symbol Lookup**: < 100ms (p95)
- **Search Performance**: < 500ms (p95)
- **Code Search**: < 200ms (p95)
- **Index Status**: < 50ms (p95)
- **Indexing Speed**: 10,000 files/minute
- **Memory Usage**: < 2GB for 100K files

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