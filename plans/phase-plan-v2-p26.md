# P26: Private Alpha Evidence & Public Alpha Decision

> Plan doc produced by `codex-plan-phase P26` against `specs/phase-plans-v2.md` on 2026-04-22.
> P26 consumes the P25 blocking release gate contract and produces IF-0-P26-1 for the public-alpha go/no-go decision.

## Context

P26 is the validation phase for the `1.2.0-rc3` public-alpha candidate. P21-P25 made the release metadata, dependency source of truth, wheel/container smoke paths, support matrix, sandbox degradation behavior, and public-alpha CI gates explicit. P26 should not reopen those contracts unless private-alpha evidence proves a release-blocking bug.

The current repo already has useful inputs:

- P25 defines the blocking gate names in `plans/phase-plan-v2-p25.md` and documents them in `docs/operations/deployment-runbook.md`.
- P22 release smoke exists in `scripts/release_smoke.py`, `make release-smoke`, and `make release-smoke-container`.
- Benchmark and retrieval runners exist under `scripts/run_e2e_retrieval_validation.py`, `scripts/run_mcp_vs_native_benchmark.py`, `scripts/run_matrix_benchmark.py`, and `scripts/run_production_benchmark.py`.
- Existing validation reports live in `docs/validation/`, and benchmark outputs live in `docs/benchmarks/`.
- Local/private output is already ignored through `data/`, `test_repos/`, `tests/fixtures/repos/`, `.indexes/`, and similar entries, but P26 needs a named raw-evidence output path so private repository data is not accidentally committed.

P26 should add a repeatable private-alpha evidence harness and a redacted decision record. Raw logs, absolute paths, repository names, source snippets, and customer/private metadata stay out of git. The committed artifacts should contain fixture categories, aggregate timings, pass/fail classifications, issue IDs, and the final go/no-go decision.

## Interface Freeze Gates

- [ ] IF-0-P26-1 - Alpha evidence contract: raw private-alpha evidence is written only under ignored `private-alpha-evidence/`, while committed redacted evidence uses `docs/validation/private-alpha-decision.md` and `docs/validation/private-alpha-evidence.schema.json`.
- [ ] IF-0-P26-2 - Fixture coverage contract: the evidence schema requires exactly these fixture categories: `python_repo`, `typescript_js_repo`, `mixed_docs_code_repo`, `multi_repo_workspace`, and `large_ignored_vendor_repo`.
- [ ] IF-0-P26-3 - Measurement contract: each fixture record captures install time, first index time, p50/p95 query latency, result quality notes, log noise classification, branch/default-branch behavior, rollback/rebuild behavior, and a blocker classification.
- [ ] IF-0-P26-4 - Public-alpha decision contract: the redacted decision record must classify every known issue as `public_alpha_blocker`, `documented_limitation`, or `post_alpha_backlog`, and must record exactly one final decision: `go`, `no_go`, or `conditional_go`.
- [ ] IF-0-P26-5 - Release-note truth contract: README and CHANGELOG public-alpha text must name the supported install paths, support matrix, beta warnings, rollback instructions, and the P26 decision artifact.

## Lane Index & Dependencies

- SL-0 - Private evidence boundary and contract tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4, SL-5; Parallel-safe: no
- SL-1 - Evidence harness; Depends on: SL-0; Blocks: SL-3, SL-4, SL-6; Parallel-safe: yes
- SL-2 - Redacted evidence templates and schema; Depends on: SL-0; Blocks: SL-3, SL-4, SL-5, SL-6; Parallel-safe: yes
- SL-3 - Private-alpha execution record; Depends on: SL-1, SL-2; Blocks: SL-4, SL-5, SL-6; Parallel-safe: no
- SL-4 - Operator go/no-go runbooks; Depends on: SL-1, SL-2, SL-3; Blocks: SL-5, SL-6; Parallel-safe: no
- SL-5 - Public-alpha release note surfaces; Depends on: SL-2, SL-3, SL-4; Blocks: SL-6; Parallel-safe: no
- SL-6 - Final P26 audit; Depends on: SL-1, SL-2, SL-3, SL-4, SL-5; Blocks: public alpha or v3 blocker roadmap; Parallel-safe: no

Lane DAG:

```text
SL-0
 ├─> SL-1 ─┐
 └─> SL-2 ─┼─> SL-3 ─> SL-4 ─> SL-5 ─> SL-6
           └───────────────┘
```

