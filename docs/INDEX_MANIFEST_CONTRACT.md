# Index Manifest Contract

## Location and format
- A JSON manifest lives next to each SQLite index file (for example `code_index.db.manifest.json`).
- Manifests are written via `IndexManager.write_index_manifest` or `IndexDiscovery.write_index_manifest` and read with `IndexManager.read_index_manifest`.
- The manifest captures:
  - `schema_version`: semantic version string for the SQLite schema.
  - `embedding_model`: identifier for the embedding model used to populate vector content.
  - `creation_commit`: git commit hash the index was generated from (if available).
  - `content_hash`: SHA256 hash of the SQLite file for integrity validation.
  - `created_at`: ISO8601 timestamp when the manifest was written.

## Version-selection contract
When multiple indexes are available, selection follows this order:
1. Prefer indexes whose manifest matches both the requested `schema_version` and `embedding_model`.
2. If no exact match exists, prefer matching `schema_version` even if the embedding model differs, and emit a warning.
3. If no schema match exists, prefer matching `embedding_model` with a warning about the schema mismatch.
4. If nothing matches or a manifest is missing, fall back to the first valid index candidate and warn that the manifest contract could not be honored.

Requests are provided via `IndexDiscovery.get_local_index_path(requested_schema_version=..., requested_embedding_model=...)`, which delegates to `IndexManager.select_best_index` for the actual choice. The selection warnings are logged via the standard MCP server logger.

## Content integrity
`IndexManager.write_index_manifest` automatically computes the SHA256 `content_hash` for the target SQLite database. Downstream tools may use this hash to confirm the manifest matches the on-disk file when loading cached artifacts.
