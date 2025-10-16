"""
Product Normalizer Agent - Sistema a Due Step
Agente OpenAI che normalizza prodotti usando solo chiamate LLM
"""
import json
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from app.config import settings
from app.agents.prompts import (
    ABBREVIATION_EXPANSION_PROMPT,
    PRODUCT_IDENTIFICATION_PROMPT
)
from app.agents.tools import TOOL_DEFINITIONS, execute_function, create_product_mapping
from app.services.supabase_service import supabase_service


class ProductNormalizerAgent:
    """Agente per normalizzazione prodotti con sistema a due step"""
    
    def __init__(self):
        """Inizializza agente"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.temperature = 0.7  # Temperature per entrambi gli step
        self.max_iterations = 10  # Per function calling nello step 2
    
    def normalize_product(
        self,
        raw_product_name: str,
        store_name: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict:
        """
        Normalizza un singolo prodotto usando processo a due step
        
        Args:
            raw_product_name: Nome grezzo dallo scontrino
            store_name: Nome negozio (per context)
            price: Prezzo (per context)
            
        Returns:
            Dict con risultati normalizzazione
        """
        try:
            # Controlla se esiste già mapping per questo raw_name
            existing_mapping = self._check_existing_mapping(
                raw_product_name, 
                store_name
            )
            
            if existing_mapping:
                return {
                    "success": True,
                    "normalized_product_id": existing_mapping["normalized_product_id"],
                    "canonical_name": existing_mapping.get("canonical_name"),
                    "created_new": False,
                    "from_cache": True,
                    "confidence": 1.0
                }
            
            # =====================================
            # STEP 1: Espansione Abbreviazioni
            # =====================================
            expansion_result = self._expand_abbreviations(
                raw_product_name, 
                store_name
            )
            
            if not expansion_result["success"]:
                return {
                    "success": False,
                    "error": f"Step 1 failed: {expansion_result.get('error')}"
                }
            
            expanded_text = expansion_result.get("expanded_text", raw_product_name)
            expansion_confidence = expansion_result.get("confidence", 0.5)
            
            print(f"  📝 Step 1 - Espansione: '{raw_product_name}' → '{expanded_text}' (confidence: {expansion_confidence:.2f})")
            
            # =====================================
            # STEP 2: Identificazione Prodotto
            # =====================================
            identification_result = self._identify_product(
                raw_product_name,
                expanded_text,
                store_name,
                price
            )
            
            if not identification_result["success"]:
                return {
                    "success": False,
                    "error": f"Step 2 failed: {identification_result.get('error')}"
                }
            
            identification_confidence = identification_result.get("confidence", 0.5)
            
            # Calcola confidence finale (media pesata)
            final_confidence = (0.3 * expansion_confidence) + (0.7 * identification_confidence)
            
            result = {
                "success": True,
                "normalized_product_id": identification_result["normalized_product_id"],
                "canonical_name": identification_result["canonical_name"],
                "created_new": identification_result.get("created_new", False),
                "confidence": final_confidence,
                "expansion_applied": expanded_text != raw_product_name,
                "expanded_text": expanded_text if expanded_text != raw_product_name else None
            }
            
            # Crea mapping raw_name → normalized_product
            mapping = create_product_mapping(
                raw_name=raw_product_name,
                normalized_product_id=result["normalized_product_id"],
                store_name=store_name,
                confidence_score=final_confidence
            )
            
            result["mapping_id"] = mapping.get("mapping", {}).get("id")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Normalization error: {str(e)}"
            }
    
    def _expand_abbreviations(
        self,
        raw_text: str,
        store_name: Optional[str] = None
    ) -> Dict:
        """
        Step 1: Espande le abbreviazioni nel testo grezzo
        
        Returns:
            Dict con testo espanso e confidence
        """
        try:
            # Costruisci messaggio con contesto
            context = f"Negozio: {store_name}" if store_name else "Negozio: non specificato"
            
            user_message = f"""Espandi le abbreviazioni in questo testo da scontrino:

Testo grezzo: "{raw_text}"
Contesto: {context}

