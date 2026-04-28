# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-28T15:41:29Z`.
- Observed commit: `e2e95198`.
- Phase plan: `plans/phase-plan-v7-SEMCLOSEOUT.md`.
- Prior repairs carried forward: `SEMSTALLFIX`, `SEMIOWAIT`,
  `SEMCHANGELOG`, `SEMROADMAP`, `SEMANALYSIS`, and `SEMAGENTS` in
  `specs/phase-plans-v7.md`.

## Reset Boundary

This SEMREADME run preserved the same repo-local reset boundary and repo-local
dogfood boundary:

- `.mcp-index/current.db` remained the active SQLite store.
- `qdrant_storage/` was preserved.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of SQLite, WAL, or Qdrant state was used.

Durable counts before the repaired rerun stayed bounded to the existing local
index state:

- `chunk_summaries`: `0`
- `semantic_points`: `0`

## README Lexical Repair

SEMAGENTS narrowed the residual live stall to an exact lexical blocker on
`README.md`. SEMREADME repaired that last bounded Markdown timeout without
weakening the lexical watchdog globally:

- `mcp_server/plugins/markdown_plugin/plugin.py` now routes `README.md`
  through the bounded Markdown lexical path with `lightweight_reason:
  "readme_path"`.
- The bounded path preserves durable lexical search input plus document and
  heading symbols for `README.md` instead of silently dropping the repo guide
  from the index.
- `mcp_server/dispatcher/dispatcher_enhanced.py` now persists shard symbols
  and chunks through one SQLite connection, so bounded Markdown shards no
  longer spend the lexical watchdog budget on per-symbol write overhead.
- The owned tests in `tests/test_dispatcher.py`,
  `tests/test_git_index_manager.py`, and
  `tests/root_tests/test_markdown_production_scenarios.py` now freeze that
  contract, including the README-specific persistence path.

## SEMCLOSEOUT Semantic Recovery

SEMCLOSEOUT did not close the semantic phase yet, but it changed the live
repo-local blocker in an important way:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now lazily builds a
  repo-scoped semantic indexer for registered contexts when the CLI sync path
  constructs `EnhancedDispatcher()` without an injected
  `SemanticIndexerRegistry`.
- The same dispatcher now bounds each authoritative summary pass instead of
  trying to drain the whole repo-local semantic backlog in one timed call.
- `tests/test_dispatcher.py` freezes that registered-context semantic
  availability and the bounded summary-pass sizing.
- `tests/real_world/test_semantic_search.py` now accepts the current
  fail-closed `index_unavailable` readiness codes instead of hard-coding only
  `stale_commit`.

Live bounded semantic replay on the fresh lexical-ready SQLite store now
persists authoritative summaries instead of making zero semantic progress:

- `chunk_summaries`: `10 -> 191`
- `semantic_points`: `0 -> 0`
- First persisted live SEMCLOSEOUT file:
  `.claude/agents/lane-executer.md` with `188` authoritative summaries
- Semantic readiness remains `summaries_missing`, so strict vector linkage has
  not started for the remaining backlog.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Live SEMREADME rerun evidence:

- The rerun no longer failed on `README.md`.
- Direct README indexing on the live SQLite store dropped from about `12.2s`
  to about `1.5s`, which keeps the bounded shard under the same five-second
  lexical watchdog.
- The repaired force-full rebuild completed cleanly with:
  `Indexed 1388 files in 281.8s`.
- The indexed commit advanced to the current commit, so the repo is no longer
  blocked at `stale_commit`.
- The rebuild did not surface a new lexical/storage blocker after `README.md`;
  the lexical stage completed and the query surface became ready.
- One oversized archive artifact was skipped during the same run:
  `analysis_archive/semantic_vs_sql_comparison_1750926162.json` (`32983030`
  bytes).

Residual blocker shape after the clean lexical rebuild:

- Lexical readiness: `ready`
- Query surface: `ready`
- Semantic readiness: `summaries_missing`
- `chunk_summaries`: `0`
- `semantic_points`: `0`
- Chunks missing summaries: `33107`
- Chunks missing vectors: `33107`

