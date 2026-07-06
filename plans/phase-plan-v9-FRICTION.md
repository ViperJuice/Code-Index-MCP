---
phase_loop_plan_version: 1
phase: FRICTION
roadmap: specs/phase-plans-v9.md
roadmap_sha256: 57848534176ac820595f4193459b86b5fdef9f5bfe5bff60a5739d8d9e192d2b
---
# FRICTION: Friction Pattern Metadata Search

## Context

FRICTION is Phase 6 in `specs/phase-plans-v9.md`. The canonical
`.phase-loop/state.json` reports PUBNAME, REPOCLEAN, LOCALCI, COVERAGE, and
PROCENV complete, `FRICTION` current/unplanned, a clean worktree at runner
reconciliation time, and roadmap SHA-256
`57848534176ac820595f4193459b86b5fdef9f5bfe5bff60a5739d8d9e192d2b`.
Legacy `.codex/phase-loop/` files are compatibility artifacts only and are not
used to supersede the canonical `.phase-loop/` state.

Planning observations:

- `mcp_server/plugin_base.py::SearchOpts` currently exposes only `semantic` and
  `limit`; friction filters must be additive and optional.
- `mcp_server/cli/tool_handlers.py::handle_search_code()` is the STDIO entry
  point for indexed query arguments and must preserve the legacy lexical result
  shape when no friction/source filter is requested.
- `mcp_server/dispatcher/dispatcher_enhanced.py::EnhancedDispatcher.search()`
  owns lexical, semantic, fuzzy, and plugin fallback routing; it is the single
  writer for dispatcher-level result enrichment and source filter semantics.
- `mcp_server/storage/sqlite_store.py` already persists `code_chunks.metadata`
  as JSON, so this phase can store an additive metadata envelope beside chunks
  without a mandatory table migration.
- Tree-sitter chunks reach storage through `SQLiteStore.store_chunk()` and
  `store_chunks_batch()`, while dispatcher-backed document/plugin shards also
  insert `code_chunks` directly in `_persist_index_shard()`.
- Markdown and plaintext indexing use the document processing contracts, so
  friction extraction should operate on chunk/file text and line spans rather
  than language-specific AST nodes.

Planning boundary:

- FRICTION may add a source metadata schema, a deterministic friction extractor,
  chunk metadata enrichment, friction/source search filters, STDIO/FastAPI admin
  parameter surfaces, focused tests, and metadata-only docs/evidence.
- FRICTION must not change normal `search_code` response shape unless a caller
  requests friction/source filtering or source metadata, must not create GitHub
  issues, must not depend on ai-dev-kit reflection workflows, and must not add a
  cross-repo prioritization UI.
- Semantic behavior must remain deterministic: no provider call, generated
  summary, or nondeterministic enrichment may be introduced solely for friction
  metadata.

## Interface Freeze Gates

- [ ] IF-0-FRICTION-1 — Friction metadata contract: configured HACK, TODO,
      FIXME, workaround, wish, and extraction-hint markers are extracted into a
      generic `search_source_metadata.v1` envelope stored under
      `code_chunks.metadata["source_metadata"]`; each friction marker records
      `source_type="friction"`, category, line, description, pattern, and
      optional reference; ordinary code search results stay shape-compatible
      unless `source_type="friction"`, `friction_categories`, or
      `include_source_metadata=true` is requested; filtered searches return only
      matching chunks/results and include deterministic source metadata; semantic
      enrichment, when enabled by existing indexing paths, uses only stable
      line/category/description ordering and never calls a provider because of
      friction extraction.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `mcp_server/indexing/source_metadata.py`,
  `mcp_server/indexing/friction.py`, `mcp_server/storage/sqlite_store.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/cli/tool_handlers.py`, `mcp_server/cli/stdio_runner.py`,
  `mcp_server/gateway.py`, `README.md`, `docs/api/API-REFERENCE.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/status/friction-metadata-search.md`
- evidence paths: `docs/status/friction-metadata-search.md`, targeted friction
  extractor/storage/search/tool/doc test output
- redaction posture: `metadata_only`
- downstream handling: `none`

## Lane Index & Dependencies

SL-0 — Source metadata schema and friction extractor contract
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3, SL-4, SL-5
  Parallel-safe: no
