# Frontend-Backend Integration - ProductNormalizerV2

Modifiche necessarie per integrare ProductNormalizerV2 con il frontend.

## Modifiche Backend

### File: `app/api/routes/receipts.py`

#### TASK 1: Aggiornare Import

```python
# RIMUOVI
from app.agents.product_normalizer import product_normalizer_agent

# AGGIUNGI
from app.agents.product_normalizer_v2 import product_normalizer_v2
```

#### TASK 2: Modificare Funzione `normalize_item`

**Linea ~167-195 - Cambiare chiamata normalizzazione:**

```python
async def normalize_item(item):
    """Normalizza singolo prodotto (include validazione e score)"""

    # CAMBIARE DA:
    # norm_result = product_normalizer_agent.normalize_product(...)

    # A:
    norm_result = await product_normalizer_v2.normalize_product(
        raw_product_name=item["raw_product_name"],
        household_id=request.household_id,  # ← AGGIUNTO
        store_name=parsing_result.get("store_name"),
        price=item["total_price"]
    )

    if not norm_result["success"]:
        print(f"⚠️ Normalization failed for '{item['raw_product_name']}': {norm_result.get('error')}")
        return None

    # CAMBIARE RETURN per includere nuovi campi
    return {
        "raw_product_name": item["raw_product_name"],
        "quantity": item.get("quantity", 1.0),
        "unit_price": item.get("unit_price"),
        "total_price": item["total_price"],

        # Campi normalizzati
        "canonical_name": norm_result.get("canonical_name"),
        "brand": norm_result.get("brand"),
        "category": norm_result.get("category"),
        "subcategory": norm_result.get("subcategory"),
        "size": norm_result.get("size"),
        "unit_type": norm_result.get("unit_type"),

        # MODIFICATI/AGGIUNTI
        "confidence": norm_result.get("confidence", 0.5),
        "confidence_level": norm_result.get("confidence_level"),  # ← NUOVO
        "source": norm_result.get("source"),  # ← NUOVO
        "pending_review": norm_result["validation"]["flags"]["needs_review"],  # ← CAMBIATO path
        "user_verified": False
    }
```

#### TASK 3: Modificare `ProcessReceiptRequest` per essere async

**Linea ~99 - Aggiungere `async`:**

```python
# CAMBIARE DA:
@router.post("/process", response_model=ProcessReceiptResponse)
async def process_receipt(request: ProcessReceiptRequest):

# La funzione è già async, ma normalize_item deve essere chiamata con await

# MODIFICARE linea ~198 (ThreadPoolExecutor):
# RIMUOVERE ThreadPoolExecutor e usare asyncio.gather

import asyncio

# CAMBIARE DA:
with ThreadPoolExecutor(max_workers=5) as executor:
    normalized_items = list(executor.map(normalize_item, aggregated_items))

# A:
normalized_items = await asyncio.gather(
    *[normalize_item(item) for item in aggregated_items]
)
```

#### TASK 4: Aggiornare Schema Response

**Linea ~44 - Aggiungere campi a `ReceiptItemData`:**

```python
class ReceiptItemData(BaseModel):
    receipt_item_id: str
    raw_product_name: str
    quantity: float
    unit_price: Optional[float]
    total_price: float

    # Dati normalizzati
    canonical_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    size: Optional[str] = None
    unit_type: Optional[str] = None
    confidence: Optional[float] = None

    # NUOVI CAMPI
    confidence_level: Optional[str] = None  # ← NUOVO: "high" | "medium" | "low"
    source: Optional[str] = None  # ← NUOVO: "cache_tier1" | "cache_tier2" | "vector_search" | "llm"

    pending_review: Optional[bool] = None
    user_verified: Optional[bool] = None
```

## Modifiche Frontend

### File: `types/receipt.ts`

#### TASK 5: Aggiornare Type Definitions

```typescript
export interface ReceiptItemWithNormalized extends ReceiptItem {
  // ID per tracking
  id?: string
  receipt_item_id?: string

  // Dati normalizzati
  normalized_product_id?: string
  canonical_name?: string
  brand?: string | null
  subcategory?: string | null
  size?: string
  unit_type?: string
  confidence?: number

  // NUOVI CAMPI
  confidence_level?: "high" | "medium" | "low"  // ← NUOVO
  source?: "cache_tier1" | "cache_tier2" | "vector_search" | "llm"  // ← NUOVO

  pending_review?: boolean
  from_cache?: boolean
  user_verified?: boolean
}
```

### File: `components/receipt/ReceiptReview.tsx`

#### TASK 6: Aggiornare UI con Nuovi Indicatori

**Opzione A - Sostituire confidence % con confidence_level:**

```typescript
{/* Linea ~268-276 - SOSTITUIRE badge confidence */}
{item.confidence_level && (
  <Badge
    variant={
      item.confidence_level === "high" ? "default" :
      item.confidence_level === "medium" ? "secondary" : "destructive"
    }
    className="text-xs"
  >
    {item.confidence_level.toUpperCase()}
  </Badge>
)}
```

