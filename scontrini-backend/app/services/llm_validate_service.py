"""
LLM Validate Service - Confidence scoring per mapping raw → prodotto normalizzato
"""
import json
import asyncio
from typing import Dict, Any
from openai import AsyncOpenAI
from app.config import settings


class LLMValidateService:
    """Servizio per validazione mapping e assegnazione confidence score tramite LLM"""

    def __init__(self):
        """Inizializza client OpenAI async"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.temperature = 0.1  # Molto bassa per scoring consistente

    async def validate_mapping(
        self,
        raw_name: str,
        selected_product: Dict[str, Any],
        hypothesis: str
    ) -> Dict[str, Any]:
        """
        Valida corrispondenza raw_name → prodotto selezionato e assegna confidence score

        Domanda: "Quanto è probabile che questa riga RAW corrisponda a questo prodotto normalizzato?"

        Args:
            raw_name: Nome grezzo originale da scontrino
            selected_product: Prodotto selezionato (da LLM Select o ipotesi)
            hypothesis: Ipotesi interpretata (contesto)

        Returns:
            {
                "confidence_score": float (0-1),
                "confidence_level": "high" | "medium" | "low",
                "needs_review": bool,
                "reasoning": str,
                "flags": {
                    "brand_mismatch": bool,
                    "size_uncertain": bool,
                    "ambiguous": bool
                }
            }
        """
        prompt = self._build_prompt(raw_name, selected_product, hypothesis)

        try:
            print(f"   [LLM VALIDATE] Calling OpenAI {self.model}...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": VALIDATE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            result = json.loads(content)

            confidence_score = float(result.get("confidence_score", 0.5))

            # Determina confidence level e needs_review
            if confidence_score >= 0.8:
                confidence_level = "high"
                needs_review = False
            elif confidence_score >= 0.5:
                confidence_level = "medium"
                needs_review = True
            else:
                confidence_level = "low"
                needs_review = True

            print(f"   [LLM VALIDATE] ✅ Confidence: {confidence_score:.2f} ({confidence_level}), review: {needs_review} (tokens: {response.usage.total_tokens})")

            return {
                "confidence_score": confidence_score,
                "confidence_level": confidence_level,
                "needs_review": needs_review,
                "reasoning": result.get("reasoning", ""),
                "flags": result.get("flags", {
                    "brand_mismatch": False,
                    "size_uncertain": False,
                    "ambiguous": False
                })
            }

        except Exception as e:
            print(f"❌ LLM Validate error: {str(e)}")
            # Fallback: confidence medio, richiede review
            return {
                "confidence_score": 0.5,
                "confidence_level": "medium",
                "needs_review": True,
                "reasoning": f"Fallback: errore validazione ({str(e)})",
                "flags": {
                    "brand_mismatch": False,
                    "size_uncertain": False,
                    "ambiguous": True
                }
            }

    def _build_prompt(
        self,
        raw_name: str,
        selected_product: Dict[str, Any],
        hypothesis: str
    ) -> str:
        """Costruisce prompt per LLM"""
        prompt = f'RAW SCONTRINO: "{raw_name}"\n'
        prompt += f'INTERPRETAZIONE: "{hypothesis}"\n\n'
        prompt += "PRODOTTO SELEZIONATO:\n"
        prompt += f"  Nome: {selected_product.get('canonical_name')}\n"

        if selected_product.get('brand'):
            prompt += f"  Brand: {selected_product['brand']}\n"
        if selected_product.get('category'):
            prompt += f"  Categoria: {selected_product['category']}\n"
        if selected_product.get('size'):
            prompt += f"  Formato: {selected_product['size']}"
            if selected_product.get('unit_type'):
                prompt += f" {selected_product['unit_type']}"
            prompt += "\n"

        return prompt


# System prompt per validazione
VALIDATE_SYSTEM_PROMPT = """Sei un esperto validatore di prodotti da supermercato. Il tuo compito è rispondere alla domanda:

**"Quanto è probabile che questa riga RAW di scontrino corrisponda a questo prodotto normalizzato?"**

**CRITERI DI VALUTAZIONE:**

1. **Brand Correspondence** (peso 35%):
   - Match esatto: alta confidence
   - Brand diverso ma plausibile (store brand vs marchio): media confidence
   - Brand completamente diverso: bassa confidence

2. **Product Type Match** (peso 40%):
   - Tipo prodotto corretto (acqua→acqua, tonno→tonno): essenziale
   - Tipo diverso: confidence molto bassa

3. **Size/Format Match** (peso 15%):
   - Size matches: boost confidence
   - Size ambigua o non specificata: neutro
   - Size completamente diversa: penalizza confidence

4. **Plausibility** (peso 10%):
   - Il mapping "ha senso" considerando negozio e contesto?
   - Abbreviazioni risolte correttamente?

**CONFIDENCE SCALE:**
- **0.9-1.0**: Match quasi certo, corrispondenza evidente
- **0.8-0.9**: Match molto probabile, piccole incertezze
- **0.6-0.8**: Match probabile, richiede review per conferma
- **0.4-0.6**: Match incerto, potrebbe essere corretto o no
- **0.0-0.4**: Match improbabile, probabilmente errato

**FLAGS:**
- `brand_mismatch`: true se brand non corrisponde
- `size_uncertain`: true se formato/dimensione ambiguo
- `ambiguous`: true se interpretazione generale è ambigua

**OUTPUT JSON:**
{
  "confidence_score": 0.85,
  "reasoning": "Brand Sant'Anna corrisponde a S.ANNA, tipo prodotto corretto (acqua frizzante), formato 1.5L matches. Unica incertezza: confezione da 6 non esplicitata nel canonical_name ma plausibile.",
  "flags": {
    "brand_mismatch": false,
    "size_uncertain": false,
    "ambiguous": false
  }
}

**IMPORTANTE:**
- Sii onesto: se il match è dubbio, assegna score basso
- Il reasoning deve spiegare il punteggio assegnato
- Considera che abbreviazioni e formati scontrino sono spesso criptici
- **SEVERO**: Se l'interpretazione contiene errori evidenti (es. "Pasta Cotta Acqua" che non ha senso), assegna confidence molto bassa (0.1-0.3)
- **SEVERO**: Se l'interpretazione non corrisponde al tipo di prodotto, assegna confidence bassa (0.2-0.4)
- **SEVERO**: Se l'interpretazione è confusa o incoerente, assegna confidence molto bassa (0.1-0.3)
"""


# Instanza globale
llm_validate_service = LLMValidateService()
