# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-28T12:57:58Z`.
- Observed commit: `340008a5`.
- Phase plan: `plans/phase-plan-v7-SEMSTALLFIX.md`.
- Roadmap follow-up added during execution: `SEMIOWAIT` in `specs/phase-plans-v7.md`.

## Reset Boundary

This SEMSTALLFIX run kept the same repo-local reset boundary and repo-local
dogfood boundary:

- `.mcp-index/current.db` remained the active SQLite store.
- `qdrant_storage/` was preserved.
- No unrelated Qdrant collections were deleted.
- The active semantic collection remained `code_index__oss_high__v1`.

Current durable counts before and after the live rerun stayed:

- `chunk_summaries`: `3018`
- `semantic_points`: `0`

## Force-Full Stall Remediation

SEMSTALLFIX tightened the force-full semantic-stage contract itself:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now records bounded semantic
  outcomes for repeated summary passes, zero-progress plateaus, semantic
  preflight blockers, semantic batch blockers, and timeout-shaped semantic
  handoff failures.
- The dispatcher now emits exact stage strings including
  `blocked_summary_plateau`, `blocked_summary_timeout`,
  `blocked_semantic_batch`, and `blocked_semantic_batch_timeout` instead of
  collapsing everything after summary generation into a generic blocked/failed
  outcome.
- This remains downstream of the earlier authoritative summary-runtime repair
  that moved the repo off the `baml-py` generator/runtime mismatch blocker.
- `mcp_server/storage/git_index_manager.py` now treats non-success semantic
  stages as exact force-full blockers, so `sync_repository_index(..., force_full=True)`
  no longer looks clean or advances the indexed commit when the semantic stage
  reports a bounded blocker.
- The owned tests in `tests/test_dispatcher.py` and
  `tests/test_git_index_manager.py` now freeze those exact closeout contracts.

This repaired the semantic-stage accounting surface, but it did not fully clear
the live repo-local dogfood blocker.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Live SEMSTALLFIX rerun evidence:

- A fresh force-full rerun was started against the patched dispatcher.
- After more than three minutes, the command was still active and had not
  emitted a bounded semantic-stage exit.
- During that live rerun, direct SQLite probes still showed
  `chunk_summaries=3018` and `semantic_points=0`.
- The same rerun therefore did not reach a durable semantic-stage outcome, did
  not refresh the indexed commit, and remained below the stage-accounting path
  that SEMSTALLFIX hardened.

Residual blocker interpretation:

- The semantic-stage contracts are now bounded in tests.
- The live repo-local stall still appears earlier or lower-level than those
  semantic-stage outcomes, because the bounded dispatcher blocker vocabulary
  never surfaced during the dogfood rerun.
- The next blocker is therefore narrower than SEMTHROUGHPUT and SEMSTALLFIX:
  the real force-full path still needs low-level stall forensics before the
  indexed commit can refresh.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the interrupted rerun still reported:

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

Semantic evidence after the rerun remained:

- Summary-backed chunks: `3018`.
- Chunks missing summaries: `64124`.
- Vector-linked chunks: `0`.
- Chunks missing vectors: `67142`.
- Collection-matched links: `0`.
- Collection mismatches: `0`.

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`
still confirmed the active profile is preflight-ready:

- Configured enrichment model: `chat`.
- Effective enrichment model:
  `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`.
- Enrichment chat smoke: `ready`.
- Embedding smoke: `ready`.
- Collection check: `ready`.

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Semantic query:
  still returns `code: "index_unavailable"` with
  `safe_fallback: "native_search"` because repository readiness remains
  `stale_commit`.
- The earlier pre-stall semantic-ready refusal shape, `semantic_not_ready`,
  remains the comparison point for semantic-path failures that occur after the
  indexed repo is fresh enough to enter semantic readiness checks.
- When indexed semantic queries recover, the expected ready metadata still
  includes `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"`.
- The semantic-stage repair narrowed the internal force-full blocker
  vocabulary to `blocked_summary_plateau`, `blocked_summary_timeout`,
  `blocked_semantic_batch`, and `blocked_semantic_batch_timeout`, but the live
  repo-local rerun did not surface one of those bounded outcomes before it
  stalled.
- Symbol query:
  `symbol_lookup("run_semantic_preflight")` remains the native fallback probe
  for `mcp_server/setup/semantic_preflight.py` while indexed search is not
  ready.

Fixed operator prompt: `where does repository status print semantic readiness evidence`

- Repository status still points operators at
  `mcp_server/cli/repository_commands.py`.
- The bounded semantic-stage repair now lives in
  `mcp_server/dispatcher/dispatcher_enhanced.py`.
- The force-full closeout refusal now lives in
  `mcp_server/storage/git_index_manager.py`.
- Summary generation still routes through
  `mcp_server/indexing/summarization.py`.
- The remaining live blocker is now below the bounded semantic-stage layer.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMSTALLFIX.

Why:

- SEMSTALLFIX repaired the semantic-stage and full-index closeout contracts in
  owned tests.
- The live repo-local force-full rerun still failed to finish on the active
  commit.
- Repository readiness remained `stale_commit`, so indexed semantic queries
  still failed closed with `index_unavailable`.
- Semantic readiness also remained `summaries_missing`.
- The same rerun still produced `0` `semantic_points`.

Steering outcome:

- SEMSTALLFIX completed the dispatcher/git-index-manager contract-hardening
  slice.
- The residual blocker is now a lower-level force-full stall that still does
  not surface through the bounded semantic-stage outcomes.
- The roadmap now needs `SEMIOWAIT` to isolate and repair that low-level
  stall before semantic vectors and repo-local semantic queries can pass.

## Verification

Verification sequence for this blocked slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- The active SEMSTALLFIX dispatcher and git-index-manager suites: passed after
  the new bounded semantic-stage contract and closeout assertions were added.
- The carried-forward summarization regression command remains part of the
  verification sequence, but the live blocker in this phase was downstream of
  that surface.
- Repo-local semantic dogfood query harness:
  pending rerun against a live repo that actually returns to indexed readiness;
  current repo-local indexed semantic queries still fail closed with
  `index_unavailable`.
- Force-full rebuild:
  rerun remained active for more than three minutes without refreshing the
  indexed commit or changing the durable semantic counts.
- Repository status:
  still `stale_commit` plus semantic readiness `summaries_missing`.
- Repo-local semantic dogfood query:
  still fails closed with `index_unavailable` /
  `safe_fallback: "native_search"` because indexed readiness never returned to
  `ready`.
