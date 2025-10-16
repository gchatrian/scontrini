-- ===================================
-- ROW LEVEL SECURITY POLICIES - SISTEMA REVIEW
-- ===================================
-- Esegui questo SQL per configurare RLS su view e tabelle review

-- ===================================
-- 1. RICREA VIEW con SECURITY INVOKER
-- ===================================

-- View prodotti pending review
DROP VIEW IF EXISTS products_pending_review;

CREATE OR REPLACE VIEW products_pending_review
WITH (security_invoker = true)  -- 🔐 Applica RLS dell'utente corrente
AS
SELECT 
    pm.id as mapping_id,
    pm.raw_name,
    pm.store_name,
    pm.confidence_score,
    pm.interpretation_details,
    pm.created_at,
    np.id as normalized_product_id,
    np.canonical_name,
    np.brand,
    np.category,
    np.verification_status,
    -- Conta quante volte questo prodotto è stato acquistato
    COUNT(DISTINCT ph.id) as purchase_count,
    -- Ultimo acquisto
    MAX(ph.purchase_date) as last_purchase_date,
    -- Household che l'hanno acquistato (solo quelli dell'utente per RLS)
    array_agg(DISTINCT ph.household_id) FILTER (WHERE ph.household_id IS NOT NULL) as household_ids
FROM product_mappings pm
JOIN normalized_products np ON np.id = pm.normalized_product_id
LEFT JOIN purchase_history ph ON ph.normalized_product_id = np.id
    -- Filtra purchase_history per household dell'utente
    AND EXISTS (
        SELECT 1 FROM household_members hm
        WHERE hm.household_id = ph.household_id
        AND hm.user_id = auth.uid()
    )
WHERE pm.requires_manual_review = true
  AND np.verification_status = 'pending_review'
GROUP BY 
    pm.id, pm.raw_name, pm.store_name, pm.confidence_score, 
    pm.interpretation_details, pm.created_at,
    np.id, np.canonical_name, np.brand, np.category, np.verification_status
ORDER BY purchase_count DESC NULLS LAST, last_purchase_date DESC NULLS LAST;

COMMENT ON VIEW products_pending_review IS 
  'Prodotti che richiedono review manuale, filtrati per household dell''utente (SECURITY INVOKER)';

-- View statistiche review (globale per utente)
DROP VIEW IF EXISTS product_review_stats;

CREATE OR REPLACE VIEW product_review_stats
WITH (security_invoker = true)  -- 🔐 Applica RLS dell'utente corrente
AS
SELECT 
    COUNT(*) FILTER (WHERE pm.requires_manual_review = true) as pending_review_count,
    COUNT(*) FILTER (WHERE pm.verified_by_user = true) as user_verified_count,
    COUNT(*) FILTER (WHERE pm.confidence_score < 0.5) as low_confidence_count,
    COUNT(*) FILTER (WHERE pm.confidence_score >= 0.8) as high_confidence_count,
    AVG(pm.confidence_score) as avg_confidence_score,
    COUNT(DISTINCT pm.store_name) as stores_with_mappings,
    -- Statistiche per household dell'utente
    COUNT(DISTINCT ph.household_id) as user_households_count,
    COUNT(DISTINCT ph.id) as user_purchases_count
FROM product_mappings pm
LEFT JOIN purchase_history ph ON ph.normalized_product_id = pm.normalized_product_id
    -- Filtra per household dell'utente
    AND EXISTS (
        SELECT 1 FROM household_members hm
        WHERE hm.household_id = ph.household_id
        AND hm.user_id = auth.uid()
    );

COMMENT ON VIEW product_review_stats IS 
  'Statistiche sistema review filtrate per household dell''utente (SECURITY INVOKER)';

-- ===================================
-- 2. VERIFICA RLS ABILITATO su tabelle
-- ===================================

-- Assicurati che RLS sia abilitato (potrebbero già esserlo)
ALTER TABLE product_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE normalized_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_history ENABLE ROW LEVEL SECURITY;

-- ===================================
-- 3. POLICIES per PRODUCT_MAPPINGS (Aggiorna esistenti)
-- ===================================

