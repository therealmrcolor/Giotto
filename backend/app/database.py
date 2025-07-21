# backend/app/database.py
"""Database access functions for SQLite."""

import sqlite3
import json
from typing import Dict, List, Tuple, Any, Optional
from app.config import DATABASE_PATH # Importa il path dal config

# Tipi definiti (possono stare qui o in models.py)
ColorObject = Dict[str, Any]
ClusterDict = Dict[str, List[str]]
TransitionRuleDict = Dict[Tuple[str, str], Dict[str, Any]]

def connect_to_db(db_path: str = DATABASE_PATH) -> Optional[sqlite3.Connection]:
    """Crea una connessione al database SQLite."""
    try:
        conn = sqlite3.connect(db_path)
        # Permette di accedere ai risultati per nome colonna (molto comodo)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Errore di connessione al database {db_path}: {e}")
        return None

def get_cluster_colori() -> ClusterDict:
    """Ottiene il mapping cluster -> lista codici colore dal DB."""
    clusters: ClusterDict = {}
    conn = connect_to_db()
    if not conn:
        return clusters # Ritorna dizionario vuoto se la connessione fallisce

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT cluster, color_code FROM cluster_colori')
        rows = cursor.fetchall()
        for row in rows:
            cluster = row['cluster']
            color = row['color_code']
            if cluster not in clusters:
                clusters[cluster] = []
            clusters[cluster].append(color)
    except sqlite3.Error as e:
        print(f"Errore durante la query get_cluster_colori: {e}")
    finally:
        if conn:
            conn.close()
    return clusters

