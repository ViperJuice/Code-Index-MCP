# P24: Sandbox & Plugin Runtime Hardening

> Plan doc produced by `codex-plan-phase P24` against `specs/phase-plans-v2.md` on 2026-04-21.
> P24 consumes P23's support matrix in `docs/SUPPORT_MATRIX.md` and produces IF-0-P24-1 for P25 release-gate automation.

## Context

P24 is the runtime hardening pass that makes sandbox-default-on behavior match the support matrix instead of treating every registry language as a loadable sandbox plugin.

Current repo surfaces relevant to P24:

- `PluginFactory.create_plugin()` defaults to sandbox mode unless `MCP_PLUGIN_SANDBOX_DISABLE=1` is set. In sandbox mode it only supports languages in `SPECIFIC_PLUGIN_MODULES`; registry-only languages currently raise `ValueError`.
- `PluginFactory.create_all_plugins()` catches construction failures and logs them at error level, which turns expected unsupported registry languages into noisy startup/runtime failures.
- `EnhancedDispatcher._ensure_plugin_loaded()` catches `ValueError` as a warning and other exceptions as errors. Normal indexing of files whose languages are in `LANGUAGE_CONFIGS` but not sandbox-supported can therefore still produce warning/error noise.
- `docs/SUPPORT_MATRIX.md` explicitly identifies P24 inputs: registry-only languages need quiet sandbox degradation, Rust/Kotlin have sandbox module mappings but factory imports may not expose `Plugin`, and plaintext has a specific factory path but no sandbox module mapping.
- `handle_list_plugins()` currently reports plugin manager rows, supported languages, and loaded plugins, but it does not expose enabled, disabled, unsupported, or missing-extra state across the factory support surface.
- Worker import/constructor failures surface through `SandboxCallError`/worker stderr shapes. Optional dependency misses such as Java's `javalang` need a capability-unavailable state with remediation, not a crash-looking worker failure.

P24 should choose the smaller runtime change: keep sandbox default-on, do not promise rich symbols for registry-only languages, and report capability state consistently enough for P25 to make it a blocking release gate.

## Interface Freeze Gates

- [ ] IF-0-P24-1 - Sandbox degradation contract: when sandbox mode is active, `PluginFactory.create_plugin()` distinguishes unavailable capability states from unexpected construction failures. Registry-only languages without a sandbox module return or raise a typed capability-unavailable result that callers can treat as a quiet skip, not an error-level runtime failure.
- [ ] IF-0-P24-2 - Plugin availability contract: `PluginFactory.get_plugin_availability(language: str | None = None, *, sandbox_enabled: bool | None = None) -> list[dict] | dict` reports each factory language with stable fields `language`, `state`, `sandbox_supported`, `specific_plugin`, `plugin_module`, `required_extras`, `remediation`, and `error_type`. `state` values are limited to `enabled`, `unsupported`, `missing_extra`, `disabled`, and `load_error`.
- [ ] IF-0-P24-3 - Dispatcher quiet-skip contract: `EnhancedDispatcher`, `PluginSetRegistry`, and `MemoryAwarePluginManager` treat expected `unsupported` and `missing_extra` plugin states as debug/info-level skips and keep `failed_files` reserved for unexpected indexing failures.
- [ ] IF-0-P24-4 - Status surface contract: the MCP `list_plugins` handler returns a `plugin_availability` list using the IF-0-P24-2 field names, plus loaded plugin rows where available. `get_status` may summarize counts, but `list_plugins` is the canonical detailed capability surface.
- [ ] IF-0-P24-5 - Sandbox worker failure contract: worker import and constructor failures caused by known optional dependencies or module/export mismatches are normalized into `missing_extra` or `unsupported` capability-unavailable details. C#/C-sharp sandbox construction succeeds for both `c_sharp` and `csharp`.

## Lane Index & Dependencies

