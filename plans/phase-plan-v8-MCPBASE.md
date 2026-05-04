---
phase_loop_plan_version: 1
phase: MCPBASE
roadmap: specs/phase-plans-v8.md
roadmap_sha256: 25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11
---
# MCPBASE: MCP Baseline Compatibility Audit

## Context

MCPBASE is the opening execution phase for the v8 MCP modernization roadmap.
Its job is to freeze the current public MCP baseline before later phases add
metadata, structured results, tasks, or transport variants.

Current repo state gathered during planning:

- `specs/phase-plans-v8.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v8.md` matches the required
  `25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11`.
- Canonical runner state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `MCPBASE` as the current
  `unplanned` phase on branch `roadmap-v8-mcp-modernization` at
  `fa77ba19750e99e6f9a77fc376e6b3d1bbb64d33` with a clean worktree. Legacy
  `.codex/phase-loop/` artifacts are compatibility-only and are not
  authoritative for this run.
- The target artifact `plans/phase-plan-v8-MCPBASE.md` did not exist before
  this planning run.
- `mcp_server/cli/stdio_runner.py` is the MCP primary surface today. Its
  `_build_tool_list()` still publishes the current eight public tools
  `symbol_lookup`, `search_code`, `get_status`, `list_plugins`, `reindex`,
  `write_summaries`, `summarize_sample`, and `handshake`, with only
  `name`, `description`, and `inputSchema` populated.
- `mcp_server/cli/server_commands.py` keeps the transport split concrete:
  `stdio()` delegates to `mcp_server.cli.stdio_runner.run`, while `serve()`
  launches `uvicorn.run("mcp_server.gateway:app", ...)` for the FastAPI admin
  surface.
- Existing tests already cover readiness-gated tool descriptions and repository
  schema parity:
  `tests/test_stdio_tool_descriptions.py`,
  `tests/test_tool_schema_handler_parity.py`,
  `tests/docs/test_p7_schema_alignment.py`, and
  `tests/test_server_commands.py`. They do not yet prove an official Python MCP
  SDK client can complete `initialize -> tools/list -> tools/call` through the
  STDIO runner, and they do not yet freeze an explicit contract that
  `mcp-index serve` is an admin/debug HTTP surface rather than MCP Streamable
  HTTP.
- User-facing docs already trend in the right direction:
  `README.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`, and
  `docs/SUPPORT_MATRIX.md` describe STDIO as the primary LLM surface and
  FastAPI as secondary/admin. MCPBASE should tighten those statements into an
  auditable compatibility baseline rather than broadening the transport story.

Practical planning boundary:

- MCPBASE may add focused tests, narrow CLI wording, and a docs/status audit
  artifact that records the current SDK/spec/tool baseline.
- MCPBASE must not migrate tool metadata, add output schemas, introduce
  `structuredContent`, implement tasks, or imply that the existing FastAPI
  gateway is already a spec-compliant remote MCP transport.

## Interface Freeze Gates

- [ ] IF-0-MCPBASE-1 - STDIO baseline compatibility contract:
      an official Python MCP SDK smoke can complete `initialize`, `tools/list`,
      and representative `tools/call` operations against
      `python -m mcp_server.cli.stdio_runner`, and the smoke proves the
      currently supported tool names still work on the MCP primary surface.
- [ ] IF-0-MCPBASE-2 - No-argument compatibility contract:
      the baseline explicitly preserves current no-argument tool behavior for
      `get_status` and `list_plugins`, and documents that later MCP phases must
      not silently break those call shapes.
- [ ] IF-0-MCPBASE-3 - Transport-boundary contract:
      `mcp-index serve` and the FastAPI gateway are documented and tested as a
      secondary admin/debug HTTP surface, not as MCP Streamable HTTP, unless a
      later roadmap phase deliberately introduces a separate remote MCP
      transport.
