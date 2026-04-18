# P9: Operational Scoping Completion

## Context

P7 added `repository=` to the input schemas of five MCP tools (`symbol_lookup`, `search_code`, `reindex`, `write_summaries`, `summarize_sample`) and rewired `symbol_lookup` and `search_code` to resolve a `RepoContext` via `RepoResolver` and route through the per-repo `SQLiteStore`. Three operational handlers were left behind: `handle_reindex`, `handle_write_summaries`, and `handle_summarize_sample` in `mcp_server/cli/tool_handlers.py` still ignore `arguments["repository"]` and use the process-wide `sqlite_store` kwarg from `stdio_runner.py`. This means a client calling `reindex(repository="repo-b")` silently reindexes whatever repo `MCP_WORKSPACE_ROOT` points at — a correctness gap that breaks multi-repo deployments.

Secondary gap: `tests/test_requirements_consolidation.py:10` does a bare `import tomllib`, which only works on Python ≥3.11. Workstation venvs on 3.10 can't run the full test suite. Fix is a `try: import tomllib except ImportError: import tomli as tomllib` guard plus a conditional `tomli>=2.0.1; python_version<"3.11"` test dep in `pyproject.toml`.

Third artifact: a new `tests/test_tool_schema_handler_parity.py` that asserts every tool whose `_build_tool_list()` schema advertises `repository` has a handler accepting the kwarg, and vice-versa. This is the lock that prevents the gap from silently re-opening.

## Interface Freeze Gates

- [ ] IF-0-P9-1 — Handler signature contract: `handle_reindex`, `handle_write_summaries`, `handle_summarize_sample` in `mcp_server/cli/tool_handlers.py` each extract `repository = (arguments or {}).get("repository")`, call `_resolve_ctx(repo_resolver, repository or path)`, and route all `SQLiteStore` reads/writes through `ctx.sqlite_store` (falling back to the `sqlite_store` kwarg only when `ctx is None`).
- [ ] IF-0-P9-2 — Structured error for inconsistent `path` + `repository` in `handle_reindex`: when both are provided and `RepoResolver.resolve(Path(path)).repo_id` differs from the ctx resolved for `repository`, return `{"error": "Conflicting scope", "code": "conflicting_path_and_repository", "path": ..., "repository": ..., "hint": "Provide only one, or ensure both resolve to the same repo."}`. No silent reinterpretation.
- [ ] IF-0-P9-3 — Tool-list registry contract: `mcp_server/cli/stdio_runner._build_tool_list()` remains the single source of truth for tool schemas. The parity test imports and calls it directly — no new registry data structure introduced.
- [ ] IF-0-P9-4 — `tomllib` import guard pattern: `tests/test_requirements_consolidation.py` uses `try: import tomllib\nexcept ImportError: import tomli as tomllib` at the top. Same pattern is applied anywhere else under `tests/` that bare-imports `tomllib` (currently none, but this freezes the convention).

## Lane Index & Dependencies

```
SL-1 — Handler scoping (reindex / write_summaries / summarize_sample) + parity test
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-2 — tomllib Python 3.10 fallback + pyproject conditional dep
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes
```

Both lanes have disjoint file ownership and no data dependency; they can execute in fully parallel worktrees.

## Lanes

### SL-1 — Handler scoping + parity test

- **Scope**: Add `repository=` support to the three operational handlers, route through `ctx.sqlite_store`, fail-loud on inconsistent `path`+`repository`, extend multi-repo integration tests, and add the schema-handler parity test.
- **Owned files**:
  - `mcp_server/cli/tool_handlers.py`
  - `tests/integration/test_multi_repo_server.py`
  - `tests/test_tool_schema_handler_parity.py` (new)
- **Interfaces provided**: IF-0-P9-1, IF-0-P9-2, IF-0-P9-3
- **Interfaces consumed**:
  - `RepoContext.sqlite_store` — `mcp_server/core/repo_context.py:13-31` (frozen dataclass, `sqlite_store: SQLiteStore` field hydrated by resolver)
  - `RepoResolver.resolve(path: Path) -> Optional[RepoContext]` — `mcp_server/core/repo_resolver.py:38-60`
  - `_resolve_ctx(repo_resolver, path_arg)` helper already present at `mcp_server/cli/tool_handlers.py:85-97` — reuse verbatim, no new helper
  - `_build_tool_list()` in `mcp_server/cli/stdio_runner.py:54-144` — parity test imports and calls it
  - `boot_test_server` + `TestServerHandle.call_tool` — `tests/fixtures/multi_repo.py:91-316`
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_tool_schema_handler_parity.py` (new), `tests/integration/test_multi_repo_server.py` | `test_schema_advertises_repository_implies_handler_accepts_it`, `test_handler_accepts_repository_implies_schema_advertises_it`, `test_reindex_scoped_to_repo` (mtime on repo A's `.mcp-index/current.db` unchanged when `repository=B`), `test_reindex_rejects_inconsistent_path_and_repository` (structured error code `conflicting_path_and_repository`), `test_write_summaries_scoped_to_repo` (result's chunks all belong to repo B's file paths), `test_summarize_sample_scoped_to_repo` (sampled files all under repo B's path) | `pytest tests/test_tool_schema_handler_parity.py tests/integration/test_multi_repo_server.py -x` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/cli/tool_handlers.py` | — | — |
| SL-1.3 | verify | SL-1.2 | `mcp_server/cli/tool_handlers.py`, `tests/integration/test_multi_repo_server.py`, `tests/test_tool_schema_handler_parity.py` | all SL-1 tests + existing handler tests | `pytest tests/test_tool_schema_handler_parity.py tests/integration/test_multi_repo_server.py tests/test_tool_handlers.py -q` |

