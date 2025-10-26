# Architettura Riconoscimento Prodotti - Vector DB + LLM

**Versione**: 1.0
**Data**: Ottobre 2025
**Autore**: Sistema Scontrini Team
**Status**: Proposta Tecnica

---

## 📋 Indice

1. [Overview](#1-overview)
2. [Situazione Attuale](#2-situazione-attuale)
3. [Proposta 1: Semantic Search First + Smart Cache](#3-proposta-1-semantic-search-first--smart-cache)
   - 3.1 [Architettura Overview](#31-architettura-overview)
   - 3.2 [PHASE 0: Smart Cache Lookup](#32-phase-0-smart-cache-lookup-new)
   - 3.3 [STEP 1: Riconoscimento Semantico](#33-step-1-riconoscimento-semantico)
   - 3.4 [STEP 2: Validazione Intelligente](#34-step-2-validazione-intelligente)
   - 3.5 [Performance Metrics](#35-performance-metrics)
   - 3.6 [Database Requirements](#36-database-requirements)
4. [Proposta 2: Hybrid Multi-Stage](#4-proposta-2-hybrid-multi-stage)
   - 4.1 [Architettura Overview](#41-architettura-overview)
   - 4.2 [STEP 1: Riconoscimento Multi-Fase](#42-step-1-riconoscimento-multi-fase)
   - 4.3 [STEP 2: Validazione Avanzata](#43-step-2-validazione-avanzata)
   - 4.4 [Performance Metrics](#44-performance-metrics)
   - 4.5 [Database Requirements](#45-database-requirements)
5. [Confronto & Raccomandazioni](#5-confronto--raccomandazioni)
6. [Implementation Roadmap](#6-implementation-roadmap)
7. [Monitoring & KPIs](#7-monitoring--kpis)
8. [Appendici](#8-appendici)

---

## 1. Overview

### 1.1 Contesto

Il sistema **Scontrini** deve riconoscere prodotti a partire da nomi grezzi estratti tramite OCR dagli scontrini fiscali. Questi nomi sono:
- **Abbreviati**: "COCA COLA PET" invece di "Coca Cola Bottiglia PET 1.5L"
- **Inconsistenti**: Stesso prodotto con nomi diversi in negozi diversi
- **Rumorosi**: Errori OCR ("C0CA C0LA" con zeri invece di O)
- **Non standardizzati**: "FTT. BSCTT MULBCO" per "Frollini Mulino Bianco"

### 1.2 Obiettivi

1. **Accuracy**: Riconoscimento corretto >90% dei prodotti
2. **Performance**: Latenza <500ms per prodotto
3. **Scalabilità**: Gestire milioni di prodotti normalizzati
4. **User Experience**: Minimizzare review manuali (<15%)
5. **Cost Efficiency**: Ottimizzare costi API LLM/embeddings

### 1.3 Scope

Questo documento descrive **due architetture alternative** per il sistema di riconoscimento:
- **Proposta 1**: Approccio veloce basato su vector search con cache intelligente
- **Proposta 2**: Approccio multi-fase ibrido con alta precisione

---

## 2. Situazione Attuale

### 2.1 Schema Database Esistente

Dal file `complete_schema.sql` abbiamo:

```sql
-- Prodotti grezzi da OCR
receipt_items (
  id UUID,
  receipt_id UUID,
  raw_product_name TEXT NOT NULL,  -- "COCA COLA PET 1.5L"
  quantity NUMERIC,
  unit_price NUMERIC,
  total_price NUMERIC,
  line_number INTEGER
)

-- Prodotti normalizzati (catalogo master)
normalized_products (
  id UUID,
  canonical_name TEXT UNIQUE,      -- "Coca Cola 1.5L"
  brand TEXT,                       -- "Coca Cola"
  category TEXT,                    -- "Bevande"
  subcategory TEXT,                 -- "Bibite Gassate"
  verification_status TEXT          -- 'auto_verified' | 'pending_review' | ...
)

-- Mapping raw → normalized
product_mappings (
  id UUID,
  raw_name TEXT NOT NULL,
  normalized_product_id UUID,
  store_name TEXT,
  confidence_score DOUBLE PRECISION,
  verified_by_user BOOLEAN,
  requires_manual_review BOOLEAN,
  interpretation_details JSONB
)

-- Storico acquisti
purchase_history (
  id UUID,
  household_id UUID,
  receipt_id UUID,
  normalized_product_id UUID,
  purchase_date DATE,
  quantity NUMERIC,
  total_price NUMERIC
)
```

### 2.2 Flusso Attuale (Ipotizzato)

```
OCR → raw_product_name → LLM normalization → normalized_product
                              │
                              └─→ confidence < 0.8 → PENDING_REVIEW
```

### 2.3 Limitazioni

❌ **No cache**: Stesso prodotto riconosciuto ogni volta (spreco risorse)
❌ **No semantic search**: Matching puramente testuale/LLM
❌ **No context**: Non usa storico acquisti o negozio
❌ **Lento**: Ogni prodotto richiede chiamata LLM
❌ **Costoso**: API costs crescono linearmente con volume

---

## 3. Proposta 1: Semantic Search First + Smart Cache

### 3.1 Architettura Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                         INPUT                                     │
│  raw_product_name: "COCA COLA PET 1.5L"                          │
│  context: {store: "Conad", price: 1.29, household_id: "..."}     │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│  PHASE 0: SMART CACHE LOOKUP (PostgreSQL)                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Query: product_mappings WHERE raw_name = ? AND store = ?   │ │
│  │        AND verified_by_user = true                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Cache HIT (65-75% dopo 3 mesi)  │  Cache MISS (25-35%)         │
└──────────────┬────────────────────┴──────────────┬───────────────┘
               │                                   │
               ▼                                   ▼
   ┌───────────────────────┐         ┌────────────────────────────┐
   │ Return cached product │         │   STEP 1: RICONOSCIMENTO   │
   │ Confidence: 0.90      │         │   ┌──────────────────────┐ │
   │ Skip to validation    │         │   │ 1. Generate embedding│ │
   └───────────┬───────────┘         │   │ 2. Vector search     │ │
               │                     │   │ 3. Context enrich    │ │
               │                     │   │ 4. LLM reasoning     │ │
               │                     │   └──────────────────────┘ │
               │                     └────────────┬───────────────┘
               │                                  │
               └──────────────┬───────────────────┘
                              ▼
               ┌──────────────────────────────────┐
               │   STEP 2: VALIDAZIONE            │
               │   • Confidence thresholds        │
               │   • Anomaly detection            │
               │   • Cache update logic           │
               │   • User feedback loop           │
               └──────────────┬───────────────────┘
                              ▼
               ┌──────────────────────────────────┐
               │         OUTPUT                   │
               │  {                               │
               │    product_id: "uuid",           │
               │    canonical_name: "...",        │
               │    confidence: 0.92,             │
               │    requires_review: false        │
               │  }                               │
               └──────────────────────────────────┘
```

### 3.2 PHASE 0: Smart Cache Lookup ⭐ NEW

**Obiettivo**: Evitare riconoscimento costoso per prodotti già visti.

#### 3.2.1 Cache Tier System

**Tier 1: Verified Cache** (Massima affidabilità)
```sql
SELECT
  pm.normalized_product_id,
  np.canonical_name,
  np.brand,
  np.category,
  COUNT(DISTINCT ph.id) as usage_count,
  MAX(ph.purchase_date) as last_used,
  AVG(ph.unit_price) as avg_price,
  COUNT(DISTINCT ph.household_id) as verified_by_households
FROM product_mappings pm
JOIN normalized_products np ON np.id = pm.normalized_product_id
LEFT JOIN purchase_history ph ON ph.normalized_product_id = np.id
WHERE pm.raw_name = 'COCA COLA PET 1.5L'
  AND pm.store_name = 'Conad'
  AND pm.verified_by_user = true
GROUP BY pm.id, np.id
ORDER BY usage_count DESC, last_used DESC
LIMIT 1;
```

**Caratteristiche**:
- ✅ Usato e verificato da utenti reali
- ✅ Confidence fissa: **0.90**
- ✅ Fast path: skip full recognition
- ✅ Validation leggera (solo price coherence)

**Tier 2: Auto-Verified Cache** (Fallback)
```sql
-- Se Tier 1 non trova risultati
WHERE pm.verified_by_user = false
  AND pm.confidence_score >= 0.85
  AND np.verification_status IN ('auto_verified', 'user_verified')
```

**Caratteristiche**:
- ⚠️ Riconosciuto automaticamente ma non ancora verificato da user
- ⚠️ Confidence: `original_confidence * 0.95`
- ⚠️ Validation media richiesta
- ⚠️ Può essere promosso a Tier 1 dopo conferma utente

#### 3.2.2 Cache Hit Response

Quando cache trova match:

```typescript
{
  product_id: "550e8400-e29b-41d4-a716-446655440000",
  canonical_name: "Coca Cola 1.5L",
  brand: "Coca Cola",
  category: "Bevande",
  subcategory: "Bibite Gassate",

  // Cache metadata
  confidence: 0.90,  // Fixed per verified cache
  source: "verified_cache",
  cache_metadata: {
    usage_count: 15,           // Usato 15 volte
    last_used: "2025-10-20",   // Usato 5 giorni fa
    verified_by_households: 3, // Verificato da 3 famiglie diverse
    avg_price: 1.29,           // Prezzo medio storico
    price_stddev: 0.15         // Deviazione standard prezzo
  },

  skip_full_recognition: true  // Flag per saltare STEP 1
}
```

#### 3.2.3 Cache Miss Fallback

Se nessun match trovato:
1. Log cache miss per analytics
2. Procedi a **STEP 1: Riconoscimento** completo
3. Salva risultato in cache per future hits

#### 3.2.4 Context-Aware Caching

La cache è **context-aware**:

```sql
-- Cache considera store_name
WHERE pm.raw_name = ? AND pm.store_name = ?

-- Possibile espansione futura:
-- Cache per household (preferenze famiglia)
WHERE pm.raw_name = ?
  AND (pm.store_name = ? OR pm.household_id = ?)
```

**Rationale**:
- Stesso raw name in negozi diversi può essere prodotto diverso
- Es: "ACQUA NAT 1.5L" → Brand diverso per Esselunga vs Lidl

### 3.3 STEP 1: Riconoscimento Semantico

**Trigger**: Solo se PHASE 0 cache miss.

#### 3.3.1 Vector Embedding Generation

```typescript
// Input
const rawName = "COCA COLA PET 1.5L";

// Call OpenAI Embeddings API (text-embedding-ada-002)
const embedding = await openai.embeddings.create({
  model: "text-embedding-ada-002",
  input: rawName
});

// Output: Float array [1536 dimensions]
const vector = embedding.data[0].embedding;
// [0.012, -0.023, 0.045, ..., 0.001]  // 1536 values
```

**Costo**: ~$0.0001 per prodotto

#### 3.3.2 Vector Search (Supabase pgvector)

```sql
-- Assumendo normalized_products abbia colonna embedding vector(1536)
SELECT
  np.id,
  np.canonical_name,
  np.brand,
  np.category,
  np.subcategory,
  1 - (np.embedding <=> $1::vector) as similarity  -- Cosine similarity
FROM normalized_products np
WHERE np.verification_status != 'rejected'
ORDER BY np.embedding <=> $1::vector  -- Distance operator
LIMIT 5;
```

**Performance**:
- pgvector index (IVFFlat o HNSW)
- Query time: ~10-50ms per milioni di vettori
- Top-K retrieval estremamente efficiente

**Output Example**:
```typescript
[
  {id: "uuid-1", canonical_name: "Coca Cola 1.5L", similarity: 0.95},
  {id: "uuid-2", canonical_name: "Coca Cola Zero 1.5L", similarity: 0.89},
  {id: "uuid-3", canonical_name: "Pepsi Cola 1.5L", similarity: 0.82},
  {id: "uuid-4", canonical_name: "Coca Cola 2L", similarity: 0.78},
  {id: "uuid-5", canonical_name: "Fanta 1.5L", similarity: 0.71}
]
```

#### 3.3.3 Context Enrichment

Arricchisci candidati con dati contestuali:

```typescript
// Per ogni candidato, aggiungi:
const enrichedCandidates = await Promise.all(
  candidates.map(async (candidate) => {
    // Storico acquisti household
    const userHistory = await db.query(`
      SELECT COUNT(*) as purchase_count, AVG(unit_price) as avg_price
      FROM purchase_history
      WHERE household_id = $1
        AND normalized_product_id = $2
    `, [householdId, candidate.id]);

    // Statistiche negozio
    const storeStats = await db.query(`
      SELECT COUNT(*) as sold_count, AVG(unit_price) as store_avg_price
      FROM purchase_history ph
      JOIN receipts r ON r.id = ph.receipt_id
      WHERE r.store_name = $1
        AND ph.normalized_product_id = $2
    `, [storeName, candidate.id]);

    return {
      ...candidate,
      user_bought_before: userHistory.purchase_count > 0,
      user_avg_price: userHistory.avg_price,
      popular_at_store: storeStats.sold_count > 10,
      store_avg_price: storeStats.store_avg_price
    };
  })
);
```

#### 3.3.4 LLM Reasoning (GPT-4o-mini)

```typescript
const systemPrompt = `Sei un esperto di prodotti retail italiano.
Analizza il nome grezzo di un prodotto da scontrino e seleziona
il prodotto normalizzato più probabile tra i candidati forniti.

Considera:
1. Similarità semantica (già calcolata)
2. Storico acquisti dell'utente (continuità)
3. Coerenza brand/negozio
4. Coherenza prezzo
5. Abbreviazioni comuni supermercati italiani

Se nessun candidato ha confidence >90%, proponi un nuovo prodotto normalizzato.`;

const userPrompt = `
Raw product name: "COCA COLA PET 1.5L"
Current price: 1.29€
Store: "Conad"

Top candidates:
1. Coca Cola 1.5L (similarity: 0.95, user bought 5 times, avg price: 1.25€)
2. Coca Cola Zero 1.5L (similarity: 0.89, never bought, avg price: 1.30€)
3. Pepsi Cola 1.5L (similarity: 0.82, bought 1 time, avg price: 1.10€)

Seleziona il prodotto o proponi nuovo.
Rispondi in JSON:
{
  "decision": "existing_product" | "new_product",
  "product_id": "uuid" | null,
  "confidence": 0.0-1.0,
  "reasoning": "spiegazione",
  "new_product": { ... } // solo se decision = "new_product"
}
`;

const response = await openai.chat.completions.create({
  model: "gpt-4o-mini",
  messages: [
    {role: "system", content: systemPrompt},
    {role: "user", content: userPrompt}
  ],
  response_format: {type: "json_object"},
  temperature: 0.1  // Low temperature per consistenza
});

const result = JSON.parse(response.choices[0].message.content);
```

**Output Example**:
```json
{
  "decision": "existing_product",
  "product_id": "uuid-1",
  "confidence": 0.95,
  "reasoning": "Match esatto per nome e formato. Prezzo coerente con storico (1.29€ vs media 1.25€). Utente ha già comprato questo prodotto 5 volte, indica preferenza consolidata.",
  "alternative_confidence": {
    "coca_cola_zero": 0.12,
    "pepsi": 0.03
  }
}
```

**Costo**: ~$0.0001 per chiamata

### 3.4 STEP 2: Validazione Intelligente

#### 3.4.1 Source-Based Validation

```typescript
function validate(result, source) {
  if (source === 'verified_cache') {
    // Cache verificata → validazione leggera
    return validateCacheHit(result);
  } else if (source === 'auto_cache') {
    // Cache non verificata → validazione media
    return validateAutoCacheHit(result);
  } else {
    // Nuovo riconoscimento → validazione completa
    return validateNewRecognition(result);
  }
}
```

**Validated Cache Hit**:
```typescript
function validateCacheHit(result) {
  const {product, context, cache_metadata} = result;

  // Check 1: Price coherence (±30% tolerance)
  const priceDeviation = Math.abs(
    context.current_price - cache_metadata.avg_price
  ) / cache_metadata.avg_price;

  if (priceDeviation > 0.30) {
    return {
      status: 'PENDING_REVIEW',
      reason: 'price_outlier',
      confidence: 0.70,  // Downgrade
      message: `Prezzo ${context.current_price}€ molto diverso da media ${cache_metadata.avg_price}€`
    };
  }

  // Check 2: Recency (cache non troppo vecchio)
  const daysSinceLastUse = daysBetween(cache_metadata.last_used, today);
  if (daysSinceLastUse > 180) {
    // Prodotto non visto da 6+ mesi → possibile cambio
    result.confidence = 0.85;  // Leggero downgrade
  }

  // Pass validation
  return {
    status: 'AUTO_VERIFIED',
    confidence: result.confidence,
    validation_checks: {
      price_coherence: true,
      recency: daysSinceLastUse < 180
    }
  };
}
```

**New Recognition Validation**:
```typescript
function validateNewRecognition(result) {
  const {confidence, product, context} = result;

  // Threshold-based
  if (confidence >= 0.90) {
    return {status: 'AUTO_VERIFIED', confidence};
  }

  if (confidence >= 0.70 && confidence < 0.90) {
    return {
      status: 'PENDING_REVIEW',
      priority: 'low',  // Soft review
      confidence
    };
  }

  // Low confidence
  return {
    status: 'PENDING_REVIEW',
    priority: 'high',  // Hard review
    confidence
  };
}
```

#### 3.4.2 Anomaly Detection

```typescript
function detectAnomalies(product, context) {
  const anomalies = [];

  // Anomaly 1: Price outlier (prezzo 5x categoria media)
  const categoryAvgPrice = await getCategoryAvgPrice(product.category);
  if (context.current_price > categoryAvgPrice * 5) {
    anomalies.push({
      type: 'price_outlier',
      severity: 'high',
      message: `Prezzo ${context.current_price}€ è 5x la media categoria`
    });
  }

  // Anomaly 2: Category-Store mismatch
  const storeType = getStoreType(context.store_name);  // 'supermarket' | 'pharmacy' | ...
  if (product.category === 'Farmaci' && storeType === 'supermarket') {
    anomalies.push({
      type: 'category_store_mismatch',
      severity: 'medium',
      message: 'Farmaco in supermercato alimentare'
    });
  }

  // Anomaly 3: Size/Unit sanity check
  if (product.unit_type === 'kg' && parseFloat(product.size) > 50) {
    anomalies.push({
      type: 'size_unrealistic',
      severity: 'medium',
      message: 'Peso >50kg improbabile per singolo prodotto retail'
    });
  }

  return anomalies;
}

// Force review se anomalie critiche
if (anomalies.some(a => a.severity === 'high')) {
  return {
    status: 'PENDING_REVIEW',
    priority: 'high',
    reason: 'critical_anomaly',
    anomalies
  };
}
```

#### 3.4.3 Cache Update Logic

```typescript
async function updateCache(result, validation) {
  if (validation.status === 'AUTO_VERIFIED' && result.source !== 'cache') {
    // Nuovo riconoscimento auto-verified → salva in cache
    await db.query(`
      INSERT INTO product_mappings (
        raw_name,
        normalized_product_id,
        store_name,
        confidence_score,
        verified_by_user,
        interpretation_details
      ) VALUES ($1, $2, $3, $4, false, $5)
      ON CONFLICT (raw_name, store_name, normalized_product_id)
      DO UPDATE SET
        confidence_score = GREATEST(product_mappings.confidence_score, $4),
        interpretation_details = $5
    `, [
      result.raw_name,
      result.product_id,
      result.context.store_name,
      result.confidence,
      {reasoning: result.reasoning, created_at: new Date()}
    ]);
  }

  if (result.source === 'verified_cache') {
    // Cache hit → incrementa usage stats (via purchase_history insert)
    // Questo avviene naturalmente quando si salva l'acquisto
  }
}
```

#### 3.4.4 Feedback Loop

**User Approves Cache Hit**:
```typescript
async function onUserApprovesCacheHit(mappingId, userId) {
  // Marca come verified_by_user se non già fatto
  await db.query(`
    UPDATE product_mappings
    SET
      verified_by_user = true,
      confidence_score = 1.0,
      reviewed_at = NOW(),
      reviewed_by = $2
    WHERE id = $1
  `, [mappingId, userId]);

  // Incrementa counter "verified_by_households"
  // (tracciato via purchase_history)

  // Se >= 3 households diversi hanno verificato → boost cache priority
}
```

**User Rejects Cache Hit** (raro ma critico):
```typescript
async function onUserRejectsCacheHit(mappingId, userId, correctedProductId) {
  // Scenario critico: cache era sbagliata!

  // 1. Marca vecchio mapping come problematico
  await db.query(`
    UPDATE product_mappings
    SET
      requires_manual_review = true,
      interpretation_details = jsonb_set(
        interpretation_details,
        '{cache_rejection}',
        $3
      )
    WHERE id = $1
  `, [mappingId, userId, {
    rejected_at: new Date(),
    rejected_by: userId,
    reason: 'cache_hit_incorrect',
    corrected_product_id: correctedProductId
  }]);

  // 2. Temporary disable cache per questo raw_name
  // (fino a re-training)
  await db.query(`
    UPDATE product_mappings
    SET verified_by_user = false
    WHERE raw_name = (SELECT raw_name FROM product_mappings WHERE id = $1)
  `, [mappingId]);

  // 3. Create new correct mapping
  await db.query(`
    INSERT INTO product_mappings (
      raw_name, normalized_product_id, store_name,
      verified_by_user, confidence_score, reviewed_by
    )
    SELECT raw_name, $2, store_name, true, 1.0, $3
    FROM product_mappings WHERE id = $1
  `, [mappingId, correctedProductId, userId]);

  // 4. Alert sistema: possibile drift o errore sistematico
  logCriticalEvent('cache_rejection', {mappingId, userId});
}
```

**New Product Approved**:
```typescript
async function onUserApprovesNewProduct(productId, userId) {
  // Prodotto appena riconosciuto e approvato → immediatamente in cache

  await db.query(`
    UPDATE normalized_products
    SET verification_status = 'user_verified'
    WHERE id = $1
  `, [productId]);

  await db.query(`
    UPDATE product_mappings
    SET verified_by_user = true, reviewed_by = $2
    WHERE normalized_product_id = $1
  `, [productId, userId]);

  // Genera embedding ottimizzato con nome normalizzato
  const embedding = await generateEmbedding(product.canonical_name);
  await db.query(`
    UPDATE normalized_products
    SET embedding = $2
    WHERE id = $1
  `, [productId, embedding]);
}
```

### 3.5 Performance Metrics

#### 3.5.1 Latency Breakdown

**Cache Hit Scenario** (65-75% dei casi dopo 3 mesi):
```
PostgreSQL cache lookup:     ~5-15ms
Price validation:            ~5ms
Response formatting:         ~5ms
────────────────────────────────────
Total:                       ~15-25ms ⚡
```

**Cache Miss Scenario** (25-35% dei casi):
```
PostgreSQL cache lookup:     ~10ms (miss)
OpenAI embedding:            ~100-200ms
pgvector search:             ~20-50ms
Context enrichment queries:  ~30-50ms
LLM reasoning (GPT-4o-mini): ~200-300ms
Validation:                  ~10ms
────────────────────────────────────
Total:                       ~370-620ms
```

**Average Latency** (weighted):
```
0.70 * 20ms + 0.30 * 450ms = 14ms + 135ms = ~149ms average ⚡⚡⚡
```

#### 3.5.2 Cost Analysis

**Per Prodotto**:
- Embedding (Ada-002): $0.0001
- LLM reasoning (GPT-4o-mini): $0.0001
- **Total per recognition**: ~$0.0002

**Con Cache (after 3 months)**:
- Cache hit: $0 (solo query DB)
- Cache miss: $0.0002
- **Average**: 0.70 * $0 + 0.30 * $0.0002 = **$0.00006 per prodotto**

**ROI Example** (1000 prodotti/giorno):
- Senza cache: 1000 * $0.0002 = $0.20/giorno = **$73/anno**
- Con cache: 1000 * $0.00006 = $0.06/giorno = **$22/anno**
- **Risparmio**: $51/anno (70% riduzione)

#### 3.5.3 Accuracy Metrics

**Aspettative**:
- Overall accuracy: **90-94%**
- Cache hit accuracy: **95-98%** (prodotti verificati)
- New recognition accuracy: **85-90%**
- Review rate: **10-15%** (vs 20% attuale)

**Misurazione**:
```sql
-- Accuracy dashboard query
SELECT
  DATE_TRUNC('week', created_at) as week,
  COUNT(*) as total_products,
  COUNT(*) FILTER (WHERE source = 'verified_cache') as cache_hits,
  COUNT(*) FILTER (WHERE verified_by_user = true) as user_verified,
  COUNT(*) FILTER (WHERE requires_manual_review = true) as pending_review,
  AVG(confidence_score) as avg_confidence
FROM product_mappings
WHERE created_at >= NOW() - INTERVAL '3 months'
GROUP BY week
ORDER BY week DESC;
```

### 3.6 Database Requirements

#### 3.6.1 Schema Changes

**Add embedding column to normalized_products**:
```sql
-- Aggiungi colonna vettoriale
ALTER TABLE normalized_products
ADD COLUMN embedding vector(1536);  -- Ada-002 dimensionality

-- Crea indice pgvector (HNSW per performance ottimali)
CREATE INDEX ON normalized_products
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Indice alternativo IVFFlat (più veloce per insert)
-- CREATE INDEX ON normalized_products
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);
```

**Add indexes for cache lookup**:
```sql
-- Indice composto per cache lookup veloce
CREATE INDEX idx_product_mappings_cache_lookup
ON product_mappings(raw_name, store_name, verified_by_user)
WHERE verified_by_user = true;

-- Indice per fallback auto-verified cache
CREATE INDEX idx_product_mappings_auto_cache
ON product_mappings(raw_name, store_name, confidence_score)
WHERE verified_by_user = false AND confidence_score >= 0.85;

-- Indice per usage statistics
CREATE INDEX idx_purchase_history_stats
ON purchase_history(normalized_product_id, household_id, purchase_date);
```

#### 3.6.2 Materialized View for Cache Stats

```sql
CREATE MATERIALIZED VIEW product_cache_stats AS
SELECT
  pm.id as mapping_id,
  pm.raw_name,
  pm.store_name,
  pm.normalized_product_id,
  np.canonical_name,

  -- Usage statistics
  COUNT(DISTINCT ph.id) as usage_count,
  MAX(ph.purchase_date) as last_used,
  MIN(ph.purchase_date) as first_used,

  -- Household verification
  COUNT(DISTINCT ph.household_id) as verified_by_households,

  -- Price statistics
  AVG(ph.unit_price) as avg_price,
  STDDEV(ph.unit_price) as price_stddev,
  MIN(ph.unit_price) as min_price,
  MAX(ph.unit_price) as max_price,

  -- Quality indicators
  pm.confidence_score,
  pm.verified_by_user,
  np.verification_status

FROM product_mappings pm
JOIN normalized_products np ON np.id = pm.normalized_product_id
LEFT JOIN purchase_history ph ON ph.normalized_product_id = np.id
WHERE pm.verified_by_user = true
GROUP BY pm.id, np.id;

-- Indici sulla view
CREATE INDEX ON product_cache_stats(raw_name, store_name);
CREATE INDEX ON product_cache_stats(usage_count DESC);
CREATE INDEX ON product_cache_stats(verified_by_households DESC);

-- Refresh periodico (ogni ora via pg_cron)
SELECT cron.schedule('refresh-cache-stats', '0 * * * *',
  'REFRESH MATERIALIZED VIEW CONCURRENTLY product_cache_stats'
);
```

#### 3.6.3 Helper Functions

**Get Cache Hit**:
```sql
CREATE OR REPLACE FUNCTION get_cached_product(
  p_raw_name TEXT,
  p_store_name TEXT,
  p_current_price NUMERIC DEFAULT NULL
)
RETURNS TABLE (
  product_id UUID,
  canonical_name TEXT,
  brand TEXT,
  category TEXT,
  confidence NUMERIC,
  usage_count BIGINT,
  avg_price NUMERIC,
  price_coherent BOOLEAN
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    pcs.normalized_product_id,
    pcs.canonical_name,
    np.brand,
    np.category,
    0.90::NUMERIC as confidence,  -- Fixed for verified cache
    pcs.usage_count,
    pcs.avg_price,
    -- Price coherence check (±30%)
    CASE
      WHEN p_current_price IS NULL THEN true
      WHEN pcs.avg_price IS NULL THEN true
      WHEN ABS(p_current_price - pcs.avg_price) / pcs.avg_price <= 0.30 THEN true
      ELSE false
    END as price_coherent
  FROM product_cache_stats pcs
  JOIN normalized_products np ON np.id = pcs.normalized_product_id
  WHERE pcs.raw_name = p_raw_name
    AND pcs.store_name = p_store_name
    AND pcs.verified_by_user = true
  ORDER BY pcs.usage_count DESC, pcs.last_used DESC
  LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

-- Usage:
-- SELECT * FROM get_cached_product('COCA COLA PET 1.5L', 'Conad', 1.29);
```

---

## 4. Proposta 2: Hybrid Multi-Stage

### 4.1 Architettura Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                           INPUT                                 │
│  raw_product_name: "FTT BSCTT MULBCO 350G"                     │
│  context: {store, price, household_id}                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STEP 1: RICONOSCIMENTO                        │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ PHASE 1: Exact Match Cache (PostgreSQL)                  │ │
│  │   └─→ HIT (confidence 1.0) → Skip to validation         │ │
│  │   └─→ MISS → Continue                                    │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ PHASE 2: Fuzzy Text Match (pg_trgm)                      │ │
│  │   └─→ Trigram similarity > 0.85 → Candidati              │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ PHASE 3: Semantic Vector Search (pgvector)               │ │
│  │   └─→ Top 5 candidati semantici                          │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ PHASE 4: LLM Structured Extraction (GPT-4o-mini)         │ │
│  │   └─→ Decodifica abbreviazioni, estrai features          │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ PHASE 5: Enhanced Vector Search (con features)           │ │
│  │   └─→ Re-search con embedding arricchito                 │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ PHASE 6: LLM Final Decision + Scoring (GPT-4o-mini)      │ │
│  │   └─→ Seleziona prodotto o crea nuovo                    │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STEP 2: VALIDAZIONE                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ [A] Multi-Signal Confidence Aggregation                   │ │
│  │     Weighted average di 5 confidence scores               │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ [B] Consistency Checks (rule-based)                       │ │
│  │     Size/unit, category/store, brand/product, price       │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ [C] Duplicate Detection                                   │ │
│  │     Evita prodotti normalizzati quasi identici            │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ [D] Human-in-the-Loop Prioritization                      │ │
│  │     Ordina review queue per importanza                    │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ [E] Continuous Learning Pipeline                          │ │
│  │     User feedback → Training data → Model improvement     │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
                  ┌───────────────────────┐
                  │       OUTPUT          │
                  │  confidence: 0.93     │
                  │  status: AUTO_VERIFIED│
                  └───────────────────────┘
```

### 4.2 STEP 1: Riconoscimento Multi-Fase

#### 4.2.1 PHASE 1: Exact Match Cache

**Identico a Proposta 1 PHASE 0**.

```sql
SELECT * FROM product_mappings
WHERE raw_name = 'FTT BSCTT MULBCO 350G'
  AND store_name = 'Esselunga'
  AND verified_by_user = true
LIMIT 1;
```

**Se HIT**: Return con `confidence = 1.0`, skip tutte le altre fasi.

#### 4.2.2 PHASE 2: Fuzzy Text Match

**Obiettivo**: Catturare variazioni minori (typos, spazi, abbreviazioni).

**PostgreSQL pg_trgm extension**:
```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Query fuzzy matches
SELECT
  pm.id,
  pm.raw_name,
  pm.normalized_product_id,
  np.canonical_name,
  similarity(pm.raw_name, 'FTT BSCTT MULBCO 350G') as text_similarity
FROM product_mappings pm
JOIN normalized_products np ON np.id = pm.normalized_product_id
WHERE pm.raw_name % 'FTT BSCTT MULBCO 350G'  -- % operator = similar
  AND pm.store_name = 'Esselunga'
ORDER BY text_similarity DESC
LIMIT 3;
```

**Output Example**:
```typescript
[
  {
    raw_name: "FETT BSCTT MULBCO 350G",  // Typo: FETT vs FTT
    canonical_name: "Frollini Mulino Bianco 350g",
    text_similarity: 0.88
  },
  {
    raw_name: "FTT BSCTT MUL BCO 350G",  // Spazio extra
    canonical_name: "Frollini Mulino Bianco 350g",
    text_similarity: 0.87
  }
]
```

**Threshold**: Se `similarity >= 0.85` → aggiungi a candidati.

**Indice per performance**:
```sql
CREATE INDEX idx_product_mappings_trgm
ON product_mappings USING gin (raw_name gin_trgm_ops);
```

#### 4.2.3 PHASE 3: Semantic Vector Search

**Identico a Proposta 1 Step 1.2**.

```sql
SELECT
  np.id,
  np.canonical_name,
  1 - (np.embedding <=> $1::vector) as semantic_similarity
FROM normalized_products np
ORDER BY np.embedding <=> $1::vector
LIMIT 5;
```

#### 4.2.4 PHASE 4: LLM Structured Extraction

**Obiettivo**: Decodificare abbreviazioni italiane comuni.

**Prompt**:
```typescript
const extractionPrompt = `Analizza questo nome prodotto da scontrino italiano:
"FTT BSCTT MULBCO 350G"

Estrai in JSON:
{
  "product_type": "categoria generale (es: biscotti, pasta, latte)",
  "brand": "marca se riconoscibile (null se non chiaro)",
  "size": "quantità numerica estratta",
  "unit": "unità di misura (g, kg, l, ml, pz, etc)",
  "keywords": ["parole", "chiave", "identificative"],
  "abbreviations_decoded": {
    "FTT": "possibile significato",
    "BSCTT": "possibile significato",
    "MULBCO": "possibile significato"
  },
  "normalized_description": "descrizione prodotto in italiano chiaro"
}

Considera abbreviazioni comuni supermercati italiani:
- FTT/FETT = Fette/Frollini
- BSCTT = Biscotti
- MUL/MULINO = Mulino
- BCO/BIANCO = Bianco
- NAT = Naturale
- GASS = Gassata
- etc.
`;

const response = await openai.chat.completions.create({
  model: "gpt-4o-mini",
  messages: [{role: "user", content: extractionPrompt}],
  response_format: {type: "json_object"}
});

const extracted = JSON.parse(response.choices[0].message.content);
```

**Output Example**:
```json
{
  "product_type": "biscotti",
  "brand": "Mulino Bianco",
  "size": "350",
  "unit": "g",
  "keywords": ["frollini", "biscotti", "mulino", "bianco"],
  "abbreviations_decoded": {
    "FTT": "Frollini/Fette",
    "BSCTT": "Biscotti",
    "MULBCO": "Mulino Bianco"
  },
  "normalized_description": "Frollini Biscotti Mulino Bianco 350 grammi"
}
```

#### 4.2.5 PHASE 5: Enhanced Vector Search

**Obiettivo**: Re-search con descrizione arricchita.

```typescript
// Genera embedding migliorato
const enhancedText = `
  ${extracted.normalized_description}
  ${extracted.brand || ''}
  ${extracted.product_type}
  ${extracted.keywords.join(' ')}
  ${extracted.size} ${extracted.unit}
`.trim();

// "Frollini Biscotti Mulino Bianco 350 grammi Mulino Bianco biscotti frollini biscotti mulino bianco 350 g"

const enhancedEmbedding = await generateEmbedding(enhancedText);

// Re-query vector DB
const enhancedCandidates = await db.query(`
  SELECT
    np.id,
    np.canonical_name,
    np.brand,
    np.category,
    1 - (np.embedding <=> $1::vector) as enhanced_similarity
  FROM normalized_products np
  WHERE np.category = $2  -- Filter by extracted category
    OR np.brand = $3       -- Filter by extracted brand
  ORDER BY np.embedding <=> $1::vector
  LIMIT 5
`, [enhancedEmbedding, extracted.product_type, extracted.brand]);
```

**Combina risultati**:
```typescript
// Merge PHASE 3 + PHASE 5 results
const allCandidates = mergeDeduplicate([
  ...phase3Candidates,  // Semantic originale
  ...phase5Candidates   // Semantic arricchito
]);

// Prendi top 3 unici per final decision
const topCandidates = allCandidates
  .sort((a, b) => b.combined_score - a.combined_score)
  .slice(0, 3);
```

#### 4.2.6 PHASE 6: LLM Final Decision + Multi-Signal Scoring

**Input Completo**:
```typescript
const finalDecisionInput = {
  raw_name: "FTT BSCTT MULBCO 350G",
  current_price: 2.49,
  store: "Esselunga",

  // Extracted features from Phase 4
  extracted_features: {
    product_type: "biscotti",
    brand: "Mulino Bianco",
    normalized_description: "Frollini Biscotti Mulino Bianco 350g"
  },

  // Candidates from Phase 2 (fuzzy)
  fuzzy_matches: [
    {canonical_name: "Frollini Mulino Bianco 350g", text_similarity: 0.88}
  ],

  // Candidates from Phase 3 + 5 (semantic)
  semantic_matches: [
    {
      canonical_name: "Frollini Mulino Bianco 350g",
      brand: "Mulino Bianco",
      category: "Dolci",
      subcategory: "Biscotti",
      semantic_similarity: 0.94,
      enhanced_similarity: 0.96
    },
    {
      canonical_name: "Biscotti Oro Saiwa 350g",
      semantic_similarity: 0.78
    }
  ],

  // Context
  household_history: {
    similar_products: ["Frollini Mulino Bianco 350g", "Pan di Stelle 350g"],
    frequent_brands: ["Mulino Bianco", "Barilla"],
    this_store_products: ["Frollini Mulino Bianco 350g"]
  },

  store_context: {
    name: "Esselunga",
    typical_brands: ["Mulino Bianco", "Barilla", "Ferrero"],
    price_point: "medio-alto"
  }
};
```

**Prompt**:
```typescript
const finalPrompt = `Sei un esperto di prodotti retail italiano.
Dato il nome grezzo e i candidati, seleziona il prodotto più probabile
o proponi di crearne uno nuovo.

Input:
${JSON.stringify(finalDecisionInput, null, 2)}

Analizza:
1. Fuzzy text matches (se presenti)
2. Semantic similarity scores
3. Extracted features vs candidate features
4. Storico acquisti household (preferenze)
5. Coerenza brand/store
6. Coherenza prezzo

Output JSON:
{
  "decision": "existing_product" | "new_product",
  "product_id": "uuid o null",
  "confidence_breakdown": {
    "text_similarity": 0.0-1.0,
    "semantic_similarity": 0.0-1.0,
    "context_match": 0.0-1.0,
    "price_coherence": 0.0-1.0,
    "llm_confidence": 0.0-1.0
  },
  "final_confidence": 0.0-1.0,
  "reasoning": "spiegazione dettagliata",
  "new_product": { ... } // solo se decision="new_product"
}
`;
```

**Output Example**:
```json
{
  "decision": "existing_product",
  "product_id": "uuid-frollini-mulbco",
  "confidence_breakdown": {
    "text_similarity": 0.88,
    "semantic_similarity": 0.96,
    "context_match": 0.92,
    "price_coherence": 0.95,
    "llm_confidence": 0.95
  },
  "final_confidence": 0.93,
  "reasoning": "Match eccellente su tutti i segnali. Abbreviazioni decodificate correttamente (FTT=Frollini, BSCTT=Biscotti, MULBCO=Mulino Bianco). Utente ha già comprato questo prodotto. Prezzo 2.49€ coerente con categoria. Brand e store coerenti (Mulino Bianco è comune in Esselunga).",
  "alternative_interpretations": []
}
```

### 4.3 STEP 2: Validazione Avanzata

#### 4.3.1 Multi-Signal Confidence Aggregation

```typescript
function calculateFinalConfidence(breakdown) {
  // Weighted average
  const weights = {
    text_similarity: 0.15,
    semantic_similarity: 0.35,
    context_match: 0.25,
    price_coherence: 0.15,
    llm_confidence: 0.10
  };

  const weightedSum = Object.entries(weights).reduce((sum, [key, weight]) => {
    return sum + (breakdown[key] * weight);
  }, 0);

  return weightedSum;
}

// Example:
const finalScore = calculateFinalConfidence({
  text_similarity: 0.88,
  semantic_similarity: 0.96,
  context_match: 0.92,
  price_coherence: 0.95,
  llm_confidence: 0.95
});
// = 0.88*0.15 + 0.96*0.35 + 0.92*0.25 + 0.95*0.15 + 0.95*0.10
// = 0.132 + 0.336 + 0.230 + 0.142 + 0.095
// = 0.935 ✅
```

**Thresholds**:
```typescript
if (finalScore >= 0.85) {
  return {status: 'AUTO_VERIFIED', confidence: finalScore};
}

if (finalScore >= 0.70 && finalScore < 0.85) {
  return {
    status: 'PENDING_REVIEW',
    priority: 'low',  // Soft review (bassa priorità)
    confidence: finalScore
  };
}

// finalScore < 0.70
return {
  status: 'PENDING_REVIEW',
  priority: 'high',  // Hard review (alta priorità)
  confidence: finalScore
};
```

#### 4.3.2 Consistency Checks (Rule-Based)

```typescript
function runConsistencyChecks(product, context) {
  const failures = [];

  // Check 1: Size + Unit validation
  const invalidSizeUnit = [
    {unit: 'kg', maxSize: 50, product: 'food'},
    {unit: 'l', maxSize: 20, product: 'beverage'},
    {unit: 'g', maxSize: 5000, product: 'food'}
  ];

  const sizeNum = parseFloat(product.size);
  const rule = invalidSizeUnit.find(r => r.unit === product.unit_type);
  if (rule && sizeNum > rule.maxSize) {
    failures.push({
      check: 'size_unit_validation',
      message: `${sizeNum}${product.unit_type} è improbabile per ${product.category}`
    });
  }

  // Check 2: Category + Store match
  const categoryStoreRules = {
    'Farmaci': ['pharmacy'],
    'Alimenti Freschi': ['supermarket', 'grocery'],
    'Elettronica': ['electronics']
  };

  const storeType = getStoreType(context.store_name);
  const allowedStores = categoryStoreRules[product.category] || [];
  if (allowedStores.length && !allowedStores.includes(storeType)) {
    failures.push({
      check: 'category_store_mismatch',
      message: `${product.category} in ${storeType} è insolito`
    });
  }

  // Check 3: Brand + Product consistency
  const brandProductRules = {
    'Barilla': ['Pasta', 'Sughi', 'Biscotti'],
    'Mulino Bianco': ['Biscotti', 'Merendine', 'Fette'],
    'Ferrero': ['Cioccolato', 'Creme spalmabili']
  };

  if (product.brand && brandProductRules[product.brand]) {
    const validCategories = brandProductRules[product.brand];
    if (!validCategories.some(cat => product.category.includes(cat))) {
      failures.push({
        check: 'brand_product_mismatch',
        message: `${product.brand} non produce tipicamente ${product.category}`
      });
    }
  }

  // Check 4: Price sanity
  const categoryPriceRanges = {
    'Biscotti': {min: 0.50, max: 10.00},
    'Bevande': {min: 0.30, max: 15.00},
    'Elettronica': {min: 5.00, max: 2000.00}
  };

  const priceRange = categoryPriceRanges[product.category];
  if (priceRange && context.current_price) {
    if (context.current_price < priceRange.min || context.current_price > priceRange.max) {
      failures.push({
        check: 'price_sanity',
        message: `Prezzo ${context.current_price}€ fuori range per ${product.category}`
      });
    }
  }

  return failures;
}

// Se fails critici → Force review
const failures = runConsistencyChecks(product, context);
if (failures.length > 0) {
  return {
    status: 'PENDING_REVIEW',
    priority: 'high',
    reason: 'consistency_check_failed',
    failures
  };
}
```

#### 4.3.3 Duplicate Detection

**Problema**: Evitare prodotti normalizzati quasi identici.

```sql
-- Check similarity con prodotti esistenti
SELECT
  np.id,
  np.canonical_name,
  similarity(np.canonical_name, 'Frollini Mulino Bianco 350g') as name_similarity
FROM normalized_products np
WHERE np.canonical_name % 'Frollini Mulino Bianco 350g'  -- Trigram
  AND np.brand = 'Mulino Bianco'
  AND np.category = 'Dolci'
ORDER BY name_similarity DESC
LIMIT 3;
```

**Output**:
```typescript
[
  {
    canonical_name: "Frollini Mulino Bianco 350 g",  // Spazio diverso
    name_similarity: 0.95
  },
  {
    canonical_name: "Frollini Mulino Bianco 0.35kg",  // Unità diversa
    name_similarity: 0.88
  }
]
```

**Logic**:
```typescript
if (newProduct.decision === 'new_product') {
  const duplicates = await findSimilarProducts(newProduct);

  if (duplicates.some(d => d.name_similarity > 0.90)) {
    // Possibile duplicato!
    return {
      status: 'PENDING_REVIEW',
      priority: 'high',
      reason: 'potential_duplicate',
      suggested_merge: duplicates[0],
      message: 'Prodotto molto simile già esistente. Verificare se è duplicato o variante.'
    };
  }
}
```

#### 4.3.4 Human-in-the-Loop Prioritization

**Ordine Review Queue**:
```sql
SELECT
  pm.id,
  pm.raw_name,
  np.canonical_name,
  pm.confidence_score,

  -- Priority factors
  COUNT(DISTINCT ph.id) as purchase_frequency,
  MAX(ph.purchase_date) as recency,
  AVG(ph.total_price) as impact,  -- Prodotti costosi = priorità
  (1.0 - pm.confidence_score) as confidence_gap,

  -- Composite priority score
  (
    COUNT(DISTINCT ph.id) * 10 +  -- Frequenza (peso 10)
    CASE
      WHEN MAX(ph.purchase_date) > NOW() - INTERVAL '7 days' THEN 20
      WHEN MAX(ph.purchase_date) > NOW() - INTERVAL '30 days' THEN 10
      ELSE 0
    END +  -- Recency bonus
    (AVG(ph.total_price) / 10) +  -- Impact (ogni 10€ = 1 punto)
    ((1.0 - pm.confidence_score) * 15)  -- Incertezza (peso 15)
  ) as priority_score

FROM product_mappings pm
JOIN normalized_products np ON np.id = pm.normalized_product_id
LEFT JOIN purchase_history ph ON ph.normalized_product_id = np.id
WHERE pm.requires_manual_review = true
  AND np.verification_status = 'pending_review'
GROUP BY pm.id, np.id
ORDER BY priority_score DESC;
```

**Smart Batching**:
```typescript
// Raggruppa prodotti simili dello stesso scontrino
const reviewBatches = groupBy(reviewQueue, (item) => {
  return `${item.receipt_id}_${item.category}`;
});

// Presenta all'utente:
// "Hai 5 prodotti categoria 'Biscotti' nello scontrino #123"
// [x] Frollini Mulino Bianco 350g (confidence: 0.82)
// [x] Pan di Stelle 350g (confidence: 0.79)
// ...
// [Approva tutti] [Rivedi singolarmente]
```

#### 4.3.5 Continuous Learning Pipeline

**User Feedback → Training Data**:

```typescript
async function processFeedback(feedbackEvent) {
  const {type, productId, mappingId, userId, correctedData} = feedbackEvent;

  if (type === 'APPROVED') {
    // Salva come golden pair
    await db.query(`
      INSERT INTO ml_training_data (
        raw_name,
        normalized_product_id,
        feedback_type,
        user_id,
        confidence_scores,
        created_at
      ) VALUES ($1, $2, 'positive', $3, $4, NOW())
    `, [
      mapping.raw_name,
      productId,
      userId,
      mapping.confidence_breakdown
    ]);

    // Re-train embeddings ogni 1000 approvazioni
    const count = await getTrainingDataCount();
    if (count % 1000 === 0) {
      await triggerEmbeddingRetraining();
    }
  }

  if (type === 'REJECTED') {
    // Marca come negative example
    await db.query(`
      INSERT INTO ml_training_data (
        raw_name,
        normalized_product_id,
        feedback_type,
        user_id,
        corrected_product_id,
        rejection_reason,
        created_at
      ) VALUES ($1, $2, 'negative', $3, $4, $5, NOW())
    `, [
      mapping.raw_name,
      mapping.normalized_product_id,
      userId,
      correctedData.product_id,
      correctedData.reason
    ]);

    // Analizza failure mode
    await analyzeFailureMode(mapping, correctedData);
  }

  if (type === 'MANUAL_EDIT') {
    // User ha corretto brand/category/name
    await db.query(`
      INSERT INTO ml_training_data (
        raw_name,
        normalized_product_id,
        feedback_type,
        user_id,
        correction_details,
        reasoning,
        created_at
      ) VALUES ($1, $2, 'correction', $3, $4, $5, NOW())
    `, [
      mapping.raw_name,
      productId,
      userId,
      correctedData,
      `User preferred "${correctedData.canonical_name}" over "${original.canonical_name}"`
    ]);

    // Fine-tune LLM prompt con questi esempi
    await updateLLMFewShotExamples(correctedData);
  }
}
```

**Failure Mode Analysis**:
```typescript
async function analyzeFailureMode(failedMapping, correction) {
  // Quale fase ha fallito?
  const phases = [
    {name: 'exact_cache', passed: failedMapping.cache_hit},
    {name: 'fuzzy_match', passed: failedMapping.fuzzy_score > 0.85},
    {name: 'semantic_search', passed: failedMapping.semantic_score > 0.80},
    {name: 'llm_extraction', passed: failedMapping.extraction_quality > 0.70},
    {name: 'llm_decision', passed: failedMapping.llm_confidence > 0.80}
  ];

  const failedPhases = phases.filter(p => !p.passed);

  // Log per monitoring
  await logMetric('failure_mode', {
    failed_phases: failedPhases.map(p => p.name),
    raw_name: failedMapping.raw_name,
    expected: correction.canonical_name,
    actual: failedMapping.canonical_name
  });

  // Adjust thresholds se pattern sistemico
  if (failedPhases.includes('semantic_search')) {
    // Molte failure in semantic → considera abbassare threshold
    await checkThresholdAdjustment('semantic_similarity');
  }
}
```

### 4.4 Performance Metrics

#### 4.4.1 Latency Breakdown

**Scenario Completo** (tutti 6 phases):
```
PHASE 1: Exact cache lookup:    ~10ms (miss)
PHASE 2: Fuzzy text match:       ~30-50ms (pg_trgm)
PHASE 3: Vector search:          ~20-50ms (pgvector)
PHASE 4: LLM extraction:         ~200-300ms (GPT-4o-mini)
PHASE 5: Enhanced vector search: ~20-50ms
PHASE 6: LLM final decision:     ~200-300ms (GPT-4o-mini)
STEP 2:  Validation:             ~20-30ms
─────────────────────────────────────────────
Total (worst case):              ~700-1000ms
```

**Con Cache Hit (PHASE 1)**:
```
PHASE 1: Exact cache hit:        ~10-20ms
STEP 2:  Light validation:       ~10ms
─────────────────────────────────────────────
Total (best case):               ~20-30ms ⚡⚡⚡
```

**Average** (dopo 3 mesi, 60% cache hits):
```
0.60 * 25ms + 0.40 * 850ms = 15ms + 340ms = ~355ms average
```

#### 4.4.2 Cost Analysis

**Per Prodotto (full recognition)**:
- Embedding #1 (Phase 3): $0.0001
- LLM extraction (Phase 4): $0.0001
- Embedding #2 (Phase 5): $0.0001
- LLM decision (Phase 6): $0.0002
- **Total**: ~$0.0005

**Con Cache (60% hit rate)**:
```
0.60 * $0 + 0.40 * $0.0005 = $0.0002 average
```

**Comparison con Proposta 1**:
- Proposta 1: $0.00006 avg (70% cache after 3mo)
- Proposta 2: $0.0002 avg (60% cache after 3mo)
- **Proposta 2 costa 3.3x di più** ma con accuracy superiore

#### 4.4.3 Accuracy Metrics

**Aspettative**:
- Overall accuracy: **92-96%** (vs 90-94% Proposta 1)
- Cache hit accuracy: **98-99%**
- New recognition accuracy: **88-93%** (multi-phase più robusto)
- Review rate: **8-12%** (vs 10-15% Proposta 1)

**Edge Cases**:
- Abbreviazioni complesse: **+15% accuracy** vs Proposta 1
- Prodotti ambigui: **+10% accuracy**
- Nuovi brand: **+5% accuracy**

### 4.5 Database Requirements

**Aggiuntive rispetto a Proposta 1**:

```sql
-- Enable pg_trgm for fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Trigram index for Phase 2
CREATE INDEX idx_product_mappings_trgm
ON product_mappings USING gin (raw_name gin_trgm_ops);

-- Table for ML training data
CREATE TABLE ml_training_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_name TEXT NOT NULL,
  normalized_product_id UUID REFERENCES normalized_products(id),
  feedback_type TEXT CHECK (feedback_type IN ('positive', 'negative', 'correction')),
  user_id UUID REFERENCES auth.users(id),

  -- Per negative feedback
  corrected_product_id UUID REFERENCES normalized_products(id),
  rejection_reason TEXT,

  -- Per corrections
  correction_details JSONB,
  reasoning TEXT,

  -- Scores per analisi
  confidence_scores JSONB,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indice per training pipeline
CREATE INDEX idx_ml_training_feedback ON ml_training_data(feedback_type, created_at);
CREATE INDEX idx_ml_training_product ON ml_training_data(normalized_product_id);

-- Table for failure mode tracking
CREATE TABLE recognition_failures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_name TEXT,
  failed_phases TEXT[],
  expected_product_id UUID,
  actual_product_id UUID,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_failures_phases ON recognition_failures USING gin(failed_phases);
```

---

## 5. Confronto & Raccomandazioni

### 5.1 Tabella Comparativa Completa

| Aspetto | Proposta 1: Semantic + Cache | Proposta 2: Hybrid Multi-Stage | Winner |
|---------|------------------------------|--------------------------------|--------|
| **Performance** |  |  |  |
| Latency media | ~149ms | ~355ms | ✅ P1 (2.4x più veloce) |
| Latency cache hit | 15-25ms | 20-30ms | ✅ P1 |
| Latency cache miss | 370-620ms | 700-1000ms | ✅ P1 |
| **Costi** |  |  |  |
| Costo per prodotto (full) | $0.0002 | $0.0005 | ✅ P1 (2.5x meno) |
| Costo medio (dopo 3mo) | $0.00006 | $0.0002 | ✅ P1 (3.3x meno) |
| ROI annuale (1000 prod/giorno) | -$51/anno | -$146/anno | ✅ P1 |
| **Accuracy** |  |  |  |
| Overall accuracy | 90-94% | 92-96% | ✅ P2 (+2-3%) |
| Cache hit accuracy | 95-98% | 98-99% | ✅ P2 |
| New recognition accuracy | 85-90% | 88-93% | ✅ P2 |
| Abbreviazioni complesse | Buono | Eccellente | ✅ P2 |
| Prodotti ambigui | Buono | Molto Buono | ✅ P2 |
| **User Experience** |  |  |  |
| Review rate | 10-15% | 8-12% | ✅ P2 (meno review) |
| Review prioritization | Base | Avanzata | ✅ P2 |
| Duplicate detection | No | Sì | ✅ P2 |
| Batch approval | No | Sì | ✅ P2 |
| **Scalabilità** |  |  |  |
| Scalabilità prodotti | Eccellente | Buona | ✅ P1 |
| Scalabilità query | Eccellente | Buona | ✅ P1 |
| Gestione picchi | Ottima | Buona | ✅ P1 |
| **Implementazione** |  |  |  |
| Complessità codice | ⭐⭐ Media | ⭐⭐⭐⭐ Alta | ✅ P1 |
| Tempo sviluppo | 1-2 settimane | 4-6 settimane | ✅ P1 (3x più veloce) |
| Debugging difficulty | Facile | Difficile | ✅ P1 |
| Manutenibilità | Alta | Media | ✅ P1 |
| **Features** |  |  |  |
| Smart cache | ✅ Sì | ✅ Sì | Pari |
| Vector search | ✅ Sì | ✅ Sì | Pari |
| Fuzzy matching | ❌ No | ✅ Sì | ✅ P2 |
| LLM extraction | ❌ No | ✅ Sì | ✅ P2 |
| Multi-signal confidence | ❌ No | ✅ Sì | ✅ P2 |
| Continuous learning | ⚠️ Base | ✅ Avanzato | ✅ P2 |
| **Cold Start** |  |  |  |
| Catalogo vuoto | Difficile | Gestibile | ✅ P2 (fuzzy fallback) |
| Primi 100 prodotti | 65% accuracy | 75% accuracy | ✅ P2 |
| Dopo 1000 prodotti | 85% accuracy | 90% accuracy | ✅ P2 |
| **Monitoring** |  |  |  |
| Failure analysis | Base | Avanzato | ✅ P2 |
| Training pipeline | Manuale | Automatico | ✅ P2 |
| A/B testing support | Limitato | Completo | ✅ P2 |

### 5.2 Scenari d'Uso Consigliati

#### Quando Scegliere Proposta 1

✅ **MVP / Launch Rapido**
- Vuoi andare in produzione in 1-2 settimane
- Budget di sviluppo limitato
- Team piccolo (1-2 sviluppatori)

✅ **Catalogo Prodotti Stabile**
- Prodotti comuni e ben definiti
- Brand riconoscibili
- Abbreviazioni standard

✅ **Basso Volume Iniziale**
- <5000 scontrini/mese nei primi mesi
- Pochi prodotti unici (<1000)

✅ **Costi Priorità**
- Budget API limitato
- Ogni centesimo conta

✅ **User Review Accettabile**
- Utenti disposti a revieware 10-15% prodotti
- Review considerata parte dell'esperienza

#### Quando Scegliere Proposta 2

✅ **Produzione Enterprise / Long-term**
- Investimento a lungo termine
- Team dedicato (3+ sviluppatori)
- Infrastruttura robusta richiesta

✅ **Catalogo Complesso**
- Prodotti con abbreviazioni oscure
- Molti brand locali/poco noti
- Descrizioni ambigue frequenti

✅ **Alto Volume**
- >20000 scontrini/mese
- Migliaia di prodotti unici
- Crescita rapida prevista

✅ **Accuracy Critica**
- Review deve essere <10%
- Errori costosi (es: analytics errate)
- Utenti professionali (es: business analytics)

✅ **Continuous Improvement**
- Investimento in ML/AI a lungo termine
- Dati di training preziosi
- A/B testing e ottimizzazione continua

### 5.3 Raccomandazione Finale

**Approccio Graduale (Consigliato)**:

#### Fase 1: MVP con Proposta 1 (Mese 1-2)
```
✅ Implementa Proposta 1 completa
✅ Raccogli metriche baseline
✅ Identifica failure patterns
✅ Valida con utenti reali
```

**Metrics da tracciare**:
- Cache hit rate
- Accuracy per categoria prodotto
- Review rate per negozio
- User satisfaction score

#### Fase 2: Valutazione (Mese 3)
```
📊 Analizza dati raccolti:
   - Quali categorie hanno bassa accuracy?
   - Quali abbreviazioni non riconosciute?
   - Dove gli utenti correggono di più?

🎯 Identifica gap:
   - Fuzzy matching risolverebbe X% errori?
   - LLM extraction necessaria per categoria Y?
   - Multi-signal scoring migliorerebbe Z%?
```

#### Fase 3: Hybrid Enhancement (Mese 4-6) - OPZIONALE
```
Se gap significativi (accuracy <85% in categorie chiave):
✅ Aggiungi PHASE 2 (fuzzy matching) a Proposta 1
✅ Aggiungi PHASE 4 (LLM extraction) per categorie problematiche
✅ Implementa multi-signal scoring
✅ A/B test: P1 vs P1+enhancements vs P2
```

#### Fase 4: Continuous Optimization (Ongoing)
```
✅ Implementa continuous learning pipeline
✅ Monitora e ajusta thresholds
✅ Fine-tune embeddings con feedback utenti
✅ Espandi cache coverage
```

### 5.4 Decision Tree

```
START: Devo scegliere architettura riconoscimento prodotti
│
├─ Team <2 dev E Budget limitato E Timeline <1 mese
│  └─→ PROPOSTA 1 ✅
│
├─ Catalogo prodotti semplice E Brand noti E Abbreviazioni standard
│  └─→ PROPOSTA 1 ✅
│
├─ Accuracy >95% richiesta E Budget API alto E Team 3+ dev
│  └─→ PROPOSTA 2 ✅
│
├─ Prodotti molto ambigui E Abbreviazioni oscure E Multi-lingua
│  └─→ PROPOSTA 2 ✅
│
└─ Caso medio: volume medio, accuracy 90%+ sufficiente, team 2 dev
   └─→ PROPOSTA 1 + Roadmap a PROPOSTA 2 ✅ (Approccio Graduale)
```

---

## 6. Implementation Roadmap

### 6.1 Roadmap Proposta 1

#### Sprint 1: Setup & Infrastructure (1 settimana)
- [ ] Setup Supabase pgvector extension
- [ ] Crea schema changes (embedding column, indexes)
- [ ] Setup OpenAI API client
- [ ] Implementa embedding generation utility
- [ ] Crea materialized view `product_cache_stats`
- [ ] Setup refresh job (pg_cron)

#### Sprint 2: PHASE 0 Cache (3 giorni)
- [ ] Implementa `get_cached_product()` function
- [ ] API endpoint cache lookup
- [ ] Integra cache nel flusso principale
- [ ] Tests cache hit/miss scenarios
- [ ] Monitoring cache hit rate

#### Sprint 3: STEP 1 Recognition (1 settimana)
- [ ] Implementa vector embedding generation
- [ ] Query pgvector per semantic search
- [ ] Context enrichment (household history, store stats)
- [ ] LLM reasoning prompt engineering
- [ ] Integra OpenAI GPT-4o-mini
- [ ] Structured JSON output parsing
- [ ] Error handling & retries

#### Sprint 4: STEP 2 Validation (3 giorni)
- [ ] Source-based validation logic
- [ ] Anomaly detection rules
- [ ] Cache update logic
- [ ] User feedback handlers
- [ ] Integration tests end-to-end

#### Sprint 5: Migration & Backfill (3 giorni)
- [ ] Genera embeddings per prodotti esistenti
- [ ] Batch processing script
- [ ] Validazione embeddings quality
- [ ] Deploy to staging
- [ ] Load testing

#### Sprint 6: Launch & Monitor (ongoing)
- [ ] Deploy to production
- [ ] Setup dashboards (Grafana/Datadog)
- [ ] Monitor KPIs
- [ ] Collect user feedback
- [ ] Iterative improvements

**Timeline Totale: 3-4 settimane**

### 6.2 Roadmap Proposta 2

#### Sprint 1-2: Setup (identico a P1)

#### Sprint 3: PHASE 1-2 (1 settimana)
- [ ] PHASE 1: Exact cache (identico P1)
- [ ] PHASE 2: Enable pg_trgm extension
- [ ] Implementa fuzzy matching queries
- [ ] Crea trigram indexes
- [ ] Tests fuzzy match accuracy

#### Sprint 4: PHASE 3-5 (1.5 settimane)
- [ ] PHASE 3: Semantic search (identico P1)
- [ ] PHASE 4: LLM extraction prompt
- [ ] Abbreviation decoder (Italian-specific)
- [ ] Feature extraction logic
- [ ] PHASE 5: Enhanced embedding generation
- [ ] Re-search with enriched embedding
- [ ] Candidate merging & deduplication

#### Sprint 5: PHASE 6 Multi-Signal (1 settimana)
- [ ] LLM final decision prompt
- [ ] Multi-signal confidence aggregation
- [ ] Weighted scoring algorithm
- [ ] Tuning weights empiricamente
- [ ] Structured output validation

#### Sprint 6: Advanced Validation (1 settimana)
- [ ] Consistency checks (size/unit, category/store, etc)
- [ ] Duplicate detection
- [ ] Smart batching logic
- [ ] Priority queue implementation
- [ ] Review UI enhancements

#### Sprint 7: Continuous Learning (1 settimana)
- [ ] Crea `ml_training_data` table
- [ ] Feedback collection pipeline
- [ ] Failure mode analysis
- [ ] Training data export scripts
- [ ] Embedding retraining scheduler

#### Sprint 8: Testing & Migration (1 settimana)
- [ ] Comprehensive integration tests
- [ ] A/B testing setup
- [ ] Backfill embeddings
- [ ] Load testing (Phase 1-6)
- [ ] Performance optimization

#### Sprint 9: Launch (identico P1)

**Timeline Totale: 8-10 settimane**

### 6.3 Milestone Checklist

**Proposta 1 MVP**:
- [ ] ✅ Cache hit rate >60% after 1 month
- [ ] ✅ Average latency <200ms
- [ ] ✅ Accuracy >88% overall
- [ ] ✅ Review rate <18%
- [ ] ✅ Zero downtime deployment
- [ ] ✅ Cost per product <$0.0001

**Proposta 2 Production**:
- [ ] ✅ Cache hit rate >55% after 1 month
- [ ] ✅ Average latency <400ms
- [ ] ✅ Accuracy >92% overall
- [ ] ✅ Review rate <12%
- [ ] ✅ Duplicate detection working
- [ ] ✅ Continuous learning pipeline active
- [ ] ✅ Failure mode analytics dashboard
- [ ] ✅ A/B testing framework operational

---

## 7. Monitoring & KPIs

### 7.1 Key Performance Indicators

#### Performance KPIs
```sql
-- Latency P50, P95, P99
SELECT
  percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms) as p50,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95,
  percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99
FROM recognition_metrics
WHERE created_at > NOW() - INTERVAL '24 hours';

-- Cache hit rate
SELECT
  COUNT(*) FILTER (WHERE source = 'verified_cache') * 100.0 / COUNT(*) as cache_hit_rate
FROM recognition_metrics
WHERE created_at > NOW() - INTERVAL '7 days';

-- API costs tracking
SELECT
  DATE_TRUNC('day', created_at) as day,
  SUM(openai_cost) as total_cost,
  COUNT(*) as total_calls,
  AVG(openai_cost) as avg_cost_per_call
FROM recognition_metrics
GROUP BY day
ORDER BY day DESC;
```

#### Accuracy KPIs
```sql
-- Overall accuracy
SELECT
  COUNT(*) FILTER (WHERE verified_by_user = true AND user_correction = false) * 100.0 /
  COUNT(*) FILTER (WHERE verified_by_user = true) as accuracy
FROM product_mappings
WHERE created_at > NOW() - INTERVAL '30 days';

-- Accuracy by category
SELECT
  np.category,
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE pm.verified_by_user = true AND user_correction = false) as correct,
  COUNT(*) FILTER (WHERE pm.verified_by_user = true AND user_correction = false) * 100.0 /
    NULLIF(COUNT(*) FILTER (WHERE pm.verified_by_user = true), 0) as accuracy_pct
FROM product_mappings pm
JOIN normalized_products np ON np.id = pm.normalized_product_id
WHERE pm.created_at > NOW() - INTERVAL '30 days'
GROUP BY np.category
ORDER BY total DESC;

-- Review rate
SELECT
  COUNT(*) FILTER (WHERE requires_manual_review = true) * 100.0 / COUNT(*) as review_rate
FROM product_mappings
WHERE created_at > NOW() - INTERVAL '7 days';
```

#### Business KPIs
```sql
-- Products recognized per day
SELECT
  DATE_TRUNC('day', created_at) as day,
  COUNT(*) as products_recognized,
  COUNT(DISTINCT normalized_product_id) as unique_products
FROM product_mappings
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY day
ORDER BY day;

-- New products created
SELECT
  DATE_TRUNC('week', created_at) as week,
  COUNT(*) as new_products
FROM normalized_products
WHERE created_at > NOW() - INTERVAL '12 weeks'
GROUP BY week
ORDER BY week;

-- User engagement (review completion rate)
SELECT
  COUNT(*) FILTER (WHERE reviewed_by IS NOT NULL) * 100.0 /
  COUNT(*) FILTER (WHERE requires_manual_review = true) as review_completion_rate
FROM product_mappings
WHERE created_at > NOW() - INTERVAL '30 days';
```

### 7.2 Dashboard Recommendations

**Real-time Dashboard** (Grafana/Datadog):
- Cache hit rate (last 24h)
- Average latency P50/P95/P99
- Recognition throughput (products/min)
- Error rate
- API costs (cumulative)

**Weekly Dashboard**:
- Overall accuracy trend
- Accuracy by category
- Review rate trend
- New products created
- Top failing raw names
- Most reviewed categories

**Monthly Dashboard**:
- Cost analysis & ROI
- User engagement metrics
- Catalog growth
- Cache coverage
- A/B test results (if running)

### 7.3 Alerting Rules

```yaml
# Example alerting config
alerts:
  - name: high_latency
    condition: p95_latency > 1000ms
    duration: 5m
    severity: warning

  - name: low_cache_hit_rate
    condition: cache_hit_rate < 40%
    duration: 1h
    severity: warning

  - name: high_error_rate
    condition: error_rate > 5%
    duration: 5m
    severity: critical

  - name: low_accuracy
    condition: accuracy < 85%
    duration: 1d
    severity: warning

  - name: api_cost_spike
    condition: daily_cost > avg_daily_cost * 2
    duration: 1h
    severity: warning
```

---

## 8. Appendici

### 8.1 SQL Query Examples

#### A. Cache Lookup con Statistics
```sql
-- Completo cache lookup con tutti i metadata
WITH cache_candidate AS (
  SELECT
    pm.id as mapping_id,
    pm.normalized_product_id,
    np.canonical_name,
    np.brand,
    np.category,
    np.subcategory,
    pm.confidence_score as original_confidence,
    pm.verified_by_user,
    pm.created_at as mapping_created_at
  FROM product_mappings pm
  JOIN normalized_products np ON np.id = pm.normalized_product_id
  WHERE pm.raw_name = $1  -- 'COCA COLA PET 1.5L'
    AND pm.store_name = $2  -- 'Conad'
    AND pm.verified_by_user = true
    AND np.verification_status NOT IN ('rejected')
  ORDER BY pm.confidence_score DESC, pm.created_at DESC
  LIMIT 1
),
usage_stats AS (
  SELECT
    COUNT(DISTINCT ph.id) as usage_count,
    MAX(ph.purchase_date) as last_used,
    MIN(ph.purchase_date) as first_used,
    COUNT(DISTINCT ph.household_id) as verified_by_households,
    AVG(ph.unit_price) as avg_price,
    STDDEV(ph.unit_price) as price_stddev
  FROM purchase_history ph
  WHERE ph.normalized_product_id = (SELECT normalized_product_id FROM cache_candidate)
)
SELECT
  cc.*,
  us.*,
  -- Price coherence check
  CASE
    WHEN $3 IS NULL THEN true  -- $3 = current_price
    WHEN us.avg_price IS NULL THEN true
    WHEN ABS($3 - us.avg_price) / us.avg_price <= 0.30 THEN true
    ELSE false
  END as price_coherent,
  -- Recency check
  CASE
    WHEN us.last_used > CURRENT_DATE - INTERVAL '180 days' THEN true
    ELSE false
  END as recently_used,
  -- Confidence boost
  0.90 +
    CASE WHEN us.usage_count > 10 THEN 0.02 ELSE 0 END +
    CASE WHEN us.verified_by_households >= 3 THEN 0.03 ELSE 0 END +
    CASE WHEN us.last_used > CURRENT_DATE - INTERVAL '30 days' THEN 0.02 ELSE 0 END
  as boosted_confidence
FROM cache_candidate cc
CROSS JOIN usage_stats us;
```

#### B. Vector Search con Filtri
```sql
-- Semantic search con category e brand filtering
SELECT
  np.id,
  np.canonical_name,
  np.brand,
  np.category,
  np.subcategory,
  np.size,
  np.unit_type,
  np.verification_status,
  1 - (np.embedding <=> $1::vector) as similarity,

  -- Usage statistics join
  COUNT(DISTINCT ph.id) as times_purchased,
  AVG(ph.unit_price) as avg_price

FROM normalized_products np
LEFT JOIN purchase_history ph ON ph.normalized_product_id = np.id

WHERE
  np.verification_status != 'rejected'
  -- Optional filters
  AND (np.category = $2 OR $2 IS NULL)  -- Category filter
  AND (np.brand = $3 OR $3 IS NULL)     -- Brand filter

GROUP BY np.id

-- Order by similarity
ORDER BY np.embedding <=> $1::vector

LIMIT $4;  -- Top K
```

#### C. Multi-Signal Confidence Aggregation
```sql
-- Calculate weighted confidence score
WITH confidence_signals AS (
  SELECT
    pm.id,
    pm.raw_name,
    pm.normalized_product_id,

    -- Signal 1: Text similarity (from fuzzy match)
    COALESCE(
      (SELECT MAX(similarity(pm2.raw_name, pm.raw_name))
       FROM product_mappings pm2
       WHERE pm2.normalized_product_id = pm.normalized_product_id
         AND pm2.id != pm.id),
      0
    ) as text_similarity,

    -- Signal 2: Semantic similarity (from vector search)
    pm.semantic_score,

    -- Signal 3: Context match (household + store)
    (
      CASE WHEN EXISTS (
        SELECT 1 FROM purchase_history ph
        WHERE ph.household_id = $1
          AND ph.normalized_product_id = pm.normalized_product_id
      ) THEN 0.8 ELSE 0.2 END
      +
      CASE WHEN EXISTS (
        SELECT 1 FROM purchase_history ph
        JOIN receipts r ON r.id = ph.receipt_id
        WHERE r.store_name = $2
          AND ph.normalized_product_id = pm.normalized_product_id
      ) THEN 0.2 ELSE 0 END
    ) as context_match,

    -- Signal 4: Price coherence
    CASE
      WHEN ABS($3 - (
        SELECT AVG(unit_price)
        FROM purchase_history
        WHERE normalized_product_id = pm.normalized_product_id
      )) / NULLIF((
        SELECT AVG(unit_price)
        FROM purchase_history
        WHERE normalized_product_id = pm.normalized_product_id
      ), 0) <= 0.30
      THEN 1.0
      ELSE 0.5
    END as price_coherence,

    -- Signal 5: LLM confidence
    pm.llm_confidence

  FROM product_mappings pm
  WHERE pm.id = $4  -- Mapping ID
)
SELECT
  *,
  -- Weighted average (total = 1.0)
  (
    text_similarity * 0.15 +
    semantic_score * 0.35 +
    context_match * 0.25 +
    price_coherence * 0.15 +
    llm_confidence * 0.10
  ) as final_confidence
FROM confidence_signals;
```

### 8.2 Example Flow: Complete Recognition

**Input**:
```json
{
  "raw_product_name": "COCA COLA PET 1.5L",
  "store_name": "Conad",
  "current_price": 1.29,
  "household_id": "hh-123",
  "receipt_id": "rec-456"
}
```

**PHASE 0: Cache Lookup** ✅ HIT
```json
{
  "source": "verified_cache",
  "product_id": "prod-789",
  "canonical_name": "Coca Cola 1.5L",
  "brand": "Coca Cola",
  "category": "Bevande",
  "subcategory": "Bibite Gassate",
  "confidence": 0.92,
  "cache_metadata": {
    "usage_count": 15,
    "last_used": "2025-10-20",
    "verified_by_households": 3,
    "avg_price": 1.25,
    "price_coherent": true,
    "recently_used": true
  },
  "skip_recognition": true
}
```

**STEP 2: Light Validation**
```json
{
  "status": "AUTO_VERIFIED",
  "confidence": 0.92,
  "validation_checks": {
    "price_coherence": true,
    "recency": true,
    "anomalies": []
  },
  "requires_review": false
}
```

**Final Output**:
```json
{
  "product_id": "prod-789",
  "canonical_name": "Coca Cola 1.5L",
  "brand": "Coca Cola",
  "category": "Bevande",
  "subcategory": "Bibite Gassate",
  "confidence": 0.92,
  "status": "AUTO_VERIFIED",
  "source": "verified_cache",
  "latency_ms": 18,
  "cost": 0.0
}
```

### 8.3 Example Flow: New Product Recognition

**Input**:
```json
{
  "raw_product_name": "FTT BSCTT MULBCO 350G",
  "store_name": "Esselunga",
  "current_price": 2.49,
  "household_id": "hh-123"
}
```

**PHASE 0: Cache** ❌ MISS

**STEP 1 (Proposta 2): Multi-Phase Recognition**

*PHASE 2: Fuzzy Match* - No results

*PHASE 3: Vector Search*
```json
[
  {
    "id": "prod-999",
    "canonical_name": "Frollini Mulino Bianco 350g",
    "similarity": 0.82
  },
  {
    "id": "prod-888",
    "canonical_name": "Biscotti Oro Saiwa 350g",
    "similarity": 0.71
  }
]
```

*PHASE 4: LLM Extraction*
```json
{
  "product_type": "biscotti",
  "brand": "Mulino Bianco",
  "size": "350",
  "unit": "g",
  "keywords": ["frollini", "biscotti", "mulino", "bianco"],
  "abbreviations_decoded": {
    "FTT": "Frollini",
    "BSCTT": "Biscotti",
    "MULBCO": "Mulino Bianco"
  },
  "normalized_description": "Frollini Biscotti Mulino Bianco 350 grammi"
}
```

*PHASE 5: Enhanced Vector Search*
```json
[
  {
    "id": "prod-999",
    "canonical_name": "Frollini Mulino Bianco 350g",
    "enhanced_similarity": 0.96
  }
]
```

*PHASE 6: LLM Final Decision*
```json
{
  "decision": "existing_product",
  "product_id": "prod-999",
  "confidence_breakdown": {
    "text_similarity": 0.0,
    "semantic_similarity": 0.96,
    "context_match": 0.85,
    "price_coherence": 0.92,
    "llm_confidence": 0.95
  },
  "final_confidence": 0.91,
  "reasoning": "Abbrev. decodificate correttamente. Match semantico eccellente (0.96) dopo enhancement. Prezzo 2.49€ coerente con categoria biscotti (range 0.50-10€)."
}
```

**STEP 2: Validation** ✅ PASS

**Final Output**:
```json
{
  "product_id": "prod-999",
  "canonical_name": "Frollini Mulino Bianco 350g",
  "brand": "Mulino Bianco",
  "category": "Dolci",
  "subcategory": "Biscotti",
  "confidence": 0.91,
  "status": "AUTO_VERIFIED",
  "source": "semantic_search_multi_phase",
  "latency_ms": 847,
  "cost": 0.0005,
  "interpretation_details": {
    "phases_used": [2, 3, 4, 5, 6],
    "extraction": {/* ... */},
    "reasoning": "..."
  }
}
```

### 8.4 Cost Calculator

```typescript
// Calculator per stima costi mensili
interface CostEstimate {
  productsPerDay: number;
  cacheHitRate: number;  // 0.0 - 1.0
  proposal: 1 | 2;
}

function estimateMonthlyCost(params: CostEstimate): number {
  const {productsPerDay, cacheHitRate, proposal} = params;

  const costPerRecognition = proposal === 1 ? 0.0002 : 0.0005;
  const avgCostPerProduct = (1 - cacheHitRate) * costPerRecognition;

  const dailyCost = productsPerDay * avgCostPerProduct;
  const monthlyCost = dailyCost * 30;

  return monthlyCost;
}

// Examples
console.log(estimateMonthlyCost({
  productsPerDay: 1000,
  cacheHitRate: 0.70,
  proposal: 1
}));
// Output: $1.80/month

console.log(estimateMonthlyCost({
  productsPerDay: 5000,
  cacheHitRate: 0.60,
  proposal: 2
}));
// Output: $30/month

console.log(estimateMonthlyCost({
  productsPerDay: 10000,
  cacheHitRate: 0.75,
  proposal: 1
}));
// Output: $15/month
```

---

## Conclusione

Questo documento fornisce due architetture complete per il riconoscimento prodotti:

- **Proposta 1**: Veloce, economica, facile da implementare. **Ideale per MVP e lancio rapido**.
- **Proposta 2**: Più accurata, robusta, con continuous learning. **Ideale per produzione enterprise**.

**Raccomandazione**: Inizia con **Proposta 1**, valuta dopo 3 mesi, e migra gradualmente a **Proposta 2** solo se necessario.

La chiave del successo è **misurare, iterare, ottimizzare**. Entrambe le architetture includono monitoring completo e feedback loops per migliorare continuamente.

---

**Documento Completo** - Pronto per implementazione.
