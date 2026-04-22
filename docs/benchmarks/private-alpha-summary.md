# Private Alpha Benchmark Summary

This P26 summary is the committed redacted aggregate companion to
`docs/validation/private-alpha-decision.md`. Raw private-alpha output must remain
under ignored `private-alpha-evidence/`.

| Fixture category | Install time | First index time | p50 query latency | p95 query latency | Result quality | Log noise |
|---|---:|---:|---:|---:|---|---|
| python_repo | 37.076 | 2.414 | 41.288 | 41.288 | Matched 1/1 expected path fragments | medium |
| typescript_js_repo | 37.076 | 2.244 | 42.564 | 42.564 | Matched 1/1 expected path fragments | medium |
| mixed_docs_code_repo | 37.076 | 2.259 | 43.285 | 43.285 | Matched 1/1 expected path fragments | medium |
| multi_repo_workspace | 37.076 | 2.305 | 45.535 | 45.535 | Matched 1/1 expected path fragments | medium |
| large_ignored_vendor_repo | 37.076 | 2.249 | 43.243 | 43.243 | Matched 1/1 expected path fragments | medium |

These numbers come from a machine-local P26 smoke run against a local checkout.
They are suitable for validating the harness and redaction path, but operator
approval for external public alpha should replace them with the selected private
fixture set.
