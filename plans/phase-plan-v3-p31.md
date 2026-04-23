# P31: Artifact Identity, Hydration & Freshness

> Plan doc produced by `codex-plan-phase specs/phase-plans-v3.md P31` on 2026-04-23.
> Source roadmap `specs/phase-plans-v3.md` is staged in this worktree (`git status --short` shows `A  specs/phase-plans-v3.md`).

## Context

P31 consumes P27's repository identity/readiness contract, P29's durable ctx-first
mutation contract, and P30's tracked-branch-only publish policy. Implementation should
not start until P30 proves that wrong-branch and unsupported-worktree paths do not mutate
or publish artifacts.

The current artifact surface still mixes at least three contracts:

- GitHub Actions artifacts named `mcp-index-<sha>` or `index-<commit>-<suffix>`.
- GitHub release tags named `index-<short_sha>` and `index-latest`.
- Local commit artifacts named `<repo_id>-<short_commit>-index.tar.gz`.

Those names do not carry the full v3 identity, and the release-level `index-latest`
pointer is global within a GitHub repository. In a multi-repo local runtime, global
"latest" is not safe unless every download validates repo id, tracked branch, commit,
schema version, checksum, and semantic profile compatibility before installation.

The current upload/download code is also root-directory oriented. `IndexArtifactUploader`,
`SecureIndexExporter`, `IndexArtifactDownloader.install_indexes()`, the artifact CLI, and
`MultiRepoArtifactCoordinator` largely assume `code_index.db` in the process working
directory. Registered repositories now use `repo.index_path`, normally
`.mcp-index/current.db`, and `StoreRegistry` opens that path. P31 must make hydration land
in the same repo-scoped runtime path the registry and readiness classifier use.

`MultiRepoArtifactCoordinator` currently uses process-wide `os.chdir()` through `_pushd()`.
That is unsafe in a multi-repo server because concurrent repository operations can observe
the wrong working directory. P31 should make repo path and index path explicit API inputs.

Freshness is presently advisory after download. `download_selected_artifact()` logs
`STALE_COMMIT`, `STALE_AGE`, or `INVALID` and proceeds with install. P31 changes this to
fail closed by default. Any unsafe install must be explicit at the call site and visible
in CLI output or logs.

Provider routing also needs a production guard. `ArtifactProviderFactory` can select the
placeholder S3 provider even though every S3 method raises `NotImplementedError`. P31
should either remove S3 from production selection or make it opt-in only for non-production
experiments with an explicit error explaining that S3 is not implemented.

External phase dependencies: P27, P29, and P30 must be completed before P31
implementation. In particular, P31 lanes assume P30 changed successful sync actions to the
actual `IndexSyncResult.action` values emitted by `GitAwareIndexManager`.

## Interface Freeze Gates

- [ ] IF-0-P31-1 - Artifact identity contract: every canonical artifact id, archive metadata payload, and `ArtifactManifestV2` payload includes `repo_id`, `tracked_branch`, `commit`, `schema_version`, `semantic_profile_hash`, `checksum`, and `artifact_type`; legacy names are compatibility aliases only and are never trusted without metadata validation.
- [ ] IF-0-P31-2 - Semantic profile hash contract: `semantic_profile_hash` is a deterministic SHA256 hex digest over sorted semantic profile ids and compatibility fingerprints; lexical-only artifacts use a stable `lexical-only` profile token.
- [ ] IF-0-P31-3 - Download validation contract: downloads reject wrong repo, wrong tracked branch, unknown schema, stale commit, invalid or missing metadata, checksum mismatch, and semantic profile mismatch before extraction or install unless an explicit unsafe override is supplied.
- [ ] IF-0-P31-4 - Unsafe override contract: unsafe install is available only through an explicit `allow_unsafe=True` API argument or a clearly named CLI flag, and every unsafe install records the rejected validation reasons in logs/output.
- [ ] IF-0-P31-5 - Hydration location contract: canonical install writes the lexical SQLite database to `repo.index_path` (`.mcp-index/current.db`) and writes artifact/index metadata plus repo-scoped semantic state under `repo.index_location`; root-level `code_index.db` is read/write compatibility only.
- [ ] IF-0-P31-6 - No process chdir contract: artifact upload, download, workspace publish, workspace fetch, and reconciliation pass `repo_path`, `index_path`, and `index_location` explicitly and never call process-wide `os.chdir()`.
- [ ] IF-0-P31-7 - Publish trigger contract: watcher/reindex publication runs only after successful mutating sync actions (`full_index` or `incremental_update`) and reports a clear local-only artifact state when remote publication is unavailable or disabled.
- [ ] IF-0-P31-8 - Provider safety contract: production configuration cannot route to unimplemented S3/GCS/Azure providers; `auto` falls back to implemented providers only, and explicit unimplemented-provider selection raises a deterministic configuration error.

