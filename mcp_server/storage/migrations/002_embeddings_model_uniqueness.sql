-- Ensure embeddings are unique per file/model version and clean duplicates

-- Remove duplicate embeddings keeping the newest entry
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY file_id, model_version
            ORDER BY created_at DESC, id DESC
        ) AS rn
    FROM embeddings
)
DELETE FROM embeddings
WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

-- Add unique index for (file_id, model_version)
CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_file_model
    ON embeddings(file_id, model_version);

-- Record migration version
INSERT INTO schema_version (version, description)
VALUES (2, 'Enforce unique embeddings per file/model and remove duplicates');
