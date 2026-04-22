# Detailed plan: release-readiness hardening for external and multi-repo use

## Task

Fix the production-readiness gaps found in the review of outside-developer and
multi-repo readiness:

- Python package/distribution identity is inconsistent with public install docs.
- Release automation can compute a version from old `v2.x` tags instead of using
  the requested `v1.2.0-rc4` release candidate.
- `MCP_ALLOWED_ROOTS` parsing is inconsistent across STDIO, REST, and docs.
- P26 private-alpha evidence is a local smoke artifact, not real external/private
  multi-repo release evidence.
- GHCR `latest` and GitHub release state do not represent the current rc4 commit.
- A stale GitHub Actions workflow remains active outside the current tree.

This is a release-readiness hardening pass, not a broad product refactor.

## Research summary

The current tree is clean on `main` at `b01260f`, and the most recent pushed
Actions are green. The readiness gaps trace to drift between phase-era release
work and older public distribution state: `pyproject.toml` was switched to
`index-it-mcp` in commit `26bd84d`, but that distribution is not published on
PyPI; the older `code-index-mcp` package exists with a newer `2.15.0` public
line. The release workflow still defaults to semantic bumping from latest tags
unless `release_type=custom`, which is unsafe with existing `v2.x` tags.
Multi-repo implementation tests are strong, but `MCP_ALLOWED_ROOTS` parsing
diverged: README/security docs describe `os.pathsep`, the gateway parses
`os.pathsep`, and STDIO bootstrap parses comma-separated values.

Product call for this plan: keep `index-it-mcp` as the Python distribution name
for rc4 and keep `code-index-mcp` as the repo/container/server alias. This
matches current package metadata and avoids colliding with the older
`code-index-mcp` PyPI lineage. The plan therefore requires publishing
`index-it-mcp` before pip-install docs are considered externally ready.

## Changes

### `mcp_server/security/path_allowlist.py` (modify)

- `parse_allowed_roots(raw: str) -> tuple[Path, ...]` — add — centralize
  parsing of `MCP_ALLOWED_ROOTS` so STDIO and REST use one contract.
- `parse_allowed_roots` behavior — add — split on `os.pathsep` as the canonical
  separator; also tolerate comma-separated legacy values when no `os.pathsep`
  separator is present.
- `resolve_allowed_roots` usage — modify — keep realpath normalization and
  symlink escape defense intact.

### `mcp_server/cli/bootstrap.py` (modify)

- `_allowed_roots` — modify — delegate parsing to
  `mcp_server.security.path_allowlist.parse_allowed_roots`.
- `_allowed_roots` docstring — modify — state `MCP_ALLOWED_ROOTS` is
  `os.pathsep` separated, with legacy comma tolerance.
- `_allowed_roots` fallback behavior — preserve — `MCP_WORKSPACE_ROOT` then
  `cwd` remain unchanged.

### `mcp_server/gateway.py` (modify)

- `_get_path_guard` — modify — use the shared `parse_allowed_roots` helper
  instead of local `raw.split(os.pathsep)` parsing.
- Path traversal behavior — preserve — unset/empty `MCP_ALLOWED_ROOTS` remains
  a no-op for dev/test; configured roots still filter result paths.

### `mcp_server/cli/tool_handlers.py` (modify)

- Path sandbox error hints — modify — replace "comma-separated" with
  "OS path separator separated (`:` on Unix, `;` on Windows)".
- Search/symbol/reindex/summarize/write_summaries guards — preserve — no change
  to rejection semantics other than accepting correctly documented root lists.

### `tests/test_bootstrap.py` (modify)

- `_allowed_roots` tests — add — prove Unix-like pathsep input such as
  `/tmp/a:/tmp/b` resolves to two roots.
- Legacy comma test — add — prove `/tmp/a,/tmp/b` still resolves to two roots
  for backward compatibility.
- Fallback tests — preserve/extend — verify `MCP_WORKSPACE_ROOT` and `cwd`
  fallback still work when `MCP_ALLOWED_ROOTS` is unset or empty.

### `tests/security/test_path_traversal.py` (modify)

- Gateway parsing test — add — prove the REST path guard uses the same shared
  parser and accepts `os.pathsep` separated roots.

### `tests/test_handler_path_sandbox.py` (modify)

- Handler path sandbox tests — add — set multiple roots with `os.pathsep` and
  prove `search_code`, `symbol_lookup`, `summarize_sample`, and `reindex`
  accept paths under either root and reject paths outside both.
- Error hint assertions — modify — expect the new path-separator wording.

### `tests/test_release_metadata.py` (modify)

- `EXPECTED_PACKAGE_NAME = "index-it-mcp"` — add — freeze the Python
  distribution name.
