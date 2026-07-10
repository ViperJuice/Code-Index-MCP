# Phase roadmap v10

## Context

This roadmap closes the confirmed defects from the 2026-07-10 repository-wide
review of Code-Index-MCP. The review covered the FastAPI admin surface, stdio MCP
tools, multi-repository routing, readiness classification, summarization,
sandboxed plugin lifecycle, tests, local CI, packaging, and release automation.

The confirmed defects are:

1. An arbitrary non-empty bearer token can become an all-permission admin user.
2. Unknown repository names and IDs can resolve to the server's current repo.
3. The MCP `reindex` tool refuses the non-ready states it tells users to repair.
4. Corrupt or provenance-less SQLite indexes can be classified `ready`.
5. `summarize_sample` treats `SummaryGenerationResult` as an iterable and fails.
6. The checked-out test, format, lint, and type-quality surfaces are not green.
7. Plugin subprocesses scale with repositories times languages while child RSS
   is outside the configured memory budget and shutdown ownership is incomplete.
8. Status can report semantic indexing active while semantic health is unavailable.
9. Release automation can tag and publish before the release branch reaches `main`.
10. The container scan executes the mutable `aquasecurity/trivy-action@master`.

The implementation branch starts from `origin/main` at the prepared `1.3.0`
surface. This is a bug-fix and hardening roadmap. It prepares `1.3.1`, but release
dispatch remains a separate operator action after merge.

The three-agent review returned `PARTIALLY AGREE` from GPT-5.5, Gemini 3.1 Pro
(High), and Fable. Required amendments are reconciled in
`specs/phase-plans-v10_reviews.md`; this amended roadmap is implementation-ready.

## Architecture North Star

Code-Index-MCP must fail closed at every authority boundary:

```text
admin request -> validated JWT -> explicit role/permission authorization
MCP request   -> exact registered repository identity -> readiness verdict
reindex       -> permitted recovery state -> atomic index/provenance update
query         -> validated ready index -> authoritative result
plugin use    -> lazy sandbox worker -> child-aware budget -> deterministic close
release       -> merged main commit -> tag -> attest -> publish
```

STDIO remains the primary MCP interface. FastAPI remains a secondary admin and
diagnostic surface. Repository names, IDs, and paths must resolve through the
registry without current-working-directory fallback. Readiness must distinguish
recoverable state from unsafe state. Tests and status surfaces must report the
same contracts operators actually receive.

## Assumptions

- `origin/main` is the implementation base and currently reports version `1.3.0`.
- The review reproductions are valid until a phase test proves otherwise.
- Registered repository names, stable IDs, and registered filesystem paths are
  supported selectors; git URLs are not promised unless an exact registered
  mapping is implemented and tested.
- Reindex may recover `missing_index`, `index_empty`, and `stale_commit` states,
  plus corrupt, missing-schema, or missing-provenance state only through an
  explicit quarantine-and-rebuild mode.
- Reindex must continue refusing unsupported worktrees, wrong branches, active
  builds, path-sandbox violations, and unregistered repositories.
- No broad fleet indexing is required to prove these fixes.
- Existing local/offloaded CI conventions are reused; hosted GitHub Actions cost
  must not increase.
- Review-class panel seats are GPT-5.5, Gemini 3.1 Pro, and Fable.

## Non-Goals

- No PMCP code changes in this repository.
- No broad semantic-index rebuild or fleet registration.
- No change from STDIO-primary to a remote MCP transport.
- No plugin-language feature expansion.
- No external release dispatch, PyPI publish, GitHub release, or merge from this
  roadmap. Phase 7 prepares a releasable `1.3.1` branch only.
- No weakening or deletion of valid tests merely to make gates green.

## Cross-Cutting Principles

- Reject ambiguity instead of guessing from process CWD.
- Reject corrupt or unproven index state instead of serving it as authoritative.
- Keep authentication validation and authorization policy separate and test both.
- Make recovery mutations explicit, state-scoped, atomic, and observable.
- Keep unit tests hermetic; external inference and Qdrant calls require explicit
  integration markers or injected fakes.
- Count sandbox child processes and child RSS in resource policy.
- Use one local validation vocabulary in developer workflows and CI.
- Preserve exact command output and browser evidence without recording secrets.
- Route any failed final gate back to its owning phase; do not waive it in closeout.
- Capture one failing-at-base reproduction for every finding before implementing
  its fix, then record that exact regression passing in phase closeout evidence.
