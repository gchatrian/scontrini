"""
Integration Tests - ProductNormalizerV2
Test con database Supabase reale
"""
import pytest
from datetime import date, timedelta
from tests.test_config import (
    TEST_PRODUCTS,
    EXPECTED_CONFIDENCE,
    LLM_TEST_TIMEOUT
)
from app.agents.product_normalizer_v2 import product_normalizer_v2


# ===================================
# SCENARIO 1: CACHE TIER 1 HIT
# ===================================

@pytest.mark.asyncio
async def test_cache_tier1_hit(
    household_id,
    create_test_product,
    create_test_mapping,
    create_test_receipt,
    create_test_receipt_item,
    create_test_purchase
):
    """
    Test cache hit Tier 1 (user-verified)

    Setup:
    - Crea prodotto verificato
    - Crea mapping verified_by_user=True
    - Crea purchase history con ≥3 acquisti

    Expected:
    - source="cache_tier1"
    - confidence ≥0.90
    - from_cache context
    """
    print("\n🧪 TEST: Cache Tier 1 Hit")

    # Setup test data
    fixture = TEST_PRODUCTS["cache_tier1"]

    # 1. Crea prodotto
    product = await create_test_product(
        canonical_name=fixture["canonical_name"],
        brand=fixture["brand"],
        category=fixture["category"],
        subcategory=fixture["subcategory"],
        size=fixture["size"],
        unit_type=fixture["unit_type"],
        tags=fixture["tags"],
        verification_status="user_verified"
    )
    print(f"✅ Prodotto creato: {product['id']}")

    # 2. Crea mapping verified
    mapping = await create_test_mapping(
        raw_name=fixture["raw_name"],
        normalized_product_id=product["id"],
        store_name=fixture["store_name"],
        confidence_score=0.95,
        verified_by_user=True
    )
    print(f"✅ Mapping creato: {mapping['id']}")

    # 3. Crea purchase history (per boost)
    receipt = await create_test_receipt(
        store_name=fixture["store_name"],
        total_amount=fixture["price"]
    )
    item = await create_test_receipt_item(
        receipt_id=receipt["id"],
        raw_product_name=fixture["raw_name"],
        total_price=fixture["price"]
    )

    # Crea 5 acquisti per triggare boost
    for i in range(5):
        await create_test_purchase(
            normalized_product_id=product["id"],
            receipt_id=receipt["id"],
            receipt_item_id=item["id"],
            store_name=fixture["store_name"],
            unit_price=fixture["price"],
            purchase_date=date.today() - timedelta(days=i*10)
        )
    print(f"✅ Purchase history creata (5 acquisti)")

    # EXECUTE: Normalizza prodotto
    result = await product_normalizer_v2.normalize_product(
        raw_product_name=fixture["raw_name"],
        household_id=household_id,
        store_name=fixture["store_name"],
        price=fixture["price"]
    )

    # ASSERT
    print(f"\n📊 Result: {result}")
    assert result["success"] == True
    assert result["source"] == "cache_tier1"
    assert result["normalized_product_id"] == product["id"]
    assert result["canonical_name"] == fixture["canonical_name"]
    assert result["confidence"] >= EXPECTED_CONFIDENCE["cache_tier1_min"]
    assert result["confidence"] <= EXPECTED_CONFIDENCE["cache_tier1_max"]
    assert result["confidence_level"] == "high"

    print(f"✅ Test passed: confidence={result['confidence']:.3f}")


# ===================================
# SCENARIO 2: CACHE TIER 2 HIT
# ===================================

@pytest.mark.asyncio
async def test_cache_tier2_hit(
    household_id,
    create_test_product,
    create_test_mapping
):
    """
    Test cache hit Tier 2 (auto-verified fallback)

    Setup:
    - Crea prodotto auto_verified
    - Crea mapping verified_by_user=False, confidence≥0.85

    Expected:
    - source="cache_tier2"
    - confidence ~0.85
    - confidence_level="medium" o "high"
    """
    print("\n🧪 TEST: Cache Tier 2 Hit")

    # Setup test data
    fixture = TEST_PRODUCTS["cache_tier2"]

    # 1. Crea prodotto
    product = await create_test_product(
        canonical_name=fixture["canonical_name"],
        brand=fixture["brand"],
        category=fixture["category"],
        subcategory=fixture["subcategory"],
        size=fixture["size"],
        unit_type=fixture["unit_type"],
        tags=fixture["tags"],
        verification_status="auto_verified"
    )
    print(f"✅ Prodotto creato: {product['id']}")

    # 2. Crea mapping NON verified
    mapping = await create_test_mapping(
        raw_name=fixture["raw_name"],
        normalized_product_id=product["id"],
        store_name=fixture["store_name"],
        confidence_score=0.87,
        verified_by_user=False
    )
    print(f"✅ Mapping creato (tier2): {mapping['id']}")

    # EXECUTE
    result = await product_normalizer_v2.normalize_product(
        raw_product_name=fixture["raw_name"],
        household_id=household_id,
        store_name=fixture["store_name"],
        price=fixture["price"]
    )

    # ASSERT
    print(f"\n📊 Result: {result}")
    assert result["success"] == True
    assert result["source"] == "cache_tier2"
    assert result["normalized_product_id"] == product["id"]
    assert result["confidence"] >= EXPECTED_CONFIDENCE["cache_tier2"] - 0.05
    assert result["confidence_level"] in ["medium", "high"]

    print(f"✅ Test passed: confidence={result['confidence']:.3f}")


