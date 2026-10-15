"""Demo account seed (CLAUDE.md section 4, "cuenta demo precargada").

Judges can sign in with the demo credentials below and try Faro without
registering. The account ships with a trusted circle (a Costa Rican bank) and
one family contact, so the full flow — check, trusted circle, family alert —
works immediately.

The demo password is intentionally public; it guards only throwaway demo data
that is reset on each startup. Real accounts use normal registration.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import SessionLocal
from app.services import store
from app.services.auth import hash_password

logger = logging.getLogger("faro")

DEMO_EMAIL = "demo@faro.app"
DEMO_PASSWORD = "FaroDemo2026!"  # noqa: S105  # nosec B105 — public demo credential
DEMO_LANGUAGE = "es"


async def _seed(session: AsyncSession) -> None:
    user = await store.get_user_by_email(session, DEMO_EMAIL)
    if user is None:
        user = await store.create_user(
            session,
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            language=DEMO_LANGUAGE,
        )
    else:
        # Reset the demo's owned data so each run starts clean.
        await store.delete_user_data(session, user.id)

    await store.create_trusted(
        session,
        user.id,
        kind="bank",
        name="BAC Credomatic",
        domains=["baccredomatic.com"],
        phones=["2295-9898"],
        emails=["servicioalcliente@baccredomatic.com"],
    )
    await store.create_trusted(
        session,
        user.id,
        kind="company",
        name="SINPE",
        domains=["sinpe.fi.cr"],
        phones=[],
        emails=[],
    )
    await store.create_family(
        session,
        user.id,
        name="Familiar de confianza",
        email="demo-familia@faro.app",
        relationship_label="hijo",
    )
    await session.commit()


async def ensure_demo_account() -> None:
    """Create or reset the demo account. Best-effort; never blocks startup."""
    try:
        async with SessionLocal() as session:
            await _seed(session)
        logger.info("Demo account ready (%s).", DEMO_EMAIL)
    except Exception as exc:  # noqa: BLE001 — seeding must not crash startup
        logger.warning("Demo seed skipped: %s", type(exc).__name__)
