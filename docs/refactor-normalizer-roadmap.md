# Roadmap: Refactoring ProductNormalizerV2

## Obiettivo
Ristrutturare il processo di normalizzazione prodotti secondo il flusso corretto: Cache Lookup → LLM Interpret → Vector Search → LLM Select → LLM Validate → Cache Update, con parallelizzazione configurabile.

---

## SETUP

**Prerequisiti:**
- Database con 18k prodotti normalizzati e embeddings (già presente)
- Indici HNSW e cache (già presenti)
- OpenAI API key per chiamate LLM

**Modifiche configurazione:**
- Aggiungere parametro `PARALLEL_NORMALIZATION_BATCH_SIZE = 10` (configurabile)
- Aggiungere parametri per 3 prompt LLM separati (interpret, select, validate)
- Rimuovere configurazioni function calling non più utilizzate

---

## FASE 1: PULIZIA CODICE ESISTENTE (Durata: 1 ora)

**TASK 1.1: Rimuovere function tools obsoleti**
Eliminare da ProductNormalizerV2 tutti i function tools (search_product_online, find_existing_product, create_normalized_product) e relativa logica function calling che causa loop infiniti.

**TASK 1.2: Semplificare struttura agente**
Rimuovere metodo `_run_identification_loop()` e tutta la logica iterativa. L'agente non deve più fare loop autonomi.

**TASK 1.3: Mantenere servizi core**
- CacheService (product_mappings lookup)
- VectorSearchService (semantic search)
- ValidationService (da modificare in FASE 3)
- CacheUpdateService (salvataggio mappings)
- ContextService (arricchimento contesto, opzionale per ora)

---

## FASE 2: LLM INTERPRET - ESPANSIONE E MATCHING (Durata: 2 ore)

**TASK 2.1: Creare servizio LLMInterpretService**
Nuovo servizio dedicato per interpretazione raw_name. Responsabilità:
- Espandere abbreviazioni (es. "AC.MINGAS" → "Acqua Minerale Frizzante")
- Riconoscere brand (es. "S.ANNA" → "Sant'Anna")
- Interpretare formati (es. "1.5X6" → "confezione 6 bottiglie da 1.5L")
- Ipotizzare prodotto completo

**TASK 2.2: Scrivere prompt LLM Interpret**
Prompt deve istruire LLM a:
- Analizzare nome grezzo scontrino
- Espandere abbreviazioni comuni italiane
- Riconoscere brand noti
- Formulare ipotesi prodotto completo e descrittivo
- Ritornare JSON: `{hypothesis: "...", brand: "...", product_type: "...", size: "..."}`

**TASK 2.3: Implementare chiamata LLM**
Chiamata singola senza function tools. Input: raw_name, store_name (opzionale per contesto). Output: ipotesi strutturata.

---

## FASE 3: VECTOR SEARCH SU IPOTESI LLM (Durata: 1 ora)

**TASK 3.1: Modificare VectorSearchService**
Aggiungere metodo `search_from_hypothesis(hypothesis_text, top_k=5)` che:
- Genera embedding dall'ipotesi LLM
- Cerca top 5 prodotti simili nel database (18k embeddings)
- Ritorna lista candidati ordinati per similarity score

**TASK 3.2: Configurare threshold similarity**
Abbassare threshold minimo per vector search (es. 0.6 invece di 0.8) perché ora cerca ipotesi LLM espansa, non raw_name grezzo. Se nessun candidato sopra threshold, ritorna lista vuota.

---

## FASE 4: LLM SELECT - SCELTA BEST MATCH (Durata: 2 ore)

**TASK 4.1: Creare servizio LLMSelectService**
Nuovo servizio per selezione best match tra candidati vector search. Responsabilità:
- Ricevere lista candidati (top 5)
- Confrontare con raw_name originale e ipotesi LLM
- Scegliere prodotto più verosimile

**TASK 4.2: Scrivere prompt LLM Select**
Prompt deve istruire LLM a:
- Analizzare raw_name originale e ipotesi interpretata
- Valutare ogni candidato considerando: brand match, product type match, size match, similarity score
- Scegliere il candidato più probabile
- Ritornare JSON: `{selected_product_id: "...", reasoning: "..."}`

**TASK 4.3: Gestire edge case "nessun candidato"**
Se vector search ritorna lista vuota, LLMSelectService viene saltato. Il flusso passa direttamente a LLM Validate con l'ipotesi LLM come "prodotto selezionato". Questo caso richiederà successivamente creazione manuale prodotto o review utente.

---

## FASE 5: LLM VALIDATE - CONFIDENCE SCORING (Durata: 2 ore)

**TASK 5.1: Sostituire ValidationService con LLMValidateService**
Eliminare ValidationService esistente (logica euristica). Nuovo servizio usa LLM per validazione semantica. Responsabilità:
- Valutare corrispondenza raw_name → prodotto selezionato
- Assegnare confidence score (0-1)
- Identificare flag per manual review

