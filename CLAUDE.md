# Claude Agent Instructions
> **AI Agents:** Do not modify this file directly. Add any updates to `AGENTS.md` in this directory.

This repository uses `AGENTS.md` for all agent guidance and configuration.
Please refer to the adjacent `AGENTS.md` file in this directory for full
instructions and notes.

Current dependency setup uses `uv sync --locked`. Language and sandbox support
claims are centralized in `docs/SUPPORT_MATRIX.md`.

## Search Tool Priority

Use indexed MCP search only when repository readiness is `ready`, or when a
ready tool response is already available. Check `get_status` first when
readiness is unknown. If `search_code` or `symbol_lookup` returns
`index_unavailable` with `safe_fallback: "native_search"`, use native Grep/Glob
or follow the returned readiness remediation such as `reindex`.

The v3 public-alpha repository model supports many unrelated repositories on one
machine, with one registered worktree per git common directory. Only the
tracked/default branch is indexed automatically; same-repo sibling worktrees and
non-default branch queries are not authoritative indexed-search contexts until
readiness is `ready`.

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

# Debugging Guidelines
- Never use broken MCP Tools to debug the same broken MCP Tool
