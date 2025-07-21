# backend/app/models.py
"""Pydantic models for API data validation and type hinting."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple, Union

# Alias di tipi come nel notebook
ColorObject = Dict[str, Any]
ClusterDict = Dict[str, List[str]]
TransitionRuleDict = Dict[Tuple[str, str], Dict[str, Any]]

# Modello per un singolo colore in input dall'API
class ColorInput(BaseModel):
    code: str
    type: str
    sequence: Optional[int] = None # O qualsiasi altro campo presente in colori.txt
    sequence_type: Optional[str] = None # "piccola" o "successiva" - per gestire le sequenze
    CH: Optional[float] = None # Centiore - da implementare in futuro
    lunghezza_ordine: Optional[str] = None # "corto" o "lungo" - per divisione in cabine
    locked: Optional[bool] = False # Nuovo campo per bloccare singoli colori
    position: Optional[int] = None # Posizione specifica se bloccato

# Modello per il corpo della richiesta all'endpoint /optimize
class OptimizationRequest(BaseModel):
    colors_today: List[ColorInput] = Field(..., description="Lista dei colori da produrre oggi.")
    start_cluster_name: Optional[str] = Field(None, description="Nome del cluster con cui forzare l'inizio (opzionale).")
    first_color: Optional[str] = Field(None, description="Codice del primo colore con cui iniziare il cluster (opzionale).")
    prioritized_reintegrations: Optional[List[str]] = Field(None, description="Lista dei codici colore dei reintegri a cui dare priorità extra.") # NUOVO CAMPO

# Modello per un singolo colore nell'output ottimizzato
class OptimizedColorOutput(BaseModel):
    code: str
    type: str
    cluster: Optional[str] # Aggiunto dal backend
    sequence: Optional[int] = None # Mantenuto se presente in input
    sequence_type: Optional[str] = None # Mantenuto se presente in input
    CH: Optional[float] = None # Mantenuto se presente in input
    lunghezza_ordine: Optional[str] = None # Mantenuto se presente in input
    locked: Optional[bool] = False # Mantenuto se presente in input
    position: Optional[int] = None # Posizione finale nel risultato ottimizzato

# Modello per la risposta dell'endpoint /optimize
class OptimizationResponse(BaseModel):
    ordered_colors: List[OptimizedColorOutput]
    optimal_cluster_sequence: List[str]
    calculated_cost: Union[float, str] # Può essere 'inf' o un numero
    message: str # Messaggio di successo o errore

# Modello per la risposta dell'endpoint /optimize con gestione cabine
class CabinOptimizationResponse(BaseModel):
    cabina_1: Optional[OptimizationResponse] = None  # Risultati per colori "corto" (opzionale)
    cabina_2: Optional[OptimizationResponse] = None  # Risultati per colori "lungo" (opzionale)
    message: str # Messaggio di successo o errore generale