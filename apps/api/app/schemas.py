from datetime import datetime

from pydantic import BaseModel


class UserBase(BaseModel):
    github_id: int
    github_login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationBase(BaseModel):
    github_id: int
    slug: str
    name: str
    avatar_url: str | None = None


class OrganizationResponse(OrganizationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrgMembershipResponse(BaseModel):
    id: int
    user_id: int
    organization_id: int
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    organization: OrganizationResponse


class CurrentUser(BaseModel):
    id: int
    github_login: str
    organization_id: int
    role: str


class IntegrationBase(BaseModel):
    type: str
    installation_id: int


class IntegrationResponse(IntegrationBase):
    id: int
    organization_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class GitHubAppInstallRequest(BaseModel):
    installation_id: int
    setup_action: str


class GitHubAppInstallResponse(BaseModel):
    success: bool
    message: str


class RepositoryResponse(BaseModel):
    id: int
    organization_id: int
    full_name: str
    owner: str
    name: str
    default_branch: str
    description: str | None
    html_url: str
    status: str
    last_synced_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class IngestionJobResponse(BaseModel):
    id: int
    organization_id: int
    repository_id: int
    kind: str
    status: str
    attempts: int
    error: str | None
    created_at: datetime
    finished_at: datetime | None

    class Config:
        from_attributes = True