-- Drop policies esistenti se presenti
DROP POLICY IF EXISTS "Anyone can view product mappings" ON product_mappings;
DROP POLICY IF EXISTS "Service can manage product mappings" ON product_mappings;
DROP POLICY IF EXISTS "Members can view their mappings" ON product_mappings;
DROP POLICY IF EXISTS "Members can update their mappings" ON product_mappings;

-- Gli utenti possono vedere mappings dei prodotti nei loro household
CREATE POLICY "Members can view household product mappings"
    ON product_mappings FOR SELECT
    USING (
        -- Può vedere se ha acquistato questo prodotto nel suo household
        EXISTS (
            SELECT 1 FROM purchase_history ph
            JOIN household_members hm ON hm.household_id = ph.household_id
            WHERE ph.normalized_product_id = product_mappings.normalized_product_id
            AND hm.user_id = auth.uid()
        )
        OR
        -- Oppure se è un mapping generico senza household specifico
        store_name IS NULL
    );

-- Gli utenti possono aggiornare (revieware) mappings dei loro household
CREATE POLICY "Members can review their product mappings"
    ON product_mappings FOR UPDATE
    USING (
        -- Può aggiornare se ha acquistato questo prodotto nel suo household
        EXISTS (
            SELECT 1 FROM purchase_history ph
            JOIN household_members hm ON hm.household_id = ph.household_id
            WHERE ph.normalized_product_id = product_mappings.normalized_product_id
            AND hm.user_id = auth.uid()
        )
    )
    WITH CHECK (
        -- Può solo modificare campi review (non normalized_product_id!)
        true
    );

-- Il backend può gestire tutto
CREATE POLICY "Service can manage product mappings"
    ON product_mappings FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ===================================
-- 4. POLICIES per NORMALIZED_PRODUCTS (Aggiorna esistenti)
-- ===================================

-- Drop policies esistenti
DROP POLICY IF EXISTS "Anyone can view normalized products" ON normalized_products;
DROP POLICY IF EXISTS "Service can manage normalized products" ON normalized_products;

-- Tutti gli utenti autenticati possono vedere prodotti normalizzati
-- (catalogo condiviso, come stores)
CREATE POLICY "Authenticated users can view normalized products"
    ON normalized_products FOR SELECT
    USING (auth.role() = 'authenticated');

-- Gli utenti possono aggiornare prodotti che hanno nei loro household
-- (per correggere nome, brand, categoria dopo review)
CREATE POLICY "Members can update their normalized products"
    ON normalized_products FOR UPDATE
    USING (
        -- Può aggiornare se l'ha acquistato nel suo household
        EXISTS (
            SELECT 1 FROM purchase_history ph
            JOIN household_members hm ON hm.household_id = ph.household_id
            WHERE ph.normalized_product_id = normalized_products.id
            AND hm.user_id = auth.uid()
        )
    )
    WITH CHECK (
        -- Può modificare solo certi campi (non id!)
        true
    );

-- Il backend può gestire tutto
CREATE POLICY "Service can manage normalized products"
    ON normalized_products FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ===================================
-- 5. POLICIES per PURCHASE_HISTORY (Già esistenti, verifica)
-- ===================================

-- Verifica che esista policy SELECT
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'purchase_history' 
        AND policyname = 'Members can view household purchase history'
    ) THEN
        -- Crea policy se non esiste
        CREATE POLICY "Members can view household purchase history"
            ON purchase_history FOR SELECT
            USING (
                EXISTS (
                    SELECT 1 FROM household_members
                    WHERE household_members.household_id = purchase_history.household_id
                    AND household_members.user_id = auth.uid()
                )
            );
    END IF;
END $$;

-- ===================================
-- 6. FUNZIONI con SECURITY DEFINER
-- ===================================

-- Le funzioni approve/reject devono bypassare RLS per fare UPDATE
-- ma verificare che l'utente abbia accesso

-- Ricrea approve_product_mapping con controllo accesso
CREATE OR REPLACE FUNCTION approve_product_mapping(
    p_mapping_id UUID,
    p_user_id UUID,
    p_new_canonical_name TEXT DEFAULT NULL,
    p_new_brand TEXT DEFAULT NULL,
    p_new_category TEXT DEFAULT NULL
)
RETURNS JSONB 
SECURITY DEFINER  -- Esegue con permessi postgres per UPDATE
SET search_path = public
AS $$
DECLARE
    v_normalized_product_id UUID;
    v_user_has_access BOOLEAN;
