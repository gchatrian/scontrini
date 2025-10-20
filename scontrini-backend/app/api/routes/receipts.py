"""
Receipt API Routes
Endpoints per gestione scontrini con flusso completo:
UPLOAD → OCR → PARSING → Normalizzazione → Validazione → Score → Review Utente → Categorizzazione modificati → Salvataggio
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================

class ProcessReceiptRequest(BaseModel):
    household_id: str
    uploaded_by: str
    image_url: str


class NormalizedProductData(BaseModel):
    normalized_product_id: str
    canonical_name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    size: Optional[str] = None
    unit_type: Optional[str] = None
    confidence: float
    requires_manual_review: bool


class ReceiptItemData(BaseModel):
    receipt_item_id: str
    raw_product_name: str
    quantity: float
    unit_price: Optional[float]
    total_price: float
    normalized_product: NormalizedProductData


class ProcessReceiptResponse(BaseModel):
    success: bool
    receipt_id: str
    message: str
    store_name: Optional[str]
    receipt_date: Optional[str]
    total_amount: Optional[float]
    items: List[ReceiptItemData]


class ModifiedProduct(BaseModel):
    """Prodotto modificato dall'utente"""
    receipt_item_id: str
    canonical_name: str
    brand: Optional[str] = None
    size: Optional[str] = None
    unit_type: Optional[str] = None
    quantity: float
    total_price: float


class ConfirmReceiptRequest(BaseModel):
    """Conferma finale dopo review utente"""
    receipt_id: str
    modified_products: List[ModifiedProduct]  # Solo prodotti modificati


class ConfirmReceiptResponse(BaseModel):
    success: bool
    message: str
    receipt_id: str


# ============================================
# ENDPOINTS
# ============================================

