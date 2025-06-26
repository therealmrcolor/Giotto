#!/usr/bin/env python3
import requests
import json

# URL dell'endpoint per aggiornare i pesi
UPDATE_URL = "http://localhost:8080/update-transition-weight"
WEIGHTS_INFO_URL = "http://localhost:8080/db-cambio-colori"

# Transizioni problematiche e i loro pesi desiderati (alti)
transitions_to_fix = [
    {"source_cluster": "Nero", "target_cluster": "Bianco", "peso": 250},
    {"source_cluster": "Bianco", "target_cluster": "Nero", "peso": 250} # Aggiunto Bianco -> Nero
]

def get_current_weights():
    try:
        response = requests.get(WEIGHTS_INFO_URL)
        response.raise_for_status()
        data = response.json()
        print("Pesi attuali delle transizioni:")
        for source, targets in data.get("transizioni", {}).items():
            for target_info in targets:
                print(f"  {source} -> {target_info['target']}: {target_info['peso']}")
        print("\nProblemi identificati dal backend:")
        for problem in data.get("problemi", []):
            print(f"  - {problem}")
        return data.get("transizioni", {})
    except requests.exceptions.RequestException as e:
        print(f"Errore ottenendo i pesi: {e}")
        return {}
    except json.JSONDecodeError:
        print(f"Errore decodificando JSON da {WEIGHTS_INFO_URL}")
        return {}

def update_weight(transition_data):
    print(f"\nTentativo aggiornamento: {transition_data['source_cluster']} -> {transition_data['target_cluster']} a peso {transition_data['peso']}...")
    try:
        response = requests.post(UPDATE_URL, json=transition_data)
        response.raise_for_status()
        result = response.json()
        print(f"  Risultato: {result.get('message', 'Nessun messaggio')}")
        if not result.get('success', False):
             print(f"  Errore dal backend: {result.get('error', 'Errore sconosciuto')}")
    except requests.exceptions.RequestException as e:
        print(f"  Errore richiesta HTTP per aggiornamento: {e}")
    except json.JSONDecodeError:
        print(f"  Errore decodificando JSON dalla risposta di aggiornamento.")


if __name__ == "__main__":
    print("--- Controllo e Correzione Pesi Transizioni ---")
    current_weights_map = get_current_weights()

    for trans_fix in transitions_to_fix:
        source = trans_fix["source_cluster"]
        target = trans_fix["target_cluster"]
        new_peso = trans_fix["peso"]
        
        # Verifica se la transizione esiste e qual è il suo peso attuale
        current_peso = None
        if source in current_weights_map:
            for t_info in current_weights_map[source]:
                if t_info['target'] == target:
                    current_peso = t_info['peso']
                    break
        
        if current_peso is None:
            print(f"\nATTENZIONE: Transizione {source} -> {target} non trovata nei dati attuali. Potrebbe non esistere o esserci un errore di nome.")
            # Opzionalmente, potresti tentare di aggiungerla qui se fosse desiderato, ma per ora solo notifica
            # Se la transizione non esiste, l'update fallirà comunque con un messaggio appropriato dal backend
            update_weight(trans_fix) # Tentiamo comunque l'update
        elif current_peso == new_peso:
            print(f"\nTransizione {source} -> {target} ha già il peso desiderato ({new_peso}). Nessun aggiornamento necessario.")
        else:
            print(f"\nTransizione {source} -> {target} ha peso {current_peso}. Verrà aggiornato a {new_peso}.")
            update_weight(trans_fix)

    print("\n--- Controllo completato ---")
    print("Verifica nuovamente i pesi tramite l'endpoint o l'interfaccia di gestione.") 