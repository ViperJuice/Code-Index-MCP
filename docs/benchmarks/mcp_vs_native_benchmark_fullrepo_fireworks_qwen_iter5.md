# MCP vs Native Benchmark

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Iterations per query: `5`
- Native pass rate: `44.4%`
- MCP pass rate: `33.3%`

## Native Tools

| Backend | Query | Top Result | Top-1 | P50 (ms) | P95 (ms) |
|---|---|---|---:|---:|---:|
| ripgrep | semantic preflight | /home/viperjuice/code/Code-Index-MCP/scripts/run_mcp_vs_native_benchmark.py:15:    {"query": "semantic preflight", "expected": "semantic_preflight.py"}, | 100.0% | 20.76 | 106.59 |
| grep | semantic preflight | /home/viperjuice/code/Code-Index-MCP/htmlcov/z_0425c7814bfde65c_semantic_preflight_py.html:276:    <p class="pln"><span class="n"><a id="t192" href="#t192">192</a></span><span class="t">    <span class="str">"""Run semantic preflight checks and return structured report."""</span>&nbsp;</span><span class="r"></span></p> | 0.0% | 61211.4 | 63104.54 |
| glob | semantic preflight | /home/viperjuice/code/Code-Index-MCP/semantic_indexing_progress.json | 0.0% | 156.19 | 291.85 |
| ripgrep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen.json:28:        "query": "qdrant autostart", | 80.0% | 20.81 | 22.22 |
| grep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/docs/benchmarks/e2e_retrieval_validation_fullrepo.md:14:| semantic | where is qdrant autostart implemented | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | yes | 58.04 | | 100.0% | 61922.54 | 62448.61 |
| glob | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/qdrant_server_mode.patch | 0.0% | 145.52 | 154.57 |
| ripgrep | setup semantic | /home/viperjuice/code/Code-Index-MCP/README.md:687:python scripts/cli/mcp_cli.py setup semantic | 40.0% | 19.25 | 27.44 |
| grep | setup semantic | /home/viperjuice/code/Code-Index-MCP/code_index_mcp.egg-info/PKG-INFO:749:python scripts/cli/mcp_cli.py setup semantic | 0.0% | 62103.48 | 62400.32 |
| glob | setup semantic | /home/viperjuice/code/Code-Index-MCP/codex-setup.sh | 0.0% | 147.27 | 171.23 |