- [ ] IF-0-MCPBASE-4 - Baseline audit artifact contract:
      a docs/status artifact records the current Python MCP SDK version, the
      targeted MCP spec revision `2025-11-25`, the stable public tool names,
      the preserved no-argument tools, and the explicit deferrals to later
      phases (`MCPMETA`, `MCPSTRUCT`, `MCPTASKS`, `MCPTRANSPORT`, `MCPAUTH`).
- [ ] IF-0-MCPBASE-5 - No-migration contract:
      MCPBASE adds evidence and wording only. It does not change tool metadata
      fields, output schemas, structured result behavior, task wiring, or the
      FastAPI endpoint surface itself.

## Lane Index & Dependencies

- SL-0 - Official SDK STDIO smoke and runtime baseline freeze; Depends on: (none); Blocks: SL-1, SL-2; Parallel-safe: yes
- SL-1 - FastAPI admin-boundary CLI and docs truth surface; Depends on: (none); Blocks: SL-2; Parallel-safe: yes
- SL-2 - Baseline audit artifact reducer and contract closeout; Depends on: SL-0, SL-1; Blocks: MCPBASE acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 ----\
          -> SL-2 -> MCPBASE acceptance
SL-1 ----/
```

## Lanes

### SL-0 - Official SDK STDIO Smoke And Runtime Baseline Freeze

- **Scope**: Add the narrowest possible runtime evidence that the existing
  STDIO server still works with the official Python MCP SDK client for
  `initialize`, `tools/list`, and representative `tools/call` operations,
  while freezing the current stable tool names and no-argument runtime
  behavior.
- **Owned files**: `mcp_server/cli/stdio_runner.py`, `tests/smoke/test_mcpbase_stdio_smoke.py`, `tests/test_stdio_tool_descriptions.py`
- **Interfaces provided**: IF-0-MCPBASE-1 STDIO baseline compatibility contract;
  IF-0-MCPBASE-2 no-argument compatibility contract;
  runtime evidence consumed by the SL-2 audit artifact
- **Interfaces consumed**: existing `mcp_server.cli.stdio_runner.run`,
  `_build_tool_list()`, the official `mcp` Python SDK client APIs, current
  public tool names, repo-local temp git fixtures, and the existing readiness
  wording already frozen by `tests/test_stdio_tool_descriptions.py`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add a focused smoke under `tests/smoke/test_mcpbase_stdio_smoke.py`
    that launches `python -m mcp_server.cli.stdio_runner` in a controlled temp
    repo and uses the official Python MCP SDK client path to complete
    `initialize`, `tools/list`, and representative `tools/call`.
  - test: Require `tools/list` to expose the current public tool names
    `symbol_lookup`, `search_code`, `get_status`, `list_plugins`, `reindex`,
    `write_summaries`, `summarize_sample`, and `handshake` without claiming any
    new metadata fields in this phase.
  - test: Freeze the current no-argument contract by proving `get_status({})`
    and `list_plugins({})` remain callable without required inputs through the
    MCP client surface.
  - test: Use one representative path-bearing tool call on a ready temp repo
    after setup, but keep the smoke lightweight and compatibility-oriented
    rather than turning it into a full metadata or task suite.
  - impl: Keep any test-only subprocess or async helper local to this lane and
    avoid production code edits unless the current runner needs a small
    compatibility-only startup hook to make the official SDK smoke reliable.
  - impl: Do not add `title`, annotations, output schemas, `structuredContent`,
    task envelopes, or transport claims here; those belong to later phases.
  - verify: `uv run pytest tests/smoke/test_mcpbase_stdio_smoke.py tests/test_stdio_tool_descriptions.py -q --no-cov`

### SL-1 - FastAPI Admin-Boundary CLI And Docs Truth Surface

- **Scope**: Tighten the CLI wording and the smallest set of user-facing docs
  so the current FastAPI gateway is explicitly framed as a secondary
  admin/debug HTTP surface and not advertised as MCP Streamable HTTP.
- **Owned files**: `mcp_server/cli/server_commands.py`, `tests/test_server_commands.py`, `README.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`, `docs/SUPPORT_MATRIX.md`
- **Interfaces provided**: IF-0-MCPBASE-3 transport-boundary contract;
  doc-truth inputs for IF-0-MCPBASE-4 baseline audit artifact;
  negative transport claim preservation for IF-0-MCPBASE-5
- **Interfaces consumed**: existing `serve()` and `stdio()` command wiring;
  current README/install wording around `mcp-index serve`; current primary vs
  secondary surface wording in `README.md`, `docs/GETTING_STARTED.md`,
  `docs/MCP_CONFIGURATION.md`, and `docs/SUPPORT_MATRIX.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `tests/test_server_commands.py` so the CLI contract proves
    `serve()` still boots `mcp_server.gateway:app` and its help/doc wording
    identifies the command as the FastAPI admin/debug HTTP path rather than an
    MCP transport entrypoint.
  - impl: Update `mcp_server/cli/server_commands.py` wording only as needed to
    make the boundary explicit in help strings and command docstrings while
    preserving current flags and behavior.
  - impl: Refresh only the docs that actually state startup/transport posture:
    `README.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`, and
    `docs/SUPPORT_MATRIX.md`.
  - impl: Keep the doc edits phrased so the downstream SL-2 contract test can
    assert STDIO-primary and FastAPI-secondary wording without needing a second
    round of wording cleanup.
  - impl: Keep this lane non-invasive. Do not add a new FastAPI endpoint, do
    not rename commands, and do not imply remote auth or Streamable HTTP
    support that does not exist yet.
  - verify: `uv run pytest tests/test_server_commands.py -q --no-cov`
  - verify: `rg -n "Streamable HTTP|secondary|admin|stdio|mcp-index serve|FastAPI" mcp_server/cli/server_commands.py README.md docs/GETTING_STARTED.md docs/MCP_CONFIGURATION.md docs/SUPPORT_MATRIX.md`

