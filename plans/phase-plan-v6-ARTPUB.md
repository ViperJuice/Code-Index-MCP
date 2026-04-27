---
phase_loop_plan_version: 1
phase: ARTPUB
roadmap: specs/phase-plans-v6.md
roadmap_sha256: 032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77
---
# ARTPUB: Remote Artifact Publish Durability

## Context

ARTPUB is the first phase in the v6 multi-repo hardening roadmap and is the
contract freeze for remote artifact publication before CIFLOW and MRE2E build
on it. The selected roadmap `specs/phase-plans-v6.md` is already staged in this
worktree as a new user-owned artifact, and its current hash matches the
required `032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77`.

Current repo state shows why this phase is needed:

- `mcp_server/artifacts/publisher.py` already computes the archive, checksum,
  attestation, and metadata inputs inside `publish_on_reindex()`, then creates
  a SHA-keyed release and moves `index-latest`, but it never calls the direct
  upload helper that would actually attach durable assets to that SHA release.
- `mcp_server/artifacts/artifact_upload.py` has `upload_direct()`, but that
  path currently writes `artifact-metadata.json` into the cwd, uploads only the
  archive plus metadata, and targets `logical_artifact_id` rather than the
  SHA-keyed tag that `ArtifactPublisher` returns and `index-latest` is supposed
  to summarize.
- `mcp_server/artifacts/artifact_download.py` still enumerates and downloads
  GitHub Actions artifacts via `/actions/artifacts/{id}/zip`, so the direct
  publish release path is not yet a validated input for restore or integrity
  checks.
- `docs/guides/artifact-persistence.md` still describes GitHub artifact
  snapshots as the remote transport, while
  `docs/INDEX_MANIFEST_CONTRACT.md` already freezes the metadata fields the
  release-backed direct publish path must persist.
- `mcp_server/watcher_multi_repo.py` already calls
  `ArtifactPublisher.publish_on_reindex()` after successful sync, so ARTPUB
  must harden that publisher surface without widening watcher scope.

## Interface Freeze Gates

- [ ] IF-0-ARTPUB-1 - SHA release asset contract:
      `ArtifactPublisher.publish_on_reindex()` persists a durable asset set on
      the SHA-keyed release consisting of the compressed archive,
      `artifact-metadata.json`, checksum sidecar material, and attestation
      sidecar material when attestation is available.
- [ ] IF-0-ARTPUB-2 - Latest pointer promotion contract:
      `index-latest` is created or moved only after the SHA-keyed release has
      the required assets and those assets match the metadata/checksum contract;
      same-commit republishes remain idempotent.
- [ ] IF-0-ARTPUB-3 - Direct publish restore contract:
      download validation can consume an artifact produced by the direct publish
      release path using the same fail-closed metadata, checksum, schema,
      branch, commit, and semantic-profile checks as existing restore flows.
- [ ] IF-0-ARTPUB-4 - Artifact contract documentation:
      `docs/INDEX_MANIFEST_CONTRACT.md` and
      `docs/guides/artifact-persistence.md` describe the direct publish asset
      set, GitHub Releases pointer semantics, and remaining local-only or
      GitHub Actions distinctions without implying unsupported providers or
      topology changes.

## Lane Index & Dependencies

- SL-0 - ARTPUB contract freeze and publish-race assertions; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Direct publish asset bundle and metadata persistence; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: yes
- SL-2 - SHA release orchestration and latest-pointer gating; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Direct publish download validation; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: yes
- SL-4 - Manifest and persistence docs reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: ARTPUB acceptance; Parallel-safe: no

## Lanes

### SL-0 - ARTPUB Contract Freeze And Publish-Race Assertions

- **Scope**: Freeze the required ARTPUB behavior in tests before changing the
  uploader, publisher, or restore flow.
