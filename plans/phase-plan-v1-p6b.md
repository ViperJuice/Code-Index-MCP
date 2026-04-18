# P6B: Documentation Alignment

## Context

Phases 1–5 are merged. The codebase now has a multi-repo model whose public surface the docs must accurately describe. Reconnaissance confirmed the ground-truth symbols and paths on `main`:

- `RepoContext` — frozen dataclass at `mcp_server/core/repo_context.py`.
- `StoreRegistry` — thread-safe, double-check pattern at `mcp_server/storage/store_registry.py`.
- `RepositoryRegistry.register_repository()` — `mcp_server/storage/repository_registry.py:245-297`.
- `compute_repo_id()` — `mcp_server/storage/repo_identity.py:69-112`. Tier 1 uses `git rev-parse --git-common-dir`, so worktrees of the same repo collapse to one `repo_id`.
- `MultiRepositoryWatcher` at `mcp_server/watcher_multi_repo.py` + `RefPoller` at `mcp_server/watcher/ref_poller.py:12-84` (default interval 30s).
- Path sandbox — uniform error code `path_outside_allowed_roots` across `search_code`, `symbol_lookup`, `summarize_sample`, `reindex`; `write_summaries` exempt. Gating predicate `_looks_like_path()` lives in `mcp_server/cli/tool_handlers.py` so registered repo *names* bypass the path check.
- `HandshakeGate` — `mcp_server/cli/handshake.py:15-61`, `MCP_CLIENT_SECRET` env var, `hmac.compare_digest`; startup logs `running unauthenticated — MCP_CLIENT_SECRET not set` when env unset.
- `initialize_stateless_services()` — `mcp_server/cli/bootstrap.py:25-64`.

Doc state on `main`:

- `AGENTS.md` (375 lines). Stale-claim zone: line 7 (`"95% Complete - NEAR PRODUCTION"`), line 9 (`"Production — 100% functional"`), lines 36-39 (`"All Implementation Complete (100%)"`), lines 188-201 (`"Phase 1 Status: 100% Complete (8/8 agents)"`). Preserve: lines 61-186 (MCP Search Strategy, Agent Constraints, Essential Commands), lines 255-309 (Code Style, Patterns, Naming, Environment).
- `README.md` (1203 lines). Stale multi-repo zones: lines 232-246 ("Using in Another Repo", single-repo framing) and lines 396-417 ("Same-Machine Multi-Repo Workflow", stub CLI-only, no `MCP_ALLOWED_ROOTS` or repo identity). Preserve: 1-114, 116-198, 285-376, 878-940.
- `CLAUDE.md` (30 lines) contains the self-instruction `"Do not modify this file directly. Add any updates to AGENTS.md."` → out of scope for edit; all agent guidance lives in `AGENTS.md`.
- `specs/active/architecture.md` (81 lines). Mermaid C4 at lines 1-45 (Context/Container) and 47-81 (Component). Missing: `RepoContext`, `StoreRegistry`, `RepositoryRegistry`, `MultiRepositoryWatcher`, `RefPoller`, `HandshakeGate`, path sandbox error. ~33% coverage of P5 architecture.
- MCP tool schemas in one function `_build_tool_list()` at `mcp_server/cli/stdio_runner.py:54-133`. Five `types.Tool` object literals, no shared helper, no test coupling on descriptions. `search_code` already has `repository` in its `inputSchema`; `symbol_lookup` accepts `repository` at handler level (`tool_handlers.py:97`) but does not advertise it in its schema. `reindex`, `summarize_sample` neither accept nor advertise `repository`. `write_summaries` is correctly exempt.

Architectural caveat to mention (not fix) in the dependability section of `architecture.md`: `EnhancedDispatcher.lookup()` falls through to `plugin.getDefinition()` for every registered language plugin when a symbol is absent from SQLite; the C plugin can hang in tree-sitter traversal on this fallback path. Surfaced in P5/SL-3. Out of scope for P6B.

## Interface Freeze Gates

- [ ] **IF-0-P6B-1** — Canonical post-refactor terminology & path-reference contract. All three lanes MUST use these exact identifiers and anchor paths (no synonyms, no renames): `RepoContext` (`mcp_server/core/repo_context.py`), `StoreRegistry` (`mcp_server/storage/store_registry.py`), `RepositoryRegistry.register_repository()` (`mcp_server/storage/repository_registry.py:245-297`), `compute_repo_id()` (`mcp_server/storage/repo_identity.py:69-112`), `MultiRepositoryWatcher` (`mcp_server/watcher_multi_repo.py`), `RefPoller` (`mcp_server/watcher/ref_poller.py:12-84`, default 30s), `HandshakeGate` (`mcp_server/cli/handshake.py:15-61`), `MCP_CLIENT_SECRET`, `MCP_ALLOWED_ROOTS`, `path_outside_allowed_roots` (error-code literal), `_looks_like_path()`, `initialize_stateless_services()` (`mcp_server/cli/bootstrap.py:25-64`). Freeze is sourced from the code on `main`; lanes consume it as `(pre-existing)` and never invent alternative spellings.

