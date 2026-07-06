# Phase roadmap v9 panel review

Review requested before implementation on 2026-07-06.

## Panel

| Leg | Requested model | Status | Result |
|---|---|---|---|
| Codex | `gpt-5.5` | OK | Usable review returned |
| Gemini | `Gemini 3.1 Pro Preview` | OK | Usable review returned |
| Fable | `claude-fable-5` | OK | Usable review returned |

Raw panel output was captured locally in
`specs/phase-plans-v9_panel_results.json`.

## Converged Findings

The panel did not approve implementation against the first v9 draft. It found
the roadmap shape broadly correct, but required amendments before planning
`PUBNAME`.

### Required Amendments Applied

- `PUBNAME` now requires owner/version verification for the live
  `index-it-mcp` PyPI package before docs may claim live PyPI readiness.
- `PUBNAME` now inventories every identity surface: distribution name, console
  scripts, Click program name, MCP server IDs, container image, profile/config
  filenames, `.mcp.json` examples, repo name, and npm kit/package names.
- `PUBNAME` now explicitly evaluates removing or justifying the
  `code-index-mcp` console-script alias.
- `PUBNAME` install smoke now uses a locally built wheel unless live
  PyPI ownership/version is proven.
- `REPOCLEAN` now uses `git ls-files` for path auditing and freezes the tracked
  relative path limit at 160 characters.
- `REPOCLEAN` now includes a tracked-but-ignored audit and package-install
  path-depth check.
- `LOCALCI` now freezes exact `make agent-*` command names.
- `LOCALCI` now audits every workflow and requires reducing the existing hosted
  per-PR footprint rather than adding a parallel validation path.
- `COVERAGE` now reconciles existing thresholds, forbids committed coverage
  artifacts, and requires fresh generated evidence.
- `PROCENV` now freezes a helper path/function contract and no longer blocks
  friction extraction.
- `FRICTION` now defines a generic search-source metadata envelope.
- `HISTORY` now depends on both `FRICTION` and `PROCENV`.
- `PYCLIENT` now explicitly waits because the supported client API should expose
  code, friction, and historical issue source filters from day one.

## Phase Order

The panel agreed that `PUBNAME -> REPOCLEAN -> LOCALCI -> COVERAGE` is the right
front half. The amended DAG lets `COVERAGE`, `PROCENV`, and `FRICTION` proceed
independently after `LOCALCI`; `HISTORY` waits on `FRICTION` and `PROCENV`;
`PYCLIENT` waits on the richer source contracts and coverage.

## Recommendation

Proceed to `PUBNAME` only after the amended roadmap validates.
