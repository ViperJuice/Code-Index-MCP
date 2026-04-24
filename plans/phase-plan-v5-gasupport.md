---
phase_loop_plan_version: 1
phase: GASUPPORT
roadmap: specs/phase-plans-v5.md
roadmap_sha256: 6c3ef37eac6b52116804f765470905ca8f8ec4333c306a57c9ba1b8a178b4dc5
---
# GASUPPORT: GA Support Matrix Hardening

## Context

GASUPPORT is the third phase in the v5 GA-hardening roadmap. It depends on
GABASE and should consume the frozen GA vocabulary and release boundary rather
than reopening product scope. The goal is to convert the current public-alpha
support narrative into explicit GA-hardening support tiers without broadening
language, topology, or install-surface claims.

Current repo state gathered during planning:

- The checkout is on `main` at `8d08545`.
- `specs/phase-plans-v5.md` is already staged in this worktree
  (`git status --short -- specs/phase-plans-v5.md` returned
  `A  specs/phase-plans-v5.md`), so it must be treated as the user-owned
  roadmap baseline.
- `.codex/phase-loop/state.json` already marks `GABASE` and `GAGOV` as
  complete and selects `GASUPPORT` as the current planned phase, so GASUPPORT
  should consume `docs/validation/ga-readiness-checklist.md` and the current
  governance artifact rather than redefining those contracts.
- `docs/SUPPORT_MATRIX.md` is still the canonical P23 support inventory for
  `1.2.0-rc5`, but it does not yet assign one explicit GA-hardening support
  tier to every language/runtime row or to every advertised install/tool
  surface.
- `PluginFactory.get_plugin_availability()` in
  `mcp_server/plugins/plugin_factory.py`, `handle_list_plugins()` in
  `mcp_server/cli/tool_handlers.py`, and the `list_plugins` tool description in
  `mcp_server/cli/stdio_runner.py` already expose machine-readable availability
  facts (`state`, `sandbox_supported`, `specific_plugin`, `plugin_module`,
  `required_extras`, `remediation`, `error_type`) that GASUPPORT should extend
  only as needed to make support-tier claims provable.
- Existing P24/P28 tests in `tests/test_p24_plugin_availability.py`,
  `tests/test_p24_list_plugins_status.py`, and
  `tests/test_stdio_tool_descriptions.py` already cover plugin availability and
  tool-surface wording; GASUPPORT should extend those tests instead of creating
  a second incompatible support-fact harness.
- Public docs already route readers to `docs/SUPPORT_MATRIX.md` and
  `docs/validation/ga-readiness-checklist.md`, but `README.md` still contains
  blanket language such as `Works with all 48 supported languages`, which is
  broader than the roadmap's explicit tiering requirement.
- `docs/validation/secondary-tool-readiness-evidence.md` exists and should stay
  classified as readiness evidence, not as a support-matrix expansion.

## Interface Freeze Gates

- [ ] IF-0-GASUPPORT-1 - Tiered support matrix contract:
      `docs/SUPPORT_MATRIX.md` assigns exactly one explicit tier to every
      advertised language/runtime row and to every advertised install/tool
      surface, using only the frozen labels `GA-supported`, `beta`,
      `experimental`, `unsupported`, or `disabled-by-default`.
- [ ] IF-0-GASUPPORT-2 - Machine-checkable support-facts contract:
      `PluginFactory.get_plugin_availability()`, `handle_list_plugins()`, and
      `stdio_runner._build_tool_list()` expose stable facts for default sandbox
      behavior, specific-plugin vs registry-only behavior, optional extras, and
      unsupported or opt-in paths so docs tests can prove the matrix does not
      overclaim.
- [ ] IF-0-GASUPPORT-3 - Public-claim guard contract: `README.md`,
      `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`, and
      `docs/DOCKER_GUIDE.md` route support claims to
      `docs/SUPPORT_MATRIX.md`, keep STDIO primary and FastAPI secondary, and
      reject universal language/runtime, unrestricted-topology, or unsupported
      install-surface claims.
