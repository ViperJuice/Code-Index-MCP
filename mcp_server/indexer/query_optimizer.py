"""
Query Optimizer for optimizing search queries and planning execution.

This module provides query optimization capabilities including cost estimation,
index selection, and search plan generation.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries supported by the optimizer."""
    SYMBOL_SEARCH = "symbol_search"
    TEXT_SEARCH = "text_search"
    FUZZY_SEARCH = "fuzzy_search"
    SEMANTIC_SEARCH = "semantic_search"
    REFERENCE_SEARCH = "reference_search"
    DEFINITION_SEARCH = "definition_search"


class IndexType(Enum):
    """Types of indexes available for query execution."""
    BTREE = "btree"
    FTS = "fts"
    TRIGRAM = "trigram"
    SEMANTIC = "semantic"
    HASH = "hash"


@dataclass
class Query:
    """Represents a search query."""
    query_type: QueryType
    text: str
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 20
    offset: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryCost:
    """Cost estimation for a query."""
    estimated_rows: int
    estimated_time_ms: float
    cpu_cost: float
    io_cost: float
    memory_cost: float
    total_cost: float
    confidence: float = 1.0  # 0.0 to 1.0


@dataclass
class IndexChoice:
    """Represents the choice of index for a query."""
    index_type: IndexType
    index_name: str
    selectivity: float
    cost: float
    reason: str


@dataclass
class OptimizedQuery:
    """An optimized version of a query."""
    original: Query
    rewritten_text: str
    index_choice: IndexChoice
    filters_order: List[str]
    use_cache: bool
    estimated_cost: QueryCost
    optimization_notes: List[str] = field(default_factory=list)


@dataclass
class SearchPlan:
    """Execution plan for a search query."""
    query: Query
    steps: List[Dict[str, Any]] = field(default_factory=list)
    index_choice: Optional[IndexChoice] = None
    estimated_cost: Optional[QueryCost] = None
    cache_key: Optional[str] = None


@dataclass
class IndexSuggestion:
    """Suggestion for creating a new index."""
    index_type: IndexType
    columns: List[str]
    estimated_benefit: float
    creation_cost: float
    maintenance_cost: float
    reason: str


@dataclass
class PerformanceReport:
    """Performance analysis report for a query."""
    query: Query
    actual_time_ms: float
    estimated_time_ms: float
    actual_rows: int
    estimated_rows: int
    index_used: str
    bottlenecks: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class SearchStatistics:
    """Search performance statistics."""
    total_queries: int = 0
    avg_response_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    index_usage: Dict[str, int] = field(default_factory=dict)
    query_patterns: Dict[str, int] = field(default_factory=dict)
    performance_trends: List[float] = field(default_factory=list)


