# Implementation Roadmap - Proposta 1: Semantic Search + Smart Cache

**Documento**: Roadmap Operativa Implementazione
**Versione**: 1.0
**Data**: Ottobre 2025
**Timeline Totale**: 5-6 settimane
**Team Size**: 2-3 sviluppatori

---

## 📋 Indice

1. [Overview & Architettura](#1-overview--architettura)
2. [Prerequisites & Setup](#2-prerequisites--setup)
3. [Sprint 0: Preparazione (1 settimana)](#3-sprint-0-preparazione)
4. [Sprint 1: Database Infrastructure (1 settimana)](#4-sprint-1-database-infrastructure)
5. [Sprint 2: PHASE 0 - Smart Cache (1 settimana)](#5-sprint-2-phase-0---smart-cache)
6. [Sprint 3: STEP 1 - Riconoscimento Semantico (1 settimana)](#6-sprint-3-step-1---riconoscimento-semantico)
7. [Sprint 4: STEP 2 - Validazione (4 giorni)](#7-sprint-4-step-2---validazione)
8. [Sprint 5: Testing & Launch (1 settimana)](#8-sprint-5-testing--launch)
9. [Post-Launch: Monitoring & Optimization](#9-post-launch-monitoring--optimization)
10. [Rischi & Mitigazioni](#10-rischi--mitigazioni)
11. [Definition of Done](#11-definition-of-done)
12. [Appendici](#12-appendici)

---

## 1. Overview & Architettura

### 1.1 Cosa Implementeremo

Sistema di riconoscimento prodotti da scontrini che:
- Utilizza cache intelligente per prodotti già visti (70% dei casi dopo 3 mesi)
- Applica vector search semantico per prodotti nuovi
- Valida risultati con anomaly detection e price coherence
- Permette feedback loop utente per miglioramento continuo

### 1.2 Componenti Principali

**PHASE 0: Smart Cache Lookup**
- Query PostgreSQL su product_mappings per exact match
- Store-aware (stesso raw_name + stesso negozio)
- Multi-tier (verified cache vs auto-verified fallback)
- Return con confidence 0.90 se hit

**STEP 1: Riconoscimento Semantico** (se cache miss)
- Vector embedding generation tramite OpenAI Ada
- Semantic search con Supabase pgvector
- Context enrichment (household history, store stats)
- LLM reasoning con GPT-4o-mini per decisione finale

**STEP 2: Validazione**
- Source-based validation (cache vs semantic)
- Anomaly detection (price outliers, category mismatches)
- Cache update logic
- User feedback handling

### 1.3 Metriche di Successo

- **Performance**: Latency media <200ms, cache hit <30ms
- **Accuracy**: Overall >88%, cache hit >95%
- **Cost**: <$0.0001 per prodotto (media pesata)
- **UX**: Review rate <18%
- **Reliability**: Uptime >99.5%

---

## 2. Prerequisites & Setup

### 2.1 Team Richiesto

**Backend Developer** (lead):
- Esperienza PostgreSQL/Supabase
- Conoscenza API OpenAI
- Familiarità con vector databases

**Full-Stack Developer**:
- Next.js/React per UI review
- TypeScript
- Integrazione API

**DevOps/SRE** (part-time):
- Deployment Supabase
- Monitoring setup
- CI/CD pipeline

**Product/QA** (part-time):
- Test case definition
- UAT coordination
- Metrics tracking

### 2.2 Ambiente Tecnico

**Necessario Prima di Iniziare**:
- ✅ Supabase project attivo con database esistente
- ✅ OpenAI API key con credito disponibile
- ✅ Ambiente staging separato da production
- ✅ Repository git con branch strategy definita
- ✅ Access a Supabase SQL editor e dashboard

**Strumenti di Sviluppo**:
- Database client (pgAdmin, DBeaver, o Supabase Studio)
- API testing tool (Postman, Insomnia, o Bruno)
- Monitoring setup (Grafana cloud free tier o Supabase dashboard)
- Project tracking tool (Jira, Linear, Notion, o GitHub Projects)

### 2.3 Conoscenze Prerequisite

**Team Deve Conoscere**:
- Vector embeddings e similarity search (concetti base)
- PostgreSQL indexes e query optimization
- Supabase Row Level Security (RLS)
- LLM prompting best practices
- TypeScript async/await patterns

**Documentazione da Leggere Prima**:
- Supabase pgvector documentation
- OpenAI Embeddings API guide
- Document: product-recognition-architecture.md (sezione Proposta 1)
- Database schema completo in complete_schema.sql

---

## 3. Sprint 0: Preparazione

**Durata**: 1 settimana
**Obiettivo**: Setup completo ambiente e allineamento team

### 3.1 Planning & Design Review

**Task 1.1: Architecture Review Session**
- **Owner**: Backend Lead + Full-Stack Dev
- **Durata**: 2 ore
- **Descrizione**: Workshop team per review architettura Proposta 1
- **Input**: Document product-recognition-architecture.md
- **Output**: Team alignment, domande clarified
- **Acceptance Criteria**:
  - Tutti i membri team hanno letto documentazione
  - Domande architetturali risolte
  - Decisioni tecniche documentate (quale embedding model, quale pgvector index type)
- **Rischi**: Team non allineato su approccio → dedica tempo extra per Q&A

**Task 1.2: Technical Spike - pgvector**
- **Owner**: Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Prova di concetto pgvector su Supabase staging
- **Attività**:
  - Abilita extension pgvector su staging database
  - Crea tabella test con colonna vector
  - Genera 100 embeddings di prova tramite OpenAI
  - Testa query similarity con diversi index types (IVFFlat vs HNSW)
  - Misura performance query (<50ms target)
- **Output**: Report spike con raccomandazione index type
- **Acceptance Criteria**:
  - Extension pgvector funzionante
  - Query similarity <50ms su 100 vettori
  - Decisione presa su index type (HNSW raccomandato per <100k vettori)

**Task 1.3: OpenAI API Integration Spike**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Test integrazione OpenAI embeddings e chat
- **Attività**:
  - Setup OpenAI client library nel backend
  - Test embedding generation per 10 raw product names
  - Test GPT-4o-mini call con prompt reasoning di esempio
  - Verifica response time e costi
  - Implementa error handling base (rate limits, timeouts)
- **Output**: Proof of concept funzionante
- **Acceptance Criteria**:
  - Embeddings generati correttamente (1536 dimensions)
  - LLM response parseable come JSON
  - Latency <300ms per embedding, <400ms per LLM call
  - Cost tracking funzionante

### 3.2 Environment Setup

**Task 2.1: Staging Database Preparation**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Prepara database staging per sviluppo
- **Attività**:
  - Crea nuovo Supabase project per staging (o usa esistente)
  - Esegui complete_schema.sql per ricreare schema
  - Seed database con dati di test (10 households, 50 receipts, 200 products)
  - Verifica RLS policies funzionanti
  - Backup production data se necessario migration
- **Output**: Staging DB pronto per sviluppo
- **Acceptance Criteria**:
  - Schema allineato con production
  - Dati di test rappresentativi
  - RLS testato e funzionante
  - Connessione da backend app verificata

**Task 2.2: Backend Service Structure**
- **Owner**: Backend Lead + Full-Stack Dev
- **Durata**: 4 ore
- **Descrizione**: Setup struttura servizi backend
- **Attività**:
  - Crea cartelle servizi: services/product-recognition/, services/cache/, services/embeddings/
  - Setup dependency injection per OpenAI client, Supabase client
  - Crea interfaces TypeScript per tutti i tipi (ProductRecognitionResult, CacheHit, etc.)
  - Setup error types custom (CacheMissError, EmbeddingError, ValidationError)
  - Configura environment variables (.env.example aggiornato)
- **Output**: Skeleton servizi pronti per implementazione
- **Acceptance Criteria**:
  - Struttura cartelle chiara e modulare
  - Types TypeScript definiti per tutti i componenti
  - Environment variables documentate
  - Test boilerplate setup (Jest o Vitest)

**Task 2.3: Monitoring & Logging Setup**
- **Owner**: DevOps + Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Setup infrastructure per monitoring
- **Attività**:
  - Configura structured logging (Winston o Pino)
  - Setup logging levels (debug, info, warn, error)
  - Crea log formatters per eventi chiave (cache_hit, cache_miss, recognition_success, recognition_failure)
  - Integra Supabase logs forwarding (se disponibile)
  - Setup basic metrics collection (latency, error rate)
  - Configura alerting email/Slack per errori critici
- **Output**: Logging e monitoring framework attivo
- **Acceptance Criteria**:
  - Logs strutturati e leggibili
  - Metrics base tracciabili
  - Alerts configurate per error rate >5%
  - Dashboard Supabase accessibile

### 3.3 Project Management Setup

**Task 3.1: Task Tracking Initialization**
- **Owner**: Product/PM
- **Durata**: 2 ore
- **Descrizione**: Setup project tracking system
- **Attività**:
  - Crea project board (Jira, Linear, GitHub Projects)
  - Import tutti i task da questa roadmap come tickets
  - Assegna labels (backend, frontend, database, testing)
  - Setup sprint views (Sprint 0, 1, 2, etc.)
  - Configura automation (move to "In Progress" quando assigned)
- **Output**: Project board completo e operativo
- **Acceptance Criteria**:
  - Tutti i task importati
  - Sprint planning possibile
  - Team ha accesso e training su tool

**Task 3.2: Testing Strategy Definition**
- **Owner**: QA + Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Definisci strategia testing per il progetto
- **Attività**:
  - Identifica test types necessari (unit, integration, e2e)
  - Definisci coverage target (80% per servizi critici)
  - Crea test data fixtures (raw product names, expected results)
  - Prepara test cases per edge cases (prodotti ambigui, typos, nuovi brand)
  - Documenta UAT scenarios per sprint 5
- **Output**: Testing plan documentato
- **Acceptance Criteria**:
  - Test strategy chiara per ogni sprint
  - Test fixtures preparati
  - UAT scenarios definiti

### 3.4 Sprint 0 Deliverables

**Checklist Fine Sprint 0**:
- [ ] Team allineato su architettura
- [ ] pgvector spike completato e decisione presa
- [ ] OpenAI integration verificata funzionante
- [ ] Staging database setup con dati test
- [ ] Backend service structure creata
- [ ] Monitoring e logging attivi
- [ ] Project tracking operativo
- [ ] Testing strategy documentata
- [ ] Sprint 1 planning meeting schedulato

**Rischi Sprint 0**:
- pgvector non disponibile su Supabase plan attuale → Mitigazione: verifica plan requirements prima
- OpenAI API costs superiori a budget → Mitigazione: usa modelli più economici o riduci test
- Team availability limitata → Mitigazione: prioritizza task critici (2.1, 1.2, 1.3)

---

## 4. Sprint 1: Database Infrastructure

**Durata**: 1 settimana
**Obiettivo**: Preparare database per supportare cache e vector search

### 4.1 Schema Changes

**Task 1.1: Add Embedding Column**
- **Owner**: Backend Lead
- **Durata**: 1 ora
- **Descrizione**: Aggiungi colonna vector a normalized_products
- **Attività**:
  - Esegui ALTER TABLE per aggiungere colonna embedding di tipo vector(1536)
  - Verifica colonna creata correttamente
  - Testa insert di vettore di prova
  - Documenta migration SQL in file versioned (001_add_embedding_column.sql)
- **Input**: Schema attuale da complete_schema.sql
- **Output**: normalized_products con colonna embedding
- **Acceptance Criteria**:
  - Colonna embedding presente in tabella
  - Tipo corretto vector(1536)
  - Migration SQL salvata in scripts/db/migrations/
  - Rollback SQL preparato
- **Dipendenze**: Task Sprint 0.2.1 completato (staging DB ready)

**Task 1.2: Create Vector Index**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Crea indice pgvector per performance
- **Attività**:
  - Decide index type basato su spike (HNSW raccomandato)
  - Esegui CREATE INDEX con parametri ottimizzati (m=16, ef_construction=64 per HNSW)
  - Testa query performance con EXPLAIN ANALYZE
  - Misura query time prima e dopo index
  - Documenta configurazione index scelta
- **Output**: Index funzionante su embedding column
- **Acceptance Criteria**:
  - Index creato senza errori
  - Query similarity <50ms su dataset test
  - EXPLAIN ANALYZE mostra index usage
  - Parametri index documentati
- **Dipendenze**: Task 1.1 completato

**Task 1.3: Cache Lookup Indexes**
- **Owner**: Backend Lead
- **Durata**: 1 ora
- **Descrizione**: Crea indici per fast cache lookup
- **Attività**:
  - Crea composite index su (raw_name, store_name, verified_by_user) nella tabella product_mappings
  - Aggiungi partial index WHERE verified_by_user = true per Tier 1 cache
  - Crea index su (raw_name, store_name, confidence_score) per Tier 2 cache fallback
  - Testa query cache lookup con EXPLAIN
  - Verifica index sia utilizzato
- **Output**: Indexes per cache queries
- **Acceptance Criteria**:
  - Composite index creato
  - Partial index creato
  - Cache query <10ms su dataset test
  - EXPLAIN conferma index usage
- **Dipendenze**: Nessuna (usa schema esistente)

**Task 1.4: Purchase History Indexes**
- **Owner**: Backend Lead
- **Durata**: 1 ora
- **Descrizione**: Ottimizza indexes per context enrichment queries
- **Attività**:
  - Crea index su (normalized_product_id, household_id) in purchase_history
  - Crea index su (normalized_product_id, purchase_date) per usage stats
  - Testa queries per household history e store stats
  - Verifica performance <30ms
- **Output**: Indexes per queries di context
- **Acceptance Criteria**:
  - Indexes creati
  - Queries context enrichment <30ms
  - EXPLAIN mostra index usage
- **Dipendenze**: Nessuna

### 4.2 Materialized View per Cache Stats

**Task 2.1: Create product_cache_stats View**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Crea materialized view per statistiche cache
- **Attività**:
  - Scrivi query per aggregare usage_count, verified_by_households, avg_price per ogni mapping
  - Crea materialized view product_cache_stats
  - Aggiungi indexes sulla view (raw_name, store_name)
  - Testa query sulla view
  - Verifica dati aggregati corretti
- **Output**: Materialized view funzionante
- **Acceptance Criteria**:
  - View creata con dati corretti
  - Query su view <10ms
  - Indexes su view funzionanti
  - Dati match con query manuale
- **Dipendenze**: Schema esistente con dati di test

**Task 2.2: Setup Refresh Strategy**
- **Owner**: Backend Lead + DevOps
- **Durata**: 2 ore
- **Descrizione**: Configura refresh automatico della materialized view
- **Attività**:
  - Installa pg_cron extension su Supabase (se disponibile)
  - Crea cron job per REFRESH MATERIALIZED VIEW CONCURRENTLY ogni ora
  - Testa manual refresh funziona
  - Se pg_cron non disponibile: crea API endpoint per trigger refresh manualmente
  - Documenta refresh schedule
- **Output**: Auto-refresh configurato
- **Acceptance Criteria**:
  - Refresh automatico ogni ora attivo OPPURE
  - Endpoint manual refresh funzionante
  - Refresh non blocca queries in corso (CONCURRENTLY)
  - Refresh time <5 secondi su dataset test
- **Dipendenze**: Task 2.1 completato
- **Rischio**: pg_cron non disponibile su Supabase tier → Mitigazione: usa endpoint manual refresh chiamato da cron esterno

### 4.3 Helper Functions

**Task 3.1: Create get_cached_product Function**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Crea PostgreSQL function per cache lookup completo
- **Attività**:
  - Scrivi function get_cached_product che accetta raw_name, store_name, current_price
  - Function query product_cache_stats per trovare best match
  - Include logic per price coherence check (±30% tolerance)
  - Include recency check (last_used < 180 giorni)
  - Calcola boosted confidence basato su usage stats
  - Return JSONB con tutti i metadata
  - Aggiungi error handling per edge cases
- **Output**: PostgreSQL function deployata
- **Acceptance Criteria**:
  - Function creata e testabile
  - Return corretto per cache hit scenario
  - Return null per cache miss scenario
  - Price coherence check funzionante
  - Performance <15ms
- **Dipendenze**: Task 2.1 completato (view disponibile)

**Task 3.2: Test get_cached_product**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Test completi della cache function
- **Attività**:
  - Crea test data fixtures (prodotti con vari usage_count, prezzi diversi)
  - Test scenario: cache hit con price match
  - Test scenario: cache hit con price outlier (fallisce coherence check)
  - Test scenario: cache miss (prodotto mai visto)
  - Test scenario: prodotto vecchio (>180 giorni)
  - Test scenario: multiple matches (prende più usato)
  - Documenta tutti i test cases
- **Output**: Test suite per cache function
- **Acceptance Criteria**:
  - Tutti i test cases passano
  - Edge cases coperti
  - Performance sempre <15ms
  - False positives: 0 (no cache hit sbagliati)
- **Dipendenze**: Task 3.1 completato

### 4.4 Data Migration & Backfill

**Task 4.1: Backfill Strategy Planning**
- **Owner**: Backend Lead + DevOps
- **Durata**: 2 ore
- **Descrizione**: Pianifica strategia per generare embeddings per prodotti esistenti
- **Attività**:
  - Stima numero prodotti esistenti in production da backfillare
  - Calcola costi OpenAI per embeddings (n_products * $0.0001)
  - Decidi batch size (raccomandato: 100 prodotti per batch)
  - Pianifica rate limiting per non superare OpenAI quota
  - Prepara rollback plan se backfill fallisce
  - Decide se fare backfill in staging prima di production
- **Output**: Backfill plan documentato
- **Acceptance Criteria**:
  - Costi stimati e approvati
  - Batch size deciso
  - Rate limits configurati
  - Timeline backfill stimata (es: 10k prodotti = ~2 ore)
- **Dipendenze**: Task 1.1, 1.2 completati (embedding column e index ready)

**Task 4.2: Backfill Script Development**
- **Owner**: Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Sviluppa script per generare embeddings batch
- **Attività**:
  - Crea script Node.js o Python per batch processing
  - Script fetches prodotti con embedding = null
  - Genera embedding per canonical_name tramite OpenAI
  - Batch insert embeddings nel database
  - Include progress logging (X/N prodotti completati)
  - Include error handling e retry logic
  - Include resume capability (riprende da dove si è fermato se crash)
  - Aggiungi dry-run mode per testing
- **Output**: Script backfill pronto
- **Acceptance Criteria**:
  - Script funziona in dry-run mode
  - Progress tracking chiaro
  - Error handling robusto
  - Resume capability testata
  - Rate limiting rispettato
- **Dipendenze**: Task 4.1 completato
- **Rischio**: OpenAI rate limits superati → Mitigazione: exponential backoff e retry

**Task 4.3: Staging Backfill Execution**
- **Owner**: Backend Lead
- **Durata**: Variabile (2-4 ore)
- **Descrizione**: Esegui backfill su staging per validazione
- **Attività**:
  - Esegui script backfill su staging database
  - Monitora progress e logs
  - Verifica embeddings generati correttamente (sample validation)
  - Testa vector search con embeddings backfillati
  - Misura query performance su dataset completo
  - Documenta issues trovati e risolti
- **Output**: Staging database con embeddings completi
- **Acceptance Criteria**:
  - 100% prodotti hanno embedding
  - Embeddings dimensionality corretta (1536)
  - Vector search funziona correttamente
  - Performance query <50ms su dataset completo
  - Zero errori in logs
- **Dipendenze**: Task 4.2 completato

### 4.5 Sprint 1 Deliverables

**Checklist Fine Sprint 1**:
- [ ] Colonna embedding aggiunta a normalized_products
- [ ] Vector index HNSW creato e ottimizzato
- [ ] Cache lookup indexes creati (composite + partial)
- [ ] Materialized view product_cache_stats funzionante
- [ ] Refresh strategy configurata
- [ ] PostgreSQL function get_cached_product deployata e testata
- [ ] Backfill script sviluppato e testato
- [ ] Staging database backfill completato con successo
- [ ] Performance targets raggiunti (cache <15ms, vector <50ms)
- [ ] Migration SQL files documentati e versioned
- [ ] Sprint 2 planning meeting completato

**Metriche di Successo Sprint 1**:
- Cache lookup query time: <15ms
- Vector search query time: <50ms
- Backfill success rate: 100%
- Database migrations: zero rollbacks
- Test coverage: >80% per database functions

---

## 5. Sprint 2: PHASE 0 - Smart Cache

**Durata**: 1 settimana
**Obiettivo**: Implementare sistema di cache intelligente completamente funzionante

### 5.1 Cache Service Implementation

**Task 1.1: CacheService Class Structure**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Crea servizio cache con dependency injection
- **Attività**:
  - Crea classe CacheService in services/cache/
  - Inyetta SupabaseClient come dipendenza
  - Definisci metodi public: getCachedProduct(), updateCacheStats(), invalidateCache()
  - Definisci tipi TypeScript per CacheHit, CacheMiss, CacheMetadata
  - Setup error types (CacheError, CacheMissError)
  - Aggiungi logging strutturato per eventi cache
- **Output**: CacheService skeleton
- **Acceptance Criteria**:
  - Classe creata con interface pulita
  - Dependency injection configurata
  - Types TypeScript completi
  - Logging events definiti
- **Dipendenze**: Sprint 0 Task 2.2 (service structure)

**Task 1.2: Tier 1 Cache Implementation (Verified)**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Implementa logica Tier 1 verified cache
- **Attività**:
  - Implementa metodo getCachedProduct che chiama get_cached_product function
  - Parse response JSONB da PostgreSQL function
  - Costruisci CacheHit object con tutti i metadata
  - Aggiungi confidence boost logic (usage_count, verified_by_households, recency)
  - Cap confidence a 0.97
  - Handle cache miss scenario (return null)
  - Aggiungi metrics logging (cache_hit, cache_miss events)
- **Output**: Tier 1 cache funzionante
- **Acceptance Criteria**:
  - Cache hit ritorna prodotto corretto
  - Cache miss ritorna null
  - Confidence boost calcolato correttamente
  - Metrics logged per ogni call
  - Error handling per database errors
- **Dipendenze**: Task 1.1, Sprint 1 Task 3.1 (get_cached_product function)

**Task 1.3: Tier 2 Cache Fallback (Auto-Verified)**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Implementa fallback cache per mappings auto-verified
- **Attività**:
  - Se Tier 1 ritorna null, query product_mappings con verified_by_user = false
  - Filtra per confidence_score >= 0.85
  - Prendi result con confidence più alto
  - Applica penalty: confidence = original_confidence * 0.95
  - Include metadata source = "auto_cache"
  - Aggiungi logging per Tier 2 fallback events
- **Output**: Tier 2 fallback funzionante
- **Acceptance Criteria**:
  - Tier 2 attivato solo se Tier 1 miss
  - Confidence penalty applicato correttamente
  - Source metadata corretto
  - Metrics separati per Tier 1 vs Tier 2 hits
- **Dipendenze**: Task 1.2 completato

**Task 1.4: Price Coherence Validation**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Implementa validazione prezzo per cache hits
- **Attività**:
  - Calcola price deviation: abs(current - avg) / avg
  - Se deviation > 0.30 (30%), downgrade confidence a 0.70
  - Aggiungi flag price_outlier nel result
  - Include suggested_price (avg_price) nel metadata
  - Log price_outlier events per monitoring
  - Gestisci caso avg_price = null (nessun acquisto precedente)
- **Output**: Price validation funzionante
- **Acceptance Criteria**:
  - Deviation calcolato correttamente
  - Confidence downgrade applicato quando necessario
  - Price outliers loggati
  - Nessun crash se avg_price null
- **Dipendenze**: Task 1.2 completato

### 5.2 API Integration

**Task 2.1: Recognition Endpoint Modification**
- **Owner**: Full-Stack Dev
- **Durata**: 3 ore
- **Descrizione**: Integra cache service nell'endpoint riconoscimento prodotti
- **Attività**:
  - Modifica endpoint POST /api/recognition/product per chiamare CacheService prima
  - Se cache hit: skip embedding e vector search, ritorna subito
  - Se cache miss: procedi con riconoscimento completo (implementato in Sprint 3)
  - Aggiungi source field nella response ("verified_cache" | "auto_cache" | "semantic_search")
  - Include metadata cache nel response
  - Setup request/response logging con latency tracking
- **Output**: Endpoint integrato con cache
- **Acceptance Criteria**:
  - Cache hit path funziona correttamente
  - Cache miss fallback preparato (stub per ora)
  - Source corretto nel response
  - Latency <30ms per cache hits
  - API errors handled gracefully
- **Dipendenze**: Task 1.2, 1.3 completati

**Task 2.2: Cache Hit Response Format**
- **Owner**: Full-Stack Dev
- **Durata**: 2 ore
- **Descrizione**: Definisci e implementa format risposta per cache hits
- **Attività**:
  - Crea type ProductRecognitionResponse con tutti i campi necessari
  - Include: product_id, canonical_name, brand, category, confidence, source
  - Include cache_metadata object con usage_count, verified_by_households, avg_price
  - Include validation_result con price_coherent, recently_used flags
  - Documenta schema response in API docs
  - Implementa response builder utility
- **Output**: Response format standardizzato
- **Acceptance Criteria**:
  - Type TypeScript completo
  - Response builder funzionante
  - Schema documentato
  - Frontend può parseare response facilmente
- **Dipendenze**: Task 2.1 in progress

### 5.3 Testing

**Task 3.1: Unit Tests - CacheService**
- **Owner**: Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Test completi del servizio cache
- **Attività**:
  - Setup test fixtures con mock data (verified cache, auto cache, no cache)
  - Test Tier 1 cache hit scenario
  - Test Tier 2 fallback scenario
  - Test cache miss scenario
  - Test price coherence validation (in range, outlier)
  - Test confidence boost logic
  - Test error handling (database down, malformed data)
  - Mock Supabase client per unit testing
- **Output**: Test suite CacheService
- **Acceptance Criteria**:
  - Coverage >85% per CacheService
  - Tutti i test passano
  - Edge cases coperti
  - Mocks configurati correttamente
- **Dipendenze**: Tasks 1.2, 1.3, 1.4 completati

**Task 3.2: Integration Tests - Cache + Database**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Test integrazione con database reale (staging)
- **Attività**:
  - Setup test database con dati fixture realistici
  - Test end-to-end cache lookup con database vero
  - Test get_cached_product function direttamente
  - Test cache stats materialized view refresh
  - Test performance sotto load (100 concurrent queries)
  - Measure cache hit rate su test dataset
- **Output**: Integration test suite
- **Acceptance Criteria**:
  - Tests passano contro staging database
  - Performance <15ms per cache query
  - Nessun data race o deadlock
  - Cache hit rate match aspettative su test data
- **Dipendenze**: Task 3.1 completato, Sprint 1 database setup

**Task 3.3: API Endpoint Tests**
- **Owner**: Full-Stack Dev
- **Durata**: 3 ore
- **Descrizione**: Test endpoint riconoscimento con cache
- **Attività**:
  - Test POST /api/recognition/product con prodotto in cache
  - Test POST con prodotto non in cache (stub response per ora)
  - Test price outlier scenario
  - Test error scenarios (malformed input, database down)
  - Test response format corretto
  - Load test: 100 requests/secondo
- **Output**: API test suite
- **Acceptance Criteria**:
  - Tutti gli endpoint tests passano
  - Response format conforme a schema
  - Performance <50ms P95 per cache hits
  - Error handling robusto
- **Dipendenze**: Task 2.1, 2.2 completati

### 5.4 Monitoring & Metrics

**Task 4.1: Cache Metrics Dashboard**
- **Owner**: DevOps + Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Setup dashboard per monitorare cache performance
- **Attività**:
  - Definisci metrics da tracciare (cache_hit_rate, cache_miss_rate, tier1_vs_tier2, avg_latency)
  - Implementa metrics collection nel CacheService
  - Configura export metrics a monitoring system (Prometheus, Datadog, o Supabase dashboard)
  - Crea dashboard Grafana o equivalente con graphs
  - Setup alerts per cache_hit_rate < 30% (anomalo)
- **Output**: Dashboard operativo
- **Acceptance Criteria**:
  - Metrics visibili in real-time
  - Dashboard comprensibile
  - Alerts funzionanti
  - Historical data salvata (min 7 giorni retention)
- **Dipendenze**: Sprint 0 Task 2.3 (monitoring setup)

**Task 4.2: Logging Enrichment**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Arricchisci logs con context utili per debugging
- **Attività**:
  - Aggiungi request_id a tutti i logs per tracing
  - Includi user_id, household_id quando disponibili
  - Log cache decision path (tier1_attempt, tier2_fallback, miss)
  - Log performance metrics (query_time_ms) in ogni log
  - Struttura logs come JSON per parsing facile
  - Test log aggregation e search in monitoring tool
- **Output**: Logs arricchiti e strutturati
- **Acceptance Criteria**:
  - Logs contengono tutti i context fields
  - Logs searchable per request_id
  - JSON format valido
  - Nessun PII (personal identifiable info) in logs
- **Dipendenze**: Task 1.2, 1.3 completati

### 5.5 Sprint 2 Deliverables

**Checklist Fine Sprint 2**:
- [ ] CacheService implementato e funzionante (Tier 1 + Tier 2)
- [ ] Price coherence validation attiva
- [ ] API endpoint integrato con cache
- [ ] Response format standardizzato
- [ ] Unit tests coverage >85%
- [ ] Integration tests passano
- [ ] API tests passano
- [ ] Performance target raggiunti (cache <30ms)
- [ ] Monitoring dashboard operativo
- [ ] Logging enrichment completato
- [ ] Cache hit rate measurable
- [ ] Sprint 3 planning completato

**Metriche di Successo Sprint 2**:
- Cache lookup latency P50: <20ms, P95: <30ms
- Test coverage: >85%
- Zero critical bugs
- API response time (cache hit): <50ms
- Cache hit rate su test data: >60%

**Rischi Sprint 2**:
- get_cached_product function performance issue → Mitigazione: optimize query con EXPLAIN ANALYZE
- Materialized view refresh troppo lento → Mitigazione: considera partial refresh o indexing migliore
- Cache hit rate bassa su test data → Mitigazione: aumenta test data fixtures con più prodotti comuni

---

## 6. Sprint 3: STEP 1 - Riconoscimento Semantico

**Durata**: 1 settimana
**Obiettivo**: Implementare riconoscimento completo per prodotti non in cache

### 6.1 Embedding Service

**Task 1.1: OpenAI Embeddings Wrapper**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Crea servizio per generare embeddings tramite OpenAI
- **Attività**:
  - Crea EmbeddingService class in services/embeddings/
  - Inyetta OpenAI client configured con API key
  - Implementa metodo generateEmbedding(text: string) → Promise<number[]>
  - Usa model text-embedding-ada-002 (1536 dimensions)
  - Aggiungi retry logic con exponential backoff per rate limits
  - Aggiungi caching locale in-memory per embeddings recenti (LRU cache, max 1000 entries)
  - Log embedding generation events con testo input (truncated)
  - Track costi per embedding generated
- **Output**: EmbeddingService funzionante
- **Acceptance Criteria**:
  - Embeddings generati correttamente (dimensionality 1536)
  - Retry logic funziona per rate limits
  - In-memory cache riduce chiamate duplicate
  - Cost tracking accurato
  - Latency <200ms P95
- **Dipendenze**: Sprint 0 Task 1.3 (OpenAI spike)

**Task 1.2: Batch Embedding Generation**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Ottimizza generazione embeddings per batch
- **Attività**:
  - Implementa metodo generateBatch(texts: string[]) per multiple embeddings in una call
  - OpenAI API supporta fino a 2048 inputs per batch
  - Chunk inputs se superano limite
  - Parallelize batch requests con Promise.all quando possibile
  - Aggiungi error handling per partial failures (alcuni successo, alcuni fail)
  - Return Map<text, embedding> per risultati
- **Output**: Batch generation ottimizzato
- **Acceptance Criteria**:
  - Batch generation funziona per N texts (N <= 2048)
  - Partial failures handled gracefully
  - Performance migliore di N chiamate singole
  - Cost efficiency mantenuta
- **Dipendenze**: Task 1.1 completato

**Task 1.3: Embedding Service Tests**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Test completi embedding service
- **Attività**:
  - Test generazione embedding singolo
  - Test batch generation (5, 50, 500 texts)
  - Test retry logic con mock rate limit error
  - Test in-memory cache hit/miss
  - Test error handling (invalid API key, network error)
  - Test cost tracking accuracy
  - Mock OpenAI API per unit tests
- **Output**: Test suite EmbeddingService
- **Acceptance Criteria**:
  - Coverage >80%
  - Tutti i tests passano
  - Mocks configurati per tests rapidi
  - Edge cases coperti
- **Dipendenze**: Task 1.1, 1.2 completati

### 6.2 Vector Search Service

**Task 2.1: VectorSearchService Implementation**
- **Owner**: Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Implementa semantic search con pgvector
- **Attività**:
  - Crea VectorSearchService class in services/vector-search/
  - Inyetta SupabaseClient
  - Implementa metodo searchSimilar(embedding: number[], limit: number) → Promise<Candidate[]>
  - Query usa operator <=> per cosine distance
  - Calcola similarity score: 1 - distance
  - Filtra prodotti con verification_status = 'rejected'
  - Order by similarity DESC
  - Return array di candidati con tutti i campi prodotto + similarity score
  - Aggiungi optional filters (category, brand) per narrowing search
  - Log query time e number of results
- **Output**: VectorSearchService funzionante
- **Acceptance Criteria**:
  - Search ritorna top K candidati corretti
  - Similarity scores calcolati correttamente (0-1 range)
  - Rejected products esclusi
  - Optional filters funzionano
  - Query time <50ms P95
- **Dipendenze**: Sprint 1 Task 1.2 (vector index creato)

**Task 2.2: Candidate Ranking Enhancement**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Arricchisci candidati con metadata aggiuntivo
- **Attività**:
  - Modifica query vector search per JOIN con purchase_history
  - Aggiungi aggregations: times_purchased, avg_price per candidato
  - Include info se prodotto già comprato dall'household corrente
  - Aggiungi popularity score basato su global purchases
  - Order candidati per weighted score (similarity * 0.7 + popularity * 0.3)
  - Limit join overhead mantenendo performance <50ms
- **Output**: Candidati arricchiti con stats
- **Acceptance Criteria**:
  - Metadata completi per ogni candidato
  - Ranking migliora rilevanza risultati
  - Performance target mantenuto
  - Query optimization verificata con EXPLAIN
- **Dipendenze**: Task 2.1 completato

**Task 2.3: Vector Search Tests**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Test vector search service
- **Attività**:
  - Setup test database con embeddings di prodotti noti
  - Test search con embedding simile a prodotto conosciuto (expected top result)
  - Test search con embedding random (expected low similarity scores)
  - Test filters (category, brand) funzionano
  - Test rejected products esclusi
  - Test performance su dataset di 1000, 10000, 100000 prodotti
  - Test edge case: embedding all zeros
- **Output**: Test suite VectorSearchService
- **Acceptance Criteria**:
  - Tests passano su database staging
  - Performance scalabile con dataset size
  - Accuracy search validata manualmente su sample
  - Edge cases handled
- **Dipendenze**: Task 2.1, 2.2 completati

### 6.3 Context Enrichment

**Task 3.1: Household History Service**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Servizio per fetch storico acquisti household
- **Attività**:
  - Crea ContextService class in services/context/
  - Implementa metodo getHouseholdHistory(householdId, candidateIds[])
  - Query purchase_history per vedere quali candidati household ha già comprato
  - Aggiungi stats: purchase_count, last_purchase_date, avg_price per candidato
  - Include flag: user_bought_before boolean
  - Optimize query con index usage
  - Cache results in-memory per request (stessa household, multiple lookups)
- **Output**: Household history service
- **Acceptance Criteria**:
  - History fetch accurato
  - Query performance <30ms
  - Cache funziona per evitare duplicate queries
  - Dati strutturati per facile consumption
- **Dipendenze**: Sprint 1 Task 1.4 (purchase_history indexes)

**Task 3.2: Store Context Service**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Servizio per fetch statistiche prodotti per store
- **Attività**:
  - Implementa metodo getStoreStats(storeName, candidateIds[])
  - Query purchase_history JOIN receipts per filtrare per store
  - Aggiungi stats: sold_count, avg_price_at_store per candidato
  - Include flag: popular_at_store (sold_count > threshold, es: 10)
  - Optimize con indexes
  - Cache results in-memory
- **Output**: Store context service
- **Acceptance Criteria**:
  - Store stats accurati
  - Query performance <30ms
  - Popular_at_store flag utile per ranking
  - Cache efficiente
- **Dipendenze**: Task 3.1 completato (stessa struttura service)

**Task 3.3: Context Aggregation**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Aggrega tutti i context enrichment per LLM input
- **Attività**:
  - Crea metodo enrichCandidates(candidates, household, store, price)
  - Chiama household history service
  - Chiama store context service
  - Merge dati in ogni candidato
  - Calcola context_match_score per candidato (0-1):
    - +0.5 se user_bought_before
    - +0.3 se popular_at_store
    - +0.2 se price vicino a avg_price
  - Return candidati arricchiti ordinati per combined_score
- **Output**: Context aggregation service
- **Acceptance Criteria**:
  - Tutti i context enrichment applicati
  - Context match score sensato
  - Candidati ranked meglio con context
  - Performance totale <100ms per enrichment
- **Dipendenze**: Task 3.1, 3.2 completati

### 6.4 LLM Reasoning Service

**Task 4.1: LLM Prompt Engineering**
- **Owner**: Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Sviluppa e ottimizza prompt per LLM reasoning
- **Attività**:
  - Scrivi system prompt che spiega ruolo LLM (esperto prodotti retail italiano)
  - Includi istruzioni per considerare tutti i segnali (similarity, context, price)
  - Specifica output format JSON richiesto
  - Scrivi user prompt template che include raw_name, candidati, context
  - Test prompt con GPT-4o-mini su 20 esempi reali
  - Itera prompt basato su risultati (accuracy, consistency)
  - Documenta prompt finali e rationale
- **Output**: Prompt ottimizzati
- **Acceptance Criteria**:
  - Prompt produce JSON parseable 100% delle volte
  - Accuracy su test set >85%
  - Reasoning spiegazioni chiare e sensate
  - Temperature setting ottimizzato (raccomandato: 0.1)
- **Dipendenze**: Sprint 0 Task 1.3 (OpenAI spike)

**Task 4.2: LLMReasoningService Implementation**
- **Owner**: Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Implementa servizio per LLM decision making
- **Attività**:
  - Crea LLMReasoningService class in services/llm/
  - Inyetta OpenAI client
  - Implementa metodo selectProduct(rawName, candidates, context) → Promise<Decision>
  - Costruisci prompt con template da Task 4.1
  - Call OpenAI GPT-4o-mini con response_format: json_object
  - Parse JSON response
  - Validate response structure (tutti i campi required presenti)
  - Handle LLM errors (malformed JSON, timeout, rate limit)
  - Retry logic con exponential backoff
  - Log LLM input/output per debugging (truncated per privacy)
  - Track costi per LLM call
- **Output**: LLMReasoningService funzionante
- **Acceptance Criteria**:
  - Service ritorna Decision object valido
  - JSON parsing robusto
  - Error handling completo
  - Retry logic funziona
  - Cost tracking accurato
  - Latency <400ms P95
- **Dipendenze**: Task 4.1 completato

**Task 4.3: New Product Creation Logic**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Gestisci scenario LLM decide di creare nuovo prodotto
- **Attività**:
  - Se LLM decision = "new_product", valida new_product object completo
  - Check required fields: canonical_name, category (brand, size optional)
  - Validate canonical_name non duplicato (trigram similarity check)
  - Generate embedding per nuovo canonical_name
  - Insert in normalized_products con verification_status = 'auto_verified'
  - Insert in product_mappings per associare raw_name → new product
  - Set confidence basato su LLM confidence score
  - Log new product creation event
- **Output**: New product creation handler
- **Acceptance Criteria**:
  - Nuovo prodotto creato correttamente in database
  - Embedding generato e salvato
  - Mapping creato
  - Duplicate check previene prodotti quasi identici
  - Audit trail completo
- **Dipendenze**: Task 4.2 completato

**Task 4.4: LLM Service Tests**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Test LLM reasoning service
- **Attività**:
  - Test scenario: LLM seleziona prodotto esistente (decision = "existing_product")
  - Test scenario: LLM crea nuovo prodotto (decision = "new_product")
  - Test edge case: LLM ritorna JSON malformed (retry)
  - Test edge case: Tutti candidati scartati (forced new product)
  - Test confidence calculation corretto
  - Test reasoning quality su sample manuale
  - Mock OpenAI per unit tests, use real API per integration tests
- **Output**: Test suite LLMReasoningService
- **Acceptance Criteria**:
  - Unit tests coverage >80%
  - Integration tests passano con real API
  - Edge cases handled gracefully
  - Nessun crash per LLM errors
- **Dipendenze**: Task 4.2, 4.3 completati

### 6.5 Orchestration - Recognition Pipeline

**Task 5.1: ProductRecognitionService Orchestrator**
- **Owner**: Backend Lead + Full-Stack Dev
- **Durata**: 4 ore
- **Descrizione**: Orchestra tutti i servizi in pipeline completo
- **Attività**:
  - Crea ProductRecognitionService class che orchestra tutto il flusso
  - Implementa metodo recognizeProduct(rawName, context) → Promise<RecognitionResult>
  - Pipeline:
    1. Check cache (CacheService)
    2. Se miss: generate embedding (EmbeddingService)
    3. Vector search (VectorSearchService)
    4. Context enrichment (ContextService)
    5. LLM reasoning (LLMReasoningService)
    6. Return RecognitionResult
  - Aggiungi timing tracking per ogni fase
  - Log pipeline execution con performance metrics
  - Handle errors gracefully (fallback strategies)
- **Output**: Orchestrator completo
- **Acceptance Criteria**:
  - Pipeline esegue tutti gli step correttamente
  - Cache hit path bypassa steps 2-5
  - Timing metrics accurate
  - Error handling robusto (non crash mai)
  - Fallback logic sensata
- **Dipendenze**: Tutti i task precedenti Sprint 2 e 3

**Task 5.2: API Endpoint Integration**
- **Owner**: Full-Stack Dev
- **Durata**: 3 ore
- **Descrizione**: Integra orchestrator nell'endpoint API
- **Attività**:
  - Modifica POST /api/recognition/product per chiamare ProductRecognitionService
  - Parse request body (raw_name, store, price, household_id)
  - Validate input (required fields, format)
  - Call recognizeProduct con context appropriato
  - Map RecognitionResult a API response format
  - Include source field ("verified_cache" | "auto_cache" | "semantic_search")
  - Include metadata (confidence, reasoning, timing)
  - Handle errors e ritorna HTTP status codes appropriati
  - Log full request/response per audit
- **Output**: Endpoint completo e funzionante
- **Acceptance Criteria**:
  - Endpoint ritorna response corretta per cache hit
  - Endpoint ritorna response corretta per semantic search
  - Input validation robusta
  - Error responses chiare e actionable
  - Logging completo
- **Dipendenze**: Task 5.1 completato

**Task 5.3: End-to-End Integration Tests**
- **Owner**: Backend Lead + Full-Stack Dev
- **Durata**: 4 ore
- **Descrizione**: Test completi flusso end-to-end
- **Attività**:
  - Test API call con prodotto in cache (fast path)
  - Test API call con prodotto nuovo (full pipeline)
  - Test API call con prodotto ambiguo (multiple candidati simili)
  - Test API call con prodotto completamente sconosciuto (new product creation)
  - Test performance sotto load (50 concurrent requests)
  - Test error scenarios (database down, OpenAI down, invalid input)
  - Measure accuracy su test set di 100 prodotti reali
- **Output**: E2E test suite
- **Acceptance Criteria**:
  - Tutti i test scenarios passano
  - Accuracy >85% su test set
  - Performance <500ms P95 per semantic search
  - Error recovery funziona
  - No memory leaks
- **Dipendenze**: Task 5.2 completato

### 6.6 Sprint 3 Deliverables

**Checklist Fine Sprint 3**:
- [ ] EmbeddingService implementato e testato
- [ ] VectorSearchService funzionante con enrichment
- [ ] ContextService (household + store) operativo
- [ ] LLMReasoningService con prompt ottimizzati
- [ ] New product creation logic funzionante
- [ ] ProductRecognitionService orchestrator completo
- [ ] API endpoint integrato
- [ ] E2E tests passano
- [ ] Performance targets raggiunti
- [ ] Accuracy >85% su test set
- [ ] Cost tracking accurato
- [ ] Sprint 4 planning completato

**Metriche di Successo Sprint 3**:
- Full pipeline latency P95: <600ms
- Embedding generation: <200ms
- Vector search: <50ms
- LLM reasoning: <400ms
- Accuracy overall: >85%
- New product creation success rate: 100%
- Test coverage: >80%

---

## 7. Sprint 4: STEP 2 - Validazione

**Durata**: 4 giorni
**Obiettivo**: Implementare validazione intelligente e feedback loop

### 7.1 Validation Service

**Task 1.1: ValidationService Implementation**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Crea servizio centralizzato per validazione risultati
- **Attività**:
  - Crea ValidationService class in services/validation/
  - Implementa metodo validate(result, context) → Promise<ValidationResult>
  - Source-based validation (cache vs semantic search hanno logic diverse)
  - Aggregate validation status (AUTO_VERIFIED, PENDING_REVIEW, FAILED)
  - Include validation_checks array con dettagli ogni check
  - Include suggested_actions per user quando PENDING_REVIEW
  - Log validation decisions
- **Output**: ValidationService skeleton
- **Acceptance Criteria**:
  - Service structure chiara
  - Source-based logic implemented
  - Validation statuses ben definiti
  - Logging configurato
- **Dipendenze**: Sprint 3 completato

**Task 1.2: Cache Hit Validation**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Validazione leggera per cache hits
- **Attività**:
  - Implementa validateCacheHit(result, context)
  - Check 1: Price coherence (già fatto in cache service, qui solo verify)
  - Check 2: Recency check (last_used < 180 giorni)
  - Se entrambi pass → AUTO_VERIFIED con confidence 0.90
  - Se price outlier → PENDING_REVIEW con confidence downgrade a 0.70
  - Se troppo vecchio → confidence leggero downgrade a 0.85
  - Return ValidationResult con checks details
- **Output**: Cache validation logic
- **Acceptance Criteria**:
  - Validazione cache hit rapida (<5ms)
  - Logic corretta per ogni scenario
  - Confidence adjustments appropriati
  - Validation details informativi
- **Dipendenze**: Task 1.1 completato

**Task 1.3: Semantic Search Validation**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Validazione completa per semantic search results
- **Attività**:
  - Implementa validateSemanticResult(result, context)
  - Threshold-based validation: confidence >= 0.90 → AUTO_VERIFIED
  - Confidence 0.70-0.89 → PENDING_REVIEW (low priority)
  - Confidence <0.70 → PENDING_REVIEW (high priority)
  - Aggiungi checks extra per confidence borderline (0.85-0.90):
    - Verify semantic_similarity > 0.80
    - Verify context_match_score > 0.60
    - Se fail → downgrade a PENDING_REVIEW
  - Return ValidationResult con all checks
- **Output**: Semantic validation logic
- **Acceptance Criteria**:
  - Threshold validation corretta
  - Extra checks per borderline cases sensati
  - Priority setting appropriato
  - Fast execution (<10ms)
- **Dipendenze**: Task 1.1 completato

**Task 1.4: Anomaly Detection Rules**
- **Owner**: Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Implementa rule-based anomaly detection
- **Attività**:
  - Crea AnomalyDetector class in services/validation/
  - Implementa detectAnomalies(product, context) → Anomaly[]
  - Rule 1: Price outlier (prezzo >5x categoria media) → HIGH severity
  - Rule 2: Category-Store mismatch (es: farmaco in supermercato) → MEDIUM
  - Rule 3: Size/Unit sanity (es: 1000kg per biscotti) → MEDIUM
  - Rule 4: Brand-Product inconsistency (Barilla per Nutella) → LOW
  - Rule 5: Duplicate canonical_name detection (trigram >0.90) → HIGH
  - Per ogni anomalia: include message, severity, suggested_fix
  - Se HIGH severity → force PENDING_REVIEW anche se confidence alta
- **Output**: Anomaly detector funzionante
- **Acceptance Criteria**:
  - Tutte le 5 rules implementate
  - Anomalies categorizzate correttamente
  - Severity levels appropriati
  - Force review logic funziona
  - Performance <20ms
- **Dipendenze**: Task 1.1 completato

**Task 1.5: Validation Tests**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Test completi validazione
- **Attività**:
  - Test cache hit validation (pass, price outlier, vecchio)
  - Test semantic validation (high confidence, medium, low)
  - Test anomaly detection per ogni rule
  - Test combined validation (semantic + anomalies)
  - Test edge cases (missing data, null values)
  - Mock dependencies per unit tests
- **Output**: Test suite ValidationService
- **Acceptance Criteria**:
  - Coverage >85%
  - Tutti i test passano
  - Edge cases coperti
  - No false positives
- **Dipendenze**: Tasks 1.2, 1.3, 1.4 completati

### 7.2 Cache Update Logic

**Task 2.1: CacheUpdateService**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Servizio per aggiornare cache dopo riconoscimenti
- **Attività**:
  - Crea CacheUpdateService in services/cache/
  - Implementa metodo updateCache(result, validation)
  - Logic:
    - Se source = "semantic_search" E validation = "AUTO_VERIFIED" → INSERT mapping
    - Se source = "verified_cache" → UPDATE usage stats (incrementato via purchase_history)
    - Se nuovo prodotto creato → INSERT mapping con verified_by_user = false
  - Use INSERT ON CONFLICT DO UPDATE per handle duplicates
  - Update confidence_score se nuovo score più alto
  - Log cache update events
- **Output**: Cache update service
- **Acceptance Criteria**:
  - Mappings creati correttamente
  - ON CONFLICT logic funziona
  - Usage stats aggiornati
  - No duplicate mappings
  - Performance <30ms
- **Dipendenze**: Sprint 2 CacheService

**Task 2.2: Materialized View Refresh Trigger**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Trigger refresh view dopo cache updates
- **Attività**:
  - Valuta se refresh view ad ogni update o batch
  - Se batch: accumula updates e refresh ogni N updates (es: 100)
  - Se real-time: trigger REFRESH MATERIALIZED VIEW CONCURRENTLY
  - Implement throttling per evitare refresh troppo frequenti
  - Monitor refresh time per evitare overhead
  - Consider alternative: aggiorna view incrementalmente se possibile
- **Output**: Refresh strategy implementata
- **Acceptance Criteria**:
  - View aggiornata senza bloccare queries
  - Refresh overhead accettabile (<500ms)
  - Cache stats accurati
  - Throttling funziona
- **Dipendenze**: Task 2.1 completato

### 7.3 User Feedback Loop

**Task 3.1: Feedback API Endpoints**
- **Owner**: Full-Stack Dev
- **Durata**: 4 ore
- **Descrizione**: Crea endpoints per user feedback
- **Attività**:
  - POST /api/feedback/approve-mapping: user approva riconoscimento
  - POST /api/feedback/reject-mapping: user rigetta riconoscimento
  - POST /api/feedback/correct-mapping: user corregge dati prodotto
  - Validate input (mapping_id, user_id required)
  - Authorize: user può revieware solo prodotti dei suoi household (RLS check)
  - Call rispettive handler functions (implementate in Task 3.2, 3.3, 3.4)
  - Return feedback_result con updated product info
  - Log feedback events per analytics
- **Output**: Feedback API endpoints
- **Acceptance Criteria**:
  - Endpoints funzionanti
  - Input validation robusta
  - Authorization verificata
  - Response format chiaro
  - Logging completo
- **Dipendenze**: Nessuna (API structure)

**Task 3.2: Approve Mapping Handler**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Gestisci approvazione user di mapping
- **Attività**:
  - Implementa approveMappingHandler(mappingId, userId)
  - UPDATE product_mappings: verified_by_user = true, confidence = 1.0
  - UPDATE normalized_products: verification_status = 'user_verified' (se non già)
  - Set reviewed_at = NOW(), reviewed_by = userId
  - Increment "verified_by_households" counter (via purchase_history join)
  - Se >= 3 households verificano → boost cache priority
  - Log approval event
  - Return updated mapping
- **Output**: Approve handler
- **Acceptance Criteria**:
  - Mapping updated correttamente
  - Verification status propagato
  - Counter incrementato
  - Audit trail completo
  - Performance <50ms
- **Dipendenze**: Task 3.1 in progress

**Task 3.3: Reject Mapping Handler**
- **Owner**: Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Gestisci rigetto user di mapping
- **Attività**:
  - Implementa rejectMappingHandler(mappingId, userId, reason, correctedProductId)
  - Scenario critico: cache/recognition era sbagliato
  - UPDATE product_mappings: requires_manual_review = true
  - Aggiungi rejection info a interpretation_details JSONB
  - Se correctedProductId fornito: crea nuovo mapping corretto con verified_by_user = true
  - Temporary disable cache per questo raw_name (verified_by_user = false)
  - UPDATE normalized_products original: verification_status = 'rejected' (se appropriato)
  - Alert sistema per possibile errore sistematico
  - Log critical event
- **Output**: Reject handler
- **Acceptance Criteria**:
  - Rejection handled correttamente
  - Nuovo mapping creato se fornito
  - Cache disabled temporaneamente
  - Alert inviato
  - Audit trail dettagliato
- **Dipendenze**: Task 3.1 in progress

**Task 3.4: Correct Product Handler**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Gestisci correzione dati prodotto da user
- **Attività**:
  - Implementa correctProductHandler(productId, userId, corrections)
  - Corrections può includere: canonical_name, brand, category, subcategory
  - Validate corrections (canonical_name required, no duplicates)
  - UPDATE normalized_products con nuovi valori
  - Set verification_status = 'user_verified'
  - UPDATE all product_mappings per questo prodotto: verified_by_user = true
  - Re-generate embedding se canonical_name cambiato
  - Log correction event con before/after values
  - Return updated product
- **Output**: Correct handler
- **Acceptance Criteria**:
  - Correzioni applicate correttamente
  - Validation previene errori
  - Embedding re-generato se necessario
  - Audit trail con before/after
  - Performance <100ms
- **Dipendenze**: Task 3.1 in progress

**Task 3.5: Feedback Loop Tests**
- **Owner**: Backend Lead + Full-Stack Dev
- **Durata**: 3 ore
- **Descrizione**: Test feedback loop completo
- **Attività**:
  - Test approve mapping flow end-to-end
  - Test reject mapping flow con corrected product
  - Test correct product flow con field changes
  - Test authorization (user non può modificare prodotti altri household)
  - Test edge case: multiple users approvano stesso mapping
  - Test cache update dopo feedback
  - Verify materialized view aggiornata
- **Output**: Feedback test suite
- **Acceptance Criteria**:
  - Tutti i flows testati
  - Authorization verificata
  - Edge cases handled
  - Cache consistency verificata
  - No data races
- **Dipendenze**: Tasks 3.2, 3.3, 3.4 completati

### 7.4 Integration with Recognition Pipeline

**Task 4.1: Integrate Validation in Pipeline**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Integra validation service nel recognition pipeline
- **Attività**:
  - Modifica ProductRecognitionService per chiamare ValidationService dopo recognition
  - Pass result e context a validate()
  - Include ValidationResult nel RecognitionResult finale
  - Se PENDING_REVIEW: set flag requires_manual_review nel response
  - Se FAILED: return error o retry logic
  - Update API response format per includere validation_result
- **Output**: Pipeline con validation integrata
- **Acceptance Criteria**:
  - Validation sempre eseguita
  - ValidationResult incluso in response
  - Requires_manual_review flag corretto
  - Error handling appropriato
- **Dipendenze**: Sprint 3 Task 5.1, Sprint 4 Tasks 1.2, 1.3

**Task 4.2: Integrate Cache Update in Pipeline**
- **Owner**: Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Integra cache update dopo validation
- **Attività**:
  - Modifica pipeline per chiamare CacheUpdateService dopo validation
  - Update cache solo se validation pass (AUTO_VERIFIED)
  - Skip update se PENDING_REVIEW (aspetta user feedback)
  - Log cache update success/failure
  - Handle cache update errors gracefully (non bloccare main flow)
- **Output**: Pipeline con cache update
- **Acceptance Criteria**:
  - Cache aggiornata per successi
  - Cache non aggiornata per pending review
  - Errors handled senza crash
  - Async update possibile (non blocca response)
- **Dipendenze**: Task 2.1 completato, Task 4.1 completato

### 7.5 Sprint 4 Deliverables

**Checklist Fine Sprint 4**:
- [ ] ValidationService implementato con source-based logic
- [ ] Anomaly detection rules funzionanti
- [ ] CacheUpdateService operativo
- [ ] Materialized view refresh strategy implementata
- [ ] Feedback API endpoints creati
- [ ] Approve/Reject/Correct handlers funzionanti
- [ ] Feedback loop testato end-to-end
- [ ] Validation integrata in pipeline
- [ ] Cache update integrato
- [ ] Test coverage >80%
- [ ] Sprint 5 planning completato

**Metriche di Successo Sprint 4**:
- Validation latency: <20ms
- Cache update success rate: >99%
- Feedback handler latency: <100ms
- Authorization errors: 0
- Test coverage: >80%

---

## 8. Sprint 5: Testing & Launch

**Durata**: 1 settimana
**Obiettivo**: Testing completo, migration production, launch

### 8.1 Comprehensive Testing

**Task 1.1: Load Testing**
- **Owner**: Backend Lead + DevOps
- **Durata**: 4 ore
- **Descrizione**: Test sistema sotto carico realistico
- **Attività**:
  - Setup tool load testing (Artillery, k6, o JMeter)
  - Definisci scenarios realistici (70% cache hits, 30% semantic search)
  - Simula 100 concurrent users
  - Ramp-up gradually: 10, 50, 100, 200 users
  - Measure latency P50, P95, P99 per scenario
  - Measure throughput (requests/second)
  - Monitor database connections, CPU, memory durante test
  - Identify bottlenecks
- **Output**: Load test report
- **Acceptance Criteria**:
  - Sistema gestisce 100 concurrent users senza crash
  - P95 latency <500ms per semantic search
  - P95 latency <50ms per cache hits
  - No memory leaks
  - Database connection pool sufficient
- **Dipendenze**: Sprint 3, 4 completati

**Task 1.2: Stress Testing**
- **Owner**: Backend Lead + DevOps
- **Durata**: 3 ore
- **Descrizione**: Test limiti sistema oltre carico normale
- **Attività**:
  - Push sistema a 500, 1000 concurrent requests
  - Identify breaking point
  - Verify graceful degradation (sistema rallenta ma non crasha)
  - Test error handling sotto stress (OpenAI rate limits, DB connection exhaustion)
  - Test recovery dopo stress (sistema torna normale)
  - Documenta max capacity
- **Output**: Stress test report
- **Acceptance Criteria**:
  - Breaking point identificato
  - Graceful degradation verificata
  - Recovery post-stress completo
  - Nessun data corruption
- **Dipendenze**: Task 1.1 completato

**Task 1.3: Accuracy Testing on Real Data**
- **Owner**: Backend Lead + QA
- **Durata**: 1 giorno
- **Descrizione**: Test accuracy su dataset reale di scontrini
- **Attività**:
  - Raccogli 200 prodotti reali da scontrini diversi
  - Manually label ground truth (prodotto corretto per ogni raw_name)
  - Run recognition pipeline su tutti i 200 prodotti
  - Compare results con ground truth
  - Calcola accuracy, precision, recall
  - Analizza false positives e false negatives
  - Identify pattern failures (categorie, negozi, brand specifici)
  - Document findings
- **Output**: Accuracy report
- **Acceptance Criteria**:
  - Accuracy overall >88%
  - Cache hit accuracy >95%
  - Semantic search accuracy >85%
  - False positive rate <5%
  - Failure patterns documentati
- **Dipendenze**: Sprint 3, 4 completati

**Task 1.4: Edge Cases & Error Scenarios**
- **Owner**: QA + Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Test edge cases e scenari errore
- **Attività**:
  - Test raw_name vuoto, null, troppo lungo (>500 chars)
  - Test raw_name con caratteri speciali, emoji, encoding strani
  - Test OCR errors simulati (typos, caratteri sostituiti)
  - Test prodotti completamente sconosciuti (brand nuovi, categorie rare)
  - Test database unavailable (mock DB down)
  - Test OpenAI unavailable (mock API down)
  - Test rate limits OpenAI (exhaust quota)
  - Test concurrent updates stesso prodotto (race conditions)
  - Verify error messages informativi per user
- **Output**: Edge case test suite
- **Acceptance Criteria**:
  - Tutti gli edge cases handled gracefully
  - Nessun crash
  - Error messages chiare
  - Fallback strategies funzionano
  - Race conditions prevented
- **Dipendenze**: Tutti i components implementati

**Task 1.5: Security Testing**
- **Owner**: DevOps + Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Test sicurezza sistema
- **Attività**:
  - Test SQL injection su API endpoints (parametrized queries check)
  - Test authentication bypass (verify RLS policies)
  - Test authorization (user non può accedere dati altri household)
  - Test API rate limiting (prevent abuse)
  - Test sensitive data in logs (no passwords, API keys in logs)
  - Test CORS configuration (only allowed origins)
  - Verify environment variables secure (no hardcoded secrets)
- **Output**: Security audit report
- **Acceptance Criteria**:
  - Zero vulnerabilità critiche
  - RLS policies verified
  - No sensitive data leaks
  - Rate limiting funzionante
  - CORS configurato correttamente
- **Dipendenze**: Tutti i components implementati

### 8.2 Production Migration Planning

**Task 2.1: Migration Checklist Creation**
- **Owner**: DevOps + Backend Lead
- **Durata**: 2 ore
- **Descrizione**: Crea checklist dettagliata per migration production
- **Attività**:
  - List pre-migration tasks (backup DB, verify staging, notify users)
  - List migration steps (schema changes, backfill, deployment)
  - List post-migration tasks (verify, monitor, rollback plan)
  - Define rollback triggers (error rate >10%, latency >2s, accuracy <70%)
  - Assign owners per task
  - Estimate downtime (target: <5 minuti)
  - Schedule migration window (low traffic period)
- **Output**: Migration plan documentato
- **Acceptance Criteria**:
  - Checklist completa
  - Rollback plan chiaro
  - Owners assigned
  - Downtime minimizzato
  - Communication plan per users
- **Dipendenze**: Testing completato

**Task 2.2: Production Database Preparation**
- **Owner**: Backend Lead + DevOps
- **Durata**: 3 ore
- **Descrizione**: Prepara production database per migration
- **Attività**:
  - Backup completo production database
  - Verify backup restoration (dry-run)
  - Run migration SQL scripts su staging per final validation
  - Estimate migration time per production data volume
  - Schedule database maintenance window
  - Notify users di scheduled maintenance (se necessario)
  - Prepare rollback SQL scripts
- **Output**: Production DB pronto per migration
- **Acceptance Criteria**:
  - Backup verificato
  - Migration scripts validati su staging
  - Rollback scripts pronti
  - Maintenance window schedulato
  - Users notificati
- **Dipendenze**: Task 2.1 completato

**Task 2.3: Production Backfill Execution**
- **Owner**: Backend Lead + DevOps
- **Durata**: Variabile (2-8 ore a seconda volume)
- **Descrizione**: Esegui backfill embeddings su production
- **Attività**:
  - Deploy backfill script su production environment
  - Esegui backfill in batches durante maintenance window
  - Monitor progress in real-time
  - Verify embeddings quality su sample
  - Handle errors e retry failed batches
  - Verify 100% completion
  - Test vector search funziona su production data
  - Document total time e costi
- **Output**: Production embeddings completi
- **Acceptance Criteria**:
  - 100% prodotti hanno embedding
  - Vector search performante
  - Zero data corruption
  - Backfill time within estimate
  - Costi within budget
- **Dipendenze**: Task 2.2 completato, Sprint 1 Task 4.2 (backfill script)

### 8.3 Deployment

**Task 3.1: Staging Deployment**
- **Owner**: DevOps
- **Durata**: 2 ore
- **Descrizione**: Deploy sistema completo su staging per final check
- **Attività**:
  - Deploy backend services su staging environment
  - Deploy frontend changes su staging
  - Verify environment variables configurate
  - Verify service connections (database, OpenAI)
  - Run smoke tests su staging (basic functionality)
  - Verify monitoring e logging funzionano
  - Load test finale su staging
- **Output**: Staging deployment completo
- **Acceptance Criteria**:
  - Tutti i services running
  - Smoke tests passano
  - Monitoring attivo
  - Performance verificata
  - No errors in logs
- **Dipendenze**: All development completato

**Task 3.2: Production Deployment**
- **Owner**: DevOps + Backend Lead
- **Durata**: 3 ore
- **Descrizione**: Deploy su production
- **Attività**:
  - Execute migration checklist step-by-step
  - Apply database migrations (schema changes, indexes, functions)
  - Deploy backend services (zero-downtime deployment se possibile)
  - Deploy frontend changes
  - Verify services health checks pass
  - Run smoke tests su production
  - Monitor metrics dashboard for anomalies
  - Verify first few real recognition requests succeed
  - Announce deployment completion
- **Output**: Production deployment live
- **Acceptance Criteria**:
  - Deployment senza errori
  - Downtime <5 minuti
  - Health checks pass
  - Smoke tests su production pass
  - No critical errors in logs
  - Metrics nominal
- **Dipendenze**: Task 3.1, Task 2.3 completati

**Task 3.3: Post-Deployment Verification**
- **Owner**: Backend Lead + QA
- **Durata**: 2 ore
- **Descrizione**: Verifica sistema funziona correttamente post-deployment
- **Attività**:
  - Execute UAT test scenarios su production
  - Verify cache hit rate inizia a crescere
  - Verify semantic search funziona per prodotti nuovi
  - Verify feedback loop funziona (approve/reject test)
  - Monitor error rate (<1% target)
  - Monitor latency (P95 <500ms)
  - Check database performance (query times)
  - Verify costs tracking (OpenAI usage)
  - Collect first user feedback
- **Output**: Post-deployment report
- **Acceptance Criteria**:
  - UAT tests passano
  - Error rate <1%
  - Latency targets met
  - Cache warming iniziato
  - No user complaints
  - Costs within budget
- **Dipendenze**: Task 3.2 completato

### 8.4 Monitoring Setup

**Task 4.1: Production Dashboards**
- **Owner**: DevOps + Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Setup dashboards per monitoring production
- **Attività**:
  - Create dashboard "Recognition Performance" (latency, throughput, error rate)
  - Create dashboard "Cache Metrics" (hit rate, tier 1 vs tier 2, miss rate)
  - Create dashboard "Accuracy Tracking" (confidence distribution, review rate)
  - Create dashboard "Cost Monitoring" (OpenAI usage, costs per day/week)
  - Create dashboard "Database Health" (connection pool, query times, index usage)
  - Setup auto-refresh (every 1 minute)
  - Configure visualization (graphs, gauges, tables)
  - Grant team access
- **Output**: Production dashboards
- **Acceptance Criteria**:
  - Dashboards live e aggiornati
  - Metrics accurate
  - Visualizations chiare
  - Team ha accesso
  - Mobile-friendly (bonus)
- **Dipendenze**: Sprint 0 Task 2.3 (monitoring setup)

**Task 4.2: Alerting Configuration**
- **Owner**: DevOps
- **Durata**: 2 ore
- **Descrizione**: Configura alerting per production
- **Attività**:
  - Alert: Error rate >5% per 5 minuti → Slack/Email (CRITICAL)
  - Alert: P95 latency >1000ms per 10 minuti → Slack (WARNING)
  - Alert: Cache hit rate <30% per 1 ora → Slack (INFO)
  - Alert: OpenAI daily cost >$50 → Email (WARNING)
  - Alert: Database connection pool >90% → Slack (CRITICAL)
  - Alert: Accuracy <80% per 24h → Email (WARNING)
  - Test alerts funzionano (trigger manualmente)
  - Document alert response procedures
- **Output**: Alerting configurato
- **Acceptance Criteria**:
  - Alerts funzionanti
  - Notifications arrivano
  - Alert thresholds appropriati
  - Response procedures documentate
  - No alert fatigue (thresholds non troppo sensibili)
- **Dipendenze**: Task 4.1 in progress

**Task 4.3: On-Call Runbook**
- **Owner**: Backend Lead + DevOps
- **Durata**: 3 ore
- **Descrizione**: Crea runbook per on-call engineers
- **Attività**:
  - Document common issues e troubleshooting steps
  - Issue: High error rate → Check logs, verify database/OpenAI status, rollback se necessario
  - Issue: High latency → Check database slow queries, verify cache hit rate, scale resources
  - Issue: Low cache hit rate → Verify materialized view refresh, check cache logic
  - Issue: OpenAI rate limits → Verify request throttling, consider upgrade tier
  - Include rollback procedures (database, code deployment)
  - Include escalation contacts (who to call)
  - Include useful commands e queries per debugging
  - Test runbook con team walkthrough
- **Output**: On-call runbook
- **Acceptance Criteria**:
  - Runbook completo e chiaro
  - Common issues coperti
  - Rollback procedures testate
  - Team trained su runbook
  - Accessible 24/7 (wiki, docs)
- **Dipendenze**: Production deployment completato

### 8.5 Documentation

**Task 5.1: API Documentation**
- **Owner**: Full-Stack Dev
- **Durata**: 3 ore
- **Descrizione**: Documenta API endpoints per team
- **Attività**:
  - Document POST /api/recognition/product (request, response, errors)
  - Document POST /api/feedback/approve-mapping
  - Document POST /api/feedback/reject-mapping
  - Document POST /api/feedback/correct-mapping
  - Include example requests/responses
  - Document authentication (JWT token)
  - Document rate limits (se applicabili)
  - Document error codes e meanings
  - Use OpenAPI/Swagger format (bonus)
- **Output**: API docs
- **Acceptance Criteria**:
  - Tutti gli endpoints documentati
  - Examples chiare
  - Error handling descritto
  - Format standard (OpenAPI)
  - Published e accessibile al team
- **Dipendenze**: Tutti gli endpoints implementati

**Task 5.2: System Architecture Documentation**
- **Owner**: Backend Lead
- **Durata**: 4 ore
- **Descrizione**: Documenta architettura sistema per future reference
- **Attività**:
  - Update product-recognition-architecture.md con implementation details
  - Document deviazioni dal design originale (se presenti)
  - Document decisions tecniche prese durante implementation
  - Document known limitations e future improvements
  - Create architecture diagrams (flow charts, component diagrams)
  - Document database schema completo (se cambiato)
  - Document configuration (environment variables, feature flags)
- **Output**: Architecture docs aggiornati
- **Acceptance Criteria**:
  - Documentation accurate
  - Diagrams chiari
  - Future improvements identificati
  - Easy per nuovi team members capire sistema
- **Dipendenze**: Sistema completo

**Task 5.3: User Guide per Review Interface**
- **Owner**: Product + Full-Stack Dev
- **Durata**: 2 ore
- **Descrizione**: Crea guida user per funzionalità review
- **Attività**:
  - Document come accedere review queue
  - Document come approvare prodotto
  - Document come rigettare e correggere
  - Include screenshots (se UI presente)
  - Include best practices (quando approvare vs rigettare)
  - Include FAQ (domande comuni)
  - Test guida con utenti reali
- **Output**: User guide
- **Acceptance Criteria**:
  - Guida chiara e concisa
  - Screenshots utili
  - FAQ comprensivo
  - Testata con utenti
  - Published su wiki/docs
- **Dipendenze**: Review interface implementato

### 8.6 Sprint 5 Deliverables

**Checklist Fine Sprint 5**:
- [ ] Load testing completato, performance verificata
- [ ] Stress testing completato, limiti identificati
- [ ] Accuracy testing >88% su real data
- [ ] Edge cases e security testing passati
- [ ] Migration checklist creata
- [ ] Production database migrated e backfilled
- [ ] Production deployment completato con successo
- [ ] Post-deployment verification passed
- [ ] Monitoring dashboards live
- [ ] Alerting configurato e testato
- [ ] On-call runbook creato
- [ ] API documentation completa
- [ ] Architecture docs aggiornati
- [ ] User guide disponibile
- [ ] **Sistema LIVE in production** 🎉

**Metriche di Successo Launch**:
- Deployment downtime: <5 minuti
- Post-deployment error rate: <1%
- Cache hit rate Day 1: >10% (warming iniziato)
- Accuracy real users: >88%
- User feedback: positive (no major complaints)
- Team confidence: high (on-call runbook useful)

---

## 9. Post-Launch: Monitoring & Optimization

**Periodo**: Settimane 6-8
**Obiettivo**: Stabilizzare sistema, ottimizzare, preparare future enhancements

### 9.1 Week 1 Post-Launch

**Task 1.1: Daily Monitoring**
- **Owner**: Backend Lead (rotating on-call)
- **Durata**: 30 min/giorno
- **Descrizione**: Monitor sistema giornalmente
- **Attività**:
  - Check dashboards ogni mattina
  - Review error logs per nuovi pattern
  - Monitor cache hit rate trend (should increase)
  - Monitor accuracy metrics
  - Monitor costs (OpenAI usage)
  - Document any issues found
  - Triage e prioritize fixes
- **Output**: Daily monitoring reports
- **Success**: Sistema stabile, no critical issues

**Task 1.2: User Feedback Collection**
- **Owner**: Product + Backend Lead
- **Durata**: Ongoing
- **Descrizione**: Raccogli feedback utenti
- **Attività**:
  - Survey users su accuracy riconoscimenti
  - Collect complaints e feature requests
  - Analyze review queue patterns (quali prodotti reviewati di più)
  - Identify pain points (categorie con bassa accuracy)
  - Document feedback strutturalmente
  - Prioritize improvements basati su feedback
- **Output**: User feedback report
- **Success**: >80% user satisfaction

**Task 1.3: Bug Fixes & Hot Patches**
- **Owner**: Backend Lead + Full-Stack Dev
- **Durata**: Variabile
- **Descrizione**: Fixa bugs critici trovati post-launch
- **Attività**:
  - Triage bugs per severity (critical, high, medium, low)
  - Fix critical bugs immediatamente (hot patch)
  - Fix high priority bugs entro 48h
  - Deploy fixes con testing rapido
  - Verify fixes in production
  - Communicate fixes al team
- **Output**: Bug fixes deployati
- **Success**: Zero critical bugs after week 1

### 9.2 Week 2-4 Post-Launch: Optimization

**Task 2.1: Performance Optimization**
- **Owner**: Backend Lead + DevOps
- **Descrizione**: Ottimizza performance basato su dati reali
- **Attività**:
  - Analyze slow query logs, optimize top 5 slowest queries
  - Optimize database indexes basato su query patterns reali
  - Tune pgvector index parameters (m, ef_construction) se necessario
  - Optimize cache hit rate (tune thresholds, expand cache coverage)
  - Consider caching layer (Redis) se database bottleneck
  - Profile backend code, optimize hot paths
- **Output**: Performance improvements deployati
- **Success**: P95 latency ridotto 20%

**Task 2.2: Accuracy Improvement**
- **Owner**: Backend Lead
- **Descrizione**: Migliora accuracy basato su failure patterns
- **Attività**:
  - Analyze rejected mappings (top failure patterns)
  - Improve LLM prompts basato su real examples
  - Add few-shot examples per categorie problematiche
  - Tune confidence thresholds basato su precision/recall trade-off
  - Consider fine-tuning embeddings (advanced)
  - Test improvements su staging prima di deploy
- **Output**: Accuracy improvements
- **Success**: Accuracy increases to >90%

**Task 2.3: Cost Optimization**
- **Owner**: Backend Lead + DevOps
- **Descrizione**: Ottimizza costi OpenAI
- **Attività**:
  - Analyze OpenAI usage patterns (embeddings vs LLM calls)
  - Optimize embedding caching (increase cache size se ROI positivo)
  - Consider batch embedding generation per ridurre API calls
  - Evaluate alternative embedding models (più economici)
  - Tune LLM temperature e max_tokens per ridurre costi senza perdere quality
  - Monitor cache hit rate increase = costi decrease
- **Output**: Cost reductions
- **Success**: Costs ridotti 30% mantenendo accuracy

### 9.3 Future Enhancements Planning

**Task 3.1: Proposta 2 Evaluation**
- **Owner**: Backend Lead + Product
- **Descrizione**: Valuta se migrare a Proposta 2 (Hybrid Multi-Stage)
- **Attività**:
  - Review accuracy data: se <85% in categorie chiave → consider Proposta 2
  - Analyze failure modes: fuzzy matching risolverebbe X% errori?
  - Estimate ROI di Proposta 2 features (LLM extraction, multi-signal)
  - Estimate effort per implementare Proposta 2 enhancements
  - Decision: stick con Proposta 1 ottimizzata OR plan migration
  - Se migration: create roadmap Sprint 6-8
- **Output**: Proposta 2 decision document
- **Success**: Clear decision con rationale

**Task 3.2: Feature Roadmap**
- **Owner**: Product + Backend Lead
- **Descrizione**: Pianifica future features
- **Attività**:
  - Prioritize user feature requests
  - Features potenziali:
    - Barcode scanning integration
    - Multi-language support (scontrini inglesi, etc.)
    - Product images recognition
    - Auto-categorization suggestions
    - Bulk import scontrini
  - Estimate effort per feature
  - Create roadmap Q1, Q2
  - Allocate resources
- **Output**: Feature roadmap
- **Success**: Roadmap approved by stakeholders

**Task 3.3: Continuous Learning Pipeline**
- **Owner**: Backend Lead
- **Descrizione**: Setup pipeline per continuous improvement
- **Attività**:
  - Collect user corrections as training data
  - Setup periodic embedding re-training (monthly)
  - Setup LLM prompt optimization cycles (quarterly)
  - Automate accuracy testing su growing dataset
  - Setup A/B testing framework per nuove features
  - Document continuous improvement process
- **Output**: Continuous learning pipeline
- **Success**: Sistema migliora automaticamente nel tempo

---

## 10. Rischi & Mitigazioni

### 10.1 Rischi Tecnici

**Rischio 1: pgvector Performance Insufficiente**
- **Probabilità**: Bassa
- **Impatto**: Alto
- **Mitigazione**:
  - Spike in Sprint 0 valida performance early
  - Use HNSW index (più performante di IVFFlat)
  - Monitor query times continuamente
  - Fallback: consider external vector DB (Pinecone, Weaviate) se necessario

**Rischio 2: OpenAI API Rate Limits**
- **Probabilità**: Media
- **Impatto**: Alto
- **Mitigazione**:
  - Implement exponential backoff e retry logic
  - Request OpenAI rate limit increase pre-launch
  - Monitor usage vs limits
  - Fallback: queue requests se rate limited (async processing)

**Rischio 3: Cache Hit Rate Troppo Bassa**
- **Probabilità**: Media
- **Impatto**: Medio (costi alti, latency alta)
- **Mitigazione**:
  - Seed cache con prodotti comuni pre-launch
  - Monitor cache warming trend
  - Optimize Tier 2 fallback logic
  - Educate users su review importance (più review = migliore cache)

**Rischio 4: Accuracy Insufficiente (<85%)**
- **Probabilità**: Media
- **Impatto**: Alto
- **Mitigazione**:
  - Extensive testing in Sprint 5 identifica issues early
  - Iterate su LLM prompts fino accuracy accettabile
  - Plan Proposta 2 features come backup (fuzzy matching, extraction)
  - Collect user feedback per target improvements

**Rischio 5: Database Performance Degradation**
- **Probabilità**: Bassa
- **Impatto**: Critico
- **Mitigazione**:
  - Load testing in Sprint 5 identifica bottlenecks
  - Optimize indexes based on query patterns
  - Monitor slow queries continuamente
  - Scale database resources se necessario (Supabase plan upgrade)

### 10.2 Rischi di Progetto

**Rischio 6: Team Availability**
- **Probabilità**: Media
- **Impatto**: Medio (delays)
- **Mitigazione**:
  - Buffer time in timeline (6 settimane, not 4)
  - Identify critical path tasks early
  - Cross-train team members (knowledge sharing)
  - Have backup resources identified

**Rischio 7: Scope Creep**
- **Probabilità**: Alta
- **Impatto**: Medio
- **Mitigazione**:
  - Strict scope per Proposta 1 (no extra features)
  - Product Owner approva changes
  - Park future features in backlog
  - Focus su MVP first, iterate later

**Rischio 8: Integration Issues**
- **Probabilità**: Media
- **Impatto**: Medio
- **Mitigazione**:
  - Early integration testing (non aspettare Sprint 5)
  - Incremental integration (dopo ogni sprint)
  - Dedicated integration sprint (Sprint 5)
  - Staging environment identical a production

### 10.3 Rischi Business

**Rischio 9: Budget Overrun (OpenAI Costs)**
- **Probabilità**: Media
- **Impatto**: Alto
- **Mitigazione**:
  - Track costs daily
  - Alert quando costs superano budget
  - Optimize caching aggressively
  - Consider cheaper models se quality sufficiente
  - Have cost ceiling agreement con stakeholders

**Rischio 10: User Adoption Bassa**
- **Probabilità**: Bassa
- **Impatto**: Medio
- **Mitigazione**:
  - User education (guide, tutorials)
  - Onboarding smooth
  - Collect feedback early e iterate
  - Incentivize review participation (gamification?)

---

## 11. Definition of Done

### 11.1 Per Task

Un task è **Done** quando:
- [ ] Code implementato e funzionante
- [ ] Unit tests scritti e passano (coverage >80%)
- [ ] Integration tests passano (se applicabile)
- [ ] Code review completato e approvato
- [ ] Documentation aggiornata (code comments, API docs)
- [ ] Deployed su staging e verificato
- [ ] Acceptance criteria tutti soddisfatti
- [ ] No critical bugs
- [ ] Performance requirements met

### 11.2 Per Sprint

Uno sprint è **Done** quando:
- [ ] Tutti i task dello sprint sono Done
- [ ] Sprint demo completata con stakeholders
- [ ] Retrospective completata e action items identified
- [ ] Sprint metrics documentate (velocity, bugs found, etc.)
- [ ] Staging deployment stabile
- [ ] Next sprint planning completato
- [ ] Team confident di procedere

### 11.3 Per Progetto (Launch)

Il progetto è **Done** quando:
- [ ] Tutti gli sprint completati
- [ ] Production deployment successful
- [ ] Post-deployment verification passed
- [ ] Monitoring e alerting operativi
- [ ] Documentation completa (API, architecture, runbook)
- [ ] Team trained su on-call procedures
- [ ] User guide pubblicata
- [ ] Performance targets raggiunti (latency, accuracy, costs)
- [ ] Stakeholder approval ottenuta
- [ ] Handoff a operations team completato

---

## 12. Appendici

### 12.1 Glossary

**Terms chiave**:
- **Cache Hit**: Prodotto trovato in cache, no need for full recognition
- **Cache Miss**: Prodotto non in cache, requires semantic search
- **Embedding**: Vector representation di testo (1536 dimensioni per Ada)
- **Semantic Search**: Ricerca basata su similarità vettoriale
- **LLM**: Large Language Model (GPT-4o-mini)
- **RLS**: Row Level Security (Supabase database security)
- **Confidence**: Score 0-1 di quanto sistema è sicuro del riconoscimento
- **Verification Status**: Stato prodotto (auto_verified, pending_review, user_verified, rejected)

### 12.2 Key Metrics Reference

**Performance Metrics**:
- **Cache Latency**: <30ms P95
- **Semantic Search Latency**: <500ms P95
- **Full Pipeline Latency**: <600ms P95

**Accuracy Metrics**:
- **Overall Accuracy**: >88%
- **Cache Hit Accuracy**: >95%
- **Semantic Search Accuracy**: >85%
- **Review Rate**: <18%

**Cost Metrics**:
- **Cost per Product (full)**: ~$0.0002
- **Cost per Product (avg with cache)**: ~$0.00006
- **Daily Budget** (1000 products/day): <$0.10

**Business Metrics**:
- **Cache Hit Rate** (after 3 months): 65-75%
- **User Satisfaction**: >80%
- **Review Completion Rate**: >70%

### 12.3 Tech Stack Summary

**Backend**:
- Language: TypeScript/Node.js
- Framework: Next.js API routes (o FastAPI se Python)
- Database: PostgreSQL (Supabase)
- Vector DB: pgvector extension
- LLM: OpenAI GPT-4o-mini
- Embeddings: OpenAI text-embedding-ada-002

**Testing**:
- Unit/Integration: Jest o Vitest
- E2E: Playwright o Cypress
- Load Testing: Artillery o k6

**Monitoring**:
- Dashboards: Grafana Cloud o Supabase Dashboard
- Logging: Winston o Pino (structured JSON)
- Alerting: Slack, Email

**DevOps**:
- Deployment: Vercel (frontend) + Supabase (backend/DB)
- CI/CD: GitHub Actions
- Version Control: Git (GitHub)

### 12.4 Useful Links

**Documentation**:
- Supabase pgvector: https://supabase.com/docs/guides/ai/vector-columns
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
- OpenAI GPT-4o-mini: https://platform.openai.com/docs/models/gpt-4o-mini
- product-recognition-architecture.md: docs/product-recognition-architecture.md

**Internal**:
- Project Board: [link to Jira/Linear/GitHub Projects]
- Team Wiki: [link to wiki]
- On-Call Schedule: [link to PagerDuty/OpsGenie]

---

## 🎯 Next Steps

**Immediate Actions**:
1. Review roadmap con team (1 ora meeting)
2. Setup project board e import tasks (Task 3.1 Sprint 0)
3. Schedule Sprint 0 kickoff (1 settimana da oggi)
4. Assign Sprint 0 tasks a team members
5. Book calendar for daily standups (15 min/giorno)

**Success Criteria**:
- Team aligned e motivated
- Timeline agreed
- Resources allocated
- Sprint 0 starts on schedule

---

**Fine Roadmap** - Ready for Execution! 🚀
