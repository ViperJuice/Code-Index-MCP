# PHASE-6A-dependency-hygiene: Phase 6A — Dependency Hygiene

> Plan doc produced by `/plan-phase P6A` against `specs/phase-plans-v1.md` lines 357–382. On approval, this is saved to `plans/phase-plan-v1-p6a.md` and handed off to `/execute-phase p6a`.

## Context

P1 is merged. P6A is parallel-safe because it doesn't touch the hot dispatcher path. Three hygiene problems are bundled, with two of them coupled via `pyproject.toml` so the lanes are 3-wide but the DAG has one edge (SL-1 blocks SL-2).

1. **Password stack + pyproject restructure (SL-1).** `mcp_server/security/auth_manager.py:82-106` defines `PasswordManager` with `passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")`. `pyproject.toml:25-49` pins `passlib[bcrypt]>=1.7.4,<2.0.0` + `bcrypt>=3.0.0,<4.0.0`; the `<4.0.0` ceiling is forced by passlib 1.7.4's incompatibility with bcrypt 4.x. `PasswordManager` public surface: `hash_password(password: str) -> str`, `verify_password(plain, hashed) -> bool`, `is_strong_password(...) -> bool`. `IPasswordManager` interface at `mcp_server/interfaces/security_interfaces.py:115-133` exists but is not inherited by the concrete class. Call sites: `auth_manager.py:197` (hash via `create_user`), `auth_manager.py:252` (verify via `authenticate_user`), plus `gateway.py` (two `create_user` calls). Hash storage is in-memory only (dict `AuthManager.users` + `User.hashed_password: str`); no DB, migrations, or fixtures with hardcoded hashes. Existing tests: `tests/test_security.py` (514 lines). `pyproject.toml` additionally needs a `[project.optional-dependencies.dev]` extension — `requirements-dev.txt` carries **28 packages not currently declared in pyproject** (`hypothesis`, `factory-boy`, `bandit`, `safety`, `ipython`, `jupyter`, `sphinx`, etc.) — and a new `[project.optional-dependencies.production]` group for `redis` (already imported by `mcp_server/cache/backends.py`), `asyncpg`, `sqlalchemy`, `alembic`, `PyJWT` (all pinned in the disconnected `requirements-production.txt`). Because all pyproject edits land in one file, P6A gives the entire `pyproject.toml` to a single owner lane to satisfy the disjointness constraint.

2. **Legacy requirements + docs + Makefile cleanup (SL-2).** Repo has **five** `requirements*.txt` files (the spec undercounts as four): `requirements.txt` (7-line aggregator), `requirements-core.txt` (38 lines), `requirements-dev.txt` (70 lines), `requirements-production.txt` (82 lines, currently disconnected from pyproject), `requirements-semantic.txt` (39 lines). `Makefile:61` still runs `pip install -r requirements.txt` (not `uv sync`). Python-version docs drift: `docs/DEPLOYMENT-GUIDE.md:20` says "Python: 3.10 or higher" and `:21` says `FROM python:3.11-slim`, both conflicting with pyproject's `requires-python = ">=3.12"`. `docs/GETTING_STARTED.md:7` already says "3.12 or higher" (consistent). `AGENTS.md` and root `README.md` carry **no** Python-version claim — spec criterion #4 mentions them but there is nothing to reconcile (flagged in Execution Notes as a spec inaccuracy). `.github/workflows/*.yml` already pin Python 3.12 consistently.

