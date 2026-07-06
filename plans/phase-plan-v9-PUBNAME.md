---
phase_loop_plan_version: 1
phase: PUBNAME
roadmap: specs/phase-plans-v9.md
roadmap_sha256: f7f4f8ae7c818525a286fd3716051f1df8832c976223ed5b23ff70e8bedc268f
---
# PUBNAME: Public Package Identity And Install Truth

## Context

PUBNAME is the first execution phase in `specs/phase-plans-v9.md`. Its job is
not to publish anything; it freezes the public package identity before cleanup,
local validation, coverage, and client API phases consume the package surface.

Current repo state gathered during planning:

- `specs/phase-plans-v9.md` is tracked and `sha256sum` matches the required
  `f7f4f8ae7c818525a286fd3716051f1df8832c976223ed5b23ff70e8bedc268f`.
- Canonical `.phase-loop/` state exists, but `.phase-loop/state.json` still
  records an older ambiguous-roadmap blocker. This run supplies an explicit
  roadmap path and matching hash, so the stale blocker is not authoritative for
  this plan. Legacy `.codex/phase-loop/` state is compatibility-only.
- `plans/phase-plan-v9-PUBNAME.md` did not exist before this planning run.
- `pyproject.toml` already names the Python distribution `index-it-mcp` and
  exposes `mcp-index`, `index-it-mcp`, and `code-index-mcp` console scripts.
- `README.md`, `docs/GETTING_STARTED.md`, and `docs/SUPPORT_MATRIX.md` already
  point package installs at `index-it-mcp==1.2.0`, but public docs still contain
  stable-surface/pre-GA/downstream-dispatch wording that this phase must make
  consistent with the live package evidence it records.
- `scripts/release_smoke.py` already builds a local wheel named
  `index_it_mcp-*.whl` and proves `mcp-index --help`, but it does not yet make
  the expected package entrypoint set explicit for this public identity phase.
- The `code-index-mcp` name appears in legitimate non-distribution surfaces such
  as profile filenames, MCP server labels in examples, and the GHCR container
  path. PUBNAME must inventory those uses and decide keep/drop/defer for each
  surface instead of treating every occurrence as an install-name bug.

Practical planning boundary:

- PUBNAME may update package metadata, release smoke tests, public install docs,
  support matrix wording, and one metadata-only status artifact.
- PUBNAME must not publish to PyPI, create tags, rename the repository, claim
  ownership of the external `code-index-mcp` distribution, or rewrite historical
  release evidence that is clearly labeled as historical.
- If live PyPI ownership/version/source facts are not proven during execution,
  public install documentation must remain conservative and the smoke proof must
  use the locally built wheel.

## Interface Freeze Gates

- [ ] IF-0-PUBNAME-1 - Public identity contract:
      `index-it-mcp` is the canonical Python distribution and install name;
      `mcp-index` and `index-it-mcp` are the canonical CLI entrypoints;
      `code-index-mcp` is either removed as a console-script alias or retained
      only with an explicit legacy-compatibility rationale and collision
      warning; live package facts for both PyPI names are captured with source
      URLs and check date; user-facing install paths do not steer users toward
      `code-index-mcp`; and package metadata, quickstart docs, release smoke,
      support matrix, and container-image claims agree on verified vs deferred
      public readiness.

## Lane Index & Dependencies

- SL-0 - Live package fact collection and public identity decision inputs; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Python package metadata and local wheel smoke contract; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Public install docs and container quickstart truth; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Identity inventory evidence reducer and acceptance closeout; Depends on: SL-0, SL-1, SL-2; Blocks: PUBNAME acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 -> SL-1 -> SL-2 -> SL-3 -> PUBNAME acceptance
```

## Lanes

### SL-0 - Live Package Fact Collection And Public Identity Decision Inputs

- **Scope**: Gather metadata-only live package facts for `index-it-mcp` and
  `code-index-mcp`, then choose the conservative install-doc posture consumed by
  the implementation lanes.
- **Owned files**: none
- **Interfaces provided**: live package fact set for IF-0-PUBNAME-1; execution
  decision on whether docs may claim live PyPI readiness or must stay on local
  wheel/prepared-surface wording
- **Interfaces consumed**: `https://pypi.org/pypi/index-it-mcp/json`,
  `https://pypi.org/pypi/code-index-mcp/json`, `python -m pip index versions`,
  current `pyproject.toml` project metadata, and roadmap requirement that
  package evidence is metadata-only