- **Owned files**: `tests/test_artifact_publish_race.py`, `tests/test_artifact_publish_rollback.py`, `tests/test_artifact_auto_delta.py`, `tests/security/test_artifact_attestation.py`
- **Interfaces provided**: IF-0-ARTPUB-1, IF-0-ARTPUB-2
- **Interfaces consumed**: `mcp_server/artifacts/publisher.py`, `mcp_server/artifacts/artifact_upload.py`, `mcp_server/artifacts/artifact_download.py`, `docs/INDEX_MANIFEST_CONTRACT.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend the publisher race and rollback tests so they assert archive,
    metadata, checksum, and attestation asset upload behavior, not only
    `gh release create` and `gh release edit` ordering.
  - test: Freeze the failure contract so missing asset upload, asset
    verification failure, or latest-pointer promotion failure never leaves
    `index-latest` advanced to an incomplete SHA release.
  - test: Tighten the delta-policy and attestation tests so ARTPUB keeps
    passing through `artifact_type`, `delta_from`, and `attestation_url` while
    persisting the corresponding release assets.
  - impl: Keep this lane test-only; it defines the execution contract for SL-1
    through SL-3 and should not mutate runtime behavior outside the owned test
    files.
  - verify: `uv run pytest tests/test_artifact_publish_race.py tests/test_artifact_publish_rollback.py tests/test_artifact_auto_delta.py tests/security/test_artifact_attestation.py -q --no-cov`

### SL-1 - Direct Publish Asset Bundle And Metadata Persistence

- **Scope**: Make the direct upload helper persist the ARTPUB asset set in a
  deterministic, reusable way for publisher-driven SHA releases.
- **Owned files**: `mcp_server/artifacts/artifact_upload.py`, `tests/test_artifact_upload.py`
- **Interfaces provided**: IF-0-ARTPUB-1 asset packaging and upload helper
  contract; deterministic asset names for SL-2 and SL-3
- **Interfaces consumed**: SL-0 ARTPUB assertions; `docs/INDEX_MANIFEST_CONTRACT.md`; `mcp_server/artifacts/attestation.py`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add or update upload tests so `create_metadata()` persistence covers
    the P31 identity fields plus durable sidecar expectations for checksum and
    optional attestation material.
  - impl: Refactor `upload_direct()` into a helper that can materialize
    `artifact-metadata.json`, checksum material, and the attestation sidecar in
    a controlled temp location instead of the repo cwd.
  - impl: Let the direct upload path target an explicit release tag so the same
    helper can upload to the SHA-keyed release that `publish_on_reindex()`
    manages, while preserving `--clobber` idempotency.
  - impl: Upload the archive, `artifact-metadata.json`, checksum asset, and
    attestation sidecar when present; keep metadata generation compatible with
    existing manifest v2, semantic-profile, and delta-policy fields.
  - verify: `uv run pytest tests/test_artifact_upload.py -q --no-cov`
  - verify: `rg -n "artifact-metadata\\.json|checksum|attestation|logical_artifact_id|tracked_branch|manifest_v2" mcp_server/artifacts/artifact_upload.py tests/test_artifact_upload.py`

### SL-2 - SHA Release Orchestration And Latest-Pointer Gating

- **Scope**: Wire `ArtifactPublisher` so SHA-keyed releases become durable
  before `index-latest` promotion and rollback remains atomic on failure.
- **Owned files**: `mcp_server/artifacts/publisher.py`
- **Interfaces provided**: IF-0-ARTPUB-1, IF-0-ARTPUB-2
- **Interfaces consumed**: SL-0 ARTPUB assertions; SL-1 direct-upload helper
  and asset names; `mcp_server/watcher_multi_repo.py` publish caller contract
- **Parallel-safe**: no
- **Tasks**:
  - test: Use the frozen publisher tests first so this lane only repairs the
    runtime orchestration required by ARTPUB.
  - impl: Call the SL-1 upload helper from `publish_on_reindex()` after the
    SHA release exists and before `index-latest` is created or moved.
  - impl: Verify the SHA release has the required assets before promoting
    `index-latest`, and keep same-commit and concurrent-commit behavior
    idempotent.
  - impl: Preserve the current rollback guarantee: if asset upload,
    verification, or pointer movement fails after SHA release creation, delete
    the partial SHA release and surface `ArtifactError` instead of silently
    advancing remote state.
  - verify: `uv run pytest tests/test_artifact_publish_race.py tests/test_artifact_publish_rollback.py tests/test_artifact_auto_delta.py tests/security/test_artifact_attestation.py -q --no-cov`
  - verify: `rg -n "publish_on_reindex|index-latest|release upload|release delete|attest|create_metadata" mcp_server/artifacts/publisher.py`

### SL-3 - Direct Publish Download Validation

- **Scope**: Teach the restore path to validate artifacts produced by the
  direct publish release flow without weakening fail-closed download behavior.
- **Owned files**: `mcp_server/artifacts/artifact_download.py`, `tests/test_artifact_download.py`
- **Interfaces provided**: IF-0-ARTPUB-3
- **Interfaces consumed**: SL-0 ARTPUB assertions; SL-1 deterministic asset
  names and metadata sidecars; SL-2 SHA release and `index-latest` contract
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add download coverage for a direct-publish release payload so ARTPUB
    proves restore validation can consume the release-backed archive,
    metadata, checksum, and optional attestation sidecar.
  - impl: Extend the downloader with a release-asset retrieval path or shared
    extraction helper that can read the direct publish output while preserving
    current fail-closed validation semantics.
  - impl: Keep Actions-artifact restore compatibility intact; ARTPUB should add
    direct publish validation, not replace the older path before CIFLOW.
  - impl: Fail closed when direct publish assets are missing, mismatched, or
    stale unless the existing unsafe override is explicitly used.
  - verify: `uv run pytest tests/test_artifact_download.py -q --no-cov`
  - verify: `rg -n "actions/artifacts|release|artifact-metadata\\.json|checksum|attestation|allow_unsafe" mcp_server/artifacts/artifact_download.py tests/test_artifact_download.py`

### SL-4 - Manifest And Persistence Docs Reducer

- **Scope**: Reduce the hardened runtime behavior into accurate artifact
  contract and operator guidance.
- **Owned files**: `docs/INDEX_MANIFEST_CONTRACT.md`, `docs/guides/artifact-persistence.md`
- **Interfaces provided**: IF-0-ARTPUB-4
- **Interfaces consumed**: SL-1 persisted asset contract; SL-2 latest-pointer
  promotion semantics; SL-3 restore validation behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Update docs only after the runtime contract is frozen so the docs
    describe the implemented direct publish asset set, not an intended future
    shape.
  - impl: Clarify that ARTPUB direct publish uses GitHub Releases assets with a
    SHA-keyed release plus `index-latest` pointer, while CI upload parity
    remains a separate CIFLOW concern.
  - impl: Document the required durable assets, identity fields, checksum and
    attestation behavior, and the still-supported local-only fallback path.
  - impl: Remove or narrow any language that still implies GitHub Actions
    artifact ZIPs are the only remote transport for runtime direct publish.
  - verify: `rg -n "GitHub Releases|GitHub Actions|index-latest|artifact-metadata\\.json|checksum|attestation|direct publish|local-only" docs/INDEX_MANIFEST_CONTRACT.md docs/guides/artifact-persistence.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual ARTPUB execution.

