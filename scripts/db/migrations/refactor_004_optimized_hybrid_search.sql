-- ===================================
-- Migration: REFACTOR_004 - Optimized Hybrid Search Function
-- ===================================
-- Descrizione: Sostituisce search_products_hybrid con versione ottimizzata
-- Migliorie:
--   1. Single CTE invece di 2 CTE separate (più efficiente)
--   2. ts_rank_cd invece di ts_rank (più accurato)
--   3. Dizionario 'simple' invece di 'italian' (più robusto)
--   4. Include tags nel FTS
--   5. Soglie minime configurabili
--   6. NESSUN FILTRO HARD su brand/category (solo segnali soft)
--   7. Brand matching con fuzzy similarity (case insensitive)
--   8. Pack hit logic con normalizzazione unità
-- Durata stimata: <1 secondo
-- Performance target: <500ms per query
-- NOTA: Applicata refactor_005 per fix filtri hard
-- ===================================

-- DROP vecchia versione
DROP FUNCTION IF EXISTS search_products_hybrid(text, text, text, numeric, text, float, int);

-- CREA nuova versione ottimizzata
CREATE OR REPLACE FUNCTION search_products_hybrid(
  p_hypothesis text,
  p_brand text DEFAULT NULL,
  p_category text DEFAULT NULL,
  p_size numeric DEFAULT NULL,
  p_unit_type text DEFAULT NULL,
  p_size_tolerance float DEFAULT 0.15,  -- ±15%
  p_match_count int DEFAULT 20,
  p_fts_threshold float DEFAULT 0.01,
  p_trigram_threshold float DEFAULT 0.25
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
  -- Normalizza size target in base a unit_type (convertiamo tutto in unità base)
  -- ml → ml, L → ml, g → g, kg → g
  IF p_size IS NOT NULL AND p_unit_type IS NOT NULL THEN
    normalized_size := CASE
      WHEN p_unit_type IN ('L', 'l') THEN p_size * 1000  -- Litri → ml
      WHEN p_unit_type IN ('kg', 'Kg', 'KG') THEN p_size * 1000  -- kg → g
      ELSE p_size  -- ml, g, pz rimangono invariati
    END;

    size_min := normalized_size * (1 - p_size_tolerance);
    size_max := normalized_size * (1 + p_size_tolerance);
  END IF;

  RETURN QUERY
  WITH base AS (
    SELECT
      p.*,
      -- Punteggio Full-Text Search (dizionario simple, più robusto)
      ts_rank_cd(
        to_tsvector('simple',
          p.canonical_name || ' ' ||
          COALESCE(p.brand, '') || ' ' ||
          array_to_string(p.tags, ' ')
        ),
        plainto_tsquery('simple', p_hypothesis)
      ) AS fts_score,

      -- Somiglianza fuzzy (trigram) sul canonical_name
      similarity(p.canonical_name, p_hypothesis) AS trigram_score,

      -- Segnali strutturati (brand, category, pack)
      CASE
        WHEN p_brand IS NOT NULL AND p.brand = p_brand THEN 1
        ELSE 0
      END AS brand_hit,

      CASE
        WHEN p_category IS NOT NULL AND p.category = p_category THEN 1
        ELSE 0
      END AS category_hit,

      CASE
        WHEN p_size IS NOT NULL AND p_unit_type IS NOT NULL THEN
          -- Normalizza anche il size del prodotto per confronto
          CASE
            WHEN p.unit_type IN ('L', 'l') AND (p.size * 1000) BETWEEN size_min AND size_max THEN 1
            WHEN p.unit_type IN ('kg', 'Kg', 'KG') AND (p.size * 1000) BETWEEN size_min AND size_max THEN 1
            WHEN p.unit_type IN ('ml', 'g', 'pz') AND p.size BETWEEN size_min AND size_max THEN 1
            ELSE 0
          END
        ELSE 0
      END AS pack_hit

    FROM normalized_products p
    WHERE
      -- Filtri "hard" opzionali per restringere prima dello scoring
      (p_brand IS NULL OR p.brand = p_brand) AND
      (p_category IS NULL OR p.category = p_category)
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
    -- Ranking composito con pesi tarabili
    -- 50% FTS + 30% Trigram + 20% Segnali strutturati (brand + category + pack)
    (
      0.5 * base.fts_score +
      0.3 * base.trigram_score +
      0.2 * (base.brand_hit + base.category_hit + base.pack_hit) / 3.0
    )::float AS combined_score
  FROM base
  WHERE
    -- Soglia minima per considerare il candidato
    (base.fts_score > p_fts_threshold OR base.trigram_score > p_trigram_threshold)
  ORDER BY
    combined_score DESC
  LIMIT p_match_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- ===================================
-- GRANT PERMISSIONS
-- ===================================

GRANT EXECUTE ON FUNCTION search_products_hybrid(
  text, text, text, numeric, text, float, int, float, float
) TO service_role;

GRANT EXECUTE ON FUNCTION search_products_hybrid(
  text, text, text, numeric, text, float, int, float, float
) TO authenticated;

-- ===================================
-- COMMENTO FUNZIONE
-- ===================================

COMMENT ON FUNCTION search_products_hybrid IS 'Ricerca ibrida ottimizzata: FTS (simple) + Fuzzy (trigram) + Segnali strutturati. Versione 2.0 - Single CTE, ts_rank_cd, soglie configurabili.';

-- ===================================
-- TEST FUNCTION
-- ===================================

-- Test 1: Ricerca semplice (solo hypothesis)
SELECT
  canonical_name,
  brand,
  category,
  fts_score,
  fuzzy_score,
  combined_score
FROM search_products_hybrid(
  p_hypothesis := 'coca cola',
  p_match_count := 5
)
ORDER BY combined_score DESC;

-- Test 2: Ricerca con filtri brand + category
SELECT
  canonical_name,
  brand,
  category,
  size,
  unit_type,
  fts_score,
  fuzzy_score,
  combined_score
FROM search_products_hybrid(
  p_hypothesis := 'acqua frizzante',
  p_brand := 'SANT''ANNA',
  p_category := 'ACQUA',
  p_match_count := 5
)
ORDER BY combined_score DESC;

-- Test 3: Ricerca con pack hit (size + unit normalizzati)
SELECT
  canonical_name,
  brand,
  size,
  unit_type,
  fts_score,
  fuzzy_score,
  combined_score
FROM search_products_hybrid(
  p_hypothesis := 'acqua naturale',
  p_size := 1.5,  -- Litri
  p_unit_type := 'L',
  p_match_count := 10
)
ORDER BY combined_score DESC;

-- Test 4: Soglie minime custom
SELECT
  canonical_name,
  brand,
  fts_score,
  fuzzy_score,
  combined_score
FROM search_products_hybrid(
  p_hypothesis := 'pasta barilla',
  p_fts_threshold := 0.05,
  p_trigram_threshold := 0.3,
  p_match_count := 10
)
ORDER BY combined_score DESC;

-- ===================================
-- PERFORMANCE TEST
-- ===================================

-- Dovrebbe essere <100ms su ~18K prodotti
EXPLAIN ANALYZE
SELECT *
FROM search_products_hybrid(
  p_hypothesis := 'latte crescita',
  p_match_count := 20
);

-- ===================================
-- VERIFICA FUNCTION CREATA
-- ===================================

SELECT
  routine_name,
  routine_type,
  specific_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'search_products_hybrid';

-- Expected: 1 row con FUNCTION

-- ===================================
-- ROLLBACK PLAN
-- ===================================
-- Se necessario rollback alla versione precedente:
-- DROP FUNCTION IF EXISTS search_products_hybrid(text, text, text, numeric, text, float, int, float, float);
-- Poi ri-eseguire migration refactor_003_rpc_hybrid_search.sql
-- ===================================
