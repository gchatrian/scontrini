# Soluzione A --- Ricerca "smart" nel Database (SQL + Fuzzy Search)

## 1. Obiettivo

Riconoscere il prodotto corretto all'interno del database (≈20.000 SKU)
a partire da una riga di scontrino, spesso abbreviata o con refusi, e da
un'ipotesi iniziale generata da un modello LLM.

------------------------------------------------------------------------

## 2. Panoramica funzionale

### Step 1 --- Pre-Processing

-   Pulizia e normalizzazione del testo: minuscole, rimozione caratteri
    speciali, espansione abbreviazioni (es. "bav." → "bavaria").\
-   Estrazione di segnali chiave: **marca**, **categoria**, **quantità**
    e **unità di misura**.\
-   Uso dell'ipotesi LLM come guida iniziale (es. brand o categoria
    suggeriti).

### Step 2 --- Filtri "Hard"

Riduzione del perimetro di ricerca:\
- Marca: se riconosciuta, filtro sui prodotti di quella marca.\
- Quantità/unità: tolleranza ±15%.\
- Categoria: se disponibile, restringe ulteriormente il campo.

### Step 3 --- Ricerca e Ranking

Utilizzo di **Full Text Search (FTS)** e **fuzzy matching (trigram)**: -
FTS per trovare prodotti con parole chiave corrispondenti.\
- Fuzzy search per gestire refusi o abbreviazioni.\
- Ranking combinato con pesi su: - coerenza testuale, - brand match, -
categoria match, - compatibilità quantità/unità.

### Step 4 --- Reranking Business

Regole di coerenza applicate ai top 20 candidati: - Scarto automatico se
unità incompatibili.\
- Penalità se il brand o "0.0/analcolica" non coincidono.\
- Ricalcolo punteggio finale (0--1).

### Step 5 --- Selezione Finale (LLM)

-   Passaggio dei top 5--10 candidati all'LLM con i relativi attributi
    strutturati.\
-   L'LLM sceglie il miglior match e assegna un **confidence score**.\
-   Se il punteggio \< soglia, il caso viene inviato in revisione
    manuale.

------------------------------------------------------------------------

## 3. Dati e Arricchimenti

-   **Dizionari abbreviazioni** aggiornabili.\
-   **Sinonimi di marca/categoria** per migliorare il recall.\
-   **Normalizzazione unità/quantità** per confronti coerenti.\
-   **Tag** rilevanti per categorie specifiche.

------------------------------------------------------------------------

## 4. Architettura Logica

  -----------------------------------------------------------------------
  Modulo                        Funzione
  ----------------------------- -----------------------------------------
  **Normalizer**                Pulisce ed espande il testo dello
                                scontrino.

  **Retriever (DB)**            Esegue ricerca con FTS e fuzzy matching.

  **Reranker (App)**            Applica regole di business e calcola
                                punteggio finale.

  **LLM Selector**              Sceglie il prodotto migliore e assegna
                                confidenza.

  **Audit & Metrics**           Monitora KPI e gestisce i casi da
                                revisionare.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 5. KPI Principali

-   **Match rate automatico** (% righe risolte senza revisione).\
-   **Precisione finale** (precision@1).\
-   **Review rate** (% righe in revisione).\
-   **Tempo medio di risoluzione**.

Target iniziale realistico:\
- Auto-match ≥ 85--90%\
- Review rate ≤ 10--15%\
- Latenza \< 600 ms

------------------------------------------------------------------------

## 6. Piano di Implementazione

### Settimana 1 --- Setup e Pilot

-   Import catalogo e creazione indici DB.\
-   Costruzione primo dizionario abbreviazioni (da 200--500 righe
    reali).\
-   Taratura soglie FTS/fuzzy e regole quantità/unità.\
-   Definizione soglie di confidenza per accettazione automatica.

### Settimana 2 --- Validazione e Tuning

-   Esecuzione pilot su 10--20% degli scontrini reali.\
-   Raccolta KPI e analisi errori.\
-   Aggiornamento dizionari, pesi e tolleranze.\
-   Attivazione dashboard monitoraggio.

### Settimana 3 --- Go-live progressivo

-   Estensione graduale al 100% del traffico.\
-   Aggiunta moduli di revisione manuale e logging automatico.\
-   Formazione team per aggiornamenti periodici dei dizionari.

------------------------------------------------------------------------

## 7. Evoluzioni Future (Fase 2)

-   **Vector Search** come fallback per categorie difficili o retailer
    con abbreviazioni complesse.\
-   **Auto-learning**: aggiornamento automatico dizionari da validazioni
    umane.\
-   **Metriche predittive**: previsione dei casi a basso confidence per
    prioritizzare la revisione.

------------------------------------------------------------------------

## 8. Benefici Attesi

-   Soluzione **cost-effective** e **rapida da implementare**.\
-   Nessuna nuova infrastruttura necessaria (solo PostgreSQL).\
-   Alta accuratezza e possibilità di estensione futura verso soluzioni
    più intelligenti (ibrido embeddings).
