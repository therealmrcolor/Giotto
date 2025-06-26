# Docker Setup per Color Optimizer

## 🐳 Setup Docker Completo

Questo progetto è ora completamente configurato per funzionare con Docker. Tutti i path e le configurazioni sono stati aggiornati per l'ambiente containerizzato.

## 📋 Prerequisiti

- Docker e Docker Compose installati
- Porte 8000 e 8080 disponibili sul sistema host

## 🚀 Avvio Rapido

### 1. Arresta tutti i servizi esistenti
```bash
# Se hai servizi in esecuzione localmente, fermali
pkill -f "flask run"
pkill -f "uvicorn"
```

### 2. Avvia con Docker
```bash
# Costruisci e avvia i container
docker-compose up --build

# Oppure in background
docker-compose up --build -d
```

### 3. Verifica il funzionamento
```bash
# Esegui il test automatico
python test_docker_setup.py
```

## 🌐 Servizi Disponibili

- **Frontend (Flask)**: http://localhost:8080
- **Backend API (FastAPI)**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📁 Struttura Volumi

- `./shared/data` → `/app/app/data` (database condiviso)
- `./frontend/app` → `/app/app` (codice frontend per development)
- `./backend/app` → `/app/app` (codice backend per development)

## 🔧 Configurazione

### Variabili d'Ambiente

#### Frontend
- `DATABASE_PATH`: `/app/app/data/colors.db`
- `FASTAPI_BACKEND_URL`: `http://backend`
- `FLASK_SECRET_KEY`: Chiave segreta Flask
- `FLASK_DEBUG`: `1` (modalità debug)

#### Backend
- `DATABASE_PATH`: `/app/app/data/colors.db`

### Database

Il database SQLite è condiviso tra frontend e backend tramite il volume `./shared/data`. Durante l'avvio, se necessario, vengono create automaticamente le tabelle mancanti:

- `cambio_colori` - Regole di transizione tra cluster
- `cluster_colori` - Mapping colori-cluster  
- `saved_sequences` - Sequenze salvate
- `optimization_colors` - Colori per ottimizzazione

## 🛠️ Comandi Utili

### Gestione Container
```bash
# Visualizza logs
docker-compose logs frontend
docker-compose logs backend

# Riavvia servizi
docker-compose restart

# Ferma tutto
docker-compose down

# Rebuild completo
docker-compose down && docker-compose up --build
```

### Debug Database
```bash
# Accedi al container frontend
docker exec -it color-optimizer-frontend bash

# Accedi al container backend  
docker exec -it color-optimizer-backend bash

# Test connessione database
docker exec color-optimizer-backend python -c "from app.database import connect_to_db; print('DB OK:', connect_to_db() is not None)"
```

### Sviluppo

I volumi sono configurati per il live-reload:
- **Frontend**: Flask si riavvia automaticamente quando modifichi file in `frontend/app/`
- **Backend**: Uvicorn si riavvia automaticamente quando modifichi file in `backend/app/`

## 🔍 Troubleshooting

### Container non si avviano
```bash
# Controlla i logs
docker-compose logs

# Verifica le porte
lsof -i :8080
lsof -i :8000
```

### Database non accessibile
```bash
# Verifica i permessi del volume
ls -la shared/data/

# Test connessione
docker exec color-optimizer-frontend python -c "from app.main import connect_to_db; print(connect_to_db())"
```

### API non risponde
```bash
# Test diretto backend
curl http://localhost:8000/docs

# Test comunicazione frontend-backend
docker exec color-optimizer-frontend curl http://backend/docs
```

## 📈 Monitoring

### Health Checks
```bash
# Test automatico completo
python test_docker_setup.py

# Test API manuale
curl -X POST http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"colors_today": [{"code": "RAL1019", "type": "R"}], "start_cluster_name": "Bianco", "prioritized_reintegrations": []}'
```

### Log Monitoring
```bash
# Segui i logs in real-time
docker-compose logs -f frontend
docker-compose logs -f backend
```

## 🔐 Sicurezza

- La chiave segreta Flask è configurata tramite variabile d'ambiente
- CSRF è disabilitato per testing (riabilitare in produzione)
- I container non hanno privilegi elevati

## 🚢 Produzione

Per l'uso in produzione:

1. **Rimuovi il flag `--reload`** dai Dockerfile
2. **Abilita CSRF** nel frontend
3. **Usa un web server** come Nginx davanti ai container
4. **Configura HTTPS**
5. **Imposta segreti sicuri**

```yaml
# Esempio docker-compose.prod.yml
environment:
  - FLASK_DEBUG=0
  - FLASK_ENV=production
```

## ✅ Test Copertura

Il setup è testato per:
- ✅ Connettività frontend-backend
- ✅ Accesso database condiviso
- ✅ API di ottimizzazione
- ✅ Interfaccia web
- ✅ Live-reload sviluppo

Tutto funziona correttamente in ambiente Docker!
