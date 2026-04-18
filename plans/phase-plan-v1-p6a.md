# PHASE-6A-dependency-hygiene: Phase 6A — Dependency Hygiene

> **How to use this document**: this is the P6A lane plan produced by `/plan-phase P6A`. On approval, save it to `plans/phase-plan-v1-p6a.md` in the repo and emit one `TaskCreate` per lane (SL-1 / SL-2 / SL-3). Then run `/execute-phase p6a`.

## Context

P1 is merged. Three independent hygiene problems are cleanly separated:

1. **Password stack**: `mcp_server/security/auth_manager.py` imports `passlib.context.CryptContext` and calls `CryptContext(schemes=["bcrypt"], deprecated="auto")`. Both `pyproject.toml` and `requirements-core.txt` pin `passlib[bcrypt]>=1.7.4,<2.0.0` and `bcrypt>=3.0.0,<4.0.0` with an inline comment explaining the `<4.0.0` ceiling is due to passlib 1.7.4's incompatibility with bcrypt 4.x. `PasswordManager.hash_password` and `verify_password` are the only two call-sites. No existing auth tests.

2. **Requirements consolidation**: Five `requirements-*.txt` files exist (`requirements.txt`, `requirements-core.txt`, `requirements-dev.txt`, `requirements-production.txt`, `requirements-semantic.txt`) alongside `pyproject.toml` + `uv.lock`. `passlib`/`bcrypt` pins appear in three of them. `AGENTS.md` line 333 claims `Python Version: 3.8+ (from pyproject.toml)` but `pyproject.toml` actually says `requires-python = ">=3.12"`. The `requirements-*.txt` files are the only dependency source-of-truth gap.

3. **Scripts literal-string bug**: 10+ scripts pass `"PathUtils.get_workspace_root()/..."` as a string literal to `Path(...)` — a string that was never a real path. The correct form is `PathUtils.get_workspace_root() / "..."`. Affected files: `scripts/comprehensive_mcp_test_runner.py`, `scripts/create_performance_visualization.py`, `scripts/comprehensive_semantic_analysis.py`, `scripts/analyze_path_mismatch.py`, `scripts/index_all_repos_semantic_simple.py`, `scripts/check_test_indexes.py`, `scripts/task_based_mcp_testing.py`, `scripts/enhanced_mcp_analysis_framework.py`, `scripts/real_strategic_recommendations.py` (9 files confirmed; spec says 10 — sweep will catch any missed).

All three are parallel roots: they touch disjoint files and can be worktree-isolated without any cross-lane type contract.

## Interface Freeze Gates

P6A introduces no new shared types or APIs consumed by downstream lanes — all changes are internal refactors or deletions. No `IF-0` gates required.

## Lane Index & Dependencies

```
SL-1 — Password stack migration (passlib → argon2-cffi)
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-2 — Requirements consolidation + Python version alignment
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-3 — Scripts PathUtils literal-string sweep
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes
```

## Lanes

### SL-1 — Password stack migration (passlib → argon2-cffi)