## Lanes

### SL-0 - Private Evidence Boundary And Contract Tests

- **Scope**: Freeze the P26 evidence boundaries and assertions before any harness or documentation work depends on them.
- **Owned files**: `.gitignore`, `tests/test_p26_alpha_evidence.py`, `tests/docs/test_p26_public_alpha_decision.py`
- **Interfaces provided**: IF-0-P26-1 through IF-0-P26-5 executable assertions; ignored raw output path `private-alpha-evidence/`
- **Interfaces consumed**: P25 required gate names from `tests/test_p25_release_gates.py`; P23 docs truth patterns from `tests/docs/test_p23_doc_truth.py`; existing release smoke contract in `tests/smoke/test_release_smoke_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add assertions that `.gitignore` ignores `private-alpha-evidence/` and does not ignore `docs/validation/private-alpha-decision.md` or `docs/validation/private-alpha-evidence.schema.json`.
  - test: Add schema tests requiring the five fixture categories from IF-0-P26-2 and all measurement fields from IF-0-P26-3.
  - test: Add docs tests requiring the decision record to classify issues into the three IF-0-P26-4 buckets and record exactly one final decision.
  - test: Add release-surface assertions that README and CHANGELOG mention the P26 decision artifact, install paths, support matrix, beta warnings, and rollback instructions.
  - impl: Add the ignored raw evidence path to `.gitignore`.
  - verify: `uv run pytest tests/test_p26_alpha_evidence.py tests/docs/test_p26_public_alpha_decision.py -v --no-cov`

### SL-1 - Evidence Harness

- **Scope**: Add a local-only evidence collection script that runs private-alpha checks against operator-supplied repositories and emits redaction-ready JSON/Markdown.
- **Owned files**: `scripts/private_alpha_evidence.py`
- **Interfaces provided**: `scripts/private_alpha_evidence.py --config <json> --output-dir private-alpha-evidence/<run-id> --redacted-md docs/validation/private-alpha-decision.md --redacted-json docs/validation/private-alpha-decision.json`; raw evidence JSON shape consumed by IF-0-P26-1 through IF-0-P26-4
- **Interfaces consumed**: P22 `scripts/release_smoke.py`; benchmark runners in `scripts/run_e2e_retrieval_validation.py` and `scripts/run_mcp_vs_native_benchmark.py`; STDIO tools `search_code`, `symbol_lookup`, and `reindex`; P25 required gate names
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 contract tests to fail until the harness entrypoint, CLI flags, redaction behavior, and schema fields exist.
  - impl: Implement a config-driven harness accepting fixture category, local repo path, optional repository display alias, query cases, and expected path fragments.
  - impl: Record install and smoke timing by invoking `make release-smoke` or `scripts/release_smoke.py --wheel --stdio` once per run.
  - impl: For each fixture, record first index time, query latency p50/p95, top-k quality summaries, log noise classification, default-branch behavior, and rollback/rebuild observations.
  - impl: Redact absolute paths, repository names, log lines, and source snippets from committed JSON/Markdown; leave raw details only under `private-alpha-evidence/`.
  - impl: Exit non-zero when any fixture is missing or any issue is classified as `public_alpha_blocker`.
  - verify: `uv run python scripts/private_alpha_evidence.py --help`
  - verify: `uv run pytest tests/test_p26_alpha_evidence.py -v --no-cov`

### SL-2 - Redacted Evidence Templates And Schema

- **Scope**: Define the committed evidence schema and decision template without including private repository data.
- **Owned files**: `docs/validation/private-alpha-evidence.schema.json`, `docs/validation/private-alpha-decision.md`, `docs/validation/private-alpha-decision.json`
- **Interfaces provided**: committed redacted evidence artifacts for IF-0-P26-1 through IF-0-P26-4
- **Interfaces consumed**: SL-0 tests; P26 roadmap exit criteria; P25 public-alpha gate checklist
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 schema/docs tests to fail until the schema and template contain the required fixture, measurement, classification, and decision fields.
  - impl: Add a JSON schema for redacted evidence with required fixture categories and measurement fields.
  - impl: Add a markdown decision template with sections for fixture inventory, install/index/query evidence, log noise, branch/default-branch behavior, rollback/rebuild behavior, known issue classification, release-note readiness, and final decision.
  - impl: Add a redacted JSON placeholder or generated artifact shape that tests can validate without real private evidence.
  - impl: Make clear in the template that raw evidence belongs only under ignored `private-alpha-evidence/`.
  - verify: `uv run pytest tests/test_p26_alpha_evidence.py tests/docs/test_p26_public_alpha_decision.py -v --no-cov`

### SL-3 - Private-Alpha Execution Record

- **Scope**: Run the evidence harness against the selected private-alpha fixture set and commit only the redacted decision outputs.
- **Owned files**: `docs/validation/private-alpha-decision.md`, `docs/validation/private-alpha-decision.json`, `docs/benchmarks/private-alpha-summary.md`
- **Interfaces provided**: completed IF-0-P26-1 evidence; completed IF-0-P26-4 go/no-go decision input
- **Interfaces consumed**: SL-1 harness output; SL-2 schema/template; selected local real repositories; P25 alpha gate results
- **Parallel-safe**: no
- **Tasks**:
  - test: Confirm the fixture config includes `python_repo`, `typescript_js_repo`, `mixed_docs_code_repo`, `multi_repo_workspace`, and `large_ignored_vendor_repo`.
  - impl: Run the harness locally with operator-supplied repository paths and write raw outputs under `private-alpha-evidence/<run-id>/`.
  - impl: Review the redacted outputs for path, repository-name, log-line, and source-snippet leaks before staging.
  - impl: Populate `docs/benchmarks/private-alpha-summary.md` with aggregate install/index/query metrics only, not raw private repo data.
  - impl: Record issue classifications and the provisional public-alpha decision in the redacted decision files.
  - verify: `uv run python scripts/private_alpha_evidence.py --config <private-config.json> --output-dir private-alpha-evidence/<run-id> --redacted-md docs/validation/private-alpha-decision.md --redacted-json docs/validation/private-alpha-decision.json`
  - verify: `rg -n "/home/|/Users/|source_snippet|raw_log|customer|secret|token" docs/validation/private-alpha-decision.md docs/validation/private-alpha-decision.json docs/benchmarks/private-alpha-summary.md`

### SL-4 - Operator Go/No-Go Runbooks

- **Scope**: Teach operators how to run P26, interpret evidence, handle blockers, and decide whether public alpha can proceed.
- **Owned files**: `docs/operations/deployment-runbook.md`, `docs/operations/user-action-runbook.md`
- **Interfaces provided**: operator procedure for IF-0-P26-1 through IF-0-P26-4
- **Interfaces consumed**: SL-1 harness CLI; SL-2 schema/template; SL-3 evidence categories, issue classifications, and provisional decision; P25 public-alpha gate checklist
- **Parallel-safe**: no
- **Tasks**:
  - test: Use SL-0 docs tests to fail until runbooks mention the P26 evidence command, raw-output boundary, fixture categories, blocker classifications, and go/no-go decision.
  - impl: Add a `Private Alpha Evidence` section to `docs/operations/deployment-runbook.md` after the P25 public-alpha gate checklist.
  - impl: Add P26 before/after operator actions to `docs/operations/user-action-runbook.md`, including fixture selection, private config handling, redaction review, and blocker escalation.
  - impl: Document that public alpha is blocked by any required P21-P25 gate failure or any P26 `public_alpha_blocker`.
  - impl: Document that non-blocking issues must be captured as documented limitations or post-alpha backlog before a `go` decision.
  - verify: `uv run pytest tests/docs/test_p26_public_alpha_decision.py -v --no-cov`

### SL-5 - Public-Alpha Release Note Surfaces

- **Scope**: Update customer-facing release surfaces with the P26 decision, supported install paths, beta warnings, rollback instructions, and links to the support matrix.
- **Owned files**: `README.md`, `CHANGELOG.md`
- **Interfaces provided**: IF-0-P26-5 release-note truth contract
- **Interfaces consumed**: SL-2 evidence schema/template; SL-3 final decision and issue classifications; SL-4 runbook wording; existing support matrix `docs/SUPPORT_MATRIX.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Use SL-0 release-surface assertions to fail until README and CHANGELOG contain the required public-alpha truth fields.
  - impl: Add P26 release-note entries under the active changelog section.
  - impl: Update README alpha status text to point at `docs/validation/private-alpha-decision.md`, `docs/SUPPORT_MATRIX.md`, and rollback instructions in the deployment runbook.
  - impl: Ensure README does not imply GA, SaaS, or universal language support beyond the support matrix.
  - verify: `uv run pytest tests/docs/test_p26_public_alpha_decision.py tests/docs/test_p23_doc_truth.py -v --no-cov`

