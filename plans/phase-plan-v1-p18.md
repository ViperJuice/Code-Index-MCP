# P18: Enforcement, Artifact Resilience & Ops

> Plan doc produced by `/plan-phase P18` against `specs/phase-plans-v1.md` lines 957–1013.
> On approval, copy to `plans/phase-plan-v1-p18.md` and hand off to `/execute-phase p18`.

## Context

Phase 17 just closed with the SL-4b carry-over gate missed (19 failures vs. ≤5 target). P18 has two jobs: (1) the scope the spec actually assigns — turn P15's security primitives from "available" into "enforced by default"; harden the artifact publish/download pipeline against partial-failure, missing delta bases, and hostile rate-limiting; wire JSON logs + Prometheus counters + secret redaction; flip `MCP_PLUGIN_SANDBOX_ENABLED` default to on — and (2) the straggler debt from P17 SL-4b, folded in as a new lane so the test-debt ledger can be taken down to zero at phase close.

### What actually exists today (vs. spec wording)

- **Gateway auth surface**: 43 routes in `mcp_server/gateway.py`. Primary auth pattern is `Depends(require_permission(Permission.READ))` (e.g. `/symbol` line 1217, `/search` line 1282). Unprotected routes that SL-1 must action: `/search/capabilities` (line 1472 — in spec), **`/graph/context` (line 2381) and `/graph/search` (line 2443)** — both flagged by `explore-auth-config` as unprotected and not in the spec's whitelist. **Decision: add auth** to both; the whitelist is closed (auth endpoints + `/health*` + `/ready` + `/liveness`) per the exit criterion wording. Recorded under Execution Notes so `execute-phase` doesn't re-litigate.
- **AuthManager startup block**: `gateway.py` lines 341–387. SL-1's fatal-validation hook inserts **before** line 341. SL-4's secret-redaction middleware registration goes inside the existing `SecurityMiddlewareStack.setup_middleware()` call at lines 378–387. Disjoint as promised by the spec.
- **`validate_production_config`** (P16-frozen stub at `config/validation.py:263`) signature is `(config: SecurityConfig, *, environment: str = "production") -> List[ValidationError]`. `ValidationError` is a frozen dataclass at lines 19–23 with `code: str`, `message: str`, `severity: Literal["fatal", "warn"]`. Helpers at `validation.py:34` (`validate_security_config`), `validation.py:273` (`generate_secure_defaults`), and `environment.py:90` (`is_production()`) are reusable. A weak-password blocklist already exists twice (gateway.py:359–361, validation.py:250–252) — SL-1 consolidates these into `config/validation.py` and imports.
- **Artifact publish flow**: `publisher.py:43-91` runs `_ensure_sha_release` (line 126) then `_move_latest_pointer` (line 147). SL-2's try/finally rollback wraps between lines 73–74. `gh release delete` is not yet used; SL-2 adds it — pattern is in `providers/github_actions.py:102–114` (`delete_artifact()`).
- **Delta base handling does not exist today**: `artifact_download.py` line 501 filters delta artifacts but has no base-missing fallback. SL-2 adds the fallback post-metadata-load (after line 146).
- **`_respect_rate_limit`** at `providers/github_actions.py:14–22` reads `X-RateLimit-*` headers with a fixed 300s cap; `Retry-After` is not parsed. 403 and 429 are both raised as `CalledProcessError` without distinction.
- **`TransientArtifactError`/`TerminalArtifactError`** frozen at `core/errors.py:124-129`, parent `ArtifactError(MCPError)`, `MCPError.__init__(message, details=None)`.
- **`mcp_server/cli/commands.py` does not exist** (spec said it did). Actual CLI layout: `mcp_server/cli/__main__.py` is the `python -m mcp_server.cli` entry (only registers `serve` and `stdio`); commands are split across `artifact_commands.py`, `server_commands.py`, `repository_commands.py`, `setup_commands.py`, etc. SL-3 adds a new `retention_commands.py` and registers it in `__main__.py` following the per-concern-file pattern.
- **`plugin_factory.py:260-262`**: `use_sandbox = capabilities is not None or (os.environ.get("MCP_PLUGIN_SANDBOX_ENABLED") == "1")`. Default off. No `MCP_PLUGIN_SANDBOX_DISABLE` read yet. Grep confirms no `socket`/`urlopen` in `mcp_server/plugins/` — flip is expected non-breaking.
- **`core/logging.py`**: plain-text formatter only; no JSON library, no `MCP_LOG_FORMAT` plumbing. SL-4 must add both.
- **Prometheus counters**: `prometheus_exporter.py:62-78` already defines `mcp_tool_calls_total`, `mcp_watcher_sweep_errors_total` (P17), `mcp_storage_readonly_total` (P17) and wires their increments at `watcher/sweeper.py:83`, `storage/sqlite_store.py:259/277`. SL-4 only needs to **define** `mcp_rate_limit_sleeps_total` + `mcp_artifact_errors_by_class_total{error_class}`; their increment sites are owned by SL-2 and will be filled when SL-2 does the rate-limit + raise-site work.
- **Middleware stack** (`security/security_middleware.py:465-491`): five existing middlewares registered in `SecurityMiddlewareStack.setup_middleware()` in documented order. No response-body-rewriting precedent; `SecretRedactionResponseMiddleware` should use Starlette `BaseHTTPMiddleware.dispatch` returning a `Response` with rewritten body, and slot between `RequestValidation` and `RateLimit` so body rewrite happens after routing but before outbound rate-limit accounting.

### P17 straggler surface (SL-6)

- `test_mcp_server_cli.py` (17 failing tests) split into two sub-clusters by patch target:
  1. **11 tests** call `asyncio.run(cli.initialize_services())` and then inspect module-level globals `cli.dispatcher`, `cli.plugin_manager`, `cli.sqlite_store`, `cli.initialization_error`, `cli._file_watcher`, `cli._indexing_thread`, `cli._fts_rebuild_thread` (TestAutoInitGitignore 5, TestMcpAutoIndexEscapeHatch 3, TestDeferredFileWatcher 3). Fix: extract `initialize_services()` from the closure inside `stdio_runner._serve()` as a standalone async function; hoist the 7 state variables to module-level globals.
  2. **6 tests** call `await cli.call_tool("search_code", {"query": ...})` (TestIndexingInProgressFlag 5, TestFreshRepoEndToEnd 1). `call_tool` is registered via `@server.call_tool()` inside `_serve()`. Fix: define the tool-handler body as a standalone async module-level function `call_tool(name, arguments)` and have `_serve()` wrap/register it with the MCP server. Tests hit the standalone directly; the MCP server still sees the same callable via the decorator.
