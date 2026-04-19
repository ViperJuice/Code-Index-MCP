# P15: Security Hardening

## Context

P14 merged (tip `936eef0`): semantic reranker wiring, dependency-graph search, schema-migrator, auto-delta, watcher-sweeper + rename atomicity. P15 is the final hardening phase and enforces trust boundaries: sandbox plugins so malicious code cannot reach the host SQLite DB, network, or arbitrary FS; require auth on `/metrics`; sign all published artifacts via `gh attestation` and verify on download; guard path traversal in search output; validate `GITHUB_TOKEN` scopes fail-loud at startup; rate-limit cross-repo artifact pulls on `X-RateLimit-Remaining`.

What exists today (reconnaissance, verified by Explore teammates + direct reads):

- **Plugin surface (SL-1):**
  - `mcp_server/plugin_base.py:83-115` defines `IPlugin` ABC: `supports(path)`, `indexFile(path, content) -> IndexShard`, `getDefinition(symbol) -> SymbolDef | None`, `findReferences(symbol) -> Iterable[Reference]`, `search(query, opts) -> Iterable[SearchResult]`, plus `bind(ctx: RepoContext)` and `language` property. **All return types are picklable/JSON-safe** (TypedDicts of primitives + immutable `Reference` class with `__slots__`).
  - `mcp_server/plugins/plugin_factory.py:197-256` — `PluginFactory.create_plugin(language, sqlite_store, enable_semantic, ctx)` lazy-imports a per-language plugin, post-construction calls `plugin.bind(ctx)` iff `ctx` was passed.
  - Dispatcher call sites that must route through the sandbox adapter: `mcp_server/dispatcher/dispatcher_enhanced.py:1434, 1541, 1676, 1794`; `mcp_server/dispatcher/fallback.py:51` (already wraps `plugin.getDefinition` in a per-call ThreadPoolExecutor with timeout).
  - Existing plugins hold SQLite handles at construction time (python_plugin, js_plugin, go_plugin); Go plugin imports `subprocess` at module load. **Sandboxing means these constructions happen in the worker process, not the host.**
  - `mcp_server/setup/qdrant_autostart.py` is the closest existing subprocess-launch pattern; **no JSON-line IPC exists anywhere in the repo yet**.
  - `tests/conftest.py:62-80` provides `_MockPlugin`; `tests/test_plugin_factory_async.py` provides `_SlowPlugin`. `tests/security/` contains only `test_symlink_escape.py` today — no `test_plugin_sandbox.py`, no malicious-plugin fixture.
- **Auth & metrics (SL-2):**
  - `mcp_server/gateway.py:2538` — FastAPI app; uses `Depends(require_permission(Permission.READ))` pattern (e.g. `/symbol` at `:1188`, `/search` at `:1245`).
  - `mcp_server/security/security_middleware.py:109-172` — `AuthenticationMiddleware` with `excluded_paths` list at `:120-129` that **explicitly excludes `/metrics`** — this is the SL-2 bug.
  - `gateway.py:1117` and `gateway.py:1127` both decorate `/metrics`. Verified behavior: FastAPI registers both but the second wins in route resolution. SL-2 deletes the first and attaches `require_auth("metrics")` to the second.
  - `require_permission(Permission)` is defined at `security_middleware.py:404-415`; `require_role(UserRole)` at `:418-442`. `Permission` enum in `mcp_server/security/models.py`.
- **Path guard / token / rate-limit (SL-4):**
  - `mcp_server/security/path_allowlist.py` (24 LOC) already defines `resolve_allowed_roots(tuple[str, ...]) -> tuple[Path, ...]` and `path_within_allowed(candidate: Path, roots)`. **Zero callers in `gateway.py`** — output paths are unguarded today.
  - `gateway.py:104-200` — `_normalize_search_result(raw_result)` is the single output-serialization choke point for search; called at `:1312, :1330, :1338, :1347, :1404, :1409`. SL-4's `PathTraversalGuard` mounts here.
  - `GITHUB_TOKEN` consumed at `mcp_server/artifacts/artifact_download.py:49` and `artifact_upload.py:33` via `os.environ.get`; **no scope validation** anywhere. `TokenValidator` is new.
  - Startup sequence: `gateway.py:270-410`. `run_startup_preflight()` at `:278` → `SecurityConfig` at `:286-306` → `AuthManager` at `:309-337` → `SecurityMiddlewareStack` at `:341-349`. SL-4 inserts `TokenValidator.validate_scopes()` after AuthManager (around `:337`) and before the cache initialization block.
  - `mcp_server/artifacts/providers/github_actions.py:19-87` — four `gh api` subprocess calls, none read `X-RateLimit-Remaining`. Neither do `publisher.py`, `artifact_upload.py`, `artifact_download.py`. Rate-limit awareness is missing entirely.
