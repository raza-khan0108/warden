from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.crypto import EncryptionManager, get_encryption_manager
from app.db import get_db
from app.models import Integration, Organization, Repository
from app.schemas import (
    GitHubAppInstallResponse,
    IntegrationResponse,
    RepositoryResponse,
)
from app.services.github import GitHubClient, GitHubError

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/github/install-url")
async def github_install_url() -> dict[str, str]:
    """Return the GitHub App installation URL for the user to authorize."""
    client_id = settings.github_app_id
    redirect_uri = "http://localhost:8000/integrations/github/install"
    state = "warden-install"

    url = (
        f"https://github.com/apps/{client_id}/installations/new?"
        f"redirect_uri={redirect_uri}&"
        f"state={state}"
    )
    return {"install_url": url}


@router.post("/github/install")
async def github_install(
    installation_id: Annotated[int, Query()],
    db: Annotated[Session, Depends(get_db)],
    encryption: Annotated[EncryptionManager, Depends(get_encryption_manager)],
    setup_action: Annotated[str, Query()] = "created",
    org_id: Annotated[int | None, Query()] = None,
) -> GitHubAppInstallResponse:
    """Handle GitHub App installation callback.

    GitHub redirects here after user authorizes the app on an org.
    We store the installation_id and fetch the app's credentials.
    """
    if not installation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing installation_id",
        )

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing org_id query param (required for tenant isolation)",
        )

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "warden",
            }
            resp = await client.get(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers=headers,
                auth=(settings.github_app_id, settings.github_app_client_secret),
            )
            resp.raise_for_status()
            token_data = resp.json()

        encrypted_creds = encryption.encrypt({
            "token": token_data.get("token"),
            "expires_at": token_data.get("expires_at"),
        })

        existing = db.query(Integration).filter(
            Integration.organization_id == org_id,
            Integration.type == "github_app",
        ).first()

        if existing:
            existing.installation_id = installation_id
            existing.encrypted_creds = encrypted_creds
        else:
            integration = Integration(
                organization_id=org_id,
                type="github_app",
                installation_id=installation_id,
                encrypted_creds=encrypted_creds,
            )
            db.add(integration)

        db.commit()

        return GitHubAppInstallResponse(
            success=True,
            message=f"GitHub App installed successfully for org {org.slug}",
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch GitHub App token: {str(e)}",
        ) from e


@router.get("/{org_id}")
async def list_integrations(
    org_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[IntegrationResponse]:
    """List all integrations for an organization."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    integrations = db.query(Integration).filter(
        Integration.organization_id == org_id
    ).all()

    return [IntegrationResponse.model_validate(i) for i in integrations]


@router.get("/{org_id}/{integration_type}")
async def get_integration(
    org_id: int,
    integration_type: str,
    db: Annotated[Session, Depends(get_db)],
) -> IntegrationResponse:
    """Get a specific integration for an organization."""
    integration = db.query(Integration).filter(
        Integration.organization_id == org_id,
        Integration.type == integration_type,
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration type '{integration_type}' not found for this organization",
        )

    return IntegrationResponse.model_validate(integration)


@router.post("/{org_id}/github/add-repositories")
async def add_github_repositories(
    org_id: int,
    db: Annotated[Session, Depends(get_db)],
    encryption: Annotated[EncryptionManager, Depends(get_encryption_manager)],
) -> list[RepositoryResponse]:
    """Fetch accessible repositories from GitHub and create repository records.

    This endpoint should be called after GitHub App installation to sync
    the list of repositories the app can access.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    integration = db.query(Integration).filter(
        Integration.organization_id == org_id,
        Integration.type == "github_app",
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub App not installed for this organization",
        )

    creds = encryption.decrypt(integration.encrypted_creds)
    token = creds.get("token")

    try:
        github_client = GitHubClient(token=token)
        installations_resp = github_client._get(
            f"/app/installations/{integration.installation_id}",
        )
        account = installations_resp.get("account", {})
        org_login = account.get("login")

        if not org_login:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not determine GitHub organization login",
            )

        repos_resp = github_client._get(
            "/installation/repositories",
            per_page=100,
        )
        gh_repos = repos_resp.get("repositories", [])

        created_repos = []
        for gh_repo in gh_repos:
            existing = db.query(Repository).filter(
                Repository.organization_id == org_id,
                Repository.full_name == gh_repo["full_name"],
            ).first()

            if existing:
                repo = existing
            else:
                repo = Repository(
                    organization_id=org_id,
                    full_name=gh_repo["full_name"],
                    owner=gh_repo["owner"]["login"],
                    name=gh_repo["name"],
                    default_branch=gh_repo.get("default_branch", "main"),
                    description=gh_repo.get("description"),
                    html_url=gh_repo["html_url"],
                    status="pending",
                )
                db.add(repo)

            created_repos.append(repo)

        db.commit()
        return [RepositoryResponse.model_validate(r) for r in created_repos]

    except GitHubError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch repositories: {str(e)}",
        ) from e
