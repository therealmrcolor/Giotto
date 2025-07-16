#!/usr/bin/env python3
"""
Integration test to verify frontend-backend communication in Docker.
Tests a complete optimization flow through the frontend interface.
"""

import requests
import json
import time

def test_frontend_backend_integration():
    """Test complete optimization flow through frontend."""
    
    print("🧪 Testing Frontend-Backend Integration...")
    print("=" * 50)
    
    # Test data for optimization
    test_payload = {
        'cabin_data': [
            {'cabin_id': 'C001', 'current_color': 'Bianco', 'priority': 1},
            {'cabin_id': 'C002', 'current_color': 'Giallo', 'priority': 2},
            {'cabin_id': 'C003', 'current_color': 'Rosso', 'priority': 3}
        ],
        'start_cluster_name': 'Bianco'
    }
    
    try:
        # Call the frontend optimization endpoint
        print("⏳ Sending optimization request to frontend...")
        response = requests.post(
            'http://localhost:8080/optimize_api',
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Optimization successful!")
            print(f"   - Ordered colors: {len(result.get('ordered_colors', []))}")
            print(f"   - Cluster sequence: {result.get('optimal_cluster_sequence', [])}")
            print(f"   - Total cost: {result.get('total_cost', 0):.2f}")
            print(f"   - Backend used: {result.get('backend_url', 'Unknown')}")
            return True
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

def test_backend_direct():
    """Test backend API directly."""
    print("\n🔧 Testing Backend API directly...")
    
    test_payload = {
        "cabin_data": [
            {"cabin_id": "C001", "current_color": "Bianco", "priority": 1},
            {"cabin_id": "C002", "current_color": "Giallo", "priority": 2},
            {"cabin_id": "C003", "current_color": "Rosso", "priority": 3}
        ],
        "start_cluster_name": "Bianco"
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
            print("✅ Direct backend call successful!")
            print(f"   - Cluster sequence: {result.get('optimal_cluster_sequence', [])}")
            print(f"   - Total cost: {result.get('total_cost', 0):.2f}")
            return True
        else:
            print(f"❌ Backend call failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Backend error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Frontend-Backend Integration Test")
    print("=" * 60)
    
    # Wait a moment for services to be ready
    time.sleep(2)
    
    # Run tests
    frontend_test = test_frontend_backend_integration()
    backend_test = test_backend_direct()
    
    print("\n" + "=" * 60)
    print("📊 Integration Test Results:")
    print(f"   Frontend-Backend Integration: {'✅ PASS' if frontend_test else '❌ FAIL'}")
    print(f"   Direct Backend API: {'✅ PASS' if backend_test else '❌ FAIL'}")
    
    if frontend_test and backend_test:
        print("\n🎉 All integration tests passed!")
        print("   The Docker setup is fully functional.")
    else:
        print("\n⚠️  Some tests failed. Check the logs above.")
    
    print("\n📋 Available Services:")
    print("   - Frontend: http://localhost:8080")
    print("   - Backend API: http://localhost:8000/docs")
