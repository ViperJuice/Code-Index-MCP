# RELGOV: Release Governance & Channel Policy

> Plan doc produced by `codex-plan-phase specs/phase-plans-v4.md RELGOV`
> on 2026-04-24.
> Source roadmap `specs/phase-plans-v4.md` is tracked and clean in this
> worktree (`git status --short -- specs/phase-plans-v4.md` produced no
> output).

## Context

RELGOV is the third v4 phase. It depends on GATEPARITY and can proceed after
the RC5 release observation work because this checkout now has
`docs/validation/rc5-release-evidence.md`, recording a successful
`v1.2.0-rc5` release workflow on 2026-04-24.

Current repo and GitHub metadata gathered during planning:

- `main` is clean and aligned with `origin/main` at `8d08545`.
- `docs/validation/rc5-release-evidence.md` records `v1.2.0-rc5` as published
  to GitHub releases, PyPI, and GHCR with `auto_merge=false`.
- `gh api repos/ViperJuice/Code-Index-MCP/branches/main` reported
  `protected: false`.
- `gh api repos/ViperJuice/Code-Index-MCP/branches/main/protection` returned
  `Branch not protected (HTTP 404)`.
- `gh api repos/ViperJuice/Code-Index-MCP/rulesets` returned an empty list.
- `gh release list --limit 10` still marks `v2.15.0-alpha.1` as GitHub Latest,
  while `v1.2.0-rc5` is a prerelease published on 2026-04-24.

This phase should not add readiness-code changes or GA claims. Its job is to
make release governance explicit: whether required gates are enforced by GitHub
settings or manually for public alpha, what the current release-channel mismatch
means, and when operators should stay on RC/public-alpha versus move toward GA
hardening.

## Interface Freeze Gates

- [x] IF-0-RELGOV-1 - Required-gate authority contract: the required public
      alpha gates are exactly `Alpha Gate - Dependency Sync`,
      `Alpha Gate - Format And Lint`, `Alpha Gate - Unit And Release Smoke`,
      `Alpha Gate - Integration Smoke`,
      `Alpha Gate - Production Multi-Repo Matrix`,
      `Alpha Gate - Docker Build And Smoke`, `Alpha Gate - Docs Truth`, and
      `Alpha Gate - Required Gates Passed`, and docs name the matching workflow
      job or command source for each.
- [x] IF-0-RELGOV-2 - Enforcement disposition contract:
      `docs/validation/release-governance-evidence.md` records the observed
      branch protection/ruleset state for `main`; if GitHub enforcement remains
      absent, `docs/operations/deployment-runbook.md` and
      `docs/operations/user-action-runbook.md` explicitly say required-gate
      enforcement is manual for public alpha.
- [x] IF-0-RELGOV-3 - Release-channel decision contract: operator docs record
      that `v1.2.0-rc5` is the active RC/public-alpha package contract, that
      GitHub Latest currently points at `v2.15.0-alpha.1`, and that GitHub
      Latest is not the policy source for the RC track unless a later release
      operation deliberately changes it.
- [x] IF-0-RELGOV-4 - Release automation policy contract:
      `.github/workflows/release-automation.yml` keeps `auto_merge=false` as
      the RC default, marks hyphenated versions as prereleases, publishes Docker
      `latest` only for stable releases, and refuses prerelease tags unless
      `release_type=custom`.
- [x] IF-0-RELGOV-5 - RC-versus-GA source-of-truth contract: the operator
      runbook has one section that states whether to stay on RC/public-alpha or
      start GA hardening, and that section points GACLOSE at the needed release
      evidence, governance evidence, and secondary-tool readiness evidence.

## Lane Index & Dependencies

- SL-0 - Governance contract tests; Depends on: GATEPARITY; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Workflow policy guardrails; Depends on: SL-0; Blocks: SL-3, SL-4; Parallel-safe: yes
- SL-2 - GitHub governance probe; Depends on: SL-0; Blocks: SL-3, SL-4; Parallel-safe: yes
- SL-3 - Operator governance docs; Depends on: SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Governance evidence reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: RELGOV acceptance; Parallel-safe: no

Lane DAG:

