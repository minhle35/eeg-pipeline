import os
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://eeg:eegpass@localhost:5432/eeg_pipeline",
)

# SQLite in-memory needs StaticPool so all connections share the same database
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a session, closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables from SQLAlchemy models."""
    from pipeline.models import EegSample, IngestionLog  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("Database initialized with tables: ", Base.metadata.tables.keys())
