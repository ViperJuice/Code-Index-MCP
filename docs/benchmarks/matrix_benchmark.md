# Matrix Benchmark: Rerankers × Embeddings × Retrieval Modes

- Run: `2026-03-29T18:43:13.431023+00:00`
- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Index: `/home/viperjuice/code/Code-Index-MCP/code_index.db`
- Qdrant: `/home/viperjuice/code/Code-Index-MCP/vector_index.qdrant`
- Qdrant points: `6766`
- Queries: 17  |  Limit: 5

## Summary: Top-1 Pass Rate by Configuration

| Configuration | Embedding | Reranker | Top-1 | Top-3 | classic/sem_preflight | bm25/qdrant_auto | fuzzy/sem_preflite | semantic/qdrant_auto | hybrid/setup_cmd | bm25/SemanticIndexer | semantic/treesitter | fuzzy/SemnticIndexer | hybrid/delta | bm25/EnhancedDispatcher(c) | bm25/SQLiteStore(c) | bm25/FlashRank(c) | bm25/VoyageReranker(c) | bm25/EnhancedDisp(bare) | bm25/def_symbol_route | semantic/sym_routing | bm25/CrossEncoder(c) |
|---|---|---|:---:|:---:| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| BM25-only / no-reranker | BM25-only | none | **10/17** | 12/17 | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | 🔶 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |
| BM25-only / flashrank | BM25-only | flashrank | **10/17** | 12/17 | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | 🔶 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |
| voyage-code-3 / none | voyage-code-3 | none | **14/17** | 16/17 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |
| voyage-code-3 / flashrank | voyage-code-3 | flashrank | **13/17** | 16/17 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |
| voyage-code-3 / cross-encoder | voyage-code-3 | cross-encoder | **12/17** | 15/17 | ❌ | ✅ | ✅ | 🔶 | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |
| voyage-code-3 / voyage-reranker | voyage-code-3 | voyage | **14/17** | 16/17 | ❌ | ✅ | ✅ | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ✅ | ✅ |
| Qwen/Qwen3-Embedding-8B / none | Qwen/Qwen3-Embedding-8B | none | **10/17** | 11/17 | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |
| Qwen/Qwen3-Embedding-8B / flashrank | Qwen/Qwen3-Embedding-8B | flashrank | **10/17** | 11/17 | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |
| Qwen/Qwen3-Embedding-8B / cross-encoder | Qwen/Qwen3-Embedding-8B | cross-encoder | **10/17** | 11/17 | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |

---

## Detailed Results per Configuration

### BM25-only / no-reranker

Top-1: **10/17** (58.8%)  Top-3: 12/17 (70.6%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 443.51 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 38.11 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 11.76 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 34.66 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `run_e2e_retrieval_validation.py` | 3900.06 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.04 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin_semantic.py` | 447.52 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 15.79 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `matrix_benchmark.json` | 7847.26 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.12 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 0.91 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 0.87 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.82 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.02 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 10.18 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 72011.22 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 0.95 |

### BM25-only / flashrank

Top-1: **10/17** (58.8%)  Top-3: 12/17 (70.6%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 403.71 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 34.5 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 13.51 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 34.76 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `run_e2e_retrieval_validation.py` | 4010.32 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.19 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin_semantic.py` | 431.7 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 117.92 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `matrix_benchmark.json` | 7858.28 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.03 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 0.86 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 0.87 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.82 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.83 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 9.92 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 71721.9 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.28 |

### voyage-code-3 / none

Top-1: **14/17** (82.4%)  Top-3: 16/17 (94.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 430.47 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 34.04 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 11.79 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 183.88 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 150.19 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.25 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 140.96 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 14.24 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 166.03 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.23 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.22 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.09 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.93 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.83 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 9.4 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 152.24 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 4.14 |

### voyage-code-3 / flashrank

Top-1: **13/17** (76.5%)  Top-3: 16/17 (94.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 415.88 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 34.34 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 12.12 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 1436.36 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 556.67 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.35 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin.py` | 528.89 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 17.47 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 568.01 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.38 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 0.97 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 0.88 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.86 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.58 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 12.26 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 627.0 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.4 |

### voyage-code-3 / cross-encoder

Top-1: **12/17** (70.6%)  Top-3: 15/17 (88.2%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 400.7 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 35.81 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 13.29 |
| 🔶 | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `setup_commands.py` | 3083.11 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 594.67 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.3 |
| ❌ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin.py` | 529.2 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 17.32 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 566.34 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.48 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 0.86 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 0.8 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.79 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.83 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 10.56 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 667.39 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.75 |

### voyage-code-3 / voyage-reranker

Top-1: **14/17** (82.4%)  Top-3: 16/17 (94.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 400.78 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 37.78 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 13.3 |
| 🔶 | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `setup_commands.py` | 594.71 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 601.18 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.84 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 600.73 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 24.48 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 346.36 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.14 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.71 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.63 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.49 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.57 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 18.06 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 562.68 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.73 |

### Qwen/Qwen3-Embedding-8B / none

Top-1: **10/17** (58.8%)  Top-3: 11/17 (64.7%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 393.34 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 44.32 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 13.94 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `(none)` | 283.32 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `(none)` | 42.68 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.36 |
| ❌ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `(none)` | 42.62 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 18.01 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `(none)` | 44.97 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.36 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.19 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.06 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.06 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.98 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 11.37 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `(none)` | 43.1 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.57 |

### Qwen/Qwen3-Embedding-8B / flashrank

Top-1: **10/17** (58.8%)  Top-3: 11/17 (64.7%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 412.5 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 37.98 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 13.73 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `(none)` | 267.78 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `(none)` | 37.35 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.36 |
| ❌ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `(none)` | 40.19 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 24.45 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `(none)` | 44.53 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.74 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.39 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.28 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.27 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.07 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 10.28 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `(none)` | 40.88 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.19 |

### Qwen/Qwen3-Embedding-8B / cross-encoder

Top-1: **10/17** (58.8%)  Top-3: 11/17 (64.7%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 412.89 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 35.66 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 375.47 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `(none)` | 1051.77 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `(none)` | 45.89 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.71 |
| ❌ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `(none)` | 42.67 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 20.56 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `(none)` | 41.06 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.59 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.16 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.04 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.99 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.01 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 10.93 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `(none)` | 46.69 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.25 |

---

## Native Tool Comparison (ripgrep / grep / glob / sed)

**Pass rate: 0/0**

| Backend | Top-1 Pass | Avg Latency (ms) |
|---|:---:|---:|

| Pass | Backend | Query | Expected | Top File | Latency (ms) |
|:---:|---|---|---|---|---:|
