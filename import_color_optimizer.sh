#!/bin/bash

# Script per importare e avviare Color Optimizer su una nuova macchina
# Uso: ./import_color_optimizer.sh

echo "🚀 Importazione Color Optimizer"
echo "================================"

# Verifica che Docker sia installato
if ! command -v docker &> /dev/null; then
    echo "❌ Docker non è installato. Installalo prima di continuare."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose non è installato. Installalo prima di continuare."
    exit 1
fi

# Importa le immagini Docker
if [ -f "color-optimizer-export.tar" ]; then
    echo "📦 Importazione immagini Docker..."
    docker load -i color-optimizer-export.tar
    echo "✅ Immagini importate con successo"
else
    echo "❌ File color-optimizer-export.tar non trovato!"
    echo "   Assicurati che il file sia nella stessa directory dello script."
    exit 1
fi

# Verifica che le immagini siano state importate
echo "🔍 Verifica immagini importate:"
docker images | grep -E "(swdevel-lab-hfarm-mastercopy|color-optimizer)"

# Avvia i container
echo "🚀 Avvio dei container..."
docker-compose up -d

# Attendi che i servizi siano pronti
echo "⏳ Attendo che i servizi siano pronti..."
sleep 10

# Verifica lo stato dei container
echo "📊 Stato dei container:"
docker-compose ps

echo ""
echo "🎉 Installazione completata!"
echo "================================"
echo "Frontend: http://localhost:8080"
echo "Backend:  http://localhost:8000"
echo ""
echo "Per vedere i log:"
echo "  docker-compose logs -f"
echo ""
echo "Per fermare i servizi:"
echo "  docker-compose down"