- SL-0 - P24 contract tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4, SL-5; Parallel-safe: yes
- SL-1 - Factory availability model; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4, SL-5, SL-6; Parallel-safe: no
- SL-2 - Sandbox IPC failure normalization; Depends on: SL-0, SL-1; Blocks: SL-3, SL-5, SL-6; Parallel-safe: yes
- SL-3 - Dispatcher and registry quiet skips; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4, SL-6; Parallel-safe: yes
- SL-4 - MCP plugin status surface; Depends on: SL-0, SL-1, SL-3; Blocks: SL-6; Parallel-safe: yes
- SL-5 - Specific plugin construction fixes; Depends on: SL-0, SL-1, SL-2; Blocks: SL-6; Parallel-safe: yes
- SL-6 - P24 docs and support-matrix reconciliation; Depends on: SL-1, SL-2, SL-3, SL-4, SL-5; Blocks: SL-7, P25; Parallel-safe: no
- SL-7 - Final P24 audit; Depends on: SL-6; Blocks: P25; Parallel-safe: no

Lane DAG:

```text
SL-0
 └─> SL-1 ─┬─> SL-2 ─┬─> SL-3 ─┬─> SL-4 ─┐
           │         │         └──────────┤
           │         └─> SL-5 ────────────┤
           └──────────────────────────────┤
                                          └─> SL-6 ─> SL-7
```

## Lanes

### SL-0 - P24 Contract Tests

- **Scope**: Add failing tests that freeze the P24 availability, quiet-degradation, status, and C# construction contracts before implementation.
- **Owned files**: `tests/test_p24_plugin_availability.py`, `tests/security/test_p24_sandbox_degradation.py`, `tests/test_p24_dispatcher_degradation.py`, `tests/test_p24_list_plugins_status.py`
- **Interfaces provided**: executable assertions for IF-0-P24-1, IF-0-P24-2, IF-0-P24-3, IF-0-P24-4, IF-0-P24-5
- **Interfaces consumed**: P23 support-matrix P24 inputs from `docs/SUPPORT_MATRIX.md`; existing sandbox test style from `tests/security/test_plugin_sandbox.py`; existing default-on tests from `tests/test_sandbox_default_on.py`; existing handler tests from `tests/test_tool_schema_handler_parity.py`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add factory tests that assert registry-only sandbox languages such as `ruby` and `json` are `unsupported`, not unexpected errors.
  - test: Add availability tests that assert every `PluginFactory.get_supported_languages()` entry has exactly one IF-0-P24-2 availability row and a stable `state`.
  - test: Add dispatcher tests that index a sandbox-unsupported file without error-level logs and without incrementing `failed_files`.
  - test: Add `list_plugins` handler tests that require `plugin_availability` rows and state counts.
  - test: Add sandbox construction tests for both `c_sharp` and `csharp`, plus an optional dependency miss shape for Java when `javalang` is unavailable.
  - verify: `uv run pytest tests/test_p24_plugin_availability.py tests/security/test_p24_sandbox_degradation.py tests/test_p24_dispatcher_degradation.py tests/test_p24_list_plugins_status.py -v --no-cov`

### SL-1 - Factory Availability Model

- **Scope**: Introduce a typed plugin availability model in the factory and make default sandbox unsupported paths quiet and machine-readable.
- **Owned files**: `mcp_server/plugins/plugin_factory.py`
- **Interfaces provided**: IF-0-P24-1; IF-0-P24-2; `PluginAvailability`; `PluginUnavailableError`; `PluginFactory.get_plugin_availability(...)`
- **Interfaces consumed**: `LANGUAGE_CONFIGS`; `SPECIFIC_PLUGINS`; `SPECIFIC_PLUGIN_MODULES`; optional extras from `pyproject.toml`; support-matrix classifications from P23
- **Parallel-safe**: no
- **Tasks**:
  - test: Use SL-0 factory tests to fail on missing availability rows and noisy unsupported sandbox languages.
  - impl: Add a small availability representation in `plugin_factory.py` with stable dictionary serialization and the allowed P24 state values.
  - impl: Add `PluginUnavailableError` carrying `language`, `state`, `required_extras`, and `remediation` for expected unavailable capability cases.
  - impl: Make sandbox-default-on registry-only languages produce `unsupported` availability instead of a generic `ValueError`.
  - impl: Add required-extra metadata for Java and any other known optional plugin dependency surfaced by existing imports.
  - impl: Update `create_all_plugins()` so expected unavailable states are skipped at debug/info level while unexpected exceptions remain error-level.
  - verify: `uv run pytest tests/test_p24_plugin_availability.py tests/test_sandbox_default_on.py tests/security/test_plugin_sandbox.py -v --no-cov`

