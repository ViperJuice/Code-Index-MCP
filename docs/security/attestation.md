# Artifact Attestation & Signing

> **Beta status**: This page targets `1.2.0-rc4`. Attestation policy is part
> of the current security posture for the `ghcr.io/viperjuice/code-index-mcp`
> release path, with operational limits documented in the deployment runbook.

## Overview

Artifact attestation (SL-3) uses GitHub's native SLSA attestation mechanism to sign index artifacts at publish time and verify them at download time. This document describes the flow, configuration, and error handling.

## Signing Flow

**At publish time** (P13 SL-4 + P15 SL-3):

1. Artifact is created (`.tar.gz` or `.json` file).
2. `gh attestation sign <artifact>` is invoked (requires `GITHUB_TOKEN` with `attestations:write` scope).
3. GitHub Actions signs the artifact with the repo's SLSA provenance.
4. A sidecar file `<artifact>.attestation.jsonl` is created in the same location.
5. Both files are published to GitHub Releases.

**At download time** (P15 SL-3):

1. Client downloads both `<artifact>` and `<artifact>.attestation.jsonl`.
2. `gh attestation verify <artifact>` checks the signature against GitHub's certificate.
3. Verification either succeeds (attestation is valid) or fails (signature doesn't match or is missing).

## Configuration

Set the attestation mode via the `MCP_ATTESTATION_MODE` environment variable:

- **`enforce`** (default, production): Raises `AttestationVerificationError` on sign or verify failure. Deployment will not start without valid attestations.
- **`warn`**: Logs a warning on sign or verify failure but continues. Allows graceful degradation.
- **`skip`**: No-op; attestations are not checked. Useful for air-gapped environments without GitHub connectivity.

## Token Requirements

`GITHUB_TOKEN` must include the `attestations:write` scope. The token is used by:
- `gh attestation sign` (at publish time)
- `gh attestation verify` (at download time)

Verify scope by checking the token's GitHub PAT settings or via HTTP `GET /user` with header `X-OAuth-Scopes`.

## GitHub CLI Requirement

The `gh` CLI tool must be installed and must support the `attestation` subcommand (available in recent GitHub CLI versions, e.g., ≥2.30.0). Check with:

```bash
gh attestation --help
```

## Error Cases

- **Missing attestation file**: `verify` will fail if the `.attestation.jsonl` sidecar is not present alongside the artifact.
- **Corrupted artifact**: If the artifact is modified after signing (e.g., in transit), `verify` will reject it.
- **Invalid signature**: If the signature doesn't match the repo or GitHub's certificate chain, `verify` fails.
- **Offline verification**: `verify` requires network access to GitHub to check the certificate. Air-gapped environments must set `MCP_ATTESTATION_MODE=skip`.

## Sidecar Convention

Attestation files follow the naming convention:
```
<artifact>           e.g., index-abc123.tar.gz
<artifact>.attestation.jsonl  e.g., index-abc123.tar.gz.attestation.jsonl
```

Both files must be kept together in the same directory and published to the same release.
