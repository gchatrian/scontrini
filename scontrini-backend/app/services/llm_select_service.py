"""
LLM Select Service - Selezione best match tra candidati vector search
"""
import json
import asyncio
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI
from app.config import settings


class LLMSelectService:
    """Servizio per selezione prodotto migliore tra candidati tramite LLM"""

    def __init__(self):
        """Inizializza client OpenAI async"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.temperature = 0.2  # Bassa per scelta deterministica

    async def select_best_match(
        self,
        raw_name: str,
        hypothesis: str,
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Seleziona il prodotto più verosimile tra i candidati

        Args:
            raw_name: Nome grezzo originale da scontrino
            hypothesis: Ipotesi interpretata da LLM Interpret
            candidates: Lista prodotti candidati da vector search (max 5)

        Returns:
            {
                "success": bool,
                "selected_product_id": str,
                "selected_product": Dict,  # Prodotto scelto
                "reasoning": str
            }
        """
        if not candidates:
            # Nessun candidato: ritorna ipotesi come fallback
            return {
                "success": False,
                "error": "No candidates found",
                "fallback_hypothesis": hypothesis
            }

        prompt = self._build_prompt(raw_name, hypothesis, candidates)

        try:
            print(f"   [LLM SELECT] Calling OpenAI {self.model} with {len(candidates)} candidates...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SELECT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            result = json.loads(content)

            # Trova prodotto selezionato nella lista candidati
            selected_idx = result.get("selected_index", 0)
            if 0 <= selected_idx < len(candidates):
                selected_product = candidates[selected_idx]
            else:
                # Fallback al primo candidato
                selected_product = candidates[0]

            print(f"   [LLM SELECT] ✅ Selected index {selected_idx}: '{selected_product['canonical_name']}' (tokens: {response.usage.total_tokens})")

            return {
                "success": True,
                "selected_product_id": selected_product['product_id'],
                "selected_product": selected_product,
                "reasoning": result.get("reasoning", "")
            }

        except Exception as e:
            print(f"❌ LLM Select error: {str(e)}")
            # Fallback: ritorna primo candidato (più alto similarity score)
            return {
                "success": True,
                "selected_product_id": candidates[0]['product_id'],
                "selected_product": candidates[0],
                "reasoning": f"Fallback: errore selezione, scelto primo candidato ({str(e)})"
            }

    def _build_prompt(
        self,
        raw_name: str,
        hypothesis: str,
        candidates: List[Dict[str, Any]]
    ) -> str:
        """Costruisce prompt per LLM"""
        prompt = f'RAW SCONTRINO: "{raw_name}"\n'
        prompt += f'INTERPRETAZIONE: "{hypothesis}"\n\n'
        prompt += "CANDIDATI:\n"

        for idx, candidate in enumerate(candidates):
            prompt += f"{idx}. {candidate['canonical_name']}"
            if candidate.get('brand'):
                prompt += f" ({candidate['brand']})"
            if candidate.get('size'):
                prompt += f" - {candidate['size']}"
            if candidate.get('unit_type'):
                prompt += f" {candidate['unit_type']}"
            # Usa combined_score (o business_score se presente dopo reranking)
            score = candidate.get('business_score') or candidate.get('combined_score', 0.0)
            prompt += f" [score: {score:.3f}]\n"

        return prompt


# System prompt per selezione
SELECT_SYSTEM_PROMPT = """Sei un esperto di prodotti da supermercato. Il tuo compito è scegliere il prodotto più verosimile tra i candidati forniti.

**CRITERI DI SELEZIONE (in ordine di priorità):**

1. **Brand Match**: Se il raw name/interpretazione menziona un brand, privilegia prodotti con quel brand
   - Esempio: "S.ANNA" → candidati "Sant'Anna" hanno priorità

2. **Product Type Match**: Il tipo di prodotto deve corrispondere
   - Esempio: "TONNO" deve matchare prodotti categoria tonno/pesce, non pasta

3. **Size/Format Match**: Se dimensione/formato specificato, deve corrispondere
   - Esempio: "1.5L" deve matchare bottiglie 1.5L, non 500ml

4. **Similarity Score**: A parità di match, preferisci score più alto

5. **Context Clues**: Usa prezzo e negozio come indizi aggiuntivi
   - Prezzi molto diversi possono indicare prodotti diversi
   - Store brand vs marchio nazionale

**RAGIONAMENTO:**
- Spiega perché hai scelto quel prodotto specifico
- Menziona eventuali dubbi o ambiguità
- Se più candidati sono egualmente validi, scegli quello con similarity più alta

**OUTPUT JSON:**
{
  "selected_index": 0,  // Indice (0-based) del prodotto scelto
  "reasoning": "Brand Sant'Anna corrisponde a S.ANNA nel raw name, size 1.5L matches, similarity score alta (0.92)"
}

**IMPORTANTE:**
- Sii pragmatico: non serve match perfetto, basta il più verosimile
- Se tutti i candidati sono ugualmente improbabili, scegli comunque il meno peggio
"""


# Instanza globale
llm_select_service = LLMSelectService()
