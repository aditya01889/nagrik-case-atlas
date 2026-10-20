import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_raw_database_url = os.getenv("DATABASE_URL", "").strip()
if os.getenv("VERCEL") == "1" and not _raw_database_url:
    raise RuntimeError("DATABASE_URL is required on Vercel; configure a persistent PostgreSQL database.")

if _raw_database_url.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + _raw_database_url[len("postgres://"):]
elif _raw_database_url.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + _raw_database_url[len("postgresql://"):]
elif _raw_database_url:
    DATABASE_URL = _raw_database_url
else:
    # Local development fallback only. SQLite is ephemeral on serverless platforms.
    DATABASE_URL = "sqlite:///./explorer.db"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
