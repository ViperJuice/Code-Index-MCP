# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T09:31:19Z`.
- Observed commit: `aec99482`.
- Prior phase evidence anchor: `SEMTRACEFRESHNESS` at `2026-04-29T08:53:23Z`
  on observed commit `8870a23f`.
- Earlier lexical anchor: `SEMJEDI` at `2026-04-29T08:35:12Z` on observed
  commit `7335cf35`.
- Phase plan: `plans/phase-plan-v7-SEMPUBLISHRACE.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMDEVREBOUND` after SEMPUBLISHRACE proved the live rerun advances beyond
  `tests/test_artifact_publish_race.py`, but the durable trace later stops
  refreshing again at `.devcontainer/devcontainer.json`.

## Reset Boundary

This SEMPUBLISHRACE rerun stayed inside the existing repo-local dogfood
boundary:

- `.mcp-index/current.db`, `.mcp-index/semantic_qdrant/`, and
  `force_full_exit_trace.json` remained the only active runtime locations
  touched by the live rerun.
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

The earlier rerun changed shape immediately:

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
- The rerun then moved to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`.
- The trace timestamp then stopped advancing at `2026-04-29T08:51:28Z`.
- The same frozen running snapshot was still present when observed again at
  `2026-04-29T08:52:53Z` and after the live process had been stopped by
  `2026-04-29T08:53:23Z`.

## SEMPUBLISHRACE Live Rerun Check

SEMPUBLISHRACE did repair the exact publish-race lexical seam on the current
`HEAD`, but the same live rerun later re-anchored on an older exact blocker
family and changed the next downstream work.

Observed progression on the same repo-local force-full command:

- At `2026-04-29T09:28:24Z`, the durable trace reset to
  `stage=force_full_started` on observed commit `aec99482`.
- At `2026-04-29T09:28:50Z`, the same rerun had already advanced to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_semantic_preflight.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_dispatcher.py`.
- At `2026-04-29T09:29:02Z`, the rerun had already advanced again to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/root_tests/test_contextual_pipeline.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/root_tests/test_c_plugin_simple.py`.
- At `2026-04-29T09:29:17Z`, the rerun had already advanced again to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/security/fixtures/mock_plugin/plugin.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/security/fixtures/mock_plugin/__init__.py`.
- At `2026-04-29T09:29:38Z`, the rerun had already advanced again to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/celery_overview.md`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/qdrant.md`.
- At `2026-04-29T09:29:40Z`, the durable trace re-anchored on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`.
- By `2026-04-29T09:30:32Z`, the same running snapshot was still present and
  `repository status` reported `Trace freshness: stale-running snapshot`.
- The rerun was then interrupted after evidence capture at
  `2026-04-29T09:31:19Z`.

Current seam sizing confirms the publish-race seam was cleared before the
rerun re-anchored on the older `.devcontainer` family:

- `.devcontainer/devcontainer.json`: `558` bytes
- `.devcontainer/post_create.sh`: `425` bytes
- `tests/test_benchmarks.py`: `30883` bytes
- `tests/test_artifact_publish_race.py`: `16280` bytes

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Observed runtime state during the current SEMPUBLISHRACE rerun check:

- Files indexed in SQLite: `666`
- Code chunks indexed in SQLite: `5418`
- Summary-backed chunks: `0`
- Chunks missing summaries: `5418`
- Vector-linked chunks: `0`
- Chunks missing vectors: `5418`

Durable stage trace from `.mcp-index/force_full_exit_trace.json` after the
current rerun stopped refreshing:

- Trace status: `running`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace timestamp: `2026-04-29T09:29:40Z`
- Trace blocker source: `lexical_mutation`
- Trace current commit: `aec99482aad0c420e74f3d57b75fb1649459f25c`
- Trace indexed commit before:
  `e2e9519858c3683c06b152c94a99e52098beaec6`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`

Runtime containment verdict for the live rerun:

- The force-full trace freshness repair is still real: the trace advanced
  through later lexical work and kept naming the current in-flight file during
  the rerun.
- The exact bounded Python seam for
  `tests/test_artifact_publish_race.py` is now preserved and no longer the
  active blocker.
