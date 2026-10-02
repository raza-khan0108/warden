from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Organization, OrgMembership, User
from app.schemas import CurrentUser


async def fetch_github_user(access_token: str) -> dict[str, Any]:
    """Fetch authenticated user info from GitHub API."""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.get("https://api.github.com/user", headers=headers)
        resp.raise_for_status()
        return resp.json()


async def fetch_github_user_orgs(access_token: str) -> list[dict[str, Any]]:
    """Fetch user's organizations from GitHub API."""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.get("https://api.github.com/user/orgs", headers=headers)
        resp.raise_for_status()
        return resp.json()


async def fetch_github_org_membership(access_token: str, org: str) -> dict[str, Any]:
    """Fetch user's role in a specific organization."""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.get(
            f"https://api.github.com/user/memberships/orgs/{org}", headers=headers
        )
        if resp.status_code == 404:
            return {"role": ""}
        resp.raise_for_status()
        return resp.json()


def create_access_token(user_id: int, org_id: int, role: str) -> str:
    """Create a JWT access token."""
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    payload = {
        "user_id": user_id,
        "org_id": org_id,
        "role": role,
        "exp": expires,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),  # noqa: B008
) -> CurrentUser:
    """FastAPI dependency: extract current user from JWT token in Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]
    payload = decode_access_token(token)
    user_id = payload.get("user_id")
    org_id = payload.get("org_id")
    role = payload.get("role", "member")

    if not user_id or not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return CurrentUser(
        id=user_id,
        github_login=user.github_login,
        organization_id=org_id,
        role=role,
    )


def upsert_user(db: Session, github_user: dict[str, Any]) -> User:
    """Create or update a user from GitHub API response."""
    user = db.query(User).filter(User.github_id == github_user["id"]).first()

    if user:
        user.github_login = github_user["login"]
        user.name = github_user.get("name")
        user.email = github_user.get("email")
        user.avatar_url = github_user.get("avatar_url")
        user.updated_at = datetime.now(timezone.utc)
    else:
        user = User(
            github_id=github_user["id"],
            github_login=github_user["login"],
            name=github_user.get("name"),
            email=github_user.get("email"),
            avatar_url=github_user.get("avatar_url"),
        )
        db.add(user)

    db.flush()
    return user


def upsert_organization(db: Session, github_org: dict[str, Any]) -> Organization:
    """Create or update an organization from GitHub API response."""
    org = db.query(Organization).filter(Organization.github_id == github_org["id"]).first()

    if org:
        org.slug = github_org["login"]
        org.name = github_org.get("name") or github_org["login"]
        org.avatar_url = github_org.get("avatar_url")
        org.updated_at = datetime.now(timezone.utc)
    else:
        org = Organization(
            github_id=github_org["id"],
            slug=github_org["login"],
            name=github_org.get("name") or github_org["login"],
            avatar_url=github_org.get("avatar_url"),
        )
        db.add(org)

    db.flush()
    return org


def upsert_membership(
    db: Session, user_id: int, organization_id: int, role: str
) -> OrgMembership:
    """Create or update an org membership."""
    membership = db.query(OrgMembership).filter(
        OrgMembership.user_id == user_id,
        OrgMembership.organization_id == organization_id,
    ).first()

    if membership:
        membership.role = role
    else:
        membership = OrgMembership(
            user_id=user_id,
            organization_id=organization_id,
            role=role,
        )
        db.add(membership)

    db.flush()
    return membership
