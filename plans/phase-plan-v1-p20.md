# P20: Multi-Repo Validation & Staged Rollout (GA)

> Plan doc produced by `/plan-phase P20` against the P20 section of `specs/phase-plans-v1.md` (line 1102) on 2026-04-20.
> On approval, copy to `plans/phase-plan-v1-p20.md` and hand off to `/execute-phase p20`.

## Context

P19 merged to `origin/main` (tip `1427666`) with `v1.2.0-rc1` tag pushed. The P19 handoff surfaced three concrete P20-scope items: (1) a **P18 sandbox-default-on regression** that fails 4 tests (`tests/test_dispatcher.py::TestEnhancedDispatcherProtocolConformance::test_get_plugins_for_file_accepts_ctx` + 3 in `tests/test_plugin_factory_async.py`) — root cause: `RLIMIT_AS=512 MiB` (`mcp_server/sandbox/caps_apply.py::_apply_rlimits`, lines 115–133) collides with OpenBLAS's multi-GiB virtual-arena reservation when plugins transitively import numpy; (2) `_check_gh_auth_for_attestations` is marker-gated rather than mockable — deferred to a 1.2.0 patch release, not in-scope for P20; (3) `ATTESTATION_GH_TOKEN` CI secret — operator action, not code. P20's job is to fix (1) as a hotfix lane, prove the multi-repo primitives under real concurrent load, rehearse a production rollout, and cut the GA tag.

### What actually exists today

**Sandbox surface** (confirmed by `explore-sandbox`):
- `mcp_server/sandbox/capabilities.py::CapabilitySet` — frozen dataclass at lines 28–36; `mem_mb: int = 512` is the default (line 36). Callers that pass explicit `mem_mb=…` are unaffected by a default bump.
- `mcp_server/sandbox/caps_apply.py::apply` (line 224) runs steps in fixed order: step 3 scrubs env (`_scrub_env`, lines 82–89) per `CapabilitySet.env_allow=frozenset()`; step 5 applies rlimits via `_apply_rlimits` (lines 115–133). Setting `OPENBLAS_NUM_THREADS` in the **parent** env is therefore ineffective — the scrub strips it before the plugin module imports numpy.
- `mcp_server/sandbox/supervisor.py::_ensure_spawned` (lines 43–54) spawns `subprocess.Popen(worker_cmd, stdin=PIPE, …)` with no `env=` kwarg. Worker inherits parent env; scrubbing then happens worker-side in `caps_apply.apply`.
- `mcp_server/sandbox/worker_main.py::main` (lines 184–202): receives plugin module + caps JSON on CLI, calls `caps_apply.apply(caps)` BEFORE `importlib.import_module(plugin_module_name)`.
- `MCP_PLUGIN_SANDBOX_DISABLE=1` opt-out read at `mcp_server/plugins/plugin_factory.py:251`. Default-on since P18 SL-5.
- No occurrences of `OPENBLAS_NUM_THREADS` or `OMP_NUM_THREADS` in production code — confirms no prior attempt.

**Multi-repo primitives surface** (confirmed by `explore-harness`):
- `mcp_server/storage/repository_registry.py::RepositoryRegistry` (lines 25–340): `register_repository(repo_path, auto_sync=True, artifact_enabled=True, priority=0) → str` returns 16-hex `repo_id`. Registry JSON at `~/.mcp/repository_registry.json` by default; `MCP_REPO_REGISTRY` env override. Flock sibling `.lock` file (line 193). Thread-safe via RLock + flock on `save()` (line 187) per IF-0-P17-1.
- `mcp_server/core/repo_context.py::RepoContext` (lines 13–31): frozen dataclass — `repo_id: str`, `sqlite_store: SQLiteStore`, `workspace_root: Path`, `tracked_branch: str`, `registry_entry: RepositoryInfo`.
- `mcp_server/dispatcher/protocol.py::DispatcherProtocol.get_plugins_for_file(ctx: RepoContext, path: Path) → List[Tuple[IPlugin, float]]` (line 78) — target of the P19-failing dispatcher test.
- `mcp_server/cli/bootstrap.py::reset_process_singletons() → None` (lines 69–123) — resets 8 module-scope `_instance` singletons. Required between gateway boot cycles in multi-gateway tests.
- `mcp_server/artifacts/delta_resolver.py::resolve_delta_chain(artifacts: List[Dict], target_commit: str) → List[Dict[str, Any]]` (lines 8–48) — cross-repo base reference resolution already exists.
- `tests/fixtures/multi_repo.py::boot_test_server` (lines 219–310) — **in-process** helper; uses `TestClient` pattern. **Insufficient** for P20's "≥2 gateways against a shared registry" requirement — SL-1 must spawn real subprocesses.
- `tests/test_registry_concurrency.py` (lines 17–56) — existing `multiprocessing.Process` pattern with `p.join(timeout=30)`. SL-1's `test_registry_concurrency_live.py` reuses this shape for the lost-writes load test.
- No existing port-allocation fixture. SL-1 introduces `socket.bind(('',0))` + close + pass-port-to-child.
- Existing `tests/integration/` contents: `__init__.py`, `test_phase1_foundation.py`, `test_multi_repo_server.py` (P5), `test_sigterm_shutdown.py`, `test_dispatcher_fallback_metrics.py`. No `multi_repo/` or `obs/` subdirectory yet.

