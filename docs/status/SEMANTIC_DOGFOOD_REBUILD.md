# Semantic Dogfood Rebuild

- Evidence captured: 2026-04-28T09:35:36Z.
- Observed commit: `64fa813165c63703c62799a7f06ca44263b68263`.
- Phase plan: `plans/phase-plan-v7-SEMCOLLECT.md`.
- Roadmap follow-up added during execution: `SEMSUMFIX` in `specs/phase-plans-v7.md`.

## Reset Boundary

This SEMCOLLECT run reused the repo-local reset boundary that already existed
in this worktree:

- `.mcp-index/current.db` remained the active SQLite store.
- `qdrant_storage/` was preserved.
- No unrelated Qdrant collections were deleted.

The rebuild still skipped one oversized file during lexical indexing:

- `analysis_archive/semantic_vs_sql_comparison_1750926162.json` at `32983030`
  bytes.

## Collection Bootstrap

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index setup semantic --json --dry-run`
reported the exact pre-bootstrap blocker:

- Active-profile preflight: `blocked`.
- Preflight blocker: `collection_missing`.
- Collection bootstrap: `dry_run`.
- Active profile: `oss_high`.
- Active collection: `code_index__oss_high__v1`.

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index setup semantic --json`
then repaired the collection gate:

- Active-profile preflight: `ready`.
- Collection check: `ready`.
- Collection bootstrap: `created`.
- Collection bootstrap message: `Created the active semantic collection for the selected profile`.
- Collection distance metric: `dot`.
- Collection vector dimension: `4096`.

## Rebuild Command

```bash
/usr/bin/time -v env \
  SEMANTIC_SEARCH_ENABLED=true \
  SEMANTIC_DEFAULT_PROFILE=oss_high \
  OPENAI_API_KEY=dummy-local-key \
  QDRANT_URL=http://localhost:6333 \
  uv run mcp-index repository sync --force-full
```

## Rebuild Evidence

- Exit status: `0`.
- CLI result: `Indexed 1378 files in 1375.4s`.
- Wall time: `22:59.17`.
- Normalized field name for contract checks: `wall time`.
- User time: `246.52s`.
- System time: `85.46s`.
- CPU: `24%`.
- Max RSS: `408260 KB`.
- Normalized field name for contract checks: `max rss`.
- File system outputs: `31593376` blocks.

SQLite counts from `.mcp-index/current.db` after the rebuild:

- Files: `1366`.
- `code_chunks`: `66923`.
- `chunk_summaries`: `0`.
- `semantic_points`: `0`.
- `code_index__oss_high__v1` collection-linked semantic chunks: `0`.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status` after
the rebuild reported:

- The lexical readiness remained `ready`.
- The semantic readiness remained `summaries_missing`.

- Lexical readiness: `ready`.
- Semantic readiness: `summaries_missing`.
- Active-profile preflight: `ready`.
- Can write semantic vectors: `yes`.
- Active profile: `oss_high`.
- Active collection: `code_index__oss_high__v1`.
- Collection bootstrap state: `reused`.
- Semantic remediation: `Run semantic summary/vector generation for the current profile before semantic queries.`
- Indexed commit: `64fa8131`.
- Index size: `198.6 MB`.
- Artifact backend: `local_workspace`.
- Artifact health: `missing`.

Semantic evidence from the rebuilt status surface:

- Summary-backed chunks: `0`.
- Chunks missing summaries: `66923`.
- Vector-linked chunks: `0`.
- Chunks missing vectors: `66923`.
- Active collection: `code_index__oss_high__v1`.
- Collection-matched links: `0`.
- Collection mismatches: `0`.

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`
confirmed the repaired active-profile contract:

- The configured enrichment model remained `chat`.
- The effective enrichment model remained `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`.

- Configured enrichment model: `chat`.
- Effective enrichment model: `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`.
- Resolution strategy: `single_served_model_for_chat_alias`.
- Enrichment chat smoke: `ready`.
- Embedding smoke: `ready`.
- Collection check: `ready`.
- Remaining preflight blocker: none.

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Lexical query:
  top result was `docs/guides/semantic-onboarding.md`.
- Fuzzy query:
  the fuzzy path still preferred phrase-heavy planning and documentation hits
  over implementation files for this prompt.
- Semantic query:
  returned `code: "semantic_not_ready"` with `semantic_source: "semantic"`,
  `semantic_collection_name: "code_index__oss_high__v1"`, and readiness state
  `summaries_missing`.
- Symbol query:
  `symbol_lookup("run_semantic_preflight")` still resolves the implementation
  symbol in `mcp_server/setup/semantic_preflight.py`.

Fixed operator prompt: `where does repository status print semantic readiness evidence`

- Repository status still points operators at `mcp_server/cli/repository_commands.py`.
- The remaining runtime blocker probe points at
  `mcp_server/indexing/summarization.py`.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** after SEMCOLLECT.

Why:

- SEMCOLLECT repaired the active collection gate:
  `setup semantic` created `code_index__oss_high__v1`, and active-profile
  preflight is now `ready`.
- A clean force-full rebuild still produced `0` `chunk_summaries`.
- The same rebuild still produced `0` `semantic_points`.
- A direct authoritative summary probe against the rebuilt store failed inside
  the summary runtime with a `baml-py` generator/runtime mismatch:
  generated client `0.220.0` vs installed `baml-py 0.221.0`.
- Semantic queries therefore still stay fail-closed with
  `semantic_not_ready` instead of returning semantic-path implementation
  results.

Steering outcome:

- SEMCOLLECT completed the active collection bootstrap recovery slice.
- The remaining blocker has moved downstream into authoritative summary
  execution, so the roadmap now needs `SEMSUMFIX` to repair the summary
  runtime before semantic vectors and dogfood queries can pass.

## Verification

Executed in this phase:

```bash
uv run pytest tests/test_semantic_preflight.py tests/test_setup_cli.py tests/test_profile_aware_semantic_indexer.py tests/test_dispatcher.py tests/test_repository_commands.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run mcp-index setup semantic --json --dry-run
env OPENAI_API_KEY=dummy-local-key uv run mcp-index setup semantic --json
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
/usr/bin/time -v env SEMANTIC_SEARCH_ENABLED=true SEMANTIC_DEFAULT_PROFILE=oss_high OPENAI_API_KEY=dummy-local-key QDRANT_URL=http://localhost:6333 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
env OPENAI_API_KEY=dummy-local-key uv run python - <<'PY'
...
PY
env MCP_ALLOWED_ROOTS=/home/viperjuice/code OPENAI_API_KEY=dummy-local-key uv run python - <<'PY'
...
PY
```

Observed outcomes:

- Phase-owned unit slice: passed (`130 passed`).
- Setup dry run: reported `collection_missing` plus `collection bootstrap: dry_run`.
- Setup live run: reported `collection bootstrap: created` and fully ready preflight.
- Full rebuild: completed successfully but left `chunk_summaries=0` and
  `semantic_points=0`.
- Semantic query probe: returned `semantic_not_ready` with readiness state
  `summaries_missing`.
- Summary probe: failed in `mcp_server/indexing/summarization.py` with the
  `baml-py` version mismatch noted above.

Pending verification for the next phase:

```bash
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run python - <<'PY'
...
PY
```
