"""
Product Normalizer Agent - Single Step
Agente OpenAI che normalizza prodotti con un unico step LLM + function-calling
"""
import json
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from app.config import settings
from app.agents.prompts import SINGLE_STEP_PRODUCT_NORMALIZATION_PROMPT, PRODUCT_IDENTIFICATION_PROMPT, PRODUCT_VALIDATION_PROMPT
from app.agents.tools import TOOL_DEFINITIONS, execute_function, create_product_mapping
from app.services.supabase_service import supabase_service


class ProductNormalizerAgent:
    """Agente per normalizzazione prodotti con single-step LLM"""
    
    def __init__(self):
        """Inizializza agente"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.temperature = 0.7
        self.max_iterations = 10
    
    def normalize_product(
        self,
        raw_product_name: str,
        store_name: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict:
        """
        Normalizza un singolo prodotto usando un unico step LLM con function-calling.
        
        Args:
            raw_product_name: Nome grezzo dallo scontrino
            store_name: Nome negozio (per context)
            price: Prezzo (per context)
            
        Returns:
            Dict con risultati normalizzazione
        """
        try:
            print(f"🔎 Normalization start | raw='{raw_product_name}' | store='{store_name}' | price={price}")
            # Controlla se esiste già mapping per questo raw_name
            existing_mapping = self._check_existing_mapping(
                raw_product_name, 
                store_name
            )
            
            if existing_mapping:
                print(f"🟢 Cache hit | canonical='{existing_mapping.get('canonical_name')}' | id={existing_mapping['normalized_product_id']}")
                return {
                    "success": True,
                    "normalized_product_id": existing_mapping["normalized_product_id"],
                    "canonical_name": existing_mapping.get("canonical_name"),
                    "created_new": False,
                    "from_cache": True,
                    "confidence": 1.0
                }
            
            print("🟡 Cache miss → invoking LLM: identification → validation…")
            # Step 1: Identificazione (senza confidenza/review)
            identification_result = self._identify_product(
                raw_product_name,
                store_name,
                price
            )
            
            if not identification_result["success"]:
                print(f"🔴 LLM normalization failed: {identification_result.get('error')}")
                return {
                    "success": False,
                    "error": f"Step 2 failed: {identification_result.get('error')}"
                }
            
            # Step 2: Validazione (confidence + pending_review)
            validation_outcome = self._validate_identification(
                raw_name=raw_product_name,
                identified={
                    "canonical_name": identification_result.get("canonical_name"),
                    "brand": identification_result.get("brand"),
                    "category": identification_result.get("category"),
                    "subcategory": identification_result.get("subcategory"),
                    "size": identification_result.get("size"),
                    "unit_type": identification_result.get("unit_type"),
                    "notes": identification_result.get("identification_notes")
                }
            )
            final_confidence = float(validation_outcome.get("confidence", 0.5))
            pending_review = bool(validation_outcome.get("pending_review"))
            print(
                "✅ LLM result | canonical='{cn}' | brand='{br}' | cat='{cat}' | size='{sz}' | conf={cf:.2f} | pending_review={pr}".format(
                    cn=identification_result.get("canonical_name"),
                    br=identification_result.get("brand"),
                    cat=identification_result.get("category"),
                    sz=identification_result.get("size"),
                    cf=final_confidence,
                    pr=pending_review
                )
            )
            # Log esplicito della confidence per audit
            print(f"📊 Product normalization confidence: {final_confidence:.2f}")
            
            result = {
                "success": True,
                "normalized_product_id": identification_result["normalized_product_id"],
                "canonical_name": identification_result["canonical_name"],
                "created_new": identification_result.get("created_new", False),
                "confidence": final_confidence,
                "brand": identification_result.get("brand"),
                "category": identification_result.get("category"),
                "subcategory": identification_result.get("subcategory"),
                "size": identification_result.get("size"),
                "unit_type": identification_result.get("unit_type"),
                "identification_notes": identification_result.get("identification_notes"),
                "pending_review": pending_review
            }
            
            # Crea mapping raw_name → normalized_product
            mapping = create_product_mapping(
                raw_name=raw_product_name,
                normalized_product_id=result["normalized_product_id"],
                store_name=store_name,
                confidence_score=final_confidence,
                requires_manual_review=pending_review
            )
            
            result["mapping_id"] = mapping.get("mapping", {}).get("id")
            if mapping.get("success"):
                print(f"🧩 Mapping created | id={result.get('mapping_id')} | requires_manual_review={pending_review}")
            else:
                print(f"⚠️ Mapping not created: {mapping.get('error')}")

            # Aggiorna anche lo status del prodotto normalizzato per far emergere nella view
            try:
                if pending_review:
                    supabase_service.client.table("normalized_products")\
                        .update({"verification_status": "pending_review"})\
                        .eq("id", result["normalized_product_id"])\
                        .execute()
                else:
                    # Mantieni auto_verified se non pending
                    supabase_service.client.table("normalized_products")\
                        .update({"verification_status": "auto_verified"})\
                        .eq("id", result["normalized_product_id"])\
                        .execute()
            except Exception as e:
                print(f"⚠️ Failed to update normalized_products.verification_status: {e}")
            return result
            
        except Exception as e:
            print(f"💥 Normalization error: {str(e)}")
            return {
                "success": False,
                "error": f"Normalization error: {str(e)}"
            }
    
    def _identify_product(
        self,
        raw_name: str,
        store_name: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict:
        """
        Single-step: Identifica e normalizza il prodotto usando function-calling.
        """
        user_message = self._create_identification_message(
            raw_name=raw_name,
            store_name=store_name,
            price=price
        )
        return self._run_identification_loop(user_message)
    
    def _create_identification_message(
        self,
        raw_name: str,
        store_name: Optional[str],
        price: Optional[float]
    ) -> str:
        """Crea messaggio per single-step identificazione"""
        context_parts = []
        
        if store_name:
            context_parts.append(f"Negozio: {store_name}")
        
        if price:
            context_parts.append(f"Prezzo: €{price:.2f}")
        
        context_str = " | ".join(context_parts) if context_parts else "Nessun contesto aggiuntivo"
        
        message = f"""Identifica e normalizza questo prodotto in UN SOLO STEP:

