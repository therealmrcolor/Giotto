# backend/app/logic.py
"""Core logic for color sequence optimization."""

import numpy as np
from functools import lru_cache
import itertools
from typing import List, Dict, Any, Optional, Tuple, Set
import json
import os
from pathlib import Path

# Importa configurazioni, funzioni DB e modelli
from app import config
from app import database
from app.models import ColorObject, ClusterDict, TransitionRuleDict

# Variabili globali per Held-Karp (devono essere accessibili dalla funzione ricorsiva)
# Vengono popolate dalla funzione principale `optimize_color_sequence`
_cost_matrix: Optional[np.ndarray] = None
_n_clusters: int = 0


def _safe_get_sequence(colore: ColorObject) -> int:
    """
    Estrae il valore di sequenza da un colore, convertendolo sempre a intero.
    Restituisce 0 se il valore è None, vuoto o non convertibile.
    """
    seq_value = colore.get('sequence')
    if seq_value is None:
        return 0
    try:
        return int(seq_value)
    except (ValueError, TypeError):
        return 0

def _get_cluster_sequence_priority(cluster_nome: str, colori_giorno: List[ColorObject]) -> int:
    """
    Calcola la priorità di sequenza di un cluster basata sul valore di sequenza minimo
    dei colori che contiene. Valori più bassi hanno priorità più alta.
    Restituisce il valore di sequenza minimo nel cluster, o 999 se non ci sono colori.
    """
    colori_del_cluster = [c for c in colori_giorno if c.get("cluster") == cluster_nome]
    if not colori_del_cluster:
        return 999  # Priorità più bassa per cluster senza colori
    
    # Trova il valore di sequenza minimo nel cluster
    sequenze = []
    for colore in colori_del_cluster:
        seq_int = _safe_get_sequence(colore)
        sequenze.append(seq_int)
    
    if sequenze:
        min_sequence = min(sequenze)
        return min_sequence
    else:
        return 999  # Nessuna sequenza valida trovata
        

# --- Funzioni Helper (simili a Cella 5 e 9 del notebook) ---

def _map_colors_to_clusters(colori_giorno: List[ColorObject], cluster_dict: ClusterDict) -> Tuple[Dict[str, str], List[str], Set[str]]:
    """
    Mappa i codici colore ai loro cluster, identifica cluster unici e urgenti.
    Restituisce (mappa colore->cluster, lista cluster_oggi ordinata, set cluster urgenti).
    (Logica da Cella 4)
    """
    colore2cluster: Dict[str, str] = {}
    for cluster, colori in cluster_dict.items():
        for c in colori:
            colore2cluster[c] = cluster

    clusters_presenti_oggi: Set[str] = set()
    clusters_urgenti: Set[str] = set()

    for c in colori_giorno:
        cluster_name = colore2cluster.get(c.get("code", ""), None)
        c["cluster"] = cluster_name # Aggiorna l'oggetto colore originale
        if cluster_name:
            clusters_presenti_oggi.add(cluster_name)
            # Considera 'R' o 'reintegro' come urgente
            if c.get("type", "").upper() in ["R", "REINTEGRO"]:
                clusters_urgenti.add(cluster_name)
        else:
             print(f"Attenzione: Colore {c.get('code')} non trovato in nessun cluster del DB.")


    clusters_oggi_list = sorted(list(clusters_presenti_oggi))
    return colore2cluster, clusters_oggi_list, clusters_urgenti