## Lane Index & Dependencies

- SL-0 - Manifest identity and validation contract; Depends on: P27; Blocks: SL-1, SL-2; Parallel-safe: yes
- SL-1 - Canonical archive and publisher identity; Depends on: P27, SL-0, SL-6; Blocks: SL-2, SL-4, SL-5; Parallel-safe: mixed
- SL-2 - Fail-closed download and repo-scoped hydration engine; Depends on: P27, SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Single-repo artifact CLI and local commit-artifact compatibility; Depends on: SL-2; Blocks: SL-7; Parallel-safe: yes
- SL-4 - Multi-repo coordinator without chdir; Depends on: SL-1, SL-2; Blocks: SL-7; Parallel-safe: yes
- SL-5 - Watcher and reindex publish triggers; Depends on: P29, P30, SL-1; Blocks: SL-7; Parallel-safe: yes
- SL-6 - Provider selection fail-safe; Depends on: (none); Blocks: SL-1, SL-7; Parallel-safe: yes
- SL-7 - P31 docs, workflow, and contract audit; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4, SL-5, SL-6; Blocks: P33; Parallel-safe: no

Lane DAG:

```text
P27
 └─> SL-0 ─> SL-1 ─> SL-2 ─> SL-3 ─┐
      │       │       └────> SL-4 ─┤
SL-6 ─┘       └────> SL-5 <─ P29 + P30
                              │
SL-0 + SL-1 + SL-2 + SL-3 + SL-4 + SL-5 + SL-6 ─> SL-7 ─> P33
```

## Lanes

### SL-0 - Manifest Identity And Validation Contract

- **Scope**: Make the artifact manifest and integrity gate express the full P31 identity before any upload or download path uses it.
- **Owned files**: `mcp_server/artifacts/manifest_v2.py`, `mcp_server/artifacts/integrity_gate.py`, `tests/test_artifact_manifest_v2.py`, `tests/test_artifact_integrity_gate.py`
- **Interfaces provided**: `ArtifactManifestV2.semantic_profile_hash`; deterministic `semantic_profile_hash` builder; canonical `logical_artifact_id` shape; required metadata validation for `repo_id`, `tracked_branch`, `commit`, `schema_version`, `semantic_profile_hash`, `checksum`, and `artifact_type`; IF-0-P31-1 through IF-0-P31-3 validation evidence
- **Interfaces consumed**: P27 `repo_id` identity; existing `ManifestUnit.compatibility_fingerprint`; existing `validate_artifact_integrity()` checksum gate
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `test_manifest_v2_round_trip_serialization` to assert `repo_id`, `tracked_branch`, `commit`, `schema_version`, `semantic_profile_hash`, and `logical_artifact_id` survive round trip.
  - test: Add manifest validation cases for missing `repo_id`, missing tracked branch, missing checksum, duplicate units, and malformed semantic profile hash.
  - test: Add deterministic semantic-profile-hash tests: sorted profiles produce one hash, reordered profiles produce the same hash, fingerprint changes produce a different hash, lexical-only produces the stable lexical token.
  - test: Extend integrity-gate tests so missing `repo_id`, `tracked_branch`, `semantic_profile_hash`, or checksum fails closed.
  - impl: Add a manifest helper that builds `semantic_profile_hash` from sorted profile ids and compatibility fingerprints without reading global settings.
  - impl: Require `repo_id`, `tracked_branch`, `commit`, `schema_version`, `semantic_profile_hash`, `checksum`, and `artifact_type` in integrity metadata validation.
  - impl: Keep legacy `branch` metadata readable as an input alias, but normalize canonical validation/output to `tracked_branch`.
  - verify: `uv run pytest tests/test_artifact_manifest_v2.py tests/test_artifact_integrity_gate.py -v --no-cov`

