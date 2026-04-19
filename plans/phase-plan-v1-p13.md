# P13: Reindex Durability + Artifact Automation

## Context

P12 merged: per-repo indexing lock (`IndexingLockRegistry`), artifact-freshness verdict (`verify_artifact_freshness` + `FreshnessVerdict`), hot-path histograms (`dispatcher_lookup_histogram`, `dispatcher_search_histogram` on `PrometheusExporter`), `/ready` + `/liveness` probes, and branch-drift loud-path with `enqueue_full_rescan`. P13 replaces happy-path indexing code with durable flows: checkpointed reindex resume, atomic Qdrant+SQLite coupling, TOCTOU-safe dispatch, direct post-reindex publish (killing the human-cron dependency), and a typed exception hierarchy with Prometheus error-counter.

What exists today:
- `mcp_server/indexing/incremental_indexer.py` — `IncrementalIndexer.update_from_changes(changes)` at L121-171 is the single reindex entry point. Processes deletions → renames → additions/modifications linearly, no resume state. Key inner methods: `_cleanup_stale_vectors` L106-119, `_remove_file` L189-221, `_move_file` L223-261 (rename handler; computes `content_hash` at L241 but does NOT couple vector cleanup with the SQLite path update), `_index_file` L263-309. Repo_id derived internally at `_get_repository_id()` L371-392; `lock_registry` NOT yet called from this file.
- `mcp_server/indexing/lock_registry.py` — P12's `IndexingLockRegistry.acquire(repo_id)` reentrant RLock, singleton at module-level.
- `mcp_server/storage/sqlite_store.py` — `move_file(old, new, repo_id, content_hash)` at L2119-2137; `remove_file` at L2079-2117; `get_semantic_point_ids` L1123-1141; `delete_semantic_point_mappings` L1143-1158; `upsert_semantic_point` L1098-1121. WAL mode enabled. **No transaction scope beyond per-call `_get_connection()` context-manager; no existing rollback pattern.**
- `mcp_server/utils/semantic_indexer.py` — `SemanticIndexer.delete_stale_vectors()` at L2031-2059 is the Qdrant delete primitive.
- `mcp_server/dispatcher/dispatcher_enhanced.py::index_file` at L1614-1680 — reads file content, calls `_get_file_hash()` helper (L615-617) and `_should_reindex()` (L619-632), then invokes plugins. Returns `None`. No `IndexResult` type exists.
- `mcp_server/watcher_multi_repo.py:142-164` — observes change event, calls `dispatcher.index_file(ctx, path)` with path only; **no file-hash carried across the watcher→dispatcher boundary today.** SL-2 of P12 added `with lock_registry.acquire(ctx.repo_id):` around dispatcher calls in this block.
- `mcp_server/artifacts/artifact_upload.py` — `IndexArtifactUploader` class (L26-296). `compress_indexes` L60-89; `_calculate_checksum` L142-148; `create_metadata` L98-139; `upload_direct` L244-296 (uses `gh release upload --clobber` against hardcoded tag `"index-latest"` at L256, L286). No commit-SHA-keyed releases; the "latest" pointer is the asset overwrite itself — two concurrent uploads at different commits race on `--clobber`.
- `mcp_server/artifacts/freshness.py` — P12 module, `verify_artifact_freshness(meta: dict, head_commit: str, max_age_days: int) -> FreshnessVerdict`. No `ArtifactMetadata` type; metadata is a plain dict with `commit` + `timestamp`.
- `.github/workflows/index-artifact-management.yml` — `workflow_dispatch` trigger exists (L4) with validate/promote/cleanup/list actions; cron at L26 (`15 3 * * *` daily) is the scheduler. P13 SL-4 replaces the cron dependency with a runtime-issued `workflow_dispatch`.
- `mcp_server/metrics/prometheus_exporter.py` — P12 SL-4 establishes the counter/histogram registration pattern (lines ~255-293 for the renamed `mcp_dispatcher_symbol_lookup_duration_seconds` + `mcp_dispatcher_search_duration_seconds` histograms; attribute names on the exporter preserved as `dispatcher_lookup_histogram`, `dispatcher_search_histogram` per the execute-phase handoff's Key Decision 1). An instance-level `errors` Counter already exists (~L255-260) with labels `["error_type", "component"]` — P13 SL-5 adds a parallel `errors_by_type` Counter with `["module", "exception"]` labels rather than retrofitting the existing one (different cardinality contract).
- `mcp_server/core/errors.py` — **exception module already lives at `core/errors.py`** (not `mcp_server/errors/` as the spec anticipated). Existing classes: `MCPError` base, `PluginError`, `IndexError`, `ConfigError`, `DocumentProcessingError`. **Spec architectural deviation: reuse `mcp_server/core/errors.py` rather than creating `mcp_server/errors/__init__.py`.** SL-5 adds `IndexingError` (as alias or rename target for existing `IndexError`) and `ArtifactError`, plus `record_handled_error(module, exception)` helper. Base class name is `MCPError` (existing) — per-spec `McpError` casing is a spec typo; use `MCPError` and record the deviation.

What constrains the design:
- **Single-writer file, non-overlapping ranges** — `incremental_indexer.py`: SL-1 owns the resume entry points (`update_from_changes` L121-171, `_index_file` L263-309); SL-2 owns the three handlers `_cleanup_stale_vectors` L106-119, `_remove_file` L189-221, `_move_file` L223-261. Zero line overlap. Wave order: SL-1 first, SL-2 after.
- **SL-5 cross-cutting** — touches 15 bare-`except`-clauses across `dispatcher/**` and 11 across `artifacts/**` (see Execution Notes for the full list). To avoid collision with SL-3/SL-4's method edits, SL-3 and SL-4 are constrained to append **new** methods/helpers rather than mutate existing method bodies. With that constraint, SL-5 can run in a final wave against a merged base without fighting peer lanes.
- **`HealthView` circular-import precedent from P12 SL-1 applies** — new `ArtifactPublisher` in `mcp_server/artifacts/publisher.py` must NOT import from `gateway.py` or `watcher_multi_repo.py`. Accept dependencies as constructor args.
- **`bypass_branch_guard` on `enqueue_full_rescan`** (P12 handoff open item) — P13 does NOT consume this parameter. Record in Execution Notes as internal-only; forbid downstream callers outside `watcher_multi_repo` from passing it.

What this phase does NOT change:
- No plugin-level error taxonomy (deferred per spec Non-goals).
- No retention-policy change (lives in user runbook).
- No artifact signing (deferred to P15).
- No changes to `artifact_download.py` call graph (P12 SL-5 already owns download path; SL-5's except-clause refactor is the only touch here).
- No behavior change to the existing `dispatcher.index_file` — SL-3 introduces a parallel `index_file_guarded` method; the caller (watcher) chooses the guarded variant. Migration of other callers is not in scope.

## Interface Freeze Gates

- [ ] **IF-0-P13-1** — `mcp_server/indexing/checkpoint.py` (new). JSON schema for `.reindex-state`:
  ```python
  from dataclasses import dataclass, field
  from typing import List

  REINDEX_STATE_VERSION: int = 1   # bump only on shape-break; new fields additive

  @dataclass
  class ReindexCheckpoint:
      repo_id: str
      started_at: str            # ISO-8601 UTC
      last_completed_path: str   # relative path; "" if none yet
      remaining_paths: List[str] # relative paths still to process
      errors: List[dict] = field(default_factory=list)  # [{"path": ..., "error": ...}]
      schema_version: int = REINDEX_STATE_VERSION

  def save(ckpt: ReindexCheckpoint, repo_root: Path) -> None: ...  # writes <repo_root>/.reindex-state atomically (tmp+rename)
  def load(repo_root: Path) -> ReindexCheckpoint | None: ...       # returns None if absent or schema mismatch
  def clear(repo_root: Path) -> None: ...                          # unlink .reindex-state
  ```
  Frozen at end of SL-1 task `SL-1.1`.

- [ ] **IF-0-P13-2** — `mcp_server/storage/two_phase.py` (new):
  ```python
  from typing import Callable, TypeVar
  T = TypeVar("T")

  class TwoPhaseCommitError(MCPError): ...

  def two_phase_commit(
      primary_op: Callable[[], T],
      shadow_op: Callable[[T], None],
      rollback: Callable[[T], None],
  ) -> T:
      """
      Invariant: after return, either BOTH primary and shadow succeeded,
      or NEITHER has visible side effects.
      primary_op runs first; its result is passed to shadow_op and rollback.
      If shadow_op raises, rollback(primary_result) is called and the
      shadow exception is re-raised wrapped in TwoPhaseCommitError.
      If primary_op raises, shadow_op is never invoked and the exception
      propagates unchanged.
      """
  ```
  Frozen at end of SL-2 task `SL-2.1`.

- [ ] **IF-0-P13-3** — `mcp_server/dispatcher/dispatcher_enhanced.py` — new method + new return type:
  ```python
  # New module-level type, defined alongside existing dataclasses near L615:
  from dataclasses import dataclass
  from enum import Enum

  class IndexResultStatus(str, Enum):
      INDEXED = "indexed"
      SKIPPED_UNCHANGED = "skipped_unchanged"
      SKIPPED_TOCTOU = "skipped_toctou"
      ERROR = "error"

  @dataclass
  class IndexResult:
      status: IndexResultStatus
      path: Path
      observed_hash: str | None
      actual_hash: str | None
      error: str | None = None

  class EnhancedDispatcher:
      def index_file_guarded(
          self, ctx: RepoContext, path: Path, expected_hash: str
      ) -> IndexResult: ...
  ```
  Semantics: recomputes file hash immediately before invoking any plugin write. If the recomputed hash differs from `expected_hash`, returns `IndexResult(status=SKIPPED_TOCTOU, ...)` and emits a structured log event `dispatcher.index.toctou_skipped`. Frozen at end of SL-3 task `SL-3.1`.

- [ ] **IF-0-P13-4** — `mcp_server/artifacts/publisher.py` (new):
  ```python
  from dataclasses import dataclass

  @dataclass(frozen=True)
  class ArtifactRef:
      repo_id: str
      commit: str
      tag: str            # e.g., "index-<short-sha>"
      release_url: str
      is_latest: bool

  class ArtifactPublisher:
      def __init__(self, uploader: IndexArtifactUploader, *, gh_cmd: str = "gh") -> None: ...
      def publish_on_reindex(self, repo_id: str, commit: str) -> ArtifactRef:
          """
          Idempotent: calling twice with same (repo_id, commit) returns the same ArtifactRef.
          Atomic 'latest' election: writes a commit-SHA-keyed release (tag='index-<short-sha>'),
          then uses `gh release edit index-latest --target <sha>` (or equivalent PointerRef update)
          as the single atomic pointer move. Losers of a concurrent race still have
          their SHA-keyed release reachable.
          """
  ```
  Frozen at end of SL-4 task `SL-4.1`.

- [ ] **IF-0-P13-5** — `mcp_server/core/errors.py` (extended; **not a new `mcp_server/errors/` package**):
  ```python
  # Existing (unchanged): MCPError, PluginError, IndexError, ConfigError, DocumentProcessingError
  # New subclasses:
  class IndexingError(MCPError): ...   # NOT the existing IndexError (which takes file_path);
                                       # IndexingError is the generic indexing subclass per spec.
                                       # IndexError retains its current signature.
  class ArtifactError(MCPError): ...

  # New helper — lives at mcp_server/core/errors.py module scope:
  def record_handled_error(module: str, exception: BaseException) -> None:
      """Increment mcp_errors_by_type_total{module, exception=type(exception).__name__}.
      Must never raise — metric surface failures are swallowed."""
  ```
  Plus, on `PrometheusExporter`:
  ```python
  self.errors_by_type: Counter | None
  # Name: "mcp_errors_by_type_total"; labels: ["module", "exception"]
  # None when prometheus_client unavailable; register in same block as P12 SL-4 histograms.
  ```
  Frozen at end of SL-5 task `SL-5.1`.

## Lane Index & Dependencies

```
SL-1 — checkpoint-resume
  Depends on: (none)
  Blocks: SL-2
  Parallel-safe: yes

SL-2 — two-phase-commit
  Depends on: SL-1
  Blocks: (none)
  Parallel-safe: yes

SL-3 — toctou-dispatch
  Depends on: (none)
  Blocks: SL-5
  Parallel-safe: yes

SL-4 — direct-publish
  Depends on: (none)
  Blocks: SL-5
  Parallel-safe: yes

SL-5 — structured-errors
  Depends on: SL-1, SL-2, SL-3, SL-4
  Blocks: (none)
  Parallel-safe: no
```

(Terminal `SL-docs` lane depends on SL-1..SL-5; see `### SL-docs` in Lanes.)

**Wave plan** (`execute-phase` default `MAX_PARALLEL_LANES=2`, four waves):

| Wave | Lanes | Rationale |
|---|---|---|
| 1 | SL-1, SL-3 | Disjoint files (SL-1: indexing; SL-3: dispatcher). Both new-file-creating with minimal existing-code edits. |
| 2 | SL-2, SL-4 | SL-2 after SL-1 (same file, non-overlapping ranges). SL-4 independent, new module. |
| 3 | SL-5 | After all impl lanes land; refactors bare-except across files SL-3 and SL-4 edited. |
| 4 | SL-docs | Terminal doc-sweep per skill contract. |

## Lanes

### SL-1 — checkpoint-resume

- **Scope**: Add `.reindex-state` checkpoint schema + save/load helpers; wrap `update_from_changes` and `_index_file` with checkpoint-aware resume loop. Wrap the resume in `lock_registry.acquire(repo_id)` (P12 carryover).
- **Owned files**: `mcp_server/indexing/checkpoint.py` (new), `mcp_server/indexing/__init__.py` (extend `__all__` to export `ReindexCheckpoint`, `save`, `load`, `clear`), `mcp_server/indexing/incremental_indexer.py` **lines 121-171 (`update_from_changes`) and 263-309 (`_index_file`) only** (no edits to L106-119, L189-221, L223-261 — owned by SL-2), `tests/test_reindex_resume.py` (new).
- **Interfaces provided**: IF-0-P13-1.
- **Interfaces consumed**: `lock_registry.acquire` (pre-existing; P12 IF-0-P12-2).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_reindex_resume.py` | `ReindexCheckpoint` round-trips via `save`+`load` preserving all 6 fields; `load` returns `None` for missing file and for schema_version mismatch; `save` is atomic (tmp+rename); simulated 1000-file reindex where file #500 raises leaves a checkpoint with `last_completed_path == paths[499]` and `remaining_paths == paths[499:]`; re-invoking `update_from_changes` starts at file #500 and skips 1-499 (assert by spying plugin `indexFile` call count); resume wraps `lock_registry.acquire(repo_id)` (assert via `IndexingLockRegistry` spy) | `pytest tests/test_reindex_resume.py -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/indexing/checkpoint.py`, `mcp_server/indexing/__init__.py` | — | — |
| SL-1.3 | impl | SL-1.2 | `mcp_server/indexing/incremental_indexer.py` (L121-171, L263-309 only) | — | — |
| SL-1.4 | verify | SL-1.3 | all SL-1 files | all SL-1 tests + indexer regression | `pytest tests/test_reindex_resume.py tests/test_incremental_indexer.py tests/test_indexing_lock.py -v` |

### SL-2 — two-phase-commit

- **Scope**: Add `two_phase_commit` primitive; rewrite `_cleanup_stale_vectors`, `_remove_file`, `_move_file` to couple Qdrant vector ops with their corresponding SQLite ops through the primitive. Rename handler becomes atomic (Qdrant delete + SQLite `move_file` are both-or-neither).
- **Owned files**: `mcp_server/storage/two_phase.py` (new), `mcp_server/indexing/incremental_indexer.py` **lines 106-119 (`_cleanup_stale_vectors`), 189-221 (`_remove_file`), 223-261 (`_move_file`) only** (no edits to L121-171 or L263-309 — owned by SL-1), `tests/test_two_phase_commit.py` (new).
- **Interfaces provided**: IF-0-P13-2.
- **Interfaces consumed**: `SQLiteStore.move_file` (pre-existing), `SQLiteStore.remove_file` (pre-existing), `SemanticIndexer.delete_stale_vectors` (pre-existing).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_two_phase_commit.py` | `two_phase_commit(primary, shadow, rollback)` with both-ok: returns primary's return; `shadow_op` raises → `rollback(primary_result)` invoked exactly once, exception re-raised wrapped as `TwoPhaseCommitError`; `primary_op` raises → `shadow_op` never invoked, `rollback` never invoked, original exception propagates; rename of a file with semantic vectors — force Qdrant-delete to fail, assert SQLite `files.relative_path` is NOT updated (rollback); reverse: force SQLite `move_file` to fail, assert Qdrant vectors are NOT deleted | `pytest tests/test_two_phase_commit.py -v` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/storage/two_phase.py` | — | — |
| SL-2.3 | impl | SL-2.2 | `mcp_server/indexing/incremental_indexer.py` (L106-119, L189-221, L223-261 only) | — | — |
| SL-2.4 | verify | SL-2.3 | all SL-2 files | all SL-2 tests + indexer regression + SL-1 resume regression | `pytest tests/test_two_phase_commit.py tests/test_incremental_indexer.py tests/test_reindex_resume.py -v` |

### SL-3 — toctou-dispatch

- **Scope**: Add `index_file_guarded(ctx, path, expected_hash) -> IndexResult` method on `EnhancedDispatcher` and `IndexResult` + `IndexResultStatus` types. Update watcher call site to pass observed hash. Do NOT modify the existing `index_file` body.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py` **additions only** — (i) new `IndexResult`/`IndexResultStatus` types near L615 (appended to existing dataclass block), (ii) new `index_file_guarded` method appended **after** the existing `index_file` method (i.e., new code after L1680, no edit to L1614-1680 body), `mcp_server/watcher_multi_repo.py` **lines 142-164 only** (compute observed hash immediately before the dispatcher call, switch the call from `index_file` to `index_file_guarded`), `tests/test_dispatcher_toctou.py` (new).
- **Interfaces provided**: IF-0-P13-3.
- **Interfaces consumed**: `_get_file_hash` (pre-existing, L615-617); `lock_registry.acquire` (pre-existing; P12 IF-0-P12-2, carried over in the watcher block).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_dispatcher_toctou.py` | `index_file_guarded` with matching hash returns `IndexResult(status=INDEXED)`; with mismatched hash returns `IndexResult(status=SKIPPED_TOCTOU)` and emits a `dispatcher.index.toctou_skipped` log event with `{path, observed, actual}` fields; concurrent-writer scenario (thread A stats+hashes file; thread B rewrites file; thread A calls `index_file_guarded`) yields `SKIPPED_TOCTOU` and plugin `indexFile` is NEVER invoked (assert via plugin spy); watcher integration test — modifying a file under watch triggers `index_file_guarded` with the observed hash (assert via dispatcher spy) | `pytest tests/test_dispatcher_toctou.py -v` |
| SL-3.2 | impl | SL-3.1 | `mcp_server/dispatcher/dispatcher_enhanced.py` (type additions near L615 + new method after L1680 only) | — | — |
| SL-3.3 | impl | SL-3.2 | `mcp_server/watcher_multi_repo.py` (L142-164 only) | — | — |
| SL-3.4 | verify | SL-3.3 | all SL-3 files | all SL-3 tests + watcher + existing dispatcher tests | `pytest tests/test_dispatcher_toctou.py tests/test_watcher_multi_repo.py tests/test_dispatcher.py tests/test_hot_path_histograms.py -v` |

### SL-4 — direct-publish

- **Scope**: New `ArtifactPublisher` class with `publish_on_reindex(repo_id, commit) -> ArtifactRef`. Commit-SHA-keyed release tags (`index-<short-sha>`); atomic `index-latest` pointer via `gh release edit --target`. Replace `index-artifact-management.yml` cron with on-demand `workflow_dispatch` input for post-reindex publishes. Hook the publisher into the watcher's full-reindex-complete path.
- **Owned files**: `mcp_server/artifacts/publisher.py` (new), `mcp_server/artifacts/__init__.py` (extend `__all__`), `mcp_server/artifacts/artifact_upload.py` **append-only** — `ArtifactMetadata` namedtuple + `publish_on_reindex` invoked from new class; **no edits to L60-240** (existing `compress_indexes`/`_calculate_checksum`/`create_metadata` bodies, which SL-5 will refactor), `.github/workflows/index-artifact-management.yml` (replace cron trigger — keep the `workflow_dispatch` block; remove or comment the `schedule:` at L26; add a `publish_on_reindex` input to the existing `workflow_dispatch` inputs), `mcp_server/watcher_multi_repo.py` **append-only** — add one post-reindex-done hook on the watcher's completion path that calls `ArtifactPublisher.publish_on_reindex` via injected callback (do NOT re-enter the L142-164 SL-3 zone), `tests/test_artifact_publish_race.py` (new).
- **Interfaces provided**: IF-0-P13-4.
- **Interfaces consumed**: `verify_artifact_freshness` (pre-existing; P12 IF-0-P12-5), `FreshnessVerdict` (pre-existing; P12 IF-0-P12-5). Consumed optionally as a sanity check before moving the `index-latest` pointer.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_artifact_publish_race.py` | `publish_on_reindex(repo_id, commit)` is idempotent (second call with same args returns equal `ArtifactRef`); two concurrent calls at commits A and B each produce their own SHA-keyed release; only one wins `index-latest` (assert via `gh release edit` call-order spy); losing side's `ArtifactRef.is_latest == False` but its release URL is still reachable; publisher survives `gh` exit-code non-zero by wrapping `ArtifactError`; workflow file's cron schedule removed, `workflow_dispatch` inputs extended with `publish_on_reindex`; **publish latency test**: with `gh` mocked to zero-delay, `publish_on_reindex` completes in < 30s wall-clock for a 10 MB synthetic artifact (budgets 60s under real-network for the spec's <2-min bar) | `pytest tests/test_artifact_publish_race.py -v` |
| SL-4.2 | impl | SL-4.1 | `mcp_server/artifacts/publisher.py`, `mcp_server/artifacts/__init__.py` | — | — |
| SL-4.3 | impl | SL-4.2 | `mcp_server/artifacts/artifact_upload.py` (append only, no L60-240 edits), `mcp_server/watcher_multi_repo.py` (new post-reindex hook, no L142-164 touches), `.github/workflows/index-artifact-management.yml` | — | — |
| SL-4.4 | verify | SL-4.3 | all SL-4 files | all SL-4 tests + artifact regression | `pytest tests/test_artifact_publish_race.py tests/test_artifact_upload.py tests/test_artifact_freshness.py tests/test_artifact_download.py -v` |

### SL-5 — structured-errors

- **Scope**: Extend `mcp_server/core/errors.py` with `IndexingError`, `ArtifactError`, `record_handled_error(module, exception)`. Register `errors_by_type` Counter on `PrometheusExporter` mirroring P12 SL-4's pattern. Refactor every bare `except:`, `except Exception:`, and `except BaseException:` in `mcp_server/dispatcher/**` and `mcp_server/artifacts/**` to a typed catch + `record_handled_error(__name__, exc)` call. **Scope strictly limited to `except` keyword replacements** — no structural changes to control flow.
- **Owned files**: `mcp_server/core/errors.py` (extend), `mcp_server/metrics/prometheus_exporter.py` **additive only** (one new Counter registration, mirroring P12 SL-4's block near L255-293), `mcp_server/dispatcher/dispatcher_enhanced.py` **except-clauses only at L355, L790, L794, L822, L1007, L1211, L1533, L1537, L1611, L1697**, `mcp_server/dispatcher/simple_dispatcher.py` **except-clause only at L182**, `mcp_server/dispatcher/fallback.py` **except-clauses only at L57, L63**, `mcp_server/dispatcher/cross_repo_coordinator.py` **except-clauses only at L649, L681**, `mcp_server/artifacts/artifact_upload.py` **except-clauses only at L116, L147, L207, L226** (none overlap with SL-4's append-only edits), `mcp_server/artifacts/artifact_download.py` **except-clauses only at L187, L229, L245, L275, L418, L442**, `mcp_server/artifacts/multi_repo_artifact_coordinator.py` **except-clause only at L62**, `tests/test_structured_errors.py` (new).
- **Interfaces provided**: IF-0-P13-5.
- **Interfaces consumed**: `MCPError` (pre-existing, `mcp_server/core/errors.py`); P12 SL-4 counter-registration pattern (pre-existing).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-5.1 | test | — | `tests/test_structured_errors.py` | `IndexingError` and `ArtifactError` subclass `MCPError`; `record_handled_error("mcp_server.dispatcher.x", OSError("x"))` calls `errors_by_type.labels(module=..., exception="OSError").inc()` exactly once; when `prometheus_client` is unavailable `errors_by_type` attribute is `None` and `record_handled_error` is a no-op that does NOT raise; counter `_count` increments by exactly 1 per handled exception; a parameterised test loops every file in the SL-5 owned-list and asserts that file contains `record_handled_error(` references (proves refactor landed — paired with a raising-unit-test for a sampled call-site per file rather than raw grep-only) | `pytest tests/test_structured_errors.py -v` |
| SL-5.2 | impl | SL-5.1 | `mcp_server/core/errors.py`, `mcp_server/metrics/prometheus_exporter.py` | — | — |
| SL-5.3 | impl | SL-5.2 | all 26 except-clause sites listed above (dispatcher + artifacts) | — | — |
| SL-5.4 | verify | SL-5.3 | all SL-5 files | all SL-5 tests + full dispatcher + artifact test suites (regression proves no error-path semantics changed) | `pytest tests/test_structured_errors.py tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_enhanced_dispatcher.py tests/integration/test_dispatcher_fallback_metrics.py tests/test_artifact_upload.py tests/test_artifact_download.py tests/test_artifact_freshness.py -v` |

### SL-docs — Documentation & spec reconciliation

- **Scope**: Refresh docs catalog, update cross-cutting docs touched or invalidated by P13's impl lanes, and append post-execution amendments to phase specs whose interface freezes turned out wrong.
- **Owned files** (authoritative list: `.claude/docs-catalog.json`; minimum set below):
  - Root: `README.md`, `CHANGELOG.md`, `AGENTS.md`, `CLAUDE.md`
  - `docs/**`, `docs/operations/user-action-runbook.md` (P13's GitHub-token-scope prerequisite per the execute-phase handoff)
  - `.claude/docs-catalog.json`
  - `specs/phase-plans-v1.md` (current-phase + any prior-phase post-execution amendments)
  - `plans/phase-plan-v1-p13.md` (this phase's own plan, append-only amendments)
- **Interfaces provided**: (none)
- **Interfaces consumed**: (none)
- **Parallel-safe**: no (terminal)
- **Depends on**: SL-1, SL-2, SL-3, SL-4, SL-5

**Tasks**:

| Task ID | Type | Depends on | Files in scope | Action |
|---|---|---|---|---|
| SL-docs.1 | docs | — | `.claude/docs-catalog.json` | Rescan: `python3 "$(git rev-parse --show-toplevel)/.claude/skills/_shared/scaffold_docs_catalog.py" --rescan`. Pick up new doc files; preserve `touched_by_phases` history. |
| SL-docs.2 | docs | SL-docs.1 | per catalog | For each catalog file, decide if P13's work changes it; if yes, update and append `p13` to `touched_by_phases`. Record any intentional skips in the commit message. Ensure `docs/operations/user-action-runbook.md` documents the GitHub-token scope requirement (`actions:write`, `contents:write`) and the new `publish_on_reindex` workflow input. |
| SL-docs.3 | docs | SL-docs.2 | `specs/phase-plans-v1.md`, prior plans | Append `### Post-execution amendments` subsections to any phase whose interface freeze was empirically wrong this run. Record: (a) `MCPError` name (spec said `McpError`); (b) `mcp_server/core/errors.py` reused instead of new `mcp_server/errors/` package; (c) `IndexingError` added alongside the pre-existing `IndexError` (not a rename); (d) any freeze-time deviation from IF-0-P13-1..5 surfaced during execute-phase. |
| SL-docs.4 | verify | SL-docs.3 | — | Run repo doc linters (`markdownlint`, `prettier --check` if configured). No-op if none. |

## Execution Notes

- **Single-writer file — `mcp_server/indexing/incremental_indexer.py`**:
  - **SL-1 owns L121-171 and L263-309** (`update_from_changes`, `_index_file`).
  - **SL-2 owns L106-119, L189-221, L223-261** (`_cleanup_stale_vectors`, `_remove_file`, `_move_file`).
  - Ranges disjoint by construction (verified against source). SL-2 is serialized after SL-1 merge in Wave 2 to avoid base-stale add/add conflicts.
- **Single-writer file — `mcp_server/dispatcher/dispatcher_enhanced.py`**:
  - **SL-3 appends only** — new `IndexResult`/`IndexResultStatus` types near L615 (in the existing dataclass block, additive) and new `index_file_guarded` method **after** L1680.
  - **SL-5 touches `except` keywords only** at L355, L790, L794, L822, L1007, L1211, L1533, L1537, L1611, L1697. None fall within the SL-3 L1614-1680 `index_file` body or within the new-method body SL-3 appends. Note the L1611 and L1697 excepts bracket the `index_file` body — SL-5 must preserve those; SL-3 must NOT re-indent or extend that body beyond L1680.
  - SL-3 must NOT touch any `except` clause. SL-5 must NOT modify any method body beyond the `except` keyword.
- **Single-writer file — `mcp_server/artifacts/artifact_upload.py`**:
  - **SL-4 append-only** — new types + new method appended AFTER the existing class body (after L296). No edits to L60-240.
  - **SL-5 touches `except` keywords only** at L116, L147, L207, L226 (inside `compress_indexes`, `_calculate_checksum`, `create_metadata` bodies, which SL-4 does NOT edit).
  - No overlap. Both can be prepared in parallel; SL-5 rebases onto SL-4's merged base.
- **Single-writer file — `mcp_server/watcher_multi_repo.py`**:
  - **SL-3 owns L142-164** (compute observed hash + swap `index_file` call for `index_file_guarded`). Inside the existing P12-SL-2 lock block.
  - **SL-4 appends** a post-reindex-done hook at the end of `MultiRepositoryWatcher._sync_repository` (immediately after the existing P12-SL-3 L363-410 reindex-completion block). Call signature: `if self._artifact_publisher is not None: self._artifact_publisher.publish_on_reindex(ctx.repo_id, head_commit)`. Publisher is injected via constructor or setter — watcher does NOT instantiate `ArtifactPublisher` itself (avoids circular import). This location is **frozen at plan-time** and MUST NOT drift during SL-4 execution.
  - Serialize SL-4 after SL-3 for this file.
- **SL-4 workflow file split** — `.github/workflows/index-artifact-management.yml`: SL-4 removes only the `schedule:` block (L26 area) and extends existing `workflow_dispatch` inputs. No other workflow edits.
- **Known destructive changes** (whitelist for execute-phase's pre-merge stale-base detector):
  - SL-4 removes the cron `schedule:` lines from `.github/workflows/index-artifact-management.yml` (legitimate cron→dispatch replacement).
  - Every other lane is purely additive.
- **Expected add/add conflicts**: none — no SL-0 preamble in this phase. Wave ordering + append-only constraints avoid the class.
- **SL-0 re-exports**: not applicable — no preamble lane. SL-1's `mcp_server/indexing/__init__.py` addition should use `__getattr__` lazy form if any symbol is re-exported; prefer just adding to `__all__` list without eager imports.
- **Interfaces-consumed audit** (stale-base blast-radius narrowing):
  - SL-2 reads: `mcp_server/indexing/checkpoint.py` public symbols (SL-1), `mcp_server/storage/sqlite_store.py::move_file/remove_file` (unchanged), `mcp_server/utils/semantic_indexer.py::delete_stale_vectors` (unchanged).
  - SL-3 reads: `mcp_server/dispatcher/dispatcher_enhanced.py::_get_file_hash`/`_should_reindex` (unchanged), `mcp_server/indexing/lock_registry.py::lock_registry` (P12, unchanged).
  - SL-4 reads: `mcp_server/artifacts/artifact_upload.py::IndexArtifactUploader` (unchanged), `mcp_server/artifacts/freshness.py::verify_artifact_freshness` (P12, unchanged).
  - SL-5 reads: `mcp_server/core/errors.py::MCPError` (unchanged), P12 SL-4 pattern in `mcp_server/metrics/prometheus_exporter.py:~L255-293`.
  - If a lane teammate finds its base pre-dates a cited upstream symbol, **stop and report** per the stale-base rule below — do not rebase silently.
- **Stale-base guidance** (verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-<first upstream dependency's merge>, it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.
- **SL-5 line-number drift**: The absolute line numbers listed for SL-5's 26 except-clause sites are plan-time references against `main` as of P13 kickoff. Once SL-3 appends new types near L615 and a new method after L1680 in `dispatcher_enhanced.py`, and SL-4 appends new code after L296 in `artifact_upload.py`, every line number past the insertion points will shift. **SL-5 teammates locate each site by enclosing function name + the specific `except` expression text, not by absolute line number.** Numbers here narrow the search; they are not acceptance criteria.
- **`bypass_branch_guard` on `enqueue_full_rescan`** (P12 execute-phase handoff open item): Treated as **internal-only**. No P13 lane consumes it; no lane may add new callers outside `mcp_server/watcher_multi_repo.py`. Not elevated to an IF-0-P13-* freeze.
- **Spec deviations to record at SL-docs.3**:
  - `MCPError` (not `McpError` per spec) — reuse existing base class.
  - `mcp_server/core/errors.py` reused; no new `mcp_server/errors/` package.
  - `IndexingError` added alongside pre-existing `IndexError` (different signature; no rename).
  - Counter named `mcp_errors_by_type_total` with labels `["module", "exception"]`.
- **User-runbook prerequisite**: Before `/execute-phase p13`, confirm runtime GitHub-token scopes include `actions:write` and `contents:write` (for `workflow_dispatch` + release-tag moves). SL-docs.2 updates `docs/operations/user-action-runbook.md` to record this.
- **Worktree naming**: `execute-phase` allocates unique worktree names via `scripts/allocate_worktree_name.sh`.
- **Circular-import precedent**: `ArtifactPublisher` in `publisher.py` MUST NOT `from mcp_server.gateway import …` or `from mcp_server.watcher_multi_repo import …`. Accept uploader + optional `gh_cmd` as constructor args; watcher injects the publisher (SL-4.3 sets the injection point).

## Acceptance Criteria

- [ ] `pytest tests/test_reindex_resume.py -v` passes; covers `ReindexCheckpoint` round-trip, atomic save, and a 1000-file mid-run-failure scenario that resumes at file #500 (test required for IF-0-P13-1).
- [ ] `pytest tests/test_two_phase_commit.py -v` passes; covers both-ok, primary-fails, shadow-fails-with-rollback, rename fault-injection (test required for IF-0-P13-2; not satisfied by grep alone).
- [ ] `pytest tests/test_dispatcher_toctou.py -v` passes; covers hash-match, hash-mismatch, and concurrent-writer scenarios (test required for IF-0-P13-3).
- [ ] `pytest tests/test_artifact_publish_race.py -v` passes; covers idempotency, two-commit parallel publish with only-one-wins on `index-latest`, and loser's release still reachable (test required for IF-0-P13-4).
- [ ] `pytest tests/test_structured_errors.py -v` passes; covers `IndexingError`/`ArtifactError` subclassing, `record_handled_error` increments and no-op fallback, and a per-file assertion that every SL-5 owned file imports + calls the helper (test required for IF-0-P13-5; paired with grep to prevent rename-defeats).
- [ ] **Bare-except exhaustiveness** (paired grep + test for Exit criterion #6): `rg -n '^\s*except\s*(Exception|BaseException)?\s*:' mcp_server/dispatcher/ mcp_server/artifacts/` returns zero hits, AND `tests/test_structured_errors.py::test_sampled_refactored_sites_increment_counter` raises the underlying exception at ≥3 of the 26 sites and asserts `mcp_errors_by_type_total{module=..., exception=...}` increments by exactly 1 per site. Grep alone is insufficient — pairing prevents the "rename the keyword regex" dodge.
- [ ] **Publish latency** (Exit criterion #4 gate): `pytest tests/test_artifact_publish_race.py::test_publish_latency_under_30s -v` asserts mocked-`gh` publish completes under 30s wall-clock for a 10 MB synthetic artifact (spec budget <2 min under real network).
- [ ] `curl -s localhost:9090/metrics | grep -E 'mcp_errors_by_type_total' | head -3` returns at least one line with non-zero count after a deliberately-failing artifact download (exercises the end-to-end counter surface).
- [ ] No new cron invocations: `grep -rn "^\s*schedule:" .github/workflows/index-artifact-management.yml` returns nothing (SL-4 cron-removal sanity; paired with the workflow integration test).
- [ ] All P12 regression green: `pytest tests/test_health_probes.py tests/test_indexing_lock.py tests/test_branch_drift_rescan.py tests/test_hot_path_histograms.py tests/test_artifact_freshness.py -v`.
- [ ] `uv lock --locked` exits 0.

## Verification

End-to-end after all lanes merge. Adapted from `specs/phase-plans-v1.md:895-909`:

```bash
# 1. Reindex resume
pytest tests/test_reindex_resume.py -v

# 2. Two-phase Qdrant+SQLite commit
pytest tests/test_two_phase_commit.py -v

# 3. TOCTOU-guarded dispatch
pytest tests/test_dispatcher_toctou.py -v

# 4. Direct publish + atomic latest
pytest tests/test_artifact_publish_race.py -v

# 5. Structured error counters surface on /metrics
op run --env-file=.mcp.env -- python -m mcp_server.cli.server_commands &
SERVER_PID=$!
sleep 3
# Issue something that triggers a handled exception in the artifact path:
MCP_ARTIFACT_FORCE_OUTAGE=1 curl -s -o /dev/null localhost:8000/repos/test/reindex
curl -fsS localhost:9090/metrics | grep -E 'mcp_errors_by_type_total\{.*\} [1-9]'
pytest tests/test_structured_errors.py -v

# 6. Workflow file sanity
! grep -q "^\s*schedule:" .github/workflows/index-artifact-management.yml
grep -q "publish_on_reindex" .github/workflows/index-artifact-management.yml

# 7. P12 regression baseline
pytest tests/test_health_probes.py tests/test_indexing_lock.py tests/test_branch_drift_rescan.py tests/test_hot_path_histograms.py tests/test_artifact_freshness.py -v

# 8. Lockfile check
uv lock --locked

kill $SERVER_PID
```

All commands must return success. Any non-zero exit, zero counter sample on `mcp_errors_by_type_total` after a forced failure, or a cron line still in the workflow file, fails the phase.

## Risks & Mitigations

1. **SL-2 rewrite of `_move_file` changes existing semantics for callers that expect non-atomic partial completion** — Mitigated by SL-2.1 tests preserving the happy-path behavior; rollback is observable only on injected fault. No existing caller relies on partial completion (audit required at SL-2.1).
2. **SL-3's `index_file_guarded` call path regresses watcher throughput via double-hashing** — Mitigated by SL-3 computing the watcher-side hash once, passing the result through; dispatcher reuses that value as `expected_hash` and recomputes only on disk-read immediately before write. No duplicate hash on the happy path inside one request.
3. **SL-4 cron removal breaks users relying on the scheduled promote/cleanup/list jobs** — Mitigated by keeping the validate/promote/cleanup/list `workflow_dispatch` inputs intact; only the `schedule:` block is removed. Users retain on-demand access. Runbook update in SL-docs.2 flags this migration.
4. **SL-5 except-clause refactor at 26 sites has high surface area for behavior regression** — Mitigated by strict `except`-keyword-only scope; SL-5 forbids any structural changes to try-blocks. SL-5.4 runs the full dispatcher + artifact test suites as regression gate.
5. **`record_handled_error` raising breaks error-path recovery** — Mitigated by helper's own inner try/except-and-swallow (specified in IF-0-P13-5 docstring); SL-5.1 test asserts the helper never raises even when `prometheus_client` is missing.
6. **Concurrent publishers at commits A and B both claim `index-latest`** — Mitigated by the SHA-keyed release being the authoritative artifact; `gh release edit --target` is the single atomic pointer move, and the loser's release is still addressable. SL-4.1 test spawns two publish-on-reindex tasks against distinct commits and asserts the final `is_latest` flag is monotone.

## Files Critical for Execution

- `mcp_server/indexing/checkpoint.py` (new) — SL-1 owns.
- `mcp_server/indexing/__init__.py` — SL-1 extends `__all__`.
- `mcp_server/indexing/incremental_indexer.py:121-171, 263-309` — SL-1 edit window.
- `mcp_server/indexing/incremental_indexer.py:106-119, 189-221, 223-261` — SL-2 edit window.
- `mcp_server/storage/two_phase.py` (new) — SL-2 owns.
- `mcp_server/dispatcher/dispatcher_enhanced.py:~615, L1680+` — SL-3 append window; `:355, 790, 794, 822, 1007, 1211, 1533, 1537, 1611, 1697` — SL-5 except-only touch sites.
- `mcp_server/watcher_multi_repo.py:142-164` — SL-3 edit window; post-reindex hook site — SL-4 edit window (non-overlapping).
- `mcp_server/artifacts/publisher.py` (new) — SL-4 owns.
- `mcp_server/artifacts/artifact_upload.py` — SL-4 appends after L296; SL-5 except-only at L116, 147, 207, 226.
- `mcp_server/artifacts/artifact_download.py:187, 229, 245, 275, 418, 442` — SL-5 except-only.
- `mcp_server/artifacts/multi_repo_artifact_coordinator.py:62` — SL-5 except-only.
- `mcp_server/dispatcher/simple_dispatcher.py:182`, `fallback.py:57, 63`, `cross_repo_coordinator.py:649, 681` — SL-5 except-only.
- `.github/workflows/index-artifact-management.yml` — SL-4 (cron removal + workflow_dispatch extension).
- `mcp_server/core/errors.py` — SL-5 extends (`IndexingError`, `ArtifactError`, `record_handled_error`).
- `mcp_server/metrics/prometheus_exporter.py:~L255-293` — SL-5 appends `errors_by_type` Counter alongside P12 SL-4's histograms.
- `tests/test_reindex_resume.py`, `tests/test_two_phase_commit.py`, `tests/test_dispatcher_toctou.py`, `tests/test_artifact_publish_race.py`, `tests/test_structured_errors.py` — all new, owned by their respective lanes.
