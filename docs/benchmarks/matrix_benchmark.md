# Matrix Benchmark: Rerankers × Embeddings × Retrieval Modes

- Run: `2026-04-01T14:18:59.494469+00:00`
- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Index: `/home/viperjuice/code/Code-Index-MCP/code_index.db`
- Qdrant: `/home/viperjuice/code/Code-Index-MCP/vector_index.qdrant`
- Qdrant points: `25490`
- Queries: 17  |  Limit: 5

## Summary: Top-1 Pass Rate by Configuration

| Configuration | Embedding | Reranker | Top-1 | Top-3 | classic/sem_preflight | bm25/qdrant_auto | fuzzy/sem_preflite | semantic/qdrant_auto | hybrid/setup_cmd | bm25/SemanticIndexer | semantic/treesitter | fuzzy/SemnticIndexer | hybrid/delta | bm25/EnhancedDispatcher(c) | bm25/SQLiteStore(c) | bm25/FlashRank(c) | bm25/VoyageReranker(c) | bm25/EnhancedDisp(bare) | bm25/def_symbol_route | semantic/sym_routing | bm25/CrossEncoder(c) |
|---|---|---|:---:|:---:| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| BM25-only / no-reranker | BM25-only | none | **12/17** | 13/17 | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | 🔶 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| BM25-only / flashrank | BM25-only | flashrank | **13/17** | 15/17 | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | 🔶 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ✅ |
| voyage-code-3 / none | voyage-code-3 | none | **17/17** | 17/17 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| voyage-code-3 / flashrank | voyage-code-3 | flashrank | **17/17** | 17/17 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| voyage-code-3 / cross-encoder | voyage-code-3 | cross-encoder | **17/17** | 17/17 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| voyage-code-3 / voyage-reranker | voyage-code-3 | voyage | **15/17** | 17/17 | ✅ | 🔶 | ✅ | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Qwen/Qwen3-Embedding-8B / none | Qwen/Qwen3-Embedding-8B | none | **17/17** | 17/17 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Qwen/Qwen3-Embedding-8B / flashrank | Qwen/Qwen3-Embedding-8B | flashrank | **17/17** | 17/17 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Qwen/Qwen3-Embedding-8B / cross-encoder | Qwen/Qwen3-Embedding-8B | cross-encoder | **17/17** | 17/17 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Detailed Results per Configuration

### BM25-only / no-reranker

