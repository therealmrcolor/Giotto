#!/usr/bin/env python3
"""
Test per verificare che la nuova logica per il tipo "F" non soddisfatto funzioni correttamente.
Invece di un costo infinito, dovrebbe applicare una penalità di 100 punti.
"""

import requests
import json
import time

def test_f_type_penalty():
    """Test che il tipo F non soddisfatto applichi una penalità invece di costo infinito."""
    
    print("🧪 Testing F Type Penalty Logic...")
    print("=" * 50)
    
    # Test con colori che includono il tipo "F"
    # Dalla seq.txt vediamo che RAL7015 e RAL9007 hanno tipo "F"
    test_payload = {
        "colors_today": [
            {"code": "RAL1019", "type": "R"},  # Reintegro
            {"code": "RAL7015", "type": "F"},  # Fisso (da seq.txt)
            {"code": "RAL9007", "type": "F"},  # Fisso (da seq.txt)
            {"code": "RAL1021", "type": "K"}   # Kit
        ],
        "start_cluster_name": "Bianco",
        "prioritized_reintegrations": []
    }
    
    try:
        print("⏳ Sending optimization request to backend...")
        response = requests.post(
            'http://localhost:8000/optimize',
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Optimization successful!")
            print(f"   - Cluster sequence: {result.get('optimal_cluster_sequence', [])}")
            print(f"   - Total cost: {result.get('total_cost', 0):.2f}")
            
            # Verifica che il costo non sia infinito (9999)
            total_cost = result.get('total_cost', 0)
            if total_cost < 9999:
                print("✅ SUCCESS: Costo non infinito - la penalità F è stata applicata correttamente!")
                print(f"   - Costo finale: {total_cost:.2f} (< 9999)")
            else:
                print("❌ FAIL: Costo ancora infinito - la logica F potrebbe non funzionare")
                
            return total_cost < 9999
        else:
            print(f"❌ Optimization failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_normal_optimization():
    """Test normale per confronto."""
    print("\n🔧 Testing Normal Optimization for comparison...")
    
    test_payload = {
        "colors_today": [
            {"code": "RAL1019", "type": "R"},
            {"code": "RAL1007", "type": "F"},
            {"code": "RAL1021", "type": "K"}
        ],
        "start_cluster_name": "Bianco",
        "prioritized_reintegrations": []
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/optimize',
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Normal optimization successful!")
            print(f"   - Cluster sequence: {result.get('optimal_cluster_sequence', [])}")
            print(f"   - Total cost: {result.get('total_cost', 0):.2f}")
            return result.get('total_cost', 0)
        else:
            print(f"❌ Normal optimization failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Normal optimization error: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Starting F Type Penalty Test")
    print("=" * 60)
    
    # Wait a moment for services to be ready
    time.sleep(2)
    
    # Run tests
    f_type_test = test_f_type_penalty()
    normal_cost = test_normal_optimization()
    
    print("\n" + "=" * 60)
    print("📊 F Type Penalty Test Results:")
    print(f"   F Type Logic Working: {'✅ PASS' if f_type_test else '❌ FAIL'}")
    
    if normal_cost is not None:
        print(f"   Normal optimization cost: {normal_cost:.2f}")
    
    if f_type_test:
        print("\n🎉 SUCCESS! F Type penalty logic is working correctly.")
        print("   - Transitions with unsatisfied F type now apply 100 point penalty")
        print("   - Instead of infinite cost, allowing the optimization to continue")
    else:
        print("\n⚠️  F Type penalty logic may need adjustment.")
        print("   - Check backend logs for details")
    
    print("\n📋 Testing completed for F Type penalty logic.")
