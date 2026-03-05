# MCP vs Native Benchmark

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Iterations per query: `5`
- Native pass rate: `44.4%`
- MCP pass rate: `33.3%`

## Native Tools

| Backend | Query | Top Result | Top-1 | P50 (ms) | P95 (ms) |
|---|---|---|---:|---:|---:|
| ripgrep | semantic preflight | /home/viperjuice/code/Code-Index-MCP/scripts/run_mcp_vs_native_benchmark.py:16:    {"query": "semantic preflight", "expected": "semantic_preflight.py"}, | 80.0% | 54.37 | 87.32 |
| grep | semantic preflight | /home/viperjuice/code/Code-Index-MCP/htmlcov/z_0425c7814bfde65c_semantic_preflight_py.html:276:    <p class="pln"><span class="n"><a id="t192" href="#t192">192</a></span><span class="t">    <span class="str">"""Run semantic preflight checks and return structured report."""</span>&nbsp;</span><span class="r"></span></p> | 0.0% | 61564.57 | 63305.98 |
| glob | semantic preflight | /home/viperjuice/code/Code-Index-MCP/semantic_indexing_progress.json | 0.0% | 148.17 | 238.84 |
| ripgrep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/scripts/run_e2e_retrieval_validation.py:62:        "semantic", "where is qdrant autostart implemented", "qdrant_autostart.py" | 80.0% | 18.59 | 20.38 |
| grep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/docs/benchmarks/e2e_retrieval_validation_fullrepo.md:14:| semantic | where is qdrant autostart implemented | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | yes | 58.04 | | 100.0% | 62760.43 | 63142.15 |
| glob | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/qdrant_server_mode.patch | 0.0% | 141.8 | 154.98 |
| ripgrep | setup semantic | /home/viperjuice/code/Code-Index-MCP/README.md:687:python scripts/cli/mcp_cli.py setup semantic | 20.0% | 19.24 | 20.56 |
| grep | setup semantic | /home/viperjuice/code/Code-Index-MCP/code_index_mcp.egg-info/PKG-INFO:749:python scripts/cli/mcp_cli.py setup semantic | 0.0% | 62316.2 | 62535.46 |
| glob | setup semantic | /home/viperjuice/code/Code-Index-MCP/codex-setup.sh | 0.0% | 139.12 | 150.4 |