3. **Scripts literal-string sweep (SL-3).** The bug: `Path("PathUtils.get_workspace_root()/...")` passes a literal string to `Path(...)`; the correct form is `PathUtils.get_workspace_root() / "..."`. Spec says "10 script-level hits"; actual ripgrep count is **20 occurrences across 17 scripts** (full list in SL-3's Owned files). None of these scripts are invoked by `pytest` (`pytest.ini testpaths = tests`) or CI. `PathUtils.get_workspace_root()` at `mcp_server/core/path_utils.py:39-61` returns `Path`, no side effects.

## Interface Freeze Gates

P6A introduces no new shared types or APIs consumed by downstream lanes. All changes are internal refactors, deletions, or edits to existing public signatures that are preserved (not broken). No `IF-0-P6A-*` gates required.

## Lane Index & Dependencies

```
SL-1 — Auth stack + pyproject.toml restructure
  Depends on: (none)
  Blocks: SL-2
  Parallel-safe: yes

SL-2 — Legacy requirements + Makefile + docs cleanup
  Depends on: SL-1
  Blocks: (none)
  Parallel-safe: yes

SL-3 — Scripts PathUtils literal-string sweep
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes
```

DAG is acyclic. SL-3 runs in parallel with SL-1 and (after SL-1 merges) with SL-2.

## Lanes

### SL-1 — Auth stack + pyproject.toml restructure

- **Scope**: Replace `passlib[bcrypt]` with `argon2-cffi` in `PasswordManager`. Lift the `bcrypt<4.0.0` ceiling. Preserve the public interface (`hash_password`, `verify_password`, `is_strong_password`) — add a separate `needs_rehash(hashed: str) -> bool` helper so `AuthManager.authenticate_user` can perform rehash-on-login without leaking persistence concerns into the verifier. Make `PasswordManager` inherit from `IPasswordManager`. In the same lane, restructure `pyproject.toml`: swap the core deps (remove passlib, lift bcrypt ceiling, add argon2-cffi), migrate the 28 currently-undeclared dev extras from `requirements-dev.txt` into `[project.optional-dependencies.dev]`, create a new `[project.optional-dependencies.production]` group covering `redis`, `asyncpg`, `sqlalchemy`, `alembic`, `PyJWT` with loose bounds. `requires-python = ">=3.12"` stays as-is.
- **Owned files**: `pyproject.toml`, `mcp_server/security/auth_manager.py`, `mcp_server/interfaces/security_interfaces.py`, `tests/test_security.py`
- **Interfaces provided**: `PasswordManager.needs_rehash(hashed: str) -> bool` (new helper, wraps `argon2.PasswordHasher.check_needs_rehash` + bcrypt-prefix guard). Existing signatures preserved.
- **Interfaces consumed**: `IPasswordManager` (pre-existing)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_security.py` (extend `TestPasswordManager`) | `hash_password` emits `$argon2id$` prefix; `verify_password` accepts argon2 hash; `verify_password` accepts a hand-crafted legacy bcrypt `$2b$…` fixture hash; `needs_rehash` returns True for the bcrypt fixture + False for a freshly-made argon2 hash at current params; wrong-password rejection for both hash formats; `isinstance(PasswordManager(), IPasswordManager)` holds | `.venv/bin/pytest tests/test_security.py::TestPasswordManager -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/security/auth_manager.py`, `mcp_server/interfaces/security_interfaces.py`, `pyproject.toml` | — | — |
| SL-1.3 | verify | SL-1.2 | SL-1 owned files | all `TestPasswordManager` + `TestAuthManager` + integration cases | `.venv/bin/pytest tests/test_security.py -v && uv sync --frozen` |

**Compat-verifier contract**
- `hash_password(password)` → always argon2id (`$argon2id$` prefix).
- `verify_password(plain, hashed)` → `bool`. Routes by prefix: `$argon2` → argon2-cffi; `$2b$` / `$2a$` → `bcrypt.checkpw`. Signature unchanged.
- `needs_rehash(hashed)` → `True` for bcrypt hashes or argon2 hashes at stale params; `False` otherwise.
- `AuthManager.authenticate_user` (line 252): on successful `verify_password`, call `needs_rehash`; if True, `user.hashed_password = self.password_manager.hash_password(plain)`.

**pyproject.toml restructure details**
- Core `dependencies = [...]`: remove `passlib[bcrypt]>=1.7.4,<2.0.0`; remove `<4.0.0` bound on bcrypt (become `bcrypt>=4.0.0`); add `argon2-cffi>=23.1.0`.
- `[project.optional-dependencies.dev]`: append the 28 undeclared packages from `requirements-dev.txt` (loose bounds — exact pins live in `uv.lock`): `aiofiles, asynctest, bandit, coverage[toml], factory-boy, faker, flake8, freezegun, hypothesis, ipdb, ipython, jupyter, line-profiler, memory-profiler, myst-parser, pydocstyle, pylint, py-spy, pytest-httpx, radon, responses, safety, sphinx, sphinx-rtd-theme, tabulate, types-requests, types-setuptools`.
- New `[project.optional-dependencies.production]`: `redis>=5.0`, `asyncpg>=0.29`, `sqlalchemy>=2.0`, `alembic>=1.13`, `PyJWT>=2.8`.
- Update `all` aggregator to include the new `production` group.

### SL-2 — Legacy requirements + Makefile + docs cleanup

- **Scope**: After SL-1 merges pyproject, delete the five `requirements*.txt` files, update `Makefile:61` from `pip install -r requirements.txt` to `uv sync`, fix `docs/DEPLOYMENT-GUIDE.md` Python-version claims (`3.10` → `3.12`; `python:3.11-slim` → `python:3.12-slim`), regenerate `uv.lock` against the SL-1 pyproject.
- **Owned files**: `requirements.txt`, `requirements-core.txt`, `requirements-dev.txt`, `requirements-production.txt`, `requirements-semantic.txt`, `Makefile`, `docs/DEPLOYMENT-GUIDE.md`, `uv.lock`, `tests/test_requirements_consolidation.py`
- **Interfaces provided**: (none)
- **Interfaces consumed**: (none)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_requirements_consolidation.py` (NEW) | no `requirements*.txt` files remain at repo root (`glob('requirements*.txt')` empty); `uv.lock` exists and parses; `grep -q '3\.10 or higher\|python:3\.11' docs/DEPLOYMENT-GUIDE.md` returns nonzero; `grep -q 'pip install -r requirements' Makefile` returns nonzero; `uv sync --frozen` exits 0 | `.venv/bin/pytest tests/test_requirements_consolidation.py -v` |
| SL-2.2 | impl | SL-2.1 | all SL-2 owned files | — | — |
| SL-2.3 | verify | SL-2.2 | all SL-2 owned files | all SL-2 tests + `uv sync --frozen` smoke | `.venv/bin/pytest tests/test_requirements_consolidation.py -v && uv sync --frozen` |

### SL-3 — Scripts PathUtils literal-string sweep

- **Scope**: Fix every `Path("PathUtils.get_workspace_root()/...")` literal-string occurrence under `scripts/` to use the actual method call `PathUtils.get_workspace_root() / "..."`.
- **Owned files** (17 scripts, 20 occurrences):
  - `scripts/analyze_path_mismatch.py`
  - `scripts/check_test_indexes.py`
  - `scripts/claude_code_behavior_simulator.py`
  - `scripts/comprehensive_real_analysis.py`
  - `scripts/comprehensive_semantic_analysis.py`
  - `scripts/consolidate_real_performance_data.py`
  - `scripts/continue_mcp_indexing.py`
  - `scripts/edit_pattern_analyzer.py`
  - `scripts/enhanced_mcp_analysis_framework.py`
  - `scripts/index_all_repos_semantic_full.py`
  - `scripts/index_all_repos_semantic_simple.py`
  - `scripts/patch_mcp_server.py`
  - `scripts/real_strategic_recommendations.py`
  - `scripts/realtime_parallel_analyzer.py`
  - `scripts/reindex_current_repo.py`
  - `scripts/run_comprehensive_query_test.py`
  - `tests/test_scripts_pathutils.py`
- **Interfaces provided**: (none)
- **Interfaces consumed**: `PathUtils.get_workspace_root()` (pre-existing)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_scripts_pathutils.py` (NEW) | Grep assertion: no file under `scripts/` matches the pattern `Path\("PathUtils\.get_workspace_root\(\)`; `PathUtils.get_workspace_root()` returns a `Path` whose parent exists; `compile(open(s).read(), s, 'exec')` succeeds for every owned script (syntax smoke) | `.venv/bin/pytest tests/test_scripts_pathutils.py -v` |
| SL-3.2 | impl | SL-3.1 | all 16 scripts listed above | — | — |
| SL-3.3 | verify | SL-3.2 | SL-3 owned files | all SL-3 tests | `.venv/bin/pytest tests/test_scripts_pathutils.py -v` |

Specific hit lines per file (for the impl to target, not part of the owned-glob contract): `analyze_path_mismatch.py:84,96`; `check_test_indexes.py:67`; `claude_code_behavior_simulator.py:27`; `comprehensive_real_analysis.py:656`; `comprehensive_semantic_analysis.py:697`; `consolidate_real_performance_data.py:455`; `continue_mcp_indexing.py:31,51`; `edit_pattern_analyzer.py:623`; `enhanced_mcp_analysis_framework.py:639`; `index_all_repos_semantic_full.py:214`; `index_all_repos_semantic_simple.py:39`; `patch_mcp_server.py:16,17,396`; `real_strategic_recommendations.py:909`; `realtime_parallel_analyzer.py:551`; `reindex_current_repo.py:19`; `run_comprehensive_query_test.py:352`. If the sweep reveals further hits (spec-count drift), fix those too.

## Execution Notes

- **Single-writer files**: `pyproject.toml` is exclusively owned by SL-1. SL-2 does not touch `pyproject.toml` — only `uv.lock` (regenerated from SL-1's final pyproject via `uv sync`). This is the cost of the single-owner discipline: SL-1's scope is slightly wider than pure "auth stack" so that SL-2 doesn't need to co-edit pyproject.

- **DAG edge**: SL-2 depends on SL-1's merge. Practically, the SL-2 teammate can START work (write `tests/test_requirements_consolidation.py`, plan the Makefile edit) in parallel with SL-1, but must rebase onto SL-1's merge commit before running its impl (otherwise `uv sync` produces a lockfile that still has passlib pins). `execute-phase`'s state machine handles this: SL-2 waits for SL-1's `verify-ok` transition before dispatch.

- **Known destructive changes** (stale-base whitelist — consumed by `pre_merge_destructiveness_check.sh`):
  - SL-1: removal of `passlib[bcrypt]>=1.7.4,<2.0.0` line and the `<4.0.0` specifier on the bcrypt line from `pyproject.toml`.
  - SL-2: deletion of `requirements.txt`, `requirements-core.txt`, `requirements-dev.txt`, `requirements-production.txt`, `requirements-semantic.txt`. In-place edit (not deletion) of `Makefile:61` and `docs/DEPLOYMENT-GUIDE.md:20-21`. Regeneration (not deletion) of `uv.lock`.
  - SL-3: no deletions — in-place string edits only.

- **Stale-base guidance** (copy verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-any upstream-SL's merge (SL-2's upstream being SL-1), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- ...` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge. P6 lost 3 of 10 lanes to exactly this pattern.

- **Harness preflight**: Before dispatch, orchestrator runs `bash ~/.claude/skills/execute-phase/scripts/verify_harness.sh`. All checks must pass.

- **Architectural choices (baseline Plan teammate, no `--consensus`)**:
  - `verify_password` keeps its `bool` return; rehash-on-login is driven by a separate `needs_rehash` helper called from `AuthManager.authenticate_user`. Rejected alternative: `bool | tuple[bool, str]` union return (breaks every caller in `tests/test_security.py` + `gateway.py`; leaks persistence concern into the verifier).
  - All 28 dev extras migrate into pyproject rather than being dropped (`hypothesis`, `bandit`, `safety`, `sphinx` are referenced by CI + docs workflows).
  - `requirements-production.txt` pins migrate to a new `[project.optional-dependencies.production]` group rather than being dropped — `redis` is actively imported by `mcp_server/cache/backends.py`.
  - SL-3 gates on a grep assertion + per-script `compile()` syntax smoke; no runtime import of the scripts is required since they're not in `pytest.ini testpaths`.

- **Spec inaccuracies logged for phase-plans v2**:
  1. Exit criterion #3 says "four requirements-*.txt files deleted"; there are actually five (`requirements.txt` is a separate aggregator).
  2. Exit criterion #4 references AGENTS.md / README Python-version claims; neither file contains any Python-version claim currently. `docs/DEPLOYMENT-GUIDE.md` and `docs/GETTING_STARTED.md` are the actual loci.
  3. Exit criterion #5 says "10 script-level hits"; actual ripgrep returns 20 occurrences across 17 scripts.

## Acceptance Criteria

- [ ] `.venv/bin/python -c "from argon2 import PasswordHasher; PasswordHasher().hash('x')"` exits 0 and the hash starts with `$argon2id$`.
- [ ] `.venv/bin/python -c "import passlib"` exits non-zero after `uv sync` (passlib removed from the venv).
- [ ] `.venv/bin/python -c "import bcrypt; assert int(bcrypt.__version__.split('.')[0]) >= 4"` exits 0.
- [ ] `PasswordManager` verifies a freshly-created argon2 hash AND a hand-crafted legacy bcrypt `$2b$…` fixture hash; `needs_rehash` returns True for the bcrypt fixture and False for the argon2 hash.
- [ ] `ls requirements*.txt 2>/dev/null | wc -l` outputs `0` (all five files deleted).
- [ ] `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert d['project']['requires-python'] == '>=3.12'"` exits 0.
- [ ] Every package in the pre-deletion `requirements-dev.txt` appears in `pyproject.toml[project.optional-dependencies.dev]` (assertion in `tests/test_requirements_consolidation.py`).
- [ ] `pyproject.toml[project.optional-dependencies]` contains a `production` key listing `redis`, `asyncpg`, `sqlalchemy`, `alembic`, `PyJWT`.
- [ ] `grep -q '3\.10 or higher\|python:3\.11' docs/DEPLOYMENT-GUIDE.md` exits non-zero.
- [ ] `grep -q 'pip install -r requirements' Makefile` exits non-zero.
- [ ] `rg -n 'Path\("PathUtils\.get_workspace_root\(\)' scripts/` produces zero hits.
- [ ] `uv sync --frozen` exits 0 against the post-SL-2 state.
- [ ] `.venv/bin/pytest tests/test_security.py tests/test_requirements_consolidation.py tests/test_scripts_pathutils.py -v` exits 0.

## Verification

```bash
# Pre-flight
bash ~/.claude/skills/execute-phase/scripts/verify_harness.sh

# Sync the environment to pick up P6A pyproject changes
uv sync

# argon2-cffi present
.venv/bin/python -c "
from argon2 import PasswordHasher
h = PasswordHasher().hash('testpassword')
assert h.startswith('\$argon2id\$'), h
print('argon2-cffi OK')
"

# passlib gone
.venv/bin/python - <<'PY'
try:
    import passlib  # noqa: F401
    raise SystemExit('FAIL: passlib still importable')
except ModuleNotFoundError:
    print('passlib removed OK')
PY

# bcrypt >=4
.venv/bin/python -c "import bcrypt; v=bcrypt.__version__; assert int(v.split('.')[0]) >= 4, v; print(f'bcrypt {v} OK')"

# Compat-verifier against both hash families
.venv/bin/python - <<'PY'
from mcp_server.security.auth_manager import PasswordManager
import bcrypt as _bc
pm = PasswordManager()
legacy = _bc.hashpw(b'hunter2', _bc.gensalt()).decode()
assert pm.verify_password('hunter2', legacy) is True
assert pm.needs_rehash(legacy) is True
modern = pm.hash_password('hunter2')
assert modern.startswith('\$argon2id\$')
assert pm.verify_password('hunter2', modern) is True
assert pm.needs_rehash(modern) is False
assert pm.verify_password('wrong', legacy) is False
assert pm.verify_password('wrong', modern) is False
print('compat-verifier OK')
PY

# Requirements files gone
test "$(ls requirements*.txt 2>/dev/null | wc -l)" -eq 0 && echo 'requirements cleanup OK' || echo 'FAIL: leftover requirements files'

# pyproject shape
.venv/bin/python -c "
import tomllib
d = tomllib.load(open('pyproject.toml','rb'))
assert d['project']['requires-python'] == '>=3.12'
opt = d['project']['optional-dependencies']
assert 'production' in opt and any(p.startswith('redis') for p in opt['production'])
print('pyproject shape OK')
"

# Docs + Makefile consistency
grep -q '3\.10 or higher\|python:3\.11' docs/DEPLOYMENT-GUIDE.md && echo 'FAIL: stale DEPLOYMENT-GUIDE Python claims' || echo 'DEPLOYMENT-GUIDE OK'
grep -q 'pip install -r requirements' Makefile && echo 'FAIL: Makefile still uses pip' || echo 'Makefile OK'

# Scripts sweep clean
rg -n 'Path\("PathUtils\.get_workspace_root\(\)' scripts/ && echo 'FAIL: literal strings remain' || echo 'scripts sweep OK'

# Lockfile frozen-resolve
uv sync --frozen && echo 'uv.lock frozen-resolve OK' || echo 'FAIL: uv.lock inconsistent with pyproject'

# Full targeted test suite
.venv/bin/pytest tests/test_security.py tests/test_requirements_consolidation.py tests/test_scripts_pathutils.py -v
```

---

### Hand-off

On ExitPlanMode approval, the orchestrator will:

1. Write this doc verbatim to `plans/phase-plan-v1-p6a.md` (replacing the earlier draft from the peer session).
2. Run `python ~/.claude/skills/plan-phase/scripts/validate_plan_doc.py plans/phase-plan-v1-p6a.md`. Fix any errors before proceeding.
3. Emit three `TaskCreate` calls (one per lane) with child `test / impl / verify` tasks and `Depends on` / `Blocks` / `Parallel-safe` metadata in the body.
4. User invokes `/execute-phase p6a` when ready.
