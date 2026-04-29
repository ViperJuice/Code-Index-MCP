# Semantic Dogfood Rebuild

- Evidence captured: `2026-04-29T19:13:19Z`.
- Observed commit: `2167f18`.
- Prior SEMCODEXLOOPTAIL live-rerun anchor: `2026-04-29T18:52:55Z` on observed
  commit `3d627c33`.
- Prior SEMMOCKPLUGIN live-rerun anchor: `2026-04-29T18:26:11Z` on observed
  commit `6a909203`.
- Prior SEMDOCTESTTAIL live-rerun anchor: `2026-04-29T17:45:52Z` on observed
  commit `5c0102d`.
- Prior SEMMIXEDPHASETAIL live-rerun anchor: `2026-04-29T16:49:50Z` on
  observed commit `468dee18`.
- Prior SEMLEGACYPLANS live-rerun anchor: `2026-04-29T16:07:22Z` on observed
  commit `fe501b97`.
- Prior SEMCROSSPLANS live-rerun anchor: `2026-04-29T15:51:12Z` on observed
  commit `d0b21255`.
- Prior SEMPHASEPLANS live-rerun anchor: `2026-04-29T15:37:57Z` on observed
  commit `40968140`.
- Prior SEMCLAUDECMDS live-rerun anchor: `2026-04-29T15:03:10Z` on observed
  commit `68ae9492`.
- Prior SEMDOCGOV live-rerun anchor: `2026-04-29T14:41:32Z` on observed
  commit `cd2c183`.
- Prior SEMVALIDEVIDENCE live-rerun anchor: `2026-04-29T13:34:20Z` on
  observed commit `705a506f`.
- Prior SEMQUICKCHARTS live-rerun anchor: `2026-04-29T12:53:24Z` on observed
  commit `26a163da`.
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
- Phase plan: `plans/phase-plan-v7-SEMDOCCONTRACTTAIL.md`.
- Prior phase plan: `plans/phase-plan-v7-SEMCODEXLOOPTAIL.md`.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMGARELTAIL` after SEMDOCCONTRACTTAIL proved the later docs-contract seam
  is now cleared, but the refreshed live rerun on the new head still
  terminalized later in lexical walking on
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py`. Older downstream assumptions
  should be treated as stale after this roadmap amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMCODEXLOOPTAIL` after SEMMOCKPLUGIN proved the later security-fixture
  seam is now cleared, but the refreshed live rerun on the new head still
  terminalized later in lexical walking on
  `.codex/phase-loop/runs/20260427T085911Z-02-mrready-execute/launch.json ->
  .codex/phase-loop/runs/20260427T085911Z-02-mrready-execute/heartbeat.json`.
- Prior roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMDOCTESTTAIL` after SEMEMBEDCONSOL proved the later Python-script seam
  is now cleared, but the refreshed live rerun on the new head still
  terminalized later in lexical walking on
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py`. Older downstream assumptions
  should be treated as stale after this roadmap amendment.
- Roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMEMBEDCONSOL` after SEMVERIFYSIMTAIL proved the later Python-script
  seam is now cleared, but the refreshed live rerun on the new head still
  terminalized later in lexical walking on
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py`. Older downstream assumptions
  should be treated as stale after this roadmap amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMVERIFYSIMTAIL` after SEMPREUPGRADETAIL proved the mixed shell/Python
  script seam is now cleared, but the refreshed live rerun on the new head
  still terminalized later in lexical walking on
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py`. Older downstream assumptions
  should be treated as stale after this roadmap amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMPREUPGRADETAIL` after SEMMIXEDPHASETAIL proved the mixed-version
  phase-plan seam is now cleared and a post-edit rerun advanced beyond the
  transient `ai_docs` waypoint, but the refreshed live rerun on the same
  head still terminalized later in lexical walking on
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py`. Older downstream assumptions should
  be treated as stale after this roadmap amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMMIXEDPHASETAIL` after SEMLEGACYPLANS proved the historical phase-plan
  seam is now cleared, but the refreshed live rerun on the new head still
  terminalized later in lexical walking on
  `plans/phase-plan-v7-SEMPHASETAIL.md ->
  plans/phase-plan-v5-gagov.md`. Older downstream assumptions should be
  treated as stale after this roadmap amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMLEGACYPLANS` after SEMPHASETAIL proved the later v7-only phase-plan
  seam is now cleared, but the refreshed live rerun on the new head still
  terminalized later in lexical walking on
  `plans/phase-plan-v6-WATCH.md ->
  plans/phase-plan-v1-p19.md`. Older downstream assumptions should be
  treated as stale after this roadmap amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMPHASETAIL` after SEMCROSSPLANS proved the cross-version phase-plan seam
  is now cleared, but the refreshed live rerun on the new head still
  terminalized later in lexical walking on
  `plans/phase-plan-v7-SEMSYNCFIX.md ->
  plans/phase-plan-v7-SEMVISUALREPORT.md`. Older downstream assumptions
  should be treated as stale after this roadmap amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMPHASEPLANS` after SEMSCRIPTLANGS proved the script language-audit seam
  is now cleared, but the refreshed live rerun on the new head still
  terminalized later in lexical walking on
  `plans/phase-plan-v7-SEMPREFLIGHT.md ->
  plans/phase-plan-v7-SEMDOCGOV.md`. Older downstream assumptions should be
  treated as stale after this roadmap amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` now adds downstream phase
  `SEMSCRIPTLANGS` after SEMCLAUDECMDS proved the `.claude/commands` seam is
  now cleared, but the refreshed live rerun on the new head still
  terminalized later in lexical walking on
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py`. Older downstream assumptions should be
  treated as stale after this roadmap amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` added downstream phase
  `SEMDOCGOV` after SEMARCHIVEWALKGAP proved the archive-tail seam is now
  cleared, but the refreshed live rerun on the new head still terminalized
  later in lexical walking on
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py`. Older downstream assumptions
  should be treated as stale after this roadmap amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` added downstream phase
  `SEMARCHIVEWALKGAP` after SEMBENCHDOCS proved the later
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
  docs/benchmarks/production_benchmark.md` seam is now cleared, but the
  refreshed live rerun on the new head still terminalized later in lexical
  walking at
  `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
  before the 120-second watchdog could expose a durable later successor path.
  Older downstream assumptions should be treated as stale after this roadmap
  amendment.
- Prior roadmap steering: `specs/phase-plans-v7.md` added downstream phase
  `SEMBENCHDOCS` after SEMVALIDEVIDENCE proved the later
  `docs/validation/ga-closeout-decision.md ->
  docs/validation/mre2e-evidence.md` seam is now frozen in dispatcher,
  durable-trace, and operator-status coverage, but the refreshed live rerun on
  the new head re-anchored later on
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
  docs/benchmarks/production_benchmark.md`. Older downstream assumptions
  should be treated as stale after this roadmap amendment.

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

## SEMWALKGAP Live Rerun Check

SEMWALKGAP repaired the post-devcontainer walk-gap contract on the current
head, and the refreshed live rerun advanced durably beyond the ignored
fast-report and `test_workspace/` tail before the 120-second watchdog
expired.

Code/test repair completed in this phase:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now prunes recursive walk
  subtrees through `build_walker_filter(...)`, so repo-local ignored fixture
  directories such as `test_workspace/` are skipped before lexical walking
  enters them.
- `mcp_server/cli/repository_commands.py` now reports the explicit
  `test_workspace/` lexical boundary alongside the existing fast-report and
  exact-path boundary lines.
- `tests/test_dispatcher.py` freezes the combined post-devcontainer tail by
  requiring the ignored `test_workspace/` subtree to be pruned before the
  walker can reach the next later included file.
- `tests/test_git_index_manager.py` freezes durable trace preservation of the
  later included path after ignored tail handling.
- `tests/test_ignore_patterns.py` freezes both the explicit repo-local
  `test_workspace/` boundary and absolute-path walker filtering for
  `fast_test_results/fast_report_*.md` plus
  `test_workspace/real_repos/search_scaling/package.json`.
- `tests/test_repository_commands.py` freezes the operator surface so the
  `test_workspace/` lexical boundary is visible while the later included path,
  not `.devcontainer/devcontainer.json`, remains authoritative.

Observed progression on the refreshed live repo-local force-full command:

- The SEMWALKGAP live rerun started on observed commit
  `26a163da52865a85c4f0c91e657c3f959e26b00e` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`.
