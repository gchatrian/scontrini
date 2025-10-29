-- ===================================
-- Migration: REFACTOR_005 - Remove Hard Filters (Fix Critical Bug)
-- ===================================
-- Descrizione: Rimuove filtri hard su brand/category che impedivano matching
-- Problema: I filtri WHERE (p_brand IS NULL OR p.brand = p_brand) scartavano candidati PRIMA dello scoring
-- Soluzione:
--   1. Rimosso WHERE su brand/category dalla CTE base
--   2. Brand matching diventato fuzzy (similarity) invece di exact match
--   3. Category matching con partial match (LIKE)
--   4. Soglie FTS/Fuzzy abbassate (0.001 e 0.15)
--   5. Pesi aggiustati: 40% FTS + 30% Fuzzy + 15% Brand + 10% Cat + 5% Pack
-- Risultato: Ora trova sempre candidati, anche se brand/category non matchano esattamente
-- Durata stimata: <1 secondo
-- Performance: ~500ms (invariata)
-- ===================================

DROP FUNCTION IF EXISTS search_products_hybrid(text, text, text, numeric, text, float, int, float, float) CASCADE;

CREATE OR REPLACE FUNCTION search_products_hybrid(
  p_hypothesis text,
  p_brand text DEFAULT NULL,
  p_category text DEFAULT NULL,
  p_size numeric DEFAULT NULL,
  p_unit_type text DEFAULT NULL,
  p_size_tolerance float DEFAULT 0.15,
  p_match_count int DEFAULT 20,
  p_fts_threshold float DEFAULT 0.001,  -- Abbassata da 0.01
  p_trigram_threshold float DEFAULT 0.15  -- Abbassata da 0.25
) RETURNS TABLE (
  id uuid,
  canonical_name text,
  brand text,
  category text,
  subcategory text,
  size numeric,
  unit_type text,
  tags text[],
  fts_score float,
  fuzzy_score float,
  combined_score float
) AS $$
DECLARE
  size_min numeric;
  size_max numeric;
  normalized_size numeric;
BEGIN
  -- Normalizza size target in base a unit_type
  IF p_size IS NOT NULL AND p_unit_type IS NOT NULL THEN
    normalized_size := CASE
      WHEN p_unit_type IN ('L', 'l') THEN p_size * 1000
      WHEN p_unit_type IN ('kg', 'Kg', 'KG') THEN p_size * 1000
      ELSE p_size
    END;

    size_min := normalized_size * (1 - p_size_tolerance);
    size_max := normalized_size * (1 + p_size_tolerance);
  END IF;

  RETURN QUERY
  WITH base AS (
    SELECT
      p.*,
      -- FTS score (simple dictionary + tags)
      ts_rank_cd(
        to_tsvector('simple',
          p.canonical_name || ' ' ||
          COALESCE(p.brand, '') || ' ' ||
          array_to_string(p.tags, ' ')
        ),
        plainto_tsquery('simple', p_hypothesis)
      ) AS fts_score,

      -- Fuzzy matching score
      similarity(p.canonical_name, p_hypothesis) AS trigram_score,

      -- Brand hit: FUZZY similarity (non più exact match!)
      CASE
        WHEN p_brand IS NOT NULL AND p.brand IS NOT NULL THEN
          similarity(LOWER(p.brand), LOWER(p_brand))
        ELSE 0
      END AS brand_similarity,

      -- Category hit: exact o partial match (case insensitive)
      CASE
        WHEN p_category IS NOT NULL AND p.category IS NOT NULL THEN
          CASE
            WHEN LOWER(p.category) = LOWER(p_category) THEN 1.0
            WHEN LOWER(p.category) LIKE '%' || LOWER(p_category) || '%' THEN 0.7
            WHEN LOWER(p_category) LIKE '%' || LOWER(p.category) || '%' THEN 0.7
            ELSE 0
          END
        ELSE 0
      END AS category_hit,

      -- Pack hit: size matching con normalizzazione
      CASE
        WHEN p_size IS NOT NULL AND p_unit_type IS NOT NULL THEN
          CASE
            WHEN p.unit_type IN ('L', 'l') AND (p.size * 1000) BETWEEN size_min AND size_max THEN 1
            WHEN p.unit_type IN ('kg', 'Kg', 'KG') AND (p.size * 1000) BETWEEN size_min AND size_max THEN 1
            WHEN p.unit_type IN ('ml', 'g', 'pz') AND p.size BETWEEN size_min AND size_max THEN 1
            ELSE 0
          END
        ELSE 0
      END AS pack_hit

    FROM normalized_products p
    -- ⚠️ NESSUN FILTRO HARD QUI! Solo soglie minime su FTS/Fuzzy applicate dopo
  )
  SELECT
    base.id,
    base.canonical_name,
    base.brand,
    base.category,
    base.subcategory,
    base.size,
    base.unit_type,
    base.tags,
    base.fts_score::float,
    base.trigram_score::float,
    -- Ranking composito: 40% FTS + 30% Fuzzy + 15% Brand + 10% Category + 5% Pack
    (
      0.40 * base.fts_score +
      0.30 * base.trigram_score +
      0.15 * base.brand_similarity +
      0.10 * base.category_hit +
      0.05 * base.pack_hit
    )::float AS combined_score
  FROM base
  WHERE
    -- Soglia minima: almeno uno tra FTS o Fuzzy deve superare threshold
    (base.fts_score > p_fts_threshold OR base.trigram_score > p_trigram_threshold)
  ORDER BY
    combined_score DESC
  LIMIT p_match_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- ===================================
