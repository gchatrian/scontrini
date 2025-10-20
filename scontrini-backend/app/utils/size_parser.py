"""
Size Parser Utility
Funzioni per separare quantità e unità di misura dal campo size
"""
import re
from typing import Tuple, Optional


def parse_size_and_unit(size_string: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Separa quantità e unità di misura da una stringa size.
    
    Args:
        size_string: Stringa contenente quantità e unità (es. "500 g", "1.5L", "2kg")
        
    Returns:
        Tuple (quantità, unità) dove:
        - quantità: solo il numero (es. "500", "1.5", "2")
        - unità: solo l'unità (es. "g", "L", "kg")
    """
    if not size_string or not isinstance(size_string, str):
        return None, None
    
    # Pulisci la stringa
    size_string = size_string.strip()
    
    # Pattern per estrarre numero e unità
    # Supporta: 500g, 1.5L, 2 kg, 750ml, etc.
    patterns = [
        r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$',  # 500g, 1.5L
        r'^(\d+(?:\.\d+)?)\s+([a-zA-Z]+)$',  # 500 g, 1.5 L
    ]
    
    for pattern in patterns:
        match = re.match(pattern, size_string)
        if match:
            quantity = match.group(1)
            unit = match.group(2).lower()
            
            # Normalizza unità comuni
            unit_mapping = {
                'g': 'g',
                'gr': 'g', 
                'grammi': 'g',
                'kg': 'kg',
                'chilogrammi': 'kg',
                'l': 'L',
                'litri': 'L',
                'ml': 'ml',
                'millilitri': 'ml',
                'cl': 'cl',
                'centilitri': 'cl'
            }
            
            normalized_unit = unit_mapping.get(unit, unit)
            
            return quantity, normalized_unit
    
    # Se non trova pattern, prova a estrarre solo numeri
    number_match = re.search(r'(\d+(?:\.\d+)?)', size_string)
    if number_match:
        return number_match.group(1), None
    
    return None, None


def clean_size_field(size_string: str) -> str:
    """
    Pulisce il campo size rimuovendo unità di misura e mantenendo solo la quantità.
    
    Args:
        size_string: Stringa size originale
        
    Returns:
        Stringa con solo la quantità numerica
    """
    quantity, _ = parse_size_and_unit(size_string)
    return quantity or ""


def get_unit_from_size(size_string: str) -> str:
    """
    Estrae solo l'unità di misura dal campo size.
    
    Args:
        size_string: Stringa size originale
        
    Returns:
        Stringa con solo l'unità di misura
    """
    _, unit = parse_size_and_unit(size_string)
    return unit or ""


# Test cases per validazione
if __name__ == "__main__":
    test_cases = [
        "500g",
        "1.5L", 
        "2 kg",
        "750ml",
        "1.25L",
        "500",
        "invalid",
        "",
        None
    ]
    
    print("Testing size parser:")
    for test in test_cases:
        quantity, unit = parse_size_and_unit(test)
        clean_size = clean_size_field(test)
        extracted_unit = get_unit_from_size(test)
        print(f"'{test}' -> quantity: '{quantity}', unit: '{unit}', clean: '{clean_size}', extracted_unit: '{extracted_unit}'")
