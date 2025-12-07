"""
Storage Interfaces

All interfaces related to data persistence, storage engines, and database operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .plugin_interfaces import IndexedFile, SymbolDefinition, SymbolReference
from .shared_interfaces import IAsyncRepository, Result

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

    @abstractmethod
    async def shutdown(self) -> Result[None]:
        """Shutdown the storage engine"""

    @abstractmethod
    async def execute_query(self, query: str, params: List[Any] = None) -> Result[QueryResult]:
        """Execute a raw SQL query"""

    @abstractmethod
    async def execute_many(self, query: str, params_list: List[List[Any]]) -> Result[int]:
        """Execute a query with multiple parameter sets"""

    @abstractmethod
    async def begin_transaction(self) -> Result[str]:
        """Begin a database transaction"""

    @abstractmethod
    async def commit_transaction(self, transaction_id: str) -> Result[None]:
        """Commit a transaction"""

    @abstractmethod
    async def rollback_transaction(self, transaction_id: str) -> Result[None]:
        """Rollback a transaction"""

    @abstractmethod
    async def get_connection_info(self) -> Result[Dict[str, Any]]:
        """Get connection information"""


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

    @abstractmethod
    async def insert(self, table: str, data: Dict[str, Any]) -> Result[int]:
        """Insert a record"""

    @abstractmethod
    async def update(self, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> Result[int]:
        """Update records"""

    @abstractmethod
    async def delete(self, table: str, where: Dict[str, Any]) -> Result[int]:
        """Delete records"""

    @abstractmethod
    async def upsert(
        self, table: str, data: Dict[str, Any], conflict_columns: List[str]
    ) -> Result[int]:
        """Insert or update on conflict"""

    @abstractmethod
    async def bulk_insert(self, table: str, data: List[Dict[str, Any]]) -> Result[int]:
        """Bulk insert records"""


class ISchemaManager(ABC):
    """Interface for database schema management"""

    @abstractmethod
    async def create_table(self, schema: TableSchema) -> Result[None]:
        """Create a table"""

    @abstractmethod
    async def drop_table(self, table_name: str) -> Result[None]:
        """Drop a table"""

    @abstractmethod
    async def alter_table(self, table_name: str, changes: List[Dict[str, Any]]) -> Result[None]:
        """Alter a table structure"""

    @abstractmethod
    async def create_index(
        self, table_name: str, index_name: str, columns: List[str], unique: bool = False
    ) -> Result[None]:
        """Create an index"""

    @abstractmethod
    async def drop_index(self, index_name: str) -> Result[None]:
        """Drop an index"""

    @abstractmethod
    async def get_table_schema(self, table_name: str) -> Result[TableSchema]:
        """Get table schema"""

    @abstractmethod
    async def list_tables(self) -> Result[List[str]]:
        """List all tables"""


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

    @abstractmethod
    async def index_content(
        self, table_name: str, document_id: str, content: Dict[str, str]
    ) -> Result[None]:
        """Index content for FTS"""

    @abstractmethod
    async def search_fts(
        self, table_name: str, query: str, options: Dict[str, Any] = None
    ) -> Result[List[Dict[str, Any]]]:
        """Search using FTS"""

    @abstractmethod
    async def update_fts_content(
        self, table_name: str, document_id: str, content: Dict[str, str]
    ) -> Result[None]:
        """Update FTS content"""

    @abstractmethod
    async def delete_fts_content(self, table_name: str, document_id: str) -> Result[None]:
        """Delete FTS content"""

    @abstractmethod
    async def optimize_fts_index(self, table_name: str) -> Result[None]:
        """Optimize FTS index"""


class ITextSearcher(ABC):
    """Interface for text search operations"""

    @abstractmethod
    async def search_exact(self, query: str, field: str = None) -> Result[List[Dict[str, Any]]]:
        """Exact text search"""

    @abstractmethod
    async def search_phrase(self, phrase: str, field: str = None) -> Result[List[Dict[str, Any]]]:
        """Phrase search"""

    @abstractmethod
    async def search_boolean(self, query: str, field: str = None) -> Result[List[Dict[str, Any]]]:
        """Boolean search (AND, OR, NOT)"""

    @abstractmethod
    async def search_wildcard(
        self, pattern: str, field: str = None
    ) -> Result[List[Dict[str, Any]]]:
        """Wildcard search"""

    @abstractmethod
    async def get_search_suggestions(
        self, partial_query: str, limit: int = 10
    ) -> Result[List[str]]:
        """Get search suggestions"""


# ========================================
# Repository Interfaces
# ========================================


class ISymbolRepository(ABC, IAsyncRepository[SymbolDefinition]):
    """Repository for symbol definitions"""

    @abstractmethod
    async def find_by_name(self, symbol_name: str) -> List[SymbolDefinition]:
        """Find symbols by name"""

    @abstractmethod
    async def find_by_file(self, file_path: str) -> List[SymbolDefinition]:
        """Find symbols in a file"""

    @abstractmethod
    async def find_by_type(self, symbol_type: str) -> List[SymbolDefinition]:
        """Find symbols by type"""

    @abstractmethod
    async def search_symbols(
        self, query: str, options: Dict[str, Any] = None
    ) -> List[SymbolDefinition]:
        """Search symbols"""


class IFileRepository(ABC, IAsyncRepository[IndexedFile]):
    """Repository for indexed files"""

    @abstractmethod
    async def find_by_language(self, language: str) -> List[IndexedFile]:
        """Find files by language"""

    @abstractmethod
    async def find_by_extension(self, extension: str) -> List[IndexedFile]:
        """Find files by extension"""

    @abstractmethod
    async def find_modified_since(self, timestamp: datetime) -> List[IndexedFile]:
        """Find files modified since timestamp"""

    @abstractmethod
    async def get_file_stats(self) -> Dict[str, Any]:
        """Get file statistics"""


class IReferenceRepository(ABC, IAsyncRepository[SymbolReference]):
    """Repository for symbol references"""

    @abstractmethod
    async def find_references_to(self, symbol: str) -> List[SymbolReference]:
        """Find references to a symbol"""

    @abstractmethod
    async def find_references_in_file(self, file_path: str) -> List[SymbolReference]:
        """Find references in a file"""

    @abstractmethod
    async def count_references(self, symbol: str) -> int:
        """Count references to a symbol"""


# ========================================
# Migration Interfaces
# ========================================


class IMigrationRunner(ABC):
    """Interface for database migrations"""

    @abstractmethod
    async def run_migrations(self, target_version: str = None) -> Result[List[str]]:
        """Run database migrations"""

    @abstractmethod
    async def rollback_migration(self, version: str) -> Result[None]:
        """Rollback a migration"""

    @abstractmethod
    async def get_current_version(self) -> Result[str]:
        """Get current schema version"""

    @abstractmethod
    async def get_pending_migrations(self) -> Result[List[MigrationInfo]]:
        """Get pending migrations"""

    @abstractmethod
    async def create_migration(
        self, description: str, up_script: str, down_script: str
    ) -> Result[str]:
        """Create a new migration"""


class ISchemaVersioning(ABC):
    """Interface for schema versioning"""

    @abstractmethod
    async def get_schema_version(self) -> Result[str]:
        """Get current schema version"""

    @abstractmethod
    async def set_schema_version(self, version: str) -> Result[None]:
        """Set schema version"""

    @abstractmethod
    async def is_compatible(self, required_version: str) -> Result[bool]:
        """Check if current version is compatible"""

    @abstractmethod
    async def get_version_history(self) -> Result[List[Dict[str, Any]]]:
        """Get version history"""


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

    @abstractmethod
    async def restore_backup(self, backup_id: str, options: Dict[str, Any] = None) -> Result[None]:
        """Restore from backup"""

    @abstractmethod
    async def list_backups(self) -> Result[List[BackupInfo]]:
        """List available backups"""

    @abstractmethod
    async def delete_backup(self, backup_id: str) -> Result[None]:
        """Delete a backup"""

    @abstractmethod
    async def verify_backup(self, backup_id: str) -> Result[bool]:
        """Verify backup integrity"""


class IDataExporter(ABC):
    """Interface for data export"""

    @abstractmethod
    async def export_to_json(self, tables: List[str] = None, file_path: str = None) -> Result[str]:
        """Export data to JSON"""

    @abstractmethod
    async def export_to_csv(self, table: str, file_path: str = None) -> Result[str]:
        """Export table to CSV"""

    @abstractmethod
    async def export_to_sql(self, tables: List[str] = None, file_path: str = None) -> Result[str]:
        """Export data to SQL"""

    @abstractmethod
    async def import_from_json(self, file_path: str, options: Dict[str, Any] = None) -> Result[int]:
        """Import data from JSON"""


# ========================================
# Performance & Monitoring Interfaces
# ========================================


class IStorageMonitor(ABC):
    """Interface for storage monitoring"""

    @abstractmethod
    async def get_storage_stats(self) -> Result[Dict[str, Any]]:
        """Get storage statistics"""

    @abstractmethod
    async def get_query_performance(self) -> Result[List[Dict[str, Any]]]:
        """Get query performance metrics"""

    @abstractmethod
    async def get_slow_queries(self, threshold: float = 1.0) -> Result[List[Dict[str, Any]]]:
        """Get slow queries"""

    @abstractmethod
    async def analyze_table(self, table_name: str) -> Result[Dict[str, Any]]:
        """Analyze table performance"""


class IConnectionPool(ABC):
    """Interface for database connection pooling"""

    @abstractmethod
    async def get_connection(self) -> Any:
        """Get a connection from the pool"""

    @abstractmethod
    async def return_connection(self, connection: Any) -> None:
        """Return a connection to the pool"""

    @abstractmethod
    async def close_pool(self) -> None:
        """Close all connections in the pool"""

    @abstractmethod
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""


# ========================================
# Storage Optimization Interfaces
# ========================================


class IQueryOptimizer(ABC):
    """Interface for storage query optimization"""

    @abstractmethod
    async def analyze_query(self, query: str) -> Result[Dict[str, Any]]:
        """Analyze query performance"""

    @abstractmethod
    async def suggest_indexes(self, queries: List[str]) -> Result[List[str]]:
        """Suggest indexes for queries"""

    @abstractmethod
    async def optimize_table(self, table_name: str) -> Result[None]:
        """Optimize table structure"""

    @abstractmethod
    async def vacuum_database(self) -> Result[None]:
        """Vacuum/compact database"""


class IStorageOptimizer(ABC):
    """Interface for storage optimization"""

    @abstractmethod
    async def compact_storage(self) -> Result[Dict[str, Any]]:
        """Compact storage to reclaim space"""

    @abstractmethod
    async def rebuild_indexes(self, table_name: str = None) -> Result[None]:
        """Rebuild indexes"""

    @abstractmethod
    async def update_statistics(self, table_name: str = None) -> Result[None]:
        """Update table statistics"""

    @abstractmethod
    async def check_integrity(self) -> Result[bool]:
        """Check database integrity"""