**TASK 5.2: Scrivere prompt LLM Validate**
Prompt deve istruire LLM a rispondere: "Quanto è probabile che questa riga RAW corrisponda a questo prodotto normalizzato?"
Considerare:
- Corrispondenza brand
- Corrispondenza product type
- Corrispondenza size/quantity
- Ambiguità o incertezze
Ritornare JSON: `{confidence_score: 0.85, needs_review: false, reasoning: "..."}`

**TASK 5.3: Configurare soglie confidence**
- confidence >= 0.8: auto-verified, non richiede review
- confidence 0.5-0.8: richiede review manuale
- confidence < 0.5: mapping incerto, marcato per review obbligatoria

---

## FASE 6: INTEGRAZIONE PIPELINE E PARALLELIZZAZIONE (Durata: 3 ore)

**TASK 6.1: Rifattorizzare normalize_product()**
Riscrivere metodo principale con nuovo flusso sequenziale:
1. Cache Lookup (product_mappings)
2. LLM Interpret (se cache miss)
3. Vector Search (su ipotesi)
4. LLM Select (se candidati trovati) o skip (se nessun candidato)
5. LLM Validate
6. Cache Update

**TASK 6.2: Implementare batch processing**
Creare metodo `normalize_batch(items, batch_size=10)` che:
- Raggruppa items in batch di N prodotti (configurabile, default 10)
- Parallelizza chiamate per ogni fase del batch
- Usa asyncio.gather() per esecuzione concorrente
- Gestisce errori per singolo item senza bloccare batch

**TASK 6.3: Ottimizzare chiamate LLM**
Per parallelizzazione efficiente:
- LLM Interpret: batch di max 10 chiamate simultanee
- Vector Search: già parallelo (solo embedding generation)
- LLM Select: batch di max 10 chiamate simultanee
- LLM Validate: batch di max 10 chiamate simultanee

**TASK 6.4: Aggiungere logging dettagliato**
Log per ogni fase con emoji distinti:
- 🔎 Cache lookup
- 💭 LLM Interpret
- 🔍 Vector Search
- ✅ LLM Select
- 📊 LLM Validate
- 💾 Cache Update

---

## FASE 7: INTEGRAZIONE API E TESTING (Durata: 2 ore)

**TASK 7.1: Aggiornare endpoint receipts.py**
Modificare `/receipts/process` per usare `normalize_batch()` invece di loop sequenziale. Passare tutti items dello scontrino in un'unica chiamata batch.

**TASK 7.2: Test con scontrino reale**
Testare con scontrino Bennet di 20 items. Verificare:
- Performance: target <30 secondi totali (parallelizzazione efficace)
- Accuracy: almeno 80% prodotti matchati correttamente
- Nessun loop infinito o timeout

**TASK 7.3: Gestione errori robusti**
Ogni fase deve gestire errori senza bloccare pipeline:
- LLM Interpret fallisce → ritorna raw_name come ipotesi
- Vector Search fallisce → passa lista vuota a Select
- LLM Select fallisce → usa primo candidato vector search
- LLM Validate fallisce → assegna confidence 0.5 (review obbligatoria)

---

## FASE 8: PULIZIA FINALE (Durata: 1 ora)

**TASK 8.1: Rimuovere codice obsoleto**
Eliminare file e metodi non più utilizzati:
- product_normalizer_agent.py (vecchio agente)
- Function tools definitions
- Logica function calling

**TASK 8.2: Aggiornare documentazione**
Modificare docs/product-recognition-architecture.md per riflettere nuovo flusso. Rimuovere riferimenti a function calling e approccio multi-stage precedente.

**TASK 8.3: Aggiornare test**
Modificare test integration per nuovo flusso. Verificare ogni servizio separatamente (LLMInterpret, LLMSelect, LLMValidate).

---

## DURATA TOTALE STIMATA: 14 ore

- FASE 1: 1h (Pulizia)
- FASE 2: 2h (LLM Interpret)
- FASE 3: 1h (Vector Search)
- FASE 4: 2h (LLM Select)
- FASE 5: 2h (LLM Validate)
- FASE 6: 3h (Pipeline + Parallelizzazione)
- FASE 7: 2h (API + Testing)
- FASE 8: 1h (Pulizia finale)

---

## NOTE TECNICHE

**Performance attesa:**
- Con parallelizzazione N=10: ~3-5 secondi per batch di 10 prodotti
- Scontrino 20 items: 2 batch = ~6-10 secondi totali
- Drastico miglioramento rispetto ai 5 minuti attuali

**Costi OpenAI stimati:**
- 3 chiamate LLM per prodotto (interpret, select, validate)
- ~60 chiamate per scontrino da 20 items
- Con GPT-4o-mini: ~$0.002-0.005 per scontrino

**Cache efficienza:**
- Dopo primo scontrino: molti prodotti in cache
- Scontrini successivi: 70-80% cache hit (0 chiamate LLM)
- Sistema diventa sempre più veloce con l'uso