SL-1 — Chunk storage metadata enrichment
  Depends on: SL-0
  Blocks: SL-2, SL-3, SL-4, SL-5
  Parallel-safe: no
SL-2 — Search filters and tool/admin surfaces
  Depends on: SL-0, SL-1
  Blocks: SL-3, SL-4, SL-5
  Parallel-safe: no
SL-3 — Language and document friction coverage
  Depends on: SL-0, SL-1, SL-2
  Blocks: SL-4, SL-5
  Parallel-safe: no
SL-4 — FRICTION contract verification
  Depends on: SL-0, SL-1, SL-2, SL-3
  Blocks: SL-5
  Parallel-safe: no
SL-5 — FRICTION schema docs and evidence reducer
  Depends on: SL-0, SL-1, SL-2, SL-3, SL-4
  Blocks: (none)
  Parallel-safe: no

Lane DAG:

```text
SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SL-5 -> FRICTION acceptance
```

## Lanes

### SL-0 — Source Metadata Schema And Friction Extractor Contract

- **Scope**: Define the generic search-source metadata envelope and the
  deterministic friction marker extractor used by storage and search lanes.
- **Owned files**: `mcp_server/indexing/source_metadata.py`,
  `mcp_server/indexing/friction.py`, `mcp_server/indexing/__init__.py`,
  `tests/test_source_metadata_contract.py`, `tests/test_friction_extractor.py`
- **Interfaces provided**: `search_source_metadata.v1`, `SourceType`, `FrictionCategory`, `FrictionMarker`, `FrictionPatternConfig`, `extract_friction_markers`, `merge_source_metadata`, `SL-0 schema contract`, `SL-0 extractor contract`, `todo|fixme|hack|workaround|wish|extraction_hint`
- **Interfaces consumed**: `code_chunks.metadata`, `Python/JS/TS/shell/Markdown/plain-text comment conventions`, `json.dumps/json.loads metadata persistence` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_source_metadata_contract.py` for the
    `search_source_metadata.v1` envelope, category vocabulary, stable
    serialization order, no source records when no markers exist, and
    preservation of unrelated metadata keys.
  - test: Add `tests/test_friction_extractor.py` cases for Python `#`, JS/TS
    `//` and block comments, shell `#`, Markdown HTML comments, Markdown/plain
    text TODO-style lines, category normalization, line offsets, description
    trimming, and optional references such as issue numbers or URLs.
  - impl: Add `mcp_server/indexing/source_metadata.py` with a generic envelope
    that can later hold non-friction source types without renaming friction
    fields into the top-level schema.
  - impl: Add `mcp_server/indexing/friction.py` with configured marker patterns
    for HACK, TODO, FIXME, workaround, wish, and extraction hints; keep pattern
    matching deterministic and case-insensitive while preserving original
    description text.
  - impl: Export only the stable helper surface from `mcp_server/indexing/__init__.py`.
  - verify: `uv run pytest tests/test_source_metadata_contract.py tests/test_friction_extractor.py -q --no-cov`

### SL-1 — Chunk Storage Metadata Enrichment

- **Scope**: Enrich persisted chunk metadata with friction source records at
  shared SQLite insertion boundaries without changing the database schema or
  ordinary chunk rows that have no markers.
- **Owned files**: `mcp_server/storage/sqlite_store.py`,
  `tests/test_friction_storage.py`
