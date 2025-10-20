"""
AI Parser Service - Usa OpenAI per parsing intelligente scontrini
Molto più robusto e accurato delle regex
"""
import json
from typing import Dict, List, Optional
from openai import OpenAI
from app.config import settings
from datetime import datetime, date, time


class AIReceiptParser:
    """Parser intelligente con OpenAI GPT-4o-mini"""
    
    def __init__(self):
        """Inizializza client OpenAI"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        # Temperatura centralizzata da .env (OPENAI_TEMPERATURE)
        self.temperature = settings.OPENAI_TEMPERATURE
    
    def parse_receipt(self, ocr_text: str) -> Dict:
        """
        Analizza testo OCR usando OpenAI
        
        Args:
            ocr_text: Testo estratto dall'OCR
            
        Returns:
            Dict con dati strutturati dello scontrino
        """
        try:
            # Crea prompt per OpenAI
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(ocr_text)
            
            # Chiama OpenAI con structured output
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}  # Forza output JSON
            )
            
            # Estrai risposta
            content = response.choices[0].message.content
            parsed_data = json.loads(content)
            
            # Post-processing: converti stringhe in date/time
            result = self._post_process(parsed_data)
            result["success"] = True
            result["raw_text"] = ocr_text
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"AI Parsing error: {str(e)}",
                "raw_text": ocr_text
            }
    
    def _create_system_prompt(self) -> str:
        """Crea system prompt per OpenAI"""
        return """Sei un esperto nell'analizzare scontrini di supermercati italiani.

Il tuo compito è estrarre dati strutturati da testo OCR di scontrini.

ISTRUZIONI:
1. Analizza attentamente il testo dello scontrino
2. Estrai tutte le informazioni richieste
3. Se un dato non è presente, usa null
4. Sii intelligente: inferisci informazioni dal contesto
5. Per i prodotti, estrai solo righe che sono chiaramente prodotti acquistati
6. Ignora righe di intestazione, piè di pagina, pubblicità, etc.

OUTPUT FORMATO JSON:
{
  "store_name": "Nome supermercato (es. Esselunga, Coop, Bennet)",
  "company_name": "Ragione sociale completa se presente (es. 'Bennet S.p.A.')",
  "vat_number": "Partita IVA se presente (solo numeri, es. '07071700152')",
  "address_full": "Indirizzo completo come appare sullo scontrino",
  "address_street": "Via/Viale/Piazza con numero civico",
  "address_city": "Città",
  "address_province": "Provincia (sigla 2 lettere, es. 'MI', 'CO', 'RM')",
  "address_postal_code": "CAP se presente",
  "receipt_date": "Data in formato YYYY-MM-DD",
  "receipt_time": "Ora in formato HH:MM",
  "total_amount": 123.45,
  "payment_method": "contanti|carta|bancomat",
  "discount_amount": 10.50,
  "items": [
    {
      "raw_product_name": "COCA COLA 1.5L",
      "quantity": 1.0,
      "unit_price": 1.49,
      "total_price": 1.49
    }
  ]
}

REGOLE IMPORTANTI:
- Tutti i prezzi devono essere numeri float (es. 12.50, non "12,50")
- Le date devono essere YYYY-MM-DD
- Gli orari devono essere HH:MM
- P.IVA: estrai solo i numeri (es. "P.IVA: 12345678901" → "12345678901")
- Provincia: solo sigla (es. "Milano (MI)" → "MI")
- quantity, unit_price, total_price devono essere numeri
- Se non trovi un dato, usa null (non stringa vuota)
- Per i prodotti: estrai SOLO righe con nome prodotto + prezzo
- Ignora sconti, subtotali, righe promozionali nei prodotti
- raw_product_name deve contenere il nome come appare sullo scontrino
- Separa address_street (via + numero) da address_city"""
    
    def _create_user_prompt(self, ocr_text: str) -> str:
        """Crea user prompt con testo OCR"""
        return f"""Analizza questo scontrino ed estrai i dati in formato JSON:

```
{ocr_text}
```

Restituisci SOLO il JSON, senza altri commenti."""
    
    def _post_process(self, parsed_data: Dict) -> Dict:
        """Post-processa dati parsati (converti stringhe in date/time)"""
        result = parsed_data.copy()
        
        # Converti date string in date object
        if result.get("receipt_date"):
            try:
                result["receipt_date"] = datetime.strptime(
                    result["receipt_date"], 
                    "%Y-%m-%d"
                ).date()
            except:
                result["receipt_date"] = None
        
        # Converti time string in time object
        if result.get("receipt_time"):
            try:
                result["receipt_time"] = datetime.strptime(
                    result["receipt_time"], 
                    "%H:%M"
                ).time()
            except:
                result["receipt_time"] = None
        
        # Assicura che items sia una lista
        if not result.get("items"):
            result["items"] = []
        
        # Valida items (assicura che abbiano tutti i campi richiesti)
        validated_items = []
        for item in result.get("items", []):
            if self._validate_item(item):
                validated_items.append(item)
        
        result["items"] = validated_items
        
        return result
    
    def _validate_item(self, item: Dict) -> bool:
        """Valida che un item abbia tutti i campi necessari"""
        required_fields = ["raw_product_name", "total_price"]
        
        # Controlla campi obbligatori
        for field in required_fields:
            if field not in item or item[field] is None:
                return False
        
        # Assicura campi numerici
        try:
            item["quantity"] = float(item.get("quantity", 1.0))
            item["total_price"] = float(item["total_price"])
            
            # Calcola unit_price se mancante
            if not item.get("unit_price"):
                item["unit_price"] = item["total_price"] / item["quantity"]
            else:
                item["unit_price"] = float(item["unit_price"])
                
        except (ValueError, TypeError, ZeroDivisionError):
            return False
        
        # Nome prodotto deve essere significativo
        if len(item["raw_product_name"].strip()) < 2:
            return False
        
        return True
    
    def estimate_cost(self, ocr_text: str) -> float:
        """
        Stima costo chiamata OpenAI
        
        Returns:
            Costo stimato in USD
        """
        # GPT-4o-mini pricing (approssimativo):
        # Input: $0.15 / 1M tokens
        # Output: $0.60 / 1M tokens
        
        # Stima tokens (approssimativo: 1 token ≈ 4 caratteri)
        input_tokens = (len(self._create_system_prompt()) + len(ocr_text)) / 4
        output_tokens = 500  # JSON output tipico
        
        cost = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)
        return cost


# Istanza globale del parser AI
ai_receipt_parser = AIReceiptParser()
