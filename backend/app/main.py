# backend/app/main.py
"""FastAPI application for color sequence optimization."""

from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional, Union # Assicurati che Optional e Union siano importati
import traceback # Per logging errori dettagliato
import json

# Importa modelli e logica
# Assicurati che i percorsi siano corretti per la tua struttura
from .models import OptimizationRequest, OptimizationResponse, ColorInput, OptimizedColorOutput, CabinOptimizationResponse
from .logic import optimize_color_sequence
from .config import INFINITE_COST
from . import logic

app = FastAPI(
    title="Color Sequence Optimizer API",
    description="API per ottimizzare la sequenza di produzione dei colori.",
    version="1.0.0"
)

# Add validation error handler
@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    """
    Handle validation errors with detailed information
    """
    print("="*50 + " VALIDATION ERROR " + "="*50)
    print(f"Request URL: {request.url}")
    print(f"Request method: {request.method}")
    
    try:
        body = await request.body()
        print(f"Request body: {body.decode('utf-8')}")
    except:
        print("Could not read request body")
    
    print(f"Validation error details: {exc}")
    print("="*100)
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": f"Validation error: {exc}",
            "error_type": "validation_error"
        }
    )

@app.post("/optimize",
          response_model=Union[OptimizationResponse, CabinOptimizationResponse],
          summary="Ottimizza la sequenza dei colori",
          description="Riceve una lista di colori da produrre e restituisce la sequenza ottimizzata. Può includere reintegri prioritari e ottimizzazione per cabine.")