## Lane Index & Dependencies

```
SL-1 — Agent-facing docs rewrite
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-2 — Architecture C4 diagram refresh
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-3 — MCP tool schema descriptions
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes
```

## Lanes

### SL-1 — Agent-facing docs rewrite

- **Scope**: Rewrite `AGENTS.md` and `README.md` so they match post-refactor reality: delete overstated readiness claims, add a multi-repo operator section covering registered-repo identity (repo_id Tier 1 via `git rev-parse --git-common-dir`, worktree collapse), default-branch policy, `MCP_ALLOWED_ROOTS` path sandbox, `MCP_CLIENT_SECRET` handshake, and concrete "use against many repos" setup steps. `CLAUDE.md` (30 lines) is untouched because the file itself forbids direct edits and redirects to `AGENTS.md`.
- **Owned files**: `AGENTS.md`, `README.md`, `tests/docs/test_p6b_sl1.py` (new).
- **Interfaces provided**: (none) — doc-only lane.
- **Interfaces consumed**: `IF-0-P6B-1` (pre-existing) — terminology contract sourced from code on `main`.
- **Execution hint**: `claude-sonnet-4-6` / medium — prose-heavy rewrite with deterministic substring-assertion tests.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/docs/test_p6b_sl1.py` | Absence of strings `"100% production-ready"`, `"Phase 1 8/8"`, `"NEAR PRODUCTION"`, `"100% functional"`, `"All Implementation Complete"` anywhere in `AGENTS.md`. Presence in `AGENTS.md` of: `RepoContext`, `StoreRegistry`, `compute_repo_id`, `MultiRepositoryWatcher`, `MCP_ALLOWED_ROOTS`, `MCP_CLIENT_SECRET`, `path_outside_allowed_roots`, and a section heading whose text contains the words `multi-repo` (case-insensitive). Presence in `README.md` of: a section heading containing the words `many repos` or `multi-repo` (case-insensitive), plus `MCP_ALLOWED_ROOTS` and `repository register` somewhere under that heading. | `pytest tests/docs/test_p6b_sl1.py -v` |
| SL-1.2 | impl | SL-1.1 | `AGENTS.md`, `README.md` | — | — |
| SL-1.3 | verify | SL-1.2 | `AGENTS.md`, `README.md`, `tests/docs/test_p6b_sl1.py` | all SL-1 tests | `pytest tests/docs/test_p6b_sl1.py -v` |

### SL-2 — Architecture C4 diagram refresh

- **Scope**: Rewrite the Mermaid C4 diagrams in `specs/active/architecture.md` so the Container and Component levels show `RepoContext`, `StoreRegistry`, `RepositoryRegistry`, `MultiRepositoryWatcher`, `RefPoller`, `HandshakeGate`, and the `path_outside_allowed_roots` sandbox boundary. Add a short dependability subsection flagging the `EnhancedDispatcher.lookup()` → C-plugin tree-sitter fallback hang as a known caveat (one paragraph; no code change). Preserve H2/H3 anchor slugs so downstream references survive.
- **Owned files**: `specs/active/architecture.md`, `tests/docs/test_p6b_sl2.py` (new).
- **Interfaces provided**: (none) — doc-only lane.
- **Interfaces consumed**: `IF-0-P6B-1` (pre-existing) — terminology contract sourced from code on `main`.
- **Execution hint**: `claude-sonnet-4-6` / medium — Mermaid C4 edits; verify renders by eye after impl.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/docs/test_p6b_sl2.py` | `specs/active/architecture.md` contains a fenced ` ```mermaid ` block whose body includes the node identifiers `RepoContext`, `StoreRegistry`, `RepositoryRegistry`, `MultiRepositoryWatcher`, `RefPoller`, `HandshakeGate`. File contains the string `path_outside_allowed_roots`. File contains a dependability note mentioning `EnhancedDispatcher` and `tree-sitter`. | `pytest tests/docs/test_p6b_sl2.py -v` |
| SL-2.2 | impl | SL-2.1 | `specs/active/architecture.md` | — | — |
| SL-2.3 | verify | SL-2.2 | `specs/active/architecture.md`, `tests/docs/test_p6b_sl2.py` | all SL-2 tests | `pytest tests/docs/test_p6b_sl2.py -v` |

### SL-3 — MCP tool schema descriptions

- **Scope**: Inside `_build_tool_list()` at `mcp_server/cli/stdio_runner.py:54-133`, update each tool's `description` string so it accurately describes the `repository=` parameter semantics, path sandbox behavior (uniform error code `path_outside_allowed_roots`), and handshake requirement (when `MCP_CLIENT_SECRET` is set). Add a `repository` property to `symbol_lookup`'s `inputSchema.properties` because the handler at `mcp_server/cli/tool_handlers.py:97` already accepts it — the schema is the MCP contract and currently misrepresents the handler. Do NOT add `repository` to `reindex` or `summarize_sample` (their handlers do not accept it — code change out of scope). Do NOT touch `tool_handlers.py`, any default values, required-fields, or anything outside the schema-literal region.
- **Owned files**: `mcp_server/cli/stdio_runner.py`, `tests/docs/test_p6b_sl3.py` (new).
- **Interfaces provided**: (none) — no new exported symbols.
- **Interfaces consumed**: `_build_tool_list` (pre-existing), `tool_handlers` (pre-existing), `IF-0-P6B-1` (pre-existing) — terminology contract sourced from code on `main`.
- **Execution hint**: `claude-sonnet-4-6` / medium — surgical string edits inside one function; impl-side behavior untouched.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/docs/test_p6b_sl3.py` | Import `_build_tool_list` from `mcp_server.cli.stdio_runner`; for each tool in the returned list assert that the `description` string matches these rules: `search_code.description` contains `repository` AND `path_outside_allowed_roots`; `symbol_lookup.description` contains `repository` AND `path_outside_allowed_roots`; `reindex.description` contains `path_outside_allowed_roots` AND `MCP_ALLOWED_ROOTS`; `summarize_sample.description` contains `path_outside_allowed_roots`; `write_summaries.description` is unchanged w.r.t. path sandbox (does not claim sandbox applies); `handshake.description` mentions `MCP_CLIENT_SECRET`. Additionally assert that `symbol_lookup.inputSchema['properties']` contains a key `repository`. | `pytest tests/docs/test_p6b_sl3.py -v` |
| SL-3.2 | impl | SL-3.1 | `mcp_server/cli/stdio_runner.py` | — | — |
| SL-3.3 | verify | SL-3.2 | `mcp_server/cli/stdio_runner.py`, `tests/docs/test_p6b_sl3.py` | all SL-3 tests + smoke of existing stdio tests | `pytest tests/docs/test_p6b_sl3.py tests/test_*stdio*.py -v` |

