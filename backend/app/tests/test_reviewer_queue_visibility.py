"""
Targeted tests for Reviewer Queue visibility, assignee isolation, and submission lifecycle.
"""
from decimal import Decimal
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.request import Request, RequestStatus, RequestType
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token


def _make_user(db: Session, email: str, role: UserRole, name: str) -> User:
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


def test_draft_does_not_appear_in_reviewer_queue(client: TestClient, db_session: Session):
    sub = _make_user(db_session, "sub_test_1@test.com", UserRole.submitter, "Sub 1")
    rev = _make_user(db_session, "rev_test_1@test.com", UserRole.reviewer, "Rev 1")
    app = _make_user(db_session, "app_test_1@test.com", UserRole.approver, "App 1")

    # Create draft
    req = Request(
        request_number="REQ-TEST-DRAFT",
        request_type=RequestType.expense_reimbursement,
        title="Draft Claim",
        claimed_amount=Decimal("100.00"),
        expense_date=date.today(),
        currency="INR",
        submitter_id=sub.id,
        assigned_reviewer_id=rev.id,
        assigned_approver_id=app.id,
        status=RequestStatus.draft,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    # Reviewer checks queue
    res = client.get("/api/v1/requests/review-queue", headers=_auth(rev))
    assert res.status_code == 200
    ids = [i["id"] for i in res.json()]
    assert req.id not in ids, "Draft must not appear in review queue"


def test_submitted_statuses_appear_in_reviewer_queue(client: TestClient, db_session: Session):
    sub = _make_user(db_session, "sub_test_2@test.com", UserRole.submitter, "Sub 2")
    rev = _make_user(db_session, "rev_test_2@test.com", UserRole.reviewer, "Rev 2")
    app = _make_user(db_session, "app_test_2@test.com", UserRole.approver, "App 2")

    for st in [RequestStatus.submitted, RequestStatus.processing, RequestStatus.under_review, RequestStatus.more_info_required]:
        req = Request(
            request_number=f"REQ-TEST-{st.value}",
            request_type=RequestType.expense_reimbursement,
            title=f"Claim {st.value}",
            claimed_amount=Decimal("100.00"),
            expense_date=date.today(),
            currency="INR",
            submitter_id=sub.id,
            assigned_reviewer_id=rev.id,
            assigned_approver_id=app.id,
            status=st,
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        # Reviewer checks queue
        res = client.get("/api/v1/requests/review-queue", headers=_auth(rev))
        assert res.status_code == 200
        ids = [i["id"] for i in res.json()]
        assert req.id in ids, f"Status {st.value} should appear in assigned reviewer queue"


def test_other_reviewer_cannot_see_or_access_claim(client: TestClient, db_session: Session):
    sub = _make_user(db_session, "sub_test_3@test.com", UserRole.submitter, "Sub 3")
    rev1 = _make_user(db_session, "rev_test_3a@test.com", UserRole.reviewer, "Rev 3A")
    rev2 = _make_user(db_session, "rev_test_3b@test.com", UserRole.reviewer, "Rev 3B")
    app = _make_user(db_session, "app_test_3@test.com", UserRole.approver, "App 3")

    req = Request(
        request_number="REQ-TEST-ISOLATION",
        request_type=RequestType.expense_reimbursement,
        title="Assigned to Rev 1",
        claimed_amount=Decimal("150.00"),
        expense_date=date.today(),
        currency="INR",
        submitter_id=sub.id,
        assigned_reviewer_id=rev1.id,
        assigned_approver_id=app.id,
        status=RequestStatus.under_review,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    # rev1 sees it
    res1 = client.get("/api/v1/requests/review-queue", headers=_auth(rev1))
    assert req.id in [i["id"] for i in res1.json()]

    # rev2 does NOT see it
    res2 = client.get("/api/v1/requests/review-queue", headers=_auth(rev2))
    assert req.id not in [i["id"] for i in res2.json()]

    # rev2 gets 403 trying to GET the request directly
    detail_res = client.get(f"/api/v1/requests/{req.id}", headers=_auth(rev2))
    assert detail_res.status_code == 403


def test_approver_only_sees_pending_approval(client: TestClient, db_session: Session):
    sub = _make_user(db_session, "sub_test_4@test.com", UserRole.submitter, "Sub 4")
    rev = _make_user(db_session, "rev_test_4@test.com", UserRole.reviewer, "Rev 4")
    app = _make_user(db_session, "app_test_4@test.com", UserRole.approver, "App 4")

    req_review = Request(
        request_number="REQ-TEST-REV-ONLY",
        request_type=RequestType.expense_reimbursement,
        title="Under Review Claim",
        claimed_amount=Decimal("200.00"),
        expense_date=date.today(),
        currency="INR",
        submitter_id=sub.id,
        assigned_reviewer_id=rev.id,
        assigned_approver_id=app.id,
        status=RequestStatus.under_review,
    )
    req_app = Request(
        request_number="REQ-TEST-APP-ONLY",
        request_type=RequestType.expense_reimbursement,
        title="Pending Approval Claim",
        claimed_amount=Decimal("300.00"),
        expense_date=date.today(),
        currency="INR",
        submitter_id=sub.id,
        assigned_reviewer_id=rev.id,
        assigned_approver_id=app.id,
        status=RequestStatus.pending_approval,
    )
    db_session.add(req_review)
    db_session.add(req_app)
    db_session.commit()
    db_session.refresh(req_review)
    db_session.refresh(req_app)

    # Approver checks queue
    res = client.get("/api/v1/requests/review-queue", headers=_auth(app))
    assert res.status_code == 200
    ids = [i["id"] for i in res.json()]
    assert req_app.id in ids, "Pending approval claim must appear for approver"
    assert req_review.id not in ids, "Under review claim must NOT appear for approver"


def test_double_submission_prevented(client: TestClient, db_session: Session):
    sub = _make_user(db_session, "sub_test_5@test.com", UserRole.submitter, "Sub 5")
    rev = _make_user(db_session, "rev_test_5@test.com", UserRole.reviewer, "Rev 5")
    app = _make_user(db_session, "app_test_5@test.com", UserRole.approver, "App 5")

    req = Request(
        request_number="REQ-TEST-DOUBLE",
        request_type=RequestType.expense_reimbursement,
        title="Already Under Review",
        claimed_amount=Decimal("500.00"),
        expense_date=date.today(),
        currency="INR",
        submitter_id=sub.id,
        assigned_reviewer_id=rev.id,
        assigned_approver_id=app.id,
        status=RequestStatus.under_review,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    res = client.post(f"/api/v1/requests/{req.id}/submit", headers=_auth(sub))
    assert res.status_code == 422
    assert "already in 'under review' status" in res.json()["detail"].lower()


def test_submitter_can_assign_reviewer_on_draft(client: TestClient, db_session: Session):
    sub = _make_user(db_session, "sub_test_6@test.com", UserRole.submitter, "Sub 6")
    rev = _make_user(db_session, "rev_test_6@test.com", UserRole.reviewer, "Rev 6")
    app = _make_user(db_session, "app_test_6@test.com", UserRole.approver, "App 6")

    req = Request(
        request_number="REQ-TEST-UNASSIGNED",
        request_type=RequestType.expense_reimbursement,
        title="Unassigned Draft",
        claimed_amount=Decimal("500.00"),
        expense_date=date.today(),
        currency="INR",
        submitter_id=sub.id,
        assigned_reviewer_id=None,
        assigned_approver_id=None,
        status=RequestStatus.draft,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    # Submitter updates assignees
    res = client.patch(
        f"/api/v1/requests/{req.id}/assignment",
        json={"assigned_reviewer_id": rev.id, "assigned_approver_id": app.id},
        headers=_auth(sub),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["assigned_reviewer_id"] == rev.id
    assert data["assigned_approver_id"] == app.id
