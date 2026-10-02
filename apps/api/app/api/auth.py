from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    fetch_github_org_membership,
    fetch_github_user,
    fetch_github_user_orgs,
    upsert_membership,
    upsert_organization,
    upsert_user,
)
from app.config import settings
from app.db import get_db
from app.schemas import OrganizationResponse, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/github/login")
async def github_login_url() -> dict[str, str]:
    """Return the GitHub OAuth login URL. Client redirects here to start OAuth flow."""
    redirect_uri = "http://localhost:8000/auth/github/callback"
    client_id = settings.github_app_id
    scopes = "user:email read:org"

    url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scopes}&"
        f"state=warden"
    )
    return {"login_url": url}


@router.get("/github/callback")
async def github_callback(
    code: Annotated[str, Query()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Handle GitHub OAuth callback. Exchange code for access token."""
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code")

    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": settings.github_app_id,
                    "client_secret": settings.github_app_private_key,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"GitHub OAuth error: {token_data['error_description']}",
            )

        github_access_token = token_data["access_token"]

        github_user = await fetch_github_user(github_access_token)
        user = upsert_user(db, github_user)

        github_orgs = await fetch_github_user_orgs(github_access_token)

        if not github_orgs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of any organizations",
            )

        primary_org_data = github_orgs[0]
        primary_org = upsert_organization(db, primary_org_data)

        membership_data = await fetch_github_org_membership(
            github_access_token, primary_org_data["login"]
        )
        role = membership_data.get("role", "member")
        membership = upsert_membership(db, user.id, primary_org.id, role)

        db.commit()

        access_token = create_access_token(user.id, primary_org.id, membership.role)

        return TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
            organization=OrganizationResponse.model_validate(primary_org),
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub API error: {str(e)}",
        ) from e
