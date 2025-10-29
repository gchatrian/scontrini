"""
Supabase Service - Gestisce operazioni database
"""
from typing import Dict, List, Optional
from supabase import create_client, Client
from app.config import settings
from datetime import date, time


class SupabaseService:
    """Servizio per operazioni Supabase"""
    
    def __init__(self):
        """Inizializza client Supabase"""
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY  # Usa service_role per bypass RLS
        )
    
    # ===================================
    # RECEIPTS
    # ===================================
    
    def create_receipt(
        self,
        household_id: str,
        uploaded_by: str,
        image_url: str,
        store_id: Optional[str] = None,
        store_name: Optional[str] = None,
        store_address: Optional[str] = None,
        receipt_date: Optional[date] = None,
        receipt_time: Optional[time] = None,
        total_amount: Optional[float] = None,
        payment_method: Optional[str] = None,
        discount_amount: Optional[float] = None,
        raw_ocr_text: Optional[str] = None,
        ocr_confidence: Optional[float] = None,
        processing_status: str = "pending"
    ) -> Dict:
        """Crea nuovo scontrino"""
        
        data = {
            "household_id": household_id,
            "uploaded_by": uploaded_by,
            "image_url": image_url,
            "store_id": store_id,
            "store_name": store_name,
            "store_address": store_address,
            "receipt_date": receipt_date.isoformat() if receipt_date else None,
            "receipt_time": receipt_time.isoformat() if receipt_time else None,
            "total_amount": total_amount,
            "payment_method": payment_method,
            "discount_amount": discount_amount,
            "raw_ocr_text": raw_ocr_text,
            "ocr_confidence": ocr_confidence,
            "processing_status": processing_status
        }
        
        response = self.client.table("receipts").insert(data).execute()
        return response.data[0] if response.data else None
    
    def update_receipt_status(
        self,
        receipt_id: str,
        status: str
    ) -> Dict:
        """Aggiorna stato processing scontrino"""
        
        response = self.client.table("receipts")\
            .update({"processing_status": status})\
            .eq("id", receipt_id)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_receipt(self, receipt_id: str) -> Optional[Dict]:
        """Ottieni scontrino per ID"""
        
        response = self.client.table("receipts")\
            .select("*")\
            .eq("id", receipt_id)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_receipts_by_household(
        self,
        household_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Ottieni scontrini di un household"""
        
        response = self.client.table("receipts")\
            .select("*")\
            .eq("household_id", household_id)\
            .order("receipt_date", desc=True)\
            .limit(limit)\
            .execute()
        
        return response.data
    
    # ===================================
    # RECEIPT ITEMS
    # ===================================
    
    def create_receipt_items(
        self,
        receipt_id: str,
        items: List[Dict]
    ) -> List[Dict]:
        """
        Crea items per uno scontrino
        
        Args:
            receipt_id: ID scontrino
            items: Lista di dict con: raw_product_name, quantity, unit_price, total_price, line_number
        """
        
        # Aggiungi receipt_id a ogni item
        items_data = []
        for idx, item in enumerate(items):
            items_data.append({
                "receipt_id": receipt_id,
                "raw_product_name": item["raw_product_name"],
                "quantity": item.get("quantity", 1),
                "unit_price": item.get("unit_price"),
                "total_price": item["total_price"],
                "line_number": item.get("line_number", idx + 1)
            })
        
        response = self.client.table("receipt_items").insert(items_data).execute()
        return response.data
    
    def get_receipt_items(self, receipt_id: str) -> List[Dict]:
        """Ottieni items di uno scontrino"""
        
        response = self.client.table("receipt_items")\
            .select("*")\
            .eq("receipt_id", receipt_id)\
            .order("line_number")\
            .execute()
        
        return response.data
    
    # ===================================
    # HOUSEHOLDS
    # ===================================
    
    def get_household(self, household_id: str) -> Optional[Dict]:
        """Ottieni household per ID"""
        
        response = self.client.table("households")\
            .select("*")\
            .eq("id", household_id)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_user_households(self, user_id: str) -> List[Dict]:
        """Ottieni tutti gli households di un utente"""
        
        response = self.client.table("household_members")\
            .select("households(*)")\
            .eq("user_id", user_id)\
            .execute()
        
        return [item["households"] for item in response.data]
    
    def create_household(
        self,
        name: str,
        owner_id: str
    ) -> Dict:
        """Crea nuovo household e aggiungi owner"""
        
        # Crea household
        household_response = self.client.table("households")\
            .insert({"name": name})\
            .execute()
        
        household = household_response.data[0]
        
        # Aggiungi owner come membro
        self.client.table("household_members").insert({
            "household_id": household["id"],
            "user_id": owner_id,
            "role": "owner"
        }).execute()
        
        return household
    
    # ===================================
    # NORMALIZED PRODUCTS (per Task 5)
    # ===================================
    
    def get_normalized_product(self, product_id: str) -> Optional[Dict]:
        """Ottieni prodotto normalizzato"""
        
        response = self.client.table("normalized_products")\
            .select("*")\
            .eq("id", product_id)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def search_normalized_products(
        self,
        search_term: str,
        limit: int = 10
    ) -> List[Dict]:
        """Cerca prodotti normalizzati"""
        
        response = self.client.table("normalized_products")\
            .select("*")\
            .ilike("canonical_name", f"%{search_term}%")\
            .limit(limit)\
            .execute()
        
        return response.data
    
    # ===================================
    # STORES
    # ===================================
    
    def get_store(self, store_id: str) -> Optional[Dict]:
        """Ottieni store per ID"""
        
        response = self.client.table("stores")\
            .select("*")\
            .eq("id", store_id)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_stores_by_household(self, household_id: str) -> List[Dict]:
        """Ottieni tutti gli stores usati da un household"""
        
        # Stores da receipts del household
        response = self.client.table("receipts")\
            .select("stores(*)")\
            .eq("household_id", household_id)\
            .execute()
        
        # Estrai stores unici
        stores_map = {}
        for item in response.data:
            if item.get("stores"):
                store = item["stores"]
                stores_map[store["id"]] = store
        
        return list(stores_map.values())
    
    def search_stores(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        """Cerca stores per nome"""
        
        response = self.client.table("stores")\
            .select("*")\
            .ilike("name", f"%{query}%")\
            .eq("is_mock", False)\
            .limit(limit)\
            .execute()
        
        return response.data
    """
    Aggiungi questo metodo alla classe SupabaseService in supabase_service.py
    Posizionarlo dopo i metodi NORMALIZED PRODUCTS
    """

    # ===================================
    # PURCHASE HISTORY
    # ===================================

    def create_purchase_history(
        self,
        household_id: str,
        receipt_id: str,
        receipt_item_id: str,
        normalized_product_id: Optional[str],
        purchase_date: date,
        store_id: Optional[str] = None,
        quantity: Optional[float] = None,
        unit_price: Optional[float] = None,
        total_price: float = 0.0
    ) -> Dict:
        """
        Crea record storico acquisto con prodotto normalizzato
        
        Args:
            household_id: ID household
            receipt_id: ID scontrino
            receipt_item_id: ID item grezzo
            normalized_product_id: ID prodotto normalizzato
            purchase_date: Data acquisto
            store_id: ID negozio
            quantity: Quantità
            unit_price: Prezzo unitario
            total_price: Prezzo totale
            
        Returns:
            Dict con record creato
        """
        
        data = {
            "household_id": household_id,
            "receipt_id": receipt_id,
            "receipt_item_id": receipt_item_id,
            "normalized_product_id": normalized_product_id,
            "purchase_date": purchase_date.isoformat() if isinstance(purchase_date, date) else purchase_date,
            "total_price": total_price
        }

        # Aggiungi solo campi non-None per evitare errori UUID
        if store_id is not None:
            data["store_id"] = store_id
        if quantity is not None:
            data["quantity"] = quantity
        if unit_price is not None:
            data["unit_price"] = unit_price

        response = self.client.table("purchase_history").insert(data).execute()
        return response.data[0] if response.data else None

    def get_purchase_history(
        self,
        household_id: str,
        limit: int = 100,
        product_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """
        Ottieni storico acquisti household con filtri
        
        Args:
            household_id: ID household
            limit: Numero massimo risultati
            product_id: Filtra per prodotto specifico
            start_date: Data inizio
            end_date: Data fine
            
        Returns:
            Lista di acquisti
        """
        
        query = self.client.table("purchase_history")\
            .select("*, normalized_products(*), receipts(receipt_date, store_name)")\
            .eq("household_id", household_id)\
            .order("purchase_date", desc=True)\
            .limit(limit)
        
        if product_id:
            query = query.eq("normalized_product_id", product_id)
        
        if start_date:
            query = query.gte("purchase_date", start_date.isoformat())
        
        if end_date:
            query = query.lte("purchase_date", end_date.isoformat())
        
        response = query.execute()
        return response.data


    # ===================================
    # STORAGE
    # ===================================
    
    def upload_receipt_image(
        self,
        file_path: str,
        file_content: bytes,
        content_type: str = "image/jpeg"
    ) -> str:
        """
        Upload immagine scontrino su Supabase Storage
        
        Args:
            file_path: Path nel bucket (es: "user_id/receipt_id.jpg")
            file_content: Contenuto file come bytes
            content_type: MIME type
            
        Returns:
            URL pubblico dell'immagine
        """
        
        # Upload su storage
        self.client.storage.from_("scontrini-receipts").upload(
            file_path,
            file_content,
            {"content-type": content_type}
        )
        
        # Genera URL
        url = self.client.storage.from_("scontrini-receipts").get_public_url(file_path)
        return url


# Istanza globale del servizio
supabase_service = SupabaseService()
