-- ===================================
-- Migration: MVP 005 - Vector Search Function
-- ===================================
-- Descrizione: Crea funzione RPC per vector search con pgvector
-- Eseguire su: Database production/staging
-- Prerequisiti: pgvector extension, indice HNSW esistente
-- Performance target: <100ms per query
-- ===================================

-- ===================================
-- FUNCTION: search_similar_products
-- ===================================
-- Cerca prodotti simili usando vector similarity
-- Ritorna prodotti ordinati per similarity score
CREATE OR REPLACE FUNCTION search_similar_products(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.6,
  match_count int DEFAULT 10
) RETURNS TABLE (
  id uuid,
  canonical_name text,
  brand text,
  category text,
  subcategory text,
  size text,
  unit_type text,
  tags text[],
  verification_status text,
  similarity float
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    np.id,
    np.canonical_name,
    np.brand,
    np.category,
    np.subcategory,
    np.size,
    np.unit_type,
    np.tags,
    np.verification_status,
    -- Calcola similarity usando cosine distance
    -- 1 - (embedding <=> query_embedding) = cosine similarity
    1 - (np.embedding <=> query_embedding) AS similarity
  FROM normalized_products np
  WHERE np.embedding IS NOT NULL
    AND 1 - (np.embedding <=> query_embedding) > match_threshold
  ORDER BY np.embedding <=> query_embedding
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ===================================
-- VERIFICA FUNZIONE CREATA
-- ===================================
-- Testa la funzione con un embedding di test
-- (Commentato per evitare errori se non ci sono prodotti)
/*
SELECT * FROM search_similar_products(
  query_embedding := '[0,0,0,...]'::vector(1536),
  match_threshold := 0.5,
  match_count := 5
);
*/

-- ===================================
-- GRANT PERMISSIONS
-- ===================================
-- Permetti accesso alla funzione per service role
GRANT EXECUTE ON FUNCTION search_similar_products(vector(1536), float, int) TO service_role;

-- ===================================
-- ROLLBACK PLAN
-- ===================================
-- Se necessario rollback:
-- DROP FUNCTION IF EXISTS search_similar_products(vector(1536), float, int);
