"""
Phase 1 tests: health endpoint, database connectivity, and model structure.

Run with:
    cd backend
    .venv/Scripts/pytest app/tests/test_phase1.py -v
"""
from sqlalchemy import inspect

# ── Health endpoint tests ────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        """Health endpoint must return HTTP 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

    def test_health_status_ok(self, client):
        """Overall status must be 'ok' when database is reachable."""
        data = client.get("/api/v1/health").json()
        assert data["status"] == "ok", f"Expected status=ok, got: {data}"

    def test_health_database_ok(self, client):
        """Database section must report status=ok."""
        data = client.get("/api/v1/health").json()
        assert data["database"]["status"] == "ok", (
            f"Database not OK: {data['database']}"
        )

    def test_health_has_version(self, client):
        """Health response must include a version field."""
        data = client.get("/api/v1/health").json()
        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_health_has_timestamp(self, client):
        """Health response must include an ISO timestamp."""
        data = client.get("/api/v1/health").json()
        assert "timestamp" in data
        assert "Z" in data["timestamp"]  # UTC marker

    def test_health_has_features(self, client):
        """Health response must report feature flags."""
        data = client.get("/api/v1/health").json()
        assert "features" in data
        assert "gemini_available" in data["features"]
        assert "ocr_engine" in data["features"]

    def test_root_returns_200(self, client):
        """Root path should return 200 with basic info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "health" in data


# ── Database structure tests ─────────────────────────────────────────────────

class TestDatabaseStructure:
    EXPECTED_TABLES = {
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

    def test_all_tables_exist(self, test_engine):
        """All 9 application tables must exist in the database."""
        inspector = inspect(test_engine)
        actual = set(inspector.get_table_names())
        missing = self.EXPECTED_TABLES - actual
        assert not missing, f"Missing tables: {missing}"

    def test_users_table_columns(self, test_engine):
        """Users table must have all required columns."""
        inspector = inspect(test_engine)
        cols = {col["name"] for col in inspector.get_columns("users")}
        required = {"id", "display_name", "email", "password_hash", "role", "is_active", "created_at"}
        missing = required - cols
        assert not missing, f"Missing columns in users: {missing}"

    def test_requests_table_columns(self, test_engine):
        """Requests table must have all required columns."""
        inspector = inspect(test_engine)
        cols = {col["name"] for col in inspector.get_columns("requests")}
        required = {"id", "request_number", "submitter_id", "status", "created_at"}
        missing = required - cols
        assert not missing, f"Missing columns in requests: {missing}"

    def test_document_versions_columns(self, test_engine):
        """Document versions table must track storage_key and file_hash."""
        inspector = inspect(test_engine)
        cols = {col["name"] for col in inspector.get_columns("document_versions")}
        required = {"id", "request_id", "storage_key", "file_hash", "version_number", "processing_status"}
        missing = required - cols
        assert not missing, f"Missing columns in document_versions: {missing}"

    def test_verification_checks_has_evidence(self, test_engine):
        """Verification checks must store evidence_references."""
        inspector = inspect(test_engine)
        cols = {col["name"] for col in inspector.get_columns("verification_checks")}
        assert "evidence_references" in cols
        assert "resolution_status" in cols

    def test_extracted_fields_preserves_raw_and_normalized(self, test_engine):
        """Extracted fields must store both raw and normalized values separately."""
        inspector = inspect(test_engine)
        cols = {col["name"] for col in inspector.get_columns("extracted_fields")}
        assert "extracted_value" in cols, "Missing extracted_value (raw OCR)"
        assert "normalized_value" in cols, "Missing normalized_value"
        # Corrections are stored in reviewer_corrections, NOT here
        assert "corrected_value" not in cols, (
            "Corrections must go in reviewer_corrections, not extracted_fields"
        )

    def test_reviewer_corrections_preserves_original(self, test_engine):
        """Reviewer corrections table must keep original_extracted_value."""
        inspector = inspect(test_engine)
        cols = {col["name"] for col in inspector.get_columns("reviewer_corrections")}
        assert "original_extracted_value" in cols
        assert "corrected_value" in cols
        assert "reviewer_id" in cols


# ── Model import tests ───────────────────────────────────────────────────────

class TestModelImports:
    def test_all_models_importable(self):
        """Every model class must be importable from app.models."""
        import app.models as m
        models = [
            "User", "Request", "DocumentVersion", "ExtractionRun",
            "ExtractedField", "ReviewerCorrection", "VerificationCheck",
            "ReviewAction", "AuditEvent",
        ]
        for name in models:
            assert hasattr(m, name), f"Model '{name}' not found in app.models"

    def test_user_role_enum(self):
        """UserRole includes the three workflow roles and secure administrator role."""
        from app.models.user import UserRole
        assert set(UserRole) == {UserRole.submitter, UserRole.reviewer, UserRole.approver, UserRole.admin}

    def test_request_status_enum(self):
        """RequestStatus includes the reviewer-to-approver handoff state."""
        from app.models.request import RequestStatus
        expected = {
            "draft", "submitted", "processing", "under_review",
            "more_info_required", "approved", "rejected", "processing_failed",
            "pending_approval",
        }
        actual = {s.value for s in RequestStatus}
        assert expected == actual, f"Status mismatch: {expected ^ actual}"

    def test_settings_loads(self):
        """Settings must load without error (reads from .env or defaults)."""
        from app.core.config import settings
        assert settings.database_url  # non-empty
        assert settings.secret_key  # non-empty
        assert settings.max_upload_bytes > 0
