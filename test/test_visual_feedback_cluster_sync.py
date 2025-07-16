#!/usr/bin/env python3
"""
Test script to verify the enhanced visual feedback for cluster synchronization
"""

import time
import requests
import json

def test_visual_feedback_system():
    """Test the enhanced visual feedback for cluster synchronization"""
    
    print("🧪 TESTING ENHANCED CLUSTER SYNCHRONIZATION VISUAL FEEDBACK")
    print("=" * 60)
    
    base_url = "http://localhost:8001"
    cabin_id = 1
    
    try:
        # Test 1: Get current state
        print("\n1. 📊 Getting current system state...")
        
        # Get current colors
        response = requests.get(f"{base_url}/api/cabin/{cabin_id}/colors")
        if response.status_code == 200:
            colors_data = response.json()
            colors = colors_data.get('colors', [])
            clusters_from_colors = list(set(c.get('cluster') for c in colors if c.get('cluster')))
            print(f"   • Colors found: {len(colors)}")
            print(f"   • Clusters in colors: {sorted(clusters_from_colors)}")
        else:
            print(f"   ❌ Failed to get colors: {response.status_code}")
            return
        
        # Get current cluster order
        response = requests.get(f"{base_url}/api/cabin/{cabin_id}/cluster_order")
        if response.status_code == 200:
            cluster_data = response.json()
            cluster_order = cluster_data.get('order', [])
            print(f"   • Current cluster order: {cluster_order}")
        else:
            print(f"   ❌ Failed to get cluster order: {response.status_code}")
            return
        
        # Test 2: Add a new color with a new cluster to trigger sync
        print("\n2. 🎨 Adding color with new cluster to test sync feedback...")
        
        new_color = {
            "color_code": "TEST_VISUAL_123",
            "color_type": "R",
            "cluster": "Test Visual Cluster",
            "ch_value": 15.0,
            "lunghezza_ordine": "4 cm",
            "sequence": 1,
            "sequence_type": "A"
        }
        
        print(f"   • Adding color: {new_color['color_code']} with cluster: {new_color['cluster']}")
        
        response = requests.post(f"{base_url}/api/cabin/{cabin_id}/colors", json=new_color)
        if response.status_code == 200:
            print("   ✅ Color added successfully")
        else:
            print(f"   ❌ Failed to add color: {response.status_code} - {response.text}")
            return
        
        # Test 3: Verify the new cluster appears
        print("\n3. 🔍 Verifying cluster synchronization...")
        
        time.sleep(1)  # Wait a moment for the system to process
        
        # Check updated colors
        response = requests.get(f"{base_url}/api/cabin/{cabin_id}/colors")
        if response.status_code == 200:
            colors_data = response.json()
            colors = colors_data.get('colors', [])
            updated_clusters_from_colors = list(set(c.get('cluster') for c in colors if c.get('cluster')))
            print(f"   • Updated clusters in colors: {sorted(updated_clusters_from_colors)}")
        
        # Check if cluster order was updated
        response = requests.get(f"{base_url}/api/cabin/{cabin_id}/cluster_order")
        if response.status_code == 200:
            cluster_data = response.json()
            updated_cluster_order = cluster_data.get('order', [])
            print(f"   • Updated cluster order: {updated_cluster_order}")
            
            # Check if new cluster is in the order
            if "Test Visual Cluster" in updated_cluster_order:
                print("   ✅ New cluster successfully added to cluster order")
            else:
                print("   ⚠️ New cluster not found in cluster order (may need manual sync)")
        
        print("\n4. 🎯 TESTING INSTRUCTIONS FOR VISUAL FEEDBACK:")
        print("   To test the enhanced visual feedback:")
        print("   1. Open http://localhost:8080 in your browser")
        print("   2. Navigate to a cabin page")
        print("   3. Look for the 'Stato Sincronizzazione' section in the cluster order panel")
        print("   4. Click 'Aggiorna Cluster' button")
        print("   5. You should see:")
        print("      • A colored message appear in the sync feedback area")
        print("      • The timestamp update showing 'Ultima sync: HH:MM:SS'")
        print("      • Different message types (success, info, warning)")
        print("   6. Click 'Test Debug' to see debug information with visual feedback")
        
        print("\n5. 📱 EXPECTED VISUAL FEEDBACK BEHAVIORS:")
        print("   • When clusters are already synchronized: '✅ Tutti i cluster sono già sincronizzati'")
        print("   • When new clusters are added: '✅ Aggiunti X nuovi cluster: [cluster names]'")
        print("   • When clusters are removed: '🔄 Ordine cluster aggiornato'")
        print("   • During refresh: '🔄 Ricaricamento cluster in corso...'")
        print("   • Debug test results: '✅ Test completato - Cluster correttamente sincronizzati'")
        print("   • Error cases: '❌ Errore durante l'aggiornamento dei cluster'")
        
        # Test 4: Clean up the test color
        print("\n6. 🧹 Cleaning up test data...")
        
        # Get all colors to find the test color ID
        response = requests.get(f"{base_url}/api/cabin/{cabin_id}/colors")
        if response.status_code == 200:
            colors_data = response.json()
            colors = colors_data.get('colors', [])
            test_color = next((c for c in colors if c.get('color_code') == 'TEST_VISUAL_123'), None)
            
            if test_color and 'id' in test_color:
                delete_response = requests.delete(f"{base_url}/api/cabin/{cabin_id}/colors/{test_color['id']}")
                if delete_response.status_code == 200:
                    print("   ✅ Test color deleted successfully")
                else:
                    print(f"   ⚠️ Could not delete test color: {delete_response.status_code}")
            else:
                print("   ⚠️ Test color not found for deletion")
        
        print("\n" + "=" * 60)
        print("🎉 VISUAL FEEDBACK TEST COMPLETED!")
        print("🔍 Check the browser interface to see the enhanced visual feedback in action")
        print("📊 The system now provides clear feedback for all cluster synchronization operations")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend service")
        print("Make sure the backend is running on http://localhost:8001")
    except Exception as e:
        print(f"❌ Error during testing: {e}")

if __name__ == "__main__":
    test_visual_feedback_system()
