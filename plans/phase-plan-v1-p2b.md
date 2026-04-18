# PHASE-2B-dispatcher-refactor: Phase 2B — Dispatcher Refactor & Entry-Point Consolidation

> Plan doc produced by `/plan-phase P2B --consensus` against `specs/phase-plans-v1.md` lines 214–248. On approval, saved to `plans/phase-plan-v1-p2b.md` and handed off to `/execute-phase p2b`.

## Context

P1 + P2A + P6A are merged. P2B is the critical-path refactor that unblocks production multi-repo serving: every downstream phase (P3 per-repo plugins, P4 multi-repo watcher, P5 STDIO hardening) consumes the dispatcher interface this phase freezes. Getting it wrong costs three phases of rework downstream.

### What exists

- **`mcp_server/dispatcher/dispatcher_enhanced.py`** — 2392 lines, single `EnhancedDispatcher` class (line 116). Constructor (155–227) captures `sqlite_store: Optional[SQLiteStore]`. Body has 40+ `self._sqlite_store` references (lines 180, 254, 400, 414, 465, 683–688, 989, 992, 1004–1010, 1083–1087, 1123, 1147, 1160, 1195, 1284, 1322, 1891–1899, 1944–1953). 17 public methods: `lookup` (676), `search` (1077), `index_file` (1540), `get_statistics` (1607), `index_directory` (1625), `search_documentation` (1769), `health_check` (1837), `remove_file` (1876), `move_file` (1925), `graph_search` (2170), `get_context_for_symbols` (2224), `find_symbol_dependencies` (2269), `find_symbol_dependents` (2315), `get_code_hotspots` (2361), plus `plugins` (607), `supported_languages` (612), `get_plugins_for_file` (659). Global dispatcher state (`_semantic_indexer`, `_reranker`, `_plugins` + `_by_lang` + `_loaded_languages`, `_file_cache`, `_graph_builder`, `_graph_analyzer`) is process-scoped, not per-repo.

- **`mcp_server/dispatcher/simple_dispatcher.py`** — 123 lines, 4 public methods (`search`, `search_symbol`, `get_stats`, `health_check`). Strict BM25-only subset of `EnhancedDispatcher`. Used as fallback and as the dispatcher base class in `tests/conftest.py:18` (`from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher as Dispatcher`).

- **Two cross-repo coordinators**: `mcp_server/storage/cross_repo_coordinator.py` (527 lines; imports `from mcp_server.plugins.memory_aware_manager import get_memory_aware_manager` under a TODO-style stub, effectively dead) and `mcp_server/dispatcher/cross_repo_coordinator.py` (578 lines; wired via the dispatcher, has reranker integration, actively used). ~1100 lines of duplication per spec line 22.

- **P2A artifacts (ready to consume)**: `RepoContext` frozen dataclass at `mcp_server/core/repo_context.py:13–31` (fields: `repo_id`, `sqlite_store`, `workspace_root`, `tracked_branch`, `registry_entry`). `RepoResolver.resolve(path) -> Optional[RepoContext]` at `mcp_server/core/repo_resolver.py:38–60`. `StoreRegistry.get(repo_id) -> SQLiteStore` thread-safe + idempotent at `mcp_server/storage/store_registry.py:50–74`. **None of these are exported from `mcp_server/core/__init__.py`** — consumers currently import directly.

- **Entry point — `scripts/cli/mcp_server_cli.py`** — 1711 lines, captures `_STARTUP_CWD` (line 78), `sqlite_store` (line 213/258), `dispatcher` (global 66/325) at init. `initialize_services()` at 180–259. 7 MCP tool handlers: `symbol_lookup` (786), `search_code` (846), `reindex` (1302), `get_status` (1165), `list_plugins` (1255), `write_summaries` (1415), `summarize_sample` (1462). Multi-repo bypass at 863–956 calls `dispatcher._multi_repo_manager.search_code(...)` directly, routing around the dispatcher's own methods. 10+ test files (`tests/root_tests/test_mcp_*.py`) do bare `import mcp_server_cli` (PYTHONPATH-dependent).

- **`mcp_server/cli/server_commands.py`** — only 40 lines, currently a Click HTTP-gateway launcher (`@click.command("serve")` → `uvicorn.run("mcp_server.gateway:app")`). Despite the spec's literal "collapse into" phrasing, this file is NOT currently a stdio entry point — P2B adds the `stdio` command alongside `serve`.

