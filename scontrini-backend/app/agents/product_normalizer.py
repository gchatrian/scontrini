"""
Product Normalizer Agent
Agente OpenAI che normalizza prodotti usando function calling
"""
import json
from typing import Dict, List, Optional
from openai import OpenAI
from app.config import settings
from app.agents.prompts import PRODUCT_NORMALIZER_SYSTEM_PROMPT
from app.agents.tools import TOOL_DEFINITIONS, execute_function, create_product_mapping
from app.services.supabase_service import supabase_service


class ProductNormalizerAgent:
    """Agente per normalizzazione prodotti con OpenAI"""
    
    def __init__(self):
        """Inizializza agente"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_iterations = 10  # Previeni loop infiniti
    
    def normalize_product(
        self,
        raw_product_name: str,
        store_name: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict:
        """
        Normalizza un singolo prodotto
        
        Args:
            raw_product_name: Nome grezzo dallo scontrino
            store_name: Nome negozio (per context)
            price: Prezzo (per context)
            
        Returns:
            Dict con:
                - success: bool
                - normalized_product_id: UUID del prodotto normalizzato
                - canonical_name: Nome canonico
                - created_new: bool (True se creato nuovo prodotto)
                - mapping_id: UUID del mapping creato
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
                    "from_cache": True
                }
            
            # Crea messaggio per agente
            user_message = self._create_user_message(
                raw_product_name, 
                store_name, 
                price
            )
            
            # Esegui agent loop con function calling
            result = self._run_agent_loop(user_message)
            
            if not result["success"]:
                return result
            
            # Crea mapping raw_name → normalized_product
            mapping = create_product_mapping(
                raw_name=raw_product_name,
                normalized_product_id=result["normalized_product_id"],
                store_name=store_name,
                confidence_score=result.get("confidence", 0.9)
            )
            
            result["mapping_id"] = mapping.get("mapping", {}).get("id")
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Normalization error: {str(e)}"
            }
    
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
    
    def _create_user_message(
        self, 
        raw_name: str, 
        store_name: Optional[str], 
        price: Optional[float]
    ) -> str:
        """Crea messaggio user per agente"""
        context = []
        
        if store_name:
            context.append(f"Negozio: {store_name}")
        
        if price:
            context.append(f"Prezzo: €{price:.2f}")
        
        context_str = " | ".join(context) if context else ""
        
        message = f"""Normalizza questo prodotto:

Nome grezzo: "{raw_name}"
{f"Contesto: {context_str}" if context_str else ""}

Segui il processo:
1. Cerca se esiste già (find_existing_product)
2. Se non esiste e non lo riconosci, cerca online (search_product_online)
3. Crea/ritorna prodotto normalizzato

Rispondi in formato JSON:
{{
  "normalized_product_id": "uuid-del-prodotto",
  "canonical_name": "Nome Normalizzato",
  "created_new": true/false,
  "confidence": 0.95
}}"""
        
        return message
    
    def _run_agent_loop(self, user_message: str) -> Dict:
        """
        Esegue loop di function calling con OpenAI
        
        Returns:
            Dict con risultato normalizzazione
        """
        messages = [
            {"role": "system", "content": PRODUCT_NORMALIZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Chiama OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.1
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
                    
                    print(f"  🔧 Agent calling: {function_name}({arguments})")
                    
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
                        "error": f"Failed to parse agent response: {message.content}"
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


# Istanza globale dell'agente
product_normalizer_agent = ProductNormalizerAgent()
