# P16: Shared Vocabulary Preamble

## Context

P14 + P15 merged. Upcoming P17 (durability & multi-instance) and P18 (enforcement + artifact resilience + ops) both depend on four shared contracts. If each phase defined them independently we'd get signature drift, circular imports (each phase touching the other's files), or an add/add merge storm on `core/errors.py`, `config/validation.py`, and `cli/bootstrap.py`. P16 is a single-lane preamble that freezes those four contracts — stubs only, no wiring — so P17 and P18 can run in parallel and each lane only fills bodies in files it already owns exclusively.

What exists today (verified by direct reads):

- **`mcp_server/core/errors.py`** — module docstring at `:1`; `MCPError(Exception)` base at `:26-45` (`__init__(message: str, details: Optional[Any] = None)`); `ArtifactError(MCPError)` subclass at `:118-121` with `pass` body. Existing siblings: `PluginError`, `IndexError`, `ConfigError`, `DocumentProcessingError`, `IndexingError`. No error taxonomy sub-classes of `ArtifactError` exist yet.
- **`mcp_server/config/validation.py`** — defines `validate_production_config(settings: Optional[Settings] = None) -> Dict[str, List[str]]` at `:252-294` that aggregates results from `validate_security_config` / `validate_database_config` / `validate_cache_config` / `validate_logging_config` / `validate_environment_variables` into a dict-of-lists. **It has zero callers outside this file** (grep-verified). No `ValidationError` class exists yet. The `mcp_server/config/__init__.py` re-exports it at `:27, :47`. The current signature does not match what IF-0-P16-3 requires (see below).
- **`mcp_server/config/env_vars.py`** — **does not exist**. No code in the repo imports it today (grep-verified). The precedent lazy pattern lives at `mcp_server/config/environment.py::get_environment()` `:40-66` — reads `os.getenv()` inside each call, no module-scope state. P15 SL-4's `_PATH_GUARD` was cited (roadmap-builder spec, line 855) as the anti-pattern that broke `monkeypatch.setenv` in tests; we deliberately avoid that here.
- **`mcp_server/cli/bootstrap.py`** — multi-line module docstring at `:1-8`; `initialize_stateless_services(registry_path=None)` at `:25-64` builds the process-wide service pool. No `reset_process_singletons` exists yet. Module-level singletons discovered via the Explore pass:

  | # | File | Attr |
  |---|---|---|
  | 1 | `mcp_server/metrics/prometheus_exporter.py:485` | `_exporter` |
  | 2 | `mcp_server/gateway.py:104` | `_repo_registry` |
  | 3 | `mcp_server/plugin_system/loader.py:325` | `_loader` |
  | 4 | `mcp_server/plugin_system/discovery.py:298` | `_discovery` |
  | 5 | `mcp_server/plugin_system/config.py:273` | `_config_manager` |
  | 6 | `mcp_server/plugins/memory_aware_manager.py:351` | `_manager_instance` (also `_manager_lock` on same line — do NOT null the lock) |

  `@lru_cache` decorators on instance methods (e.g. `dispatcher/plugin_router.py`, `security/path_allowlist.py`) are NOT reset here — per P17 spec they're per-call memoization of the current service pool, not process-lifetime singletons. P18 SL-5 does not touch these either.
- **Tests layout.** New contract-shape tests live under `tests/test_*.py`. Exemplar pattern: `tests/test_structured_errors.py:1-57` — module docstring tagging the phase + IF, direct imports from target modules, flat `test_<aspect>()` functions, `monkeypatch` for env manipulation. `tests/conftest.py:26-28` sets `JWT_SECRET_KEY` and `DEFAULT_ADMIN_PASSWORD` at module scope — ambient to every test. No repo-wide `mypy` / `tsc` baseline to hold; the AC here is `pytest --collect-only -q` exits 0.

Key constraint, declared up front: the IF-0-P16-3 signature in the **roadmap's freeze register** (`specs/phase-plans-v1.md:178`) is more specific than the one in the phase body (`:847`). We honor the register form: `validate_production_config(config: SecurityConfig, *, environment: str) -> list[ValidationError]`. `ValidationError` is a frozen dataclass `{code: str, message: str, severity: Literal["fatal","warn"]}`. Because the existing function has zero external callers, replacing the signature is non-breaking — the `__init__.py` re-export still works verbatim, and `ValidationError` gets added to `__all__`. The existing `validate_security_config` / `validate_database_config` / etc. sub-validators are left untouched; P18 SL-1 uses them to fill the body.