- **Consumers of the dispatcher**: `mcp_server/gateway.py` (2370 lines) — dispatcher constructed line 540, plus lines 1632 + 1664; ~12 FastAPI routes call dispatcher methods (`/symbol` 1086, `/search` 1221/1271, `/reindex` 1523/1531/1557, `/symbol-deps` 2137, `/symbol-dependents` 2161, `/hotspots` 2184, `/context` 2209, `/graph-search` 2271); direct private-attr access: `dispatcher._plugins` (1385, 1390, 1393), `dispatcher._graph_analyzer` / `_graph_nodes` / `_graph_edges` (2315–2366). Module-global + `app.state.dispatcher`. Tests: `tests/conftest.py` fixtures (lines 18, 251–262), 4 dispatcher-focused test files (`test_dispatcher.py` 819 lines, `test_dispatcher_advanced.py` 699 lines, `test_enhanced_dispatcher.py` 360 lines, plus document-routing), ~100+ test methods total. 8 `from mcp_server.dispatcher` imports across `gateway.py`, `conftest.py`, `cli/artifact_commands.py`, `cli/index_management.py`, `cli/repository_commands.py`, `benchmarks/benchmark_suite.py`, `benchmarks/quick_comparison.py`, `utils/mcp_client_wrapper.py`.

- **Config templates** touching `scripts/cli/mcp_server_cli.py`: `.mcp.json`, `.mcp.json.example`, `.mcp.json.template`, `.mcp.json.templates/native.json`, `.mcp.json.templates/docker-sidecar.json`, `.mcp.json.templates/auto-detect.json` (6 files). `op run --env-file=.mcp.env` wrapper shape must be preserved (from earlier session work).

### Why a facade freeze is mandatory

Without the `DispatcherProtocol` frozen before lanes diverge, every lane (internals rewrite, gateway refactor, entry-point consolidation, test migration) needs to edit `dispatcher_enhanced.py` to see the new method signatures — producing four-way merge conflicts on a 2392-line file. The Protocol freeze lets consumer lanes develop against the declared interface while the implementation lane rewrites the bodies; merge order serializes on integration but dispatch-time parallelism is full.

## Interface Freeze Gates

- [ ] **IF-0-P2B-1** — `DispatcherProtocol` (`typing.Protocol`) in new file `mcp_server/dispatcher/protocol.py`. Declares all 17 public methods with `ctx: RepoContext` as first positional arg. Exception: `supported_languages()` takes no `ctx` (language support is process-global, derived from installed plugins — spec non-goal says plugins stay dispatcher-global during P2B). Also promotes `dispatcher._plugins` / `_graph_nodes` / `_graph_edges` to public methods (`plugins()`, `graph_nodes(ctx)`, `graph_edges(ctx)`) so gateway.py stops reaching into private attrs.
- [ ] **IF-0-P2B-2** — `RepoContext` / `RepoResolver` / `StoreRegistry` re-export surface: `mcp_server/core/__init__.py` exposes `RepoContext`, `RepoResolver`; `mcp_server/storage/__init__.py` exposes `StoreRegistry`. Single canonical import path for all consumers.
- [ ] **IF-0-P2B-3** — Entry-point contract: `mcp_server/cli/server_commands.py` gains a `@click.command("stdio")` that invokes `mcp_server.cli.stdio_runner:run()` (new module). `.mcp.json` templates invoke `python -m mcp_server.cli stdio` (Click group discovers the subcommand). Preserves `op run --env-file=.mcp.env` outer wrapper.
- [ ] **IF-0-P2B-4** — Bootstrap signature: `mcp_server/cli/bootstrap.py:initialize_stateless_services() -> tuple[StoreRegistry, RepoResolver, DispatcherProtocol]`. Zero captured cwd, zero preloaded `sqlite_store`. First tool call resolves `RepoContext` from the tool's path argument or `MCP_WORKSPACE_ROOT` default.

## Lane Index & Dependencies

```
SL-1 — Dispatcher internals rewrite
  Depends on: (none)
  Blocks: SL-3, SL-4
  Parallel-safe: yes

SL-2 — Entry-point consolidation + .mcp.json templates
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-3 — Gateway refactor
  Depends on: SL-1
  Blocks: (none)
  Parallel-safe: yes

SL-4 — Test migration (conftest + ~100 call-sites)
  Depends on: SL-1
  Blocks: (none)
  Parallel-safe: yes
```

