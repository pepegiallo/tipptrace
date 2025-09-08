from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from flask import g

engine = None
SessionLocal = None
Base = declarative_base()


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite:")


def init_engine_and_session(database_url: str):
    """
    Initialisiert die globale Engine/Session.
    - pool_pre_ping für stabile Verbindungen (wichtig bei Cloud-DBs wie Supabase)
    - SQLite: check_same_thread=False für Flask-Threading
    """
    global engine, SessionLocal
    if engine is not None:
        return

    engine_kwargs = {
        "future": True,
        "pool_pre_ping": True,
    }

    if _is_sqlite(database_url):
        # SQLite: mehr Toleranz für parallele Threads (Gunicorn-Worker sprechen je eigenen Prozess)
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(database_url, **engine_kwargs)
    SessionLocal = scoped_session(
        sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    )


def get_db():
    # Request-scoped session via Flask's g
    if "db" not in g:
        if SessionLocal is None:
            raise RuntimeError("Database not initialized. Call init_engine_and_session first.")
        g.db = SessionLocal()
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    # Import der Modelle registriert die Tabellen am Base.metadata
    from models import TippingGame, Member, PaymentMethod, VictoryStatus, PointsStatus  # noqa: F401
    Base.metadata.create_all(bind=engine)