async def optimize_sequence(request: Request, request_data: OptimizationRequest = Body(...)):
    """
    Endpoint principale per l'ottimizzazione.
    Riceve la lista colori, il cluster iniziale opzionale e la lista
    opzionale dei codici dei reintegri da prioritizzare.
    """
    print("=" * 80)
    print("DETTAGLI RICHIESTA RICEVUTA:")
    
    # Log raw request for debugging
    try:
        body = await request.body()
        raw_data = json.loads(body.decode('utf-8'))
        print(f"Raw request data: {json.dumps(raw_data, indent=2)}")
        print(f"first_color nel raw data: {repr(raw_data.get('first_color'))}")
        print(f"start_cluster_name nel raw data: {repr(raw_data.get('start_cluster_name'))}")
    except Exception as e:
        print(f"Could not parse raw request: {e}")
    
    print(f"Richiesta API /optimize ricevuta per {len(request_data.colors_today)} colori.")
    
    # Log dettagliato dei colori ricevuti
    print("COLORI RICEVUTI:")
    for i, color in enumerate(request_data.colors_today):
        print(f"  Colore {i}: code={color.code}, type={color.type}, sequence={color.sequence}")
        # Validate required fields
        if not color.code:
            raise HTTPException(status_code=422, detail=f"Color {i}: 'code' field is required and cannot be empty")
        if not color.type:
            raise HTTPException(status_code=422, detail=f"Color {i}: 'type' field is required and cannot be empty")
    
    # Log del cluster iniziale
    if request_data.start_cluster_name:
         print(f"Cluster iniziale richiesto: {request_data.start_cluster_name}")
    else:
         print("Nessun cluster iniziale specificato")
         
    # Log del primo colore
    if request_data.first_color:
         print(f"Primo colore richiesto: {request_data.first_color}")
         print(f"Tipo primo colore: {type(request_data.first_color)}")
         print(f"Lunghezza primo colore: {len(request_data.first_color.strip()) if request_data.first_color else 0}")
         
         # Verifica se il primo colore è nella lista
         color_codes = [c.code for c in request_data.colors_today]
         print(f"Codici colori disponibili: {color_codes}")
         if request_data.first_color in color_codes:
             print(f"PRIMO COLORE TROVATO nella lista: {request_data.first_color}")
         else:
             print(f"PRIMO COLORE NON TROVATO nella lista: {request_data.first_color}")
             print(f"Confronti:")
             for i, code in enumerate(color_codes):
                 print(f"  {i}: '{code}' == '{request_data.first_color}' ? {code == request_data.first_color}")
    else:
         print("Nessun primo colore specificato")
         print(f"Valore raw first_color: {repr(request_data.first_color)}")
         
    # Log dei reintegri prioritari
    if request_data.prioritized_reintegrations: 
        print(f"Reintegri prioritari da richiesta API: {request_data.prioritized_reintegrations}")
    else:
        print("Nessun reintegro prioritario specificato nella richiesta API.")
    print("=" * 80)


    # Converti Pydantic model in dict per la funzione logica
    # Usa .dict() o .model_dump() a seconda della versione di Pydantic
    try:
        # Per Pydantic v1.x
        # colori_input_dict = [color.dict() for color in request_data.colors_today]
        # Per Pydantic v2.x
        colori_input_dict = [color.model_dump() for color in request_data.colors_today]
    except AttributeError:
         # Fallback se uno dei due metodi non esiste
         try:
              colori_input_dict = [color.dict() for color in request_data.colors_today]
         except AttributeError:
              print("Errore: Impossibile convertire modelli Pydantic in dizionari.")
              raise HTTPException(status_code=500, detail="Errore interno nella conversione dei dati di input.")


    try:
        # Verifica se ci sono colori con lunghezza_ordine per usare la logica delle cabine
        has_cabin_info = any(color.get('lunghezza_ordine') for color in colori_input_dict)
        
        if has_cabin_info:
            print("Rilevata informazione lunghezza_ordine, utilizzo della logica standard...")
            # Per ora usiamo la logica standard invece della logica cabine complessa
            ordered_colors_dict, cluster_seq, cost_num, message = logic.optimize_color_sequence(
                colori_giorno_input=colori_input_dict,
                start_cluster_nome=request_data.start_cluster_name,
                first_color=request_data.first_color,
                prioritized_reintegrations=request_data.prioritized_reintegrations
            )
            
            # Converti i dizionari risultato nel modello Pydantic per la risposta
            ordered_colors_output = [OptimizedColorOutput(**c) for c in ordered_colors_dict]
            
            # Gestisce costo infinito per la risposta JSON
            cost_str = "infinito" if cost_num >= INFINITE_COST else f"{cost_num:.2f}"
            
            response_data = OptimizationResponse(
                ordered_colors=ordered_colors_output,
                optimal_cluster_sequence=cluster_seq,
                calculated_cost=cost_str,
                message=message
            )
            
            print(f"[API] Invio risposta: {len(ordered_colors_output)} colori, {len(cluster_seq)} cluster, costo={cost_str}")
            return response_data
            
        # Verifica se ci sono sequenze con sequence_type per usare la nuova logica
        has_sequence_types = any(color.get('sequence_type') for color in colori_input_dict)
        
        if has_sequence_types:
            print("Rilevati tipi di sequenza, utilizzo della logica avanzata...")
            # Chiama la funzione che gestisce i tipi di sequenza (ora è un wrapper)
            ordered_colors_dict, cluster_seq, cost_num, message = logic.optimize_color_sequence_with_types(
                colors_input=colori_input_dict,
                start_cluster_nome=request_data.start_cluster_name,
                first_color=request_data.first_color,
                prioritized_reintegrations=request_data.prioritized_reintegrations
            )
        else:
            print("Nessun tipo di sequenza rilevato, utilizzo della logica standard...")
            # Chiama la funzione logica standard
            ordered_colors_dict, cluster_seq, cost_num, message = logic.optimize_color_sequence(
                colori_giorno_input=colori_input_dict,
                start_cluster_nome=request_data.start_cluster_name,
                first_color=request_data.first_color,
                prioritized_reintegrations=request_data.prioritized_reintegrations # Passa la lista
            )

        # Converti i dizionari risultato nel modello Pydantic per la risposta
        ordered_colors_output = [OptimizedColorOutput(**c) for c in ordered_colors_dict]

        # Formatta costo infinito per JSON
        # Usa il costo numerico restituito per il confronto
        cost_str = "infinito" if cost_num >= INFINITE_COST else f"{cost_num:.2f}"

        # Costruisci la risposta Pydantic
        response_data = OptimizationResponse(
            ordered_colors=ordered_colors_output,
            optimal_cluster_sequence=cluster_seq,
            calculated_cost=cost_str, # Usa la stringa formattata
            message=message
        )

        print(f"[API] Invio risposta: Costo={response_data.calculated_cost}, Seq={response_data.optimal_cluster_sequence}, Msg='{response_data.message}'")
        return response_data

    except HTTPException:
         raise # Rilancia le eccezioni HTTP già gestite (raro qui)
    except Exception as e:
        # Log dettagliato dell'errore inatteso nel backend
        print("="*30 + " ERRORE INATTESO IN API /optimize " + "="*30)
        print(f"Errore durante l'ottimizzazione: {e}")
        # Stampa lo stack trace completo nei log del backend per debug
        traceback.print_exc()
        print("="*80)
        # Restituisce un errore generico 500 al client
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno del server durante l'ottimizzazione. Controlla i log del backend per dettagli."
        )

