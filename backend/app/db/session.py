"""
Database engine and session factory.

Design notes:
- Uses SQLAlchemy 2.x style (create_engine + sessionmaker).
- SQLite gets check_same_thread=False for FastAPI's async workers.
- PostgreSQL: just change DATABASE_URL in .env — no code changes needed.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Build engine
connect_args = {}
if settings.database_url.startswith("sqlite"):
    # SQLite requires this flag in multi-threaded environments
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=(settings.environment == "development"),
)

# Enable WAL mode for SQLite (better concurrent read performance)
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    """FastAPI dependency: yields a database session and closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
