"""
Configurazione Test - IDs e Fixtures Modificabili
"""

# ===================================
# IDS - MODIFICA CON I TUOI VALORI
# ===================================

TEST_HOUSEHOLD_ID = "72bc4164-a682-4827-a0a5-0cc029d049b0"  # MODIFICA!
TEST_USER_ID = "1c1ffd3e-511a-41f7-933a-8558ddfb5660"  # MODIFICA!

# ===================================
# TEST FIXTURES - PRODOTTI
# ===================================

TEST_PRODUCTS = {
    # SCENARIO 1: Cache Tier 1 Hit
    "cache_tier1": {
        "raw_name": "COCA COLA 1.5L",
        "canonical_name": "Coca Cola 1.5L",
        "brand": "Coca Cola",
        "category": "Bevande",
        "subcategory": "Bibite Gassate",
        "size": "1.5",
        "unit_type": "l",
        "tags": ["bibita", "gassata"],
        "price": 1.49,
        "store_name": "Esselunga"
    },

    # SCENARIO 2: Cache Tier 2 Hit
    "cache_tier2": {
        "raw_name": "PANE INTEGRALE 500G",
        "canonical_name": "Pane Integrale 500g",
        "brand": None,
        "category": "Panetteria",
        "subcategory": "Pane",
        "size": "500",
        "unit_type": "g",
        "tags": ["pane", "integrale"],
        "price": 1.20,
        "store_name": "Carrefour"
    },

    # SCENARIO 3: Vector Search Hit
    "vector_search": {
        "existing_canonical": "Coca Cola 1.5L",  # Prodotto già in DB
        "raw_name_similar": "COCACOLA 1.5",  # Raw name simile ma diverso
        "price": 1.39,
        "store_name": "Coop"
    },

    # SCENARIO 4: LLM Normalization (nuovo prodotto)
    "llm_new": {
        "raw_name": "ACQUA SANT'ANNA NATURALE 2L",
        "expected_canonical": "Acqua Sant'Anna Naturale 2L",
        "expected_brand": "Sant'Anna",
        "expected_category": "Bevande",
        "price": 0.49,
        "store_name": "Lidl"
    },

    # SCENARIO 5: Price Anomaly
    "price_anomaly": {
        "raw_name": "LATTE INTERO 1L",
        "canonical_name": "Latte Intero 1L",
        "brand": "Granarolo",
        "category": "Latticini",
        "subcategory": "Latte",
        "size": "1",
        "unit_type": "l",
        "tags": ["latte", "intero"],
        "normal_price": 1.50,
        "anomaly_price": 10.00,  # Prezzo anomalo!
        "store_name": "Conad"
    },

    # SCENARIO 6: Low Context (prodotto mai comprato dall'household)
    "low_context": {
        "raw_name": "BISCOTTI FROLLINI 350G",
        "canonical_name": "Biscotti Frollini 350g",
        "brand": "Mulino Bianco",
        "category": "Dolci",
        "subcategory": "Biscotti",
        "size": "350",
        "unit_type": "g",
        "tags": ["biscotti", "frollini"],
        "price": 2.50,
        "store_name": "Esselunga"
    }
}

# ===================================
# TEST STORES
# ===================================

TEST_STORES = {
    "esselunga": {
        "name": "Esselunga",
        "chain": "Esselunga",
        "address_city": "Milano"
    },
    "carrefour": {
        "name": "Carrefour",
        "chain": "Carrefour",
        "address_city": "Roma"
    },
    "coop": {
        "name": "Coop",
        "chain": "Coop",
        "address_city": "Firenze"
    },
    "lidl": {
        "name": "Lidl",
        "chain": "Lidl",
        "address_city": "Torino"
    },
    "conad": {
        "name": "Conad",
        "chain": "Conad",
        "address_city": "Bologna"
    }
}

# ===================================
# CONFIGURAZIONE TEST
# ===================================

# Confidence thresholds attesi
EXPECTED_CONFIDENCE = {
    "cache_tier1_min": 0.90,
    "cache_tier1_max": 0.97,
    "cache_tier2": 0.85,
    "vector_search_min": 0.75,
    "llm_min": 0.50
}

# Timeout per test LLM (in secondi)
LLM_TEST_TIMEOUT = 30

# Flag per cleanup automatico
AUTO_CLEANUP = True
