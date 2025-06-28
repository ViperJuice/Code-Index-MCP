"""
Comparison tests for MCP Server vs Direct approaches.

This package contains comprehensive tests that compare:
- Token usage between MCP and direct file operations
- Performance metrics (latency, throughput)
- Result quality (precision, recall)
- Resource utilization (memory, CPU)
"""

from .test_mcp_vs_direct import (
    MCPComparison,
    ComparisonResult,
    TokenUsage,
    PerformanceMetrics,
    SearchResult,
    TokenCounter,
    DirectSearcher
)

__all__ = [
    'MCPComparison',
    'ComparisonResult', 
    'TokenUsage',
    'PerformanceMetrics',
    'SearchResult',
    'TokenCounter',
    'DirectSearcher'
]