from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthCredentials

from app.api import auth, health
from app.auth import get_current_user
from app.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


async def token_dependency(credentials: HTTPAuthCredentials | None = Depends(security)) -> str | None:
    """Extract token from Authorization header."""
    return credentials.credentials if credentials else None


app.dependency_overrides[str] = token_dependency

app.include_router(health.router)
app.include_router(auth.router)
