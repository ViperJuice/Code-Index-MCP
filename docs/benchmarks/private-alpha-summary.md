# Private Alpha Benchmark Summary

This P26 summary is the committed redacted aggregate companion to
`docs/validation/private-alpha-decision.md`. Raw private-alpha output must remain
under ignored `private-alpha-evidence/`.

| Fixture category | Install time | First index time | p50 query latency | p95 query latency | Result quality | Log noise |
|---|---:|---:|---:|---:|---|---|
| python_repo | 32.864 | 0.041 | 39.289 | 39.289 | Matched 1/1 expected path fragments | low |
| typescript_js_repo | 32.864 | 0.089 | 84.544 | 84.544 | Matched 1/1 expected path fragments | low |
| mixed_docs_code_repo | 32.864 | 0.001 | 0.289 | 0.518 | Matched 2/2 expected path fragments | low |
| multi_repo_workspace | 32.864 | 0.073 | 34.837 | 63.454 | Matched 2/2 expected path fragments | low |
| large_ignored_vendor_repo | 32.864 | 0.122 | 121.124 | 121.124 | Matched 1/1 expected path fragments | low |

These numbers come from a machine-local P26 smoke run against operator-selected
local fixture repositories. They are suitable for public-alpha readiness smoke;
repeat with named customer opt-in repositories before stable release.
