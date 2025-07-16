#!/usr/bin/env python3
"""
Comprehensive test for the partial cluster order optimization feature.
Tests both API endpoints and UI functionality.
"""

import requests
import json
import time
import sys

def test_cluster_endpoints():
    """Test the cluster order management endpoints"""
    print("🔍 Testing cluster order endpoints...")
    
    # Test cluster order endpoint
    try:
        response = requests.get("http://localhost:8080/api/cabin/1/cluster_order", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Cluster order endpoint working: {data}")
        else:
            print(f"   ❌ Cluster order endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cluster order endpoint error: {e}")
        return False
    
    # Test original cluster order endpoint
    try:
        response = requests.get("http://localhost:8080/api/cabin/1/original_cluster_order", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Original cluster order endpoint working: {data}")
        else:
            print(f"   ❌ Original cluster order endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Original cluster order endpoint error: {e}")
        return False
    
    return True

def test_partial_optimization_api():
    """Test the partial optimization API with proper payload structure"""
    print("🧪 Testing partial optimization API...")
    
    # Create test payload matching the expected structure
    test_payload = {
        "colors": [
            {
                "code": "RAL1019",
                "type": "R",
                "CH": 2.5,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "RAL1007",
                "type": "F",
                "CH": 4.1,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "RAL1021",
                "type": "K",
                "CH": 3.8,
                "lunghezza_ordine": "corto"
            }
        ],
        "partial_cluster_order": [
            {
                "cluster": "Giallo",
                "position": 0,
                "locked": False
            }
        ],
        "prioritized_reintegrations": []
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/api/cabin/1/optimize-partial",
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"   ✅ Partial optimization API working")
            print(f"   📊 Results: {len(results.get('ordered_colors', []))} colors optimized")
            print(f"   🔗 Cluster sequence: {' → '.join(results.get('optimal_cluster_sequence', []))}")
            return True
        else:
            print(f"   ❌ Partial optimization API failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Partial optimization API error: {e}")
        return False

def test_cabin_ui_accessibility():
    """Test that the cabin UI loads without errors"""
    print("🖥️  Testing cabin UI accessibility...")
    
    try:
        response = requests.get("http://localhost:8080/cabin/1", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # Check for key UI elements
            ui_elements = [
                "Gestione Ordine Cluster",
                "cluster-order-list",
                "recalculateBtn",
                "jQuery UI",
                "initSortable"
            ]
            
            missing_elements = []
            for element in ui_elements:
                if element not in content:
                    missing_elements.append(element)
            
            if not missing_elements:
                print("   ✅ All required UI elements found")
                return True
            else:
                print(f"   ⚠️  Missing UI elements: {missing_elements}")
                return False
        else:
            print(f"   ❌ Cabin UI not accessible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Cabin UI accessibility error: {e}")
        return False

def test_full_workflow():
    """Test a complete workflow from optimization to partial reoptimization"""
    print("🔄 Testing complete workflow...")
    
    # Step 1: Basic optimization
    basic_payload = {
        "colors_today": [
            {
                "code": "RAL1019",
                "type": "R",
                "CH": 2.5,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "RAL1007",
                "type": "F", 
                "CH": 4.1,
                "lunghezza_ordine": "corto"
            },
            {
                "code": "RAL1021",
                "type": "K",
                "CH": 3.8,
                "lunghezza_ordine": "corto"
            }
        ],
        "start_cluster_name": None,
        "prioritized_reintegrations": []
    }
    
    try:
        # Basic optimization
        print("   📝 Step 1: Running basic optimization...")
        response = requests.post(
            "http://localhost:8080/api/optimize",
            json=basic_payload,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"   ❌ Basic optimization failed: {response.status_code}")
            return False
            
        initial_results = response.json()
        cabin_1_results = initial_results.get('cabina_1', {})
        initial_colors = cabin_1_results.get('ordered_colors', [])
        initial_sequence = cabin_1_results.get('optimal_cluster_sequence', [])
        
        print(f"   ✅ Initial optimization: {len(initial_colors)} colors, sequence: {' → '.join(initial_sequence)}")
        
        if not initial_colors:
            print("   ❌ No colors returned from initial optimization")
            return False
        
        # Step 2: Get current cluster order
        print("   📝 Step 2: Getting current cluster order...")
        response = requests.get("http://localhost:8080/api/cabin/1/cluster_order")
        
        if response.status_code != 200:
            print(f"   ❌ Failed to get cluster order: {response.status_code}")
            return False
            
        cluster_data = response.json()
        current_clusters = cluster_data.get('order', [])
        
        print(f"   ✅ Current clusters: {current_clusters}")
        
        # Step 3: Partial optimization with some locked clusters
        if len(current_clusters) > 0:
            print("   📝 Step 3: Running partial optimization with locked clusters...")
            
            partial_payload = {
                "colors": [
                    {
                        "code": color.get('code', ''),
                        "type": color.get('type', ''),
                        "CH": color.get('CH', 0),
                        "lunghezza_ordine": color.get('lunghezza_ordine', 'corto')
                    }
                    for color in initial_colors
                ],
                "partial_cluster_order": [
                    {
                        "cluster": cluster,
                        "position": idx,
                        "locked": idx == 0  # Lock first cluster
                    }
                    for idx, cluster in enumerate(current_clusters)
                ],
                "prioritized_reintegrations": []
            }
            
            response = requests.post(
                "http://localhost:8080/api/cabin/1/optimize-partial",
                json=partial_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                partial_results = response.json()
                partial_colors = partial_results.get('ordered_colors', [])
                partial_sequence = partial_results.get('optimal_cluster_sequence', [])
                
                print(f"   ✅ Partial optimization: {len(partial_colors)} colors, sequence: {' → '.join(partial_sequence)}")
                return True
            else:
                print(f"   ❌ Partial optimization failed: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                return False
        else:
            print("   ⚠️  No clusters found for partial optimization test")
            return True
            
    except Exception as e:
        print(f"   ❌ Workflow test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting comprehensive partial optimization tests...")
    print("=" * 60)
    
    tests = [
        ("Cluster Endpoints", test_cluster_endpoints),
        ("Partial Optimization API", test_partial_optimization_api),
        ("Cabin UI Accessibility", test_cabin_ui_accessibility),
        ("Full Workflow", test_full_workflow)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Partial optimization feature is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