- **Scope**: Replace `passlib[bcrypt]` with `argon2-cffi` in `auth_manager.py`, lift the `bcrypt<4.0.0` ceiling, and implement a backward-compat verifier (rehash-on-login for legacy `$2b$`/`$2a$` bcrypt hashes).
- **Owned files**: `mcp_server/security/auth_manager.py`, `tests/test_auth_manager.py` (NEW)
- **Interfaces provided**: (none — internal to auth_manager; callers use `PasswordManager.hash_password` / `verify_password` which retain their signatures)
- **Interfaces consumed**: (none from P6A peers)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_auth_manager.py` | `hash_password` returns argon2 hash (`$argon2id$` prefix); `verify_password` accepts argon2 hash; `verify_password` accepts legacy bcrypt hash and rehashes; `verify_password` rejects wrong password for both hash types | `.venv/bin/pytest tests/test_auth_manager.py -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/security/auth_manager.py` | — | — |
| SL-1.3 | verify | SL-1.2 | `mcp_server/security/auth_manager.py`, `tests/test_auth_manager.py` | all SL-1 tests | `.venv/bin/pytest tests/test_auth_manager.py -v` |

**Compat-verifier contract**: `verify_password(plain, hashed)`:
- If `hashed` starts with `$argon2` → verify via argon2-cffi. Return True/False.
- If `hashed` starts with `$2b$` or `$2a$` → verify via bcrypt. If match, rehash with argon2 and **return the new hash as a second return value** (caller stores it); if mismatch, return False. Signature: `verify_password(plain, hashed) -> bool | tuple[bool, str]`.

**pyproject.toml edit**: Remove `passlib[bcrypt]>=1.7.4,<2.0.0` and `bcrypt>=3.0.0,<4.0.0`; add `argon2-cffi>=23.1.0` and `bcrypt>=4.0.0` (no ceiling). SL-1 owns the `pyproject.toml` dep lines for these four packages only — SL-2 owns the rest of `pyproject.toml` restructuring.

> **Note**: SL-1 and SL-2 both touch `pyproject.toml` but at disjoint line ranges. SL-1 replaces the two passlib/bcrypt dep lines (lines 38-39 of dependencies list); SL-2 deletes the `requirements-*.txt` references and updates `requires-python` docs. Coordinate via stale-base rebase — do NOT use `git add -A` or overwrite the whole file.

### SL-2 — Requirements consolidation + Python version alignment

- **Scope**: Delete the four `requirements-*.txt` files (keep `requirements-dev.txt` if it contains dev-only extras not in `pyproject.toml[project.optional-dependencies]`; otherwise delete it too), make `pyproject.toml` + `uv.lock` the sole dependency source of truth, and fix the `AGENTS.md` Python version claim.
- **Owned files**: `requirements.txt`, `requirements-core.txt`, `requirements-production.txt`, `requirements-semantic.txt`, `requirements-dev.txt` (all DELETED if dev deps are covered by optional-dependencies), `AGENTS.md`, `pyproject.toml` (optional-dependencies section only — not the core dependencies list owned by SL-1)
- **Interfaces provided**: (none)
- **Interfaces consumed**: (none from P6A peers)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_requirements_consolidation.py` (NEW) | `pyproject.toml` parseable as valid TOML; no `requirements-*.txt` files exist post-merge; `requires-python` in pyproject equals `">=3.12"`; `AGENTS.md` does not contain `3.8` Python version claim; `uv.lock` exists | `.venv/bin/pytest tests/test_requirements_consolidation.py -v` |
| SL-2.2 | impl | SL-2.1 | `requirements.txt`, `requirements-core.txt`, `requirements-production.txt`, `requirements-semantic.txt`, `requirements-dev.txt`, `AGENTS.md`, `pyproject.toml` (optional-deps section) | — | — |
| SL-2.3 | verify | SL-2.2 | owned files | all SL-2 tests | `.venv/bin/pytest tests/test_requirements_consolidation.py -v` |

### SL-3 — Scripts PathUtils literal-string sweep

