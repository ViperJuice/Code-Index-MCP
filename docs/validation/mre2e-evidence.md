> **Historical artifact — as-of 2026-04-25, may not reflect current behavior**

# MRE2E Evidence

## Summary

- Evidence captured: 2026-04-27T08:48:42Z.
- Repository: `ViperJuice/Code-Index-MCP`.
- Observed commit: `09b777992cd6cd22211c860f1014676250319990`.
- Phase plan: `plans/phase-plan-v6-MRE2E.md`.

MRE2E is the acceptance record for the v6 multi-repo hardening line. It freezes
the supported two-repository lifecycle as `register -> index -> publish ->
hydrate -> reconcile -> query`, proves wrong-branch non-mutation behavior, and
records the hydration validation fields that must pass before a restored local
workspace is treated as `ready`.

## Supported Deployment Shape

Normal CI uses a deterministic local GitHub/CLI mock strategy. The tests
exercise the real workspace lifecycle surfaces and local runtime files, but
normal CI does not require live GitHub publication, live release mutation, or
network artifact downloads.

Optional live-operator validation remains outside routine CI:

- use the existing CLI/runtime publication path only when an operator explicitly
  needs to confirm real GitHub artifact behavior;
- preserve the local-first workspace commands as the canonical acceptance
  surface for MRE2E;
- leave rollout posture, operator gating, and any broader deployment claim to
  `MRREADY`.

## Fresh-State Multi-Repo Lifecycle

The accepted lifecycle is two unrelated repositories on one machine, with one
registered worktree per git common directory and tracked/default branch
indexing only.

Frozen command set:

| Command | Result |
|---|---|
| `uv run pytest tests/integration/test_multi_repo_hydration.py -q --no-cov` | Proves register, index, publish, hydrate, reconcile, and query across two repos from clean local artifact state. |
| `uv run pytest tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py -q --no-cov` | Freezes workspace-status, publish-workspace, fetch-workspace, and reconcile-workspace truth surfacing. |
| `uv run pytest tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py tests/integration/test_multi_repo_server.py -q --no-cov` | Preserves ready-path isolation and fail-closed readiness vocabulary. |
| `uv run pytest tests/docs/test_mre2e_evidence_contract.py -q --no-cov` | Keeps this artifact and deployment-shape wording canonical. |

Lifecycle facts frozen by MRE2E:

- the tracked/default branch repository returns to `ready` after hydrate and
  reconcile;
- hydrated query results reflect add, modify, delete, and rename behavior from
  the restored artifact-backed SQLite state, not a silent local reseed;
- unrelated repositories remain isolated after hydration and reconcile;
- ready-path query results stay distinct from `index_unavailable` fail-closed
  rows.

## Wrong-Branch Non-Mutation Contract

Wrong-branch repositories remain fail-closed for both query and workspace
artifact mutation surfaces.

Frozen behavior:

- query tools return `code: "index_unavailable"` with
  `safe_fallback: "native_search"` and readiness state `wrong_branch`;
- workspace mutation actions refuse wrong-branch repositories without mutating
  tracked repository index rows, registry state, or ready query results;
- readiness wording stays within the existing vocabulary: `ready`,
  `wrong_branch`, `stale_commit`, `missing_index`, `unsupported_worktree`, and
  `unregistered_repository`.

## Hydration Validation Evidence

Hydration truth must surface explicit validation evidence rather than only a
restored file list.

Required surfaced fields:

- `artifact_backend`
- `artifact_health`
- `last_published_commit`
- `last_recovered_commit`
- `validation_status`
- `validation_reasons`
- `checksum`
- `branch`
- `commit`
- `schema_version`
- `semantic_profile_hash`
- `semantic_profiles`

The accepted happy-path validation record names both canonical semantic
profiles, `commercial_high` and `oss_high`, and treats an empty
`validation_reasons` list as a passed validation path rather than a missing
proof.

## Beta Limitations

MRE2E does not widen support claims beyond the existing beta model:

- many unrelated repositories are supported only through one registered
  worktree per git common directory;
- only the tracked/default branch is indexed automatically;
- local-first workspace lifecycle commands are the supported operator path for
  CI acceptance;
- optional live-operator validation is intentionally separate from normal CI;
- broader rollout posture, operator sequencing, and any final “ready for broad
  deployment” statement are deferred to `MRREADY`.

## Verification

Planned and required:

```bash
uv run pytest tests/docs/test_mre2e_evidence_contract.py -q --no-cov
uv run pytest tests/integration/test_multi_repo_hydration.py -q --no-cov
uv run pytest tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py -q --no-cov
uv run pytest tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py tests/integration/test_multi_repo_server.py -q --no-cov
```
