"""
Product Normalizer Agent - Single Step
Agente OpenAI che normalizza prodotti con un unico step LLM + function-calling
"""
import json
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from app.config import settings
from app.agents.prompts import PRODUCT_IDENTIFICATION_PROMPT, PRODUCT_VALIDATION_PROMPT
from app.agents.tools import TOOL_DEFINITIONS, execute_function, create_product_mapping
from app.services.supabase_service import supabase_service


class ProductNormalizerAgent:
    """Agente per normalizzazione prodotti con single-step LLM"""
    
    def __init__(self):
        """Inizializza agente"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        # Temperature specifiche per ogni fase
        self.temperature_normalizer = settings.OPENAI_TEMPERATURE_NORMALIZER
        self.temperature_validator = settings.OPENAI_TEMPERATURE_VALIDATOR
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
                print(
                    "🟢 Cache hit | canonical='{cn}' | id={id}".format(
                        cn=existing_mapping.get("canonical_name"),
                        id=existing_mapping["normalized_product_id"]
                    )
                )
                # Ritorna TUTTI i dettagli del prodotto normalizzato
                return {
                    "success": True,
                    "normalized_product_id": existing_mapping["normalized_product_id"],
                    "canonical_name": existing_mapping.get("canonical_name"),
                    "brand": existing_mapping.get("brand"),
                    "category": existing_mapping.get("category"),
                    "subcategory": existing_mapping.get("subcategory"),
                    "size": existing_mapping.get("size"),
                    "unit_type": existing_mapping.get("unit_type"),
                    "tags": existing_mapping.get("tags", []),
                    "created_new": False,
                    "from_cache": True,
                    "confidence": 1.0
                }
            
            print("🟡 Cache miss → invoking LLM: identification → validation…")
            # Step 1: Identificazione (usa temperature_normalizer)
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
            
            # Step 2: Validazione (usa temperature_validator)
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
            
            # Crea mapping
            mapping_result = create_product_mapping(
                raw_name=raw_product_name,
                normalized_product_id=identification_result["normalized_product_id"],
                store_name=store_name,
                confidence_score=final_confidence,
                requires_manual_review=pending_review
            )
            
            if not mapping_result["success"]:
                print(f"⚠️ Warning: Failed to create mapping: {mapping_result.get('error')}")
            
            return {
                "success": True,
                "normalized_product_id": identification_result["normalized_product_id"],
                "canonical_name": identification_result.get("canonical_name"),
                "brand": identification_result.get("brand"),
                "category": identification_result.get("category"),
                "subcategory": identification_result.get("subcategory"),
                "size": identification_result.get("size"),
                "unit_type": identification_result.get("unit_type"),
                "tags": identification_result.get("tags", []),
                "created_new": identification_result.get("created_new", False),
                "from_cache": False,
                "confidence": final_confidence,
                "requires_manual_review": pending_review
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Normalization error: {str(e)}"
            }
    
    def _identify_product(
        self,
        raw_product_name: str,
        store_name: Optional[str],
        price: Optional[float]
    ) -> Dict:
        """
        Identifica prodotto usando LLM con function calling.
        Usa OPENAI_TEMPERATURE_NORMALIZER.
        """
        user_message = self._build_user_message(
            raw_product_name, 
            store_name, 
            price
        )
        
        return self._run_identification_loop(user_message)
    
    def _build_user_message(
        self,
        raw_name: str,
        store_name: Optional[str],
        price: Optional[float]
    ) -> str:
        """Costruisce messaggio utente per LLM"""
        message = f"RAW: '{raw_name}'"
        
        if store_name:
            message += f" | STORE: '{store_name}'"
        if price:
            message += f" | PRICE: €{price:.2f}"
        
        message += """

TASK:
- Estrai BRAND (se presente), PRODOTTO, FORMATO.
- Se uno tra BRAND o PRODOTTO è incerto, parti da quello più certo per vincolare la ricerca dell'altro (es. se PRODOTTO=Acqua Frizzante, limita i brand plausibili).
- Non esiste un mapping per questo RAW: prova PRIMA a riusare un prodotto esistente (find_existing_product) e SOLO se non trovato crea un nuovo prodotto (create_normalized_product).
- Rispondi SOLO con JSON finale (niente testo extra)."""
        
        return message
    
    def _run_identification_loop(self, user_message: str) -> Dict:
        """
        Esegue loop di function calling per identificazione prodotto.
        Usa OPENAI_TEMPERATURE_NORMALIZER.
        
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
            
            # Chiama OpenAI con function tools - USA temperature_normalizer
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=self.temperature_normalizer  # Temperature specifica
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
        """
        Seconda chiamata LLM: valida il risultato e produce confidence/pending_review.
        Usa OPENAI_TEMPERATURE_VALIDATOR.
        """
        messages = [
            {"role": "system", "content": PRODUCT_VALIDATION_PROMPT},
            {"role": "user", "content": json.dumps({
                "raw": raw_name,
                "identified": identified
            })}
        ]
        try:
            # USA temperature_validator per validazione
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature_validator,  # Temperature specifica
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
                .select(
                    "*, normalized_products(canonical_name, brand, category, subcategory, size, unit_type, tags)"
                )\
                .eq("raw_name", raw_name)
            
            if store_name:
                query = query.eq("store_name", store_name)
            
            response = query.execute()
            
            if response.data and len(response.data) > 0:
                mapping = response.data[0]
                normalized_product = mapping.get("normalized_products")
                
                if normalized_product:
                    return {
                        "normalized_product_id": mapping["normalized_product_id"],
                        "canonical_name": normalized_product.get("canonical_name"),
                        "brand": normalized_product.get("brand"),
                        "category": normalized_product.get("category"),
                        "subcategory": normalized_product.get("subcategory"),
                        "size": normalized_product.get("size"),
                        "unit_type": normalized_product.get("unit_type"),
                        "tags": normalized_product.get("tags", [])
                    }
            
            return None
            
        except Exception as e:
            print(f"Error checking existing mapping: {str(e)}")
            return None


# Instanza globale
product_normalizer_agent = ProductNormalizerAgent()