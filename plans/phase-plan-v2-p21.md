# P21: Release Contract & Dependency Unification

> Plan doc produced by `codex-plan-phase P21` against `specs/phase-plans-v2.md` on 2026-04-21.
> P20 was verified first with targeted P20 checks: `22 passed in 25.80s` for multi-repo, observability, metrics/redaction, async plugin factory, and the dispatcher sandbox regression test.

## Context

P20 is complete enough to plan P21: the multi-repo integration harness exists, observability smoke exists, `CapabilitySet.mem_mb` defaults to `2048`, the deployment runbook exists, and the targeted P20 verification command passed:

```bash
uv run pytest tests/integration/multi_repo tests/integration/obs tests/test_prometheus_exporter_http.py tests/test_secret_redaction.py tests/test_plugin_factory_async.py tests/test_dispatcher.py::TestEnhancedDispatcherProtocolConformance::test_get_plugins_for_file_accepts_ctx -v --no-cov
```

Current P21 drift is concrete:

- `mcp_server.__version__` is `1.2.0-rc2`, but `pyproject.toml` is still `1.1.0`.
- `README.md` status still advertises `1.0.0 (MVP, beta)`.
- `tests/test_release_metadata.py` only checks runtime version and local tag presence; it does not check package metadata, README, changelog, or workflow release inputs.
- Active workflows and Dockerfiles still reference removed `requirements*.txt` files via `pip install -r`, `COPY requirements*.txt`, and dependency cache keys.
- `tests/test_requirements_consolidation.py` checks that requirements files are absent, but not that active release paths stopped referencing them.

P21 should be small and mechanical. Since P20 already cut `v1.2.0-rc2`, this plan freezes the next pre-release contract as `1.2.0-rc3` / `v1.2.0-rc3`. P22 consumes this contract for wheel and container smoke; it should not need to rediscover version or dependency sources.

## Interface Freeze Gates

- [ ] IF-0-P21-1 — Version source-of-truth contract: `tests/test_release_metadata.py` defines `EXPECTED_VERSION = "1.2.0-rc3"` and `EXPECTED_TAG = "v1.2.0-rc3"` and verifies all of the following exact surfaces agree: `mcp_server.__version__`, `pyproject.toml` `[project].version`, `README.md` project status version text, `CHANGELOG.md` section `## [1.2.0-rc3]`, `.github/workflows/release-automation.yml` workflow-dispatch version example/default text, release notes body text, and the local tag lookup.
- [ ] IF-0-P21-2 — Dependency source-of-truth contract: `pyproject.toml` and `uv.lock` are the only active first-party dependency inputs. Active workflows under `.github/workflows/` and Dockerfiles under `docker/dockerfiles/` must not reference `requirements.txt`, `requirements-production.txt`, `requirements-semantic.txt`, `requirements*.txt`, `pip install -r`, or `hashFiles('**/requirements*.txt')`; install commands use `uv sync --locked` or `uv pip install` from the project/lockfile instead.

## Lane Index & Dependencies

- SL-0 — Contract tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: yes
- SL-1 — Version metadata files; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-2 — Release workflow contract; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-3 — CI dependency unification; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-4 — Docker dependency unification; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-5 — Final P21 audit; Depends on: SL-1, SL-2, SL-3, SL-4; Blocks: (none); Parallel-safe: no

Lane DAG:

```text
SL-0
 ├─> SL-1
 ├─> SL-2
 ├─> SL-3
 └─> SL-4
      SL-1, SL-2, SL-3, SL-4 ─> SL-5
```

## Lanes

### SL-0 — Contract Tests

