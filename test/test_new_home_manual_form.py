#!/usr/bin/env python3
"""
Test del nuovo modulo di aggiunta manuale nella home page
"""
import requests
import json

def test_home_manual_form():
    """Test del modulo di aggiunta manuale nella home"""
    print("🧪 Test del modulo di aggiunta manuale nella home page")
    print("=" * 60)
    
    base_url = "http://localhost:8080"
    
    # Test 1: Verifica che la home page sia accessibile
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"✅ Home page accessibile: {response.status_code}")
    except Exception as e:
        print(f"❌ Errore accesso home page: {e}")
        return False
    
    # Test 2: Verifica endpoint clusters
    try:
        response = requests.get(f"{base_url}/api/clusters", timeout=10)
        clusters_data = response.json()
        print(f"✅ Clusters API funzionante: {len(clusters_data.get('clusters', []))} cluster disponibili")
        print(f"   Cluster: {', '.join(clusters_data.get('clusters', []))}")
    except Exception as e:
        print(f"❌ Errore endpoint clusters: {e}")
        return False
    
    # Test 3: Test ottimizzazione con lista manuale simulata
    test_colors = [
        {
            "code": "RAL1019", 
            "type": "R", 
            "lunghezza_ordine": "corto",
            "CH": 2.5
        },
        {
            "code": "RAL1007", 
            "type": "F", 
            "lunghezza_ordine": "lungo",
            "CH": 4.1
        },
        {
            "code": "RAL9001", 
            "type": "E", 
            "lunghezza_ordine": "corto",
            "CH": 1.8
        }
    ]
    
    payload = {
        "colors_today": test_colors,
        "start_cluster_name": "Bianco"
    }
    
    try:
        print("🔄 Test ottimizzazione con lista manuale...")
        response = requests.post(
            f"{base_url}/api/optimize", 
            json=payload, 
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Ottimizzazione completata con successo!")
            
            if 'cabina_1' in result and 'cabina_2' in result:
                print("📊 Risultati per cabine:")
                if result['cabina_1'].get('ordered_colors'):
                    print(f"   Cabina 1 (corto): {len(result['cabina_1']['ordered_colors'])} colori")
                if result['cabina_2'].get('ordered_colors'):
                    print(f"   Cabina 2 (lungo): {len(result['cabina_2']['ordered_colors'])} colori")
            else:
                print(f"📊 Risultati: {len(result.get('ordered_colors', []))} colori ottimizzati")
            
            return True
        else:
            print(f"❌ Errore ottimizzazione: {response.status_code}")
            print(f"   Messaggio: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante il test di ottimizzazione: {e}")
        return False

def test_cabin_status():
    """Test dell'endpoint stato cabine"""
    try:
        response = requests.get("http://localhost:8080/api/cabin-status", timeout=10)
        if response.status_code == 200:
            status_data = response.json()
            print("✅ Stato cabine disponibile:")
            for cabin, data in status_data.items():
                print(f"   {cabin}: {data.get('total', 0)} colori totali")
            return True
        else:
            print(f"❌ Errore stato cabine: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Errore endpoint stato cabine: {e}")
        return False

def main():
    """Esegue tutti i test"""
    print("🚀 Test completo del nuovo modulo di aggiunta manuale")
    print("=" * 80)
    
    tests_passed = 0
    total_tests = 2
    
    if test_home_manual_form():
        tests_passed += 1
    
    if test_cabin_status():
        tests_passed += 1
    
    print("\n" + "=" * 80)
    print(f"🏁 Risultati finali: {tests_passed}/{total_tests} test superati")
    
    if tests_passed == total_tests:
        print("🎉 TUTTI I TEST SUPERATI!")
        print("✅ Il modulo di aggiunta manuale nella home è funzionante")
        print("✅ L'interfaccia è pronta per l'uso")
        print("\n🎯 Come utilizzare il nuovo modulo:")
        print("1. Vai su http://localhost:8080")
        print("2. Compila il form 'Aggiungi Colori Manualmente'")
        print("3. Aggiungi colori alla lista temporanea")
        print("4. Imposta il cluster di partenza se necessario")
        print("5. Clicca 'Ottimizza Lista Manuale'")
        return True
    else:
        print("❌ Alcuni test sono falliti")
        return False

if __name__ == "__main__":
    main()
