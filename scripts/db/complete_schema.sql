-- ===================================
-- SCONTRINI - COMPLETE DATABASE SCHEMA
-- ===================================
-- Questo file ricrea l'intero schema del database da zero
-- Esegui questo SQL nel SQL Editor di Supabase per ricreare tutto lo schema
-- 
-- ATTENZIONE: Questo script elimina e ricrea tutto lo schema!
-- Usa solo su database di sviluppo o per ricreare da zero.

-- ===================================
-- 1. PULIZIA INIZIALE (OPZIONALE)
-- ===================================
-- Decommenta queste righe se vuoi eliminare tutto e ricreare da zero
-- ATTENZIONE: Questo eliminerà tutti i dati!

/*
DROP VIEW IF EXISTS stores_with_stats CASCADE;
DROP VIEW IF EXISTS products_pending_review CASCADE;
DROP VIEW IF EXISTS product_review_stats CASCADE;
DROP TABLE IF EXISTS purchase_history CASCADE;
DROP TABLE IF EXISTS product_mappings CASCADE;
DROP TABLE IF EXISTS normalized_products CASCADE;
DROP TABLE IF EXISTS receipt_items CASCADE;
DROP TABLE IF EXISTS receipts CASCADE;
DROP TABLE IF EXISTS stores CASCADE;
DROP TABLE IF EXISTS household_members CASCADE;
DROP TABLE IF EXISTS households CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS calculate_store_data_quality(store_row stores) CASCADE;
DROP FUNCTION IF EXISTS update_store_data_quality() CASCADE;
DROP FUNCTION IF EXISTS approve_product_mapping(UUID, UUID, TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS reject_product_mapping(UUID, UUID, TEXT) CASCADE;
*/

-- ===================================
-- 2. FUNZIONI DI SUPPORTO
-- ===================================

-- Funzione per aggiornare updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Funzione per calcolare data quality score dei negozi
CREATE OR REPLACE FUNCTION calculate_store_data_quality(store_row stores)
RETURNS FLOAT AS $$
DECLARE
    total_fields INTEGER := 15;  -- Campi principali da valutare
    filled_fields INTEGER := 0;
BEGIN
    -- Conta quanti campi sono compilati
    IF store_row.name IS NOT NULL AND store_row.name != '' THEN filled_fields := filled_fields + 1; END IF;
    IF store_row.chain IS NOT NULL AND store_row.chain != '' THEN filled_fields := filled_fields + 1; END IF;
    IF store_row.branch_name IS NOT NULL THEN filled_fields := filled_fields + 1; END IF;
    IF store_row.vat_number IS NOT NULL THEN filled_fields := filled_fields + 2; END IF;  -- P.IVA vale doppio
    IF store_row.company_name IS NOT NULL THEN filled_fields := filled_fields + 1; END IF;
    IF store_row.address_street IS NOT NULL THEN filled_fields := filled_fields + 1; END IF;
    IF store_row.address_city IS NOT NULL THEN filled_fields := filled_fields + 1; END IF;
    IF store_row.address_province IS NOT NULL THEN filled_fields := filled_fields + 1; END IF;
    IF store_row.address_postal_code IS NOT NULL THEN filled_fields := filled_fields + 1; END IF;
    IF store_row.latitude IS NOT NULL THEN filled_fields := filled_fields + 2; END IF;  -- Coordinate valgono doppio
    IF store_row.longitude IS NOT NULL THEN filled_fields := filled_fields + 1; END IF;
    IF store_row.phone IS NOT NULL THEN filled_fields := filled_fields + 1; END IF;
    IF store_row.website IS NOT NULL THEN filled_fields := filled_fields + 1; END IF;
    
    RETURN ROUND(filled_fields::FLOAT / total_fields, 2);
END;
$$ LANGUAGE plpgsql;

-- Funzione per aggiornare data quality score automaticamente
CREATE OR REPLACE FUNCTION update_store_data_quality()
RETURNS TRIGGER AS $$
BEGIN
    NEW.data_quality_score := calculate_store_data_quality(NEW);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===================================
