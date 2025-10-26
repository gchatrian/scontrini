"""
Context Service - Arricchimento dati con contesto household e store
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from supabase import Client
from app.config import settings


class ContextService:
    """Servizio per arricchire dati prodotto con contesto storico"""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

        # Configurazione dalla config centralizzata
        self.recent_days = settings.CONTEXT_RECENT_PURCHASES_DAYS
        self.min_frequency = settings.CONTEXT_MIN_FREQUENCY_THRESHOLD
        self.popular_min_households = settings.CONTEXT_POPULAR_MIN_HOUSEHOLDS

    async def get_household_context(
        self,
        household_id: str,
        normalized_product_id: str
    ) -> Dict[str, Any]:
        """
        Recupera contesto storico prodotto per household

        Args:
            household_id: ID household
            normalized_product_id: ID prodotto normalizzato

        Returns:
            {
                "has_history": bool,
                "purchase_count": int,
                "last_purchase_date": str | None,
                "avg_price": float | None,
                "typical_stores": [str],
                "is_frequent": bool
            }
        """
        # Query purchase history per household e prodotto
        response = self.supabase.table('purchase_history') \
            .select('purchase_date, unit_price, store_name') \
            .eq('household_id', household_id) \
            .eq('normalized_product_id', normalized_product_id) \
            .order('purchase_date', desc=True) \
            .execute()

        if not response.data:
            return {
                'has_history': False,
                'purchase_count': 0,
                'last_purchase_date': None,
                'avg_price': None,
                'typical_stores': [],
                'is_frequent': False
            }

        purchases = response.data
        purchase_count = len(purchases)

        # Calcola statistiche
        prices = [p['unit_price'] for p in purchases if p.get('unit_price')]
        avg_price = sum(prices) / len(prices) if prices else None

        # Trova negozi tipici (più frequenti)
        store_counts = {}
        for p in purchases:
            store = p.get('store_name')
            if store:
                store_counts[store] = store_counts.get(store, 0) + 1

        typical_stores = sorted(
            store_counts.keys(),
            key=lambda s: store_counts[s],
            reverse=True
        )[:3]  # Top 3 negozi

        # Determina se è acquisto frequente
        recent_cutoff = datetime.now() - timedelta(days=self.recent_days)
        recent_purchases = [
            p for p in purchases
            if datetime.fromisoformat(p['purchase_date'].replace('Z', '+00:00')) > recent_cutoff
        ]
        is_frequent = len(recent_purchases) >= self.min_frequency

        return {
            'has_history': True,
            'purchase_count': purchase_count,
            'last_purchase_date': purchases[0]['purchase_date'],
            'avg_price': avg_price,
            'typical_stores': typical_stores,
            'is_frequent': is_frequent
        }

    async def get_store_popularity(
        self,
        store_name: str,
        normalized_product_id: str
    ) -> Dict[str, Any]:
        """
        Recupera popolarità prodotto in un negozio specifico

        Args:
            store_name: Nome negozio
            normalized_product_id: ID prodotto normalizzato

        Returns:
            {
                "is_popular": bool,
                "household_count": int,
                "total_purchases": int,
                "avg_price": float | None
            }
        """
        # Query purchase history per negozio e prodotto
        response = self.supabase.table('purchase_history') \
            .select('household_id, unit_price') \
            .eq('store_name', store_name) \
            .eq('normalized_product_id', normalized_product_id) \
            .execute()

        if not response.data:
            return {
                'is_popular': False,
                'household_count': 0,
                'total_purchases': 0,
                'avg_price': None
            }

        purchases = response.data
        unique_households = len(set(p['household_id'] for p in purchases))
        total_purchases = len(purchases)

        prices = [p['unit_price'] for p in purchases if p.get('unit_price')]
        avg_price = sum(prices) / len(prices) if prices else None

        is_popular = unique_households >= self.popular_min_households

        return {
            'is_popular': is_popular,
            'household_count': unique_households,
            'total_purchases': total_purchases,
            'avg_price': avg_price
        }

    async def get_enriched_context(
        self,
        household_id: str,
        normalized_product_id: str,
        store_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recupera contesto completo (household + store)

        Args:
            household_id: ID household
            normalized_product_id: ID prodotto normalizzato
            store_name: Nome negozio (opzionale)

        Returns:
            {
                "household": {...},
                "store": {...} | None,
                "context_score": float  # 0-1 quanto contesto abbiamo
            }
        """
        # Recupera contesto household
        household_ctx = await self.get_household_context(
            household_id=household_id,
            normalized_product_id=normalized_product_id
        )

        # Recupera contesto store se disponibile
        store_ctx = None
        if store_name:
            store_ctx = await self.get_store_popularity(
                store_name=store_name,
                normalized_product_id=normalized_product_id
            )

        # Calcola context score
        context_score = self._calculate_context_score(
            household_ctx=household_ctx,
            store_ctx=store_ctx
        )

        return {
            'household': household_ctx,
            'store': store_ctx,
            'context_score': context_score
        }

    async def get_batch_context(
        self,
        household_id: str,
        product_ids: List[str],
        store_name: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Recupera contesto per lista di prodotti (batch processing)

        Args:
            household_id: ID household
            product_ids: Lista di ID prodotti normalizzati
            store_name: Nome negozio (opzionale)

        Returns:
            Dict con product_id come chiave e contesto come valore
            {
                "product-uuid-1": {household: {...}, store: {...}, context_score: 0.8},
                "product-uuid-2": {household: {...}, store: {...}, context_score: 0.3},
                ...
            }
        """
        results = {}

        for product_id in product_ids:
            context = await self.get_enriched_context(
                household_id=household_id,
                normalized_product_id=product_id,
                store_name=store_name
            )
            results[product_id] = context

        return results

    def _calculate_context_score(
        self,
        household_ctx: Dict[str, Any],
        store_ctx: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calcola context score basato su disponibilità dati

        Args:
            household_ctx: Contesto household
            store_ctx: Contesto store (opzionale)

        Returns:
            Score 0-1 (1 = molto contesto, 0 = nessun contesto)
        """
        score = 0.0

        # Componente household (60% del peso)
        if household_ctx['has_history']:
            score += 0.3  # Base per storia esistente

            if household_ctx['is_frequent']:
                score += 0.2  # Acquisto frequente

            if household_ctx['purchase_count'] >= 5:
                score += 0.1  # Molti acquisti

        # Componente store (40% del peso)
        if store_ctx:
            if store_ctx['is_popular']:
                score += 0.2  # Popolare nel negozio

            if store_ctx['household_count'] >= 2:
                score += 0.1  # Usato da più household

            if store_ctx['total_purchases'] >= 10:
                score += 0.1  # Molti acquisti totali

        return min(score, 1.0)

    async def get_price_history(
        self,
        household_id: str,
        normalized_product_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recupera storico prezzi prodotto per household

        Args:
            household_id: ID household
            normalized_product_id: ID prodotto normalizzato
            limit: Numero massimo risultati

        Returns:
            Lista di acquisti con prezzi
            [
                {
                    "purchase_date": "2024-01-15",
                    "store_name": "Esselunga",
                    "unit_price": 1.49,
                    "quantity": 2
                },
                ...
            ]
        """
        response = self.supabase.table('purchase_history') \
            .select('purchase_date, store_name, unit_price, quantity') \
            .eq('household_id', household_id) \
            .eq('normalized_product_id', normalized_product_id) \
            .order('purchase_date', desc=True) \
            .limit(limit) \
            .execute()

        if not response.data:
            return []

        return [
            {
                'purchase_date': p['purchase_date'],
                'store_name': p.get('store_name'),
                'unit_price': p.get('unit_price'),
                'quantity': p.get('quantity')
            }
            for p in response.data
        ]