Current SQLite artifact size after the rerun:

- `.mcp-index/current.db`: `107.7 MB`

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the completed rerun reported:

- Lexical readiness: `ready`
- Semantic readiness: `summaries_missing`
- Active-profile preflight: `ready`
- Can write semantic vectors: `yes`
- Active profile: `oss_high`
- Active collection: `code_index__oss_high__v1`
- Collection bootstrap state: `reused`
- Query surface: `ready`
- Rollout status: `local_only`

Repository/index freshness evidence:

- Current commit: `e2e95198`
- Indexed commit: `e2e95198`

Semantic evidence after the latest SEMCLOSEOUT replay is now:

- Summary-backed chunks: `191`
- Chunks missing summaries: `32978`
- Vector-linked chunks: `0`
- Chunks missing vectors: `33169`
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

- Semantic query routing is now eligible because the repository query surface is
  `ready`, but repo-local semantic dogfood still skips on
  `semantic_not_ready` because semantic readiness remains `summaries_missing`
  even after bounded SEMCLOSEOUT summary progress.
- Repo-local semantic dogfood query harness:
  `tests/real_world/test_semantic_search.py -k repo_local_dogfood_queries_stay_on_semantic_path`
  now skips on semantic readiness rather than on `index_unavailable`.
- Ready-path semantic metadata still remains the target once summaries and
  vectors exist: `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"`.
- `symbol` and ready lexical probes still point operators at
  `mcp_server/setup/semantic_preflight.py` and
  `mcp_server/cli/repository_commands.py`.
- The remaining downstream work is now in the semantic path centered on
  `mcp_server/indexing/summarization.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/storage/git_index_manager.py`, and
  `mcp_server/utils/semantic_indexer.py`.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMCLOSEOUT.

Why:

- The original `README.md` lexical timeout is repaired.
- The active indexed commit is now fresh at `e2e95198`.
- Repository readiness is `ready`, and the query surface is `ready`.
- Semantic readiness remains `summaries_missing`.
- `chunk_summaries` increased to `191`, which proves the live semantic writer
  now persists authoritative summaries on the repo-local index.
- `semantic_points` remains `0`.
- The precise remaining blocker is no longer semantic-stage availability. It is
  semantic closeout throughput and vector linkage: the remaining summary
  backlog still has to drain before strict vector writes can begin.

Steering outcome:

- SEMREADME changed downstream work by clearing the final lexical timeout and
  exposing semantic closeout as the next exact blocker family.
- SEMCLOSEOUT then repaired the registered-context semantic-stage skip and
  proved live summary persistence on the repo-local index.
- This registered-context semantic stage is now live in the repo-local
  recovery path instead of being silently skipped.
- The current phase still remains blocked on finishing summary drain and strict
  vector linkage, so no newer downstream phase is execution-authoritative yet.

## Verification

Verification sequence for this SEMCLOSEOUT slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k readme
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

Command-level anchors preserved for contract checks:

- `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov`
- `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov`
- `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k readme`
- `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`
- `env OPENAI_API_KEY=dummy-local-key uv run python - <<'PY' ... ComprehensiveChunkWriter.process_scope(limit=512, target_paths=...) ... PY`

Observed outcomes:

- Dispatcher suite: passed after SEMCLOSEOUT dispatcher repairs.
- Git-index-manager suite remained green from the SEMREADME lexical closeout.
- Markdown README production slice remained green from the SEMREADME lexical
  closeout.
- Force-full rebuild still restores lexical/query readiness `ready` and fresh
  indexed commit state for the active repo.
- Repository status now shows semantic readiness `summaries_missing` with
  non-zero `Summary-backed chunks: 191` and `Vector-linked chunks: 0`.
- Active-profile semantic preflight: still `ready`.
- Repo-local semantic dogfood harness: skipped on semantic readiness
  `summaries_missing`.
