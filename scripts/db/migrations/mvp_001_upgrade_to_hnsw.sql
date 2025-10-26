-- ===================================
-- Migration: MVP 001 - Upgrade Vector Index to HNSW
-- ===================================
-- Descrizione: Migra indice vector da IVFFlat a HNSW per performance migliori
-- Eseguire su: Database production/staging
-- Prerequisiti: pgvector extension già installata
-- Downtime: ~30 secondi durante recreate index
--
-- Performance target: vector search <50ms P95
-- ===================================

-- Step 1: Drop vecchio indice IVFFlat
DROP INDEX IF EXISTS idx_normalized_products_embedding;

-- Step 2: Crea indice HNSW ottimizzato
-- Parametri:
--   m = 16: numero di connessioni per layer (default 16, buono per accuracy/speed balance)
--   ef_construction = 64: size della dynamic candidate list durante construction (default 64)
-- Per dataset <100k vettori, HNSW è più performante di IVFFlat
CREATE INDEX idx_normalized_products_embedding
ON normalized_products
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Step 3: Verifica performance (opzionale - commentato per evitare errore se no embeddings validi)
-- EXPLAIN ANALYZE
-- SELECT id, canonical_name,
--        1 - (embedding <=> '[0,0,0,...]'::vector(1536)) AS similarity
-- FROM normalized_products
-- WHERE embedding IS NOT NULL
-- ORDER BY embedding <=> '[0,0,0,...]'::vector(1536)
-- LIMIT 10;

-- Step 4: Verifica indice creato correttamente
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'normalized_products'
  AND indexname = 'idx_normalized_products_embedding';

-- Expected output:
-- indexname: idx_normalized_products_embedding
-- indexdef: CREATE INDEX ... USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64')

-- ===================================
-- ROLLBACK PLAN
-- ===================================
-- Se necessario rollback a IVFFlat:
-- DROP INDEX IF EXISTS idx_normalized_products_embedding;
-- CREATE INDEX idx_normalized_products_embedding
-- ON normalized_products
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 140);
