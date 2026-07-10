# Comprehensive Hardening V10

## Verdict

The eight-phase v10 hardening roadmap is locally verified for controlled beta
rollout. Authentication boundaries, exact repository selection, readiness
recovery, summarization contracts, bounded plugin workers, local quality gates,
and release preparation are covered by executable tests. This evidence run did
no broad fleet indexing and no external release dispatch.

## Browser And Admin UI

The admin gateway was started with generated ephemeral credentials and isolated
temporary state. The metadata-only probe passed with `/docs` `200`,
`/openapi.json` `200`, and unauthenticated `/metrics` `401`:

```text
uv run --python 3.12 python scripts/admin_browser_smoke.py --base-url http://127.0.0.1:<port> --expect-unauthorized --json-output /tmp/code-index-mcp-hardverify/admin.json
```

Playwright rendered the Swagger UI at 1440x1000 and 390x844, exercised the
visible `GET /metrics` operation, and displayed its `401` response. A clean docs
navigation produced console errors: `0`; both viewport checks produced
overlap violations: `0` and no horizontal overflow.

- `/tmp/code-index-mcp-hardverify/admin-docs-desktop.png`
- `/tmp/code-index-mcp-hardverify/admin-docs-mobile.png`

## MCP And Runtime

`uv run --python 3.12 python scripts/hardening_e2e.py --json-output
/tmp/code-index-mcp-hardverify/runtime.json` passed all six frozen groups with
47 passed: STDIO SDK and secondary tools (3), repository isolation/refusal (2),
readiness/recovery (4), worker lifecycle (5), handshake enforcement (30), and
signal cleanup (3). The reducer records only group metadata and summaries.

Default pytest execution retains the socket guard that denies unmarked network
access. Intentional local-server tests remain explicitly marked.

## Package, Quality, And Security

- `uv sync --locked --extra dev --link-mode=copy` reproduced the locked
  development environment.
- `make release-smoke` passed: the 1.3.1 wheel built, installed into an isolated
  environment, exposed both CLI entrypoints, and completed STDIO search.
- Workflow-policy tests passed 9 tests, proving immutable action refs and
  protected-main release mutation guards.
- `uv run --python 3.12 python scripts/check_mypy_baseline.py` passed with 1,540
  current errors at or below the 1,562-error baseline; the 43-file
  release-critical mypy surface passed with zero errors.
- `uv run --python 3.12 bandit -r mcp_server -f json -o
  /tmp/code-index-mcp-hardverify/bandit.json` reported zero high-severity
  findings (60 medium and 284 low findings remain for normal triage).
- `uv run --python 3.12 pytest tests --benchmark-skip --no-cov` passed after
  final review repairs with 2,639 passed, 140 skipped, and 38 deselected.
- `make alpha-release-gates` passed after all hardening edits, covering locked
  dependency sync, format/lint, the type ratchet, unit and integration smokes,
  documentation truth, the production matrix, and wheel/STDIO release smoke.

## Release Posture

Version 1.3.1 is prepared and unpublished. Local and remote tag checks, GitHub
release checks, and the PyPI project-version probe found no 1.3.1 collision.
No tag, release, container, provenance artifact, or package was published.

## Final Panel Review

GPT-5.5, Gemini 3.1 Pro High, and Fable independently reviewed the cumulative
eight-phase patch. Gemini found no blocker; GPT-5.5 and Fable identified six
substantive integration findings. All six were accepted and repaired: the
container workflow now proves protected-main ancestry before push and signing,
the STDIO handshake precedes lazy initialization, exact registered aliases are
classified before path sandboxing, authentication executes before
authorization, healthy readiness checks are safely cached, and unpublished
container instructions default to a local smoke image. The reconciled review
is recorded in `specs/phase-plans-v10_final_code_review.md`.

The first post-repair canonical gate then exposed a seventh integration defect:
activating authorization caused the legacy gateway routes to be default-denied
because the access table covered only `/api/v1/*`. The gateway now has explicit
least-privilege rules for its real route surface, while route-aware middleware
preserves authenticated `404` and `405` responses. The gateway and auth-boundary
regression matrix passes 61 tests, and the repeated canonical gate passes.

In focused confirmation, Gemini returned `AGREE`; GPT-5.5 identified one final
P2 audit-semantics gap for `/api/v1/security/events`. The gap was repaired with
an admin-only middleware rule and regression. Fable returned `AGREE` on that
corrected frozen patch, and GPT-5.5's focused follow-up also returned `AGREE`.
No panel finding remains open.

## Residual Risk

Multi-repository and STDIO operation remain beta, so the correct posture is
controlled rollout rather than fleet-wide indexing. The full-project mypy debt
is bounded by a no-growth ratchet but is not zero. Bandit's medium and low
advisories remain visible in the JSON evidence; the release blocker threshold
of zero high-severity findings is satisfied.