- **Artifact attestation (SL-3):**
  - `mcp_server/artifacts/publisher.py:42-88` — `ArtifactPublisher.publish_on_reindex(repo_id, commit) -> ArtifactRef`. Calls `self._uploader.compress_indexes(...)` at `:56`, `self._uploader.create_metadata(...)` at `:64`, then creates the SHA-keyed release via `_ensure_sha_release`/`_move_latest_pointer`. Uses `gh_cmd: str = "gh"` ctor arg for test injection. Wraps `gh` subprocess failures in `ArtifactError(MCPError)`.
  - `mcp_server/artifacts/artifact_upload.py:100-142` — `create_metadata()` returns the metadata dict (`checksum`, `version`, `commit`, `branch`, `artifact_type`, `base_commit`, `target_commit`, `compressed_size`, `index_stats`, `compatibility`, `security`). SL-3 extends the return with `attestation_url: str | None` and the new sidecar path.
  - `mcp_server/artifacts/artifact_download.py:145` is the download integrity checkpoint (`validate_artifact_integrity(...)`), directly followed by `tarfile.open(archive_path, "r:gz")` at `:154` and `tar.extractall(...)` at `:159`. SL-3 inserts `verify_attestation(archive_path, attestation)` between `:145` and `:154`.
  - `tests/test_artifact_publish_race.py:26-42` — post-P14 commit `936eef0` fixture that stubs `uploader.compress_indexes` and `uploader.create_metadata` via `MagicMock`, and stubs the publisher's `gh` `subprocess.run` via `mock_run.side_effect`. SL-3 extends this pattern with an attestation stub.
  - `docs/operations/user-action-runbook.md:84-94` documents P15 prerequisites: enable SLSA artifact attestations in GitHub Settings, extend `GITHUB_TOKEN` scope to include `attestations:write`, pick plugin-trust posture (default: posture 3, fully sandboxed).

What constrains the design:

