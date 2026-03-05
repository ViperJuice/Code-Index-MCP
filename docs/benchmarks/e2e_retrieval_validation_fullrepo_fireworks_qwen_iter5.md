# E2E Retrieval Validation

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Indexed files: `1272`
- Iterations per query: `5`
- Top-1 pass rate: `33.3%`
- Top-3 pass rate: `57.8%`

## Retrieval Modes

| Mode | Category | Query | Top File | Top-1 | Top-3 | P50 (ms) | P95 (ms) |
|---|---|---|---|---:|---:|---:|---:|
| classic | semantic | semantic preflight | /home/viperjuice/code/Code-Index-MCP/docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen.json | 0.0% | 0.0% | 3.33 | 3.88 |
| bm25 | symbol_precise | qdrant docker compose autostart | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 37.61 | 42.07 |
| fuzzy | noisy | semntic preflite raport | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/semantic_preflight.py | 100.0% | 100.0% | 10.22 | 24.76 |
| semantic | general | where is qdrant autostart implemented | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | 100.0% | 100.0% | 256.12 | 349.02 |
| hybrid | semantic_intent | how does semantic setup validate qdrant and embedding readiness | mcp_server/setup/semantic_preflight.py | 0.0% | 20.0% | 5157.88 | 5464.51 |
| bm25 | symbol_precise | class SemanticIndexer | /home/viperjuice/code/Code-Index-MCP/mcp_server/utils/__init__.py | 0.0% | 100.0% | 19.82 | 23.39 |
| semantic | semantic_intent | extract symbols from python using treesitter | /home/viperjuice/code/Code-Index-MCP/ai_docs/tree_sitter_overview.md | 0.0% | 0.0% | 195.56 | 394.18 |
| fuzzy | noisy | SemnticIndexer index_file | /home/viperjuice/code/Code-Index-MCP/architecture/path_management_architecture.md | 0.0% | 100.0% | 15.88 | 16.41 |
| hybrid | persistence | how do artifact push pull and delta resolution work |  | 0.0% | 0.0% | 8445.79 | 10160.61 |