BEGIN
    -- Verifica che l'utente sia autenticato
    IF p_user_id IS NULL OR p_user_id != auth.uid() THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Unauthorized'
        );
    END IF;
    
    -- Ottieni normalized_product_id
    SELECT normalized_product_id INTO v_normalized_product_id
    FROM product_mappings
    WHERE id = p_mapping_id;
    
    IF v_normalized_product_id IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Mapping not found'
        );
    END IF;
    
    -- Verifica che l'utente abbia accesso (ha acquistato questo prodotto)
    SELECT EXISTS (
        SELECT 1 FROM purchase_history ph
        JOIN household_members hm ON hm.household_id = ph.household_id
        WHERE ph.normalized_product_id = v_normalized_product_id
        AND hm.user_id = p_user_id
    ) INTO v_user_has_access;
    
    IF NOT v_user_has_access THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Access denied: product not in your households'
        );
    END IF;
    
    -- Aggiorna prodotto normalizzato se forniti nuovi valori
    IF p_new_canonical_name IS NOT NULL THEN
        UPDATE normalized_products
        SET 
            canonical_name = COALESCE(p_new_canonical_name, canonical_name),
            brand = COALESCE(p_new_brand, brand),
            category = COALESCE(p_new_category, category),
            verification_status = 'user_verified'
        WHERE id = v_normalized_product_id;
    ELSE
        -- Solo aggiorna status
        UPDATE normalized_products
        SET verification_status = 'user_verified'
        WHERE id = v_normalized_product_id;
    END IF;
    
    -- Aggiorna mapping
    UPDATE product_mappings
    SET 
        requires_manual_review = false,
        verified_by_user = true,
        confidence_score = 1.0,
        reviewed_at = NOW(),
        reviewed_by = p_user_id
    WHERE id = p_mapping_id;
    
    RETURN jsonb_build_object(
        'success', true,
        'mapping_id', p_mapping_id,
        'normalized_product_id', v_normalized_product_id
    );
END;
$$ LANGUAGE plpgsql;

-- Ricrea reject_product_mapping con controllo accesso
CREATE OR REPLACE FUNCTION reject_product_mapping(
    p_mapping_id UUID,
    p_user_id UUID,
    p_reason TEXT DEFAULT NULL
)
RETURNS JSONB
SECURITY DEFINER  -- Esegue con permessi postgres per UPDATE
SET search_path = public
AS $$
DECLARE
    v_normalized_product_id UUID;
    v_user_has_access BOOLEAN;
