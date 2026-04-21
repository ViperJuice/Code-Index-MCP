# P22: Packaging & Container Release Smoke

> Plan doc produced by `codex-plan-phase P22` against `specs/phase-plans-v2.md` on 2026-04-21.
> P22 consumes the P21 contract in `plans/phase-plan-v2-p21.md`: `1.2.0-rc3` / `v1.2.0-rc3`, and `pyproject.toml` + `uv.lock` as the only active dependency source of truth.

## Context

P22 proves the first clean-user release paths: wheel install, CLI startup, a minimal lexical MCP smoke against a fixture repo, and the production container build/run path.

Current repo surfaces relevant to P22:

- `pyproject.toml` already reports `1.2.0-rc3`, but the dev extras do not include `build`; release automation installs `build` ad hoc before `python -m build`.
- No `tests/smoke/` directory exists yet.
- `Makefile` has no release smoke target; `docker` still builds `mcp-server:latest` from the repo-root `Dockerfile`, not `docker/dockerfiles/Dockerfile.production`.
- `docker/dockerfiles/Dockerfile.production` now copies `pyproject.toml` and `uv.lock`, but the builder stage only runs `uv sync --locked --extra production --no-install-project`, then the runtime stage copies source files without installing the project entry points. That is not enough to prove `mcp-index --help` in the image.
- The production image currently starts the FastAPI admin surface with Gunicorn. P22 can keep that default if the local smoke explicitly validates the documented STDIO/CLI path inside the image.
- GHCR names disagree: README and `docker/README.md` use `ghcr.io/code-index-mcp/mcp-index:*`; release automation uses `ghcr.io/viperjuice/code-index-mcp:*`; container workflows derive `${{ github.repository }}` and should be frozen to the same lower-case package name.

P22 should stay lexical-first. Optional semantic dependencies may remain out of the production smoke as long as the image and docs say so plainly.

## Interface Freeze Gates

- [ ] IF-0-P22-1 - Release smoke contract: `make release-smoke` runs one committed smoke harness that builds a wheel from the current checkout, creates a fresh virtual environment, installs the built wheel, verifies `mcp-index --help`, and runs a minimal lexical `search_code` and `symbol_lookup` smoke against a temporary Python fixture repo.
- [ ] IF-0-P22-2 - Container contract: `make release-smoke-container` builds `docker/dockerfiles/Dockerfile.production` as `ghcr.io/viperjuice/code-index-mcp:local-smoke`, verifies the image has the `mcp-index` console script, runs `mcp-index --help` inside the image, and runs a local HTTP health check against the default container command.
- [ ] IF-0-P22-3 - Image-name contract: `ghcr.io/viperjuice/code-index-mcp` is the single documented and workflow-pushed GHCR package name across release automation, container registry workflow, CI Docker build metadata, README, Docker README, and install/setup helper scripts.
- [ ] IF-0-P22-4 - CI smoke contract: active CI/release workflows call the same Make targets or smoke script used locally; they do not duplicate bespoke release-smoke command sequences.

## Lane Index & Dependencies

- SL-0 - Contract tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4, SL-5; Parallel-safe: yes
- SL-1 - Shared release smoke harness; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: yes
- SL-2 - Build metadata and Make targets; Depends on: SL-0, SL-1; Blocks: SL-4, SL-6; Parallel-safe: yes
- SL-3 - Production Docker smoke path; Depends on: SL-0, SL-1; Blocks: SL-4, SL-5, SL-6; Parallel-safe: yes
- SL-4 - Workflow smoke and image-name wiring; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SL-5, SL-6; Parallel-safe: yes
- SL-5 - Documented image/helper alignment; Depends on: SL-0, SL-3, SL-4; Blocks: SL-6; Parallel-safe: yes
- SL-6 - Final P22 audit; Depends on: SL-2, SL-3, SL-4, SL-5; Blocks: (none); Parallel-safe: no

Lane DAG:

```text
SL-0
 ├─> SL-1 ─┬─> SL-2 ─┐
 │         ├─> SL-3 ─┼─> SL-4 ─> SL-5 ─┐
 │         └─────────┘                  │
 └──────────────────────────────────────┴─> SL-6
```

