from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class OrgRole(str, Enum):
    OWNER = "owner"
    MEMBER = "member"


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    owner: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_url: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="repositories")
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


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    github_login: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[list["OrgMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[list["OrgMembership"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", passive_deletes=True
    )
    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", passive_deletes=True
    )


class OrgMembership(Base):
    __tablename__ = "org_memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_user_org"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), default=OrgRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")
