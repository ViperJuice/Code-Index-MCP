# Semantic Dogfood Rebuild

- Evidence captured: 2026-04-28T08:10:04Z.
- Observed commit: `5c8c087c14d13bdb0c95e51cea198b60f404448d`.
- Phase plan: `plans/phase-plan-v7-SEMDOGFOOD.md`.
- Roadmap follow-up added during execution: `SEMREADYFIX` in `specs/phase-plans-v7.md`.

## Reset Boundary

This run used a repo-local reset boundary before the rebuild. Existing local
runtime artifacts were moved aside into
`.codex-tmp-reset/20260428T073708Z/`:

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
- CLI result: `Indexed 1375 files in 1819.8s`.
- Wall time: `30:23.44`.
- Normalized field name for contract checks: `wall time`.
- User time: `244.90s`.
- System time: `74.19s`.
- CPU: `17%`.
- Max RSS: `406640 KB`.
- Normalized field name for contract checks: `max rss`.
- File system outputs: `26885312` blocks.

SQLite counts from `.mcp-index/current.db` after the rebuild:

- Files: `1363`.
- Symbols: `23909`.
- Chunks: `66463`.
- `chunk_summaries`: `0`.
- `semantic_points`: `0`.
- `code_index__oss_high__v1` collection-linked semantic chunks: `0`.

## Repository Status

`env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status` after
the clean rebuild reported:

- Lexical readiness: `ready`.
- Semantic readiness: `summaries_missing`.
- Active-profile preflight: `blocked`.
- Preflight blocker: `wrong_chat_model`.
- Preflight message: `Enrichment endpoint rejected the configured chat model`.
- Semantic remediation: `Run semantic summary/vector generation for the current profile before semantic queries.`
- Indexed commit: `5c8c087c`.
- Index size: `177.0 MB`.
- Artifact backend: `local_workspace`.
- Artifact health: `missing`.

Semantic evidence from the same status surface:

- Summary-backed chunks: `0`.
- Chunks missing summaries: `66463`.
- Vector-linked chunks: `0`.
- Chunks missing vectors: `66463`.
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

Local multi-repo dogfooding is **not ready** under the default `oss_high`
setup proven by this rebuild.

Why:

- A clean force-full rebuild still produced `0` `chunk_summaries`.
- The same rebuild produced `0` `semantic_points`.
- Active-profile preflight still failed with `wrong_chat_model`.
- Semantic queries therefore stayed fail-closed with `semantic_not_ready`
  instead of returning semantic-path implementation results.

Steering outcome:

- `SEMDOGFOOD` remains valid as an evidence phase.
- The roadmap required a new downstream repair phase, now recorded as
  `SEMREADYFIX`, to repair default enrichment compatibility and rerun the
  dogfood proof after the blocker is fixed.

## Verification

Executed in this phase:

```bash
uv run pytest tests/test_repository_commands.py -q --no-cov
uv run pytest tests/test_benchmark_query_regressions.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index preflight
/usr/bin/time -v env SEMANTIC_SEARCH_ENABLED=true SEMANTIC_DEFAULT_PROFILE=oss_high OPENAI_API_KEY=dummy-local-key QDRANT_URL=http://localhost:6333 uv run mcp-index repository sync --force-full
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
```

Observed test outcomes:

- `tests/test_repository_commands.py`: passed.
- `tests/test_benchmark_query_regressions.py`: passed.
- `tests/real_world/test_semantic_search.py`: skipped under the rebuilt repo
  because the semantic dogfood query path remained `semantic_not_ready`.

Pending verification tied to this report artifact:

```bash
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "SEMANTIC_DOGFOOD_REBUILD|lexical readiness|semantic readiness|active-profile preflight|code_index__oss_high__v1|semantic_points|chunk_summaries" docs/status/SEMANTIC_DOGFOOD_REBUILD.md docs/guides/semantic-onboarding.md tests/docs/test_semdogfood_evidence_contract.py
```
