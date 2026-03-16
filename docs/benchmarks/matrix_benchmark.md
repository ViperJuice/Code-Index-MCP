# Matrix Benchmark: Rerankers × Embeddings × Retrieval Modes

- Run: `2026-03-16T17:44:09.785354+00:00`
- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Index: `/home/viperjuice/code/Code-Index-MCP/code_index.db`
- Qdrant: `/home/viperjuice/code/Code-Index-MCP/vector_index.qdrant`
- Qdrant points: `16262`
- Queries: 17  |  Limit: 5

## Summary: Top-1 Pass Rate by Configuration

| Configuration | Embedding | Reranker | Top-1 | Top-3 | classic/sem_preflight | bm25/qdrant_auto | fuzzy/sem_preflite | semantic/qdrant_auto | hybrid/setup_cmd | bm25/SemanticIndexer | semantic/treesitter | fuzzy/SemnticIndexer | hybrid/delta | bm25/EnhancedDispatcher(c) | bm25/SQLiteStore(c) | bm25/FlashRank(c) | bm25/VoyageReranker(c) | bm25/EnhancedDisp(bare) | bm25/def_symbol_route | semantic/sym_routing | bm25/CrossEncoder(c) |
|---|---|---|:---:|:---:| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| BM25-only / no-reranker | BM25-only | none | **8/17** | 8/17 | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| BM25-only / flashrank | BM25-only | flashrank | **8/17** | 8/17 | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| voyage-code-3 / no-reranker | voyage-code-3 | none | **12/17** | 13/17 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | 🔶 | ❌ |
| voyage-code-3 / flashrank | voyage-code-3 | flashrank | **12/17** | 13/17 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | 🔶 | ❌ |
| voyage-code-3 / voyage-reranker | voyage-code-3 | voyage | **12/17** | 13/17 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | 🔶 | ❌ |
| voyage-code-3 / cross-encoder | voyage-code-3 | cross-encoder | **12/17** | 13/17 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | 🔶 | ❌ |

---

## Detailed Results per Configuration

### BM25-only / no-reranker

