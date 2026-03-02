# Multi-Profile Semantic Indexing Specification for Code-Index-MCP

## What exists today vs what must change

### Existing capabilities to preserve
- **Lexical index core is already stable and rich**: `SQLiteStore` maintains `files`, `symbols`, FTS tables, `code_chunks`, and migration support; this should remain the single lexical source of truth.  
- **Semantic retrieval stack exists and is integrated**: semantic search uses `SemanticIndexer` + Qdrant and is fused in `HybridSearch` with optional reranking.  
- **Incremental lexical lifecycle exists**: `ChangeDetector`, `IncrementalIndexer`, git-aware workflows, and filesystem watcher-triggered updates already drive incremental reindexing behavior.  
- **Artifact lifecycle exists**: local scripts and GitHub workflows already package, validate, and distribute index artifacts with metadata and compatibility checks.  
- **Backend abstraction exists**: artifact provider protocol/factory already models interchangeable backends (GitHub Actions, local FS, S3 placeholder).

### Existing assumptions to generalize
- **Single semantic model assumption** is hard-coded (e.g., `voyage-code-3`, fixed 1024-dim cosine hash, single `.index_metadata.json` compatibility check).  
- **Single semantic collection assumption** is inconsistent but singular (e.g., `SemanticIndexer` default `code-index`, settings default `code-embeddings`, plugin base appends language suffix).  
- **Artifact metadata assumes one semantic configuration** (`compatibility.embedding_model`, `embedding_dimension`, `distance_metric`), not profile sets.  
- **CLI surface assumes global semantic state** (check/rebuild semantic compatibility globally, not profile-scoped operations).

### Missing capabilities to add
- **Semantic profile registry** with durable, explicit profile IDs and metadata-driven compatibility.
- **Profile-scoped semantic namespaces/collections** per repo/commit/profile, with deterministic naming and routing.
- **Profile-aware incremental indexing** (lexical once, semantic per selected profile with isolated stale-vector cleanup).
- **Profile-aware artifacts** allowing lexical-only and selective semantic profile publishing.
- **Policy-driven backend routing** (GitHub Artifacts vs S3) with storage-independent artifact identity.
- **Chunk schema/version contract** that binds semantic compatibility to chunk boundaries and chunk IDs.

---

## 1) Executive summary

This spec evolves Code-Index-MCP from a single semantic embedding configuration into a **multi-profile semantic architecture** while preserving the existing single lexical index lifecycle.

Core architecture outcome:
- Keep **one lexical index** per repo lineage (SQLite).
- Introduce **many semantic profiles** via a registry.
- Store **one semantic namespace/collection per profile**.
- Package artifacts as **lexical unit + optional semantic profile units**.
- Route artifact transport through **backend-agnostic policy** (GitHub Artifacts or S3).

The design intentionally avoids model-specific top-level abstractions. “Commercial vs OSS” is expressed as profile definitions (`commercial-high`, `oss-high`) in a registry, not hardcoded branching.

---

## 2) Current implementation audit

### 2.1 Lexical index format and lifecycle (actual code)
- Lexical persistence is centered on `SQLiteStore`, with schema/migration management and FTS.  
- `code_chunks` already stores rich chunk identity metadata (`chunk_id`, `node_id`, `treesitter_file_id`, `symbol_hash`, `definition_id`), token metadata, and parent/depth relationships.  
- Incremental lexical flow exists via:
  - git diff-based `ChangeDetector` (`added|modified|deleted|renamed`)  
  - `IncrementalIndexer` for remove/move/reindex operations  
  - watcher-triggered dispatcher indexing/removal/move in `watcher.py`.

### 2.2 Semantic index format and lifecycle (actual code)
- `SemanticIndexer`:
  - defaults to a single collection (`collection="code-index"`)  
  - hardcodes one model (`voyage-code-3`) and compatibility hash over fixed tuple (`model:1024:cosine`)  
  - writes one metadata file `.index_metadata.json`.
- Qdrant connection supports server URL, explicit URL, memory mode, or local path fallback.
- Semantic writes are upsert-based; file-level deletion helpers exist (soft-delete payload and filtered search logic).

