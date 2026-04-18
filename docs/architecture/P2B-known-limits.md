# P2B Known Limits — Deferred Per-Repo Global State

## Status

These items were intentionally deferred from Phase 2B per the consensus decision
(arch-minimal + arch-parallel) recorded in `plans/phase-plan-v1-p2b.md`.

## Deferred: Process-Global Dispatcher State

`EnhancedDispatcher` retains the following attributes as **process-global singletons**
rather than per-`RepoContext` instances:

| Attribute | Type | Deferred to |
|---|---|---|
| `_semantic_indexer` | `SemanticIndexer` (Qdrant) | P3 — per-repo semantic index |
| `_reranker` | `VoyageReranker / FlashRankReranker / CrossEncoderReranker` | P3 |
| `_plugins` / `_by_lang` / `_loaded_languages` | plugin registry | P3 — `RepoScopedDispatcher` |
| `_file_cache` / `_file_cache_lock` | mtime/size/hash cache | P4 |
| `_graph_builder` / `_graph_analyzer` / `_context_selector` / `_graph_nodes` / `_graph_edges` | call-graph state | P4 — per-repo graph |

## Impact

- **Semantic search** (`SemanticIndexer`) uses a single Qdrant collection path for all
  repos.  Results from different repos are not isolated by `repo_id` at the vector level.
  The BM25 path is correctly scoped to `ctx.sqlite_store`.
- **Plugins** are loaded once per process without per-repo isolation.  `PluginFactory`
  creates plugins with `sqlite_store=None`; they write to whichever store is passed at
  call time via `ctx.sqlite_store`.
- **Graph analysis** (`_graph_nodes`, `_graph_edges`) is process-global and not rebuilt
  per-repo.  `graph_search`, `find_symbol_dependencies`, etc. will reflect a merged
  graph across all repos indexed during the session.

## Why Deferred

- Spec non-goal for P2B: "No per-repo plugin map yet — P3 wraps that in a
  repo-scoped registry."
- `arch-minimal` and `arch-parallel` majority: extracting `ServicePool` in P2B adds
  significant scope with no downstream consumer ready to consume it until P3/P4.
- `arch-clean` dissent recorded: principled improvement to revisit in P3 when
  `RepoScopedDispatcher` is introduced.

## Resolution Plan

- **P3**: Introduce `RepoScopedDispatcher(base: EnhancedDispatcher, ctx: RepoContext)`
  wrapper that carries per-repo plugin map and semantic index reference.
- **P4**: Extract `_graph_*` into a per-repo `GraphSession` tied to `RepoContext`.
  Per-repo watcher events invalidate only the affected repo's graph.