- `test_benchmarks.py` (2 failing tests): `test_benchmark_symbol_lookup_performance` measures 7138ms vs. 100ms SLO (71× over); `test_benchmark_search_performance` measures 7032ms vs. 500ms SLO (14× over). Benchmark run logs show `'Plugin' object has no attribute '_sqlite_store'` errors for `c_sharp`/`csharp` plugin loads — strongly suggests `mock_plugins` is not actually preventing real plugin initialization. SL-6 investigates root cause; fix likely in the fixture (`tests/test_benchmarks.py` `mock_plugins` fixture) or a missing `self._sqlite_store` assignment in a plugin subclass not yet covered by `9d79870` / `cdc299d`. May or may not touch production code — decided at impl time.
- `known-test-debt.md` gets the P17 residual snapshot deleted on SL-6 merge; leaves only future debt.

### P2B rationale confirmed compatible

P2B's SL-2 (`plans/phase-plan-v1-p2b.md:93-105`) extracted CLI handlers out of the 1711-line `scripts/cli/mcp_server_cli.py` monolith. Its goal was **file decomposition**, not closure-based test isolation. `_serve()`'s closure-scoping of mutable state was a consequence of wiring through `server.call_tool()` decorators, not an intentional test-isolation mechanism. SL-6's hoisting of `initialize_services()` + 7 state variables to module level does not reverse P2B's architectural intent — it restores the test-surface that existed before the refactor, on the post-P2B file layout.

### Cross-phase landscape

- P16 merged → taxonomy shapes in `core/errors.py` frozen. SL-2 fills `TransientArtifactError`/`TerminalArtifactError` raise-sites; no class-shape changes.
- P17 merged → SL-1's validation hook is the only remaining security-startup surface to harden. `reset_process_singletons` from P17 is orthogonal.
- P18 runs standalone; no cross-phase freeze-conflicts.

## Interface Freeze Gates

- [ ] **IF-0-P18-1** — `SecretRedactionResponseMiddleware` + registration order: new class in `mcp_server/security/security_middleware.py` following the `BaseHTTPMiddleware` pattern; `SecurityMiddlewareStack.setup_middleware()` registers it between `RequestValidation` and `RateLimit`. Patterns matched: `Bearer \S+`, `JWT_SECRET_KEY=\S+`, `GITHUB_TOKEN=\S+`. Applies to 4xx/5xx response bodies only. **Owner**: SL-4. **Consumers**: SL-docs (documents opt-out and envvar surface), test files for every handler that emits error bodies.