- By `2026-04-29T12:51:58Z`, the durable trace had already advanced far past
  `.devcontainer/devcontainer.json` to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/post_migration/test_mcp_functionality.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_semcontract_contract.py`.
- By `2026-04-29T12:52:00Z`, `repository status` reported the same live rerun
  at
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_p7_schema_alignment.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_sempipe_contract.py`.
- By `2026-04-29T12:53:14Z`, the durable trace had advanced again to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/mcp_server/visualization/__init__.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/mcp_server/visualization/quick_charts.py`.
- The bounded command then timed out locally after 120 seconds, and
  `repository status` terminalized the dead-process snapshot to
  `Trace status: interrupted` at `2026-04-29T12:53:24Z` while preserving the
  same later visualization pair.

Current downstream verdict confirms the post-devcontainer walk gap is cleared:

- `.devcontainer/devcontainer.json`: no longer the latest durable
  `last_progress_path`.
- `.devcontainer/devcontainer.json`: no longer the active `in_flight_path`.
- `fast_test_results/fast_report_*.md`: still a bounded ignored lexical
  family, not the authoritative blocker.
- `test_workspace/real_repos/search_scaling/package.json`: still a bounded
  ignored fixture path, not the authoritative blocker.
- `mcp_server/visualization/__init__.py`: latest durable `last_progress_path`.
- `mcp_server/visualization/quick_charts.py`: current exact `in_flight_path`.
- The next blocker is no longer the post-devcontainer ignore tail. It is the
  later visualization lexical seam.

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

Observed runtime state during the current SEMARCHIVEWALKGAP rerun check:

- Files indexed in SQLite: `1116`
- Code chunks indexed in SQLite: `28182`
- Summary-backed chunks: `0`
- Chunks missing summaries: `28182`
- Vector-linked chunks: `0`
- Chunks missing vectors: `28182`

Durable stage trace from `.mcp-index/force_full_exit_trace.json` after the
post-timeout SEMARCHIVEWALKGAP rerun evidence capture:

- Trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace timestamp: `2026-04-29T14:12:49Z`
- Trace blocker source: `lexical_mutation`
- Trace current commit: `9138e0b0c78841324bcc9dc6863aede8e435f51d`
- Trace indexed commit before:
  `e2e9519858c3683c06b152c94a99e52098beaec6`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/tests/docs/test_mre2e_evidence_contract.py`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/tests/docs/test_gagov_governance_contract.py`

Runtime containment verdict for the refreshed live rerun:

- The repaired archive-tail contract is now validated live: the durable trace
  advanced beyond
  `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
  and the exact bounded archive JSON successor
  `analysis_archive/semantic_vs_sql_comparison_1750926162.json`.
- The live rerun still exited under the 120-second watchdog, and
  `repository status` rewrote the dead-process durable trace from
  `status=running` to `status=interrupted` on the later docs contract-test
  pair.
- The next exact blocker is now
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py`.
- The partial runtime still ends with no `chunk_summaries` and no
  `semantic_points`.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
after the SEMARCHIVEWALKGAP live rerun had already timed out
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
  `fixture repositories under test_workspace/ are ignored during lexical walking`
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
- Lexical boundary:
  `using exact bounded JSON indexing for analysis_archive/semantic_vs_sql_comparison_1750926162.json after analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
- Trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/tests/docs/test_mre2e_evidence_contract.py`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/tests/docs/test_gagov_governance_contract.py`

Repository/index freshness evidence:

- Current commit: `9138e0b0`
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
  `mcp_server/cli/repository_commands.py`, and the new
  `tests/docs/test_gagov_governance_contract.py` lexical blocker.
- The remaining downstream work is no longer centered on the archive tail
  captured by `SEMARCHIVEWALKGAP`. It is now centered on the later docs
  contract seam uncovered by the refreshed rerun.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after
SEMARCHIVEWALKGAP.

Why:

- The SEMWALKGAP evidence refresh is real: the post-devcontainer ignore tail
  is now frozen in phase-local tests and the live status artifact.
- The stale trace bug from SEMJEDI remains closed as a unit/status contract:
  the operator surface now distinguishes missing traces, stale-running traces,
  and storage-closeout traces.
- The refreshed live rerun on commit `26a163da` still times out, but the
  durable trace now advances to
  `mcp_server/visualization/__init__.py ->
  mcp_server/visualization/quick_charts.py` while `repository status`
  truthfully terminalizes that later running trace to `interrupted`.
- The post-devcontainer ignored tail is no longer the active blocker on the
  current head.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`.

Steering outcome:

- SEMTRACEFRESHNESS acceptance remains satisfied for the operator surface: the
  stale-running condition is now reported truthfully instead of silently
  disappearing behind a missing trace.
- SEMDEVRELAPSE remains historically valid on the prior head: it captured the
  walk-order evidence showing the post-devcontainer tail was the next
  unexplained gap.
- SEMDEVSTALE and SEMTESTSTALE remain historically valid on earlier heads, and
  SEMWALKGAP now proves the refreshed current-head rerun has moved beyond the
  same-file `.devcontainer/devcontainer.json` marker again.
- SEMSCRIPTABORT and SEMROOTTESTABORT remain historically valid repairs for
  later seams that were not reached by the refreshed current-head rerun.
- The roadmap now adds downstream phase `SEMQUICKCHARTS`.
- The roadmap now adds downstream phase `SEMVALIDEVIDENCE`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the post-devcontainer ignore tail or the older
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` rebound.

## SEMQUICKCHARTS Live Rerun Check

SEMQUICKCHARTS repaired the visualization lexical seam on the current
head. The refreshed repo-local rerun advanced beyond
`mcp_server/visualization/quick_charts.py` and re-anchored on a newer exact
validation-doc blocker before the 120-second watchdog expired.

Observed runtime state during the current SEMQUICKCHARTS rerun check:

- The live rerun terminalized at `2026-04-29T13:16:35Z`.
- The durable running trace had last refreshed at `2026-04-29T13:16:25Z`
  before `repository status` truthfully terminalized it to `interrupted`.
- The SEMQUICKCHARTS live rerun used
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- Observed commit: `8f5c5f0a`
- Indexed commit before rerun: `e2e95198`
- Force-full trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/docs/validation/ga-closeout-decision.md`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/docs/validation/mre2e-evidence.md`
- Repository status now advertises the repaired visualization boundary:
  `Lexical boundary: using exact bounded Python indexing for mcp_server/visualization/quick_charts.py`
- SQLite runtime counts after the rerun:
  `files = 1114`, `code_chunks = 28182`, `chunk_summaries = 0`,
  `semantic_points = 0`

Steering outcome:

- SEMQUICKCHARTS acceptance is satisfied: the active lexical blocker is no
  longer `mcp_server/visualization/__init__.py ->
  mcp_server/visualization/quick_charts.py`.
