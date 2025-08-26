# Tipptrace

**Allgemein**

Webanwendung zur Verwaltung von Tippspielen. Es können mehrere Tippspiele mit Mitgliedern, Einsätzen, Auszahlungstöpfen und Auszahlungsverteilung angelegt werden.
Die Spieltagssiege und Punkte müssen manuell gepflegt werden.

## Start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install flask sqlalchemy

# App starten
export FLASK_APP=app.py         # Windows PowerShell: $env:FLASK_APP="app.py"
export FLASK_ENV=development    # optional
python app.py
# oder: flask run
```

## Deployment Raspberry PI

**Setup**

```bash
#!/usr/bin/env bash
set -euo pipefail

# === Einstellungen (bei Bedarf anpassen) ===
APP_USER="tipptrace"
APP_NAME="tipptrace"
APP_REPO_URL="https://github.com/pepegiallo/tipptrace.git"
APP_DIR="/opt/${APP_NAME}"
PY_ENV="${APP_DIR}/.venv"
BIND_IP="0.0.0.0"
BIND_PORT="8000"
LOG_DIR="/var/log/${APP_NAME}"
DATA_DIR="/var/lib/${APP_NAME}"   # falls die App z.B. SQLite-Dateien anlegt
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

# === Root-Check ===
if [[ "$EUID" -ne 0 ]]; then
  echo "Bitte als root ausführen (sudo -s)."
  exit 1
fi

echo "[1/9] Systempakete installieren…"
apt-get update -y
apt-get install -y --no-install-recommends \
  python3 python3-venv python3-pip git

echo "[2/9] Systemnutzer anlegen…"
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "${APP_USER}"
fi

echo "[3/9] Verzeichnisse anlegen…"
mkdir -p "${APP_DIR}" "${LOG_DIR}" "${DATA_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}" "${LOG_DIR}" "${DATA_DIR}"
chmod 750 "${APP_DIR}" "${DATA_DIR}"
chmod 750 "${LOG_DIR}"

echo "[4/9] Repository klonen/aktualisieren…"
if [[ ! -d "${APP_DIR}/.git" ]]; then
  sudo -u "${APP_USER}" git clone "${APP_REPO_URL}" "${APP_DIR}"
else
  pushd "${APP_DIR}" >/dev/null
  sudo -u "${APP_USER}" git fetch --all
  sudo -u "${APP_USER}" git reset --hard origin/$(sudo -u "${APP_USER}" git rev-parse --abbrev-ref HEAD || echo main)
  popd >/dev/null
fi

echo "[5/9] Python venv & Requirements…"
sudo -u "${APP_USER}" python3 -m venv "${PY_ENV}"
# neuere pip/wheel (ARM-kompatibel)
sudo -u "${APP_USER}" "${PY_ENV}/bin/pip" install --upgrade pip wheel
# Minimal-Requirements laut Vorgabe + Gunicorn als WSGI-Server
sudo -u "${APP_USER}" "${PY_ENV}/bin/pip" install flask sqlalchemy gunicorn

# Falls im Repo eine eigene requirements.txt liegt, alternativ:
if [[ -f "${APP_DIR}/requirements.txt" ]]; then
  sudo -u "${APP_USER}" "${PY_ENV}/bin/pip" install -r "${APP_DIR}/requirements.txt" || true
fi

echo "[6/9] WSGI-Einstiegspunkt erzeugen (falls nicht vorhanden)…"
# Wir erstellen eine robuste wsgi.py, die eine 'app' findet.
WSGI_FILE="${APP_DIR}/wsgi.py"
if [[ ! -f "${WSGI_FILE}" ]]; then
  cat > "${WSGI_FILE}" << 'PYEOF'
import importlib, os, sys

BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# mögliche Kandidaten-Module, die eine Flask-Instanz 'app' enthalten könnten
candidates = [
    ("app", "app"),                # app.py -> app
    ("wsgi", "app"),               # falls bereits vorhanden
    ("tipptrace", "app"),          # Paket tipptrace -> app
    ("run", "app"),                # run.py -> app
]

app = None
last_err = None
for mod_name, attr in candidates:
    try:
        m = importlib.import_module(mod_name)
        app = getattr(m, attr)
        break
    except Exception as e:
        last_err = e
        continue

if app is None:
    raise RuntimeError("Konnte keine Flask-App 'app' finden. Zuletzt: %r" % (last_err,))
PYEOF
  chown "${APP_USER}:${APP_USER}" "${WSGI_FILE}"
fi

echo "[7/9] Logfiles vorbereiten…"
# Gunicorn schreibt Access & Error Logs hierhin
touch "${LOG_DIR}/access.log" "${LOG_DIR}/error.log"
chown "${APP_USER}:${APP_USER}" "${LOG_DIR}/access.log" "${LOG_DIR}/error.log"
chmod 640 "${LOG_DIR}/access.log" "${LOG_DIR}/error.log"

echo "[8/9] systemd Service schreiben…"
cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=${APP_NAME} Flask Webapp (Gunicorn)
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
# Wenn du eine DB-URL setzen willst, hier als Beispiel (auskommentiert lassen, bis benötigt):
# Environment=SQLALCHEMY_DATABASE_URI=sqlite:////${DATA_DIR}/app.db
ExecStart=${PY_ENV}/bin/gunicorn --workers 2 --bind ${BIND_IP}:${BIND_PORT} \\
  --access-logfile ${LOG_DIR}/access.log --error-logfile ${LOG_DIR}/error.log \\
  wsgi:app
Restart=always
RestartSec=5

# Gib Gunicorn ein paar offene Files/Conns
LimitNOFILE=4096

[Install]
WantedBy=multi-user.target
EOF

echo "[9/9] Service aktivieren & starten…"
systemctl daemon-reload
systemctl enable "${APP_NAME}.service"
systemctl restart "${APP_NAME}.service"

echo "-------------------------------------------"
echo "Deployment fertig."
echo "Service-Status:    systemctl status ${APP_NAME}.service"
echo "Logs (Error):      tail -f ${LOG_DIR}/error.log"
echo "Logs (Access):     tail -f ${LOG_DIR}/access.log"
echo "HTTP erreichbar:   http://${BIND_IP}:${BIND_PORT}"
echo "Codepfad:          ${APP_DIR}"
echo "Datenverz.:        ${DATA_DIR}"
echo "-------------------------------------------"
```

**Status prüfen**
```bash
systemctl status tipptrace.service
```

**Update auf neue Repo-Version**
```bash
sudo -s
cd /opt/tipptrace
sudo -u tipptrace git pull
sudo systemctl restart tipptrace.service
```


