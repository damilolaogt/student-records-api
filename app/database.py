"""
database.py
──────────────────────────────────────────────────────────────────────────────
SQLAlchemy 2.0 engine, session factory, and declarative base.

Connection parameters are read exclusively from the DATABASE_URL environment
variable (populated via python-dotenv from a local .env file).  All other
modules must import `SessionLocal` for dependency injection and `Base` for
model inheritance.
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ---------------------------------------------------------------------------
# Load .env before reading environment variables
# ---------------------------------------------------------------------------
load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]

# ---------------------------------------------------------------------------
# Engine with connection pool tuned for a typical web-service workload
# ---------------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    # Pool settings
    pool_size=10,          # persistent connections kept in pool
    max_overflow=20,       # extra connections allowed beyond pool_size
    pool_pre_ping=True,    # check connection liveness before handing it out
    pool_recycle=1800,     # recycle connections after 30 minutes
    echo=False,            # set True locally to log generated SQL
)


# ---------------------------------------------------------------------------
# Session factory – never import Session from SQLAlchemy directly in routes;
# always obtain it through the `get_db` dependency.
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # avoids lazy-load errors after commit
)


# ---------------------------------------------------------------------------
# Declarative base – all ORM models inherit from this
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# Utility: verify connectivity on start-up (optional sanity check)
# ---------------------------------------------------------------------------
def verify_database_connection() -> None:
    """Raise an informative error early if the DB is unreachable."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
