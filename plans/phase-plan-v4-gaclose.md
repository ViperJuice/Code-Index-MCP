# GACLOSE: GA Hardening Evidence Closeout

> Plan doc produced by `codex-plan-phase specs/phase-plans-v4.md GACLOSE`
> on 2026-04-24.
> Source roadmap `specs/phase-plans-v4.md` is tracked and clean in this
> worktree (`git status --short -- specs/phase-plans-v4.md` produced no
> output).

## Context

GACLOSE is the terminal v4 decision and evidence phase. It depends on the
published RC5 release evidence, the RELGOV release-governance evidence, and the
TOOLRDY secondary-tool readiness evidence. It must not introduce GA claims or
new feature work; it should decide whether to stay on RC/public-alpha, cut a
follow-up RC, or start a separate GA-hardening roadmap.

Current repo state gathered during planning:

- The checkout is on `main` at `8d08545`.
- `plans/phase-plan-v4-gaclose.md` did not exist before this planning run.
- PMCP catalog search did not expose a running `code-index-mcp` tool surface in
  this session, so native `rg` and targeted file reads were used for planning.
- `docs/validation/rc5-release-evidence.md` exists and records a successful
  `v1.2.0-rc5` release workflow with GitHub release, PyPI artifacts, and GHCR
  image published.
- `docs/validation/release-governance-evidence.md` exists in the current staged
  RELGOV artifacts and records manual public-alpha gate enforcement, no branch
  protection/rulesets, active RC contract `v1.2.0-rc5`, and GitHub Latest
  pointing at `v2.15.0-alpha.1`.
- `docs/validation/secondary-tool-readiness-evidence.md` exists in the current
  staged TOOLRDY artifacts and records passing secondary-tool readiness tests
  plus `make alpha-production-matrix`.
- The worktree contains staged and unstaged RELGOV/TOOLRDY implementation
  artifacts. GACLOSE execution must treat those as upstream/user-owned inputs,
  reread them before editing, and avoid folding unrelated cleanup into this
  closeout.

## Interface Freeze Gates

- [ ] IF-0-GACLOSE-1 - Evidence intake contract:
      `docs/validation/ga-closeout-decision.md` links and summarizes
      `docs/validation/rc5-release-evidence.md`,
      `docs/validation/release-governance-evidence.md`, and
      `docs/validation/secondary-tool-readiness-evidence.md`, including the
      observed commit, timestamps, release identity, governance disposition, and
      secondary-tool readiness disposition.
- [ ] IF-0-GACLOSE-2 - Active public-surface release contract: README,
      getting-started, Docker, MCP configuration, changelog, and operator
      runbooks contain no stale active-release claims, no active RC4 installer
      guidance, and no instruction that treats GitHub Latest as the RC policy
      source.
- [ ] IF-0-GACLOSE-3 - Support-tier contract: `docs/SUPPORT_MATRIX.md`
      explicitly distinguishes public-alpha, beta, and GA claims; keeps the v3
      repository-topology limits; and does not imply unrestricted
      multi-worktree, multi-branch, or universal language/runtime support.
- [ ] IF-0-GACLOSE-4 - Post-TOOLRDY production-matrix contract:
      `make alpha-production-matrix` passes after the TOOLRDY changes that
      GACLOSE consumes, and the final decision artifact records the command and
      result.
- [ ] IF-0-GACLOSE-5 - Decision vocabulary contract: the final decision
      artifact states exactly one of `stay on RC/public-alpha`, `cut a
      follow-up RC`, or `start a GA hardening roadmap`, and records the
      evidence-backed rationale and next command.
- [ ] IF-0-GACLOSE-6 - Validation artifact hygiene contract: any new
      `docs/validation/*.md` closeout artifact follows the repo's historical
      artifact banner/triage expectations, records redacted metadata only, and
      contains no secret values or raw credential-bearing CLI output.

## Lane Index & Dependencies

