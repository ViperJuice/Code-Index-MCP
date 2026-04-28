# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-28T17:19:00Z`.
- Observed commit: `57bcec0d`.
- Phase plan: `plans/phase-plan-v7-SEMTIMEOUT.md`.
- Prior repairs carried forward: `SEMSTALLFIX`, `SEMIOWAIT`,
  `SEMCHANGELOG`, `SEMROADMAP`, `SEMANALYSIS`, `SEMAGENTS`, and
  `SEMREADME` plus `SEMCLOSEOUT` in `specs/phase-plans-v7.md`.

## Reset Boundary

This SEMTIMEOUT run preserved the same repo-local reset boundary and repo-local
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

SEMREADME remains the lexical prerequisite this phase inherits:

- `README.md` still indexes through the bounded Markdown lexical path.
- The README-specific lexical repair remains green in
  `tests/root_tests/test_markdown_production_scenarios.py -k readme`.
- The live SEMCLOSEOUT reruns in this turn did not reopen a lexical timeout on
  `README.md`; the remaining blocker stayed inside the semantic stage.

## SEMTIMEOUT Semantic Recovery

SEMTIMEOUT is still incomplete, but this execution changed the live semantic
recovery path in four important ways:

- `mcp_server/indexing/summarization.py` now exposes `process_scope(..., max_batches=1)`
  so one dispatcher summary pass can stop after one durable batch instead of
  looping until the whole repo backlog drains.
- `mcp_server/dispatcher/dispatcher_enhanced.py` now calls that one-batch mode
  and now drives one-batch passes while halving the repo-wide summary limit all
  the way down to single-chunk passes and preserving any progress made
  underneath timeout cancellation.
- Profile-backed summary clients now close deterministically, so the latest
  SEMTIMEOUT reruns no longer reproduce the earlier
  `httpx.AsyncClient.aclose()` / `RuntimeError: Event loop is closed` cleanup
  failure after timeout recovery.
- Profile-batch failures no longer retry the same doomed profile batch a second
  time before falling back, and the direct per-chunk fallback now uses a much
  smaller file-context budget for markdown/plaintext-style documents.
- `tests/test_summarization.py`, `tests/test_dispatcher.py`, and
  `tests/test_git_index_manager.py` now freeze the client-close,
  continuation-aware backlog, and deeper timeout-backoff contract.

Live bounded semantic replay on the repo-local SQLite store now persists
authoritative summaries instead of making zero semantic progress:

- `chunk_summaries`: `0 -> 269`
- `semantic_points`: `0 -> 0`
- Semantic readiness remains `summaries_missing`, so strict vector linkage has
  still not started for the remaining backlog.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Live SEMTIMEOUT rerun evidence from this turn:

- The rerun no longer stayed at zero semantic progress: authoritative summary
  rows were persisted into `chunk_summaries`.
- One oversized archive artifact was still skipped during the same run:
  `analysis_archive/semantic_vs_sql_comparison_1750926162.json` (`32983030`
  bytes).
- The latest reruns no longer emitted the earlier event-loop cleanup warning,
  but they still did not reach strict vector linkage before operator
  interruption.
- The remaining live blocker is still inside repo-wide summary drain. The first
  unsummarized backlog slice after the latest repair remains dominated by
  `.claude/*.md` command/agent documents, and semantic vector writes have not
  started for that backlog yet.

Residual blocker shape after the latest repaired rerun:

- Lexical readiness: `stale_commit`
- Query surface: `index_unavailable`
- Semantic readiness: `summaries_missing`
- `chunk_summaries`: `269`
- `semantic_points`: `0`
- Chunks missing summaries: `33126`
- Chunks missing vectors: `33395`

Current SQLite artifact size after the rerun:

- `.mcp-index/current.db`: `159.4 MB`

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the latest rerun attempt reported:

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

- Current commit: `57bcec0d`
- Indexed commit: `e2e95198`

Semantic evidence after the latest SEMCLOSEOUT replay is now:

- Summary-backed chunks: `269`
- Chunks missing summaries: `33126`
- Vector-linked chunks: `0`
- Chunks missing vectors: `33395`
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

- Repo-local semantic dogfood is currently blocked before semantic query
  routing because the repository query surface is `index_unavailable` on
  `stale_commit`.
- Repo-local semantic dogfood query harness:
  `tests/real_world/test_semantic_search.py -k repo_local_dogfood_queries_stay_on_semantic_path`
  now skips on `stale_commit` instead of reaching semantic-path results.
- Ready-path semantic metadata still remains the target once summaries and
  vectors exist: `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"`.
- `symbol` and lexical probes still point operators at
  `mcp_server/setup/semantic_preflight.py` and
  `mcp_server/cli/repository_commands.py`.
- The remaining downstream work is still in the semantic timeout and linkage
  path centered on `mcp_server/indexing/summarization.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/storage/git_index_manager.py`, and
  `mcp_server/utils/semantic_indexer.py`, with the current hot backlog rooted
  in `.claude/agents/lane-executer.md` and related `.claude/commands/*.md`
  documents.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMCLOSEOUT.

Why:

- The final lexical timeout repairs remain intact.
- Semantic readiness remains `summaries_missing`.
- `chunk_summaries` increased to `234`, which proves the live semantic writer
  now persists authoritative summaries on the repo-local index.
- `semantic_points` remains `0`.
- The repo has regressed back to `stale_commit` because the force-full rerun
  still does not complete cleanly on the active commit.
- The precise remaining blocker is narrower than the stale checked-in report:
  the cleanup leak is gone and repo-wide summary drain now reaches `269`
  authoritative summaries, but the `.claude` document backlog still prevents
  strict vector linkage from starting.

Steering outcome:

- SEMCLOSEOUT repaired the registered-context semantic-stage skip earlier and,
  in this turn, SEMTIMEOUT repaired client cleanup, doc-heavy fallback size,
  and deeper timeout backoff on top of the earlier one-batch summary pass
  behavior.
- Those repairs are enough to prove partial live summary persistence on the
  repo-local index.
- They are not enough to close the phase: semantic summary timeout is still the
  current blocker, so downstream work still belongs to `SEMTIMEOUT` rather
  than to any older handoff.

## Verification

Verification sequence for this SEMCLOSEOUT slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_summarization.py tests/test_profile_aware_semantic_indexer.py -q --no-cov
uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k readme
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

Command-level anchors preserved for contract checks:

- `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_summarization.py tests/test_profile_aware_semantic_indexer.py -q --no-cov`
- `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k readme`
- `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`
- `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
- `env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`

Observed outcomes:

- Owned semantic regression suite: passed (`168 passed`).
- Markdown README production slice remains green from the SEMREADME lexical
  closeout.
- Force-full rebuild still persists non-zero summary progress but does not yet
  advance the indexed commit to the current commit.
- Repository status now shows semantic readiness `summaries_missing` with
  non-zero `Summary-backed chunks: 269` and `Vector-linked chunks: 0`.
- Active-profile semantic preflight: still `ready`.
- Repo-local semantic dogfood harness: still blocked on indexed-query
  unavailability `stale_commit`.
