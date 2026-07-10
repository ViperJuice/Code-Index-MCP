---
phase_loop_plan_version: 1
phase: HARDVERIFY
roadmap: specs/phase-plans-v10.md
roadmap_sha256: 7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e
---

# HARDVERIFY: End-To-End Hardening Verification

## Context
Consolidate the completed hardening phases into executable, redacted evidence without indexing the fleet or dispatching a release. At entry, `scripts/admin_browser_smoke.py` is an HTTP-only AUTHBOUND probe, `scripts/hardening_e2e.py` and `docs/status/COMPREHENSIVE_HARDENING_V10.md` do not exist, and the preceding RELEASESAFE phase passes the canonical alpha release gate with a prepared but unpublished `1.3.1` package.

## Interface Freeze Gates
- [ ] IF-0-HARDVERIFY-1 — Browser, MCP STDIO, exact multi-repository isolation and recovery, worker lifecycle, handshake, package, security, and full local quality evidence pass in one clean closeout with no secrets, fleet indexing, or external release mutation.

## Lane Index & Dependencies
SL-0 — Browser and admin UI verification
  Depends on: (none)
  Blocks: SL-2
  Parallel-safe: no

SL-1 — MCP, multi-repository, and runtime verification
  Depends on: (none)
  Blocks: SL-2
  Parallel-safe: no

SL-2 — Package, quality, security, and documentation sweep
  Depends on: SL-0, SL-1
  Blocks: (none)
  Parallel-safe: no

## Lanes

### SL-0 — Browser and admin UI verification
- **Scope**: Make the existing admin probe produce structured metadata-only evidence, then use the Playwright plugin against a locally started FastAPI process to prove `/docs` rendering and visible protected-route refusal at desktop and mobile viewports.
- **Owned files**: `scripts/admin_browser_smoke.py`, `tests/test_admin_browser_smoke.py`
- **Interfaces provided**: `HARDVERIFY-BROWSER-EVIDENCE`
- **Interfaces consumed**: `IF-0-AUTHBOUND-1` (pre-existing), `IF-0-AUTHBOUND-2` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add deterministic request/response and redaction tests for docs, OpenAPI, protected-route refusal, JSON evidence output, and error exits.
  - impl: Extend the probe with bounded timeouts, OpenAPI validation, JSON output, and no credential/token capture; retain its standalone `--base-url` contract.
  - verify: Start `mcp-index serve` with generated ephemeral local credentials and isolated registry state; run the probe; use Playwright accessibility snapshots, console capture, protected-operation interaction, overlap checks, and desktop/mobile screenshots under `/tmp/code-index-mcp-hardverify/`.

### SL-1 — MCP, multi-repository, and runtime verification
- **Scope**: Add one deterministic reducer over existing high-value STDIO, selector, readiness, recovery, worker, shutdown, and handshake tests rather than duplicating those contracts.
- **Owned files**: `scripts/hardening_e2e.py`, `tests/smoke/test_hardening_e2e.py`
- **Interfaces provided**: `HARDVERIFY-RUNTIME-EVIDENCE`
- **Interfaces consumed**: `IF-0-REPOSEL-1` (pre-existing), `IF-0-READYREC-1` (pre-existing), `IF-0-SUMCONTRACT-1` (pre-existing), `IF-0-PLUGLIFE-1` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Prove the reducer command manifest covers official SDK STDIO status/plugins/search/symbol/reindex/summarize, unknown-repository refusal, two-repository isolation, missing/corrupt recovery, bounded worker allocation/shutdown, SIGTERM cleanup, and `MCP_CLIENT_SECRET` handshake behavior.
  - impl: Run each frozen pytest group in a subprocess, stop on failure, record duration and summary only, redact environment/command output, and optionally write one JSON report outside the repository.
  - verify: Run the reducer with `/tmp/code-index-mcp-hardverify/runtime.json` and independently inspect its group/count summary.

