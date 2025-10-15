"""
Parser Service - Analizza testo OCR ed estrae dati strutturati
Gestisce diversi formati di scontrini italiani
"""
import re
from typing import Dict, List, Optional
from datetime import datetime, date, time
from decimal import Decimal


class ReceiptParser:
    """Parser per scontrini italiani"""
    
    # Pattern comuni supermercati italiani
    STORE_PATTERNS = [
        r'ESSELUNGA',
        r'COOP',
        r'CONAD',
        r'CARREFOUR',
        r'LIDL',
        r'EUROSPIN',
        r'MD',
        r'PENNY\s*MARKET',
        r'IPER',
        r'IPERAL',
        r'FAMILA',
        r'TODIS',
        r'IN\'S',
        r'PAM',
        r'SIMPLY',
        r'TIGROS'
    ]
    
    def __init__(self):
        """Inizializza parser"""
        pass
    
    def parse_receipt(self, ocr_text: str) -> Dict:
        """
        Analizza testo OCR e estrae dati strutturati
        
        Args:
            ocr_text: Testo estratto dall'OCR
            
        Returns:
            Dict con dati strutturati dello scontrino
        """
        result = {
            "success": True,
            "store_name": None,
            "store_address": None,
            "receipt_date": None,
            "receipt_time": None,
            "items": [],
            "total_amount": None,
            "payment_method": None,
            "discount_amount": None,
            "raw_text": ocr_text
        }
        
        try:
            # Normalizza testo (uppercase, rimuovi spazi multipli)
            text = self._normalize_text(ocr_text)
            
            # Estrai nome negozio
            result["store_name"] = self._extract_store_name(text)
            
            # Estrai indirizzo
            result["store_address"] = self._extract_address(text)
            
            # Estrai data
            result["receipt_date"] = self._extract_date(text)
            
            # Estrai ora
            result["receipt_time"] = self._extract_time(text)
            
            # Estrai items (prodotti)
            result["items"] = self._extract_items(text)
            
            # Estrai totale
            result["total_amount"] = self._extract_total(text)
            
            # Estrai metodo pagamento
            result["payment_method"] = self._extract_payment_method(text)
            
            # Estrai sconti
            result["discount_amount"] = self._extract_discount(text)
            
            return result
            
        except Exception as e:
            result["success"] = False
            result["error"] = f"Parsing error: {str(e)}"
            return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalizza testo"""
        # Uppercase
        text = text.upper()
        # Rimuovi spazi multipli
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _extract_store_name(self, text: str) -> Optional[str]:
        """Estrae nome negozio"""
        for pattern in self.STORE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).title()
        return None
    
    def _extract_address(self, text: str) -> Optional[str]:
        """Estrae indirizzo (basilare)"""
        # Pattern per indirizzi italiani (Via, Viale, Piazza, etc.)
        patterns = [
            r'(VIA|VIALE|PIAZZA|CORSO|V\.LE|P\.ZZA)\s+[A-Z\s]+\d+',
            r'(VIA|VIALE|PIAZZA|CORSO)\s+[A-Z\.\s]+,?\s*\d+'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return None
    
    def _extract_date(self, text: str) -> Optional[date]:
        """Estrae data"""
        # Pattern per date italiane
        patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # DD/MM/YYYY o DD-MM-YYYY
            r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})',       # DD.MM.YYYY
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                day, month, year = match.groups()
                day, month = int(day), int(month)
                year = int(year)
                
                # Se anno a 2 cifre, converte a 4
                if year < 100:
                    year += 2000
                
                try:
                    return date(year, month, day)
                except ValueError:
                    continue
        
        return None
    
    def _extract_time(self, text: str) -> Optional[time]:
        """Estrae ora"""
        # Pattern per orari
        pattern = r'(\d{1,2})[:\.](\d{2})'
        
        match = re.search(pattern, text)
        if match:
            hour, minute = match.groups()
            hour, minute = int(hour), int(minute)
            
            try:
                return time(hour, minute)
            except ValueError:
                return None
        
        return None
    
    def _extract_items(self, text: str) -> List[Dict]:
        """
        Estrae lista prodotti
        Pattern tipico: NOME PRODOTTO  QUANTITA  PREZZO
        Es: COCA COLA 1.5L    1  €1.49
        """
        items = []
        lines = text.split('\n')
        
        # Pattern per linea prodotto: testo seguito da prezzo
        # Cerca linee con formato: [TESTO] [NUMERO] [PREZZO]
        pattern = r'^(.+?)\s+(\d+[,.]?\d*)\s*€?\s*(\d+[,\.]\d{2})$'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Cerca pattern prezzo alla fine della linea
            price_match = re.search(r'(\d+[,\.]\d{2})\s*€?\s*$', line)
            
            if price_match:
                price_str = price_match.group(1).replace(',', '.')
                
                # Estrai nome prodotto (tutto prima del prezzo)
                product_name = line[:price_match.start()].strip()
                
                # Rimuovi caratteri speciali comuni
                product_name = re.sub(r'[*#@]', '', product_name)
                
                # Cerca quantità (numero prima del prezzo)
                qty_match = re.search(r'(\d+[,.]?\d*)\s*$', product_name)
                quantity = 1.0
                
                if qty_match:
                    quantity = float(qty_match.group(1).replace(',', '.'))
                    product_name = product_name[:qty_match.start()].strip()
                
                # Valida: nome deve essere significativo
                if len(product_name) < 3:
                    continue
                
                # Calcola prezzo unitario
                total_price = float(price_str)
                unit_price = total_price / quantity if quantity > 0 else total_price
                
                items.append({
                    "raw_product_name": product_name,
                    "quantity": quantity,
                    "unit_price": round(unit_price, 2),
                    "total_price": round(total_price, 2)
                })
        
        return items
    
    def _extract_total(self, text: str) -> Optional[float]:
        """Estrae totale"""
        # Cerca pattern: TOTALE, TOTAL, TOT seguito da importo
        patterns = [
            r'TOTALE?\s*:?\s*€?\s*(\d+[,\.]\d{2})',
            r'TOT\.?\s*:?\s*€?\s*(\d+[,\.]\d{2})',
            r'TOTAL\s*:?\s*€?\s*(\d+[,\.]\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount = match.group(1).replace(',', '.')
                return float(amount)
        
        return None
    
    def _extract_payment_method(self, text: str) -> Optional[str]:
        """Estrae metodo di pagamento"""
        methods = {
            r'CONTANT[EI]': 'contanti',
            r'CASH': 'contanti',
            r'CARTA': 'carta',
            r'BANCOMAT': 'bancomat',
            r'CREDIT': 'carta',
            r'DEBIT': 'bancomat',
        }
        
        for pattern, method in methods.items():
            if re.search(pattern, text):
                return method
        
        return None
    
    def _extract_discount(self, text: str) -> Optional[float]:
        """Estrae sconti applicati"""
        patterns = [
            r'SCONTO\s*:?\s*€?\s*(\d+[,\.]\d{2})',
            r'DISCOUNT\s*:?\s*€?\s*(\d+[,\.]\d{2})',
            r'RISP\.?\s*:?\s*€?\s*(\d+[,\.]\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount = match.group(1).replace(',', '.')
                return float(amount)
        
        return None


# Istanza globale del parser
receipt_parser = ReceiptParser()
