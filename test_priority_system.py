#!/usr/bin/env python3
"""
Test script to verify priority-based color sequence optimization system
"""

import requests
import json
import sqlite3

# Test data with specific colors that will demonstrate priority handling
test_data_with_priorities = {
    "colors_today": [
        {
            "code": "RAL7048",
            "type": "E",
            "CH": 1.5,
            "lunghezza_ordine": "corto"
        },
        {
            "code": "RAL5017", 
            "type": "K",
            "CH": 3.2,
            "lunghezza_ordine": "lungo"
        },
        {
            "code": "69115038",  # This will be marked as priority
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
            "code": "160024",    # This will also be marked as priority
            "type": "F",
            "CH": 4.1,
            "lunghezza_ordine": "lungo"
        },
        {
            "code": "20889000",
            "type": "E",
            "CH": 1.2,
            "lunghezza_ordine": "corto"
        }
    ],
    "start_cluster_name": "Grigio Scuro",  # Specific start point
    "prioritized_reintegrations": ["69115038", "160024"]  # Two priority colors
}

def test_backend_priority_handling():
    """Test backend API with priority handling"""
    print("=== Testing Backend API with Priorities ===")
    try:
        response = requests.post("http://127.0.0.1:8001/optimize", json=test_data_with_priorities, timeout=30)
        response.raise_for_status()
        results = response.json()
        
        cabina_1 = results.get('cabina_1', {})
        cabina_2 = results.get('cabina_2', {})
        
        print(f"✅ Backend API works with priorities")
        print(f"  Cabina 1: {len(cabina_1.get('ordered_colors', []))} colors")
        print(f"  Cabina 2: {len(cabina_2.get('ordered_colors', []))} colors")
        
        # Check if priority colors are handled
        all_colors = cabina_1.get('ordered_colors', []) + cabina_2.get('ordered_colors', [])
        priority_colors_found = []
        for color in all_colors:
            if color.get('color_code') in test_data_with_priorities["prioritized_reintegrations"]:
                priority_colors_found.append(color.get('color_code'))
                print(f"  Priority color found: {color.get('color_code')} -> {color.get('cluster_name')}")
        
        if len(priority_colors_found) == len(test_data_with_priorities["prioritized_reintegrations"]):
            print("✅ All priority colors handled correctly")
        else:
            print(f"⚠️  Expected {len(test_data_with_priorities['prioritized_reintegrations'])} priority colors, found {len(priority_colors_found)}")
            
        return results
    except Exception as e:
        print(f"❌ Backend API failed: {e}")
        return None

