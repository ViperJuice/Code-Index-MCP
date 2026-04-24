---
phase_loop_plan_version: 1
phase: GABASE
roadmap: specs/phase-plans-v5.md
roadmap_sha256: 6c3ef37eac6b52116804f765470905ca8f8ec4333c306a57c9ba1b8a178b4dc5
---
# GABASE: GA Criteria Freeze

## Context

GABASE is the first phase in the v5 GA-hardening roadmap. It is an
interface-freeze phase: the goal is to define the GA contract before changing
release automation, GitHub settings, runtime code, or support behavior.

Current repo state gathered during planning:

- The checkout is on `main` at `8d08545`.
- `specs/phase-plans-v5.md` is already staged in this worktree
  (`git status --short -- specs/phase-plans-v5.md` returned
  `A  specs/phase-plans-v5.md`), so it must be treated as user-owned baseline
  context rather than rewritten during this phase.
- `.codex/phase-loop/state.json` already selects `GABASE` from a prior dry-run
  and records the same roadmap SHA used in this plan.
- `docs/validation/ga-closeout-decision.md`,
  `docs/validation/release-governance-evidence.md`,
  `docs/validation/secondary-tool-readiness-evidence.md`, and
  `docs/validation/rc5-release-evidence.md` already define the current
  RC/public-alpha baseline that GABASE must classify as input evidence.
- `docs/SUPPORT_MATRIX.md`, `README.md`, `docs/GETTING_STARTED.md`,
  `docs/MCP_CONFIGURATION.md`, `docs/DOCKER_GUIDE.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`, and the existing docs tests already
  carry RC/public-alpha vocabulary that downstream GA phases must reuse rather
  than replace ad hoc.
- `docs/validation/ga-readiness-checklist.md` does not exist yet and is the
  main new artifact required by this phase.

## Interface Freeze Gates

- [ ] IF-0-GABASE-1 - Checklist schema contract:
      `docs/validation/ga-readiness-checklist.md` is the canonical GA readiness
      artifact and contains explicit sections for `Release boundary`,
      `Support tiers`, `Required gates`, `Evidence map`,
      `Rollback expectations`, and `Non-GA surfaces`, while preserving
      `v1.2.0-rc5` as the active RC/public-alpha baseline.
- [ ] IF-0-GABASE-2 - Evidence vocabulary contract: the checklist classifies
      `docs/validation/rc5-release-evidence.md`,
      `docs/validation/release-governance-evidence.md`,
      `docs/validation/secondary-tool-readiness-evidence.md`, and
      `docs/validation/ga-closeout-decision.md` as input evidence, and names
      `docs/validation/ga-governance-evidence.md`,
      `docs/validation/ga-e2e-evidence.md`,
      `docs/validation/ga-operations-evidence.md`,
      `docs/validation/ga-rc-evidence.md`,
      `docs/validation/ga-final-decision.md`, and
      `docs/validation/ga-release-evidence.md` as refresh evidence required
      before a GA ship decision.
- [ ] IF-0-GABASE-3 - Pre-GA docs truth contract: `README.md`,
      `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`,
      `docs/DOCKER_GUIDE.md`, and the operator runbooks keep `1.2.0-rc5` in
      beta/public-alpha wording, reject GA or stable-release claims before
      `GAREL`, and route support claims to `docs/SUPPORT_MATRIX.md` or the GA
      readiness checklist.
- [ ] IF-0-GABASE-4 - Shared readiness vocabulary contract:
      `docs/SUPPORT_MATRIX.md`, the operator runbooks, and the checklist use
      the same support-tier labels (`public-alpha`, `beta`, `GA`,
      `experimental`, `unsupported`, `disabled-by-default`) and preserve the
      v3 repository-topology contract (`one registered worktree per git common
      directory`, tracked/default branch indexing, `index_unavailable`, and
      `safe_fallback: "native_search"`).

## Lane Index & Dependencies

- SL-0 - GABASE contract tests; Depends on: GACLOSE; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Public docs vocabulary alignment; Depends on: SL-0; Blocks: SL-4; Parallel-safe: yes
- SL-2 - Support matrix vocabulary alignment; Depends on: SL-0; Blocks: SL-4; Parallel-safe: yes
- SL-3 - Operator runbook readiness alignment; Depends on: SL-0; Blocks: SL-4; Parallel-safe: yes
- SL-4 - GA readiness checklist reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: GABASE acceptance; Parallel-safe: no

## Lanes

### SL-0 - GABASE Contract Tests

- **Scope**: Freeze the GA checklist shape, evidence vocabulary, and pre-GA
  docs truth assertions before editing docs.
