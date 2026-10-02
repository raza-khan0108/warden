from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Repository
from app.schemas import CurrentUser, IngestionJobResponse, RepositoryResponse
from app.services.github import GitHubClient, build_github_client
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _verify_org_access(org_id: int, current_user: CurrentUser) -> None:
    """Helper: verify user has access to organization."""
    if current_user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization",
        )


@router.post("/repos/{org_id}/{repo_id}/sync")
async def sync_repository(
    org_id: int,
    repo_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    github_client: Annotated[GitHubClient, Depends(build_github_client)],
) -> RepositoryResponse:
    """Trigger a repository sync: fetch files and create documents.

    This endpoint queues an ingestion job to fetch the repo's file tree
    from GitHub and create document records for each file.
    """
    _verify_org_access(org_id, current_user)

    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.organization_id == org_id,
    ).first()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    if repo.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository sync already started (status: {repo.status})",
        )

    repo.status = "indexing"
    db.commit()

    service = IngestionService(db, github_client)
    try:
        service.fetch_repo_files(repo_id, org_id)
        repo.status = "ready"
        repo.last_synced_at = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )
    except Exception as e:
        repo.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync repository: {str(e)}",
        ) from e

    db.commit()
    return RepositoryResponse.model_validate(repo)


@router.get("/repos/{org_id}/{repo_id}/status")
async def get_repo_status(
    org_id: int,
    repo_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RepositoryResponse:
    """Get the current ingestion status of a repository."""
    _verify_org_access(org_id, current_user)

    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.organization_id == org_id,
    ).first()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    return RepositoryResponse.model_validate(repo)