What constrains the design:

- **Single lane, by spec.** P16 Scope notes (`specs/phase-plans-v1.md:852`) explicitly invoke Rule 5 escape hatch: "Preamble / interface-only phase — single lane justified." Four tiny freezes, all additive in four files, none of which conflict with any P17 or P18 owned file. Decomposing into sub-lanes would add DAG + worktree overhead with no parallelism benefit.
- **Stubs-only discipline.** `validate_production_config` must return `[]` — downstream P18 SL-1 fills the fatal entries. `reset_process_singletons` has a real body (nulls the 6 attrs above) but has no consumer wiring in P16 — P17 SL-1 adds the `initialize_stateless_services` call-site. Env-var getters have real bodies but no callers yet. Error subclasses are `pass` bodies with class docstrings only. Any wiring pulled in here bleeds into P17 / P18 territory.
- **Owned-file lockdown.** Lane teammate must NOT edit `gateway.py`, `security_middleware.py`, `publisher.py`, `artifact_download.py`, `providers/github_actions.py`, `plugin_factory.py`, `sqlite_store.py`, or any watcher file. Those are P17/P18 territory per Scope notes `:854`. The only existing file that is modified is `core/errors.py` (additive only — three new classes at file end), `config/validation.py` (additive class + signature replacement, no deletion of existing helpers), `config/__init__.py` (one line added to imports, one line added to `__all__`), and `cli/bootstrap.py` (one new function, additive only). Two new files created: `mcp_server/config/env_vars.py`, `tests/test_p16_vocabulary.py`.
- **Repo-specific gotcha (from the phase-roadmap-builder handoff).** `.claude/skills/_shared/scaffold_docs_catalog.py` is absent — confirmed via `ls ~/.claude/skills/_shared/`. SL-docs must skip the catalog rescan step, as every prior phase has done. Pattern lifted from `plans/phase-plan-v1-p15.md` SL-docs.

What this phase does NOT change:

- No startup wiring. `initialize_stateless_services` is NOT modified (P17 SL-1 adds the `reset_process_singletons()` call). `validate_production_config` has no caller added in P16.
- No changes to existing sub-validators (`validate_security_config`, etc.) or the `Settings` shape.
- No changes to `MCPError` base class constructor or `ArtifactError`'s class body.
- No migration of existing env-var reads in `mcp_server/` to the new getters — that is a P17 / P18 concern (the consumer lanes do the substitution inside their own owned files). P16 just provides the getters.

## Interface Freeze Gates

- [ ] **IF-0-P16-1** — Error taxonomy. Three new classes appended to `mcp_server/core/errors.py`, all subclassing `ArtifactError`:
  - `class TransientArtifactError(ArtifactError): """Retryable artifact failure (rate-limit, network blip, 5xx)."""`
  - `class TerminalArtifactError(ArtifactError): """Non-retryable artifact failure (403, missing scopes, corrupt bundle)."""`
  - `class SchemaMigrationError(ArtifactError): """Raised when a schema migration apply step fails; caller must roll back."""`
  - All three inherit the existing `MCPError.__init__(message: str, details: Optional[Any] = None)` unchanged — no custom ctors.
- [ ] **IF-0-P16-2** — Lazy-read env-var module. New file `mcp_server/config/env_vars.py` exports five getter functions (each reads `os.getenv()` on every call — no module-scope caching, no `functools.lru_cache`, no module-scope assignments that read env):
  - `def get_max_file_size_bytes() -> int` — reads `MCP_MAX_FILE_SIZE_BYTES`, default `10 * 1024 * 1024` (10 MiB); `int(os.getenv(..., default))`.
  - `def get_artifact_retention_count() -> int` — reads `MCP_ARTIFACT_RETENTION_COUNT`, default `10`.
  - `def get_artifact_retention_days() -> int` — reads `MCP_ARTIFACT_RETENTION_DAYS`, default `30`.
  - `def get_disk_readonly_threshold_mb() -> int` — reads `MCP_DISK_READONLY_THRESHOLD_MB`, default `100`.
  - `def get_publish_rollback_enabled() -> bool` — reads `MCP_PUBLISH_ROLLBACK_ENABLED`; truthy if `os.getenv(...).strip().lower() in {"1","true","yes","on"}`; default `True` (rollback on by default — P18 SL-2 relies on this).
  - Module must import only `os` at module scope; no side effects at import time.
