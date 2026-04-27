# Dogfood Index Reset - 2026-04-27

## Scope

Reset stale repo-local index artifacts for `/home/viperjuice/code/Code-Index-MCP`
and rebuilt the local dogfood index from scratch.

Removed before the clean run:

- `.mcp-index/`
- `.code_index.db`
- `code_index.db`
- `vector_index.qdrant`
- `.indexes/`
- `.claude/worktrees/code_index.db`

Left intact:

- `qdrant_storage/` - 11G live Qdrant service storage. A Qdrant process was
  running on port 6333 and collections are language-level, so this was not
  deleted as part of the repo-local reset.

## Clean Run

Command:

```bash
/usr/bin/time -v env \
  SEMANTIC_SEARCH_ENABLED=true \
  SEMANTIC_DEFAULT_PROFILE=oss_high \
  VLLM_EMBEDDING_BASE_URL=http://ai:8001/v1 \
  OPENAI_API_KEY=dummy-local-key \
  QDRANT_URL=http://localhost:6333 \
  uv run mcp-index repository sync --force-full
```

Result:

- Exit status: 0
- CLI result: `Indexed 1357 files in 1686.6s`
- Wall time: `28:10.51`
- User time: `239.14s`
- System time: `71.35s`
- CPU: `18%`
- Max RSS: `403984 KB`
- File system outputs: `26694576` blocks

## Final Index State

SQLite counts from `.mcp-index/current.db`:

- Files: `1345`
- Symbols: `23491`
- Chunks: `66799`
- Repositories: `1`

Disk usage:

- `.mcp-index/`: `175M`
- `qdrant_storage/`: `11G` (not reset)

Repository status after rebuild:

- Repository: `Code-Index-MCP`
- Repository ID: `74f50742925c9613`
- Indexed commit: `55eedd68`
- Readiness: `ready`
- Query surface: `ready`
- Artifact backend: `local_workspace`
- Artifact health: `missing`

## Notes

Preflight reports working-tree drift until the dogfood hardening fixes are
committed, because the rebuilt index is tied to commit `55eedd68` while the
working tree contains the fixes that made this clean run reliable.

## Post-Commit Incremental Sync

After committing the dogfood hardening fixes, a normal repository sync advanced
the index to the new commit.

Result:

- Exit status: 0
- CLI result: `Indexed 10 files in 11.3s`
- Wall time: `0:13.50`
- User time: `7.71s`
- System time: `0.83s`
- CPU: `63%`
- Max RSS: `146512 KB`
- File system outputs: `203632` blocks