### SL-2 - Sandbox IPC Failure Normalization

- **Scope**: Normalize sandbox worker import and constructor failures so host callers can distinguish missing extras, unsupported modules, and unexpected worker crashes.
- **Owned files**: `mcp_server/sandbox/worker_main.py`, `mcp_server/sandbox/supervisor.py`, `mcp_server/plugins/sandboxed_plugin.py`, `tests/security/fixtures/p24_missing_extra_plugin.py`
- **Interfaces provided**: IF-0-P24-5 worker-side error envelope shape; host-side `SandboxCallError.details` fields compatible with SL-1 unavailable states
- **Interfaces consumed**: `CapabilitySet`; sandbox protocol `Envelope`; `SandboxCallError`; SL-1 `PluginUnavailableError` semantics without importing factory code into the worker hot path unless needed
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 sandbox degradation tests to fail on raw worker tracebacks for known missing-extra fixture imports.
  - impl: Wrap worker module import and plugin construction in structured error envelopes when the failure occurs before the IPC loop is ready.
  - impl: Preserve stderr diagnostics for unexpected crashes while ensuring returned payloads include `type`, `message`, `state`, `language` when known, and `remediation` when known.
  - impl: Ensure `SandboxedPlugin.language`, `supports`, and `indexFile` propagate normalized `SandboxCallError.details` without losing state.
  - verify: `uv run pytest tests/security/test_p24_sandbox_degradation.py tests/security/test_plugin_sandbox.py tests/security/test_malicious_plugin.py -v --no-cov`

### SL-3 - Dispatcher And Registry Quiet Skips

