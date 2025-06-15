---
automation:
  suite_command: "SEMANTIC_SEARCH_ENABLED=false MCP_SKIP_PLUGIN_PREINDEX=true PYTHON_DOTENV_DISABLED=1 uv run --locked --extra dev pytest -q --no-cov tests/test_python_plugin.py tests/test_dispatcher.py tests/test_dispatcher_extension_gating.py tests/smoke/test_mcpbase_stdio_smoke.py tests/smoke/test_mcpeval_sdk_surface.py tests/test_tool_handlers_readiness.py tests/test_handler_path_sandbox.py tests/test_tool_schema_handler_parity.py"
---

# Detailed plan: correct Code-Index-MCP symbol extraction and lookup

## Task and scope

Deliver one Code-Index-MCP PR that fixes the three observed symbol-lookup failure families: omitted decorated Python declarations, unrelated partial-name results, and documentation examples selected ahead of source definitions. Include regression tests and the required rebuild documentation. This plan is intended for implementation by one executor. Manual review findings and limitations are recorded in `.dev-skills/reviews/code-index-symbol-correctness/manual-review-closeout.md`; unanimous approval was not obtained because Grok's final run failed. Planning does not perform implementation or deployment.

This is the execution plan for the Code-Index-MCP items. It replaces the execution scope of the earlier mixed-repository proposal, `plans/detailed-dev0-symbol-lookup-fixes-20261014-1523.md`, which remains historical research. PMCP's JSON corruption is tracked separately in [Consiliency/pmcp#401](https://github.com/Consiliency/pmcp/issues/401) and is not an implementation dependency. No PMCP patch or workaround belongs in this PR.

The PR completes with repository verification and an isolated installed-wheel smoke test. Updating the live dev0 runtime, rebuilding its live index, replaying its acceptance workload, publication and wider rollout are subsequent operational work.

## Research summary

The saved real-repository suite passed 192 of 207 checks; the same 15 symbol failures reproduced through native STDIO and the gateway. An independent AST inventory found all 752 undecorated public top-level declarations indexed and all 326 decorated declarations missing, out of 1,078 audited declarations. `Plugin.indexFile` skips Tree-sitter decorator wrapper nodes at both module and immediate class-body scope; `EnhancedDispatcher.lookup` accepts arbitrary substring matches and selects a single row without ordering source ahead of documents. Markdown deliberately extracts code-block symbols, so checking symbol kind alone cannot distinguish those examples from source definitions. Existing tests miss these cases because decorator coverage is skipped and several lookup tests exercise mocked search routing rather than the actual SQL lookup path.

Research base: `6b29c4a880141bcd4cfb187ec6e30d99859ba11d`. The relevant installed v1.4.1 production files match this base. The live pilot indexes the separate primary checkout at `dc5aca176a049b558d449346d88c4e92be475afd`; its historical line numbers and declaration count must not be confused with the implementation worktree.

| Observed failure | Requests | Planned correction |
| --- | --- | --- |
| Nine real definitions return `not_found` | `ArtifactRef`, `BenchmarkResult`, `CacheMetrics`, `GraphEdge`, `RuntimeSnapshot`, `SemanticWriteBlocker`, `get_search_config`, `ingest_history`, `invalidate_semantic_cache` | Extract decorated declarations. |
| Two requests return a different name | `FrozenEval` returns `FrozenEvalError`; `RepositoryReadiness` returns `RepositoryReadinessState` | Extract the missing declarations and independently reject unrelated partial matches. |
| Four requests select Markdown examples | `EnhancedDispatcher`, `IndexDiscovery`, `PluginFactory`, `SQLiteStore` | Rank source definitions ahead of document examples, with deterministic ties. |

Original evidence is under `/home/viperjuice/workspace/pilots/code-index-mcp-v1.4.1-dev0-20261014/automated-tests-20261014T071607Z/`: `REPORT.md`, `validated-results.json`, `python-declaration-inventory.json`, and `gateway-crosschecks.json`. The audit covers public top-level Python declarations, not all nested or conditional definitions.

