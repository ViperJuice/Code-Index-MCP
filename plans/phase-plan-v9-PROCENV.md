---
phase_loop_plan_version: 1
phase: PROCENV
roadmap: specs/phase-plans-v9.md
roadmap_sha256: 57848534176ac820595f4193459b86b5fdef9f5bfe5bff60a5739d8d9e192d2b
---
# PROCENV: Shared Subprocess Environment Helper

## Context

PROCENV is Phase 5 in `specs/phase-plans-v9.md`. The canonical
`.phase-loop/state.json` reports PUBNAME, REPOCLEAN, LOCALCI, and COVERAGE
complete, `PROCENV` current/unplanned, a clean worktree at runner reconciliation
time, and roadmap SHA-256
`57848534176ac820595f4193459b86b5fdef9f5bfe5bff60a5739d8d9e192d2b`.
Legacy `.codex/phase-loop/` files are compatibility artifacts only and are not
used to supersede the canonical `.phase-loop/` state.

Planning observations:

- `docs/status/localci-validation-contract.md` establishes the post-LOCALCI
  `make agent-*` validation contract; downstream verification should use
  `make agent-full` as the whole-phase suite when execution time allows.
- `docs/status/coverage-evidence.md` records the current local/offloaded
  coverage baseline at `17.31%`; PROCENV must not change coverage thresholds.
- Subprocess usage is currently scattered across `mcp_server/cli/`,
  `mcp_server/indexing/`, `mcp_server/watcher_multi_repo.py`,
  `mcp_server/health/repository_readiness.py`, `mcp_server/core/path_utils.py`,
  `mcp_server/core/preflight_validator.py`, and `scripts/agent_validation.py`.
- The subprocess calls that matter for this phase are command-discovery or
  tool-spawn paths for `git`, `mcp-index`, `sqlite3`, `make`, `ssh`, `dagger`,
  `uv`, `pytest`, `docker`, and equivalent local tools. Test-only process
  fixtures are not a product subprocess environment contract unless they are
  asserting that contract.
- Existing tests patch `subprocess.run` and `asyncio.create_subprocess_exec` in
  targeted modules; new PROCENV tests should preserve those patch points while
  proving the helper-provided `env` is passed where PATH/tool discovery matters.

Planning boundary:

- PROCENV may add a small helper module under `mcp_server/utils/`, route
  selected production subprocess call sites through it, add focused tests, and
  write a metadata-only evidence note.
- PROCENV must not rewrite every subprocess use in historical analysis scripts,
  introduce a broad process-runner abstraction, add shell-specific setup
  scripts, log raw environment values, mutate secrets, change coverage
  thresholds, or alter the public package identity contract.
- Existing command output may report command names, executable paths, boolean
  availability, return codes, and remediation text. It must not print raw env
  values or full secret-bearing command strings.

## Interface Freeze Gates

- [ ] IF-0-PROCENV-1 — Subprocess environment contract: `mcp_server/utils/subprocess_env.py::get_full_env()` returns a copy of the current environment with existing variables preserved; PATH entries are merged using the host OS path separator while preserving current PATH order, virtualenv entries, and common user tool directories for Linux, macOS, Windows, uv, npm, cargo, and local Python scripts; helper-provided env is used by indexing and server-adjacent subprocess calls that rely on `git`, `rg`, uv, npm, cargo, tree-sitter, `mcp-index`, `sqlite3`, `make`, `ssh`, or `dagger`; command availability reporting is metadata-only and includes remediation without printing raw environment values.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `no_spec_delta`
- target surfaces: `mcp_server/utils/subprocess_env.py`, `mcp_server/cli/index_commands.py`, `mcp_server/indexing/change_detector.py`, `mcp_server/indexing/incremental_indexer.py`, `mcp_server/watcher_multi_repo.py`, `mcp_server/health/repository_readiness.py`, `mcp_server/cli/artifact_commands.py`, `mcp_server/cli/preflight_commands.py`, `mcp_server/core/preflight_validator.py`, `mcp_server/core/path_utils.py`, `scripts/agent_validation.py`, `tests/`, `docs/status/procenv-subprocess-env.md`
- evidence paths: `docs/status/procenv-subprocess-env.md`, targeted subprocess environment test output
- redaction posture: `metadata_only`
- downstream handling: `none`

