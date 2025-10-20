"""
Categorization Service
Servizio per categorizzare prodotti usando OpenAI LLM
"""
import json
from typing import Dict, Optional
from openai import OpenAI
from app.config import settings


class CategorizationService:
    """Servizio per categorizzazione prodotti con LLM"""
    
    def __init__(self):
        """Inizializza client OpenAI"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        # Temperatura specifica per categorizzazione (da .env: OPENAI_TEMPERATURE_CATEGORIZER)
        self.temperature = settings.OPENAI_TEMPERATURE_CATEGORIZER
    
    def categorize_product(
        self,
        canonical_name: str,
        brand: Optional[str] = None,
        size: Optional[str] = None,
        unit_type: Optional[str] = None
    ) -> Dict:
        """
        Categorizza un prodotto usando OpenAI.
        
        Args:
            canonical_name: Nome prodotto normalizzato
            brand: Brand del prodotto
            size: Dimensione/peso del prodotto
            unit_type: Tipo unità (kg, l, pz, ecc.)
            
        Returns:
            Dict con category, subcategory, confidence
        """
        try:
            # Costruisci descrizione prodotto
            product_desc = self._build_product_description(
                canonical_name, brand, size, unit_type
            )
            
            # System prompt per categorizzazione
            system_prompt = self._create_categorization_prompt()
            
            # User prompt con dati prodotto
            user_prompt = f"Prodotto da categorizzare:\n{product_desc}"
            
            # Chiamata OpenAI con structured output
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            # Parse risposta
            content = response.choices[0].message.content
            result = json.loads(content)
            
            return {
                "success": True,
                "category": result.get("category", "Altro"),
                "subcategory": result.get("subcategory"),
                "confidence": result.get("confidence", 0.8),
                "reasoning": result.get("reasoning")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Categorization error: {str(e)}"
            }
    
    def _build_product_description(
        self,
        canonical_name: str,
        brand: Optional[str],
        size: Optional[str],
        unit_type: Optional[str]
    ) -> str:
        """Costruisce descrizione testuale prodotto per LLM"""
        parts = [f"Nome: {canonical_name}"]
        
        if brand:
            parts.append(f"Brand: {brand}")
        if size:
            parts.append(f"Dimensione: {size}")
        if unit_type:
            parts.append(f"Unità: {unit_type}")
        
        return "\n".join(parts)
    
    def _create_categorization_prompt(self) -> str:
        """Crea system prompt per categorizzazione"""
        return """Sei un esperto nella categorizzazione di prodotti alimentari e di supermercato.

Il tuo compito è analizzare un prodotto e assegnargli una categoria e sottocategoria appropriate.

CATEGORIE PRINCIPALI (scegli UNA):
- Frutta e Verdura
- Latticini e Uova
- Carne e Pesce
- Panetteria e Cereali
- Bevande
- Dolci e Snack
- Pasta, Riso e Legumi
- Condimenti e Spezie
- Surgelati
- Igiene Personale
- Pulizia Casa
- Altro

ISTRUZIONI:
1. Analizza attentamente nome, brand, dimensione del prodotto
2. Assegna la categoria più appropriata
3. Crea una sottocategoria specifica (es. per Latticini: Formaggi, Yogurt, Latte, ecc.)
4. Indica il livello di confidenza (0.0 - 1.0)
5. Spiega brevemente il ragionamento

OUTPUT FORMATO JSON:
{
  "category": "Categoria principale",
  "subcategory": "Sottocategoria specifica (opzionale)",
  "confidence": 0.95,
  "reasoning": "Breve spiegazione della scelta"
}

ESEMPI:
- "Parmigiano Reggiano DOP 500g" → Latticini e Uova / Formaggi
- "Coca Cola 1.5L" → Bevande / Soft Drink
- "Pasta Barilla Penne 500g" → Pasta, Riso e Legumi / Pasta
- "Detersivo Dash 30 lavaggi" → Pulizia Casa / Detersivi Bucato

Sii preciso e coerente nelle tue categorizzazioni."""


# Instanza globale
categorization_service = CategorizationService()