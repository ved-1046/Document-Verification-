"""Unit and integration tests for Decision Replay service and endpoint."""

from datetime import datetime, timezone, timedelta
from app.core.security import create_access_token, hash_password
from app.models.document_version import DocumentVersion, DocType, ProcessingStatus
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.extracted_field import ExtractedField
from app.models.reviewer_correction import ReviewerCorrection
from app.models.review_action import ReviewAction, ReviewActionType
from app.models.audit_event import AuditEvent, AuditEventType
from app.models.request import Request, RequestStatus, RequestType
from app.models.user import User, UserRole


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def _user(db_session, email: str, role: UserRole) -> User:
    user = User(
        display_name=email.split("@")[0].title(),
        email=email,
        password_hash=hash_password("password123"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_decision_replay_unauthenticated(client):
    res = client.get("/api/v1/requests/1/decision-replay")
    assert res.status_code == 401


def test_decision_replay_unauthorized_user(client, db_session):
    owner = _user(db_session, "owner_replay@example.com", UserRole.submitter)
    other = _user(db_session, "other_replay@example.com", UserRole.submitter)

    req = Request(
        request_number="REQ-REPLAY-001",
        request_type=RequestType.expense_reimbursement,
        title="Owner's Request",
        submitter_id=owner.id,
        status=RequestStatus.draft,
    )
    db_session.add(req)
    db_session.commit()

    res = client.get(f"/api/v1/requests/{req.id}/decision-replay", headers=_auth_headers(other))
    assert res.status_code == 403


def test_decision_replay_empty_draft_request(client, db_session):
    submitter = _user(db_session, "sub_empty_replay@example.com", UserRole.submitter)
    req = Request(
        request_number="REQ-REPLAY-EMPTY",
        request_type=RequestType.expense_reimbursement,
        title="Empty Draft Claim",
        description="Initial taxi claim draft",
        claimed_amount=150.00,
        currency="INR",
        expense_category="transportation",
        submitter_id=submitter.id,
        status=RequestStatus.draft,
    )
    db_session.add(req)
    db_session.commit()

    res = client.get(f"/api/v1/requests/{req.id}/decision-replay", headers=_auth_headers(submitter))
    assert res.status_code == 200
    data = res.json()

    assert data["request_id"] == req.id
    assert data["request_number"] == "REQ-REPLAY-EMPTY"
    assert data["current_status"] == "draft"
    assert data["total_events"] == 1

    first_event = data["events"][0]
    assert first_event["event_type"] == "request_created"
    assert first_event["category"] == "lifecycle"
    assert first_event["actor"]["id"] == submitter.id
    assert first_event["request_state_at_event"]["status"] == "draft"
    assert first_event["request_state_at_event"]["is_historical_state_available"] is True


def test_decision_replay_full_lifecycle(client, db_session):
    submitter = _user(db_session, "sub_lifecycle_replay@example.com", UserRole.submitter)
    reviewer = _user(db_session, "rev_lifecycle_replay@example.com", UserRole.reviewer)
    approver = _user(db_session, "app_lifecycle_replay@example.com", UserRole.approver)

    base_time = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Request
    req = Request(
        request_number="REQ-REPLAY-FULL",
        request_type=RequestType.expense_reimbursement,
        title="Conference Expenses",
        description="Travel and registration",
        claimed_amount=5000.00,
        currency="INR",
        expense_category="travel",
        submitter_id=submitter.id,
        assigned_reviewer_id=reviewer.id,
        assigned_approver_id=approver.id,
        status=RequestStatus.approved,
        created_at=base_time,
    )
    db_session.add(req)
    db_session.flush()

    # 2. Document upload (v1)
    doc_v1 = DocumentVersion(
        request_id=req.id,
        doc_type=DocType.receipt,
        original_filename="receipt_taxi.pdf",
        storage_key="req/v1-receipt.pdf",
        mime_type="application/pdf",
        file_size=20480,
        file_hash="fake-hash-v1",
        version_number=1,
        uploader_id=submitter.id,
        processing_status=ProcessingStatus.ready,
        uploaded_at=base_time + timedelta(minutes=5),
    )
    db_session.add(doc_v1)
    db_session.flush()

    # 3. Extraction Run
    run_v1 = ExtractionRun(
        document_version_id=doc_v1.id,
        ocr_engine="tesseract-5.3.1",
        started_at=base_time + timedelta(minutes=6),
        completed_at=base_time + timedelta(minutes=7),
        status=ExtractionStatus.success,
    )
    db_session.add(run_v1)
    db_session.flush()

    # 4. Automated Verification Audit
    db_session.add(AuditEvent(
        request_id=req.id,
        actor_id=None,
        event_type=AuditEventType.verification_run,
        change_summary="Automated verification completed (3 checks passed)",
        created_at=base_time + timedelta(minutes=8),
    ))

    # 5. Submitter Submits Request
    db_session.add(ReviewAction(
        request_id=req.id,
        actor_id=submitter.id,
        action_type=ReviewActionType.submitted,
        comment="Submitted conference expenses for review",
        previous_status=RequestStatus.draft.value,
        new_status=RequestStatus.processing.value,
        created_at=base_time + timedelta(minutes=10),
    ))

    # 6. Reviewer requests more info
    db_session.add(ReviewAction(
        request_id=req.id,
        actor_id=reviewer.id,
        action_type=ReviewActionType.correction_requested,
        comment="Please provide itemized hotel bill",
        previous_status=RequestStatus.under_review.value,
        new_status=RequestStatus.more_info_required.value,
        created_at=base_time + timedelta(hours=2),
    ))

    # 7. Submitter uploads v2 document
    doc_v2 = DocumentVersion(
        request_id=req.id,
        doc_type=DocType.receipt,
        original_filename="receipt_hotel_itemized.pdf",
        storage_key="req/v2-receipt.pdf",
        mime_type="application/pdf",
        file_size=40960,
        file_hash="fake-hash-v2",
        version_number=2,
        uploader_id=submitter.id,
        processing_status=ProcessingStatus.ready,
        uploaded_at=base_time + timedelta(hours=3),
    )
    db_session.add(doc_v2)
    db_session.flush()

    # 8. Submitter resubmits
    db_session.add(ReviewAction(
        request_id=req.id,
        actor_id=submitter.id,
        action_type=ReviewActionType.correction_submitted,
        comment="Uploaded itemized hotel bill",
        previous_status=RequestStatus.more_info_required.value,
        new_status=RequestStatus.processing.value,
        created_at=base_time + timedelta(hours=3, minutes=5),
    ))

    # 9. Reviewer corrects a field
    db_session.add(ReviewerCorrection(
        request_id=req.id,
        document_version_id=doc_v2.id,
        field_name="total_amount",
        original_extracted_value="5000",
        corrected_value="5200.00",
        reviewer_id=reviewer.id,
        reason="Included room tax omitted by OCR",
        created_at=base_time + timedelta(hours=4),
    ))

    # 10. Reviewer completes review
    db_session.add(ReviewAction(
        request_id=req.id,
        actor_id=reviewer.id,
        action_type=ReviewActionType.review_completed,
        comment="All receipts verified against policy limits",
        previous_status=RequestStatus.under_review.value,
        new_status=RequestStatus.pending_approval.value,
        created_at=base_time + timedelta(hours=4, minutes=15),
    ))

    # 11. Approver approves
    db_session.add(ReviewAction(
        request_id=req.id,
        actor_id=approver.id,
        action_type=ReviewActionType.approved,
        comment="Approved for reimbursement",
        previous_status=RequestStatus.pending_approval.value,
        new_status=RequestStatus.approved.value,
        created_at=base_time + timedelta(hours=5),
    ))
    db_session.commit()

    # Test retrieval as approver
    res = client.get(f"/api/v1/requests/{req.id}/decision-replay", headers=_auth_headers(approver))
    assert res.status_code == 200
    data = res.json()

    assert data["request_id"] == req.id
    assert data["total_events"] == 11
    assert data["summary"]["final_decision"] == "approved"
    assert data["summary"]["total_documents_uploaded"] == 2
    assert data["summary"]["total_corrections_made"] == 1

    # Verify chronological ordering
    events = data["events"]
    for i in range(len(events) - 1):
        t_curr = datetime.fromisoformat(events[i]["timestamp"])
        t_next = datetime.fromisoformat(events[i + 1]["timestamp"])
        assert t_curr <= t_next, f"Events out of order at index {i}: {events[i]['title']} -> {events[i+1]['title']}"
        assert events[i]["sequence_number"] == i + 1

    # Verify final event is approved
    last_event = events[-1]
    assert last_event["event_type"] == "action_approved"
    assert last_event["actor"]["id"] == approver.id
    assert last_event["comment"] == "Approved for reimbursement"
    assert last_event["request_state_at_event"]["status"] == "approved"


def test_decision_replay_rejection(client, db_session):
    submitter = _user(db_session, "sub_reject_replay@example.com", UserRole.submitter)
    approver = _user(db_session, "app_reject_replay@example.com", UserRole.approver)

    req = Request(
        request_number="REQ-REPLAY-REJECT",
        request_type=RequestType.expense_reimbursement,
        title="Overbudget Expense",
        submitter_id=submitter.id,
        assigned_approver_id=approver.id,
        status=RequestStatus.rejected,
    )
    db_session.add(req)
    db_session.flush()

    db_session.add(ReviewAction(
        request_id=req.id,
        actor_id=approver.id,
        action_type=ReviewActionType.rejected,
        comment="Exceeds travel per diem limit without prior manager sign-off",
        previous_status=RequestStatus.pending_approval.value,
        new_status=RequestStatus.rejected.value,
    ))
    db_session.commit()

    res = client.get(f"/api/v1/requests/{req.id}/decision-replay", headers=_auth_headers(submitter))
    assert res.status_code == 200
    data = res.json()

    assert data["summary"]["final_decision"] == "rejected"
    assert data["current_status"] == "rejected"
    rejection_event = next(e for e in data["events"] if e["event_type"] == "action_rejected")
    assert "Exceeds travel per diem" in rejection_event["comment"]
    assert rejection_event["status_badge"] == "error"