## Lanes

### SL-0 - Contract Tests

- **Scope**: Add executable P22 contract tests for smoke entry points, image-name consistency, and workflow reuse before implementation changes land.
- **Owned files**: `tests/smoke/test_release_smoke_contract.py`
- **Interfaces provided**: IF-0-P22-1 assertions, IF-0-P22-2 assertions, IF-0-P22-3 assertions, IF-0-P22-4 assertions
- **Interfaces consumed**: P21 `EXPECTED_VERSION = "1.2.0-rc3"` / `EXPECTED_TAG = "v1.2.0-rc3"` from `tests/test_release_metadata.py`; pre-existing `tests/fixtures/multi_repo.py::build_temp_repo` and `boot_test_server`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Create `tests/smoke/test_release_smoke_contract.py` and assert `scripts/release_smoke.py`, `make release-smoke`, and `make release-smoke-container` exist.
  - test: Assert `pyproject.toml` exposes the `mcp-index` console script and includes whatever dependency is required for the committed build command.
  - test: Assert active workflows reference the shared Make targets or `scripts/release_smoke.py`, not hand-rolled wheel/container smoke blocks.
  - test: Assert GHCR package references across `.github/workflows/ci-cd-pipeline.yml`, `.github/workflows/release-automation.yml`, `.github/workflows/container-registry.yml`, `README.md`, `docker/README.md`, and install/setup helper scripts all use `ghcr.io/viperjuice/code-index-mcp`.
  - verify: `uv run pytest tests/smoke/test_release_smoke_contract.py -v --no-cov`

### SL-1 - Shared Release Smoke Harness

- **Scope**: Implement one Python smoke harness that can run wheel, CLI, lexical MCP, and optional Docker smoke modes locally and in CI.
- **Owned files**: `scripts/release_smoke.py`
- **Interfaces provided**: `scripts/release_smoke.py --wheel`, `scripts/release_smoke.py --stdio`, `scripts/release_smoke.py --container`, `scripts/release_smoke.py --all`, fixture-repo smoke behavior for IF-0-P22-1 and IF-0-P22-2
- **Interfaces consumed**: `mcp-index` console script from `pyproject.toml`; `build_temp_repo` / `boot_test_server` smoke pattern from `tests/fixtures/multi_repo.py`; CLI entry point in `mcp_server/cli/server_commands.py`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 contract tests to require the harness and its CLI modes.
  - impl: Add `scripts/release_smoke.py` with argparse modes for wheel, STDIO/lexical, container, and all.
  - impl: In wheel mode, remove/recreate a temporary build root, run the committed build command, create a fresh venv outside the project `.venv`, install `dist/index_it_mcp-1.2.0rc3*.whl`, and execute `mcp-index --help`.
  - impl: In STDIO/lexical mode, build a temporary git repo with a small Python file, boot the existing in-process MCP test server, and assert lexical `search_code` finds a known token and `symbol_lookup` finds a known function or class.
  - impl: In container mode, build the production Dockerfile as `ghcr.io/viperjuice/code-index-mcp:local-smoke`, run `mcp-index --help` inside the image, start the default container command, and poll `/health` before cleanup.
  - verify: `uv run python scripts/release_smoke.py --wheel --stdio`
  - verify: `uv run python scripts/release_smoke.py --container`

### SL-2 - Build Metadata and Make Targets

- **Scope**: Make the local release-smoke commands first-class and ensure the wheel build command works from the locked project dependency contract.
- **Owned files**: `pyproject.toml`, `uv.lock`, `Makefile`
- **Interfaces provided**: `make release-smoke`, `make release-smoke-container`, build dependency availability for `python -m build`
- **Interfaces consumed**: SL-1 `scripts/release_smoke.py` CLI; P21 dependency source-of-truth contract
- **Parallel-safe**: yes
- **Tasks**:
  - test: Run SL-0 contract tests before implementation to expose missing Make targets and build dependency drift.
  - impl: Add `build>=1.2.0` to the `dev` optional dependency group if the chosen build command is `uv run python -m build`; update `uv.lock` with `uv lock`.
  - impl: Add `.PHONY` entries and Make targets: `release-smoke` for wheel plus lexical STDIO smoke, and `release-smoke-container` for Docker smoke.
  - impl: Keep existing `docker` target unchanged unless needed by the new targets; do not convert broad Docker workflows outside the P22 smoke path.
  - verify: `uv lock --check`
  - verify: `make release-smoke`

