"""
Receipt API Routes
Endpoints per gestione scontrini
"""
from fastapi import APIRouter, HTTPException
from app.api.schemas.receipt import (
    ProcessReceiptRequest,
    ProcessReceiptResponse,
    ParsedReceiptData,
    ReceiptItemData,
    ReceiptResponse,
    ReceiptListResponse
)
from app.services.ocr_service import ocr_service
from app.services.ai_parser_service import ai_receipt_parser
from app.services.parser_service import receipt_parser
from app.services.supabase_service import supabase_service
from app.services.store_service import store_service
from typing import List
import requests

router = APIRouter()


@router.post("/process", response_model=ProcessReceiptResponse)
async def process_receipt(request: ProcessReceiptRequest):
    """
    Processa uno scontrino completo:
    1. OCR per estrarre testo
    2. Parsing per analizzare dati
    3. Salva in database
    
    Flow:
    - Frontend carica immagine su Supabase Storage
    - Frontend chiama questo endpoint con l'URL
    - Backend fa OCR + parsing + salva
    """
    
    print(f"\n{'='*60}")
    print(f"🔍 Processing receipt request:")
    print(f"   household_id: {request.household_id}")
    print(f"   uploaded_by: {request.uploaded_by}")
    print(f"   image_url: {request.image_url}")
    print(f"{'='*60}\n")
    
    try:
        # Verifica che household esista
        household = supabase_service.get_household(request.household_id)
        if not household:
            raise HTTPException(status_code=404, detail="Household not found")
        
        print(f"✅ Household trovato: {household.get('name')}")
        
        # Step 1: Crea record scontrino (status=processing)
        receipt = supabase_service.create_receipt(
            household_id=request.household_id,
            uploaded_by=request.uploaded_by,
            image_url=request.image_url,
            processing_status="processing"
        )
        
        receipt_id = receipt["id"]
        print(f"✅ Receipt creato: {receipt_id}")
        
        try:
            # Step 2: OCR - Scarica immagine e processa
            print("📸 Downloading image...")
            img_response = requests.get(request.image_url, timeout=30)
            img_content = img_response.content
            
            print("🔍 Running OCR...")
            ocr_result = ocr_service.extract_text_from_image(
                image_content=img_content
            )
            
            if not ocr_result["success"]:
                raise Exception(f"OCR failed: {ocr_result.get('error')}")
            
            print(f"✅ OCR completato (confidence: {ocr_result.get('confidence', 0):.2%})")
            
            # Step 3: Parsing con AI (più accurato)
            print("🤖 Parsing con AI...")
            parsing_result = ai_receipt_parser.parse_receipt(ocr_result["text"])
            
            # Fallback: se AI parsing fallisce, usa regex parser
            if not parsing_result["success"]:
                print("⚠️ AI parsing fallito, usando regex fallback")
                parsing_result = receipt_parser.parse_receipt(ocr_result["text"])
            
            if not parsing_result["success"]:
                raise Exception(f"Parsing failed: {parsing_result.get('error')}")
            
            print(f"✅ Parsing completato: {len(parsing_result.get('items', []))} prodotti trovati")
            
            # Step 4: Find or create store
            store_id = None
            store_name = parsing_result.get("store_name")
            
            if store_name:
                print(f"🏪 Cercando store: {store_name}")
                store_result = store_service.find_or_create_store({
                    "name": store_name,
                    "address_full": parsing_result.get("store_address")
                })
                
                if store_result.get("success"):
                    store_id = store_result["store_id"]
                    print(f"✅ Store: {store_result['store']['name']} (ID: {store_id})")
                    print(f"   Matched by: {store_result.get('matched_by')}")
                else:
                    print("⚠️ Store matching fallito, continuando senza store_id")
            
            # Step 5: Aggiorna scontrino con dati parsati
            print("💾 Salvando dati scontrino...")
            updated_receipt = supabase_service.client.table("receipts")\
                .update({
                    "store_id": store_id,
                    "store_name": parsing_result.get("store_name"),
                    "store_address": parsing_result.get("store_address"),
                    "receipt_date": str(parsing_result.get("receipt_date")) if parsing_result.get("receipt_date") else None,
                    "receipt_time": str(parsing_result.get("receipt_time")) if parsing_result.get("receipt_time") else None,
                    "total_amount": parsing_result.get("total_amount"),
                    "payment_method": parsing_result.get("payment_method"),
                    "discount_amount": parsing_result.get("discount_amount"),
                    "raw_ocr_text": ocr_result["text"],
                    "ocr_confidence": ocr_result.get("confidence"),
                    "processing_status": "completed"
                })\
                .eq("id", receipt_id)\
                .execute()
            
            # Step 6: Salva items
            if parsing_result.get("items"):
                print(f"💾 Salvando {len(parsing_result['items'])} items...")
                supabase_service.create_receipt_items(
                    receipt_id=receipt_id,
                    items=parsing_result["items"]
                )
            
            print("✅ Processing completato con successo!")
            
            # Step 7: Prepara response con parsed_data
            return ProcessReceiptResponse(
                success=True,
                receipt_id=receipt_id,
                message="Scontrino processato con successo",
                parsed_data=ParsedReceiptData(
                    store_name=parsing_result.get("store_name"),
                    store_address=parsing_result.get("store_address"),
                    receipt_date=str(parsing_result.get("receipt_date")) if parsing_result.get("receipt_date") else None,
                    receipt_time=str(parsing_result.get("receipt_time")) if parsing_result.get("receipt_time") else None,
                    total_amount=float(parsing_result.get("total_amount")) if parsing_result.get("total_amount") else None,
                    tax_amount=float(parsing_result.get("tax_amount")) if parsing_result.get("tax_amount") else None,
                    payment_method=parsing_result.get("payment_method"),
                    items=[
                        ReceiptItemData(
                            raw_product_name=item.get("raw_product_name", ""),
                            quantity=float(item.get("quantity", 1)),
                            unit_price=float(item.get("unit_price", 0)),
                            total_price=float(item.get("total_price", 0)),
                            category=item.get("category")
                        )
                        for item in parsing_result.get("items", [])
                    ]
                ),
                ocr_confidence=ocr_result.get("confidence")
            )
            
        except Exception as e:
            # Errore durante processing: aggiorna status a failed
            print(f"❌ Errore processing: {str(e)}")
            supabase_service.update_receipt_status(receipt_id, "failed")
            
            import traceback
            traceback.print_exc()
            
            raise HTTPException(
                status_code=500,
                detail=f"Processing error: {str(e)}"
            )
    
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ ERRORE COMPLETO:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Messaggio: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(receipt_id: str):
    """Ottieni dettagli scontrino"""
    
    receipt = supabase_service.get_receipt(receipt_id)
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    # Carica items
    items = supabase_service.get_receipt_items(receipt_id)
    receipt["items"] = items
    
    return ReceiptResponse(**receipt)


@router.get("/household/{household_id}", response_model=ReceiptListResponse)
async def get_household_receipts(
    household_id: str,
    limit: int = 50
):
    """Ottieni tutti gli scontrini di un household"""
    
    receipts = supabase_service.get_receipts_by_household(
        household_id=household_id,
        limit=limit
    )
    
    # Per ogni receipt, carica items
    for receipt in receipts:
        items = supabase_service.get_receipt_items(receipt["id"])
        receipt["items"] = items
    
    return ReceiptListResponse(
        receipts=[ReceiptResponse(**r) for r in receipts],
        total=len(receipts),
        page=1,
        page_size=limit
    )


@router.delete("/{receipt_id}")
async def delete_receipt(receipt_id: str):
    """Elimina scontrino"""
    
    receipt = supabase_service.get_receipt(receipt_id)
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    # Elimina (cascade elimina anche items grazie a ON DELETE CASCADE)
    supabase_service.client.table("receipts")\
        .delete()\
        .eq("id", receipt_id)\
        .execute()
    
    return {"message": "Receipt deleted successfully"}