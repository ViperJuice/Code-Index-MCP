# Gateway Startup Checklist

- Confirm `JWT_SECRET_KEY` is present and valid before startup.
- Confirm `DEFAULT_ADMIN_PASSWORD` is present and not blocklisted before startup.
- Start the gateway and verify `/docs` renders publicly.
- Verify a protected route such as `/metrics` rejects unauthenticated requests.
- Use validated JWT test tokens for operator smoke checks; arbitrary bearer headers are not valid proof.
- Keep the public allowlist explicit and small.
- Preserve the separate STDIO `MCP_CLIENT_SECRET` handshake contract.

The gateway fail closed when required auth configuration is missing or invalid.