**Observability + docs surface** (confirmed by `explore-obs-docs`):
- `mcp_server/metrics/prometheus_exporter.py` defines all three counters: `mcp_tool_calls_total{tool,status}` (line 62–66), `mcp_rate_limit_sleeps_total` (line 81–84), `mcp_artifact_errors_by_class_total{error_class}` (line 87–91). Emission sites: `mcp_server/artifacts/providers/github_actions.py` (rate-limit + error class) and `mcp_server/artifacts/publisher.py` (error class).
- `/metrics` endpoint: `mcp_server/gateway.py` lines 1167–1206, gated by `require_auth("metrics")` (P15 SL-2). Port configured via `prometheus_port` in `mcp_server/config/settings.py:267` (default 8001). **No `MCP_METRICS_PORT` env var** — plan must configure via `prometheus_port` setting or `MCP_PROMETHEUS_PORT` env mapping.
- JSON logging: `mcp_server/core/logging.py::JSONFormatter` (lines 14–34). Gated on `Environment.PRODUCTION` OR `MCP_LOG_FORMAT=json` (lines 37–41). Single-line JSON via `json.dumps()` (line 34).
- Secret redaction: `mcp_server/security/security_middleware.py::SecretRedactionResponseMiddleware` (lines 458–524). Three regex patterns: `Bearer\s+\S+`, `JWT_SECRET_KEY=\S+`, `GITHUB_TOKEN=\S+` (lines 458–462), all replaced with `[REDACTED]`.
- `scripts/preflight_upgrade.sh` (from P19 SL-4, per IF-0-P19-1) — shell-wraps `python -m mcp_server.cli preflight_env <file>`; exit 0 pass, 1 fatal; `[FATAL]`/`[WARN]` rendered per `render_validation_errors_to_stderr`.
- `docs/operations/` today: `artifact-retention.md`, `gateway-startup-checklist.md`, `known-test-debt.md`, `multi-instance.md`, `p18-upgrade.md`, `user-action-runbook.md` (6 files). Style convention: numbered section headings, env-var + code-path cross-links, short tables.
- Existing monitoring compose template: `docker/compose/production/docker-compose.monitoring.yml` (Prometheus + Loki + Grafana). SL-2's `tests/integration/obs/infra/docker-compose.yml` mirrors this shape at minimal scale (Prom + Loki only; no Grafana in smoke).
- `prometheus_client` is already a dep (present in `pyproject.toml`).
- `.claude/docs-catalog.json` present; schema `{version:int, generated_at:str, docs:[{path,description,touched_by_phases}]}`. Scaffold tool `.claude/skills/_shared/scaffold_docs_catalog.py` — invocation `python3 .claude/skills/_shared/scaffold_docs_catalog.py --rescan` (P19 SL-3 delivered at 130 LOC).
- `CHANGELOG.md` header style: `## [VERSION] — DATE`, subsections `### Added (Pxx — …)`. P19 added `[1.2.0-rc1]`. SL-4 promotes `[Unreleased]` → `[1.2.0]` and tags `v1.2.0`.

### Repo-specific gotchas (inherited from P19 handoff)

- `pytest.ini` has `--cov-fail-under=35` in `addopts` — new integration tests must pass `--no-cov` when run standalone, else coverage gate fails despite passing tests.
- `tag.forceSignAnnotated=true` + `tag.gpgSign=true` in git config — `git tag <name> <sha>` without `-m "…"` fails with "no tag message". SL-4 must use `git tag -m "…" <name> <sha>`.
- `.claude/scheduled_tasks.lock` is touched throughout sessions by a background scheduler; it's in `verify_harness.sh`'s allowlist. Not a lane concern but noisy in `git status`.
- Orchestrator scripts live in `~/.claude/skills/execute-phase/scripts/`, not in `scripts/`. Do NOT look for `allocate_worktree_name.sh` in the repo.
- `scripts/validate_plan_doc.py` does not exist in this repo; P19 plan skipped the validator step. This plan does likewise.

## Interface Freeze Gates

- [ ] **IF-0-P20-1** — `tests/integration/multi_repo/conftest.py::multi_repo_fixture` is a `pytest.fixture(scope="module")` yielding a `MultiRepoContext` dataclass:

  ```python
  @dataclass(frozen=True)
  class MultiRepoContext:
      gateways: tuple[GatewayHandle, ...]   # len == n_gateways, default 2
      registry_path: Path                    # shared across all gateways
      repos: dict[str, RepoHandle]           # keyed by repo_id; len == n_repos

  @dataclass(frozen=True)
  class GatewayHandle:
      pid: int
      port: int
      base_url: str            # e.g. "http://127.0.0.1:53412"
      # proc: subprocess.Popen  # not part of frozen contract; internal only

  @dataclass(frozen=True)
  class RepoHandle:
      path: Path               # workspace dir; each distinct
      repo_id: str             # 16-hex sha256 from RepositoryRegistry.register_repository
      sqlite_path: Path        # per-repo SQLite store
  ```

  Fixture factory signature (driven by indirect parametrization): `multi_repo_fixture(n_gateways: int = 2, n_repos: int = 2)`. Teardown is synchronous and idempotent: `proc.terminate() → wait(timeout=10) → kill()` per gateway, followed by unlinking `registry_path` and repo workspaces. Consumed by every P20 multi-repo integration test. **Owner**: SL-1. **Consumers**: `test_registry_concurrency_live.py`, `test_cross_repo_delta.py`, `test_multi_repo_dispatcher.py`.

