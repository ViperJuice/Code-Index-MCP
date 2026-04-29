# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T07:28:19Z`.
- Observed commit: `feda36fc`.
- Phase plan: `plans/phase-plan-v7-SEMFASTREPORT.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMPYTESTOVERVIEW` after SEMFASTREPORT proved the generated fast-test
  report family is cleared but the live lexical blocker moved to
  `ai_docs/pytest_overview.md`.

## Reset Boundary

This SEMFASTREPORT rerun stayed inside the existing repo-local dogfood
boundary:

- `.mcp-index/current.db`, `.mcp-index/semantic_qdrant/`, and
  `.mcp-index/force_full_exit_trace.json` remained the only active runtime
  locations touched by the live rerun.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of the SQLite runtime, WAL files, or Qdrant directory
  was used before or after the rerun.

## SEMFASTREPORT Live Lexical Recovery

SEMFASTREPORT made the generated-report boundary explicit in code, config, and
tests:

- `.mcp-index-ignore` now ignores `fast_test_results/fast_report_*.md`.
- `mcp_server/core/ignore_patterns.py` remains the live walker/filter surface
  consumed by `build_walker_filter(...)`; SEMFASTREPORT kept the repair on
  that existing repo-local ignore contract instead of introducing a second
  filter path.
- `mcp_server/dispatcher/dispatcher_enhanced.py` still owns the lexical walk
  and consumed the repaired repo-local boundary without broader Markdown-path
  changes.
- `mcp_server/storage/git_index_manager.py` still owns the persisted
  force-full trace and proved the blocker moved past the fast-report family.
- `mcp_server/cli/repository_commands.py` now surfaces the explicit lexical
  boundary alongside the durable trace.
- `tests/test_ignore_patterns.py` freezes that the boundary is explicit and
  narrow enough to keep nearby Markdown such as
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` indexable.
- `tests/test_dispatcher.py` proves `index_directory(...)` skips the fast-test
  report family before lexical mutation begins.
- `tests/test_git_index_manager.py` proves the durable trace can move past the
  fast-report family while still failing closed on a new downstream lexical
  blocker.
- `mcp_server/cli/repository_commands.py` now prints
  `Lexical boundary: ignoring generated fast-test reports matching fast_test_results/fast_report_*.md`
  when the repo-local rule is present, and
  `tests/test_repository_commands.py` freezes that status wording.

The live rerun still did not close semantic dogfood readiness:

- A fresh `repository sync --force-full` was started with
  `MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5`.
- The durable trace advanced beyond
  `fast_test_results/fast_report_20250628_193425.md`.
- The most recent durable lexical progress marker became
  `/home/viperjuice/code/Code-Index-MCP/ai_docs/pytest_overview.md`.
- The command remained in flight until external termination at
  `2026-04-29T07:28:19Z`, and the last durable trace snapshot before that stop
  remained the lexical-walking update from `2026-04-29T07:27:49Z`.

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
- Trace timestamp: `2026-04-29T07:27:49Z`
- Trace current commit: `feda36fc6414cbf5ba686961475c5f56b7ca6377`
- Trace indexed commit before:
  `e2e9519858c3683c06b152c94a99e52098beaec6`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/ai_docs/pytest_overview.md`

Runtime containment verdict for the live rerun:

- The generated fast-test report family is no longer the active lexical
  blocker.
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
- Force-full exit trace stage: `lexical_walking`
- Force-full exit trace stage family: `lexical`
- Force-full exit trace blocker source: `lexical_mutation`
- Force-full exit trace last progress path:
  `/home/viperjuice/code/Code-Index-MCP/ai_docs/pytest_overview.md`

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
  `mcp_server/setup/semantic_preflight.py` and
  `mcp_server/cli/repository_commands.py`.
- The remaining downstream work is no longer centered on the generated
  `fast_test_results/fast_report_*.md` family. It is now centered on the
  lexical handling of `ai_docs/pytest_overview.md`.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMFASTREPORT.

Why:

- The fast-test report boundary is now explicit, narrow, and reflected in
  both the repo-local ignore file and `repository status`.
- The durable trace proves the live rerun advanced beyond
  `fast_test_results/fast_report_20250628_193425.md`.
- The live force-full rerun still did not complete cleanly and remained in
  lexical walking on `ai_docs/pytest_overview.md` when it was externally
  terminated.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`.

Steering outcome:

- SEMFASTREPORT acceptance is satisfied: the live repo-local force-full rerun
  no longer leaves the durable trace anchored on the fast-test report family.
- The roadmap now adds `SEMPYTESTOVERVIEW` as the nearest downstream phase.
- Older downstream assumptions should be treated as stale. The next repair is
  not another generic lexical retry; it is a bounded recovery for
  `ai_docs/pytest_overview.md` or the next narrower blocker that path exposes.

## Verification

Verification sequence for this SEMFASTREPORT slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_ignore_patterns.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- Targeted owned regression for the explicit fast-report boundary and
  repository-status wording passes.
- The live force-full rebuild moved beyond the generated fast-test report
  family and surfaced a new exact lexical blocker at
  `ai_docs/pytest_overview.md`.
- Repository status now shows both the explicit fast-report boundary and the
  new durable lexical progress marker directly.
- The next work item is roadmap phase `SEMPYTESTOVERVIEW`, not another retry
  of the older fast-report assumption.
