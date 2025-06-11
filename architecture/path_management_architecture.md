# Path Management Architecture

## Overview
This document describes the comprehensive path management system that enables portable indexes by using relative paths as primary identifiers across all storage layers (SQLite, Qdrant vectors, and contextual embeddings) while tracking file moves efficiently without re-indexing unchanged content.

## Problem Statement
The current implementation has several critical issues:

### SQLite Storage Issues
1. **Non-Portable Indexes**: Absolute paths like `/home/user/project/file.py` make indexes unusable when shared
2. **Duplicate Entries**: Moving files creates new entries instead of updating existing ones
3. **Stale Data**: Deleted files remain in the index indefinitely
4. **Unnecessary Re-indexing**: Moved files are fully re-indexed even when content hasn't changed

### Vector Embedding Issues
5. **Non-Portable Embeddings**: Vector IDs use absolute paths via `_symbol_id(file, name, line)`
6. **No Cleanup Operations**: Missing `remove_file()` and `move_file()` methods in SemanticIndexer
7. **Duplicate Embeddings**: Same code indexed from different paths creates duplicate vectors
8. **Contextual Embedding Gaps**: No content-based deduplication for document chunks

## Solution Architecture

### Core Components

#### 1. Path Resolver (`mcp_server/core/path_resolver.py`)
Centralizes all path operations to ensure consistency across the system.

```python
class PathResolver:
    """Handles path normalization and resolution for portable indexes."""
    
    def __init__(self, repository_root: Optional[Path] = None):
        self.repository_root = repository_root or self._detect_repository_root()
    
    def normalize_path(self, absolute_path: Union[str, Path]) -> str:
        """Convert absolute path to relative path from repository root."""
        path = Path(absolute_path).resolve()
        try:
            return str(path.relative_to(self.repository_root))
        except ValueError:
            # Path is outside repository
            return str(path)
    
    def resolve_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path."""
        return (self.repository_root / relative_path).resolve()
    
    def compute_content_hash(self, file_path: Union[str, Path]) -> str:
        """Compute SHA-256 hash of file content."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _detect_repository_root(self) -> Path:
        """Auto-detect repository root by finding .git directory."""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return Path.cwd()
```

#### 2. Enhanced SQLite Store
Updates to handle relative paths and content tracking:

```python
class SQLiteStore:
    def store_file(self, repository_id: int, file_path: Path,
                   content_hash: Optional[str] = None, **kwargs):
        """Store file with relative path as primary identifier."""
        relative_path = self.path_resolver.normalize_path(file_path)
        
        # Check if file with same content already exists (moved file)
        if content_hash:
            existing = self.get_file_by_content_hash(content_hash, repository_id)
            if existing and existing['relative_path'] != relative_path:
                # This is a moved file - update path instead of re-indexing
                self.move_file(existing['relative_path'], relative_path, 
                             repository_id, content_hash)
                return existing['id']
        
        # Normal file storage with relative path
        return self._store_file_record(repository_id, relative_path, 
                                     content_hash, **kwargs)
    
    def remove_file(self, relative_path: str, repository_id: int):
        """Remove file and all associated data."""
        with self._get_connection() as conn:
            # Get file ID
            cursor = conn.execute(
                "SELECT id FROM files WHERE relative_path = ? AND repository_id = ?",
                (relative_path, repository_id)
            )
            file_id = cursor.fetchone()
            if not file_id:
                return
            
            # Delete with CASCADE (symbols, references, etc.)
            conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id[0],))
            conn.execute("DELETE FROM references WHERE file_id = ?", (file_id[0],))
            conn.execute("DELETE FROM imports WHERE file_id = ?", (file_id[0],))
            conn.execute("DELETE FROM files WHERE id = ?", (file_id[0],))
    
    def mark_file_deleted(self, relative_path: str, repository_id: int):
        """Soft delete - mark file as deleted but keep data."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE files 
                SET is_deleted = TRUE, deleted_at = CURRENT_TIMESTAMP
                WHERE relative_path = ? AND repository_id = ?
            """, (relative_path, repository_id))
```

#### 3. File Watcher Integration
Enhanced to handle all file system events properly:

