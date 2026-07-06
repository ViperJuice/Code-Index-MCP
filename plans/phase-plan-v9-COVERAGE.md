---
phase_loop_plan_version: 1
phase: COVERAGE
roadmap: specs/phase-plans-v9.md
roadmap_sha256: b1900a431a8c6f2191e009f4623d23f00024953febeb78947149f986fd36934b
---
# COVERAGE: Coverage Evidence Without Hosted Compute Creep

## Context

COVERAGE is Phase 4 in `specs/phase-plans-v9.md`. The canonical
`.phase-loop/state.json` reports PUBNAME, REPOCLEAN, and LOCALCI complete,
`COVERAGE` unplanned, a clean worktree at runner reconciliation time, and
roadmap SHA-256
`b1900a431a8c6f2191e009f4623d23f00024953febeb78947149f986fd36934b`.
Legacy `.codex/phase-loop/` files are compatibility artifacts only and are not
used to supersede the canonical `.phase-loop/` state.

Planning observations:

- `docs/status/localci-validation-contract.md` is the frozen LOCALCI input for
  this phase; it records `make agent-*` commands, fail-closed offload
  semantics, and no prior coverage threshold or hosted upload change.
- Existing coverage config lives in `.coveragerc`, not `pyproject.toml`; it
  already emits `coverage.xml`, `coverage.json`, and `htmlcov/` when coverage
  runs.
- `Makefile` has legacy `coverage` and `test-all` targets, while
  `agent-gate-local` and `agent-full-local` currently run LOCALCI suites with
  `--no-cov`.
- `.gitignore` ignores `.coverage` but does not yet explicitly ignore
  `coverage.xml`, `coverage.json`, `htmlcov/`, or the full `.coverage*` family
  required by the roadmap.
- `.github/workflows/ci-cd-pipeline.yml` consumes `make agent-gate` as
  protected evidence and has no current Codecov upload job; stale
  Codecov/upload examples still appear in
  `docs/development/TESTING-GUIDE.md`.
- `README.md` mentions ad hoc coverage commands, but it does not yet advertise
  a real uploaded badge; the badge must stay deferred unless upload evidence
  exists.

Planning boundary:

- COVERAGE may add coverage command targets, generated-artifact guards,
  coverage posture tests, local docs, workflow posture assertions, and a
  metadata-only evidence artifact.
- COVERAGE must measure the baseline before enforcing `--cov-fail-under=80`; if
  the local/offloaded baseline does not support 80 percent, it must record a
  threshold-ramp roadmap amendment instead of forcing a false gate.
- COVERAGE must not configure a Codecov token, mutate GitHub secrets, register
  self-hosted runners, expand the hosted matrix, or rewrite broad tests merely
  to chase percentage.
- Generated coverage outputs are runtime evidence only and must remain
  untracked and unstaged.

## Interface Freeze Gates

- [ ] IF-0-COVERAGE-1 — Coverage evidence contract: a local/offloaded coverage
      command emits `coverage.xml` and terminal missing-line output; baseline
      coverage and existing threshold posture are measured before any
      `--cov-fail-under=80` enforcement; generated coverage outputs are ignored
      and rejected when tracked or staged; hosted uploads or README badges are
      used only with real trusted-event evidence; and `agent-gate` or
      `agent-full` owns coverage generation without turning ordinary pull
      requests into a broader hosted coverage matrix.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `roadmap_amendment`
- target surfaces: `Makefile`, `.coveragerc`, `.gitignore`,
  `.github/workflows/ci-cd-pipeline.yml`, `README.md`,
  `docs/development/TESTING-GUIDE.md`, `docs/status/coverage-evidence.md`,
  `specs/phase-plans-v9.md`
- evidence paths: `docs/status/coverage-evidence.md`, `coverage.xml`,
  `coverage terminal output`, `workflow diff`
- redaction posture: `metadata_only`
- downstream handling: `roadmap amendment`

## Lane Index & Dependencies

SL-0 — Generated artifact guard and ignore policy
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3, SL-4, SL-5
  Parallel-safe: no
SL-1 — Coverage command and agent ownership
  Depends on: SL-0
  Blocks: SL-2, SL-3, SL-4, SL-5
  Parallel-safe: no
SL-2 — Documentation and README coverage posture
  Depends on: SL-0, SL-1
  Blocks: SL-3, SL-4, SL-5
  Parallel-safe: no