-- 3. TABELLE PRINCIPALI
-- ===================================

-- 3.1 HOUSEHOLDS (Account condivisi)
CREATE TABLE households (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.2 HOUSEHOLD_MEMBERS (Relazione utenti-households)
CREATE TABLE household_members (
    household_id UUID REFERENCES households(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (household_id, user_id)
);

-- 3.3 STORES (Negozi normalizzati)
CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificazione
    name TEXT NOT NULL,
    chain TEXT,
    branch_name TEXT,
    
    -- Dati fiscali
    vat_number TEXT,
    company_name TEXT,
    
    -- Indirizzo
    address_full TEXT,
    address_street TEXT,
    address_city TEXT,
    address_province TEXT,
    address_postal_code TEXT,
    address_country TEXT DEFAULT 'IT',
    
    -- Geolocalizzazione
    latitude NUMERIC,
    longitude NUMERIC,
    
    -- Metadata
    store_type TEXT,
    is_mock BOOLEAN DEFAULT FALSE,
    data_quality_score DOUBLE PRECISION CHECK (data_quality_score >= 0 AND data_quality_score <= 1),
    
    -- Informazioni aggiuntive
    phone TEXT,
    email TEXT,
    website TEXT,
    opening_hours JSONB,
    
    -- Statistiche
    total_receipts INTEGER DEFAULT 0,
    avg_receipt_amount NUMERIC,
    last_receipt_date DATE,
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(vat_number, branch_name)
);

-- 3.4 RECEIPTS (Scontrini)
CREATE TABLE receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID REFERENCES households(id) ON DELETE CASCADE NOT NULL,
    uploaded_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    image_url TEXT NOT NULL,
    store_name TEXT,
    store_address TEXT,
    receipt_date DATE,
    receipt_time TIME WITHOUT TIME ZONE,
    total_amount NUMERIC,
    payment_method TEXT,
    discount_amount NUMERIC,
    raw_ocr_text TEXT,
    ocr_confidence DOUBLE PRECISION CHECK (ocr_confidence >= 0 AND ocr_confidence <= 1),
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    store_id UUID REFERENCES stores(id) ON DELETE SET NULL
);

-- 3.5 RECEIPT_ITEMS (Prodotti sullo scontrino - dati grezzi)
CREATE TABLE receipt_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id UUID REFERENCES receipts(id) ON DELETE CASCADE NOT NULL,
    raw_product_name TEXT NOT NULL,
    quantity NUMERIC DEFAULT 1,
    unit_price NUMERIC,
    total_price NUMERIC NOT NULL,
    line_number INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.6 NORMALIZED_PRODUCTS (Prodotti normalizzati - master data)
CREATE TABLE normalized_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name TEXT UNIQUE NOT NULL,
    brand TEXT,
    category TEXT,
    subcategory TEXT,
    size TEXT,
    unit_type TEXT,
    barcode TEXT,
    tags TEXT[],
    nutritional_info JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    verification_status TEXT DEFAULT 'auto_verified' CHECK (verification_status IN ('auto_verified', 'pending_review', 'user_verified', 'rejected'))
);

-- 3.7 PRODUCT_MAPPINGS (Mappatura nomi grezzi → normalizzati)
CREATE TABLE product_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_name TEXT NOT NULL,
    normalized_product_id UUID REFERENCES normalized_products(id) ON DELETE CASCADE NOT NULL,
    store_name TEXT,
    confidence_score DOUBLE PRECISION CHECK (confidence_score >= 0 AND confidence_score <= 1),
    verified_by_user BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    requires_manual_review BOOLEAN DEFAULT FALSE,
    interpretation_details JSONB DEFAULT '{}',
    reviewed_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