**SL-1.2 impl notes** (for the executor):
- For each of the three handlers, mirror the exact pattern already established in `handle_symbol_lookup` (`tool_handlers.py:100-167`) and `handle_search_code` (`tool_handlers.py:170-291`):
  1. `repository = (arguments or {}).get("repository")`
  2. If `repository` is path-shaped and fails `_path_within_allowed`, return the existing structured `path_outside_allowed_roots` error
  3. `ctx = _resolve_ctx(repo_resolver, repository or <existing-path-arg>)`
  4. Use `ctx.sqlite_store if ctx is not None else sqlite_store` as the active store (don't remove the `sqlite_store` kwarg — it remains as the pre-resolver fallback)
  5. Pass `ctx` into dispatcher calls using the same `try: dispatcher.method(ctx, …) except TypeError: dispatcher.method(…)` compatibility shim already in place
- `handle_reindex` conflict check (IF-0-P9-2): compute `ctx_from_path = _resolve_ctx(repo_resolver, path) if path else None` and `ctx_from_repo = _resolve_ctx(repo_resolver, repository) if repository else None`; if both are non-None and `ctx_from_path.repo_id != ctx_from_repo.repo_id`, return the conflict error before any indexing work starts.
- Parity test (`tests/test_tool_schema_handler_parity.py`): import `_build_tool_list` from `mcp_server.cli.stdio_runner`; build a `{tool.name: tool.inputSchema}` map; import the handlers module; hand-maintain a `TOOL_NAME_TO_HANDLER = {"reindex": handle_reindex, ...}` dict at the top of the test file (one line per tool — kept honest by the parity test itself); use `inspect.signature` to check each handler accepts `arguments` and, for tools whose schema has `"repository"` in `inputSchema["properties"]`, assert the handler's body references `arguments.get("repository")` OR (stronger) route through ctx. For the "handler advertises repository back to schema" direction, grep the handler source for `arguments.get("repository")` and assert the schema advertises it.

### SL-2 — tomllib Python 3.10 fallback + pyproject conditional dep

- **Scope**: Replace bare `import tomllib` with a 3.10-compatible fallback, and declare `tomli` as a conditional test dep in `pyproject.toml`.
- **Owned files**:
  - `tests/test_requirements_consolidation.py`
  - `pyproject.toml`
- **Interfaces provided**: IF-0-P9-4
- **Interfaces consumed**: none
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_requirements_consolidation.py` | Extend file with `test_tomllib_import_guard_present` (reads its own source with `inspect.getsource(sys.modules[__name__])` and asserts the `try/except ImportError: import tomli as tomllib` pattern is present verbatim). Also extend with `test_pyproject_declares_tomli_for_py310` that parses `pyproject.toml` and asserts the `dev` extra contains `tomli>=2.0.1; python_version<"3.11"` (normalized). | `python3.10 -m pytest tests/test_requirements_consolidation.py -x` if 3.10 is available locally; else `pytest tests/test_requirements_consolidation.py -x` |
| SL-2.2 | impl | SL-2.1 | `tests/test_requirements_consolidation.py`, `pyproject.toml` | — | — |
| SL-2.3 | verify | SL-2.2 | `tests/test_requirements_consolidation.py`, `pyproject.toml` | all SL-2 tests | `pytest tests/test_requirements_consolidation.py -q && python -c "import tomllib" 2>/dev/null || python -c "import tomli"` |

**SL-2.2 impl notes**:
- Top of `tests/test_requirements_consolidation.py`: replace `import tomllib` (line 10) with:
  ```python
  try:
      import tomllib
  except ImportError:  # Python <3.11
      import tomli as tomllib
  ```
- `pyproject.toml` `[project.optional-dependencies].dev` (lines 77–124): add `"tomli>=2.0.1; python_version<\"3.11\""` in the utility section (after `freezegun` per explore report). Preserve existing alphabetical/logical grouping; do not reorder other entries.

## Execution Notes

- **Parallelism**: SL-1 and SL-2 touch disjoint files. No SL-0 preamble is needed — neither lane adds symbols that the other consumes.
- **Single-writer files**: `mcp_server/cli/tool_handlers.py` is SL-1's sole writer. `pyproject.toml` is SL-2's sole writer. `stdio_runner.py` is NOT touched in P9 (schemas and wiring both settled in P7) — if a lane feels the urge to edit it, that is a signal to reconsider.
- **Known destructive changes**: none — both lanes are purely additive / modifying in place.
- **Expected add/add conflicts**: none.
- **SL-0 re-exports**: none.
- **Stale-base guidance** (copy verbatim into executor brief): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-P7-merge (schemas missing `repository` on the three tools), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.
- **Worktree naming**: `execute-phase` allocates unique worktree names via `scripts/allocate_worktree_name.sh`.
- **Test-infra reuse**: SL-1 must use `boot_test_server` + `TestServerHandle.call_tool` from `tests/fixtures/multi_repo.py` (already sets up repo_a + repo_b with `.mcp-index/current.db`). Do NOT introduce a new multi-repo fixture. The mtime assertion reads `<repo>/.mcp-index/current.db` via `Path.stat().st_mtime_ns`.
- **Handler backward compatibility**: the `sqlite_store` kwarg on the three handlers stays in the signature for pre-resolver callers (tests and any lingering direct-invocation paths). Handlers prefer `ctx.sqlite_store` when `ctx is not None`; fall back to the kwarg otherwise. This is the same shape as `handle_search_code` and `handle_symbol_lookup` today.
- **Parity test scope**: only tools whose schema currently advertises `repository` are in scope — `symbol_lookup`, `search_code`, `reindex`, `write_summaries`, `summarize_sample`. `get_status` and `list_plugins` intentionally do NOT advertise `repository` and the parity test must accept that (bi-directional check).

## Acceptance Criteria

- [ ] `pytest tests/test_tool_schema_handler_parity.py -q` passes with all five advertised-repository tools mapped to handlers that accept `arguments["repository"]` — and no handler accepts `repository` for a tool whose schema doesn't advertise it.
- [ ] `pytest tests/integration/test_multi_repo_server.py::test_reindex_scoped_to_repo -q` passes: before/after `reindex(repository=repo_b_path)`, `(<repo_a>/.mcp-index/current.db).stat().st_mtime_ns` is unchanged while repo B's changes.
- [ ] `pytest tests/integration/test_multi_repo_server.py::test_reindex_rejects_inconsistent_path_and_repository -q` passes: call with `path=<repo_a>` + `repository=<repo_b>` returns JSON with `"code": "conflicting_path_and_repository"` and no files were indexed in either repo.
- [ ] `pytest tests/integration/test_multi_repo_server.py::test_write_summaries_scoped_to_repo -q` passes: all returned chunk file paths have `<repo_b_path>` as prefix; none under `<repo_a_path>`.
- [ ] `pytest tests/integration/test_multi_repo_server.py::test_summarize_sample_scoped_to_repo -q` passes: all sampled `file_path` entries are under `<repo_b_path>`.
- [ ] `python3.10 -m pytest tests/test_requirements_consolidation.py -q` exits 0 (if Python 3.10 is available in CI/venv); on Python 3.11+, same test still passes (tomllib preferred path). Locally verifiable via a pyenv 3.10 shim if available.
- [ ] `rg -n "import tomllib$" tests/` returns zero matches (only guarded imports remain). Paired with `test_tomllib_import_guard_present` inside the consolidation test so a grep-only regression doesn't slip through via rename.
- [ ] `pyproject.toml` `[project.optional-dependencies].dev` contains the literal marker `tomli>=2.0.1; python_version<"3.11"` (verifiable by `tomli.load`-ing the pyproject and checking the `dev` list).

## Verification

After both lanes merge to `main`:

```bash
# SL-1 core contracts
pytest tests/test_tool_schema_handler_parity.py -v
pytest tests/integration/test_multi_repo_server.py -v -k "scoped_to_repo or rejects_inconsistent"

# SL-2 Python 3.10 compat
pytest tests/test_requirements_consolidation.py -v
# If pyenv 3.10 is available:
#   pyenv shell 3.10.14 && python -m pytest tests/test_requirements_consolidation.py

# Regression: full handler suite
pytest tests/test_tool_handlers.py tests/integration/test_multi_repo_server.py -q

# End-to-end sanity via MCP CLI (manual): call reindex with repository=<repo_b> and
# confirm repo_a index mtime is untouched:
stat -c %Y <repo_a>/.mcp-index/current.db  # before
python -m mcp_server.cli reindex --repository <repo_b_path>
stat -c %Y <repo_a>/.mcp-index/current.db  # after — must match

# Grep assertions (paired with tests above, not sole checks):
rg -n "import tomllib$" tests/           # expect zero
rg -n 'arguments.*\.get\("repository"\)' mcp_server/cli/tool_handlers.py  # expect 5+ matches
```
