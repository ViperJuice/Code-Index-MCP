# P34: Outside Developer Readiness & Public Alpha Recut

> Plan doc produced by `codex-plan-phase specs/phase-plans-v3.md P34` on 2026-04-23.
> Source roadmap `specs/phase-plans-v3.md` is clean in this worktree
> (`git status --short -- specs/phase-plans-v3.md` produced no output).

## Context

P34 is the release-readiness closeout for the v3 multi-repo blocker roadmap. It
should start only after P33 gates are green, because this phase must document the
corrected operating model rather than compensate for unresolved implementation
behavior.

The current release surface already includes several P21-P26 public-alpha guardrails:

- `tests/test_release_metadata.py` freezes `1.2.0-rc4` across package metadata,
  runtime metadata, README status, changelog, and release automation.
- `tests/docs/test_p23_doc_truth.py`, `tests/docs/test_p25_release_checklist.py`,
  and `tests/docs/test_p26_public_alpha_decision.py` guard active docs, release
  checklist language, and private-alpha decision links.
- `README.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`, and
  `docs/DOCKER_GUIDE.md` already mention beta status, MCP STDIO as primary, and
  the current container image, but they still need a single outside-developer v3
  model: many unrelated repos, one registered worktree per git common directory,
  tracked/default branch only, explicit readiness, and fail-closed fallback.
- `CLAUDE.md` currently contains unconditional MCP-first instructions that
  conflict with the v3 readiness contract and must be reconciled with
  `AGENTS.md`.

P34 should choose the next prerelease identifier once, update the version source
of truth and release surfaces consistently, and leave GA positioning out of scope.
The default recut target in this plan is `1.2.0-rc5` / `v1.2.0-rc5`; if the
release manager chooses a different prerelease tag before execution, update SL-0
first and let all downstream docs consume that single frozen value.

## Interface Freeze Gates

- [ ] IF-0-P34-1 - Public-alpha readiness contract: `README.md`,
      `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`,
      `docs/DOCKER_GUIDE.md`, `docs/operations/deployment-runbook.md`,
      `docs/operations/user-action-runbook.md`, `docs/SUPPORT_MATRIX.md`,
      `AGENTS.md`, and `CLAUDE.md` describe the same v3 model: many unrelated
      repositories on one machine, one registered worktree/path per git common
      directory, tracked/default branch indexing only, readiness must be `ready`
      before indexed MCP search is authoritative, and unavailable indexes return
      `index_unavailable` with `safe_fallback: "native_search"`.
- [ ] IF-0-P34-2 - Public-alpha checklist contract:
      `docs/operations/deployment-runbook.md` requires P27-P33 gates before
      public-alpha promotion, including the P33
      `make alpha-production-matrix` gate, clean-checkout wheel/container smoke,
      docs truth tests, release metadata tests, and the remaining limitations
      from IF-0-P34-1.
- [ ] IF-0-P34-3 - Agent handoff contract: `AGENTS.md` and `CLAUDE.md` tell
      agents to check `get_status` or honor tool readiness before using indexed
      MCP results; they state that `index_unavailable` plus
      `safe_fallback: "native_search"` means use native search or run the
      returned remediation, and they contain no unconditional "always use MCP
      before grep" guidance.
- [ ] IF-0-P34-4 - Changelog recut contract: `CHANGELOG.md` records the v3
      blocker fixes from P27-P33, the P34 docs/release recut, and the remaining
      limitations; it removes or corrects stale claims about unrestricted
      multi-worktree or multi-branch operation.
- [ ] IF-0-P34-5 - Version source-of-truth contract: `pyproject.toml`,
      `mcp_server/__init__.py`, `tests/test_release_metadata.py`, release
      automation defaults, README status, and support-matrix version references
      all agree on `1.2.0-rc5` and `v1.2.0-rc5`, and the release metadata test
      continues to prevent local tag reuse.
- [ ] IF-0-P34-6 - Clean-checkout release verification contract: the P34
      acceptance command set is `uv run pytest tests/smoke tests/docs
      tests/test_release_metadata.py tests/test_requirements_consolidation.py -v
      --no-cov`, `make alpha-production-matrix alpha-release-gates`, `make
      release-smoke release-smoke-container`, and the roadmap P34 `rg` truth
      sweep.

## Lane Index & Dependencies

