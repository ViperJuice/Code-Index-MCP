# Path Management Implementation Plan - Optimized for Parallel Execution

## Executive Summary
This plan fixes critical issues with the current indexing system across all storage layers:
- **Non-portable indexes** due to absolute paths in SQLite and Qdrant
- **Duplicate entries** when files are moved (both database and vectors)
- **Stale data** from deleted files in all storage layers
- **Unnecessary re-indexing** of moved files
- **Vector embeddings** using absolute paths, making them non-portable
- **Missing cleanup operations** for vector embeddings

## Parallel Execution Strategy

### Team Structure (8 total: 7 developers + 1 coordinator)
- **Stream A**: Core Path Management (2 devs)
- **Stream B**: Storage Layer - SQLite & Vectors (3 devs)
- **Stream C**: Integration (1 dev)
- **Stream D**: Testing & QA (2 devs)
- **Coordinator**: Daily standups, integration, blockers

### Week 1: Core Implementation (Parallel Streams A & B)

#### Stream A: Path Management Core
**Developer A1**: Path Resolver Module
```bash
# Day 1-2: Create path resolver
- mcp_server/core/path_resolver.py
- tests/test_path_resolver.py

# Day 3-4: Content hashing
- Add hash computation methods
- Add hash caching layer

# Day 5: Integration interfaces
- Create interfaces for other components
- Document API contracts
```

**Developer A2**: Database Migration
```bash
# Day 1-2: Schema design
- mcp_server/storage/migrations/002_relative_paths.sql
- Migration testing framework

# Day 3-4: Migration script
- scripts/migrate_to_relative_paths.py
- Batch processing logic

# Day 5: Rollback procedures
- Create rollback scripts
- Test migration/rollback cycles
```

#### Stream B: Storage Layer Updates
**Developer B1**: SQLiteStore Methods
```bash
# Day 1-2: File operation methods
- mark_file_deleted()
- remove_file() with CASCADE
- move_file() with hash check

# Day 3-4: Query updates
- Update all queries to use relative_path
- Add backward compatibility layer

# Day 5: Performance optimization
- Add query optimization
- Implement batch operations
```

**Developer B2**: Vector Store Enhancement
```bash
# Day 1-2: SemanticIndexer updates
- Update _symbol_id() to use relative paths
- Add PathResolver integration
- Design new payload schema

# Day 3-4: Vector operations
- Implement remove_file() for Qdrant
- Implement move_file() with metadata update
- Add get_embeddings_by_content_hash()

# Day 5: Batch operations
- Implement batch update methods
- Add progress tracking for migrations
```

**Developer B3**: Migration Scripts
```bash
# Day 1-2: SQLite migration
- scripts/migrate_to_relative_paths.py
- Content hash computation for all files
- Duplicate detection and merging

# Day 3-4: Vector migration
- scripts/migrate_vector_embeddings.py
- Qdrant payload updates
- ID regeneration with relative paths

# Day 5: Coordination & rollback
- Coordinate SQLite + vector migrations
- Implement rollback procedures
- Add verification tools
```

### Week 2: Integration & Testing (Streams C & D + Reviews)

#### Stream C: System Integration
**Developer C1**: File Watcher & Dispatcher
```bash
# Day 1-2: File watcher events
- on_deleted() implementation
- on_moved() with hash checking

# Day 3-4: Dispatcher updates
- remove_file() method
- move_file() with optimization
- Hash computation integration

# Day 5: Cache invalidation
- Update all cache layers
- Test cache consistency
```

#### Stream D: Testing & Validation
**Developer D1**: Core Testing
```bash
# Day 1-2: Unit tests
- Path resolver tests
- SQLite operation tests
- Vector operation tests

# Day 3-4: Integration tests
- End-to-end workflows
- Cross-platform testing
- Concurrent operation tests

# Day 5: Performance testing
- Hash computation benchmarks
- Migration performance
- Query performance
```

**Developer D2**: Migration & QA
```bash
# Day 1-2: Migration testing
- Test SQLite migration with real data
- Test vector migration procedures
- Verify data integrity

# Day 3-4: Edge cases
- Large repository testing (10K+ files)
- Special characters in paths
- Symlinks and junction points

# Day 5: Acceptance testing
- User acceptance scenarios
- Documentation review
- Release preparation
```

