"""SQLite database configuration.

Database URL is read from the DATABASE_URL environment variable (with
a sensible default for development). When using SQLite, the database
file is resolved relative to DATA_DIR so it lives outside the source
tree.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Resolve settings from environment. Imported lazily to avoid pulling
# pydantic-settings during test collection when only the engine is needed.
try:
    from app.core.config import settings as _settings

    DATABASE_URL = os.getenv("DATABASE_URL") or _settings.DATABASE_URL
    _data_dir = _settings.DATA_DIR
except Exception:  # pragma: no cover - fallback for minimal env
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./actap.db")
    _data_dir = os.getenv("DATA_DIR", "./data")

# When using SQLite, ensure the data directory exists and the DB file
# lives inside it (out of the source tree).
if DATABASE_URL.startswith("sqlite:///"):
    _db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    if not os.path.isabs(_db_path):
        os.makedirs(_data_dir, exist_ok=True)
        _db_path = os.path.join(_data_dir, os.path.basename(_db_path))
        DATABASE_URL = f"sqlite:///{_db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
