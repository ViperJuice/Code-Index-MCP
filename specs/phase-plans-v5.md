# Phase roadmap v5

## Context

The v4 roadmap closed the public-alpha release cleanup path. `v1.2.0-rc5`
exists as the active RC/public-alpha package contract, the release governance
evidence records manual gate enforcement, TOOLRDY hardened secondary repository
tools, and GACLOSE decided to stay on RC/public-alpha rather than publish GA
claims.

This roadmap starts a separate GA-hardening family. It must not reopen v4 as a
catch-all cleanup track. The goal is to make a GA decision mechanically boring:
support claims, release gates, install paths, operational runbooks, and runtime
failure behavior must all be explicit, enforced where possible, and backed by
fresh evidence.

## Architecture North Star

GA should mean the current product contract is enforced, documented, tested,
installable, observable, and supportable. It does not require broadening the
product surface. In particular, the v3 topology model remains valid unless a
specific phase explicitly changes it: many unrelated repositories, one
registered worktree per git common directory, tracked/default branch indexing,
and fail-closed readiness behavior for unavailable indexes.

## Assumptions

- `v1.2.0-rc5` remains the active RC/public-alpha contract until this roadmap
  cuts a follow-up RC or GA release.
- STDIO remains the primary LLM tool surface; FastAPI remains secondary/admin.
- GitHub Actions remains the release automation and evidence surface.
- GitHub branch protection or rulesets may require live repository settings
  probes and operator acceptance.
- GA support may be tiered by language/runtime instead of universal.
- Existing v4 evidence is input evidence, not sufficient GA evidence by itself.

## Non-Goals

- No unrestricted multi-worktree or multi-branch support unless a future
  roadmap explicitly chooses that product expansion.
- No universal language/runtime support claim.
- No marketing-site or launch-announcement work.
- No broad dispatcher or plugin rewrite unless required by a frozen GA contract.
- No GA tag until follow-up RC soak evidence and final GA decision evidence
  exist.

## Cross-Cutting Principles

- Freeze the GA contract before changing release or support behavior.
- Prefer enforcement over prose when a repository setting or workflow gate can
  represent the policy.
- Treat docs as release surface: every public claim needs a test or evidence
  source.
- Keep public-alpha/beta limitations visible until final GA evidence justifies
  narrower GA wording.
- Record access and settings probes as redacted metadata only.
- Keep follow-up RC evidence separate from final GA release evidence.

## Top Interface-Freeze Gates

- IF-0-GABASE-1 — GA readiness contract: a canonical checklist defines the GA
  release boundary, support tiers, required gates, evidence artifacts, rollback
  expectations, and non-GA surfaces.
- IF-0-GAGOV-1 — Enforced governance contract: required GA gates are enforced by
  branch protection or repository rulesets, or a documented blocker prevents GA.
- IF-0-GASUPPORT-1 — GA support-tier contract: every advertised language,
  runtime, install path, and tool surface has an explicit GA/beta/experimental/
  unsupported tier with tests preventing broader claims.
- IF-0-GAE2E-1 — GA end-to-end evidence contract: clean install, indexing,
  multi-repo, readiness, summarization, Docker, and artifact identity checks
  pass from fresh environments and are recorded as release evidence.
- IF-0-GAOPS-1 — GA operations contract: runbooks define deployment, rollback,
  observability, index rebuild, incident response, and support boundaries without
  relying on project-history knowledge.
- IF-0-GARC-1 — Follow-up RC soak contract: a post-hardening RC is cut,
  observed, and verified before any GA tag or GA claim.
- IF-0-GAREL-1 — GA decision and release contract: final evidence states exactly
  one of ship GA, cut another RC, or defer GA, and release mutation happens only
  when the ship-GA path is selected.

## Phases

### Phase 1 — GA Criteria Freeze (GABASE)

**Objective**

Define the GA contract before changing code, docs, release settings, or support
claims.

**Exit criteria**
- [ ] A canonical GA readiness checklist exists and names release gates, support
      tiers, required evidence, rollback expectations, and non-GA surfaces.
- [ ] Docs tests prove public docs do not claim GA before the final GA decision.
- [ ] The checklist preserves v3 repository-topology limits unless a later
      roadmap changes them explicitly.
- [ ] The checklist names which existing v4 evidence is input evidence and which
      evidence must be refreshed for GA.
- [ ] Downstream phases consume the same readiness vocabulary and support-tier
      labels.

**Scope notes**

This is an interface-freeze phase. It may add docs and tests, but it should not
modify release automation, GitHub settings, runtime code, or support behavior.

**Non-goals**

- No GA release.
- No branch protection or ruleset mutation.
- No support-matrix expansion.

**Key files**

