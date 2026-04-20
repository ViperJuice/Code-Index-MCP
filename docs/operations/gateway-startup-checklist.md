# Gateway Startup Checklist

This document provides an operator deployment checklist for Code-Index-MCP gateway startup, with exit validation modes and pre-flight verification steps.

## Pre-Deployment Validation

### Environment Setup

- [ ] All required secrets are populated:
  - `JWT_SECRET_KEY` — Generated with `openssl rand -hex 32` (minimum 32 hex characters / 16 bytes)
  - `DEFAULT_ADMIN_PASSWORD` — Set to a strong, unique value
  - `GITHUB_TOKEN` — Valid with required scopes: `repo`, `read:attestations`, `attestations:write`, `workflow`
  - `VOYAGEAI_API_KEY` — Valid Voyage AI API key for semantic search

- [ ] Environment variables are correctly set:
  ```bash
  export MCP_ENVIRONMENT=production
  export MCP_SERVER_HOST=0.0.0.0
  export MCP_SERVER_PORT=8080
  export MCP_ATTESTATION_MODE=enforce  # or warn/off as appropriate
  export MCP_LOG_FORMAT=json
  # ... other vars as needed
  ```

### Security Validation

- [ ] **CORS**: Verify `CORS_ORIGINS` is NOT `*` in production. Must be a whitelist of specific domains.
  - Fatal in production if set to `*`
  - Logs WARN in dev/test

- [ ] **Rate Limiting**: Verify `rate_limit_requests` is reasonable (≤1000 requests/min for production).
  - Fatal in production if > 1000 or disabled (0)
  - Logs WARN in dev/test

- [ ] **GitHub Token Scopes**: Verify `GITHUB_TOKEN` has all required scopes:
  - `repo` — for artifact repository access
  - `read:attestations` — for attestation verification
  - `attestations:write` — for attestation signing
  - `workflow` — for CI artifact download
  - Missing scopes are logged at startup; fatal if `MCP_ATTESTATION_MODE=enforce`

- [ ] **Plugin Sandbox**: Plugin sandbox is ON by default (as of P18). To opt out:
  ```bash
  export MCP_PLUGIN_SANDBOX_DISABLE=1  # Only if necessary
  ```

### Network & Connectivity

- [ ] Port is available and not already bound:
  ```bash
  netstat -ln | grep :$MCP_SERVER_PORT
  # Should return no results
  ```

- [ ] GitHub API connectivity (rate-limit check):
  ```bash
  curl -H "Authorization: Bearer $GITHUB_TOKEN" \
    https://api.github.com/rate_limit | jq .
  # Verify `remaining` is > 0 and `limit` is at least 5000
  ```

- [ ] Voyage AI API connectivity:
  ```bash
  curl -H "Authorization: Bearer $VOYAGEAI_API_KEY" \
    https://api.voyageai.com/v1/rerank \
    -d '{"query":"test","documents":["test"]}' 2>/dev/null | jq .
  # Verify response is valid (no 401 or 403)
  ```

## Startup Sequence

### Step 1: Boot the Gateway

```bash
MCP_ENVIRONMENT=production \
MCP_LOG_FORMAT=json \
python -m mcp_server.cli.server_commands
```

### Step 2: Monitor Startup Output

Watch for:

- ✅ **Expected**: `[INFO] Startup validation passed` (or no validation block if dev/test)
- ✅ **Expected**: `[INFO] MCP Gateway initialized, listening on 0.0.0.0:8080`
- ✅ **Expected in enforce mode**: Single `ATTESTATION_PREREQ` WARN if `gh attestation` subcommand unavailable (non-fatal)

- ❌ **Fatal (production)**:
  ```
  [FATAL] <code>: <message>
  ```
  Example:
  ```
  [FATAL] JWT_SECRET_KEY: Weak JWT secret (length 16 < minimum 32 hex chars)
  [FATAL] CORS_ORIGINS: Wildcard CORS in production forbidden
  [FATAL] RATE_LIMIT: Rate limit disabled or > 1000 req/min
  ```

- ❌ **Fallback to dev mode if fatal errors appear in production**: Check `MCP_ENVIRONMENT` and re-generate secrets.

### Step 3: Validate Health Endpoints

Once the gateway is running:

```bash
# Health check (no auth required)
curl -f http://localhost:8080/health

# Readiness probe (no auth required)
curl -f http://localhost:8080/ready

# Liveness probe (no auth required)
curl -f http://localhost:8080/liveness

# Metrics endpoint (auth required; Bearer token needed)
curl -H "Authorization: Bearer <VALID_JWT_TOKEN>" \
  http://localhost:8080/metrics | head -20
```

All three should return 200 OK.

### Step 4: Verify JSON Logging (if MCP_LOG_FORMAT=json)

Sample a log line and verify it parses as JSON:

```bash
# Tail recent logs and parse the first JSON line
tail -f /var/log/mcp-server.log | head -1 | jq .
# Should output: {"timestamp":"...","level":"INFO","name":"...","message":"..."}
```

### Step 5: Test a Basic Tool Call

```bash
# Register a test repository (adjust path as needed)
curl -X POST http://localhost:8080/repos \
  -H "Authorization: Bearer <VALID_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/test/repo"}'

# Run a symbol lookup
curl -X POST http://localhost:8080/search/symbol \
  -H "Authorization: Bearer <VALID_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "foo", "repository_id": "test"}'

# Verify response contains no plaintext secrets in error messages
```

## Exit Modes

### ✅ Success: All Checks Pass

- Exit code: `0`
- Gateway is accepting tool calls
- All health endpoints return 200
- JSON logs (if enabled) parse without errors

### ❌ Fatal: Production + Weak Credentials

- Exit code: `1`
- Error message lists all violations:
  ```
  [FATAL] JWT_SECRET_KEY: Weak JWT secret (length 16 < minimum 32 hex chars)
  [FATAL] DEFAULT_ADMIN_PASSWORD: Weak password or not set
  [FATAL] CORS_ORIGINS: Wildcard CORS in production forbidden
  ```

**Resolution**: Set the missing or weak variables and restart.

### ⚠️ Degraded: Production + Missing Attestation Support

- Exit code: `0` (non-fatal)
- Single WARN line in logs:
  ```
  [WARN] ATTESTATION_PREREQ: gh attestation subcommand unavailable; artifact signing disabled
  ```

**Resolution**: Install `gh` CLI and ensure `gh attestation` subcommand is available. Attestation will remain skipped until remedied.

## Troubleshooting

### Port Already in Use

```bash
# Find process using the port
lsof -i :$MCP_SERVER_PORT

# Kill the process or choose a different port
kill -9 <PID>
export MCP_SERVER_PORT=8081
```

### JWT Secret Validation Fails

```bash
# Check current JWT_SECRET_KEY length
echo -n "$JWT_SECRET_KEY" | wc -c

# Must be at least 32 hex characters (16 bytes)
# Regenerate if needed
export JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### CORS Wildcard Error in Production

```bash
# Check current CORS setting
echo "$CORS_ORIGINS"

# Must be specific domains, not "*"
export CORS_ORIGINS="https://example.com,https://example.org"
```

### Rate Limit Too Permissive

```bash
# Check current rate limit
echo "$rate_limit_requests"

# Must be <= 1000 req/min in production
# Set to a reasonable value (e.g., 500)
export rate_limit_requests=500
```

### GitHub Token Missing Scopes

```bash
# Check token scopes
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/user | jq .

# Regenerate token with required scopes: repo, read:attestations, attestations:write, workflow
```

### Attestation Subcommand Missing

```bash
# Check if gh CLI is installed
which gh

# Verify gh attestation subcommand exists
gh attestation --help

# If missing, update gh CLI
brew upgrade gh  # macOS
apt-get install -y gh  # Debian/Ubuntu
```

## Post-Deployment Validation

After successful startup:

1. **Logs Validation**: Confirm no `[FATAL]` entries in the first minute of logs
2. **Metrics Collection**: Query `/metrics` and verify counters are incrementing
3. **Artifact Attestation**: If enabled, trigger a tool call that publishes an artifact and verify attestation succeeds
4. **Rate Limiting**: Trigger > 1000 requests/min and verify 429 responses with `Retry-After` header

## Production Rollback Procedure

If the gateway fails startup or becomes unavailable:

1. Stop the failing gateway: `kill -9 <PID>`
2. Revert to the previous known-good version/configuration
3. Restart with the previous environment variables
4. Verify health endpoints return 200
5. Monitor logs for any recurrence of the issue
6. File an incident and investigate root cause offline

## See Also

- `docs/configuration/environment-variables.md` — full env var reference
- `docs/security/sandbox.md` — plugin sandboxing migration guide
- `docs/operations/artifact-retention.md` — retention janitor operator guide