```text
GATEPARITY
  -> SL-0
       -> SL-1 --.
       -> SL-2 ----> SL-3 -> SL-4 -> RELGOV acceptance
```

## Lanes

### SL-0 - Governance Contract Tests

- **Scope**: Freeze the release-governance assertions before changing workflow
  comments, runbooks, or evidence files.
- **Owned files**: `tests/docs/test_p25_release_checklist.py`,
  `tests/test_p25_release_gates.py`
- **Interfaces provided**: IF-0-RELGOV-1 through IF-0-RELGOV-5 as executable
  docs/workflow contract assertions
- **Interfaces consumed**: existing P25 required-gate vocabulary; existing
  GATEPARITY tests; existing RC5 release automation policy tests
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_p25_release_checklist.py` to require a
    release-governance section in `docs/operations/deployment-runbook.md` and
    `docs/operations/user-action-runbook.md` that names enforcement mode,
    branch protection or ruleset disposition, the active RC contract, the
    GitHub Latest mismatch, and the RC-versus-GA decision point.
  - test: Extend `tests/docs/test_p25_release_checklist.py` to require
    `docs/validation/release-governance-evidence.md` to contain non-secret
    metadata for `main` protection, repository rulesets, `v1.2.0-rc5`,
    `v2.15.0-alpha.1`, and the operator who accepted or changed the policy.
  - test: Extend `tests/test_p25_release_gates.py` only if needed so the
    release automation policy remains frozen around prerelease detection,
    Docker `latest` only for stable releases, and `auto_merge=false` for RC
    dispatch.
  - verify: `uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py -v --no-cov`

### SL-1 - Workflow Policy Guardrails

- **Scope**: Keep workflow behavior aligned with the governance contract without
  changing the release semantics unless SL-0 exposes drift.
- **Owned files**: `.github/workflows/release-automation.yml`,
  `.github/workflows/ci-cd-pipeline.yml`,
  `.github/workflows/container-registry.yml`
- **Interfaces provided**: IF-0-RELGOV-1 required job names and aggregator
  behavior; IF-0-RELGOV-4 release automation behavior
- **Interfaces consumed**: SL-0 workflow assertions; current GATEPARITY release
  preflight contract
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 tests to confirm required workflow job names and aggregator
    dependencies still match the runbook gate list.
  - impl: If workflow comments are stale, clarify that `preflight-release-gates`
    is the release-mutation boundary and that `auto_merge=false` is the RC
    default until governance changes.
  - impl: If workflow behavior has drifted, restore the existing policy:
    hyphenated versions are prereleases, `release_type=custom` is required for
    prerelease tags, and Docker `latest` is emitted only for stable releases.
  - impl: Do not promote scan, signing, cleanup, or manifest-publish jobs to
    blockers in this phase.
  - verify: `uv run pytest tests/test_p25_release_gates.py -v --no-cov`
  - verify: `rg -n 'auto_merge|is_prerelease|release_type=custom|ghcr.io/viperjuice/code-index-mcp:latest|Alpha Gate - Required Gates Passed' .github/workflows tests/test_p25_release_gates.py`

### SL-2 - GitHub Governance Probe

- **Scope**: Capture current GitHub repository policy and release-channel state
  as redacted metadata for the docs/evidence lanes.
- **Owned files**: none
- **Interfaces provided**: observed branch protection state, repository ruleset
  state, latest-release state, RC5 release state, and accepted policy path for
  SL-3 and SL-4
- **Interfaces consumed**: GitHub CLI repository metadata; RC5 release evidence
  from `docs/validation/rc5-release-evidence.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Run `gh repo view ViperJuice/Code-Index-MCP --json nameWithOwner,defaultBranchRef,visibility`.
  - test: Run `gh api repos/ViperJuice/Code-Index-MCP/branches/main --jq '{name, protected, protection_url}'`.
  - test: Run `gh api repos/ViperJuice/Code-Index-MCP/branches/main/protection`
    and record either the required status checks or the `Branch not protected`
    result.
  - test: Run `gh api repos/ViperJuice/Code-Index-MCP/rulesets` and record
    names, enforcement modes, targets, and rule types if any exist.
  - test: Run `gh release list --repo ViperJuice/Code-Index-MCP --limit 10`,
    `gh api repos/ViperJuice/Code-Index-MCP/releases/latest`, and
    `gh release view v1.2.0-rc5 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url`.
  - impl: Decide from observed metadata whether execution should document
    manual enforcement for public alpha or record an actual branch
    protection/ruleset configuration.
  - verify: no file verification in this lane; outputs are consumed by SL-3 and
    SL-4.

