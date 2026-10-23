"""Identity provisioning and assigned reviewer/approver workflow tests."""
from app.core.security import hash_password
from app.models.document_version import DocType, DocumentVersion, ProcessingStatus
from app.models.extracted_field import ExtractedField
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.request import Request, RequestStatus, RequestType
from app.models.user import User, UserRole
from app.models.verification_check import (
    CheckResult, CheckSeverity, CheckType, ResolutionStatus, VerificationCheck,
)


def _create_user(db, name, email, role, password="initial-password"):
    user = User(
        display_name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _token(client, email, password="initial-password"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_admin_can_provision_user_without_public_role_escalation(client, db_session):
    admin = _create_user(db_session, "Workspace Admin", "admin@example.com", UserRole.admin)
    db_session.commit()
    admin_token = _token(client, admin.email)
    headers = {"Authorization": f"Bearer {admin_token}"}

    created = client.post("/api/v1/admin/users", headers=headers, json={
        "display_name": "Priya Deshmukh",
        "email": "priya@example.com",
        "role": "reviewer",
        "is_active": True,
    })
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["display_name"] == "Priya Deshmukh"
    assert payload["role"] == "reviewer"
    assert len(payload["temporary_password"]) >= 20
    assert "password_hash" not in payload

    duplicate = client.post("/api/v1/admin/users", headers=headers, json={
        "display_name": "Duplicate", "email": "PRIYA@example.com", "role": "approver",
    })
    assert duplicate.status_code == 409

    provisioned_login = client.post("/api/v1/auth/login", json={
        "email": "priya@example.com", "password": payload["temporary_password"],
    })
    assert provisioned_login.status_code == 200

    public_escalation = client.post("/api/v1/auth/register", json={
        "display_name": "Escalation", "email": "escalation2@example.com",
        "password": "valid-password", "role": "admin",
    })
    assert public_escalation.status_code == 403


def test_eligible_assignee_endpoint_requires_auth_and_returns_active_workflow_roles(client, db_session):
    submitter = _create_user(db_session, "Employee", "employee@example.com", UserRole.submitter)
    reviewer = _create_user(db_session, "Active Reviewer", "active-reviewer@example.com", UserRole.reviewer)
    approver = _create_user(db_session, "Active Approver", "active-approver@example.com", UserRole.approver)
    inactive = _create_user(db_session, "Inactive Reviewer", "inactive-reviewer@example.com", UserRole.reviewer)
    inactive.is_active = False
    db_session.commit()

    unauthorized = client.get("/api/v1/users/eligible-assignees")
    assert unauthorized.status_code == 401

    token = _token(client, submitter.email)
    response = client.get(
        "/api/v1/users/eligible-assignees",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == [
        {"id": approver.id, "display_name": approver.display_name, "role": "approver"},
        {"id": reviewer.id, "display_name": reviewer.display_name, "role": "reviewer"},
    ]
    assert inactive.id not in {person["id"] for person in response.json()}


def test_assigned_reviewer_handoff_and_approver_decision_are_scoped(client, db_session):
    submitter = _create_user(db_session, "Aarav Sharma", "aarav@example.com", UserRole.submitter)
    reviewer = _create_user(db_session, "Priya Deshmukh", "priya2@example.com", UserRole.reviewer)
    approver = _create_user(db_session, "Rahul Patil", "rahul@example.com", UserRole.approver)
    other_approver = _create_user(db_session, "Other Approver", "other@example.com", UserRole.approver)
    request = Request(
        request_number="REQ-2026-9001",
        request_type=RequestType.expense_reimbursement,
        title="Client visit",
        submitter_id=submitter.id,
        assigned_reviewer_id=reviewer.id,
        assigned_approver_id=approver.id,
        status=RequestStatus.under_review,
    )
    db_session.add(request)
    db_session.commit()

    # The review handoff requires the latest required documents to have successful
    # extraction. Seed isolated test evidence instead of bypassing that rule.
    for index, (doc_type, fields) in enumerate((
        (DocType.expense_form, {
            "employee_name": "Aarav Sharma", "expense_date": "2026-10-22",
            "total_amount": "2000.00",
        }),
        (DocType.receipt, {
            "merchant_name": "Sample Transport Provider", "expense_date": "2026-10-22",
            "total_amount": "2000.00",
        }),
    ), start=1):
        document = DocumentVersion(
            request_id=request.id,
            doc_type=doc_type,
            original_filename=f"{doc_type.value}.pdf",
            storage_key=f"test/{request.id}/{doc_type.value}.pdf",
            mime_type="application/pdf",
            file_size=100,
            file_hash=f"{index:064x}",
            version_number=1,
            uploader_id=submitter.id,
            processing_status=ProcessingStatus.ready,
        )
        db_session.add(document)
        db_session.flush()
        extraction = ExtractionRun(
            document_version_id=document.id,
            ocr_engine="test-native-text",
            status=ExtractionStatus.success,
        )
        db_session.add(extraction)
        db_session.flush()
        db_session.add_all([
            ExtractedField(
                extraction_run_id=extraction.id,
                field_name=name,
                extracted_value=value,
                normalized_value=value,
            )
            for name, value in fields.items()
        ])

    db_session.add(VerificationCheck(
        request_id=request.id,
        check_type=CheckType.amount_mismatch,
        rule_name="test_open_flag",
        result=CheckResult.flag,
        severity=CheckSeverity.medium,
        explanation="Test flag requires reviewer disposition.",
        resolution_status=ResolutionStatus.open,
        is_current=True,
    ))
    db_session.commit()

    reviewer_token = _token(client, reviewer.email)
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}
    queue = client.get("/api/v1/requests/review-queue", headers=reviewer_headers)
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()] == [request.id]
    sent = client.post(
        f"/api/v1/requests/{request.id}/complete-review",
        headers=reviewer_headers,
        json={"comment": "Receipt and claim details reviewed."},
    )
    assert sent.status_code == 422, sent.text
    check = db_session.query(VerificationCheck).filter_by(request_id=request.id).one()
    resolved = client.post(
        f"/api/v1/requests/{request.id}/resolve-check?check_id={check.id}",
        headers=reviewer_headers,
        json={"resolution_status": "resolved"},
    )
    assert resolved.status_code == 200, resolved.text
    sent = client.post(
        f"/api/v1/requests/{request.id}/complete-review",
        headers=reviewer_headers,
        json={"comment": "Evidence reviewed; open flag disposition recorded."},
    )
    assert sent.status_code == 200, sent.text

    approver_token = _token(client, approver.email)
    approver_headers = {"Authorization": f"Bearer {approver_token}"}
    approver_queue = client.get("/api/v1/requests/review-queue", headers=approver_headers)
    assert approver_queue.status_code == 200
    assert [item["id"] for item in approver_queue.json()] == [request.id]

    other_token = _token(client, other_approver.email)
    forbidden = client.post(
        f"/api/v1/requests/{request.id}/approve",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"comment": "Unauthorized attempt."},
    )
    assert forbidden.status_code == 403

    decided = client.post(
        f"/api/v1/requests/{request.id}/approve",
        headers=approver_headers,
        json={"comment": "Approved after human review."},
    )
    assert decided.status_code == 200, decided.text
    detail = client.get(f"/api/v1/requests/{request.id}", headers=approver_headers)
    assert detail.json()["status"] == "approved"
    history = client.get(f"/api/v1/requests/{request.id}/history", headers=approver_headers)
    assert [event["actor_name"] for event in history.json()] == [reviewer.display_name, approver.display_name]

    outsider = _create_user(db_session, "Unassigned Reviewer", "unassigned@example.com", UserRole.reviewer)
    db_session.commit()
    outsider_token = _token(client, outsider.email)
    hidden = client.get(
        f"/api/v1/requests/{request.id}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert hidden.status_code == 403


def test_submitter_reviewer_approver_claim_workflow_with_native_text_documents(client, db_session, monkeypatch):
    """Exercise upload, extraction, queue visibility, review, decision, and access control."""
    import fitz

    submitter = _create_user(db_session, "End-to-End Submitter", "e2e-submit@example.com", UserRole.submitter)
    reviewer = _create_user(db_session, "End-to-End Reviewer", "e2e-review@example.com", UserRole.reviewer)
    other_reviewer = _create_user(db_session, "Different Reviewer", "e2e-other@example.com", UserRole.reviewer)
    approver = _create_user(db_session, "End-to-End Approver", "e2e-approve@example.com", UserRole.approver)
    db_session.commit()
    submitter_headers = {"Authorization": f"Bearer {_token(client, submitter.email)}"}
    reviewer_headers = {"Authorization": f"Bearer {_token(client, reviewer.email)}"}
    other_headers = {"Authorization": f"Bearer {_token(client, other_reviewer.email)}"}
    approver_headers = {"Authorization": f"Bearer {_token(client, approver.email)}"}
    monkeypatch.setattr(
        "app.services.assistant.service._gemini_answer",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("provider unavailable in test")),
    )

    created = client.post("/api/v1/requests", headers=submitter_headers, json={
        "title": "Local travel reimbursement",
        "expense_category": "travel",
        "claimed_amount": "2000.00",
        "expense_date": "2026-10-22",
        "currency": "INR",
        "assigned_reviewer_id": reviewer.id,
        "assigned_approver_id": approver.id,
    })
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]
    assistant = client.post("/api/v1/assistant/ask", headers=reviewer_headers, json={
        "request_id": request_id,
        "question": "What is the current request status?",
    })
    assert assistant.status_code == 200, assistant.text
    assert assistant.json()["mode"] == "fallback"
    assert "draft" in assistant.json()["answer"]
    assert client.post("/api/v1/assistant/ask", headers=other_headers, json={
        "request_id": request_id, "question": "What is the current status?",
    }).status_code == 403
    assert client.post("/api/v1/assistant/ask", headers=reviewer_headers, json={
        "request_id": 999999, "question": "What is the current status?",
    }).status_code == 404
    draft_queue = client.get("/api/v1/requests/review-queue", headers=reviewer_headers)
    assert draft_queue.status_code == 200
    assert request_id not in {item["id"] for item in draft_queue.json()}
    assigned_drafts = client.get("/api/v1/requests?status=draft", headers=reviewer_headers)
    assert assigned_drafts.status_code == 200
    assert request_id in {item["id"] for item in assigned_drafts.json()}

    def pdf_bytes(text):
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((72, 72), text)
        result = pdf.tobytes()
        pdf.close()
        return result

    documents = [
        ("expense_form", "expense-form.pdf", "SAMPLE EXPENSE REIMBURSEMENT FORM\nEmployee name: End-to-End Submitter\nExpense date: 22 October 2026\nAmount claimed: INR 2,000.00\nBusiness purpose: Local travel for a work-related meeting"),
        ("receipt", "receipt.pdf", "SAMPLE RECEIPT\nSample Transport Provider\nDate: 22 October 2026\nTOTAL: INR 2,000.00\nReceipt reference: DEMO-TRAVEL-2000"),
    ]
    uploaded_ids = []
    for doc_type, filename, content in documents:
        response = client.post(
            f"/api/v1/requests/{request_id}/documents",
            headers=submitter_headers,
            data={"doc_type": doc_type},
            files={"file": (filename, pdf_bytes(content), "application/pdf")},
        )
        assert response.status_code == 201, response.text
        assert response.json()["processing_status"] == "pending"
        uploaded_ids.append(response.json()["id"])

    listed = client.get(f"/api/v1/requests/{request_id}/documents", headers=submitter_headers)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 2
    assert {document["version_number"] for document in listed.json()} == {1}
    for document_id in uploaded_ids:
        result = client.get(f"/api/v1/documents/{document_id}/extraction", headers=submitter_headers)
        assert result.status_code == 200, result.text
        assert result.json()["status"] == "success", result.text

    receipt_extraction = client.get(
        f"/api/v1/documents/{uploaded_ids[1]}/extraction", headers=submitter_headers
    ).json()
    receipt_fields = {field["field_name"]: field["normalized_value"] for field in receipt_extraction["fields"]}
    assert receipt_fields["total_amount"] == "2000.00"
    assert receipt_fields["expense_date"] == "2026-10-22"
    assert receipt_fields["merchant_name"] == "Sample Transport Provider"

    submitted = client.post(f"/api/v1/requests/{request_id}/submit", headers=submitter_headers)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "under_review"
    reviewer_queue = client.get("/api/v1/requests/review-queue", headers=reviewer_headers)
    assert reviewer_queue.status_code == 200, reviewer_queue.text
    assert [item["id"] for item in reviewer_queue.json()] == [request_id]
    other_queue = client.get("/api/v1/requests/review-queue", headers=other_headers)
    assert other_queue.status_code == 200
    assert request_id not in {item["id"] for item in other_queue.json()}
    assert client.get(f"/api/v1/requests/{request_id}", headers=other_headers).status_code == 403

    receipt_id = uploaded_ids[1]
    stale_correction = client.post(f"/api/v1/requests/{request_id}/corrections", headers=reviewer_headers, json={
        "document_version_id": receipt_id,
        "field_name": "total_amount",
        "corrected_value": "2100.00",
        "original_extracted_value": "999.00",
        "reason": "Stale value must be rejected",
    })
    assert stale_correction.status_code == 409
    valid_correction = client.post(f"/api/v1/requests/{request_id}/corrections", headers=reviewer_headers, json={
        "document_version_id": receipt_id,
        "field_name": "total_amount",
        "corrected_value": "2000.00",
        "original_extracted_value": "2000.00",
        "reason": "Confirmed against the uploaded receipt text",
    })
    assert valid_correction.status_code == 201, valid_correction.text
    still_extracted = client.get(f"/api/v1/documents/{receipt_id}/extraction", headers=submitter_headers).json()
    assert next(field for field in still_extracted["fields"] if field["field_name"] == "total_amount")["normalized_value"] == "2000.00"

    reviewed = client.post(
        f"/api/v1/requests/{request_id}/complete-review",
        headers=reviewer_headers,
        json={"comment": "Native text evidence reviewed."},
    )
    assert reviewed.status_code == 200, reviewed.text
    approver_queue = client.get("/api/v1/requests/review-queue", headers=approver_headers)
    assert approver_queue.status_code == 200
    assert [item["id"] for item in approver_queue.json()] == [request_id]
    decision = client.post(
        f"/api/v1/requests/{request_id}/approve",
        headers=approver_headers,
        json={"comment": "Approved after reviewing extracted evidence."},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "approved"
    history = client.get(f"/api/v1/requests/{request_id}/history", headers=approver_headers)
    assert history.status_code == 200
    assert [entry["action_type"] for entry in history.json()] == [
        "assigned", "submitted", "submitted", "review_completed", "approved",
    ]
