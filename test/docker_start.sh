#!/bin/bash

# Color Optimizer - Docker Launcher
# Avvia il sistema di ottimizzazione colori con Docker

set -e

echo "🎨 Color Sequence Optimizer - Docker Setup"
echo "=========================================="

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per logging colorato
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verifica prerequisiti
check_prerequisites() {
    log "Verifico prerequisiti..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker non è installato. Installalo da: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose non è installato."
        exit 1
    fi
    
    log "✅ Prerequisiti verificati"
}

# Verifica porte
check_ports() {
    log "Verifico disponibilità porte..."
    
    if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
        warn "Porta 8080 già in uso. Fermerò il processo esistente."
        pkill -f ":8080" || true
    fi
    
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        warn "Porta 8000 già in uso. Fermerò il processo esistente."
        pkill -f ":8000" || true
    fi
    
    log "✅ Porte disponibili"
}

# Avvia servizi
start_services() {
    log "Avvio servizi Docker..."
    
    # Ferma container esistenti se presenti
    docker-compose down 2>/dev/null || true
    
    # Costruisci e avvia
    log "Costruzione immagini Docker..."
    docker-compose build --no-cache
    
    log "Avvio container..."
    docker-compose up -d
    
    # Attendi che i servizi siano pronti
    log "Attendo che i servizi siano pronti..."
    sleep 5
    
    # Verifica salute servizi
    for i in {1..30}; do
        if curl -s http://localhost:8080 >/dev/null 2>&1 && curl -s http://localhost:8000/docs >/dev/null 2>&1; then
            log "✅ Servizi avviati con successo!"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Timeout: i servizi non rispondono dopo 30 secondi"
            docker-compose logs
            exit 1
        fi
        echo -n "."
        sleep 1
    done
}

# Test funzionamento
run_tests() {
    log "Eseguo test di verifica..."
    
    if python3 test_docker_setup.py; then
        log "✅ Tutti i test passati!"
    else
        warn "Alcuni test sono falliti, ma i servizi sono attivi"
    fi
}

# Mostra informazioni finali
show_info() {
    echo ""
    echo -e "${BLUE}🎉 Setup completato!${NC}"
    echo "======================="
    echo ""
    echo -e "${GREEN}📋 Servizi disponibili:${NC}"
    echo "  • Frontend (Web UI):     http://localhost:8080"
    echo "  • Backend (API docs):    http://localhost:8000/docs"
    echo "  • Backend (API):         http://localhost:8000"
    echo ""
    echo -e "${GREEN}🛠️ Comandi utili:${NC}"
    echo "  • Logs frontend:         docker-compose logs frontend"
    echo "  • Logs backend:          docker-compose logs backend"
    echo "  • Ferma servizi:         docker-compose down"
    echo "  • Riavvia:               docker-compose restart"
    echo ""
    echo -e "${GREEN}📖 Documentazione:${NC}"
    echo "  • Setup Docker:          DOCKER_SETUP.md"
    echo "  • README:                README.md"
    echo ""
}

# Menu principale
main() {
    case "${1:-start}" in
        "start")
            check_prerequisites
            check_ports
            start_services
            run_tests
            show_info
            ;;
        "stop")
            log "Fermo i servizi..."
            docker-compose down
            log "✅ Servizi fermati"
            ;;
        "restart")
            log "Riavvio i servizi..."
            docker-compose down
            docker-compose up -d
            log "✅ Servizi riavviati"
            ;;
        "logs")
            docker-compose logs -f
            ;;
        "test")
            run_tests
            ;;
        "clean")
            log "Pulizia completa..."
            docker-compose down -v --rmi all
            log "✅ Pulizia completata"
            ;;
        "help"|"-h"|"--help")
            echo "Uso: $0 [comando]"
            echo ""
            echo "Comandi disponibili:"
            echo "  start     Avvia i servizi (default)"
            echo "  stop      Ferma i servizi"
            echo "  restart   Riavvia i servizi"
            echo "  logs      Mostra i logs in real-time"
            echo "  test      Esegue i test di verifica"
            echo "  clean     Pulizia completa (rimuove tutto)"
            echo "  help      Mostra questo messaggio"
            ;;
        *)
            error "Comando sconosciuto: $1"
            echo "Usa '$0 help' per vedere i comandi disponibili"
            exit 1
            ;;
    esac
}

# Gestione Ctrl+C
trap 'echo ""; warn "Operazione interrotta"; exit 130' INT

# Esegui funzione principale
main "$@"
