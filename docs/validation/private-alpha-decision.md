> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**

# Private Alpha Decision

Raw private-alpha evidence belongs only under ignored `private-alpha-evidence/`.
This committed record contains redacted fixture categories, aggregate timings,
issue classifications, and the public-alpha decision.

Generated at: `2026-04-22T23:04:35+00:00`
Schema version: `1.0`
Decision summary: `conditional_go`

## Fixture Inventory

| Fixture category | Install time | First index time | p50 | p95 | Blocker classification |
|---|---:|---:|---:|---:|---|
| python_repo | 32.864 | 0.041 | 39.289 | 39.289 | post_alpha_backlog |
| typescript_js_repo | 32.864 | 0.089 | 84.544 | 84.544 | post_alpha_backlog |
| mixed_docs_code_repo | 32.864 | 0.001 | 0.289 | 0.518 | post_alpha_backlog |
| multi_repo_workspace | 32.864 | 0.073 | 34.837 | 63.454 | post_alpha_backlog |
| large_ignored_vendor_repo | 32.864 | 0.122 | 121.124 | 121.124 | post_alpha_backlog |

## Install/Index/Query Evidence

### python_repo

- Install time: `32.864` seconds.
- First index time: `0.041` seconds.
- Query latency p50: `39.289` ms.
- Query latency p95: `39.289` ms.
- Result quality notes: Matched 1/1 expected path fragments in redacted fixture checks.
- Log noise classification: `low`.
- Branch/default-branch behavior: Operator-owned Python checkout exercised default-branch-neutral file discovery; documented default-branch tracking remains the production policy.
- Rollback/rebuild behavior: Release smoke rebuild path completed during this evidence run.
- Blocker classification: `post_alpha_backlog`.

### typescript_js_repo

- Install time: `32.864` seconds.
- First index time: `0.089` seconds.
- Query latency p50: `84.544` ms.
- Query latency p95: `84.544` ms.
- Result quality notes: Matched 1/1 expected path fragments in redacted fixture checks.
- Log noise classification: `low`.
- Branch/default-branch behavior: Operator-owned TypeScript checkout exercised default-branch-neutral file discovery.
- Rollback/rebuild behavior: Release smoke rebuild path completed during this evidence run.
- Blocker classification: `post_alpha_backlog`.

### mixed_docs_code_repo

- Install time: `32.864` seconds.
- First index time: `0.001` seconds.
- Query latency p50: `0.289` ms.
- Query latency p95: `0.518` ms.
- Result quality notes: Matched 2/2 expected path fragments in redacted fixture checks.
- Log noise classification: `low`.
- Branch/default-branch behavior: Operator-owned mixed docs/code checkout exercised branch-neutral file discovery across Markdown and TypeScript.
- Rollback/rebuild behavior: Release smoke rebuild path completed during this evidence run.
- Blocker classification: `post_alpha_backlog`.

### multi_repo_workspace

- Install time: `32.864` seconds.
- First index time: `0.073` seconds.
- Query latency p50: `34.837` ms.
- Query latency p95: `63.454` ms.
- Result quality notes: Matched 2/2 expected path fragments in redacted fixture checks.
- Log noise classification: `low`.
- Branch/default-branch behavior: Operator-owned nested workspace exercised file discovery across root and nested repository boundaries; registered-repo default-branch tracking remains covered by the multi-repo tests.
- Rollback/rebuild behavior: Release smoke rebuild path completed during this evidence run.
- Blocker classification: `post_alpha_backlog`.

### large_ignored_vendor_repo

- Install time: `32.864` seconds.
- First index time: `0.122` seconds.
- Query latency p50: `121.124` ms.
- Query latency p95: `121.124` ms.
- Result quality notes: Matched 1/1 expected path fragments in redacted fixture checks.
- Log noise classification: `low`.
- Branch/default-branch behavior: Operator-owned vendor-heavy checkout exercised discovery in a repo containing ignored/generated dependency directories.
- Rollback/rebuild behavior: Release smoke rebuild path completed during this evidence run.
- Blocker classification: `post_alpha_backlog`.

## Known Issue Classification

| Issue ID | Classification | Summary | Disposition |
|---|---|---|---|
| P26-LOCAL-001 | `documented_limitation` | Private-alpha evidence uses operator-owned local repositories selected on this workstation rather than external customer repositories. | Acceptable for public-alpha readiness smoke; repeat with named customer opt-in repositories before stable release. |
| P26-LOCAL-002 | `post_alpha_backlog` | Harness quality checks currently use redacted path-fragment matching rather than full MCP semantic relevance scoring. | Keep the conservative harness for public alpha and extend retrieval scoring before stable release. |

Issue buckets used for this decision: `public_alpha_blocker`,
`documented_limitation`, and `post_alpha_backlog`.

## Release-Note Readiness

- Supported install paths are the local `uv sync --locked`/STDIO path and the
  `ghcr.io/viperjuice/code-index-mcp` container path.
- Language coverage is bounded by `docs/SUPPORT_MATRIX.md`.
- Beta warnings and rollback instructions are maintained in
  `docs/operations/deployment-runbook.md`.

## Public Alpha Decision

Final decision: `conditional_go`
