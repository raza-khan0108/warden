import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import create_access_token, decode_access_token
from app.main import app
from app.models import Organization, OrgMembership, User


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """Test public health endpoint."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_db_endpoint(client):
    """Test database health check."""
    resp = client.get("/health/db")
    assert resp.status_code == 200
    data = resp.json()
    assert data["database"] == "ok"
    assert "pgvector" in data


def test_github_login_url(client):
    """Test GitHub login URL generation."""
    resp = client.get("/auth/github/login")
    assert resp.status_code == 200
    data = resp.json()
    assert "login_url" in data
    assert "github.com/login/oauth/authorize" in data["login_url"]
    assert "client_id" in data["login_url"]


def test_create_and_decode_token():
    """Test JWT token creation and decoding."""
    user_id = 123
    org_id = 456
    role = "owner"

    token = create_access_token(user_id, org_id, role)
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["user_id"] == user_id
    assert payload["org_id"] == org_id
    assert payload["role"] == role


def test_protected_endpoint_requires_auth(client):
    """Test that protected endpoints require authentication."""
    resp = client.get("/health/protected")
    assert resp.status_code == 403


def test_protected_endpoint_with_valid_token(client, db: Session):
    """Test protected endpoint with valid token."""
    user = User(
        github_id=1,
        github_login="testuser",
        name="Test User",
        email="test@example.com",
    )
    org = Organization(
        github_id=1,
        slug="test-org",
        name="Test Org",
    )
    db.add(user)
    db.add(org)
    db.flush()

    membership = OrgMembership(
        user_id=user.id,
        organization_id=org.id,
        role="owner",
    )
    db.add(membership)
    db.commit()

    token = create_access_token(user.id, org.id, "owner")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/health/protected", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"] == "testuser"
    assert data["org_id"] == org.id
