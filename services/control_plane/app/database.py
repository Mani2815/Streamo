import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

def _normalize_database_url(database_url: str) -> str:
    normalized = database_url.strip()

    if (normalized.startswith('"') and normalized.endswith('"')) or (
        normalized.startswith("'") and normalized.endswith("'")
    ):
        normalized = normalized[1:-1].strip()

    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql+psycopg2://", 1)
    elif normalized.startswith("postgresql://"):
        normalized = normalized.replace("postgresql://", "postgresql+psycopg2://", 1)

    return normalized

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL = _normalize_database_url(DATABASE_URL) if DATABASE_URL else None

engine = None
SessionLocal = None

if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    except Exception as e:
        print(f"Warning: Failed to initialize database engine: {e}")

Base = declarative_base()

def get_db():
    if SessionLocal is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database is not configured or unavailable.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
