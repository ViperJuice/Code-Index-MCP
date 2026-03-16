# MCP vs Native Benchmark

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Iterations per query: `1`
- Native pass rate: `33.3%`
- MCP pass rate: `n/a%`

## Native Tools

| Backend | Query | Top Result | Top-1 | P50 (ms) | P95 (ms) |
|---|---|---|---:|---:|---:|
| ripgrep | semantic preflight | /home/viperjuice/code/Code-Index-MCP/scripts/run_e2e_retrieval_validation.py:78:    QueryCase("classic", "semantic preflight", "semantic_preflight.py", "semantic"), | 100.0% | 56.9 | 56.9 |
| grep | semantic preflight | /home/viperjuice/code/Code-Index-MCP/htmlcov/z_0425c7814bfde65c_semantic_preflight_py.html:276:    <p class="pln"><span class="n"><a id="t192" href="#t192">192</a></span><span class="t">    <span class="str">"""Run semantic preflight checks and return structured report."""</span>&nbsp;</span><span class="r"></span></p> | 0.0% | 14133.68 | 14133.68 |
| glob | semantic preflight | /home/viperjuice/code/Code-Index-MCP/semantic_indexing_progress.json | 0.0% | 78.66 | 78.66 |
| ripgrep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/scripts/run_e2e_retrieval_validation.py:87:        "semantic", "where is qdrant autostart implemented", "qdrant_autostart.py" | 100.0% | 31.86 | 31.86 |
| grep | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/docs/benchmarks/e2e_retrieval_validation_fullrepo.md:14:| semantic | where is qdrant autostart implemented | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | yes | 58.04 | | 100.0% | 10990.7 | 10990.7 |
| glob | qdrant autostart | /home/viperjuice/code/Code-Index-MCP/qdrant_server_mode.patch | 0.0% | 76.09 | 76.09 |
| ripgrep | setup semantic | /home/viperjuice/code/Code-Index-MCP/README.md:772:mcp-index setup semantic | 0.0% | 19.78 | 19.78 |
| grep | setup semantic | /home/viperjuice/code/Code-Index-MCP/code_index_mcp.egg-info/PKG-INFO:766:python scripts/cli/mcp_cli.py setup semantic | 0.0% | 10598.09 | 10598.09 |
| glob | setup semantic | /home/viperjuice/code/Code-Index-MCP/codex-setup.sh | 0.0% | 81.86 | 81.86 |
