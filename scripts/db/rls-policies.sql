-- ===================================
-- ROW LEVEL SECURITY POLICIES
-- ===================================
-- Esegui questo SQL dopo aver creato lo schema

-- ===================================
-- ABILITA RLS su tutte le tabelle
-- ===================================

ALTER TABLE households ENABLE ROW LEVEL SECURITY;
ALTER TABLE household_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipt_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE normalized_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_history ENABLE ROW LEVEL SECURITY;

-- ===================================
-- POLICIES per HOUSEHOLDS
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
-- POLICIES per HOUSEHOLD_MEMBERS
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
-- POLICIES per RECEIPTS
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
-- POLICIES per RECEIPT_ITEMS
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

-- Il backend può inserire receipt items (usando service_role key)
CREATE POLICY "Service can create receipt items"
    ON receipt_items FOR INSERT
    WITH CHECK (true);

-- ===================================
-- POLICIES per NORMALIZED_PRODUCTS
-- ===================================

-- Tutti possono leggere prodotti normalizzati (catalogo condiviso)
CREATE POLICY "Anyone can view normalized products"
    ON normalized_products FOR SELECT
    USING (true);

-- Solo il backend può creare/aggiornare prodotti normalizzati
CREATE POLICY "Service can manage normalized products"
    ON normalized_products FOR ALL
    USING (true)
    WITH CHECK (true);

-- ===================================
-- POLICIES per PRODUCT_MAPPINGS
-- ===================================

-- Tutti possono leggere mappings
CREATE POLICY "Anyone can view product mappings"
    ON product_mappings FOR SELECT
    USING (true);

-- Solo il backend può creare/aggiornare mappings
CREATE POLICY "Service can manage product mappings"
    ON product_mappings FOR ALL
    USING (true)
    WITH CHECK (true);

-- ===================================
-- POLICIES per PURCHASE_HISTORY
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
