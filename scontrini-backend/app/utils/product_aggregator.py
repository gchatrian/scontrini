"""
Product Aggregator Utility
Funzioni per aggregare prodotti duplicati durante il salvataggio
"""
from typing import List, Dict, Tuple
from collections import defaultdict


def aggregate_duplicate_products(items: List[Dict]) -> List[Dict]:
    """
    Aggrega prodotti duplicati basandosi su raw_product_name e store_name.
    
    Args:
        items: Lista di prodotti parsati dallo scontrino
        
    Returns:
        Lista di prodotti aggregati
    """
    if not items:
        return []
    
    # Raggruppa per chiave unica (raw_product_name + store_name)
    grouped = defaultdict(list)
    
    for item in items:
        # Crea chiave unica per il raggruppamento
        key = f"{item.get('raw_product_name', '')}_{item.get('store_name', '')}"
        grouped[key].append(item)
    
    aggregated_items = []
    
    for key, group in grouped.items():
        if len(group) == 1:
            # Nessun duplicato, mantieni come è
            aggregated_items.append(group[0])
        else:
            # Aggrega i duplicati
            aggregated_item = aggregate_product_group(group)
            aggregated_items.append(aggregated_item)
    
    return aggregated_items


def aggregate_product_group(group: List[Dict]) -> Dict:
    """
    Aggrega un gruppo di prodotti duplicati in un singolo prodotto.
    
    Args:
        group: Lista di prodotti duplicati
        
    Returns:
        Prodotto aggregato
    """
    if not group:
        return {}
    
    if len(group) == 1:
        return group[0]
    
    # Prendi il primo prodotto come base
    base_item = group[0].copy()
    
    # Aggrega quantità e prezzi
    total_quantity = sum(item.get('quantity', 1) for item in group)
    total_price = sum(item.get('total_price', 0) for item in group)
    
    # Calcola prezzo unitario medio
    unit_price = total_price / total_quantity if total_quantity > 0 else 0
    
    # Aggiorna i valori aggregati
    base_item.update({
        'quantity': total_quantity,
        'total_price': total_price,
        'unit_price': unit_price,
        'aggregated_from': len(group),  # Numero di prodotti aggregati
        'original_items': [item.get('raw_product_name') for item in group]  # Per debug
    })
    
    return base_item


def detect_duplicate_products(items: List[Dict]) -> List[Tuple[int, int]]:
    """
    Rileva prodotti duplicati nella lista.
    
    Args:
        items: Lista di prodotti
        
    Returns:
        Lista di tuple (indice1, indice2) per prodotti duplicati
    """
    duplicates = []
    
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            item1 = items[i]
            item2 = items[j]
            
            # Confronta raw_product_name e store_name
            if (item1.get('raw_product_name') == item2.get('raw_product_name') and
                item1.get('store_name') == item2.get('store_name')):
                duplicates.append((i, j))
    
    return duplicates


def validate_aggregation(items: List[Dict], aggregated: List[Dict]) -> bool:
    """
    Valida che l'aggregazione sia corretta.
    
    Args:
        items: Lista originale
        aggregated: Lista aggregata
        
    Returns:
        True se l'aggregazione è valida
    """
    # Controlla che la somma delle quantità sia preservata
    original_total_quantity = sum(item.get('quantity', 1) for item in items)
    aggregated_total_quantity = sum(item.get('quantity', 1) for item in aggregated)
    
    # Controlla che la somma dei prezzi sia preservata
    original_total_price = sum(item.get('total_price', 0) for item in items)
    aggregated_total_price = sum(item.get('total_price', 0) for item in aggregated)
    
    return (abs(original_total_quantity - aggregated_total_quantity) < 0.001 and
            abs(original_total_price - aggregated_total_price) < 0.001)


# Test cases per validazione
if __name__ == "__main__":
    test_items = [
        {
            'raw_product_name': 'COCA COLA 1.5L',
            'quantity': 1,
            'unit_price': 1.50,
            'total_price': 1.50,
            'store_name': 'Esselunga'
        },
        {
            'raw_product_name': 'COCA COLA 1.5L',
            'quantity': 2,
            'unit_price': 1.50,
            'total_price': 3.00,
            'store_name': 'Esselunga'
        },
        {
            'raw_product_name': 'ACQUA NATURALE',
            'quantity': 1,
            'unit_price': 0.50,
            'total_price': 0.50,
            'store_name': 'Esselunga'
        }
    ]
    
    print("Test aggregazione prodotti:")
    print(f"Originali: {len(test_items)} prodotti")
    
    aggregated = aggregate_duplicate_products(test_items)
    print(f"Aggregati: {len(aggregated)} prodotti")
    
    for item in aggregated:
        print(f"- {item['raw_product_name']}: {item['quantity']}x = €{item['total_price']}")
    
    print(f"Validazione: {validate_aggregation(test_items, aggregated)}")
