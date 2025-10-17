"""
Pydantic schemas per Receipt API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, time, datetime
from decimal import Decimal


# ===================================
# REQUEST SCHEMAS
# ===================================

class ProcessReceiptRequest(BaseModel):
    """Request per processare uno scontrino"""
    household_id: str = Field(..., description="ID household")
    uploaded_by: str = Field(..., description="ID utente che carica")
    image_url: str = Field(..., description="URL immagine scontrino")

    class Config:
        json_schema_extra = {
            "example": {
                "household_id": "123e4567-e89b-12d3-a456-426614174000",
                "uploaded_by": "123e4567-e89b-12d3-a456-426614174001",
                "image_url": "https://storage.supabase.co/..."
            }
        }


# ===================================
# RESPONSE SCHEMAS
# ===================================

class ReceiptItemData(BaseModel):
    """Dati di un item parsato"""
    raw_product_name: str
    quantity: float = 1.0
    unit_price: float = 0.0
    total_price: float = 0.0
    category: Optional[str] = None

class ParsedReceiptData(BaseModel):
    """Dati parsati dallo scontrino"""
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    receipt_date: Optional[str] = None
    receipt_time: Optional[str] = None
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    payment_method: Optional[str] = None
    items: List[ReceiptItemData] = []

class ProcessReceiptResponse(BaseModel):
    """Response dopo processing scontrino"""
    success: bool
    receipt_id: Optional[str] = None
    message: Optional[str] = None
    parsed_data: Optional[ParsedReceiptData] = None
    ocr_confidence: Optional[float] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "receipt_id": "123e4567-e89b-12d3-a456-426614174002",
                "message": "Scontrino processato con successo",
                "ocr_confidence": 0.95,
                "parsed_data": {
                    "store_name": "Esselunga",
                    "total_amount": 45.20,
                    "items": []
                }
            }
        }


class ReceiptItemResponse(BaseModel):
    """Schema per item scontrino"""
    id: str
    receipt_id: str
    raw_product_name: str
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    total_price: Decimal
    line_number: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReceiptResponse(BaseModel):
    """Schema per scontrino"""
    id: str
    household_id: str
    uploaded_by: Optional[str] = None
    image_url: str
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    receipt_date: Optional[date] = None
    receipt_time: Optional[time] = None
    total_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    discount_amount: Optional[Decimal] = None
    raw_ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    processing_status: str
    created_at: datetime
    updated_at: datetime
    
    # Items opzionali (quando richiesti)
    items: Optional[List[ReceiptItemResponse]] = None

    class Config:
        from_attributes = True


class ReceiptListResponse(BaseModel):
    """Response per lista scontrini"""
    receipts: List[ReceiptResponse]
    total: int
    page: int = 1
    page_size: int = 50

    class Config:
        json_schema_extra = {
            "example": {
                "receipts": [],
                "total": 0,
                "page": 1,
                "page_size": 50
            }
        }