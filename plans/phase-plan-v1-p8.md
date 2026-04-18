# P8: Doc Truth — Customer Audience & Historical Artifact Sweep

## Context

Phases P1–P6B of the multi-repo refactor have shipped. P7 (in parallel with this phase) handles agent/machine-facing docs (`AGENTS.md`, `specs/active/architecture.md`, `stdio_runner.py` schemas). P8 handles the customer-facing prose and the long-tail historical doc sweep. The two phases have fully disjoint file ownership and are parallelizable.

**README.md** (1204 LOC): stale strings at `L88` (`Production-Ready Features:`), `L110` (`Implementation Status: Production-Ready`), `L1139` (`100% implemented`), `L1140` (`fully operational`). FastAPI-primary framing at `L947-960` (endpoint tables for `GET /symbol`, `GET /search`) and at `L362`/`L365` (curl examples). "beta" is mentioned in scattered places (`L8`, `L32`) but no prominent Beta admonition. MCP tool-based usage is demoted below REST.

**docs/GETTING_STARTED.md** (253 LOC): curl examples at `L104` (`POST /search`) and `L109` (`symbol?symbol_name=`). The `.mcp.json` snippet at `L112-126` registers a server but shows no tool-call JSON. Customers arriving via this doc learn REST first, MCP second — inverted.

**docs/DEPLOYMENT-GUIDE.md** (985 LOC): a `## Security Best Practices` section exists at `L710` with subsections `### 1. Authentication and Authorization`, `### 2. Input Validation`, `### 3. Rate Limiting`, `### 4. Network Security`. Neither `MCP_CLIENT_SECRET` nor `MCP_ALLOWED_ROOTS` is mentioned anywhere in the file.

**Spec heading ambiguity (resolved here)**: the spec says "has a `## Security` section mentioning both `MCP_CLIENT_SECRET` and `MCP_ALLOWED_ROOTS` by name". Two readings are possible: (a) the heading must become the exact literal `## Security`, renaming the existing `## Security Best Practices` heading and absorbing its subsections; (b) any H2 beginning with `## Security` qualifies. This plan picks **(b)**: add a new subsection `### MCP Access Controls` inside the existing `## Security Best Practices` block, naming both env vars in subsection body. Rationale: (a) requires a collateral heading rename that invalidates any external anchors (e.g. `DEPLOYMENT-GUIDE.md#security-best-practices`) and destructively reshapes an already-structured section for no semantic gain; (b) satisfies the grep `grep -nE '^## Security' docs/DEPLOYMENT-GUIDE.md` and the env-var greps with additive edits only. IF-0-P8-2 encodes (b) with an explicit regex.

