"""
Pytest Fixtures per Integration Tests
"""
import pytest
import asyncio
from datetime import date
from typing import List, Dict, Any
import sys
import os

# Aggiungi app al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.supabase_service import supabase_service
from app.services.embedding_service import EmbeddingService
from tests.test_config import (
    TEST_HOUSEHOLD_ID,
    TEST_USER_ID,
    TEST_PRODUCTS,
    TEST_STORES,
    AUTO_CLEANUP
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def household_id():
    """Test household ID"""
    return TEST_HOUSEHOLD_ID


@pytest.fixture
def user_id():
    """Test user ID"""
    return TEST_USER_ID


@pytest.fixture
def embedding_service():
    """Embedding service instance"""
    return EmbeddingService()


@pytest.fixture
async def cleanup_tracker():
    """
    Tracker per IDs da eliminare dopo il test

    Usage:
        cleanup_tracker.add('normalized_products', product_id)
        # Cleanup automatico a fine test
    """
    tracker = CleanupTracker()
    yield tracker

    if AUTO_CLEANUP:
        await tracker.cleanup_all()


class CleanupTracker:
    """Helper per tracciare e pulire dati test"""

    def __init__(self):
        self.items = {
            'purchase_history': [],
            'product_mappings': [],
            'receipt_items': [],
            'receipts': [],
            'normalized_products': [],
            'stores': []
        }

    def add(self, table: str, item_id: str):
        """Aggiungi item da eliminare"""
        if table in self.items:
            self.items[table].append(item_id)

    async def cleanup_all(self):
        """Elimina tutti gli items tracciati (in ordine inverso per FK)"""
        # Ordine per rispettare foreign keys
        order = [
            'purchase_history',
            'product_mappings',
            'receipt_items',
            'receipts',
            'normalized_products',
            'stores'
        ]

        for table in order:
            for item_id in self.items[table]:
                try:
                    supabase_service.client.table(table).delete().eq('id', item_id).execute()
                except Exception as e:
                    print(f"⚠️ Cleanup warning: Failed to delete {table}/{item_id}: {e}")


@pytest.fixture
async def create_test_product(embedding_service, cleanup_tracker):
    """
    Factory fixture per creare prodotti test

    Usage:
        product = await create_test_product(
            canonical_name="Test Product",
            brand="Test Brand",
            ...
        )
    """
    async def _create(
        canonical_name: str,
        brand: str = None,
        category: str = None,
        subcategory: str = None,
        size: str = None,
        unit_type: str = None,
        tags: List[str] = None,
        verification_status: str = "auto_verified"
    ) -> Dict[str, Any]:
        # Genera embedding
        embedding = await embedding_service.generate_embedding(canonical_name)

        # Crea prodotto
        response = supabase_service.client.table('normalized_products').insert({
            'canonical_name': canonical_name,
            'brand': brand,
            'category': category,
            'subcategory': subcategory,
            'size': size,
            'unit_type': unit_type,
            'tags': tags,
            'verification_status': verification_status,
            'embedding': embedding
        }).execute()

        product = response.data[0]
        cleanup_tracker.add('normalized_products', product['id'])

        return product

    return _create


@pytest.fixture
async def create_test_mapping(cleanup_tracker):
    """
    Factory fixture per creare product mappings

    Usage:
        mapping = await create_test_mapping(
            raw_name="TEST RAW",
            normalized_product_id=product_id,
            ...
        )
    """
    async def _create(
        raw_name: str,
        normalized_product_id: str,
        store_name: str = None,
        confidence_score: float = 0.90,
        verified_by_user: bool = True
    ) -> Dict[str, Any]:
        response = supabase_service.client.table('product_mappings').insert({
            'raw_name': raw_name,
            'normalized_product_id': normalized_product_id,
            'store_name': store_name,
            'confidence_score': confidence_score,
            'verified_by_user': verified_by_user
        }).execute()

        mapping = response.data[0]
        cleanup_tracker.add('product_mappings', mapping['id'])

        return mapping

    return _create


@pytest.fixture
async def create_test_purchase(cleanup_tracker, household_id):
    """
    Factory fixture per creare purchase history

    Usage:
        purchase = await create_test_purchase(
            normalized_product_id=product_id,
            unit_price=1.50,
            ...
        )
    """
    async def _create(
        normalized_product_id: str,
        receipt_id: str,
        receipt_item_id: str,
        store_id: str = None,
        store_name: str = None,
        unit_price: float = 1.00,
        quantity: float = 1.0,
        total_price: float = None,
        purchase_date: date = None
    ) -> Dict[str, Any]:
        if total_price is None:
            total_price = unit_price * quantity

        if purchase_date is None:
            purchase_date = date.today()

        response = supabase_service.client.table('purchase_history').insert({
            'household_id': household_id,
            'receipt_id': receipt_id,
            'receipt_item_id': receipt_item_id,
            'normalized_product_id': normalized_product_id,
            'store_id': store_id,
            'store_name': store_name,
            'unit_price': unit_price,
            'quantity': quantity,
            'total_price': total_price,
            'purchase_date': purchase_date.isoformat()
        }).execute()

        purchase = response.data[0]
        cleanup_tracker.add('purchase_history', purchase['id'])

        return purchase

    return _create


@pytest.fixture
async def create_test_receipt(cleanup_tracker, household_id, user_id):
    """
    Factory fixture per creare receipts test

    Usage:
        receipt = await create_test_receipt(
            store_name="Test Store",
            total_amount=10.50
        )
    """
    async def _create(
        store_id: str = None,
        store_name: str = "Test Store",
        total_amount: float = 0.00,
        receipt_date: date = None
    ) -> Dict[str, Any]:
        if receipt_date is None:
            receipt_date = date.today()

        response = supabase_service.client.table('receipts').insert({
            'household_id': household_id,
            'uploaded_by': user_id,
            'image_url': 'test://test.jpg',
            'store_id': store_id,
            'store_name': store_name,
            'total_amount': total_amount,
            'receipt_date': receipt_date.isoformat(),
            'processing_status': 'completed'
        }).execute()

        receipt = response.data[0]
        cleanup_tracker.add('receipts', receipt['id'])

        return receipt

    return _create


@pytest.fixture
async def create_test_receipt_item(cleanup_tracker):
    """
    Factory fixture per creare receipt items

    Usage:
        item = await create_test_receipt_item(
            receipt_id=receipt_id,
            raw_product_name="TEST ITEM",
            total_price=5.00
        )
    """
    async def _create(
        receipt_id: str,
        raw_product_name: str,
        quantity: float = 1.0,
        unit_price: float = None,
        total_price: float = 0.00
    ) -> Dict[str, Any]:
        response = supabase_service.client.table('receipt_items').insert({
            'receipt_id': receipt_id,
            'raw_product_name': raw_product_name,
            'quantity': quantity,
            'unit_price': unit_price,
            'total_price': total_price
        }).execute()

        item = response.data[0]
        cleanup_tracker.add('receipt_items', item['id'])

        return item

    return _create


@pytest.fixture
async def create_test_store(cleanup_tracker):
    """
    Factory fixture per creare stores test

    Usage:
        store = await create_test_store(
            name="Test Store",
            chain="Test Chain"
        )
    """
    async def _create(
        name: str,
        chain: str = None,
        address_city: str = None
    ) -> Dict[str, Any]:
        response = supabase_service.client.table('stores').insert({
            'name': name,
            'chain': chain,
            'address_city': address_city,
            'is_mock': True  # Flag per test data
        }).execute()

        store = response.data[0]
        cleanup_tracker.add('stores', store['id'])

        return store

    return _create
