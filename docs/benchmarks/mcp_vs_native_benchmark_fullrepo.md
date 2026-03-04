# MCP vs Native Benchmark

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Native pass rate: `44.4%`
- MCP pass rate: `60.0%`

## Native Tools

| Backend | Query | Top Result | Pass | Latency (ms) |
|---|---|---|---:|---:|
| ripgrep | semantic preflight | /home/viperjuice/code/Code-Index-MCP/scripts/run_e2e_retrieval_validation.py:36:    QueryCase("classic", "semantic preflight", "semantic_preflight.py"), | yes | 33.46 |
| grep | semantic preflight | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/semantic_preflight.py:192:    """Run semantic preflight checks and return structured report.""" | yes | 36872.06 |
| glob | semantic preflight | /home/viperjuice/code/Code-Index-MCP/semantic_indexing_progress.json | no | 0.0 |
| ripgrep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/scripts/run_e2e_retrieval_validation.py:40:        "semantic", "where is qdrant autostart implemented", "qdrant_autostart.py" | yes | 18.37 |
| grep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/docs/benchmarks/mcp_vs_native_benchmark_fullrepo.md:14:| ripgrep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/scripts/run_mcp_vs_native_benchmark.py:16:    {"query": "qdrant autostart", "expected": "qdrant_autostart.py"}, | yes | 64.48 | | yes | 35780.13 |
| glob | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/qdrant_server_mode.patch | no | 0.0 |
| ripgrep | setup semantic | /home/viperjuice/code/Code-Index-MCP/README.md:687:python scripts/cli/mcp_cli.py setup semantic | no | 23.31 |
| grep | setup semantic | /home/viperjuice/code/Code-Index-MCP/code_index_mcp.egg-info/PKG-INFO:749:python scripts/cli/mcp_cli.py setup semantic | no | 33660.41 |
| glob | setup semantic | /home/viperjuice/code/Code-Index-MCP/codex-setup.sh | no | 0.0 |
