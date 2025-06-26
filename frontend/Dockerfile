# frontend/Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app

EXPOSE 80

# Variabile d'ambiente per specificare l'URL del backend
# Può essere sovrascritta da docker-compose.yml
ENV FASTAPI_BACKEND_URL=http://backend
# Chiave segreta per Flask (meglio sovrascriverla in docker-compose)
ENV FLASK_SECRET_KEY=default-secret-key-change-me

# Imposta variabili d'ambiente per Flask
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.main:app \
    FLASK_DEBUG=1 \
    FLASK_ENV=development

# Crea una directory per i dati condivisi (verrà montata in fase di esecuzione)
RUN mkdir -p /app/app/data

# Comando per avviare l'applicazione Flask
# Specifica il modulo e l'oggetto app usando l'opzione --app
CMD ["flask", "run", "--host=0.0.0.0", "--port=80", "--debug"]
# Per produzione (dopo aver aggiunto gunicorn a requirements.txt):
# CMD ["gunicorn", "-w 4", "-b 0.0.0.0:80", "app.main:app"]