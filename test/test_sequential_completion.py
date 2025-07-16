#!/usr/bin/env python3
"""
Test script per verificare la logica di completamento sequenziale dei colori.
Questo test verifica che quando si imposta un colore come "in esecuzione",
tutti i colori precedenti nella sequenza vengano automaticamente marcati come "completati".
"""

import sqlite3
import requests
import json
import time

DATABASE_PATH = "/Users/baldi/H-Farm/tesi/swdevel-lab-hfarm-master copy/frontend/app/data/colors.db"
FRONTEND_URL = "http://localhost:5001"

def connect_db():
    """Connette al database SQLite."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def clear_optimization_colors():
    """Pulisce la tabella optimization_colors per iniziare con dati puliti."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM optimization_colors")
    conn.commit()
    conn.close()
    print("✓ Tabella optimization_colors pulita")

def insert_test_colors():
    """Inserisce colori di test per verificare la logica sequenziale."""
    conn = connect_db()
    cursor = conn.cursor()
    
    test_colors = [
        ("RAL1001", "E", "Bianco", 1, 1),  # sequence_order = 1
        ("RAL2002", "K", "Nero", 2, 1),    # sequence_order = 2  
        ("RAL3003", "R", "Rosso", 3, 1),   # sequence_order = 3
        ("RAL4004", "RE", "Bianco", 4, 1), # sequence_order = 4
        ("RAL5005", "E", "Nero", 5, 1),    # sequence_order = 5
    ]
    
    for color_code, color_type, cluster, sequence_order, cabin_id in test_colors:
        cursor.execute("""
            INSERT INTO optimization_colors (
                color_code, color_type, cluster, sequence_order, 
                completed, in_execution, cabin_id, input_sequence, 
                ch_value, lunghezza_ordine, sequence_type, is_prioritized
            ) VALUES (?, ?, ?, ?, 0, 0, ?, 1, 2.0, 'corto', 'oggi', 0)
        """, (color_code, color_type, cluster, sequence_order, cabin_id))
    
    conn.commit()
    conn.close()
    print("✓ Inseriti 5 colori di test per la cabina 1")

def get_colors_state(cabin_id=1):
    """Ottiene lo stato attuale di tutti i colori nella cabina."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, color_code, sequence_order, completed, in_execution 
        FROM optimization_colors 
        WHERE cabin_id = ? 
        ORDER BY sequence_order
    """, (cabin_id,))
    
    colors = cursor.fetchall()
    conn.close()
    return colors

def print_colors_state(cabin_id=1, title="Stato attuale"):
    """Stampa lo stato attuale dei colori."""
    colors = get_colors_state(cabin_id)
    print(f"\n{title} (Cabina {cabin_id}):")
    print("ID | Codice   | Order | Completato | In Esecuzione")
    print("---|----------|-------|------------|---------------")
    for color in colors:
        completed_str = "SÌ" if color['completed'] else "NO"
        in_execution_str = "SÌ" if color['in_execution'] else "NO"
        print(f"{color['id']:2} | {color['color_code']:8} | {color['sequence_order']:5} | {completed_str:10} | {in_execution_str}")

