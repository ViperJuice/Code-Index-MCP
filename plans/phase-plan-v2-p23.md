# P23: Customer Docs Truth & Support Matrix

> Plan doc produced by `codex-plan-phase P23` against `specs/phase-plans-v2.md` on 2026-04-21.
> P23 consumes P21's release contract (`1.2.0-rc3` / `v1.2.0-rc3`, `pyproject.toml` + `uv.lock`) and P22's smoke/image contract (`ghcr.io/viperjuice/code-index-mcp`, shared release smoke commands).

## Context

P23 is the alpha documentation truth pass. It must make customer-facing docs, agent-facing docs, and support claims describe the product that P21 and P22 actually proved, without adding runtime features or reopening packaging work.

Current repo surfaces relevant to P23:

- `README.md` has the P21 version line, but still contains older release examples such as `1.0.0`, broad `48-Language Support` framing, and Docker/semantic sections that need to be checked against P22's proven smoke path.
- `docs/DOCKER_GUIDE.md` still uses stale image names such as `ghcr.io/code-index-mcp/mcp-index:*`, variant tags that are not the frozen P22 image contract, and broad zero-setup claims.
- `docs/operations/deployment-runbook.md` is labeled `v1.2.0` and references `v1.2.0-rc2`; it must either become alpha-current or be clearly scoped as a later production/staged rollout runbook.
- `mcp_server/AGENTS.md` still references `pip install -r requirements.txt`.
- Existing doc tests under `tests/docs/` cover P7/P8 truth work. P23 should add a narrow P23 test module instead of rewriting older phase tests.
- Plugin support truth should be derived from the runtime sources: `mcp_server/plugins/language_registry.py`, `mcp_server/plugins/plugin_factory.py`, `mcp_server/plugins/plugin_set_registry.py`, `mcp_server/plugins/sandboxed_plugin.py`, and `pyproject.toml` optional extras.

This phase may narrow advertised support. It should distinguish specialized sandbox-supported plugins, generic Tree-sitter registry coverage, document/plaintext behavior, optional semantic/rerank/java extras, and known alpha limitations. Any runtime mismatch found while documenting support is a P24 input unless it is a pure documentation contradiction.

## Interface Freeze Gates

- [ ] IF-0-P23-1 - Support matrix contract: `docs/SUPPORT_MATRIX.md` exists and contains one canonical support table with columns `Language`, `Runtime behavior`, `Parser status`, `Sandbox support`, `Required extras`, `Symbol quality`, `Semantic support`, and `Known limitations`; rows are grounded in `LANGUAGE_CONFIGS`, `SPECIFIC_PLUGINS`, `SPECIFIC_PLUGIN_MODULES`, and `pyproject.toml` optional extras.
- [ ] IF-0-P23-2 - Release docs truth contract: README, Getting Started, Docker guide, MCP configuration, deployment runbook, and security docs agree on version `1.2.0-rc3`, beta/alpha status, `mcp-index` as the console script, `pyproject.toml`/`uv.lock` as dependency truth, and `ghcr.io/viperjuice/code-index-mcp` as the documented image package.
- [ ] IF-0-P23-3 - Agent docs truth contract: root `AGENTS.md`, `CLAUDE.md`, and active nested agent docs do not contradict P21/P22 install, dependency, transport, Docker, beta status, or support-matrix claims.
- [ ] IF-0-P23-4 - Historical-doc visibility contract: historical/status/validation docs are either bannered as historical artifacts, listed in `docs/HISTORICAL-ARTIFACTS-TRIAGE.md`, or removed from active navigation; active customer docs do not cite stale status reports as current truth.
- [ ] IF-0-P23-5 - Doc truth test contract: `tests/docs/test_p23_doc_truth.py` fails on stale version strings, removed requirements install paths, stale GHCR image names, unsupported "complete"/"fully operational"/"Production-Ready" claims, and missing support-matrix columns.

## Lane Index & Dependencies

- SL-0 - P23 doc truth tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4, SL-5, SL-6; Parallel-safe: yes
- SL-1 - Canonical support matrix; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4, SL-7; Parallel-safe: yes
- SL-2 - README alpha truth; Depends on: SL-0, SL-1; Blocks: SL-7; Parallel-safe: yes
- SL-3 - Customer setup docs truth; Depends on: SL-0, SL-1; Blocks: SL-7; Parallel-safe: yes
- SL-4 - Operations and security docs truth; Depends on: SL-0, SL-1; Blocks: SL-7; Parallel-safe: yes
- SL-5 - Agent docs truth; Depends on: SL-0; Blocks: SL-7; Parallel-safe: yes
- SL-6 - Historical navigation and triage; Depends on: SL-0; Blocks: SL-7; Parallel-safe: yes
- SL-7 - Final P23 audit; Depends on: SL-2, SL-3, SL-4, SL-5, SL-6; Blocks: P24; Parallel-safe: no

