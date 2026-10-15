"""Family-alert route: email a trusted contact (CLAUDE.md 12.9, section 4).

The alert carries no message content — only the risk level and a suggested
verification question. The target contact must belong to the caller, and
alerts are rate-limited per user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import AlertRequest, AlertResponse
from app.config import get_settings
from app.db.base import get_session
from app.db.models import User
from app.services import store
from app.services.ratelimit import ALERT_PER_DAY, limiter
from app.services.ses import send_family_alert

router = APIRouter(prefix="/api", tags=["alert"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
_RATE_LIMITED = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Daily alert limit reached.",
)


@router.post("/alert", response_model=AlertResponse)
async def send_alert(
    body: AlertRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AlertResponse:
    if not limiter.check(f"alert-day:{user.id}", ALERT_PER_DAY):
        raise _RATE_LIMITED

    contact = await store.get_family(session, user.id, body.family_contact_id)
    if contact is None:
        raise _NOT_FOUND

    settings = get_settings()
    sent_ok = await send_family_alert(
        settings,
        to_email=contact.email,
        risk_level=body.risk_level,
        verification_question=body.verification_question,
        language=user.language,
    )
    alert = await store.create_alert(
        session,
        user.id,
        family_contact_id=contact.id,
        risk_level=body.risk_level,
        sent_ok=sent_ok,
    )
    await session.commit()
    return AlertResponse(id=alert.id, sent_ok=sent_ok)
