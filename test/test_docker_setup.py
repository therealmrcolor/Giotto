#!/usr/bin/env python3
"""
Test script to verify the Docker setup is working correctly.
Tests both backend API and frontend connectivity.
"""

import requests
import json
import time

def test_backend_health():
    """Test if backend is responding"""
    try:
        response = requests.get("http://localhost:8000/docs")
        print(f"✅ Backend health check: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        return False

def test_frontend_health():
    """Test if frontend is responding"""
    try:
        response = requests.get("http://localhost:8080")
        print(f"✅ Frontend health check: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Frontend health check failed: {e}")
        return False

def test_optimization_api():
    """Test the optimization API with real data"""
    try:
        url = "http://localhost:8000/optimize"
        payload = {
            "colors_today": [
                {"code": "RAL1019", "type": "R"},
                {"code": "RAL1007", "type": "F"},
                {"code": "RAL1021", "type": "K"}
            ],
            "start_cluster_name": "Bianco",
            "prioritized_reintegrations": []
        }
        
        response = requests.post(url, json=payload)
        print(f"✅ Optimization API test: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   - Ordered colors: {len(result['ordered_colors'])}")
            print(f"   - Cluster sequence: {result['optimal_cluster_sequence']}")
            print(f"   - Cost: {result['calculated_cost']}")
            return True
        else:
            print(f"   - Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Optimization API test failed: {e}")
        return False

def test_frontend_db_connectivity():
    """Test if frontend can access database"""
    try:
        response = requests.get("http://localhost:8080/db-check")
        print(f"✅ Frontend DB connectivity test: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   - DB connection: {result['connection']}")
            print(f"   - DB path: {result['database_path']}")
            return result['connection']
        else:
            print(f"   - Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Frontend DB connectivity test failed: {e}")
        return False

def main():
    print("🐳 Testing Docker setup...")
    print("=" * 50)
    
    # Wait a moment for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(2)
    
    # Run tests
    tests = [
        ("Backend Health", test_backend_health),
        ("Frontend Health", test_frontend_health),
        ("Backend Optimization API", test_optimization_api),
        ("Frontend DB Connectivity", test_frontend_db_connectivity)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Docker setup is working correctly.")
        print("\n📋 Services available at:")
        print("   - Frontend: http://localhost:8080")
        print("   - Backend API docs: http://localhost:8000/docs")
    else:
        print("❌ Some tests failed. Please check the logs above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