**Opzione B - Aggiungere source badge (opzionale):**

```typescript
{/* Nuovo badge per indicare sorgente normalizzazione */}
{item.source && (
  <Badge variant="outline" className="text-xs">
    {item.source === "cache_tier1" && "✓ Cache Verificata"}
    {item.source === "cache_tier2" && "~ Cache Auto"}
    {item.source === "vector_search" && "🔍 Ricerca Semantica"}
    {item.source === "llm" && "🤖 Nuova Normalizzazione"}
  </Badge>
)}
```

**Posizione suggerita (dopo linea ~266):**

```typescript
{/* Confidence Tags sopra il box */}
{item.confidence_level && (
  <div className="flex justify-end items-center gap-2">
    {item.user_verified && (
      <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-300">
        Verificato dall'utente
      </Badge>
    )}

    {/* Nuovo: Source Badge */}
    {item.source && (
      <Badge variant="outline" className="text-xs">
        {item.source === "cache_tier1" && "✓ Cache"}
        {item.source === "cache_tier2" && "~ Auto"}
        {item.source === "vector_search" && "🔍 Search"}
        {item.source === "llm" && "🤖 AI"}
      </Badge>
    )}

    {/* Confidence Level Badge */}
    <span className="text-xs text-muted-foreground">Confidence:</span>
    <Badge
      variant={
        item.confidence_level === "high" ? "default" :
        item.confidence_level === "medium" ? "secondary" : "destructive"
      }
      className="text-xs"
    >
      {item.confidence_level?.toUpperCase()}
    </Badge>
  </div>
)}
```

## Testing

### Test Manuale

1. **Setup**:
   - Applica modifiche backend
   - Applica modifiche frontend
   - Restart backend server: `uvicorn app.main:app --reload`
   - Restart frontend: `npm run dev`

2. **Test Upload Scontrino**:
   - Carica scontrino test
   - Verifica console log per nuovi campi:
     ```javascript
     console.log('Item:', item)
     // Dovrebbe mostrare: confidence_level, source, validation
     ```

3. **Verifica UI**:
   - Badge confidence_level visualizzato correttamente
   - Source badge (se implementato) mostra sorgente
   - Pending review funziona con nuovo path `validation.flags.needs_review`

### Test Scenari

#### Scenario 1: Cache Hit Tier 1
- **Input**: Prodotto già normalizzato e verificato
- **Expected Output**:
  - `source: "cache_tier1"`
  - `confidence_level: "high"`
  - `confidence: 0.90-0.97`
  - `pending_review: false`

#### Scenario 2: Vector Search Hit
- **Input**: Prodotto simile ma raw_name diverso
- **Expected Output**:
  - `source: "vector_search"`
  - `confidence_level: "medium" o "high"`
  - `confidence: ≥0.75`
  - `pending_review: false o true` (dipende da validation)

#### Scenario 3: LLM Normalization
- **Input**: Prodotto completamente nuovo
- **Expected Output**:
  - `source: "llm"`
  - `confidence_level: "medium" o "low"`
  - `confidence: 0.50-0.80`
  - `pending_review: true` (se low confidence)

#### Scenario 4: Price Anomaly
- **Input**: Prodotto con prezzo anomalo
- **Expected Output**:
  - `source: qualsiasi`
  - `confidence_level: "low"` (penalizzata)
  - `pending_review: true`
  - Badge rosso "LOW CONFIDENCE"

## Checklist Implementazione

### Backend
- [ ] Task 1: Aggiornare import ProductNormalizerV2
- [ ] Task 2: Modificare `normalize_item` con nuova chiamata async
- [ ] Task 3: Cambiare da ThreadPoolExecutor a `asyncio.gather`
- [ ] Task 4: Aggiornare `ReceiptItemData` schema con nuovi campi
- [ ] Test: Verificare response API include `confidence_level` e `source`

### Frontend
- [ ] Task 5: Aggiornare type `ReceiptItemWithNormalized`
- [ ] Task 6: Aggiornare UI `ReceiptReview.tsx` con nuovi badge
- [ ] Test: Verificare badge visualizzati correttamente

### Integration Testing
- [ ] Test cache tier1 hit → source="cache_tier1", high confidence
- [ ] Test vector search → source="vector_search", medium/high
- [ ] Test LLM → source="llm", variable confidence
- [ ] Test price anomaly → pending_review=true, low confidence

## Note Importanti

1. **Async/Await**: ProductNormalizerV2 è async, tutte le chiamate devono usare `await`
2. **household_id obbligatorio**: Context service richiede household_id per enrichment
3. **Validazione automatica**: ProductNormalizerV2 include validation integrata
4. **Backward compatibility**: Frontend continua a funzionare anche senza nuovi campi (graceful degradation)

## Rollback Plan

Se problemi in produzione:

1. **Backend**: Revert import a `product_normalizer_agent`
2. **Frontend**: Rimuovi nuovi campi da UI (mantieni solo confidence %)
3. **Types**: Lascia nuovi campi optional (non breaking change)