- Until QUALITY removes the known red baseline, every earlier phase must run its
  scoped tests plus the frozen baseline comparison and introduce no new failures.

## Findings-To-Gates Matrix

| Finding | Owner phase | IF gate | Regression test/evidence | Refusal or recovery behavior | Closeout artifact |
|---|---|---|---|---|---|
| F1 arbitrary bearer becomes admin | AUTHBOUND | IF-0-AUTHBOUND-1/-2 | `tests/security/test_auth_boundary.py` | invalid auth is `401`/`403`; missing signing config fails closed | AUTHBOUND `verification.json` |
| F2 repository selector misroutes | REPOSEL | IF-0-REPOSEL-1/-2 | `tests/test_repo_resolver.py`, multi-repo integration | unknown or ambiguous selector is a typed refusal | REPOSEL `verification.json` |
| F3 reindex refuses remediation | READYREC | IF-0-READYREC-2 | `tests/test_tool_readiness_fail_closed.py` | recoverable states rebuild; unsafe states refuse | READYREC `verification.json` |
| F4 corrupt/provenance-less index is ready | READYREC | IF-0-READYREC-1/-2 | `tests/test_repository_readiness.py` | fail closed, quarantine, then explicit rebuild | READYREC `verification.json` |
| F5 summarize result mismatch | SUMCONTRACT | IF-0-SUMCONTRACT-1 | `tests/test_summarization.py`, multi-repo integration | one typed result, including zero summaries | SUMCONTRACT `verification.json` |
| F6 quality gates are red | QUALITY | IF-0-QUALITY-1/-2 | full gate outputs and type census | no waiver; zero or frozen shrinking type debt | QUALITY `verification.json` |
| F7 plugin worker/resource growth | PLUGLIFE | IF-0-PLUGLIFE-1/-2 | worker-budget and process-death tests | LRU/backpressure, repo close, parent-death reaping | PLUGLIFE `verification.json` |
| F8 semantic status contradicts health | READYREC | IF-0-READYREC-3 | status tests with unavailable backend | active false with typed unavailable reason | READYREC `verification.json` |
| F9 publish occurs before merge | RELEASESAFE | IF-0-RELEASESAFE-1 | workflow-policy tests | preparation stops; publish requires in-job main proof | RELEASESAFE `verification.json` |
| F10 mutable Trivy action | RELEASESAFE | IF-0-RELEASESAFE-2 | workflow action-pin policy test | mutable third-party action refs fail CI | RELEASESAFE `verification.json` |

## Top Interface-Freeze Gates

- IF-0-AUTHBOUND-1 - Every FastAPI protected route accepts only a validated,
  unexpired JWT and never synthesizes an administrator from header presence.
- IF-0-AUTHBOUND-2 - Security middleware and dependencies are configured before
  application startup; late registration cannot be swallowed as success.
- IF-0-REPOSEL-1 - Repository selectors resolve exact registered ID, exact
  registered name, or registered path; unknown selectors return a typed refusal.
- IF-0-REPOSEL-2 - Selector resolution never climbs from a nonexistent relative
  path into the server's current git repository.
- IF-0-READYREC-1 - Missing, empty, corrupt, provenance-less, stale, wrong-branch,
  active-build, and ready indexes have distinct fail-closed readiness verdicts.
- IF-0-READYREC-2 - Reindex is permitted only for explicitly recoverable states
  and atomically records successful index/provenance state.
- IF-0-READYREC-3 - Status feature flags are computed from usable runtime
  capability and agree with component health.
- IF-0-SUMCONTRACT-1 - `summarize_file_chunks` has one typed return contract that
  carries generated summaries and counters without list/result ambiguity.
- IF-0-PLUGLIFE-1 - `MemoryAwarePluginManager` is the sole worker lifecycle owner;
  plugin registries delegate create, repo eviction, resource snapshot, and shutdown.
- IF-0-PLUGLIFE-2 - Workers load lazily, child RSS and worker count participate in
  deterministic budgets, and workers do not outlive graceful or killed parents.
- IF-0-QUALITY-1 - Required unit, integration, documentation, format, lint, and
  release-smoke gates pass from a clean locked environment.
- IF-0-QUALITY-2 - Phase-owned production modules type-check at zero errors and
  any bounded legacy baseline is enumerated, enforced, and allowed only to shrink.