- **Owned files**: `tests/docs/test_gabase_ga_readiness_contract.py`
- **Interfaces provided**: IF-0-GABASE-1, IF-0-GABASE-2, IF-0-GABASE-3, IF-0-GABASE-4
- **Interfaces consumed**: `docs/validation/ga-closeout-decision.md`,
  `docs/validation/rc5-release-evidence.md`,
  `docs/validation/release-governance-evidence.md`,
  `docs/validation/secondary-tool-readiness-evidence.md`,
  `docs/SUPPORT_MATRIX.md`, `README.md`, `docs/GETTING_STARTED.md`,
  `docs/MCP_CONFIGURATION.md`, `docs/DOCKER_GUIDE.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`, `tests/docs/test_p23_doc_truth.py`,
  `tests/docs/test_p25_release_checklist.py`,
  `tests/docs/test_p34_public_alpha_recut.py`,
  `tests/docs/test_gaclose_evidence_closeout.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add assertions that `docs/validation/ga-readiness-checklist.md`
    exists and exposes the exact required section headings, evidence classes,
    tier labels, and topology constraints.
  - test: Add assertions that active docs keep `1.2.0-rc5` in beta/public-alpha
    language and do not introduce `ship GA`, `stable release`, or equivalent
    launch wording before `GAREL`.
  - test: Add assertions that the checklist distinguishes input evidence from
    refresh evidence and references the exact artifact paths used by later
    phases.
  - impl: Keep this test file self-contained and additive so existing P23, P25,
    P34, and GACLOSE tests remain the lower-level contracts.
  - verify: `uv run pytest tests/docs/test_gabase_ga_readiness_contract.py -v --no-cov`

### SL-1 - Public Docs Vocabulary Alignment

- **Scope**: Align customer-facing docs to the frozen GA-readiness vocabulary
  without changing the current RC/public-alpha product contract.
- **Owned files**: `README.md`, `docs/GETTING_STARTED.md`,
  `docs/MCP_CONFIGURATION.md`, `docs/DOCKER_GUIDE.md`
- **Interfaces provided**: IF-0-GABASE-3 for customer-facing docs
- **Interfaces consumed**: SL-0 assertions; current `1.2.0-rc5` package and
  install contract; `docs/SUPPORT_MATRIX.md`; `docs/validation/ga-closeout-decision.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use the SL-0 contract tests together with existing P23/P34 docs tests
    to identify stale GA, stable, or support-tier wording.
  - impl: Route support or readiness claims to `docs/SUPPORT_MATRIX.md` and the
    GA readiness checklist instead of duplicating partial GA criteria in each
    doc.
  - impl: Keep current `1.2.0-rc5`, `index-it-mcp`, and
    `ghcr.io/viperjuice/code-index-mcp` references intact while clarifying that
    GA remains a future decision artifact rather than a present release state.
  - impl: Do not introduce release automation, GitHub settings, or support-tier
    expansion changes in this lane.
  - verify: `uv run pytest tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_p23_doc_truth.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov`
  - verify: `rg -n "ship GA|stable release|generally available|public-alpha|beta|1\\.2\\.0-rc5|SUPPORT_MATRIX\\.md|ga-readiness-checklist" README.md docs/GETTING_STARTED.md docs/MCP_CONFIGURATION.md docs/DOCKER_GUIDE.md`

### SL-2 - Support Matrix Vocabulary Alignment

- **Scope**: Make the support matrix the canonical source for frozen support
  tiers and topology language that downstream GA phases will consume.
- **Owned files**: `docs/SUPPORT_MATRIX.md`
- **Interfaces provided**: IF-0-GABASE-4
- **Interfaces consumed**: SL-0 assertions; current plugin/runtime facts
  already documented in the support matrix; `docs/validation/ga-closeout-decision.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 and existing P23/GACLOSE docs assertions to locate any
    support-tier labels or topology wording that diverge from the planned GA
    vocabulary.
  - impl: Add or tighten the support-tier guidance so the matrix explicitly
    matches the labels GAGOV, GASUPPORT, GAE2E, and GAOPS will consume.
  - impl: Preserve the current v3 repository-topology limits and current plugin
    facts; do not broaden support claims or alter runtime behavior in this
    phase.
  - impl: Point readers at the GA readiness checklist for release-boundary and
    evidence requirements instead of embedding a second checklist here.
  - verify: `uv run pytest tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_p23_doc_truth.py -v --no-cov`
  - verify: `rg -n "public-alpha|beta|GA|experimental|unsupported|disabled-by-default|one registered worktree|tracked/default branch|index_unavailable|safe_fallback: \\\"native_search\\\"" docs/SUPPORT_MATRIX.md`

### SL-3 - Operator Runbook Readiness Alignment

- **Scope**: Align operator docs to the frozen GA-readiness contract without
  changing current manual-enforcement or RC release behavior.
- **Owned files**: `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`
- **Interfaces provided**: IF-0-GABASE-3, IF-0-GABASE-4 for operator-facing
  workflows
- **Interfaces consumed**: SL-0 assertions;
  `docs/validation/ga-closeout-decision.md`,
  `docs/validation/release-governance-evidence.md`,
  `docs/validation/secondary-tool-readiness-evidence.md`,
  `docs/validation/rc5-release-evidence.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 plus existing release-checklist tests to identify any
    operator wording that skips the GA checklist or implies that GA governance
    is already enforced.
  - impl: Add a concise GA-hardening intake section that points future operators
    to the canonical checklist and names the downstream evidence phases without
    introducing new release-dispatch steps.
  - impl: Preserve the current manual-enforcement and RC/public-alpha
    governance language until GAGOV changes it explicitly.
  - impl: Keep rollback expectations and non-GA surfaces aligned with the
    checklist vocabulary rather than inventing runbook-only rules.
  - verify: `uv run pytest tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_p25_release_checklist.py tests/docs/test_gaclose_evidence_closeout.py -v --no-cov`
  - verify: `rg -n "GABASE|ga-readiness-checklist|manual enforcement|public-alpha|beta|GA|rollback|non-GA" docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md`

