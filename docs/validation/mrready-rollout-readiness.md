> **Historical artifact — as-of 2026-04-25, may not reflect current behavior**

# MRREADY Rollout Readiness

## Verdict

- Evidence captured: 2026-04-27T09:04:51Z.
- Repository: `ViperJuice/Code-Index-MCP`.
- Observed commit: `17b8742cc030a5cd42830604bbc7323ca2e622cf`.
- Phase plan: `plans/phase-plan-v6-MRREADY.md`.
- Verdict: `controlled rollout only`.

MRREADY is the final reducer for the v6 multi-repo hardening line. It consumes
the accepted hydration evidence in `docs/validation/mre2e-evidence.md`,
freezes one operator-facing rollout status surface, and records whether the
current multi-repo package is ready for broad deployment or still bounded by
beta controls.

## Rollout Status Contract

MRREADY freezes these rollout-facing statuses for
`mcp-index repository list -v`, `mcp-index repository status`, and
`mcp-index artifact workspace-status`:

- `ready`
- `local_only`
- `publish_failed`
- `wrong_branch`
- `stale_commit`
- `missing_index`
- `partial_index_failure`

These are rollout and operator-recovery states, not query results. Query tools
remain fail-closed: when readiness is not `ready`, MCP search returns
`index_unavailable` with `safe_fallback: "native_search"` and the existing
readiness remediation. In other words, rollout status is a repository/workspace
surface, while `index_unavailable` is the query surface.

## Operator Command Set

Frozen MRREADY command set:

```bash
mcp-index repository list -v
mcp-index repository status
mcp-index artifact workspace-status
mcp-index artifact reconcile-workspace
uv run pytest tests/docs/test_mrready_rollout_contract.py -q --no-cov
uv run pytest tests/test_git_index_manager.py tests/test_health_surface.py tests/test_repository_commands.py tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py -q --no-cov
```

Supporting guidance remains anchored in:

- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `docs/operations/artifact-retention.md`

## Recovery Mapping

Use the surfaced rollout status to choose the next operator action:

| Status | Meaning | Recovery path |
|---|---|---|
| `ready` | Local runtime state, readiness, and artifact state agree. | Indexed results may be trusted. |
| `local_only` | Local runtime state works, but durable rollout readiness is not yet proven. | Publish or fetch/reconcile workspace artifacts before broader rollout. |
| `publish_failed` | Artifact publication failed. | Repair the publish path, then rerun publish/reconcile checks. |
| `wrong_branch` | The checkout is not on the tracked/default branch. | Switch to the tracked branch or register the intended path. |
| `stale_commit` | The index is behind `HEAD`. | Reindex or fetch the matching artifact, then reconcile workspace state. |
| `missing_index` | No durable local index exists. | Reindex or fetch workspace state before querying. |
| `partial_index_failure` | A required incremental mutation failed. | Run a full reindex or hydrate a known-good artifact, then reconcile workspace state. |

## Beta Boundary

MRREADY does not erase the existing beta limits:

- multi-repo and STDIO remain beta surfaces;
- the supported topology is still many unrelated repositories with one
  registered worktree per git common directory;
- only the tracked/default branch is indexed automatically;
- status rows are not a substitute for query readiness;
- `docs/validation/mre2e-evidence.md` remains the upstream hydration proof, not
  a broad rollout decision.

Because those limits still apply, the correct MRREADY verdict is
`controlled rollout only`, not broad multi-repo deployment.

## Verification

Executed during MRREADY:

```bash
uv run pytest tests/docs/test_mrready_rollout_contract.py -q --no-cov
uv run pytest tests/test_git_index_manager.py tests/test_health_surface.py tests/test_repository_commands.py tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py -q --no-cov
```
