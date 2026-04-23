# Phase roadmap v4

## Context

The v3 roadmap is complete through P34. P27-P33 removed the technical blockers for the
public-alpha multi-repo contract, and P34 recut the outside-developer release surface for
`v1.2.0-rc5`.

The release-readiness review found no blocker in the primary `search_code` /
`symbol_lookup` contract, and the current P34 commit has passed the important local and
GitHub gates. The remaining work is release-management cleanup and post-alpha hardening:

- release automation does not run every check named by the P34 runbook;
- Docker installer scripts still offer `v1.2.0-rc4`;
- branch protection does not enforce the CI gates operators call required;
- GitHub release channel state is confusing because a newer `v2.15.0-alpha.1` release is
  marked latest while the active package contract is `v1.2.0-rc5`;
- secondary tools such as `reindex`, `write_summaries`, and `summarize_sample` are not as
  readiness-gated as the primary query tools.

This roadmap starts after v3. It must not add a P35 to `specs/phase-plans-v3.md`.

## Architecture North Star

The release process should be boring and auditable. A public-alpha operator should be able
to cut `v1.2.0-rc5`, watch named gates, and decide whether to announce or roll back without
remembering review-only caveats.

For post-alpha hardening, every MCP tool that reads or mutates indexed repository state
should share the same readiness vocabulary. The primary model-facing query path remains
the release-critical surface, but secondary tools should not silently fall back to global
or wrong-repository state when a repository target is unavailable.

## Assumptions

- `v1.2.0-rc5` remains the active public-alpha release identifier for this cleanup track.
- The v3 operating model remains unchanged: many unrelated repositories, one registered
  worktree per git common directory, tracked/default branch only, and fail-closed indexed
  search when readiness is not `ready`.
- The next release may proceed before GA-grade secondary-tool hardening if the pre-release
  gate and installer cleanup is completed.
- GitHub Actions remains the release automation surface.
- STDIO remains the primary LLM tool surface.

## Non-Goals

- No new multi-worktree or multi-branch support.
- No support-matrix expansion.
- No new artifact backend.
- No marketing-site work.
- No rewrite of the completed v3 roadmap.

## Cross-Cutting Principles

- Keep v3 release cleanup separate from future GA product hardening.
- Make automated release gates match the runbook, or make any manual exception explicit.
- Prefer one readiness helper and one response vocabulary across tools.
- Do not treat GitHub UI state as policy unless it is documented and verified.
- Keep public docs, installer scripts, release metadata, and operator checklists in sync.

## Top Interface-Freeze Gates

- IF-0-GATEPARITY-1 - Release gate parity contract: every check the public-alpha runbook
  names as release-blocking is either wired into `alpha-release-gates` / release
  automation or explicitly documented as a manual pre-dispatch check.
- IF-0-RC5REL-1 - RC5 release evidence contract: the `v1.2.0-rc5` tag/release flow records
  the exact commit, GitHub workflow runs, PyPI artifact, GHCR image tags, and rollback
  disposition.
- IF-0-RELGOV-1 - Release governance contract: required gates, branch-protection or
  ruleset behavior, prerelease/latest semantics, and the `v2.x` vs `v1.2.0-rc5` channel
  decision are documented before auto-merge or GA claims.
- IF-0-TOOLRDY-1 - Secondary tool readiness contract: repository-scoped secondary tools
  fail closed or require explicit path scope instead of using stale, unsupported, or
  wrong-repository state.
- IF-0-GACLOSE-1 - GA evidence contract: public docs, installer flows, release gates, and
  end-to-end indexing evidence are sufficient to decide whether to start GA promotion.

## Phases

### Phase 1 — Release Gate Parity & RC5 Surface Cleanup (GATEPARITY)

**Objective**

Make the quick pre-release cleanup from the review concrete: align automation with the
P34 runbook, update the RC5 installer surface, and close stale public-alpha checklist gaps.

**Exit criteria**
- [ ] `alpha-release-gates` or release automation runs the P34 public-alpha recut docs
      contract and container smoke, or the runbook names those checks as mandatory manual
      pre-dispatch commands.
- [ ] `tests/docs/test_p25_release_checklist.py` requires the P33 production multi-repo
      matrix gate wherever the public-alpha required gate list is asserted.
- [ ] Shell and PowerShell Docker installer scripts offer `v1.2.0-rc5` as the release
      candidate image.
- [ ] User-facing docs that still point to `v1.2.0-rc4` are either updated to RC5 or
      explicitly marked historical/non-current.
- [ ] P34 release-truth tests, production matrix, wheel smoke, and container smoke pass
      from a clean checkout.

**Scope notes**

This is intentionally small and should be safe to do before the RC5 tag. It should not
reopen the v3 technical implementation.

**Non-goals**

- No GitHub branch-protection/ruleset changes.
- No changes to release channel policy beyond removing obvious RC4 drift.
- No secondary-tool readiness refactor.

