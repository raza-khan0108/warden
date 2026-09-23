from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# pool_pre_ping checks a connection is alive before handing it out, so a
# dropped connection (e.g. the db container restarted) doesn't surface as a
# confusing error on the next request.
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """All ORM models inherit from this. Its .metadata is what Alembic reads
    to know what tables should exist."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: opens one Session per request, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
