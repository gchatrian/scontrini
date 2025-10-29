-- ===================================
-- Migration: REFACTOR_001 - Cleanup Vector Search
-- ===================================
-- Descrizione: Rimuove completamente logica vector search
-- Durata stimata: ~30 secondi
-- Rollback: Manuale (richiede re-generazione embeddings)
-- ===================================

-- Step 1: Drop RPC function
DROP FUNCTION IF EXISTS search_similar_products(vector(1536), float, int);

-- Step 2: Drop HNSW index (potrebbe richiedere qualche secondo)
DROP INDEX IF EXISTS idx_normalized_products_embedding;

-- Step 3: Drop embedding column
ALTER TABLE normalized_products
DROP COLUMN IF EXISTS embedding;

-- Step 4: Verifica pulizia
SELECT
  column_name,
  data_type,
  udt_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'normalized_products'
  AND column_name = 'embedding';

-- Expected: 0 rows (colonna rimossa con successo)

-- Step 5: Verifica indice rimosso
SELECT
  indexname,
  indexdef
FROM pg_indexes
WHERE tablename = 'normalized_products'
  AND indexname = 'idx_normalized_products_embedding';

-- Expected: 0 rows (indice rimosso con successo)

-- Step 6: Verifica function rimossa
SELECT
  routine_name,
  routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'search_similar_products';

-- Expected: 0 rows (function rimossa con successo)

-- ===================================
-- NOTA: Extension pgvector rimane installata
-- per eventuale uso futuro, ma non più utilizzata
-- ===================================
