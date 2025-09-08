import os
from typing import Tuple
try:
    # Deine App ist laut README unter "app:app" erreichbar. :contentReference[oaicite:2]{index=2}
    from app import app as _app
except Exception as e:
    # Fallback für klare Fehlermeldung im Container-Log
    raise RuntimeError(f"Could not import 'app:app': {e}")

app = _app  # von Gunicorn als wsgi:app verwendet
