# Matrix Benchmark: Rerankers × Embeddings × Retrieval Modes

- Run: `2026-03-29T16:34:40.452256+00:00`
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
| voyage-code-3 / flashrank | voyage-code-3 | flashrank | **14/17** | 16/17 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |
| voyage-code-3 / cross-encoder | voyage-code-3 | cross-encoder | **14/17** | 16/17 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |
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
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 415.59 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 34.3 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 11.97 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 35.72 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `run_e2e_retrieval_validation.py` | 3981.0 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.09 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin_semantic.py` | 433.5 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 14.49 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `matrix_benchmark.json` | 7823.81 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.0 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 0.9 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 0.84 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.84 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.04 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 10.14 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 71542.8 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 0.98 |

### BM25-only / flashrank

Top-1: **10/17** (58.8%)  Top-3: 12/17 (70.6%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 388.54 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 35.35 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 12.15 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 35.14 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `run_e2e_retrieval_validation.py` | 3945.22 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 0.99 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin_semantic.py` | 420.51 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 14.07 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `matrix_benchmark.json` | 7742.29 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.0 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 0.83 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 0.82 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.84 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.8 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 9.89 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 71648.37 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.5 |

### voyage-code-3 / none

Top-1: **14/17** (82.4%)  Top-3: 16/17 (94.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 396.46 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 34.82 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 13.18 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 169.26 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 136.93 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.17 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 145.48 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 15.04 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 140.21 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.32 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 0.93 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 0.89 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 3.85 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.89 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 23.83 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 141.38 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.14 |

### voyage-code-3 / flashrank

Top-1: **14/17** (82.4%)  Top-3: 16/17 (94.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 396.45 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 36.94 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 12.76 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 163.96 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 185.9 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 0.92 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 161.25 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 20.13 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 152.12 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.92 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 0.88 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 0.88 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.87 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.92 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 11.32 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 179.07 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 4.02 |

### voyage-code-3 / cross-encoder

Top-1: **14/17** (82.4%)  Top-3: 16/17 (94.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 388.81 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 37.5 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.19 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 168.37 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 147.41 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 0.86 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 158.6 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 14.81 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 157.64 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.98 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.27 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.2 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.88 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.91 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 11.11 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 148.8 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.02 |

### voyage-code-3 / voyage-reranker

Top-1: **14/17** (82.4%)  Top-3: 16/17 (94.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 383.06 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 35.27 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 12.28 |
| 🔶 | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `setup_commands.py` | 680.78 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 639.11 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.52 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 791.94 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 18.64 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 335.33 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.65 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.18 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.13 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.16 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.05 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 12.81 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 666.04 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 2.68 |

### Qwen/Qwen3-Embedding-8B / none

Top-1: **10/17** (58.8%)  Top-3: 11/17 (64.7%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 387.5 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 34.57 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 11.56 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `(none)` | 425.7 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `(none)` | 44.84 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.91 |
| ❌ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `(none)` | 50.94 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 23.11 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `(none)` | 43.27 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.37 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.37 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.22 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.19 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.2 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 11.32 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `(none)` | 44.19 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.29 |

### Qwen/Qwen3-Embedding-8B / flashrank

Top-1: **10/17** (58.8%)  Top-3: 11/17 (64.7%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 389.9 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 35.21 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 12.62 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `(none)` | 312.31 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `(none)` | 42.42 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.47 |
| ❌ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `(none)` | 41.81 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 19.89 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `(none)` | 42.52 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.35 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.2 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.03 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.01 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.15 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 11.76 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `(none)` | 46.66 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.84 |

### Qwen/Qwen3-Embedding-8B / cross-encoder

Top-1: **10/17** (58.8%)  Top-3: 11/17 (64.7%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `Makefile` | 403.64 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 42.14 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 13.81 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `(none)` | 239.0 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `(none)` | 45.72 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.53 |
| ❌ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `(none)` | 42.58 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 19.82 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `(none)` | 40.48 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.3 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.13 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.1 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.09 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.83 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 10.01 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `(none)` | 46.98 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.25 |

---

## Native Tool Comparison (ripgrep / grep / glob / sed)

**Pass rate: 0/0**

| Backend | Top-1 Pass | Avg Latency (ms) |
|---|:---:|---:|

| Pass | Backend | Query | Expected | Top File | Latency (ms) |
|:---:|---|---|---|---|---:|