# ===================================
# SCENARIO 3: VECTOR SEARCH HIT
# ===================================

@pytest.mark.asyncio
async def test_vector_search_hit(
    household_id,
    create_test_product
):
    """
    Test vector search semantico

    Setup:
    - Crea prodotto "Coca Cola 1.5L"
    - NO mapping per raw_name diverso

    Execute:
    - Cerca "COCACOLA 1.5" (simile semanticamente)

    Expected:
    - source="vector_search"
    - similarity ≥0.75
    - trova prodotto esistente
    """
    print("\n🧪 TEST: Vector Search Hit")

    # Setup test data
    fixture = TEST_PRODUCTS["vector_search"]

    # 1. Crea prodotto esistente
    product = await create_test_product(
        canonical_name=fixture["existing_canonical"],
        brand="Coca Cola",
        category="Bevande",
        subcategory="Bibite Gassate",
        size="1.5",
        unit_type="l",
        tags=["bibita", "gassata"],
        verification_status="user_verified"
    )
    print(f"✅ Prodotto esistente creato: {product['canonical_name']}")

    # 2. NO mapping per raw_name_similar (forza vector search)

    # EXECUTE: Cerca con nome simile
    result = await product_normalizer_v2.normalize_product(
        raw_product_name=fixture["raw_name_similar"],
        household_id=household_id,
        store_name=fixture["store_name"],
        price=fixture["price"]
    )

    # ASSERT
    print(f"\n📊 Result: {result}")
    assert result["success"] == True
    assert result["source"] == "vector_search"
    assert result["canonical_name"] == fixture["existing_canonical"]
    assert result["confidence"] >= EXPECTED_CONFIDENCE["vector_search_min"]

    print(f"✅ Test passed: found via vector search, confidence={result['confidence']:.3f}")


# ===================================
# SCENARIO 4: LLM NORMALIZATION
# ===================================

@pytest.mark.asyncio
@pytest.mark.timeout(LLM_TEST_TIMEOUT)
async def test_llm_normalization(household_id):
    """
    Test LLM normalization per prodotto nuovo

    Setup:
    - Nessun setup (prodotto completamente nuovo)

    Execute:
    - Normalizza prodotto mai visto

    Expected:
    - source="llm"
    - success=True
    - canonical_name popolato
    - created_new=True o trovato via LLM tools
    """
    print("\n🧪 TEST: LLM Normalization (nuovo prodotto)")

    # Setup test data
    fixture = TEST_PRODUCTS["llm_new"]

    # EXECUTE: Normalizza prodotto nuovo
    result = await product_normalizer_v2.normalize_product(
        raw_product_name=fixture["raw_name"],
        household_id=household_id,
        store_name=fixture["store_name"],
        price=fixture["price"]
    )

    # ASSERT
    print(f"\n📊 Result: {result}")
    assert result["success"] == True
    assert result["source"] == "llm"
    assert result["canonical_name"] is not None
    assert len(result["canonical_name"]) > 0
    assert result["confidence"] >= EXPECTED_CONFIDENCE["llm_min"]

    # Verifica campi normalizzati
    if fixture.get("expected_brand"):
        assert result.get("brand") == fixture["expected_brand"]
    if fixture.get("expected_category"):
        assert result.get("category") == fixture["expected_category"]

    print(f"✅ Test passed: LLM normalized to '{result['canonical_name']}', confidence={result['confidence']:.3f}")


# ===================================
# SCENARIO 5: PRICE ANOMALY DETECTION
# ===================================