- The fast-test report boundary, the bounded `ai_docs/*_overview.md` seam, the
  exact `ai_docs/jedi.md` boundary, and the exact visual-report Python
  boundary all remained preserved.
- Prompt terminal closeout is still not restored for the renewed exact
  `.devcontainer/devcontainer.json` lexical seam.
- The next exact blocker is no longer `ai_docs/jedi.md`,
  `ai_docs/pytest_overview.md`, or `tests/test_artifact_publish_race.py`; it
  has re-anchored on `.devcontainer/devcontainer.json`.
- The partial runtime still ends with no `chunk_summaries` and no
  `semantic_points`.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the SEMPUBLISHRACE rerun check reported:

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
- Lexical boundary:
  `using exact bounded Python indexing for tests/test_artifact_publish_race.py`
- Force-full exit trace stage: `lexical_walking`
- Force-full exit trace stage family: `lexical`
- Force-full exit trace freshness: `stale-running snapshot`
- Force-full exit trace blocker source: `lexical_mutation`
- Force-full exit trace last progress path:
  `/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
- Force-full exit trace in-flight path:
  `/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`

Repository/index freshness evidence:

- Current commit: `aec99482`
- Indexed commit: `e2e95198`

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Repo-local semantic dogfood is still blocked before semantic query routing
  because the repository query surface remains `index_unavailable`.
- Ready-path semantic metadata still remains the target once summaries and
  vectors exist: `semantic_source: "semantic"` and
  `semantic_collection_name: "code_index__oss_high__v1"`.
- `symbol` and lexical probes still point operators at
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/cli/repository_commands.py`, and the renewed exact lexical
  blocker seam.
- The remaining downstream work is no longer centered on `ai_docs/jedi.md`,
  the stale `ai_docs/pytest_overview.md` marker, or
  `tests/test_artifact_publish_race.py`. It is now centered on the renewed
  `.devcontainer/devcontainer.json` lexical re-anchor.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMPUBLISHRACE.

Why:

- The stale trace bug from SEMJEDI remains closed: the durable trace still
  refreshes beyond `ai_docs/pytest_overview.md` and names the current
  in-flight path during the live rerun.
- SEMPUBLISHRACE acceptance is satisfied on the current worktree because the
  live rerun no longer remained on `tests/test_artifact_publish_race.py`; it
  advanced into later lexical work.
- The live force-full rerun still did not complete cleanly and later
  re-anchored in lexical walking on `.devcontainer/devcontainer.json`.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`.

Steering outcome:

- SEMTRACEFRESHNESS acceptance remains satisfied for trace freshness: the
  rerun no longer hangs with the durable trace frozen on the older
  `ai_docs/pytest_overview.md` marker and `in_flight_path=null`.
- SEMPUBLISHRACE acceptance is now also satisfied: the refreshed live rerun
  advances beyond `tests/test_artifact_publish_race.py`.
- The roadmap now adds `SEMDEVREBOUND` as the nearest downstream phase.
- Older downstream assumptions should be treated as stale, including older
  downstream phase plans or handoffs that still treat
  `tests/test_artifact_publish_race.py` as the active blocker. The next repair
  is not another retry of the publish-race seam; it is a bounded recovery for
  the renewed `.devcontainer/devcontainer.json` lexical re-anchor.

## Verification

Verification sequence for this SEMPUBLISHRACE slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Observed outcomes:

- Targeted owned regression for the exact bounded Python path, the additive
  status boundary line, and evidence contract coverage passes.
- The live force-full rebuild still refreshes durable in-flight progress
  through later lexical files instead of remaining pinned to
  `tests/test_artifact_publish_race.py`.
- The current live rerun advanced beyond `tests/test_artifact_publish_race.py`
  and later re-anchored on `.devcontainer/devcontainer.json`.
- The live rerun still does not reach semantic work and can stop refreshing on
  `.devcontainer/devcontainer.json` without reaching a bounded lexical exit on
  the active commit.
- The next work item is roadmap phase `SEMDEVREBOUND`, not another retry of
  the publish-race seam.