- IF-0-RELEASESAFE-1 - No workflow can tag, release, or publish a commit that is
  not already reachable from protected `main`.
- IF-0-RELEASESAFE-2 - Third-party workflow actions are immutable and the prepared
  package, docs, changelog, and runtime version agree on `1.3.1`.
- IF-0-HARDVERIFY-1 - Browser, MCP stdio, multi-repo recovery, worker lifecycle,
  package, and full local quality evidence all pass in one clean closeout.

## Phases

### Phase 1 — FastAPI Authentication Boundary (AUTHBOUND)

**Objective**

Remove the synthetic-admin fallback and make FastAPI authentication fail closed
under real application startup and TestClient startup.

**Exit criteria**

- [ ] Security middleware or equivalent validated-token dependencies are wired
      before startup and cannot hit Starlette's late-registration error.
- [ ] Missing, malformed, invalid-signature, expired, and unknown-user bearer
      tokens receive `401` or `403` as appropriate.
- [ ] A valid token receives only its declared role and permissions.
- [ ] No code path creates `fallback-user`, grants `ADMIN`, or grants every
      permission based only on a non-empty `Authorization` header.
- [ ] Missing or invalid JWT signing configuration fails application startup or
      makes protected routes unavailable; it never selects a permissive mode.
- [ ] A route-inventory test walks every FastAPI route and proves all routes outside
      an explicit public allowlist reject unauthenticated requests.
- [ ] Tests cover forged signatures, wrong/none algorithm, missing subject, unknown
      user, expiry, and a low-privilege token attempting a mutation.
- [ ] Tests cover protected read and mutation endpoints, including `/metrics`,
      `/reindex`, cache/config mutations, and plugin administration.
- [ ] API tests assert OpenAPI auth metadata; browser smoke proves `/docs` renders
      and visibly receives an unauthorized response on a protected operation.

**Scope notes**

Plan this phase with at least 2 lanes: application/auth wiring and adversarial
API/browser tests. Prefer existing `AuthenticationManager` and permission
dependencies over a parallel authentication stack.

**Non-goals**

- No redesign of STDIO `MCP_CLIENT_SECRET` handshake behavior.
- No external identity provider integration.

**Key files**

- `mcp_server/gateway.py`
- `mcp_server/security/security_middleware.py`
- `mcp_server/security/authentication.py`
- `tests/conftest.py`
- `tests/security/**`
- `tests/test_gateway*.py`
- `docs/security/**`

**Depends on**

- (none)

**Produces**

- IF-0-AUTHBOUND-1 - Validated JWT-only protected routes.
- IF-0-AUTHBOUND-2 - Pre-startup security wiring.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: canonical_spec_update
- target_surfaces: FastAPI authentication contract and security docs
- evidence_paths: targeted API tests, OpenAPI/browser smoke, auth diff
- redaction_posture: metadata_only
- blocker_class: contract_bug for any remaining synthetic or late auth path

### Phase 2 — Exact Repository Selection (REPOSEL)

**Objective**

Replace path-shaped guessing with one canonical selector resolver for repository
ID, registered name, and registered path.

**Exit criteria**

- [ ] A shared resolver accepts exact repository ID, exact registered name, or a
      filesystem path that belongs to the registered checkout.
- [ ] Resolution precedence is exact ID, then exact registered name, then
      canonicalized path; collisions or residual ambiguity return a typed refusal.
- [ ] Paths use `realpath` canonicalization, preserve `MCP_ALLOWED_ROOTS`, compare
      git-common-dir identity, and reject sibling worktrees unless explicitly
      registered as the supported checkout.
- [ ] Unknown names, unknown IDs, unregistered paths, and unsupported worktrees
      return typed refusals and never fall back to the current repository.
- [ ] Tool schemas describe only selectors that are actually implemented.
- [ ] Path-shaped selectors continue enforcing `MCP_ALLOWED_ROOTS`; registered
      names do not bypass repository identity checks.
- [ ] Search, symbol, summarize, write-summary, and reindex tools use the same
      selector contract.
- [ ] Status and every repository-scoped diagnostic use the same resolver.
- [ ] Tests cover symlinks, nested paths, nonexistent relative paths, path-like repo
      names, duplicate names/IDs, and sibling worktrees.
