"""
Test completo Receipt Processing
Testa OCR + Parsing + Database

REQUISITI:
1. Crea un household di test in Supabase
2. Metti un'immagine di scontrino in tests/fixtures/sample_receipt.jpg
3. Esegui: python test_receipt_processing.py
"""
import os
import sys
from dotenv import load_dotenv

# Carica .env
load_dotenv()

# Aggiungi app al path
sys.path.insert(0, os.path.abspath('.'))

from app.services.ocr_service import ocr_service
from app.services.ai_parser_service import ai_receipt_parser  # AI Parser
from app.services.parser_service import receipt_parser  # Fallback
from app.services.supabase_service import supabase_service

print("="*60)
print("TEST RECEIPT PROCESSING - END TO END")
print("="*60)

# ===================================
# CONFIGURAZIONE
# ===================================

# Path immagine test (metti uno scontrino qui)
IMAGE_PATH = "tests/fixtures/sample_receipt.jpg"

# ID household test (sostituisci con un ID reale dal tuo database)
# Puoi ottenerlo da: Supabase → Table Editor → households
TEST_HOUSEHOLD_ID = "99cb47ef-5712-4362-8e94-4a1ef651f7c0"  # MODIFICA QUESTO!

# ID utente test (sostituisci con un ID reale)
# Puoi ottenerlo da: Supabase → Authentication → Users
TEST_USER_ID = "1c1ffd3e-511a-41f7-933a-8558ddfb5660"  # MODIFICA QUESTO!

print(f"\n📁 Immagine test: {IMAGE_PATH}")
print(f"🏠 Household ID: {TEST_HOUSEHOLD_ID}")
print(f"👤 User ID: {TEST_USER_ID}")

# Verifica immagine esista
if not os.path.exists(IMAGE_PATH):
    print(f"\n❌ ERRORE: Immagine non trovata: {IMAGE_PATH}")
    print("Crea la directory tests/fixtures/ e metti uno scontrino come sample_receipt.jpg")
    sys.exit(1)

print("\n" + "="*60)
print("STEP 1: OCR - Estrazione Testo")
print("="*60)

# Esegui OCR
ocr_result = ocr_service.extract_text_from_image(image_path=IMAGE_PATH)

if not ocr_result["success"]:
    print(f"❌ OCR fallito: {ocr_result.get('error')}")
    sys.exit(1)

print(f"✅ OCR completato")
print(f"   Confidence: {ocr_result.get('confidence', 0):.2%}")
print(f"   Parole trovate: {len(ocr_result.get('words', []))}")
print(f"   Lunghezza testo: {len(ocr_result['text'])} caratteri")

print(f"\n📄 Testo estratto (prime 500 caratteri):")
print("-" * 60)
print(ocr_result["text"][:500])
print("-" * 60)

# ===================================
# STEP 2: PARSING
# ===================================

print("\n" + "="*60)
print("STEP 2: PARSING - Analisi Dati con AI")
print("="*60)

# Stima costo
estimated_cost = ai_receipt_parser.estimate_cost(ocr_result["text"])
print(f"💰 Costo stimato chiamata OpenAI: ${estimated_cost:.4f}")

parsing_result = ai_receipt_parser.parse_receipt(ocr_result["text"])

if not parsing_result["success"]:
    print(f"⚠️ AI parsing fallito: {parsing_result.get('error')}")
    print("🔄 Tentativo con regex parser...")
    parsing_result = receipt_parser.parse_receipt(ocr_result["text"])
    
    if not parsing_result["success"]:
        print(f"❌ Anche regex parsing fallito: {parsing_result.get('error')}")
        sys.exit(1)

print(f"✅ Parsing completato")
print(f"\n📊 Dati estratti:")
print(f"   Negozio: {parsing_result.get('store_name') or 'Non trovato'}")
print(f"   Indirizzo: {parsing_result.get('store_address') or 'Non trovato'}")
print(f"   Data: {parsing_result.get('receipt_date') or 'Non trovata'}")
print(f"   Ora: {parsing_result.get('receipt_time') or 'Non trovata'}")

# Gestisci None per total_amount
total = parsing_result.get('total_amount')
if total is not None:
    print(f"   Totale: €{total:.2f}")
else:
    print(f"   Totale: Non trovato")

print(f"   Metodo pagamento: {parsing_result.get('payment_method') or 'Non trovato'}")
print(f"   Prodotti trovati: {len(parsing_result.get('items', []))}")

if parsing_result.get('items'):
    print(f"\n🛒 Primi 5 prodotti:")
    for i, item in enumerate(parsing_result['items'][:5], 1):
        print(f"   {i}. {item['raw_product_name']}")
        print(f"      Quantità: {item['quantity']} | Prezzo: €{item['total_price']:.2f}")

# ===================================
# STEP 3: SALVA IN DATABASE
# ===================================

print("\n" + "="*60)
print("STEP 3: DATABASE - Salvataggio")
print("="*60)

try:
    # Verifica household esista
    household = supabase_service.get_household(TEST_HOUSEHOLD_ID)
    if not household:
        print(f"❌ Household non trovato: {TEST_HOUSEHOLD_ID}")
        print("Crea un household in Supabase o usa l'ID di uno esistente")
        sys.exit(1)
    
    print(f"✅ Household trovato: {household.get('name', 'Unnamed')}")
    
    # Crea receipt
    receipt = supabase_service.create_receipt(
        household_id=TEST_HOUSEHOLD_ID,
        uploaded_by=TEST_USER_ID,
        image_url=f"file:///{IMAGE_PATH}",  # In produzione sarà URL Supabase Storage
        store_name=parsing_result.get("store_name"),
        store_address=parsing_result.get("store_address"),
        receipt_date=parsing_result.get("receipt_date"),
        receipt_time=parsing_result.get("receipt_time"),
        total_amount=parsing_result.get("total_amount"),
        payment_method=parsing_result.get("payment_method"),
        discount_amount=parsing_result.get("discount_amount"),
        raw_ocr_text=ocr_result["text"],
        ocr_confidence=ocr_result.get("confidence"),
        processing_status="completed"
    )
    
    print(f"✅ Receipt creato: {receipt['id']}")
    
    # Crea items
    if parsing_result.get("items"):
        items = supabase_service.create_receipt_items(
            receipt_id=receipt['id'],
            items=parsing_result['items']
        )
        print(f"✅ {len(items)} items salvati")
    
    print("\n" + "="*60)
    print("🎉 TEST COMPLETATO CON SUCCESSO!")
    print("="*60)
    print(f"\n✅ Scontrino salvato nel database")
    print(f"   Receipt ID: {receipt['id']}")
    print(f"   Household: {household.get('name')}")
    print(f"   Prodotti: {len(parsing_result.get('items', []))}")
    
    # Gestisci None per total_amount
    total = parsing_result.get('total_amount')
    if total is not None:
        print(f"   Totale: €{total:.2f}")
    else:
        print(f"   Totale: Non trovato (controlla manualmente lo scontrino)")
    
    print(f"\n📍 Verifica in Supabase:")
    print(f"   Table Editor → receipts → cerca ID: {receipt['id']}")
    print(f"   Table Editor → receipt_items → filtra per receipt_id")
    
except Exception as e:
    print(f"\n❌ Errore database: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