### 2.3 Provider integration and reranking
- Embedding provider integration is directly tied to `voyageai.Client` in `SemanticIndexer`; there is no provider plugin abstraction for embeddings.
- Hybrid retrieval merges BM25 + semantic + fuzzy and supports reranking via `RerankerFactory` (`tfidf`, `cohere`, `cross_encoder`, hybrid fallback patterns).

### 2.4 Artifact distribution and storage assumptions
- Artifact CLI and scripts currently center on GitHub artifacts (`scripts/index-artifact-upload.py`, `scripts/index-artifact-download.py`, `mcp_server/cli/artifact_commands.py`).
- Compatibility checks currently compare single semantic model + schema.
- Provider abstraction exists (`ArtifactProvider`, factory), but S3 provider is currently a placeholder (`NotImplementedError`), so practical runtime distribution is still GitHub-centric.
- Commit artifact helper names artifacts as one bundle per repo/commit (`{repo}-{shortsha}-index.tar.gz`) without semantic profile partitioning.

### 2.5 README/docs vs code mismatches (explicit)
1. **Python requirement mismatch**: user brief/docs claims Python 3.8+, but `pyproject.toml` requires `>=3.12`. Prefer code.
2. **Semantic collection mismatch**:
   - settings default `semantic_collection_name="code-embeddings"`  
   - `SemanticIndexer` default collection is `code-index`  
   - plugin base builds `f"{collection_name}-{lang}"`.  
   This creates inconsistent collection identity semantics.
3. **S3 readiness mismatch**: docs and config imply S3 support, but `S3ArtifactProvider` is unimplemented.
4. **mcp-index-kit maturity mismatch**: README describes complete portable workflow, but `mcp-index-kit/scripts/cli.py` contains explicit “not implemented” paths (e.g., indexer download/upload behavior placeholders).

---

## 3) Problem statement

Current semantic indexing is effectively singleton-configured. This causes:
- conflict risk between embeddings from different models,
- inability to coexist commercial and OSS semantic quality tiers per repo/commit,
- brittle compatibility checks (single hash, single metadata file),
- inability to publish/distribute profile-specific semantic payloads,
- no clean path for adding a new profile later without touching existing semantic assets.

---

## 4) Goals

1. Preserve **single lexical index** behavior and compatibility.
2. Add **semantic profile registry** (N profiles, not fixed 2).
3. Guarantee **profile isolation** in vector storage and artifacts.
4. Enable **incremental per-profile semantic updates** over shared lexical delta detection.
5. Support **selective publication**: lexical-only, lexical+one profile, lexical+many profiles.
6. Separate **artifact identity contract** from transport backend (GitHub Artifacts/S3).
7. Introduce **chunk schema/version-aware compatibility**.

## 5) Non-goals

- Replacing SQLite lexical architecture.
- Mixing vectors from different embedding models into a single similarity space.
- Immediate rewrite of all semantic internals (this is a staged migration).
- Building custom object store protocols beyond GitHub Artifacts/S3 in first rollout.

---

## 6) Proposed architecture

### 6.1 Core model
- **Lexical plane (singleton):** one SQLite index per repo+lineage, chunk metadata canonical.
- **Semantic plane (profile-scoped):** one vector namespace/collection per `(repo_id, profile_id, branch-or-commit scope)`.
- **Artifact plane:** composable units with shared manifest:
  - lexical unit
  - zero or more semantic profile units
  - manifest linking compatibility and storage references.

### 6.2 New key components
1. `SemanticProfileRegistry` (new module): load/validate profile definitions.
2. `SemanticNamespaceResolver` (new module): deterministic collection naming.
3. `ProfileAwareSemanticIndexer` (refactor of `SemanticIndexer`): provider/model from profile, metadata per profile.
4. `ArtifactManifestV2` (new schema): multi-unit manifest with profile descriptors.
5. `ArtifactRoutingPolicy` (new module): choose GitHub vs S3 backend independent of artifact identity.

---

## 7) Semantic profile registry design