**Key files**

- `Makefile`
- `.github/workflows/release-automation.yml`
- `.github/workflows/container-registry.yml`
- `tests/docs/test_p25_release_checklist.py`
- `tests/docs/test_p34_public_alpha_recut.py`
- `tests/smoke/test_release_smoke_contract.py`
- `scripts/install-mcp-docker.sh`
- `scripts/install-mcp-docker.ps1`
- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `docs/DEPLOYMENT-GUIDE.md`
- `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`

**Depends on**
- P34

**Produces**
- IF-0-GATEPARITY-1 - Release gate parity contract.

### Phase 2 — RC5 Release Execution & Observation (RC5REL)

**Objective**

Execute the public-alpha `v1.2.0-rc5` release/tag flow and capture the release evidence
needed to decide whether the RC is usable for outside-developer validation.

**Exit criteria**
- [ ] Local pre-dispatch checks confirm a clean worktree, `main == origin/main`, and no
      reused local or remote `v1.2.0-rc5` tag.
- [ ] Release Automation is dispatched with `version=v1.2.0-rc5`,
      `release_type=custom`, and `auto_merge=false` unless governance has changed.
- [ ] Preflight, build artifacts, release creation, PyPI publish, tag-triggered CI, and
      container publish/smoke runs are watched to completion.
- [ ] The created GitHub release is marked prerelease and points at the expected commit.
- [ ] PyPI and GHCR contain the expected RC5 artifacts or the rollback path is executed
      and documented.
- [ ] A release evidence note records workflow URLs, artifact identifiers, and any manual
      decisions.

**Scope notes**

This phase is operational. It may produce an evidence artifact rather than code changes.

**Non-goals**

- No announcement decision unless requested.
- No branch-protection or release-channel cleanup beyond documenting what happened.
- No auto-merge unless RELGOV has already frozen that policy.

**Key files**

- `.github/workflows/release-automation.yml`
- `.github/workflows/ci-cd-pipeline.yml`
- `.github/workflows/container-registry.yml`
- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `CHANGELOG.md`
- `RELEASE_NOTES.md`

**Depends on**
- GATEPARITY

**Produces**
- IF-0-RC5REL-1 - RC5 release evidence contract.

### Phase 3 — Release Governance & Channel Policy (RELGOV)

**Objective**

Turn the manual release-management caveats into explicit repository policy before relying
on auto-merge, public announcements, or GA promotion.

**Exit criteria**
- [ ] GitHub branch protection or a repository ruleset enforces the required gates, or
      the runbook explicitly states that enforcement is manual for public alpha.
- [ ] The required gate list in docs matches the actual workflow job names and aggregator
      behavior.
- [ ] The repository has a documented decision for the current GitHub "latest" release
      mismatch between `v2.15.0-alpha.1` and the active `v1.2.0-rc5` contract.
- [ ] Release automation behavior for prerelease, latest, Docker `latest`, and
      auto-merge is documented and tested where practical.
- [ ] Operators have a single source of truth for when to stay on RC/public-alpha versus
      start GA hardening.

**Scope notes**

This phase may require GitHub settings changes outside the worktree. When settings cannot
be represented as repo files, the phase should produce evidence that names the setting,
current value, and who changed or accepted it.

**Non-goals**

- No code readiness changes.
- No GA support claims.
- No requirement to change historical release tags unless the policy decision calls for it.

**Key files**

- `.github/workflows/release-automation.yml`
- `.github/workflows/ci-cd-pipeline.yml`
- `.github/workflows/container-registry.yml`
- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `tests/docs/test_p25_release_checklist.py`
- `tests/test_p25_release_gates.py`
- GitHub repository branch-protection or ruleset settings

**Depends on**
- GATEPARITY

**Produces**
- IF-0-RELGOV-1 - Release governance contract.

### Phase 4 — Secondary Tool Readiness Hardening (TOOLRDY)

**Objective**

Extend the v3 readiness model from primary query tools to secondary repository-scoped
operations so mutation and summarization tools do not accidentally use unavailable or
wrong-repository state.

**Exit criteria**
- [ ] `reindex` classifies unregistered, wrong-branch, stale/missing-index, and
      unsupported-worktree targets before mutating, with explicit remediation in
      responses.
- [ ] `write_summaries` and `summarize_sample` reject unsafe repository targets or require
      explicit path scope rather than falling back to a global/default store.
- [ ] Path-based invocations keep the `MCP_ALLOWED_ROOTS` boundary and conflict detection.
- [ ] Tests cover secondary-tool behavior for ready repo, unregistered repo,
      unsupported sibling worktree, wrong branch, missing index, and explicit path scope.
- [ ] An end-to-end register/reindex/search smoke covers a fresh repository and durable
      SQLite rows without relying only on seeded fixtures.

**Scope notes**

