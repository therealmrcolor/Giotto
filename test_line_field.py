#!/usr/bin/env python3
"""Script di test per verificare il salvataggio del campo 'line'."""

import requests
import json

# Test data con campo line
test_data = {
    "colors": [
        {
            "code": "RAL7010",
            "type": "R",
            "line": "Linea Test A",
            "CH": 25.5,
            "sequence": 1,
            "lunghezza_ordine": "corto"
        }
    ]
}

print("=== TEST CAMPO LINE ===")
print(f"Invio dati di test: {json.dumps(test_data, indent=2)}")

# Invia richiesta di ottimizzazione al frontend
try:
    response = requests.post(
        "http://localhost:8080/api/optimize", 
        json={"colors_today": test_data["colors"]},
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    print(f"\nRisposta status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Risposta ricevuta: {json.dumps(result, indent=2)}")
        
        # Verifica se il campo line è presente nella risposta
        if 'ordered_colors' in result:
            for i, color in enumerate(result['ordered_colors']):
                print(f"\nColore {i}: code={color.get('code')}, type={color.get('type')}, line={color.get('line')}")
                if color.get('line'):
                    print(f"✓ Campo line preservato: {color.get('line')}")
                else:
                    print(f"❌ Campo line mancante o vuoto")
    else:
        print(f"Errore: {response.text}")
        
except Exception as e:
    print(f"Errore durante il test: {e}")

print("\n=== FINE TEST ===")