- **Parallel-safe**: no
- **Tasks**:
  - test: Run metadata-only probes for `index-it-mcp` and `code-index-mcp` that
    capture package URL, normalized name, latest visible versions, release file
    filenames, upload timestamps, yanked status, project URLs, and check date
    without downloading artifacts or printing credentials.
  - impl: Decide from the probe output whether live `index-it-mcp` owner/version
    facts prove this repo's intended release. If proof is incomplete, force the
    downstream docs and smoke lanes to describe the local wheel/prepared package
    surface rather than live PyPI readiness.
  - impl: Treat `code-index-mcp` as an external/colliding package name unless
    owner verification proves otherwise; do not try to publish, reserve,
    delete, or migrate that name in this phase.
  - verify: `python - <<'PY'\nimport json, urllib.request\nfor name in ('index-it-mcp', 'code-index-mcp'):\n    url = f'https://pypi.org/pypi/{name}/json'\n    with urllib.request.urlopen(url, timeout=20) as response:\n        payload = json.load(response)\n    info = payload.get('info', {})\n    releases = payload.get('releases', {})\n    print(json.dumps({\n        'name': name,\n        'url': url,\n        'normalized_name': info.get('name'),\n        'version': info.get('version'),\n        'project_urls': sorted((info.get('project_urls') or {}).keys()),\n        'release_count': len(releases),\n    }, sort_keys=True))\nPY`

### SL-1 - Python Package Metadata And Local Wheel Smoke Contract

- **Scope**: Align the Python distribution metadata, console-script contract,
  and local wheel smoke around `index-it-mcp` without requiring a live PyPI
  install.
- **Owned files**: `pyproject.toml`, `scripts/release_smoke.py`, `tests/test_release_metadata.py`, `tests/smoke/test_release_smoke_contract.py`
- **Interfaces provided**: package metadata portion of IF-0-PUBNAME-1; local
  wheel smoke evidence consumed by SL-3
- **Interfaces consumed**: SL-0 package fact decision; existing
  `smoke_wheel()` local build/install path; existing release metadata tests;
  current console script map from `[project.scripts]`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/test_release_metadata.py` so the canonical distribution
    name remains `index-it-mcp`, canonical install docs do not use
    `code-index-mcp`, and any retained `code-index-mcp` console-script alias is
    treated as an explicitly documented legacy compatibility alias rather than
    a canonical install surface.
  - test: Update `tests/smoke/test_release_smoke_contract.py` so the local wheel
    smoke contract proves the locally built `index-it-mcp` wheel exposes the
    expected canonical entrypoints, including `index-it-mcp` and `mcp-index`.
  - impl: Keep or remove the `code-index-mcp` console-script alias deliberately.
    Prefer retaining it only if the evidence reducer records a compatibility
    rationale and collision warning; otherwise remove it and update tests to
    expect only `mcp-index` and `index-it-mcp`.
  - impl: Extend `scripts/release_smoke.py` so the wheel smoke checks every
    expected entrypoint from the finalized script contract instead of only
    `mcp-index --help`.
  - impl: Do not change package version, build backend, dependencies, release
    workflows, or publication commands in this phase.
  - verify: `uv run pytest tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -q --no-cov`
  - verify: `uv run --extra dev python scripts/release_smoke.py --wheel --stdio`

### SL-2 - Public Install Docs And Container Quickstart Truth

- **Scope**: Make public install and quickstart documentation use
  `index-it-mcp` as the Python distribution while separating verified package,
  container, profile, and MCP server-label identities.
- **Owned files**: `README.md`, `docs/GETTING_STARTED.md`, `docs/SUPPORT_MATRIX.md`, `docs/DOCKER_GUIDE.md`, `docs/MCP_CONFIGURATION.md`, `tests/docs/test_pubname_public_docs.py`
- **Interfaces provided**: public docs portion of IF-0-PUBNAME-1; docs truth
  inputs consumed by SL-3
- **Interfaces consumed**: SL-0 package fact decision; SL-1 finalized console
  script contract; existing STDIO-primary/FastAPI-secondary docs; existing
  GHCR image tests and support matrix rows
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_pubname_public_docs.py` to freeze that public
    Python install examples use `index-it-mcp`, README no longer claims release
    publication is merely pending/downstream-only when live evidence proves a
    release, and docs use conservative local-wheel/prepared-surface wording when
    live evidence does not prove readiness.
  - test: Require docs that mention `code-index-mcp` to classify the occurrence
    as a non-distribution surface, such as the GHCR image, a profile filename,
    or an MCP client server label, or to point at the SL-3 collision warning.
  - impl: Update the README project status, quickstart install section,
    `docs/GETTING_STARTED.md`, and `docs/SUPPORT_MATRIX.md` so package install
    claims match SL-0 evidence and SL-1 metadata.
  - impl: Update Docker/MCP configuration quickstarts only where they make
    inspectable public claims. Keep the GHCR image path if still treated as a
    verified container identity, but remove or qualify unsupported container
    readiness claims until evidence exists.
  - impl: Keep historical validation and release-evidence documents intact
    unless a line is presented as current quickstart truth. Historical RC/GA
    evidence should remain historical rather than rewritten into current docs.
  - verify: `uv run pytest tests/docs/test_pubname_public_docs.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -q --no-cov`
  - verify: `rg -n "pip install|index-it-mcp|code-index-mcp|ghcr.io/viperjuice/code-index-mcp|dispatch pending|downstream-only" README.md docs/GETTING_STARTED.md docs/SUPPORT_MATRIX.md docs/DOCKER_GUIDE.md docs/MCP_CONFIGURATION.md tests/docs/test_pubname_public_docs.py`

