# Repo Root Cleanup Inventory

Audit date: 2026-07-06
Phase plan: `plans/phase-plan-v9-REPOCLEAN.md`

## Audit Commands

```bash
uv run python scripts/repo_clean_audit.py --json --max-path 160
uv run python scripts/repo_clean_audit.py --json --max-path 160 --wheel-depth
git ls-files -ci --exclude-standard
git ls-files | python -c "import sys; paths=[p.rstrip('\n') for p in sys.stdin]; print(max((len(p), p) for p in paths)); assert all(len(p) <= 160 for p in paths)"
```

## Generated Path Classes

| Class | Decision | Notes |
| --- | --- | --- |
| `runtime_metadata` | drop | Removed tracked `.metadata/**` runtime outputs, including legacy artifact metadata. |
| `root_generated_json` | drop | Removed tracked root JSON result dumps and status outputs such as `INDEXING_STATUS.json`. |
| `root_generated_log` | drop | Removed `full_indexing_log.txt`. |
| `root_generated_markdown` | drop | Removed root generated report/status/summary/analysis Markdown files matched by the cleanup contract. |
| `analysis_archive` | drop | Removed the tracked `analysis_archive/` scratch tree rather than preserving a raw archive policy in git. |
| `generated_results` | drop | Removed tracked result trees such as `performance_reports/`, `reports/`, `test_indexes/`, and `test_results/`. |

Result: `scripts/repo_clean_audit.py --json --max-path 160` reports
`tracked_generated_candidates: []` after cleanup.

## Tracked-But-Ignored Classes

`git ls-files -ci --exclude-standard` still reports these tracked paths after
cleanup:

| Class | Paths | Decision | Rationale |
| --- | --- | --- | --- |
| `tracked_editor_rules_under_ignored_parent` | `.cursor/rules/*.mdc` | keep | Team-shared editor guidance remains tracked even though `.cursor/` stays ignored for user-local state. |
| `tracked_generated_metadata_under_runtime_ignore` | `.index_metadata.json` | defer | Legacy tracked index metadata remains outside the active owned-file set; it needs a later explicit keep/drop decision. |
| `tracked_local_mcp_example_under_private_ignore` | `.mcp.json` | defer | Existing tracked local MCP config remains outside the active owned-file set; cleanup recorded it instead of mutating an unowned private config surface. |

The broad `cache/` ignore hazard was repaired by scoping the ignore rule to
`/cache/`, so `mcp_server/cache/` is no longer classified as tracked-but-ignored
source.

## Keep Drop Defer Decisions

- Drop: 373 phase-owned generated paths were removed from git via the REPOCLEAN
  inventory.
- Keep: `docs/status/public-package-identity.md`,
  `code-index-mcp.profiles.yaml`, `mcp-index-kit/`, `.mcp.json.example`, and
  `.mcp.json.templates/` were preserved.
- Keep: source and test files were preserved unless explicitly listed in the
  cleanup inventory above.
- Defer: `.index_metadata.json` and `.mcp.json` remain for a later bounded
  cleanup because the active plan did not own those exact paths.

## Path-Length Audit

- Longest tracked path: `docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json` (`94`)
- Over-limit tracked paths above the 160-character tracked-path limit: none

## Wheel Path-Depth Audit

- Max wheel site-packages member path:
  `mcp_server/indexing/baml_client/baml_client/async_client.py` (`59`)
- The wheel audit stayed below the same 160-character tracked-path limit used
  for the public tree.

## Windows Fallback

The primary mitigation is the cleaned source tree plus the path-length audits
above. If a Windows checkout still fails because of a deep clone root or
third-party tooling, use `git config --global core.longpaths true` as a
fallback after the repo tree is clean.
