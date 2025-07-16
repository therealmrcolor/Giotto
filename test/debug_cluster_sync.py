#!/usr/bin/env python3
"""
Test per verificare il problema di sincronizzazione cluster
"""

def test_cluster_sync_issue():
    """Test del problema di sincronizzazione cluster"""
    print("🔍 DEBUG: Problema sincronizzazione cluster")
    print("=" * 60)
    
    try:
        import requests
        
        base_url = "http://localhost:8080"
        cabin_id = 1
        
        print("1️⃣ Stato attuale colori cabina...")
        response = requests.get(f"{base_url}/api/cabin/{cabin_id}/colors", timeout=10)
        if response.status_code == 200:
            colors_data = response.json()
            colors = colors_data.get('colors', [])
            
            if colors:
                # Analizza i cluster nei colori
                clusters_in_colors = []
                for color in colors:
                    cluster = color.get('cluster')
                    if cluster and cluster not in clusters_in_colors:
                        clusters_in_colors.append(cluster)
                
                print(f"✅ Colori trovati: {len(colors)}")
                print(f"✅ Cluster nei colori: {sorted(clusters_in_colors)}")
            else:
                print("❌ Nessun colore nella cabina")
                return False
        else:
            print(f"❌ Errore API colori: {response.status_code}")
            return False
        
        print("\n2️⃣ Stato attuale ordine cluster...")
        response = requests.get(f"{base_url}/api/cabin/{cabin_id}/cluster_order", timeout=10)
        if response.status_code == 200:
            cluster_data = response.json()
            cluster_order = cluster_data.get('order', [])
            print(f"✅ Ordine cluster salvato: {cluster_order}")
            
            # Confronta cluster nell'ordine vs cluster nei colori
            clusters_in_order = set(cluster_order)
            clusters_in_colors_set = set(clusters_in_colors)
            
            extra_in_order = clusters_in_order - clusters_in_colors_set
            missing_in_order = clusters_in_colors_set - clusters_in_order
            
            if extra_in_order:
                print(f"⚠️  Cluster nell'ordine ma NON nei colori: {list(extra_in_order)}")
            if missing_in_order:
                print(f"⚠️  Cluster nei colori ma NON nell'ordine: {list(missing_in_order)}")
            
            if not extra_in_order and not missing_in_order:
                print("✅ Cluster perfettamente sincronizzati")
            else:
                print("❌ PROBLEMA: Cluster NON sincronizzati!")
                
        else:
            print(f"❌ Errore API cluster order: {response.status_code}")
            return False
        
        print("\n3️⃣ Test di aggiornamento...")
        
        # Forza un piccolo aggiornamento per testare la sincronizzazione
        test_colors = [
            {"code": "RAL9999", "type": "E", "lunghezza_ordine": "corto"},  # Test temporaneo
        ]
        
        # Prendi i colori esistenti e aggiungi il test
        all_colors = []
        for color in colors:
            all_colors.append({
                "code": color.get('color_code', color.get('code', '')),
                "type": color.get('color_type', color.get('type', '')),
                "lunghezza_ordine": color.get('lunghezza_ordine', 'corto'),
                "CH": color.get('ch_value', color.get('CH')),
                "sequence": color.get('input_sequence', color.get('sequence')),
                "sequence_type": color.get('sequence_type')
            })
        
        # Aggiungi il colore di test
        all_colors.extend(test_colors)
        
        payload = {
            "colors_today": all_colors,
            "start_cluster_name": None
        }
        
        print(f"Inviando {len(all_colors)} colori per ottimizzazione...")
        response = requests.post(f"{base_url}/api/optimize", json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Ottimizzazione completata")
            
            # Verifica l'ordine cluster dopo l'ottimizzazione
            import time
            time.sleep(2)  # Aspetta un momento
            
            response = requests.get(f"{base_url}/api/cabin/{cabin_id}/cluster_order", timeout=10)
            if response.status_code == 200:
                new_cluster_data = response.json()
                new_cluster_order = new_cluster_data.get('order', [])
                print(f"✅ Nuovo ordine cluster: {new_cluster_order}")
                
                # Verifica se è cambiato
                if new_cluster_order != cluster_order:
                    print("✅ Ordine cluster è stato aggiornato!")
                else:
                    print("❌ Ordine cluster NON è cambiato")
                    
            else:
                print("❌ Errore verifica nuovo ordine cluster")
        else:
            print(f"❌ Errore ottimizzazione: {response.status_code}")
            print(f"Dettagli: {response.text}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        return False

def main():
    """Test principale"""
    print("🚀 Debugging sincronizzazione cluster")
    print("Questo test analizzerà il problema di sincronizzazione")
    print("e tenterà di risolverlo")
    
    success = test_cluster_sync_issue()
    
    if success:
        print("\n🎯 SUGGERIMENTI PER IL DEBUG:")
        print("1. Apri la console del browser (F12)")
        print("2. Vai alla cabina: http://localhost:8080/cabin/1") 
        print("3. Clicca 'Aggiorna Cluster' e controlla i log della console")
        print("4. Verifica che le funzioni JavaScript siano chiamate")
        print("\n🔧 SE IL PROBLEMA PERSISTE:")
        print("- Controlla la console del browser per errori JavaScript")
        print("- Verifica che le funzioni syncClusterOrderWithColors e refreshClusterOrder siano definite")
        print("- Ricarica la pagina e riprova")
    else:
        print("\n❌ Test fallito - controlla gli errori sopra")

if __name__ == "__main__":
    main()
