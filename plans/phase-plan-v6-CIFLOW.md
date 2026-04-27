---
phase_loop_plan_version: 1
phase: CIFLOW
roadmap: specs/phase-plans-v6.md
roadmap_sha256: 032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77
---
# CIFLOW: CI Artifact Workflow Parity

## Context

CIFLOW is the fourth phase in the v6 multi-repo hardening roadmap. It depends
on ARTPUB's release-asset contract and keeps the GitHub Actions and scripted
upload surfaces compatible with that runtime artifact shape without reopening
publisher orchestration.

Current repo state gathered during planning:

- `specs/phase-plans-v6.md` is tracked and its live SHA matches the required
  `032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77`.
- The checkout is on `main` and ahead of `origin/main` by three commits after
  ARTPUB, IDXSAFE, and WATCH landed; `plans/phase-plan-v6-CIFLOW.md` did not
  exist before this planning run.
- `.github/workflows/index-artifact-management.yml` still builds
  `artifact-metadata.json` inline inside the workflow, and the
  `.index_metadata.json` parsing block currently contains malformed embedded
  Python indentation in the metadata-present path.
- The reusable workflow still advertises legacy workflow-dispatch artifact
  management actions (`promote`, `cleanup`, `list`) plus a
  `publish_on_reindex` flag, even though the v6 roadmap exit criteria only
  require supported local-only, CI upload, and runtime publish-on-reindex
  paths to remain operator-visible.
- `.github/workflows/index-management.yml` still checks for root-level
  `code_index.db` and `.index_metadata.json`, then calls
  `scripts/index-artifact-upload.py --method direct`, so the push-trigger CI
  path is not yet clearly aligned with the repo-scoped `.mcp-index/` runtime
  layout or ARTPUB metadata contract.
- `scripts/index-artifact-upload.py` is only a thin wrapper over
  `mcp_server/artifacts/artifact_upload.py`, and `IndexArtifactUploader` already
  owns the canonical metadata-building logic (`create_metadata()` plus
  manifest-v2 population), making it the safest parity anchor for CIFLOW.
- `docs/guides/artifact-persistence.md` already distinguishes runtime direct
  publish, GitHub Actions artifacts, and local-only fallback, but
  `docs/operations/user-action-runbook.md` is still centered on older
  phase-specific artifact governance and does not yet explain the v6 operator
  split among local-only, CI, and publish-on-reindex flows.

## Interface Freeze Gates

- [ ] IF-0-CIFLOW-1 - Reusable workflow upload contract:
      `.github/workflows/index-artifact-management.yml` produces a valid
      archive plus `artifact-metadata.json` when `.index_metadata.json` is
      present, without broken shell or embedded Python syntax, and it preserves
      compatibility facts required by the ARTPUB/MRE2E contracts.
- [ ] IF-0-CIFLOW-2 - Supported workflow-dispatch contract:
      `workflow_dispatch.inputs.action` and any auxiliary inputs expose only
      maintained artifact-management actions with matching jobs and docs; stale
      or misleading legacy options are removed or explicitly narrowed.
- [ ] IF-0-CIFLOW-3 - Metadata parity contract:
      reusable workflow upload, push-trigger CI upload, and
      `IndexArtifactUploader.create_metadata()` emit compatible
      `artifact-metadata.json` fields for `repo_id`, `tracked_branch`, `commit`,
      `schema_version`, `semantic_profile_hash`, `artifact_type`, `checksum`,
      `compatibility`, and `manifest_v2`.
- [ ] IF-0-CIFLOW-4 - Operator path-selection contract:
      docs identify which path operators should use for local-only
      build/recovery, CI snapshot upload, and runtime publish-on-reindex
      without implying stable release dispatch or unsupported artifact
      management flows.

## Lane Index & Dependencies

- SL-0 - CIFLOW contract freeze tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Reusable workflow syntax and action-surface repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Push-trigger and packaged metadata parity; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Operator docs reducer; Depends on: SL-0, SL-1, SL-2; Blocks: CIFLOW acceptance; Parallel-safe: no

## Lanes

### SL-0 - CIFLOW Contract Freeze Tests

- **Scope**: Freeze the supported workflow action surface, metadata-present CI
  upload behavior, and parity expectations before changing workflow YAML or the
  packaged upload helper.
