# P25: Blocking Release Gates & Automation

> Plan doc produced by `codex-plan-phase P25` against `specs/phase-plans-v2.md` on 2026-04-21.
> P25 consumes the P21-P24 release, smoke, documentation, and sandbox contracts and produces IF-0-P25-1 for P26 private-alpha evidence.

## Context

P25 turns the alpha release qualification story into enforceable automation. Earlier phases already created the required inputs:

- P21 freezes the `1.2.0-rc3` version contract in `mcp_server.__version__`, `pyproject.toml`, `README.md`, `CHANGELOG.md`, and `.github/workflows/release-automation.yml`.
- P21 also makes `pyproject.toml`/`uv.lock` the dependency source of truth and adds `tests/test_requirements_consolidation.py`.
- P22 adds `scripts/release_smoke.py`, `make release-smoke`, `make release-smoke-container`, and `tests/smoke/test_release_smoke_contract.py`.
- P23 adds documentation truth checks in `tests/docs/test_p23_doc_truth.py` and the canonical support matrix in `docs/SUPPORT_MATRIX.md`.
- P24 is expected to leave sandbox-default-on degradation visible through `list_plugins` and documented in `docs/security/sandbox.md` and `docs/operations/user-action-runbook.md`.

The current workflows have useful pieces but not a crisp alpha gate:

- `.github/workflows/ci-cd-pipeline.yml` has quality, Ubuntu tests, integration tests, release smoke, docs-adjacent checks, non-blocking cross-platform tests, non-blocking authenticated tests, non-blocking benchmarks, and a Docker job marked `continue-on-error: true`.
- `.github/workflows/container-registry.yml` builds production images and runs `make release-smoke-container` for `linux/amd64`, but image scanning and signing are separate from the alpha-required build/smoke gate.
- `.github/workflows/lockfile-check.yml` only runs on dependency-file path changes, so it is not currently an always-visible alpha qualification gate.
- `.github/workflows/release-automation.yml` mutates version files and creates a release branch before proving all P21-P24 contracts; release publication should be downstream of an explicit preflight gate.
- `docs/operations/deployment-runbook.md` describes staged rollout gates, but it does not yet map each required CI job to an operator decision.
- `docs/operations/user-action-runbook.md` documents attestation prerequisites from P15/P24, but P25 needs an explicit private-alpha fallback state for authenticated GitHub attestation tests.

P25 should keep slow/performance/cross-platform jobs visible and informational. It should make only the honest alpha blockers required: dependency sync, focused formatting/lint checks, unit/integration smoke, release smoke, Docker build/smoke, and docs truth checks.

## Interface Freeze Gates

- [ ] IF-0-P25-1 - Blocking release gate contract: the required alpha gate job names are stable and map directly to the release checklist. Required gates are `Alpha Gate - Dependency Sync`, `Alpha Gate - Format And Lint`, `Alpha Gate - Unit And Release Smoke`, `Alpha Gate - Integration Smoke`, `Alpha Gate - Docker Build And Smoke`, `Alpha Gate - Docs Truth`, and `Alpha Gate - Required Gates Passed`.
- [ ] IF-0-P25-2 - Informational job contract: non-blocking workflow jobs are named with an `Informational - ` prefix and are either `continue-on-error: true`, schedule/manual only, or omitted from the required-gate aggregator.
- [ ] IF-0-P25-3 - Release refusal contract: `.github/workflows/release-automation.yml` runs a preflight gate before version mutation, branch creation, artifact build, tag creation, GitHub release creation, PyPI publish, or container publish. Publication jobs depend on the gate and cannot run if P21-P24 contract checks fail.
- [ ] IF-0-P25-4 - Attestation prerequisite contract: authenticated GitHub attestation tests document the required `ATTESTATION_GH_TOKEN`/repository settings and have a private-alpha fallback state of informational `skipped` or `warn`, not a silent pass and not a contributor-PR blocker.
- [ ] IF-0-P25-5 - Release checklist mapping contract: `docs/operations/deployment-runbook.md` contains a table mapping every IF-0-P25-1 required job to the operator decision it supports, the command/workflow source, and the block/fallback behavior.

## Lane Index & Dependencies