- `docs/validation/ga-closeout-decision.md`
- `docs/validation/ga-readiness-checklist.md`
- `docs/SUPPORT_MATRIX.md`
- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/MCP_CONFIGURATION.md`
- `docs/DOCKER_GUIDE.md`
- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `tests/docs/`

**Depends on**
- GACLOSE

**Produces**
- IF-0-GABASE-1 — GA readiness contract.

### Phase 2 — Enforced Release Governance (GAGOV)

**Objective**

Move the release process from manually accepted public-alpha governance to
enforced GA governance where repository settings and workflow gates can express
the policy.

**Exit criteria**
- [ ] GitHub branch protection or repository rulesets enforce the required GA
      gate set on `main`, or a blocker artifact records why GA cannot proceed.
- [ ] Required workflow job names and aggregator behavior match the GA readiness
      checklist.
- [ ] Release Automation prerelease/latest, Docker latest, tag, auto-merge, and
      rollback behavior is documented and covered by tests where practical.
- [ ] GitHub Latest is either aligned with the intended GA channel or explicitly
      excluded until final GA release.
- [ ] A redacted governance evidence artifact records repository settings,
      release-channel state, and operator acceptance.

**Scope notes**

This phase may require metadata-only GitHub CLI probes and repository settings
changes. Report settings and access state as redacted metadata only.

**Non-goals**

- No release dispatch.
- No GA support claim.
- No code readiness refactor.

**Key files**

- `.github/workflows/release-automation.yml`
- `.github/workflows/ci-cd-pipeline.yml`
- `.github/workflows/container-registry.yml`
- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `docs/validation/ga-governance-evidence.md`
- `tests/docs/test_p25_release_checklist.py`
- `tests/test_p25_release_gates.py`

**Depends on**
- GABASE

**Produces**
- IF-0-GAGOV-1 — Enforced governance contract.

### Phase 3 — GA Support Matrix Hardening (GASUPPORT)

**Objective**

Convert the support matrix from public-alpha/beta caveats into explicit GA
support tiers without broadening the actual product surface.

**Exit criteria**
- [ ] Every language/runtime row has one explicit tier: GA-supported, beta,
      experimental, unsupported, or disabled-by-default.
- [ ] STDIO tools, FastAPI/admin surfaces, Docker, uv/wheel install, semantic
      search, reranking, sandbox behavior, and optional extras have explicit
      support tiers.
- [ ] Tests reject universal language/runtime support, unrestricted repository
      topology, and unsupported install-surface claims.
- [ ] `list_plugins` and plugin availability docs agree on sandbox/default
      behavior for GA-tier claims.
- [ ] Secondary-tool readiness evidence is referenced as readiness evidence, not
      as support expansion.

**Scope notes**

This phase is docs and contract hardening first. Runtime changes should be
limited to making existing support-tier facts machine-checkable.

**Non-goals**

- No new language plugins.
- No multi-worktree or multi-branch expansion.
- No semantic provider change.

**Key files**

- `docs/SUPPORT_MATRIX.md`
- `mcp_server/plugins/language_registry.py`
- `mcp_server/plugins/plugin_factory.py`
- `mcp_server/plugins/plugin_set_registry.py`
- `mcp_server/plugins/sandboxed_plugin.py`
- `mcp_server/cli/stdio_runner.py`
- `README.md`
- `docs/GETTING_STARTED.md`
- `tests/docs/`
- `tests/test_stdio_tool_descriptions.py`

**Depends on**
- GABASE

**Produces**
- IF-0-GASUPPORT-1 — GA support-tier contract.

### Phase 4 — GA End-to-End Evidence (GAE2E)

**Objective**

Generate fresh GA-grade evidence from clean install and fresh repository flows,
covering the actual release surfaces and failure modes.

**Exit criteria**
- [ ] Clean uv/wheel install and STDIO smoke pass from a fresh checkout or
      isolated environment.
- [ ] Docker image build/run smoke covers the GA candidate image name and tag
      policy.
- [ ] Fresh repository register/reindex/search/symbol/summarize flows persist
      durable SQLite rows and return expected readiness vocabulary.
- [ ] Multi-repo isolation, wrong-branch, unsupported-worktree, stale/missing
      index, and allowed-roots failure modes pass from fresh fixtures.
- [ ] Artifact identity checks cover expected package, wheel, sdist, GHCR image,
      and release metadata.
- [ ] A GA E2E evidence artifact records commands, timestamps, commit, artifact
      identities, and redacted metadata only.

**Scope notes**

This phase should prefer reproducible local and CI-friendly smokes over manual
claims. Any credentialed checks must be recorded as metadata only. GASUPPORT is
the canonical source for row-level support tiers
(`GA-supported`, `beta`, `experimental`, `unsupported`,
`disabled-by-default`), while GABASE still owns the product-level release
posture (`public-alpha`, `beta`, `GA`). GAE2E must consume that distinction
rather than collapsing the vocabularies again.

**Non-goals**

- No release dispatch.
- No GA decision.
- No support-tier changes unless tests expose a mismatch with GASUPPORT.

**Key files**

- `tests/smoke/`
- `tests/test_multi_repo_production_matrix.py`
- `tests/test_multi_repo_failure_matrix.py`
- `tests/test_tool_readiness_fail_closed.py`
- `tests/test_repository_readiness.py`
- `tests/test_git_index_manager.py`
- `tests/test_release_metadata.py`
- `scripts/download-release.py`
- `scripts/install-mcp-docker.sh`
- `scripts/install-mcp-docker.ps1`
- `docs/validation/ga-e2e-evidence.md`

**Depends on**
- GABASE
- GASUPPORT

**Produces**
- IF-0-GAE2E-1 — GA end-to-end evidence contract.

### Phase 5 — GA Operational Readiness (GAOPS)

**Objective**

Make the operator path complete enough for GA: deployment, rollback,
observability, index rebuild, incident response, support triage, and limitation
handling must be documented and testable.

**Exit criteria**
- [ ] Deployment and user-action runbooks define GA preflight, deployment,
      rollback, index rebuild, and incident-response procedures.
- [ ] Observability expectations and failure thresholds are documented without
      promising unimplemented managed operations.
- [ ] Operator docs distinguish local-first indexing responsibilities from any
      hosted or managed-service assumptions.
- [ ] Runbook tests prevent stale RC/public-alpha instructions from becoming GA
      instructions accidentally.
- [ ] A GA operations evidence artifact records which procedures were validated
      locally, in CI, or as metadata-only checks.

**Scope notes**

This is operational documentation and evidence hardening. It can add lightweight
scripts or tests only where they verify operator procedures.

**Non-goals**

- No managed service launch.
- No new monitoring backend selection unless the current docs require one.
- No broad documentation redesign.

**Key files**

- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `docs/operations/observability-verification.md`
- `docs/DEPLOYMENT-GUIDE.md`
- `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`
- `docs/validation/ga-operations-evidence.md`
- `tests/docs/`
- `scripts/preflight_upgrade.sh`

**Depends on**
- GABASE
- GAGOV
- GAE2E

**Produces**
- IF-0-GAOPS-1 — GA operations contract.

### Phase 6 — Follow-Up RC Soak (GARC)

**Objective**

Cut and observe a post-hardening RC before making any GA release decision.

**Exit criteria**
- [ ] Local pre-dispatch checks confirm clean release state, expected branch,
      synchronized `origin/main`, and no reused follow-up RC tag.
- [ ] Release Automation dispatch uses the agreed follow-up RC version,
      prerelease/custom release type, and governance-approved auto-merge policy.
- [ ] Preflight gates, release artifact build, GitHub release, PyPI publish,
      GHCR publish, install smokes, and container smokes are watched to
      completion.
- [ ] The follow-up RC evidence artifact records workflow URLs, artifact
      identities, tag target, release-channel state, rollback disposition, and
      any manual decisions.
- [ ] No GA docs or stable Docker latest claims are published from the RC.

**Scope notes**

This phase is operational release execution. GABASE freezes the follow-up RC
version as `v1.2.0-rc6` before planning this phase.

**Non-goals**

- No GA tag.
- No GA announcement.
- No support-tier expansion during release execution.

**Key files**

- `.github/workflows/release-automation.yml`
- `.github/workflows/ci-cd-pipeline.yml`
- `.github/workflows/container-registry.yml`
- `CHANGELOG.md`
- `RELEASE_NOTES.md`
- `docs/validation/ga-rc-evidence.md`
- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`