### SL-6 - Final P26 Audit

- **Scope**: Run the full P26 evidence and release-readiness audit, then either approve public alpha or create a narrow blocker roadmap.
- **Owned files**: (none)
- **Interfaces provided**: final IF-0-P26-1 completion evidence; public-alpha `go`/`no_go`/`conditional_go` decision; optional v3 blocker-roadmap input
- **Interfaces consumed**: IF-0-P26-1 through IF-0-P26-5 from SL-1 through SL-5; P21-P25 required gates; redacted evidence artifacts
- **Parallel-safe**: no
- **Tasks**:
  - test: Run P26 contract tests and docs truth tests after all producer lanes land.
  - verify: `uv run pytest tests/test_p26_alpha_evidence.py tests/docs/test_p26_public_alpha_decision.py -v --no-cov`
  - verify: `uv run pytest tests/smoke tests/docs tests/test_release_metadata.py tests/test_requirements_consolidation.py tests/test_p25_release_gates.py -v --no-cov`
  - verify: `make -n alpha-release-gates release-smoke release-smoke-container`
  - verify: `rg -n "Alpha Gate -|private alpha|public alpha|private-alpha-decision|rollback|support matrix" README.md CHANGELOG.md docs/operations docs/validation`
  - verify: `rg -n "/home/|/Users/|source_snippet|raw_log|secret|token" docs/validation/private-alpha-decision.md docs/validation/private-alpha-decision.json docs/benchmarks/private-alpha-summary.md`
  - impl: If the final decision is `go`, record the public-alpha release-note readiness state.
  - impl: If the final decision is `no_go` or `conditional_go`, append roadmap amendments or create a narrow v3 blocker roadmap instead of broadening P26 implementation.