### 7.1 Profile schema (minimum required)
Each semantic profile must include:
- `profile_id` (stable external identifier; e.g., `commercial-high`, `oss-high`)
- `provider` (`voyage`, `sentence_transformers`, etc.)
- `model_name`
- `model_version` (explicit; required for compatibility and reproducibility)
- `vector_dimension`
- `distance_metric` (`cosine`, `dot`, etc.)
- `normalization_policy` (none/l2/other; affects comparability)
- `chunk_schema_version` (ties vectors to chunk boundary semantics)
- `chunker_version` (e.g., `treesitter-chunker` semver)
- `reranker_defaults` (optional but pinned for profile behavior consistency)
- `compatibility_fingerprint` (derived hash over relevant fields)
- `build_metadata` (`created_at`, `git_commit`, `tool_version`)

Rationale: these are the minimum fields needed to prevent silent incompatibility when model/chunker/schema/routing changes.

### 7.2 Config surface proposal
Add a registry block to `.mcp-index.json` (and env override support):

```json
{
  "semantic_profiles": {
    "commercial-high": {
      "provider": "voyage",
      "model_name": "voyage-code-3",
      "model_version": "2025-01",
      "vector_dimension": 1024,
      "distance_metric": "cosine",
      "normalization_policy": "provider-default",
      "chunk_schema_version": "2.0",
      "chunker_version": "treesitter-chunker@2.x"
    },
    "oss-high": {
      "provider": "sentence_transformers",
      "model_name": "intfloat/e5-large-v2",
      "model_version": "hf-revision-sha",
      "vector_dimension": 1024,
      "distance_metric": "cosine",
      "normalization_policy": "l2",
      "chunk_schema_version": "2.0",
      "chunker_version": "treesitter-chunker@2.x"
    }
  },
  "semantic_default_profile": "commercial-high"
}
```

---

## 8) Namespace / collection design

### 8.1 Strategy choice
**Choose collection-per-profile** for Qdrant (not mixed namespace payload filtering) because:
- dimensions and distance metrics can differ per profile,
- explicit lifecycle isolation (rebuild/delete/migrate by profile),
- lower risk of accidental cross-profile queries.

### 8.2 Naming convention
`ci__{repo_hash}__{profile_id}__{lineage_id}`
- `repo_hash`: stable id already used in index management logic
- `profile_id`: registry ID
- `lineage_id`: branch or commit lineage scope (configurable)

### 8.3 Chunk ID mapping
- Keep chunk IDs **profile-independent** and lexical-derived.
- Vector point IDs become deterministic from `(chunk_id, profile_id)` to avoid collisions while preserving shared chunk identity references.

### 8.4 Query routing
- Runtime selects one profile (explicit parameter or default profile).
- Never perform raw vector fusion across profiles.
- Multi-profile querying (if enabled later) returns profile-separated result sets and optional lexical rerank merge only at score-normalized layer.

---

## 9) Chunk identity and chunk schema versioning

Current SQLite schema already has stable chunk identity columns and upsert semantics; leverage this as canonical lexical chunk identity.

Introduce:
- `chunk_schema_version` as first-class index config + artifact manifest field.
- `chunk_identity_algorithm` field (e.g., `treesitter_chunk_id_v1`) to prevent silent changes.

Compatibility rules:
1. If `chunk_schema_version` differs, semantic artifacts are incompatible (rebuild profile).
2. If `chunker_version` changes and affects boundaries/IDs, mark semantic incompatible unless migration mapping exists.
3. Lexical may still be reusable if SQLite schema unchanged and chunk table integrity valid.

---

## 10) TreeSitter Chunker integration analysis

### 10.1 Observed current usage
- Direct chunker usage exists in generic plugin (`chunk_text`) and graph/xref adapter (`build_xref`, `chunk_file`).
- SQLite chunk schema already stores stable IDs + token fields useful for future chunk-aware semantics.
- `TreeSitterWrapper` remains Python-centric legacy parser utility, separate from chunker path.

### 10.2 Capability-by-capability decision
1. **Stable deterministic chunk IDs**: **Adopt now** as semantic point identity base (already aligned with `code_chunks.chunk_id`).
2. **Byte-accurate spans**: **Adopt now** (store in chunk metadata where missing; helpful for precise stale-chunk deletes).
3. **Incremental chunk diffing**: **Adopt in phase 2** (requires robust chunk map comparison utility).
4. **Token-aware chunking/token limits**: **Adopt now for metadata; enforce limits in phase 2**.
5. **`pack_hint`/priority metadata**: **Defer** (useful for retrieval optimization but not required for profile split).
6. **Repository processor features**: **Defer pending maturity evaluation**.
7. **Graph/xref metadata**: **Defer for semantic payload enrichment after profile baseline is stable**.
8. **AST caching and parallel processing improvements**: **Adopt incrementally** where compatible with existing watcher/incremental pipeline.

