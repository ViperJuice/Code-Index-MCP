# Matrix Benchmark: Rerankers × Embeddings × Retrieval Modes

- Run: `2026-03-19T03:49:06.171108+00:00`
- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Index: `/home/viperjuice/code/Code-Index-MCP/code_index.db`
- Qdrant: `/home/viperjuice/code/Code-Index-MCP/vector_index.qdrant`
- Qdrant points: `28512`
- Queries: 17  |  Limit: 5

## Summary: Top-1 Pass Rate by Configuration

| Configuration | Embedding | Reranker | Top-1 | Top-3 | classic/sem_preflight | bm25/qdrant_auto | fuzzy/sem_preflite | semantic/qdrant_auto | hybrid/setup_cmd | bm25/SemanticIndexer | semantic/treesitter | fuzzy/SemnticIndexer | hybrid/delta | bm25/EnhancedDispatcher(c) | bm25/SQLiteStore(c) | bm25/FlashRank(c) | bm25/VoyageReranker(c) | bm25/EnhancedDisp(bare) | bm25/def_symbol_route | semantic/sym_routing | bm25/CrossEncoder(c) |
|---|---|---|:---:|:---:| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| BM25-only / no-reranker | BM25-only | none | **10/17** | 13/17 | 🔶 | ✅ | ✅ | ❌ | ❌ | ✅ | 🔶 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |
| BM25-only / flashrank | BM25-only | flashrank | **10/17** | 13/17 | 🔶 | ✅ | ✅ | ❌ | ❌ | ✅ | 🔶 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ❌ | ✅ |
| voyage-code-3 / no-reranker | voyage-code-3 | none | **14/17** | 17/17 | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |
| voyage-code-3 / flashrank | voyage-code-3 | flashrank | **14/17** | 17/17 | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |
| voyage-code-3 / voyage-reranker | voyage-code-3 | voyage | **14/17** | 17/17 | 🔶 | ✅ | ✅ | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | ✅ | ✅ |
| voyage-code-3 / cross-encoder | voyage-code-3 | cross-encoder | **14/17** | 17/17 | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔶 | 🔶 | ✅ |

---

## Detailed Results per Configuration

### BM25-only / no-reranker

