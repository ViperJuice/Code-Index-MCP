"""
Storage Interfaces

All interfaces related to data persistence, storage engines, and database operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Union, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from .shared_interfaces import Result, IAsyncRepository, IRepository
from .plugin_interfaces import SymbolDefinition, SymbolReference, IndexedFile

# ========================================
# Storage Data Types
# ========================================


@dataclass
class StorageConfig:
    """Storage configuration"""

    storage_type: str  # sqlite, postgresql, etc.
    connection_string: str
    max_connections: int
    timeout: int
    enable_fts: bool = True
    enable_wal: bool = True
    options: Dict[str, Any] = None


@dataclass
class QueryResult:
    """Database query result"""

    rows: List[Dict[str, Any]]
    total_count: int
    execution_time: float
    metadata: Dict[str, Any] = None


@dataclass
class TableSchema:
    """Database table schema"""

    table_name: str
    columns: List[Dict[str, Any]]
    indexes: List[str]
    constraints: List[str]
    options: Dict[str, Any] = None


@dataclass
class MigrationInfo:
    """Database migration information"""

    version: str
    description: str
    up_script: str
    down_script: str
    applied_at: Optional[datetime] = None


@dataclass
class BackupInfo:
    """Backup information"""

    backup_id: str
    backup_type: str  # full, incremental
    file_path: str
    size_bytes: int
    created_at: datetime
    metadata: Dict[str, Any] = None


# ========================================
# Core Storage Interfaces
# ========================================


class IStorageEngine(ABC):
    """Main storage engine interface"""

    @abstractmethod
    async def initialize(self, config: StorageConfig) -> Result[None]:
        """Initialize the storage engine"""
        pass

    @abstractmethod
    async def shutdown(self) -> Result[None]:
        """Shutdown the storage engine"""
        pass

    @abstractmethod
    async def execute_query(
        self, query: str, params: List[Any] = None
    ) -> Result[QueryResult]:
        """Execute a raw SQL query"""
        pass

    @abstractmethod
    async def execute_many(
        self, query: str, params_list: List[List[Any]]
    ) -> Result[int]:
        """Execute a query with multiple parameter sets"""
        pass

    @abstractmethod
    async def begin_transaction(self) -> Result[str]:
        """Begin a database transaction"""
        pass

    @abstractmethod
    async def commit_transaction(self, transaction_id: str) -> Result[None]:
        """Commit a transaction"""
        pass

    @abstractmethod
    async def rollback_transaction(self, transaction_id: str) -> Result[None]:
        """Rollback a transaction"""
        pass

    @abstractmethod
    async def get_connection_info(self) -> Result[Dict[str, Any]]:
        """Get connection information"""
        pass


class IQueryEngine(ABC):
    """Interface for query execution and optimization"""

    @abstractmethod
    async def select(
        self,
        table: str,
        columns: List[str] = None,
        where: Dict[str, Any] = None,
        order_by: List[str] = None,
        limit: int = None,
        offset: int = None,
    ) -> Result[QueryResult]:
        """Execute a SELECT query"""
        pass

    @abstractmethod
    async def insert(self, table: str, data: Dict[str, Any]) -> Result[int]:
        """Insert a record"""
        pass

    @abstractmethod
    async def update(
        self, table: str, data: Dict[str, Any], where: Dict[str, Any]
    ) -> Result[int]:
        """Update records"""
        pass

    @abstractmethod
    async def delete(self, table: str, where: Dict[str, Any]) -> Result[int]:
        """Delete records"""
        pass

    @abstractmethod
    async def upsert(
        self, table: str, data: Dict[str, Any], conflict_columns: List[str]
    ) -> Result[int]:
        """Insert or update on conflict"""
        pass

    @abstractmethod
    async def bulk_insert(self, table: str, data: List[Dict[str, Any]]) -> Result[int]:
        """Bulk insert records"""
        pass


class ISchemaManager(ABC):
    """Interface for database schema management"""

    @abstractmethod
    async def create_table(self, schema: TableSchema) -> Result[None]:
        """Create a table"""
        pass

    @abstractmethod
    async def drop_table(self, table_name: str) -> Result[None]:
        """Drop a table"""
        pass

    @abstractmethod
    async def alter_table(
        self, table_name: str, changes: List[Dict[str, Any]]
    ) -> Result[None]:
        """Alter a table structure"""
        pass

    @abstractmethod
    async def create_index(
        self, table_name: str, index_name: str, columns: List[str], unique: bool = False
    ) -> Result[None]:
        """Create an index"""
        pass

    @abstractmethod
    async def drop_index(self, index_name: str) -> Result[None]:
        """Drop an index"""
        pass

    @abstractmethod
    async def get_table_schema(self, table_name: str) -> Result[TableSchema]:
        """Get table schema"""
        pass

    @abstractmethod
    async def list_tables(self) -> Result[List[str]]:
        """List all tables"""
        pass


# ========================================
# Full-Text Search Interfaces
# ========================================


class IFTSEngine(ABC):
    """Interface for Full-Text Search engine"""

    @abstractmethod
    async def create_fts_table(
        self, table_name: str, columns: List[str], options: Dict[str, Any] = None
    ) -> Result[None]:
        """Create a FTS table"""
        pass

    @abstractmethod
    async def index_content(
        self, table_name: str, document_id: str, content: Dict[str, str]
    ) -> Result[None]:
        """Index content for FTS"""
        pass

    @abstractmethod
    async def search_fts(
        self, table_name: str, query: str, options: Dict[str, Any] = None
    ) -> Result[List[Dict[str, Any]]]:
        """Search using FTS"""
        pass

    @abstractmethod
    async def update_fts_content(
        self, table_name: str, document_id: str, content: Dict[str, str]
    ) -> Result[None]:
        """Update FTS content"""
        pass

    @abstractmethod
    async def delete_fts_content(
        self, table_name: str, document_id: str
    ) -> Result[None]:
        """Delete FTS content"""
        pass

    @abstractmethod
    async def optimize_fts_index(self, table_name: str) -> Result[None]:
        """Optimize FTS index"""
        pass


class ITextSearcher(ABC):
    """Interface for text search operations"""

    @abstractmethod
    async def search_exact(
        self, query: str, field: str = None
    ) -> Result[List[Dict[str, Any]]]:
        """Exact text search"""
        pass

    @abstractmethod
    async def search_phrase(
        self, phrase: str, field: str = None
    ) -> Result[List[Dict[str, Any]]]:
        """Phrase search"""
        pass

    @abstractmethod
    async def search_boolean(
        self, query: str, field: str = None
    ) -> Result[List[Dict[str, Any]]]:
        """Boolean search (AND, OR, NOT)"""
        pass

    @abstractmethod
    async def search_wildcard(
        self, pattern: str, field: str = None
    ) -> Result[List[Dict[str, Any]]]:
        """Wildcard search"""
        pass

    @abstractmethod
    async def get_search_suggestions(
        self, partial_query: str, limit: int = 10
    ) -> Result[List[str]]:
        """Get search suggestions"""
        pass


# ========================================
# Repository Interfaces
# ========================================


class ISymbolRepository(ABC, IAsyncRepository[SymbolDefinition]):
    """Repository for symbol definitions"""

    @abstractmethod
    async def find_by_name(self, symbol_name: str) -> List[SymbolDefinition]:
        """Find symbols by name"""
        pass

    @abstractmethod
    async def find_by_file(self, file_path: str) -> List[SymbolDefinition]:
        """Find symbols in a file"""
        pass

    @abstractmethod
    async def find_by_type(self, symbol_type: str) -> List[SymbolDefinition]:
        """Find symbols by type"""
        pass

    @abstractmethod
    async def search_symbols(
        self, query: str, options: Dict[str, Any] = None
    ) -> List[SymbolDefinition]:
        """Search symbols"""
        pass


class IFileRepository(ABC, IAsyncRepository[IndexedFile]):
    """Repository for indexed files"""

    @abstractmethod
    async def find_by_language(self, language: str) -> List[IndexedFile]:
        """Find files by language"""
        pass

    @abstractmethod
    async def find_by_extension(self, extension: str) -> List[IndexedFile]:
        """Find files by extension"""
        pass

    @abstractmethod
    async def find_modified_since(self, timestamp: datetime) -> List[IndexedFile]:
        """Find files modified since timestamp"""
        pass

    @abstractmethod
    async def get_file_stats(self) -> Dict[str, Any]:
        """Get file statistics"""
        pass


class IReferenceRepository(ABC, IAsyncRepository[SymbolReference]):
    """Repository for symbol references"""

    @abstractmethod
    async def find_references_to(self, symbol: str) -> List[SymbolReference]:
        """Find references to a symbol"""
        pass

    @abstractmethod
    async def find_references_in_file(self, file_path: str) -> List[SymbolReference]:
        """Find references in a file"""
        pass

    @abstractmethod
    async def count_references(self, symbol: str) -> int:
        """Count references to a symbol"""
        pass


# ========================================
# Migration Interfaces
# ========================================


class IMigrationRunner(ABC):
    """Interface for database migrations"""

    @abstractmethod
    async def run_migrations(self, target_version: str = None) -> Result[List[str]]:
        """Run database migrations"""
        pass

    @abstractmethod
    async def rollback_migration(self, version: str) -> Result[None]:
        """Rollback a migration"""
        pass

    @abstractmethod
    async def get_current_version(self) -> Result[str]:
        """Get current schema version"""
        pass

    @abstractmethod
    async def get_pending_migrations(self) -> Result[List[MigrationInfo]]:
        """Get pending migrations"""
        pass

    @abstractmethod
    async def create_migration(
        self, description: str, up_script: str, down_script: str
    ) -> Result[str]:
        """Create a new migration"""
        pass


class ISchemaVersioning(ABC):
    """Interface for schema versioning"""

    @abstractmethod
    async def get_schema_version(self) -> Result[str]:
        """Get current schema version"""
        pass

    @abstractmethod
    async def set_schema_version(self, version: str) -> Result[None]:
        """Set schema version"""
        pass

    @abstractmethod
    async def is_compatible(self, required_version: str) -> Result[bool]:
        """Check if current version is compatible"""
        pass

    @abstractmethod
    async def get_version_history(self) -> Result[List[Dict[str, Any]]]:
        """Get version history"""
        pass


# ========================================
# Backup & Recovery Interfaces
# ========================================


class IBackupManager(ABC):
    """Interface for backup management"""

    @abstractmethod
    async def create_backup(
        self, backup_type: str = "full", options: Dict[str, Any] = None
    ) -> Result[BackupInfo]:
        """Create a backup"""
        pass

    @abstractmethod
    async def restore_backup(
        self, backup_id: str, options: Dict[str, Any] = None
    ) -> Result[None]:
        """Restore from backup"""
        pass

    @abstractmethod
    async def list_backups(self) -> Result[List[BackupInfo]]:
        """List available backups"""
        pass

    @abstractmethod
    async def delete_backup(self, backup_id: str) -> Result[None]:
        """Delete a backup"""
        pass

    @abstractmethod
    async def verify_backup(self, backup_id: str) -> Result[bool]:
        """Verify backup integrity"""
        pass


class IDataExporter(ABC):
    """Interface for data export"""

    @abstractmethod
    async def export_to_json(
        self, tables: List[str] = None, file_path: str = None
    ) -> Result[str]:
        """Export data to JSON"""
        pass

    @abstractmethod
    async def export_to_csv(self, table: str, file_path: str = None) -> Result[str]:
        """Export table to CSV"""
        pass

    @abstractmethod
    async def export_to_sql(
        self, tables: List[str] = None, file_path: str = None
    ) -> Result[str]:
        """Export data to SQL"""
        pass

    @abstractmethod
    async def import_from_json(
        self, file_path: str, options: Dict[str, Any] = None
    ) -> Result[int]:
        """Import data from JSON"""
        pass


# ========================================
# Performance & Monitoring Interfaces
# ========================================


class IStorageMonitor(ABC):
    """Interface for storage monitoring"""

    @abstractmethod
    async def get_storage_stats(self) -> Result[Dict[str, Any]]:
        """Get storage statistics"""
        pass

    @abstractmethod
    async def get_query_performance(self) -> Result[List[Dict[str, Any]]]:
        """Get query performance metrics"""
        pass

    @abstractmethod
    async def get_slow_queries(
        self, threshold: float = 1.0
    ) -> Result[List[Dict[str, Any]]]:
        """Get slow queries"""
        pass

    @abstractmethod
    async def analyze_table(self, table_name: str) -> Result[Dict[str, Any]]:
        """Analyze table performance"""
        pass


class IConnectionPool(ABC):
    """Interface for database connection pooling"""

    @abstractmethod
    async def get_connection(self) -> Any:
        """Get a connection from the pool"""
        pass

    @abstractmethod
    async def return_connection(self, connection: Any) -> None:
        """Return a connection to the pool"""
        pass

    @abstractmethod
    async def close_pool(self) -> None:
        """Close all connections in the pool"""
        pass

    @abstractmethod
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pass


# ========================================
# Storage Optimization Interfaces
# ========================================


class IQueryOptimizer(ABC):
    """Interface for storage query optimization"""

    @abstractmethod
    async def analyze_query(self, query: str) -> Result[Dict[str, Any]]:
        """Analyze query performance"""
        pass

    @abstractmethod
    async def suggest_indexes(self, queries: List[str]) -> Result[List[str]]:
        """Suggest indexes for queries"""
        pass

    @abstractmethod
    async def optimize_table(self, table_name: str) -> Result[None]:
        """Optimize table structure"""
        pass

    @abstractmethod
    async def vacuum_database(self) -> Result[None]:
        """Vacuum/compact database"""
        pass


class IStorageOptimizer(ABC):
    """Interface for storage optimization"""

    @abstractmethod
    async def compact_storage(self) -> Result[Dict[str, Any]]:
        """Compact storage to reclaim space"""
        pass

    @abstractmethod
    async def rebuild_indexes(self, table_name: str = None) -> Result[None]:
        """Rebuild indexes"""
        pass

    @abstractmethod
    async def update_statistics(self, table_name: str = None) -> Result[None]:
        """Update table statistics"""
        pass

    @abstractmethod
    async def check_integrity(self) -> Result[bool]:
        """Check database integrity"""
        pass
