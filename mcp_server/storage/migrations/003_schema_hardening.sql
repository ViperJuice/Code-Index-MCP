-- Migration 003: Schema hardening and manifest backfill
-- Ensures missing content tracking columns exist, enforces embedding uniqueness,
-- and records manifest compatibility information.

-- Phase 1: Add missing columns and indexes (idempotent)
ALTER TABLE files ADD COLUMN IF NOT EXISTS content_hash TEXT;
ALTER TABLE files ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE files ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_files_content_hash ON files(content_hash);
CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(is_deleted);
CREATE INDEX IF NOT EXISTS idx_files_relative_path ON files(relative_path);
CREATE UNIQUE INDEX IF NOT EXISTS files_repository_id_relative_path_key 
  ON files(repository_id, relative_path);

-- Phase 2: Ensure file_moves table exists with content hash tracking
CREATE TABLE IF NOT EXISTS file_moves (
    id INTEGER PRIMARY KEY,
    repository_id INTEGER NOT NULL,
    old_relative_path TEXT NOT NULL,
    new_relative_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    moved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    move_type TEXT CHECK(move_type IN ('rename', 'relocate', 'restructure')),
    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_moves_content_hash ON file_moves(content_hash);
CREATE INDEX IF NOT EXISTS idx_moves_timestamp ON file_moves(moved_at);
CREATE INDEX IF NOT EXISTS idx_moves_old_path ON file_moves(old_relative_path);
CREATE INDEX IF NOT EXISTS idx_moves_new_path ON file_moves(new_relative_path);

-- Phase 3: Backfill newly added columns with safe defaults
UPDATE files 
SET content_hash = COALESCE(content_hash, hash, relative_path)
WHERE content_hash IS NULL OR content_hash = '';

UPDATE files 
SET is_deleted = COALESCE(is_deleted, FALSE)
WHERE is_deleted IS NULL;

-- Phase 4: Enforce embedding uniqueness (deduplicate first)
DELETE FROM embeddings
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM embeddings
    GROUP BY file_id, symbol_id, chunk_start, chunk_end
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_unique_scope 
  ON embeddings(file_id, symbol_id, chunk_start, chunk_end);

-- Phase 5: Manifest compatibility metadata
INSERT OR IGNORE INTO index_config (config_key, config_value, description) VALUES
    ('manifest_version', '1.0', 'Index manifest compatibility version');

-- Phase 6: Update schema version and migration log
INSERT OR REPLACE INTO schema_version (version, description) 
VALUES (3, 'Schema hardening and manifest backfill');

INSERT INTO migrations (version_from, version_to, status) 
VALUES (2, 3, 'completed');
