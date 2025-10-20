"""
Function Tools per Product Normalizer Agent
L'agente OpenAI può chiamare queste funzioni per:
- Trovare prodotti normalizzati esistenti
- Creare nuovi prodotti normalizzati
"""
import json
from typing import Dict, List, Optional
from app.services.supabase_service import supabase_service
from app.utils.size_parser import clean_size_field, get_unit_from_size


# ===================================
# TOOL: FIND EXISTING PRODUCT
# ===================================

def find_existing_product(product_name: str) -> Dict:
    """
    Cerca prodotto normalizzato esistente nel database
    
    Args:
        product_name: Nome prodotto da cercare
        
    Returns:
        Dict con prodotto trovato o None
    """
    try:
        # Cerca per nome esatto
        results = supabase_service.client.table("normalized_products")\
            .select("*")\
            .eq("canonical_name", product_name)\
            .execute()
        
        if results.data:
            return {
                "success": True,
                "found": True,
                "product": results.data[0]
            }
        
        # Cerca per similarità (fuzzy search)
        results = supabase_service.search_normalized_products(
            product_name, 
            limit=5
        )
        
        if results:
            return {
                "success": True,
                "found": True,
                "product": results[0],
                "note": "Found by similarity"
            }
        
        return {
            "success": True,
            "found": False,
            "product": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Database error: {str(e)}",
            "found": False
        }


# ===================================
# TOOL: CREATE NORMALIZED PRODUCT
# ===================================

def create_normalized_product(
    canonical_name: str,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    size: Optional[str] = None,
    unit_type: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Dict:
    """
    Crea nuovo prodotto normalizzato
    
    Args:
        canonical_name: Nome canonico normalizzato
        brand: Brand del prodotto
        category: Categoria principale
        subcategory: Sottocategoria
        size: Dimensione/quantità
        unit_type: Tipo unità di misura
        tags: Tag descrittivi
        
    Returns:
        Dict con prodotto creato
    """
    try:
        # Guardia anti-duplicati lato server: prima di creare, tenta riuso
        try:
            existing = supabase_service.client.table("normalized_products")\
                .select("*")\
                .eq("canonical_name", canonical_name)\
                .execute()
            if existing.data:
                return {"success": True, "product": existing.data[0], "note": "Reused existing (exact match)"}
        except Exception:
            pass
        # second best: similarità
        try:
            similar = supabase_service.search_normalized_products(canonical_name, limit=1)
            if similar:
                return {"success": True, "product": similar[0], "note": "Reused existing (similar)"}
        except Exception:
            pass
        # Processa il campo size per separare quantità e unità
        clean_size = clean_size_field(size) if size else None
        extracted_unit = get_unit_from_size(size) if size else unit_type
        
        data = {
            "canonical_name": canonical_name,
            "brand": brand,
            "category": category,
            "subcategory": subcategory,
            "size": clean_size,  # Solo la quantità numerica
            "unit_type": extracted_unit or unit_type,  # Unità di misura
            "tags": tags or []
        }
        
        response = supabase_service.client.table("normalized_products")\
            .insert(data)\
            .execute()
        
        if response.data:
            return {
                "success": True,
                "product": response.data[0]
            }
        
        return {
            "success": False,
            "error": "Failed to create product"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Database error: {str(e)}"
        }


# ===================================
# TOOL: CREATE PRODUCT MAPPING
# ===================================

def create_product_mapping(
    raw_name: str,
    normalized_product_id: str,
    store_name: Optional[str] = None,
    confidence_score: float = 0.9,
    requires_manual_review: Optional[bool] = None
) -> Dict:
    """
    Crea mapping tra nome grezzo e prodotto normalizzato
    
    Args:
        raw_name: Nome grezzo dallo scontrino
        normalized_product_id: ID prodotto normalizzato
        store_name: Nome negozio (opzionale)
        confidence_score: Confidenza (0-1)
        
    Returns:
        Dict con mapping creato
    """
    try:
        data = {
            "raw_name": raw_name,
            "normalized_product_id": normalized_product_id,
            "store_name": store_name,
            "confidence_score": confidence_score,
            "verified_by_user": False
        }
        if requires_manual_review is not None:
            data["requires_manual_review"] = requires_manual_review
        
        response = supabase_service.client.table("product_mappings")\
            .insert(data)\
            .execute()
        
        if response.data:
            return {
                "success": True,
                "mapping": response.data[0]
            }
        
        return {
            "success": False,
            "error": "Failed to create mapping"
        }
        
    except Exception as e:
        # Se mapping già esiste, va bene comunque
        if "duplicate key" in str(e).lower():
            return {
                "success": True,
                "note": "Mapping already exists"
            }
        
        return {
            "success": False,
            "error": f"Database error: {str(e)}"
        }


# ===================================
# TOOL DEFINITIONS per OpenAI
# ===================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "find_existing_product",
            "description": "Cerca se un prodotto normalizzato esiste già nel database. Usa sempre questo PRIMA di creare un nuovo prodotto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Nome prodotto normalizzato da cercare"
                    }
                },
                "required": ["product_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_normalized_product",
            "description": "Crea un nuovo prodotto normalizzato nel database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "canonical_name": {
                        "type": "string",
                        "description": "Nome canonico normalizzato del prodotto"
                    },
                    "brand": {
                        "type": "string",
                        "description": "Marca/brand del prodotto"
                    },
                    "category": {
                        "type": "string",
                        "description": "Categoria principale usando formato gerarchico"
                    },
                    "subcategory": {
                        "type": "string",
                        "description": "Sottocategoria specifica (opzionale)"
                    },
                    "size": {
                        "type": "string",
                        "description": "Solo la quantità numerica (es. 500, 1.5, 2)"
                    },
                    "unit_type": {
                        "type": "string",
                        "description": "Unità di misura (es. g, kg, L, ml)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tag descrittivi del prodotto"
                    }
                },
                "required": ["canonical_name", "category"]
            }
        }
    }
]


# ===================================
# FUNCTION DISPATCHER
# ===================================

def execute_function(function_name: str, arguments: Dict) -> Dict:
    """
    Esegue una funzione tool dato il nome e gli argomenti
    
    Args:
        function_name: Nome funzione da eseguire
        arguments: Dict con argomenti funzione
        
    Returns:
        Risultato esecuzione funzione
    """
    functions = {
        "find_existing_product": find_existing_product,
        "create_normalized_product": create_normalized_product
    }
    
    if function_name not in functions:
        return {
            "success": False,
            "error": f"Unknown function: {function_name}"
        }
    
    try:
        result = functions[function_name](**arguments)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Function execution error: {str(e)}"
        }