class QueryOptimizer:
    """
    Query optimizer that provides cost estimation and query optimization.
    
    This class implements both IQueryOptimizer and ISearchPlanner interfaces
    from the architecture specification.
    """
    
    def __init__(self, storage=None):
        """
        Initialize the query optimizer.
        
        Args:
            storage: Optional storage backend for statistics
        """
        self.storage = storage
        self._query_cache: Dict[str, Any] = {}
        self._statistics = SearchStatistics()
        self._cost_model = CostModel()
        self._index_stats: Dict[str, Dict[str, Any]] = {}
        
        # Initialize with default index statistics
        self._initialize_index_stats()
    
    def _initialize_index_stats(self) -> None:
        """Initialize default index statistics."""
        self._index_stats = {
            "symbols_name": {
                "type": IndexType.BTREE,
                "cardinality": 10000,
                "selectivity": 0.01,
                "scan_cost": 1.0
            },
            "symbols_kind": {
                "type": IndexType.BTREE,
                "cardinality": 10,
                "selectivity": 0.1,
                "scan_cost": 0.5
            },
            "fts_symbols": {
                "type": IndexType.FTS,
                "cardinality": 10000,
                "selectivity": 0.05,
                "scan_cost": 2.0
            },
            "symbol_trigrams": {
                "type": IndexType.TRIGRAM,
                "cardinality": 50000,
                "selectivity": 0.02,
                "scan_cost": 1.5
            }
        }
    
    # ========================================
    # IQueryOptimizer Implementation
    # ========================================
    
    def optimize_query(self, query: Query) -> OptimizedQuery:
        """
        Optimize a query for better performance.
        
        Args:
            query: Query to optimize
            
        Returns:
            OptimizedQuery with optimization applied
        """
        # Rewrite query text for better matching
        rewritten_text = self._rewrite_query_text(query)
        
        # Choose best index
        index_choice = self._choose_index(query)
        
        # Optimize filter order
        filters_order = self._optimize_filter_order(query)
        
        # Determine cache usage
        use_cache = self._should_use_cache(query)
        
        # Estimate cost
        estimated_cost = self.estimate_cost(query)
        
        # Generate optimization notes
        notes = self._generate_optimization_notes(query, index_choice)
        
        return OptimizedQuery(
            original=query,
            rewritten_text=rewritten_text,
            index_choice=index_choice,
            filters_order=filters_order,
            use_cache=use_cache,
            estimated_cost=estimated_cost,
            optimization_notes=notes
        )
    
    def estimate_cost(self, query: Query) -> QueryCost:
        """
        Estimate the cost of executing a query.
        
        Args:
            query: Query to estimate cost for
            
        Returns:
            QueryCost with estimated performance metrics
        """
        # Get base statistics
        base_rows = self._estimate_base_rows(query)
        
        # Apply selectivity for filters
        selectivity = self._calculate_selectivity(query)
        estimated_rows = int(base_rows * selectivity)
        
        # Calculate different cost components
        cpu_cost = self._cost_model.calculate_cpu_cost(query, estimated_rows)
        io_cost = self._cost_model.calculate_io_cost(query, estimated_rows)
        memory_cost = self._cost_model.calculate_memory_cost(query, estimated_rows)
        
        total_cost = cpu_cost + io_cost + memory_cost
        estimated_time_ms = total_cost * 10  # Convert to approximate milliseconds
        
        # Confidence based on available statistics
        confidence = self._calculate_confidence(query)
        
        return QueryCost(
            estimated_rows=estimated_rows,
            estimated_time_ms=estimated_time_ms,
            cpu_cost=cpu_cost,
            io_cost=io_cost,
            memory_cost=memory_cost,
            total_cost=total_cost,
            confidence=confidence
        )
    
    def suggest_indexes(self, query_patterns: List[Query]) -> List[IndexSuggestion]:
        """
        Suggest indexes based on query patterns.
        
        Args:
            query_patterns: List of representative queries
            
        Returns:
            List of index suggestions
        """
        suggestions = []
        
        # Analyze query patterns
        column_usage = defaultdict(int)
        filter_combinations = defaultdict(int)
        
        for query in query_patterns:
            # Track column usage
            for filter_name in query.filters.keys():
                column_usage[filter_name] += 1
            
            # Track filter combinations
            filter_combo = tuple(sorted(query.filters.keys()))
            filter_combinations[filter_combo] += 1
        
        # Suggest indexes for frequently used columns
        for column, usage_count in column_usage.items():
            if usage_count >= len(query_patterns) * 0.3:  # Used in 30% of queries
                benefit = usage_count * 5.0
                creation_cost = 10.0
                maintenance_cost = 1.0
                
                suggestions.append(IndexSuggestion(
                    index_type=IndexType.BTREE,
                    columns=[column],
                    estimated_benefit=benefit,
                    creation_cost=creation_cost,
                    maintenance_cost=maintenance_cost,
                    reason=f"Column '{column}' used in {usage_count} queries"
                ))
        
        # Suggest composite indexes for common filter combinations
        for filter_combo, usage_count in filter_combinations.items():
            if len(filter_combo) > 1 and usage_count >= 2:
                benefit = usage_count * 8.0
                creation_cost = 15.0 * len(filter_combo)
                maintenance_cost = 2.0 * len(filter_combo)
                
                suggestions.append(IndexSuggestion(
                    index_type=IndexType.BTREE,
                    columns=list(filter_combo),
                    estimated_benefit=benefit,
                    creation_cost=creation_cost,
                    maintenance_cost=maintenance_cost,
                    reason=f"Filter combination {filter_combo} used {usage_count} times"
                ))
        
        # Sort by benefit-to-cost ratio
        suggestions.sort(
            key=lambda s: s.estimated_benefit / (s.creation_cost + s.maintenance_cost),
            reverse=True
        )
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def analyze_query_performance(
        self, 
        query: Query, 
        actual_time_ms: float,
        actual_rows: int
    ) -> PerformanceReport:
        """
        Analyze actual query performance against estimates.
        
        Args:
            query: The executed query
            actual_time_ms: Actual execution time
            actual_rows: Actual number of rows returned
            
        Returns:
            PerformanceReport with analysis
        """
        # Get original cost estimate
        estimated_cost = self.estimate_cost(query)
        
        # Identify bottlenecks
        bottlenecks = []
        suggestions = []
        
        # Check if time was much higher than estimated
        time_ratio = actual_time_ms / max(estimated_cost.estimated_time_ms, 1.0)
        if time_ratio > 2.0:
            bottlenecks.append("Query took much longer than estimated")
            suggestions.append("Consider adding an index or rewriting the query")
        
        # Check if row count was much higher than estimated
        row_ratio = actual_rows / max(estimated_cost.estimated_rows, 1)
        if row_ratio > 2.0:
            bottlenecks.append("Returned more rows than estimated")
            suggestions.append("Consider more selective filters")
        
        # Update statistics
        self._statistics.total_queries += 1
        current_avg = self._statistics.avg_response_time_ms
        total = self._statistics.total_queries
        self._statistics.avg_response_time_ms = (
            (current_avg * (total - 1) + actual_time_ms) / total
        )
        
        return PerformanceReport(
            query=query,
            actual_time_ms=actual_time_ms,
            estimated_time_ms=estimated_cost.estimated_time_ms,
            actual_rows=actual_rows,
            estimated_rows=estimated_cost.estimated_rows,
            index_used="unknown",  # Would need to be tracked during execution
            bottlenecks=bottlenecks,
            suggestions=suggestions
        )
    
    # ========================================
    # ISearchPlanner Implementation
    # ========================================
    
    def plan_search(self, query: Query) -> SearchPlan:
        """
        Create an execution plan for a search query.
        
        Args:
            query: Query to plan
            
        Returns:
            SearchPlan with execution steps
        """
        optimized = self.optimize_query(query)
        
        steps = []
        
        # Step 1: Index scan
        steps.append({
            "type": "index_scan",
            "index": optimized.index_choice.index_name,
            "index_type": optimized.index_choice.index_type.value,
            "estimated_rows": optimized.estimated_cost.estimated_rows
        })
        
        # Step 2: Apply filters in optimized order
        if query.filters:
            steps.append({
                "type": "filter",
                "filters": optimized.filters_order,
                "estimated_selectivity": self._calculate_selectivity(query)
            })
        
        # Step 3: Sort/limit if needed
        if query.limit > 0:
            steps.append({
                "type": "limit",
                "limit": query.limit,
                "offset": query.offset
            })
        
        # Generate cache key
        cache_key = self._generate_cache_key(query) if optimized.use_cache else None
        
        return SearchPlan(
            query=query,
            steps=steps,
            index_choice=optimized.index_choice,
            estimated_cost=optimized.estimated_cost,
            cache_key=cache_key
        )
    
    async def execute_plan(self, plan: SearchPlan) -> Dict[str, Any]:
        """
        Execute a search plan.
        
        Args:
            plan: SearchPlan to execute
            
        Returns:
            Dictionary containing search results
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if plan.cache_key and plan.cache_key in self._query_cache:
                self._statistics.cache_hit_rate = (
                    self._statistics.cache_hit_rate * 0.9 + 0.1
                )
                return self._query_cache[plan.cache_key]
            
            # Execute plan steps
            results = await self._execute_plan_steps(plan)
            
            # Cache results if appropriate
            if plan.cache_key:
                self._query_cache[plan.cache_key] = results
                self._statistics.cache_hit_rate = (
                    self._statistics.cache_hit_rate * 0.9
                )
            
            # Update statistics
            execution_time = (time.time() - start_time) * 1000
            self._update_execution_stats(plan, execution_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Error executing search plan: {e}")
            return {"error": str(e), "results": []}
    
    def optimize_plan(self, plan: SearchPlan) -> SearchPlan:
        """
        Optimize an existing search plan.
        
        Args:
            plan: SearchPlan to optimize
            
        Returns:
            Optimized SearchPlan
        """
        # Re-optimize the query
        optimized_query = self.optimize_query(plan.query)
        
        # Create new plan with optimizations
        return self.plan_search(plan.query)
    
    def get_search_statistics(self) -> SearchStatistics:
        """Get current search performance statistics."""
        return self._statistics
    
    # ========================================
    # Private Helper Methods
    # ========================================
    
    def _rewrite_query_text(self, query: Query) -> str:
        """Rewrite query text for better matching."""
        text = query.text.strip()
        
        if query.query_type == QueryType.FUZZY_SEARCH:
            # For fuzzy search, ensure we have reasonable length
            if len(text) < 3:
                return text
            # Could add stemming, normalization here
            return text.lower()
        
        elif query.query_type == QueryType.SYMBOL_SEARCH:
            # For symbol search, handle camelCase and snake_case
            # This is a simplified example
            return text
        
        elif query.query_type == QueryType.TEXT_SEARCH:
            # For FTS, might want to add operators
            if ' ' in text and not any(op in text for op in ['AND', 'OR', 'NOT']):
                # Add AND between words for more precise matching
                words = text.split()
                return ' AND '.join(f'"{word}"' for word in words)
        
        return text
    
    def _choose_index(self, query: Query) -> IndexChoice:
        """Choose the best index for a query."""
        best_choice = None
        best_cost = float('inf')
        
        for index_name, stats in self._index_stats.items():
            cost = self._estimate_index_cost(query, index_name, stats)
            
            if cost < best_cost:
                best_cost = cost
                best_choice = IndexChoice(
                    index_type=stats["type"],
                    index_name=index_name,
                    selectivity=stats["selectivity"],
                    cost=cost,
                    reason=f"Lowest estimated cost: {cost:.2f}"
                )
        
        if best_choice is None:
            # Fallback to table scan
            best_choice = IndexChoice(
                index_type=IndexType.BTREE,
                index_name="table_scan",
                selectivity=1.0,
                cost=1000.0,
                reason="No suitable index found, using table scan"
            )
        
        return best_choice
    
    def _estimate_index_cost(
        self, 
        query: Query, 
        index_name: str, 
        stats: Dict[str, Any]
    ) -> float:
        """Estimate the cost of using a specific index."""
        base_cost = stats["scan_cost"]
        selectivity = stats["selectivity"]
        
        # Adjust cost based on query type
        if query.query_type == QueryType.FUZZY_SEARCH:
            if stats["type"] == IndexType.TRIGRAM:
                return base_cost * 0.5  # Trigram is good for fuzzy
            else:
                return base_cost * 2.0  # Other indexes are less efficient
        
        elif query.query_type == QueryType.TEXT_SEARCH:
            if stats["type"] == IndexType.FTS:
                return base_cost * 0.3  # FTS is excellent for text search
            else:
                return base_cost * 3.0
        
        elif query.query_type == QueryType.SYMBOL_SEARCH:
            if "name" in index_name:
                return base_cost * 0.8  # Name indexes are good for symbols
            else:
                return base_cost * 1.5
        
        return base_cost
    
    def _optimize_filter_order(self, query: Query) -> List[str]:
        """Optimize the order of filter application."""
        if not query.filters:
            return []
        
        # Sort filters by estimated selectivity (most selective first)
        filter_selectivity = []
        
        for filter_name, filter_value in query.filters.items():
            selectivity = self._estimate_filter_selectivity(filter_name, filter_value)
            filter_selectivity.append((filter_name, selectivity))
        
        # Sort by selectivity (lowest first - most selective)
        filter_selectivity.sort(key=lambda x: x[1])
        
        return [name for name, _ in filter_selectivity]
    
    def _estimate_filter_selectivity(self, filter_name: str, filter_value: Any) -> float:
        """Estimate how selective a filter is."""
        # This is a simplified implementation
        # In practice, you'd use actual statistics from the database
        
        if filter_name == "kind":
            return 0.1  # Assuming 10 different kinds
        elif filter_name == "language":
            return 0.2  # Assuming 5 different languages
        elif filter_name == "file_path":
            return 0.01  # File paths are usually very selective
        else:
            return 0.5  # Default moderate selectivity
    
    def _should_use_cache(self, query: Query) -> bool:
        """Determine if query results should be cached."""
        # Cache for expensive queries or common patterns
        if query.query_type in [QueryType.SEMANTIC_SEARCH, QueryType.TEXT_SEARCH]:
            return True
        
        # Cache if no complex filters (static results)
        if not query.filters:
            return True
        
        return False
    
    def _estimate_base_rows(self, query: Query) -> int:
        """Estimate base number of rows for a query type."""
        if query.query_type == QueryType.SYMBOL_SEARCH:
            return 10000  # Typical symbol count
        elif query.query_type == QueryType.TEXT_SEARCH:
            return 5000   # Typical text matches
        elif query.query_type == QueryType.FUZZY_SEARCH:
            return 1000   # Fuzzy matches are typically fewer
        elif query.query_type == QueryType.SEMANTIC_SEARCH:
            return 100    # Semantic matches are even fewer
        else:
            return 1000   # Default
    
    def _calculate_selectivity(self, query: Query) -> float:
        """Calculate overall selectivity for a query."""
        if not query.filters:
            return 1.0
        
        # Multiply selectivities (assuming independence)
        total_selectivity = 1.0
        for filter_name, filter_value in query.filters.items():
            selectivity = self._estimate_filter_selectivity(filter_name, filter_value)
            total_selectivity *= selectivity
        
        return total_selectivity
    
    def _calculate_confidence(self, query: Query) -> float:
        """Calculate confidence in cost estimates."""
        # Start with base confidence
        confidence = 0.8
        
        # Reduce confidence for complex queries
        if len(query.filters) > 3:
            confidence *= 0.8
        
        # Reduce confidence for uncommon query types
        if query.query_type in [QueryType.SEMANTIC_SEARCH]:
            confidence *= 0.6
        
        return max(0.1, confidence)
    
    def _generate_optimization_notes(
        self, 
        query: Query, 
        index_choice: IndexChoice
    ) -> List[str]:
        """Generate human-readable optimization notes."""
        notes = []
        
        notes.append(f"Selected {index_choice.index_type.value} index: {index_choice.index_name}")
        notes.append(f"Estimated selectivity: {index_choice.selectivity:.3f}")
        
        if query.filters:
            notes.append(f"Applied {len(query.filters)} filters")
        
        if query.limit < 100:
            notes.append("Small result set limit - good for performance")
        
        return notes
    
    def _generate_cache_key(self, query: Query) -> str:
        """Generate a cache key for a query."""
        import hashlib
        
        key_parts = [
            query.query_type.value,
            query.text,
            str(sorted(query.filters.items())),
            str(query.limit),
            str(query.offset)
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _execute_plan_steps(self, plan: SearchPlan) -> Dict[str, Any]:
        """Execute the steps in a search plan."""
        # This is a simplified implementation
        # In practice, this would interface with the actual storage/search backends
        
        results = []
        estimated_rows = 0
        
        for step in plan.steps:
            if step["type"] == "index_scan":
                estimated_rows = step.get("estimated_rows", 0)
                # Would perform actual index scan here
                
            elif step["type"] == "filter":
                # Would apply filters here
                pass
                
            elif step["type"] == "limit":
                # Would apply limit here
                pass
        
        return {
            "results": results,
            "total_count": estimated_rows,
            "execution_plan": plan.steps
        }
    
    def _update_execution_stats(self, plan: SearchPlan, execution_time_ms: float) -> None:
        """Update execution statistics."""
        if plan.index_choice:
            index_name = plan.index_choice.index_name
            self._statistics.index_usage[index_name] = (
                self._statistics.index_usage.get(index_name, 0) + 1
            )
        
        # Track query patterns
        pattern = plan.query.query_type.value
        self._statistics.query_patterns[pattern] = (
            self._statistics.query_patterns.get(pattern, 0) + 1
        )
        
        # Track performance trends
        self._statistics.performance_trends.append(execution_time_ms)
        if len(self._statistics.performance_trends) > 100:
            self._statistics.performance_trends = self._statistics.performance_trends[-100:]


class CostModel:
    """Cost model for estimating query execution costs."""
    
    def __init__(self):
        """Initialize cost model with default parameters."""
        self.cpu_cost_per_row = 0.01
        self.io_cost_per_page = 1.0
        self.memory_cost_per_mb = 0.1
        self.rows_per_page = 100
    
    def calculate_cpu_cost(self, query: Query, estimated_rows: int) -> float:
        """Calculate CPU cost for a query."""
        base_cost = estimated_rows * self.cpu_cost_per_row
        
        # Add cost for complex operations
        if query.query_type == QueryType.FUZZY_SEARCH:
            base_cost *= 3.0  # Fuzzy matching is CPU intensive
        elif query.query_type == QueryType.SEMANTIC_SEARCH:
            base_cost *= 5.0  # Semantic search is very CPU intensive
        
        # Add cost for filters
        filter_cost = len(query.filters) * estimated_rows * 0.001
        
        return base_cost + filter_cost
    
    def calculate_io_cost(self, query: Query, estimated_rows: int) -> float:
        """Calculate I/O cost for a query."""
        pages_needed = max(1, estimated_rows // self.rows_per_page)
        return pages_needed * self.io_cost_per_page
    
    def calculate_memory_cost(self, query: Query, estimated_rows: int) -> float:
        """Calculate memory cost for a query."""
        # Estimate memory usage based on result set size
        mb_needed = max(1, estimated_rows * 0.001)  # Assume 1KB per row
        return mb_needed * self.memory_cost_per_mb