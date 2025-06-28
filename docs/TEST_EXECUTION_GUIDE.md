# MCP vs Native Performance Test Execution Guide

## Overview

This guide explains how to execute the performance comparison tests between MCP and Native search tools using Claude Code agents via the Task tool.

## Test Configuration

- **Total Tests**: 48 (24 MCP, 24 Native)
- **Repositories**: 4 (go_gin, python_django, javascript_react, rust_tokio)
- **Categories**: Symbol, Content, Navigation queries
- **Tests per Repository**: 12 (6 MCP, 6 Native)

## Quick Start

### 1. Check Test Status

```bash
# List all test batches
python scripts/run_test_batch.py --list

# Check specific batch status
python scripts/run_test_batch.py --status go_gin
```

### 2. Get Next Test Prompt

```bash
# Get the next test for a specific batch
python scripts/run_test_batch.py --next go_gin
```

### 3. Execute Test with Task Tool

Copy the prompt provided and use it with the Task tool to execute the test.

### 4. Save Test Results

After the Task tool completes, save the JSON result:

```bash
# Save result for specific test
python scripts/save_test_result.py <test_id> --batch <batch_name> --json '<JSON_RESULT>'

# Or save from file
python scripts/save_test_result.py go_gin_0_mcp --batch go_gin --file result.json
```

### 5. View Progress

```bash
# Generate summary report
python scripts/run_test_batch.py --summary

# Save report to file
python scripts/run_test_batch.py --save-summary report.txt
```

## Test Execution Workflow

1. **Start with a repository batch**
   ```bash
   python scripts/run_test_batch.py --status go_gin
   ```

2. **Execute tests in pairs** (MCP vs Native for same query)
   - Get MCP test prompt
   - Execute with Task tool
   - Save result
   - Get Native test prompt for same query
   - Execute with Task tool
   - Save result

3. **Monitor progress**
   - Each batch has a checkpoint file tracking completion
   - Results are saved with timestamps
   - Can resume from any point

## Test Prompt Structure

### MCP Test Prompts
- Use ONLY MCP tools: `mcp__code-index-mcp__symbol_lookup`, `mcp__code-index-mcp__search_code`
- Repository name provided for context
- Focus on tool efficiency

### Native Test Prompts
- Use ONLY native tools: `grep`, `find`, `glob`, `ls`, `read`
- Working directory provided
- No MCP tools allowed

## Expected Output Format

Each test should return JSON with:
```json
{
  "query": "The search query",
  "mode": "mcp" or "native",
  "tools_used": ["list", "of", "tools"],
  "tool_calls": {"tool_name": count},
  "results_found": number,
  "execution_time_ms": milliseconds,
  "token_estimate": number,
  "success": true/false,
  "error": null or error message
}
```

## Current Progress

As of the latest execution:
- **go_gin**: 2/12 tests completed (16.7%)
- **python_django**: 0/12 tests completed (0%)
- **javascript_react**: 0/12 tests completed (0%)
- **rust_tokio**: 0/12 tests completed (0%)

## Initial Results

From the first 2 tests on go_gin:

| Metric | MCP | Native |
|--------|-----|--------|
| Execution Time | 3,500ms | 12,000ms |
| Token Usage | 8,500 | 3,500 |
| Success | ✓ | ✗ |

**Key Finding**: MCP was 3.4x faster and successfully found the answer, despite using more tokens.

## Tips for Efficient Testing

1. **Batch Execution**: Run tests for one repository at a time
2. **Pair Testing**: Always run MCP and Native versions of the same query together
3. **Save Frequently**: Results are saved individually, no batch loss
4. **Monitor Tokens**: Keep track of token usage for cost analysis

## Troubleshooting

- **Test Failed**: Check error message in result JSON
- **Wrong Directory**: Ensure you're in `/workspaces/Code-Index-MCP`
- **Missing Checkpoint**: Checkpoint files are created automatically
- **Duplicate Tests**: System tracks completed tests, won't duplicate

## Next Steps

After all tests are complete:
1. Run comprehensive analysis: `python scripts/run_comprehensive_performance_test.py --analyze`
2. Generate visualizations: `python scripts/create_performance_visualization.py`
3. Create final report with recommendations