## Changes

Nine existing files: three production modules, four test modules, and two documentation files. No new production module, database migration, dependency change or tool-schema change is needed.

### `mcp_server/plugins/python_plugin/plugin.py` — modify

- In `Plugin.indexFile`, unwrap `decorated_definition` through its `definition` field before the existing type filter, both for module children and immediate class-body methods. The current skip points are lines 157–159 and 203–205.
- Pass the inner definition node through existing extraction and persistence logic. Use the actual `class` / `def` / `async def` declaration line and definition end line, rather than the first decorator line. Preserve current signature formatting and symbol kinds.
- Support stacked decorators, decorated async functions, decorated classes, and decorated methods within both ordinary and decorated classes. Do not evaluate decorators or import the indexed source.
- Emit one symbol per declaration site. Property getters and setters remain distinct sites even though their names coincide. Preserve parent-class metadata where it is already stored; compare the shard and database's shared name/kind/location fields without adding a new metadata contract.
- Keep current extraction scope: top-level functions/classes and immediate class methods. Arbitrary nested classes/functions, variable extraction, import resolution and enriched signatures are outside this correction. Keep chunk identities and chunking unchanged.

### `mcp_server/plugins/python_plugin/plugin_semantic.py` — modify

- Apply the same static decorator unwrapping at the module and immediate class-method loops in `PythonPluginSemantic.indexFile`. The package selects this separate extractor when `SEMANTIC_SEARCH_ENABLED=true`; leaving it unchanged would retain the same bug in a supported configuration.
- Execution finding (2026-10-17): initialize this class's `_sqlite_store` from its existing constructor argument. Its base class no longer assigns that attribute; direct construction otherwise raises before static extraction. This minimal prerequisite stays in the owned file and does not enable inference.
- Preserve this class's existing signatures, shard fields, chunks and embedding behavior. Do not refactor the two extractors or add semantic features. Exercise its extraction directly with `PythonPluginSemantic(enable_semantic=False)`, so the shared regression matrix needs no inference calls or Qdrant service.

### `mcp_server/dispatcher/dispatcher_enhanced.py` — modify