- `EXPECTED_PRODUCT_NAME = "code-index-mcp"` — add — freeze the product/container
  alias separately from the Python distribution name.
- `test_pyproject_package_name_matches_release_contract` — add — assert
  `[project].name == "index-it-mcp"`.
- `test_console_script_aliases_match_release_contract` — add — assert
  `mcp-index`, `index-it-mcp`, and `code-index-mcp` console scripts remain
  available.
- `test_readme_install_paths_match_release_contract` — add — assert pip docs use
  `index-it-mcp`, while container docs use `ghcr.io/viperjuice/code-index-mcp`.
- `test_release_workflow_uses_exact_requested_rc_version` — add — assert
  release automation defaults to exact rc release behavior and no longer bumps
  from latest tags for rc inputs.
- `test_release_workflow_marks_rc_as_prerelease` — add — assert GitHub releases
  for rc/alpha/beta versions are created with `prerelease: true`.
- `test_release_workflow_does_not_push_latest_for_prerelease` — add — assert
  `latest` is added only for stable releases, not rc tags.

### `tests/test_p25_release_gates.py` (modify)

- `test_release_automation_refuses_before_mutating_or_publishing` — extend —
  keep current preflight-before-mutation checks and add assertions that exact
  version validation occurs before branch creation, tag creation, Docker push,
  GitHub release creation, and PyPI publish.
- New release workflow contract test — add — assert the default manual-dispatch
  path cannot compute a release from existing repository tags when an explicit
  `inputs.version` is provided.

### `.github/workflows/release-automation.yml` (modify)

- `workflow_dispatch.inputs.release_type.default` — modify — set to `custom`.
- `workflow_dispatch.inputs.release_type.options` — modify — list `custom`
  first to match the safe default.
- `Validate requested release version` step — modify — validate:
  - requested version starts with `v`;
  - requested version without `v` matches `pyproject.toml`;
  - requested version without `v` matches `mcp_server/__init__.py`;
  - prerelease versions require `release_type=custom`.
- `Determine Version` step — modify — use `inputs.version` exactly for
  `custom`; if non-custom is retained for future stable releases, fail when
  `inputs.version` is a prerelease.
- Image tag generation — add — create a `docker_tags` output:
  - always include `ghcr.io/viperjuice/code-index-mcp:<version>`;
  - include `ghcr.io/viperjuice/code-index-mcp:latest` only when the version is
    stable, not `-rc`, `-alpha`, or `-beta`.
- Docker build step — modify — consume the computed tag list instead of
  hard-coding `latest`.
- GitHub release step — modify — set `prerelease: true` for rc/alpha/beta
  versions and `false` only for stable releases.
- PyPI publish step — preserve — keep after artifact build and smoke gates, but
  rely on the exact package name from `pyproject.toml`.
- `post-release` docs rewrite — modify — remove broad
  `sed -i "s/code-index-mcp:.*/..."` replacement because it can corrupt docs;
  use targeted docs if needed.

### `pyproject.toml` (modify)

- `[project].name` — preserve as `index-it-mcp`.
- `[project].version` — preserve as `1.2.0-rc4`.
- `[project.urls]` — review/modify — ensure links target the current repository.
- `[project.scripts]` — preserve — keep all three entry points:
  `mcp-index`, `code-index-mcp`, and `index-it-mcp`.

### `README.md` (modify)

- Project status block — modify — explicitly distinguish:
  - Python distribution: `index-it-mcp`;
  - container image: `ghcr.io/viperjuice/code-index-mcp`;
  - MCP server/tool alias: `code-index-mcp`.
- Quick Start / pip install — modify — say pip install requires the rc4 package
  to be published; after publication use `pip install --pre index-it-mcp` or
  exact version `pip install index-it-mcp==1.2.0rc4`.
- Docker examples — modify — prefer `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc4`
  for public-alpha docs; reserve `latest` for stable releases.
- `Using Against Many Repos` — modify — document `MCP_ALLOWED_ROOTS` with
  `os.pathsep`: `:` on Unix, `;` on Windows.
- Release/prebuilt-index section — modify — either remove stale manual
  `scripts/create-release.py` guidance from the primary README path or clearly
  label it as legacy index-artifact tooling, not rc4 package publishing.

### `docs/GETTING_STARTED.md` (modify)

- Installation section — modify — align pip install command with
  `index-it-mcp` rc4 publication state and exact prerelease syntax.
- Multi-repo section — modify — include `MCP_ALLOWED_ROOTS` setup before
  repository registration and use `os.pathsep` language.
- Artifact-first startup — modify — make GitHub artifact access optional for new
  outside developers; document local rebuild fallback as first-class when no
  artifact exists or the user lacks `gh` access.

### `docs/security/path-guard.md` (modify)