### SL-2 - Baseline Audit Artifact Reducer And Contract Closeout

- **Scope**: Reduce the runtime and docs findings into a single docs/status
  artifact that records the frozen MCP baseline and the exact modernization
  work intentionally deferred to later v8 phases.
- **Owned files**: `docs/status/MCP_BASELINE_COMPATIBILITY_AUDIT.md`, `tests/docs/test_mcpbase_baseline_audit.py`
- **Interfaces provided**: IF-0-MCPBASE-4 baseline audit artifact contract;
  closeout evidence for IF-0-MCPBASE-5 no-migration contract
- **Interfaces consumed**: SL-0 official SDK smoke results and stable tool
  names; SL-1 transport-boundary wording; current dependency truth from
  `pyproject.toml` and `uv.lock`; roadmap spec references from
  `specs/phase-plans-v8.md`; and the existing repo posture that later phases
  will own metadata, structured results, tasks, transport, and auth changes
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_mcpbase_baseline_audit.py` to freeze the final
    docs/status claims: targeted spec revision `2025-11-25`, current Python MCP
    SDK version source, stable public tool names, preserved no-argument tools,
    STDIO-primary/FastAPI-secondary wording, and explicit deferral of
    metadata/structured results/tasks/transport/auth work to later phases.
  - impl: Write `docs/status/MCP_BASELINE_COMPATIBILITY_AUDIT.md` as the
    single MCPBASE status artifact. It should cite the official SDK/spec
    baseline, the exact tool names, the no-argument compatibility constraints,
    the representative smoke coverage, and the negative claim that
    `mcp-index serve` is not current Streamable HTTP support.
  - impl: Record the current baseline faithfully rather than polishing it into
    a marketing summary. The artifact should separate confirmed current facts
    from explicit later-phase work items.
  - impl: If a broader doc cleanup feels tempting, defer it. This reducer is
    only for baseline capture and contract closeout.
  - verify: `uv run pytest tests/docs/test_mcpbase_baseline_audit.py -q --no-cov`
  - verify: `uv run pytest tests/smoke/test_mcpbase_stdio_smoke.py tests/test_stdio_tool_descriptions.py tests/test_server_commands.py tests/docs/test_mcpbase_baseline_audit.py -q --no-cov`
  - verify: `git diff --stat -- mcp_server/cli/server_commands.py README.md docs/GETTING_STARTED.md docs/MCP_CONFIGURATION.md docs/SUPPORT_MATRIX.md docs/status/MCP_BASELINE_COMPATIBILITY_AUDIT.md tests/smoke/test_mcpbase_stdio_smoke.py tests/test_stdio_tool_descriptions.py tests/test_server_commands.py tests/docs/test_mcpbase_baseline_audit.py`

## Verification

Planning-only work is complete once this artifact is written and staged. Do
not execute the commands below during plan creation; run them during
`codex-execute-phase` or manual MCPBASE execution.

Lane-specific checks:

```bash
uv run pytest tests/smoke/test_mcpbase_stdio_smoke.py tests/test_stdio_tool_descriptions.py -q --no-cov
uv run pytest tests/test_server_commands.py -q --no-cov
rg -n "Streamable HTTP|secondary|admin|stdio|mcp-index serve|FastAPI" \
  mcp_server/cli/server_commands.py \
  README.md \
  docs/GETTING_STARTED.md \
  docs/MCP_CONFIGURATION.md \
  docs/SUPPORT_MATRIX.md \
  docs/status/MCP_BASELINE_COMPATIBILITY_AUDIT.md \
  tests/test_server_commands.py \
  tests/docs/test_mcpbase_baseline_audit.py
