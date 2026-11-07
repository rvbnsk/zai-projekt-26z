import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "schema.sql"


def database_url():
    url = os.environ["DATABASE_URL"]
    # Hosting providers give "postgresql://", SQLAlchemy needs the driver name.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_schema():
    with engine.begin() as conn:
        conn.exec_driver_sql(SCHEMA_FILE.read_text(encoding="utf-8"))
