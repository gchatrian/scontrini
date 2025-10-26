Cache Intelligente - Spiegazione Semplice
Cos'è la Cache?
La cache è una "memoria veloce" che ricorda i prodotti già visti in passato. Senza cache: Ogni volta devi chiedere all'AI "Cos'è questo prodotto?" → lento (2 secondi) e costoso Con cache: "L'ho già visto! È questo" → velocissimo (0.03 secondi) e gratis
Come Funziona?
1. Prima Volta - Nessuna Cache
Tu: Scannerizzi "COCA COLA 1.5L" al Conad
Sistema: "Non l'ho mai visto prima"
→ Chiede all'AI (embedding + vector search + LLM)
→ Propone: "Coca Cola Bottiglia 1.5L" (confidence 0.92)
Tu: Confermi ✓
Sistema: Salva nel database:
  - raw_name: "COCA COLA 1.5L"
  - store_name: "Conad"
  - normalized_product_id: 12345
  - verified_by_user: TRUE
2. Seconda Volta - Cache Hit!
Tu: Scannerizzi di nuovo "COCA COLA 1.5L" al Conad
Sistema: "L'ho già visto! È il prodotto 12345"
→ NON chiede all'AI
→ Propone direttamente: "Coca Cola Bottiglia 1.5L" (confidence 0.90)
→ Velocissimo (30ms) e gratis!
Cache "Intelligente" - 2 Tier
Tier 1: Cache Verificata (Priorità Alta)
Prodotti che tu hai confermato:
verified_by_user = TRUE
Confidence base: 0.90 (90% sicuro)
Molto affidabile perché sei stato tu a dire "è giusto"
Tier 2: Cache Auto-Verificata (Fallback)
Prodotti che altri utenti hanno confermato o che il sistema ha auto-approvato con alta confidence:
verified_by_user = FALSE ma confidence_score >= 0.85
Usata se Tier 1 non trova nulla
Penalty: -5% confidence (0.85 → 0.80)
Confidence Boost (Come Cresce la Fiducia)
Quando trova un prodotto in cache, il sistema aumenta la confidence: Base: 0.90 (90%) Boost 1: +3% se 3+ famiglie hanno confermato lo stesso prodotto
"Se 5 famiglie dicono che è giusto, probabilmente lo è!"
Boost 2: +2% se il prodotto è stato usato 10+ volte
"Se l'abbiamo visto tante volte, siamo più sicuri"
Boost 3: +2% se usato negli ultimi 90 giorni
"Se è recente, è più affidabile (i prodotti cambiano nel tempo)"
Massimo: 0.97 (97% - non arriva mai a 100% perché nulla è certo al 100%)
Esempio Pratico
Prodotto in cache: "Pasta Barilla 500g"
- Base: 0.90
- Confermato da 5 famiglie → +0.03
- Usato 15 volte → +0.02
- Ultimo uso 20 giorni fa → +0.02
→ Confidence finale: 0.97 ✅
Price Coherence (Controllo Prezzo)
La cache ricorda anche i prezzi storici:
Pasta Barilla 500g
- Prezzo medio storico: €1.20
- Deviazione standard: €0.10
- Oggi paghi: €1.30 → OK (±30% tolleranza)
Prezzo Coerente → Confidence rimane alta (0.90) Prezzo Anomalo:
- Prezzo medio storico: €1.20
- Oggi paghi: €3.50 → STRANO! (+191%)
→ Confidence scende a 0.70
→ Prodotto evidenziato ⚠️
Perché? Potrebbe essere:
Errore OCR
Prodotto diverso (es. formato famiglia)
Prezzo davvero cambiato molto
Materialized View (La "Tabella Veloce")
Il sistema crea una tabella speciale (product_cache_stats) che contiene:
raw_name: "COCA COLA 1.5L"
store_name: "Conad"
normalized_product_id: 12345
usage_count: 15 (quante volte usato)
verified_by_households: 3 (quante famiglie l'hanno confermato)
avg_price: €1.80 (prezzo medio)
price_stddev: €0.15 (quanto varia)
last_used: 2025-10-20 (ultima volta)
first_used: 2025-08-10 (prima volta)
Perché serve?
Invece di calcolare ogni volta "quante famiglie l'hanno confermato?", guarda nella tabella veloce
Query: 15ms invece di 200ms
Flusso Completo Cache Service
1. Ricevi: raw_name="COCA COLA 1.5L", store_name="Conad", price=€1.80

2. Query Tier 1 (prodotti verificati da te):
   SELECT * FROM product_cache_stats
   WHERE raw_name = 'COCA COLA 1.5L'
     AND store_name = 'Conad'
   
3. Trovato? SÌ!
   - usage_count: 15
   - verified_by_households: 3
   - avg_price: €1.75
   - last_used: 20 giorni fa

4. Calcola Confidence Boost:
   - Base: 0.90
   - +0.03 (3 households)
   - +0.02 (15 utilizzi)
   - +0.02 (recente)
   = 0.97

5. Verifica Prezzo:
   - Attuale: €1.80
   - Medio: €1.75
   - Differenza: +2.8% → OK!
   - price_coherent: TRUE

6. Ritorna:
   {
     product_id: 12345,
     confidence: 0.97,
     price_coherent: true,
     source: "cache_tier1"
   }
Quando NON Usa la Cache?
Prima volta che vedi quel prodotto in quel negozio
Nome scritto diversamente: "CC 1.5L" invece di "COCA COLA 1.5L"
(per questo serve semantic search + AI)
Negozio diverso: "COCA COLA 1.5L" visto alla Coop ma non al Conad
In questi casi → Semantic Search (embedding + vector + LLM)
In Pratica
Mese 1: Cache hit rate 10% (pochi prodotti memorizzati) Mese 2: Cache hit rate 40% (inizia ad imparare) Mese 3: Cache hit rate 65%+ (conosce la maggior parte dei tuoi prodotti) Risultato:
70% richieste → Cache (30ms, gratis)
30% richieste → AI (600ms, €0.0002)
Media: ~200ms e ~€0.00006 per prodotto 🚀
Chiaro? La cache è come un cervello che ricorda i prodotti che compri spesso