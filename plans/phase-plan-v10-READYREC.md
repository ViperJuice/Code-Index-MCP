---
phase_loop_plan_version: 1
phase: READYREC
roadmap: specs/phase-plans-v10.md
roadmap_sha256: 7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e
---

# READYREC: Readiness, Recovery, And Status Truth

## Context
Make readiness fail closed, let reindex repair only recoverable states, and make status claims agree with usable runtime components.

## Interface Freeze Gates
- [ ] IF-0-READYREC-1 — Fail-closed readiness state contract.
- [ ] IF-0-READYREC-2 — State-scoped reindex recovery contract.
- [ ] IF-0-READYREC-3 — Truthful status capability contract.

## Lane Index & Dependencies
SL-0 — Readiness Classifier and Storage Validation
  Depends on: (none)
  Blocks: SL-1, SL-2
  Parallel-safe: no

SL-1 — Locked Staged Recovery Mutation
  Depends on: SL-0
  Blocks: (none)
  Parallel-safe: no

SL-2 — Truthful Status and Integration
  Depends on: SL-0
  Blocks: (none)
  Parallel-safe: yes

## Lanes

### SL-0 — Readiness Classifier and Storage Validation
- **Scope**: Define strict fail-closed readiness classifications and quarantine states for indexes.
- **Owned files**: `mcp_server/health/repository_readiness.py`, `tests/fixtures/health_repo.py`, `tests/test_repo_resolver.py`, `tests/test_repository_readiness.py`
- **Interfaces provided**: IF-0-READYREC-1
- **Interfaces consumed**: IF-0-REPOSEL-1 (pre-existing), IF-0-REPOSEL-2 (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add fixtures for corrupt SQLite, missing schema, missing provenance, empty index, stale commit, wrong branch, and active build.
  - impl: Update classification logic to explicitly identify and isolate corrupt or unproven states from ready states, returning explicit manual quarantine-and-rebuild instructions when unsafe.
  - verify: Run `uv run pytest tests/test_repository_readiness.py -q`.

### SL-1 — Locked Staged Recovery Mutation
- **Scope**: Implement reindex recovery that explicitly repairs recoverable states through a staged temporary index.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: IF-0-READYREC-2
- **Interfaces consumed**: IF-0-READYREC-1
- **Parallel-safe**: no
- **Tasks**:
  - test: Add multi-thread lock simulation and failure injection (before/after replacement) tests.
  - impl: Implement per-repo reindex locking, temporary sibling index generation, atomic swap, and provenance recording in `git_index_manager.py`.
  - verify: Run `uv run pytest tests/test_git_index_manager.py -q`.

### SL-2 — Truthful Status and Integration
- **Scope**: Ensure status claims reflect actual usable runtime capabilities and agree with readiness health.
- **Owned files**: `mcp_server/cli/stdio_runner.py`, `mcp_server/cli/tool_handlers.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`, `tests/test_handler_path_sandbox.py`, `tests/test_health_surface.py`, `tests/test_tool_handlers_readiness.py`, `tests/test_tool_readiness_fail_closed.py`
- **Interfaces provided**: IF-0-READYREC-3
- **Interfaces consumed**: IF-0-READYREC-1
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add status feature flag validation tests simulating unavailable semantic backend and handler transition tests for recoverable and refused readiness states.
  - impl: Wire staged recovery through `stdio_runner.py` and `tool_handlers.py`; use `dispatcher_enhanced.py` runtime capability status so semantic active flags are true only when the indexer is reachable.
  - verify: Run `uv run pytest tests/test_handler_path_sandbox.py tests/test_health_surface.py tests/test_tool_readiness_fail_closed.py -q`.

## Verification
- Run full readiness tests: `uv run pytest tests/test_repository_readiness.py tests/test_tool_readiness_fail_closed.py -q`
- Run integration tests for status and recovery: `uv run pytest tests/test_git_index_manager.py -q`

## Execution Notes
- Ensure state names and typed error codes are explicitly defined before testing.
- The temporary-build publication protocol must guarantee atomic replacement.

## Acceptance Criteria
- [ ] Corrupt SQLite, missing schema, missing provenance, empty index, stale commit, wrong branch, active build, missing index, and ready index classify distinctly.
- [ ] Exceptions while opening or querying an index never classify it as non-empty or ready.
- [ ] `reindex` can bootstrap `missing_index` and `index_empty` and refresh `stale_commit` without first requiring `ready`.
- [ ] Corrupt SQLite, missing schema, and missing provenance can recover only via explicit quarantine-and-rebuild, preserving the prior bytes for diagnosis.
- [ ] Reindex still refuses wrong branch, unsupported worktree, active indexing, path-sandbox violations, and unregistered repositories.
- [ ] A per-repo reindex lock rejects or serializes concurrent rebuilds.
- [ ] Reindex builds and validates a sibling temporary index, atomically replaces the active index, then records matching provenance; any interrupted or mismatched generation remains non-ready.
- [ ] Failure injection before replacement, after replacement, and before provenance publication proves no corrupt generation can classify as `ready`.
- [ ] Every non-ready state advertises a remediation the implementation actually permits, including an explicit manual path when automatic recovery is unsafe.
- [ ] Semantic feature flags report active only when a usable semantic indexer is available and agree with health details.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `readiness enum/remediation, reindex schema, status schema`
- evidence paths: `readiness matrix tests and reindex transition tests`
- redaction posture: `metadata_only`
- downstream handling: `none`
