from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.schemas import CurrentUser

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict:
    return {"status": "ok"}


@router.get("/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    has_vector = db.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ).first()
    return {"database": "ok", "pgvector": bool(has_vector)}


@router.get("/protected")
def health_protected(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return {
        "status": "ok",
        "user": current_user.github_login,
        "org_id": current_user.organization_id,
    }
