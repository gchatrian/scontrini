-- ===================================
-- STORES TABLE - Negozi normalizzati
-- ===================================

-- Tabella stores
CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificazione
    name TEXT NOT NULL,                      -- Nome normalizzato (es. "Esselunga")
    chain TEXT,                              -- Catena (es. "Esselunga", "Coop", "Conad")
    branch_name TEXT,                        -- Nome specifico filiale (es. "Esselunga Via Roma")
    
    -- Dati fiscali
    vat_number TEXT,                         -- Partita IVA (es. "07071700152")
    company_name TEXT,                       -- Ragione sociale completa
    
    -- Indirizzo
    address_full TEXT,                       -- Indirizzo completo come su scontrino
    address_street TEXT,                     -- Via normalizzata
    address_city TEXT,                       -- Città
    address_province TEXT,                   -- Provincia (sigla es. "MI", "CO")
    address_postal_code TEXT,                -- CAP
    address_country TEXT DEFAULT 'IT',       -- Paese (default Italia)
    
    -- Geolocalizzazione
    latitude DECIMAL(10, 8),                 -- Latitudine
    longitude DECIMAL(11, 8),                -- Longitudine
    
    -- Metadata
    store_type TEXT,                         -- Tipo: "supermarket", "hypermarket", "discount", "grocery"
    is_mock BOOLEAN DEFAULT FALSE,           -- TRUE se è un negozio mock (dati incompleti)
    data_quality_score FLOAT,                -- Score 0-1 qualità dati (quanti campi compilati)
    
    -- Informazioni aggiuntive (opzionali)
    phone TEXT,
    email TEXT,
    website TEXT,
    opening_hours JSONB,                     -- Orari apertura
    
    -- Statistiche (da calcolare periodicamente)
    total_receipts INTEGER DEFAULT 0,        -- Numero scontrini processati
    avg_receipt_amount DECIMAL(10, 2),       -- Importo medio scontrino
    last_receipt_date DATE,                  -- Data ultimo scontrino
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(vat_number, branch_name),         -- Stesso negozio = stessa P.IVA + branch
    CHECK (data_quality_score >= 0 AND data_quality_score <= 1)
);

-- Indici per performance
CREATE INDEX idx_stores_name ON stores(name);
CREATE INDEX idx_stores_chain ON stores(chain);
CREATE INDEX idx_stores_city ON stores(address_city);
CREATE INDEX idx_stores_vat ON stores(vat_number);
CREATE INDEX idx_stores_location ON stores(latitude, longitude);
CREATE INDEX idx_stores_is_mock ON stores(is_mock);

-- Trigger per updated_at
CREATE TRIGGER update_stores_updated_at
    BEFORE UPDATE ON stores
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Commento
COMMENT ON TABLE stores IS 'Catalogo negozi normalizzati con dati completi';
COMMENT ON COLUMN stores.is_mock IS 'TRUE per negozi mock creati quando dati mancanti/illeggibili';
COMMENT ON COLUMN stores.data_quality_score IS 'Score basato su quanti campi sono compilati (0=solo nome, 1=tutti i dati)';

-- ===================================
-- MOCK STORE di default
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
-- AGGIORNA TABELLE ESISTENTI
-- ===================================

-- Aggiungi colonna store_id a receipts
ALTER TABLE receipts 
    ADD COLUMN store_id UUID REFERENCES stores(id) ON DELETE SET NULL;

-- Crea indice
CREATE INDEX idx_receipts_store ON receipts(store_id);

-- Aggiungi colonna store_id a purchase_history
ALTER TABLE purchase_history
    ADD COLUMN store_id UUID REFERENCES stores(id) ON DELETE SET NULL;

-- Crea indice
CREATE INDEX idx_purchase_history_store ON purchase_history(store_id);

-- Nota: Manteniamo store_name come testo per backward compatibility
-- Ma ora useremo store_id come riferimento principale

-- ===================================
-- FUNZIONE: Calcola Data Quality Score
-- ===================================

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

-- ===================================
-- TRIGGER: Aggiorna data_quality_score automaticamente
-- ===================================

CREATE OR REPLACE FUNCTION update_store_data_quality()
RETURNS TRIGGER AS $$
BEGIN
    NEW.data_quality_score := calculate_store_data_quality(NEW);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_store_data_quality
    BEFORE INSERT OR UPDATE ON stores
    FOR EACH ROW
    EXECUTE FUNCTION update_store_data_quality();

-- ===================================
-- VIEW: Stores con statistiche
-- ===================================

CREATE OR REPLACE VIEW stores_with_stats AS
SELECT 
    s.*,
    COUNT(DISTINCT r.id) as actual_receipts,
    AVG(r.total_amount) as actual_avg_amount,
    MAX(r.receipt_date) as actual_last_receipt,
    COUNT(DISTINCT r.household_id) as unique_households
FROM stores s
LEFT JOIN receipts r ON r.store_id = s.id
GROUP BY s.id;

COMMENT ON VIEW stores_with_stats IS 'Stores con statistiche calcolate in real-time';
