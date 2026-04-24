---
phase_loop_plan_version: 1
phase: GAGOV
roadmap: specs/phase-plans-v5.md
roadmap_sha256: 6c3ef37eac6b52116804f765470905ca8f8ec4333c306a57c9ba1b8a178b4dc5
---
# GAGOV: Enforced Release Governance

## Context

GAGOV is the second phase in the v5 GA-hardening roadmap. It depends on
GABASE, which is already recorded as `complete` in
`.codex/phase-loop/state.json`, and it should convert the current
RC/public-alpha governance posture into an enforced GA-governance decision:
either `main` gets the required repository enforcement, or a blocker artifact
proves why GA cannot proceed yet.

Current repo and access state gathered during planning:

- The checkout is on `main` at `8d08545`.
- `specs/phase-plans-v5.md` is already staged in this worktree
  (`git status --short -- specs/phase-plans-v5.md` returned
  `A  specs/phase-plans-v5.md`), so it must be treated as the user-owned
  roadmap baseline.
- GABASE outputs already exist in the worktree, including
  `docs/validation/ga-readiness-checklist.md`,
  `tests/docs/test_gabase_ga_readiness_contract.py`, and the related docs
  vocabulary updates. GAGOV should consume that frozen checklist instead of
  redefining GA gates or tier labels.
- `gh auth status` reports an authenticated `github.com` session for account
  `ViperJuice`, so metadata-only GitHub governance probes are available during
  execution without asking the user for credentials first.
- `gh repo view ViperJuice/Code-Index-MCP --json nameWithOwner,defaultBranchRef,visibility`
  reports a public repository with default branch `main`.
- `gh api repos/ViperJuice/Code-Index-MCP/branches/main --jq '{name, protected, protection_url}'`
  reports `protected: false`, and `gh api repos/ViperJuice/Code-Index-MCP/rulesets`
  returned no rulesets, so the current live repository state does not yet
  satisfy the GAGOV exit criterion.
- `gh release view v1.2.0-rc5 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url`
  reports `v1.2.0-rc5` as the active prerelease published on 2026-04-24.
- `gh api repos/ViperJuice/Code-Index-MCP/releases/latest --jq '{tag_name, draft, prerelease, published_at, html_url}'`
  reports GitHub Latest as `v2.15.0-alpha.1` published on 2026-04-05, so
  release-channel state is still misaligned with the intended GA-hardening
  path.
- `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`, and
  `docs/validation/release-governance-evidence.md` currently describe the
  public-alpha manual-enforcement posture; GAGOV should either replace that
  posture with enforced GA governance or record an explicit blocker path in
  `docs/validation/ga-governance-evidence.md`.

## Interface Freeze Gates

- [ ] IF-0-GAGOV-1 - Required-gate authority contract:
      `docs/validation/ga-readiness-checklist.md` remains the source of truth
      for the required gate set, and the live workflows plus repository
      enforcement reference the exact gate names they actually require on
      `main`.
- [ ] IF-0-GAGOV-2 - Enforcement disposition contract: `main` is protected by
      branch protection or repository rulesets that enforce the required GA gate
      set, or `docs/validation/ga-governance-evidence.md` records a blocker
      with the exact missing repository setting, actor, and operator acceptance
      needed before GA can proceed.
- [ ] IF-0-GAGOV-3 - Release-channel policy contract: release automation,
      operator docs, and governance evidence all agree on prerelease/latest,
      Docker `latest`, tag mutation, auto-merge, and rollback behavior, and
      they explicitly state whether GitHub Latest is excluded until final GA
      release.
- [ ] IF-0-GAGOV-4 - Redacted evidence contract:
      `docs/validation/ga-governance-evidence.md` is the canonical GAGOV
      artifact and records only redacted metadata for repository settings,
      rulesets, release-channel state, and operator acceptance.

## Lane Index & Dependencies