- [ ] **IF-0-P16-3** — Production validation surface. In `mcp_server/config/validation.py`:
  - New frozen dataclass `@dataclass(frozen=True) class ValidationError:` with fields `code: str`, `message: str`, `severity: Literal["fatal","warn"]`. Import `dataclass` from `dataclasses` and `Literal` from `typing`.
  - Replace the body of `validate_production_config`. New signature: `def validate_production_config(config: "SecurityConfig", *, environment: str = "production") -> list[ValidationError]:`. P16 body returns `[]` unconditionally. Keep the existing helper functions (`validate_security_config`, `validate_database_config`, `validate_cache_config`, `validate_logging_config`, `validate_environment_variables`) untouched; P18 SL-1 will call them from the new body. `SecurityConfig` is imported under a `TYPE_CHECKING` guard (verified location: `mcp_server/security/models.py:146` — grep-checked, no `mcp_server/security/config.py` exists) to avoid creating a new runtime import cycle.
  - Update `mcp_server/config/__init__.py`: add `ValidationError` to the `from .validation import (...)` import block and to `__all__`.
- [ ] **IF-0-P16-4** — Process singleton reset. In `mcp_server/cli/bootstrap.py`, new module-level function `def reset_process_singletons() -> None:`. Body sets each of the six module-level singleton attrs (table above) to `None` via `setattr(module, "_attr", None)`, tolerating `ImportError` per-module (imports are wrapped in `try: import ...; except ImportError: pass` so a pruned install that lacks e.g. `prometheus_client` still lets the reset run). Does NOT touch `_manager_lock`. Does NOT wire a caller (P17 SL-1 adds the caller inside `initialize_stateless_services`).

## Lane Index & Dependencies

```
SL-1 — vocabulary freezes (errors, env_vars, validation, bootstrap reset)
  Depends on: (none)
  Blocks: SL-docs
  Parallel-safe: yes (single impl lane — no peer to race)

SL-docs — Documentation & spec reconciliation (terminal)
  Depends on: SL-1
  Blocks: (none)
  Parallel-safe: no (terminal)
```

## Lanes

### SL-1 — Vocabulary freezes

- **Scope**: Add the four frozen contracts listed in IF-0-P16-1…4. Stubs only; no consumer wiring; additive-only touches to existing files.
- **Owned files**: `mcp_server/core/errors.py`, `mcp_server/config/env_vars.py` (new), `mcp_server/config/validation.py`, `mcp_server/config/__init__.py`, `mcp_server/cli/bootstrap.py`, `tests/test_p16_vocabulary.py` (new).
- **Interfaces provided**: `TransientArtifactError`, `TerminalArtifactError`, `SchemaMigrationError`, `get_max_file_size_bytes`, `get_artifact_retention_count`, `get_artifact_retention_days`, `get_disk_readonly_threshold_mb`, `get_publish_rollback_enabled`, `ValidationError` (dataclass), `validate_production_config` (new signature), `reset_process_singletons`.
- **Interfaces consumed**: existing `ArtifactError` from `mcp_server.core.errors`; existing `SecurityConfig` type-hint target from `mcp_server.security.config` (TYPE_CHECKING only); `os.getenv`.
- **Parallel-safe**: yes.

**Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_p16_vocabulary.py` (new) | see test outline below | `pytest -q tests/test_p16_vocabulary.py` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/core/errors.py` (append-only, after existing `ArtifactError`) | IF-0-P16-1 shape | `pytest -q tests/test_p16_vocabulary.py::test_error_taxonomy` |
| SL-1.3 | impl | SL-1.1 | `mcp_server/config/env_vars.py` (new) | IF-0-P16-2 shape | `pytest -q tests/test_p16_vocabulary.py::test_env_vars_lazy` |
| SL-1.4 | impl | SL-1.1 | `mcp_server/config/validation.py`, `mcp_server/config/__init__.py` | IF-0-P16-3 shape | `pytest -q tests/test_p16_vocabulary.py::test_validate_production_config` |
| SL-1.5 | impl | SL-1.1 | `mcp_server/cli/bootstrap.py` | IF-0-P16-4 shape | `pytest -q tests/test_p16_vocabulary.py::test_reset_process_singletons` |
| SL-1.6 | verify | SL-1.2, SL-1.3, SL-1.4, SL-1.5 | repo-wide | all SL-1 tests + repo collect | `pytest -q tests/test_p16_vocabulary.py && pytest --collect-only -q` |

**Test outline for `tests/test_p16_vocabulary.py`** (SL-1.1):

1. `test_error_taxonomy` — imports all three classes from `mcp_server.core.errors`; asserts each is a subclass of `ArtifactError`, which is a subclass of `MCPError`; instantiates each with `("msg", {"key":"val"})` and asserts `.message` and `.details` round-trip (confirms inherited `__init__` works).
2. `test_env_vars_lazy_no_import_side_effect` — deletes `mcp_server.config.env_vars` from `sys.modules` if present, sets all five env vars to sentinel values via `monkeypatch.setenv(...)`, imports the module, and asserts **none** of the getters have been called yet (introspect by monkeypatching `os.getenv` to record calls; import, assert recorded-calls-list is empty). Importing MUST NOT trigger any getter.
3. `test_env_vars_lazy_getters_read_on_each_call` — for each getter: set env var via `monkeypatch.setenv`, call, assert returned value matches; update env var; call again; assert new value reflected. Proves no cached state.
4. `test_env_vars_defaults` — clear each env var via `monkeypatch.delenv(..., raising=False)`, call getter, assert it returns the declared default.
5. `test_env_vars_boolean_parsing` — for `get_publish_rollback_enabled`: parametrize over `"1"`, `"true"`, `"True"`, `"TRUE"`, `"yes"`, `"on"` → True; `"0"`, `"false"`, `"no"`, `"off"`, `""` → False; unset → True (default).
6. `test_validation_error_dataclass` — asserts `ValidationError` is a frozen dataclass; instantiates `ValidationError(code="X", message="y", severity="fatal")`; asserts `dataclasses.fields(...)` names are `("code","message","severity")`; asserts mutating any field raises `FrozenInstanceError`; asserts `severity="warn"` is accepted (no runtime enforcement of `Literal`).
7. `test_validate_production_config_signature` — imports from `mcp_server.config`; calls `validate_production_config(object(), environment="production")`; asserts return is exactly `[]` and `list` (not `dict`). Also asserts `validate_production_config(object(), environment="dev")` returns `[]`. Asserts the function's signature via `inspect.signature` has params named `config` and (keyword-only) `environment`, and `environment` has default `"production"`.
8. `test_validate_production_config_reexported` — asserts `from mcp_server.config import ValidationError, validate_production_config` succeeds and both are in `mcp_server.config.__all__`.
9. `test_reset_process_singletons_nulls_all` — imports each of the six singleton-owning modules, sets each module-level attr to a sentinel object (not `None`), calls `reset_process_singletons()`, asserts each attr is `None`. Uses a parametrized list `[(module_path, attr_name), ...]` mirroring the Context table so the test drift-detects if a later phase adds / removes singleton sites (the phase author updates both the impl and this parametrized list).
10. `test_reset_process_singletons_leaves_lock_alone` — sets `_manager_lock` on `mcp_server.plugins.memory_aware_manager`, calls reset, asserts `_manager_lock is not None` (still a `Lock` instance).
11. `test_reset_process_singletons_tolerates_missing_module` — simulates a pruned install for one of the six modules (e.g. `mcp_server.metrics.prometheus_exporter`) by setting `sys.modules["mcp_server.metrics.prometheus_exporter"] = None` (the `None`-sentinel form raises `ImportError` on re-import; plain `del sys.modules[name]` would silently re-import from disk and not exercise the `except` branch). Call `reset_process_singletons()`; assert no exception. Restore `sys.modules` via `monkeypatch`.

