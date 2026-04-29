# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T12:21:08Z`.
- Observed commit: `ec443d85`.
- Prior SEMDISKIO live-rerun anchor: `2026-04-29T10:35:02Z` on observed
  commit `c8b2d724`.
- Prior SEMSCRIPTREBOUND evidence anchor: `2026-04-29T10:13:12Z` on observed
  commit `1e7a2a10`.
- Prior phase evidence anchor: `SEMPUBLISHRACE` at `2026-04-29T09:31:19Z`
  on observed commit `aec99482`.
- Prior trace-freshness anchor: `SEMTRACEFRESHNESS` at `2026-04-29T08:53:23Z`
  on observed commit `8870a23f`.
- Earlier lexical anchor: `SEMJEDI` at `2026-04-29T08:35:12Z` on observed
  commit `7335cf35`.
- Phase plan: `plans/phase-plan-v7-SEMDEVRELAPSE.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMDEVRELAPSE` after SEMROOTTESTABORT proved the later
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py` seam is now frozen in dispatcher,
  durable-trace, and operator-status coverage, but the refreshed live rerun on
  the new head never reached that pair and instead re-anchored earlier on
  `.devcontainer/devcontainer.json`. Older downstream assumptions should be
  treated as stale after this roadmap amendment.

## Reset Boundary

This SEMDISKIO execution stayed inside the existing repo-local dogfood
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

SEMPUBLISHRACE repaired the exact publish-race lexical seam on the prior
`HEAD`, but that earlier live rerun still re-anchored on the older
`.devcontainer` blocker family and changed the next downstream work.

Observed progression on the prior repo-local force-full command:

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

Current seam sizing from that earlier rebound confirmed the publish-race seam
was cleared before the rerun re-anchored on the older `.devcontainer` family:

- `.devcontainer/devcontainer.json`: `558` bytes
- `.devcontainer/post_create.sh`: `425` bytes
- `tests/test_benchmarks.py`: `30883` bytes
- `tests/test_artifact_publish_race.py`: `16280` bytes

## SEMDEVREBOUND Live Rerun Check

SEMDEVREBOUND repaired the exact `.devcontainer/devcontainer.json` lexical seam
on the prior evidence commit, but the same live rerun later re-anchored on a
later exact Python-script pair and changed the next downstream work again.

Observed progression on the earlier current repo-local force-full command:

- At `2026-04-29T09:50:53Z`, the durable trace had already advanced to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/check_index_schema.py`
  with `in_flight_path=null`.
