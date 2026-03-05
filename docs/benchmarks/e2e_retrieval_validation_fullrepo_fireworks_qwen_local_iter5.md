# E2E Retrieval Validation

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Indexed files: `1276`
- Iterations per query: `5`
- Top-1 pass rate: `33.3%`
- Top-3 pass rate: `55.6%`

## Retrieval Modes

| Mode | Category | Query | Top File | Top-1 | Top-3 | P50 (ms) | P95 (ms) |
|---|---|---|---|---:|---:|---:|---:|
| classic | semantic | semantic preflight | /home/viperjuice/code/Code-Index-MCP/docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen.json | 0.0% | 0.0% | 2.73 | 3.37 |
| bm25 | symbol_precise | qdrant docker compose autostart | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 38.62 | 45.23 |
| fuzzy | noisy | semntic preflite raport | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/semantic_preflight.py | 100.0% | 100.0% | 8.64 | 35.4 |
| semantic | general | where is qdrant autostart implemented | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 171.34 | 330.85 |
| hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness |  | 0.0% | 0.0% | 5051.61 | 5105.47 |
| bm25 | symbol_precise | class SemanticIndexer | /home/viperjuice/code/Code-Index-MCP/mcp_server/utils/__init__.py | 0.0% | 100.0% | 22.81 | 23.9 |
| semantic | semantic_intent | extract symbols from python using treesitter | /home/viperjuice/code/Code-Index-MCP/ai_docs/tree_sitter_overview.md | 0.0% | 0.0% | 258.65 | 383.15 |
| fuzzy | noisy | SemnticIndexer index_file | /home/viperjuice/code/Code-Index-MCP/architecture/path_management_architecture.md | 0.0% | 100.0% | 17.92 | 20.07 |
| hybrid | persistence | how do artifact push pull and delta resolution work |  | 0.0% | 0.0% | 8245.92 | 8390.6 |

## Semantic Model Comparison

| Mode | Top File | Top-1 | Top-3 | P50 (ms) | P95 (ms) |
|---|---|---:|---:|---:|---:|
| semantic_qwen_local | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 48.02 | 97.24 |
