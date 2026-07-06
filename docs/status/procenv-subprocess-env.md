# PROCENV Subprocess Environment Evidence

Audit date: 2026-07-06
Phase plan: `plans/phase-plan-v9-PROCENV.md`
Helper symbol: `mcp_server/utils/subprocess_env.py::get_full_env`

## Contract Summary

`get_full_env()` returns a copy of the current environment, preserves existing
variables, keeps existing PATH entries first, de-duplicates appended entries,
and appends common subprocess discovery paths for virtualenv, conda, user-local
Python scripts, cargo, npm, and platform-specific home-directory tools.

## Helper Behavior

- OS path separator behavior: PATH merging uses the host path separator and the
  tests exercise both `:` and `;` forms.
- Virtualenv and conda preservation: `VIRTUAL_ENV` and `CONDA_PREFIX` script
  directories are appended without mutating the input environment.
- Command availability metadata: `get_command_availability()` reports command
  name, boolean availability, resolved executable path when found, and
  remediation text.

## Indexed call-site adoption

- `mcp_server/cli/index_commands.py`
- `mcp_server/indexing/change_detector.py`
- `mcp_server/indexing/incremental_indexer.py`
- `mcp_server/watcher_multi_repo.py`
- `mcp_server/health/repository_readiness.py`

## Server-adjacent and preflight adoption

- `mcp_server/cli/artifact_commands.py`
- `mcp_server/cli/preflight_commands.py`
- `mcp_server/core/preflight_validator.py`
- `mcp_server/core/path_utils.py`
- `scripts/agent_validation.py`

## Redaction proof

No raw environment values are printed in this evidence note. The LOCALCI helper
now emits `selected_mode`, `selected_target`, `command_name`, and
`command_redacted=true` instead of echoing remote commands or env-derived
payloads.

## Verification commands

- `uv sync --locked --extra dev`
- `uv run pytest tests/test_subprocess_env.py tests/test_procenv_indexing_call_sites.py tests/test_procenv_cli_call_sites.py -q --no-cov`
- `uv run pytest tests/test_index_cli.py tests/test_git_integration.py tests/test_incremental_indexer.py tests/test_watcher_multi_repo.py tests/test_repository_readiness.py tests/test_artifact_commands.py tests/test_preflight_commands.py tests/test_preflight_validation.py tests/test_scripts_pathutils.py tests/test_agent_validation.py tests/docs/test_procenv_evidence_contract.py -q --no-cov`
- `make agent-full`
- `phase-loop validate-roadmap specs/phase-plans-v9.md`

## Non-goals confirmed

- No shell setup script was added.
- No broad subprocess runner abstraction was added.
- No secret mutation was introduced.
- No coverage threshold was changed.
- No hosted runner or release behavior was changed.

README/CHANGELOG decision: no public doc delta because PROCENV changes internal
subprocess environment handling and records its public-facing evidence in
`docs/status/`.
