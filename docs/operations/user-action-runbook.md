# User Action Runbook — P12 through P15

> This runbook lists actions that **cannot** be performed by automated phase execution (`/execute-phase`) and must be done by the operator. Each phase has a "before execute-phase" checklist and an "after-merge" checklist. Read the relevant section before invoking `/plan-phase` for that phase.

Companion document to `specs/phase-plans-v1.md` (Phases P12–P15).

---

## 1. Overview

The P12–P15 remediation arc depends on out-of-band operator actions at several points: GitHub repository settings, token scopes, infrastructure provisioning, policy decisions, and post-merge observability wiring. The code changes are designed to **fail loud** when these actions are missing (e.g., `TokenValidator.validate_scopes()` at P15 startup), so performing the operator actions *before* the matching phase executes saves rework.

If you're reading this for the first time: work through Section 2 (one-time prerequisites) now, then consult Sections 3.x ("Before P1n" / "After P1n") alongside each phase execution.

---

## 2. One-time prerequisites

Do these once, before running `/plan-phase P12`:

- [ ] **Create or rotate `GITHUB_TOKEN`** with base scopes `contents:read`, `metadata:read`. This token is consumed by artifact downloads throughout P12–P15. Additional scopes are added in later phases — do not pre-grant them unless you have a reason.
- [ ] **Decide on distribution channel** (PyPI / private PyPI / container-only). This affects P12 SL-5's lockfile CI job — the job assumes you will have a way to install pinned dependencies in production.
- [ ] **Provision Prometheus scrape target.** Ensure a Prometheus instance can reach the existing `/metrics` endpoint. Authentication posture is decided later in P15 SL-2 (Section 3.4); for now, treat `/metrics` as internal-only.
- [ ] **Confirm GitHub Artifacts storage is available** for the repo(s) you'll index. If not — or if you plan to store >10 GB per artifact or >100 GB total — review the artifact-backend alternatives before P13 (bullet in Section 3.2 "Before P13").

---

## 3. Per-phase user actions

### 3.1 Phase 12 — Ops Readiness + Reindex Safety

#### Before P12

No operator actions required. P12 is fully codebase-internal.

#### After P12 merge

- [ ] **Update Prometheus scrape rules** to recognize the new histograms:
  - `mcp_symbol_lookup_duration_seconds`
  - `mcp_search_duration_seconds`
  Add recording rules for P95/P99 if you plan to alert on latency regressions.
- [ ] **Configure k8s readiness + liveness probes** pointing at the new endpoints (if deploying to k8s):
  - `readinessProbe.httpGet.path: /ready`
  - `livenessProbe.httpGet.path: /liveness`
  - Defaults from the phase: ready threshold responds within ~1s; liveness tolerates up to 10s event-loop block.
- [ ] **Extend GitHub Artifact retention** from 90 days (default) → 400 days if you depend on them long-term. Navigate to `Settings → Actions → General → Artifact and log retention → 400 days`. Alternatively, plan for regular re-publishes before expiry (P13 SL-4 enables this).
- [ ] **Set `MCP_ARTIFACT_MAX_AGE_DAYS`** (default 14) according to your staleness tolerance.

### 3.2 Phase 13 — Reindex Durability + Artifact Automation

#### Before P13