All four lanes branch from the SL-0 preamble commit (authored + merged by the orchestrator before `/execute-phase p2b` dispatches — see Execution Notes below). From the lane-dispatch DAG's point of view, IF-0-P2B-1..4 are pre-existing. Dispatch-time parallelism: all 4 lanes launch simultaneously; SL-3/SL-4 teammates develop against Protocol + mocks and have their verify gated on SL-1's merge. Merge order: SL-1 first, then SL-2/SL-3/SL-4 in any order.

## Lanes

### SL-0 — Protocol freeze (preamble commit)

Landed as a single commit on `main` before `/execute-phase p2b` dispatches. **Not a lane** (not emitted as TaskCreate; orchestrator authors it). Produces:

- `mcp_server/dispatcher/protocol.py` (new, ~150 lines): `DispatcherProtocol(Protocol)` with 17 method signatures. Every method takes `ctx: RepoContext` as first arg except `supported_languages()` and `plugins()` (process-global per spec non-goal). Cross-repo methods take `List[RepoContext]`.
- `mcp_server/core/__init__.py` edit: re-export `RepoContext`, `RepoResolver`.
- `mcp_server/storage/__init__.py` edit: re-export `StoreRegistry`.
- `mcp_server/cli/bootstrap.py` (new, stub): `initialize_stateless_services()` signature only (body raises `NotImplementedError`; SL-2 fills it in).
- `mcp_server/cli/stdio_runner.py` (new, stub): `run()` signature only.
- Update `tests/fixtures/repo_context.py` (new): declares the fixture-name contract (`repo_ctx`, `store_registry`, `repo_resolver`, `dispatcher_factory`) that SL-4 implements against.

This commit is ~250 LOC of scaffolding. It compiles and passes existing tests (no behavior change).

### SL-1 — Dispatcher internals rewrite