- **Scope**: Strengthen release metadata and dependency-consolidation tests so P21 has executable contracts before implementation.
- **Owned files**: `tests/test_release_metadata.py`, `tests/test_requirements_consolidation.py`
- **Interfaces provided**: IF-0-P21-1 assertions, IF-0-P21-2 assertions
- **Interfaces consumed**: pre-existing `tomllib`/`tomli` guard pattern in `tests/test_requirements_consolidation.py`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Update `tests/test_release_metadata.py` to parse `pyproject.toml`, read README/changelog/release workflow text, and assert every version surface matches `1.2.0-rc3` / `v1.2.0-rc3`.
  - test: Update `tests/test_requirements_consolidation.py` with explicit active-path scans for `.github/workflows/*.yml` and `docker/dockerfiles/Dockerfile*`, failing on `requirements*.txt`, `pip install -r`, and requirements hash cache keys.
  - impl: Keep helper functions local to the test files; avoid introducing a new test utility module for this narrow contract.
  - verify: `uv run pytest tests/test_requirements_consolidation.py tests/test_release_metadata.py -v --no-cov`

### SL-1 — Version Metadata Files

- **Scope**: Make package metadata, runtime metadata, README status, and changelog agree on the frozen P21 pre-release version.
- **Owned files**: `pyproject.toml`, `mcp_server/__init__.py`, `README.md`, `CHANGELOG.md`
- **Interfaces provided**: version surfaces consumed by IF-0-P21-1
- **Interfaces consumed**: `EXPECTED_VERSION = "1.2.0-rc3"` from SL-0
- **Parallel-safe**: yes
- **Tasks**:
  - test: Run SL-0 tests first and confirm version assertions fail for the current `pyproject.toml`/README/changelog mismatch.
  - impl: Set `[project].version` in `pyproject.toml` and `mcp_server.__version__` to `1.2.0-rc3`.
  - impl: Update README project status version text to `1.2.0-rc3` without doing the P23 support-matrix truth pass.
  - impl: Add a `## [1.2.0-rc3] — 2026-04-21` changelog section describing only P21 contract/dependency unification work; leave historical P20/P19 entries intact.
  - verify: `uv run pytest tests/test_release_metadata.py -v --no-cov`

### SL-2 — Release Workflow Contract

- **Scope**: Align release automation with the P21 version/dependency contract without redesigning the release pipeline.
- **Owned files**: `.github/workflows/release-automation.yml`
- **Interfaces provided**: release workflow surfaces consumed by IF-0-P21-1 and IF-0-P21-2
- **Interfaces consumed**: `EXPECTED_VERSION`/`EXPECTED_TAG` from SL-0; `pyproject.toml`/`uv.lock` dependency source from the roadmap
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 tests to expose stale release workflow version example/body text and `pip install -r requirements.txt` usage.
  - impl: Update workflow-dispatch version text/examples/defaults that name the release version to `v1.2.0-rc3`.
  - impl: Replace release-test dependency setup with uv-backed commands, for example install `uv`, run `uv sync --locked --extra dev`, and run tests through `uv run pytest`.
  - impl: Extend the workflow's version consistency step to check both `pyproject.toml` and `mcp_server/__init__.py`; do not add package build/smoke behavior reserved for P22.
  - impl: Update release notes PR/body template version wording only where it is part of the release contract.
  - verify: `uv run pytest tests/test_requirements_consolidation.py tests/test_release_metadata.py -v --no-cov`

### SL-3 — CI Dependency Unification

- **Scope**: Remove stale requirements-file dependency setup from active non-release workflows while preserving existing job intent.
- **Owned files**: `.github/workflows/ci-cd-pipeline.yml`, `.github/workflows/index-management.yml`, `.github/workflows/mcp-index.yml`, `.github/workflows/index-artifact-management.yml`, `.github/workflows/lockfile-check.yml`, `.github/workflows/container-registry.yml`, `.github/workflows/maintenance.yml`
- **Interfaces provided**: workflow side of IF-0-P21-2
- **Interfaces consumed**: `pyproject.toml`/`uv.lock` dependency source from the roadmap
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 requirements-consolidation tests to identify exact active workflow references to removed requirements files.
  - impl: Replace dependency cache keys based on `requirements*.txt` with `uv.lock`/`pyproject.toml` keys.
  - impl: Replace `pip install -r requirements.txt` and `pip install -r requirements-semantic.txt` with the smallest equivalent uv commands for each job, typically `python -m pip install uv`, `uv sync --locked --extra dev`, and `uv sync --locked --extra semantic` where semantic dependencies are required.
  - impl: Keep informational and release-gate job semantics unchanged; P25 owns blocking-gate redesign.
  - verify: `uv run pytest tests/test_requirements_consolidation.py -v --no-cov`