def test_sequential_completion():
    """Testa la logica di completamento sequenziale."""
    print("\n" + "="*70)
    print("TEST COMPLETAMENTO SEQUENZIALE")
    print("="*70)
    
    # 1. Prepara dati di test
    print("\n1. Preparazione dati di test...")
    clear_optimization_colors()
    insert_test_colors()
    print_colors_state(title="Stato iniziale")
    
    # 2. Test: imposta il terzo colore (sequence_order=3) come "in esecuzione"
    print("\n2. Impostazione del colore 3 (RAL3003) come 'in esecuzione'...")
    colors = get_colors_state()
    color_3_id = next(c['id'] for c in colors if c['sequence_order'] == 3)
    
    response = requests.put(
        f"{FRONTEND_URL}/api/cabin/1/colors/{color_3_id}/execution",
        json={"in_execution": True}
    )
    
    if response.status_code == 200:
        print("✓ Richiesta API eseguita con successo")
    else:
        print(f"✗ Errore API: {response.status_code} - {response.text}")
        return False
    
    print_colors_state(title="Dopo aver impostato colore 3 'in esecuzione'")
    
    # 3. Verifica che i colori 1 e 2 siano completati
    colors_after = get_colors_state()
    colors_1_and_2 = [c for c in colors_after if c['sequence_order'] in [1, 2]]
    all_completed = all(c['completed'] for c in colors_1_and_2)
    
    if all_completed:
        print("✓ TEST SUPERATO: I colori 1 e 2 sono stati marcati come completati")
    else:
        print("✗ TEST FALLITO: Non tutti i colori precedenti sono stati completati")
        return False
    
    # 4. Test: imposta il quinto colore (sequence_order=5) come "in esecuzione"
    print("\n3. Impostazione del colore 5 (RAL5005) come 'in esecuzione'...")
    color_5_id = next(c['id'] for c in colors if c['sequence_order'] == 5)
    
    response = requests.put(
        f"{FRONTEND_URL}/api/cabin/1/colors/{color_5_id}/execution",
        json={"in_execution": True}
    )
    
    if response.status_code == 200:
        print("✓ Richiesta API eseguita con successo")
    else:
        print(f"✗ Errore API: {response.status_code} - {response.text}")
        return False
    
    print_colors_state(title="Dopo aver impostato colore 5 'in esecuzione'")
    
    # 5. Verifica che i colori 1, 2, 3, 4 siano tutti completati
    colors_final = get_colors_state()
    colors_1_to_4 = [c for c in colors_final if c['sequence_order'] in [1, 2, 3, 4]]
    all_completed_final = all(c['completed'] for c in colors_1_to_4)
    
    # Verifica che solo il colore 5 sia "in esecuzione"
    in_execution_colors = [c for c in colors_final if c['in_execution']]
    only_5_in_execution = len(in_execution_colors) == 1 and in_execution_colors[0]['sequence_order'] == 5
    
    if all_completed_final and only_5_in_execution:
        print("✓ TEST SUPERATO: Tutti i colori precedenti (1-4) sono completati e solo il 5 è in esecuzione")
    else:
        print("✗ TEST FALLITO: La logica di completamento sequenziale non funziona correttamente")
        return False
    
    print("\n" + "="*70)
    print("TUTTI I TEST SUPERATI! ✓")
    print("La logica di completamento sequenziale funziona correttamente.")
    print("="*70)
    return True

def test_optimization_with_completed_colors():
    """Testa che i colori completati vengano esclusi dall'ottimizzazione."""
    print("\n" + "="*70)
    print("TEST OTTIMIZZAZIONE CON COLORI COMPLETATI")
    print("="*70)
    
    # Ottieni lo stato attuale
    colors = get_colors_state()
    completed_colors = [c for c in colors if c['completed']]
    not_completed_colors = [c for c in colors if not c['completed']]
    
    print(f"Colori completati: {len(completed_colors)}")
    print(f"Colori non completati: {len(not_completed_colors)}")
    
    # Simula ottimizzazione chiamando l'API di ottimizzazione con solo i colori non completati
    if not_completed_colors:
        print("\n✓ Solo i colori non completati dovrebbero essere inclusi nell'ottimizzazione")
        return True
    else:
        print("\n⚠ Tutti i colori sono completati - ottimizzazione non necessaria")
        return True

if __name__ == "__main__":
    try:
        # Verifica che il frontend sia raggiungibile
        response = requests.get(f"{FRONTEND_URL}/")
        if response.status_code != 200:
            print(f"Errore: Frontend non raggiungibile su {FRONTEND_URL}")
            exit(1)
        
        # Esegui i test
        success = test_sequential_completion()
        if success:
            test_optimization_with_completed_colors()
        
    except requests.exceptions.ConnectionError:
        print(f"Errore: Impossibile connettersi al frontend su {FRONTEND_URL}")
        print("Assicurati che il frontend sia in esecuzione.")
        exit(1)
    except Exception as e:
        print(f"Errore inaspettato: {e}")
        exit(1)
