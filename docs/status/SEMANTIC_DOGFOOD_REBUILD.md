# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-28T13:55:06Z`.
- Observed commit: `019e31d6`.
- Phase plan: `plans/phase-plan-v7-SEMROADMAP.md`.
- Prior repairs carried forward: `SEMSTALLFIX`, `SEMIOWAIT`, and
  `SEMCHANGELOG` in `specs/phase-plans-v7.md`.

## Reset Boundary

This SEMROADMAP run preserved the same repo-local reset boundary and
repo-local dogfood boundary:

- `.mcp-index/current.db` remained the active SQLite store.
- `qdrant_storage/` was preserved.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of SQLite, WAL, or Qdrant state was used.

Durable counts around the live rerun stayed bounded and restarted from the
partially rebuilt local index:

- `chunk_summaries`: `0`
- `semantic_points`: `0`

## Roadmap Lexical Repair

SEMCHANGELOG already narrowed the residual live stall to an exact lexical
blocker on `ROADMAP.md`. SEMROADMAP repaired that file-path-specific timeout
without weakening the watchdog globally:

- `mcp_server/plugins/markdown_plugin/plugin.py` now uses a bounded lexical
  path for roadmap and phase-plan Markdown filenames.
- The bounded path preserves durable lexical search input plus document and
  heading symbols for `ROADMAP.md` instead of silently dropping the file from
  the index.
- The heavyweight Markdown AST/section/chunk path is still available for other
  Markdown documents, and the lexical watchdog still fails closed for genuine
  path-level stalls.
- The owned tests in `tests/test_dispatcher.py`,
  `tests/test_git_index_manager.py`, and
  `tests/root_tests/test_markdown_production_scenarios.py` now freeze that
  contract.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Live SEMROADMAP rerun evidence:

- The rerun no longer failed on `ROADMAP.md`.
- The command now fails fast with:
  `Lexical indexing timed out while processing FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`.
- The dispatcher-side lexical blocker classification remains
  `lexical_stage=blocked_file_timeout`.
- `last_progress_path` advanced past `ROADMAP.md`.
- `in_flight_path` now points at `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` when
  the watchdog fires.
- The bounded downstream blocker moved from `ROADMAP.md` to
  `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`.
- The indexed commit did not advance after the failed rerun.

Residual blocker shape:

- `ROADMAP.md`: `1010` lines, `45009` bytes, cleared by the bounded lexical
  Markdown path.
- `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`: `206` lines, `7356` bytes, now the
  next exact file-path timeout under the same five-second watchdog.

Low-level diagnostic evidence from `SQLiteStore.health_check()` remains part of
the fail-closed contract:

- `journal_mode`
- `busy_timeout_ms`
- `storage_diagnostics`

Current SQLite artifact size after the rerun:

- `.mcp-index/current.db`: `1.2 MB`

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the blocked rerun reported:

- Lexical readiness: `stale_commit`
- Semantic readiness: `summaries_missing`
- Active-profile preflight: `ready`
- Can write semantic vectors: `yes`
- Active profile: `oss_high`
- Active collection: `code_index__oss_high__v1`
- Collection bootstrap state: `reused`
- Query surface: `index_unavailable`
- Rollout status: `stale_commit`

Repository/index freshness evidence:

- Current commit: `019e31d6`
- Indexed commit: `93f00d29`
- Readiness remediation: `Run reindex to update the repository index to the current commit.`

Semantic evidence after the rerun remained:

- Summary-backed chunks: `0`
- Chunks missing summaries: `306`
- Vector-linked chunks: `0`
- Chunks missing vectors: `306`
- Collection-matched links: `0`
- Collection mismatches: `0`

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`
still confirmed the active profile is preflight-ready:

- Configured enrichment model: `chat`
- Effective enrichment model:
  `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`
- Enrichment chat smoke: `ready`
- Embedding smoke: `ready`
- Collection check: `ready`

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Semantic query:
  still returns `code: "index_unavailable"` with
  `safe_fallback: "native_search"` because repository readiness remains
  `stale_commit`.
- Repo-local semantic dogfood query harness:
  `tests/real_world/test_semantic_search.py -k repo_local_dogfood_queries_stay_on_semantic_path`
  still skips while indexed semantic queries remain unavailable on the stale
  repo-local index.
- Ready-path semantic metadata still remains the target once the index is
  fresh again: `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"`.
- `symbol` and native fallback probes still point operators at
  `mcp_server/setup/semantic_preflight.py` and
  `mcp_server/cli/repository_commands.py`.
- The current low-level blocker path still reduces through
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/storage/git_index_manager.py`, and
  `mcp_server/storage/sqlite_store.py`.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMROADMAP.

Why:

- The original `ROADMAP.md` lexical timeout is repaired.
- The active indexed commit remains stale at `93f00d29` while `HEAD` is
  `019e31d6`.
- Semantic readiness remains `summaries_missing`.
- `semantic_points` remains `0`.
- The precise remaining blocker is now a new exact lexical/storage blocker:
  `blocked_file_timeout` on `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`.

Steering outcome:

- SEMROADMAP changed downstream work by clearing the `ROADMAP.md` blocker and
  exposing `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` as the next exact file-path
  timeout.
- `specs/phase-plans-v7.md` is amended with downstream phase `SEMANALYSIS`
  before any further execution handoff is considered authoritative.
- Older downstream plans must be treated as stale after that roadmap
  amendment.

## Verification

Verification sequence for this SEMROADMAP slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k roadmap
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Command-level anchors preserved for contract checks:

- `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov`
- `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov`
- `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_sqlite_store.py -q --no-cov`
- `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k roadmap`
- `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`

Observed outcomes:

- Dispatcher and git-index-manager suites: passed.
- Markdown roadmap production slice: passed.
- Force-full rebuild:
  failed fast with
  `Lexical indexing timed out while processing FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`.
- Repository status:
  still `stale_commit` plus semantic readiness `summaries_missing`.
- Active-profile semantic preflight:
  still `ready`.