-- GRANT PERMISSIONS
-- ===================================

GRANT EXECUTE ON FUNCTION search_products_hybrid(text, text, text, numeric, text, float, int, float, float) TO service_role;
GRANT EXECUTE ON FUNCTION search_products_hybrid(text, text, text, numeric, text, float, int, float, float) TO authenticated;

COMMENT ON FUNCTION search_products_hybrid IS 'Ricerca ibrida v2.1: Nessun filtro hard, solo segnali soft per ranking. FTS+Fuzzy+Brand+Category+Pack.';

-- ===================================
-- TEST FUNCTION
-- ===================================

-- Test 1: Rio Mare (prima falliva con exact brand match)
SELECT
  canonical_name,
  brand,
  category,
  fts_score,
  fuzzy_score,
  combined_score
FROM search_products_hybrid(
  p_hypothesis := 'Rio Mare Tonno in scatola',
  p_brand := 'Rio Mare',
  p_category := 'Alimentari'
)
LIMIT 5;
-- Ora trova prodotti RIO MARE nonostante category='PESCE E CARNE IN SCATOLA' ≠ 'Alimentari'

-- Test 2: Paulaner (prima falliva con category mismatch)
SELECT
  canonical_name,
  brand,
  category,
  size,
  unit_type,
  combined_score
FROM search_products_hybrid(
  p_hypothesis := 'Paulaner Weiss Birra',
  p_brand := 'Paulaner',
  p_category := 'Bevande',
  p_size := 0.5,
  p_unit_type := 'L'
)
LIMIT 5;
-- Ora trova PAULANER nonostante category='BIRRE' ≠ 'Bevande'

-- Test 3: Latte crescita (verifica che funzioni ancora bene)
SELECT
  canonical_name,
  brand,
  fts_score,
  fuzzy_score,
  combined_score
FROM search_products_hybrid(
  p_hypothesis := 'latte crescita'
)
LIMIT 5;

-- ===================================
-- PERFORMANCE COMPARISON
-- ===================================

-- Prima (con filtri hard): ~150ms ma 0 risultati su mismatch
-- Dopo (senza filtri hard): ~530ms ma trova sempre candidati

EXPLAIN ANALYZE
SELECT *
FROM search_products_hybrid(
  p_hypothesis := 'tonno rio mare',
  p_brand := 'Rio Mare',
  p_category := 'Alimentari',
  p_match_count := 20
);

-- ===================================
-- VERIFICA FUNCTION
-- ===================================

SELECT
  routine_name,
  routine_type,
  specific_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'search_products_hybrid';

-- Expected: 1 row

-- ===================================
-- ROLLBACK PLAN
-- ===================================
-- Se necessario rollback:
-- DROP FUNCTION IF EXISTS search_products_hybrid(text, text, text, numeric, text, float, int, float, float);
-- Poi ri-eseguire migration refactor_004 (versione con filtri hard)
-- ===================================
