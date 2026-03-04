# E2E Retrieval Validation

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Indexed files: `1260`
- Pass rate: `60.0%`

## Retrieval Modes

| Mode | Query | Top File | Pass | Latency (ms) |
|---|---|---|---:|---:|
| classic | semantic preflight |  | no | 9.51 |
| bm25 | qdrant docker compose autostart | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | yes | 40.58 |
| fuzzy | semntic preflite raport | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/semantic_preflight.py | yes | 11.62 |
| semantic | where is qdrant autostart implemented | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | yes | 58.04 |
| hybrid | how does semantic setup validate qdrant and embedding readiness |  | no | 5169.1 |

## Semantic Model Comparison

| Mode | Top File | Pass | Latency (ms) |
|---|---|---:|---:|
| semantic_qwen | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | yes | 51.72 |
| semantic_voyage | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | yes | 323.31 |