Analizza e ricostruisci le abbreviazioni presenti."""
            
            # Chiamata LLM per espansione
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ABBREVIATION_EXPANSION_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                
                result = json.loads(content)
                result["success"] = True
                return result
                
            except json.JSONDecodeError:
                # Se non riesce a parsare, ritorna il testo originale
                return {
                    "success": True,
                    "expanded_text": raw_text,
                    "confidence": 0.3,
                    "error": "Failed to parse expansion"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "expanded_text": raw_text,
                "confidence": 0.0
            }
    
    def _identify_product(
        self,
        raw_name: str,
        expanded_name: str,
        store_name: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict:
        """
        Step 2: Identifica e normalizza il prodotto usando function calling
        
        Returns:
            Dict con prodotto normalizzato
        """
        # Crea messaggio per l'agente
        user_message = self._create_identification_message(
            raw_name,
            expanded_name,
            store_name,
            price
        )
        
        # Esegui loop con function calling
        return self._run_identification_loop(user_message)
    
    def _create_identification_message(
        self,
        raw_name: str,
        expanded_name: str,
        store_name: Optional[str],
        price: Optional[float]
    ) -> str:
        """Crea messaggio per step 2 di identificazione"""
        context_parts = []
        
        if store_name:
            context_parts.append(f"Negozio: {store_name}")
        
        if price:
            context_parts.append(f"Prezzo: €{price:.2f}")
        
        context_str = " | ".join(context_parts) if context_parts else "Nessun contesto aggiuntivo"
        
        message = f"""Identifica e normalizza questo prodotto:

Nome grezzo originale: "{raw_name}"
Nome con abbreviazioni espanse: "{expanded_name}"
Contesto: {context_str}

Processo da seguire:
1. Cerca prima se esiste già nel database (find_existing_product)
2. Se non trovato, crea nuovo prodotto normalizzato (create_normalized_product)

Fornisci il risultato finale in formato JSON."""
        
        return message
    
    def _run_identification_loop(self, user_message: str) -> Dict:
        """
        Esegue loop di function calling per identificazione prodotto
        
        Returns:
            Dict con risultato identificazione
        """
        messages = [
            {"role": "system", "content": PRODUCT_IDENTIFICATION_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Chiama OpenAI con function tools
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=self.temperature
            )
            
            message = response.choices[0].message
            
            # Se ha chiamato function tools
            if message.tool_calls:
                # Aggiungi risposta assistant ai messaggi
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in message.tool_calls
                    ]
                })
                
                # Esegui ogni function call
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    print(f"  🔧 Step 2 - Calling: {function_name}")
                    
                    # Esegui funzione
                    function_result = execute_function(function_name, arguments)
                    
                    print(f"  ✅ Result: {function_result.get('success', False)}")
                    
                    # Aggiungi risultato ai messaggi
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(function_result)
                    })
                
                # Continua loop - l'agent processerà i risultati
                continue
            
            # Se non ha chiamato tools, ha finito
            if message.content:
                try:
                    # Cerca JSON nella risposta
                    content = message.content.strip()
                    
                    # Rimuovi markdown code blocks se presenti
                    if content.startswith("```"):
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]
                    
                    result = json.loads(content)
                    result["success"] = True
                    return result
                    
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": f"Failed to parse response: {message.content}"
                    }
            
            # Nessun content e nessun tool call - errore
            return {
                "success": False,
                "error": "Agent did not return valid response"
            }
        
        # Max iterations raggiunto
        return {
            "success": False,
            "error": f"Max iterations ({self.max_iterations}) reached"
        }
    
    def _check_existing_mapping(
        self, 
        raw_name: str, 
        store_name: Optional[str]
    ) -> Optional[Dict]:
        """Controlla se esiste già mapping per questo prodotto"""
        try:
            query = supabase_service.client.table("product_mappings")\
                .select("*, normalized_products(canonical_name)")\
                .eq("raw_name", raw_name)
            
            if store_name:
                query = query.eq("store_name", store_name)
            
            response = query.execute()
            
            if response.data:
                mapping = response.data[0]
                return {
                    "normalized_product_id": mapping["normalized_product_id"],
                    "canonical_name": mapping.get("normalized_products", {}).get("canonical_name")
                }
            
            return None
            
        except Exception:
            return None
    
    def normalize_products_batch(
        self,
        products: List[Dict],
        store_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Normalizza lista di prodotti
        
        Args:
            products: Lista di dict con raw_product_name, price
            store_name: Nome negozio
            
        Returns:
            Lista di risultati normalizzazione
        """
        results = []
        
        for product in products:
            result = self.normalize_product(
                raw_product_name=product.get("raw_product_name"),
                store_name=store_name,
                price=product.get("total_price")
            )
            
            result["original_product"] = product
            results.append(result)
        
        return results


# Istanza globale dell'agente
product_normalizer_agent = ProductNormalizerAgent()
