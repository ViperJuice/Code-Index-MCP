# Phase roadmap v2

## Context

`specs/phase-plans-v1.md` is complete through P20. The current branch has a strong
runtime/test base but is not yet release-coherent for alpha:

- Runtime reports `1.2.0-rc2`, while `pyproject.toml` and README still advertise older
  versions.
- The repo intentionally uses `pyproject.toml` + `uv.lock` as dependency truth, but CI
  and Docker still reference removed `requirements*.txt` files.
- README/Docker docs advertise image names that do not match the release workflow.
- Customer docs, agent docs, and language support claims disagree about which plugins
  are production-quality under sandbox-default-on.
- The local broad suite passed (`1652 passed, 138 skipped, 29 deselected`), but several
  release gates are non-blocking and therefore cannot qualify a market release.

This roadmap is scoped to private-alpha readiness first, then public-alpha readiness.
It does not reopen v1 architectural work unless that work is required to make release
claims true.

## Architecture North Star

The releaseable product is a local-first MCP STDIO code indexer with a boring install
path, honest support matrix, and repeatable smoke gates. FastAPI remains a secondary
admin surface. Multi-repo and GitHub Artifact sync stay beta until the install,
container, and documentation contracts are reliable for new users.

## Assumptions

- `uv.lock` and `pyproject.toml` are the sole dependency source of truth.
- `mcp_server.__version__`, `pyproject.toml`, `CHANGELOG.md`, release tags, README, and
  container tags must agree before any alpha tag is cut.
- Private alpha may ship with a narrowed support matrix if unsupported languages are
  clearly marked and degrade quietly.
- Public alpha requires Docker and wheel install paths to pass in clean environments.
- `.index_metadata.json` remains uncommitted unless the user explicitly requests an
  index metadata refresh commit.

## Non-Goals

- No broad rewrite of dispatcher, storage, registry, watcher, or artifact architecture.
- No GA stability claim.
- No new language plugin families beyond fixing default-runtime breakage for currently
  advertised support.
- No production SaaS, hosted control plane, or external billing work.

## Cross-Cutting Principles

- Prefer one dependency/install contract over compatibility shims.
- Public docs must describe behavior that is exercised by blocking CI or explicit
  manual release smoke.
- Default runtime logs should distinguish expected unsupported capabilities from real
  failures.
- Phase boundaries exist only where downstream work needs a frozen release contract.

## Top Interface-Freeze Gates

- IF-0-P21-1 — Version source-of-truth contract: package metadata, runtime version,
  changelog, README status, release workflow input, and tag names agree on one
  pre-release version.
- IF-0-P21-2 — Dependency source-of-truth contract: all first-party install, CI, Docker,
  and release automation paths use `pyproject.toml`/`uv.lock`; `requirements*.txt` is
  not referenced by active release paths.
- IF-0-P22-1 — Release smoke contract: a clean checkout can build a wheel, install the
  wheel into a clean venv, start STDIO enough to list/help tools, and run a minimal
  index/search smoke.
- IF-0-P22-2 — Container contract: production Docker builds from the same dependency
  source of truth, uses the documented image name, and passes a local health/smoke run.
- IF-0-P23-1 — Support matrix contract: every advertised language/support tier has an
  explicit runtime behavior, sandbox status, required extras, and known limitation.
- IF-0-P24-1 — Sandbox degradation contract: unsupported sandbox languages and optional
  dependency misses are reported as capability-unavailable, not noisy runtime errors.
- IF-0-P25-1 — Blocking release gate contract: the required CI jobs for alpha are
  blocking and map directly to the release checklist.
- IF-0-P26-1 — Alpha evidence contract: private-alpha validation records install,
  indexing, query quality, multi-repo behavior, and rollback observations from real
  repositories before public-alpha launch.

## Phases

### Phase 21 — Release Contract & Dependency Unification (P21)

**Objective**

Make versioning, dependency installation, CI setup, and release automation internally
consistent before any packaging or docs work depends on them.

**Exit criteria**
- [ ] `mcp_server.__version__`, `pyproject.toml`, `CHANGELOG.md`, README status text,
      release tag, and release notes template all agree on the next alpha/RC version.
- [ ] Active workflows no longer install from removed `requirements*.txt` files.
- [ ] Production Dockerfiles no longer copy removed dependency files.
- [ ] Tests that enforce "no requirements files" also cover active workflow and Docker
      references.
- [ ] `uv sync --locked` and the narrow release-metadata tests pass locally.

**Scope notes**

Keep this phase mechanical. It should not improve Docker behavior beyond removing the
stale dependency contract. It should produce the contract consumed by P22.

**Non-goals**

- No public release.
- No plugin support-matrix edits.
- No broad workflow redesign beyond dependency/version correctness.

**Key files**

- `pyproject.toml`
- `mcp_server/__init__.py`
- `CHANGELOG.md`
- `README.md`
- `.github/workflows/*.yml`
- `docker/dockerfiles/Dockerfile.production`
- `docker/dockerfiles/Dockerfile*`
- `tests/test_requirements_consolidation.py`
- `tests/test_release_metadata.py`

**Depends on**
- (none)