Top-1: **10/17** (58.8%)  Top-3: 13/17 (76.5%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 1390.45 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 54.39 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 113.0 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 49.58 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `matrix_benchmark.json` | 3851.03 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 2.35 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin_semantic.py` | 513.51 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 121.0 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `matrix_benchmark.json` | 7749.27 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.17 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.22 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.18 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.96 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.13 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 44.71 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `matrix_benchmark.json` | 71496.27 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.22 |

### BM25-only / flashrank

Top-1: **10/17** (58.8%)  Top-3: 13/17 (76.5%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 292.74 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 36.72 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.83 |
| ❌ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 34.33 |
| ❌ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `matrix_benchmark.json` | 3865.89 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.28 |
| 🔶 | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `plugin_semantic.py` | 432.68 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 19.77 |
| ❌ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `matrix_benchmark.json` | 7784.77 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.18 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.0 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 0.96 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 0.96 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.01 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 12.16 |
| ❌ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `matrix_benchmark.json` | 71687.54 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.08 |

### voyage-code-3 / no-reranker

Top-1: **14/17** (82.4%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 319.68 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 37.07 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.6 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 145.03 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 129.87 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 5.54 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 116.79 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 20.1 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 113.07 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.94 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.6 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.51 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.37 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.31 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 18.79 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 119.7 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.37 |

### voyage-code-3 / flashrank

Top-1: **14/17** (82.4%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 340.52 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 35.88 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.34 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 158.37 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 142.62 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.04 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 142.62 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 18.44 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 144.9 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.25 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.37 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 3.5 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.32 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 4.19 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 15.91 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 125.12 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.18 |

### voyage-code-3 / voyage-reranker

Top-1: **14/17** (82.4%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 338.7 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 37.82 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.64 |
| 🔶 | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `setup_commands.py` | 349.68 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 642.32 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.94 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 611.04 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 24.35 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 286.48 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2.1 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.63 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.34 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.35 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.35 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 13.95 |
| ✅ | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 529.18 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 2.2 |

### voyage-code-3 / cross-encoder

Top-1: **14/17** (82.4%)  Top-3: 17/17 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50ms |
|:---:|---|---|---|---|---|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `gateway.py` | 339.99 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 37.5 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 14.52 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 171.0 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 142.79 |
| ✅ | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `semantic_indexer.py` | 1.25 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 159.97 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 43.12 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 139.69 |
| ✅ | bm25 | symbol_precise | class EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.17 |
| ✅ | bm25 | symbol_precise | class SQLiteStore | `sqlite_store.py` | `sqlite_store.py` | 1.15 |
| ✅ | bm25 | symbol_precise | class FlashRankReranker | `reranker.py` | `reranker.py` | 1.1 |
| ✅ | bm25 | symbol_precise | class VoyageReranker | `reranker.py` | `reranker.py` | 1.11 |
| ✅ | bm25 | symbol_precise | EnhancedDispatcher | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 1.44 |
| 🔶 | bm25 | symbol_precise | def _symbol_route | `dispatcher_enhanced.py` | `run_matrix_benchmark.py` | 13.8 |
| 🔶 | semantic | semantic_intent | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `routing_policy.py` | 130.13 |
| ✅ | bm25 | symbol_precise | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 1.38 |

---

## Native Tool Comparison (ripgrep / grep / glob / sed)

**Pass rate: 7/68**

| Backend | Top-1 Pass | Avg Latency (ms) |
|---|:---:|---:|
| ripgrep | 3/17 | 20.7 |
| grep | 4/17 | 2512.4 |
| glob | 0/17 | 198.8 |
| sed | 0/17 | 64.5 |

| Pass | Backend | Query | Expected | Top File | Latency (ms) |
|:---:|---|---|---|---|---:|
| ❌ | ripgrep | semantic preflight | `semantic_preflight.py` | `run_production_benchmark.py` | 48.18 |
| ❌ | grep | semantic preflight | `semantic_preflight.py` | `z_0425c7814bfde65c_semantic_preflight_py.html` | 2629.08 |
| ❌ | glob | semantic preflight | `semantic_preflight.py` | `semantic_indexing_progress.json` | 193.21 |
| ❌ | sed | semantic preflight | `semantic_preflight.py` | `fix_dispatcher_timeout.py` | 42.74 |
| ❌ | ripgrep | qdrant docker compose autostart | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 19.22 |
| ❌ | grep | qdrant docker compose autostart | `qdrant_autostart.py` | `z_e329aef19d4c5371_query_intent_py.html` | 2444.65 |
| ❌ | glob | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_server_mode.patch` | 202.87 |
| ❌ | sed | qdrant docker compose autostart | `qdrant_autostart.py` | `fix_qdrant_server_mode.py` | 43.76 |
| ❌ | ripgrep | semntic preflite raport | `semantic_preflight.py` | `run_e2e_retrieval_validation.py` | 19.84 |
| ❌ | grep | semntic preflite raport | `semantic_preflight.py` | `e2e_retrieval_validation_fullrepo.md` | 3144.62 |
| ❌ | glob | semntic preflite raport | `semantic_preflight.py` | `(none)` | 187.3 |
| ❌ | sed | semntic preflite raport | `semantic_preflight.py` | `run_e2e_retrieval_validation.py` | 148.34 |
| ❌ | ripgrep | where is qdrant autostart implemented | `qdrant_autostart.py` | `e2e_retrieval_validation_fullrepo.md` | 22.02 |
| ❌ | grep | where is qdrant autostart implemented | `qdrant_autostart.py` | `test_dispatcher.py` | 2548.57 |
| ❌ | glob | where is qdrant autostart implemented | `qdrant_autostart.py` | `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` | 192.24 |
| ❌ | sed | where is qdrant autostart implemented | `qdrant_autostart.py` | `debug_mcp_components.py` | 60.08 |
| ❌ | ripgrep | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `e2e_retrieval_validation_fullrepo.md` | 18.64 |
| ❌ | grep | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `test_benchmark_query_regressions.py` | 2498.48 |
| ❌ | glob | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `codex-setup.sh` | 216.93 |
| ❌ | sed | how does semantic setup validate qdrant and embedd | `setup_commands.py` | `coverage_html_cb_dd2e7eb5.js` | 49.74 |
| ❌ | ripgrep | class SemanticIndexer | `semantic_indexer.py` | `e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` | 23.08 |
| ❌ | grep | class SemanticIndexer | `semantic_indexer.py` | `qdrant_server_mode.patch` | 2191.96 |
| ❌ | glob | class SemanticIndexer | `semantic_indexer.py` | `class_index.html` | 219.51 |
| ❌ | sed | class SemanticIndexer | `semantic_indexer.py` | `coverage_html_cb_dd2e7eb5.js` | 36.18 |
| ❌ | ripgrep | extract symbols from python using treesitter | `semantic_indexer.py` | `run_e2e_retrieval_validation.py` | 14.71 |
| ❌ | grep | extract symbols from python using treesitter | `semantic_indexer.py` | `query_intent.cpython-312.pyc` | 2499.46 |
| ❌ | glob | extract symbols from python using treesitter | `semantic_indexer.py` | `z_f08e9fa3feeeb918_section_extractor_py.html` | 195.87 |
| ❌ | sed | extract symbols from python using treesitter | `semantic_indexer.py` | `coverage_html_cb_dd2e7eb5.js` | 45.8 |
| ❌ | ripgrep | SemnticIndexer index_file | `semantic_indexer.py` | `production_benchmark.json` | 20.0 |
| ❌ | grep | SemnticIndexer index_file | `semantic_indexer.py` | `e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` | 3083.14 |
| ❌ | glob | SemnticIndexer index_file | `semantic_indexer.py` | `(none)` | 184.7 |
| ❌ | sed | SemnticIndexer index_file | `semantic_indexer.py` | `(none)` | 161.43 |
| ❌ | ripgrep | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `run_e2e_retrieval_validation.py` | 21.16 |
| ❌ | grep | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `query_intent.cpython-312.pyc` | 2490.45 |
| ❌ | glob | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `docker-compose.yml` | 209.23 |
| ❌ | sed | how do artifact push pull and delta resolution wor | `delta_resolver.py` | `coverage_html_cb_dd2e7eb5.js` | 46.52 |
| ❌ | ripgrep | class EnhancedDispatcher | `dispatcher_enhanced.py` | `CONCRETE_EXAMPLES_SHOWCASE.md` | 14.08 |
| ❌ | grep | class EnhancedDispatcher | `dispatcher_enhanced.py` | `semantic_vs_sql_comparison_1750925968.json` | 2147.58 |
| ❌ | glob | class EnhancedDispatcher | `dispatcher_enhanced.py` | `class_index.html` | 187.96 |
| ❌ | sed | class EnhancedDispatcher | `dispatcher_enhanced.py` | `coverage_html_cb_dd2e7eb5.js` | 41.99 |
| ❌ | ripgrep | class SQLiteStore | `sqlite_store.py` | `consolidated_performance_data.csv` | 19.39 |
| ❌ | grep | class SQLiteStore | `sqlite_store.py` | `consolidated_performance_data.json` | 2301.29 |
| ❌ | glob | class SQLiteStore | `sqlite_store.py` | `class_index.html` | 200.62 |
| ❌ | sed | class SQLiteStore | `sqlite_store.py` | `coverage_html_cb_dd2e7eb5.js` | 60.14 |
| ✅ | ripgrep | class FlashRankReranker | `reranker.py` | `reranker.py` | 19.02 |
| ✅ | grep | class FlashRankReranker | `reranker.py` | `reranker.py` | 2281.71 |
| ❌ | glob | class FlashRankReranker | `reranker.py` | `class_index.html` | 193.03 |
| ❌ | sed | class FlashRankReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 41.98 |
| ✅ | ripgrep | class VoyageReranker | `reranker.py` | `reranker.py` | 20.4 |
| ✅ | grep | class VoyageReranker | `reranker.py` | `reranker.py` | 2322.25 |
| ❌ | glob | class VoyageReranker | `reranker.py` | `class_index.html` | 192.06 |
| ❌ | sed | class VoyageReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 41.95 |
| ❌ | ripgrep | EnhancedDispatcher | `dispatcher_enhanced.py` | `ENHANCED_MCP_VS_NATIVE_COMPREHENSIVE_ANALYSIS.md` | 19.17 |
| ❌ | grep | EnhancedDispatcher | `dispatcher_enhanced.py` | `PKG-INFO` | 2258.61 |
| ❌ | glob | EnhancedDispatcher | `dispatcher_enhanced.py` | `(none)` | 215.14 |
| ❌ | sed | EnhancedDispatcher | `dispatcher_enhanced.py` | `(none)` | 142.24 |
| ❌ | ripgrep | def _symbol_route | `dispatcher_enhanced.py` | `matrix_benchmark.md` | 17.0 |
| ✅ | grep | def _symbol_route | `dispatcher_enhanced.py` | `dispatcher_enhanced.py` | 2688.59 |
| ❌ | glob | def _symbol_route | `dispatcher_enhanced.py` | `27c37f37d6fb0172def7f568bdf47e2212f344` | 199.8 |
| ❌ | sed | def _symbol_route | `dispatcher_enhanced.py` | `coverage_html_cb_dd2e7eb5.js` | 40.7 |
| ❌ | ripgrep | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `matrix_benchmark.md` | 18.28 |
| ❌ | grep | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `matrix_benchmark.md` | 2936.54 |
| ❌ | glob | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` | 206.03 |
| ❌ | sed | where is the symbol routing logic implemented | `dispatcher_enhanced.py` | `debug_mcp_components.py` | 57.17 |
| ✅ | ripgrep | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 17.95 |
| ✅ | grep | class CrossEncoderReranker | `reranker.py` | `reranker.py` | 2243.68 |
| ❌ | glob | class CrossEncoderReranker | `reranker.py` | `class_index.html` | 183.66 |
| ❌ | sed | class CrossEncoderReranker | `reranker.py` | `coverage_html_cb_dd2e7eb5.js` | 35.45 |