## Implementation Files Checklist

### New Files to Create
- [ ] `mcp_server/core/path_resolver.py` - Central path management
- [ ] `mcp_server/storage/migrations/002_relative_paths.sql` - Schema updates
- [ ] `scripts/migrate_to_relative_paths.py` - SQLite migration
- [ ] `scripts/migrate_vector_embeddings.py` - Qdrant migration
- [ ] `tests/test_path_management.py` - Path operations tests
- [ ] `tests/test_vector_operations.py` - Vector store tests
- [ ] `tests/test_file_operations.py` - End-to-end tests
- [ ] `tests/test_migration.py` - Migration tests

### Files to Modify
- [ ] `mcp_server/storage/sqlite_store.py` - Add file operations
- [ ] `mcp_server/utils/semantic_indexer.py` - Add vector operations
- [ ] `mcp_server/watcher.py` - Add deletion handling
- [ ] `mcp_server/dispatcher/dispatcher_enhanced.py` - Coordinate operations
- [ ] `mcp_server/document_processing/contextual_embeddings.py` - Use relative paths
- [ ] `mcp_server/storage/migrations/001_initial_schema.sql` - Update schema
- [ ] `mcp_server/config/settings.py` - Add path config options
- [ ] All plugin files - Use PathResolver for paths

## Code Review Points

### Week 1 Reviews
- **Day 2**: Path resolver API design
- **Day 4**: Database schema changes
- **Day 5**: Integration interfaces

### Week 2 Reviews
- **Day 2**: File watcher implementation
- **Day 4**: Test coverage report
- **Day 5**: Performance benchmarks

## Success Criteria

### Functional Requirements
- [ ] Indexes portable between environments (SQLite + Qdrant)
- [ ] File moves don't re-index unchanged content
- [ ] Deleted files removed from all indexes
- [ ] No duplicate entries for moved files
- [ ] Vector embeddings use relative paths
- [ ] Content-based deduplication works

### Performance Requirements
- [ ] Hash computation < 50ms for average file
- [ ] File move operation < 100ms (including vectors)
- [ ] Migration processes 1000 files/minute
- [ ] Vector query performance unchanged
- [ ] Batch operations for large migrations

### Quality Requirements
- [ ] 90%+ test coverage for new code
- [ ] All existing tests pass
- [ ] Migration is reversible
- [ ] Backward compatibility maintained
- [ ] Cross-platform compatibility verified

## Risk Mitigation

### Technical Risks
1. **Large database migrations**
   - Solution: Batch processing with progress tracking
   - Fallback: Incremental migration option

2. **Hash computation performance**
   - Solution: Background processing with caching
   - Fallback: Optional hash computation

3. **Breaking changes**
   - Solution: Backward compatibility layer
   - Fallback: Dual-path support period

### Process Risks
1. **Integration conflicts**
   - Daily standups for coordination
   - Shared integration branch
   - Continuous integration tests

2. **Timeline slippage**
   - Weekly progress reviews
   - Prioritized feature list
   - MVP approach if needed

## Post-Implementation

### Documentation Updates
- Update API documentation
- Create migration guide
- Update architecture diagrams
- Add troubleshooting guide

### Monitoring
- Track migration success rate
- Monitor hash computation times
- Check for duplicate entries
- Measure search performance

### Maintenance
- Weekly cleanup of deleted files
- Monthly duplicate checks
- Quarterly performance review
- Annual architecture review

## Approval Checklist

Before implementation begins:
- [ ] Architecture review completed
- [ ] Database schema approved
- [ ] API design reviewed
- [ ] Test plan approved
- [ ] Resource allocation confirmed
- [ ] Timeline accepted

## Next Steps

1. **Immediate**: Assign developers to streams
2. **Day 1**: Set up development branches
3. **Day 1**: Create shared integration environment
4. **Day 2**: Begin parallel implementation
5. **Daily**: Standup meetings at 10 AM
6. **Weekly**: Progress review meetings

---

**Ready to implement?** This plan enables true index portability while maintaining performance and backward compatibility.