**Produces**
- IF-0-P21-1 — Version source-of-truth contract.
- IF-0-P21-2 — Dependency source-of-truth contract.

### Phase 22 — Packaging & Container Release Smoke (P22)

**Objective**

Prove that a clean user can install and run the alpha package via wheel and Docker.

**Exit criteria**
- [ ] `python -m build` works from a clean checkout after dependency setup.
- [ ] A fresh virtual environment can install the built wheel and run `mcp-index --help`.
- [ ] A minimal STDIO smoke can start, initialize, and execute a small lexical
      `search_code`/`symbol_lookup` path against a fixture repo.
- [ ] `docker/dockerfiles/Dockerfile.production` builds without removed dependency files.
- [ ] The documented GHCR image name matches the workflow push target.
- [ ] Release smoke commands are captured in a script or Make target and used by CI.

**Scope notes**

Prefer one small smoke harness over many bespoke scripts. If Docker cannot support every
optional semantic feature, document that and keep the minimal image lexical-first.

**Non-goals**

- No full production deployment.
- No Kubernetes hardening.
- No semantic GPU/container optimization.

**Key files**

- `pyproject.toml`
- `Makefile`
- `.github/workflows/ci-cd-pipeline.yml`
- `.github/workflows/release-automation.yml`
- `.github/workflows/container-registry.yml`
- `docker/dockerfiles/Dockerfile.production`
- `docker/README.md`
- `README.md`
- `tests/smoke/`
- `scripts/`

**Depends on**
- P21

**Produces**
- IF-0-P22-1 — Release smoke contract.
- IF-0-P22-2 — Container contract.

### Phase 23 — Customer Docs Truth & Support Matrix (P23)

**Objective**

Make public and agent-facing docs accurately describe the alpha product, with a clear
support matrix and no stale status claims.

**Exit criteria**
- [ ] README, Getting Started, Docker guide, MCP configuration, deployment runbook, and
      security docs agree on install commands, image names, version, and beta status.
- [ ] `AGENTS.md`, `CLAUDE.md`, and nested active agent docs no longer contradict the
      current implementation.
- [ ] A support matrix lists language, parser status, sandbox support, optional extras,
      symbol quality, semantic support, and known limitations.
- [ ] Historical/status docs are archived, bannered, or removed from active navigation.
- [ ] Grep-based doc truth tests cover stale version strings, unsupported "complete"
      claims, and removed install paths.

**Scope notes**

This phase is about truth, not feature expansion. It may narrow advertised scope. That is
acceptable for alpha and preferable to overclaiming.

**Non-goals**

- No redesign of docs site tooling.
- No generated marketing site.
- No new benchmarks unless existing numbers are directly cited.

**Key files**

- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/DOCKER_GUIDE.md`
- `docs/MCP_CONFIGURATION.md`
- `docs/operations/deployment-runbook.md`
- `docs/security/*.md`
- `AGENTS.md`
- `CLAUDE.md`
- `mcp_server/AGENTS.md`
- `docs/HISTORICAL-ARTIFACTS-TRIAGE.md`
- `tests/docs/`

**Depends on**
- P21
- P22

**Produces**
- IF-0-P23-1 — Support matrix contract.

### Phase 24 — Sandbox & Plugin Runtime Hardening (P24)

**Objective**

Align sandbox-default-on runtime behavior with the support matrix so unsupported or
optional plugin paths degrade quietly and predictably.

**Exit criteria**
- [ ] Languages outside sandbox support do not emit error-level logs during normal
      lexical searches.
- [ ] Optional dependency misses such as Java extras are reported as unavailable
      capabilities with remediation hints.
- [ ] C#/C-sharp plugin construction does not crash sandbox workers.
- [ ] `list_plugins` or equivalent status output reflects enabled, disabled, unsupported,
      and missing-extra states.
- [ ] Regression tests cover sandbox-supported and sandbox-unsupported languages.

**Scope notes**

This phase may either expand sandbox support or explicitly gate unsupported languages.
Choose the smaller change that makes runtime behavior match P23's support matrix.

**Non-goals**

- No guarantee that every Tree-sitter grammar has rich symbol intelligence.
- No new cloud reranker or semantic provider integration.
- No removal of sandbox-default-on.

**Key files**

- `mcp_server/plugins/plugin_factory.py`
- `mcp_server/plugins/sandboxed_plugin.py`
- `mcp_server/sandbox/worker_main.py`
- `mcp_server/plugins/*_plugin/`
- `mcp_server/cli/tool_handlers.py`
- `mcp_server/cli/stdio_runner.py`
- `tests/security/test_plugin_sandbox.py`
- `tests/test_sandbox_default_on.py`
- `tests/test_dispatcher.py`

**Depends on**
- P23

**Produces**
- IF-0-P24-1 — Sandbox degradation contract.

### Phase 25 — Blocking Release Gates & Automation (P25)

**Objective**

Turn alpha qualification into blocking automation, with optional jobs still visible but
not confused with release gates.

**Exit criteria**
- [ ] Required alpha CI jobs are blocking: dependency sync, formatting/lint subset,
      unit/integration smoke, release smoke, Docker build, and docs truth checks.
- [ ] Non-blocking jobs are explicitly named informational and cannot be mistaken for
      release qualification.
- [ ] Release automation refuses to cut/publish when version, dependency, Docker, docs,
      or smoke contracts fail.
- [ ] Authenticated GitHub attestation tests have a documented operator prerequisite and
      a clear fallback state for private alpha.
- [ ] The release checklist maps each blocking job to an operator decision.

**Scope notes**

Do not try to make every slow/performance/cross-platform job blocking at once. The goal is
an honest alpha gate that catches broken install and release paths.

**Non-goals**

- No full GA compliance gate.
- No mandatory live third-party credentials for contributor PRs.
- No changing the core test framework.

**Key files**

- `.github/workflows/ci-cd-pipeline.yml`
- `.github/workflows/release-automation.yml`
- `.github/workflows/container-registry.yml`
- `.github/workflows/lockfile-check.yml`
- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `CHANGELOG.md`
- `Makefile`

**Depends on**
- P22
- P23
- P24

**Produces**
- IF-0-P25-1 — Blocking release gate contract.

### Phase 26 — Private Alpha Evidence & Public Alpha Decision (P26)

**Objective**

Run a controlled private alpha on real repositories, capture evidence, and decide whether
to proceed to public alpha or loop back through targeted fixes.

**Exit criteria**
- [ ] Private-alpha fixture set includes at least: Python repo, TypeScript/JS repo,
      mixed docs/code repo, multi-repo workspace, and large ignored/vendor-heavy repo.
- [ ] Evidence captures install time, first index time, query latency, result quality,
      log noise, branch/default-branch behavior, and rollback/rebuild behavior.
- [ ] Known issues are classified as public-alpha blockers, documented limitations, or
      post-alpha backlog.
- [ ] Public alpha release notes include exact supported install paths, support matrix,
      beta warnings, and rollback instructions.
- [ ] A final go/no-go decision is recorded in the roadmap amendments or release notes.

**Scope notes**

This is validation and decision work. Fix only critical blockers discovered during
validation; route everything else to a follow-up roadmap.

**Non-goals**

- No GA.
- No broad feature roadmap beyond alpha blockers.
- No private customer data committed to the repo.

**Key files**

- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `docs/benchmarks/`
- `docs/validation/`
- `CHANGELOG.md`
- `README.md`
- `tests/smoke/`
- `scripts/`

**Depends on**
- P25

**Produces**
- IF-0-P26-1 — Alpha evidence contract.

## Phase Dependency DAG

```text
P21
 ├─> P22
 │    └─> P23
 │         └─> P24
 │              └─> P25
 │                   └─> P26
 └─> P23
```

P23 depends on both P21 and P22 because docs must consume the final dependency/version
contract and the proven install/container paths. P24 depends on P23 so runtime behavior
can be hardened against an explicit support matrix instead of vague language claims.

## Execution Notes

- Plan P21 first: `codex-plan-phase P21` or pass the full phase heading if aliases have
  not been updated.
- P21 should be small and mechanical; do not let it absorb Docker smoke or docs matrix
  work.
- P22 can start planning as soon as P21's contracts are known. Its implementation should
  own smoke scripts/tests and Docker build changes.
- P23 should wait for P22's install and image names to settle. It is the docs truth pass.
- P24 can split into at least two lanes: capability/status reporting and plugin/sandbox
  crash/noise fixes.
- P25 should not start until P22-P24 gates exist; otherwise it will hard-code unstable
  release gates.
- P26 is a validation phase. If it discovers blockers, append post-execution amendments
  and create a narrow v3 roadmap only for those blockers.

## Verification

```bash
# P21
uv sync --locked
uv run pytest tests/test_requirements_consolidation.py tests/test_release_metadata.py -v --no-cov
rg -n "requirements(-production|-semantic)?\\.txt" .github docker README.md docs pyproject.toml

# P22
uv run python -m build
python -m venv /tmp/code-index-alpha-venv
/tmp/code-index-alpha-venv/bin/pip install dist/*.whl
/tmp/code-index-alpha-venv/bin/mcp-index --help
docker build -f docker/dockerfiles/Dockerfile.production -t code-index-mcp:alpha-smoke .

# P23
uv run pytest tests/docs -v --no-cov
rg -n "1\\.0\\.0|1\\.1\\.0|requirements\\.txt|Production-Ready|fully operational|48-Language Support" \
  README.md docs AGENTS.md mcp_server/AGENTS.md

# P24
uv run pytest tests/security/test_plugin_sandbox.py tests/test_sandbox_default_on.py tests/test_dispatcher.py -v --no-cov

# P25
gh workflow view "CI/CD Pipeline"
gh workflow view "Release Automation"
uv run pytest tests/smoke tests/docs tests/test_release_metadata.py -v --no-cov

# P26
# Run the private-alpha evidence script/checklist against the selected real repositories.
# The exact command should be produced by P26 and must avoid committing private repo data.
```

Any failure in the required P21-P25 gates blocks public alpha. P26 determines whether a
private-alpha candidate can become public alpha or needs a targeted v3 blocker roadmap.