- The live rerun now reaches the later validation-doc pair
  `docs/validation/ga-closeout-decision.md ->
  docs/validation/mre2e-evidence.md`.
- The roadmap now adds downstream phase `SEMVALIDEVIDENCE`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the visualization pair.

## SEMVALIDEVIDENCE Live Rerun Check

SEMVALIDEVIDENCE repaired the validation-doc lexical seam on the current head.
The refreshed repo-local rerun advanced beyond
`docs/validation/mre2e-evidence.md` and re-anchored on a newer exact
benchmark-doc blocker before the 120-second watchdog expired.

Observed runtime state during the current SEMVALIDEVIDENCE rerun check:

- The live rerun terminalized at `2026-04-29T13:34:20Z`.
- The durable running trace last refreshed at `2026-04-29T13:34:05Z` before
  `repository status` truthfully terminalized it to `interrupted`.
- The SEMVALIDEVIDENCE live rerun used
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- Observed commit: `705a506f`
- Indexed commit before rerun: `e2e95198`
- Force-full trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/docs/benchmarks/production_benchmark.md`
- Repository status now advertises the repaired validation boundaries:
  `Lexical boundary: using exact bounded Markdown indexing for docs/validation/ga-closeout-decision.md`
  and
  `Lexical boundary: using exact bounded Markdown indexing for docs/validation/mre2e-evidence.md`
- `repository status` still surfaces the older sync error `disk I/O error`,
  but the refreshed durable trace proves the active blocker has moved back
  into lexical walking on a later benchmark-doc pair.
- SQLite runtime counts after the rerun:
  `files = 1115`, `code_chunks = 28182`, `chunk_summaries = 0`,
  `semantic_points = 0`

Steering outcome:

- SEMVALIDEVIDENCE acceptance is satisfied: the active lexical blocker is no
  longer `docs/validation/ga-closeout-decision.md ->
  docs/validation/mre2e-evidence.md`.
- The live rerun now reaches the later benchmark-doc pair
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
  docs/benchmarks/production_benchmark.md`.
- The roadmap now adds downstream phase `SEMBENCHDOCS`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the validation-doc pair.

## SEMBENCHDOCS Live Rerun Check

SEMBENCHDOCS repaired the benchmark-doc lexical seam on the current head. The
refreshed repo-local rerun advanced beyond
`docs/benchmarks/production_benchmark.md`, but the same 120-second watchdog
still terminalized the run later in lexical walking around the archive tail.

Observed runtime state during the current SEMBENCHDOCS rerun check:

- The live rerun terminalized at `2026-04-29T13:53:03Z`.
- A later durable running snapshot at `2026-04-29T13:51:47Z` had already
  advanced to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/root_tests/test_document_plugins.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/root_tests/test_real_world_repos.py`,
  proving the benchmark-doc pair was no longer the active blocker.
- The durable running trace last refreshed at `2026-04-29T13:52:50Z` before
  `repository status` truthfully terminalized it to `interrupted`.
- The SEMBENCHDOCS live rerun used
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- Observed commit: `7282e341`
- Indexed commit before rerun: `e2e95198`
- Force-full trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
- In-flight path: `null`
- The timed-out command emitted a later oversized-file warning for
  `/home/viperjuice/code/Code-Index-MCP/analysis_archive/semantic_vs_sql_comparison_1750926162.json`
  (`32983030` bytes), which did not reopen the benchmark-doc seam.
- Repository status now advertises the repaired benchmark boundary:
  `Lexical boundary: using exact bounded Markdown indexing for docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md -> docs/benchmarks/production_benchmark.md`
- SQLite runtime counts after the rerun:
  `files = 1116`, `code_chunks = 28182`, `chunk_summaries = 0`,
  `semantic_points = 0`

Steering outcome:

- SEMBENCHDOCS acceptance is satisfied: the active lexical blocker is no
  longer
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
  docs/benchmarks/production_benchmark.md`.
- The live rerun now reaches a later archive-tail walk gap centered on
  `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`.
- The roadmap now adds downstream phase `SEMARCHIVEWALKGAP`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the benchmark-doc pair.

## SEMARCHIVEWALKGAP Live Rerun Check

SEMARCHIVEWALKGAP repaired the archive-tail walk-gap seam on the current
head. The refreshed repo-local rerun advanced beyond both
`analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py` and
the exact bounded archive JSON successor
`analysis_archive/semantic_vs_sql_comparison_1750926162.json`, but the same
120-second watchdog still terminalized the run later in lexical walking on a
docs contract-test pair.

Observed runtime state during the current SEMARCHIVEWALKGAP rerun check:

- Evidence capture completed at `2026-04-29T14:13:50Z`.
- The durable running trace last refreshed at `2026-04-29T14:12:49Z` before
  `repository status` truthfully terminalized it to `interrupted`.
- The SEMARCHIVEWALKGAP live rerun used
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `135`.
- Observed commit: `9138e0b0`
- Indexed commit before rerun: `e2e95198`
- Force-full trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/tests/docs/test_mre2e_evidence_contract.py`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/tests/docs/test_gagov_governance_contract.py`
- Repository status now advertises the repaired archive boundary:
  `Lexical boundary: using exact bounded JSON indexing for analysis_archive/semantic_vs_sql_comparison_1750926162.json after analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
- SQLite runtime counts after the rerun:
  `files = 1116`, `code_chunks = 28182`, `chunk_summaries = 0`,
  `semantic_points = 0`

Steering outcome:

- SEMARCHIVEWALKGAP acceptance is satisfied: the active lexical blocker is no
  longer the archive-tail seam centered on
  `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`.
- The live rerun now reaches the later docs contract-test pair
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py`.
- The roadmap now adds downstream phase `SEMDOCGOV`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the archive-tail seam.

## SEMDOCGOV Live Rerun Check

SEMDOCGOV repaired the docs-governance lexical seam on the current head. The
refreshed repo-local rerun advanced beyond both
`tests/docs/test_mre2e_evidence_contract.py` and
`tests/docs/test_gagov_governance_contract.py`, but the same 120-second
watchdog still terminalized the run later in lexical walking on a `.claude`
command pair.

Observed runtime state during the current SEMDOCGOV rerun check:

- Evidence capture completed at `2026-04-29T14:41:32Z`.
- The durable running trace last refreshed at `2026-04-29T14:41:18Z` before
  `repository status` truthfully terminalized it to `interrupted`.
- The SEMDOCGOV live rerun used
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- Observed commit: `cd2c183`
- Indexed commit before rerun: `e2e95198`
- Force-full trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/.claude/commands/execute-lane.md`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/.claude/commands/plan-phase.md`
- Repository status now advertises the repaired docs-governance boundary:
  `Lexical boundary: using exact bounded Python indexing for tests/docs/test_mre2e_evidence_contract.py -> tests/docs/test_gagov_governance_contract.py`
- SQLite runtime counts after the rerun:
  `files = 1119`, `code_chunks = 28182`, `chunk_summaries = 0`,
  `semantic_points = 0`

Steering outcome:

