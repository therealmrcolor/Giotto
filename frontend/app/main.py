# frontend/app/main.py
import os
import requests
import json
import traceback # Importa traceback
import sqlite3
import logging
from typing import Dict, List, Tuple, Any, Optional
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify # Importa jsonify
# from flask_wtf.csrf import CSRFProtect  # Temporarily disabled for testing
try:
    from .forms import (
        OptimizationInputForm, CambioColoriRowForm, NewSourceClusterForm,
        ClusterColoriRowForm, NewClusterForm
    )
except ImportError:
    from forms import (
        OptimizationInputForm, CambioColoriRowForm, NewSourceClusterForm,
        ClusterColoriRowForm, NewClusterForm
    )

# Configurazione del logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('frontend')

# Path del database SQLite
# Usa variabile d'ambiente o default per Docker
DATABASE_PATH = os.environ.get('DATABASE_PATH', "/app/app/data/colors.db")

# --- DATABASE FUNCTIONS ---
def connect_to_db(db_path: str = DATABASE_PATH) -> Optional[sqlite3.Connection]:
    """Connette al database SQLite."""
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

def migrate_db_data():
    """Migra i dati del database dai cluster generici (A, B, C) a nomi significativi."""
    conn = connect_to_db()
    if not conn:
        logger.error("Impossibile migrare il database: connessione fallita")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Mappa dei nomi dei cluster da aggiornare
        cluster_mapping = {
            'A': 'Bianco',
            'B': 'Nero',
            'C': 'Rosso'
        }
        
        # Aggiorna i nomi dei cluster nella tabella cambio_colori
        for old_name, new_name in cluster_mapping.items():
            # Aggiorna source_cluster
            cursor.execute("UPDATE cambio_colori SET source_cluster = ? WHERE source_cluster = ?", (new_name, old_name))
            # Aggiorna target_cluster
            cursor.execute("UPDATE cambio_colori SET target_cluster = ? WHERE target_cluster = ?", (new_name, old_name))
        
        # Aggiorna i nomi dei cluster nella tabella cluster_colori
        for old_name, new_name in cluster_mapping.items():
            cursor.execute("UPDATE cluster_colori SET cluster = ? WHERE cluster = ?", (new_name, old_name))
        
        conn.commit()
        logger.info("Migrazione dei dati completata con successo")
        return True
    except sqlite3.Error as e:
        logger.error(f"Errore durante la migrazione dei dati: {e}")
        return False
    finally:
        if conn:
            conn.close()

def init_db():
    """Inizializza il database creando le tabelle necessarie se non esistono."""
    conn = connect_to_db()
    if not conn:
        logger.error("Impossibile inizializzare il database: connessione fallita")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Verifica se le tabelle esistono
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('cambio_colori', 'cluster_colori', 'saved_sequences', 'optimization_colors')")
        existing_tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Tabelle esistenti: {existing_tables}")
        
        # Crea la tabella cambio_colori se non esiste
        if 'cambio_colori' not in existing_tables:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cambio_colori (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_cluster TEXT NOT NULL,
                target_cluster TEXT NOT NULL,
                peso INTEGER NOT NULL,
                transition_colors TEXT,
                required_trigger_type TEXT
            )
            ''')
            logger.info("Tabella cambio_colori creata")
        
        # Crea la tabella cluster_colori se non esiste
        if 'cluster_colori' not in existing_tables:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cluster_colori (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster TEXT NOT NULL,
                color_code TEXT NOT NULL,
                UNIQUE(cluster, color_code)
            )comp
            ''')
            logger.info("Tabella cluster_colori creata")
        
        # Crea la tabella saved_sequences se non esiste
        if 'saved_sequences' not in existing_tables:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            logger.info("Tabella saved_sequences creata")
        
        # Crea la tabella optimization_colors se non esiste
        if 'optimization_colors' not in existing_tables:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_colors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                color_code TEXT NOT NULL,
                color_type TEXT NOT NULL,
                cluster TEXT,
                ch_value REAL,
                lunghezza_ordine TEXT,
                input_sequence INTEGER,
                sequence_type TEXT,
                completed INTEGER DEFAULT 0,
                in_execution INTEGER DEFAULT 0,
                sequence_order INTEGER,
                cabin_id INTEGER DEFAULT 1,
                is_prioritized INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            logger.info("Tabella optimization_colors creata")
        else:
            # Aggiungi le nuove colonne se la tabella esiste ma non ha tutte le colonne
            cursor.execute("PRAGMA table_info(optimization_colors)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # Lista delle colonne che dovrebbero esistere
            required_columns = {
                'ch_value': 'REAL',
                'lunghezza_ordine': 'TEXT',
                'sequence_type': 'TEXT', 
                'cabin_id': 'INTEGER DEFAULT 1',
                'is_prioritized': 'INTEGER DEFAULT 0',
                'sequence_order': 'INTEGER'
            }
            
            # Aggiungi le colonne mancanti
            for column, column_type in required_columns.items():
                if column not in existing_columns:
                    cursor.execute(f'ALTER TABLE optimization_colors ADD COLUMN {column} {column_type}')
                    logger.info(f"Aggiunta colonna {column} alla tabella optimization_colors")
                    
            # Aggiungi campo locked se non esiste
            try:
                cursor.execute("ALTER TABLE optimization_colors ADD COLUMN locked BOOLEAN DEFAULT 0")
                logger.info("Aggiunto campo 'locked' alla tabella optimization_colors")
            except sqlite3.Error as e:
                if "duplicate column name" not in str(e).lower():
                    logger.warning(f"Errore durante aggiunta campo locked: {e}")
            
            # Aggiungi campo position se non esiste  
            try:
                cursor.execute("ALTER TABLE optimization_colors ADD COLUMN position INTEGER")
                logger.info("Aggiunto campo 'position' alla tabella optimization_colors")
            except sqlite3.Error as e:
                if "duplicate column name" not in str(e).lower():
                    logger.warning(f"Errore durante aggiunta campo position: {e}")
        
        # Verifica i dati esistenti per debug
        cursor.execute("SELECT DISTINCT source_cluster FROM cambio_colori")
        source_clusters = [row[0] for row in cursor.fetchall()]
        logger.info(f"Source clusters esistenti: {source_clusters}")
        
        cursor.execute("SELECT DISTINCT cluster FROM cluster_colori")
        clusters = [row[0] for row in cursor.fetchall()]
        logger.info(f"Clusters esistenti: {clusters}")
        
        # Verifica se è necessaria la migrazione dei dati
        if 'A' in source_clusters or 'B' in source_clusters or 'C' in source_clusters:
            logger.info("Avvio migrazione dei dati...")
            migrate_db_data()
        
        conn.commit()
        logger.info("Database inizializzato con successo")
        return True
    except sqlite3.Error as e:
        logger.error(f"Errore durante l'inizializzazione del database: {e}")
        return False
    finally:
        if conn:
            conn.close()

# === CAMBIO COLORI ===
def get_all_cambio_colori_grouped() -> Dict[str, List[Dict[str, Any]]]:
    """Ottiene tutte le regole di cambio_colori, raggruppate per source_cluster."""
    grouped_rules: Dict[str, List[Dict[str, Any]]] = {}
    conn = connect_to_db()
    if not conn:
        return grouped_rules
    try:
        cursor = conn.cursor()
        
        # Ottieni tutte le righe ordinate per source_cluster
        cursor.execute("SELECT * FROM cambio_colori ORDER BY source_cluster, target_cluster")
        rows = cursor.fetchall()
        
        # Debug: stampa tutte le righe trovate
        print(f"Trovate {len(rows)} righe nella tabella cambio_colori")
        
        for row in rows:
            row_dict = dict(row)
            source_cluster = row_dict['source_cluster']
            
            # Assicurati che il source_cluster non sia None o vuoto
            if not source_cluster:
                print(f"Attenzione: riga con source_cluster vuoto: {row_dict}")
                continue
                
            if source_cluster not in grouped_rules:
                grouped_rules[source_cluster] = []
            
            # Gestisci il campo transition_colors come JSON
            if 'transition_colors' in row_dict and row_dict['transition_colors']:
                try:
                    # Se è già una stringa JSON, convertila in lista
                    if isinstance(row_dict['transition_colors'], str):
                        # Rimuovi eventuali spazi bianchi e sostituisci le virgolette singole con doppie
                        json_str = row_dict['transition_colors'].strip().replace("'", '"')
                        row_dict['transition_colors'] = json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"Errore nel parsing JSON per transition_colors: {e}, valore: {row_dict['transition_colors']}")
                    # In caso di errore, mantieni il valore originale come stringa
            
            grouped_rules[source_cluster].append(row_dict)
        
        # Debug: stampa i cluster trovati e il numero di righe per cluster
        print(f"Gruppi di regole trovati: {list(grouped_rules.keys())}")
        for cluster, rules in grouped_rules.items():
            print(f"Cluster '{cluster}': {len(rules)} regole")
            
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
def get_all_cluster_colori_grouped() -> Dict[str, List[Dict[str, Any]]]:
    """Ottiene tutti i mapping cluster_colori, raggruppati per cluster."""
    grouped_mappings: Dict[str, List[Dict[str, Any]]] = {}
    conn = connect_to_db()
    if not conn:
        return grouped_mappings
    try:
        cursor = conn.cursor()
        
        # Ottieni tutte le righe ordinate per cluster
        cursor.execute("SELECT * FROM cluster_colori ORDER BY cluster, color_code")
        rows = cursor.fetchall()
        
        # Debug: stampa tutte le righe trovate
        print(f"Trovate {len(rows)} righe nella tabella cluster_colori")
        
        for row in rows:
            row_dict = dict(row)
            cluster_name = row_dict['cluster']
            
            # Assicurati che il cluster non sia None o vuoto
            if not cluster_name:
                print(f"Attenzione: riga con cluster vuoto: {row_dict}")
                continue
                
            if cluster_name not in grouped_mappings:
                grouped_mappings[cluster_name] = []
                
            grouped_mappings[cluster_name].append(row_dict)
        
        # Debug: stampa i cluster trovati e il numero di righe per cluster
        print(f"Gruppi di cluster trovati: {list(grouped_mappings.keys())}")
        for cluster, colors in grouped_mappings.items():
            print(f"Cluster '{cluster}': {len(colors)} colori")
            
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
    clusters = []
    conn = connect_to_db()
    if not conn:
        return clusters
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT cluster FROM cluster_colori ORDER BY cluster")
        clusters = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Errore in get_unique_clusters: {e}")
    finally:
        if conn:
            conn.close()
    return clusters

