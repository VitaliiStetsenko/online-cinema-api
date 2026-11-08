"""Cleanup tasks for Celery Beat."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.models.user import ActivationToken, PasswordResetToken, RefreshToken


@celery_app.task
def cleanup_expired_tokens():
    """Remove expired tokens from database."""
    asyncio.run(_cleanup_expired_tokens())


async def _cleanup_expired_tokens():
    """Async cleanup of expired tokens."""
    engine = create_async_engine(settings.database_url)
    session_maker = async_sessionmaker(engine)
    try:
        async with session_maker() as db:
            now = datetime.now(UTC)
            results = await asyncio.gather(
                db.execute(delete(ActivationToken).where(ActivationToken.expires_at < now)),
                db.execute(delete(PasswordResetToken).where(PasswordResetToken.expires_at < now)),
                db.execute(delete(RefreshToken).where(RefreshToken.expires_at < now)),
            )
            await db.commit()
            logger.info("Deleted %s expired tokens", sum(result.rowcount for result in results))
    finally:
        await engine.dispose()


logger = logging.getLogger(__name__)