- In `EnhancedDispatcher.lookup`, replace `s.name = ? OR s.name LIKE '%query%'` with literal matching. Accept an exact stored name. For an unqualified query (containing neither `.` nor `::`), also accept either a qualified stored member of kind `method`, `getter`, `setter`, or `property` whose final dot-separated component literally equals the query, or a stored name of any kind whose final `::`-separated component literally equals the query. This preserves JavaScript member aliases and C++ namespace/class-scoped definitions, including functions, classes, constructors and destructors. A query containing `.` or `::` must match the full stored name. `%`, `_`, quotes and backslashes in the query are literal data, not SQL pattern syntax; keep SQL parameterized. Use literal equality plus literal suffix/component comparison, not raw `LIKE` or `GLOB`. Exact matching remains case-sensitive; the old substring branch's case-insensitive matches are intentionally removed.
- Rank eligible candidates before taking the first result. The ordering is: source before documents; then exact stored name before a qualified alias within that tier (dot-member and `::` aliases share this alias tier); then repository-relative path, declaration start line, end line, kind and stored name. Identical observable definitions may tie. Do not use insertion order or a hard-coded production directory/name preference.
- Classify document candidates using `files.language` (including Markdown, plaintext and reStructuredText/document languages registered by this repo) and existing document metadata (`in_code_block`, document/heading/section/chunk kinds). A known programming-language file remains source even if it is located under `docs/`. Use the existing `_is_documentation_file` heuristic only when file language/provenance is missing or unknown. Markdown code examples have `kind=class` but file language `markdown`, so they rank as documents. Do not use a code block's `metadata.language` (which can be `python`) as the file language. Retain exact document-only symbols when there is no eligible source definition.
- Remove the BM25 branch that turns a matching text snippet into a definition at line 1. Continue using BM25 only as an extension hint for the existing bounded plugin fallback. Check the fallback's returned symbol against the same exact-name/dot-member/`::`-scope alias rules; a nonmatching result is a miss. Preserve existing first-result fallback order, timeout and extension gating; do not add plugin retries or change `run_gated_fallback`'s interface. A rejected first truthy result remains a miss even if a later plugin could match, and the helper's existing hit metric remains unchanged; pin this bounded behavior in the regression test.
- Preserve current output shape and location/language fields. Keep `search_code` fuzzy/content search and its separate `_symbol_route` behavior unchanged. Avoid a storage-layer or ranking-framework refactor.
- Review correction (2026-10-21, Consiliency/Code-Index-MCP#105): include Dart's existing `build_method` and `lifecycle_method` kinds in the dot-member alias allowlist, in both SQL lookup and fallback validation. The original allowlist omitted these supported method subtypes. Extend the existing dispatcher and fallback regression matrices to preserve these aliases while rejecting partial qualified names, case mismatches, and unrelated names. This corrects AC3's compatibility coverage within the existing owned files; it does not change Dart extraction or support tiers.

### `tests/test_python_plugin.py` — modify

- Parameterize the new extraction matrix over the basic `Plugin` and `PythonPluginSemantic(enable_semantic=False)` classes, importing each explicitly. Disable preindexing and semantic inference. Do not use `importorskip` to hide failure to import the semantic-capable class.
- Add active extraction cases for decorated classes/dataclasses, stacked route/Click-style decorators, decorated async functions, ordinary functions, class/static methods, and property getter/setter pairs. Include a decorated class containing an async method with stacked decorators on distinct lines. Assert exact declaration lines, kinds, spans and one record per declaration site.
- Exercise both a plugin without SQLite and the existing SQLite-backed fixture; verify persisted shared fields agree with returned symbols. Check existing parent metadata where present. Include a decorator name that cannot be imported, proving parsing does not execute the module.
- Replace or split the skipped decorator-signature test into supported declaration-presence assertions. Do not enable unrelated skipped tests that demand richer signatures or unsupported nested-definition extraction. Add method assertions to the existing class fixture, which currently contains decorated methods but only checks the classes.

### `tests/test_dispatcher.py` — modify

- Add real-SQLite lookup fixtures using `RepoContext`, `files`, and `symbols`, covering the production `EnhancedDispatcher.lookup` path rather than mocked `_symbol_route` results.
- Parameterize the four source/document collisions and insert candidates in both orders. Confirm source wins, including when source is under `docs/`, and document-only exact lookup remains available.
- Seed multiple source definitions and assert deterministic selection across insertion orders. Cover exact-name and explicit member-alias precedence, including an exact document symbol competing with an eligible source member alias.
- Exercise `FrozenEval` / `FrozenEvalError` and `RepositoryReadiness` / `RepositoryReadinessState` both with and without the exact declaration. The shorter query must miss when only the longer name exists. Add substring, case-mismatch, `%`, `_`, quote and backslash cases without broadening existing case-sensitive exact lookup.
- Preserve unqualified and fully qualified JavaScript method, getter, setter and property lookup; reject suffix fragments such as `User` matching `UserManager.addUser`. Test the declared kind allowlist and literal suffix comparison independently of parser extraction.
- Add real-SQLite C++ cases: `Widget` resolves to class `NS::Widget`, `draw` resolves to method `Widget::draw`, `Wid` misses, and `NS::Widget` resolves exactly. Cover a namespaced function and constructor/destructor kinds to pin the kind-independent `::` rule. Assert exact-name precedence over either alias form and reject partial qualified names, case mismatches and wildcard characters as patterns. These cases use the existing dispatcher test module; no C++ plugin or support-tier change is needed.

### `tests/test_dispatcher_extension_gating.py` — modify

- Keep existing BM25-only fixtures for extension-gating behavior, but use a separate full-schema fixture for definition-fabrication regression: construct `SQLiteStore(path)` first, then create/populate `bm25_content` with mention-only text and no symbols. Creating BM25 first causes `SQLiteStore._init_database` to skip its schema; the subsequent missing-symbols exception bypasses the bug and is not valid evidence.
- With no matching plugin result, assert that lookup returns `None`. During implementation, confirm this exact fixture returns a fabricated line-1 definition on the researched base (or a temporary isolated base checkout), then fails closed after the fix. Do not manufacture a baseline receipt during planning.
- Also assert that an unrelated plugin result is rejected and a matching plugin result is retained, including the declared first-truthy-result behavior.
- Retain the current no-hint, C/Python extension-hint, exception and timeout behavior. No change to the fallback helper's public/internal signature is planned.

### `tests/smoke/test_mcpbase_stdio_smoke.py` — modify

- Extend the committed temporary repository used by the official MCP SDK test with decorated class/function/async/method declarations, longer-name collision cases, and Markdown examples colliding with actual source definitions. Use simple source text that requires no runtime imports.
- After using `boot_test_server` for isolated registration/bootstrap, explicitly call the real `reindex` tool for every Python and Markdown fixture file through the first SDK session before querying. Await successful terminal completion and assert `mutation_performed=true`, `indexed_files=1` for each file, using the existing SDK task pattern in `tests/smoke/test_mcpeval_sdk_surface.py` if necessary. This must traverse `Plugin.indexFile` and `EnhancedDispatcher._persist_index_shard` with default sandboxing.
- The shared helper's line scanner must not be the writer of any asserted symbol row: production reindex must replace its rows for each asserted Python file and index the Markdown file. Do not extend that scanner, seed corrected symbol rows manually, or change `tests/fixtures/multi_repo.py`. Assert the Markdown collision candidate exists in the persisted database as well as the source candidate before the source-winning query.
- Assert the correct `symbol`, `kind`, `defined_in` and declaration `line` in both MCP `content` JSON and `structuredContent`; assert `line_start`, `line_end` and kind on the persisted `symbols` row, in the first session and again after reopening. Include decorated async declarations and `kind=method` with multi-line bodies, which the scanner cannot produce correctly. MCP `span` has its existing name-offset meaning; do not equate it with the extractor's declaration span. Assert a ready miss for the shorter absent symbol and keep text retrieval working for documentation.
- Close the first STDIO session, reopen a fresh client on the same registry and on-disk index, and repeat representative decorated and source-preference lookups without calling bootstrap, the scanner or reindex again. Keep auto-index off for this reopen. Confirm the asserted rows come from the persisted production generation, not an in-memory plugin or rebuilt fixture. Use existing session/fixture helpers and isolated registry paths. Keep semantic inference disabled and default plugin sandboxing enabled.

### `mcp_server/plugins/python_plugin/AGENTS.md` — modify

- Update only the indexing capability statements affected by this patch: decorated declarations are supported statically by both Python extractor classes at the existing module/class-method scopes, with declaration locations and existing signatures. Remove the obsolete blanket decorator limitation and stale claims that no methods are extracted. Keep unsupported nested/runtime behavior explicit.

### `docs/operations/v13-pmcp-pilot.md` — modify

- Add a corrective-upgrade note that the extractor fix requires a full lexical rebuild for each affected repository. Ordinary restart or incremental sync can retain unchanged files with missing definitions. Document the existing `repository sync --repo-id <id> --force-full` operation and preserve old generations/backups according to the existing runbook.
- Distinguish the PR's tests from later dev0 operational acceptance. Preserve historical release/provider receipts and allowances. Link Consiliency/pmcp#401 as a separate gateway limitation if describing gateway validation; do not make resolving it a condition for completing this Code-Index-MCP PR.

## Protocol and documentation contract

The existing `mcp_server/cli/stdio_runner.py:334` contract states: “Ready misses return not_found with readiness metadata.” The implementation at `mcp_server/cli/tool_handlers.py:434–440` constructs `"result": "not_found"` and adds readiness. Preserve these exact terms and existing `index_unavailable`, `safe_fallback=native_search`, and `path_outside_allowed_roots` behavior. No new protocol vocabulary or response fields are introduced.

The two documentation changes above are sufficient. Support tiers, semantic inference/features, dependency pins, allowlists, authentication, schema and chunk identity remain outside this change. The semantic-capable class receives only the same static extraction bug fix; the SDK smoke and pilot remain lexical. Full reindexing is an operator requirement for the corrective upgrade; automatic extractor-version invalidation is not part of this bounded PR.

## Dependencies and order

1. Start implementation from the researched base or rebase the isolated implementation branch onto current upstream main after checking for intervening changes. Keep the primary pilot checkout and its index untouched. Carry only this scoped plan and its manifest entry as planning inputs; the older mixed-scope proposal is not an implementation input.
2. Add the relevant regression cases and implement the Python extraction correction and lookup correction. These production changes can be developed independently but belong in the same PR because the decorated-name collisions exercise both.
3. Finish SDK/persistence coverage and the two documentation updates, then run the focused suite once for the combined changes. Diagnose any failures before broadening verification.
4. Run the protected pre-PR agent gate and baseline-aware format/type checks. Reuse its successful isolated wheel/STDIO smoke receipt for V3; do not repeat that build without a change or failure that justifies it. Record exact commands, exit statuses, commit/source identity and artifact hash in the execution handoff. Do not claim the installed smoke proves the later real-repository audit.
5. Hand off the completed, verified Code-Index-MCP patch for one PR. Live dev0 deployment and release operations are separate work after review; they are not part of this plan's completion criteria.

## Verification commands

These commands are prescribed for implementation; none are run while planning. Run from the corrective implementation worktree, with its own Python 3.12 virtual environment. Tests use synthetic/local fixtures; never invoke the previously consumed live-provider acceptance workflow.

**V0 — locked environment:**

```bash
uv sync --locked --python 3.12 --extra dev
```

Before the required agent gate, check `make agent-doctor` and the pinned BAML 0.20.1 regeneration prerequisite. Use the toolchain version/checksum and `BAML_TOOLCHAIN` setup declared in `.github/workflows/ci-cd-pipeline.yml`; do not turn off `BAML_REQUIRE_REGEN` or skip a gate when the toolchain is absent. Resolve missing local prerequisites before reporting acceptance.

**V1 — focused regressions and existing safety/contract tests** (also the effective `automation.suite_command`; `--no-cov` avoids applying the whole-repository coverage threshold to this subset):

```bash
SEMANTIC_SEARCH_ENABLED=false MCP_SKIP_PLUGIN_PREINDEX=true PYTHON_DOTENV_DISABLED=1 uv run --locked --extra dev pytest -q --no-cov tests/test_python_plugin.py tests/test_dispatcher.py tests/test_dispatcher_extension_gating.py tests/smoke/test_mcpbase_stdio_smoke.py tests/smoke/test_mcpeval_sdk_surface.py tests/test_tool_handlers_readiness.py tests/test_handler_path_sandbox.py tests/test_tool_schema_handler_parity.py
```

**V2 — required protected CI gate and baseline-aware lint/type checks**, aligned with `docs/status/localci-validation-contract.md`:

```bash
SEMANTIC_SEARCH_ENABLED=false MCP_SKIP_PLUGIN_PREINDEX=true PYTHON_DOTENV_DISABLED=1 uv run --locked --extra dev make agent-gate alpha-format-lint alpha-mypy-ratchet UV_RUN='UV_LINK_MODE=copy uv run --locked'
```

This runs the substantive protected suite, including BAML regeneration, protocol/schema checks, installed-wheel smoke and production-matrix tests. The format/lint target uses the repository's declared pylint threshold, and the mypy target enforces its recorded baseline rather than demanding zero legacy errors. Do not edit either threshold/baseline in this PR. `make test-all` is optional additional coverage, not a substitute for `agent-gate`; its normal discovery excludes integration/slow tests.

Any unrelated failure must be distinguished using baseline evidence and recorded; do not silently remove checks or expand this patch into unrelated cleanup. A required gate failure remains unresolved: documentation of a pre-existing failure alone does not satisfy AC7. Record an explicit acceptance amendment with rationale if the owner later changes a requirement; do not label it a pass.

**V3 — isolated installed-wheel/STDIO check**, using the existing build/install probe and a temporary runtime outside the checkout. V2's `agent-gate` already invokes this smoke: a successful receipt on the same unchanged candidate satisfies V3. Run the following separately only for isolated diagnosis or if the candidate changed after that receipt:

```bash
SEMANTIC_SEARCH_ENABLED=false PYTHON_DOTENV_DISABLED=1 uv run --locked --extra dev python scripts/release_smoke.py --wheel --stdio
```

**V4 — scope and documentation review:**

```bash
git diff --check
git diff --stat
git diff -- mcp_server/plugins/python_plugin/AGENTS.md docs/operations/v13-pmcp-pilot.md
```

V4's content review is human/agent assessment, not an automated semantic test. The execution handoff must record the reviewed file paths, implementation commit/diff identity and confirmation that the rebuild requirement and extraction limits are documented. Record any acceptance amendment explicitly with its reason and evidence; old pilot receipts are research, not candidate acceptance proof.

## Acceptance criteria

- [ ] **AC1 — V1:** Both Python extractor classes index decorated top-level classes, functions, async functions and immediate methods with correct declaration locations; stacked decorators and property getter/setter sites are covered without executing source or duplicating sites.
- [ ] **AC2 — V1:** Returned shards and SQLite persistence agree on names, kinds and locations. SDK assertions read rows written by production reindex through the extractor and `_persist_index_shard`, including decorated async/method and Markdown candidates; those rows survive a fresh server session without reseeding/reindexing.
- [ ] **AC3 — V1:** Exact/explicit-qualified-alias matching preserves dot-member and C++ `::`-scoped lookups while rejecting unrelated partial names and literal pattern-character traps; both shorter-name collision regressions pass independently of extractor behavior.
- [ ] **AC4 — V1:** All four source/document collision regressions prefer source in both insertion orders, multiple source definitions have deterministic selection, and document-only exact symbols remain discoverable.
- [ ] **AC5 — V1:** The full-schema BM25 regression reaches the old fabrication branch on the base and rejects mentions after the fix; mismatched plugin results cannot be returned as definitions; existing extension/timeout behavior, readiness refusal, allowlist checks and tool-schema parity remain green.
- [ ] **AC6 — V1 and V3:** Official SDK text and structured responses agree on the corrected fixture definitions, and the newly built installed wheel passes the existing STDIO smoke.
- [ ] **AC7 — V2:** The required `agent-gate`, `alpha-format-lint` and `alpha-mypy-ratchet` pass on the candidate. Unresolved baseline failures are recorded as blockers, not acceptance passes.
- [ ] **AC8 — V4 and execution handoff:** Only the bounded source/test/documentation scope is changed; static decorator support and the mandatory full-rebuild upgrade step are documented. No live pilot mutation is required or represented as completed by these checks.

## Subsequent dev0 operational acceptance — outside this implementation plan

After the PR is reviewed and a corrective candidate is selected, install that candidate in the existing pilot, perform a full lexical rebuild, and repeat the saved 207-query suite and 38 gateway crosschecks. Independently repeat the AST declaration audit; for the unchanged original corpus the target is all 1,078 public top-level declarations, including the 326 previously missing decorated declarations. If the corpus changes, regenerate the AST expectations and record the change rather than forcing the historical count.

Capture fresh native/gateway results, source restoration, readiness recovery, restart and resource evidence, then complete the agreed day of normal dev0 use before any wider rollout. Track PMCP JSON integrity against Consiliency/pmcp#401 separately; use direct STDIO to assess our retrieval correctness while that gateway issue remains open, without claiming the entire gateway path is fixed.

## Planning provenance

Prepared in Default mode under `codex-plan-detailed`; no implementation, tests, builds, commits or deployment occur during this planning turn. The existing planning worktree is used to preserve the live checkout's cleanliness. This plan's starting status and retained prior artifacts are recorded in the new repo-local handoff; the earlier proposal and its historical evidence remain intact.