- [ ] **IF-0-P20-2** — `docs/operations/deployment-runbook.md` frozen structure:

  ```
  # Deployment Runbook (v1.2.0)
  ## Overview
  ## Stages
  ### Stage: dev
  ### Stage: staging
  ### Stage: canary
  ### Stage: full-prod
  ## Bake-gate criteria
  ## Rollback triggers
  ## Rollback procedure
  ## Preflight checklist (cross-link to scripts/preflight_upgrade.sh)
  ```

  Each `### Stage: <name>` has H4s: `Pass criteria` (measurable: error rate %, 99p latency ms, log JSON parse rate %, counter non-zero), `Bake window` (duration), `Rollback trigger` (first breach of pass criteria), `Rollback procedure` (sequenced commands with expected exit codes). Additional stages may be appended in future releases without editing existing ones. **Owner**: SL-3. **Consumers**: SL-4 executes the runbook; P21+ appends stages.

- [ ] **IF-0-P20-3** — `CapabilitySet.mem_mb` default is `2048`. `mcp_server/sandbox/capabilities.py` line 36 reads `mem_mb: int = 2048`. Callers that supply explicit `mem_mb=…` are unchanged. Rationale: retains fork-bomb/leak ceiling while leaving headroom for OpenBLAS's virtual-arena reservation at default thread count. **Owner**: SL-0. **Consumers**: `tests/test_dispatcher.py::TestEnhancedDispatcherProtocolConformance::test_get_plugins_for_file_accepts_ctx` + 3 in `tests/test_plugin_factory_async.py`.

## Lane Index & Dependencies

```
SL-0 — Sandbox hotfix (mem_mb 512 → 2048)
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-4
  Parallel-safe: yes (single-line default change in isolated file)

SL-1 — Multi-repo integration harness
  Depends on: SL-0
  Blocks: SL-4
  Parallel-safe: yes (new tests/integration/multi_repo/ subtree, disjoint from SL-2/SL-3)

SL-2 — Observability staging smoke
  Depends on: SL-0
  Blocks: SL-4
  Parallel-safe: yes (new tests/integration/obs/ subtree + new docs/operations/observability-verification.md)

SL-3 — Deployment runbook
  Depends on: (none)
  Blocks: SL-4
  Parallel-safe: yes (single new file docs/operations/deployment-runbook.md)

SL-4 — Staged rollout execution (operator-gated halt)
  Depends on: SL-0, SL-1, SL-2, SL-3
  Blocks: SL-docs
  Parallel-safe: no (serial after all impl lanes; ends at "ready-for-operator" state, halts)

SL-docs — Documentation & spec reconciliation (terminal)
  Depends on: SL-0, SL-1, SL-2, SL-3, SL-4
  Blocks: (none)
  Parallel-safe: no (terminal)
```

Two-wave dispatch under `MAX_PARALLEL_LANES=2`: **Wave 1** {SL-0, SL-3} (both DAG roots, disjoint files). **Wave 2** {SL-1, SL-2}. **Wave 3** {SL-4} (operator-gated). **Wave 4** {SL-docs}.

## Lanes

### SL-0 — Sandbox hotfix (mem_mb 512 → 2048)

- **Scope**: Raise default `CapabilitySet.mem_mb` from 512 to 2048 so sandbox-default-on plugins that transitively import numpy/OpenBLAS don't abort on RLIMIT_AS.
- **Owned files**: `mcp_server/sandbox/capabilities.py`
- **Interfaces provided**: IF-0-P20-3 (`CapabilitySet.mem_mb` default = 2048)
- **Interfaces consumed**: (none)
- **Parallel-safe**: yes
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-0.1 | test | — | `tests/test_plugin_factory_async.py`, `tests/test_dispatcher.py` (read-only) | confirm the 4 failing tests currently fail for the OpenBLAS reason (baseline) | `pytest tests/test_plugin_factory_async.py tests/test_dispatcher.py::TestEnhancedDispatcherProtocolConformance::test_get_plugins_for_file_accepts_ctx -v --no-cov` |
| SL-0.2 | impl | SL-0.1 | `mcp_server/sandbox/capabilities.py` | — | — |
| SL-0.3 | verify | SL-0.2 | `mcp_server/sandbox/**`, `tests/test_plugin_factory_async.py`, `tests/test_dispatcher.py` | 4 target tests pass; no regression in `tests/test_sandbox*.py` | `pytest tests/test_plugin_factory_async.py tests/test_dispatcher.py tests/test_sandbox -v --no-cov` |

Concrete diff shape for SL-0.2: one line in `mcp_server/sandbox/capabilities.py`:

```diff
-    mem_mb: int = 512
+    mem_mb: int = 2048
```

No test needs to be written beyond unskipping/asserting the existing 4 — they encode the contract.

### SL-1 — Multi-repo integration harness

