# GitHub Token Scopes & Validation

> **Beta status**: This page targets `1.2.0-rc4`. Token validation supports
> artifact and attestation operations for the current beta release path.

## Overview

The token validator (SL-4) ensures that `GITHUB_TOKEN` includes the five required scopes for artifact operations, attestation signing, and metadata access. This document lists the scopes and describes the validation flow.

## Required Scopes

The `GITHUB_TOKEN` must include all five of the following scopes:

1. **`contents:read`** — Read repository contents (artifacts, code, releases).
2. **`metadata:read`** — Read repository metadata (used for permissions checks and schema info).
3. **`actions:read`** — Read GitHub Actions workflow results and artifacts.
4. **`actions:write`** — Trigger workflow runs and manage artifacts directly.
5. **`attestations:write`** — Sign artifacts with SLSA attestations (P15 SL-3).

## Validation Flow

The `TokenValidator.validate_scopes(required: set[str])` method is called at startup:

1. Reads the `GITHUB_TOKEN` environment variable.
2. Sends an HTTP `GET /user` request to GitHub API with the token in the `Authorization` header.
3. Parses the response header `X-OAuth-Scopes` (comma-separated list of granted scopes).
4. Checks that all required scopes are present.
5. On mismatch, either raises `TokenScopeError` or logs a warning, depending on `MCP_REQUIRE_TOKEN_SCOPES`.

## Configuration

### Soft-fail mode (default):

If `GITHUB_TOKEN` is unset or scopes are missing, a `WARN` level log is emitted. Development and testing can proceed without the token, but artifact operations will fail at runtime.

Set `MCP_REQUIRE_TOKEN_SCOPES=1` to enforce strict validation (hard-fail on unset or missing scopes).

### Hard-fail mode:

If `MCP_REQUIRE_TOKEN_SCOPES=1` is set, the validator raises `TokenScopeError` at startup if the token is unset or any required scope is missing. Deployment will not start.

## Token Management

**Creating a new token**:
1. Go to GitHub → Settings → Developer settings → Personal access tokens (classic).
2. Click "Generate new token".
3. Grant scopes: `contents:read`, `metadata:read`, `actions:read`, `actions:write`, `attestations:write`.
4. Copy the token and store in a secure location (1Password, GitHub OIDC, etc.).

**Rotating the token**:
1. Generate a new token with the same scopes.
2. Update `GITHUB_TOKEN` in your deployment environment.
3. Optionally revoke the old token from GitHub settings.

**Token rotation cadence**:
- Recommended: every 90 days.
- Enforcement: use a credential manager (1Password, Vault, GitHub OIDC → short-lived tokens).

## Checking Token Scopes

To verify a token's scopes without deploying:

```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/user \
     | grep -o 'X-OAuth-Scopes: [^,]*'
```

Or use the `gh` CLI:

```bash
gh auth status
```

## Backward Compatibility

Tokens created before P15 may lack the `attestations:write` scope. Rotate these tokens before upgrading to P15 to avoid deployment failures.
