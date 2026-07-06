# Phase roadmap v9

## Context

The v8 roadmap modernized the MCP-facing protocol surface. The next work is a
public-release cleanup and issue-consolidation roadmap for the remaining live
GitHub issues:

- #68: reconcile the live `index-it-mcp` package, stale README release wording,
  and package-name confusion with `code-index-mcp`.
- #66: clean generated analysis dumps, scratch directories, result JSONs, and
  path-depth hazards out of the tracked repository.
- #43: enable coverage evidence without accidentally increasing GitHub Actions
  spend.
- #29: add a shared subprocess environment helper for robust CLI spawning.
- #28 and #31: add richer search sources for friction patterns and historical
  GitHub issue context.
- #32: extract a programmatic Python search API after the public surface and
  source contracts settle.

Live PyPI verification on 2026-07-05 found that `index-it-mcp` and
`code-index-mcp` both resolve as separate distributions. The intended public
install identity for this repo is `index-it-mcp`; `code-index-mcp` should be
treated as a confusing external/colliding package name unless a later
owner-verified migration proves otherwise. This distribution-name decision does
not settle every public identity surface by itself: console scripts, Click
program names, MCP server IDs, container image names, profile/config filenames,
`.mcp.json` examples, npm kit names, and repo/container branding each need an
explicit keep/drop/defer decision.

The CI posture should follow the existing local-first validation pattern used
across the surrounding repos: repo-local validation commands are the agent
contract; heavy validation runs locally, through Dagger, or on owned tailnet
compute; GitHub Actions should be orchestration, protected-branch evidence, and
small checks rather than the default place to burn compute minutes. Relevant
local design records include:

- `consiliency-portal/plans/unification/compute-offload/README.md`
- `consiliency-portal/plans/unification/compute-offload/DESIGN-ci-offload.md`
- `governed-pipeline/docs/agent-validation.md`
- `Code-Index-MCP/mcp-index-kit/README.md`

## Architecture North Star

Code-Index-MCP should present one obvious public identity and one obvious local
operator loop:

```text
index-it-mcp package
  -> local-first install/readme truth
  -> clean public repo tree
  -> repo-local validation commands
  -> optional Dagger / AGENT_REMOTE_HOST / self-hosted offload for heavy gates
  -> hosted GitHub Actions as minimal orchestration and protected evidence
  -> richer indexing/search product work after the public surface is stable
```

## Assumptions

- `index-it-mcp` is the canonical Python distribution and install command for
  this repository.
- The repository may keep its GitHub repo name and container image name for now,
  but package docs must not steer users toward `code-index-mcp` unless ownership
  and migration are explicitly verified.
- Public-release cleanup should happen before new feature work.
- Coverage enforcement is approved only after this repo has a local/offloaded
  validation contract that avoids unnecessary GitHub-hosted compute.
- Current GitHub Actions can remain as protected-branch evidence while the
  roadmap adds cheaper local/offloaded equivalents.
- Large generated indexes and analysis outputs should be produced locally and
  shared as artifacts, not committed into the source tree.

## Non-Goals

- No package release dispatch in this roadmap.
- No takeover, deletion, or rename of the external `code-index-mcp` package.
- No migration to a new GitHub repo name.
- No broad product rewrite while public release truth is stale.
- No mandatory GitHub-hosted coverage matrix expansion.
- No GitHub Actions secret or runner registration changes without a later
  execution plan and operator approval.

## Cross-Cutting Principles

- Prefer local proof first, then small hosted orchestration when needed.
- Keep generated outputs out of git unless they are intentional, reviewed,
  durable evidence.
- Make each public claim machine-checkable.
- Use `uv sync --locked`; `pyproject.toml` and `uv.lock` remain dependency
  truth.
- Preserve STDIO as the primary MCP surface and keep FastAPI admin claims
  separate.
- Treat same-repo worktrees and non-default branch indexed routing as beta
  limitations unless a later roadmap changes the support contract.

## Top Interface-Freeze Gates

- IF-0-PUBNAME-1 — Public identity contract: `index-it-mcp` is the canonical
  package/install name; every identity surface has a keep/drop/defer decision;
  stale release-pending/internal wording is removed; and `code-index-mcp`
  ambiguity is explicitly documented, removed from user-facing install paths, or
  deferred with rationale.
