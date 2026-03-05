# E2E Retrieval Validation

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Indexed files: `1280`
- Iterations per query: `5`
- Top-1 pass rate: `33.3%`
- Top-3 pass rate: `55.6%`

## Retrieval Modes

| Mode | Category | Query | Top File | Top-1 | Top-3 | P50 (ms) | P95 (ms) |
|---|---|---|---|---:|---:|---:|---:|
| classic | semantic | semantic preflight | /home/viperjuice/code/Code-Index-MCP/docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen.json | 0.0% | 0.0% | 3.16 | 5.58 |
| bm25 | symbol_precise | qdrant docker compose autostart | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 45.59 | 50.17 |
| fuzzy | noisy | semntic preflite raport | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/semantic_preflight.py | 100.0% | 100.0% | 9.95 | 120.31 |
| semantic | general | where is qdrant autostart implemented | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 250.29 | 428.49 |
| hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness |  | 0.0% | 0.0% | 5496.63 | 9783.35 |
| bm25 | symbol_precise | class SemanticIndexer | /home/viperjuice/code/Code-Index-MCP/mcp_server/utils/__init__.py | 0.0% | 100.0% | 20.59 | 63.74 |
| semantic | semantic_intent | extract symbols from python using treesitter | /home/viperjuice/code/Code-Index-MCP/ai_docs/tree_sitter_overview.md | 0.0% | 0.0% | 237.23 | 280.42 |
| fuzzy | noisy | SemnticIndexer index_file | /home/viperjuice/code/Code-Index-MCP/architecture/path_management_architecture.md | 0.0% | 100.0% | 15.29 | 192.86 |
| hybrid | persistence | how do artifact push pull and delta resolution work |  | 0.0% | 0.0% | 8811.24 | 8995.96 |

## Semantic Model Comparison

| Mode | Top File | Top-1 | Top-3 | P50 (ms) | P95 (ms) |
|---|---|---:|---:|---:|---:|
| semantic_qwen | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 260.51 | 603.57 |
| semantic_voyage | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 113.91 | 227.82 |
| semantic_qwen_local | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 52.35 | 94.0 |
