# Claude Agent Instructions
> **AI Agents:** Do not modify this file directly. Add any updates to `AGENTS.md` in this directory.

This repository uses `AGENTS.md` for all agent guidance and configuration.
Please refer to the adjacent `AGENTS.md` file in this directory for full
instructions and notes.

Current dependency setup uses `uv sync --locked`. Language and sandbox support
claims are centralized in `docs/SUPPORT_MATRIX.md`.

## Search Tool Priority (MCP-FIRST)

This repo has a pre-built code index (BM25 + semantic). **Always search with MCP tools
before using Grep or Glob.** Using native tools first wastes context and ignores 100x
faster indexed retrieval.

**Required order:**
1. `mcp__code-index-mcp__symbol_lookup` — for any symbol/class/function lookup
2. `mcp__code-index-mcp__search_code` — for any pattern or content search
3. Native Grep/Glob — ONLY if MCP search returns 0 results

**Cost:** Using Grep instead of MCP when MCP is available is always wrong. MCP indexed
search is <500ms and returns ranked results with line numbers. Grep through this repo takes
~45 seconds and returns unranked noise.

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

# Debugging Guidelines
- Never use broken MCP Tools to debug the same broken MCP Tool
