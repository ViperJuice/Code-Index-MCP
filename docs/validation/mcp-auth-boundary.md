# MCP Auth Boundary Validation

AUTHBOUND hardens the FastAPI admin/debug JWT boundary only. Protected HTTP routes accept validated JWT bearer tokens, arbitrary bearer headers are rejected, and the gateway fail closed when signing or bootstrap auth configuration is invalid.

The public allowlist remains `/docs`, `/redoc`, `/openapi.json`, `/health`, `/ready`, and `/liveness`.

The STDIO `MCP_CLIENT_SECRET` handshake remains a separate contract and is unchanged by AUTHBOUND.
It is a local STDIO handshake guard. FastAPI continues to use admin/debug bearer token authentication, and no remote MCP authorization is implemented.