Migration impact:
- adopting deterministic chunk IDs as canonical may invalidate legacy vector IDs; provide remap or rebuild path.
- any chunk-boundary change increments `chunk_schema_version`.

---

## 11) Incremental indexing design

### 11.1 Detection and planning
1. Run existing `ChangeDetector` once.
2. Apply lexical update once (SQLite + chunk tables).
3. Resolve affected chunks from lexical delta.
4. For each selected semantic profile:
   - delete stale points for removed/changed chunks,
   - embed/upsert new chunk payloads.

### 11.2 Stale vector deletion
- Maintain mapping table (new) `semantic_points(profile_id, chunk_id, point_id, collection, updated_at)`.
- On file delete/rename/change: derive impacted `chunk_id`s from lexical tables and delete by `point_id`.

### 11.3 Add profile later without disturbing existing one
- Building a newly introduced profile runs semantic pass over existing lexical chunks only.
- Existing profile collections remain untouched.

### 11.4 Branch switching behavior
- Use existing git hooks/change logic to detect lineage switch.
- If lexical artifact for target lineage is available and compatible, hydrate lexical first.
- Semantic profiles are loaded lazily per demand; missing profile can be pulled/built independently.

---

## 12) Artifact packaging and compatibility design

### 12.1 Artifact unit model
Define three unit types:
1. `lexical` (SQLite db + lexical metadata)
2. `semantic_profile` (single profile vector payload + profile metadata)
3. `manifest` (ties units together; includes compatibility matrix)

### 12.2 Packaging choices
- Support both:
  - bundled package (`manifest + lexical + selected profiles`) for convenience
  - split package (lexical artifact plus profile artifacts) for selective distribution.

### 12.3 Manifest v2 fields (required)
- artifact identity (logical id, repo, branch, commit)
- unit list with checksums and sizes
- lexical schema metadata
- per-profile registry metadata + compatibility fingerprints
- backend transport references (opaque URIs per backend)

### 12.4 Publication combinations
Must support:
- lexical only
- lexical + OSS
- lexical + commercial
- lexical + multiple semantic profiles

### 12.5 Compatibility checks before use
- lexical compatibility: schema + migration level
- semantic compatibility per profile: profile fingerprint + chunk schema/chunker version + vector params
- incompatible profiles are skipped (not fatal to lexical load)

---

## 13) Storage backend routing design

### 13.1 Principle
Separate:
- **Artifact identity**: logical artifact key and manifest contract
- **Artifact transport**: GitHub Artifacts, S3, local FS

### 13.2 Routing policy
Add `ArtifactRoutingPolicy` using:
- repo visibility (public/private)
- artifact size thresholds
- org policy override
- profile sensitivity flags (e.g., commercial profile artifacts may require private backend)

Default policy:
- public + small artifacts => GitHub Artifacts
- private/large => S3
- fallback chain configurable

### 13.3 Backend reality and gap
- Factory/config already support backend selection, but S3 provider is unimplemented. Phase 1 must implement S3 list/download/upload/delete to satisfy this spec.

---

## 14) CLI / API / config changes

### 14.1 CLI additions
Proposed commands (new or extended):
- `index profile list`
- `index profile build --profile <id>`
- `index profile rebuild --profile <id>`
- `index profile rebuild --all`
- `artifact pull --profile <id>`
- `artifact push --profile <id>`
- `index compatibility --profile <id>|--all`
- `artifact route explain [--profile <id>]`
- `index migrate --from single-model`

### 14.2 API additions
- `/search` add `semantic_profile` parameter.
- `/status` expose available profiles and compatibility state.
- `/reindex` support `profile_scope=one|all|none` and explicit profile IDs.

### 14.3 Config additions
- `semantic_profiles` registry block.
- `semantic_default_profile`.
- `artifact_routing_policy` block.
- `artifact_publish_policy` (lexical/semantic coupling choices).
- `semantic_build_profiles` defaults for CI/hook automation.

---

## 15) Migration plan

