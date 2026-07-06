# Friction Metadata Search

Audit date: 2026-07-06
Phase plan: `plans/phase-plan-v9-FRICTION.md`
Schema version: `search_source_metadata.v1`
Category vocabulary: `todo`, `fixme`, `hack`, `workaround`, `wish`, `extraction_hint`
Storage surface: `code_chunks.metadata["source_metadata"]` via shared SQLite chunk writes
Search filter surface: `search_code(source_type="friction", friction_categories, include_source_metadata)`, FastAPI `GET /search`
Semantic determinism: friction extraction sorts records by line/category/description/pattern/reference and does not introduce provider calls or nondeterministic enrichment
Verification commands:
- `uv run pytest tests/test_source_metadata_contract.py tests/test_friction_extractor.py tests/test_friction_storage.py tests/test_friction_search_filters.py tests/test_friction_tool_handlers.py tests/test_friction_language_coverage.py tests/test_friction_document_coverage.py -q --no-cov`
- `uv run pytest tests/docs/test_friction_api_contract.py tests/docs/test_friction_evidence_contract.py -q --no-cov`
- `uv run pytest tests/test_sqlite_store.py tests/test_stdio_tool_descriptions.py tests/test_gateway.py -q --no-cov`
- `make agent-full`
- `phase-loop validate-roadmap specs/phase-plans-v9.md`
Non-goals:
- no GitHub issue creation
- no ai-dev-kit reflection workflow dependency
- no cross-repo prioritization UI
- no provider-based semantic enrichment for friction extraction
HISTORY reuse note: the generic envelope is intentionally future-safe so later history metadata can reuse `source_metadata` without renaming friction-specific fields into the top level.
