#!/usr/bin/env python3
"""
Test per verificare la prioritizzazione a livello di cluster basata sui valori di sequenza.
I cluster contenenti colori con sequenza più bassa (es. 3) dovrebbero essere processati
prima dei cluster con sequenza più alta (es. 4).
"""

import requests
import json

def test_cluster_sequence_prioritization():
    """
    Test con colori che hanno sequenze diverse per verificare che i cluster
    vengano ordinati in base al valore di sequenza minimo contenuto.
    """
    test_payload = {
        "colors_today": [
            # Cluster Grigio Scuro: sequenza 4 (dovrebbe essere processato dopo)
            {
                "code": "RAL8019",
                "type": "E",
                "sequence": 4,
                "lunghezza_ordine": "corto"
            },
            
            # Cluster Grigio Chiaro: sequenza 3 (dovrebbe essere processato prima)
            {
                "code": "RAL7036",
                "type": "E",
                "sequence": 3,
                "lunghezza_ordine": "corto"
            },
            
            # Cluster Metallizzati: mix sequenza 3 e 4 (min=3, dovrebbe essere processato prima di Grigio Scuro)
            {
                "code": "RAL9006",
                "type": "K",
                "sequence": 3,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "RAL9006",
                "type": "E",
                "sequence": 4,
                "lunghezza_ordine": "corto"
            }
        ],
        "start_cluster_name": None,
        "prioritized_reintegrations": []
    }
    
    print("🎯 TEST: Prioritizzazione Cluster per Sequenza")
    print("="*60)
    print("Test dei colori di input:")
    for i, color in enumerate(test_payload["colors_today"]):
        print(f"  {i+1}. {color['code']} ({color['type']}) - Sequenza: {color['sequence']}")
    
    print("\n🔍 Atteso:")
    print("  - Cluster con sequenza 3 dovrebbero essere processati PRIMA")
    print("  - Cluster con sequenza 4 dovrebbero essere processati DOPO")
    print("  - Ordine atteso: Grigio Chiaro (seq 3) -> Metallizzati (seq min 3) -> Grigio Scuro (seq 4)")
    
    try:
        response = requests.post(
            'http://localhost:8000/optimize',
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Ottimizzazione completata!")
            
            # Analizza la sequenza cluster risultante (gestisce formato cabin-based)
            if 'cabina_1' in result:
                # Formato cabin-based
                cabina_1 = result.get('cabina_1', {})
                cabina_2 = result.get('cabina_2', {})
                optimal_sequence = cabina_1.get('optimal_cluster_sequence', []) + cabina_2.get('optimal_cluster_sequence', [])
                ordered_colors = cabina_1.get('ordered_colors', []) + cabina_2.get('ordered_colors', [])
            else:
                # Formato diretto (legacy)
                optimal_sequence = result.get('optimal_cluster_sequence', [])
                ordered_colors = result.get('ordered_colors', [])
            
            print(f"\n📊 Sequenza cluster ottimale: {' -> '.join(optimal_sequence)}")
            
            # Verifica l'ordine dei cluster
            print(f"\n🔍 Verifica prioritizzazione sequenza:")
            
            # Mappa i cluster e le loro sequenze minime
            cluster_sequences = {}
            for color in test_payload["colors_today"]:
                # Determina cluster del colore basato sui dati reali del DB
                code = color['code']
                if code == 'RAL8019':
                    cluster = 'Grigio Scuro'
                elif code == 'RAL7036':
                    cluster = 'Grigio Chiaro'
                elif code == 'RAL9006':
                    cluster = 'Metallizzati'
                else:
                    cluster = 'Altro'
                
                if cluster not in cluster_sequences:
                    cluster_sequences[cluster] = []
                cluster_sequences[cluster].append(color['sequence'])
            
            print("Cluster e loro sequenze minime:")
            for cluster, sequences in cluster_sequences.items():
                min_seq = min(sequences) if sequences else None
                print(f"  {cluster}: sequenze {sequences} -> min = {min_seq}")
            
            # Verifica che i cluster siano nell'ordine corretto
            expected_order_by_sequence = []
            for cluster, sequences in cluster_sequences.items():
                min_seq = min(sequences) if sequences else 999
                expected_order_by_sequence.append((cluster, min_seq))
            
            expected_order_by_sequence.sort(key=lambda x: x[1])
            expected_clusters = [cluster for cluster, _ in expected_order_by_sequence]
            
            print(f"\nOrdine atteso per sequenza: {expected_clusters}")
            print(f"Ordine ottenuto: {optimal_sequence}")
            
            # Controlla se l'ordine rispetta la prioritizzazione
            sequence_prioritization_ok = True
            if len(optimal_sequence) >= 2:
                # Verifica che cluster con sequenza più bassa vengano prima
                for i in range(len(optimal_sequence) - 1):
                    current_cluster = optimal_sequence[i]
                    next_cluster = optimal_sequence[i + 1]
                    
                    current_min_seq = min(cluster_sequences.get(current_cluster, [999]))
                    next_min_seq = min(cluster_sequences.get(next_cluster, [999]))
                    
                    if current_min_seq > next_min_seq:
                        print(f"❌ Violazione priorità: {current_cluster} (seq {current_min_seq}) prima di {next_cluster} (seq {next_min_seq})")
                        sequence_prioritization_ok = False
            
            if sequence_prioritization_ok:
                print("✅ Prioritizzazione per sequenza CORRETTA!")
                print("   I cluster con sequenze più basse sono stati processati per primi")
            else:
                print("❌ Prioritizzazione per sequenza NON CORRETTA!")
                
            print(f"\n📋 Sequenza colori finale:")
            for i, color in enumerate(ordered_colors):
                print(f"  {i+1}. {color.get('code')} ({color.get('type')}) - Cluster: {color.get('cluster')} - Seq: {color.get('sequence')}")
            
            return sequence_prioritization_ok
            
        else:
            print(f"❌ Errore API: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Dettaglio errore: {error_detail}")
            except:
                print(f"Risposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Test Prioritizzazione Cluster per Sequenza")
    print("Assicurati che il backend sia in esecuzione su localhost:8000")
    print("")
    
    success = test_cluster_sequence_prioritization()
    
    print("\n" + "=" * 60)
    print("📊 RISULTATO FINALE")
    print("=" * 60)
    
    if success:
        print("✅ TEST SUPERATO: La prioritizzazione per sequenza funziona correttamente!")
        print("   I cluster con valori di sequenza più bassi vengono processati per primi.")
    else:
        print("❌ TEST FALLITO: La prioritizzazione per sequenza non funziona come atteso.")
        print("   Verificare l'implementazione della logica di ordinamento cluster.")
    
    print("\nNote:")
    print("- I cluster dovrebbero essere ordinati per sequenza minima contenuta")
    print("- Sequenza 3 deve avere priorità su sequenza 4")
    print("- Questo test verifica la prioritizzazione a livello di cluster")
