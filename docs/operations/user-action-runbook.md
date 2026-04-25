# User Action Runbook — P12 through P26

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
- Plugin sandboxing is default-on as of P18/P24. Set
  `MCP_PLUGIN_SANDBOX_DISABLE=1` only for trusted environments that need
  unsandboxed generic parsing.
- When enabled, sandbox-supported plugins run in isolated worker processes
  communicating via JSON-line IPC over stdin/stdout.
- Per-plugin capability restrictions can be set via `PluginFactory.create_plugin(..., capabilities=CapabilitySet(...))`.
- Use the MCP `list_plugins` tool to audit `plugin_availability` before rollout.
  Expected states are `enabled`, `unsupported`, `missing_extra`, `disabled`, and
  `load_error`. Registry-only languages without hardened sandbox modules are
  `unsupported` and skipped quietly; optional extras such as Java's `javalang`
  are `missing_extra` with remediation.
- Three recommended postures:
  1. **Sandbox with default caps (default)**: Hardened plugins run in workers; unsupported registry-only languages are visible in `list_plugins`.
  2. **Locked-down per-plugin**: Each plugin gets custom capability set (e.g., Go plugin granted `subprocess`, others locked down).
  3. **Trusted unsandboxed opt-out**: Plugins run in-process; fastest but least safe.
- For production deployments, keep the default sandbox posture and alert on
  `load_error` availability rows.

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

### 3.5 Phase 25 - Blocking Release Gates & Automation

#### Before P25

- [ ] **Confirm GitHub artifact attestations are enabled.** Navigate to
  `Settings -> Actions -> General -> Artifact attestations` and keep the
  repository setting enabled before relying on authenticated attestation tests.
- [ ] **Provision `ATTESTATION_GH_TOKEN` only where appropriate.** The token must
  be stored as a GitHub Actions secret and have the repository access required
  by `tests/security/test_artifact_attestation.py`. Do not expose it to
  contributor pull requests.
- [ ] **Decide private-alpha fallback posture.** If `ATTESTATION_GH_TOKEN` or the
  repository attestation setting is unavailable, the authenticated attestation
  job must remain private-alpha informational skipped/warn. It must not silently
  pass and must not block contributor PRs.

#### After P25 merge

- [ ] **Require the public alpha gate set before release evidence is accepted.**
  The required jobs are `Alpha Gate - Dependency Sync`,
  `Alpha Gate - Format And Lint`, `Alpha Gate - Unit And Release Smoke`,
  `Alpha Gate - Integration Smoke`, `Alpha Gate - Production Multi-Repo Matrix`,
  `Alpha Gate - Docker Build And Smoke`, `Alpha Gate - Docs Truth`, and
  `Alpha Gate - Required Gates Passed`.
- [ ] **Verify release automation refuses early.** Before approving a release
  workflow run, confirm `preflight-release-gates` completed before
  `prepare-release`; version mutation, branch creation, artifact build, tag
  creation, GitHub release creation, PyPI publish, and container publish must
  remain downstream of that gate. Confirm `make release-smoke-container` ran in
  preflight before approving manual dispatch, or that release automation
  preflight ran it after `make alpha-release-gates`.
- [ ] **Record informational leftovers explicitly.** Cross-platform tests,
  authenticated attestation tests without `ATTESTATION_GH_TOKEN`, benchmarks,
  vulnerability scans, cleanup, signing, and publish-only container manifest work
  are informational for private alpha unless promoted by a later phase.

### 3.5A Phase GAGOV - Enforced Release Governance

#### Before GAGOV

- [ ] **Probe live repository governance with metadata-only GitHub CLI calls.**
  Record only redacted metadata in `docs/validation/ga-governance-evidence.md`:
  `gh repo view ViperJuice/Code-Index-MCP --json nameWithOwner,defaultBranchRef,visibility`,
  `gh api repos/ViperJuice/Code-Index-MCP/branches/main --jq '{name, protected, protection_url}'`,
  `gh api repos/ViperJuice/Code-Index-MCP/branches/main/protection`, and
  `gh api repos/ViperJuice/Code-Index-MCP/rulesets`.
- [ ] **Freeze the exact GABASE gate contexts.** GAGOV must enforce only:
  `Alpha Gate - Dependency Sync`,
  `Alpha Gate - Format And Lint`,
  `Alpha Gate - Unit And Release Smoke`,
  `Alpha Gate - Integration Smoke`,
  `Alpha Gate - Production Multi-Repo Matrix`,
  `Alpha Gate - Docker Build And Smoke`,
  `Alpha Gate - Docs Truth`, and
  `Alpha Gate - Required Gates Passed`.
