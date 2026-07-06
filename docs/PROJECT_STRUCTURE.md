# Project Structure
Updated: 2026-07-06

## Overview

This repository keeps tracked source, docs, tests, and durable evidence in git.
Generated analysis dumps, scratch result trees, runtime indexes, and local
operator state are intentionally excluded from the public source layout.

## Tracked Top-Level Layout

- `mcp_server/` - Core MCP server package, plugins, CLI, storage, and watcher code
- `scripts/` - Developer and operator helper scripts that remain part of the repo surface
- `tests/` - Unit, docs-contract, smoke, and security coverage
- `docs/` - Product, operations, validation, and status documentation
- `mcp-index-kit/` - Shared MCP indexing toolkit and examples
- `architecture/` - Architecture diagrams and supporting design material
- `docker/` - Container build and compose assets
- `specs/`, `plans/` - Roadmaps and bounded phase plans

## Public Root Files

The root keeps the public-facing repository surfaces that users and reviewers
need directly:

- `README.md`, `TROUBLESHOOTING.md`, `CHANGELOG.md`, `LICENSE`
- `pyproject.toml`, `uv.lock`, `pytest.ini`, `Makefile`
- `AGENTS.md`, `CLAUDE.md`, `.mcp.json.example`, `.mcp.json.templates/`
- `code-index-mcp.profiles.yaml`, `docker-compose*.yml`

## Durable Evidence

Tracked evidence belongs under committed documentation paths such as:

- `docs/status/` for status and release-boundary notes
- `docs/benchmarks/` for intentionally retained benchmark material
- `docs/validation/` for contract and verification documents

These locations replace ad hoc root-level result dumps and scratch directories.

## Local-Only Outputs

The following classes are local runtime or generated outputs, not first-class
tracked layout:

- local indexes and caches such as `.indexes/`, `.mcp-index/`, `build/`, `dist/`
- generated reports and scratch result trees
- local phase-loop or dev-skill runtime state
- temporary logs, coverage artifacts, and benchmark output

If these need to be retained as evidence, summarize them into `docs/status/` or
another approved committed documentation path instead of committing the raw
output tree.

## Windows Path Guidance

REPOCLEAN keeps tracked repository-relative paths at or below the
160-character tracked-path limit and records a wheel-content path-depth audit
for installed files. If a Windows clone still encounters long-path failures
because of a deep checkout root or third-party tooling, use
`git config --global core.longpaths true` as a fallback after the repo tree is
clean.
