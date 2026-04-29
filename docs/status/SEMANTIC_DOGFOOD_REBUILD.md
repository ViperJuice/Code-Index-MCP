# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T08:13:25Z`.
- Observed commit: `6aae3502`.
- Phase plan: `plans/phase-plan-v7-SEMVISUALREPORT.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMJEDI` after SEMVISUALREPORT proved the exact bounded Python repair
  cleared `scripts/create_multi_repo_visual_report.py` but the live lexical
  progress marker advanced to `ai_docs/jedi.md`.

## Reset Boundary

This SEMVISUALREPORT rerun stayed inside the existing repo-local dogfood
boundary:

- `.mcp-index/current.db`, `.mcp-index/semantic_qdrant/`, and
  `.mcp-index/force_full_exit_trace.json` remained the only active runtime
  locations touched by the live rerun.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of the SQLite runtime, WAL files, or Qdrant directory
  was used before or after the rerun.

## SEMVISUALREPORT Live Lexical Recovery

SEMVISUALREPORT made the visual-report-script boundary explicit in code,
tests, and status output:

- `mcp_server/plugins/python_plugin/plugin.py` now uses an exact bounded
  Python chunk path for `scripts/create_multi_repo_visual_report.py` while
  preserving stored file content and top-level symbol discoverability.
- `mcp_server/dispatcher/dispatcher_enhanced.py` still owns the lexical walk
  and consumed the repaired visual-report boundary without broadening Python
  timeout behavior for unrelated files.
- `mcp_server/storage/git_index_manager.py` still owns the persisted
  force-full trace and proved the blocker moved past
  `scripts/create_multi_repo_visual_report.py`.
- `tests/test_python_plugin.py` proves the visual-report script no longer
  calls the heavyweight Python chunker and also proves the repair does not
  broaden to another Python file.
- `tests/test_dispatcher.py` proves the lexical walk can finish
  `scripts/create_multi_repo_visual_report.py` without suppressing the
  watchdog for unrelated Python timeouts.
- `tests/test_git_index_manager.py` proves the durable trace can move past
  `scripts/create_multi_repo_visual_report.py` while still failing closed on a
  new downstream lexical blocker.
- `mcp_server/cli/repository_commands.py` now prints
  `Lexical boundary: using exact bounded Python indexing for scripts/create_multi_repo_visual_report.py`
  when the repo contains that exact script, and
  `tests/test_repository_commands.py` freezes that status wording.

The live rerun still did not close semantic dogfood readiness:

- A fresh `repository sync --force-full` was started with
  `MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5`.
- The durable trace advanced beyond
  `scripts/create_multi_repo_visual_report.py`.
- The most recent durable lexical progress marker became
  `/home/viperjuice/code/Code-Index-MCP/ai_docs/jedi.md`.
- The command later exited with code `135` before a newer durable trace
  snapshot was written, so the last durable lexical trace still remains the
  `2026-04-29T08:13:25Z` `lexical_walking` update on `ai_docs/jedi.md`.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Observed runtime state after the force-full command exited with code `135`:

- Files indexed in SQLite: `666`
- Code chunks indexed in SQLite: `7068`
- Summary-backed chunks: `0`
- Chunks missing summaries: `7068`
- Vector-linked chunks: `0`
- Chunks missing vectors: `7068`

Durable stage trace from `.mcp-index/force_full_exit_trace.json`:

- Trace status: `running`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Trace timestamp: `2026-04-29T08:13:25Z`
- Trace current commit: `6aae3502f966f878010f553d752dd1908b6a9ed6`
- Trace indexed commit before:
  `e2e9519858c3683c06b152c94a99e52098beaec6`
- Last progress path: `/home/viperjuice/code/Code-Index-MCP/ai_docs/jedi.md`

Runtime containment verdict for the live rerun:

- The generated fast-test report family, the bounded
  `ai_docs/pytest_overview.md` seam, and the exact bounded Python repair for
  `scripts/create_multi_repo_visual_report.py` are no longer the active
  lexical blocker.
- Prompt exit is still not restored in repo-local execution.
- The durable trace now names a narrower downstream blocker in `ai_docs/jedi.md`.
- The partial runtime still ends with no `chunk_summaries` and no
  `semantic_points`.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the SEMVISUALREPORT rerun reported:

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
  `using exact bounded Python indexing for scripts/create_multi_repo_visual_report.py`
- Force-full exit trace stage: `lexical_walking`
- Force-full exit trace stage family: `lexical`
- Force-full exit trace blocker source: `lexical_mutation`
- Force-full exit trace last progress path:
  `/home/viperjuice/code/Code-Index-MCP/ai_docs/jedi.md`

Repository/index freshness evidence:

- Current commit: `6aae3502`
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
- The remaining downstream work is no longer centered on
  `scripts/create_multi_repo_visual_report.py`. It is now centered on the
  lexical handling of `ai_docs/jedi.md`.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMVISUALREPORT.

Why:

- The fast-test report boundary, the bounded `ai_docs/*_overview.md`
  boundary, and the exact bounded Python repair for
  `scripts/create_multi_repo_visual_report.py` are explicit, narrow, and
  reflected in `repository status`.
- The durable trace proves the live rerun advanced beyond
  `scripts/create_multi_repo_visual_report.py`.
- The live force-full rerun still did not complete cleanly and the last
  durable lexical trace now points at `ai_docs/jedi.md`.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`.

Steering outcome:

- SEMVISUALREPORT acceptance is satisfied: the live repo-local force-full
  rerun no longer leaves the durable trace anchored on
  `scripts/create_multi_repo_visual_report.py`.
- The roadmap now adds `SEMJEDI` as the nearest downstream phase.
- Older downstream assumptions should be treated as stale. The next repair is
  not another retry of the visual-report seam; it is a bounded recovery for
  `ai_docs/jedi.md` or the next narrower blocker that file exposes.

## Verification

Verification sequence for this SEMVISUALREPORT slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_python_plugin.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- Targeted owned regression for the exact bounded Python rule, durable-trace
  handoff, repository-status wording, and dogfood evidence contract passes.
- The live force-full rebuild moved beyond
  `scripts/create_multi_repo_visual_report.py` and carried the latest durable
  lexical progress marker to `ai_docs/jedi.md`.
- Repository status now shows the explicit fast-test report boundary, the
  explicit `ai_docs/*_overview.md` boundary, and the exact bounded Python
  boundary for `scripts/create_multi_repo_visual_report.py` directly.
- The next work item is roadmap phase `SEMJEDI`, not another retry of the
  older visual-report assumption.