- [ ] Two-repository tests prove selecting A cannot return results or storage from B.

**Scope notes**

Plan at least 2 lanes: canonical resolver/registry contract and MCP handler/schema
adoption with cross-repository tests. Keep auto-registration out of query tools.

**Non-goals**

- No fuzzy repository aliases.
- No implicit git clone or registration from URL input.

**Key files**

- `mcp_server/core/repo_resolver.py`
- `mcp_server/storage/repository_registry.py`
- `mcp_server/cli/tool_handlers.py`
- `mcp_server/cli/stdio_runner.py`
- `tests/test_repo_resolver.py`
- `tests/test_tool_readiness_fail_closed.py`
- `tests/integration/test_multi_repo_server.py`

**Depends on**

- AUTHBOUND

**Produces**

- IF-0-REPOSEL-1 - Exact registered selector contract.
- IF-0-REPOSEL-2 - No CWD fallback contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: canonical_spec_update
- target_surfaces: MCP tool selector schemas and multi-repo docs
- evidence_paths: resolver unit tests and two-repository integration output
- redaction_posture: metadata_only
- blocker_class: contract_bug if any handler retains independent selector guessing

### Phase 3 — Readiness, Recovery, And Status Truth (READYREC)

**Objective**

Make readiness fail closed, let reindex repair only recoverable states, and make
status claims agree with usable runtime components.

**Exit criteria**

- [ ] Corrupt SQLite, missing schema, missing provenance, empty index, stale commit,
      wrong branch, active build, missing index, and ready index classify distinctly.
- [ ] Exceptions while opening or querying an index never classify it as non-empty
      or ready.
- [ ] `reindex` can bootstrap `missing_index` and `index_empty` and refresh
      `stale_commit` without first requiring `ready`.
- [ ] Corrupt SQLite, missing schema, and missing provenance can recover only via
      explicit quarantine-and-rebuild, preserving the prior bytes for diagnosis.
- [ ] Reindex still refuses wrong branch, unsupported worktree, active indexing,
      path-sandbox violations, and unregistered repositories.
- [ ] A per-repo reindex lock rejects or serializes concurrent rebuilds.
- [ ] Reindex builds and validates a sibling temporary index, atomically replaces
      the active index, then records matching provenance; any interrupted or
      mismatched generation remains non-ready.
- [ ] Failure injection before replacement, after replacement, and before provenance
      publication proves no corrupt generation can classify as `ready`.
- [ ] Every non-ready state advertises a remediation the implementation actually
      permits, including an explicit manual path when automatic recovery is unsafe.
- [ ] Semantic feature flags report active only when a usable semantic indexer is
      available and agree with health details.

**Scope notes**

Plan at least 3 lanes: readiness classifier/storage validation, locked staged
recovery mutation, and truthful status plus regression tests. Freeze state names,
typed error codes, and the temporary-build publication protocol before implementation.

**Non-goals**

- No broad index migration.
- No automatic indexing merely because a repository is registered.

**Key files**