### SL-3 - Production Docker Smoke Path

- **Scope**: Make the production Dockerfile install the package and support the P22 container smoke without expanding production deployment scope.
- **Owned files**: `docker/dockerfiles/Dockerfile.production`
- **Interfaces provided**: production image with installed `mcp-index` console script, default HTTP health surface, lexical-first container contract
- **Interfaces consumed**: P21 `pyproject.toml`/`uv.lock` dependency source; SL-1 container smoke mode; SL-2 image target name
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 and SL-1 container smoke expectations to fail on missing `mcp-index` inside the current image.
  - impl: In the builder stage, copy enough project metadata and source for `uv sync --locked --extra production` to install the package entry points into the virtualenv.
  - impl: Preserve non-root runtime, health check, exposed ports, and default Gunicorn/FastAPI command unless the smoke exposes a direct startup bug.
  - impl: Add build labels or args only where they are already accepted by existing workflows; do not add Kubernetes or deployment hardening.
  - verify: `docker build -f docker/dockerfiles/Dockerfile.production -t ghcr.io/viperjuice/code-index-mcp:local-smoke .`
  - verify: `docker run --rm ghcr.io/viperjuice/code-index-mcp:local-smoke mcp-index --help`
  - verify: `make release-smoke-container`

### SL-4 - Workflow Smoke and Image-Name Wiring

- **Scope**: Wire active CI and release workflows to the shared smoke targets and freeze the workflow GHCR package name.
- **Owned files**: `.github/workflows/ci-cd-pipeline.yml`, `.github/workflows/release-automation.yml`, `.github/workflows/container-registry.yml`
- **Interfaces provided**: CI side of IF-0-P22-3 and IF-0-P22-4
- **Interfaces consumed**: SL-1 smoke harness modes; SL-2 Make targets; SL-3 production Dockerfile/image behavior
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 workflow assertions to expose bespoke release smoke and image-name drift.
  - impl: Add or adjust CI job steps to run `make release-smoke` after dependency setup in the Ubuntu test/build path.
  - impl: Add or adjust container workflow validation to run `make release-smoke-container` for the production image path where Docker is available.
  - impl: Replace workflow image-name derivation with the frozen lower-case package `viperjuice/code-index-mcp` while preserving the `ghcr.io` registry.
  - impl: In release automation, replace ad hoc `pip install build wheel` / `python -m build` smoke blocks with `make release-smoke`; keep actual artifact build/publish steps in the release artifact job.
  - verify: `uv run pytest tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `rg -n "ghcr\\.io/code-index-mcp/mcp-index|IMAGE_NAME: \\$\\{\\{ github\\.repository \\}\\}|python -m build" .github README.md docker scripts`

### SL-5 - Documented Image/Helper Alignment

- **Scope**: Update only P22-facing image names and release-smoke command references in docs and helper scripts, leaving the broader P23 docs truth pass untouched.
- **Owned files**: `README.md`, `docker/README.md`, `scripts/install-mcp-docker.sh`, `scripts/install-mcp-docker.ps1`, `scripts/setup-mcp-json.sh`, `scripts/setup-mcp-json.ps1`, `scripts/build-images.sh`
- **Interfaces provided**: documentation/helper side of IF-0-P22-3
- **Interfaces consumed**: SL-3 image behavior; SL-4 workflow package name
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 image-name assertions to identify stale docs/helper image references.
  - impl: Replace `ghcr.io/code-index-mcp/mcp-index` examples and defaults with `ghcr.io/viperjuice/code-index-mcp`.
  - impl: If examples still need variants such as `minimal` or `standard`, either map them to tags actually produced by workflows or narrow examples to the tags P22 proves, such as `:latest`, `:v1.2.0-rc3`, and `:local-smoke` for local-only commands.
  - impl: Add a terse release-smoke command reference near existing Docker/build documentation; do not rewrite support matrices or broad feature claims reserved for P23.
  - verify: `uv run pytest tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `rg -n "ghcr\\.io/code-index-mcp/mcp-index|mcp-index:(minimal|standard)" README.md docker/README.md scripts`