- IF-0-REPOCLEAN-1 — Clean source-tree contract: generated dumps, scratch
  directories, deep path hazards, and committed runtime outputs are removed or
  relocated; ignore patterns prevent recurrence; tracked relative paths are at
  or below the frozen limit; Windows long-path fallback guidance is documented.
- IF-0-LOCALCI-1 — Local validation contract: this repo exposes cheap,
  repo-local `make agent-*` validation commands plus a pre-PR gate, with
  optional Dagger/remote-host/self-hosted offload for heavy work and
  fail-closed hosted orchestration that shrinks rather than duplicates the
  hosted workflow footprint.
- IF-0-COVERAGE-1 — Coverage evidence contract: coverage can be generated and
  thresholded locally/offloaded; hosted CI uploads or badges only consume
  freshly generated evidence without turning every PR into a costly hosted run;
  committed coverage artifacts are forbidden.
- IF-0-PROCENV-1 — Subprocess environment contract: indexing and server spawn
  paths use a shared environment helper that preserves user tool paths across
  Linux, macOS, Windows, uv, npm, cargo, and local virtualenv contexts.
- IF-0-FRICTION-1 — Friction metadata contract: HACK/TODO/FIXME/workaround
  patterns are extracted, stored, filtered, and searched as first-class metadata
  without polluting ordinary code search.
- IF-0-HISTORY-1 — Historical issue source contract: labeled GitHub issues can
  be fetched, deduplicated, normalized, and indexed as historical planning
  context.
- IF-0-PYCLIENT-1 — Python client API contract: a supported programmatic search
  API exists separately from MCP transport without breaking existing MCP tools.

## Phases

### Phase 1 — Public Package Identity And Install Truth (PUBNAME)

**Objective**

Make `index-it-mcp` the unambiguous public install identity and remove stale
release-pending/internal wording from public docs.

**Exit criteria**
- [ ] Live package facts for `index-it-mcp` and `code-index-mcp` are captured in
      a metadata-only evidence note with check date and source URLs.
- [ ] The evidence note proves whether `index-it-mcp` on PyPI is owner-verified,
      contains this code, and exposes the intended version; if not proven, public
      install docs do not claim live PyPI readiness.
- [ ] Every identity surface is inventoried with a keep/drop/defer decision:
      distribution name, console scripts, Click program name, MCP server IDs,
      container image, profile/config filenames, `.mcp.json` examples, repo
      name, and npm kit/package names.
- [ ] The `code-index-mcp` console-script alias is removed or explicitly kept
      with a compatibility rationale and collision warning.
- [ ] `pyproject.toml`, README, getting-started docs, and release metadata agree
      on `index-it-mcp` as the canonical Python distribution.
- [ ] README no longer says release publication is pending or downstream-only.
- [ ] README either avoids `code-index-mcp` as an install name or explains that
      it is not this repo's canonical package identity.
- [ ] A clean environment install smoke builds a local wheel and proves the
      locally built `index-it-mcp` artifact exposes the expected CLI entrypoints;
      a live `pip install index-it-mcp` smoke is allowed only after owner/version
      verification.
- [ ] Docker/container naming claims are either verified or removed from the
      public quickstart until verified.

**Scope notes**

This phase owns #68. It may update docs and metadata, but it must not dispatch
a new release. If PyPI ownership/version is not proven, release smoke must use a
locally built wheel rather than the live PyPI distribution.

**Non-goals**

- No publishing to PyPI.
- No attempt to control the `code-index-mcp` package.
- No repo rename.

**Key files**