- SEMDOCGOV acceptance is satisfied: the active lexical blocker is no longer
  the docs-governance seam centered on
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py`.
- The live rerun now reaches the later `.claude` command pair
  `.claude/commands/execute-lane.md ->
  .claude/commands/plan-phase.md`.
- The roadmap now adds downstream phase `SEMCLAUDECMDS`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the docs-governance seam.

## SEMCLAUDECMDS Live Rerun Check

SEMCLAUDECMDS repaired the exact `.claude/commands` lexical seam on the
current head. The refreshed repo-local rerun advanced beyond both
`.claude/commands/execute-lane.md` and `.claude/commands/plan-phase.md`, but
the same 120-second watchdog still terminalized the run later in lexical
walking on a newer exact script pair.

Observed runtime state during the current SEMCLAUDECMDS rerun check:

- Evidence capture completed at `2026-04-29T15:03:10Z`.
- The durable running trace refreshed during the active rerun at
  `2026-04-29T15:02:46Z` and `repository status` then truthfully terminalized
  it to `interrupted` at `2026-04-29T15:03:10Z`.
- The SEMCLAUDECMDS live rerun used
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `135`.
- Observed commit: `68ae9492`
- Indexed commit before rerun: `e2e95198`
- Force-full trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/scripts/migrate_large_index_to_multi_repo.py`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/scripts/check_index_languages.py`
- Repository status now advertises the repaired `.claude` command boundary:
  `Lexical boundary: using exact bounded Markdown indexing for .claude/commands/execute-lane.md -> .claude/commands/plan-phase.md`
- SQLite runtime counts after the rerun:
  `files = 1119`, `code_chunks = 28182`, `chunk_summaries = 0`,
  `semantic_points = 0`

Steering outcome:

- SEMCLAUDECMDS acceptance is satisfied: the active lexical blocker is no
  longer the `.claude` command seam centered on
  `.claude/commands/execute-lane.md ->
  .claude/commands/plan-phase.md`.
- The live rerun now reaches the later script pair
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py`.
- The roadmap now adds downstream phase `SEMSCRIPTLANGS`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the `.claude` command seam.

## SEMSCRIPTLANGS Live Rerun Check

SEMSCRIPTLANGS repaired the exact later script-language lexical seam on the
current head. The refreshed repo-local rerun advanced beyond both
`scripts/migrate_large_index_to_multi_repo.py` and
`scripts/check_index_languages.py`, but the same 120-second watchdog still
terminalized the run later in lexical walking on a newer exact phase-plan
markdown pair.

Observed runtime state during the current SEMSCRIPTLANGS rerun check:

- Evidence capture completed at `2026-04-29T15:24:06Z`.
- The durable raw trace snapshot last refreshed at `2026-04-29T15:22:41Z`
  while still marked `running`, and `repository status` then truthfully
  terminalized the same blocker to `interrupted` using the later observed
  trace timestamp `2026-04-29T15:22:48Z`.
- The SEMSCRIPTLANGS live rerun used
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- Observed commit: `769cd75c`
- Indexed commit before rerun: `e2e95198`
- Force-full trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMPREFLIGHT.md`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOCGOV.md`
- Repository status now advertises the repaired script-language boundary:
  `Lexical boundary: using exact bounded Python indexing for scripts/migrate_large_index_to_multi_repo.py -> scripts/check_index_languages.py`
- Repository status still reports the historical field `Last sync error:
  disk I/O error`, but the active blocker for this rerun is the later lexical
  phase-plan pair above.
- SQLite runtime counts after the rerun:
  `files = 1119`, `code_chunks = 28182`, `chunk_summaries = 0`,
  `semantic_points = 0`

Steering outcome:

- SEMSCRIPTLANGS acceptance is satisfied: the active lexical blocker is no
  longer the script language-audit seam centered on
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py`.
- The live rerun now reaches the later phase-plan markdown pair
  `plans/phase-plan-v7-SEMPREFLIGHT.md ->
  plans/phase-plan-v7-SEMDOCGOV.md`.
- The roadmap now adds downstream phase `SEMPHASEPLANS`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the script language-audit seam.

## SEMPHASEPLANS Live Rerun Check

SEMPHASEPLANS did not need a new dispatcher or Markdown-path repair on the
current head. The refreshed repo-local rerun advanced durably beyond
`plans/phase-plan-v7-SEMPREFLIGHT.md` and
`plans/phase-plan-v7-SEMDOCGOV.md`, but the same 120-second watchdog still
terminalized the run later in lexical walking on a newer cross-version
phase-plan pair.

Observed runtime state during the current SEMPHASEPLANS rerun check:

- Evidence capture completed at `2026-04-29T15:37:57Z`.
- The durable raw trace snapshot last refreshed at `2026-04-29T15:37:54Z`
  while still marked `running`, and `repository status` then truthfully
  terminalized the same blocker to `interrupted` using the later observed
  trace timestamp `2026-04-29T15:37:57Z`.
- The SEMPHASEPLANS live rerun used
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- Observed commit: `40968140`
- Indexed commit before rerun: `e2e95198`
- Force-full trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-garecut.md`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMWALKGAP.md`
- The SEMPHASEPLANS target pair is no longer the active blocker:
  `plans/phase-plan-v7-SEMPREFLIGHT.md ->
  plans/phase-plan-v7-SEMDOCGOV.md`.
- `repository status` still advertises only the earlier bounded lexical
  surfaces; the newly exposed cross-version phase-plan seam is currently
  visible through `force_full_exit_trace.json`, not a dedicated lexical
  boundary line yet.
- Repository status still reports the historical field `Last sync error:
  disk I/O error`, but the active blocker for this rerun is the later lexical
  phase-plan pair above.
- SQLite runtime counts after the rerun:
  `files = 1119`, `code_chunks = 28182`, `chunk_summaries = 0`,
  `semantic_points = 0`

Steering outcome:

- SEMPHASEPLANS acceptance is satisfied for its named blocker: the active
  lexical blocker is no longer
  `plans/phase-plan-v7-SEMPREFLIGHT.md ->
  plans/phase-plan-v7-SEMDOCGOV.md`.
- The live rerun now reaches the later cross-version phase-plan pair
  `plans/phase-plan-v5-garecut.md ->
  plans/phase-plan-v7-SEMWALKGAP.md`.
- The roadmap now adds downstream phase `SEMCROSSPLANS`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the `SEMPREFLIGHT -> SEMDOCGOV` phase-plan seam.

## SEMCROSSPLANS Live Rerun Check

SEMCROSSPLANS also did not need a new dispatcher or Markdown-path repair on
the current head. The refreshed repo-local rerun advanced durably beyond
`plans/phase-plan-v5-garecut.md` and
`plans/phase-plan-v7-SEMWALKGAP.md`, but the same 120-second watchdog still
terminalized the run later in lexical walking on a newer v7-only phase-plan
pair.

Observed runtime state during the current SEMCROSSPLANS rerun check:

- Evidence capture completed at `2026-04-29T15:51:12Z`.
- The durable raw trace snapshot last refreshed at `2026-04-29T15:51:03Z`
  while still marked `running`, and `repository status` then truthfully
  terminalized the same blocker to `interrupted` using the later observed
  trace timestamp `2026-04-29T15:51:12Z`.
- The SEMCROSSPLANS live rerun used
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- Observed commit: `d0b21255`
- Indexed commit before rerun: `e2e95198`
- Force-full trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSYNCFIX.md`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMVISUALREPORT.md`
- The SEMCROSSPLANS target pair is no longer the active blocker:
  `plans/phase-plan-v5-garecut.md ->
  plans/phase-plan-v7-SEMWALKGAP.md`.
- `repository status` still advertises only the earlier bounded lexical
  surfaces; the newly exposed later phase-plan seam is currently visible
  through `force_full_exit_trace.json`, not a dedicated lexical boundary line
  yet.
- Repository status still reports the historical field `Last sync error:
  disk I/O error`, but the active blocker for this rerun is the later lexical
  phase-plan pair above.
- SQLite runtime counts after the rerun:
  `files = 1122`, `code_chunks = 28182`, `chunk_summaries = 0`,
  `semantic_points = 0`

Steering outcome:

- SEMCROSSPLANS acceptance is satisfied for its named blocker: the active
  lexical blocker is no longer
  `plans/phase-plan-v5-garecut.md ->
  plans/phase-plan-v7-SEMWALKGAP.md`.
- The live rerun now reaches the later v7-only phase-plan pair
  `plans/phase-plan-v7-SEMSYNCFIX.md ->
  plans/phase-plan-v7-SEMVISUALREPORT.md`.
- The roadmap now adds downstream phase `SEMPHASETAIL`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the `garecut -> SEMWALKGAP` cross-version phase-plan seam.

## SEMPHASETAIL Live Rerun Check

SEMPHASETAIL also did not need a new dispatcher or Markdown-path repair on
the current head. The refreshed repo-local rerun advanced durably beyond
`plans/phase-plan-v7-SEMSYNCFIX.md` and
`plans/phase-plan-v7-SEMVISUALREPORT.md`, but the same 120-second watchdog
still terminalized the run later in lexical walking on a historical
phase-plan pair.

Observed runtime state during the current SEMPHASETAIL rerun check:

- Evidence capture completed at `2026-04-29T16:07:22Z`.
- The SEMPHASETAIL live rerun used
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- Observed commit: `fe501b97`
- Indexed commit before rerun: `e2e95198`
- Force-full trace status: `interrupted`
- Trace stage: `lexical_walking`
- Trace stage family: `lexical`
- Trace blocker source: `lexical_mutation`
- Last progress path:
  `/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v6-WATCH.md`
- In-flight path:
  `/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v1-p19.md`
- The SEMPHASETAIL target pair is no longer the active blocker:
  `plans/phase-plan-v7-SEMSYNCFIX.md ->
  plans/phase-plan-v7-SEMVISUALREPORT.md`.
- `repository status` now advertises the repaired exact bounded lexical
  surface:
  `Lexical boundary: using exact bounded Markdown indexing for plans/phase-plan-v7-SEMSYNCFIX.md -> plans/phase-plan-v7-SEMVISUALREPORT.md`.
- The newly exposed later blocker is the historical phase-plan pair above;
  it is visible through `force_full_exit_trace.json`, not a dedicated lexical
  boundary line yet.
- Repository status still reports the historical field `Last sync error:
  disk I/O error`, but the active blocker for this rerun is the later
  lexical phase-plan pair above.
- SQLite runtime counts after the rerun:
  `files = 1123`, `code_chunks = 28182`, `chunk_summaries = 0`,
  `semantic_points = 0`

Steering outcome:

- SEMPHASETAIL acceptance is satisfied for its named blocker: the active
  lexical blocker is no longer
  `plans/phase-plan-v7-SEMSYNCFIX.md ->
  plans/phase-plan-v7-SEMVISUALREPORT.md`.
- The live rerun now reaches the historical phase-plan pair
  `plans/phase-plan-v6-WATCH.md ->
  plans/phase-plan-v1-p19.md`.
- The roadmap now adds downstream phase `SEMLEGACYPLANS`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the `SEMSYNCFIX -> SEMVISUALREPORT` phase-plan seam.

## SEMLEGACYPLANS Live Rerun Check

SEMLEGACYPLANS tightened the exact historical phase-plan seam in the bounded
Markdown and operator-status surfaces, and the refreshed live rerun advanced
durably beyond `plans/phase-plan-v6-WATCH.md` and
`plans/phase-plan-v1-p19.md` before the 120-second watchdog expired.

Code/test repair completed in this phase:

- `mcp_server/plugins/markdown_plugin/plugin.py` now treats
  `plans/phase-plan-v6-WATCH.md` and `plans/phase-plan-v1-p19.md` as exact
  bounded Markdown paths in addition to the generic lightweight phase-plan
  rule.
- `mcp_server/cli/repository_commands.py` now advertises the repaired exact
  bounded lexical boundary for
  `plans/phase-plan-v6-WATCH.md -> plans/phase-plan-v1-p19.md`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` now freeze dispatcher discoverability,
  durable trace progression, and status reporting for the exact historical
  phase-plan pair without widening into a blanket `plans/phase-plan-*.md`
  bypass.