def _build_cost_matrix(clusters_oggi: List[str],
                       colori_giorno: List[ColorObject],
                       cambio_colori: TransitionRuleDict,
                       prioritized_reintegrations: Optional[List[str]] = None) -> np.ndarray: # NUOVO PARAMETRO
    """
    Costruisce la matrice dei costi di transizione tra i cluster.
    LOGICA:
    - Costo base = 'peso' della regola.
    - Vincoli 'transition_colors' e 'required_trigger_type' (tipo specifico)
      vengono verificati sulla DESTINAZIONE.
    - Se la DESTINAZIONE contiene Reintegri ('R'), viene applicato un BONUS.
    - Se la DESTINAZIONE contiene Reintegri PRIORITARI, viene applicato un BONUS MAGGIORE.
    """
    n = len(clusters_oggi)
    if n == 0:
        print("[MATRIX] Nessun cluster oggi, matrice vuota.")
        return np.array([[]])

    cost_matrix = np.full((n, n), config.INFINITE_COST, dtype=float)

    colori_per_cluster_oggi: Dict[str, List[ColorObject]] = {cl: [] for cl in clusters_oggi}
    for c in colori_giorno:
        cluster_key = c.get("cluster")
        if cluster_key in colori_per_cluster_oggi:
            colori_per_cluster_oggi[cluster_key].append(c)

    # --- Cache per sapere se un cluster di destinazione ha reintegri (standard, non urgenti e prioritari) ---
    destinazione_ha_reintegri_standard: Dict[str, bool] = {}
    destinazione_ha_reintegri_non_urgenti: Dict[str, bool] = {}
    destinazione_ha_reintegri_prioritari: Dict[str, bool] = {}

    # Crea un set dei codici dei reintegri prioritari per ricerche veloci
    prioritized_reintegrations_set = set(prioritized_reintegrations or [])

    print("[MATRIX] Pre-calcolo presenza Reintegri (standard, non urgenti e prioritari) nei cluster di destinazione...")
    for cj_nome in clusters_oggi:
        colori_in_cj = colori_per_cluster_oggi.get(cj_nome, [])
        ha_r_standard = False
        ha_re_non_urgente = False
        ha_r_prioritario = False
        for colore_in_cj in colori_in_cj:
            color_type = colore_in_cj.get("type", "").upper()
            if color_type == "R":
                ha_r_standard = True # Trovato almeno un reintegro urgente standard
                if colore_in_cj.get("code") in prioritized_reintegrations_set:
                    ha_r_prioritario = True # Trovato anche un prioritario
            elif color_type == "RE":
                ha_re_non_urgente = True # Trovato almeno un reintegro non urgente
        
        destinazione_ha_reintegri_standard[cj_nome] = ha_r_standard
        destinazione_ha_reintegri_non_urgenti[cj_nome] = ha_re_non_urgente
        destinazione_ha_reintegri_prioritari[cj_nome] = ha_r_prioritario

        log_msg = f"[MATRIX]   -> Cluster '{cj_nome}': "
        if ha_r_prioritario:
            log_msg += "CONTIENE Reintegri PRIORITARI."
        elif ha_r_standard:
            log_msg += "CONTIENE Reintegri urgenti STANDARD."
        elif ha_re_non_urgente:
            log_msg += "CONTIENE Reintegri NON URGENTI."
        else:
            log_msg += "NON contiene Reintegri."
        print(log_msg)


    print(f"\n[MATRIX] Inizio costruzione matrice costi (Bonus Reintegro Dest. & Prioritari) per {n} cluster...")

    for i, ci in enumerate(clusters_oggi): # Cluster sorgente (indice i)
        for j, cj in enumerate(clusters_oggi): # Cluster destinazione (indice j)

            # ... (stampa Valutando transizione, gestione stesso cluster - NESSUNA MODIFICA QUI) ...
            print(f"\n[MATRIX] Valutando transizione: {ci} ({i}) -> {cj} ({j})")

            if i == j:
                cost_matrix[i, j] = config.SAME_CLUSTER_COST
                print(f"[MATRIX]   Stesso cluster: Costo = {config.SAME_CLUSTER_COST}")
                continue
            
            # --- A. Ottieni Regola e Costo Base --- (NESSUNA MODIFICA QUI)
            key = (ci, cj)
            regola = cambio_colori.get(key, {})
            costo_base_transizione = float(regola.get('peso', config.DEFAULT_TRANSITION_COST))

            # --- B. Definisci Vincoli sulla Destinazione 'cj' --- (NESSUNA MODIFICA QUI)
            colori_richiesti_dest_raw = regola.get('colors', [])
            colori_richiesti_dest_set = set(c for c in colori_richiesti_dest_raw if isinstance(c, str) and c.upper() != 'VIETATO')
            required_type_raw = regola.get('required_type')
            tipo_specifico_richiesto_dest = None
            if isinstance(required_type_raw, str) and required_type_raw.strip() and required_type_raw.upper() != 'ALLOW_E':
                  cleaned_type = required_type_raw.strip()
                  if len(cleaned_type) > 1 and cleaned_type.startswith("'") and cleaned_type.endswith("'"):
                      tipo_specifico_richiesto_dest = cleaned_type[1:-1].upper()
                  else:
                      tipo_specifico_richiesto_dest = cleaned_type.upper()
            print(f"[MATRIX]   Regola DB: PesoBase={costo_base_transizione:.0f}, RichiestiColoriDest={colori_richiesti_dest_set or 'Nessuno'}, RichiestoTipoDest='{tipo_specifico_richiesto_dest or 'Nessuno'}'")

            # --- C. Verifica Vincoli sulla Destinazione 'cj' --- (NESSUNA MODIFICA QUI)
            vincolo_colori_dest_ok = True 
            vincolo_tipo_dest_ok = True   
            costo_finale = config.INFINITE_COST 
            colori_destinazione_oggi = colori_per_cluster_oggi.get(cj, [])
            if not colori_destinazione_oggi:
                 print(f"[MATRIX]     ATTENZIONE: Cluster destinazione '{cj}' è vuoto oggi.")
                 if colori_richiesti_dest_set: vincolo_colori_dest_ok = False
                 if tipo_specifico_richiesto_dest: vincolo_tipo_dest_ok = False
            else:
                 colori_destinazione_oggi_codes = {c['code'] for c in colori_destinazione_oggi}
                 colori_destinazione_oggi_types = {c.get("type", "N/A").upper() for c in colori_destinazione_oggi}
                 if colori_richiesti_dest_set:
                      # ... (logica verifica colori specifici - NESSUNA MODIFICA QUI) ...
                      print(f"[MATRIX]     Verifico Vincolo Colori Specifici su Destinazione '{cj}'...")
                      # ...
                      if not colori_richiesti_dest_set.intersection(colori_destinazione_oggi_codes):
                          vincolo_colori_dest_ok = False
                          print(f"[MATRIX]       --> Vincolo Colori Specifici FALLITO.")
                      else:
                           print(f"[MATRIX]       Vincolo Colori Specifici OK.")
                 else:
                       print(f"[MATRIX]     Nessun Vincolo Colori Specifici sulla destinazione.")

                 if vincolo_colori_dest_ok and tipo_specifico_richiesto_dest:
                      # ... (logica verifica tipo specifico - NESSUNA MODIFICA QUI) ...
                      print(f"[MATRIX]     Verifico Vincolo Tipo Specifico ('{tipo_specifico_richiesto_dest}') su Destinazione '{cj}'...")
                      # ...
                      if tipo_specifico_richiesto_dest not in colori_destinazione_oggi_types:
                          vincolo_tipo_dest_ok = False
                          print(f"[MATRIX]       --> Vincolo Tipo Specifico FALLITO.")
                      else:
                           print(f"[MATRIX]       Vincolo Tipo Specifico OK.")
                 elif vincolo_colori_dest_ok:
                      print(f"[MATRIX]     Nessun Vincolo Tipo Specifico sulla destinazione (o vincolo colori già fallito).")

            # --- D. Calcolo Costo Finale con Bonus --- (MODIFICATO QUI)
            if vincolo_colori_dest_ok and vincolo_tipo_dest_ok:
                 costo_finale = costo_base_transizione # Inizia con il peso della regola

                 # Applica il bonus appropriato (in ordine di priorità)
                 if destinazione_ha_reintegri_prioritari.get(cj, False):
                     bonus_applicato = config.BONUS_REINTEGRO_PRIORITARIO
                     tipo_bonus_log = "PRIORITARIO"
                 elif destinazione_ha_reintegri_standard.get(cj, False):
                     bonus_applicato = config.BONUS_REINTEGRO_DESTINAZIONE
                     tipo_bonus_log = "Urgente Standard"
                 elif destinazione_ha_reintegri_non_urgenti.get(cj, False):
                     bonus_applicato = config.BONUS_REINTEGRO_NON_URGENTE_DESTINAZIONE
                     tipo_bonus_log = "Non Urgente"
                 else:
                     bonus_applicato = 0 # Nessun bonus reintegro
                     tipo_bonus_log = "Nessuno"

                 if bonus_applicato != 0:
                     print(f"[MATRIX]     Applicando Bonus Reintegro {tipo_bonus_log} ({bonus_applicato}) a Destinazione '{cj}'.")
                     costo_finale += bonus_applicato
                     costo_finale = max(1.0, costo_finale) # Assicura costo minimo
                     print(f"[MATRIX]       Costo dopo bonus: {costo_finale:.0f}")
                 
                 # --- E. Applica Prioritizzazione per Sequenza ---
                 # Calcola priorità di sequenza per i cluster source e destination
                 source_seq_priority = _get_cluster_sequence_priority(ci, colori_giorno)
                 dest_seq_priority = _get_cluster_sequence_priority(cj, colori_giorno)
                 
                 # Applica bonus/penalità basato sulla differenza di priorità
                 sequence_diff = abs(source_seq_priority - dest_seq_priority)
                 
                 if sequence_diff >= config.SEQUENCE_PRIORITY_THRESHOLD:
                     if dest_seq_priority < source_seq_priority:
                         # Destinazione ha priorità più alta (sequenza più bassa) -> BONUS
                         sequence_adjustment = config.BONUS_SEQUENCE_PRIORITY
                         adjustment_type = "BONUS (priorità alta dest.)"
                     elif dest_seq_priority > source_seq_priority:
                         # Destinazione ha priorità più bassa (sequenza più alta) -> PENALITÀ  
                         sequence_adjustment = config.PENALTY_SEQUENCE_PRIORITY
                         adjustment_type = "PENALITÀ (priorità bassa dest.)"
                     else:
                         sequence_adjustment = 0
                         adjustment_type = "Nessuno (stessa priorità)"
                     
                     if sequence_adjustment != 0:
                         print(f"[MATRIX]     Applicando Aggiustamento Sequenza {adjustment_type} ({sequence_adjustment}) - Source seq: {source_seq_priority}, Dest seq: {dest_seq_priority}")
                         costo_finale += sequence_adjustment
                         costo_finale = max(1.0, costo_finale) # Assicura costo minimo
                         print(f"[MATRIX]       Costo dopo aggiustamento sequenza: {costo_finale:.0f}")
                 
                 print(f"[MATRIX]   --> SUCCESSO: Vincoli Destinazione OK. Costo Finale Calcolato = {costo_finale:.0f}")
                 cost_matrix[i, j] = costo_finale
            else:
                 # Gestione speciale per tipo "F" non soddisfatto
                 if (not vincolo_tipo_dest_ok and tipo_specifico_richiesto_dest == "F" and vincolo_colori_dest_ok):
                     # Per tipo "F" non soddisfatto, applica penalità invece di costo infinito
                     costo_finale = costo_base_transizione + config.PENALTY_UNSATISFIED_F_TYPE
                     print(f"[MATRIX]   --> TIPO F NON SODDISFATTO: Applico penalità {config.PENALTY_UNSATISFIED_F_TYPE}. Costo Finale = {costo_finale:.0f}")
                     cost_matrix[i, j] = costo_finale
                 else:
                     print(f"[MATRIX]   --> FALLITO: Almeno un vincolo sulla destinazione non soddisfatto. Costo Finale = Infinito")
                     # cost_matrix[i, j] rimane config.INFINITE_COST

    # ... (stampa matrice finale - NESSUNA MODIFICA QUI) ...
    print("\n[MATRIX] Matrice dei costi finale costruita (Bonus Reintegro Dest. & Prioritari):")
    # ...
    return cost_matrix



# --- Algoritmo Held-Karp (Cella 6, 7) ---
# La cache è fondamentale qui!
@lru_cache(maxsize=None)
def _held_karp(mask: int, last: int, fixed_start_node: Optional[int] = None) -> float:
    """Funzione ricorsiva Held-Karp."""
    global _cost_matrix, _n_clusters # Usa le variabili globali popolate

    if _cost_matrix is None or _n_clusters == 0:
        return config.INFINITE_COST

    # Caso base MODIFICATO
    if fixed_start_node is not None:
        # If a start node is fixed, the path must originate from it.
        # A path consisting of a single node 'last' can only have cost 0 if 'last' is the fixed_start_node.
        if mask == (1 << last): # mask contains only 'last'
            return 0.0 if last == fixed_start_node else config.INFINITE_COST
    else: # Original behavior when no start node is fixed
        if mask == (1 << last): # mask contains only 'last'
            # This implies 'last' is the starting point of this subpath.
            return 0.0

    prev_mask = mask ^ (1 << last)
    min_cost = config.INFINITE_COST

    for k in range(_n_clusters):
        if prev_mask & (1 << k): # Se k era nel percorso precedente
             if 0 <= k < _n_clusters and 0 <= last < _n_clusters:
                transition_cost = _cost_matrix[k, last]
                if transition_cost >= config.INFINITE_COST:
                     continue
                
                # Recursive call MODIFIED
                cost_via_k = _held_karp(prev_mask, k, fixed_start_node)

                if cost_via_k >= config.INFINITE_COST:
                    continue

                current_total_cost = cost_via_k + transition_cost
                if current_total_cost < min_cost:
                    min_cost = current_total_cost
             else:
                  print(f"Errore indice in Held-Karp: k={k}, last={last}, n={_n_clusters}")
    return min_cost


