# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T08:53:23Z`.
- Observed commit: `8870a23f`.
- Prior phase evidence anchor: `SEMJEDI` at `2026-04-29T08:35:12Z` on
  observed commit `7335cf35`.
- Phase plan: `plans/phase-plan-v7-SEMTRACEFRESHNESS.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMDEVCONTAINER` after SEMTRACEFRESHNESS proved the durable trace now
  refreshes beyond `ai_docs/pytest_overview.md`, but the live rerun still
  stops progressing at `.devcontainer/devcontainer.json`.

## Reset Boundary

This SEMTRACEFRESHNESS rerun stayed inside the existing repo-local dogfood
boundary:

- `.mcp-index/current.db`, `.mcp-index/semantic_qdrant/`, and
  `.mcp-index/force_full_exit_trace.json` remained the only active runtime
  locations touched by the live rerun.
- The active semantic collection remained `code_index__oss_high__v1`.
- No destructive reset of the SQLite runtime, WAL files, or Qdrant directory
  was used before or after the rerun.

## SEMTRACEFRESHNESS Live Trace Recovery

SEMTRACEFRESHNESS repaired the stale lexical handoff at the mutation source and
operator surface:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now emits a lexical progress
  snapshot as soon as a file becomes in flight instead of waiting only for the
  file to return.
- `mcp_server/storage/git_index_manager.py` already persisted dispatcher
  snapshots into `force_full_exit_trace.json`; the refreshed live rerun now
  records current `in_flight_path` values durably.
- `mcp_server/cli/repository_commands.py` now distinguishes a missing durable
  trace from a stale running trace and prints `Trace freshness:
  stale-running snapshot` when the last running snapshot ages past the
  configured lexical-timeout window.
- `tests/test_dispatcher.py` freezes the stale-trace regression shape by
  requiring a prior `last_progress_path` plus a new `in_flight_path` snapshot
  before the second lexical file returns.
- `tests/test_git_index_manager.py` freezes durable persistence of the fresh
  in-flight snapshot.
- `tests/test_repository_commands.py` freezes both the missing-trace and
  stale-running trace wording.

The live rerun changed shape immediately:

- At `2026-04-29T08:50:29Z`, the durable trace refreshed to
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/ARCHITECTURE.md`
  with `last_progress_path=null`.
- At `2026-04-29T08:50:44Z`, the same rerun had already advanced to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_utils.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_index_discovery.py`.
- The original stale shape from SEMJEDI
  (`last_progress_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/pytest_overview.md`
  with `in_flight_path=null`) did not recur.

The rerun still did not reach semantic work:

- The durable trace eventually moved to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`.
- The trace timestamp then stopped advancing at `2026-04-29T08:51:28Z`.
- The same frozen running snapshot was still present when observed again at
  `2026-04-29T08:52:53Z` and after the live process had been stopped by
  `2026-04-29T08:53:23Z`.

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Observed runtime state during the refreshed force-full rerun:

- Files indexed in SQLite: `666`
- Code chunks indexed in SQLite: `5418`
- Summary-backed chunks: `0`
- Chunks missing summaries: `5418`
- Vector-linked chunks: `0`
- Chunks missing vectors: `5418`

Durable stage trace from `.mcp-index/force_full_exit_trace.json` after the
rerun stopped progressing:

- Trace status: `running`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace timestamp: `2026-04-29T08:51:28Z`
- Trace blocker source: `lexical_mutation`
- Trace current commit: `8870a23f6460727afb0a43e9f971bc0d77e16ba4`
- Trace indexed commit before:
  `e2e9519858c3683c06b152c94a99e52098beaec6`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`

Runtime containment verdict for the live rerun:

- The force-full trace freshness repair is real: the trace advanced through
  later lexical work and kept naming the current in-flight file during the
  rerun.
- The fast-test report boundary, the bounded `ai_docs/*_overview.md` seam, the
  exact `ai_docs/jedi.md` boundary, and the exact visual-report Python
  boundary all remained preserved.
- Prompt terminal closeout is still not restored for the next lexical seam.
- The next exact blocker is no longer `ai_docs/jedi.md` or
  `ai_docs/pytest_overview.md`; it is the stalled `.devcontainer` JSON seam.
- The partial runtime still ends with no `chunk_summaries` and no
  `semantic_points`.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the live rerun had been stopped reported:

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
- Force-full exit trace freshness: `stale-running snapshot`
- Force-full exit trace blocker source: `lexical_mutation`
- Force-full exit trace last progress path:
  `/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
- Force-full exit trace in-flight path:
  `/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`

Repository/index freshness evidence:

- Current commit: `8870a23f`
- Indexed commit: `e2e95198`

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Repo-local semantic dogfood is still blocked before semantic query routing
  because the repository query surface remains `index_unavailable`.
- Ready-path semantic metadata still remains the target once summaries and
  vectors exist: `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"`.
- `symbol` and lexical probes still point operators at
  `mcp_server/setup/semantic_preflight.py`, `mcp_server/cli/repository_commands.py`,
  and the active lexical blocker seam.
- The remaining downstream work is no longer centered on `ai_docs/jedi.md` or
  the stale `ai_docs/pytest_overview.md` marker. It is now centered on the
  `.devcontainer/devcontainer.json` lexical exit gap.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMTRACEFRESHNESS.

Why:

- The stale trace bug from SEMJEDI is closed: the durable trace now refreshes
  beyond `ai_docs/pytest_overview.md` and names the current in-flight path
  during the live rerun.
- Repository status now distinguishes a missing trace from a stale running
  trace and no longer implies live progress when the running snapshot has aged
  out.
- The live force-full rerun still did not complete cleanly and remained in
  lexical walking on `.devcontainer/devcontainer.json`.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`.

Steering outcome:

- SEMTRACEFRESHNESS acceptance is satisfied for trace freshness: the rerun no
  longer hangs with the durable trace frozen on the older
  `ai_docs/pytest_overview.md` marker and `in_flight_path=null`.
- The roadmap now adds `SEMDEVCONTAINER` as the nearest downstream phase.
- Older downstream assumptions should be treated as stale. The next repair is
  not another retry of the Jedi seam or the earlier stale-trace gap; it is a
  bounded recovery for the `.devcontainer/devcontainer.json` lexical exit
  blocker.

## Verification

Verification sequence for this SEMTRACEFRESHNESS slice:

```bash
uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- Targeted owned regression for dispatcher progress emission, durable trace
  persistence, missing/stale status wording, and evidence contract coverage
  passes.
- The live force-full rebuild now refreshes durable in-flight progress through
  later lexical files instead of remaining pinned to
  `ai_docs/pytest_overview.md`.
- The live rerun still does not reach semantic work and can stop refreshing on
  `.devcontainer/devcontainer.json` without reaching a bounded lexical exit on
  the active commit.
- The next work item is roadmap phase `SEMDEVCONTAINER`, not another retry of
  the earlier Markdown seams.