- [ ] **Keep the release channel split explicit.** `v1.2.0-rc5` remains the
  active RC/public-alpha contract, GitHub Latest currently points at
  `v2.15.0-alpha.1`, `auto_merge=false` remains the RC default, and Docker
  latest remains stable-only until a final GA release changes those channels.

#### After GAGOV

- [ ] **Verify the enforced governance posture is still live.** As of
  2026-04-24, `main` is enforced via branch protection with strict status
  checks, `1 approving review`, stale-review dismissal, conversation
  resolution, linear history, and administrator enforcement. No repository
  rulesets are configured; branch protection is the active enforcement surface.
- [ ] **Preserve the historical baseline.** Earlier RELGOV/GACLOSE evidence
  captured manual enforcement before GAGOV applied live protection. Keep that
  wording as input evidence, but treat
  `docs/validation/ga-governance-evidence.md` as the canonical post-GAGOV
  artifact.
- [ ] **Escalate drift immediately.** If a later probe shows branch protection
  drift, a missing required gate context, or a GitHub product limit that weakens
  enforcement, stop release qualification, refresh
  `docs/validation/ga-governance-evidence.md`, and route the blocker through
  GAGOV/GAOPS before GARC dispatches another RC.

### 3.6 Phase 26 - Private Alpha Evidence & Public Alpha Decision

#### Before P26

- [ ] **Select the private-alpha fixture set.** The local config must cover
  exactly `python_repo`, `typescript_js_repo`, `mixed_docs_code_repo`,
  `multi_repo_workspace`, and `large_ignored_vendor_repo`.
- [ ] **Keep fixture details local.** Store private paths, repository names,
  source expectations, and operator notes in a local config file that is not
  committed. Raw harness output belongs only under ignored
  `private-alpha-evidence/`.
- [ ] **Confirm P21-P25 required gates are green.** Any required gate failure
  blocks public alpha before P26 evidence is considered.

#### During P26

- [ ] **Run the evidence harness.**
  ```bash
  uv run python scripts/private_alpha_evidence.py \
    --config <private-config.json> \
    --output-dir private-alpha-evidence/<run-id> \
    --redacted-md docs/validation/private-alpha-decision.md \
    --redacted-json docs/validation/private-alpha-decision.json
  ```
- [ ] **Review redaction before committing.** The committed decision files must
  contain fixture categories, aggregate timings, pass/fail classifications, and
  issue IDs only. Do not commit private names, absolute paths, source excerpts,
  or raw logs.
- [ ] **Classify every known issue.** Use exactly `public_alpha_blocker`,
  `documented_limitation`, or `post_alpha_backlog`.

#### After P26

- [ ] **Record the final go/no-go decision.** The redacted decision artifact is
  `docs/validation/private-alpha-decision.md`, and the decision must be exactly
  `go`, `no_go`, or `conditional_go`.
- [ ] **Escalate blockers narrowly.** Any P26 `public_alpha_blocker` or required
  P21-P25 gate failure blocks public alpha and should become a targeted follow-up
  roadmap item.
- [ ] **Close non-blockers explicitly.** A `go` decision requires all remaining
  non-blocking issues to be captured as `documented_limitation` or
  `post_alpha_backlog`.

### 3.7 Phase 34 - Public Alpha Recut

#### Before P34

- [ ] **Confirm P33 is green.** `make alpha-production-matrix` must pass before
  public-alpha release evidence is accepted.
- [ ] **Choose and freeze the prerelease tag.** For this recut the selected tag
  is `v1.2.0-rc5`; confirm `git tag -l v1.2.0-rc5` does not show a reused local
  tag unless it points at the release commit.
- [ ] **Review public limitations.** Customer docs must state that v3 supports
  many unrelated repositories, one registered worktree per git common directory,
  tracked/default branch indexing only, and readiness-gated MCP search.

#### During P34

- [ ] **Run the clean-checkout release verification set.**
  ```bash
  uv run pytest tests/smoke tests/docs tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
  make alpha-production-matrix alpha-release-gates
  make release-smoke release-smoke-container
  ```
- [ ] **Validate fail-closed fallback language.** Public docs and agent handoffs
  must tell users that `index_unavailable` plus
  `safe_fallback: "native_search"` means use native search or follow the
  returned readiness remediation until readiness is `ready`.
- [ ] **Keep raw/local evidence out of git.** Commit only redacted release
  decision artifacts and documentation updates.

#### After P34

