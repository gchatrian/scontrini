"""
Cache Update Service - Aggiornamento cache e materialized views
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from supabase import Client
from app.services.embedding_service import EmbeddingService
from app.config import settings


class CacheUpdateService:
    """Servizio per aggiornamento cache prodotti e materialized views"""

    def __init__(self, supabase_client: Client, embedding_service: EmbeddingService):
        self.supabase = supabase_client
        self.embedding_service = embedding_service

    async def update_product_mapping(
        self,
        raw_name: str,
        normalized_product_id: str,
        store_name: Optional[str],
        confidence_score: float,
        verified_by_user: bool = False,
        interpretation_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crea o aggiorna mapping prodotto grezzo → normalizzato

        Args:
            raw_name: Nome prodotto grezzo da scontrino
            normalized_product_id: ID prodotto normalizzato
            store_name: Nome negozio (opzionale per mappings generici)
            confidence_score: Score di confidence (0-1)
            verified_by_user: Se approvato da utente
            interpretation_details: Dettagli interpretazione (JSONB)

        Returns:
            {
                "success": bool,
                "mapping_id": str,
                "created": bool  # true se nuovo, false se aggiornato
            }
        """
        # Cerca mapping esistente
        existing = self.supabase.table('product_mappings') \
            .select('id, confidence_score') \
            .eq('raw_name', raw_name) \
            .eq('normalized_product_id', normalized_product_id)

        if store_name:
            existing = existing.eq('store_name', store_name)
        else:
            existing = existing.is_('store_name', 'null')

        existing_response = existing.execute()

        mapping_data = {
            'raw_name': raw_name,
            'normalized_product_id': normalized_product_id,
            'store_name': store_name,
            'confidence_score': confidence_score,
            'verified_by_user': verified_by_user,
            'interpretation_details': interpretation_details or {}
        }

        if existing_response.data:
            # Aggiorna mapping esistente solo se nuovo confidence è maggiore
            existing_mapping = existing_response.data[0]
            if confidence_score > existing_mapping.get('confidence_score', 0):
                response = self.supabase.table('product_mappings') \
                    .update(mapping_data) \
                    .eq('id', existing_mapping['id']) \
                    .execute()

                return {
                    'success': True,
                    'mapping_id': existing_mapping['id'],
                    'created': False
                }
            else:
                return {
                    'success': True,
                    'mapping_id': existing_mapping['id'],
                    'created': False
                }
        else:
            # Crea nuovo mapping
            response = self.supabase.table('product_mappings') \
                .insert(mapping_data) \
                .execute()

            return {
                'success': True,
                'mapping_id': response.data[0]['id'],
                'created': True
            }

    async def update_normalized_product(
        self,
        product_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Aggiorna prodotto normalizzato esistente

        Args:
            product_id: ID prodotto da aggiornare
            updates: Dict con campi da aggiornare

        Returns:
            {
                "success": bool,
                "product_id": str,
                "updated_fields": [str]
            }
        """
        # Filtra solo campi validi
        valid_fields = [
            'canonical_name', 'brand', 'category', 'subcategory',
            'size', 'unit_type', 'barcode', 'tags', 'nutritional_info',
            'verification_status'
        ]

        filtered_updates = {
            k: v for k, v in updates.items()
            if k in valid_fields
        }

        if not filtered_updates:
            return {
                'success': False,
                'error': 'No valid fields to update'
            }

        # Aggiorna prodotto
        response = self.supabase.table('normalized_products') \
            .update(filtered_updates) \
            .eq('id', product_id) \
            .execute()

        return {
            'success': True,
            'product_id': product_id,
            'updated_fields': list(filtered_updates.keys())
        }

    async def create_normalized_product(
        self,
        canonical_name: str,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        size: Optional[str] = None,
        unit_type: Optional[str] = None,
        barcode: Optional[str] = None,
        tags: Optional[List[str]] = None,
        nutritional_info: Optional[Dict[str, Any]] = None,
        verification_status: str = 'auto_verified'
    ) -> Dict[str, Any]:
        """
        Crea nuovo prodotto normalizzato con embedding

        Args:
            canonical_name: Nome standardizzato prodotto
            brand, category, etc: Altri campi prodotto
            verification_status: Stato verifica

        Returns:
            {
                "success": bool,
                "product_id": str,
                "embedding_generated": bool
            }
        """
        # Genera embedding per il canonical name
        embedding = await self.embedding_service.generate_embedding(canonical_name)

        product_data = {
            'canonical_name': canonical_name,
            'brand': brand,
            'category': category,
            'subcategory': subcategory,
            'size': size,
            'unit_type': unit_type,
            'barcode': barcode,
            'tags': tags,
            'nutritional_info': nutritional_info,
            'verification_status': verification_status,
            'embedding': embedding
        }

        # Inserisci prodotto
        response = self.supabase.table('normalized_products') \
            .insert(product_data) \
            .execute()

        return {
            'success': True,
            'product_id': response.data[0]['id'],
            'embedding_generated': True
        }

    async def refresh_cache_stats(self) -> Dict[str, Any]:
        """
        Refresh materialized view product_cache_stats

        Returns:
            {
                "success": bool,
                "refreshed_at": str,
                "rows_count": int
            }
        """
        # Chiama RPC function per refresh
        self.supabase.rpc('refresh_product_cache_stats').execute()

        # Conta righe nella view
        count_response = self.supabase.table('product_cache_stats') \
            .select('*', count='exact') \
            .execute()

        return {
            'success': True,
            'refreshed_at': datetime.utcnow().isoformat(),
            'rows_count': count_response.count
        }

    async def create_purchase_history(
        self,
        household_id: str,
        receipt_id: str,
        receipt_item_id: str,
        normalized_product_id: str,
        store_id: Optional[str],
        purchase_date: str,
        store_name: Optional[str],
        quantity: Optional[float],
        unit_price: Optional[float],
        total_price: float
    ) -> Dict[str, Any]:
        """
        Crea record in purchase_history

        Args:
            household_id, receipt_id, etc: Dati acquisto

        Returns:
            {
                "success": bool,
                "purchase_id": str
            }
        """
        purchase_data = {
            'household_id': household_id,
            'receipt_id': receipt_id,
            'receipt_item_id': receipt_item_id,
            'normalized_product_id': normalized_product_id,
            'store_id': store_id,
            'purchase_date': purchase_date,
            'store_name': store_name,
            'quantity': quantity,
            'unit_price': unit_price,
            'total_price': total_price
        }

        response = self.supabase.table('purchase_history') \
            .insert(purchase_data) \
            .execute()

        return {
            'success': True,
            'purchase_id': response.data[0]['id']
        }

    async def batch_create_mappings(
        self,
        mappings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Crea batch di product mappings

        Args:
            mappings: Lista di mappings da creare
                [
                    {
                        "raw_name": "...",
                        "normalized_product_id": "...",
                        "store_name": "...",
                        "confidence_score": 0.85,
                        "verified_by_user": false
                    },
                    ...
                ]

        Returns:
            {
                "success": bool,
                "created_count": int,
                "updated_count": int,
                "failed_count": int,
                "errors": [str]
            }
        """
        created = 0
        updated = 0
        failed = 0
        errors = []

        for mapping in mappings:
            try:
                result = await self.update_product_mapping(
                    raw_name=mapping['raw_name'],
                    normalized_product_id=mapping['normalized_product_id'],
                    store_name=mapping.get('store_name'),
                    confidence_score=mapping.get('confidence_score', 0.0),
                    verified_by_user=mapping.get('verified_by_user', False),
                    interpretation_details=mapping.get('interpretation_details')
                )

                if result['success']:
                    if result['created']:
                        created += 1
                    else:
                        updated += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1
                errors.append(f"Failed for {mapping.get('raw_name')}: {str(e)}")

        return {
            'success': failed == 0,
            'created_count': created,
            'updated_count': updated,
            'failed_count': failed,
            'errors': errors
        }

    async def batch_create_purchases(
        self,
        purchases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Crea batch di purchase history records

        Args:
            purchases: Lista di purchases

        Returns:
            {
                "success": bool,
                "created_count": int,
                "failed_count": int,
                "errors": [str]
            }
        """
        created = 0
        failed = 0
        errors = []

        for purchase in purchases:
            try:
                result = await self.create_purchase_history(
                    household_id=purchase['household_id'],
                    receipt_id=purchase['receipt_id'],
                    receipt_item_id=purchase['receipt_item_id'],
                    normalized_product_id=purchase['normalized_product_id'],
                    store_id=purchase.get('store_id'),
                    purchase_date=purchase['purchase_date'],
                    store_name=purchase.get('store_name'),
                    quantity=purchase.get('quantity'),
                    unit_price=purchase.get('unit_price'),
                    total_price=purchase['total_price']
                )

                if result['success']:
                    created += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1
                errors.append(f"Failed for receipt_item {purchase.get('receipt_item_id')}: {str(e)}")

        return {
            'success': failed == 0,
            'created_count': created,
            'failed_count': failed,
            'errors': errors
        }

    def get_service_stats(self) -> Dict[str, Any]:
        """
        Restituisce statistiche del servizio

        Returns:
            Dict con embedding stats
        """
        return {
            'embedding_stats': self.embedding_service.get_usage_stats()
        }