def sync_clusters_to_source_clusters():
    """Sincronizza i cluster dalla tabella cluster_colori alla tabella cambio_colori.
    Assicura che ogni cluster in cluster_colori esista anche come source_cluster in cambio_colori."""
    # Ottieni tutti i cluster esistenti
    all_clusters = get_unique_clusters()
    # Ottieni tutti i source_cluster esistenti
    existing_source_clusters = get_unique_source_clusters()
    
    # Trova i cluster che non sono ancora source_cluster
    new_source_clusters = [c for c in all_clusters if c not in existing_source_clusters]
    
    if not new_source_clusters:
        return True  # Nessun nuovo cluster da sincronizzare
    
    # Per ogni nuovo cluster, crea una regola di transizione di base
    conn = connect_to_db()
    if not conn:
        return False
    
    try:
        for source_cluster in new_source_clusters:
            # Scegli un target_cluster diverso dal source_cluster se possibile
            target_clusters = [c for c in all_clusters if c != source_cluster]
            target_cluster = target_clusters[0] if target_clusters else source_cluster
            
            # Aggiungi una regola di base
            add_cambio_colori_row(
                source_cluster=source_cluster,
                target_cluster=target_cluster,
                peso=100,  # Peso di default
                transition_colors="[]",  # Nessun colore di transizione
                required_trigger_type=None  # Nessun trigger richiesto
            )
            print(f"Sincronizzato cluster '{source_cluster}' come source_cluster con target '{target_cluster}'")
        
        return True
    except sqlite3.Error as e:
        print(f"Errore durante la sincronizzazione dei cluster: {e}")
        return False
    finally:
        if conn:
            conn.close()

def check_and_fix_transition_weights():
    """Controlla e corregge i pesi delle transizioni problematiche."""
    conn = connect_to_db()
    if not conn:
        logger.error("Impossibile controllare i pesi delle transizioni: connessione al database fallita")
        return
    
    try:
        cursor = conn.cursor()
        
        # Controlla il peso della transizione Nero->Bianco (nota come problematica)
        cursor.execute(
            "SELECT peso FROM cambio_colori WHERE source_cluster = ? AND target_cluster = ?",
            ("Nero", "Bianco")
        )
        row = cursor.fetchone()
        
        if row:
            current_weight = row[0]
            if current_weight < 200:  # Se il peso è troppo basso
                # Imposta un peso molto alto per evitare questa transizione
                cursor.execute(
                    "UPDATE cambio_colori SET peso = ? WHERE source_cluster = ? AND target_cluster = ?",
                    (250, "Nero", "Bianco")
                )
                conn.commit()
                logger.warning(f"Transizione Nero->Bianco corretta: peso aumentato da {current_weight} a 250")
            else:
                logger.info(f"Transizione Nero->Bianco ha già un peso alto: {current_weight}")
        else:
            logger.warning("Transizione Nero->Bianco non trovata nel database")
        
        # Verifica anche che ci siano alternative ragionevoli da Nero
        cursor.execute(
            "SELECT target_cluster, peso FROM cambio_colori WHERE source_cluster = ? AND target_cluster != ? ORDER BY peso",
            ("Nero", "Bianco")
        )
        
        alternatives = cursor.fetchall()
        if alternatives:
            logger.info("Alternative alla transizione Nero->Bianco:")
            for alt in alternatives:
                logger.info(f"  - Nero->{alt['target_cluster']}: peso {alt['peso']}")
        else:
            logger.warning("Nessuna alternativa alla transizione Nero->Bianco trovata!")
            
    except sqlite3.Error as e:
        logger.error(f"Errore SQL durante la verifica dei pesi: {e}")
    finally:
        conn.close()

def merge_locked_colors(original_colors, optimized_colors):
    """
    Unisce lo stato locked dei colori originali con quelli ottimizzati (per posizione e codice colore).
    """
    locked_map = {c.get('color_code') or c.get('code'): c.get('locked', False) for c in original_colors}
    for color in optimized_colors:
        code = color.get('color_code') or color.get('code')
        if code in locked_map:
            color['locked'] = locked_map[code]
    return optimized_colors

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'una-chiave-segreta-default-per-sviluppo')

# Disable CSRF protection entirely for testing
app.config['WTF_CSRF_ENABLED'] = False

# Configura CSRF per escludere le API routes
# app.config['WTF_CSRF_EXEMPT_LIST'] = [
#     'api_optimize',
#     'api_clusters', 
#     'api_cabin_status',
#     'api_cabin_colors',
#     'api_cabin_color_execution',
#     'api_cabin_color_delete',
#     'api_clear_all'
# ]

# Inizializza la protezione CSRF (temporaneamente disabilitata per test)
# csrf = CSRFProtect(app)

# ... (rest of the code remains the same)
BACKEND_URL = os.environ.get('FASTAPI_BACKEND_URL', 'http://localhost:8001')
OPTIMIZE_ENDPOINT = f"{BACKEND_URL}/optimize"

# Inizializza il database all'avvio dell'applicazione
with app.app_context():
    app.logger.setLevel(logging.DEBUG)
    logger.info("Inizializzazione dell'applicazione Flask")
    init_db()
    # Controllo e correzione dei pesi delle transizioni
    # check_and_fix_transition_weights()  # Commentato: correzione manuale già effettuata
    # Ottieni tutte le regole di cambio colore per debug
    regole = get_all_cambio_colori_grouped()
    logger.info(f"Regole di cambio colore caricate: {len(regole)} cluster source")
    for source, rules in regole.items():
        logger.info(f"Cluster source '{source}' ha {len(rules)} regole di transizione:")
        for rule in rules:
            logger.info(f"  -> {rule['target_cluster']} (peso: {rule['peso']})")

@app.route('/', methods=['GET'])
def index():
    form = OptimizationInputForm()
    return render_template('index.html', form=form)

@app.route('/db-check')
def db_check():
    """Endpoint per verificare lo stato della connessione al database."""
    result = {
        'connection': False,
        'database_path': DATABASE_PATH,
        'tables': [],
        'cambio_colori_count': 0,
        'cluster_colori_count': 0,
        'error': None
    }
    
    try:
        conn = connect_to_db()
        if conn:
            result['connection'] = True
            cursor = conn.cursor()
            
            # Ottieni le tabelle
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            result['tables'] = [table[0] for table in cursor.fetchall()]
            
            # Conta le righe nelle tabelle principali
            if 'cambio_colori' in result['tables']:
                cursor.execute("SELECT COUNT(*) FROM cambio_colori")
                result['cambio_colori_count'] = cursor.fetchone()[0]
            
            if 'cluster_colori' in result['tables']:
                cursor.execute("SELECT COUNT(*) FROM cluster_colori")
                result['cluster_colori_count'] = cursor.fetchone()[0]
            
            conn.close()
    except Exception as e:
        result['error'] = str(e)
    
    return jsonify(result)

@app.route('/db-diagnostic')
def db_diagnostic():
    """Endpoint per visualizzare il contenuto esatto del database."""
    result = {
        'cambio_colori': [],
        'cluster_colori': [],
        'error': None
    }
    
    try:
        conn = connect_to_db()
        if conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Ottieni tutte le righe dalla tabella cambio_colori
            cursor.execute("SELECT * FROM cambio_colori")
            cambio_rows = cursor.fetchall()
            for row in cambio_rows:
                row_dict = dict(row)
                # Converti il campo transition_colors in JSON se possibile
                if 'transition_colors' in row_dict and row_dict['transition_colors']:
                    try:
                        json_str = row_dict['transition_colors'].strip().replace("'", '"')
                        row_dict['transition_colors'] = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Mantieni il valore originale se non è JSON valido
                        pass
                result['cambio_colori'].append(row_dict)
            
            # Ottieni tutte le righe dalla tabella cluster_colori
            cursor.execute("SELECT * FROM cluster_colori")
            cluster_rows = cursor.fetchall()
            for row in cluster_rows:
                result['cluster_colori'].append(dict(row))
            
            conn.close()
    except Exception as e:
        result['error'] = str(e)
    
    return jsonify(result)

