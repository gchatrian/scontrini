-- ===================================
-- Migration: MVP 004 - Cache Lookup Function
-- ===================================
-- Descrizione: Funzione per lookup cache con price coherence validation
-- Eseguire su: Database production/staging
-- Prerequisiti: product_cache_stats materialized view esistente
-- Performance target: <15ms
-- ===================================

-- ===================================
-- FUNCTION: get_cached_product
-- ===================================
-- Cerca prodotto in cache e valida price coherence
-- Ritorna JSONB con dati prodotto + flag price_coherent
CREATE OR REPLACE FUNCTION get_cached_product(
  p_raw_name TEXT,
  p_store_name TEXT,
  p_current_price NUMERIC DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
  v_result JSONB;
BEGIN
  -- Query product_cache_stats
  -- Ordina per: exact store match > usage_count > recency
  SELECT jsonb_build_object(
    'product_id', cs.normalized_product_id,
    'usage_count', cs.usage_count,
    'verified_by_households', cs.verified_by_households,
    'avg_price', cs.avg_price,
    'price_stddev', cs.price_stddev,
    'last_used', cs.last_used,
    'first_used', cs.first_used,
    'price_coherent', CASE
      -- Se prezzo non fornito, assume coerente
      WHEN p_current_price IS NULL THEN true
      -- Se non c'è storico prezzi, assume coerente
      WHEN cs.avg_price IS NULL THEN true
      -- Calcola deviazione percentuale (tolleranza ±30%)
      ELSE ABS(p_current_price - cs.avg_price) / NULLIF(cs.avg_price, 0) <= 0.30
    END
  )
  INTO v_result
  FROM product_cache_stats cs
  WHERE cs.raw_name = p_raw_name
    -- Match exact store o store NULL (generico)
    AND (cs.store_name = p_store_name OR (cs.store_name IS NULL AND p_store_name IS NULL))
  ORDER BY
    -- Priorità 1: Exact store match
    CASE WHEN cs.store_name = p_store_name THEN 1 ELSE 2 END,
    -- Priorità 2: Più utilizzato
    cs.usage_count DESC,
    -- Priorità 3: Più recente
    cs.last_used DESC
  LIMIT 1;

  RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- ===================================
-- GRANT PERMISSIONS
-- ===================================
GRANT EXECUTE ON FUNCTION get_cached_product TO authenticated;
GRANT EXECUTE ON FUNCTION get_cached_product TO service_role;

-- ===================================
-- VERIFICA FUNZIONE
-- ===================================
-- Test 1: Cerca prodotto inesistente
SELECT get_cached_product('PRODOTTO_NON_ESISTENTE', 'Conad', 1.50) as result;
-- Expected: NULL

-- Test 2: Se hai dati in cache, testa con prodotto reale
-- SELECT get_cached_product('COCA COLA 1.5L', 'Conad', 1.80) as result;
-- Expected: JSONB con product_id, usage_count, price_coherent, etc.

-- ===================================
-- COMMENTI
-- ===================================
COMMENT ON FUNCTION get_cached_product IS
'Cerca prodotto in cache verificata (product_cache_stats).
Ritorna JSONB con stats prodotto + flag price_coherent (±30% tolerance).
NULL se prodotto non trovato in cache.';
