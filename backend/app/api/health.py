from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

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