@app.get("/", summary="Endpoint di Health Check")
async def read_root():
    """Endpoint di base per verificare che il servizio sia attivo."""
    return {"status": "Color Optimizer Backend running!"}

@app.post("/optimize-partial",
          summary="Ottimizza con ordine parziale dei cluster",
          description="Ottimizza rispettando un ordine parziale specificato dall'utente per i cluster.")
async def optimize_partial_sequence(request_data: dict = Body(...)):
    """
    Endpoint per ottimizzazione con ordine parziale dei cluster.
    """
    print("=" * 80)
    print("RICHIESTA OTTIMIZZAZIONE PARZIALE:")
    print(f"Request data: {request_data}")
    
    try:
        colors_data = request_data.get('colors', [])
        partial_order = request_data.get('partial_cluster_order', [])
        cabin_id = request_data.get('cabin_id', 1)
        prioritized_reintegrations = request_data.get('prioritized_reintegrations', [])
        
        if not colors_data:
            raise HTTPException(status_code=400, detail="Lista colori vuota")
        
        # Chiama la funzione di ottimizzazione parziale
        from .logic import optimize_with_partial_cluster_order
        
        ordered_colors, cluster_sequence, cost, message = optimize_with_partial_cluster_order(
            colori_giorno_input=colors_data,
            partial_cluster_order=partial_order,
            cabin_id=cabin_id,
            prioritized_reintegrations=prioritized_reintegrations
        )
        
        # Converti i risultati
        ordered_colors_output = [OptimizedColorOutput(**c) for c in ordered_colors]
        cost_str = "infinito" if cost >= INFINITE_COST else f"{cost:.2f}"
        
        response_data = OptimizationResponse(
            ordered_colors=ordered_colors_output,
            optimal_cluster_sequence=cluster_sequence,
            calculated_cost=cost_str,
            message=message
        )
        
        print(f"[API] Risposta ottimizzazione parziale: {len(ordered_colors)} colori, {len(cluster_sequence)} cluster")
        return response_data
        
    except Exception as e:
        print(f"Errore durante ottimizzazione parziale: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")

@app.post("/optimize-locked-colors",
          response_model=OptimizationResponse,
          summary="Ottimizzazione con colori bloccati individualmente",
          description="Ottimizza la sequenza considerando colori bloccati in posizioni specifiche")
