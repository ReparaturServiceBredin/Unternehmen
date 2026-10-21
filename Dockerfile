# Reparatur Service Bredin – Buchhaltung als Server (Linux/Docker)
# Bauen:   docker build -t rsb-buchhaltung .
# Starten: docker compose up -d   (siehe docs/BETRIEB_SERVER.md)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    TZ=Europe/Berlin \
    RSB_MODUS=server \
    RSB_DATEN=/daten \
    RSB_HOST=0.0.0.0 \
    RSB_PORT=5000

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rsb ./rsb
COPY docs/AENDERUNGEN.md ./docs/AENDERUNGEN.md

# Ohne Root-Rechte laufen; Daten liegen im Volume /daten
RUN useradd --system --uid 1000 --create-home rsb \
    && mkdir -p /daten && chown rsb:rsb /daten
USER rsb
VOLUME ["/daten"]
EXPOSE 5000

HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('RSB_PORT', '5000') + '/version', timeout=4)"

# Ein Prozess (Waitress mit Threads); SIGTERM schließt die Datenbank sauber
STOPSIGNAL SIGTERM
CMD ["python", "-m", "rsb"]
