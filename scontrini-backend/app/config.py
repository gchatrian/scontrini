"""
Configuration settings per Scontrini Backend
Gestisce tutte le environment variables
"""
from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Settings globali applicazione"""
    
    # Project info
    PROJECT_NAME: str = "scontrini"
    ENVIRONMENT: str = "development"
    API_VERSION: str = "v1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Supabase (Task 2)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    # Google Cloud (Task 3)
    GOOGLE_CLOUD_PROJECT_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    
    # OpenAI (Task 3)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # OpenAI Temperature Settings - Configurabili per ogni tipo di chiamata LLM
    OPENAI_TEMPERATURE_PARSER: float = 0.3      # Parsing scontrini (serve precisione)
    OPENAI_TEMPERATURE_NORMALIZER: float = 0.7  # Normalizzazione prodotti (bilanciato)
    OPENAI_TEMPERATURE_CATEGORIZER: float = 0.3 # Categorizzazione (serve consistenza)
    OPENAI_TEMPERATURE_VALIDATOR: float = 0.2   # Validazione (molto conservativo)

    # OpenAI Embeddings
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536
    OPENAI_EMBEDDING_CACHE_SIZE: int = 1000
    OPENAI_EMBEDDING_MAX_RETRIES: int = 3
    OPENAI_EMBEDDING_RETRY_DELAY: float = 1.0
    OPENAI_EMBEDDING_COST_PER_1K: float = 0.0001  # $0.0001 per 1000 tokens

    # Cache Service
    CACHE_BASE_CONFIDENCE: float = 0.90
    CACHE_PRICE_TOLERANCE: float = 0.30  # ±30%
    CACHE_MIN_HOUSEHOLDS_BOOST: int = 3
    CACHE_MIN_USAGE_BOOST: int = 10
    CACHE_RECENT_DAYS_THRESHOLD: int = 90
    CACHE_BOOST_HOUSEHOLDS: float = 0.03
    CACHE_BOOST_USAGE: float = 0.02
    CACHE_BOOST_RECENCY: float = 0.02
    CACHE_MAX_CONFIDENCE: float = 0.97
    CACHE_TIER2_PENALTY: float = 0.05
    CACHE_TIER2_MIN_CONFIDENCE: float = 0.85

    # Validation Service
    VALIDATION_HIGH_CONFIDENCE_THRESHOLD: float = 0.90
    VALIDATION_LOW_CONFIDENCE_THRESHOLD: float = 0.70

    # Vector Search Service
    VECTOR_SEARCH_MAX_RESULTS: int = 10
    VECTOR_SEARCH_SIMILARITY_THRESHOLD: float = 0.75
    VECTOR_SEARCH_BOOST_VERIFIED: float = 0.05  # +5% per prodotti user-verified
    VECTOR_SEARCH_BOOST_SAME_STORE: float = 0.03  # +3% per stesso negozio

    # Context Service
    CONTEXT_RECENT_PURCHASES_DAYS: int = 90  # Giorni per considerare acquisti recenti
    CONTEXT_MIN_FREQUENCY_THRESHOLD: int = 3  # Min acquisti per considerare frequente
    CONTEXT_POPULAR_MIN_HOUSEHOLDS: int = 2  # Min households per considerare popolare

    # Web Search (Optional - Task 5)
    SERPER_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse BACKEND_CORS_ORIGINS se è una stringa JSON
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            try:
                self.BACKEND_CORS_ORIGINS = json.loads(self.BACKEND_CORS_ORIGINS)
            except json.JSONDecodeError:
                self.BACKEND_CORS_ORIGINS = [self.BACKEND_CORS_ORIGINS]


# Instanza globale settings
settings = Settings()