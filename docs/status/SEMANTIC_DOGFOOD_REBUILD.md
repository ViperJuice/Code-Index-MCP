# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T06:24:13Z`.
- Observed commit: `7ec6351`.
- Phase plan: `plans/phase-plan-v7-SEMCALLTIME.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMCANCEL` for the still-unbounded timed-out summary-call exit path.

## Reset Boundary

This SEMCALLTIME rerun stayed inside the existing repo-local dogfood boundary:

- `.mcp-index/current.db` remained the active SQLite store.
- `.mcp-index/semantic_qdrant/` remained the active local vector path.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of SQLite, WAL, or Qdrant state was used.

## README Lexical Repair

SEMREADME remains the lexical prerequisite this phase inherits:

- `README.md` still indexes through the bounded Markdown lexical path.
- The remaining blocker is no longer the README lexical timeout path.
- The current live blocker remains in semantic summary execution after lexical
  rows are present.

## SEMCALLTIME Timeout Recovery

SEMCALLTIME tightened the exact first-call summary blocker in code and tests:

- `mcp_server/indexing/summarization.py` now returns explicit blocked-call
  metadata from the repo-scope summary path, including the timed-out file,
  chunk window, and timeout seconds.
- `mcp_server/dispatcher/dispatcher_enhanced.py` now distinguishes
  `blocked_summary_call_timeout` from the older pass-level
  `blocked_summary_timeout`, `blocked_summary_plateau`, and
  `blocked_missing_summaries` states.
- `mcp_server/storage/git_index_manager.py` and
  `mcp_server/cli/repository_commands.py` now preserve exact timed-out-call
  metadata on failed sync results and keep the latest sync blocker available
  for status reporting once the sync path actually returns.
- `tests/test_summarization.py`, `tests/test_dispatcher.py`, and
  `tests/test_git_index_manager.py` now freeze the exact timed-out-call
  contract.

The live rerun did not close the phase:

- A fresh `repository sync --force-full` started at `2026-04-29T06:19:36Z`.
- The process remained in flight for more than three minutes with
  `chunk_summaries = 0` and `semantic_points = 0`.
- The sync was terminated manually after it failed to return an exact blocker.
- After termination, the active SQLite store had larger lexical row counts
  than the prior SEMCALLTIME input while still preserving zero semantic
  progress.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Live SEMCALLTIME rerun evidence from this turn:

- The force-full rebuild recreated or expanded lexical rows in
  `.mcp-index/current.db`.
- No authoritative semantic progress was persisted:
  `chunk_summaries = 0`, `semantic_points = 0`.
- The rerun still did not return a bounded live blocker after the first
  repo-scope summary window should have timed out.
- Manual termination left a larger lexical-only partial state than the
  previous SEMPASSSTALL evidence snapshot.

Residual blocker shape after the latest repaired rerun:

- Files indexed in SQLite: `1046`
- Code chunks indexed in SQLite: `29194`
- Summary-backed chunks: `0`
- Chunks missing summaries: `29194`
- Vector-linked chunks: `0`
- Chunks missing vectors: `29194`
- Lexical readiness: `stale_commit`
- Query surface: `index_unavailable`
- Semantic readiness: `summaries_missing`

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the terminated rerun reported:

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

- Current commit: `7ec6351`
- Indexed commit: `e2e95198`

The status surface still does not show the new exact timed-out-call blocker
after the live rerun, because the force-full sync never returned cleanly
enough to persist that blocker before manual termination.

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Repo-local semantic dogfood is currently blocked before semantic query
  routing because the repository query surface is `index_unavailable` on
  `stale_commit`.
- Ready-path semantic metadata still remains the target once summaries and
  vectors exist: `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"`.
- `symbol` and lexical probes still point operators at
  `mcp_server/setup/semantic_preflight.py` and
  `mcp_server/cli/repository_commands.py`.
- The remaining downstream work is centered on
  `mcp_server/indexing/summarization.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/storage/git_index_manager.py`, and
  `mcp_server/cli/repository_commands.py`.
- No broader guide or support-matrix change is needed yet; the remaining
  issue is still a repo-local dogfood runtime blocker.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMCALLTIME.

Why:

- The unit-level timed-out summary-call contract is now explicit in code and
  tests.
- Semantic readiness remains `summaries_missing`.
- `chunk_summaries` remains `0`.
- `semantic_points` remains `0`.
- The live force-full rerun still does not exit promptly after the first
  timed-out repo-scope summary call.
- Manual termination leaves a larger lexical-only partial state instead of a
  clean fail-closed blocker.

Steering outcome:

- SEMCALLTIME implementation landed, but acceptance did not.
- The roadmap now adds `SEMCANCEL` as the nearest downstream phase.
- Older downstream assumptions that per-call timeout vocabulary alone would
  finish the live dogfood rerun should be treated as stale.

## Verification

Verification sequence for this SEMCALLTIME slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- Owned semantic regression suite: passed (`181 passed`).
- Live force-full rebuild stayed in flight for more than three minutes and was
  terminated manually after failing to return the exact timed-out-call blocker.
- Repository status still shows semantic readiness `summaries_missing` with
  `Summary-backed chunks: 0` and `Vector-linked chunks: 0`.
- Active-profile semantic preflight remains `ready`.
- The next work item is roadmap phase `SEMCANCEL`, not another retry of the
  older “per-call timeout vocabulary only” assumption.
