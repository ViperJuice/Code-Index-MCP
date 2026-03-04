# MCP vs Native Benchmark

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Native pass rate: `44.4%`
- MCP pass rate: `60.0%`

## Native Tools

| Backend | Query | Top Result | Pass | Latency (ms) |
|---|---|---|---:|---:|
| ripgrep | semantic preflight | /home/viperjuice/code/Code-Index-MCP/scripts/run_mcp_vs_native_benchmark.py:15:    {"query": "semantic preflight", "expected": "semantic_preflight.py"}, | yes | 30.86 |
| grep | semantic preflight | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/semantic_preflight.py:192:    """Run semantic preflight checks and return structured report.""" | yes | 33086.75 |
| glob | semantic preflight | /home/viperjuice/code/Code-Index-MCP/semantic_indexing_progress.json | no | 0.0 |
| ripgrep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/scripts/run_e2e_retrieval_validation.py:40:        "semantic", "where is qdrant autostart implemented", "qdrant_autostart.py" | yes | 18.01 |
| grep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/docs/benchmarks/e2e_retrieval_validation_fullrepo.md:14:| semantic | where is qdrant autostart implemented | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | yes | 58.04 | | yes | 33711.73 |
| glob | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/qdrant_server_mode.patch | no | 0.0 |
| ripgrep | setup semantic | /home/viperjuice/code/Code-Index-MCP/README.md:687:python scripts/cli/mcp_cli.py setup semantic | no | 21.01 |
| grep | setup semantic | /home/viperjuice/code/Code-Index-MCP/code_index_mcp.egg-info/PKG-INFO:749:python scripts/cli/mcp_cli.py setup semantic | no | 33134.88 |
| glob | setup semantic | /home/viperjuice/code/Code-Index-MCP/codex-setup.sh | no | 0.0 |
