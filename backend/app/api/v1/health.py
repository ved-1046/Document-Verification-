"""
Health-check endpoint.

GET /api/v1/health — returns status of service, database, and optional features.
This endpoint does not require authentication so it can be used by
load balancers and monitoring tools.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/health", summary="Health check")
def health_check(db: Session = Depends(get_db)):
    """
    Returns the current status of the API and its dependencies.

    - **status**: overall service status
    - **database**: whether the database is reachable
    - **gemini_available**: whether the AI provider is configured
    - **ocr_engine**: which OCR engine will be used
    """
    # Database connectivity check
    db_status = "ok"
    db_detail = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = "error"
        db_detail = str(exc)

    overall = "ok" if db_status == "ok" else "degraded"

    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    from app.services.ocr.engine import OCREngine
    ocr = OCREngine(tesseract_cmd=settings.tesseract_cmd or None)
    ocr_name = ocr.engine_name if ocr.is_available else "unavailable"

    return {
        "status": overall,
        "timestamp": ts,
        "version": "0.1.0",
        "environment": settings.environment,
        "database": {
            "status": db_status,
            "detail": db_detail,
        },
        "features": {
            "gemini_available": settings.gemini_available,
            "ocr_engine": ocr_name,
            "max_upload_mb": settings.max_upload_mb,
        },
    }