def _reconstruct_tour(end_node: int, num_nodes: int, full_mask_val: int, fixed_start_node: Optional[int] = None) -> List[int]:
    """Ricostruisce il percorso ottimale (lista di indici)."""
    global _cost_matrix

    print(f"[RECONSTRUCT] Avvio ricostruzione tour per {num_nodes} nodi, terminante in {end_node}" + (f" (start fisso: {fixed_start_node})" if fixed_start_node is not None else ""))
    if num_nodes == 0: return []
    if num_nodes == 1:
        # If fixed_start_node is specified, it must be node 0. Otherwise, any single node is [0].
        return [0] if fixed_start_node is None or fixed_start_node == 0 else []

    if _cost_matrix is None:
        print("[RECONSTRUCT] Errore: Matrice costi non disponibile.")
        return []

    last = end_node
    mask = full_mask_val
    tour = [last]
    visited_indices_in_tour = {last}

    for step in range(num_nodes - 1):
        print(f"[RECONSTRUCT]   Passo {step+1}/{num_nodes-1}: Cerco predecessore di {last} (maschera attuale: {bin(mask)})")
        prev_mask = mask ^ (1 << last)
        candidates = []
        for k in range(num_nodes):
            if prev_mask & (1 << k):
                if 0 <= k < num_nodes and 0 <= last < num_nodes:
                    # Call to _held_karp MODIFIED
                    cost_to_k = _held_karp(prev_mask, k, fixed_start_node)
                    transition_cost = _cost_matrix[k, last]

                    if cost_to_k < config.INFINITE_COST and transition_cost < config.INFINITE_COST:
                        total_cost_via_k = cost_to_k + transition_cost
                        candidates.append((total_cost_via_k, k))
                    else:
                        print(f"[RECONSTRUCT]     Candidato {k} scartato (cost_to_k={cost_to_k}, transition={transition_cost})")
                else:
                     print(f"[RECONSTRUCT] Errore indice in ricostruzione: k={k}, last={last}")

        if not candidates:
             print(f"[RECONSTRUCT] --> ERRORE: Impossibile trovare predecessore valido per nodo {last} (maschera {bin(mask)})!")
             print(f"[RECONSTRUCT] Tour parziale trovato finora: {list(reversed(tour))}")
             break

        min_cost_step, prev_node_idx = min(candidates, key=lambda x: x[0])
        print(f"[RECONSTRUCT]   -> Predecessore scelto per {last}: {prev_node_idx} (con costo passo {min_cost_step:.1f})")

        if prev_node_idx in visited_indices_in_tour:
             print(f"[RECONSTRUCT] --> ATTENZIONE: Indice {prev_node_idx} già presente nel tour parziale {list(reversed(tour))}! Possibile ciclo errato.")

        tour.append(prev_node_idx)
        visited_indices_in_tour.add(prev_node_idx)
        mask = prev_mask
        last = prev_node_idx

    tour.reverse()
    print(f"[RECONSTRUCT] Tour ricostruito (indici): {tour}")
    if len(tour) != num_nodes:
         print(f"[RECONSTRUCT] --> ATTENZIONE: Lunghezza tour finale {len(tour)} diversa da {num_nodes}!")
    
    # Ensure the reconstructed tour starts with fixed_start_node if specified
    if fixed_start_node is not None and num_nodes > 0:
        if not tour or tour[0] != fixed_start_node:
            # This might happen if the path reconstruction logic coupled with fixed_start_node in _held_karp
            # doesn't naturally lead to it. This situation implies an issue or an impossible path.
            # However, for an open path, any node can be the first if fixed_start_node is None.
            # If fixed_start_node is set, the _held_karp logic should ensure paths originate from it.
            # If reconstruction doesn't yield this, it's a deeper issue or no such path exists.
            print(f"[RECONSTRUCT] ATTENZIONE: Tour ricostruito {tour} non inizia con il fixed_start_node {fixed_start_node}. Potrebbe essere un percorso non valido.")
            # For now, we proceed, _find_best_path_and_reconstruct will check validity.

    return tour


def _find_best_path_and_reconstruct(num_nodes: int, start_node_index: Optional[int] = None) -> List[Tuple[float, List[int]]]:
    """
    Trova i TOP_N_RESULTS percorsi aperti ottimali usando Held-Karp e li ricostruisce.
    Se start_node_index è fornito, forza l'inizio da lì.
    Restituisce una lista di tuple (costo_minimo, lista_indici_percorso), ordinata per costo.
    """
    global _cost_matrix, _n_clusters
    _held_karp.cache_clear() # Clear cache for each call to this overarching function.

    TOP_N_RESULTS = 3

    if num_nodes == 0 or _cost_matrix is None or _cost_matrix.size == 0:
        return []
    if num_nodes == 1:
        if start_node_index is not None and start_node_index != 0:
            print(f"[HELD-KARP] Single node path requested to start at {start_node_index} but only node 0 exists.")
            return [] # Invalid request for fixed start
        return [(0.0, [0])] # Costo 0 per un solo nodo

    full_mask = (1 << num_nodes) - 1
    
    all_potential_paths: List[Tuple[float, int, Optional[List[int]]]] = [] # (cost, end_node, optional_reconstructed_tour)

    if start_node_index is not None and 0 <= start_node_index < num_nodes:
        print(f"[HELD-KARP] Calcolo TOP {TOP_N_RESULTS} percorsi forzati inizio da indice {start_node_index}")
        
        calculated_paths_for_fixed_start: List[Tuple[float, int]] = [] # (cost_S_to_E, end_node)
        for end_node in range(num_nodes):
            print(f"[HELD-KARP]   Calcolo costo S={start_node_index} -> ... -> E={end_node}...")
            cost_S_to_E = _held_karp(full_mask, end_node, start_node_index)
            print(f"[HELD-KARP]     Costo S={start_node_index} -> ... -> E={end_node} (visitando tutti): {cost_S_to_E}")
            if cost_S_to_E < config.INFINITE_COST:
                 calculated_paths_for_fixed_start.append((cost_S_to_E, end_node))

        if not calculated_paths_for_fixed_start:
            print(f"[HELD-KARP] Errore: nessun percorso valido trovato partendo da nodo fisso {start_node_index}.")
            return []

        # Sort by cost to get the best ending nodes
        calculated_paths_for_fixed_start.sort(key=lambda x: x[0])
        
        for cost, end_node_for_path in calculated_paths_for_fixed_start:
            # We store cost and end_node here; reconstruction happens later if it's in top N
            all_potential_paths.append((cost, end_node_for_path, None))

    else: # Caso: Start node non è fisso
        print(f"[HELD-KARP] Calcolo TOP {TOP_N_RESULTS} percorsi ottimali senza nodo iniziale fisso.")
        calculated_paths_no_fixed_start: List[Tuple[float, int]] = [] # (cost_to_end, end_node)
        for end_node in range(num_nodes):
            print(f"[HELD-KARP]   Calcolo costo per finire in {end_node}...")
            cost_to_end = _held_karp(full_mask, end_node, None)
            print(f"[HELD-KARP]     Costo per finire in {end_node} (visitando tutti): {cost_to_end}")
            if cost_to_end < config.INFINITE_COST:
                 calculated_paths_no_fixed_start.append((cost_to_end, end_node))
        
        if not calculated_paths_no_fixed_start:
            print("[HELD-KARP] Errore: nessun percorso valido trovato (senza nodo iniziale fisso).")
            return []

        calculated_paths_no_fixed_start.sort(key=lambda x: x[0])
        for cost, end_node_for_path in calculated_paths_no_fixed_start:
            all_potential_paths.append((cost, end_node_for_path, None))

    # Sort all collected potential paths by cost
    all_potential_paths.sort(key=lambda x: x[0])
    
    top_results: List[Tuple[float, List[int]]] = []

    print(f"--- [HELD-KARP] Ricostruzione per i TOP {TOP_N_RESULTS} (o meno se non disponibili) ---")
    processed_tours_set = set() # To avoid duplicate tours if costs are identical

    for i, (cost, end_node, _) in enumerate(all_potential_paths):
        if len(top_results) >= TOP_N_RESULTS:
            break # Abbiamo abbastanza risultati

        print(f"  Tentativo {i+1}: Ricostruzione per percorso con costo {cost:.2f}, finente in {end_node}" + (f", S={start_node_index}" if start_node_index is not None else ""))
        
        current_tour_indices = _reconstruct_tour(end_node, num_nodes, full_mask, start_node_index)

        valid_tour = True
        if not current_tour_indices or len(current_tour_indices) != num_nodes:
            print(f"    [HELD-KARP] Errore ricostruzione o lunghezza tour errata ({len(current_tour_indices)} vs {num_nodes}). Tour: {current_tour_indices}. Scartato.")
            valid_tour = False
        
        if valid_tour and start_node_index is not None and (not current_tour_indices or current_tour_indices[0] != start_node_index):
            print(f"    [HELD-KARP] ATTENZIONE: Tour fisso ricostruito {current_tour_indices} non inizia con {start_node_index}. Scartato.")
            valid_tour = False

        if valid_tour:
            tour_tuple = tuple(current_tour_indices) # Use tuple for set operations
            if tour_tuple not in processed_tours_set:
                print(f"    [HELD-KARP] Percorso valido ({cost:.2f}): {current_tour_indices}. Aggiunto ai top.")
                top_results.append((cost, current_tour_indices))
                processed_tours_set.add(tour_tuple)
            else:
                print(f"    [HELD-KARP] Percorso valido ({cost:.2f}): {current_tour_indices}. MA DUPLICATO. Scartato.")
        
    if not top_results:
        print("[HELD-KARP] Nessun percorso valido trovato dopo ricostruzione per TOP N.")
        return []
        
    print(f"--- [HELD-KARP] TOP {len(top_results)} percorsi trovati ---")
    for idx, (p_cost, p_indices) in enumerate(top_results):
        print(f"  {idx+1}. Costo: {p_cost:.2f}, Percorso: {p_indices}")
    print("------------------------------------")
    return top_results