Observed progression on the refreshed live repo-local force-full command:

- The SEMLEGACYPLANS live rerun started on observed commit `7ab3e4ca` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- At `2026-04-29T16:29:03Z`, `force_full_exit_trace.json` still showed a
  running lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMPHASETAIL.md`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gagov.md`.
- At `2026-04-29T16:29:12Z`, `repository status` terminalized that stale
  running snapshot to `Trace status: interrupted` with the same
  `SEMPHASETAIL -> phase-plan-v5-gagov.md` pair and advertised the repaired
  exact bounded historical lexical surface:
  `Lexical boundary: using exact bounded Markdown indexing for plans/phase-plan-v6-WATCH.md -> plans/phase-plan-v1-p19.md`.
- SQLite runtime counts after the rerun remained
  `files = 1123`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`.

Steering outcome:

- SEMLEGACYPLANS acceptance is satisfied for its named blocker: the active
  lexical blocker is no longer
  `plans/phase-plan-v6-WATCH.md ->
  plans/phase-plan-v1-p19.md`.
- The live rerun now reaches the mixed-version phase-plan pair
  `plans/phase-plan-v7-SEMPHASETAIL.md ->
  plans/phase-plan-v5-gagov.md`.
- The roadmap now adds downstream phase `SEMMIXEDPHASETAIL`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the historical `WATCH -> p19` phase-plan seam.

## SEMMIXEDPHASETAIL Live Rerun Check

SEMMIXEDPHASETAIL tightened the exact mixed-version phase-plan seam in the
bounded Markdown and operator-status surfaces, and the refreshed live rerun
advanced durably beyond `plans/phase-plan-v7-SEMPHASETAIL.md` and
`plans/phase-plan-v5-gagov.md` before the 120-second watchdog expired.

Code/test repair completed in this phase:

- `mcp_server/plugins/markdown_plugin/plugin.py` now treats
  `plans/phase-plan-v7-SEMPHASETAIL.md` and `plans/phase-plan-v5-gagov.md`
  as exact bounded Markdown paths in addition to the generic lightweight
  phase-plan rule.
- `mcp_server/cli/repository_commands.py` now advertises the repaired exact
  bounded lexical boundary for
  `plans/phase-plan-v7-SEMPHASETAIL.md -> plans/phase-plan-v5-gagov.md`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` now freeze dispatcher discoverability,
  durable trace progression, and status reporting for the exact mixed-version
  phase-plan pair without widening into a blanket `plans/phase-plan-*.md`
  bypass.

Observed progression on the refreshed repo-local force-full command:

- The SEMMIXEDPHASETAIL live rerun started on observed commit `468dee18` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- At `2026-04-29T16:42:11Z`, `force_full_exit_trace.json` showed a running
  lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/celery_overview.md`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/qdrant.md`.
- At `2026-04-29T16:42:21Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same
  `ai_docs/celery_overview.md -> ai_docs/qdrant.md` pair and advertised the
  repaired exact bounded mixed-version lexical surface:
  `Lexical boundary: using exact bounded Markdown indexing for plans/phase-plan-v7-SEMPHASETAIL.md -> plans/phase-plan-v5-gagov.md`.
- After the exact mixed-version Markdown/status repair landed, a fresh rerun
  on the same observed commit again exited with code `124`.
- At `2026-04-29T16:49:38Z`, `force_full_exit_trace.json` showed a newer
  running lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/preflight_upgrade.sh`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/test_mcp_protocol_direct.py`.
- At `2026-04-29T16:49:50Z`, `repository status` terminalized that newer
  running snapshot to `Trace status: interrupted` with the same
  `scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py`
  pair while still advertising the repaired exact bounded mixed-version
  lexical surface for
  `plans/phase-plan-v7-SEMPHASETAIL.md -> plans/phase-plan-v5-gagov.md`.
- SQLite runtime counts after the rerun remained
  `files = 1123`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`.