- At `2026-04-29T09:50:55Z`, `repository status` reported the live rerun at
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/rerun_failed_native_tests.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/quick_mcp_vs_native_validation.py`.
- By `2026-04-29T09:52:03Z`, the durable trace had still not advanced beyond
  the same script pair, the earlier live process had already exited with a
  non-zero status, and `repository status` later reported `Trace freshness:
  stale-running snapshot`.

Current rebound sizing confirmed the `.devcontainer` seam was cleared before
the rerun re-anchored on the new script family:

- `scripts/check_index_schema.py`: later lexical progress observed after the
  `.devcontainer/devcontainer.json` boundary was added.
- `scripts/rerun_failed_native_tests.py`: latest durable `last_progress_path`.
- `scripts/quick_mcp_vs_native_validation.py`: current exact `in_flight_path`.
- `.devcontainer/devcontainer.json`: no longer the active blocker.

## SEMSCRIPTREBOUND Live Rerun Check

SEMSCRIPTREBOUND repaired the renewed exact
`scripts/quick_mcp_vs_native_validation.py` lexical seam on the current
`HEAD`, and the same live rerun advanced well past that script family before
failing later in semantic closeout.

Observed progression on the current repo-local force-full command:

- At `2026-04-29T10:09:17Z`, the durable trace still showed an early lexical
  snapshot on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
  with `in_flight_path=null` while the force-full command was still running.
- At `2026-04-29T10:12:58Z`, the same rerun had already advanced to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/mcp_server/plugin_system/loader.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/mcp_server/plugin_system/interfaces.py`.
- At `2026-04-29T10:13:00Z`, `repository status` reported the live rerun at
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/mcp_server/document_processing/__init__.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/mcp_server/document_processing/chunk_optimizer.py`.
- At `2026-04-29T10:13:12Z`, the force-full command exited with
  `disk I/O error`, and the durable trace recorded
  `Trace status: completed`, `Trace stage: force_full_failed`,
  `Trace stage family: final_closeout`, and
  `Trace blocker source: final_closeout`.

Current downstream verdict confirms the renewed script rebound seam is cleared:

- `scripts/rerun_failed_native_tests.py`: no longer the latest durable
  `last_progress_path`.
- `scripts/quick_mcp_vs_native_validation.py`: no longer the active
  `in_flight_path`.
- `.devcontainer/devcontainer.json`: no longer the active blocker.
- The next blocker is no longer lexical. It is the post-lexical semantic
  closeout failure `disk I/O error`.

## SEMDISKIO Live Rerun Check

SEMDISKIO repaired the code-path contract for storage-closeout classification,
runtime restoration, and operator status, but the refreshed live rerun on the
new head did not reach that intended semantic-closeout seam.

Code/test repair completed in this phase:

- `mcp_server/storage/sqlite_store.py` now records stable read-only
  provenance for `disk I/O error` and `database or disk is full`.
- `mcp_server/dispatcher/dispatcher_enhanced.py` now preserves
  `storage_closeout` semantics and storage diagnostics when the semantic
  closeout path raises a storage failure after lexical walking has completed.
- `mcp_server/storage/git_index_manager.py` now propagates the storage-closeout
  family through force-full traces and reuses the zero-summary/zero-vector
  runtime restore path for that failure family.
- `mcp_server/cli/repository_commands.py` now renders storage-closeout trace
  fields and runtime-restore context.
- `tests/test_disk_full.py`, `tests/test_dispatcher.py`,
  `tests/test_git_index_manager.py`, and `tests/test_repository_commands.py`
  freeze that repaired contract.

Observed progression on the refreshed live repo-local force-full command:

- The SEMDISKIO live rerun started on observed commit
  `c8b2d72469b9bdf7887f3f30ee411b8b529c040b`.
- By `2026-04-29T10:34:59Z`, `repository status` still showed active lexical
  progress with
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/fastapi_overview.md`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/plantuml_reference.md`.
- The durable trace then stopped advancing at `2026-04-29T10:35:02Z` with
  `Trace stage: lexical_walking`,
  `Trace stage family: lexical`,
  `Trace blocker source: lexical_mutation`, and
  `Last progress path: /home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`.
- At `2026-04-29T10:37:14Z`, the trace was still frozen on the same
  `.devcontainer/devcontainer.json` marker and `repository status` reported
  `Trace freshness: stale-running snapshot`.
- The hung sync was terminated after evidence capture so the stale-running
  lexical rebound could be treated as the next roadmap slice.

Steering outcome from that live rerun:

- The SEMDISKIO code/test contract landed, but the live rerun did not
  validate the intended storage-closeout seam on the current head.
- The roadmap now adds `SEMDEVSTALE` as the nearest downstream phase.
- Older downstream assumptions should be treated as stale, including any plan
  or handoff that still treats the active blocker as the semantic-closeout
  `disk I/O error` seam on the current head.

## SEMROOTTESTABORT Code And Live Rerun Check

SEMROOTTESTABORT tightened the later root-test contract at the exact bounded
path, durable trace, and operator-status surfaces, but the refreshed live
rerun on the new head re-anchored earlier and changed the next downstream
work again.

Code/test repair completed in this phase:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now treats
  `tests/root_tests/run_reranking_tests.py` as an exact bounded Python path.
- `mcp_server/cli/repository_commands.py` now prints the matching exact
  bounded lexical boundary line for
  `tests/root_tests/run_reranking_tests.py`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` now freeze the later
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py` trace and status contract without
  reopening earlier script, publish-race, or `.devcontainer` seams.

Observed progression on the refreshed live repo-local force-full command:

- The SEMROOTTESTABORT live rerun started on observed commit
  `a4120401381a0e179d0ee0e9355742817e8285d1` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`.
- By `2026-04-29T12:04:35Z`, the durable trace was still in
  `Trace stage: lexical_walking` with
  `Trace blocker source: lexical_mutation` and
  `Last progress path: /home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`.
- The bounded command timed out locally after 120 seconds, and
  `uv run mcp-index repository status` then terminalized the stale running
  snapshot to
  `Trace status: interrupted` at `2026-04-29T12:04:52Z` on the same
  `.devcontainer/devcontainer.json` marker.
- The rerun did not advance to
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py` on the new head.

Steering outcome from that refreshed rerun:

- The root-test seam is now covered and operator-visible when reached, but the
  active live blocker on observed commit `a4120401` is no longer the later
  root-test pair.
- The roadmap now adds `SEMDEVRELAPSE` as the nearest downstream phase.
- Older downstream assumptions should be treated as stale, including any plan
  or handoff that still treats the active blocker as the later root-test pair
  on the current head.

## SEMDEVRELAPSE Live Rerun Check

SEMDEVRELAPSE re-ran the renewed same-file devcontainer relapse on the current
head, refreshed the evidence contract, and amended the roadmap because the
next unexplained work is no longer devcontainer-file-local.

Observed progression on the refreshed live repo-local force-full command:

- The SEMDEVRELAPSE live rerun started on observed commit
  `ec443d85edd902cdcc018d2103a334abe5235124` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`.
