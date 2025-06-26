#!/usr/bin/env python3
"""
Debug script to test the exact database transaction that happens in /api/optimize
"""
import sqlite3
import json
import logging

# Setup logging exactly as in main.py
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('debug')

DATABASE_PATH = "/Users/baldi/H-Farm/tesi/swdevel-lab-hfarm-master copy/frontend/app/data/colors.db"

def connect_to_db(db_path: str = DATABASE_PATH):
    """Connect to database exactly as in main.py"""
    logger.debug(f"Tentativo di connessione al database: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        # Importante: imposta row_factory per ottenere risultati come dizionari
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logger.debug(f"Tabelle trovate nel database: {[table[0] for table in tables]}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Errore di connessione al database {db_path}: {e}")
        return None

def save_color_to_db_internal(cursor, color, sequence_order, cabin_id, prioritized_reintegrations=None):
    """Helper function per salvare un singolo colore nel database - EXACT COPY from main.py"""
    color_code = color.get('code', color.get('color_code', ''))
    is_prioritized = 0
    
    # Controlla se il colore è tra i reintegri prioritari
    if prioritized_reintegrations and color_code in prioritized_reintegrations:
        is_prioritized = 1
        logger.info(f"Impostando colore {color_code} come prioritario nel database")
    
    logger.debug(f"Inserting color: {color_code}, type: {color.get('type', color.get('color_type', ''))}, cluster: {color.get('cluster', '')}")
    
    cursor.execute('''
        INSERT INTO optimization_colors (
            color_code, color_type, cluster, sequence_order, 
            completed, in_execution, input_sequence, ch_value,
            lunghezza_ordine, sequence_type, cabin_id, is_prioritized
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        color_code,
        color.get('type', color.get('color_type', '')),
        color.get('cluster', ''),
        sequence_order,
        0,  # completed
        0,  # in_execution
        color.get('sequence', color.get('input_sequence')),
        color.get('CH', color.get('ch_value')),
        color.get('lunghezza_ordine', ''),
        color.get('sequence_type', ''),
        cabin_id,
        is_prioritized
    ))

def test_exact_db_transaction():
    """Test the exact same database transaction that happens in /api/optimize"""
    
    # Sample backend response like what we get from optimization
    backend_results = {
        "ordered_colors": [
            {
                "CH": 25.5,
                "cluster": "Grigio Chiaro", 
                "code": "RAL7044",
                "lunghezza_ordine": "corto",
                "sequence": None,
                "sequence_type": None,
                "type": "E"
            },
            {
                "CH": 15.2,
                "cluster": "Bianco", 
                "code": "RAL9003",
                "lunghezza_ordine": "corto",
                "sequence": None,
                "sequence_type": None,
                "type": "E"
            }
        ]
    }
    
    print("=== Testing Exact Database Transaction ===")
    print(f"Database path: {DATABASE_PATH}")
    print(f"Backend results: {json.dumps(backend_results, indent=2)}")
    
    conn = connect_to_db()
    if not conn:
        print("❌ Could not connect to database")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check initial count
        cursor.execute("SELECT COUNT(*) FROM optimization_colors")
        count_before = cursor.fetchone()[0]
        print(f"Colors in DB before: {count_before}")
        
        # EXACT SAME LOGIC AS /api/optimize endpoint
        print("🗑️  Clearing existing data...")
        cursor.execute("DELETE FROM optimization_colors")
        
        cursor.execute("SELECT COUNT(*) FROM optimization_colors")
        count_after_delete = cursor.fetchone()[0]
        print(f"Colors in DB after DELETE: {count_after_delete}")
        
        # Save colors using exact same logic
        prioritized_reintegrations = []  # Empty list like in the endpoint
        
        print("💾 Saving colors...")
        if backend_results.get('ordered_colors'):
            for idx, color in enumerate(backend_results['ordered_colors']):
                cabin_id = 2 if color.get('lunghezza_ordine') == 'lungo' else 1
                print(f"  Saving color {idx}: {color['code']} to cabin {cabin_id}")
                save_color_to_db_internal(cursor, color, idx, cabin_id, prioritized_reintegrations)
        
        # Check count before commit
        cursor.execute("SELECT COUNT(*) FROM optimization_colors")
        count_before_commit = cursor.fetchone()[0]
        print(f"Colors in DB before commit: {count_before_commit}")
        
        # Commit transaction
        print("📝 Committing transaction...")
        conn.commit()
        print("✅ Transaction committed")
        
        # Check final count
        cursor.execute("SELECT COUNT(*) FROM optimization_colors")
        count_final = cursor.fetchone()[0]
        print(f"Colors in DB after commit: {count_final}")
        
        # Verify data
        cursor.execute("SELECT color_code, color_type, cluster, cabin_id FROM optimization_colors ORDER BY sequence_order")
        rows = cursor.fetchall()
        print(f"Saved colors:")
        for row in rows:
            print(f"  - {row[0]} ({row[1]}) -> {row[2]} | Cabin: {row[3]}")
        
        return count_final > 0
        
    except Exception as e:
        print(f"❌ Error during transaction: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting exact database transaction test...")
    success = test_exact_db_transaction()
    print(f"\nTest result: {'✅ SUCCESS' if success else '❌ FAILED'}")