async def optimize_locked_colors_sequence(request_data: dict = Body(...)):
    """
    Ottimizza la sequenza di colori rispettando i blocchi individuali.
    I colori bloccati mantengono la loro posizione, gli altri vengono ottimizzati.
    """
    try:
        print(f"[API] Richiesta ottimizzazione con colori bloccati: {request_data}")
        
        colors_today = request_data.get('colors_today', [])
        cabin_id = request_data.get('cabin_id', 1)
        prioritized_reintegrations = request_data.get('prioritized_reintegrations', [])
        
        if not colors_today:
            raise HTTPException(status_code=400, detail="Lista colori vuota")
        
        # Chiama la funzione di ottimizzazione con colori bloccati
        result = logic.optimize_with_locked_colors(colors_today)
        
        ordered_colors = result['colors']
        cluster_sequence = result['cluster_sequence']
        cost = result['cost']
        message = result['message']
        
        # Converte il risultato in OptimizedColorOutput
        ordered_colors_output = []
        for color in ordered_colors:
            color_output = OptimizedColorOutput(
                code=color.get("code", ""),
                type=color.get("type", ""),
                cluster=color.get("cluster"),
                sequence=color.get("sequence"),
                sequence_type=color.get("sequence_type"),
                CH=color.get("CH"),
                lunghezza_ordine=color.get("lunghezza_ordine"),
                locked=color.get("locked", False),
                position=color.get("position")
            )
            ordered_colors_output.append(color_output)
        
        # Gestisce costo infinito
        cost_str = "inf" if cost == float('inf') or cost >= INFINITE_COST else cost
        
        response_data = OptimizationResponse(
            ordered_colors=ordered_colors_output,
            optimal_cluster_sequence=cluster_sequence,
            calculated_cost=cost_str,
            message=message
        )
        
        print(f"[API] Risposta ottimizzazione con colori bloccati: {len(ordered_colors)} colori, {len(cluster_sequence)} cluster")
        return response_data
        
    except Exception as e:
        print(f"Errore durante ottimizzazione con colori bloccati: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")

@app.post("/update-color-lock",
          summary="Aggiorna stato di blocco di un colore",
          description="Blocca o sblocca un singolo colore nella lista della cabina")
async def update_color_lock(request_data: dict = Body(...)):
    """
    Aggiorna lo stato di blocco di un singolo colore.
    """
    try:
        print(f"[API] Richiesta aggiornamento blocco colore: {request_data}")
        
        cabin_id = request_data.get('cabin_id')
        color_index = request_data.get('color_index')
        locked = request_data.get('locked', False)
        
        if cabin_id is None or color_index is None:
            raise HTTPException(status_code=400, detail="cabin_id e color_index sono obbligatori")
        
        # Recupera la lista colori corrente
        colors_list = logic.get_colors_for_cabin(cabin_id)
        
        if not colors_list or color_index >= len(colors_list):
            raise HTTPException(status_code=404, detail="Colore non trovato")
        
        # Aggiorna lo stato di blocco
        colors_list[color_index]['locked'] = locked
        colors_list[color_index]['position'] = color_index if locked else None
        
        # Salva la lista aggiornata
        logic.save_colors_for_cabin(cabin_id, colors_list)
        
        color_code = colors_list[color_index].get('code', 'Unknown')
        action = "bloccato" if locked else "sbloccato"
        
        return {
            "success": True,
            "message": f"Colore {color_code} {action} con successo",
            "color_index": color_index,
            "locked": locked
        }
        
    except Exception as e:
        print(f"Errore durante aggiornamento blocco colore: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")

@app.post("/update-cluster-lock",
          summary="Aggiorna stato di blocco di un cluster",
          description="Blocca o sblocca tutti i colori di un cluster")
