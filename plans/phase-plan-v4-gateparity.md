# GATEPARITY: Release Gate Parity & RC5 Surface Cleanup

> Plan doc produced by `codex-plan-phase specs/phase-plans-v4.md GATEPARITY`
> on 2026-04-23.
> Source roadmap `specs/phase-plans-v4.md` is staged as a new artifact in this
> worktree (`git status --short -- specs/phase-plans-v4.md` shows `A`).

## Context

GATEPARITY is the first v4 phase and depends on the completed P34 public-alpha
recut work. It is intentionally a release-management cleanup phase, not a
reopening of the v3 multi-repo implementation.

Current repo state already has much of the P34 release surface:

- `Makefile` exposes `alpha-docs-truth`, `alpha-production-matrix`,
  `alpha-release-gates`, `release-smoke`, and `release-smoke-container`.
- `make alpha-release-gates` includes the P33 production matrix, but
  `alpha-docs-truth` does not currently run
  `tests/docs/test_p34_public_alpha_recut.py`.
- `.github/workflows/release-automation.yml` runs `make alpha-release-gates`
  in `preflight-release-gates`, but does not run `make release-smoke-container`
  before mutating release state.
- `.github/workflows/container-registry.yml` has a separate blocking
  `Alpha Gate - Docker Build And Smoke` job that runs
  `make release-smoke-container`.
- `tests/docs/test_p25_release_checklist.py` and
  `tests/test_p25_release_gates.py` still omit
  `Alpha Gate - Production Multi-Repo Matrix` from the shared required-gate
  vocabulary, even though the CI aggregator already depends on
  `alpha-production-matrix`.
- `scripts/install-mcp-docker.sh` and `scripts/install-mcp-docker.ps1` still
  offer `v1.2.0-rc4` as the release-candidate image.
- Active docs still contain unqualified RC4 examples in
  `docs/DEPLOYMENT-GUIDE.md`, `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`,
  `docs/DYNAMIC_PLUGIN_LOADING.md`, and `docs/api/API-REFERENCE.md`; historical
  docs such as `CHANGELOG.md` may keep RC4 only when clearly historical.

The phase should make the release gate vocabulary executable, wire the missing
P34 docs/container checks into automated or mandatory pre-dispatch flow, update
the installer RC, and either update or explicitly mark remaining RC4 references
as non-current.

## Interface Freeze Gates

- [ ] IF-0-GATEPARITY-1 - Release automation parity contract:
      `alpha-docs-truth` runs `tests/docs/test_p34_public_alpha_recut.py`, and
      `.github/workflows/release-automation.yml` runs `make release-smoke-container`
      in `preflight-release-gates` after `make alpha-release-gates` and before
      any version mutation, branch creation, artifact build, release creation,
      PyPI publish, or container publish.
- [ ] IF-0-GATEPARITY-2 - Required gate vocabulary contract:
      every required public-alpha gate list asserted by
      `tests/docs/test_p25_release_checklist.py`,
      `tests/test_p25_release_gates.py`, `docs/operations/deployment-runbook.md`,
      and `docs/operations/user-action-runbook.md` includes
      `Alpha Gate - Production Multi-Repo Matrix`.
- [ ] IF-0-GATEPARITY-3 - Docker installer RC contract:
      `scripts/install-mcp-docker.sh` and `scripts/install-mcp-docker.ps1`
      offer `v1.2.0-rc5` as the release-candidate image, select that tag for
      option `2`, and contain no active `v1.2.0-rc4` installer variant text.
- [ ] IF-0-GATEPARITY-4 - RC4 drift disposition contract:
      active user-facing docs contain no unqualified `1.2.0-rc4` or
      `v1.2.0-rc4` release instructions; remaining RC4 references are either in
      historical changelog/summary material or are explicitly labeled
      historical, archived, or non-current.
- [ ] IF-0-GATEPARITY-5 - Verification contract: the phase accepts only after
      the GATEPARITY doc tests, P34 release-truth tests, P33 production matrix,
      wheel smoke, container smoke, and RC4/RC5 truth sweep pass from a clean
      checkout.

## Lane Index & Dependencies

