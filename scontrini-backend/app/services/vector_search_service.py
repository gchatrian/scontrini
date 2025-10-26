"""
Vector Search Service - Semantic similarity search using pgvector
"""
from typing import List, Dict, Any, Optional
from supabase import Client
from app.services.embedding_service import EmbeddingService
from app.config import settings


class VectorSearchService:
    """Servizio per ricerca semantica usando embeddings vettoriali"""

    def __init__(self, supabase_client: Client, embedding_service: EmbeddingService):
        self.supabase = supabase_client
        self.embedding_service = embedding_service

        # Configurazione dalla config centralizzata
        self.max_results = settings.VECTOR_SEARCH_MAX_RESULTS
        self.similarity_threshold = settings.VECTOR_SEARCH_SIMILARITY_THRESHOLD
        self.boost_verified = settings.VECTOR_SEARCH_BOOST_VERIFIED
        self.boost_same_store = settings.VECTOR_SEARCH_BOOST_SAME_STORE

    async def search_similar_products(
        self,
        raw_name: str,
        store_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Cerca prodotti simili usando vector search

        Args:
            raw_name: Nome prodotto grezzo da cercare
            store_name: Nome negozio (opzionale, per context boosting)
            limit: Numero massimo risultati (default da config)

        Returns:
            Lista di prodotti con similarity score e metadata
            [
                {
                    "product_id": "uuid",
                    "canonical_name": "Coca Cola 1.5L",
                    "brand": "Coca Cola",
                    "category": "Bevande",
                    "similarity_score": 0.92,
                    "verified_by_user": true,
                    "store_context_match": true
                },
                ...
            ]
        """
        # Genera embedding per il testo di ricerca
        query_embedding = await self.embedding_service.generate_embedding(raw_name)

        # Usa limit configurato se non specificato
        search_limit = limit if limit is not None else self.max_results

        # Chiama RPC function per vector search
        response = self.supabase.rpc(
            'search_similar_products',
            {
                'query_embedding': query_embedding,
                'match_threshold': self.similarity_threshold,
                'match_count': search_limit
            }
        ).execute()

        if not response.data:
            return []

        # Arricchisci risultati con boosting basato su contesto
        results = []
        for product in response.data:
            # Calcola similarity score con boost
            base_similarity = product.get('similarity', 0.0)
            boosted_score = self._calculate_boosted_similarity(
                base_similarity=base_similarity,
                is_verified=product.get('verified_by_user', False),
                product_store=product.get('store_context'),
                query_store=store_name
            )

            results.append({
                'product_id': product['id'],
                'canonical_name': product['canonical_name'],
                'brand': product.get('brand'),
                'category': product.get('category'),
                'subcategory': product.get('subcategory'),
                'size': product.get('size'),
                'unit_type': product.get('unit_type'),
                'similarity_score': boosted_score,
                'base_similarity': base_similarity,
                'verified_by_user': product.get('verified_by_user', False),
                'store_context_match': product.get('store_context') == store_name if store_name else False,
                'verification_status': product.get('verification_status'),
                'tags': product.get('tags', [])
            })

        # Riordina per similarity boosted
        results.sort(key=lambda x: x['similarity_score'], reverse=True)

        return results

    async def search_batch(
        self,
        raw_names: List[str],
        store_name: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Cerca prodotti simili per lista di nomi (batch processing)

        Args:
            raw_names: Lista di nomi prodotti grezzi
            store_name: Nome negozio per context boosting

        Returns:
            Dict con raw_name come chiave e lista risultati come valore
            {
                "COCA 1.5L": [{product}, {product}, ...],
                "PANE INTEGR": [{product}, {product}, ...],
                ...
            }
        """
        # Genera embeddings in batch
        embeddings = await self.embedding_service.generate_batch(raw_names)

        # Cerca per ogni embedding
        results = {}
        for raw_name, embedding in zip(raw_names, embeddings):
            # Per batch search usiamo la RPC function direttamente
            response = self.supabase.rpc(
                'search_similar_products',
                {
                    'query_embedding': embedding,
                    'match_threshold': self.similarity_threshold,
                    'match_count': self.max_results
                }
            ).execute()

            products = []
            if response.data:
                for product in response.data:
                    base_similarity = product.get('similarity', 0.0)
                    boosted_score = self._calculate_boosted_similarity(
                        base_similarity=base_similarity,
                        is_verified=product.get('verified_by_user', False),
                        product_store=product.get('store_context'),
                        query_store=store_name
                    )

                    products.append({
                        'product_id': product['id'],
                        'canonical_name': product['canonical_name'],
                        'brand': product.get('brand'),
                        'category': product.get('category'),
                        'similarity_score': boosted_score,
                        'base_similarity': base_similarity,
                        'verified_by_user': product.get('verified_by_user', False),
                        'store_context_match': product.get('store_context') == store_name if store_name else False
                    })

                products.sort(key=lambda x: x['similarity_score'], reverse=True)

            results[raw_name] = products

        return results

    def _calculate_boosted_similarity(
        self,
        base_similarity: float,
        is_verified: bool,
        product_store: Optional[str],
        query_store: Optional[str]
    ) -> float:
        """
        Calcola similarity score con boosting basato su contesto

        Args:
            base_similarity: Score base da vector search
            is_verified: Se il prodotto è verificato da utente
            product_store: Negozio associato al prodotto nel DB
            query_store: Negozio dello scontrino corrente

        Returns:
            Similarity score con boost applicato (max 1.0)
        """
        score = base_similarity

        # Boost per prodotti verificati da utenti
        if is_verified:
            score += self.boost_verified

        # Boost per stesso contesto negozio
        if query_store and product_store == query_store:
            score += self.boost_same_store

        # Cap a 1.0
        return min(score, 1.0)

    def get_service_stats(self) -> Dict[str, Any]:
        """
        Restituisce statistiche del servizio

        Returns:
            Dict con stats embedding service e configurazione
        """
        embedding_stats = self.embedding_service.get_usage_stats()

        return {
            'embedding_stats': embedding_stats,
            'config': {
                'max_results': self.max_results,
                'similarity_threshold': self.similarity_threshold,
                'boost_verified': self.boost_verified,
                'boost_same_store': self.boost_same_store
            }
        }
