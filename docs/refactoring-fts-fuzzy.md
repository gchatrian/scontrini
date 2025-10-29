# Refactoring Piano di Normalizzazione Prodotti

## 🎯 Obiettivo

Sostituire l'approccio attuale basato su **semantic search via embeddings** (costoso, lento) con un sistema **SQL-first** basato su Full-Text Search e Fuzzy Matching (veloce, economico, scalabile).

---

## 📊 Situazione AS-IS

### Architettura Attuale

**Pipeline in 6 step:**
1. **Cache Lookup** - Tier 1 (verified) e Tier 2 (auto-verified)
2. **LLM Interpret** - Espande abbreviazioni e identifica componenti prodotto
3. **Vector Search** - Genera embedding e cerca per similarità semantica (~18K vettori)
4. **LLM Select** - Sceglie best match tra top 5 candidati
5. **LLM Validate** - Calcola confidence score e decide se serve review
6. **Cache Update** - Aggiorna mappature (attualmente disabilitato)

### Problemi Identificati

| Problema | Impatto |
|----------|---------|
| **Embedding generation costosa** | +$0.00002 per prodotto + latenza ~200ms |
| **Vector search lenta** | Ricerca su 18K vettori ~300-500ms |
| **Dipendenza OpenAI API** | Rate limits, downtime, costi crescenti |
| **Scarsa scalabilità** | Bottleneck su chiamate API esterne |
| **Dead code** | Colonne/indici/servizi vector non ottimizzati |

### Metriche Attuali

- **Latenza media**: ~1000ms per prodotto
- **Costo**: ~$0.00013 per prodotto
- **Throughput**: ~50 prodotti/sec
- **Accuracy**: ~80% auto-match (stimato)

---

## 🎯 Soluzione TO-BE

### Principi Guida

1. **SQL-First**: Usare PostgreSQL per ricerca primaria (gratis, veloce, scalabile)
2. **LLM per intelligenza**: Mantenere LLM solo per interpretazione e validazione
3. **Zero embeddings**: Eliminare completamente vector search e dipendenze
4. **Regole business**: Aggiungere layer di regole deterministiche per filtering

### Nuova Architettura

**Pipeline in 6 step (refactored):**

1. **Cache Lookup**
   - Mantiene logica attuale (Tier 1 + Tier 2)
   - Nessuna modifica

2. **LLM Interpret**
   - Mantiene servizio attuale
   - Espande abbreviazioni intelligentemente
   - Estrae: brand, category, size, unit_type, tags
   - Output: ipotesi prodotto strutturata

3. **SQL Hybrid Search** ⭐ NUOVO
   - Combina tre tecniche SQL:
     - **Full-Text Search (FTS)**: ricerca semantica su canonical_name + brand
     - **Fuzzy Matching (trigram)**: tolleranza a typo e abbreviazioni
     - **Filtri Hard**: brand, category, size (±15%), unit_type
   - Ranking combinato con pesi configurabili
   - Output: Top 20 candidati con score

4. **Business Reranking** ⭐ NUOVO
   - Applica regole deterministiche:
     - **Scarta** unità incompatibili (es. "1.5L" non può essere "500g")
     - **Penalizza** brand/category mismatch
     - **Boost** per tag overlap e size proximity
   - Ricalcola business_score
   - Output: Top 5-10 candidati filtrati

5. **LLM Select**
   - Mantiene logica attuale
   - Riceve candidati pre-filtrati da business reranker
   - Sceglie best match con reasoning

6. **LLM Validate**
   - Mantiene logica attuale
   - Calcola confidence e decide review
   - Nessuna modifica

### Fallback Strategy

Se SQL search non trova candidati (score troppo basso o zero risultati):
- **Usa ipotesi LLM come prodotto** con confidence=0.60 (low)
- **Flag per review manuale** automatico
- Nessun fallback a vector search (eliminato completamente)

---

## 🗑️ Componenti da Rimuovere

### Backend (Dead Code Cleanup)