- `mcp_server/health/repository_readiness.py`
- `mcp_server/cli/tool_handlers.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/storage/repository_registry.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `tests/test_repository_readiness.py`
- `tests/test_tool_readiness_fail_closed.py`
- `tests/test_git_index_manager.py`
- `tests/test_handler_path_sandbox.py`

**Depends on**

- REPOSEL

**Produces**

- IF-0-READYREC-1 - Fail-closed readiness state contract.
- IF-0-READYREC-2 - State-scoped reindex recovery contract.
- IF-0-READYREC-3 - Truthful status capability contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: canonical_spec_update
- target_surfaces: readiness enum/remediation, reindex schema, status schema
- evidence_paths: readiness matrix tests and reindex transition tests
- redaction_posture: metadata_only
- blocker_class: contract_bug for ambiguous recovery or status states

### Phase 4 — Summarization Contract And Hermetic Tests (SUMCONTRACT)

**Objective**

Repair the summarization return contract and make its default tests hermetic.

**Exit criteria**

- [ ] `SummaryGenerationResult` carries immutable generated-summary items and
      counters, or an equally explicit single typed contract approved in planning.
- [ ] `summarize_sample` and write-summary paths consume that contract without
      iteration or `len()` ambiguity.
- [ ] Empty, partial, fully successful, and provider-failed result cases preserve
      counters, missing IDs, and generated items consistently.
- [ ] Summarization unit tests use injected fakes and never contact `ai:8002`,
      Qdrant, or another network service unless explicitly marked integration.
- [ ] The original TypeError reproduction fails at the base commit and the exact
      regression passes at closeout.

**Scope notes**

Decompose into 2 lanes: typed summarization result/handler adoption and hermetic
provider/storage test fixtures.

**Non-goals**

- No new summarization provider.
- No plugin lifecycle changes.

**Key files**

- `mcp_server/indexing/summarization.py`
- `mcp_server/cli/tool_handlers.py`
- `tests/test_summarization.py`
- `tests/integration/test_multi_repo_server.py`

**Depends on**

- READYREC

**Produces**

- IF-0-SUMCONTRACT-1 - Typed summarization result contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: canonical_spec_update
- target_surfaces: summarization internal API
- evidence_paths: failing-at-base reproduction and hermetic summarization tests
- redaction_posture: metadata_only
- blocker_class: contract_bug if more than one summarization return shape remains

### Phase 5 — Plugin Worker Lifecycle And Resource Governance (PLUGLIFE)

**Objective**

Make sandbox worker allocation, child memory accounting, eviction, backpressure,
and parent-death shutdown bounded for fleet use.

**Exit criteria**

- [ ] `MemoryAwarePluginManager` is the sole owner of worker creation and close,
      exposing `get_plugin`, `evict_repo`, `resource_snapshot`, and `shutdown` or
      equally explicit frozen APIs; other registries delegate lifecycle operations.
- [ ] Plugin workers are created lazily for languages actually used by a repo,
      rather than eagerly for every registered repo/language pair.
- [ ] Resource policy enforces both child-RSS and worker-count caps, documents its
      sampling method/cadence, and handles measurement failure fail closed.
- [ ] Eviction is deterministic LRU and a blocked spawn returns typed backpressure
      instead of silently exceeding budget.
- [ ] Repo eviction closes repo-owned workers and removes all strong references.
- [ ] Graceful process shutdown closes dispatcher/plugin registries and leaves no
      sandbox workers after the parent exits.
- [ ] Linux workers use parent-death signaling or a parent-pipe watchdog so SIGKILL
      or parent crash cannot leave orphan workers; other platforms use a tested
      equivalent or explicit bounded fallback.
- [ ] Tests prove count scales with used languages, fake-RSS breaches evict, idle
      workers expire, SIGTERM/SIGINT/SIGKILL leave no children, and cold-start
      latency remains bounded.

**Scope notes**

Decompose into 3 lanes: lifecycle owner/lazy allocation, resource accounting and
backpressure, and graceful/ungraceful process-death tests. Preserve sandbox
isolation and existing plugin search behavior.

**Non-goals**

- No plugin-language feature expansion.
- No removal of plugin sandboxing.

**Key files**

- `mcp_server/plugins/plugin_set_registry.py`
- `mcp_server/plugins/memory_aware_manager.py`
- `mcp_server/plugins/sandboxed_plugin.py`
- `mcp_server/plugin_sandbox/**`
- `mcp_server/cli/stdio_runner.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `tests/integration/test_sigterm_shutdown.py`
- `tests/test_multi_repo_manager.py`
- `tests/test_plugin_memory_*.py`

**Depends on**

- SUMCONTRACT

**Produces**

- IF-0-PLUGLIFE-1 - Single worker lifecycle owner contract.
- IF-0-PLUGLIFE-2 - Bounded allocation, budget, and parent-death contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: canonical_spec_update
- target_surfaces: plugin lifecycle and sandbox process contract
- evidence_paths: worker count/RSS tests and process-death evidence
- redaction_posture: metadata_only
- blocker_class: contract_bug if worker ownership or hard-kill reaping remains split

### Phase 6 — Quality Gate Recovery (QUALITY)

**Objective**

Restore deterministic tests and static quality gates without hiding real failures
or depending on live infrastructure.

**Exit criteria**

- [ ] A fresh locked environment records a current failure inventory before edits.
- [ ] Phase entry records mypy and pylint error censuses by module and error code.
- [ ] All deterministic failures in unit, integration, documentation, schema,
      rename, dispatcher, multi-repo, and summarization tests are fixed.
- [ ] Default unit tests make no unmarked network calls and have bounded timeouts.
- [ ] Black, isort, flake8, and pylint pass through the repository's canonical
      local validation targets.
- [ ] Security, resolver, readiness, summarization, plugin lifecycle, CLI handler,
      and release-tooling modules type-check with zero errors.
- [ ] If the entry census proves full-project zero is not bounded for this phase,
      an enumerated per-module legacy baseline is committed with a ratchet test:
      counts may only shrink, adding an excluded module fails CI, and blanket
      `ignore_errors` remains forbidden.
- [ ] The full non-benchmark test suite passes from a clean worktree.
- [ ] GitHub workflow changes in this phase do not increase hosted per-PR compute.

**Scope notes**

Plan at least 4 lanes: deterministic test-contract repair, hermetic fixture/network
repair, pylint/format recovery, and mypy census/zero-or-ratchet enforcement.
Formatting may be applied mechanically after behavioral edits. Do not classify a
failure as stale without proving the production contract that replaced it.

**Non-goals**

- No coverage-threshold increase unrelated to the reviewed defects.
- No test deletion solely to obtain a green result.

**Key files**

- `tests/**`
- `mcp_server/**`
- `pyproject.toml`
- `pytest.ini`
- `Makefile`
- `.github/workflows/ci-cd-pipeline.yml`
- `docs/development/TESTING-GUIDE.md`

**Depends on**

- PLUGLIFE

**Produces**

- IF-0-QUALITY-1 - Green deterministic release-quality gate.
- IF-0-QUALITY-2 - Enforced production type-check contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: canonical_spec_update
- target_surfaces: local validation contract and testing guide
- evidence_paths: clean full-suite, format/lint, pylint, and mypy output
- redaction_posture: metadata_only
- blocker_class: repeated_verification_failure after one diagnosed repair rerun

### Phase 7 — Release And Supply-Chain Safety (RELEASESAFE)

**Objective**

Prevent publish-before-merge, pin workflow dependencies, and prepare one coherent
`1.3.1` bug-fix release surface without dispatching it.

**Exit criteria**

- [ ] Release preparation and release dispatch are separate workflow modes or
      separate workflows with explicit protected-main reachability checks.
- [ ] No tag, GitHub release, artifact attestation, container publish, or PyPI
      publish step can run before the target commit is reachable from `main`.
- [ ] Manual `auto_merge=false` preparation creates or updates a release PR and
      stops without publishing.
- [ ] Publish mode verifies clean protected-main topology and the exact prepared
      version in the same job immediately before each mutation, with full history
      available for `git merge-base --is-ancestor`.
- [ ] Every third-party action is pinned to an immutable 40-hex commit SHA, with
      update comments where useful.
- [ ] A workflow-policy test parses every workflow and rejects mutable action refs,
      shallow ancestry checks, or tag/release/publish steps lacking an in-job
      protected-main reachability guard.
- [ ] `pyproject.toml`, runtime `__version__`, README, changelog, lock metadata, and
      release tests agree on `1.3.1`.
- [ ] A locally built wheel passes release smoke; no external release is dispatched.

**Scope notes**

Plan at least 3 lanes: release workflow topology, immutable action audit, and
version/docs/package preparation. Keep hosted compute flat or lower.

**Non-goals**

- No push to PyPI, GitHub release creation, container publication, or tag creation.
- No merge to `main` from this phase.

**Key files**

- `.github/workflows/release-automation.yml`
- `.github/workflows/container-registry.yml`
- `.github/workflows/**`
- `pyproject.toml`
- `uv.lock`
- `mcp_server/__init__.py`
- `README.md`
- `CHANGELOG.md`
- `tests/test_release_metadata.py`
- `tests/smoke/test_release_smoke_contract.py`
- `tests/test_workflow_release_policy.py`

**Depends on**

- QUALITY

**Produces**

- IF-0-RELEASESAFE-1 - Merge-before-publish workflow contract.
- IF-0-RELEASESAFE-2 - Immutable actions and coherent `1.3.1` surface.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: canonical_spec_update
- target_surfaces: release workflow, package metadata, release documentation
- evidence_paths: workflow contract tests and local wheel smoke
- redaction_posture: metadata_only
- blocker_class: contract_bug if any publish path lacks protected-main proof

### Phase 8 — End-To-End Hardening Verification (HARDVERIFY)

**Objective**

Prove the complete fixed system through local MCP, browser/admin UI, multi-repo,
worker-lifecycle, package, and repository-quality evidence.

**Exit criteria**

- [ ] Browser automation renders `/docs`, exercises a visible unauthorized path,
      records zero console errors outside an explicit empty-by-default allowlist,
      and finds no overlapping or broken UI surfaces.
- [ ] STDIO smoke proves status, plugin listing, exact repo search/symbol selection,
      unknown-repo refusal, readiness fallback, recoverable reindex, and summarize.
- [ ] A two-repository temporary fixture proves no cross-repo result leakage.
- [ ] Corrupt-index and missing-index fixtures prove fail-closed classification and
      successful allowed recovery transitions.
- [ ] Worker evidence proves lazy bounded allocation and zero workers after shutdown.
- [ ] STDIO handshake smoke proves `MCP_CLIENT_SECRET` behavior remains intact.
- [ ] Default test evidence records zero unmarked network calls.
- [ ] Workflow policy evidence proves immutable actions and in-job publish guards.
- [ ] Full tests, static checks, type checks, security scan, and local wheel smoke pass.
- [ ] `docs/status/COMPREHENSIVE_HARDENING_V10.md` records commands, versions,
      counts, and redacted outcomes without secrets.
- [ ] Any failed gate is routed back to the owning phase and rerun after repair.

**Scope notes**

Decompose into 3 lanes: browser/admin UI verification, MCP/multi-repo/runtime
verification, and package/quality/security verification. This phase may add
reusable smoke scripts and evidence, but it must not waive failed upstream
contracts.

**Non-goals**

- No broad fleet indexing.
- No external release dispatch.

**Key files**

- `scripts/admin_browser_smoke.py`
- `scripts/hardening_e2e.py`
- `tests/smoke/**`
- `docs/status/COMPREHENSIVE_HARDENING_V10.md`
- `.phase-loop/runs/**/verification.json`

**Depends on**

- RELEASESAFE

**Produces**

- IF-0-HARDVERIFY-1 - Complete hardening verification evidence.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: verification scripts and status evidence
- evidence_paths: browser screenshot, MCP smoke output, worker metrics, full gate output
- redaction_posture: metadata_only
- blocker_class: repeated_verification_failure for a reproducible failed final gate

## Phase Dependency DAG

```text
AUTHBOUND
   -> REPOSEL
      -> READYREC
         -> SUMCONTRACT
            -> PLUGLIFE
               -> QUALITY
                  -> RELEASESAFE
                     -> HARDVERIFY
