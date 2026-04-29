# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T08:35:12Z`.
- Observed commit: `7335cf35`.
- Phase plan: `plans/phase-plan-v7-SEMJEDI.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMTRACEFRESHNESS` after SEMJEDI proved the exact bounded Markdown repair
  cleared `ai_docs/jedi.md` but the live force-full rerun still hung with a
  stale durable trace.

## Reset Boundary

This SEMJEDI rerun stayed inside the existing repo-local dogfood boundary:

- `.mcp-index/current.db`, `.mcp-index/semantic_qdrant/`, and
  `.mcp-index/force_full_exit_trace.json` remained the only active runtime
  locations touched by the live rerun.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of the SQLite runtime, WAL files, or Qdrant directory
  was used before or after the rerun.

## SEMJEDI Live Lexical Recovery

SEMJEDI made the Jedi-doc boundary explicit in code, tests, and status output:

- `mcp_server/plugins/markdown_plugin/plugin.py` now uses an exact bounded
  Markdown path for `ai_docs/jedi.md` while preserving stored file content and
  document and heading symbol discoverability.
- `mcp_server/dispatcher/dispatcher_enhanced.py` still owns the lexical walk
  and the live progress snapshots consumed by the force-full trace.
- `mcp_server/storage/git_index_manager.py` still owns the persisted
  `force_full_exit_trace.json` contract and exposed the stale-trace downstream
  gap once `ai_docs/jedi.md` was cleared.
- `tests/root_tests/test_markdown_production_scenarios.py` now freezes the
  exact `ai_docs/jedi.md` bounded Markdown contract and keeps unrelated
  `ai_docs/*.md` files on the heavy Markdown path.
- `tests/test_dispatcher.py` proves the lexical walk can finish
  `ai_docs/jedi.md` without invoking the heavy Markdown path or broadening to
  unrelated status Markdown.
- `tests/test_git_index_manager.py` proves the durable trace can move past
  `ai_docs/jedi.md` while still failing closed on a newer downstream blocker.
- `mcp_server/cli/repository_commands.py` now prints
  `Lexical boundary: using exact bounded Markdown indexing for ai_docs/jedi.md`
  when the repo contains that exact file, and
  `tests/test_repository_commands.py` freezes that status wording.

The live rerun still did not close semantic dogfood readiness:

- A fresh `repository sync --force-full` was started with
  `MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5`.
- The repo-local `repository status` surface now reports the exact bounded
  Markdown boundary for `ai_docs/jedi.md`.
- The durable trace no longer points at `ai_docs/jedi.md`.
- The live command remained running for more than two minutes and was
  terminated at `2026-04-29T08:35:12Z` after the durable trace stopped
  refreshing.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Observed runtime state while the force-full command was still hung:

- Files indexed in SQLite: `666`
- Code chunks indexed in SQLite: `5418`
- Summary-backed chunks: `0`
- Chunks missing summaries: `5418`
- Vector-linked chunks: `0`
- Chunks missing vectors: `5418`

Durable stage trace from `.mcp-index/force_full_exit_trace.json`:

- Trace status: `running`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Trace timestamp: `2026-04-29T08:33:47Z`
- Trace current commit: `7335cf35a61804199c4f637d5d1c8ab380be7303`
- Trace indexed commit before:
  `e2e9519858c3683c06b152c94a99e52098beaec6`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/ai_docs/pytest_overview.md`
- In-flight path: `none recorded`

Runtime containment verdict for the live rerun:

- The exact bounded Markdown repair for `ai_docs/jedi.md` is active and the
  durable trace no longer anchors on that file.
- The fast-test report boundary, the bounded `ai_docs/*_overview.md` seam, and
  the exact visual-report Python boundary remain explicit in
  `repository status`.
- Prompt exit is still not restored in repo-local execution.
- The durable trace is now stale rather than precise: it remains frozen on the
  older `ai_docs/pytest_overview.md` marker and never names a current
  `in_flight_path`.
- The partial runtime still ends with no `chunk_summaries` and no
  `semantic_points`.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
while the SEMJEDI rerun was still hung reported:

- Lexical readiness: `stale_commit`
- Semantic readiness: `summaries_missing`
- Active-profile preflight: `ready`
- Can write semantic vectors: `yes`
- Active profile: `oss_high`
- Active collection: `code_index__oss_high__v1`
- Collection bootstrap state: `reused`
- Query surface: `index_unavailable`
- Rollout status: `stale_commit`
- Lexical boundary:
  `ignoring generated fast-test reports matching fast_test_results/fast_report_*.md`
- Lexical boundary:
  `using bounded Markdown indexing for ai_docs/*_overview.md`
- Lexical boundary:
  `using exact bounded Markdown indexing for ai_docs/jedi.md`
- Lexical boundary:
  `using exact bounded Python indexing for scripts/create_multi_repo_visual_report.py`
- Force-full exit trace stage: `lexical_walking`
- Force-full exit trace stage family: `lexical`
- Force-full exit trace blocker source: `lexical_mutation`
- Force-full exit trace last progress path:
  `/home/viperjuice/code/Code-Index-MCP/ai_docs/pytest_overview.md`

Repository/index freshness evidence:

- Current commit: `7335cf35`
- Indexed commit: `e2e95198`

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Repo-local semantic dogfood is still blocked before semantic query routing
  because the repository query surface remains `index_unavailable`.
- Ready-path semantic metadata still remains the target once summaries and
  vectors exist: `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"`.
- `symbol` and lexical probes still point operators at
  `mcp_server/setup/semantic_preflight.py`, `ai_docs/jedi.md`, and
  `mcp_server/cli/repository_commands.py`.
- The remaining downstream work is no longer centered on `ai_docs/jedi.md`.
  It is now centered on the stale force-full trace that remains frozen at the
  older `ai_docs/pytest_overview.md` progress marker.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMJEDI.

Why:

- The exact bounded Markdown repair for `ai_docs/jedi.md` is explicit, narrow,
  and reflected in `repository status`.
- The durable trace no longer leaves the live rerun anchored on
  `ai_docs/jedi.md`.
- The live force-full rerun still did not complete cleanly and the persisted
  trace stopped refreshing while still reporting `lexical_walking`.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`.

Steering outcome:

- SEMJEDI acceptance is satisfied: the live repo-local force-full rerun no
  longer leaves the durable trace anchored on `ai_docs/jedi.md`.
- The roadmap now adds `SEMTRACEFRESHNESS` as the nearest downstream phase.
- Older downstream assumptions should be treated as stale. The next repair is
  not another retry of the Jedi seam; it is a bounded recovery for the stale
  force-full trace so the live rerun can report the true downstream blocker.

## Verification

Verification sequence for this SEMJEDI slice:

```bash
uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- Targeted owned regression for the exact bounded Markdown rule, durable-trace
  handoff, repository-status wording, and root Markdown production scenarios
  passes.
- The live force-full rebuild no longer leaves the durable trace on
  `ai_docs/jedi.md`, but the command hung for more than two minutes and was
  terminated after the persisted trace stopped refreshing.
- Repository status now shows the explicit fast-test report boundary, the
  explicit `ai_docs/*_overview.md` boundary, the exact bounded Markdown
  boundary for `ai_docs/jedi.md`, and the exact bounded Python boundary for
  `scripts/create_multi_repo_visual_report.py` directly.
- The next work item is roadmap phase `SEMTRACEFRESHNESS`, not another retry
  of the Jedi seam.