@app.route('/db-cambio-colori')
def db_cambio_colori():
    """Endpoint per visualizzare le transizioni e i pesi."""
    try:
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Impossibile connettersi al database"}), 500
        
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Ottieni tutte le transizioni dalla tabella cambio_colori, ordinate per peso
        cursor.execute("SELECT source_cluster, target_cluster, peso FROM cambio_colori ORDER BY source_cluster, peso")
        rows = cursor.fetchall()
        
        # Organizza i dati per source_cluster
        result = {}
        for row in rows:
            source = row["source_cluster"]
            target = row["target_cluster"]
            peso = row["peso"]
            
            if source not in result:
                result[source] = []
            
            result[source].append({
                "target": target,
                "peso": peso
            })
        
        # Cerca eventuali problemi nelle transizioni
        problemi = []
        
        # Verifica se ci sono transizioni ad alto costo (>50)
        for source, targets in result.items():
            for target_info in targets:
                if target_info["peso"] > 50:
                    problemi.append(f"Transizione costosa: {source} -> {target_info['target']} (peso: {target_info['peso']})")
        
        conn.close()
        
        return jsonify({
            "transizioni": result,
            "problemi": problemi
        })
        
    except Exception as e:
        logger.error(f"Errore in db-cambio-colori: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/optimize', methods=['POST'])
def optimize():
    is_json_request = request.content_type == 'application/json'
    payload_to_backend = {}
    
    # Questo dizionario conterrà i dati da passare al tag <script id="initial-data">
    # quando la pagina results.html viene renderizzata per la prima volta.
    initial_page_data_for_script = {
        "original_input_json": [], # Sarà la lista di colori inviata dall'utente
        "original_start_cluster": "",
        "current_prioritized_reintegrations": [], # All'inizio, nessuna priorità
        "results": None # Risultati dell'ottimizzazione iniziale
    }

    if is_json_request:
        logger.info("Richiesta JSON ricevuta (da JS per ri-ottimizzazione)")
        try:
            payload_from_js = request.get_json()
            if not payload_from_js: raise ValueError("Payload JSON vuoto.")
            
            payload_to_backend = {
                "colors_today": payload_from_js.get("colors_today", []),
                "start_cluster_name": payload_from_js.get("start_cluster_name"),
                "prioritized_reintegrations": payload_from_js.get("prioritized_reintegrations", [])
            }
            logger.debug(f"Payload da JavaScript: {json.dumps(payload_to_backend)}")
            # Non modifichiamo initial_page_data_for_script qui perché non stiamo renderizzando
            # un nuovo HTML completo, ma restituendo JSON.
        except Exception as e:
            logger.error(f"Errore nel processare richiesta JSON: {e}")
            return jsonify({"error": f"Errore nel payload JSON ricevuto: {e}", "message": f"Errore nel payload JSON ricevuto: {e}"}), 400

    else: # Invio da Form HTML (prima ottimizzazione dalla pagina index)
        logger.info("Invio da Form HTML ricevuto")
        form = OptimizationInputForm()
        if not form.validate_on_submit():
            for field, errors_list in form.errors.items(): # Rinomina 'errors'
                for error_item in errors_list: # Rinomina 'error'
                    flash(f"Errore nel campo '{getattr(form, field).label.text}': {error_item}", 'danger')
            return redirect(url_for('index'))

        colors_json_str_from_form = form.colors_json.data
        start_cluster_str_from_form = form.start_cluster.data.strip()
        
        logger.debug(f"Input dal form - colori: {colors_json_str_from_form}, cluster iniziale: {start_cluster_str_from_form}")

        try:
            colors_list_from_form = json.loads(colors_json_str_from_form)
            if not isinstance(colors_list_from_form, list):
                raise ValueError("Il JSON dei colori non è una lista.")
            
            # Popola i dati per lo script con l'input originale del form
            initial_page_data_for_script["original_input_json"] = colors_list_from_form
            initial_page_data_for_script["original_start_cluster"] = start_cluster_str_from_form
            # current_prioritized_reintegrations rimane [] per il primo invio

            payload_to_backend = {
                "colors_today": colors_list_from_form,
                "start_cluster_name": start_cluster_str_from_form if start_cluster_str_from_form else None,
                "prioritized_reintegrations": [] # Nessuna priorità al primo invio
            }
        except Exception as e:
            flash(f"Errore nei dati del form: {e}", "danger")
            return render_template('index.html', form=form) # Torna a index se il form ha problemi
    
    # --- Chiamata al Backend ---
    # --- Chiamata al Backend ---
    logger.info(f"Invio richiesta a {OPTIMIZE_ENDPOINT}")
    # Aggiungi log più dettagliati per il parametro start_cluster_name
    logger.warning(f"Invio start_cluster_name al backend: '{payload_to_backend.get('start_cluster_name')}'")
    logger.debug(f"Payload completo: {json.dumps(payload_to_backend)}")
    try:
        response = requests.post(OPTIMIZE_ENDPOINT, json=payload_to_backend, timeout=120)
        response.raise_for_status()
        backend_results = response.json() 
        logger.info(f"Risposta ricevuta dal backend")
        
        # Log dettagliati sui risultati dell'ottimizzazione
        if 'optimal_cluster_sequence' in backend_results:
            seq = backend_results['optimal_cluster_sequence']
            logger.info(f"Sequenza cluster ottimale: {' -> '.join(seq)}")
            # Verifica se il cluster iniziale richiesto è stato rispettato
            if payload_to_backend.get('start_cluster_name') and seq and seq[0] != payload_to_backend.get('start_cluster_name'):
                logger.error(f"ERRORE: Il cluster iniziale richiesto '{payload_to_backend.get('start_cluster_name')}' non corrisponde al cluster iniziale restituito '{seq[0]}'")
            
            # Analizza transizioni e costi
            if len(seq) > 1:
                cambio_colori = get_all_cambio_colori_grouped()
                logger.info("Analisi dei costi di transizione:")
                total_cost = 0
                for i in range(len(seq)-1):
                    source = seq[i]
                    target = seq[i+1]
                    cost = None
                    
                    # Cerca il costo nella tabella cambio_colori
                    if source in cambio_colori:
                        for rule in cambio_colori[source]:
                            if rule['target_cluster'] == target:
                                cost = rule['peso']
                                break
                    
                    logger.info(f"  {source} -> {target}: Costo = {cost if cost is not None else 'NON TROVATO!'}")
                    if cost is not None:
                        total_cost += cost
                
                logger.info(f"Costo totale calcolato: {total_cost}")
                # Verifica se il costo calcolato corrisponde a quello riportato
                if 'calculated_cost' in backend_results:
                    reported_cost = float(backend_results['calculated_cost'])
                    logger.info(f"Costo riportato dal backend: {reported_cost}")
                    if abs(total_cost - reported_cost) > 0.01:
                        logger.warning(f"DISCREPANZA NEI COSTI: calcolato={total_cost}, riportato={reported_cost}")
                
                # Verifica specifica per la transizione Nero -> Bianco
                for i in range(len(seq)-1):
                    if seq[i] == "Nero" and seq[i+1] == "Bianco":
                        # Trova il peso attuale nel database
                        conn_check = connect_to_db()
                        if conn_check:
                            try:
                                cursor_check = conn_check.cursor()
                                cursor_check.execute(
                                    "SELECT peso FROM cambio_colori WHERE source_cluster = ? AND target_cluster = ?",
                                    ("Nero", "Bianco")
                                )
                                row_check = cursor_check.fetchone()
                                if row_check:
                                    db_weight = row_check[0]
                                    logger.error(f"ATTENZIONE! Trovata transizione Nero->Bianco nella sequenza ottimale nonostante peso alto ({db_weight})")
                            except sqlite3.Error as e_check:
                                logger.error(f"Errore durante verifica peso Nero->Bianco: {e_check}")
                            finally:
                                conn_check.close()

        # Salva i risultati nel database - gestisce sia risultati standard che per cabine
        def save_colors_to_db(colors_list, cabin_id_override=None):
            """Helper function to save colors to database with proper cabin handling"""
            if not colors_list:
                return
                
            conn = connect_to_db()
            if not conn:
                return
                
            try:
                cursor = conn.cursor()
                
                # Prima verifica se la tabella optimization_colors esiste
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='optimization_colors'")
                table_exists = cursor.fetchone()
                
                if not table_exists:
                    # Crea la tabella se non esiste
                    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS optimization_colors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        color_code TEXT NOT NULL,
                        color_type TEXT NOT NULL,
                        cluster TEXT,
                        sequence_order INTEGER,
                        completed INTEGER DEFAULT 0,
                        in_execution INTEGER DEFAULT 0,
                        line TEXT DEFAULT 'Cabina 1',
                        m2 REAL DEFAULT 0.0,
                        input_sequence INTEGER,
                        ch_value REAL,
                        lunghezza_ordine TEXT,
                        sequence_type TEXT,
                        cabin_id INTEGER DEFAULT 1,
                        is_prioritized INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    ''')
                
                # Aggiungi campo locked se non esiste
                try:
                    cursor.execute("ALTER TABLE optimization_colors ADD COLUMN locked BOOLEAN DEFAULT 0")
                    logger.info("Aggiunto campo 'locked' alla tabella optimization_colors")
                except sqlite3.Error as e:
                    if "duplicate column name" not in str(e).lower():
                        logger.warning(f"Errore durante aggiunta campo locked: {e}")
                
                # Aggiungi campo position se non esiste  
                try:
                    cursor.execute("ALTER TABLE optimization_colors ADD COLUMN position INTEGER")
                    logger.info("Aggiunto campo 'position' alla tabella optimization_colors")
                except sqlite3.Error as e:
                    if "duplicate column name" not in str(e).lower():
                        logger.warning(f"Errore durante aggiunta campo position: {e}")
                
                # Ottieni la lista dei reintegri prioritari
                prioritized_reintegrations = payload_to_backend.get("prioritized_reintegrations", [])
                
                # Inserisci le righe dei colori ottimizzati
                for idx, color in enumerate(colors_list):
                    color_code = color.get('color_code', color.get('code', ''))
                    color_type = color.get('color_type', color.get('type', ''))
                    cluster = color.get('cluster_name', color.get('cluster', ''))
                    input_sequence = color.get('input_sequence', color.get('sequence'))
                    ch_value = color.get('CH')
                    lunghezza_ordine = color.get('lunghezza_ordine')
                    sequence_type = color.get('sequence_type')
                    
                    # Determina cabin_id - usa override se specificato, altrimenti basato su lunghezza_ordine
                    if cabin_id_override is not None:
                        cabin_id = cabin_id_override
                    else:
                        cabin_id = 2 if lunghezza_ordine == 'lungo' else 1
                    
                    # Determina se è un colore prioritario
                    is_prioritized = 1 if color_code in prioritized_reintegrations else 0
                    if is_prioritized:
                        print(f"Colore {color_code} impostato come prioritario nel database (optimize route)")
                    
                    cursor.execute('''
                    INSERT INTO optimization_colors (
                        color_code, color_type, cluster, sequence_order, 
                        completed, in_execution, input_sequence, ch_value,
                        lunghezza_ordine, sequence_type, cabin_id, is_prioritized
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        color_code, 
                        color_type, 
                        cluster, 
                        idx, 
                        1 if color.get('completed', False) else 0,
                        1 if color.get('in_execution', False) else 0,
                        input_sequence,
                        ch_value,
                        lunghezza_ordine,
                        sequence_type,
                        cabin_id,
                        is_prioritized
                    ))
                    
                    # Ottieni l'ID generato e aggiungilo all'oggetto colore
                    color['id'] = cursor.lastrowid
                
                conn.commit()
                print(f"Salvati {len(colors_list)} colori nel database (cabin_id: {cabin_id})")
            except sqlite3.Error as e:
                print(f"Errore SQL durante il salvataggio dei colori: {e}")
            finally:
                conn.close()

        # Salva i risultati nel database
        if backend_results:
            if 'cabina_1' in backend_results and 'cabina_2' in backend_results:
                # Risultati per cabine separate
                print("Salvataggio risultati cabine nel database...")
                
                # Salva colori cabina 1
                if backend_results['cabina_1'].get('ordered_colors'):
                    save_colors_to_db(backend_results['cabina_1']['ordered_colors'], cabin_id_override=1)
                
                # Salva colori cabina 2  
                if backend_results['cabina_2'].get('ordered_colors'):
                    save_colors_to_db(backend_results['cabina_2']['ordered_colors'], cabin_id_override=2)
                    
            elif 'ordered_colors' in backend_results and backend_results['ordered_colors']:
                # Risultati standard
                print("Salvataggio risultati standard nel database...")
                save_colors_to_db(backend_results['ordered_colors'])

        if is_json_request:
            backend_results["prioritized_reintegrations_used"] = payload_to_backend.get("prioritized_reintegrations", [])
            return jsonify(backend_results)
        else:
            # Per il primo rendering, popola i risultati e i dati iniziali
            initial_page_data_for_script["results"] = backend_results
            # current_prioritized_reintegrations è già []
            
            return render_template('results.html', 
                                   results=backend_results, # Per la visualizzazione Jinja iniziale
                                   error_message=None,      
                                   current_prioritized_reintegrations=payload_to_backend.get("prioritized_reintegrations", []),
                                   initial_data_json=json.dumps(initial_page_data_for_script)
                                  )

    except requests.exceptions.RequestException as e_req:
        error_text = f"Errore durante la richiesta al backend: {e_req}."
        # ... (aggiungi dettagli errore) ...
        print(error_text)

        # Costruisci initial_page_data_for_script anche in caso di errore
        initial_page_data_for_script["results"] = None # Non ci sono risultati validi
        initial_page_data_for_script["error_message"] = error_text # Memorizza l'errore per lo script
        # current_prioritized_reintegrations rimane quella che era per questa richiesta
        initial_page_data_for_script["current_prioritized_reintegrations"] = payload_to_backend.get("prioritized_reintegrations", [])


        if is_json_request:
             return jsonify({"error": error_text, "message": error_text, "ordered_colors": [], "optimal_cluster_sequence": [], "calculated_cost": "Errore"}), 500
        else:
             return render_template('results.html', 
                                    results=None, # Jinja non mostrerà la tabella
                                    error_message=error_text, # Jinja mostrerà questo errore
                                    current_prioritized_reintegrations=payload_to_backend.get("prioritized_reintegrations", []),
                                    initial_data_json=json.dumps(initial_page_data_for_script)
                                   )
    except Exception as e_gen:
        error_text = f"Errore imprevisto nel frontend: {e_gen}"
        print(error_text)
        traceback.print_exc()
        initial_page_data_for_script["results"] = None
        initial_page_data_for_script["error_message"] = "Errore interno del server nel frontend."
        initial_page_data_for_script["current_prioritized_reintegrations"] = payload_to_backend.get("prioritized_reintegrations", [])


        if is_json_request:
             return jsonify({"error": "Errore interno del server nel frontend.", "message": "Errore interno...", "ordered_colors": [], "optimal_cluster_sequence": [], "calculated_cost": "Errore"}), 500
        else:
             flash(f"Errore interno: {e_gen}", "danger")
             # Potrebbe essere meglio reindirizzare o mostrare una pagina di errore più generica
             return render_template('results.html', 
                                        results=None, 
                                        error_message="Errore interno grave.", 
                                        current_prioritized_reintegrations=initial_page_data_for_script.get("current_prioritized_reintegrations", []),
                                        initial_data_json=json.dumps(initial_page_data_for_script))