- **Interfaces provided**: `SQLiteStore.store_chunk friction enrichment`, `SQLiteStore.store_chunks_batch friction enrichment`, `SQLiteStore.search_chunks_by_source_metadata`, `SL-1 storage evidence`, `SL-1 storage enrichment`, `chunk-level preservation of existing metadata keys`
- **Interfaces consumed**: `extract_friction_markers`, `merge_source_metadata`, `code_chunks.metadata JSON persistence`, `code_chunks.line_start`, `code_chunks.line_end`, `code_chunks.language`, `FTS5 tables` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_friction_storage.py` coverage for `store_chunk()` and
    `store_chunks_batch()` preserving existing metadata, attaching line-adjusted
    friction markers, omitting `source_metadata` when no marker exists, and
    returning category-filtered chunks without changing FTS query results.
  - test: Prove no new migration is required by asserting a fresh
    `SQLiteStore` initialized from current schema can persist and query the
    envelope using the existing `metadata` column.
  - impl: Merge friction source metadata immediately before JSON serialization
    in `store_chunk()` and `store_chunks_batch()`.
  - impl: Add a metadata query helper that filters `code_chunks.metadata` for
    `source_type="friction"` and optional categories, returning file path, line
    span, snippet/content, categories, and source metadata in a result-shaped
    dictionary for dispatcher consumption.
  - impl: Keep invalid or absent marker data internal to the helper; do not log
    source file contents or raw secrets in metadata diagnostics.
  - verify: `uv run pytest tests/test_friction_storage.py tests/test_sqlite_store.py -q --no-cov`

### SL-2 — Search Filters And Tool/Admin Surfaces

- **Scope**: Expose friction/source filtering through the dispatcher, STDIO
  `search_code`, and FastAPI admin search while preserving legacy output for
  unfiltered lexical searches.
- **Owned files**: `mcp_server/plugin_base.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/cli/tool_handlers.py`, `mcp_server/cli/stdio_runner.py`,
  `mcp_server/gateway.py`, `tests/test_friction_search_filters.py`,
  `tests/test_friction_tool_handlers.py`, `tests/test_stdio_tool_descriptions.py`,
  `tests/test_gateway.py`
- **Interfaces provided**: `SearchOpts.source_type`, `SearchOpts.friction_categories`, `SearchOpts.include_source_metadata`, `EnhancedDispatcher.search source filters`, `search_code source filter schema`, `FastAPI /search source filter params`, `SL-2 search/tool evidence`
- **Interfaces consumed**: `SQLiteStore.search_chunks_by_source_metadata`, `search_source_metadata.v1`, `semantic readiness refusal contract`, `legacy lexical result shape`, `FastAPI SearchResult response model normalization` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_friction_search_filters.py` to prove unfiltered
    lexical search emits the same shape as before, `source_type="friction"`
    returns only chunks with friction metadata, category filtering narrows
    results, and `include_source_metadata=true` is required for metadata on
    unfiltered results.
  - test: Add `tests/test_friction_tool_handlers.py` to prove
    `handle_search_code()` parses source filters, passes them to the dispatcher,
    includes source metadata only when requested or friction-filtered, and keeps
    semantic readiness refusals fail-closed before dispatch.
  - test: Extend `tests/test_stdio_tool_descriptions.py` and
    `tests/test_gateway.py` for the new input schema, admin query params, and
    legacy no-filter calls.
  - impl: Extend `SearchOpts` with optional source metadata fields without
    making existing plugin implementations responsible for friction filtering.
  - impl: Add dispatcher routing that uses the storage metadata helper for
    friction/source filtered queries, applies existing limit handling, and emits
    result-shaped dictionaries with source metadata only under the frozen rules.
  - impl: Add STDIO and FastAPI argument parsing for source filters; normalize
    categories to the SL-0 enum and return metadata-only validation errors for
    unknown categories.
  - verify: `uv run pytest tests/test_friction_search_filters.py tests/test_friction_tool_handlers.py tests/test_stdio_tool_descriptions.py tests/test_gateway.py -q --no-cov`

### SL-3 — Language And Document Friction Coverage

- **Scope**: Prove the extractor and search path cover the roadmap-required
  Python, JS/TS, shell, Markdown, and plain-text marker syntaxes without adding
  per-language product rewrites.
- **Owned files**: `tests/test_friction_language_coverage.py`,
  `tests/test_friction_document_coverage.py`