**File da eliminare:**
- `embedding_service.py` - Wrapper OpenAI embeddings (obsoleto)
- `vector_search_service.py` - Semantic search via pgvector (obsoleto)
- `cache_update_service.py` - Update mappings (già deprecato)

**File da aggiornare:**
- `product_normalizer_v2.py` - Rimuovere import e logica vector search
- `config.py` - Rimuovere configurazioni embeddings e vector search

### Database

**Colonne da droppare:**
- `normalized_products.embedding` (vector 1536)

**Indici da droppare:**
- `idx_normalized_products_embedding` (HNSW)

**RPC Functions da droppare:**
- `search_similar_products()`

**Migrations obsolete:**
- `mvp_001_upgrade_to_hnsw.sql`
- `mvp_005_vector_search_function.sql`

---

## 🆕 Componenti da Creare

### Backend

1. **SQL Retriever Service**
   - Chiama RPC function per ricerca ibrida
   - Gestisce parametri filtri hard
   - Formatta risultati con score multipli

2. **Business Reranker Service**
   - Implementa regole di compatibilità unità
   - Calcola penalità/boost business
   - Filtra e ordina candidati

3. **Product Normalizer V3**
   - Orchestra nuova pipeline SQL-first
   - Mantiene compatibilità con cache
   - Gestisce fallback su ipotesi LLM

### Database

1. **Extension Setup**
   - Abilita `pg_trgm` per fuzzy matching

2. **Indici per Performance**
   - **GIN Index FTS**: su `to_tsvector(canonical_name || brand)` per full-text search
   - **GIN Index Trigram**: su `canonical_name` per fuzzy matching
   - **Composite Index**: su (brand, category, unit_type, size) per filtri hard

3. **RPC Function Hybrid Search**
   - Combina FTS + Fuzzy + Filtri in query unica
   - Calcola score combinato con pesi
   - Ottimizzata per <100ms su 18K prodotti

---

## 📈 Benefici Attesi

### Performance

| Metrica | AS-IS | TO-BE | Miglioramento |
|---------|-------|-------|---------------|
| Latenza media | ~1000ms | ~500ms | **-50%** |
| Costo/prodotto | $0.00013 | $0.00006 | **-54%** |
| Throughput | ~50/sec | ~200/sec | **+300%** |
| Accuracy | ~80% | 85-90% | **+5-10%** |

### Scalabilità

- **Eliminazione bottleneck API esterne**: no più rate limits OpenAI
- **Caching PostgreSQL**: query plan cache per performance costanti
- **Zero costi variabili**: solo infra DB (già pagata)

### Manutenibilità

- **Codice più semplice**: -23% file backend
- **Meno dipendenze**: -1 servizio esterno (OpenAI embeddings)
- **Debug più facile**: SQL query analizzabili con EXPLAIN

---

## 📅 Piano di Implementazione

### FASE 1: Database Setup (1-2 giorni)

**Obiettivo**: Preparare database per ricerca SQL ibrida

- Backup completo database
- Rimuovere colonna embedding e indice HNSW
- Abilitare extension pg_trgm
- Creare indici GIN per FTS e trigram
- Creare indice composite per filtri hard
- Implementare RPC function per ricerca ibrida
- Test performance: target <100ms per query

### FASE 2: Backend Cleanup (1 giorno)

**Obiettivo**: Rimuovere dead code vector search

- Eliminare 3 file servizi obsoleti
- Aggiornare config (remove vector settings)
- Rimuovere import vector search da normalizer V2
- Test che tutto compila senza errori

### FASE 3: Nuovi Componenti (3-4 giorni)

**Obiettivo**: Implementare pipeline SQL-first

- **SQL Retriever Service**: wrapper RPC con gestione parametri
- **Business Reranker Service**: regole filtering e scoring
- **Product Normalizer V3**: pipeline completa refactored
- Unit test per ogni componente (coverage >80%)

### FASE 4: Integration (1-2 giorni)

**Obiettivo**: Integrare V3 nell'applicazione

