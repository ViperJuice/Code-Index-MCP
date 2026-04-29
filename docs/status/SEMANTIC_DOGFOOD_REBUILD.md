# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T09:10:41Z`.
- Observed commit: `cb748650`.
- Prior phase evidence anchor: `SEMTRACEFRESHNESS` at `2026-04-29T08:53:23Z`
  on observed commit `8870a23f`.
- Earlier lexical anchor: `SEMJEDI` at `2026-04-29T08:35:12Z` on observed
  commit `7335cf35`.
- Phase plan: `plans/phase-plan-v7-SEMDEVCONTAINER.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMPUBLISHRACE` after SEMDEVCONTAINER proved the live rerun advances beyond
  `.devcontainer/devcontainer.json`, but the durable trace now stops
  refreshing at `tests/test_artifact_publish_race.py`.

## Reset Boundary

This SEMDEVCONTAINER rerun stayed inside the existing repo-local dogfood
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

## SEMDEVCONTAINER Live Rerun Check

SEMDEVCONTAINER did not require a new `.devcontainer` code-path repair on the
current `HEAD`; the live rerun disproved the old blocker shape and exposed a
later exact lexical seam.

Observed progression on the same repo-local force-full command:

- At `2026-04-29T09:09:46Z`, the durable trace had already advanced to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_secret_redaction.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_repo_resolver.py`.
- At `2026-04-29T09:09:48Z`, the same rerun had already advanced again to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_benchmarks.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_artifact_publish_race.py`.
- The prior `.devcontainer` seam from SEMTRACEFRESHNESS
  (`last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`)
  did not recur on this rerun.
- By `2026-04-29T09:10:41Z`, the same running snapshot was still present on
  the test-file seam.

Current seam sizing confirms the steering change is about a later file family,
not the old small `.devcontainer` JSON:

- `.devcontainer/devcontainer.json`: `558` bytes
- `.devcontainer/post_create.sh`: `425` bytes
- `tests/test_benchmarks.py`: `30883` bytes
- `tests/test_artifact_publish_race.py`: `16280` bytes

## Rebuild Command

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Observed runtime state during the current SEMDEVCONTAINER rerun check:

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
- Trace timestamp: `2026-04-29T09:09:48Z`
- Trace blocker source: `lexical_mutation`
- Trace current commit: `cb748650e13658461183ded0afc5643a221f6d96`
- Trace indexed commit before:
  `e2e9519858c3683c06b152c94a99e52098beaec6`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/tests/test_benchmarks.py`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/tests/test_artifact_publish_race.py`

Runtime containment verdict for the live rerun:

- The force-full trace freshness repair is still real: the trace advanced
  through later lexical work and kept naming the current in-flight file during
  the rerun.
- The fast-test report boundary, the bounded `ai_docs/*_overview.md` seam, the
  exact `ai_docs/jedi.md` boundary, and the exact visual-report Python
  boundary all remained preserved.
- The `.devcontainer/devcontainer.json` seam is cleared on the current
  worktree.
- Prompt terminal closeout is still not restored for the next lexical seam.
- The next exact blocker is no longer `ai_docs/jedi.md`,
  `ai_docs/pytest_overview.md`, or `.devcontainer/devcontainer.json`; it is
  the stalled `tests/test_artifact_publish_race.py` seam.
- The partial runtime still ends with no `chunk_summaries` and no
  `semantic_points`.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the SEMDEVCONTAINER rerun check reported:

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
  `/home/viperjuice/code/Code-Index-MCP/tests/test_benchmarks.py`
- Force-full exit trace in-flight path:
  `/home/viperjuice/code/Code-Index-MCP/tests/test_artifact_publish_race.py`

Repository/index freshness evidence:

- Current commit: `cb748650`
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
- The remaining downstream work is no longer centered on `ai_docs/jedi.md`,
  the stale `ai_docs/pytest_overview.md` marker, or
  `.devcontainer/devcontainer.json`. It is now centered on the
  `tests/test_artifact_publish_race.py` lexical exit gap.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMDEVCONTAINER.

Why:

- The stale trace bug from SEMJEDI remains closed: the durable trace still
  refreshes beyond `ai_docs/pytest_overview.md` and names the current
  in-flight path during the live rerun.
- SEMDEVCONTAINER acceptance is satisfied on the current worktree because the
  live rerun no longer remained on `.devcontainer/devcontainer.json`; it
  advanced into later lexical work.
- The live force-full rerun still did not complete cleanly and remained in
  lexical walking on `tests/test_artifact_publish_race.py`.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`.

Steering outcome:

- SEMTRACEFRESHNESS acceptance remains satisfied for trace freshness: the
  rerun no longer hangs with the durable trace frozen on the older
  `ai_docs/pytest_overview.md` marker and `in_flight_path=null`.
- SEMDEVCONTAINER acceptance is now also satisfied: the refreshed live rerun
  advances beyond `.devcontainer/devcontainer.json`.
- The roadmap now adds `SEMPUBLISHRACE` as the nearest downstream phase.
- Older downstream assumptions should be treated as stale, including older
  downstream phase plans that still treat `.devcontainer/devcontainer.json` as
  the active blocker. The next repair is not another retry of the devcontainer
  seam; it is a bounded recovery for the
  `tests/test_artifact_publish_race.py` lexical exit blocker.

## Verification

Verification sequence for this SEMDEVCONTAINER slice:

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
- The live force-full rebuild still refreshes durable in-flight progress
  through later lexical files instead of remaining pinned to
  `ai_docs/pytest_overview.md`.
- The current live rerun advanced beyond `.devcontainer/devcontainer.json` and
  re-anchored on `tests/test_artifact_publish_race.py`.
- The live rerun still does not reach semantic work and can stop refreshing on
  `tests/test_artifact_publish_race.py` without reaching a bounded lexical
  exit on the active commit.
- The next work item is roadmap phase `SEMPUBLISHRACE`, not another retry of
  the devcontainer seam.