- SL-0 - Gate contract tests; Depends on: P34; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Automation parity wiring; Depends on: SL-0; Blocks: GATEPARITY acceptance; Parallel-safe: yes
- SL-2 - Docker installer RC5 variants; Depends on: SL-0; Blocks: GATEPARITY acceptance; Parallel-safe: yes
- SL-3 - Required-gate runbook vocabulary; Depends on: SL-0; Blocks: GATEPARITY acceptance; Parallel-safe: yes
- SL-4 - RC4 drift documentation cleanup; Depends on: SL-0; Blocks: GATEPARITY acceptance; Parallel-safe: yes

Lane DAG:

```text
P34
  -> SL-0
       -> SL-1 --.
       -> SL-2 --.
       -> SL-3 ----> GATEPARITY acceptance
       -> SL-4 --'
```

## Lanes

### SL-0 - Gate Contract Tests

- **Scope**: Freeze the executable release-gate and RC5 drift contracts before
  changing automation, installer scripts, or docs.
- **Owned files**: `tests/docs/test_p25_release_checklist.py`,
  `tests/test_p25_release_gates.py`,
  `tests/docs/test_p34_public_alpha_recut.py`,
  `tests/smoke/test_release_smoke_contract.py`
- **Interfaces provided**: IF-0-GATEPARITY-1 through IF-0-GATEPARITY-4 as
  focused assertions; shared required-gate name list containing
  `Alpha Gate - Production Multi-Repo Matrix`
- **Interfaces consumed**: P34 `PUBLIC_ALPHA_VERSION = "1.2.0-rc5"` and
  `PUBLIC_ALPHA_TAG = "v1.2.0-rc5"`; existing P25 gate workflow tests; existing
  P22 release smoke contract tests
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `Alpha Gate - Production Multi-Repo Matrix` to the required gate
    vocabulary in `tests/docs/test_p25_release_checklist.py` and
    `tests/test_p25_release_gates.py`.
  - test: Extend `tests/docs/test_p25_release_checklist.py` so the user-action
    runbook required-gate list is asserted alongside the deployment runbook
    gate table.
  - test: Extend `tests/docs/test_p34_public_alpha_recut.py` with active-doc
    RC4 drift assertions for `docs/DEPLOYMENT-GUIDE.md`,
    `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`,
    `docs/DYNAMIC_PLUGIN_LOADING.md`, and `docs/api/API-REFERENCE.md`; allow
    RC4 only when a file or nearby section is explicitly historical or archived.
  - test: Extend `tests/smoke/test_release_smoke_contract.py` to require
    `tests/docs/test_p34_public_alpha_recut.py` in `alpha-docs-truth` and
    `make release-smoke-container` in release automation preflight.
  - verify: `uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py tests/docs/test_p34_public_alpha_recut.py tests/smoke/test_release_smoke_contract.py -v --no-cov`

### SL-1 - Automation Parity Wiring

- **Scope**: Make automated release qualification run the P34 docs contract and
  container smoke before any release mutation.
- **Owned files**: `Makefile`, `.github/workflows/release-automation.yml`,
  `.github/workflows/container-registry.yml`
- **Interfaces provided**: IF-0-GATEPARITY-1; `alpha-docs-truth` coverage for
  the P34 recut test; release-automation preflight sequence that runs container
  smoke before mutating release state
- **Interfaces consumed**: SL-0 release smoke contract assertions; existing
  `alpha-release-gates`; existing `release-smoke-container`; existing blocking
  container-registry job name `Alpha Gate - Docker Build And Smoke`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 tests to fail first on missing P34 docs coverage and missing
    release-automation container smoke.
  - impl: Add `tests/docs/test_p34_public_alpha_recut.py` to the
    `alpha-docs-truth` pytest command in `Makefile`.
  - impl: Update `.github/workflows/release-automation.yml` so
    `preflight-release-gates` runs `make alpha-release-gates` and then
    `make release-smoke-container`, with comments naming the P34 docs contract,
    P33 matrix, wheel smoke, and container smoke.
  - impl: Leave `.github/workflows/container-registry.yml` as the blocking
    Docker build/smoke workflow unless the SL-0 contract shows its command name
    or gate name has drifted.
  - impl: Do not promote scan, signing, cleanup, or manifest-publish jobs to
    blockers in this phase.
  - verify: `make -n alpha-docs-truth alpha-release-gates release-smoke-container`
  - verify: `uv run pytest tests/smoke/test_release_smoke_contract.py -v --no-cov`

