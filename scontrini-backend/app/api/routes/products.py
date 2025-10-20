"""
Product Routes
Endpoints per gestione prodotti e categorizzazione
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.categorization_service import categorization_service


# Crea il router
router = APIRouter()


class CategorizeProductRequest(BaseModel):
    """Request per categorizzazione prodotto"""
    canonical_name: str
    brand: Optional[str] = None
    size: Optional[str] = None
    unit_type: Optional[str] = None


class CategorizeProductResponse(BaseModel):
    """Response con categoria e sottocategoria"""
    category: str
    subcategory: Optional[str] = None
    confidence: float


@router.post("/categorize", response_model=CategorizeProductResponse)
async def categorize_product(request: CategorizeProductRequest):
    """
    Categorizza un prodotto usando LLM.
    Usato dopo che l'utente modifica un prodotto.
    
    Args:
        request: Dati prodotto da categorizzare
        
    Returns:
        Categoria e sottocategoria suggerite
    """
    try:
        result = categorization_service.categorize_product(
            canonical_name=request.canonical_name,
            brand=request.brand,
            size=request.size,
            unit_type=request.unit_type
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Errore durante categorizzazione")
            )
        
        return CategorizeProductResponse(
            category=result["category"],
            subcategory=result.get("subcategory"),
            confidence=result.get("confidence", 0.8)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore imprevisto: {str(e)}"
        )