def _generate_final_ordered_list(tour_clusters: List[str],
                                 colori_giorno: List[ColorObject],
                                 first_color: Optional[str] = None) -> List[ColorObject]:
    """Ordina i colori seguendo il tour dei cluster e le priorità interne."""
    colori_ordinati: List[ColorObject] = []
    colori_usati_keys: Set[str] = set() # Per tracciare i colori già aggiunti (code+type)

    print("\nGenerazione lista colori ordinata finale...")
    # LOG: Stato colori_giorno in ingresso a questa funzione
    print(f"[ORDERED_LIST] Ricevuti {len(colori_giorno)} colori per ordinamento. Codici: {[c.get('code') + ' ' + str(c.get('type')) for c in colori_giorno]}")
    
    # Gestione first_color se specificato
    first_color_obj = None
    first_color_cluster = None
    if first_color:
        print(f"[FIRST_COLOR] Primo colore specificato: {first_color}")
        print(f"[FIRST_COLOR] DEBUG: first_color type: {type(first_color)}, repr: {repr(first_color)}")
        print(f"[FIRST_COLOR] first_color dopo strip: '{first_color.strip()}'" if isinstance(first_color, str) else f"[FIRST_COLOR] first_color non è stringa: {type(first_color)}")
        
        print(f"[FIRST_COLOR] Tutti i colori disponibili ({len(colori_giorno)} totali):")
        for i, c in enumerate(colori_giorno):
            code = c.get('code', '')
            print(f"  {i}: code='{code}' (type: {type(code)}), cluster='{c.get('cluster')}'")
        
        # Trova il colore nella lista - prova sia con che senza strip
        search_variations = [first_color]
        if isinstance(first_color, str):
            stripped = first_color.strip()
            if stripped != first_color:
                search_variations.append(stripped)
                print(f"[FIRST_COLOR] Aggiunta variazione con strip: '{stripped}'")
        
        for variation in search_variations:
            print(f"[FIRST_COLOR] Cerco variazione: '{variation}'")
            for c in colori_giorno:
                color_code = c.get('code', '')
                if color_code == variation:
                    first_color_obj = c
                    first_color_cluster = c.get('cluster')
                    print(f"[FIRST_COLOR] ✓ Trovato colore {variation} nel cluster {first_color_cluster}")
                    break
            if first_color_obj:
                break
        
        if not first_color_obj:
            print(f"[FIRST_COLOR] ❌ ATTENZIONE: Colore {first_color} non trovato nella lista colori!")
            print(f"[FIRST_COLOR] Confronti dettagliati effettuati:")
            for i, c in enumerate(colori_giorno):
                code = c.get('code', '')
                for variation in search_variations:
                    result = code == variation
                    print(f"  {i}: '{code}' == '{variation}' ? {result} (len: {len(code)} vs {len(variation)})")
                    if not result and len(code) == len(variation):
                        # Confronto carattere per carattere
                        for j, (c1, c2) in enumerate(zip(code, variation)):
                            if c1 != c2:
                                print(f"    Differenza alla posizione {j}: '{c1}' != '{c2}' (ord: {ord(c1)} vs {ord(c2)})")
        elif first_color_cluster and first_color_cluster in tour_clusters:
            # Riordina tour_clusters per mettere il cluster del primo colore all'inizio
            new_tour = [first_color_cluster] + [c for c in tour_clusters if c != first_color_cluster]
            print(f"[FIRST_COLOR] ✓ Tour cluster riordinato: {tour_clusters} -> {new_tour}")
            tour_clusters = new_tour
        else:
            print(f"[FIRST_COLOR] ❌ ATTENZIONE: Cluster {first_color_cluster} non trovato nel tour: {tour_clusters}")
    else:
        print(f"[FIRST_COLOR] Nessun primo colore specificato (first_color={repr(first_color)})")
    
    for cluster_nome in tour_clusters:
        print(f"  Processo cluster: {cluster_nome}")
        colori_del_cluster = [c for c in colori_giorno if c.get("cluster") == cluster_nome and f"{c.get('code')}_{c.get('type')}" not in colori_usati_keys]

        if not colori_del_cluster:
            print(f"    Nessun colore nuovo per questo cluster.")
            continue

        # Gestione first_color se il cluster corrente contiene il primo colore specificato
        first_color_in_cluster = None
        if first_color and first_color_obj and cluster_nome == first_color_cluster:
            print(f"    [FIRST_COLOR] ✓ Processando cluster {cluster_nome} che contiene il primo colore {first_color}")
            # Trova il primo colore in questo cluster
            for c in colori_del_cluster:
                if c.get('code') == first_color:
                    first_color_in_cluster = c
                    print(f"    [FIRST_COLOR] ✓ Trovato {first_color} in questo cluster")
                    break
            
            if not first_color_in_cluster:
                print(f"    [FIRST_COLOR] ❌ ERRORE: {first_color} non trovato nei colori del cluster {cluster_nome}")
                print(f"    [FIRST_COLOR]   colori_del_cluster: {[c.get('code') for c in colori_del_cluster]}")
        elif first_color and cluster_nome == first_color_cluster:
            print(f"    [FIRST_COLOR] ❌ ERRORE: Cluster {cluster_nome} dovrebbe contenere {first_color} ma first_color_obj è None")
        elif first_color:
            print(f"    [FIRST_COLOR] Cluster {cluster_nome} non contiene il primo colore {first_color} (first_color_cluster={first_color_cluster})")

        # NUOVA REGOLA INTRA-CLUSTER: Raggruppa per stesso codice RAL/codice
        print(f"    Applicazione regola raggruppamento per stesso codice...")
        cluster_ordinato_temp = []
        added_keys_this_cluster = set()
        
        # PRIMA PRIORITÀ: Se c'è un first_color in questo cluster, inizia con quello
        if first_color_in_cluster:
            cluster_ordinato_temp.append(first_color_in_cluster)
            added_keys_this_cluster.add(f"{first_color_in_cluster['code']}_{first_color_in_cluster['type']}")
            print(f"    + [FIRST_COLOR] PRIORITÀ ASSOLUTA: {first_color_in_cluster['code']} {first_color_in_cluster['type']}")
            
            # Aggiungi subito tutti gli altri tipi dello stesso codice del first_color
            first_color_code = first_color_in_cluster.get('code')
            altri_tipi_first_color = [c for c in colori_del_cluster 
                                    if c.get('code') == first_color_code and c != first_color_in_cluster]
            if altri_tipi_first_color:
                altri_tipi_first_color.sort(key=lambda x: (
                    0 if x.get('type') == 'F' else
                    1 if x.get('type') == 'R' else
                    2 if x.get('type') == 'K' else
                    3 if x.get('type') not in ['E'] else 4,
                    _safe_get_sequence(x)
                ))
                for colore_stesso_codice in altri_tipi_first_color:
                    key = f"{colore_stesso_codice['code']}_{colore_stesso_codice['type']}"
                    if key not in added_keys_this_cluster:
                        cluster_ordinato_temp.append(colore_stesso_codice)
                        added_keys_this_cluster.add(key)
                        print(f"    + [FIRST_COLOR] Stesso codice: {colore_stesso_codice['code']} {colore_stesso_codice['type']}")
        
        # Ora continua con la logica normale per i colori rimanenti
        
        # Raggruppa i colori per codice (RAL o numerico) - solo quelli non ancora processati
        colori_per_codice: Dict[str, List[ColorObject]] = {}
        for c in colori_del_cluster:
            key = f"{c.get('code')}_{c.get('type')}"
            if key not in added_keys_this_cluster:  # Solo colori non ancora aggiunti
                code = c.get('code', '')
                if code not in colori_per_codice:
                    colori_per_codice[code] = []
                colori_per_codice[code].append(c)
        
        print(f"    Trovati {len(colori_per_codice)} codici distinti rimanenti: {list(colori_per_codice.keys())}")

        # Separa per tipo e ordina considerando sequence_type per le sequenze piccole - solo colori non ancora processati
        colori_rimanenti = [c for c in colori_del_cluster if f"{c.get('code')}_{c.get('type')}" not in added_keys_this_cluster]
        fissi = sorted([c for c in colori_rimanenti if c.get("type") == "F"], 
                      key=lambda x: (_safe_get_sequence(x), 
                                   0 if x.get('sequence_type') == config.SEQUENCE_TYPE_SMALL else 1))
        kit = sorted([c for c in colori_rimanenti if c.get("type") == "K"], 
                    key=lambda x: (_safe_get_sequence(x), 
                                 0 if x.get('sequence_type') == config.SEQUENCE_TYPE_SMALL else 1))
        reintegri = sorted([c for c in colori_rimanenti if c.get("type") == "R"], 
                          key=lambda x: (_safe_get_sequence(x), 
                                       0 if x.get('sequence_type') == config.SEQUENCE_TYPE_SMALL else 1))
        altri_non_estetici = sorted([c for c in colori_rimanenti if c.get("type") not in ["F", "K", "R", "E"]], 
                                   key=lambda x: (config.TIPOLOGIA_PESO.get(x.get("type", "E"), 100), 
                                                _safe_get_sequence(x), 
                                                0 if x.get('sequence_type') == config.SEQUENCE_TYPE_SMALL else 1))
        estetici = sorted([c for c in colori_rimanenti if c.get("type") == "E"], 
                         key=lambda x: (_safe_get_sequence(x), 
                                      0 if x.get('sequence_type') == config.SEQUENCE_TYPE_SMALL else 1))

        # Logica di ordinamento con raggruppamento per stesso codice:
        # 1. Prendi un fisso come trigger (se presente)
        # 2. Se del fisso scelto ci sono altri tipi (E, K, R), li raggruppi subito dopo
        # 3. Poi continui con reintegri, altri non-E, estetici rimanenti

        # 1. Aggiungi UN SOLO pezzo Fisso (il primo) + eventuali altri tipi dello stesso codice
        primo_fisso_code = None
        if fissi:
            primo_fisso = fissi.pop(0) # Prendi e rimuovi il primo
            primo_fisso_code = primo_fisso.get('code')
            cluster_ordinato_temp.append(primo_fisso)
            added_keys_this_cluster.add(f"{primo_fisso['code']}_{primo_fisso['type']}")
            print(f"    + Fisso (trigger): {primo_fisso['code']}")
            
            # NUOVA LOGICA: Aggiungi subito tutti gli altri tipi dello stesso codice del fisso
            if primo_fisso_code and primo_fisso_code in colori_per_codice:
                altri_tipi_stesso_codice = [c for c in colori_per_codice[primo_fisso_code] 
                                          if f"{c.get('code')}_{c.get('type')}" not in added_keys_this_cluster]
                # Ordina per priorità tipo: R > K > altri > E
                altri_tipi_stesso_codice.sort(key=lambda x: (
                    0 if x.get('type') == 'R' else
                    1 if x.get('type') == 'K' else
                    2 if x.get('type') not in ['E'] else 3,
                    _safe_get_sequence(x)
                ))
                
                for colore_stesso_codice in altri_tipi_stesso_codice:
                    key = f"{colore_stesso_codice['code']}_{colore_stesso_codice['type']}"
                    if key not in added_keys_this_cluster:
                        cluster_ordinato_temp.append(colore_stesso_codice)
                        added_keys_this_cluster.add(key)
                        print(f"    + Stesso codice del fisso ({primo_fisso_code}): {colore_stesso_codice['type']}")

        # 2. Aggiungi tutti i reintegri rimanenti + eventuali altri tipi degli stessi codici
        reintegri_da_processare = [r for r in reintegri if f"{r['code']}_{r['type']}" not in added_keys_this_cluster]
        codici_reintegri_processati = set()
        
        for r in reintegri_da_processare:
            key = f"{r['code']}_{r['type']}"
            if key not in added_keys_this_cluster:
                cluster_ordinato_temp.append(r)
                added_keys_this_cluster.add(key)
                r_code = r.get('code')
                print(f"    + Reintegro: {r_code}")
                codici_reintegri_processati.add(r_code)
                
                # Aggiungi subito tutti gli altri tipi dello stesso codice del reintegro
                if r_code and r_code in colori_per_codice:
                    altri_tipi_stesso_codice_r = [c for c in colori_per_codice[r_code] 
                                                if f"{c.get('code')}_{c.get('type')}" not in added_keys_this_cluster]
                    altri_tipi_stesso_codice_r.sort(key=lambda x: (
                        0 if x.get('type') == 'F' else
                        1 if x.get('type') == 'K' else
                        2 if x.get('type') not in ['E'] else 3,
                        _safe_get_sequence(x)
                    ))
                    
                    for colore_stesso_codice_r in altri_tipi_stesso_codice_r:
                        key_r = f"{colore_stesso_codice_r['code']}_{colore_stesso_codice_r['type']}"
                        if key_r not in added_keys_this_cluster:
                            cluster_ordinato_temp.append(colore_stesso_codice_r)
                            added_keys_this_cluster.add(key_r)
                            print(f"    + Stesso codice del reintegro ({r_code}): {colore_stesso_codice_r['type']}")

        # 3. Aggiungi i rimanenti non estetici + eventuali altri tipi degli stessi codici
        # 3. Aggiungi i rimanenti non estetici + eventuali altri tipi degli stessi codici
        rimanenti_non_estetici = [c for c in (fissi + kit + altri_non_estetici) 
                                 if f"{c.get('code')}_{c.get('type')}" not in added_keys_this_cluster]
        codici_non_estetici_processati = set()
        
        # Ordina per sicurezza per tipo e poi codice
        rimanenti_non_estetici.sort(key=lambda c: (config.TIPOLOGIA_PESO.get(c.get("type", "E"), 100), c.get('code')))
        
        for rne in rimanenti_non_estetici:
            key = f"{rne['code']}_{rne['type']}"
            rne_code = rne.get('code')
            if key not in added_keys_this_cluster and rne_code not in codici_non_estetici_processati:
                cluster_ordinato_temp.append(rne)
                added_keys_this_cluster.add(key)
                print(f"    + {rne['type']}: {rne_code}")
                codici_non_estetici_processati.add(rne_code)
                
                # Aggiungi subito tutti gli altri tipi dello stesso codice
                if rne_code and rne_code in colori_per_codice:
                    altri_tipi_stesso_codice_ne = [c for c in colori_per_codice[rne_code] 
                                                  if f"{c.get('code')}_{c.get('type')}" not in added_keys_this_cluster]
                    altri_tipi_stesso_codice_ne.sort(key=lambda x: (
                        0 if x.get('type') == 'F' else
                        1 if x.get('type') == 'R' else
                        2 if x.get('type') == 'K' else
                        3 if x.get('type') not in ['E'] else 4,
                        _safe_get_sequence(x)
                    ))
                    
                    for colore_stesso_codice_ne in altri_tipi_stesso_codice_ne:
                        key_ne = f"{colore_stesso_codice_ne['code']}_{colore_stesso_codice_ne['type']}"
                        if key_ne not in added_keys_this_cluster:
                            cluster_ordinato_temp.append(colore_stesso_codice_ne)
                            added_keys_this_cluster.add(key_ne)
                            print(f"    + Stesso codice ({rne_code}): {colore_stesso_codice_ne['type']}")

        # 4. Aggiungi gli estetici rimanenti + eventuali altri tipi degli stessi codici
        estetici_da_processare = [e for e in estetici if f"{e['code']}_{e['type']}" not in added_keys_this_cluster]
        codici_estetici_processati = set()
        
        for e in estetici_da_processare:
            key = f"{e['code']}_{e['type']}"
            e_code = e.get('code')
            if key not in added_keys_this_cluster and e_code not in codici_estetici_processati:
                cluster_ordinato_temp.append(e)
                added_keys_this_cluster.add(key)
                print(f"    + Estetico: {e_code}")
                codici_estetici_processati.add(e_code)
                
                # Aggiungi subito tutti gli altri tipi dello stesso codice dell'estetico
                if e_code and e_code in colori_per_codice:
                    altri_tipi_stesso_codice_e = [c for c in colori_per_codice[e_code] 
                                                if f"{c.get('code')}_{c.get('type')}" not in added_keys_this_cluster]
                    altri_tipi_stesso_codice_e.sort(key=lambda x: (
                        0 if x.get('type') == 'F' else
                        1 if x.get('type') == 'R' else
                        2 if x.get('type') == 'K' else
                        3 if x.get('type') not in ['E'] else 4,
                        _safe_get_sequence(x)
                    ))
                    
                    for colore_stesso_codice_e in altri_tipi_stesso_codice_e:
                        key_e = f"{colore_stesso_codice_e['code']}_{colore_stesso_codice_e['type']}"
                        if key_e not in added_keys_this_cluster:
                            cluster_ordinato_temp.append(colore_stesso_codice_e)
                            added_keys_this_cluster.add(key_e)
                            print(f"    + Stesso codice dell'estetico ({e_code}): {colore_stesso_codice_e['type']}")

        colori_ordinati.extend(cluster_ordinato_temp)
        colori_usati_keys.update(added_keys_this_cluster) # Aggiorna set globale

    # Verifica se tutti i colori sono stati inclusi
    if len(colori_ordinati) != len(colori_giorno):
        print(f"ATTENZIONE: Numero colori finali ({len(colori_ordinati)}) diverso da input ({len(colori_giorno)}).")
        original_keys = {f"{c['code']}_{c['type']}" for c in colori_giorno}
        missing_keys = original_keys - colori_usati_keys
        if missing_keys:
             print(f"Colori mancanti: {missing_keys}")
    # LOG: Stato finale lista ordinata
    print(f"[ORDERED_LIST OUTPUT] Lista finale ({len(colori_ordinati)}):")
    for i, color in enumerate(colori_ordinati):
        if color.get('code') == 'RAL5019':
            print(f"  [ORDERED OUT] {i}: {color}")
    print(f"  Tutti i codici ordinati: {[c.get('code') + ' ' + str(c.get('type')) for c in colori_ordinati]}")
    return colori_ordinati