- [ ] IF-0-GASUPPORT-4 - Readiness-evidence boundary contract:
      `docs/validation/secondary-tool-readiness-evidence.md` and any
      `list_plugins` / plugin-availability diagnostics are referenced only as
      readiness evidence for existing secondary-tool surfaces, not as support
      expansion for new languages, topologies, or install modes.

## Lane Index & Dependencies

- SL-0 - GASUPPORT contract tests; Depends on: GABASE; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Machine-checkable plugin and tool support facts; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: yes
- SL-2 - Support matrix tier reducer; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Public docs and install-surface alignment; Depends on: SL-0, SL-2; Blocks: SL-4; Parallel-safe: yes
- SL-4 - Shared docs-truth support regressions; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: GASUPPORT acceptance; Parallel-safe: no

## Lanes

### SL-0 - GASUPPORT Contract Tests

- **Scope**: Freeze the tiered support-matrix shape, machine-checkable support
  facts, and forbidden public-claim patterns before changing docs or tool
  descriptions.
- **Owned files**: `tests/docs/test_gasupport_support_contract.py`
- **Interfaces provided**: IF-0-GASUPPORT-1, IF-0-GASUPPORT-2,
  IF-0-GASUPPORT-3, IF-0-GASUPPORT-4
- **Interfaces consumed**: `docs/validation/ga-readiness-checklist.md`,
  `docs/SUPPORT_MATRIX.md`, `README.md`, `docs/GETTING_STARTED.md`,
  `docs/MCP_CONFIGURATION.md`, `docs/DOCKER_GUIDE.md`,
  `docs/validation/secondary-tool-readiness-evidence.md`,
  `mcp_server/plugins/plugin_factory.py`,
  `mcp_server/cli/tool_handlers.py`, `mcp_server/cli/stdio_runner.py`,
  `tests/docs/test_gabase_ga_readiness_contract.py`,
  `tests/test_p24_plugin_availability.py`,
  `tests/test_p24_list_plugins_status.py`,
  `tests/test_stdio_tool_descriptions.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a dedicated GASUPPORT contract test that requires one explicit
    support tier per language/runtime row and one explicit support tier per
    advertised install/tool surface.
  - test: Assert that public docs reject phrases such as universal
    language/runtime support, unrestricted repository topology, or blanket
    install-surface support that bypasses the support matrix.
  - test: Assert that the support matrix and docs ground claims in stable
    runtime facts such as sandbox support, optional extras, plugin-module
    presence, and opt-in features rather than prose-only assumptions.
  - test: Assert that secondary-tool readiness evidence stays an evidence
    reference and does not become a support-expansion claim.
  - impl: Keep the phase test additive and phase-specific so GABASE, P23, P24,
    and GACLOSE tests remain lower-level contracts.
  - verify: `uv run pytest tests/docs/test_gasupport_support_contract.py -v --no-cov`

### SL-1 - Machine-Checkable Plugin And Tool Support Facts

- **Scope**: Expose the narrow structured support facts that the support matrix
  and docs tests need without broadening runtime behavior or changing actual
  support scope.
- **Owned files**: `mcp_server/plugins/plugin_factory.py`,
  `mcp_server/plugins/language_registry.py`, `mcp_server/cli/tool_handlers.py`,
  `mcp_server/cli/stdio_runner.py`, `tests/test_p24_plugin_availability.py`,
  `tests/test_p24_list_plugins_status.py`,
  `tests/test_stdio_tool_descriptions.py`
- **Interfaces provided**: stable plugin-availability and tool-surface facts
  for sandbox/default behavior, optional extras, specific-plugin coverage, and
  advertised surface posture
- **Interfaces consumed**: SL-0 assertions; existing `PluginAvailability`
  fields; `SPECIFIC_PLUGIN_MODULES`; `LANGUAGE_CONFIGS`; current `list_plugins`
  and `get_status` payload shapes; GABASE vocabulary for STDIO primary /
  FastAPI secondary / pre-GA surfaces
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend P24/P28 tests to fail first when the structured
    plugin-availability payload or tool descriptions stop exposing the facts
    that the support matrix depends on.
  - impl: If the current availability payload is insufficient, add narrowly
    named machine-checkable fields for default behavior or opt-in posture
    rather than encoding support claims only in docs prose.
  - impl: Keep the existing availability-state contract backward-compatible:
    do not widen supported languages, remove sandbox safeguards, or change the
    meaning of readiness-gated tool descriptions during this phase.
  - impl: Keep STDIO primary, FastAPI secondary, and readiness-gated query
    language intact; GASUPPORT should tighten claims, not redesign surfaces.
  - verify: `uv run pytest tests/test_p24_plugin_availability.py tests/test_p24_list_plugins_status.py tests/test_stdio_tool_descriptions.py -v --no-cov`
  - verify: `uv run python -m mcp_server.cli.server_commands list-plugins --help`

### SL-2 - Support Matrix Tier Reducer

- **Scope**: Rewrite `docs/SUPPORT_MATRIX.md` into the canonical tiered support
  inventory that downstream GA phases can consume directly.
- **Owned files**: `docs/SUPPORT_MATRIX.md`
- **Interfaces provided**: IF-0-GASUPPORT-1 and IF-0-GASUPPORT-4; canonical
  language/runtime and install/tool support tiers for GAE2E, GAOPS, GARC, and
  GAREL
- **Interfaces consumed**: SL-0 assertions; SL-1 machine-checkable support
  facts; `docs/validation/ga-readiness-checklist.md`;
  `docs/validation/secondary-tool-readiness-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Use SL-0 and SL-1 to identify missing tier columns, mismatched
    sandbox/default behavior, or install/tool claims that are not grounded in
    structured facts.
  - impl: Add explicit tiering for every language/runtime row and for every
    advertised tool/install surface, including STDIO tools, FastAPI/admin,
    Docker, native uv/wheel installs, semantic search, reranking, sandbox
    behavior, optional extras, and any disabled-by-default or unsupported
    paths.
  - impl: Preserve the current topology limits, readiness vocabulary, and
    public-alpha baseline while converting the document from inventory-only
    prose into the canonical support-tier source of truth.
  - impl: Reference secondary-tool readiness evidence only as readiness
    evidence and explicitly avoid using it as proof of broader support.
  - verify: `uv run pytest tests/docs/test_gasupport_support_contract.py tests/test_p24_plugin_availability.py tests/test_p24_list_plugins_status.py tests/test_stdio_tool_descriptions.py -v --no-cov`
  - verify: `rg -n "GA-supported|beta|experimental|unsupported|disabled-by-default|STDIO|FastAPI|Docker|uv sync --locked|wheel|semantic|rerank|secondary-tool-readiness-evidence" docs/SUPPORT_MATRIX.md`

