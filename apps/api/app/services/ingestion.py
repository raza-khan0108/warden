import hashlib
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Document, IngestionJob, Repository
from app.services.github import GitHubClient


class IngestionService:
    """Handles repo ingestion: fetching code, creating documents, queuing jobs."""

    def __init__(self, db: Session, github_client: GitHubClient):
        self.db = db
        self.github = github_client

    def create_ingestion_job(
        self,
        org_id: int,
        repo_id: int,
        kind: str,
    ) -> IngestionJob:
        """Create a new ingestion job and queue it for processing."""
        job = IngestionJob(
            organization_id=org_id,
            repository_id=repo_id,
            kind=kind,
            status="pending",
        )
        self.db.add(job)
        self.db.commit()
        return job

    def fetch_repo_files(
        self,
        repo_id: int,
        org_id: int,
    ) -> list[dict]:
        """Fetch all files from a repository via GitHub API and create documents.

        Returns list of created documents.
        """
        repo = self.db.query(Repository).filter(
            Repository.id == repo_id,
            Repository.organization_id == org_id,
        ).first()

        if not repo:
            raise ValueError(f"Repository {repo_id} not found for org {org_id}")

        tree, truncated = self.github.get_tree(repo.full_name, repo.default_branch)

        if truncated:
            raise ValueError(
                f"Repository {repo.full_name} is too large (>100k files), truncated tree"
            )

        documents = []
        for entry in tree:
            if entry["type"] != "blob":
                continue

            path = entry["path"]
            sha = entry["sha"]

            doc = self._create_or_update_document(
                org_id=org_id,
                repo_id=repo_id,
                path=path,
                commit_sha=sha,
                source_type="code",
            )
            documents.append(doc)

        self.db.commit()
        return documents

    def _create_or_update_document(
        self,
        org_id: int,
        repo_id: int,
        path: str,
        commit_sha: str,
        source_type: str,
        content_hash: str | None = None,
    ) -> Document:
        """Create or update a document record."""
        if not content_hash:
            content_hash = hashlib.sha256(path.encode()).hexdigest()

        existing = self.db.query(Document).filter(
            Document.repository_id == repo_id,
            Document.source_type == source_type,
            Document.path == path,
            Document.commit_sha == commit_sha,
        ).first()

        if existing:
            existing.version += 1
            existing.updated_at = datetime.now()
            return existing

        doc = Document(
            organization_id=org_id,
            repository_id=repo_id,
            source_type=source_type,
            path=path,
            commit_sha=commit_sha,
            content_hash=content_hash,
            version=1,
        )
        self.db.add(doc)
        return doc
