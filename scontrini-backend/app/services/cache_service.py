"""
Cache Service - Smart Cache 2-Tier con Confidence Boost
Interroga product_cache_stats via RPC e calcola confidence score
"""
from typing import Dict, Optional
from app.services.supabase_service import supabase_service


class CacheService:
    """Servizio di cache intelligente a 2 tier"""

    def __init__(self):
        """Inizializza configurazioni da settings"""
        from app.config import settings

        # Configurazione confidence
        self.CACHE_BASE_CONFIDENCE = settings.CACHE_BASE_CONFIDENCE
        self.PRICE_TOLERANCE = settings.CACHE_PRICE_TOLERANCE

        # Thresholds per boost
        self.MIN_HOUSEHOLDS_FOR_BOOST = settings.CACHE_MIN_HOUSEHOLDS_BOOST
        self.MIN_USAGE_FOR_BOOST = settings.CACHE_MIN_USAGE_BOOST
        self.RECENT_DAYS_THRESHOLD = settings.CACHE_RECENT_DAYS_THRESHOLD

        # Boost increments
        self.BOOST_HOUSEHOLDS = settings.CACHE_BOOST_HOUSEHOLDS
        self.BOOST_USAGE = settings.CACHE_BOOST_USAGE
        self.BOOST_RECENCY = settings.CACHE_BOOST_RECENCY

        # Max confidence
        self.MAX_CONFIDENCE = settings.CACHE_MAX_CONFIDENCE

        # Tier 2
        self.TIER2_PENALTY = settings.CACHE_TIER2_PENALTY
        self.TIER2_MIN_CONFIDENCE = settings.CACHE_TIER2_MIN_CONFIDENCE

    def get_cached_product(
        self,
        raw_name: str,
        store_name: Optional[str],
        current_price: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Cerca prodotto in cache (Tier 1: verified, Tier 2: auto-verified fallback)

        Args:
            raw_name: Nome grezzo dallo scontrino
            store_name: Nome negozio (opzionale)
            current_price: Prezzo corrente per price coherence check

        Returns:
            Dict con cache hit oppure None se miss
        """
        # TIER 1: Query product_cache_stats (verified by user)
        print(f"   [CACHE] Tier 1 lookup: '{raw_name}' @ {store_name}")
        cache_result = self._query_cache_tier1(raw_name, store_name, current_price)

        if cache_result:
            # Calculate confidence boost
            confidence = self._calculate_confidence_boost(cache_result)

            # Check price coherence
            if not cache_result.get('price_coherent', True):
                # Price anomalo: downgrade confidence
                confidence = max(0.70, confidence - 0.20)

            # Fetch product data
            product_data = self._fetch_product_data(cache_result['product_id'])

            result = {
                'product_id': cache_result['product_id'],
                'confidence': confidence,
                'price_coherent': cache_result.get('price_coherent', True),
                'usage_count': cache_result.get('usage_count', 0),
                'verified_by_households': cache_result.get('verified_by_households', 0),
                'tier': 'cache_tier1',
                'from_cache': True
            }

            # Merge product data
            if product_data:
                result.update(product_data)

            print(f"   [CACHE] ✅ Tier 1 HIT: '{result.get('canonical_name')}' (conf: {confidence:.2f}, usage: {cache_result.get('usage_count', 0)})")
            return result

        # TIER 2: Fallback su auto-verified mappings (non ancora in cache stats)
        print(f"   [CACHE] Tier 1 MISS, trying Tier 2...")
        tier2_result = self._query_cache_tier2(raw_name, store_name)

        if tier2_result:
            # Tier 2 ha penalty
            confidence = max(0.70, self.CACHE_BASE_CONFIDENCE - self.TIER2_PENALTY)

            # Fetch product data
            product_data = self._fetch_product_data(tier2_result['normalized_product_id'])

            result = {
                'product_id': tier2_result['normalized_product_id'],
                'confidence': confidence,
                'price_coherent': True,  # No price history per Tier 2
                'usage_count': 0,
                'verified_by_households': 0,
                'tier': 'cache_tier2',
                'from_cache': True
            }

            # Merge product data
            if product_data:
                result.update(product_data)

            print(f"   [CACHE] ✅ Tier 2 HIT: '{result.get('canonical_name')}' (conf: {confidence:.2f})")
            return result

        # Cache miss
        print(f"   [CACHE] ❌ MISS (both tiers)")
        return None

    def _query_cache_tier1(
        self,
        raw_name: str,
        store_name: Optional[str],
        current_price: Optional[float]
    ) -> Optional[Dict]:
        """
        Query Tier 1: product_cache_stats (verified by user)
        Via RPC call a get_cached_product()
        """
        try:
            response = supabase_service.client.rpc(
                'get_cached_product',
                {
                    'p_raw_name': raw_name,
                    'p_store_name': store_name,
                    'p_current_price': current_price
                }
            ).execute()

            if response.data:
                return response.data

            return None

        except Exception as e:
            print(f"Error querying cache tier 1: {str(e)}")
            return None

    def _query_cache_tier2(
        self,
        raw_name: str,
        store_name: Optional[str]
    ) -> Optional[Dict]:
        """
        Query Tier 2: product_mappings con confidence >= 0.85
        Fallback quando Tier 1 non trova nulla
        """
        try:
            query = supabase_service.client.table("product_mappings")\
                .select("normalized_product_id, confidence_score")\
                .eq("raw_name", raw_name)\
                .eq("verified_by_user", False)\
                .gte("confidence_score", self.TIER2_MIN_CONFIDENCE)\
                .order("confidence_score", desc=True)\
                .limit(1)

            if store_name:
                query = query.eq("store_name", store_name)

            response = query.execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            print(f"Error querying cache tier 2: {str(e)}")
            return None

    def _fetch_product_data(self, product_id: str) -> Optional[Dict]:
        """
        Fetch dati completi del prodotto normalizzato

        Args:
            product_id: ID del prodotto normalizzato

        Returns:
            Dict con dati del prodotto o None se non trovato
        """
        try:
            response = supabase_service.client.table("normalized_products")\
                .select("canonical_name, brand, category, subcategory, size, unit_type")\
                .eq("id", product_id)\
                .single()\
                .execute()

            if response.data:
                return response.data

            return None

        except Exception as e:
            print(f"Error fetching product data for {product_id}: {str(e)}")
            return None

    def _calculate_confidence_boost(self, cache_result: Dict) -> float:
        """
        Calcola confidence boost basato su usage stats

        Base: 0.90
        +0.03 se verified_by_households >= 3
        +0.02 se usage_count >= 10
        +0.02 se last_used < 90 giorni
        Max: 0.97
        """
        confidence = self.CACHE_BASE_CONFIDENCE

        # Boost 1: Multiple households verified
        verified_households = cache_result.get('verified_by_households', 0)
        if verified_households >= self.MIN_HOUSEHOLDS_FOR_BOOST:
            confidence += self.BOOST_HOUSEHOLDS

        # Boost 2: High usage count
        usage_count = cache_result.get('usage_count', 0)
        if usage_count >= self.MIN_USAGE_FOR_BOOST:
            confidence += self.BOOST_USAGE

        # Boost 3: Recently used
        last_used = cache_result.get('last_used')
        if last_used:
            from datetime import datetime, timedelta
            if isinstance(last_used, str):
                last_used_date = datetime.fromisoformat(last_used.replace('Z', '+00:00')).date()
            else:
                last_used_date = last_used

            days_since_last_use = (datetime.now().date() - last_used_date).days
            if days_since_last_use <= self.RECENT_DAYS_THRESHOLD:
                confidence += self.BOOST_RECENCY

        # Cap at max confidence
        return min(confidence, self.MAX_CONFIDENCE)


# Instanza globale
cache_service = CacheService()
