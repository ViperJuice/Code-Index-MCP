---
phase_loop_plan_version: 1
phase: QUALITY
roadmap: specs/phase-plans-v10.md
roadmap_sha256: 7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e
---

# QUALITY: Quality Gate Recovery

## Context
Restore deterministic local release gates from a fresh `uv sync --locked --extra dev` environment, fix current behavioral failures, and ratchet the unbounded full-project type backlog while bringing release-critical modules to zero.

Entry census from commit `14a833c`:
- `uv sync --locked --extra dev --link-mode=copy`: passed; undeclared optional provider/ML packages were removed.
- Black: 60 of 745 Python files require formatting.
- isort: 25 files require import normalization.
- flake8: 6 findings (`E122` x2; `E302`, `E305`, `E306`, `F401` x1 each).
- pylint: canonical `--fail-under=7.0` passes at 8.84/10 with 4,599 messages.
- full mypy: 1,610 errors; top codes are `assignment` 263, `attr-defined` 259, `arg-type` 241, `no-any-return` 157, and `union-attr` 123.
- release-critical mypy target with `--follow-imports=skip`: 60 errors across summarization 17, security 14, artifacts 19, CLI handlers 3, artifact CLI 2, plugin lifecycle 4, and readiness 1.
- `make alpha-unit-release-smoke`: 2,524 passed, 140 skipped, 23 failed, and 1 setup error before release smoke.

## Interface Freeze Gates
- [ ] IF-0-QUALITY-1 — `make alpha-release-gates` and the documented local gate run from a clean locked environment without unmarked network access or hosted-PR compute expansion.
- [ ] IF-0-QUALITY-2 — Release-critical modules type-check at zero and the committed full-project mypy census can only shrink; new modules/errors and blanket `ignore_errors` fail validation.

## Lane Index & Dependencies
SL-0 — Documentation and schema contract repair
  Depends on: (none)
  Blocks: SL-3, SL-4
  Parallel-safe: yes

SL-1 — Deterministic runtime and hermetic fixture repair
  Depends on: (none)
  Blocks: SL-2, SL-3, SL-4
  Parallel-safe: yes

SL-2 — Critical typing zero and full-project ratchet
  Depends on: SL-1
  Blocks: SL-3, SL-4
  Parallel-safe: no

SL-3 — Mechanical format and lint recovery
  Depends on: SL-0, SL-1, SL-2
  Blocks: SL-4
  Parallel-safe: no

SL-4 — Local release-gate verification and documentation
  Depends on: SL-0, SL-1, SL-2, SL-3
  Blocks: (none)
  Parallel-safe: no

## Lanes

### SL-0 — Documentation and schema contract repair
- **Scope**: Reconcile stale documentation/schema tests with the exact selector, JWT boundary, PMCP pilot evidence, and current schema contract proven by prior phases.
- **Owned files**: `docs/validation/mcp-auth-boundary.md`, `docs/status/HISTORICAL_TRIAGE_LOG.md`, `docs/status/PMCP_FLEET_PILOT.md`, `tests/docs/test_mcpauth_surface_alignment.py`, `tests/docs/test_p8_historical_sweep.py`, `tests/docs/test_p7_schema_alignment.py`, `tests/test_schema_migration.py`
- **Interfaces provided**: none
- **Interfaces consumed**: IF-0-AUTHBOUND-1 (pre-existing), IF-0-REPOSEL-1 (pre-existing), IF-0-READYREC-1 (pre-existing)
- **Parallel-safe**: yes
- **Tasks**:
  - test: Prove the selector description requires exact registered ID/name/path with no CWD fallback, and retain the separate local STDIO handshake wording.
  - docs: Add the four PMCP pilot evidence paths to the historical triage union with current dispositions.
  - test: Update compatible-schema fixtures to construct the required schema/provenance contract rather than accepting an empty SQLite file.
  - verify: Run the four affected documentation/schema test modules with `--no-cov`.