## Lane Index & Dependencies

SL-0 — Shared environment helper contract
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3, SL-4
  Parallel-safe: no
SL-1 — Indexing and git-state subprocess adoption
  Depends on: SL-0
  Blocks: SL-3, SL-4
  Parallel-safe: no
SL-2 — CLI, preflight, and validation subprocess adoption
  Depends on: SL-0
  Blocks: SL-3, SL-4
  Parallel-safe: no
SL-3 — PROCENV contract verification
  Depends on: SL-0, SL-1, SL-2
  Blocks: SL-4
  Parallel-safe: no
SL-4 — PROCENV evidence and docs reducer
  Depends on: SL-0, SL-1, SL-2, SL-3
  Blocks: (none)
  Parallel-safe: no

Lane DAG:

```text
SL-0 -> SL-1 -> SL-3 -> SL-4 -> PROCENV acceptance
SL-0 -> SL-2 -> SL-3
```

## Lanes

### SL-0 — Shared Environment Helper Contract

- **Scope**: Add the shared subprocess environment helper and freeze its PATH merge, virtualenv preservation, OS path separator, command metadata, and redaction semantics.
- **Owned files**: `mcp_server/utils/subprocess_env.py`, `tests/test_subprocess_env.py`
- **Interfaces provided**: `get_full_env`, `get_command_availability`, `get_full_env(base_env: Mapping[str, str] | None = None) -> dict[str, str]`, `get_command_availability(command: str, env: Mapping[str, str] | None = None) -> CommandAvailability`, metadata-only command availability contract
- **Interfaces consumed**: `os.environ` (pre-existing), `os.pathsep` (pre-existing), `Path.home()` (pre-existing), `VIRTUAL_ENV` (pre-existing), `CONDA_PREFIX` (pre-existing), `PYTHONPATH` (pre-existing), existing PATH order (pre-existing), platform-specific user tool path conventions (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_subprocess_env.py` cases for preserving arbitrary env vars, keeping existing PATH entries first, de-duplicating appended paths, respecting `os.pathsep`, preserving virtualenv and conda script paths, and adding common Linux/macOS/Windows user tool directories without requiring those directories to exist.
  - test: Cover uv, npm, cargo, and local Python script directory candidates using mocked home/platform inputs rather than host-specific assertions.
  - test: Cover metadata-only command availability so reported fields include command name, availability, resolved executable path when present, and remediation while excluding raw PATH, env values, and secret-looking strings.
  - impl: Add `mcp_server/utils/subprocess_env.py` with a small typed helper surface and no broad subprocess wrapper.
  - impl: Keep the helper pure and deterministic: it should build env dictionaries and availability metadata, not launch commands or mutate global `os.environ`.
  - verify: `uv run pytest tests/test_subprocess_env.py -q --no-cov`

### SL-1 — Indexing And Git-State Subprocess Adoption

- **Scope**: Route indexing, incremental git-state, watcher, and readiness subprocess calls through the shared env helper where external CLI discovery matters.
- **Owned files**: `mcp_server/cli/index_commands.py`, `mcp_server/indexing/change_detector.py`, `mcp_server/indexing/incremental_indexer.py`, `mcp_server/watcher_multi_repo.py`, `mcp_server/health/repository_readiness.py`, `tests/test_procenv_indexing_call_sites.py`, `tests/test_index_cli.py`, `tests/test_git_integration.py`, `tests/test_incremental_indexer.py`, `tests/test_watcher_multi_repo.py`, `tests/test_repository_readiness.py`
- **Interfaces provided**: indexing subprocess env adoption for `git` and `mcp-index`, watcher branch/commit subprocess env adoption, readiness git metadata env adoption
- **Interfaces consumed**: `get_full_env`, `get_command_availability`, existing `subprocess.run` (pre-existing) and `asyncio.create_subprocess_exec` (pre-existing) patch points, `ChangeDetector` (pre-existing), `IncrementalIndexer` (pre-existing), `MultiRepositoryWatcher` (pre-existing), `ReadinessClassifier` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_procenv_indexing_call_sites.py` to assert `CreateIndexCommand`, `SyncIndexCommand`, `ChangeDetector`, `IncrementalIndexer._get_repository_id`, `MultiRepositoryWatcher` branch/commit checks, and readiness git helpers pass helper-provided `env` into external command calls without changing command arguments.
  - test: Extend existing module tests only where their subprocess patch assertions need to accept the new `env` keyword.
  - impl: Import and use `get_full_env()` for `git` and `mcp-index` calls in `mcp_server/cli/index_commands.py` without changing command semantics.
  - impl: Use `get_full_env()` in `mcp_server/indexing/change_detector.py`, `mcp_server/indexing/incremental_indexer.py`, `mcp_server/watcher_multi_repo.py`, and `mcp_server/health/repository_readiness.py` for subprocess calls that rely on the local tool PATH.
  - impl: When command discovery fails, preserve existing fallback behavior but enrich non-secret error/remediation metadata only where an error is already surfaced.
  - verify: `uv run pytest tests/test_procenv_indexing_call_sites.py tests/test_index_cli.py tests/test_git_integration.py tests/test_incremental_indexer.py tests/test_watcher_multi_repo.py tests/test_repository_readiness.py -q --no-cov`

### SL-2 — CLI, Preflight, And Validation Subprocess Adoption

- **Scope**: Route CLI preflight, artifact git metadata, Python path discovery, dependency checks, and LOCALCI validation subprocess calls through the shared env helper without exposing raw environment values.
- **Owned files**: `mcp_server/cli/artifact_commands.py`, `mcp_server/cli/preflight_commands.py`, `mcp_server/core/preflight_validator.py`, `mcp_server/core/path_utils.py`, `scripts/agent_validation.py`, `tests/test_procenv_cli_call_sites.py`, `tests/test_artifact_commands.py`, `tests/test_preflight_commands.py`, `tests/test_preflight_validation.py`, `tests/test_scripts_pathutils.py`, `tests/test_agent_validation.py`
- **Interfaces provided**: CLI/preflight subprocess env adoption, metadata-only LOCALCI command reporting, Python executable discovery without shell-specific `which` dependence when standard-library alternatives suffice
- **Interfaces consumed**: `get_full_env`, `get_command_availability`, LOCALCI `agent-*` command contract (pre-existing), existing click runner tests (pre-existing), existing preflight and artifact helper contracts (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_procenv_cli_call_sites.py` to assert artifact git metadata helpers, preflight ahead/behind checks, preflight dependency checks, `PathUtils.get_python_executable`, and `scripts/agent_validation.py` command execution use helper env or standard-library command discovery.
  - test: Extend `tests/test_agent_validation.py` so doctor and offload output reports booleans and command names only, and does not echo raw `AGENT_REMOTE_HOST`, `AGENT_REMOTE_COMMAND`, PATH, or secret-looking env values.
  - impl: Use `get_full_env()` in `mcp_server/cli/artifact_commands.py` and `mcp_server/cli/preflight_commands.py` for git subprocess calls.
  - impl: Use `get_full_env()` in `mcp_server/core/preflight_validator.py` dependency checks, and convert `PathUtils.get_python_executable()` to helper-backed or `shutil.which` discovery so it does not rely on shell-specific `which` behavior.
  - impl: Update `scripts/agent_validation.py` so subprocess execution and explicit offload command checks use the shared helper or metadata helper while preserving LOCALCI fail-closed semantics.
  - impl: Redact or summarize command strings that may contain env-derived values; report command availability, selected mode, and remediation instead of raw environment values.
  - verify: `uv run pytest tests/test_procenv_cli_call_sites.py tests/test_artifact_commands.py tests/test_preflight_commands.py tests/test_preflight_validation.py tests/test_scripts_pathutils.py tests/test_agent_validation.py -q --no-cov`

### SL-3 — PROCENV Contract Verification

- **Scope**: Run the PROCENV-specific behavior suite and collect metadata-only command output for the terminal evidence reducer.
- **Owned files**: none
- **Interfaces provided**: targeted PROCENV test command output, `PROCENV acceptance pre-verdict`
- **Interfaces consumed**: `get_full_env`, `get_command_availability`, SL-1 indexing/git-state adoption evidence, SL-2 CLI/preflight/validation adoption evidence
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the complete PROCENV-specific test slice before evidence is reduced.
  - impl: No implementation writes; this lane is read-only verification and metadata collection for SL-4.
  - verify: `uv sync --locked --extra dev`
  - verify: `uv run pytest tests/test_subprocess_env.py tests/test_procenv_indexing_call_sites.py tests/test_procenv_cli_call_sites.py -q --no-cov`
  - verify: `make agent-full`

### SL-4 — PROCENV Evidence And Docs Reducer

- **Scope**: Reduce helper, adoption, redaction, verification, and roadmap results into metadata-only PROCENV evidence for IF-0-PROCENV-1.
- **Owned files**: `docs/status/procenv-subprocess-env.md`, `tests/docs/test_procenv_evidence_contract.py`
- **Interfaces provided**: `IF-0-PROCENV-1 evidence`, metadata-only subprocess environment proof, `docs/status/procenv-subprocess-env.md`, `PROCENV acceptance verdict`
- **Interfaces consumed**: `get_full_env`, `get_command_availability`, SL-1 indexing/git-state adoption evidence, SL-2 CLI/preflight/validation adoption evidence, targeted PROCENV test command output, `PROCENV acceptance pre-verdict`, roadmap non-goals (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_procenv_evidence_contract.py` to require audit date, phase plan reference, helper symbol path, OS path separator behavior, virtualenv preservation, indexed call-site adoption list, server-adjacent/preflight adoption list, redaction proof, no raw env value examples, verification commands, and explicit non-goal notes.
  - impl: Write `docs/status/procenv-subprocess-env.md` with metadata-only evidence from the targeted PROCENV tests and the call-site audit.
  - impl: Record a public-doc no doc change decision for README, CHANGELOG, and release notes because PROCENV changes internal subprocess environment behavior and produces its public-facing evidence only under `docs/status/`.
  - impl: Record that no shell setup script, broad subprocess wrapper, secret mutation, coverage threshold change, or hosted runner change was made.
  - verify: `uv run pytest tests/docs/test_procenv_evidence_contract.py -q --no-cov`
  - verify: `phase-loop validate-roadmap specs/phase-plans-v9.md`

## Execution Policy

- work-unit defaults: work-unit=`lane_execute`, effort=`medium`, unsupported=`inherit_default`, inherit-default=`true`
- SL-3: executor=`codex`, effort=`medium`, work-unit=`phase_verify`, unsupported=`inherit_default`, inherit-default=`true`
- SL-4: executor=`codex`, effort=`medium`, work-unit=`phase_reducer`, unsupported=`inherit_default`, inherit-default=`true`

## Execution Notes

- Use `uv sync --locked --extra dev` before running targeted tests;
  `pyproject.toml` and `uv.lock` remain dependency truth.
- Keep `get_full_env()` focused on environment construction. Do not create a
  generic subprocess runner in this phase.
- Preserve current subprocess command arguments and failure/fallback behavior
  unless the existing behavior prints raw environment data or hides actionable
  command availability metadata.
- Test-only fixtures that intentionally create custom env dictionaries may stay
  explicit; the required adoption surface is product indexing, CLI, preflight,
  validation, watcher, and readiness subprocess calls that rely on local tool
  discovery.
- `HISTORY` depends on PROCENV because it shells out to GitHub tooling; the
  evidence artifact should state whether `gh`-style future call sites can
  consume the same helper without live credentials in unit tests.
- Do not change coverage thresholds, hosted workflow matrices, package names,
  release dispatch behavior, GitHub secrets, or runner registration in this
  phase.

## Acceptance Criteria

- [ ] `mcp_server/utils/subprocess_env.py::get_full_env()` preserves existing
      environment variables, PATH order, virtualenv/conda paths, and OS path
      separator behavior while adding common user tool directories for Linux,
      macOS, Windows, uv, npm, cargo, and local Python scripts.
- [ ] `tests/test_subprocess_env.py` proves PATH merge, de-duplication,
      virtualenv preservation, Windows path separator behavior, and
      metadata-only command availability without relying on host-specific tools.
- [ ] Indexing and git-state subprocess call sites in `mcp_server/cli/`,
      `mcp_server/indexing/`, `mcp_server/watcher_multi_repo.py`, and
      `mcp_server/health/repository_readiness.py` pass helper-provided env for
      external command discovery while preserving existing commands and
      fallbacks.
- [ ] CLI, preflight, path utility, and `scripts/agent_validation.py` subprocess
      call sites use the helper or standard-library command discovery and do
      not print raw env values or secret-bearing command strings.
- [ ] `docs/status/procenv-subprocess-env.md` records metadata-only evidence for
      helper behavior, adoption call sites, redaction proof, verification
      commands, and non-goals.
- [ ] `make agent-full` and `phase-loop validate-roadmap specs/phase-plans-v9.md`
      pass without changing coverage thresholds, hosted workflow posture,
      package identity, or release behavior.

## Verification

`automation.suite_command`: `make agent-full`

Lane-specific verification commands are listed under each lane. Whole-phase
verification:

```bash
uv sync --locked --extra dev
uv run pytest tests/test_subprocess_env.py tests/test_procenv_indexing_call_sites.py tests/test_procenv_cli_call_sites.py tests/docs/test_procenv_evidence_contract.py -q --no-cov
uv run pytest tests/test_index_cli.py tests/test_git_integration.py tests/test_incremental_indexer.py tests/test_watcher_multi_repo.py tests/test_repository_readiness.py tests/test_artifact_commands.py tests/test_preflight_commands.py tests/test_preflight_validation.py tests/test_scripts_pathutils.py tests/test_agent_validation.py -q --no-cov
make agent-full
phase-loop validate-roadmap specs/phase-plans-v9.md
git status --short -- \
  mcp_server/utils/subprocess_env.py \
  mcp_server/cli/index_commands.py \
  mcp_server/indexing/change_detector.py \
  mcp_server/indexing/incremental_indexer.py \
  mcp_server/watcher_multi_repo.py \
  mcp_server/health/repository_readiness.py \
  mcp_server/cli/artifact_commands.py \
  mcp_server/cli/preflight_commands.py \
  mcp_server/core/preflight_validator.py \
  mcp_server/core/path_utils.py \
  scripts/agent_validation.py \
  tests/test_subprocess_env.py \
  tests/test_procenv_indexing_call_sites.py \
  tests/test_procenv_cli_call_sites.py \
  tests/docs/test_procenv_evidence_contract.py \
  docs/status/procenv-subprocess-env.md \
  plans/phase-plan-v9-PROCENV.md
```

Next phase: PROCENV - execution ready
Next command: codex-execute-phase plans/phase-plan-v9-PROCENV.md

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v9-PROCENV.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v9-PROCENV.md
  artifact_state: staged
```
