-- ===================================
-- Migration: REFACTOR_003 - RPC Hybrid Search Function
-- ===================================
-- Descrizione: Crea RPC per ricerca ibrida FTS + Fuzzy + Filtri
-- Durata stimata: <1 secondo
-- Performance target: <100ms per query
-- ===================================

CREATE OR REPLACE FUNCTION search_products_hybrid(
  p_hypothesis text,
  p_brand text DEFAULT NULL,
  p_category text DEFAULT NULL,
  p_size numeric DEFAULT NULL,
  p_unit_type text DEFAULT NULL,
  p_size_tolerance float DEFAULT 0.15,  -- ±15%
  p_match_count int DEFAULT 20
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
BEGIN
  -- Calcola range size con tolleranza se specificato
  IF p_size IS NOT NULL THEN
    size_min := p_size * (1 - p_size_tolerance);
    size_max := p_size * (1 + p_size_tolerance);
  END IF;

  RETURN QUERY
  WITH fts_results AS (
    -- Full-Text Search con dizionario italiano
    SELECT
      np.id,
      ts_rank(
        to_tsvector('italian', np.canonical_name || ' ' || COALESCE(np.brand, '')),
        plainto_tsquery('italian', p_hypothesis)
      ) AS fts_score
    FROM normalized_products np
    WHERE to_tsvector('italian', np.canonical_name || ' ' || COALESCE(np.brand, ''))
          @@ plainto_tsquery('italian', p_hypothesis)
  ),
  fuzzy_results AS (
    -- Fuzzy Matching con trigram
    -- Threshold 0.2 = 20% similarità minima
    SELECT
      np.id,
      similarity(np.canonical_name, p_hypothesis) AS fuzzy_score
    FROM normalized_products np
    WHERE similarity(np.canonical_name, p_hypothesis) > 0.2
  )
  SELECT
    np.id,
    np.canonical_name,
    np.brand,
    np.category,
    np.subcategory,
    np.size,
    np.unit_type,
    np.tags,
    COALESCE(fts.fts_score, 0)::float AS fts_score,
    COALESCE(fuz.fuzzy_score, 0)::float AS fuzzy_score,
    -- Score combinato con pesi
    -- 40% FTS + 30% Fuzzy + 20% Brand + 10% Category
    (
      COALESCE(fts.fts_score, 0) * 0.4 +
      COALESCE(fuz.fuzzy_score, 0) * 0.3 +
      CASE WHEN p_brand IS NOT NULL AND np.brand = p_brand THEN 0.2 ELSE 0 END +
      CASE WHEN p_category IS NOT NULL AND np.category = p_category THEN 0.1 ELSE 0 END
    )::float AS combined_score
  FROM normalized_products np
  LEFT JOIN fts_results fts ON np.id = fts.id
  LEFT JOIN fuzzy_results fuz ON np.id = fuz.id
  WHERE
    -- Almeno uno dei due match deve esistere
    (fts.id IS NOT NULL OR fuz.id IS NOT NULL)
    -- Filtri hard opzionali
    AND (p_brand IS NULL OR np.brand = p_brand)
    AND (p_category IS NULL OR np.category = p_category)
    AND (p_unit_type IS NULL OR np.unit_type = p_unit_type)
    AND (p_size IS NULL OR (np.size BETWEEN size_min AND size_max))
  ORDER BY combined_score DESC
  LIMIT p_match_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- ===================================
-- GRANT PERMISSIONS
-- ===================================

GRANT EXECUTE ON FUNCTION search_products_hybrid(
  text, text, text, numeric, text, float, int
) TO service_role;

GRANT EXECUTE ON FUNCTION search_products_hybrid(
  text, text, text, numeric, text, float, int
) TO authenticated;

-- ===================================
-- TEST FUNCTION
-- ===================================

-- Test 1: Ricerca semplice (solo hypothesis)
SELECT
  canonical_name,
  brand,
  fts_score,
  fuzzy_score,
  combined_score
FROM search_products_hybrid(
  p_hypothesis := 'coca cola',
  p_match_count := 5
);

-- Test 2: Ricerca con filtri brand + category
SELECT
  canonical_name,
  brand,
  category,
  size,
  unit_type,
  combined_score
FROM search_products_hybrid(
  p_hypothesis := 'acqua frizzante',
  p_brand := 'Sant''Anna',
  p_category := 'Bevande',
  p_match_count := 5
);

-- Test 3: Ricerca con size filtering (±15%)
SELECT
  canonical_name,
  brand,
  size,
  unit_type,
  combined_score
FROM search_products_hybrid(
  p_hypothesis := 'acqua naturale',
  p_size := 1.5,
  p_unit_type := 'L',
  p_match_count := 10
);

-- ===================================
-- VERIFICA FUNCTION CREATA
-- ===================================

SELECT
  routine_name,
  routine_type,
  data_type as return_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'search_products_hybrid';

-- Expected: 1 row con FUNCTION

-- ===================================
-- PERFORMANCE TEST
-- ===================================

-- Dovrebbe essere <100ms su ~18K prodotti
EXPLAIN ANALYZE
SELECT *
FROM search_products_hybrid(
  p_hypothesis := 'pasta barilla',
  p_match_count := 20
);

-- ===================================
-- ROLLBACK PLAN
-- ===================================
-- Se necessario rollback:
-- DROP FUNCTION IF EXISTS search_products_hybrid(text, text, text, numeric, text, float, int);
-- ===================================
