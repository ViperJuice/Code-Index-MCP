# E2E Retrieval Validation

- Repo: `/home/viperjuice/code/Code-Index-MCP`
- Indexed files: `1262`
- Pass rate: `60.0%`

## Retrieval Modes

| Mode | Query | Top File | Pass | Latency (ms) |
|---|---|---|---:|---:|
| classic | semantic preflight |  | no | 8.62 |
| bm25 | qdrant docker compose autostart | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | yes | 37.5 |
| fuzzy | semntic preflite raport | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/semantic_preflight.py | yes | 11.58 |
| semantic | where is qdrant autostart implemented | /home/viperjuice/code/Code-Index-MCP/mcp_server/setup/qdrant_autostart.py | yes | 243.63 |
| hybrid | how does semantic setup validate qdrant and embedding readiness |  | no | 5102.41 |
