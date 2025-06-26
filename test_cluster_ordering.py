#!/usr/bin/env python3
"""
Test per verificare il sistema di ordinamento cluster completo.
"""

import requests
import json

# URL del backend
BACKEND_URL = "http://localhost:8000"

def test_cluster_ordering_system():
    print("=== TEST SISTEMA ORDINAMENTO CLUSTER ===")
    
    # 1. Carica colori attuali
    print("1. Caricamento colori attuali...")
    response = requests.get(f"{BACKEND_URL}/api/cabin/1/colors")
    
    if response.status_code != 200:
        print(f"Errore nel caricamento colori: {response.status_code}")
        return
    
    colors_data = response.json()
    colors = colors_data.get('colors', [])
    
    print(f"   Trovati {len(colors)} colori")
    
    # 2. Analizza cluster presenti
    clusters = list(set(color['cluster'] for color in colors if color.get('cluster')))
    clusters.sort()
    print(f"   Cluster presenti: {clusters}")
    
    # 3. Mostra situazione iniziale
    print("\n2. Situazione PRIMA del riordino cluster:")
    cluster_counts = {}
    for i, color in enumerate(colors[:15]):  # Primi 15
        cluster = color.get('cluster', 'N/A')
        if cluster not in cluster_counts:
            cluster_counts[cluster] = {'first_pos': i+1, 'count': 0}
        cluster_counts[cluster]['count'] += 1
        print(f"   {i+1:2}: {color['color_code']:<12} {cluster:<15}")
    
    print(f"\n   Cluster summary prima: {dict((c, info['count']) for c, info in cluster_counts.items())}")
    
    # 4. Definisce nuovo ordine (inverso dell'alfabetico)
    new_order = sorted(clusters, reverse=True)  # Ordine inverso
    print(f"\n3. Nuovo ordine cluster da applicare: {new_order}")
    
    # 5. Applica nuovo ordine
    print("\n4. Applicazione nuovo ordine cluster...")
    
    apply_data = {
        'cluster_order': new_order,
        'colors': []  # Lascio vuoto, il backend caricherà dal DB
    }
    
    response = requests.post(
        f"{BACKEND_URL}/api/cabin/1/apply-cluster-order",
        headers={'Content-Type': 'application/json'},
        data=json.dumps(apply_data)
    )
    
    if response.status_code != 200:
        print(f"   Errore nell'applicazione ordine: {response.status_code}")
        print(f"   Risposta: {response.text}")
        return
    
    result = response.json()
    print(f"   ✅ Ordine applicato: {result.get('message', '')}")
    
    # 6. Verifica risultato
    print("\n5. Verifica risultato...")
    response = requests.get(f"{BACKEND_URL}/api/cabin/1/colors")
    
    if response.status_code != 200:
        print(f"   Errore nel ricaricamento: {response.status_code}")
        return
    
    new_colors = response.json().get('colors', [])
    
    print(f"   Ricaricati {len(new_colors)} colori")
    
    # 7. Mostra situazione finale
    print("\n6. Situazione DOPO il riordino cluster:")
    cluster_counts_after = {}
    for i, color in enumerate(new_colors[:15]):  # Primi 15
        cluster = color.get('cluster', 'N/A')
        if cluster not in cluster_counts_after:
            cluster_counts_after[cluster] = {'first_pos': i+1, 'count': 0}
        cluster_counts_after[cluster]['count'] += 1
        print(f"   {i+1:2}: {color['color_code']:<12} {cluster:<15}")
    
    print(f"\n   Cluster summary dopo: {dict((c, info['count']) for c, info in cluster_counts_after.items())}")
    
    # 8. Verifica che l'ordine sia corretto
    print("\n7. Verifica ordine applicato...")
    clusters_found_order = []
    current_cluster = None
    
    for color in new_colors:
        cluster = color.get('cluster')
        if cluster and cluster != current_cluster:
            if cluster not in clusters_found_order:
                clusters_found_order.append(cluster)
            current_cluster = cluster
    
    print(f"   Ordine cluster trovato: {clusters_found_order}")
    print(f"   Ordine cluster richiesto: {new_order}")
    
    # Verifica se l'ordine è corretto (almeno i primi cluster)
    match_count = 0
    for i in range(min(len(clusters_found_order), len(new_order))):
        if clusters_found_order[i] == new_order[i]:
            match_count += 1
        else:
            break
    
    if match_count >= 2:  # Almeno i primi 2 cluster nell'ordine giusto
        print("   ✅ Ordine cluster applicato correttamente")
    else:
        print("   ❌ Ordine cluster NON corretto")
    
    print("\n=== FINE TEST ===")

if __name__ == "__main__":
    test_cluster_ordering_system()