- `pyproject.toml`
- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/SUPPORT_MATRIX.md`
- `docs/status/`
- `tests/test_release_metadata.py`
- `tests/smoke/test_release_smoke_contract.py`

**Depends on**
- (none)

**Produces**
- IF-0-PUBNAME-1 — Public identity contract.

**Spec closeout policy**
- schema: spec_delta_closeout.v1
- expected_decision: roadmap_amendment
- target_surfaces: README, install docs, release metadata, package identity
- evidence_paths: docs/status/public-package-identity.md, test output
- redaction_posture: metadata_only
- blocker_routing: missing or malformed package evidence is
  blocker_class=contract_bug

### Phase 2 — Public Repo Root Cleanup And Windows Clone Safety (REPOCLEAN)

**Objective**

Clean tracked generated artifacts and scratch outputs from the public tree,
reduce path-depth hazards, and preserve only intentional source, config, docs,
tests, and durable evidence.

**Exit criteria**
- [ ] Generated root JSON/log/status dumps are deleted, moved to approved
      documentation/evidence locations, or explicitly justified.
- [ ] Scratch/output directories such as `analysis_archive/`, `test_results/`,
      and similar generated folders are removed from git unless intentionally
      preserved under a documented archive policy.
- [ ] `.gitignore` covers regenerated dumps, transient index outputs,
      performance results, and local runtime state.
- [ ] A tracked-but-ignored audit classifies any files that are already tracked
      but match ignore rules before deletion or retention.
- [ ] README/project structure docs no longer advertise scratch directories as
      first-class source layout.
- [ ] A `git ls-files` tracked-path audit proves no tracked repository-relative
      path exceeds 160 characters.
- [ ] A package-install path audit checks generated wheel contents for
      site-packages path-depth risk on Windows.
- [ ] Windows troubleshooting mentions `git config --global core.longpaths true`
      as a fallback, not as the primary fix.

**Scope notes**

This phase owns #66 and the accepted #67 duplicate criteria. It should be
reviewed carefully because it removes many tracked files. Preserve
`docs/status/public-package-identity.md` as durable PUBNAME evidence, and do
not delete or rename deferred identity surfaces such as
`code-index-mcp.profiles.yaml`, client-label examples, or `mcp-index-kit/`
unless a later phase explicitly re-decides those public names.

**Non-goals**

- No git history rewrite.
- No deletion of source, tests, active docs, or release evidence without an
  explicit inventory.
- No runtime behavior changes.

**Key files**

- `.gitignore`
- `README.md`
- `docs/PROJECT_STRUCTURE.md`
- generated root reports and JSON files
- `analysis_archive/`
- `test_results/`
- `performance_reports/`

**Depends on**
- PUBNAME

**Produces**
- IF-0-REPOCLEAN-1 — Clean source-tree contract.

**Spec closeout policy**
- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: repository tree, ignore policy, public docs
- evidence_paths: cleanup inventory, longest-path audit output
- redaction_posture: metadata_only
- blocker_routing: missing cleanup inventory is blocker_class=contract_bug

### Phase 3 — Local Validation And CI Offload Contract (LOCALCI)

**Objective**

Define this repo's local-first validation interface before expanding coverage
or hosted CI behavior.

**Exit criteria**
- [ ] Repo-local commands exist with exact names: `make agent-doctor`,
      `make agent-fast`, `make agent-gate`, `make agent-full`,
      `make agent-fix`, and `make agent-affected`.
- [ ] `agent-fast` is cheap and offline: dependency lock sanity, static checks,
      focused docs/package truth checks, and no network by default.
- [ ] `agent-gate` is the pre-PR gate and maps to the same substantive suite CI
      uses, preferably through an optional Dagger path when available.
- [ ] `agent-affected` routes docs-only changes to the cheap gate and source,
      workflow, package, or unknown diffs to the full pre-PR gate.
- [ ] Optional `AGENT_REMOTE_HOST` or equivalent offload is documented for heavy
      validation on owned tailnet compute, fail-closed when unreachable.
- [ ] Every `.github/workflows/*.yml` and `.github/workflows/*.yaml` file is
      audited and classified as protected evidence, manual-only, offloaded, or
      retired.
- [ ] GitHub Actions posture is documented as minimal orchestration/protected
      evidence, with heavy compute either local/offloaded or explicitly
      operator-triggered.
- [ ] The existing hosted per-PR alpha gates are collapsed, path-scoped,
      offloaded, or otherwise reduced so `agent-*` does not merely add a second
      validation vocabulary beside the current hosted matrix.
- [ ] No hosted runner fallback silently converts an unavailable offload host
      into a green check.

**Scope notes**

This phase adapts the governed-pipeline validation contract to a Python/uv repo
instead of copying npm command names blindly. Decompose into three lanes:
repo-local command contract, offload/fail-closed posture, and hosted workflow
orchestration.

**Non-goals**

- No registration of self-hosted runners.
- No GitHub secret mutation.
- No coverage threshold changes yet.

**Key files**

- `Makefile`
- `pyproject.toml`
- `.github/workflows/*.yml`
- `.github/workflows/*.yaml`
- `docs/development/TESTING-GUIDE.md`
- `docs/operations/`
- optional validation scripts under `scripts/`

**Depends on**
- REPOCLEAN

**Produces**
- IF-0-LOCALCI-1 — Local validation contract.

**Spec closeout policy**
- schema: spec_delta_closeout.v1
- expected_decision: roadmap_amendment
- target_surfaces: validation command contract, CI/offload posture
- evidence_paths: docs/development/agent-validation.md, command output
- redaction_posture: metadata_only
- blocker_routing: missing command contract is blocker_class=contract_bug

### Phase 4 — Coverage Evidence Without Hosted Compute Creep (COVERAGE)

**Objective**

Implement #43 in a local/offload-first way: generate coverage evidence, expose a
badge or status surface, and threshold it only after the local gate proves the
baseline.

**Exit criteria**
- [ ] Local coverage command emits `coverage.xml` and terminal missing-line
      output.
- [ ] The current coverage baseline and any existing pytest coverage threshold
      are measured before enforcing a new threshold.
- [ ] `--cov-fail-under=80` replaces or ramps from the existing threshold only
      if the measured local/offloaded gate supports it; otherwise the roadmap
      records an explicit threshold-ramp amendment.
- [ ] `coverage.xml`, `.coverage*`, `htmlcov/`, and equivalent generated
      coverage outputs are ignored and must not be tracked or staged.
- [ ] A CI/local gate fails if generated coverage artifacts are committed or
      staged; coverage evidence must be freshly generated during the run.
- [ ] Hosted GitHub Actions coverage upload, if used, runs only on trusted
      protected events, self-hosted/offloaded jobs, or manual dispatch.
- [ ] README badge reflects a real uploaded report or is deferred until upload
      is proven.
- [ ] `agent-gate` or `agent-full` owns coverage generation so agents do not
      rely on GitHub-hosted minutes for normal pre-PR proof.

**Scope notes**

This phase owns #43. It should not spend hosted CI minutes merely to discover
that coverage is below threshold. It must reconcile existing coverage config
before adding a new 80 percent gate.
`docs/status/localci-validation-contract.md` is the frozen LOCALCI evidence
input: COVERAGE may extend `agent-full` or manual protected evidence, but it
must not re-introduce retired/manual-only workflow families as pull-request
gates or recreate a second hosted validation vocabulary beside `make agent-*`.

**Non-goals**

- No Codecov token setup unless a later execution plan confirms it is required.
- No broad test rewrite to chase coverage percentage.
- No hosted matrix expansion.

**Key files**

- `pyproject.toml`
- `Makefile`
- `.github/workflows/ci-cd-pipeline.yml`
- `README.md`
- `docs/development/TESTING-GUIDE.md`

**Depends on**
- LOCALCI

**Produces**
- IF-0-COVERAGE-1 — Coverage evidence contract.

**Spec closeout policy**
- schema: spec_delta_closeout.v1
- expected_decision: roadmap_amendment
- target_surfaces: coverage gate, README badge, CI/offload evidence
- evidence_paths: coverage.xml, coverage terminal output, workflow diff
- redaction_posture: metadata_only
- blocker_routing: absent baseline measurement is blocker_class=contract_bug

### Phase 5 — Shared Subprocess Environment Helper (PROCENV)

**Objective**

Add a robust subprocess environment helper and route indexing/server subprocess
calls through it where PATH/tool discovery matters.

**Exit criteria**
- [ ] A shared helper builds a subprocess environment that preserves existing
      env vars while adding common user tool paths for Linux, macOS, and
      Windows.
- [ ] The helper path and function contract are frozen, for example
      `mcp_server/utils/subprocess_env.py::get_full_env()`.
- [ ] Indexing and server-spawn subprocess calls that rely on `git`, `rg`, uv,
      npm, cargo, tree-sitter, or related CLIs use the helper.
- [ ] Tests cover PATH merging, virtualenv preservation, Windows path separator
      behavior, and no secret-value logging.
- [ ] Failure messages include command availability metadata and remediation
      without printing env values.

**Scope notes**

This phase owns #29. Prefer a small local helper over importing from
ai-dev-kit directly unless a stable shared package exists. This phase does not
gate friction extraction, but it should gate historical issue fetching because
that path shells out to `gh`.

**Non-goals**

- No broad subprocess abstraction rewrite.
- No shell-specific setup scripts.
- No logging of raw environment values.

**Key files**

- `mcp_server/utils/`
- `mcp_server/cli/`
- `mcp_server/storage/`
- `scripts/`
- `tests/`

**Depends on**
- LOCALCI

**Produces**
- IF-0-PROCENV-1 — Subprocess environment contract.

**Spec closeout policy**
- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: subprocess helper, spawn call sites, tests
- evidence_paths: targeted subprocess environment test output
- redaction_posture: metadata_only
- blocker_routing: missing redaction proof is blocker_class=contract_bug

### Phase 6 — Friction Pattern Metadata Search (FRICTION)

**Objective**

Index technical-friction markers such as HACK, TODO, FIXME, workaround, wish,
and extraction hints as searchable metadata.

**Exit criteria**
- [ ] A friction extractor detects configured patterns with category, line,
      description, and optional reference fields.
- [ ] A generic search-source metadata envelope is defined so later source types
      such as historical issues do not inherit a friction-specific schema.
- [ ] Friction metadata is stored alongside chunks without changing ordinary
      search result contracts unless requested.
- [ ] Search supports filtering or querying friction categories.
- [ ] Semantic embedding enrichment, if enabled, is deterministic and
      documented.
- [ ] Tests cover common comment syntaxes across Python, JS/TS, shell, and
      Markdown/plain text.

**Scope notes**

This phase owns #28 and should produce a stable metadata schema before any
workflow integration consumes it.

**Non-goals**

- No automatic issue creation.
- No ai-dev-kit reflection workflow dependency.
- No cross-repo prioritization UI.

**Key files**

- `mcp_server/indexing/`
- `mcp_server/plugins/`
- `mcp_server/storage/`
- `mcp_server/dispatcher/`
- `tests/`
- `docs/`

**Depends on**
- LOCALCI

**Produces**
- IF-0-FRICTION-1 — Friction metadata contract.

**Spec closeout policy**
- schema: spec_delta_closeout.v1
- expected_decision: canonical_spec_update
- target_surfaces: chunk metadata schema, search filter contract
- evidence_paths: friction schema docs, extractor/search test output
- redaction_posture: metadata_only
- blocker_routing: schema/test mismatch is blocker_class=contract_bug

### Phase 7 — Historical GitHub Issue Context Indexing (HISTORY)

**Objective**

Add an optional source adapter for labeled GitHub issues so agents can search
phase-complete, retrospective, and reflection history.

**Exit criteria**
- [ ] GitHub issue fetcher supports repo, label allowlist, date window, and
      state filters.
- [ ] Deduplication prevents repeated phase-complete/reflection records from
      crowding the index.
- [ ] Issue documents are normalized with type, repo, number, title, labels,
      timestamps, URL, summary, and extracted learnings.
- [ ] Search can filter historical issue records separately from source-code
      chunks.
- [ ] Tests use fixtures or mocked `gh` output and require no live credentials.
- [ ] Docs mark the feature optional and metadata-only by default.

**Scope notes**

This phase owns #31. It consumes the friction metadata direction but remains a
separate source type.

**Non-goals**

- No live GitHub calls in unit tests.
- No indexing of private issue bodies by default.
- No write operations to GitHub.

**Key files**

- `mcp_server/indexing/`
- `mcp_server/storage/`
- `mcp_server/dispatcher/`
- `mcp_server/cli/`
- `tests/fixtures/`
- `docs/`

**Depends on**
- FRICTION
- PROCENV

**Produces**
- IF-0-HISTORY-1 — Historical issue source contract.

**Spec closeout policy**
- schema: spec_delta_closeout.v1
- expected_decision: canonical_spec_update
- target_surfaces: external source adapter schema, historical search filters
- evidence_paths: issue adapter docs, fixture-backed tests
- redaction_posture: metadata_only
- blocker_routing: live-credential dependency in tests is
  blocker_class=contract_bug

### Phase 8 — Programmatic Python Search Client (PYCLIENT)

**Objective**

Extract a supported Python client API for local programmatic search while
keeping the MCP server as a compatible transport wrapper.

**Exit criteria**
- [ ] Public API surface exposes local search/index operations with typed result
      objects and clear stability notes.
- [ ] Public API scope explicitly includes source filters for code, friction,
      and historical issue records from day one, which justifies waiting for
      `FRICTION` and `HISTORY`.
- [ ] MCP tool handlers call shared library functionality rather than forking
      search behavior.
- [ ] Import path and package exports align with the canonical
      `index-it-mcp` distribution.
- [ ] Tests cover direct client use without starting an MCP server.
- [ ] Existing MCP STDIO tests still pass.
- [ ] Docs show when to use Python client versus MCP tools.

**Scope notes**

This phase owns #32 and intentionally comes after package identity, validation,
and source contracts settle.

**Non-goals**

- No removal of MCP tools.
- No second package name.
- No remote service client.

**Key files**

- `mcp_server/`
- candidate public package module under the canonical distribution
- `pyproject.toml`
- `tests/`
- `README.md`
- `docs/`

**Depends on**
- HISTORY
- COVERAGE

**Produces**
- IF-0-PYCLIENT-1 — Python client API contract.

**Spec closeout policy**
- schema: spec_delta_closeout.v1
- expected_decision: canonical_spec_update
- target_surfaces: public Python API, package exports, MCP wrapper boundary
- evidence_paths: client API docs, direct client tests, MCP compatibility tests
- redaction_posture: metadata_only
- blocker_routing: public API ambiguity is blocker_class=contract_bug

## Phase Dependency DAG

```text
PUBNAME
  -> REPOCLEAN
     -> LOCALCI
        -> COVERAGE
        -> PROCENV
        -> FRICTION
           -> HISTORY
              -> PYCLIENT
PROCENV
  -> HISTORY
COVERAGE
  -> PYCLIENT
```

## Execution Notes

- `PUBNAME` should be planned first because the package identity decision
  affects docs, install tests, and the eventual Python client API.
- `REPOCLEAN` should follow before feature work so implementation agents are not
  navigating generated debris or Windows path hazards.
- `LOCALCI` must precede `COVERAGE`; coverage is approved only with the
  local/offloaded validation posture in place.
- After `LOCALCI`, `COVERAGE`, `PROCENV`, and `FRICTION` can be planned
  independently.
- `FRICTION` and `HISTORY` are serial because historical issue records should
  reuse the same generic search-source metadata envelope instead of inventing a
  second model. `HISTORY` also depends on `PROCENV` because it shells out to
  GitHub tooling.
- `PYCLIENT` waits until the public package name and richer source contracts are
  stable, because the supported client API should expose code, friction, and
  historical issue source filters from day one.

## Verification

Roadmap-level commands to incorporate into downstream phase plans:

```bash
uv sync --locked --extra dev
make alpha-docs-truth
make alpha-release-gates
uv run pytest tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -q --no-cov
python - <<'PY'
import subprocess
paths = subprocess.check_output(['git', 'ls-files'], text=True).splitlines()
print(max((len(p), p) for p in paths))
PY
phase-loop validate-roadmap specs/phase-plans-v9.md
```

After `LOCALCI`, downstream plans should replace or supplement
`make alpha-release-gates` with the exact repo-local validation command contract:
`make agent-fast`, `make agent-gate`, `make agent-full`, `make agent-affected`,
`make agent-fix`, and `make agent-doctor`.

## Next Step

Next phase: PUBNAME - Public Package Identity And Install Truth
Next command: codex-plan-phase specs/phase-plans-v9.md PUBNAME

```yaml
automation:
  status: unplanned
  next_skill: codex-plan-phase
  next_command: codex-plan-phase specs/phase-plans-v9.md PUBNAME
  next_model_hint: plan
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/specs/phase-plans-v9.md
  artifact_state: staged
```