- **Scope**: Make dispatcher, per-repo plugin registry, and memory-aware plugin loading consume expected unavailable states as quiet skips during normal indexing/search paths.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/plugin_set_registry.py`, `mcp_server/plugins/memory_aware_manager.py`
- **Interfaces provided**: IF-0-P24-3; quiet `unsupported`/`missing_extra` handling in `_ensure_plugin_loaded`, `_ensure_plugin_for_file`, `index_file`, `index_directory`, and `PluginSetRegistry.plugins_for_file`
- **Interfaces consumed**: SL-1 `PluginUnavailableError`; SL-1 `get_plugin_availability`; SL-2 normalized `SandboxCallError.details`; existing dispatcher `IndexResultStatus`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 dispatcher tests to fail when sandbox-unsupported registry languages produce error-level logs or count as indexing failures.
  - impl: Catch `PluginUnavailableError` separately from unexpected exceptions in dispatcher lazy loading and memory-aware loading.
  - impl: Track skipped unavailable languages internally so repeated attempts do not spam logs.
  - impl: Keep `failed_files` for real plugin/indexing failures and count unsupported files as ignored or skipped according to existing stats vocabulary.
  - impl: Ensure `PluginSetRegistry._build_plugin_list()` does not silently mask unexpected errors while still quietly skipping expected unavailable states.
  - verify: `uv run pytest tests/test_p24_dispatcher_degradation.py tests/test_dispatcher.py tests/test_memory_aware_manager.py -v --no-cov`

### SL-4 - MCP Plugin Status Surface

- **Scope**: Expose the new plugin capability states through the MCP `list_plugins` tool and status summaries without changing tool names or required schema inputs.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `mcp_server/cli/stdio_runner.py`, `tests/test_mcp_server_cli.py`
- **Interfaces provided**: IF-0-P24-4 `list_plugins` response shape; optional status count summary for plugin availability states
- **Interfaces consumed**: SL-1 `PluginFactory.get_plugin_availability`; SL-3 loaded/quiet-skip state; existing `_build_tool_list()` schema and `handle_list_plugins(...)`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 handler tests to fail until `handle_list_plugins()` returns `plugin_availability` rows with the IF-0-P24-2 fields.
  - impl: Add `plugin_availability` and `availability_counts` to `handle_list_plugins()` while preserving existing `plugin_manager_plugins`, `supported_languages`, and `loaded_plugins` keys.
  - impl: Update the `list_plugins` tool description in `stdio_runner.py` to mention enabled, unsupported, disabled, and missing-extra states.
  - impl: Add a compact availability count to `handle_get_status()` only if it can reuse SL-1 APIs without instantiating plugins.
  - verify: `uv run pytest tests/test_p24_list_plugins_status.py tests/test_tool_schema_handler_parity.py tests/test_mcp_server_cli.py -v --no-cov`

### SL-5 - Specific Plugin Construction Fixes

- **Scope**: Fix the narrow plugin export and construction mismatches called out by P23 without broadening language support claims.
- **Owned files**: `mcp_server/plugins/csharp_plugin/**`, `mcp_server/plugins/rust_plugin/**`, `mcp_server/plugins/kotlin_plugin/**`, `mcp_server/plugins/java_plugin/**`, `mcp_server/plugins/simple_text_plugin.py`
- **Interfaces provided**: IF-0-P24-5 for C#/C-sharp; importable `Plugin` aliases where existing package modules expose differently named plugin classes; optional-extra remediation metadata surfaced through plugin construction
- **Interfaces consumed**: SL-1 factory module map and availability model; SL-2 normalized sandbox worker failures; existing plugin class contracts from `IPlugin`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 sandbox construction tests to fail for `PluginFactory.create_plugin("c_sharp")` and `PluginFactory.create_plugin("csharp")` if either sandbox worker path crashes.
  - impl: Add or normalize `Plugin` exports in Rust/Kotlin package `__init__.py` files if their class names differ from factory expectations.
  - impl: Confirm C# plugin construction has no sandbox-time project scan, filesystem write, or capability violation before `supports()`/`indexFile()` calls.
  - impl: Add lightweight optional dependency checks or remediation hints in Java plugin construction paths without requiring the `java` extra for core install.
  - impl: Make plaintext sandbox support explicit if SL-1 maps it to `mcp_server.plugins.simple_text_plugin`, or keep it `unsupported` if mapping introduces worker incompatibility.
  - verify: `uv run pytest tests/security/test_p24_sandbox_degradation.py tests/root_tests/test_java_plugin_simple.py tests/root_tests/test_all_specialized_plugins.py -v --no-cov`

### SL-6 - P24 Docs And Support-Matrix Reconciliation

- **Scope**: Update the canonical support matrix and sandbox docs to describe the hardened runtime states after all producer lanes land.
- **Owned files**: `docs/SUPPORT_MATRIX.md`, `docs/security/sandbox.md`, `docs/operations/user-action-runbook.md`
- **Interfaces provided**: documented IF-0-P24-1; P25 input for blocking release gate definitions
- **Interfaces consumed**: SL-1 availability state names and remediation hints; SL-2 worker failure details; SL-3 dispatcher skip behavior; SL-4 `list_plugins` response shape; SL-5 resolved plugin construction facts
- **Parallel-safe**: no
- **Tasks**:
  - test: Use P23 doc truth tests and any SL-0 status tests that validate state names in docs.
  - impl: Replace P23's "P24 must add..." support-matrix limitations with the actual P24 runtime states and any remaining known limitations.
  - impl: Document that sandbox-default-on remains the default and that unsupported registry languages are visible in `list_plugins` as unavailable capabilities.
  - impl: Add remediation wording for missing extras such as Java's `javalang` without changing the core dependency contract.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py tests/test_p24_list_plugins_status.py -v --no-cov`

### SL-7 - Final P24 Audit

- **Scope**: Run the P24 regression set, check for error-level sandbox noise in targeted scenarios, and hand IF-0-P24-1 to P25.
- **Owned files**: (none)
- **Interfaces provided**: P24 completion evidence for P25; final IF-0-P24-1 status
- **Interfaces consumed**: IF-0-P24-1 through IF-0-P24-5 from SL-1 through SL-6
- **Parallel-safe**: no
- **Tasks**:
  - test: Run all P24 contract tests and the existing sandbox/dispatcher regression tests after producer lanes land.
  - verify: `uv run pytest tests/test_p24_plugin_availability.py tests/security/test_p24_sandbox_degradation.py tests/test_p24_dispatcher_degradation.py tests/test_p24_list_plugins_status.py -v --no-cov`
  - verify: `uv run pytest tests/security/test_plugin_sandbox.py tests/test_sandbox_default_on.py tests/test_dispatcher.py tests/test_memory_aware_manager.py tests/test_mcp_server_cli.py -v --no-cov`
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py -v --no-cov`
  - verify: `uv run pytest tests/security/test_plugin_sandbox.py tests/test_sandbox_default_on.py tests/test_dispatcher.py -v --no-cov`
  - verify: `rg -n "Failed to create plugin|Sandbox mode does not yet support|Error loading plugin" mcp_server/plugins mcp_server/dispatcher mcp_server/cli`
  - impl: Record any residual unsupported languages as support-matrix limitations, not runtime TODOs, unless they violate the P24 quiet-degradation contract.

## Verification

Required P24 checks:

```bash
uv run pytest tests/test_p24_plugin_availability.py tests/security/test_p24_sandbox_degradation.py tests/test_p24_dispatcher_degradation.py tests/test_p24_list_plugins_status.py -v --no-cov
uv run pytest tests/security/test_plugin_sandbox.py tests/test_sandbox_default_on.py tests/test_dispatcher.py tests/test_memory_aware_manager.py tests/test_mcp_server_cli.py -v --no-cov
uv run pytest tests/docs/test_p23_doc_truth.py -v --no-cov
uv run pytest tests/security/test_plugin_sandbox.py tests/test_sandbox_default_on.py tests/test_dispatcher.py -v --no-cov
```

Recommended manual smoke after implementation:

```bash
uv run python - <<'PY'
from mcp_server.plugins.plugin_factory import PluginFactory
for lang in ["python", "java", "c_sharp", "csharp", "ruby", "json", "plaintext"]:
    print(PluginFactory.get_plugin_availability(lang, sandbox_enabled=True))
PY
```

Expected final state:

- Sandbox-default-on is preserved.
- Registry-only languages without sandbox support are reported as `unsupported` capabilities and skipped quietly during normal indexing/search flows.
- Optional dependency misses are reported as `missing_extra` with remediation hints.
- C#/C-sharp sandbox construction succeeds for both aliases.
- `list_plugins` exposes enabled, unsupported, disabled, load-error, and missing-extra states using stable field names.
- P23 support-matrix P24 notes are replaced with actual runtime behavior and remaining known limitations.

## Acceptance Criteria

- [ ] Languages outside sandbox support do not emit error-level logs during normal lexical searches or indexing.
- [ ] Optional dependency misses such as Java extras are reported as unavailable capabilities with remediation hints.
- [ ] C#/C-sharp plugin construction does not crash sandbox workers for either `c_sharp` or `csharp`.
- [ ] `list_plugins` includes `plugin_availability` rows for all supported factory languages with enabled, disabled, unsupported, missing-extra, or load-error state.
- [ ] Regression tests cover sandbox-supported and sandbox-unsupported languages.
- [ ] Dispatcher and plugin registry paths treat expected unavailable capabilities as quiet skips, while unexpected plugin failures still surface as errors.
- [ ] `docs/SUPPORT_MATRIX.md` and sandbox docs describe P24's actual runtime states and keep sandbox-default-on as the documented default.
- [ ] Existing sandbox-default-on, plugin sandbox, dispatcher, and P23 doc truth tests still pass.