**Depends on**
- GAGOV
- GASUPPORT
- GAE2E
- GAOPS

**Produces**
- IF-0-GARC-1 — Follow-up RC soak contract.

### Phase 7 — GA Decision and Release (GAREL)

**Objective**

Reduce all GA-hardening evidence into one final decision and, only if the
decision is ship GA, execute the GA release.

**Exit criteria**
- [ ] A final decision artifact states exactly one of `ship GA`, `cut another
      RC`, or `defer GA`.
- [ ] If the decision is not `ship GA`, no GA release mutation occurs and the
      artifact names the next roadmap or RC scope.
- [ ] If the decision is `ship GA`, Release Automation dispatches the GA version
      with governance-approved inputs and records tag, GitHub release, PyPI,
      GHCR, install, and rollback evidence.
- [ ] Public docs, support matrix, changelog, runbooks, and installer flows
      match the final release channel and support-tier claims.
- [ ] Post-release verification passes from a clean checkout and the final GA
      evidence artifact records all command results.

**Scope notes**

This phase is a guarded decision reducer plus release execution. It must stop
before mutation if governance, support, E2E, operations, or RC soak evidence is
missing.

**Non-goals**

- No release mutation when final evidence selects another RC or defer-GA.
- No unreviewed support expansion.
- No GitHub Latest policy change outside the release decision.

