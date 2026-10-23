"""
Tests for document quality checks (blank, blurry), auto-population of extracted receipt fields,
and the PATCH /requests/{id} endpoint for submitters.
"""
from decimal import Decimal
from datetime import date
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw
import pytest
from starlette.testclient import TestClient

from app.models.document_version import DocType, DocumentVersion, ProcessingStatus
from app.models.request import Request, RequestStatus, RequestType
from app.models.user import User, UserRole
from app.services.document_processing.processor import DocumentProcessor
from app.core.security import hash_password, create_access_token


def _make_user(db, email: str, role: UserRole, name: str) -> User:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            email=email,
            password_hash=hash_password("password123"),
            role=role,
            display_name=name,
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _auth(user: User) -> dict[str, str]:
    tok = create_access_token({"sub": str(user.id), "role": user.role.value, "email": user.email})
    return {"Authorization": f"Bearer {tok}"}


def test_blank_document_detection_raises_clear_message(tmp_path, db_session):
    blank = Image.new("RGB", (400, 500), (255, 255, 255))
    img_path = tmp_path / "blank_test.png"
    blank.save(img_path)

    processor = DocumentProcessor(db=db_session)
    submitter = _make_user(db_session, "sub_blank@test.com", UserRole.submitter, "Sub Blank")
    reviewer = _make_user(db_session, "rev_blank@test.com", UserRole.reviewer, "Rev Blank")
    approver = _make_user(db_session, "app_blank@test.com", UserRole.approver, "App Blank")

    req = Request(
        request_number="REQ-TEST-BLANK",
        title="Blank Test Claim",
        request_type=RequestType.expense_reimbursement,
        submitter_id=submitter.id,
        assigned_reviewer_id=reviewer.id,
        assigned_approver_id=approver.id,
        status=RequestStatus.draft,
    )
    db_session.add(req)
    db_session.commit()

    from app.core.config import settings
    target_path = settings.storage_path / "blank_test.png"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    blank.save(target_path)

    doc = DocumentVersion(
        request_id=req.id,
        doc_type=DocType.receipt,
        original_filename="blank.png",
        mime_type="image/png",
        file_size=100,
        file_hash="dummyhash",
        storage_key="blank_test.png",
        version_number=1,
        uploader_id=submitter.id,
        processing_status=ProcessingStatus.pending,
    )
    db_session.add(doc)
    db_session.commit()

    processor.process(doc.id)
    db_session.refresh(doc)

    assert doc.processing_status == ProcessingStatus.failed
    assert "No readable content found" in doc.processing_error


def test_blurry_document_detection_raises_clear_message(tmp_path, db_session):
    blurry = Image.new("RGB", (400, 500), (255, 255, 255))
    d = ImageDraw.Draw(blurry)
    d.rectangle([50, 50, 350, 450], fill=(220, 220, 220))
    img_path = tmp_path / "blurry_test.png"
    blurry.save(img_path)

    from app.core.config import settings
    target_path = settings.storage_path / "blurry_test.png"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    blurry.save(target_path)

    processor = DocumentProcessor(db=db_session)
    submitter = _make_user(db_session, "sub_blur@test.com", UserRole.submitter, "Sub Blur")
    reviewer = _make_user(db_session, "rev_blur@test.com", UserRole.reviewer, "Rev Blur")
    approver = _make_user(db_session, "app_blur@test.com", UserRole.approver, "App Blur")

    req = Request(
        request_number="REQ-TEST-BLURRY",
        title="Blurry Test Claim",
        request_type=RequestType.expense_reimbursement,
        submitter_id=submitter.id,
        assigned_reviewer_id=reviewer.id,
        assigned_approver_id=approver.id,
        status=RequestStatus.draft,
    )
    db_session.add(req)
    db_session.commit()

    doc = DocumentVersion(
        request_id=req.id,
        doc_type=DocType.receipt,
        original_filename="blurry.png",
        mime_type="image/png",
        file_size=100,
        file_hash="dummyhash2",
        storage_key="blurry_test.png",
        version_number=1,
        uploader_id=submitter.id,
        processing_status=ProcessingStatus.pending,
    )
    db_session.add(doc)
    db_session.commit()

    class LowConfOCR:
        engine_name = "test_ocr"
        is_available = True
        unavailable_reason = None
        def extract_blocks(self, _img, page=0):
            from app.services.ocr.engine import TextBlock
            return [TextBlock("~#$%", page=page, confidence=0.15)]
        def reliable_text(self, _blocks, _thresh):
            return ""

    processor.ocr = LowConfOCR()
    processor.process(doc.id)
    db_session.refresh(doc)

    assert doc.processing_status == ProcessingStatus.failed
    assert "This document is difficult to read" in doc.processing_error


def test_patch_request_details_and_verification_update(client: TestClient, db_session):
    sub1 = _make_user(db_session, "sub_patch_1@test.com", UserRole.submitter, "Sub 1")
    sub2 = _make_user(db_session, "sub_patch_2@test.com", UserRole.submitter, "Sub 2")
    rev = _make_user(db_session, "rev_patch@test.com", UserRole.reviewer, "Rev")
    app = _make_user(db_session, "app_patch@test.com", UserRole.approver, "App")

    # 1. Create a minimal draft claim without manual expense details
    create_resp = client.post(
        "/api/v1/requests",
        headers=_auth(sub1),
        json={
            "title": "Expense Reimbursement",
            "assigned_reviewer_id": rev.id,
            "assigned_approver_id": app.id,
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    claim_id = create_resp.json()["id"]

    # 2. Submitter updates claimed_amount, date, merchant, title
    patch_resp = client.patch(
        f"/api/v1/requests/{claim_id}",
        headers=_auth(sub1),
        json={
            "title": "Starbucks Client Meeting",
            "claimed_amount": "450.00",
            "expense_date": "2026-10-23",
            "expense_category": "meals",
            "currency": "INR",
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text
    updated = patch_resp.json()
    assert updated["title"] == "Starbucks Client Meeting"
    assert updated["claimed_amount"] == "450.00"
    assert updated["expense_date"] == "2026-10-23"
    assert updated["expense_category"] == "meals"

    # 3. Unauthorized submitter cannot edit
    unauth_resp = client.patch(
        f"/api/v1/requests/{claim_id}",
        headers=_auth(sub2),
        json={"title": "Hacked Title"},
    )
    assert unauth_resp.status_code == 403