- SL-0 - Version and P34 doc-test contract; Depends on: P33; Blocks: SL-1, SL-2, SL-3, SL-4, SL-5; Parallel-safe: no
- SL-1 - Outside-developer onboarding docs; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-2 - MCP and container configuration docs; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-3 - Operator checklist and support limits; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-4 - Agent handoff docs; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-5 - Changelog and final release-surface synthesis; Depends on: SL-1, SL-2, SL-3, SL-4; Blocks: P34 acceptance; Parallel-safe: no

Lane DAG:

```text
P33
  -> SL-0
       -> SL-1 --.
       -> SL-2 --.
       -> SL-3 ----> SL-5 -> P34 acceptance
       -> SL-4 --'
```

## Lanes

### SL-0 - Version And P34 Doc-Test Contract

- **Scope**: Freeze the public-alpha recut identifier and add focused tests that
  make the P34 documentation contract executable before editing the docs.
- **Owned files**: `pyproject.toml`, `mcp_server/__init__.py`,
  `tests/test_release_metadata.py`, `tests/docs/test_p34_public_alpha_recut.py`,
  `.github/workflows/release-automation.yml`
- **Interfaces provided**: `PUBLIC_ALPHA_VERSION = "1.2.0-rc5"` /
  `PUBLIC_ALPHA_TAG = "v1.2.0-rc5"` via `tests/test_release_metadata.py`;
  IF-0-P34-1, IF-0-P34-2, IF-0-P34-3, and IF-0-P34-5 executable doc assertions
