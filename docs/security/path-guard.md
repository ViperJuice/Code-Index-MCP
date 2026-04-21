# Path Traversal Guard

> **Beta status**: This page targets `1.2.0-rc3`. `MCP_ALLOWED_ROOTS` is the
> current path boundary knob for MCP tools in beta multi-repo deployments.

## Overview

The path traversal guard (SL-4) prevents search results from leaking paths outside of explicitly allowed repository roots. This document describes the guard's operation, configuration, and fallback behavior.

## Mechanism

The `PathTraversalGuard` class wraps path normalization and validation:

```python
def normalize_and_check(path: str, allowed_roots: list[Path]) -> Path
```

This function:
1. Normalizes the path (resolves `.` and `..`, removes trailing slashes).
2. Verifies that the resolved path falls within at least one of the `allowed_roots`.
3. Returns the normalized `Path` if valid.
4. Raises `PathTraversalError` if the path escapes all allowed roots.

## Integration Point

The guard is wired in the dispatcher's `_normalize_search_result` method, which processes each search result before returning to the client. This ensures that symlinks, relative paths, and other tricks cannot escape the allowed boundaries.

## Configuration

Set the list of allowed roots via the `MCP_ALLOWED_ROOTS` environment variable:

```bash
export MCP_ALLOWED_ROOTS="/home/user/repo1:/home/user/repo2:/var/indexed-code"
```

Paths are separated by the OS path separator (`os.pathsep`; `:` on Unix, `;` on Windows).

## Fallback Behavior

- **Unset `MCP_ALLOWED_ROOTS`**: The guard becomes a no-op in `_normalize_search_result`. This allows development and testing without configuring roots, but **provides no protection**. Suitable for air-gapped single-repo usage only.
- **Empty `MCP_ALLOWED_ROOTS`**: Same as unset (no-op).
- **Misconfigured roots**: If a repo is not included in the roots list, its search results will be rejected. This is the safe default.

## Threat Model

**What it prevents**:
- Search results returning paths outside the indexed repositories
- Symlink-based escapes (by resolving before checking)
- Relative-path traversal (normalized before checking)

**What it does NOT prevent**:
- Information leakage via error messages (a 403 "forbidden path" reveals the attempted path)
- Brute-force guessing of paths (attackers must already be able to trigger searches)
- Denial of service via expensive path normalization (should be <1 ms per result)

## Recommended Usage

For multi-repo deployments:
1. Enumerate all repository roots in `MCP_ALLOWED_ROOTS` at startup.
2. Use absolute paths (not relative to `MCP_WORKSPACE_ROOT`).
3. Verify that the list is synchronized with your actual indexed repos.
4. Audit the list quarterly as repos are added/removed.