### SL-3 - Operator Governance Docs

- **Scope**: Make the operator-facing release governance policy explicit in the
  runbooks.
- **Owned files**: `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`
- **Interfaces provided**: IF-0-RELGOV-1, IF-0-RELGOV-2, IF-0-RELGOV-3, and
  IF-0-RELGOV-5 as human-readable operator policy
- **Interfaces consumed**: SL-0 docs assertions; SL-1 workflow policy; SL-2
  GitHub metadata; `docs/validation/rc5-release-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Use SL-0 docs tests to fail first on missing governance sections.
  - impl: Add a release-governance section to `docs/operations/deployment-runbook.md`
    that names the required gate list, the workflow/job source for each gate,
    and whether GitHub branch protection/rulesets enforce them or manual
    enforcement remains the public-alpha policy.
  - impl: Add the same governance decision to `docs/operations/user-action-runbook.md`
    as an operator checklist item, including who must accept manual enforcement
    if branch settings remain unchanged.
  - impl: Document the release-channel decision: `v1.2.0-rc5` is the active
    RC/public-alpha package contract, `v2.15.0-alpha.1` is currently GitHub
    Latest, and GitHub Latest is not the RC policy source unless a later
    operation changes release channel state.
  - impl: Document release automation behavior for prerelease, latest, Docker
    `latest`, and `auto_merge=false`, pointing at
    `.github/workflows/release-automation.yml` instead of duplicating workflow
    internals.
  - impl: Add the RC/public-alpha versus GA decision rule: remain on RC until
    RC5 release evidence, RELGOV evidence, TOOLRDY evidence, and GACLOSE
    acceptance justify GA hardening or another follow-up RC.
  - verify: `uv run pytest tests/docs/test_p25_release_checklist.py -v --no-cov`
  - verify: `rg -n 'branch protection|ruleset|manual enforcement|v2\\.15\\.0-alpha\\.1|v1\\.2\\.0-rc5|GitHub Latest|auto_merge=false|Docker latest|GACLOSE' docs/operations`

### SL-4 - Governance Evidence Reducer

- **Scope**: Reduce the contract tests, workflow policy, GitHub metadata, and
  operator-doc decisions into a single evidence artifact.
- **Owned files**: `docs/validation/release-governance-evidence.md`
- **Interfaces provided**: IF-0-RELGOV-2 and IF-0-RELGOV-3 evidence for
  GACLOSE; redacted access/probe record for any external GitHub settings
- **Interfaces consumed**: SL-0 test contract; SL-1 workflow policy; SL-2
  GitHub metadata; SL-3 operator-doc policy; RC5 release evidence
- **Parallel-safe**: no
- **Tasks**:
  - test: Create or update `docs/validation/release-governance-evidence.md`
    only after SL-2 and SL-3 have terminal outputs.
  - impl: Record exact UTC timestamp, repository, default branch, branch
    protection state, ruleset state, required gate names, GitHub Latest release,
    active RC release, release automation policy, Docker `latest` policy,
    auto-merge policy, and RC-versus-GA decision.
  - impl: If GitHub settings were changed outside the worktree, record the
    setting name, previous value, new value, actor, and non-secret evidence
    command. If settings were not changed, record who accepted manual
    enforcement for public alpha or that manual acceptance is still required.
  - impl: Do not include tokens, private keys, raw secret-bearing CLI output, or
    credential payloads.
  - verify: `uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py -v --no-cov`
  - verify: `rg -n 'Branch protection|Ruleset|Required gates|GitHub Latest|v2\\.15\\.0-alpha\\.1|v1\\.2\\.0-rc5|auto_merge=false|Docker latest|GACLOSE' docs/validation/release-governance-evidence.md docs/operations`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` after lane changes land.

Lane-local checks:

