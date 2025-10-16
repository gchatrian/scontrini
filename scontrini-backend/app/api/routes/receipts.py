"""
Receipt API Routes
Endpoints per gestione scontrini
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.api.schemas.receipt import (
    ProcessReceiptRequest,
    ProcessReceiptResponse,
    ReceiptResponse,
    ReceiptListResponse,
    ReceiptItemResponse
)
from app.services.ocr_service import ocr_service
from app.services.ai_parser_service import ai_receipt_parser
from app.services.parser_service import receipt_parser
from app.services.supabase_service import supabase_service
from app.services.store_service import store_service  # Store service
from app.agents.product_normalizer import product_normalizer_agent
from typing import List
import tempfile
import os

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
    
    try:
        # Verifica che household esista
        household = supabase_service.get_household(request.household_id)
        if not household:
            raise HTTPException(status_code=404, detail="Household not found")
        
        # Step 1: Crea record scontrino (status=processing)
        receipt = supabase_service.create_receipt(
            household_id=request.household_id,
            uploaded_by=request.uploaded_by,
            image_url=request.image_url,
            processing_status="processing"
        )
        
        receipt_id = receipt["id"]
        
        try:
            # Step 2: OCR - Scarica immagine e processa
            # TODO: In produzione, scarica da Supabase Storage
            # Per ora assumiamo che image_url sia accessibile
            
            # Opzione A: Se image_url è URL pubblico
            import requests
            img_response = requests.get(request.image_url)
            img_content = img_response.content
            
            ocr_result = ocr_service.extract_text_from_image(
                image_content=img_content
            )
            
            if not ocr_result["success"]:
                raise Exception(f"OCR failed: {ocr_result.get('error')}")
            
            # Step 3: Parsing con AI (più accurato)
            parsing_result = ai_receipt_parser.parse_receipt(ocr_result["text"])
            
            # Fallback: se AI parsing fallisce, usa regex parser
            if not parsing_result["success"]:
                print("⚠️ AI parsing fallito, usando regex fallback")
                parsing_result = receipt_parser.parse_receipt(ocr_result["text"])
            
            if not parsing_result["success"]:
                raise Exception(f"Parsing failed: {parsing_result.get('error')}")
            
            # Step 4: Find or create store
            print(f"🏪 Finding/creating store...")
            
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
            
            store_id = store_result.get("store_id")
            print(f"✅ Store: {store_result.get('store', {}).get('name')} (matched by: {store_result.get('matched_by')})")
            
            # Step 5: Aggiorna scontrino con dati parsati + store_id
            updated_receipt = supabase_service.client.table("receipts")\
                .update({
                    "store_id": store_id,
                    "store_name": parsing_result.get("store_name"),
                    "store_address": parsing_result.get("address_full"),
                    "receipt_date": parsing_result.get("receipt_date").isoformat() if parsing_result.get("receipt_date") else None,
                    "receipt_time": parsing_result.get("receipt_time").isoformat() if parsing_result.get("receipt_time") else None,
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
            items_data = []
            if parsing_result.get("items"):
                items_data = supabase_service.create_receipt_items(
                    receipt_id=receipt_id,
                    items=parsing_result["items"]
                )
            
            # Step 6: Normalizza prodotti con agente AI
            print(f"🤖 Normalizing {len(items_data)} products with AI agent...")
            
            normalization_results = []
            if items_data:
                # Normalizza ogni prodotto
                for item_data in items_data:
                    print(f"  📦 Normalizing: {item_data['raw_product_name']}")
                    
                    norm_result = product_normalizer_agent.normalize_product(
                        raw_product_name=item_data["raw_product_name"],
                        store_name=parsing_result.get("store_name"),
                        price=item_data.get("total_price")
                    )
                    
                    normalization_results.append(norm_result)
                    
                    # Se normalizzazione riuscita, crea entry in purchase_history
                    if norm_result["success"] and norm_result.get("normalized_product_id"):
                        # Usa receipt_date se presente, altrimenti fallback a now UTC
                        from datetime import datetime, timezone
                        purchase_date_value = parsing_result.get("receipt_date")
                        # Assicura formato DATE (YYYY-MM-DD), mai datetime
                        if purchase_date_value is not None:
                            purchase_date_str = purchase_date_value.isoformat()
                        else:
                            purchase_date_str = datetime.now(timezone.utc).date().isoformat()

                        supabase_service.client.table("purchase_history").insert({
                            "household_id": request.household_id,
                            "receipt_id": receipt_id,
                            "receipt_item_id": item_data["id"],
                            "normalized_product_id": norm_result["normalized_product_id"],
                            "store_id": store_id,  # Aggiungi store_id
                            "purchase_date": purchase_date_str,
                            "store_name": parsing_result.get("store_name"),
                            "quantity": item_data.get("quantity", 1),
                            "unit_price": item_data.get("unit_price"),
                            "total_price": item_data.get("total_price")
                        }).execute()
                        
                        print(f"    ✅ Normalized: {norm_result.get('canonical_name')}")
                    else:
                        print(f"    ⚠️  Failed to normalize")
            
            # Step 7: Ottieni scontrino completo con items
            final_receipt = supabase_service.get_receipt(receipt_id)
            items = supabase_service.get_receipt_items(receipt_id)
            
            final_receipt["items"] = items
            
            # Step 8: Aggiorna statistiche store
            if store_id and store_id != store_service.MOCK_STORE_ID:
                store_service.update_store_statistics(store_id)
            
            return ProcessReceiptResponse(
                success=True,
                message="Scontrino processato con successo",
                receipt=ReceiptResponse(**final_receipt),
                ocr_result={
                    "text_length": len(ocr_result["text"]),
                    "confidence": ocr_result.get("confidence"),
                    "words_count": len(ocr_result.get("words", []))
                },
                parsing_result={
                    "items_found": len(parsing_result.get("items", [])),
                    "store_detected": parsing_result.get("store_name") is not None,
                    "products_normalized": len([r for r in normalization_results if r.get("success")]),
                    "products_created": len([r for r in normalization_results if r.get("created_new")])
                }
            )
            
        except Exception as e:
            # Errore durante processing: aggiorna status a failed
            supabase_service.update_receipt_status(receipt_id, "failed")
            
            raise HTTPException(
                status_code=500,
                detail=f"Processing error: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
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