def test_frontend_priority_handling():
    """Test frontend API endpoint with priority handling"""
    print("\n=== Testing Frontend API with Priorities ===")
    try:
        # Print the payload we're sending
        print(f"Sending payload with prioritized_reintegrations: {test_data_with_priorities['prioritized_reintegrations']}")
        
        # First clear the database to ensure a clean slate
        try:
            db_path = "/Users/baldi/H-Farm/tesi/swdevel-lab-hfarm-master copy/frontend/app/data/colors.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM optimization_colors")
            conn.commit()
            conn.close()
            print("Database cleared before test")
        except Exception as e:
            print(f"Error clearing database: {e}")
        
        response = requests.post("http://127.0.0.1:5001/api/optimize", json=test_data_with_priorities, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Frontend API failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        results = response.json()
        cabina_1 = results.get('cabina_1', {})
        cabina_2 = results.get('cabina_2', {})
        
        print(f"✅ Frontend API works with priorities")
        print(f"  Cabina 1: {len(cabina_1.get('ordered_colors', []))} colors")
        print(f"  Cabina 2: {len(cabina_2.get('ordered_colors', []))} colors")
        
        # Check cluster sequence
        cluster_sequence = results.get('optimal_cluster_sequence', [])
        if cluster_sequence:
            print(f"  Optimal cluster sequence: {' -> '.join(cluster_sequence)}")
            
            # Verify start cluster was respected
            start_cluster = test_data_with_priorities.get('start_cluster_name')
            if start_cluster and cluster_sequence and cluster_sequence[0] == start_cluster:
                print(f"✅ Start cluster '{start_cluster}' was respected")
            elif start_cluster:
                print(f"⚠️  Start cluster '{start_cluster}' was not respected, got '{cluster_sequence[0] if cluster_sequence else 'none'}'")
        
        return results
    except Exception as e:
        print(f"❌ Frontend API failed: {e}")
        return None

def test_reoptimization_workflow():
    """Test re-optimization with changed priorities"""
    print("\n=== Testing Re-optimization Workflow ===")
    
    # First optimization - no priorities
    test_data_no_priority = test_data_with_priorities.copy()
    test_data_no_priority["prioritized_reintegrations"] = []
    
    try:
        print("Step 1: Initial optimization (no priorities)")
        response1 = requests.post("http://127.0.0.1:5001/api/optimize", json=test_data_no_priority, timeout=30)
        response1.raise_for_status()
        results1 = response1.json()
        
        cluster_seq1 = results1.get('optimal_cluster_sequence', [])
        print(f"  Initial sequence: {' -> '.join(cluster_seq1)}")
        
        print("Step 2: Re-optimization with priorities")
        response2 = requests.post("http://127.0.0.1:5001/api/optimize", json=test_data_with_priorities, timeout=30)
        response2.raise_for_status()
        results2 = response2.json()
        
        cluster_seq2 = results2.get('optimal_cluster_sequence', [])
        print(f"  Priority sequence: {' -> '.join(cluster_seq2)}")
        
        # Check if the sequences are different (priorities should influence optimization)
        if cluster_seq1 != cluster_seq2:
            print("✅ Priority handling changed the optimization result")
        else:
            print("ℹ️  Priority handling resulted in the same sequence (may be optimal)")
            
        return True
    except Exception as e:
        print(f"❌ Re-optimization workflow failed: {e}")
        return False

def check_priority_database_storage():
    """Check if priority flags are stored correctly in database"""
    print("\n=== Checking Priority Storage in Database ===")
    try:
        db_path = "/Users/baldi/H-Farm/tesi/swdevel-lab-hfarm-master copy/frontend/app/data/colors.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check all records
        print("All records in database:")
        cursor.execute("SELECT color_code, is_prioritized FROM optimization_colors")
        all_colors = cursor.fetchall()
        for color_code, is_prioritized in all_colors:
            print(f"  - {color_code} (priority: {is_prioritized})")
        
        # Check if we have priority colors in database
        cursor.execute("SELECT color_code, is_prioritized FROM optimization_colors WHERE is_prioritized = 1")
        priority_colors = cursor.fetchall()
        
        print(f"Found {len(priority_colors)} priority colors in database:")
        for color_code, is_prioritized in priority_colors:
            print(f"  - {color_code} (priority: {is_prioritized})")
        
        # Check total records
        cursor.execute("SELECT count(*) FROM optimization_colors")
        total_count = cursor.fetchone()[0]
        print(f"Total colors in database: {total_count}")
        
        # Check expected priority colors
        expected_priorities = test_data_with_priorities["prioritized_reintegrations"]
        print(f"Expected priority colors: {expected_priorities}")
        
        # Check if expected priorities are in the database
        actual_priorities = [color_code for color_code, _ in priority_colors]
        missing_priorities = set(expected_priorities) - set(actual_priorities)
        if missing_priorities:
            print(f"Missing priority colors in database: {missing_priorities}")
        
        conn.close()
        return len(priority_colors) > 0
        
    except Exception as e:
        print(f"❌ Database priority check failed: {e}")
        return False

def main():
    print("Priority-Based Color Optimization Test")
    print("=" * 50)
    
    # Test backend API with priorities
    backend_results = test_backend_priority_handling()
    
    # Test frontend API with priorities  
    frontend_results = test_frontend_priority_handling()
    
    # Test re-optimization workflow
    reoptimization_success = test_reoptimization_workflow()
    
    # Check database storage of priorities
    db_priority_storage = check_priority_database_storage()
    
    print("\n" + "=" * 50)
    print("PRIORITY SYSTEM SUMMARY:")
    print(f"✅ Backend Priority Handling: {'Working' if backend_results else 'Failed'}")
    print(f"✅ Frontend Priority Handling: {'Working' if frontend_results else 'Failed'}")
    print(f"✅ Re-optimization Workflow: {'Working' if reoptimization_success else 'Failed'}")
    print(f"✅ Database Priority Storage: {'Working' if db_priority_storage else 'Failed'}")
    
    if all([backend_results, frontend_results, reoptimization_success, db_priority_storage]):
        print("\n🎉 PRIORITY SYSTEM FULLY FUNCTIONAL!")
    else:
        print("\n⚠️  Some priority system components need attention")

if __name__ == "__main__":
    main()
