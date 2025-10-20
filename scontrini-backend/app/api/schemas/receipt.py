"""
Aggiorna app/api/schemas/receipt.py con questi schemas
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, time

# ===================================
# REQUEST SCHEMAS
# ===================================

class ProcessReceiptRequest(BaseModel):
    """Request per processare scontrino"""
    household_id: str
    uploaded_by: str
    image_url: str


# ===================================
# RESPONSE SCHEMAS
# ===================================

class ReceiptItemData(BaseModel):
    """Dati singolo item con normalizzazione"""
    # Dati grezzi
    raw_product_name: str
    quantity: float
    unit_price: float
    total_price: float
    
    # Dati normalizzati
    normalized_product_id: Optional[str] = None
    canonical_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    size: Optional[str] = None
    unit_type: Optional[str] = None
    confidence: Optional[float] = None
    pending_review: Optional[bool] = False
    from_cache: Optional[bool] = False


class StoreData(BaseModel):
    """Dati store completi"""
    id: str
    name: str
    chain: Optional[str] = None
    branch_name: Optional[str] = None
    vat_number: Optional[str] = None
    company_name: Optional[str] = None
    address_full: Optional[str] = None
    address_city: Optional[str] = None
    address_province: Optional[str] = None
    is_mock: bool = False


class ParsedReceiptData(BaseModel):
    """Dati scontrino parsato con store e normalizzazione"""
    # Store info
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    company_name: Optional[str] = None
    vat_number: Optional[str] = None
    store_address: Optional[str] = None
    store_data: Optional[dict] = None  # Oggetto store completo
    
    # Receipt info
    receipt_date: Optional[str] = None
    receipt_time: Optional[str] = None
    total_amount: Optional[float] = None
    payment_method: Optional[str] = None
    discount_amount: Optional[float] = None
    
    # Items con normalizzazione
    items: List[ReceiptItemData] = []


class ProcessReceiptResponse(BaseModel):
    """Response processamento scontrino"""
    success: bool
    receipt_id: Optional[str] = None
    parsed_data: Optional[ParsedReceiptData] = None
    ocr_confidence: Optional[float] = None
    error: Optional[str] = None
    message: Optional[str] = None


# ===================================
# UPDATE REVIEW SCHEMAS
# ===================================

class UpdateProductReviewRequest(BaseModel):
    """Request per aggiornare prodotto dopo review utente"""
    # Dati corretti dall'utente
    canonical_name: str
    brand: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    size: Optional[str] = None
    unit_type: Optional[str] = None


class UpdateProductReviewResponse(BaseModel):
    """Response update review"""
    success: bool
    message: Optional[str] = None
    normalized_product_id: Optional[str] = None


# ===================================
# ALTRI SCHEMAS (già esistenti, mantenere)
# ===================================

class ReceiptResponse(BaseModel):
    """Response singolo receipt"""
    id: str
    household_id: str
    uploaded_by: str
    image_url: str
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    receipt_date: Optional[str] = None
    receipt_time: Optional[str] = None
    total_amount: Optional[float] = None
    payment_method: Optional[str] = None
    processing_status: str
    ocr_confidence: Optional[float] = None
    created_at: str
    updated_at: str
    items: List[dict] = []


class ReceiptListResponse(BaseModel):
    """Response lista receipts"""
    receipts: List[ReceiptResponse]
    total: int
    page: int
    page_size: int