-- 3.8 PURCHASE_HISTORY (Storico acquisti normalizzato)
CREATE TABLE purchase_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID REFERENCES households(id) ON DELETE CASCADE NOT NULL,
    receipt_id UUID REFERENCES receipts(id) ON DELETE CASCADE NOT NULL,
    receipt_item_id UUID REFERENCES receipt_items(id) ON DELETE CASCADE NOT NULL,
    normalized_product_id UUID REFERENCES normalized_products(id) ON DELETE SET NULL,
    purchase_date DATE NOT NULL,
    store_name TEXT,
    quantity NUMERIC,
    unit_price NUMERIC,
    total_price NUMERIC NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    store_id UUID REFERENCES stores(id) ON DELETE SET NULL
);

-- ===================================
-- 4. INDICI per Performance
-- ===================================

-- Households
CREATE INDEX idx_household_members_user ON household_members(user_id);
CREATE INDEX idx_household_members_household ON household_members(household_id);

-- Stores
CREATE INDEX idx_stores_name ON stores(name);
CREATE INDEX idx_stores_chain ON stores(chain);
CREATE INDEX idx_stores_city ON stores(address_city);
CREATE INDEX idx_stores_vat ON stores(vat_number);
CREATE INDEX idx_stores_location ON stores(latitude, longitude);
CREATE INDEX idx_stores_is_mock ON stores(is_mock);

-- Receipts
CREATE INDEX idx_receipts_household ON receipts(household_id);
CREATE INDEX idx_receipts_date ON receipts(receipt_date);
CREATE INDEX idx_receipts_status ON receipts(processing_status);
CREATE INDEX idx_receipts_uploaded_by ON receipts(uploaded_by);
CREATE INDEX idx_receipts_store ON receipts(store_id);

-- Receipt Items
CREATE INDEX idx_receipt_items_receipt ON receipt_items(receipt_id);

-- Normalized Products
CREATE INDEX idx_normalized_products_category ON normalized_products(category);
CREATE INDEX idx_normalized_products_brand ON normalized_products(brand);

-- Product Mappings
CREATE INDEX idx_product_mappings_raw_name ON product_mappings(raw_name);
CREATE INDEX idx_product_mappings_normalized ON product_mappings(normalized_product_id);

-- Purchase History
CREATE INDEX idx_purchase_history_household ON purchase_history(household_id);
CREATE INDEX idx_purchase_history_date ON purchase_history(purchase_date);
CREATE INDEX idx_purchase_history_product ON purchase_history(normalized_product_id);
CREATE INDEX idx_purchase_history_receipt ON purchase_history(receipt_id);
CREATE INDEX idx_purchase_history_store ON purchase_history(store_id);

-- ===================================
-- 5. TRIGGER per updated_at automatico
-- ===================================

-- Applica trigger alle tabelle con updated_at
CREATE TRIGGER update_households_updated_at
    BEFORE UPDATE ON households
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_receipts_updated_at
    BEFORE UPDATE ON receipts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_normalized_products_updated_at
    BEFORE UPDATE ON normalized_products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stores_updated_at
    BEFORE UPDATE ON stores
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger per data quality score automatico
CREATE TRIGGER trigger_update_store_data_quality
    BEFORE INSERT OR UPDATE ON stores
    FOR EACH ROW
    EXECUTE FUNCTION update_store_data_quality();

-- ===================================
-- 6. VISTE
-- ===================================

-- Vista stores con statistiche
CREATE OR REPLACE VIEW stores_with_stats
WITH (security_invoker = true)
AS
SELECT 
    s.*,
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

-- Vista prodotti pending review
CREATE OR REPLACE VIEW products_pending_review
WITH (security_invoker = true)
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
    COUNT(DISTINCT ph.id) as purchase_count,
    MAX(ph.purchase_date) as last_purchase_date,
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

