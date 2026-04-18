# Breaking Changes

This file logs every schema bump and other breaking changes to Code-Index-MCP.

## P10 (2026-04-18): `strict_compatibility` default flipped to True

`IndexManager.select_best_index` now raises `SchemaMismatchError` by default
when the on-disk index schema version does not match the expected current version.

**Migration**: Re-index affected repositories, or pass
`--rebuild-on-schema-mismatch` to `mcp-server stdio` / `serve` to rebuild
automatically on load.

## Schema migration history

| Migration | Date | Summary |
|---|---|---|
| 001_initial_schema | 2025-01-28 | Initial SQLite schema (files, symbols, chunks tables) |
| 002_relative_paths | 2025-03-28 | Relative-path migration |
| 003_stable_ids | 2025-01-28 | Stable symbol IDs |
| 004_semantic_points | 2025-03-12 | Semantic/embedding point storage |
| 005_chunk_summaries | 2025-03-16 | Chunk summaries table |
