#!/usr/bin/env python3
import sqlite3
import json

# Test directly inserting priority flags
conn = sqlite3.connect('frontend/app/data/colors.db')
cursor = conn.cursor()

# Clear the table first
print("Clearing optimization_colors table...")
cursor.execute("DELETE FROM optimization_colors")
conn.commit()

# Insert test data with priorities
test_colors = [
    {"color_code": "RAL7048", "color_type": "E", "is_prioritized": 0},
    {"color_code": "69115038", "color_type": "R", "is_prioritized": 1},  # Priority
    {"color_code": "160024", "color_type": "F", "is_prioritized": 1},    # Priority
]

print("Inserting test data with priorities...")
for idx, color in enumerate(test_colors):
    cursor.execute("""
    INSERT INTO optimization_colors (
        color_code, color_type, sequence_order, is_prioritized,
        cabin_id, completed, in_execution
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        color["color_code"],
        color["color_type"],
        idx,
        color["is_prioritized"],
        1,  # cabin_id
        0,  # completed
        0   # in_execution
    ))
    print(f"Inserted {color['color_code']} with is_prioritized={color['is_prioritized']}")

conn.commit()

# Verify the data was inserted correctly
print("\nVerifying data in the database...")
cursor.execute("SELECT color_code, is_prioritized FROM optimization_colors")
rows = cursor.fetchall()
for row in rows:
    print(f"Color {row[0]} has is_prioritized={row[1]}")

# Check if priorities were preserved
priority_colors = [row[0] for row in rows if row[1] == 1]
if priority_colors:
    print(f"\nSuccess! Found {len(priority_colors)} priority colors: {priority_colors}")
else:
    print("\nFailed! No priority colors found in database.")

conn.close()