Tests 1–11 collectively pin every bullet in IF-0-P16-1 through IF-0-P16-4 at shape level.

### SL-docs — Documentation & spec reconciliation

- **Scope**: Record that P16 frozen vocabulary exists, update env-var reference docs to include the five new `MCP_*` names with defaults, add each of the four freezes to the module docstrings / CHANGELOG, append any post-execution amendments if the freeze landed with any deviation. Terminal lane; mandatory per skill template.
- **Owned files**:
  - `.claude/docs-catalog.json` if present (skip catalog rescan — `scaffold_docs_catalog.py` absent in this repo per roadmap-builder handoff; pattern matches P14 / P15 SL-docs).
  - `docs/configuration/ENVIRONMENT-VARIABLES.md` — append a "P16 reserved (stub-only; not yet enforced)" subsection listing the five new vars with default values.
  - `CHANGELOG.md` — one bullet under an "Unreleased" heading noting P16 frozen contracts (taxonomy, env_vars getters, ValidationError dataclass, reset_process_singletons).
  - `specs/phase-plans-v1.md` — append `### Post-execution amendments` to the P16 section IF (and only if) any IF-0-P16-N signature drifted during SL-1 impl. If zero drift, record "no amendments" in the SL-docs commit message, do not edit the spec.
- **Interfaces provided**: (none)
- **Interfaces consumed**: (none)
- **Parallel-safe**: no (terminal)
- **Depends on**: SL-1

**Tasks**:

| Task ID | Type | Depends on | Files in scope | Action |
|---|---|---|---|---|
| SL-docs.1 | docs | — | `.claude/docs-catalog.json` | Skip rescan — `scaffold_docs_catalog.py` helper absent. Record rationale in commit message. Precedent: P14/P15 SL-docs. |
| SL-docs.2 | docs | SL-docs.1 | `docs/configuration/ENVIRONMENT-VARIABLES.md`, `CHANGELOG.md` | Append the P16 env-var section with defaults; append Unreleased CHANGELOG entry. |
| SL-docs.3 | docs | SL-docs.2 | `specs/phase-plans-v1.md` | Conditional: only edit if IF-0-P16-N drift was observed during SL-1; otherwise no-op with reason in commit. |
| SL-docs.4 | verify | SL-docs.3 | — | Repo has no markdownlint / vale configured (verify on first run). No-op if none present. |

## Execution Notes

- **Single-writer files**: None within this phase. `mcp_server/core/errors.py`, `mcp_server/config/validation.py`, `mcp_server/config/__init__.py`, `mcp_server/cli/bootstrap.py` are each owned by SL-1 only. No cross-lane file contention exists because there is only one impl lane.
- **Known destructive changes**: none — every touch is purely additive, except the `validate_production_config` body replacement. That replacement removes ~40 lines of existing dict-aggregation code that has zero external callers (grep-verified); the helper functions (`validate_security_config` etc.) it called are preserved untouched for P18 SL-1 to re-use. Call this out explicitly in the SL-1.4 commit message ("replaces body; zero external callers; helpers preserved") so the execute-phase stale-base check treats it as legitimate.
- **Expected add/add conflicts**: none — no SL-0 preamble stub precedes SL-1 (this phase IS the preamble for P17/P18).
- **SL-0 re-exports**: n/a — no SL-0 lane. The `mcp_server/config/__init__.py` edit (adding `ValidationError` to imports + `__all__`) is a direct surface addition, not a lazy re-export; acceptable here because `ValidationError` is a concrete dataclass, not a symbol that might be renamed later.
- **Worktree naming**: execute-phase allocates via `scripts/allocate_worktree_name.sh`. No plan-specified lane worktree paths needed.
- **Stale-base guidance**: Lane teammate working in isolated worktree does not see sibling merges automatically. Since P16 has only one impl lane (SL-1), stale-base risk is limited to the SL-docs lane reading a base that predates SL-1's merge. If SL-docs finds its worktree base is pre-SL-1, it MUST stop and report — do not silently `git reset --hard` or `git checkout HEAD~N -- …`. Lesson from P15 SL-4 publisher_race post-hoc fix.
- **Lazy-getter discipline check**: during SL-1.3 impl review, visually verify that `mcp_server/config/env_vars.py` has NO top-level `X = os.getenv(...)` or `X = int(os.environ.get(...))` statements. `test_env_vars_lazy_no_import_side_effect` (SL-1.1 test 2) mechanically enforces this, but a reviewer eyeball catches the case where a getter caches the first read in a module-level `_cache` dict. Do not add caching — P17/P18 tests depend on `monkeypatch.setenv` flipping values mid-test.
- **`ValidationError` vs `SecurityConfigurationError`**: existing `SecurityConfigurationError(MCPError)` at `mcp_server/config/validation.py` stays. The new `ValidationError` is a plain dataclass (not an exception) representing a single validation finding; callers decide whether to raise `SecurityConfigurationError` aggregating a non-empty `list[ValidationError]`. No name collision because the old class is an exception and the new one is a dataclass under a different name.
- **`TYPE_CHECKING` import for `SecurityConfig`**: `SecurityConfig` lives at `mcp_server/security/models.py:146` (grep-verified; `mcp_server/security/config.py` does NOT exist in this repo). Import under `from typing import TYPE_CHECKING; if TYPE_CHECKING: from mcp_server.security.models import SecurityConfig` so the validation module does not pull security at import time (which would defeat the preamble discipline — P18 SL-1 is the file that introduces the real runtime dep).