### Phase M1: metadata and registry introduction
- Introduce profile registry + manifest v2 while keeping existing single-model flow as implicit `legacy-default` profile.
- Continue writing legacy `.index_metadata.json` for backward compatibility.

### Phase M2: dual-write / profile-aware semantic
- New builds write profile-scoped metadata + collection names.
- Read path accepts legacy artifact/model metadata and maps to `legacy-default`.

### Phase M3: artifact split and routing
- Emit lexical + profile units and manifest.
- Add backend routing and S3 operational support.

### Phase M4: deprecate legacy singleton semantics
- deprecate direct single-hash compatibility checks.
- enforce profile fingerprint compatibility.

Failure handling:
- incompatible semantic profile never blocks lexical availability.
- model upgrade/chunker/schema change marks affected profile “rebuild required.”

---

## 16) Test plan

1. **Registry validation tests**: schema validation, fingerprint stability, duplicate profile IDs.
2. **Namespace tests**: deterministic collection naming and collision avoidance.
3. **Incremental tests**:
   - changed chunk deletion + upsert per profile,
   - add new profile after lexical exists,
   - branch switch behavior.
4. **Artifact tests**:
   - manifest v2 validation,
   - lexical-only and selective-profile packaging,
   - compatibility rejection by profile.
5. **Routing tests**:
   - policy decisions for GitHub vs S3,
   - backend failure fallback.
6. **Migration tests**:
   - legacy artifact ingestion,
   - mixed legacy + new profile environments.
7. **Retrieval tests**:
   - explicit profile query routing,
   - default/fallback rules,
   - no cross-model vector mixing.

---

## 17) Benchmark / evaluation plan

Track before/after across representative repos:
- lexical incremental latency (should remain neutral)
- semantic build latency per profile
- memory footprint per active profile
- artifact size per unit (lexical vs profile)
- pull/push latency by backend
- search relevance by profile (NDCG@k, MRR@k) and reranker variants
- operational metrics: profile compatibility failure rate, rebuild frequency

Target: introducing a second profile should not regress lexical indexing SLA and should scale near-linearly in semantic compute only for selected profiles.

---

## 18) Risks and open questions

1. **S3 provider incomplete today**: blocks real backend routing until implemented.
2. **Collection naming migration**: existing inconsistent names (`code-index`, `code-embeddings[-lang]`) need a canonical resolver and migration map.
3. **Chunk schema drift**: chunk boundary or ID algorithm changes can force semantic rebuild storms.
4. **CI artifact complexity**: workflows currently assume monolithic archive; must migrate to manifest-driven handling.
5. **mcp-index-kit parity**: kit CLI currently has placeholders and may lag core server capabilities.
6. **Profile-default behavior**: must define strict deterministic selection rules to avoid silent runtime changes.

Open design choices:
- lineage granularity in collection naming (commit-only vs branch+commit).
- whether semantic profile artifacts can delta-compress independently.
- whether reranker defaults should be hardbound to profile or query-time override only.

---

## 19) Recommended rollout phases

### R1 (Foundation)
- Implement profile registry, compatibility fingerprinting, and namespace resolver.
- Keep one active profile default (`commercial-high`) to avoid disruptive behavior.

### R2 (Dual profile enablement)
- Enable `commercial-high` + `oss-high` side-by-side.
- Add CLI for explicit profile build/search/publish.

### R3 (Artifact and routing)
- Introduce manifest v2 and selective unit publishing.
- Implement S3 provider + routing policy explainability.

### R4 (Incremental hardening)
- Add chunk-diff-driven semantic incremental updater and profile-aware stale-point cleanup.
- Add branch switch optimization with lazy semantic hydration.

### R5 (Legacy deprecation)
- Deprecate singleton semantic metadata path after migration period.
- Remove single-model assumptions from compatibility and workflows.

---

## Retrieval behavior policy (explicit)

- Runtime semantic retrieval always executes against **one profile at a time**.
- Default profile is resolved from registry/config.
- If default profile unavailable:
  - optional fallback to lexical-only (recommended default),
  - optional fallback to configured secondary profile (explicit opt-in only).
- Hybrid fusion (BM25 + semantic) is profile-specific.
- Combining multiple semantic profiles in one score space is disallowed by default.
