-- ===================================
-- Migration: MVP 003 - Cache Stats Materialized View
-- ===================================
-- Descrizione: Crea materialized view per statistiche cache prodotti
-- Eseguire su: Database production/staging
-- Prerequisiti: product_mappings e purchase_history con dati
-- Performance: Refresh <500ms
-- ===================================

-- ===================================
-- MATERIALIZED VIEW: product_cache_stats
-- ===================================
-- Aggrega statistiche di utilizzo prodotti per calcolo confidence boost
CREATE MATERIALIZED VIEW IF NOT EXISTS product_cache_stats AS
SELECT
  pm.raw_name,
  pm.store_name,
  pm.normalized_product_id,
  COUNT(DISTINCT ph.id) as usage_count,
  COUNT(DISTINCT ph.household_id) as verified_by_households,
  AVG(ph.unit_price) as avg_price,
  STDDEV(ph.unit_price) as price_stddev,
  MAX(ph.purchase_date) as last_used,
  MIN(ph.purchase_date) as first_used
FROM product_mappings pm
JOIN purchase_history ph ON ph.normalized_product_id = pm.normalized_product_id
WHERE pm.verified_by_user = true
GROUP BY pm.raw_name, pm.store_name, pm.normalized_product_id;

-- ===================================
-- INDICE per lookup veloce
-- ===================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_cache_stats_lookup
ON product_cache_stats(raw_name, store_name);

-- ===================================
-- FUNZIONE: refresh_product_cache_stats
-- ===================================
-- Funzione per refresh manuale/automatico della materialized view
CREATE OR REPLACE FUNCTION refresh_product_cache_stats()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY product_cache_stats;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION refresh_product_cache_stats TO authenticated;
GRANT EXECUTE ON FUNCTION refresh_product_cache_stats TO service_role;

-- ===================================
-- VERIFICA
-- ===================================
-- Verifica view creata
SELECT
  schemaname,
  matviewname,
  definition
FROM pg_matviews
WHERE matviewname = 'product_cache_stats';

-- Verifica indice creato
SELECT
  indexname,
  indexdef
FROM pg_indexes
WHERE tablename = 'product_cache_stats';

-- Count record nella view (opzionale)
SELECT COUNT(*) as total_cached_products
FROM product_cache_stats;