### SL-1 - Canonical Archive And Publisher Identity

- **Scope**: Make upload, archive creation, and release publishing generate canonical repo-scoped artifact ids and metadata from explicit repo/index paths.
- **Owned files**: `mcp_server/artifacts/artifact_upload.py`, `mcp_server/artifacts/publisher.py`, `mcp_server/artifacts/secure_export.py`, `tests/test_artifact_upload.py`, `tests/test_artifact_publish_rollback.py`, `tests/test_artifact_auto_delta.py`, `tests/test_artifact_publish_race.py`, `tests/security/test_artifact_attestation.py`
- **Interfaces provided**: `IndexArtifactUploader.compress_indexes(index_location=..., output_path=..., secure=...)`; `IndexArtifactUploader.create_metadata(repo_id=..., tracked_branch=..., commit=..., schema_version=..., semantic_profile_hash=...)`; canonical artifact name `mcp-index-<repo_id>-<tracked_branch>-<short_commit>-<semantic_profile_hash>`; `ArtifactPublisher.publish_on_reindex(repo_id, commit, tracked_branch=..., index_location=...)`; IF-0-P31-1 and IF-0-P31-2 upload evidence
- **Interfaces consumed**: SL-0 manifest identity helpers; SL-6 provider decision contract; existing `DeltaPolicy`; existing attestation `attest()` contract; P29/P30 durable index path `repo.index_location`
- **Parallel-safe**: mixed
- **Tasks**:
  - test: Add `tests/test_artifact_upload.py` covering archive creation from `.mcp-index/current.db`, metadata creation with full P31 identity, lexical-only hash fallback, and compatibility archive inclusion for legacy `code_index.db` only when no `current.db` is supplied.
  - test: Update publisher tests so SHA-keyed tags include repo id and tracked branch, and global `index-latest` is treated as a compatibility pointer whose target metadata still validates repo identity.
  - test: Preserve rollback and race tests with the new canonical tag/name shape.
  - test: Update delta tests so `create_metadata()` receives and persists P31 identity fields for full and delta artifacts.
  - impl: Change `SecureIndexExporter` to accept explicit `repo_path` and `index_location`, read ignore files from `repo_path`, and export `current.db`, `.index_metadata.json`, and `vector_index.qdrant` from `index_location`.
  - impl: Change `IndexArtifactUploader` so archive/stat/schema reads do not assume process cwd or root-level `code_index.db`.
  - impl: Build artifact metadata with canonical `tracked_branch` while preserving legacy `branch` as a duplicate compatibility field during the migration window.
  - impl: Add `manifest_v2` to uploaded metadata using SL-0 helpers and current semantic profile metadata.
  - impl: Change `ArtifactPublisher` release/tag naming to include repo id and tracked branch; keep `index-latest` only as an alias that is never sufficient for download validation.
  - verify: `uv run pytest tests/test_artifact_upload.py tests/test_artifact_publish_rollback.py tests/test_artifact_auto_delta.py tests/test_artifact_publish_race.py tests/security/test_artifact_attestation.py -v --no-cov`

