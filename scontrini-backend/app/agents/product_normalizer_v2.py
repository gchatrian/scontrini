"""
Product Normalizer V2 - Multi-Stage Pipeline
Pipeline completa: Cache → Vector Search → LLM → Validation → Cache Update
"""
import json
from typing import Dict, List, Optional, Any
from openai import OpenAI
from app.config import settings
from app.agents.prompts import PRODUCT_IDENTIFICATION_PROMPT, PRODUCT_VALIDATION_PROMPT
from app.agents.tools import TOOL_DEFINITIONS, execute_function
from app.services.cache_service import CacheService
from app.services.vector_search_service import VectorSearchService
from app.services.context_service import ContextService
from app.services.validation_service import ValidationService
from app.services.cache_update_service import CacheUpdateService
from app.services.embedding_service import EmbeddingService
from app.services.supabase_service import supabase_service


class ProductNormalizerV2:
    """Agente per normalizzazione prodotti con pipeline multi-stage"""

    def __init__(self):
        """Inizializza agente e servizi"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.temperature_normalizer = settings.OPENAI_TEMPERATURE_NORMALIZER
        self.temperature_validator = settings.OPENAI_TEMPERATURE_VALIDATOR
        self.max_iterations = 10

        # Inizializza servizi
        self.embedding_service = EmbeddingService()
        self.cache_service = CacheService(
            supabase_client=supabase_service.client,
            embedding_service=self.embedding_service
        )
        self.vector_search_service = VectorSearchService(
            supabase_client=supabase_service.client,
            embedding_service=self.embedding_service
        )
        self.context_service = ContextService(
            supabase_client=supabase_service.client
        )
        self.validation_service = ValidationService()
        self.cache_update_service = CacheUpdateService(
            supabase_client=supabase_service.client,
            embedding_service=self.embedding_service
        )

    async def normalize_product(
        self,
        raw_product_name: str,
        household_id: str,
        store_name: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Normalizza prodotto usando pipeline multi-stage

        Pipeline:
        1. Cache Lookup (Tier 1 + Tier 2)
        2. Vector Search (se cache miss)
        3. LLM Normalization (se vector search non trova match)
        4. Validation
        5. Cache Update

        Args:
            raw_product_name: Nome grezzo da scontrino
            household_id: ID household per context
            store_name: Nome negozio
            price: Prezzo prodotto

        Returns:
            {
                "success": bool,
                "normalized_product_id": str,
                "canonical_name": str,
                "brand": str,
                "category": str,
                "subcategory": str,
                "size": str,
                "unit_type": str,
                "tags": [str],
                "confidence": float,
                "confidence_level": "high" | "medium" | "low",
                "source": "cache_tier1" | "cache_tier2" | "vector_search" | "llm",
                "validation": {...},
                "context": {...}
            }
        """
        try:
            print(f"🔎 [PIPELINE START] raw='{raw_product_name}' | store='{store_name}' | price={price}")

            # PHASE 0: Cache Lookup
            cache_result = await self._try_cache_lookup(
                raw_name=raw_product_name,
                store_name=store_name,
                current_price=price
            )

            if cache_result:
                print(f"✅ [CACHE HIT] tier={cache_result['tier']} | confidence={cache_result['confidence']:.3f}")

                # Arricchisci con contesto
                context = await self.context_service.get_enriched_context(
                    household_id=household_id,
                    normalized_product_id=cache_result['product_id'],
                    store_name=store_name
                )

                # Valida
                validation = self.validation_service.validate_normalization(
                    normalized_product=cache_result['product'],
                    raw_name=raw_product_name,
                    confidence_score=cache_result['confidence'],
                    context=context,
                    current_price=price
                )

                return {
                    "success": True,
                    "normalized_product_id": cache_result['product_id'],
                    **cache_result['product'],
                    "confidence": validation['final_confidence'],
                    "confidence_level": validation['confidence_level'],
                    "source": cache_result['tier'],
                    "validation": validation,
                    "context": context
                }

            print("⚠️ [CACHE MISS] → trying vector search...")

            # PHASE 1: Vector Search
            vector_result = await self._try_vector_search(
                raw_name=raw_product_name,
                store_name=store_name
            )

            if vector_result:
                print(f"✅ [VECTOR HIT] similarity={vector_result['similarity_score']:.3f}")

                # Arricchisci con contesto
                context = await self.context_service.get_enriched_context(
                    household_id=household_id,
                    normalized_product_id=vector_result['product_id'],
                    store_name=store_name
                )

                # Valida
                validation = self.validation_service.validate_normalization(
                    normalized_product=vector_result['product'],
                    raw_name=raw_product_name,
                    confidence_score=vector_result['similarity_score'],
                    context=context,
                    current_price=price
                )

                return {
                    "success": True,
                    "normalized_product_id": vector_result['product_id'],
                    **vector_result['product'],
                    "confidence": validation['final_confidence'],
                    "confidence_level": validation['confidence_level'],
                    "source": "vector_search",
                    "validation": validation,
                    "context": context
                }

            print("⚠️ [VECTOR MISS] → invoking LLM...")

            # PHASE 2: LLM Normalization
            llm_result = await self._llm_normalization(
                raw_name=raw_product_name,
                store_name=store_name,
                price=price
            )

            if not llm_result['success']:
                return llm_result

            print(f"✅ [LLM SUCCESS] canonical='{llm_result['canonical_name']}' | created_new={llm_result.get('created_new', False)}")

            # Arricchisci con contesto
            context = await self.context_service.get_enriched_context(
                household_id=household_id,
                normalized_product_id=llm_result['normalized_product_id'],
                store_name=store_name
            )

            # PHASE 3: Validation
            validation = self.validation_service.validate_normalization(
                normalized_product={
                    'canonical_name': llm_result['canonical_name'],
                    'brand': llm_result.get('brand'),
                    'category': llm_result.get('category'),
                    'subcategory': llm_result.get('subcategory'),
                    'size': llm_result.get('size'),
                    'unit_type': llm_result.get('unit_type'),
                    'tags': llm_result.get('tags', [])
                },
                raw_name=raw_product_name,
                confidence_score=llm_result.get('confidence', 0.7),
                context=context,
                current_price=price
            )

            print(f"📊 [VALIDATION] final_confidence={validation['final_confidence']:.3f} | level={validation['confidence_level']}")

            # PHASE 4: Cache Update
            await self._update_cache(
                raw_name=raw_product_name,
                normalized_product_id=llm_result['normalized_product_id'],
                store_name=store_name,
                confidence_score=validation['final_confidence'],
                requires_manual_review=validation['flags']['needs_review']
            )

            return {
                "success": True,
                "normalized_product_id": llm_result['normalized_product_id'],
                "canonical_name": llm_result['canonical_name'],
                "brand": llm_result.get('brand'),
                "category": llm_result.get('category'),
                "subcategory": llm_result.get('subcategory'),
                "size": llm_result.get('size'),
                "unit_type": llm_result.get('unit_type'),
                "tags": llm_result.get('tags', []),
                "confidence": validation['final_confidence'],
                "confidence_level": validation['confidence_level'],
                "source": "llm",
                "created_new": llm_result.get('created_new', False),
                "validation": validation,
                "context": context
            }

        except Exception as e:
            print(f"🔴 [PIPELINE ERROR] {str(e)}")
            return {
                "success": False,
                "error": f"Pipeline error: {str(e)}"
            }

    async def _try_cache_lookup(
        self,
        raw_name: str,
        store_name: Optional[str],
        current_price: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """
        Prova cache lookup (Tier 1 + Tier 2)

        Returns:
            None se cache miss, altrimenti dict con product data
        """
        cache_hit = await self.cache_service.get_cached_product(
            raw_name=raw_name,
            store_name=store_name,
            current_price=current_price
        )

        if not cache_hit:
            return None

        return {
            'tier': cache_hit['tier'],
            'product_id': cache_hit['product_id'],
            'confidence': cache_hit['confidence'],
            'product': {
                'canonical_name': cache_hit.get('canonical_name'),
                'brand': cache_hit.get('brand'),
                'category': cache_hit.get('category'),
                'subcategory': cache_hit.get('subcategory'),
                'size': cache_hit.get('size'),
                'unit_type': cache_hit.get('unit_type'),
                'tags': cache_hit.get('tags', [])
            }
        }

    async def _try_vector_search(
        self,
        raw_name: str,
        store_name: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Prova vector search semantico

        Returns:
            None se no match, altrimenti best match
        """
        results = await self.vector_search_service.search_similar_products(
            raw_name=raw_name,
            store_name=store_name,
            limit=1
        )

        if not results:
            return None

        best_match = results[0]

        # Accetta solo se similarity sopra threshold
        if best_match['similarity_score'] < settings.VECTOR_SEARCH_SIMILARITY_THRESHOLD:
            return None

        return {
            'product_id': best_match['product_id'],
            'similarity_score': best_match['similarity_score'],
            'product': {
                'canonical_name': best_match['canonical_name'],
                'brand': best_match.get('brand'),
                'category': best_match.get('category'),
                'subcategory': best_match.get('subcategory'),
                'size': best_match.get('size'),
                'unit_type': best_match.get('unit_type'),
                'tags': best_match.get('tags', [])
            }
        }

    async def _llm_normalization(
        self,
        raw_name: str,
        store_name: Optional[str],
        price: Optional[float]
    ) -> Dict[str, Any]:
        """
        Esegue normalizzazione via LLM con function calling

        Returns:
            Dict con risultato normalizzazione
        """
        # Step 1: Identificazione
        user_message = self._build_user_message(raw_name, store_name, price)
        identification_result = self._run_identification_loop(user_message)

        if not identification_result["success"]:
            return {
                "success": False,
                "error": f"LLM identification failed: {identification_result.get('error')}"
            }

        # Step 2: Validazione LLM
        validation_outcome = self._validate_identification(
            raw_name=raw_name,
            identified={
                "canonical_name": identification_result.get("canonical_name"),
                "brand": identification_result.get("brand"),
                "category": identification_result.get("category"),
                "subcategory": identification_result.get("subcategory"),
                "size": identification_result.get("size"),
                "unit_type": identification_result.get("unit_type"),
                "notes": identification_result.get("identification_notes")
            }
        )

        final_confidence = float(validation_outcome.get("confidence", 0.5))

        return {
            "success": True,
            "normalized_product_id": identification_result["normalized_product_id"],
            "canonical_name": identification_result.get("canonical_name"),
            "brand": identification_result.get("brand"),
            "category": identification_result.get("category"),
            "subcategory": identification_result.get("subcategory"),
            "size": identification_result.get("size"),
            "unit_type": identification_result.get("unit_type"),
            "tags": identification_result.get("tags", []),
            "created_new": identification_result.get("created_new", False),
            "confidence": final_confidence
        }

    def _build_user_message(
        self,
        raw_name: str,
        store_name: Optional[str],
        price: Optional[float]
    ) -> str:
        """Costruisce messaggio utente per LLM"""
        message = f"RAW: '{raw_name}'"

        if store_name:
            message += f" | STORE: '{store_name}'"
        if price:
            message += f" | PRICE: €{price:.2f}"

        message += """

TASK:
- Estrai BRAND (se presente), PRODOTTO, FORMATO.
- Se uno tra BRAND o PRODOTTO è incerto, parti da quello più certo per vincolare la ricerca dell'altro.
- Prova PRIMA a riusare un prodotto esistente (find_existing_product) e SOLO se non trovato crea nuovo (create_normalized_product).
- Rispondi SOLO con JSON finale."""

        return message

    def _run_identification_loop(self, user_message: str) -> Dict:
        """Esegue loop di function calling per identificazione"""
        messages = [
            {"role": "system", "content": PRODUCT_IDENTIFICATION_PROMPT},
            {"role": "user", "content": user_message}
        ]

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=self.temperature_normalizer
            )

            message = response.choices[0].message

            if message.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in message.tool_calls
                    ]
                })

                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    function_result = execute_function(function_name, arguments)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(function_result)
                    })

                continue

            if message.content:
                try:
                    content = message.content.strip()

                    if content.startswith("```"):
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]

                    result = json.loads(content)
                    result["success"] = True
                    return result

                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": f"Failed to parse response: {message.content}"
                    }

            return {
                "success": False,
                "error": "Agent did not return valid response"
            }

        return {
            "success": False,
            "error": f"Max iterations ({self.max_iterations}) reached"
        }

    def _validate_identification(self, raw_name: str, identified: Dict) -> Dict:
        """Valida risultato identificazione via LLM"""
        messages = [
            {"role": "system", "content": PRODUCT_VALIDATION_PROMPT},
            {"role": "user", "content": json.dumps({
                "raw": raw_name,
                "identified": identified
            })}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature_validator,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content.strip()
            return json.loads(content)
        except Exception as e:
            return {
                "confidence": 0.5,
                "pending_review": True,
                "validation_notes": f"validation_error: {str(e)}"
            }

    async def _update_cache(
        self,
        raw_name: str,
        normalized_product_id: str,
        store_name: Optional[str],
        confidence_score: float,
        requires_manual_review: bool
    ) -> None:
        """Aggiorna cache con nuovo mapping"""
        await self.cache_update_service.update_product_mapping(
            raw_name=raw_name,
            normalized_product_id=normalized_product_id,
            store_name=store_name,
            confidence_score=confidence_score,
            verified_by_user=False,
            interpretation_details={
                'requires_manual_review': requires_manual_review
            }
        )


# Instanza globale
product_normalizer_v2 = ProductNormalizerV2()
