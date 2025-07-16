#!/bin/bash
# Script per avviare frontend e backend contemporaneamente

echo "🚀 Avvio del sistema di ottimizzazione colori..."

# Funzione per pulire i processi alla chiusura
cleanup() {
    echo "🛑 Arresto dei servizi..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit 0
}

# Intercetta SIGINT (Ctrl+C) e SIGTERM
trap cleanup SIGINT SIGTERM

# Avvia il backend
echo "🔧 Avvio backend (porta 8001)..."
cd backend
python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0 &
BACKEND_PID=$!
cd ..

# Aspetta che il backend si avvii
sleep 3

# Verifica che il backend sia attivo
if curl -s http://localhost:8001/docs > /dev/null; then
    echo "✅ Backend avviato con successo su http://localhost:8001"
else
    echo "❌ Errore nell'avvio del backend"
    cleanup
fi

# Avvia il frontend
echo "🎨 Avvio frontend (porta 5001)..."
cd frontend
python app/main.py &
FRONTEND_PID=$!
cd ..

# Aspetta che il frontend si avvii
sleep 3

# Verifica che il frontend sia attivo
if curl -s http://localhost:5001 > /dev/null; then
    echo "✅ Frontend avviato con successo su http://localhost:5001"
else
    echo "❌ Errore nell'avvio del frontend"
    cleanup
fi

echo ""
echo "🎉 Entrambi i servizi sono attivi!"
echo "📊 Frontend: http://localhost:5001"
echo "🔧 Backend API: http://localhost:8001"
echo "📚 Documentazione API: http://localhost:8001/docs"
echo ""
echo "Premi Ctrl+C per arrestare entrambi i servizi"

# Mantieni lo script in esecuzione
wait