- SL-0 - P25 contract tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4, SL-5, SL-6; Parallel-safe: yes
- SL-1 - Shared alpha gate commands; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4, SL-5, SL-6; Parallel-safe: no
- SL-2 - CI/CD required and informational gates; Depends on: SL-0, SL-1; Blocks: SL-5, SL-6, SL-7; Parallel-safe: yes
- SL-3 - Lockfile gate normalization; Depends on: SL-0, SL-1; Blocks: SL-5, SL-6, SL-7; Parallel-safe: yes
- SL-4 - Container alpha gate; Depends on: SL-0, SL-1; Blocks: SL-5, SL-6, SL-7; Parallel-safe: yes
- SL-5 - Release automation refusal gate; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4; Blocks: SL-6, SL-7; Parallel-safe: no
- SL-6 - Operator checklist and attestation docs; Depends on: SL-2, SL-3, SL-4, SL-5; Blocks: SL-7, P26; Parallel-safe: no
- SL-7 - Final P25 audit; Depends on: SL-5, SL-6; Blocks: P26; Parallel-safe: no

Lane DAG:

```text
SL-0
 └─> SL-1 ─┬─> SL-2 ─┐
           ├─> SL-3 ─┼─> SL-5 ─> SL-6 ─> SL-7
           └─> SL-4 ─┘
```

## Lanes

### SL-0 - P25 Contract Tests

- **Scope**: Add failing workflow and documentation tests that freeze required alpha gates, informational job naming, release refusal dependencies, attestation fallback wording, and checklist mapping.
- **Owned files**: `tests/test_p25_release_gates.py`, `tests/docs/test_p25_release_checklist.py`
- **Interfaces provided**: executable assertions for IF-0-P25-1, IF-0-P25-2, IF-0-P25-3, IF-0-P25-4, IF-0-P25-5
- **Interfaces consumed**: P21 tests in `tests/test_release_metadata.py` and `tests/test_requirements_consolidation.py`; P22 tests in `tests/smoke/test_release_smoke_contract.py`; P23 tests in `tests/docs/test_p23_doc_truth.py`; P24 status/docs contracts if present
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add YAML-based assertions that `.github/workflows/ci-cd-pipeline.yml`, `.github/workflows/lockfile-check.yml`, and `.github/workflows/container-registry.yml` expose the IF-0-P25-1 required job names.
  - test: Assert the required-gate aggregator job depends on all required CI jobs and has no `continue-on-error`.
  - test: Assert non-blocking jobs in the P25 workflow surfaces use the `Informational - ` name prefix and do not appear in the required-gate aggregator.
  - test: Assert `.github/workflows/release-automation.yml` has a preflight gate before `prepare-release`, and publish/tag jobs depend on the gate path.
  - test: Assert authenticated attestation tests mention `ATTESTATION_GH_TOKEN` and a documented private-alpha fallback state.
  - test: Assert `docs/operations/deployment-runbook.md` maps each required alpha gate to an operator decision.
  - verify: `uv run pytest tests/test_p25_release_gates.py tests/docs/test_p25_release_checklist.py -v --no-cov`

### SL-1 - Shared Alpha Gate Commands

- **Scope**: Add or normalize Makefile targets so workflows and release automation call the same alpha gate commands instead of duplicating shell fragments.
- **Owned files**: `Makefile`
- **Interfaces provided**: `make alpha-dependency-sync`, `make alpha-format-lint`, `make alpha-unit-release-smoke`, `make alpha-integration-smoke`, `make alpha-docs-truth`, `make alpha-release-gates`
- **Interfaces consumed**: `uv sync --locked`; `uv lock --locked`; `make release-smoke`; `make release-smoke-container`; P21-P23 test modules; existing lint tools declared in `pyproject.toml`
- **Parallel-safe**: no
- **Tasks**:
  - test: Use SL-0 workflow tests to fail until required jobs call stable Makefile targets where practical.
  - impl: Add focused alpha targets that avoid broad full-suite/performance checks while covering P25 blockers.
  - impl: Keep existing `lint`, `test`, `test-all`, `release-smoke`, and `release-smoke-container` behavior intact for local developers.
  - impl: Make `alpha-docs-truth` run the P23 docs truth tests and P25 checklist tests once they exist.
  - impl: Make `alpha-release-gates` compose the local non-container checks for release-automation preflight.
  - verify: `make -n alpha-dependency-sync alpha-format-lint alpha-unit-release-smoke alpha-integration-smoke alpha-docs-truth alpha-release-gates`

### SL-2 - CI/CD Required And Informational Gates

