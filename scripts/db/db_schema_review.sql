-- ===================================
-- SCHEMA UPDATE: Sistema Review Prodotti
-- ===================================
-- Esegui questo SQL per aggiungere il sistema di review manuale

-- ===================================
-- 1. Aggiungi campi a product_mappings
-- ===================================

-- Flag per indicare se richiede review manuale
ALTER TABLE product_mappings 
ADD COLUMN IF NOT EXISTS requires_manual_review BOOLEAN DEFAULT false;

-- Dettagli interpretazione per debugging/review
ALTER TABLE product_mappings
ADD COLUMN IF NOT EXISTS interpretation_details JSONB DEFAULT '{}'::jsonb;

-- Timestamp review
ALTER TABLE product_mappings
ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

ALTER TABLE product_mappings
ADD COLUMN IF NOT EXISTS reviewed_by UUID REFERENCES auth.users(id);

-- Commenti
COMMENT ON COLUMN product_mappings.requires_manual_review IS 
  'TRUE se il prodotto richiede verifica manuale da parte dell''utente (confidence bassa)';

COMMENT ON COLUMN product_mappings.interpretation_details IS 
  'JSON con dettagli interpretazione: reasoning, web_verification, alternatives';

-- ===================================
-- 2. Aggiungi campi a normalized_products
-- ===================================

-- Status verifica prodotto
ALTER TABLE normalized_products
ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'auto_verified';

-- Constraint per verification_status
ALTER TABLE normalized_products
ADD CONSTRAINT check_verification_status 
CHECK (verification_status IN ('auto_verified', 'pending_review', 'user_verified', 'rejected'));

COMMENT ON COLUMN normalized_products.verification_status IS 
  'Stato verifica: auto_verified (AI alta confidence), pending_review (richiede review), user_verified (approvato da utente), rejected (scartato)';

-- ===================================
-- 3. Indici per performance queries
-- ===================================

-- Indice per trovare prodotti da revieware
CREATE INDEX IF NOT EXISTS idx_product_mappings_review 
ON product_mappings(requires_manual_review) 
WHERE requires_manual_review = true;

-- Indice per trovare prodotti pending
CREATE INDEX IF NOT EXISTS idx_normalized_products_status 
ON normalized_products(verification_status);

-- Indice composto per query review per utente/household
CREATE INDEX IF NOT EXISTS idx_product_mappings_store_review
ON product_mappings(store_name, requires_manual_review);

-- ===================================
-- 4. View per prodotti da revieware
-- ===================================

CREATE OR REPLACE VIEW products_pending_review AS
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
    -- Household che l'hanno acquistato
    array_agg(DISTINCT ph.household_id) as household_ids
FROM product_mappings pm
JOIN normalized_products np ON np.id = pm.normalized_product_id
LEFT JOIN purchase_history ph ON ph.normalized_product_id = np.id
WHERE pm.requires_manual_review = true
  AND np.verification_status = 'pending_review'
GROUP BY 
    pm.id, pm.raw_name, pm.store_name, pm.confidence_score, 
    pm.interpretation_details, pm.created_at,
    np.id, np.canonical_name, np.brand, np.category, np.verification_status
ORDER BY purchase_count DESC, last_purchase_date DESC;

COMMENT ON VIEW products_pending_review IS 
  'Prodotti che richiedono review manuale, ordinati per frequenza di acquisto';

-- ===================================
-- 5. Funzione per approvare prodotto
-- ===================================

CREATE OR REPLACE FUNCTION approve_product_mapping(
    p_mapping_id UUID,
    p_user_id UUID,
    p_new_canonical_name TEXT DEFAULT NULL,
    p_new_brand TEXT DEFAULT NULL,
    p_new_category TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_normalized_product_id UUID;
    v_result JSONB;
BEGIN
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION approve_product_mapping IS 
  'Approva un prodotto dopo review manuale, opzionalmente correggendo i dati';

-- ===================================
-- 6. Funzione per rigettare prodotto
-- ===================================

CREATE OR REPLACE FUNCTION reject_product_mapping(
    p_mapping_id UUID,
    p_user_id UUID,
    p_reason TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_normalized_product_id UUID;
BEGIN
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
            jsonb_build_object('rejection_reason', p_reason)
    WHERE id = p_mapping_id;
    
    RETURN jsonb_build_object(
        'success', true,
        'mapping_id', p_mapping_id,
        'status', 'rejected'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION reject_product_mapping IS 
  'Rigetta un prodotto dopo review manuale';

-- ===================================
-- 7. Statistiche review
-- ===================================

CREATE OR REPLACE VIEW product_review_stats AS
SELECT 
    COUNT(*) FILTER (WHERE requires_manual_review = true) as pending_review_count,
    COUNT(*) FILTER (WHERE verified_by_user = true) as user_verified_count,
    COUNT(*) FILTER (WHERE confidence_score < 0.5) as low_confidence_count,
    COUNT(*) FILTER (WHERE confidence_score >= 0.8) as high_confidence_count,
    AVG(confidence_score) as avg_confidence_score,
    COUNT(DISTINCT store_name) as stores_with_mappings
FROM product_mappings;

COMMENT ON VIEW product_review_stats IS 
  'Statistiche sistema review prodotti';

-- ===================================
-- VERIFICA INSTALLAZIONE
-- ===================================

-- Controlla che i campi siano stati aggiunti
DO $$
BEGIN
    -- Verifica product_mappings
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'product_mappings' 
        AND column_name = 'requires_manual_review'
    ) THEN
        RAISE EXCEPTION 'Campo requires_manual_review non trovato in product_mappings';
    END IF;
    
    -- Verifica normalized_products
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'normalized_products' 
        AND column_name = 'verification_status'
    ) THEN
        RAISE EXCEPTION 'Campo verification_status non trovato in normalized_products';
    END IF;
    
    RAISE NOTICE '✅ Schema review system installato correttamente!';
END $$;

-- Query di test
SELECT 
    '✅ Campi aggiunti correttamente' as status,
    (SELECT COUNT(*) FROM product_mappings WHERE requires_manual_review = true) as pending_reviews,
    (SELECT COUNT(*) FROM normalized_products WHERE verification_status = 'pending_review') as pending_products;