## Acceptance Criteria

- [ ] `pytest -q tests/test_p16_vocabulary.py` reports 0 failures, ≥11 tests passing.
- [ ] `python -c "from mcp_server.core.errors import TransientArtifactError, TerminalArtifactError, SchemaMigrationError, ArtifactError; assert all(issubclass(c, ArtifactError) for c in (TransientArtifactError, TerminalArtifactError, SchemaMigrationError))"` exits 0. *(Paired with `test_error_taxonomy` — grep alone is not sufficient.)*
- [ ] `python -c "import mcp_server.config.env_vars as m; import inspect; assert all(hasattr(m, n) for n in ('get_max_file_size_bytes','get_artifact_retention_count','get_artifact_retention_days','get_disk_readonly_threshold_mb','get_publish_rollback_enabled'))"` exits 0. *(Paired with `test_env_vars_lazy_*`.)*
- [ ] `python -c "from mcp_server.config import ValidationError, validate_production_config; from dataclasses import is_dataclass; assert is_dataclass(ValidationError); assert validate_production_config(object(), environment='production') == []"` exits 0. *(Paired with `test_validate_production_config_signature`.)*
- [ ] `python -c "from mcp_server.cli.bootstrap import reset_process_singletons; reset_process_singletons()"` exits 0 on a fresh interpreter (confirms the function is callable with no wiring in place). *(Paired with `test_reset_process_singletons_*`.)*
- [ ] `pytest --collect-only -q` exits 0 across the whole repo (proves no downstream test-module import broke when `validate_production_config`'s signature changed or when `ValidationError` was added to `__init__.py`).
- [ ] `grep -RnE "^[[:space:]]*[A-Z_]+ *= *(os\.getenv|os\.environ(\[|\.get))" mcp_server/config/env_vars.py` returns zero matches. *(Static anti-regression guard against the module-scope env-read pattern; paired with `test_env_vars_lazy_no_import_side_effect`.)*

## Verification

End-to-end commands to run after SL-1 + SL-docs merge:

```bash
# IF-0-P16-1..4 shape gate
pytest -q tests/test_p16_vocabulary.py

# Repo-wide import / collect gate (required by spec line 849)
pytest --collect-only -q

# Lazy-discipline anti-regression
! grep -RnE "^[[:space:]]*[A-Z_]+ *= *(os\.getenv|os\.environ(\[|\.get))" mcp_server/config/env_vars.py

# Existing P15 suite must not regress (covers the singleton sites we introspect)
pytest -q tests/security/

# Smoke: import bootstrap without calling initialize_stateless_services;
# reset_process_singletons must be callable on a virgin interpreter.
python -c "from mcp_server.cli.bootstrap import reset_process_singletons; reset_process_singletons(); print('ok')"
```

After all the above pass, the phase is ready for P17 and P18 to plan in parallel against the frozen vocabulary.
