"""
TEST COMPLETO END-TO-END
Testa: OCR → AI Parsing → Normalizzazione → Database

REQUISITI:
1. Household di test in Supabase
2. Immagine scontrino in tests/fixtures/sample_receipt.jpg
3. API keys configurate (Google Vision, OpenAI, Supabase)

Esegui: python test_complete_flow.py
"""
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Carica .env
load_dotenv()

# Aggiungi app al path
sys.path.insert(0, os.path.abspath('.'))

from app.services.ocr_service import ocr_service
from app.services.ai_parser_service import ai_receipt_parser
from app.services.supabase_service import supabase_service
from app.services.store_service import store_service
from app.agents.product_normalizer import product_normalizer_agent

print("="*80)
print("TEST COMPLETO END-TO-END - SCONTRINI")
print("="*80)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ===================================
# CONFIGURAZIONE
# ===================================

IMAGE_PATH = "tests/fixtures/sample_receipt.jpg"
TEST_HOUSEHOLD_ID = "99cb47ef-5712-4362-8e94-4a1ef651f7c0"  # MODIFICA!
TEST_USER_ID = "1c1ffd3e-511a-41f7-933a-8558ddfb5660"  # MODIFICA!

print(f"\n📁 Immagine: {IMAGE_PATH}")
print(f"🏠 Household: {TEST_HOUSEHOLD_ID}")
print(f"👤 User: {TEST_USER_ID}")

# Verifica file
if not os.path.exists(IMAGE_PATH):
    print(f"\n❌ Immagine non trovata: {IMAGE_PATH}")
    sys.exit(1)

# ===================================
# STEP 1: OCR
# ===================================

print("\n" + "="*80)
print("STEP 1: OCR - Estrazione Testo")
print("="*80)

ocr_result = ocr_service.extract_text_from_image(image_path=IMAGE_PATH)

if not ocr_result["success"]:
    print(f"❌ OCR fallito: {ocr_result.get('error')}")
    sys.exit(1)

print(f"✅ OCR completato")
print(f"   Confidence: {ocr_result.get('confidence', 0):.2%}")
print(f"   Caratteri: {len(ocr_result['text'])}")
print(f"   Parole: {len(ocr_result.get('words', []))}")

# ===================================
# STEP 2: AI PARSING
# ===================================

print("\n" + "="*80)
print("STEP 2: AI PARSING - Analisi Strutturata")
print("="*80)

estimated_cost = ai_receipt_parser.estimate_cost(ocr_result["text"])
print(f"💰 Costo stimato: ${estimated_cost:.4f}")

parsing_result = ai_receipt_parser.parse_receipt(ocr_result["text"])

if not parsing_result["success"]:
    print(f"❌ Parsing fallito: {parsing_result.get('error')}")
    sys.exit(1)

print(f"✅ Parsing completato")
print(f"\n📊 Dati estratti:")
print(f"   Negozio: {parsing_result.get('store_name') or 'Non trovato'}")
print(f"   Data: {parsing_result.get('receipt_date') or 'Non trovata'}")
print(f"   Totale: €{parsing_result.get('total_amount') or 0:.2f}")
print(f"   Prodotti: {len(parsing_result.get('items', []))}")

if parsing_result.get('items'):
    print(f"\n🛒 Prodotti parsati:")
    for i, item in enumerate(parsing_result['items'][:5], 1):
        print(f"   {i}. {item['raw_product_name']} - €{item['total_price']:.2f}")
    
    if len(parsing_result['items']) > 5:
        print(f"   ... e altri {len(parsing_result['items']) - 5} prodotti")

# ===================================
# STEP 3: FIND/CREATE STORE
# ===================================

print("\n" + "="*80)
print("STEP 3: STORE - Identificazione Negozio")
print("="*80)

store_result = store_service.find_or_create_store({
    "name": parsing_result.get("store_name"),
    "company_name": parsing_result.get("company_name"),
    "vat_number": parsing_result.get("vat_number"),
    "address_full": parsing_result.get("address_full"),
    "address_street": parsing_result.get("address_street"),
    "address_city": parsing_result.get("address_city"),
    "address_province": parsing_result.get("address_province"),
    "address_postal_code": parsing_result.get("address_postal_code")
})

print(f"✅ Store identificato")
print(f"   ID: {store_result['store_id']}")
print(f"   Nome: {store_result['store']['name']}")
print(f"   Matched by: {store_result['matched_by']}")
print(f"   Created new: {store_result['created_new']}")
if store_result['store'].get('address_city'):
    print(f"   Città: {store_result['store']['address_city']}")
if store_result['store'].get('vat_number'):
    print(f"   P.IVA: {store_result['store']['vat_number']}")

store_id = store_result['store_id']
store_name = store_result['store']['name']

# ===================================
# STEP 4: SALVA SCONTRINO E ITEMS
# ===================================

print("\n" + "="*80)
print("STEP 4: DATABASE - Salvataggio Scontrino")
print("="*80)

try:
    # Verifica household
    household = supabase_service.get_household(TEST_HOUSEHOLD_ID)
    if not household:
        print(f"❌ Household non trovato: {TEST_HOUSEHOLD_ID}")
        sys.exit(1)
    
    print(f"✅ Household: {household.get('name')}")
    
    # Crea receipt
    receipt = supabase_service.create_receipt(
        household_id=TEST_HOUSEHOLD_ID,
        uploaded_by=TEST_USER_ID,
        image_url=f"file:///{IMAGE_PATH}",
        store_id=store_id,
        store_name=store_name,
        store_address=parsing_result.get("address_full"),
        receipt_date=parsing_result.get("receipt_date"),
        receipt_time=parsing_result.get("receipt_time"),
        total_amount=parsing_result.get("total_amount"),
        payment_method=parsing_result.get("payment_method"),
        discount_amount=parsing_result.get("discount_amount"),
        raw_ocr_text=ocr_result["text"],
        ocr_confidence=ocr_result.get("confidence"),
        processing_status="processing"
    )
    
    receipt_id = receipt['id']
    print(f"✅ Receipt creato: {receipt_id}")
    
    # Crea items
    items_data = []
    if parsing_result.get("items"):
        items_data = supabase_service.create_receipt_items(
            receipt_id=receipt_id,
            items=parsing_result['items']
        )
        print(f"✅ {len(items_data)} items salvati")

