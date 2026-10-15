"""Message-check route: the core analysis endpoint (CLAUDE.md 12.9)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import CheckRequest
from app.config import get_settings
from app.db.base import get_session
from app.db.models import User
from app.pipeline.pipeline import analyze
from app.pipeline.schemas import AnalysisResult
from app.services import store
from app.services.ratelimit import CHECK_PER_DAY, CHECK_PER_MINUTE, limiter

router = APIRouter(prefix="/api", tags=["check"])

_RATE_LIMITED = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="You've reached the check limit. Please try again shortly.",
)


@router.post("/check", response_model=AnalysisResult)
async def check_message(
    body: CheckRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnalysisResult:
    if not limiter.check(f"check-min:{user.id}", CHECK_PER_MINUTE):
        raise _RATE_LIMITED
    if not limiter.check(f"check-day:{user.id}", CHECK_PER_DAY):
        raise _RATE_LIMITED

    settings = get_settings()
    entities = await store.list_trusted(session, user.id)
    trusted = store.to_pipeline_trusted(entities)
    language = body.language or user.language

    return await analyze(body.message, trusted, settings, language=language)