```python
class _Handler(FileSystemEventHandler):
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        if path.suffix in self.code_extensions:
            logger.info(f"File deleted: {path}")
            # Use relative path for deletion
            relative_path = self.path_resolver.normalize_path(path)
            self.dispatcher.remove_file(relative_path)
    
    def on_moved(self, event):
        """Handle file move events efficiently."""
        old_path = Path(event.src_path)
        new_path = Path(event.dest_path)
        
        if old_path.suffix in self.code_extensions:
            # Compute content hash to check if it's just a move
            content_hash = self.path_resolver.compute_content_hash(new_path)
            
            # Let dispatcher handle the move
            self.dispatcher.move_file(old_path, new_path, content_hash)
```

#### 4. Dispatcher Updates
Methods to support file operations without re-indexing:

```python
class EnhancedDispatcher:
    def move_file(self, old_path: Path, new_path: Path, content_hash: str):
        """Handle file move efficiently."""
        old_relative = self.path_resolver.normalize_path(old_path)
        new_relative = self.path_resolver.normalize_path(new_path)
        
        # Check if content changed by comparing hashes
        existing_file = self.sqlite_store.get_file(old_relative, self.repo_id)
        if existing_file and existing_file.get('content_hash') == content_hash:
            # Just a move/rename - update path only
            logger.info(f"File moved without changes: {old_relative} → {new_relative}")
            self.sqlite_store.move_file(old_relative, new_relative, 
                                      self.repo_id, content_hash)
            # Invalidate caches
            self._invalidate_caches_for_file(old_relative)
            self._invalidate_caches_for_file(new_relative)
        else:
            # Content changed - remove old and index new
            logger.info(f"File moved with changes: {old_relative} → {new_relative}")
            self.remove_file(old_relative)
            self.index_file(new_path)
    
    def remove_file(self, file_path: Union[Path, str]):
        """Remove file from all indexes."""
        relative_path = self.path_resolver.normalize_path(file_path)
        logger.info(f"Removing file from index: {relative_path}")
        
        # Remove from SQLite
        self.sqlite_store.remove_file(relative_path, self.repo_id)
        
        # Remove from vector store if present
        if self.semantic_indexer:
            self.semantic_indexer.remove_file(relative_path)
        
        # Invalidate caches
        self._invalidate_caches_for_file(relative_path)
```

### Database Schema Changes

#### Migration Strategy
1. Add new columns without breaking existing functionality
2. Populate content hashes in background
3. Convert absolute paths to relative
4. Switch primary key to relative paths
5. Clean up duplicates

```sql
-- Phase 1: Add new columns (non-breaking)
ALTER TABLE files ADD COLUMN content_hash TEXT;
ALTER TABLE files ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE files ADD COLUMN deleted_at TIMESTAMP;

-- Phase 2: Add indexes
CREATE INDEX idx_files_content_hash ON files(content_hash);
CREATE INDEX idx_files_deleted ON files(is_deleted);

-- Phase 3: Add file moves tracking
CREATE TABLE file_moves (
    id INTEGER PRIMARY KEY,
    repository_id INTEGER NOT NULL,
    old_relative_path TEXT NOT NULL,
    new_relative_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    moved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    move_type TEXT,
    FOREIGN KEY (repository_id) REFERENCES repositories(id)
);

-- Phase 4: Update unique constraint (after migration)
DROP INDEX files_repository_id_path_key;
CREATE UNIQUE INDEX files_repository_id_relative_path_key 
  ON files(repository_id, relative_path);
```

### Migration Process

#### Data Migration Script
```python
def migrate_to_relative_paths():
    """Convert existing absolute paths to relative paths."""
    
    # 1. Detect repository roots
    repos = get_all_repositories()
    for repo in repos:
        resolver = PathResolver(Path(repo['path']))
        
        # 2. Update all file paths
        files = get_files_for_repository(repo['id'])
        for file in files:
            # Convert absolute to relative
            try:
                relative_path = resolver.normalize_path(file['path'])
            except ValueError:
                # File is outside repository - skip
                continue
            
            # Compute content hash
            if Path(file['path']).exists():
                content_hash = resolver.compute_content_hash(file['path'])
            else:
                content_hash = None
            
            # Update record
            update_file_paths(file['id'], relative_path, content_hash)
        
        # 3. Remove duplicates (same content_hash)
        remove_duplicate_files(repo['id'])
        
        # 4. Update repository root if needed
        update_repository_root(repo['id'], str(resolver.repository_root))
```

