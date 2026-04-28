# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-28T14:49:59Z`.
- Observed commit: `4959b36a`.
- Phase plan: `plans/phase-plan-v7-SEMREADME.md`.
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

- Current commit: `4959b36a`
- Indexed commit: `4959b36a`

Semantic evidence after the rerun remained:

- Summary-backed chunks: `0`
- Chunks missing summaries: `33107`
- Vector-linked chunks: `0`
- Chunks missing vectors: `33107`
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
  `semantic_not_ready` because semantic readiness remains `summaries_missing`.
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

Local multi-repo dogfooding is **still not ready** after SEMREADME.

Why:

- The original `README.md` lexical timeout is repaired.
- The active indexed commit is now fresh at `4959b36a`.
- Repository readiness is `ready`, and the query surface is `ready`.
- Semantic readiness remains `summaries_missing`.
- `chunk_summaries` remains `0`.
- `semantic_points` remains `0`.
- The precise remaining blocker is no longer lexical. It is semantic closeout:
  authoritative summaries and vectors are still missing for the active profile.

Steering outcome:

- SEMREADME changed downstream work by clearing the final lexical timeout and
  exposing semantic closeout as the next exact blocker family.
- `specs/phase-plans-v7.md` is amended with downstream phase `SEMCLOSEOUT`
  before any further execution handoff is considered authoritative.
- Older downstream plans or handoffs must be treated as stale after that
  roadmap amendment.

## Verification

Verification sequence for this SEMREADME slice:

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

Observed outcomes:

- Dispatcher and git-index-manager suites: passed.
- Markdown README production slice: passed.
- Force-full rebuild: passed with `Indexed 1388 files in 281.8s`.
- Repository status: lexical/query readiness `ready`, semantic readiness
  `summaries_missing`, rollout status `local_only`.
- Active-profile semantic preflight: still `ready`.
- Repo-local semantic dogfood harness: skipped on semantic readiness
  `summaries_missing`.