### SL-3 - Identity Inventory Evidence Reducer And Acceptance Closeout

- **Scope**: Reduce the live package facts, metadata decisions, docs edits, and
  smoke evidence into one metadata-only public identity artifact that records
  every keep/drop/defer identity-surface decision.
- **Owned files**: `docs/status/public-package-identity.md`, `tests/docs/test_pubname_identity_contract.py`
- **Interfaces provided**: final IF-0-PUBNAME-1 public identity contract and
  phase acceptance evidence
- **Interfaces consumed**: SL-0 live package fact set; SL-1 console-script and
  wheel-smoke results; SL-2 public docs truth; current package/repo/container
  naming surfaces from `pyproject.toml`, README/docs, MCP configuration
  examples, `code-index-mcp.profiles.yaml`, `.mcp-index*` paths, and
  `mcp-index-kit/`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_pubname_identity_contract.py` to require
    `docs/status/public-package-identity.md` to include check date, source URLs,
    live facts for both PyPI names, owner/version/source-code proof status,
    local wheel smoke evidence, and an inventory table for distribution name,
    console scripts, Click program name, MCP server IDs, container image,
    profile/config filenames, `.mcp.json` examples, repo name, and npm kit names.
  - test: Require the evidence artifact to use only keep/drop/defer decisions
    and to include a non-empty rationale for any deferred or retained
    `code-index-mcp` surface.
  - impl: Write `docs/status/public-package-identity.md` as metadata-only
    evidence. Include exact command snippets and source URLs, but do not include
    tokens, credentials, raw downloaded artifacts, or secret-bearing environment
    output.
  - impl: Record whether `index-it-mcp` live PyPI readiness is proven. If not,
    state that public docs intentionally rely on the locally built wheel smoke
    and prepared package surface until a later release/evidence update proves
    live readiness.
  - impl: Record the final console-script decision. If `code-index-mcp` remains
    as an alias, the artifact must warn that it is not the canonical Python
    distribution or install name and explain the compatibility reason.
  - verify: `uv run pytest tests/docs/test_pubname_identity_contract.py tests/docs/test_pubname_public_docs.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -q --no-cov`
  - verify: `git diff --stat -- pyproject.toml scripts/release_smoke.py README.md docs/GETTING_STARTED.md docs/SUPPORT_MATRIX.md docs/DOCKER_GUIDE.md docs/MCP_CONFIGURATION.md docs/status/public-package-identity.md tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py tests/docs/test_pubname_public_docs.py tests/docs/test_pubname_identity_contract.py`

## Verification

Plan artifact creation is complete once this artifact is written and staged. Do
not execute the commands below during `codex-plan-phase`; run them during
`codex-execute-phase` or manual PUBNAME execution.

Lane-specific checks:

```bash
python - <<'PY'
import json, urllib.request
for name in ('index-it-mcp', 'code-index-mcp'):
    url = f'https://pypi.org/pypi/{name}/json'
    with urllib.request.urlopen(url, timeout=20) as response:
        payload = json.load(response)
    info = payload.get('info', {})
    releases = payload.get('releases', {})
    print(json.dumps({
        'name': name,
        'url': url,
        'normalized_name': info.get('name'),
        'version': info.get('version'),
        'project_urls': sorted((info.get('project_urls') or {}).keys()),
        'release_count': len(releases),
    }, sort_keys=True))