- **Owned files**: `tests/test_artifact_publish_race.py`, `tests/test_release_metadata.py`, `tests/test_artifact_upload.py`
- **Interfaces provided**: IF-0-CIFLOW-1, IF-0-CIFLOW-2, IF-0-CIFLOW-3
- **Interfaces consumed**: IF-0-ARTPUB-1; current `.github/workflows/index-artifact-management.yml`; current `.github/workflows/index-management.yml`; existing `IndexArtifactUploader.create_metadata()` manifest-v2 contract
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend the workflow-facing tests so the reusable upload path fails
    when `.index_metadata.json` is present but the embedded metadata-generation
    logic is syntactically invalid or omits required compatibility fields.
  - test: Freeze the supported workflow-dispatch action vocabulary so CIFLOW
    removes or narrows any stale artifact-management options instead of leaving
    them accidentally documented as supported.
  - test: Add metadata-parity assertions that compare the CI/upload surfaces to
    `IndexArtifactUploader.create_metadata()` for the core identity,
    compatibility, checksum, and `manifest_v2` fields that MRE2E will rely on.
  - impl: Keep this lane test-only; it defines the CIFLOW contract for SL-1
    through SL-3 without mutating workflow or runtime behavior directly.
  - verify: `uv run pytest tests/test_artifact_publish_race.py tests/test_release_metadata.py tests/test_artifact_upload.py -q --no-cov`

### SL-1 - Reusable Workflow Syntax And Action-Surface Repair

- **Scope**: Repair the reusable artifact-upload workflow so metadata-present
  uploads are syntactically valid and the dispatch surface reflects only
  supported artifact-management actions.
- **Owned files**: `.github/workflows/index-artifact-management.yml`
- **Interfaces provided**: IF-0-CIFLOW-1, IF-0-CIFLOW-2, reusable workflow asset-and-metadata contract for SL-2
- **Interfaces consumed**: SL-0 CIFLOW workflow assertions; IF-0-ARTPUB-1 durable asset vocabulary; current `artifact-metadata.json` compatibility requirements
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 workflow-focused tests first so this lane repairs the
    actual reusable-workflow contract rather than inventing a new YAML surface.
  - impl: Remove the malformed embedded metadata-generation block or reroute it
    through a packaged helper so the metadata-present upload path stays valid
    when `.index_metadata.json` exists.
  - impl: Keep the reusable workflow centered on repo-scoped `.mcp-index/`
    payloads and `artifact-metadata.json`, preserving the compatibility fields
    that ARTPUB and MRE2E expect.
  - impl: Reconcile `workflow_dispatch` actions and inputs with the maintained
    artifact-management surface; if legacy `promote`, `cleanup`, or `list`
    flows are no longer supported in the v6 model, remove or quarantine them
    instead of advertising them as first-class operator actions.
  - verify: `uv run pytest tests/test_artifact_publish_race.py tests/test_release_metadata.py -q --no-cov`
  - verify: `rg -n "workflow_dispatch|artifact-metadata\\.json|semantic_profiles|available_semantic_profiles|publish_on_reindex|promote|cleanup|list" .github/workflows/index-artifact-management.yml`

### SL-2 - Push-Trigger And Packaged Metadata Parity

- **Scope**: Align the push-trigger CI upload path and packaged upload helper
  with the reusable workflow and direct runtime metadata contract without
  changing ARTPUB's publish orchestration semantics.