```

The phases are serial for merge safety and because later gates consolidate the
earlier contracts. AUTHBOUND and REPOSEL are technically independent but remain
serialized because both touch shared test fixtures. Every behavioral phase must
compare against the frozen known-failure inventory until QUALITY removes it.
Within each phase, downstream phase plans should use disjoint lanes wherever the
owned-file graph permits.

## Execution Notes

- Implementation must not begin until the three-agent panel review is complete,
  required amendments are reconciled, and this roadmap validates again.
- Use `codex-plan-phase` for every phase; do not execute directly from this roadmap.
- Run phases in DAG order. Parallel work is allowed only inside a phase after lane
  ownership is machine-validated.
- Every phase plan must include a failing-at-base reproduction command and the same
  command passing after implementation, plus a no-new-failures baseline comparison.
- If execution changes a downstream contract, amend the nearest unstarted phase and
  regenerate its plan before continuing.
- The final phase is verification, not release dispatch. Publishing requires a
  separate clean-tree operator action after merge.

## Verification

Roadmap validation:

```bash
phase-loop validate-roadmap specs/phase-plans-v10.md
```

Representative phase and final verification commands:

```bash
uv sync --locked --extra dev --extra semantic
uv run pytest tests/security tests/test_repository_readiness.py tests/test_tool_readiness_fail_closed.py -q --no-cov
uv run pytest tests/test_summarization.py tests/integration/test_multi_repo_server.py tests/integration/test_sigterm_shutdown.py -q --no-cov
make alpha-format-lint
uv run mypy mcp_server
uv run python scripts/check_mypy_baseline.py
uv run pytest -q --no-cov --benchmark-skip
make release-smoke
uv run bandit -r mcp_server -f json -o /tmp/code-index-mcp-bandit.json
uv run python scripts/admin_browser_smoke.py
uv run python scripts/hardening_e2e.py
git diff --check
git status --short
```
