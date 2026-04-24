---
phase_loop_plan_version: 1
phase: GAE2E
roadmap: specs/phase-plans-v5.md
roadmap_sha256: cad74cc0a8ba6c41a82c9efa5b014bc689c5127f25564b3ff3c0f6de0031c130
---
# GAE2E: GA End-to-End Evidence

## Context

GAE2E is the fourth phase in the v5 GA-hardening roadmap. It depends on
GABASE and GASUPPORT, both of which are already marked complete in
`.codex/phase-loop/state.json`, and it should convert those frozen contracts
into fresh evidence across the actual release surfaces: wheel/native install,
STDIO, Docker, multi-repo indexing, readiness failure modes, and artifact
identity.

Current repo state gathered during planning:

- The checkout is on `main` at `8d08545`.
- `specs/phase-plans-v5.md` is already staged in this worktree
  (`git status --short -- specs/phase-plans-v5.md` returned
  `A  specs/phase-plans-v5.md`), so it must be treated as the user-owned
  roadmap baseline.
- The current roadmap bytes hash to
  `cad74cc0a8ba6c41a82c9efa5b014bc689c5127f25564b3ff3c0f6de0031c130`,
  which differs from the older staged v5 plan frontmatter hash
  (`6c3ef37e...`); this plan must therefore freeze against the current roadmap
  bytes instead of copying older plan metadata forward.
- `.codex/phase-loop/state.json` already sets `current_phase` to `GAE2E` and
  marks `GAE2E` as `unplanned`, so this artifact should hand directly to
  `codex-execute-phase`.
- `docs/validation/ga-readiness-checklist.md`,
  `docs/SUPPORT_MATRIX.md`, and `docs/validation/ga-governance-evidence.md`
  now exist and should be consumed as frozen upstream contracts rather than
  rewritten here.
- `docs/validation/ga-e2e-evidence.md` does not exist yet and is the canonical
  new artifact required by this phase.
- Fresh-install and release-surface smoke infrastructure already exists in
  `scripts/release_smoke.py`, `tests/smoke/test_release_smoke_contract.py`,
  `Makefile`, and the Docker installer helpers, but it is still oriented around
  the RC/public-alpha release contract and needs a phase-specific GAE2E freeze.
- Fresh-repository and readiness/failure coverage already exists across
  `tests/smoke/test_secondary_tool_readiness_smoke.py`,
  `tests/test_multi_repo_production_matrix.py`,
  `tests/test_multi_repo_failure_matrix.py`,
  `tests/test_tool_readiness_fail_closed.py`,
  `tests/test_repository_readiness.py`, and
  `tests/test_git_index_manager.py`; GAE2E should extend these fixtures instead
  of creating a parallel harness.
- Artifact-identity checks currently live in `tests/test_release_metadata.py`,
  while helper/install surfaces live in `scripts/install-mcp-docker.sh`,
  `scripts/install-mcp-docker.ps1`, and `scripts/download-release.py`; this
  phase should reconcile those identities with the frozen `v1.2.0-rc5`
  baseline and the roadmap's requirement to record package, wheel, sdist, GHCR
  image, and release metadata explicitly.

## Interface Freeze Gates

- [ ] IF-0-GAE2E-1 - Release-surface smoke contract:
      `scripts/release_smoke.py`, `tests/smoke/test_release_smoke_contract.py`,
      `Makefile`, and the installer helpers define one reproducible command
      set for clean wheel/native install, STDIO smoke, and Docker build/run
      smoke without dispatching a release.
- [ ] IF-0-GAE2E-2 - Fresh repository durability contract:
      fresh registered-repository flows prove `register -> reindex ->
      search_code -> symbol_lookup -> summarize_sample` on clean fixtures and
      verify durable SQLite rows plus `ready` readiness vocabulary.
- [ ] IF-0-GAE2E-3 - Fail-closed readiness matrix contract:
      unsupported worktree, wrong branch, stale commit, missing index,
      unregistered repository, allowed-roots violation, and conflicting
      path/repository inputs all return the exact frozen fail-closed codes and
      prevent unintended mutation or summarization.
- [ ] IF-0-GAE2E-4 - Artifact identity contract:
      tests and helper scripts agree on exact package, version, wheel, sdist,
      GHCR image, image tags, and release-metadata expectations for the active
      RC/public-alpha baseline and any local GAE2E smoke artifacts.
- [ ] IF-0-GAE2E-5 - Redacted evidence contract:
      `docs/validation/ga-e2e-evidence.md` records commands, timestamps,
      commit, artifact identities, and metadata-only probes while preserving
      GABASE product-level posture (`public-alpha`/`beta`/`GA`) and GASUPPORT
      row-level support tiers without collapsing those vocabularies again.

