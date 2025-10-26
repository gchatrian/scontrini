# MVP Implementation Roadmap - Product Recognition System

**Documento**: Roadmap MVP - Core Features Only
**Versione**: 1.0
**Data**: Ottobre 2025

---

## 📋 Indice

1. [MVP Scope & Obiettivi](#1-mvp-scope--obiettivi)
2. [Architettura Core](#2-architettura-core)
3. [Setup & Prerequisites](#3-setup--prerequisites)
4. [Phase 1: Database Foundation](#4-phase-1-database-foundation)
5. [Phase 2: Smart Cache](#5-phase-2-smart-cache)
6. [Phase 3: Semantic Recognition](#6-phase-3-semantic-recognition)
7. [Phase 4: Validation & Feedback](#7-phase-4-validation--feedback)
8. [Phase 5: Testing & Launch](#8-phase-5-testing--launch)
9. [Post-Launch](#9-post-launch)
10. [Success Metrics](#10-success-metrics)

---

## 1. MVP Scope & Obiettivi

### 1.1 Cosa Implementeremo (MVP)

Sistema minimo per riconoscere prodotti da scontrini con:
- **Cache intelligente** per prodotti già visti
- **Vector search semantico** per prodotti nuovi
- **Validazione automatica** con confidence scoring
- **User feedback** per correggere errori e migliorare sistema

### 1.2 Cosa NON includeremo nell'MVP

- Dashboard analytics complesse
- Bulk import scontrini
- Barcode scanning integration
- Multi-language support
- Advanced anomaly detection (solo price coherence base)
- A/B testing framework
- ML model fine-tuning

### 1.3 Core Components

**PHASE 0: Smart Cache** (70% use case dopo 3 mesi)
- Exact match su `product_mappings` (raw_name + store)
- Multi-tier: verified cache vs auto-verified fallback
- Price coherence check
- Confidence 0.90 se hit

**STEP 1: Semantic Recognition** (se cache miss)
- Generate embedding tramite OpenAI Ada
- Vector search con pgvector
- Context enrichment (household history, store stats)
- LLM reasoning con GPT-4o-mini
- Confidence-based auto-approval o review flagging

**STEP 2: Validation**
- Source-based validation (cache vs semantic)
- Price coherence check (±30% tolerance)
- Confidence score calculation per prodotto
- Warning flags per confidence <0.70 (high priority review)
- Tutti i prodotti mostrati all'utente per review obbligatoria
- User feedback handling (confirm/correct)

### 1.4 Success Criteria MVP

- **Performance**: P95 latency <600ms (full pipeline), cache <30ms
- **Accuracy**: Overall >85%, cache hit >95%
- **Cost**: <$0.0002 per prodotto (full pipeline)
- **User Correction Rate**: <20% (utente modifica solo 20% dei prodotti proposti)
- **System Stability**: No critical bugs, uptime >99%

---

## 2. Architettura Core

### 2.1 Flusso Principale

```
┌─────────────────────────────────────────────────────┐
│                 PRODUCT RECOGNITION                  │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
          ┌───────────────────────────────┐
          │  PHASE 0: Smart Cache Lookup  │
          │  (product_mappings query)     │
          └───────────────────────────────┘
                    │           │
              Hit   │           │  Miss
                    │           │
         ┌──────────┘           └──────────┐
         ▼                                 ▼
    ┌─────────┐              ┌──────────────────────┐
    │ RETURN  │              │  STEP 1: Semantic    │
    │ (0.90)  │              │  - Generate Embedding│
    └─────────┘              │  - Vector Search     │
                             │  - Context Enrichment│
                             │  - LLM Reasoning     │
                             └──────────────────────┘
                                        │
                                        ▼
                             ┌──────────────────────┐
                             │  STEP 2: Validation  │
                             │  - Confidence Check  │
                             │  - Price Coherence   │
                             │  - Auto-approve or   │
                             │    Flag for Review   │
                             └──────────────────────┘
                                        │
                                        ▼
                             ┌──────────────────────┐
                             │  Cache Update        │
                             │  User Feedback Loop  │
                             └──────────────────────┘
```

### 2.2 Database Schema Essenziale

**Tabelle Core**:
```sql
-- Prodotti normalizzati (catalogo master)
normalized_products (
  id UUID PRIMARY KEY,
  canonical_name TEXT UNIQUE NOT NULL,
  brand TEXT,
  category TEXT,
  subcategory TEXT,
  size TEXT,
  unit_type TEXT,
  embedding vector(1536),  -- OpenAI Ada embedding
  verification_status TEXT CHECK (status IN
    ('auto_verified', 'pending_review', 'user_verified', 'rejected')),
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Mappature raw_name → normalized_product
product_mappings (
  id UUID PRIMARY KEY,
  raw_name TEXT NOT NULL,
  normalized_product_id UUID REFERENCES normalized_products,
  store_name TEXT,
  confidence_score DOUBLE PRECISION CHECK (0 <= score <= 1),
  verified_by_user BOOLEAN DEFAULT FALSE,
  requires_manual_review BOOLEAN DEFAULT FALSE,
  interpretation_details JSONB,
  reviewed_at TIMESTAMPTZ,
  reviewed_by UUID REFERENCES auth.users,
  created_at TIMESTAMPTZ,
  UNIQUE(raw_name, store_name)  -- Un mapping per combinazione
)

-- Purchase history (per context enrichment)
purchase_history (
  id UUID PRIMARY KEY,
  household_id UUID NOT NULL,
  normalized_product_id UUID REFERENCES normalized_products,
  store_name TEXT,
  purchase_date DATE NOT NULL,
  quantity NUMERIC,
  unit_price NUMERIC,
  total_price NUMERIC,
  created_at TIMESTAMPTZ
)
```

### 2.3 Tech Stack

**Backend Services**:
- Language: TypeScript/Node.js o Python
- Database: PostgreSQL via Supabase (pgvector extension)
- AI Services: OpenAI (Ada embeddings + GPT-4o-mini)
- Caching: In-memory (Node) + Database materialized view

**Monitoring (Basic)**:
- Structured logging (JSON)
- Supabase dashboard
- Basic alerts (error rate, latency)

---

## 3. Setup & Prerequisites

### 3.1 Environment Setup

**Necessario Prima di Iniziare**:
- ✅ Supabase project attivo
- ✅ OpenAI API key con credito
- ✅ Ambiente staging separato da production
- ✅ Git repository
- ✅ Database client (Supabase Studio, DBeaver, pgAdmin)

**Environment Variables**:
```env
# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_ANON_KEY=

# OpenAI
OPENAI_API_KEY=

# Config
CACHE_CONFIDENCE_THRESHOLD=0.90
SEMANTIC_AUTO_APPROVE_THRESHOLD=0.90
PRICE_COHERENCE_TOLERANCE=0.30  # ±30%
```

### 3.2 Pre-Development Tasks

**Task: pgvector Spike**
- Abilita extension `pgvector` su database
- Test query similarity su dataset sample
- Decide index type (HNSW raccomandato per <100k vettori)
- Measure query performance (<50ms target)

**Task: OpenAI Integration Test**
- Test embedding generation (10 sample product names)
- Test GPT-4o-mini call con prompt reasoning
- Verify response time (<300ms embedding, <400ms LLM)
- Setup error handling (rate limits, timeouts)

**Task: Logging Setup**
- Configure structured logging (Winston/Pino o Python logging)
- Define log events: `cache_hit`, `cache_miss`, `recognition_success`, `recognition_failure`
- Setup log levels (debug, info, warn, error)

---

## 4. Phase 1: Database Foundation

### 4.1 Schema Implementation

**Task: Core Tables**
- Create `normalized_products` con colonna `embedding vector(1536)`
- Create `product_mappings` con composite index `(raw_name, store_name)`
- Create `purchase_history` con index su `(household_id, normalized_product_id)`
- Add triggers: `update_updated_at_column()` su tabelle con `updated_at`

**Task: Vector Index**
- Create HNSW index su `normalized_products.embedding`:
  ```sql
  CREATE INDEX idx_products_embedding ON normalized_products
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  ```
- Test query performance con `EXPLAIN ANALYZE`
- Target: <50ms per vector search

**Task: Cache Indexes**
- Composite index: `(raw_name, store_name, verified_by_user)` su `product_mappings`
- Partial index: `WHERE verified_by_user = true` per Tier 1 cache
- Index: `(raw_name, store_name, confidence_score)` per Tier 2 fallback
- Target: <15ms per cache lookup

### 4.2 Materialized View per Cache Stats

**Task: product_cache_stats View**
```sql
CREATE MATERIALIZED VIEW product_cache_stats AS
SELECT
  pm.raw_name,
  pm.store_name,
  pm.normalized_product_id,
  COUNT(*) as usage_count,
  COUNT(DISTINCT ph.household_id) as verified_by_households,
  AVG(ph.unit_price) as avg_price,
  MAX(ph.purchase_date) as last_used
FROM product_mappings pm
JOIN purchase_history ph ON ph.normalized_product_id = pm.normalized_product_id
WHERE pm.verified_by_user = true
GROUP BY pm.raw_name, pm.store_name, pm.normalized_product_id;

CREATE INDEX idx_cache_stats_lookup ON product_cache_stats(raw_name, store_name);
```

**Task: Refresh Strategy**
- Setup auto-refresh (pg_cron ogni ora) OR
- Create API endpoint per manual refresh
- Use `REFRESH MATERIALIZED VIEW CONCURRENTLY` (non-blocking)

### 4.3 Database Function: Cache Lookup

**Task: get_cached_product Function**
```sql
CREATE OR REPLACE FUNCTION get_cached_product(
  p_raw_name TEXT,
  p_store_name TEXT,
  p_current_price NUMERIC
) RETURNS JSONB AS $$
DECLARE
  v_result JSONB;
BEGIN
  -- Query cache stats per best match
  SELECT jsonb_build_object(
    'product_id', normalized_product_id,
    'usage_count', usage_count,
    'verified_by_households', verified_by_households,
    'avg_price', avg_price,
    'last_used', last_used,
    'price_coherent', ABS(p_current_price - avg_price) / NULLIF(avg_price, 0) <= 0.30
  )
  INTO v_result
  FROM product_cache_stats
  WHERE raw_name = p_raw_name AND store_name = p_store_name
  ORDER BY usage_count DESC, last_used DESC
  LIMIT 1;

  RETURN v_result;
END;
$$ LANGUAGE plpgsql;
```

### 4.4 Data Backfill (se database esistente)

**Task: Generate Embeddings for Existing Products**
- Script batch per generare embeddings per prodotti senza embedding
- Batch size: 100 prodotti per batch (rate limiting OpenAI)
- Include retry logic + exponential backoff
- Progress tracking + resume capability
- Validate embeddings dimensionality (1536) dopo generation

**Deliverables Phase 1**:
- ✅ Database schema completo
- ✅ Indexes ottimizzati (vector + cache)
- ✅ Materialized view funzionante
- ✅ Cache lookup function testata
- ✅ Embeddings backfill completato (se applicabile)
- ✅ Performance targets raggiunti (cache <15ms, vector <50ms)

---

## 5. Phase 2: Smart Cache

### 5.1 Cache Service Implementation

**Task: CacheService Class**
```typescript
class CacheService {
  async getCachedProduct(
    rawName: string,
    storeName: string,
    currentPrice: number
  ): Promise<CacheHit | null> {
    // 1. Query get_cached_product function
    // 2. Parse JSONB response
    // 3. Calculate confidence boost (0.90 base + boosts)
    // 4. Check price coherence
    // 5. Return CacheHit or null
  }
}

interface CacheHit {
  productId: string
  confidence: number  // 0.90-0.97
  source: 'verified_cache' | 'auto_cache'
  priceCoherent: boolean
  metadata: {
    usageCount: number
    verifiedByHouseholds: number
    avgPrice: number
    lastUsed: Date
  }
}
```

**Task: Tier 1 Cache (Verified)**
- Query `get_cached_product` function
- Se hit: confidence = 0.90 (base)
- Boost logic:
  - +0.03 se `verified_by_households >= 3`
  - +0.02 se `usage_count >= 10`
  - +0.02 se `last_used < 90 giorni`
  - Cap a 0.97 max
- Log `cache_hit` event

**Task: Tier 2 Fallback (Auto-Verified)**
- Se Tier 1 miss: query `product_mappings` con `verified_by_user = false`
- Filter: `confidence_score >= 0.85`
- Prendi result con confidence più alto
- Apply penalty: `confidence = original * 0.95`
- Source: `'auto_cache'`
- Log `cache_hit_tier2` event

**Task: Price Coherence Validation**
- Calcola deviation: `abs(current - avg) / avg`
- Se deviation > 0.30 (30%):
  - Downgrade confidence a 0.70
  - Flag `priceCoherent = false`
  - Log `price_outlier` event
- Include `suggested_price` (avg_price) in metadata

### 5.2 API Integration

**Task: Recognition Endpoint**
```typescript
POST /api/recognition/product
Request: {
  raw_name: string
  store: string
  price: number
  household_id: string
}

Response: {
  product_id: string
  canonical_name: string
  brand: string | null
  category: string
  confidence: number
  source: 'verified_cache' | 'auto_cache' | 'semantic_search'
  validation: {
    status: 'AUTO_VERIFIED' | 'PENDING_REVIEW'
    price_coherent: boolean
    requires_review: boolean
  }
  metadata: object
}
```

**Implementation**:
- Call `CacheService.getCachedProduct()` first
- Se cache hit: return subito (fast path <30ms)
- Se cache miss: proceed to semantic search (next phase)
- Include `source` field in response
- Log latency per ogni request

### 5.3 Testing

**Task: Unit Tests - CacheService**
- Test Tier 1 cache hit scenario
- Test Tier 2 fallback scenario
- Test cache miss scenario
- Test price coherence (in range, outlier)
- Test confidence boost calculation
- Mock Supabase client

**Task: Integration Tests - Cache + DB**
- Setup test database con fixture data
- Test end-to-end cache lookup
- Test materialized view refresh
- Test performance (100 concurrent queries)
- Measure cache hit rate su test dataset

**Deliverables Phase 2**:
- ✅ CacheService implementato (Tier 1 + Tier 2)
- ✅ Price coherence validation attiva
- ✅ API endpoint integrato
- ✅ Unit tests coverage >80%
- ✅ Performance: cache lookup <30ms P95
- ✅ Monitoring: cache hit rate tracciata

---

## 6. Phase 3: Semantic Recognition

### 6.1 Embedding Service

**Task: OpenAI Embeddings Wrapper**
```typescript
class EmbeddingService {
  async generateEmbedding(text: string): Promise<number[]> {
    // 1. Call OpenAI API (text-embedding-ada-002)
    // 2. Return 1536-dim vector
    // 3. Retry logic con exponential backoff
    // 4. In-memory LRU cache (max 1000 entries)
    // 5. Track costs
  }

  async generateBatch(texts: string[]): Promise<Map<string, number[]>> {
    // Batch generation (max 2048 texts per call)
    // Handle partial failures
  }
}
```

**Implementation**:
- Model: `text-embedding-ada-002`
- Dimensionality: 1536
- Retry: 3 attempts con exponential backoff
- Cache: LRU 1000 entries (evita duplicate calls)
- Cost tracking: $0.0001 per embedding
- Target latency: <200ms P95

### 6.2 Vector Search Service

**Task: VectorSearchService Implementation**
```typescript
class VectorSearchService {
  async searchSimilar(
    embedding: number[],
    limit: number = 5
  ): Promise<Candidate[]> {
    // 1. Query normalized_products con operator <=>
    // 2. Calcola similarity: 1 - distance
    // 3. Filter rejected products
    // 4. Order by similarity DESC
    // 5. Return top K candidates
  }
}

interface Candidate {
  productId: string
  canonicalName: string
  brand: string | null
  category: string
  similarity: number  // 0-1
  purchaseStats: {
    timesPurchased: number
    avgPrice: number
    userBoughtBefore: boolean
  }
}
```

**Task: Candidate Enrichment**
- JOIN con `purchase_history` per aggregations:
  - `times_purchased` (global)
  - `avg_price`
  - `user_bought_before` (per household corrente)
- Calcola `popularity_score` basato su global purchases
- Weighted ranking: `similarity * 0.7 + popularity * 0.3`
- Target latency: <50ms

### 6.3 Context Enrichment

**Task: ContextService**
```typescript
class ContextService {
  async enrichCandidates(
    candidates: Candidate[],
    householdId: string,
    storeName: string,
    currentPrice: number
  ): Promise<EnrichedCandidate[]> {
    // 1. Fetch household history
    // 2. Fetch store stats
    // 3. Calculate context_match_score per candidato:
    //    +0.5 se user_bought_before
    //    +0.3 se popular_at_store
    //    +0.2 se price vicino a avg_price
    // 4. Return candidates arricchiti e ranked
  }
}
```

**Household History**:
- Query `purchase_history` per vedere quali candidati household ha comprato
- Stats: `purchase_count`, `last_purchase_date`, `avg_price`

**Store Context**:
- Query `purchase_history` JOIN `receipts` per filtrare per store
- Stats: `sold_count_at_store`, `avg_price_at_store`
- Flag: `popular_at_store` (sold_count > threshold es: 10)

### 6.4 LLM Reasoning Service

**Task: Prompt Engineering**
```typescript
const SYSTEM_PROMPT = `
Sei un esperto di prodotti retail italiano.
Il tuo compito è identificare il prodotto corretto da uno scontrino.

Considera:
- Similarità semantica del nome
- Storico acquisti dell'utente
- Popolarità del prodotto nel negozio
- Coerenza del prezzo

Output JSON:
{
  "decision": "existing_product" | "new_product",
  "product_id": "uuid",  // se existing
  "confidence": 0.0-1.0,
  "reasoning": "Spiegazione decisione",
  "new_product": {  // se new_product
    "canonical_name": "...",
    "brand": "...",
    "category": "...",
    "size": "...",
    "unit_type": "..."
  }
}
`;
```

**Task: LLMReasoningService Implementation**
```typescript
class LLMReasoningService {
  async selectProduct(
    rawName: string,
    candidates: EnrichedCandidate[],
    context: Context
  ): Promise<Decision> {
    // 1. Build prompt con system + user message
    // 2. Call OpenAI GPT-4o-mini (response_format: json_object)
    // 3. Parse JSON response
    // 4. Validate structure
    // 5. Handle errors (retry if malformed JSON)
    // 6. Track costs
  }
}
```

**Configuration**:
- Model: `gpt-4o-mini`
- Temperature: 0.1 (deterministic)
- Response format: `json_object`
- Max tokens: 500
- Retry: 2 attempts
- Cost: ~$0.0001 per call
- Target latency: <400ms

**Task: New Product Creation**
- Se LLM decision = `"new_product"`:
  - Validate `new_product` object (required fields)
  - Check canonical_name non duplicato (trigram similarity)
  - Generate embedding per nuovo canonical_name
  - Insert in `normalized_products` con `verification_status = 'auto_verified'`
  - Create mapping in `product_mappings`

### 6.5 Pipeline Orchestration

**Task: ProductRecognitionService**
```typescript
class ProductRecognitionService {
  async recognizeProduct(
    rawName: string,
    context: RecognitionContext
  ): Promise<RecognitionResult> {
    // PIPELINE:
    // 1. Check cache (CacheService)
    // 2. Se miss: generate embedding (EmbeddingService)
    // 3. Vector search (VectorSearchService)
    // 4. Context enrichment (ContextService)
    // 5. LLM reasoning (LLMReasoningService)
    // 6. Return RecognitionResult

    // Track timing per ogni fase
    // Log pipeline execution
    // Handle errors gracefully
  }
}

interface RecognitionResult {
  productId: string
  confidence: number
  source: 'verified_cache' | 'auto_cache' | 'semantic_search'
  reasoning: string | null
  timing: {
    cache: number
    embedding: number
    vectorSearch: number
    context: number
    llm: number
    total: number
  }
}
```

**Task: API Endpoint Integration**
- Modifica POST `/api/recognition/product` per chiamare `ProductRecognitionService`
- Parse request body + validate input
- Map `RecognitionResult` a API response format
- Include metadata (confidence, reasoning, timing)
- Handle errors e return HTTP status codes appropriati

### 6.6 Testing

**Task: Unit Tests - Services**
- EmbeddingService: test generation, batch, cache, retry
- VectorSearchService: test search, enrichment, filters
- ContextService: test household history, store stats
- LLMReasoningService: test existing product, new product, malformed JSON
- Mock OpenAI API per unit tests

**Task: E2E Integration Tests**
- Test full pipeline: cache miss → semantic search → return
- Test con prodotto ambiguo (multiple candidati simili)
- Test con prodotto completamente nuovo (new product creation)
- Test error scenarios (OpenAI down, DB down)
- Measure accuracy su test set (100 prodotti reali)
- Target accuracy: >85%

**Deliverables Phase 3**:
- ✅ EmbeddingService funzionante
- ✅ VectorSearchService con enrichment
- ✅ ContextService (household + store)
- ✅ LLMReasoningService con prompt ottimizzati
- ✅ New product creation logic
- ✅ ProductRecognitionService orchestrator
- ✅ API endpoint completo
- ✅ E2E tests accuracy >85%
- ✅ Performance: full pipeline <600ms P95

---

## 7. Phase 4: Validation & Feedback

### 7.1 Validation Service

**Task: ValidationService Implementation**
```typescript
class ValidationService {
  validate(
    result: RecognitionResult,
    context: ValidationContext
  ): ValidationResult {
    // Source-based validation:
    if (result.source === 'verified_cache') {
      return this.validateCacheHit(result, context)
    } else {
      return this.validateSemanticResult(result, context)
    }
  }
}

interface ValidationResult {
  status: 'AUTO_VERIFIED' | 'PENDING_REVIEW'
  requiresReview: boolean
  checks: ValidationCheck[]
  suggestedActions: string[]
}
```

**Task: Cache Hit Validation**
- Check 1: Price coherence (già fatto in cache service)
- Check 2: Recency (last_used < 180 giorni)
- Se entrambi pass → `AUTO_VERIFIED` con confidence 0.90
- Se price outlier → `PENDING_REVIEW` con confidence 0.70
- Fast validation: <5ms

**Task: Semantic Result Validation**
- Threshold-based:
  - Confidence ≥ 0.90 → `AUTO_VERIFIED`
  - Confidence 0.70-0.89 → `PENDING_REVIEW` (low priority)
  - Confidence < 0.70 → `PENDING_REVIEW` (high priority)
- Extra checks per borderline (0.85-0.90):
  - Verify `semantic_similarity > 0.80`
  - Verify `context_match_score > 0.60`
  - Se fail → downgrade a `PENDING_REVIEW`

### 7.2 Cache Update Logic

**Task: CacheUpdateService**
```typescript
class CacheUpdateService {
  async updateCache(
    result: RecognitionResult,
    validation: ValidationResult
  ): Promise<void> {
    // Logic:
    // - Se source = 'semantic_search' E status = 'AUTO_VERIFIED':
    //   → INSERT mapping con verified_by_user = false
    // - Use INSERT ON CONFLICT DO UPDATE per handle duplicates
    // - Update confidence_score se nuovo score > vecchio
    // - Log cache_update event
  }
}
```

**Implementation**:
```sql
INSERT INTO product_mappings (raw_name, normalized_product_id, store_name, confidence_score)
VALUES ($1, $2, $3, $4)
ON CONFLICT (raw_name, store_name)
DO UPDATE SET
  confidence_score = GREATEST(product_mappings.confidence_score, EXCLUDED.confidence_score),
  updated_at = NOW();
```

**Task: Materialized View Refresh**
- Decide strategy: batch refresh (ogni N updates) o throttled refresh
- Use `REFRESH MATERIALIZED VIEW CONCURRENTLY` (non-blocking)
- Monitor refresh time (target <500ms)

### 7.3 User Feedback Loop

**Task: Feedback API Endpoints**
```typescript
POST /api/feedback/approve-mapping
Request: { mapping_id: string }
Response: { success: boolean, product_id: string }

POST /api/feedback/reject-mapping
Request: { mapping_id: string, reason?: string, corrected_product_id?: string }
Response: { success: boolean }

POST /api/feedback/correct-mapping
Request: { mapping_id: string, corrections: Partial<Product> }
Response: { success: boolean, product_id: string }
```

**Task: Approve Mapping Handler**
- Use `approve_product_mapping()` function (RPC)
- UPDATE `product_mappings`: `verified_by_user = true`, `confidence = 1.0`
- UPDATE `normalized_products`: `verification_status = 'user_verified'`
- Increment `verified_by_households` counter
- Set `reviewed_at`, `reviewed_by`
- Return updated mapping

**Task: Reject Mapping Handler**
- Use `reject_product_mapping()` function (RPC)
- UPDATE `product_mappings`: `requires_manual_review = true`
- Save rejection info in `interpretation_details` JSONB
- Se `corrected_product_id` fornito: crea nuovo mapping verified
- Temporary disable cache per questo raw_name
- Log critical event

**Task: Correct Product Handler**
- UPDATE `normalized_products` con correzioni
- Validate corrections (canonical_name required, no duplicates)
- Re-generate embedding se canonical_name cambiato
- Set `verification_status = 'user_verified'`
- UPDATE all `product_mappings`: `verified_by_user = true`

### 7.4 Integration

**Task: Integrate Validation in Pipeline**
- ProductRecognitionService chiama ValidationService dopo recognition
- Include ValidationResult nel response
- Se `PENDING_REVIEW`: set flag `requires_manual_review`
- Update API response format

**Task: Integrate Cache Update**
- Pipeline chiama CacheUpdateService dopo validation
- Update cache solo se validation pass (`AUTO_VERIFIED`)
- Skip update se `PENDING_REVIEW` (aspetta user feedback)
- Async update (non blocca response)

**Deliverables Phase 4**:
- ✅ ValidationService implementato
- ✅ CacheUpdateService operativo
- ✅ Feedback API endpoints (approve/reject/correct)
- ✅ Validation integrata in pipeline
- ✅ Cache update integrato
- ✅ Tests coverage >80%

---

## 8. Phase 5: Testing & Launch

### 8.1 Comprehensive Testing

**Task: Load Testing**
- Setup tool (Artillery, k6)
- Scenarios: 70% cache hits, 30% semantic search
- Simulate 100 concurrent users
- Ramp-up: 10 → 50 → 100 → 200 users
- Measure P50, P95, P99 latency
- Monitor database connections, CPU, memory
- Identify bottlenecks

**Targets**:
- P95 latency <50ms per cache hits
- P95 latency <600ms per semantic search
- Sistema gestisce 100 concurrent users senza crash
- No memory leaks

**Task: Accuracy Testing on Real Data**
- Raccogli 200 prodotti reali da scontrini
- Manually label ground truth
- Run recognition pipeline su tutti
- Calcola accuracy, precision, recall
- Analizza false positives/negatives
- Identify failure patterns
- Target: accuracy >85%

**Task: Edge Cases Testing**
- Test raw_name vuoto, null, troppo lungo
- Test caratteri speciali, emoji
- Test OCR errors simulati (typos)
- Test prodotti sconosciuti (brand nuovi)
- Test database unavailable
- Test OpenAI unavailable
- Test rate limits exhausted
- Verify error messages informativi

**Task: Security Testing**
- Test SQL injection (verify parametrized queries)
- Test authentication bypass (verify RLS)
- Test authorization (user non può accedere altri household)
- Test API rate limiting
- Test sensitive data in logs (no secrets)
- Verify CORS configuration

### 8.2 Production Migration

**Task: Migration Checklist**
- Pre-migration: backup DB, verify staging, notify users
- Migration steps: schema changes, backfill, deployment
- Post-migration: verify, monitor, rollback plan ready
- Define rollback triggers (error rate >10%, latency >2s)
- Estimate downtime (target <5 minuti)

**Task: Production Database Preparation**
- Backup completo production database
- Verify backup restoration (dry-run)
- Run migration SQL scripts su staging per validation
- Prepare rollback SQL scripts
- Schedule maintenance window
- Notify users se necessario

**Task: Production Backfill**
- Deploy backfill script
- Esegui in batches durante maintenance
- Monitor progress real-time
- Verify embeddings quality su sample
- Handle errors e retry failed batches
- Test vector search funziona su production data

### 8.3 Deployment

**Task: Staging Deployment**
- Deploy backend services su staging
- Deploy frontend changes
- Verify environment variables
- Run smoke tests (basic functionality)
- Verify monitoring attivo
- Load test finale su staging

**Task: Production Deployment**
- Execute migration checklist step-by-step
- Apply database migrations
- Deploy backend services (zero-downtime se possibile)
- Deploy frontend changes
- Run smoke tests su production
- Monitor metrics dashboard
- Verify first requests succeed
- Announce completion

**Task: Post-Deployment Verification**
- Execute UAT test scenarios
- Verify cache hit rate inizia a crescere
- Verify semantic search funziona
- Verify feedback loop (test approve/reject)
- Monitor error rate (<1% target)
- Monitor latency (P95 <600ms)
- Check costs tracking (OpenAI usage)

### 8.4 Monitoring Setup

**Task: Production Dashboards**
- Dashboard "Recognition Performance": latency, throughput, error rate
- Dashboard "Cache Metrics": hit rate, tier 1 vs tier 2, miss rate
- Dashboard "Accuracy Tracking": confidence distribution, review rate
- Dashboard "Cost Monitoring": OpenAI usage, costs per day
- Dashboard "Database Health": connection pool, query times
- Auto-refresh ogni 1 minuto

**Task: Alerting**
- Alert: Error rate >5% per 5 minuti → Critical
- Alert: P95 latency >1000ms per 10 minuti → Warning
- Alert: Cache hit rate <30% per 1 ora → Info
- Alert: OpenAI daily cost >$50 → Warning
- Alert: Database connection pool >90% → Critical
- Test alerts funzionano (trigger manually)

**Task: On-Call Runbook**
- Document common issues e troubleshooting:
  - High error rate → Check logs, verify DB/OpenAI, rollback se necessario
  - High latency → Check slow queries, verify cache, scale resources
  - Low cache hit rate → Verify view refresh, check cache logic
  - OpenAI rate limits → Verify throttling, consider upgrade
- Include rollback procedures
- Include escalation contacts
- Include useful debugging commands

**Deliverables Phase 5**:
- ✅ Load testing completato, performance verificata
- ✅ Accuracy testing >85%
- ✅ Edge cases e security testing passati
- ✅ Production deployment completato
- ✅ Post-deployment verification passed
- ✅ Monitoring dashboards live
- ✅ Alerting configurato
- ✅ On-call runbook creato
- ✅ **Sistema LIVE in production** 🎉

---

## 9. Post-Launch

### 9.1 Week 1: Monitoring & Stabilization

**Daily Tasks**:
- Check dashboards ogni mattina
- Review error logs per nuovi pattern
- Monitor cache hit rate trend (should increase)
- Monitor accuracy metrics
- Monitor costs (OpenAI usage)
- Document issues found
- Fix critical bugs immediatamente (hot patch)

**Success Criteria**:
- Zero critical bugs after week 1
- Error rate <1%
- System stable

### 9.2 Weeks 2-4: Optimization

**Performance Optimization**:
- Analyze slow query logs
- Optimize top 5 slowest queries
- Tune pgvector index parameters se necessario
- Optimize cache hit rate (tune thresholds)
- Consider Redis caching se DB bottleneck

**Accuracy Improvement**:
- Analyze rejected mappings (failure patterns)
- Improve LLM prompts basato su real examples
- Add few-shot examples per categorie problematiche
- Tune confidence thresholds (precision/recall trade-off)

**Cost Optimization**:
- Analyze OpenAI usage patterns
- Optimize embedding caching (increase cache size)
- Consider batch generation per ridurre calls
- Tune LLM temperature e max_tokens

### 9.3 Future Enhancements (Post-MVP)

**Potential Features**:
- Barcode scanning integration
- Multi-language support
- Advanced anomaly detection (5+ rules)
- Bulk import scontrini
- Product images recognition
- A/B testing framework
- ML model fine-tuning
- Continuous learning pipeline

**Decision Point**:
- Review accuracy dopo 1 mese: se <85% in categorie chiave, consider Proposta 2 (Hybrid Multi-Stage)
- Estimate ROI features vs effort
- Create roadmap Q2

---

## 10. Success Metrics

### 10.1 Performance Metrics (Target)

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Cache Latency P95 | <30ms | >100ms |
| Semantic Search Latency P95 | <600ms | >1000ms |
| Full Pipeline Latency P95 | <600ms | >1000ms |
| Database Query Time | <50ms | >200ms |
| Error Rate | <1% | >5% |
| Uptime | >99% | <95% |

### 10.2 Accuracy Metrics (Target)

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Overall Accuracy | >85% | <80% |
| Cache Hit Accuracy | >95% | <90% |
| Semantic Search Accuracy | >85% | <80% |
| False Positive Rate | <5% | >10% |
| Review Rate | <20% | >30% |

### 10.3 Cost Metrics (Target)

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Cost per Product (full pipeline) | <$0.0002 | >$0.0005 |
| Cost per Product (avg with cache) | <$0.00006 | >$0.0002 |
| Daily Cost (1000 products) | <$0.10 | >$0.30 |
| Monthly Cost (30k products) | <$3 | >$10 |

### 10.4 Business Metrics (Target)

| Metric | Target (Month 1) | Target (Month 3) |
|--------|------------------|------------------|
| Cache Hit Rate | >10% | >65% |
| User Satisfaction | >80% | >85% |
| Review Completion Rate | >70% | >80% |
| Daily Active Users | N/A | Track trend |

### 10.5 Monitoring Checklist

**Daily**:
- [ ] Error rate within target
- [ ] Latency within target
- [ ] No critical alerts triggered
- [ ] Costs within budget

**Weekly**:
- [ ] Cache hit rate trend positive
- [ ] Accuracy metrics stable or improving
- [ ] User feedback reviewed
- [ ] Bugs triaged and scheduled

**Monthly**:
- [ ] Performance optimization opportunities identified
- [ ] Accuracy improvements implemented
- [ ] Cost optimizations evaluated
- [ ] Roadmap updated with learnings

---

## Appendici

### A. Tech Stack Summary

**Core**:
- Database: PostgreSQL (Supabase) + pgvector
- Backend: TypeScript/Node.js o Python/FastAPI
- AI: OpenAI (Ada embeddings + GPT-4o-mini)
- Monitoring: Structured logging + Supabase dashboard

**Testing**:
- Unit/Integration: Jest/Vitest o Pytest
- E2E: Playwright
- Load: Artillery o k6

**DevOps**:
- Deployment: Supabase + Vercel/Railway
- CI/CD: GitHub Actions
- Version Control: Git

### B. Key SQL Queries

**Cache Lookup**:
```sql
SELECT * FROM product_cache_stats
WHERE raw_name = $1 AND store_name = $2
ORDER BY usage_count DESC
LIMIT 1;
```

**Vector Search**:
```sql
SELECT *, 1 - (embedding <=> $1) AS similarity
FROM normalized_products
WHERE verification_status != 'rejected'
ORDER BY embedding <=> $1
LIMIT 5;
```

**Cache Update**:
```sql
INSERT INTO product_mappings (raw_name, normalized_product_id, store_name, confidence_score)
VALUES ($1, $2, $3, $4)
ON CONFLICT (raw_name, store_name) DO UPDATE
SET confidence_score = GREATEST(product_mappings.confidence_score, EXCLUDED.confidence_score);
```

### C. Useful Links

**Documentation**:
- [Supabase pgvector](https://supabase.com/docs/guides/ai/vector-columns)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [OpenAI GPT-4o-mini](https://platform.openai.com/docs/models/gpt-4o-mini)
- [Product Recognition Architecture](./product-recognition-architecture.md)

### D. Definition of Done

**Per Task**:
- [ ] Code implementato e funzionante
- [ ] Unit tests scritti (coverage >80%)
- [ ] Integration tests passano (se applicabile)
- [ ] Documentation aggiornata
- [ ] Deployed su staging e verificato
- [ ] Acceptance criteria soddisfatti
- [ ] No critical bugs
- [ ] Performance requirements met

**Per Phase**:
- [ ] Tutti i task Done
- [ ] End-to-end testing passed
- [ ] Performance targets raggiunti
- [ ] Documentation completa
- [ ] Staging stabile
- [ ] Ready for next phase

**Per Launch**:
- [ ] Tutte le phase completate
- [ ] Production deployment successful
- [ ] Monitoring e alerting operativi
- [ ] Documentation completa (API, architecture, runbook)
- [ ] User guide pubblicata
- [ ] Metrics targets raggiunti
- [ ] Stakeholder approval

---

**Fine MVP Roadmap** - Focus on Core, Ship Fast, Iterate! 🚀
