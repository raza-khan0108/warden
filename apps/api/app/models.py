from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    owner: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_url: Mapped[str] = mapped_column(String(500))
    # pending | syncing | ready | failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    files: Mapped[list["RepoFile"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", passive_deletes=True
    )


class RepoFile(Base):
    __tablename__ = "repo_files"
    __table_args__ = (UniqueConstraint("repository_id", "path", name="uq_repo_file_path"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(Text)
    sha: Mapped[str] = mapped_column(String(40))
    size: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)

    repository: Mapped[Repository] = relationship(back_populates="files")
