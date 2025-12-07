"""
Indexing Engine Interfaces

All interfaces related to code indexing, search optimization, and semantic analysis.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .plugin_interfaces import (
    IndexedFile,
    SearchResult,
    SymbolDefinition,
    SymbolReference,
)
from .shared_interfaces import IAsyncRepository, IndexStatus, IObservable, Result

# ========================================
# Indexing Data Types
# ========================================


@dataclass
class IndexEntry:
    """Single index entry"""

    file_path: str
    symbol: str
    symbol_type: str
    line: int
    column: int
    content_hash: str
    last_indexed: datetime
    metadata: Dict[str, Any] = None


@dataclass
class IndexStatistics:
    """Index statistics"""

    total_files: int
    total_symbols: int
    index_size_bytes: int
    last_update: datetime
    index_health: str
    plugin_stats: Dict[str, Dict[str, int]]


@dataclass
class SearchQuery:
    """Search query with options"""

    query: str
    search_type: str  # exact, fuzzy, semantic, regex
    file_patterns: List[str] = None
    language_filters: List[str] = None
    symbol_types: List[str] = None
    max_results: int = 100
    include_context: bool = True
    case_sensitive: bool = False


@dataclass
class IndexingTask:
    """Task for indexing operations"""

    task_id: str
    file_path: str
    operation: str  # index, reindex, delete
    priority: int
    created_at: datetime
    status: IndexStatus
    progress: float = 0.0
    error_message: Optional[str] = None


@dataclass
class SemanticMatch:
    """Semantic search match"""

    symbol: str
    file_path: str
    similarity_score: float
    embedding_vector: List[float]
    context: str
    metadata: Dict[str, Any] = None


# ========================================
# Core Indexing Interfaces
# ========================================


class IIndexEngine(IObservable):
    """Main interface for the indexing engine"""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> Result[None]:
        """Initialize the indexing engine"""

    @abstractmethod
    async def shutdown(self) -> Result[None]:
        """Shutdown the indexing engine"""

    @abstractmethod
    async def index_file(self, file_path: str, force: bool = False) -> Result[IndexedFile]:
        """Index a single file"""

    @abstractmethod
    async def index_directory(
        self, directory: str, recursive: bool = True
    ) -> Result[List[IndexedFile]]:
        """Index all files in a directory"""

    @abstractmethod
    async def reindex_file(self, file_path: str) -> Result[IndexedFile]:
        """Reindex a specific file"""

    @abstractmethod
    async def remove_file(self, file_path: str) -> Result[None]:
        """Remove a file from the index"""

    @abstractmethod
    async def search(self, query: SearchQuery) -> Result[List[SearchResult]]:
        """Search the index"""

    @abstractmethod
    async def get_statistics(self) -> Result[IndexStatistics]:
        """Get index statistics"""


class IIndexCoordinator(ABC):
    """Interface for coordinating indexing operations across plugins"""

    @abstractmethod
    async def coordinate_indexing(self, files: List[str]) -> Result[Dict[str, IndexedFile]]:
        """Coordinate indexing across multiple plugins"""

    @abstractmethod
    async def schedule_indexing_task(self, task: IndexingTask) -> Result[str]:
        """Schedule an indexing task"""

    @abstractmethod
    async def get_indexing_status(self, task_id: str) -> Result[IndexingTask]:
        """Get status of an indexing task"""

    @abstractmethod
    async def cancel_indexing_task(self, task_id: str) -> Result[None]:
        """Cancel an indexing task"""

    @abstractmethod
    async def get_pending_tasks(self) -> Result[List[IndexingTask]]:
        """Get list of pending indexing tasks"""


class IParseCoordinator(ABC):
    """Interface for coordinating parsing operations"""

    @abstractmethod
    async def parse_file(
        self, file_path: str, content: Optional[str] = None
    ) -> Result[List[SymbolDefinition]]:
        """Parse a file using appropriate plugins"""

    @abstractmethod
    async def parse_content(self, content: str, language: str) -> Result[List[SymbolDefinition]]:
        """Parse content for a specific language"""

    @abstractmethod
    async def batch_parse(self, files: List[str]) -> Result[Dict[str, List[SymbolDefinition]]]:
        """Parse multiple files in batch"""

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""


# ========================================
# Search Interfaces
# ========================================


class ISearchEngine(ABC):
    """Interface for search operations"""

    @abstractmethod
    async def search_symbols(
        self, query: str, options: Dict[str, Any]
    ) -> Result[List[SymbolDefinition]]:
        """Search for symbols"""

    @abstractmethod
    async def search_references(
        self, symbol: str, options: Dict[str, Any]
    ) -> Result[List[SymbolReference]]:
        """Search for symbol references"""

    @abstractmethod
    async def search_content(
        self, query: str, options: Dict[str, Any]
    ) -> Result[List[SearchResult]]:
        """Search file content"""

    @abstractmethod
    async def search_fuzzy(self, query: str, options: Dict[str, Any]) -> Result[List[SearchResult]]:
        """Perform fuzzy search"""

    @abstractmethod
    async def search_semantic(
        self, query: str, options: Dict[str, Any]
    ) -> Result[List[SemanticMatch]]:
        """Perform semantic search"""


class IQueryOptimizer(ABC):
    """Interface for optimizing search queries"""

    @abstractmethod
    def optimize_query(self, query: SearchQuery) -> SearchQuery:
        """Optimize a search query"""

    @abstractmethod
    def estimate_cost(self, query: SearchQuery) -> float:
        """Estimate the cost of executing a query"""

    @abstractmethod
    def suggest_improvements(self, query: SearchQuery) -> List[str]:
        """Suggest query improvements"""

    @abstractmethod
    def get_query_plan(self, query: SearchQuery) -> Dict[str, Any]:
        """Get execution plan for a query"""


class ISearchPlanner(ABC):
    """Interface for planning search execution"""

    @abstractmethod
    def create_execution_plan(self, query: SearchQuery) -> Dict[str, Any]:
        """Create an execution plan for a search query"""

    @abstractmethod
    def select_indexes(self, query: SearchQuery) -> List[str]:
        """Select appropriate indexes for a query"""

    @abstractmethod
    def estimate_selectivity(self, query: SearchQuery) -> float:
        """Estimate query selectivity"""


# ========================================
# Indexing Strategy Interfaces
# ========================================


class IFuzzyIndexer(ABC):
    """Interface for fuzzy text indexing"""

    @abstractmethod
    async def build_fuzzy_index(self, content: str, file_path: str) -> Result[None]:
        """Build fuzzy index for content"""

    @abstractmethod
    async def search_fuzzy(self, query: str, max_distance: int = 2) -> Result[List[SearchResult]]:
        """Search with fuzzy matching"""

    @abstractmethod
    async def get_suggestions(self, partial_query: str, limit: int = 10) -> Result[List[str]]:
        """Get search suggestions"""

    @abstractmethod
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""


class ISemanticIndexer(ABC):
    """Interface for semantic indexing with embeddings"""

    @abstractmethod
    async def generate_embeddings(
        self, content: str, metadata: Dict[str, Any] = None
    ) -> Result[List[float]]:
        """Generate embeddings for content"""

    @abstractmethod
    async def index_embeddings(
        self, embeddings: List[float], content: str, file_path: str
    ) -> Result[None]:
        """Index embeddings"""

    @abstractmethod
    async def search_similar(
        self, query_embedding: List[float], top_k: int = 10
    ) -> Result[List[SemanticMatch]]:
        """Search for similar content using embeddings"""

    @abstractmethod
    async def update_embeddings(self, file_path: str, content: str) -> Result[None]:
        """Update embeddings for a file"""


class ITrigramSearcher(ABC):
    """Interface for trigram-based search"""

    @abstractmethod
    async def build_trigram_index(self, content: str, file_path: str) -> Result[None]:
        """Build trigram index"""

    @abstractmethod
    async def search_trigrams(self, query: str) -> Result[List[SearchResult]]:
        """Search using trigrams"""

    @abstractmethod
    def extract_trigrams(self, text: str) -> Set[str]:
        """Extract trigrams from text"""


# ========================================
# Index Management Interfaces
# ========================================


class IIndexManager(ABC):
    """Interface for managing indexes"""

    @abstractmethod
    async def create_index(
        self, index_name: str, index_type: str, config: Dict[str, Any]
    ) -> Result[None]:
        """Create a new index"""

    @abstractmethod
    async def drop_index(self, index_name: str) -> Result[None]:
        """Drop an index"""

    @abstractmethod
    async def rebuild_index(self, index_name: str) -> Result[None]:
        """Rebuild an index"""

    @abstractmethod
    async def optimize_index(self, index_name: str) -> Result[None]:
        """Optimize an index"""

    @abstractmethod
    async def get_index_info(self, index_name: str) -> Result[Dict[str, Any]]:
        """Get information about an index"""

    @abstractmethod
    async def list_indexes(self) -> Result[List[str]]:
        """List all indexes"""


class IIndexStore(IAsyncRepository[IndexEntry]):
    """Interface for storing index data"""

    @abstractmethod
    async def store_symbols(self, file_path: str, symbols: List[SymbolDefinition]) -> Result[None]:
        """Store symbols for a file"""

    @abstractmethod
    async def get_symbols(self, file_path: str) -> Result[List[SymbolDefinition]]:
        """Get symbols for a file"""

    @abstractmethod
    async def delete_symbols(self, file_path: str) -> Result[None]:
        """Delete symbols for a file"""

    @abstractmethod
    async def search_symbols(
        self, query: str, filters: Dict[str, Any]
    ) -> Result[List[SymbolDefinition]]:
        """Search symbols with filters"""


# ========================================
# Change Detection Interfaces
# ========================================


class IChangeDetector(ABC):
    """Interface for detecting file changes"""

    @abstractmethod
    async def detect_changes(self, file_path: str) -> Result[bool]:
        """Detect if a file has changed since last index"""

    @abstractmethod
    async def get_file_hash(self, file_path: str) -> Result[str]:
        """Get hash of a file"""

    @abstractmethod
    async def store_file_hash(self, file_path: str, hash_value: str) -> Result[None]:
        """Store file hash"""

    @abstractmethod
    async def get_modified_files(self, since: datetime) -> Result[List[str]]:
        """Get files modified since a timestamp"""


class IIncrementalIndexer(ABC):
    """Interface for incremental indexing"""

    @abstractmethod
    async def process_file_change(self, file_path: str, change_type: str) -> Result[None]:
        """Process a file change (created, modified, deleted)"""

    @abstractmethod
    async def get_incremental_updates(self, since: datetime) -> Result[List[IndexEntry]]:
        """Get incremental updates since a timestamp"""

    @abstractmethod
    async def apply_incremental_update(self, update: IndexEntry) -> Result[None]:
        """Apply an incremental update"""


# ========================================
# Reranking Interfaces
# ========================================


@dataclass
class RerankResult:
    """Result from reranking operation"""

    original_result: SearchResult
    rerank_score: float
    original_rank: int
    new_rank: int
    explanation: Optional[str] = None


class IReranker(ABC):
    """Interface for reranking search results"""

    @abstractmethod
    async def rerank(
        self, query: str, results: List[SearchResult], top_k: Optional[int] = None
    ) -> Result[List[RerankResult]]:
        """Rerank search results based on relevance to query"""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> Result[None]:
        """Initialize the reranker with configuration"""

    @abstractmethod
    async def shutdown(self) -> Result[None]:
        """Shutdown the reranker and clean up resources"""

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get reranker capabilities and metadata"""


