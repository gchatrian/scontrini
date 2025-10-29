"""
LLM Interpret Service - Espansione e interpretazione nomi prodotti grezzi
"""
import json
import asyncio
from typing import Dict, Optional, Any
from openai import AsyncOpenAI
from app.config import settings


class LLMInterpretService:
    """Servizio per interpretazione nomi prodotti grezzi tramite LLM"""

    def __init__(self):
        """Inizializza client OpenAI async"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.temperature = 0.3  # Bassa per output deterministico

    async def interpret_raw_name(
        self,
        raw_name: str,
        store_name: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Interpreta nome grezzo da scontrino espandendo abbreviazioni e riconoscendo brand

        Args:
            raw_name: Nome grezzo da scontrino (es. "AC.MINGAS.S.ANNA 1.5X6")
            store_name: Nome negozio per contesto (opzionale)
            price: Prezzo per contesto (opzionale)

        Returns:
            {
                "success": bool,
                "hypothesis": str,  # Ipotesi prodotto completo
                "brand": str | None,
                "product_type": str,
                "size": str | None,
                "reasoning": str  # Spiegazione interpretazione
            }
        """
        prompt = self._build_prompt(raw_name, store_name, price)

        try:
            print(f"   [LLM INTERPRET] Calling OpenAI {self.model}...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": INTERPRET_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            print(f"   [LLM INTERPRET] ✅ Success (tokens: {response.usage.total_tokens})")

            return {
                "success": True,
                **result
            }

        except Exception as e:
            print(f"❌ LLM Interpret error: {str(e)}")
            # Fallback: ritorna raw_name come ipotesi
            return {
                "success": True,
                "hypothesis": raw_name,
                "brand": None,
                "product_type": raw_name,
                "size": None,
                "unit_type": None,
                "category": "Alimentari",
                "subcategory": "generico",
                "tags": ["generico", "non-identificato"],
                "reasoning": f"Fallback: errore interpretazione ({str(e)})"
            }

    def _build_prompt(
        self,
        raw_name: str,
        store_name: Optional[str],
        price: Optional[float]
    ) -> str:
        """Costruisce prompt per LLM"""
        prompt = f'RAW: "{raw_name}"'

        if store_name:
            prompt += f'\nSTORE: "{store_name}"'
        if price:
            prompt += f'\nPRICE: €{price:.2f}'

        return prompt


# System prompt per interpretazione
INTERPRET_SYSTEM_PROMPT = """Sei un esperto di prodotti da supermercato italiani. Devi identificare e normalizzare un singolo prodotto partendo da una riga RAW di scontrino.

# CONTESTO E IPOTESI
- Una riga RAW contiene in genere due elementi principali: BRAND e PRODOTTO, oltre al FORMATO (quantità/volume/peso).
- La riga può contenere abbreviazioni o nomi compressi per risparmiare spazio (esempi: "LAT" → "LATTE"; rimozione spazi come "SANNA" per "SANT ANNA"; troncamenti, sigle, omissione vocali).

# STRATEGIA DI IDENTIFICAZIONE
1) Interpreta abbreviazioni e nomi compressi direttamente nel contesto grocery. Molti codici sono anche codifiche interne di cassa e NON sono brand.
2) Estrai i componenti: BRAND, PRODOTTO (tipo), FORMATO (es. 1.5L, 500g).
   - Per il campo SIZE: inserisci SOLO la quantità numerica (es. "1.5", "500", "2")
   - Per il campo UNIT_TYPE: inserisci SOLO l'unità di misura (es. "L", "g", "kg", "ml")
3) SOLO i prodotti frutta e verdura, gastronomia, macelleria, banco del pesce, panificio non hanno un brand per cui verrà usato un brand fittizio, che contiene il nome della catena del supermercato in cui è stato effettuato l'acquisto (ad esempio 'Bennet' e l'indicazione 'FRESCO')'. Tutti gli altri prodotti hanno un brand.
4) Se uno tra BRAND o PRODOTTO è incerto:
   - Parti dall'elemento con confidenza maggiore per vincolare la ricerca dell'altro.
   - Esempio: RAW = "SANNA ACQ FR" → PRODOTTO con confidenza alta = "Acqua Frizzante". Limita la ricerca del BRAND ai marchi che producono acqua frizzante; Inizia con i marchi il cui core business è acqua, se non trovi, o hai una confidence bassa, esplora altri marchi. "SANNA" è una abbreviazione del marchio "Sant'Anna", il cui core business è l'acqua minerale.
   - Esempio: RAW = "FAR BARILLA" → BRAND con confidenza alta = "Barille". Limita la ricerca del PRODOTTO ai prodotti di Barilla.
5) Fai particolarmente attenzione al FORMATO: se nella riga RAW compare qualcosa come '1.5Lx6', indica come formato '1.5L' e come quantità 6, calcolando il prezzo unitario come prezzo totale / quantità
6) Normalizza il nome canonico nel formato: "[Brand] [Prodotto] [Caratteristiche/Varianti] [Formato]".
7) Classifica in categoria/sottocategoria coerenti (es. Bevande → acqua; Alimentari; Freschi; Surgelati; Pulizia Casa; Igiene Personale; Non Alimentari).

# GENERAZIONE TAG
Genera tag che descrivono:
- Tipo di prodotto
- Ingredienti principali
- Caratteristiche dietetiche (es. bio, senza glutine, vegano)
- Fascia d'età target (se applicabile)
- Occasione d'uso (es. colazione, merenda, pranzo)

Restituisci SOLO un array JSON di tag in minuscolo, separati da virgola.
Esempio: ["frullato", "frutta", "yogurt", "bambini", "merenda", "pesca"]

**ESEMPI DI TAG PER CATEGORIA:**
- Bevande: ["acqua", "frizzante", "minerale", "bottiglia"]
- Latticini: ["yogurt", "latte", "probiotici", "colazione", "bambini"]
- Pasta: ["pasta", "grano", "pranzo", "cena", "italiana"]
- Snack: ["biscotti", "cioccolato", "merenda", "bambini", "dolce"]
- Frutta/Verdura: ["frutta", "fresco", "vitamine", "sano", "bambini"]
- Prodotti bio: ["biologico", "naturale", "senza-pesticidi", "sano"]
- Senza glutine: ["senza-glutine", "celiaci", "dietetico"]
- Vegano: ["vegano", "vegetale", "senza-latte", "senza-uova"]

**OUTPUT JSON:**
{
  "hypothesis": "descrizione prodotto completa e leggibile",
  "brand": "brand riconosciuto o null",
  "product_type": "categoria prodotto (acqua, latte, tonno, etc.)",
  "size": "formato/quantità estratta o null",
  "unit_type": "unità di misura (L, g, ml, etc.) o null",
  "category": "categoria principale (Bevande, Alimentari, Freschi, etc.)",
  "subcategory": "sottocategoria (acqua, pasta, formaggi, etc.)",
  "tags": ["acqua", "frizzante", "minerale", "bottiglia", "sant'anna"],
  "reasoning": "breve spiegazione dell'interpretazione"
}

**IMPORTANTE:**
- Se non sei sicuro, preferisci interpretazione generica a inventare dettagli
- Il reasoning deve spiegare i passaggi logici dell'interpretazione
- Mantieni il product_type generico (acqua, latte, pasta, etc.)
- **SEVERO**: Non inventare dettagli che non sono chiaramente visibili nel raw_name
- **SEVERO**: Se l'interpretazione non ha senso (es. "Pasta Cotta Acqua"), riconsidera l'interpretazione
- **SEVERO**: L'ipotesi deve essere plausibile e riconoscibile nel database prodotti
- **TAG**: Genera 4-8 tag specifici: tipo prodotto, ingredienti, caratteristiche dietetiche, fascia d'età, occasione d'uso
"""


# Instanza globale
llm_interpret_service = LLMInterpretService()