def get_cambio_colori() -> TransitionRuleDict:
    """Ottiene le regole di transizione tra cluster dal DB."""
    transitions: TransitionRuleDict = {}
    conn = connect_to_db()
    if not conn:
        return transitions

    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT source_cluster, target_cluster, peso, transition_colors, required_trigger_type
            FROM cambio_colori
        ''')
        rows = cursor.fetchall()
        for row in rows:
            source = row['source_cluster']
            target = row['target_cluster']
            colors = []
            if row['transition_colors']:
                try:
                    # Tenta di caricare come JSON, gestendo stringhe vuote o non JSON
                    loaded_colors = json.loads(row['transition_colors'])
                    if isinstance(loaded_colors, list):
                         # Filtra valori non stringa o 'VIETATO' se presenti per errore
                        colors = [c for c in loaded_colors if isinstance(c, str) and c.upper() != 'VIETATO']
                    else:
                         print(f"Warning: DB transition_colors for ({source}, {target}) non è una lista JSON: {row['transition_colors']}")
                except (json.JSONDecodeError, TypeError):
                     print(f"Warning: DB transition_colors for ({source}, {target}) non è JSON valido: {row['transition_colors']}")
                     # Se non è JSON valido o non è una lista, considera vuota
                     colors = []


            transitions[(source, target)] = {
                'peso': row['peso'],
                'colors': colors, # Lista pulita di codici colore specifici
                'required_type': row['required_trigger_type']
            }
    except sqlite3.Error as e:
        print(f"Errore durante la query get_cambio_colori: {e}")
    finally:
        if conn:
            conn.close()
    return transitions

# --- NUOVE FUNZIONI PER LA GESTIONE DB ---

# === CAMBIO COLORI ===

def get_all_cambio_colori_grouped() -> Dict[str, List[Dict[str, Any]]]:
    """Ottiene tutte le regole di cambio_colori, raggruppate per source_cluster."""
    grouped_rules: Dict[str, List[Dict[str, Any]]] = {}
    conn = connect_to_db()
    if not conn:
        return grouped_rules
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, source_cluster, target_cluster, peso, transition_colors, required_trigger_type FROM cambio_colori ORDER BY source_cluster, target_cluster")
        rows = cursor.fetchall()
        for row in rows:
            source_cluster = row['source_cluster']
            if source_cluster not in grouped_rules:
                grouped_rules[source_cluster] = []
            grouped_rules[source_cluster].append(dict(row))
    except sqlite3.Error as e:
        print(f"Errore in get_all_cambio_colori_grouped: {e}")
    finally:
        if conn:
            conn.close()
    return grouped_rules

def get_cambio_colori_row_by_id(row_id: int) -> Optional[Dict[str, Any]]:
    """Ottiene una singola riga da cambio_colori per ID."""
    conn = connect_to_db()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, source_cluster, target_cluster, peso, transition_colors, required_trigger_type FROM cambio_colori WHERE id = ?", (row_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Errore in get_cambio_colori_row_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def add_cambio_colori_row(source_cluster: str, target_cluster: str, peso: int, transition_colors: str, required_trigger_type: Optional[str]) -> bool:
    """Aggiunge una nuova riga a cambio_colori."""
    conn = connect_to_db()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cambio_colori (source_cluster, target_cluster, peso, transition_colors, required_trigger_type)
            VALUES (?, ?, ?, ?, ?)
        """, (source_cluster, target_cluster, peso, transition_colors, required_trigger_type if required_trigger_type else None))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Errore in add_cambio_colori_row: {e}")
        return False
    finally:
        if conn: conn.close()

def update_cambio_colori_row(row_id: int, target_cluster: str, peso: int, transition_colors: str, required_trigger_type: Optional[str]) -> bool:
    """Aggiorna una riga in cambio_colori. Source_cluster non è modificabile qui."""
    conn = connect_to_db()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE cambio_colori
            SET target_cluster = ?, peso = ?, transition_colors = ?, required_trigger_type = ?
            WHERE id = ?
        """, (target_cluster, peso, transition_colors, required_trigger_type if required_trigger_type else None, row_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Errore in update_cambio_colori_row: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_cambio_colori_row(row_id: int) -> bool:
    """Elimina una riga da cambio_colori per ID."""
    conn = connect_to_db()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cambio_colori WHERE id = ?", (row_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Errore in delete_cambio_colori_row: {e}")
        return False
    finally:
        if conn: conn.close()

def get_unique_source_clusters() -> List[str]:
    """Ottiene una lista unica di source_cluster."""
    conn = connect_to_db()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT source_cluster FROM cambio_colori ORDER BY source_cluster")
        return [row['source_cluster'] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Errore in get_unique_source_clusters: {e}")
        return []
    finally:
        if conn: conn.close()

# === CLUSTER COLORI ===
# Assumendo che cluster_colori abbia una colonna 'id INTEGER PRIMARY KEY AUTOINCREMENT'

def get_all_cluster_colori_grouped() -> Dict[str, List[Dict[str, Any]]]:
    """Ottiene tutti i mapping cluster_colori, raggruppati per cluster."""
    grouped_mappings: Dict[str, List[Dict[str, Any]]] = {}
    conn = connect_to_db()
    if not conn:
        return grouped_mappings
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, cluster, color_code FROM cluster_colori ORDER BY cluster, color_code")
        rows = cursor.fetchall()
        for row in rows:
            cluster_name = row['cluster']
            if cluster_name not in grouped_mappings:
                grouped_mappings[cluster_name] = []
            grouped_mappings[cluster_name].append(dict(row))
    except sqlite3.Error as e:
        print(f"Errore in get_all_cluster_colori_grouped: {e}")
    finally:
        if conn:
            conn.close()
    return grouped_mappings

def get_cluster_colori_row_by_id(row_id: int) -> Optional[Dict[str, Any]]:
    """Ottiene una singola riga da cluster_colori per ID."""
    conn = connect_to_db()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, cluster, color_code FROM cluster_colori WHERE id = ?", (row_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Errore in get_cluster_colori_row_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def add_cluster_colori_row(cluster: str, color_code: str) -> bool:
    """Aggiunge una nuova riga a cluster_colori."""
    conn = connect_to_db()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO cluster_colori (cluster, color_code) VALUES (?, ?)", (cluster, color_code))
        conn.commit()
        return True
    except sqlite3.IntegrityError: # Es. se c'è UNIQUE constraint (cluster, color_code)
        print(f"Errore di integrità: Coppia cluster '{cluster}' e codice '{color_code}' probabilmente già esistente.")
        return False
    except sqlite3.Error as e:
        print(f"Errore in add_cluster_colori_row: {e}")
        return False
    finally:
        if conn: conn.close()

def update_cluster_colori_row(row_id: int, color_code: str) -> bool:
    """Aggiorna una riga in cluster_colori. Cluster non è modificabile qui."""
    conn = connect_to_db()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE cluster_colori SET color_code = ? WHERE id = ?", (color_code, row_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        print(f"Errore di integrità: Aggiornamento a codice colore '{color_code}' probabilmente creerebbe un duplicato.")
        return False
    except sqlite3.Error as e:
        print(f"Errore in update_cluster_colori_row: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_cluster_colori_row(row_id: int) -> bool:
    """Elimina una riga da cluster_colori per ID."""
    conn = connect_to_db()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cluster_colori WHERE id = ?", (row_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Errore in delete_cluster_colori_row: {e}")
        return False
    finally:
        if conn: conn.close()

def get_unique_clusters() -> List[str]:
    """Ottiene una lista unica di cluster da cluster_colori."""
    conn = connect_to_db()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT cluster FROM cluster_colori ORDER BY cluster")
        return [row['cluster'] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Errore in get_unique_clusters: {e}")
        return []
    finally:
        if conn: conn.close()

# === OPTIMIZATION COLORS ===

def save_optimization_results(ordered_colors: List[Dict[str, Any]], cabin_id: int = 1) -> bool:
    """
    Salva i risultati dell'ottimizzazione nella tabella optimization_colors.
    Sostituisce tutti i colori esistenti per la cabina specificata.
    """
    conn = connect_to_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Elimina tutti i colori esistenti per questa cabina
        cursor.execute("DELETE FROM optimization_colors WHERE cabin_id = ?", (cabin_id,))
        
        # Inserisci i nuovi colori ottimizzati
        for i, color in enumerate(ordered_colors):
            cursor.execute("""
                INSERT INTO optimization_colors (
                    color_code, color_type, cluster, ch_value, lunghezza_ordine,
                    input_sequence, sequence_type, sequence_order, cabin_id,
                    is_prioritized, completed, in_execution, locked
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
            """, (
                color.get('code'),
                color.get('type'),
                color.get('cluster'),
                color.get('CH'),
                color.get('lunghezza_ordine'),
                color.get('sequence'),
                color.get('sequence_type'),
                i + 1,  # sequence_order basato sulla posizione nell'array
                cabin_id,
                color.get('is_prioritized', False)
            ))
        
        conn.commit()
        print(f"[DB] Salvati {len(ordered_colors)} colori per cabina {cabin_id}")
        return True
        
    except sqlite3.Error as e:
        print(f"Errore durante il salvataggio dei colori ottimizzati: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_optimization_colors(cabin_id: int = 1) -> List[Dict[str, Any]]:
    """
    Recupera i colori ottimizzati per una cabina specifica,
    ordinati per sequence_order.
    """
    conn = connect_to_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, color_code, color_type, cluster, ch_value, lunghezza_ordine,
                input_sequence, sequence_type, sequence_order, cabin_id,
                is_prioritized, completed, in_execution, locked, position,
                created_at
            FROM optimization_colors 
            WHERE cabin_id = ?
            ORDER BY sequence_order ASC
        """, (cabin_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append(dict(row))
        
        return results
        
    except sqlite3.Error as e:
        print(f"Errore durante il recupero dei colori ottimizzati: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_cabin_status(cabin_id: int = 1) -> Dict[str, int]:
    """
    Recupera lo status di una cabina (totali, in esecuzione, completati).
    """
    conn = connect_to_db()
    if not conn:
        return {"total": 0, "executing": 0, "completed": 0}
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN in_execution = 1 THEN 1 ELSE 0 END) as executing,
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
            FROM optimization_colors 
            WHERE cabin_id = ?
        """, (cabin_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                "total": row['total'] or 0,
                "executing": row['executing'] or 0,
                "completed": row['completed'] or 0
            }
        else:
            return {"total": 0, "executing": 0, "completed": 0}
            
    except sqlite3.Error as e:
        print(f"Errore durante il recupero dello status cabina: {e}")
        return {"total": 0, "executing": 0, "completed": 0}
    finally:
        if conn:
            conn.close()

def clear_all_optimization_colors() -> bool:
    """
    Elimina tutti i colori ottimizzati da entrambe le cabine.
    """
    conn = connect_to_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM optimization_colors")
        conn.commit()
        print("[DB] Eliminati tutti i colori ottimizzati")
        return True
        
    except sqlite3.Error as e:
        print(f"Errore durante la pulizia dei colori ottimizzati: {e}")
        return False
    finally:
        if conn:
            conn.close()