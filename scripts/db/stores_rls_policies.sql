-- ===================================
-- ROW LEVEL SECURITY POLICIES - STORES
-- ===================================
-- Esegui questo SQL per abilitare RLS su stores e stores_with_stats

-- ===================================
-- 1. ABILITA RLS sulla tabella stores
-- ===================================

ALTER TABLE stores ENABLE ROW LEVEL SECURITY;

-- ===================================
-- 2. POLICIES per STORES
-- ===================================

-- Rimuovi policies esistenti se presenti
DROP POLICY IF EXISTS "Authenticated users can view all stores" ON stores;
DROP POLICY IF EXISTS "Authenticated users can create stores" ON stores;
DROP POLICY IF EXISTS "Only service role can update stores" ON stores;
DROP POLICY IF EXISTS "Only service role can delete stores" ON stores;

-- Tutti gli utenti autenticati possono vedere tutti i negozi (catalogo condiviso)
CREATE POLICY "Authenticated users can view all stores"
    ON stores FOR SELECT
    USING (auth.role() = 'authenticated');

-- Tutti gli utenti autenticati possono creare nuovi negozi
CREATE POLICY "Authenticated users can create stores"
    ON stores FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

-- Solo il backend (service_role) può aggiornare negozi
CREATE POLICY "Only service role can update stores"
    ON stores FOR UPDATE
    USING (auth.role() = 'service_role');

-- Solo il backend (service_role) può eliminare negozi
CREATE POLICY "Only service role can delete stores"
    ON stores FOR DELETE
    USING (auth.role() = 'service_role');

-- ===================================
-- 3. RICREA VIEW stores_with_stats con SECURITY INVOKER
-- ===================================
-- IMPORTANTE: Usa SECURITY INVOKER per applicare le RLS policies dell'utente
-- invece di quelle del creator della vista

DROP VIEW IF EXISTS stores_with_stats;

CREATE OR REPLACE VIEW stores_with_stats
WITH (security_invoker = true)  -- 🔐 CRITICO: Applica RLS dell'utente corrente
AS
SELECT 
    s.*,
    -- Statistiche calcolate solo sui receipts degli household dell'utente
    COUNT(DISTINCT r.id) as actual_receipts,
    AVG(r.total_amount) as actual_avg_amount,
    MAX(r.receipt_date) as actual_last_receipt,
    COUNT(DISTINCT r.household_id) as unique_households
FROM stores s
LEFT JOIN receipts r ON r.store_id = s.id
    -- Filtra solo receipts degli household a cui l'utente appartiene
    AND EXISTS (
        SELECT 1 FROM household_members hm
        WHERE hm.household_id = r.household_id
        AND hm.user_id = auth.uid()
    )
GROUP BY s.id;

COMMENT ON VIEW stores_with_stats IS 'Stores con statistiche filtrate per household (SECURITY INVOKER per RLS)';

-- ===================================
-- 4. VERIFICA POLICIES
-- ===================================

-- Verifica che le policies siano state create correttamente
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename = 'stores'
ORDER BY policyname;

-- ===================================
-- NOTE IMPLEMENTATIVE
-- ===================================

-- 1. CATALOGO CONDIVISO:
--    Tutti gli utenti vedono tutti i negozi, ma le statistiche
--    nella vista stores_with_stats sono personalizzate per household
--
-- 2. CREAZIONE NEGOZI:
--    Gli utenti possono creare negozi quando caricano scontrini.
--    Il backend può fare ulteriori validazioni/merge di negozi duplicati
--
-- 3. BACKEND OPERATIONS:
--    Solo il backend con service_role key può:
--    - Aggiornare dati dei negozi (es. arricchimento dati)
--    - Eliminare negozi (es. merge, pulizia duplicati)
--    - Aggiornare statistiche aggregate
--
-- 4. VISTA stores_with_stats con SECURITY INVOKER:
--    🔐 CRITICO: La vista usa security_invoker = true per applicare
--    le RLS policies dell'utente corrente, non del creator della vista
--    
--    - Mostra TUTTI i negozi (catalogo completo)
--    - Le statistiche (receipts, avg_amount, ecc.) sono filtrate
--      per mostrare solo i dati degli household dell'utente
--    - Se un negozio non è mai stato usato dall'utente,
--      le statistiche saranno NULL o 0
--    - Ogni utente vede statistiche personalizzate basate sui propri household
--
-- 5. SECURITY DEFINER vs SECURITY INVOKER:
--    ❌ SECURITY DEFINER (default): Vista eseguita con permessi del creator
--       → Bypassa RLS, tutti vedono tutti i dati
--    ✅ SECURITY INVOKER: Vista eseguita con permessi dell'utente corrente
--       → Applica RLS correttamente, ogni utente vede solo i suoi dati
--
-- 6. PERFORMANCE:
--    La vista usa LEFT JOIN quindi è ottimizzata.
--    Gli indici esistenti su receipts.store_id e household_members
--    garantiscono buone performance.

-- ===================================
-- TEST QUERIES (da eseguire come utente autenticato)
-- ===================================

-- Test 1: Vedere tutti i negozi
-- SELECT * FROM stores LIMIT 10;

-- Test 2: Vedere negozi con statistiche personalizzate
-- SELECT 
--     name, 
--     chain, 
--     actual_receipts, 
--     actual_avg_amount,
--     actual_last_receipt
-- FROM stores_with_stats 
-- WHERE actual_receipts > 0
-- ORDER BY actual_receipts DESC;

-- Test 3: Creare un nuovo negozio (dovrebbe funzionare)
-- INSERT INTO stores (name, chain, address_full, store_type)
-- VALUES ('Test Store', 'Test Chain', 'Via Test 1', 'supermarket');

-- Test 4: Aggiornare un negozio (dovrebbe fallire se non service_role)
-- UPDATE stores SET name = 'Updated Name' WHERE id = 'some-uuid';

-- Test 5: Eliminare un negozio (dovrebbe fallire se non service_role)
-- DELETE FROM stores WHERE id = 'some-uuid';

-- ===================================
-- TEST SECURITY INVOKER (IMPORTANTE!)
-- ===================================

-- Test 6: Verifica che SECURITY INVOKER funzioni correttamente
-- Esegui questa query come utente1 e utente2 (devono vedere statistiche diverse)
-- 
-- SELECT 
--     s.name,
--     s.chain,
--     sw.actual_receipts,
--     sw.unique_households,
--     sw.actual_avg_amount
-- FROM stores s
-- JOIN stores_with_stats sw ON sw.id = s.id
-- WHERE sw.actual_receipts > 0
-- ORDER BY sw.actual_receipts DESC;
--
-- ASPETTATIVA:
-- - Utente1 vede solo statistiche dei suoi household
-- - Utente2 vede solo statistiche dei suoi household
-- - Le statistiche sono DIVERSE per ogni utente (a meno che non condividano household)

-- Test 7: Verifica proprietà della vista
-- SELECT 
--     schemaname,
--     viewname,
--     viewowner,
--     definition
-- FROM pg_views 
-- WHERE viewname = 'stores_with_stats';
--
-- ASPETTATIVA: La definizione deve contenere "security_invoker = true"

-- Test 8: Confronto stores vs stores_with_stats
-- SELECT COUNT(*) as total_stores FROM stores;
-- SELECT COUNT(*) as stores_with_stats FROM stores_with_stats;
-- 
-- ASPETTATIVA: Stesso numero (tutti i negozi visibili, ma con statistiche filtrate)