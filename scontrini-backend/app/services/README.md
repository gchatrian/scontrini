# Services - Product Normalization Pipeline

Servizi per la pipeline multi-stage di normalizzazione prodotti.

## Architettura

```
ProductNormalizerV2
    ├── CacheService (Tier 1 + Tier 2 lookup)
    ├── VectorSearchService (Semantic search)
    ├── ContextService (Household + Store context)
    ├── ValidationService (Quality scoring)
    └── CacheUpdateService (Cache refresh)
         └── EmbeddingService (OpenAI embeddings)
```

## Servizi

### EmbeddingService
Wrapper per OpenAI embeddings con caching e retry logic.

**Funzioni:**
- `generate_embedding(text)`: genera embedding singolo
- `generate_batch(texts)`: genera batch embeddings
- `get_usage_stats()`: statistiche uso (tokens, costi)
- `clear_cache()`: svuota cache

**Configurazione:**
- `OPENAI_EMBEDDING_MODEL`: text-embedding-ada-002
- `OPENAI_EMBEDDING_CACHE_SIZE`: 1000 items
- `OPENAI_EMBEDDING_MAX_RETRIES`: 3
- `OPENAI_EMBEDDING_COST_PER_1K`: $0.0001

### CacheService
Smart cache 2-tier con confidence boosting.

**Funzioni:**
- `get_cached_product(raw_name, store_name, current_price)`: lookup cache

**Logica:**
1. **Tier 1** (user-verified): confidence base 0.90 + boost (max 0.97)
   - Boost: +3% se ≥3 households, +2% se ≥10 uses, +2% se <90 giorni
2. **Tier 2** (auto-verified): confidence 0.85 (fallback)
3. **Price coherence**: -20% confidence se prezzo ±30% fuori range

**Configurazione:**
- `CACHE_BASE_CONFIDENCE`: 0.90
- `CACHE_PRICE_TOLERANCE`: 0.30 (±30%)
- `CACHE_MAX_CONFIDENCE`: 0.97

### VectorSearchService
Ricerca semantica con pgvector HNSW.

**Funzioni:**
- `search_similar_products(raw_name, store_name, limit)`: ricerca singola
- `search_batch(raw_names, store_name)`: ricerca batch

**Boosting:**
- +5% se prodotto user-verified
- +3% se stesso negozio

**Configurazione:**
- `VECTOR_SEARCH_SIMILARITY_THRESHOLD`: 0.75
- `VECTOR_SEARCH_MAX_RESULTS`: 10

### ContextService
Arricchimento dati con storico household e store.

**Funzioni:**
- `get_household_context(household_id, product_id)`: storico household
- `get_store_popularity(store_name, product_id)`: popolarità in negozio
- `get_enriched_context(household_id, product_id, store_name)`: contesto completo
- `get_price_history(household_id, product_id)`: storico prezzi

**Context Score (0-1):**
- 60% componente household (storia, frequenza, numero acquisti)
- 40% componente store (popolarità, households, totale acquisti)

**Configurazione:**
- `CONTEXT_RECENT_PURCHASES_DAYS`: 90
- `CONTEXT_MIN_FREQUENCY_THRESHOLD`: 3 acquisti
- `CONTEXT_POPULAR_MIN_HOUSEHOLDS`: 2

### ValidationService
Validazione qualità normalizzazioni con scoring.

**Funzioni:**
- `validate_normalization(...)`: valida singola normalizzazione
- `validate_batch(normalizations)`: valida batch
- `get_validation_summary(validations)`: statistiche aggregate

**Output:**
```python
{
    "is_valid": bool,
    "final_confidence": float,  # 0-1
    "confidence_level": "high" | "medium" | "low",
    "warnings": [str],
    "flags": {
        "missing_fields": bool,
        "price_anomaly": bool,
        "low_context": bool,
        "needs_review": bool
    },
    "recommendations": [str]
}
```

**Logica Confidence:**
- Base confidence (da cache/vector/llm)
- -10% se campi mancanti
- -15% se prezzo anomalo (>±30%)
- +5% se context_score ≥0.7

**Livelli:**
- HIGH: ≥0.90
- MEDIUM: 0.70-0.89
- LOW: <0.70

**Configurazione:**
- `VALIDATION_HIGH_CONFIDENCE_THRESHOLD`: 0.90
- `VALIDATION_LOW_CONFIDENCE_THRESHOLD`: 0.70

### CacheUpdateService
Aggiornamento cache e materialized views.

**Funzioni:**
- `update_product_mapping(...)`: crea/aggiorna mapping
- `create_normalized_product(...)`: crea prodotto con embedding
- `update_normalized_product(product_id, updates)`: aggiorna prodotto
- `refresh_cache_stats()`: refresh materialized view
- `create_purchase_history(...)`: inserisce purchase record
- `batch_create_mappings(mappings)`: batch insert mappings
- `batch_create_purchases(purchases)`: batch insert purchases

**Logica intelligente:**
- Update mapping solo se nuovo confidence > esistente
- Generazione automatica embeddings per nuovi prodotti
- Error handling per batch operations

## Pipeline Multi-Stage

### ProductNormalizerV2

```python
result = await product_normalizer_v2.normalize_product(
    raw_product_name="COCA 1.5L",
    household_id="uuid",
    store_name="Esselunga",
    price=1.49
)
```

**Fasi:**
1. **PHASE 0 - Cache Lookup**: Tier 1 → Tier 2
2. **PHASE 1 - Vector Search**: Se cache miss
3. **PHASE 2 - LLM Normalization**: Se vector miss
4. **PHASE 3 - Validation**: Sempre
5. **PHASE 4 - Cache Update**: Per nuovi prodotti

**Output:**
```python
{
    "success": True,
    "normalized_product_id": "uuid",
    "canonical_name": "Coca Cola 1.5L",
    "brand": "Coca Cola",
    "category": "Bevande",
    "subcategory": "Bibite Gassate",
    "size": "1.5",
    "unit_type": "l",
    "tags": ["bibita", "gassata"],
    "confidence": 0.92,
    "confidence_level": "high",
    "source": "cache_tier1" | "cache_tier2" | "vector_search" | "llm",
    "created_new": False,
    "validation": {...},
    "context": {...}
}
```

## Performance Target

- Cache hit: <50ms
- Vector search: <100ms
- LLM normalization: <3s
- Validation: <10ms

## Cost Analysis

**Cache hit**: $0 (gratis)
**Vector search**: $0.0001 per query (embedding generation)
**LLM normalization**: ~$0.002 per prodotto (GPT-4o-mini + embeddings)

**Target**: 80% cache hit rate → costo medio $0.0004 per prodotto
