# P12–P18 → v1.2.0-rc1 Operator Upgrade Guide

This document is the authoritative migration guide for operators upgrading
`Code-Index-MCP` from any release between P12 and P18 to **v1.2.0-rc1**.

---

## Who this is for

Any operator running a self-hosted `Code-Index-MCP` instance on a release older than
`v1.2.0-rc1` who wants to upgrade in a single step.  If you are already running the
v1.2.0 release candidate you do not need this guide.

---

## What broke

### 1. Plugin sandbox defaults are now ON

**Change**: The plugin sandbox is now enabled by default (`MCP_PLUGIN_SANDBOX_DISABLE`
was previously un-set, meaning sandboxing was opt-in; it is now opt-out).

**Impact**: Plugins that spawn sub-processes or access the filesystem outside their
declared scope will fail at runtime.

**Mitigation**: Audit your plugins before upgrading.  Set
`MCP_PLUGIN_SANDBOX_DISABLE=1` to revert to the pre-P18 behaviour while you complete
the audit; remove it when plugins have been updated.

### 2. Startup now aborts on fatal validation errors (production environment)

**Change**: `validate_production_config` is called during gateway startup.  If the
current environment is `production` (i.e. `MCP_ENVIRONMENT=production`) and any fatal
validation error is found, startup aborts rather than continuing with an insecure
configuration.

**Impact**: An instance that was silently misconfigured will no longer start.

**Mitigation**: Run the pre-flight check (see below) before deploying.

### 3. New required environment variables

The following env vars are required in production and were not enforced in earlier
phases.  Missing or weak values now cause a fatal error and abort startup.

| Variable | Requirement | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | ≥ 32 characters; not a blocklist value | Generate: `openssl rand -hex 32` |
| `DEFAULT_ADMIN_PASSWORD` | Non-empty; not a blocklist value | Any reasonably strong password |
| `MCP_ENVIRONMENT` | Set to `production` for prod deployments | Controls severity of validation errors |
| `MCP_LOG_FORMAT` | `json` (recommended for production log aggregation) | Optional but strongly advised |
| `CORS_ORIGINS` | Comma-separated explicit origin list; never `*` | Example: `https://app.example.com` |

### 4. CORS wildcard refused at startup

**Change**: `CORS_ORIGINS=*` is now refused.  Gateway startup logs a warning and strips
the wildcard; in a future release this will become fatal.

**Mitigation**: Replace with an explicit allowlist.

### 5. `gh` attestation probed at boot (warning only)

**Change**: The gateway probes for `gh attestation verify` support at boot.  If `gh` is
not installed or does not support attestation subcommands a warning is emitted; startup
is not blocked.

**Impact**: None in most deployments.  Silence the warning by installing GitHub CLI ≥
2.49.

---

## Pre-flight procedure

Run this check **before** upgrading any production instance.  It validates your env file
against the same rules the gateway applies at startup.

```bash
# From the repository root (or wherever the release is extracted):
bash scripts/preflight_upgrade.sh /path/to/your/production.env
echo "exit: $?"
```

Exit code `0` means no fatal errors were found.  Exit code `1` means at least one fatal
error was found; fix all `[FATAL]` lines before proceeding.

`[WARN]` lines are non-blocking but should be reviewed before the next major release.

### Minimal passing env file

```env
JWT_SECRET_KEY=<at-least-32-hex-chars>
DEFAULT_ADMIN_PASSWORD=<strong-password>
MCP_ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend.example.com
RATE_LIMIT_REQUESTS=100
```

---

## No-downtime upgrade steps

1. **Take a snapshot** of the current `repository_registry.json` and index files.
2. **Run the pre-flight check** against your production env file.  Resolve all `[FATAL]`
   errors before continuing.
3. **Update environment variables** listed in "New required environment variables" above.
4. **Set `MCP_PLUGIN_SANDBOX_DISABLE=1`** if any of your plugins have not yet been
   audited for sandbox compatibility.
5. **Deploy the new image** (or pull and restart the process).  Startup logs will show
   the validation result.
6. **Confirm healthy startup** by checking the `/health` endpoint and reviewing logs for
   `[FATAL]` or `[WARN]` prefixes.
7. **Remove `MCP_PLUGIN_SANDBOX_DISABLE=1`** after completing the plugin audit.

---

## Rollback procedure

If the new version fails to start or exhibits unexpected behaviour:

1. **Restore the previous image/binary** without changing env files.
2. **Restore `repository_registry.json`** from the snapshot taken in step 1 above if
   it was modified during the upgrade.
3. **Re-enable `MCP_PLUGIN_SANDBOX_DISABLE=1`** if you had set it before rollback is
   not needed.
4. **Restart** and confirm `/health` responds successfully.

The index files are forward-compatible; a rollback does not require re-indexing.

---

## Appendix: full env var delta

The table below lists every environment variable that changed semantics between P12 and
v1.2.0-rc1.

| Variable | P12–P17 default | v1.2.0-rc1 default | Notes |
|---|---|---|---|
| `MCP_ENVIRONMENT` | unset (treated as `development`) | no new default; must be set explicitly in production | Governs validation severity |
| `MCP_LOG_FORMAT` | unset | unset | `json` strongly advised for prod |
| `JWT_SECRET_KEY` | silently accepted if weak | **fatal** if blocklisted value (in production) | Use `openssl rand -hex 32` |
| `DEFAULT_ADMIN_PASSWORD` | silently accepted if unset | **fatal** if unset or blocklisted (in production) | |
| `CORS_ORIGINS` | `*` (wildcard allowed) | wildcard refused; explicit list required | |
| `RATE_LIMIT_REQUESTS` | silently accepted any value | **fatal** if > 1000 in production | |
| `MCP_PLUGIN_SANDBOX_DISABLE` | unset = sandbox off | unset = sandbox **on**; set `=1` to opt out | Breaking change — see above |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | `30` | No change |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | `7` | No change |
