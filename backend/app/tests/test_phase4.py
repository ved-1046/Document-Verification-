"""Phase 4 verification tests for role-based authentication and workspace boundaries."""

from app.core.security import create_access_token, hash_password
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


def test_submitter_cannot_access_review_queue(client, db_session):
    submitter = _user(db_session, "submitter_phase4@example.com", UserRole.submitter)
    res = client.get("/api/v1/requests/review-queue", headers=_auth_headers(submitter))
    assert res.status_code == 403
    assert "Forbidden" in res.text or "not authorized" in res.text.lower() or "role" in res.text.lower()


def test_reviewer_cannot_create_requests(client, db_session):
    reviewer = _user(db_session, "reviewer_phase4@example.com", UserRole.reviewer)
    res = client.post(
        "/api/v1/requests",
        headers=_auth_headers(reviewer),
        json={"title": "Unauthorized claim", "request_type": "expense_reimbursement"},
    )
    assert res.status_code == 403


def test_reviewer_can_access_review_queue_assigned_to_them(client, db_session):
    submitter = _user(db_session, "sub_assigned@example.com", UserRole.submitter)
    reviewer1 = _user(db_session, "rev1_phase4@example.com", UserRole.reviewer)
    reviewer2 = _user(db_session, "rev2_phase4@example.com", UserRole.reviewer)

    req1 = Request(
        request_number="REQ-P4-001",
        request_type=RequestType.expense_reimbursement,
        title="Assigned to Rev1",
        submitter_id=submitter.id,
        assigned_reviewer_id=reviewer1.id,
        status=RequestStatus.under_review,
    )
    req2 = Request(
        request_number="REQ-P4-002",
        request_type=RequestType.expense_reimbursement,
        title="Assigned to Rev2",
        submitter_id=submitter.id,
        assigned_reviewer_id=reviewer2.id,
        status=RequestStatus.under_review,
    )
    db_session.add_all([req1, req2])
    db_session.commit()

    # Reviewer 1 should only see req1
    res1 = client.get("/api/v1/requests/review-queue", headers=_auth_headers(reviewer1))
    assert res1.status_code == 200
    ids1 = [item["id"] for item in res1.json()]
    assert req1.id in ids1
    assert req2.id not in ids1


def test_approver_can_access_decision_queue_assigned_to_them(client, db_session):
    submitter = _user(db_session, "sub_app_test@example.com", UserRole.submitter)
    approver1 = _user(db_session, "app1_phase4@example.com", UserRole.approver)
    approver2 = _user(db_session, "app2_phase4@example.com", UserRole.approver)

    req1 = Request(
        request_number="REQ-P4-003",
        request_type=RequestType.expense_reimbursement,
        title="Pending App1",
        submitter_id=submitter.id,
        assigned_approver_id=approver1.id,
        status=RequestStatus.pending_approval,
    )
    req2 = Request(
        request_number="REQ-P4-004",
        request_type=RequestType.expense_reimbursement,
        title="Pending App2",
        submitter_id=submitter.id,
        assigned_approver_id=approver2.id,
        status=RequestStatus.pending_approval,
    )
    db_session.add_all([req1, req2])
    db_session.commit()

    # Approver 1 should only see req1
    res1 = client.get("/api/v1/requests/review-queue", headers=_auth_headers(approver1))
    assert res1.status_code == 200
    ids1 = [item["id"] for item in res1.json()]
    assert req1.id in ids1
    assert req2.id not in ids1


def test_audit_log_access_restrictions(client, db_session):
    submitter = _user(db_session, "sub_audit_phase4@example.com", UserRole.submitter)
    reviewer = _user(db_session, "rev_audit_phase4@example.com", UserRole.reviewer)
    approver = _user(db_session, "app_audit_phase4@example.com", UserRole.approver)

    # Submitter forbidden
    res_sub = client.get("/api/v1/audit", headers=_auth_headers(submitter))
    assert res_sub.status_code == 403

    # Reviewer forbidden
    res_rev = client.get("/api/v1/audit", headers=_auth_headers(reviewer))
    assert res_rev.status_code == 403

    # Approver permitted
    res_app = client.get("/api/v1/audit", headers=_auth_headers(approver))
    assert res_app.status_code == 200
    assert isinstance(res_app.json(), list)


def test_reviewer_cannot_approve_or_reject(client, db_session):
    submitter = _user(db_session, "sub_norev_app@example.com", UserRole.submitter)
    reviewer = _user(db_session, "rev_norev_app@example.com", UserRole.reviewer)
    approver = _user(db_session, "app_target@example.com", UserRole.approver)

    req = Request(
        request_number="REQ-P4-005",
        request_type=RequestType.expense_reimbursement,
        title="Awaiting Approval",
        submitter_id=submitter.id,
        assigned_reviewer_id=reviewer.id,
        assigned_approver_id=approver.id,
        status=RequestStatus.pending_approval,
    )
    db_session.add(req)
    db_session.commit()

    # Reviewer attempting to approve
    res = client.post(
        f"/api/v1/requests/{req.id}/approve",
        headers=_auth_headers(reviewer),
        json={"comment": "Unauthorized approve attempt"},
    )
    assert res.status_code == 403
