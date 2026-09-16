"""
alembic/env.py
──────────────────────────────────────────────────────────────────────────────
Alembic environment configuration.

Key behaviours:
  - Reads DATABASE_URL from the .env file so migrations use the same
    credentials as the application.
  - Passes `target_metadata` from our ORM Base so `alembic revision
    --autogenerate` can diff the live schema against our models.
  - Runs in "online" mode only (suitable for CI and developer machines).
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# ─── ensure the project root is on sys.path so `app.*` imports work ──────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ─── load environment variables ───────────────────────────────────────────────
load_dotenv()

# ─── Alembic config object ────────────────────────────────────────────────────
config = context.config

# Override the sqlalchemy.url from alembic.ini with the value from .env
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

# ─── Python logging setup ─────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ─── Import Base + all models so Alembic can detect them ─────────────────────
from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401  – registers all ORM classes on Base.metadata

target_metadata = Base.metadata


# ─── Migration runner ─────────────────────────────────────────────────────────

def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,          # detect column type changes
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
