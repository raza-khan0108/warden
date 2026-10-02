import pytest
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from app.models import Document
from app.services.github import GitHubClient
from app.services.ingestion import IngestionService


@pytest.fixture
def mock_github_client():
    """Mock GitHub client that returns test data."""
    client = MagicMock(spec=GitHubClient)
    client.get_tree.return_value = (
        [
            {
                "path": "README.md",
                "type": "blob",
                "sha": "abc123",
            },
            {
                "path": "src/main.py",
                "type": "blob",
                "sha": "def456",
            },
            {
                "path": "src",
                "type": "tree",
                "sha": "tree123",
            },
        ],
        False,
    )
    return client


def test_create_ingestion_job(db_session: Session, org, repo):
    """Test creating an ingestion job."""
    client = MagicMock(spec=GitHubClient)
    service = IngestionService(db_session, client)

    job = service.create_ingestion_job(
        org_id=org.id,
        repo_id=repo.id,
        kind="clone",
    )

    assert job.organization_id == org.id
    assert job.repository_id == repo.id
    assert job.kind == "clone"
    assert job.status == "pending"
    assert job.attempts == 0


def test_fetch_repo_files(
    db_session: Session,
    org,
    repo,
    mock_github_client,
):
    """Test fetching repo files and creating documents."""
    service = IngestionService(db_session, mock_github_client)

    documents = service.fetch_repo_files(repo.id, org.id)

    assert len(documents) == 2
    assert documents[0].path == "README.md"
    assert documents[0].source_type == "code"
    assert documents[1].path == "src/main.py"

    db_docs = db_session.query(Document).filter(
        Document.repository_id == repo.id,
    ).all()
    assert len(db_docs) == 2


def test_fetch_repo_files_not_found(db_session: Session, mock_github_client):
    """Test fetching files for a non-existent repo."""
    service = IngestionService(db_session, mock_github_client)

    with pytest.raises(ValueError, match="Repository .* not found"):
        service.fetch_repo_files(repo_id=9999, org_id=9999)


def test_fetch_repo_files_truncated(db_session: Session, org, repo):
    """Test handling truncated repository tree."""
    client = MagicMock(spec=GitHubClient)
    client.get_tree.return_value = ([], True)

    service = IngestionService(db_session, client)

    with pytest.raises(ValueError, match="too large"):
        service.fetch_repo_files(repo.id, org.id)
