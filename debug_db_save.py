#!/usr/bin/env python3
"""
Debug script to test the database save operation from the frontend
"""
import sqlite3
import json

DATABASE_PATH = "/Users/baldi/H-Farm/tesi/swdevel-lab-hfarm-master copy/frontend/app/data/colors.db"

def test_db_save():
    """Test the database save operation with sample data"""
    
    # Sample color data matching what the backend returns
    test_color = {
        "CH": 25.5,
        "cluster": "Grigio Chiaro", 
        "code": "RAL7044",
        "lunghezza_ordine": "corto",
        "sequence": None,
        "sequence_type": None,
        "type": "E"
    }
    
    print("Testing database save operation...")
    print(f"Database path: {DATABASE_PATH}")
    print(f"Test color: {test_color}")
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check current count
        cursor.execute("SELECT COUNT(*) FROM optimization_colors")
        count_before = cursor.fetchone()[0]
        print(f"Colors in DB before: {count_before}")
        
        # Clear existing data (like the API does)
        cursor.execute("DELETE FROM optimization_colors")
        print("Cleared optimization_colors table")
        
        # Insert test color using same logic as save_color_to_db_internal
        cursor.execute('''
            INSERT INTO optimization_colors (
                color_code, color_type, cluster, sequence_order, 
                completed, in_execution, input_sequence, ch_value,
                lunghezza_ordine, sequence_type, cabin_id, is_prioritized
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            test_color.get('code', test_color.get('color_code', '')),
            test_color.get('type', test_color.get('color_type', '')),
            test_color.get('cluster', ''),
            0,  # sequence_order
            0,  # completed
            0,  # in_execution
            test_color.get('sequence', test_color.get('input_sequence')),
            test_color.get('CH', test_color.get('ch_value')),
            test_color.get('lunghezza_ordine', ''),
            test_color.get('sequence_type', ''),
            1,  # cabin_id
            0   # is_prioritized
        ))
        
        print("Inserted test color")
        
        # Commit the transaction
        conn.commit()
        print("Committed transaction")
        
        # Check final count
        cursor.execute("SELECT COUNT(*) FROM optimization_colors")
        count_after = cursor.fetchone()[0]
        print(f"Colors in DB after: {count_after}")
        
        # Show the inserted color
        cursor.execute("SELECT color_code, color_type, cluster FROM optimization_colors WHERE color_code = ?", (test_color['code'],))
        row = cursor.fetchone()
        if row:
            print(f"Successfully saved: {row[0]} ({row[1]}) - {row[2]}")
        else:
            print("ERROR: Color not found after insert!")
            
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting debug script...")
    try:
        test_db_save()
        print("Debug script completed successfully")
    except Exception as e:
        print(f"Debug script failed: {e}")
        import traceback
        traceback.print_exc()
