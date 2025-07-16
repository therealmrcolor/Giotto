#!/usr/bin/env python3
import json
import sqlite3
import os
import subprocess

# Clear database first
print("Clearing database...")
conn = sqlite3.connect('frontend/app/data/colors.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM optimization_colors')
conn.commit()
conn.close()

# Test data with priorities
test_data = {
    "colors_today": [
        {
            "code": "RAL7048",
            "type": "E",
            "CH": 1.5,
            "lunghezza_ordine": "corto"
        },
        {
            "code": "69115038",  # This will be marked as priority
            "type": "R",
            "CH": 1.8,
            "lunghezza_ordine": "corto"
        },
        {
            "code": "160024",    # This will also be marked as priority
            "type": "F",
            "CH": 4.1,
            "lunghezza_ordine": "lungo"
        }
    ],
    "start_cluster_name": "Grigio Scuro",
    "prioritized_reintegrations": ["69115038", "160024"]  # Two priority colors
}

# Save test data to a file
with open('test_priority_data.json', 'w') as f:
    json.dump(test_data, f)

print("\nSending API request with curl...")
# Use curl for the API request
curl_cmd = [
    'curl', '-X', 'POST',
    'http://127.0.0.1:5001/api/optimize',
    '-H', 'Content-Type: application/json',
    '--data', '@test_priority_data.json',
    '-v'  # verbose output
]

try:
    output = subprocess.check_output(curl_cmd, universal_newlines=True)
    print("API request completed")
    
    # Check database after API call
    print("\nChecking database after API call...")
    conn = sqlite3.connect('frontend/app/data/colors.db')
    cursor = conn.cursor()
    
    # Check table structure first
    print("Database table structure:")
    cursor.execute("PRAGMA table_info(optimization_colors)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  - {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] else ''}")
    
    cursor.execute("SELECT color_code, is_prioritized FROM optimization_colors")
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} records in database:")
    for row in rows:
        print(f"Color {row[0]} has is_prioritized={row[1]}")
    
    # Check if priorities were preserved
    priority_colors = [row[0] for row in rows if row[1] == 1]
    if priority_colors:
        print(f"\nSuccess! Found {len(priority_colors)} priority colors: {priority_colors}")
    else:
        print("\nFailed! No priority colors found in database.")
    
    conn.close()
    
except subprocess.CalledProcessError as e:
    print(f"Error calling API: {e}")
    
finally:
    # Clean up
    if os.path.exists('test_priority_data.json'):
        os.remove('test_priority_data.json')
