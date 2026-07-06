---
phase_loop_plan_version: 1
phase: REPOCLEAN
roadmap: specs/phase-plans-v9.md
roadmap_sha256: 4bdeba36d7fdba2d849c35deaaadbf73e0223b2272969f0f712c4970d63f55a5
---
# REPOCLEAN: Public Repo Root Cleanup And Windows Clone Safety

## Context

REPOCLEAN is Phase 2 in `specs/phase-plans-v9.md`. PUBNAME is complete in the
canonical `.phase-loop/state.json`, the current `.phase-loop/` state names
`REPOCLEAN` as the next phase, and the worktree was clean at planning time.
Legacy `.codex/phase-loop/` files are compatibility artifacts only and are not
used to supersede the canonical runner state.

Planning observations:

- `specs/phase-plans-v9.md` is tracked and its SHA-256 matches
  `4bdeba36d7fdba2d849c35deaaadbf73e0223b2272969f0f712c4970d63f55a5`.
- `plans/phase-plan-v9-REPOCLEAN.md` did not exist before this planning run.
- `git ls-files -ci --exclude-standard` currently reports
  tracked-but-ignored paths, including local config/index metadata and source
  under `mcp_server/cache/`; execution must classify these before removal or
  retention.
- `git ls-files` currently has no repository-relative path over 160
  characters; the longest observed tracked path during planning was 123
  characters.
- Tracked generated candidates include root JSON/status outputs, `.metadata/`,
  `analysis_archive/`, `test_results/`, `performance_reports/`,
  benchmark/result trees, and root report Markdown files.
- README and `docs/PROJECT_STRUCTURE.md` still mention scratch/output
  directories as project-structure concepts, including `analysis_archive/` and
  `test_results/`.
- REPOCLEAN must preserve PUBNAME evidence at
  `docs/status/public-package-identity.md` and must not delete or rename
  deferred identity surfaces such as `code-index-mcp.profiles.yaml`,
  `mcp-index-kit/`, client-label examples, or MCP config examples unless a
  later phase explicitly re-decides those names.

Planning boundary:

- This plan authorizes inventory, ignore-policy cleanup, tracked
  generated-artifact deletion or documented retention, project-structure
  documentation updates, Windows path guidance, and metadata-only cleanup
  evidence.
- This plan does not authorize git history rewrite, package release dispatch,
  source/test deletion outside the declared generated-output inventory, or
  runtime behavior changes.
- Any path that looks generated but is retained must be justified in
  `docs/status/repo-root-cleanup-inventory.md` with a keep/drop/defer decision
  and non-secret rationale.

## Interface Freeze Gates

- [ ] IF-0-REPOCLEAN-1 - Clean source-tree contract: generated root
      JSON/log/status dumps, tracked scratch/output directories, deep path
      hazards, and committed runtime outputs are classified and removed from
      git unless explicitly retained as source or durable evidence; `.gitignore`
      prevents recurrence without masking source directories; tracked-but-ignored
      paths are audited before deletion or retention; README/project-structure
      docs no longer advertise scratch directories as first-class layout;
      `git ls-files` proves every tracked repository-relative path is at or
      below 160 characters; a local wheel-content audit checks site-packages
      path-depth risk; and Windows troubleshooting presents
      `git config --global core.longpaths true` as a fallback after the repo tree
      is clean.

## Lane Index & Dependencies