except Exception as e:
    print(f"❌ Errore database: {e}")
    sys.exit(1)

# ===================================
# STEP 5: NORMALIZZAZIONE CON AGENTE AI
# ===================================

print("\n" + "="*80)
print("STEP 5: AI AGENT - Normalizzazione Prodotti")
print("="*80)

if not items_data:
    print("⚠️  Nessun prodotto da normalizzare")
else:
    print(f"🤖 Normalizzazione di {len(items_data)} prodotti con OpenAI Agent...")
    print()
    
    normalization_results = []
    products_normalized = 0
    products_created = 0
    
    for idx, item in enumerate(items_data, 1):
        print(f"[{idx}/{len(items_data)}] 📦 {item['raw_product_name']}")
        
        # Normalizza prodotto
        result = product_normalizer_agent.normalize_product(
            raw_product_name=item["raw_product_name"],
            store_name=parsing_result.get("store_name"),
            price=item.get("total_price")
        )
        
        normalization_results.append(result)
        
        if result["success"]:
            products_normalized += 1
            
            if result.get("created_new"):
                products_created += 1
                print(f"   ✨ Creato nuovo: {result.get('canonical_name')}")
            else:
                print(f"   ✅ Trovato: {result.get('canonical_name')}")
            
            # Crea purchase_history
            try:
                supabase_service.client.table("purchase_history").insert({
                    "household_id": TEST_HOUSEHOLD_ID,
                    "receipt_id": receipt_id,
                    "receipt_item_id": item["id"],
                    "normalized_product_id": result["normalized_product_id"],
                    "store_id": store_id,
                    "purchase_date": parsing_result.get("receipt_date").isoformat() if parsing_result.get("receipt_date") else None,
                    "store_name": store_name,
                    "quantity": item.get("quantity", 1),
                    "unit_price": item.get("unit_price"),
                    "total_price": item.get("total_price")
                }).execute()
            except Exception as e:
                print(f"   ⚠️  Purchase history error: {e}")
        else:
            print(f"   ❌ Fallito: {result.get('error')}")
        
        print()
    
    # Aggiorna receipt status
    supabase_service.update_receipt_status(receipt_id, "completed")
    
    # Aggiorna statistiche store
    store_service.update_store_statistics(store_id)

# ===================================
# STEP 6: VERIFICA FINALE
# ===================================

print("="*80)
print("STEP 6: VERIFICA FINALE")
print("="*80)

# Conta prodotti normalizzati
total_normalized_products = supabase_service.client.table("normalized_products")\
    .select("*", count="exact")\
    .execute()

# Conta mappings
total_mappings = supabase_service.client.table("product_mappings")\
    .select("*", count="exact")\
    .execute()

# Conta purchase history
total_purchases = supabase_service.client.table("purchase_history")\
    .select("*", count="exact")\
    .eq("household_id", TEST_HOUSEHOLD_ID)\
    .execute()

# Conta stores
total_stores = supabase_service.client.table("stores")\
    .select("*", count="exact")\
    .eq("is_mock", False)\
    .execute()

print(f"\n📊 Statistiche Database:")
print(f"   Prodotti normalizzati totali: {total_normalized_products.count}")
print(f"   Mappings totali: {total_mappings.count}")
print(f"   Stores totali: {total_stores.count}")
print(f"   Purchase history (tuo household): {total_purchases.count}")

# ===================================
# RIEPILOGO FINALE
# ===================================

print("\n" + "="*80)
print("🎉 TEST COMPLETATO CON SUCCESSO!")
print("="*80)

print(f"\n✅ Scontrino processato completamente:")
print(f"   Receipt ID: {receipt_id}")
print(f"   Household: {household.get('name')}")
print(f"   Negozio: {store_name}")
print(f"   Store ID: {store_id}")
print(f"   Prodotti: {len(items_data)}")
print(f"   Prodotti normalizzati: {products_normalized}/{len(items_data)}")
print(f"   Nuovi prodotti creati: {products_created}")
print(f"   Totale: €{parsing_result.get('total_amount', 0):.2f}")

print(f"\n💰 Costi stimati:")
print(f"   Google Vision OCR: $0 (free tier)")
print(f"   OpenAI Parsing: ~${estimated_cost:.4f}")
print(f"   OpenAI Normalizzazione: ~${len(items_data) * 0.002:.4f}")
print(f"   TOTALE: ~${estimated_cost + len(items_data) * 0.002:.4f}")

print(f"\n📍 Verifica in Supabase:")
print(f"   Table Editor → receipts → cerca: {receipt_id}")
print(f"   Table Editor → stores → vedi negozi normalizzati")
print(f"   Table Editor → normalized_products → vedi prodotti normalizzati")
print(f"   Table Editor → purchase_history → vedi acquisti")

print(f"\n🎯 Prossimi passi:")
print(f"   ✅ Task 1-5 completati + Stores!")
print(f"   ⏭️  Task 6-10: Frontend + Dashboard + Analytics + Deploy")

print("\n" + "="*80)