class IRerankerFactory(ABC):
    """Factory for creating reranker instances"""

    @abstractmethod
    def create_reranker(self, reranker_type: str, config: Dict[str, Any]) -> IReranker:
        """Create a reranker instance"""

    @abstractmethod
    def get_available_rerankers(self) -> List[str]:
        """Get list of available reranker types"""


# ========================================
# Performance Monitoring Interfaces
# ========================================


class IIndexPerformanceMonitor(ABC):
    """Interface for monitoring index performance"""

    @abstractmethod
    async def record_indexing_time(self, file_path: str, time_taken: float) -> None:
        """Record time taken to index a file"""

    @abstractmethod
    async def record_search_time(self, query: str, time_taken: float, result_count: int) -> None:
        """Record search performance"""

    @abstractmethod
    async def get_performance_metrics(self) -> Result[Dict[str, Any]]:
        """Get performance metrics"""

    @abstractmethod
    async def get_slow_queries(self, threshold: float) -> Result[List[Dict[str, Any]]]:
        """Get queries that took longer than threshold"""


class IBenchmarkRunner(ABC):
    """Interface for running performance benchmarks"""

    @abstractmethod
    async def run_indexing_benchmark(self, file_paths: List[str]) -> Result[Dict[str, Any]]:
        """Run indexing performance benchmark"""

    @abstractmethod
    async def run_search_benchmark(self, queries: List[str]) -> Result[Dict[str, Any]]:
        """Run search performance benchmark"""

    @abstractmethod
    async def run_memory_benchmark(self, file_count: int) -> Result[Dict[str, Any]]:
        """Run memory usage benchmark"""

    @abstractmethod
    async def generate_benchmark_report(self) -> Result[str]:
        """Generate benchmark report"""
