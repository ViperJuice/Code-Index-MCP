# E2E Retrieval Validation

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Indexed files: `1282`
- Iterations per query: `5`
- Top-1 pass rate: `33.3%`
- Top-3 pass rate: `64.4%`

## Retrieval Modes

| Mode | Category | Query | Top File | Top-1 | Top-3 | P50 (ms) | P95 (ms) |
|---|---|---|---|---:|---:|---:|---:|
| classic | semantic | semantic preflight | /home/viperjuice/code/Code-Index-MCP/docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen.json | 0.0% | 0.0% | 2.88 | 3.83 |
| bm25 | symbol_precise | qdrant docker compose autostart | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 46.45 | 51.8 |
| fuzzy | noisy | semntic preflite raport | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/semantic_preflight.py | 100.0% | 100.0% | 10.11 | 13.16 |
| semantic | general | where is qdrant autostart implemented | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 265.01 | 271.96 |
| hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | mcp_server/setup/semantic_preflight.py | 0.0% | 80.0% | 5093.14 | 9388.48 |
| bm25 | symbol_precise | class SemanticIndexer | /home/viperjuice/code/Code-Index-MCP/mcp_server/utils/__init__.py | 0.0% | 100.0% | 18.44 | 21.94 |
| semantic | semantic_intent | extract symbols from python using treesitter | /home/viperjuice/code/Code-Index-MCP/ai_docs/tree_sitter_overview.md | 0.0% | 0.0% | 265.27 | 275.95 |
| fuzzy | noisy | SemnticIndexer index_file | /home/viperjuice/code/Code-Index-MCP/architecture/path_management_architecture.md | 0.0% | 100.0% | 18.4 | 22.02 |
| hybrid | persistence | how do artifact push pull and delta resolution work | tests/test_artifact_lifecycle.py | 0.0% | 0.0% | 8381.4 | 8434.29 |

## Semantic Model Comparison

| Mode | Top File | Top-1 | Top-3 | P50 (ms) | P95 (ms) |
|---|---|---:|---:|---:|---:|
| semantic_qwen | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 238.5 | 1123.12 |
| semantic_voyage | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 116.68 | 134.45 |
| semantic_qwen_local | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 49.22 | 70.26 |
