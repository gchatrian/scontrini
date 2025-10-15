"""
Store Service - Gestione negozi normalizzati
Logica intelligente per find/create stores ed evitare duplicati
"""
from typing import Dict, Optional, List
from difflib import SequenceMatcher
from app.services.supabase_service import supabase_service


class StoreService:
    """Servizio per gestione stores"""
    
    # ID del mock store di default
    MOCK_STORE_ID = "00000000-0000-0000-0000-000000000000"
    
    # Soglia similarità per matching (0-1)
    SIMILARITY_THRESHOLD = 0.85
    
    def __init__(self):
        """Inizializza service"""
        pass
    
    def find_or_create_store(
        self,
        store_data: Dict
    ) -> Dict:
        """
        Trova store esistente o crea nuovo
        
        Args:
            store_data: Dict con dati estratti da scontrino:
                - name: Nome negozio
                - company_name: Ragione sociale (opzionale)
                - vat_number: P.IVA (opzionale)
                - address_full: Indirizzo completo
                - address_street: Via
                - address_city: Città
                - address_province: Provincia
                - address_postal_code: CAP
                
        Returns:
            Dict con:
                - success: bool
                - store_id: UUID store
                - store: Dict completo store
                - created_new: bool (True se creato nuovo)
                - matched_by: str (come è stato trovato)
        """
        try:
            # Estrai e normalizza nome
            raw_name = store_data.get("name")
            
            # Se non c'è nome, usa mock store
            if not raw_name or len(raw_name.strip()) < 2:
                return self._get_mock_store()
            
            normalized_name = self._normalize_store_name(raw_name)
            
            # STEP 1: Cerca per P.IVA (match più affidabile)
            if store_data.get("vat_number"):
                store = self._find_by_vat_number(
                    store_data["vat_number"],
                    store_data.get("address_city")
                )
                if store:
                    return {
                        "success": True,
                        "store_id": store["id"],
                        "store": store,
                        "created_new": False,
                        "matched_by": "vat_number"
                    }
            
            # STEP 2: Cerca per nome + città (match esatto)
            if store_data.get("address_city"):
                store = self._find_by_name_and_city(
                    normalized_name,
                    store_data["address_city"]
                )
                if store:
                    return {
                        "success": True,
                        "store_id": store["id"],
                        "store": store,
                        "created_new": False,
                        "matched_by": "name_city"
                    }
            
            # STEP 3: Cerca per similarità nome (fuzzy matching)
            store = self._find_by_similarity(normalized_name)
            if store:
                return {
                    "success": True,
                    "store_id": store["id"],
                    "store": store,
                    "created_new": False,
                    "matched_by": "similarity"
                }
            
            # STEP 4: Nessun match trovato - crea nuovo store
            new_store = self._create_new_store(store_data, normalized_name)
            
            if new_store:
                return {
                    "success": True,
                    "store_id": new_store["id"],
                    "store": new_store,
                    "created_new": True,
                    "matched_by": "created"
                }
            
            # Fallback: usa mock store se creazione fallisce
            return self._get_mock_store()
            
        except Exception as e:
            print(f"Error in find_or_create_store: {e}")
            # Fallback a mock store in caso di errore
            return self._get_mock_store()
    
    def _get_mock_store(self) -> Dict:
        """Ritorna mock store per dati mancanti"""
        mock_store = supabase_service.get_store(self.MOCK_STORE_ID)
        
        return {
            "success": True,
            "store_id": self.MOCK_STORE_ID,
            "store": mock_store,
            "created_new": False,
            "matched_by": "mock"
        }
    
    def _normalize_store_name(self, name: str) -> str:
        """
        Normalizza nome negozio per matching
        
        Examples:
            "ESSELUNGA" → "esselunga"
            "Esselunga  SPA" → "esselunga spa"
            "COOP - Firenze" → "coop firenze"
        """
        if not name:
            return ""
        
        # Lowercase
        normalized = name.lower().strip()
        
        # Rimuovi punteggiatura comune
        normalized = normalized.replace(".", "").replace(",", "")
        
        # Rimuovi suffissi societari comuni
        for suffix in [" spa", " s.p.a", " srl", " s.r.l", " snc"]:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        # Normalizza spazi
        normalized = " ".join(normalized.split())
        
        return normalized
    
    def _find_by_vat_number(
        self, 
        vat_number: str, 
        city: Optional[str] = None
    ) -> Optional[Dict]:
        """Cerca store per P.IVA"""
        try:
            # Query semplice per P.IVA
            response = supabase_service.client.table("stores")\
                .select("*")\
                .eq("vat_number", vat_number)\
                .eq("is_mock", False)\
                .execute()
            
            if not response.data:
                return None
            
            # Se specificata città, preferisci stesso negozio in stessa città
            if city:
                city_normalized = city.lower().strip()
                for store in response.data:
                    if store.get("address_city"):
                        store_city = store["address_city"].lower().strip()
                        if store_city == city_normalized:
                            print(f"Found by VAT+city: {vat_number} in {city}")
                            return store
            
            # Altrimenti ritorna il primo
            print(f"Found by VAT: {vat_number}")
            return response.data[0]
            
        except Exception as e:
            print(f"Error in _find_by_vat_number: {e}")
            return None
    
    def _find_by_name_and_city(
        self, 
        normalized_name: str, 
        city: str
    ) -> Optional[Dict]:
        """Cerca store per nome normalizzato + città"""
        try:
            # Normalizza città
            city_normalized = city.lower().strip()
            
            # Cerca tutti gli stores non-mock in quella città
            # Query semplificata senza ILIKE pattern matching
            response = supabase_service.client.table("stores")\
                .select("*")\
                .eq("is_mock", False)\
                .execute()
            
            # Filtra in Python per nome + città
            for store in response.data:
                store_name = self._normalize_store_name(store.get("name", ""))
                
                # Match nome (esatto o contenuto)
                name_match = (
                    normalized_name == store_name or
                    normalized_name in store_name or
                    store_name in normalized_name
                )
                
                # Match città (case insensitive)
                city_match = False
                if store.get("address_city"):
                    store_city = store["address_city"].lower().strip()
                    city_match = (store_city == city_normalized)
                
                # Se match su entrambi
                if name_match and city_match:
                    print(f"Found by name+city: '{normalized_name}' in '{city}' → {store['name']}")
                    return store
            
            return None
            
        except Exception as e:
            print(f"Error in _find_by_name_and_city: {e}")
            return None
    
    def _find_by_similarity(self, normalized_name: str) -> Optional[Dict]:
        """
        Cerca store per similarità nome (fuzzy matching)
        Usa SequenceMatcher per calcolare similarità
        """
        try:
            # Recupera tutti gli stores non-mock (query semplice)
            response = supabase_service.client.table("stores")\
                .select("*")\
                .eq("is_mock", False)\
                .limit(100)\
                .execute()
            
            if not response.data:
                return None
            
            best_match = None
            best_score = 0.0
            
            for store in response.data:
                store_name = self._normalize_store_name(store.get("name", ""))
                
                if not store_name:
                    continue
                
                # Calcola similarità
                similarity = SequenceMatcher(
                    None, 
                    normalized_name, 
                    store_name
                ).ratio()
                
                # Se similarità alta e migliore del precedente
                if similarity > best_score and similarity >= self.SIMILARITY_THRESHOLD:
                    best_score = similarity
                    best_match = store
            
            if best_match:
                print(f"Found by similarity: '{normalized_name}' → '{best_match['name']}' (score: {best_score:.2f})")
            
            return best_match
            
        except Exception as e:
            print(f"Error in _find_by_similarity: {e}")
            return None
    
    def _create_new_store(
        self, 
        store_data: Dict, 
        normalized_name: str
    ) -> Optional[Dict]:
        """Crea nuovo store nel database"""
        try:
            # Determina chain dal nome
            chain = self._extract_chain_from_name(normalized_name)
            
            # Crea branch_name descrittivo
            branch_name = normalized_name.title()
            if store_data.get("address_street"):
                branch_name += f" - {store_data['address_street']}"
            elif store_data.get("address_city"):
                branch_name += f" - {store_data['address_city']}"
            
            # Prepara dati
            new_store_data = {
                "name": normalized_name.title(),  # Proper case
                "chain": chain,
                "branch_name": branch_name,
                "vat_number": store_data.get("vat_number"),
                "company_name": store_data.get("company_name"),
                "address_full": store_data.get("address_full"),
                "address_street": store_data.get("address_street"),
                "address_city": store_data.get("address_city"),
                "address_province": store_data.get("address_province"),
                "address_postal_code": store_data.get("address_postal_code"),
                "store_type": "supermarket",  # Default
                "is_mock": False
            }
            
            # Crea in database
            response = supabase_service.client.table("stores")\
                .insert(new_store_data)\
                .execute()
            
            if response.data:
                print(f"Created new store: {normalized_name.title()}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            print(f"Error in _create_new_store: {e}")
            return None
    
    def _extract_chain_from_name(self, normalized_name: str) -> str:
        """
        Estrae nome catena dal nome normalizzato
        
        Examples:
            "esselunga via roma" → "Esselunga"
            "coop firenze" → "Coop"
            "bennet" → "Bennet"
        """
        # Catene comuni italiane
        chains = [
            "esselunga", "coop", "conad", "carrefour", 
            "lidl", "eurospin", "md", "penny", "iper",
            "bennet", "pam", "simply", "tigros", "famila"
        ]
        
        # Cerca se il nome contiene una catena conosciuta
        for chain in chains:
            if chain in normalized_name:
                return chain.title()
        
        # Fallback: usa prima parola del nome
        first_word = normalized_name.split()[0] if normalized_name else "Sconosciuto"
        return first_word.title()
    
    def update_store_statistics(self, store_id: str) -> bool:
        """
        Aggiorna statistiche store (total_receipts, avg_amount, etc.)
        Da chiamare periodicamente o dopo batch di receipts
        """
        try:
            # Calcola statistiche
            receipts_response = supabase_service.client.table("receipts")\
                .select("total_amount, receipt_date")\
                .eq("store_id", store_id)\
                .execute()
            
            receipts = receipts_response.data
            
            if not receipts:
                return True
            
            # Calcola
            total_receipts = len(receipts)
            
            amounts = [r["total_amount"] for r in receipts if r.get("total_amount")]
            avg_amount = sum(amounts) / len(amounts) if amounts else None
            
            dates = [r["receipt_date"] for r in receipts if r.get("receipt_date")]
            last_date = max(dates) if dates else None
            
            # Aggiorna
            supabase_service.client.table("stores")\
                .update({
                    "total_receipts": total_receipts,
                    "avg_receipt_amount": avg_amount,
                    "last_receipt_date": last_date
                })\
                .eq("id", store_id)\
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error updating store statistics: {e}")
            return False


# Istanza globale
store_service = StoreService()