# --- Funzione Principale di Orchestrazione ---
# backend/app/logic.py
# ...

def optimize_color_sequence(colori_giorno_input: List[Dict[str, Any]],
                            start_cluster_nome: Optional[str] = None,
                            first_color: Optional[str] = None,
                            prioritized_reintegrations: Optional[List[str]] = None
                           ) -> Tuple[List[Dict[str, Any]], List[str], float, str]:
    
    """
    Funzione principale che orchestra l'intero processo di ottimizzazione.
    Restituisce (lista_colori_ordinata_BEST, sequenza_cluster_BEST, costo_calcolato_BEST, messaggio_CON_TOP_N).
    """
    global _cost_matrix, _n_clusters
    _held_karp.cache_clear()
    print(f"  Cache Held-Karp pulita (inizio optimize_color_sequence): {_held_karp.cache_info()}")

    print("\n" + "="*50)
    print("--- Inizio Ottimizzazione Sequenza Colori ---")
    print(f"Input: {len(colori_giorno_input)} colori. Start Cluster Forzato: {start_cluster_nome or 'Nessuno'}")
    print(f"Primo Colore Specificato: {first_color or 'Nessuno'}")
    print(f"DEBUG: first_color type: {type(first_color)}, repr: {repr(first_color)}")
    if first_color:
        print(f"DEBUG: first_color dopo strip: '{first_color.strip()}'")
        print(f"DEBUG: first_color is truthy: {bool(first_color and first_color.strip())}")
    if prioritized_reintegrations:
        print(f"Reintegri Prioritari Richiesti: {prioritized_reintegrations}")
    if not colori_giorno_input:
        print("Errore: Lista colori input vuota.")
        return [], [], 0.0, "Errore: Lista colori input vuota."
    # LOG: Dettaglio input
    print(f"[LOGIC INPUT] Ricevuti {len(colori_giorno_input)} colori:")
    for i, color in enumerate(colori_giorno_input):
        if color.get('code') == 'RAL5019':
            print(f"  [INPUT] {i}: {color}")
    print(f"  Tutti i codici input: {[c.get('code') + ' ' + str(c.get('type')) for c in colori_giorno_input]}")

    # 1. Carica dati DB
    print("\n[STEP 1] Caricamento dati da DB...")
    cluster_dict = database.get_cluster_colori()
    cambio_colori = database.get_cambio_colori()
    if not cluster_dict or not cambio_colori:
         print("Errore: Impossibile caricare dati cluster o transizioni dal DB.")
         return [], [], 0.0, "Errore: Impossibile caricare dati cluster o transizioni dal DB."
    print(f"  Caricati {len(cluster_dict)} cluster mapping e {len(cambio_colori)} regole transizione.")

    # Crea una copia per non modificare l'input originale direttamente con i cluster
    colori_giorno = [c.copy() for c in colori_giorno_input]

    # 2. Mappa colori a cluster e identifica quelli di oggi
    print("\n[STEP 2] Mappatura colori a cluster...")
    colore2cluster, clusters_oggi_from_input, urgenti = _map_colors_to_clusters(colori_giorno, cluster_dict)
    
    # Costruisci la lista finale di cluster per la matrice, includendo start_cluster_nome se specificato
    _clusters_for_matrix_build = list(set(clusters_oggi_from_input)) # Cluster unici dagli input

    if start_cluster_nome and start_cluster_nome not in _clusters_for_matrix_build:
        _clusters_for_matrix_build.append(start_cluster_nome)
        print(f"  INFO: Requested start cluster '{start_cluster_nome}' was not in input colors' clusters. Added to the optimization set.")

    # Ordina i cluster con prioritizzazione per sequenza: prima i cluster con valori di sequenza più bassi
    clusters_unique = list(set(_clusters_for_matrix_build))
    
    # Calcola priorità di sequenza per ogni cluster
    cluster_priorities = []
    print("\n[CLUSTER SEQUENCE PRIORITIZATION] Calcolo priorità sequenza per cluster...")
    for cluster_nome in clusters_unique:
        seq_priority = _get_cluster_sequence_priority(cluster_nome, colori_giorno)
        cluster_priorities.append((cluster_nome, seq_priority))
        print(f"  Cluster '{cluster_nome}': sequenza minima = {seq_priority if seq_priority != 999 else 'N/D'}")
    
    # Ordina per priorità sequenza (valori più bassi prima), poi alfabeticamente per consistenza
    final_matrix_clusters = [cluster for cluster, _ in sorted(cluster_priorities, key=lambda x: (x[1], x[0]))]

    print(f"  Cluster considerati per la matrice ({len(final_matrix_clusters)}) - ORDINATI PER PRIORITÀ SEQUENZA: {final_matrix_clusters}")
    print(f"  Cluster urgenti ({len(urgenti)}): {urgenti}")

    _n_clusters = len(final_matrix_clusters) # Aggiorna variabile globale per Held-Karp
    
    start_index: Optional[int] = None
    
    # Se non è stato specificato un cluster di partenza, usa quello con priorità sequenza più alta
    if not start_cluster_nome and final_matrix_clusters:
        # Trova il cluster con la sequenza più bassa (priorità più alta)
        best_cluster = final_matrix_clusters[0]  # Già ordinato per priorità sequenza
        start_cluster_nome = best_cluster
        print(f"  INFO: Nessun cluster di partenza specificato. Auto-selezione cluster con priorità sequenza più alta: '{start_cluster_nome}'")
    
    if start_cluster_nome: # Trova l'indice di start_cluster_nome nella lista final_matrix_clusters
        try:
            start_index = final_matrix_clusters.index(start_cluster_nome)
            print(f"  Forcing optimization to start from cluster '{start_cluster_nome}' (index {start_index} in {final_matrix_clusters})")
        except ValueError:
            # Questo non dovrebbe accadere se l'abbiamo aggiunto sopra, ma per sicurezza
            print(f"  CRITICAL ERROR: Requested start_cluster_nome '{start_cluster_nome}' not found in final_matrix_clusters even after adding. Ignoring fixed start.")
            start_cluster_nome = None # Resetta
            # start_index rimane None

    if _n_clusters == 0:
        print("Nessun cluster valido trovato (neanche lo start_cluster_nome se specificato). Restituito ordine input.")
        return colori_giorno_input, [], 0.0, "Nessun cluster valido trovato. Restituito ordine input."
    
    if _n_clusters == 1:
         # Se c'è un solo cluster (potrebbe essere lo start_cluster_nome aggiunto artificialmente)
         the_only_cluster = final_matrix_clusters[0]
         print(f"Trovato solo 1 cluster per l'ottimizzazione: {the_only_cluster}. Ordinamento banale.")
         tour_clusters = [the_only_cluster]
         # Filtra colori_giorno per includere solo quelli che appartengono a the_only_cluster (se ce ne sono)
         colori_per_unico_cluster = [c for c in colori_giorno if c.get("cluster") == the_only_cluster]
         colori_finali_ordinati = _generate_final_ordered_list(tour_clusters, colori_per_unico_cluster, first_color)
         for c_out in colori_finali_ordinati:
             if 'cluster' not in c_out or not c_out['cluster']:
                  c_out['cluster'] = colore2cluster.get(c_out.get('code',''), the_only_cluster)
         return colori_finali_ordinati, tour_clusters, 0.0, f"Ottimizzazione completata (solo 1 cluster considerato: {tour_clusters[0]})."

    # 3. Costruisci matrice costi usando final_matrix_clusters
    print("\n[STEP 3] Costruzione matrice costi...")
    _cost_matrix = _build_cost_matrix(final_matrix_clusters, colori_giorno, cambio_colori, prioritized_reintegrations)
    if _cost_matrix.size == 0 or _cost_matrix.shape != (_n_clusters, _n_clusters):
        # ... (gestione errore matrice come prima, ma usa final_matrix_clusters per fallback)
        fallback_ordered = []
        for cl_name in final_matrix_clusters: # Itera sui cluster della matrice
            # Aggiungi solo colori che effettivamente appartengono a questo cluster
            fallback_ordered.extend([c for c in colori_giorno if c.get('cluster') == cl_name])
        return fallback_ordered, [], config.INFINITE_COST, f"Errore: Matrice costi non valida (shape: {_cost_matrix.shape}). Restituito raggruppamento per cluster."

    # 4. Trova percorso ottimale (Held-Karp)
    print("\n[STEP 4] Ricerca percorsi ottimali (Held-Karp)...")
    
    # start_index è già stato calcolato sopra basandosi su final_matrix_clusters
    # _find_best_path_and_reconstruct ora restituisce una lista di (costo, indici_tour)
    top_paths_data = _find_best_path_and_reconstruct(_n_clusters, start_index)

    if not top_paths_data:
         fallback_ordered = []
         for cl_name in final_matrix_clusters:
             fallback_ordered.extend([c for c in colori_giorno if c.get('cluster') == cl_name])
         err_msg = "Errore: Held-Karp non ha trovato nessun percorso valido."
         if start_cluster_nome:
             err_msg += f" (partendo da '{start_cluster_nome}')"
         err_msg += " Restituito raggruppamento per cluster."
         return fallback_ordered, [], config.INFINITE_COST, err_msg

    # Il primo elemento è il migliore in assoluto
    best_cost, best_tour_indices = top_paths_data[0]
    
    print(f"  Miglior risultato Held-Karp (1 di {len(top_paths_data)}): Costo={best_cost}, Tour Indici={best_tour_indices}")

    if not best_tour_indices or len(best_tour_indices) != _n_clusters or best_cost >= config.INFINITE_COST:
         # Questo blocco potrebbe non essere più necessario se _find_best_path_and_reconstruct
         # garantisce di restituire solo percorsi validi o una lista vuota.
         # Ma lo teniamo per sicurezza.
         fallback_ordered = []
         for cl_name in final_matrix_clusters:
             fallback_ordered.extend([c for c in colori_giorno if c.get('cluster') == cl_name])
         return fallback_ordered, [], config.INFINITE_COST, "Errore: Il miglior percorso Held-Karp non è valido. Restituito raggruppamento per cluster."

    best_tour_clusters = [final_matrix_clusters[i] for i in best_tour_indices]
    print(f"  Percorso cluster ottimale (TOP 1): {' -> '.join(best_tour_clusters)} (Costo: {best_cost:.2f})")

    # 5. Genera lista colori finale ordinata (SOLO PER IL MIGLIOR PERCORSO)
    print("\n[STEP 5] Generazione lista colori finale ordinata (per il miglior percorso)...")
    colori_finali_ordinati = _generate_final_ordered_list(best_tour_clusters, colori_giorno, first_color)
    print(f"  Generata lista finale con {len(colori_finali_ordinati)} colori.")
    print(f"[LOGIC OUTPUT] colori_finali_ordinati (len {len(colori_finali_ordinati)}):")
    for i, color in enumerate(colori_finali_ordinati):
        if color.get('code') == 'RAL5019': # Esempio di log specifico
            print(f"  [OUTPUT] {i}: {color}")
    print(f"  Tutti i codici output: {[c.get('code') + ' ' + str(c.get('type')) for c in colori_finali_ordinati]}")

    if len(colori_finali_ordinati) != len(colori_giorno_input):
         print(f"  ATTENZIONE: Numero colori finali ({len(colori_finali_ordinati)}) diverso da input ({len(colori_giorno_input)})!")
         input_codes = {c['code'] for c in colori_giorno_input}
         output_codes = {c['code'] for c in colori_finali_ordinati}
         print(f"    Colori input non in output: {input_codes - output_codes}")
         print(f"    Colori output non in input: {output_codes - input_codes}")

    # 6. Prepara messaggio finale, includendo i TOP N percorsi
    messaggio = f"Ottimizzazione completata. \n"
    messaggio += f"Miglior Percorso Cluster (usato per ordinamento colori): {' -> '.join(best_tour_clusters)}. Costo: {best_cost:.2f}.\n"
    
    if len(top_paths_data) > 1:
        messaggio += "\nAltri percorsi ottimali trovati (fino a {TOP_N_RESULTS}): \n"
        for i, (cost, indices) in enumerate(top_paths_data): # Mostra tutti quelli restituiti
            if i == 0 and len(top_paths_data) >1 : messaggio += f"  1. (Come sopra)\n" # evita di stampare due volte il primo
            elif i < 3 : # mostra fino a 3, incluso il primo se è l'unico o se stiamo mostrando gli "altri"
                # if i == 0 and len(top_paths_data) == 1: # caso in cui è l'unico
                #      pass # già incluso nella linea "Miglior Percorso"
                # el
                current_tour_c_names = [final_matrix_clusters[j] for j in indices]
                messaggio += f"  {i+1}. Sequenza: {' -> '.join(current_tour_c_names)}. Costo: {cost:.2f}.\n"

    if start_cluster_nome and start_index is not None:
         messaggio += f" (Nota: Inizio forzato da '{start_cluster_nome}')."
    if prioritized_reintegrations:
        messaggio += f" (Considerati reintegri prioritari: {prioritized_reintegrations})."

    for c_out in colori_finali_ordinati:
         if 'cluster' not in c_out or not c_out['cluster']:
              c_out['cluster'] = colore2cluster.get(c_out.get('code',''), 'N/D')

    print("\n--- Fine Ottimizzazione ---")
    print("="*50 + "\n")

    final_cost_value = config.INFINITE_COST if best_cost >= config.INFINITE_COST else best_cost
    return colori_finali_ordinati, best_tour_clusters, final_cost_value, messaggio.strip()

