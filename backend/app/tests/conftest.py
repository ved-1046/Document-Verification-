"""Shared pytest fixtures for DocuVerify AI backend tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app as fastapi_app
from app.db.session import get_db
from app.db.base import Base
from app.core.config import settings
import app.models  # noqa: F401 — registers all models on Base.metadata

REQUIRED_TEST_TABLES = {
    "users",
    "requests",
    "document_versions",
    "extraction_runs",
    "extracted_fields",
    "reviewer_corrections",
    "verification_checks",
    "review_actions",
    "audit_events",
}


@pytest.fixture
def test_engine():
    """Fresh in-memory DB shared across the TestClient worker thread."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    # Importing app.models registers every mapped class on this metadata.
    Base.metadata.create_all(bind=engine)
    created_tables = set(inspect(engine).get_table_names())
    missing_tables = REQUIRED_TEST_TABLES - created_tables
    if missing_tables:
        engine.dispose()
        raise RuntimeError(
            "Test database schema is incomplete; missing tables: "
            + ", ".join(sorted(missing_tables))
        )
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Keep synthetic upload tests away from the application's upload folder."""
    storage_path = tmp_path / "uploads"
    monkeypatch.setattr(settings, "storage_dir", str(storage_path))
    return storage_path


@pytest.fixture
def db_session(test_engine):
    """Yield a transactional DB session rolled back after each test."""
    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(test_engine, isolated_storage):
    """FastAPI test client with DB overridden to in-memory SQLite."""
    TestSession = sessionmaker(bind=test_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    previous_overrides = fastapi_app.dependency_overrides.copy()
    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(fastapi_app) as c:
            yield c
    finally:
        fastapi_app.dependency_overrides.clear()
        fastapi_app.dependency_overrides.update(previous_overrides)
