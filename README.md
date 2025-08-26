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