@app.route('/show_saved_results')
def show_saved_results():
    """Mostra l'ultima sequenza di colori salvata nel database."""
    try:
        conn = connect_to_db()
        if not conn:
            flash("Impossibile connettersi al database", "danger")
            return redirect(url_for('index'))
        
        cursor = conn.cursor()
        
        # Verifica se esiste la tabella saved_sequences
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='saved_sequences'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            flash("Nessuna sequenza salvata trovata nel database", "warning")
            return redirect(url_for('index'))
        
        # Ottieni l'ultima sequenza salvata
        cursor.execute("""
            SELECT id, sequence_data, created_at 
            FROM saved_sequences 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        saved_sequence = cursor.fetchone()
        
        if not saved_sequence:
            flash("Nessuna sequenza salvata trovata", "warning")
            return redirect(url_for('index'))
        
        # Converti la stringa JSON in un oggetto Python
        sequence_data = json.loads(saved_sequence['sequence_data'])
        
        # Prepara i dati iniziali per lo script
        initial_page_data = {
            "original_input_json": sequence_data.get("original_colors", []),
            "original_start_cluster": sequence_data.get("start_cluster", ""),
            "current_prioritized_reintegrations": sequence_data.get("prioritized_reintegrations", []),
            "results": sequence_data
        }
        
        # Rendi il template con i dati caricati
        return render_template('results.html', 
                               results=sequence_data,
                               error_message=None,
                               current_prioritized_reintegrations=sequence_data.get("prioritized_reintegrations", []),
                               initial_data_json=json.dumps(initial_page_data))
    
    except Exception as e:
        print(f"Errore nel caricare la sequenza salvata: {e}")
        traceback.print_exc()
        flash(f"Errore nel caricare la sequenza salvata: {e}", "danger")
        return redirect(url_for('index'))
    finally:
        if conn:
            conn.close()

@app.route('/save_current_sequence', methods=['POST'])
def save_current_sequence():
    """Salva la sequenza attuale di colori nel database."""
    try:
        data = request.get_json()
        
        if not data or 'sequence_data' not in data:
            return jsonify({"success": False, "error": "Dati mancanti per il salvataggio"}), 400
        
        sequence_data = data['sequence_data']
        
        # Salva nel database
        conn = connect_to_db()
        if not conn:
            return jsonify({"success": False, "error": "Errore di connessione al database"}), 500
        
        try:
            cursor = conn.cursor()
            
            # Converti l'oggetto Python in una stringa JSON
            sequence_json = json.dumps(sequence_data)
            
            cursor.execute("""
                INSERT INTO saved_sequences (sequence_data)
                VALUES (?)
            """, (sequence_json,))
            
            conn.commit()
            
            # Ottieni l'ID del record appena inserito
            sequence_id = cursor.lastrowid
            
            return jsonify({
                "success": True, 
                "message": "Sequenza salvata con successo",
                "sequence_id": sequence_id
            })
            
        except sqlite3.Error as e:
            print(f"Errore nel salvataggio della sequenza: {e}")
            return jsonify({"success": False, "error": f"Errore nel salvare la sequenza: {e}"}), 500
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        print(f"Errore in save_current_sequence: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Errore generale: {e}"}), 500

@app.route('/mark_complete/<int:item_id>', methods=['POST'])
def mark_item_complete(item_id):
    """Marca un elemento come completato o non completato."""
    try:
        data = request.get_json()
        if data is None:
            # Stampa il corpo della richiesta per debug
            raw_data = request.get_data()
            print(f"Contenuto grezzo della richiesta: {raw_data}")
            try:
                # Tenta di decodificare manualmente come stringa
                decoded_data = raw_data.decode('utf-8')
                print(f"Contenuto decodificato: {decoded_data}")
                # Tenta parsing manuale del JSON
                if decoded_data.strip():
                    data = json.loads(decoded_data)
                else:
                    data = {"completed": True}  # Default se il corpo è vuoto
            except Exception as parse_error:
                print(f"Errore nel parsing manuale: {parse_error}")
                return jsonify({"success": False, "error": f"JSON non valido: {parse_error}"}), 400
        
        completed = data.get('completed', True)  # Default a True
        print(f"Richiesta di aggiornamento completamento per item_id={item_id}, completato={completed}")
        
        conn = connect_to_db()
        if not conn:
            return jsonify({"success": False, "error": "Errore di connessione al database"}), 500
        
        try:
            cursor = conn.cursor()
            
            # Prima verifica se l'elemento esiste e ottieni il suo stato attuale
            cursor.execute("SELECT completed, in_execution FROM optimization_colors WHERE id = ?", (item_id,))
            item = cursor.fetchone()
            
            if not item:
                return jsonify({"success": False, "error": f"Elemento con ID {item_id} non trovato"}), 404
            
            # Aggiorna lo stato di completamento
            cursor.execute("""
                UPDATE optimization_colors 
                SET completed = ?, 
                    in_execution = CASE WHEN ? = 1 THEN 0 ELSE in_execution END
                WHERE id = ?
            """, (1 if completed else 0, 1 if completed else 0, item_id))
            
            conn.commit()
            
            return jsonify({"success": True, "message": f"Stato completamento aggiornato per ID {item_id}"})
            
        except sqlite3.Error as e:
            print(f"Errore SQL in mark_item_complete: {e}")
            return jsonify({"success": False, "error": f"Errore database: {e}"}), 500
        finally:
            if conn: conn.close()
                
    except json.JSONDecodeError as e:
        print(f"Errore nel parsing JSON in mark_item_complete: {e}")
        print(f"Contenuto della richiesta: {request.get_data()}")
        return jsonify({"success": False, "error": f"JSON non valido: {e}"}), 400
    except Exception as e:
        print(f"Errore generico in mark_item_complete: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Errore generale: {e}"}), 500

@app.route('/set_in_execution/<int:item_id>', methods=['POST'])
def set_in_execution(item_id):
    """Imposta un elemento come 'in esecuzione'. Solo un elemento può essere 'in esecuzione' alla volta.
    Quando un nuovo elemento viene impostato come 'in esecuzione', quello precedente diventa 'completato'."""
    try:
        print(f"Richiesta di impostazione esecuzione per item_id={item_id}")
        
        conn = connect_to_db()
        if not conn:
            return jsonify({"success": False, "error": "Errore di connessione al database"}), 500
        
        try:
            cursor = conn.cursor()
            
            # Verifica se l'elemento esiste e ottieni il suo sequence_order
            cursor.execute("SELECT sequence_order FROM optimization_colors WHERE id = ?", (item_id,))
            item = cursor.fetchone()
            
            if not item:
                return jsonify({"success": False, "error": f"Elemento con ID {item_id} non trovato"}), 404
            
            current_sequence_order = item[0]
            
            # Trova l'elemento attualmente "in esecuzione" (se esiste)
            cursor.execute("SELECT id FROM optimization_colors WHERE in_execution = 1")
            current_in_execution = cursor.fetchone()
            
            # Se c'è un elemento già "in esecuzione", marcalo come completato
            if current_in_execution:
                cursor.execute("""
                    UPDATE optimization_colors 
                    SET in_execution = 0, completed = 1 
                    WHERE in_execution = 1
                """)
                print(f"Elemento precedentemente in esecuzione (ID {current_in_execution[0]}) marcato come completato")
            
            # Marca come completati tutti gli elementi con sequence_order minore del nuovo elemento in esecuzione
            cursor.execute("""
                UPDATE optimization_colors 
                SET completed = 1 
                WHERE sequence_order < ? AND completed = 0
            """, (current_sequence_order,))
            
            # Imposta l'elemento corrente come 'in esecuzione' e assicurati che non sia completato
            cursor.execute("""
                UPDATE optimization_colors 
                SET in_execution = 1, completed = 0
                WHERE id = ?
            """, (item_id,))
            
            conn.commit()
            
            # Ottieni tutti gli elementi completati per aggiornare il frontend
            cursor.execute("SELECT id FROM optimization_colors WHERE completed = 1")
            completed_ids = [row[0] for row in cursor.fetchall()]
            
            return jsonify({
                "success": True, 
                "message": f"Elemento ID {item_id} impostato in esecuzione",
                "completed_ids": completed_ids,
                "previous_in_execution_id": current_in_execution[0] if current_in_execution else None
            })
            
        except sqlite3.Error as e:
            print(f"Errore SQL in set_in_execution: {e}")
            return jsonify({"success": False, "error": f"Errore database: {e}"}), 500
        finally:
            if conn: conn.close()
                
    except Exception as e:
        print(f"Errore generico in set_in_execution: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Errore generale: {e}"}), 500

@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    """Elimina un elemento dalla sequenza."""
    try:
        print(f"Richiesta di eliminazione per item_id={item_id}")
        
        conn = connect_to_db()
        if not conn:
            return jsonify({"success": False, "error": "Errore di connessione al database"}), 500
        
        try:
            cursor = conn.cursor()
            
            # Verifica se l'elemento esiste
            cursor.execute("SELECT id FROM optimization_colors WHERE id = ?", (item_id,))
            item = cursor.fetchone()
            
            if not item:
                return jsonify({"success": False, "error": f"Elemento con ID {item_id} non trovato"}), 404
            
            # Elimina l'elemento
            cursor.execute("DELETE FROM optimization_colors WHERE id = ?", (item_id,))
            
            conn.commit()
            
            return jsonify({
                "success": True, 
                "message": f"Elemento ID {item_id} eliminato con successo"
            })
            
        except sqlite3.Error as e:
            print(f"Errore SQL in delete_item: {e}")
            return jsonify({"success": False, "error": f"Errore database: {e}"}), 500
        finally:
            if conn: conn.close()
                
    except Exception as e:
        print(f"Errore generico in delete_item: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Errore generale: {e}"}), 500

# --- NUOVE ROUTE PER GESTIONE DB ---

@app.route('/manage/cambio_colori', methods=['GET', 'POST'])
def manage_cambio_colori():
    # Sincronizza i cluster esistenti con i source_cluster
    # Questo assicura che tutti i cluster creati in 'Gestione Cluster Colori'
    # siano disponibili anche in 'Gestione Cambio Colori'
    sync_clusters_to_source_clusters()
    
    new_source_cluster_form = NewSourceClusterForm(prefix="new_source")
    add_row_form = CambioColoriRowForm(prefix="add_row") # Prefisso per evitare conflitti se più form

    if new_source_cluster_form.validate_on_submit() and new_source_cluster_form.submit.data:
        # Ottieni il nome del nuovo source cluster
        source_cluster_name = new_source_cluster_form.source_cluster_name.data.strip()
        
        # Verifica se il source cluster esiste già
        existing_source_clusters = get_unique_source_clusters()
        if source_cluster_name in existing_source_clusters:
            flash(f"Il source cluster '{source_cluster_name}' esiste già. Aggiungi regole di transizione utilizzando il form sotto.", "info")
        else:
            # Ottieni tutti i cluster esistenti per creare una regola di esempio
            existing_clusters = get_unique_clusters()
            if existing_clusters:
                # Scegli un cluster di destinazione (diverso dal source se possibile)
                target_clusters = [c for c in existing_clusters if c != source_cluster_name]
                target_cluster = target_clusters[0] if target_clusters else existing_clusters[0]
                
                # Aggiungi una regola di transizione di esempio
                success = add_cambio_colori_row(
                    source_cluster=source_cluster_name,
                    target_cluster=target_cluster,
                    peso=100,  # Peso di default
                    transition_colors="[]",  # Nessun colore di transizione
                    required_trigger_type=None  # Nessun trigger richiesto
                )
                
                if success:
                    flash(f"Nuovo source cluster '{source_cluster_name}' creato con successo con una regola di transizione di esempio verso '{target_cluster}'. Aggiungi altre regole per completarlo.", "success")
                else:
                    flash(f"Errore durante la creazione del source cluster '{source_cluster_name}'.", "danger")
            else:
                # Se non ci sono cluster, suggerisci di crearne prima uno
                flash(f"Nuovo source cluster '{source_cluster_name}' registrato. Prima di aggiungere regole di transizione, crea almeno un cluster di destinazione nella sezione 'Gestione Cluster Colori'.", "warning")
        
        return redirect(url_for('manage_cambio_colori'))
    
    grouped_rules = get_all_cambio_colori_grouped()
    return render_template('manage_cambio_colori.html',
                           grouped_rules=grouped_rules,
                           new_source_cluster_form=new_source_cluster_form,
                           add_row_form_template=CambioColoriRowForm()) # Passa una istanza per il template del form di aggiunta

@app.route('/manage/cambio_colori/add_row/<source_cluster>', methods=['POST'])
def add_cambio_colori_row_route(source_cluster):
    form = CambioColoriRowForm()
    if form.validate_on_submit():
        # La transition_colors è già una stringa dal TextAreaField, validata come JSON.
        # Se non è fornita (Optional), sarà una stringa vuota o None. Assicuriamo sia stringa.
        transition_colors_str = form.transition_colors.data if form.transition_colors.data else "[]"
        
        success = add_cambio_colori_row(
            source_cluster=source_cluster,
            target_cluster=form.destination_cluster.data,
            peso=form.peso.data,
            transition_colors=transition_colors_str,
            required_trigger_type=form.required_trigger_type.data
        )
        if success:
            flash(f"Riga aggiunta a {source_cluster} con successo!", "success")
        else:
            flash(f"Errore durante l'aggiunta della riga a {source_cluster}.", "danger")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Errore nel campo '{getattr(form, field).label.text}': {error}", "danger")
    return redirect(url_for('manage_cambio_colori'))


@app.route('/manage/cambio_colori/edit/<int:row_id>', methods=['GET', 'POST'])
def edit_cambio_colori_row(row_id):
    row_data = get_cambio_colori_row_by_id(row_id)
    if not row_data:
        flash(f"Riga con ID {row_id} non trovata.", "danger")
        return redirect(url_for('manage_cambio_colori'))

    form = CambioColoriRowForm(data=row_data) # Pre-popola il form

    if form.validate_on_submit():
        transition_colors_str = form.transition_colors.data if form.transition_colors.data else "[]"
        success = update_cambio_colori_row(
            row_id=row_id,
            target_cluster=form.destination_cluster.data,
            peso=form.peso.data,
            transition_colors=transition_colors_str,
            required_trigger_type=form.required_trigger_type.data
        )
        if success:
            flash(f"Riga ID {row_id} aggiornata con successo!", "success")
        else:
            flash(f"Errore durante l'aggiornamento della riga ID {row_id}.", "danger")
        return redirect(url_for('manage_cambio_colori'))
    
    return render_template('edit_cambio_colori_row.html', form=form, row_id=row_id, source_cluster=row_data['source_cluster'])

@app.route('/manage/cambio_colori/delete/<int:row_id>', methods=['POST'])
def delete_cambio_colori_row_route(row_id):
    success = delete_cambio_colori_row(row_id)
    if success:
        flash(f"Riga ID {row_id} eliminata con successo!", "success")
    else:
        flash(f"Errore durante l'eliminazione della riga ID {row_id}.", "danger")
    return redirect(url_for('manage_cambio_colori'))

# --- CLUSTER COLORI ---
@app.route('/manage/cluster_colori', methods=['GET', 'POST'])
def manage_cluster_colori():
    new_cluster_form = NewClusterForm(prefix="new_cluster")
    
    if new_cluster_form.validate_on_submit() and new_cluster_form.submit.data:
        # Ottieni il nome del nuovo cluster
        cluster_name = new_cluster_form.cluster_name.data.strip()
        
        # Verifica se il cluster esiste già
        existing_clusters = get_unique_clusters()
        if cluster_name in existing_clusters:
            flash(f"Il cluster '{cluster_name}' esiste già. Aggiungi codici colore utilizzando il form sotto.", "info")
        else:
            # Aggiungi un colore di esempio per inizializzare il cluster
            success = add_cluster_colori_row(
                cluster=cluster_name,
                color_code="RAL9016"  # Colore bianco di default
            )
            
            if success:
                flash(f"Nuovo cluster '{cluster_name}' creato con successo con un colore di esempio (RAL9016). Aggiungi altri codici colore per completarlo.", "success")
            else:
                flash(f"Errore durante la creazione del cluster '{cluster_name}'.", "danger")
        
        return redirect(url_for('manage_cluster_colori'))

    grouped_mappings = get_all_cluster_colori_grouped()
    return render_template('manage_cluster_colori.html',
                           grouped_mappings=grouped_mappings,
                           new_cluster_form=new_cluster_form,
                           add_row_form_template=ClusterColoriRowForm())

@app.route('/manage/cluster_colori/add_row/<cluster_name>', methods=['POST'])
def add_cluster_colori_row_route(cluster_name):
    form = ClusterColoriRowForm()
    if form.validate_on_submit():
        success = add_cluster_colori_row(
            cluster=cluster_name,
            color_code=form.color_code.data
        )
        if success:
            flash(f"Codice colore aggiunto a {cluster_name} con successo!", "success")
        else:
            flash(f"Errore durante l'aggiunta del codice colore a {cluster_name}.", "danger")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Errore nel campo '{getattr(form, field).label.text}': {error}", "danger")
    return redirect(url_for('manage_cluster_colori'))

@app.route('/manage/cluster_colori/edit/<int:row_id>', methods=['GET', 'POST'])
def edit_cluster_colori_row(row_id):
    row_data = get_cluster_colori_row_by_id(row_id)
    if not row_data:
        flash(f"Mapping con ID {row_id} non trovato.", "danger")
        return redirect(url_for('manage_cluster_colori'))

    form = ClusterColoriRowForm(data=row_data) # Pre-popola

    if form.validate_on_submit():
        success = update_cluster_colori_row(
            row_id=row_id,
            color_code=form.color_code.data
        )
        if success:
            flash(f"Mapping ID {row_id} aggiornato con successo!", "success")
        else:
            flash(f"Errore durante l'aggiornamento del mapping ID {row_id}.", "danger")
        return redirect(url_for('manage_cluster_colori'))
        
    return render_template('edit_cluster_colori_row.html', form=form, row_id=row_id, cluster_name=row_data['cluster'])

@app.route('/manage/cluster_colori/delete/<int:row_id>', methods=['POST'])
def delete_cluster_colori_row_route(row_id):
    success = delete_cluster_colori_row(row_id)
    if success:
        flash(f"Mapping ID {row_id} eliminato con successo!", "success")
    else:
        flash(f"Errore durante l'eliminazione del mapping ID {row_id}.", "danger")
    return redirect(url_for('manage_cluster_colori'))

@app.route('/update-transition-weight', methods=['POST'])
def update_transition_weight():
    """Aggiorna il peso di una transizione specifica."""
    try:
        data = request.get_json()
        if not data or 'source_cluster' not in data or 'target_cluster' not in data or 'peso' not in data:
            return jsonify({"error": "Parametri mancanti"}), 400
        
        source_cluster = data['source_cluster']
        target_cluster = data['target_cluster']
        peso = int(data['peso'])
        
        if peso < 0:
            return jsonify({"error": "Il peso deve essere un numero positivo"}), 400
        
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Impossibile connettersi al database"}), 500
        
        try:
            cursor = conn.cursor()
            
            # Verifica se la transizione esiste
            cursor.execute(
                "SELECT id FROM cambio_colori WHERE source_cluster = ? AND target_cluster = ?", 
                (source_cluster, target_cluster)
            )
            row = cursor.fetchone()
            
            if not row:
                return jsonify({"error": f"Transizione {source_cluster} -> {target_cluster} non trovata"}), 404
            
            # Aggiorna il peso
            cursor.execute(
                "UPDATE cambio_colori SET peso = ? WHERE source_cluster = ? AND target_cluster = ?",
                (peso, source_cluster, target_cluster)
            )
            
            conn.commit()
            logger.info(f"Peso della transizione {source_cluster} -> {target_cluster} aggiornato a {peso}")
            
            return jsonify({
                "success": True,
                "message": f"Peso della transizione {source_cluster} -> {target_cluster} aggiornato a {peso}"
            })
            
        except Exception as e:
            logger.error(f"Errore durante l'aggiornamento del peso: {e}")
            return jsonify({"error": f"Errore durante l'aggiornamento: {e}"}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Errore generale in update-transition-weight: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== NUOVE ROUTE PER IL FRONTEND MODERNO ====================

@app.route('/')
def home():
    """Pagina principale del sistema di ottimizzazione colori."""
    return render_template('home.html')

@app.route('/cabin/<int:cabin_id>')
def cabin_view(cabin_id):
    """Vista della cabina specifica."""
    if cabin_id not in [1, 2]:
        flash('Cabina non valida. Seleziona cabina 1 o 2.', 'error')
        return redirect(url_for('home'))
    
    return render_template('cabin.html', cabin_id=cabin_id)

# ==================== API ENDPOINTS ====================

@app.route('/api/clusters')
def api_get_clusters():
    """API per ottenere la lista dei clusters disponibili."""
    try:
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Connessione database fallita"}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT cluster FROM cluster_colori ORDER BY cluster")
        clusters = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({"clusters": clusters})
    except Exception as e:
        logger.error(f"Errore in api_get_clusters: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin-status')
def api_cabin_status():
    """API per ottenere lo stato delle cabine."""
    try:
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Connessione database fallita"}), 500
        
        cursor = conn.cursor()
        
        # Statistiche cabina 1
        cursor.execute("SELECT COUNT(*) FROM optimization_colors WHERE cabin_id = 1")
        cabin1_total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM optimization_colors WHERE cabin_id = 1 AND in_execution = 1")
        cabin1_executing = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM optimization_colors WHERE cabin_id = 1 AND completed = 1")
        cabin1_completed = cursor.fetchone()[0]
        
        # Statistiche cabina 2
        cursor.execute("SELECT COUNT(*) FROM optimization_colors WHERE cabin_id = 2")
        cabin2_total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM optimization_colors WHERE cabin_id = 2 AND in_execution = 1")
        cabin2_executing = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM optimization_colors WHERE cabin_id = 2 AND completed = 1")
        cabin2_completed = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "cabin_1": {
                "total": cabin1_total,
                "executing": cabin1_executing,
                "completed": cabin1_completed
            },
            "cabin_2": {
                "total": cabin2_total,
                "executing": cabin2_executing,
                "completed": cabin2_completed
            }
        })
    except Exception as e:
        logger.error(f"Errore in api_cabin_status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin/<int:cabin_id>/colors')
def api_get_cabin_colors(cabin_id):
    """API per ottenere i colori di una cabina specifica."""
    try:
        if cabin_id not in [1, 2]:
            return jsonify({"error": "Cabina non valida"}), 400
        
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Connessione database fallita"}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, color_code, color_type, cluster, ch_value, lunghezza_ordine, 
                   input_sequence, sequence_type, completed, in_execution, sequence_order
            FROM optimization_colors 
            WHERE cabin_id = ? 
            ORDER BY sequence_order ASC, id ASC
        """, (cabin_id,))
        
        colors = []
        for row in cursor.fetchall():
            colors.append({
                "id": row[0],
                "color_code": row[1],
                "color_type": row[2],
                "cluster": row[3],
                "ch_value": row[4],
                "lunghezza_ordine": row[5],
                "input_sequence": row[6],
                "sequence_type": row[7],
                "completed": bool(row[8]),
                "in_execution": bool(row[9]),
                "sequence_order": row[10]
            })
        
        conn.close()
        return jsonify({"colors": colors})
    except Exception as e:
        logger.error(f"Errore in api_get_cabin_colors: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin/<int:cabin_id>/colors/<int:color_id>/execution', methods=['PUT'])
def api_update_color_execution(cabin_id, color_id):
    """API per aggiornare lo stato di esecuzione di un colore."""
    try:
        if cabin_id not in [1, 2]:
            return jsonify({"error": "Cabina non valida"}), 400
        
        data = request.get_json()
        if not data or 'in_execution' not in data:
            return jsonify({"error": "Parametro in_execution mancante"}), 400
        
        in_execution = bool(data['in_execution'])
        
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Connessione database fallita"}), 500
        
        cursor = conn.cursor()
        
        # Se sto impostando un colore come "in esecuzione"
        if in_execution:
            # Prima rimuovi lo stato "in esecuzione" da tutti gli altri colori della stessa cabina
            cursor.execute("""
                UPDATE optimization_colors 
                SET in_execution = 0 
                WHERE cabin_id = ? AND id != ?
            """, (cabin_id, color_id))
            
            # Poi imposta TUTTI i colori precedenti come completati
            cursor.execute("""
                SELECT sequence_order FROM optimization_colors 
                WHERE id = ? AND cabin_id = ?
            """, (color_id, cabin_id))
            current_row = cursor.fetchone()
            
            if current_row:
                current_order = current_row[0]
                # Marca come completati TUTTI i colori con sequence_order minore
                cursor.execute("""
                    UPDATE optimization_colors 
                    SET completed = 1
                    WHERE cabin_id = ? AND sequence_order < ? AND completed = 0
                """, (cabin_id, current_order))
                
                rows_affected = cursor.rowcount
                if rows_affected > 0:
                                                                                                                 logger.info(f"Segnati {rows_affected} colori precedenti come completati per cabina {cabin_id}")
                else:
                    logger.info(f"Nessun colore precedente da completare per cabina {cabin_id}")
        
        # Aggiorna lo stato del colore richiesto
        cursor.execute("""
            UPDATE optimization_colors 
            SET in_execution = ? 
            WHERE id = ? AND cabin_id = ?
        """, (in_execution, color_id, cabin_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Errore in api_update_color_execution: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin/<int:cabin_id>/colors/<int:color_id>', methods=['DELETE'])
def api_delete_color(cabin_id, color_id):
    """API per rimuovere un colore dalla cabina."""
    try:
        if cabin_id not in [1, 2]:
            return jsonify({"error": "Cabina non valida"}), 400
        
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Connessione database fallita"}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM optimization_colors 
            WHERE id = ? AND cabin_id = ?
        """, (color_id, cabin_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Colore non trovato"}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Errore in api_delete_color: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    """API per eseguire l'ottimizzazione dei colori."""
    try:
        data = request.get_json()
        if not data or 'colors_today' not in data:
            logger.error("Lista colori mancante nella richiesta")
            return jsonify({"error": "Lista colori mancante"}), 400
        
        # Valida i dati di input
        colors_today = data['colors_today']
        if not isinstance(colors_today, list) or len(colors_today) == 0:
            logger.error("colors_today deve essere un array non vuoto")
            return jsonify({"error": "colors_today deve essere un array non vuoto"}), 400
        
        # Valida ogni colore
        for i, color in enumerate(colors_today):
            if not isinstance(color, dict):
                logger.error(f"Colore {i} non è un oggetto valido")
                return jsonify({"error": f"Colore {i} non è un oggetto valido"}), 400
            
            if 'code' not in color or not color['code']:
                logger.error(f"Colore {i}: campo 'code' mancante o vuoto")
                return jsonify({"error": f"Colore {i}: campo 'code' è richiesto"}), 400
            
            if 'type' not in color or not color['type']:
                logger.error(f"Colore {i}: campo 'type' mancante o vuoto")
                return jsonify({"error": f"Colore {i}: campo 'type' è richiesto"}), 400
        
        # Prepara la richiesta per il backend
        backend_payload = {
            "colors_today": colors_today,
            "start_cluster_name": data.get('start_cluster_name'),
            "prioritized_reintegrations": data.get('prioritized_reintegrations', [])
        }
        
        logger.info(f"Invio richiesta al backend con {len(colors_today)} colori")
        logger.debug(f"Payload backend: {json.dumps(backend_payload, indent=2)}")
        
        # Chiama il backend API
        response = requests.post(
            OPTIMIZE_ENDPOINT,
            json=backend_payload,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        logger.info(f"Risposta backend: status={response.status_code}")
        
        if response.status_code != 200:
            error_detail = "Errore backend sconosciuto"
            try:
                error_data = response.json()
                error_detail = error_data.get('detail', error_detail)
                logger.error(f"Errore backend dettagliato: {error_data}")
            except Exception as e:
                logger.error(f"Impossibile parsare errore backend: {e}")
                error_detail = f"Errore backend HTTP {response.status_code}: {response.text[:500]}"
            return jsonify({"error": error_detail}), response.status_code
        
        backend_results = response.json()
        
        # Salva i risultati nel database
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Pulisci i dati esistenti
                cursor.execute("DELETE FROM optimization_colors")
                
                # Ottieni la lista dei reintegri prioritari
                prioritized_reintegrations = backend_payload.get('prioritized_reintegrations', [])
                
                if 'cabina_1' in backend_results and 'cabina_2' in backend_results:
                    # Risultati per cabine separate
                    if backend_results['cabina_1'].get('ordered_colors'):
                        save_colors_to_db_internal(cursor, backend_results['cabina_1']['ordered_colors'], 1, prioritized_reintegrations)
                    
                    if backend_results['cabina_2'].get('ordered_colors'):
                        save_colors_to_db_internal(cursor, backend_results['cabina_2']['ordered_colors'], 2, prioritized_reintegrations)
                else:
                    # Risultati standard - separa per lunghezza ordine
                    if backend_results.get('ordered_colors'):
                        for idx, color in enumerate(backend_results['ordered_colors']):
                            cabin_id = 2 if color.get('lunghezza_ordine') == 'lungo' else 1
                            save_color_to_db_internal_simple(cursor, color, idx, cabin_id)
                
                conn.commit()
            except Exception as e:
                logger.error(f"Errore durante il salvataggio: {e}")
            finally:
                conn.close()
        
        return jsonify(backend_results)
    except requests.RequestException as e:
        logger.error(f"Errore durante la chiamata al backend: {e}")
        return jsonify({"error": "Errore di comunicazione con il backend"}), 500
    except Exception as e:
        logger.error(f"Errore in api_optimize: {e}")
        return jsonify({"error": str(e)}), 500

def save_color_to_db_internal(cursor, color, cabin_id, position):
    """
    Funzione base per salvare un singolo colore nel database.
    """
    color_code = color.get('code', color.get('color_code', ''))
    
    cursor.execute("""
        INSERT INTO optimization_colors 
        (color_code, color_type, cluster, input_sequence, sequence_type, ch_value, lunghezza_ordine, 
         cabin_id, sequence_order, locked, position)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        color_code,
        color.get('type', ''),
        color.get('cluster', ''),
        color.get('sequence', 0),
        color.get('sequence_type', ''),
        color.get('CH', 0),
        color.get('lunghezza_ordine', 0),
        cabin_id,
        position,
        color.get('locked', False),
        color.get('position', position)
    ))

def save_colors_to_db_internal(cursor, colors_list, cabin_id, prioritized_reintegrations=None):
    """Helper function per salvare colori nel database."""
    for idx, color in enumerate(colors_list):
        save_color_to_db_internal_with_priority(cursor, color, idx, cabin_id, prioritized_reintegrations)

def save_color_to_db_internal_with_priority(cursor, color, sequence_order, cabin_id, prioritized_reintegrations=None):
    """Helper function per salvare un singolo colore nel database con supporto priorità."""
    color_code = color.get('code', color.get('color_code', ''))
    is_prioritized = 0
    
    # Controlla se il colore è tra i reintegri prioritari
    if prioritized_reintegrations and color_code in prioritized_reintegrations:
        is_prioritized = 1
        logger.info(f"Impostando colore {color_code} come prioritario nel database")
    
    cursor.execute('''
        INSERT INTO optimization_colors (
            color_code, color_type, cluster, ch_value, 
            lunghezza_ordine, input_sequence, sequence_type,
            cabin_id, sequence_order, locked, position
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        color_code,
        color.get('type', color.get('color_type', '')),
        color.get('cluster', ''),
        color.get('CH', color.get('ch_value')),
        color.get('lunghezza_ordine', ''),
        color.get('sequence', color.get('input_sequence')),
        color.get('sequence_type', ''),
        cabin_id,
        sequence_order,
        color.get('locked', False),
        color.get('position', sequence_order)
    ))

def save_color_to_db_internal_simple(cursor, color, position, cabin_id):
    """
    Versione semplificata per compatibilità.
    """
    save_color_to_db_internal(cursor, color, cabin_id, position)

@app.route('/api/clear-all', methods=['POST'])
def api_clear_all():
    """API per pulire tutti i dati delle cabine."""
    try:
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Connessione database fallita"}), 500
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM optimization_colors")
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Errore in api_clear_all: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin/<int:cabin_id>/optimize-partial', methods=['POST'])
def api_cabin_optimize_partial(cabin_id):
    """API per eseguire l'ottimizzazione parziale dei cluster per una cabina specifica."""
    try:
        if cabin_id not in [1, 2]:
            return jsonify({"error": "Cabina non valida"}), 400
            
        data = request.get_json()
        if not data:
            logger.error("Dati mancanti nella richiesta")
            return jsonify({"error": "Dati mancanti nella richiesta"}), 400
        
        # Valida i dati richiesti
        if 'colors' not in data:
            logger.error("Lista colori mancante nella richiesta")
            return jsonify({"error": "Lista colori mancante"}), 400
            
        if 'partial_cluster_order' not in data:
            logger.error("Ordine parziale cluster mancante nella richiesta")
            return jsonify({"error": "Ordine parziale cluster mancante nella richiesta"}), 400
        
        # Prepara la richiesta per il backend
        backend_payload = {
            "colors": data['colors'],
            "partial_cluster_order": data['partial_cluster_order'],
            "cabin_id": cabin_id,
            "prioritized_reintegrations": data.get('prioritized_reintegrations', [])
        }
        
        logger.info(f"Invio richiesta di ottimizzazione parziale al backend per cabina {cabin_id}")
        logger.debug(f"Payload backend: {json.dumps(backend_payload, indent=2)}")
        
        # Chiama il backend API
        backend_url = f"{BACKEND_URL}/optimize-partial"
        response = requests.post(
            backend_url,
            json=backend_payload,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        logger.info(f"Risposta backend optimize-partial: status={response.status_code}")
        
        if response.status_code != 200:
            error_detail = "Errore backend sconosciuto"
            try:
                error_data = response.json()
                error_detail = error_data.get('detail', error_detail)
                logger.error(f"Errore backend dettagliato: {error_data}")
            except Exception as e:
                logger.error(f"Impossibile parsare errore backend: {e}")
                error_detail = f"Errore backend HTTP {response.status_code}: {response.text[:500]}"
            return jsonify({"error": error_detail}), response.status_code
        
        backend_results = response.json()
        
        # Salva i risultati nel database (sovrascrive i colori della cabina specifica)
        conn = connect_to_db()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Rimuovi solo i colori della cabina specifica
                cursor.execute("DELETE FROM optimization_colors WHERE cabin_id = ?", (cabin_id,))
                
                # Salva i nuovi risultati
                if backend_results.get('ordered_colors'):
                    prioritized_reintegrations = backend_payload.get('prioritized_reintegrations', [])
                    save_colors_to_db_internal(cursor, backend_results['ordered_colors'], cabin_id, prioritized_reintegrations)
                
                conn.commit()
                logger.info(f"Risultati ottimizzazione parziale salvati per cabina {cabin_id}")
            except Exception as e:
                logger.error(f"Errore durante il salvataggio: {e}")
            finally:
                conn.close()
        
        return jsonify(backend_results)
    except requests.RequestException as e:
        logger.error(f"Errore durante la chiamata al backend optimize-partial: {e}")
        return jsonify({"error": "Errore di comunicazione con il backend"}), 500
    except Exception as e:
        logger.error(f"Errore in api_cabin_optimize_partial: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin/<int:cabin_id>/cluster_order')
def api_get_cabin_cluster_order(cabin_id):
    """API per ottenere l'ordine dei cluster di una cabina specifica."""
    try:
        if cabin_id not in [1, 2]:
            return jsonify({"error": "Cabina non valida"}), 400
        
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Connessione database fallita"}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT cluster, MIN(sequence_order) as min_order
            FROM optimization_colors 
            WHERE cabin_id = ? AND cluster IS NOT NULL
            GROUP BY cluster
            ORDER BY min_order ASC
        """, (cabin_id,))
        
        clusters = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({"order": clusters})
    except Exception as e:
        logger.error(f"Errore in api_get_cabin_cluster_order: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin/<int:cabin_id>/original_cluster_order')
def api_get_cabin_original_cluster_order(cabin_id):
    """API per ottenere l'ordine originale dei cluster di una cabina specifica."""
    try:
        if cabin_id not in [1, 2]:
            return jsonify({"error": "Cabina non valida"}), 400
        
        # Per l'ordine originale, usiamo l'ordine alfabetico dei cluster presenti
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Connessione database fallita"}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT cluster
            FROM optimization_colors 
            WHERE cabin_id = ? AND cluster IS NOT NULL
            ORDER BY cluster ASC
        """, (cabin_id,))
        
        clusters = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({"order": clusters})
    except Exception as e:
        logger.error(f"Errore in api_get_cabin_original_cluster_order: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin/<int:cabin_id>/colors/<int:color_index>/lock', methods=['PUT'])
def api_update_color_lock(cabin_id, color_index):
    """API per aggiornare lo stato di blocco di un singolo colore."""
    try:
        if cabin_id not in [1, 2]:
            return jsonify({"error": "Cabina non valida"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dati richiesti"}), 400
        
        locked = data.get('locked', False)
        
        # Lavora direttamente con il database locale
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Connessione database fallita"}), 500
        
        try:
            cursor = conn.cursor()
            
            # Verifica che il colore esista
            cursor.execute("""
                SELECT color_code FROM optimization_colors 
                WHERE cabin_id = ? AND sequence_order = ?
                ORDER BY id DESC LIMIT 1
            """, (cabin_id, color_index))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({"error": "Colore non trovato"}), 404
            
            color_code = result[0]
            
            # Aggiorna lo stato locked
            cursor.execute("""
                UPDATE optimization_colors 
                SET locked = ?
                WHERE cabin_id = ? AND sequence_order = ?
            """, (locked, cabin_id, color_index))
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Nessun colore aggiornato"}), 404
            
            conn.commit()
            
            action = "bloccato" if locked else "sbloccato"
            logger.info(f"Colore {color_code} {action} per cabina {cabin_id} posizione {color_index}")
            
            return jsonify({
                "success": True,
                "message": f"Colore {color_code} {action} con successo",
                "color_index": color_index,
                "locked": locked
            })
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Errore aggiornamento blocco colore: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Errore in api_update_color_lock: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin/<int:cabin_id>/cluster/<cluster_name>/lock', methods=['PUT'])
def api_update_cluster_lock(cabin_id, cluster_name):
    """API per aggiornare lo stato di blocco di tutti i colori di un cluster."""
    try:
        if cabin_id not in [1, 2]:
            return jsonify({"error": "Cabina non valida"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dati richiesti"}), 400
        
        locked = data.get('locked', False)
        
        # Chiama il backend per aggiornare il blocco del cluster
        backend_url = f"{BACKEND_URL}/update-cluster-lock"
        response = requests.post(
            backend_url,
            json={
                'cabin_id': cabin_id,
                'cluster_name': cluster_name,
                'locked': locked
            },
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            # Aggiorna anche il database locale se necessario
            conn = connect_to_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Aggiorna lo stato locked per tutti i colori del cluster
                    cursor.execute("""
                        UPDATE optimization_colors 
                        SET locked = ?
                        WHERE cabin_id = ? AND cluster = ?
                    """, (locked, cabin_id, cluster_name))
                    conn.commit()
                except Exception as e:
                    logger.error(f"Errore aggiornamento DB locale: {e}")
                finally:
                    conn.close()
            
            return jsonify(response.json())
        else:
            return jsonify({"error": "Errore backend"}), response.status_code
            
    except Exception as e:
        logger.error(f"Errore in api_update_cluster_lock: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin/<int:cabin_id>/colors/reorder', methods=['PUT'])
def api_reorder_colors(cabin_id):
    """API per riordinare i colori con drag & drop."""
    try:
        if cabin_id not in [1, 2]:
            return jsonify({"error": "Cabina non valida"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dati richiesti"}), 400
        
        new_order = data.get('new_order', [])
        
        if not new_order:
            return jsonify({"error": "new_order non può essere vuoto"}), 400
        
        # Lavora direttamente con il database locale
        conn = connect_to_db()
        if not conn:
            return jsonify({"error": "Connessione database fallita"}), 500
        
        try:
            cursor = conn.cursor()
            
            # Recupera tutti i colori attuali per questa cabina
            cursor.execute("""
                SELECT color_code, color_type, cluster, input_sequence, sequence_type, 
                       ch_value, lunghezza_ordine, locked, position, sequence_order
                FROM optimization_colors 
                WHERE cabin_id = ?
                ORDER BY sequence_order
            """, (cabin_id,))
            
            current_colors = cursor.fetchall()
            
            if len(current_colors) != len(new_order):
                return jsonify({"error": f"Lunghezza new_order ({len(new_order)}) non corrisponde al numero di colori ({len(current_colors)})"}), 400
            
            # Valida che tutti gli indici siano validi
            for index in new_order:
                if index < 0 or index >= len(current_colors):
                    return jsonify({"error": f"Indice non valido: {index}"}), 400
            
            # Elimina tutti i colori esistenti per questa cabina
            cursor.execute("DELETE FROM optimization_colors WHERE cabin_id = ?", (cabin_id,))
            
            # Reinserisci i colori nel nuovo ordine
            for new_pos, old_index in enumerate(new_order):
                color_data = current_colors[old_index]
                
                cursor.execute("""
                    INSERT INTO optimization_colors 
                    (color_code, color_type, cluster, input_sequence, sequence_type, ch_value, lunghezza_ordine, 
                     cabin_id, sequence_order, locked, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    color_data[0],  # color_code
                    color_data[1],  # color_type
                    color_data[2],  # cluster
                    color_data[3],  # input_sequence
                    color_data[4],  # sequence_type
                    color_data[5],  # ch_value
                    color_data[6],  # lunghezza_ordine
                    cabin_id,
                    new_pos,       # sequence_order (nuova posizione)
                    color_data[7],  # locked
                    new_pos        # position
                ))
            
            conn.commit()
            
            logger.info(f"Riordinati {len(new_order)} colori per cabina {cabin_id}")
            
            return jsonify({
                "success": True,
                "message": f"Riordinati {len(new_order)} colori per cabina {cabin_id}",
                "cabin_id": cabin_id,
                "colors_count": len(new_order)
            })
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Errore durante riordino colori: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Errore in api_reorder_colors: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cabin/<int:cabin_id>/optimize-locked', methods=['POST'])
def api_optimize_with_locked_colors(cabin_id):
    """API per ottimizzazione con colori bloccati individualmente."""
    try:
        if cabin_id not in [1, 2]:
            return jsonify({"error": "Cabina non valida"}), 400
        
        data = request.get_json()
        colors_today = data.get('colors_today', [])
        prioritized_reintegrations = data.get('prioritized_reintegrations', [])
        
        if not colors_today:
            return jsonify({"error": "Lista colori vuota"}), 400
        
        # Chiama il backend per ottimizzazione con colori bloccati
        backend_url = f"{BACKEND_URL}/optimize-locked-colors"
        response = requests.post(
            backend_url,
            json={
                'colors_today': colors_today,
                'cabin_id': cabin_id,
                'prioritized_reintegrations': prioritized_reintegrations
            },
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        if response.status_code == 200:
            backend_results = response.json()
            
            # Salva i risultati nel database locale
            conn = connect_to_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Rimuovi i colori esistenti per questa cabina
                    cursor.execute("DELETE FROM optimization_colors WHERE cabin_id = ?", (cabin_id,))
                    
                    # Salva i nuovi risultati
                    if backend_results.get('ordered_colors'):
                        # Merge dei locked tra lista originale e ottimizzata
                        merged_colors = merge_locked_colors(colors_today, backend_results['ordered_colors'])
                        save_colors_to_db_internal(cursor, merged_colors, cabin_id, prioritized_reintegrations)
                    
                    conn.commit()
                    logger.info(f"Risultati ottimizzazione con blocchi salvati per cabina {cabin_id}")
                except Exception as e:
                    logger.error(f"Errore durante il salvataggio: {e}")
                finally:
                    conn.close()
            
            return jsonify(backend_results)
        else:
            error_detail = "Errore backend sconosciuto"
            try:
                error_data = response.json()
                error_detail = error_data.get('detail', error_detail)
            except:
                pass
            return jsonify({"error": error_detail}), response.status_code
            
    except Exception as e:
        logger.error(f"Errore in api_optimize_with_locked_colors: {e}")
        return jsonify({"error": str(e)}), 500