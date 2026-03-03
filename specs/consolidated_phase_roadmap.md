# Consolidated Multi-Profile and Productionization Roadmap

## Objective

Unify existing implementation specs into one executable roadmap with clear phases, swim lanes, and agent assignments.

This roadmap consolidates:

- `specs/multi_profile_semantic_indexing_spec.md`
- `specs/phase1_implementation_plan.md`
- `docs/implementation/PRODUCTIONIZATION_PLAN_2026-02.md`

## Current Baseline

- Artifact provider abstraction and delta chain tooling are implemented.
- Full + delta artifact contracts exist and are tested.
- Multi-profile semantic architecture is specified but not fully implemented.

## Phase Plan

### Phase 1: Multi-Profile Foundation

Goal: Introduce profile metadata contracts and profile-aware artifact manifests.

Swim lanes:

- **Lane A (Semantic Profile Core)**
  - Implement semantic profile schema and compatibility fingerprinting.
  - Introduce profile registry with deterministic validation and defaults.
- **Lane B (Artifact Contract)**
  - Add `ArtifactManifestV2` with lexical + profile unit descriptors.
  - Keep backward-compatible behavior with existing metadata files.

Agents:

- **Agent 9**: Semantic profile registry implementation.
- **Agent 10**: Artifact manifest v2 schema and validation.

Exit criteria:

- Semantic profile definitions are validated with deterministic fingerprints.
- Manifest v2 supports lexical-only and lexical+semantic profile payloads.

### Phase 2: Profile-Isolated Semantic Indexing

Goal: Move semantic storage/query behavior to profile-isolated namespaces.

Swim lanes:

- **Lane A (Namespace and Routing)**
  - Add namespace resolver (`ci__{repo_hash}__{profile_id}__{lineage_id}`).
  - Route index/query operations by explicit or default profile.
- **Lane B (Indexer Refactor)**
  - Refactor semantic indexer to profile-driven model/dimension/metric config.
  - Preserve lexical singleton behavior.

Agents:

- **Agent 11**: Semantic namespace resolver and collection naming.
- **Agent 12**: Profile-aware semantic indexer refactor.

Exit criteria:

- No cross-profile vector mixing.
- Query path supports explicit profile selection and safe lexical fallback.

### Phase 3: Incremental Profile Lifecycle

Goal: Ensure semantic updates are profile-scoped and incremental over shared lexical deltas.

Swim lanes:

- **Lane A (Delta-to-Profile Sync)**
  - Track semantic point IDs per `(profile_id, chunk_id)`.
  - Delete stale vectors by impacted chunk IDs.
- **Lane B (Branch/Commit Hydration)**
  - Load lexical first; hydrate semantic profiles lazily.
  - Support profile add-after-lexical without disturbing existing profiles.

Agents:

- **Agent 13**: Semantic point mapping and stale vector cleanup.
- **Agent 14**: Branch switch + lazy profile hydration behavior.

Exit criteria:

- Incremental semantic rebuild can target one profile or all profiles.
- Branch transitions do not require full semantic rebuild by default.

### Phase 4: Artifact Routing and Operational Hardening

Goal: Enforce production-grade artifact selection, verification, and backend routing.

Swim lanes:

- **Lane A (Routing and Storage Policy)**
  - Implement artifact routing policy (GitHub Artifacts vs S3/local).
  - Support policy explainability for operators.
- **Lane B (Integrity and Recovery)**
  - Enforce checksum + manifest validation for pull/recover.
  - Ensure disaster recovery path for branch/commit remains operational.

Agents:

- **Agent 15**: Artifact routing policy implementation.
- **Agent 16**: Integrity gating and recovery workflow hardening.

Exit criteria:

- Pull path fails closed on manifest/integrity mismatch.
- Routing decisions are deterministic and logged.

## Parallel Execution Model

- Within each phase, swim lanes can execute in parallel.
- Next phase starts after prior phase exit criteria are met.
- Shared interfaces require freeze gates before dependent work proceeds.

## Interface Freeze Gates

- **IF-P1**: Semantic profile schema and fingerprint contract frozen.
- **IF-P2**: Manifest v2 unit schema frozen.
- **IF-P3**: Namespace resolver naming contract frozen.
- **IF-P4**: Routing policy decision inputs and outputs frozen.

## Immediate Execution Queue

1. Build profile registry module and tests (Agent 9).
2. Build manifest v2 schema module and tests (Agent 10).
3. Wire both into artifact package exports for downstream integration.

## Agent Prompt Templates

Use these prompts when launching autonomous workstreams:

- **Agent 9 Prompt**
  - Implement `SemanticProfileRegistry` with deterministic compatibility fingerprinting.
  - Add tests for validation, duplicate IDs, and fingerprint stability.
  - Do not modify semantic query execution yet.

- **Agent 10 Prompt**
  - Implement `ArtifactManifestV2` for lexical and per-profile semantic units.
  - Add strict validation and round-trip serialization tests.
  - Keep compatibility with existing full/delta metadata contracts.

- **Agent 11 Prompt**
  - Implement semantic namespace resolver for profile-isolated collection naming.
  - Add tests for deterministic naming and collision resistance.

- **Agent 12 Prompt**
  - Refactor semantic indexer to consume profile configuration.
  - Ensure model/dimension/metric are profile-bound.
  - Preserve default behavior through a legacy default profile.