- **Owned files**: `.github/workflows/index-management.yml`, `scripts/index-artifact-upload.py`, `mcp_server/artifacts/artifact_upload.py`
- **Interfaces provided**: IF-0-CIFLOW-3
- **Interfaces consumed**: SL-0 metadata-parity assertions; SL-1 reusable workflow contract; existing `IndexArtifactUploader.create_metadata()` and `upload_direct()` interfaces
- **Parallel-safe**: no
- **Tasks**:
  - test: Use the SL-0 parity assertions first so this lane only narrows the
    drift between CI metadata generation and the packaged runtime helper.
  - impl: Add or expose a small packaged helper/CLI path that materializes
    ARTPUB-compatible `artifact-metadata.json` from repo-scoped `.mcp-index/`
    inputs instead of duplicating metadata schema logic in workflow YAML.
  - impl: Update `scripts/index-artifact-upload.py` and
    `.github/workflows/index-management.yml` so the push-trigger CI path reads
    `.mcp-index/current.db` and `.mcp-index/.index_metadata.json` rather than
    relying on root-level `code_index.db` heuristics.
  - impl: Preserve direct runtime publish tag/pointer behavior; CIFLOW should
    align CI upload metadata and invocation surfaces, not rewrite ARTPUB's
    release orchestration.
  - verify: `uv run pytest tests/test_artifact_upload.py tests/test_release_metadata.py -q --no-cov`
  - verify: `python -m py_compile scripts/index-artifact-upload.py mcp_server/artifacts/artifact_upload.py`
  - verify: `rg -n "code_index\\.db|\\.mcp-index|create_metadata|upload_direct|--method direct|artifact-metadata\\.json" .github/workflows/index-management.yml scripts/index-artifact-upload.py mcp_server/artifacts/artifact_upload.py`

### SL-3 - Operator Docs Reducer

- **Scope**: Reduce the repaired workflow surfaces into accurate operator
  guidance for local-only, CI, and publish-on-reindex artifact handling.
- **Owned files**: `docs/guides/artifact-persistence.md`, `docs/operations/user-action-runbook.md`
- **Interfaces provided**: IF-0-CIFLOW-4
- **Interfaces consumed**: SL-1 supported workflow action surface; SL-2 metadata-parity and push-trigger behavior; roadmap CIFLOW exit criteria
- **Parallel-safe**: no
- **Tasks**:
  - test: Update docs only after SL-1 and SL-2 freeze the supported workflow
    and script surfaces.
  - impl: Document which path operators should use for local-only artifact
    build/recovery, reusable CI upload, and runtime publish-on-reindex.
  - impl: Remove or narrow stale references that imply unsupported manual
    artifact management flows remain part of the v6 operator contract.
  - impl: Keep the docs scoped to artifact workflow parity; do not widen this
    phase into release dispatch, remote provider expansion, or broader rollout
    readiness claims.
  - verify: `rg -n "local-only|GitHub Actions|publish_on_reindex|runtime direct publish|artifact push|promote|cleanup|list" docs/guides/artifact-persistence.md docs/operations/user-action-runbook.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual CIFLOW execution.

Lane-specific contract checks:

```bash
uv run pytest tests/test_artifact_publish_race.py tests/test_release_metadata.py tests/test_artifact_upload.py -q --no-cov
python -m py_compile scripts/index-artifact-upload.py mcp_server/artifacts/artifact_upload.py
rg -n "workflow_dispatch|artifact-metadata\\.json|semantic_profiles|available_semantic_profiles|publish_on_reindex|promote|cleanup|list|code_index\\.db|\\.mcp-index|create_metadata|upload_direct" \
  .github/workflows/index-artifact-management.yml \
  .github/workflows/index-management.yml \
  scripts/index-artifact-upload.py \
  mcp_server/artifacts/artifact_upload.py \
  docs/guides/artifact-persistence.md \
  docs/operations/user-action-runbook.md
```

Whole-phase regression commands:

```bash
uv run pytest tests/test_artifact_publish_race.py tests/test_release_metadata.py tests/test_artifact_upload.py -q --no-cov
make test
git status --short --branch
```

## Acceptance Criteria

- [ ] The reusable `index-artifact-management.yml` upload path has valid shell
      and Python syntax when `.index_metadata.json` is present.
- [ ] Workflow-dispatch inputs do not advertise unsupported artifact-management
      actions.
- [ ] Push-trigger upload, reusable workflow upload, and direct runtime publish
      produce compatible `artifact-metadata.json` fields for repo identity,
      branch, commit, schema, semantic-profile, checksum, compatibility, and
      manifest-v2 metadata.
- [ ] Workflow tests or syntax checks exercise the metadata-present upload path.
- [ ] Docs clearly name which path operators should use for local-only, CI, and
      publish-on-reindex workflows.
- [ ] CIFLOW stays scoped to workflow parity and does not rewrite ARTPUB
      runtime publish orchestration or broaden into release dispatch.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v6-CIFLOW.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v6-CIFLOW.md
  artifact_state: staged
```
