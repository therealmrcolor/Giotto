#!/usr/bin/env python3
import sqlite3
import sys

DATABASE_PATH = "/Users/baldi/H-Farm/tesi/swdevel-lab-hfarm-master copy/frontend/app/data/colors.db"

print("Testing manual database transaction...")

try:
    # Connect to database
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check initial count
    cursor.execute("SELECT COUNT(*) FROM optimization_colors")
    count_before = cursor.fetchone()[0]
    print(f"Initial count: {count_before}")
    
    # Delete all records
    cursor.execute("DELETE FROM optimization_colors")
    print("Executed DELETE command")
    
    # Check count after delete (before commit)
    cursor.execute("SELECT COUNT(*) FROM optimization_colors")
    count_after_delete = cursor.fetchone()[0]
    print(f"Count after DELETE (before commit): {count_after_delete}")
    
    # Insert a test record
    cursor.execute('''
        INSERT INTO optimization_colors (
            color_code, color_type, cluster, sequence_order, 
            completed, in_execution, input_sequence, ch_value,
            lunghezza_ordine, sequence_type, cabin_id, is_prioritized
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'TESTCOLOR789',
        'E',
        'Test Cluster',
        0,  # sequence_order
        0,  # completed
        0,  # in_execution
        None,  # input_sequence
        25.5,  # ch_value
        'corto',  # lunghezza_ordine
        None,  # sequence_type
        1,  # cabin_id
        0   # is_prioritized
    ))
    print("Executed INSERT command")
    
    # Check count after insert (before commit)
    cursor.execute("SELECT COUNT(*) FROM optimization_colors")
    count_after_insert = cursor.fetchone()[0]
    print(f"Count after INSERT (before commit): {count_after_insert}")
    
    # Commit transaction
    conn.commit()
    print("Executed COMMIT")
    
    # Check final count
    cursor.execute("SELECT COUNT(*) FROM optimization_colors")
    count_final = cursor.fetchone()[0]
    print(f"Final count after commit: {count_final}")
    
    # Verify the record exists
    cursor.execute("SELECT color_code, color_type, cluster FROM optimization_colors WHERE color_code = 'TESTCOLOR789'")
    row = cursor.fetchone()
    if row:
        print(f"Test record found: {row[0]} ({row[1]}) -> {row[2]}")
    else:
        print("ERROR: Test record not found!")
    
    conn.close()
    print("✅ Manual transaction test completed successfully")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
