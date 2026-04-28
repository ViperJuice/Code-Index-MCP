# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-28T12:30:53Z`.
- Observed commit: `340008a5`.
- Phase plan: `plans/phase-plan-v7-SEMTHROUGHPUT.md`.
- Roadmap follow-up added during execution: `SEMSTALLFIX` in `specs/phase-plans-v7.md`.

## Reset Boundary

This SEMTHROUGHPUT run reused the repo-local reset boundary that already
existed in this worktree:

- `.mcp-index/current.db` remained the active SQLite store.
- `qdrant_storage/` was preserved.
- No unrelated Qdrant collections were deleted.

The lexical pass still skips one oversized JSON artifact:

- `analysis_archive/semantic_vs_sql_comparison_1750926162.json` at `32983030`
  bytes.

## Full-Sync Recovery

SEMTHROUGHPUT changed the large-file summary path itself:

- `FileBatchSummarizer.summarize_file_chunks(...)` no longer jumps straight
  from `FileTooLargeError` to per-chunk topological fallback.
- When a file exceeds `_BATCH_FILE_SIZE_THRESHOLD`, the full-sync path now
  attempts bounded profile-backed summary batches before allowing topological
  fallback.
- This remains downstream of the earlier BAML generator/runtime mismatch
  repair (`0.220.0` vs `baml-py 0.221.0`); the new path keeps that mismatch
  from forcing the slowest fallback immediately.
- The new tests keep the authoritative audit contract intact for
  `is_authoritative=1`, `provider_name`, `profile_id`, configured model, and
  effective model metadata.

Live force-full evidence after the repair:

- Pre-phase SEMSYNCFIX evidence stopped at roughly `chunk_summaries=2465`,
  `semantic_points=0`, and semantic readiness `summaries_missing`.
- After the SEMTHROUGHPUT patch, a fresh `repository sync --force-full` run
  raised `chunk_summaries` to `3018`.
- The same run never produced any `semantic_points`.
- The same run also never refreshed the indexed commit to the current commit.

This proves the oversized-file recovery path now makes additional durable
summary progress, but one force-full pass still does not complete the semantic
handoff.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

- The SEMTHROUGHPUT force-full run stayed active for about 22 minutes before
  manual interruption once summary counts plateaued and the process no longer
  emitted stage-completion output.
- During that run, direct SQLite probes showed `chunk_summaries=3018` and
  `semantic_points=0`.
- No semantic vector writes became visible in `.mcp-index/current.db`.

SQLite counts after interrupting the stalled run:

- `chunk_summaries`: `3018`
- `semantic_points`: `0`

The rebuild therefore improved summary throughput without satisfying the
one-pass completion contract.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status` after
the interrupted rebuild reported:

- Lexical readiness: `stale_commit`.
- Semantic readiness: `summaries_missing`.
- Active-profile preflight: `ready`.
- Can write semantic vectors: `yes`.
- Active profile: `oss_high`.
- Active collection: `code_index__oss_high__v1`.
- Collection bootstrap state: `reused`.
- Query surface: `index_unavailable`.
- Rollout status: `stale_commit`.

Repository/index freshness evidence:

- Current commit: `340008a5`.
- Indexed commit: `93f00d29`.
- Readiness remediation: `Run reindex to update the repository index to the current commit.`

Semantic evidence after the interrupted rebuild:

- Summary-backed chunks: `3018`.
- Chunks missing summaries: `64124`.
- Vector-linked chunks: `0`.
- Chunks missing vectors: `67142`.
- Collection-matched links: `0`.
- Collection mismatches: `0`.

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`
confirmed the active profile is still preflight-ready:

- Configured enrichment model: `chat`.
- Effective enrichment model:
  `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`.
- Enrichment chat smoke: `ready`.
- Embedding smoke: `ready`.
- Collection check: `ready`.

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Semantic query:
  now returns `code: "index_unavailable"` with
  `safe_fallback: "native_search"` because repository readiness stayed at
  `stale_commit` after the interrupted force-full run.
- The pre-SEMTHROUGHPUT dogfood query shape is still relevant context:
  before the force-full stall became the primary blocker, the same prompt
  returned `semantic_not_ready` with `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"` while readiness was
  blocked at `summaries_missing`.
- Symbol query:
  `symbol_lookup("run_semantic_preflight")` is still the native fallback probe
  for `mcp_server/setup/semantic_preflight.py` while indexed search is not
  ready.

Fixed operator prompt: `where does repository status print semantic readiness evidence`

- Repository status still points operators at
  `mcp_server/cli/repository_commands.py`.
- The large-file throughput repair lives in
  `mcp_server/indexing/summarization.py`.
- The strict summary-before-vector stage handoff still lives in
  `mcp_server/dispatcher/dispatcher_enhanced.py`.
- The remaining blocker is no longer only `semantic_not_ready`; the active
  force-full path is still failing to finish cleanly enough to refresh the
  registered index on the current commit.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMTHROUGHPUT.

Why:

- SEMTHROUGHPUT repaired the oversized-file summary recovery path and improved
  durable summary counts.
- The repaired path still left the force-full rebuild incomplete on the active
  commit.
- Repository readiness remained `stale_commit`, so `search_code(semantic=true)`
  returned `index_unavailable` before semantic query acceptance could even be
  re-evaluated on a fresh index.
- Semantic readiness also remained `summaries_missing`.
- The same rebuild still produced `0` `semantic_points`.

Steering outcome:

- SEMTHROUGHPUT completed the large-file summary recovery slice.
- The remaining blocker has moved downstream into force-full rebuild
  completion and indexed-commit freshness after summary throughput improves.
- The roadmap now needs `SEMSTALLFIX` to finish the durable force-full
  completion path before semantic vectors and repo-local semantic queries can
  pass.

## Verification

Executed in this phase:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov -k "index_directory_runs_lexical_then_summaries_then_semantic or index_directory_blocks_semantic_stage_when_summaries_missing or index_directory_retries_summary_generation_until_scope_is_drained or index_directory_bootstraps_missing_collection_before_semantic_writes"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov -k "full_index_preserves_semantic_stats_when_blocked_on_missing_summaries or full_index_preserves_semantic_ready_stats_when_force_full_rebuild_succeeds"
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- Phase-owned summarization tests: passed.
- Phase-owned dispatcher/git-index manager acceptance slice: pending rerun
  against the final docs/test updates, but no owned runtime regressions were
  observed before the long force-full verification became the blocker.
- Force-full rebuild: improved summary counts to `3018`, then stalled and was
  interrupted after about 22 minutes without refreshing the indexed commit.
- Repository status: `stale_commit` plus semantic readiness `summaries_missing`.
- Repo-local semantic dogfood query: now fails closed with
  `index_unavailable` / `safe_fallback: "native_search"` because indexed
  readiness never returned to `ready`.