SL-3 — Protected CI coverage posture
  Depends on: SL-0, SL-1, SL-2
  Blocks: SL-4, SL-5
  Parallel-safe: no
SL-4 — Coverage evidence and threshold reducer
  Depends on: SL-0, SL-1, SL-2, SL-3
  Blocks: SL-5
  Parallel-safe: no
SL-5 — COVERAGE acceptance verification
  Depends on: SL-4
  Blocks: (none)
  Parallel-safe: no

Lane DAG:

```text
SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SL-5 -> COVERAGE acceptance
```

## Lanes

### SL-0 — Generated Artifact Guard And Ignore Policy

- **Scope**: Ensure generated coverage outputs are ignored and cannot be
  committed or staged as source-tree artifacts.
- **Owned files**: `.gitignore`, `scripts/check_coverage_artifacts.py`,
  `tests/test_coverage_artifact_guard.py`, `tests/test_ignore_patterns.py`
- **Interfaces provided**: `coverage-artifact-guard contract`
- **Interfaces consumed**: `git status --short`, `git ls-files`,
  `IgnorePatternManager`, `build_walker_filter` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_coverage_artifact_guard.py` coverage for tracked,
    staged, and merely untracked generated coverage outputs so only
    tracked/staged artifacts fail.
  - test: Extend `tests/test_ignore_patterns.py` to prove `coverage.xml`,
    `coverage.json`, `.coverage`, `.coverage.*`, and `htmlcov/` are ignored by
    repo policy and walker filters.
  - impl: Add explicit `.gitignore` entries for `coverage.xml`,
    `coverage.json`, `.coverage*`, `htmlcov/`, and any equivalent generated
    coverage output surfaced by `.coveragerc`.
  - impl: Add `scripts/check_coverage_artifacts.py` as a metadata-only guard
    that reports offending paths without printing file contents.
  - verify: `uv run pytest tests/test_coverage_artifact_guard.py tests/test_ignore_patterns.py -q --no-cov`

### SL-1 — Coverage Command And Agent Ownership

- **Scope**: Make coverage generation a local/offloaded command contract and
  wire it into the agent validation surface without making ordinary hosted pull
  requests run a new matrix.
- **Owned files**: `Makefile`, `.coveragerc`,
  `tests/test_coverage_command_contract.py`
- **Interfaces provided**: `make coverage`, `make coverage-baseline`,
  `make coverage-artifact-guard`, `agent-full coverage ownership`
- **Interfaces consumed**: `coverage-artifact-guard contract`, `pytest-cov`,
  `.coveragerc`, `make agent-* LOCALCI contract` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_coverage_command_contract.py` to assert coverage
    commands emit both `coverage.xml` and terminal missing-line output, do not
    add `--cov-fail-under=80` until a baseline decision exists, and keep
    `agent-full-local` or `agent-gate-local` as the owner of coverage
    generation.
  - test: Assert the guard is run by the cheap/gate path before expensive
    validation can pass with staged generated coverage files.
  - impl: Update `Makefile` so `coverage` uses
    `$(UV_RUN) --extra dev pytest` with `--cov=mcp_server`,
    `--cov-report=term-missing`, and `--cov-report=xml`, plus a baseline target
    that records the current local result without threshold enforcement.
  - impl: Add a `coverage-artifact-guard` target wired to
    `scripts/check_coverage_artifacts.py`, then include coverage generation in
    `agent-full-local` unless measurement proves `agent-gate-local` is cheap
    enough.
  - impl: Reconcile `.coveragerc` with the command contract without duplicating
    coverage configuration in `pyproject.toml` unless execution finds a real
    threshold source there.
  - verify: `uv run pytest tests/test_coverage_command_contract.py -q --no-cov`
  - verify: `make coverage-artifact-guard`
  - verify: `make coverage`

### SL-2 — Documentation And README Coverage Posture

- **Scope**: Replace stale hosted-first coverage examples with local/offloaded
  instructions and defer public badge claims until upload evidence exists.
- **Owned files**: `README.md`, `docs/development/TESTING-GUIDE.md`,
  `tests/docs/test_coverage_docs.py`
- **Interfaces provided**: `coverage docs contract`,
  `README badge deferral contract`