- **Scope**: Spec-mandated live integration suite under `tests/integration/multi_repo/` — fixture + registry concurrency load test + cross-repo delta resolution + dispatcher routing under 2+ live gateway subprocesses sharing one registry.
- **Owned files**: `tests/integration/multi_repo/**` (new directory). Specifically: `tests/integration/multi_repo/__init__.py`, `tests/integration/multi_repo/conftest.py`, `tests/integration/multi_repo/test_registry_concurrency_live.py`, `tests/integration/multi_repo/test_cross_repo_delta.py`, `tests/integration/multi_repo/test_multi_repo_dispatcher.py`.
- **Interfaces provided**: IF-0-P20-1 (`multi_repo_fixture` + `MultiRepoContext`/`GatewayHandle`/`RepoHandle`)
- **Interfaces consumed**: `RepositoryRegistry.register_repository` (`mcp_server/storage/repository_registry.py`), `RepoContext` (`mcp_server/core/repo_context.py`), `reset_process_singletons` (`mcp_server/cli/bootstrap.py`), `DispatcherProtocol.get_plugins_for_file(ctx,…)` (`mcp_server/dispatcher/protocol.py`), `resolve_delta_chain` (`mcp_server/artifacts/delta_resolver.py`), `CapabilitySet.mem_mb=2048` (from SL-0).
- **Parallel-safe**: yes (disjoint tree from SL-2/SL-3; independent process namespace from SL-2's compose stack)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/integration/multi_repo/test_registry_concurrency_live.py` | 2 `multiprocessing.Process` writers × 100 `register_repository` calls each to shared registry; post-run registry has 200 distinct `repo_id`s | `pytest tests/integration/multi_repo/test_registry_concurrency_live.py -v --no-cov` |
| SL-1.2 | test | — | `tests/integration/multi_repo/test_cross_repo_delta.py` | repo-A publishes delta whose `base_commit` matches repo-B's latest artifact; `resolve_delta_chain` returns the full chain containing repo-B's base | `pytest tests/integration/multi_repo/test_cross_repo_delta.py -v --no-cov` |
| SL-1.3 | test | — | `tests/integration/multi_repo/test_multi_repo_dispatcher.py` | `GET <gateway_a>/search?repository=<repo_b_id>` returns only files from repo-B's workspace (no cross-contamination); dispatcher honors `ctx.repo_id` | `pytest tests/integration/multi_repo/test_multi_repo_dispatcher.py -v --no-cov` |
| SL-1.4 | impl | SL-1.1 | `tests/integration/multi_repo/__init__.py`, `tests/integration/multi_repo/conftest.py` | — | — |
| SL-1.5 | impl | SL-1.4 | `tests/integration/multi_repo/test_registry_concurrency_live.py` (body) | — | — |
| SL-1.6 | impl | SL-1.4 | `tests/integration/multi_repo/test_cross_repo_delta.py` (body) | — | — |
| SL-1.7 | impl | SL-1.4 | `tests/integration/multi_repo/test_multi_repo_dispatcher.py` (body) | — | — |
| SL-1.8 | verify | SL-1.5, SL-1.6, SL-1.7 | `tests/integration/multi_repo/**` | full SL-1 suite passes twice back-to-back (zombie-cleanup proof) | `pytest tests/integration/multi_repo -v --no-cov && pytest tests/integration/multi_repo -v --no-cov` |

**SL-1.4 `conftest.py` implementation contract** (binds IF-0-P20-1):

1. `_alloc_free_ports(n: int) -> list[int]` — for i in range(n): `sock=socket.socket(); sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]; sock.close(); yield port`. Accept TOCTOU risk via bounded retry at gateway boot (below).
2. `_spawn_gateway(port: int, registry_path: Path, workspace_root: Path) -> GatewayHandle` — `subprocess.Popen(['python','-m','uvicorn','mcp_server.gateway:app','--host','127.0.0.1','--port',str(port)], env={**os.environ, 'MCP_REPO_REGISTRY': str(registry_path), 'MCP_ALLOWED_ROOTS': str(workspace_root), 'MCP_ENVIRONMENT': 'development', 'MCP_LOG_FORMAT': 'text'}, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)`. Then poll `GET http://127.0.0.1:{port}/status` with 0.25s interval, 30s total timeout. On timeout: `proc.kill(); raise GatewayBootTimeout(port=port, stderr=proc.stderr.read())`. Bounded retry (×2) on `OSError: [Errno 98]` port-in-use.
3. `multi_repo_fixture` yields the `MultiRepoContext`; in `finally`: for each gateway `proc.terminate() → proc.wait(timeout=10) → proc.kill()`; `shutil.rmtree(registry_path.parent, ignore_errors=True)`.
4. Register 2 repos via direct `RepositoryRegistry(registry_path).register_repository(str(workspace_root/f'repo-{i}'))` **before** spawning gateways (so gateways see a populated registry on boot).

**SL-1.1 load-test specifics** (binds spec line 1109):
```python
def _writer(registry_path, start_idx, count):
    reg = RepositoryRegistry(registry_path=registry_path)
    for i in range(start_idx, start_idx+count):
        # Register via path per handle so repo_id is computed naturally
        (registry_path.parent / f'repo-{i}').mkdir(parents=True, exist_ok=True)
        reg.register_repository(str(registry_path.parent / f'repo-{i}'))

# Main: 2 Process, each 100 calls; post-join: reload RepositoryRegistry; assert len(repos) >= 200 and all 200 workspaces are represented.
```

### SL-2 — Observability staging smoke

- **Scope**: Local compose stack (Prometheus + Loki) proves production-mode gateway emits JSON logs, scrapeable counters, and redacted secrets. Operator doc captures the reproduce-on-staging procedure.
- **Owned files**: `tests/integration/obs/__init__.py`, `tests/integration/obs/test_obs_smoke.py`, `tests/integration/obs/infra/docker-compose.yml`, `tests/integration/obs/infra/prometheus.yml`, `tests/integration/obs/infra/loki-config.yml`, `docs/operations/observability-verification.md`.
- **Interfaces provided**: verified counter scrape (3 counters), JSON log parse rate assertion, `Bearer [REDACTED]` assertion.
- **Interfaces consumed**: `/metrics` endpoint (`mcp_server/gateway.py:1167–1206`), `prometheus_port` setting (`mcp_server/config/settings.py:267`), `JSONFormatter` (`mcp_server/core/logging.py:14`), `SecretRedactionResponseMiddleware` (`mcp_server/security/security_middleware.py:458`), `CapabilitySet.mem_mb=2048` (from SL-0).
- **Parallel-safe**: yes (disjoint tree from SL-1/SL-3; gateway boots in a separate process namespace from SL-1's gateways)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/integration/obs/test_obs_smoke.py` | (a) gateway stdout lines in PRODUCTION mode all parse as JSON via `json.loads`; (b) `curl /metrics` returns 200 with the 3 counters present; (c) synthetic 4xx with `Authorization: Bearer ABC123` renders response body containing `Bearer [REDACTED]` not `Bearer ABC123` | `pytest tests/integration/obs/test_obs_smoke.py -v --no-cov -m "not skipif_no_docker"` |
| SL-2.2 | impl | SL-2.1 | `tests/integration/obs/__init__.py`, `tests/integration/obs/infra/docker-compose.yml`, `tests/integration/obs/infra/prometheus.yml`, `tests/integration/obs/infra/loki-config.yml` | — | — |
| SL-2.3 | impl | SL-2.2 | `tests/integration/obs/test_obs_smoke.py` (body) | — | — |
| SL-2.4 | impl | SL-2.3 | `docs/operations/observability-verification.md` | — | — |
| SL-2.5 | verify | SL-2.3, SL-2.4 | `tests/integration/obs/**`, `docs/operations/observability-verification.md` | smoke passes; doc's reproduce steps are copy-pasteable (literal commands, no "$VAR" placeholders left unbound) | `pytest tests/integration/obs -v --no-cov && docker compose -f tests/integration/obs/infra/docker-compose.yml down` |

**SL-2.1 test contract**:
```python
@pytest.mark.skipif(shutil.which('docker') is None or subprocess.call(['docker','info'], stdout=..., stderr=...) != 0, reason='requires docker')
def test_obs_smoke(tmp_path):
    # 1. bring up compose stack (Prom :9091, Loki :3100)
    # 2. spawn gateway subprocess with MCP_ENVIRONMENT=production, MCP_LOG_FORMAT=json, MCP_PROMETHEUS_PORT=free_port
    # 3. drain 50 stdout lines; assert all parse as json.loads (parse rate == 1.0)
    # 4. make 5 sample tool calls against the gateway (register + symbol_lookup)
    # 5. curl http://127.0.0.1:{prom_port}/metrics; assert lines match:
    #       r'^mcp_tool_calls_total\{.*\} \d+$'
    #       r'^mcp_rate_limit_sleeps_total(\{.*\})? \d+$'
    #       r'^mcp_artifact_errors_by_class_total\{.*\} \d+$'
    # 6. POST /search with header 'Authorization: Bearer SYNTH_ABC123'; assert 401/403 body contains 'Bearer [REDACTED]' and not 'Bearer SYNTH_ABC123'
```

**SL-2.4 operator doc** must include the literal command sequence from SL-2.3 plus how to point it at a staging gateway (`GATEWAY_URL=https://staging.example.internal`) and expected output for each assertion. Cross-link to `docs/operations/gateway-startup-checklist.md` and `scripts/preflight_upgrade.sh`.

### SL-3 — Deployment runbook

- **Scope**: Write `docs/operations/deployment-runbook.md` per IF-0-P20-2 with staging → canary → full-prod stages, each with measurable bake-pass criteria, bake window, rollback trigger, rollback procedure. Cross-link `scripts/preflight_upgrade.sh`.
- **Owned files**: `docs/operations/deployment-runbook.md` (new, single file).
- **Interfaces provided**: IF-0-P20-2 (runbook structure).
- **Interfaces consumed**: `scripts/preflight_upgrade.sh` (P19 SL-4), `scripts/deploy-production.sh` (existing), `docs/operations/gateway-startup-checklist.md`, `docs/operations/p18-upgrade.md`, `docs/operations/observability-verification.md` (forward-ref to SL-2 output — runbook is authored optimistically and SL-4 smoke will confirm cross-links resolve).
- **Parallel-safe**: yes (single new file, disjoint from every other lane)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_deployment_runbook_shape.py` | file exists; contains H2 `Stages`; each of `dev`/`staging`/`canary`/`full-prod` present as H3 `Stage: <n>`; each stage has H4 `Pass criteria`, `Bake window`, `Rollback trigger`, `Rollback procedure`; cross-link to `scripts/preflight_upgrade.sh` resolves on disk | `pytest tests/test_deployment_runbook_shape.py -v --no-cov` |
| SL-3.2 | impl | SL-3.1 | `docs/operations/deployment-runbook.md` | — | — |
| SL-3.3 | verify | SL-3.2 | `docs/operations/deployment-runbook.md`, `tests/test_deployment_runbook_shape.py` | shape test passes; all linked `scripts/*.sh` exist | `pytest tests/test_deployment_runbook_shape.py -v --no-cov` |

**SL-3.2 content contract** — measurable pass criteria per stage (not prose):

- **staging**: error rate <1% over 15 min, 99p latency <500ms, JSON log parse rate ≥99%, `mcp_tool_calls_total` increments non-zero per 5-min window. Bake window: 30 min. Rollback trigger: any pass criterion breached for >2 consecutive 1-min windows. Rollback procedure: `git tag --delete v1.2.0-rc2 && kubectl rollout undo deploy/mcp-gateway -n staging`.
- **canary** (5% of prod traffic): error rate <0.5%, 99p latency <400ms, JSON log parse rate ≥99.5%. Bake window: 2h. Rollback trigger: 2-min sustained breach. Procedure: remove canary target from LB, scale canary deploy to 0.
- **full-prod**: error rate <0.1%, 99p latency <300ms, JSON log parse rate 100%. Bake window: 72h post-rollout (ties to spec exit criterion). Rollback trigger: 1-min sustained breach of error rate OR any 5xx spike >10× baseline. Procedure: `kubectl rollout undo deploy/mcp-gateway -n prod && git tag v1.2.0-rollback $(git rev-parse HEAD~1) -m "rollback of v1.2.0 at $(date -Iseconds)"`.

### SL-4 — Staged rollout execution (operator-gated halt)

- **Scope**: Cut RC tag (`v1.2.0-rc2` — SL-0 guarantees a code change since `v1.2.0-rc1`), prepare CHANGELOG promotion, drive to "ready-for-operator" state. Halt before actual `git push` of tag or any kubectl action; operator takes over.
- **Owned files**: `CHANGELOG.md` (`[Unreleased]` → `[1.2.0-rc2]` and partial `[1.2.0]` stub), `mcp_server/__init__.py` (version bump `1.2.0-rc1` → `1.2.0-rc2`), `RELEASE-CHECKLIST.md` (new, optional — gated on whether `docs/operations/deployment-runbook.md` suffices).
- **Interfaces provided**: tagged artifact `v1.2.0-rc2` (lightweight; not pushed), promoted CHANGELOG section.
- **Interfaces consumed**: SL-0 (sandbox hotfix must ship in rc2), SL-1 (harness green on origin/main), SL-2 (obs smoke green locally), SL-3 (runbook exists for operator cross-reference), `scripts/preflight_upgrade.sh` (P19).
- **Parallel-safe**: no (serial after all impl lanes; ends at operator-gated halt — no `git push`, no kubectl).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_release_readiness_p20.py` | (a) `mcp_server.__version__` == `'1.2.0-rc2'`; (b) `CHANGELOG.md` contains `## [1.2.0-rc2]` section with P20 hotfix block; (c) all SL-1 + SL-2 + SL-3 test files exist and their targeted assertions pass against the current checkout | `pytest tests/test_release_readiness_p20.py -v --no-cov` |
| SL-4.2 | impl | SL-4.1 | `mcp_server/__init__.py`, `CHANGELOG.md` | — | — |
| SL-4.3 | impl | SL-4.2 | — (creates git tag, does NOT push) | — | `git tag -m "1.2.0-rc2 — P20 GA-track" v1.2.0-rc2 HEAD` |
| SL-4.4 | verify | SL-4.3 | repo state | readiness test passes; `git tag -l v1.2.0-rc2` non-empty; `git status` clean; operator handoff note (see below) appended to task body | `pytest tests/test_release_readiness_p20.py -v --no-cov && git tag -l v1.2.0-rc2` |

**Operator halt contract**: SL-4 does NOT execute `git push`, `git push --tags`, `kubectl`, `helm`, `docker push`, or any production-facing command. SL-4's completion message to orchestrator must include verbatim: "READY-FOR-OPERATOR. Run `git push origin main --follow-tags` to publish rc2, then follow `docs/operations/deployment-runbook.md` Stages section beginning with staging. Do not proceed past staging without bake-gate green per IF-0-P20-2." The actual production rollout, bake-window wall-clock waits, canary promotion, and 72h post-prod bake are tracked outside this plan as operator work.

### SL-docs — Documentation & spec reconciliation

- **Scope**: Refresh the docs catalog, update cross-cutting documentation touched or invalidated by this phase's impl lanes, and append any post-execution amendments to phase specs whose interface freezes turned out wrong.
- **Owned files** (read `.claude/docs-catalog.json` for the authoritative list; a minimum set is below, but the catalog is canonical):
  - Root: `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `MIGRATION.md`, `ARCHITECTURE.md`, `DESIGN.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`
  - Agent indexes: `llm.txt`, `llms.txt`, `llms-full.txt`
  - Service manifests: `services.json`, `openapi.yaml`/`.yml`/`.json`
  - `docs/**`, `rfcs/**`, `adrs/**`
  - `.claude/docs-catalog.json` (this lane maintains it)
  - The current phase's section of `specs/phase-plans-v1.md` (append-only amendments)
  - Any prior `plans/phase-plan-v1-*.md` or prior spec phase sections whose contracts this phase invalidated
- **Interfaces provided**: (none)
- **Interfaces consumed**: (none)
- **Parallel-safe**: no (terminal)
- **Depends on**: SL-0, SL-1, SL-2, SL-3, SL-4

| Task ID | Type | Depends on | Files in scope | Action |
|---|---|---|---|---|
| SL-docs.1 | docs | — | `.claude/docs-catalog.json` | Rescan: `python3 "$(git rev-parse --show-toplevel)/.claude/skills/_shared/scaffold_docs_catalog.py" --rescan`. Picks up `docs/operations/deployment-runbook.md` and `docs/operations/observability-verification.md`; preserves `touched_by_phases` history. |
| SL-docs.2 | docs | SL-docs.1 | per catalog | For each file in the catalog, decide: does P20's work change it? If yes, update the file and append `p20` to its `touched_by_phases`. Expected updates: `CHANGELOG.md` (rc2 section), `docs/operations/p18-upgrade.md` (cross-link to new runbook), `docs/security/sandbox.md` (note mem_mb default bump), `.claude/docs-catalog.json` (self). Record in commit message any files intentionally skipped. |
| SL-docs.3 | docs | SL-docs.2 | `specs/phase-plans-v1.md`, prior plans | Append `### Post-execution amendments` subsection to P20 if any freeze was empirically wrong this run (e.g., if IF-0-P20-1's `GatewayHandle` needed an additional field). Also: append an amendment to P19's section if the `_check_gh_auth_for_attestations` deferral needs formal recording. Named freeze IDs + dated correction. |
| SL-docs.4 | verify | SL-docs.3 | — | Run repo doc linters if configured (`markdownlint`, `prettier --check`). If none configured, no-op. Run `pytest tests/test_docs_catalog_integrity.py` (P19 IF-0-P19-3 gate) to confirm catalog stays valid. |

## Execution Notes

- **Two-wave dispatch under `MAX_PARALLEL_LANES=2`**: Wave 1 {SL-0, SL-3}. Wave 2 {SL-1, SL-2}. Wave 3 {SL-4}. Wave 4 {SL-docs}. SL-0 and SL-3 are both DAG roots with disjoint files, making them the cleanest first wave. SL-1 and SL-2 both consume SL-0 and have independent process namespaces, so they run safely in Wave 2.
- **Single-writer files**:
  - `mcp_server/sandbox/capabilities.py` — SL-0 only (one-line default bump; no other P20 lane touches it).
  - `CHANGELOG.md` — SL-4 only during impl, then SL-docs appends during docs sweep (SL-docs depends on SL-4 so the edits are serialized).
  - `mcp_server/__init__.py` — SL-4 only (version bump).
  - `.claude/docs-catalog.json` — SL-docs only (via `--rescan`; no other lane edits by hand).
  - `tests/integration/multi_repo/` — SL-1 exclusive.
  - `tests/integration/obs/` — SL-2 exclusive.
  - `docs/operations/deployment-runbook.md` — SL-3 exclusive.
  - `docs/operations/observability-verification.md` — SL-2 exclusive.
- **Known destructive changes**: none — every lane is purely additive (SL-0 edits one line of an existing file but deletes nothing; SL-4 promotes `[Unreleased]` to `[1.2.0-rc2]` but `[Unreleased]` stays as an empty stub for future phases).
- **Expected add/add conflicts**: none anticipated. No SL-0 preamble stubs files consumed by later lanes; each lane owns its own new directory or file.
- **SL-0 re-exports**: none — SL-0's change is a default-value edit inside an existing dataclass; no `__init__.py` additions or re-exports required.
- **Port allocation under parallel dispatch**: SL-1 and SL-2 both allocate ports via `socket.bind(('',0))`. The TOCTOU window between close and child `bind` is bounded-retry mitigated in `_spawn_gateway` (×2 retry on `OSError: [Errno 98]`). Cross-lane contention is low because SL-1 and SL-2 run in separate worktrees with their own kernel-allocated ephemeral ports, and the compose stack in SL-2 uses fixed-but-high ports (Prom 9091, Loki 3100) that SL-1 would never pick.
- **Docker-compose dependency**: SL-2 requires a docker daemon. Tests use `@pytest.mark.skipif(docker unavailable)` so they auto-skip on runners without docker. CI job matrix should include only `ubuntu-latest` for SL-2; macOS/Windows entries must skip. Operator handoff doc (SL-2.4) calls out "requires docker" prominently.
- **Zombie uvicorn cleanup**: SL-1's `_spawn_gateway` uses `start_new_session=True` so the child gateway becomes a new process group. Fixture teardown does `os.killpg(os.getpgid(proc.pid), signal.SIGTERM)` before `proc.wait(timeout=10)` + `SIGKILL` fallback. `atexit` registers a backstop that kills any surviving PGs from the fixture's session.
- **SL-4 operator-gated halt**: execute-phase drives SL-4 to a ready state (rc2 tag created locally, CHANGELOG staged, release-readiness test passing). Do NOT let the lane teammate run `git push`, `git push --tags`, `kubectl`, `helm`, `docker push`, `curl -X POST`, or any command that mutates remote state. The lane's final commit message must end with the operator-halt banner described in SL-4's task table.
- **RC tag strategy**: `v1.2.0-rc1` was pushed at end of P19. Because SL-0 mutates `mcp_server/sandbox/capabilities.py`, a new tag is mandatory. Cut `v1.2.0-rc2` unconditionally — do not attempt to move `rc1`.
- **`git tag` signing gotcha**: this repo has `tag.forceSignAnnotated=true` + `tag.gpgSign=true`. Use `git tag -m "1.2.0-rc2 — …" v1.2.0-rc2 HEAD` (the `-m` is mandatory). A bare `git tag v1.2.0-rc2 HEAD` fails with "no tag message".
- **`pytest.ini` coverage gate**: all SL-0/1/2/3/4 test invocations include `--no-cov` to avoid the `--cov-fail-under=35` failure on single-file or single-dir runs. Full-suite runs during SL-docs.4 (if performed) should omit `--no-cov`.
- **Worktree naming**: execute-phase allocates unique worktree names via `~/.claude/skills/execute-phase/scripts/allocate_worktree_name.sh` (skill dir, not repo). Plan doc does not spell out lane worktree paths.
- **Stale-base guidance** (copy verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. SL-1 and SL-2 branch from origin/main after SL-0 merges. If either lane finds its worktree base is pre-SL-0 (i.e., `mcp_server/sandbox/capabilities.py` still reads `mem_mb: int = 512`), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge. SL-4 likewise must verify all of SL-0/SL-1/SL-2/SL-3 are present in its base before cutting rc2.
- **Deferred from P20 scope**: `_check_gh_auth_for_attestations` mockability refactor is NOT in P20 — it goes in a 1.2.0 patch release. P20 is "validation + rollout only" per spec line 1129; adding the refactor expands cross-writer surface on `artifacts/attestation.py` during a release cut, which is exactly the time to minimize surface.
- **Gate escalation**: per spec line 1126, if SL-1 or SL-2 surfaces a real bug (not a harness gap), SL-4 must not advance past staging. The orchestrator should surface such findings to the user via `AskUserQuestion` with `[add hotfix lane, proceed to staging anyway, abort rollout]` and halt until a decision.

## Acceptance Criteria

- [ ] `pytest tests/test_plugin_factory_async.py tests/test_dispatcher.py::TestEnhancedDispatcherProtocolConformance::test_get_plugins_for_file_accepts_ctx -v --no-cov` exits 0 — the 4 previously-failing OpenBLAS tests now pass.
- [ ] `pytest tests/integration/multi_repo -v --no-cov` exits 0 after SL-1 merges — the fixture spawns ≥2 gateway subprocesses sharing one registry, the registry-concurrency test proves all 200 entries land, the cross-repo delta test resolves the chain, the dispatcher test proves `ctx.repo_id` isolation.
- [ ] `pytest tests/integration/obs -v --no-cov` exits 0 on a host with docker — JSON log parse rate == 1.0, all 3 counters scrape, `Bearer [REDACTED]` appears in the redaction test response body.
- [ ] `docs/operations/deployment-runbook.md` exists with H2 `Stages`, H3 `Stage: {dev,staging,canary,full-prod}`, each stage containing H4 `Pass criteria`, `Bake window`, `Rollback trigger`, `Rollback procedure`; file is referenced from `docs/operations/p18-upgrade.md` and `CHANGELOG.md` `[1.2.0-rc2]` section; `tests/test_deployment_runbook_shape.py` exits 0.
- [ ] `git tag -l v1.2.0-rc2` returns a single matching tag; `mcp_server.__version__` == `'1.2.0-rc2'`; `CHANGELOG.md` contains `## [1.2.0-rc2]` section with a P20 hotfix subsection listing the sandbox `mem_mb` default bump.
- [ ] `.claude/docs-catalog.json` integrity test (`pytest tests/test_docs_catalog_integrity.py`) exits 0 after SL-docs runs `--rescan`; both new docs are present in the catalog with `"touched_by_phases": ["p20"]`.
- [ ] Full-suite regression: `pytest --no-cov --ignore=tests/real_world tests/` reports `0 failed` (down from 4 at P19 close).
- [ ] SL-4's final commit message ends with the literal "READY-FOR-OPERATOR" banner described in the SL-4 section; no `git push` or `kubectl` command was executed by any lane teammate.

## Verification

Post-merge commands to run on origin/main:

```bash
# (0) Sandbox hotfix proven
pytest tests/test_plugin_factory_async.py \
       tests/test_dispatcher.py::TestEnhancedDispatcherProtocolConformance::test_get_plugins_for_file_accepts_ctx \
       -v --no-cov
# expect: 4 passed

# (1) Multi-repo integration harness green
pytest tests/integration/multi_repo -v --no-cov
# expect: 3+ passed; 200 registry entries after concurrent writers

# (2) Observability smoke (docker required)
docker info >/dev/null 2>&1 && \
  pytest tests/integration/obs -v --no-cov
# expect: 1 passed (or skipped with reason='requires docker')

# (3) Runbook shape + cross-links
pytest tests/test_deployment_runbook_shape.py -v --no-cov
# expect: 1 passed; all scripts/* cross-links resolve on disk

# (4) Release readiness
pytest tests/test_release_readiness_p20.py -v --no-cov
git tag -l v1.2.0-rc2
grep -F '## [1.2.0-rc2]' CHANGELOG.md
python -c "import mcp_server; print(mcp_server.__version__)"
# expect: readiness green; tag present; CHANGELOG section present; version 1.2.0-rc2

# (5) Docs catalog integrity
pytest tests/test_docs_catalog_integrity.py -v --no-cov
# expect: 1 passed

# (6) Full-suite regression gate
pytest --no-cov --ignore=tests/real_world tests/
# expect: 0 failed (down from 4 pre-P20)

# (7) Preflight script still green (P19 regression check)
./scripts/preflight_upgrade.sh .mcp.env.example
# expect: exit 0, no [FATAL] lines

# (8) Operator-gated halt — MANUAL FROM HERE
# These commands are NOT run by execute-phase. Operator executes per docs/operations/deployment-runbook.md:
#   git push origin main --follow-tags
#   kubectl apply -f deploy/staging.yaml
#   # bake 30min per staging pass criteria in runbook
#   # promote to canary per runbook
#   # bake 2h
#   # promote to full-prod per runbook
#   # 72h post-rollout bake — final GA exit criterion
```

Any failure in (0)–(7) fails the lane-merge pipeline and blocks SL-4. Failures in (8) during operator rollout trigger the runbook's rollback procedure; post-rollback, SL-docs appends an amendment noting what bake-gate criterion was breached and why.
