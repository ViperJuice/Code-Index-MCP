# P19: Release Readiness

> Plan doc produced by `/plan-phase P19` against the P19 section of `specs/phase-plans-v1.md` (resolved from commit `2e574df`, the phase-roadmap-builder's append; local tip `977c82f` does not yet contain the P19 text).
> On approval, copy to `plans/phase-plan-v1-p19.md` and hand off to `/execute-phase p19`.

## Context

P18 is feature-complete but not publishable. The phase's outputs landed across a long-lived worktree branch (`worktree-lane-sl-4b-20260419T170149-ms2d`, tip `2e574df`) and local `main` (`977c82f`), while `origin/main` (`8151341`) has seen **zero** of the ≥100 commits from P12 onward. A misplaced SL-docs commit (`977c82f`, the tip of local main) landed on main rather than through the lane-merge pipeline; inside it is one defect — a duplicate, lowercase `.claude/docs-catalog.json` entry that points at a non-existent file. The remaining five files in that commit (CHANGELOG P18 block, new operator docs, sandbox.md P18 section, env-vars extension, spec amendments) are legitimate outputs and must be preserved.

P19's job is strictly hygiene: reconcile, close residual test debt, fix the catalog leak, publish. No new product features. The exit criterion is a pushed `origin/main` with CI green and a `v1.2.0-rc1` tag cut on it.

### What actually exists today (vs. spec wording)

- **Git topology** (confirmed by `explore-reconcile-ci`):
  - `origin/main` → `8151341` ("chore(roadmap): append P12-P15"). Untouched since before P12.
  - `worktree-lane-sl-4b-20260419T170149-ms2d` → `2e574df` ("chore(roadmap): append P19 + P20"). Carries the full P12–P18 integration history plus the P17 SL-4b burn-down merge (`059cec4`) and the proper P18 SL-docs merge (`4580c6c`).
  - Local `main` → `977c82f` ("docs(p18,sl-docs): P18 operator docs + spec amendments"). Diverges from the worktree tip by a single commit — `977c82f` itself. `977c82f..2e574df` = 0 commits; `2e574df..977c82f` = 1 commit. **The worktree branch is a strict superset of main's history *except* for `977c82f`.**
  - `977c82f` diff: 7 files / 859 insertions / 18 deletions. **Legitimate**: `CHANGELOG.md` P18 block (89 lines), `docs/configuration/ENVIRONMENT-VARIABLES.md` (+112 lines), `docs/operations/gateway-startup-checklist.md` (NEW, 189 lines), `docs/operations/artifact-retention.md` (NEW, 242 lines), `docs/security/sandbox.md` (+80 lines, P18 migration section), `specs/phase-plans-v1.md` (+64 lines, P18 post-execution amendments). **Defect**: `.claude/docs-catalog.json` adds both a valid new entry and a duplicate lowercase `docs/configuration/environment-variables.md` that points at a non-existent file.
- **Leaked catalog entry** (confirmed by `explore-docs-catalog`): line 26 of `.claude/docs-catalog.json` after `977c82f` is a 3-line block referencing `docs/configuration/environment-variables.md` (all lowercase). Disk has only `ENVIRONMENT-VARIABLES.md` (uppercase). Filesystem is case-sensitive on Linux; the test contract IF-0-P19-3 fails on this today.
- **CI workflows** (confirmed by `explore-reconcile-ci`): `.github/workflows/ci-cd-pipeline.yml` exists with jobs `quality-checks`, `test` (pytest gate, `-n auto --timeout=60`, `--no-cov` on PRs), `test-cross-platform` (macOS/Windows smoke, informational), `test-integration` (`-m "integration or slow"`), `test-extended` (nightly/manual, sets `RUN_REAL_WORLD_TESTS=1`), `benchmark`, `build-docker`, `security-scan`. No `test-authenticated` job gated on `RUN_GH_AUTHENTICATED_TESTS=1` exists; SL-1 adds one.
- **Validation API surface** (for SL-4 reuse, confirmed by `explore-reconcile-ci`):
  - `mcp_server/config/validation.py::validate_production_config(config, *, environment="production") -> List[ValidationError]`
  - `mcp_server/config/validation.py::render_validation_errors_to_stderr(errors: List[ValidationError]) -> None`
  - `ValidationError = @dataclass(frozen=True){code, message, severity: Literal["fatal","warn"]}`
  - Wired at boot in `mcp_server/gateway.py`; `sys.exit(1)` on any `severity=="fatal"` when `MCP_ENVIRONMENT=production`.
- **Current version** (confirmed): `1.1.0` in `mcp_server/__init__.py`; latest tag `v1.1.0`. Spec's `v0.X.0-rc1` placeholder resolves to **`v1.2.0-rc1`** given the feature delta shipped P12–P18.
- **`tests/conftest.py`** (confirmed by `explore-test-debt`): 571 lines. No existing `pytest_collection_modifyitems` hook. `pytest.ini` has `strict-markers = true` and an existing `markers:` block listing `unit, integration, slow, benchmark, e2e, requires_db, requires_network, interface, plugin, performance, resilience, security`. Existing `addopts = -m "not integration and not slow"`. No existing env-var-gated marker pattern — IF-0-P19-2 introduces the first.
- **The 4 residual failures** (confirmed):
  1. `tests/test_p16_vocabulary.py::test_validate_production_config_signature` — passes `object()` to `validate_production_config`; P18-filled body accesses `config.jwt_secret_key` → `AttributeError`. Contract intent: prove the function accepts a `SecurityConfig` and returns `List[ValidationError]`. Amendment: replace `object()` with a minimal mock (or real `SecurityConfig` with strong JWT secret) and assert signature + return type.
  2–4. `tests/security/test_artifact_attestation.py::TestAttest::{test_attest_returns_attestation_with_bundle_url, test_attest_sidecar_path_is_set, test_attest_signed_at_is_datetime}` — mock `subprocess.run` but the module's `_check_gh_auth_for_attestations` fires first and raises `AttestationError: ATTESTATION_PREREQ: gh token missing attestations:write scope`. Root cause is the mock being placed too late; the tactical fix is to marker-gate them behind `requires_gh_auth`. (Noted for P20 follow-up: long-term the prereq check should itself be mockable.)
- **`.claude/skills/_shared/scaffold_docs_catalog.py` is ABSENT** (confirmed). The `.claude/skills/` directory does not exist in this repo. The SL-docs template in the `plan-phase` skill invokes `scaffold_docs_catalog.py --rescan`; SL-3 authors it from scratch.
- **`docs/operations/multi-instance.md` exists** as a viable shape template for P19's new `docs/operations/p18-upgrade.md`.
- **`CHANGELOG.md`** has a fully-populated `[Unreleased]` section carrying P13–P18 content (P18 block was brought in by `977c82f`). Prior tagged section: `[1.1.0] — 2026-04-14`.
- **`README.md`** has **no** `## Recent phases` section (grep confirmed). SL-5's README extension resolves to no-op.
- **`docs/security/sandbox.md`** exists (125+ lines, last extended by `977c82f` to include P18 migration section). Ready for a cross-link to `p18-upgrade.md`.
- **`scripts/` directory** has 10 shell scripts; none are `*_upgrade.sh` or `preflight*`. `deploy-production.sh` + `health-check.sh` + `plantuml-validate.sh` are the bridge-pattern references (shell → Python CLI with exit-code propagation).

### Single defect clarified

The **entire** recoverable defect in `977c82f` is three JSON lines at `.claude/docs-catalog.json:26-28`. Everything else in that commit is genuine P18 output. Reconciliation should preserve all 859 insertions sans those 3 lines — not revert-and-recompose.

## Interface Freeze Gates

- [ ] **IF-0-P19-1** — `scripts/preflight_upgrade.sh <env_file_path>` exits `0` when the supplied env file won't fatal under current gateway validation, `1` with a `[FATAL]`/`[WARN]` line-per-error listing on stdout/stderr otherwise. Rendering contract is byte-identical to `render_validation_errors_to_stderr` (same prefixing, same order). Internal mechanism: shells into `python -m mcp_server.cli preflight_env <file>` (new subcommand) or directly imports `validate_production_config` + `render_validation_errors_to_stderr`. **Owner**: SL-4. **Consumers**: P20 deployment runbook, operator migration from P18.

- [ ] **IF-0-P19-2** — `pytest.mark.requires_gh_auth` is declared in `pytest.ini`'s `markers:` block (so `strict-markers = true` passes) and wired in `tests/conftest.py` via a `pytest_collection_modifyitems(config, items)` hook that, when `os.getenv("RUN_GH_AUTHENTICATED_TESTS") != "1"`, appends `pytest.mark.skip(reason="set RUN_GH_AUTHENTICATED_TESTS=1 to run")` to every item carrying the marker. Default `pytest --no-cov --ignore=tests/real_world` run reports `0 failed` after SL-2 lands. **Owner**: SL-2. **Consumers**: SL-1 (adds `test-authenticated` CI job that sets the env var).

- [ ] **IF-0-P19-3** — `tests/test_docs_catalog_integrity.py` asserts: (a) for every `docs[].path` in `.claude/docs-catalog.json`, the file exists on disk (case-sensitive); (b) no two entries share the same `path` (case-sensitive comparison — also warn on case-variant collisions where a lowercased path equals another entry's lowercased path); (c) the document conforms to the schema `{version: int, generated_at: str, docs: [{path: str, description: str, touched_by_phases: list[str]}]}`. Test imports and calls the core assertions from `.claude/skills/_shared/scaffold_docs_catalog.py` (single source of truth). **Owner**: SL-3. **Consumers**: CI `test` job (runs as part of the default gate).

## Lane Index & Dependencies

```
SL-1 — Reconcile + publish + CI + tag
  Depends on: (none)
  Blocks: SL-2, SL-3, SL-4, SL-5, SL-docs
  Parallel-safe: no (singleton root — rewrites local main's tip;
                  all other lanes must branch off the reconciled main)

SL-2 — Residual test debt (marker gate + P16 signature fix)
  Depends on: SL-1
  Blocks: SL-docs
  Parallel-safe: yes (test-only; disjoint from SL-3/4/5 files)

SL-3 — Docs-catalog integrity + rescan tool
  Depends on: SL-1
  Blocks: SL-docs
  Parallel-safe: yes (owns .claude/docs-catalog.json + .claude/skills/_shared/ + its own new test file)

SL-4 — Upgrade comms + preflight script
  Depends on: SL-1
  Blocks: SL-5 (CHANGELOG cross-link target), SL-docs
  Parallel-safe: yes (new files only — docs/operations/p18-upgrade.md, scripts/preflight_upgrade.sh, tests/test_preflight_upgrade.py)

SL-5 — Release-notes migration
  Depends on: SL-1 (CHANGELOG shape lands via cherry-pick), SL-4 (p18-upgrade.md referenced)
  Blocks: SL-docs
  Parallel-safe: yes-after-deps

SL-docs — Documentation & spec reconciliation (terminal)
  Depends on: SL-1, SL-2, SL-3, SL-4, SL-5
  Parallel-safe: no (terminal)
```

Wave plan (MAX_PARALLEL_LANES=2):
- **W1**: SL-1 (alone; rewrites main)
- **W2a**: SL-2 + SL-3
- **W2b**: SL-4
- **W3**: SL-5
- **W4**: SL-docs

3 logical waves; 4 with the MAX_PARALLEL_LANES=2 split.

## Lanes

### SL-1 — Reconcile + publish + CI + tag

- **Scope**: Reset local `main` onto the worktree branch tip, re-apply the legitimate parts of the leaked SL-docs commit, push fast-forward to `origin/main`, add the `test-authenticated` CI job, cut release tag `v1.2.0-rc1`. Owns the version bump in `mcp_server/__init__.py`.
- **Owned files**:
  - `mcp_server/__init__.py` (version bump `1.1.0` → `1.2.0rc1`)
  - `.github/workflows/ci-cd-pipeline.yml` (add `test-authenticated` job; add `tests/test_docs_catalog_integrity.py` coverage if not implicitly picked up)
  - Git refs: `refs/heads/main`, `refs/tags/v1.2.0-rc1`, `refs/tags/pre-p19-main` (backup tag)
  - **Conflict-resolve** (not owned, edited once during cherry-pick): `.claude/docs-catalog.json` — strips lines 26–28 of `977c82f`'s diff. SL-3 is the single-writer for the *content* of this file post-reconciliation; SL-1's touch is a one-shot reconciliation edit.
- **Interfaces provided**:
  - Reconciled `main` at the post-P18 tip (all P12–P18 integration history + the legitimate parts of `977c82f`).
  - `origin/main` pushed fast-forward; `origin v1.2.0-rc1` tag.
  - CI `test-authenticated` job stub for SL-2's marker.
- **Interfaces consumed**: (none — DAG root).
- **Parallel-safe**: **no** (singleton; subsequent lanes branch off post-SL-1 main).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_release_metadata.py` (NEW, small) | asserts `mcp_server.__version__ == "1.2.0rc1"` and asserts an `origin v1.2.0-rc1` tag is set locally (`git tag -l`) | `./.venv/bin/pytest tests/test_release_metadata.py -q` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/__init__.py`; git refs (main + tags) | — | — |
| SL-1.3 | impl | SL-1.2 | `.github/workflows/ci-cd-pipeline.yml` (new `test-authenticated` job gated on `secrets.ATTESTATION_GH_TOKEN`; runs `RUN_GH_AUTHENTICATED_TESTS=1 pytest tests/security/test_artifact_attestation.py -m requires_gh_auth`) | — | — |
| SL-1.4 | verify | SL-1.3 | repo-wide | SL-1.1 + smoke | `./.venv/bin/pytest tests/test_release_metadata.py -q && git log --oneline origin/main..HEAD && git tag -l v1.2.0-rc1` |

**Orchestrator-level reconciliation sequence** (performed inside SL-1's worktree before any code tasks):

1. `git fetch origin main`; assert `git rev-parse origin/main == 8151341` (else halt: someone else is pushing).
2. `git tag pre-p19-main <current main SHA>` (backup; safe no-op if push fails).
3. `git switch main`; `git reset --hard 0ce5f9f` (worktree branch tip after the `chore(plan): P19 lane plan` commit; this adopts the full worktree history *including* this plan doc at `plans/phase-plan-v1-p19.md`). If the worktree tip has advanced past `0ce5f9f` before SL-1 starts, use `git rev-parse worktree-lane-sl-4b-20260419T170149-ms2d` to get the current tip and reset there instead; log whatever SHA you used.
4. `git cherry-pick 977c82f`. Resolve the single expected conflict on `.claude/docs-catalog.json` by dropping the duplicate lowercase `docs/configuration/environment-variables.md` entry (3 JSON lines). Complete with `git cherry-pick --continue`.
5. Verify: `grep -c 'environment-variables.md' .claude/docs-catalog.json` returns `1` (only the uppercase path); `jq '.docs | length' .claude/docs-catalog.json` returns the expected count.
6. Execute SL-1.1 → SL-1.2 → SL-1.3 → SL-1.4 in-order.
7. `git push origin main` — **must be fast-forward**. If the push is rejected for non-FF, halt and surface.
8. `git push origin v1.2.0-rc1`.

Spec amendment note: if CI on `origin/main` comes back non-green on first push, SL-1 does not force-re-push; it lands a fix commit on top and pushes that. If fixes are needed, they open a new SL within the phase — recorded under Execution Notes.

### SL-2 — Residual test debt

- **Scope**: Register `pytest.mark.requires_gh_auth` + gate it via an env-var-aware `pytest_collection_modifyitems` hook; mark the 3 failing `TestAttest` tests; fix `test_p16_vocabulary::test_validate_production_config_signature` by supplying a real-shaped `SecurityConfig` mock. No production-code edits.
- **Owned files**:
  - `tests/conftest.py` (add `pytest_collection_modifyitems` hook)
  - `pytest.ini` (extend `markers:` block only)
  - `tests/test_p16_vocabulary.py` (amend `test_validate_production_config_signature`)
  - `tests/security/test_artifact_attestation.py` (add `@pytest.mark.requires_gh_auth` to 3 tests in `TestAttest`)
- **Interfaces provided**: IF-0-P19-2.
- **Interfaces consumed**: SL-1's reconciled main (post-reconciliation so CHANGELOG/docs state is stable; consumes no symbols).
- **Parallel-safe**: yes.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_requires_gh_auth_marker.py` (NEW; asserts marker is registered, that the hook skips when env unset, that the hook runs when `RUN_GH_AUTHENTICATED_TESTS=1`; uses `pytester` fixture) | marker contract | `./.venv/bin/pytest tests/test_requires_gh_auth_marker.py -q` |
| SL-2.2 | impl | SL-2.1 | `pytest.ini` (add `requires_gh_auth: tests requiring live gh CLI auth; set RUN_GH_AUTHENTICATED_TESTS=1 to run`); `tests/conftest.py` (+ `pytest_collection_modifyitems` hook) | — | — |
| SL-2.3 | impl | SL-2.2 | `tests/security/test_artifact_attestation.py` (add marker to 3 `TestAttest` tests) | SL-2.1 | — |
| SL-2.4 | impl | SL-2.2 | `tests/test_p16_vocabulary.py::test_validate_production_config_signature` (replace `object()` with a minimal `SecurityConfig`-shaped object with strong JWT secret; assert signature + return-type invariants) | — | — |
| SL-2.5 | verify | SL-2.3, SL-2.4 | repo-wide | SL-2.1 + regression | `./.venv/bin/pytest --no-cov --ignore=tests/real_world -q 2>&1 \| tail -5` — expect `0 failed`; then `RUN_GH_AUTHENTICATED_TESTS=1 ./.venv/bin/pytest tests/security/test_artifact_attestation.py::TestAttest -m requires_gh_auth --collect-only -q` — expect 3 tests collected (not skipped). |

### SL-3 — Docs-catalog integrity + rescan tool

- **Scope**: Author `.claude/skills/_shared/scaffold_docs_catalog.py` from scratch (no external source to port from); write `tests/test_docs_catalog_integrity.py` per IF-0-P19-3; clean up any residual catalog issues missed by SL-1's cherry-pick fix.
- **Owned files**:
  - `.claude/skills/_shared/scaffold_docs_catalog.py` (NEW, ≤150 LOC)
  - `tests/test_docs_catalog_integrity.py` (NEW)
  - `.claude/docs-catalog.json` (single-writer for content post-SL-1 — e.g., `generated_at` refresh)
- **Interfaces provided**: IF-0-P19-3; `scaffold_docs_catalog.py --rescan` CLI (consumed by every SL-docs lane in every future phase).
- **Interfaces consumed**: Post-SL-1 main (catalog without the duplicate).
- **Parallel-safe**: yes.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_docs_catalog_integrity.py` (NEW; asserts (a) every path exists on disk, (b) no duplicates by exact path, (c) warns on case-variant duplicates, (d) schema shape matches) | catalog integrity | `./.venv/bin/pytest tests/test_docs_catalog_integrity.py -q` |
| SL-3.2 | impl | SL-3.1 | `.claude/skills/_shared/scaffold_docs_catalog.py` (NEW — expose `check_catalog(path) -> list[IntegrityError]`, `rescan(path) -> None`, argparse CLI with `--rescan`/`--check`); test imports `check_catalog` directly | — | — |
| SL-3.3 | impl | SL-3.2 | `.claude/docs-catalog.json` (rescan to bump `generated_at` and validate post-SL-1 state; no entry additions) | — | — |
| SL-3.4 | verify | SL-3.3 | catalog + tests | SL-3.1 | `./.venv/bin/pytest tests/test_docs_catalog_integrity.py -q && python3 .claude/skills/_shared/scaffold_docs_catalog.py --check .claude/docs-catalog.json` (exit 0 expected) |

### SL-4 — Upgrade comms + preflight

- **Scope**: Author `docs/operations/p18-upgrade.md` (breaking-change migration guide for operators upgrading through P12–P18 in one step), `scripts/preflight_upgrade.sh` (IF-0-P19-1), and `tests/test_preflight_upgrade.py`. Preflight script shells into Python to reuse `validate_production_config` and `render_validation_errors_to_stderr` — no re-implementation of validation rules.
- **Owned files**:
  - `docs/operations/p18-upgrade.md` (NEW)
  - `scripts/preflight_upgrade.sh` (NEW)
  - `mcp_server/cli/preflight_commands.py` (NEW; thin `preflight_env <file>` subcommand that registers in `mcp_server/cli/__main__.py`)
  - `tests/test_preflight_upgrade.py` (NEW)
- **Interfaces provided**: IF-0-P19-1; `p18-upgrade.md` referenced by SL-5 and SL-docs.
- **Interfaces consumed**:
  - `validate_production_config` + `render_validation_errors_to_stderr` from `mcp_server/config/validation.py` (no modifications).
  - `SecurityConfig` loader path from `mcp_server/gateway.py` startup (inlined or imported; read-only).
- **Parallel-safe**: yes (net-new files only; the single edit to `mcp_server/cli/__main__.py` is a pure subcommand registration — a one-line insert after existing registrations).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_preflight_upgrade.py` (NEW; covers: (a) argparse usage printed on no args; (b) happy-path env file exits 0 with no stdout; (c) fatal-detected env file exits 1 with `[FATAL] …` lines; (d) warn-only env file exits 0 with `[WARN]` lines) | preflight contract | `./.venv/bin/pytest tests/test_preflight_upgrade.py -q` |
| SL-4.2 | impl | SL-4.1 | `mcp_server/cli/preflight_commands.py` + `mcp_server/cli/__main__.py` (1-line registration) | — | — |
| SL-4.3 | impl | SL-4.2 | `scripts/preflight_upgrade.sh` (shell wrapper: resolves `.venv`/system Python, invokes `python -m mcp_server.cli preflight_env "$1"`, propagates exit code; idempotent, read-only) | — | — |
| SL-4.4 | impl | SL-4.3 | `docs/operations/p18-upgrade.md` (NEW) — sections: "Who this is for", "What broke" (sandbox default flip, validation fatals, new required env vars: `DEFAULT_ADMIN_PASSWORD`, `MCP_ENVIRONMENT`, `MCP_LOG_FORMAT`, etc.), "Pre-flight procedure" (invokes `scripts/preflight_upgrade.sh`), "No-downtime upgrade steps", "Rollback procedure", "Appendix: full env var delta" | — | — |
| SL-4.5 | verify | SL-4.4 | — | SL-4.1 | `./.venv/bin/pytest tests/test_preflight_upgrade.py -q && bash scripts/preflight_upgrade.sh tests/fixtures/preflight_happy.env; echo $?` (expect 0) |

### SL-5 — Release-notes migration

- **Scope**: Move CHANGELOG `[Unreleased]` contents into a new `[1.2.0-rc1] — <date>` section; re-open `[Unreleased]` empty. Add cross-link from `docs/security/sandbox.md` to `docs/operations/p18-upgrade.md`. No README edits (the "Recent phases" section does not exist; SL-5 explicitly does **not** create it).
- **Owned files**:
  - `CHANGELOG.md` (surgical header rewrite + date stamp only; no content changes)
  - `docs/security/sandbox.md` (one-line cross-link insert under the "P18: Default-On & Opt-Out Migration" section)
- **Interfaces provided**: Release-ready CHANGELOG section named `[1.2.0-rc1]`.
- **Interfaces consumed**:
  - CHANGELOG `[Unreleased]` content (comes via SL-1's cherry-pick of `977c82f`).
  - `docs/operations/p18-upgrade.md` (authored by SL-4).
- **Parallel-safe**: yes-after-deps.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-5.1 | test | — | `tests/test_release_notes.py` (NEW; asserts CHANGELOG has a `[1.2.0-rc1]` section with a date, `[Unreleased]` exists but empty, sandbox.md has a link to `p18-upgrade.md`) | CHANGELOG + sandbox shape | `./.venv/bin/pytest tests/test_release_notes.py -q` |
| SL-5.2 | impl | SL-5.1 | `CHANGELOG.md` (rename `[Unreleased]` → `[1.2.0-rc1] — 2026-04-20`; open fresh `[Unreleased]` above) | — | — |
| SL-5.3 | impl | SL-5.2 | `docs/security/sandbox.md` (add one line under the "P18: Default-On & Opt-Out Migration" section: `> See [docs/operations/p18-upgrade.md](../operations/p18-upgrade.md) for the full operator migration procedure.`) | — | — |
| SL-5.4 | verify | SL-5.3 | — | SL-5.1 | `./.venv/bin/pytest tests/test_release_notes.py -q` |

### SL-docs — Documentation & spec reconciliation

- **Scope**: Refresh the docs catalog (register new P19 doc files created by SL-3/SL-4); append any post-execution amendments to the P19 phase spec section if IF freezes drifted during impl; run any repo doc linters.
- **Owned files** (post-impl catalog touches only; content owned by originating lanes):
  - `.claude/docs-catalog.json` (register new entries via `scaffold_docs_catalog.py --rescan`)
  - `specs/phase-plans-v1.md` (append `### Post-execution amendments` to the P19 section if needed)
  - Legacy catalog entries (retouch `touched_by_phases` to include `p19` for docs touched this phase)
- **Interfaces provided**: (none).
- **Interfaces consumed**: All of SL-1..SL-5's outputs (in-tree post-merge).
- **Parallel-safe**: no (terminal).
- **Depends on**: SL-1, SL-2, SL-3, SL-4, SL-5.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Action |
|---|---|---|---|---|
| SL-docs.1 | docs | — | `.claude/docs-catalog.json` | `python3 .claude/skills/_shared/scaffold_docs_catalog.py --rescan .claude/docs-catalog.json` (SL-3 provides the tool). Picks up `docs/operations/p18-upgrade.md` as a new entry; preserves `touched_by_phases` history. |
| SL-docs.2 | docs | SL-docs.1 | per catalog | For each entry in the catalog, decide whether P19 work changed it. If yes, append `"p19"` to `touched_by_phases`. Specifically expected: `CHANGELOG.md`, `docs/security/sandbox.md`, the new `p18-upgrade.md`, `.claude/docs-catalog.json` itself. |
| SL-docs.3 | docs | SL-docs.2 | `specs/phase-plans-v1.md` | If any IF-0-P19-* gate signature drifted from spec wording during impl, append a `### Post-execution amendments` subsection to the P19 phase block listing the drift. Otherwise no-op; commit message records "no amendments needed". |
| SL-docs.4 | verify | SL-docs.3 | — | `./.venv/bin/pytest tests/test_docs_catalog_integrity.py -q && python3 .claude/skills/_shared/scaffold_docs_catalog.py --check .claude/docs-catalog.json` (no repo doc linters configured today — skip-with-note is acceptable). |

## Execution Notes

- **SL-1 is a non-standard lane**. It rewrites `refs/heads/main` rather than adding a commit. `execute-phase` must run SL-1 **alone** and wait for it to complete before spawning SL-2..SL-5 — their worktrees must be branched off the post-SL-1 main tip, not off the pre-reconciliation `977c82f`. If the orchestrator spawns them in parallel off the old tip, their merges will replay the duplicate-catalog defect and SL-3's integrity test will fail.

- **Single-writer files**:
  - `.claude/docs-catalog.json`: SL-1 (one-shot during cherry-pick conflict resolve) → SL-3 (content owner post-reconciliation) → SL-docs (rescan only). Enforce this ordering via DAG dependency — no two of these may merge concurrently.
  - `CHANGELOG.md`: SL-1 (brings in the P18 block via cherry-pick) → SL-5 (surgical header-rename) → SL-docs (no edits).
  - `docs/security/sandbox.md`: SL-1 brings the P18 section via cherry-pick; SL-5 adds the cross-link only.
  - `specs/phase-plans-v1.md`: SL-1 brings the P18 amendments via cherry-pick; SL-docs may append P19 amendments.

- **Known destructive changes**: SL-1 runs `git reset --hard 2e574df` on local `main` (destructive to local main history only; `977c82f` is preserved via the cherry-pick + `pre-p19-main` backup tag + local reflog). No file-level deletions. Every other lane is purely additive.

- **Expected add/add conflicts**: none. SL-1 lands the cherry-pick before any other lane starts, so the catalog/CHANGELOG/sandbox.md are already at their post-P18 shape when SL-2..SL-5 spawn.

- **SL-0 re-exports**: no SL-0 preamble in this phase (SL-1 serves the same role but through git-operations rather than code stubs). Not applicable.

- **Worktree naming**: `execute-phase` allocates unique worktree names via `scripts/allocate_worktree_name.sh` if present; if absent (confirmed absent at plan time), the orchestrator falls back to `worktree-lane-p19-<SL-ID>-<ISO>` naming. Record the scheme used in the run summary.

- **Stale-base guidance** (copy verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-SL-1 (i.e., `git merge-base HEAD origin/main` resolves to a commit older than SL-1's tip), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge. SL-2, SL-3, SL-4, SL-5 all consume SL-1's reconciliation; do **not** spawn any of them until SL-1 has pushed to `origin/main` successfully.

- **CI-green precondition for SL-1 push**: `git push origin main` must be fast-forward. If `origin/main` has advanced since SL-1's `git fetch` (e.g., a concurrent operator push), SL-1 halts, re-fetches, and either re-applies on top or surfaces for human decision. **No force-push to origin is allowed under any circumstance.**

- **First push to origin in 114 commits**: CI against a 114-commit delta carries flaky-test risk on a first green run. Budget one automatic CI retry before declaring SL-1 failed. Actual test failures (not flakes) halt and surface.

- **Tag cut semantics**: `v1.2.0-rc1` is an RC tag. Semver `1.2.0` is reserved for the promoted production cut in P20. Tag message: `P19 release candidate — full P12–P18 feature set, pre-GA`.

- **`test-authenticated` CI job** (SL-1.3): gated on `secrets.ATTESTATION_GH_TOKEN` — skipped on forks and contributor PRs; runs on pushes to main and scheduled nightly. If the secret is absent in the repo's current settings, SL-1.3 still registers the job (with a `continue-on-error: true` and a visible skip log) so operators can wire the secret later without a further workflow edit. Record whether the secret is set in the SL-1 commit message.

- **P20 follow-up**: the 3 `TestAttest` tests are marker-gated rather than properly-mocked because `_check_gh_auth_for_attestations` in `mcp_server/artifacts/attestation.py` is not currently mockable from test scope. The tactical gate is acceptable for P19, but P20 or a follow-up lane should refactor the prereq check for proper unit-test mockability.

- **`scaffold_docs_catalog.py` scope cap** (SL-3): keep the initial tool ≤150 LOC. Features: `--check <catalog>` (read-only validation, exit 0/1), `--rescan <catalog>` (drop entries pointing at missing files, bump `generated_at`). **No** auto-discovery of new docs — new entries are still a human review step. SL-docs uses `--rescan` only to refresh `generated_at` and prune any orphans; new entries for SL-4's `p18-upgrade.md` are added manually in SL-docs.2.

## Acceptance Criteria

- [ ] `git rev-parse main` resolves to a descendant of `2e574df`, carrying `977c82f`'s legitimate changes (all 7 files) minus the 3-line duplicate catalog entry. Verified: `grep -c 'environment-variables.md' .claude/docs-catalog.json` returns `1`.
- [ ] `git ls-remote origin main` returns a SHA equal to `git rev-parse main` (fast-forward push succeeded). Verified by `git push origin main && git fetch origin && git merge-base --is-ancestor origin/main main`.
- [ ] CI on `origin/main` reports green on the post-push commit. Verified by `gh run list --branch main --limit 1 --json status,conclusion` (or manual CI UI check).
- [ ] `./.venv/bin/pytest --no-cov --ignore=tests/real_world -q` reports `0 failed` on the post-SL-2 state.
- [ ] `RUN_GH_AUTHENTICATED_TESTS=1 ./.venv/bin/pytest tests/security/test_artifact_attestation.py::TestAttest -m requires_gh_auth --collect-only -q` lists exactly 3 tests (verifies the marker applied correctly).
- [ ] `./.venv/bin/pytest tests/test_docs_catalog_integrity.py -q` passes.
- [ ] `./.venv/bin/pytest tests/test_p16_vocabulary.py::test_validate_production_config_signature -q` passes.
- [ ] `test -f docs/operations/p18-upgrade.md && test -f scripts/preflight_upgrade.sh && test -x scripts/preflight_upgrade.sh`.
- [ ] `./.venv/bin/pytest tests/test_preflight_upgrade.py -q` passes.
- [ ] `bash scripts/preflight_upgrade.sh tests/fixtures/preflight_happy.env` exits `0` with no `[FATAL]` lines; `bash scripts/preflight_upgrade.sh tests/fixtures/preflight_fatal.env` exits `1` with `[FATAL]` lines (fixtures provided by SL-4.1 test setup).
- [ ] `grep -c '## \[1.2.0-rc1\]' CHANGELOG.md` returns `1`; `grep -c '## \[Unreleased\]' CHANGELOG.md` returns `1`.
- [ ] `grep -c 'p18-upgrade.md' docs/security/sandbox.md` returns at least `1`.
- [ ] `git tag -l v1.2.0-rc1` returns `v1.2.0-rc1`; `git ls-remote --tags origin v1.2.0-rc1` returns a match.
- [ ] `python3 -c 'from mcp_server import __version__; assert __version__ == "1.2.0rc1", __version__'` passes.
- [ ] No commit on the final `origin/main` has a `tests/test_*` file with a red xfail status or a `pytest.mark.xfail` marker added in this phase (prevents rug-sweep).

## Verification

After all lanes merge and SL-docs completes, run end-to-end from a clean shell:

```bash
# 0. Fetch latest
git fetch origin

# 1. Confirm we are at the tagged RC
git checkout v1.2.0-rc1
python3 -c 'from mcp_server import __version__; print(__version__)'
# expect: 1.2.0rc1

# 2. Full-suite regression (default markers only)
./.venv/bin/pytest --no-cov --ignore=tests/real_world -q
# expect: 0 failed

# 3. Opt-in gh-auth suite (requires gh CLI with attestations:write scope)
RUN_GH_AUTHENTICATED_TESTS=1 ./.venv/bin/pytest tests/security/test_artifact_attestation.py::TestAttest -q
# expect: 3 passed (if gh token has scope) or 3 errored-during-execution (if token scoped wrong)
# Either outcome proves the marker gate + test wiring are live.

# 4. Docs-catalog integrity
./.venv/bin/pytest tests/test_docs_catalog_integrity.py -q
python3 .claude/skills/_shared/scaffold_docs_catalog.py --check .claude/docs-catalog.json
echo "catalog exit: $?"
# expect: 0

# 5. Preflight script — happy path
bash scripts/preflight_upgrade.sh tests/fixtures/preflight_happy.env
echo "preflight happy exit: $?"
# expect: 0

# 6. Preflight script — fatal path
bash scripts/preflight_upgrade.sh tests/fixtures/preflight_fatal.env
echo "preflight fatal exit: $?"
# expect: 1, with at least one [FATAL] line in stderr

# 7. Release-notes shape
grep -n '^## \[' CHANGELOG.md | head -5
# expect: [Unreleased] then [1.2.0-rc1] — <date> as first two entries

# 8. Sandbox cross-link
grep -n 'p18-upgrade' docs/security/sandbox.md
# expect: at least one match

# 9. CI latest run
gh run list --branch main --limit 1 --json status,conclusion,url
# expect: conclusion = "success"
```

Any failure of steps 2–9 is a regression; file as a follow-up lane within P19 (do not proceed to P20).

---

## Pre-approval checklist (main thread)

- [x] Disjoint file ownership: verified lane-by-lane; single-writer conflicts on catalog, CHANGELOG, sandbox.md, specs resolved via DAG dependency ordering.
- [x] DAG acyclic: SL-1 → {SL-2, SL-3, SL-4} → SL-5 → SL-docs.
- [x] Every `impl` task has a preceding `test` task in the same lane.
- [x] Acceptance criteria are testable (no prose-only asserts).
- [x] Grep assertions are always paired with a pytest invocation.
- [x] Interface freeze gates name concrete symbols / scripts / schema.
- [x] Stale-base resilience documented (SL-2..SL-5 must verify post-SL-1 base).
- [x] Cross-lane destructive changes called out (SL-1 `git reset --hard`).
- [x] Expected add/add conflicts: none within the phase (SL-1's conflict is cherry-pick-internal, not a lane-merge conflict).
- [x] Terminal SL-docs lane present with `Depends on:` covering SL-1..SL-5.
- [ ] `scripts/validate_plan_doc.py` — **not present in this repo**; skipped. Manual validation performed against the plan-phase skill's checklist.

## Handoff notes for `/execute-phase`

- Start team `phase-p19`.
- **Crucial**: do not parallelize SL-1 with anything. Spawn it alone; wait for SL-1 to push to `origin/main` and tag before spawning SL-2..SL-5.
- The three `TestAttest` tests marker-gated in SL-2 are test-infrastructure debt that P20 is expected to revisit — flag in the P20 handoff.
- If the fast-forward push in SL-1 fails for non-FF reasons, **halt the phase and surface to the user**. No force-push is permitted.
- If CI is red on the first push, allow one automatic retry (flake budget); further failures land a fix-forward lane within P19.