# Funzioni helper per la gestione persistente dei dati delle cabine
import json
import os
from pathlib import Path

# Percorso per salvare i dati delle cabine
CABIN_DATA_DIR = Path(__file__).parent / "data" / "cabins"

def _ensure_cabin_data_dir():
    """Assicura che la directory per i dati delle cabine esista."""
    CABIN_DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_colors_for_cabin(cabin_id: int) -> List[Dict[str, Any]]:
    """
    Recupera la lista colori salvata per una cabina specifica dal database.
    """
    try:
        conn = database.connect_to_db()
        if not conn:
            print(f"Errore connessione database per cabina {cabin_id}")
            return []
            
        cursor = conn.cursor()
        
        # Legge i colori dal database ordinati per sequence_order
        cursor.execute("""
            SELECT color_code, color_type, cluster, ch_value, lunghezza_ordine, 
                   input_sequence, sequence_type, locked, sequence_order
            FROM optimization_colors 
            WHERE cabin_id = ? 
            ORDER BY sequence_order ASC
        """, (cabin_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        colors = []
        for row in rows:
            color_dict = {
                'color_code': row[0],
                'color_type': row[1], 
                'cluster': row[2],
                'ch_value': row[3],
                'lunghezza_ordine': row[4],
                'input_sequence': row[5],
                'sequence_type': row[6],
                'locked': bool(row[7]) if row[7] is not None else False,
                'sequence_order': row[8]
            }
            colors.append(color_dict)
        
        print(f"[DB] Caricati {len(colors)} colori per cabina {cabin_id}")
        return colors
        
    except Exception as e:
        print(f"Errore durante il caricamento dei colori della cabina {cabin_id}: {e}")
        return []

def save_colors_for_cabin(cabin_id: int, colors: List[Dict[str, Any]]):
    """
    Salva la lista colori per una cabina specifica nel database.
    """
    try:
        conn = database.connect_to_db()
        if not conn:
            print(f"Errore connessione database per salvataggio cabina {cabin_id}")
            return
            
        cursor = conn.cursor()
        
        # Prima cancella tutti i colori esistenti per questa cabina
        cursor.execute("DELETE FROM optimization_colors WHERE cabin_id = ?", (cabin_id,))
        
        # Inserisce i nuovi colori
        for i, color in enumerate(colors):
            cursor.execute("""
                INSERT INTO optimization_colors 
                (cabin_id, color_code, color_type, cluster, ch_value, lunghezza_ordine, 
                 input_sequence, sequence_type, locked, sequence_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cabin_id,
                color.get('color_code', ''),
                color.get('color_type', ''),
                color.get('cluster', ''),
                color.get('ch_value', ''),
                color.get('lunghezza_ordine', ''),
                color.get('input_sequence', ''),
                color.get('sequence_type', ''),
                color.get('locked', False),
                color.get('sequence_order', i + 1)
            ))
        
        conn.commit()
        conn.close()
        
        print(f"[DB] Salvati {len(colors)} colori per cabina {cabin_id} nel database")
        
    except Exception as e:
        print(f"Errore durante il salvataggio dei colori della cabina {cabin_id}: {e}")
        raise

def reorganize_colors_by_cluster_order(colors: List[Dict[str, Any]], cluster_order: List[str]) -> List[Dict[str, Any]]:
    """
    Riorganizza i colori secondo un ordine specifico dei cluster.
    I colori vengono raggruppati per cluster secondo l'ordine specificato.
    """
    try:
        print(f"[LOGIC] Riorganizzazione {len(colors)} colori secondo ordine cluster: {cluster_order}")
        
        # Raggruppa i colori per cluster
        colors_by_cluster = {}
        colors_without_cluster = []
        
        for color in colors:
            cluster = color.get('cluster', '')
            if cluster:
                if cluster not in colors_by_cluster:
                    colors_by_cluster[cluster] = []
                colors_by_cluster[cluster].append(color)
            else:
                colors_without_cluster.append(color)
        
        print(f"[LOGIC] Cluster trovati: {list(colors_by_cluster.keys())}")
        print(f"[LOGIC] Colori senza cluster: {len(colors_without_cluster)}")
        
        # Riorganizza secondo l'ordine specificato
        reorganized_colors = []
        
        # Prima aggiungi i cluster nell'ordine specificato
        for cluster in cluster_order:
            if cluster in colors_by_cluster:
                cluster_colors = colors_by_cluster[cluster]
                print(f"[LOGIC] Aggiungendo cluster '{cluster}': {len(cluster_colors)} colori")
                
                # Mantieni l'ordine interno dei colori del cluster (per tipo, sequenza, ecc.)
                # Ordina per color_code e color_type per un ordinamento coerente
                cluster_colors.sort(key=lambda c: (c.get('color_code', ''), c.get('color_type', '')))
                
                reorganized_colors.extend(cluster_colors)
                # Rimuovi il cluster dalla lista per evitare duplicati
                del colors_by_cluster[cluster]
        
        # Aggiungi eventuali cluster non specificati nell'ordine (in ordine alfabetico)
        remaining_clusters = sorted(colors_by_cluster.keys())
        for cluster in remaining_clusters:
            cluster_colors = colors_by_cluster[cluster]
            print(f"[LOGIC] Aggiungendo cluster rimanente '{cluster}': {len(cluster_colors)} colori")
            
            cluster_colors.sort(key=lambda c: (c.get('color_code', ''), c.get('color_type', '')))
            reorganized_colors.extend(cluster_colors)
        
        # Infine aggiungi i colori senza cluster
        if colors_without_cluster:
            print(f"[LOGIC] Aggiungendo {len(colors_without_cluster)} colori senza cluster")
            colors_without_cluster.sort(key=lambda c: (c.get('color_code', ''), c.get('color_type', '')))
            reorganized_colors.extend(colors_without_cluster)
        
        # Aggiorna le posizioni nella sequenza
        for i, color in enumerate(reorganized_colors):
            color['sequence_order'] = i + 1
        
        print(f"[LOGIC] Riorganizzazione completata: {len(reorganized_colors)} colori")
        return reorganized_colors
        
    except Exception as e:
        print(f"Errore durante riorganizzazione colori per cluster: {e}")
        raise
def optimize_with_locked_colors(colors: List[Dict[str, Any]], cluster_sequence: List[str] = None) -> Dict[str, Any]:
    """
    Ottimizza la sequenza colori rispettando i colori bloccati.
    I colori bloccati mantengono la loro posizione, quelli non bloccati vengono riordinati.
    """
    try:
        # Separa colori bloccati da quelli liberi
        locked_colors = [c for c in colors if c.get('locked', False)]
        free_colors = [c for c in colors if not c.get('locked', False)]
        
        # Se non ci sono colori liberi, restituisci la sequenza attuale
        if not free_colors:
            return {
                'colors': colors,
                'cluster_sequence': cluster_sequence or [],
                'cost': 0,
                'message': 'Tutti i colori sono bloccati - nessuna ottimizzazione eseguita'
            }
        
        # Determina il cluster di partenza dall'ultimo colore bloccato
        starting_cluster = None
        if locked_colors:
            # Trova l'ultimo colore bloccato nella sequenza originale
            last_locked_index = -1
            last_locked_color = None
            
            for i, color in enumerate(colors):
                if color.get('locked', False):
                    if i > last_locked_index:
                        last_locked_index = i
                        last_locked_color = color
            
            if last_locked_color:
                starting_cluster = last_locked_color.get('cluster')
                print(f"[OPTIMIZE] Cluster di partenza determinato dall'ultimo colore bloccato (pos {last_locked_index + 1}): {starting_cluster}")
        
        # Se c'è un cluster di partenza, riordina i colori liberi per iniziare con quelli dello stesso cluster
        if starting_cluster:
            same_cluster_colors = [c for c in free_colors if c.get('cluster') == starting_cluster]
            other_colors = [c for c in free_colors if c.get('cluster') != starting_cluster]
            
            print(f"[OPTIMIZE] Colori liberi stesso cluster ({starting_cluster}): {len(same_cluster_colors)}")
            print(f"[OPTIMIZE] Altri colori liberi: {len(other_colors)}")
            
            # Riordina: prima i colori dello stesso cluster, poi gli altri
            free_colors_ordered = same_cluster_colors + other_colors
        else:
            free_colors_ordered = free_colors
        
        # Ottimizza i colori liberi con informazione del cluster di partenza
        if starting_cluster:
            # Forza l'ottimizzazione a partire dal cluster determinato
            optimized_free, cluster_seq, cost, message = optimize_color_sequence(
                free_colors_ordered, start_cluster_nome=starting_cluster
            )
        else:
            # Ottimizzazione normale
            optimized_free, cluster_seq, cost, message = optimize_color_sequence(free_colors_ordered)
        
        # Ricostruisci la sequenza finale rispettando le posizioni bloccate
        final_colors = []
        free_index = 0
        
        for i, original_color in enumerate(colors):
            if original_color.get('locked', False):
                # Mantieni il colore bloccato nella sua posizione
                final_colors.append(original_color)
            else:
                # Inserisci il prossimo colore ottimizzato
                if free_index < len(optimized_free):
                    optimized_color = optimized_free[free_index].copy()
                    optimized_color['position'] = i
                    final_colors.append(optimized_color)
                    free_index += 1
        
        return {
            'colors': final_colors,
            'cluster_sequence': cluster_seq,
            'cost': cost,
            'message': f'Ottimizzazione completata con {len(locked_colors)} colori bloccati. {message}'
        }
    
    except Exception as e:
        print(f"Errore durante l'ottimizzazione con colori bloccati: {e}")
        raise

def optimize_with_partial_cluster_order(colors: List[Dict[str, Any]], cluster_locks: Dict[str, bool] = None) -> Dict[str, Any]:
    """
    Ottimizza la sequenza colori considerando i cluster bloccati.
    Quando un cluster è bloccato, tutti i suoi colori vengono automaticamente bloccati.
    """
    try:
        cluster_locks = cluster_locks or {}
        
        # Applica il blocco automatico ai colori dei cluster bloccati
        updated_colors = []
        for color in colors:
            color_copy = color.copy()
            cluster_name = color_copy.get('cluster', '')
            
            # Se il cluster è bloccato, blocca automaticamente tutti i suoi colori
            if cluster_locks.get(cluster_name, False):
                color_copy['locked'] = True
                color_copy['cluster_locked'] = True
            
            updated_colors.append(color_copy)
        
        # Usa la funzione di ottimizzazione con colori bloccati
        return optimize_with_locked_colors(updated_colors)
    
    except Exception as e:
        print(f"Errore durante l'ottimizzazione con cluster parzialmente bloccati: {e}")
        raise

def update_color_positions(colors: List[Dict[str, Any]], new_positions: List[int]) -> List[Dict[str, Any]]:
    """
    Aggiorna le posizioni dei colori basandosi su una nuova sequenza di posizioni.
    Utilizzato per il drag & drop.
    """
    try:
        if len(colors) != len(new_positions):
            raise ValueError("Il numero di colori deve corrispondere al numero di nuove posizioni")
        
        # Crea una copia dei colori e aggiorna le posizioni
        updated_colors = []
        for i, new_pos in enumerate(new_positions):
            if new_pos < len(colors):
                color_copy = colors[new_pos].copy()
                color_copy['position'] = i
                updated_colors.append(color_copy)
        
        return updated_colors
    
    except Exception as e:
        print(f"Errore durante l'aggiornamento delle posizioni: {e}")
        raise

def optimize_color_sequence_with_types(colors_input: List[Dict[str, Any]], **kwargs) -> tuple:
    """
    Wrapper function per compatibilità con il codice esistente.
    Chiama optimize_color_sequence con i parametri appropriati.
    """
    return optimize_color_sequence(colors_input, **kwargs)

def optimize_color_sequence_with_cabins(colori_giorno_input: List[Dict[str, Any]], **kwargs) -> dict:
    """
    Wrapper function per compatibilità con il codice esistente.
    Chiama optimize_color_sequence con i parametri appropriati.
    """
    return optimize_color_sequence(colori_giorno_input, **kwargs)
