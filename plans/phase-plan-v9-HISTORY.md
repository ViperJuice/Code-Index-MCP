---
phase_loop_plan_version: 1
phase: HISTORY
roadmap: specs/phase-plans-v9.md
roadmap_sha256: 57848534176ac820595f4193459b86b5fdef9f5bfe5bff60a5739d8d9e192d2b
---
# HISTORY: Historical GitHub Issue Context Indexing

## Context

HISTORY is Phase 7 in `specs/phase-plans-v9.md`. The canonical
`.phase-loop/state.json` reports PUBNAME, REPOCLEAN, LOCALCI, COVERAGE,
PROCENV, and FRICTION complete; `HISTORY` is current/unplanned; the worktree was
clean at planner reconciliation time; and the roadmap SHA-256 is
`57848534176ac820595f4193459b86b5fdef9f5bfe5bff60a5739d8d9e192d2b`.
Legacy `.codex/phase-loop/` files are compatibility artifacts only and are not
used to supersede canonical `.phase-loop/` state.

Planning observations:

- FRICTION introduced the generic `search_source_metadata.v1` envelope in
  `mcp_server/indexing/source_metadata.py`, but its typed surface and storage
  filters currently accept only `source_type="friction"` and friction-specific
  categories.
- `mcp_server/storage/sqlite_store.py::search_chunks_by_source_metadata()` is
  the existing metadata-backed search hook; HISTORY should generalize that path
  rather than adding a second search index or a parallel response shape.
- `mcp_server/dispatcher/dispatcher_enhanced.py::EnhancedDispatcher.search()`
  and `mcp_server/cli/tool_handlers.py::handle_search_code()` already preserve
  the legacy search result shape unless source metadata filters are requested.
- PROCENV added `mcp_server/utils/subprocess_env.py::get_full_env()`, which is
  the required subprocess environment helper for any `gh` invocation.
- `mcp-index` command registration lives in `mcp_server/cli/__init__.py`; new
  issue-history ingestion commands should be lazy-registered with other heavy
  CLI commands and tested through Click without requiring live GitHub access.

Planning boundary:

- HISTORY may extend the source metadata schema, add a deterministic GitHub
  issue fetcher/normalizer, add an explicit issue-history ingestion command,
  reuse SQLite chunk metadata for indexed history documents, expose
  `source_type="history"` search filtering, and write metadata-only docs and
  evidence.
- HISTORY must not make live GitHub calls in unit tests, write to GitHub,
  index private issue bodies by default, change package identity, change hosted
  CI posture, or introduce a separate historical search API that bypasses the
  existing `search_code`/`/search` source metadata contract.
- Raw issue body text is not persisted by default. Any optional body-derived
  learnings extraction must be explicit, fixture-backed in tests, metadata-only
  in persisted records, and must never log or expose credential values.

## Interface Freeze Gates

- [ ] IF-0-HISTORY-1 — Historical issue source contract: `source_type="history"`
      records use the generic `search_source_metadata.v1` envelope and normalize
      labeled GitHub issues into metadata-only documents with type, repo,
      number, title, labels, state, created/updated/closed timestamps, URL,
      summary, and extracted learnings; the fetcher supports repo, label
      allowlist, date window, and state filters through `gh` using
      `get_full_env()`; deduplication upserts by canonical repo/issue/update key
      and suppresses repeated phase-complete/reflection records; `search_code`
      and `/search` can filter history records separately from code and friction
      chunks without changing the legacy unfiltered result shape; tests use
      fixtures or mocked `gh` output and require no live credentials.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `mcp_server/indexing/source_metadata.py`,
  `mcp_server/indexing/github_issues.py`, `mcp_server/storage/sqlite_store.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/cli/tool_handlers.py`, `mcp_server/cli/stdio_runner.py`,
  `mcp_server/cli/history_commands.py`, `mcp_server/gateway.py`, `README.md`,
  `docs/api/API-REFERENCE.md`, `docs/SUPPORT_MATRIX.md`,
  `docs/status/historical-issue-context.md`
- evidence paths: `docs/status/historical-issue-context.md`, fixture-backed
  GitHub issue fetcher/normalizer/storage/search/tool/doc test output
- redaction posture: `metadata_only`
- downstream handling: `none`

## Lane Index & Dependencies

SL-0 — Generic history source metadata schema
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3, SL-4, SL-5
  Parallel-safe: no
SL-1 — GitHub issue fetcher and normalizer
  Depends on: SL-0
  Blocks: SL-2, SL-3, SL-4, SL-5
  Parallel-safe: no