- [ ] **IF-0-P18-2** — `delete_releases_older_than(repo: str, *, older_than_days: Optional[int] = None, keep_latest_n: Optional[int] = None, dry_run: bool = False) -> list[ReleaseRef]` appended to end of `mcp_server/artifacts/providers/github_actions.py`. Returns the list of releases deleted (or that would be deleted if `dry_run`). Raises `TerminalArtifactError` on 403, `TransientArtifactError` on 429 (matches SL-2's existing raise conventions). **Owner**: SL-3. **Consumers**: `mcp_server/artifacts/retention.py`, `mcp_server/cli/retention_commands.py`.

- [ ] **IF-0-P18-3** — `mcp_server.cli.stdio_runner` module surface:
  - `async def initialize_services() -> None` — top-level, no args. Body is the current contents of `_serve()`'s `lazy_initialize()` closure plus the service-pool construction currently at `_serve():234-237`. Writes results to module-level globals.
  - Module-level globals (all initially `None`, reset by `_reset_globals()` in tests): `dispatcher`, `plugin_manager`, `sqlite_store`, `initialization_error`, `_file_watcher`, `_indexing_thread`, `_fts_rebuild_thread`.
  - `async def call_tool(name: str, arguments: dict) -> list[types.TextContent]` — top-level async function; body is the current closure body inside `_serve()` at `stdio_runner.py:430-~595`. `_serve()` registers it with the MCP server via `server.call_tool()(call_tool)`.
  - **Owner**: SL-6. **Consumers**: `tests/test_mcp_server_cli.py` (17 tests), `scripts/cli/mcp_server_cli.py` shim (already delegates — no change needed).

- [ ] **IF-0-P18-4** — Startup-validation error-rendering contract: `validate_production_config()` (P16-frozen signature, body filled by SL-1) returns `List[ValidationError]`. A new helper `render_validation_errors_to_stderr(errors: List[ValidationError]) -> None` formats the list and writes to `sys.stderr`. The `gateway.py` startup path calls `validate_production_config`, renders the list via the helper, and `sys.exit(1)` if **any** `severity=="fatal"`. Dev-mode (non-production) emits `logger.warning(...)` and continues. **Owner**: SL-1. **Consumers**: any future validation lane; SL-docs.

## Lane Index & Dependencies

```
SL-1 — Auth + Config enforcement
  Depends on: (none)
  Blocks: SL-docs
  Parallel-safe: yes

SL-2 — Artifact pipeline resilience
  Depends on: (none)
  Blocks: SL-3 (line-range discipline on github_actions.py), SL-5 (function-block discipline on attestation.py), SL-docs
  Parallel-safe: yes (disjoint line ranges documented in Execution Notes)

SL-3 — Retention janitor
  Depends on: (none — lane is append-only past SL-2's line range in github_actions.py; can develop in parallel, merges after SL-2 if the file lands first)
  Blocks: SL-docs
  Parallel-safe: yes

SL-4 — Observability (JSON logs, secret redaction, counter definitions)
  Depends on: (none)
  Blocks: SL-docs
  Parallel-safe: yes (gateway.py line ranges disjoint from SL-1's)

SL-5 — Safe defaults flip (sandbox on + attestation probe)
  Depends on: (none — attestation.py function block disjoint from SL-2's preflight edits)
  Blocks: SL-docs
  Parallel-safe: yes

SL-6 — P17 straggler burn-down
  Depends on: (none — touches only stdio_runner.py + test files + known-test-debt.md; no overlap with P18's security/artifact surface)
  Blocks: SL-docs
  Parallel-safe: yes

SL-docs — Documentation & spec reconciliation
  Depends on: SL-1, SL-2, SL-3, SL-4, SL-5, SL-6
  Blocks: (terminal)
  Parallel-safe: no (terminal)
```

All six impl lanes are DAG-roots. Two waves: wave-1 ships SL-1, SL-2, SL-4, SL-6 (no shared files); wave-2 ships SL-3 and SL-5 after SL-2 lands (same-file append discipline). `MAX_PARALLEL_LANES=2` per spec Execution Notes → six lanes → three waves; SL-docs last.

## Lanes

### SL-1 — Auth + Config enforcement

- **Scope**: Add auth to `/search/capabilities`, `/graph/context`, `/graph/search`. Fill `validate_production_config` body with weak-JWT / CORS-wildcard / permissive-RATE_LIMIT / missing-admin-password entries. Add `render_validation_errors_to_stderr` helper. Wire the validation call into `gateway.py` startup before `AuthManager` construction. New test file `test_route_auth_coverage.py` introspects `app.routes` and asserts 401 without token on every non-whitelisted route.
- **Owned files**:
  - `mcp_server/gateway.py` — **line ranges 341–343 only** (insert validation call block before `auth_manager = AuthManager(...)`); **line 1472 only** (add `Depends(require_permission(Permission.READ))` to `/search/capabilities`); **lines 2381, 2443 only** (same auth dep on `/graph/context`, `/graph/search`).
  - `mcp_server/config/validation.py` — fill body of `validate_production_config()` (P16-frozen signature at line 263); add `render_validation_errors_to_stderr` helper; consolidate the duplicated weak-password blocklist (gateway.py:359-361 + validation.py:250-252 → single constant in validation.py).
  - `tests/security/test_route_auth_coverage.py` (NEW).
  - `tests/security/test_startup_config_validation.py` (NEW — tests fatal-exit on prod+weak-JWT and WARN-continue on dev+weak-JWT).
- **Interfaces provided**: IF-0-P18-4.
- **Interfaces consumed**: `SecurityConfig`, `Environment` enum, `is_production()` (all pre-existing from P16/environment.py).
- **Parallel-safe**: yes. Gateway line ranges 341–343 + 1472 + 2381 + 2443 are disjoint from SL-4's 378–387.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/security/test_route_auth_coverage.py` (NEW), `tests/security/test_startup_config_validation.py` (NEW) | Every `@app.{get,post,put,delete,patch}` route returns 401 without token unless in whitelist (`/health*`, `/ready`, `/liveness`, `/api/v1/auth/{login,refresh,register}`); prod+weak-JWT → non-zero exit + stderr ValidationError listing; dev+weak-JWT → WARN log + continue | `pytest -q tests/security/test_route_auth_coverage.py tests/security/test_startup_config_validation.py` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/config/validation.py` | — | `pytest -q tests/security/test_startup_config_validation.py` |
| SL-1.3 | impl | SL-1.1 | `mcp_server/gateway.py` (line-range discipline) | — | `pytest -q tests/security/test_route_auth_coverage.py` |
| SL-1.4 | verify | SL-1.2, SL-1.3 | lane-owned | all SL-1 tests + existing `tests/security/` regression | `pytest -q tests/security/ --no-cov` |

**SL-1 impl notes**:
- Validation insertion point: between `gateway.py:340` (end of security_config load) and `gateway.py:341` (`logger.info("Initializing authentication manager...")`). Pattern:
  ```python
  errors = validate_production_config(security_config, environment=str(get_environment()))
  if errors:
      render_validation_errors_to_stderr(errors)
      if any(e.severity == "fatal" for e in errors) and is_production():
          sys.exit(1)
  ```
- `render_validation_errors_to_stderr`: one-line-per-error, prefix `[FATAL]` or `[WARN]`, include code + message. No logger; direct `sys.stderr.write`.
- Weak-JWT heuristic: `len(jwt_secret) < 32` OR `jwt_secret in WEAK_SECRETS_BLOCKLIST`. Blocklist: `{"secret", "password", "changeme", "jwt-secret", "test", "dev", "123", "admin"}` ∪ the existing admin-password blocklist (dedup + move to module constant in validation.py).
- Permissive RATE_LIMIT threshold: `rate_limit_requests > 1000` per minute → fatal in prod; disabled (`rate_limit_enabled = False`) → fatal in prod (mirrors existing warn at validation.py:79-83).
- CORS wildcard: `"*" in cors_allowed_origins` in prod → fatal (mirrors existing validation.py:76).
- Missing admin password: env `DEFAULT_ADMIN_PASSWORD` unset OR in blocklist in prod → fatal.
- `/graph/context` + `/graph/search` get the same `Depends(require_permission(Permission.READ))` as `/search`. Rationale in Execution Notes.

### SL-2 — Artifact pipeline resilience

- **Scope**: (1) `publisher.py` try/finally rollback between `_ensure_sha_release` and `_move_latest_pointer`; on downstream failure, `gh release delete` the SHA release. (2) `artifact_download.py` delta-base-missing fallback → request full artifact. (3) `providers/github_actions.py` `_respect_rate_limit` parses `Retry-After`, distinguishes 429 (backoff + `mcp_rate_limit_sleeps_total.inc()`) from 403 (raise `TerminalArtifactError`). (4) `attestation.py` wrap `attest()` callers in preflight that checks `attestations:write` scope before calling. (5) Every artifact-pipeline raise-site uses `TransientArtifactError` / `TerminalArtifactError` per IF-0-P16-1 and increments `mcp_artifact_errors_by_class_total{error_class=...}`.
- **Owned files**:
  - `mcp_server/artifacts/publisher.py` (lines 55–83 region; insert try/finally between lines 73 and 74)
  - `mcp_server/artifacts/artifact_download.py` (post-line 146 insertion; delta-base fallback)
  - `mcp_server/artifacts/providers/github_actions.py` (`_respect_rate_limit` at lines 14–22; any inline raise-sites — append-only file-end territory reserved for SL-3)
  - `mcp_server/artifacts/attestation.py` (lines 44–76 — `attest` preflight; file-end reserved for SL-5's `probe_gh_attestation_support`)
  - `tests/test_artifact_publish_rollback.py` (NEW)
  - `tests/test_delta_base_fallback.py` (NEW)
  - `tests/test_rate_limit_retry_after.py` (NEW)
- **Interfaces provided**: raise-site coverage for IF-0-P16-1 in `providers/github_actions.py` + `artifact_download.py`; increment sites for `mcp_rate_limit_sleeps_total` and `mcp_artifact_errors_by_class_total`.
- **Interfaces consumed**: `TransientArtifactError`, `TerminalArtifactError` from `core/errors.py` (IF-0-P16-1); the two counters defined by SL-4.
- **Parallel-safe**: yes. SL-2 merges first on `github_actions.py` (inline edits); SL-3 appends after. SL-2 merges first on `attestation.py` (function body); SL-5 appends new function at EOF.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_artifact_publish_rollback.py`, `tests/test_delta_base_fallback.py`, `tests/test_rate_limit_retry_after.py` | Mid-publish kill cleans up SHA release; delta base 404 → full artifact requested; 429 w/Retry-After triggers backoff; 403 raises `TerminalArtifactError` | `pytest -q tests/test_artifact_publish_rollback.py tests/test_delta_base_fallback.py tests/test_rate_limit_retry_after.py` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/artifacts/publisher.py`, `attestation.py` | publish rollback + attest preflight | `pytest -q tests/test_artifact_publish_rollback.py tests/test_artifact_attestation.py` |
| SL-2.3 | impl | SL-2.1 | `mcp_server/artifacts/artifact_download.py` | delta-base fallback | `pytest -q tests/test_delta_base_fallback.py` |
| SL-2.4 | impl | SL-2.1 | `mcp_server/artifacts/providers/github_actions.py` | rate-limit Retry-After + 403/429 branching + counter increments | `pytest -q tests/test_rate_limit_retry_after.py` |
| SL-2.5 | verify | SL-2.2, SL-2.3, SL-2.4 | lane-owned | all SL-2 tests + regression on existing artifact tests | `pytest -q tests/test_artifact_attestation.py tests/test_artifact_publish_race.py tests/test_artifact_freshness.py tests/test_artifact_publish_rollback.py tests/test_delta_base_fallback.py tests/test_rate_limit_retry_after.py` |

**SL-2 impl notes**:
- `publisher.py` try/finally: wrap the `_move_latest_pointer(...)` call at ~line 74 in `try:` followed by `except Exception:` which calls `subprocess.run(["gh", "release", "delete", sha_release_tag, "--yes"], ...)` and re-raises. Idempotent: if `_move_latest_pointer` succeeded before another failure, `except` is never hit. The existing `except ArtifactError` / `except CalledProcessError` at lines 55–83 stays as the outer handler.
- `artifact_download.py` fallback: after metadata load (line 146), inspect `metadata.get("delta_from")`. If set, probe existence of the base release via a HEAD-equivalent (`gh release view <base_tag> --repo owner/repo` exit=0). If missing (404), log WARN + clear the `delta_from` pointer in the download plan and re-request the full artifact from the candidate list.
- `_respect_rate_limit`: parse `Retry-After` header (int seconds or HTTP-date) → sleep min(parsed, 300s) + `mcp_rate_limit_sleeps_total.inc()`. Distinguish by looking at `response.status_code` on the wrapped `gh api` call: 403 → `raise TerminalArtifactError("forbidden / missing scope")` + `mcp_artifact_errors_by_class_total.labels(error_class="TerminalArtifactError").inc()`; 429 → backoff + retry (exponential, cap at 5 attempts).
- Attest preflight: before `subprocess.run(["gh", "attestation", ...])`, call a local `_check_attestation_scope()` helper that runs `gh auth status --show-token` and grep for `attestations:write` in scopes. If missing, log single prominent `ATTESTATION_PREREQ` WARN and fall back per existing `MCP_ATTESTATION_MODE`. The boot-time startup-probe (emits WARN once at boot) is SL-5's responsibility.

### SL-3 — Retention janitor

- **Scope**: Implement `delete_releases_older_than()` appended at EOF of `providers/github_actions.py`. New `mcp_server/artifacts/retention.py` module with policy logic (age vs. count-based retention). New `mcp_server/cli/retention_commands.py` with click group `retention` + subcommand `prune` (flags `--repo`, `--dry-run`, `--older-than-days`, `--keep-latest-n`; env defaults `MCP_ARTIFACT_RETENTION_DAYS`, `MCP_ARTIFACT_RETENTION_COUNT`). Register the group in `mcp_server/cli/__main__.py`.
- **Owned files**:
  - `mcp_server/artifacts/retention.py` (NEW)
  - `mcp_server/artifacts/providers/github_actions.py` — **EOF append only** (after line 115; disjoint from SL-2's inline edits)
  - `mcp_server/cli/retention_commands.py` (NEW)
  - `mcp_server/cli/__main__.py` — **one `_cli.add_command(retention)` line only** (current file has two; lane adds one)
  - `tests/test_retention_janitor.py` (NEW)
- **Interfaces provided**: IF-0-P18-2.
- **Interfaces consumed**: `TransientArtifactError`, `TerminalArtifactError` (IF-0-P16-1); subprocess patterns from `providers/github_actions.py`.
- **Parallel-safe**: yes. `github_actions.py` is append-only past SL-2's inline range; `__main__.py` is a single-line add.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_retention_janitor.py` | `delete_releases_older_than` respects `older_than_days` + `keep_latest_n`; `dry_run=True` deletes nothing and returns the plan; `python -m mcp_server.cli retention prune --repo x/y --dry-run` exits 0 and lists candidates | `pytest -q tests/test_retention_janitor.py` |
| SL-3.2 | impl | SL-3.1 | `mcp_server/artifacts/providers/github_actions.py` (EOF append), `mcp_server/artifacts/retention.py` (NEW) | — | `pytest -q tests/test_retention_janitor.py` |
| SL-3.3 | impl | SL-3.1 | `mcp_server/cli/retention_commands.py` (NEW), `mcp_server/cli/__main__.py` (one-line add) | — | `python -m mcp_server.cli retention prune --help` exits 0 |
| SL-3.4 | verify | SL-3.2, SL-3.3 | lane-owned | all SL-3 tests + the `--dry-run` CLI smoke | `pytest -q tests/test_retention_janitor.py && python -m mcp_server.cli retention prune --repo foo/bar --dry-run --older-than-days 30` |

**SL-3 impl notes**:
- `delete_releases_older_than` signature per IF-0-P18-2. Implementation:
  1. `gh release list --repo <repo> --json tagName,createdAt,isLatest,isDraft --limit 1000`
  2. Filter: drop `isLatest=true` + `tagName == "index-latest"` (protect the pointer); apply age filter; apply keep-latest-N filter (preserve the newest N non-pointer tags).
  3. For each deletable: if `dry_run` skip the call, else `gh release delete <tag> --repo <repo> --yes`.
  4. Wrap subprocess failures per SL-2's raise conventions: 403 → `TerminalArtifactError`; 429 → backoff via `_respect_rate_limit`.
- `retention.py` holds the policy layer (reads env vars, composes the call). No CLI parsing here.
- `retention_commands.py` is click-only: `@click.group()` `retention` + `@retention.command("prune")` that delegates to `retention.py`. Matches existing `artifact_commands.py` style.
- `__main__.py` single-line add: `from mcp_server.cli.retention_commands import retention` + `_cli.add_command(retention)` near the existing `_cli.add_command(serve)` / `_cli.add_command(stdio)` pair.

### SL-4 — Observability

- **Scope**: JSON logging default in production (`MCP_ENVIRONMENT=production` or `MCP_LOG_FORMAT=json`). `SecretRedactionResponseMiddleware` class + registration. Two new Prometheus counter definitions (`mcp_rate_limit_sleeps_total`, `mcp_artifact_errors_by_class_total{error_class}`). One-line middleware registration in `gateway.py`.
- **Owned files**:
  - `mcp_server/core/logging.py` (full file — adds JSON formatter branch)
  - `mcp_server/security/security_middleware.py` — appends new `SecretRedactionResponseMiddleware` class + adds one registration line in `SecurityMiddlewareStack.setup_middleware()` (lines 465–491)
  - `mcp_server/metrics/prometheus_exporter.py` — appends two new `Counter(...)` definitions after line 78 (disjoint from P17's additions)
  - `mcp_server/gateway.py` — **lines 378–387 only** (inside `security_middleware.setup_middleware()` flow; disjoint from SL-1's 341–343 + 1472 + 2381 + 2443)
  - `tests/test_json_logs.py` (NEW)
  - `tests/test_secret_redaction.py` (NEW)
- **Interfaces provided**: IF-0-P18-1; counter definitions for SL-2 to increment.
- **Interfaces consumed**: `Environment` enum + `get_environment()` from `config/environment.py`.
- **Parallel-safe**: yes. Gateway line range disjoint from SL-1's. `prometheus_exporter.py` appends after existing counter block; SL-4 is the only P18 lane defining new counters (no duplicate-name risk).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_json_logs.py`, `tests/test_secret_redaction.py` | Prod-mode log line parses as `json.loads(...)`; dev-mode stays plain-text; response body with `Bearer abc123` in 4xx/5xx is redacted to `Bearer [REDACTED]`; 2xx bodies untouched | `pytest -q tests/test_json_logs.py tests/test_secret_redaction.py` |
| SL-4.2 | impl | SL-4.1 | `mcp_server/core/logging.py` | JSON formatter branch | `pytest -q tests/test_json_logs.py` |
| SL-4.3 | impl | SL-4.1 | `mcp_server/security/security_middleware.py` | `SecretRedactionResponseMiddleware` + stack registration | `pytest -q tests/test_secret_redaction.py` |
| SL-4.4 | impl | SL-4.1 | `mcp_server/metrics/prometheus_exporter.py` | two new counter defs | `python -c "from mcp_server.metrics.prometheus_exporter import mcp_rate_limit_sleeps_total, mcp_artifact_errors_by_class_total"` exits 0 |
| SL-4.5 | impl | SL-4.3 | `mcp_server/gateway.py` (line range 378–387) | middleware registration line | `pytest -q tests/security/` |
| SL-4.6 | verify | SL-4.2..SL-4.5 | lane-owned | all SL-4 tests + prometheus scrape smoke | `pytest -q tests/test_json_logs.py tests/test_secret_redaction.py tests/security/` |

**SL-4 impl notes**:
- JSON formatter: add optional `python-json-logger` to `pyproject.toml` (Dependencies) OR hand-roll a minimal `JSONFormatter(logging.Formatter)` whose `format()` builds a dict (`{"timestamp", "level", "name", "message", **record.__dict__ extras}`) and returns `json.dumps(...)`. Preference: hand-roll, to avoid a new dependency. Gate at `logging.py` `setup_logging()`: `if get_environment() == Environment.PRODUCTION or os.getenv("MCP_LOG_FORMAT") == "json": use JSONFormatter else: use existing plain-text formatter`.
- `SecretRedactionResponseMiddleware`: `BaseHTTPMiddleware.dispatch(request, call_next)` → `response = await call_next(request)`; if `400 <= response.status_code < 600`, read body, apply three regex `re.sub(pattern, replacement, ...)` over:
  - `(Bearer\s+)\S+` → `\1[REDACTED]`
  - `(JWT_SECRET_KEY=)\S+` → `\1[REDACTED]`
  - `(GITHUB_TOKEN=)\S+` → `\1[REDACTED]`
  Return a new `Response(content=redacted_body, status_code=response.status_code, headers=response.headers)`. For streaming bodies use `StreamingResponse` passthrough (do not redact streamed responses; document the limitation).
- Registration point: inside `SecurityMiddlewareStack.setup_middleware()` between the `RequestValidation` and `RateLimit` `add_middleware` calls. One line.
- Counter defs: follow the P17 pattern at `prometheus_exporter.py:69-78`. `mcp_rate_limit_sleeps_total = Counter("mcp_rate_limit_sleeps_total", "Total sleep events due to rate-limit backoff.")` — no labels. `mcp_artifact_errors_by_class_total = Counter("mcp_artifact_errors_by_class_total", "Artifact errors grouped by error class.", ["error_class"])` — one label.

### SL-5 — Safe defaults flip

- **Scope**: Flip `MCP_PLUGIN_SANDBOX_ENABLED` default to on. Honor `MCP_PLUGIN_SANDBOX_DISABLE=1` as opt-out. Append `probe_gh_attestation_support()` at EOF of `attestation.py`. Call the probe at boot (register in `stdio_runner._serve()` startup — this is the only SL-5 gateway-adjacent touch; single line). Extend `docs/security/sandbox.md` with migration guide.
- **Owned files**:
  - `mcp_server/plugins/plugin_factory.py` — lines 260–262 only (swap the `== "1"` default check for `!= "1"` on `MCP_PLUGIN_SANDBOX_DISABLE`)
  - `mcp_server/artifacts/attestation.py` — **EOF append only** (after line 103; disjoint from SL-2's 44–76 preflight range)
  - `mcp_server/cli/stdio_runner.py` — **one-line call** to `probe_gh_attestation_support()` in `_serve()` startup banner area (after `logger.info("=" * 60)` at line 232; disjoint from SL-6's `initialize_services()` extraction — SL-6 owns the `_serve()` body hoist but not the startup-banner lines)
  - `tests/test_sandbox_default_on.py` (NEW)
  - `tests/test_attestation_probe.py` (NEW)
- **Interfaces provided**: `probe_gh_attestation_support() -> bool` for future ops use.
- **Interfaces consumed**: existing `subprocess` / `gh` patterns.
- **Parallel-safe**: yes. `attestation.py` disjoint-by-function-block from SL-2. `stdio_runner.py` one-line add disjoint from SL-6's `initialize_services()` hoist.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-5.1 | test | — | `tests/test_sandbox_default_on.py`, `tests/test_attestation_probe.py` | default sandbox enabled; `MCP_PLUGIN_SANDBOX_DISABLE=1` → off; probe returns True when `gh attestation --help` exits 0 and False otherwise; boot-time WARN emitted when probe fails + `MCP_ATTESTATION_MODE=enforce` | `pytest -q tests/test_sandbox_default_on.py tests/test_attestation_probe.py` |
| SL-5.2 | impl | SL-5.1 | `mcp_server/plugins/plugin_factory.py` | sandbox default flip | `pytest -q tests/test_sandbox_default_on.py` |
| SL-5.3 | impl | SL-5.1 | `mcp_server/artifacts/attestation.py` (EOF append), `mcp_server/cli/stdio_runner.py` (one-line probe call) | `probe_gh_attestation_support` + startup wiring | `pytest -q tests/test_attestation_probe.py` |
| SL-5.4 | verify | SL-5.2, SL-5.3 | lane-owned | all SL-5 tests + existing plugin-sandbox regression | `pytest -q tests/test_sandbox_default_on.py tests/test_attestation_probe.py tests/security/test_plugin_sandbox.py tests/test_plugin_sandbox.py` |

**SL-5 impl notes**:
- Flip: `use_sandbox = capabilities is not None or os.environ.get("MCP_PLUGIN_SANDBOX_DISABLE") != "1"` (previously: `== "1"` on `_ENABLED`). Preserves capability-override semantics. Document the env-var name switch in CHANGELOG (SL-docs).
- `probe_gh_attestation_support`: `subprocess.run(["gh", "attestation", "--help"], capture_output=True, timeout=5)`; returns `True` on exit=0. Cached at module level (probe once per process).
- Boot wiring: one `logger.warning("ATTESTATION_PREREQ: gh attestation subcommand unavailable; attestation will degrade per MCP_ATTESTATION_MODE")` if probe=False and `MCP_ATTESTATION_MODE=="enforce"`.

### SL-6 — P17 straggler burn-down

- **Scope**: Extract `initialize_services()` and the `call_tool` handler body from closures inside `stdio_runner._serve()` to module-level top-level async functions. Hoist the 7 runtime-state variables to module-level globals. Resolve the 17 failing `test_mcp_server_cli.py` cases and the 2 `test_benchmarks.py` SLO cases. Remove the P17 residual snapshot from `known-test-debt.md`.
- **Owned files**:
  - `mcp_server/cli/stdio_runner.py` — extract `initialize_services()` from `_serve()`'s `lazy_initialize()` closure (current `_serve():304-~420`); extract `call_tool()` from `_serve():430-~595`; hoist state globals; hoist 6 imports (`EnhancedDispatcher`, `PluginManager`, `SQLiteStore`, `IndexDiscovery`, `FileWatcher`, `validate_index`) from function-local at `_serve():211-218` to module top; `_serve()` becomes a thin orchestrator that calls `initialize_services()` and registers `call_tool` with the MCP server. **SL-5 owns the startup-banner line 232 probe call — do not overwrite.**
  - `tests/test_mcp_server_cli.py` — may need minor fixup if real API drifts from test expectations
  - `tests/test_benchmarks.py` — retune or fix the 2 SLO-failing tests
  - `mcp_server/benchmarks/benchmark_suite.py` — **only if** the benchmark root cause is production-side (flagged at impl time)
  - `mcp_server/plugins/**/plugin.py` — **only if** the benchmark root cause is a missing `self._sqlite_store =` on a specific plugin subclass (flagged at impl time; if touched, follow the `9d79870` / `cdc299d` precedent)
  - `docs/operations/known-test-debt.md` — remove the P17 residual snapshot section (the SL-docs lane owns the rest of this file's docs-catalog maintenance; SL-6's single edit is the snapshot deletion)
- **Interfaces provided**: IF-0-P18-3.
- **Interfaces consumed**: (none — purely additive API surface on `stdio_runner`).
- **Parallel-safe**: yes. `stdio_runner.py` is not edited by any other P18 lane (SL-5's one-line probe call at line 232 is in the startup banner, disjoint from SL-6's body-extraction work — line-range discipline: SL-6 reserves lines 206–597 excluding 232).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-6.1 | test | — | `tests/test_mcp_server_cli.py` (unchanged; already targets the surface being restored); `tests/test_benchmarks.py::test_benchmark_symbol_lookup_performance` and `::test_benchmark_search_performance` (investigate + minimal fix) | 17 CLI tests pass; 2 benchmark tests pass at realistic speeds | `pytest -q tests/test_mcp_server_cli.py tests/test_benchmarks.py::test_benchmark_symbol_lookup_performance tests/test_benchmarks.py::test_benchmark_search_performance --no-cov` |
| SL-6.2 | impl | SL-6.1 | `mcp_server/cli/stdio_runner.py` | extract `initialize_services()` + `call_tool`; hoist globals + 6 imports | `pytest -q tests/test_mcp_server_cli.py --no-cov` |
| SL-6.3 | impl | SL-6.1 | benchmark-fix file(s) — decided at impl time | 2 benchmark tests | `pytest -q tests/test_benchmarks.py::test_benchmark_symbol_lookup_performance tests/test_benchmarks.py::test_benchmark_search_performance --no-cov` |
| SL-6.4 | docs | SL-6.2, SL-6.3 | `docs/operations/known-test-debt.md` | remove P17 residual snapshot | `grep -q "P17 residual snapshot" docs/operations/known-test-debt.md && exit 1 || exit 0` |
| SL-6.5 | verify | SL-6.4 | lane-owned + full suite | ledger clean + failure count ≤5 | `pytest -q --no-cov --ignore=tests/real_world 2>&1 \| tail -3 \| grep -E "[0-4] failed"` |

**SL-6 impl notes**:
- `initialize_services()` body is a straight copy of `lazy_initialize()` from `_serve()`, with `nonlocal` → module-level `global` and the pre-existing `store_registry, repo_resolver, dispatcher, repo_registry, git_index_manager = initialize_stateless_services(...)` call from `_serve():234-237` moved inside. `_serve()` replaces its current body with: `await initialize_services()`, `server.call_tool()(call_tool)`, register signal handlers, `await stdio_server(...)` loop.
- The 6 imports hoist from `_serve():211-218` to module top. This makes `patch.object(stdio_runner, "IndexDiscovery", ...)` work as the tests expect.
- `call_tool(name, arguments)` body is the current closure body — reads module-level globals (dispatcher, sqlite_store, initialization_error) via `global` declaration. `_serve()` registers it via `server.call_tool()(call_tool)` — the decorator is a function, so applying it imperatively is equivalent to the `@` syntax.
- Benchmark investigation path: (a) Run `pytest -q --no-cov tests/test_benchmarks.py::test_benchmark_symbol_lookup_performance -s 2>&1 | grep -iE "plugin|sqlite_store"` to confirm whether `_sqlite_store` attr errors reappear. (b) Read `tests/test_benchmarks.py::mock_plugins` fixture; check whether it truly mocks or loads real plugins via `PluginFactory`. (c) If mock is broken, fix fixture (test-only change). (d) If a plugin subclass is missing `self._sqlite_store = sqlite_store`, fix the plugin (production change, follow precedent). Do not simply raise SLO bounds — that hides real regressions.
- Ledger deletion: delete the `## P17 residual snapshot` section in `docs/operations/known-test-debt.md` only if SL-6.5 confirms failure count ≤5. If residuals remain, update the snapshot to reflect the new state instead.

### SL-docs — Documentation & spec reconciliation

- **Scope**: Refresh the docs catalog, create the new operator-facing docs the spec assigns, update cross-cutting docs touched by P18 impl lanes, append post-execution amendments to this spec phase if any freeze was empirically wrong.
- **Owned files** (read `.claude/docs-catalog.json` for the authoritative list; minimum set below):
  - `docs/configuration/environment-variables.md` (NEW — full `MCP_*` env reference including new P18 vars: `MCP_PLUGIN_SANDBOX_DISABLE`, `MCP_ARTIFACT_RETENTION_DAYS`, `MCP_ARTIFACT_RETENTION_COUNT`, `MCP_LOG_FORMAT`; existing: `MCP_ENVIRONMENT`, `MCP_PLUGIN_SANDBOX_ENABLED`, `MCP_ATTESTATION_MODE`, `MCP_MAX_FILE_SIZE_BYTES`, `MCP_METRICS_PORT`, …)
  - `docs/operations/gateway-startup-checklist.md` (NEW — operator deploy checklist incl. SL-1 validation exit modes)
  - `docs/operations/artifact-retention.md` (NEW — operator janitor guide w/ `--dry-run` recipes)
  - `docs/security/sandbox.md` (extend — opt-out path via `MCP_PLUGIN_SANDBOX_DISABLE=1`; the default-on migration guide)
  - `README.md` (brief P18 section if present; else no-op)
  - `CHANGELOG.md` — new `Unreleased` → `P18` entry: sandbox default flip (behavioural change), JSON logs, retention CLI, new counters
  - `specs/phase-plans-v1.md` — append `### Post-execution amendments` subsection to the P18 section if any freeze (IF-0-P18-*) differed from what shipped; the `cli/commands.py` → `cli/retention_commands.py` rename is already a Context-noted correction but should also appear as a spec amendment
  - `.claude/docs-catalog.json` (this lane maintains it)
- **Interfaces provided**: (none)
- **Interfaces consumed**: (none)
- **Parallel-safe**: no (terminal)
- **Depends on**: SL-1, SL-2, SL-3, SL-4, SL-5, SL-6

**Tasks**:

| Task ID | Type | Depends on | Files in scope | Action |
|---|---|---|---|---|
| SL-docs.1 | docs | — | `.claude/docs-catalog.json` | Rescan catalog: `python3 "$(git rev-parse --show-toplevel)/.claude/skills/_shared/scaffold_docs_catalog.py" --rescan` (if present; else manual). Picks up any new doc files created by impl lanes. |
| SL-docs.2 | docs | SL-docs.1 | per catalog + the NEW doc files above | Write/extend each doc per spec. Append P18 alias to `touched_by_phases` for updated files. |
| SL-docs.3 | docs | SL-docs.2 | `specs/phase-plans-v1.md` | Append amendments: (a) `cli/commands.py` (spec) → `cli/retention_commands.py` (actual). (b) Any IF-0-P18-* rename / signature drift noted during execute-phase. |
| SL-docs.4 | verify | SL-docs.3 | — | `grep -q "MCP_PLUGIN_SANDBOX_DISABLE" docs/configuration/environment-variables.md && grep -q "retention prune" docs/operations/artifact-retention.md`. Run any repo doc linters. |

## Execution Notes

- **Graph endpoints auth decision**: `/graph/context` (gateway.py:2381) and `/graph/search` (gateway.py:2443) are not in the spec's explicit whitelist (`/health*`, `/ready`, `/liveness`, auth endpoints). The phase objective is "enforced by default." SL-1 **adds** `Depends(require_permission(Permission.READ))` to both. If a stakeholder later determines they must be public, revert in a separate PR — but the phase-level default is enforcement.
- **CLI file path correction (spec vs. reality)**: spec says `cli/commands.py`; actual file is `cli/__main__.py` as the click entry, with per-concern files (`artifact_commands.py` etc.). SL-3 adds `cli/retention_commands.py` + one registration line in `__main__.py`. Recorded as a post-execution spec amendment by SL-docs.
- **P17 straggler scope**: 17 `test_mcp_server_cli.py` tests split 11/6 by patch target. Both sub-clusters solvable by SL-6's `initialize_services()` + `call_tool` module-level hoist. 2 `test_benchmarks.py` SLO cases may be a fixture bug (real plugin loading despite `mock_plugins` fixture name). Investigation-first impl per SL-6.3; do not paper over with SLO retuning.
- **Single-writer files within phase**:
  - `mcp_server/gateway.py`: SL-1 owns lines 341–343 (validation insert) + 1472 (`/search/capabilities` decorator) + 2381 (`/graph/context`) + 2443 (`/graph/search`). SL-4 owns lines 378–387 (middleware registration inside `SecurityMiddlewareStack.setup_middleware()` flow). Disjoint line ranges; top-of-file imports merged alphabetically at lane merge time (P14/P15 pattern).
  - `mcp_server/artifacts/providers/github_actions.py`: SL-2 owns inline edits in existing functions (lines 14–22 `_respect_rate_limit` + inline raise-site conversions). SL-3 owns EOF append of `delete_releases_older_than` (post-line 115). Disjoint.
  - `mcp_server/artifacts/attestation.py`: SL-2 owns preflight block around `attest()` at lines 44–76. SL-5 owns EOF append of `probe_gh_attestation_support` (post-line 103). Disjoint function blocks.
  - `mcp_server/cli/stdio_runner.py`: SL-6 owns the `_serve()` body extraction (lines 206–597 excluding 232). SL-5 owns the one-line probe call at line 232 (startup banner area). Disjoint.
  - `mcp_server/cli/__main__.py`: SL-3 owns a single `_cli.add_command(retention)` line addition.
  - `docs/operations/known-test-debt.md`: SL-6 owns the P17-snapshot deletion; SL-docs owns the rest of the file (catalog-driven updates).
- **Known destructive changes**: `docs/operations/known-test-debt.md` — the P17 residual snapshot section gets deleted by SL-6.4 **only if** failure count ≤5 after SL-6.2/SL-6.3. Pre-authorized.
- **Expected add/add conflicts**: none. Every new file is solely owned by one lane. Every existing file has disjoint line ranges as enumerated above.
- **SL-0 re-exports**: no SL-0 preamble phase. Lanes dispatch directly against the P17-merged base.
- **Worktree naming**: `execute-phase` allocates unique names; plan doc does not spell them out.
- **Stale-base guidance** (verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-P17-merge or pre-SL-2-merge (for SL-3/SL-5 which depend on SL-2's line-range commits in `github_actions.py` and `attestation.py`), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.
- **Merge order for wave-2**: SL-2 must merge before SL-3 and before SL-5 because SL-3 appends after SL-2's tail-of-file region in `github_actions.py` and SL-5 appends after SL-2's function block in `attestation.py`. Orchestrator dispatches SL-3/SL-5 worktrees rebased on the post-SL-2 tip.
- **Rationale (post-P2B module-level state)**: SL-6 hoists `stdio_runner` state to module level. This is compatible with P2B's architectural intent (file decomposition of the 1711-line CLI monolith); P2B did not mandate closure-based isolation. Recorded here so `execute-phase` does not interpret the change as a P2B rollback.

## Acceptance Criteria

- [ ] `pytest -q tests/security/test_route_auth_coverage.py --no-cov` passes: every `@app.{get,post,put,delete,patch}` route returns 401 without token unless in the closed whitelist (auth endpoints + `/health*` + `/ready` + `/liveness`). **Test file**: `tests/security/test_route_auth_coverage.py`.
- [ ] `MCP_ENVIRONMENT=production JWT_SECRET_KEY=weak python -m mcp_server.cli serve` exits non-zero with a `[FATAL]`-prefixed ValidationError listing on stderr. `MCP_ENVIRONMENT=dev JWT_SECRET_KEY=weak python -m mcp_server.cli serve` logs a WARN and continues. **Test file**: `tests/security/test_startup_config_validation.py`.
- [ ] Mid-publish kill scenario: stub `_move_latest_pointer` to raise → `_ensure_sha_release` output is cleaned up via `gh release delete`. **Test file**: `tests/test_artifact_publish_rollback.py`.
- [ ] `artifact_download` delta-base-missing → full-artifact fallback. **Test file**: `tests/test_delta_base_fallback.py`.
- [ ] `_respect_rate_limit` parses `Retry-After`, backs off on 429 (+ `mcp_rate_limit_sleeps_total.inc()`), raises `TerminalArtifactError` on 403. **Test file**: `tests/test_rate_limit_retry_after.py`.
- [ ] `MCP_PLUGIN_SANDBOX_ENABLED` default is on; `MCP_PLUGIN_SANDBOX_DISABLE=1` opts out; `tests/test_plugin_sandbox.py` + `tests/security/test_plugin_sandbox.py` pass. **Test file**: `tests/test_sandbox_default_on.py`.
- [ ] Production-mode log line parses as `json.loads(line)`. **Test file**: `tests/test_json_logs.py`.
- [ ] 4xx/5xx response body with `Bearer abc123`, `JWT_SECRET_KEY=xyz`, or `GITHUB_TOKEN=ghp_…` is rewritten to `[REDACTED]`. **Test file**: `tests/test_secret_redaction.py`.
- [ ] `python -m mcp_server.cli retention prune --repo foo/bar --dry-run --older-than-days 30` exits 0 and prints candidate releases without mutation. **Test file**: `tests/test_retention_janitor.py`.
- [ ] Boot with `MCP_ATTESTATION_MODE=enforce` + `gh attestation` unavailable → single `ATTESTATION_PREREQ` WARN emitted at startup; boot continues. **Test file**: `tests/test_attestation_probe.py`.
- [ ] New counters `mcp_rate_limit_sleeps_total` and `mcp_artifact_errors_by_class_total` registered and scrapeable on `/metrics`. **Test file**: `tests/test_json_logs.py` (covers) or a single-purpose smoke in `tests/test_prometheus_exporter_http.py`.
- [ ] **P17 straggler burn-down**: `pytest -q --no-cov --ignore=tests/real_world 2>&1 | tail -3` shows ≤5 failures (down from 19). `grep -q "P17 residual snapshot" docs/operations/known-test-debt.md` returns non-zero (snapshot section removed). **Test files**: `tests/test_mcp_server_cli.py`, `tests/test_benchmarks.py`.
- [ ] **Route auth coverage regression-free**: existing `tests/security/` suite green.
- [ ] **Ruff F401 gate clean**: `ruff check --select F401 mcp_server/dispatcher mcp_server/storage mcp_server/watcher mcp_server/artifacts mcp_server/security mcp_server/cli` → 0 errors.

## Verification

```bash
# SL-1 — route auth coverage + startup validation
pytest -q tests/security/test_route_auth_coverage.py tests/security/test_startup_config_validation.py --no-cov
MCP_ENVIRONMENT=production JWT_SECRET_KEY=weak python -m mcp_server.cli serve 2>&1 | grep -E "\[FATAL\].*JWT" && echo OK

# SL-2 — artifact resilience
pytest -q tests/test_artifact_publish_rollback.py tests/test_delta_base_fallback.py tests/test_rate_limit_retry_after.py --no-cov
pytest -q tests/test_artifact_attestation.py tests/test_artifact_publish_race.py tests/test_artifact_freshness.py --no-cov   # regression

# SL-3 — retention CLI round-trip
pytest -q tests/test_retention_janitor.py --no-cov
python -m mcp_server.cli retention prune --repo foo/bar --dry-run --older-than-days 30

# SL-4 — observability
pytest -q tests/test_json_logs.py tests/test_secret_redaction.py --no-cov
MCP_ENVIRONMENT=production python -m mcp_server.cli serve & SERVER_PID=$!
sleep 2
curl -s localhost:9090/metrics | grep -E 'mcp_rate_limit_sleeps_total|mcp_artifact_errors_by_class_total'
kill $SERVER_PID

# SL-5 — safe defaults flip
pytest -q tests/test_sandbox_default_on.py tests/test_attestation_probe.py --no-cov
pytest -q tests/test_plugin_sandbox.py tests/security/test_plugin_sandbox.py --no-cov  # regression

# SL-6 — P17 straggler resolved
pytest -q tests/test_mcp_server_cli.py tests/test_benchmarks.py --no-cov
grep -q "P17 residual snapshot" docs/operations/known-test-debt.md && echo "FAIL: ledger still has P17 snapshot" || echo "OK: ledger clean"

# Full-suite regression gate — residuals must be ≤5 (down from 19 post-SL-4b)
pytest -q --no-cov --ignore=tests/real_world 2>&1 | tail -3

# Ruff F401 gate
ruff check --select F401 mcp_server/dispatcher mcp_server/storage mcp_server/watcher mcp_server/artifacts mcp_server/security mcp_server/cli
```

All commands above must pass. Any failure — an unauth'd route returning 200, weak-JWT accepted under `MCP_ENVIRONMENT=production`, orphaned GitHub release after mid-publish kill, production logs emitting plaintext, secrets leaked in 4xx/5xx response bodies, P17 straggler count staying above 5 — fails the P18 gate and blocks `execute-phase p18` from declaring the phase done.
