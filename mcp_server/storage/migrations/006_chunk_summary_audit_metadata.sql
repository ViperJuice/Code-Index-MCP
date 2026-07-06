-- Migration 006: Add audit metadata for authoritative chunk summaries

ALTER TABLE chunk_summaries ADD COLUMN provider_name TEXT;
ALTER TABLE chunk_summaries ADD COLUMN profile_id TEXT;
ALTER TABLE chunk_summaries ADD COLUMN prompt_fingerprint TEXT;
ALTER TABLE chunk_summaries ADD COLUMN audit_metadata TEXT;

INSERT OR REPLACE INTO schema_version (version, description)
VALUES (6, 'Chunk summary audit metadata');

INSERT INTO migrations (version_from, version_to, status)
VALUES (5, 6, 'completed');
