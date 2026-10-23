"""Unit and integration tests for Evidence Impact Graph generation."""

import json
from app.core.security import create_access_token, hash_password
from app.models.document_version import DocumentVersion, DocType, ProcessingStatus
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.extracted_field import ExtractedField
from app.models.verification_check import (
    VerificationCheck, CheckType, CheckResult, CheckSeverity, ResolutionStatus,
)
from app.models.reviewer_correction import ReviewerCorrection
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


def test_evidence_graph_unauthenticated(client):
    res = client.get("/api/v1/requests/1/evidence-graph")
    assert res.status_code == 401


def test_evidence_graph_unauthorized_user(client, db_session):
    owner = _user(db_session, "owner_graph@example.com", UserRole.submitter)
    other = _user(db_session, "other_graph@example.com", UserRole.submitter)

    req = Request(
        request_number="REQ-GRAPH-001",
        request_type=RequestType.expense_reimbursement,
        title="Owner's Request",
        submitter_id=owner.id,
        status=RequestStatus.draft,
    )
    db_session.add(req)
    db_session.commit()

    res = client.get(f"/api/v1/requests/{req.id}/evidence-graph", headers=_auth_headers(other))
    assert res.status_code == 403


def test_evidence_graph_empty_draft_request(client, db_session):
    submitter = _user(db_session, "sub_empty_graph@example.com", UserRole.submitter)
    req = Request(
        request_number="REQ-GRAPH-002",
        request_type=RequestType.expense_reimbursement,
        title="Empty Draft",
        submitter_id=submitter.id,
        status=RequestStatus.draft,
    )
    db_session.add(req)
    db_session.commit()

    res = client.get(f"/api/v1/requests/{req.id}/evidence-graph", headers=_auth_headers(submitter))
    assert res.status_code == 200
    data = res.json()
    assert data["request_id"] == req.id
    assert data["request_number"] == "REQ-GRAPH-002"
    assert data["request_status"] == "draft"

    # Only 1 decision node, 0 docs, 0 fields, 0 findings
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["type"] == "decision"
    assert data["summary"]["total_documents"] == 0
    assert data["summary"]["total_extracted_fields"] == 0
    assert data["summary"]["total_findings"] == 0


def test_evidence_graph_with_documents_fields_and_checks(client, db_session):
    submitter = _user(db_session, "sub_full_graph@example.com", UserRole.submitter)
    reviewer = _user(db_session, "rev_full_graph@example.com", UserRole.reviewer)

    req = Request(
        request_number="REQ-GRAPH-003",
        request_type=RequestType.expense_reimbursement,
        title="Conference Expense",
        submitter_id=submitter.id,
        assigned_reviewer_id=reviewer.id,
        status=RequestStatus.under_review,
        claimed_amount="450.00",
        currency="INR",
    )
    db_session.add(req)
    db_session.commit()

    # Uploaded receipt document
    doc = DocumentVersion(
        request_id=req.id,
        doc_type=DocType.receipt,
        original_filename="receipt.pdf",
        mime_type="application/pdf",
        file_size=10240,
        file_hash="hash123",
        storage_key="receipt.pdf",
        version_number=1,
        uploader_id=submitter.id,
        processing_status=ProcessingStatus.ready,
    )
    db_session.add(doc)
    db_session.commit()

    # Extraction run with fields
    run = ExtractionRun(
        document_version_id=doc.id,
        ocr_engine="tesseract",
        status=ExtractionStatus.success,
    )
    db_session.add(run)
    db_session.commit()

    field_merchant = ExtractedField(
        extraction_run_id=run.id,
        field_name="merchant_name",
        extracted_value="ABC Stationery",
        normalized_value="ABC Stationery",
        confidence=0.95,
        page_number=1,
    )
    field_amount = ExtractedField(
        extraction_run_id=run.id,
        field_name="total_amount",
        extracted_value="450.00",
        normalized_value="450.00",
        confidence=0.92,
        page_number=1,
    )
    db_session.add_all([field_merchant, field_amount])

    # Verification checks
    check_amount = VerificationCheck(
        request_id=req.id,
        check_type=CheckType.amount_mismatch,
        rule_name="amount_comparison_check",
        result=CheckResult.pass_,
        severity=CheckSeverity.medium,
        explanation="Amounts match successfully",
        resolution_status=ResolutionStatus.resolved,
        is_current=True,
    )
    check_req_fields = VerificationCheck(
        request_id=req.id,
        check_type=CheckType.missing_field,
        rule_name="required_fields_check",
        result=CheckResult.flag,
        severity=CheckSeverity.low,
        explanation="Date was not detected",
        evidence_references=json.dumps([{
            "doc_version_id": doc.id,
            "missing_fields": ["expense_date"],
            "found_fields": ["merchant_name", "total_amount"],
        }]),
        resolution_status=ResolutionStatus.open,
        is_current=True,
    )
    db_session.add_all([check_amount, check_req_fields])
    db_session.commit()

    res = client.get(f"/api/v1/requests/{req.id}/evidence-graph", headers=_auth_headers(reviewer))
    assert res.status_code == 200
    data = res.json()

    # Verify node types
    node_types = [n["type"] for n in data["nodes"]]
    assert "document" in node_types
    assert "field" in node_types
    assert "finding" in node_types
    assert "decision" in node_types

    # Verify document node
    doc_node = next(n for n in data["nodes"] if n["type"] == "document")
    assert doc_node["data"]["original_filename"] == "receipt.pdf"
    assert doc_node["status"] == "ready"

    # Verify field nodes
    merchant_node = next(n for n in data["nodes"] if n["type"] == "field" and n["data"]["field_name"] == "merchant_name")
    assert merchant_node["data"]["effective_value"] == "ABC Stationery"
    assert merchant_node["data"]["confidence"] == 0.95

    # Verify finding nodes
    finding_nodes = [n for n in data["nodes"] if n["type"] == "finding"]
    assert len(finding_nodes) == 2

    # Verify edges
    edge_sources = [e["source"] for e in data["edges"]]
    edge_targets = [e["target"] for e in data["edges"]]
    assert doc_node["id"] in edge_sources
    assert merchant_node["id"] in edge_targets

    # Summary
    assert data["summary"]["total_documents"] == 1
    assert data["summary"]["total_extracted_fields"] == 2
    assert data["summary"]["total_findings"] == 2
    assert data["summary"]["passed_findings"] == 1
    assert data["summary"]["flagged_findings"] == 1