Steering outcome:

- SEMMIXEDPHASETAIL acceptance is satisfied for its named blocker: the active
  lexical blocker is no longer
  `plans/phase-plan-v7-SEMPHASETAIL.md ->
  plans/phase-plan-v5-gagov.md`.
- The first refreshed rerun moved beyond the mixed-version phase-plan pair to
  the transient ai-docs lexical pair
  `ai_docs/celery_overview.md ->
  ai_docs/qdrant.md`.
- The final authoritative rerun for this phase moved later still and now
  reaches the script lexical pair
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py`.
- The roadmap now adds downstream phase `SEMPREUPGRADETAIL`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as either the mixed-version
  `SEMPHASETAIL -> phase-plan-v5-gagov.md` phase-plan seam or the transient
  `ai_docs/celery_overview.md -> ai_docs/qdrant.md` waypoint.

## SEMPREUPGRADETAIL Live Rerun Check

SEMPREUPGRADETAIL tightened the exact mixed shell/Python script seam in the
dispatcher and operator-status surfaces, and the refreshed live rerun
advanced durably beyond `scripts/preflight_upgrade.sh` and
`scripts/test_mcp_protocol_direct.py` before the 120-second watchdog expired.

Code/test repair completed in this phase:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now treats
  `scripts/preflight_upgrade.sh` as an exact bounded shell path and
  `scripts/test_mcp_protocol_direct.py` as an exact bounded Python path,
  preserving full-text discoverability plus the `preflight_env` and
  `test_mcp_protocol` entry surfaces without widening into a blanket
  `scripts/*.sh` or `scripts/*.py` bypass.
- `mcp_server/cli/repository_commands.py` now advertises the repaired exact
  bounded lexical boundary for
  `scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` now freeze dispatcher discoverability,
  durable trace progression, and status reporting for the exact mixed
  shell/Python pair without widening into a broader script-family shortcut.

Observed progression on the refreshed repo-local force-full command:

- The SEMPREUPGRADETAIL live rerun started on observed commit `c240c23e` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- At `2026-04-29T17:07:44Z`, `force_full_exit_trace.json` showed a running
  lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/verify_embeddings.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/claude_code_behavior_simulator.py`.
- At `2026-04-29T17:07:52Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same
  `scripts/verify_embeddings.py -> scripts/claude_code_behavior_simulator.py`
  pair while advertising the repaired exact bounded shell/Python lexical
  surface:
  `Lexical boundary: using exact bounded shell/Python indexing for scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py`.
- SQLite runtime counts after the rerun remained
  `files = 1123`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`.

Steering outcome:

- SEMPREUPGRADETAIL acceptance is satisfied for its named blocker: the active
  lexical blocker is no longer
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py`.
- The final authoritative rerun for this phase moved later and now reaches the
  Python-script lexical pair
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py`.
- The roadmap now adds downstream phase `SEMVERIFYSIMTAIL`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the preflight-upgrade
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py` script seam.

## SEMVERIFYSIMTAIL Live Rerun Check

SEMVERIFYSIMTAIL tightened the exact later Python-script seam in the
dispatcher, Python plugin, and operator-status surfaces, and the refreshed live
rerun advanced durably beyond `scripts/verify_embeddings.py` and
`scripts/claude_code_behavior_simulator.py` before the 120-second watchdog
expired.

Code/test repair completed in this phase:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now treats
  `scripts/verify_embeddings.py` and
  `scripts/claude_code_behavior_simulator.py` as exact bounded Python paths,
  preserving full-text discoverability plus the `verify_embeddings()` and
  `ClaudeCodeSimulator` entry surfaces without widening into a blanket
  `scripts/*.py` bypass.
- `mcp_server/plugins/python_plugin/plugin.py` now keeps the same exact pair
  on the bounded chunk path list so direct Python-plugin indexing stays aligned
  with dispatcher exact-bounded behavior.
- `mcp_server/cli/repository_commands.py` now advertises the repaired exact
  bounded lexical boundary for
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` now freeze dispatcher discoverability,
  durable trace progression, and status reporting for the exact verify/simulator
  pair without widening into a broader script-family shortcut.

Observed progression on the refreshed repo-local force-full command:

- The SEMVERIFYSIMTAIL live rerun started on observed commit `504e419a` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- Immediately after the timeout, a direct `repository status` probe still
  showed `Force-full exit trace: missing`, but the durable trace file had
  already been rewritten in `.mcp-index/force_full_exit_trace.json`.
- At `2026-04-29T17:28:28Z`, `force_full_exit_trace.json` showed a running
  lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/create_semantic_embeddings.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/consolidate_real_performance_data.py`.
- At `2026-04-29T17:28:49Z`, a refreshed `repository status` terminalized that
  running snapshot to `Trace status: interrupted` with the same
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py` pair while advertising both
  repaired exact bounded lexical surfaces:
  `Lexical boundary: using exact bounded shell/Python indexing for scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py`
  and
  `Lexical boundary: using exact bounded Python indexing for scripts/verify_embeddings.py -> scripts/claude_code_behavior_simulator.py`.
- SQLite runtime counts after the rerun remained
  `files = 1123`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`.

Steering outcome:

- SEMVERIFYSIMTAIL acceptance is satisfied for its named blocker: the active
  lexical blocker is no longer
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py`.
- The final authoritative rerun for this phase moved later and now reaches the
  Python-script lexical pair
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py`.
- The roadmap now adds downstream phase `SEMEMBEDCONSOL`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the verify/simulator
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py` script seam.

## SEMEMBEDCONSOL Live Rerun Check

SEMEMBEDCONSOL tightened the exact later Python-script seam in the
dispatcher, Python plugin, and operator-status surfaces, and the refreshed live
rerun advanced durably beyond `scripts/create_semantic_embeddings.py` and
`scripts/consolidate_real_performance_data.py` before the 120-second watchdog
expired.

Code/test repair completed in this phase:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now treats
  `scripts/create_semantic_embeddings.py` and
  `scripts/consolidate_real_performance_data.py` as exact bounded Python
  paths, preserving full-text discoverability plus
  `get_repository_info(...)`, `process_repository(...)`,
  `ConsolidatedResult`, and `PerformanceDataConsolidator` without widening
  into a blanket `scripts/*.py` bypass.
- `mcp_server/plugins/python_plugin/plugin.py` now keeps the same exact pair
  on the bounded chunk path list so direct Python-plugin indexing stays aligned
  with dispatcher exact-bounded behavior.
- `mcp_server/cli/repository_commands.py` now advertises the repaired exact
  bounded lexical boundary for
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py`:
  `Lexical boundary: using exact bounded Python indexing for scripts/create_semantic_embeddings.py -> scripts/consolidate_real_performance_data.py`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` now freeze dispatcher discoverability,
  durable trace progression, and status reporting for the exact
  embed/consolidation pair without widening into a broader script-family
  shortcut.

Observed progression on the refreshed repo-local force-full command:

- The SEMEMBEDCONSOL live rerun started on observed commit `5c0102d` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- At `2026-04-29T17:45:44Z`, `.mcp-index/force_full_exit_trace.json` showed a
  running lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_gaclose_evidence_closeout.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_p8_deployment_security.py`.
- At `2026-04-29T17:45:52Z`, a refreshed `repository status` terminalized that
  running snapshot to `Trace status: interrupted` with the same
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py` pair while advertising the
  repaired exact bounded Python lexical surfaces for both the
  verify/simulator and embed/consolidation seams.
- SQLite runtime counts after the rerun remained
  `files = 1123`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`.

Steering outcome:

- SEMEMBEDCONSOL acceptance is satisfied for its named blocker: the active
  lexical blocker is no longer
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py`.
- The final authoritative rerun for this phase moved later and now reaches the
  tests/docs lexical pair
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py`.
- The roadmap now adds downstream phase `SEMDOCTESTTAIL`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the embed/consolidation
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py` script seam.

## SEMDOCTESTTAIL Live Rerun Check

SEMDOCTESTTAIL tightened the exact later docs-test seam and corrected an
existing exact-bounded Python fallback so invalid-syntax bounded files remain
content-discoverable instead of aborting lexical walking.

- `mcp_server/dispatcher/dispatcher_enhanced.py` now treats exact bounded
  Python files with invalid syntax as content-only bounded shards instead of
  raising from `ast.parse(...)`.
- `mcp_server/plugins/python_plugin/plugin.py` now keeps
  `tests/docs/test_gaclose_evidence_closeout.py` and
  `tests/docs/test_p8_deployment_security.py` on the bounded chunk path list so
  direct Python-plugin indexing stays aligned with dispatcher exact-bounded
  behavior.
- `mcp_server/cli/repository_commands.py` now advertises the repaired exact
  bounded lexical boundary for
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py`:
  `Lexical boundary: using exact bounded Python indexing for tests/docs/test_gaclose_evidence_closeout.py -> tests/docs/test_p8_deployment_security.py`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` now freeze dispatcher discoverability,
  invalid-syntax exact-bounded fallback, durable trace progression, and status
  reporting for the later docs-test pair without widening into a broader
  tests/docs shortcut.

Observed progression on the refreshed repo-local force-full command:

- A first SEMDOCTESTTAIL rerun exposed an exact-bounded fallback bug on
  `scripts/consolidate_real_performance_data.py`; the run exited with code
  `124` after `ast.parse(...)` raised on invalid syntax before the later
  docs-test tail could be trusted.
- After the exact-bounded invalid-syntax fallback landed, the refreshed
  SEMDOCTESTTAIL live rerun started on observed commit `4133bfe` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- At `2026-04-29T18:06:31Z`, `.mcp-index/force_full_exit_trace.json` showed a
  running lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/security/fixtures/mock_plugin/plugin.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/security/fixtures/mock_plugin/__init__.py`.
- At `2026-04-29T18:06:41Z`, a refreshed `repository status` terminalized that
  running snapshot to `Trace status: interrupted` with the same
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py` pair while advertising the
  repaired exact bounded Python lexical surfaces for the docs-governance,
  docs-test, verify/simulator, and embed/consolidation seams.
- The SEMDOCTESTTAIL target pair is no longer the active blocker:
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py`.
- SQLite runtime counts after the rerun remained
  `files = 1123`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`.

Steering outcome:

- SEMDOCTESTTAIL acceptance is satisfied for its named blocker: the active
  lexical blocker is no longer
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py`.
- The final authoritative rerun for this phase moved later and now reaches the
  security-fixture lexical pair
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py`.
- The roadmap now adds downstream phase `SEMMOCKPLUGIN`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the docs-test
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py` seam.

## SEMMOCKPLUGIN Live Rerun Check

SEMMOCKPLUGIN tightened the exact later mock-plugin seam and aligned the
operator boundary surface so the repaired security-fixture pair remains
discoverable without burning the lexical watchdog on direct Python chunking.

Code/test repair completed in this phase:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now treats
  `tests/security/fixtures/mock_plugin/plugin.py` and
  `tests/security/fixtures/mock_plugin/__init__.py` as exact bounded Python
  paths, preserving bounded symbol and content discoverability without widening
  into a blanket `tests/security/fixtures/**/*.py` bypass.
- `mcp_server/plugins/python_plugin/plugin.py` now keeps the same exact pair on
  the bounded chunk path list so direct Python-plugin indexing stays aligned
  with dispatcher exact-bounded behavior.
- `mcp_server/cli/repository_commands.py` now advertises the repaired exact
  bounded lexical boundary for
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py`:
  `Lexical boundary: using exact bounded Python indexing for tests/security/fixtures/mock_plugin/plugin.py -> tests/security/fixtures/mock_plugin/__init__.py`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` now freeze dispatcher discoverability,
  durable trace progression, and status reporting for the later mock-plugin
  pair without widening into a broader security-fixture shortcut.

Observed progression on the refreshed repo-local force-full command:

- The refreshed SEMMOCKPLUGIN live rerun started on observed commit
  `6a909203` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- At `2026-04-29T18:25:58Z`, `.mcp-index/force_full_exit_trace.json` showed a
  running lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.codex/phase-loop/runs/20260424T180441Z-01-gagov-execute/launch.json`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.codex/phase-loop/runs/20260427T071807Z-02-artpub-execute/terminal-summary.json`.
- At `2026-04-29T18:26:11Z`, a refreshed `repository status` terminalized that
  running snapshot to `Trace status: interrupted` with the same
  `.codex/phase-loop/.../launch.json ->
  .codex/phase-loop/.../terminal-summary.json` pair while advertising the
  repaired exact bounded Python lexical surface for the mock-plugin seam.
- The SEMMOCKPLUGIN target pair is no longer the active blocker:
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py`.
- SQLite runtime counts after the rerun remained
  `files = 1123`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`.

Steering outcome:

- SEMMOCKPLUGIN acceptance is satisfied for its named blocker: the active
  lexical blocker is no longer
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py`.
- The final authoritative rerun for this phase moved later and now reaches the
  legacy `.codex/phase-loop` lexical pair
  `.codex/phase-loop/runs/20260424T180441Z-01-gagov-execute/launch.json ->
  .codex/phase-loop/runs/20260427T071807Z-02-artpub-execute/terminal-summary.json`.