Lane-specific contract checks:

```bash
uv run pytest tests/test_artifact_publish_race.py tests/test_artifact_publish_rollback.py tests/test_artifact_auto_delta.py tests/security/test_artifact_attestation.py -q --no-cov
uv run pytest tests/test_artifact_upload.py tests/test_artifact_download.py -q --no-cov
rg -n "publish_on_reindex|upload_direct|artifact-metadata\\.json|checksum|attestation|index-latest|actions/artifacts|release upload" \
  mcp_server/artifacts/publisher.py \
  mcp_server/artifacts/artifact_upload.py \
  mcp_server/artifacts/artifact_download.py \
  docs/INDEX_MANIFEST_CONTRACT.md \
  docs/guides/artifact-persistence.md
```

Whole-phase regression commands:

```bash
uv run pytest tests/test_artifact_publish_race.py tests/test_artifact_publish_rollback.py tests/test_artifact_auto_delta.py tests/test_artifact_upload.py tests/test_artifact_download.py tests/security/test_artifact_attestation.py -q --no-cov
make test
git status --short --branch
```

## Acceptance Criteria

- [ ] The SHA-keyed release produced by `publish_on_reindex()` contains the
      compressed archive, `artifact-metadata.json`, checksum material, and
      attestation material when attestation is available.
- [ ] Metadata generated by `create_metadata()` is persisted durably and
      remains aligned with the P31 artifact identity contract.
- [ ] `index-latest` is created or moved only after the SHA-keyed release has
      the required assets and those assets validate successfully.
- [ ] Repeated publish calls for the same repo, tracked branch, and commit
      remain idempotent.
- [ ] Race and rollback tests assert release asset upload behavior rather than
      only release create/edit ordering.
- [ ] Download validation can consume an artifact produced by the direct
      publish path without weakening fail-closed identity, checksum, schema, or
      freshness checks.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v6-ARTPUB.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v6-ARTPUB.md
  artifact_state: staged
```