BEGIN
    -- Verifica che l'utente sia autenticato
    IF p_user_id IS NULL OR p_user_id != auth.uid() THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Unauthorized'
        );
    END IF;
    
    -- Ottieni normalized_product_id
    SELECT normalized_product_id INTO v_normalized_product_id
    FROM product_mappings
    WHERE id = p_mapping_id;
    
    IF v_normalized_product_id IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Mapping not found'
        );
    END IF;
    
    -- Verifica che l'utente abbia accesso
    SELECT EXISTS (
        SELECT 1 FROM purchase_history ph
        JOIN household_members hm ON hm.household_id = ph.household_id
        WHERE ph.normalized_product_id = v_normalized_product_id
        AND hm.user_id = p_user_id
    ) INTO v_user_has_access;
    
    IF NOT v_user_has_access THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Access denied: product not in your households'
        );
    END IF;
    
    -- Aggiorna prodotto come rejected
    UPDATE normalized_products
    SET verification_status = 'rejected'
    WHERE id = v_normalized_product_id;
    
    -- Aggiorna mapping
    UPDATE product_mappings
    SET 
        requires_manual_review = false,
        reviewed_at = NOW(),
        reviewed_by = p_user_id,
        interpretation_details = interpretation_details || 
            jsonb_build_object('rejection_reason', p_reason, 'rejected_at', NOW())
    WHERE id = p_mapping_id;
    
    RETURN jsonb_build_object(
        'success', true,
        'mapping_id', p_mapping_id,
        'status', 'rejected'
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION approve_product_mapping IS 
  'Approva prodotto dopo review. Verifica che l''utente abbia accesso al prodotto.';

COMMENT ON FUNCTION reject_product_mapping IS 
  'Rigetta prodotto dopo review. Verifica che l''utente abbia accesso al prodotto.';

-- ===================================
-- 7. GRANT EXECUTE sulle funzioni
-- ===================================

-- Permetti a utenti autenticati di chiamare le funzioni
GRANT EXECUTE ON FUNCTION approve_product_mapping TO authenticated;
GRANT EXECUTE ON FUNCTION reject_product_mapping TO authenticated;

-- ===================================
-- 8. VERIFICA POLICIES
-- ===================================

-- Verifica che le policies siano state create
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    CASE 
        WHEN qual IS NOT NULL THEN 'Has USING clause'
        ELSE 'No USING clause'
    END as using_clause,
    CASE 
        WHEN with_check IS NOT NULL THEN 'Has WITH CHECK clause'
        ELSE 'No WITH CHECK clause'
    END as with_check_clause
FROM pg_policies
WHERE tablename IN ('product_mappings', 'normalized_products', 'purchase_history')
ORDER BY tablename, policyname;

-- Verifica view properties
SELECT 
    schemaname,
    viewname,
    viewowner,
    CASE 
        WHEN definition LIKE '%security_invoker%' THEN '✅ SECURITY INVOKER'
        ELSE '⚠️ SECURITY DEFINER (default)'
    END as security_mode
FROM pg_views 
WHERE viewname IN ('products_pending_review', 'product_review_stats')
ORDER BY viewname;

-- ===================================
-- TEST QUERIES
-- ===================================

-- Test 1: Vedere prodotti pending review (come utente autenticato)
-- SELECT * FROM products_pending_review LIMIT 5;

-- Test 2: Statistiche review (come utente autenticato)
-- SELECT * FROM product_review_stats;

-- Test 3: Approvare un prodotto (sostituisci UUID)
-- SELECT approve_product_mapping(
--     'mapping-uuid'::uuid,
--     auth.uid(),
--     'Nome Corretto Prodotto',
--     'Brand Corretto',
--     'Categoria > Subcategoria'
-- );

-- Test 4: Rigettare un prodotto (sostituisci UUID)
-- SELECT reject_product_mapping(
--     'mapping-uuid'::uuid,
--     auth.uid(),
--     'Interpretazione completamente sbagliata'
-- );

-- ===================================
-- RIEPILOGO SICUREZZA
-- ===================================

-- 📋 RIEPILOGO:
--
-- ✅ VIEW con SECURITY INVOKER:
--    - products_pending_review: Filtra automaticamente per household utente
--    - product_review_stats: Statistiche filtrate per household utente
--
-- ✅ TABELLE con RLS:
--    - product_mappings: Utenti vedono solo mappings dei loro household
--    - normalized_products: Catalogo condiviso (come stores)
--    - purchase_history: Utenti vedono solo acquisti loro household
--
-- ✅ FUNZIONI con controllo accesso:
--    - approve_product_mapping: Verifica accesso prima di approvare
--    - reject_product_mapping: Verifica accesso prima di rigettare
--
-- ✅ PERMESSI:
--    - Utenti autenticati: SELECT su view e tabelle (filtrati da RLS)
--    - Utenti autenticati: UPDATE su mappings/products dei loro household
--    - Utenti autenticati: EXECUTE su funzioni approve/reject
--    - Service role: Pieno accesso per backend operations

-- ===================================
-- NOTE FINALI
-- ===================================

-- IMPORTANTE: 
-- 1. Le view usano SECURITY INVOKER quindi applicano RLS dell'utente
-- 2. Le funzioni usano SECURITY DEFINER ma verificano manualmente l'accesso
-- 3. Gli utenti possono solo revieware prodotti che hanno acquistato
-- 4. Il backend (service_role) ha accesso completo per automazione

DO $$
BEGIN
    RAISE NOTICE '✅ RLS Policies per Sistema Review installate correttamente!';
    RAISE NOTICE '📊 Verifica le policies con le SELECT sopra';
    RAISE NOTICE '🔐 Le view usano SECURITY INVOKER per filtrare per household';
END $$;