Lane DAG:

```text
SL-0
 ├─> SL-1 ─┬─> SL-2 ─┐
 │         ├─> SL-3 ─┤
 │         └─> SL-4 ─┤
 ├───────────> SL-5 ─┤
 └───────────> SL-6 ─┤
                     └─> SL-7
```

## Lanes

### SL-0 - P23 Doc Truth Tests

- **Scope**: Add executable tests that freeze P23's documentation contracts before prose edits land.
- **Owned files**: `tests/docs/test_p23_doc_truth.py`
- **Interfaces provided**: IF-0-P23-1 assertions, IF-0-P23-2 assertions, IF-0-P23-3 assertions, IF-0-P23-4 assertions, IF-0-P23-5 assertions
- **Interfaces consumed**: P21 constants from `tests/test_release_metadata.py`; P22 `GHCR_IMAGE = "ghcr.io/viperjuice/code-index-mcp"` from `tests/smoke/test_release_smoke_contract.py`; existing P7/P8 doc test style under `tests/docs/`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add tests that assert `docs/SUPPORT_MATRIX.md` exists and has the required columns exactly once.
  - test: Add tests that reject stale doc-wide strings: `1.0.0`, `1.1.0`, `v1.2.0-rc2`, `requirements.txt`, `pip install -r`, `Production-Ready`, `fully operational`, `48-Language Support`, and `complete tree-sitter integration`.
  - test: Add tests that reject stale image packages such as `ghcr.io/code-index-mcp/mcp-index` and require `ghcr.io/viperjuice/code-index-mcp` in Docker-facing docs.
  - test: Add tests that require README, Getting Started, Docker guide, MCP configuration, deployment runbook, and security docs to contain beta/alpha status language where they make release or deployment claims.
  - test: Add tests that require agent docs to avoid removed dependency install paths and to point to the support matrix when discussing language support.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py -v --no-cov`

### SL-1 - Canonical Support Matrix

- **Scope**: Create the single support-matrix document that downstream P23 docs cite for language/runtime support claims.
- **Owned files**: `docs/SUPPORT_MATRIX.md`
- **Interfaces provided**: IF-0-P23-1 canonical support matrix; P24 runtime-hardening input for unsupported sandbox languages and optional dependency misses
- **Interfaces consumed**: `LANGUAGE_CONFIGS` from `mcp_server/plugins/language_registry.py`; `SPECIFIC_PLUGINS` and `SPECIFIC_PLUGIN_MODULES` from `mcp_server/plugins/plugin_factory.py`; sandbox default behavior from `PluginFactory.create_plugin`; optional extras from `pyproject.toml`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 support-matrix tests to fail on missing document, missing columns, and stale overclaims.
  - impl: Add `docs/SUPPORT_MATRIX.md` with a short beta-status note and one table using the required P23 columns.
  - impl: Classify specialized sandbox-supported languages separately from generic registry languages that currently fail sandbox construction until P24 expands degradation behavior.
  - impl: Mark semantic/vector/rerank behavior as optional and dependent on configured providers/API keys or extras, not as unconditional support.
  - impl: Include known limitations for multi-repo beta status, generic symbol quality, document/plaintext behavior, sandbox gaps, and unsupported plugin families.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py -v --no-cov`

### SL-2 - README Alpha Truth