- [ ] **Extend `GITHUB_TOKEN` scope** to include `actions:read` and `actions:write` (required by SL-4's direct-publish path). Rotate the token if needed; `TokenValidator` checks scopes at P15 startup but earlier diagnostics are emitted as warnings.
- [ ] **Decide on artifact storage growth strategy.** If repos are approaching GitHub's 10 GB per-artifact or 100 GB per-repo caps, now is the decision point — stay on GitHub Releases, migrate to GCS/S3, or introduce delta-only publishes (the latter is actually enabled automatically in P14 SL-4 when full artifacts exceed `MCP_ARTIFACT_FULL_SIZE_LIMIT`; until then, plan headroom).
- [ ] **Create a workflow concurrency group** on the GitHub Actions workflow that will receive direct-publish triggers. This prevents double-uploads from simultaneous reindexes:
  ```yaml
  concurrency:
    group: index-publish-${{ github.ref }}
    cancel-in-progress: false
  ```
- [ ] **Decide on a `latest`-pointer namespace.** P13 SL-4 uses release tags to implement atomic `latest` pointer; pick a convention (e.g., `index-latest-{repo_id_short}`) and reserve the namespace.

#### After P13 merge

- [ ] **Write alerting rules on `mcp_errors_by_type_total`.** Page on sudden spikes; alert-on-any for `PluginError` if plugin errors should be rare in your deployment. Counter labels: `module` (e.g., `dispatcher`, `publisher`) and `exception` (e.g., `IndexingError`, `ArtifactError`).
- [ ] **Retire the cron-based upload workflow.** P13 SL-4 replaces the cron trigger with direct-publish-on-reindex. The watcher now calls `ArtifactPublisher.publish_on_reindex()` directly on successful repository reindex. The workflow still exists for manual publishes via `gh workflow run index-artifact-management.yml -f action=publish_on_reindex -f repo=<repo_id> -f commit=<sha>`. Either delete the cron schedule or convert it to a no-op stub documenting the deprecation.
- [ ] **Configure a reindex-resume dashboard** if you monitor reindex progress. The new `.reindex-state` file (ReindexCheckpoint dataclass) lets operators observe mid-flight reindex state without waiting for completion; exposing it via a debug endpoint is optional but helpful.
- [ ] **Verify atomic artifact releases.** P13 SL-4 writes `index-<short-sha>` releases atomically and moves `index-latest` pointer via `gh release edit --target`. Spot-check that the latest pointer always references the most recent successful reindex.

### 3.3 Phase 14 — Multi-Repo Completeness + Schema Evolution

#### Before P14

- [ ] **Audit dependency-file coverage across your multi-repo fleet.** SL-2 detects dependencies only in `pyproject.toml`, `package.json`, `go.mod`, and `Cargo.toml`. Repos using unsupported ecosystems (Python `pyproject.toml`, Ruby Gemfile, PHP composer.json, etc.) will show empty dep sets. Either add ecosystem-parser lanes to P14 SL-2 or accept the gap.
- [ ] **Decide schema-version deprecation policy.** SL-3's `SchemaMigrator` supports forward migration across versions; set a cap on how many versions back you'll support (e.g., N-2). Document the policy here for future reference.
- [ ] **Decide reranker provider.** SL-1 wires `RerankerProvider`. Options: no-op (default, same as today), Voyage AI reranker, Cohere reranker, or self-hosted. Pick one and provision the credential + endpoint before planning SL-1.

#### After P14 merge

- [ ] **Tune `MCP_ARTIFACT_FULL_SIZE_LIMIT`** (default 500 MB) against your storage budget. Below this threshold, full artifacts are published; above it, auto-delta kicks in.
- [ ] **Tune `MCP_WATCHER_SWEEP_MINUTES`** (default 60) and `MCP_WATCHER_POLL_SECONDS` (inherited default) based on expected event-drop frequency. Slow filesystems or high-churn repos benefit from lower sweep intervals.
- [ ] **Stage schema migration in a non-prod environment first.** P14 SL-3 runs migrations on startup; a prod outage during migration is possible. Verify in staging, then roll the phase to prod.

### 3.4 Phase 15 — Security Hardening

#### Before P15

- [ ] **Enable SLSA attestations for GitHub Actions artifacts.** Navigate to `Settings → Actions → General → Artifact attestations` and flip the toggle. Required by SL-3's signing flow.
- [ ] **Extend `GITHUB_TOKEN` scope** to include `attestations:write` (required by SL-3).
- [ ] **Pick plugin-trust policy.** SL-1 implements plugin sandboxing; the default posture depends on your threat model. Options:
  1. **First-party only.** Only plugins shipped with the repo are loaded; no external plugins. Safest, least flexible.
  2. **Signed third-party.** External plugins must be signed by a trusted key. Requires a signing-key management story (out of scope for P15; decide if/when).
  3. **Fully sandboxed untrusted.** Any plugin can load, but execution is confined by the SL-1 sandbox. Most flexible.
  Pick one and document. Default recommendation: posture 3 (fully sandboxed) — the sandbox is the protective boundary regardless of plugin provenance.
- [ ] **Pick `/metrics` auth posture.** SL-2 supports two modes:
  1. **Bearer token.** Metrics scrape sends `Authorization: Bearer <token>`. Simple; works anywhere Prometheus runs.
  2. **NetworkPolicy (k8s).** Metrics port is only reachable from the Prometheus pod selector. No app-level auth.
  Pick one and document. Default recommendation: NetworkPolicy if deploying to k8s; bearer token otherwise.

#### Operationalization subsections

**SL-1 plugin-trust posture operationalization**:
- Plugin sandboxing is controlled by `MCP_PLUGIN_SANDBOX_ENABLED=1` (default off in P15).
- When enabled, all plugins run in isolated worker processes communicating via JSON-line IPC over stdin/stdout.
- Per-plugin capability restrictions can be set via `PluginFactory.create_plugin(..., capabilities=CapabilitySet(...))`.
- Three recommended postures:
  1. **No sandbox (default)**: Plugins run in-process; fastest but least safe.
  2. **Sandbox with default caps**: All plugins run in workers; default `CapabilitySet` allows SQLite only.
  3. **Locked-down per-plugin**: Each plugin gets custom capability set (e.g., Go plugin granted `subprocess`, others locked down).
- For production deployments, set `MCP_PLUGIN_SANDBOX_ENABLED=1`.

**SL-2 bearer-vs-NetworkPolicy decision matrix**:
- `/metrics` endpoint now requires authentication (`Depends(require_auth("metrics"))` → `Permission.ADMIN`).
- Two deployment postures:
  1. **App-level bearer token (A)** (recommended): Clients send `Authorization: Bearer <token>` to `/metrics`. Uses existing `GITHUB_TOKEN` or a derived metrics-only token. Works anywhere Prometheus runs.
  2. **Network-policy restriction (B)**: Metrics port is only reachable from the Prometheus pod selector (k8s only). Requires Prometheus to be in the same namespace or behind a service mesh. Requires disabling the `/metrics` scope requirement (revert the scope check).
- Default for new deployments: **Bearer token (A)**. For k8s + existing NetworkPolicy: **NetworkPolicy (B)**.

**SL-3 `MCP_ATTESTATION_MODE` trinary**:
- Artifact attestation mode controlled by environment variable:
  - **`enforce`** (default, production): Raises error on sign or verify failure; deployment will not start. Safest.
  - **`warn`**: Logs warning on failure; continues. Graceful degradation.
  - **`skip`**: No attestation checking. Use for air-gapped environments without GitHub connectivity.
- Required: `GITHUB_TOKEN` must include `attestations:write` scope.
- Required: `gh` CLI must be installed and support `attestation` subcommand (GitHub CLI ≥ recent version).
- Verify with: `gh attestation --help`.

**SL-4 `MCP_ALLOWED_ROOTS` + `MCP_REQUIRE_TOKEN_SCOPES` guidance**:
- **Path traversal guard**: `MCP_ALLOWED_ROOTS` is an `os.pathsep`-separated list of absolute paths (`:` on Unix, `;` on Windows). Unset → guard is a no-op. Recommended for production: set to the list of all indexed repo roots.
- **Token scope validation**:
  - Five required scopes: `contents:read, metadata:read, actions:read, actions:write, attestations:write`.
  - `TokenValidator.validate_scopes(required)` fires at startup.
  - Default behavior: soft-skip (WARN log if token unset or scopes missing).
  - Hard-fail mode: set `MCP_REQUIRE_TOKEN_SCOPES=1` to raise error at startup.
  - Verify token scopes: `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | grep X-OAuth-Scopes` or `gh auth status`.

#### After P15 merge

- [ ] **Rotate `GITHUB_TOKEN`** and verify scopes via the new `TokenValidator` at startup. If `TokenValidator` emits missing-scope errors, the deployment will refuse to start — this is intentional fail-loud behavior.
- [ ] **Add alerting on path-traversal-guard rejections + attestation-verify failures.** Either event should be rare and indicates either a bug or an attack. Page-worthy.
- [ ] **Verify attestation-enabled download path in staging.** Sign a test artifact, download it, confirm the verify step passes. Then deliberately corrupt an artifact and confirm verify rejects it.

---

## 4. Ongoing operations

- **Token rotation cadence.** 90 days recommended for `GITHUB_TOKEN`. Automation: configure a scheduled job to rotate via a credential manager (1Password, Vault, GitHub OIDC → short-lived tokens).
- **Schema version deprecation.** Follow the policy picked before P14. When you drop support for an old version, commit a test that proves the migrator refuses to load it.
- **Artifact retention eviction.** Either use GitHub's retention controls (set in step 3.1) or run an explicit cleanup job. The `latest` pointer is always preserved; only historical SHA-addressed artifacts get evicted.
- **Alerting rules template.** After P13 merge, populate a monitoring-config file with alerts on:
  - `rate(mcp_errors_by_type_total[5m]) > N`
  - `histogram_quantile(0.99, rate(mcp_symbol_lookup_duration_seconds_bucket[5m])) > N`
  - `mcp_dispatcher_fallback_duration_seconds_count{outcome="timeout"} > 0` (from P11)
  - Health probe 503 for >1 minute.
- **Plugin-trust posture review.** If you picked "fully sandboxed untrusted" in P15, re-audit the sandbox's capability set every 6 months — kernel syscall surface changes over time.

---

## 5. Incremental rollout guide

**Do not ship P12–P15 as a single big-bang deploy.** Recommended cadence:

1. **Merge and ship P12.** Collect probe behavior + histogram metrics for ~2 weeks. Specifically watch for: probe flapping (suggests a health check is too tight), reindex-lock contention (suggests lock granularity is wrong), and histogram bucket saturation (latency alerting thresholds need adjusting).
2. **Merge and ship P13.** Verify direct-publish latency (reindex-done → artifact-available < 2 min) and exception-counter signal for 2 weeks. Watch for: race-loss artifacts (commit-SHA addressable but not latest), checkpoint-resume correctness on simulated crashes, and any surprising `PluginError` or `ArtifactError` spikes.
3. **Merge and ship P14.** Verify schema migration behavior in staging before prod flip. Watch for: migration failures on edge-case schemas, reranker latency additions (can add 100–500 ms per query depending on provider), dependency-graph incorrect resolution for repos with unusual dep files.
4. **Merge and ship P15.** Plugin sandboxing is the biggest single risk — consider a canary repo (one low-traffic repo using a known-good plugin set) before fleet rollout. Watch for: sandbox IPC overhead, legitimate plugins rejected by the sandbox's capability set, attestation-verify false-negatives on corrupted-during-transit artifacts.

Between phases, expect ~1 week for observation + policy calibration. The entire arc (P12→P15) realistically ships over 6–8 weeks including observation windows.

---

## 6. Emergency rollback

Each phase is an independent git commit range; `git revert` of a phase's merge commits restores the prior behavior. Concrete rollback notes:

- **P12 SL-5 (freshness gate)** — if rollback, clients downloading older artifacts may use stale indexes silently. Mitigation: override via `MCP_SKIP_FRESHNESS_CHECK=1` temporarily.
- **P13 SL-4 (direct publish)** — if rollback, re-enable the cron upload workflow you retired.
- **P13 SL-5 (exceptions)** — if rollback, the bare-except refactor is cosmetic; behavior is preserved by the typed catches. Low-risk to revert.
- **P14 SL-3 (schema migration)** — **this one cannot be cleanly rolled back.** Once a DB is migrated to schema v_{N+1}, downgrading requires restoring from pre-migration backup. Stage carefully.
- **P15 SL-1 (sandboxing)** — if rollback, plugins run in-process again (pre-P15 behavior). No data loss risk; only a security posture change. Revert freely if sandbox breaks production plugins.

---

## 7. FAQ

**Q: Can I skip P12 and go straight to P13?**
A: No. P13 SL-1 depends on P12 SL-2's `IndexingLockRegistry` (IF-0-P12-2) to serialize the resume path. P13's validator check `git merge-base --is-ancestor <P12-merge> HEAD` will fail if P12 isn't merged first.

**Q: Can I parallelize P13 and P14?**
A: No. Both edit `artifact_upload.py` and the execution-notes instruction is explicit: P13 SL-4 must merge before P14 SL-4 starts.

**Q: Do I need Qdrant for P13?**
A: Only if you have semantic indexing enabled. If `PROMETHEUS_AVAILABLE=False`-style gating applies (Qdrant optional), the two-phase-commit helper short-circuits the Qdrant side and SQLite updates proceed normally. Document your posture in the alerting template.

**Q: What if I don't use GitHub Artifacts?**
A: Then P13 SL-4 and P15 SL-3 become partial no-ops. The freshness gate (P12 SL-5), the rate limiter (P15 SL-4), and the token validator (P15 SL-4) still apply to any HTTP-based artifact retrieval. Consider splitting off the GitHub-specific lanes for your deployment.
