# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-28T10:19:00Z`.
- Observed commit: `62ad8fae`.
- Phase plan: `plans/phase-plan-v7-SEMSUMFIX.md`.
- Roadmap follow-up added during execution: `SEMSYNCFIX` in `specs/phase-plans-v7.md`.

## Reset Boundary

This SEMSUMFIX run reused the repo-local reset boundary that already existed
in this worktree:

- `.mcp-index/current.db` remained the active SQLite store.
- `qdrant_storage/` was preserved.
- No unrelated Qdrant collections were deleted.

The rebuild still skipped one oversized file during lexical indexing:

- `analysis_archive/semantic_vs_sql_comparison_1750926162.json` at `32983030`
  bytes.

## Summary Runtime Recovery

The direct authoritative summary runtime is now repaired for the default local
`oss_high` path even though the generated BAML client still reports version
`0.220.0` and the locked runtime still installs `baml-py 0.221.0`.

Observed repair path:

- `FileBatchSummarizer.summarize_file_chunks(...)` still attempts the BAML
  batch runtime first.
- When that batch import fails with the current `baml-py` mismatch, the
  summary path now falls back to the existing direct profile API route and
  persists those recovered summaries as `is_authoritative=1`.
- The fallback no longer imports BAML-only summary types during recovery, so
  the same mismatch does not re-break the per-chunk path.

Direct probe outcomes:

- `ComprehensiveChunkWriter.process_scope(limit=5)` wrote `5` authoritative
  summaries and returned `authoritative_chunks=5`.
- `ComprehensiveChunkWriter.process_scope(limit=20)` wrote `20` authoritative
  summaries and returned `authoritative_chunks=20`.
- `ComprehensiveChunkWriter.process_scope(limit=100)` wrote `100`
  authoritative summaries in `47.96s` and returned
  `authoritative_chunks=100`.

Audit metadata remained intact on the recovered path:

- Provider: `openai_compatible`.
- Active profile: `oss_high`.
- Configured enrichment model: `chat`.
- Effective enrichment model:
  `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`.
- Resolution strategy: `single_served_model_for_chat_alias`.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

- Exit status: `0`.
- CLI result: `Indexed 1379 files in 1395.5s`.

SQLite counts from `.mcp-index/current.db` immediately after the force-full
rebuild:

- `chunk_summaries`: `5`.
- `semantic_points`: `0`.

SQLite counts after the direct post-rebuild summary probes above:

- `chunk_summaries`: `125`.
- `semantic_points`: `0`.

This proves the repaired direct summary runtime can write authoritative rows,
but the real full-sync path still does not drain repo-wide summary work.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status` after
the rebuild reported:

- Lexical readiness: `ready`.
- Semantic readiness: `summaries_missing`.
- Active-profile preflight: `ready`.
- Can write semantic vectors: `yes`.
- Active profile: `oss_high`.
- Active collection: `code_index__oss_high__v1`.
- Collection bootstrap state: `reused`.
- Semantic remediation: `Run semantic summary/vector generation for the current profile before semantic queries.`

Semantic evidence after the rebuild:

- Summary-backed chunks: `5`.
- Chunks missing summaries: `66814`.
- Vector-linked chunks: `0`.
- Chunks missing vectors: `66819`.
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
- The repaired direct summary runtime lives in
  `mcp_server/indexing/summarization.py`.
- The remaining full-sync blocker now points at
  `mcp_server/dispatcher/dispatcher_enhanced.py`.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMSUMFIX.

Why:

- SEMSUMFIX repaired the direct authoritative summary runtime for `oss_high`
  even when the BAML batch import fails on the `0.220.0` vs `0.221.0`
  generator/runtime mismatch.
- Manual post-rebuild probes can now write authoritative summaries with the
  expected profile/provider audit metadata.
- The real `repository sync --force-full` path still leaves semantic readiness
  at `summaries_missing`.
- The same rebuild still produced `0` `semantic_points`.
- Repo-local semantic dogfood queries still stay fail-closed with
  `semantic_not_ready`.

Steering outcome:

- SEMSUMFIX completed the direct summary-runtime recovery slice.
- The remaining blocker has moved downstream into full-sync summary coverage
  and strict semantic readiness accounting.
- The roadmap now needs `SEMSYNCFIX` to repair the real rebuild path before
  semantic vectors and dogfood queries can pass.

## Verification

Executed in this phase:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run python - <<'PY'
...
PY
uv sync --locked
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

Observed outcomes:

- Phase-owned unit slice: passed (`25 passed`).
- Direct summary probe: recovered from the live `baml-py` mismatch and wrote
  authoritative summaries.
- Force-full rebuild: completed successfully but left semantic readiness at
  `summaries_missing`.
- Post-rebuild manual probes: increased `chunk_summaries` from `5` to `125`
  without producing any `semantic_points`.
- Repo-local semantic dogfood query: skipped with the exact blocker
  `summaries_missing`.