- **Scope**: Rewrite `EnhancedDispatcher` and `SimpleDispatcher` to conform to `DispatcherProtocol`. Remove `sqlite_store` constructor param; replace all 40+ `self._sqlite_store` references with `ctx.sqlite_store`. Consolidate cross-repo coordinators: delete `mcp_server/storage/cross_repo_coordinator.py` (the dead-import stub), keep `mcp_server/dispatcher/cross_repo_coordinator.py` (the actively-wired variant with reranker integration), fix any remaining imports from the deleted path. Process-global state (`_semantic_indexer`, `_reranker`, `_plugins`, `_file_cache`, `_graph_*`) STAYS on the dispatcher for P2B — P3/P4 handle per-repo extraction. The dispatcher becomes per-process-singleton but per-call-repo-aware.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/dispatcher/simple_dispatcher.py`, `mcp_server/dispatcher/cross_repo_coordinator.py`, `mcp_server/dispatcher/__init__.py`, `mcp_server/storage/cross_repo_coordinator.py` (DELETE), `docs/architecture/P2B-known-limits.md` (NEW — documents deferred per-repo global state).
- **Interfaces provided**: concrete impl of IF-0-P2B-1 (Protocol); clean import for `CrossRepositorySearchCoordinator` from `mcp_server.dispatcher.cross_repo_coordinator`.
- **Interfaces consumed**: `DispatcherProtocol` (pre-existing), `RepoContext` (pre-existing), `StoreRegistry` (pre-existing)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_dispatcher.py` (extend), `tests/test_dispatcher_advanced.py` (extend) | `EnhancedDispatcher()` ctor raises `TypeError` if passed `sqlite_store=`; every public method accepts `ctx: RepoContext` as first positional and routes to `ctx.sqlite_store`; `isinstance(dispatcher, DispatcherProtocol)` via `typing.get_type_hints`; `SimpleDispatcher` also conforms to Protocol; `search_code(ctx, query)` with a two-repo registry returns results scoped to `ctx.repo_id` only; `from mcp_server.storage.cross_repo_coordinator import *` raises `ModuleNotFoundError` | `uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/dispatcher/simple_dispatcher.py`, `mcp_server/dispatcher/cross_repo_coordinator.py` (absorb storage variant's `SearchScope` dataclass if unique), `mcp_server/dispatcher/__init__.py`, `mcp_server/storage/cross_repo_coordinator.py` (DELETE), `docs/architecture/P2B-known-limits.md` (NEW) | — | — |
| SL-1.3 | verify | SL-1.2 | SL-1 owned files | all SL-1 + `test_enhanced_dispatcher.py` + `test_dispatcher_document_routing.py` | `uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/root_tests/test_enhanced_dispatcher.py -v` |

### SL-2 — Entry-point consolidation + `.mcp.json` templates

- **Scope**: Extract the 7 MCP tool handlers + stdio server wiring from `scripts/cli/mcp_server_cli.py` into `mcp_server/cli/` sub-modules. The 1711-line god file becomes: `mcp_server/cli/bootstrap.py` (`initialize_stateless_services()`, `_allowed_roots()`, `_path_within_allowed()`, `validate_index()`); `mcp_server/cli/tool_handlers.py` (one `async def handle_<tool>()` per MCP tool, each resolving `ctx` via `RepoResolver` from the tool's path arg or `MCP_WORKSPACE_ROOT` default); `mcp_server/cli/stdio_runner.py` (stdio server + `list_tools()` + `call_tool()` dispatching to `tool_handlers`). `mcp_server/cli/server_commands.py` gains a `@click.command("stdio")` that invokes `stdio_runner.run()`. `scripts/cli/mcp_server_cli.py` becomes a 3-line shim: `from mcp_server.cli.stdio_runner import run; run()` — preserves the 10+ `import mcp_server_cli` tests that depend on PYTHONPATH. Update 6 `.mcp.json*` templates to `python -m mcp_server.cli stdio` (preserving `op run --env-file=.mcp.env` outer wrapper). Update `Makefile` and `scripts/cli/mcp_server_wrapper.py` callers. The multi-repo bypass path at old lines 863–956 is REPLACED by a single `dispatcher.search(ctx, query, ...)` call in the new `handle_search_code` handler (where `ctx` comes from `RepoResolver.resolve(arguments.get("repository")` or cwd default).
- **Owned files**: `mcp_server/cli/bootstrap.py` (extend SL-0 stub), `mcp_server/cli/tool_handlers.py` (NEW, ~800 lines moved from old CLI), `mcp_server/cli/stdio_runner.py` (extend SL-0 stub), `mcp_server/cli/server_commands.py` (add `stdio` subcommand; existing `serve` untouched), `mcp_server/cli/__init__.py` (register `stdio` in Click group), `scripts/cli/mcp_server_cli.py` (shrink to 3-line shim — file path persists so PYTHONPATH imports keep working), `scripts/cli/mcp_server_wrapper.py` (update import source), `Makefile` (if it invokes the CLI), `.mcp.json`, `.mcp.json.example`, `.mcp.json.template`, `.mcp.json.templates/native.json`, `.mcp.json.templates/docker-sidecar.json`, `.mcp.json.templates/auto-detect.json`, `tests/test_bootstrap.py` (NEW).
- **Interfaces provided**: IF-0-P2B-3 impl, IF-0-P2B-4 impl.
- **Interfaces consumed**: `DispatcherProtocol` (pre-existing)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_bootstrap.py` (NEW), extend `tests/test_server_commands.py` | `initialize_stateless_services()` returns `(StoreRegistry, RepoResolver, DispatcherProtocol)` with zero captured cwd; `python -m mcp_server.cli stdio --help` exits 0; `from scripts.cli.mcp_server_cli import main` still importable (shim); each `.mcp.json*` template parses as valid JSON and its `args` no longer reference `scripts/cli/mcp_server_cli.py` by absolute path (module invocation); `handle_search_code({"query": "x", "repository": "<path>"})` resolves via `RepoResolver` and calls `dispatcher.search(ctx, ...)` | `uv run pytest tests/test_bootstrap.py tests/test_server_commands.py -v` |
| SL-2.2 | impl | SL-2.1 | all SL-2 owned files | — | — |
| SL-2.3 | verify | SL-2.2 | SL-2 owned files | all SL-2 tests + manual `echo '...' | python -m mcp_server.cli stdio` smoke | `uv run pytest tests/test_bootstrap.py tests/test_server_commands.py -v` |

### SL-3 — Gateway refactor

- **Scope**: `mcp_server/gateway.py` — update all ~30 dispatcher call sites (routes `/symbol`, `/search`, `/reindex`, `/symbol-deps`, `/symbol-dependents`, `/hotspots`, `/context`, `/graph-search`) to resolve `RepoContext` per request via a new `get_repo_ctx(request)` helper that pulls from `X-Repo-Id` header or query-string `?repository=<path>` or falls back to `RepoResolver.resolve(cwd)`. Replace direct private-attr access (`dispatcher._plugins` at 1385/1390/1393, `dispatcher._graph_analyzer` / `_graph_nodes` / `_graph_edges` at 2315–2366) with the new public Protocol methods (`dispatcher.plugins()`, `dispatcher.graph_nodes(ctx)`, `dispatcher.graph_edges(ctx)`). Dispatcher instantiation at line 540 changes from `EnhancedDispatcher(sqlite_store=..., ...)` to `EnhancedDispatcher()` (no ctor args). Same update at reload/enable handlers (lines 1632, 1664).
- **Owned files**: `mcp_server/gateway.py`, `tests/test_gateway.py` (extend).
- **Interfaces consumed**: `DispatcherProtocol` (pre-existing), `RepoResolver` (pre-existing)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_gateway.py` (extend) | `POST /search` with `X-Repo-Id: <id>` header routes via `RepoResolver`; `POST /search` with `?repository=<path>` query resolves via path; `POST /search` without either falls back to cwd-resolved context; `grep -n 'dispatcher\._' mcp_server/gateway.py` returns zero hits (no private-attr access); `dispatcher` constructor calls pass no `sqlite_store` kwarg | `uv run pytest tests/test_gateway.py -v` |
| SL-3.2 | impl | SL-3.1 | `mcp_server/gateway.py` | — | — |
| SL-3.3 | verify | SL-3.2 | SL-3 owned files | all SL-3 tests + cross-repo integration smoke | `uv run pytest tests/test_gateway.py -v` |

### SL-4 — Test migration (conftest + ~100 call-sites)

- **Scope**: Rewrite the dispatcher test harness for the new Protocol. `tests/conftest.py` gets new fixtures: `repo_ctx` (builds a `RepoContext` from the existing `sqlite_store` fixture with a fake `repo_id` and a `Mock(RepositoryInfo)`), `store_registry` (in-memory `StoreRegistry`), `repo_resolver` (given `repo_ctx`), `dispatcher_factory` (replaces the `Dispatcher([plugins])` positional constructor). Then sweep ~100 test call-sites across `test_dispatcher*.py` + `test_enhanced_dispatcher*.py` + any test that calls `dispatcher.<method>(args)` to add `ctx` as the first arg. No legacy shim — clean migration per consensus majority. Same treatment for `tests/base_test.py` (line 51 `EnhancedDispatcher()` call). Benchmark files under `mcp_server/benchmarks/` also updated.
- **Owned files**: `tests/conftest.py`, `tests/base_test.py`, `tests/fixtures/repo_context.py` (extend SL-0 stub), `tests/fixtures/__init__.py`, `tests/test_dispatcher.py`, `tests/test_dispatcher_advanced.py`, `tests/root_tests/test_enhanced_dispatcher.py`, `tests/root_tests/test_dispatcher_document_routing.py`, plus any `tests/**/*.py` grepping positive for `Dispatcher(` or `dispatcher\._sqlite_store` or `dispatcher\._plugins` or `EnhancedDispatcher(`. `mcp_server/benchmarks/benchmark_suite.py`, `mcp_server/benchmarks/quick_comparison.py`, `mcp_server/utils/mcp_client_wrapper.py` (3 non-test dispatcher callers).
- **Interfaces consumed**: `DispatcherProtocol` (pre-existing), `RepoResolver` (pre-existing)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_fixtures.py` (NEW, small) | `repo_ctx` fixture returns a `RepoContext` with a live `SQLiteStore`; `store_registry` fixture shuts down cleanly; `dispatcher_factory()` produces an object that passes `isinstance(..., DispatcherProtocol)` at runtime (via `typing.runtime_checkable`) | `uv run pytest tests/test_fixtures.py -v` |
| SL-4.2 | impl | SL-4.1 | all SL-4 owned files | — | — |
| SL-4.3 | verify | SL-4.2 | SL-4 owned files | full dispatcher/gateway/CLI test subset | `uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_gateway.py tests/test_bootstrap.py tests/root_tests/test_enhanced_dispatcher.py -v` |

## Execution Notes

- **Single-writer files**:
  - `mcp_server/dispatcher/dispatcher_enhanced.py` — SL-1 only. SL-3 and SL-4 consume it via the Protocol; they do not edit the file.
  - `mcp_server/gateway.py` — SL-3 only.
  - `tests/conftest.py` — SL-4 only.
  - `scripts/cli/mcp_server_cli.py` — SL-2 only (becomes a shim).
  - Each `.mcp.json*` template — SL-2 only.

- **SL-0 preamble sequencing**: the orchestrator authors SL-0 as a direct commit to main BEFORE invoking `/execute-phase p2b`. This is a ~250-LOC scaffolding commit that compiles and passes existing tests without behavior change. Only after SL-0 is on main does execute-phase dispatch SL-1/SL-2/SL-3/SL-4. The dispatch brief for each lane tells the teammate: "The Protocol at `mcp_server/dispatcher/protocol.py` is frozen — do not edit it. If you find you need to, stop and report to the orchestrator for an amendment round."

- **Wave dispatch**: Per `MAX_PARALLEL_LANES=2` (execute-phase default), orchestrator dispatches SL-1 + SL-2 first wave. After SL-1 merges, dispatches SL-3 + SL-4 second wave. SL-2 merges independently whenever it completes (no lane depends on it).

- **Known destructive changes** (stale-base whitelist — consumed by `pre_merge_destructiveness_check.sh`):
  - SL-1: deletion of `mcp_server/storage/cross_repo_coordinator.py` (527 lines; dead-import stub superseded by dispatcher/ variant).
  - SL-2: deletion of the 7 tool handler bodies + `initialize_services` from `scripts/cli/mcp_server_cli.py` (file shrinks from 1711 to 3 lines — path persists, not deleted outright).
  - SL-3: no file deletions; `dispatcher._*` private-attr references removed (promoted to public Protocol methods).
  - SL-4: no file deletions; ~100 test method bodies edited in-place.

- **Stale-base guidance** (copy verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-SL-0 preamble (Protocol not yet frozen) or pre-SL-1 (dispatcher bodies not rewritten), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- ...` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge. P6 lost 3 of 10 lanes to exactly this pattern; P2B has larger per-lane diffs (SL-1 alone touches ~2900 LOC) and correspondingly larger blast radius.

- **Harness preflight**: Before dispatch, orchestrator runs `bash ~/.claude/skills/execute-phase/scripts/verify_harness.sh`. All checks must pass.

- **Architectural choices (consensus outcome of `--consensus` round 1)**:
  - **Protocol, not ABC** (UNANIMOUS): `typing.Protocol` lets `SimpleDispatcher` and `EnhancedDispatcher` conform without forced inheritance; supports P3's future `RepoScopedDispatcher` wrapper via composition.
  - **SL-0 preamble freeze, not a lane** (UNANIMOUS): the Protocol + re-exports + stubs land as a pre-dispatch commit, not the first swim lane. Unblocks t=0 dispatch of all 4 lanes.
  - **No legacy compat shim on `SimpleDispatcher.__init__`** (MAJORITY 2/3: arch-clean + arch-parallel): pay the ~100-test-method migration cost once rather than leave a permanent shim that downstream phases inherit. `arch-minimal` dissented with a `DeprecationWarning`-tagged shim — recorded here as tech debt if SL-4 overruns (fall back to shim + deprecate in P3).
  - **Delete `mcp_server/storage/cross_repo_coordinator.py`, keep `mcp_server/dispatcher/cross_repo_coordinator.py`** (TECHNICAL OVERRIDE of 2/3 majority): Explore teammate found the dispatcher/ variant is newer, has reranker integration, and is actively wired; the storage/ variant has dead imports (`from mcp_server.plugins.memory_aware_manager import get_memory_aware_manager` under a stub). `arch-minimal` and `arch-parallel` both proposed the opposite direction (deleting dispatcher/, keeping storage/) — reversed in synthesis since their proposal would LOSE the reranker integration that is already functional.
  - **Non-sqlite global state stays on dispatcher** (MAJORITY 2/3: arch-minimal + arch-parallel-implicit): `_semantic_indexer`, `_reranker`, `_plugins`, `_file_cache`, `_graph_*` remain dispatcher instance attributes during P2B. Spec non-goals explicitly defer plugins to P3; semantic/graph deferred to P3/P4. `arch-clean` dissented (wanted `ServicePool` extraction now) — recorded as a principled design improvement to revisit in P3. Tech-debt note lands in `docs/architecture/P2B-known-limits.md` (SL-1 owns).
  - **Entry-point: extend `server_commands.py` with `stdio` subcommand + helper modules** (SPEC-LITERAL SYNTHESIS): spec says "collapse into `mcp_server/cli/server_commands.py`". Taking that literally, the `stdio` Click command lives there alongside the existing `serve`. The 1711 lines of CLI logic extract into `bootstrap.py` + `tool_handlers.py` + `stdio_runner.py` (arch-clean's decomposition), imported by `server_commands.py:stdio()`. This honors the spec while avoiding a 1711-line god-function in `server_commands.py`.
  - **Thin shim at `scripts/cli/mcp_server_cli.py`, not outright deletion** (MAJORITY 2/3: arch-minimal + arch-parallel-implicit): 10+ tests do `import mcp_server_cli` via PYTHONPATH. A 3-line shim preserves them without leaking new API surface. Spec exit criterion 3's parenthetical "(or a thin `scripts/` wrapper that imports from the package)" covers this.

- **Spec inaccuracies flagged for phase-plans v2**:
  1. Spec line 217 says "Collapse the 1700-line `scripts/cli/mcp_server_cli.py` into `mcp_server/cli/server_commands.py`." At the time of this plan, `server_commands.py` is a 40-line Click HTTP-gateway launcher (`serve` command), not a stdio entry point. P2B adds `stdio` as a sibling command; `serve` stays untouched. Spec phrasing should clarify "into `mcp_server/cli/` sub-modules, with `server_commands.py` adding a `stdio` subcommand" in v2.
  2. Spec line 220 says "15+ `self._sqlite_store` references". Actual count is 40+ across 26 lines in `dispatcher_enhanced.py`.
  3. Spec doesn't mention the cross-repo coordinator duplication explicitly in the exit criteria; P2B handles it as a scoped cleanup.

## Acceptance Criteria

- [ ] `.venv/bin/python -c "from mcp_server.dispatcher import EnhancedDispatcher; EnhancedDispatcher(sqlite_store=None)"` raises `TypeError` (ctor no longer accepts `sqlite_store`).
- [ ] `.venv/bin/python -c "from mcp_server.dispatcher.protocol import DispatcherProtocol; from mcp_server.dispatcher import EnhancedDispatcher, SimpleDispatcher; assert isinstance(EnhancedDispatcher(), DispatcherProtocol); assert isinstance(SimpleDispatcher(), DispatcherProtocol)"` exits 0.
- [ ] `rg -n 'self\._sqlite_store' mcp_server/dispatcher/dispatcher_enhanced.py` produces zero hits.
- [ ] `rg -n 'dispatcher\._(plugins|graph_|sqlite_store|multi_repo_manager)' mcp_server/gateway.py` produces zero hits (private-attr access removed).
- [ ] `.venv/bin/python -c "import mcp_server.storage.cross_repo_coordinator" 2>&1 | grep -q ModuleNotFoundError` exits 0 (file deleted).
- [ ] `.venv/bin/python -c "from mcp_server.dispatcher.cross_repo_coordinator import CrossRepositorySearchCoordinator"` exits 0 (dispatcher variant retained).
- [ ] `python -m mcp_server.cli stdio --help` exits 0; stdout contains the `stdio` command name.
- [ ] `python -c "from scripts.cli.mcp_server_cli import main"` exits 0 (shim intact, PYTHONPATH tests not broken).
- [ ] `wc -l scripts/cli/mcp_server_cli.py` reports < 10 lines (shim, not god-file).
- [ ] For every `.mcp.json*` file in repo root + templates dir: `jq -r '.mcpServers[].args[]' <file> | grep -q 'scripts/cli/mcp_server_cli.py'` returns 1 (no absolute path references; module invocation instead) — **exception**: templates using `op run` wrap Python differently; verify each by hand that the final CLI invocation uses the module form.
- [ ] Existing single-repo usage works: `echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_code","arguments":{"query":"def test"}}}' | python -m mcp_server.cli stdio` (or via `.mcp.json`) returns non-empty results.
- [ ] Cross-repo usage works: same call with `"arguments": {"query": "def test", "repository": "<second-repo-path>"}` routes via `RepoResolver` and returns results scoped to that repo.
- [ ] `uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_gateway.py tests/test_bootstrap.py tests/test_fixtures.py tests/root_tests/test_enhanced_dispatcher.py -v` exits 0.
- [ ] `docs/architecture/P2B-known-limits.md` exists and documents the process-global state deferred to P3/P4.

## Verification

```bash
# Pre-flight
bash ~/.claude/skills/execute-phase/scripts/verify_harness.sh

# Sync environment
uv sync --extra dev

# Protocol conformance
.venv/bin/python - <<'PY'
from mcp_server.dispatcher.protocol import DispatcherProtocol
from mcp_server.dispatcher import EnhancedDispatcher, SimpleDispatcher
# runtime_checkable Protocol
assert isinstance(EnhancedDispatcher(), DispatcherProtocol), "EnhancedDispatcher does not conform"
assert isinstance(SimpleDispatcher(), DispatcherProtocol), "SimpleDispatcher does not conform"
print("Protocol conformance OK")
PY

# Old sqlite_store ctor param removed
.venv/bin/python - <<'PY'
from mcp_server.dispatcher import EnhancedDispatcher
try:
    EnhancedDispatcher(sqlite_store=None)
    raise SystemExit("FAIL: EnhancedDispatcher still accepts sqlite_store")
except TypeError:
    print("ctor signature OK")
PY

# No private-attr access in gateway
rg -n 'dispatcher\._(plugins|graph_|sqlite_store|multi_repo_manager)' mcp_server/gateway.py && echo "FAIL: private access remains" || echo "gateway private-access OK"

# Stale cross-repo file deleted
.venv/bin/python -c "import mcp_server.storage.cross_repo_coordinator" 2>&1 | grep -q ModuleNotFoundError && echo "storage cross-repo deleted OK" || echo "FAIL: storage cross-repo still present"

# Dispatcher variant retained
.venv/bin/python -c "from mcp_server.dispatcher.cross_repo_coordinator import CrossRepositorySearchCoordinator; print('dispatcher cross-repo OK')"

# Entry-point consolidation
python -m mcp_server.cli stdio --help > /dev/null && echo "stdio subcommand OK" || echo "FAIL: stdio subcommand missing"
test $(wc -l < scripts/cli/mcp_server_cli.py) -lt 10 && echo "shim OK" || echo "FAIL: shim too large"
.venv/bin/python -c "from scripts.cli.mcp_server_cli import main" && echo "shim-import OK" || echo "FAIL: shim broken"

# MCP JSON templates point at module, not script
for f in .mcp.json .mcp.json.example .mcp.json.template .mcp.json.templates/*.json; do
  if jq -r '..|strings' "$f" 2>/dev/null | grep -q 'scripts/cli/mcp_server_cli.py'; then
    # Allowed: op run wrappers that reference the shim path in their --file flag are OK.
    # Verify each template by hand for the final CLI invocation shape.
    echo "INSPECT: $f references scripts/cli/mcp_server_cli.py"
  fi
done

# Single-repo stdio smoke
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | timeout 10 python -m mcp_server.cli stdio | grep -q '"name":"search_code"' && echo "single-repo stdio OK" || echo "FAIL: stdio didn't respond"

# Cross-repo routing smoke (requires two registered repos in the registry)
# Manual step — see docs/testing/cross-repo-smoke.md

# Full targeted test suite
.venv/bin/python -m pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_gateway.py tests/test_bootstrap.py tests/test_fixtures.py tests/root_tests/test_enhanced_dispatcher.py -v

# Tech-debt note exists
test -f docs/architecture/P2B-known-limits.md && echo "tech-debt doc OK" || echo "FAIL: missing P2B-known-limits.md"
```

---

### Hand-off

On ExitPlanMode approval, the orchestrator will:

1. Write this doc to `plans/phase-plan-v1-p2b.md`.
2. Run `python ~/.claude/skills/plan-phase/scripts/validate_plan_doc.py plans/phase-plan-v1-p2b.md` and fix any errors.
3. **Author + commit the SL-0 preamble to main** — a single ~250-LOC scaffolding commit that lands the `DispatcherProtocol`, the `mcp_server/core/__init__.py` re-exports, the `mcp_server/storage/__init__.py` re-exports, and the stub modules (`bootstrap.py`, `stdio_runner.py`, `tests/fixtures/repo_context.py`). This commit compiles and passes existing tests; it introduces no behavior change. `/execute-phase p2b` will not dispatch until SL-0 is on main.
4. Emit four `TaskCreate` calls — one per lane — with `test / impl / verify` children and DAG metadata.
5. User invokes `/execute-phase p2b` when ready.
