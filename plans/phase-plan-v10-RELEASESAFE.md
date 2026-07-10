---
phase_loop_plan_version: 1
phase: RELEASESAFE
roadmap: specs/phase-plans-v10.md
roadmap_sha256: 7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e
---

# RELEASESAFE: Release And Supply-Chain Safety

## Context
Prepare the repository-owned `1.3.1` bug-fix surface without dispatching a release. At entry, `release-automation.yml` builds and publishes containers, creates a tag/GitHub release, and publishes to PyPI before its later release-PR job; every external workflow action is tag-pinned rather than commit-pinned, including `aquasecurity/trivy-action@master`; package/runtime/docs still report `1.3.0`. Read-only collision probes found no remote `v1.3.1` tag, no GitHub `v1.3.1` release, and no PyPI `index-it-mcp==1.3.1` artifact.

## Interface Freeze Gates
- [ ] IF-0-RELEASESAFE-1 — Prepare mode may create/update a release PR and optionally request auto-merge, but never tags or publishes; publish mode checks out protected `main` with full history and repeats an exact `git merge-base --is-ancestor` proof plus version proof immediately before every tag, release, container, attestation, or PyPI mutation.
- [ ] IF-0-RELEASESAFE-2 — Every non-local `uses:` reference in `.github/workflows/**` is a 40-hex commit SHA with an adjacent update comment, and package metadata, runtime metadata, active docs, installers, changelog, lock metadata, and release tests agree on `1.3.1` / `v1.3.1`.

## Lane Index & Dependencies
SL-0 — Release workflow topology
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3, SL-4
  Parallel-safe: no

SL-1 — Immutable action audit
  Depends on: SL-0
  Blocks: SL-3, SL-4
  Parallel-safe: no

SL-2 — Version and package preparation
  Depends on: SL-0
  Blocks: SL-3, SL-4
  Parallel-safe: no

SL-3 — Package and workflow reducer
  Depends on: SL-0, SL-1, SL-2
  Blocks: SL-4
  Parallel-safe: no

SL-4 — Documentation sweep and release closeout
  Depends on: SL-0, SL-1, SL-2, SL-3
  Blocks: (none)
  Parallel-safe: no

## Lanes

### SL-0 — Release workflow topology
- **Scope**: Split preparation from publication in the existing manual workflow and make every external mutation contingent on same-job protected-main ancestry and exact-version proofs.
- **Owned files**: `.github/workflows/release-automation.yml`, `tests/test_workflow_release_policy.py`
- **Interfaces provided**: `IF-0-RELEASESAFE-1`, workflow modes `prepare` and `publish`, reusable protected-main guard step contract
- **Interfaces consumed**: `IF-0-QUALITY-1` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a structured YAML policy test reproducing publish-before-merge, shallow checkout, preparation-side mutations, missing guard adjacency, and `auto_merge=false` fallthrough at the entry commit.
  - impl: Keep one manual workflow with explicit `prepare`/`publish` modes; move release PR creation/optional auto-merge into prepare and terminate that path before mutation; make publish run only from full-history protected `main`, bind every artifact to the proven commit/version, and repeat guards immediately before each external mutation.
  - verify: Run `uv run --python 3.12 pytest tests/test_workflow_release_policy.py -q --no-cov` and inspect the parsed job DAG for prepare-to-publish dependencies.

### SL-1 — Immutable action audit
- **Scope**: Pin every external workflow action to its current immutable commit without adding hosted jobs or trigger expansion.
- **Owned files**: `.github/workflows/ci-cd-pipeline.yml`, `.github/workflows/container-registry.yml`, `.github/workflows/index-artifact-management.yml`, `.github/workflows/index-management.yml`, `.github/workflows/lockfile-check.yml`, `.github/workflows/maintenance.yml`, `.github/workflows/mcp-index.yml`, `tests/test_workflow_action_pins.py`
- **Interfaces provided**: `IF-0-RELEASESAFE-2-ACTION-PINS`
- **Interfaces consumed**: `IF-0-RELEASESAFE-1`
- **Parallel-safe**: no
- **Tasks**:
  - test: Parse every workflow with `yaml.BaseLoader`; reject non-local action refs that are not exactly 40 lowercase hex characters, missing update comments, mutable Trivy refs, and any trigger/job-count expansion.
  - impl: Resolve each currently selected action tag against its upstream repository, pin the exact commit with a readable version comment, and leave local actions/ordinary shell commands unchanged.
  - verify: Run `uv run --python 3.12 pytest tests/test_workflow_action_pins.py tests/test_localci_workflow_posture.py -q --no-cov` and compare workflow job/trigger census to entry.

### SL-2 — Version and package preparation
- **Scope**: Advance the active package/runtime/install/documentation surface to one coherent, unpublished `1.3.1` bug-fix release candidate.
- **Owned files**: `pyproject.toml`, `uv.lock`, `mcp_server/__init__.py`, `tests/test_release_metadata.py`
- **Interfaces provided**: `IF-0-RELEASESAFE-2-VERSION`
- **Interfaces consumed**: `IF-0-RELEASESAFE-1`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update release metadata assertions to distinguish the prepared repo-owned `1.3.1` surface from live publication and retain historical `1.3.0` evidence where explicitly historical.
  - impl: Bump project/runtime/lock metadata to `1.3.1` without claiming a tag, GitHub release, container push, or PyPI publication.
  - verify: Run `uv lock --locked`, `tests/test_release_metadata.py`, and `uv build`; inspect wheel and sdist names for `1.3.1`.