### SL-3 - Public Docs And Install-Surface Alignment

- **Scope**: Tighten customer-facing docs so they advertise only the tiered
  support claims frozen in the support matrix.
- **Owned files**: `README.md`, `docs/GETTING_STARTED.md`,
  `docs/MCP_CONFIGURATION.md`, `docs/DOCKER_GUIDE.md`
- **Interfaces provided**: IF-0-GASUPPORT-3 across public install and
  configuration docs
- **Interfaces consumed**: SL-0 assertions; SL-2 support tiers;
  `docs/validation/ga-readiness-checklist.md`; current install commands and
  image names already documented in these files
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 failures and existing docs-truth tests to locate blanket
    support claims such as `Works with all 48 supported languages` and other
    wording that bypasses explicit tier labels.
  - impl: Route all support claims to `docs/SUPPORT_MATRIX.md` and keep the
    release-boundary language tied to `docs/validation/ga-readiness-checklist.md`.
  - impl: Preserve the documented install commands and image/package identities
    that already exist, but label them according to the tiered support contract
    rather than implying universal or GA support.
  - impl: Keep STDIO primary, FastAPI secondary, and the current repository
    topology limitations visible in each public surface that discusses them.
  - verify: `uv run pytest tests/docs/test_gasupport_support_contract.py tests/docs/test_gabase_ga_readiness_contract.py -v --no-cov`
  - verify: `rg -n "48 supported languages|works with all|universal language/runtime support|unrestricted|GA-supported|beta|experimental|unsupported|disabled-by-default|STDIO|FastAPI|Docker|uv sync --locked" README.md docs/GETTING_STARTED.md docs/MCP_CONFIGURATION.md docs/DOCKER_GUIDE.md`

