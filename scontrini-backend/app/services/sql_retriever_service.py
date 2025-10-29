"""
SQL Retriever Service - Ricerca ibrida FTS + Fuzzy Matching
Wrapper per RPC function search_products_hybrid()
"""
from typing import List, Dict, Any, Optional
from app.services.supabase_service import supabase_service
from app.config import settings


class SQLRetrieverService:
    """Servizio per ricerca prodotti via SQL (FTS + Fuzzy)"""

    def __init__(self):
        self.supabase = supabase_service.client

    def search_products(
        self,
        hypothesis: str,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        size: Optional[float] = None,
        unit_type: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Cerca prodotti usando ricerca ibrida SQL

        Args:
            hypothesis: Testo interpretato da LLM (es. "acqua frizzante sant anna")
            brand: Brand identificato (opzionale per filtro hard)
            category: Categoria identificata
            size: Quantità (per filtro ±15%)
            unit_type: Unità di misura
            top_k: Numero candidati da ritornare (default da config)

        Returns:
            Lista prodotti con score FTS, fuzzy, combined
            [
                {
                    "product_id": "uuid",
                    "canonical_name": "Acqua Frizzante Sant'Anna 1.5L",
                    "brand": "SANT'ANNA",
                    "category": "ACQUA",
                    "subcategory": "acqua minerale",
                    "size": "1500",
                    "unit_type": "ml",
                    "tags": ["acqua", "frizzante"],
                    "fts_score": 0.8,
                    "fuzzy_score": 0.7,
                    "combined_score": 0.9
                },
                ...
            ]
        """
        # Usa top_k da config se non specificato
        if top_k is None:
            top_k = settings.SQL_RETRIEVER_TOP_K

        try:
            print(f"   [SQL] Calling RPC with: hypothesis='{hypothesis}', brand={brand}, category={category}, size={size}, unit={unit_type}")
            response = self.supabase.rpc(
                'search_products_hybrid',
                {
                    'p_hypothesis': hypothesis,
                    'p_brand': brand,
                    'p_category': category,
                    'p_size': size,
                    'p_unit_type': unit_type,
                    'p_size_tolerance': settings.SQL_RETRIEVER_SIZE_TOLERANCE,
                    'p_match_count': top_k,
                    'p_fts_threshold': settings.SQL_RETRIEVER_FTS_THRESHOLD,
                    'p_trigram_threshold': settings.SQL_RETRIEVER_TRIGRAM_THRESHOLD
                }
            ).execute()

            if not response.data:
                print(f"   [SQL] No results for hypothesis: '{hypothesis}'")
                return []

            # Formatta risultati
            results = []
            for product in response.data:
                results.append({
                    'product_id': product['id'],
                    'canonical_name': product['canonical_name'],
                    'brand': product.get('brand'),
                    'category': product.get('category'),
                    'subcategory': product.get('subcategory'),
                    'size': str(product.get('size')) if product.get('size') else None,
                    'unit_type': product.get('unit_type'),
                    'tags': product.get('tags', []),
                    'fts_score': product.get('fts_score', 0.0),
                    'fuzzy_score': product.get('fuzzy_score', 0.0),
                    'combined_score': product.get('combined_score', 0.0)
                })

            print(f"   [SQL] Found {len(results)} candidates (top score: {results[0]['combined_score']:.3f})")
            return results

        except Exception as e:
            print(f"❌ SQL Retriever error: {str(e)}")
            return []


# Instanza globale
sql_retriever_service = SQLRetrieverService()