async def update_cluster_lock(request_data: dict = Body(...)):
    """
    Aggiorna lo stato di blocco di tutti i colori di un cluster.
    """
    try:
        print(f"[API] Richiesta aggiornamento blocco cluster: {request_data}")
        
        cabin_id = request_data.get('cabin_id')
        cluster_name = request_data.get('cluster_name')
        locked = request_data.get('locked', False)
        
        if cabin_id is None or not cluster_name:
            raise HTTPException(status_code=400, detail="cabin_id e cluster_name sono obbligatori")
        
        # Recupera la lista colori corrente
        colors_list = logic.get_colors_for_cabin(cabin_id)
        
        if not colors_list:
            raise HTTPException(status_code=404, detail="Nessun colore trovato per la cabina")
        
        # Aggiorna lo stato di blocco per tutti i colori del cluster
        updated_count = 0
        for i, color in enumerate(colors_list):
            if color.get('cluster') == cluster_name:
                color['locked'] = locked
                color['position'] = i if locked else None
                updated_count += 1
        
        # Salva la lista aggiornata
        logic.save_colors_for_cabin(cabin_id, colors_list)
        
        action = "bloccati" if locked else "sbloccati"
        
        return {
            "success": True,
            "message": f"Cluster {cluster_name}: {updated_count} colori {action}",
            "cluster_name": cluster_name,
            "locked": locked,
            "updated_count": updated_count
        }
        
    except Exception as e:
        print(f"Errore durante aggiornamento blocco cluster: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")

@app.post("/reorder-colors",
          summary="Riordina i colori con drag & drop",
          description="Aggiorna l'ordine dei colori dopo drag & drop")
async def reorder_colors(request_data: dict = Body(...)):
    """
    Riordina i colori secondo il nuovo ordine specificato dall'utente.
    """
    try:
        print(f"[API] Richiesta riordino colori: {request_data}")
        
        cabin_id = request_data.get('cabin_id')
        new_order = request_data.get('new_order', [])  # Lista di indici nel nuovo ordine
        
        if cabin_id is None:
            raise HTTPException(status_code=400, detail="cabin_id è obbligatorio")
        
        if not new_order:
            raise HTTPException(status_code=400, detail="new_order non può essere vuoto")
        
        # Recupera la lista colori corrente
        colors_list = logic.get_colors_for_cabin(cabin_id)
        
        if not colors_list:
            raise HTTPException(status_code=404, detail="Nessun colore trovato per la cabina")
        
        if len(new_order) != len(colors_list):
            raise HTTPException(status_code=400, detail="La lunghezza del nuovo ordine non corrisponde al numero di colori")
        
        # Riordina i colori secondo il nuovo ordine
        reordered_colors = []
        for new_index, old_index in enumerate(new_order):
            if 0 <= old_index < len(colors_list):
                color = colors_list[old_index].copy()
                color['position'] = new_index
                reordered_colors.append(color)
            else:
                raise HTTPException(status_code=400, detail=f"Indice non valido: {old_index}")
        
        # Salva la lista riordinata
        logic.save_colors_for_cabin(cabin_id, reordered_colors)
        
        return {
            "success": True,
            "message": f"Riordinati {len(reordered_colors)} colori per cabina {cabin_id}",
            "cabin_id": cabin_id,
            "colors_count": len(reordered_colors)
        }
        
    except Exception as e:
        print(f"Errore durante riordino colori: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")