### SL-2 - Fail-Closed Download And Repo-Scoped Hydration Engine

- **Scope**: Make artifact selection, compatibility, freshness, extraction, and install reject unsafe payloads before writing repo runtime state.
- **Owned files**: `mcp_server/artifacts/artifact_download.py`, `mcp_server/artifacts/freshness.py`, `tests/test_artifact_download.py`, `tests/test_artifact_freshness.py`, `tests/test_artifact_recovery_selection.py`
- **Interfaces provided**: `IndexArtifactDownloader.download_selected_artifact(..., repo_id, repo_path, tracked_branch, target_commit, index_location, index_path, allow_unsafe=False)`; `install_indexes(source_dir, index_location, index_path, backup=True)` writing `.mcp-index/current.db`; fail-closed `FreshnessVerdict` enforcement; IF-0-P31-3 through IF-0-P31-5 evidence
- **Interfaces consumed**: SL-0 integrity validation; SL-1 canonical metadata/archive shape; P27 tracked branch and repo id; `SchemaMigrator.is_known()` and `UnknownSchemaVersionError`; existing attestation verification
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_artifact_download.py` cases that reject wrong `repo_id`, wrong `tracked_branch`, stale commit, unknown schema, invalid metadata, missing checksum, checksum mismatch, and semantic profile mismatch before extraction/install.
  - test: Add unsafe override coverage proving rejected reasons are returned/logged and install proceeds only when `allow_unsafe=True`.
  - test: Change freshness tests so `STALE_COMMIT`, `STALE_AGE`, and `INVALID` block install by default instead of logging and proceeding.
  - test: Add hydration tests proving canonical install writes `repo.index_path` as `.mcp-index/current.db`, metadata files under `repo.index_location`, and no root-level `code_index.db` in normal mode.
  - test: Preserve tar-member traversal tests and add a legacy archive case where `code_index.db` is accepted only after metadata validation and installed as `current.db`.
  - test: Update recovery selection tests so branch/commit name matching is only a candidate filter; metadata validation decides final acceptance.
  - impl: Add an explicit artifact validation method that compares metadata/manifest identity to expected `repo_id`, `tracked_branch`, and commit before extraction and before install.
  - impl: Make freshness verdicts hard failures unless `allow_unsafe=True`; remove warning-only continuation for stale and invalid metadata.
  - impl: Map canonical archive members to `index_path`, `.index_metadata.json`, `artifact-metadata.json`, and repo-scoped semantic/vector state under `index_location`.
  - impl: Keep backup behavior repo-scoped under `index_location`, not process cwd.
  - verify: `uv run pytest tests/test_artifact_download.py tests/test_artifact_freshness.py tests/test_artifact_recovery_selection.py -v --no-cov`

### SL-3 - Single-Repo Artifact CLI And Local Commit-Artifact Compatibility

- **Scope**: Update user-facing artifact CLI and local commit artifacts to use repo-scoped runtime paths while keeping legacy root files compatibility-only.
- **Owned files**: `mcp_server/cli/artifact_commands.py`, `mcp_server/artifacts/commit_artifacts.py`, `tests/test_artifact_commands.py`, `tests/test_artifact_lifecycle.py`
- **Interfaces provided**: artifact CLI flags for `--repository`, `--unsafe-allow-mismatched-artifact`, and repo-scoped restored-path reporting; `CommitArtifactManager` archives using `current.db` and P31 metadata; IF-0-P31-4 and IF-0-P31-5 CLI evidence
- **Interfaces consumed**: SL-2 downloader/hydration API; SL-0 metadata validation shape; P27 registered repository lookup and `repo.index_path`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Update pull/recover/sync tests so restored paths report `.mcp-index/current.db` and metadata under `.mcp-index`, not root-level `code_index.db`.
  - test: Add CLI unsafe flag coverage proving the flag is required for mismatched artifacts and the output includes the validation reasons.
  - test: Add `--repository` coverage where CLI resolves a registered repo and passes explicit repo path/index path to the downloader.
  - test: Update `_run_incremental_reconcile` coverage to open `SQLiteStore(repo.index_path)` when a repository context exists; keep root-level fallback only for legacy one-off local mode.
  - test: Update commit-artifact lifecycle tests so local commit artifacts include P31 metadata and extract to `.mcp-index/current.db`.
  - impl: Change restored path helpers and runtime notes to use `.mcp-index/current.db` as canonical.
  - impl: Route CLI download/recover/sync through SL-2 repo-scoped install APIs.
  - impl: Update `CommitArtifact.artifact_name` and metadata to include repo id, tracked branch, commit, schema version, semantic profile hash, and checksum.
  - verify: `uv run pytest tests/test_artifact_commands.py tests/test_artifact_lifecycle.py -v --no-cov`

### SL-4 - Multi-Repo Coordinator Without Chdir

- **Scope**: Remove process-wide directory switching from workspace artifact operations and make registry state reflect repo-scoped hydration.
- **Owned files**: `mcp_server/artifacts/multi_repo_artifact_coordinator.py`, `tests/test_multi_repo_artifact_coordinator.py`
- **Interfaces provided**: no `_pushd()`/`os.chdir()` usage; explicit uploader/downloader calls with `repo.path`, `repo.index_path`, and `repo.index_location`; registry updates for `last_published_commit`, `last_recovered_commit`, `artifact_backend`, `artifact_health`, and `available_semantic_profiles`; IF-0-P31-6 evidence
- **Interfaces consumed**: SL-1 uploader API; SL-2 downloader API; P27 `RepositoryInfo.tracked_branch`; `RepositoryRegistry.update_artifact_state()`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add a guard test that monkeypatches `os.chdir` to fail and proves `publish_workspace()` and `fetch_workspace()` do not call it.
  - test: Update fetch tests so restored local state is `.mcp-index/current.db`, and `artifact_health` becomes `ready` only after that file exists.
  - test: Update reconcile tests to consider `repo.index_path` and stop treating root-level `code_index.db` as ready unless explicitly in legacy mode.
  - test: Add wrong-repo and wrong-branch workspace fetch tests proving the coordinator records failure and does not update `last_recovered_commit`.
  - impl: Delete `_pushd()` and pass explicit paths into `IndexArtifactUploader` and `IndexArtifactDownloader`.
  - impl: Read semantic profile metadata from `repo.index_location / ".index_metadata.json"`.
  - impl: Record `artifact_health="local_only"` or `artifact_health="publish_failed"` when upload is disabled/unavailable after successful local archive preparation.
  - verify: `uv run pytest tests/test_multi_repo_artifact_coordinator.py -v --no-cov`

### SL-5 - Watcher And Reindex Publish Triggers

- **Scope**: Publish artifacts only after real successful indexed mutations and report local-only state when remote publication is not available.
- **Owned files**: `mcp_server/watcher_multi_repo.py`, `tests/test_watcher_multi_repo.py`
- **Interfaces provided**: successful-action predicate for `IndexSyncResult.action in {"full_index", "incremental_update"}`; no publish on `wrong_branch`, `up_to_date`, `downloaded`, or `failed`; registry artifact-state updates for local-only and publish-failed outcomes; IF-0-P31-7 evidence
- **Interfaces consumed**: P30 tracked-branch contract; P29 durable commit-advance contract; SL-1 `ArtifactPublisher.publish_on_reindex(repo_id, commit, tracked_branch=..., index_location=...)`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add watcher tests proving `full_index` and `incremental_update` publish exactly once after a successful commit sync.
  - test: Add negative tests proving `wrong_branch`, `up_to_date`, `downloaded`, and `failed` do not create local commit artifacts or call `ArtifactPublisher.publish_on_reindex()`.
  - test: Add local-only reporting coverage where `artifact_enabled=True` but no remote publisher is configured; assert the registry artifact state records prepared/local-only rather than implying upload success.
  - test: Add remote-publish failure coverage proving sync success is preserved, `artifact_health` records `publish_failed`, and the failure is logged.
  - impl: Replace the stale `result.action == "indexed"` predicate in `_sync_repository()`.
  - impl: Pass `result.commit` and repository tracked branch/index location to the publisher rather than trusting the git-monitor callback commit.
  - impl: Keep local commit artifact cleanup only after successful local artifact creation.
  - verify: `uv run pytest tests/test_watcher_multi_repo.py -v --no-cov`

### SL-6 - Provider Selection Fail-Safe

- **Scope**: Prevent runtime configuration from selecting unimplemented providers in production or auto routing.
- **Owned files**: `mcp_server/artifacts/provider_factory.py`, `mcp_server/artifacts/routing_policy.py`, `mcp_server/artifacts/providers/s3.py`, `tests/test_artifact_provider_factory.py`, `tests/test_artifact_routing_policy.py`
- **Interfaces provided**: deterministic configuration error for unimplemented `s3`, `gcs`, and `azure`; `auto` routes only to implemented providers; IF-0-P31-8 evidence
- **Interfaces consumed**: existing settings fields `artifact_provider`, `artifact_s3_bucket`, `artifact_routing_fallback_order`, and environment state from settings
- **Parallel-safe**: yes
- **Tasks**:
  - test: Change auto-routing tests so private/large artifacts fall back to `local_fs` or `github_actions` even when `artifact_s3_bucket` is present.
  - test: Add explicit `artifact_provider="s3"` coverage proving factory raises a clear "provider not implemented" configuration error.
  - test: Add fallback-order coverage proving unimplemented providers in the fallback list are skipped.
  - impl: Remove `s3` from `_SUPPORTED_PROVIDERS` for production selection or mark it as known-unimplemented and reject it before construction.
  - impl: Update `ArtifactRoutingPolicy` so `s3_configured=True` does not select S3 until the provider is implemented.
  - impl: Keep `S3ArtifactProvider` placeholder only as a non-selected implementation stub with a clear class docstring.
  - verify: `uv run pytest tests/test_artifact_provider_factory.py tests/test_artifact_routing_policy.py -v --no-cov`

### SL-7 - P31 Docs, Workflow, And Contract Audit

- **Scope**: Align active docs and workflows with the canonical P31 artifact contract after all implementation lanes land.
- **Owned files**: `.github/workflows/mcp-index.yml`, `.github/workflows/index-artifact-management.yml`, `docs/INDEX_MANIFEST_CONTRACT.md`, `docs/guides/artifact-persistence.md`
- **Interfaces provided**: documented artifact id/manifest contract; workflow metadata generation using P31 fields; explicit legacy compatibility notes; P31 exit-criteria evidence for P33
- **Interfaces consumed**: SL-0 manifest fields; SL-1 canonical archive/upload shape; SL-2 fail-closed download semantics; SL-3 CLI behavior; SL-4 no-chdir workspace behavior; SL-5 publish trigger behavior; SL-6 provider safety behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Run all targeted P31 tests after implementation lanes land.
  - verify: `uv run pytest tests/test_artifact_manifest_v2.py tests/test_artifact_integrity_gate.py tests/test_artifact_upload.py tests/test_artifact_download.py tests/test_artifact_freshness.py tests/test_artifact_recovery_selection.py tests/test_artifact_commands.py tests/test_artifact_lifecycle.py tests/test_multi_repo_artifact_coordinator.py tests/test_watcher_multi_repo.py tests/test_artifact_provider_factory.py tests/test_artifact_routing_policy.py -v --no-cov`
  - verify: `uv run pytest tests/test_artifact_publish_rollback.py tests/test_artifact_auto_delta.py tests/test_artifact_publish_race.py tests/security/test_artifact_attestation.py -v --no-cov`
  - verify: `rg -n "code_index\\.db|index-latest|mcp-index-|os\\.chdir|_pushd|STALE_COMMIT.*proceeding|STALE_AGE.*proceeding|NotImplementedError\\(\"S3" mcp_server/artifacts mcp_server/cli mcp_server/watcher_multi_repo.py tests docs .github/workflows`
  - impl: Update workflows to generate artifact names and `artifact-metadata.json` with repo id, tracked branch, commit, schema version, semantic profile hash, checksum, and manifest v2 payload.
  - impl: Update docs to state `.mcp-index/current.db` is canonical and root-level `code_index.db` is legacy compatibility only.
  - impl: Update docs to state S3/GCS/Azure providers are not production-selectable until implemented.
  - impl: Review grep results and either remove stale claims or record compatibility-only exceptions in docs.

## Verification

Required P31 targeted checks:

```bash
uv run pytest tests/test_artifact_manifest_v2.py tests/test_artifact_integrity_gate.py -v --no-cov
uv run pytest tests/test_artifact_upload.py tests/test_artifact_download.py tests/test_artifact_freshness.py tests/test_artifact_recovery_selection.py -v --no-cov
uv run pytest tests/test_artifact_commands.py tests/test_artifact_lifecycle.py tests/test_multi_repo_artifact_coordinator.py -v --no-cov
uv run pytest tests/test_watcher_multi_repo.py tests/test_artifact_provider_factory.py tests/test_artifact_routing_policy.py -v --no-cov
```

Publisher, delta, and attestation compatibility checks:

```bash
uv run pytest tests/test_artifact_publish_rollback.py tests/test_artifact_auto_delta.py tests/test_artifact_publish_race.py tests/security/test_artifact_attestation.py -v --no-cov
```

Contract searches:

```bash
rg -n "code_index\\.db|index-latest|mcp-index-|os\\.chdir|_pushd|STALE_COMMIT.*proceeding|STALE_AGE.*proceeding|NotImplementedError\\(\"S3" \
  mcp_server/artifacts mcp_server/cli mcp_server/watcher_multi_repo.py tests docs .github/workflows