## Lane Index & Dependencies

- SL-0 - GAE2E contract tests; Depends on: GABASE, GASUPPORT; Blocks: SL-1, SL-2, SL-3, SL-4, SL-5; Parallel-safe: no
- SL-1 - Fresh install and container smoke hardening; Depends on: SL-0; Blocks: SL-4, SL-5; Parallel-safe: yes
- SL-2 - Fresh repository durability matrix; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-3 - Fail-closed readiness matrix; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-4 - Artifact identity and installer parity; Depends on: SL-0, SL-1; Blocks: SL-5; Parallel-safe: yes
- SL-5 - GA E2E evidence reducer; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4; Blocks: GAE2E acceptance; Parallel-safe: no

## Lanes

### SL-0 - GAE2E Contract Tests

- **Scope**: Freeze the GAE2E evidence shape, smoke entrypoints, failure-mode
  rows, and artifact-identity requirements before changing helpers or evidence
  docs.
- **Owned files**: `tests/docs/test_gae2e_evidence_contract.py`
- **Interfaces provided**: IF-0-GAE2E-1, IF-0-GAE2E-2, IF-0-GAE2E-3,
  IF-0-GAE2E-4, IF-0-GAE2E-5
- **Interfaces consumed**: `docs/validation/ga-readiness-checklist.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/validation/ga-governance-evidence.md`,
  `scripts/release_smoke.py`, `tests/smoke/test_release_smoke_contract.py`,
  `tests/smoke/test_secondary_tool_readiness_smoke.py`,
  `tests/test_multi_repo_production_matrix.py`,
  `tests/test_multi_repo_failure_matrix.py`,
  `tests/test_tool_readiness_fail_closed.py`,
  `tests/test_repository_readiness.py`, `tests/test_git_index_manager.py`,
  `tests/test_release_metadata.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a dedicated GAE2E contract test that requires a canonical
    `docs/validation/ga-e2e-evidence.md` artifact and asserts that it records
    release-surface smoke, fresh repo durability, fail-closed matrix results,
    artifact identities, timestamps, commit, and redacted metadata only.
  - test: Assert that the evidence artifact references the GABASE checklist and
    GASUPPORT support tiers instead of inventing replacement vocabulary.
  - test: Assert that the planned smoke and matrix coverage names the exact
    readiness codes and artifact identities that downstream GAOPS/GARC/GAREL
    will consume.
  - impl: Keep this file additive and phase-specific so P22, P27, P33, GABASE,
    GAGOV, and GASUPPORT tests remain lower-level supporting contracts.
  - verify: `uv run pytest tests/docs/test_gae2e_evidence_contract.py -v --no-cov`

### SL-1 - Fresh Install And Container Smoke Hardening

- **Scope**: Make the clean-install, STDIO, and Docker smoke entrypoints
  reproducible enough to serve as GAE2E evidence rather than ad hoc release
  checks.
- **Owned files**: `scripts/release_smoke.py`,
  `tests/smoke/test_release_smoke_contract.py`, `Makefile`
- **Interfaces provided**: IF-0-GAE2E-1
- **Interfaces consumed**: SL-0 assertions; `pyproject.toml`;
  `.github/workflows/release-automation.yml`,
  `.github/workflows/container-registry.yml`, current `mcp_server.__version__`,
  current `index-it-mcp` wheel naming, and the documented
  `ghcr.io/viperjuice/code-index-mcp` image contract
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend the release-smoke contract to fail first when wheel/native
    install, STDIO smoke, container build/run smoke, or Makefile targets drift
    from the exact GAE2E command set.
  - impl: Keep `scripts/release_smoke.py` fresh-environment oriented:
    isolated wheel build/install, local STDIO ready/fallback smoke, and Docker
    contract smoke should all run without release mutation.
  - impl: If image-tag handling or target naming is still ambiguous, freeze it
    in the script and Makefile so downstream evidence does not depend on
    operator interpretation.
  - impl: Preserve the current RC/public-alpha release state; this lane may
    build or run local smoke artifacts, but it must not publish or retag them.
  - verify: `uv run pytest tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `make release-smoke`
  - verify: `make release-smoke-container`

### SL-2 - Fresh Repository Durability Matrix

- **Scope**: Prove the happy-path repository flows from clean fixtures, with
  durable SQLite persistence and ready-state vocabulary across the primary tool
  surface.
- **Owned files**: `tests/smoke/test_secondary_tool_readiness_smoke.py`,
  `tests/test_multi_repo_production_matrix.py`,
  `tests/integration/test_multi_repo_server.py`
