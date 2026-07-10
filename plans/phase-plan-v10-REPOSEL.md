---
phase_loop_plan_version: 1
phase: REPOSEL
roadmap: specs/phase-plans-v10.md
roadmap_sha256: 7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e
---
# REPOSEL: Exact Repository Selection

## Context
Replace path-shaped guessing with one canonical selector resolver for repository ID, registered name, and registered path.

## Interface Freeze Gates
- [ ] IF-0-REPOSEL-1 — Exact registered selector contract.
- [ ] IF-0-REPOSEL-2 — No CWD fallback contract.

## Lane Index & Dependencies
SL-1 — Canonical resolver and registry contract
  Depends on: (none)
  Blocks: SL-2
  Parallel-safe: yes

SL-2 — MCP handler/schema adoption with cross-repository tests
  Depends on: SL-1
  Blocks: (none)
  Parallel-safe: yes

## Lanes

### SL-1 — Canonical resolver and registry contract
- **Scope**: Implement canonical selector resolver for repository ID, registered name, and registered path with exact precedence and no CWD fallback.
- **Owned files**: `mcp_server/core/repo_resolver.py`, `mcp_server/storage/repository_registry.py`, `mcp_server/health/repository_readiness.py`, `tests/test_repo_resolver.py`, `tests/test_repository_readiness.py`
- **Interfaces provided**: `RepoResolver.resolve`
- **Interfaces consumed**: none
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add unit tests for `RepoResolver` covering exact ID, name, path canonicalization, symlinks, nested paths, nonexistent relative paths, duplicate names/IDs, and sibling worktrees.
  - impl: Update `RepoResolver` and `RepositoryRegistry` to implement exact precedence without CWD fallback.
  - verify: `uv run pytest tests/test_repo_resolver.py -q --no-cov`

### SL-2 — MCP handler/schema adoption with cross-repository tests
- **Scope**: Adopt the new resolver in all MCP tools (search, symbol, summarize, reindex) and status surfaces, and update schemas.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `mcp_server/cli/stdio_runner.py`, `mcp_server/client.py`, `mcp_server/indexing/summarization.py`, `tests/test_tool_readiness_fail_closed.py`, `tests/integration/test_multi_repo_server.py`
- **Interfaces provided**: none
- **Interfaces consumed**: `RepoResolver.resolve`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add cross-repository tests to ensure selecting repo A cannot return results/storage from B, and tests for tool schema validation.
  - impl: Update `tool_handlers.py` and `stdio_runner.py` to use `RepoResolver.resolve` and update MCP tool schemas.
  - impl: Preserve `SummaryGenerationResult` as the typed result while exposing its generated summary items to the existing `summarize_sample` consumer; SUMCONTRACT remains responsible for the public response-schema freeze.
  - verify: `uv run pytest tests/test_tool_readiness_fail_closed.py tests/integration/test_multi_repo_server.py -q --no-cov`

## Verification
- Unit tests pass: `uv run pytest tests/test_repo_resolver.py tests/test_tool_readiness_fail_closed.py tests/integration/test_multi_repo_server.py -q --no-cov`
- Linter and type checking pass: `uv run mypy mcp_server/core/repo_resolver.py mcp_server/storage/repository_registry.py mcp_server/cli/tool_handlers.py mcp_server/cli/stdio_runner.py`

## Execution Notes
- Planning notes, explicit deferrals, and any metadata repairs needed before execution.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `MCP tool selector schemas and multi-repo docs`
- evidence paths: `resolver unit tests and two-repository integration output`
- redaction posture: `metadata_only`
- downstream handling: `roadmap amendment`

## Acceptance Criteria
- [ ] A shared resolver accepts exact repository ID, exact registered name, or a filesystem path that belongs to the registered checkout.
- [ ] Resolution precedence is exact ID, then exact registered name, then canonicalized path; collisions or residual ambiguity return a typed refusal.
- [ ] Paths use `realpath` canonicalization, preserve `MCP_ALLOWED_ROOTS`, compare git-common-dir identity, and reject sibling worktrees unless explicitly registered as the supported checkout.
- [ ] Unknown names, unknown IDs, unregistered paths, and unsupported worktrees return typed refusals and never fall back to the current repository.
- [ ] Tool schemas describe only selectors that are actually implemented.
- [ ] Path-shaped selectors continue enforcing `MCP_ALLOWED_ROOTS`; registered names do not bypass repository identity checks.
- [ ] Search, symbol, summarize, write-summary, and reindex tools use the same selector contract.
- [ ] Status and every repository-scoped diagnostic use the same resolver.
- [ ] Tests cover symlinks, nested paths, nonexistent relative paths, path-like repo names, duplicate names/IDs, and sibling worktrees.
- [ ] Two-repository tests prove selecting A cannot return results or storage from B.
