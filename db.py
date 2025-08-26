from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from flask import g

engine = None
SessionLocal = None
Base = declarative_base()

def init_engine_and_session(database_url: str):
    global engine, SessionLocal
    if engine is None:
        engine = create_engine(database_url, future=True)
        SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True))

def get_db():
    # Request-scoped session via Flask's g
    if 'db' not in g:
        if SessionLocal is None:
            raise RuntimeError("Database not initialized. Call init_engine_and_session first.")
        g.db = SessionLocal()
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    from models import TippingGame, Member, PaymentMethod, VictoryStatus, PointsStatus  # noqa: F401
    Base.metadata.create_all(bind=engine)
