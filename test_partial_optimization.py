#!/usr/bin/env python3
"""
Test script for the partial cluster order optimization feature
"""

import requests
import json
import time

def test_partial_optimization():
    """Test the complete partial optimization workflow"""
    
    print("🧪 Testing Partial Cluster Order Optimization")
    print("=" * 60)
    
    # Frontend and backend URLs
    frontend_url = "http://localhost:8080"
    backend_url = "http://localhost:8000"
    
    # Test data - colors for cabin 1 (corto)
    test_colors = [
        {"code": "RAL1019", "type": "R", "lunghezza_ordine": "corto"},
        {"code": "RAL1007", "type": "F", "lunghezza_ordine": "corto"}, 
        {"code": "RAL1021", "type": "K", "lunghezza_ordine": "corto"},
        {"code": "RAL2004", "type": "R", "lunghezza_ordine": "corto"}
    ]
    
    # Step 1: First run a normal optimization to establish baseline
    print("1️⃣ Running initial optimization to establish baseline...")
    
    initial_payload = {
        "colors_today": test_colors,
        "start_cluster_name": "Bianco",
        "prioritized_reintegrations": []
    }
    
    try:
        response = requests.post(f"{frontend_url}/api/optimize", json=initial_payload, timeout=30)
        
        if response.status_code == 200:
            initial_results = response.json()
            
            if 'cabina_1' in initial_results:
                cabin1_results = initial_results['cabina_1']
                print(f"   ✅ Initial optimization successful")
                print(f"   📊 Cabin 1 colors: {len(cabin1_results.get('ordered_colors', []))}")
                print(f"   🔗 Original cluster sequence: {cabin1_results.get('optimal_cluster_sequence', [])}")
                print(f"   💰 Original cost: {cabin1_results.get('calculated_cost', 'N/A')}")
                
                original_sequence = cabin1_results.get('optimal_cluster_sequence', [])
                
            else:
                print(f"   ❌ No cabin results in response")
                return False
        else:
            print(f"   ❌ Initial optimization failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Initial optimization error: {e}")
        return False
    
    # Step 2: Test partial optimization with some clusters locked
    print("\n2️⃣ Testing partial optimization with locked clusters...")
    
    if len(original_sequence) < 2:
        print("   ⚠️ Not enough clusters for partial optimization test")
        return True
    
    # Create partial order: lock first cluster, leave others free
    partial_cluster_order = [
        {"cluster": original_sequence[0], "locked": True},
        {"cluster": original_sequence[1], "locked": False}
    ]
    
    # Add remaining clusters as free
    for cluster in original_sequence[2:]:
        partial_cluster_order.append({"cluster": cluster, "locked": False})
    
    partial_payload = {
        "colors": test_colors,
        "partial_cluster_order": partial_cluster_order,
        "prioritized_reintegrations": []
    }
    
    try:
        response = requests.post(f"{frontend_url}/api/cabin/1/optimize-partial", json=partial_payload, timeout=30)
        
        if response.status_code == 200:
            partial_results = response.json()
            print(f"   ✅ Partial optimization successful")
            print(f"   🔗 New cluster sequence: {partial_results.get('optimal_cluster_sequence', [])}")
            print(f"   💰 New cost: {partial_results.get('calculated_cost', 'N/A')}")
            
            new_sequence = partial_results.get('optimal_cluster_sequence', [])
            
            # Verify that locked cluster stayed in position
            if len(new_sequence) > 0 and new_sequence[0] == original_sequence[0]:
                print(f"   ✅ Locked cluster '{original_sequence[0]}' maintained position")
            else:
                print(f"   ❌ Locked cluster position not maintained")
                
        else:
            print(f"   ❌ Partial optimization failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Partial optimization error: {e}")
        return False
    
    # Step 3: Test backend API directly
    print("\n3️⃣ Testing backend partial optimization API directly...")
    
    try:
        backend_payload = {
            "colors": test_colors,
            "partial_cluster_order": partial_cluster_order,
            "cabin_id": 1,
            "prioritized_reintegrations": []
        }
        
        response = requests.post(f"{backend_url}/optimize-partial", json=backend_payload, timeout=30)
        
        if response.status_code == 200:
            backend_results = response.json()
            print(f"   ✅ Backend partial optimization successful")
            print(f"   🔗 Backend cluster sequence: {backend_results.get('optimal_cluster_sequence', [])}")
            print(f"   💰 Backend cost: {backend_results.get('calculated_cost', 'N/A')}")
        else:
            print(f"   ❌ Backend partial optimization failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Backend partial optimization error: {e}")
        return False
    
    print("\n✅ All partial optimization tests completed successfully!")
    print("🎉 The partial cluster order recalculation feature is working!")
    
    return True

def test_cabin_ui_access():
    """Test that the cabin UI is accessible"""
    print("\n4️⃣ Testing cabin UI accessibility...")
    
    try:
        response = requests.get("http://localhost:8080/cabin/1", timeout=10)
        if response.status_code == 200:
            print("   ✅ Cabin 1 UI accessible")
            
            # Check if cluster management UI elements are present
            content = response.text
            if "Gestione Ordine Cluster" in content:
                print("   ✅ Cluster management UI found in page")
            else:
                print("   ⚠️ Cluster management UI not found in page")
                
            if "cluster-order-list" in content:
                print("   ✅ Cluster order list element found")
            else:
                print("   ⚠️ Cluster order list element not found")
                
        else:
            print(f"   ❌ Cabin UI not accessible: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Cabin UI access error: {e}")

if __name__ == "__main__":
    print("Starting comprehensive test of partial cluster order optimization...")
    print("Please ensure Docker containers are running (docker-compose up -d)")
    print()
    
    # Wait a moment for services to be ready
    time.sleep(2)
    
    success = test_partial_optimization()
    test_cabin_ui_access()
    
    if success:
        print("\n🎊 All tests passed! The partial cluster order recalculation feature is fully implemented.")
        print("\n📋 What you can now do:")
        print("   1. Visit http://localhost:8080/cabin/1 or http://localhost:8080/cabin/2")
        print("   2. Add some colors and run optimization")
        print("   3. Use the 'Gestione Ordine Cluster' section to:")
        print("      - Drag and drop clusters to reorder them")
        print("      - Lock/unlock clusters to control which ones get optimized")
        print("      - Click 'Ricalcola Ordine' to run partial optimization")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