-- Vista statistiche review
CREATE OR REPLACE VIEW product_review_stats
WITH (security_invoker = true)
AS
SELECT 
    COUNT(*) FILTER (WHERE pm.requires_manual_review = true) as pending_review_count,
    COUNT(*) FILTER (WHERE pm.verified_by_user = true) as user_verified_count,
    COUNT(*) FILTER (WHERE pm.confidence_score < 0.5) as low_confidence_count,
    COUNT(*) FILTER (WHERE pm.confidence_score >= 0.8) as high_confidence_count,
    AVG(pm.confidence_score) as avg_confidence_score,
    COUNT(DISTINCT pm.store_name) as stores_with_mappings,
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

-- ===================================
-- 7. FUNZIONI per REVIEW SYSTEM
-- ===================================

-- Funzione per approvare prodotto dopo review
CREATE OR REPLACE FUNCTION approve_product_mapping(
    p_mapping_id UUID,
    p_user_id UUID,
    p_new_canonical_name TEXT DEFAULT NULL,
    p_new_brand TEXT DEFAULT NULL,
    p_new_category TEXT DEFAULT NULL
)
RETURNS JSONB 
SECURITY DEFINER
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

-- Funzione per rigettare prodotto dopo review
CREATE OR REPLACE FUNCTION reject_product_mapping(
    p_mapping_id UUID,
    p_user_id UUID,
    p_reason TEXT DEFAULT NULL
)
RETURNS JSONB
SECURITY DEFINER
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

-- ===================================
-- 8. ROW LEVEL SECURITY (RLS)
-- ===================================

-- Abilita RLS su tutte le tabelle
ALTER TABLE households ENABLE ROW LEVEL SECURITY;
ALTER TABLE household_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipt_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE normalized_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE stores ENABLE ROW LEVEL SECURITY;

-- ===================================
-- 9. POLICIES per HOUSEHOLDS
-- ===================================

-- Gli utenti vedono solo households di cui sono membri
CREATE POLICY "Users can view their households"
    ON households FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM household_members
            WHERE household_members.household_id = households.id
            AND household_members.user_id = auth.uid()
        )
    );

-- Gli utenti possono creare nuovi households
CREATE POLICY "Users can create households"
    ON households FOR INSERT
    WITH CHECK (true);

-- Solo gli owner possono aggiornare households
CREATE POLICY "Owners can update their households"
    ON households FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM household_members
            WHERE household_members.household_id = households.id
            AND household_members.user_id = auth.uid()
            AND household_members.role = 'owner'
        )
    );

-- Solo gli owner possono eliminare households
CREATE POLICY "Owners can delete their households"
    ON households FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM household_members
            WHERE household_members.household_id = households.id
            AND household_members.user_id = auth.uid()
            AND household_members.role = 'owner'
        )
    );

-- ===================================
-- 10. POLICIES per HOUSEHOLD_MEMBERS
-- ===================================

-- I membri vedono tutti i membri del loro household
CREATE POLICY "Members can view household members"
    ON household_members FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM household_members hm
            WHERE hm.household_id = household_members.household_id
            AND hm.user_id = auth.uid()
        )
    );

-- Gli owner possono aggiungere membri
CREATE POLICY "Owners can add members"
    ON household_members FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM household_members
            WHERE household_members.household_id = household_members.household_id
            AND household_members.user_id = auth.uid()
            AND household_members.role = 'owner'
        )
    );

-- Gli owner possono rimuovere membri
CREATE POLICY "Owners can remove members"
    ON household_members FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM household_members hm
            WHERE hm.household_id = household_members.household_id
            AND hm.user_id = auth.uid()
            AND hm.role = 'owner'
        )
    );

-- ===================================
-- 11. POLICIES per RECEIPTS
-- ===================================

-- I membri vedono gli scontrini del loro household
CREATE POLICY "Members can view household receipts"
    ON receipts FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM household_members
            WHERE household_members.household_id = receipts.household_id
            AND household_members.user_id = auth.uid()
        )
    );

-- I membri possono creare scontrini nel loro household
CREATE POLICY "Members can create receipts"
    ON receipts FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM household_members
            WHERE household_members.household_id = receipts.household_id
            AND household_members.user_id = auth.uid()
        )
    );