- SL-0 - GACLOSE contract tests; Depends on: RC5REL, RELGOV, TOOLRDY; Blocks: SL-1, SL-2, SL-3, SL-5; Parallel-safe: no
- SL-1 - Public release-surface cleanup; Depends on: SL-0; Blocks: SL-4, SL-5; Parallel-safe: yes
- SL-2 - Support-tier matrix cleanup; Depends on: SL-0; Blocks: SL-4, SL-5; Parallel-safe: yes
- SL-3 - Evidence-link runbook cleanup; Depends on: SL-0; Blocks: SL-4, SL-5; Parallel-safe: no
- SL-4 - Post-TOOLRDY verification pass; Depends on: SL-1, SL-2, SL-3; Blocks: SL-5; Parallel-safe: no
- SL-5 - GA closeout decision reducer; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4; Blocks: GACLOSE acceptance; Parallel-safe: no

Lane DAG:

```text
RC5REL + RELGOV + TOOLRDY
  -> SL-0
       -> SL-1 --.
       -> SL-2 ----> SL-4 -> SL-5 -> GACLOSE acceptance
       -> SL-3 --'
```

## Lanes

### SL-0 - GACLOSE Contract Tests

- **Scope**: Freeze the closeout evidence, public-surface, support-tier, and
  final-decision assertions before editing docs.
- **Owned files**: `tests/docs/test_gaclose_evidence_closeout.py`
- **Interfaces provided**: IF-0-GACLOSE-1 through IF-0-GACLOSE-6 as executable
  docs/evidence assertions
- **Interfaces consumed**: pre-existing RC5 release evidence; staged RELGOV
  evidence; staged TOOLRDY evidence; P23 docs truth tests; P34 public-alpha
  recut tests; release metadata tests
- **Parallel-safe**: no
- **Tasks**:
  - test: Add assertions that `docs/validation/ga-closeout-decision.md`
    exists, links the three prerequisite evidence artifacts, records the
    post-TOOLRDY production matrix result, and states exactly one allowed final
    decision.
  - test: Add assertions that public docs and installer flows contain the
    active `1.2.0-rc5` / `v1.2.0-rc5` contract, do not contain active
    `1.2.0-rc4` or `v1.2.0-rc4` instructions, and describe GitHub Latest as
    non-authoritative for the RC track when mentioned.
  - test: Add assertions that `docs/SUPPORT_MATRIX.md` names public-alpha,
    beta, and GA claim boundaries while preserving one registered worktree per
    git common directory, tracked/default branch indexing, readiness gating,
    `index_unavailable`, and `safe_fallback: "native_search"`.
  - test: Add assertions that the new validation artifact has the required
    historical banner/triage relationship used by existing validation docs.
  - impl: Keep the new test file self-contained so existing P23/P25/P34 tests
    remain the lower-level contracts.
  - verify: `uv run pytest tests/docs/test_gaclose_evidence_closeout.py -v --no-cov`

### SL-1 - Public Release-Surface Cleanup

- **Scope**: Remove stale or ambiguous active-release language from customer
  and installer-facing docs without changing operator policy.
- **Owned files**: `README.md`, `docs/GETTING_STARTED.md`,
  `docs/DOCKER_GUIDE.md`, `docs/MCP_CONFIGURATION.md`, `CHANGELOG.md`
- **Interfaces provided**: IF-0-GACLOSE-2 for public/customer docs
- **Interfaces consumed**: SL-0 assertions; RC5 release evidence; RELGOV
  release-channel disposition; existing P23 and P34 docs contracts
- **Parallel-safe**: yes
- **Tasks**:
  - test: Run the SL-0 public-surface tests and existing P23/P34 docs tests to
    identify stale active-release claims.
  - impl: Clarify any "latest" install wording so it refers to artifact/index
    sync where appropriate and does not imply GitHub Latest is the RC package
    policy source.
  - impl: Preserve `1.2.0-rc5`, `v1.2.0-rc5`, `index-it-mcp`, and
    `ghcr.io/viperjuice/code-index-mcp` as the active RC/public-alpha package
    identifiers.
  - impl: Remove or reframe any remaining active GA, production-ready,
    universal language support, unrestricted multi-worktree, or unrestricted
    multi-branch claims.
  - impl: Keep historical changelog entries historical; do not rewrite release
    history except to add a GACLOSE note if needed.
  - verify: `uv run pytest tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_p23_doc_truth.py tests/docs/test_p34_public_alpha_recut.py tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n 'v1\.2\.0-rc4|1\.2\.0-rc4|unrestricted multi-worktree|unrestricted multi-branch|indexes every branch|Production-Ready|fully operational|Download latest release|GitHub Latest' README.md CHANGELOG.md docs/GETTING_STARTED.md docs/DOCKER_GUIDE.md docs/MCP_CONFIGURATION.md`