- **Scope**: Refactor the main CI workflow so required alpha jobs are blocking, named consistently, and summarized by a single required-gate aggregator while existing slow jobs stay visible as informational.
- **Owned files**: `.github/workflows/ci-cd-pipeline.yml`
- **Interfaces provided**: IF-0-P25-1 required CI jobs except the lockfile/container workflow portions; IF-0-P25-2 informational naming in the main CI workflow
- **Interfaces consumed**: SL-1 Makefile targets; P21-P24 contract tests; existing workflow env names `PYTHON_VERSION`, `DOCKER_IMAGE_REF`, and `MCP_SKIP_PLUGIN_PREINDEX`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 workflow assertions to fail on missing required job names, missing `needs`, or `continue-on-error` on required gates.
  - impl: Rename or split `quality-checks` into `Alpha Gate - Format And Lint` with no informational mypy/bandit ambiguity inside the blocking job.
  - impl: Rename or split Ubuntu tests into `Alpha Gate - Unit And Release Smoke`, keeping `make release-smoke` in the blocking path.
  - impl: Rename integration smoke into `Alpha Gate - Integration Smoke` and keep it blocking.
  - impl: Add `Alpha Gate - Docs Truth` running P21/P23/P25 docs and release metadata checks.
  - impl: Add `Alpha Gate - Required Gates Passed` with `needs` on all required main-CI gates and no `continue-on-error`.
  - impl: Rename cross-platform, extended, authenticated, benchmark, and broad security/performance jobs with `Informational - ` and keep their current opt-in/non-blocking posture.
  - verify: `uv run pytest tests/test_p25_release_gates.py -v --no-cov`

### SL-3 - Lockfile Gate Normalization

- **Scope**: Make lockfile verification an explicit alpha gate rather than a path-filtered helper that disappears from release qualification.
- **Owned files**: `.github/workflows/lockfile-check.yml`
- **Interfaces provided**: IF-0-P25-1 `Alpha Gate - Dependency Sync`
- **Interfaces consumed**: SL-1 `make alpha-dependency-sync`; P21 dependency source-of-truth contract; `uv lock --locked`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 workflow assertions to fail if the lockfile workflow lacks `Alpha Gate - Dependency Sync` or is only path-filtered.
  - impl: Ensure the workflow runs for pushes/PRs relevant to alpha release qualification, not only dependency-file changes.
  - impl: Name the job `Alpha Gate - Dependency Sync` and keep it blocking with no `continue-on-error`.
  - impl: Use `astral-sh/setup-uv` or the same install path as the other workflows, then call the SL-1 target.
  - verify: `uv run pytest tests/test_p25_release_gates.py -v --no-cov`

### SL-4 - Container Alpha Gate

- **Scope**: Make the production container build and smoke run an explicit blocking alpha gate while keeping scans, signing, cleanup, and multi-platform publication separate where they are not alpha blockers.
- **Owned files**: `.github/workflows/container-registry.yml`
- **Interfaces provided**: IF-0-P25-1 `Alpha Gate - Docker Build And Smoke`; IF-0-P25-2 informational container jobs
- **Interfaces consumed**: SL-1 `make release-smoke-container`; P22 image contract `ghcr.io/viperjuice/code-index-mcp`; `docker/dockerfiles/Dockerfile.production`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 workflow assertions to fail if `Alpha Gate - Docker Build And Smoke` is missing, has `continue-on-error`, or does not run `make release-smoke-container`.
  - impl: Rename or split the current `build-and-push` path so a no-push build/smoke job is the required alpha gate.
  - impl: Keep vulnerability scans, SBOM upload, manifest push, cleanup, and signing visible but informational unless they are part of the release-publish path.
  - impl: Avoid requiring live third-party credentials for contributor PRs; use `GITHUB_TOKEN` only where existing workflow permissions already allow it.
  - verify: `uv run pytest tests/test_p25_release_gates.py tests/smoke/test_release_smoke_contract.py -v --no-cov`

### SL-5 - Release Automation Refusal Gate

- **Scope**: Make release automation prove the P21-P24/P25 contracts before mutating release files, building artifacts, pushing tags, creating GitHub releases, publishing packages, or publishing images.
- **Owned files**: `.github/workflows/release-automation.yml`
- **Interfaces provided**: IF-0-P25-3 release refusal contract
- **Interfaces consumed**: SL-1 `make alpha-release-gates`; SL-2/SL-3/SL-4 required gate names; P21 version contract; P22 release smoke; P23 docs truth; P24 sandbox docs/status contract
- **Parallel-safe**: no
- **Tasks**:
  - test: Use SL-0 workflow assertions to fail until `prepare-release` depends on a preflight gate and all publish/tag jobs are downstream of it.
  - impl: Add `preflight-release-gates` before `prepare-release`, using a clean checkout and the SL-1 gate target.
  - impl: Add a release-version check that validates the workflow input against P21 release metadata before version files are edited.
  - impl: Ensure `build-artifacts`, Docker publish, `create-release`, PyPI publish, tag creation, auto-merge, post-release docs updates, and deployment triggers are downstream of the successful preflight/release test path.
  - impl: Keep authenticated attestation publication behavior documented, but do not require live third-party credentials for contributor PRs.
  - verify: `uv run pytest tests/test_p25_release_gates.py tests/test_release_metadata.py -v --no-cov`