-- I membri possono aggiornare scontrini del loro household
CREATE POLICY "Members can update household receipts"
    ON receipts FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM household_members
            WHERE household_members.household_id = receipts.household_id
            AND household_members.user_id = auth.uid()
        )
    );

-- I membri possono eliminare scontrini del loro household
CREATE POLICY "Members can delete household receipts"
    ON receipts FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM household_members
            WHERE household_members.household_id = receipts.household_id
            AND household_members.user_id = auth.uid()
        )
    );

-- ===================================
-- 12. POLICIES per RECEIPT_ITEMS
-- ===================================

-- I membri vedono gli item degli scontrini del loro household
CREATE POLICY "Members can view receipt items"
    ON receipt_items FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM receipts
            JOIN household_members ON household_members.household_id = receipts.household_id
            WHERE receipts.id = receipt_items.receipt_id
            AND household_members.user_id = auth.uid()
        )
    );

-- Il backend può inserire receipt items
CREATE POLICY "Service can create receipt items"
    ON receipt_items FOR INSERT
    WITH CHECK (true);

-- ===================================
-- 13. POLICIES per NORMALIZED_PRODUCTS
-- ===================================

-- Tutti possono leggere prodotti normalizzati (catalogo condiviso)
CREATE POLICY "Authenticated users can view normalized products"
    ON normalized_products FOR SELECT
    USING (auth.role() = 'authenticated');

-- Gli utenti possono aggiornare prodotti che hanno nei loro household
CREATE POLICY "Members can update their normalized products"
    ON normalized_products FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM purchase_history ph
            JOIN household_members hm ON hm.household_id = ph.household_id
            WHERE ph.normalized_product_id = normalized_products.id
            AND hm.user_id = auth.uid()
        )
    );

-- Solo il backend può gestire prodotti normalizzati
CREATE POLICY "Service can manage normalized products"
    ON normalized_products FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ===================================
-- 14. POLICIES per PRODUCT_MAPPINGS
-- ===================================

-- Gli utenti possono vedere mappings dei prodotti nei loro household
CREATE POLICY "Members can view household product mappings"
    ON product_mappings FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM purchase_history ph
            JOIN household_members hm ON hm.household_id = ph.household_id
            WHERE ph.normalized_product_id = product_mappings.normalized_product_id
            AND hm.user_id = auth.uid()
        )
        OR
        store_name IS NULL
    );

-- Gli utenti possono aggiornare mappings dei loro household
CREATE POLICY "Members can review their product mappings"
    ON product_mappings FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM purchase_history ph
            JOIN household_members hm ON hm.household_id = ph.household_id
            WHERE ph.normalized_product_id = product_mappings.normalized_product_id
            AND hm.user_id = auth.uid()
        )
    );

-- Solo il backend può gestire mappings
CREATE POLICY "Service can manage product mappings"
    ON product_mappings FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ===================================
-- 15. POLICIES per PURCHASE_HISTORY
-- ===================================

-- I membri vedono lo storico del loro household
CREATE POLICY "Members can view household purchase history"
    ON purchase_history FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM household_members
            WHERE household_members.household_id = purchase_history.household_id
            AND household_members.user_id = auth.uid()
        )
    );

-- Il backend può inserire nella purchase history
CREATE POLICY "Service can create purchase history"
    ON purchase_history FOR INSERT
    WITH CHECK (true);

-- ===================================
-- 16. POLICIES per STORES
-- ===================================

-- Tutti gli utenti autenticati possono vedere tutti i negozi
CREATE POLICY "Authenticated users can view all stores"
    ON stores FOR SELECT
    USING (auth.role() = 'authenticated');

-- Tutti gli utenti autenticati possono creare nuovi negozi
CREATE POLICY "Authenticated users can create stores"
    ON stores FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

-- Solo il backend può aggiornare negozi
CREATE POLICY "Only service role can update stores"
    ON stores FOR UPDATE
    USING (auth.role() = 'service_role');

