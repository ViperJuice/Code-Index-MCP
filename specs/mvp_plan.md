# Code-Index-MCP MVP Specification

## Executive Summary

The **Code-Index-MCP** project aims to provide a robust, local-first code indexing solution for AI assistants. While the current codebase boasts extensive feature implementation and "Production Ready" claims, a critical review identifies key gaps that must be addressed to achieve a true Minimum Viable Product (MVP).

**MVP Definition**: A stable, installable MCP server that:
1.  Locally indexes code repositories (SQLite + basic FTS).
2.  Provides fast symbol and text search via MCP protocol.
3.  Synchronizes indexes across a development team (Basic Artifact Sync).
4.  Installing and running is reliable on standard developer environments.

## Current State Analysis

-   **Strengths**: Robust `gateway` implementation, detailed `plugin_system` with dynamic loading, extensive test suite.
-   **Weaknesses**: `sync.py` is a stub (critical for team features), reliance on idealized `ROADMAP` claims vs. actual functioning integration.
-   **Risks**: Complexity of "Production Ready" claims might mask integration bugs.

## Phased Implementation Plan

### Phase 1: Foundation & Cleanup (Weeks 1-2)
**Goal**: Ensure the core indexing and searching works reliably for a single user.

-   **Swim Lane: Core Indexing**
    -   [ ] Verify `SQLiteStore` persistence and schema stability.
    -   [ ] Validate `EnhancedDispatcher` fallback mechanisms (BM25 vs Plugin).
    -   [ ] **Action**: audit `mcp_server/__init__.py` and entry points for correct initialization.
-   **Swim Lane: Operations**
    -   [ ] Clean up `requirements.txt` to match actual imports.
    -   [ ] Verify Docker build for "Minimal" image.

### Phase 2: Synchronization Implementation (Weeks 3-4)
**Goal**: Enable index sharing between developers (The "Rough Edge" Fix).

-   **Swim Lane: Sync Service**
    -   [ ] **Implement `CloudSync` in `mcp_server/sync.py`**.
        -   *Spec*: Must support GitHub Artifacts API or a modular backend (S3/GCS).
        -   *Requirement*: `push_shard(id)` and `pull_shard(id)` must be functional.
    -   [ ] Integrate `SyncService` into `Gateway` startup/shutdown.
-   **Swim Lane: Testing**
    -   [ ] Write unit tests for `sync.py`.
    -   [ ] Create integration test for sync flow (mocking backend).

### Phase 3: Semantic Search & Hybrid Polish (Weeks 5-6)
**Goal**: Enable optional "AI-powered" features without breaking the MVP.

-   **Swim Lane: Search**
    -   [ ] Validate `Qdrant` integration in `mcp_server/utils/semantic_indexer.py`.
    -   [ ] Ensure `HybridSearch` degrades gracefully when Qdrant is missing.
    -   [ ] Improve result ranking in `ResultAggregator`.

### Phase 4: Release & Documentation (Week 7)
**Goal**: Packaging for public consumption.

-   **Swim Lane: Release**
    -   [ ] Create `setup.py` or `pyproject.toml` for easy pip install.
    -   [ ] Finalize `README.md` to reflect *actual* MVP features (remove "100% complete" if Sync is limited).
    -   [ ] Create a "Getting Started" guide that works 100% of the time.

## Architecture

See [System Architecture Maps](./architecture.md) for C4 diagrams.

## Key Technical Decisions

1.  **Sync Backend**: For MVP, prioritize **GitHub Artifacts** as the primary sync backend to align with the "zero cost" promise.
2.  **Plugin Loading**: Keep `lazy_load=True` as default to minimize startup time.
3.  **Database**: Continue with `SQLite` for metadata; ensure WAL mode is enabled for concurrency.

## Success Metrics

-   **Installation Success Rate**: > 90% on fresh environments.
-   **Index Time**: < 10s for medium repo (10k files) using existing index.
-   **Search Latency**: < 200ms for P95 queries.
