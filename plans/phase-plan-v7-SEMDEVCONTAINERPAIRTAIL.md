---
phase_loop_plan_version: 1
phase: SEMDEVCONTAINERPAIRTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 782d37327ea7270d7eccc7c9bc08ac1136611119e04cca5d048245812ae68596
---
# SEMDEVCONTAINERPAIRTAIL: Devcontainer Tail Pair Recovery

## Context

SEMDEVCONTAINERPAIRTAIL is the phase-97 follow-up for the v7 semantic
hardening roadmap. Canonical `.phase-loop/` runtime exists in this checkout,
so it is the authoritative runner state for this planning run. The current
canonical state still shows `SEMAIDOCREADMETAIL` as `blocked` because its
closeout reported unrelated dirty runtime paths, but `.phase-loop/state.json`
also records `SEMDEVCONTAINERPAIRTAIL` as `unplanned`, and the user explicitly
requested this downstream plan artifact write. Legacy `.codex/phase-loop/`
artifacts remain compatibility-only and do not supersede canonical
`.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `782d37327ea7270d7eccc7c9bc08ac1136611119e04cca5d048245812ae68596`.
- The target artifact `plans/phase-plan-v7-SEMDEVCONTAINERPAIRTAIL.md` did not
  exist before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live evidence anchor. Its
  `SEMAIDOCREADMETAIL Live Rerun Check` block records that the refreshed
  repo-local force-full rerun on observed commit
  `518d15a54a99a4d8872a6684bb44cfc0399157cb` no longer terminalized at
  `ai_docs/prometheus_overview.md -> ai_docs/README.md` and instead moved
  later into the `.devcontainer` surface
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json`.
- The same evidence block captures the current live trace for this phase: at
  `2026-04-30T06:39:04Z`, `.mcp-index/force_full_exit_trace.json` reported
  `status: running`, `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`;
  at `2026-04-30T06:39:16Z`, `uv run mcp-index repository status`
  terminalized the same rerun to `Trace status: interrupted` while preserving
  that exact later pair.
- The two `.devcontainer` files are small and already have some bounded
  treatment. `.devcontainer/post_create.sh` is a short setup shell script that
  creates a uv environment and installs requirements, and
  `.devcontainer/devcontainer.json` is a small config that points
  `postCreateCommand` back at that script.
