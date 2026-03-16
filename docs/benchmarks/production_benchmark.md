# Production Retrieval Benchmark

- Run: `2026-03-16T05:02:21.439111+00:00`
- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Index: `/home/viperjuice/code/Code-Index-MCP/code_index.db`
- Qdrant: `/home/viperjuice/code/Code-Index-MCP/vector_index.qdrant`
- Qdrant points: `12546`
- Iterations per query: `1`

## MCP Dispatcher Results

**Top-1 pass rate: 7/9 (77.8%)**  Top-3: 9/9 (100.0%)

| Pass | Mode | Category | Query | Expected | Top File | P50 (ms) | P95 (ms) |
|:---:|---|---|---|---|---|---:|---:|
| 🔶 | classic | semantic | semantic preflight | `semantic_preflight.py` | `setup_commands.py` | 346.45 | 346.45 |
| ✅ | bm25 | symbol_precise | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_autostart.py` | 55.96 | 55.96 |
| ✅ | fuzzy | noisy | semntic preflite raport | `semantic_preflight.py` | `semantic_preflight.py` | 66.0 | 66.0 |
| ✅ | semantic | general | where is qdrant autostart implemented | `qdrant_autostart.py` | `qdrant_autostart.py` | 288.08 | 288.08 |
| ✅ | hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | `setup_commands.py` | `setup_commands.py` | 525.14 | 525.14 |
| 🔶 | bm25 | symbol_precise | class SemanticIndexer | `semantic_indexer.py` | `__init__.py` | 433.82 | 433.82 |
| ✅ | semantic | semantic_intent | extract symbols from python using treesitter | `semantic_indexer.py` | `semantic_indexer.py` | 739.04 | 739.04 |
| ✅ | fuzzy | noisy | SemnticIndexer index_file | `semantic_indexer.py` | `semantic_indexer.py` | 127.31 | 127.31 |
| ✅ | hybrid | persistence | how do artifact push pull and delta resolution work | `delta_resolver.py` | `delta_resolver.py` | 303.83 | 303.83 |

## Native Tool Comparison

**Pass rate: 0/15**

| Pass | Backend | Query | Expected | Top File | Latency (ms) |
|:---:|---|---|---|---|---:|
| ❌ | ripgrep | semantic preflight | `semantic_preflight.py` | `e2e_retrieval_validation_fullrepo.md` | 18.24 |
| ❌ | grep | semantic preflight | `semantic_preflight.py` | `z_0425c7814bfde65c_semantic_preflight_py.html` | 2441.08 |
| ❌ | glob | semantic preflight | `semantic_preflight.py` | `semantic_indexing_progress.json` | 185.27 |
| ❌ | ripgrep | qdrant docker compose autostart | `qdrant_autostart.py` | `run_e2e_retrieval_validation.py` | 22.35 |
| ❌ | grep | qdrant docker compose autostart | `qdrant_autostart.py` | `e2e_retrieval_validation_fullrepo.md` | 2419.43 |
| ❌ | glob | qdrant docker compose autostart | `qdrant_autostart.py` | `qdrant_server_mode.patch` | 230.7 |
| ❌ | ripgrep | semntic preflite raport | `semantic_preflight.py` | `run_e2e_retrieval_validation.py` | 21.91 |
| ❌ | grep | semntic preflite raport | `semantic_preflight.py` | `e2e_retrieval_validation_fullrepo.md` | 2522.44 |
| ❌ | glob | semntic preflite raport | `semantic_preflight.py` | `` | 209.67 |
| ❌ | ripgrep | class SemanticIndexer | `semantic_indexer.py` | `run_e2e_retrieval_validation.py` | 17.74 |
| ❌ | grep | class SemanticIndexer | `semantic_indexer.py` | `qdrant_server_mode.patch` | 2220.17 |
| ❌ | glob | class SemanticIndexer | `semantic_indexer.py` | `class_index.html` | 177.79 |
| ❌ | ripgrep | SemnticIndexer index_file | `semantic_indexer.py` | `run_e2e_retrieval_validation.py` | 20.19 |
| ❌ | grep | SemnticIndexer index_file | `semantic_indexer.py` | `e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` | 2514.84 |
| ❌ | glob | SemnticIndexer index_file | `semantic_indexer.py` | `` | 195.63 |
