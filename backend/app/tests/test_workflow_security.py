"""Regression coverage for authorization and request submission requirements."""

from app.core.security import hash_password, create_access_token
from app.models.request import Request, RequestStatus, RequestType
from app.models.user import User, UserRole


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def _user(db_session, email: str, role: UserRole) -> User:
    user = User(
        display_name=email.split("@")[0],
        email=email,
        password_hash=hash_password("password123"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_requests_reject_unauthenticated_access(client):
    assert client.get("/api/v1/requests").status_code == 401


def test_submitter_cannot_submit_without_expense_form_and_receipt(client, db_session):
    submitter = _user(db_session, "owner@example.com", UserRole.submitter)
    headers = _auth_headers(submitter)
    created = client.post(
        "/api/v1/requests",
        headers=headers,
        json={"title": "Travel expense", "request_type": "expense_reimbursement"},
    )
    assert created.status_code == 201, created.text

    response = client.post(
        f"/api/v1/requests/{created.json()['id']}/submit",
        headers=headers,
    )
    assert response.status_code == 422
    assert "expense form" in response.json()["detail"]
    assert "receipt" in response.json()["detail"]


def test_approver_cannot_approve_own_request(client, db_session):
    approver = _user(db_session, "self-approver@example.com", UserRole.approver)
    req = Request(
        request_number="REQ-2099-9999",
        request_type=RequestType.expense_reimbursement,
        title="Self approval attempt",
        submitter_id=approver.id,
        status=RequestStatus.under_review,
    )
    db_session.add(req)
    db_session.commit()

    response = client.post(
        f"/api/v1/requests/{req.id}/approve",
        headers=_auth_headers(approver),
        json={"comment": "I approve this request"},
    )
    assert response.status_code == 403
    db_session.refresh(req)
    assert req.status == RequestStatus.under_review