PY

uv run pytest tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -q --no-cov
uv run --extra dev python scripts/release_smoke.py --wheel --stdio
uv run pytest tests/docs/test_pubname_public_docs.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -q --no-cov
uv run pytest tests/docs/test_pubname_identity_contract.py tests/docs/test_pubname_public_docs.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -q --no-cov
```

Whole-phase verification after code changes:

```bash
uv sync --locked --extra dev
make alpha-docs-truth
make release-smoke
uv run pytest \
  tests/test_release_metadata.py \
  tests/smoke/test_release_smoke_contract.py \
  tests/docs/test_pubname_public_docs.py \
  tests/docs/test_pubname_identity_contract.py \
  -q --no-cov
phase-loop validate-roadmap specs/phase-plans-v9.md
git status --short -- \
  pyproject.toml \
  scripts/release_smoke.py \
  README.md \
  docs/GETTING_STARTED.md \
  docs/SUPPORT_MATRIX.md \
  docs/DOCKER_GUIDE.md \
  docs/MCP_CONFIGURATION.md \
  docs/status/public-package-identity.md \
  tests/test_release_metadata.py \
  tests/smoke/test_release_smoke_contract.py \
  tests/docs/test_pubname_public_docs.py \
  tests/docs/test_pubname_identity_contract.py \
  plans/phase-plan-v9-PUBNAME.md
```

Full gate when execution time allows:

```bash
make alpha-release-gates
```

## Acceptance Criteria

- [ ] Live package facts for `index-it-mcp` and `code-index-mcp` are captured in
      `docs/status/public-package-identity.md` with check date and source URLs.
- [ ] The evidence note proves whether `index-it-mcp` on PyPI is owner-verified,
      contains this code, and exposes the intended version; if not proven,
      public install docs do not claim live PyPI readiness.
- [ ] Every identity surface is inventoried with a keep/drop/defer decision:
      distribution name, console scripts, Click program name, MCP server IDs,
      container image, profile/config filenames, `.mcp.json` examples, repo
      name, and npm kit/package names.
- [ ] The `code-index-mcp` console-script alias is removed or explicitly kept
      with a compatibility rationale and collision warning.
- [ ] `pyproject.toml`, README, getting-started docs, and release metadata agree
      on `index-it-mcp` as the canonical Python distribution.
- [ ] README no longer says release publication is pending or downstream-only
      unless the live evidence note explicitly says the stable live release is
      not proven and public docs are intentionally conservative.
- [ ] README either avoids `code-index-mcp` as an install name or explains that
      it is not this repo's canonical package identity.
- [ ] A clean environment install smoke builds a local wheel and proves the
      locally built `index-it-mcp` artifact exposes the expected CLI
      entrypoints; a live `pip install index-it-mcp` smoke is used only after
      owner/version verification.
- [ ] Docker/container naming claims are verified or removed from the public
      quickstart until verified.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `roadmap_amendment`
- target surfaces: `pyproject.toml`, `README.md`, `docs/GETTING_STARTED.md`, `docs/SUPPORT_MATRIX.md`, `docs/DOCKER_GUIDE.md`, `docs/MCP_CONFIGURATION.md`, `docs/status/public-package-identity.md`, `tests/test_release_metadata.py`, `tests/smoke/test_release_smoke_contract.py`, `tests/docs/test_pubname_public_docs.py`, `tests/docs/test_pubname_identity_contract.py`, `scripts/release_smoke.py`
- evidence paths: `docs/status/public-package-identity.md`
- redaction posture: `metadata_only`
- downstream handling: roadmap amendment

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v9-PUBNAME.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v9-PUBNAME.md
  artifact_state: staged
```