```

Whole-phase verification after code changes:

```bash
uv run pytest \
  tests/smoke/test_mcpbase_stdio_smoke.py \
  tests/test_stdio_tool_descriptions.py \
  tests/test_server_commands.py \
  tests/docs/test_mcpbase_baseline_audit.py \
  -q --no-cov
git status --short -- \
  mcp_server/cli/server_commands.py \
  README.md \
  docs/GETTING_STARTED.md \
  docs/MCP_CONFIGURATION.md \
  docs/SUPPORT_MATRIX.md \
  docs/status/MCP_BASELINE_COMPATIBILITY_AUDIT.md \
  tests/smoke/test_mcpbase_stdio_smoke.py \
  tests/test_stdio_tool_descriptions.py \
  tests/test_server_commands.py \
  tests/docs/test_mcpbase_baseline_audit.py \
  plans/phase-plan-v8-MCPBASE.md
```

## Acceptance Criteria

- [ ] An official Python MCP SDK smoke proves the current STDIO runner can
      complete `initialize`, `tools/list`, and representative `tools/call`
      behavior without any metadata, structured-result, or task migration.
- [ ] The current MCP baseline is captured in
      `docs/status/MCP_BASELINE_COMPATIBILITY_AUDIT.md`, including the targeted
      MCP spec revision `2025-11-25`, the current Python MCP SDK version
      source, the stable public tool names, and the preserved no-argument tools
      `get_status` and `list_plugins`.
- [ ] `mcp-index serve` is documented and tested as the FastAPI
      admin/debug HTTP surface rather than MCP Streamable HTTP, while STDIO
      remains the primary MCP entrypoint.
- [ ] MCPBASE makes no tool metadata, result-shape, task, or remote transport
      migration; those deferrals are called out explicitly for `MCPMETA`,
      `MCPSTRUCT`, `MCPTASKS`, `MCPTRANSPORT`, and `MCPAUTH`.
- [ ] The resulting verification set is narrow, reproducible, and scoped to
      compatibility evidence rather than broader feature expansion.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v8-MCPBASE.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v8-MCPBASE.md
  artifact_state: staged
```
