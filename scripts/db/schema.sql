-- ===================================
-- SCONTRINI DATABASE SCHEMA
-- ===================================
-- Da eseguire nel SQL Editor di Supabase

-- ===================================
-- 1. HOUSEHOLDS (Account condivisi)
-- ===================================
CREATE TABLE households (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===================================
-- 2. HOUSEHOLD_MEMBERS (Relazione utenti-households)
-- ===================================
CREATE TABLE household_members (
    household_id UUID REFERENCES households(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (household_id, user_id)
);

-- ===================================
-- 3. RECEIPTS (Scontrini)
-- ===================================
CREATE TABLE receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID REFERENCES households(id) ON DELETE CASCADE NOT NULL,
    uploaded_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    image_url TEXT NOT NULL,
    store_name TEXT,
    store_address TEXT,
    receipt_date DATE,
    receipt_time TIME,
    total_amount DECIMAL(10, 2),
    payment_method TEXT,
    discount_amount DECIMAL(10, 2),
    raw_ocr_text TEXT,
    ocr_confidence FLOAT CHECK (ocr_confidence >= 0 AND ocr_confidence <= 1),
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===================================
-- 4. RECEIPT_ITEMS (Prodotti sullo scontrino - dati grezzi)
-- ===================================
CREATE TABLE receipt_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id UUID REFERENCES receipts(id) ON DELETE CASCADE NOT NULL,
    raw_product_name TEXT NOT NULL,
    quantity DECIMAL(10, 3) DEFAULT 1,
    unit_price DECIMAL(10, 2),
    total_price DECIMAL(10, 2) NOT NULL,
    line_number INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===================================
-- 5. NORMALIZED_PRODUCTS (Prodotti normalizzati - master data)
-- ===================================
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
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===================================
-- 6. PRODUCT_MAPPINGS (Mappatura nomi grezzi → normalizzati)
-- ===================================
CREATE TABLE product_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_name TEXT NOT NULL,
    normalized_product_id UUID REFERENCES normalized_products(id) ON DELETE CASCADE NOT NULL,
    store_name TEXT,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    verified_by_user BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(raw_name, store_name)
);

-- ===================================
-- 7. PURCHASE_HISTORY (Storico acquisti normalizzato)
-- ===================================
CREATE TABLE purchase_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID REFERENCES households(id) ON DELETE CASCADE NOT NULL,
    receipt_id UUID REFERENCES receipts(id) ON DELETE CASCADE NOT NULL,
    receipt_item_id UUID REFERENCES receipt_items(id) ON DELETE CASCADE NOT NULL,
    normalized_product_id UUID REFERENCES normalized_products(id) ON DELETE SET NULL,
    purchase_date DATE NOT NULL,
    store_name TEXT,
    quantity DECIMAL(10, 3),
    unit_price DECIMAL(10, 2),
    total_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===================================
-- INDICI per Performance
-- ===================================

-- Households
CREATE INDEX idx_household_members_user ON household_members(user_id);
CREATE INDEX idx_household_members_household ON household_members(household_id);

-- Receipts
CREATE INDEX idx_receipts_household ON receipts(household_id);
CREATE INDEX idx_receipts_date ON receipts(receipt_date);
CREATE INDEX idx_receipts_status ON receipts(processing_status);
CREATE INDEX idx_receipts_uploaded_by ON receipts(uploaded_by);

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

-- ===================================
-- TRIGGER per updated_at automatico
-- ===================================

-- Funzione per aggiornare updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

-- ===================================
-- COMMENTI sulle tabelle
-- ===================================

COMMENT ON TABLE households IS 'Account condivisi (es. famiglia, coppia)';
COMMENT ON TABLE household_members IS 'Membri di un household';
COMMENT ON TABLE receipts IS 'Scontrini caricati dagli utenti';
COMMENT ON TABLE receipt_items IS 'Prodotti singoli sullo scontrino (dati grezzi OCR)';
COMMENT ON TABLE normalized_products IS 'Catalogo prodotti normalizzati';
COMMENT ON TABLE product_mappings IS 'Mappatura nomi grezzi a prodotti normalizzati';
COMMENT ON TABLE purchase_history IS 'Storico acquisti con prodotti normalizzati';
