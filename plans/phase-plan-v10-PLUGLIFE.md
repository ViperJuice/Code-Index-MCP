---
phase_loop_plan_version: 1
phase: PLUGLIFE
roadmap: specs/phase-plans-v10.md
roadmap_sha256: 7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e
---

# PLUGLIFE: Plugin Worker Lifecycle And Resource Governance

## Context
Make sandbox plugin allocation lazy and bounded, put every worker close behind one lifecycle owner, and prove parent shutdown cannot leave worker processes behind.

## Interface Freeze Gates
- [ ] IF-0-PLUGLIFE-1 — `MemoryAwarePluginManager` owns cached plugin adapters and exposes `get_plugin`, `evict_repo`, `resource_snapshot`, and `shutdown`; registries delegate close operations.
- [ ] IF-0-PLUGLIFE-2 — Worker slots and child RSS are hard caps with deterministic LRU reclamation, typed backpressure, bounded sampling, and parent-pipe/process-death cleanup.

## Lane Index & Dependencies
SL-0 — Lifecycle owner and resource policy
  Depends on: (none)
  Blocks: SL-1, SL-2
  Parallel-safe: no

SL-1 — Lazy registry and dispatcher integration
  Depends on: SL-0
  Blocks: SL-2
  Parallel-safe: no

SL-2 — Shutdown and process-death proof
  Depends on: SL-0, SL-1
  Blocks: (none)
  Parallel-safe: no

## Lanes

### SL-0 — Lifecycle owner and resource policy
- **Scope**: Consolidate plugin ownership, deterministic eviction, idle expiry, worker/RSS accounting, and typed allocation refusal in the memory-aware manager.
- **Owned files**: `mcp_server/plugins/memory_aware_manager.py`, `tests/test_memory_aware_manager.py`
- **Interfaces provided**: IF-0-PLUGLIFE-1, IF-0-PLUGLIFE-2
- **Interfaces consumed**: `SandboxedPlugin.close` and worker resource introspection (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add fake-clock and fake-resource tests for per-repo used-language scaling, deterministic LRU, worker-count pressure, child-RSS pressure, failed measurement, idle expiry, repo eviction, and idempotent shutdown.
  - impl: Add frozen resource snapshots and a typed backpressure exception, configured worker/RSS/idle/sample limits, and fail-closed capacity checks.
  - impl: Make eviction call `close`, remove all strong references, support repo-scoped eviction, and make shutdown idempotently close every cached plugin.
  - verify: Run `uv run --python 3.12 pytest tests/test_memory_aware_manager.py -q --no-cov`.

### SL-1 — Lazy registry and dispatcher integration
- **Scope**: Select one likely language from a file path, keep status reads side-effect free, and route all registry lifecycle calls through the manager.
- **Owned files**: `mcp_server/plugins/plugin_set_registry.py`, `mcp_server/plugins/sandboxed_plugin.py`, `mcp_server/sandbox/supervisor.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`, `tests/test_plugin_set_registry.py`, `tests/security/test_plugin_sandbox.py`
- **Interfaces provided**: none
- **Interfaces consumed**: IF-0-PLUGLIFE-1, IF-0-PLUGLIFE-2, `PluginFactory` extension registry (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Prove empty status/list reads spawn no workers, two used languages allocate at most two adapters, repository eviction closes workers, and resource metadata reflects a live sandbox child.
  - impl: Replace eager all-language registry construction with extension-directed lookup while preserving stable per-repo list identity for already loaded plugins.
  - impl: Add non-spawning worker PID/RSS/running-state introspection to the sandbox adapter and supervisor, and retain stdin EOF as the parent-pipe watchdog.
  - impl: Update dispatcher health and routing paths to consume lazy registry APIs and resource snapshots without broad plugin loading.
  - verify: Run `uv run --python 3.12 pytest tests/test_plugin_set_registry.py tests/security/test_plugin_sandbox.py tests/test_dispatcher.py -q --no-cov`.

### SL-2 — Shutdown and process-death proof
- **Scope**: Close plugin workers on all normal server shutdown paths and verify parent signal/crash behavior with real subprocesses.
- **Owned files**: `mcp_server/cli/stdio_runner.py`, `mcp_server/gateway.py`, `tests/integration/test_sigterm_shutdown.py`, `tests/integration/plugin_worker_parent.py`
- **Interfaces provided**: none
- **Interfaces consumed**: IF-0-PLUGLIFE-1, IF-0-PLUGLIFE-2
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend graceful-shutdown order assertions to include dispatcher/plugin shutdown and add subprocess probes for SIGTERM, SIGINT, and SIGKILL parent exit with bounded child reaping.
  - impl: Add dispatcher shutdown to STDIO signal/finally cleanup and gateway application shutdown, preserving idempotence and bounded timeouts.
  - impl: Use the existing worker stdin pipe as the cross-platform parent watchdog; avoid thread-unsafe subprocess pre-exec hooks.
  - verify: Run `uv run --python 3.12 pytest tests/integration/test_sigterm_shutdown.py tests/security/test_plugin_sandbox.py -q --no-cov`.

## Verification
- Run `uv run --python 3.12 pytest tests/test_memory_aware_manager.py tests/test_plugin_set_registry.py tests/security/test_plugin_sandbox.py tests/integration/test_sigterm_shutdown.py -q --no-cov`.
- Run dispatcher integration coverage after lazy-routing changes: `uv run --python 3.12 pytest tests/test_dispatcher.py -q --no-cov`.
- Run targeted `flake8` on phase-owned Python files and `git diff --check`.
- Record worker PID evidence before and after each real parent-signal probe; every child must disappear within the bounded timeout.

## Execution Notes
- The roadmap's `mcp_server/plugin_sandbox/**` pointer maps to the implemented `mcp_server/sandbox/**` package.
- Worker accounting counts cached sandbox adapters as reserved worker slots and reports live child RSS separately, preventing a first call from bypassing the count cap.
- RSS sampling is monotonic-time bounded; an unavailable or failed process measurement blocks new allocation until a valid sample is available.
- Public release documentation has no delta in this phase; operator-facing resource settings are finalized with release documentation in RELEASESAFE.

## Acceptance Criteria
- [ ] Unit tests prove deterministic LRU eviction, hard worker-slot and child-RSS caps, typed backpressure, failed-measurement refusal, and idle expiry.
- [ ] Registry tests prove status/list reads are non-spawning and plugin count scales with languages actually requested per repository.
- [ ] Repo eviction and manager shutdown call every adapter's `close` exactly once and remove strong references.
- [ ] Real-process SIGTERM, SIGINT, and SIGKILL probes leave no sandbox child process after the bounded reaping interval.
- [ ] Targeted plugin, dispatcher, security, and shutdown tests pass with targeted `flake8` and `git diff --check` clean.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `plugin lifecycle, resource policy, sandbox parent-death contract`
- evidence paths: `tests/test_memory_aware_manager.py, tests/test_plugin_set_registry.py, tests/security/test_plugin_sandbox.py, and tests/integration/test_sigterm_shutdown.py`
- redaction posture: `metadata_only`
- downstream handling: `none`
- blocker_class: contract_bug if worker ownership, hard allocation limits, or hard-parent-death cleanup remains unproven
