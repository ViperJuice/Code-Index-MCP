"""
Indexer package for coordinating code indexing operations.

This package provides the core indexing engine and related components
for efficiently indexing and searching code repositories.
"""

from .index_engine import (
    BatchIndexResult,
    IndexEngine,
    IndexOptions,
    IndexProgress,
    IndexResult,
    IndexTask,
)
from .query_optimizer import Query, QueryType

__all__ = [
    # Index Engine
    "IndexEngine",
    "IndexResult",
    "BatchIndexResult",
    "IndexOptions",
    "IndexProgress",
    "IndexTask",
    # Query Optimizer
    "Query",
    "QueryType",
]
