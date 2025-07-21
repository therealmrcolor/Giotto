# backend/app/config.py
"""Configuration constants for the color optimization backend."""

# Pesi per tipologia di colore (Cella 3 del notebook)
# Valori più bassi = priorità più alta nel triggerare un cambio
TIPOLOGIA_PESO = {
    "R": 0,    # Reintegro urgente (massima priorità)
    "RE": 1,   # Reintegro non urgente
    "F": 2,    # Fisso
    "K": 4,    # Kit
    "E": 100   # Estetico (molto penalizzato come *trigger* per un cambio)
}

# Penalità aggiuntiva se si è *costretti* ad usare un colore Estetico come trigger
# (Usato nella logica di costruzione matrice se allow_estetico_trigger=True)
PENALITA_TRIGGER_ESTETICO = 6

# Costo "infinito" per transizioni vietate o impossibili
INFINITE_COST = 9999

# Penalità per tipo "F" (Fisso) non soddisfatto
# Invece di rendere la transizione impossibile, applica questa penalità
PENALTY_UNSATISFIED_F_TYPE = 100

# Costo per rimanere nello stesso cluster
SAME_CLUSTER_COST = 1

# Bonus (valore negativo) da applicare al costo di transizione
# se il cluster di DESTINAZIONE contiene colori di tipo 'R' (Reintegro urgente).
# Un valore più negativo rende la transizione più attraente.
BONUS_REINTEGRO_DESTINAZIONE = -20 # Esempio: Sconto di 20 sul costo

# Bonus per Reintegri non urgenti (meno bonus rispetto agli urgenti)
BONUS_REINTEGRO_NON_URGENTE_DESTINAZIONE = -10  # Sconto di 10 sul costo

# Bonus (valore negativo MAGGIORE) per Reintegri specificamente prioritizzati dall'utente.
BONUS_REINTEGRO_PRIORITARIO = -50  # Esempio: Sconto di 50, deve essere > BONUS_REINTEGRO_DESTINAZIONE

# Path del database SQLite
import os
from pathlib import Path

# Calcola il path relativo al database partendo dalla directory corrente
# Il backend/app/ dovrebbe puntare a ../../shared/data/colors.db
current_dir = Path(__file__).parent
DATABASE_PATH = os.environ.get('DATABASE_PATH', str(current_dir / "../../shared/data/colors.db"))

# Fattore di penalità per le urgenze 
URGENCY_PENALTY_FACTOR = 10

# Costo di default se non esiste una regola specifica tra due cluster
DEFAULT_TRANSITION_COST = 10

# --- NUOVE CONFIGURAZIONI PER GESTIONE SEQUENZE ---

# Tipi di sequenza supportati
SEQUENCE_TYPE_SMALL = "piccola"  # Sequenza piccola - può essere fatta nella giornata odierna
SEQUENCE_TYPE_NEXT = "successiva"  # Sequenza successiva - del giorno successivo

# Mapping dei tipi di sequenza per validazione
VALID_SEQUENCE_TYPES = [SEQUENCE_TYPE_SMALL, SEQUENCE_TYPE_NEXT]

# Peso aggiuntivo per ordinamento interno delle sequenze piccole
# (le sequenze piccole con numero diverso vengono ordinate internamente)
SMALL_SEQUENCE_INTERNAL_WEIGHT = 1

# Soglia per determinare automaticamente se una sequenza è "piccola"
# (numero di colori sotto questa soglia possono essere considerati "piccoli")
AUTO_SMALL_SEQUENCE_THRESHOLD = 10

# --- CONFIGURAZIONI PER PRIORITIZZAZIONE CLUSTER PER SEQUENZA ---

# Bonus (valore negativo) da applicare al costo di transizione quando si va 
# VERSO un cluster con priorità di sequenza più alta (valore di sequenza più basso).
# Questo incoraggia il movimento verso cluster con sequenze inferiori.
BONUS_SEQUENCE_PRIORITY = -50  # Sconto di 50 sul costo per priorità alta

# Penalità (valore positivo) da applicare al costo di transizione quando si va
# VERSO un cluster con priorità di sequenza più bassa (valore di sequenza più alto).
# Questo scoraggia il movimento verso cluster con sequenze superiori.
PENALTY_SEQUENCE_PRIORITY = 25  # Penalità di 25 sul costo per priorità bassa

# Soglia per la differenza di sequenza che attiva bonus/penalità.
# Solo se la differenza di sequenza tra source e destination è >= questa soglia
# verranno applicati i bonus/penalità.
SEQUENCE_PRIORITY_THRESHOLD = 1