- **Scope**: Make README's first-screen status, install, Docker, language support, and release examples match P21/P22 and cite the support matrix.
- **Owned files**: `README.md`
- **Interfaces provided**: README side of IF-0-P23-2 and IF-0-P23-1
- **Interfaces consumed**: SL-1 `docs/SUPPORT_MATRIX.md`; P21 `1.2.0-rc3` version contract; P22 `ghcr.io/viperjuice/code-index-mcp` image contract; P22 release smoke commands
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 stale-string and support-link tests to expose README contradictions.
  - impl: Replace broad `48-Language Support` framing with a beta support statement and a link to `docs/SUPPORT_MATRIX.md`.
  - impl: Remove or update stale `1.0.0` release examples and any text implying GA or production-ready status.
  - impl: Align Docker examples with P22's frozen image package and proven smoke scope.
  - impl: Keep FastAPI framed as secondary admin surface and STDIO/MCP as the primary LLM tool surface.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py tests/docs/test_p8_customer_docs_alignment.py tests/test_release_metadata.py -v --no-cov`

### SL-3 - Customer Setup Docs Truth

- **Scope**: Align Getting Started, Docker guide, and MCP configuration docs with the alpha install, image, and MCP configuration contracts.
- **Owned files**: `docs/GETTING_STARTED.md`, `docs/DOCKER_GUIDE.md`, `docs/MCP_CONFIGURATION.md`
- **Interfaces provided**: customer setup side of IF-0-P23-2
- **Interfaces consumed**: SL-1 support matrix; P21 dependency source-of-truth; P22 wheel, CLI, STDIO, and container smoke contracts
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 docs sweep assertions to fail on stale image names, old install paths, and unproven Docker variant claims.
  - impl: Update installation examples to prefer `uv sync --locked`, wheel/CLI smoke, and `mcp-index` commands that P22 proves.
  - impl: Replace stale Docker image package names and variant tags with `ghcr.io/viperjuice/code-index-mcp` examples that match P22.
  - impl: Clarify optional semantic setup, required environment variables, and beta multi-repo behavior without adding new setup flows.
  - impl: Link language-support claims to `docs/SUPPORT_MATRIX.md` instead of duplicating broad matrices.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py tests/docs/test_p8_customer_docs_alignment.py -v --no-cov`

### SL-4 - Operations and Security Docs Truth

- **Scope**: Make deployment and security docs accurately describe alpha/beta posture, current image names, release version, auth/path knobs, and sandbox limitations.
- **Owned files**: `docs/operations/deployment-runbook.md`, `docs/security/attestation.md`, `docs/security/path-guard.md`, `docs/security/sandbox.md`, `docs/security/token-scopes.md`
- **Interfaces provided**: operations/security side of IF-0-P23-2; security-specific inputs for P24/P25
- **Interfaces consumed**: SL-1 support matrix; P21 version/tag contract; P22 container image contract; existing P15 security posture documented in AGENTS.md
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 tests to fail on `v1.2.0-rc2`, stale `v1.2.0` production labels, stale image names, and unqualified production claims.
  - impl: Update or scope `docs/operations/deployment-runbook.md` so it no longer reads like a GA production playbook for `v1.2.0`; clearly mark alpha/beta and current `1.2.0-rc3` assumptions.
  - impl: Confirm security docs use `MCP_ALLOWED_ROOTS`, `MCP_CLIENT_SECRET`, sandbox, attestation, and token-scope language that matches current runtime and alpha support.
  - impl: Link sandbox language limitations to `docs/SUPPORT_MATRIX.md` and identify mismatches as P24 work instead of claiming they are fixed.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py -v --no-cov`

### SL-5 - Agent Docs Truth

- **Scope**: Align agent-facing instructions with the current MCP-first, STDIO-primary, pyproject/uv, Docker, and support-matrix contracts.
- **Owned files**: `AGENTS.md`, `CLAUDE.md`, `mcp_server/AGENTS.md`
- **Interfaces provided**: IF-0-P23-3 agent docs truth
- **Interfaces consumed**: P21 dependency and version contracts; P22 image/smoke contracts; SL-1 support matrix; existing MCP-first search guidance
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 agent-doc assertions to fail on `pip install -r requirements.txt`, stale Python version claims, unsupported production claims, and conflicting language-support text.
  - impl: Replace removed requirements install instructions with `uv sync --locked` or the existing project-approved command.
  - impl: Update plugin/language support language to cite `docs/SUPPORT_MATRIX.md` and avoid claiming all registry languages are equally production-quality under sandbox default-on.
  - impl: Preserve project-specific MCP-first search guidance and existing multi-repo operational notes.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py tests/docs/test_p7_markdown_alignment.py tests/test_requirements_consolidation.py -v --no-cov`

### SL-6 - Historical Navigation and Triage

