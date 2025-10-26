-- ===================================
-- Migration: MVP 002 - Cache Indexes
-- ===================================
-- Descrizione: Crea indici ottimizzati per cache 2-tier e context enrichment
-- Eseguire su: Database production/staging
-- Prerequisiti: Tabelle product_mappings e purchase_history esistenti
-- Performance target: cache lookup <15ms
-- ===================================

-- ===================================
-- TIER 1: Verified Cache Index
-- ===================================
-- Indice partial per mappings verificati dagli utenti
-- Usato per cache lookup ad alta priorità
CREATE INDEX IF NOT EXISTS idx_mappings_cache_tier1
ON product_mappings(raw_name, store_name, verified_by_user)
WHERE verified_by_user = true;

-- ===================================
-- TIER 2: Auto-Verified Fallback Index
-- ===================================
-- Indice partial per mappings auto-verificati con alta confidence
-- Usato come fallback quando Tier 1 non trova risultati
CREATE INDEX IF NOT EXISTS idx_mappings_cache_tier2
ON product_mappings(raw_name, store_name, confidence_score)
WHERE verified_by_user = false AND confidence_score >= 0.85;

-- ===================================
-- CONTEXT ENRICHMENT: Purchase History Indexes
-- ===================================
-- Indice per query household history (user ha già comprato questo prodotto?)
CREATE INDEX IF NOT EXISTS idx_purchase_household_product_date
ON purchase_history(household_id, normalized_product_id, purchase_date DESC);

-- Indice per query store popularity (prodotto popolare in questo negozio?)
CREATE INDEX IF NOT EXISTS idx_purchase_store_product
ON purchase_history(store_name, normalized_product_id);

-- ===================================
-- VERIFICA INDICI CREATI
-- ===================================
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('product_mappings', 'purchase_history')
  AND indexname LIKE '%cache%' OR indexname LIKE '%purchase%'
ORDER BY tablename, indexname;

-- Expected output: 4 nuovi indici creati