### SL-2 — Package, quality, security, and documentation sweep
- **Scope**: Reduce browser/runtime results with package, workflow, static, type, security, network-hermeticity, and full test evidence into the final status record.
- **Owned files**: `docs/status/COMPREHENSIVE_HARDENING_V10.md`, `tests/docs/test_comprehensive_hardening_v10.py`
- **Interfaces provided**: `IF-0-HARDVERIFY-1`
- **Interfaces consumed**: `HARDVERIFY-BROWSER-EVIDENCE`, `HARDVERIFY-RUNTIME-EVIDENCE`, `IF-0-QUALITY-1` (pre-existing), `IF-0-QUALITY-2` (pre-existing), `IF-0-RELEASESAFE-1` (pre-existing), `IF-0-RELEASESAFE-2` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Freeze required headings, commands, version, test counts, screenshot/report paths, unpublished posture, no-unmarked-network result, and the absence of secret values or completion claims unsupported by commands.
  - verify: Run `uv sync --locked --extra dev --link-mode=copy`, the hardening reducer, browser/admin smoke, workflow policy tests, `make release-smoke`, `make alpha-release-gates`, full non-benchmark pytest, mypy ratchet, and Bandit JSON scan.
  - docs: Record exact commands, versions, counts, artifact paths, repaired failures, and redacted outcomes only after every cited command passes.

## Verification
- `uv sync --locked --extra dev --link-mode=copy`.
- `uv run --python 3.12 pytest tests/test_admin_browser_smoke.py tests/smoke/test_hardening_e2e.py tests/docs/test_comprehensive_hardening_v10.py -q --no-cov`.
- Local `mcp-index serve` plus `uv run --python 3.12 python scripts/admin_browser_smoke.py --base-url http://127.0.0.1:<port> --expect-unauthorized --json-output /tmp/code-index-mcp-hardverify/admin.json`.
- Playwright `/docs` accessibility snapshot, protected-operation interaction, console-error check, overlap check, and desktop/mobile screenshots under `/tmp/code-index-mcp-hardverify/`.
- `uv run --python 3.12 python scripts/hardening_e2e.py --json-output /tmp/code-index-mcp-hardverify/runtime.json`.
- `uv run --python 3.12 pytest tests/test_workflow_release_policy.py tests/test_workflow_action_pins.py -q --no-cov`.
- `uv run --python 3.12 python scripts/check_mypy_baseline.py` and release-critical mypy target at zero.
- `uv run --python 3.12 bandit -r mcp_server -f json -o /tmp/code-index-mcp-hardverify/bandit.json` with no high-severity findings.
- `make release-smoke`, `make alpha-release-gates`, and full non-benchmark `uv run --python 3.12 pytest tests --benchmark-skip --no-cov`.
- `git diff --check`, generated-index-metadata restoration, and clean-tree audit.

## Execution Notes
- Browser work uses the installed Playwright plugin; the repository script remains a portable HTTP/OpenAPI probe and does not add a Playwright package dependency.
- Local server credentials are generated ephemerally and are never printed, committed, or included in JSON/status evidence.
- Runtime evidence invokes exact existing test nodes and records group summaries, not captured application logs or environment values.
- `/tmp/code-index-mcp-hardverify/` is transient local evidence and is not staged; the committed status document names paths and redacted observations only.
- A failed upstream contract is repaired in its owning implementation or test surface and the original final gate is rerun; no assertion or scan threshold is waived.
- Doc delta decision: `no_doc_delta` for README, CHANGELOG, and release notes because RELEASESAFE already made the active `1.3.1` public surface coherent; HARDVERIFY records evidence only.
- This phase performs no broad fleet indexing, workflow dispatch, tag, release, container push, attestation upload, or package publication.

## Acceptance Criteria
- [ ] `scripts/admin_browser_smoke.py` and Playwright prove `/docs` renders, a protected operation visibly returns `401` or `403`, console errors are empty, overlap checks return zero, and desktop/mobile screenshots exist.
- [ ] `scripts/hardening_e2e.py` exits zero only after all frozen STDIO, isolation, recovery, worker, shutdown, and handshake pytest groups pass and writes a redacted JSON summary.
- [ ] The Bandit command reports zero high-severity findings, `scripts/check_mypy_baseline.py` passes, and the focused workflow-policy pytest command proves immutable refs plus protected-main mutation guards.
- [ ] `make release-smoke`, `make alpha-release-gates`, and full non-benchmark pytest pass after all phase edits, with default tests still denying unmarked network access.
- [ ] `docs/status/COMPREHENSIVE_HARDENING_V10.md` passes its contract test and records `1.3.1` as prepared/unpublished with exact redacted evidence and no secret values.
- [ ] `git diff --check` passes, generated index metadata matches `HEAD`, all phase outputs are committed, and the roadmap reconciles to complete.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `no_spec_delta`
- target surfaces: verification scripts and status evidence
- evidence paths: browser screenshots, admin/runtime/Bandit JSON summaries, full gate output, and `docs/status/COMPREHENSIVE_HARDENING_V10.md`
- redaction posture: `metadata_only`
- downstream handling: `none`
- blocker_class: repeated_verification_failure after one diagnosed repair rerun
