# Matrix Benchmark: Rerankers × Embeddings × Retrieval Modes

- Run: `2026-03-29T14:28:07.948918+00:00`
- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Index: `/home/viperjuice/code/Code-Index-MCP/code_index.db`
- Qdrant: `/home/viperjuice/code/Code-Index-MCP/vector_index.qdrant`
- Qdrant points: `30212`
- Queries: 17  |  Limit: 5

## Summary: Top-1 Pass Rate by Configuration

| Configuration | Embedding | Reranker | Top-1 | Top-3 | classic/sem_preflight | bm25/qdrant_auto | fuzzy/sem_preflite | semantic/qdrant_auto | hybrid/setup_cmd | bm25/SemanticIndexer | semantic/treesitter | fuzzy/SemnticIndexer | hybrid/delta | bm25/EnhancedDispatcher(c) | bm25/SQLiteStore(c) | bm25/FlashRank(c) | bm25/VoyageReranker(c) | bm25/EnhancedDisp(bare) | bm25/def_symbol_route | semantic/sym_routing | bm25/CrossEncoder(c) |
|---|---|---|:---:|:---:| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| BM25-only / no-reranker | BM25-only | none | **10/17** | 13/17 | 🔶 | ✅ | ✅ | ❌ | ❌ | ✅ | 🔶 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |
| BM25-only / flashrank | BM25-only | flashrank | **10/17** | 13/17 | 🔶 | ✅ | ✅ | ❌ | ❌ | ✅ | 🔶 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |
| voyage-code-3 / none | voyage-code-3 | none | **14/17** | 17/17 | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |
| voyage-code-3 / flashrank | voyage-code-3 | flashrank | **14/17** | 17/17 | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |
| voyage-code-3 / cross-encoder | voyage-code-3 | cross-encoder | **14/17** | 17/17 | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |
| voyage-code-3 / voyage-reranker | voyage-code-3 | voyage | **14/17** | 17/17 | 🔶 | ✅ | ✅ | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ✅ | ✅ |
| Qwen/Qwen3-Embedding-8B / none | Qwen/Qwen3-Embedding-8B | none | **14/17** | 16/17 | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |
| Qwen/Qwen3-Embedding-8B / flashrank | Qwen/Qwen3-Embedding-8B | flashrank | **14/17** | 16/17 | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |
| Qwen/Qwen3-Embedding-8B / cross-encoder | Qwen/Qwen3-Embedding-8B | cross-encoder | **14/17** | 16/17 | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |

---

## Detailed Results per Configuration

### BM25-only / no-reranker

