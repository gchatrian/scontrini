# Refactoring Roadmap - Sistema Normalizzazione Prodotti

**Versione**: 1.0
**Data**: Ottobre 2025

---

## Setup & Prerequisites

**Già Presente**:
- pgvector extension attiva
- Colonna embedding su normalized_products (18k prodotti, 100% popolata)
- Funzioni search: search_similar_products(), search_products_hybrid()
- UNIQUE constraint (raw_name, store_name) su product_mappings

**Da Implementare**:
- Indice HNSW (attualmente IVFFlat)
- Smart cache 2-tier
- Materialized view cache stats
- Context enrichment
- Validation service

---

## Phase 1: Database Foundation

**Duration**: 2 giorni

**TASK 1: Upgrade Vector Index**
Migrare l'indice esistente da IVFFlat a HNSW per migliorare le performance delle query di similarity search. L'indice HNSW è più performante per dataset sotto i 100k vettori e garantisce latenze sotto i 50ms.

**TASK 2: Cache Indexes**
Creare indici ottimizzati per il sistema di cache a 2 tier. Il Tier 1 indicizza i mapping verificati dagli utenti, il Tier 2 indicizza i mapping auto-verificati con alta confidence. Aggiungere indici su purchase_history per velocizzare le query di context enrichment basate su household e store.

**TASK 3: Materialized View**
Creare una materialized view che aggrega statistiche di utilizzo dei prodotti cached: numero di utilizzi, numero di household che hanno verificato il prodotto, prezzo medio, deviazione standard del prezzo, data ultimo utilizzo. Questa view supporta il calcolo rapido del confidence boost e della price coherence.

**TASK 4: Cache Lookup Function**
Implementare una funzione database che esegue la lookup nella cache, calcola il flag di price coherence confrontando il prezzo corrente con il prezzo medio storico (tolleranza ±30%), e ritorna i dati in formato JSONB per facile consumo dal backend.

---

## Phase 2: Backend Services

**Duration**: 3 giorni

**TASK 1: CacheService**
Implementare il servizio di cache intelligente che interroga la cache lookup function via RPC. Il servizio calcola il confidence boost partendo da un base di 0.90 e aggiungendo incrementi basati su: numero di household che hanno verificato il prodotto, numero di utilizzi totali, recency dell'ultimo utilizzo. In caso di miss nel Tier 1, il servizio esegue fallback al Tier 2 applicando una penalty del 5% al confidence score.

**TASK 2: EmbeddingService**
Creare un wrapper per l'API OpenAI text-embedding-ada-002 che gestisce la generazione degli embeddings. Il servizio include una cache LRU locale per evitare chiamate duplicate, implementa retry logic con exponential backoff per gestire rate limits, e traccia i costi delle chiamate API.

**TASK 3: VectorSearchService**
Implementare il servizio che esegue vector similarity search chiamando la funzione search_similar_products() via RPC. Il servizio arricchisce i risultati con statistiche di acquisto (times_purchased, avg_price) e calcola un ranking pesato che combina similarity semantica e popolarità del prodotto.

**TASK 4: ContextService**
Creare il servizio di context enrichment che interroga lo storico acquisti dell'household e le statistiche del negozio. Per ogni candidato prodotto, il servizio calcola un context match score sommando boost per: prodotto già acquistato dall'utente, prodotto popolare nel negozio specifico, prezzo coerente con lo storico.

**TASK 5: ValidationService**
Implementare il servizio di validazione threshold-based che calcola confidence score e flag di warning per l'utente. Per i cache hits, valida price coherence e recency. Per i risultati semantic, applica thresholds sul confidence score. Prodotti con confidence <0.70 vengono evidenziati come high priority review. Tutti i prodotti vengono sempre mostrati all'utente per review finale.

**TASK 6: CacheUpdateService**
Creare il servizio che aggiorna asincronamente la cache dopo ogni riconoscimento successful. Il servizio usa INSERT ON CONFLICT per aggiornare i mapping esistenti solo se il nuovo confidence è superiore, e triggera il refresh della materialized view in modo throttled per evitare overhead.

---

## Phase 3: Pipeline Integration

**Duration**: 3 giorni

**TASK 1: Refactor ProductNormalizer**
Refactorare la classe ProductNormalizer per iniettare i 6 servizi come dependencies e orchestrare il flusso completo. Implementare PHASE 0 con cache lookup prima di qualsiasi processing LLM, STEP 1 con la catena embedding → vector search → context enrichment → LLM reasoning, STEP 2 con validation (calcolo confidence e warning flags). Tutti i prodotti normalizzati vengono restituiti al frontend per review utente obbligatoria. Cache update avviene SOLO dopo conferma finale utente.

**TASK 2: Config Updates**
Aggiornare il file di configurazione per includere i nuovi parametri MVP: cache base confidence, semantic auto-approve threshold, price coherence tolerance, embedding cache size. Documentare le nuove variabili nel file .env.example.

**TASK 3: Integration Testing**
Sviluppare test end-to-end che verificano l'intera pipeline con dataset reale. Validare accuracy su campione etichettato di almeno 100 prodotti, misurare latenze P95 per cache hits e full pipeline, verificare che i confidence scores siano calcolati correttamente. Testare flusso completo: normalizzazione → review utente → salvataggio finale.

---

## Phase 4: Testing & Launch

**Duration**: 2 giorni

**TASK 1: Load Testing**
Eseguire test di carico simulando 100 utenti concurrent con mix realistico di richieste (70% cache hits, 30% semantic search). Monitorare latenze, connection pool del database, utilizzo CPU e memoria. Identificare eventuali bottleneck.

**TASK 2: Accuracy Validation**
Raccogliere 100 scontrini reali, etichettare manualmente i prodotti (ground truth), eseguire la pipeline su tutti e calcolare metriche di accuracy, precision, recall. Analizzare i falsi positivi e negativi per identificare pattern di errore.

**TASK 3: Edge Cases Testing**
Testare scenari limite: raw_name null o vuoto, prodotti completamente sconosciuti, database temporaneamente non disponibile, OpenAI API down o rate limited. Verificare che gli error messages siano informativi e il sistema degradi gracefully.

**TASK 4: Monitoring Setup**
Configurare logging strutturato in formato JSON con eventi chiave (cache_hit, cache_miss, recognition_success, recognition_failure, user_review_approve, user_review_correct). Implementare tracking di metriche: latenze per ogni fase, cache hit rate, user correction rate, costi API OpenAI.

**TASK 5: Production Deployment**
Eseguire le 4 migration SQL su production database. Deployare il backend aggiornato con strategia zero-downtime. Eseguire smoke tests sulle prime 100 richieste monitorando metriche in real-time. Verificare che il sistema sia stabile prima di annunciare il go-live.

---

**Total Duration**: 10 giorni