- **Interfaces consumed**: P33 `make alpha-production-matrix` gate and CI naming;
  existing P21 release metadata contract; existing P23/P25/P26 docs-test style
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_p34_public_alpha_recut.py` with table-driven
    assertions for the v3 operating model, unsupported same-repo worktree
    language, tracked branch only, readiness states, `index_unavailable`,
    `safe_fallback`, `native_search`, and absence of unrestricted
    multi-worktree/multi-branch claims across all P34 public surfaces.
  - test: Extend `tests/test_release_metadata.py` to expect `1.2.0-rc5` /
    `v1.2.0-rc5` across runtime metadata, package metadata, README, changelog,
    and release automation.
  - impl: Update `pyproject.toml`, `mcp_server/__init__.py`, and
    `.github/workflows/release-automation.yml` to use the chosen prerelease
    identifier consistently.
  - impl: Keep the release workflow's "No automatic documentation rewrite"
    guard intact; P34 updates docs explicitly.
  - verify: `uv run pytest tests/test_release_metadata.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov`

### SL-1 - Outside-Developer Onboarding Docs

- **Scope**: Update the primary outside-developer docs so a new user sees the
  supported v3 model before setup commands or feature claims.
- **Owned files**: `README.md`, `docs/GETTING_STARTED.md`
- **Interfaces provided**: README and getting-started statements for IF-0-P34-1;
  public-alpha installation and first-use flow for `1.2.0-rc5`
- **Interfaces consumed**: SL-0 `PUBLIC_ALPHA_VERSION`; SL-0 P34 doc-test
  contract; P27 readiness states; P28 readiness-aware tool guidance; P30
  tracked-branch contract; P33 production matrix gate
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use `tests/docs/test_p34_public_alpha_recut.py` to drive the required
    README and getting-started language before editing prose.
  - impl: Update project status, quick start, and "Using Against Many Repos" in
    `README.md` to state that public alpha supports many unrelated repositories,
    one registered worktree per repo, tracked/default branch indexing, and
    fail-closed readiness.
  - impl: Update `docs/GETTING_STARTED.md` to show the STDIO-first flow:
    configure `MCP_ALLOWED_ROOTS`, register repos, inspect readiness with
    `mcp-index repository list -v` or `get_status`, and only trust indexed MCP
    results when readiness is `ready`.
  - impl: Remove or qualify any phrasing that implies unrestricted multi-branch
    or same-repo multi-worktree support.
  - verify: `uv run pytest tests/docs/test_p34_public_alpha_recut.py tests/docs/test_p23_doc_truth.py tests/docs/test_p26_public_alpha_decision.py -v --no-cov`

### SL-2 - MCP And Container Configuration Docs

- **Scope**: Make configuration and Docker docs show the same repository
  boundary, readiness, and fallback semantics as the onboarding docs.
- **Owned files**: `docs/MCP_CONFIGURATION.md`, `docs/DOCKER_GUIDE.md`
- **Interfaces provided**: MCP configuration and Docker setup statements for
  IF-0-P34-1; container guidance for `MCP_ALLOWED_ROOTS`, repo registration, and
  readiness inspection
- **Interfaces consumed**: SL-0 `PUBLIC_ALPHA_VERSION`; SL-0 P34 doc-test
  contract; P27 path sandbox and unsupported-worktree errors; P28
  `index_unavailable` fallback; current image package
  `ghcr.io/viperjuice/code-index-mcp`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend the P34 doc-test table to cover `docs/MCP_CONFIGURATION.md`
    and `docs/DOCKER_GUIDE.md`, including image tag, readiness, tracked branch,
    and same-repo worktree limitations.
  - impl: Replace the current "multiple servers" multi-repo example in
    `docs/MCP_CONFIGURATION.md` with the v3 supported model or clearly label it
    as separate server instances, not one shared multi-worktree index.
  - impl: Add Docker examples that set `MCP_ALLOWED_ROOTS`, mount unrelated repo
    roots deliberately, register each repo, and inspect readiness before MCP
    tool use.
  - impl: Keep semantic search and artifact sync documented as optional features
    behind provider credentials and support-matrix limitations.
  - verify: `uv run pytest tests/docs/test_p34_public_alpha_recut.py tests/docs/test_p23_doc_truth.py -v --no-cov`

### SL-3 - Operator Checklist And Support Limits

- **Scope**: Update operator-facing release checklists and support limits so the
  public-alpha decision is gated by P27-P33 and remaining limitations are
  explicit.
- **Owned files**: `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`, `docs/SUPPORT_MATRIX.md`
- **Interfaces provided**: IF-0-P34-2 checklist; support-matrix operating-model
  limitations; operator actions for P27-P34 public-alpha recut
- **Interfaces consumed**: SL-0 `PUBLIC_ALPHA_VERSION`; SL-0 P34 doc-test
  contract; P33 `Alpha Gate - Production Multi-Repo Matrix`; P27-P33 exit
  criteria and verification commands
- **Parallel-safe**: yes
- **Tasks**:
  - test: Update or add docs tests so the deployment runbook requires P27-P33
    gates, `make alpha-production-matrix`, clean-checkout release smoke,
    release metadata, docs truth, and explicit documented limitations before
    public-alpha promotion.
  - impl: Extend `docs/operations/deployment-runbook.md` with a P34 recut
    checklist that names the required commands and blocks release when P33 or
    P34 documentation truth checks fail.
  - impl: Add a P27-P34 section to `docs/operations/user-action-runbook.md`
    covering release-manager actions: confirm P33 green, choose the prerelease
    tag, check tag reuse, review public limitation disclosures, run clean
    checkout smoke, and keep raw/local evidence out of git.
  - impl: Update `docs/SUPPORT_MATRIX.md` to distinguish language/runtime
    support from repository-topology support and to state the v3 repo topology
    limitations near the top.
  - verify: `uv run pytest tests/docs/test_p25_release_checklist.py tests/docs/test_p34_public_alpha_recut.py tests/docs/test_p23_doc_truth.py -v --no-cov`

### SL-4 - Agent Handoff Docs

- **Scope**: Align AI-agent guidance with readiness-aware indexed search so
  models do not treat unavailable indexes as authoritative.
- **Owned files**: `AGENTS.md`, `CLAUDE.md`
- **Interfaces provided**: IF-0-P34-3 agent handoff contract; readiness-aware
  MCP search strategy for outside developers and in-repo agents
- **Interfaces consumed**: SL-0 P34 doc-test contract; P28 model handoff
  contract; P27 readiness response schema
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `tests/docs/test_p34_public_alpha_recut.py` to assert that
    `AGENTS.md` and `CLAUDE.md` contain readiness-aware search guidance and do
    not contain unconditional MCP-first wording.
  - impl: Keep `AGENTS.md` as the source of detailed agent instructions and
    ensure its MCP search strategy says to check readiness first or honor
    `index_unavailable`.
  - impl: Reduce `CLAUDE.md` to a pointer-only or readiness-aware handoff; remove
    the stale "Always search with MCP tools before using Grep or Glob" section if
    it cannot be made consistent with P28.
  - impl: Preserve the existing `uv sync --locked` and support-matrix pointers.
  - verify: `uv run pytest tests/docs/test_p28_agents_handoff.py tests/docs/test_p34_public_alpha_recut.py tests/test_requirements_consolidation.py -v --no-cov`

### SL-5 - Changelog And Final Release-Surface Synthesis

- **Scope**: Write the final changelog section and run a cross-surface sweep
  after all public docs have converged on the same v3 model.
- **Owned files**: `CHANGELOG.md`, `tests/test_release_notes.py`
- **Interfaces provided**: IF-0-P34-4 changelog recut; final P34 release-surface
  summary for public alpha
- **Interfaces consumed**: SL-1 onboarding statements; SL-2 configuration and
  Docker statements; SL-3 operator checklist and support limits; SL-4 agent
  handoff wording; SL-0 `PUBLIC_ALPHA_VERSION`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/test_release_notes.py` as needed so it accepts the new
    recut changelog section while preserving historical release-note checks.
  - impl: Add the `1.2.0-rc5` changelog section with grouped entries for P27-P33
    blocker fixes, P34 public-alpha docs/release cleanup, and remaining
    limitations.
  - impl: Ensure `CHANGELOG.md` no longer implies unrestricted same-repo
    multi-worktree or multi-branch support and links to the support matrix,
    deployment runbook, and private-alpha decision where appropriate.
  - verify: `uv run pytest tests/test_release_notes.py tests/test_release_metadata.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov`
  - verify: `rg -n "multiple worktree|tracked branch|index readiness|public alpha|support matrix|rollback" README.md CHANGELOG.md docs AGENTS.md CLAUDE.md`