**Historical sweep inventory** (43 files total; `ls` verified — scout's earlier 46 figure was stale):
- `docs/implementation/` — 20 files
- `docs/status/` — 20 files
- `docs/validation/` — 3 files

**PROJECT_STRUCTURE.md coupling**: `docs/PROJECT_STRUCTURE.md` L125-140 lists `docs/implementation/`, `docs/status/`, `docs/validation/` as part of the documentation tree. Any deletions inside those dirs do not invalidate that list (the dirs remain, just with fewer files); if a directory ends up empty post-sweep, SL-3 must update PROJECT_STRUCTURE.md in the same commit to avoid nav drift. `mkdocs.yml` was previously inspected and has no explicit nav for these files — no mkdocs change needed.

**No HISTORICAL-ARTIFACTS-TRIAGE.md exists** — SL-3 creates it.

**Banner text**: the exit-criterion grep is `grep -L 'Historical artifact'`, so any banner containing the substring `Historical artifact` passes. This plan requires the **actual date `2026-04-18`** in the banner (not the literal template `YYYY-MM-DD`), to keep the artifact forensically useful after the sweep. Rationale: the phrase "as-of 2026-04-18" is the signal an archaeologist needs; leaving `YYYY-MM-DD` verbatim makes every bannered file look equally stale and defeats the triage log's cross-reference value. Each bannered file on line 1 MUST read verbatim: `> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**`.

**Replacement-phrasing hazard (carried from P7)**: the naive replacement "no longer 100% implemented" silently re-matches the grep `100% implemented`; "previously production-ready" matches `Production-Ready`. SL-1 verify MUST re-run the stale-claim greps post-edit. Acceptance test enforces this programmatically.

`CLAUDE.md`, `mcp_server/CLAUDE.md`, and `AGENTS.md` (post-P7) are invariant for this phase. `mcp_server/` source is invariant. P8 is a pure docs phase.

## Interface Freeze Gates

- [ ] **IF-0-P8-1** — `README.md` stale-claim greps all return zero: `grep -nE '(Production-Ready|Implementation Status: Production|100% implemented|fully operational)' README.md` returns zero matches. The file contains exactly one "Beta status" admonition near the top (within first 80 lines): a blockquote whose first line begins with `> **Beta status**:` and whose body names both the MCP tool interface as primary and the FastAPI REST surface as a secondary admin surface. This literal pattern is self-contained — P8 does NOT depend on P7's AGENTS.md having landed first. The REST endpoint tables at former `L947-960` (`GET /symbol`, `GET /search`) are either removed or demoted under an explicit "Admin REST Interface (secondary)" heading; the primary usage section shows MCP tool-call JSON (tool name + arguments object for `search_code` and `symbol_lookup`). FastAPI curl examples at former `L362`/`L365` are replaced with MCP tool-call JSON equivalents. All pre-existing non-stale content (architecture overview, language support matrix, benchmark numbers) is preserved.
- [ ] **IF-0-P8-2** — `docs/GETTING_STARTED.md` contains zero matches for `grep -nE 'curl .*(search|symbol)' docs/GETTING_STARTED.md`. The "Search Your Code" section leads with a **Via MCP Protocol** subsection that shows (i) the `.mcp.json` registration AND (ii) at least one tool-call JSON example using `search_code` with an `arguments` object, AND (iii) at least one tool-call JSON example using `symbol_lookup` with an `arguments` object. A **Via REST API (admin/debug)** subsection MAY remain as a secondary alternative but MUST NOT use the words "primary" or lead the section.
- [ ] **IF-0-P8-3** — `docs/DEPLOYMENT-GUIDE.md` satisfies `grep -nE '^## Security' docs/DEPLOYMENT-GUIDE.md` with at least one match, AND `grep -n 'MCP_CLIENT_SECRET' docs/DEPLOYMENT-GUIDE.md` returns at least one line inside the range of the `## Security`-prefixed H2 section, AND `grep -n 'MCP_ALLOWED_ROOTS' docs/DEPLOYMENT-GUIDE.md` returns at least one line inside that same range. The existing `## Security Best Practices` heading is preserved (no rename). A new subsection `### MCP Access Controls` is added inside it, containing a prose paragraph naming both env vars by name and a code block or table documenting their intent. No existing subsections (`### 1. Authentication…` etc.) are removed or renumbered.
- [ ] **IF-0-P8-4** — Every file under `docs/implementation/`, `docs/status/`, `docs/validation/` is either (a) deleted, (b) begins with a line-1 banner matching the exact regex `^> \*\*Historical artifact — as-of 2026-04-18, may not reflect current behavior\*\*\s*$`, or (c) rewritten such that the phrase "Historical artifact" still appears as a line-1 banner. The shell command `grep -L 'Historical artifact' docs/implementation/*.md docs/status/*.md docs/validation/*.md` returns only names of files that `git status` confirms are deleted in the P8 diff (i.e. zero "present but unbannered" files).
- [ ] **IF-0-P8-5** — `docs/HISTORICAL-ARTIFACTS-TRIAGE.md` exists and is a markdown table with columns `| Path | Disposition | Rationale | As-of |` (header row exactly this). Every file that was in `docs/implementation/`, `docs/status/`, or `docs/validation/` at P7-merge time has exactly one row in the table. Disposition values are one of `deleted`, `bannered`, `rewritten`. The `As-of` column is `2026-04-18` on every row. Grouped by H3 subsection per directory (`### docs/implementation/`, `### docs/status/`, `### docs/validation/`).
- [ ] **IF-0-P8-6** — Cross-cutting invariants (both lanes must respect): `CLAUDE.md`, `mcp_server/CLAUDE.md`, `AGENTS.md`, and every file under `mcp_server/` are byte-identical to their pre-P8 state (`git diff main -- CLAUDE.md mcp_server/CLAUDE.md AGENTS.md mcp_server/` is empty). `specs/active/architecture.md` is also invariant in P8 (owned by P7).

## Lane Index & Dependencies

```
SL-1 — Customer-primary prose (README.md + docs/GETTING_STARTED.md)
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-2 — Deployment security section (docs/DEPLOYMENT-GUIDE.md)
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-3 — Historical sweep + triage log (docs/implementation|status|validation/, docs/HISTORICAL-ARTIFACTS-TRIAGE.md)
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes
```

Spec mandates three lanes. Agreed. Kept as-is — splitting the historical sweep into two sub-lanes (e.g. impl+status vs validation+triage-log) would create an artificial boundary since the triage log is single-owner and must be authored atomically against the full sweep. 43 files is mechanical work (banner prepend or delete); one teammate handles it cleanly. README + GETTING_STARTED are kept in a single lane because the MCP-tool-call JSON examples must be consistent between the two files (same argument shape, same tool names); splitting risks drift. DEPLOYMENT-GUIDE security section is structurally independent and stays its own lane.

## Lanes

### SL-1 — Customer-primary prose (README.md + docs/GETTING_STARTED.md)

- **Scope**: Rewrite `README.md` to (i) add a "Beta status" blockquote near the top, (ii) strip the four stale strings at `L88`, `L110`, `L1139`, `L1140` via affirmative replacement phrasing that does NOT contain the forbidden substrings, (iii) replace the FastAPI-primary curl examples at `L362`/`L365` and the REST endpoint tables at `L947-960` with MCP tool-call JSON examples (or demote REST under an explicit "Admin REST Interface (secondary)" heading), (iv) preserve all architecture, language-support, and benchmark content. Rewrite `docs/GETTING_STARTED.md` "Search Your Code" section so the **Via MCP Protocol** subsection leads with `.mcp.json` registration AND tool-call JSON examples for `search_code` and `symbol_lookup` with `arguments` objects; REST/curl examples are either removed or demoted under "Via REST API (admin/debug)". Do NOT touch `docs/DEPLOYMENT-GUIDE.md`, `AGENTS.md`, `CLAUDE.md`, `mcp_server/`, or the historical-sweep dirs.
- **Content map (README, to prevent re-derivation by the lane teammate)**:
  - **Remove**: the four stale-string sites at L88 (`Production-Ready Features:`), L110 (`Implementation Status: Production-Ready …` paragraph), L1139 (`Workspace Definition: 100% implemented …`), L1140 (`System Context (L1): … fully operational`). Replace with affirmative beta-aware phrasing.
  - **Keep verbatim**: language-support matrix (L97-108), benchmark tables (L1120-1133), architecture overview (L1135-1145 minus the removed stale lines), roadmap pointer (L1147-1149).
  - **Demote**: REST endpoint tables at L947-960 (`GET /symbol`, `GET /search`) under a new H2 `## Admin REST Interface (secondary)` or similar; curl examples at L362/L365 replaced inline with MCP tool-call JSON equivalents.
  - **Add**: Beta-status blockquote within first 80 lines; primary-usage section featuring MCP tool-call JSON for `search_code` and `symbol_lookup` with `arguments` objects.
- **Rewrite depth (README)**: proportionate reorganization — not a minimal stale-string patch. Spec language ("rewrite human-facing docs to reflect beta status and tool-based MCP usage") mandates tool-based MCP as primary framing, which requires more than line-level edits. The four stale-string sites must be fixed AND the primary-usage narrative must invert (MCP tool-call leads, REST demoted). This is closer to option (b) in the teammate's design question — reorganize to lead with MCP tool usage.
- **Owned files**: `README.md`, `docs/GETTING_STARTED.md`, `tests/docs/test_p8_customer_docs_alignment.py` (new).
- **Interfaces provided**: IF-0-P8-1, IF-0-P8-2.
- **Interfaces consumed**: (pre-existing) — root lane.
- **Execution hint**: `claude-opus-4-7` / high — large judgment-heavy rewrite (README is 1204 LOC; the "invert primary surface" reorganization requires understanding which sections to keep vs relocate; replacement-phrasing hazard from P7 applies). Prose quality directly affects customer perception.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/docs/test_p8_customer_docs_alignment.py` | stale-claim greps on README (`Production-Ready`, `Implementation Status: Production`, `100% implemented`, `fully operational`) all zero; README contains `Beta status` admonition; README contains `search_code` AND `symbol_lookup` as MCP tool names with JSON argument examples; GETTING_STARTED `curl .*(search|symbol)` grep zero; GETTING_STARTED `search_code` and `symbol_lookup` tool-call JSON present; GETTING_STARTED contains `.mcp.json` string | `pytest tests/docs/test_p8_customer_docs_alignment.py -v --no-cov` |
| SL-1.2 | impl | SL-1.1 | `README.md`, `docs/GETTING_STARTED.md` | — | — |
| SL-1.3 | verify | SL-1.2 | `README.md`, `docs/GETTING_STARTED.md`, `tests/docs/test_p8_customer_docs_alignment.py` | all SL-1.1 assertions pass; `git diff main -- docs/DEPLOYMENT-GUIDE.md AGENTS.md CLAUDE.md mcp_server/CLAUDE.md` empty; no files under `mcp_server/` modified | `pytest tests/docs/test_p8_customer_docs_alignment.py -v --no-cov && ! git diff --name-only main..HEAD \| grep -E '^(AGENTS\.md\|CLAUDE\.md\|mcp_server/)'` |

- **Risks**: (i) replacement-phrasing re-match (e.g. "no longer 100% implemented"); (ii) over-delete of REST content customers depend on — keep REST as secondary, don't strip it; (iii) MCP tool-call JSON must be shape-consistent between README and GETTING_STARTED (same tool names, same argument keys) — write both files in a single session to avoid drift.

### SL-2 — Deployment security section (docs/DEPLOYMENT-GUIDE.md)

- **Scope**: Inside the existing `## Security Best Practices` section at `L710`, add a new subsection `### MCP Access Controls` that (i) names `MCP_CLIENT_SECRET` in prose — its purpose (shared-secret handshake for MCP client authentication), default behavior when unset, and guidance for rotation/storage — AND (ii) names `MCP_ALLOWED_ROOTS` in prose — its purpose (path-prefix allowlist for multi-repo access), format (colon-separated absolute paths), failure mode when a request targets a path outside the allowlist. Include at least one code block showing both env vars set. Do NOT rename the `## Security Best Practices` heading. Do NOT remove or renumber the existing `### 1. Authentication…` / `### 2. Input Validation` / `### 3. Rate Limiting` / `### 4. Network Security` subsections — the new subsection is purely additive. Do NOT touch any other file.
- **Owned files**: `docs/DEPLOYMENT-GUIDE.md`, `tests/docs/test_p8_deployment_security.py` (new).
- **Interfaces provided**: IF-0-P8-3.
- **Interfaces consumed**: (pre-existing) — root lane.
- **Execution hint**: `claude-sonnet-4-6` / medium — additive prose with a clear anchor. Factual content about two env vars; not judgment-heavy but must be accurate (cross-reference `mcp_server/` source for semantics before writing).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/docs/test_p8_deployment_security.py` | `^## Security` regex matches ≥1 heading; `MCP_CLIENT_SECRET` appears ≥1 time inside first `## Security`-prefixed section (line-range test); same for `MCP_ALLOWED_ROOTS`; existing `### 1. Authentication and Authorization` heading unchanged; `### MCP Access Controls` subsection present | `pytest tests/docs/test_p8_deployment_security.py -v --no-cov` |
| SL-2.2 | impl | SL-2.1 | `docs/DEPLOYMENT-GUIDE.md` | — | — |
| SL-2.3 | verify | SL-2.2 | `docs/DEPLOYMENT-GUIDE.md`, `tests/docs/test_p8_deployment_security.py` | all SL-2.1 assertions pass; `git diff --name-only main..HEAD` shows only `docs/DEPLOYMENT-GUIDE.md` and the test file | `pytest tests/docs/test_p8_deployment_security.py -v --no-cov` |

- **Risks**: (i) factual accuracy about env-var semantics — SL-2 teammate MUST grep `mcp_server/` for both env var names before writing, to ground the prose in actual code behavior; (ii) accidental rename of `## Security Best Practices` to `## Security` — forbidden by IF-0-P8-3 (would break external anchors).

### SL-3 — Historical sweep + triage log

- **Scope**: For each of the 43 `.md` files under `docs/implementation/`, `docs/status/`, `docs/validation/`, apply one of three dispositions: **delete** (file describes vanished code or is superseded), **banner** (design discussion, benchmark result, or historical snapshot worth keeping as-of), or **rewrite** (only if low effort and the file has active callers). Banner format: line 1 is exactly `> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**`, followed by a blank line 2, then pre-existing content. Create `docs/HISTORICAL-ARTIFACTS-TRIAGE.md` with grouped subsections per directory and one row per file in a table with columns `| Path | Disposition | Rationale | As-of |`. If any of the three directories ends up empty after deletions, update `docs/PROJECT_STRUCTURE.md` L125-140 in the same commit to note the archived status (single-writer: SL-3 owns PROJECT_STRUCTURE.md edits for this phase; no collision with SL-1 or SL-2). Do NOT touch `README.md`, `docs/GETTING_STARTED.md`, `docs/DEPLOYMENT-GUIDE.md`, `AGENTS.md`, `CLAUDE.md`, `mcp_server/`.
- **Disposition-rule for UNDECIDED files**: scout flagged 3 files in `docs/implementation/` as undecided. The push-toward-single-choice rule: if a grep of `mcp_server/`, `scripts/`, and `tests/` shows the file's central subject (named module, class, or CLI command) still exists in current code, `banner` the file. If the central subject has vanished, `delete`. If >50% of the file's named references have vanished but some remain, `banner` with a leading note "partial; see HISTORICAL-ARTIFACTS-TRIAGE.md row for scope". Do NOT `rewrite` unless the file is <100 LOC AND has active external callers (mkdocs nav, README link, another doc's relative-link) — discovered by `grep -r <basename>.md docs/ README.md AGENTS.md`.
- **Owned files**: `docs/implementation/*.md` (all 20), `docs/status/*.md` (all 20), `docs/validation/*.md` (all 3), `docs/HISTORICAL-ARTIFACTS-TRIAGE.md` (new), `docs/PROJECT_STRUCTURE.md` (conditional single-writer for this phase), `tests/docs/test_p8_historical_sweep.py` (new).
- **Interfaces provided**: IF-0-P8-4, IF-0-P8-5.
- **Interfaces consumed**: (pre-existing) — root lane.
- **Execution hint**: `claude-sonnet-4-6` / medium — mechanical but high-cardinality (43 files). Each per-file disposition is a 30-second judgment (grep for current-code references, then banner/delete). Triage table authoring is straightforward. Medium thinking ensures the undecided-file rule is applied consistently.
- **Candidate deletion list** (scout-suggested 13+3+0 = 16; SL-3 teammate may adjust based on disposition rule, but each change must be reflected in the triage log):
  - `docs/implementation/` (scout-suggested 13): `ADAPTIVE_CHUNKING_IMPLEMENTATION.md`, `ALIGNMENT_PLAN_2025-01-06.md`, `BM25_HYBRID_SEARCH_IMPLEMENTATION.md`, `COMPATIBILITY_TESTING_SUMMARY.md`, `CONTEXTUAL_EMBEDDINGS_SUMMARY.md`, `DOCUMENTATION_UPDATE_REPORT_2025-01-06-FINAL.md`, `DOCUMENTATION_UPDATE_REPORT_2025-01-06.md`, `DOCUMENTATION_UPDATE_REPORT_2025-06-10.md`, `GIT_HOOKS_IMPLEMENTATION_SUMMARY.md`, `IMPLEMENTATION_SUMMARY.md`, `INDEX_MANAGEMENT_SUMMARY.md`, `PATH_MANAGEMENT_IMPLEMENTATION_PLAN.md`, `PATH_MANAGEMENT_IMPLEMENTATION_SUMMARY.md`.
  - `docs/status/` (scout-suggested 3): `DEBUG_AND_FIX_PLAN.md`, `TEST_SUITE_DEBUG_REPORT.md`, `TEST_SUITE_IMPLEMENTATION_REPORT.md`.
  - `docs/validation/` (scout-suggested 0): none.
  - **Total candidates: 16 deletions**. This is the "Known destructive changes" whitelist for execute-phase's pre-merge check.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/docs/test_p8_historical_sweep.py` | every non-deleted file under `docs/implementation|status|validation/*.md` has line 1 matching regex `^> \*\*Historical artifact — as-of 2026-04-18, may not reflect current behavior\*\*\s*$`; `docs/HISTORICAL-ARTIFACTS-TRIAGE.md` exists with required header row; **deleted-set enumeration uses `git diff --diff-filter=D --name-only main..HEAD -- docs/implementation/ docs/status/ docs/validation/`**, unioned with the current `*.md` glob on those dirs; triage table row count equals the size of that union; every row's Path points to a file that is either currently present OR in the deleted set (no phantom rows); disposition values restricted to `deleted\|bannered\|rewritten`; per-directory H3 subsection count is 3 | `pytest tests/docs/test_p8_historical_sweep.py -v --no-cov` |
| SL-3.2 | impl | SL-3.1 | 43 files in 3 dirs, triage log, optional PROJECT_STRUCTURE.md | — | — |
| SL-3.3 | verify | SL-3.2 | all SL-3 owned files | all SL-3.1 assertions pass; `git status` shows only SL-3-owned paths modified | `pytest tests/docs/test_p8_historical_sweep.py -v --no-cov && ! git diff --name-only main..HEAD \| grep -vE '^(docs/(implementation\|status\|validation)/.*\.md\|docs/HISTORICAL-ARTIFACTS-TRIAGE\.md\|docs/PROJECT_STRUCTURE\.md\|tests/docs/test_p8_historical_sweep\.py)$'` |

- **Risks**: (i) nav drift — a delete that breaks `docs/markdown-table-of-contents.md` or an in-repo relative link; SL-3 teammate MUST grep `docs/ README.md AGENTS.md` for each deletion candidate's basename before deleting, and if found, downgrade to `banner`; (ii) triage-log drift against the actual sweep — the test enforces one row per present-or-deleted file, catching both missed files and phantom rows; (iii) byte-exact banner string — easy to get an em-dash vs hyphen wrong; the test regex is the authoritative spec.

## Execution Notes

- **Single-writer files**:
  - `docs/PROJECT_STRUCTURE.md` — SL-3 only (conditional edit). Not touched by SL-1 or SL-2.
  - `tests/docs/test_p8_customer_docs_alignment.py` — SL-1 only.
  - `tests/docs/test_p8_deployment_security.py` — SL-2 only.
  - `tests/docs/test_p8_historical_sweep.py` — SL-3 only.
  - Mirrors P7's per-lane test-file strategy (one test file per lane; avoids a consolidated test file becoming a write-collision point).
- **Known destructive changes (whitelist for execute-phase pre-merge check)**: 16 file deletions listed above in SL-3. Any additional deletions in SL-3's final diff must be justified in the triage log and are at the SL-3 teammate's discretion per the disposition rule — but the execute-phase pre-merge check should surface any delta >20% from this whitelist as a warning.
- **Expected add/add conflicts**: none. SL-1, SL-2, SL-3 touch fully disjoint directories and files.
- **SL-0 re-exports**: none — no SL-0 preamble lane in this phase.
- **Worktree naming**: execute-phase allocates unique names via `scripts/allocate_worktree_name.sh`. Plan doc does not spell out lane worktree paths.
- **Stale-base guidance**: all three lanes are root lanes (no upstream dependency, runnable in parallel with P7). If a lane's worktree base is pre-P6B merge (`d795d36` or earlier), the teammate MUST stop and report — do not silently rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge. No inter-lane sequencing hazards within P8; no P7↔P8 hazards because ownership is disjoint.
- **Test-coupling pre-check (SL-1)**: before editing `README.md` L88/L110/L1139/L1140 and `docs/GETTING_STARTED.md` L104/L109, grep `tests/` for any literal string on those lines. If any test asserts the stale phrasing exists, SL-1 owns updating that test in the same commit. (Pre-check at plan time: none known.)
- **Nav-coupling pre-check (SL-3)**: before deleting any file, grep `docs/ README.md AGENTS.md docs/PROJECT_STRUCTURE.md` for the file's basename. `docs/markdown-table-of-contents.md` was flagged as a potential nav-risk hub; at plan time its presence was not verified, so SL-3 teammate MUST explicitly `ls` it and, if present, include it in the basename-grep set. Downgrade to `banner` on any incoming-link hit and note in triage log.
- **Replacement-phrasing hazard (SL-1)**: the P7 lesson. "No longer fully operational" re-matches `fully operational`; "previously production-ready" re-matches `Production-Ready`; "100% implemented → now partially" re-matches `100% implemented`. SL-1 teammate MUST use affirmative phrasing that contains none of the forbidden substrings (e.g. "Beta: multi-repo support and MCP STDIO interface are in active development" replaces "Implementation Status: Production-Ready"; "Extensive language coverage across 46+ tree-sitter grammars" replaces "Production-Ready Features:"). SL-1.1 test enforces via post-edit regrep.
- **Banner byte-exactness (SL-3)**: the banner uses an em-dash (—, U+2014), not a hyphen-minus. Copying it from this plan doc preserves it; typing it fresh risks substitution. SL-3.1 test regex uses the literal em-dash.
- **Factual grounding (SL-2)**: SL-2 teammate MUST `grep -rn 'MCP_CLIENT_SECRET\|MCP_ALLOWED_ROOTS' mcp_server/` before writing the security subsection, to ground env-var behavior description in actual code. Do not guess semantics.
- **No handler / no source edits**: this is a pure docs phase. Any file under `mcp_server/` modified by any lane is out of scope — reject at verify time. IF-0-P8-6 enforces.
- **Parallel with P7**: P7 owns `AGENTS.md`, `specs/active/architecture.md`, `mcp_server/cli/stdio_runner.py`, `tests/docs/test_p7_*.py`. P8 owns everything above. Zero overlap. Either phase may land first.

## Acceptance Criteria

- [ ] `grep -nE '(Production-Ready|Implementation Status: Production|100% implemented|fully operational)' README.md` returns zero matches — asserted programmatically in `tests/docs/test_p8_customer_docs_alignment.py`.
- [ ] README.md contains a "Beta status" blockquote near the top (within first 80 lines) — asserted programmatically.
- [ ] README.md primary-usage section names `search_code` and `symbol_lookup` as MCP tool names with at least one JSON `arguments` object example each — asserted programmatically.
- [ ] `grep -nE 'curl .*(search|symbol)' docs/GETTING_STARTED.md` returns zero matches — asserted programmatically.
- [ ] `docs/GETTING_STARTED.md` "Search Your Code" section contains both `.mcp.json` AND tool-call JSON examples for `search_code` AND `symbol_lookup` — asserted programmatically.
- [ ] `grep -nE '^## Security' docs/DEPLOYMENT-GUIDE.md` returns ≥1 match AND `grep -n 'MCP_CLIENT_SECRET' docs/DEPLOYMENT-GUIDE.md` returns ≥1 line inside the section AND same for `MCP_ALLOWED_ROOTS` — asserted programmatically in `tests/docs/test_p8_deployment_security.py`.
- [ ] `docs/DEPLOYMENT-GUIDE.md` contains subsection heading `### MCP Access Controls` AND preserves `### 1. Authentication and Authorization` / `### 2. Input Validation` / `### 3. Rate Limiting` / `### 4. Network Security` — asserted programmatically.
- [ ] Every non-deleted `.md` file under `docs/implementation|status|validation/` has line 1 matching `^> \*\*Historical artifact — as-of 2026-04-18, may not reflect current behavior\*\*\s*$` — asserted programmatically in `tests/docs/test_p8_historical_sweep.py`.
- [ ] `docs/HISTORICAL-ARTIFACTS-TRIAGE.md` exists with header `| Path | Disposition | Rationale | As-of |`, three H3 subsections (one per sweep dir), and one row per present-or-deleted file — asserted programmatically.
- [ ] `git diff main -- CLAUDE.md mcp_server/CLAUDE.md AGENTS.md mcp_server/` is empty — asserted at verify step in each lane.
- [ ] `specs/active/architecture.md` byte-identical to its P7-merge state — asserted at verify step (owned by P7, invariant here).
- [ ] `tests/docs/test_p8_customer_docs_alignment.py`, `tests/docs/test_p8_deployment_security.py`, `tests/docs/test_p8_historical_sweep.py` all pass.

## Verification

```bash
# SL-1 customer docs
pytest tests/docs/test_p8_customer_docs_alignment.py -v --no-cov

# SL-2 deployment security
pytest tests/docs/test_p8_deployment_security.py -v --no-cov

# SL-3 historical sweep
pytest tests/docs/test_p8_historical_sweep.py -v --no-cov

# Cross-cutting invariants
git diff main -- CLAUDE.md mcp_server/CLAUDE.md AGENTS.md mcp_server/ specs/active/architecture.md
# ↑ must be empty

# Exit-criterion greps (authoritative)
grep -nE '(Production-Ready|Implementation Status: Production|100% implemented|fully operational)' README.md
# ↑ must be empty
grep -nE 'curl .*(search|symbol)' docs/GETTING_STARTED.md
# ↑ must be empty
grep -nE '^## Security' docs/DEPLOYMENT-GUIDE.md
# ↑ must have ≥1 match
grep -n 'MCP_CLIENT_SECRET\|MCP_ALLOWED_ROOTS' docs/DEPLOYMENT-GUIDE.md
# ↑ must have ≥2 matches
grep -L 'Historical artifact' docs/implementation/*.md docs/status/*.md docs/validation/*.md 2>/dev/null
# ↑ must return only names that git confirms are deleted (ideally empty in present-file listing)
test -f docs/HISTORICAL-ARTIFACTS-TRIAGE.md && echo OK
# ↑ must print OK

# Full P8 suite
pytest tests/docs/test_p8_customer_docs_alignment.py tests/docs/test_p8_deployment_security.py tests/docs/test_p8_historical_sweep.py -v --no-cov
```

All assertions pass, all cross-cutting `git diff` queries return empty, and all exit-criterion greps match the stated expectations. Any source-code edit under `mcp_server/`, any `AGENTS.md` / `CLAUDE.md` / `mcp_server/CLAUDE.md` edit, any `specs/active/architecture.md` edit, or any lane modifying a file outside its owned-files glob fails the phase.

## Risks / Known Issues

- **Sweep size (43 files)**: one lane is sufficient. Mechanical disposition work; the triage log is single-owner and benefits from atomic authoring. Splitting creates a coordination tax without a concrete collision to avoid.
- **`## Security` heading ambiguity**: resolved in favor of additive subsection (option (b)); IF-0-P8-2 regex pins the exact contract so lane teammate cannot drift into option (a).
- **Banner byte-exactness**: em-dash hazard. The test regex uses the literal em-dash; SL-3 teammate should copy-paste from plan doc, not retype.
- **Replacement-phrasing re-match (README)**: P7 lesson. Enforced by SL-1.1 post-edit regrep.
- **Nav drift on deletions**: SL-3 teammate must grep for every deletion candidate's basename in `docs/ README.md AGENTS.md` before deleting; downgrade to `banner` on hit.
- **Factual accuracy (SL-2)**: env-var semantics must come from `mcp_server/` source, not imagination. SL-2 teammate pre-edit grep is mandatory.
- **Inter-phase**: P7 and P8 are disjoint. Either may merge first. No cross-phase coordination needed.
