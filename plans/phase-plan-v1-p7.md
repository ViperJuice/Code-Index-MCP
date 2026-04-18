# P7: Doc Truth — Agent & Machine Audiences

## Context

Phases P1–P6B of the multi-repo refactor have shipped. The audit that followed revealed three agent/machine-facing artifacts that still reflect pre-refactor reality: `AGENTS.md` (the agent-facing developer instructions), `specs/active/architecture.md` (the C4 diagrams architects and agents consult), and the MCP tool JSON schemas in `mcp_server/cli/stdio_runner.py` (consumed by MCP clients). This phase brings all three into alignment. It does not touch customer-facing prose (P8) or handler implementations (P9).

**AGENTS.md** (388 LOC, 14 `##` sections): stale claims at `L8` ("MCP Status: Fully operational"), `L29` ("Production-ready Docker and Kubernetes configurations"). FastAPI-primary framing at `L12` (endpoint list) and `L310-312` (`@app.get(...)` code example). No "Beta status" note anywhere. The Multi-Repo Operation section at `L135-168` already exists and already references `RepoContext`, `StoreRegistry`, `MultiRepositoryWatcher`, `MCP_ALLOWED_ROOTS` — the multi-repo model exit criterion is already satisfied in content; only a beta-status note is missing.

**specs/active/architecture.md** (100 LOC, Mermaid C4): the L2 Container diagram (`L22-51`) already contains `MultiRepositoryWatcher` (`L34`), `RefPoller` (`L35`), and `HandshakeGate` (`L30`). The L3 Component diagram (`L53-96`) has 5 Container_Boundary groups (Core, Registry, Plugin, Storage, Services) and is missing `MultiRepositoryWatcher`. The spec requires only `MultiRepositoryWatcher` on L3; `RefPoller` and `HandshakeGate` are adjacent gaps but deferred to a follow-up phase per arch-baseline recommendation (adding more widens SL-1's acceptance surface without differential value).

**mcp_server/cli/stdio_runner.py** (tool-list in `_build_tool_list()` at `L54-137`): `search_code` (`L68-81`) and `symbol_lookup` (`L57-66`) already advertise `repository`. `reindex` (`L93-99`), `write_summaries` (`L101-110`), and `summarize_sample` (`L112-126`) do not. Handler safety verified: `handle_reindex`, `handle_write_summaries`, `handle_summarize_sample` in `tool_handlers.py` do not currently read `arguments.get("repository")`, so schema-only adds cause zero behavior change (handler-side wiring is P9).

`CLAUDE.md` is a clean 30-line redirector — no edits needed, invariant for both lanes.

## Interface Freeze Gates

- [ ] **IF-0-P7-1** — `AGENTS.md` Current State section (lines 5-31 in source) no longer contains the strings `Fully operational` or `Production-ready`, contains exactly one "Beta status" admonition naming STDIO as primary and FastAPI as secondary admin surface, and no longer frames FastAPI endpoints as the primary surface. Multi-Repo Operation section (L135-168) continues to reference `RepoContext`, `StoreRegistry`, `MultiRepositoryWatcher`, `MCP_ALLOWED_ROOTS`.
- [ ] **IF-0-P7-2** — `specs/active/architecture.md` L3 Component diagram contains a `MultiRepositoryWatcher` node with at least one `Rel(...)` edge connecting it to an existing component (suggested: `Rel(enhanced_dispatcher, multi_repo_watcher, "Observes file changes")` and `Rel(multi_repo_watcher, store_registry, "Invalidates on change")`). `RefPoller` and `HandshakeGate` additions to L3 are deferred — not part of this freeze.
- [ ] **IF-0-P7-3** — `_build_tool_list()` in `mcp_server/cli/stdio_runner.py` returns `Tool` entries where `inputSchema["properties"]` contains a `repository` property on all five path-accepting tools: `search_code`, `symbol_lookup`, `reindex`, `write_summaries`, `summarize_sample`. The property description is verbatim `"Repository ID, path, or git URL. Defaults to current repository."`. `repository` is NOT in any tool's `inputSchema.get("required", [])`. `handshake`, `get_status`, `list_plugins` do not have the property.
- [ ] **IF-0-P7-4** — `CLAUDE.md` and `mcp_server/CLAUDE.md` are byte-identical to their pre-P7 state (cross-cutting invariant; both lanes must respect).

## Lane Index & Dependencies

```
SL-1 — Markdown rewrites (AGENTS.md + architecture.md L3)
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-2 — Tool-schema additions (stdio_runner.py + parity test)
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes
```

## Lanes

### SL-1 — Markdown rewrites (AGENTS.md + architecture.md L3)

- **Scope**: Rewrite `AGENTS.md` `Current State` section (lines 5-31) to strip `Fully operational` and `Production-ready` claims, rewrite the FastAPI-primary endpoint list (L12) and `@app.get(...)` code example (L310-312) to frame STDIO as primary and FastAPI as secondary admin surface, and add a single "Beta status" admonition near the top. Verify the existing Multi-Repo Operation section (L135-168) continues to satisfy IF-0-P7-1's content check. In `specs/active/architecture.md`, add a `MultiRepositoryWatcher` Component node to the L3 diagram (lines 53-96) with `Rel(...)` edges connecting to `enhanced_dispatcher` and `store_registry`. Do not touch `CLAUDE.md` or `mcp_server/CLAUDE.md`.
- **Owned files**: `AGENTS.md`, `specs/active/architecture.md`, `tests/docs/test_p7_markdown_alignment.py` (new).
- **Interfaces provided**: IF-0-P7-1, IF-0-P7-2.
- **Interfaces consumed**: (pre-existing) — root lane with no cross-lane deps.
- **Execution hint**: `claude-sonnet-4-6` / medium — judgment-heavy prose rewrite; the naive "no longer fully operational" phrasing silently re-matches the grep. Think carefully about replacement wording.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/docs/test_p7_markdown_alignment.py` | stale-claim greps on AGENTS.md (`Fully operational`, `Production-ready`, `100% implemented`, `fully operational`) all return zero; FastAPI-primary framing greps return zero (`FastAPI gateway with all endpoints`, `@app\.get\("/(symbol\|search)"\)`); positive checks (`STDIO` appears ≥ 1 time, `RepoContext`+`StoreRegistry`+`MCP_ALLOWED_ROOTS` all present); architecture.md L3 block contains `MultiRepositoryWatcher` | `pytest tests/docs/test_p7_markdown_alignment.py -v --no-cov` |
| SL-1.2 | impl | SL-1.1 | `AGENTS.md`, `specs/active/architecture.md` | — | — |
| SL-1.3 | verify | SL-1.2 | `AGENTS.md`, `specs/active/architecture.md`, `tests/docs/test_p7_markdown_alignment.py` | all SL-1.1 assertions pass; `git diff --name-only HEAD~..HEAD` does not include `CLAUDE.md` or `mcp_server/CLAUDE.md` | `pytest tests/docs/test_p7_markdown_alignment.py -v --no-cov && ! git diff --name-only main..HEAD \| grep -E '^(CLAUDE\.md\|mcp_server/CLAUDE\.md)$'` |

### SL-2 — Tool-schema additions (stdio_runner.py + parity test)

- **Scope**: In `mcp_server/cli/stdio_runner.py::_build_tool_list()` (lines 54-137), add a `"repository": {"type": "string", "description": "Repository ID, path, or git URL. Defaults to current repository."}` property to the `inputSchema.properties` block of `reindex` (L93-99), `write_summaries` (L101-110), and `summarize_sample` (L112-126). Description text is copied verbatim from the existing entries at `search_code` (L75) and `symbol_lookup` (L63). Do NOT add `repository` to any `required` array. Do NOT modify handler code in `tool_handlers.py` (handler-side wiring is P9). Add `tests/docs/test_p7_schema_alignment.py` that imports `_build_tool_list` and asserts per-tool schema shape so future drift is caught deterministically.
- **Owned files**: `mcp_server/cli/stdio_runner.py` (tool-list only; do not touch `_serve()` or dispatch), `tests/docs/test_p7_schema_alignment.py` (new).
- **Interfaces provided**: IF-0-P7-3.
- **Interfaces consumed**: (pre-existing) — root lane with no cross-lane deps.
- **Execution hint**: `claude-haiku-4-5` / low — small components against a frozen schema style. Mechanical.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/docs/test_p7_schema_alignment.py` | imports `_build_tool_list`; asserts `repository` present in `inputSchema["properties"]` for `search_code`, `symbol_lookup`, `reindex`, `write_summaries`, `summarize_sample`; absent from `get_status`, `list_plugins`, `handshake`; NOT in any `inputSchema.get("required", [])`; description string matches `"Repository ID, path, or git URL. Defaults to current repository."` verbatim | `pytest tests/docs/test_p7_schema_alignment.py -v --no-cov` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/cli/stdio_runner.py` | — | — |
| SL-2.3 | verify | SL-2.2 | `mcp_server/cli/stdio_runner.py`, `tests/docs/test_p7_schema_alignment.py`, `tests/test_handshake.py` | all SL-2.1 assertions pass; existing stdio tests still pass (no collateral breakage) | `pytest tests/docs/test_p7_schema_alignment.py tests/test_handshake.py -v --no-cov` |

## Execution Notes

- **Single-writer files**: none. SL-1 owns `AGENTS.md`, `specs/active/architecture.md`, and `tests/docs/test_p7_markdown_alignment.py`. SL-2 owns `mcp_server/cli/stdio_runner.py` and `tests/docs/test_p7_schema_alignment.py`. Fully disjoint.
- **Known destructive changes**: none — every lane is purely additive. SL-1 removes offending lines inside existing sections but no files are deleted. SL-2 adds properties to existing inputSchema blocks.
- **Expected add/add conflicts**: none — SL-1 and SL-2 touch different directories.
- **SL-0 re-exports**: none — no SL-0 preamble lane in this phase.
- **Worktree naming**: execute-phase allocates unique names via `scripts/allocate_worktree_name.sh`. Plan doc does not spell out lane worktree paths.
- **Stale-base guidance**: Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. Both lanes are root lanes (no upstream dependency), so stale-base-versus-upstream-SL is not a concern for P7. However, if a lane's worktree base is pre-P6B merge (`d795d36` or earlier), the teammate MUST stop and report — do not silently rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.
- **Replacement-phrasing hazard (SL-1)**: the naive replacement "no longer fully operational" silently re-matches the grep `Fully operational`. The verify step must re-run the stale-claim greps post-edit; SL-1.1 enforces this. Prefer affirmative phrasing that does not contain either substring (e.g., "Multi-repo support is beta. STDIO is the primary surface; FastAPI is a secondary admin surface.").
- **Test coupling check (SL-1)**: before editing `AGENTS.md`, grep `tests/` for any literal string present in lines 8, 12, 29, 310-312. If a test asserts the stale phrasing exists, SL-1 owns updating that test in the same commit. (Pre-check: none known at plan time.)
- **Mermaid edge requirement (SL-1)**: the new `MultiRepositoryWatcher` node in architecture.md L3 must have at least one `Rel(...)` edge or the diagram reads disconnected. Suggested: `Rel(enhanced_dispatcher, multi_repo_watcher, "Observes file changes")` and `Rel(multi_repo_watcher, store_registry, "Invalidates on change")`.
- **No handler edits (SL-2)**: the spec and the arch-baseline both require schema-only changes in this phase. Handler-side wiring is P9. A teammate that edits `mcp_server/cli/tool_handlers.py` is out of scope — reject at verify time.

## Acceptance Criteria

- [ ] `grep -nE '(Fully operational|Production-ready|100% implemented|fully operational)' AGENTS.md` returns zero matches — asserted programmatically in `tests/docs/test_p7_markdown_alignment.py`.
- [ ] `grep -nE 'curl .*(search|symbol)' AGENTS.md` returns zero matches (regression guard, currently passing) — asserted programmatically in `tests/docs/test_p7_markdown_alignment.py`.
- [ ] `grep -nE 'FastAPI gateway with all endpoints' AGENTS.md` returns zero matches — asserted programmatically in `tests/docs/test_p7_markdown_alignment.py`.
- [ ] `grep -nE '@app\.get\("/(symbol|search)"\)' AGENTS.md` returns zero matches — asserted programmatically in `tests/docs/test_p7_markdown_alignment.py`.
- [ ] `grep -c 'STDIO' AGENTS.md` returns a count ≥ 1 (positive STDIO-primary framing check) — asserted programmatically in `tests/docs/test_p7_markdown_alignment.py`.
- [ ] `AGENTS.md` contains a "Beta status" admonition and the Multi-Repo section references `RepoContext`, `StoreRegistry`, `MCP_ALLOWED_ROOTS` — asserted programmatically in `tests/docs/test_p7_markdown_alignment.py`.
- [ ] `specs/active/architecture.md` L3 component diagram contains a `MultiRepositoryWatcher` node with at least one `Rel(...)` edge — asserted programmatically in `tests/docs/test_p7_markdown_alignment.py`.
- [ ] `CLAUDE.md` and `mcp_server/CLAUDE.md` are byte-identical to their pre-P7 state (`git diff main -- CLAUDE.md mcp_server/CLAUDE.md` is empty; SL-1.3 verify step asserts).
- [ ] `_build_tool_list()` in `mcp_server/cli/stdio_runner.py` returns `Tool` entries where `inputSchema["properties"]` contains `repository` for `search_code`, `symbol_lookup`, `reindex`, `write_summaries`, `summarize_sample`; absent from `handshake`, `get_status`, `list_plugins`; NOT in any `required` array (SL-2.1 asserts programmatically).
- [ ] `repository` description is `"Repository ID, path, or git URL. Defaults to current repository."` verbatim on all 5 tools (SL-2.1 asserts).
- [ ] `mcp_server/cli/tool_handlers.py` is byte-identical to its pre-P7 state — no handler code modified (`git diff main -- mcp_server/cli/tool_handlers.py` is empty; verify-step assertion in both SL-1.3 and SL-2.3).
- [ ] Existing `tests/test_handshake.py` still passes post-SL-2 (no stdio regression).

## Verification

```bash
# SL-1 markdown parity
pytest tests/docs/test_p7_markdown_alignment.py -v --no-cov

# SL-2 schema parity
pytest tests/docs/test_p7_schema_alignment.py -v --no-cov

# Cross-lane invariants
git diff main -- CLAUDE.md mcp_server/CLAUDE.md mcp_server/cli/tool_handlers.py
# ↑ must be empty

# Existing stdio tests unbroken
pytest tests/test_handshake.py -v --no-cov

# Full P7 suite
pytest tests/docs/test_p7_markdown_alignment.py tests/docs/test_p7_schema_alignment.py tests/test_handshake.py -v --no-cov
```

All assertions pass, and the `git diff` invariant queries return empty output. Any handler-code edit, any `CLAUDE.md` edit, or any regressed stdio/handshake test fails the phase.