- The roadmap now adds downstream phase `SEMCODEXLOOPTAIL`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the mock-plugin
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py` seam.

## SEMCODEXLOOPTAIL Live Rerun Check

SEMCODEXLOOPTAIL tightened the legacy `.codex/phase-loop` compatibility-runtime
surface so the old `launch.json -> terminal-summary.json` blocker is no longer
the active tail and `repository status` now distinguishes that repaired family
from canonical `.phase-loop/` runner state.

Code/test repair completed in this phase:

- `mcp_server/plugins/generic_treesitter_plugin.py` now recognizes the narrow
  legacy `.codex/phase-loop` JSON family under `runs/*/launch.json`,
  `runs/*/terminal-summary.json`, `archive/*/state.json`, and top-level
  legacy `state.json`, plus the matching `events.jsonl` ledger family, without
  widening into a blanket `.codex/**` bypass.
- `mcp_server/dispatcher/dispatcher_enhanced.py` now routes those exact legacy
  JSON and JSONL compatibility-runtime artifacts through bounded lexical
  persistence, including `.jsonl` files that previously missed the supported
  extension gate before the bounded shard could run.
- `mcp_server/cli/repository_commands.py` now advertises the repaired exact
  bounded lexical surface as
  `Lexical boundary: using exact bounded JSON/JSONL indexing for legacy .codex/phase-loop compatibility runtime artifacts while canonical .phase-loop remains authoritative`.
- `tests/test_dispatcher.py` and `tests/test_repository_commands.py` now freeze
  the legacy run/archive fixture family while proving canonical
  `.phase-loop/state.json` stays on its normal JSON path.

Observed progression on the refreshed repo-local force-full command:

- The first refreshed SEMCODEXLOOPTAIL live rerun started on observed commit
  `3d627c33` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- At `2026-04-29T18:48:10Z`, `.mcp-index/force_full_exit_trace.json` showed a
  running lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.codex/phase-loop/runs/20260427T085911Z-02-mrready-execute/launch.json`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.codex/phase-loop/runs/20260427T085911Z-02-mrready-execute/heartbeat.json`.
- At `2026-04-29T18:48:20Z`, a refreshed `repository status` terminalized that
  running snapshot to `Trace status: interrupted` with the same
  `.codex/phase-loop/.../launch.json ->
  .codex/phase-loop/.../heartbeat.json` pair while advertising the repaired
  exact bounded JSON/JSONL compatibility-runtime surface.
- The earlier SEMMOCKPLUGIN-era legacy pair was no longer the active blocker:
  `.codex/phase-loop/runs/20260424T180441Z-01-gagov-execute/launch.json ->
  .codex/phase-loop/runs/20260427T071807Z-02-artpub-execute/terminal-summary.json`.
- The second refreshed SEMCODEXLOOPTAIL live rerun on the same observed commit
  `3d627c33` used the same command, exited with code `124`, and advanced beyond
  the legacy `.codex/phase-loop` compatibility-runtime family entirely.
- At `2026-04-29T18:52:49Z`, `.mcp-index/force_full_exit_trace.json` showed a
  running lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_semincr_contract.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_gabase_ga_readiness_contract.py`.
- At `2026-04-29T18:52:55Z`, a refreshed `repository status` terminalized that
  running snapshot to `Trace status: interrupted` with the same
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py` pair while keeping the
  repaired legacy `.codex/phase-loop` boundary advertised as historical
  cleared ground rather than the active blocker.
- SQLite runtime counts after the rerun remained
  `files = 1152`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`.

Steering outcome:

- SEMCODEXLOOPTAIL acceptance is satisfied for its named blocker family: the
  live watchdog no longer terminalizes on the legacy `.codex/phase-loop`
  compatibility-runtime artifacts that motivated this phase.
- The intermediate same-family pair
  `.codex/phase-loop/runs/20260427T085911Z-02-mrready-execute/launch.json ->
  .codex/phase-loop/runs/20260427T085911Z-02-mrready-execute/heartbeat.json`
  is also no longer the active blocker after the heartbeat repair.
- The current active blocker is now the later docs contract-test pair
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py`.
- The roadmap now adds downstream phase `SEMDOCCONTRACTTAIL`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as a legacy `.codex/phase-loop` compatibility-runtime seam.

## SEMDOCCONTRACTTAIL Live Rerun Check

SEMDOCCONTRACTTAIL tightened the later docs contract-test seam so the
`test_semincr_contract.py -> test_gabase_ga_readiness_contract.py` blocker is
no longer the active lexical tail and `repository status` now advertises that
repaired boundary while preserving the next blocker truthfully.

Code/test repair completed in this phase:

- `mcp_server/dispatcher/dispatcher_enhanced.py` now treats
  `tests/docs/test_semincr_contract.py` and
  `tests/docs/test_gabase_ga_readiness_contract.py` as exact bounded Python
  paths, preserving bounded symbol and content discoverability without
  widening into a blanket `tests/docs/**/*.py` bypass.
- `mcp_server/plugins/python_plugin/plugin.py` now keeps the same exact pair on
  the bounded chunk path list so direct Python-plugin indexing stays aligned
  with dispatcher exact-bounded behavior.
- `mcp_server/cli/repository_commands.py` now advertises the repaired exact
  bounded lexical boundary for
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py`:
  `Lexical boundary: using exact bounded Python indexing for tests/docs/test_semincr_contract.py -> tests/docs/test_gabase_ga_readiness_contract.py`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` now freeze dispatcher discoverability,
  durable trace progression, and status reporting for the later docs
  contract-test pair without widening into a broader docs-test shortcut.

Observed progression on the refreshed repo-local force-full command:

- The refreshed SEMDOCCONTRACTTAIL live rerun started on observed commit
  `2167f184` via
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  and exited with code `124`.
- At `2026-04-29T19:13:08Z`, `.mcp-index/force_full_exit_trace.json` showed a
  running lexical trace on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_garc_rc_soak_contract.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_garel_ga_release_contract.py`.
