#!/usr/bin/env python3
"""
Test specifico per verificare che il primo colore RAL9005 sia prioritario
"""

import requests
import json

# URL del backend
BASE_URL = "http://localhost:8000"

# Test data con RAL9005 e altri colori
test_colors = [
    {"code": "RAL9003", "type": "E", "cluster": "Bianco", "sequence": 1, "sequence_type": "LARGE"},
    {"code": "RAL9016", "type": "K", "cluster": "Bianco", "sequence": 2, "sequence_type": "LARGE"},
    {"code": "RAL7035", "type": "K", "cluster": "Grigio Chiaro", "sequence": 3, "sequence_type": "LARGE"},
    {"code": "RAL9005", "type": "K", "cluster": "Nero", "sequence": 4, "sequence_type": "LARGE"},
    {"code": "RAL9005", "type": "F", "cluster": "Nero", "sequence": 5, "sequence_type": "LARGE"},
    {"code": "RAL9005", "type": "E", "cluster": "Nero", "sequence": 5, "sequence_type": "LARGE"},
    {"code": "RAL7037", "type": "E", "cluster": "Grigio Scuro", "sequence": 6, "sequence_type": "LARGE"},
    {"code": "RAL7037", "type": "F", "cluster": "Grigio Scuro", "sequence": 7, "sequence_type": "LARGE"},
]

def test_without_first_color():
    """Test senza specificare primo colore"""
    print("=== TEST SENZA PRIMO COLORE ===")
    
    payload = {
        "colors_today": test_colors,
        "start_cluster_name": None,
        "first_color": None
    }
    
    response = requests.post(f"{BASE_URL}/optimize", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print("Struttura risposta:", list(result.keys()))
        optimized_colors = result.get('ordered_colors', [])
        print(f"✓ Risposta ricevuta: {len(optimized_colors)} colori")
        print("Primi 5 colori:")
        for i, color in enumerate(optimized_colors[:5]):
            print(f"  {i+1}. {color.get('code')} {color.get('type')}")
        return optimized_colors
    else:
        print(f"❌ Errore: {response.status_code} - {response.text}")
        return []

def test_with_first_color():
    """Test con primo colore RAL9005 specificato"""
    print("\n=== TEST CON PRIMO COLORE RAL9005 ===")
    
    payload = {
        "colors_today": test_colors,
        "start_cluster_name": None,
        "first_color": "RAL9005"
    }
    
    response = requests.post(f"{BASE_URL}/optimize", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print("Struttura risposta:", list(result.keys()))
        optimized_colors = result.get('ordered_colors', [])
        print(f"✓ Risposta ricevuta: {len(optimized_colors)} colori")
        print("Primi 5 colori:")
        for i, color in enumerate(optimized_colors[:5]):
            print(f"  {i+1}. {color.get('code')} {color.get('type')}")
        
        # Verifica se RAL9005 è il primo
        if optimized_colors and optimized_colors[0].get('code') == 'RAL9005':
            print("✅ SUCCESS: RAL9005 è il primo colore!")
        else:
            print("❌ FAIL: RAL9005 non è il primo colore!")
            
        return optimized_colors
    else:
        print(f"❌ Errore: {response.status_code} - {response.text}")
        return []

if __name__ == "__main__":
    print("Test per verificare la priorità del primo colore RAL9005")
    print("=" * 50)
    
    # Test senza primo colore
    result1 = test_without_first_color()
    
    # Test con primo colore
    result2 = test_with_first_color()
    
    # Confronto
    if result1 and result2:
        print("\n=== CONFRONTO ===")
        print("Senza first_color:", [f"{c.get('code')} {c.get('type')}" for c in result1[:3]])
        print("Con first_color:  ", [f"{c.get('code')} {c.get('type')}" for c in result2[:3]])
