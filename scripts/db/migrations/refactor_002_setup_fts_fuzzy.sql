-- ===================================
-- Migration: REFACTOR_002 - Setup FTS + Fuzzy Matching
-- ===================================
-- Descrizione: Abilita full-text search e fuzzy matching
-- Durata stimata: ~2-3 minuti (dipende da dimensione tabella)
-- Rollback: DROP INDEX commands
-- ===================================

-- Step 1: Abilita extension pg_trgm (se non già presente)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Step 2: Verifica extension abilitata
SELECT
  extname,
  extversion
FROM pg_extension
WHERE extname = 'pg_trgm';

-- Expected: 1 row con pg_trgm

-- ===================================
-- INDICI PER PERFORMANCE
-- ===================================

-- Step 3: GIN Index per Full-Text Search
-- Combina canonical_name + brand per ricerca completa
-- Usa dizionario 'italian' per stemming corretto
CREATE INDEX IF NOT EXISTS idx_products_fts
ON normalized_products
USING GIN (
  to_tsvector('italian',
    canonical_name || ' ' || COALESCE(brand, '')
  )
);

-- Step 4: GIN Index per Trigram (fuzzy matching)
-- Permette similarity() e % operator
CREATE INDEX IF NOT EXISTS idx_products_trigram
ON normalized_products
USING GIN (canonical_name gin_trgm_ops);

-- Step 5: Composite Index per Filtri Hard
-- Ottimizza WHERE su brand, category, unit_type, size
CREATE INDEX IF NOT EXISTS idx_products_filters
ON normalized_products (brand, category, unit_type, size);

-- ===================================
-- VERIFICA INDICI CREATI
-- ===================================

SELECT
  schemaname,
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE tablename = 'normalized_products'
  AND indexname IN (
    'idx_products_fts',
    'idx_products_trigram',
    'idx_products_filters'
  )
ORDER BY indexname;

-- Expected: 3 rows con i 3 nuovi indici

-- ===================================
-- TEST PERFORMANCE (opzionale)
-- ===================================

-- Test FTS (dovrebbe usare idx_products_fts)
EXPLAIN ANALYZE
SELECT
  id,
  canonical_name,
  brand,
  ts_rank(
    to_tsvector('italian', canonical_name || ' ' || COALESCE(brand, '')),
    plainto_tsquery('italian', 'coca cola')
  ) AS rank
FROM normalized_products
WHERE to_tsvector('italian', canonical_name || ' ' || COALESCE(brand, ''))
      @@ plainto_tsquery('italian', 'coca cola')
ORDER BY rank DESC
LIMIT 10;

-- Test Fuzzy (dovrebbe usare idx_products_trigram)
EXPLAIN ANALYZE
SELECT
  id,
  canonical_name,
  similarity(canonical_name, 'coca cola') AS sim
FROM normalized_products
WHERE similarity(canonical_name, 'coca cola') > 0.3
ORDER BY sim DESC
LIMIT 10;

-- ===================================
-- ROLLBACK PLAN
-- ===================================
-- Se necessario rollback:
-- DROP INDEX IF EXISTS idx_products_fts;
-- DROP INDEX IF EXISTS idx_products_trigram;
-- DROP INDEX IF EXISTS idx_products_filters;
-- DROP EXTENSION IF EXISTS pg_trgm CASCADE;
-- ===================================