SL-2 — Historical issue indexing, CLI ingestion, and dedupe storage
  Depends on: SL-0, SL-1
  Blocks: SL-3, SL-4, SL-5
  Parallel-safe: no
SL-3 — History search filters and tool/admin surfaces
  Depends on: SL-0, SL-1, SL-2
  Blocks: SL-4, SL-5
  Parallel-safe: no
SL-4 — HISTORY contract verification
  Depends on: SL-0, SL-1, SL-2, SL-3
  Blocks: SL-5
  Parallel-safe: no
SL-5 — HISTORY docs and evidence reducer
  Depends on: SL-0, SL-1, SL-2, SL-3, SL-4
  Blocks: (none)
  Parallel-safe: no

Lane DAG:

```text
SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SL-5 -> HISTORY acceptance
```

## Lanes

### SL-0 — Generic History Source Metadata Schema

- **Scope**: Extend the generic source metadata envelope so history records can
  coexist with friction records without changing the top-level schema version or
  legacy search output.
- **Owned files**: `mcp_server/indexing/source_metadata.py`,
  `tests/test_source_metadata_contract.py`, `tests/test_history_source_metadata.py`
- **Interfaces provided**: `SourceType` includes `history`, `HistoryIssueRecord`, `HistoryIssueType`, `normalize_history_issue_record`, `build_source_metadata(history records)`, `extract_matching_source_metadata(source_type="history")`, `SL-0 history metadata schema contract`
- **Interfaces consumed**: `search_source_metadata.v1` (pre-existing), existing friction record normalization (pre-existing), `code_chunks.metadata["source_metadata"]` JSON persistence (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_source_metadata_contract.py` to prove existing
    friction metadata remains byte-stable and legacy callers that omit
    `source_type` still match all source records.
  - test: Add `tests/test_history_source_metadata.py` for required history
    fields, label sorting, timestamp normalization, repo/number URL identity,
    empty `learnings` behavior, no raw body persistence by default, mixed
    friction/history envelopes, and unknown source-type validation errors.
  - impl: Extend `mcp_server/indexing/source_metadata.py` with typed history
    record normalization while preserving `SEARCH_SOURCE_METADATA_VERSION`.
  - impl: Keep history-specific fields inside individual records; do not add
    history-only keys to the envelope root.
  - impl: Make matching/filter helpers generic across `friction` and `history`
    while preserving friction category validation semantics.
  - verify: `uv run pytest tests/test_source_metadata_contract.py tests/test_history_source_metadata.py -q --no-cov`

### SL-1 — GitHub Issue Fetcher And Normalizer

- **Scope**: Add a deterministic `gh`-backed issue fetcher and normalizer that
  supports roadmap filters and converts fixture or CLI JSON into history source
  records without live test credentials.
- **Owned files**: `mcp_server/indexing/github_issues.py`,
  `mcp_server/indexing/__init__.py`, `tests/test_github_issue_fetcher.py`,
  `tests/fixtures/github_issues/*.json`
- **Interfaces provided**: `GitHubIssueFetchOptions`, `GitHubIssueRecord`, `fetch_github_issues`, `normalize_github_issue`, `extract_issue_learnings`, `issue_history_dedupe_key`, `SL-1 issue adapter contract`
- **Interfaces consumed**: `get_full_env` (pre-existing), `get_command_availability` (pre-existing), `subprocess.run` patch points (pre-existing), `search_source_metadata.v1` history record shape, GitHub CLI JSON fields `number`, `title`, `labels`, `state`, `createdAt`, `updatedAt`, `closedAt`, `url`, and optional `body`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add fixture JSON for phase-complete, retrospective, reflection, and
    unrelated labeled issues under `tests/fixtures/github_issues/`.
  - test: Add `tests/test_github_issue_fetcher.py` cases that assert `gh issue
    list` arguments for repo, label allowlist, date window, and state filters;
    helper-provided env is passed; non-zero `gh` exits produce metadata-only
    errors; and no test requires authenticated GitHub access.
  - test: Cover normalization for type inference, sorted/deduped labels,
    timestamp fields, URL preservation, title-derived metadata-only summaries,
    optional body-derived learning extraction, and no raw body field in the
    persisted normalized record.
  - impl: Add `mcp_server/indexing/github_issues.py` with small typed option and
    record structures, `gh` JSON invocation, deterministic normalization, and
    a dedupe key based on canonical repo, issue number, record type, updated
    timestamp, and normalized learning hash.
  - impl: Export only the stable adapter helpers from `mcp_server/indexing/__init__.py`.
  - verify: `uv run pytest tests/test_github_issue_fetcher.py -q --no-cov`

### SL-2 — Historical Issue Indexing, CLI Ingestion, And Dedupe Storage

- **Scope**: Persist normalized historical issue documents through SQLite chunk
  metadata and expose an explicit local ingestion command without coupling issue
  fetching to ordinary code reindexing.
- **Owned files**: `mcp_server/storage/sqlite_store.py`,
  `mcp_server/cli/history_commands.py`, `mcp_server/cli/__init__.py`,
  `tests/test_history_issue_storage.py`, `tests/test_history_issue_cli.py`
- **Interfaces provided**: `SQLiteStore.upsert_history_issue_documents`, `SQLiteStore.search_chunks_by_source_metadata(source_type="history")`, `SQLiteStore.search_chunks_by_source_metadata`, `mcp-index history ingest`, `history ingestion metadata-only summary`, `SL-2 history storage evidence`
- **Interfaces consumed**: `GitHubIssueFetchOptions`, `fetch_github_issues`, `normalize_github_issue`, `issue_history_dedupe_key`, `merge_source_metadata`, `store_file` (pre-existing), `store_chunk` (pre-existing), existing SQLite schema (pre-existing), `click.CliRunner` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_history_issue_storage.py` proving issue documents are
    upserted by stable history key, repeated phase-complete/reflection records
    do not crowd search results, normalized metadata survives JSON round trips,
    and source-type filtering excludes source-code and friction chunks.
  - test: Add `tests/test_history_issue_cli.py` proving `mcp-index history
    ingest --repo --label --since --until --state` wires filters into the
    fetcher, writes metadata-only ingestion summaries, and reports `gh`
    availability without printing tokens, env values, or raw body text.
  - impl: Generalize `SQLiteStore.search_chunks_by_source_metadata()` to accept
    history source filters while keeping existing friction-category behavior.
  - impl: Add `SQLiteStore.upsert_history_issue_documents()` or a similarly
    narrow helper that writes synthetic history document chunks with stable
    file paths such as `.mcp-index/history/<owner>/<repo>/issues/<number>.md`
    and source metadata only.
  - impl: Add `mcp_server/cli/history_commands.py` with a lazy-registered
    `history ingest` command in `mcp_server/cli/__init__.py`; default to
    metadata-only issue fields and require an explicit flag before body-derived
    learning extraction.
  - verify: `uv run pytest tests/test_history_issue_storage.py tests/test_history_issue_cli.py tests/test_sqlite_store.py -q --no-cov`

### SL-3 — History Search Filters And Tool/Admin Surfaces

- **Scope**: Expose `source_type="history"` through dispatcher, STDIO
  `search_code`, and FastAPI `/search` while preserving legacy unfiltered search
  responses and existing friction filter behavior.
- **Owned files**: `mcp_server/plugin_base.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/cli/tool_handlers.py`, `mcp_server/cli/stdio_runner.py`,
  `mcp_server/gateway.py`, `tests/test_history_search_filters.py`,
  `tests/test_history_tool_handlers.py`, `tests/test_stdio_tool_descriptions.py`,
  `tests/test_gateway.py`
- **Interfaces provided**: `SearchOpts.source_type="history"`, `SearchOpts.history_labels`, `SearchOpts.history_repos`, `EnhancedDispatcher.search history source filter`, `search_code history input schema`, `FastAPI /search history params`, `SL-3 history search/tool evidence`
- **Interfaces consumed**: `SQLiteStore.search_chunks_by_source_metadata`, `search_source_metadata.v1` (pre-existing), `legacy lexical result shape` (pre-existing), `source_type="friction"` behavior (pre-existing), semantic readiness refusal contract (pre-existing), FastAPI search result normalization (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_history_search_filters.py` proving
    `source_type="history"` returns only history issue chunks, history label/repo
    filters narrow results, unfiltered lexical calls keep the legacy result
    shape, and `include_source_metadata=true` enriches unfiltered hits without
    forcing history-only filtering.
  - test: Add `tests/test_history_tool_handlers.py` proving
    `handle_search_code()` accepts `source_type="history"`, rejects unknown
    source types with metadata-only validation errors, passes history filters to
    the dispatcher, and keeps semantic readiness refusals fail-closed before
    dispatch.
  - test: Extend `tests/test_stdio_tool_descriptions.py` and `tests/test_gateway.py`
    for the new source type, input schema, query params, and preservation of the
    existing friction category contract.
  - impl: Extend `SearchOpts`, STDIO schema, tool handler parsing, dispatcher
    routing, and FastAPI parameters for history source filters.
  - impl: Keep response metadata included only when requested or when a source
    filter is active; do not add history fields to legacy list-shaped lexical
    results.
  - verify: `uv run pytest tests/test_history_search_filters.py tests/test_history_tool_handlers.py tests/test_stdio_tool_descriptions.py tests/test_gateway.py -q --no-cov`

### SL-4 — HISTORY Contract Verification

- **Scope**: Run the complete fixture-backed HISTORY contract suite before the
  terminal docs/evidence reducer writes public status artifacts.
- **Owned files**: none
- **Interfaces provided**: `SL-4 verification evidence`, `HISTORY acceptance pre-verdict`
- **Interfaces consumed**: `SL-0 history metadata schema contract`, `SL-1 issue adapter contract`, `SL-2 history storage evidence`, `SL-3 history search/tool evidence`, `post-LOCALCI make agent-* validation contract` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Run all HISTORY-targeted unit and contract tests with mocked or
    fixture-backed GitHub data.
  - impl: No implementation writes; this lane is read-only verification and
    metadata collection for SL-5.
  - verify: `uv sync --locked --extra dev`
  - verify: `uv run pytest tests/test_history_source_metadata.py tests/test_github_issue_fetcher.py tests/test_history_issue_storage.py tests/test_history_issue_cli.py tests/test_history_search_filters.py tests/test_history_tool_handlers.py -q --no-cov`
  - verify: `make agent-full`

### SL-5 — HISTORY Docs And Evidence Reducer

- **Scope**: Reduce schema, fetcher, dedupe, search-filter, redaction, and
  verification evidence into public docs and metadata-only status evidence for
  IF-0-HISTORY-1.
- **Owned files**: `README.md`, `docs/api/API-REFERENCE.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/status/historical-issue-context.md`,
  `tests/docs/test_history_api_contract.py`,
  `tests/docs/test_history_evidence_contract.py`
- **Interfaces provided**: `IF-0-HISTORY-1 evidence`, `HISTORY acceptance verdict`,
  `public history source filter documentation`, `metadata-only issue history posture`,
  `docs/status/historical-issue-context.md`
- **Interfaces consumed**: `SL-0 history metadata schema contract`, `SL-1 issue adapter contract`, `SL-2 history storage evidence`, `SL-3 history search/tool evidence`, `SL-4 verification evidence`, `HISTORY acceptance pre-verdict`, roadmap non-goals (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_history_api_contract.py` to require public docs
    for optional issue-history ingestion, `source_type="history"`, history
    labels/repo filters, `include_source_metadata`, fixture-backed/no-live-test
    posture, and legacy result-shape compatibility.
  - test: Add `tests/docs/test_history_evidence_contract.py` to require audit
    date, phase plan reference, schema version, normalized issue fields,
    fetcher filters, dedupe rule, redaction posture, verification commands,
    non-goals, and downstream PYCLIENT reuse notes.
  - impl: Update `README.md`, `docs/api/API-REFERENCE.md`, and
    `docs/SUPPORT_MATRIX.md` only for optional metadata-only history ingestion
    and source filtering.
  - impl: Write `docs/status/historical-issue-context.md` with metadata-only
    evidence from targeted tests and state that no live credentials, private
    issue bodies by default, GitHub writes, package identity changes, hosted CI
    changes, or second search API were introduced.
  - verify: `uv run pytest tests/docs/test_history_api_contract.py tests/docs/test_history_evidence_contract.py -q --no-cov`
  - verify: `phase-loop validate-roadmap specs/phase-plans-v9.md`

## Execution Policy

- work-unit defaults: work-unit=`lane_execute`, effort=`medium`, unsupported=`inherit_default`, inherit-default=`true`
- SL-4: executor=`codex`, effort=`medium`, work-unit=`phase_verify`, unsupported=`inherit_default`, inherit-default=`true`
- SL-5: executor=`codex`, effort=`medium`, work-unit=`phase_reducer`, unsupported=`inherit_default`, inherit-default=`true`

## Execution Notes

- Use `uv sync --locked --extra dev` before targeted test execution;
  `pyproject.toml` and `uv.lock` remain dependency truth.
- Use `get_full_env()` for every `gh` subprocess call. Tests should patch the
  subprocess boundary and fixture JSON, not require `gh auth login` or network
  access.
- Keep HISTORY ingestion explicit through `mcp-index history ingest`; ordinary
  code reindexing must not make live GitHub calls.
- Preserve `source_type="friction"` behavior and the legacy unfiltered lexical
  result shape. Unknown source types are metadata-only validation errors.
- Default to metadata-only issue fields. Optional body-derived learning
  extraction must not persist raw body text and must be covered with fixture
  data, not live private issue reads.
- Do not write to GitHub, create issues, change package identity, alter hosted
  CI posture, change coverage thresholds, or introduce a separate historical
  search API in this phase.

## Acceptance Criteria

- [ ] `mcp_server/indexing/source_metadata.py` supports `source_type="history"`
      records in the existing `search_source_metadata.v1` envelope while
      preserving friction metadata behavior and legacy matching semantics.
- [ ] `mcp_server/indexing/github_issues.py` fetches and normalizes labeled
      GitHub issues by repo, label allowlist, date window, and state filters
      using `gh` with `get_full_env()` and fixture-backed tests.
- [ ] `tests/test_github_issue_fetcher.py` proves normalized issue documents include type, repo, number, title, labels, state, timestamps, URL, summary, and extracted learnings, and raw issue bodies are not persisted by default.
- [ ] `tests/test_history_issue_storage.py` proves deduplication/upsert logic prevents repeated phase-complete/reflection records from crowding indexed history results.
- [ ] `mcp-index history ingest` provides an explicit metadata-only ingestion
      surface whose tests mock fetcher output and require no live credentials.
- [ ] `search_code` and `/search` support `source_type="history"`, optional
      history label/repo filtering, and explicit source metadata inclusion while
      ordinary unfiltered lexical results remain shape-compatible.
- [ ] `README.md`, `docs/api/API-REFERENCE.md`, `docs/SUPPORT_MATRIX.md`, and
      `docs/status/historical-issue-context.md` document optional metadata-only
      history ingestion, filters, dedupe, verification evidence, and non-goals.
- [ ] `make agent-full` and `phase-loop validate-roadmap specs/phase-plans-v9.md`
      pass without live GitHub credentials, GitHub writes, private issue body
      indexing by default, package identity changes, or hosted CI changes.

## Verification

`automation.suite_command`: `make agent-full`

Lane-specific verification commands are listed under each lane. Whole-phase
verification:

```bash
uv sync --locked --extra dev
uv run pytest tests/test_source_metadata_contract.py tests/test_history_source_metadata.py tests/test_github_issue_fetcher.py tests/test_history_issue_storage.py tests/test_history_issue_cli.py tests/test_history_search_filters.py tests/test_history_tool_handlers.py tests/docs/test_history_api_contract.py tests/docs/test_history_evidence_contract.py -q --no-cov
uv run pytest tests/test_sqlite_store.py tests/test_stdio_tool_descriptions.py tests/test_gateway.py -q --no-cov
make agent-full
phase-loop validate-roadmap specs/phase-plans-v9.md
git status --short -- \
  mcp_server/indexing/source_metadata.py \
  mcp_server/indexing/github_issues.py \
  mcp_server/indexing/__init__.py \
  mcp_server/storage/sqlite_store.py \
  mcp_server/cli/history_commands.py \
  mcp_server/cli/__init__.py \
  mcp_server/plugin_base.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/cli/tool_handlers.py \
  mcp_server/cli/stdio_runner.py \
  mcp_server/gateway.py \
  README.md \
  docs/api/API-REFERENCE.md \
  docs/SUPPORT_MATRIX.md \
  docs/status/historical-issue-context.md \
  tests/test_source_metadata_contract.py \
  tests/test_history_source_metadata.py \
  tests/test_github_issue_fetcher.py \
  tests/fixtures/github_issues/ \
  tests/test_history_issue_storage.py \
  tests/test_history_issue_cli.py \
  tests/test_history_search_filters.py \
  tests/test_history_tool_handlers.py \
  tests/test_stdio_tool_descriptions.py \
  tests/test_gateway.py \
  tests/docs/test_history_api_contract.py \
  tests/docs/test_history_evidence_contract.py \
  plans/phase-plan-v9-HISTORY.md
```

Next phase: HISTORY - execution ready
Next command: codex-execute-phase plans/phase-plan-v9-HISTORY.md

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v9-HISTORY.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v9-HISTORY.md
  artifact_state: staged
```
