"""
Authentication and authorization tests.

Run with:
    cd backend
    .venv/Scripts/pytest app/tests/test_auth.py -v
"""

from app.models.user import User, UserRole
from app.core.security import hash_password


DEMO_PASSWORD = "password123"

DEMO_USERS = [
    ("Alex Submitter", "submitter@example.com", UserRole.submitter),
    ("Riley Reviewer", "reviewer@example.com", UserRole.reviewer),
    ("Avery Approver", "approver@example.com", UserRole.approver),
]


def _register(client, name: str, email: str, role: UserRole) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": name,
            "email": email,
            "password": DEMO_PASSWORD,
            "role": role.value,
        },
    )
    assert response.status_code == 201, response.text


class TestLogin:
    def test_login_succeeds_for_provisioned_roles(self, client, db_session):
        # Privileged roles are provisioned internally, never via public signup.
        for name, email, role in DEMO_USERS:
            db_session.add(User(
                display_name=name,
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                role=role,
                is_active=True,
            ))
        db_session.commit()
        for _, email, role in DEMO_USERS:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": DEMO_PASSWORD},
            )
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["token_type"] == "bearer"
            assert data["access_token"]

            me = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {data['access_token']}"},
            )
            assert me.status_code == 200
            assert me.json()["email"] == email
            assert me.json()["role"] == role.value

    def test_wrong_password_returns_401(self, client):
        _register(client, "Test User", "user@example.com", UserRole.submitter)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    def test_unknown_email_returns_401(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": DEMO_PASSWORD},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    def test_reserved_demo_local_email_rejected_on_login(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "submitter@demo.local", "password": DEMO_PASSWORD},
        )
        assert response.status_code == 422

    def test_inactive_user_cannot_login(self, client, db_session):
        _register(client, "Inactive", "inactive@example.com", UserRole.submitter)
        user = db_session.query(User).filter(User.email == "inactive@example.com").one()
        user.is_active = False
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": DEMO_PASSWORD},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Account is disabled"


class TestRegistration:
    def test_public_registration_cannot_assign_privileged_role(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "display_name": "Escalation Attempt",
                "email": "escalation@example.com",
                "password": DEMO_PASSWORD,
                "role": "approver",
            },
        )
        assert response.status_code == 403

    def test_public_registration_defaults_to_submitter(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "display_name": "New User",
                "email": "newuser@example.com",
                "password": DEMO_PASSWORD,
            },
        )
        assert response.status_code == 201
        assert response.json()["role"] == "submitter"

    def test_invalid_email_rejected(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "display_name": "Bad Email",
                "email": "not-an-email",
                "password": DEMO_PASSWORD,
                "role": "submitter",
            },
        )
        assert response.status_code == 422

    def test_login_request_payload_uses_email_field(self, client):
        """Contract: login body must use `email`, not `username`."""
        _register(client, "Payload", "payload@example.com", UserRole.submitter)
        ok = client.post(
            "/api/v1/auth/login",
            json={"email": "payload@example.com", "password": DEMO_PASSWORD},
        )
        assert ok.status_code == 200

        bad = client.post(
            "/api/v1/auth/login",
            json={"username": "payload@example.com", "password": DEMO_PASSWORD},
        )
        assert bad.status_code == 422
