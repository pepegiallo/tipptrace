# Tippspiel Webanwendung (Flask + SQLAlchemy)

**Vorgaben erfüllt:**

- Flask + **normales** SQLAlchemy (kein `flask_sqlalchemy`)
- Modelle: Tippspiel, Mitglied, Zahlungsart (1:1 zum Mitglied), Siege-Status, Punkte-Status
- Gesamteinsatz = Einsatz/Person × Mitgliederanzahl (berechnet)
- Neuster Punkte- und Siege-Status je Mitglied wird angezeigt
- Frontend in **Bootstrap**; deutschsprachige UI, englische Bezeichner im Code
- **Dynamische Formulare**: Jeweils ein Formular-Template fürs Anlegen & Bearbeiten
- **Blueprints**: `main`, `games`, `members`

## Start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# App starten
export FLASK_APP=app.py         # Windows PowerShell: $env:FLASK_APP="app.py"
export FLASK_ENV=development    # optional
python app.py
# oder: flask run