### Vector Embedding Enhancement

#### Enhanced SemanticIndexer
```python
class SemanticIndexer:
    def __init__(self, path_resolver: PathResolver, ...):
        self.path_resolver = path_resolver
        # ... existing init code
    
    def _symbol_id(self, relative_path: str, name: str, line: int, 
                   content_hash: str) -> int:
        """Generate portable symbol ID using relative path and content hash."""
        # Include content hash for better deduplication
        id_string = f"{relative_path}:{name}:{line}:{content_hash[:8]}"
        h = hashlib.sha256(id_string.encode("utf-8")).digest()[:8]
        return int.from_bytes(h, "big", signed=False)
    
    def remove_file(self, relative_path: str):
        """Remove all embeddings for a deleted file."""
        self.qdrant.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(
                        key="relative_path",
                        match=models.MatchValue(value=relative_path)
                    )]
                )
            )
        )
    
    def move_file(self, old_relative_path: str, new_relative_path: str,
                  content_hash: str):
        """Update file path in embedding metadata."""
        # Get all points for the old path
        results = self.qdrant.scroll(
            collection_name=self.collection,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(
                    key="relative_path",
                    match=models.MatchValue(value=old_relative_path)
                )]
            ),
            limit=1000
        )
        
        # Update each point with new path
        for point in results[0]:
            point.payload["relative_path"] = new_relative_path
            point.payload["file"] = new_relative_path  # Legacy field
            point.payload["content_hash"] = content_hash
            # Generate new ID with relative path
            new_id = self._symbol_id(
                new_relative_path,
                point.payload["symbol"],
                point.payload["line"],
                content_hash
            )
            # Reinsert with new ID and delete old
            self.qdrant.upsert(
                collection_name=self.collection,
                points=[models.PointStruct(
                    id=new_id,
                    vector=point.vector,
                    payload=point.payload
                )]
            )
            self.qdrant.delete(
                collection_name=self.collection,
                points=[point.id]
            )
    
    def get_embeddings_by_content_hash(self, content_hash: str) -> List[Dict]:
        """Find all embeddings with the same content hash."""
        results = self.qdrant.scroll(
            collection_name=self.collection,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(
                    key="content_hash",
                    match=models.MatchValue(value=content_hash)
                )]
            ),
            limit=1000
        )
        return results[0] if results else []
```

#### Updated Qdrant Payload Schema
```json
{
    "file": "src/module.py",              // Legacy: absolute path
    "relative_path": "src/module.py",     // Primary: relative path
    "content_hash": "sha256:abc123...",   // Content hash for deduplication
    "repository_id": 1,                   // Link to SQLite repository
    "symbol": "process_data",
    "kind": "function",
    "signature": "def process_data(items)",
    "line": 42,
    "span": [42, 58],
    "language": "python",
    "indexed_at": "2025-01-30T12:00:00Z",
    "context_before": "# Process incoming data",
    "context_after": "return results",
    "chunk_metadata": {
        "chunk_index": 0,
        "total_chunks": 1,
        "chunk_hash": "sha256:def456..."  // Chunk-specific hash
    }
}
```