@pytest.mark.asyncio
async def test_price_anomaly_detection(
    household_id,
    create_test_product,
    create_test_mapping,
    create_test_receipt,
    create_test_receipt_item,
    create_test_purchase
):
    """
    Test rilevamento prezzo anomalo

    Setup:
    - Prodotto con storico prezzi ~1.50€
    - Crea 5 acquisti con prezzo normale

    Execute:
    - Normalizza con prezzo 10.00€ (anomalo)

    Expected:
    - validation.flags.price_anomaly=True
    - confidence penalizzata
    - warning presente
    """
    print("\n🧪 TEST: Price Anomaly Detection")

    # Setup test data
    fixture = TEST_PRODUCTS["price_anomaly"]

    # 1. Crea prodotto
    product = await create_test_product(
        canonical_name=fixture["canonical_name"],
        brand=fixture["brand"],
        category=fixture["category"],
        subcategory=fixture["subcategory"],
        size=fixture["size"],
        unit_type=fixture["unit_type"],
        tags=fixture["tags"],
        verification_status="user_verified"
    )

    # 2. Crea mapping
    mapping = await create_test_mapping(
        raw_name=fixture["raw_name"],
        normalized_product_id=product["id"],
        store_name=fixture["store_name"],
        confidence_score=0.95,
        verified_by_user=True
    )

    # 3. Crea storico con prezzi normali
    receipt = await create_test_receipt(
        store_name=fixture["store_name"],
        total_amount=fixture["normal_price"] * 5
    )
    item = await create_test_receipt_item(
        receipt_id=receipt["id"],
        raw_product_name=fixture["raw_name"],
        total_price=fixture["normal_price"]
    )

    for i in range(5):
        await create_test_purchase(
            normalized_product_id=product["id"],
            receipt_id=receipt["id"],
            receipt_item_id=item["id"],
            store_name=fixture["store_name"],
            unit_price=fixture["normal_price"],  # Prezzo normale
            purchase_date=date.today() - timedelta(days=i*7)
        )
    print(f"✅ Purchase history creata con prezzo normale: €{fixture['normal_price']}")

    # EXECUTE: Normalizza con prezzo ANOMALO
    result = await product_normalizer_v2.normalize_product(
        raw_product_name=fixture["raw_name"],
        household_id=household_id,
        store_name=fixture["store_name"],
        price=fixture["anomaly_price"]  # PREZZO ANOMALO!
    )

    # ASSERT
    print(f"\n📊 Result: {result}")
    assert result["success"] == True
    assert result["validation"]["flags"]["price_anomaly"] == True
    assert len(result["validation"]["warnings"]) > 0
    assert any("anomalo" in w.lower() or "prezzo" in w.lower() for w in result["validation"]["warnings"])

    # Confidence dovrebbe essere penalizzata
    # (cache tier1 base ~0.90-0.97, ma penalità -15% per price anomaly)
    assert result["confidence"] < 0.90

    print(f"✅ Test passed: price anomaly detected, confidence penalized to {result['confidence']:.3f}")


# ===================================
# SCENARIO 6: LOW CONTEXT WARNING
# ===================================

@pytest.mark.asyncio
async def test_low_context_warning(
    household_id,
    create_test_product,
    create_test_mapping
):
    """
    Test warning per contesto basso

    Setup:
    - Prodotto senza purchase_history per household

    Execute:
    - Normalizza prodotto mai comprato

    Expected:
    - context.context_score < 0.3
    - validation.flags.low_context=True
    - warning presente
    """
    print("\n🧪 TEST: Low Context Warning")

    # Setup test data
    fixture = TEST_PRODUCTS["low_context"]

    # 1. Crea prodotto
    product = await create_test_product(
        canonical_name=fixture["canonical_name"],
        brand=fixture["brand"],
        category=fixture["category"],
        subcategory=fixture["subcategory"],
        size=fixture["size"],
        unit_type=fixture["unit_type"],
        tags=fixture["tags"],
        verification_status="auto_verified"
    )

    # 2. Crea mapping
    mapping = await create_test_mapping(
        raw_name=fixture["raw_name"],
        normalized_product_id=product["id"],
        store_name=fixture["store_name"],
        confidence_score=0.80,
        verified_by_user=False
    )

    # 3. NO purchase_history (contesto basso)
    print("⚠️ No purchase history creata (low context scenario)")

    # EXECUTE
    result = await product_normalizer_v2.normalize_product(
        raw_product_name=fixture["raw_name"],
        household_id=household_id,
        store_name=fixture["store_name"],
        price=fixture["price"]
    )

    # ASSERT
    print(f"\n📊 Result: {result}")
    assert result["success"] == True
    assert result["context"]["context_score"] < 0.3
    assert result["validation"]["flags"]["low_context"] == True
    assert any("contesto" in w.lower() or "context" in w.lower() for w in result["validation"]["warnings"])

    print(f"✅ Test passed: low context detected, context_score={result['context']['context_score']:.3f}")