Top-1: **12/17** (70.6%)  Top-3: 13/17 (76.5%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ✅ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `semantic_preflight.py` | 981.55 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 383.91 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 17.85 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 6642.46 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `run_e2e_retrieval_validation.py` | 8360.23 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.43 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin_semantic.py` | 2286.64 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 19.88 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `run_production_benchmark.py` | 15648.43 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.4 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 0.9 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 0.9 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.0 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.19 |
| ✅ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.46 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 143093.56 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 2.67 |

### BM25-only / flashrank

Top-1: **13/17** (76.5%)  Top-3: 15/17 (88.2%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ✅ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `semantic_preflight.py` | 1563.48 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 707.64 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 19.74 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 7037.13 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `semantic_preflight.py` | 8480.94 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 2.15 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `chunker_adapter.py` | 2677.72 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 21.79 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `run_matrix_benchmark.py` | 15935.88 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.19 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.17 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.01 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.96 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.89 |
| ✅ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.46 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `pending_test_prompts.json` | 144047.54 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 2.08 |

### voyage-code-3 / none

Top-1: **17/17** (100.0%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ✅ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `semantic_preflight.py` | 913.78 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 397.05 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 16.55 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 187.73 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 151.52 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.51 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 141.53 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 30.62 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 161.64 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.67 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.41 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.65 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.93 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.57 |
| ✅ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.37 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 145.97 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.21 |

### voyage-code-3 / flashrank

Top-1: **17/17** (100.0%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ✅ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `semantic_preflight.py` | 1473.11 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 647.02 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 18.51 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 138.49 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 152.85 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.51 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 156.05 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 21.74 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 144.86 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 4.99 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 4.57 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.44 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 4.26 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.24 |
| ✅ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.9 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 147.96 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.51 |

### voyage-code-3 / cross-encoder

Top-1: **17/17** (100.0%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ✅ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `semantic_preflight.py` | 2350.47 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 653.8 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 18.05 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 152.27 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 143.75 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.32 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 145.33 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 23.08 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 142.58 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.45 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.61 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.4 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.24 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 0.98 |
| ✅ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.78 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 142.58 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.61 |

### voyage-code-3 / voyage-reranker

Top-1: **15/17** (88.2%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ✅ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `semantic_preflight.py` | 1377.12 |
| 🔶 | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `.env.docker` | 619.2 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 26.44 |
| 🔶 | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `setup_commands.py` | 374.36 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 652.61 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 2.01 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 629.56 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 24.96 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 386.24 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.9 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.41 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.28 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.33 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.24 |
| ✅ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.09 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 812.44 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.96 |

### Qwen/Qwen3-Embedding-8B / none

Top-1: **17/17** (100.0%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ✅ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `semantic_preflight.py` | 950.88 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 407.38 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 16.75 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 224.11 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 58.8 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.95 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 57.99 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 32.04 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 57.16 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.6 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.32 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.2 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.18 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.24 |
| ✅ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.02 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 54.89 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.46 |

### Qwen/Qwen3-Embedding-8B / flashrank

Top-1: **17/17** (100.0%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ✅ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `semantic_preflight.py` | 1475.91 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 666.12 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 18.89 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 60.19 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 54.88 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.47 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 54.18 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 27.92 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 56.93 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.35 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.18 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 4.14 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 4.69 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.05 |
| ✅ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.71 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 58.23 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.45 |

### Qwen/Qwen3-Embedding-8B / cross-encoder

Top-1: **17/17** (100.0%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ✅ | classic | semantic | semantic preflight checks implementation | `semantic_preflight.py` | `semantic_preflight.py` | 2024.6 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 671.13 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 20.17 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 62.53 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 67.65 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.41 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 58.29 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 39.2 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 63.28 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.75 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.42 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.28 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 4.39 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.63 |
| ✅ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.38 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 55.72 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.69 |

---

## Native Tool Comparison (ripgrep / grep / glob / sed)

**Pass rate: 4/68**

| Backend | Top-1 Pass | Avg Latency (ms) |
|---|:---:|---:|
| ripgrep | 0/17 | 26.7 |
| grep | 4/17 | 10545.3 |
| glob | 0/17 | 2346.5 |
| sed | 0/17 | 71.8 |

| Pass | Backend | Query | Expected | Top File | Latency (ms) |
|:---:|---|---|---|---|---:|
| ❌ | ripgrep | semantic preflight checks implementation | `semantic_preflight.py` | `run_matrix_benchmark.py` | 114.24 |
| ❌ | grep | semantic preflight checks implementation | `semantic_preflight.py` | `ERROR:Command '['grep', '-rl', 'semantic preflight checks implementation', '/home/viperjuice/code/Code-Index-MCP']' timed out after 30 seconds` | 30092.92 |
| ❌ | glob | semantic preflight checks implementation | `semantic_preflight.py` | `semantic_indexing_progress.json` | 2618.37 |
| ❌ | sed | semantic preflight checks implementation | `semantic_preflight.py` | `fix_dispatcher_timeout.py` | 62.6 |
| ❌ | ripgrep | qdrant docker compose autostart | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 18.84 |
| ❌ | grep | qdrant docker compose autostart | `qdrant_autostart.py` | `ERROR:Command '['grep', '-rl', 'qdrant docker compose autostart', '/home/viperjuice/code/Code-Index-MCP']' timed out after 30 seconds` | 30098.57 |
| ❌ | glob | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_server_mode.patch` | 2275.58 |
| ❌ | sed | qdrant docker compose autostart | `qdrant_autostart.py` | `fix_qdrant_server_mode.py` | 52.31 |
| ❌ | ripgrep | semntic preflite raport | `semantic_preflight.py` | `e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` | 42.85 |
| ❌ | grep | semntic preflite raport | `semantic_preflight.py` | `e2e_retrieval_validation_fullrepo.md` | 14652.78 |
| ❌ | glob | semntic preflite raport | `semantic_preflight.py` | `(none)` | 2298.79 |
| ❌ | sed | semntic preflite raport | `semantic_preflight.py` | `run_e2e_retrieval_validation.py` | 147.26 |
| ❌ | ripgrep | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 19.85 |
| ❌ | grep | where is qdrant autostart implemented | `qdrant_autostart.py` | `test_dispatcher.py` | 7193.86 |
| ❌ | glob | where is qdrant autostart implemented | `qdrant_autostart.py` | `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` | 2338.07 |
| ❌ | sed | where is qdrant autostart implemented | `qdrant_autostart.py` | `debug_mcp_components.py` | 76.91 |
| ❌ | ripgrep | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `test_benchmark_query_regressions.py` | 20.25 |
| ❌ | grep | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `test_benchmark_query_regressions.py` | 6724.17 |
| ❌ | glob | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `codex-setup.sh` | 2545.12 |
| ❌ | sed | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `coverage_html_cb_dd2e7eb5.js` | 51.33 |
| ❌ | ripgrep | class SemanticIndexer | `semantic_indexer.py` | `run_e2e_retrieval_validation.py` | 21.34 |
| ❌ | grep | class SemanticIndexer | `semantic_indexer.py` | `qdrant_server_mode.patch` | 7444.51 |
| ❌ | glob | class SemanticIndexer | `semantic_indexer.py` | `class_index.html` | 2275.07 |
| ❌ | sed | class SemanticIndexer | `semantic_indexer.py` | `coverage_html_cb_dd2e7eb5.js` | 66.59 |
| ❌ | ripgrep | extract symbols from python using treesitter | `semantic_indexer.py` | `run_e2e_retrieval_validation.py` | 16.99 |
| ❌ | grep | extract symbols from python using treesitter | `semantic_indexer.py` | `query_intent.cpython-312.pyc` | 7154.56 |
| ❌ | glob | extract symbols from python using treesitter | `semantic_indexer.py` | `z_f08e9fa3feeeb918_section_extractor_py.html` | 2406.56 |
| ❌ | sed | extract symbols from python using treesitter | `semantic_indexer.py` | `coverage_html_cb_dd2e7eb5.js` | 69.27 |
| ❌ | ripgrep | SemnticIndexer index_file | `semantic_indexer.py` | `run_production_benchmark.py` | 18.42 |
| ❌ | grep | SemnticIndexer index_file | `semantic_indexer.py` | `e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` | 8264.08 |
| ❌ | glob | SemnticIndexer index_file | `semantic_indexer.py` | `(none)` | 2251.67 |
| ❌ | sed | SemnticIndexer index_file | `semantic_indexer.py` | `(none)` | 133.32 |
| ❌ | ripgrep | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` | 20.19 |
| ❌ | grep | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `query_intent.cpython-312.pyc` | 6919.58 |
| ❌ | glob | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `docker-compose.yml` | 2544.07 |
| ❌ | sed | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `coverage_html_cb_dd2e7eb5.js` | 54.45 |
| ❌ | ripgrep | class EnhancedDispatcher | `dispatcher_enhanced.py` | `comprehensive_real_analysis_1750977545.json` | 23.08 |
| ❌ | grep | class EnhancedDispatcher | `dispatcher_enhanced.py` | `semantic_vs_sql_comparison_1750925968.json` | 7255.91 |
| ❌ | glob | class EnhancedDispatcher | `dispatcher_enhanced.py` | `class_index.html` | 2228.63 |
| ❌ | sed | class EnhancedDispatcher | `dispatcher_enhanced.py` | `coverage_html_cb_dd2e7eb5.js` | 44.77 |
| ❌ | ripgrep | class SQLiteStore | `sqlite_store.py` | `phase1_implementation_plan.md` | 19.67 |
| ❌ | grep | class SQLiteStore | `sqlite_store.py` | `consolidated_performance_data.json` | 7888.17 |
| ❌ | glob | class SQLiteStore | `sqlite_store.py` | `class_index.html` | 2229.33 |
| ❌ | sed | class SQLiteStore | `sqlite_store.py` | `coverage_html_cb_dd2e7eb5.js` | 46.47 |
| ❌ | ripgrep | class FlashRankReranker | `reranker.py` | `matrix_benchmark.md` | 21.77 |
| ✅ | grep | class FlashRankReranker | `reranker.py` | `reranker.py` | 7340.19 |
| ❌ | glob | class FlashRankReranker | `reranker.py` | `class_index.html` | 2256.7 |
| ❌ | sed | class FlashRankReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 41.78 |
| ❌ | ripgrep | class VoyageReranker | `reranker.py` | `matrix_benchmark.md` | 19.24 |
| ✅ | grep | class VoyageReranker | `reranker.py` | `reranker.py` | 7555.92 |
| ❌ | glob | class VoyageReranker | `reranker.py` | `class_index.html` | 2240.88 |
| ❌ | sed | class VoyageReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 69.21 |
| ❌ | ripgrep | EnhancedDispatcher | `dispatcher_enhanced.py` | `feature_test_20250628_190614.json` | 17.8 |
| ❌ | grep | EnhancedDispatcher | `dispatcher_enhanced.py` | `PKG-INFO` | 7712.23 |
| ❌ | glob | EnhancedDispatcher | `dispatcher_enhanced.py` | `(none)` | 2248.49 |
| ❌ | sed | EnhancedDispatcher | `dispatcher_enhanced.py` | `(none)` | 144.02 |
| ❌ | ripgrep | def _symbol_route | `dispatcher_enhanced.py` | `README.md` | 21.33 |
| ✅ | grep | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 8274.21 |
| ❌ | glob | def _symbol_route | `dispatcher_enhanced.py` | `27c37f37d6fb0172def7f568bdf47e2212f344` | 2351.61 |
| ❌ | sed | def _symbol_route | `dispatcher_enhanced.py` | `coverage_html_cb_dd2e7eb5.js` | 44.81 |
| ❌ | ripgrep | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 19.93 |
| ❌ | grep | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `matrix_benchmark.md` | 7483.57 |
| ❌ | glob | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` | 2429.98 |
| ❌ | sed | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `debug_mcp_components.py` | 64.78 |
| ❌ | ripgrep | class CrossEncoderReranker | `reranker.py` | `run_matrix_benchmark.py` | 18.88 |
| ✅ | grep | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 7215.18 |
| ❌ | glob | class CrossEncoderReranker | `reranker.py` | `class_index.html` | 2352.28 |
| ❌ | sed | class CrossEncoderReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 50.65 |
