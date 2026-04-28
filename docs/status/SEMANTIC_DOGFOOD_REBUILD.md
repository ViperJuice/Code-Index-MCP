# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-28T13:18:41Z`.
- Observed commit: `dce6920e`.
- Phase plan: `plans/phase-plan-v7-SEMIOWAIT.md`.
- Prior repair carried forward: `SEMSTALLFIX` in `specs/phase-plans-v7.md`.

## Reset Boundary

This SEMIOWAIT run preserved the same repo-local reset boundary and
repo-local dogfood boundary:

- `.mcp-index/current.db` remained the active SQLite store.
- `qdrant_storage/` was preserved.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of SQLite, WAL, or Qdrant state was used.

Durable counts around the live rerun stayed bounded but still blocked:

- `chunk_summaries`: `3018`
- `semantic_points`: `0`

## Low-Level Force-Full Forensics

SEMSTALLFIX already hardened semantic-stage accounting and fail-closed
full-index closeout. SEMIOWAIT tightened the lower lexical/storage path that
still sat underneath those semantic-stage outcomes:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now records
  `lexical_stage`, `lexical_files_attempted`, `lexical_files_completed`,
  `last_progress_path`, and `in_flight_path` during `index_directory(...)`.
- The dispatcher now fails closed with a low-level blocker when lexical work
  stops below semantic-stage accounting. The live blocker string here is
  `blocked_file_timeout`, separate from SEMSTALLFIX semantic-stage values such
  as `blocked_summary_plateau` or `blocked_semantic_batch`.
- `mcp_server/storage/sqlite_store.py` now surfaces metadata-only storage
  diagnostics for `journal_mode`, `busy_timeout_ms`, `wal_checkpoint`, and the
  active SQLite/WAL/SHM file sizes.
- `mcp_server/storage/git_index_manager.py` now treats those low-level lexical
  blockers as exact force-full failures and keeps the indexed commit unchanged
  when the lexical path fails before semantic-stage accounting begins.
- The owned tests in `tests/test_dispatcher.py`,
  `tests/test_git_index_manager.py`, and `tests/test_sqlite_store.py` now
  freeze that contract.

This did not restore semantic readiness, but it did replace the prior opaque
multi-minute hang with a deterministic lexical/storage refusal.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Live SEMIOWAIT rerun evidence:

- The rerun no longer stayed active indefinitely.
- The command failed fast with:
  `Lexical indexing timed out while processing CHANGELOG.md`.
- The dispatcher-side lexical blocker classification was
  `lexical_stage=blocked_file_timeout`.
- The last in-flight lexical path was `CHANGELOG.md`; the run never advanced
  into semantic-stage accounting on this attempt.
- The indexed commit did not advance after the failed rerun.

Low-level diagnostic evidence from `SQLiteStore.health_check()` after the run:

- `journal_mode`: `WAL`
- `busy_timeout_ms`: `5000`
- `wal_checkpoint.status`: `ok`
- `wal_checkpoint.busy`: `1`
- `wal_checkpoint.log_frames`: `-1`
- `wal_checkpoint.checkpointed_frames`: `-1`
- SQLite file sizes:
  - `.mcp-index/current.db`: `297316352`
  - `.mcp-index/current.db-wal`: `17122752`
  - `.mcp-index/current.db-shm`: `65536`

Residual blocker interpretation:

- SEMSTALLFIX remains valid: semantic-stage accounting is still bounded in
  tests.
- The live blocker is now narrower and reproducible: lexical indexing times
  out on `CHANGELOG.md` before the semantic-stage path begins.
- The storage diagnostics are metadata-only and show WAL/checkpoint posture
  without destructive resets.

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

- Current commit: `dce6920e`
- Indexed commit: `93f00d29`
- Readiness remediation: `Run reindex to update the repository index to the current commit.`

Semantic evidence after the rerun remained:

- Summary-backed chunks: `3018`
- Chunks missing summaries: `62769`
- Vector-linked chunks: `0`
- Chunks missing vectors: `65686`
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
  now skips with `stale_commit` instead of hanging on an unbounded live sync.
- Ready-path semantic metadata still remains the target once the index is
  fresh again: `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"`.
- `symbol` and native fallback probes still point operators at
  `mcp_server/setup/semantic_preflight.py` and
  `mcp_server/cli/repository_commands.py`.
- The new low-level blocker path now lives in
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/storage/git_index_manager.py`, and
  `mcp_server/storage/sqlite_store.py`.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMIOWAIT.

Why:

- The rebuild now fails deterministically instead of hanging silently.
- The active indexed commit remains stale at `93f00d29` while `HEAD` is
  `dce6920e`.
- Semantic readiness remains `summaries_missing`.
- `semantic_points` remains `0`.
- The precise remaining blocker is now lexical/storage scoped:
  `blocked_file_timeout` on `CHANGELOG.md`.

Steering outcome:

- No downstream roadmap amendment was needed because `SEMIOWAIT` is the
  terminal phase in `specs/phase-plans-v7.md`.
- Older downstream plans are therefore not in play here.
- The remaining follow-up, if pursued, should start from a fresh plan or
  roadmap extension focused on the `CHANGELOG.md` lexical timeout path rather
  than reopening semantic-stage accounting.

## Verification

Verification sequence for this SEMIOWAIT slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_sqlite_store.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_sqlite_store.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
sqlite3 .mcp-index/current.db 'PRAGMA journal_mode; PRAGMA wal_checkpoint(PASSIVE); PRAGMA busy_timeout; SELECT COUNT(*) AS chunk_summaries FROM chunk_summaries; SELECT COUNT(*) AS semantic_points FROM semantic_points;'
```

Observed outcomes:

- Dispatcher, git-index-manager, and SQLiteStore suites: passed.
- SEMDOGFOOD evidence contract test: passed after the docs refresh.
- Force-full rebuild:
  failed fast with `Lexical indexing timed out while processing CHANGELOG.md`.
- Repository status:
  still `stale_commit` plus semantic readiness `summaries_missing`.
- Active-profile semantic preflight:
  still `ready`.
- Repo-local semantic dogfood query harness:
  skipped because indexed semantic queries remain unavailable while the repo is
  still `stale_commit`.