This is post-alpha hardening. It should follow the existing readiness vocabulary from P27
and fail-closed query responses from P28, but it may define secondary-tool-specific
mutation responses where `safe_fallback: native_search` is not meaningful.

**Non-goals**

- No multi-worktree support.
- No summarization model/provider changes.
- No broad dispatcher rewrite beyond what secondary-tool safety requires.

**Key files**

- `mcp_server/cli/tool_handlers.py`
- `mcp_server/core/repo_resolver.py`
- `mcp_server/health/repo_status.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `tests/test_tool_readiness_fail_closed.py`
- `tests/test_repository_readiness.py`
- `tests/test_git_index_manager.py`
- `tests/smoke/`

**Depends on**
- GATEPARITY

**Produces**
- IF-0-TOOLRDY-1 - Secondary tool readiness contract.

### Phase 5 — GA Hardening Evidence Closeout (GACLOSE)

**Objective**

Collect the remaining evidence and public-surface cleanup needed to decide whether the
project should begin GA promotion or open a narrower post-alpha follow-up roadmap.

**Exit criteria**
- [ ] Public docs and installer flows no longer contain stale active-release claims.
- [ ] The support matrix distinguishes public-alpha, beta, and GA claims without
      overpromising multi-worktree or multi-branch behavior.
- [ ] Release evidence from RC5, release governance evidence, and secondary-tool
      readiness evidence are linked from the operator runbook or release checklist.
- [ ] The production matrix still passes after TOOLRDY.
- [ ] A final decision artifact states one of: stay on RC/public-alpha, cut a follow-up
      RC, or start a GA hardening roadmap.

**Scope notes**

This is a decision and evidence phase. It should not become a dumping ground for unrelated
feature work.

**Non-goals**

- No GA launch unless a separate release decision is made.
- No new language/runtime support.
- No broad documentation redesign.

**Key files**

- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/DOCKER_GUIDE.md`
- `docs/MCP_CONFIGURATION.md`
- `docs/SUPPORT_MATRIX.md`
- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `CHANGELOG.md`
- `tests/docs/`
- `tests/smoke/`

**Depends on**
- RC5REL
- RELGOV
- TOOLRDY

**Produces**
- IF-0-GACLOSE-1 - GA evidence contract.

## Phase Dependency DAG

```text
P34
 └─> GATEPARITY
      ├─> RC5REL ─────┐
      ├─> RELGOV ─────┼─> GACLOSE
      └─> TOOLRDY ────┘
```

GATEPARITY is the only phase that should block the RC5 release if the goal is a clean
public-alpha tag. RC5REL is operational release execution. RELGOV and TOOLRDY can be
planned after GATEPARITY; TOOLRDY should not delay RC5 unless the team decides secondary
tools are part of the announcement promise. GACLOSE waits for release evidence, governance
policy, and secondary-tool hardening.

## Execution Notes

- Plan GATEPARITY first with `codex-plan-phase specs/phase-plans-v4.md GATEPARITY`.
- Execute GATEPARITY before dispatching the RC5 workflow unless the operator explicitly
  accepts the current manual preflight caveat.
- Plan RC5REL after GATEPARITY if the goal is to cut `v1.2.0-rc5` immediately.
- RELGOV can be planned in parallel with RC5 observation, but branch-protection settings
  may require manual GitHub access outside the repo.
- TOOLRDY is the first code-hardening phase and should be treated as post-alpha unless a
  release decision says otherwise.
- GACLOSE should be planned only after RC5 release evidence exists.

## Verification

```bash
# GATEPARITY
uv run pytest tests/docs/test_p25_release_checklist.py tests/docs/test_p34_public_alpha_recut.py tests/smoke/test_release_smoke_contract.py -v --no-cov
make alpha-production-matrix
make release-smoke
make release-smoke-container
rg -n "v1\\.2\\.0-rc4|v1\\.2\\.0-rc5|Alpha Gate - Production Multi-Repo Matrix|release-smoke-container" \
  Makefile .github/workflows docs scripts tests

# RC5REL
git status --short --branch
git rev-parse HEAD origin/main
git tag -l v1.2.0-rc5
git ls-remote --tags origin refs/tags/v1.2.0-rc5
gh workflow run "Release Automation" -f version=v1.2.0-rc5 -f release_type=custom -f auto_merge=false
gh run list --workflow "Release Automation" --limit 5
gh release view v1.2.0-rc5

# RELGOV
gh api repos/ViperJuice/Code-Index-MCP/branches/main/protection/required_status_checks
gh release list --limit 20
uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py -v --no-cov

# TOOLRDY
uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py tests/smoke -v --no-cov

# GACLOSE
uv run pytest tests/docs tests/smoke tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
make alpha-production-matrix
rg -n "v1\\.2\\.0-rc4|unrestricted multi-worktree|unrestricted multi-branch|indexes every branch|latest" \
  README.md CHANGELOG.md docs scripts
```