### SL-1 — Deterministic runtime and hermetic fixture repair
- **Scope**: Fix the 23 behavioral failures and setup error without weakening readiness, selector, auth, or summarization contracts; deny unmarked default-suite network access.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/cli/tool_handlers.py`, `mcp_server/storage/multi_repo_manager.py`, `mcp_server/gateway.py`, `tests/conftest.py`, `tests/test_artifact_commands.py`, `tests/test_dispatcher_toctou.py`, `tests/test_mcp_server_cli.py`, `tests/test_multi_repo_manager.py`, `tests/test_multi_repo_artifact_coordinator.py`, `tests/test_repository_commands.py`, `tests/test_multi_repo_failure_matrix.py`, `tests/test_startup_preflight.py`, `tests/smoke/test_secondary_tool_readiness_smoke.py`, `tests/test_gateway_auth_boundary.py`
- **Interfaces provided**: none
- **Interfaces consumed**: IF-0-READYREC-1 (pre-existing), IF-0-SUMCONTRACT-1 (pre-existing), IF-0-PLUGLIFE-1 (pre-existing)
- **Parallel-safe**: yes
- **Tasks**:
  - test: Replace stale list-return, implicit-CWD, empty-file readiness, and nonexistent absolute-path fixtures with typed summaries, explicit contexts, valid SQLite/provenance, and temporary repositories.
  - impl: Preserve injected-plugin authority in guarded indexing and retain repository context in CLI compatibility paths without reintroducing selector fallback.
  - test: Make gateway preflight/auth fixtures provide valid JWT configuration before injecting their intended sentinel and isolate index-discovery paths under `tmp_path`.
  - test: Add an autouse socket guard that denies network for unmarked tests; mark only intentional bounded local-server/network tests with `requires_network`.
  - verify: Rerun every failed node from the entry inventory, then `make alpha-unit-release-smoke`.

### SL-2 — Critical typing zero and full-project ratchet
- **Scope**: Eliminate the 60 direct errors in release-critical modules and enforce a generated full-project baseline that cannot grow.
- **Owned files**: `mcp_server/security/**`, `mcp_server/health/repository_readiness.py`, `mcp_server/indexing/summarization.py`, `mcp_server/plugins/memory_aware_manager.py`, `mcp_server/plugins/plugin_set_registry.py`, `mcp_server/plugins/sandboxed_plugin.py`, `mcp_server/sandbox/supervisor.py`, `mcp_server/cli/artifact_commands.py`, `mcp_server/artifacts/**`, `scripts/check_mypy_baseline.py`, `config/mypy_baseline.json`, `tests/test_mypy_baseline.py`, `Makefile`, `pyproject.toml`
- **Interfaces provided**: IF-0-QUALITY-2
- **Interfaces consumed**: IF-0-SUMCONTRACT-1 (pre-existing), IF-0-PLUGLIFE-1 (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - impl: Fix concrete annotations, unions, typed dictionaries, and return contracts in the target set without blanket ignores or runtime behavior changes.
  - tooling: Add a structured baseline keyed by module and mypy code plus a checker that rejects count growth, new excluded modules, malformed output, and project-level `ignore_errors`.
  - test: Add ratchet self-tests covering shrink, growth, new module, new code, and blanket-ignore rejection.
  - verify: Run target mypy with `--follow-imports=skip` at zero, full mypy through the ratchet, and the checker tests.

### SL-3 — Mechanical format and lint recovery
- **Scope**: Apply Black/isort to the entry-census paths after semantic edits, fix the six flake8 findings, and preserve the passing pylint threshold.
- **Owned files**: `the 60 Black and 25 isort entry-census Python paths not otherwise owned above (mechanical edits only)`
- **Interfaces provided**: none
- **Interfaces consumed**: none
- **Parallel-safe**: no
- **Tasks**:
  - format: Run canonical Black and isort over `mcp_server tests` after all behavioral/type edits.
  - impl: Fix the six remaining flake8 findings without suppressions.
  - verify: Run `make alpha-format-lint` and confirm pylint remains at or above 7.0.

### SL-4 — Local release-gate verification and documentation
- **Scope**: Run the full local quality story, document fast/gate/full commands and hermetic policy, and prove hosted per-PR compute is unchanged.
- **Owned files**: `docs/development/TESTING-GUIDE.md`, `tests/test_localci_workflow_posture.py`, `tests/docs/test_localci_validation_contract.py`
- **Interfaces provided**: IF-0-QUALITY-1
- **Interfaces consumed**: IF-0-QUALITY-2
- **Parallel-safe**: no
- **Tasks**:
  - docs: Record locked-environment setup, fast/gate/full local commands, network markers, type ratchet behavior, and artifact locations.
  - test: Assert the GitHub PR workflow does not invoke the expanded local release gate or add hosted matrix jobs.
  - verify: Run `make alpha-release-gates`, the full non-benchmark suite from a clean worktree, release smoke, and repo-clean audit.

## Verification
- `uv sync --locked --extra dev --link-mode=copy`.
- `make alpha-format-lint`.
- Critical target mypy at zero plus `scripts/check_mypy_baseline.py` against full-project output.
- `make alpha-unit-release-smoke`, `make alpha-integration-smoke`, `make alpha-docs-truth`, and `make alpha-production-matrix`.
- Full non-benchmark `pytest tests --benchmark-skip --no-cov` with only explicit external-resource skips.
- `git diff --check`, `git status --short`, and workflow-posture tests.

## Execution Notes
- Full-project mypy zero is explicitly out of bounds at 1,610 entry errors; the ratchet is required and must enumerate every current module/code count.
- Formatting is intentionally terminal and mechanical so behavioral diffs remain reviewable first.
- Default tests may use temporary Unix sockets or explicitly marked bounded local HTTP servers; all other socket connections fail.
- No GitHub workflow may add hosted per-PR compute in this phase.
- README, CHANGELOG, and release notes have no delta: this phase repairs internal validation policy and does not dispatch or prepare a release.
- No external release, tag, package publish, or hosted workflow is dispatched in this phase.

## Acceptance Criteria
- [ ] The 24 entry behavioral/setup failures pass in targeted reruns and `make alpha-unit-release-smoke` completes release smoke.
- [ ] Black, isort, flake8, and pylint pass through `make alpha-format-lint`.
- [ ] Critical target mypy reports zero errors and `tests/test_mypy_baseline.py` proves the full-project ratchet rejects growth/new modules/new codes/blanket ignores.
- [ ] The full non-benchmark suite passes with unmarked socket access denied.
- [ ] `make alpha-release-gates` and local workflow-posture tests pass without adding hosted PR compute.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `local validation contract, hermetic test policy, and production type-check ratchet`
- evidence paths: `entry census in this plan, alpha release-gate output, mypy baseline, and testing guide`
- redaction posture: `metadata_only`
- downstream handling: `none`
- blocker_class: repeated_verification_failure after one diagnosed repair rerun