### SL-6 - Operator Checklist And Attestation Docs

- **Scope**: Document the alpha gate checklist, operator decisions, and attestation fallback state after all workflow producer lanes define their final job names.
- **Owned files**: `docs/operations/deployment-runbook.md`, `docs/operations/user-action-runbook.md`, `CHANGELOG.md`
- **Interfaces provided**: IF-0-P25-4; IF-0-P25-5; P26 input describing the exact gates that block public alpha
- **Interfaces consumed**: SL-2 main CI required/informational job names; SL-3 dependency gate job name; SL-4 container gate job name; SL-5 release refusal path; P24 attestation and sandbox guidance
- **Parallel-safe**: no
- **Tasks**:
  - test: Use SL-0 docs tests to fail until each IF-0-P25-1 required gate appears in the checklist mapping table.
  - impl: Add a `Public Alpha Release Gate Checklist` section to `docs/operations/deployment-runbook.md` mapping job names to operator decisions, command/workflow source, and block/fallback behavior.
  - impl: Add P25 before/after operator actions to `docs/operations/user-action-runbook.md`, including the `ATTESTATION_GH_TOKEN` prerequisite and private-alpha fallback state.
  - impl: Record the P25 gate automation change under `CHANGELOG.md` `[Unreleased]` or the active `1.2.0-rc3` section according to the repository's current release-note convention at execution time.
  - verify: `uv run pytest tests/docs/test_p25_release_checklist.py tests/docs/test_p23_doc_truth.py -v --no-cov`

### SL-7 - Final P25 Audit

- **Scope**: Run the complete P25 regression set and verify that P25's blocking release gate contract is ready for P26 private-alpha evidence.
- **Owned files**: (none)
- **Interfaces provided**: final IF-0-P25-1 completion evidence for P26
- **Interfaces consumed**: IF-0-P25-1 through IF-0-P25-5 from SL-2 through SL-6
- **Parallel-safe**: no
- **Tasks**:
  - test: Run P25 workflow and docs contract tests after all producer lanes land.
  - verify: `uv run pytest tests/test_p25_release_gates.py tests/docs/test_p25_release_checklist.py -v --no-cov`
  - verify: `uv run pytest tests/smoke tests/docs tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov`
  - verify: `make -n alpha-release-gates release-smoke release-smoke-container`
  - verify: `rg -n "continue-on-error: true" .github/workflows/ci-cd-pipeline.yml .github/workflows/container-registry.yml .github/workflows/lockfile-check.yml .github/workflows/release-automation.yml`
  - verify: `rg -n "Alpha Gate -|Informational -" .github/workflows docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md`
  - impl: Record any intentionally informational residual jobs in the deployment runbook rather than silently leaving ambiguous job names.

## Verification

Required P25 checks:

```bash
uv run pytest tests/test_p25_release_gates.py tests/docs/test_p25_release_checklist.py -v --no-cov
uv run pytest tests/smoke tests/docs tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
make -n alpha-release-gates release-smoke release-smoke-container
rg -n "Alpha Gate -|Informational -" .github/workflows docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md
```

Whole-phase optional workflow checks:

```bash
gh workflow view "CI/CD Pipeline"
gh workflow view "Release Automation"
gh workflow view "Container Registry Management"
gh workflow view "lockfile-check"
```

## Acceptance Criteria

- [ ] Required alpha CI jobs are blocking and named exactly: `Alpha Gate - Dependency Sync`, `Alpha Gate - Format And Lint`, `Alpha Gate - Unit And Release Smoke`, `Alpha Gate - Integration Smoke`, `Alpha Gate - Docker Build And Smoke`, `Alpha Gate - Docs Truth`, and `Alpha Gate - Required Gates Passed`.
- [ ] Required gates have no `continue-on-error: true`, and the required-gate aggregator depends on every required main-CI gate it summarizes.
- [ ] Non-blocking jobs are explicitly named with `Informational - ` and cannot be confused with release qualification.
- [ ] Release automation refuses to mutate version files, create release branches, build/publish artifacts, push tags, create GitHub releases, publish to PyPI, or publish containers when P21-P25 contracts fail.
- [ ] Authenticated GitHub attestation tests document `ATTESTATION_GH_TOKEN` and repository settings prerequisites plus a clear private-alpha fallback of informational skipped/warn state.
- [ ] `docs/operations/deployment-runbook.md` maps each blocking job to an operator decision and block/fallback behavior.
- [ ] P25 verification commands pass locally or failures are recorded as explicit blockers before P26 starts.