```bash
uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py -v --no-cov
rg -n 'auto_merge|is_prerelease|release_type=custom|ghcr.io/viperjuice/code-index-mcp:latest|Alpha Gate - Required Gates Passed' .github/workflows tests/test_p25_release_gates.py
rg -n 'branch protection|ruleset|manual enforcement|v2\.15\.0-alpha\.1|v1\.2\.0-rc5|GitHub Latest|auto_merge=false|Docker latest|GACLOSE' docs/operations docs/validation/release-governance-evidence.md
```

External metadata probes:

```bash
gh repo view ViperJuice/Code-Index-MCP --json nameWithOwner,defaultBranchRef,visibility
gh api repos/ViperJuice/Code-Index-MCP/branches/main --jq '{name, protected, protection_url}'
gh api repos/ViperJuice/Code-Index-MCP/branches/main/protection
gh api repos/ViperJuice/Code-Index-MCP/rulesets
gh release list --repo ViperJuice/Code-Index-MCP --limit 10
gh api repos/ViperJuice/Code-Index-MCP/releases/latest
gh release view v1.2.0-rc5 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url
```

Whole-phase acceptance checks:

```bash
uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py tests/test_release_metadata.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov
git status --short -- docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md docs/validation/release-governance-evidence.md tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py .github/workflows/release-automation.yml .github/workflows/ci-cd-pipeline.yml .github/workflows/container-registry.yml
```

## Acceptance Criteria

- [x] GitHub branch protection or a repository ruleset enforces the required
      gates, or the runbooks explicitly state that enforcement is manual for
      public alpha.
- [x] The required gate list in docs matches the actual workflow job names and
      aggregator behavior.
- [x] `docs/validation/release-governance-evidence.md` records the observed
      `main` protection/ruleset state and the accepted enforcement disposition.
- [x] Operator docs document the current GitHub Latest mismatch between
      `v2.15.0-alpha.1` and the active `v1.2.0-rc5` RC/public-alpha contract.
- [x] Release automation behavior for prerelease, GitHub Latest, Docker
      `latest`, and `auto_merge=false` is documented and tested where
      practical.
- [x] Operators have a single source of truth for staying on RC/public-alpha
      versus starting GA hardening.
- [x] The RELGOV docs/workflow contract tests pass without printing secret
      values.

## Execution Evidence

- Executed: 2026-04-24.
- GitHub metadata probes confirmed `main` is unprotected, repository rulesets
  are empty, `v1.2.0-rc5` is the active prerelease RC/public-alpha contract, and
  GitHub Latest resolves to `v2.15.0-alpha.1`.
- Workflow files did not need behavior changes; existing tests already freeze
  prerelease detection, `release_type=custom`, stable-only Docker latest, and
  `auto_merge=false` for RC dispatch.
- Added operator release-governance policy to
  `docs/operations/deployment-runbook.md` and
  `docs/operations/user-action-runbook.md`.
- Added `docs/validation/release-governance-evidence.md` and the matching
  historical-validation triage row.
- Updated release metadata verification so a local `v1.2.0-rc5` tag is valid
  when it points at the released commit documented in
  `docs/validation/rc5-release-evidence.md`.

Verification passed:

```bash
uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py -v --no-cov
uv run pytest tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py tests/test_release_metadata.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov
uv run pytest tests/docs/test_p8_historical_sweep.py -v --no-cov
rg -n 'auto_merge|is_prerelease|release_type=custom|ghcr.io/viperjuice/code-index-mcp:latest|Alpha Gate - Required Gates Passed' .github/workflows tests/test_p25_release_gates.py
rg -n 'branch protection|ruleset|manual enforcement|v2\.15\.0-alpha\.1|v1\.2\.0-rc5|GitHub Latest|auto_merge=false|Docker latest|GACLOSE' docs/operations docs/validation/release-governance-evidence.md
```

## Automation Handoff

```yaml
automation:
  status: complete
  next_skill: codex-plan-phase
  next_command: codex-plan-phase specs/phase-plans-v4.md TOOLRDY
  next_model_hint: plan
  next_effort_hint: high
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: passed
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v4-relgov.md
  artifact_state: staged
```
