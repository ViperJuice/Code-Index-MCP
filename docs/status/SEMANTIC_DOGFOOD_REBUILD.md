# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-28T11:43:09Z`.
- Observed commit: `93f00d29`.
- Phase plan: `plans/phase-plan-v7-SEMSYNCFIX.md`.
- Roadmap follow-up added during execution: `SEMTHROUGHPUT` in `specs/phase-plans-v7.md`.

## Reset Boundary

This SEMSYNCFIX run reused the repo-local reset boundary that already existed
in this worktree:

- `.mcp-index/current.db` remained the active SQLite store.
- `qdrant_storage/` was preserved.
- No unrelated Qdrant collections were deleted.

The rebuild still skipped one oversized file during lexical indexing:

- `analysis_archive/semantic_vs_sql_comparison_1750926162.json` at `32983030`
  bytes.

## Full-Sync Recovery

SEMSYNCFIX repaired two correctness gaps in the full-sync summary path:

- `ComprehensiveChunkWriter._fetch_unsummarized_rows(...)` now scopes before
  applying `LIMIT`, so targeted rebuilds no longer starve on unrelated rows.
- `EnhancedDispatcher.rebuild_semantic_for_paths(...)` now retries summary
  passes until scoped missing-summary counts stop shrinking, instead of making
  a single partial pass before declaring `blocked_missing_summaries`.

SEMSYNCFIX also added a new BAML-mismatch recovery path for full sync:

- `FileBatchSummarizer.summarize_file_chunks(...)` still attempts the BAML
  batch runtime first.
- When that batch call fails on the current generator/runtime mismatch
  (`0.220.0` vs `baml-py 0.221.0`), the full-sync path now attempts direct
  profile-backed summary batches before falling all the way back to per-chunk
  recovery.

Live probe evidence after the repair:

- Pre-repair force-full rebuild: `chunk_summaries=125`, `semantic_points=0`.
- After a targeted post-patch probe against `specs/phase-plans-v1.md`,
  `chunk_summaries` rose from `125` to `1111`, proving the new direct batch
  fallback can make durable progress on the previously stuck markdown/spec
  backlog.
- A second clean force-full rebuild then increased `chunk_summaries` again to
  `2465`, but still did not clear repo-wide summary coverage.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

- First SEMSYNCFIX acceptance rebuild: exit status `0`,
  `Indexed 1380 files in 1405.6s`.
- Second SEMSYNCFIX acceptance rebuild after the direct batch fallback landed:
  exit status `0`, `Indexed 1380 files in 1504.4s`.

SQLite counts from `.mcp-index/current.db` immediately after the second
force-full rebuild:

- `chunk_summaries`: `2463` from the direct SQLite count command and `2465`
  from `repository status` evidence captured moments later.
- `semantic_points`: `0`.

This proves the repaired full-sync path now writes far more authoritative
summary rows than the earlier manual-probe-only baseline, but it still does
not drain repo-wide summary work within one force-full rebuild.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status` after
the second rebuild reported:

- Lexical readiness: `ready`.
- Semantic readiness: `summaries_missing`.
- Active-profile preflight: `ready`.
- Can write semantic vectors: `yes`.
- Active profile: `oss_high`.
- Active collection: `code_index__oss_high__v1`.
- Collection bootstrap state: `reused`.
- Semantic remediation: `Run semantic summary/vector generation for the current profile before semantic queries.`

Semantic evidence after the rebuild:

- Summary-backed chunks: `2465`.
- Chunks missing summaries: `64514`.
- Vector-linked chunks: `0`.
- Chunks missing vectors: `66979`.
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
  still returns `code: "semantic_not_ready"` with
  `semantic_source: "semantic"`,
  `semantic_collection_name: "code_index__oss_high__v1"`, and readiness state
  `summaries_missing`.
- Symbol query:
  `symbol_lookup("run_semantic_preflight")` still resolves the implementation
  symbol in `mcp_server/setup/semantic_preflight.py`.

Fixed operator prompt: `where does repository status print semantic readiness evidence`

- Repository status still points operators at
  `mcp_server/cli/repository_commands.py`.
- The repaired full-sync recovery lives in
  `mcp_server/indexing/summarization.py` and
  `mcp_server/dispatcher/dispatcher_enhanced.py`.
- The remaining blocker is now summary throughput across the large
  markdown/plaintext backlog.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMSYNCFIX.

Why:

- SEMSYNCFIX repaired the scoped summary selection and strict retry logic, and
  it materially improved live full-sync summary coverage.
- The direct batch fallback also proved it can drain the previously stuck
  markdown/spec backlog when the BAML runtime mismatch is hit.
- The real `repository sync --force-full` path still leaves semantic readiness
  at `summaries_missing` after `2465` summary-backed chunks, so vector writes
  still never start.
- The same rebuild still produced `0` `semantic_points`.
- Repo-local semantic dogfood queries still stay fail-closed with
  `semantic_not_ready`.

Steering outcome:

- SEMSYNCFIX completed the full-sync scoping/retry repair slice.
- The remaining blocker has moved downstream into summary throughput for the
  large markdown/plaintext backlog that still dominates repo-wide missing
  summaries.
- The roadmap now needs `SEMTHROUGHPUT` to finish the durable batch recovery
  path before semantic vectors and dogfood queries can pass.

## Verification

Executed in this phase:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

Observed outcomes:

- Phase-owned SEMSYNCFIX unit slice: passed.
- First force-full rebuild: completed successfully and reproduced the still
  blocked state at `chunk_summaries=125`, `semantic_points=0`.
- Post-patch targeted summary probe on `specs/phase-plans-v1.md`: increased
  `chunk_summaries` from `125` to `1111`, proving direct batch recovery can
  make durable progress on the large markdown/spec backlog.
- Second force-full rebuild: completed successfully and increased
  `chunk_summaries` again to `2463`, but still left semantic readiness at
  `summaries_missing`.
- Repo-local semantic dogfood query: still skipped with the exact blocker
  `summaries_missing`.
