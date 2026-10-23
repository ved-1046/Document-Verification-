"""
Models package — import all models here so Alembic can discover them
when autogenerating migrations.
"""
from app.models.user import User, UserRole  # noqa: F401
from app.models.request import Request, RequestStatus, RequestType  # noqa: F401
from app.models.document_version import DocumentVersion, DocType, ProcessingStatus  # noqa: F401
from app.models.extraction_run import ExtractionRun, ExtractionStatus  # noqa: F401
from app.models.extracted_field import ExtractedField  # noqa: F401
from app.models.reviewer_correction import ReviewerCorrection  # noqa: F401
from app.models.verification_check import VerificationCheck, CheckType, CheckResult, CheckSeverity, ResolutionStatus  # noqa: F401
from app.models.review_action import ReviewAction, ReviewActionType  # noqa: F401
from app.models.audit_event import AuditEvent, AuditEventType  # noqa: F401

__all__ = [
    "User", "UserRole",
    "Request", "RequestStatus", "RequestType",
    "DocumentVersion", "DocType", "ProcessingStatus",
    "ExtractionRun", "ExtractionStatus",
    "ExtractedField",
    "ReviewerCorrection",
    "VerificationCheck", "CheckType", "CheckResult", "CheckSeverity", "ResolutionStatus",
    "ReviewAction", "ReviewActionType",
    "AuditEvent", "AuditEventType",
]