#### Vector Migration Script
```python
def migrate_vector_embeddings():
    """Migrate Qdrant embeddings to use relative paths."""
    
    # 1. Initialize components
    path_resolver = PathResolver()
    indexer = SemanticIndexer()
    
    # 2. Get all collections
    collections = indexer.qdrant.get_collections()
    
    for collection in collections.collections:
        print(f"Migrating collection: {collection.name}")
        
        # 3. Scroll through all points
        offset = None
        while True:
            results, offset = indexer.qdrant.scroll(
                collection_name=collection.name,
                offset=offset,
                limit=100
            )
            
            if not results:
                break
            
            # 4. Update each point
            updated_points = []
            for point in results:
                old_path = point.payload.get("file", "")
                
                # Convert to relative path
                try:
                    relative_path = path_resolver.normalize_path(old_path)
                except ValueError:
                    continue  # Skip if outside repo
                
                # Compute content hash if file exists
                content_hash = None
                if Path(old_path).exists():
                    content_hash = path_resolver.compute_content_hash(old_path)
                
                # Update payload
                point.payload["relative_path"] = relative_path
                point.payload["content_hash"] = content_hash
                point.payload["repository_id"] = 1  # Or detect from path
                
                # Generate new ID
                new_id = indexer._symbol_id(
                    relative_path,
                    point.payload.get("symbol", ""),
                    point.payload.get("line", 0),
                    content_hash or ""
                )
                
                updated_points.append(models.PointStruct(
                    id=new_id,
                    vector=point.vector,
                    payload=point.payload
                ))
            
            # 5. Batch update
            if updated_points:
                indexer.qdrant.upsert(
                    collection_name=collection.name,
                    points=updated_points
                )
                
                # Delete old points with absolute paths
                old_ids = [p.id for p in results]
                indexer.qdrant.delete(
                    collection_name=collection.name,
                    points=old_ids
                )
        
        print(f"✓ Migrated {collection.name}")
```

## Benefits

### 1. True Portability
- Indexes can be shared between users regardless of where code is located
- Works across different operating systems (Windows, Mac, Linux)
- Supports containerized environments

### 2. Efficient File Operations
- File moves don't trigger re-indexing if content unchanged
- Renames are instant updates
- Reduces CPU and API usage

### 3. Clean Index Maintenance
- Deleted files are properly removed
- No accumulation of stale entries
- Audit trail via soft deletes

### 4. Performance Improvements
- Content hash prevents duplicate indexing
- Faster file move detection
- Reduced database size

## Implementation Checklist

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create PathResolver class with hash computation
- [ ] Add content_hash columns to SQLite database
- [ ] Design vector payload schema updates
- [ ] Create base migration framework

### Phase 2: Storage Layer (Week 1)
#### SQLite Updates
- [ ] Update SQLiteStore methods for relative paths
- [ ] Add file operation methods (remove, move, soft delete)
- [ ] Implement content hash checking
- [ ] Add deduplication logic

#### Vector Store Updates
- [ ] Update SemanticIndexer with PathResolver
- [ ] Implement remove_file() for vectors
- [ ] Implement move_file() for vectors
- [ ] Add content hash to embeddings
- [ ] Update _symbol_id() to use relative paths

### Phase 3: Integration (Week 1.5-2)
- [ ] Update file watcher with deletion handling
- [ ] Enhance dispatcher to coordinate SQLite + vector ops
- [ ] Update all plugins to use path resolver
- [ ] Fix search methods to use relative paths
- [ ] Ensure contextual embeddings use relative paths

### Phase 4: Testing & Migration (Week 2-2.5)
#### Testing
- [ ] Unit tests for path operations
- [ ] Vector operation tests
- [ ] Cross-platform path tests
- [ ] Performance benchmarks
- [ ] End-to-end workflows

#### Migration
- [ ] SQLite migration script
- [ ] Vector embedding migration script
- [ ] Rollback procedures
- [ ] Progress tracking
- [ ] Verification tools

## Backward Compatibility

### Transition Period
1. Keep absolute `path` column for compatibility
2. Use relative_path for all new operations
3. Provide fallback for old indexes
4. Gradual migration with logging

### API Compatibility
- Search APIs return relative paths by default
- Optional flag to return absolute paths
- Path resolution on demand

## Performance Considerations

### Content Hash Caching
- Cache hashes in memory for recently accessed files
- Compute hashes asynchronously
- Use file modification time to invalidate cache

### Migration Performance
- Process files in batches
- Run migration in background
- Progress tracking and resumability

## Security Considerations

### Path Traversal Protection
- Validate all paths stay within repository
- Prevent `../` escapes
- Sanitize user input

### Hash Collision Handling
- Use SHA-256 for low collision probability
- Include file size in uniqueness check
- Log any detected collisions