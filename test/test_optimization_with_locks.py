#!/usr/bin/env python3
"""
Test per verificare che l'ottimizzazione con blocchi funzioni correttamente.
"""

import requests
import json

# URL del backend
BACKEND_URL = "http://localhost:8000"

def test_optimization_with_locks():
    print("=== TEST OTTIMIZZAZIONE CON BLOCCHI ===")
    
    # Prima ottieni i colori attuali per cabina 1
    print("1. Caricamento colori attuali...")
    response = requests.get(f"{BACKEND_URL}/api/cabin/1/colors")
    
    if response.status_code != 200:
        print(f"Errore nel caricamento colori: {response.status_code}")
        return
    
    colors_data = response.json()
    colors = colors_data.get('colors', [])
    
    print(f"   Trovati {len(colors)} colori")
    
    if len(colors) < 5:
        print("   Non ci sono abbastanza colori per il test")
        return
    
    # Modifica alcuni colori per il test: sblocca alcuni colori
    test_colors = []
    for i, color in enumerate(colors):
        test_color = {
            'code': color['color_code'],
            'type': color['color_type'],
            'cluster': color['cluster'],
            'CH': color.get('ch_value', ''),
            'lunghezza_ordine': color.get('lunghezza_ordine', ''),
            'sequence': color.get('input_sequence', ''),
            'sequence_type': color.get('sequence_type', ''),
            'locked': False if i >= 10 else True,  # Sblocca colori dalla posizione 10 in poi
            'position': i if (False if i >= 10 else True) else None
        }
        test_colors.append(test_color)
    
    locked_count = sum(1 for c in test_colors if c['locked'])
    free_count = len(test_colors) - locked_count
    
    print(f"2. Preparazione test: {locked_count} colori bloccati, {free_count} liberi")
    
    # Stampa la situazione prima dell'ottimizzazione
    print("\n3. Prima dell'ottimizzazione:")
    for i, color in enumerate(test_colors[:15]):  # Mostra primi 15
        status = "🔒" if color['locked'] else "🔓"
        print(f"   {i+1:2}: {color['code']:<12} {color['cluster']:<15} {status}")
    
    # Esegui ottimizzazione
    print("\n4. Esecuzione ottimizzazione...")
    
    optimization_data = {
        'colors_today': test_colors,
        'prioritized_reintegrations': []
    }
    
    response = requests.post(
        f"{BACKEND_URL}/api/cabin/1/optimize-locked",
        headers={'Content-Type': 'application/json'},
        data=json.dumps(optimization_data)
    )
    
    if response.status_code != 200:
        print(f"   Errore nell'ottimizzazione: {response.status_code}")
        print(f"   Risposta: {response.text}")
        return
    
    result = response.json()
    print(f"   ✅ Ottimizzazione completata: {result.get('message', '')}")
    
    # Ricarica i colori dopo l'ottimizzazione
    print("\n5. Verifica risultato...")
    response = requests.get(f"{BACKEND_URL}/api/cabin/1/colors")
    
    if response.status_code != 200:
        print(f"   Errore nel ricaricamento: {response.status_code}")
        return
    
    new_colors = response.json().get('colors', [])
    
    print(f"   Ricaricati {len(new_colors)} colori")
    
    # Confronta prima e dopo
    print("\n6. Dopo l'ottimizzazione:")
    for i, color in enumerate(new_colors[:15]):  # Mostra primi 15
        status = "🔒" if color.get('locked', False) else "🔓"
        print(f"   {i+1:2}: {color['color_code']:<12} {color['cluster']:<15} {status}")
    
    # Verifica che i colori bloccati non si siano mossi
    print("\n7. Verifica blocchi...")
    moved_locked = 0
    for i, (old, new) in enumerate(zip(test_colors[:10], new_colors[:10])):
        if old['locked'] and (old['code'] != new['color_code'] or old['type'] != new['color_type']):
            moved_locked += 1
            print(f"   ❌ Colore bloccato mosso in pos {i+1}: {old['code']}{old['type']} -> {new['color_code']}{new['color_type']}")
    
    if moved_locked == 0:
        print("   ✅ Tutti i colori bloccati sono rimasti in posizione")
    else:
        print(f"   ❌ {moved_locked} colori bloccati sono stati spostati")
    
    print("\n=== FINE TEST ===")

if __name__ == "__main__":
    test_optimization_with_locks()
