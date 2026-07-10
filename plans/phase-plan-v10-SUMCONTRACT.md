---
phase_loop_plan_version: 1
phase: SUMCONTRACT
roadmap: specs/phase-plans-v10.md
roadmap_sha256: 7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e
---

# SUMCONTRACT: Summarization Contract And Hermetic Tests

## Context
Give every summarization path one immutable typed result, normalize provider output at the boundary, and keep default tests independent of network services.

## Interface Freeze Gates
- [ ] IF-0-SUMCONTRACT-1 — `summarize_file_chunks` always returns `SummaryGenerationResult`; generated items and ID collections are immutable, and handlers consume named fields only.

## Lane Index & Dependencies
SL-0 — Typed result and handler adoption
  Depends on: (none)
  Blocks: SL-1
  Parallel-safe: no

SL-1 — Hermetic provider and integration verification
  Depends on: SL-0
  Blocks: (none)
  Parallel-safe: no

## Lanes

### SL-0 — Typed result and handler adoption
- **Scope**: Remove list/result unions from the file summarization path and expose immutable generated-summary records and complete counters.
- **Owned files**: `mcp_server/indexing/summarization.py`, `mcp_server/cli/tool_handlers.py`, `tests/test_summarization.py`
- **Interfaces provided**: IF-0-SUMCONTRACT-1
- **Interfaces consumed**: IF-0-READYREC-1 (pre-existing), `FileBatchSummarizer` provider adapters (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add empty, partial, success, timeout, and provider-failure cases plus a regression proving `summarize_sample` never iterates or calls `len()` on the result wrapper.
  - impl: Add an immutable generated-summary item, normalize provider records once, make recovery helpers return one collection type, and make `SummaryGenerationResult` the only public return shape.
  - impl: Update `summarize_sample` and write-summary payloads to read named result fields and preserve missing IDs and counters.
  - verify: Run `uv run --python 3.12 pytest tests/test_summarization.py -q --no-cov`.

### SL-1 — Hermetic provider and integration verification
- **Scope**: Prove the contract through multi-repository and provider/storage boundaries without live service access.
- **Owned files**: `tests/integration/test_multi_repo_server.py`, `tests/test_tool_handlers_readiness.py`
- **Interfaces provided**: none
- **Interfaces consumed**: IF-0-SUMCONTRACT-1
- **Parallel-safe**: no
- **Tasks**:
  - test: Use injected provider and storage fakes for all default summarization tests and add explicit socket denial around the targeted test command.
  - test: Verify zero-summary and partial-summary results remain valid typed responses in multi-repository handlers.
  - verify: Run `uv run --python 3.12 pytest tests/test_summarization.py tests/test_tool_handlers_readiness.py tests/integration/test_multi_repo_server.py -q --no-cov`.

## Verification
- Run `uv run --python 3.12 pytest tests/test_summarization.py tests/test_tool_handlers_readiness.py tests/integration/test_multi_repo_server.py -q --no-cov`.
- Run targeted `flake8` on phase-owned Python files and `git diff --check`.
- Preserve a base-commit reproduction showing the old `SummaryGenerationResult` cannot be safely consumed as a list.

## Execution Notes
- No summarization provider or vector backend may be contacted by the default verification command.
- Public release documentation has no delta; this phase changes the internal summarization contract and additive response metadata only.

## Acceptance Criteria
- [ ] `tests/test_summarization.py` proves immutable generated items and one typed return for empty, partial, successful, timed-out, and failed-provider cases.
- [ ] A handler regression in `tests/test_summarization.py` proves `summarize_sample` consumes `.summaries` and counters without wrapper iteration or `len()`.
- [ ] The targeted test command passes with network sockets denied.
- [ ] `tests/integration/test_multi_repo_server.py` proves zero-summary and partial results remain repository-scoped and structured.
- [ ] Targeted `flake8` and `git diff --check` pass.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `summarization internal API and MCP summary response schema`
- evidence paths: `tests/test_summarization.py and tests/integration/test_multi_repo_server.py`
- redaction posture: `metadata_only`
- downstream handling: `none`