- **Interfaces provided**: `SL-3 language/document coverage evidence`, `roadmap syntax coverage evidence`, `deterministic semantic-enrichment posture evidence`
- **Interfaces consumed**: `extract_friction_markers`, `SQLiteStore.store_chunk friction enrichment`, `EnhancedDispatcher.search source filters`, `MarkdownPlugin.indexFile`, `PlainTextPlugin.indexFile`, `Python/JS plugin indexed content behavior` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_friction_language_coverage.py` fixtures for `.py`,
    `.js`, `.ts`, `.sh`, and mixed-comment content that assert category, line,
    description, and reference extraction independent of host-specific parser
    availability.
  - test: Add `tests/test_friction_document_coverage.py` fixtures for Markdown
    and plaintext chunks, including Markdown HTML comments, heading-adjacent
    TODO lines, and plain prose workaround/wish markers.
  - test: Prove semantic enrichment is deterministic by comparing two identical
    extraction/storage runs and asserting sorted source metadata is byte-stable.
  - impl: No production writes; this lane adds cross-language and document
    coverage for the SL-0 through SL-2 contracts.
  - verify: `uv run pytest tests/test_friction_language_coverage.py tests/test_friction_document_coverage.py -q --no-cov`

### SL-4 — FRICTION Contract Verification

- **Scope**: Run the complete FRICTION contract suite before the final evidence
  reducer writes docs and closeout notes.
- **Owned files**: none
- **Interfaces provided**: `SL-4 verification evidence`, `FRICTION acceptance pre-verdict`
- **Interfaces consumed**: `SL-0 schema contract`, `SL-1 storage evidence`, `SL-2 search/tool evidence`, `SL-3 language/document coverage evidence`, `post-LOCALCI make agent-* validation contract` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Run all FRICTION-targeted behavior tests before docs evidence is
    reduced.
  - impl: No implementation writes; this lane is read-only verification and
    metadata collection for SL-5.
  - verify: `uv sync --locked --extra dev`
  - verify: `uv run pytest tests/test_source_metadata_contract.py tests/test_friction_extractor.py tests/test_friction_storage.py tests/test_friction_search_filters.py tests/test_friction_tool_handlers.py tests/test_friction_language_coverage.py tests/test_friction_document_coverage.py -q --no-cov`
  - verify: `make agent-full`

### SL-5 — FRICTION Schema Docs And Evidence Reducer

- **Scope**: Reduce schema, extraction, storage, search, semantic posture, and
  verification evidence into canonical docs and metadata-only status evidence
  for IF-0-FRICTION-1.
- **Owned files**: `README.md`, `docs/api/API-REFERENCE.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/status/friction-metadata-search.md`,
  `tests/docs/test_friction_api_contract.py`,
  `tests/docs/test_friction_evidence_contract.py`
- **Interfaces provided**: `IF-0-FRICTION-1 evidence`, `FRICTION acceptance verdict`, `public friction source filter documentation`, `metadata-only semantic determinism note`, `docs/status/friction-metadata-search.md`
- **Interfaces consumed**: `SL-0 schema contract`, `SL-1 storage evidence`, `SL-2 search/tool evidence`, `SL-3 language/document coverage evidence`, `SL-4 verification evidence`, `FRICTION acceptance pre-verdict`, `roadmap non-goals` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_friction_api_contract.py` to require public docs
    for `source_type="friction"`, `friction_categories`,
    `include_source_metadata`, legacy result-shape compatibility, and
    metadata-only category validation.
  - test: Add `tests/docs/test_friction_evidence_contract.py` to require audit
    date, phase plan reference, schema version, category vocabulary, storage
    surface, search filter surface, semantic determinism statement, verification
    commands, non-goals, and downstream `HISTORY` reuse note.
  - impl: Update `README.md`, `docs/api/API-REFERENCE.md`, and
    `docs/SUPPORT_MATRIX.md` only for the new friction source filter and schema
    contract; avoid unrelated release, package, or hosted CI wording.
  - impl: Write `docs/status/friction-metadata-search.md` with metadata-only
    evidence from the targeted test slices and state that no GitHub issue
    creation, ai-dev-kit workflow dependency, cross-repo UI, or provider-based
    semantic enrichment was added.
  - verify: `uv run pytest tests/docs/test_friction_api_contract.py tests/docs/test_friction_evidence_contract.py -q --no-cov`
  - verify: `phase-loop validate-roadmap specs/phase-plans-v9.md`

## Execution Policy

- work-unit defaults: work-unit=`lane_execute`, effort=`medium`, unsupported=`inherit_default`, inherit-default=`true`
- SL-4: executor=`codex`, effort=`medium`, work-unit=`phase_verify`, unsupported=`inherit_default`, inherit-default=`true`
- SL-5: executor=`codex`, effort=`medium`, work-unit=`phase_reducer`, unsupported=`inherit_default`, inherit-default=`true`

## Execution Notes

