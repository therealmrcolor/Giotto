# backend/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copia prima requirements per sfruttare cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto dell'applicazione
COPY ./app /app/app

# Crea la directory per il DB se non esiste (anche se il volume la monterà)
RUN mkdir -p /app/app/data

EXPOSE 80

# Comando per avviare l'applicazione FastAPI con Uvicorn
# --reload è utile per sviluppo, rimuovilo per produzione
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]