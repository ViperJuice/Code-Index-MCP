> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**

# Private Alpha Decision

Raw private-alpha evidence belongs only under ignored `private-alpha-evidence/`.
This committed record contains redacted fixture categories, aggregate timings,
issue classifications, and the public-alpha decision.

Generated at: `2026-04-22T04:34:25+00:00`
Schema version: `1.0`
Decision summary: `go`

## Fixture Inventory

| Fixture category | Install time | First index time | p50 | p95 | Blocker classification |
|---|---:|---:|---:|---:|---|
| python_repo | 37.076 | 2.414 | 41.288 | 41.288 | post_alpha_backlog |
| typescript_js_repo | 37.076 | 2.244 | 42.564 | 42.564 | post_alpha_backlog |
| mixed_docs_code_repo | 37.076 | 2.259 | 43.285 | 43.285 | post_alpha_backlog |
| multi_repo_workspace | 37.076 | 2.305 | 45.535 | 45.535 | post_alpha_backlog |
| large_ignored_vendor_repo | 37.076 | 2.249 | 43.243 | 43.243 | post_alpha_backlog |

## Install/Index/Query Evidence

### python_repo

- Install time: `37.076` seconds.
- First index time: `2.414` seconds.
- Query latency p50: `41.288` ms.
- Query latency p95: `41.288` ms.
- Result quality notes: Matched 1/1 expected path fragments in redacted fixture checks.
- Log noise classification: `medium`.
- Branch/default-branch behavior: Local checkout confirmed suitable for default-branch evidence smoke; multi-repo production policy remains documented in the deployment runbook.
- Rollback/rebuild behavior: Release smoke rebuild path completed during the harness run.
- Blocker classification: `post_alpha_backlog`.

### typescript_js_repo

- Install time: `37.076` seconds.
- First index time: `2.244` seconds.
- Query latency p50: `42.564` ms.
- Query latency p95: `42.564` ms.
- Result quality notes: Matched 1/1 expected path fragments in redacted fixture checks.
- Log noise classification: `medium`.
- Branch/default-branch behavior: Local checkout used as a mixed-language stand-in; default-branch behavior remained non-blocking for this smoke.
- Rollback/rebuild behavior: Release smoke rebuild path completed during the harness run.
- Blocker classification: `post_alpha_backlog`.

### mixed_docs_code_repo

- Install time: `37.076` seconds.
- First index time: `2.259` seconds.
- Query latency p50: `43.285` ms.
- Query latency p95: `43.285` ms.
- Result quality notes: Matched 1/1 expected path fragments in redacted fixture checks.
- Log noise classification: `medium`.
- Branch/default-branch behavior: Local docs/code checkout exercised branch-neutral file discovery.
- Rollback/rebuild behavior: Release smoke rebuild path completed during the harness run.
- Blocker classification: `post_alpha_backlog`.

### multi_repo_workspace

- Install time: `37.076` seconds.
- First index time: `2.305` seconds.
- Query latency p50: `45.535` ms.
- Query latency p95: `45.535` ms.
- Result quality notes: Matched 1/1 expected path fragments in redacted fixture checks.
- Log noise classification: `medium`.
- Branch/default-branch behavior: Local checkout confirmed the public multi-repo docs and tests remain discoverable; real multi-repo fleet evidence should replace this smoke before promotion.
- Rollback/rebuild behavior: Release smoke rebuild path completed during the harness run.
- Blocker classification: `post_alpha_backlog`.

### large_ignored_vendor_repo

- Install time: `37.076` seconds.
- First index time: `2.249` seconds.
- Query latency p50: `43.243` ms.
- Query latency p95: `43.243` ms.
- Result quality notes: Matched 1/1 expected path fragments in redacted fixture checks.
- Log noise classification: `medium`.
- Branch/default-branch behavior: Local checkout exercised ignored-output boundary checks for P26 evidence.
- Rollback/rebuild behavior: Release smoke rebuild path completed during the harness run.
- Blocker classification: `post_alpha_backlog`.

## Known Issue Classification

| Issue ID | Classification | Summary | Disposition |
|---|---|---|---|
| P26-LOCAL-001 | `documented_limitation` | This run uses a local checkout as fixture evidence rather than customer repositories. | Acceptable for machine-local smoke; replace with operator-selected private repositories before external release approval. |
| P26-LOCAL-002 | `post_alpha_backlog` | Harness quality checks currently use path-fragment evidence rather than full MCP semantic relevance scoring. | Keep the harness conservative and extend retrieval scoring after public alpha. |

Issue buckets used for this decision: `public_alpha_blocker`,
`documented_limitation`, and `post_alpha_backlog`.

## Release-Note Readiness

- Supported install paths are the local `uv sync --locked`/STDIO path and the
  `ghcr.io/viperjuice/code-index-mcp` container path.
- Language coverage is bounded by `docs/SUPPORT_MATRIX.md`.
- Beta warnings and rollback instructions are maintained in
  `docs/operations/deployment-runbook.md`.

## Public Alpha Decision

Final decision: `go`