- Use `uv sync --locked --extra dev` before targeted test execution;
  `pyproject.toml` and `uv.lock` remain dependency truth.
- Keep source metadata additive. Do not add a mandatory migration unless
  execution proves the existing `code_chunks.metadata` JSON column cannot meet
  the filter contract.
- Preserve ordinary `search_code` and `/search` result shapes when no
  friction/source filter or metadata flag is requested.
- Treat unknown friction categories as metadata-only validation errors, not as
  silent empty searches.
- `HISTORY` depends on the generic source metadata envelope produced here; do
  not put historical issue fields inside friction-specific schema keys.
- Do not create GitHub issues, add reflection workflow dependencies, introduce a
  prioritization UI, change package identity, alter hosted CI posture, or add
  provider-based semantic enrichment in this phase.

## Acceptance Criteria

- [ ] `mcp_server/indexing/source_metadata.py` defines a generic
      `search_source_metadata.v1` envelope that can carry friction markers now
      and later historical issue metadata without renaming friction-specific
      fields into the top-level schema.
- [ ] `mcp_server/indexing/friction.py` detects HACK, TODO, FIXME, workaround,
      wish, and extraction-hint markers with category, line, description,
      pattern, and optional reference fields.
- [ ] Chunk persistence attaches friction source metadata to
      `code_chunks.metadata` through shared SQLite insertion paths while
      preserving unrelated metadata and requiring no schema migration.
- [ ] `search_code` and `/search` support `source_type="friction"`, optional
      category filtering, and explicit source metadata inclusion while legacy
      unfiltered lexical results remain shape-compatible.
- [ ] `uv run pytest tests/test_friction_language_coverage.py tests/test_friction_document_coverage.py -q --no-cov`
      proves Python, JS/TS, shell, Markdown, and plain-text marker syntax,
      deterministic line offsets, and deterministic semantic metadata posture.
- [ ] `README.md`, `docs/api/API-REFERENCE.md`, `docs/SUPPORT_MATRIX.md`, and
      `docs/status/friction-metadata-search.md` document the schema, filters,
      deterministic semantic posture, verification evidence, and non-goals.
- [ ] `make agent-full` and `phase-loop validate-roadmap specs/phase-plans-v9.md`
      pass without changing package identity, hosted CI posture, release
      behavior, or automatic issue creation.

## Verification

`automation.suite_command`: `make agent-full`

Lane-specific verification commands are listed under each lane. Whole-phase
verification:

```bash
uv sync --locked --extra dev
uv run pytest tests/test_source_metadata_contract.py tests/test_friction_extractor.py tests/test_friction_storage.py tests/test_friction_search_filters.py tests/test_friction_tool_handlers.py tests/test_friction_language_coverage.py tests/test_friction_document_coverage.py tests/docs/test_friction_api_contract.py tests/docs/test_friction_evidence_contract.py -q --no-cov
uv run pytest tests/test_sqlite_store.py tests/test_stdio_tool_descriptions.py tests/test_gateway.py -q --no-cov
make agent-full
phase-loop validate-roadmap specs/phase-plans-v9.md
git status --short -- \
  mcp_server/indexing/source_metadata.py \
  mcp_server/indexing/friction.py \
  mcp_server/indexing/__init__.py \
  mcp_server/storage/sqlite_store.py \
  mcp_server/plugin_base.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/cli/tool_handlers.py \
  mcp_server/cli/stdio_runner.py \
  mcp_server/gateway.py \
  README.md \
  docs/api/API-REFERENCE.md \
  docs/SUPPORT_MATRIX.md \
  docs/status/friction-metadata-search.md \
  tests/test_source_metadata_contract.py \
  tests/test_friction_extractor.py \
  tests/test_friction_storage.py \
  tests/test_friction_search_filters.py \
  tests/test_friction_tool_handlers.py \
  tests/test_friction_language_coverage.py \
  tests/test_friction_document_coverage.py \
  tests/docs/test_friction_api_contract.py \
  tests/docs/test_friction_evidence_contract.py \
  plans/phase-plan-v9-FRICTION.md
```

Next phase: FRICTION - execution ready
Next command: codex-execute-phase plans/phase-plan-v9-FRICTION.md

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v9-FRICTION.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v9-FRICTION.md
  artifact_state: staged
```
