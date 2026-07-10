# Comprehensive Hardening V10 Final Review Reconciliation

## Panel

The cumulative `origin/main...2a8efd1` patch was reviewed independently by
GPT-5.5 at high reasoning, Gemini 3.1 Pro High, and Fable
(`claude-fable-5`). The review was blocking: concrete findings had to be fixed
and re-verified before the roadmap could close.

| Reviewer | Initial verdict | Substantive result |
|---|---|---|
| GPT-5.5 | `DISAGREE` | Three authentication, repository-selection, and release-install findings |
| Gemini 3.1 Pro High | `AGREE` | No blocking findings |
| Fable | `PARTIALLY AGREE` | Three release, middleware, and readiness-performance findings |

## Reconciled Findings

All six findings were accepted as valid and repaired:

1. **P1, release ancestry:** tag-triggered container publication could push and
   sign without proving the tagged commit belonged to protected `main`.
   Publication and signing now perform a full-depth exact-SHA checkout and an
   adjacent protected-main ancestry/version guard.
2. **P1, STDIO handshake boundary:** lazy service construction ran before the
   handshake gate. `call_tool` now handles the handshake and rejects all other
   pre-handshake calls before request context or service initialization.
3. **P2, repository aliases:** an exact registered name that collided with a
   relative filesystem path could be sandboxed before alias classification.
   Exact IDs/names and ambiguous aliases are classified first across every
   affected tool; explicit filesystem paths still receive sandbox checks.
4. **P2, middleware order:** Starlette's reverse middleware wrapping caused
   authorization to execute before authentication. Registration order now
   makes authentication execute first, with a regression assertion.
5. **P2, readiness cost:** SQLite `quick_check` ran on every tool query. Healthy
   inspection results now use a bounded, signature-keyed cache that includes
   database/WAL/SHM identity; failures are never cached, and atomic publication
   clears the cache.
6. **P2, unpublished image default:** README and Docker installers defaulted to
   the not-yet-published `v1.3.1` image. They now default to the locally built
   `local-smoke` image and explicitly fence candidate-image instructions behind
   protected-main publication.

## Gate-Discovered Defect

The first canonical post-repair gate correctly failed an existing authenticated
gateway test. Once the middleware order was fixed, `AuthorizationMiddleware`
became effective, but the default access table covered only `/api/v1/*`; valid
legacy routes such as `/symbol` were therefore denied. Explicit least-privilege
rules now cover the real gateway surface, with stricter rules for reindex,
plugins, cache mutation, metrics, search administration, and graph
initialization. Authorization is route-aware so nonexistent and wrong-method
requests retain router `404`/`405` responses, while any real unlisted route
still fails closed.

## Repair Verification

The six-finding focused matrix passes 71 tests. The completed readiness cache
suite passes 23 tests, including healthy reuse and transient-failure retry, and
the gateway/auth-boundary matrix passes 61 tests after the gate-discovered
repair. Changed Python files pass Black, isort, Flake8, and the mypy ratchet
(1,540 errors, below the 1,562 baseline). Workflow YAML parses, shell installers
pass `bash -n`, and release metadata and workflow-policy tests exercise the
publication fences. PowerShell is not installed on this host, so the PowerShell
installer is covered by textual contract tests rather than a local parser.

`make alpha-release-gates` passes after the complete repair set. The full
active non-benchmark suite passes with 2,639 passed, 140 skipped, and 38
deselected. Bandit reports zero high-severity findings (60 medium and 284 low).

The focused post-repair three-agent confirmation is recorded below after it
runs against the frozen final repair state.

## Post-Repair Confirmation

The first frozen repair patch had SHA-256
`44c5a707f0aecbac33e9d81127a5779e1bebb5ec480cf20e1b22c451a224e11f`.
Gemini 3.1 Pro High returned `AGREE`. GPT-5.5 returned `PARTIALLY AGREE`
because `/api/v1/security/events` still inherited the broad `/api/v1/*` READ
rule, causing middleware to log authorization before the route's admin
dependency rejected the user.

That dissent was accepted. A specific admin-only security-events rule and a
READ-user/admin regression were added. The corrected frozen patch had SHA-256
`9e39d7b527bb5914e4ed4db8ef6c1ec78e97b766b08bb73453ab27b09bc524ae`.
Fable reviewed that corrected patch and returned `AGREE`. GPT-5.5 then
rechecked its sole finding against the current rule and regression and returned
`AGREE`.

The panel is reconciled: every concrete finding was accepted and repaired, and
no reviewer has an outstanding defect against the final state.