- [ ] **Approve public alpha only with explicit evidence.** Docs truth,
  release metadata, clean-checkout wheel/container smoke, P27-P33 gates, and the
  support matrix must all match the `1.2.0-rc5` public-alpha contract.

### 3.8 Phase RELGOV - Release Governance and Channel Policy

#### Before RELGOV

- [ ] **Probe GitHub enforcement before accepting release evidence.** Check
  branch protection for `main`, repository rulesets, the current GitHub Latest
  release, and release `v1.2.0-rc5`. If branch protection and rulesets remain
  absent, public-alpha required gates use manual enforcement.

#### During RELGOV

- [ ] **Accept the required gate authority.** The required public-alpha gates
  are `Alpha Gate - Dependency Sync`, `Alpha Gate - Format And Lint`,
  `Alpha Gate - Unit And Release Smoke`, `Alpha Gate - Integration Smoke`,
  `Alpha Gate - Production Multi-Repo Matrix`,
  `Alpha Gate - Docker Build And Smoke`, `Alpha Gate - Docs Truth`, and
  `Alpha Gate - Required Gates Passed`.
- [ ] **Record branch protection and ruleset disposition.** If `main` remains
  without branch protection and repository rulesets remain empty, record that
  manual enforcement is accepted by the repository operator for public alpha.
- [ ] **Record the release-channel decision.** `v1.2.0-rc5` is the active
  RC/public-alpha package contract. GitHub Latest currently points at
  `v2.15.0-alpha.1`, and GitHub Latest is not the RC policy source unless a
  later release operation deliberately changes channel state.
- [ ] **Keep release automation in RC posture.** The release workflow treats
  hyphenated versions as prereleases, requires `release_type=custom` for
  prerelease tags, publishes Docker latest only for stable releases, and keeps
  `auto_merge=false` as the RC default.
- [ ] **Keep the GA decision singular.** Stay on RC/public-alpha until RC5
  release evidence, RELGOV evidence, TOOLRDY evidence, and GACLOSE acceptance
  justify GA hardening or another follow-up RC.
- [ ] **Choose one GACLOSE outcome.** Record exactly one of
  `stay on RC/public-alpha`, `cut a follow-up RC`, or `start a GA hardening
  roadmap` in `docs/validation/ga-closeout-decision.md`; do not add GA launch
  instructions while manual enforcement is the public-alpha governance posture.

#### After RELGOV

- [ ] **Attach release-governance evidence to GACLOSE.** Use
  `docs/validation/release-governance-evidence.md` as the governance input for
  GACLOSE, alongside `docs/validation/rc5-release-evidence.md` and
  `docs/validation/secondary-tool-readiness-evidence.md`.
- [ ] **Record post-TOOLRDY verification.** Rerun `make alpha-production-matrix`
  and attach the result to `docs/validation/ga-closeout-decision.md` before any
  follow-up release or GA-hardening roadmap decision.

### 3.9 Phase GABASE - GA Criteria Freeze

#### Before GABASE

- [ ] **Use the canonical checklist as the contract source.** Freeze the GA
  release boundary, support tiers, required gates, evidence map, rollback
  expectations, and non-GA surfaces in
  `docs/validation/ga-readiness-checklist.md` before changing governance,
  support claims, release execution, or operations posture.
- [ ] **Keep the support-tier labels shared.** Use exactly `public-alpha`,
  `beta`, `GA`, `experimental`, `unsupported`, and `disabled-by-default` across
  the checklist, `docs/SUPPORT_MATRIX.md`, and the operator runbooks.
- [ ] **Keep the v3 topology limits explicit.** Preserve many unrelated
  repositories, one registered worktree per git common directory,
  tracked/default branch indexing only, and `index_unavailable` with
  `safe_fallback: "native_search"` until readiness is `ready`.

#### During GABASE

- [ ] **Classify current evidence as input evidence.** Use
  `docs/validation/rc5-release-evidence.md`,
  `docs/validation/release-governance-evidence.md`,
  `docs/validation/secondary-tool-readiness-evidence.md`, and
  `docs/validation/ga-closeout-decision.md` as the carried-forward
  RC/public-alpha baseline.
- [ ] **Map refresh evidence to downstream owners.** Reserve
  `docs/validation/ga-governance-evidence.md` for `GAGOV`,
  `docs/validation/ga-e2e-evidence.md` for `GAE2E`,
  `docs/validation/ga-operations-evidence.md` for `GAOPS`,
  `docs/validation/ga-rc-evidence.md` for `GARC`, and
  `docs/validation/ga-final-decision.md` plus
  `docs/validation/ga-release-evidence.md` for `GAREL`.