@router.post("/process", response_model=ProcessReceiptResponse)
async def process_receipt(request: ProcessReceiptRequest):
    """
    Step 1-6: UPLOAD → OCR → PARSING → Normalizzazione → Validazione → Score
    
    Ritorna dati per review utente (con categoria/sottocategoria NASCOSTE nel frontend)
    """
    try:
        # Verifica household
        household = supabase_service.get_household(request.household_id)
        if not household:
            raise HTTPException(status_code=404, detail="Household not found")
        
        # Step 1-2: OCR
        print("📸 Step 1-2: OCR...")
        img_response = requests.get(request.image_url)
        img_content = img_response.content
        
        ocr_result = ocr_service.extract_text_from_image(image_content=img_content)
        if not ocr_result["success"]:
            raise Exception(f"OCR failed: {ocr_result.get('error')}")
        
        # Step 3: PARSING
        print("📝 Step 3: Parsing...")
        parsing_result = ai_receipt_parser.parse_receipt(ocr_result["text"])
        if not parsing_result["success"]:
            raise Exception(f"Parsing failed: {parsing_result.get('error')}")
        
        # Find or Create Store
        store_id = None
        if parsing_result.get("store_name"):
            store_result = store_service.find_or_create_store(
                store_name=parsing_result["store_name"],
                address=parsing_result.get("address_full"),
                city=parsing_result.get("address_city"),
                vat_number=parsing_result.get("vat_number")
            )
            if store_result["success"]:
                store_id = store_result["store"]["id"]
        
        # Crea receipt (status=processing)
        receipt = supabase_service.create_receipt(
            household_id=request.household_id,
            uploaded_by=request.uploaded_by,
            image_url=request.image_url,
            store_id=store_id,
            store_name=parsing_result.get("store_name"),
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
        receipt_id = receipt["id"]
        
        # Step 4-5-6: Normalizzazione + Validazione + Score (parallelo)
        print("🤖 Step 4-5-6: Normalizzazione + Validazione + Score...")
        
        parsed_items = parsing_result.get("items", [])
        
        # Aggrega prodotti duplicati
        aggregated_items = aggregate_duplicate_products(parsed_items)
        
        def normalize_item(item):
            """Normalizza singolo prodotto (include validazione e score)"""
            # Normalizzazione (già include validazione interna)
            norm_result = product_normalizer_agent.normalize_product(
                raw_product_name=item["raw_product_name"],
                store_name=parsing_result.get("store_name"),
                price=item["total_price"]
            )
            
            if not norm_result["success"]:
                print(f"⚠️ Normalization failed for '{item['raw_product_name']}': {norm_result.get('error')}")
                return None
            
            # Salva receipt_item
            item_record = supabase_service.create_receipt_item(
                receipt_id=receipt_id,
                raw_product_name=item["raw_product_name"],
                quantity=item.get("quantity", 1.0),
                unit_price=item.get("unit_price"),
                total_price=item["total_price"],
                line_number=item.get("line_number", 0)
            )
            
            return {
                "receipt_item_id": item_record["id"],
                "raw_product_name": item["raw_product_name"],
                "quantity": item.get("quantity", 1.0),
                "unit_price": item.get("unit_price"),
                "total_price": item["total_price"],
                "normalized_product": {
                    "normalized_product_id": norm_result["normalized_product_id"],
                    "canonical_name": norm_result["canonical_name"],
                    "brand": norm_result.get("brand"),
                    "category": norm_result.get("category"),  # PRESENTE ma nascosta nel frontend
                    "subcategory": norm_result.get("subcategory"),  # PRESENTE ma nascosta nel frontend
                    "size": norm_result.get("size"),
                    "unit_type": norm_result.get("unit_type"),
                    "confidence": norm_result.get("confidence", 0.5),
                    "requires_manual_review": norm_result.get("requires_manual_review", False)
                }
            }
        
        # Normalizza tutti i prodotti in parallelo
        with ThreadPoolExecutor(max_workers=5) as executor:
            normalized_items = list(executor.map(normalize_item, aggregated_items))
        
        # Filtra None (prodotti falliti)
        normalized_items = [item for item in normalized_items if item is not None]
        
        # Aggiorna receipt status
        supabase_service.client.table("receipts")\
            .update({"processing_status": "pending_review"})\
            .eq("id", receipt_id)\
            .execute()
        
        print(f"✅ Processing completato: {len(normalized_items)} prodotti normalizzati")
        
        return ProcessReceiptResponse(
            success=True,
            receipt_id=receipt_id,
            message="Scontrino processato. Verifica i dati prima di confermare.",
            store_name=parsing_result.get("store_name"),
            receipt_date=parsing_result.get("receipt_date"),
            total_amount=parsing_result.get("total_amount"),
            items=[ReceiptItemData(**item) for item in normalized_items]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in process_receipt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/confirm", response_model=ConfirmReceiptResponse)
async def confirm_receipt(request: ConfirmReceiptRequest):
    """
    Step 7-8: Review finale utente → Categorizzazione prodotti modificati → Salvataggio
    
    Flow:
    1. Riceve lista prodotti MODIFICATI dall'utente
    2. Per ogni prodotto modificato: ri-categorizza con LLM
    3. Aggiorna normalized_products con nuove categorie
    4. Crea purchase_history per TUTTI i prodotti
    5. Aggiorna receipt status=completed
    """
    try:
        # Verifica receipt
        receipt = supabase_service.get_receipt(request.receipt_id)
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        print(f"📋 Step 7-8: Conferma receipt {request.receipt_id}")
        print(f"   Prodotti modificati: {len(request.modified_products)}")
        
        # Step 7: Categorizzazione prodotti modificati
        for modified in request.modified_products:
            print(f"🔄 Re-categorizing modified product: {modified.canonical_name}")
            
            # Chiamata LLM per categorizzazione
            cat_result = categorization_service.categorize_product(
                canonical_name=modified.canonical_name,
                brand=modified.brand,
                size=modified.size,
                unit_type=modified.unit_type
            )
            
            if not cat_result["success"]:
                print(f"⚠️ Categorization failed for {modified.canonical_name}")
                continue
            
            # Ottieni normalized_product_id dal receipt_item
            item_data = supabase_service.client.table("receipt_items")\
                .select("*, product_mappings(normalized_product_id)")\
                .eq("id", modified.receipt_item_id)\
                .single()\
                .execute()
            
            if not item_data.data:
                continue
            
            mapping = item_data.data.get("product_mappings")
            if not mapping:
                continue
            
            normalized_product_id = mapping["normalized_product_id"]
            
            # Aggiorna normalized_product con nuovi dati + categoria
            supabase_service.client.table("normalized_products")\
                .update({
                    "canonical_name": modified.canonical_name,
                    "brand": modified.brand,
                    "size": modified.size,
                    "unit_type": modified.unit_type,
                    "category": cat_result["category"],
                    "subcategory": cat_result.get("subcategory")
                })\
                .eq("id", normalized_product_id)\
                .execute()
            
            print(f"✅ Updated: {modified.canonical_name} → {cat_result['category']}/{cat_result.get('subcategory')}")
        
        # Step 8: Crea purchase_history per TUTTI i prodotti
        print("💾 Step 8: Creating purchase history...")
        
        all_items = supabase_service.get_receipt_items(request.receipt_id)
        
        for item in all_items:
            # Ottieni normalized_product_id
            mapping_data = supabase_service.client.table("product_mappings")\
                .select("normalized_product_id")\
                .eq("raw_name", item["raw_product_name"])\
                .limit(1)\
                .execute()
            
            if not mapping_data.data:
                continue
            
            normalized_product_id = mapping_data.data[0]["normalized_product_id"]
            
            # Crea purchase_history
            supabase_service.create_purchase_history(
                household_id=receipt["household_id"],
                receipt_id=request.receipt_id,
                normalized_product_id=normalized_product_id,
                quantity=item["quantity"],
                unit_price=item.get("unit_price"),
                total_price=item["total_price"],
                purchase_date=receipt.get("receipt_date")
            )
        
        # Aggiorna receipt status=completed
        supabase_service.client.table("receipts")\
            .update({"processing_status": "completed"})\
            .eq("id", request.receipt_id)\
            .execute()
        
        print(f"✅ Receipt {request.receipt_id} completato!")
        
        return ConfirmReceiptResponse(
            success=True,
            message="Scontrino salvato con successo!",
            receipt_id=request.receipt_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in confirm_receipt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/{receipt_id}")
async def get_receipt(receipt_id: str):
    """Ottieni dettagli scontrino"""
    receipt = supabase_service.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    items = supabase_service.get_receipt_items(receipt_id)
    receipt["items"] = items
    
    return receipt


@router.get("/household/{household_id}")
async def get_household_receipts(household_id: str, limit: int = 50):
    """Ottieni tutti gli scontrini di un household"""
    receipts = supabase_service.get_receipts_by_household(
        household_id=household_id,
        limit=limit
    )
    
    for receipt in receipts:
        items = supabase_service.get_receipt_items(receipt["id"])
        receipt["items"] = items
    
    return {"receipts": receipts, "total": len(receipts)}


@router.delete("/{receipt_id}")
async def delete_receipt(receipt_id: str):
    """Elimina scontrino"""
    receipt = supabase_service.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    supabase_service.client.table("receipts")\
        .delete()\
        .eq("id", receipt_id)\
        .execute()
    
    return {"message": "Receipt deleted successfully"}