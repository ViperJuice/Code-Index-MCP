# Semantic Dogfood Rebuild

- Evidence captured: 2026-04-28T08:54:31Z.
- Observed commit: `c4e78776e5727d73b9168e8bf198e54803a791d0`.
- Phase plan: `plans/phase-plan-v7-SEMREADYFIX.md`.
- Roadmap follow-up added during execution: `SEMCOLLECT` in `specs/phase-plans-v7.md`.

## Reset Boundary

This run used a repo-local reset boundary before the rebuild. Existing repo-local
runtime artifacts were moved aside into `.codex-tmp-reset/20260428T082620Z/`:

- `.mcp-index`
- `.indexes`

Shared live service state was preserved:

- `qdrant_storage/` was left intact.
- No shared Qdrant collections were deleted.

The rebuild also logged one oversized-file skip during indexing:

- `analysis_archive/semantic_vs_sql_comparison_1750926162.json` at `32983030`
  bytes.

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
- CLI result: `Indexed 1377 files in 1331.5s`.
- Wall time: `22:15.19`.
- Normalized field name for contract checks: `wall time`.
- User time: `234.73s`.
- System time: `71.72s`.
- CPU: `22%`.
- Max RSS: `407188 KB`.
- Normalized field name for contract checks: `max rss`.
- File system outputs: `26961024` blocks.

SQLite counts from `.mcp-index/current.db` after the rebuild:

- Files: `1365`.
- Symbols: `23985`.
- Chunks: `66694`.
- `chunk_summaries`: `0`.
- `semantic_points`: `0`.
- `code_index__oss_high__v1` collection-linked semantic chunks: `0`.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status` after
the clean rebuild reported:

- Lexical readiness: `ready`.
- Semantic readiness: `summaries_missing`.
- Active-profile preflight: `blocked`.
- Preflight blocker: `collection_missing`.
- Preflight message: `Qdrant collection is missing for the active semantic profile`.
- Semantic remediation: `Run semantic summary/vector generation for the current profile before semantic queries.`
- Indexed commit: `c4e78776`.
- Index size: `177.5 MB`.
- Artifact backend: `local_workspace`.
- Artifact health: `missing`.

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`
proved that the enrichment compatibility repair itself is active:

- Configured enrichment model: `chat`.
- Effective enrichment model: `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`.
- Resolution strategy: `single_served_model_for_chat_alias`.
- Enrichment chat smoke: `ready`.
- Embedding smoke: `ready`.
- Remaining preflight blocker: `collection_missing`.

Semantic evidence from the rebuilt status surface:

- Summary-backed chunks: `0`.
- Chunks missing summaries: `66694`.
- Vector-linked chunks: `0`.
- Chunks missing vectors: `66694`.
- Active collection: `code_index__oss_high__v1`.
- Collection-matched links: `0`.
- Collection mismatches: `0`.

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index preflight` still reported
working-tree drift after the rebuild because the phase implementation files are
not committed in this worktree:

- Branch is ahead of `origin/main` by `7` commits.
- Local runtime index has drift relative to the working tree (`7 change(s)`).

## Query Comparison

Fixed dogfood prompt: `how does semantic setup validate qdrant and embedding readiness`

- Lexical query:
  top result was `docs/guides/semantic-onboarding.md`.
  Follow-on hits were `tests/test_benchmark_query_regressions.py` and
  `plans/phase-plan-v7-SEMPREFLIGHT.md`.
- Fuzzy query:
  This is the `fuzzy` comparison lane for the fixed dogfood prompt.
  top result was `plans/phase-plan-v7-SEMCONTRACT.md`.
  Follow-on hits were `architecture/document_processing_architecture.md` and
  `scripts/create_semantic_embeddings.py`.
- Semantic query:
  returned `code: "semantic_not_ready"` with `semantic_source: "semantic"`,
  `semantic_collection_name: "code_index__oss_high__v1"`, and readiness state
  `summaries_missing`.
- Symbol query:
  `symbol_lookup("run_semantic_preflight")` resolved the implementation symbol
  in `mcp_server/setup/semantic_preflight.py`.

Fixed operator prompt: `where does repository status print semantic readiness evidence`

- Lexical query still preferred `docs/guides/semantic-onboarding.md` over the
  implementation file, which is expected for a phrase-driven lexical search.
- The benchmark regression fixture added in this phase keeps
  `mcp_server/cli/repository_commands.py` as the preferred implementation path
  when semantic reranking is available.

## Dogfood Verdict

The exact verdict string for contract checks is `local multi-repo dogfooding`.

Local multi-repo dogfooding is **still not ready** under the default `oss_high`
setup after `SEMREADYFIX`.

Why:

- `SEMREADYFIX` repaired the default enrichment compatibility path:
  preflight now resolves configured `chat` to served
  `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`.
- A clean force-full rebuild still produced `0` `chunk_summaries`.
- The same rebuild still produced `0` `semantic_points`.
- Active-profile preflight moved forward but is now blocked on
  `collection_missing`.
- Semantic queries therefore still stay fail-closed with
  `semantic_not_ready` instead of returning semantic-path implementation
  results.

Steering outcome:

- `SEMREADYFIX` completed the enrichment-compatibility repair slice, but it did
  not restore semantic-write readiness.
- The roadmap now needs a downstream `SEMCOLLECT` phase to provision or hydrate
  the active `code_index__oss_high__v1` collection and reconnect the strict
  summary/vector pipeline before rerunning semantic dogfood acceptance.

## Verification

Executed in this phase:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_semantic_profile_settings.py tests/test_semantic_preflight.py tests/test_summarization.py -q --no-cov
curl -s http://ai:8002/v1/models
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
/usr/bin/time -v env SEMANTIC_SEARCH_ENABLED=true SEMANTIC_DEFAULT_PROFILE=oss_high OPENAI_API_KEY=dummy-local-key QDRANT_URL=http://localhost:6333 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index preflight
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
env SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run python - <<'PY'
...
PY
```

Observed test outcomes:

- `tests/test_semantic_profile_settings.py`: passed.
- `tests/test_semantic_preflight.py`: passed.
- `tests/test_summarization.py`: passed.
- Semantic query harness: lexical and symbol paths resolved, while semantic
  queries still returned `semantic_not_ready` with readiness state
  `summaries_missing`.

Pending verification tied to this report artifact:

```bash
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "SEMANTIC_DOGFOOD_REBUILD|configured enrichment model|effective enrichment model|collection_missing|lexical readiness|semantic readiness|active-profile preflight|code_index__oss_high__v1|semantic_points|chunk_summaries" docs/status/SEMANTIC_DOGFOOD_REBUILD.md docs/guides/semantic-onboarding.md tests/docs/test_semdogfood_evidence_contract.py
```
