"""
Embedding Service - Wrapper OpenAI Ada per generazione embeddings
Include cache locale e retry logic
"""
from typing import List
import time
from openai import OpenAI
from app.config import settings


class EmbeddingService:
    """Servizio per generazione embeddings OpenAI Ada"""

    def __init__(self):
        """Inizializza client OpenAI e configurazioni"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Configurazioni da settings
        self.MODEL = settings.OPENAI_EMBEDDING_MODEL
        self.DIMENSIONS = settings.OPENAI_EMBEDDING_DIMENSIONS
        self.MAX_RETRIES = settings.OPENAI_EMBEDDING_MAX_RETRIES
        self.RETRY_DELAY = settings.OPENAI_EMBEDDING_RETRY_DELAY
        self.cost_per_1k_tokens = settings.OPENAI_EMBEDDING_COST_PER_1K

        # Cache interno (dict semplice con limite size)
        self.cache = {}
        self.cache_max_size = settings.OPENAI_EMBEDDING_CACHE_SIZE

        # Usage tracking
        self.total_tokens = 0
        self.total_cost = 0.0

    def generate_embedding(self, text: str) -> List[float]:
        """
        Genera embedding per testo con cache

        Args:
            text: Testo da convertire in embedding

        Returns:
            Lista di 1536 float (embedding vector)
        """
        # Normalizza testo
        text_normalized = self._normalize_text(text)

        # Check cache
        if text_normalized in self.cache:
            return self.cache[text_normalized]

        # Retry loop
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.embeddings.create(
                    model=self.MODEL,
                    input=text_normalized
                )

                # Estrai embedding
                embedding = response.data[0].embedding

                # Track usage
                self._track_usage(response.usage.total_tokens)

                # Save to cache
                self._add_to_cache(text_normalized, embedding)

                return embedding

            except Exception as e:
                print(f"Embedding error (attempt {attempt + 1}/{self.MAX_RETRIES}): {str(e)}")

                if attempt < self.MAX_RETRIES - 1:
                    # Exponential backoff
                    delay = self.RETRY_DELAY * (2 ** attempt)
                    time.sleep(delay)
                else:
                    # Max retries raggiunto
                    raise Exception(f"Failed to generate embedding after {self.MAX_RETRIES} attempts: {str(e)}")

    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings per batch di testi

        Args:
            texts: Lista di testi

        Returns:
            Lista di embeddings
        """
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)

        return embeddings

    def _normalize_text(self, text: str) -> str:
        """
        Normalizza testo prima di embedding

        Args:
            text: Testo originale

        Returns:
            Testo normalizzato
        """
        # Strip whitespace
        normalized = text.strip()

        # Uppercase per consistency
        normalized = normalized.upper()

        # Limita lunghezza (OpenAI ha limite 8191 tokens)
        # 1 token ≈ 4 chars, quindi ~32k chars max
        # Ma per prodotti, non dovremmo mai avvicinarci
        if len(normalized) > 500:
            normalized = normalized[:500]

        return normalized

    def _track_usage(self, tokens: int):
        """
        Traccia uso tokens e costi

        Args:
            tokens: Numero di tokens usati
        """
        self.total_tokens += tokens
        cost = (tokens / 1000) * self.cost_per_1k_tokens
        self.total_cost += cost

    def _add_to_cache(self, text: str, embedding: List[float]):
        """Aggiunge embedding a cache con limite size"""
        if len(self.cache) >= self.cache_max_size:
            # Rimuovi primo elemento (FIFO)
            self.cache.pop(next(iter(self.cache)))

        self.cache[text] = embedding

    def get_usage_stats(self) -> dict:
        """
        Ritorna statistiche uso

        Returns:
            Dict con total_tokens, total_cost, cache_size
        """
        return {
            'total_tokens': self.total_tokens,
            'total_cost': round(self.total_cost, 6),
            'cache_size': len(self.cache),
            'cache_max_size': self.cache_max_size
        }

    def clear_cache(self):
        """Svuota cache"""
        self.cache.clear()


# Instanza globale
embedding_service = EmbeddingService()