- `MCP_ALLOWED_ROOTS` examples — preserve/modify — keep `os.pathsep` as the
  canonical separator and mention legacy comma tolerance only as compatibility,
  not as the documented standard.
- Fallback behavior — preserve — unset guard remains no-op for dev/test and is
  not recommended for production.

### `docs/DEPLOYMENT-GUIDE.md` (modify)

- `MCP_ALLOWED_ROOTS` section — modify — replace comma-separated guidance with
  `os.pathsep` separated guidance.
- Examples — modify — use Unix `:` and Windows `;` examples.

### `docs/configuration/ENVIRONMENT-VARIABLES.md` (modify)

- `MCP_ALLOWED_PATHS` section — modify/delete — replace stale `MCP_ALLOWED_PATHS`
  with the active `MCP_ALLOWED_ROOTS` contract.
- Type/example — modify — document `os.pathsep` separated absolute paths.
- Related variables — review — ensure `MCP_MAX_FILE_SIZE` versus
  `MCP_MAX_FILE_SIZE_BYTES` naming does not contradict the active runtime
  contract; fix only if tests already cover or if a targeted doc truth assertion
  is added.

### `AGENTS.md` (modify)

- Path sandbox section — preserve/modify — keep colon-separated Unix example but
  state the portable contract as `os.pathsep`.

### `docs/validation/private-alpha-decision.md` (modify after real evidence run)

- Historical banner — delete/replace — remove "Historical artifact" only after
  real private fixture evidence has been generated and reviewed.
- Fixture table — modify — replace local-smoke timings with redacted real fixture
  aggregate timings.
- Known issue `P26-LOCAL-001` — delete/replace — remove the "local checkout"
  limitation once real fixtures are used; add any real limitations discovered.
- Final decision — modify — keep `go` only if no real fixture issue is classified
  as `public_alpha_blocker`; otherwise record `conditional_go` or `no_go`.

### `docs/validation/private-alpha-decision.json` (modify after real evidence run)

- Fixture records — modify — replace local-smoke fixture records with redacted
  real fixture summaries.
- `known_issues` — modify — remove local-smoke-only issue IDs and add real
  issue classifications.
- `final_decision` — modify — must match the Markdown decision exactly.

### `docs/benchmarks/private-alpha-summary.md` (modify after real evidence run)

- Aggregate benchmark table — modify — replace local-checkout smoke metrics with
  real private fixture aggregate metrics.
- Caveat paragraph — modify — remove "suitable for validating the harness" once
  real evidence replaces the placeholder.

### `scripts/private_alpha_evidence.py` (modify only if evidence run exposes gaps)

- Redaction behavior — preserve — raw output remains under ignored
  `private-alpha-evidence/`.
- Fixture validation — modify only if needed — ensure the harness refuses missing
  categories before writing a `go` decision.
- Quality scoring — do not broaden for this pass unless current path-fragment
  checks cannot support the real fixture evidence; classify richer scoring as
  backlog if not required for rc4.

### `scripts/create-release.py` (modify or de-emphasize)

- Release notes install command — modify — use `index-it-mcp` exact prerelease
  syntax if this script remains documented.
- Script purpose — modify docs rather than expanding script behavior — this
  script creates GitHub index artifact releases, while
  `.github/workflows/release-automation.yml` is the package/container release
  path.

### GitHub repository workflow state (external operation)

- Stale workflow `Phase 5 Parallel Build` — disable — run:
  `gh workflow disable 166608681` or disable by path
  `.github/workflows/phase5-parallel.yml`.
- Reason — the workflow file is not present in current `HEAD`, but GitHub still
  lists it as active with an old failed run. This is repository state cleanup,
  not a source-file change.

### GHCR and PyPI release state (external operation)

- PyPI `index-it-mcp` — publish — publish `1.2.0rc4` only after the release
  workflow hardening passes.
- GHCR `v1.2.0-rc4` — publish — publish exact rc tag.
- GHCR `latest` — do not update — keep unchanged until a stable public release
  is intentionally promoted.
- GitHub release `v1.2.0-rc4` — create as prerelease — do not mark latest.

## Documentation impact

Documentation changes are part of the fix because several readiness gaps are
contract/documentation drift:

- `README.md` — package/container identity, external install path, rc Docker tag,
  multi-repo root separator, and stale release-script guidance.
- `docs/GETTING_STARTED.md` — outside-developer install flow and artifact fallback.
- `docs/security/path-guard.md` — canonical root separator.
- `docs/DEPLOYMENT-GUIDE.md` — production root separator.
- `docs/configuration/ENVIRONMENT-VARIABLES.md` — replace stale
  `MCP_ALLOWED_PATHS` with `MCP_ALLOWED_ROOTS`.
