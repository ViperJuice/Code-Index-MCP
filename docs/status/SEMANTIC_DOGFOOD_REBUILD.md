# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T07:06:18Z`.
- Observed commit: `a6492a44`.
- Phase plan: `plans/phase-plan-v7-SEMEXITTRACE.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMFASTREPORT` for the newly narrowed lexical blocker after SEMEXITTRACE
  landed its live trace persistence and operator-surface repair.

## Reset Boundary

This SEMEXITTRACE rerun stayed inside the existing repo-local dogfood boundary:

- `.mcp-index/current.db`, `.mcp-index/semantic_qdrant/`, and the new durable
  trace file `.mcp-index/force_full_exit_trace.json` remained the only active
  runtime locations touched by the live rerun.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of the SQLite runtime, WAL files, or Qdrant directory
  was used before the rerun.

## SEMEXITTRACE Live Exit Recovery

SEMEXITTRACE tightened the repo-local observability contract in code and tests:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now emits stable lexical,
  summary-shutdown, semantic-closeout, and final-closeout progress snapshots
  during `index_directory(...)` and `rebuild_semantic_for_paths(...)`.
- `mcp_server/storage/git_index_manager.py` now persists repo-scoped force-full
  trace updates to `.mcp-index/force_full_exit_trace.json` from force-full
  start through closeout, and `get_repository_status(...)` now carries that
  trace into operator-facing status output.
- `mcp_server/cli/repository_commands.py`, `tests/test_dispatcher.py`,
  `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`, and
  `tests/docs/test_semdogfood_evidence_contract.py` now freeze the durable
  trace contract and its repository-status rendering.

The live rerun still did not close semantic dogfood readiness:

- A fresh `repository sync --force-full` was started with
  `MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5`.
- The command stayed in flight for `2:10.04` before external termination by
  `timeout`.
- This time the command left a durable stage trace instead of forcing manual
  SQLite-only interpretation.
- The durable trace narrowed the blocker to lexical walking, with the most
  recent durable progress path at
  `/home/viperjuice/code/Code-Index-MCP/fast_test_results/fast_report_20250628_193425.md`.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Observed in-flight runtime state after external termination:

- Files indexed in SQLite: `666`
- Code chunks indexed in SQLite: `8934`
- Summary-backed chunks: `0`
- Chunks missing summaries: `8934`
- Vector-linked chunks: `0`
- Chunks missing vectors: `8934`

Durable stage trace from `.mcp-index/force_full_exit_trace.json`:

- Trace status: `running`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Trace timestamp: `2026-04-29T07:06:18Z`
- Trace current commit: `a6492a44fe4aa77bfa8ebb4e3fcb928da97995ab`
- Trace indexed commit before:
  `e2e9519858c3683c06b152c94a99e52098beaec6`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/fast_test_results/fast_report_20250628_193425.md`

Runtime containment verdict for the live rerun:

- Prompt exit: **not restored** in repo-local execution.
- Zero-summary containment before process exit: **not restored**.
- Runtime containment happened before process exit or only after external
  termination: **neither**; external termination still left the partial
  lexical runtime in place.

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
- Force-full exit trace stage: `lexical_walking`
- Force-full exit trace stage family: `lexical`
- Force-full exit trace blocker source: `lexical_mutation`

Repository/index freshness evidence:

- Current commit: `a6492a44`
- Indexed commit: `e2e95198`

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
- The remaining downstream work is no longer centered on summary-call exit
  uncertainty. It is now centered on the lexical handling of generated
  `fast_test_results/fast_report_*.md` artifacts plus the durable trace/status
  surfaces that proved that narrowing.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMEXITTRACE.

Why:

- The unit-level stage-trace, force-full trace persistence, and repository
  status rendering contracts now pass in owned tests.
- The live force-full rerun still does not finish inside the observed
  `2:10.04` window.
- The durable trace now proves the command was still in lexical walking rather
  than summary shutdown or semantic closeout when it was terminated.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`.

Steering outcome:

- SEMEXITTRACE implementation landed, and its acceptance goal was met: the
  blocker is now durably visible without guesswork.
- The roadmap now adds `SEMFASTREPORT` as the nearest downstream phase.
- Older downstream assumptions should be treated as stale. The next repair is
  not another generic exit-path rerun; it is a lexical file-family recovery or
  explicit ignore-boundary decision for `fast_test_results/fast_report_*.md`.

## Verification

Verification sequence for this SEMEXITTRACE slice:

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

- Targeted owned unit regression currently passes for the durable trace and
  repository-status rendering contracts.
- The live force-full rebuild stayed in flight for `2:10.04` and was
  externally terminated.
- Repository status now shows the durable trace directly instead of forcing
  manual SQLite-only diagnosis.
- The next work item is roadmap phase `SEMFASTREPORT`, not another blind retry
  of the older generic “exit-path uncertainty” assumption.
