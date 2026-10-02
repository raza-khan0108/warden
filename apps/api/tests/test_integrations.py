from app.crypto import EncryptionManager
from app.models import Integration, Organization, User, OrgMembership
from app.schemas import IntegrationResponse


def test_encryption_manager():
    """Test encrypt/decrypt roundtrip."""
    manager = EncryptionManager()
    original_data = {
        "token": "ghu_test_token_123",
        "expires_at": "2026-10-03T14:00:00Z",
    }

    encrypted = manager.encrypt(original_data)
    assert isinstance(encrypted, str)
    assert encrypted != str(original_data)

    decrypted = manager.decrypt(encrypted)
    assert decrypted == original_data


def test_integration_model(db_session):
    """Test Integration model can be created and queried."""
    org = Organization(
        github_id=123456,
        slug="test-org",
        name="Test Org",
    )
    db_session.add(org)
    db_session.flush()

    manager = EncryptionManager()
    encrypted_creds = manager.encrypt({
        "token": "ghu_test_123",
        "expires_at": "2026-10-03T14:00:00Z",
    })

    integration = Integration(
        organization_id=org.id,
        type="github_app",
        installation_id=12345678,
        encrypted_creds=encrypted_creds,
    )
    db_session.add(integration)
    db_session.commit()

    retrieved = db_session.query(Integration).filter(
        Integration.organization_id == org.id,
        Integration.type == "github_app",
    ).first()

    assert retrieved is not None
    assert retrieved.installation_id == 12345678
    assert retrieved.organization_id == org.id

    decrypted = manager.decrypt(retrieved.encrypted_creds)
    assert decrypted["token"] == "ghu_test_123"


def test_integration_response_schema():
    """Test IntegrationResponse schema serialization."""
    response = IntegrationResponse(
        id=1,
        organization_id=1,
        type="github_app",
        installation_id=12345678,
        created_at="2026-10-02T10:00:00",
    )

    assert response.id == 1
    assert response.type == "github_app"
    assert response.installation_id == 12345678