- [ ] **Freeze the follow-up RC target.** GARC should plan around
  `v1.2.0-rc8` unless a later roadmap amendment changes that contract.
- [ ] **Keep governance in manual enforcement posture.** GABASE does not change
  branch protection, rulesets, release dispatch, or GA claims.

### 3.10 Phase GAOPS - GA Operational Readiness

#### Before GAOPS

- [ ] **Use the canonical GA artifacts as inputs.** GAOPS consumes
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`, and
  `docs/validation/ga-e2e-evidence.md`; it does not replace them with a new
  release decision.
- [ ] **Keep the local-first boundary explicit.** Operators still own repo
  registration, one registered worktree per git common directory, allowed-roots
  policy, tracked/default branch indexing, readiness remediation, and support
  triage.
- [ ] **Use the exact preflight invocation.** Run
  `./scripts/preflight_upgrade.sh /path/to/staging.env` before qualification.

#### During GAOPS

- [ ] **Record GAOPS evidence in one place.** Use
  `docs/validation/ga-operations-evidence.md` as the canonical GAOPS artifact.
- [ ] **Keep observability evidence-backed.** `/metrics` verification uses the
  authenticated admin path, JSON-log validation, and response-redaction checks
  from `docs/operations/observability-verification.md`; warnings or posture
  notes are `metadata-only`, while the smoke test remains `CI`.
- [ ] **Freeze the operator procedure set.** GAOPS must define deployment
  preflight, deployment qualification, rollback, index rebuild, incident
  response, and support triage without implying a hosted service. Keep
  incident response and support triage operator-owned.

#### After GAOPS

- [ ] **Route downstream release work through the refreshed ops artifact.**
  GARC and GAREL must consume `docs/validation/ga-operations-evidence.md`
  instead of relying on older runbook assumptions.
- [ ] **Escalate contract drift before RC dispatch.** If operator procedures,
  readiness vocabulary, or observability posture drift, stop and route the
  blocker through GAOPS before GARC dispatches the follow-up RC.

### 3.11 Phase GARC - Follow-Up RC Soak

#### Before GARC

- [ ] **Freeze the `rc8` contract surfaces first.** `pyproject.toml`,
  `mcp_server/__init__.py`, `.github/workflows/release-automation.yml`,
  `CHANGELOG.md`, customer docs, installer helpers, and
  `tests/test_release_metadata.py` must all agree on `v1.2.0-rc8` before any
  release dispatch is attempted.
- [ ] **Require a clean release candidate state.** Run
  `git status --short --branch`; if the worktree is dirty, stop and record
  `blocked before dispatch` in `docs/validation/ga-rc-evidence.md`.
- [ ] **Verify branch and tag qualification.** Run
  `git fetch origin main --tags --prune`,
  `git rev-parse HEAD origin/main`,
  `git tag -l v1.2.0-rc8`, and
  `git ls-remote --tags origin refs/tags/v1.2.0-rc8`.
- [ ] **Require fresh upstream evidence.** Treat
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`, and
  `docs/validation/ga-operations-evidence.md` as the required upstream inputs.

#### During GARC

- [ ] **Confirm release-workflow visibility before dispatch.** Run
  `gh workflow view "Release Automation"` and record only metadata.
- [ ] **Dispatch with the frozen RC policy.** Use exactly
  `gh workflow run "Release Automation" -f version=v1.2.0-rc8 -f release_type=custom -f auto_merge=false`.
- [ ] **Observe the workflow to completion.** Record
  `gh run list --workflow "Release Automation" --limit 10`,
  `gh run watch <run-id> --exit-status`,
  `gh run view <run-id> --json url,headSha,status,conclusion,jobs`, and
  `gh release view v1.2.0-rc8 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets`.
- [ ] **Keep the channel split explicit.** `v1.2.0-rc8` remains prerelease
  public-alpha/beta posture, `auto_merge=false` stays the default, GitHub
  Latest remains excluded from the RC policy source, and Docker `latest`
  remains stable-only.

#### After GARC

- [ ] **Reduce the run into one canonical artifact.** Use
  `docs/validation/ga-rc-evidence.md` to record pre-dispatch checks, dispatch
  inputs, workflow URL or run ID, artifact identities, release-channel state,
  and rollback disposition using redacted metadata only.
- [ ] **Do not imply GA readiness from a blocked or failed soak.** If dispatch
  did not happen or the workflow failed, state that explicitly and keep GA
  release work blocked until GARC is rerun successfully.

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