- SL-0 - Cleanup audit command contract; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Generated artifact removal and ignore policy; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Public structure docs and Windows clone safety; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Cleanup evidence reducer and acceptance verification; Depends on: SL-0, SL-1, SL-2; Blocks: REPOCLEAN acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 -> SL-1 -> SL-2 -> SL-3 -> REPOCLEAN acceptance
```

## Lanes

### SL-0 - Cleanup Audit Command Contract

- **Scope**: Add a small local audit helper that makes tracked-generated,
  tracked-ignored, path-length, and wheel path-depth checks repeatable without
  deleting files.
- **Owned files**: `scripts/repo_clean_audit.py`, `tests/test_repo_clean_audit.py`
- **Interfaces provided**: audit JSON schema for IF-0-REPOCLEAN-1 with fields
  for `tracked_generated_candidates`, `tracked_ignored_paths`,
  `longest_tracked_path`, `over_limit_paths`, `wheel_site_packages_paths`,
  `max_wheel_site_packages_path_length`, and `retention_required_paths`
- **Interfaces consumed**: `git ls-files`,
  `git ls-files -ci --exclude-standard`, `.gitignore`, `pyproject.toml`,
  `uv run --extra dev python -m build --wheel`, and the roadmap path limit of
  160 characters
- **Parallel-safe**: no
- **Tasks**:
  - test: Add unit tests for the audit helper that exercise generated root
    JSON/report detection, tracked ignored parsing, source-directory false
    positives such as `mcp_server/cache/`, max path-length calculation, and
    wheel path-depth extraction from a built wheel or fixture zip.
  - impl: Implement `scripts/repo_clean_audit.py` so `--json --max-path 160`
    reports metadata only and never deletes files; add an optional
    `--wheel-depth` mode that builds the wheel into a temporary directory,
    inspects zip member names, and removes temporary build output.
  - impl: Keep the audit output deterministic enough for docs tests while
    avoiding absolute user-specific paths except where explicitly labelled
    runtime evidence.
  - verify: `uv run pytest tests/test_repo_clean_audit.py -q --no-cov`
  - verify: `uv run python scripts/repo_clean_audit.py --json --max-path 160`

### SL-1 - Generated Artifact Removal And Ignore Policy

- **Scope**: Remove or deliberately retain tracked generated outputs and update
  ignore rules so regenerated artifacts stay out of git without hiding source
  files.
- **Owned files**: `.gitignore`, `.metadata/**`, `INDEXING_STATUS.json`, `artifact-metadata.json`, `complete_indexing_results.json`, `indexing_progress_summary.json`, `mcp_direct_test_results.json`, `mcp_indexing_status.json`, `mcp_indexing_summary.json`, `mcp_path_fix_test_results.json`, `mcp_search_code_test_results.json`, `mcp_validation_results.json`, `mcp_verification_results.json`, `missing_repos_to_index.json`, `multi_repo_search_test_results.json`, `proper_repo_mapping.json`, `real_quick_results.json`, `repo_db_mapping.json`, `semantic_indexing_progress.json`, `test_queries.json`, `test_queries_small.json`, `full_indexing_log.txt`, `*_REPORT.md`, `*_SUMMARY.md`, `*_STATUS.md`, `*_ANALYSIS.md`, `analysis_archive/**`, `comprehensive_real_results/**`, `comprehensive_semantic_results/**`, `fast_test_results/**`, `final_optimized_report_final_report_1750958096/**`, `mcp_test_results/**`, `performance_reports/**`, `quick_test_results/**`, `real_cost_analysis/**`, `real_edit_analysis/**`, `real_session_analysis/**`, `reports/**`, `sample_transcripts/**`, `strategic_recommendations/**`, `test_indexes/**`, `test_results/**`
- **Interfaces provided**: cleaned tracked-source inventory and
  recurrence-prevention ignore policy for IF-0-REPOCLEAN-1
- **Interfaces consumed**: SL-0 audit JSON schema; roadmap requirement to
  preserve source, tests, active docs, release evidence,
  `docs/status/public-package-identity.md`, deferred identity surfaces, and MCP
  example/config surfaces until explicitly re-decided
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 audit before deletion and record the generated
    candidates and tracked-ignored classes that require keep/drop/defer
    decisions.
  - impl: Delete tracked generated root JSON/log/status dumps and
    scratch/output directories unless the inventory classifies a path as active
    source or durable evidence.
  - impl: Remove committed runtime/index outputs such as `.metadata/**` unless a
    retained metadata file is explicitly justified as source-of-truth evidence.
  - impl: Update `.gitignore` so regenerated dumps, local runtime state,
    transient index outputs, wheel/build byproducts, performance result
    directories, and phase-loop/dev-skill runtime output are ignored, while
    source directories such as `mcp_server/cache/` are not accidentally masked
    by broad `cache/` rules.
  - impl: Preserve `docs/status/public-package-identity.md`,
    `code-index-mcp.profiles.yaml`, `mcp-index-kit/**`, `.mcp.json.example`,
    `.mcp.json.templates/**`, and user-facing MCP example labels unless the
    inventory names a specific safe cleanup action.
  - verify: `uv run python scripts/repo_clean_audit.py --json --max-path 160`
  - verify: `git ls-files -ci --exclude-standard`
  - verify: `git ls-files | python -c "import sys; paths=[p.rstrip('\\n') for p in sys.stdin]; print(max((len(p), p) for p in paths)); assert all(len(p) <= 160 for p in paths)"`

### SL-2 - Public Structure Docs And Windows Clone Safety

- **Scope**: Update public structure and troubleshooting docs so the cleaned
  repository layout is accurate and Windows long-path guidance is a fallback,
  not the main mitigation.
- **Owned files**: `README.md`, `TROUBLESHOOTING.md`, `docs/PROJECT_STRUCTURE.md`, `docs/TROUBLESHOOTING.md`, `docs/GETTING_STARTED.md`, `tests/docs/test_repoclean_docs.py`
- **Interfaces provided**: public docs portion of IF-0-REPOCLEAN-1
- **Interfaces consumed**: SL-0 audit output; SL-1 final keep/drop/defer cleanup
  decisions; PUBNAME evidence path preservation; existing local-wheel install
  flow from README and `docs/GETTING_STARTED.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_repoclean_docs.py` to assert README and
    `docs/PROJECT_STRUCTURE.md` do not present `analysis_archive/`,
    `test_results/`, `performance_reports/`, or generated result directories as
    first-class source layout.
  - test: Require troubleshooting/getting-started docs to mention
    `git config --global core.longpaths true` only as a Windows fallback after
    using the cleaned source tree and local/offloaded artifacts.
  - impl: Remove or rewrite public project-structure references to
    scratch/output directories; point durable evidence readers to `docs/status/`
    or `docs/benchmarks/` only when those files remain intentionally tracked.
  - impl: Add concise Windows clone/install troubleshooting that explains the
    frozen 160-character tracked-path limit, the wheel path-depth audit, and
    `core.longpaths` as a fallback for unusual local paths or third-party
    tooling.
  - verify: `uv run pytest tests/docs/test_repoclean_docs.py -q --no-cov`
  - verify: `rg -n "analysis_archive|test_results|performance_reports|core\.longpaths|160|Windows" README.md TROUBLESHOOTING.md docs/PROJECT_STRUCTURE.md docs/TROUBLESHOOTING.md docs/GETTING_STARTED.md tests/docs/test_repoclean_docs.py`

### SL-3 - Cleanup Evidence Reducer And Acceptance Verification

- **Scope**: Reduce the audit output, deletion decisions, ignore-policy
  changes, docs updates, and wheel path-depth check into one metadata-only
  cleanup evidence artifact.
- **Owned files**: `docs/status/repo-root-cleanup-inventory.md`, `tests/docs/test_repoclean_inventory_contract.py`
- **Interfaces provided**: final IF-0-REPOCLEAN-1 clean source-tree contract and
  phase acceptance evidence
- **Interfaces consumed**: SL-0 audit JSON; SL-1 generated artifact deletion and
  tracked-ignored decisions; SL-2 docs changes; `git ls-files` path-length
  output; temporary wheel-content audit output; current
  `docs/status/public-package-identity.md` preservation requirement
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_repoclean_inventory_contract.py` to require
    `docs/status/repo-root-cleanup-inventory.md` to include the audit date,
    audit commands, generated-path classes, tracked-but-ignored classes,
    keep/drop/defer decisions, longest tracked path, wheel site-packages max
    path, and Windows fallback wording.
  - test: Require the evidence artifact to state that
    `docs/status/public-package-identity.md`, deferred identity surfaces, and
    source/test files were preserved unless explicitly listed in the cleanup
    table.
  - impl: Write `docs/status/repo-root-cleanup-inventory.md` as metadata-only
    evidence. Include command snippets and summarized output, but do not include
    secrets, local tokens, raw credentials, or user-private absolute paths
    beyond the repo root already present in runner state.
  - impl: Record the post-cleanup `git ls-files` maximum path and the
    wheel-content maximum path; if either check cannot run, keep the phase
    blocked with `blocker_class=contract_bug` rather than treating proxy
    evidence as acceptance.
  - verify: `uv run pytest tests/docs/test_repoclean_inventory_contract.py tests/docs/test_repoclean_docs.py tests/test_repo_clean_audit.py -q --no-cov`
  - verify: `uv run python scripts/repo_clean_audit.py --json --max-path 160 --wheel-depth`
  - verify: `git diff --stat -- .gitignore scripts/repo_clean_audit.py tests/test_repo_clean_audit.py README.md TROUBLESHOOTING.md docs/PROJECT_STRUCTURE.md docs/TROUBLESHOOTING.md docs/GETTING_STARTED.md docs/status/repo-root-cleanup-inventory.md tests/docs/test_repoclean_docs.py tests/docs/test_repoclean_inventory_contract.py`

## Verification

Plan artifact creation is complete once this artifact is written and staged. Do
not execute the commands below during `codex-plan-phase`; run them during
`codex-execute-phase` or manual REPOCLEAN execution.

Lane-specific checks:

```bash
uv run pytest tests/test_repo_clean_audit.py -q --no-cov
uv run python scripts/repo_clean_audit.py --json --max-path 160
uv run pytest tests/docs/test_repoclean_docs.py -q --no-cov
uv run pytest tests/docs/test_repoclean_inventory_contract.py tests/docs/test_repoclean_docs.py tests/test_repo_clean_audit.py -q --no-cov
uv run python scripts/repo_clean_audit.py --json --max-path 160 --wheel-depth
```

Whole-phase verification after cleanup changes:

```bash
uv sync --locked --extra dev
uv run pytest \
  tests/test_repo_clean_audit.py \
  tests/docs/test_repoclean_docs.py \
  tests/docs/test_repoclean_inventory_contract.py \
  -q --no-cov
uv run python scripts/repo_clean_audit.py --json --max-path 160 --wheel-depth
git ls-files -ci --exclude-standard
git ls-files | python -c "import sys; paths=[p.rstrip('\n') for p in sys.stdin]; print(max((len(p), p) for p in paths)); assert all(len(p) <= 160 for p in paths)"
make alpha-docs-truth
phase-loop validate-roadmap specs/phase-plans-v9.md
git status --short -- \
  .gitignore \
  scripts/repo_clean_audit.py \
  tests/test_repo_clean_audit.py \
  README.md \
  TROUBLESHOOTING.md \
  docs/PROJECT_STRUCTURE.md \
  docs/TROUBLESHOOTING.md \
  docs/GETTING_STARTED.md \
  docs/status/repo-root-cleanup-inventory.md \
  tests/docs/test_repoclean_docs.py \
  tests/docs/test_repoclean_inventory_contract.py \
  plans/phase-plan-v9-REPOCLEAN.md
```

Full gate when execution time allows:

```bash
make alpha-release-gates
```

## Acceptance Criteria

- [ ] Generated root JSON/log/status dumps are deleted, moved to approved
      documentation/evidence locations, or explicitly justified in
      `docs/status/repo-root-cleanup-inventory.md`.
- [ ] Scratch/output directories such as `analysis_archive/`, `test_results/`,
      `performance_reports/`, result trees, and similar generated folders are
      removed from git unless intentionally preserved under a documented archive
      policy.
- [ ] `.gitignore` covers regenerated dumps, transient index outputs,
      performance results, local runtime state, and local phase-loop/dev-skill
      artifacts without ignoring source directories such as `mcp_server/cache/`.
- [ ] A tracked-but-ignored audit classifies every
      `git ls-files -ci --exclude-standard` path before deletion or retention.
- [ ] README and project-structure docs no longer advertise scratch/output
      directories as first-class source layout.
- [ ] A `git ls-files` tracked-path audit proves no tracked
      repository-relative path exceeds 160 characters.
- [ ] A package-install path audit checks generated wheel contents for
      site-packages path-depth risk on Windows and records the maximum path
      length.
- [ ] Windows troubleshooting mentions `git config --global core.longpaths true`
      as a fallback, not as the primary fix.
- [ ] PUBNAME evidence at `docs/status/public-package-identity.md` and deferred
      identity surfaces such as `code-index-mcp.profiles.yaml`, MCP config
      examples, and `mcp-index-kit/` are preserved unless a later phase
      re-decides those names.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `no_spec_delta`
- target surfaces: `.gitignore`, `scripts/repo_clean_audit.py`, `tests/test_repo_clean_audit.py`, generated root reports and JSON files, generated output directories, `README.md`, `TROUBLESHOOTING.md`, `docs/PROJECT_STRUCTURE.md`, `docs/TROUBLESHOOTING.md`, `docs/GETTING_STARTED.md`, `docs/status/repo-root-cleanup-inventory.md`, `tests/docs/test_repoclean_docs.py`, `tests/docs/test_repoclean_inventory_contract.py`
- evidence paths: `docs/status/repo-root-cleanup-inventory.md`
- redaction posture: `metadata_only`
- downstream handling: none

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v9-REPOCLEAN.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v9-REPOCLEAN.md
  artifact_state: staged
```