### SL-2 - Support-Tier Matrix Cleanup

- **Scope**: Make the canonical support matrix explicit about public-alpha,
  beta, and GA boundaries.
- **Owned files**: `docs/SUPPORT_MATRIX.md`
- **Interfaces provided**: IF-0-GACLOSE-3
- **Interfaces consumed**: SL-0 assertions; existing language/plugin registry
  facts already referenced by the support matrix; P23 docs truth contract;
  TOOLRDY readiness evidence
- **Parallel-safe**: yes
- **Tasks**:
  - test: Run the SL-0 support-tier assertions and existing support matrix
    tests before editing.
  - impl: Add a concise claim-tier section that states the current package is
    RC/public-alpha beta status, not GA; names what would be needed before GA
    claims; and preserves the current repository-topology limitations.
  - impl: Keep the canonical language table's required columns and current
    language/plugin rows intact unless a row contains a stale status claim.
  - impl: Link secondary-tool readiness evidence only as readiness evidence,
    not as a GA support expansion.
  - verify: `uv run pytest tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_p23_doc_truth.py tests/docs/test_p34_public_alpha_recut.py -v --no-cov`
  - verify: `rg -n 'public-alpha|public alpha|beta|GA|one registered worktree|tracked/default branch|index_unavailable|safe_fallback|native_search' docs/SUPPORT_MATRIX.md`

### SL-3 - Evidence-Link Runbook Cleanup

- **Scope**: Give operators one runbook/checklist path from RC5, RELGOV, and
  TOOLRDY evidence into the GACLOSE decision.
- **Owned files**: `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`
- **Interfaces provided**: IF-0-GACLOSE-1, IF-0-GACLOSE-2, and
  IF-0-GACLOSE-5 as operator-facing workflow
- **Interfaces consumed**: SL-0 assertions; RC5 release evidence; RELGOV
  governance evidence; TOOLRDY secondary-tool readiness evidence
- **Parallel-safe**: no
- **Tasks**:
  - test: Use SL-0 assertions to identify missing links or ambiguous decision
    language in the runbooks.
  - impl: Add a GACLOSE checklist section that names the three prerequisite
    evidence artifacts and the post-TOOLRDY production matrix command.
  - impl: State that GACLOSE chooses exactly one of staying on
    RC/public-alpha, cutting a follow-up RC, or starting a GA-hardening roadmap.
  - impl: Preserve RELGOV policy: manual enforcement remains the public-alpha
    disposition unless branch protection/rulesets change in a separate
    governance action.
  - impl: Do not add a GA launch procedure or announcement decision.
  - verify: `uv run pytest tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_p25_release_checklist.py -v --no-cov`
  - verify: `rg -n 'GACLOSE|rc5-release-evidence|release-governance-evidence|secondary-tool-readiness-evidence|alpha-production-matrix|stay on RC/public-alpha|follow-up RC|GA hardening roadmap' docs/operations`

### SL-4 - Post-TOOLRDY Verification Pass

- **Scope**: Rerun the closeout verification set after docs cleanup and record
  the result for the decision reducer.
- **Owned files**: none
- **Interfaces provided**: IF-0-GACLOSE-4 verification result for SL-5
- **Interfaces consumed**: SL-1 public docs; SL-2 support matrix; SL-3
  runbooks; TOOLRDY implementation and evidence state
- **Parallel-safe**: no
- **Tasks**:
  - test: Run `uv run pytest tests/docs tests/smoke tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov`.
  - test: Run `make alpha-production-matrix`.
  - test: Run the stale-claim `rg` sweep from the roadmap GACLOSE verification
    block against README, changelog, docs, and scripts.
  - impl: No file edits in this lane; capture command, UTC timestamp, commit,
    and pass/fail result for SL-5.
  - verify: no additional command beyond the lane commands.

### SL-5 - GA Closeout Decision Reducer

- **Scope**: Reduce prerequisite evidence, docs cleanup, and verification
  results into the final v4 closeout artifact.