- Aggiornare endpoint `/receipts/process` per usare V3
- Mantenere backward compatibility response schema
- Integration tests end-to-end
- Error handling e logging

### FASE 5: Testing & Tuning (2-3 giorni)

**Obiettivo**: Validare accuracy e performance

- Test su 100+ scontrini reali diversificati
- Confronto accuracy AS-IS vs TO-BE
- Tuning pesi ranking (FTS vs Fuzzy)
- Tuning soglie business rules
- Performance benchmarks sotto carico

### FASE 6: Deployment (1 giorno)

**Obiettivo**: Go-live production

- Deploy migrations database (in finestra manutenzione)
- Deploy backend refactored
- Monitoring attivo logs/metriche
- Rollback plan documentato e testato

**Effort Totale: 9-13 giorni** (~2-2.5 settimane)

---

## ✅ Criteri di Successo

### KPI Tecnici

- [ ] Latenza media < 600ms (target: 500ms)
- [ ] Accuracy auto-match ≥ 85%
- [ ] Review rate ≤ 15%
- [ ] Zero errori su 100 test scontrini
- [ ] Performance query SQL < 100ms P95

### KPI Business

- [ ] Riduzione costi operativi: -50%
- [ ] Nessuna regressione UX
- [ ] Zero downtime durante migration
- [ ] Rollback plan testato e funzionante

### Quality Gates

- [ ] Unit test coverage ≥ 80%
- [ ] Integration tests 100% passanti
- [ ] No dead code residuo
- [ ] Documentazione aggiornata

---

## 🚨 Rischi e Mitigazioni

### Rischio 1: Accuracy Inferiore a AS-IS

**Probabilità**: Media | **Impatto**: Alto

**Mitigazione**:
- Fase 5 (Testing) estesa se accuracy <80%
- A/B testing graduale con feature flag
- Possibilità di tuning pesi/soglie post-deploy

### Rischio 2: Query SQL Lente su Production

**Probabilità**: Bassa | **Impatto**: Alto

**Mitigazione**:
- Benchmark su replica database production
- Indici ottimizzati preventivamente
- EXPLAIN ANALYZE su query critiche
- Monitoring query performance attivo

### Rischio 3: Edge Cases Non Gestiti

**Probabilità**: Media | **Impatto**: Medio

**Mitigazione**:
- Fallback su ipotesi LLM sempre disponibile
- Flag review manuale per confidence <0.70
- Logging dettagliato per analisi post-mortem

### Rischio 4: Regressioni Durante Migration

**Probabilità**: Bassa | **Impatto**: Alto

**Mitigazione**:
- Rollback plan testato pre-deploy
- Backup database completo
- Deploy in finestra manutenzione
- Smoke tests post-deploy immediati

---

## 📋 Checklist Pre-Deploy

### Database
- [ ] Backup completato e verificato
- [ ] Migrations testate su staging
- [ ] Indici creati e performance validata
- [ ] RPC function funzionante

### Backend
- [ ] Dead code rimosso
- [ ] Nuovi componenti implementati
- [ ] Unit tests >80% coverage
- [ ] Integration tests passanti
- [ ] Logging strutturato configurato

### Testing
- [ ] Test su 100+ scontrini reali
- [ ] Accuracy ≥ 85%
- [ ] Performance < 600ms
- [ ] Error handling validato

### Operations
- [ ] Rollback plan documentato
- [ ] Monitoring configurato
- [ ] Alerting attivo
- [ ] Runbook operativo aggiornato

---

## 🎯 Conclusioni

Il refactoring proposto elimina la dipendenza da vector search (costosa, lenta) in favore di un approccio SQL-first (veloce, economico, scalabile). La soluzione mantiene l'intelligenza LLM dove serve (interpretazione, selezione, validazione) e aggiunge un layer di regole business deterministiche per migliorare accuracy.

**Benefici principali:**
- Performance: -50% latenza
- Costi: -54% per prodotto
- Scalabilità: +300% throughput
- Manutenibilità: -23% complessità codice

**Effort stimato:** 2-2.5 settimane con team dedicato.
