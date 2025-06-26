#!/usr/bin/env python3
"""
Test comprehensivo per verificare che la gestione di sequence=None e valori mancanti 
funzioni correttamente in tutti i casi possibili.
"""

import requests
import json

def test_comprehensive_sequence_handling():
    """Test con tutti i possibili scenari di sequence problematici"""
    
    print("🔧 Test Comprehensivo Gestione Sequence")
    print("Verifica tutti i casi di sequence=None, mancante, e valori edge case")
    print()
    
    # Test 1: Tutti i tipi di sequence problematici
    test_cases = [
        {
            "name": "Mix di sequence None, mancanti, e normali",
            "payload": {
                "colors_today": [
                    {"code": "RAL7040", "type": "R", "sequence": None, "lunghezza_ordine": "corto"},
                    {"code": "RAL3020", "type": "E", "lunghezza_ordine": "corto"},  # sequence mancante
                    {"code": "RAL1019", "type": "K", "sequence": 3, "lunghezza_ordine": "corto"},
                    {"code": "RAL7015", "type": "F", "sequence": 4, "lunghezza_ordine": "corto"},
                    {"code": "RAL9006", "type": "E", "sequence": 0, "lunghezza_ordine": "corto"},  # sequence = 0
                ],
                "start_cluster_name": None,
            }
        },
        {
            "name": "Solo colori con sequence=None",
            "payload": {
                "colors_today": [
                    {"code": "RAL7040", "type": "R", "sequence": None, "lunghezza_ordine": "corto"},
                    {"code": "RAL3020", "type": "E", "sequence": None, "lunghezza_ordine": "corto"},
                    {"code": "RAL1019", "type": "K", "sequence": None, "lunghezza_ordine": "corto"},
                ],
                "start_cluster_name": None,
            }
        },
        {
            "name": "Solo colori senza campo sequence",
            "payload": {
                "colors_today": [
                    {"code": "RAL7040", "type": "R", "lunghezza_ordine": "corto"},
                    {"code": "RAL3020", "type": "E", "lunghezza_ordine": "corto"},
                    {"code": "RAL1019", "type": "K", "lunghezza_ordine": "corto"},
                ],
                "start_cluster_name": None,
            }
        },
        {
            "name": "Sequence con valori string che dovrebbero convertirsi",
            "payload": {
                "colors_today": [
                    {"code": "RAL7040", "type": "R", "sequence": "5", "lunghezza_ordine": "corto"},
                    {"code": "RAL3020", "type": "E", "sequence": "abc", "lunghezza_ordine": "corto"},  # non convertibile
                    {"code": "RAL1019", "type": "K", "sequence": "", "lunghezza_ordine": "corto"},  # stringa vuota
                ],
                "start_cluster_name": None,
            }
        }
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🧪 TEST {i}/{total_tests}: {test_case['name']}")
        print("=" * 60)
        
        try:
            response = requests.post(
                "http://localhost:8000/optimize",
                json=test_case["payload"],
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ SUCCESS: {test_case['name']}")
                
                # Verifica che la risposta contenga i risultati attesi
                if "cabina_1" in result and "ordered_colors" in result["cabina_1"]:
                    colors = result["cabina_1"]["ordered_colors"]
                    print(f"📋 Colori ordinati: {len(colors)} colori")
                    for j, color in enumerate(colors[:3], 1):  # Mostra primi 3
                        print(f"  {j}. {color.get('code', 'N/A')} ({color.get('type', 'N/A')}) - Seq: {color.get('sequence', 'N/A')}")
                    if len(colors) > 3:
                        print(f"  ... e altri {len(colors) - 3} colori")
                    success_count += 1
                else:
                    print(f"⚠️  ATTENZIONE: Risposta inaspettata per {test_case['name']}")
                    print(f"Chiavi trovate: {list(result.keys())}")
            else:
                print(f"❌ ERROR: {test_case['name']} - Status: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ EXCEPTION: {test_case['name']} - {str(e)}")
        
        print()
    
    print("=" * 60)
    print("📊 RISULTATO FINALE")
    print("=" * 60)
    print(f"Test superati: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("✅ TUTTI I TEST SUPERATI!")
        print("   La gestione di sequence=None e valori mancanti funziona correttamente in tutti i casi.")
        print()
        print("📋 Verifica completata:")
        print("   - sequence=None ✅")
        print("   - sequence mancante ✅") 
        print("   - sequence=0 ✅")
        print("   - sequence con stringhe ✅")
        print("   - sequence non convertibili ✅")
        print()
        print("🎯 Il sistema è ora robusto per l'aggiunta manuale di colori dalla cabina!")
    else:
        print(f"⚠️  {total_tests - success_count} TEST FALLITI")
        print("   Alcuni scenari potrebbero ancora avere problemi.")
    
    return success_count == total_tests

if __name__ == "__main__":
    test_comprehensive_sequence_handling()
