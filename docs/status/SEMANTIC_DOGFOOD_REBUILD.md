# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T07:49:50Z`.
- Observed commit: `6be33712`.
- Phase plan: `plans/phase-plan-v7-SEMPYTESTOVERVIEW.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMVISUALREPORT` after SEMPYTESTOVERVIEW proved the bounded
  `ai_docs/*_overview.md` repair cleared `ai_docs/pytest_overview.md` but the
  live lexical progress marker advanced to
  `scripts/create_multi_repo_visual_report.py`.

## Reset Boundary

This SEMFASTREPORT rerun stayed inside the existing repo-local dogfood
boundary:

- `.mcp-index/current.db`, `.mcp-index/semantic_qdrant/`, and
  `.mcp-index/force_full_exit_trace.json` remained the only active runtime
  locations touched by the live rerun.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of the SQLite runtime, WAL files, or Qdrant directory
  was used before or after the rerun.

## SEMPYTESTOVERVIEW Live Lexical Recovery

SEMPYTESTOVERVIEW made the bounded pytest-overview boundary explicit in code,
tests, and status output:

- `mcp_server/plugins/markdown_plugin/plugin.py` now treats direct
  `ai_docs/*_overview.md` files as a bounded Markdown class with lightweight
  title and heading extraction.
- `mcp_server/dispatcher/dispatcher_enhanced.py` still owns the lexical walk
  and consumed the repaired overview boundary without broader docs-wide
  Markdown-path changes.
- `mcp_server/storage/git_index_manager.py` still owns the persisted
  force-full trace and proved the blocker moved past
  `ai_docs/pytest_overview.md`.
- `mcp_server/cli/repository_commands.py` now surfaces the explicit lexical
  boundary alongside the durable trace.
- `tests/test_dispatcher.py` proves `ai_docs/pytest_overview.md` stays on the
  bounded path with heading discoverability preserved, while
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` still takes the heavy Markdown
  path.
- `tests/test_git_index_manager.py` proves the durable trace can move past
  `ai_docs/pytest_overview.md` while still failing closed on a new downstream
  lexical blocker.
- `mcp_server/cli/repository_commands.py` now prints
  `Lexical boundary: using bounded Markdown indexing for ai_docs/*_overview.md`
  when the repo contains that narrow class, and
  `tests/test_repository_commands.py` freezes that status wording.

The live rerun still did not close semantic dogfood readiness:

- A fresh `repository sync --force-full` was started with
  `MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5`.
- The durable trace advanced beyond `ai_docs/pytest_overview.md`.
- The most recent durable lexical progress marker became
  `/home/viperjuice/code/Code-Index-MCP/scripts/create_multi_repo_visual_report.py`.
- The process later exited with code `135` before writing a newer durable
  trace snapshot, so the last durable lexical trace remains the
  `2026-04-29T07:49:07Z` `lexical_walking` update on that script path.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Observed in-flight runtime state after external termination:

- Files indexed in SQLite: `666`
- Code chunks indexed in SQLite: `8914`
- Summary-backed chunks: `0`
- Chunks missing summaries: `8914`
- Vector-linked chunks: `0`
- Chunks missing vectors: `8914`

Durable stage trace from `.mcp-index/force_full_exit_trace.json`:

- Trace status: `running`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Trace timestamp: `2026-04-29T07:49:07Z`
- Trace current commit: `6be33712225f4eaf24b151620bdfa12deacb7247`
- Trace indexed commit before:
  `e2e9519858c3683c06b152c94a99e52098beaec6`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/scripts/create_multi_repo_visual_report.py`

Runtime containment verdict for the live rerun:

- The generated fast-test report family and the bounded
  `ai_docs/pytest_overview.md` seam are no longer the active lexical blocker.
- Prompt exit is still not restored in repo-local execution.
- External termination still left the partial lexical runtime in place, with
  no `chunk_summaries` or `semantic_points` written.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after external termination reported:

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
- Force-full exit trace stage: `lexical_walking`
- Force-full exit trace stage family: `lexical`
- Force-full exit trace blocker source: `lexical_mutation`
- Force-full exit trace last progress path:
  `/home/viperjuice/code/Code-Index-MCP/scripts/create_multi_repo_visual_report.py`

Repository/index freshness evidence:

- Current commit: `feda36fc`
- Indexed commit: `e2e95198`

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Repo-local semantic dogfood is still blocked before semantic query routing
  because the repository query surface remains `index_unavailable`.
- Ready-path semantic metadata still remains the target once summaries and
  vectors exist: `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"`.
- `symbol` and lexical probes still point operators at
  `mcp_server/setup/semantic_preflight.py`,
  `scripts/create_multi_repo_visual_report.py`, and
  `mcp_server/cli/repository_commands.py`.
- The remaining downstream work is no longer centered on
  `ai_docs/pytest_overview.md`. It is now centered on the lexical handling of
  `scripts/create_multi_repo_visual_report.py`.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMPYTESTOVERVIEW.

Why:

- The fast-test report boundary and the bounded `ai_docs/*_overview.md`
  boundary are explicit, narrow, and reflected in `repository status`.
- The durable trace proves the live rerun advanced beyond
  `ai_docs/pytest_overview.md`.
- The live force-full rerun still did not complete cleanly and the last
  durable lexical trace now points at
  `scripts/create_multi_repo_visual_report.py`.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`.

Steering outcome:

- SEMPYTESTOVERVIEW acceptance is satisfied: the live repo-local force-full
  rerun no longer leaves the durable trace anchored on
  `ai_docs/pytest_overview.md`.
- The roadmap now adds `SEMVISUALREPORT` as the nearest downstream phase.
- Older downstream assumptions should be treated as stale. The next repair is
  not another retry of the overview-doc seam; it is a bounded recovery for
  `scripts/create_multi_repo_visual_report.py` or the next narrower blocker
  that script path exposes.

## Verification

Verification sequence for this SEMPYTESTOVERVIEW slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- Targeted owned regression for the bounded `ai_docs/*_overview.md` rule and
  repository-status wording passes.
- The live force-full rebuild moved beyond `ai_docs/pytest_overview.md` and
  carried the latest durable lexical progress marker to
  `scripts/create_multi_repo_visual_report.py`.
- Repository status now shows both the explicit fast-test report boundary and
  the explicit `ai_docs/*_overview.md` boundary directly.
- The next work item is roadmap phase `SEMVISUALREPORT`, not another retry of
  the older overview-doc assumption.