**Key files**

- `.github/workflows/release-automation.yml`
- `README.md`
- `CHANGELOG.md`
- `docs/GETTING_STARTED.md`
- `docs/DOCKER_GUIDE.md`
- `docs/MCP_CONFIGURATION.md`
- `docs/SUPPORT_MATRIX.md`
- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `docs/validation/ga-final-decision.md`
- `docs/validation/ga-release-evidence.md`
- `tests/docs/`
- `tests/smoke/`

**Depends on**
- GARC

**Produces**
- IF-0-GAREL-1 — GA decision and release contract.

## Phase Dependency DAG

```text
GACLOSE
  -> GABASE
       ├─> GAGOV ─────┐
       ├─> GASUPPORT ─┼─> GAE2E ─┐
       │              │          ├─> GAOPS ─┐
       └──────────────┘          │          │
                                 └──────────┴─> GARC -> GAREL
```

GAGOV and GASUPPORT can be planned after GABASE. GAE2E depends on the support
contract because the E2E evidence must know which claims it is proving. GAOPS
depends on governance and E2E evidence so operator procedures reference the
actual enforced gates and validated runtime behavior. GARC waits for governance,
support, E2E, and operations. GAREL waits for the follow-up RC soak.

## Execution Notes

- Plan GABASE first with `codex-plan-phase specs/phase-plans-v5.md GABASE`.
- Do not execute release mutation in GABASE, GAGOV, GASUPPORT, GAE2E, or GAOPS.
- GAGOV may require safe GitHub metadata probes before asking for settings
  changes or operator acceptance.
- GASUPPORT and GAGOV can be planned independently after GABASE, but their
  implementation should preserve dirty-tree boundaries because they both touch
  docs and tests.
- GAE2E should run after GASUPPORT so evidence maps to the frozen support tiers.
- GAOPS should consume GAGOV and GAE2E results before changing runbooks.
- GARC is the first phase that may dispatch a release workflow.
- GAREL must stop before any release mutation unless the final evidence selects
  `ship GA`.

## Verification

```bash
# GABASE
uv run pytest tests/docs -v --no-cov
rg -n "GA|public-alpha|beta|v1\\.2\\.0-rc5|unrestricted multi-worktree|unrestricted multi-branch|indexes every branch" \
  README.md CHANGELOG.md docs tests

# GAGOV
gh repo view ViperJuice/Code-Index-MCP --json nameWithOwner,defaultBranchRef,visibility
gh api repos/ViperJuice/Code-Index-MCP/branches/main --jq '{name, protected, protection_url}'
gh api repos/ViperJuice/Code-Index-MCP/rulesets
gh release list --repo ViperJuice/Code-Index-MCP --limit 20
uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py -v --no-cov

# GASUPPORT
uv run pytest tests/docs tests/test_stdio_tool_descriptions.py -v --no-cov
uv run python -m mcp_server.cli.server_commands list-plugins --help
rg -n "GA-supported|beta|experimental|unsupported|disabled-by-default|universal language|unrestricted" \
  docs/SUPPORT_MATRIX.md README.md docs tests

# GAE2E
uv run pytest tests/smoke tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py \
  tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py \
  tests/test_release_metadata.py -v --no-cov
make alpha-production-matrix
make release-smoke
make release-smoke-container

# GAOPS
uv run pytest tests/docs -v --no-cov
bash scripts/preflight_upgrade.sh --help
rg -n "rollback|observability|incident|index rebuild|GA|public-alpha|manual enforcement|branch protection|ruleset" \
  docs/operations docs/DEPLOYMENT-GUIDE.md docs/PRODUCTION_DEPLOYMENT_GUIDE.md tests/docs

# GARC
git status --short --branch
git rev-parse HEAD origin/main
git tag -l <follow-up-rc-tag>
git ls-remote --tags origin refs/tags/<follow-up-rc-tag>
gh workflow run "Release Automation" -f version=<follow-up-rc-tag> -f release_type=custom -f auto_merge=false
gh run list --workflow "Release Automation" --limit 10
gh release view <follow-up-rc-tag>

# GAREL
git status --short --branch
uv run pytest tests/docs tests/smoke tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
make alpha-production-matrix
make release-smoke
make release-smoke-container
gh workflow run "Release Automation" -f version=<ga-version> -f release_type=stable -f auto_merge=<approved-policy>
gh release view <ga-version>
```