RAW: "{raw_name}"
Contesto: {context_str}

Istruzioni:
- Interpreta abbreviazioni/nomi compressi presenti nel RAW.
- Estrai BRAND (se presente), PRODOTTO, FORMATO.
- Se uno tra BRAND o PRODOTTO è incerto, parti da quello più certo per vincolare la ricerca dell'altro (es. se PRODOTTO=Acqua Frizzante, limita i brand plausibili).
- Non esiste un mapping per questo RAW: prova PRIMA a riusare un prodotto esistente (find_existing_product) e SOLO se non trovato crea un nuovo prodotto (create_normalized_product).
- Rispondi SOLO con JSON finale (niente testo extra)."""
        
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
            print(f"🔁 LLM iteration #{iteration}")
            
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
                    print(f"  🔧 Tool call: {function_name} | args={arguments}")
                    
                    # Esegui funzione
                    function_result = execute_function(function_name, arguments)
                    print(f"  ✅ Tool result: success={function_result.get('success', False)}")
                    
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
                    print("🏁 LLM completed with final JSON response")
                    result["success"] = True
                    return result
                    
                except json.JSONDecodeError:
                    print("⚠️ Failed to parse LLM response as JSON")
                    return {
                        "success": False,
                        "error": f"Failed to parse response: {message.content}"
                    }
            
            # Nessun content e nessun tool call - errore
            print("⚠️ LLM returned neither tool_calls nor content")
            return {
                "success": False,
                "error": "Agent did not return valid response"
            }
        
        # Max iterations raggiunto
        return {
            "success": False,
            "error": f"Max iterations ({self.max_iterations}) reached"
        }

    def _validate_identification(self, raw_name: str, identified: Dict) -> Dict:
        """Seconda chiamata LLM: valida il risultato e produce confidence/pending_review"""
        messages = [
            {"role": "system", "content": PRODUCT_VALIDATION_PROMPT},
            {"role": "user", "content": json.dumps({
                "raw": raw_name,
                "identified": identified
            })}
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content.strip()
            return json.loads(content)
        except Exception as e:
            return {"confidence": 0.5, "pending_review": True, "validation_notes": f"validation_error: {str(e)}"}
    
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
