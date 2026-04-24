> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**

# GA E2E Evidence

## Summary

- Evidence captured: 2026-04-24T18:47:00Z.
- Repository: `ViperJuice/Code-Index-MCP`.
- Observed commit: `8d08545c15c53322128ef87b5e06308bd8b0dad3`.
- Phase plan: `plans/phase-plan-v5-gae2e.md`.
- Active product-level release posture from `docs/validation/ga-readiness-checklist.md`: `public-alpha`.
- Active package/image baseline: `index-it-mcp` / `v1.2.0-rc5` / `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc5`.
- Local smoke image used for container evidence: `ghcr.io/viperjuice/code-index-mcp:local-smoke`.

GAE2E does not create a GA claim. It refreshes end-to-end evidence for the
current RC/public-alpha baseline so later phases can make a mechanically
defensible RC or GA decision without reinterpreting install surfaces, readiness
vocabulary, or artifact identities.

## Release-Surface Smoke

Release-surface command set frozen by `scripts/release_smoke.py`,
`tests/smoke/test_release_smoke_contract.py`, and `Makefile`:

| Command | Timestamp | Result |
|---|---|---|
| `uv run pytest tests/smoke/test_release_smoke_contract.py -v --no-cov` | 2026-04-24T18:39:17Z | Passed, 6 tests. |
| `uv run pytest tests/test_release_metadata.py -v --no-cov` | 2026-04-24T18:39:17Z | Passed, 8 tests after GAE2E parity updates. |
| `make release-smoke` | 2026-04-24T18:47:00Z | Passed; wheel build/install and STDIO smoke completed against a fresh venv and fixture repo. |
| `make release-smoke-container` | 2026-04-24T18:47:00Z | Passed; production Dockerfile built `ghcr.io/viperjuice/code-index-mcp:local-smoke`, container CLI help succeeded, fail-closed handler smoke returned `index_unavailable`, and `/health` returned healthy. |

Frozen smoke expectations:

- Wheel/native install produces and installs `index_it_mcp-1.2.0rc5-py3-none-any.whl`.
- STDIO smoke proves `search_code`, `symbol_lookup`, and `get_status` on a
  ready registered repo and verifies `index_unavailable` with
  `safe_fallback: "native_search"` for an unregistered repo.
- Container smoke uses the local evidence tag `ghcr.io/viperjuice/code-index-mcp:local-smoke`
  without publishing or retagging the release channel.
- Installer helpers keep `v1.2.0-rc5` as the recommended default and leave
  `latest` as an explicit stable-only selector rather than an implicit pre-GA
  default.

## Fresh Repository Durability

Happy-path repository flows were refreshed against the existing multi-repo test
fixtures instead of introducing a separate harness:

| Command | Timestamp | Result |
|---|---|---|
| `uv run pytest tests/smoke/test_secondary_tool_readiness_smoke.py -v --no-cov` | 2026-04-24T18:39:18Z | Passed, 1 test; ready registered repo proved `reindex -> search_code -> symbol_lookup -> summarize_sample` with durable SQLite rows. |
| `uv run pytest tests/test_multi_repo_production_matrix.py tests/integration/test_multi_repo_server.py -v --no-cov` | 2026-04-24T18:47:00Z | Passed; unrelated repos remained isolated, watcher-style repair stayed repo-scoped, and repository-scoped summary handlers stayed inside the requested repo. |

Durability facts frozen by GAE2E:

- `reindex` on a clean registered repo persists durable rows in SQLite `files`
  and records `durable_files >= 1`.
- Ready-path query tools return readiness state `ready`, not
  `index_unavailable`.
- `symbol_lookup` resolves the newly indexed symbol from the registered repo
  instead of crossing into sibling repositories.
- `summarize_sample` only runs on a ready registered repository scope and
  returns `files_processed`, `model_used`, `persisted`, and repo-local
  `file_path` rows. In test evidence, the summarizer is mocked so the release
  proof stays metadata-only and does not require a live provider secret.

## Fail-Closed Readiness Matrix

The non-ready matrix stayed explicit and fail-closed:

| Command | Timestamp | Result |
|---|---|---|
| `uv run pytest tests/test_multi_repo_failure_matrix.py tests/test_tool_readiness_fail_closed.py -v --no-cov` | 2026-04-24T18:39:18Z | Passed, 8 tests. |
| `uv run pytest tests/test_repository_readiness.py tests/test_git_index_manager.py -v --no-cov` | 2026-04-24T18:47:00Z | Passed; readiness classifier values and branch-drift guard behavior remained frozen. |

Frozen fail-closed rows:

- Query tools return `code: "index_unavailable"` plus
  `safe_fallback: "native_search"` for `unsupported_worktree`,
  `wrong_branch`, `stale_commit`, `missing_index`, and
  `unregistered_repository`.
- Secondary tools `reindex`, `write_summaries`, and `summarize_sample` refuse
  the same non-ready states with `results: []` and no native-search fallback;
  `reindex` records `mutation_performed: false`, while summary tools record
  `persisted: false`.
- `path_outside_allowed_roots` still wins before readiness classification for
  out-of-sandbox repository or explicit-path inputs.
- `conflicting_path_and_repository` still wins before summarization or
  mutation when the repository argument and explicit paths do not resolve to
  the same repo.
- Ready no-match behavior stays distinct: ready query misses remain true empty
  result sets or `result: "not_found"` instead of synthetic readiness errors.

## Artifact Identity

GAE2E froze the current artifact identities across tests and helpers rather
than changing release channel state:

| Surface | Frozen identity |
|---|---|
| Python package | `index-it-mcp` |
| Runtime version | `1.2.0-rc5` |
| Git tag | `v1.2.0-rc5` |
| Wheel | `index_it_mcp-1.2.0rc5-py3-none-any.whl` |
| sdist | `index_it_mcp-1.2.0rc5.tar.gz` |
| Container image | `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc5` |
| Local smoke image | `ghcr.io/viperjuice/code-index-mcp:local-smoke` |
| Release metadata evidence | `docs/validation/rc5-release-evidence.md` |
| Governance/channel evidence | `docs/validation/ga-governance-evidence.md` |

Helper parity decisions:

- `scripts/install-mcp-docker.sh` and `scripts/install-mcp-docker.ps1` now
  recommend `v1.2.0-rc5` by default and keep `latest` opt-in because
  `latest` is a stable-only channel and GABASE still freezes a pre-GA posture.
- `scripts/download-release.py` now recognizes both legacy index archives and
  the current package-release assets (`wheel`, `sdist`, `CHANGELOG.md`,
  `DEPLOYMENT-GUIDE.md`, `sbom.spdx.json`) so helper behavior matches the
  actual RC/public-alpha release surfaces instead of only older index bundles.

## Inputs And Posture

GAE2E consumed, but did not replace:

- `docs/validation/ga-readiness-checklist.md` for product-level release posture
  (`public-alpha`, `beta`, `GA`) and required evidence sequencing.
- `docs/SUPPORT_MATRIX.md` for row-level support tiers
  (`GA-supported`, `beta`, `experimental`, `unsupported`,
  `disabled-by-default`).
- `docs/validation/ga-governance-evidence.md` for branch protection and release
  channel metadata.
- `docs/validation/rc5-release-evidence.md` for published tag, wheel, sdist,
  GHCR, and GitHub release identity.

That split matters: GAE2E records execution evidence against the current
baseline, but it does not collapse product-level release posture into row-level
support tiers and it does not turn an RC/public-alpha artifact into final GA
release wording.

## Verification

Passed:

```bash
uv run pytest tests/docs/test_gae2e_evidence_contract.py -v --no-cov
```

Passed:

```bash
uv run pytest tests/smoke/test_release_smoke_contract.py tests/smoke/test_secondary_tool_readiness_smoke.py -v --no-cov
```

Passed:

```bash
uv run pytest tests/test_multi_repo_production_matrix.py tests/integration/test_multi_repo_server.py tests/test_multi_repo_failure_matrix.py tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py -v --no-cov
```

Passed:

```bash
uv run pytest tests/test_release_metadata.py -v --no-cov
```

Passed:

```bash
make release-smoke
```

Passed:

```bash
make release-smoke-container
```
