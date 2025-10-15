"""
Function Tools per Product Normalizer Agent
L'agente OpenAI può chiamare queste funzioni per:
- Cercare prodotti online
- Trovare prodotti normalizzati esistenti
- Creare nuovi prodotti normalizzati
"""
import requests
import json
from typing import Dict, List, Optional
from app.services.supabase_service import supabase_service
from app.config import settings


# ===================================
# TOOL 1: WEB SEARCH
# ===================================

def search_product_online(query: str, max_results: int = 3) -> Dict:
    """
    Cerca informazioni su un prodotto online
    
    Args:
        query: Nome prodotto da cercare
        max_results: Numero massimo risultati
        
    Returns:
        Dict con risultati search
    """
    try:
        # Opzione A: Usa Serper API (se configurata)
        if settings.SERPER_API_KEY:
            return _search_with_serper(query, max_results)
        
        # Opzione B: Usa DuckDuckGo (free, no API key)
        return _search_with_duckduckgo(query, max_results)
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Search error: {str(e)}",
            "results": []
        }


def _search_with_serper(query: str, max_results: int) -> Dict:
    """Cerca con Serper API (richiede API key)"""
    url = "https://google.serper.dev/search"
    
    payload = json.dumps({
        "q": query,
        "num": max_results
    })
    
    headers = {
        'X-API-KEY': settings.SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, data=payload, timeout=5)
    data = response.json()
    
    results = []
    for item in data.get("organic", [])[:max_results]:
        results.append({
            "title": item.get("title"),
            "snippet": item.get("snippet"),
            "link": item.get("link")
        })
    
    return {
        "success": True,
        "query": query,
        "results": results
    }


def _search_with_duckduckgo(query: str, max_results: int) -> Dict:
    """
    Cerca con DuckDuckGo (free, no API key)
    Usa l'API istantanea di DuckDuckGo
    """
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        results = []
        
        # Abstract (descrizione principale)
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", query),
                "snippet": data.get("Abstract"),
                "link": data.get("AbstractURL", "")
            })
        
        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "snippet": topic.get("Text", ""),
                    "link": topic.get("FirstURL", "")
                })
        
        return {
            "success": True,
            "query": query,
            "results": results[:max_results]
        }
        
    except Exception as e:
        # Fallback: crea risultato "mock" per continuare
        return {
            "success": False,
            "query": query,
            "results": [],
            "note": "Search unavailable, proceeding with basic info"
        }


# ===================================
# TOOL 2: FIND EXISTING PRODUCT
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
                "product": results[0],  # Primo risultato più simile
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
# TOOL 3: CREATE NORMALIZED PRODUCT
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
        brand: Brand (es. "Coca-Cola")
        category: Categoria (es. "Bevande > Bibite Gassate")
        subcategory: Sottocategoria
        size: Dimensione (es. "1.5L")
        unit_type: Tipo unità (es. "litri", "kg")
        tags: Tag (es. ["bibita", "gassata"])
        
    Returns:
        Dict con prodotto creato
    """
    try:
        data = {
            "canonical_name": canonical_name,
            "brand": brand,
            "category": category,
            "subcategory": subcategory,
            "size": size,
            "unit_type": unit_type,
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
# TOOL 4: CREATE PRODUCT MAPPING
# ===================================

def create_product_mapping(
    raw_name: str,
    normalized_product_id: str,
    store_name: Optional[str] = None,
    confidence_score: float = 0.9
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

# Queste sono le definizioni che OpenAI usa per capire come chiamare le funzioni
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_product_online",
            "description": "Cerca informazioni su un prodotto online quando non lo riconosci. Usa questo per prodotti sconosciuti o per verificare informazioni.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Nome prodotto da cercare (es. 'Coca-Cola caratteristiche', 'Barilla pasta ingredienti')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Numero massimo risultati (default: 3)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
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
                        "description": "Nome prodotto normalizzato da cercare (es. 'Coca-Cola Regular 1.5L')"
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
            "description": "Crea un nuovo prodotto normalizzato nel database. Usa SOLO se find_existing_product non lo trova.",
            "parameters": {
                "type": "object",
                "properties": {
                    "canonical_name": {
                        "type": "string",
                        "description": "Nome canonico normalizzato (es. 'Coca-Cola Regular 1.5L')"
                    },
                    "brand": {
                        "type": "string",
                        "description": "Brand del prodotto (es. 'Coca-Cola', 'Barilla')"
                    },
                    "category": {
                        "type": "string",
                        "description": "Categoria principale (es. 'Bevande > Bibite Gassate', 'Alimentari > Pasta')"
                    },
                    "subcategory": {
                        "type": "string",
                        "description": "Sottocategoria specifica (opzionale)"
                    },
                    "size": {
                        "type": "string",
                        "description": "Dimensione/quantità (es. '1.5L', '500g', '1kg')"
                    },
                    "unit_type": {
                        "type": "string",
                        "description": "Tipo unità (es. 'litri', 'grammi', 'chilogrammi', 'pezzi')"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tag descrittivi (es. ['bibita', 'gassata', 'zuccherata'])"
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
        "search_product_online": search_product_online,
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