## Verification

Required P26 checks:

```bash
uv run pytest tests/test_p26_alpha_evidence.py tests/docs/test_p26_public_alpha_decision.py -v --no-cov
uv run pytest tests/smoke tests/docs tests/test_release_metadata.py tests/test_requirements_consolidation.py tests/test_p25_release_gates.py -v --no-cov
make -n alpha-release-gates release-smoke release-smoke-container
uv run python scripts/private_alpha_evidence.py --help
```

Private-alpha evidence run:

```bash
uv run python scripts/private_alpha_evidence.py \
  --config <private-config.json> \
  --output-dir private-alpha-evidence/<run-id> \
  --redacted-md docs/validation/private-alpha-decision.md \
  --redacted-json docs/validation/private-alpha-decision.json
```

Redaction checks:

```bash
rg -n "/home/|/Users/|source_snippet|raw_log|secret|token" \
  docs/validation/private-alpha-decision.md \
  docs/validation/private-alpha-decision.json \
  docs/benchmarks/private-alpha-summary.md
```

Whole-phase optional workflow checks:

```bash
gh workflow view "CI/CD Pipeline"
gh workflow view "Release Automation"
gh workflow view "Container Registry Management"
gh workflow view "lockfile-check"
```

## Acceptance Criteria

- [ ] Private-alpha fixture set includes `python_repo`, `typescript_js_repo`, `mixed_docs_code_repo`, `multi_repo_workspace`, and `large_ignored_vendor_repo`.
- [ ] Raw private-alpha evidence is written only under ignored `private-alpha-evidence/`; committed artifacts contain no private repository names, absolute paths, source snippets, raw logs, secrets, or tokens.
- [ ] Evidence captures install time, first index time, p50/p95 query latency, result quality, log noise, branch/default-branch behavior, and rollback/rebuild behavior for every fixture category.
- [ ] Known issues are classified as `public_alpha_blocker`, `documented_limitation`, or `post_alpha_backlog`.
- [ ] README and CHANGELOG public-alpha text name the supported install paths, support matrix, beta warnings, rollback instructions, and `docs/validation/private-alpha-decision.md`.
- [ ] The final decision is recorded as exactly one of `go`, `no_go`, or `conditional_go`.
- [ ] Any P21-P25 required gate failure or P26 `public_alpha_blocker` blocks public alpha and is routed to a narrow follow-up roadmap.
