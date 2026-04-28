# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-28T18:45:19Z`.
- Observed commit: `7f2c9afb`.
- Phase plan: `plans/phase-plan-v7-SEMPASSSTALL.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMCALLTIME` for the newly exposed single-call summary hang.

## Reset Boundary

This SEMPASSSTALL rerun stayed inside the existing repo-local dogfood boundary:

- `.mcp-index/current.db` remained the active SQLite store.
- `qdrant_storage/` was preserved.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of SQLite, WAL, or Qdrant state was used.

The live force-full attempt rebuilt lexical rows but did not reach a durable
semantic checkpoint:

- Files indexed in SQLite: `666`
- Code chunks indexed in SQLite: `8934`
- `chunk_summaries`: `0`
- `semantic_points`: `0`

## README Lexical Repair

SEMREADME remains the lexical prerequisite this phase inherits:

- `README.md` still indexes through the bounded Markdown lexical path.
- The remaining blocker is no longer the README lexical timeout path.
- The current live blocker is in semantic summary execution after lexical rows
  are present.

## SEMPASSSTALL Semantic Recovery

SEMPASSSTALL tightened the repo-scope unit contract in code and tests:

- `mcp_server/indexing/summarization.py` now checkpoints repo-scope summary
  work at one file per pass and one doc-like chunk per file.
- `summarize_file_chunks(...)` now reports `remaining_chunks` and
  `scope_drained` for bounded partial-file progress.
- `tests/test_summarization.py`, `tests/test_dispatcher.py`, and
  `tests/test_git_index_manager.py` now freeze the one-file / one-chunk
  continuation behavior and the dispatcher’s continuation bookkeeping.

The live rerun did not close the phase, because it exposed a narrower blocker:

- A fresh `repository sync --force-full` stayed in flight from approximately
  `2026-04-28T18:42Z` until it was stopped at `2026-04-28T18:45:19Z`.
- During that live window, `chunk_summaries` remained `0` and
  `semantic_points` remained `0`.
- The new blocker is not repo-scope pass breadth anymore. It is a
  single-call summary hang: even the first repo-scope summary invocation does
  not return promptly enough to surface the bounded continuation verdict.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Live SEMPASSSTALL rerun evidence from this turn:

- The force-full rebuild recreated lexical rows in `.mcp-index/current.db`
  (`666` files, `8934` chunks).
- No authoritative semantic progress was persisted:
  `chunk_summaries = 0`, `semantic_points = 0`.
- The rerun did not reach the expected bounded continuation verdict before it
  was manually stopped.
- The narrower blocker is now "single-call summary timeout/hang before first
  authoritative summary write", not the older broad repo-scope pass stall.

Residual blocker shape after the latest repaired rerun:

- Lexical readiness: `stale_commit`
- Query surface: `index_unavailable`
- Semantic readiness: `summaries_missing`
- `chunk_summaries`: `0`
- `semantic_points`: `0`
- Chunks missing summaries: `8934`
- Chunks missing vectors: `8934`

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the stopped rerun reported:

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

- Current commit: `7f2c9afb`
- Indexed commit: `e2e95198`

Semantic evidence after the latest rerun is:

- Summary-backed chunks: `0`
- Chunks missing summaries: `8934`
- Vector-linked chunks: `0`
- Chunks missing vectors: `8934`
- Collection-matched links: `0`
- Collection mismatches: `0`

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
  `mcp_server/utils/semantic_indexer.py`.
- The current hot path is no longer a broad one-batch pass. It is a
  single-file, single-chunk repo-scope summary call that still does not return
  promptly.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMPASSSTALL.

Why:

- The repo-scope pass contract is narrower in code and tests.
- Semantic readiness remains `summaries_missing`.
- `chunk_summaries` remains `0`.
- `semantic_points` remains `0`.
- The force-full rerun still does not return a bounded continuation verdict in
  live repo-local execution.
- The exact blocker is now narrower than the SEMPASSSTALL plan input:
  the remaining problem is a single-call summary timeout/hang with zero
  authoritative summary progress.

Steering outcome:

- SEMPASSSTALL implementation landed, but acceptance did not.
- The roadmap now adds `SEMCALLTIME` as the nearest downstream phase.
- Older downstream assumptions that the remaining issue was only pass-level
  doc-heavy breadth should be treated as stale.

## Verification

Verification sequence for this SEMPASSSTALL slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- Owned semantic regression suite: passed (`176 passed`).
- Live force-full rebuild recreated lexical rows but produced zero summary or
  vector rows before manual stop at `2026-04-28T18:45:19Z`.
- Repository status still shows semantic readiness `summaries_missing` with
  `Summary-backed chunks: 0` and `Vector-linked chunks: 0`.
- Active-profile semantic preflight remains `ready`.
- The next work item is roadmap phase `SEMCALLTIME`, not another retry of the
  older pass-breadth assumption.