### SL-3 — Package and workflow reducer
- **Scope**: Reconcile workflow, pin, version, and package outputs before documentation is updated, without dispatching external mutations.
- **Owned files**: `tests/smoke/test_release_smoke_contract.py`
- **Interfaces provided**: `IF-0-RELEASESAFE-2-PACKAGE`
- **Interfaces consumed**: `IF-0-RELEASESAFE-1`, `IF-0-RELEASESAFE-2-ACTION-PINS`, `IF-0-RELEASESAFE-2-VERSION`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update shared release-smoke assertions only where immutable refs or prepare/publish topology changed, preserving image/distribution identity checks.
  - impl: Make no production change unless reducer testing finds a contract mismatch; route any mismatch to its owning lane.
  - verify: Run focused workflow/version tests, `make release-smoke`, and verify no local or remote `v1.3.1` tag/release/package artifact was created by this phase.

### SL-4 — Documentation sweep and release closeout
- **Scope**: Align active documentation, installers, and release evidence with the prepared `1.3.1` contract while preserving explicitly historical `1.3.0` records.
- **Owned files**: `README.md`, `CHANGELOG.md`, `scripts/install-mcp-docker.sh`, `scripts/install-mcp-docker.ps1`, `docs/DOCKER_GUIDE.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`, `docs/SUPPORT_MATRIX.md`, `docs/api/API-REFERENCE.md`, `docs/operations/deployment-runbook.md`, `docs/operations/user-action-runbook.md`, `tests/docs/test_gabase_ga_readiness_contract.py`, `tests/docs/test_gaclose_evidence_closeout.py`, `tests/docs/test_gaops_operations_contract.py`, `tests/docs/test_garc_rc_soak_contract.py`, `tests/docs/test_garecut_rc_recut_contract.py`, `tests/docs/test_garel_ga_release_contract.py`, `tests/docs/test_p23_doc_truth.py`, `tests/docs/test_p34_public_alpha_recut.py`, `tests/docs/test_pubname_public_docs.py`, `tests/smoke/test_mcpbase_stdio_smoke.py`, `tests/smoke/test_mcpeval_sdk_surface.py`
- **Interfaces provided**: `IF-0-RELEASESAFE-2`
- **Interfaces consumed**: `IF-0-RELEASESAFE-1`, `IF-0-RELEASESAFE-2-ACTION-PINS`, `IF-0-RELEASESAFE-2-VERSION`, `IF-0-RELEASESAFE-2-PACKAGE`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update active documentation assertions for `1.3.1` while retaining historical `1.3.0` evidence where tests explicitly freeze prior releases.
  - docs: Bump active image/install examples and changelog to `1.3.1`; describe the hardening fixes accurately and label the release candidate unpublished.
  - verify: Run the owned documentation/smoke tests, `make alpha-release-gates`, `git diff --check`, and read-only collision probes.

## Verification
- `uv sync --locked --extra dev --link-mode=copy`.
- `uv run --python 3.12 pytest tests/test_workflow_release_policy.py tests/test_workflow_action_pins.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py tests/test_localci_workflow_posture.py -q --no-cov`.
- `uv lock --locked` and `uv build`.
- `make release-smoke`.
- `make alpha-release-gates`.
- `git diff --check` and `git status --short`.
- Read-only remote collision probes for `v1.3.1`; no workflow dispatch, tag, release, container push, attestation, or package upload.

## Execution Notes
- This phase prepares release-owned files only. It must not dispatch a workflow, push a branch, create a tag or release, upload a container or attestation, or publish a package.
- Resolve action tags through each action's upstream Git repository and record the selected version beside the immutable SHA.
- Preserve `1.3.0` where a document or test is explicitly historical evidence; advance active instructions and current metadata only.
- Route any reducer mismatch back to the lane that owns the failing contract instead of weakening the reducer assertion.
- The terminal documentation sweep runs after package construction so its claims can be checked against real local artifacts.

## Acceptance Criteria
- [ ] Prepare mode creates or updates a release PR, honors `auto_merge`, and has no path to tag/publish jobs.
- [ ] Publish mode fails unless its exact target commit is on protected `main`, uses full history, repeats ancestry/version guards immediately before every mutation, and publishes only artifacts built from that proven commit.
- [ ] `tests/test_workflow_action_pins.py` proves all external workflow actions use immutable 40-hex refs with update comments, Trivy is no longer mutable, and hosted PR compute is unchanged.
- [ ] `1.3.1` is coherent across package, runtime, lock, active docs/installers, changelog, workflow defaults, and tests while remaining explicitly unpublished.
- [ ] The focused workflow/version pytest command, `make release-smoke`, and `make alpha-release-gates` pass without external dispatch.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `.github/workflows/**`, `pyproject.toml`, `uv.lock`, `mcp_server/__init__.py`, `README.md`, `CHANGELOG.md`, active install and release documentation
- evidence paths: workflow policy test output, package artifact names, local release-smoke output, alpha release-gate output
- redaction posture: `metadata_only`
- downstream handling: `none`