### SL-2 - Docker Installer RC5 Variants

- **Scope**: Update the interactive Docker installer release-candidate variant
  from RC4 to RC5 in shell and PowerShell paths.
- **Owned files**: `scripts/install-mcp-docker.sh`,
  `scripts/install-mcp-docker.ps1`
- **Interfaces provided**: IF-0-GATEPARITY-3; option `2` maps to
  `v1.2.0-rc5` in both installers
- **Interfaces consumed**: SL-0 RC5 drift assertions; P34 public-alpha tag
  `v1.2.0-rc5`; current image package
  `ghcr.io/viperjuice/code-index-mcp`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 P34 drift tests to require both installers to contain
    `v1.2.0-rc5` and no active `v1.2.0-rc4` variant.
  - impl: In `scripts/install-mcp-docker.sh`, change the menu text, assignment,
    and selected log line for option `2` from `v1.2.0-rc4` to `v1.2.0-rc5`.
  - impl: In `scripts/install-mcp-docker.ps1`, make the same menu,
    `$script:Variant`, and selected log-line update.
  - impl: Keep `latest` and `local-smoke` behavior unchanged.
  - verify: `uv run pytest tests/docs/test_p34_public_alpha_recut.py tests/smoke/test_release_smoke_contract.py -v --no-cov`

### SL-3 - Required-Gate Runbook Vocabulary

- **Scope**: Align operator-facing required-gate prose with the CI aggregator
  and the P33 production matrix gate.
- **Owned files**: `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`
- **Interfaces provided**: IF-0-GATEPARITY-2; mandatory pre-dispatch language
  for P34 docs truth, P33 production matrix, wheel smoke, and container smoke
- **Interfaces consumed**: SL-0 required-gate assertions; SL-1 automation
  parity decision; existing deployment runbook gate table; existing user-action
  P25 and P34 sections
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 tests to assert both operator docs include
    `Alpha Gate - Production Multi-Repo Matrix` wherever the required
    public-alpha gate list appears.
  - impl: Update the P25 required-gate list in
    `docs/operations/user-action-runbook.md` to include
    `Alpha Gate - Production Multi-Repo Matrix` between integration smoke and
    Docker build/smoke.
  - impl: Ensure `docs/operations/deployment-runbook.md` continues to map the
    P33 gate to `.github/workflows/ci-cd-pipeline.yml` and
    `make alpha-production-matrix`, and that failure behavior says the gate is
    release-blocking.
  - impl: Strengthen the P34 recut checklist wording so `make release-smoke-container`
    is mandatory before release dispatch or is covered by release automation
    preflight from SL-1.
  - verify: `uv run pytest tests/docs/test_p25_release_checklist.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov`

### SL-4 - RC4 Drift Documentation Cleanup

- **Scope**: Remove active RC4 release instructions from user-facing docs or
  mark genuinely historical RC4 examples as non-current.
- **Owned files**: `docs/DEPLOYMENT-GUIDE.md`,
  `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`,
  `docs/DYNAMIC_PLUGIN_LOADING.md`, `docs/api/API-REFERENCE.md`,
  `docs/implementation/PROJECT_COMPLETION_SUMMARY.md`
- **Interfaces provided**: IF-0-GATEPARITY-4; active docs aligned to the
  `1.2.0-rc5` public-alpha contract or clearly labeled historical