Top-1: **8/17** (47.1%)  Top-3: 8/17 (47.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight | `semantic_preflight.py` | `setup_commands.py` | 345.82 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 54.48 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 66.29 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `(none)` | 29668.97 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `(none)` | 1.38 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 3.58 |
| ❌ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `(none)` | 1.59 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 103.52 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `(none)` | 1.58 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.15 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 3.04 |
| ❌ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `(none)` | 9.56 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 2.86 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.12 |
| ❌ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `core.py` | 71.27 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `(none)` | 1.61 |
| ❌ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `CONTEXTUAL_EMBEDDINGS_ARCHITECTURE_UPDATE.md` | 14.79 |

### BM25-only / flashrank

Top-1: **8/17** (47.1%)  Top-3: 8/17 (47.1%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight | `semantic_preflight.py` | `setup_commands.py` | 319.97 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 59.42 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 64.35 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `(none)` | 30343.39 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `(none)` | 2.08 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 4.15 |
| ❌ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `(none)` | 2.07 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 112.11 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `(none)` | 2.35 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.75 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 3.61 |
| ❌ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `(none)` | 8.07 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 3.44 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.35 |
| ❌ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `core.py` | 11.1 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `(none)` | 1.71 |
| ❌ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `CONTEXTUAL_EMBEDDINGS_ARCHITECTURE_UPDATE.md` | 8.62 |

### voyage-code-3 / no-reranker

Top-1: **12/17** (70.6%)  Top-3: 13/17 (76.5%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight | `semantic_preflight.py` | `setup_commands.py` | 343.08 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 68.88 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 69.61 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 132.2 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 117.0 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 3.89 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 115.53 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 141.55 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 234.9 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 6.47 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 6.32 |
| ❌ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `(none)` | 30361.62 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 3.67 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.85 |
| ❌ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `core.py` | 12.75 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 135.42 |
| ❌ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `CONTEXTUAL_EMBEDDINGS_ARCHITECTURE_UPDATE.md` | 12.04 |

### voyage-code-3 / flashrank

Top-1: **12/17** (70.6%)  Top-3: 13/17 (76.5%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight | `semantic_preflight.py` | `setup_commands.py` | 333.68 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 60.37 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 71.35 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 121.59 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 133.53 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 8.44 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 139.26 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 136.67 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 133.54 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 5.54 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 3.63 |
| ❌ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `(none)` | 24072.74 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 3.66 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.49 |
| ❌ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `core.py` | 10.92 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 166.44 |
| ❌ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `CONTEXTUAL_EMBEDDINGS_ARCHITECTURE_UPDATE.md` | 21.79 |

### voyage-code-3 / voyage-reranker

Top-1: **12/17** (70.6%)  Top-3: 13/17 (76.5%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight | `semantic_preflight.py` | `setup_commands.py` | 332.17 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 58.2 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 312.06 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 304.4 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 632.45 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 7.82 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 655.27 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 124.81 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 343.77 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 5.67 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 5.25 |
| ❌ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `(none)` | 24087.77 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 3.67 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.37 |
| ❌ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `core.py` | 10.82 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 587.68 |
| ❌ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `CONTEXTUAL_EMBEDDINGS_ARCHITECTURE_UPDATE.md` | 13.54 |

### voyage-code-3 / cross-encoder

Top-1: **12/17** (70.6%)  Top-3: 13/17 (76.5%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| ❌ | classic | semantic | semantic preflight | `semantic_preflight.py` | `setup_commands.py` | 337.38 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 63.38 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 71.48 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 151.7 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 150.35 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 6.62 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 163.16 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 136.69 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 131.63 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 3.69 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 3.34 |
| ❌ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `(none)` | 18062.41 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 4.26 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 4.26 |
| ❌ | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `core.py` | 12.01 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 146.12 |
| ❌ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `CONTEXTUAL_EMBEDDINGS_ARCHITECTURE_UPDATE.md` | 13.56 |

---

## Native Tool Comparison (ripgrep / grep / glob / sed)

**Pass rate: 4/68**

| Backend | Top-1 Pass | Avg Latency (ms) |
|---|:---:|---:|
| ripgrep | 0/17 | 23.6 |
| grep | 4/17 | 2482.1 |
| glob | 0/17 | 205.0 |
| sed | 0/17 | 66.1 |

| Pass | Backend | Query | Expected | Top File | Latency (ms) |
|:---:|---|---|---|---|---:|
| ❌ | ripgrep | semantic preflight | `semantic_preflight.py` | `run_e2e_retrieval_validation.py` | 81.54 |
| ❌ | grep | semantic preflight | `semantic_preflight.py` | `z_0425c7814bfde65c_semantic_preflight_py.html` | 2521.45 |
| ❌ | glob | semantic preflight | `semantic_preflight.py` | `semantic_indexing_progress.json` | 200.46 |
| ❌ | sed | semantic preflight | `semantic_preflight.py` | `fix_dispatcher_timeout.py` | 57.05 |
| ❌ | ripgrep | qdrant docker compose autostart | `qdrant_autostart.py` | `query_intent.py` | 19.75 |
| ❌ | grep | qdrant docker compose autostart | `qdrant_autostart.py` | `z_e329aef19d4c5371_query_intent_py.html` | 2463.29 |
| ❌ | glob | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_server_mode.patch` | 196.14 |
| ❌ | sed | qdrant docker compose autostart | `qdrant_autostart.py` | `fix_qdrant_server_mode.py` | 42.46 |
| ❌ | ripgrep | semntic preflite raport | `semantic_preflight.py` | `run_e2e_retrieval_validation.py` | 18.4 |
| ❌ | grep | semntic preflite raport | `semantic_preflight.py` | `e2e_retrieval_validation_fullrepo.md` | 2566.95 |
| ❌ | glob | semntic preflite raport | `semantic_preflight.py` | `(none)` | 191.97 |
| ❌ | sed | semntic preflite raport | `semantic_preflight.py` | `run_e2e_retrieval_validation.py` | 130.35 |
| ❌ | ripgrep | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 18.15 |
| ❌ | grep | where is qdrant autostart implemented | `qdrant_autostart.py` | `test_dispatcher.py` | 2357.08 |
| ❌ | glob | where is qdrant autostart implemented | `qdrant_autostart.py` | `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` | 234.73 |
| ❌ | sed | where is qdrant autostart implemented | `qdrant_autostart.py` | `debug_mcp_components.py` | 71.33 |
| ❌ | ripgrep | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `test_benchmark_query_regressions.py` | 18.93 |
| ❌ | grep | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `test_benchmark_query_regressions.py` | 2323.17 |
| ❌ | glob | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `codex-setup.sh` | 213.29 |
| ❌ | sed | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `coverage_html_cb_dd2e7eb5.js` | 49.81 |
| ❌ | ripgrep | class SemanticIndexer | `semantic_indexer.py` | `run_e2e_retrieval_validation.py` | 23.36 |
| ❌ | grep | class SemanticIndexer | `semantic_indexer.py` | `qdrant_server_mode.patch` | 2287.47 |
| ❌ | glob | class SemanticIndexer | `semantic_indexer.py` | `class_index.html` | 204.59 |
| ❌ | sed | class SemanticIndexer | `semantic_indexer.py` | `coverage_html_cb_dd2e7eb5.js` | 42.4 |
| ❌ | ripgrep | extract symbols from python using treesitter | `semantic_indexer.py` | `e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` | 19.56 |
| ❌ | grep | extract symbols from python using treesitter | `semantic_indexer.py` | `query_intent.cpython-312.pyc` | 2411.41 |
| ❌ | glob | extract symbols from python using treesitter | `semantic_indexer.py` | `z_f08e9fa3feeeb918_section_extractor_py.html` | 207.3 |
| ❌ | sed | extract symbols from python using treesitter | `semantic_indexer.py` | `coverage_html_cb_dd2e7eb5.js` | 46.37 |
| ❌ | ripgrep | SemnticIndexer index_file | `semantic_indexer.py` | `run_production_benchmark.py` | 17.05 |
| ❌ | grep | SemnticIndexer index_file | `semantic_indexer.py` | `e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` | 2548.37 |
| ❌ | glob | SemnticIndexer index_file | `semantic_indexer.py` | `(none)` | 208.81 |
| ❌ | sed | SemnticIndexer index_file | `semantic_indexer.py` | `(none)` | 129.37 |
| ❌ | ripgrep | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `run_e2e_retrieval_validation.py` | 21.16 |
| ❌ | grep | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `query_intent.cpython-312.pyc` | 2343.78 |
| ❌ | glob | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `docker-compose.yml` | 227.17 |
| ❌ | sed | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `coverage_html_cb_dd2e7eb5.js` | 73.36 |
| ❌ | ripgrep | class EnhancedDispatcher | `dispatcher_enhanced.py` | `ENHANCED_MCP_VS_NATIVE_COMPREHENSIVE_ANALYSIS.md` | 19.7 |
| ❌ | grep | class EnhancedDispatcher | `dispatcher_enhanced.py` | `semantic_vs_sql_comparison_1750925968.json` | 2210.49 |
| ❌ | glob | class EnhancedDispatcher | `dispatcher_enhanced.py` | `class_index.html` | 189.78 |
| ❌ | sed | class EnhancedDispatcher | `dispatcher_enhanced.py` | `coverage_html_cb_dd2e7eb5.js` | 44.84 |
| ❌ | ripgrep | class SQLiteStore | `sqlite_store.py` | `consolidated_performance_data.json` | 15.76 |
| ❌ | grep | class SQLiteStore | `sqlite_store.py` | `consolidated_performance_data.json` | 2394.67 |
| ❌ | glob | class SQLiteStore | `sqlite_store.py` | `class_index.html` | 190.63 |
| ❌ | sed | class SQLiteStore | `sqlite_store.py` | `coverage_html_cb_dd2e7eb5.js` | 42.7 |
| ❌ | ripgrep | class FlashRankReranker | `reranker.py` | `run_matrix_benchmark.py` | 18.83 |
| ✅ | grep | class FlashRankReranker | `reranker.py` | `reranker.py` | 2976.62 |
| ❌ | glob | class FlashRankReranker | `reranker.py` | `class_index.html` | 195.64 |
| ❌ | sed | class FlashRankReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 43.12 |
| ❌ | ripgrep | class VoyageReranker | `reranker.py` | `run_matrix_benchmark.py` | 29.61 |
| ✅ | grep | class VoyageReranker | `reranker.py` | `reranker.py` | 2407.5 |
| ❌ | glob | class VoyageReranker | `reranker.py` | `class_index.html` | 195.01 |
| ❌ | sed | class VoyageReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 42.12 |
| ❌ | ripgrep | EnhancedDispatcher | `dispatcher_enhanced.py` | `FINAL_MCP_PERFORMANCE_REPORT.md` | 18.33 |
| ❌ | grep | EnhancedDispatcher | `dispatcher_enhanced.py` | `PKG-INFO` | 2325.45 |
| ❌ | glob | EnhancedDispatcher | `dispatcher_enhanced.py` | `(none)` | 195.4 |
| ❌ | sed | EnhancedDispatcher | `dispatcher_enhanced.py` | `(none)` | 164.04 |
| ❌ | ripgrep | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 20.31 |
| ✅ | grep | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2954.63 |
| ❌ | glob | def _symbol_route | `dispatcher_enhanced.py` | `27c37f37d6fb0172def7f568bdf47e2212f344` | 207.15 |
| ❌ | sed | def _symbol_route | `dispatcher_enhanced.py` | `coverage_html_cb_dd2e7eb5.js` | 38.16 |
| ❌ | ripgrep | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 20.09 |
| ❌ | grep | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 2481.06 |
| ❌ | glob | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` | 207.09 |
| ❌ | sed | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `debug_mcp_components.py` | 62.58 |
| ❌ | ripgrep | class CrossEncoderReranker | `reranker.py` | `run_matrix_benchmark.py` | 21.14 |
| ✅ | grep | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 2622.08 |
| ❌ | glob | class CrossEncoderReranker | `reranker.py` | `class_index.html` | 219.56 |
| ❌ | sed | class CrossEncoderReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 44.47 |
