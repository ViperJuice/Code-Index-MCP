# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T06:47:14Z`.
- Observed commit: `0032c46a`.
- Phase plan: `plans/phase-plan-v7-SEMCANCEL.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMEXITTRACE` for the still-unbounded live force-full exit path after the
  SEMCANCEL code-side repair landed.

## Reset Boundary

This SEMCANCEL rerun stayed inside the existing repo-local dogfood boundary:

- `.mcp-index/current.db` and `.mcp-index/semantic_qdrant/` remained the only
  active runtime locations touched by the live rerun.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of the SQLite runtime, WAL files, or Qdrant directory
  was used before the rerun.

## SEMCANCEL Exit Recovery

SEMCANCEL tightened the repo-scope timeout exit path in code and tests:

- `mcp_server/indexing/summarization.py` now bounds repo-scope summary-call
  waiting with explicit cancellation settlement instead of waiting
  indefinitely for the first timed-out call to unwind.
- `mcp_server/storage/git_index_manager.py` now snapshots the active
  SQLite/Qdrant runtime, carries SQLite WAL/SHM sidecars, and restores the
  pre-run runtime on zero-summary timed-out-call failures that return through
  the repaired force-full closeout path.
- `tests/test_summarization.py` and `tests/test_git_index_manager.py` now
  freeze both the prompt timeout blocker and the zero-summary runtime restore
  contract.

The live rerun still did not close the phase:

- A fresh `repository sync --force-full` was started from a `missing_index`
  baseline where no active `.mcp-index/current.db` existed yet.
- The process stayed in flight for `1:43` before manual termination.
- While in flight it recreated lexical rows in `.mcp-index/current.db` but
  persisted no semantic progress.
- Because the process never returned through the repaired closeout path, the
  runtime-restore hook could not run before manual termination.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Pre-run runtime state for this SEMCANCEL rerun:

- Active SQLite runtime: missing (`.mcp-index/current.db` did not exist).
- Active Qdrant runtime: missing or empty for local semantic writes.
- Files indexed in SQLite: `0`
- Code chunks indexed in SQLite: `0`
- Summary-backed chunks: `0`
- Vector-linked chunks: `0`

Observed in-flight runtime state before manual termination:

- Files indexed in SQLite: `666`
- Code chunks indexed in SQLite: `8934`
- Summary-backed chunks: `0`
- Chunks missing summaries: `8934`
- Vector-linked chunks: `0`
- Chunks missing vectors: `8934`

Runtime containment verdict for the live rerun:

- Prompt exit: **not restored** in repo-local execution.
- Zero-summary containment before process exit: **not restored** in repo-local
  execution because the process never returned through force-full closeout.
- Unit-level restore contract: **passed** in targeted coverage.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after manual termination reported:

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

- Current commit: `0032c46a`
- Indexed commit: `e2e95198`

The status surface still does not show the repaired exact timed-out-call
blocker after the live rerun, because the command again had to be terminated
before `sync_repository_index(...)` returned and persisted closeout state.

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Repo-local semantic dogfood is still blocked before semantic query routing
  because the repository query surface remains `index_unavailable`.
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
- No broader guide or support-matrix change is needed yet; the remaining issue
  is still a repo-local dogfood runtime blocker.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMCANCEL.

Why:

- The unit-level timeout-settlement and zero-summary runtime-restore contracts
  now pass in owned tests.
- The live force-full rerun still does not exit promptly.
- Manual termination still leaves a lexical-only partial runtime with
  `chunk_summaries = 0` and `semantic_points = 0`.
- Repository status still lands on semantic readiness `summaries_missing`.

Steering outcome:

- SEMCANCEL implementation landed, but acceptance did not.
- The roadmap now adds `SEMEXITTRACE` as the nearest downstream phase.
- Older downstream assumptions that bounded timeout settlement plus restore
  alone would finish the live dogfood rerun should be treated as stale.

## Verification

Verification sequence for this SEMCANCEL slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- Targeted owned unit regression currently passes for the patched timeout and
  restore contracts.
- The live force-full rebuild stayed in flight for `1:43` and was terminated
  manually.
- Repository status still shows semantic readiness `summaries_missing` with
  `Summary-backed chunks: 0` and `Vector-linked chunks: 0`.
- Active-profile semantic preflight remains `ready`.
- The next work item is roadmap phase `SEMEXITTRACE`, not another blind retry
  of the older “timeout settlement plus restore is sufficient” assumption.