- **Scope**: Ensure historical/status documents are visibly non-current or absent from active navigation without rewriting old reports as current docs.
- **Owned files**: `docs/HISTORICAL-ARTIFACTS-TRIAGE.md`, `docs/implementation/*.md`, `docs/status/*.md`, `docs/validation/*.md`, `docs/MARKDOWN_INDEX.md`
- **Interfaces provided**: IF-0-P23-4 historical-doc visibility
- **Interfaces consumed**: existing P8 historical banner convention from `tests/docs/test_p8_historical_sweep.py`; SL-0 stale-claim patterns
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 tests plus existing P8 historical sweep tests to detect stale status docs exposed as current truth.
  - impl: Add/update historical banners where status/implementation/validation docs remain in place.
  - impl: Update `docs/HISTORICAL-ARTIFACTS-TRIAGE.md` for any newly bannered, rewritten, or removed docs.
  - impl: Update `docs/MARKDOWN_INDEX.md` so active navigation points to current customer docs and the support matrix, not stale completion/status reports.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py tests/docs/test_p8_historical_sweep.py -v --no-cov`

### SL-7 - Final P23 Audit

- **Scope**: Run the P23 acceptance checks, record any runtime/doc mismatch as P24 input, and verify older doc truth tests still pass.
- **Owned files**: (none)
- **Interfaces provided**: P23 completion evidence for P24 and P25
- **Interfaces consumed**: IF-0-P23-1 from SL-1; IF-0-P23-2 from SL-2/SL-3/SL-4; IF-0-P23-3 from SL-5; IF-0-P23-4 from SL-6; IF-0-P23-5 from SL-0
- **Parallel-safe**: no
- **Tasks**:
  - test: Run all P23 and prior doc truth tests after every producer lane lands.
  - verify: `uv run pytest tests/docs -v --no-cov`
  - verify: `uv run pytest tests/test_release_metadata.py tests/test_requirements_consolidation.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `rg -n "1\\.0\\.0|1\\.1\\.0|v1\\.2\\.0-rc2|requirements\\.txt|pip install -r|Production-Ready|fully operational|48-Language Support|complete tree-sitter integration" README.md docs AGENTS.md CLAUDE.md mcp_server/AGENTS.md`
  - verify: `rg -n "ghcr\\.io/code-index-mcp/mcp-index|mcp-index:(minimal|standard|full)" README.md docs AGENTS.md CLAUDE.md mcp_server/AGENTS.md`
  - impl: Record any support-matrix/runtime gaps as P24 work items in the final implementation summary; do not patch runtime behavior in P23.

## Verification

Required P23 checks:

```bash
uv run pytest tests/docs -v --no-cov
uv run pytest tests/test_release_metadata.py tests/test_requirements_consolidation.py tests/smoke/test_release_smoke_contract.py -v --no-cov
rg -n "1\\.0\\.0|1\\.1\\.0|v1\\.2\\.0-rc2|requirements\\.txt|pip install -r|Production-Ready|fully operational|48-Language Support|complete tree-sitter integration" README.md docs AGENTS.md CLAUDE.md mcp_server/AGENTS.md
rg -n "ghcr\\.io/code-index-mcp/mcp-index|mcp-index:(minimal|standard|full)" README.md docs AGENTS.md CLAUDE.md mcp_server/AGENTS.md
```

Expected final state:

- README, Getting Started, Docker guide, MCP configuration, deployment runbook, and security docs agree on version, beta/alpha status, image package, install commands, and dependency source of truth.
- Agent docs no longer contradict current dependency, Docker, STDIO/MCP, or language-support contracts.
- `docs/SUPPORT_MATRIX.md` is the canonical support matrix and distinguishes specialized support, generic registry coverage, sandbox behavior, optional extras, semantic support, and known limitations.
- Historical/status docs are bannered, triaged, or removed from active navigation.
- Grep-based P23 doc truth tests catch stale versions, removed install paths, stale image names, and unsupported "complete"/production claims.
- Any runtime mismatch discovered while documenting support is explicitly deferred to P24.

## Acceptance Criteria

- [ ] README, Getting Started, Docker guide, MCP configuration, deployment runbook, and security docs agree on install commands, image names, version `1.2.0-rc3`, and beta/alpha status.
- [ ] `AGENTS.md`, `CLAUDE.md`, and `mcp_server/AGENTS.md` no longer contradict the current implementation, P21 dependency contract, P22 image/smoke contract, or P23 support matrix.
- [ ] `docs/SUPPORT_MATRIX.md` lists language, runtime behavior, parser status, sandbox support, required extras, symbol quality, semantic support, and known limitations.
- [ ] Historical/status docs are archived, bannered, or removed from active navigation and recorded in `docs/HISTORICAL-ARTIFACTS-TRIAGE.md`.
- [ ] `tests/docs/test_p23_doc_truth.py` covers stale version strings, unsupported "complete" claims, removed install paths, stale GHCR image names, and support-matrix structure.
- [ ] Existing P7/P8 doc truth tests still pass.
- [ ] P21 release metadata, P21 dependency consolidation, and P22 release smoke contract tests still pass.