- **`gateway.py` is a single-writer file touched by SL-2 and SL-4.** Line-range ownership is disjoint. SL-2 owns `:1117` (delete) and `:1127` (add `require_auth` dependency). SL-4 owns `:104` (PathTraversalGuard injection into `_normalize_search_result`) and `:337` area (TokenValidator startup call). Top-of-file imports are a known add/add conflict surface — resolution noted in Execution Notes.
- **`security_middleware.py` is touched by SL-0 and SL-2.** SL-0 adds `require_auth` stub; SL-2 fills the body and removes `/metrics` from the exclusion list. Execution Notes pre-authorize `git checkout --theirs security_middleware.py` at merge time (SL-0's stub is replaced by SL-2's full body).
- **`artifact_upload.py::create_metadata` is touched only by SL-3.** `publisher.py::publish_on_reindex` is touched only by SL-3.
- **Plugin interface surface is frozen.** SL-1 MUST NOT change `IPlugin` ABC at `plugin_base.py:83-115` — the dispatcher and every concrete plugin depends on it unchanged. `SandboxedPlugin` is a new class that implements `IPlugin` and wraps a subprocess worker.
- **`PluginFactory.create_plugin` wrapping strategy.** Default behavior in P15: `PluginFactory` produces a `SandboxedPlugin` iff `MCP_PLUGIN_SANDBOX_ENABLED=1` (or `capabilities` is explicitly passed). Default-off during P15 so existing test fixtures and local dev keep working. Runbook will document flipping it on for prod. P16 (or a follow-up PR) flips the default.
- **`TokenValidator.validate_scopes()` gating.** Strict fail-loud only when `GITHUB_TOKEN` is set. If the env var is unset, log one WARN and skip validation (dev/test). If `MCP_REQUIRE_TOKEN_SCOPES=1` is set, the check is mandatory regardless. This avoids breaking existing test suites and keeps the spec's "fails-loud" guarantee for production.
- **`MCP_ATTESTATION_MODE` env var.** Three modes: `enforce` (default) raises on verify failure, `warn` logs and continues, `skip` bypasses attest + verify entirely (air-gap). Runbook documents.
- **SL-1 transport choice (consensus):** subprocess + JSON-line IPC over stdin/stdout. All three Plan teammates converged on this. WASI rejected (requires recompiling all tree-sitter/SQLite native deps + Go plugin's subprocess use). Subinterpreters rejected (share FS/net surface; fails "no arbitrary FS access" exit criterion).

What this phase does NOT change:

- No plugin signing (explicit Non-goal: sandbox replaces signing).
- No TLS termination inside the app (ingress/sidecar concern).
- No secrets management beyond `GITHUB_TOKEN` validation.
- No changes to `IPlugin` ABC, `IndexShard`, `SymbolDef`, `SearchResult`, `Reference`.
- No removal of `path_allowlist.py` (arch-clean recommended deletion; majority kept it — `PathTraversalGuard` uses it internally).
- No deprecation of `require_permission` (arch-clean recommended; majority kept it — `require_auth` wraps it as a new primitive).
- Does NOT address the P14-handoff debt items (18 pre-existing `test_cross_repo_coordinator.py` failures, 9 `ruff F401` warnings, `RerankerFactory.create_default()` realization). If a lane touches those files incidentally, the lane must leave them alone.

## Interface Freeze Gates

- [ ] **IF-0-P15-0** — SL-0 preamble: frozen stub surfaces for every downstream IF. Landing this lane unblocks SL-1/SL-2/SL-3/SL-4 in parallel.
- [ ] **IF-0-P15-1** — Plugin sandbox IPC protocol + `SandboxedPlugin` adapter:
  - `mcp_server/sandbox/protocol.py` — `Envelope` Pydantic model `{v: Literal[1], id: str, kind: Literal["call","result","error","log"], method: str, payload: dict}`, JSON-line over stdin/stdout, newline-delimited, 16 MiB max line, 30 s per-call timeout.
  - `mcp_server/sandbox/capabilities.py` — `CapabilitySet` frozen dataclass: `fs_read: tuple[Path, ...]`, `fs_write: tuple[Path, ...]`, `env_allow: frozenset[str]`, `network: bool = False`, `sqlite: Literal["none","readonly"] = "none"`, `cpu_seconds: int = 30`, `mem_mb: int = 512`.
  - `mcp_server/plugins/sandboxed_plugin.py` — `class SandboxedPlugin(IPlugin)` with `__init__(self, plugin_module: str, capabilities: CapabilitySet, *, gh_cmd: str = "python")`; forwards every `IPlugin` method over IPC. `bind(ctx)` sends a `BoundContext` DTO (`root_path: str`, `repo_id: str`, `enable_semantic: bool`) — `RepoContext` itself does not cross the boundary.
  - `mcp_server/sandbox/supervisor.py` — `class SandboxSupervisor` that spawns/manages the worker subprocess; public methods `call(method: str, payload: dict, *, timeout: float = 30.0) -> dict` and `close() -> None`.
  - `mcp_server/sandbox/worker_main.py` — `python -m mcp_server.sandbox.worker_main <plugin_module> <caps_json>` entry point; applies `CapabilitySet` (closes non-allowed FDs, chdir to tmpdir, monkey-patches socket when `network=False`, scrubs env).
- [ ] **IF-0-P15-2** — `require_auth(scope: Literal["metrics","admin","tools"]) -> Callable[..., User]` FastAPI dependency. Implemented as a thin wrapper that maps each scope to an existing `Permission` and delegates to `require_permission`. Scope→Permission mapping lives at top of `security_middleware.py`: `"metrics" → Permission.ADMIN`, `"admin" → Permission.ADMIN`, `"tools" → Permission.READ`.
- [ ] **IF-0-P15-3** — `Attestation` + `attest` + `verify_attestation`:
  - `mcp_server/artifacts/attestation.py` — `@dataclass(frozen=True) Attestation(bundle_url: str, bundle_path: Path, subject_digest: str, signed_at: datetime)`.
  - `attest(artifact_path: Path, *, repo: str, gh_cmd: str = "gh") -> Attestation` — shells `gh attestation sign`, writes sidecar `<artifact_path>.attestation.jsonl`, returns `Attestation`. Raises `AttestationError(ArtifactError)` on non-zero exit when `MCP_ATTESTATION_MODE=enforce`.
  - `verify_attestation(archive_path: Path, attestation: Attestation, *, expected_repo: str, gh_cmd: str = "gh") -> None` — shells `gh attestation verify --bundle <path> --repo <repo>`; raises `AttestationError` on non-zero exit when mode is `enforce`, logs WARN and returns when mode is `warn`, no-ops when mode is `skip`.
- [ ] **IF-0-P15-4** — Path guard + token validator + rate-limit:
  - `mcp_server/security/path_guard.py` — `class PathTraversalGuard` with `__init__(self, allowed_roots: Sequence[Path])` and `normalize_and_check(self, p: str | Path) -> Path` (raises `PathTraversalError` on escape). Internally calls `path_allowlist.path_within_allowed`.
  - `mcp_server/security/token_validator.py` — `class TokenValidator` with classmethod `validate_scopes(required: Iterable[str], *, token: str | None = None) -> None`. Calls `https://api.github.com/user` with the token, reads the `X-OAuth-Scopes` response header, raises `InsufficientScopesError(MCPError)` on missing scopes.
  - `mcp_server/artifacts/providers/github_actions.py` — new helper `_respect_rate_limit(headers: Mapping[str, str]) -> float` returns sleep seconds when `X-RateLimit-Remaining < 100` (exponential from `X-RateLimit-Reset`); integrated after each `gh api` subprocess return.

## Lane Index & Dependencies

SL-0 — preamble: interface-freeze stubs
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3, SL-4
  Parallel-safe: yes

SL-1 — plugin sandbox (IPC + supervisor + SandboxedPlugin + malicious fixture)
  Depends on: SL-0
  Blocks: SL-docs
  Parallel-safe: yes

SL-2 — metrics auth (require_auth + exclusion removal + duplicate decorator cleanup)
  Depends on: SL-0
  Blocks: SL-docs
  Parallel-safe: yes (disjoint gateway.py line ranges with SL-4)

SL-3 — artifact attestation (attest + verify + publisher + download integration)
  Depends on: SL-0
  Blocks: SL-docs
  Parallel-safe: yes

SL-4 — path guard + token validator + rate-limit
  Depends on: SL-0
  Blocks: SL-docs
  Parallel-safe: yes (disjoint gateway.py line ranges with SL-2)

SL-docs — documentation & spec reconciliation
  Depends on: SL-0, SL-1, SL-2, SL-3, SL-4
  Blocks: (none)
  Parallel-safe: no (terminal)

## Lanes

### SL-0 — Preamble: interface-freeze stubs

- **Scope**: Land the module-level type surface for every downstream lane to import from. Stubs only — every function body raises `NotImplementedError("filled by SL-<N>")` and every type is fully annotated. Uses the lazy `__getattr__` re-export pattern for `__init__.py` files to avoid eager-import failure when a sibling lane later renames a symbol.
- **Owned files**:
  - `mcp_server/sandbox/__init__.py` (new; lazy `__getattr__`)
  - `mcp_server/sandbox/protocol.py` (new; `Envelope` Pydantic model)
  - `mcp_server/sandbox/capabilities.py` (new; `CapabilitySet` frozen dataclass)
  - `mcp_server/sandbox/supervisor.py` (new; `SandboxSupervisor` stub)
  - `mcp_server/sandbox/worker_main.py` (new; module-level main stub)
  - `mcp_server/plugins/sandboxed_plugin.py` (new; `SandboxedPlugin(IPlugin)` stub with all method signatures)
  - `mcp_server/artifacts/attestation.py` (new; `Attestation` dataclass + `attest` + `verify_attestation` stubs + `AttestationError`)
  - `mcp_server/security/path_guard.py` (new; `PathTraversalGuard` class stub + `PathTraversalError`)
  - `mcp_server/security/token_validator.py` (new; `TokenValidator` class stub + `InsufficientScopesError`)
  - `mcp_server/security/security_middleware.py` (edit: add `require_auth` stub function that raises `NotImplementedError`)
  - `tests/security/test_sl0_interface_surface.py` (new; pure import tests that each stub exists and every type resolves)
- **Interfaces provided**: every IF-0-P15-{1,2,3,4} surface listed above, in stub form.
- **Interfaces consumed**: `mcp_server.plugin_base.IPlugin` (unchanged), `mcp_server.security.security_middleware.require_permission` (unchanged), `mcp_server.security.path_allowlist.path_within_allowed` (unchanged), `mcp_server.core.errors.MCPError` (unchanged).

**Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-0.1 | test | — | `tests/security/test_sl0_interface_surface.py` | import-shape contract: every IF symbol is importable and has the correct signature | `pytest tests/security/test_sl0_interface_surface.py -v --no-cov` |
| SL-0.2 | impl | SL-0.1 | all files listed above | — | — |
| SL-0.3 | verify | SL-0.2 | all SL-0 files + every file that will later import from these stubs | all SL-0 tests + `pytest --collect-only` across the whole repo (proves nothing breaks) | `pytest tests/security/test_sl0_interface_surface.py -v --no-cov && pytest --collect-only -q` |

### SL-1 — Plugin sandbox

- **Scope**: Implement the subprocess-backed `SandboxedPlugin` adapter over JSON-line IPC, the worker bootstrap, the `CapabilitySet` enforcement mechanics, the supervisor lifecycle, and the malicious-plugin fixture + negative test that proves the boundary holds.
- **Owned files**:
  - `mcp_server/sandbox/protocol.py` (fill body)
  - `mcp_server/sandbox/capabilities.py` (fill body)
  - `mcp_server/sandbox/supervisor.py` (fill body)
  - `mcp_server/sandbox/worker_main.py` (fill body)
  - `mcp_server/sandbox/caps_apply.py` (new — applies `CapabilitySet` to a live subprocess: closes FDs, chdir, socket monkey-patch, env scrub)
  - `mcp_server/plugins/sandboxed_plugin.py` (fill body)
  - `mcp_server/plugins/plugin_factory.py` (edit: `PluginFactory.create_plugin(...)` checks `MCP_PLUGIN_SANDBOX_ENABLED=1` env or explicit `capabilities=` kwarg; when on, returns `SandboxedPlugin(...)`; when off, returns the direct plugin class as today. **Do not change the existing code path's behavior when the flag is unset.**)
  - `tests/security/test_plugin_sandbox.py` (new — unit tests for protocol, supervisor, adapter)
  - `tests/security/test_malicious_plugin.py` (new — integration test that spawns a sandboxed subprocess, runs the malicious plugin, asserts host is unharmed)
  - `tests/security/fixtures/malicious_plugin/__init__.py` (new — minimal package)
  - `tests/security/fixtures/malicious_plugin/plugin.py` (new — hostile `IPlugin` impl attempting `open("/etc/passwd")`, `socket.socket()`, `sqlite3.connect("/path/to/host.db")`, `os.environ["GITHUB_TOKEN"]`, `subprocess.run(["sh","-c","..."])`)
- **Interfaces provided**: IF-0-P15-1 (filled).
- **Interfaces consumed**: `mcp_server.plugin_base.IPlugin`, `mcp_server.plugins.plugin_factory.PluginFactory`, `mcp_server.sandbox.protocol.Envelope`, `mcp_server.sandbox.capabilities.CapabilitySet`.

**Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/security/test_plugin_sandbox.py`, `tests/security/test_malicious_plugin.py`, `tests/security/fixtures/malicious_plugin/**` | RED: (a) envelope round-trip; (b) supervisor spawns worker + closes on `close()`; (c) malicious plugin's `open("/etc/passwd")` raises `SandboxViolation` in worker, host process unaffected; (d) `indexFile` round-trip through sandbox returns equivalent `IndexShard` to an in-process call | `pytest tests/security/test_plugin_sandbox.py tests/security/test_malicious_plugin.py -v --no-cov` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/sandbox/protocol.py`, `capabilities.py`, `supervisor.py`, `worker_main.py`, `caps_apply.py` | — | — |
| SL-1.3 | impl | SL-1.2 | `mcp_server/plugins/sandboxed_plugin.py`, `mcp_server/plugins/plugin_factory.py` | — | — |
| SL-1.4 | verify | SL-1.3 | all SL-1 files | all SL-1 tests + smoke test of `plugin_factory.create_plugin("python", ..., capabilities=CapabilitySet(...))` returning a working `SandboxedPlugin` | `pytest tests/security/test_plugin_sandbox.py tests/security/test_malicious_plugin.py tests/test_plugin_factory_async.py -v --no-cov` |

### SL-2 — Metrics auth

- **Scope**: Introduce the `require_auth(scope)` FastAPI dependency, remove `/metrics` from `AuthenticationMiddleware.excluded_paths`, collapse the duplicate `/metrics` decorators in `gateway.py`, and wire `require_auth("metrics")` onto the surviving route.
- **Owned files**:
  - `mcp_server/security/security_middleware.py` (edit: fill SL-0's `require_auth` stub body, remove `/metrics` from `excluded_paths` list at `:120-129`; **do not touch** `/health*`, `/api/v1/auth/*` entries — they stay excluded)
  - `mcp_server/gateway.py` (edit: delete decorator + function at `:1117-1126`; add `dependencies=[Depends(require_auth("metrics"))]` on the `/metrics` route at `:1127`. **No other gateway.py edits in this lane.**)
  - `tests/security/test_metrics_auth.py` (new)
- **Interfaces provided**: IF-0-P15-2 (filled).
- **Interfaces consumed**: `mcp_server.security.security_middleware.require_permission`, `mcp_server.security.models.Permission`.

**Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/security/test_metrics_auth.py` | RED: (a) unauth'd `GET /metrics` returns 401; (b) bearer-auth'd admin `GET /metrics` returns 200 + Prometheus payload; (c) non-admin token returns 403; (d) unaffected routes (`/health`, `/search` with token) still work | `pytest tests/security/test_metrics_auth.py -v --no-cov` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/security/security_middleware.py`, `mcp_server/gateway.py` (lines `:120-129, :1117-1127` only) | — | — |
| SL-2.3 | verify | SL-2.2 | all SL-2 files + regression suite on gateway | all SL-2 tests + existing auth suite (`tests/test_security.py` if present) | `pytest tests/security/test_metrics_auth.py tests/ -k "auth or metrics" -v --no-cov` |

### SL-3 — Artifact attestation

- **Scope**: Implement `attest` + `verify_attestation` in `attestation.py`, wire `attest` into the publisher's post-compress pre-release step, wire `verify_attestation` into the downloader between integrity check and extract, extend the metadata dict with `attestation_url`, and update the publisher race test fixture to stub the new subprocess calls.
- **Owned files**:
  - `mcp_server/artifacts/attestation.py` (fill body from SL-0 stub)
  - `mcp_server/artifacts/publisher.py` (edit: insert `attest(archive_path, repo=self._uploader.repo)` between existing `compress_indexes` at `:56` and `create_metadata` at `:64`; pass resulting `Attestation` into `create_metadata` call)
  - `mcp_server/artifacts/artifact_upload.py` (edit: `create_metadata(...)` accepts a new optional kwarg `attestation: Attestation | None = None`; if provided, include `attestation_url` field in the returned dict at `:100-142`. Default `None` keeps existing callers green.)
  - `mcp_server/artifacts/artifact_download.py` (edit: at `:145-154`, after `validate_artifact_integrity` and before `tarfile.open`, call `verify_attestation(archive_path, attestation)` where `attestation` is reconstructed from the metadata's `attestation_url` + sidecar file. Respect `MCP_ATTESTATION_MODE`.)
  - `tests/security/test_artifact_attestation.py` (new — verify tampering a post-attest archive byte causes verify to raise under `enforce`, log WARN under `warn`, and succeed silently under `skip`)
  - `tests/test_artifact_publish_race.py` (edit: extend the `compress_indexes`/`create_metadata` MagicMock fixture at `:26-42` to also stub `attest` and include `attestation_url` in the metadata dict. **No test deletions.**)
- **Interfaces provided**: IF-0-P15-3 (filled).
- **Interfaces consumed**: `mcp_server.core.errors.MCPError` (parent of `AttestationError`), `subprocess` (for `gh` CLI calls), `mcp_server.artifacts.publisher.ArtifactPublisher._uploader` (accessor only).

**Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/security/test_artifact_attestation.py`, `tests/test_artifact_publish_race.py` (fixture extension) | RED: (a) `attest` on a known archive returns an `Attestation` with a sidecar path that exists; (b) `verify_attestation` on the same archive returns cleanly; (c) tampering a byte of the archive then re-verify raises `AttestationError` under `enforce`; (d) `MCP_ATTESTATION_MODE=warn` logs + continues; (e) `MCP_ATTESTATION_MODE=skip` no-ops; (f) `publish_on_reindex` end-to-end stubbed flow includes `attestation_url` in returned metadata | `pytest tests/security/test_artifact_attestation.py tests/test_artifact_publish_race.py -v --no-cov` |
| SL-3.2 | impl | SL-3.1 | `mcp_server/artifacts/attestation.py`, `mcp_server/artifacts/publisher.py` (lines `:56, :64` only), `mcp_server/artifacts/artifact_upload.py` (`create_metadata` at `:100-142` only), `mcp_server/artifacts/artifact_download.py` (lines `:145-154` only) | — | — |
| SL-3.3 | verify | SL-3.2 | all SL-3 files + P14 publisher tests | all SL-3 tests + existing artifact tests (`tests/test_artifact_publish*`, `tests/test_artifact_download*`, `tests/test_multi_repo_artifact_coordinator.py`) | `pytest tests/security/test_artifact_attestation.py tests/test_artifact_publish_race.py tests/test_artifact_publish.py tests/test_artifact_download.py tests/test_multi_repo_artifact_coordinator.py -v --no-cov` |

### SL-4 — Path guard + token validator + rate-limit

- **Scope**: Fill `PathTraversalGuard` and `TokenValidator` bodies, wire the guard into `gateway._normalize_search_result`, wire the validator into startup, add `X-RateLimit-Remaining` header-aware backoff to the four `gh api` subprocess callsites in `providers/github_actions.py`.
- **Owned files**:
  - `mcp_server/security/path_guard.py` (fill body from SL-0 stub)
  - `mcp_server/security/token_validator.py` (fill body from SL-0 stub)
  - `mcp_server/artifacts/providers/github_actions.py` (edit: add `_respect_rate_limit(headers)` helper; call after each `subprocess.run([gh_cmd, "api", ...])` return, parsing headers from `--include` added to the gh call)
  - `mcp_server/gateway.py` (edit: (a) in `_normalize_search_result` at `:104`, construct `PathTraversalGuard` once at module init from `MCP_ALLOWED_ROOTS` env var, call `guard.normalize_and_check(file_value)` on the extracted `file` field; drop the result by raising a caught `PathTraversalError` that maps to a 403. (b) in `startup_event` at `:271` area, after the AuthManager instantiation at `:337`, call `TokenValidator.validate_scopes(required=["contents:read","actions:read","actions:write","attestations:write"])`. **No other gateway.py edits in this lane.**)
  - `tests/security/test_path_traversal.py` (new)
  - `tests/security/test_token_scope.py` (new)
  - `tests/test_cross_repo_rate_limit.py` (new)
- **Interfaces provided**: IF-0-P15-4 (filled).
- **Interfaces consumed**: `mcp_server.security.path_allowlist.path_within_allowed` (unchanged — internal to guard), `mcp_server.core.errors.MCPError`.

**Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/security/test_path_traversal.py`, `tests/security/test_token_scope.py`, `tests/test_cross_repo_rate_limit.py` | RED: (a) `GET /search?q=foo` returning a raw `{"file": "../../../etc/passwd"}` hit gets 403 (or the hit is dropped and the test asserts it's missing from results); (b) `TokenValidator.validate_scopes(["attestations:write"])` raises `InsufficientScopesError` when `X-OAuth-Scopes` response header lacks it; (c) rate-limit simulation with `X-RateLimit-Remaining: 50` causes the next gh call to sleep; (d) `GITHUB_TOKEN` unset + `MCP_REQUIRE_TOKEN_SCOPES=0` → validator no-ops; (e) `MCP_REQUIRE_TOKEN_SCOPES=1` + `GITHUB_TOKEN` unset → raises | `pytest tests/security/test_path_traversal.py tests/security/test_token_scope.py tests/test_cross_repo_rate_limit.py -v --no-cov` |
| SL-4.2 | impl | SL-4.1 | `mcp_server/security/path_guard.py`, `mcp_server/security/token_validator.py`, `mcp_server/artifacts/providers/github_actions.py` | — | — |
| SL-4.3 | impl | SL-4.2 | `mcp_server/gateway.py` (lines `:104-200` normalize + `:337` area startup only) | — | — |
| SL-4.4 | verify | SL-4.3 | all SL-4 files + full gateway regression | all SL-4 tests + `tests/test_multi_repo_server*`, `tests/security/test_symlink_escape.py` | `pytest tests/security/ tests/test_cross_repo_rate_limit.py tests/test_multi_repo_server.py -v --no-cov` |

### SL-docs — Documentation & spec reconciliation

- **Scope**: Refresh the docs catalog, update cross-cutting documentation touched or invalidated by this phase's impl lanes, and append any post-execution amendments to phase specs whose interface freezes turned out wrong. See plan-phase SKILL `## Docs-sweep lane template` for rationale.
- **Owned files** (authoritative list is `.claude/docs-catalog.json` when it exists; minimum set below):
  - Root: `README.md`, `CHANGELOG.md`, `ARCHITECTURE.md`, `AGENTS.md`, `CLAUDE.md`
  - `docs/operations/user-action-runbook.md` (add the SL-1 posture choice operationalization, SL-2 bearer-vs-NetworkPolicy decision, SL-3 `MCP_ATTESTATION_MODE` matrix, SL-4 `MCP_ALLOWED_ROOTS` and `MCP_REQUIRE_TOKEN_SCOPES` guidance)
  - `docs/security/` (new directory, contains `sandbox.md`, `attestation.md`, `path-guard.md`, `token-scopes.md` — one-pager per IF gate)
  - `specs/phase-plans-v1.md` (append `### Post-execution amendments` under Phase 15 section if any IF signature drifted)
  - `.claude/docs-catalog.json` if it exists; otherwise skip the catalog rescan step
- **Interfaces provided**: (none)
- **Interfaces consumed**: (none)
- **Parallel-safe**: no (terminal)
- **Depends on**: SL-0, SL-1, SL-2, SL-3, SL-4

**Tasks**:

| Task ID | Type | Depends on | Files in scope | Action |
|---|---|---|---|---|
| SL-docs.1 | docs | — | `.claude/docs-catalog.json` if exists | Rescan: `python3 "$(git rev-parse --show-toplevel)/.claude/skills/_shared/scaffold_docs_catalog.py" --rescan` — **skip with `echo 'scaffold_docs_catalog.py absent — skipping per P14 handoff'` if the script doesn't exist** |
| SL-docs.2 | docs | SL-docs.1 | per catalog, at minimum the files listed above | For each file in the catalog, decide: does this phase's work change it? If yes, update the file. If no, leave it. Record in commit message any files intentionally skipped. |
| SL-docs.3 | docs | SL-docs.2 | `specs/phase-plans-v1.md` | Append `### Post-execution amendments` subsections to the Phase 15 section if any interface freeze was empirically wrong this run. Named freeze IDs + dated correction. If nothing drifted, say so explicitly. |
| SL-docs.4 | verify | SL-docs.3 | — | Run any repo doc linters (`markdownlint`, `vale`, `prettier --check`, Mermaid render). If none configured, no-op. Record outcome in commit message. |

## Execution Notes

- **Parallelism caveats:** SL-0 must land before any impl lane starts — it owns the interface-freeze stubs that SL-1/SL-2/SL-3/SL-4 all import. After SL-0 merges, the four impl lanes may run fully in parallel; plan-phase SKILL defaults `MAX_PARALLEL_LANES=2` for execute-phase, which is the right posture here (P15 has demonstrably risky lanes — SL-1 especially).
- **Single-writer files:**
  - `mcp_server/gateway.py` — owner lane mapping: SL-2 owns lines `:1117-1127` (metrics decorator collapse + dependency injection). SL-4 owns line `:104` (normalize_search_result guard injection) and line `:337` area (TokenValidator startup call). These ranges do not overlap. Top-of-file imports are a shared add/add surface; resolve alphabetically at merge time per the P14 pattern.
  - `mcp_server/security/security_middleware.py` — owner lane mapping: SL-0 authors the `require_auth` stub (raises `NotImplementedError`). SL-2 fills the body + removes `/metrics` from `excluded_paths`. Expected add/add conflict at merge time — pre-authorized below.
  - `mcp_server/artifacts/artifact_upload.py::create_metadata` — owner lane mapping: SL-3 exclusively. Its signature gains a new optional `attestation: Attestation | None = None` kwarg; default `None` means every non-SL-3 caller stays green.
- **Known destructive changes:** none — every lane is purely additive or strictly-scoped in-place edits.
- **Expected add/add conflicts:**
  - `mcp_server/security/security_middleware.py` — SL-0 preamble stubs `require_auth`; SL-2 replaces the body. Pre-authorize `git checkout --theirs mcp_server/security/security_middleware.py` at SL-2 merge time.
  - `mcp_server/sandbox/*.py`, `mcp_server/plugins/sandboxed_plugin.py`, `mcp_server/artifacts/attestation.py`, `mcp_server/security/path_guard.py`, `mcp_server/security/token_validator.py` — all stubbed by SL-0 and filled by their owner lane. Pre-authorize `git checkout --theirs <path>` for each at the filling lane's merge time.
- **SL-0 re-exports:** `mcp_server/sandbox/__init__.py` uses the lazy `__getattr__` re-export pattern so that if SL-1 later renames an internal symbol, the package load doesn't break. Do NOT add top-level `from .protocol import Envelope` etc. — use:
  ```python
  def __getattr__(name: str):
      if name == "Envelope":
          from .protocol import Envelope
          return Envelope
      if name == "CapabilitySet":
          from .capabilities import CapabilitySet
          return CapabilitySet
      # ... etc.
      raise AttributeError(f"module 'mcp_server.sandbox' has no attribute {name!r}")
  ```
- **Worktree naming:** execute-phase allocates unique worktree names via `scripts/allocate_worktree_name.sh`. The plan doc does not spell out lane worktree paths.
- **Stale-base guidance (copy verbatim):** Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-SL-0-merge and it depends on SL-0's stubs, it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.
- **Architectural choices (consensus summary):**
  - **IF-0-P15-1 transport: subprocess + JSON-line IPC.** UNANIMOUS across arch-minimal, arch-clean, arch-parallel. WASI rejected (requires recompiling tree-sitter/SQLite native deps; blocks Go plugin's `subprocess` use). Subinterpreters rejected (share FS/net surface).
  - **SL-0 preamble: yes.** Majority (arch-clean + arch-parallel). arch-minimal judged it unnecessary; accepted as the cheap insurance against eager-import breakage mid-phase.
  - **SL-1 single lane (not split).** Majority (arch-minimal + arch-clean). arch-parallel advocated for SL-1a/1b/1c split. Dissent recorded: if SL-1 executes and finds itself larger than one lane-day, re-plan mid-phase by splitting into the same three chunks arch-parallel proposed (IPC protocol / supervisor+worker / adapter+malicious) — disjoint file globs already defined in that proposal.
  - **`require_permission` stays; `require_auth` wraps it.** arch-clean advocated deprecation; majority kept to minimize migration surface in a security phase. Dissent: deprecation deferred to P16 or a side-PR.
  - **`path_allowlist.py` stays.** arch-clean advocated deletion; majority kept — `PathTraversalGuard` uses `path_allowlist.path_within_allowed` internally. No out-of-scope refactor in a security phase.
  - **`TokenValidator` uses HTTP `GET /user` + `X-OAuth-Scopes` header,** not `gh auth status --show-token` parsing. arch-clean's choice; arch-minimal's CLI-parse alternative is fragile.
  - **`MCP_ATTESTATION_MODE={enforce,warn,skip}`,** default `enforce`. arch-clean's design; accepted over arch-minimal's binary `DISABLED` toggle.
- **Repo-script absence (from P14 handoff):** `scripts/validate_plan_doc.py`, `.claude/skills/_shared/scaffold_docs_catalog.py`, `.claude/skills/_shared/next_reflection_path.py` are absent in this repo. Skip the validator step in Step 7, skip docs-catalog rescan in SL-docs.1, emit plain reflection file paths in close-out.
- **P14 carry-over debt NOT addressed in P15:** 18 pre-existing `test_cross_repo_coordinator.py` failures, 9 `ruff F401` warnings, `RerankerFactory.create_default()` realization. Out of scope. Lane teammates must leave these alone on sight.

## Acceptance Criteria

- [ ] **SL-1 (plugin sandbox):** `pytest tests/security/test_malicious_plugin.py -v --no-cov` passes. The malicious plugin's attempts to `open("/etc/passwd")`, `socket.socket()`, `sqlite3.connect(<host_db>)`, `subprocess.run([...])`, and `os.environ["GITHUB_TOKEN"]` each either raise `SandboxViolation` inside the worker or return an empty/default value; the host process is unaffected (assertable by checking a host-side canary file created pre-test is unchanged post-test). Unit test `test_plugin_sandbox.py` proves `Envelope` round-trip and supervisor lifecycle.
- [ ] **SL-2 (metrics auth):** `curl -s -o /dev/null -w '%{http_code}' localhost:8000/metrics` returns `401`. `curl -H "Authorization: Bearer <admin-token>" localhost:8000/metrics` returns `200` with Prometheus `text/plain` content. `pytest tests/security/test_metrics_auth.py -v --no-cov` passes. Grep: `rg 'excluded_paths' mcp_server/security/security_middleware.py` shows `/metrics` is not in the list (this grep assertion is paired with the test file — not standalone).
- [ ] **SL-3 (attestation):** `pytest tests/security/test_artifact_attestation.py -v --no-cov` passes. Tampering one byte of a post-attest archive under `MCP_ATTESTATION_MODE=enforce` causes `verify_attestation` to raise `AttestationError`. The metadata dict returned from `create_metadata` includes an `attestation_url` key when `attestation=` is passed.
- [ ] **SL-4 (path guard + token + rate-limit):** `pytest tests/security/test_path_traversal.py tests/security/test_token_scope.py tests/test_cross_repo_rate_limit.py -v --no-cov` passes. `GET /search` with an injected `../../../etc/passwd` result either returns 403 or filters the hit out of the response (test asserts the hit is absent). Startup with `MCP_REQUIRE_TOKEN_SCOPES=1` + a token missing `attestations:write` raises `InsufficientScopesError` with a message naming the missing scope. `_respect_rate_limit` sleeps when `X-RateLimit-Remaining: 50`.
- [ ] **SL-docs:** `docs/operations/user-action-runbook.md` contains new subsections for: SL-1 plugin-trust posture selection, SL-2 bearer-vs-NetworkPolicy decision matrix, SL-3 `MCP_ATTESTATION_MODE` trinary, SL-4 `MCP_ALLOWED_ROOTS` + `MCP_REQUIRE_TOKEN_SCOPES` guidance. `specs/phase-plans-v1.md` Phase 15 section has a `### Post-execution amendments` subsection (possibly empty, explicitly stating "no drift").
- [ ] **No regressions on prior phases:** full test suite excluding the 18 pre-existing `test_cross_repo_coordinator.py` failures and the P14 known-pre-existing `TestRemoveFileSemanticCleanup` case still passes: `pytest --ignore=tests/test_cross_repo_coordinator.py --deselect tests/test_plugin_manager_enhanced.py::TestRemoveFileSemanticCleanup -v --no-cov`.

## Verification

```bash
# SL-1 — plugin sandboxing
pytest tests/security/test_plugin_sandbox.py tests/security/test_malicious_plugin.py -v --no-cov

# SL-2 — metrics auth — unauth'd request denied
MCP_ALLOWED_ROOTS=/tmp/repo-a op run --env-file=.mcp.env -- python -m mcp_server.cli.server_commands &
sleep 3
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/metrics   # expect 401
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $MCP_ADMIN_TOKEN" localhost:8000/metrics   # expect 200
pytest tests/security/test_metrics_auth.py -v --no-cov

# SL-3 — artifact attestation verify
pytest tests/security/test_artifact_attestation.py -v --no-cov

# SL-4 — path traversal + token scope + rate limit
pytest tests/security/test_path_traversal.py tests/security/test_token_scope.py tests/test_cross_repo_rate_limit.py -v --no-cov

# Regression gate — prior-phase suites must remain green (minus pre-existing P14 carry-over)
pytest \
  --ignore=tests/test_cross_repo_coordinator.py \
  --deselect tests/test_plugin_manager_enhanced.py::TestRemoveFileSemanticCleanup \
  -v --no-cov
```

If any of the above fails — a sandboxed plugin escapes to the host filesystem, an unauth'd `/metrics` scrape returns 200, a tampered artifact passes attestation verification under `enforce`, a path-traversal variant reaches the HTTP response body, or startup silently succeeds with a token missing `attestations:write` — the phase is not merge-ready.
