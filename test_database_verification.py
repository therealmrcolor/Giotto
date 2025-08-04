#!/usr/bin/env python3
"""Script per verificare i dati salvati nel database."""

import sqlite3
import json
import requests

# Prima facciamo una richiesta per assicurarci che i dati siano salvati
print("=== VERIFICA DATABASE DOPO OTTIMIZZAZIONE ===")

# Invia richiesta di test
test_data = {
    "colors_today": [
        {
            "code": "RAL5019",
            "type": "F",
            "line": "Test Line B",
            "CH": 30.0,
            "sequence": 2,
            "lunghezza_ordine": "corto"
        }
    ]
}

print(f"Invio nuovo test: {json.dumps(test_data, indent=2)}")

try:
    response = requests.post(
        "http://localhost:8080/api/optimize", 
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    print(f"Risposta: {response.status_code}")
    if response.status_code == 200:
        print("✓ Ottimizzazione completata")
    else:
        print(f"❌ Errore: {response.text}")
    
    # Ora verifichiamo i dati usando l'API del frontend
    response = requests.get("http://localhost:8080/api/cabin/1/colors")
    if response.status_code == 200:
        colors = response.json().get('colors', [])
        print(f"\n=== COLORI SALVATI IN CABINA 1 ({len(colors)} totali) ===")
        for color in colors:
            print(f"ID: {color.get('id')}, Code: {color.get('color_code')}, Type: {color.get('color_type')}, Line: {color.get('line')}, Cluster: {color.get('cluster')}")
            
        # Verifica se ci sono colori con line non nullo
        colors_with_line = [c for c in colors if c.get('line') and c.get('line') != 'N/D']
        if colors_with_line:
            print(f"\n✓ Trovati {len(colors_with_line)} colori con campo line valorizzato:")
            for color in colors_with_line:
                print(f"  - {color.get('color_code')} {color.get('color_type')}: line = '{color.get('line')}'")
        else:
            print("\n❌ Nessun colore con campo line valorizzato trovato")
    else:
        print(f"❌ Errore nell'ottenere i colori: {response.status_code}")
        
except Exception as e:
    print(f"Errore: {e}")

print("\n=== FINE VERIFICA ===")