## Verification

Lane-specific verification:

```bash
uv run pytest tests/test_release_metadata.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov
uv run pytest tests/docs/test_p34_public_alpha_recut.py tests/docs/test_p23_doc_truth.py tests/docs/test_p26_public_alpha_decision.py -v --no-cov
uv run pytest tests/docs/test_p25_release_checklist.py tests/docs/test_p34_public_alpha_recut.py tests/docs/test_p23_doc_truth.py -v --no-cov
uv run pytest tests/docs/test_p28_agents_handoff.py tests/docs/test_p34_public_alpha_recut.py tests/test_requirements_consolidation.py -v --no-cov
uv run pytest tests/test_release_notes.py tests/test_release_metadata.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov
```

Whole-phase regression commands:

```bash
uv run pytest tests/smoke tests/docs tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
make alpha-production-matrix alpha-release-gates
make release-smoke release-smoke-container
rg -n "multiple worktree|tracked branch|index readiness|public alpha|support matrix|rollback" \
  README.md CHANGELOG.md docs AGENTS.md CLAUDE.md
```

Clean-checkout release verification:

```bash
uv sync --locked
uv run pytest tests/smoke tests/docs tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
make alpha-production-matrix alpha-release-gates release-smoke release-smoke-container
git tag -l v1.2.0-rc5
```

P34 planning does not execute these commands. Run them during implementation and
again from a clean checkout before public-alpha promotion.

## Acceptance Criteria

- [ ] P33 gates are green before P34 implementation starts.
- [ ] `pyproject.toml`, `mcp_server/__init__.py`,
      `.github/workflows/release-automation.yml`, README status,
      `docs/SUPPORT_MATRIX.md`, `tests/test_release_metadata.py`, and
      `CHANGELOG.md` agree on the selected recut identifier.
- [ ] README, GETTING_STARTED, MCP configuration docs, Docker docs, deployment
      runbook, user-action runbook, support matrix, AGENTS, and CLAUDE describe
      the supported v3 model: many unrelated repos, one worktree per repo,
      tracked/default branch only, and fail-closed index readiness.
- [ ] Agent guidance no longer tells models to use indexed MCP search
      unconditionally; it requires readiness `ready` or directs fallback to
      native search/remediation on `index_unavailable`.
- [ ] Changelog records the v3 blocker fixes and removes stale claims about
      unrestricted multi-worktree or multi-branch operation.
- [ ] Public-alpha checklist requires P27-P33 gates, P34 docs truth, clean
      checkout wheel/container smoke, and release metadata checks.
- [ ] Container/wheel smoke, production matrix gates, docs tests, release
      metadata tests, and requirements-consolidation tests pass from a clean
      checkout.
