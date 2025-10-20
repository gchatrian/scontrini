"""
Receipt API Routes
Endpoints per gestione scontrini con normalizzazione prodotti
"""
from fastapi import APIRouter, HTTPException
from app.api.schemas.receipt import (
    ProcessReceiptRequest,
    ProcessReceiptResponse,
    ParsedReceiptData,
    ReceiptItemData,
    ReceiptResponse,
    ReceiptListResponse,
    UpdateProductReviewRequest,
    UpdateProductReviewResponse
)
from app.services.ocr_service import ocr_service
from app.services.ai_parser_service import ai_receipt_parser
from app.services.parser_service import receipt_parser
from app.services.supabase_service import supabase_service
from app.services.store_service import store_service
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import requests

# Crea il router
router = APIRouter()


@router.post("/process", response_model=ProcessReceiptResponse)
async def process_receipt(request: ProcessReceiptRequest):
    """
    Processa uno scontrino completo con normalizzazione prodotti:
    1. OCR per estrarre testo
    2. Parsing per analizzare dati  
    3. Find/Create Store
    4. Salva receipt e items
    5. Normalizzazione prodotti (parallelo)
    6. Salva purchase history
    
    Flow:
    - Frontend carica immagine su Supabase Storage
    - Frontend chiama questo endpoint con l'URL
    - Backend fa OCR → parsing → store → normalizzazione → salva
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
            store_data = None
            store_name = parsing_result.get("store_name")
            
            if store_name:
                print(f"🏪 Cercando/creando store: {store_name}")
                store_result = store_service.find_or_create_store({
                    "name": store_name,
                    "company_name": parsing_result.get("company_name"),
                    "vat_number": parsing_result.get("vat_number"),
                    "address_full": parsing_result.get("address_full"),
                    "address_street": parsing_result.get("address_street"),
                    "address_city": parsing_result.get("address_city"),
                    "address_province": parsing_result.get("address_province"),
                    "address_postal_code": parsing_result.get("address_postal_code")
                })
                
                if store_result.get("success"):
                    store_id = store_result["store_id"]
                    store_data = store_result["store"]
                    print(f"✅ Store: {store_data['name']} (ID: {store_id})")
                    print(f"   Matched by: {store_result.get('matched_by')}")
                    print(f"   Created new: {store_result.get('created_new', False)}")
                else:
                    print(f"⚠️ Store service fallito: {store_result.get('error')}")
            
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
                    "processing_status": "processing"  # Ancora in processing per normalizzazione
                })\
                .eq("id", receipt_id)\
                .execute()
            
            print("✅ Receipt aggiornato con dati parsati")
            
            # Step 6: Salva items
            receipt_items_data = []
            if parsing_result.get("items"):
                items_to_insert = []
                for idx, item in enumerate(parsing_result["items"]):
                    items_to_insert.append({
                        "receipt_id": receipt_id,
                        "raw_product_name": item.get("raw_product_name", ""),
                        "quantity": item.get("quantity", 1),
                        "unit_price": item.get("unit_price"),
                        "total_price": item.get("total_price", 0),
                        "line_number": idx + 1
                    })
                
                receipt_items_data = supabase_service.create_receipt_items(
                    receipt_id=receipt_id,
                    items=items_to_insert
                )
                
                print(f"✅ Salvati {len(receipt_items_data)} items")
            
            # ============================================
            # Step 7: NORMALIZZAZIONE PRODOTTI (PARALLELO)
            # ============================================
            normalized_results = []
            
            if receipt_items_data:
                print(f"\n{'='*60}")
                print(f"🧠 Iniziando normalizzazione di {len(receipt_items_data)} prodotti...")
                print(f"{'='*60}\n")
                
                from app.agents.product_normalizer import product_normalizer_agent
                
                # Funzione helper per normalizzare un singolo item
                def normalize_single_item(item_data: Dict, receipt_item: Dict) -> Dict:
                    """Normalizza singolo prodotto"""
                    try:
                        result = product_normalizer_agent.normalize_product(
                            raw_product_name=item_data.get("raw_product_name", ""),
                            store_name=store_name,
                            price=item_data.get("total_price")
                        )
                        
                        # Aggiungi info item originale
                        result["receipt_item_id"] = receipt_item["id"]
                        result["raw_product_name"] = item_data.get("raw_product_name")
                        result["quantity"] = item_data.get("quantity")
                        result["total_price"] = item_data.get("total_price")
                        
                        return result
                        
                    except Exception as e:
                        print(f"❌ Errore normalizzazione '{item_data.get('raw_product_name')}': {str(e)}")
                        return {
                            "success": False,
                            "error": str(e),
                            "receipt_item_id": receipt_item["id"],
                            "raw_product_name": item_data.get("raw_product_name")
                        }
                
                # Processa items in parallelo (max 5 alla volta per evitare rate limits)
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = []
                    for parsed_item, receipt_item in zip(parsing_result["items"], receipt_items_data):
                        future = executor.submit(normalize_single_item, parsed_item, receipt_item)
                        futures.append(future)
                    
                    # Attendi completamento
                    for future in futures:
                        normalized_results.append(future.result())
                
                print(f"\n{'='*60}")
                print(f"✅ Normalizzazione completata")
                print(f"   Successi: {sum(1 for r in normalized_results if r.get('success'))}")
                print(f"   Fallimenti: {sum(1 for r in normalized_results if not r.get('success'))}")
                print(f"   Pending review: {sum(1 for r in normalized_results if r.get('pending_review'))}")
                print(f"{'='*60}\n")
            
            # ============================================
            # Step 8: SALVA PURCHASE HISTORY
            # ============================================
            purchase_history_saved = []
            
            for norm_result in normalized_results:
                if norm_result.get("success") and norm_result.get("normalized_product_id"):
                    try:
                        purchase_record = supabase_service.create_purchase_history(
                            household_id=request.household_id,
                            receipt_id=receipt_id,
                            receipt_item_id=norm_result["receipt_item_id"],
                            normalized_product_id=norm_result["normalized_product_id"],
                            purchase_date=parsing_result.get("receipt_date") or datetime.now().date(),
                            store_id=store_id,
                            quantity=norm_result.get("quantity"),
                            unit_price=norm_result.get("total_price") / norm_result.get("quantity", 1) if norm_result.get("quantity") else None,
                            total_price=norm_result.get("total_price", 0)
                        )
                        
                        if purchase_record:
                            purchase_history_saved.append(purchase_record)
                            
                    except Exception as e:
                        print(f"⚠️ Errore salvataggio purchase history: {str(e)}")
            
            print(f"✅ Salvati {len(purchase_history_saved)} record in purchase_history")
            
            # ============================================
            # Step 9: UPDATE STORE STATS
            # ============================================
            if store_id and parsing_result.get("total_amount"):
                try:
                    store_service.update_store_stats(
                        store_id=store_id,
                        receipt_total=parsing_result.get("total_amount")
                    )
                    print(f"✅ Statistiche store aggiornate")
                except Exception as e:
                    print(f"⚠️ Errore aggiornamento stats store: {str(e)}")
            
            # ============================================
            # Step 10: FINALIZZA RECEIPT
            # ============================================
            supabase_service.client.table("receipts")\
                .update({"processing_status": "completed"})\
                .eq("id", receipt_id)\
                .execute()
            
            print(f"\n✅ Processing completato con successo! Receipt ID: {receipt_id}\n")
            
            # ============================================
            # RESPONSE
            # ============================================
            return ProcessReceiptResponse(
                success=True,
                receipt_id=receipt_id,
                parsed_data=ParsedReceiptData(
                    store_name=parsing_result.get("store_name"),
                    company_name=parsing_result.get("company_name"),
                    vat_number=parsing_result.get("vat_number"),
                    store_address=parsing_result.get("address_full"),
                    receipt_date=parsing_result.get("receipt_date").isoformat() if parsing_result.get("receipt_date") else None,
                    receipt_time=parsing_result.get("receipt_time").isoformat() if parsing_result.get("receipt_time") else None,
                    total_amount=parsing_result.get("total_amount"),
                    payment_method=parsing_result.get("payment_method"),
                    discount_amount=parsing_result.get("discount_amount"),
                    items=[
                        ReceiptItemData(
                            raw_product_name=norm.get("raw_product_name", ""),
                            quantity=norm.get("quantity", 1),
                            unit_price=norm.get("total_price", 0) / norm.get("quantity", 1) if norm.get("quantity") else 0,
                            total_price=norm.get("total_price", 0),
                            # Dati normalizzati
                            normalized_product_id=norm.get("normalized_product_id"),
                            canonical_name=norm.get("canonical_name"),
                            brand=norm.get("brand"),
                            category=norm.get("category"),
                            subcategory=norm.get("subcategory"),
                            size=norm.get("size"),
                            unit_type=norm.get("unit_type"),
                            confidence=norm.get("confidence", 0),
                            pending_review=norm.get("pending_review", False),
                            from_cache=norm.get("from_cache", False)
                        )
                        for norm in normalized_results
                    ],
                    store_id=store_id,
                    store_data=store_data
                ),
                ocr_confidence=ocr_result.get("confidence"),
                message="Scontrino elaborato con successo"
            )
            
        except Exception as e:
            # Se errore durante processing, aggiorna status a failed
            print(f"\n❌ Errore durante processing: {str(e)}\n")
            
            supabase_service.client.table("receipts")\
                .update({"processing_status": "failed"})\
                .eq("id", receipt_id)\
                .execute()
            
            raise HTTPException(
                status_code=500,
                detail=f"Processing error: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n💥 Errore generale: {str(e)}\n")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.put("/items/{receipt_item_id}/review", response_model=UpdateProductReviewResponse)
async def update_product_review(
    receipt_item_id: str,
    review_data: UpdateProductReviewRequest
):
    """
    Aggiorna prodotto normalizzato dopo review manuale utente
    
    Flow:
    1. Ottieni receipt_item e mapping corrente
    2. Aggiorna normalized_product con dati corretti
    3. Aggiorna product_mapping: verified_by_user=true, requires_manual_review=false
    4. Return success
    
    Args:
        receipt_item_id: ID del receipt_item da aggiornare
        review_data: Dati corretti dall'utente
    """
    
    print(f"\n{'='*60}")
    print(f"📝 Update product review for item: {receipt_item_id}")
    print(f"   Canonical name: {review_data.canonical_name}")
    print(f"   Brand: {review_data.brand}")
    print(f"   Category: {review_data.category}")
    print(f"{'='*60}\n")
    
    try:
        # Step 1: Ottieni receipt_item
        receipt_item_response = supabase_service.client.table("receipt_items")\
            .select("*, receipts(store_name)")\
            .eq("id", receipt_item_id)\
            .execute()
        
        if not receipt_item_response.data:
            raise HTTPException(status_code=404, detail="Receipt item not found")
        
        receipt_item = receipt_item_response.data[0]
        raw_name = receipt_item["raw_product_name"]
        store_name = receipt_item.get("receipts", {}).get("store_name")
        
        print(f"✅ Receipt item trovato: '{raw_name}'")
        
        # Step 2: Trova mapping corrente
        mapping_response = supabase_service.client.table("product_mappings")\
            .select("*")\
            .eq("raw_name", raw_name)
        
        if store_name:
            mapping_response = mapping_response.eq("store_name", store_name)
        
        mapping_response = mapping_response.execute()
        
        if not mapping_response.data:
            raise HTTPException(status_code=404, detail="Product mapping not found")
        
        mapping = mapping_response.data[0]
        normalized_product_id = mapping["normalized_product_id"]
        
        print(f"✅ Mapping trovato: {mapping['id']}")
        print(f"   Normalized product ID: {normalized_product_id}")
        
        # Step 3: Aggiorna normalized_product con dati corretti
        update_product_data = {
            "canonical_name": review_data.canonical_name,
            "brand": review_data.brand,
            "category": review_data.category,
            "subcategory": review_data.subcategory,
            "size": review_data.size,
            "unit_type": review_data.unit_type,
            "verification_status": "user_verified"  # Marcato come verificato da utente
        }
        
        updated_product = supabase_service.client.table("normalized_products")\
            .update(update_product_data)\
            .eq("id", normalized_product_id)\
            .execute()
        
        print(f"✅ Normalized product aggiornato")
        
        # Step 4: Aggiorna product_mapping
        update_mapping_data = {
            "verified_by_user": True,
            "requires_manual_review": False,
            "confidence_score": 1.0,  # Confidence massima dopo verifica utente
            "reviewed_at": "NOW()"
        }
        
        updated_mapping = supabase_service.client.table("product_mappings")\
            .update(update_mapping_data)\
            .eq("id", mapping["id"])\
            .execute()
        
        print(f"✅ Product mapping aggiornato (verified_by_user=true)")
        
        # Step 5: Aggiorna anche purchase_history se esiste
        purchase_history_response = supabase_service.client.table("purchase_history")\
            .select("id")\
            .eq("receipt_item_id", receipt_item_id)\
            .execute()
        
        if purchase_history_response.data:
            for ph_record in purchase_history_response.data:
                # Aggiorna solo il normalized_product_id se è cambiato
                supabase_service.client.table("purchase_history")\
                    .update({"normalized_product_id": normalized_product_id})\
                    .eq("id", ph_record["id"])\
                    .execute()
            
            print(f"✅ Purchase history aggiornato ({len(purchase_history_response.data)} records)")
        
        print(f"\n✅ Review completata con successo!\n")
        
        return UpdateProductReviewResponse(
            success=True,
            message="Prodotto aggiornato con successo",
            normalized_product_id=normalized_product_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Errore durante update review: {str(e)}\n")
        raise HTTPException(
            status_code=500,
            detail=f"Update error: {str(e)}"
        )


@router.get("/items/{receipt_item_id}/normalized")
async def get_normalized_product_for_item(receipt_item_id: str):
    """
    Ottieni prodotto normalizzato per un receipt_item
    Utile per frontend per caricare dati correnti prima di edit
    """
    
    try:
        # Ottieni receipt_item
        receipt_item_response = supabase_service.client.table("receipt_items")\
            .select("*, receipts(store_name)")\
            .eq("id", receipt_item_id)\
            .execute()
        
        if not receipt_item_response.data:
            raise HTTPException(status_code=404, detail="Receipt item not found")
        
        receipt_item = receipt_item_response.data[0]
        raw_name = receipt_item["raw_product_name"]
        store_name = receipt_item.get("receipts", {}).get("store_name")
        
        # Trova mapping
        mapping_response = supabase_service.client.table("product_mappings")\
            .select("*, normalized_products(*)")\
            .eq("raw_name", raw_name)
        
        if store_name:
            mapping_response = mapping_response.eq("store_name", store_name)
        
        mapping_response = mapping_response.execute()
        
        if not mapping_response.data:
            return {
                "success": False,
                "error": "No normalized product found for this item"
            }
        
        mapping = mapping_response.data[0]
        
        return {
            "success": True,
            "receipt_item": receipt_item,
            "mapping": {
                "id": mapping["id"],
                "confidence_score": mapping.get("confidence_score"),
                "verified_by_user": mapping.get("verified_by_user"),
                "requires_manual_review": mapping.get("requires_manual_review")
            },
            "normalized_product": mapping.get("normalized_products")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
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