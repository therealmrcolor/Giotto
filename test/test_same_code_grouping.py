#!/usr/bin/env python3
"""
Test per verificare la nuova regola di raggruppamento per stesso codice RAL/codice.
Questa regola deve avere priorità massima: i colori con lo stesso codice devono essere sempre raggruppati insieme.
"""

import requests
import json

def test_same_code_grouping():
    """
    Test della nuova regola di raggruppamento per stesso codice.
    
    Scenario di test:
    - RAL9006 tipo F (fisso)
    - Altri colori diversi
    - RAL9006 tipo E (estetico)
    - RAL9006 tipo K (kit)
    
    Risultato atteso: tutti i RAL9006 devono essere raggruppati insieme.
    """
    print("🧪 Test Raggruppamento per Stesso Codice RAL/Codice")
    print("=" * 60)
    
    # Dati di test con stesso codice RAL ma tipi diversi
    test_payload = {
        "colors_today": [
            {
                "code": "RAL9006",
                "type": "F",
                "sequence": 1,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "RAL7015",
                "type": "R", 
                "sequence": 1,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "RAL9006",
                "type": "E",
                "sequence": 2,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "160000",
                "type": "K",
                "sequence": 1,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "RAL9006",
                "type": "K",
                "sequence": 1,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "RAL7015",
                "type": "E",
                "sequence": 2,
                "lunghezza_ordine": "corto"
            }
        ],
        "start_cluster_name": None,
        "prioritized_reintegrations": []
    }
    
    print("Colori di input:")
    for i, color in enumerate(test_payload["colors_today"]):
        print(f"  {i+1}. {color['code']} ({color['type']})")
    
    print(f"\nChiamata API al backend...")
    
    try:
        response = requests.post(
            'http://localhost:8000/optimize',
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Ottimizzazione completata!")
            
            # Verifica la sequenza risultante
            ordered_colors = result.get('ordered_colors', [])
            optimal_sequence = result.get('optimal_cluster_sequence', [])
            
            print(f"\nSequenza cluster ottimale: {' -> '.join(optimal_sequence)}")
            print(f"\nSequenza colori risultante:")
            
            for i, color in enumerate(ordered_colors):
                print(f"  {i+1}. {color.get('code')} ({color.get('type')}) - Cluster: {color.get('cluster')}")
            
            # Verifica che i colori con stesso codice siano raggruppati
            print(f"\n🔍 Verifica raggruppamento per stesso codice:")
            
            # Trova tutte le posizioni dei RAL9006
            ral9006_positions = []
            for i, color in enumerate(ordered_colors):
                if color.get('code') == 'RAL9006':
                    ral9006_positions.append((i, color.get('type')))
            
            print(f"Posizioni RAL9006: {ral9006_positions}")
            
            # Verifica che siano consecutivi
            if len(ral9006_positions) > 1:
                positions = [pos[0] for pos in ral9006_positions]
                is_consecutive = all(positions[i] + 1 == positions[i + 1] for i in range(len(positions) - 1))
                
                if is_consecutive:
                    print("✅ I colori RAL9006 sono correttamente raggruppati insieme!")
                else:
                    print("❌ I colori RAL9006 NON sono raggruppati insieme!")
                    return False
            
            # Trova tutte le posizioni dei RAL7015
            ral7015_positions = []
            for i, color in enumerate(ordered_colors):
                if color.get('code') == 'RAL7015':
                    ral7015_positions.append((i, color.get('type')))
            
            print(f"Posizioni RAL7015: {ral7015_positions}")
            
            # Verifica che siano consecutivi
            if len(ral7015_positions) > 1:
                positions = [pos[0] for pos in ral7015_positions]
                is_consecutive = all(positions[i] + 1 == positions[i + 1] for i in range(len(positions) - 1))
                
                if is_consecutive:
                    print("✅ I colori RAL7015 sono correttamente raggruppati insieme!")
                else:
                    print("❌ I colori RAL7015 NON sono raggruppati insieme!")
                    return False
            
            return True
            
        else:
            print(f"❌ Errore API: {response.status_code}")
            print(f"Dettagli: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        return False

def test_mixed_scenario():
    """
    Test con scenario più complesso con più codici e tipi misti.
    """
    print("\n" + "=" * 60)
    print("🧪 Test Scenario Misto Complesso")
    print("=" * 60)
    
    test_payload = {
        "colors_today": [
            # Primo gruppo: RAL9005
            {"code": "RAL9005", "type": "F", "sequence": 1, "lunghezza_ordine": "corto"},
            {"code": "RAL7015", "type": "R", "sequence": 1, "lunghezza_ordine": "corto"},
            {"code": "RAL9005", "type": "E", "sequence": 2, "lunghezza_ordine": "corto"},
            
            # Secondo gruppo: 160000
            {"code": "160000", "type": "K", "sequence": 1, "lunghezza_ordine": "corto"},
            {"code": "RAL9005", "type": "K", "sequence": 1, "lunghezza_ordine": "corto"},
            {"code": "160000", "type": "E", "sequence": 2, "lunghezza_ordine": "corto"},
            
            # Terzo gruppo: RAL7015
            {"code": "RAL7015", "type": "E", "sequence": 2, "lunghezza_ordine": "corto"},
        ],
        "start_cluster_name": None,
        "prioritized_reintegrations": []
    }
    
    print("Colori di input:")
    for i, color in enumerate(test_payload["colors_today"]):
        print(f"  {i+1}. {color['code']} ({color['type']})")
    
    try:
        response = requests.post(
            'http://localhost:8000/optimize',
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Ottimizzazione completata!")
            
            ordered_colors = result.get('ordered_colors', [])
            
            print(f"\nSequenza colori risultante:")
            for i, color in enumerate(ordered_colors):
                print(f"  {i+1}. {color.get('code')} ({color.get('type')}) - Cluster: {color.get('cluster')}")
            
            # Verifica raggruppamenti per ogni codice
            codes_to_check = ['RAL9005', '160000', 'RAL7015']
            all_grouped = True
            
            for code in codes_to_check:
                positions = []
                for i, color in enumerate(ordered_colors):
                    if color.get('code') == code:
                        positions.append((i, color.get('type')))
                
                if len(positions) > 1:
                    pos_list = [pos[0] for pos in positions]
                    is_consecutive = all(pos_list[i] + 1 == pos_list[i + 1] for i in range(len(pos_list) - 1))
                    
                    if is_consecutive:
                        print(f"✅ Colori {code} raggruppati correttamente: {positions}")
                    else:
                        print(f"❌ Colori {code} NON raggruppati: {positions}")
                        all_grouped = False
            
            return all_grouped
            
        else:
            print(f"❌ Errore API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Avvio Test Raggruppamento Stesso Codice")
    print("Assicurati che il backend sia in esecuzione su localhost:8000")
    print("")
    
    # Test 1: Scenario base
    success1 = test_same_code_grouping()
    
    # Test 2: Scenario complesso
    success2 = test_mixed_scenario()
    
    print("\n" + "=" * 60)
    print("📊 RISULTATI FINALI")
    print("=" * 60)
    
    if success1:
        print("✅ Test base: PASSATO")
    else:
        print("❌ Test base: FALLITO")
    
    if success2:
        print("✅ Test complesso: PASSATO")
    else:
        print("❌ Test complesso: FALLITO")
    
    if success1 and success2:
        print("\n🎉 Tutti i test sono passati! La regola di raggruppamento funziona correttamente.")
    else:
        print("\n⚠️  Alcuni test sono falliti. Controlla la logica di raggruppamento.")