- **Owned files**: `docs/validation/ga-closeout-decision.md`,
  `docs/HISTORICAL-ARTIFACTS-TRIAGE.md`
- **Interfaces provided**: IF-0-GACLOSE-1, IF-0-GACLOSE-4, IF-0-GACLOSE-5,
  IF-0-GACLOSE-6, and terminal v4 decision output
- **Interfaces consumed**: SL-0 test contract; SL-1 public release-surface
  findings; SL-2 support-tier matrix; SL-3 runbook links; SL-4 verification
  results; RC5 release evidence; RELGOV governance evidence; TOOLRDY secondary
  readiness evidence
- **Parallel-safe**: no
- **Tasks**:
  - test: Create or update the decision artifact only after SL-1 through SL-4
    have terminal outputs.
  - impl: Add `docs/validation/ga-closeout-decision.md` with the required
    historical banner, source evidence links, post-TOOLRDY verification result,
    risk disposition, and exactly one final decision.
  - impl: If the decision is `stay on RC/public-alpha`, list the concrete
    blockers to GA and the recommended next phase/roadmap action. If the
    decision is `cut a follow-up RC`, name the required follow-up RC scope. If
    the decision is `start a GA hardening roadmap`, point to the roadmap-builder
    command to create it.
  - impl: Append the GACLOSE decision artifact to
    `docs/HISTORICAL-ARTIFACTS-TRIAGE.md` without disturbing existing staged
    RELGOV/TOOLRDY rows.
  - impl: Do not include secrets, credential payloads, raw environment values,
    or raw CLI output containing tokens.
  - verify: `uv run pytest tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_p8_historical_sweep.py -v --no-cov`
  - verify: `rg -n 'GACLOSE|RC5 Release Evidence|Release Governance Evidence|Secondary Tool Readiness Evidence|alpha-production-matrix|stay on RC/public-alpha|cut a follow-up RC|start a GA hardening roadmap' docs/validation/ga-closeout-decision.md docs/HISTORICAL-ARTIFACTS-TRIAGE.md`

## Verification

Planning-only status: not run.

Lane-specific commands:

```bash
uv run pytest tests/docs/test_gaclose_evidence_closeout.py -v --no-cov
uv run pytest tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_p23_doc_truth.py tests/docs/test_p34_public_alpha_recut.py tests/test_release_metadata.py -v --no-cov
uv run pytest tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_p25_release_checklist.py -v --no-cov
uv run pytest tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_p8_historical_sweep.py -v --no-cov
rg -n 'GACLOSE|rc5-release-evidence|release-governance-evidence|secondary-tool-readiness-evidence|alpha-production-matrix|stay on RC/public-alpha|follow-up RC|GA hardening roadmap' docs/operations docs/validation/ga-closeout-decision.md docs/HISTORICAL-ARTIFACTS-TRIAGE.md
```

Whole-phase regression commands:

```bash
uv run pytest tests/docs tests/smoke tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
make alpha-production-matrix
rg -n 'v1\.2\.0-rc4|1\.2\.0-rc4|unrestricted multi-worktree|unrestricted multi-branch|indexes every branch|GitHub Latest|Download latest release' README.md CHANGELOG.md docs scripts
```

## Acceptance Criteria

- [ ] Public docs and installer flows no longer contain stale active-release
      claims or active RC4 install guidance.
- [ ] `docs/SUPPORT_MATRIX.md` distinguishes public-alpha, beta, and GA claim
      boundaries while preserving v3 topology limits and readiness vocabulary.
- [ ] Operator runbooks or release checklists link RC5 release evidence, RELGOV
      governance evidence, TOOLRDY secondary-tool readiness evidence, and the
      GACLOSE decision artifact.
- [ ] The post-TOOLRDY production matrix passes and the result is recorded in
      the final decision artifact.
- [ ] `docs/validation/ga-closeout-decision.md` states exactly one of
      `stay on RC/public-alpha`, `cut a follow-up RC`, or `start a GA hardening
      roadmap`.
- [ ] The GACLOSE decision artifact is included in historical/validation
      artifact hygiene, contains redacted metadata only, and introduces no GA
      launch claim.

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v4-gaclose.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v4-gaclose.md
  artifact_state: staged
```
