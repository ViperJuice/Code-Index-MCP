# Historical Issue Context

Audit date: 2026-07-06
Phase plan: `plans/phase-plan-v9-HISTORY.md`
Schema version: `search_source_metadata.v1`
Normalized issue fields: type, repo, number, title, labels, state, created_at, updated_at, closed_at, url, summary, learnings
Fetcher filters: repo, label allowlist, updated-date window (`since` / `until`), state, optional body-derived learning extraction
Dedupe rule: stable `history:<type>` chunk upserts per issue file with metadata key `repo#number:type:updated_at:learning_hash`, preventing repeated phase-complete and reflection records from crowding search
Redaction posture: metadata_only; raw issue bodies are not persisted by default and GitHub writes are out of scope
Verification commands:
- `uv run pytest tests/test_source_metadata_contract.py tests/test_history_source_metadata.py tests/test_github_issue_fetcher.py tests/test_history_issue_storage.py tests/test_history_issue_cli.py tests/test_history_search_filters.py tests/test_history_tool_handlers.py -q --no-cov`
- `uv run pytest tests/docs/test_history_api_contract.py tests/docs/test_history_evidence_contract.py -q --no-cov`
- `uv run pytest tests/test_sqlite_store.py tests/test_stdio_tool_descriptions.py tests/test_gateway.py -q --no-cov`
- `make agent-full`
- `phase-loop validate-roadmap specs/phase-plans-v9.md`
Non-goals:
- no live GitHub access in unit tests
- no private issue body indexing by default
- no GitHub writes
- no package identity changes
- no hosted CI posture changes
- no separate historical search API outside `search_code` and `GET /search`
PYCLIENT reuse note: HISTORY reuses the generic `search_source_metadata.v1` envelope and the existing SQLite-backed `search_code` / `/search` filter surface so downstream PYCLIENT work can consume the same source-metadata contract instead of introducing a parallel history API.
