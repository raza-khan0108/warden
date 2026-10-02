from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.crypto import get_encryption_manager, EncryptionManager
from app.db import get_db
from app.models import Integration, Organization
from app.schemas import (
    GitHubAppInstallResponse,
    IntegrationResponse,
)

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
    setup_action: Annotated[str, Query()] = "created",
    org_id: Annotated[int, Query()] = None,
    db: Annotated[Session, Depends(get_db)] = None,
    encryption: Annotated[EncryptionManager, Depends(get_encryption_manager)] = None,
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
        )


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
