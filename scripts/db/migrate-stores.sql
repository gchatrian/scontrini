-- ===================================
-- MIGRATION: Popola stores da receipts esistenti
-- ===================================
-- Esegui DOPO aver creato la tabella stores

-- Step 1: Crea stores da receipts con store_name univoci
INSERT INTO stores (name, chain, address_full, store_type, is_mock, branch_name)
SELECT DISTINCT
    COALESCE(store_name, 'Negozio Sconosciuto') as name,
    COALESCE(store_name, 'Sconosciuto') as chain,
    COALESCE(store_address, 'Indirizzo non disponibile') as address_full,
    'supermarket' as store_type,
    CASE 
        WHEN store_name IS NULL THEN TRUE 
        ELSE FALSE 
    END as is_mock,
    CASE 
        WHEN store_address IS NOT NULL 
        THEN COALESCE(store_name, 'Negozio') || ' - ' || store_address
        ELSE COALESCE(store_name, 'Negozio Sconosciuto')
    END as branch_name
FROM receipts
WHERE store_name IS NOT NULL
ON CONFLICT DO NOTHING;

-- Step 2: Aggiorna receipts con store_id
UPDATE receipts r
SET store_id = s.id
FROM stores s
WHERE r.store_name = s.name
  AND r.store_id IS NULL;

-- Step 3: Assegna mock store ai receipts senza store
UPDATE receipts
SET store_id = '00000000-0000-0000-0000-000000000000'
WHERE store_id IS NULL;

-- Step 4: Aggiorna purchase_history con store_id
UPDATE purchase_history ph
SET store_id = r.store_id
FROM receipts r
WHERE ph.receipt_id = r.id
  AND ph.store_id IS NULL;

-- Step 5: Aggiorna statistiche stores
UPDATE stores s
SET 
    total_receipts = (
        SELECT COUNT(*) 
        FROM receipts r 
        WHERE r.store_id = s.id
    ),
    avg_receipt_amount = (
        SELECT AVG(total_amount) 
        FROM receipts r 
        WHERE r.store_id = s.id AND total_amount IS NOT NULL
    ),
    last_receipt_date = (
        SELECT MAX(receipt_date) 
        FROM receipts r 
        WHERE r.store_id = s.id AND receipt_date IS NOT NULL
    );

-- Verifica risultati
SELECT 
    'Stores creati' as metric,
    COUNT(*) as count
FROM stores
UNION ALL
SELECT 
    'Receipts collegati' as metric,
    COUNT(*) as count
FROM receipts
WHERE store_id IS NOT NULL
UNION ALL
SELECT 
    'Purchase history aggiornati' as metric,
    COUNT(*) as count
FROM purchase_history
WHERE store_id IS NOT NULL;