- Existing code and tests already freeze adjacent but not identical
  contracts. `mcp_server/cli/repository_commands.py` advertises the exact
  bounded JSON surface for `.devcontainer/devcontainer.json`, and the current
  test corpus already covers same-file `.devcontainer/devcontainer.json`
  relapse handling plus later exact blockers. Repo inspection during planning
  did not show a dedicated current-head contract for the live paired handoff
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` across
  dispatcher, durable-trace, operator-status, and evidence surfaces.
- Semantic state remains fail-closed rather than hiding the lexical blocker:
  the current handoff still reports `Readiness: stale_commit`,
  `Rollout status: partial_index_failure`, `Last sync error: disk I/O error`,
  and `Semantic readiness: summaries_missing` after the refreshed rerun.

Practical planning boundary:

- SEMDEVCONTAINERPAIRTAIL may tighten the exact shell/JSON handoff between
  `.devcontainer/post_create.sh` and `.devcontainer/devcontainer.json`, the
  immediate lexical-to-closeout trace handoff after that pair, operator status
  wording for the active pair, the dogfood evidence artifact, and only the
  smallest file-local devcontainer edits proved necessary by tests.
- SEMDEVCONTAINERPAIRTAIL must stay narrow and evidence-driven. It must not
  reopen the cleared `ai_docs/prometheus_overview.md -> ai_docs/README.md`
  seam, broaden into arbitrary shell or JSON or repo-wide `.devcontainer/*`
  bypasses, or widen into unrelated semantic, integration, security, or
  compatibility work unless the refreshed rerun directly re-anchors there.

## Interface Freeze Gates

- [ ] IF-0-SEMDEVCONTAINERPAIRTAIL-1 - Exact devcontainer tail-pair advance
      contract: a refreshed repo-local `repository sync --force-full` on the
      post-SEMAIDOCREADMETAIL head no longer terminalizes with the durable
      lexical trace centered on
      `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json`; it
      either advances durably beyond that pair or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMDEVCONTAINERPAIRTAIL-2 - Exact bounded repair contract: any
      repair introduced by this phase remains limited to
      `.devcontainer/post_create.sh`, `.devcontainer/devcontainer.json`, or
      the immediate dispatcher or durable-trace handoff around that exact
      pair. The phase must not reopen the repaired
      `ai_docs/prometheus_overview.md -> ai_docs/README.md` seam or broaden to
      arbitrary shell, arbitrary JSON, or repo-wide devcontainer bypasses
      without direct evidence.
- [ ] IF-0-SEMDEVCONTAINERPAIRTAIL-3 - Discoverability and trace-truthfulness
      contract: both `.devcontainer` files remain lexically discoverable after
      the repair, and `force_full_exit_trace.json` plus `repository status`
      preserve the truthful active pair or the truthful newer blocker instead
      of regressing to a stale or misleading boundary report.
- [ ] IF-0-SEMDEVCONTAINERPAIRTAIL-4 - Evidence alignment contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMAIDOCREADMETAIL rerun outcome and the final live verdict for the
      exact `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json`
      pair.

## Lane Index & Dependencies

- SL-0 - Exact devcontainer tail-pair fixture freeze; Depends on: SEMAIDOCREADMETAIL; Blocks: SL-1, SL-2; Parallel-safe: no
- SL-1 - Exact devcontainer tail-pair repair or truthful blocker capture; Depends on: SL-0; Blocks: SL-2; Parallel-safe: no
- SL-2 - Operator-status and dogfood-evidence reducer; Depends on: SL-0, SL-1; Blocks: SEMDEVCONTAINERPAIRTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMAIDOCREADMETAIL
  -> SL-0 -> SL-1 -> SL-2 -> SEMDEVCONTAINERPAIRTAIL acceptance
```

## Lanes

### SL-0 - Exact Devcontainer Tail-Pair Fixture Freeze

- **Scope**: Freeze the exact
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` lexical
  seam in dispatcher and durable-trace coverage so this phase proves the live
  current-head blocker exactly instead of relying on older same-file
  devcontainer relapse fixtures or on the already-cleared `ai_docs` seam.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMDEVCONTAINERPAIRTAIL-1,
  IF-0-SEMDEVCONTAINERPAIRTAIL-2,
  and the trace-truthfulness half of IF-0-SEMDEVCONTAINERPAIRTAIL-3
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`,
  `GitAwareIndexManager._finalize_running_force_full_trace_as_interrupted(...)`,
  the current bounded `.devcontainer/devcontainer.json` path handling, and the
  SEMAIDOCREADMETAIL evidence captured in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    freezes the exact live handoff
    `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json`,
    verifies dispatcher progress snapshots preserve that pair, and fails if
    the active blocker silently falls back to the cleared
    `ai_docs/prometheus_overview.md -> ai_docs/README.md` seam.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the same exact pair through timeout or interrupted
    terminalization, including preserved `last_progress_path`,
    preserved `in_flight_path`, and negative assertions that older `ai_docs`
    markers or later unrelated blockers do not appear under this fixture.
  - test: Require explicit assertions that the exact pair still yields lexical
    discoverability instead of turning `.devcontainer/post_create.sh` or
    `.devcontainer/devcontainer.json` into untracked blind spots.
  - impl: Use synthetic dispatcher progress and synthetic durable-trace
    payloads rather than a live multi-minute rerun in unit coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate operator
    status wording, evidence docs, or the checked-in `.devcontainer` files
    here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "devcontainer or lexical or force_full or interrupted or handoff or trace"`

### SL-1 - Exact Devcontainer Tail-Pair Repair Or Truthful Blocker Capture

- **Scope**: Implement the smallest repair needed so the refreshed repo-local
  force-full rerun no longer burns its watchdog budget on the exact
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` pair, or
  otherwise records the real next blocker truthfully.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `.devcontainer/post_create.sh`, `.devcontainer/devcontainer.json`
- **Interfaces provided**: IF-0-SEMDEVCONTAINERPAIRTAIL-1 exact
  tail-pair advance contract; IF-0-SEMDEVCONTAINERPAIRTAIL-2 exact bounded
  repair contract; the discoverability half of
  IF-0-SEMDEVCONTAINERPAIRTAIL-3
- **Interfaces consumed**: SL-0 exact tail-pair fixtures; current bounded
  devcontainer path behavior; current lexical progress and
  `force_full_closeout_handoff` emission in the dispatcher; current durable
  `last_progress_path` and `in_flight_path` persistence in the git index
  manager; and the current checked-in content of the two `.devcontainer` files
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-manager slice first and confirm
    whether the active cost is concentrated in the exact shell-to-JSON
    handoff, in the post-lexical closeout transition immediately after the
    pair, or in the file-local devcontainer content itself.
  - impl: Choose one singular repair surface and keep it exact. Acceptable
    examples are an exact handoff optimization in dispatcher progress
    accounting, a durable-trace fix that preserves the truthful newer blocker
    after the pair clears, or the smallest file-local simplification to
    `.devcontainer/post_create.sh` or `.devcontainer/devcontainer.json` that
    lets the existing bounded behavior complete under the current watchdog.
  - impl: Only edit `.devcontainer/post_create.sh` or
    `.devcontainer/devcontainer.json` if tests prove the hotspot is file-local
    rather than already-matched path handling. Preserve the devcontainer's
    existing setup meaning and `postCreateCommand` contract.
  - impl: Keep lexical discoverability intact for both files. Do not turn this
    phase into a blanket `.devcontainer/*`, arbitrary `.sh`, or arbitrary
    `.json` bypass.
  - impl: If the rerun still cannot progress beyond the exact pair, prefer a
    truthful newer blocker or a truthful interrupted tail snapshot over
    another misleading report that reuses the cleared `ai_docs` seam.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "devcontainer or lexical or force_full or interrupted or handoff or trace"`
  - verify: `rg -n "devcontainer|post_create|force_full_closeout_handoff|last_progress_path|in_flight_path|interrupted|ai_docs/prometheus_overview|ai_docs/README" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/storage/git_index_manager.py tests/test_dispatcher.py tests/test_git_index_manager.py`

### SL-2 - Operator-Status And Dogfood-Evidence Reducer

- **Scope**: Keep the operator-facing status surface and the dogfood evidence
  document aligned with the repaired devcontainer pair so the current-head
  live verdict is explicit and does not regress to the older `ai_docs` seam.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/test_repository_commands.py`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMDEVCONTAINERPAIRTAIL-3 trace-truthfulness
  contract; IF-0-SEMDEVCONTAINERPAIRTAIL-4 evidence alignment contract
- **Interfaces consumed**: SL-0 exact tail-pair fixtures; SL-1 repair outcome;
  `_print_force_full_exit_trace(...)`; the current
  `_print_devcontainer_json_boundary(...)` status behavior; and the existing
  dogfood report structure around `SEMAIDOCREADMETAIL`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the active pair when `last_progress_path` is
    `.devcontainer/post_create.sh` and `in_flight_path` is
    `.devcontainer/devcontainer.json`, while preserving the existing exact
    bounded JSON surface for `.devcontainer/devcontainer.json` and avoiding a
    misleading reappearance of the cleared
    `ai_docs/prometheus_overview.md -> ai_docs/README.md` seam.
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence report requires the new phase plan reference and a
    `SEMDEVCONTAINERPAIRTAIL Live Rerun Check` section that records the
    SEMAIDOCREADMETAIL rerun outcome plus the final verdict for the exact
    `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` pair.
  - impl: Add only the smallest operator wording needed to make the exact
    live pair obvious when the trace references both files. Keep the existing
    exact `.devcontainer/devcontainer.json` boundary copy truthful and intact.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the refreshed
    force-full command, observed commit, trace timestamps, current
    `last_progress_path` and `in_flight_path`, terminalized status, SQLite
    counts, and the final live verdict for the repaired pair.
  - impl: If execution exposes a newer blocker after the pair clears, record
    that blocker truthfully in the evidence document instead of restating the
    cleared devcontainer seam.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "devcontainer or dogfood or boundary or SEMAIDOCREADMETAIL or SEMDEVCONTAINERPAIRTAIL"`
  - verify: `rg -n "SEMDEVCONTAINERPAIRTAIL|SEMAIDOCREADMETAIL|devcontainer/post_create.sh|devcontainer/devcontainer.json|prometheus_overview|ai_docs/README" mcp_server/cli/repository_commands.py docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py`

## Verification

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "devcontainer or lexical or force_full or interrupted or handoff or trace"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "devcontainer or dogfood or boundary or SEMAIDOCREADMETAIL or SEMDEVCONTAINERPAIRTAIL"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMAIDOCREADMETAIL
      head either advances durably beyond
      `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` or
      emits a truthful newer blocker before the 120-second watchdog expires.
- [ ] Any repair chosen for this later `.devcontainer` seam stays narrow,
      tested, and does not reopen the cleared
      `ai_docs/prometheus_overview.md -> ai_docs/README.md` seam without
      direct evidence.
- [ ] `.devcontainer/post_create.sh` and `.devcontainer/devcontainer.json`
      remain lexically discoverable after the repair and are not converted
      into indexing blind spots.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMAIDOCREADMETAIL rerun outcome and the final live verdict for the
      exact `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json`
      pair.