- **Scope**: Fix all script-level `Path("PathUtils.get_workspace_root()/...")` literal-string occurrences to call the actual method: `PathUtils.get_workspace_root() / "..."`.
- **Owned files**: `scripts/comprehensive_mcp_test_runner.py`, `scripts/create_performance_visualization.py`, `scripts/comprehensive_semantic_analysis.py`, `scripts/analyze_path_mismatch.py`, `scripts/index_all_repos_semantic_simple.py`, `scripts/check_test_indexes.py`, `scripts/task_based_mcp_testing.py`, `scripts/enhanced_mcp_analysis_framework.py`, `scripts/real_strategic_recommendations.py`, `tests/test_scripts_pathutils.py` (NEW)
- **Interfaces provided**: (none)
- **Interfaces consumed**: `PathUtils.get_workspace_root()` from `mcp_server/core/path_utils.py` (pre-existing, not a P6A gate)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_scripts_pathutils.py` | Grep-based assertion: no file under `scripts/` contains the pattern `Path("PathUtils.get_workspace_root()` (literal string); `PathUtils.get_workspace_root()` returns a `Path` that exists | `.venv/bin/pytest tests/test_scripts_pathutils.py -v` |
| SL-3.2 | impl | SL-3.1 | all 9 affected scripts | — | — |
| SL-3.3 | verify | SL-3.2 | owned files | all SL-3 tests | `.venv/bin/pytest tests/test_scripts_pathutils.py -v` |

## Execution Notes

- **Single-writer files**: `pyproject.toml` is co-touched by SL-1 (dep lines 38-39 only) and SL-2 (optional-dependencies section + any version metadata). The stale-base rebase discipline prevents clobber. SL-1 should edit only the `passlib`/`bcrypt` lines; SL-2 should edit only the optional-dependencies block. If both lanes land on main in the same merge wave, the second merger must rebase first.

- **Known destructive changes**:
  - SL-2 deletes: `requirements.txt`, `requirements-core.txt`, `requirements-production.txt`, `requirements-semantic.txt`. If `requirements-dev.txt` dev extras are already represented in `pyproject.toml[project.optional-dependencies]`, delete it too; otherwise migrate its extras first.
  - SL-1 removes the two passlib/bcrypt dep lines from `pyproject.toml` (net deletion of 2 lines in the dependencies list).
  - All other changes are purely additive or in-place edits.

- **Stale-base guidance** (copy verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-any-other-SL's merge, it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.

- **verify_harness.sh pre-flight**: Before dispatching lanes, run `bash ~/.claude/skills/execute-phase/scripts/verify_harness.sh main` (script now ships from dotfiles — the in-repo copy was removed in `78836d9` revert). All four checks must pass. If any fail, stop and fix before spawning worktrees.

- **bcrypt ceiling note**: `bcrypt>=4.0.0` (no ceiling) is safe once passlib is removed, since argon2-cffi's bcrypt compat path can import bcrypt directly without passlib's `__about__` shim.

## Acceptance Criteria

- [ ] `python -c "from argon2 import PasswordHasher; print(PasswordHasher().hash('x'))"` exits 0 and prints a `$argon2id$` hash (argon2-cffi installed).
- [ ] `python -c "import passlib"` exits non-zero (passlib removed from the venv after `uv sync`).
- [ ] `python -c "import bcrypt; print(bcrypt.__version__)"` prints `4.x.x` or higher (ceiling lifted).
- [ ] `ls requirements*.txt 2>/dev/null | wc -l` outputs `0` (all requirements files deleted).
- [ ] `grep '3\.8' AGENTS.md` exits non-zero (stale Python version claim removed).
- [ ] `grep -r 'Path("PathUtils.get_workspace_root()' scripts/` exits non-zero (no literal-string occurrences remain).
- [ ] `.venv/bin/pytest tests/test_auth_manager.py tests/test_requirements_consolidation.py tests/test_scripts_pathutils.py -v` exits 0.

## Verification

```bash
# Pre-flight harness check (script ships from dotfiles)
bash ~/.claude/skills/execute-phase/scripts/verify_harness.sh main

# Import smoke (run after uv sync)
.venv/bin/python -c "
from argon2 import PasswordHasher
ph = PasswordHasher()
h = ph.hash('testpassword')
assert h.startswith('\$argon2id\$'), f'Expected argon2id hash, got: {h}'
ph.verify(h, 'testpassword')
print('argon2-cffi OK')
"

# passlib gone
.venv/bin/python -c "import passlib" 2>&1 | grep -q "ModuleNotFoundError" && echo "passlib removed OK" || echo "FAIL: passlib still present"

# bcrypt version (must be >=4.x)
.venv/bin/python -c "import bcrypt; v=bcrypt.__version__; assert int(v.split('.')[0])>=4, f'bcrypt {v} < 4'; print(f'bcrypt {v} OK')"

# No requirements files
ls requirements*.txt 2>/dev/null && echo "FAIL: requirements files still exist" || echo "requirements files removed OK"

# Python version consistency
grep -q '3\.8' AGENTS.md && echo "FAIL: stale Python 3.8 claim in AGENTS.md" || echo "Python version claim OK"

# No literal-string PathUtils occurrences
grep -r 'Path("PathUtils.get_workspace_root()' scripts/ && echo "FAIL: literal strings remain" || echo "scripts sweep OK"

# Full test suite
.venv/bin/pytest tests/test_auth_manager.py tests/test_requirements_consolidation.py tests/test_scripts_pathutils.py -v
```