### SL-4 - Shared Docs-Truth Support Regressions

- **Scope**: Reduce the phase-specific and public-doc changes into the shared
  docs-truth regressions that keep support claims from drifting again.
- **Owned files**: `tests/docs/test_p23_doc_truth.py`,
  `tests/docs/test_gaclose_evidence_closeout.py`
- **Interfaces provided**: durable docs-truth and public-alpha regression
  coverage for GASUPPORT claims
- **Interfaces consumed**: SL-0 GASUPPORT assertions; SL-1 machine-checkable
  facts; SL-2 support tiers; SL-3 public docs wording;
  `docs/validation/ga-readiness-checklist.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update the shared docs-truth suite so future docs edits fail when
    they overclaim language/runtime support, topology scope, or install-surface
    support outside the matrix.
  - test: Keep GACLOSE's RC/public-alpha baseline assertions intact while
    allowing GASUPPORT's explicit support tiers to become the new canonical
    support vocabulary.
  - impl: Make the shared docs tests reference the support matrix and checklist
    consistently instead of relying on older blanket-language heuristics.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_gasupport_support_contract.py -v --no-cov`

## Verification

- `uv run pytest tests/docs/test_gasupport_support_contract.py -v --no-cov`
- `uv run pytest tests/test_p24_plugin_availability.py tests/test_p24_list_plugins_status.py tests/test_stdio_tool_descriptions.py -v --no-cov`
- `uv run pytest tests/docs/test_p23_doc_truth.py tests/docs/test_gaclose_evidence_closeout.py tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_gasupport_support_contract.py -v --no-cov`
- `uv run pytest tests/docs tests/test_p24_plugin_availability.py tests/test_p24_list_plugins_status.py tests/test_stdio_tool_descriptions.py -v --no-cov`
- `uv run python -m mcp_server.cli.server_commands list-plugins --help`
- `rg -n "GA-supported|beta|experimental|unsupported|disabled-by-default|48 supported languages|works with all|universal language/runtime support|unrestricted|STDIO|FastAPI|Docker|uv sync --locked|wheel|semantic|rerank" README.md docs/SUPPORT_MATRIX.md docs/GETTING_STARTED.md docs/MCP_CONFIGURATION.md docs/DOCKER_GUIDE.md tests`

## Acceptance Criteria

- [ ] `docs/SUPPORT_MATRIX.md` assigns exactly one explicit tier to every
      language/runtime row and to every advertised install/tool surface.
- [ ] Plugin availability output, `list_plugins`, and related tests expose the
      machine-checkable facts needed to prove the matrix's sandbox/default and
      optional-extra claims.
- [ ] Public docs reject universal language/runtime, unrestricted-topology, and
      unsupported install-surface claims and route support claims to the
      support matrix.
- [ ] `list_plugins` and the support matrix agree about default sandbox
      behavior, unsupported registry-only paths, and optional-extra posture for
      supported languages.
- [ ] `docs/validation/secondary-tool-readiness-evidence.md` is referenced as
      readiness evidence only and is not used to imply broader GA support.

## Automation

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gasupport.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gasupport.md
  artifact_state: staged
```