### SL-4 - GA Readiness Checklist Reducer

- **Scope**: Reduce the frozen doc vocabulary and existing v4 evidence into the
  canonical GA readiness checklist artifact.
- **Owned files**: `docs/validation/ga-readiness-checklist.md`
- **Interfaces provided**: IF-0-GABASE-1, IF-0-GABASE-2, canonical GABASE
  checklist for downstream phases
- **Interfaces consumed**: SL-0 test contract; SL-1 customer-doc wording;
  SL-2 support-tier vocabulary; SL-3 operator vocabulary;
  `docs/validation/ga-closeout-decision.md`,
  `docs/validation/rc5-release-evidence.md`,
  `docs/validation/release-governance-evidence.md`,
  `docs/validation/secondary-tool-readiness-evidence.md`;
  roadmap phases `GAGOV`, `GASUPPORT`, `GAE2E`, `GAOPS`, `GARC`, and `GAREL`
- **Parallel-safe**: no
- **Tasks**:
  - test: Write the checklist only after SL-1 through SL-3 have settled the
    exact vocabulary that the checklist will freeze.
  - impl: Create `docs/validation/ga-readiness-checklist.md` with explicit
    sections for release boundary, support tiers, required gates, evidence map,
    rollback expectations, and non-GA surfaces.
  - impl: Classify which current v4 artifacts are input evidence versus which
    GA-hardening artifacts must be refreshed later, and map each refresh
    artifact to the downstream roadmap phase that owns it.
  - impl: Preserve the current v3 repository-topology limits and current
    RC/public-alpha baseline without mutating release automation, GitHub
    settings, runtime behavior, or support scope.
  - verify: `uv run pytest tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_p23_doc_truth.py tests/docs/test_p25_release_checklist.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov`
  - verify: `rg -n "Release boundary|Support tiers|Required gates|Evidence map|Rollback expectations|Non-GA surfaces|v1\\.2\\.0-rc5|ga-governance-evidence|ga-e2e-evidence|ga-operations-evidence|ga-rc-evidence|ga-final-decision|ga-release-evidence" docs/validation/ga-readiness-checklist.md`

## Verification

- `uv run pytest tests/docs/test_gabase_ga_readiness_contract.py -v --no-cov`
- `uv run pytest tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_p23_doc_truth.py tests/docs/test_p25_release_checklist.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov`
- `uv run pytest tests/docs -v --no-cov`
- `rg -n "ship GA|stable release|generally available|public-alpha|beta|GA|1\\.2\\.0-rc5|one registered worktree|tracked/default branch|index_unavailable|safe_fallback: \\\"native_search\\\"" README.md docs tests`

## Acceptance Criteria

- [ ] `docs/validation/ga-readiness-checklist.md` exists as the canonical GA
      checklist and names the release boundary, support tiers, required gates,
      rollback expectations, non-GA surfaces, and current `v1.2.0-rc5`
      baseline.
- [ ] Docs tests prevent GA or stable-release claims from appearing in active
      docs before the final GA decision phase.
- [ ] The checklist preserves the v3 repository-topology limits and does not
      broaden support or runtime behavior in GABASE.
- [ ] The checklist classifies current v4 evidence as input evidence and names
      the later GA-hardening artifacts that must be refreshed before `ship GA`.
- [ ] `README.md`, the getting-started/install docs, the support matrix, and
      the operator runbooks share one readiness vocabulary that downstream
      phases can consume without redefining tier labels or gate names.

## Automation

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gabase.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gabase.md
  artifact_state: staged
```
