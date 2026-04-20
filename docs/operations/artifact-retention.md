# Artifact Retention & Janitor Guide

This document provides operators with guidance on managing artifact retention and running the retention janitor CLI tool.

## Overview

The retention janitor is a CLI tool that removes old or excess artifact revisions from GitHub releases. It is **operator-triggered** (not a daemon) and respects protected release markers to prevent data loss.

### Protected Releases

The janitor **never deletes**:

- The `index-latest` pointer release (contains the current code index reference)
- Any release marked with `isLatest=true` in metadata
- The most recent N releases (where N = `MCP_ARTIFACT_RETENTION_COUNT`)

## Configuration

### Environment Variables

Set these before running the janitor:

#### `MCP_ARTIFACT_RETENTION_DAYS`
- **Description**: Maximum age (in days) for artifact revisions
- **Type**: Integer
- **Default**: `30`
- **Example**:
  ```bash
  export MCP_ARTIFACT_RETENTION_DAYS=14  # Delete artifacts older than 14 days
  ```

#### `MCP_ARTIFACT_RETENTION_COUNT`
- **Description**: Maximum number of artifact revisions to keep per artifact
- **Type**: Integer
- **Default**: `10`
- **Example**:
  ```bash
  export MCP_ARTIFACT_RETENTION_COUNT=5  # Keep only the 5 most recent revisions
  ```

## Running the Janitor

### Basic Syntax

```bash
python -m mcp_server.cli retention prune --repo OWNER/REPO [OPTIONS]
```

### Required Arguments

- `--repo OWNER/REPO` — GitHub repository in `owner/repo` format (e.g., `anthropic/code-index-mcp`)

### Optional Arguments

#### `--dry-run`
- Perform a trial run without deleting anything
- Lists all candidates for deletion
- **Always run with `--dry-run` first** to verify you're not deleting important artifacts

```bash
python -m mcp_server.cli retention prune \
  --repo myorg/myrepo \
  --dry-run
```

#### `--older-than-days N`
- Override `MCP_ARTIFACT_RETENTION_DAYS` for this run
- Delete releases older than N days

```bash
python -m mcp_server.cli retention prune \
  --repo myorg/myrepo \
  --older-than-days 7 \
  --dry-run
```

#### `--keep-latest-n N`
- Override `MCP_ARTIFACT_RETENTION_COUNT` for this run
- Keep the N most recent releases

```bash
python -m mcp_server.cli retention prune \
  --repo myorg/myrepo \
  --keep-latest-n 3 \
  --dry-run
```

### Authorization

The tool requires `GITHUB_TOKEN` environment variable with the `repo` scope:

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"  # Token with repo scope
python -m mcp_server.cli retention prune --repo owner/repo
```

## Workflows

### Scenario 1: Trial Run Before Production Cleanup

```bash
# Set retention policy
export MCP_ARTIFACT_RETENTION_DAYS=30
export MCP_ARTIFACT_RETENTION_COUNT=10
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Review what would be deleted
python -m mcp_server.cli retention prune \
  --repo myorg/myrepo \
  --dry-run

# Expected output:
# Candidates for deletion (older than 30 days or beyond 10 most recent):
# - release-abc123 (created 2026-02-15)
# - release-def456 (created 2026-02-10)
# ... (list of releases)

# If satisfied, run without --dry-run
python -m mcp_server.cli retention prune \
  --repo myorg/myrepo

# Expected output:
# Pruned 2 releases matching retention policy
# Freed approximately 250MB
```

### Scenario 2: Aggressive Cleanup (Emergency Disk Space)

If disk space is critical and you need to free space immediately:

```bash
# Keep only the 3 most recent releases
# Delete anything older than 7 days
python -m mcp_server.cli retention prune \
  --repo myorg/myrepo \
  --older-than-days 7 \
  --keep-latest-n 3 \
  --dry-run

# Review and confirm
python -m mcp_server.cli retention prune \
  --repo myorg/myrepo \
  --older-than-days 7 \
  --keep-latest-n 3
```

### Scenario 3: One-Time Cleanup at Scheduled Window

```bash
# In a cron job or scheduled task
# Run daily at 2 AM
0 2 * * * \
  source /etc/mcp-server/env && \
  python -m mcp_server.cli retention prune \
    --repo myorg/myrepo \
    --older-than-days 30 \
  >> /var/log/mcp-retention.log 2>&1
```

### Scenario 4: Multiple Repositories

```bash
# Loop through repositories
REPOS=("org1/repo1" "org1/repo2" "org2/repo3")

for repo in "${REPOS[@]}"; do
  echo "Pruning $repo..."
  python -m mcp_server.cli retention prune \
    --repo "$repo" \
    --dry-run