- The bounded command produced a durable running trace at
  `2026-04-29T12:19:54Z` with
  `Trace stage: lexical_walking`,
  `Trace blocker source: lexical_mutation`, and
  `Last progress path: /home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
  while `in_flight_path` was already `null`.
- The bounded command timed out locally after 120 seconds, and
  `uv run mcp-index repository status` then terminalized the stale running
  snapshot to `Trace status: interrupted` at `2026-04-29T12:21:08Z` on the
  same `.devcontainer/devcontainer.json` marker.
- A walk-order probe on the same head showed
  `.devcontainer/devcontainer.json` immediately followed by
  `fast_test_results/fast_report_20250628_193425.md` and then
  `test_workspace/real_repos/search_scaling/package.json`, so the renewed
  relapse is no longer explained by the older
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` handoff
  alone.
- The refreshed rerun still did not advance to the later
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py` pair on the current head.

Steering outcome from that refreshed rerun:

- The same-file devcontainer relapse remains the truthful live blocker for
  SEMDEVRELAPSE; acceptance for this phase is still blocked.
- The renewed evidence no longer supports treating the next repair as strictly
  file-local to `.devcontainer/devcontainer.json`.
- The roadmap now adds downstream phase `SEMWALKGAP`.
- Older downstream assumptions should be treated as stale, including any plan
  or handoff that assumes the next work still belongs to the later root-test
  seam or to the older `.devcontainer/post_create.sh` rebound.

## SEMDEVSTALE Live Rerun Check

SEMDEVSTALE repaired the post-lexical handoff contract around the renewed
`.devcontainer/devcontainer.json` seam, and the refreshed live rerun advanced
past that boundary before exposing a later stale-running lexical blocker.

Code/test repair completed in this phase:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now emits a durable
  `force_full_closeout_handoff` snapshot as soon as lexical walking completes,
  before semantic setup begins.
- `mcp_server/storage/git_index_manager.py` now preserves the latest completed
  lexical `last_progress_path` across later semantic-stage progress snapshots
  that do not carry a new lexical path.
- `tests/test_dispatcher.py` freezes the renewed devcontainer rebound by
  requiring a durable post-lexical handoff snapshot even when semantic
  closeout stalls before emitting its own progress.
- `tests/test_git_index_manager.py` freezes preservation of the later lexical
  `last_progress_path` across semantic handoff snapshots.

Observed progression on the refreshed live repo-local force-full command:

- The SEMDEVSTALE live rerun started on observed commit
  `7e547c77da72da4def8fce65fb8962a36f759c3c`.
- At `2026-04-29T10:55:11Z`, the durable trace had already advanced beyond
  `.devcontainer/devcontainer.json` to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_security.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_bootstrap.py`.
- At `2026-04-29T10:55:12Z`, `repository status` and the durable trace had
  advanced again to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_deployment_runbook_shape.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_reindex_resume.py`.
- The `uv run mcp-index repository sync --force-full` process then exited with
  code `135` before any later durable terminal trace was written.
- When observed again after the process had already exited, `repository
  status` reported `Trace freshness: stale-running snapshot` on the same
  later test-file pair.

Current downstream verdict confirms the renewed devcontainer seam is cleared:

- `.devcontainer/devcontainer.json`: no longer the latest durable
  `last_progress_path`.
- `.devcontainer/devcontainer.json`: no longer the active `in_flight_path`.
- `tests/test_deployment_runbook_shape.py`: latest durable `last_progress_path`.
- `tests/test_reindex_resume.py`: current exact `in_flight_path`.
- The next blocker is no longer the renewed devcontainer seam. It is the
  later lexical/crash rebound that leaves a stale-running trace after the
  process has already exited.

## SEMTESTSTALE Live Rerun Check

SEMTESTSTALE repaired the later force-full trace truthfulness contract after
abnormal exit, and the refreshed live reruns advanced beyond the later test
pair before exposing a still-later script-family blocker.

Code/test repair completed in this phase:

- `mcp_server/storage/git_index_manager.py` now terminalizes an already-started
  force-full trace as `interrupted` when `_full_index(...)` raises after
  lexical progress has already been persisted.
- `mcp_server/storage/git_index_manager.py` now persists `process_id` in
  force-full progress snapshots and rewrites a dead-process `status=running`
  trace to `status=interrupted` during `repository status`.
- `tests/test_dispatcher.py` freezes the later
  `tests/test_deployment_runbook_shape.py ->
  tests/test_reindex_resume.py` lexical pair and the post-lexical handoff that
  follows it.
- `tests/test_git_index_manager.py` freezes both the later test-pair snapshot
  and the dead-process terminalization path.
- `tests/test_repository_commands.py` freezes the operator surface so the
  later interrupted test-pair trace no longer prints
  `Trace freshness: stale-running snapshot`.

Observed progression on the refreshed live repo-local force-full commands:

- The first SEMTESTSTALE rerun started on observed commit
  `a186b352144a8211552afa432f42d90d2c79546d`.
- At `2026-04-29T11:13:51Z`, the durable trace had already advanced beyond the
  later test pair to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_p8_customer_docs_alignment.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_p7_markdown_alignment.py`.