rg -n "repo_id|tracked_branch|semantic_profile_hash|current\\.db|allow_unsafe|unsafe-allow-mismatched-artifact" \
  mcp_server/artifacts mcp_server/cli tests docs .github/workflows
```

Whole-phase optional regression:

```bash
make test
```

## Acceptance Criteria

- [ ] Artifact names, metadata, and manifest v2 payloads include `repo_id`, `tracked_branch`, `commit`, `schema_version`, `semantic_profile_hash`, checksum, and artifact type.
- [ ] Legacy `index-latest`, `index-*`, `mcp-index-*`, and root-level `code_index.db` conventions are compatibility-only and cannot bypass P31 metadata validation.
- [ ] Downloads reject wrong repo, wrong branch, unknown schema, stale commit, invalid metadata, missing checksum, checksum mismatch, and semantic profile mismatch before extraction/install by default.
- [ ] Unsafe install requires an explicit override and reports the rejected validation reasons.
- [ ] Hydration writes lexical state to `.mcp-index/current.db` and metadata/vector state under the registered repository's `.mcp-index` directory.
- [ ] Multi-repo artifact coordination performs no process-wide `chdir()`.
- [ ] Watcher/reindex artifact publication triggers only for successful mutating sync actions and never for wrong-branch, failed, up-to-date, or already-downloaded states.
- [ ] Local-only and remote-publish-failed artifact states are visible in repository artifact health.
- [ ] Production provider selection cannot route to unimplemented S3/GCS/Azure behavior.
- [ ] Active docs and workflows describe the canonical P31 artifact contract and the remaining legacy compatibility paths truthfully.
