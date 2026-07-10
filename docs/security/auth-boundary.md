# AUTHBOUND FastAPI Auth Boundary

FastAPI protected routes accept only validated JWT bearer tokens. Arbitrary bearer headers are rejected, and no dependency or middleware creates `fallback-user`, grants `admin`, or grants every permission from header presence alone.

The public allowlist is explicit: `/docs`, `/redoc`, `/openapi.json`, `/health`, `/ready`, and `/liveness`. All other FastAPI admin/debug routes require validated JWT authentication and then enforce role or permission checks.

Startup and request handling fail closed. Missing or invalid JWT signing configuration, missing default admin password, or weak blocklisted admin password do not enable a permissive mode. When auth state is unavailable, protected routes stay unavailable instead of trusting headers.

This phase does not change the STDIO `MCP_CLIENT_SECRET` handshake. The HTTP admin/debug boundary and the STDIO handshake remain separate contracts.