- The same rerun later advanced again to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_p8_historical_sweep.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_p26_public_alpha_decision.py`
  before the process exited with code `135`.
- After the liveness repair landed, the next rerun advanced again to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/run_test_batch.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/validate_mcp_comprehensive.py`
  at `2026-04-29T11:17:34Z`.
- When observed again through `repository status` at `2026-04-29T11:17:51Z`
  after that live process had already exited with code `135`, the durable
  trace had been rewritten from `running` to `interrupted` while preserving
  the same later script pair.

Current downstream verdict confirms the later stale-running test seam is
cleared:

- `tests/test_deployment_runbook_shape.py`: no longer the latest durable
  `last_progress_path`.
- `tests/test_reindex_resume.py`: no longer the active `in_flight_path`.
- `scripts/run_test_batch.py`: latest durable `last_progress_path`.
- `scripts/validate_mcp_comprehensive.py`: current exact `in_flight_path`.
- The next blocker is no longer the later test-pair stale trace. It is the
  later script-family abort that still exits with code `135`.

## SEMSCRIPTABORT Live Rerun Check

SEMSCRIPTABORT repaired the later
`scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py` lexical
seam on the current `HEAD`, and the refreshed live rerun advanced beyond that
pair before failing later in `tests/root_tests`.

Code/test repair completed in this phase:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now bypasses chunking for
  the exact path `scripts/validate_mcp_comprehensive.py` while still
  persisting symbols and lexical content.
- `mcp_server/cli/repository_commands.py` now reports the exact bounded Python
  boundary for `scripts/validate_mcp_comprehensive.py`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` freeze the later script-pair progress
  and post-repair boundary contract.

Observed progression on the refreshed live repo-local force-full command:

- The SEMSCRIPTABORT live rerun started on observed commit
  `098c1ad19c3957af05bf1bfaf4ee6ceb07b73cce`.
- At `2026-04-29T11:43:04Z`, the durable trace had already advanced to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/real_world/conftest.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/real_world/test_redis_caching.py`.
- At `2026-04-29T11:43:05Z`, `repository status` reported the same live rerun at
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/root_tests/test_voyage_api.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/root_tests/run_reranking_tests.py`.
- The force-full command still exited with code `135`.
- When observed again through `repository status` at `2026-04-29T11:43:19Z`
  after that live process had already exited, the durable trace had been
  rewritten from `running` to `interrupted` while preserving the same later
  root-test pair.

Current downstream verdict confirms the later script seam is cleared:

- `scripts/run_test_batch.py`: no longer the latest durable
  `last_progress_path`.
- `scripts/validate_mcp_comprehensive.py`: no longer the active
  `in_flight_path`.
- `tests/root_tests/test_voyage_api.py`: latest durable `last_progress_path`.
- `tests/root_tests/run_reranking_tests.py`: current exact `in_flight_path`.
- The next blocker is no longer the later script-family abort. It is the
  later root-test abort that still exits with code `135`.

## Rebuild Command

```bash
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

Observed runtime state during the current SEMDEVRELAPSE rerun check:

- Files indexed in SQLite: `665`
- Code chunks indexed in SQLite: `5418`
- Summary-backed chunks: `0`
- Chunks missing summaries: `5418`
- Vector-linked chunks: `0`
- Chunks missing vectors: `5418`

Durable stage trace from `.mcp-index/force_full_exit_trace.json` after the
post-timeout SEMDEVRELAPSE rerun evidence capture:

- Trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace timestamp: `2026-04-29T12:21:08Z`
- Trace blocker source: `lexical_mutation`
- Trace current commit: `ec443d85edd902cdcc018d2103a334abe5235124`
- Trace indexed commit before:
  `e2e9519858c3683c06b152c94a99e52098beaec6`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`

Runtime containment verdict for the refreshed live rerun:

- The repaired later script and root-test contracts remain frozen in unit
  coverage, but this refreshed live rerun never reached them again.
- The current exact blocker is still the renewed same-file marker
  `.devcontainer/devcontainer.json` under `Trace stage: lexical_walking`.
- The live rerun timed out under the 120-second watchdog, and
  `repository status` rewrote the dead-process durable trace from
  `status=running` to `status=interrupted` on the same same-file marker.
- Walk-order evidence shows the next unexplained tail after that marker now
  includes `fast_test_results/fast_report_20250628_193425.md` and
  `test_workspace/real_repos/search_scaling/package.json`, so the next repair
  is no longer obviously the older `.devcontainer` predecessor/handoff pair.
- The partial runtime still ends with no `chunk_summaries` and no
  `semantic_points`.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the SEMDEVRELAPSE live rerun had already timed out
reported:

- Lexical readiness: `stale_commit`
- Semantic readiness: `summaries_missing`
- Active-profile preflight: `ready`
- Can write semantic vectors: `yes`
- Active profile: `oss_high`
- Active collection: `code_index__oss_high__v1`
- Collection bootstrap state: `reused`
- Query surface: `index_unavailable`
- Rollout status: `partial_index_failure`
- Last sync error: `disk I/O error`
- Lexical boundary:
  `ignoring generated fast-test reports matching fast_test_results/fast_report_*.md`
- Lexical boundary:
  `using bounded Markdown indexing for ai_docs/*_overview.md`
- Lexical boundary:
  `using exact bounded Markdown indexing for ai_docs/jedi.md`
- Lexical boundary:
  `using exact bounded Python indexing for scripts/create_multi_repo_visual_report.py`
- Lexical boundary:
  `using exact bounded Python indexing for scripts/quick_mcp_vs_native_validation.py`
- Lexical boundary:
  `using exact bounded Python indexing for scripts/validate_mcp_comprehensive.py`
- Lexical boundary:
  `using exact bounded Python indexing for tests/test_artifact_publish_race.py`
- Lexical boundary:
  `using exact bounded JSON indexing for .devcontainer/devcontainer.json`
- Trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`

Repository/index freshness evidence:

- Current commit: `ec443d85`
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
  `mcp_server/cli/repository_commands.py`, and the renewed
  `.devcontainer/devcontainer.json` lexical blocker.
- The remaining downstream work is no longer centered on the later root-test
  abort captured by `SEMROOTTESTABORT`. It is now centered on the renewed
  same-file devcontainer relapse plus the newly observed post-devcontainer
  walk gap captured by `SEMWALKGAP`.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMDEVRELAPSE.

Why:

- The SEMDEVRELAPSE evidence refresh is real: the renewed same-file
  `.devcontainer/devcontainer.json` relapse is now frozen in the phase-local
  tests and live status artifact.
- The stale trace bug from SEMJEDI remains closed as a unit/status contract:
  the operator surface now distinguishes missing traces, stale-running traces,
  and storage-closeout traces.
- The refreshed live rerun on commit `ec443d85` still times out with the
  durable trace re-anchored on `.devcontainer/devcontainer.json` while
  `repository status` truthfully terminalizes that stale running trace to
  `interrupted`.
- The live rerun still does not reach the later
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py` pair on the current head.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`.

Steering outcome:

- SEMTRACEFRESHNESS acceptance remains satisfied for the operator surface: the
  stale-running condition is now reported truthfully instead of silently
  disappearing behind a missing trace.
- SEMSCRIPTREBOUND remains historically valid on the prior head: the earlier
  rerun did clear `scripts/quick_mcp_vs_native_validation.py` and expose the
  later disk-I/O closeout seam.
- SEMDEVSTALE and SEMTESTSTALE remain historically valid on earlier heads, but
  the refreshed current-head rerun in SEMDEVRELAPSE reintroduced the same-file
  `.devcontainer/devcontainer.json` marker before those later seams were
  reached again.
- SEMSCRIPTABORT and SEMROOTTESTABORT remain historically valid repairs for
  later seams that were not reached by the refreshed current-head rerun.
- The roadmap now adds downstream phase `SEMWALKGAP`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as either the later root-test seam or the older
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` rebound.

## Verification

Verification sequence for this SEMDEVRELAPSE slice:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "devcontainer or lexical or force_full or interrupted or stale or trace or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```