- **Interfaces consumed**: `make coverage`, `make coverage-baseline`,
  `agent-full coverage ownership`, `coverage-artifact-guard contract`
  (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_coverage_docs.py` to require docs for
    `make coverage`, baseline measurement, generated-artifact exclusion, and
    the rule that README badges require real uploaded evidence.
  - test: Require the testing guide to remove or clearly mark stale
    Codecov/upload snippets as non-default/manual-only until trusted upload
    evidence exists.
  - impl: Update `docs/development/TESTING-GUIDE.md` to point coverage users at
    the local/offloaded command contract and generated-artifact guard.
  - impl: Update `README.md` coverage instructions so they do not promise a
    badge or hosted upload before SL-3 and SL-4 prove it.
  - verify: `uv run pytest tests/docs/test_coverage_docs.py -q --no-cov`
  - verify: `rg -n "coverage|coverage.xml|htmlcov|Codecov|badge|agent-full|agent-gate" README.md docs/development/TESTING-GUIDE.md tests/docs/test_coverage_docs.py`

### SL-3 — Protected CI Coverage Posture

- **Scope**: Freeze the hosted CI behavior so coverage upload or badge evidence
  is trusted-event only, deferred, or absent, and ordinary pull requests keep
  consuming the existing agent contract.
- **Owned files**: `.github/workflows/ci-cd-pipeline.yml`,
  `tests/test_coverage_workflow_posture.py`, `tests/test_localci_workflow_posture.py`
- **Interfaces provided**: `trusted coverage workflow posture`
- **Interfaces consumed**: `make agent-gate`, `make agent-full`,
  `coverage docs contract`, `coverage-artifact-guard contract` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_coverage_workflow_posture.py` to assert ordinary
    `pull_request` jobs do not upload coverage, Codecov is absent or
    trusted-event/manual-only, and no hosted matrix expansion is introduced for
    COVERAGE.
  - test: Extend existing LOCALCI workflow posture checks only where needed to
    preserve the `make agent-gate` protected evidence contract while
    recognizing any coverage guard added by SL-1.
  - impl: Keep `.github/workflows/ci-cd-pipeline.yml` on the existing
    `make agent-gate` protected evidence path unless execution proves a
    trusted-event coverage upload is available without secrets or matrix
    expansion.
  - impl: If upload remains unproven, explicitly defer upload and badge
    evidence rather than adding a dead Codecov step.
  - verify: `uv run pytest tests/test_coverage_workflow_posture.py tests/test_localci_workflow_posture.py -q --no-cov`
  - verify: `rg -n "coverage|codecov|upload-artifact|pull_request|workflow_dispatch|make agent-" .github/workflows/ci-cd-pipeline.yml tests/test_coverage_workflow_posture.py tests/test_localci_workflow_posture.py`

### SL-4 — Coverage Evidence And Threshold Reducer

- **Scope**: Reduce command, guard, docs, workflow, and live baseline findings
  into metadata-only COVERAGE evidence and any required threshold-ramp roadmap
  amendment.
- **Owned files**: `docs/status/coverage-evidence.md`,
  `tests/docs/test_coverage_evidence_contract.py`, `specs/phase-plans-v9.md`
- **Interfaces provided**: `IF-0-COVERAGE-1 evidence`,
  `threshold ramp amendment decision`
- **Interfaces consumed**: `coverage-artifact-guard contract`,
  `agent-full coverage ownership`, `coverage docs contract`,
  `trusted coverage workflow posture` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_coverage_evidence_contract.py` to require audit
    date, baseline command, terminal missing-line summary, `coverage.xml`
    generation status, existing threshold posture, guard results, workflow
    upload/badge decision, and verification commands.
  - test: Require the evidence artifact to record either
    `--cov-fail-under=80 enforced` with baseline support or
    `threshold ramp deferred` with a roadmap amendment.
  - impl: Run the local/offloaded baseline once, capture metadata-only results
    in `docs/status/coverage-evidence.md`, and avoid committing
    `coverage.xml`, `.coverage*`, `coverage.json`, or `htmlcov/`.
  - impl: If baseline is below 80 percent or unstable, amend
    `specs/phase-plans-v9.md` with an explicit threshold-ramp note instead of
    forcing the 80 percent gate in this phase.
  - impl: If baseline supports 80 percent locally/offloaded, record the
    evidence and wire the fail-under gate only through the local/offloaded
    command path.
  - verify: `uv run pytest tests/docs/test_coverage_evidence_contract.py -q --no-cov`
  - verify: `make coverage-artifact-guard`
  - verify: `phase-loop validate-roadmap specs/phase-plans-v9.md`

### SL-5 — COVERAGE Acceptance Verification

- **Scope**: Run the phase acceptance suite and confirm generated coverage
  artifacts remain untracked and unstaged after fresh coverage generation.
- **Owned files**: none
- **Interfaces provided**: `COVERAGE acceptance verdict`
- **Interfaces consumed**: `IF-0-COVERAGE-1 evidence`,
  `threshold ramp amendment decision`, `trusted coverage workflow posture`,
  `coverage docs contract`, `coverage-artifact-guard contract` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the complete COVERAGE-specific test slice plus the roadmap
    validation command.
  - impl: No implementation writes; this lane is read-only verification and
    closeout evidence collection.
  - verify: `uv sync --locked --extra dev`
  - verify: `uv run pytest tests/test_coverage_command_contract.py tests/test_coverage_artifact_guard.py tests/test_coverage_workflow_posture.py tests/docs/test_coverage_docs.py tests/docs/test_coverage_evidence_contract.py -q --no-cov`
  - verify: `make coverage`
  - verify: `make coverage-artifact-guard`
  - verify: `make agent-full`
  - verify: `phase-loop validate-roadmap specs/phase-plans-v9.md`

## Execution Policy

- work-unit defaults: work-unit=`lane_execute`, effort=`medium`,
  unsupported=`inherit_default`, inherit-default=`true`
- SL-4: executor=`codex`, effort=`medium`, work-unit=`phase_reducer`,
  unsupported=`inherit_default`, inherit-default=`true`
- SL-5: executor=`codex`, effort=`medium`, work-unit=`phase_verify`,
  unsupported=`inherit_default`, inherit-default=`true`

## Execution Notes

- Use `uv sync --locked --extra dev` before running coverage or tests;
  `pyproject.toml` and `uv.lock` remain dependency truth.
- Treat `.coveragerc` as the current coverage configuration source unless
  execution discovers an existing threshold in another canonical config file.
- Run the first baseline without `--cov-fail-under=80`; enforcement is allowed
  only after the metadata-only evidence proves the local/offloaded gate
  supports it.
- Do not add Codecov tokens, GitHub secrets, self-hosted runner labels, or
  hosted matrix expansion in this phase.
- Generated coverage files are runtime outputs. They may exist locally after
  `make coverage`, but they must not be tracked, staged, or committed.
- If a README badge cannot point to a real uploaded report produced on a
  trusted event or manual dispatch, record badge deferral in docs and evidence.

## Acceptance Criteria

- [ ] `make coverage` emits `coverage.xml` and terminal missing-line output
      using the repo-local coverage configuration.
- [ ] `docs/status/coverage-evidence.md` records the measured baseline,
      existing threshold posture, and either supported `--cov-fail-under=80`
      enforcement or an explicit threshold-ramp roadmap amendment in
      `specs/phase-plans-v9.md`.
- [ ] `.gitignore` and `tests/test_coverage_artifact_guard.py` prove
      `coverage.xml`, `coverage.json`, `.coverage*`, and `htmlcov/` are
      generated-only artifacts that fail the guard when tracked or staged.
- [ ] `tests/test_coverage_workflow_posture.py` proves ordinary pull requests
      do not upload coverage or run a new hosted coverage matrix.
- [ ] `README.md`, `docs/development/TESTING-GUIDE.md`, and
      `tests/docs/test_coverage_docs.py` prove badge/upload claims are deferred
      unless real trusted upload evidence exists.
- [ ] `make agent-full` or `make agent-gate` owns coverage generation, and
      `make coverage-artifact-guard` passes after a fresh local coverage run
      without staging generated outputs.

## Verification

`automation.suite_command`: `make agent-full`

Lane-specific verification commands are listed under each lane. Whole-phase
verification:

```bash
uv sync --locked --extra dev
uv run pytest tests/test_coverage_command_contract.py tests/test_coverage_artifact_guard.py tests/test_coverage_workflow_posture.py tests/docs/test_coverage_docs.py tests/docs/test_coverage_evidence_contract.py -q --no-cov
make coverage
make coverage-artifact-guard
make agent-full
phase-loop validate-roadmap specs/phase-plans-v9.md
```

Next phase: COVERAGE - execution ready
Next command: codex-execute-phase plans/phase-plan-v9-COVERAGE.md