Top-1: **10/17** (58.8%)  Top-3: 13/17 (76.5%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 1492.72 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 52.11 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 107.77 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 59.17 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `matrix_benchmark.json` | 3911.82 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 2.44 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin_semantic.py` | 519.55 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 106.39 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `matrix_benchmark.json` | 7702.92 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.35 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.22 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.11 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.11 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.29 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 33.21 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `matrix_benchmark.json` | 72746.51 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.19 |

### BM25-only / flashrank

Top-1: **10/17** (58.8%)  Top-3: 13/17 (76.5%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 302.82 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 36.37 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.11 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 36.69 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `matrix_benchmark.json` | 3878.32 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.3 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin_semantic.py` | 420.41 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 17.83 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `matrix_benchmark.json` | 7680.91 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.26 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.11 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.09 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.1 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.1 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 12.49 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `matrix_benchmark.json` | 71844.99 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.16 |

### voyage-code-3 / none

Top-1: **14/17** (82.4%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 305.99 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 38.5 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.84 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 353.37 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 145.2 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.49 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 130.78 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 23.02 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 147.07 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.04 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.89 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.5 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.34 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.25 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 14.42 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 140.74 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 4.37 |

### voyage-code-3 / flashrank

Top-1: **14/17** (82.4%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 355.49 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 41.25 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 15.1 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 182.68 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 174.82 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.51 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 208.29 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 31.48 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 169.63 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.42 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 2.61 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.21 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.28 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.33 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 21.47 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 159.26 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 2.62 |

### voyage-code-3 / cross-encoder

Top-1: **14/17** (82.4%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 338.07 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 38.6 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.93 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 157.62 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 158.15 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.52 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 181.0 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 19.64 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 169.85 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.38 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 3.45 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.58 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.2 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.41 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 16.59 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 155.44 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.35 |

### voyage-code-3 / voyage-reranker

Top-1: **14/17** (82.4%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 346.3 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 40.65 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.72 |
| 🔶 | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `setup_commands.py` | 322.46 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 703.52 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 3.45 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 721.91 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 32.28 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 385.76 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.03 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 2.55 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 2.42 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 2.41 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.41 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 19.48 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 724.58 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 2.44 |

### Qwen/Qwen3-Embedding-8B / none

Top-1: **14/17** (82.4%)  Top-3: 16/17 (94.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 340.92 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 37.08 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.06 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 374.53 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 54.34 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.5 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 52.98 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 19.4 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 58.31 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.59 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.26 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.16 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.24 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.14 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 24.89 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 55.9 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.47 |

### Qwen/Qwen3-Embedding-8B / flashrank

Top-1: **14/17** (82.4%)  Top-3: 16/17 (94.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 339.6 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 37.93 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.69 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 78.67 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 97.37 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 4.24 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 91.81 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 34.19 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 64.15 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.09 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.11 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.09 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.1 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.36 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 13.51 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 74.93 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.17 |

### Qwen/Qwen3-Embedding-8B / cross-encoder

Top-1: **14/17** (82.4%)  Top-3: 16/17 (94.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 336.94 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 38.48 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.84 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 74.03 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 91.83 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.12 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 62.87 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 32.91 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 73.22 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.17 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.22 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.32 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.25 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.25 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 18.77 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 63.44 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.11 |

---

## Native Tool Comparison (ripgrep / grep / glob / sed)

**Pass rate: 5/68**

| Backend | Top-1 Pass | Avg Latency (ms) |
|---|:---:|---:|
| ripgrep | 1/17 | 21.3 |
| grep | 4/17 | 5926.8 |
| glob | 0/17 | 2108.8 |
| sed | 0/17 | 68.1 |

| Pass | Backend | Query | Expected | Top File | Latency (ms) |
|:---:|---|---|---|---|---:|
| ❌ | ripgrep | semantic preflight | `semantic_preflight.py` | `README.md` | 53.1 |
| ❌ | grep | semantic preflight | `semantic_preflight.py` | `ERROR:Command '['grep', '-rl', 'semantic preflight', '/home/viperjuice/code/Code-Index-MCP']' timed out after 30 seconds` | 30018.71 |
| ❌ | glob | semantic preflight | `semantic_preflight.py` | `semantic_indexing_progress.json` | 2172.03 |
| ❌ | sed | semantic preflight | `semantic_preflight.py` | `fix_dispatcher_timeout.py` | 49.57 |
| ❌ | ripgrep | qdrant docker compose autostart | `qdrant_autostart.py` | `test_dispatcher.py` | 19.78 |
| ❌ | grep | qdrant docker compose autostart | `qdrant_autostart.py` | `z_e329aef19d4c5371_query_intent_py.html` | 6091.23 |
| ❌ | glob | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_server_mode.patch` | 2123.87 |
| ❌ | sed | qdrant docker compose autostart | `qdrant_autostart.py` | `fix_qdrant_server_mode.py` | 46.15 |
| ❌ | ripgrep | semntic preflite raport | `semantic_preflight.py` | `run_production_benchmark.py` | 19.81 |
| ❌ | grep | semntic preflite raport | `semantic_preflight.py` | `e2e_retrieval_validation_fullrepo.md` | 5109.24 |
| ❌ | glob | semntic preflite raport | `semantic_preflight.py` | `(none)` | 2054.32 |
| ❌ | sed | semntic preflite raport | `semantic_preflight.py` | `run_e2e_retrieval_validation.py` | 134.64 |
| ❌ | ripgrep | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_production_benchmark.py` | 19.13 |
| ❌ | grep | where is qdrant autostart implemented | `qdrant_autostart.py` | `test_dispatcher.py` | 4160.59 |
| ❌ | glob | where is qdrant autostart implemented | `qdrant_autostart.py` | `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` | 2130.99 |
| ❌ | sed | where is qdrant autostart implemented | `qdrant_autostart.py` | `debug_mcp_components.py` | 73.2 |
| ❌ | ripgrep | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `run_e2e_retrieval_validation.py` | 21.02 |
| ❌ | grep | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `test_benchmark_query_regressions.py` | 4011.48 |
| ❌ | glob | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `codex-setup.sh` | 2259.33 |
| ❌ | sed | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `coverage_html_cb_dd2e7eb5.js` | 68.93 |
| ❌ | ripgrep | class SemanticIndexer | `semantic_indexer.py` | `qdrant_server_mode.patch` | 13.88 |
| ❌ | grep | class SemanticIndexer | `semantic_indexer.py` | `qdrant_server_mode.patch` | 4021.04 |
| ❌ | glob | class SemanticIndexer | `semantic_indexer.py` | `class_index.html` | 2009.05 |
| ❌ | sed | class SemanticIndexer | `semantic_indexer.py` | `coverage_html_cb_dd2e7eb5.js` | 47.0 |
| ❌ | ripgrep | extract symbols from python using treesitter | `semantic_indexer.py` | `run_e2e_retrieval_validation.py` | 19.08 |
| ❌ | grep | extract symbols from python using treesitter | `semantic_indexer.py` | `query_intent.cpython-312.pyc` | 4233.03 |
| ❌ | glob | extract symbols from python using treesitter | `semantic_indexer.py` | `z_f08e9fa3feeeb918_section_extractor_py.html` | 2265.54 |
| ❌ | sed | extract symbols from python using treesitter | `semantic_indexer.py` | `coverage_html_cb_dd2e7eb5.js` | 46.45 |
| ❌ | ripgrep | SemnticIndexer index_file | `semantic_indexer.py` | `e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` | 19.05 |
| ❌ | grep | SemnticIndexer index_file | `semantic_indexer.py` | `e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` | 4970.39 |
| ❌ | glob | SemnticIndexer index_file | `semantic_indexer.py` | `(none)` | 2007.97 |
| ❌ | sed | SemnticIndexer index_file | `semantic_indexer.py` | `(none)` | 131.62 |
| ❌ | ripgrep | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `run_e2e_retrieval_validation.py` | 27.36 |
| ❌ | grep | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `query_intent.cpython-312.pyc` | 4047.74 |
| ❌ | glob | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `docker-compose.yml` | 2258.33 |
| ❌ | sed | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `coverage_html_cb_dd2e7eb5.js` | 52.8 |
| ❌ | ripgrep | class EnhancedDispatcher | `dispatcher_enhanced.py` | `path_management_architecture.md` | 17.93 |
| ❌ | grep | class EnhancedDispatcher | `dispatcher_enhanced.py` | `semantic_vs_sql_comparison_1750925968.json` | 3990.11 |
| ❌ | glob | class EnhancedDispatcher | `dispatcher_enhanced.py` | `class_index.html` | 1942.23 |
| ❌ | sed | class EnhancedDispatcher | `dispatcher_enhanced.py` | `coverage_html_cb_dd2e7eb5.js` | 44.86 |
| ❌ | ripgrep | class SQLiteStore | `sqlite_store.py` | `raw_results_20250628_055033.json` | 18.81 |
| ❌ | grep | class SQLiteStore | `sqlite_store.py` | `consolidated_performance_data.json` | 4401.75 |
| ❌ | glob | class SQLiteStore | `sqlite_store.py` | `class_index.html` | 2012.22 |
| ❌ | sed | class SQLiteStore | `sqlite_store.py` | `coverage_html_cb_dd2e7eb5.js` | 45.37 |
| ❌ | ripgrep | class FlashRankReranker | `reranker.py` | `matrix_benchmark.md` | 18.8 |
| ✅ | grep | class FlashRankReranker | `reranker.py` | `reranker.py` | 4033.62 |
| ❌ | glob | class FlashRankReranker | `reranker.py` | `class_index.html` | 2025.44 |
| ❌ | sed | class FlashRankReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 55.9 |
| ✅ | ripgrep | class VoyageReranker | `reranker.py` | `reranker.py` | 17.1 |
| ✅ | grep | class VoyageReranker | `reranker.py` | `reranker.py` | 4174.41 |
| ❌ | glob | class VoyageReranker | `reranker.py` | `class_index.html` | 2110.73 |
| ❌ | sed | class VoyageReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 47.15 |
| ❌ | ripgrep | EnhancedDispatcher | `dispatcher_enhanced.py` | `test_queries.json` | 16.35 |
| ❌ | grep | EnhancedDispatcher | `dispatcher_enhanced.py` | `PKG-INFO` | 4154.12 |
| ❌ | glob | EnhancedDispatcher | `dispatcher_enhanced.py` | `(none)` | 2033.56 |
| ❌ | sed | EnhancedDispatcher | `dispatcher_enhanced.py` | `(none)` | 143.79 |
| ❌ | ripgrep | def _symbol_route | `dispatcher_enhanced.py` | `matrix_benchmark.md` | 21.33 |
| ✅ | grep | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 4852.41 |
| ❌ | glob | def _symbol_route | `dispatcher_enhanced.py` | `27c37f37d6fb0172def7f568bdf47e2212f344` | 2080.17 |
| ❌ | sed | def _symbol_route | `dispatcher_enhanced.py` | `coverage_html_cb_dd2e7eb5.js` | 44.62 |
| ❌ | ripgrep | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 19.14 |
| ❌ | grep | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `matrix_benchmark.md` | 4513.44 |
| ❌ | glob | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` | 2271.5 |
| ❌ | sed | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `debug_mcp_components.py` | 80.31 |
| ❌ | ripgrep | class CrossEncoderReranker | `reranker.py` | `contextual_embeddings.puml` | 21.15 |
| ✅ | grep | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 3972.38 |
| ❌ | glob | class CrossEncoderReranker | `reranker.py` | `class_index.html` | 2092.85 |
| ❌ | sed | class CrossEncoderReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 45.04 |