- **Interfaces provided**: IF-0-GAE2E-2
- **Interfaces consumed**: SL-0 assertions; `tests.fixtures.multi_repo`;
  `boot_test_server`, `build_temp_repo`, `build_production_matrix`,
  `tool_handlers.handle_summarize_sample`, dispatcher/store-registry durable
  row behavior, and the frozen readiness vocabulary from GABASE/GASUPPORT
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend the fresh-fixture smokes so a clean registered repo proves
    `reindex`, `search_code`, `symbol_lookup`, and `summarize_sample` on the
    primary surface with durable SQLite evidence.
  - test: Keep unrelated repositories isolated while proving happy-path repair
    after reindex, watcher-style changes, and explicit repository scoping.
  - impl: Reuse the existing multi-repo fixtures and helper server instead of
    introducing a second end-to-end harness.
  - impl: Ensure happy-path summarization coverage only runs on ready,
    registered repos so the evidence distinguishes success-path behavior from
    the fail-closed refusals owned by SL-3.
  - verify: `uv run pytest tests/smoke/test_secondary_tool_readiness_smoke.py -v --no-cov`
  - verify: `uv run pytest tests/test_multi_repo_production_matrix.py tests/integration/test_multi_repo_server.py -v --no-cov`

### SL-3 - Fail-Closed Readiness Matrix

- **Scope**: Freeze the non-ready and out-of-contract behaviors so GAE2E
  evidence proves failure modes explicitly instead of inferring them from empty
  search results or manual notes.
- **Owned files**: `tests/test_multi_repo_failure_matrix.py`,
  `tests/test_tool_readiness_fail_closed.py`,
  `tests/test_repository_readiness.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: IF-0-GAE2E-3
- **Interfaces consumed**: SL-0 assertions; `ReadinessClassifier`,
  `RepositoryReadinessState`, `GitAwareIndexManager`,
  `should_reindex_for_branch`, readiness-refusal payload shape, and path
  sandbox / conflicting-path precedence behavior
- **Parallel-safe**: yes
- **Tasks**:
  - test: Require exact fail-closed codes and payload fields for
    `unsupported_worktree`, `wrong_branch`, `stale_commit`, `missing_index`,
    `unregistered_repository`, `path_outside_allowed_roots`, and
    `conflicting_path_and_repository`.
  - test: Assert that secondary tools do not mutate SQLite state or invoke the
    summarizer when readiness is non-ready or scope validation fails earlier.
  - test: Assert that wrong-branch and missing-index paths do not silently
    incremental-sync, return empty success payloads, or widen fallback
    semantics beyond the frozen contract.
  - impl: Keep the readiness vocabulary aligned with the classifier and support
    matrix; do not introduce new fallback labels or best-effort mutation paths
    in this phase.
  - verify: `uv run pytest tests/test_multi_repo_failure_matrix.py tests/test_tool_readiness_fail_closed.py -v --no-cov`
  - verify: `uv run pytest tests/test_repository_readiness.py tests/test_git_index_manager.py -v --no-cov`

### SL-4 - Artifact Identity And Installer Parity

- **Scope**: Align versioned helper surfaces and release-metadata checks with
  the exact artifact identities that GAE2E evidence must record.
- **Owned files**: `tests/test_release_metadata.py`,
  `scripts/install-mcp-docker.sh`, `scripts/install-mcp-docker.ps1`,
  `scripts/download-release.py`
- **Interfaces provided**: IF-0-GAE2E-4
- **Interfaces consumed**: SL-0 assertions; SL-1 smoke entrypoint and image
  policy; `pyproject.toml`; `mcp_server.__version__`;
  `.github/workflows/release-automation.yml`; current package name
  `index-it-mcp`; current tag `v1.2.0-rc5`; current image
  `ghcr.io/viperjuice/code-index-mcp`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend release-metadata assertions so package name, console scripts,
    version, tag, and image expectations are frozen alongside helper-script
    defaults and selectable smoke variants.
  - test: Fail if installer or download helpers reference retired image names,
    impossible tag defaults, or legacy artifact assumptions that do not match
    the wheel/sdist/GHCR/release-metadata contract actually documented now.
  - impl: Align the shell, PowerShell, and download helpers with the current
    artifact identity contract without mutating live release state or implying
    a GA release.
  - impl: Keep any networked or credentialed release checks metadata-only;
    artifact publication and final channel decisions remain out of scope for
    GAE2E.
  - verify: `uv run pytest tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n "index-it-mcp|v1\\.2\\.0-rc5|local-smoke|latest|ghcr\\.io/viperjuice/code-index-mcp|code-index-" scripts/install-mcp-docker.sh scripts/install-mcp-docker.ps1 scripts/download-release.py tests/test_release_metadata.py`

### SL-5 - GA E2E Evidence Reducer

- **Scope**: Reduce the frozen command set, fresh repo results, failure-matrix
  rows, and artifact-identity outputs into the canonical GAE2E evidence
  artifact.
- **Owned files**: `docs/validation/ga-e2e-evidence.md`
- **Interfaces provided**: IF-0-GAE2E-5; canonical GAE2E evidence for GAOPS,
  GARC, and GAREL
- **Interfaces consumed**: SL-0 GAE2E assertions; SL-1 smoke commands/results;
  SL-2 fresh-repo durability results; SL-3 fail-closed matrix results;
  SL-4 artifact identities; `docs/validation/ga-readiness-checklist.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/validation/ga-governance-evidence.md`,
  `docs/validation/rc5-release-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Write `docs/validation/ga-e2e-evidence.md` only after SL-1 through
    SL-4 settle the final command set, result rows, and artifact identities.
  - impl: Record commands, timestamps, commit, fixture/environment notes,
    SQLite persistence proof, failure-matrix rows, package/wheel/sdist/GHCR
    identities, and any metadata-only CLI probes needed to explain release
    surfaces.
  - impl: Preserve the distinction between GABASE product-level posture and
    GASUPPORT row-level support tiers so the evidence does not collapse the two
    vocabularies again.
  - impl: Use the same historical-artifact posture as the other
    `docs/validation/` evidence files when the evidence is point-in-time and
    should not be mistaken for a perpetual current-state claim.
  - verify: `uv run pytest tests/docs/test_gae2e_evidence_contract.py tests/smoke/test_release_smoke_contract.py tests/smoke/test_secondary_tool_readiness_smoke.py tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n "Commit:|Timestamp:|Wheel|sdist|GHCR|safe_fallback|unsupported_worktree|wrong_branch|stale_commit|missing_index|path_outside_allowed_roots|redacted" docs/validation/ga-e2e-evidence.md`

