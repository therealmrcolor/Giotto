#!/usr/bin/env python3
"""
Simple test to verify partial optimization functionality
"""
import requests
import json

def test_basic_functionality():
    print("🧪 Testing basic partial optimization functionality...")
    
    # Test payload
    payload = {
        "colors": [
            {"code": "RAL1019", "type": "R", "CH": 2.5, "lunghezza_ordine": "corto"},
            {"code": "RAL1007", "type": "F", "CH": 4.1, "lunghezza_ordine": "corto"},
            {"code": "RAL1021", "type": "K", "CH": 3.8, "lunghezza_ordine": "corto"}
        ],
        "partial_cluster_order": [
            {"cluster": "Giallo", "position": 0, "locked": False}
        ],
        "cabin_id": 1,
        "prioritized_reintegrations": []
    }
    
    try:
        # Test frontend API
        response = requests.post(
            "http://localhost:8080/api/cabin/1/optimize-partial",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Frontend API: {len(result.get('ordered_colors', []))} colors optimized")
            print(f"   Cluster sequence: {' → '.join(result.get('optimal_cluster_sequence', []))}")
            
            # Test cluster order endpoints
            cluster_response = requests.get("http://localhost:8080/api/cabin/1/cluster_order")
            if cluster_response.status_code == 200:
                cluster_data = cluster_response.json()
                print(f"✅ Cluster order endpoint: {cluster_data.get('order', [])}")
            else:
                print(f"❌ Cluster order endpoint failed: {cluster_response.status_code}")
                
            return True
        else:
            print(f"❌ Frontend API failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_ui_elements():
    print("🖥️  Testing UI elements...")
    
    try:
        response = requests.get("http://localhost:8080/cabin/1")
        if response.status_code == 200:
            content = response.text
            ui_checks = {
                "Cluster management UI": "Gestione Ordine Cluster" in content,
                "Sortable functionality": "initSortable" in content,
                "jQuery UI": "jquery-ui" in content,
                "Partial optimization endpoint": "/api/cabin/1/optimize-partial" in content
            }
            
            all_passed = True
            for check_name, passed in ui_checks.items():
                status = "✅" if passed else "❌"
                print(f"   {status} {check_name}")
                if not passed:
                    all_passed = False
                    
            return all_passed
        else:
            print(f"❌ Cannot access cabin UI: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ UI test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Quick partial optimization test")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_basic_functionality():
        tests_passed += 1
    
    if test_ui_elements():
        tests_passed += 1
        
    print("\n" + "=" * 50)
    print(f"🏁 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Partial optimization is working!")
    else:
        print("⚠️  Some tests failed")