### SL-6 - Final P22 Audit

- **Scope**: Run the P22 acceptance checks and record remaining docs/support-matrix drift for P23 without broadening P22.
- **Owned files**: (none)
- **Interfaces provided**: P22 completion evidence for P23 and P25
- **Interfaces consumed**: IF-0-P22-1 from SL-1/SL-2; IF-0-P22-2 from SL-1/SL-3; IF-0-P22-3 from SL-4/SL-5; IF-0-P22-4 from SL-4
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the P22 smoke contract tests after all implementation lanes land.
  - verify: `uv sync --locked --extra dev`
  - verify: `uv run pytest tests/smoke/test_release_smoke_contract.py tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov`
  - verify: `make release-smoke`
  - verify: `make release-smoke-container`
  - verify: `rg -n "requirements(-production|-semantic)?\\.txt|requirements\\*\\.txt|pip install -r|hashFiles\\('\\*\\*/requirements\\*\\.txt'\\)" .github docker README.md docs pyproject.toml`
  - verify: `rg -n "ghcr\\.io/code-index-mcp/mcp-index|mcp-index:(minimal|standard)|IMAGE_NAME: \\$\\{\\{ github\\.repository \\}\\}" .github README.md docker scripts`
  - impl: Classify any remaining broad support/documentation inconsistency as P23 work, not P22 implementation.

## Verification

Required P22 checks:

```bash
uv sync --locked --extra dev
uv run pytest tests/smoke/test_release_smoke_contract.py tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
make release-smoke
make release-smoke-container
rg -n "requirements(-production|-semantic)?\\.txt|requirements\\*\\.txt|pip install -r|hashFiles\\('\\*\\*/requirements\\*\\.txt'\\)" .github docker README.md docs pyproject.toml
rg -n "ghcr\\.io/code-index-mcp/mcp-index|mcp-index:(minimal|standard)|IMAGE_NAME: \\$\\{\\{ github\\.repository \\}\\}" .github README.md docker scripts
```

Expected final state:

- Wheel build and fresh-venv install pass through `make release-smoke`.
- `mcp-index --help` passes from the installed wheel and from the production image.
- Minimal lexical `search_code` and `symbol_lookup` pass against a temporary fixture repo.
- Production Dockerfile builds from `pyproject.toml`/`uv.lock`, not removed requirements files.
- The production image starts its default HTTP command and responds to `/health`.
- GHCR package naming is frozen to `ghcr.io/viperjuice/code-index-mcp` across active workflows, docs, and helper scripts.
- Remaining docs truth/support-matrix work is explicitly deferred to P23.

## Acceptance Criteria

- [ ] `python -m build` works from a clean checkout after `uv sync --locked --extra dev`, either directly or through `make release-smoke`.
- [ ] A fresh virtual environment can install the built wheel and run `mcp-index --help`.
- [ ] A minimal lexical smoke can start MCP services and execute `search_code` plus `symbol_lookup` against a fixture repo.
- [ ] `docker/dockerfiles/Dockerfile.production` builds without removed dependency files and includes the installed `mcp-index` entry point.
- [ ] The production Docker image passes `mcp-index --help` and default-command `/health` smoke checks.
- [ ] The documented GHCR image name matches the release workflow, container registry workflow, and CI Docker metadata target.
- [ ] Release smoke commands are captured in `scripts/release_smoke.py` and Make targets, and active CI/release workflows use those shared commands.
- [ ] P21 release metadata and dependency consolidation tests still pass.