## Verification

- `uv run pytest tests/docs/test_gae2e_evidence_contract.py -v --no-cov`
- `uv run pytest tests/smoke/test_release_smoke_contract.py tests/smoke/test_secondary_tool_readiness_smoke.py -v --no-cov`
- `uv run pytest tests/test_multi_repo_production_matrix.py tests/integration/test_multi_repo_server.py tests/test_multi_repo_failure_matrix.py tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py -v --no-cov`
- `uv run pytest tests/test_release_metadata.py -v --no-cov`
- `make release-smoke`
- `make release-smoke-container`
- `uv run pytest tests/docs/test_gae2e_evidence_contract.py tests/smoke/test_release_smoke_contract.py tests/smoke/test_secondary_tool_readiness_smoke.py tests/test_multi_repo_production_matrix.py tests/integration/test_multi_repo_server.py tests/test_multi_repo_failure_matrix.py tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py tests/test_release_metadata.py -v --no-cov`
- `git status --short -- docs/validation/ga-e2e-evidence.md scripts/release_smoke.py scripts/install-mcp-docker.sh scripts/install-mcp-docker.ps1 scripts/download-release.py Makefile tests/docs/test_gae2e_evidence_contract.py tests/smoke/test_release_smoke_contract.py tests/smoke/test_secondary_tool_readiness_smoke.py tests/test_multi_repo_production_matrix.py tests/integration/test_multi_repo_server.py tests/test_multi_repo_failure_matrix.py tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py tests/test_release_metadata.py`

## Acceptance Criteria

- [ ] Clean wheel/native install and STDIO smoke pass from a fresh checkout or
      isolated environment using the frozen GAE2E command set.
- [ ] Docker build/run smoke covers the exact GAE2E candidate image/tag policy
      without publishing or retagging a release.
- [ ] Fresh repository register/reindex/search/symbol/summarize flows persist
      durable SQLite rows and return the expected `ready` readiness vocabulary.
- [ ] Multi-repo isolation, wrong-branch, unsupported-worktree, stale/missing
      index, allowed-roots, and conflicting-path failure modes all pass with
      the exact fail-closed contracts and without unintended mutation.
- [ ] Artifact identity checks cover the expected package, wheel, sdist, GHCR
      image, and release-metadata surfaces for the current RC/public-alpha
      baseline.
- [ ] `docs/validation/ga-e2e-evidence.md` exists as the canonical redacted
      GAE2E artifact and records commands, timestamps, commit, and artifact
      identities for downstream GA phases.

## Automation

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gae2e.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gae2e.md
  artifact_state: staged
```
