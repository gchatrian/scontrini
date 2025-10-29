"""
Product Normalizer - SQL-First Pipeline
Pipeline: Cache → LLM Interpret → SQL Search → Business Rerank → LLM Select → Validate
Note: Vector Search RIMOSSO - usa SQL FTS + Fuzzy Matching
"""
import asyncio
from typing import Dict, List, Optional, Any
from app.config import settings
from app.services.cache_service import CacheService
from app.services.llm_interpret_service import LLMInterpretService
from app.services.sql_retriever_service import SQLRetrieverService
from app.services.business_reranker_service import BusinessRerankerService
from app.services.llm_select_service import LLMSelectService
from app.services.llm_validate_service import LLMValidateService


class ProductNormalizerV2:
    """Agente per normalizzazione prodotti - SQL-first approach"""

    def __init__(self):
        """Inizializza servizi"""
        self.cache_service = CacheService()
        self.llm_interpret_service = LLMInterpretService()
        self.sql_retriever_service = SQLRetrieverService()
        self.business_reranker_service = BusinessRerankerService()
        self.llm_select_service = LLMSelectService()
        self.llm_validate_service = LLMValidateService()

    async def normalize_product(
        self,
        raw_product_name: str,
        household_id: str,
        store_name: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Normalizza singolo prodotto

        Pipeline:
        1. Cache Lookup (Tier 1 + Tier 2)
        2. LLM Interpret (espansione abbreviazioni + estrazione dati)
        3. SQL Hybrid Search (FTS + Fuzzy + filtri hard)
        4. Business Reranking (regole deterministiche)
        5. LLM Select (scelta best match)
        6. LLM Validate (confidence scoring)

        Returns:
            {
                "success": bool,
                "normalized_product_id": str,
                "canonical_name": str,
                "brand": str,
                "category": str,
                "confidence": float,
                "confidence_level": "high" | "medium" | "low",
                "source": "cache_tier1" | "cache_tier2" | "sql_search",
                "needs_review": bool
            }
        """
        try:
            print(f"🔎 [START] raw='{raw_product_name}'")

            # STEP 1: Cache Lookup
            cache_hit = self.cache_service.get_cached_product(
                raw_name=raw_product_name,
                store_name=store_name,
                current_price=price
            )

            if cache_hit:
                print(f"✅ [CACHE] {cache_hit.get('canonical_name')}")
                return self._format_cache_result(cache_hit)

            print("💭 [LLM INTERPRET]...")

            # STEP 2: LLM Interpret
            interpret_result = await self.llm_interpret_service.interpret_raw_name(
                raw_name=raw_product_name,
                store_name=store_name,
                price=price
            )

            if not interpret_result['success']:
                return {
                    "success": False,
                    "error": "LLM Interpret failed",
                    "canonical_name": raw_product_name,  # Usa raw name come fallback
                    "normalized_product_id": None,
                    "brand": None,
                    "category": None,
                    "subcategory": None,
                    "size": None,
                    "unit_type": None,
                    "tags": [],
                    "confidence": 0.0,
                    "confidence_level": "low",
                    "source": "error",
                    "needs_review": True
                }

            hypothesis = interpret_result['hypothesis']
            print(f"   → hypothesis: '{hypothesis}'")
            print(f"   → brand: {interpret_result.get('brand')}")
            print(f"   → category: {interpret_result.get('category')}")
            print(f"   → size: {interpret_result.get('size')} {interpret_result.get('unit_type')}")
            print(f"   → tags: {interpret_result.get('tags', [])}")

            # STEP 3: SQL Hybrid Search
            print("🔍 [SQL SEARCH]...")
            candidates = await asyncio.to_thread(
                self.sql_retriever_service.search_products,
                hypothesis=hypothesis,
                brand=interpret_result.get('brand'),
                category=interpret_result.get('category'),
                size=float(interpret_result.get('size')) if interpret_result.get('size') else None,
                unit_type=interpret_result.get('unit_type'),
                top_k=20
            )

            if not candidates:
                # No candidates: usa ipotesi come fallback
                print("⚠️ [NO CANDIDATES] using hypothesis as fallback")
                return self._format_hypothesis_fallback(interpret_result)

            print(f"   → found {len(candidates)} candidates")
            for i, c in enumerate(candidates[:3], 1):
                print(f"      {i}. {c.get('canonical_name')} (score: {c.get('combined_score', 0):.3f})")

            # STEP 4: Business Reranking
            print("📊 [BUSINESS RERANK]...")
            hypothesis_context = {
                'brand': interpret_result.get('brand'),
                'category': interpret_result.get('category'),
                'size': interpret_result.get('size'),
                'unit_type': interpret_result.get('unit_type'),
                'tags': interpret_result.get('tags', [])
            }
            reranked = self.business_reranker_service.rerank_candidates(
                candidates=candidates,
                hypothesis_context=hypothesis_context
            )

            if not reranked:
                # Tutti scartati da business rules
                print("⚠️ [NO CANDIDATES AFTER RERANK] using hypothesis as fallback")
                return self._format_hypothesis_fallback(interpret_result)

            print(f"   → {len(reranked)} candidates survived reranking")
            for i, c in enumerate(reranked[:3], 1):
                print(f"      {i}. {c.get('canonical_name')} (adjusted: {c.get('combined_score', 0):.3f})")

            # STEP 5: LLM Select (top 5 a LLM)
            print("✅ [LLM SELECT]...")
            select_result = await self.llm_select_service.select_best_match(
                raw_name=raw_product_name,
                hypothesis=hypothesis,
                candidates=reranked[:5]
            )

            if not select_result['success']:
                # Fallback: primo candidato
                selected_product = reranked[0]
                print(f"   → fallback to first candidate: '{selected_product['canonical_name']}'")
            else:
                selected_product = select_result['selected_product']
                print(f"   → selected: '{selected_product['canonical_name']}'")

            # STEP 6: LLM Validate
            print("📊 [LLM VALIDATE]...")
            validation = await self.llm_validate_service.validate_mapping(
                raw_name=raw_product_name,
                selected_product=selected_product,
                hypothesis=hypothesis
            )

            print(f"   → confidence: {validation['confidence_score']:.2f} ({validation['confidence_level']})")
            print(f"✅ [DONE] '{selected_product['canonical_name']}' | confidence: {validation['confidence_score']:.2f} | review: {validation['needs_review']}\n")

            return {
                "success": True,
                "normalized_product_id": selected_product.get('product_id'),
                "canonical_name": selected_product['canonical_name'],
                "brand": selected_product.get('brand'),
                "category": selected_product.get('category'),
                "subcategory": selected_product.get('subcategory'),
                "size": str(selected_product.get('size')) if selected_product.get('size') is not None else None,
                "unit_type": selected_product.get('unit_type'),
                "tags": selected_product.get('tags', []),
                "confidence": validation['confidence_score'],
                "confidence_level": validation['confidence_level'],
                "source": "sql_search",
                "needs_review": validation['needs_review']
            }

        except Exception as e:
            print(f"🔴 [ERROR] {str(e)}")
            return {
                "success": False,
                "error": f"Pipeline error: {str(e)}",
                "canonical_name": raw_product_name,  # Usa raw name come fallback
                "normalized_product_id": None,
                "brand": None,
                "category": None,
                "subcategory": None,
                "size": None,
                "unit_type": None,
                "tags": [],
                "confidence": 0.0,
                "confidence_level": "low",
                "source": "error",
                "needs_review": True
            }

    async def normalize_batch(
        self,
        items: List[Dict[str, Any]],
        household_id: str,
        batch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Normalizza batch di prodotti in parallelo

        Args:
            items: Lista items con raw_product_name, store_name, price
            household_id: ID household
            batch_size: Numero prodotti da processare simultaneamente (default da config)

        Returns:
            Lista risultati normalizzazione (stesso ordine di input)
        """
        # Usa batch_size da config se non specificato
        if batch_size is None:
            batch_size = settings.PARALLEL_NORMALIZATION_BATCH_SIZE

        print(f"🚀 [BATCH START] {len(items)} items, batch_size={batch_size}")

        results = []

        # Processa in batch di N items
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            print(f"   → Processing batch {i//batch_size + 1} ({len(batch)} items)...")

            # Parallelizza normalizzazione del batch
            batch_tasks = [
                self.normalize_product(
                    raw_product_name=item['raw_product_name'],
                    household_id=household_id,
                    store_name=item.get('store_name'),
                    price=item.get('price')
                )
                for item in batch
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Gestisci errori per singolo item
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        "success": False,
                        "error": str(result)
                    })
                else:
                    results.append(result)

        print(f"✅ [BATCH DONE] {len(results)} items processed")
        return results

    def _format_cache_result(self, cache_hit: Dict) -> Dict[str, Any]:
        """Formatta risultato cache in formato standard"""
        return {
            "success": True,
            "normalized_product_id": cache_hit['product_id'],
            "canonical_name": cache_hit.get('canonical_name'),
            "brand": cache_hit.get('brand'),
            "category": cache_hit.get('category'),
            "subcategory": cache_hit.get('subcategory'),
            "size": str(cache_hit.get('size')) if cache_hit.get('size') is not None else None,
            "unit_type": cache_hit.get('unit_type'),
            "tags": cache_hit.get('tags', []),
            "confidence": cache_hit['confidence'],
            "confidence_level": "high" if cache_hit['confidence'] >= 0.8 else "medium",
            "source": cache_hit['tier'],
            "needs_review": False
        }

    def _format_hypothesis_fallback(self, interpret_result: Dict) -> Dict[str, Any]:
        """Formatta fallback quando nessun candidato trovato"""
        return {
            "success": True,
            "normalized_product_id": None,
            "canonical_name": interpret_result['hypothesis'],
            "brand": interpret_result.get('brand'),
            "category": interpret_result.get('category'),
            "subcategory": interpret_result.get('subcategory'),
            "size": str(interpret_result.get('size')) if interpret_result.get('size') else None,
            "unit_type": interpret_result.get('unit_type'),
            "tags": interpret_result.get('tags', []),
            "confidence": 0.60,
            "confidence_level": "low",
            "source": "hypothesis_fallback",
            "needs_review": True
        }


# Instanza globale
product_normalizer_v2 = ProductNormalizerV2()