-- Solo il backend può eliminare negozi
CREATE POLICY "Only service role can delete stores"
    ON stores FOR DELETE
    USING (auth.role() = 'service_role');

-- ===================================
-- 17. GRANT PERMISSIONS
-- ===================================

-- Permetti a utenti autenticati di chiamare le funzioni
GRANT EXECUTE ON FUNCTION approve_product_mapping TO authenticated;
GRANT EXECUTE ON FUNCTION reject_product_mapping TO authenticated;

-- ===================================
-- 18. COMMENTI sulle tabelle
-- ===================================

COMMENT ON TABLE households IS 'Account condivisi (es. famiglia, coppia)';
COMMENT ON TABLE household_members IS 'Membri di un household';
COMMENT ON TABLE stores IS 'Catalogo negozi normalizzati con dati completi';
COMMENT ON TABLE receipts IS 'Scontrini caricati dagli utenti';
COMMENT ON TABLE receipt_items IS 'Prodotti singoli sullo scontrino (dati grezzi OCR)';
COMMENT ON TABLE normalized_products IS 'Catalogo prodotti normalizzati';
COMMENT ON TABLE product_mappings IS 'Mappatura nomi grezzi a prodotti normalizzati';
COMMENT ON TABLE purchase_history IS 'Storico acquisti con prodotti normalizzati';

COMMENT ON VIEW stores_with_stats IS 'Stores con statistiche filtrate per household (SECURITY INVOKER per RLS)';
COMMENT ON VIEW products_pending_review IS 'Prodotti che richiedono review manuale, filtrati per household dell''utente (SECURITY INVOKER)';
COMMENT ON VIEW product_review_stats IS 'Statistiche sistema review filtrate per household dell''utente (SECURITY INVOKER)';

COMMENT ON FUNCTION approve_product_mapping IS 'Approva prodotto dopo review. Verifica che l''utente abbia accesso al prodotto.';
COMMENT ON FUNCTION reject_product_mapping IS 'Rigetta prodotto dopo review. Verifica che l''utente abbia accesso al prodotto.';

-- ===================================
-- 19. DATI INIZIALI
-- ===================================

-- Crea store "Sconosciuto" per quando non abbiamo dati
INSERT INTO stores (
    id,
    name, 
    chain,
    branch_name,
    address_full,
    store_type,
    is_mock,
    data_quality_score
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    'Negozio Sconosciuto',
    'Sconosciuto',
    'Dati non disponibili',
    'Indirizzo non disponibile',
    'supermarket',
    TRUE,
    0.0
) ON CONFLICT DO NOTHING;

-- ===================================
-- 20. VERIFICA FINALE
-- ===================================

-- Verifica che tutte le tabelle siano state create
SELECT 
    'Tabelle create' as metric,
    COUNT(*) as count
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'households', 'household_members', 'stores', 'receipts', 
    'receipt_items', 'normalized_products', 'product_mappings', 'purchase_history'
);

-- Verifica che tutte le view siano state create
SELECT 
    'View create' as metric,
    COUNT(*) as count
FROM information_schema.views 
WHERE table_schema = 'public' 
AND table_name IN ('stores_with_stats', 'products_pending_review', 'product_review_stats');

-- Verifica che RLS sia abilitato
SELECT 
    'Tabelle con RLS' as metric,
    COUNT(*) as count
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
AND c.relname IN (
    'households', 'household_members', 'stores', 'receipts', 
    'receipt_items', 'normalized_products', 'product_mappings', 'purchase_history'
)
AND c.relrowsecurity = true;

-- ===================================
-- COMPLETATO!
-- ===================================

DO $$
BEGIN
    RAISE NOTICE '✅ Schema completo creato con successo!';
    RAISE NOTICE '📊 Tutte le tabelle, view, funzioni e policies sono state create';
    RAISE NOTICE '🔐 RLS è abilitato su tutte le tabelle';
    RAISE NOTICE '🎯 Il database è pronto per l''uso!';
END $$;