- SL-0 - GAGOV governance contract tests; Depends on: GABASE; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Workflow and release-channel policy alignment; Depends on: SL-0; Blocks: SL-3, SL-4; Parallel-safe: yes
- SL-2 - GitHub governance enforcement and probe lane; Depends on: SL-0; Blocks: SL-3, SL-4; Parallel-safe: yes
- SL-3 - Operator governance docs alignment; Depends on: SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - GA governance evidence reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: GAGOV acceptance; Parallel-safe: no

## Lanes

### SL-0 - GAGOV Governance Contract Tests

- **Scope**: Freeze the GA-governance assertions before changing workflows,
  GitHub settings, or operator docs.
- **Owned files**: `tests/docs/test_gagov_governance_contract.py`
- **Interfaces provided**: IF-0-GAGOV-1, IF-0-GAGOV-2, IF-0-GAGOV-3, IF-0-GAGOV-4
- **Interfaces consumed**: `docs/validation/ga-readiness-checklist.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`,
  `docs/validation/release-governance-evidence.md`,
  `.github/workflows/release-automation.yml`,
  `.github/workflows/ci-cd-pipeline.yml`,
  `.github/workflows/container-registry.yml`,
  `.github/workflows/lockfile-check.yml`,
  `tests/docs/test_gabase_ga_readiness_contract.py`,
  `tests/docs/test_p25_release_checklist.py`,
  `tests/test_p25_release_gates.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a dedicated GAGOV contract test that requires a canonical
    `docs/validation/ga-governance-evidence.md` artifact, references the exact
    GABASE gate set, and asserts that operator docs state either enforced
    governance or an explicit blocker path.
  - test: Assert that the runbooks and evidence file record the live release
    channel distinction between the active RC release (`v1.2.0-rc5`) and
    GitHub Latest (`v2.15.0-alpha.1`) until final GA release changes it.
  - test: Assert that redacted evidence records repository settings, ruleset
    disposition, release automation policy, and operator acceptance without
    leaking secret-bearing CLI output.
  - impl: Keep this file additive and phase-specific so GABASE/P25 assertions
    remain lower-level supporting contracts rather than being rewritten in
    place.
  - verify: `uv run pytest tests/docs/test_gagov_governance_contract.py -v --no-cov`

### SL-1 - Workflow And Release-Channel Policy Alignment

- **Scope**: Align workflow-declared gate names and release-channel behavior to
  the frozen GABASE checklist without dispatching a release.
- **Owned files**: `.github/workflows/release-automation.yml`,
  `.github/workflows/ci-cd-pipeline.yml`,
  `.github/workflows/container-registry.yml`,
  `.github/workflows/lockfile-check.yml`
- **Interfaces provided**: IF-0-GAGOV-1 required gate names and workflow
  sources; IF-0-GAGOV-3 release-channel policy behavior
- **Interfaces consumed**: SL-0 governance assertions; GABASE checklist gate
  list; current RC/public-alpha release automation contract
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 plus the existing P25 workflow tests to confirm that the
    required gate set still matches the GABASE checklist and that the release
    preflight boundary remains explicit.
  - impl: If any workflow names, comments, or aggregator wiring drift from the
    GABASE gate list, restore them so the required GA-governance gate set is
    mechanically identifiable on `main`.
  - impl: Preserve the current non-dispatch behavior: prerelease tags stay
    prereleases, Docker `latest` stays stable-only, and no release mutation
    occurs in GAGOV.
  - impl: Make GitHub Latest policy explicit where practical in workflow-adjacent
    comments or test-visible metadata instead of leaving the exclusion as
    unstated operator knowledge.
  - verify: `uv run pytest tests/docs/test_gagov_governance_contract.py tests/test_p25_release_gates.py -v --no-cov`
  - verify: `rg -n 'Alpha Gate - |preflight-release-gates|release_type=custom|is_prerelease|docker_tags|ghcr.io/viperjuice/code-index-mcp:latest' .github/workflows tests/test_p25_release_gates.py tests/docs/test_gagov_governance_contract.py`

### SL-2 - GitHub Governance Enforcement And Probe Lane

- **Scope**: Apply or conclusively fail repository-side governance enforcement
  on `main` using metadata-only probes and redacted settings evidence.
- **Owned files**: none (GitHub repository settings, rulesets, and metadata probes only)
- **Interfaces provided**: live branch protection or ruleset disposition; exact
  blocker facts if GA governance cannot yet be enforced; release-channel probe
  results for SL-3 and SL-4
- **Interfaces consumed**: SL-0 governance assertions; GABASE checklist gate
  list; authenticated GitHub CLI metadata; current `v1.2.0-rc5` and GitHub
  Latest release state
- **Parallel-safe**: yes
- **Tasks**:
  - test: Run `gh repo view ViperJuice/Code-Index-MCP --json nameWithOwner,defaultBranchRef,visibility`.
  - test: Run `gh api repos/ViperJuice/Code-Index-MCP/branches/main --jq '{name, protected, protection_url}'`.
  - test: Run `gh api repos/ViperJuice/Code-Index-MCP/branches/main/protection` and
    `gh api repos/ViperJuice/Code-Index-MCP/rulesets` to determine whether the
    required gate set is already enforced.
  - test: Run `gh release view v1.2.0-rc5 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url`
    and `gh api repos/ViperJuice/Code-Index-MCP/releases/latest --jq '{tag_name, draft, prerelease, published_at, html_url}'`.
  - impl: If repository settings can be updated safely, apply the exact branch
    protection or ruleset configuration that enforces the required gate set on
    `main`.
  - impl: If repository enforcement cannot be applied because of GitHub product
    limits, missing admin authority, or another non-local prerequisite, record
    the blocker facts and required human action for SL-4 instead of guessing.
  - verify: Re-run the same metadata probes and confirm the recorded state
    matches the live repository disposition.

### SL-3 - Operator Governance Docs Alignment

- **Scope**: Make the GA-governance policy explicit in operator-facing docs
  without dispatching a release or claiming GA support.
- **Owned files**: `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`
- **Interfaces provided**: IF-0-GAGOV-2 and IF-0-GAGOV-3 as operator-readable
  policy and escalation rules
- **Interfaces consumed**: SL-0 governance assertions; SL-1 workflow policy;
  SL-2 live GitHub governance disposition;
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/release-governance-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Use SL-0 to fail first on missing GA-governance sections, blocker
    wording, or stale manual-enforcement text that is no longer accurate.
  - impl: Add or revise a GAGOV section in both runbooks that states the exact
    required gate set, the repository-enforcement disposition, and the operator
    response when governance is blocked outside the worktree.
  - impl: Make the release-channel policy explicit: `v1.2.0-rc5` remains the
    active prerelease baseline, GitHub Latest currently points at
    `v2.15.0-alpha.1`, and GitHub Latest is either intentionally excluded until
    final GA release or aligned by a separately recorded operator action.
  - impl: Document rollback and acceptance behavior in terms of the GABASE
    checklist and the canonical `docs/validation/ga-governance-evidence.md`
    artifact instead of leaving the policy split across older v4 evidence.
  - verify: `uv run pytest tests/docs/test_gagov_governance_contract.py tests/docs/test_p25_release_checklist.py -v --no-cov`
  - verify: `rg -n 'GAGOV|branch protection|ruleset|manual enforcement|blocked|v1\\.2\\.0-rc5|v2\\.15\\.0-alpha\\.1|GitHub Latest|auto_merge=false|Docker latest|ga-governance-evidence' docs/operations`

### SL-4 - GA Governance Evidence Reducer

- **Scope**: Reduce workflow policy, live GitHub governance state, and operator
  decisions into the canonical GAGOV evidence artifact.
- **Owned files**: `docs/validation/ga-governance-evidence.md`
- **Interfaces provided**: IF-0-GAGOV-2 and IF-0-GAGOV-4; canonical GAGOV
  evidence for GAOPS, GARC, and GAREL
- **Interfaces consumed**: SL-0 governance assertions; SL-1 workflow/release
  policy; SL-2 GitHub metadata or blocker facts; SL-3 operator-doc policy;
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/release-governance-evidence.md`,
  `docs/validation/rc5-release-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Write or update `docs/validation/ga-governance-evidence.md` only
    after SL-1 through SL-3 have settled the final governance disposition.
  - impl: Record repository identity, default branch, branch protection state,
    repository rulesets, required gate set, GitHub Latest state, active RC
    release state, release automation policy, Docker `latest` policy,
    auto-merge policy, rollback notes, and operator acceptance.
  - impl: If governance is blocked, record the exact blocker, the redacted
    access attempts or probes that proved it, and the required human action
    without embedding secret-bearing output.
  - impl: If governance is enforced, record the exact ruleset or branch
    protection configuration and the verification probes that prove it.
  - verify: `uv run pytest tests/docs/test_gagov_governance_contract.py tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py -v --no-cov`
  - verify: `rg -n 'Repository:|Default branch:|Branch protection|Repository rulesets|Required gates|GitHub Latest|v1\\.2\\.0-rc5|v2\\.15\\.0-alpha\\.1|auto_merge=false|Docker latest|Operator acceptance|Blocker' docs/validation/ga-governance-evidence.md`

## Verification

- `uv run pytest tests/docs/test_gagov_governance_contract.py -v --no-cov`
- `uv run pytest tests/docs/test_gagov_governance_contract.py tests/docs/test_p25_release_checklist.py tests/test_p25_release_gates.py -v --no-cov`
- `rg -n 'GAGOV|branch protection|ruleset|manual enforcement|blocked|GitHub Latest|v1\\.2\\.0-rc5|v2\\.15\\.0-alpha\\.1|auto_merge=false|Docker latest|ga-governance-evidence' docs/operations docs/validation .github/workflows`
- `gh repo view ViperJuice/Code-Index-MCP --json nameWithOwner,defaultBranchRef,visibility`
- `gh api repos/ViperJuice/Code-Index-MCP/branches/main --jq '{name, protected, protection_url}'`
- `gh api repos/ViperJuice/Code-Index-MCP/branches/main/protection`
- `gh api repos/ViperJuice/Code-Index-MCP/rulesets`
- `gh release view v1.2.0-rc5 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url`
- `gh api repos/ViperJuice/Code-Index-MCP/releases/latest --jq '{tag_name, draft, prerelease, published_at, html_url}'`
- `git status --short -- plans/phase-plan-v5-gagov.md docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md docs/validation/ga-governance-evidence.md tests/docs/test_gagov_governance_contract.py .github/workflows/release-automation.yml .github/workflows/ci-cd-pipeline.yml .github/workflows/container-registry.yml .github/workflows/lockfile-check.yml`

## Acceptance Criteria

- [ ] `main` is protected by repository rulesets or branch protection that
      enforces the GABASE-required gate set, or
      `docs/validation/ga-governance-evidence.md` records a precise blocker
      that prevents GA governance from being enforced.
- [ ] Required workflow job names and aggregator behavior still match the
      GABASE checklist and are test-covered without dispatching a release.
- [ ] Operator docs and evidence agree on prerelease/latest, Docker `latest`,
      auto-merge, and rollback policy for the active RC/public-alpha baseline.
- [ ] GitHub Latest is either intentionally excluded until final GA release or
      explicitly aligned by a recorded operator action.
- [ ] `docs/validation/ga-governance-evidence.md` exists as the canonical
      redacted governance artifact for downstream GA phases.

## Automation

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gagov.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gagov.md
  artifact_state: staged
```