## Execution Notes

- **Single-writer files**: none. Lanes own fully disjoint paths: SL-1 owns `AGENTS.md` + `README.md`; SL-2 owns `specs/active/architecture.md`; SL-3 owns `mcp_server/cli/stdio_runner.py`. Each lane owns its own new test file under `tests/docs/`. No barrel indexes, generated types, routers, or package-init files are touched.
- **Known destructive changes**: SL-1 deletes the stale-claim lines inside `AGENTS.md` (line 7, line 9, lines 36-39, lines 188-201) and rewrites the stale multi-repo sections of `README.md` (lines 232-246 and 396-417) — these deletions are expected and whitelisted. SL-2 rewrites the Mermaid C4 blocks in `specs/active/architecture.md`. No other deletions.
- **Expected add/add conflicts**: none — no SL-0 preamble, no shared file.
- **SL-0 preamble**: none. No lane adds, modifies, or exposes any package-init symbol; no package-init files are touched at all.
- **CLAUDE.md policy**: The repo-level `CLAUDE.md` contains a self-instruction forbidding direct edits and pointing agents to `AGENTS.md`. P6B respects that: no lane touches `CLAUDE.md`. The spec's "CLAUDE.md usage hints" exit-criterion item is satisfied via the multi-repo sections added to `AGENTS.md` by SL-1.
- **SL-3 scope boundary**: SL-3 edits are restricted to the `_build_tool_list()` region (`mcp_server/cli/stdio_runner.py:54-133`): description strings and adding `repository` to `symbol_lookup.inputSchema.properties` because the handler already accepts it. Any edit to `tool_handlers.py`, any change to required fields or default values, or adding `repository` to tools whose handlers do not accept it (`reindex`, `summarize_sample`) is out of scope and must be rejected during review.
- **Terminology discipline**: All three lanes use the exact identifiers and paths from IF-0-P6B-1. If a lane finds the canonical name/path on `main` differs from the freeze (e.g., discovers `repo_identity.py` lives under `mcp_server/repository/` instead of `mcp_server/storage/`), the lane MUST stop and report — do not substitute a guess.
- **Worktree naming**: execute-phase allocates unique worktree names via `scripts/allocate_worktree_name.sh`. Plan doc does not spell out lane worktree paths.
- **Stale-base guidance**: Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. Since all three lanes are DAG roots and touch disjoint files, staleness is not a merge hazard here — but the rule still applies: if a lane finds its worktree base is pre-P5 merge (`648054c`), it MUST stop and report rather than committing; the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.

