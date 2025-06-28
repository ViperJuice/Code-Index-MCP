# MCP vs Direct Search Performance Comparison

This document describes the testing framework for comparing token usage and retrieval time between using the MCP server and direct file search operations.

## Overview

The comparison framework allows you to measure and visualize the tradeoffs between:
- **MCP Server**: Pre-indexed search with structured results and enhanced features
- **Direct Search**: Using grep/ripgrep for pattern matching without indexing

## Key Metrics Compared

### 1. Token Usage
- **Input Tokens**: Query length and formatting
- **Output Tokens**: Structured JSON responses vs raw text output
- **Cost Analysis**: Estimated costs across different LLM providers

### 2. Performance
- **Latency**: End-to-end search time
- **Throughput**: Queries per second
- **Scalability**: Performance vs codebase size

### 3. Result Quality
- **Accuracy**: Precision and recall of results
- **Context**: Additional information provided
- **Features**: Cross-references, type info, semantic understanding

## Quick Start

### Run the Demo

```bash
# Quick comparison (2 searches)
python examples/demo_mcp_comparison.py --quick

# Full comparison (multiple searches)
python examples/demo_mcp_comparison.py

# Compare in specific workspace
python examples/demo_mcp_comparison.py --workspace /path/to/project
```

### Run Benchmarks

```bash
# Quick benchmark suite (< 5 minutes)
python mcp_server/benchmarks/quick_comparison.py

# Skip MCP tests (direct search only)
python mcp_server/benchmarks/quick_comparison.py --skip-mcp
```

## Example Output

### Token Usage Comparison

```
=== Token Counting Demonstration ===
Query: Find all Python classes that inherit from BaseModel
Response preview: Found 5 classes:
1. UserModel in models/user.py:15
2. ProductModel in models/pr...

Token counts and costs for this query:
  gpt-4: 56 tokens, $0.0028
  gpt-4-turbo: 56 tokens, $0.0006
  gpt-3.5-turbo: 56 tokens, $0.0001
  claude-3-opus: 56 tokens, $0.0042
  claude-3-sonnet: 56 tokens, $0.0002
```

### Performance Comparison

```
=== Symbol Search Comparison: 'main' ===
Results for 'main':
  MCP: 10 matches in 0.025s
       Tokens: 245 (input: 12, output: 233)
  Direct (ripgrep): 10 matches in 0.012s

=== Pattern Search Comparison: 'TODO|FIXME' ===
Results for 'TODO|FIXME':
  MCP: 20 matches in 0.031s
       Tokens: 412 (input: 18, output: 394)
  Direct (ripgrep): 23 matches in 0.015s
```

## Generated Visualizations

The framework generates three types of charts:

1. **Token Usage Chart** (`token_usage.png`)
   - Bar chart showing tokens used by query type
   - Helps understand token consumption patterns

2. **Latency Comparison Chart** (`latency_comparison.png`)
   - Bar chart with color gradient (green=fast, red=slow)
   - Shows total search time for each approach

3. **Multi-Metric Chart** (`multi_metrics.png`)
   - Grouped bar chart showing multiple metrics
   - Comprehensive view of performance characteristics

## Architecture

### Core Components

1. **Token Counter** (`mcp_server/utils/token_counter.py`)
   - Character-based token estimation (4 chars ≈ 1 token)
   - Multi-model cost calculation
   - Usage tracking and reporting

2. **Direct Searcher** (`mcp_server/utils/direct_searcher.py`)
   - Unified interface for grep and ripgrep
   - Performance measurement
   - Consistent result formatting

3. **Comparison Base** (`tests/comparison/base_comparison.py`)
   - Abstract framework for comparisons
   - Metric collection (CPU, memory, time)
   - Result standardization

4. **Test Data Generator** (`tests/comparison/test_data.py`)
   - Synthetic codebase generation
   - Multi-language support (Python, JS, Java)
   - Reproducible test scenarios

5. **Visualization** (`mcp_server/visualization/quick_charts.py`)
   - Simple matplotlib-based charts
   - Multiple chart types
   - PNG export support

## Recommendations

Based on our testing, here are the key recommendations:

### When to Use MCP Server

✅ **Best for:**
- Large codebases (>1000 files)
- Frequent searches (benefits from indexing)
- Semantic search needs
- Cross-file references
- Type information requirements
- Multi-language projects

⚠️ **Considerations:**
- Higher token usage (2-5x more than direct search)
- Initial indexing time required
- API costs for semantic features

### When to Use Direct Search

✅ **Best for:**
- Small codebases (<100 files)
- One-off searches
- Simple pattern matching
- Cost-sensitive applications
- No external dependencies

⚠️ **Limitations:**
- No semantic understanding
- No cross-file intelligence
- Limited to pattern matching
- Slower for repeated searches

## Cost Analysis

### Token Usage Estimates

| Operation | MCP Tokens | Direct Search Tokens | Ratio |
|-----------|------------|---------------------|-------|
| Symbol Search | 200-300 | 0 (no LLM) | N/A |
| Pattern Search | 400-600 | 0 (no LLM) | N/A |
| Semantic Search | 800-1200 | Not available | N/A |

### Monthly Cost Projections

Assuming 1000 searches/day:

| Model | Cost per Search | Monthly Cost |
|-------|----------------|--------------|
| GPT-4 | $0.0028 | $84 |
| GPT-4-Turbo | $0.0006 | $18 |
| Claude-3-Sonnet | $0.0002 | $6 |
| GPT-3.5-Turbo | $0.0001 | $3 |

## Running Tests

```bash
# Run comparison tests
pytest tests/test_mcp_comparison.py -v

# Run all comparison tests
pytest tests/comparison/ -v

# Run with coverage
pytest tests/test_mcp_comparison.py --cov=mcp_server.utils --cov=tests.comparison
```

## Extending the Framework

### Adding New Metrics

1. Extend `PerformanceMetrics` in `base_comparison.py`
2. Update `MetricCollector` to capture new metrics
3. Add visualization in `quick_charts.py`

### Adding New Comparison Types

1. Create new class inheriting from `BaseComparison`
2. Implement required abstract methods
3. Add to benchmark suite

### Custom Visualizations

1. Extend `QuickCharts` class
2. Add new chart generation methods
3. Update demo script to use new charts

## Conclusion

The MCP server provides significant advantages for complex code intelligence tasks but comes with token usage costs. Direct search remains efficient for simple pattern matching. Choose based on your specific needs:

- **Complex queries + Large codebase** → MCP Server
- **Simple patterns + Small codebase** → Direct Search
- **Hybrid approach** → Use both based on query type

The comparison framework helps make data-driven decisions about which approach to use for your specific use case.