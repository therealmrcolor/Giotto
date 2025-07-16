#!/usr/bin/env python3
"""
Test script to verify end-to-end color optimization workflow
"""

import requests
import json
import sqlite3

# Test data
test_data = {
    "colors_today": [
        {
            "code": "RAL7048",
            "type": "E",
            "CH": 1.5,
            "lunghezza_ordine": "corto"
        },
        {
            "code": "RAL7044",
            "type": "E",
            "CH": 2.0,
            "lunghezza_ordine": "corto"
        },
        {
            "code": "RAL5017",
            "type": "K",
            "CH": 3.2,
            "lunghezza_ordine": "lungo"
        },
        {
            "code": "69115038",
            "type": "R",
            "CH": 1.8,
            "lunghezza_ordine": "corto"
        },
        {
            "code": "RAL1019",
            "type": "RE",
            "CH": 2.5,
            "lunghezza_ordine": "lungo"
        },
        {
            "code": "160024",
            "type": "F",
            "CH": 4.1,
            "lunghezza_ordine": "lungo"
        },
        {
            "code": "20889000",
            "type": "E",
            "CH": 1.2,
            "lunghezza_ordine": "corto"
        },
        {
            "code": "54864032",
            "type": "K",
            "CH": 3.8,
            "lunghezza_ordine": "lungo"
        }
    ],
    "start_cluster_name": None,
    "prioritized_reintegrations": ["69115038"]
}

def test_backend_api():
    """Test backend API directly"""
    print("=== Testing Backend API ===")
    try:
        response = requests.post("http://127.0.0.1:8001/optimize", json=test_data, timeout=30)
        response.raise_for_status()
        results = response.json()
        print(f"✅ Backend API works: {len(results.get('cabina_1', {}).get('ordered_colors', []))} + {len(results.get('cabina_2', {}).get('ordered_colors', []))} colors optimized")
        return results
    except Exception as e:
        print(f"❌ Backend API failed: {e}")
        return None

def test_frontend_api():
    """Test frontend API endpoint (what the frontend actually uses)"""
    print("\n=== Testing Frontend API Endpoint ===")
    try:
        # Use the same endpoint that the frontend JavaScript uses
        response = requests.post("http://127.0.0.1:5001/api/optimize", json=test_data, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Frontend API failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        results = response.json()
        print(f"✅ Frontend API works: {len(results.get('cabina_1', {}).get('ordered_colors', []))} + {len(results.get('cabina_2', {}).get('ordered_colors', []))} colors optimized")
        return results
    except Exception as e:
        print(f"❌ Frontend API failed: {e}")
        return None

def check_database():
    """Check database for saved results"""
    print("\n=== Checking Database ===")
    try:
        db_path = "/Users/baldi/H-Farm/tesi/swdevel-lab-hfarm-master copy/frontend/app/data/colors.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if optimization_colors table exists and has data
        cursor.execute("SELECT count(*) FROM optimization_colors")
        count = cursor.fetchone()[0]
        print(f"optimization_colors table has {count} records")
        
        if count > 0:
            # Show some sample data
            cursor.execute("""
                SELECT color_code, color_type, cluster, cabin_id, is_prioritized, completed, in_execution 
                FROM optimization_colors 
                ORDER BY sequence_order 
                LIMIT 5
            """)
            rows = cursor.fetchall()
            print("Sample data:")
            for row in rows:
                print(f"  {row[0]} ({row[1]}) -> {row[2]} | Cabin: {row[3]} | Priority: {row[4]} | Complete: {row[5]} | Executing: {row[6]}")
        
        conn.close()
        return count > 0
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def main():
    print("Color Optimization End-to-End Test")
    print("="*50)
    
    # Test backend API
    backend_results = test_backend_api()
    
    # Test frontend API endpoint (what the frontend actually uses)
    frontend_results = test_frontend_api()
    
    # Check database
    db_has_data = check_database()
    
    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"✅ Backend API: {'Working' if backend_results else 'Failed'}")
    print(f"✅ Frontend API: {'Working' if frontend_results else 'Failed'}")
    print(f"✅ Database Save: {'Working' if db_has_data else 'No data saved'}")
    
    if backend_results and frontend_results and db_has_data:
        print("\n🎉 END-TO-END WORKFLOW COMPLETE!")
    else:
        print("\n⚠️  Some components need attention")

if __name__ == "__main__":
    main()
