import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import Organization, Repository

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def org(db_session):
    """Create a test organization."""
    org = Organization(
        github_id=1,
        slug="test-org",
        name="Test Organization",
    )
    db_session.add(org)
    db_session.commit()
    return org


@pytest.fixture
def repo(db_session, org):
    """Create a test repository."""
    repo = Repository(
        organization_id=org.id,
        full_name="test-org/test-repo",
        owner="test-org",
        name="test-repo",
        default_branch="main",
        description="A test repository",
        html_url="https://github.com/test-org/test-repo",
        status="pending",
    )
    db_session.add(repo)
    db_session.commit()
    return repo