- `AGENTS.md` — keep agent/operator guidance aligned with runtime.
- `docs/validation/private-alpha-decision.md`,
  `docs/validation/private-alpha-decision.json`, and
  `docs/benchmarks/private-alpha-summary.md` — replace local smoke evidence with
  real private fixture evidence before external public-alpha publication.

## Dependencies & order

1. **Root separator contract first.**
   Fix the shared parser and tests before changing docs broadly. This removes
   the direct multi-repo correctness bug.

2. **Release identity tests second.**
   Freeze `index-it-mcp` as Python distribution and `code-index-mcp` as
   product/container alias in tests before editing workflow/docs.

3. **Release automation third.**
   Harden exact rc version behavior, prerelease flags, and image tagging before
   any external publish operation.

4. **Docs fourth.**
   Update outside-developer and operator docs after runtime/workflow behavior is
   fixed, so docs describe tested behavior.

5. **Private evidence fifth.**
   Run the real P26 fixture harness after docs/workflow contracts are correct.
   This may produce a blocker; do not publish until blocker classification is
   resolved.

6. **External state cleanup sixth.**
   Disable the stale workflow, then publish rc4 artifacts. Do this only after
   source changes are committed and CI is green.

## Verification

Do not run these during planning; run them during implementation.

Targeted tests:

```bash
uv run pytest \
  tests/test_bootstrap.py \
  tests/security/test_path_traversal.py \
  tests/test_handler_path_sandbox.py \
  -q --no-cov --benchmark-skip

uv run pytest \
  tests/test_release_metadata.py \
  tests/test_p25_release_gates.py \
  tests/test_requirements_consolidation.py \
  tests/smoke/test_release_smoke_contract.py \
  -q --no-cov --benchmark-skip

uv run pytest \
  tests/test_p26_alpha_evidence.py \
  tests/docs/test_p26_public_alpha_decision.py \
  -q --no-cov --benchmark-skip
```

Manual contract checks:

```bash
uv run python - <<'PY'
import os
from mcp_server.cli.bootstrap import _allowed_roots
os.environ["MCP_ALLOWED_ROOTS"] = "/tmp/a:/tmp/b"
print([str(p) for p in _allowed_roots()])
PY

python -m pip index versions index-it-mcp || true
docker manifest inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc4
gh workflow list --all
gh release view v1.2.0-rc4 --json isPrerelease,isLatest,tagName
```

Release gates after implementation:

```bash
make alpha-release-gates
make release-smoke-container
```

Private-alpha evidence run:

```bash
uv run python scripts/private_alpha_evidence.py \
  --config <private-config.json> \
  --output-dir private-alpha-evidence/<run-id> \
  --redacted-md docs/validation/private-alpha-decision.md \
  --redacted-json docs/validation/private-alpha-decision.json

rg -n "/home/|/Users/|source_snippet|raw_log|customer|secret|token" \
  docs/validation/private-alpha-decision.md \
  docs/validation/private-alpha-decision.json \
  docs/benchmarks/private-alpha-summary.md
```

External release checks after publishing:

```bash
python -m pip index versions index-it-mcp
python -m pip install --dry-run --pre index-it-mcp==1.2.0rc4
docker manifest inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc4
gh run list --commit HEAD --json workflowName,status,conclusion
```

## Acceptance criteria

- [ ] STDIO and REST both parse `MCP_ALLOWED_ROOTS` through the same helper.
- [ ] `MCP_ALLOWED_ROOTS=/tmp/a:/tmp/b` resolves as two roots on Unix.
- [ ] Legacy comma-separated roots remain tolerated or are explicitly rejected
      with updated docs and tests; this plan chooses tolerance.
- [ ] README, deployment docs, path-guard docs, environment-variable docs, and
      AGENTS all describe one canonical root separator contract.
- [ ] Tests freeze `index-it-mcp` as the Python distribution name and
      `ghcr.io/viperjuice/code-index-mcp` as the container image name.
- [ ] Release automation defaults to exact `v1.2.0-rc4` custom release behavior.
- [ ] Release automation cannot compute from old `v2.x` tags when an rc version
      is requested.
- [ ] GitHub rc release is marked prerelease.
- [ ] RC container publish produces `v1.2.0-rc4` and does not move `latest`.
- [ ] PyPI has `index-it-mcp==1.2.0rc4`, or docs explicitly state pip install is
      unavailable and direct users to source/container paths.
- [ ] P26 evidence is generated from real selected private fixtures, not the
      local checkout placeholder.
- [ ] Redacted P26 artifacts contain no private paths, repo names, snippets,
      raw logs, secrets, or tokens.
- [ ] Stale `Phase 5 Parallel Build` workflow is disabled in GitHub.
- [ ] `make alpha-release-gates` and `make release-smoke-container` pass before
      publishing.