@app.post("/api/cabin/{cabin_id}/optimize-locked")
async def optimize_cabin_with_locks(cabin_id: int, request_data: dict = Body(...)):
    """
    Ottimizza la sequenza di colori per una cabina specifica rispettando i blocchi 
    e salva i risultati nel database.
    """
    try:
        print(f"[API] Ottimizzazione cabina {cabin_id} con blocchi: {request_data}")
        
        colors_today = request_data.get('colors_today', [])
        prioritized_reintegrations = request_data.get('prioritized_reintegrations', [])
        
        if not colors_today:
            raise HTTPException(status_code=400, detail="Lista colori vuota")
        
        # Prima ottimizza la sequenza rispettando i blocchi
        result = logic.optimize_with_locked_colors(colors_today)
        
        ordered_colors = result['colors']
        cluster_sequence = result['cluster_sequence']
        cost = result['cost']
        message = result['message']
        
        print(f"[API] Ottimizzazione completata, salvando {len(ordered_colors)} colori per cabina {cabin_id}")
        
        # Ora salva i risultati nel database
        # Converte i colori ottimizzati nel formato per il salvataggio
        colors_to_save = []
        for i, color in enumerate(ordered_colors):
            color_dict = {
                'color_code': color.get('code', ''),
                'color_type': color.get('type', ''),
                'cluster': color.get('cluster', ''),
                'ch_value': color.get('CH', ''),
                'lunghezza_ordine': color.get('lunghezza_ordine', ''),
                'input_sequence': color.get('sequence', ''),
                'sequence_type': color.get('sequence_type', ''),
                'locked': color.get('locked', False),
                'sequence_order': i + 1  # Posizione nella sequenza ottimizzata
            }
            colors_to_save.append(color_dict)
        
        # Salva nel database
        logic.save_colors_for_cabin(cabin_id, colors_to_save)
        
        print(f"[API] Colori salvati nel database per cabina {cabin_id}")
        
        return {
            "success": True,
            "message": f"Ottimizzazione completata e salvata: {message}",
            "cabin_id": cabin_id,
            "colors_count": len(ordered_colors),
            "cluster_count": len(cluster_sequence),
            "cost": cost if cost != float('inf') else "infinito"
        }
        
    except Exception as e:
        print(f"Errore durante ottimizzazione cabina {cabin_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")

@app.get("/api/cabin/{cabin_id}/colors")
async def get_cabin_colors(cabin_id: int):
    """
    Ottiene tutti i colori per una cabina specifica dal database.
    """
    try:
        print(f"[API] Richiesta colori per cabina {cabin_id}")
        
        # Legge i colori dal database usando la funzione di logic
        colors = logic.get_colors_for_cabin(cabin_id)
        
        print(f"[API] Trovati {len(colors)} colori per cabina {cabin_id}")
        
        return {
            "success": True,
            "cabin_id": cabin_id,
            "colors": colors,
            "count": len(colors)
        }
        
    except Exception as e:
        print(f"Errore durante recupero colori cabina {cabin_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")

@app.post("/api/cabin/{cabin_id}/apply-cluster-order")
async def apply_cluster_order_to_cabin(cabin_id: int, request_data: dict = Body(...)):
    """
    Applica un ordine specifico dei cluster riorganizzando tutti i colori della cabina.
    """
    try:
        print(f"[API] Applicazione ordine cluster per cabina {cabin_id}: {request_data}")
        
        cluster_order = request_data.get('cluster_order', [])
        current_colors = request_data.get('colors', [])
        
        if not cluster_order:
            raise HTTPException(status_code=400, detail="Ordine cluster non specificato")
        
        if not current_colors:
            # Se non ci sono colori nel request, li carica dal database
            current_colors = logic.get_colors_for_cabin(cabin_id)
        
        if not current_colors:
            raise HTTPException(status_code=404, detail="Nessun colore trovato per la cabina")
        
        print(f"[API] Riorganizzando {len(current_colors)} colori secondo ordine cluster: {cluster_order}")
        
        # Riorganizza i colori secondo l'ordine cluster
        reorganized_colors = logic.reorganize_colors_by_cluster_order(current_colors, cluster_order)
        
        # Salva la nuova organizzazione nel database
        logic.save_colors_for_cabin(cabin_id, reorganized_colors)
        
        print(f"[API] Colori riorganizzati e salvati per cabina {cabin_id}")
        
        return {
            "success": True,
            "message": f"Ordine cluster applicato: {len(reorganized_colors)} colori riorganizzati",
            "cabin_id": cabin_id,
            "colors_count": len(reorganized_colors),
            "cluster_order": cluster_order
        }
        
    except Exception as e:
        print(f"Errore durante applicazione ordine cluster cabina {cabin_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")