## Acceptance Criteria

- [ ] `pytest tests/docs/test_p6b_sl1.py::test_no_stale_claims -v` — `AGENTS.md` contains none of the strings `100% production-ready`, `Phase 1 8/8`, `NEAR PRODUCTION`, `100% functional`, `All Implementation Complete`.
- [ ] `pytest tests/docs/test_p6b_sl1.py::test_agents_multi_repo_section -v` — `AGENTS.md` contains the literal tokens `RepoContext`, `StoreRegistry`, `compute_repo_id`, `MultiRepositoryWatcher`, `MCP_ALLOWED_ROOTS`, `MCP_CLIENT_SECRET`, `path_outside_allowed_roots`, plus a heading whose text (case-insensitive) contains `multi-repo`.
- [ ] `pytest tests/docs/test_p6b_sl1.py::test_readme_many_repos_section -v` — `README.md` contains a heading (case-insensitive) matching `many repos` or `multi-repo`, and under that heading contains both `MCP_ALLOWED_ROOTS` and `repository register`.
- [ ] `pytest tests/docs/test_p6b_sl2.py::test_architecture_c4_nodes -v` — `specs/active/architecture.md` contains a fenced ```` ```mermaid ```` block whose body includes each of the node identifiers `RepoContext`, `StoreRegistry`, `RepositoryRegistry`, `MultiRepositoryWatcher`, `RefPoller`, `HandshakeGate`.
- [ ] `pytest tests/docs/test_p6b_sl2.py::test_architecture_sandbox_and_caveat -v` — `specs/active/architecture.md` contains the literal `path_outside_allowed_roots` and a dependability note containing both `EnhancedDispatcher` and `tree-sitter`.
- [ ] `pytest tests/docs/test_p6b_sl3.py::test_tool_descriptions -v` — calling `_build_tool_list()` returns tools whose `description` fields satisfy: `search_code` mentions `repository` and `path_outside_allowed_roots`; `symbol_lookup` mentions `repository` and `path_outside_allowed_roots`; `reindex` mentions `path_outside_allowed_roots` and `MCP_ALLOWED_ROOTS`; `summarize_sample` mentions `path_outside_allowed_roots`; `handshake` mentions `MCP_CLIENT_SECRET`.
- [ ] `pytest tests/docs/test_p6b_sl3.py::test_symbol_lookup_schema_has_repository -v` — the `symbol_lookup` tool's `inputSchema['properties']` dict contains a key `repository`.
- [ ] `pytest tests/docs/test_p6b_sl3.py::test_write_summaries_sandbox_claim -v` — the `write_summaries` tool's `description` does NOT claim the path sandbox applies (string `path_outside_allowed_roots` absent from that tool's description).

## Verification

```bash
# After all three lanes merge, run the full P6B test suite.
pytest tests/docs/ -v

# Smoke-check existing stdio runner unit tests still pass (SL-3 edits inside _build_tool_list).
pytest tests/test_*stdio*.py -v

# Mermaid render sanity (manual — GitHub renders Mermaid natively).
git show HEAD:specs/active/architecture.md | head -120
```

Exit criteria from spec map 1:1 to acceptance criteria above:
- AGENTS.md no longer claims 100% production-ready / Phase 1 8/8 → `test_no_stale_claims`.
- AGENTS.md describes multi-repo model, repo identity, default-branch policy, `MCP_ALLOWED_ROOTS`, registry-based auth → `test_agents_multi_repo_section`.
- README.md has "how to use against many repos" with concrete setup → `test_readme_many_repos_section`.
- `specs/active/architecture.md` C4 shows `RepoContext` + `StoreRegistry` + `MultiRepoWatcher` → `test_architecture_c4_nodes`.
- MCP tool JSON schemas mention `repository=` parameter semantics accurately → `test_tool_descriptions` + `test_symbol_lookup_schema_has_repository`.
