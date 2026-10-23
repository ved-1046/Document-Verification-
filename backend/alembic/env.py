"""
Alembic environment configuration for DocuVerify AI.

This file configures Alembic to:
1. Read the database URL from app.core.config (which reads from .env)
2. Import all SQLAlchemy models so autogenerate can detect all tables
3. Run synchronous migrations (SQLite/PostgreSQL both synchronous via SQLAlchemy)

To create a new migration:
    cd backend
    .venv/Scripts/alembic revision --autogenerate -m "describe change"

To apply all pending migrations:
    .venv/Scripts/alembic upgrade head

To check current state:
    .venv/Scripts/alembic current
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make sure `app` is importable when running alembic from /backend ─────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import settings (reads from .env)
from app.core.config import settings  # noqa: E402

# Import the declarative base so Alembic knows about the schema
from app.db.base import Base  # noqa: E402

# Import ALL models so their tables are registered on Base.metadata
import app.models  # noqa: E402, F401

# ── Alembic Config ───────────────────────────────────────────────────────────
config = context.config

# Inject database URL from settings (overrides the (absent) sqlalchemy.url in alembic.ini)
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the MetaData object for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (just emit SQL, no real connection).
    Useful for generating migration scripts to review before running.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render column-level constraints for better diffs
        render_as_batch=True,  # Required for SQLite ALTER TABLE
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (real DB connection).
    This is the normal mode when running `alembic upgrade head`.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