- **Interfaces consumed**: SL-0 RC4 drift assertions; P34 public-alpha tag;
  existing support-matrix scope limits
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 P34 drift tests plus an explicit `rg` sweep to identify all
    remaining `1.2.0-rc4` and `v1.2.0-rc4` references.
  - impl: Update active deployment examples in `docs/DEPLOYMENT-GUIDE.md` and
    `docs/PRODUCTION_DEPLOYMENT_GUIDE.md` to RC5.
  - impl: Update version examples in `docs/DYNAMIC_PLUGIN_LOADING.md` and
    `docs/api/API-REFERENCE.md` to RC5 unless the surrounding section is made
    explicitly historical/non-current.
  - impl: Treat `docs/implementation/PROJECT_COMPLETION_SUMMARY.md` as
    historical implementation material; either label its RC4 command as
    historical or leave it only if SL-0's allowed-historical rule covers it.
  - impl: Do not rewrite `CHANGELOG.md` historical RC4 release sections.
  - verify: `rg -n "v1\\.2\\.0-rc4|1\\.2\\.0-rc4|v1\\.2\\.0-rc5|1\\.2\\.0-rc5" README.md CHANGELOG.md docs scripts tests .github Makefile pyproject.toml mcp_server/__init__.py`
  - verify: `uv run pytest tests/docs/test_p34_public_alpha_recut.py -v --no-cov`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` after the lane changes land.

Lane-local checks:

```bash
uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py tests/docs/test_p34_public_alpha_recut.py tests/smoke/test_release_smoke_contract.py -v --no-cov
make -n alpha-docs-truth alpha-release-gates release-smoke-container
```

Whole-phase acceptance checks:

```bash
uv run pytest tests/docs/test_p25_release_checklist.py tests/docs/test_p34_public_alpha_recut.py tests/smoke/test_release_smoke_contract.py -v --no-cov
make alpha-production-matrix
make release-smoke
make release-smoke-container
rg -n "v1\\.2\\.0-rc4|v1\\.2\\.0-rc5|Alpha Gate - Production Multi-Repo Matrix|release-smoke-container" \
  Makefile .github/workflows docs scripts tests
```

Optional release-automation dry read:

```bash
rg -n "make alpha-release-gates|make release-smoke-container|tests/docs/test_p34_public_alpha_recut.py" \
  Makefile .github/workflows/release-automation.yml tests
```

## Acceptance Criteria

- [x] `alpha-docs-truth` runs `tests/docs/test_p34_public_alpha_recut.py`.
- [x] `.github/workflows/release-automation.yml` runs
      `make release-smoke-container` in `preflight-release-gates` before
      downstream release mutation jobs.
- [x] `tests/docs/test_p25_release_checklist.py` and
      `tests/test_p25_release_gates.py` require
      `Alpha Gate - Production Multi-Repo Matrix` in public-alpha required gate
      lists.
- [x] `docs/operations/deployment-runbook.md` and
      `docs/operations/user-action-runbook.md` name the P33 production matrix as
      a required public-alpha gate.
- [x] `scripts/install-mcp-docker.sh` and
      `scripts/install-mcp-docker.ps1` offer/select `v1.2.0-rc5` for the release
      candidate image.
- [x] Active user-facing docs no longer contain unqualified RC4 release
      instructions; remaining RC4 references are historical or explicitly
      non-current.
- [ ] P34 release-truth tests, production matrix, wheel smoke, container smoke,
      and the RC4/RC5 truth sweep pass from a clean checkout.

## Execution Evidence

GATEPARITY was executed on 2026-04-23 from `main` at
`87b3b3a149d52f64a18f6275c4c078bac176ebee`.

Verification completed:

- `uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py tests/docs/test_p34_public_alpha_recut.py tests/smoke/test_release_smoke_contract.py -v --no-cov` - 23 passed.
- `make -n alpha-docs-truth alpha-release-gates release-smoke-container` - command expansion confirmed P34 docs truth, alpha release gates, and container smoke wiring.
- `make alpha-production-matrix` - 65 passed.
- `make release-smoke` - wheel build/install and STDIO release smoke passed.
- `make release-smoke-container` - local production container build and fallback/readiness smoke passed.
- `rg -n "v1\\.2\\.0-rc4|1\\.2\\.0-rc4|v1\\.2\\.0-rc5|1\\.2\\.0-rc5|Alpha Gate - Production Multi-Repo Matrix|release-smoke-container" Makefile .github/workflows docs scripts tests` - remaining RC4 reference is explicitly labeled historical/non-current in `docs/implementation/PROJECT_COMPLETION_SUMMARY.md`.

GATEPARITY implementation and verification are complete in the current worktree.
Formal clean-checkout acceptance still requires these changes to be committed on
`main` and rechecked from a clean tree before RC5REL dispatch.