def test_evidence_graph_with_reviewer_corrections(client, db_session):
    submitter = _user(db_session, "sub_corr_graph@example.com", UserRole.submitter)
    reviewer = _user(db_session, "rev_corr_graph@example.com", UserRole.reviewer)

    req = Request(
        request_number="REQ-GRAPH-004",
        request_type=RequestType.expense_reimbursement,
        title="Correction Test",
        submitter_id=submitter.id,
        assigned_reviewer_id=reviewer.id,
        status=RequestStatus.under_review,
    )
    db_session.add(req)
    db_session.commit()

    doc = DocumentVersion(
        request_id=req.id,
        doc_type=DocType.receipt,
        original_filename="receipt.jpg",
        mime_type="image/jpeg",
        file_size=5000,
        file_hash="hash456",
        storage_key="receipt.jpg",
        version_number=1,
        uploader_id=submitter.id,
        processing_status=ProcessingStatus.ready,
    )
    db_session.add(doc)
    db_session.commit()

    run = ExtractionRun(
        document_version_id=doc.id,
        ocr_engine="tesseract",
        status=ExtractionStatus.success,
    )
    db_session.add(run)
    db_session.commit()

    field = ExtractedField(
        extraction_run_id=run.id,
        field_name="merchant_name",
        extracted_value="ABC Statioery",
        normalized_value="ABC Statioery",
        confidence=0.55,
    )
    db_session.add(field)
    db_session.commit()

    # Reviewer records correction
    correction = ReviewerCorrection(
        request_id=req.id,
        document_version_id=doc.id,
        field_name="merchant_name",
        original_extracted_value="ABC Statioery",
        corrected_value="ABC Stationery",
        reviewer_id=reviewer.id,
        reason="Fixed OCR spelling typo from source receipt header",
    )
    db_session.add(correction)
    db_session.commit()

    res = client.get(f"/api/v1/requests/{req.id}/evidence-graph", headers=_auth_headers(reviewer))
    assert res.status_code == 200
    data = res.json()

    merchant_node = next(n for n in data["nodes"] if n["type"] == "field" and n["data"]["field_name"] == "merchant_name")
    assert merchant_node["data"]["is_corrected"] is True
    assert merchant_node["data"]["effective_value"] == "ABC Stationery"
    assert merchant_node["data"]["correction_reason"] == "Fixed OCR spelling typo from source receipt header"
    assert merchant_node["status"] == "verified"