- At `2026-04-29T19:13:19Z`, a refreshed `repository status` terminalized that
  running snapshot to `Trace status: interrupted` with the same
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py` pair while advertising the
  repaired exact bounded Python surface for the cleared
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py` seam.
- The SEMDOCCONTRACTTAIL target pair is no longer the active blocker:
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py`.
- SQLite runtime counts after the rerun remained
  `files = 1152`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`.

Steering outcome:

- SEMDOCCONTRACTTAIL acceptance is satisfied for its named blocker: the live
  watchdog no longer terminalizes on
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py`.
- The final authoritative rerun for this phase moved later and now reaches the
  GA release docs contract-test pair
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py`.
- The roadmap now adds downstream phase `SEMGARELTAIL`.
- Older downstream assumptions should be treated as stale, including any
  downstream phase plan or handoff that still treats the active current-head
  blocker as the SEMDOCCONTRACTTAIL-era docs contract seam
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py`.

## Verification

Verification sequence for this SEMDOCCONTRACTTAIL slice:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "semincr or gabase or docs_contract or readiness or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "semincr or gabase or docs_contract or readiness or boundary or interrupted or lexical"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Verification sequence for this SEMEMBEDCONSOL slice:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "create_semantic_embeddings or consolidate_real_performance_data or lexical or bounded or consolidator or script"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "create_semantic_embeddings or consolidate_real_performance_data or lexical or interrupted or boundary or consolidator or script"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Verification sequence for this SEMDOCTESTTAIL slice:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "gaclose_evidence_closeout or p8_deployment_security or consolidate_real_performance_data or lexical or bounded or deployment or security or docs or consolidator"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "gaclose_evidence_closeout or p8_deployment_security or consolidate_real_performance_data or lexical or interrupted or boundary or deployment or security or docs or consolidator"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Verification sequence for this SEMMOCKPLUGIN slice:

```bash
uv run pytest tests/test_dispatcher.py tests/security/test_plugin_sandbox.py -q --no-cov -k "mock_plugin or lexical or bounded or sandbox or fixture"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "mock_plugin or lexical or interrupted or boundary or sandbox or fixture"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Verification sequence for this SEMCROSSPLANS slice:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or garecut or SEMWALKGAP or markdown or lexical"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "phase_plan or garecut or SEMWALKGAP or lexical or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Verification sequence for this SEMPHASETAIL slice:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or SEMSYNCFIX or SEMVISUALREPORT or markdown or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "phase_plan or SEMSYNCFIX or SEMVISUALREPORT or lexical or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Verification sequence for this SEMLEGACYPLANS slice:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or WATCH or p19 or markdown or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "phase_plan or WATCH or p19 or lexical or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Verification sequence for this SEMMIXEDPHASETAIL slice:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or SEMPHASETAIL or gagov or markdown or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "phase_plan or SEMPHASETAIL or gagov or lexical or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Verification sequence for this SEMPREUPGRADETAIL slice:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "preflight_upgrade or test_mcp_protocol_direct or lexical or bounded or shell or script"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "preflight_upgrade or test_mcp_protocol_direct or lexical or interrupted or boundary or script"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Verification sequence for this SEMVERIFYSIMTAIL slice:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "verify_embeddings or claude_code_behavior_simulator or lexical or bounded or simulator or script"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "verify_embeddings or claude_code_behavior_simulator or lexical or interrupted or boundary or simulator or script"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```