### SL-4 — Docker Dependency Unification

- **Scope**: Remove stale requirements-file copies and installs from Dockerfiles without trying to prove full container release behavior.
- **Owned files**: `docker/dockerfiles/Dockerfile`, `docker/dockerfiles/Dockerfile.dev`, `docker/dockerfiles/Dockerfile.enhanced`, `docker/dockerfiles/Dockerfile.mcp`, `docker/dockerfiles/Dockerfile.production`, `docker/dockerfiles/Dockerfile.full`, `docker/dockerfiles/Dockerfile.minimal`, `docker/dockerfiles/Dockerfile.standard`
- **Interfaces provided**: Dockerfile side of IF-0-P21-2
- **Interfaces consumed**: `pyproject.toml`/`uv.lock` dependency source from the roadmap
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 requirements-consolidation tests to fail on Dockerfile `COPY requirements*.txt` and `pip install -r` references.
  - impl: Copy `pyproject.toml` and `uv.lock` before dependency installation for Docker cache locality.
  - impl: Install dependencies from the locked project source, using uv in the image build path. For production, install only the package/extras needed by the existing production image; do not add P22 smoke/build behavior.
  - impl: Preserve existing exposed ports, health checks, users, and command shapes unless directly blocked by dependency unification.
  - verify: `uv run pytest tests/test_requirements_consolidation.py -v --no-cov`

### SL-5 — Final P21 Audit

- **Scope**: Run the P21 acceptance checks and record any remaining drift for P22/P23 without writing new feature/docs artifacts.
- **Owned files**: (none)
- **Interfaces provided**: P21 completion evidence for P22
- **Interfaces consumed**: IF-0-P21-1 from SL-1/SL-2; IF-0-P21-2 from SL-2/SL-3/SL-4
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the P21 metadata tests after all implementation lanes land.
  - verify: `uv sync --locked`
  - verify: `uv run pytest tests/test_requirements_consolidation.py tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n "requirements(-production|-semantic)?\\.txt|requirements\\*\\.txt|pip install -r|hashFiles\\('\\*\\*/requirements\\*\\.txt'\\)" .github docker README.md docs pyproject.toml`
  - impl: If the final `rg` finds documentation-only references outside P21 scope, classify them explicitly as P23 docs-truth work instead of editing broad docs in P21.

## Verification

Required P21 checks:

```bash
uv sync --locked
uv run pytest tests/test_requirements_consolidation.py tests/test_release_metadata.py -v --no-cov
rg -n "requirements(-production|-semantic)?\\.txt|requirements\\*\\.txt|pip install -r|hashFiles\\('\\*\\*/requirements\\*\\.txt'\\)" .github docker README.md docs pyproject.toml
```

Expected final state:

- The pytest command passes.
- The `rg` command returns no active workflow or Dockerfile references. Documentation hits may remain only if explicitly classified as P23 truth-pass work.
- No Docker build, wheel build, or release publish is run in P21; those are P22/P25 responsibilities.

## Acceptance Criteria

- [ ] `mcp_server.__version__`, `pyproject.toml`, README status text, `CHANGELOG.md`, `.github/workflows/release-automation.yml`, and local tag lookup all agree on `1.2.0-rc3` / `v1.2.0-rc3`.
- [ ] Active workflows no longer install from or cache against removed `requirements*.txt` files.
- [ ] Dockerfiles no longer copy or install from removed `requirements*.txt` files.
- [ ] `tests/test_requirements_consolidation.py` covers active workflow and Docker references, not only file absence.
- [ ] `tests/test_release_metadata.py` covers package metadata, runtime metadata, README, changelog, release workflow, and tag lookup.
- [ ] `uv sync --locked` passes.
- [ ] `uv run pytest tests/test_requirements_consolidation.py tests/test_release_metadata.py -v --no-cov` passes.
- [ ] Any remaining stale install/version claims outside active release paths are explicitly deferred to P23.
