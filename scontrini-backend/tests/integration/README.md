# Integration Tests - ProductNormalizerV2

Test integration end-to-end per la pipeline di normalizzazione prodotti.

## Setup

### 1. Installa Dependencies

```bash
cd scontrini-backend
pip install -r requirements-dev.txt
```

### 2. Configura Environment

Verifica che `.env` contenga:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
OPENAI_API_KEY=sk-...
```

### 3. Modifica IDs Test

Apri `tests/test_config.py` e modifica:

```python
TEST_HOUSEHOLD_ID = "il-tuo-household-uuid"  # ← MODIFICA!
TEST_USER_ID = "il-tuo-user-uuid"            # ← MODIFICA!
```

**Come trovare i tuoi IDs:**

1. Vai su Supabase Dashboard → Table Editor
2. Tabella `household_members` → cerca il tuo user_id
3. Copia `household_id` e `user_id`

### 4. (Opzionale) Personalizza Test Fixtures

In `tests/test_config.py` puoi modificare i prodotti test:

```python
TEST_PRODUCTS = {
    "cache_tier1": {
        "raw_name": "COCA COLA 1.5L",  # ← Modifica se vuoi
        "canonical_name": "Coca Cola 1.5L",
        ...
    },
    ...
}
```

## Esecuzione Test

### Run Tutti i Test

```bash
pytest tests/integration/test_product_normalizer_v2.py -v
```

**Output atteso:**
```
tests/integration/test_product_normalizer_v2.py::test_cache_tier1_hit PASSED [16%]
tests/integration/test_product_normalizer_v2.py::test_cache_tier2_hit PASSED [33%]
tests/integration/test_product_normalizer_v2.py::test_vector_search_hit PASSED [50%]
tests/integration/test_product_normalizer_v2.py::test_llm_normalization PASSED [66%]
tests/integration/test_product_normalizer_v2.py::test_price_anomaly_detection PASSED [83%]
tests/integration/test_product_normalizer_v2.py::test_low_context_warning PASSED [100%]

===================== 6 passed in 15.23s =====================
```

### Run Test Singolo

```bash
# Test specifico
pytest tests/integration/test_product_normalizer_v2.py::test_cache_tier1_hit -v

# Con output dettagliato
pytest tests/integration/test_product_normalizer_v2.py::test_cache_tier1_hit -v -s
```

### Run con Coverage

```bash
pytest tests/integration/test_product_normalizer_v2.py --cov=app.agents.product_normalizer_v2 --cov-report=html
```

## Scenari di Test

### 1. Cache Tier 1 Hit
- **Setup**: Prodotto user-verified + mapping + purchase history
- **Test**: Normalizza prodotto già mappato
- **Expected**: source="cache_tier1", confidence ~0.90-0.97

### 2. Cache Tier 2 Hit
- **Setup**: Prodotto auto-verified + mapping NON verified
- **Test**: Normalizza prodotto con mapping tier2
- **Expected**: source="cache_tier2", confidence ~0.85

### 3. Vector Search Hit
- **Setup**: Prodotto esistente con embedding
- **Test**: Normalizza raw_name simile semanticamente
- **Expected**: source="vector_search", similarity ≥0.75

### 4. LLM Normalization
- **Setup**: Nessuno (prodotto nuovo)
- **Test**: Normalizza prodotto mai visto
- **Expected**: source="llm", LLM crea/trova prodotto

### 5. Price Anomaly Detection
- **Setup**: Prodotto con storico prezzi ~1.50€
- **Test**: Normalizza con prezzo 10.00€
- **Expected**: validation.flags.price_anomaly=True, confidence penalizzata

### 6. Low Context Warning
- **Setup**: Prodotto senza purchase_history
- **Test**: Normalizza prodotto mai comprato
- **Expected**: context.context_score <0.3, validation.flags.low_context=True

## Cleanup

**I test fanno cleanup automatico** dopo ogni esecuzione.

Se AUTO_CLEANUP=True in `test_config.py`, tutti i dati test vengono eliminati al termine del test.

Per disabilitare cleanup (debug):
```python
# tests/test_config.py
AUTO_CLEANUP = False  # ← Disabilita cleanup
```

## Troubleshooting

### "Household non trovato"

Verifica che `TEST_HOUSEHOLD_ID` in `test_config.py` sia corretto:

```bash
# Controlla su Supabase
Table Editor → households → cerca il tuo household
```

### Test LLM Timeout

Se il test LLM fallisce per timeout, aumenta il limite in `test_config.py`:

```python
LLM_TEST_TIMEOUT = 60  # Aumenta a 60 secondi
```

### Import Error

Verifica di essere nella directory corretta:

```bash
cd scontrini-backend
pytest tests/integration/...
```

### OpenAI Rate Limit

Se ricevi errore "Rate limit exceeded", attendi qualche secondo e riprova:

```bash
sleep 10 && pytest tests/integration/...
```

## Note

- **Test usano DB reale**: richiedono credentials Supabase + OpenAI valide
- **Costi**: Test LLM costa ~$0.002 per run (embeddings + normalizzazione)
- **Durata**: ~15-20 secondi per suite completa
- **Idempotenza**: Ogni test è indipendente, cleanup automatico
- **Fixture modificabili**: Personalizza `TEST_PRODUCTS` in `test_config.py`

## Prossimi Passi

Dopo i test integration:
1. Run in CI/CD pipeline
2. Load testing (Phase 4)
3. Accuracy validation con dataset reale
4. Edge cases testing
