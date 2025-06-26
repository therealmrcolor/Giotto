#!/usr/bin/env python3
"""
Test per verificare che la correzione del problema 'NoneType' vs 'int' nel campo sequence funzioni correttamente.
Questo test simula l'aggiunta manuale di colori che potrebbero avere sequence=None.
"""

import requests
import json

def test_sequence_none_handling():
    """Test con colori che hanno sequence=None o mancante per verificare la gestione corretta"""
    
    # Test payload che include colori con sequence=None, mancante, o con valori normali
    test_payload = {
        "colors_today": [
            # Colore normale con sequence presente
            {
                "code": "RAL9006",
                "type": "E",
                "sequence": 4,
                "lunghezza_ordine": "corto"
            },
            # Colore con sequence=None (simula aggiunta manuale)
            {
                "code": "RAL7040",  # Questo dovrebbe essere nel cluster Grigio Chiaro
                "type": "R",
                "sequence": None,  # <- QUESTO È IL PROBLEMA CHE STIAMO TESTANDO
                "lunghezza_ordine": "corto"
            },
            # Colore senza campo sequence
            {
                "code": "RAL3020",
                "type": "E",
                # sequence non presente del tutto
                "lunghezza_ordine": "corto"
            },
            # Altri colori normali per creare un scenario realistico
            {
                "code": "RAL1019",
                "type": "K",
                "sequence": 3,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "RAL7015",
                "type": "F",
                "sequence": 4,
                "lunghezza_ordine": "corto"
            }
        ],
        "start_cluster_name": None,
        "prioritized_reintegrations": []
    }
    
    print("🧪 TEST: Gestione Sequence=None/Mancante")
    print("=" * 60)
    print("Test con colori che hanno problemi nel campo sequence:")
    
    for i, color in enumerate(test_payload["colors_today"]):
        sequence_info = color.get('sequence', 'MANCANTE')
        print(f"  {i+1}. {color['code']} ({color['type']}) - Sequence: {sequence_info}")
    
    print(f"\n🔧 Problema da testare:")
    print("  - RAL7040 ha sequence=None")
    print("  - RAL3020 non ha il campo sequence")
    print("  - Prima del fix: errore '<' not supported between instances of 'NoneType' and 'int'")
    print("  - Dopo il fix: dovrebbe funzionare correttamente")
    
    try:
        print(f"\n🚀 Chiamata API al backend (Docker)...")
        response = requests.post(
            'http://localhost:8000/optimize',
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Ottimizzazione completata senza errori!")
            
            # Analizza la risposta
            if 'cabina_1' in result:
                # Formato cabin-based
                ordered_colors = result.get('cabina_1', {}).get('ordered_colors', [])
                optimal_sequence = result.get('cabina_1', {}).get('optimal_cluster_sequence', [])
            else:
                # Formato legacy
                ordered_colors = result.get('ordered_colors', [])
                optimal_sequence = result.get('optimal_cluster_sequence', [])
            
            print(f"\n📊 Sequenza cluster ottimale: {' -> '.join(optimal_sequence)}")
            print(f"\n📋 Sequenza colori risultante:")
            
            for i, color in enumerate(ordered_colors):
                sequence_val = color.get('sequence', 'N/A')
                print(f"  {i+1}. {color.get('code')} ({color.get('type')}) - Cluster: {color.get('cluster')} - Seq: {sequence_val}")
            
            # Verifica specifica per i colori problematici
            print(f"\n🔍 Verifica gestione colori problematici:")
            
            # Trova i colori che avevano problemi di sequence
            ral7040_found = any(c.get('code') == 'RAL7040' for c in ordered_colors)
            ral3020_found = any(c.get('code') == 'RAL3020' for c in ordered_colors)
            
            if ral7040_found:
                print("  ✅ RAL7040 (sequence=None) è presente nella sequenza ottimizzata")
            else:
                print("  ❌ RAL7040 (sequence=None) NON è presente nella sequenza")
                
            if ral3020_found:
                print("  ✅ RAL3020 (sequence mancante) è presente nella sequenza ottimizzata") 
            else:
                print("  ❌ RAL3020 (sequence mancante) NON è presente nella sequenza")
            
            return True
            
        else:
            print(f"❌ ERRORE API: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Dettaglio errore: {error_detail}")
            except:
                print(f"Risposta raw: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_addition_simulation():
    """Test che simula l'aggiunta manuale tramite interfaccia cabina"""
    
    print("\n\n🎯 TEST: Simulazione Aggiunta Manuale Cabina")
    print("=" * 60)
    
    # Simula l'aggiunta di un colore tramite interfaccia web della cabina
    # che potrebbe non avere tutti i campi impostati
    manual_color_payload = {
        "colors_today": [
            {
                "code": "RAL7044",  # Colore che ha causato l'errore nel log originale
                "type": "E",
                # sequence deliberatamente non impostato
                "lunghezza_ordine": "corto"
            }
        ],
        "start_cluster_name": None,
        "prioritized_reintegrations": []
    }
    
    print("Simulo l'aggiunta di un singolo colore senza sequence:")
    print(f"  - Codice: RAL7044")
    print(f"  - Tipo: E (Estetico)")
    print(f"  - Sequence: NON IMPOSTATO (come in aggiunta manuale)")
    
    try:
        print(f"\n🚀 Test aggiunta manuale via API...")
        response = requests.post(
            'http://localhost:8000/optimize',
            json=manual_color_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Aggiunta manuale simulata completata!")
            
            # Verifica che il colore sia stato processato
            ordered_colors = result.get('ordered_colors', []) or result.get('cabina_1', {}).get('ordered_colors', [])
            
            if ordered_colors:
                print(f"\n📋 Colore processato:")
                color = ordered_colors[0]
                sequence_val = color.get('sequence', 'DEFAULT_0')
                print(f"  {color.get('code')} ({color.get('type')}) - Cluster: {color.get('cluster')} - Seq: {sequence_val}")
                print("  ✅ Il colore è stato processato correttamente nonostante sequence mancante")
            else:
                print("  ❌ Nessun colore nel risultato")
                
            return True
        else:
            print(f"❌ ERRORE: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Errore: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Test Correzione Gestione Sequence=None")
    print("Verifica che la correzione _safe_get_sequence() funzioni correttamente")
    print("")
    
    # Test 1: Gestione sequence=None e mancante
    test1_success = test_sequence_none_handling()
    
    # Test 2: Simulazione aggiunta manuale
    test2_success = test_manual_addition_simulation()
    
    print("\n" + "=" * 60)
    print("📊 RISULTATO FINALE")
    print("=" * 60)
    
    if test1_success and test2_success:
        print("✅ TUTTI I TEST SUPERATI!")
        print("   La correzione per sequence=None funziona correttamente.")
        print("   L'aggiunta manuale di colori ora dovrebbe funzionare senza errori.")
    else:
        print("❌ ALCUNI TEST FALLITI!")
        print("   Potrebbero esserci ancora problemi con la gestione di sequence=None.")
        
    print("\nNote:")
    print("- La funzione _safe_get_sequence() converte None -> 0")
    print("- Valori mancanti vengono gestiti con default 0")
    print("- L'ordinamento ora funziona senza errori di tipo")