done
```

## Output Format

### Dry-Run Output

```
Artifact Retention Janitor — Dry Run
Repository: myorg/myrepo
Retention Policy: Keep 10 most recent OR newer than 30 days

Protected Releases (never deleted):
  - index-latest (current code index)
  - latest-production (isLatest=true)

Candidates for Deletion (by creation date, oldest first):
  1. v1.0-abc123 (created 2026-02-08 — 70 days old) → DELETE
  2. v1.0-def456 (created 2026-02-12 — 66 days old) → DELETE
  3. v1.0-ghi789 (created 2026-02-15 — 63 days old) → DELETE
  (... more candidates ...)

Total candidates: 3
Estimated space to free: ~150 MB

Would proceed with deletion? (dry-run only, no changes made)
```

### Execution Output

```
Artifact Retention Janitor — Execution
Repository: myorg/myrepo
Retention Policy: Keep 10 most recent OR newer than 30 days

Deleting release: v1.0-abc123
  ✓ Deleted GitHub release
  ✓ Cleaned up associated artifacts

Deleting release: v1.0-def456
  ✓ Deleted GitHub release
  ✓ Cleaned up associated artifacts

Deleting release: v1.0-ghi789
  ✓ Deleted GitHub release
  ✓ Cleaned up associated artifacts

Summary:
  Releases deleted: 3
  Space freed: ~150 MB
  Duration: 2.3 seconds
```

### Error Output

```
Error: Release 'v1.0-protected' marked as isLatest=true — skipping
Error: Failed to delete 'v1.0-bad456': 403 Forbidden (insufficient token scope?)
Error: GitHub API rate limit exceeded — retry after 60 seconds

Partial cleanup complete:
  Releases deleted: 2
  Releases skipped: 1
  Releases failed: 1
```

## Troubleshooting

### "Insufficient token scope?" Error

The `GITHUB_TOKEN` must have the `repo` scope:

```bash
# Verify token has repo scope
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -I | grep X-OAuth-Scopes

# Expected output includes: repo
# X-OAuth-Scopes: repo, read:user
```

**Fix**: Regenerate the token with `repo` scope.

### "Protected Release — Skipping" Messages

These are expected and safe. The janitor is protecting:
- `index-latest` (current code index pointer)
- Any release with `isLatest=true` metadata
- The N most recent releases (where N = `MCP_ARTIFACT_RETENTION_COUNT`)

**Action**: No action needed — these releases are intentionally preserved.

### Rate Limit Exceeded

GitHub API enforces rate limits (5000 requests/hour for authenticated tokens):

```bash
# Check current rate limit
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit | jq .
```

**Fix**: Wait for the `reset` timestamp to pass, then retry.

### No Releases Deleted

This can happen if:
1. All releases are younger than `MCP_ARTIFACT_RETENTION_DAYS`
2. You have fewer releases than `MCP_ARTIFACT_RETENTION_COUNT`
3. All releases are marked as protected (`index-latest` or `isLatest=true`)

**Action**: Adjust retention policy with `--older-than-days` or `--keep-latest-n` if desired.

## Disk Space Calculation

### Estimating Space Freed

Each artifact revision can vary in size. To estimate:

```bash
# List releases with sizes (GitHub API)
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/releases | \
  jq '.[] | {name, created_at, size_bytes}'
```

### Typical Space Savings

- **Code index artifacts**: 10–100 MB per revision
- **With 30-day retention at 10 revisions**: ~500 MB–1 GB
- **Aggressive policy** (7 days, 3 revisions): ~30–90 MB

## Best Practices

1. **Always dry-run first**:
   ```bash
   python -m mcp_server.cli retention prune --repo OWNER/REPO --dry-run
   ```

2. **Run during low-traffic windows**: Schedule cleanup for off-peak hours (e.g., 2–4 AM UTC).

3. **Monitor disk usage**:
   ```bash
   df -h /path/to/artifact/storage
   ```
   Set up alerting if free space drops below 20%.

4. **Keep audit logs**:
   ```bash
   python -m mcp_server.cli retention prune \
     --repo OWNER/REPO \
     2>&1 | tee -a /var/log/mcp-retention-$(date +%Y%m%d).log
   ```

5. **Version your policy**: Document the retention policy in your ops runbook:
   ```bash
   # Retention policy as of 2026-04-20:
   # - Keep 10 most recent revisions per artifact
   # - Delete revisions older than 30 days
   # - Never delete index-latest or isLatest=true releases
   ```

## See Also

- `docs/configuration/environment-variables.md` — `MCP_ARTIFACT_RETENTION_DAYS` and `MCP_ARTIFACT_RETENTION_COUNT`
- `docs/operations/gateway-startup-checklist.md` — gateway deployment
- `mcp_server/artifacts/retention.py` — janitor implementation
